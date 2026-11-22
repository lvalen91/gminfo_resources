// State: one entry per loaded file, normalized to the same shape whether it came from
// a single-file ingest or a .zip of several.
let modules = [];          // [{filename, meta, entries, template_b64, slot_summary, slot_triage, expanded}]
let expandedIndex = null;  // which module index "add entry" currently targets

async function ingest() {
  const input = document.getElementById("fileInput");
  if (!input.files.length) { alert("choose a file first"); return; }
  const file = input.files[0];
  const status = document.getElementById("uploadStatus");
  status.textContent = " loading…";

  const isZip = file.name.toLowerCase().endsWith(".zip");
  const form = new FormData();
  form.append("file", file);
  let res, data;
  try {
    res = await fetch(isZip ? "/api/ingest_zip" : "/api/ingest", { method: "POST", body: form });
  } catch (err) {
    status.textContent = "";
    alert("network error talking to the local server: " + err.message);
    return;
  }
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    // e.g. a 413 (file too large) or a raw Flask error page -- never call res.json() on
    // these, it throws and used to leave the UI stuck on "loading…" forever
    status.textContent = "";
    alert(`upload failed: HTTP ${res.status} ${res.statusText}` +
          (res.status === 413 ? " (file too large)" : ""));
    return;
  }
  data = await res.json();
  if (data.error) { status.textContent = ""; alert(data.error); return; }

  // reset per-load state so a smaller/different set loaded next can't leave addEntry
  // targeting a module index that no longer exists, or a collapsed one silently
  expandedIndex = null;
  document.getElementById("searchResults").innerHTML = "";

  if (isZip) {
    modules = data.modules.map(m => ({ ...m, expanded: false }));
    renderSkipped(data.skipped);
  } else {
    modules = [{
      filename: data.filename, meta: data.meta, entries: data.entries,
      template_b64: data.template_b64, slot_summary: data.slot_summary,
      slot_triage: data.slot_triage, expanded: true,
    }];
    renderSkipped([]);
  }
  status.textContent = ` loaded ${modules.length} module(s)`;
  renderModules();
  document.getElementById("moduleList").style.display = modules.length ? "block" : "none";
  document.getElementById("caldefLookup").style.display = modules.length ? "block" : "none";
  if (modules.length === 1) { expandedIndex = 0; modules[0].expanded = true; renderModules(); }
}

function renderSkipped(skipped) {
  const section = document.getElementById("skippedSection");
  if (!skipped || !skipped.length) { section.style.display = "none"; return; }
  section.style.display = "block";
  document.getElementById("skippedNote").textContent =
    `Skipped ${skipped.length} file(s) not recognized as a calibration module: ` +
    skipped.map(s => s.filename).join(", ");
}

const TRIAGE_CLASS = { safe: "safe", mixed: "mixed", avoid: "avoid", "n/a": "" };

function renderModules() {
  document.getElementById("moduleCount").textContent = modules.length;
  const container = document.getElementById("modules");
  container.innerHTML = "";
  const tpl = document.getElementById("moduleTemplate");

  modules.forEach((m, idx) => {
    const node = tpl.content.cloneNode(true);
    const root = node.querySelector(".module");
    root.dataset.index = idx;

    const slotBadge = node.querySelector(".slot-badge");
    if (m.meta.slot !== null && m.meta.slot !== undefined) {
      slotBadge.textContent = `Slot ${m.meta.slot.toString(16).toUpperCase().padStart(2, "0")} (${m.meta.slot})`;
    } else {
      slotBadge.textContent = "no container header";
    }
    node.querySelector(".filename").textContent = m.filename;
    node.querySelector(".entry-count").textContent = `${m.entries.length} entries`;
    const triageBadge = node.querySelector(".triage-badge");
    if (m.slot_triage) {
      triageBadge.textContent = m.slot_triage;
      triageBadge.className = "triage-badge " + (TRIAGE_CLASS[m.slot_triage] || "");
    }
    node.querySelector(".slot-summary").textContent = m.slot_summary || "";

    const body = node.querySelector(".module-body");
    body.style.display = m.expanded ? "block" : "none";
    node.querySelector(".chevron").textContent = m.expanded ? "▾" : "▸";

    renderEntriesTable(node.querySelector(".entries-table tbody"), m, idx);

    node.querySelector(".export-xml-btn").onclick = () => exportModule(idx, "xml");
    node.querySelector(".export-container-btn").onclick = () => exportModule(idx, "container");
    if (!m.template_b64) node.querySelector(".export-container-btn").disabled = true;

    container.appendChild(node);
  });
}

function toggleModule(headerEl) {
  const root = headerEl.closest(".module");
  const idx = parseInt(root.dataset.index, 10);
  modules[idx].expanded = !modules[idx].expanded;
  if (modules[idx].expanded) {
    expandedIndex = idx;
  } else if (expandedIndex === idx) {
    // collapsing the module "add to open module" currently targets -- clear it rather
    // than silently letting the next add land in a module the user can no longer see
    expandedIndex = null;
  }
  renderModules();
}

function renderEntriesTable(tbody, mod, modIdx) {
  tbody.innerHTML = "";
  mod.entries.forEach((e, entryIdx) => {
    const tr = document.createElement("tr");

    const infoTd = document.createElement("td");
    if (e.description) {
      const btn = document.createElement("button");
      btn.className = "info-btn";
      btn.textContent = "i";
      btn.title = e.description;
      btn.onclick = (ev) => { ev.stopPropagation(); showInfoPopover(btn, e); };
      infoTd.appendChild(btn);
    }

    const nameTd = document.createElement("td");
    nameTd.title = e.name || e.cal_id;
    nameTd.textContent = e.name || `(unresolved: ${e.cal_id})`;
    if (e.safety_restricted) {
      const badge = document.createElement("span");
      badge.className = "safetybadge";
      badge.textContent = " ⚠";
      badge.title = "elevated-caution chime/safety group";
      nameTd.appendChild(badge);
    }

    const groupTd = document.createElement("td");
    groupTd.title = e.group || "";
    groupTd.textContent = e.group || "";

    const typeTd = document.createElement("td");
    typeTd.title = e.type;
    typeTd.textContent = e.type;

    const valueTd = document.createElement("td");
    const valueInner = document.createElement("div");
    valueInner.className = "value-cell-inner";
    valueTd.appendChild(valueInner);
    renderValueControl(valueInner, e, mod, entryIdx);

    tr.append(infoTd, nameTd, groupTd, typeTd, valueTd);
    tbody.appendChild(tr);
  });
}

function renderValueControl(td, e, mod, entryIdx) {
  if (e.type === "Boolean") {
    const select = document.createElement("select");
    ["true", "false"].forEach(v => {
      const opt = document.createElement("option");
      opt.value = v; opt.textContent = v;
      if (e.value === v) opt.selected = true;
      select.appendChild(opt);
    });
    select.onchange = () => { mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = select.value; };
    td.appendChild(select);
    return;
  }
  if (e.type === "Enumeration" && e.enum_options && e.enum_options.length) {
    const select = document.createElement("select");
    let matched = false;
    const optionLabel = (opt) => `${opt.value} — ${opt.label}`;
    e.enum_options.forEach(opt => {
      const o = document.createElement("option");
      o.value = opt.value; o.textContent = optionLabel(opt);
      o.title = optionLabel(opt);
      if (opt.value === e.value) { o.selected = true; matched = true; }
      select.appendChild(o);
    });
    const customOpt = document.createElement("option");
    customOpt.value = "__custom__"; customOpt.textContent = "Custom value…";
    select.appendChild(customOpt);
    const customInput = document.createElement("input");
    customInput.type = "text";
    customInput.className = "custom-enum-input";
    customInput.style.display = matched ? "none" : "inline-block";
    if (!matched) customInput.value = e.value;
    if (!matched) select.value = "__custom__";
    const updateTitle = () => {
      const sel = e.enum_options.find(o => o.value === select.value);
      select.title = sel ? optionLabel(sel) : "custom value";
    };
    updateTitle();

    select.onchange = () => {
      if (select.value === "__custom__") {
        customInput.style.display = "inline-block";
        mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = customInput.value;
      } else {
        customInput.style.display = "none";
        mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = select.value;
      }
      updateTitle();
    };
    customInput.onchange = () => { mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = customInput.value; };
    td.append(select, customInput);
    return;
  }
  if (e.editable) {
    const input = document.createElement("input");
    input.type = "text";
    input.value = e.value;
    input.onchange = () => { mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = input.value; };
    td.appendChild(input);
    return;
  }
  const span = document.createElement("span");
  span.className = "readonly-value";
  span.textContent = e.value + " (edit via JSON/CLI for this type)";
  td.appendChild(span);
}

let popoverEl = null;
function showInfoPopover(anchor, entry) {
  if (popoverEl) popoverEl.remove();
  popoverEl = document.createElement("div");
  popoverEl.className = "info-popover";
  popoverEl.innerHTML = `<b>${entry.name || entry.cal_id}</b> (${entry.group || "unknown group"})<br>${entry.description}`;
  document.body.appendChild(popoverEl);
  const rect = anchor.getBoundingClientRect();
  popoverEl.style.top = (rect.bottom + window.scrollY + 6) + "px";
  popoverEl.style.left = (rect.left + window.scrollX) + "px";
  const closeHandler = (ev) => {
    if (popoverEl && !popoverEl.contains(ev.target) && ev.target !== anchor) {
      popoverEl.remove(); popoverEl = null;
      document.removeEventListener("click", closeHandler);
    }
  };
  document.addEventListener("click", closeHandler);
}

let searchTimer = null;
function searchCalDef() {
  clearTimeout(searchTimer);
  const q = document.getElementById("calSearch").value;
  searchTimer = setTimeout(async () => {
    if (q.length < 2) { document.getElementById("searchResults").innerHTML = ""; return; }
    const res = await fetch("/api/caldef/search?q=" + encodeURIComponent(q));
    const results = await res.json();
    const div = document.getElementById("searchResults");
    div.innerHTML = "";
    if (expandedIndex === null) {
      div.innerHTML = "<p class='muted'>Expand a module above first — new entries are added to whichever module is open.</p>";
      return;
    }
    results.forEach(r => {
      const row = document.createElement("div");
      row.className = "searchrow";
      const warn = r.safety_restricted ? ' <span class="safetybadge">⚠ elevated-caution chime/safety group</span>' : "";
      row.innerHTML = `<b>${r.name}</b> (${r.group}, ${r.type}, default ${r.default})${warn} — ${r.description}
        <button onclick='addEntry(${JSON.stringify(r.name)})'>add to open module</button>`;
      div.appendChild(row);
    });
  }, 250);
}

async function addEntry(name) {
  if (expandedIndex === null) { alert("expand a module first"); return; }
  const mod = modules[expandedIndex];
  if (mod.entries.some(e => e.name === name)) { alert(name + " is already present in this module"); return; }
  const res = await fetch("/api/caldef/entry?name=" + encodeURIComponent(name));
  const e = await res.json();
  if (e.error) { alert(e.error); return; }
  if (!["Boolean", "Integer", "Float", "Enumeration", "String"].includes(e.type)) {
    alert(e.type + " entries can't be added from this minimal UI yet — use the CLI (caltool add) or edit exported JSON directly.");
    return;
  }
  if (e.safety_restricted) {
    const ok = confirm(
      e.safety_warning + "\n\n" +
      "Type OK only if you have read CALIBRATION_CUSTOMIZATION_GUIDE.md §3 and are proceeding " +
      "as a deliberate research action, not a feature customization."
    );
    if (!ok) return;
  }
  const initial = e.default_value || "";
  mod.entries.push({
    cal_id: e.cal_id, version: e.version, type: e.type, value: initial, value_raw: initial,
    editable: true, name: e.name, group: e.group, description: e.description,
    enum_options: e.enum_options || [], safety_restricted: e.safety_restricted,
  });
  renderModules();
}

function _entryForExport(e) {
  // value_raw is the authoritative, full-fidelity value for every type (set on ingest,
  // and kept in sync with .value by every editable control's onchange handler above).
  // Never send the flattened display string for a structured type -- that was a real,
  // confirmed data-corruption bug.
  return { cal_id: e.cal_id, version: e.version, type: e.type, value_raw: e.value_raw };
}

function _confirmSafetyRestricted(entries) {
  const restricted = entries.filter(e => e.safety_restricted);
  if (!restricted.length) return true;
  const names = restricted.slice(0, 10).map(e => e.name || e.cal_id);
  const more = restricted.length > 10 ? `, and ${restricted.length - 10} more` : "";
  return confirm(
    `This export includes ${restricted.length} entr${restricted.length === 1 ? "y" : "ies"} from ` +
    `elevated-caution chime/safety/driver-workload CalDef group(s): ${names.join(", ")}${more}.\n\n` +
    "These govern chime/alert/safety-volume/driver-workload/security-logging behavior, not a " +
    "cosmetic feature -- see CALIBRATION_CUSTOMIZATION_GUIDE.md §3. Click OK only if you " +
    "intend to export this data as a deliberate research action."
  );
}

async function exportModule(idx, format) {
  const mod = modules[idx];
  if (!_confirmSafetyRestricted(mod.entries)) return;
  const body = {
    entries: mod.entries.map(_entryForExport),
    format: format === "container" ? "container" : "xml",
    safety_ack: true,  // the confirm() above (a no-op if nothing restricted) is this tool's gate
  };
  if (format === "container") {
    if (!mod.template_b64) { alert("no container header available for this module"); return; }
    body.template_b64 = mod.template_b64;
  }
  const res = await fetch("/api/export", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) { alert(await _errorText(res)); return; }
  const name = format === "container" ? mod.filename : mod.filename.replace(/\.[^.]*$/, "") + ".calovride";
  download(await res.blob(), name);
}

async function exportAllZip() {
  const allEntries = modules.flatMap(m => m.entries);
  if (!_confirmSafetyRestricted(allEntries)) return;
  const payload = {
    modules: modules.map(m => ({
      filename: m.filename, entries: m.entries.map(_entryForExport), template_b64: m.template_b64,
    })),
    safety_ack: true,
  };
  const res = await fetch("/api/export_zip", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!res.ok) { alert(await _errorText(res)); return; }
  download(await res.blob(), "custom_calibration_set.zip");
}

async function _errorText(res) {
  try {
    const d = await res.json();
    return d.error || `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status} ${res.statusText}`;
  }
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
