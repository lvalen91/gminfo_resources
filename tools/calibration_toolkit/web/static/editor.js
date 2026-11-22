let currentEntries = [];
let currentFileB64 = null;
let hasContainerHeader = false;

async function ingest() {
  const input = document.getElementById("fileInput");
  if (!input.files.length) { alert("choose a file first"); return; }
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = async () => {
    currentFileB64 = reader.result.split(",")[1];
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/ingest", { method: "POST", body: form });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    currentEntries = data.entries;
    hasContainerHeader = data.meta.has_container_header;
    document.getElementById("meta").textContent =
      hasContainerHeader
        ? ` — slot ${data.meta.slot} (0x${data.meta.slot.toString(16).toUpperCase()}), alpha ${data.meta.alpha_code}, part ${data.meta.part_number}`
        : " — bare .calovride XML (no container header; container export unavailable)";
    renderTable();
    document.getElementById("entriesSection").style.display = "block";
    document.getElementById("addRow").style.display = "block";
    document.getElementById("exportSection").style.display = "block";
  };
  reader.readAsDataURL(file);
}

function renderTable() {
  document.getElementById("entryCount").textContent = currentEntries.length;
  const tbody = document.querySelector("#entriesTable tbody");
  tbody.innerHTML = "";
  currentEntries.forEach((e, i) => {
    const tr = document.createElement("tr");
    const nameTd = document.createElement("td");
    nameTd.textContent = e.name || "(unresolved CalID: " + e.cal_id + ")";
    const groupTd = document.createElement("td");
    groupTd.textContent = e.group || "";
    const typeTd = document.createElement("td");
    typeTd.textContent = e.type;
    const valueTd = document.createElement("td");
    if (e.editable) {
      const input = document.createElement("input");
      input.type = "text";
      input.value = e.value;
      input.onchange = () => { currentEntries[i].value = input.value; };
      valueTd.appendChild(input);
      if (Object.keys(e.enum_labels || {}).length) {
        const hint = document.createElement("div");
        hint.className = "enumhint";
        hint.textContent = Object.entries(e.enum_labels).map(([k, v]) => `${k}=${v}`).join(", ");
        valueTd.appendChild(hint);
      }
    } else {
      valueTd.textContent = e.value + " (edit via CLI/JSON for this type)";
    }
    const descTd = document.createElement("td");
    descTd.className = "desc";
    descTd.textContent = e.description || "";
    tr.append(nameTd, groupTd, typeTd, valueTd, descTd);
    tbody.appendChild(tr);
  });
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
    results.forEach(r => {
      const row = document.createElement("div");
      row.className = "searchrow";
      const warn = r.safety_restricted ? ' <span class="safetybadge">⚠ never-shipped safety/chime group</span>' : "";
      row.innerHTML = `<b>${r.name}</b> (${r.group}, ${r.type}, default ${r.default})${warn} — ${r.description}
        <button onclick='addEntry(${JSON.stringify(r.name)})'>add</button>`;
      div.appendChild(row);
    });
  }, 250);
}

async function addEntry(name) {
  if (currentEntries.some(e => e.name === name)) { alert(name + " is already present"); return; }
  const res = await fetch("/api/caldef/entry?name=" + encodeURIComponent(name));
  const e = await res.json();
  if (e.error) { alert(e.error); return; }
  if (!["Boolean", "Integer", "Float", "Enumeration", "String"].includes(e.type)) {
    alert(e.type + " entries can't be added from this minimal UI yet — use the CLI (caltool add) or edit the exported JSON directly.");
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
  currentEntries.push({
    cal_id: e.cal_id, version: e.version, type: e.type, value: e.default_value || "",
    editable: true, name: e.name, group: e.group, description: e.description, enum_labels: {},
  });
  renderTable();
}

async function exportXml() {
  const res = await fetch("/api/export", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries: currentEntries.map(e => ({ cal_id: e.cal_id, version: e.version, type: e.type, value: e.value })), format: "xml" }),
  });
  if (!res.ok) { alert(await res.text()); return; }
  download(await res.blob(), "custom.calovride");
}

async function exportContainer() {
  if (!hasContainerHeader) { alert("no container header available — upload a signed container, not a bare XML file, to export a full container"); return; }
  const res = await fetch("/api/export", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entries: currentEntries.map(e => ({ cal_id: e.cal_id, version: e.version, type: e.type, value: e.value })),
      format: "container", template_b64: currentFileB64,
    }),
  });
  if (!res.ok) { alert(await res.text()); return; }
  download(await res.blob(), "custom_container");
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
