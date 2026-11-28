#!/usr/bin/env python3
"""How each ELF file on an image refers to calibrations. x86-64 images; uses `nm` and `objdump` (LLVM).

  native_refs.py CALSETS_DB IMAGE_ROOT OUT_JSON

Per file:
  names / guids      exact strings present in the file
  pointer_table      strings whose address also appears as an 8-byte value in the file (an entry in a pointer table)
  calid_imports      imported `gm::calibrations::CalId::<name>` symbols (libcalmgr exports one per calibration, so a
                     binary can name a calibration without holding its string)
  getters            imported calibration getter functions
  calid_read_set     True when every `CalibrationManager::get(const char*)` call is preceded by a load of a distinct
                     GOT slot and the number of distinct slots equals the number of CalId imports. This shows the
                     imported set is what is read; it does not pair a call site with a name (packed relocations are
                     not decoded here).
  catalog            holds at least 90% of all names (the calibration service and its client library)
No function is decompiled. A string or table entry shows the name is used by the file, not what is done with it.
"""
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import zipfile

db, root, out = sys.argv[1:4]
rows = list(sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True).execute("select _id,CalName from AllCalSets"))
names, ids = {r[1].encode(): r[1] for r in rows}, {r[0].encode(): r[1] for r in rows}
SKIP = {"proc", "sys", "dev", "data", "data_mirror", "mnt", "d", "storage", "sdcard", "apex"}
GETTER = re.compile(r"GMCalibrationManager\d+(get\w+?)E|calibrations18CalibrationManager\d+(get\w*?)E")
CALID = re.compile(r"_ZN2gm12calibrations5CalId(\d+)(\w+)E$")


def loads(b):
    if b[4] != 2:
        return []
    phoff, = struct.unpack_from("<Q", b, 0x20)
    size, num = struct.unpack_from("<HH", b, 0x36)
    res = []
    for i in range(num):
        t, _, off, va, _, fsz, _, _ = struct.unpack_from("<IIQQQQQQ", b, phoff + i * size)
        if t == 1:
            res.append((off, va, fsz))
    return res


def analyse(b, path):
    info = dict(names=sorted({names[t] for t in set(re.findall(rb"[A-Za-z0-9_]{3,}", b)) if t in names}),
                guids=sorted({ids[t] for t in set(re.findall(rb"_[A-Za-z0-9_\-]{21,22}", b)) if t in ids}))
    if b"alibration" not in b and not info["guids"]:
        return info if info["names"] else None
    table = set()
    segs = loads(b)
    for key, cal in list(ids.items()) + list(names.items()):
        if cal not in info["guids"] and cal not in info["names"]:
            continue
        at = b.find(b"\0" + key + b"\0")
        while at >= 0:
            for off, va, fsz in segs:
                if off <= at + 1 < off + fsz and b.find(struct.pack("<Q", va + at + 1 - off)) >= 0:
                    table.add(cal)
            at = b.find(b"\0" + key + b"\0", at + 1)
    info["pointer_table"] = sorted(table)
    if path:
        und = [l.split()[-1] for l in subprocess.run(["nm", "-D", path], capture_output=True, text=True).stdout.splitlines()
               if len(l.split()) >= 2 and l.split()[-2] == "U"]
        info["calid_imports"] = sorted(m.group(2)[:int(m.group(1))] for m in map(CALID.match, und) if m)
        info["getters"] = sorted({(m.group(1) or m.group(2)) for m in map(GETTER.search, und) if m})
        if info["calid_imports"]:
            ins = [l.split(":", 1)[1].strip() for l in subprocess.run(["objdump", "-d", "--no-show-raw-insn", path], capture_output=True,
                   text=True).stdout.splitlines() if re.match(r"\s*[0-9a-f]+:\s", l)]
            slots, calls, bare = set(), 0, 0
            for i, t in enumerate(ins):
                if t.startswith("call") and "CalibrationManager3getEPKc" in t:
                    calls += 1
                    for j in range(i - 1, max(i - 14, 0), -1):
                        m = re.match(r"movq\s+0x[0-9a-f]+\(%rip\), %rdx\s+# (0x[0-9a-f]+)", ins[j])
                        if m or ins[j].startswith(("call", "ret")):
                            break
                    if m:
                        slots.add(m.group(1))
                    else:
                        bare += 1
            info["get_calls"], info["got_slots_before_get"] = calls, len(slots)
            info["calid_read_set"] = bool(calls) and bare == 0 and len(slots) == len(info["calid_imports"])
    return info


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
                for n in z.namelist():
                    if n.endswith(".so"):
                        info = analyse(z.read(n), None)
                        if info:
                            files[f"{rel}!{n}"] = info
                continue
            if os.path.getsize(p) > 400e6:
                continue
            with open(p, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            info = analyse(open(p, "rb").read(), p)
            if info:
                files[rel] = info
        except (OSError, struct.error, zipfile.BadZipFile) as e:
            files[rel] = dict(error=str(e))
for i in files.values():
    i["catalog"] = len(i.get("names", [])) >= 0.9 * len(names)
json.dump(files, open(out, "w"), indent=0)
for rel, i in sorted(files.items(), key=lambda x: -len(x[1].get("names", []) + x[1].get("calid_imports", []))):
    if len(i.get("names", [])) + len(i.get("guids", [])) + len(i.get("calid_imports", [])) >= 3 or i.get("getters"):
        print(f"{rel}: names {len(i.get('names', []))} guids {len(i.get('guids', []))} table {len(i.get('pointer_table', []))} "
              f"CalId imports {len(i.get('calid_imports', []))} getters {i.get('getters')} read-set {i.get('calid_read_set')} catalog {i['catalog']}")
