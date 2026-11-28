#!/usr/bin/env python3
"""Calibration names (8 characters or longer) and row GUIDs found in image files that are neither ELF nor dex-bearing packages:
XML and text configuration, tuning-file names, databases.

  config_files.py CALSETS_DB IMAGE_ROOT OUT_JSON

The calibration database itself and any file with only one generic word are left to the reader to judge; the output
lists every hit. A hit shows a file is keyed by the same name, not that the calibration is read.
"""
import json
import os
import re
import sqlite3
import sys

db, root, out = sys.argv[1:4]
rows = list(sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True).execute("select _id,CalName from AllCalSets"))
names = {r[1].encode() for r in rows if len(r[1]) >= 8}
ids = {r[0].encode(): r[1] for r in rows}
SKIP = {"proc", "sys", "dev", "data", "data_mirror", "mnt", "d", "storage", "sdcard", "apex"}
found, read = {}, 0
for base, dirs, files in os.walk(root):
    if base == root:
        dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        p = os.path.join(base, f)
        if os.path.islink(p) or not os.path.isfile(p) or f.endswith((".apk", ".jar", ".vdex", ".odex", ".art", ".oat", "CalSets.db")):
            continue
        try:
            if os.path.getsize(p) > 200e6:
                continue
            data = open(p, "rb").read()
        except OSError:
            continue
        if data[:4] == b"\x7fELF":
            continue
        read += 1
        hit = {h.decode() for h in set(re.findall(rb"[A-Za-z0-9_]{8,}", data)) & names}
        hit |= {ids[g] for g in set(re.findall(rb"_[A-Za-z0-9_\-]{21,22}", data)) if g in ids}
        if hit:
            found[os.path.relpath(p, root)] = sorted(hit)
json.dump(found, open(out, "w"), indent=0)
print("files read", read, "| with a calibration name", len(found))
