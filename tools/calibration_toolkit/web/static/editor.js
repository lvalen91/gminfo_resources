// State: one entry per loaded file, normalized to the same shape whether it came from
// a single-file ingest or a .zip of several.
let modules = [];          // [{filename, meta, entries, template_b64, slot_summary, slot_triage, expanded, _built}]
// There is deliberately no "currently targeted module" global for adding a CalDef entry.
// Each expanded module has its own "Add entry" control, scoped to that module by
// position -- not by a hidden pointer that silently follows whichever module happened
// to be expanded last. That was a real, reported design flaw: the add-UI sat detached
// at the bottom of the page and only worked if some module was already open, with no
// visible indication of which one it would affect.

// ----------------------------------------------------------------- small utilities ---

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function nameWithBreaks(name) {
  // Inline, escaped, with a <wbr> after each underscore so long SCREAMING_SNAKE_CASE
  // identifiers wrap at token boundaries instead of mid-word or not at all. overflow-wrap:
  // anywhere in CSS is the fallback for the rare name with no underscores at all.
  return escapeHtml(name).split("_").join("_<wbr>");
}

function cloneValue(v) {
  return v === undefined ? v : JSON.parse(JSON.stringify(v));
}

function isModified(e) {
  if (e.is_new) return true;
  return JSON.stringify(e.value_raw) !== JSON.stringify(e.original_value_raw);
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  // revoking synchronously can cancel the download before the browser has read the blob
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function baseName(path) {
  // zip members keep their directory ("spsCacheInternal/04"); a download name cannot
  return String(path).split(/[\\/]/).pop() || "module";
}

// A CalDef name is not unique: ~154 names exist in two groups with different CalIDs, so
// "is this search result already in the module" must compare name AND group.
function sameCalDef(e, name, group) {
  return e.name === name && (e.group || null) === (group || null);
}

// POST a JSON body and download the response. Every failure, including the network
// itself, ends in an alert rather than an unhandled rejection that looks like nothing.
async function postAndDownload(url, body, name) {
  let res;
  try {
    res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
  } catch (err) {
    alert("network error talking to the local server: " + err.message);
    return;
  }
  if (!res.ok) { alert(await _errorText(res)); return; }
  download(await res.blob(), name);
}

async function _errorText(res) {
  try {
    const d = await res.json();
    return d.error || `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status} ${res.statusText}`;
  }
}

// ------------------------------------------------------------------------- ingest ---

async function ingest() {
  const input = document.getElementById("fileInput");
  if (!input.files.length) { alert("choose a file first"); return; }
  const file = input.files[0];
  // loading replaces every open module; the desktop UI asks first, so does this
  if (modules.some(m => modifiedCount(m) > 0) &&
      !confirm("Replace the open modules? Their edits are lost unless you have already downloaded them.")) return;
  const status = document.getElementById("uploadStatus");
  status.textContent = " loading…";

  const isZip = file.name.toLowerCase().endsWith(".zip");
  const form = new FormData();
  form.append("file", file);
  let res;
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
  const data = await res.json();
  if (data.error) { status.textContent = ""; alert(data.error); return; }

  const snapshot = (entries) => entries.map(e => ({
    ...e, original_value_raw: cloneValue(e.value_raw), is_new: false,
  }));

  if (isZip) {
    modules = data.modules.map(m => ({ ...m, entries: snapshot(m.entries), expanded: false, _built: false }));
    renderSkipped(data.skipped);
  } else {
    modules = [{
      filename: data.filename, meta: data.meta, entries: snapshot(data.entries),
      template_b64: data.template_b64, slot_summary: data.slot_summary,
      slot_triage: data.slot_triage, expanded: true, _built: false,
    }];
    renderSkipped([]);
  }
  status.textContent = ` loaded ${modules.length} module(s)`;
  renderModuleList();
  document.getElementById("moduleList").style.display = modules.length ? "block" : "none";
  if (modules.length === 1) { modules[0].expanded = true; renderModuleList(); }
}

function renderSkipped(skipped) {
  const section = document.getElementById("skippedSection");
  if (!skipped || !skipped.length) { section.style.display = "none"; return; }
  section.style.display = "block";
  document.getElementById("skippedNote").textContent =
    `Skipped ${skipped.length} file(s) not recognized as a calibration module: ` +
    skipped.map(s => s.filename).join(", ");
}

// --------------------------------------------------------------- module list shell ---

const TRIAGE_CLASS = { safe: "safe", mixed: "mixed", avoid: "avoid", "n/a": "" };
const TRIAGE_LABEL = { safe: "try", mixed: "mixed", avoid: "avoid", "n/a": "n/a" };

function modifiedCount(mod) {
  return mod.entries.reduce((n, e) => n + (isModified(e) ? 1 : 0), 0);
}

// A module's shell (header/summary/body/export-bar DOM nodes) is built exactly ONCE per
// module and never recreated after that -- only its header badges and its body's
// visibility get updated on subsequent calls. This matters: buildModuleBody() only
// populates a body element the FIRST time it sees a given module (so editing one of up
// to 404 rows doesn't re-render all of them) -- if renderModuleList() ever threw away
// and rebuilt the body <div> itself (as an earlier version of this function did), that
// guard would silently leave the brand-new element empty forever, which is exactly the
// "section collapses and expanding it does nothing" bug: EVERY edit, and even a plain
// collapse/re-expand with no edit at all, destroyed and replaced the populated body.
function renderModuleList() {
  document.getElementById("moduleCount").textContent = modules.length;
  const container = document.getElementById("modules");

  const isFreshLoad = container.children.length !== modules.length ||
    [...container.children].some((el, i) => Number(el.dataset.index) !== i);

  if (isFreshLoad) {
    container.innerHTML = "";
    modules.forEach((mod, idx) => container.appendChild(buildModuleShell(mod, idx)));
  } else {
    modules.forEach((mod, idx) => updateModuleShell(container.children[idx], mod, idx));
  }
}

function buildModuleShell(mod, idx) {
  const root = document.createElement("div");
  root.className = "module";
  root.dataset.index = idx;

  const header = document.createElement("div");
  header.className = "module-header";
  header.setAttribute("role", "button");
  header.setAttribute("tabindex", "0");
  header.onclick = () => toggleModule(idx);
  header.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggleModule(idx); } };
  root.appendChild(header);

  const body = document.createElement("div");
  body.className = "module-body";
  body.dataset.index = idx;
  root.appendChild(body);

  const exportBar = document.createElement("div");
  exportBar.className = "module-export";
  const xmlBtn = document.createElement("button");
  xmlBtn.textContent = "Download edited .calovride XML";
  xmlBtn.onclick = () => exportModule(idx, "xml");
  const containerBtn = document.createElement("button");
  containerBtn.className = "primary";
  containerBtn.textContent = "Download full container";
  containerBtn.title = "Reuses this module's own header; digest recomputed, signature stays stale — see help";
  containerBtn.disabled = !mod.template_b64;
  containerBtn.onclick = () => exportModule(idx, "container");
  exportBar.append(xmlBtn, containerBtn);
  root.appendChild(exportBar);

  updateModuleShell(root, mod, idx);
  return root;
}

function updateModuleShell(root, mod, idx) {
  root.dataset.expanded = String(mod.expanded);
  const header = root.querySelector(".module-header");
  header.setAttribute("aria-expanded", String(mod.expanded));
  const slotLabel = (mod.meta.slot !== null && mod.meta.slot !== undefined)
    ? `Slot ${mod.meta.slot.toString(16).toUpperCase().padStart(2, "0")} (${mod.meta.slot})`
    : "no container header";
  const mCount = modifiedCount(mod);
  header.innerHTML = `
    <span class="chevron">${mod.expanded ? "▾" : "▸"}</span>
    <span class="slot-badge">${escapeHtml(slotLabel)}</span>
    <span class="filename">${escapeHtml(mod.filename)}</span>
    <span class="entry-count">${mod.entries.length} entries</span>
    ${mod.meta.digest_ok === false ? `<span class="triage-badge avoid">digest mismatch</span>` : ""}
    ${mCount ? `<span class="modified-count">${mCount} modified</span>` : ""}
    ${mod.slot_triage ? `<span class="triage-badge ${TRIAGE_CLASS[mod.slot_triage] || ""}">${escapeHtml(TRIAGE_LABEL[mod.slot_triage] || mod.slot_triage)}</span>` : ""}
  `;
  header.onclick = () => toggleModule(idx);
  header.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggleModule(idx); } };

  // slot-summary isn't built once in buildModuleShell -- a shell can be reused for a
  // DIFFERENT module (same index, re-loaded), so whether this element should exist at
  // all, and what it says, has to be re-decided on every update, not just the first.
  let summary = root.querySelector(".slot-summary");
  if (mod.slot_summary) {
    if (!summary) {
      summary = document.createElement("div");
      summary.className = "slot-summary";
      header.after(summary);
    }
    summary.textContent = mod.slot_summary;
  } else if (summary) {
    summary.remove();
  }

  const body = root.querySelector(".module-body");
  body.style.display = mod.expanded ? "block" : "none";
  if (mod.expanded) buildModuleBody(body, mod, idx);  // no-op if mod._built is already true

  const containerBtn = root.querySelector(".module-export button.primary");
  if (containerBtn) containerBtn.disabled = !mod.template_b64;
}

function toggleModule(idx) {
  const mod = modules[idx];
  mod.expanded = !mod.expanded;
  renderModuleList();
}

// ------------------------------------------------------------- module body (lazy) ---

function slotLabel(mod) {
  const slot = mod.meta && mod.meta.slot;
  return (slot !== null && slot !== undefined)
    ? `Slot ${slot.toString(16).toUpperCase().padStart(2, "0")}`
    : mod.filename;
}

function buildModuleBody(bodyEl, mod, idx) {
  if (mod._built) { bodyEl.style.display = "block"; return; }
  mod._built = true;
  bodyEl.innerHTML = "";

  const hasEntries = mod.entries.length > 0;

  // toolbar: the per-module filter (filters entries already loaded here) and the
  // "Add entry" control (searches the whole CalDef reference, not just this module)
  // live in the same sticky row but are never the same control -- conflating "filter
  // what's loaded" with "search everything to add something new" is exactly the
  // confusion this replaces.
  const toolbar = document.createElement("div");
  toolbar.className = "module-toolbar";

  const bar = document.createElement("div");
  bar.className = "filter-bar";
  let textInput, typeSelect, modifiedCheckbox, countEl;
  if (hasEntries) {
    const types = [...new Set(mod.entries.map(e => e.type))].sort();
    bar.innerHTML = `
      <input type="text" placeholder="filter name / group / description / value…" class="filter-text">
      <select class="filter-type"><option value="">all types</option>${types.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join("")}</select>
      <label><input type="checkbox" class="filter-modified"> modified only</label>
      <span class="filter-count"></span>
    `;
    textInput = bar.querySelector(".filter-text");
    typeSelect = bar.querySelector(".filter-type");
    modifiedCheckbox = bar.querySelector(".filter-modified");
    countEl = bar.querySelector(".filter-count");
  } else {
    bar.innerHTML = `<span class="muted">No entries in this module.</span>`;
  }
  const addToggle = document.createElement("button");
  addToggle.className = "add-entry-toggle";
  addToggle.type = "button";
  addToggle.textContent = "+ Add entry…";
  addToggle.setAttribute("aria-expanded", "false");
  bar.appendChild(addToggle);
  toolbar.appendChild(bar);

  const noMatch = document.createElement("div");
  noMatch.className = "filter-no-match";
  noMatch.style.display = "none";
  toolbar.appendChild(noMatch);

  bodyEl.appendChild(toolbar);

  const groupsEl = document.createElement("div");
  bodyEl.appendChild(groupsEl);

  // group entries by their CalDef group (fallback bucket for unresolved CalIDs); kept
  // incremental (not rebuilt wholesale) so adding one entry doesn't reset filter state,
  // collapsed groups, or an open add-entry search.
  const groupSections = new Map(); // groupName -> {sectionEl, rowsEl, countEl, safetyEl, count}
  const allRowEls = [];            // {el, entryIdx}

  const makeGroupSection = (groupName) => {
    const section = document.createElement("div");
    section.className = "group-section";
    section.dataset.expanded = "true";
    const gHeader = document.createElement("div");
    gHeader.className = "group-header";
    gHeader.innerHTML = `
      <span class="chevron">▾</span>
      <span class="group-name">${nameWithBreaks(groupName)}</span>
      <span class="group-safety"></span>
      <span class="group-count">0</span>
    `;
    const rows = document.createElement("div");
    rows.className = "group-rows";
    gHeader.onclick = () => {
      const expanded = section.dataset.expanded === "true";
      section.dataset.expanded = String(!expanded);
      gHeader.querySelector(".chevron").textContent = expanded ? "▸" : "▾";
    };
    section.append(gHeader, rows);
    const ref = {
      sectionEl: section, rowsEl: rows,
      countEl: gHeader.querySelector(".group-count"),
      safetyEl: gHeader.querySelector(".group-safety"),
      count: 0,
    };
    groupSections.set(groupName, ref);
    groupsEl.appendChild(section);
    return ref;
  };

  const addRowToGroup = (groupName, entryIdx) => {
    let ref = groupSections.get(groupName);
    if (!ref) ref = makeGroupSection(groupName);
    const rowEl = renderEntryRow(mod, entryIdx);
    ref.rowsEl.appendChild(rowEl);
    ref.count++;
    ref.countEl.textContent = ref.count;
    if (mod.entries[entryIdx].safety_restricted) ref.safetyEl.innerHTML = safetyBadgeHtml();
    allRowEls.push({ el: rowEl, entryIdx });
    return rowEl;
  };

  mod.entries.forEach((e, entryIdx) => addRowToGroup(e.group || "(unresolved CalID)", entryIdx));

  // state other functions (incremental add, the empty-filter bridge) need, without a
  // global pointer: it hangs off the module object that's already passed around.
  mod._domRefs = { groupsEl, allRowEls, addRowToGroup, toolbar, addToggle };

  if (hasEntries) {
    const applyFilter = () => {
      const q = textInput.value.trim();
      const qLower = q.toLowerCase();
      const typeFilter = typeSelect.value;
      const modOnly = modifiedCheckbox.checked;
      let visible = 0;
      allRowEls.forEach(({ el, entryIdx }) => {
        const e = mod.entries[entryIdx];
        let show = true;
        if (qLower) {
          const hay = [e.name, e.group, e.description, e.cal_id, String(e.value)].join(" ").toLowerCase();
          show = hay.includes(qLower);
        }
        if (show && typeFilter) show = e.type === typeFilter;
        if (show && modOnly) show = isModified(e);
        el.style.display = show ? "" : "none";
        if (show) visible++;
      });
      groupsEl.querySelectorAll(".group-section").forEach(section => {
        const anyVisible = [...section.querySelectorAll(".entry-row")].some(r => r.style.display !== "none");
        section.style.display = anyVisible ? "" : "none";
      });
      countEl.textContent = (q || typeFilter || modOnly) ? `${visible} of ${mod.entries.length}` : "";

      if (visible === 0 && q) {
        noMatch.style.display = "block";
        noMatch.textContent = `No loaded entries match "${q}". `;
        const link = document.createElement("button");
        link.type = "button";
        link.className = "link-button";
        link.textContent = `Search all CalDef definitions for "${q}" →`;
        link.onclick = () => openAddPanel(mod, idx, q);
        noMatch.appendChild(link);
      } else {
        noMatch.style.display = "none";
      }
    };
    textInput.oninput = applyFilter;
    typeSelect.onchange = applyFilter;
    modifiedCheckbox.onchange = applyFilter;
    mod._domRefs.clearFilter = () => {
      if (!textInput.value && !typeSelect.value && !modifiedCheckbox.checked) return;
      textInput.value = ""; typeSelect.value = ""; modifiedCheckbox.checked = false;
      applyFilter();
    };
  } else {
    noMatch.style.display = "block";
    noMatch.textContent = "Use Add entry to pull a calibration in from the CalDef reference.";
  }

  addToggle.onclick = () => toggleAddPanel(mod, idx);

  bodyEl.style.display = "block";
}

function safetyBadgeHtml() {
  return `<span class="safetybadge" title="elevated-caution chime/safety/driver-workload group">
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1 L15 14 H1 Z M8 5.5 V9.5 M8 11.5 V12.5"
      stroke="currentColor" stroke-width="1.4" fill="none" stroke-linejoin="round" stroke-linecap="round"/></svg>
    caution</span>`;
}

// ----------------------------------------------------------------------- entry row ---

function renderEntryRow(mod, entryIdx) {
  const e = mod.entries[entryIdx];
  const row = document.createElement("div");
  row.className = "entry-row" + (isModified(e) ? " modified" : "");
  row.dataset.entryIdx = entryIdx;

  const identity = document.createElement("div");
  identity.className = "entry-identity";
  const nameLine = document.createElement("div");
  nameLine.className = "entry-name-line";
  nameLine.innerHTML = `
    <span class="entry-name">${e.name ? nameWithBreaks(e.name) : `(unresolved: ${escapeHtml(e.cal_id)})`}</span>
    <span class="entry-type-chip">${escapeHtml(e.type)}</span>
    ${e.safety_restricted ? safetyBadgeHtml() : ""}
  `;
  identity.appendChild(nameLine);

  if (e.description) {
    const desc = document.createElement("div");
    desc.className = "entry-desc";
    desc.textContent = e.description;  // textContent, not innerHTML -- CalDef prose can contain <, &
    identity.appendChild(desc);
    // only show a toggle if the text is actually being clamped (more than ~2 lines worth)
    requestAnimationFrame(() => {
      if (desc.scrollHeight > desc.clientHeight + 2) {
        const toggle = document.createElement("button");
        toggle.className = "entry-desc-toggle";
        toggle.textContent = "more";
        toggle.onclick = () => {
          const expanded = desc.classList.toggle("expanded");
          toggle.textContent = expanded ? "less" : "more";
        };
        identity.appendChild(toggle);
      }
    });
  }

  const valueCell = document.createElement("div");
  valueCell.className = "entry-value";
  renderValueControl(valueCell, e, mod, entryIdx, row);

  row.append(identity, valueCell);
  return row;
}

function markModified(mod, entryIdx, row) {
  const modified = isModified(mod.entries[entryIdx]);
  row.classList.toggle("modified", modified);
  // module header's modified count is cheap enough to just re-render the shell
  renderModuleList();
}

function renderValueControl(td, e, mod, entryIdx, row) {
  if (e.type === "Boolean") {
    const wrap = document.createElement("div");
    wrap.className = "bool-toggle";
    ["true", "false"].forEach(v => {
      const btn = document.createElement("button");
      btn.type = "button"; btn.textContent = v;
      btn.className = (e.value_raw === v ? `active ${v}` : "");
      btn.onclick = () => {
        mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = v;
        wrap.querySelectorAll("button").forEach(b => b.className = (b.textContent === v ? `active ${v}` : ""));
        markModified(mod, entryIdx, row);
      };
      wrap.appendChild(btn);
    });
    td.appendChild(wrap);
    return;
  }

  if (e.type === "Enumeration") {
    const wrap = document.createElement("div");
    wrap.className = "enum-pair";
    const numInput = document.createElement("input");
    numInput.type = "text"; numInput.inputMode = "numeric"; numInput.value = e.value_raw;
    const select = document.createElement("select");
    const options = e.enum_options || [];
    const noteEl = document.createElement("div");
    noteEl.className = "enum-unlisted-note";

    const rebuildSelect = (currentValue) => {
      select.innerHTML = "";
      let matched = false;
      options.forEach(opt => {
        const o = document.createElement("option");
        o.value = opt.value; o.textContent = `${opt.value} — ${opt.label}`;
        if (opt.value === currentValue) { o.selected = true; matched = true; }
        select.appendChild(o);
      });
      if (!matched) {
        const o = document.createElement("option");
        o.value = currentValue; o.textContent = `${currentValue} — not in CalDef`; o.selected = true;
        select.appendChild(o);
      }
      wrap.classList.toggle("unlisted", !matched);
      noteEl.textContent = matched ? "" : "value not in the known CalDef enum list";
    };
    rebuildSelect(e.value_raw);

    const setValue = (v) => {
      mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = v;
      markModified(mod, entryIdx, row);
    };
    numInput.onchange = () => { rebuildSelect(numInput.value); setValue(numInput.value); };
    select.onchange = () => { numInput.value = select.value; rebuildSelect(select.value); setValue(select.value); };

    wrap.append(numInput, select);
    td.append(wrap, noteEl);
    return;
  }

  if (e.editable) {
    const input = document.createElement("input");
    input.type = "text";
    input.value = e.value_raw;
    input.onchange = () => {
      mod.entries[entryIdx].value = mod.entries[entryIdx].value_raw = input.value;
      markModified(mod, entryIdx, row);
    };
    td.appendChild(input);
    return;
  }

  renderStructuredValue(td, e, mod, entryIdx, row);
}

// ----------------------------------------------------------- structured value types ---

function structuredPreview(e) {
  const v = e.value_raw;
  if (e.type === "Record") {
    const first = v.find(f => f.type === "String");
    return `${first ? `"${first.value}" · ` : ""}${v.length} field${v.length === 1 ? "" : "s"}`;
  }
  if (e.type === "IntegerArray" || e.type === "FloatArray" || e.type === "StringArray") {
    return `[${v.length}] ${v.slice(0, 6).join(", ")}${v.length > 6 ? ", …" : ""}`;
  }
  if (e.type === "EnumIntegerMap" || e.type === "EnumFloatMap") {
    return `{${v.length} pair${v.length === 1 ? "" : "s"}}`;
  }
  if (e.type === "BinaryFile") {
    return `${v.filename} · ${v.length}B · CRC32 ${v.checksum}`;
  }
  return String(v);
}

function renderStructuredValue(td, e, mod, entryIdx, row) {
  const wrap = document.createElement("div");
  wrap.className = "readonly-value-row";
  const preview = document.createElement("span");
  preview.className = "readonly-value-preview";
  preview.textContent = structuredPreview(e);
  wrap.appendChild(preview);

  if (e.type === "BinaryFile") {
    // never meaningfully editable inline -- a fact sheet is the honest UI for this
    const btn = document.createElement("button");
    btn.className = "expand-btn"; btn.textContent = "Details";
    btn.onclick = () => togglePanel(row, () => buildBinaryPanel(e));
    wrap.appendChild(btn);
    td.appendChild(wrap);
    return;
  }

  const btn = document.createElement("button");
  btn.className = "expand-btn"; btn.textContent = "Edit";
  btn.onclick = () => togglePanel(row, () => buildStructuredPanel(e, mod, entryIdx, row, preview));
  wrap.appendChild(btn);
  td.appendChild(wrap);
}

function togglePanel(row, buildFn) {
  const existing = row.querySelector(".structured-panel");
  if (existing) { existing.remove(); return; }
  const panel = buildFn();
  row.appendChild(panel);
}

function buildBinaryPanel(e) {
  const panel = document.createElement("div");
  panel.className = "structured-panel";
  const v = e.value_raw;
  panel.innerHTML = `
    <div class="binary-fact">
      <div><b>Filename:</b> ${escapeHtml(v.filename)}</div>
      <div><b>Length:</b> ${v.length} bytes</div>
      <div><b>CRC-32:</b> ${v.checksum}</div>
      <div class="muted" style="margin-top:6px;font-family:inherit">Not editable inline — this is an opaque
        binary blob (tuning table / audio file). Use the CLI or edit the exported JSON directly to replace it.</div>
    </div>`;
  return panel;
}

function buildStructuredPanel(e, mod, entryIdx, row, previewEl) {
  const panel = document.createElement("div");
  panel.className = "structured-panel";

  const commit = (newValue) => {
    mod.entries[entryIdx].value_raw = newValue;
    mod.entries[entryIdx].value = structuredPreview(mod.entries[entryIdx]);
    previewEl.textContent = mod.entries[entryIdx].value;
    markModified(mod, entryIdx, row);
  };

  if (e.type === "Record") {
    const fields = e.value_raw;
    fields.forEach((f, i) => {
      const fRow = document.createElement("div");
      fRow.className = "structured-field-row";
      const label = document.createElement("div");
      label.className = "structured-field-label";
      label.textContent = f.name;
      const control = document.createElement("div");
      const input = document.createElement("input");
      input.type = "text"; input.value = f.value;
      input.onchange = () => { fields[i] = { ...f, value: input.value }; commit(fields); };
      control.appendChild(input);
      fRow.append(label, control);
      panel.appendChild(fRow);
    });
  } else if (e.type === "IntegerArray" || e.type === "FloatArray" || e.type === "StringArray") {
    const arr = e.value_raw;
    const grid = document.createElement("div");
    grid.className = "array-grid";
    arr.forEach((val, i) => {
      const cell = document.createElement("div");
      cell.className = "array-cell";
      const input = document.createElement("input");
      input.type = "text"; input.value = val;
      input.onchange = () => { arr[i] = input.value; commit(arr); };
      cell.innerHTML = `<span class="idx">[${i}]</span>`;
      cell.appendChild(input);
      grid.appendChild(cell);
    });
    panel.appendChild(grid);
  } else if (e.type === "EnumIntegerMap" || e.type === "EnumFloatMap") {
    const pairs = e.value_raw;
    const grid = document.createElement("div");
    grid.className = "map-grid";
    pairs.forEach((pair, i) => {
      const keyEl = document.createElement("div");
      keyEl.textContent = pair.key;
      keyEl.style.fontFamily = "var(--mono)"; keyEl.style.fontSize = "12px"; keyEl.style.alignSelf = "center";
      const input = document.createElement("input");
      input.type = "text"; input.value = pair.value;
      input.onchange = () => { pairs[i] = { ...pair, value: input.value }; commit(pairs); };
      grid.append(keyEl, input);
    });
    panel.appendChild(grid);
  }

  const footer = document.createElement("div");
  footer.style.marginTop = "8px";
  const resetBtn = document.createElement("button");
  resetBtn.className = "reset-btn"; resetBtn.textContent = "Reset to loaded value";
  resetBtn.onclick = () => {
    const entry = mod.entries[entryIdx];
    entry.value_raw = cloneValue(entry.original_value_raw);
    entry.value = structuredPreview(entry);
    // rebuild the panel in place: its inputs still show the edited values, and
    // togglePanel() here only closed it, so Reset looked like "Close"
    const fresh = buildStructuredPanel(entry, mod, entryIdx, row, previewEl);
    panel.replaceWith(fresh);
    previewEl.textContent = entry.value;
    markModified(mod, entryIdx, row);
  };
  footer.appendChild(resetBtn);
  panel.appendChild(footer);

  return panel;
}

// --------------------------------------------------------- per-module add-entry panel ---
// Searches the whole CalDef reference (~3,000 definitions) to add a new entry to ONE
// specific, already-visible module. Scoped by closure over `mod`/`idx` -- never by a
// global "currently targeted module" pointer -- so there's nothing to desync and no
// hidden state the search box could be silently acting on.

function toggleAddPanel(mod, idx) {
  const toolbar = mod._domRefs.toolbar;
  const existing = toolbar.querySelector(".add-panel");
  if (existing) {
    existing.remove();
    mod._domRefs.addToggle.setAttribute("aria-expanded", "false");
    return;
  }
  openAddPanel(mod, idx, "");
}

function openAddPanel(mod, idx, prefillQuery) {
  const toolbar = mod._domRefs.toolbar;
  let panel = toolbar.querySelector(".add-panel");
  if (!panel) {
    panel = buildAddPanel(mod, idx);
    toolbar.appendChild(panel);
    mod._domRefs.addToggle.setAttribute("aria-expanded", "true");
  }
  const input = panel.querySelector(".add-panel-search");
  input.value = prefillQuery;
  input.focus();
  runAddPanelSearch(mod, idx, panel, prefillQuery);
}

function buildAddPanel(mod, idx) {
  const panel = document.createElement("div");
  panel.className = "add-panel";
  panel.innerHTML = `
    <div class="add-panel-header">
      <span>Add entry to ${escapeHtml(slotLabel(mod))} — from the CalDef reference</span>
      <button type="button" class="add-panel-close" aria-label="Close">×</button>
    </div>
    <input type="text" class="add-panel-search" placeholder="search all CalDef definitions by name…">
    <div class="add-panel-results"></div>
  `;
  const close = () => {
    panel.remove();
    mod._domRefs.addToggle.setAttribute("aria-expanded", "false");
    mod._domRefs.addToggle.focus();
  };
  panel.querySelector(".add-panel-close").onclick = close;

  const input = panel.querySelector(".add-panel-search");
  let timer = null, seq = 0;
  input.oninput = () => {
    clearTimeout(timer);
    const mySeq = ++seq;
    timer = setTimeout(() => {
      if (mySeq === seq) runAddPanelSearch(mod, idx, panel, input.value);
    }, 250);
  };
  input.onkeydown = (ev) => { if (ev.key === "Escape") close(); };
  return panel;
}

async function runAddPanelSearch(mod, idx, panel, rawQuery) {
  const resultsEl = panel.querySelector(".add-panel-results");
  const q = rawQuery.trim();
  if (q.length < 2) {
    resultsEl.innerHTML = '<p class="muted add-panel-hint">Type at least 2 characters.</p>';
    return;
  }
  let results;
  try {
    const res = await fetch("/api/caldef/search?q=" + encodeURIComponent(q));
    if (!res.ok) throw new Error(await _errorText(res));
    results = await res.json();
  } catch (err) {
    if (panel.querySelector(".add-panel-search").value.trim() !== q) return;
    resultsEl.innerHTML = "";
    const p = document.createElement("p");
    p.className = "muted add-panel-hint";
    p.textContent = "Search failed: " + err.message;
    resultsEl.appendChild(p);
    return;
  }
  if (panel.querySelector(".add-panel-search").value.trim() !== q) return; // stale response
  resultsEl.innerHTML = "";
  if (!results.length) {
    resultsEl.innerHTML = `<p class="muted add-panel-hint">No CalDef definitions match "${escapeHtml(q)}".</p>`;
    return;
  }
  results.forEach(r => resultsEl.appendChild(buildAddPanelRow(mod, idx, r)));
  if (results.length === 50) {
    const footer = document.createElement("div");
    footer.className = "add-panel-footer muted";
    footer.textContent = "Showing first 50 results — refine the search for more.";
    resultsEl.appendChild(footer);
  }
}

function buildAddPanelRow(mod, idx, r) {
  const row = document.createElement("div");
  row.className = "searchrow";

  const identity = document.createElement("div");
  identity.className = "searchrow-identity";
  identity.innerHTML = `
    <div class="searchrow-name-line">
      <span class="searchrow-name">${nameWithBreaks(r.name)}</span>
      <span class="entry-type-chip">${escapeHtml(r.type)}</span>
      <span class="searchrow-meta">${escapeHtml(r.group)} · default ${escapeHtml(String(r.default))}</span>
      ${r.safety_restricted ? safetyBadgeHtml() : ""}
    </div>
  `;
  if (r.description) {
    const desc = document.createElement("div");
    desc.className = "searchrow-desc";
    desc.textContent = r.description;
    identity.appendChild(desc);
    requestAnimationFrame(() => {
      if (desc.scrollHeight > desc.clientHeight + 2) {
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "entry-desc-toggle";
        toggle.textContent = "more";
        toggle.onclick = () => {
          const expanded = desc.classList.toggle("expanded");
          toggle.textContent = expanded ? "less" : "more";
        };
        identity.appendChild(toggle);
      }
    });
  }

  const actions = document.createElement("div");
  actions.className = "searchrow-actions";
  const alreadyPresent = mod.entries.some(e => sameCalDef(e, r.name, r.group));
  const supported = ["Boolean", "Integer", "Float", "Enumeration", "String"].includes(r.type);

  if (alreadyPresent) {
    row.classList.add("already-present");
    const showBtn = document.createElement("button");
    showBtn.type = "button";
    showBtn.textContent = "In this module · Show";
    showBtn.onclick = () => scrollToAndFlashEntry(mod, r.name, r.group);
    actions.appendChild(showBtn);
  } else if (!supported) {
    const note = document.createElement("span");
    note.className = "muted add-panel-unsupported";
    note.textContent = `${r.type} not supported here — use the CLI`;
    actions.appendChild(note);
  } else {
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.textContent = "Add";
    addBtn.onclick = async () => {
      addBtn.disabled = true; // the only guard against a double-click firing two overlapping fetches
      // Always resolve the full CalDef entry first -- search results carry no cal_id/
      // version/safety_warning, so a restricted-entry confirm needs this fetch BEFORE
      // showing the dialog, and a failed resolution (e.g. one of the ~154 CalDef names
      // that collide across two groups, which /api/caldef/entry rejects as ambiguous)
      // must be caught before the button is ever marked "Added".
      let e;
      try {
        const res = await fetch("/api/caldef/entry?name=" + encodeURIComponent(r.name) +
                                "&group=" + encodeURIComponent(r.group));
        e = await res.json();
        if (!res.ok && !e.error) e = { error: `HTTP ${res.status}` };
      } catch (err) {
        e = { error: "could not look up this CalDef entry: " + err.message };
      }
      if (e.error) { alert(e.error); addBtn.disabled = false; return; }
      if (mod.entries.some(x => x.cal_id === e.cal_id)) {
        alert(`${e.name} (CalID ${e.cal_id}) is already in this module`);
        addBtn.disabled = false;
        return;
      }
      if (e.safety_restricted) {
        const ok = await confirmDialog(
          "Add an elevated-caution entry?",
          (e.safety_warning || "") + " Confirm only if you have read CALIBRATION_CUSTOMIZATION_GUIDE.md §3 and are " +
          "proceeding as a deliberate research action, not a feature customization.",
          [], "Add anyway"
        );
        if (!ok) { addBtn.disabled = false; return; }
      }
      insertCalDefEntryIntoModule(mod, idx, e);
      row.classList.add("already-present");
      addBtn.textContent = "Added · Show";
      addBtn.disabled = false;
      addBtn.onclick = () => scrollToAndFlashEntry(mod, r.name, r.group);
    };
    actions.appendChild(addBtn);
  }

  row.append(identity, actions);
  return row;
}

function insertCalDefEntryIntoModule(mod, idx, e) {
  const initial = e.default_value || "";
  mod.entries.push({
    cal_id: e.cal_id, version: e.version, type: e.type, value: initial, value_raw: initial,
    original_value_raw: undefined, is_new: true,
    editable: true, name: e.name, group: e.group, description: e.description,
    enum_options: e.enum_options || [], safety_restricted: e.safety_restricted,
  });
  const entryIdx = mod.entries.length - 1;
  const refs = mod._domRefs;
  const rowEl = refs.addRowToGroup(e.group || "(unresolved CalID)", entryIdx);
  // the type filter's options were built from the types present at build time; a new
  // type would otherwise be unfilterable
  const typeSelect = refs.toolbar.querySelector(".filter-type");
  if (typeSelect && ![...typeSelect.options].some(o => o.value === e.type)) {
    const o = document.createElement("option");
    o.value = e.type; o.textContent = e.type;
    typeSelect.appendChild(o);
  }
  // an initially empty module shows a "use Add entry" hint that is stale once it has one
  if (!refs.clearFilter) refs.toolbar.querySelector(".filter-no-match").style.display = "none";
  revealRow(mod, rowEl);
  renderModuleList(); // only refreshes header badges (updateModuleShell) -- the open panel is untouched
}

function scrollToAndFlashEntry(mod, name, group) {
  const entryIdx = mod.entries.findIndex(e => sameCalDef(e, name, group));
  if (entryIdx === -1) return;
  const ref = mod._domRefs.allRowEls.find(r => r.entryIdx === entryIdx);
  if (!ref) return;
  revealRow(mod, ref.el);
}

// Guarantees a row is actually visible before flashing it -- not just un-hiding the row
// itself, which left it invisible whenever its whole group section was hidden (by a
// non-matching filter) or collapsed. Clears the module's filter, since "where did my
// new entry go" is exactly the complaint a half-fix (row.style.display only) left open.
function revealRow(mod, rowEl) {
  const refs = mod._domRefs;
  if (refs.clearFilter) refs.clearFilter();
  const groupEl = rowEl.closest(".group-section");
  if (groupEl) {
    groupEl.dataset.expanded = "true";
    const chevron = groupEl.querySelector(".chevron");
    if (chevron) chevron.textContent = "▾";
    groupEl.style.display = "";
  }
  rowEl.style.display = "";
  flashRow(rowEl);
}

function flashRow(el) {
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1200);
}

// ------------------------------------------------------------------ safety dialog ---

function confirmDialog(title, bodyText, items, confirmLabel) {
  return new Promise((resolve) => {
    const dialog = document.getElementById("safetyDialog");
    document.getElementById("safetyDialogTitle").textContent = title;
    document.getElementById("safetyDialogBody").textContent = bodyText;
    const listEl = document.getElementById("safetyDialogList");
    listEl.innerHTML = "";
    if (items.length) {
      let lastGroup = null;
      items.forEach(it => {
        if (it.group !== lastGroup) {
          const g = document.createElement("div");
          g.className = "group-label";
          g.textContent = it.group;
          listEl.appendChild(g);
          lastGroup = it.group;
        }
        const row = document.createElement("div");
        row.className = "item";
        row.innerHTML = `<span>${escapeHtml(it.name)}</span><span class="old-new">${escapeHtml(it.change || "")}</span>`;
        listEl.appendChild(row);
      });
      listEl.style.display = "block";
    } else {
      listEl.style.display = "none";
    }
    const confirmBtn = document.getElementById("safetyDialogConfirm");
    const cancelBtn = document.getElementById("safetyDialogCancel");
    confirmBtn.textContent = confirmLabel;
    const cleanup = (result) => {
      dialog.close();
      confirmBtn.onclick = null; cancelBtn.onclick = null; dialog.onclose = null;
      resolve(result);
    };
    confirmBtn.onclick = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
    dialog.onclose = () => resolve(false);  // Esc / backdrop click
    dialog.showModal();
    cancelBtn.focus();  // Cancel, not Confirm, gets default focus for a caution-gated action
  });
}

async function confirmExportIfNeeded(entries) {
  // Gate on entries that are BOTH safety-restricted AND actually added/modified in this
  // session. An unmodified, already-shipped restricted entry (stock slot 04 alone ships
  // 162 of them) doesn't need a prompt every single export -- that's exactly the alert-
  // fatigue pattern that trains people to click through without reading. The server still
  // requires safety_ack whenever ANY restricted entry is present in the payload; this
  // dialog is what legitimately earns that ack, computed from real edit-tracking rather
  // than asked blindly on every export.
  const changed = entries.filter(e => e.safety_restricted && isModified(e));
  if (!changed.length) return true;
  const items = changed.map(e => ({
    name: e.name || e.cal_id, group: e.group || "",
    change: e.is_new ? "(added)" : `${JSON.stringify(e.original_value_raw)} → ${JSON.stringify(e.value_raw)}`,
  }));
  return confirmDialog(
    `Export ${changed.length} modified elevated-caution ${changed.length === 1 ? "entry" : "entries"}?`,
    "These belong to CalDef groups that govern chime/alert/safety-volume/driver-workload/security-logging " +
    "behavior, not a cosmetic feature — see CALIBRATION_CUSTOMIZATION_GUIDE.md §3.",
    items, `Export with ${changed.length} caution ${changed.length === 1 ? "entry" : "entries"}`
  );
}

// ------------------------------------------------------------------------- export ---

function _entryForExport(e) {
  return { cal_id: e.cal_id, version: e.version, type: e.type, value_raw: e.value_raw };
}

async function exportModule(idx, format) {
  const mod = modules[idx];
  if (format === "container" && !mod.template_b64) {
    alert("no container header available for this module"); return;
  }
  if (!(await confirmExportIfNeeded(mod.entries))) return;
  const body = {
    entries: mod.entries.map(_entryForExport),
    format: format === "container" ? "container" : "xml",
    safety_ack: true,
  };
  if (format === "container") body.template_b64 = mod.template_b64;
  const base = baseName(mod.filename);
  const name = format === "container" ? base : base.replace(/\.[^.]*$/, "") + ".calovride";
  await postAndDownload("/api/export", body, name);
}

async function exportAllZip() {
  const allEntries = modules.flatMap(m => m.entries);
  if (!(await confirmExportIfNeeded(allEntries))) return;
  const payload = {
    modules: modules.map(m => ({
      filename: m.filename, entries: m.entries.map(_entryForExport), template_b64: m.template_b64,
    })),
    safety_ack: true,
  };
  await postAndDownload("/api/export_zip", payload, "custom_calibration_set.zip");
}
