"""Doc-grounded catalogs for the diagnosticsd panel: safe read DIDs, the calibration
slot map, SecurityAccess profiles, and the reset/recovery routine catalog.

Every value here is transcribed from the repo docs (cited inline). Nothing is invented.
Destructive routines carry destructive=True and are never auto-executed by the backend.
"""
from __future__ import annotations

# --- Safe, non-destructive ReadDataByIdentifier ($22) DIDs ----------------------
# diagnostics/diagnosticsd_dids_and_dtc.md:99-136, 278-316. All readable in default
# session unless security_level is set. decode hints are informational only.
READ_DIDS = [
    {"did": "F180", "name": "Boot module IDs", "security": None,
     "note": "15 B: 2x (tag + BE32 part# + 2 ver). tag47 p85056831, tag48 p85098661"},
    {"did": "F181", "name": "Application IDs", "security": None,
     "note": "15 B: tag01 p85759599 ver 'CJ', tag15 p85098662 ver 'BM'"},
    {"did": "F182", "name": "Calibration identity block", "security": None,
     "note": "197 B: count 28 + 28x (tag + BE32 part# + 2 ver); slots 02..0F present"},
    {"did": "F190", "name": "VIN", "security": None, "note": "17 B VIN"},
    {"did": "F0F0", "name": "Programming status block", "security": None, "note": "28 B"},
    {"did": "F0F1", "name": "PEC (prog event code)", "security": None, "note": "2 B; 0000=ok, 0015=rejected write"},
    {"did": "F0F2", "name": "PEC secondary", "security": None, "note": "2 B"},
    {"did": "F0F3", "name": "ECU identity (VIP-correlated)", "security": None, "note": "16 B; matches seed ECUID prefix"},
    {"did": "F198", "name": "Repair-shop code", "security": None, "note": "10 B (SPS-written)"},
    {"did": "F199", "name": "Programming date", "security": None, "note": "4 B"},
    {"did": "F1A0", "name": "SBI/bypass flag", "security": None, "note": "1 B; FF in bypassed state"},
    {"did": "F0A7", "name": "Protected datum", "security": "09/0B/0D",
     "note": "1 B; 7F 22 7F in default session - requires SecurityAccess unlock"},
]

# --- Calibration slot map (CALIBRATION_SLOT_MAP.md:54-70) ------------------------
# Read path is identity-only: parse DID F182 for the applied part number per slot.
# There is NO per-slot content read over UDS ($23 is gated and fails downstream).
SLOT_MAP = {
    0x02: {"part": 87863250, "alpha": "AA", "overrides": 21, "triage": "mixed",
           "content": "Nav/fuel-type config + steering-wheel switch map"},
    0x03: {"part": 84517309, "alpha": "AA", "overrides": 0, "triage": "n/a",
           "content": "Empty (valid, digested, no overrides)"},
    0x04: {"part": 85045371, "alpha": "AA", "overrides": 404, "triage": "safe",
           "content": "UI/home-screen/chime/audio/diagnostics - largest, most-tested"},
    0x05: {"part": 87846416, "alpha": "AB", "overrides": 194, "triage": "mixed",
           "content": "HMI policy: driver-workload lockouts, CarPlay/AA, tuner, region/language, servers"},
    0x06: {"part": 87846371, "alpha": "AA", "overrides": 34, "triage": "safe",
           "content": "Speech-recognition config + .vtc tuning files"},
    0x07: {"part": 85783460, "alpha": "AA", "overrides": 34, "triage": "safe",
           "content": "Bluetooth profile enables + .scd hands-free audio tuning"},
    0x08: {"part": 87846432, "alpha": "AA", "overrides": 30, "triage": "avoid",
           "content": "Rear-vision camera geometry/intrinsics + screen resolution"},
    0x09: {"part": 87846376, "alpha": "AA", "overrides": 48, "triage": "avoid",
           "content": "Diagnostic masks, GNSS dead-reckoning, system-state timers"},
    0x0A: {"part": 87846368, "alpha": "AA", "overrides": 23, "triage": "safe",
           "content": "HVAC/climate touch UI + air-quality UI"},
    0x0B: {"part": 86292118, "alpha": "AA", "overrides": 42, "triage": "avoid",
           "content": "Connectivity/telematics switches, DTC masks, OMA-DM timers"},
    0x0C: {"part": 85102312, "alpha": "AB", "overrides": 20, "triage": "safe",
           "content": "Tuner/SXM/HD/DAB feature set + antenna + voice-recog DTC masks"},
    0x0D: {"part": 87846384, "alpha": "AB", "overrides": 19, "triage": "avoid",
           "content": "Trailering/trailer-camera, rear-seat entertainment, DTC masks"},
    0x0E: {"part": 84517418, "alpha": "AA", "overrides": 0, "triage": "n/a",
           "content": "Empty (inner XML byte-identical to slot 03)"},
    0x0F: {"part": 87846380, "alpha": "AA", "overrides": 114, "triage": "safe",
           "content": "Vehicle-specific parametric EQ (per-channel acoustic tune)"},
}
TRIAGE_LABEL = {"safe": "try - proven/low-risk", "mixed": "mixed - some entries safety-adjacent",
                "avoid": "avoid specific entries - see slot map doc", "n/a": "empty slot"}


def parse_f182(resp: bytes) -> list[dict]:
    """Parse a 62 F1 82 response into per-record {tag, part, version, slot?}.
    Layout (dids_and_dtc.md:102-108): 62 F1 82 <count> then count x 7-byte records
    = 1-byte tag + BE32 part# + 2 version bytes."""
    if len(resp) < 4 or resp[0] != 0x62 or resp[1:3] != b"\xf1\x82":
        raise ValueError("not a 62 F1 82 response")
    count = resp[3]
    body = resp[4:]
    out = []
    for i in range(count):
        rec = body[i * 7:i * 7 + 7]
        if len(rec) < 7:
            break
        tag = rec[0]
        part = int.from_bytes(rec[1:5], "big")
        ver = rec[5:7]
        entry = {"tag": f"{tag:02X}", "part_number": part, "version_hex": ver.hex(),
                 "version_ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in ver)}
        if tag in SLOT_MAP:
            info = SLOT_MAP[tag]
            entry["slot"] = tag
            entry["slot_content"] = info["content"]
            entry["triage"] = info["triage"]
            entry["expected_part"] = info["part"]
            entry["matches_stock"] = (part == info["part"])
        out.append(entry)
    return out


# --- SecurityAccess profiles ($27) ----------------------------------------------
# diagnosticsd_security_access.md:75-82, 6-8. The bench-confirmed exchange is the
# degenerate SBI-bypass form: 31-byte all-FF seed -> 12-byte all-zero key -> 67 grant.
# This is NOT the normal seed->key algorithm (that needs a backend secret, candidate
# only: AES-128-CMAC(backend16, FF16)[:12], GM_SEED_KEY...md:130-167).
SECURITY_LEVELS = [0x01, 0x03, 0x05, 0x09, 0x0B, 0x0D, 0x11, 0x13, 0x15]
DEGENERATE_KEY = bytes(12)  # all-zero 12-byte key accepted on this bench unit
SECURITY_NOTE = ("Bench-confirmed degenerate exchange only (all-FF seed -> 12 zero bytes -> "
                 "67 grant), valid in this unit's SBI-bypass state. The real seed->key math "
                 "is candidate/static-only and needs a per-unit backend secret not in the repo.")

# --- Reset / recovery routines ($31) --------------------------------------------
# diagnostics/diagnosticsd_routines_and_recovery.md. destructive routines are wired
# but the backend refuses to fire them without explicit confirm (see routines flow).
ROUTINES = [
    {"rid": "0260", "control": "01", "params": "05", "name": "Reset retry counters (NONE)",
     "desc": "Resets retry counters; option 05=NONE succeeds (others 00-04 -> 7F 31 31).",
     "security": "extended session", "destructive": False, "status": "bench",
     "reversible": "counter reset"},
    {"rid": "0248", "control": "01", "params": "03", "name": "Reset favorites (no-op 03)",
     "desc": "Reset-favorites routine. 03=no-op; 00 audio, 01 phone, 02 nav lists.",
     "security": "extended session / level 09", "destructive": True, "status": "bench",
     "reversible": "clears the named favorites list"},
    {"rid": "0254", "control": "01", "params": "", "name": "LCM-record clear",
     "desc": "Clears last-communication-module records (empty DB treated as success).",
     "security": "extended session", "destructive": True, "status": "bench",
     "reversible": "destroys LCM records"},
    {"rid": "0247", "control": "01", "params": "", "name": "Android factory reset / user-data wipe",
     "desc": "vehicle-settings restore + RecoverySystem.rebootWipeUserData. Needs CAN 20D "
             "byte4 bits5-7=2 precondition else 7F 31 22. Async reboot.",
     "security": "extended session (+ CAN precondition)", "destructive": True, "status": "bench",
     "reversible": "IRREVERSIBLE user-data wipe + reboot"},
    {"rid": "0249", "control": "01", "params": "", "name": "Calibration clear (ALL overrides)",
     "desc": "clearAllOverrides - reverts all 14 module records to base part 70008. "
             "DO NOT send 31 03 02 49 (requestResults also clears).",
     "security": "extended session + level-01 grant", "destructive": True, "status": "bench",
     "reversible": "IRREVERSIBLE: boots to NoCalibration(0xe); recovery needs 14-container reprogram"},
    {"rid": "F0008180", "control": "01", "params": "03", "name": "ELK / fastboot reboot",
     "desc": "31 01 F000 8180 03 -> controlled reboot into ELK/fastboot (titan_gm_my22). "
             "Gated: needs session-4 + security-40 DCM mask AND VIP RAM FEBD0CF8=1.",
     "security": "gated (VIP RAM write)", "destructive": True, "status": "bench-gated",
     "reversible": "reboots into bootloader; display off, ADB drops"},
]


def routine_request_bytes(control_hex: str, rid_hex: str, params_hex: str) -> bytes:
    """Build the exact 31 <ctrl> <RID...> [params] UDS payload (for dry-run / display)."""
    rid = bytes.fromhex(rid_hex)
    return bytes([0x31, int(control_hex, 16)]) + rid + bytes.fromhex(params_hex or "")
