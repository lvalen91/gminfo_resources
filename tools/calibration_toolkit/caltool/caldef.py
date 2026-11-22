"""Look up any of the ~215 GM CalDef calibration definitions by name, across every
group defined on this platform -- not just the ones currently shipped in a slot.

CalDef files (.caldef, XML) live outside this repo in the local GIS-646 CalDef
database. Point GMINFO_REPO_ROOT at your checkout of this repo (the directory
containing reference/GIS-646_CalDef_Database_.../caldefs/*.caldef), following the same
env-var convention already used elsewhere in tools/ (see tools/mdi2_client/mdi2/dpdu_replay.py).
Enum label resolution additionally reads the matching .enumdef files in the same directory.

This module is read-only reference lookup -- it does not touch the live radio, CalSets.db,
or any override package.
"""
from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache

CALDEF_GLOB = "reference/GIS-646_CalDef_Database_*/caldefs/*.caldef"
ENUMDEF_GLOB = "reference/GIS-646_CalDef_Database_*/caldefs/*.enumdef"


class CalDefError(ValueError):
    pass


class SafetyGateError(ValueError):
    """Raised when an operation on a never-shipped safety/chime CalDef group is attempted
    without the explicit acknowledgment this toolkit requires for that category."""
    pass


# CalDef groups present in CalSets.db only as untouched base defaults -- never touched by
# any shipped or custom override on this vehicle, per CALIBRATION_CUSTOMIZATION_GUIDE.md §3.
# Anything in these groups requires an explicit, separate acknowledgment before this
# toolkit will add or edit it; see require_safety_ack() below.
NEVER_SHIPPED_SAFETY_GROUPS = frozenset({
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

SAFETY_WARNING = (
    "SAFETY WARNING: {name} belongs to {group}, a CalDef group that has NEVER been shipped "
    "in any stock or custom override on this vehicle -- there is zero bench precedent for "
    "what touching it does. This group governs chime/alert/driver-workload/safety-volume "
    "behavior, not a cosmetic feature. See CALIBRATION_CUSTOMIZATION_GUIDE.md §3 before "
    "proceeding. This toolkit will not add or edit an entry in this group unless you "
    "explicitly acknowledge that warning (--i-understand-the-safety-risk on the CLI, or the "
    "confirmation dialog in the web UI)."
)


def is_safety_restricted(entry: "CalDefEntry") -> bool:
    return entry.group.upper() in NEVER_SHIPPED_SAFETY_GROUPS


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


def _repo_root() -> str:
    root = os.environ.get("GMINFO_REPO_ROOT")
    if not root:
        raise CalDefError(
            "GMINFO_REPO_ROOT is not set. Point it at your gminfo_resources checkout "
            "(the directory containing reference/GIS-646_CalDef_Database_.../)."
        )
    return root


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


@lru_cache(maxsize=1)
def _load_all() -> dict[str, CalDefEntry]:
    root = _repo_root()
    by_name: dict[str, CalDefEntry] = {}
    files = sorted(glob.glob(os.path.join(root, CALDEF_GLOB)))
    if not files:
        raise CalDefError(f"no .caldef files found under {root}/{CALDEF_GLOB} -- check GMINFO_REPO_ROOT")
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
            for c in defn:
                if _local(c.tag) in ALL_VALUE_TYPES:
                    type_elem = c
                    break
            if name is None or cal_id is None or type_elem is None:
                continue
            type_ = _local(type_elem.tag)
            default = type_elem.findtext("Value") or type_elem.findtext("StringValue")
            enum_id = type_elem.findtext("EnumID") if type_ == "Enumeration" else None
            by_name[name] = CalDefEntry(
                name=name, cal_id=cal_id, type_=type_, version=version or "1",
                description=desc, group=group, default_value=default, enum_id=enum_id,
            )
    return by_name


@lru_cache(maxsize=1)
def _load_enum_labels() -> dict[str, dict[str, str]]:
    """{EnumID: {value_str: label}}"""
    root = _repo_root()
    out: dict[str, dict[str, str]] = {}
    for path in sorted(glob.glob(os.path.join(root, ENUMDEF_GLOB))):
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
    return {e.cal_id: e for e in _load_all().values()}


def lookup_by_id(cal_id: str) -> CalDefEntry | None:
    return _by_cal_id().get(cal_id)


def lookup(name: str) -> CalDefEntry:
    entries = _load_all()
    try:
        return entries[name]
    except KeyError as e:
        raise CalDefError(f"no CalDef named {name!r} in the local database") from e


def search(substring: str) -> list[CalDefEntry]:
    substring = substring.lower()
    return [e for e in _load_all().values() if substring in e.name.lower()]


def groups() -> list[str]:
    return sorted({e.group for e in _load_all().values()})


def entries_in_group(group: str) -> list[CalDefEntry]:
    return sorted((e for e in _load_all().values() if e.group == group), key=lambda e: e.name)


def enum_label(enum_id: str | None, value: str) -> str | None:
    if not enum_id:
        return None
    return _load_enum_labels().get(enum_id, {}).get(value)
