"""Stock LTZ calibration reference set - ground-truth known-good containers.

Hashes transcribed from tools/mdi2_client/mdi2/ltz_reference_manifest.py (LTZ_REFERENCE):
SHA-256 of the UNWRAPPED CSM container (outer gzip removed), slot = decimal index.
The deployed files (named by part number) are the outer-gzip containers; unwrap with
gzip then hash to compare. These are the lowest-risk real payload for a live write test
(restoring known stock is a documented, already-performed recovery operation).
"""
from __future__ import annotations

import gzip
import hashlib
import zlib
from pathlib import Path

from . import config

# slot(dec) -> (part_number, unwrapped CSM SHA-256)
LTZ_REFERENCE = {
    2: ("87863250", "604f34c19822f204a852a252b601fb1d9b3dc425a989a9a41a807864a509b286"),
    3: ("84517309", "79167d182ca5cde22b8e8da80e61f2058f3d20d5dd595158970cdea914118f4d"),
    4: ("85045371", "27aa0cb3427225518e51cd1a5c53d6139462609ea11df106bf27bde2a7136231"),
    5: ("87846416", "7d58ff19805c296463fcd6764a1b9cb08028f905c91a2d5d89b4fc7f114dbb5e"),
    6: ("87846371", "d34e1deaaf748e8c27b6d9980856e2236d4614223686288f4ebd340b2bbbacf7"),
    7: ("85783460", "37756273d117233e0ccd503606bbdefe3524a7b55cc1834c34d93eaf5e565ace"),
    8: ("87846432", "c97114731de14bc5f748f98ed10f931fb5e0a432b40bb1e75c01efd43b7055b4"),
    9: ("87846376", "1af636050a32ae729a7a21a29212943ff98fc2ea8798823f9c8f285772a97e2c"),
    10: ("87846368", "0c5f7a1aa31b1c6551a34b04df32368f2913a02d3d4dcc798fbb345511038cb0"),
    11: ("86292118", "0dfe3c339a14811d8a2ac6aeebfae04f5f27ae720d60fca7cb60096a5c22b789"),
    12: ("85102312", "c8c36547fa2292b5aed6bb58b063e34da8b4490c60747dee5c40e50f6edf532e"),
    13: ("87846384", "3af4aa72d303dff844659ccb90d7d1514436c47412b7f8e0162a75a9d7198b1e"),
    14: ("84517418", "a07d08ead8cb96147cf2a8ff31788b0e22e76e961ffce0516918e37f26a824cf"),
    15: ("87846380", "2e6f8247aecfdfc32997fbd3779c1917c7360579484de39b21f757d1d2740f53"),
}
# The SPS programming-sequence utility (not a calibration slot).
SPS_UTILITY_PART = "85577468"


def _unwrapped_sha256(raw: bytes) -> str:
    try:
        inner = gzip.decompress(raw)
    except (OSError, EOFError, zlib.error):
        inner = raw
    return hashlib.sha256(inner).hexdigest()


def container_path(part: str) -> Path | None:
    # `part` is attacker-influenced (POST /api/cal/write/plan form field, echoed into
    # a live-write plan). `LTZ_REF_DIR / part` is unsafe: Path join DISCARDS the left
    # side when `part` is absolute (e.g. "/etc/passwd"), and "../.." would escape the
    # directory - either would let an arbitrary file's bytes be planned and, if
    # confirmed, streamed to the ECU as a calibration container. Collapse to a bare
    # filename and reject anything that was path-like (matches the elk upload guards).
    # The ONLY source is the verified stock reference set - there is no custom source.
    name = Path(part).name
    if not name or name != part:
        return None
    p = config.LTZ_REF_DIR / name
    return p if p.is_file() else None


def part_for_slot(slot_hex: str) -> str | None:
    """Map a slot (hex string like '05') to its stock part number, if known."""
    try:
        slot_dec = int(slot_hex, 16)
    except (TypeError, ValueError):
        return None
    entry = LTZ_REFERENCE.get(slot_dec)
    return entry[0] if entry else None


def expected_sha_for_part(part: str) -> str | None:
    """Unwrapped CSM SHA-256 the manifest expects for a stock part number, if known."""
    for _slot, (p, sha) in LTZ_REFERENCE.items():
        if p == part:
            return sha
    return None


def slot_for_part(part: str) -> str | None:
    """Map a GM part number to its calibration slot (hex string like '08'), if known.
    This is the reverse of SLOT_PARTS: an uploaded module is identified by its part-number
    filename, and that part number pins the slot it belongs to."""
    for slot, (p, _sha) in LTZ_REFERENCE.items():
        if p == part:
            return f"{slot:02X}"
    return None


def is_stock_bytes(part: str, raw: bytes) -> bool:
    """True iff `raw` (an outer-gzip container's bytes) unwraps to the exact stock CSM
    payload the manifest pins for `part`. A True result means the module is genuine/stock
    and is written with the ordinary genuine path; a False result means it is a modified
    container that must go through the 0x613/0x614 VIP override path (genuine=False)."""
    exp = expected_sha_for_part(part)
    return exp is not None and _unwrapped_sha256(raw) == exp


def full_package() -> list[dict]:
    """Every present+matching stock slot, ordered by slot, for a full-package write."""
    pkg = []
    for slot, (part, _sha) in sorted(LTZ_REFERENCE.items()):
        p = config.LTZ_REF_DIR / part
        if p.is_file():
            pkg.append({"slot": f"{slot:02X}", "part": part, "path": str(p)})
    return pkg


def verify_all() -> dict:
    """Check every reference container's unwrapped SHA-256 against the manifest."""
    rows = []
    ok = True
    for slot, (part, expected) in sorted(LTZ_REFERENCE.items()):
        path = config.LTZ_REF_DIR / part
        if not path.is_file():
            rows.append({"slot": f"{slot:02X}", "part": part, "present": False, "match": None})
            ok = False
            continue
        actual = _unwrapped_sha256(path.read_bytes())
        match = actual == expected
        ok = ok and match
        rows.append({"slot": f"{slot:02X}", "part": part, "present": True,
                     "match": match, "sha256": actual, "expected": expected})
    sps = config.LTZ_REF_DIR / SPS_UTILITY_PART
    return {"dir": str(config.LTZ_REF_DIR), "all_match": ok, "containers": rows,
            "sps_utility": {"part": SPS_UTILITY_PART, "present": sps.is_file(),
                            "note": "programming-sequence utility, not a calibration slot"}}
