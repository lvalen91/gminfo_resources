#!/usr/bin/env python3
"""caltool -- command-line interface for the GM CalOvride calibration toolkit.

Agent/LLM-friendly: every subcommand that emits data defaults to JSON on stdout, and
every subcommand that takes an edit takes it as plain arguments -- no interactive
prompts, nothing is required that can't be scripted.

Signature/live-hardware acceptance is explicitly OUT OF SCOPE (see caltool/container.py
and docs/CALIBRATION_CUSTOMIZATION_GUIDE.md). This tool produces
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


# Canonical JSON shape for an Override lives in caltool.calovride (to_jsonable/
# from_jsonable) -- shared with the web API so there's one place that knows how to
# round-trip every type, including the structured ones.
_entry_to_json = calovride.to_jsonable
_entry_from_json = calovride.from_jsonable


def cmd_ingest(args):
    raw = Path(args.file).read_bytes()
    c = container.parse_any(raw)
    if c is not None:
        xml = c.inner_xml
        meta = {"slot": c.slot, "alpha_code": c.alpha_code, "part_number": c.part_number, "digest_ok": c.digest_ok}
        if not c.digest_ok:
            print("warning: this container's stored payload digest does NOT match its actual content "
                  "-- it was tampered with or corrupted after signing; treat its values with suspicion",
                  file=sys.stderr)
    else:
        xml = raw
        meta = {"slot": None, "alpha_code": None, "part_number": None, "digest_ok": None}
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
    known = caldef.groups()
    if args.name not in known:
        print(f"warning: {args.name!r} is not a known group name (case-sensitive) -- "
              f"this will print an empty list; run 'caltool groups' to see valid names", file=sys.stderr)
    entries = caldef.entries_in_group(args.name)
    print(json.dumps([{"name": e.name, "type": e.type_, "default": e.default_value,
                        "description": e.description} for e in entries], indent=2))


def _resolve_existing_entry(entries: list, name: str):
    """Find the entry in an already-ingested list whose CalID is literally `name`, OR
    whose CalDef resolves (by its OWN CalID, looked up in reverse) to a CalDef named
    `name`. Reverse resolution is what lets this work correctly even when `name` is
    ambiguous as a forward lookup (154 real CalDef names collide across two groups) --
    the entry already in the file has a known-correct CalID, so there's nothing to
    disambiguate. Returns (entry, CalDefEntry|None) or (None, None) if not found."""
    for e in entries:
        if e.cal_id == name:
            return e, caldef.lookup_by_id(e.cal_id)
        de = caldef.lookup_by_id(e.cal_id)
        if de and de.name == name:
            return e, de
    return None, None


def cmd_set(args):
    entries_json = json.loads(Path(args.file).read_text())
    entries = [_entry_from_json(d) for d in entries_json["entries"]]
    entry, de = _resolve_existing_entry(entries, args.name)
    if entry is None:
        print(f"error: {args.name!r} not present in {args.file} -- use 'add' to introduce a new CalID", file=sys.stderr)
        sys.exit(1)
    if de:
        caldef.require_safety_ack(de, args.i_understand_the_safety_risk)
        calovride.validate_value(de.type_, args.value)
    else:
        calovride.validate_value(entry.type_, args.value)
    entry.value = args.value
    entries_json["entries"] = [_entry_to_json(e) for e in entries]
    entries_json["entry_count"] = len(entries)
    Path(args.file).write_text(json.dumps(entries_json, indent=2))
    print(f"set {args.name} = {args.value!r} in {args.file}")


def cmd_add(args):
    de = caldef.lookup(args.name)
    caldef.require_safety_ack(de, args.i_understand_the_safety_risk)
    calovride.validate_value(de.type_, args.value)
    entries_json = json.loads(Path(args.file).read_text()) if Path(args.file).exists() else \
        {"meta": {"slot": None, "alpha_code": None, "part_number": None}, "entries": []}
    entries = [_entry_from_json(d) for d in entries_json["entries"]]
    if any(e.cal_id == de.cal_id for e in entries):
        print(f"error: {args.name!r} already present -- use 'set' to change it", file=sys.stderr)
        sys.exit(1)
    entries.append(calovride.Override(de.cal_id, de.version, de.type_, args.value))
    entries_json["entries"] = [_entry_to_json(e) for e in entries]
    entries_json["entry_count"] = len(entries)
    Path(args.file).write_text(json.dumps(entries_json, indent=2))
    print(f"added {args.name} ({de.group}) = {args.value!r} to {args.file}")


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
    c = container.parse_any(template_raw)
    if c is None:
        print(f"error: {args.template} is not a recognized CSM container (gzip-wrapped or unwrapped)", file=sys.stderr)
        sys.exit(1)
    meta = entries_json.get("meta", {})
    if meta.get("slot") is not None and meta["slot"] != c.slot:
        print(f"warning: this JSON's entries came from slot {meta['slot']}, but --template is slot "
              f"{c.slot} -- packing {meta['slot']}-slot content under a {c.slot}-slot header", file=sys.stderr)
    unwrapped = container.reseal(c.header, xml)
    outer = container.pack_outer(unwrapped)
    Path(args.out).write_bytes(outer)
    ok = container.verify_digest(unwrapped)
    print(f"wrote container ({len(outer)} bytes) to {args.out} -- digest {'OK' if ok else 'FAILED'}; "
          f"signature is UNCHANGED/STALE from the template, as always (see module docstring)")


def main():
    # allow_abbrev=False matters here specifically: without it, a typo'd/truncated
    # "--i" or "--i-u" silently satisfies the full --i-understand-the-safety-risk flag,
    # defeating the one piece of friction the safety gate is supposed to add.
    p = argparse.ArgumentParser(prog="caltool", description=__doc__.split("\n\n")[0], allow_abbrev=False)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="parse a container or .calovride file to JSON", allow_abbrev=False)
    s.add_argument("file")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("explain", help="print the CalDef definition for a calibration name", allow_abbrev=False)
    s.add_argument("name")
    s.set_defaults(func=cmd_explain)

    s = sub.add_parser("search", help="search CalDef names by substring", allow_abbrev=False)
    s.add_argument("substring")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("groups", help="list all known CalDef groups", allow_abbrev=False)
    s.set_defaults(func=cmd_groups)

    s = sub.add_parser("group", help="list all CalDef entries in one group", allow_abbrev=False)
    s.add_argument("name")
    s.set_defaults(func=cmd_group)

    s = sub.add_parser("set", help="change an existing entry's value in an ingested JSON file, in place", allow_abbrev=False)
    s.add_argument("file")
    s.add_argument("name", help="CalDef name or literal CalID")
    s.add_argument("value")
    s.add_argument("--i-understand-the-safety-risk", action="store_true",
                    help="required to edit an entry from an elevated-caution chime/safety CalDef group "
                         "(see caltool.caldef.SAFETY_RESTRICTED_GROUPS and CALIBRATION_CUSTOMIZATION_GUIDE.md §3)")
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("add", help="add a CalID absent from the JSON file (scalar types only via CLI)", allow_abbrev=False)
    s.add_argument("file")
    s.add_argument("name", help="CalDef name (looked up for its CalID/type/version)")
    s.add_argument("value")
    s.add_argument("--i-understand-the-safety-risk", action="store_true",
                    help="required to add an entry from an elevated-caution chime/safety CalDef group "
                         "(see caltool.caldef.SAFETY_RESTRICTED_GROUPS and CALIBRATION_CUSTOMIZATION_GUIDE.md §3)")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("pack", help="serialize an ingested JSON file back to XML or a full container", allow_abbrev=False)
    s.add_argument("file")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--xml-only", action="store_true", help="write only the CalOvride XML, no container/header")
    s.add_argument("--template", help="a genuine container file to borrow the header from (required unless --xml-only)")
    s.set_defaults(func=cmd_pack)

    args = p.parse_args()
    try:
        args.func(args)
    except (calovride.CalOvrideError, caldef.CalDefError, caldef.SafetyGateError,
            container.ContainerError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"error: not valid JSON -- {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"error: malformed entries JSON (expected keys cal_id/version/type/value on every "
              f"entry) -- {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"error: not a text/JSON file where one was expected -- {e}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
        print(f"error: {e.strerror} -- {e.filename}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
