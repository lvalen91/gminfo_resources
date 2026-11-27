"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const wsURL = (p) => (location.protocol === "https:" ? "wss://" : "ws://") + location.host + p;
// opts.timeout (ms, opt-in): abort a request that has not answered by then. Used by the
// page-load reads and the status poll so a connection stuck in TCP connect (observed:
// ERR_CONNECTION_TIMED_OUT after ~15-20 s, e.g. a stale cached address for pi-bench.local)
// fails fast and is retried, instead of holding its section blank for the whole timeout.
// Long-running actions (UDS, calibration, installs) never pass it.
async function api(path, opts = {}) {
  const { timeout, ...fetchOpts } = opts;
  let timer;
  if (timeout) {
    const ac = new AbortController();
    fetchOpts.signal = ac.signal;
    timer = setTimeout(() => ac.abort(), timeout);
  }
  let r;
  try { r = await fetch("/api" + path, fetchOpts); }
  catch (e) {
    if (e.name === "AbortError") throw new Error(`no reply from /api${path} within ${timeout / 1000}s`);
    throw e;
  } finally { clearTimeout(timer); }
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch { j = { raw: t }; }
  if (!r.ok) {
    // FastAPI 422 puts a list of objects in `detail`; never let it render as [object Object]
    const d = j.detail ?? j.raw ?? "";
    throw new Error(`${r.status}: ${typeof d === "string" ? d : JSON.stringify(d)}`);
  }
  return j;
}
const esc = (s) => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const INIT_TIMEOUT = 8000;  // page-load reads all answer in <0.2 s when the Pi is reachable
const loadingHTML = (text, failed = false) => `<span class="loading${failed ? " failed" : ""}">${esc(text)}</span>`;
// Page-load reads used to be fire-once: a request that failed (backend restarting -> 502,
// connect timeout) left its section showing an error or nothing until a manual reload.
// Retry with backoff until it succeeds; `onRetry(err, delayMs)` shows the pending state.
async function loadUntilOk(fn, onRetry) {
  for (let attempt = 0; ; attempt++) {
    try { return await fn(); }
    catch (e) {
      const delay = Math.min(1000 * 2 ** attempt, 15000);
      try { onRetry && onRetry(e, delay); } catch { /* display only */ }
      await sleep(delay);
    }
  }
}

/* ---------------- tabs ---------------- */
$$("#tabs button").forEach(b => b.onclick = () => {
  $$("#tabs button").forEach(x => x.classList.toggle("active", x === b));
  $$(".tab").forEach(t => t.classList.toggle("active", t.id === "tab-" + b.dataset.tab));
  if (b.dataset.tab === "uart") initUart();
  if (b.dataset.tab === "t1") refreshAdb();
  if (b.dataset.tab === "pi") { startPiPoll(); refreshT1(); } else stopPiPoll();
  if (b.dataset.tab === "can") startCanDecodePoll(); else stopCanDecodePoll();
  if (b.dataset.tab === "capture") startCapPoll(); else stopCapPoll();
  if (b.dataset.tab === "controls") startPowerModePoll(); else stopPowerModePoll();
  // a terminal opened (or the window resized) while its tab was hidden has a stale size
  if (b.dataset.tab === "term") {
    piFit && piFit.fit(); adbFit && adbFit.fit();
    // The adb-shell device dropdown only ever got filled by visiting T1/adb or
    // clicking its Refresh button -- a device that appears (radio powers on,
    // adb-over-T1 connects) while you're already on this tab never showed up.
    // Refresh it every time this tab is opened, in addition to the periodic poll.
    refreshAdb();
  }
});
const tickClock = () => $("#clock").textContent = new Date().toLocaleTimeString();
tickClock(); setInterval(tickClock, 1000);  // set now, not 1 s after load

/* ---------------- confirm modal ---------------- */
function confirmPhrase(title, body, phrase) {
  return new Promise((resolve) => {
    $("#modalTitle").textContent = title;
    $("#modalBody").innerHTML = body;
    $("#modalInput").value = "";
    $("#modalInput").placeholder = phrase;
    $("#modal").classList.remove("hidden");
    const ok = $("#modalOk"), cancel = $("#modalCancel");
    const done = (v) => { $("#modal").classList.add("hidden"); ok.onclick = cancel.onclick = null; resolve(v); };
    ok.onclick = () => done($("#modalInput").value === phrase ? phrase : null);
    cancel.onclick = () => done(null);
  });
}

/* ---------------- status header ---------------- */
function ind(id, label, state, text) {
  return `<div class="ind" title="${esc(text || "")}"><span class="dot ${state}"></span>${esc(label)}</div>`;
}
// Backend tri-state -> dot class. "zero" (link up, peer silent) is amber, never red;
// "error" (link down / socket failed) is red; "stale" (not observing) is grey.
const STATE_DOT = { ok: "ok", zero: "warn", error: "bad", stale: "stale" };
const dotFor = (state) => STATE_DOT[state] || "stale";
let statusBusy = false;
let statusEverOk = false;
let statusRetry = null;
async function refreshStatus() {
  if (statusBusy) return;  // /api/status can take longer than the poll interval
  statusBusy = true;
  clearTimeout(statusRetry);
  try {
    // ~1.1 s normally (it probes CAN, T1, UART and adb). The timeout matters: without it a
    // request stuck in TCP connect kept statusBusy set, so every 4 s tick was skipped and
    // the topbar stayed on its first result for the whole ~20 s connect timeout.
    const s = await api("/status", { timeout: 10000 });
    statusEverOk = true;
    const can = s.can, obs = can.observer || {}, t1 = s.t1;
    const parts = [];
    // controller state outranks the observer: BUS-OFF is an error, ERROR-PASSIVE a warning
    let canDot = can.present === false ? "bad" : dotFor(obs.state);
    if (can.state === "BUS-OFF" || can.state === "STOPPED") canDot = "bad";
    else if (can.state === "ERROR-PASSIVE" && canDot === "ok") canDot = "warn";
    parts.push(ind("can", "can0", canDot,
      `observer=${obs.state} controller=${can.state || "?"} errors=${obs.errors ?? "?"} keepalive=${can.keepalive_active}`));
    parts.push(ind("ka", "keepalive", can.keepalive_active ? "ok" : "bad", "0x53B sender (systemd)"));
    applyKeepaliveToggle(can.keepalive_active);
    parts.push(ind("v5", "T1 vlan5", dotFor(t1.vlan5.state),
      `${t1.vlan5.state}: ${t1.vlan5.addr} radio_ping=${t1.vlan5.radio_ping}`));
    parts.push(ind("v4", "vlan4 diag", dotFor(t1.vlan4.state),
      `${t1.vlan4.state}: ${t1.vlan4.addr} tcp=${t1.vlan4.diag_tcp_open}`));
    // no device attached is "zero", not a failure
    parts.push(ind("adb", `adb ${s.adb.count}`, s.adb.count ? "ok" : "warn",
      s.adb.devices.map(d => d.transport).join(", ") || "no devices"));
    const uok = s.uart.filter(u => u.state === "ok").length;
    parts.push(ind("uart", `UART ${uok}/${s.uart.length}`, uok ? "ok" : "warn",
      s.uart.map(u => `${u.id}: ${u.state} (${u.note})`).join("\n")));
    // field capture: shown only while recording, or after a session was aborted
    const cap = s.capture || {};
    if (cap.state === "capturing") parts.push(ind("cap", "REC", "bad", `field capture running: ${cap.id}`));
    else if (cap.state === "aborted") parts.push(ind("cap", "capture aborted", "warn", `${cap.id}: ${cap.reason}`));
    $("#indicators").innerHTML = parts.join("");
  } catch (e) {
    // Before the first successful reply this is still "connecting" (amber, says it is
    // retrying), not a hard red failure; after one, losing it is a real outage.
    $("#indicators").innerHTML = statusEverOk
      ? ind("err", "backend unreachable — retrying", "bad", String(e))
      : `<div class="ind" title="${esc(String(e))}"><span class="dot warn"></span><span class="loading">connecting… (retrying)</span></div>`;
    // retry sooner than the 4 s poll while the page has never had status
    if (!statusEverOk) statusRetry = setTimeout(refreshStatus, 1500);
  }
  finally { statusBusy = false; }
}
refreshStatus(); setInterval(refreshStatus, 4000);

/* ================= CAN ================= */
// Pull the live theme colors (light/dark follows prefers-color-scheme in style.css) so
// the two canvases aren't hardcoded to one theme.
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let idChart;
function initCanCharts() {
  // chart.umd.min.js is a separate resource load; if it failed, say so in the card and let
  // the rest of the page initialise (this used to throw and abort the whole boot block).
  if (typeof Chart === "undefined") {
    $("#canIdChartEmpty").textContent = "chart library failed to load -- reload to retry";
    $("#canIdChartEmpty").classList.add("failed");
    return;
  }
  const muted = cssVar("--muted") || "#8b98a5", border = cssVar("--border") || "#1c232d",
    ok = cssVar("--ok") || "#3fb950";
  const base = { responsive: true, animation: false, plugins: { legend: { display: false } },
    scales: { x: { ticks: { color: muted }, grid: { color: border } },
              y: { ticks: { color: muted }, grid: { color: border }, beginAtZero: true } } };
  idChart = new Chart($("#canIdChart"), { type: "bar",
    data: { labels: [], datasets: [{ data: [], backgroundColor: ok }] },
    options: { ...base, indexAxis: "y" } });
}
const canCapture = LogCapture.register("can0", "CAN0 monitor");
// Live per-frame scrolling list: off by default (owner feedback -- it produced an
// "excessive scrolling list"). Stats (errors/unique IDs/total, below) keep updating via
// the same /ws/can connection regardless of this toggle; only the raw frame-by-frame
// render/append is gated on it. State lives at module scope so it survives the
// ws.onclose auto-reconnect in startCanWS (a fresh connection must not reset the toggle
// or silently resume appending).
const canLog = $("#canLog");
let showLiveFrames = false;
let canFrameLines = [];
function renderCanLog() {
  canLog.textContent = showLiveFrames
    ? (canFrameLines.join("\n") || "(no frames captured yet)")
    : "live frame list paused -- turn on “show live frames” above to resume";
}
renderCanLog();
$("#canLiveToggle").onchange = (e) => { showLiveFrames = e.target.checked; renderCanLog(); };
let canWsEverOpen = false;
function startCanWS() {
  const ws = new WebSocket(wsURL("/ws/can"));
  // Chrome lets only one WebSocket per host sit in CONNECTING; one stuck in TCP connect
  // would also hold up the terminal/UART sockets. Give up after 8 s and reconnect.
  const connectTimer = setTimeout(() => { if (ws.readyState === WebSocket.CONNECTING) ws.close(); }, 8000);
  ws.onopen = () => {
    clearTimeout(connectTimer);
    canWsEverOpen = true;
    if (!$("#canStatRow b")) $("#canStatRow").innerHTML = loadingHTML("connected, waiting for stats…");
  };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "frame") {
      const f = m.data;
      const line = `${f.t.toFixed(3)}  ${f.id.padEnd(4)} [${f.dlc}] ${f.data}`;
      canFrameLines.unshift(line);
      if (canFrameLines.length > 200) canFrameLines.pop();
      if (showLiveFrames) canLog.textContent = canFrameLines.join("\n");
      canCapture.push(line + "\n");
    } else if (m.type === "stats") {
      const s = m.data;
      if (idChart) {
        idChart.data.labels = s.top_ids.map(x => x.id);
        idChart.data.datasets[0].data = s.top_ids.map(x => x.count);
        idChart.update();
        $("#canIdChartEmpty").textContent = "no CAN frames seen yet";
        $("#canIdChartEmpty").hidden = s.top_ids.length > 0;
      }
      $("#canStatRow").innerHTML =
        `<span>errors <b>${s.errors}</b></span>` +
        `<span>unique IDs <b>${s.unique_ids}</b></span><span>total <b>${s.total}</b></span>` +
        (s.last_error ? `<span style="color:var(--bad)">${esc(s.last_error)}</span>` : "");
    }
  };
  ws.onclose = () => {
    clearTimeout(connectTimer);
    // say so, instead of leaving the last stats/frames on screen looking live
    $("#canStatRow").innerHTML = canWsEverOpen
      ? `<span style="color:var(--bad)">/ws/can disconnected, reconnecting...</span>`
      : loadingHTML("connecting to /ws/can… (retrying)");
    setTimeout(startCanWS, 2000);
  };
}

/* ---- decoded signals (read-only: /api/can/decode) ----
// Polls the backend decoder, which runs the same passive observer's frames through a
// vendored opendbc CANParser against backend/gm_bench.dbc. Nothing here transmits. The
// poll runs only while the CAN tab is on screen (started at boot, since CAN is default). */
let canDecodePoll = null, canDecodeBusy = false, canDecodeEver = false;
async function refreshCanDecode() {
  if (canDecodeBusy) return;
  canDecodeBusy = true;
  try { renderCanDecode(await api("/can/decode", { timeout: 10000 })); canDecodeEver = true; }
  catch (e) {
    if (!canDecodeEver) $("#canDecode").innerHTML = loadingHTML(`couldn't load (${e.message}) — retrying…`, true);
  } finally { canDecodeBusy = false; }
}
function renderCanDecode(d) {
  $("#canDecodeMeta").innerHTML =
    `DBC <span class="mono">${esc(d.dbc)}</span> · ${d.message_count} messages · ` +
    `<b>${d.frames_decoded}</b> frames decoded`;
  const blocks = d.messages.map(m => {
    const pill = m.seen ? statePill("ok", `seen ×${m.count}`) : statePill("stale", "not seen yet");
    const age = m.seen && m.age_s != null ? `<span class="row-sub">${m.age_s}s ago</span>` : "";
    const raw = m.seen ? `<span class="mono muted">${esc(m.raw_hex)}</span>` : "";
    const sigRows = m.signals.map(s => {
      const isEnum = s.has_enum && typeof s.value === "string";
      const val = isEnum
        ? `<span class="state-pill state-ok">${esc(s.value)}</span> <span class="muted mono">(${s.raw})</span>`
        : `<b class="mono">${esc(s.value)}</b>`;
      const note = s.note ? ` title="${esc(s.note)}"` : "";
      return `<tr><td class="mono"${note}>${esc(s.name)}${s.note ? ' <span class="muted">&#9432;</span>' : ""}</td>
        <td>${val}</td></tr>`;
    }).join("");
    return `<div class="decode-msg${m.seen ? "" : " unseen"}">
      <div class="decode-head">
        <span class="mono decode-id">0x${esc(m.id)}</span>
        <span class="decode-name">${esc(m.name)}</span>
        <span class="muted">DLC ${m.dlc}</span>
        ${pill} ${age} ${raw}
        <button class="seq-info decode-info" type="button" aria-label="about this message" title="${esc(m.note)}">&#9432;</button>
      </div>
      <table class="decode-sigs">${sigRows}</table>
    </div>`;
  }).join("");
  $("#canDecode").innerHTML = blocks;
}
function startCanDecodePoll() {
  refreshCanDecode();
  if (!canDecodePoll) canDecodePoll = setInterval(refreshCanDecode, 1000);
}
function stopCanDecodePoll() { clearInterval(canDecodePoll); canDecodePoll = null; }

// A sequence is one of two UI shapes, decided by the backend `kind` (sequences.py):
//   continuous (full, startup-keepalive) -> an ON/OFF toggle; the run transmits until
//     stopped (SIGTERM via /can/sequence/stop).
//   one-shot (startup, vip-reset) -> a RUN control with a live progress/elapsed readout;
//     the process exits on its own. `duration_s` (when the code knows it) drives a
//     determinate bar; otherwise an indeterminate spinner + elapsed.
// While a one-shot is mid-run every row greys out (one-shots own the bus exclusively, so
// a continuous schedule is itself stopped by the backend's exclusive_bus takeover).
//
// keepalive-start/keepalive-stop (kind service-start/service-stop) are a long-running
// systemd service, not a one-shot or a continuous CAN-frame loop -- they get the same
// ON/OFF toggle affordance as "continuous" (one real control, not two separate buttons),
// but its on/off state comes from can.keepalive_active (/api/status, already polled by
// refreshStatus()), never from continuous_status() -- that endpoint only knows about the
// true continuous sequences and has no idea the keepalive service exists.
let _seqSpecs = [];
let _seqBusyOneshot = false;
const seqRow = (name) => $(`#seqList .seq-row[data-seq="${CSS.escape(name)}"]`);
const seqIsContinuous = (s) => s.kind === "continuous";
const KEEPALIVE_START = "keepalive-start", KEEPALIVE_STOP = "keepalive-stop";
// No-dry-run-left raw results aren't worth a permanent JSON box on every row; the full
// result still goes somewhere -- the bench log ("Export logs" above), via LogCapture.
const seqLog = LogCapture.register("sequences", "CAN sequences");
function renderSeqResult(name, statusEl, result) {
  renderExecResult(statusEl, null, result);
  const isErr = result instanceof Error;
  const body = isErr ? String(result) : JSON.stringify(result, null, 2);
  seqLog.push(`[${new Date().toISOString()}] ${name}\n${body}\n\n`);
}

async function loadSequences() {
  let sequences, continuous;
  try {
    ({ sequences, continuous } = await loadUntilOk(() => api("/can/sequences", { timeout: INIT_TIMEOUT }),
      (e, d) => $("#seqList").innerHTML = loadingHTML(`couldn't load sequences (${e.message}) -- retrying in ${d / 1000}s…`, true)));
  } catch (e) { $("#seqList").innerHTML = "error: " + esc(String(e)); return; }
  _seqSpecs = sequences;
  renderSequences(sequences);
  applyContinuous(continuous);
}
function renderSequences(sequences) {
  // keepalive-start/-stop render as one merged toggle row (see the comment above
  // seqIsContinuous); everything else keeps its existing continuous-toggle/oneshot-run shape.
  const shown = sequences.filter(s => s.name !== KEEPALIVE_START && s.name !== KEEPALIVE_STOP);
  const hasKeepalivePair = sequences.some(s => s.name === KEEPALIVE_START)
    && sequences.some(s => s.name === KEEPALIVE_STOP);
  const keepaliveRow = hasKeepalivePair ? `<div class="seq-row" data-seq="keepalive" data-kind="keepalive">
      <div class="seq-main">
        <span class="seq-name">keepalive</span>
        <button class="seq-info" data-seq="${esc(KEEPALIVE_START)}" aria-label="what this sequence does" title="what this does">&#9432;</button>
      </div>
      <div class="seq-control">
        <label class="seq-toggle" title="turn the 0x53B keepalive service on/off">
          <input type="checkbox" class="seq-switch seq-switch-keepalive">
          <span class="seq-slider"></span><span class="seq-toggle-txt">OFF</span></label>
      </div>
      <div class="seq-status"><div class="exec-status"></div></div>
    </div>` : "";
  $("#seqList").innerHTML = keepaliveRow + shown.map(s => {
    const control = seqIsContinuous(s)
      ? `<label class="seq-toggle" title="turn this sequence on/off">
           <input type="checkbox" class="seq-switch" data-seq="${esc(s.name)}">
           <span class="seq-slider"></span><span class="seq-toggle-txt">OFF</span></label>`
      : `<button class="seq-run ${s.destructive ? "destructive" : ""}" data-seq="${esc(s.name)}">&#9654; RUN${s.destructive ? " &#9888;" : ""}</button>
         <span class="seq-progress" data-seq="${esc(s.name)}"></span>`;
    return `<div class="seq-row" data-seq="${esc(s.name)}" data-kind="${esc(seqIsContinuous(s) ? "continuous" : "oneshot")}">
      <div class="seq-main">
        <span class="seq-name">${esc(s.name)}${s.destructive ? ' <span class="tag avoid">destructive</span>' : ""}</span>
        <button class="seq-info" data-seq="${esc(s.name)}" aria-label="what this sequence does" title="what this does">&#9432;</button>
      </div>
      <div class="seq-control">${control}</div>
      <div class="seq-status"><div class="exec-status"></div></div>
    </div>`;
  }).join("");
  $$("#seqList .seq-info").forEach(b => b.onclick = (e) => {
    e.stopPropagation();
    const s = _seqSpecs.find(x => x.name === b.dataset.seq);
    infoPopover(b, (s && s.desc) || b.dataset.seq);
  });
  $$("#seqList .seq-run").forEach(b => b.onclick = () => {
    const s = _seqSpecs.find(x => x.name === b.dataset.seq);
    if (s.destructive) runSeqDestructive(s, b);
    else runSeqOneshot(s);
  });
  $$("#seqList .seq-switch:not(.seq-switch-keepalive)").forEach(c => c.onchange = () => {
    const s = _seqSpecs.find(x => x.name === c.dataset.seq);
    toggleContinuous(s, c);
  });
  const kaBox = $("#seqList .seq-switch-keepalive");
  if (kaBox) kaBox.onchange = () => toggleKeepalive(kaBox);
  applyKeepaliveToggle(lastKeepaliveActive);
}
// Reflect which continuous sequence (if any) is running, and the global one-shot lock.
// Excludes the keepalive toggle: that one reflects can.keepalive_active, not this endpoint,
// which has no idea the keepalive service exists (see the comment above seqIsContinuous).
function applyContinuous(continuous) {
  const running = continuous && continuous.running ? continuous.sequence : null;
  $$("#seqList .seq-switch:not(.seq-switch-keepalive)").forEach(c => {
    const on = c.dataset.seq === running;
    c.checked = on;
    const row = c.closest(".seq-row");
    row.classList.toggle("seq-on", on);
    const txt = row.querySelector(".seq-toggle-txt");
    if (txt) txt.textContent = on ? "ON" : "OFF";
  });
  updateSeqLock();
}
// Reflect the keepalive systemd service's real state, sourced only from can.keepalive_active
// (refreshStatus(), below) -- never from continuous_status(). Cached in lastKeepaliveActive
// so a re-render (tab reopen, a toggle's own result refresh) doesn't flash "OFF" before the
// next status poll lands.
let lastKeepaliveActive = null;
function applyKeepaliveToggle(active) {
  if (active == null) return;
  lastKeepaliveActive = active;
  const cb = $("#seqList .seq-switch-keepalive");
  if (!cb) return;
  cb.checked = !!active;
  const row = cb.closest(".seq-row");
  row.classList.toggle("seq-on", !!active);
  const txt = row.querySelector(".seq-toggle-txt");
  if (txt) txt.textContent = active ? "ON" : "OFF";
}
async function toggleKeepalive(cb) {
  if (_seqBusyOneshot) { cb.checked = !cb.checked; return; }
  const row = cb.closest(".seq-row");
  const status = row.querySelector(".exec-status");
  const name = cb.checked ? KEEPALIVE_START : KEEPALIVE_STOP;
  _seqBusyOneshot = true; updateSeqLock();
  renderExecPending(status);
  let result;
  try {
    result = await api("/can/sequence/" + name, { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: false }) });
  } catch (e) { result = e; }
  renderSeqResult(name, status, result);
  _seqBusyOneshot = false; updateSeqLock();
  await refreshContinuous();  // keepalive-stop also stops any running continuous (exclusive bus)
  await refreshStatus();      // reconcile the toggle with the real keepalive_active state
}
function updateSeqLock() {
  $("#seqList").classList.toggle("seq-locked", _seqBusyOneshot);
  $$("#seqList .seq-switch, #seqList .seq-run").forEach(el => { el.disabled = _seqBusyOneshot; });
}
// A determinate bar when the code knows the duration, else an indeterminate spinner; both
// show an elapsed-seconds counter. Returns a stop() that clears the indicator.
function startSeqProgress(name, durationS) {
  const prog = seqRow(name) && seqRow(name).querySelector(".seq-progress");
  const run = seqRow(name) && seqRow(name).querySelector(".seq-run");
  if (run) run.classList.add("running");
  const start = Date.now();
  const tick = () => {
    if (!prog) return;
    const el = (Date.now() - start) / 1000;
    if (durationS) {
      const pct = Math.min(99, (el / durationS) * 100);
      prog.innerHTML = `<span class="seq-bar"><span class="seq-bar-fill" style="width:${pct}%"></span></span><span class="seq-elapsed">${el.toFixed(1)}s / ~${durationS}s</span>`;
    } else {
      prog.innerHTML = `<span class="seq-spin"></span><span class="seq-elapsed">${el.toFixed(1)}s</span>`;
    }
  };
  tick();
  const timer = setInterval(tick, 150);
  return () => { clearInterval(timer); if (prog) prog.innerHTML = ""; if (run) run.classList.remove("running"); };
}
async function refreshContinuous() {
  try { const { continuous } = await api("/can/sequences"); applyContinuous(continuous); } catch { /* transient */ }
}
async function runSeqOneshot(s) {
  if (_seqBusyOneshot) return;
  _seqBusyOneshot = true; updateSeqLock();
  const row = seqRow(s.name);
  const status = row.querySelector(".exec-status");
  renderExecPending(status);
  const stop = startSeqProgress(s.name, s.duration_s);
  let result;
  try {
    result = await api("/can/sequence/" + s.name, { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: false }) });
  } catch (e) { result = e; }
  stop();
  renderSeqResult(s.name, status, result);
  _seqBusyOneshot = false; updateSeqLock();
  await refreshContinuous();  // a one-shot may have stopped a running continuous (exclusive bus)
}
function runSeqDestructive(s, btn) {
  // Destructive one-shot (vip-reset): keep the Tier-2 plan->execute confirm (that's the
  // real server-side gate, not UI friction) -- drive the row lock + progress ring, and
  // also mirror the result into the bench log like every other sequence (the popover's
  // own exec-more detail box is a one-time confirm aid, not something we duplicate here).
  let stop;
  tier2Popover(btn,
    () => api("/can/sequence/" + s.name + "/plan", { method: "POST" }),
    "/can/sequence/" + s.name + "/execute",
    seqRow(s.name).querySelector(".seq-status"),
    { onExecStart: () => { _seqBusyOneshot = true; updateSeqLock(); stop = startSeqProgress(s.name, s.duration_s); },
      onExecEnd: async (result) => {
        if (stop) stop(); _seqBusyOneshot = false; updateSeqLock();
        seqLog.push(`[${new Date().toISOString()}] ${s.name}\n${result instanceof Error ? String(result) : JSON.stringify(result, null, 2)}\n\n`);
        await refreshContinuous();
      } });
}
async function toggleContinuous(s, cb) {
  if (_seqBusyOneshot) { cb.checked = !cb.checked; return; }
  const row = seqRow(s.name);
  const status = row.querySelector(".exec-status");
  const turningOn = cb.checked;
  if (turningOn && s.destructive) {
    // A destructive continuous keeps the confirm gate; don't latch until confirmed.
    cb.checked = false;
    runSeqDestructive(s, cb.closest(".seq-toggle"));
    return;
  }
  cb.disabled = true;
  renderExecPending(status);
  let result;
  try {
    result = turningOn
      ? await api("/can/sequence/" + s.name, { method: "POST",
          headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: false }) })
      : await api("/can/sequence/stop", { method: "POST" });
  } catch (e) { result = e; }
  renderSeqResult(s.name, status, result);
  cb.disabled = false;
  await refreshContinuous();  // reflect the real running state
}
let _seqPoll = null;
let seqPollBusy = false;  // overlap guard, same pattern as refreshStatus()'s statusBusy
function startSeqPoll() {
  if (_seqPoll) return;
  // A cheap poll of the lightweight /sequences endpoint so a continuous toggle reflects a
  // run started by another client (the API, a CLI run, a previous session). Skipped while a
  // one-shot is mid-run (its own completion handler refreshes), and overlap-guarded.
  _seqPoll = setInterval(async () => {
    if (seqPollBusy || _seqBusyOneshot) return;
    seqPollBusy = true;
    try { const { continuous } = await api("/can/sequences"); applyContinuous(continuous); }
    catch (e) { /* transient; next poll retries */ }
    finally { seqPollBusy = false; }
  }, 3000);
}

/* ================= Vehicle state (engine power mode / gear position) =================
 * Zero-guessing: only a state the backend marks verified gets a live segmented button
 * (wired through the same Tier-2 plan->execute flow as every other destructive CAN
 * action here); an unverified state renders disabled with the backend's own reason in
 * its tooltip, and its plan endpoint always refuses (409/501) -- this UI never invents a
 * byte pattern or lets a click reach the bus for one. */
async function loadVehiclePowerModes() {
  const wrap = $("#vehiclePowerModes");
  try {
    const { modes } = await loadUntilOk(() => api("/vehicle/power-modes", { timeout: INIT_TIMEOUT }),
      (e, d) => wrap.innerHTML = `<span class="seg-loading">${loadingHTML(`couldn't load (${e.message}) -- retrying in ${d / 1000}s…`, true)}</span>`);
    wrap.innerHTML = modes.map(m => {
      const title = m.verified ? esc(m.evidence) : esc("No verified CAN signal -- scaffold only: " + m.reason);
      return `<button class="seg-btn" data-mode="${esc(m.name)}" ${m.verified ? "" : "disabled"} title="${title}">${esc(m.label)}${m.verified ? "" : " — unverified"}</button>`;
    }).join("");
    $$("#vehiclePowerModes button[data-mode]").forEach(b => {
      if (b.disabled) return;
      // Not destructive (owner call): picking a power mode is a plain select-and-highlight,
      // no confirmation step. The backend still requires a real plan->token->execute
      // round-trip (that's the server's actual security gate, not UI friction), so this
      // still calls both -- it just never shows the user a popup to click through.
      b.onclick = () => selectPowerMode(b);
    });
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
// Repeat-send: hold the selected power mode by CO-SENDING its frame on an interval
// (No/5/10/15 s). The initial select goes through the verified plan->execute (pauses the
// keepalive once); each repeat co-sends the same frame via /api/can/send with
// pause_keepalive=false, so it never cycles the keepalive/interface (which would thrash
// the bus and drop frames).
let _pmRepeatSecs = 0, _pmRepeatFrame = null, _pmRepeatTimer = null;
async function selectPowerMode(b) {
  const mode = b.dataset.mode;
  const buttons = $$("#vehiclePowerModes button[data-mode]");
  buttons.forEach(x => x.disabled = true);
  renderExecPending($("#vehicleOut"));
  let result;
  try {
    const plan = await api(`/vehicle/power-mode/${mode}/plan`, { method: "POST" });
    _pmRepeatFrame = { can_id: plan.can_id, data: plan.data_hex };
    result = await api(`/vehicle/power-mode/${mode}/execute`, { method: "POST",
      headers: { "content-type": "application/json" }, body: execBodyOf(plan, {}) });
  } catch (e) { result = e; }
  buttons.forEach(x => x.disabled = false);
  if (!(result instanceof Error) && execOutcome(result).ok) buttons.forEach(x => x.classList.toggle("sel", x === b));
  renderExecResult($("#vehicleOut"), null, result);
  restartPmRepeat();
}
function restartPmRepeat() {
  clearInterval(_pmRepeatTimer); _pmRepeatTimer = null;
  if (_pmRepeatSecs > 0 && _pmRepeatFrame)
    _pmRepeatTimer = setInterval(() => {
      api("/can/send", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ..._pmRepeatFrame, pause_keepalive: false }) }).catch(() => {});
    }, _pmRepeatSecs * 1000);
}
function setPmRepeat(secs) {
  _pmRepeatSecs = secs;
  $$("#pmRepeat button[data-repeat]").forEach(x => x.classList.toggle("sel", +x.dataset.repeat === secs));
  restartPmRepeat();
}
// Live power-mode readback (UDS DID F085 on raw CAN5). This POLL TRANSMITS a UDS request
// on can0 every 3 s while the Controls tab is open -- active, not passive observation.
let _pmPoll = null;
async function pollActivePowerMode() {
  const badge = $("#activePowerMode"); if (!badge) return;
  const clear = () => $$("#vehiclePowerModes button[data-mode]").forEach(x => x.classList.remove("live-active"));
  try {
    const r = await api("/vehicle/power-mode/active", { timeout: 4000 });
    const mode = r.ok ? r.mode : null;
    badge.textContent = r.ok ? `live: ${mode || "0x" + r.value_hex}` : "live: no response";
    badge.classList.toggle("muted", !r.ok || !mode);
    $$("#vehiclePowerModes button[data-mode]").forEach(x =>
      x.classList.toggle("live-active", !!mode && x.dataset.mode === mode));
  } catch (e) {
    badge.textContent = "live: error"; badge.classList.add("muted"); clear();
  }
}
function startPowerModePoll() { pollActivePowerMode(); if (!_pmPoll) _pmPoll = setInterval(pollActivePowerMode, 3000); }
function stopPowerModePoll() { clearInterval(_pmPoll); _pmPoll = null; }
async function loadVehicleGearPositions() {
  const wrap = $("#vehicleGearPositions");
  try {
    const { positions } = await loadUntilOk(() => api("/vehicle/gear-positions", { timeout: INIT_TIMEOUT }),
      (e, d) => wrap.innerHTML = `<span class="seg-loading">${loadingHTML(`couldn't load (${e.message}) -- retrying in ${d / 1000}s…`, true)}</span>`);
    wrap.innerHTML = positions.map(p =>
      `<button class="seg-btn" disabled title="${esc('No verified CAN signal -- scaffold only: ' + p.reason)}">${esc(p.label)} — unverified</button>`).join("");
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}

/* ================= Driver door (verified CAN 0x4DA, send-only) ================= */
async function loadVehicleDoors() {
  const wrap = $("#vehicleDoors");
  try {
    const { doors } = await loadUntilOk(() => api("/vehicle/doors", { timeout: INIT_TIMEOUT }),
      (e, d) => wrap.innerHTML = `<span class="seg-loading">${loadingHTML(`couldn't load (${e.message}) -- retrying in ${d / 1000}s…`, true)}</span>`);
    wrap.innerHTML = doors.map(m =>
      `<button class="seg-btn" data-door="${esc(m.name)}" title="${esc(m.evidence)}">${esc(m.label)}</button>`).join("");
    $$("#vehicleDoors button[data-door]").forEach(b => b.onclick = () => selectDoor(b));
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function selectDoor(b) {
  const buttons = $$("#vehicleDoors button[data-door]");
  buttons.forEach(x => x.disabled = true);
  renderExecPending($("#doorOut"));
  let result;
  try {
    const plan = await api(`/vehicle/door/${b.dataset.door}/plan`, { method: "POST" });
    result = await api(`/vehicle/door/${b.dataset.door}/execute`, { method: "POST",
      headers: { "content-type": "application/json" }, body: execBodyOf(plan, {}) });
  } catch (e) { result = e; }
  buttons.forEach(x => x.disabled = false);
  if (!(result instanceof Error) && execOutcome(result).ok) buttons.forEach(x => x.classList.toggle("sel", x === b));
  renderExecResult($("#doorOut"), null, result);
}

/* ================= Steering wheel / media controls (UDS IOCID) ================= */
async function loadSteeringControls() {
  const wrap = $("#steeringControls");
  try {
    const { controls } = await loadUntilOk(() => api("/vehicle/controls", { timeout: INIT_TIMEOUT }),
      (e, d) => wrap.innerHTML = `<span class="seg-loading">${loadingHTML(`couldn't load (${e.message}) -- retrying in ${d / 1000}s…`, true)}</span>`);
    const groups = [...new Set(controls.map(c => c.group))];
    wrap.innerHTML = groups.map(g => {
      const rows = controls.filter(c => c.group === g).map(c => c.verified
        ? `<button class="seg-btn" data-control="${esc(c.name)}" title="${esc(c.evidence)}">${esc(c.label)}</button>`
        : `<button class="seg-btn" disabled title="${esc('No verified IOCID -- scaffold only: ' + c.reason)}">${esc(c.label)} — unverified</button>`
      ).join("");
      return `<div class="field-row"><span class="field-label">${esc(g)}</span><div class="segmented">${rows}</div></div>`;
    }).join("");
    $$("#steeringControls button[data-control]").forEach(b => b.onclick = () => pressControl(b));
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function pressControl(b) {
  const buttons = $$("#steeringControls button[data-control]");
  buttons.forEach(x => x.disabled = true);
  const out = $("#controlsOut");
  renderExecPending(out);
  let result;
  try {
    result = await api(`/vehicle/control/${b.dataset.control}/press`, { method: "POST" });
  } catch (e) { result = e; }
  buttons.forEach(x => x.disabled = false);
  renderExecResult(out, null, result);
}

$("#btnEcuReset").onclick = (ev) => tier2Popover(ev.currentTarget,
  () => api("/uds/can5/ecu-reset/plan", { method: "POST" }),
  "/uds/can5/ecu-reset/execute", $("#ecuResetOut"));

/* ================= Diagnostics (UDS) ================= */
async function readSafe() {
  const wrap = $("#didTableWrap"); wrap.innerHTML = "reading...";
  try {
    const { dids } = await api("/uds/dids");
    const safe = dids.filter(d => !d.security).map(d => d.did);
    const r = await api("/uds/read", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ dids: safe }) });
    let rows = dids.map(d => {
      const res = r.reads[d.did];
      const val = res ? (res.ok ? res.response_hex : `<span style="color:var(--bad)">${res.nrc_name || "neg"}</span>`) : "-";
      return `<tr><td class="mono">${d.did}</td><td>${esc(d.name)}</td><td>${d.security ? '<span class="tag avoid">'+d.security+'</span>' : '<span class="tag ok">none</span>'}</td><td class="mono">${val}</td></tr>`;
    }).join("");
    wrap.innerHTML = `<table><tr><th>DID</th><th>Name</th><th>Security</th><th>Response</th></tr>${rows}</table>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function readCal() {
  const wrap = $("#didTableWrap"); wrap.innerHTML = "reading F182...";
  try {
    const r = await api("/uds/calibration");
    if (!r.ok) { wrap.innerHTML = "negative: " + JSON.stringify(r.uds); return; }
    const rows = r.records.map(rec => {
      const slot = rec.slot != null ? rec.slot.toString(16).toUpperCase().padStart(2, "0") : "-";
      const match = rec.matches_stock == null ? "" : (rec.matches_stock ? '<span class="tag ok">stock</span>' : '<span class="tag avoid">changed</span>');
      return `<tr><td class="mono">${rec.tag}</td><td class="mono">${slot}</td><td class="mono">${rec.part_number}</td><td class="mono">${rec.version_ascii}</td><td>${esc(rec.slot_content || "")}</td><td>${match}</td></tr>`;
    }).join("");
    wrap.innerHTML = `<p class="mono">F182: ${r.uds.response_hex.slice(0, 8)}... (${r.records.length} records, ${r.uds.elapsed_ms}ms)</p>` +
      `<table><tr><th>Tag</th><th>Slot</th><th>Part#</th><th>Ver</th><th>Content</th><th></th></tr>${rows}</table>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function readDtc() {
  const wrap = $("#didTableWrap"); wrap.innerHTML = "reading DTCs...";
  try {
    const r = await api("/uds/dtc?sub=02&mask=FF");
    wrap.innerHTML = `<pre class="out">19 02 FF -> ${esc(JSON.stringify(r, null, 2))}\n\nNote: the native DTC handler builds responses from zero-filled buffers; a positive 59 / zero count is not proof of a live fault store.</pre>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function unlock() {
  const wrap = $("#didTableWrap"); wrap.innerHTML = "requesting seed...";
  try {
    const r = await api("/uds/security/unlock", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ level: 1 }) });
    wrap.innerHTML = `<pre class="out">${esc(JSON.stringify(r, null, 2))}</pre>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function loadRoutines() {
  let routines;
  ({ routines } = await loadUntilOk(() => api("/uds/routines", { timeout: INIT_TIMEOUT }),
    (e, d) => $("#routineButtons").innerHTML = loadingHTML(`couldn't load routines (${e.message}) -- retrying in ${d / 1000}s…`, true)));
  $("#routineButtons").innerHTML = routines.map(r =>
    `<button class="${r.destructive ? "destructive" : ""}" data-rid="${r.rid}" title="${esc(r.desc)}">${esc(r.name)}${r.destructive ? " ⚠" : ""}</button>`).join("");
  $$("#routineButtons button").forEach(b => b.onclick = () => runRoutine(b.dataset.rid, routines.find(x => x.rid === b.dataset.rid)));
}
async function runRoutine(rid, spec) {
  const dry = $("#rtnDryRun").checked;
  // Destructive + live: Tier-2 plan->execute token flow (server-gated), same as the
  // calibration write. The plain POST handles dry-runs and non-destructive routines.
  if (!dry && spec.destructive) {
    tier2Flow($("#routineOut"),
      () => api("/uds/routine/" + rid + "/plan", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({}) }),
      "/uds/routine/" + rid + "/execute");
    return;
  }
  $("#routineOut").textContent = `routine ${rid} (dry_run=${dry})...`;
  try {
    const r = await api("/uds/routine/" + rid, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ dry_run: dry }) });
    $("#routineOut").textContent = JSON.stringify(r, null, 2);
  } catch (e) { $("#routineOut").textContent = "error: " + e; }
}

/* ================= Calibration ================= */
async function loadSlotMap() {
  const wrap = $("#slotTableWrap"); wrap.innerHTML = "loading...";
  try {
    const [map, live] = await Promise.all([api("/uds/slot-map"), api("/uds/calibration").catch(() => null)]);
    const liveBySlot = {};
    if (live && live.ok) live.slots.forEach(s => liveBySlot[s.slot] = s.part_number);
    const rows = map.slots.map(s => {
      const livePart = liveBySlot[s.slot_dec];
      const liveCell = livePart ? (livePart === s.part ? `<span class="tag ok">${livePart}</span>` : `<span class="tag avoid">${livePart}</span>`) : "-";
      return `<tr><td class="mono">${s.slot}</td><td class="mono">${s.part}</td><td class="mono">${s.alpha}</td><td>${s.overrides}</td><td><span class="tag ${s.triage === 'n/a' ? 'na' : s.triage}">${s.triage}</span></td><td>${esc(s.content)}</td><td>${liveCell}</td></tr>`;
    }).join("");
    wrap.innerHTML = `<table><tr><th>Slot</th><th>Part#</th><th>Alpha</th><th>#Ovr</th><th>Triage</th><th>Content</th><th>Live</th></tr>${rows}</table>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}

/* ================= UART ================= */
const uartCapture = LogCapture.register("uart", "UART console");
let uartTerm, uartFit, uartWS, uartInited = false;
function initUart() {
  if (uartInited) { uartFit && uartFit.fit(); return; }
  uartInited = true;
  uartTerm = new Terminal({ convertEol: true, fontSize: 12, scrollback: 5000, disableStdin: true,
    theme: { background: "#000000" } });
  uartFit = new FitAddon.FitAddon(); uartTerm.loadAddon(uartFit);
  uartTerm.open($("#uartTerm")); uartFit.fit();
  api("/uart/ports").then(({ ports }) => {
    $("#uartButtons").innerHTML = ports.map(p =>
      `<button data-uid="${p.id}" ${p.reachable ? "" : 'title="unreachable: ' + esc(p.note) + '"'}>${esc(p.label)}${p.reachable ? "" : " ✗"}</button>`).join("");
    $$("#uartButtons button").forEach(b => b.onclick = () => openUart(b.dataset.uid, b));
    const first = ports.find(p => p.reachable);
    if (first) openUart(first.id, $(`#uartButtons button[data-uid="${first.id}"]`));
  }).catch(e => {
    uartInited = false;  // allow a retry on the next tab visit
    $("#uartButtons").textContent = "error loading ports: " + e;
  });
}
function openUart(uid, btn) {
  $$("#uartButtons button").forEach(x => x.style.borderColor = "");
  if (btn) btn.style.borderColor = "var(--accent)";
  // detach the old socket's handlers first, or its late onclose prints into the new stream
  if (uartWS) { uartWS.onclose = uartWS.onmessage = null; uartWS.close(); }
  uartTerm.clear(); uartTerm.writeln(`\x1b[90m-- connecting ${uid} --\x1b[0m`);
  uartCapture.push(`\n-- connecting ${uid} --\n`);
  const ws = uartWS = new WebSocket(wsURL("/ws/uart/" + uid));
  ws.onmessage = (ev) => { uartTerm.write(ev.data); uartCapture.push(ev.data); };
  ws.onclose = (ev) => { uartTerm.writeln(`\r\n\x1b[90m-- disconnected (code ${ev.code}) --\x1b[0m`); uartCapture.push(`\n-- disconnected (code ${ev.code}) --\n`); };
}
window.addEventListener("resize", () => { uartFit && uartFit.fit(); piFit && piFit.fit(); adbFit && adbFit.fit(); });

/* ================= T1 / adb ================= */
async function refreshT1() {
  try {
    const t = await api("/t1");
    const row = (o) => Object.entries(o).map(([k, v]) => `<tr><td class="mono">${k}</td><td class="mono">${esc(JSON.stringify(v))}</td></tr>`).join("");
    $("#t1Status").innerHTML = `<h3>VLAN5 (adb/T1)</h3><table>${row(t.vlan5)}</table><h3>VLAN4 (diagnosticsd)</h3><table>${row(t.vlan4)}</table>`;
  } catch (e) { $("#t1Status").textContent = "error: " + e; }
  refreshAdb();
}
async function refreshAdb() {
  try {
    const { devices } = await api("/adb/devices");
    $("#adbDevices").innerHTML = devices.length
      ? `<ul class="dev-list">` + devices.map(d =>
          `<li><span class="tag ${d.transport === 'usb' ? 'ok' : 'mixed'}">${esc(d.transport)}</span> `
          + `<span class="mono">${esc(d.serial)}</span> `
          + `<span class="muted">${esc(d.state)}${d.product ? " · " + esc(d.product) : ""}</span></li>`).join("")
        + `</ul>`
      : `<span class="muted">no devices</span>`;
    const opts = devices.map(d => `<option value="${esc(d.serial)}">${esc(d.serial)} (${esc(d.transport)})</option>`).join("");
    // Preserve the current selection across a refresh (e.g. re-polling while a
    // terminal is already open against one serial shouldn't silently reselect another).
    for (const id of ["#apkSerial", "#adbShellSerial", "#pkgSerial"]) {
      const el = $(id); if (!el) continue;
      const prev = el.value; el.innerHTML = opts;
      if (devices.some(d => d.serial === prev)) el.value = prev;
    }
  } catch (e) { $("#adbDevices").textContent = "error: " + e; }
}
let _adbPoll = null;
function startAdbPoll() {
  if (_adbPoll) return;
  // Self-heal the device list (and therefore the adb-shell dropdown) even if the
  // user never revisits the T1/adb tab after a device appears or disappears.
  _adbPoll = setInterval(refreshAdb, 5000);
}
$("#btnConnectT1").onclick = async () => {
  try { await api("/adb/connect-t1", { method: "POST" }); }
  catch (e) { $("#adbDevices").textContent = "connect-t1 error: " + e; }
  refreshT1();
};
$("#btnEnableT1").onclick = async () => {
  const btn = $("#btnEnableT1"), out = $("#enableT1Out");
  btn.disabled = true;
  out.textContent = "enabling (adb tcpip over USB, then connecting over T1)...";
  try {
    const r = await api("/adb/enable-t1", { method: "POST" });
    out.textContent = JSON.stringify(r, null, 2);
  } catch (e) { out.textContent = "error: " + e; }
  btn.disabled = false;
  refreshT1();
};
$("#btnRefreshT1").onclick = refreshT1;
$("#apkForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#apkOut").textContent = "uploading + installing (may take a while)...";
  try {
    const r = await api("/adb/install", { method: "POST", body: new FormData(e.target) });
    $("#apkOut").textContent = JSON.stringify(r, null, 2);
    if (r.success && $("#pkgSerial").value === r.serial) loadPkgs();
  } catch (err) { $("#apkOut").textContent = "error: " + err; }
};
async function loadPkgs() {
  const serial = $("#pkgSerial").value, wrap = $("#pkgList");
  if (!serial) { wrap.innerHTML = `<span class="muted">no device selected</span>`; return; }
  wrap.innerHTML = `<span class="loading">loading…</span>`;
  try {
    const { packages } = await api(`/adb/packages?serial=${encodeURIComponent(serial)}`);
    if (!packages.length) { wrap.innerHTML = `<span class="muted">no third-party apps installed</span>`; return; }
    wrap.innerHTML = `<ul class="dev-list">` + packages.map(p =>
      `<li><button class="pkg-uninstall" data-pkg="${esc(p.package)}" title="uninstall">&times;</button> `
      + `<span class="mono">${esc(p.package)}</span>`
      + (p.installer ? ` <span class="muted">via ${esc(p.installer)}</span>` : "") + `</li>`).join("") + `</ul>`;
    $$("#pkgList .pkg-uninstall").forEach(b => b.onclick = () => uninstallPkg(serial, b.dataset.pkg, b));
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function uninstallPkg(serial, pkg, btn) {
  if (!confirm(`Uninstall ${pkg} from ${serial}?`)) return;
  btn.disabled = true;
  $("#pkgOut").textContent = `uninstalling ${pkg}…`;
  try {
    const r = await api("/adb/uninstall", { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify({ serial, package: pkg }) });
    $("#pkgOut").textContent = r.success ? `uninstalled ${pkg}` : `failed: ${r.output || ("exit " + r.exit_code)}`;
  } catch (e) { $("#pkgOut").textContent = "error: " + e; }
  loadPkgs();
}
$("#btnLoadPkgs").onclick = loadPkgs;
$("#canSendForm").onsubmit = async (e) => {
  e.preventDefault();
  const out = $("#canSendOut"); renderExecPending(out);
  const payload = { can_id: $("#canSendId").value.trim(), data: $("#canSendData").value.trim() };
  if ($("#canSendExt").checked) payload.extended = true;
  let result;
  try {
    result = await api("/can/send", { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
  } catch (err) { result = err; }
  renderExecResult(out, null, result);
};

/* ================= Terminals ================= */
let piTerm, piFit, piWS, adbT, adbFit, adbWS;
const piCapture = LogCapture.register("pi-shell", "Pi shell");
const adbCapture = LogCapture.register("t1-adb", "adb shell (T1)");
const textDecoder = new TextDecoder();
function makeTerm(el) {
  const term = new Terminal({ fontSize: 13, cursorBlink: true, theme: { background: "#000000" } });
  const fit = new FitAddon.FitAddon(); term.loadAddon(fit); term.open(el); fit.fit();
  return [term, fit];
}
function wireTerm(term, fit, path, capture) {
  const ws = new WebSocket(wsURL(path)); ws.binaryType = "arraybuffer";
  ws.onopen = () => { fit.fit(); ws.send("\x00resize:" + term.cols + "," + term.rows); };
  ws.onmessage = (ev) => {
    const isStr = typeof ev.data === "string";
    const text = isStr ? ev.data : new Uint8Array(ev.data);
    term.write(text);
    if (capture) capture.push(isStr ? text : textDecoder.decode(text));
  };
  ws.onclose = () => { term.writeln("\r\n\x1b[90m-- session closed --\x1b[0m"); if (capture) capture.push("\n-- session closed --\n"); };
  // keep the xterm listeners with the socket so a reconnect disposes them (no pile-up)
  ws._subs = [term.onData(d => ws.readyState === 1 && ws.send(d)),
    term.onResize(({ cols, rows }) => ws.readyState === 1 && ws.send("\x00resize:" + cols + "," + rows))];
  return ws;
}
function unwireTerm(ws) {
  if (!ws) return;
  (ws._subs || []).forEach(s => s.dispose());
  ws.onclose = ws.onmessage = null;  // its late onclose must not print into the new session
  ws.close();
}
$("#btnPiShell").onclick = () => {
  if (!piTerm) [piTerm, piFit] = makeTerm($("#piTerm"));
  unwireTerm(piWS); piTerm.clear();
  piWS = wireTerm(piTerm, piFit, "/ws/shell", piCapture); piTerm.focus();
};
$("#btnAdbShell").onclick = () => {
  const serial = $("#adbShellSerial").value;
  if (!serial) { alert("no adb device selected"); return; }
  if (!adbT) [adbT, adbFit] = makeTerm($("#adbTerm"));
  unwireTerm(adbWS); adbT.clear();
  adbWS = wireTerm(adbT, adbFit, "/ws/adb-shell?serial=" + encodeURIComponent(serial), adbCapture); adbT.focus();
};

/* ================= Calibration write + LTZ + 613/614 ================= */
// retry: page-load call (retry until the backend answers); the button calls it plainly
// (an onclick passes the click event, whose missing `retry` reads as false).
async function ltzRef({ retry = false } = {}) {
  const wrap = $("#ltzRefWrap"); wrap.innerHTML = loadingHTML("verifying…");
  try {
    const r = retry
      ? await loadUntilOk(() => api("/cal/ltz-reference", { timeout: INIT_TIMEOUT }),
          (e, d) => wrap.innerHTML = loadingHTML(`couldn't verify (${e.message}) -- retrying in ${d / 1000}s…`, true))
      : await api("/cal/ltz-reference");
    const rows = r.containers.map(c =>
      `<tr><td class="mono">${c.slot}</td><td class="mono">${c.part}</td><td>${c.present ? "yes" : '<span class="tag avoid">missing</span>'}</td><td>${c.match == null ? "-" : (c.match ? '<span class="tag ok">match</span>' : '<span class="tag avoid">MISMATCH</span>')}</td><td class="mono" style="font-size:10px">${(c.sha256 || "").slice(0, 16)}…</td></tr>`).join("");
    wrap.innerHTML = `<p>all_match: <b class="${r.all_match ? "" : ""}">${r.all_match}</b> · dir <span class="mono">${esc(r.dir)}</span> · SPS util ${r.sps_utility.present ? "present" : "missing"}</p>` +
      `<table><tr><th>Slot</th><th>Part#</th><th>Present</th><th>Hash</th><th>SHA-256</th></tr>${rows}</table>`;
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function dev613Test() {
  $("#dev613Out").textContent = "connecting 613/614...";
  try {
    const r = await api("/cal/write/test", { method: "POST" });
    $("#dev613Out").textContent = JSON.stringify(r, null, 2);
  } catch (e) { $("#dev613Out").textContent = "error: " + e; }
}

// Tier-2 plan rendering (shared by the inline flow below and the anchored popover):
// a clean, human-formatted view -- never a raw JSON dump of the plan. token/op/
// evidence/can_id/dlc/data_hex/confirm_how (and the equally-raw uds_payload_hex/
// wire_frame_hex some routines carry) are never shown as visible text; the token is
// still used internally for the execute call. Anything else present on the plan that
// isn't one of those, and isn't itself a nested object/array handled as a special case
// below, is shown as a plain labeled row so this stays generic across actions whose
// plan shape differs (sequence/routine/mode/scope, etc.) rather than only working for
// one action's fields.
const PLAN_HIDDEN_FIELDS = new Set([
  "token", "op", "evidence", "can_id", "dlc", "data_hex", "confirm_how",
  "uds_payload_hex", "wire_frame_hex",
]);
const PLAN_STRUCTURAL_FIELDS = new Set([
  "literal", "expires_in", "will_do", "risk", "min_delay_seconds",
  "entries", "offline_validation", "image_validation",
]);
function planFallbackSummary(plan) {
  // Only the uds-routine plan currently lacks its own will_do.
  if (plan.routine) return `Run routine "${plan.routine}"${plan.rid ? ` (${plan.rid})` : ""} on the ECU.`;
  if (plan.sequence) return `Run CAN sequence "${plan.sequence}".`;
  return "This will make a destructive change.";
}
function renderPlanSummary(plan) {
  const rows = [];
  if (Array.isArray(plan.entries) && plan.entries.length) {
    rows.push(["slots", plan.entries.map(e => `${e.slot}${e.part ? ` (${e.part})` : ""}`).join(", ")]);
  }
  if (plan.image_validation && typeof plan.image_validation === "object") {
    const iv = plan.image_validation;
    rows.push(["image validation", iv.ok === false ? "FAILED" : (iv.ok ? "OK" : "see result after execute")]);
  }
  for (const [k, v] of Object.entries(plan)) {
    if (PLAN_HIDDEN_FIELDS.has(k) || PLAN_STRUCTURAL_FIELDS.has(k)) continue;
    if (v !== null && typeof v === "object") continue;  // never dump a raw object/array as text
    rows.push([k.replace(/_/g, " "), String(v)]);
  }
  const rowsHtml = rows.map(([k, v]) =>
    `<div class="plan-row"><span class="plan-key">${esc(k)}</span><span class="plan-val">${esc(v)}</span></div>`).join("");
  return `<div class="plan-summary">
    <p class="plan-will-do">${esc(plan.will_do || planFallbackSummary(plan))}</p>
    ${plan.risk ? `<p class="plan-risk">${esc(plan.risk)}</p>` : ""}
    ${rowsHtml ? `<div class="plan-rows">${rowsHtml}</div>` : ""}
  </div>`;
}

// Tier-2 execute result: a compact status pill next to the Execute control ("✓ Done" /
// "✗ Failed: <reason>"), never a raw JSON dump by default. The full response stays one
// click away in a collapsed "details" disclosure for debugging. Execute responses differ
// per action, so success is read generically: top-level ok:false, a non-zero exit_code
// (ELK runners), or any UDS step with ok:false (routines) is a failure; an HTTP error is
// a failure via the thrown Error; anything else that came back 2xx is success.
const lastLine = (t) => String(t || "").trim().split("\n").filter(Boolean).pop() || "";
function execOutcome(r) {
  if (!r || typeof r !== "object") return { ok: true, text: "Done" };
  const steps = r.steps && typeof r.steps === "object" ? Object.entries(r.steps) : [];
  const badStep = steps.find(([, v]) => v && v.ok === false);
  const badSlot = Array.isArray(r.slots) ? r.slots.find(x => x && x.ok === false) : null;
  const exitBad = typeof r.exit_code === "number" && r.exit_code !== 0;
  if (r.ok === false || exitBad || badStep) {
    const reason = r.error
      || (badStep && `${badStep[0].replace(/_/g, " ")}: ${badStep[1].nrc_name || badStep[1].error || "negative response"}`)
      || (badSlot && `slot ${badSlot.slot}${badSlot.part ? ` (${badSlot.part})` : ""} failed`)
      || (r.write_ok === false ? "write failed" : r.verify_ok === false ? "verify failed" : "")
      || lastLine(r.stderr)
      || (exitBad ? `exit code ${r.exit_code}` : "see details");
    return { ok: false, text: "Failed: " + reason };
  }
  if (r.status === "running") return { ok: true, text: `Running in background${r.pid ? ` (pid ${r.pid})` : ""}` };
  // an action may name its own one-line outcome (Pi tab: "Connected to X on wlan0 (ip)",
  // "Reboot scheduled in 3 s"); otherwise the generic "Done"
  if (typeof r.summary === "string" && r.summary) return { ok: true, text: r.summary };
  return { ok: true, text: "Done" };
}
// statusEl gets the pill; detailsEl (may be the same element's sibling) gets the
// collapsed full response. `result` is the parsed response, or an Error from api().
function renderExecResult(statusEl, detailsEl, result) {
  const isErr = result instanceof Error;
  const o = isErr ? { ok: false, text: "Failed: " + result.message } : execOutcome(result);
  const short = o.text.length > 140 ? o.text.slice(0, 139) + "…" : o.text;
  statusEl.innerHTML = `<span class="exec-pill ${o.ok ? "ok" : "bad"}" title="${esc(o.text)}">${o.ok ? "✓" : "✗"} ${esc(short)}</span>`;
  if (detailsEl) detailsEl.innerHTML = `<details class="exec-details"><summary>details</summary><pre class="out">${
    esc(isErr ? String(result) : JSON.stringify(result, null, 2))}</pre></details>`;
}
const renderExecPending = (statusEl, detailsEl) => {
  statusEl.innerHTML = `<span class="exec-pill pending">executing…</span>`;
  if (detailsEl) detailsEl.innerHTML = "";
};

// Generic Tier-2 plan->execute flow with literal confirmation + optional cooldown.
// Both Tier-2 helpers take the same optional hooks: execBody() returns extra execute-body
// fields read at the moment Execute is clicked (the Wi-Fi password -- it never goes into
// the plan request), onExecStart() / onExecEnd(result) bracket the execute call.
const execBodyOf = (plan, opts) => JSON.stringify({ token: plan.token, literal: plan.literal,
  ...(opts.execBody ? opts.execBody() : {}) });
async function tier2Flow(outEl, planFn, execPath, { cooldown = 0, ...opts } = {}) {
  outEl.textContent = "planning...";
  let plan;
  try { plan = await planFn(); } catch (e) { outEl.textContent = "plan error: " + e; return; }
  outEl.innerHTML = renderPlanSummary(plan);
  // build step-2 UI
  let step = outEl.nextElementSibling;
  if (step && step.classList && step.classList.contains("danger-step2")) { clearInterval(step._checkTimer); step.remove(); }
  step = document.createElement("div");
  step.className = "danger-step2";
  // No typed-literal input -- the owner found typing a pre-knowable phrase to be pure
  // friction with no real safety value. The plan->token->execute round-trip (the actual
  // safety mechanism: the server only executes a token it itself issued, scoped to this
  // one plan, within its expiry) is unchanged -- this only removes the human-typing step
  // on top of it. The client still sends plan.literal with the execute call, since the
  // server's token check is keyed against it; only the "retype it" UI is gone.
  step.innerHTML = `<div class="exec-row"><button class="danger armed">Execute</button>
    <span class="cooldown" style="color:var(--muted);font-size:12px"></span>
    <span class="exec-status"></span></div>
    <div class="exec-more"></div>`;
  outEl.after(step);
  const btn = step.querySelector("button");
  const cd = step.querySelector(".cooldown");
  const execStatus = step.querySelector(".exec-status"), execMore = step.querySelector(".exec-more");
  let cooling = cooldown;
  if (cooldown) {
    btn.disabled = true;
    cd.textContent = `cooldown ${cooling}s`;
    const timer = setInterval(() => {
      cooling--;
      cd.textContent = cooling > 0 ? `cooldown ${cooling}s` : "cooldown done";
      if (cooling <= 0) { clearInterval(timer); btn.disabled = false; }
    }, 1000);
  }
  btn.onclick = async () => {
    btn.disabled = true; cd.textContent = ""; renderExecPending(execStatus, execMore);
    if (opts.onExecStart) { try { opts.onExecStart(); } catch { /* caller UI only */ } }
    let result;
    try {
      result = await api(execPath, { method: "POST", headers: { "content-type": "application/json" },
        body: execBodyOf(plan, opts) });
    } catch (e) { result = e; }
    renderExecResult(execStatus, execMore, result);
    if (opts.onExecEnd) { try { await opts.onExecEnd(result, execStatus); } catch { /* caller UI only */ } }
  };
}

// Compact anchored Tier-2 confirmation popover -- same plan -> type-the-literal ->
// execute safety gate as tier2Flow above (unchanged), just presented as a small sheet
// anchored to the control that was clicked instead of an inline block that grows the
// card. Used for the engine power-mode / gear-position segmented control so picking a
// mode never visually restructures the page.
let _planPopover = null;
function _popoverEsc(e) { if (e.key === "Escape") closePlanPopover(); }
function _popoverOutside(e) { if (_planPopover && !_planPopover.contains(e.target)) closePlanPopover(); }
function closePlanPopover() {
  if (_planPopover) { _planPopover.remove(); _planPopover = null; }
  document.removeEventListener("keydown", _popoverEsc);
  document.removeEventListener("mousedown", _popoverOutside, true);
}

// Lightweight read-only info popover (the (i) on a sequence row). Positioned like the
// Tier-2 popover but carries only text and dismisses on Escape / outside click.
let _infoPopover = null;
function _infoEsc(e) { if (e.key === "Escape") closeInfoPopover(); }
function _infoOutside(e) { if (_infoPopover && !_infoPopover.contains(e.target)) closeInfoPopover(); }
function closeInfoPopover() {
  if (_infoPopover) { _infoPopover.remove(); _infoPopover = null; }
  document.removeEventListener("keydown", _infoEsc);
  document.removeEventListener("mousedown", _infoOutside, true);
}
function infoPopover(anchor, text) {
  closeInfoPopover();
  const pop = document.createElement("div");
  pop.className = "plan-popover info-popover";
  pop.innerHTML = `<div class="plan-popover-body">${esc(text)}</div>`;
  document.body.appendChild(pop);
  _infoPopover = pop;
  const r = anchor.getBoundingClientRect();
  pop.style.top = `${Math.min(r.bottom + 8, window.innerHeight - 40)}px`;
  pop.style.left = `${r.left}px`;
  requestAnimationFrame(() => {
    const w = pop.offsetWidth, left = parseFloat(pop.style.left);
    if (left + w > window.innerWidth - 12) pop.style.left = `${Math.max(12, window.innerWidth - w - 12)}px`;
  });
  setTimeout(() => {
    document.addEventListener("keydown", _infoEsc);
    document.addEventListener("mousedown", _infoOutside, true);
  }, 0);
}
// HTML variant of the info popover: the card (i) buttons carry trusted static markup
// (code/bold) moved out of the card body, so this sets innerHTML rather than esc-ing.
function infoPopoverHTML(anchor, html) {
  closeInfoPopover();
  const pop = document.createElement("div");
  pop.className = "plan-popover info-popover";
  pop.innerHTML = `<div class="plan-popover-body">${html}</div>`;
  document.body.appendChild(pop);
  _infoPopover = pop;
  const r = anchor.getBoundingClientRect();
  pop.style.top = `${Math.min(r.bottom + 8, window.innerHeight - 40)}px`;
  pop.style.left = `${r.left}px`;
  requestAnimationFrame(() => {
    const w = pop.offsetWidth, left = parseFloat(pop.style.left);
    if (left + w > window.innerWidth - 12) pop.style.left = `${Math.max(12, window.innerWidth - w - 12)}px`;
  });
  setTimeout(() => {
    document.addEventListener("keydown", _infoEsc);
    document.addEventListener("mousedown", _infoOutside, true);
  }, 0);
}
$$(".card-info").forEach(b => b.onclick = (e) => {
  e.stopPropagation();
  const body = b.closest(".card").querySelector(".card-info-body");
  infoPopoverHTML(e.currentTarget, body ? body.innerHTML : "");
});
function tier2Popover(anchorBtn, planFn, execPath, statusEl, opts = {}) {
  closePlanPopover();
  const pop = document.createElement("div");
  pop.className = "plan-popover";
  pop.innerHTML = `<div class="plan-popover-body">planning...</div>`;
  document.body.appendChild(pop);
  _planPopover = pop;
  // position: fixed is already viewport-relative, so these use the bounding rect
  // directly -- no window.scrollX/scrollY offset (that would double-count scroll and
  // push the popover away from the control on a scrolled page).
  const r = anchorBtn.getBoundingClientRect();
  // Re-run after every content change: the plan text arrives async and sets the height.
  // Below the anchor if it fits, else above it; never past the viewport edges.
  const place = () => {
    pop.style.maxHeight = `${window.innerHeight - 24}px`;
    pop.style.overflowY = "auto";
    const w = pop.offsetWidth, h = pop.offsetHeight;
    let top = r.bottom + 8;
    if (top + h > window.innerHeight - 12) top = Math.max(12, Math.min(r.top - h - 8, window.innerHeight - h - 12));
    pop.style.top = `${top}px`;
    pop.style.left = `${Math.max(12, Math.min(r.left, window.innerWidth - w - 12))}px`;
  };
  place();
  setTimeout(() => {  // avoid catching the click that opened this popover
    document.addEventListener("keydown", _popoverEsc);
    document.addEventListener("mousedown", _popoverOutside, true);
  }, 0);

  const body = pop.querySelector(".plan-popover-body");
  (async () => {
    let plan;
    try { plan = await planFn(); }
    catch (e) {
      body.innerHTML = `<p class="plan-risk">plan error: ${esc(String(e))}</p>
        <div class="btnrow"><button type="button" class="plan-cancel">Close</button></div>`;
      body.querySelector(".plan-cancel").onclick = closePlanPopover;
      place();
      return;
    }
    if (_planPopover !== pop) return;  // closed while planning
    // No typed-literal input here either -- see tier2Flow's comment above. The
    // plan->token->execute round-trip is unchanged; only the retype-to-confirm step is gone.
    body.innerHTML = `${renderPlanSummary(plan)}
      <div class="btnrow">
        <button type="button" class="plan-cancel">Cancel</button>
        <button type="button" class="danger armed plan-execute">Execute</button>
        <span class="exec-status"></span>
      </div>
      <div class="exec-more"></div>`;
    place();
    const execBtn = body.querySelector(".plan-execute");
    const execStatus = body.querySelector(".exec-status"), execMore = body.querySelector(".exec-more");
    body.querySelector(".plan-cancel").onclick = closePlanPopover;
    execBtn.onclick = async () => {
      execBtn.disabled = true;
      renderExecPending(execStatus, execMore);
      if (statusEl) renderExecPending(statusEl);
      if (opts.onExecStart) { try { opts.onExecStart(); } catch { /* caller UI only */ } }
      let result;
      try {
        result = await api(execPath, { method: "POST", headers: { "content-type": "application/json" },
          body: execBodyOf(plan, opts) });
      } catch (e) { result = e; }
      if (opts.onExecEnd) { try { await opts.onExecEnd(result); } catch { /* caller UI only */ } }
      renderExecResult(execStatus, execMore, result);
      // the popover is transient: also leave the result (with its own details toggle)
      // in the card's status line under the control, so it survives closing the sheet
      if (statusEl) {
        statusEl.innerHTML = `<div class="exec-status"></div><div class="exec-more"></div>`;
        renderExecResult(statusEl.querySelector(".exec-status"), statusEl.querySelector(".exec-more"), result);
      }
    };
  })();
}

// Upload -> detect slots -> pick -> write (one Tier-2-gated action). The upload (a .zip or
// individual part-number-named module files) is staged; its own bytes decide genuine vs
// modified. "Use stock reference set" stages the pinned stock set for a recovery write.
let _calStage = null;
async function calDetect(useStock) {
  const wrap = $("#calDetectWrap");
  $("#calWritePlanOut").innerHTML = "";
  clearCalStep();
  wrap.innerHTML = loadingHTML(useStock ? "staging stock reference set…" : "staging upload…");
  try {
    const fd = new FormData();
    if (!useStock) {
      const pkg = $("#calWritePackage").files[0];
      const mods = $("#calWriteModules").files;
      if (!pkg && (!mods || !mods.length)) {
        wrap.innerHTML = `<p class="warn">Choose a .zip or one or more module files, or use the stock reference set.</p>`;
        return;
      }
      if (pkg) fd.append("package", pkg);
      for (const m of mods) fd.append("modules", m);
    }
    const r = await api("/cal/write/stage", { method: "POST", body: fd });
    _calStage = r;
    renderCalDetect(r);
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
function clearCalStep() {
  const step = $("#calWritePlanOut").nextElementSibling;
  if (step && step.classList && step.classList.contains("danger-step2")) { clearInterval(step._checkTimer); step.remove(); }
}
function renderCalDetect(r) {
  const wrap = $("#calDetectWrap");
  const rows = r.entries.map(e => `
    <label class="cal-slot-row">
      <input type="checkbox" class="cal-slot-pick" value="${esc(e.slot)}" checked>
      <span class="mono">slot ${esc(e.slot)}</span>
      <span class="mono">${esc(e.part)}</span>
      <span class="tag ${e.genuine ? "ok" : "mixed"}">${e.genuine ? "stock (genuine)" : "modified"}</span>
      <span class="muted">${(e.bytes / 1024).toFixed(1)} KB</span>
    </label>`).join("");
  const unrec = (r.unrecognized || []).length
    ? `<p class="warn">Ignored (not a known GM part number): ${r.unrecognized.map(u => esc(u.filename)).join(", ")}</p>` : "";
  const anyMod = r.entries.some(e => !e.genuine);
  wrap.innerHTML = `
    <p class="hint">${esc(r.source)} — ${r.entries.length} slot(s) detected. Pick which to write${
      anyMod ? ' <b>(modified module present → the write uses the 613/614 VIP override path)</b>' : ""}.</p>
    <div class="cal-slot-list">${rows}</div>
    ${unrec}
    <div class="btnrow" style="margin-top:10px">
      <button type="button" id="btnCalPlan" class="primary">Plan write</button>
      <label class="switch-label" style="margin:0"><input type="checkbox" id="calPickAll" checked> all</label>
      <span class="hint" id="calPickHint"></span>
    </div>`;
  $("#calPickAll").onchange = (e) => $$(".cal-slot-pick").forEach(c => { c.checked = e.target.checked; });
  $("#btnCalPlan").onclick = calPlan;
}
function calPlan() {
  const picks = $$(".cal-slot-pick").filter(c => c.checked).map(c => c.value);
  if (!picks.length) { $("#calPickHint").textContent = "select at least one slot"; return; }
  $("#calPickHint").textContent = "";
  tier2Flow($("#calWritePlanOut"), () =>
    api("/cal/write/plan", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ stage_id: _calStage.stage_id, slots: picks }) }),
    "/cal/write/execute");
}
$("#btnCalDetect").onclick = () => calDetect(false);
$("#btnCalUseStock").onclick = () => calDetect(true);

/* ================= ELK ================= */
async function elkStatus() {
  $("#elkStatusOut").textContent = "probing...";
  try { $("#elkStatusOut").textContent = JSON.stringify(await api("/elk/status"), null, 2); }
  catch (e) { $("#elkStatusOut").textContent = "error: " + e; }
}
async function elkCheck() {
  $("#elkStatusOut").textContent = "checking can0 transport...";
  try { $("#elkStatusOut").textContent = JSON.stringify(await api("/elk/check-transport", { method: "POST" }), null, 2); }
  catch (e) { $("#elkStatusOut").textContent = "error: " + e; }
}
async function elkImages({ retry = false } = {}) {
  try {
    const { images } = retry
      ? await loadUntilOk(() => api("/elk/images", { timeout: INIT_TIMEOUT }))
      : await api("/elk/images");
    $("#elkBootImage").innerHTML = images.map(i => `<option value="${esc(i.name)}">${esc(i.name)} (${i.size} B)</option>`).join("") || "<option value=''>(none uploaded)</option>";
  } catch { /* ignore */ }
}
$("#elkUploadForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#elkUploadOut").textContent = "uploading + validating...";
  try {
    const r = await api("/elk/image/upload", { method: "POST", body: new FormData(e.target) });
    $("#elkUploadOut").textContent = JSON.stringify(r, null, 2);
    elkImages();
  } catch (err) { $("#elkUploadOut").textContent = "error: " + err; }
};
$("#btnElkEnterPlan").onclick = () => tier2Flow($("#elkEnterOut"),
  () => api("/elk/enter/plan", { method: "POST" }), "/elk/enter/execute");
$("#btnElkBootPlan").onclick = () => {
  const image = $("#elkBootImage").value;
  if (!image) { $("#elkBootOut").textContent = "upload an image first"; return; }
  tier2Flow($("#elkBootOut"), () => {
    const fd = new FormData(); fd.append("image", image);
    return api("/elk/boot/plan", { method: "POST", body: fd });
  }, "/elk/boot/execute", { cooldown: 5 });  // mandatory cooldown before a custom-image boot
};

/* ================= Raspberry Pi (the bench host itself) =================
 * Read-only stats poll /api/pi/status every 4 s, only while this tab is open. Every
 * state change (service restart, reboot, Wi-Fi connect/disconnect) is the same Tier-2
 * plan -> token -> execute flow as the rest of the dashboard (tier2Popover / tier2Flow).
 * Self-disruptive actions are scheduled server-side a few seconds out; afterwards this
 * page polls until the restarted unit (or, for a reboot, a new boot id) is back. */
const fmtBytes = (n) => {
  if (n == null) return "?";
  const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n >= 100 || i === 0 ? n.toFixed(0) : n.toFixed(1)} ${u[i]}`;
};
const fmtDur = (s) => {
  if (s == null) return "?";
  const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60);
  return d ? `${d} d ${h} h` : h ? `${h} h ${m} m` : `${m} m ${Math.floor(s % 60)} s`;
};
const meter = (pct) => {
  const p = Math.max(0, Math.min(100, pct || 0));
  const cls = p >= 90 ? "bad" : p >= 75 ? "warn" : "";
  return `<span class="seq-bar meter"><span class="seq-bar-fill ${cls}" style="width:${p}%"></span></span>`;
};
const statePill = (cls, text) => `<span class="state-pill state-${cls}">${esc(text)}</span>`;
const pillOnly = (el, ok, text) => {   // the renderExecResult pill, for a follow-up outcome
  if (el) el.innerHTML = `<span class="exec-pill ${ok === null ? "pending" : ok ? "ok" : "bad"}" title="${esc(text)}">${ok === null ? "" : ok ? "✓ " : "✗ "}${esc(text)}</span>`;
};
let piLast = null, piPoll = null, piBusy = false, piWifiLoaded = false, piSvcRendered = false;

function unitPill(u) {
  const a = u.active || "unknown";
  const cls = a === "active" ? "ok" : (a === "activating" || a === "reloading" || a === "deactivating") ? "zero"
    : a === "failed" ? "error" : "stale";
  return statePill(cls, `${u.unit.replace(/\.service$/, "")}: ${a}${u.sub && u.sub !== "running" && a === "active" ? ` (${u.sub})` : ""}`);
}
function renderPiStatus(s) {
  $("#piIdent").textContent = [s.hostname, s.model, s.kernel].filter(Boolean).join(" · ");
  const c = s.cpu || {}, m = s.memory || {};
  const rows = [];
  rows.push(["CPU", meter(c.percent), `<b>${c.percent ?? "?"}%</b>`,
    `load ${(c.load || []).map(x => x.toFixed(2)).join(" / ") || "?"} · ${c.cores ?? "?"} cores${c.temp_c != null ? ` · ${c.temp_c} °C` : ""}`]);
  rows.push(["Memory", meter(m.percent), `<b>${m.percent ?? "?"}%</b>`,
    `${fmtBytes(m.used)} of ${fmtBytes(m.total)} used · ${fmtBytes(m.available)} available` +
    (m.swap_total ? ` · swap ${fmtBytes(m.swap_used)} / ${fmtBytes(m.swap_total)}` : "")]);
  for (const d of s.disks || []) {
    rows.push([`Disk <span class="mono">${esc(d.mount)}</span>`, meter(d.percent), `<b>${d.percent ?? "?"}%</b>`,
      `${fmtBytes(d.free)} free of ${fmtBytes(d.total)}`]);
  }
  rows.push(["Uptime", "", `<b>${fmtDur(s.uptime_s)}</b>`, `dashboard up ${fmtDur(s.time - s.dashboard.started)}`]);
  $("#piResources").innerHTML = `<div class="group-list">${rows.map(([k, bar, val, sub]) =>
    `<div class="group-row pi-stat"><span class="row-label">${k}</span><span class="pi-meter">${bar}</span>
      <span class="pi-val">${val}</span><span class="row-sub">${sub}</span></div>`).join("")}</div>`;

  const ifRows = (s.interfaces || []).map(i => {
    const up = i.admin_up && (i.operstate === "UP" || (i.operstate === "UNKNOWN" && i.carrier));
    const pill = up ? statePill("ok", "up") : i.admin_up ? statePill("zero", "no link") : statePill("stale", "down");
    const addrs = [...i.ipv4.map(a => `<div class="mono nowrap">${esc(a)}</div>`),
      ...i.ipv6.map(a => `<div class="mono">${esc(a)}</div>`)].join("") || `<span class="muted">—</span>`;
    return `<tr><td class="mono">${esc(i.name)}</td><td>${esc(i.type || "")}</td><td>${pill}</td><td>${addrs}</td>
      <td>${i.connection ? esc(i.connection) : `<span class="muted">${esc(i.nm_state || "")}</span>`}</td></tr>`;
  }).join("");
  $("#piIfaces").innerHTML = `<div class="pi-table-wrap"><table><tr><th>Name</th><th>Type</th><th>State</th><th>Addresses</th><th>NM connection</th></tr>${ifRows}</table></div>`;
  renderPiServices(s.services || []);
}
function renderPiServices(svcs) {
  const wrap = $("#piServices");
  if (!piSvcRendered) {
    // built once (so a pending status pill under a row survives the 4 s refresh);
    // only the unit-state pills are refreshed afterwards
    wrap.innerHTML = svcs.map(t => `<div class="seq-row" data-target="${esc(t.target)}">
      <div class="seq-main"><span class="seq-name">${esc(t.label)}</span>
        <button class="seq-info" data-target="${esc(t.target)}" aria-label="what this restart does" title="what this does">&#9432;</button>
        <span class="pi-units"></span></div>
      <div class="seq-control"><button class="destructive pi-restart" data-target="${esc(t.target)}">Restart&hellip;</button></div>
      <div class="seq-status"><div class="exec-status"></div><div class="exec-more"></div></div>
    </div>`).join("");
    $$("#piServices .seq-info").forEach(b => b.onclick = (e) => {
      e.stopPropagation();
      const t = (piLast.services || []).find(x => x.target === b.dataset.target);
      infoPopover(b, (t && t.desc) || b.dataset.target);
    });
    $$("#piServices .pi-restart").forEach(b => b.onclick = () => piRestart(b.dataset.target, b));
    piSvcRendered = true;
  }
  for (const t of svcs) {
    const row = $(`#piServices .seq-row[data-target="${CSS.escape(t.target)}"] .pi-units`);
    if (row) row.innerHTML = t.units.map(unitPill).join("");
  }
}
async function refreshPiStatus() {
  if (piBusy) return;
  piBusy = true;
  try { piLast = await api("/pi/status", { timeout: 10000 }); renderPiStatus(piLast); }
  catch (e) {
    if (!piLast) $("#piResources").innerHTML = loadingHTML(`couldn't load (${e.message}) -- retrying…`, true);
    else $("#piIdent").innerHTML = `<span style="color:var(--bad)">/api/pi/status unreachable — retrying</span>`;
  } finally { piBusy = false; }
}
function startPiPoll() {
  refreshPiStatus();
  if (!piWifiLoaded) { piWifiLoaded = true; refreshPiWifi(); }
  if (!piPoll) piPoll = setInterval(refreshPiStatus, 4000);
}
function stopPiPoll() { clearInterval(piPoll); piPoll = null; }

// After a scheduled self-restart / reboot: poll until `done(status)` is true, then report.
async function waitForPi(statusEl, done, { what, timeoutS = 120, firstDelayMs = 1500 } = {}) {
  const t0 = Date.now();
  pillOnly(statusEl, null, `waiting for ${what} to come back…`);
  await sleep(firstDelayMs);
  while ((Date.now() - t0) / 1000 < timeoutS) {
    try {
      const s = await api("/pi/status", { timeout: 4000 });
      if (done(s)) {
        piLast = s; renderPiStatus(s);
        pillOnly(statusEl, true, `${what} back up after ${((Date.now() - t0) / 1000).toFixed(1)} s`);
        return true;
      }
    } catch { /* expected while it is down */ }
    pillOnly(statusEl, null, `waiting for ${what} to come back… ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    await sleep(1500);
  }
  pillOnly(statusEl, false, `Failed: ${what} not back after ${timeoutS} s -- check the Pi`);
  return false;
}
const unitSince = (s, unit) => {
  for (const t of (s && s.services) || []) for (const u of t.units) if (u.unit === unit) return u;
  return null;
};

function piRestart(target, btn) {
  const row = $(`#piServices .seq-row[data-target="${CSS.escape(target)}"]`);
  const spec = ((piLast && piLast.services) || []).find(t => t.target === target);
  const unit = spec && spec.units[0].unit;
  let before = null;
  tier2Popover(btn, () => api(`/pi/restart/${target}/plan`, { method: "POST" }),
    `/pi/restart/${target}/execute`, row.querySelector(".seq-status"), {
      onExecStart: () => { before = unitSince(piLast, unit); },
      onExecEnd: (r) => {
        if (r instanceof Error || !r || r.ok === false) return;
        if (r.status === "scheduled") {
          // runs after the popover has written its pill into the row's status line
          setTimeout(() => waitForPi(row.querySelector(".seq-status .exec-status"), (s) => {
            const u = unitSince(s, unit);
            return u && u.active === "active" && (!before || u.since_mono !== before.since_mono);
          }, { what: spec.label, firstDelayMs: 2500 }), 50);
        } else setTimeout(refreshPiStatus, 300);
      } });
}

/* ---- Wi-Fi ---- */
let piWifi = null;
async function refreshPiWifi() {
  try { piWifi = await api("/pi/wifi", { timeout: 15000 }); renderPiWifi(piWifi); }
  catch (e) { $("#piWifiState").innerHTML = loadingHTML(`couldn't read Wi-Fi state (${e.message})`, true); }
}
function renderPiWifi(w) {
  const dev = (w.devices || [])[0];
  let head;
  if (!dev) head = `<p>${statePill("error", "no Wi-Fi device")} NetworkManager reports no Wi-Fi interface.</p>`;
  else {
    const conn = dev.connected
      ? `${statePill("ok", "connected")} <b>${esc(dev.ssid || dev.connection || "?")}</b> on <span class="mono">${esc(dev.device)}</span>${dev.ipv4.length ? ` · <span class="mono">${esc(dev.ipv4.join(", "))}</span>` : ""}`
      : `${statePill("stale", dev.nm_state || "disconnected")} <span class="mono">${esc(dev.device)}</span> is not connected`;
    head = `<div class="btnrow"><span>${conn}</span>
      <span class="muted">radio ${esc(w.radio)}</span>
      ${dev.connected ? `<button type="button" class="destructive" id="btnPiWifiDisc">Disconnect…</button>` : ""}
      <button type="button" id="btnPiWifiRefresh">Refresh</button></div>`;
  }
  $("#piWifiState").innerHTML = head;
  const disc = $("#btnPiWifiDisc");
  if (disc) disc.onclick = () => tier2Popover(disc,
    () => api("/pi/wifi/disconnect/plan", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }),
    "/pi/wifi/disconnect/execute", $("#piWifiOut"), { onExecEnd: () => setTimeout(refreshPiWifi, 300) });
  const rf = $("#btnPiWifiRefresh"); if (rf) rf.onclick = refreshPiWifi;

  $("#piWifiSaved").innerHTML = (w.saved || []).length ? w.saved.map(c => `<div class="seq-row" data-uuid="${esc(c.uuid)}">
      <div class="seq-main"><span class="seq-name">${esc(c.ssid)}</span>
        ${c.name !== c.ssid ? `<span class="muted">profile ${esc(c.name)}</span>` : ""}
        <span class="tag na">${esc(c.security)}</span>
        <span class="tag na">autoconnect ${c.autoconnect ? "on" : "off"}</span>
        ${c.active ? statePill("ok", "active") : ""}</div>
      <div class="seq-control"><button class="pi-wifi-saved" data-uuid="${esc(c.uuid)}" ${c.active ? "disabled title='already connected'" : ""}>Connect…</button></div>
      <div class="seq-status"></div></div>`).join("")
    : `<p class="hint">No saved Wi-Fi networks.</p>`;
  $$("#piWifiSaved .pi-wifi-saved").forEach(b => b.onclick = () => {
    const status = b.closest(".seq-row").querySelector(".seq-status");
    tier2Popover(b, () => api("/pi/wifi/connect/plan", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ uuid: b.dataset.uuid }) }), "/pi/wifi/connect/execute", status,
      { onExecEnd: () => setTimeout(refreshPiWifi, 300) });
  });

  const vis = w.visible || [];
  $("#piWifiVisible").innerHTML = vis.map(v => `<option value="${esc(v.ssid)}">`).join("");
  $("#piWifiVisibleList").innerHTML = vis.length
    ? `<details class="exec-details"><summary>${vis.length} network(s) in the last scan</summary><table>
        <tr><th>SSID</th><th>Signal</th><th>Security</th><th></th></tr>${vis.map(v => `<tr>
        <td>${esc(v.ssid)}${v.in_use ? " " + statePill("ok", "in use") : ""}${v.saved ? ' <span class="tag na">saved</span>' : ""}</td>
        <td><span class="pi-meter">${meter(v.signal)}</span> <span class="mono">${v.signal}</span></td>
        <td>${esc(v.security)}</td>
        <td><button type="button" class="pi-wifi-use" data-ssid="${esc(v.ssid)}">Use</button></td></tr>`).join("")}</table></details>`
    : `<p class="hint">No networks in the cached scan -- press Rescan.</p>`;
  $$("#piWifiVisibleList .pi-wifi-use").forEach(b => b.onclick = () => {
    $("#piWifiSsid").value = b.dataset.ssid; $("#piWifiHidden").checked = false; $("#piWifiPass").focus();
  });
}
$("#piWifiJoin").onsubmit = (e) => {
  e.preventDefault();
  const ssid = $("#piWifiSsid").value;
  if (!ssid) { pillOnly($("#piWifiOut"), false, "Failed: enter or pick a network name"); return; }
  const withPw = $("#piWifiPass").value.length > 0;
  tier2Popover($("#btnPiWifiJoin"),
    () => api("/pi/wifi/connect/plan", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ ssid, hidden: $("#piWifiHidden").checked, with_password: withPw }) }),
    "/pi/wifi/connect/execute", $("#piWifiOut"), {
      // the password is read only now, sent only in this execute body, then cleared from
      // the field; it never goes into the plan request, a URL, a log or a response
      execBody: () => {
        const pw = $("#piWifiPass").value;
        $("#piWifiPass").value = "";
        return pw ? { password: pw } : {};
      },
      onExecEnd: () => setTimeout(refreshPiWifi, 300) });
};
$("#btnPiWifiRescan").onclick = async () => {
  const b = $("#btnPiWifiRescan"), out = $("#piWifiRescanOut");
  b.disabled = true; out.innerHTML = `<span class="exec-pill pending">scanning…</span>`;
  let r;
  try { r = await api("/pi/wifi/rescan", { method: "POST" }); } catch (e) { r = e; }
  renderExecResult(out, null, r);
  b.disabled = false;
  await refreshPiWifi();
};

/* ---- reboot (danger zone) ---- */
$("#btnPiRebootPlan").onclick = () => {
  const bootBefore = piLast && piLast.boot_id;
  tier2Flow($("#piRebootOut"), () => api("/pi/reboot/plan", { method: "POST" }), "/pi/reboot/execute", {
    onExecEnd: (r, statusEl) => {
      if (r instanceof Error || !r || r.ok === false) return;
      const prev = r.previous_boot_id || bootBefore;
      return waitForPi(statusEl, (s) => s.boot_id && s.boot_id !== prev,
        { what: "the Pi", timeoutS: 300, firstDelayMs: 8000 });
    } });
};

/* ================= Field capture (raw T1 + CAN + UART to USB) =================
 * Polls /api/capture/status every 2 s while this tab is open (the backend's own monitor
 * runs regardless). Start is the Tier-2 popover like every other action that opens raw
 * sockets / runs sudo; Stop and Unmount are plain actions (they only end and flush). */
let capPoll = null, capBusy = false, capLast = null, capSelVol = null, capPickBuilt = false;
const capKeys = () => $$("#capStreamPick input:checked").map(i => i.value);
const CAP_STATE = { capturing: "ok", restarting: "zero", stopping: "zero", pending: "stale",
  stopped: "stale", failed: "error", killed: "error" };
function capVolName(v) {
  const d = v.disk || {};
  return `${v.label || v.name}${(d.vendor || d.model) ? ` — ${[d.vendor, d.model].filter(Boolean).join(" ")}` : ""}`;
}
function renderCapture(s) {
  capLast = s;
  const sess = s.session, active = !!(sess && sess.active);
  // ---- safe-to-unplug banner ----
  const safe = s.safe_to_unplug || {};
  let cls, head;
  if (active) { cls = "rec"; head = "Recording — do NOT unplug the drive"; }
  else if (sess && sess.state === "stopping") { cls = "no"; head = "Stopping — flushing files…"; }
  else if (safe.safe === true) { cls = "yes"; head = "Safe to unplug"; }
  else if (safe.safe === false) { cls = "no"; head = "Not safe to unplug yet"; }
  else { cls = ""; head = "No USB drive"; }
  $("#capSafe").innerHTML = `<div class="cap-safe ${cls}"><span class="cap-dot"></span>
    <div>${esc(head)}<small>${esc(active ? `session ${sess.id} on ${sess.mountpoint}` : safe.reason || "")}</small></div></div>`;

  // ---- stream picker (built once) ----
  if (!capPickBuilt) {
    $("#capStreamPick").innerHTML = (s.streams || []).map(x =>
      `<label><input type="checkbox" value="${esc(x.key)}" checked> ${esc(x.label)}</label>`).join("");
    capPickBuilt = true;
  }
  $$("#capStreamPick input").forEach(i => i.disabled = active);

  // ---- volumes ----
  const vols = s.volumes || [];
  const usable = vols.filter(v => v.supported || v.mountpoint);
  if (!vols.find(v => v.id === capSelVol)) capSelVol = usable.length === 1 ? usable[0].id : null;
  if (active) capSelVol = sess.volume.id;
  $("#capVolumes").innerHTML = s.volumes_error ? loadingHTML(`couldn't list drives: ${s.volumes_error}`, true)
    : !vols.length ? `<p class="hint">No USB drive detected. Plug one in (FAT32, exFAT, NTFS or ext4); it appears here within a couple of seconds.</p>`
    : vols.map(v => {
      const used = v.total ? 100 * (1 - v.free / v.total) : null;
      const mnt = v.mountpoint
        ? `${statePill(v.ours ? "ok" : "zero", v.ours ? "mounted" : "mounted (not by the dashboard)")} <span class="mono">${esc(v.mountpoint)}</span>
           ${v.total ? `<span class="pi-meter">${meter(used)}</span> <span class="muted">${fmtBytes(v.free)} free of ${fmtBytes(v.total)}</span>` : ""}`
        : statePill("stale", "not mounted");
      const sel = v.id === capSelVol;
      return `<div class="seq-row cap-vol${sel ? " selected" : ""}" data-vol="${esc(v.id)}">
        <div class="seq-main"><input type="radio" name="capVol" ${sel ? "checked" : ""} ${active || !(v.supported || v.mountpoint) ? "disabled" : ""}>
          <span class="seq-name">${esc(capVolName(v))}</span>
          <span class="tag ${v.supported ? "na" : "avoid"}">${esc(v.fstype || "no filesystem")}${v.supported ? "" : " (unsupported)"}</span>
          <span class="muted mono">${esc(v.path)} · ${fmtBytes(v.size)}</span></div>
        <div class="seq-control">${v.mountpoint && !active ? `<button type="button" class="cap-unmount" data-vol="${esc(v.id)}">Unmount</button>` : ""}</div>
        <div class="seq-status">${mnt}</div></div>`;
    }).join("");
  $$("#capVolumes .cap-vol").forEach(r => r.onclick = (e) => {
    if (active || e.target.closest("button")) return;
    const v = vols.find(x => x.id === r.dataset.vol);
    if (v && (v.supported || v.mountpoint)) { capSelVol = v.id; renderCapture(capLast); }
  });
  $$("#capVolumes .cap-unmount").forEach(b => b.onclick = async (e) => {
    e.stopPropagation(); b.disabled = true; pillOnly($("#capOut"), null, "unmounting…");
    let r; try { r = await api("/capture/unmount", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ volume: b.dataset.vol }) }); } catch (err) { r = err; }
    renderExecResult($("#capOut"), null, r); refreshCapture();
  });

  // ---- buttons ----
  $("#btnCapStart").disabled = active || !vols.length;
  $("#btnCapStart").title = !vols.length ? "plug in a USB drive first" : active ? "a session is running" : "";
  $("#btnCapStop").disabled = !active;
  $("#btnCapStop").className = active ? "primary" : "";

  // ---- session / streams / events ----
  const show = sess || s.last;
  if (!show) { $("#capSession").innerHTML = ""; $("#capStreamsWhich").textContent = ""; $("#capEvents").textContent = ""; return; }
  const dur = ((show.stopped || s.time) - show.started);
  const used = show.total ? 100 * (1 - show.free / show.total) : null;
  $("#capSession").innerHTML = `<div class="group-list">
    <div class="group-row"><span class="row-label">${sess ? "Current session" : "Last session"}</span>
      <span>${statePill(show.state === "capturing" ? "ok" : show.state === "aborted" ? "error" : "stale", show.state)}
      <span class="mono">${esc(show.id)}</span> · ${fmtDur(dur)}</span></div>
    <div class="group-row"><span class="row-label">Folder</span><span class="mono">${esc(show.dir)}</span></div>
    ${show.total ? `<div class="group-row"><span class="row-label">Drive space</span><span><span class="pi-meter">${meter(used)}</span>
      ${fmtBytes(show.free)} free of ${fmtBytes(show.total)}${show.low_space ? " " + statePill("zero", "low") : ""}</span></div>` : ""}
    ${show.end_reason ? `<div class="group-row"><span class="row-label">Ended</span><span>${esc(show.end_reason)}${
      show.unmount ? ` · unmount ${show.unmount.ok ? "ok" : "FAILED: " + esc(show.unmount.error || "")}` : ""}</span></div>` : ""}
  </div>`;
  $("#capStreamsWhich").textContent = sess ? `(session ${show.id}, live)` : `(last session ${show.id})`;
  $("#capStreams").innerHTML = `<table><tr><th>Stream</th><th>State</th><th>Current file</th><th>Size</th><th>Rate</th><th>Segments</th><th>Restarts</th><th>Last error</th></tr>${
    (show.streams || []).map(x => `<tr><td>${esc(x.label)}</td><td>${statePill(CAP_STATE[x.state] || "stale", x.state)}</td>
      <td class="mono">${esc(x.file || "—")}</td><td class="mono nowrap">${fmtBytes(x.bytes)}</td>
      <td class="mono nowrap">${x.rate_bps ? fmtBytes(x.rate_bps) + "/s" : "—"}</td><td>${x.segments}</td><td>${x.restarts}</td>
      <td>${x.last_error ? `<span style="color:var(--bad)">${esc(x.last_error)}</span>` : (x.dropped_bytes ? `<span class="muted">${x.dropped_bytes} B dropped</span>` : "")}</td></tr>`).join("")}</table>`;
  $("#capEvents").textContent = (show.events || []).slice().reverse().join("\n");
}
async function refreshCapture() {
  if (capBusy) return;
  capBusy = true;
  try { renderCapture(await api("/capture/status", { timeout: 10000 })); }
  catch (e) { $("#capSafe").innerHTML = loadingHTML(`/api/capture/status unreachable (${e.message}) -- retrying…`, true); }
  finally { capBusy = false; }
}
function startCapPoll() { refreshCapture(); if (!capPoll) capPoll = setInterval(refreshCapture, 2000); }
function stopCapPoll() { clearInterval(capPoll); capPoll = null; }
$("#btnCapStart").onclick = () => {
  const streams = capKeys();
  if (!streams.length) { pillOnly($("#capOut"), false, "Failed: pick at least one stream"); return; }
  // inline plan -> Execute (tier2Flow, like the Pi reboot): this plan is longer than the
  // anchored popover comfortably fits on a small in-car screen
  tier2Flow($("#capOut"), () => api("/capture/start/plan", { method: "POST",
    headers: { "content-type": "application/json" }, body: JSON.stringify({ volume: capSelVol, streams }) }),
    "/capture/start/execute", { onExecEnd: () => setTimeout(refreshCapture, 300) });
};
$("#btnCapStop").onclick = async () => {
  const b = $("#btnCapStop"); b.disabled = true;
  const step = $("#capOut").nextElementSibling;   // a leftover start plan/Execute block
  if (step && step.classList.contains("danger-step2")) step.remove();
  pillOnly($("#capOut"), null, "stopping: closing files, syncing, unmounting…");
  let r; try { r = await api("/capture/stop", { method: "POST" }); } catch (e) { r = e; }
  $("#capOut").innerHTML = `<div class="exec-status"></div><div class="exec-more"></div>`;
  renderExecResult($("#capOut .exec-status"), $("#capOut .exec-more"), r);
  refreshCapture();
};

/* ================= boot ================= */
$("#btnReadSafe").onclick = readSafe;
$("#btnReadCal").onclick = readCal;
$("#btnReadDtc").onclick = readDtc;
$("#btnUnlock").onclick = unlock;
$("#btnSlotMap").onclick = loadSlotMap;
$("#btnLtzRef").onclick = ltzRef;
$("#btn613Test").onclick = dev613Test;
$("#btnElkStatus").onclick = elkStatus;
$("#btnElkCheck").onclick = elkCheck;
$("#btnExportLogs").onclick = exportCapturedLogsAsTar;
// Each section boots independently: a synchronous throw in one (e.g. chart.umd.min.js
// failed to load) must not stop the others, and every page-load read retries on its own
// (loadUntilOk) behind a visible loading placeholder from index.html.
function boot(name, fn) {
  try { const p = fn(); if (p && p.catch) p.catch(e => console.error(`boot ${name}:`, e)); }
  catch (e) { console.error(`boot ${name}:`, e); }
}
// /api/status already went out first (above). Then the CAN tab, which is what is on
// screen; reads for the hidden tabs follow a beat later so they don't compete with it for
// the browser's 6 per-host connections.
boot("can chart", initCanCharts);
boot("can ws", startCanWS);
boot("can decode", startCanDecodePoll);  // CAN is the default tab, so start its poll now
boot("power modes", loadVehiclePowerModes);
boot("pm repeat", () => $$("#pmRepeat button[data-repeat]").forEach(b => b.onclick = () => setPmRepeat(+b.dataset.repeat)));
boot("gear positions", loadVehicleGearPositions);
boot("doors", loadVehicleDoors);
boot("steering controls", loadSteeringControls);
boot("sequences", loadSequences);
boot("sequence poll", startSeqPoll);
setTimeout(() => {
  boot("adb", refreshAdb);
  boot("adb poll", startAdbPoll);
  boot("meta", () => loadUntilOk(() => api("/meta", { timeout: INIT_TIMEOUT }))
    .then(m => $("#diagEndpoint").textContent = `${m.uds.endpoint} · tester ${m.uds.tester} · ecu ${m.uds.ecu} · ${m.uds.vlan}`));
  boot("routines", loadRoutines);
  boot("ltz reference", () => ltzRef({ retry: true }));
  boot("elk images", () => elkImages({ retry: true }));
}, 300);
