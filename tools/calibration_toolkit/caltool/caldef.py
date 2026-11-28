"""Look up any of the ~215 GM CalDef calibration definitions by name, across every
group defined on this platform -- not just the ones currently shipped in a slot.

CalDef files (.caldef, XML) are bundled in data/caldefs/, a copy of the GIS-646 CalDef
database (see sync_bundle.py). Set CALTOOL_CALDEF_DIR to read a different caldefs
directory. Enum label resolution reads the matching .enumdef files in the same directory.

This module is read-only reference lookup -- it does not touch the live radio, CalSets.db,
or any override package.
"""
from __future__ import annotations

import copy
import glob
import json
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BUNDLED_CALDEF_DIR = Path(__file__).resolve().parent.parent / "data" / "caldefs"
KNOWN_EFFECTS_FILE = Path(__file__).resolve().parent.parent / "data" / "known_effects.json"


class CalDefError(ValueError):
    pass


class SafetyGateError(ValueError):
    """Raised when an operation on a never-shipped safety/chime CalDef group is attempted
    without the explicit acknowledgment this toolkit requires for that category."""
    pass


# CalDef groups this toolkit treats as elevated-caution: chime/alert/driver-workload/
# security-logging behavior, not cosmetic features. Anything in these groups requires an
# explicit, separate acknowledgment before this toolkit will add or edit it; see
# require_safety_ack() below.
#
# CORRECTED 2026-11-22: these groups were originally documented (CALIBRATION_CUSTOMIZATION_
# GUIDE.md §3) as "never shipped in any stock or custom override on this vehicle." That
# claim was false and has been withdrawn there and here: direct verification against the
# real stock slot04/slot05 LTZ containers found 162 and 5 real shipped entries respectively
# in these groups (seat-belt-reminder and forward-collision-alert chime records under
# GIS631_ConfigChimeProd_StdTheme0_GlobalB, ADASIS_SUPPORT, SAFETY_VOL_OVRD_LEVEL, all four
# GIS509_DriverWorkloadRestrictions entries, SECURITY_EVENT_LOGGING_ENABLED). The gate stays
# -- what it protects against is real regardless of whether GM already ships some of it --
# but the stated reason for caution is "this governs chime/alert/driver-workload/security-
# event behavior," not "nobody has ever touched it."
SAFETY_RESTRICTED_GROUPS = frozenset({
    "GIS604_SAFETYRELATEDVOLUMEGROUPOVERRIDES",
    "GIS604 SAFETYRELATEDVOLUMEGROUPOVERRIDES",  # the on-disk .caldef filename has a literal space
    "GIS631_CONFIGCHIMEPROD_CADTHEME1_GLOBALB",
    "GIS631_CONFIGCHIMEPROD_STDTHEME0_GLOBALB",
    "GIS631_CONFIGSTDCHIMEPROD_GENERICCAL_GLOBALB",
    "GIS631_STANDARDCHIMEPROD_DB_GLOBALB",
    "GLOBALCHIMEGAINCALS",
    "MUTEUNMUTERAMPTIMES",
    "VOLUMEGROUPRAMPTIMES",
    "DRIVINGRESTRICTIONS",
    "GIS509_DRIVERWORKLOADRESTRICTIONS",
    "SFS22_SECURITYEVENTLOGGINGFRD",
    "ADASIS",
})

# Deprecated name -- kept so anything still importing the old identifier doesn't break.
# Use SAFETY_RESTRICTED_GROUPS; the old name asserted a "never shipped" claim that's false.
NEVER_SHIPPED_SAFETY_GROUPS = SAFETY_RESTRICTED_GROUPS

SAFETY_WARNING = (
    "SAFETY WARNING: {name} belongs to {group}, a CalDef group this toolkit treats as "
    "elevated-caution -- it governs chime/alert/driver-workload/safety-volume/security-"
    "logging behavior, not a cosmetic feature. (Some entries in this category of group ARE "
    "already present in stock calibrations; being shipped is not what makes this risky.) "
    "See CALIBRATION_CUSTOMIZATION_GUIDE.md §3 before proceeding. This toolkit will not add "
    "or edit an entry in this group unless you explicitly acknowledge that warning "
    "(--i-understand-the-safety-risk on the CLI, or the confirmation dialog in the web UI)."
)


def is_safety_restricted(entry: "CalDefEntry") -> bool:
    return entry.group.upper() in SAFETY_RESTRICTED_GROUPS


def require_safety_ack(entry: "CalDefEntry", acknowledged: bool) -> None:
    """Call before adding/editing any entry. Raises SafetyGateError if the entry is in a
    never-shipped safety group and `acknowledged` is not True."""
    if is_safety_restricted(entry) and not acknowledged:
        raise SafetyGateError(SAFETY_WARNING.format(name=entry.name, group=entry.group))


@dataclass
class CalDefEntry:
    name: str
    cal_id: str
    type_: str
    version: str
    description: str
    group: str              # the .caldef filename (without extension), e.g. "GIS501_HomeScreenUI"
    default_value: str | None
    enum_id: str | None = None


def caldef_dir() -> str:
    return os.environ.get("CALTOOL_CALDEF_DIR") or str(BUNDLED_CALDEF_DIR)


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


@lru_cache(maxsize=1)
def _load_all_entries() -> list[CalDefEntry]:
    """Every CalDefinition found, across every group, as a flat list. 154 names in the
    real database collide across two different groups (e.g. the same DTC-mask name
    defined once under GIS621_DiagnosticCalDef_GlobalA and again, with a DIFFERENT
    CalID, under GIS643_DiagnosticCalDef_GlobalA) -- keep every one of them here rather
    than silently letting the alphabetically-last file win, which used to make 154 real,
    currently-shipped entries resolve to the wrong group's CalID. See `lookup()` and
    `lookup_in_group()` for how ambiguity is surfaced instead of silently resolved."""
    root = caldef_dir()
    entries: list[CalDefEntry] = []
    files = sorted(glob.glob(os.path.join(glob.escape(root), "*.caldef")))
    if not files:
        raise CalDefError(f"no .caldef files found in {root} -- check the bundle or CALTOOL_CALDEF_DIR")
    skipped_types = set()
    for path in files:
        group = os.path.splitext(os.path.basename(path))[0]
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        for defn in tree.getroot():
            if _local(defn.tag) != "CalDefinition":
                continue
            name = defn.get("Name")
            desc = defn.get("Description", "")
            cal_id = defn.findtext("CalID")
            version = defn.findtext("Version")
            # CalDef files carry an explicit <Type>Boolean</Type> element AND a
            # separately-named <Boolean><Value>...</Value></Boolean> element holding
            # the actual default. Find the latter by matching known type tag names,
            # not by excluding the former.
            from .calovride import ALL_VALUE_TYPES
            type_elem = None
            declared_type = defn.findtext("Type")
            for c in defn:
                if _local(c.tag) in ALL_VALUE_TYPES:
                    type_elem = c
                    break
            if name is None or cal_id is None:
                continue
            if type_elem is None:
                # A real, if rare, case: e.g. StringArray-typed CalDefs whose value
                # element this toolkit doesn't model. Skip rather than silently drop
                # under a wrong assumption -- but say so, once, so it's discoverable.
                if declared_type and declared_type not in skipped_types:
                    skipped_types.add(declared_type)
                continue
            type_ = _local(type_elem.tag)
            default = type_elem.findtext("Value") or type_elem.findtext("StringValue")
            enum_id = type_elem.findtext("EnumID") if type_ == "Enumeration" else None
            entries.append(CalDefEntry(
                name=name, cal_id=cal_id, type_=type_, version=version or "1",
                description=desc, group=group, default_value=default, enum_id=enum_id,
            ))
    return entries


@lru_cache(maxsize=1)
def _by_name() -> dict[str, list[CalDefEntry]]:
    out: dict[str, list[CalDefEntry]] = {}
    for e in _load_all_entries():
        out.setdefault(e.name, []).append(e)
    return out


@lru_cache(maxsize=1)
def _load_enum_labels() -> dict[str, dict[str, str]]:
    """{EnumID: {value_str: label}}"""
    out: dict[str, dict[str, str]] = {}
    for path in sorted(glob.glob(os.path.join(glob.escape(caldef_dir()), "*.enumdef"))):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        for enum_def in tree.getroot():
            if _local(enum_def.tag) != "EnumDefinition":
                continue
            enum_id = enum_def.findtext("EnumID")
            if not enum_id:
                continue
            labels = {}
            for member in enum_def:
                if _local(member.tag) != "EnumValueDefinition":
                    continue
                val = member.findtext("Value")
                label = member.get("Name")
                if val is not None and label is not None:
                    labels[val] = label
            if labels:
                out[enum_id] = labels
    return out


@lru_cache(maxsize=1)
def _by_cal_id() -> dict[str, CalDefEntry]:
    # CalIDs are GM's own globally-unique GUIDs; no collision has been observed here
    # (unlike names, which do collide across groups -- see _load_all_entries()).
    return {e.cal_id: e for e in _load_all_entries()}


def lookup_by_id(cal_id: str) -> CalDefEntry | None:
    return _by_cal_id().get(cal_id)


def lookup(name: str) -> CalDefEntry:
    """Look up a CalDef by name. Raises CalDefError if the name is unknown, OR if it's
    ambiguous (defined under more than one group with a different CalID) -- callers that
    hit the ambiguous case must disambiguate via lookup_in_group(name, group) or by using
    the literal CalID directly, rather than silently getting whichever group happened to
    load last."""
    matches = _by_name().get(name)
    if not matches:
        raise CalDefError(f"no CalDef named {name!r} in the local database")
    if len(matches) > 1:
        groups_str = ", ".join(sorted(f"{e.group} ({e.cal_id})" for e in matches))
        raise CalDefError(
            f"{name!r} is ambiguous -- defined under {len(matches)} different groups with "
            f"different CalIDs: {groups_str}. Use lookup_in_group(name, group), or the "
            f"literal CalID, to disambiguate."
        )
    return matches[0]


def lookup_in_group(name: str, group: str) -> CalDefEntry:
    matches = [e for e in _by_name().get(name, []) if e.group == group]
    if not matches:
        raise CalDefError(f"no CalDef named {name!r} in group {group!r}")
    return matches[0]


def search(substring: str) -> list[CalDefEntry]:
    substring = substring.lower()
    return [e for e in _load_all_entries() if substring in e.name.lower()]


def groups() -> list[str]:
    return sorted({e.group for e in _load_all_entries()})


def entries_in_group(group: str) -> list[CalDefEntry]:
    return sorted((e for e in _load_all_entries() if e.group == group), key=lambda e: e.name)


def enum_label(enum_id: str | None, value: str) -> str | None:
    if not enum_id:
        return None
    return _load_enum_labels().get(enum_id, {}).get(value)


# ------------------------------------------------------------------ known effects ---
# Reverse-engineered findings about what a calibration does on the device. This is a
# separate source from the CalDef database above (GM's own definitions) and is never
# merged into a CalDefEntry. Read-only; nothing here is consulted by the safety gate or
# by any edit or export path.

@lru_cache(maxsize=1)
def _load_known_effects() -> dict:
    """The bundled snapshot of research/calibration-map (see build_known_effects.py).
    A missing or unreadable snapshot yields no findings rather than an error: lookups,
    loading and export must keep working without it."""
    try:
        doc = json.loads(KNOWN_EFFECTS_FILE.read_text(encoding="utf-8"))
        doc["entries"], doc["rules"], doc["source"]  # noqa: B018 -- shape check
    except (OSError, ValueError, KeyError, TypeError):
        return {"entries": {}, "rules": {}, "source": {}}
    return doc


def _group_key(group: str) -> str:
    # The map spells CalDef groups upper-case with every non-alphanumeric as "_"
    # ("GIS604 SafetyRelatedVolumeGroupOverrides" -> "GIS604_SAFETYRELATEDVOLUMEGROUPOVERRIDES").
    return "".join(c if c.isalnum() else "_" for c in group.upper())


def known_effect(name: str, group: str | None = None) -> dict | None:
    """What the calibration-map research records about `name`, or None.

    None is the normal answer: most calibrations have no traced behaviour, and nothing
    is made up for them. `group` (a CalDefEntry.group) guards names defined in two
    groups: the map keys rows by name, so a row is returned only for the group it
    was recorded under.

    The result keeps three kinds of evidence apart:
      status / rules[].level / value_effect  -- from the calibration map: `status` is the
          row's map status verbatim; each rule's `level` is "traced" (code connects the
          setting to the effect) or "observed" (a saved log or owner record shows it)
      predicted                              -- "predicted, untested": reasoned in one chat
          session, not part of the map, not run on hardware. None for most entries.
    `image` and `bench` are the values the map recorded, not values from any loaded file.
    """
    doc = _load_known_effects()
    row = doc["entries"].get(name)
    if row is None:
        return None
    if group is not None and row.get("caldef") and _group_key(group) != row["caldef"]:
        return None
    rules = [{"id": rid, **doc["rules"][rid]} for rid in row.get("rules", []) if rid in doc["rules"]]
    return copy.deepcopy({
        "name": name,
        "source": "calibration map (reverse-engineered; not GM's CalDef description)",
        "firmware": doc["source"].get("firmware"),
        "status": row["status"],
        "basis": row.get("basis"),
        "caldef_group": row.get("caldef"),
        "image": row.get("image"),
        "bench": row.get("bench"),
        "bench_slot": row.get("bench_slot"),
        "bench_part": row.get("bench_part"),
        "rules": rules,
        "value_effect": row.get("value_effect"),
        "predicted": row.get("predicted"),
    })


def known_effect_summary(name: str, group: str | None = None) -> str | None:
    """One line for listings: the map status, plus a marker when a predicted/untested
    note exists. None when known_effect() is None."""
    ke = known_effect(name, group)
    if ke is None:
        return None
    return ke["status"] + (f" + {ke['predicted']['evidence']} note" if ke["predicted"] else "")


def known_effect_text(ke: dict | None) -> str | None:
    """Plain-text rendering of a known_effect() result for the detail views of the
    interactive UIs. Every block is labelled with its evidence."""
    if ke is None:
        return None
    lines = [f"Calibration map ({ke['firmware']}) -- reverse-engineered, not GM's description.",
             f"Map status: {ke['status']}. Recorded values: image {ke['image']}, bench {ke['bench']}."]
    if ke["value_effect"]:
        lines.append(f"Value effect: {ke['value_effect']}")
    for r in ke["rules"]:
        lines.append(f"[{r['level']}] {r['feature']} ({r['id']}): {r['effect']}. When: {r['expr']}"
                     + (f" Note: {r['note']}" if r["note"] else ""))
    p = ke["predicted"]
    if p:
        lines.append(f"[{p['evidence'].upper()} -- {p['kind']}; not from the calibration map] {p['text']}")
        lines += [f"  Uncertain: {u}" for u in p["uncertainties"]]
        if p["suggested_test"]:
            lines.append(f"  Suggested test: {p['suggested_test']}")
    return "\n".join(lines)
