"""The backend shared by both interactive layers: the web UI (web/app.py) and the
desktop UI (gui.py). Loading, display shaping, CalDef search, change tracking, the
safety gate and export all live here, so the two front ends cannot drift apart.

An "entry view" is the plain dict both front ends work with. `value_raw` is the
authoritative full-fidelity value and the only one ever exported; `value` is a
flattened string for display.
"""
from __future__ import annotations

import copy
import io
import zipfile
from pathlib import Path

from . import caldef, calovride, container, slotinfo

MAX_MEMBER_SIZE = container.MAX_DECOMPRESSED_SIZE


class InputError(ValueError):
    """Bad input or a refused request; the message is meant to be shown to the user."""


class SafetyAckRequired(InputError):
    pass


# Every exception a front end should show as a message rather than treat as a crash.
USER_ERRORS = (InputError, calovride.CalOvrideError, caldef.CalDefError, container.ContainerError)


# ------------------------------------------------------------------------- loading ---

def enum_options(de) -> list[dict]:
    if not (de and de.type_ == "Enumeration" and de.enum_id):
        return []
    labels = caldef._load_enum_labels().get(de.enum_id, {})
    return [{"value": v, "label": lbl} for v, lbl in sorted(labels.items(), key=lambda kv: int(kv[0]))]


def display_value(type_: str, value_raw) -> str:
    if type_ == "BinaryFile":
        return f"<BinaryFile: {value_raw['filename']}, {value_raw['length']} bytes>"
    if type_ in calovride.MAP_TYPES:
        return f"<{type_}: {len(value_raw)} entries>"
    if type_ == "Record":
        return f"<Record: {len(value_raw)} fields>"
    if type_ in calovride.ARRAY_TYPES:
        return ", ".join(value_raw)
    return value_raw


def is_editable(type_: str) -> bool:
    return type_ in calovride.SCALAR_TYPES or type_ == "String"


def known_effect_view(de) -> dict | None:
    """caldef.known_effect() plus a ready-to-show `text`, or None. For detail views
    only; export never reads it."""
    ke = caldef.known_effect(de.name, de.group) if de else None
    if ke is not None:
        ke["text"] = caldef.known_effect_text(ke)
    return ke


def entry_view(ov: calovride.Override) -> dict:
    de = caldef.lookup_by_id(ov.cal_id)
    value_raw = calovride.to_jsonable(ov)["value"]
    return {
        "cal_id": ov.cal_id,
        "version": ov.version,
        "type": ov.type_,
        "value": display_value(ov.type_, value_raw),
        "value_raw": value_raw,
        "editable": is_editable(ov.type_),
        "name": de.name if de else None,
        "group": de.group if de else None,
        "description": de.description if de else None,
        "enum_options": enum_options(de),
        "safety_restricted": caldef.is_safety_restricted(de) if de else False,
        # Display only: calibration-map findings, separate from GM's `description`.
        "known_effect": known_effect_view(de),
    }


def load_module(filename: str, data: bytes) -> dict:
    """Parse one signed container, unwrapped container, or bare .calovride document.
    `template` holds the original bytes when they can supply a container header."""
    meta = {"slot": None, "alpha_code": None, "part_number": None,
            "has_container_header": False, "digest_ok": None}
    c = container.parse_any(data)
    if c is not None:
        xml = c.inner_xml
        meta.update(slot=c.slot, alpha_code=c.alpha_code, part_number=c.part_number,
                    has_container_header=True, digest_ok=c.digest_ok)
    else:
        xml = data
    entries = [entry_view(e) for e in calovride.parse(xml)]
    info = slotinfo.describe(meta["slot"])
    return {
        "filename": filename,
        "meta": meta,
        "entries": entries,
        "template": data if c is not None else None,
        "slot_summary": info.summary if info else None,
        "slot_triage": info.triage if info else None,
    }


def load_zip(data: bytes) -> tuple[list[dict], list[dict]]:
    """Returns (modules, skipped). Members that are not calibration modules are listed
    in `skipped`; they never fail the whole archive."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise InputError("not a valid .zip file") from None
    modules, skipped = [], []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        if info.file_size > MAX_MEMBER_SIZE:
            skipped.append({"filename": name, "reason": "larger than the per-file size cap"})
            continue
        try:
            raw = zf.read(info)
        except Exception as e:
            skipped.append({"filename": name, "reason": str(e)})
            continue
        try:
            modules.append(load_module(name, raw))
        except Exception:
            skipped.append({"filename": name, "reason": "not a CSM container or CalOvride XML"})
    modules.sort(key=lambda m: (m["meta"]["slot"] is None, m["meta"]["slot"] or 0))
    return modules, skipped


# ------------------------------------------------------------------- CalDef lookup ---

def search_caldefs(query: str, limit: int = 50) -> list[dict]:
    if len(query) < 2:
        return []
    return [{"name": e.name, "group": e.group, "type": e.type_, "default": e.default_value,
             "description": e.description, "safety_restricted": caldef.is_safety_restricted(e),
             "known_effect_status": caldef.known_effect_summary(e.name, e.group)}
            for e in caldef.search(query)[:limit]]


def caldef_detail(name: str, group: str | None = None) -> dict:
    """Full detail needed to add an entry. `group` disambiguates a name defined twice."""
    e = caldef.lookup_in_group(name, group) if group else caldef.lookup(name)
    restricted = caldef.is_safety_restricted(e)
    return {
        "name": e.name, "cal_id": e.cal_id, "version": e.version, "type": e.type_,
        "group": e.group, "description": e.description, "default_value": e.default_value,
        "enum_options": enum_options(e),
        "safety_restricted": restricted,
        "safety_warning": caldef.SAFETY_WARNING.format(name=e.name, group=e.group) if restricted else None,
        "known_effect": known_effect_view(e),
    }


# ------------------------------------------------------------------------- editing ---

def start_tracking(module: dict) -> dict:
    """Remember each entry's loaded value so changes can be reported."""
    for e in module["entries"]:
        e["original_value_raw"] = copy.deepcopy(e["value_raw"])
        e["is_new"] = False
    return module


def is_modified(e: dict) -> bool:
    return e.get("is_new", False) or e["value_raw"] != e.get("original_value_raw", e["value_raw"])


def set_value(e: dict, value: str) -> None:
    if not e["editable"]:
        raise InputError(f"{e['type']} values are read-only here; edit the ingested JSON and use the CLI")
    calovride.validate_value(e["type"], value)
    e["value_raw"] = value
    e["value"] = value


def add_entry(module: dict, detail: dict) -> dict:
    """Append a new entry built from caldef_detail(). Safety confirmation is the
    caller's job, before calling this."""
    if any(e["cal_id"] == detail["cal_id"] for e in module["entries"]):
        raise InputError(f"{detail['name']} is already in this module")
    if not is_editable(detail["type"]):
        raise InputError(f"{detail['type']} entries cannot be added here")
    value = detail["default_value"] or ""
    entry = {
        "cal_id": detail["cal_id"], "version": detail["version"], "type": detail["type"],
        "value": value, "value_raw": value, "original_value_raw": None, "is_new": True,
        "editable": True, "name": detail["name"], "group": detail["group"],
        "description": detail["description"], "enum_options": detail["enum_options"],
        "safety_restricted": detail["safety_restricted"],
    }
    module["entries"].append(entry)
    return entry


def matches(e: dict, query: str = "", type_: str = "", modified_only: bool = False) -> bool:
    if type_ and e["type"] != type_:
        return False
    if modified_only and not is_modified(e):
        return False
    if query:
        hay = " ".join(str(e.get(k) or "") for k in ("name", "group", "description", "cal_id", "value"))
        return query.lower() in hay.lower()
    return True


def changed_restricted(entries: list[dict]) -> list[dict]:
    """Elevated-caution entries added or changed this session: what a front end must
    confirm with the user before it sends safety_ack on export."""
    return [e for e in entries if e["safety_restricted"] and is_modified(e)]


# -------------------------------------------------------------------------- export ---

def build_entries(entry_dicts) -> list[calovride.Override]:
    """Turn entry views (or minimal export payloads) into validated Overrides. Only
    value_raw is trusted; `value` is accepted solely for payloads that lack value_raw."""
    if not isinstance(entry_dicts, list):
        raise InputError(f"'entries' must be a list, got {type(entry_dicts).__name__}")
    out = []
    try:
        for d in entry_dicts:
            value = d["value_raw"] if "value_raw" in d else d["value"]
            ov = calovride.from_jsonable({"cal_id": d["cal_id"], "version": d["version"],
                                          "type": d["type"], "value": value})
            if is_editable(ov.type_):
                try:
                    calovride.validate_value(ov.type_, ov.value)
                except calovride.CalOvrideError as e:
                    de = caldef.lookup_by_id(ov.cal_id)
                    raise InputError(f"{de.name if de else ov.cal_id}: {e}") from e
            out.append(ov)
    except (KeyError, TypeError) as e:
        raise InputError(f"malformed entry (expected cal_id/version/type/value_raw on each) -- {e}") from e
    return out


def restricted_names(entries: list[calovride.Override]) -> list[str]:
    """Names of every entry in a safety-restricted CalDef group. Export gates on
    presence, not on change: a documented tradeoff of the stateless API (see README)."""
    found = (caldef.lookup_by_id(ov.cal_id) for ov in entries)
    return [de.name for de in found if de and caldef.is_safety_restricted(de)]


def check_safety_gate(entries: list[calovride.Override], acknowledged: bool) -> None:
    if acknowledged:
        return
    names = restricted_names(entries)
    if names:
        more = f", and {len(names) - 10} more" if len(names) > 10 else ""
        raise SafetyAckRequired(
            "safety_ack required: this export includes entries from elevated-caution chime/"
            f"safety/driver-workload CalDef groups ({', '.join(names[:10])}{more}). "
            "Set safety_ack:true in the request after confirming with the user -- see "
            "CALIBRATION_CUSTOMIZATION_GUIDE.md §3."
        )


def _reseal_with(template: bytes, xml: bytes) -> bytes | None:
    c = container.parse_any(template)
    return None if c is None else container.pack_outer(container.reseal(c.header, xml))


def export_module(entry_dicts, fmt: str = "xml", template: bytes | None = None,
                  safety_ack: bool = False) -> bytes:
    entries = build_entries(entry_dicts)
    check_safety_gate(entries, safety_ack)
    xml = calovride.serialize(entries)
    if fmt == "xml":
        return xml
    if fmt != "container":
        raise InputError(f"unknown format {fmt!r}")
    if not template:
        raise InputError("format=container requires a genuine container to borrow the header from")
    out = _reseal_with(template, xml)
    if out is None:
        raise InputError("the template is not a recognized CSM container (gzip-wrapped or unwrapped)")
    return out


def safe_member_name(raw_name: str) -> str:
    """Strip directory parts (both separator styles) so a hostile or malformed name
    cannot look like a traversal path to whatever extracts the zip."""
    name = Path(raw_name.replace("\\", "/")).name
    return "unnamed" if name in ("", ".", "..") else name


def export_zip(modules, safety_ack: bool = False) -> bytes:
    """modules: [{"filename", "entries", "template": bytes|None}]. A module with a
    usable template is written as a container, otherwise as .calovride XML."""
    if not isinstance(modules, list):
        raise InputError("expected a 'modules' list")
    built = []
    for mod in modules:
        if not isinstance(mod, dict) or "filename" not in mod:
            raise InputError("each module needs a 'filename'")
        built.append((mod["filename"], build_entries(mod.get("entries", [])), mod.get("template")))
    check_safety_gate([ov for _, entries, _ in built for ov in entries], safety_ack)

    buf = io.BytesIO()
    used = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, entries, template in built:
            xml = calovride.serialize(entries)
            base = safe_member_name(str(filename))
            name = base if base.endswith(".calovride") else base + ".calovride"
            data = xml
            if template:
                sealed = _reseal_with(template, xml)
                if sealed is not None:
                    name, data = base, sealed
            final, n = name, 1
            while final in used:  # two modules with the same basename must both survive
                n += 1
                stem, dot, ext = name.rpartition(".")
                final = f"{stem or name}_{n}{dot}{ext}" if dot else f"{name}_{n}"
            used.add(final)
            zf.writestr(final, data)
    return buf.getvalue()
