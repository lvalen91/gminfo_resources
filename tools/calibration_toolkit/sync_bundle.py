#!/usr/bin/env python3
"""Refresh (or verify) the copies of repo material bundled inside this toolkit.

The toolkit runs from the copies; the originals in a gminfo_resources checkout stay
the place to edit them.

    python3 sync_bundle.py /path/to/gminfo_resources           # rewrite the copies
    python3 sync_bundle.py /path/to/gminfo_resources --check   # report drift, exit 1
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = "research/eeprom-calibration"
DOCS = [
    "CALIBRATION_SLOT_MAP.md",
    "CALIBRATION_CUSTOMIZATION_GUIDE.md",
    "DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md",
    "CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md",
    "GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md",
    "EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md",
    "calibration_glossary.md",
]
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def _localize(text: str) -> str:
    """Keep links between bundled docs; turn links that would leave the bundle into
    plain text naming the repo path."""
    def repl(m):
        label, target = m.group(1), m.group(2)
        if target.startswith(("#", "http://", "https://", "mailto:")):
            return m.group(0)
        path = target.split("#")[0]
        if path in DOCS:
            return m.group(0)
        full = posixpath.normpath(posixpath.join(RESEARCH, path))
        return f"{label} (not bundled: `{full}`)"
    return LINK.sub(repl, text)


def expected_files(repo: Path) -> dict[Path, bytes]:
    dbs = sorted(repo.glob("reference/GIS-646_CalDef_Database_*/caldefs"))
    if len(dbs) != 1:
        sys.exit(f"error: expected one CalDef database under {repo}/reference, found {len(dbs)}")
    out = {}
    for pattern in ("*.caldef", "*.enumdef"):
        for src in sorted(dbs[0].glob(pattern)):
            out[Path("data/caldefs") / src.name] = src.read_bytes()
    out[Path("data/CALDEF_SOURCE.txt")] = (dbs[0].parent.name + "\n").encode()
    for name in DOCS:
        src = repo / RESEARCH / name
        out[Path("docs") / name] = _localize(src.read_text(encoding="utf-8")).encode("utf-8")
    out[Path("tests/fixtures/ltz_trim_sample.calovride")] = (
        repo / RESEARCH / "calibration_prototypes/a11_ltz_gmtrim_highcountry.calovride.xml").read_bytes()
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    want = expected_files(args.repo.resolve())
    have = {f.relative_to(HERE) for d in ("data", "docs", "tests/fixtures")
            for f in (HERE / d).rglob("*") if f.is_file() and f.name != ".DS_Store"}
    changed = sorted(r for r, b in want.items() if r not in have or (HERE / r).read_bytes() != b)
    extra = sorted(have - set(want))
    if args.check:
        for r in changed:
            print("differs or missing:", r)
        for r in extra:
            print("not in source:", r)
        print(f"{len(want)} bundled files, {len(changed) + len(extra)} out of sync")
        sys.exit(1 if changed or extra else 0)
    for r in changed:
        (HERE / r).parent.mkdir(parents=True, exist_ok=True)
        (HERE / r).write_bytes(want[r])
    for r in extra:
        (HERE / r).unlink()
    print(f"wrote {len(changed)}, removed {len(extra)}, {len(want)} bundled files")


if __name__ == "__main__":
    main()
