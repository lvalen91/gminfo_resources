#!/usr/bin/env python3
"""Local-only web UI for the calibration toolkit. Run with:

    GMINFO_REPO_ROOT=/path/to/gminfo_resources python3 web/app.py

then open http://127.0.0.1:5057/ . Nothing here is hosted externally; all state is
either in the uploaded/downloaded files themselves or in this process's memory for the
duration of one edit session -- there is no database and no account system. Edits are
made by uploading a file, changing values, and downloading the result; nothing persists
across a server restart.
"""
from __future__ import annotations

import base64
import binascii
import io
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, render_template, request, send_file

from caltool import caldef, calovride, container, slotinfo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def _repo_root() -> Path:
    root = os.environ.get("GMINFO_REPO_ROOT")
    return Path(root) if root else Path(__file__).resolve().parent.parent.parent.parent


# Set at import time (not just in __main__) so caldef lookups work regardless of how this
# module is invoked -- direct script run, `flask run`, or imported by a test harness.
os.environ.setdefault("GMINFO_REPO_ROOT", str(_repo_root()))


def _entry_to_dict(ov: calovride.Override) -> dict:
    de = None
    try:
        de = caldef.lookup_by_id(ov.cal_id)
    except caldef.CalDefError:
        pass
    jsonable = calovride.to_jsonable(ov)
    value_raw = jsonable["value"]  # the authoritative, full-fidelity value -- always sent back on export
    display_value = value_raw
    editable = ov.type_ in calovride.SCALAR_TYPES or ov.type_ == "String"
    if isinstance(ov.value, calovride.BinaryFileValue):
        display_value = f"<BinaryFile: {ov.value.filename}, {ov.value.length} bytes>"
    elif ov.type_ in calovride.MAP_TYPES:
        display_value = f"<{ov.type_}: {len(ov.value)} entries>"
    elif ov.type_ == "Record":
        display_value = f"<Record: {len(ov.value)} fields>"
    elif ov.type_ in calovride.ARRAY_TYPES:
        display_value = ", ".join(ov.value)
    enum_options = []
    if de and de.type_ == "Enumeration" and de.enum_id:
        labels = caldef._load_enum_labels().get(de.enum_id, {})
        enum_options = [{"value": v, "label": lbl} for v, lbl in sorted(labels.items(), key=lambda kv: int(kv[0]))]
    return {
        "cal_id": ov.cal_id,
        "version": ov.version,
        "type": ov.type_,
        "value": display_value,     # for display only -- a flattened string for structured types
        "value_raw": value_raw,     # authoritative -- ALWAYS send this back on export, never "value"
        "editable": editable,
        "name": de.name if de else None,
        "group": de.group if de else None,
        "description": de.description if de else None,
        "enum_options": enum_options,
        "safety_restricted": caldef.is_safety_restricted(de) if de else False,
    }


def _entries_from_payload(entry_dicts: list[dict]) -> list[calovride.Override]:
    """Build Override objects from client-submitted entries, using the authoritative
    value_raw field (falling back to value for older/simpler payloads where they're the
    same thing, e.g. a freshly-added scalar entry). Never trusts a flattened display
    string for a structured type."""
    out = []
    for d in entry_dicts:
        value = d["value_raw"] if "value_raw" in d else d["value"]
        out.append(calovride.from_jsonable({"cal_id": d["cal_id"], "version": d["version"],
                                             "type": d["type"], "value": value}))
    return out


def _restricted_names(entries: list[calovride.Override]) -> list[str]:
    """Names of every entry that resolves to a safety-restricted CalDef group. Used to
    gate export: see api_export/api_export_zip. This can't distinguish "already present
    unmodified" from "just added/edited" without server-side session state, which this
    stateless API intentionally doesn't keep -- so it gates on presence, not on change.
    That's a known, documented tradeoff (see README), not an oversight."""
    names = []
    for ov in entries:
        de = caldef.lookup_by_id(ov.cal_id)
        if de and caldef.is_safety_restricted(de):
            names.append(de.name)
    return names


def _ingest_bytes(data: bytes) -> tuple[list, dict]:
    """Returns (entries_dict_list, meta). meta['has_container_header'] tells callers
    whether a container export is possible for this module."""
    meta = {"slot": None, "alpha_code": None, "part_number": None, "has_container_header": False, "digest_ok": None}
    c = container.parse_any(data)
    if c is not None:
        xml = c.inner_xml
        meta.update(slot=c.slot, alpha_code=c.alpha_code, part_number=c.part_number,
                    has_container_header=True, digest_ok=c.digest_ok)
    else:
        xml = data
    entries = calovride.parse(xml)  # may raise calovride.CalOvrideError -- let caller decide
    return [_entry_to_dict(e) for e in entries], meta


@app.route("/")
def index():
    return render_template("editor.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file uploaded"}), 400
    raw = f.read()
    try:
        entries, meta = _ingest_bytes(raw)
    except Exception as e:
        return jsonify({"error": f"could not parse as CalOvride XML: {e}"}), 400
    slot_info = slotinfo.describe(meta["slot"])
    return jsonify({
        "meta": meta, "filename": f.filename, "entries": entries,
        "template_b64": base64.b64encode(raw).decode("ascii") if meta["has_container_header"] else None,
        "slot_summary": slot_info.summary if slot_info else None,
        "slot_triage": slot_info.triage if slot_info else None,
    })


@app.route("/api/ingest_zip", methods=["POST"])
def api_ingest_zip():
    """Accept a .zip (e.g. a whole spsCacheInternal/ directory, or a mix of outer-gzip
    SPS files / already-unwrapped .dec containers / bare .calovride files) and return
    every file that parses as a calibration module. Files that don't parse as either a
    CSM container or a bare CalOvride XML document (DLLs, .cfx, .log, manifests, etc.)
    are silently skipped and listed under "skipped", never raise an error for the whole
    upload."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file uploaded"}), 400
    try:
        zf = zipfile.ZipFile(io.BytesIO(f.read()))
    except zipfile.BadZipFile:
        return jsonify({"error": "not a valid .zip file"}), 400

    modules = []
    skipped = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        try:
            raw = zf.read(info)
        except Exception as e:
            skipped.append({"filename": name, "reason": str(e)})
            continue
        try:
            entries, meta = _ingest_bytes(raw)
        except Exception:
            skipped.append({"filename": name, "reason": "not a CSM container or CalOvride XML"})
            continue
        slot_info = slotinfo.describe(meta["slot"])
        modules.append({
            "filename": name,
            "meta": meta,
            "entries": entries,
            "template_b64": base64.b64encode(raw).decode("ascii") if meta["has_container_header"] else None,
            "slot_summary": slot_info.summary if slot_info else None,
            "slot_triage": slot_info.triage if slot_info else None,
        })

    modules.sort(key=lambda m: (m["meta"]["slot"] is None, m["meta"]["slot"] or 0))
    return jsonify({"modules": modules, "skipped": skipped})


@app.route("/api/caldef/search")
def api_caldef_search():
    q = request.args.get("q", "")
    if len(q) < 2:
        return jsonify([])
    results = caldef.search(q)[:50]
    return jsonify([{"name": e.name, "group": e.group, "type": e.type_,
                      "default": e.default_value, "description": e.description,
                      "safety_restricted": caldef.is_safety_restricted(e)} for e in results])


@app.route("/api/caldef/entry")
def api_caldef_entry():
    """Full detail for one CalDef name, including CalID/version -- needed to actually add
    it as a new override entry (search results above are display-only, by design)."""
    name = request.args.get("name", "")
    try:
        e = caldef.lookup(name)
    except caldef.CalDefError as exc:
        return jsonify({"error": str(exc)}), 404
    restricted = caldef.is_safety_restricted(e)
    enum_options = []
    if e.type_ == "Enumeration" and e.enum_id:
        labels = caldef._load_enum_labels().get(e.enum_id, {})
        enum_options = [{"value": v, "label": lbl} for v, lbl in sorted(labels.items(), key=lambda kv: int(kv[0]))]
    return jsonify({
        "name": e.name, "cal_id": e.cal_id, "version": e.version, "type": e.type_,
        "group": e.group, "description": e.description, "default_value": e.default_value,
        "enum_options": enum_options,
        "safety_restricted": restricted,
        "safety_warning": caldef.SAFETY_WARNING.format(name=e.name, group=e.group) if restricted else None,
    })


@app.route("/api/caldef/groups")
def api_caldef_groups():
    return jsonify(caldef.groups())


class _ExportInputError(ValueError):
    """Malformed export request body -- always a clean 400, never a 500."""


def _safe_member_name(raw_name: str) -> str:
    """Strip directory separators (both / and \\, so a Windows-style traversal name
    can't survive on a POSIX host either) and collapse a resulting empty/"."/".."  name
    to something inert. The export zip is for the user's own download, not written to
    disk server-side, but a hostile or just-malformed member name shouldn't be allowed
    to look like a traversal path to whatever extracts the zip later."""
    name = raw_name.replace("\\", "/")
    name = Path(name).name  # keeps only the final path component
    if name in ("", ".", ".."):
        name = "unnamed"
    return name


def _build_entries(entry_dicts) -> list[calovride.Override]:
    if not isinstance(entry_dicts, list):
        raise _ExportInputError(f"'entries' must be a list, got {type(entry_dicts).__name__}")
    try:
        return _entries_from_payload(entry_dicts)
    except (KeyError, TypeError) as e:
        raise _ExportInputError(f"malformed entry (expected cal_id/version/type/value_raw on each) -- {e}") from e


def _check_safety_gate(entries: list[calovride.Override], acknowledged: bool) -> None:
    """See _restricted_names()'s docstring for the "gates on presence, not on change"
    tradeoff this makes as a stateless API."""
    if acknowledged:
        return
    restricted = _restricted_names(entries)
    if restricted:
        raise _ExportInputError(
            "safety_ack required: this export includes entries from elevated-caution chime/"
            f"safety/driver-workload CalDef groups ({', '.join(restricted[:10])}"
            f"{f', and {len(restricted)-10} more' if len(restricted) > 10 else ''}). "
            "Set safety_ack:true in the request after confirming with the user -- see "
            "CALIBRATION_CUSTOMIZATION_GUIDE.md §3."
        )


@app.route("/api/export", methods=["POST"])
def api_export():
    """Body: {"entries": [{cal_id, version, type, value_raw}, ...], "format": "xml"|"container",
    "template_b64": optional base64 of a genuine container to borrow the header from,
    "safety_ack": optional bool, required true if any entry is safety-restricted}."""
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict) or "entries" not in payload:
            raise _ExportInputError("request body must be a JSON object with an 'entries' list")
        entries = _build_entries(payload["entries"])
        _check_safety_gate(entries, payload.get("safety_ack") is True)
        xml = calovride.serialize(entries)
        fmt = payload.get("format", "xml")
        if fmt == "xml":
            return send_file(io.BytesIO(xml), mimetype="application/xml",
                              as_attachment=True, download_name="custom.calovride")
        if fmt == "container":
            template_b64 = payload.get("template_b64")
            if not template_b64:
                return jsonify({"error": "format=container requires template_b64 (a genuine container to borrow the header from)"}), 400
            try:
                template_raw = base64.b64decode(template_b64, validate=True)
            except (binascii.Error, ValueError) as e:
                return jsonify({"error": f"template_b64 is not valid base64: {e}"}), 400
            c = container.parse_any(template_raw)
            if c is None:
                return jsonify({"error": "template_b64 is not a recognized CSM container (gzip-wrapped or unwrapped)"}), 400
            unwrapped = container.reseal(c.header, xml)
            outer = container.pack_outer(unwrapped)
            return send_file(io.BytesIO(outer), mimetype="application/octet-stream",
                              as_attachment=True, download_name="custom_container")
        return jsonify({"error": f"unknown format {fmt!r}"}), 400
    except (_ExportInputError, calovride.CalOvrideError, container.ContainerError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/export_zip", methods=["POST"])
def api_export_zip():
    """Body: {"modules": [{"filename", "entries": [...], "template_b64": optional}, ...],
    "safety_ack": optional bool, required true if any entry in any module is restricted}."""
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("modules"), list):
            raise _ExportInputError("request body must be a JSON object with a 'modules' list")
        acknowledged = payload.get("safety_ack") is True
        built = []
        for mod in payload["modules"]:
            if not isinstance(mod, dict) or "filename" not in mod:
                raise _ExportInputError("each module needs a 'filename'")
            entries = _build_entries(mod.get("entries", []))
            built.append((mod["filename"], entries, mod.get("template_b64")))
        all_entries = [ov for _, entries, _ in built for ov in entries]
        _check_safety_gate(all_entries, acknowledged)

        buf = io.BytesIO()
        used_names = set()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, entries, template_b64 in built:
                xml = calovride.serialize(entries)
                base_name = _safe_member_name(str(filename))
                xml_name = base_name if base_name.endswith(".calovride") else base_name + ".calovride"
                member_name, data = xml_name, xml
                if template_b64:
                    try:
                        template_raw = base64.b64decode(template_b64, validate=True)
                    except (binascii.Error, ValueError):
                        template_raw = None
                    c = container.parse_any(template_raw) if template_raw is not None else None
                    if c is not None:
                        unwrapped = container.reseal(c.header, xml)
                        member_name, data = base_name, container.pack_outer(unwrapped)
                # de-duplicate: two modules with the same basename would otherwise
                # silently collide and one would be lost from the zip
                final_name, n = member_name, 1
                while final_name in used_names:
                    n += 1
                    stem, dot, ext = member_name.rpartition(".")
                    final_name = f"{stem or member_name}_{n}{dot}{ext}" if dot else f"{member_name}_{n}"
                used_names.add(final_name)
                zf.writestr(final_name, data)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="custom_calibration_set.zip")
    except (_ExportInputError, calovride.CalOvrideError, container.ContainerError) as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5057, debug=False, use_reloader=False)
