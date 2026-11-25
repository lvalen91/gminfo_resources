"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const wsURL = (p) => (location.protocol === "https:" ? "wss://" : "ws://") + location.host + p;
async function api(path, opts) {
  const r = await fetch("/api" + path, opts);
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
setInterval(() => $("#clock").textContent = new Date().toLocaleTimeString(), 1000);

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
async function refreshStatus() {
  if (statusBusy) return;  // /api/status can take longer than the poll interval
  statusBusy = true;
  try {
    const s = await api("/status");
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
  } catch (e) { $("#indicators").innerHTML = ind("err", "backend", "bad", String(e)); }
  finally { statusBusy = false; }
}
refreshStatus(); setInterval(refreshStatus, 4000);

/* ================= CAN ================= */
// Pull the live theme colors (light/dark follows prefers-color-scheme in style.css) so
// the two canvases aren't hardcoded to one theme.
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let idChart;
function initCanCharts() {
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
function startCanWS() {
  const log = $("#canLog"); let lines = [];
  const ws = new WebSocket(wsURL("/ws/can"));
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "frame") {
      const f = m.data;
      const line = `${f.t.toFixed(3)}  ${f.id.padEnd(4)} [${f.dlc}] ${f.data}`;
      lines.unshift(line);
      if (lines.length > 200) lines.pop();
      log.textContent = lines.join("\n");
      canCapture.push(line + "\n");
    } else if (m.type === "stats") {
      const s = m.data;
      idChart.data.labels = s.top_ids.map(x => x.id);
      idChart.data.datasets[0].data = s.top_ids.map(x => x.count);
      idChart.update();
      $("#canStatRow").innerHTML =
        `<span>errors <b>${s.errors}</b></span>` +
        `<span>unique IDs <b>${s.unique_ids}</b></span><span>total <b>${s.total}</b></span>` +
        (s.last_error ? `<span style="color:var(--bad)">${esc(s.last_error)}</span>` : "");
    }
  };
  ws.onclose = () => {
    // say so, instead of leaving the last stats/frames on screen looking live
    $("#canStatRow").innerHTML = `<span style="color:var(--bad)">/ws/can disconnected, reconnecting...</span>`;
    setTimeout(startCanWS, 2000);
  };
}
async function loadSequences() {
  let sequences, continuous;
  try { ({ sequences, continuous } = await api("/can/sequences")); }
  catch (e) { $("#seqButtons").textContent = "error loading sequences: " + e; return; }
  $("#seqButtons").innerHTML = sequences.map(s =>
    `<button class="${s.destructive ? "destructive" : ""}" data-seq="${s.name}" title="${esc(s.desc)}">${esc(s.name)}${s.destructive ? " ⚠" : ""}</button>`).join("");
  $$("#seqButtons button").forEach(b => b.onclick = () => runSeq(b.dataset.seq, sequences.find(s => s.name === b.dataset.seq)));
  showContinuous(continuous);
}
function showContinuous(continuous) {
  const row = $("#seqContinuousRow");
  if (continuous && continuous.running) {
    row.style.display = "";
    $("#seqContinuousStatus").textContent = `running: ${continuous.sequence} (${continuous.mode}, pid ${continuous.pid})`;
  } else {
    row.style.display = "none";
  }
}
let _seqPoll = null;
function startSeqPoll() {
  if (_seqPoll) return;
  // Only while something may be running: a cheap poll of the lightweight /sequences
  // endpoint so the Stop button/status appears even if it was started by another
  // client (the API, a CLI run, a previous session) rather than this tab's own click.
  _seqPoll = setInterval(async () => {
    try { const { continuous } = await api("/can/sequences"); showContinuous(continuous); }
    catch (e) { /* transient; next poll retries */ }
  }, 3000);
}
$("#btnSeqStop").onclick = async () => {
  $("#btnSeqStop").disabled = true;
  try {
    const r = await api("/can/sequence/stop", { method: "POST" });
    $("#seqOut").textContent = JSON.stringify(r, null, 2);
    showContinuous({ running: false });
  } catch (e) { $("#seqOut").textContent = "stop error: " + e; }
  finally { $("#btnSeqStop").disabled = false; }
};
async function runSeq(name, spec) {
  const dry = $("#seqDryRun").checked;
  // Destructive + live: go through the Tier-2 plan->execute token flow (server-gated),
  // identical to calibration-write / ELK. The plain POST only handles dry-runs now.
  if (!dry && spec.destructive) {
    tier2Flow($("#seqOut"),
      () => api("/can/sequence/" + name + "/plan", { method: "POST" }),
      "/can/sequence/" + name + "/execute");
    return;
  }
  $("#seqOut").textContent = `running ${name} (dry_run=${dry})...`;
  try {
    const r = await api("/can/sequence/" + name, { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify({ dry_run: dry }) });
    // Headline the outcome: a failed live run (e.g. exit_code 3 "transmit queue stayed
    // full") must not look like a successful one buried in a JSON blob.
    const head = r.ok === false ? `FAILED ${name}: ${r.error || "exit_code=" + r.exit_code}`
      : r.dry_run ? `DRY RUN ${name}: validated, zero frames sent (untick dry-run to transmit)`
      : r.status === "running" ? `RUNNING ${name} (pid ${r.pid}) in the background`
      : `OK ${name}`;
    $("#seqOut").textContent = head + "\n\n" + JSON.stringify(r, null, 2);
    $("#seqOut").style.color = r.ok === false ? "var(--bad)" : "";
    // Show the Stop control immediately on a successful continuous start, instead of
    // waiting up to 3s for the next poll.
    if (r.ok && r.status === "running") showContinuous({ running: true, sequence: name, mode: r.mode, pid: r.pid });
    else if (!dry) showContinuous({ running: false });
  } catch (e) { $("#seqOut").textContent = "error: " + e; $("#seqOut").style.color = "var(--bad)"; }
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
    const { modes } = await api("/vehicle/power-modes");
    wrap.innerHTML = modes.map(m => {
      const title = m.verified ? esc(m.evidence) : esc("No verified CAN signal -- scaffold only: " + m.reason);
      return `<button class="seg-btn" data-mode="${esc(m.name)}" ${m.verified ? "" : "disabled"} title="${title}">${esc(m.label)}${m.verified ? "" : " — unverified"}</button>`;
    }).join("");
    $$("#vehiclePowerModes button[data-mode]").forEach(b => {
      if (b.disabled) return;
      b.onclick = () => tier2Flow($("#vehicleOut"),
        () => api(`/vehicle/power-mode/${b.dataset.mode}/plan`, { method: "POST" }),
        `/vehicle/power-mode/${b.dataset.mode}/execute`);
    });
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function loadVehicleGearPositions() {
  const wrap = $("#vehicleGearPositions");
  try {
    const { positions } = await api("/vehicle/gear-positions");
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
  try { ({ routines } = await api("/uds/routines")); }
  catch (e) { $("#routineButtons").textContent = "error loading routines: " + e; return; }
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
$("#calValidateForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#calValidateOut").textContent = "validating offline...";
  try {
    const r = await api("/cal/validate", { method: "POST", body: new FormData(e.target) });
    $("#calValidateOut").textContent = JSON.stringify(r, null, 2);
  } catch (err) { $("#calValidateOut").textContent = "error: " + err; }
};

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
async function ltzRef() {
  const wrap = $("#ltzRefWrap"); wrap.innerHTML = "verifying...";
  try {
    const r = await api("/cal/ltz-reference");
    const rows = r.containers.map(c =>
      `<tr><td class="mono">${c.slot}</td><td class="mono">${c.part}</td><td>${c.present ? "yes" : '<span class="tag avoid">missing</span>'}</td><td>${c.match == null ? "-" : (c.match ? '<span class="tag ok">match</span>' : '<span class="tag avoid">MISMATCH</span>')}</td><td class="mono" style="font-size:10px">${(c.sha256 || "").slice(0, 16)}…</td></tr>`).join("");
    wrap.innerHTML = `<p>all_match: <b class="${r.all_match ? "" : ""}">${r.all_match}</b> · dir <span class="mono">${esc(r.dir)}</span> · SPS util ${r.sps_utility.present ? "present" : "missing"}</p>` +
      `<table><tr><th>Slot</th><th>Part#</th><th>Present</th><th>Hash</th><th>SHA-256</th></tr>${rows}</table>`;
    // populate the single write form's slot select from the verified stock set
    const parts = r.containers.filter(c => c.present);
    $("#calWriteSlot").innerHTML = parts.map(c => `<option value="${c.slot}">${c.slot} (part ${c.part})</option>`).join("");
  } catch (e) { wrap.innerHTML = "error: " + esc(String(e)); }
}
async function dev613Test() {
  $("#dev613Out").textContent = "connecting 613/614...";
  try {
    const r = await api("/cal/write/test", { method: "POST" });
    $("#dev613Out").textContent = JSON.stringify(r, null, 2);
  } catch (e) { $("#dev613Out").textContent = "error: " + e; }
}

// Generic Tier-2 plan->execute flow with literal confirmation + optional cooldown.
async function tier2Flow(outEl, planFn, execPath, { cooldown = 0 } = {}) {
  outEl.textContent = "planning...";
  let plan;
  try { plan = await planFn(); } catch (e) { outEl.textContent = "plan error: " + e; return; }
  outEl.textContent = JSON.stringify(plan, null, 2);
  // build step-2 UI
  let step = outEl.nextElementSibling;
  if (step && step.classList && step.classList.contains("danger-step2")) { clearInterval(step._checkTimer); step.remove(); }
  step = document.createElement("div");
  step.className = "danger-step2";
  step.innerHTML = `<label>2. Type confirmation <code>${esc(plan.literal)}</code>:
    <input type="text" autocomplete="off" placeholder="${esc(plan.literal)}"></label>
    <button class="danger" disabled>Execute</button>
    <span class="cooldown" style="color:var(--muted);font-size:12px"></span>
    <pre class="out execout"></pre>`;
  outEl.after(step);
  const input = step.querySelector("input"), btn = step.querySelector("button");
  const cd = step.querySelector(".cooldown"), execout = step.querySelector(".execout");
  let cooling = cooldown;
  if (cooldown) {
    cd.textContent = `cooldown ${cooling}s`;
    const timer = setInterval(() => { cooling--; cd.textContent = cooling > 0 ? `cooldown ${cooling}s` : "cooldown done"; if (cooling <= 0) clearInterval(timer); }, 1000);
  }
  const check = () => { btn.disabled = !(input.value === plan.literal && cooling <= 0); btn.classList.toggle("armed", !btn.disabled); };
  input.oninput = check; step._checkTimer = setInterval(check, 500);  // cleared on re-plan
  btn.onclick = async () => {
    btn.disabled = true; execout.textContent = "executing...";
    try {
      const r = await api(execPath, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ token: plan.token, literal: input.value }) });
      execout.textContent = JSON.stringify(r, null, 2);
    } catch (e) { execout.textContent = "execute error: " + e; }
  };
}

// One flow: scope = individual slot | full package. Bytes are the verified stock set, or
// a verified-stock .zip if one is attached. There is no custom-calibration option.
const calScopeSel = $("#calWriteScope");
const syncCalScope = () => { $("#calWriteSlotLabel").style.display = calScopeSel.value === "package" ? "none" : ""; };
calScopeSel.onchange = syncCalScope; syncCalScope();
$("#btnCalWritePlan").onclick = () => {
  const scope = calScopeSel.value, slot = $("#calWriteSlot").value;
  const pkg = $("#calWritePackage").files[0];
  tier2Flow($("#calWriteOut"), () => {
    const fd = new FormData();
    fd.append("scope", scope);
    if (scope === "slot") fd.append("slot", slot);
    if (pkg) fd.append("package", pkg);
    return api("/cal/write/plan", { method: "POST", body: fd });
  }, "/cal/write/execute");
};

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
async function elkImages() {
  try {
    const { images } = await api("/elk/images");
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
(async () => {
  initCanCharts(); startCanWS(); loadSequences(); startSeqPoll(); refreshAdb(); startAdbPoll();
  api("/meta").then(m => $("#diagEndpoint").textContent = `${m.uds.endpoint} · tester ${m.uds.tester} · ecu ${m.uds.ecu} · ${m.uds.vlan}`);
  loadRoutines(); ltzRef(); elkImages();
  loadVehiclePowerModes(); loadVehicleGearPositions();
})();
