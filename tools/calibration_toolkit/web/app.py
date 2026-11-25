#!/usr/bin/env python3
"""Local-only web UI for the calibration toolkit. Run with:

    python3 run.py web            # then open http://127.0.0.1:5057/

This file is only the HTTP layer; the behaviour lives in caltool/service.py, which the
desktop UI (gui.py) shares. Nothing here is hosted externally; all state is either in
the uploaded/downloaded files or in the browser tab for one edit session -- there is no
database and no account system.
"""
from __future__ import annotations

import base64
import binascii
import io
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_ROOT), str(_ROOT / "vendor")]  # bundled Flask and dependencies

from flask import Flask, jsonify, render_template, request, send_file

from caltool import caldef, calovride, service

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024   # uploads (compressed containers/zips)
# Export bodies are JSON: every entry's full value_raw plus each module's template as
# base64. That is ~25x the size of the gzip-compressed container it came from (measured
# on the test fixture), so the upload cap would make "Download all as .zip" fail with a
# 413 for a set whose upload was well under 8 MiB. Each module's XML is itself capped at
# 16 MiB by the decompressor, so this bounds a realistic full set, not an arbitrary one.
EXPORT_MAX_CONTENT_LENGTH = 192 * 1024 * 1024

# Element type each structured type's members must satisfy (checked on export; see
# _check_structured). Maps' keys are enumeration numbers.
_ARRAY_ELEMENT = {"IntegerArray": "Integer", "FloatArray": "Float", "StringArray": "String"}
_MAP_VALUE = {"EnumIntegerMap": "Integer", "EnumFloatMap": "Float"}


def _module_json(module: dict) -> dict:
    """The browser round-trips the container template as base64."""
    out = dict(module)
    template = out.pop("template")
    out["template_b64"] = base64.b64encode(template).decode("ascii") if template else None
    return out


def _decode_template(template_b64):
    if not template_b64:
        return None
    try:
        return base64.b64decode(template_b64, validate=True)
    except (binascii.Error, ValueError, TypeError) as e:
        raise service.InputError(f"template_b64 is not valid base64: {e}") from e


def _json_body() -> dict:
    """The export request body. Invalid JSON is a 400 with a JSON error (the editor shows
    it) rather than werkzeug's HTML BadRequest page."""
    request.max_content_length = EXPORT_MAX_CONTENT_LENGTH
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        raise service.InputError("request body must be a JSON object")
    return payload


def _check_member(where: str, type_: str, value) -> None:
    if not isinstance(value, str):
        raise service.InputError(f"{where}: expected a string, got {type(value).__name__}")
    try:
        calovride.validate_value(type_, value)
    except calovride.CalOvrideError as e:
        raise service.InputError(f"{where}: {e}") from e


def _check_structured(entry_dicts) -> None:
    """The web editor (unlike the CLI and desktop UI) edits array/map/record members
    inline, and service.build_entries validates only scalar/String entries. Without this
    a cleared or mistyped member (an IntegerArray cell set to "abc" or "", a Boolean
    Record field set to "maybe") exported silently; an empty <ArrayValue> is a file this
    toolkit cannot even re-ingest; and an array sent as a bare string would be serialized
    one character per element. Each member goes through calovride.validate_value with
    its own element type. Shapes this does not recognize are left to build_entries."""
    if not isinstance(entry_dicts, list):
        return
    for d in entry_dicts:
        if not isinstance(d, dict):
            continue
        type_ = d.get("type")
        value = d["value_raw"] if "value_raw" in d else d.get("value")
        name = caldef.lookup_by_id(d.get("cal_id")) if isinstance(d.get("cal_id"), str) else None
        label = name.name if name else str(d.get("cal_id"))
        if type_ in _ARRAY_ELEMENT or type_ in _MAP_VALUE or type_ == "Record":
            if not isinstance(value, list):
                raise service.InputError(f"{label}: {type_} value must be a list")
        if type_ in _ARRAY_ELEMENT:
            for i, v in enumerate(value):
                _check_member(f"{label}[{i}]", _ARRAY_ELEMENT[type_], v)
                if v == "":
                    raise service.InputError(f"{label}[{i}]: array elements may not be empty")
        elif type_ in _MAP_VALUE:
            for i, pair in enumerate(value):
                if not isinstance(pair, dict):
                    raise service.InputError(f"{label}: map entry {i} must be a {{key, value}} object")
                # keys are not editable in the UI; only their shape is checked
                _check_member(f"{label} entry {i} key", "String", pair.get("key"))
                _check_member(f"{label} key {pair.get('key')!r}", _MAP_VALUE[type_], pair.get("value"))
        elif type_ == "Record":
            for i, field in enumerate(value):
                if not isinstance(field, dict):
                    raise service.InputError(f"{label}: record field {i} must be a {{name, type, value}} object")
                ftype = field.get("type")
                if ftype in calovride.SCALAR_TYPES or ftype == "String":
                    _check_member(f"{label}.{field.get('name')}", ftype, field.get("value"))


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
    try:
        module = service.load_module(f.filename, f.read())
    except Exception as e:
        return jsonify({"error": f"could not parse as CalOvride XML: {e}"}), 400
    return jsonify(_module_json(module))


@app.route("/api/ingest_zip", methods=["POST"])
def api_ingest_zip():
    """Accept a .zip (e.g. a whole spsCacheInternal/ directory). See service.load_zip."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file uploaded"}), 400
    try:
        modules, skipped = service.load_zip(f.read())
    except service.InputError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"modules": [_module_json(m) for m in modules], "skipped": skipped})


@app.route("/api/caldef/search")
def api_caldef_search():
    return jsonify(service.search_caldefs(request.args.get("q", "")))


@app.route("/api/caldef/entry")
def api_caldef_entry():
    """Full detail for one CalDef name, including CalID/version -- needed to actually add
    it as a new override entry (search results above are display-only, by design)."""
    try:
        return jsonify(service.caldef_detail(request.args.get("name", ""),
                                             request.args.get("group") or None))
    except caldef.CalDefError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/caldef/groups")
def api_caldef_groups():
    return jsonify(caldef.groups())


@app.route("/api/export", methods=["POST"])
def api_export():
    """Body: {"entries": [{cal_id, version, type, value_raw}, ...], "format": "xml"|"container",
    "template_b64": optional base64 of a genuine container to borrow the header from,
    "safety_ack": optional bool, required true if any entry is safety-restricted}."""
    try:
        payload = _json_body()
        if "entries" not in payload:
            raise service.InputError("request body must be a JSON object with an 'entries' list")
        fmt = payload.get("format", "xml")
        template = _decode_template(payload.get("template_b64")) if fmt == "container" else None
        _check_structured(payload["entries"])
        data = service.export_module(payload["entries"], fmt, template,
                                     payload.get("safety_ack") is True)
    except service.USER_ERRORS as e:
        return jsonify({"error": str(e)}), 400
    mimetype, name = (("application/xml", "custom.calovride") if fmt == "xml"
                      else ("application/octet-stream", "custom_container"))
    return send_file(io.BytesIO(data), mimetype=mimetype, as_attachment=True, download_name=name)


@app.route("/api/export_zip", methods=["POST"])
def api_export_zip():
    """Body: {"modules": [{"filename", "entries": [...], "template_b64": optional}, ...],
    "safety_ack": optional bool, required true if any entry in any module is restricted}."""
    try:
        payload = _json_body()
        if not isinstance(payload.get("modules"), list):
            raise service.InputError("request body must be a JSON object with a 'modules' list")
        modules = []
        for mod in payload["modules"]:
            if not isinstance(mod, dict):
                raise service.InputError("each module needs a 'filename'")
            try:
                template = _decode_template(mod.get("template_b64"))
            except service.InputError:
                template = None  # fall back to XML for this one module
            _check_structured(mod.get("entries"))
            modules.append({**mod, "template": template})
        data = service.export_zip(modules, payload.get("safety_ack") is True)
    except service.USER_ERRORS as e:
        return jsonify({"error": str(e)}), 400
    return send_file(io.BytesIO(data), mimetype="application/zip", as_attachment=True,
                     download_name="custom_calibration_set.zip")


def main(port: int = 5057):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
