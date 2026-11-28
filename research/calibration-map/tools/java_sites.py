#!/usr/bin/env python3
"""Find and classify every place decompiled Java names a calibration.

  java_sites.py CALSETS_DB OUT_JSON DECOMPILED_ROOT [DECOMPILED_ROOT ...]

A calibration can be named four ways: the name as a string literal, `CalId.<name>`, `<GROUP>.<name>_CalID`, or the
row GUID as a string literal (the GUID is what the by-ID API takes; javac inlines it, so only the GUID is in the dex).
Catalog classes (`gm/calibrations/`, `gm/compat/calibrations/`), which list every name, are skipped.

Site kinds, strongest first:
  read               the token is the first argument of a typed getter (getBoolean, getEnumeration, ...)
  read-via-constant  a getter takes an identifier that the same app defines as `String X = "<name>"`
  read-via-wrapper   the token is passed to a method listed in rules.WRAPPERS (hand-checked to forward to a getter)
  read-via-table     the token is an entry of a list in a file listed in rules.TABLES (hand-checked: one loop reads
                     every entry)
  table              the token is an element of a list, map, array or constructor call
  constant           `String X = "<name>"`
  compare            equals()/case label
  mention            anything else in a file or app that uses calibrations
  unrelated-literal  the literal sits in code with no calibration link (e.g. "Search" in a UI toolkit), or is a
                     `CalId.<name>` that jadx substituted for an equal plain string in a file with no other
                     calibration reference; not counted

`receiver` on a read says whether the object the getter is called on was resolved to a calibration manager type
("typed": a cast, a declaration in the same file, a declaration elsewhere in the app under a name of two or more
characters, or `Class.x` where that class declares `x`), only sits in a file that uses calibrations ("file"), or was
accepted because the token is a CalId/GUID form ("token").
This is pattern matching on decompiler output, not data-flow analysis.
"""
import collections
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from rules import TABLES, WRAPPERS  # noqa: E402

db, out_path, *roots = sys.argv[1:]
rows = list(sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True).execute("select _id,CalName from AllCalSets"))
names, ids = {r[1] for r in rows}, {r[0]: r[1] for r in rows}
G = (r"(?:Boolean|Int|Integer|Float|Double|Enumeration|Enum|String|Long|Byte|Short|IntegerArray|IntArray|FloatArray|"
     r"StringArray|EnumArray|EnumIntegerMap|EnumFloatMap|Record|RecordLegacy|BinaryFile|CalInfo)")
TOKEN = re.compile(r'"([^"\\]{3,80})"|\bCalId\.(\w+)|\b[A-Z][A-Z0-9_a-z]*\.(\w+?)_CalID\b')
GETTER = re.compile(r"\.get" + G + r"\(\s*(?:\(String\)\s*)?$")
CATALOG = re.compile(r"(^|/)gm/(compat/)?calibrations/")
RELATED = re.compile(r"alibration|CalId|_CalID|[cC]alManager|[cC]alMgr")
RELATED_STRICT = re.compile(r"alibration|_CalID|[cC]alManager|[cC]alMgr")
MANAGER_DECL = re.compile(r"\b(?:CalibrationManager|GMCalibrationsManager|CalibrationShadow|CalibrationManagerClient)\s+(\w+)\s*[;=(,)]")
THIRD_PARTY = re.compile(r"^(androidx?|kotlinx?|com/google|com/android/internal|vendor/gm/vehicle|okhttp3|io/|org/)")
CONSTDEF = re.compile(r"\bString\s+(\w+)\s*=\s*$")
TABLE = re.compile(r"(\bnew\s+[\w.<>]+\(\s*([^()]*,\s*)?$)|(\.(add|put|of|asList|listOf|mapOf|to)\(\s*([^()]*,\s*)?$)|([{,]\s*$)|(^\s*$)|(^\s*\w+\(\s*$)")
COMPARE = re.compile(r"(\.equals(IgnoreCase)?\(\s*$)|(\bcase\s+$)|([!=]=\s*$)")
PRIORITY = ["info3", "services", "framework"]

apps = {}
for root in roots:
    for app in sorted(os.listdir(root)):
        if os.path.isdir(os.path.join(root, app, "sources")):
            apps[app] = os.path.join(root, app, "sources")

sites = collections.defaultdict(list)
digests, stats = {}, collections.Counter()
for app, src in apps.items():
    app_decl, app_const, pending, texts = set(), {}, [], {}
    tables = {rel for (a, rel) in TABLES if a == app}
    wrappers = {m: rel for (a, rel), (methods, _) in WRAPPERS.items() if a == app for m in methods}
    for base, _, files in os.walk(src):
        sub = os.path.relpath(base, src).replace(os.sep, "/") + "/"
        for fn in files:
            if not fn.endswith(".java"):
                continue
            stats["java files"] += 1
            if CATALOG.search(sub):
                stats["catalog files skipped"] += 1
                continue
            path = os.path.join(base, fn)
            try:
                text = open(path, errors="replace").read()
            except OSError:
                continue
            decl = set(MANAGER_DECL.findall(text))
            app_decl |= {d for d in decl if len(d) >= 2} | {(fn[:-5], d) for d in decl}
            if not TOKEN.search(text):
                if RELATED.search(text):
                    texts[sub + fn] = text
                continue
            texts[sub + fn] = text
            related = bool(RELATED.search(text))
            strict = bool(RELATED_STRICT.search(re.sub(r"import gm\.(compat\.)?calibrations\.CalId;", "", text)))
            for no, line in enumerate(text.split("\n"), 1):
                for m in TOKEN.finditer(line):
                    lit, cid, gid = m.groups()
                    if lit is not None:
                        cal, via = (lit, "literal") if lit in names else (ids.get(lit), "guid")
                    elif cid:
                        cal, via = (cid if cid in names else None), "CalId"
                    else:
                        cal, via = (gid if gid in names else None), "CalID-const"
                    if cal:
                        pending.append((sub + fn, no, line, m.start(), m.end(), cal, via, related, strict, decl))
    for rel, no, line, a, b, cal, via, related, strict, decl in pending:
        pre = re.sub(r"(gm\.calibrations\.|gm\.compat\.calibrations\.)$", "", line[:a])
        post, extra = line[b:], {}
        third = bool(THIRD_PARTY.match(rel))
        if GETTER.search(pre):
            recv = pre[:pre.rfind(".get")][-90:]
            words = re.findall(r"\w+", recv)
            last = words[-1:] or [""]
            if "alibration" in recv or last[0] in decl or last[0] in app_decl or tuple(words[-2:]) in app_decl:
                extra["receiver"] = "typed"
            elif via != "literal":
                extra["receiver"] = "token"
            elif related:
                extra["receiver"] = "file"
            kind = "read" if "receiver" in extra else "unrelated-literal"
            fb = re.match(r"\s*,\s*([^;]*?)\)(?:\s*[;)?:&|=!<>]|\s*$)", post)
            extra["fallback"] = fb.group(1).strip() if fb else None
        else:
            call = re.search(r"\b(\w+)\(\s*(?:\(String\)\s*)?$", pre)
            if call and call.group(1) in wrappers and not re.search(r"\bnew\s+\w+\($", pre):
                kind, extra = "read-via-wrapper", {"wrapper": f"{wrappers[call.group(1)]}#{call.group(1)}"}
            elif CONSTDEF.search(pre) and via in ("literal", "guid"):
                kind = "constant"
                app_const[CONSTDEF.search(pre).group(1)] = cal
            elif COMPARE.search(pre) or re.match(r"\s*\.equals\(", post):
                kind = "compare"
            elif TABLE.search(pre):
                kind = "read-via-table" if rel in tables else "table"
            else:
                kind = "mention"
            if via == "literal" and (third or not (related or rel.startswith("com/gm/") or app.startswith("GM"))):
                kind = "unrelated-literal"
            # In a package that bundles the CalId class, jadx prints any equal string literal as CalId.<name>.
            if via == "CalId" and not strict and kind != "read-via-wrapper":
                kind = "unrelated-literal"
        sites[cal].append(dict(app=app, file=rel, line=no, via=via, kind=kind, code=line.strip()[:260], **extra))
        digests[(app, rel)] = hashlib.sha1(texts[rel].encode()).hexdigest()
    if app_const:
        pat = re.compile(r"\.get" + G + r"\(\s*(?:[\w.]+\.)?(" + "|".join(map(re.escape, sorted(app_const, key=len, reverse=True))) + r")\s*[,)]")
        for rel, text in texts.items():
            if not pat.search(text) or not RELATED.search(text):
                continue
            for no, line in enumerate(text.split("\n"), 1):
                for m in pat.finditer(line):
                    sites[app_const[m.group(1)]].append(dict(app=app, file=rel, line=no, via="constant", kind="read-via-constant",
                                                             code=line.strip()[:260], const=m.group(1)))
                    digests[(app, rel)] = hashlib.sha1(text.encode()).hexdigest()

# Byte-identical copies of one source file bundled into several packages are one site with `copies_in`.
out = {}
for cal, found in sites.items():
    groups = collections.defaultdict(list)
    for s in found:
        groups[(s["file"], s["line"], s["kind"], digests[(s["app"], s["file"])])].append(s)
    merged = []
    for group in groups.values():
        group.sort(key=lambda s: (PRIORITY.index(s["app"]) if s["app"] in PRIORITY else 99, s["app"]))
        merged.append(dict(group[0], copies_in=sorted({x["app"] for x in group[1:]})))
    out[cal] = sorted(merged, key=lambda s: (s["app"], s["file"], s["line"]))
json.dump(out, open(out_path, "w"), indent=0)
kinds = collections.Counter(s["kind"] for v in out.values() for s in v)
print("apps", len(apps), dict(stats))
print("sites by kind", dict(kinds))
print("receivers", dict(collections.Counter(s.get("receiver") for v in out.values() for s in v if s["kind"] == "read")))
