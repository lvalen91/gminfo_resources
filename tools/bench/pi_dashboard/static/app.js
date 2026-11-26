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
  if (b.dataset.tab === "t1") refreshT1();
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
    parts.push(ind("ka", "keepalive", can.keepalive_active ? "ok" : "bad", "0x529 sender (systemd)"));
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
// A sequence is one of two UI shapes, decided by the backend `kind` (sequences.py):
//   continuous (full, startup-keepalive) -> an ON/OFF toggle; the run transmits until
//     stopped (SIGTERM via /can/sequence/stop).
//   one-shot (startup, vip-reset, keepalive-start/stop) -> a RUN control with a live
//     progress/elapsed readout; the process exits on its own. `duration_s` (when the code
//     knows it) drives a determinate bar; otherwise an indeterminate spinner + elapsed.
// While a one-shot is mid-run every row greys out (one-shots own the bus exclusively, so
// a continuous schedule is itself stopped by the backend's exclusive_bus takeover).
let _seqSpecs = [];
let _seqBusyOneshot = false;
const seqRow = (name) => $(`#seqList .seq-row[data-seq="${CSS.escape(name)}"]`);
const seqIsContinuous = (s) => s.kind === "continuous";

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
  $("#seqList").innerHTML = sequences.map(s => {
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
      <div class="seq-status"><div class="exec-status"></div><div class="exec-more"></div></div>
    </div>`;
  }).join("");
  $$("#seqList .seq-info").forEach(b => b.onclick = (e) => {
    e.stopPropagation();
    const s = _seqSpecs.find(x => x.name === b.dataset.seq);
    infoPopover(b, (s && s.desc) || b.dataset.seq);
  });
  $$("#seqList .seq-run").forEach(b => b.onclick = () => {
    const s = _seqSpecs.find(x => x.name === b.dataset.seq);
    if (s.destructive && !$("#seqDryRun").checked) runSeqDestructive(s, b);
    else runSeqOneshot(s);
  });
  $$("#seqList .seq-switch").forEach(c => c.onchange = () => {
    const s = _seqSpecs.find(x => x.name === c.dataset.seq);
    toggleContinuous(s, c);
  });
}
// Reflect which continuous sequence (if any) is running, and the global one-shot lock.
function applyContinuous(continuous) {
  const running = continuous && continuous.running ? continuous.sequence : null;
  $$("#seqList .seq-switch").forEach(c => {
    const on = c.dataset.seq === running;
    c.checked = on;
    const row = c.closest(".seq-row");
    row.classList.toggle("seq-on", on);
    const txt = row.querySelector(".seq-toggle-txt");
    if (txt) txt.textContent = on ? "ON" : "OFF";
  });
  updateSeqLock();
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
  const dry = $("#seqDryRun").checked;
  _seqBusyOneshot = true; updateSeqLock();
  const row = seqRow(s.name);
  const status = row.querySelector(".exec-status"), more = row.querySelector(".exec-more");
  renderExecPending(status, more);
  const stop = startSeqProgress(s.name, dry ? 0 : s.duration_s);
  let result;
  try {
    result = await api("/can/sequence/" + s.name, { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: dry }) });
  } catch (e) { result = e; }
  stop();
  renderExecResult(status, more, result);
  _seqBusyOneshot = false; updateSeqLock();
  await refreshContinuous();  // a one-shot may have stopped a running continuous (exclusive bus)
}
function runSeqDestructive(s, btn) {
  // Destructive one-shot (vip-reset): keep the Tier-2 plan->execute confirm; drive the row
  // lock + progress ring around the execute via the popover's exec hooks.
  let stop;
  tier2Popover(btn,
    () => api("/can/sequence/" + s.name + "/plan", { method: "POST" }),
    "/can/sequence/" + s.name + "/execute",
    seqRow(s.name).querySelector(".seq-status"),
    { onExecStart: () => { _seqBusyOneshot = true; updateSeqLock(); stop = startSeqProgress(s.name, s.duration_s); },
      onExecEnd: async () => { if (stop) stop(); _seqBusyOneshot = false; updateSeqLock(); await refreshContinuous(); } });
}
async function toggleContinuous(s, cb) {
  if (_seqBusyOneshot) { cb.checked = !cb.checked; return; }
  const dry = $("#seqDryRun").checked;
  const row = seqRow(s.name);
  const status = row.querySelector(".exec-status"), more = row.querySelector(".exec-more");
  const turningOn = cb.checked;
  if (turningOn && s.destructive && !dry) {
    // A destructive continuous keeps the confirm gate; don't latch until confirmed.
    cb.checked = false;
    runSeqDestructive(s, cb.closest(".seq-toggle"));
    return;
  }
  cb.disabled = true;
  renderExecPending(status, more);
  let result;
  try {
    result = turningOn
      ? await api("/can/sequence/" + s.name, { method: "POST",
          headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: dry }) })
      : await api("/can/sequence/stop", { method: "POST" });
  } catch (e) { result = e; }
  renderExecResult(status, more, result);
  cb.disabled = false;
  await refreshContinuous();  // reflect the real running state (dry-run ON never actually starts)
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
      // Anchored popover (see tier2Popover above), not the inline tier2Flow: picking a
      // mode must stay a simple, compact control -- it must not expand the card into a
      // new page area. The plan->type-the-literal->execute Tier-2 gate is identical.
      b.onclick = () => tier2Popover(b,
        () => api(`/vehicle/power-mode/${b.dataset.mode}/plan`, { method: "POST" }),
        `/vehicle/power-mode/${b.dataset.mode}/execute`,
        $("#vehicleOut"));
    });
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function loadVehicleGearPositions() {
  const wrap = $("#vehicleGearPositions");
  try {
    const { positions } = await loadUntilOk(() => api("/vehicle/gear-positions", { timeout: INIT_TIMEOUT }),
      (e, d) => wrap.innerHTML = `<span class="seg-loading">${loadingHTML(`couldn't load (${e.message}) -- retrying in ${d / 1000}s…`, true)}</span>`);
    wrap.innerHTML = positions.map(p =>
      `<button class="seg-btn" disabled title="${esc('No verified CAN signal -- scaffold only: ' + p.reason)}">${esc(p.label)} — unverified</button>`).join("");
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}

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
    $("#adbDevices").innerHTML = devices.length ? `<table><tr><th>Serial</th><th>State</th><th>Transport</th><th>Product</th></tr>` +
      devices.map(d => `<tr><td class="mono">${esc(d.serial)}</td><td>${esc(d.state)}</td><td><span class="tag ${d.transport === 'usb' ? 'ok' : 'mixed'}">${esc(d.transport)}</span></td><td>${esc(d.product || "")}</td></tr>`).join("") + "</table>"
      : "<p>no devices</p>";
    const opts = devices.map(d => `<option value="${esc(d.serial)}">${esc(d.serial)} (${esc(d.transport)})</option>`).join("");
    // Preserve the current selection across a refresh (e.g. re-polling while a
    // terminal is already open against one serial shouldn't silently reselect another).
    const prevApk = $("#apkSerial").value, prevShell = $("#adbShellSerial").value;
    $("#apkSerial").innerHTML = opts; $("#adbShellSerial").innerHTML = opts;
    if (devices.some(d => d.serial === prevApk)) $("#apkSerial").value = prevApk;
    if (devices.some(d => d.serial === prevShell)) $("#adbShellSerial").value = prevShell;
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
$("#btnRefreshT1").onclick = refreshT1;
$("#apkForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#apkOut").textContent = "uploading + installing (may take a while)...";
  try {
    const r = await api("/adb/install", { method: "POST", body: new FormData(e.target) });
    $("#apkOut").textContent = JSON.stringify(r, null, 2);
  } catch (err) { $("#apkOut").textContent = "error: " + err; }
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
async function tier2Flow(outEl, planFn, execPath, { cooldown = 0 } = {}) {
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
    try {
      const r = await api(execPath, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ token: plan.token, literal: plan.literal }) });
      renderExecResult(execStatus, execMore, r);
    } catch (e) { renderExecResult(execStatus, execMore, e); }
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
  pop.style.top = `${Math.min(r.bottom + 8, window.innerHeight - 40)}px`;
  pop.style.left = `${r.left}px`;
  requestAnimationFrame(() => {  // clamp to viewport once it has a real width
    const w = pop.offsetWidth, left = parseFloat(pop.style.left);
    if (left + w > window.innerWidth - 12) pop.style.left = `${Math.max(12, window.innerWidth - w - 12)}px`;
  });
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
          body: JSON.stringify({ token: plan.token, literal: plan.literal }) });
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
boot("power modes", loadVehiclePowerModes);
boot("gear positions", loadVehicleGearPositions);
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
