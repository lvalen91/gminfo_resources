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

import io
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, render_template, request, send_file

from caltool import caldef, calovride, container

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def _repo_root() -> Path:
    root = os.environ.get("GMINFO_REPO_ROOT")
    return Path(root) if root else Path(__file__).resolve().parent.parent.parent.parent


def _entry_to_dict(ov: calovride.Override) -> dict:
    de = None
    try:
        entries_by_id = _caldef_by_id()
        de = entries_by_id.get(ov.cal_id)
    except caldef.CalDefError:
        pass
    value = ov.value
    editable = ov.type_ in calovride.SCALAR_TYPES or ov.type_ == "String"
    if isinstance(value, calovride.BinaryFileValue):
        value = f"<BinaryFile: {value.filename}, {value.length} bytes>"
    elif ov.type_ in calovride.MAP_TYPES:
        value = f"<{ov.type_}: {len(value)} entries>"
    elif ov.type_ == "Record":
        value = f"<Record: {len(value)} fields>"
    elif ov.type_ in calovride.ARRAY_TYPES:
        value = ", ".join(value)
    return {
        "cal_id": ov.cal_id,
        "version": ov.version,
        "type": ov.type_,
        "value": value,
        "editable": editable,
        "name": de.name if de else None,
        "group": de.group if de else None,
        "description": de.description if de else None,
        "enum_labels": caldef._load_enum_labels().get(de.enum_id, {}) if de and de.enum_id else {},
    }


_caldef_cache = None


def _caldef_by_id():
    global _caldef_cache
    if _caldef_cache is None:
        os.environ.setdefault("GMINFO_REPO_ROOT", str(_repo_root()))
        _caldef_cache = {e.cal_id: e for e in caldef._load_all().values()}
    return _caldef_cache


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
    meta = {"slot": None, "alpha_code": None, "part_number": None, "has_container_header": False}
    try:
        c = container.parse(raw)
        xml = c.inner_xml
        meta.update(slot=c.slot, alpha_code=c.alpha_code, part_number=c.part_number, has_container_header=True)
    except container.ContainerError:
        try:
            c = container.parse_unwrapped(raw)
            xml = c.inner_xml
            meta.update(slot=c.slot, alpha_code=c.alpha_code, part_number=c.part_number, has_container_header=True)
        except container.ContainerError:
            xml = raw
    try:
        entries = calovride.parse(xml)
    except Exception as e:
        return jsonify({"error": f"could not parse as CalOvride XML: {e}"}), 400
    return jsonify({"meta": meta, "filename": f.filename,
                     "entries": [_entry_to_dict(e) for e in entries]})


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
    return jsonify({
        "name": e.name, "cal_id": e.cal_id, "version": e.version, "type": e.type_,
        "group": e.group, "description": e.description, "default_value": e.default_value,
        "safety_restricted": restricted,
        "safety_warning": caldef.SAFETY_WARNING.format(name=e.name, group=e.group) if restricted else None,
    })


@app.route("/api/caldef/groups")
def api_caldef_groups():
    return jsonify(caldef.groups())


@app.route("/api/export", methods=["POST"])
def api_export():
    """Body: {"entries": [{cal_id, version, type, value}, ...], "format": "xml"|"json",
    "template_b64": optional base64 of a genuine container to borrow the header from}."""
    import base64
    import json as jsonlib

    payload = request.get_json(force=True)
    entries = []
    for d in payload["entries"]:
        type_ = d["type"]
        value = d["value"]
        entries.append(calovride.Override(d["cal_id"], str(d["version"]), type_, value))
    xml = calovride.serialize(entries)
    fmt = payload.get("format", "xml")
    if fmt == "xml":
        return send_file(io.BytesIO(xml), mimetype="application/xml",
                          as_attachment=True, download_name="custom.calovride")
    if fmt == "container":
        template_b64 = payload.get("template_b64")
        if not template_b64:
            return jsonify({"error": "format=container requires template_b64 (a genuine container to borrow the header from)"}), 400
        template_raw = base64.b64decode(template_b64)
        c = container.parse(template_raw)
        unwrapped = container.reseal(c.header, xml)
        outer = container.pack_outer(unwrapped)
        return send_file(io.BytesIO(outer), mimetype="application/octet-stream",
                          as_attachment=True, download_name="custom_container")
    return jsonify({"error": f"unknown format {fmt!r}"}), 400


if __name__ == "__main__":
    os.environ.setdefault("GMINFO_REPO_ROOT", str(_repo_root()))
    app.run(host="127.0.0.1", port=5057, debug=True)
