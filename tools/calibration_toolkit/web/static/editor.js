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
  const res = await fetch(isZip ? "/api/ingest_zip" : "/api/ingest", { method: "POST", body: form });
  const data = await res.json();
  if (data.error) { status.textContent = ""; alert(data.error); return; }

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
  if (modules[idx].expanded) expandedIndex = idx;
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
    nameTd.textContent = e.name || `(unresolved: ${e.cal_id})`;
    if (e.safety_restricted) {
      const badge = document.createElement("span");
      badge.className = "safetybadge";
      badge.textContent = " ⚠";
      badge.title = "never-shipped safety/chime group";
      nameTd.appendChild(badge);
    }

    const groupTd = document.createElement("td");
    groupTd.textContent = e.group || "";

    const typeTd = document.createElement("td");
    typeTd.textContent = e.type;

    const valueTd = document.createElement("td");
    renderValueControl(valueTd, e, mod, entryIdx);

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
    select.onchange = () => { mod.entries[entryIdx].value = select.value; };
    td.appendChild(select);
    return;
  }
  if (e.type === "Enumeration" && e.enum_options && e.enum_options.length) {
    const select = document.createElement("select");
    let matched = false;
    e.enum_options.forEach(opt => {
      const o = document.createElement("option");
      o.value = opt.value; o.textContent = `${opt.value} — ${opt.label}`;
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

    select.onchange = () => {
      if (select.value === "__custom__") {
        customInput.style.display = "inline-block";
        mod.entries[entryIdx].value = customInput.value;
      } else {
        customInput.style.display = "none";
        mod.entries[entryIdx].value = select.value;
      }
    };
    customInput.onchange = () => { mod.entries[entryIdx].value = customInput.value; };
    td.append(select, customInput);
    return;
  }
  if (e.editable) {
    const input = document.createElement("input");
    input.type = "text";
    input.value = e.value;
    input.onchange = () => { mod.entries[entryIdx].value = input.value; };
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
      const warn = r.safety_restricted ? ' <span class="safetybadge">⚠ never-shipped safety/chime group</span>' : "";
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
  mod.entries.push({
    cal_id: e.cal_id, version: e.version, type: e.type, value: e.default_value || "",
    editable: true, name: e.name, group: e.group, description: e.description,
    enum_options: e.enum_options || [], safety_restricted: e.safety_restricted,
  });
  renderModules();
}

function b64ToArrayBuffer(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function exportModule(idx, format) {
  const mod = modules[idx];
  const body = {
    entries: mod.entries.map(e => ({ cal_id: e.cal_id, version: e.version, type: e.type, value: e.value })),
    format: format === "container" ? "container" : "xml",
  };
  if (format === "container") {
    if (!mod.template_b64) { alert("no container header available for this module"); return; }
    body.template_b64 = mod.template_b64;
  }
  const res = await fetch("/api/export", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) { alert(await res.text()); return; }
  const name = format === "container" ? mod.filename : mod.filename.replace(/\.[^.]*$/, "") + ".calovride";
  download(await res.blob(), name);
}

async function exportAllZip() {
  const payload = { modules: modules.map(m => ({
    filename: m.filename,
    entries: m.entries.map(e => ({ cal_id: e.cal_id, version: e.version, type: e.type, value: e.value })),
    template_b64: m.template_b64,
  })) };
  const res = await fetch("/api/export_zip", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!res.ok) { alert(await res.text()); return; }
  download(await res.blob(), "custom_calibration_set.zip");
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
