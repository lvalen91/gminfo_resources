#!/usr/bin/env python3
"""Count saved runtime text files (logcat captures, dumpsys, property dumps) that contain each calibration name.

  log_mentions.py CALSETS_DB OUT_JSON DIR [DIR ...]

Names shorter than 8 characters or without an underscore/camel-case boundary are skipped (too generic to attribute).
A hit shows the string was printed at runtime by something; it is not a status change on its own.
"""
import collections
import json
import os
import re
import sqlite3
import sys

db, out, *dirs = sys.argv[1:]
names = {r[0] for r in sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True).execute("select CalName from AllCalSets")}
names = {n for n in names if len(n) >= 8 and (("_" in n) or re.search(r"[a-z][A-Z]", n))}
TEXT = (".txt", ".log", ".logcat", ".json", ".xml", ".prop", ".out", ".md", "")
hits, seen = collections.defaultdict(list), 0
for d in dirs:
    for base, _, files in os.walk(d):
        for f in files:
            p = os.path.join(base, f)
            if not f.lower().endswith(TEXT[:-1]) and "." in f:
                continue
            try:
                if os.path.getsize(p) > 300e6:
                    continue
                data = open(p, "rb").read()
            except OSError:
                continue
            if b"\0" in data[:4096]:
                continue
            seen += 1
            for t in {m.decode() for m in re.findall(rb"[A-Za-z0-9_]{8,}", data)} & names:
                hits[t].append(os.path.relpath(p, d))
json.dump({k: sorted(v)[:8] for k, v in hits.items()}, open(out, "w"), indent=0)
print("text files read", seen, "| names seen", len(hits))
