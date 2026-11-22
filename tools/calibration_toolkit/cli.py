#!/usr/bin/env python3
"""caltool -- command-line interface for the GM CalOvride calibration toolkit.

Agent/LLM-friendly: every subcommand that emits data defaults to JSON on stdout, and
every subcommand that takes an edit takes it as plain arguments -- no interactive
prompts, nothing is required that can't be scripted.

Signature/live-hardware acceptance is explicitly OUT OF SCOPE (see caltool/container.py
and research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md). This tool produces
correctly-formatted, correctly-digested calibration payloads; getting a modified one
accepted by real hardware is a separate, already-documented, live-bench procedure.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from dataclasses import asdict
from pathlib import Path

from caltool import caldef, calovride, container


def _entry_to_json(ov: calovride.Override) -> dict:
    value = ov.value
    if isinstance(value, calovride.BinaryFileValue):
        value = {"filename": value.filename, "length": value.length,
                 "checksum": value.checksum, "data_b64": value.data_b64}
    elif ov.type_ in calovride.MAP_TYPES:
        value = [{"key": k, "value": v} for k, v in value]
    elif ov.type_ == "Record":
        value = [{"name": f.name, "type": f.type_, "value": f.value} for f in value]
    return {"cal_id": ov.cal_id, "version": ov.version, "type": ov.type_, "value": value}


def _entry_from_json(d: dict) -> calovride.Override:
    value = d["value"]
    type_ = d["type"]
    if type_ == "BinaryFile":
        value = calovride.BinaryFileValue(value["filename"], value["data_b64"], value["length"], value["checksum"])
    elif type_ in calovride.MAP_TYPES:
        value = [(e["key"], e["value"]) for e in value]
    elif type_ == "Record":
        value = [calovride.Field(e["name"], e["type"], e["value"]) for e in value]
    return calovride.Override(d["cal_id"], str(d["version"]), type_, value)


def cmd_ingest(args):
    raw = Path(args.file).read_bytes()
    try:
        c = container.parse(raw)
        xml = c.inner_xml
        meta = {"slot": c.slot, "alpha_code": c.alpha_code, "part_number": c.part_number}
    except container.ContainerError:
        # might already be an unwrapped container, or a bare .calovride XML file
        try:
            c = container.parse_unwrapped(raw)
            xml = c.inner_xml
            meta = {"slot": c.slot, "alpha_code": c.alpha_code, "part_number": c.part_number}
        except container.ContainerError:
            xml = raw
            meta = {"slot": None, "alpha_code": None, "part_number": None}
    entries = calovride.parse(xml)
    out = {"meta": meta, "entry_count": len(entries), "entries": [_entry_to_json(e) for e in entries]}
    print(json.dumps(out, indent=2))


def cmd_explain(args):
    e = caldef.lookup(args.name)
    out = asdict(e)
    out["safety_restricted"] = caldef.is_safety_restricted(e)
    if out["safety_restricted"]:
        out["safety_warning"] = caldef.SAFETY_WARNING.format(name=e.name, group=e.group)
    if e.type_ == "Enumeration" and e.enum_id:
        out["enum_labels"] = caldef._load_enum_labels().get(e.enum_id, {})
    print(json.dumps(out, indent=2))


def cmd_search(args):
    results = caldef.search(args.substring)
    print(json.dumps([{"name": e.name, "group": e.group, "type": e.type_, "default": e.default_value}
                       for e in results], indent=2))


def cmd_groups(args):
    print(json.dumps(caldef.groups(), indent=2))


def cmd_group(args):
    entries = caldef.entries_in_group(args.name)
    print(json.dumps([{"name": e.name, "type": e.type_, "default": e.default_value,
                        "description": e.description} for e in entries], indent=2))


def cmd_set(args):
    entries_json = json.loads(Path(args.file).read_text())
    entries = [_entry_from_json(d) for d in entries_json["entries"]]
    found = False
    for e in entries:
        de = None
        try:
            de = caldef.lookup(args.name)
        except caldef.CalDefError:
            pass
        if (de and e.cal_id == de.cal_id) or e.cal_id == args.name:
            de_by_id = de or caldef.lookup_by_id(e.cal_id)
            if de_by_id:
                try:
                    caldef.require_safety_ack(de_by_id, args.i_understand_the_safety_risk)
                except caldef.SafetyGateError as exc:
                    print(f"error: {exc}", file=sys.stderr)
                    sys.exit(1)
            e.value = args.value
            found = True
            break
    if not found:
        print(f"error: {args.name!r} not present in {args.file} -- use 'add' to introduce a new CalID", file=sys.stderr)
        sys.exit(1)
    entries_json["entries"] = [_entry_to_json(e) for e in entries]
    entries_json["entry_count"] = len(entries)
    Path(args.file).write_text(json.dumps(entries_json, indent=2))
    print(f"set {args.name} = {args.value!r} in {args.file}")


def cmd_add(args):
    de = caldef.lookup(args.name)
    try:
        caldef.require_safety_ack(de, args.i_understand_the_safety_risk)
    except caldef.SafetyGateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    entries_json = json.loads(Path(args.file).read_text()) if Path(args.file).exists() else \
        {"meta": {"slot": None, "alpha_code": None, "part_number": None}, "entries": []}
    entries = [_entry_from_json(d) for d in entries_json["entries"]]
    if any(e.cal_id == de.cal_id for e in entries):
        print(f"error: {args.name!r} already present -- use 'set' to change it", file=sys.stderr)
        sys.exit(1)
    value = args.value
    if de.type_ in calovride.ARRAY_TYPES or de.type_ in calovride.MAP_TYPES or de.type_ == "Record":
        print(f"error: {de.type_} values must be edited via JSON directly (use ingest/set on the JSON file)", file=sys.stderr)
        sys.exit(1)
    entries.append(calovride.Override(de.cal_id, de.version, de.type_, value))
    entries_json["entries"] = [_entry_to_json(e) for e in entries]
    entries_json["entry_count"] = len(entries)
    Path(args.file).write_text(json.dumps(entries_json, indent=2))
    print(f"added {args.name} ({de.group}) = {value!r} to {args.file}")


def cmd_pack(args):
    entries_json = json.loads(Path(args.file).read_text())
    entries = [_entry_from_json(d) for d in entries_json["entries"]]
    xml = calovride.serialize(entries)
    if args.xml_only:
        Path(args.out).write_bytes(xml)
        print(f"wrote CalOvride XML ({len(xml)} bytes) to {args.out}")
        return
    if not args.template:
        print("error: --template <genuine container file> is required to supply the header "
              "(this tool never fabricates a signature) unless --xml-only is given", file=sys.stderr)
        sys.exit(1)
    template_raw = Path(args.template).read_bytes()
    c = container.parse(template_raw)
    unwrapped = container.reseal(c.header, xml)
    outer = container.pack_outer(unwrapped)
    Path(args.out).write_bytes(outer)
    ok = container.verify_digest(unwrapped)
    print(f"wrote container ({len(outer)} bytes) to {args.out} -- digest {'OK' if ok else 'FAILED'}; "
          f"signature is UNCHANGED/STALE from the template, as always (see module docstring)")


def main():
    p = argparse.ArgumentParser(prog="caltool", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="parse a container or .calovride file to JSON")
    s.add_argument("file")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("explain", help="print the CalDef definition for a calibration name")
    s.add_argument("name")
    s.set_defaults(func=cmd_explain)

    s = sub.add_parser("search", help="search CalDef names by substring")
    s.add_argument("substring")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("groups", help="list all known CalDef groups")
    s.set_defaults(func=cmd_groups)

    s = sub.add_parser("group", help="list all CalDef entries in one group")
    s.add_argument("name")
    s.set_defaults(func=cmd_group)

    s = sub.add_parser("set", help="change an existing entry's value in an ingested JSON file, in place")
    s.add_argument("file")
    s.add_argument("name", help="CalDef name or literal CalID")
    s.add_argument("value")
    s.add_argument("--i-understand-the-safety-risk", action="store_true",
                    help="required to edit an entry from a never-shipped chime/safety CalDef group "
                         "(see caltool.caldef.NEVER_SHIPPED_SAFETY_GROUPS and CALIBRATION_CUSTOMIZATION_GUIDE.md §3)")
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("add", help="add a CalID absent from the JSON file (scalar types only via CLI)")
    s.add_argument("file")
    s.add_argument("name", help="CalDef name (looked up for its CalID/type/version)")
    s.add_argument("value")
    s.add_argument("--i-understand-the-safety-risk", action="store_true",
                    help="required to add an entry from a never-shipped chime/safety CalDef group "
                         "(see caltool.caldef.NEVER_SHIPPED_SAFETY_GROUPS and CALIBRATION_CUSTOMIZATION_GUIDE.md §3)")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("pack", help="serialize an ingested JSON file back to XML or a full container")
    s.add_argument("file")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--xml-only", action="store_true", help="write only the CalOvride XML, no container/header")
    s.add_argument("--template", help="a genuine container file to borrow the header from (required unless --xml-only)")
    s.set_defaults(func=cmd_pack)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
