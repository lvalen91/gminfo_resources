#!/usr/bin/env python3
"""Which packages on a firmware image carry calibration names or GUIDs in their dex string tables.

  scan_image.py CALSETS_DB IMAGE_ROOT OUT_JSON

Reads every .apk/.jar (classes*.dex string tables, exact match) and every .vdex/.odex (raw token match, because
compact dex inside a vdex is not parsed here). A package with no classes*.dex is listed so vdex-only code is visible.
`catalog` marks a file holding at least 90% of all names: it embeds the generated constant classes and proves nothing
about which calibrations it reads.
"""
import json
import os
import re
import sqlite3
import struct
import sys
import zipfile

db, root, out = sys.argv[1:4]
rows = list(sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True).execute("select _id,CalName from AllCalSets"))
names, ids = {r[1] for r in rows}, {r[0]: r[1] for r in rows}
SKIP = {"proc", "sys", "dev", "data", "data_mirror", "mnt", "d", "storage", "sdcard", "apex"}  # /apex duplicates /system/apex


def dex_strings(d):
    if d[:3] != b"dex":
        return
    n, off = struct.unpack_from("<II", d, 0x38)
    for i in range(n):
        p = struct.unpack_from("<I", d, off + 4 * i)[0]
        while d[p] & 0x80:
            p += 1
        p += 1
        yield d[p:d.index(b"\0", p)].decode("utf-8", "replace")


files = {}
for base, dirs, fs in os.walk(root):
    if base == root:
        dirs[:] = [d for d in dirs if d not in SKIP]
    for f in fs:
        p = os.path.join(base, f)
        rel = os.path.relpath(p, root)
        if os.path.islink(p) or not os.path.isfile(p):
            continue
        try:
            if f.endswith((".apk", ".jar")):
                z = zipfile.ZipFile(p)
                dex = [n for n in z.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
                strings = set()
                for n in dex:
                    strings |= set(dex_strings(z.read(n)))
                files[rel] = dict(kind="package", dex=len(dex), names=sorted(strings & names),
                                  guids=sorted(ids[s] for s in strings & set(ids)),
                                  uses_api=any("gm/calibrations/" in s or "gm/compat/calibrations/" in s for s in strings),
                                  native_libs=[n for n in z.namelist() if n.endswith(".so")])
            elif f.endswith((".vdex", ".odex")):
                b = open(p, "rb").read()
                tokens = {m.decode() for m in re.findall(rb"[A-Za-z0-9_\-]{3,}", b)}
                files[rel] = dict(kind=f.rsplit(".", 1)[1], names=sorted(tokens & names), guids=sorted(ids[t] for t in tokens & set(ids)),
                                  has_dex=b"dex\n03" in b, has_cdex=b"cdex" in b)
        except (zipfile.BadZipFile, OSError, struct.error, ValueError) as e:
            files[rel] = dict(kind="error", error=str(e))
for i in files.values():
    i["catalog"] = len(i.get("names", [])) >= 0.9 * len(names)
json.dump(files, open(out, "w"), indent=0)
pk = [i for i in files.values() if i["kind"] == "package"]
print("packages", len(pk), "| without classes.dex", sum(1 for i in pk if not i["dex"]), "| with a name or GUID",
      sum(1 for i in pk if i["names"] or i["guids"]), "| catalogs", sum(1 for i in pk if i["catalog"]),
      "| errors", sum(1 for i in files.values() if i["kind"] == "error"))
