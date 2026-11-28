#!/usr/bin/env python3
"""Rebuild map.json and check every rule anchor against decompiled Y175 sources.

  build_map.py SCOPE_JSON VALUES_JSON READS_JSON DECOMPILED_ROOT [--root DIR ...]
               [--db CALSETS_DB --sites SITES_JSON --packages PACKAGES_JSON --native NATIVE_JSON
                [--config CONFIG_JSON] [--logs LOGS_JSON]]
               [--groups-md FILE]

DECOMPILED_ROOT and each --root hold <app>/sources/ trees (jadx). The first four inputs drive the first-slice pass.
The --db group adds the wide pass over every row of the calibration database: tools/java_sites.py, tools/scan_image.py,
tools/native_refs.py, tools/config_files.py and tools/log_mentions.py produce its inputs. Inputs are derived from firmware and are not stored
here. --groups-md writes the per-group status table used in README.md.
"""
import argparse
import collections
import json
import os
import pathlib
import re
import sqlite3
import sys

from rules import ENUM_KEYS, RULES, TABLES, VALUE_EFFECTS, WRAPPERS

STATUSES = ["effect traced", "read, effect not traced", "mentioned in decompiled Java, read not established",
            "name only", "not found outside bulk lists"]
READ_KINDS = {"read", "read-via-constant", "read-via-wrapper", "read-via-table"}
MENTION_KINDS = {"table", "constant", "compare", "mention"}

# README sections; every CalDef group belongs to one family (prefix match, first hit wins).
FAMILIES = [
    ("Home screen and launcher", ["GIS501_", "GIS511_", "GIS674_", "GIS538_", "GIS521_", "GIS1000_"]),
    ("Projection, connections, Wi-Fi, Bluetooth, phone", ["GIS337_", "GIS513_", "WIFIINFO3", "GIS512_", "BLUETOOTH", "HANDSFREE", "GIS503_", "USB"]),
    ("Audio processing, volume, chimes", ["VEHICLESPECIFICEQ", "SINKLEVEL", "AOSP", "DISTORTION", "ROOMMODE", "GM_SR_", "REQUESTACTIONMAP",
                                          "VOLUMEGROUP", "MUTEUNMUTE", "FRONTZONE", "CODEC", "AMPINTERFACE", "AUDIOHMICALS", "DIRECTIONALAUDIO",
                                          "GIS604_", "TELEMATICSAUDIO", "GIS999_", "GIS1001_", "GIS631_", "GLOBALCHIME", "BRANDANIMATIONS"]),
    ("Tuner", ["GIS502_", "GIS653_", "GIS655_", "GIS605_", "GIS625_", "GIS756_"]),
    ("Camera and video", ["FRONTREARCAMERA", "GIS738_", "GIS742_", "GIS1016_", "IMAGE_ENHANCEMENT", "VIDEO_DECODER", "GIS608_", "GIS942_"]),
    ("Diagnostics", ["GIS641_", "GIS621_", "GIS888_", "GIS642_", "CSM_ON_BOARD", "CSM2IPCORTCP", "ODI", "ECUACTIVITY"]),
    ("System state, display, controls", ["GIS618_", "GIS619_", "DISPLAYGESTURES", "FACEPLATE", "STEERINGWHEEL", "GIS652_", "GIS549_", "TOUCHCONTROLLER",
                                         "GIS309_", "CANHANDLER", "GARAGEMODE", "GIS611_", "GIS651_", "CUSTOMIZATIONGATEWAY"]),
    ("Climate, seats, energy, trailering, vehicle apps", ["GIS550_", "GIS1050_", "GIS551_", "GIS517_", "GIS520_", "HYBRID", "OFFROADAPP", "GIS539_",
                                                          "GIS516_", "DRIVEMODE", "HMIEXTERNAL", "GIS1062_"]),
    ("Navigation and location", ["NAVAPP", "GNSS_DR", "ADASIS", "GIS504_"]),
    ("Speech", ["SPEECHRECOGNITION", "GIS350_", "GIS582_", "GIS696_"]),
    ("Settings, personalization, accounts, restrictions", ["GIS507_", "GIS1007_", "GIS508_", "SFS", "GIS1008_", "GIS525_", "GIS524_", "GIS1024_",
                                                           "DRIVINGRESTRICTIONS", "GIS509_"]),
    ("Connected services and updates", ["REMOTESERVER", "GIS668_", "GIS887_", "GIS864_", "GIS697_", "GIS658_", "GIS1009_", "GIS505_", "GIS506_",
                                        "GIS675_", "PARTNERAPPS", "GIS609_"]),
    ("Vehicle identity and region", ["GLOBAL_INFO3", "LANGUAGEANDREGION", "GIS500_"]),
]


def family(group):
    return next((f for f, prefixes in FAMILIES if group.startswith(tuple(prefixes))), "Unassigned")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("scope"), ap.add_argument("values"), ap.add_argument("reads"), ap.add_argument("decompiled_root")
ap.add_argument("--root", action="append", default=[])
for opt in ("db", "sites", "packages", "native", "logs", "config", "groups-md"):
    ap.add_argument(f"--{opt}")
args = ap.parse_args()
scope, values, reads = (json.load(open(p)) for p in (args.scope, args.values, args.reads))
roots = [pathlib.Path(p) for p in [args.decompiled_root] + args.root]


def source(app, rel, plain=False):
    sub = rel[1:] if rel.startswith("@") else rel if plain else "com/gm/" + rel
    for root in roots:
        path = root / app / "sources" / sub
        if path.is_file():
            return path.read_text(errors="replace")
    return None


failed = []
for r in RULES:
    for app, rel, text in r["anchors"]:
        if text not in (source(app, rel) or ""):
            failed.append(f"{r['id']}: {app}/{rel}: {text}")
for name, (_, app, rel) in VALUE_EFFECTS.items():
    if not re.search(rf'"{re.escape(name)}"|\bCalId\.{re.escape(name)}\b', source(app, rel) or ""):
        failed.append(f"value effect {name}: {app}/{rel}")
for table, where in ((WRAPPERS, "wrapper"), (TABLES, "table")):
    for (app, rel), value in table.items():
        text = value[1] if where == "wrapper" else value
        if text not in (source(app, rel, plain=True) or ""):
            failed.append(f"{where} {app}/{rel}: {text}")

for (app, rel), (_, _, text, getter_rel) in ENUM_KEYS.items():
    if source(app, rel, plain=True) is None or text not in (source(app, getter_rel, plain=True) or ""):
        failed.append(f"enum catalog {app}/{rel}: {text}")

info = {r["name"]: r for r in scope}
first_slice = set(info)
for r in RULES:
    if not r["id"].startswith(("icon.", "settings.", "time.", "tuner.", "trailer.")):  # these rule families belong to the wide pass
        for token in re.findall(r"[A-Za-z_]\w*", r["expr"]):
            if token in values:
                first_slice.add(token)

wide = bool(args.db)
in_config = collections.defaultdict(list)
rows, sites, packages, native, logs = {}, {}, {}, {}, {}
if wide:
    con = sqlite3.connect(f"file:{args.db}?mode=ro&immutable=1", uri=True)
    rows = {n: dict(caldef=d, type=t) for n, d, t in con.execute("select CalName,CalDefFileName,CalType from AllCalSets")}
    sites, packages, native = (json.load(open(p)) for p in (args.sites, args.packages, args.native))
    logs = json.load(open(args.logs)) if args.logs else {}
    for rel, found in (json.load(open(args.config)) if args.config else {}).items():
        for n in found:
            in_config[n].append(rel)

# Non-catalog packages and native files naming each calibration.
in_java, in_native = collections.defaultdict(set), collections.defaultdict(dict)
for rel, i in packages.items():
    if i.get("kind") == "package" and not i.get("catalog"):
        for n in set(i["names"]) | set(i["guids"]):
            in_java[n].add(os.path.basename(rel))
for rel, i in native.items():
    base = os.path.basename(rel)
    if i.get("catalog") or "error" in i:
        continue
    reader = bool(i.get("getters") or i.get("guids") or i.get("calid_imports") or base.startswith("libpal_"))
    for n in i.get("calid_imports", []):
        in_native[n][base] = "calid-import-read-set" if i.get("calid_read_set") else "calid-import"
    if not reader:
        continue  # a bare matching string in an unrelated binary (for example "Search") is treated as coincidence
    for n in set(i.get("names", [])) | set(i.get("guids", [])):
        if base.startswith("libpal_calibrations"):
            how = "pal-table"
        elif n in i.get("pointer_table", []):
            how = "pointer-table"
        else:
            how = "string"
        in_native[n].setdefault(base, how)



def clip(value):
    """Array, record and binary values run to kilobytes; keep the head and the length."""
    return value if value is None or len(value) <= 160 else f"{value[:120]}... ({len(value)} characters)"


settings = {}
for name in sorted(set(values) if wide else first_slice):
    v, row = values[name], info.get(name, {})
    rule_ids = [r["id"] for r in RULES if re.search(rf"\b{re.escape(name)}\b", r["expr"])]
    old = reads.get(name, [])
    new = sites.get(name, [])
    read_sites = {f"{s['file']}:{s['line']}" for s in old if s["kind"].startswith("read")}
    read_sites |= {f"{s['app']}/sources/{s['file']}:{s['line']}" for s in new if s["kind"] in READ_KINDS}
    mentions = [s for s in new if s["kind"] in MENTION_KINDS]
    if not wide:  # the first-slice list has no coincidence filter; the wide pass replaces it
        mentions += [s for s in old if not s["kind"].startswith("read")]
    nat = in_native.get(name, {})
    native_read = sorted(b for b, how in nat.items() if how == "calid-import-read-set")
    java_pkgs = sorted(set(row.get("dex", [])) | in_java.get(name, set()))
    native_files = sorted(set(row.get("native", [])) | set(nat)) if not wide else sorted(nat)
    if rule_ids or name in VALUE_EFFECTS:
        status, basis = STATUSES[0], "hand-traced rule or value effect in rules.py"
    elif read_sites:
        status, basis = STATUSES[1], "typed getter call in decompiled Java"
    elif native_read:
        status, basis = STATUSES[1], "native: imported CalId symbols match the GOT slots passed to CalibrationManager::get (set level)"
    elif mentions:
        kinds = sorted({s["kind"] for s in mentions})
        status, basis = STATUSES[2], "Java " + "/".join(kinds) + " site, no getter call found"
    elif java_pkgs or native_files or name in in_config:
        status = STATUSES[3]
        basis = ("native: " + ", ".join(sorted(set(nat.values()))) if nat else "named in a configuration file" if name in in_config
                 else "string in a non-catalog package, no calibration use found (coincidence possible)")
    else:
        status, basis = STATUSES[4], "only in the generated constant classes, the calibration service and its client library"
    settings[name] = {
        "caldef": row.get("caldef") or rows.get(name, {}).get("caldef"), "type": rows.get(name, {}).get("type"),
        "image": clip(v["base"]), "bench": clip(v["live"]), "bench_slot": v["slot"], "bench_part": v["part"],
        "status": status, "basis": basis, "first_slice": name in first_slice, "rules": rule_ids,
        "value_effect": VALUE_EFFECTS.get(name, [None])[0], "read_sites": sorted(read_sites),
        "mention_sites": sorted({(f"{s['app']}/sources/{s['file']}" if "copies_in" in s else s["file"]) + f":{s['line']}" for s in mentions})[:12],
        "name_in_java": java_pkgs, "name_in_native": native_files, "native_evidence": nat,
        "name_in_config": sorted(in_config.get(name, []))[:6], "log_files": logs.get(name, []),
    }

groups = collections.defaultdict(collections.Counter)
readers = collections.defaultdict(collections.Counter)
for name, s in settings.items():
    g = s["caldef"] or "(row absent from the image database)"
    groups[g][s["status"]] += 1
    for site in s["read_sites"]:
        readers[g][site.split("/")[0]] += 1
    for b in s["name_in_native"]:
        readers[g][b] += 1
NATIVE_EVIDENCE = {
    "calid-import-read-set": "binary imports the CalId symbol; every CalibrationManager::get call takes one of the imported symbols",
    "calid-import": "binary imports the CalId symbol and CalibrationManager::get; call sites not paired",
    "pointer-table": "name or GUID string referenced from a pointer table in a binary that imports a calibration getter",
    "string": "name string in a binary that imports a calibration getter",
    "pal-table": "entry of the table exported by libpal_calibrations.so; no importing binary on the Android image",
}
head = {"firmware": "Y175 code and bench dump values", "statuses": STATUSES, "native_evidence": NATIVE_EVIDENCE,
        "groups": {g: {st: c[st] for st in STATUSES if c[st]} for g, c in sorted(groups.items())},
        "rules": [{k: v for k, v in r.items() if k != "anchors"} | {"anchors": [f"{a}/{p}" for a, p, _ in r["anchors"]]} for r in RULES]}
body = ",\n".join(f'  {json.dumps(n)}: {json.dumps(s, separators=(",", ":"))}' for n, s in settings.items())  # one setting per line
pathlib.Path(__file__).with_name("map.json").write_text(json.dumps(head, indent=1)[:-2] + ',\n "settings": {\n' + body + "\n }\n}\n")

if args.groups_md:
    head = ["| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |", "|---|---|---|---|---|---|---|---|"]
    lines = []
    for fam in [f for f, _ in FAMILIES] + ["Unassigned"]:
        members = sorted((g for g in groups if family(g) == fam), key=lambda g: (-sum(groups[g].values()), g))
        if not members:
            continue
        tot = collections.Counter()
        for g in members:
            tot.update(groups[g])
        lines += [f"### {fam}", "", f"{len(members)} groups, {sum(tot.values())} rows: " + ", ".join(
            f"{tot[st]} {label}" for st, label in zip(STATUSES, ("traced", "read", "mentioned", "name only", "bulk lists only"))) + ".", ""] + head
        for g in members:
            c = groups[g]
            who = ", ".join(f"{a} {n}" for a, n in readers[g].most_common(3)) or "none"
            lines.append(f"| `{g}` | {sum(c.values())} | " + " | ".join(str(c[st]) for st in STATUSES) + f" | {who} |")
        lines.append("")
    pathlib.Path(args.groups_md).write_text("\n".join(lines))

for label, subset in (("all settings", settings), ("first slice", {n: s for n, s in settings.items() if s["first_slice"]})):
    counts = collections.Counter(s["status"] for s in subset.values())
    print(label, len(subset), {st: counts[st] for st in STATUSES})
print("groups", len(groups), "| rules", len(RULES), "anchors checked", sum(len(r["anchors"]) for r in RULES), "+", len(VALUE_EFFECTS),
      "value effects +", len(WRAPPERS), "wrappers +", len(TABLES), "tables +", len(ENUM_KEYS), "enum catalogs")
for f in failed:
    print("ANCHOR FAILED", f)
sys.exit(1 if failed else 0)
