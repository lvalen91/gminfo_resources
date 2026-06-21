#!/usr/bin/env python3
"""
GM IOK (Info 3.7/3.8 CSM) EEPROM Editor — ST M24C64 (8 KB) dumps.

A zero-dependency, single-file local web UI for inspecting and editing
GM Harman infotainment EEPROM flash dumps. Built from the research in
EEPROM_Analysis_Report.md and EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md.

KEY DESIGN PRINCIPLE — marker bytes are runtime-generated (CalGroup), so the
tool NEVER assumes a fixed framing marker. For every flag it reads the LIVE
marker at the base address and edits ONLY the data byte at base+1, preserving
whatever marker the firmware assigned. (Report §"Framing Protocol", Feb 2026.)

Usage:
    python3 eeprom_editor.py [path/to/dump.bin] [--port 8765] [--no-browser]

Runs at http://127.0.0.1:8765 (localhost only). Stdlib only — works under any
python3 (no tkinter, no pip). Upload a dump in the browser, or pick one of the
known dumps from the dropdown. The original file is never overwritten unless you
explicitly Save As to the same path; edits live in memory until you save.
"""

import argparse
import hashlib
import http.server
import json
import os
import socketserver
import sys
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

EEPROM_SIZE = 8192
KNOWN_MARKERS = {0x5A, 0x69, 0xC3, 0xF0}
DIR = os.path.dirname(os.path.abspath(__file__))
# Dumps live in the parent EEPROM folder (this script sits in config_tool/).
# Relative load/save paths and the file dropdown resolve against DUMP_ROOT.
DUMP_ROOT = os.path.dirname(DIR)

# VIN: [marker][17 ASCII chars][marker][0xFF pad]
VIN_BASE = 0x05C0
VIN_DATA = 0x05C1
VIN_LEN = 17

# ── Field definitions (grounded in the analysis docs) ───────────────────────
# Each flag is [marker][data][marker]; we read marker live, edit data at base+1.

SECURITY_FLAGS = [
    {"key": "sbi1", "base": 0x0440, "name": "Primary SBI — ADB Security #1",
     "on": 0xFF, "off": 0x00, "on_label": "Bypass", "off_label": "Lock",
     "states": {0x00: ("LOCKED", "bad"), 0xFF: ("BYPASSED", "good")},
     "note": "ADB security. 0x00 requires GM Secure Client; 0xFF opens ADB."},
    {"key": "sbi2", "base": 0x0A80, "name": "Backup SBI — ADB Security #2",
     "on": 0xFF, "off": 0x00, "on_label": "Bypass", "off_label": "Lock",
     "states": {0x00: ("LOCKED", "bad"), 0xFF: ("BYPASSED", "good")},
     "note": "Backup copy. Was 0xFF (empty) pre-Y181; now actively initialized. "
             "Both SBIs must match for the bypass to hold."},
    {"key": "debug", "base": 0x0B40, "name": "Debug / Developer Mode",
     "on": 0x01, "off": 0x00, "on_label": "On", "off_label": "Off",
     "states": {0x00: ("OFF", "neutral"), 0x01: ("ON", "good")},
     "note": "Developer/debug mode flag. 0x01 = on, 0x00 = off."},
]

# Best-effort ASCII string fields: [marker][ascii...][marker][0xFF pad]
STRING_FIELDS = [
    {"key": "vin",      "base": VIN_BASE, "maxlen": 24, "name": "VIN", "vin": True},
    {"key": "partno",   "base": 0x0500, "maxlen": 24, "name": "Part Number"},
    {"key": "hwver",    "base": 0x0520, "maxlen": 16, "name": "HW Version field"},
    {"key": "rev",      "base": 0x0540, "maxlen": 16, "name": "Revision field"},
    {"key": "hwrev",    "base": 0x0560, "maxlen": 16, "name": "HW Rev field"},
    {"key": "progdate", "base": 0x0580, "maxlen": 16, "name": "Programming Date"},
    {"key": "serial",   "base": 0x05A0, "maxlen": 24, "name": "Serial Number"},
    {"key": "region",   "base": 0x04E0, "maxlen": 8,  "name": "Region Code"},
    {"key": "unit",     "base": 0x0680, "maxlen": 24, "name": "Unit Serial"},
    {"key": "fwid",     "base": 0x14A0, "maxlen": 24, "name": "Firmware ID"},
]

# Single-byte feature toggles (data byte at base+1). From report tables.
# Suspected values are surfaced as buttons even where on/off semantics are unknown.
FF = [0x00, 0x01, 0xFF]   # default option set
FEATURE_FLAGS = [
    {"base": 0x0000, "name": "Boot/Init complete flag", "risk": "high", "options": FF,
     "note": "Header. Corrupting may make EEPROM look virgin."},
    {"base": 0x0020, "name": "Secondary boot flag", "risk": "med", "options": FF,
     "note": "Report: try 0xFF (unknown feature #1)."},
    {"base": 0x0B80, "name": "Feature enable #1", "risk": "med", "options": FF,
     "note": "Unknown feature; report suggests 0xFF."},
    {"base": 0x0BA0, "name": "Feature enable #2", "risk": "med", "options": FF,
     "note": "Unknown feature."},
    {"base": 0x0BC0, "name": "Feature toggle", "risk": "med", "options": FF,
     "note": "Unknown feature; report suggests 0xFF."},
    {"base": 0x0C00, "name": "Extended config (ACTIVE in sample)", "risk": "med", "options": FF,
     "note": "Observed 0x01 in sample dumps."},
    {"base": 0x1500, "name": "Runtime flag", "risk": "med", "options": FF, "note": "Unknown feature."},
    {"base": 0x15C0, "name": "Feature enable", "risk": "med", "options": FF, "note": "Unknown feature."},
    {"base": 0x1A00, "name": "Tertiary security / calibration flag", "risk": "high", "options": FF,
     "note": "Security-critical per map; modify with care."},
    # Undocumented candidates (EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS §6)
    {"base": 0x04A0, "name": "UNDOC security-region flag (17 refs)", "risk": "high", "options": FF,
     "note": "Undocumented. Test: 0xFF. Security region."},
    {"base": 0x04C0, "name": "UNDOC security-region flag (11 refs)", "risk": "high", "options": FF,
     "note": "Undocumented. Test: 0xFF. Security region."},
    {"base": 0x0A40, "name": "UNDOC feature flag (28 refs)", "risk": "med", "options": FF,
     "note": "Undocumented. Test: 0xFF."},
    {"base": 0x0BE0, "name": "UNDOC feature flag (24 refs)", "risk": "med", "options": FF,
     "note": "Undocumented. Test: 0xFF or 0x01."},
]

# UI flags block at 0xE80: [marker][b1 b2 ...]; individual data bytes.
UI_FLAGS_BASE = 0x0E80
UI_FLAGS = [
    {"off": 0x01, "name": "Display mode / theme selector", "bitfield": True},
    {"off": 0x02, "name": "Touch input enabled"},
    {"off": 0x03, "name": "Haptic / vibration feedback"},
    {"off": 0x04, "name": "UI sound effects"},
    {"off": 0x05, "name": "Transition animations"},
    {"off": 0x06, "name": "Auto-brightness / night mode"},
    {"off": 0x07, "name": "Reserved feature #1 (hidden?)"},
    {"off": 0x08, "name": "Reserved feature #2 (hidden?)"},
    {"off": 0x09, "name": "Feature mask bitfield", "bitfield": True},
    {"off": 0x0A, "name": "Input mode / gesture control"},
    {"off": 0x0D, "name": "Unknown toggle"},
]

# CRC fields. kind='std' → [marker][3-byte version counter][2-byte CRC16][marker].
CRC_FIELDS = [
    {"base": 0x16E0, "name": "Primary CRC #1", "kind": "std"},
    {"base": 0x19E0, "name": "Secondary CRC #2", "kind": "std"},
    {"base": 0x1B40, "name": "Data CRC", "kind": "std"},
    {"base": 0x1A80, "name": "Config CRC (reference copy)", "kind": "raw", "len": 10},
]

VIN_YEAR = {  # 10th VIN char -> model year (current cycle)
    'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025,
    'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029, 'Y': 2030,
}

# SPS calibrations known to re-write the EEPROM security state during programming.
# (gm_dps/calibrations: SW ID 0x07 = "Security Config" file 85783460; SW ID 0x0D/13
#  = "Security Flags" file 87846384.) These overwrite the SBI/debug bytes back to
#  locked on any SPS/USB programming pass — the firmware itself does NOT CRC-gate
#  these bytes (confirmed by VIP firmware RE), so GM enforces re-lock via these cals.
SBI_CAL_RESET = "Reset to LOCKED by SPS cal SW ID 7 (Security Config) / 13 (Security Flags) on programming"

# Plain-language security-state interpretation for the SBI data byte.
SBI_INTERP = {
    0xFF: "ADB open · SELinux likely permissive",
    0x00: "Secured · GM Secure Client required",
}

# VIN check-digit (position 9) transliteration + weights (ISO 3779 / NHTSA).
VIN_TRANSLIT = {**{c: i for i, c in enumerate("0123456789")},
                'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
                'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
                'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9}
VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def vin_check_digit_ok(vin):
    """Return True/False if the VIN's position-9 check digit is valid, or None if N/A."""
    if len(vin) != 17 or any(c not in VIN_TRANSLIT for c in vin.upper()):
        return None
    total = sum(VIN_TRANSLIT[c] * w for c, w in zip(vin.upper(), VIN_WEIGHTS))
    rem = total % 11
    expect = 'X' if rem == 10 else str(rem)
    return vin[8].upper() == expect


# ── EEPROM model ────────────────────────────────────────────────────────────

class Eeprom:
    def __init__(self):
        self.data = None       # bytearray (working copy)
        self.original = None   # bytes (as loaded)
        self.path = None       # real filesystem path (None for uploads)
        self.name = None       # display name

    def load_bytes(self, raw, name, path=None):
        if len(raw) != EEPROM_SIZE:
            raise ValueError(
                f"Expected {EEPROM_SIZE} bytes (M24C64), got {len(raw)} bytes.")
        self.data = bytearray(raw)
        self.original = bytes(raw)
        self.path = path
        self.name = name

    def load(self, path):
        with open(path, "rb") as fh:
            raw = fh.read()
        self.load_bytes(raw, os.path.basename(path), path=path)

    def loaded(self):
        return self.data is not None

    def write_bytes(self, addr, values):
        if not self.loaded():
            raise ValueError("No file loaded.")
        for i, v in enumerate(values):
            a = addr + i
            if not (0 <= a < EEPROM_SIZE):
                raise ValueError(f"Address 0x{a:04X} out of range.")
            if not (0 <= v <= 0xFF):
                raise ValueError(f"Byte value {v} out of range (0-255).")
            self.data[a] = v

    def revert(self):
        if self.original is None:
            raise ValueError("Nothing loaded.")
        self.data = bytearray(self.original)

    def save(self, path):
        if not self.loaded():
            raise ValueError("No file loaded.")
        with open(path, "wb") as fh:
            fh.write(self.data)

    def diff(self):
        out = []
        if not self.loaded():
            return out
        for a in range(EEPROM_SIZE):
            if self.data[a] != self.original[a]:
                out.append({"addr": a, "was": self.original[a], "now": self.data[a]})
        return out

    def sha256(self):
        return hashlib.sha256(bytes(self.data)).hexdigest() if self.loaded() else ""


EE = Eeprom()


# ── Parsing helpers ─────────────────────────────────────────────────────────

def parse_string(data, base, maxlen):
    """Read [marker][ascii...] until marker repeats / 0xFF / 0x00 / non-printable."""
    if base >= len(data):
        return "", None
    marker = data[base]
    chars = []
    for i in range(base + 1, min(base + 1 + maxlen, len(data))):
        b = data[i]
        if b == marker or b in (0x00, 0xFF):
            break
        if 32 <= b < 127:
            chars.append(chr(b))
        else:
            break
    return "".join(chars).strip(), marker


def decode_vin(vin):
    info = []
    if len(vin) >= 11:
        wmi = vin[:3]
        country = {"1": "USA", "2": "Canada", "3": "Mexico"}.get(vin[0], "?")
        info.append(f"WMI {wmi} ({country})")
        yr = VIN_YEAR.get(vin[9].upper())
        if yr:
            info.append(f"Model year {yr}")
        info.append(f"Plant {vin[10]}")
    return " · ".join(info)


def state_for(value, states):
    if value in states:
        return states[value]
    return (f"0x{value:02X}", "warn")


def byte_state(value):
    """Generic ON/OFF state for an undocumented single byte."""
    if value == 0x00:
        return ("OFF", "neutral")
    if value == 0xFF:
        return ("ON (FF)", "good")
    if value == 0x01:
        return ("ON (01)", "good")
    return (f"SET 0x{value:02X}", "warn")


def region_modified(base, length):
    o, d = EE.original, EE.data
    return any(o[base + i] != d[base + i] for i in range(length))


def fingerprint():
    """One-line verdicts about the loaded dump's security/identity state."""
    d = EE.data
    tags = []
    sbi1, sbi2, dbg = d[0x0441], d[0x0A81], d[0x0B41]
    m2 = d[0x0A80]
    vin_learn = all(d[VIN_DATA + i] == 0xFF for i in range(VIN_LEN))
    backup_uninit = (m2 == 0xFF and sbi2 == 0xFF)

    if sbi1 == 0xFF and sbi2 == 0xFF and not backup_uninit:
        tags.append(("Full ADB bypass active — both SBIs unlocked", "good"))
    elif sbi1 == 0xFF and backup_uninit:
        tags.append(("Primary SBI bypassed; backup SBI uninitialized", "warn"))
    elif (sbi1 == 0xFF) ^ (sbi2 == 0xFF):
        tags.append(("Partial / mismatched SBI state — bypass may not hold", "warn"))
    elif sbi1 == 0x00 and sbi2 == 0x00:
        tags.append(("Locked / secured — stock security state", "bad"))
    else:
        tags.append((f"Non-standard SBI bytes (0x{sbi1:02X}/0x{sbi2:02X})", "warn"))

    if dbg == 0x01:
        tags.append(("Debug / Developer mode ON", "good"))
    if vin_learn:
        tags.append(("VIN in learn / relearn mode (all 0xFF)", "warn"))
    elif vin_check_digit_ok(parse_string(d, VIN_BASE, 24)[0]) is False:
        tags.append(("VIN present but check digit INVALID", "warn"))
    if backup_uninit:
        tags.append(("Backup SBI slot uninitialized (FF FF FF) — pre-Y181 pattern", "warn"))
    return [{"text": t, "css": c} for t, c in tags]


def build_address_labels():
    """Map data addresses -> human label, for annotating diffs/compares."""
    lab = {}
    for f in SECURITY_FLAGS:
        lab[f["base"] + 1] = f["name"]
    for f in FEATURE_FLAGS:
        lab[f["base"] + 1] = f["name"]
    for f in UI_FLAGS:
        lab[UI_FLAGS_BASE + f["off"]] = "UI: " + f["name"]
    for f in STRING_FIELDS:
        lab[f["base"]] = f["name"]
    for f in CRC_FIELDS:
        lab[f["base"]] = f["name"]
    return lab


ADDRESS_LABELS = build_address_labels()
SECURITY_ADDRS = {0x0441, 0x0A81, 0x0B41, 0x0440, 0x0A80, 0x0B40}


def annotate_addr(a):
    """Best-effort label for an address: exact field, region, or VIN/identity span."""
    if a in ADDRESS_LABELS:
        return ADDRESS_LABELS[a]
    if VIN_DATA <= a < VIN_DATA + VIN_LEN:
        return "VIN"
    # nearest known field within 0x20 below
    for base in sorted(ADDRESS_LABELS):
        if base <= a < base + 0x20:
            return ADDRESS_LABELS[base] + " (+%d)" % (a - base)
    return ""


def build_state():
    if not EE.loaded():
        return {"loaded": False, "files": list_dumps()}
    d, o = EE.data, EE.original

    # security
    sec = []
    for f in SECURITY_FLAGS:
        base = f["base"]
        marker = d[base]
        val = d[base + 1]
        if marker == 0xFF and val == 0xFF:
            label, css = ("UNINITIALIZED", "warn")  # empty slot, not a real bypass
        else:
            label, css = state_for(val, f["states"])
        sec.append({
            "name": f["name"], "base": base, "addr": base, "data_addr": base + 1,
            "marker": marker, "value": val, "orig": o[base + 1],
            "modified": val != o[base + 1],
            "label": label, "css": css, "note": f["note"],
            "interp": SBI_INTERP.get(val, "") if f["key"] in ("sbi1", "sbi2") else "",
            "reset_by": SBI_CAL_RESET,
            "options": [{"val": f["on"], "label": f["on_label"]},
                        {"val": f["off"], "label": f["off_label"]}],
            "raw": f"{d[base]:02X} {d[base+1]:02X} {d[base+2]:02X}",
        })

    # strings / identity
    strs = []
    for f in STRING_FIELDS:
        s, marker = parse_string(d, f["base"], f["maxlen"])
        item = {"key": f["key"], "name": f["name"], "base": f["base"],
                "marker": marker, "value": s,
                "modified": region_modified(f["base"], f["maxlen"])}
        if f.get("vin"):
            learn = all(d[VIN_DATA + i] == 0xFF for i in range(VIN_LEN))
            chk = None if learn else vin_check_digit_ok(s)
            item.update({"vin": True, "data_addr": VIN_DATA, "length": VIN_LEN,
                         "learn": learn, "check_ok": chk,
                         "decoded": "" if learn else decode_vin(s)})
        strs.append(item)

    # feature flags
    feats = []
    for f in FEATURE_FLAGS:
        base = f["base"]
        val = d[base + 1]
        label, css = byte_state(val)
        feats.append({"name": f["name"], "base": base, "addr": base,
                      "data_addr": base + 1, "marker": d[base], "value": val,
                      "orig": o[base + 1], "modified": val != o[base + 1],
                      "label": label, "css": css, "risk": f["risk"], "note": f["note"],
                      "options": [{"val": v, "label": "0x%02X" % v} for v in f["options"]]})

    # UI flags
    ui = []
    ui_marker = d[UI_FLAGS_BASE]
    for f in UI_FLAGS:
        a = UI_FLAGS_BASE + f["off"]
        val = d[a]
        if f.get("bitfield"):
            label, css = (f"0x{val:02X}", "warn" if val else "neutral")
            opts = []  # bitfield: hex input only
        else:
            label, css = ("ON", "good") if val else ("OFF", "neutral")
            opts = [{"val": 1, "label": "On"}, {"val": 0, "label": "Off"}]
        ui.append({"name": f["name"], "base": a, "addr": a, "data_addr": a,
                   "marker": ui_marker, "value": val, "orig": o[a],
                   "modified": val != o[a], "label": label, "css": css,
                   "options": opts})

    # CRCs
    crcs = []
    for f in CRC_FIELDS:
        base = f["base"]
        if f["kind"] == "std":
            counter = (d[base + 1] << 16) | (d[base + 2] << 8) | d[base + 3]
            crc16 = (d[base + 4] << 8) | d[base + 5]
            crcs.append({"name": f["name"], "base": base, "kind": "std",
                         "marker": d[base], "counter": counter, "crc16": crc16,
                         "raw": " ".join(f"{x:02X}" for x in d[base:base + 7])})
        else:
            n = f.get("len", 8)
            crcs.append({"name": f["name"], "base": base, "kind": "raw",
                         "raw": " ".join(f"{x:02X}" for x in d[base:base + n])})

    return {
        "loaded": True, "name": EE.name, "path": EE.path, "files": list_dumps(),
        "security": sec, "strings": strs, "features": feats,
        "ui_marker": ui_marker, "ui": ui, "crcs": crcs, "diff": EE.diff(),
        "sha256": EE.sha256(), "fingerprint": fingerprint(),
    }


def compare_to(ref_bytes):
    """Diff the working buffer against a reference dump, annotated."""
    out = []
    n = min(len(ref_bytes), EEPROM_SIZE)
    for a in range(n):
        if EE.data[a] != ref_bytes[a]:
            out.append({"addr": a, "cur": EE.data[a], "ref": ref_bytes[a],
                        "label": annotate_addr(a), "security": a in SECURITY_ADDRS})
    return out


def change_report():
    """Human-readable text report of in-memory edits vs the loaded original."""
    lines = ["GM IOK EEPROM — change report",
             f"file: {EE.name or '(uploaded)'}",
             f"sha256 (current): {EE.sha256()}",
             f"edits: {len(EE.diff())} byte(s)", ""]
    for ch in EE.diff():
        lab = annotate_addr(ch["addr"]) or "(unmapped)"
        lines.append(f"  0x{ch['addr']:04X}  {ch['was']:02X} -> {ch['now']:02X}   {lab}")
    return "\n".join(lines) + "\n"


def list_dumps():
    out = []
    for root, _dirs, files in os.walk(DUMP_ROOT):
        for fn in files:
            if fn.lower().endswith(".bin") or fn.startswith("bricked"):
                p = os.path.join(root, fn)
                try:
                    if os.path.getsize(p) == EEPROM_SIZE:
                        out.append(os.path.relpath(p, DUMP_ROOT))
                except OSError:
                    pass
    return sorted(out)


def hex_dump(start, length):
    d = EE.data
    start = max(0, min(start, EEPROM_SIZE - 1))
    end = min(EEPROM_SIZE, start + length)
    lines = []
    for row in range(start, end, 16):
        chunk = d[row:row + 16]
        hexs = " ".join(f"{b:02X}" for b in chunk)
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{row:04X}  {hexs:<47}  {asci}")
    return "\n".join(lines)


# ── HTTP handler ────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, text):
        body = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send_html(PAGE)
        if u.path == "/api/state":
            return self._send_json(build_state())
        if u.path == "/api/hex":
            q = parse_qs(u.query)
            start = int(q.get("start", ["0"])[0], 0)
            length = int(q.get("len", ["256"])[0], 0)
            if not EE.loaded():
                return self._send_json({"error": "No file loaded."}, 400)
            return self._send_json({"text": hex_dump(start, length)})
        if u.path == "/api/report":
            if not EE.loaded():
                return self._send_json({"error": "No file loaded."}, 400)
            body = change_report().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="eeprom_change_report.txt"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            if u.path == "/api/upload":
                raw = self._read_body()
                name = parse_qs(u.query).get("name", ["uploaded.bin"])[0]
                EE.load_bytes(raw, os.path.basename(name), path=None)
                return self._send_json(build_state())

            body = json.loads(self._read_body().decode() or "{}")

            if u.path == "/api/load":
                path = body["path"]
                if not os.path.isabs(path):
                    path = os.path.join(DUMP_ROOT, path)
                EE.load(path)
                return self._send_json(build_state())
            if u.path == "/api/compare":
                if not EE.loaded():
                    return self._send_json({"error": "No file loaded."}, 400)
                path = body["path"]
                if not os.path.isabs(path):
                    path = os.path.join(DUMP_ROOT, path)
                with open(path, "rb") as fh:
                    ref = fh.read()
                if len(ref) != EEPROM_SIZE:
                    return self._send_json(
                        {"error": f"Reference is {len(ref)} bytes, expected {EEPROM_SIZE}."}, 400)
                deltas = compare_to(ref)
                return self._send_json({"ref": os.path.basename(path),
                                        "deltas": deltas,
                                        "sec_count": sum(1 for x in deltas if x["security"])})
            if u.path == "/api/write":
                addr = body["addr"] if isinstance(body["addr"], int) \
                    else int(str(body["addr"]), 0)
                values = body["values"]
                if isinstance(values, str):
                    values = [int(values, 16)]
                EE.write_bytes(addr, [int(v) & 0xFF for v in values])
                return self._send_json(build_state())
            if u.path == "/api/action":
                self._do_action(body)
                return self._send_json(build_state())
            if u.path == "/api/revert":
                EE.revert()
                return self._send_json(build_state())
            if u.path == "/api/save":
                path = body["path"]
                if not os.path.isabs(path):
                    path = os.path.join(DUMP_ROOT, path)
                overwrite_orig = (EE.path and
                                  os.path.abspath(path) == os.path.abspath(EE.path))
                if overwrite_orig and not body.get("confirm_overwrite"):
                    return self._send_json(
                        {"error": "refuse_overwrite",
                         "message": "That is the original file. Re-send with "
                                    "confirm_overwrite to overwrite it."}, 409)
                EE.save(path)
                return self._send_json({"ok": True, "saved": path,
                                        "state": build_state()})
            return self._send_json({"error": "not found"}, 404)
        except Exception as e:  # surface to UI
            return self._send_json({"error": str(e)}, 400)

    def _do_action(self, body):
        """High-level marker-preserving actions."""
        name = body["action"]
        if name == "set_flag":
            base = int(body["base"])
            EE.write_bytes(base + 1, [int(body["value"]) & 0xFF])  # data byte only
        elif name == "adb_bypass":
            EE.write_bytes(0x0441, [0xFF])
            EE.write_bytes(0x0A81, [0xFF])
        elif name == "adb_relock":
            EE.write_bytes(0x0441, [0x00])
            EE.write_bytes(0x0A81, [0x00])
        elif name == "debug_on":
            EE.write_bytes(0x0B41, [0x01])
        elif name == "debug_off":
            EE.write_bytes(0x0B41, [0x00])
        elif name == "set_vin":
            if body.get("learn"):
                EE.write_bytes(VIN_DATA, [0xFF] * VIN_LEN)
            else:
                vin = str(body.get("value", "")).upper()
                if len(vin) > VIN_LEN:
                    raise ValueError(f"VIN max {VIN_LEN} chars.")
                if any(not (32 <= ord(c) < 127) for c in vin):
                    raise ValueError("VIN must be printable ASCII.")
                chars = [ord(c) for c in vin] + [0xFF] * (VIN_LEN - len(vin))
                EE.write_bytes(VIN_DATA, chars)
        else:
            raise ValueError(f"Unknown action: {name}")


# ── Frontend (single embedded page) ─────────────────────────────────────────

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>GM IOK EEPROM Editor</title>
<style>
 :root{--bg:#0e1116;--panel:#161b22;--line:#2a313c;--fg:#d7dde5;--mut:#8b97a7;
       --good:#2ea043;--bad:#cf3b3b;--warn:#d29922;--neutral:#4b5563;--accent:#388bfd;}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);
   font:13px/1.5 -apple-system,Segoe UI,Roboto,monospace}
 header{position:sticky;top:0;background:#0b0e13;border-bottom:1px solid var(--line);
   padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:5}
 header h1{font-size:14px;margin:0;color:#fff} .grow{flex:1}
 select,input,button{background:#0d1117;color:var(--fg);border:1px solid var(--line);
   border-radius:6px;padding:5px 8px;font:inherit}
 button{cursor:pointer} button:hover{border-color:var(--accent)}
 button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
 button.danger{border-color:var(--bad);color:#ff8c8c}
 button.good{border-color:var(--good);color:#7ee787}
 main{max-width:1120px;margin:0 auto;padding:16px;display:grid;gap:16px}
 .panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
 .panel h2{margin:0 0 4px;font-size:13px;color:#fff;letter-spacing:.3px;text-transform:uppercase}
 .panel .sub{color:var(--mut);font-size:11px;margin-bottom:10px;
   border-bottom:1px solid var(--line);padding-bottom:8px}
 table{width:100%;border-collapse:collapse} td,th{padding:7px 8px;text-align:left;
   border-bottom:1px solid #20262f;vertical-align:middle} th{color:var(--mut);font-weight:600;font-size:11px;
   text-transform:uppercase;letter-spacing:.3px}
 .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-weight:700;font-size:11px;white-space:nowrap}
 .good{background:rgba(46,160,67,.16);color:#7ee787}
 .bad{background:rgba(207,59,59,.16);color:#ff8c8c}
 .warn{background:rgba(210,153,34,.16);color:#f0c674}
 .neutral{background:rgba(120,130,150,.16);color:#aab4c2}
 .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
 .mut{color:var(--mut)} .addr{color:#79c0ff}
 .note{color:var(--mut);font-size:11px;margin-top:2px}
 .interp{color:#7ee787;font-size:11px;margin-top:2px}
 .resetby{color:#f0c674;font-size:10.5px;margin-top:2px;opacity:.85}
 .secrow td{background:rgba(207,59,59,.08)}
 .risk-high{color:#ff8c8c} .risk-med{color:#f0c674}
 .row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
 .opt{padding:3px 9px;font-size:12px;border-radius:6px}
 .opt.cur{background:var(--accent);border-color:var(--accent);color:#fff}
 .opt.def{box-shadow:inset 0 0 0 1px var(--warn)}
 .hexin{width:54px;text-align:center}
 .deftag{font-size:10px;color:var(--mut);white-space:nowrap}
 .modbadge{font-size:10px;font-weight:700;color:#f0c674;background:rgba(210,153,34,.16);
   padding:1px 6px;border-radius:5px;margin-left:6px}
 .hexview{white-space:pre;font-family:ui-monospace,Menlo,monospace;background:#0a0d12;
   border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto;max-height:340px;font-size:12px}
 input.val{width:84px}
 #toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#1c2430;
   border:1px solid var(--line);padding:10px 16px;border-radius:8px;opacity:0;transition:.2s;pointer-events:none}
 #toast.show{opacity:1} .dirty{color:var(--warn);font-weight:700}
 .small{font-size:11px} .empty{color:var(--mut);padding:40px;text-align:center}
 .quick{background:#10151c;border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:12px}
 .upbtn{position:relative;overflow:hidden}
 .upbtn input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer}
 .infonote{background:#10151c;border:1px solid var(--line);border-left:3px solid var(--warn);
   border-radius:6px;padding:10px 12px;color:var(--mut);font-size:12px;line-height:1.6}
</style></head><body>
<header>
  <h1>GM IOK EEPROM Editor</h1>
  <span class="mut small">M24C64 · 8 KB</span>
  <button class="primary upbtn">Upload dump<input type="file" accept=".bin,application/octet-stream"
    onchange="uploadFile(this.files[0])"></button>
  <span class="mut small">or</span>
  <select id="fileSel"></select><button onclick="loadSel()">Load</button>
  <span class="grow"></span>
  <span id="fileInfo" class="mut small"></span>
  <button class="danger" onclick="revert()">Revert</button>
  <button class="primary" onclick="saveAs()">Save As…</button>
</header>
<main id="app"><div class="empty">Upload an EEPROM dump, or pick a known dump and click Load.</div></main>
<div id="toast"></div>
<script>
let S=null;
const $=s=>document.querySelector(s);
function toast(m,ok=true){const t=$('#toast');t.textContent=m;t.style.borderColor=ok?'#2ea043':'#cf3b3b';
  t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2400);}
async function api(path,body){
  const o=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};
  const r=await fetch(path,o);const j=await r.json();
  if(j.error){toast(j.message||j.error,false);throw new Error(j.error);}
  return j;}
function hx(n,w=2){return '0x'+n.toString(16).toUpperCase().padStart(w,'0');}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

async function boot(){const j=await api('/api/state');fillFiles(j);if(j.loaded){S=j;render();}}
function fillFiles(j){const s=$('#fileSel');s.innerHTML='';
  (j.files||[]).forEach(f=>{const o=document.createElement('option');o.value=f;o.textContent=f;s.appendChild(o);});}
async function loadSel(){const f=$('#fileSel').value;if(!f)return;
  S=await api('/api/load',{path:f});render();toast('Loaded '+f);}
async function uploadFile(file){if(!file)return;
  const buf=await file.arrayBuffer();
  const r=await fetch('/api/upload?name='+encodeURIComponent(file.name),
    {method:'POST',headers:{'Content-Type':'application/octet-stream'},body:buf});
  const j=await r.json();
  if(j.error){toast(j.error,false);return;}
  S=j;render();toast('Uploaded '+file.name+' ('+file.size+' bytes)');}
async function revert(){if(!S){return;} if(!confirm('Discard all in-memory edits and reload original bytes?'))return;
  S=await api('/api/revert');render();toast('Reverted to original');}
async function saveAs(){if(!S)return;
  const def=(S.name||'dump.bin').replace(/\.bin$/,'')+'_edited.bin';
  let p=prompt('Save to path (relative paths resolve to the EEPROM folder):',def);
  if(!p)return;
  let r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({path:p})});let j=await r.json();
  if(j.error==='refuse_overwrite'){
     if(!confirm('That is the ORIGINAL file. Overwrite it?'))return;
     r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({path:p,confirm_overwrite:true})});j=await r.json();}
  if(j.error){toast(j.error,false);return;}
  toast('Saved → '+j.saved);S=j.state;render();}

async function setByte(addr,value){S=await api('/api/write',{addr,values:[value&0xFF]});render();}
async function setByteHex(addr,hexval){const v=parseInt(hexval,16);
  if(isNaN(v)){toast('Bad hex',false);return;} setByte(addr,v);}
async function action(a){S=await api('/api/action',{action:a});render();toast(a.replace(/_/g,' ')+' applied');}
async function setVin(){const v=$('#vinInput').value.trim();
  S=await api('/api/action',{action:'set_vin',value:v});render();toast('VIN set');}
async function vinLearn(){if(!confirm('Set VIN to all 0xFF (learn / relearn mode)?'))return;
  S=await api('/api/action',{action:'set_vin',learn:true});render();toast('VIN → learn mode (0xFF)');}
async function writeRaw(){
  const a=parseInt($('#rawAddr').value,16);
  const bytes=$('#rawBytes').value.trim().split(/\s+/).map(x=>parseInt(x,16));
  if(isNaN(a)||bytes.some(isNaN)){toast('Bad address or bytes',false);return;}
  S=await api('/api/write',{addr:a,values:bytes});render();toast('Wrote '+bytes.length+' byte(s) @ '+hx(a,4));}

function render(){
  $('#fileInfo').innerHTML=(S.name?('<span class=addr>'+esc(S.name)+'</span> · '):'')
    +(S.sha256?('<span class=mut title="SHA-256 of current bytes">sha '+S.sha256.slice(0,12)+'</span> · '):'')
    +(S.diff&&S.diff.length?('<span class=dirty>'+S.diff.length+' byte(s) modified</span>'):'<span class=mut>no edits</span>');
  const a=$('#app');a.innerHTML='';
  a.appendChild(verdictPanel());
  a.appendChild(secPanel());
  a.appendChild(idPanel());
  a.appendChild(featPanel());
  a.appendChild(uiPanel());
  a.appendChild(crcPanel());
  a.appendChild(comparePanel());
  a.appendChild(diffPanel());
  a.appendChild(hexPanel());
  loadHex();
}

function verdictPanel(){const p=panel('Configuration verdict','Auto-assessment of the loaded dump.');
  const wrap=document.createElement('div');wrap.className='row';
  (S.fingerprint||[]).forEach(t=>{const s=document.createElement('span');
    s.className='pill '+t.css;s.style.fontSize='12px';s.textContent=t.text;wrap.appendChild(s);});
  p.appendChild(wrap);return p;}
function panel(title,sub){const p=document.createElement('div');p.className='panel';
  p.innerHTML='<h2>'+esc(title)+'</h2>'+(sub?'<div class="sub">'+esc(sub)+'</div>':'');return p;}

// Unified row used by Security / Feature / UI sections.
function flagRows(items){
  const t=document.createElement('table');
  t.innerHTML='<tr><th>Flag</th><th>Addr</th><th>Marker</th><th>State</th><th>Set</th><th>Default</th></tr>';
  items.forEach(f=>{
    const opts=(f.options||[]).map(o=>{
      const cur=o.val===f.value, def=o.val===f.orig;
      return `<button class="opt ${cur?'cur':''} ${def?'def':''}"
        title="${def?'default state':''}" onclick="setByte(${f.data_addr},${o.val})">${esc(o.label)}</button>`;
    }).join('');
    const risk=f.risk?`<span class="risk-${f.risk}">●</span> `:'';
    const interp=f.interp?('<div class="interp">→ '+esc(f.interp)+'</div>'):'';
    const reset=f.reset_by?('<div class="resetby" title="'+esc(f.reset_by)+'">⟲ reverts on SPS programming (cal SW ID 7/13)</div>'):'';
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${risk}${esc(f.name)}${f.note?('<div class="note">'+esc(f.note)+'</div>'):''}${interp}${reset}</td>
      <td class="addr mono">${hx(f.addr,4)}</td>
      <td class="mono mut">${f.marker!=null?hx(f.marker):'—'}</td>
      <td><span class="pill ${f.css}">${esc(f.label)}</span>${f.modified?'<span class="modbadge">MOD</span>':''}</td>
      <td class="row">${opts}
        <input class="hexin mono" value="${hx(f.value).slice(2)}"
          onkeydown="if(event.key=='Enter')setByteHex(${f.data_addr},this.value)"></td>
      <td class="deftag">def ${hx(f.orig)}</td>`;
    t.appendChild(tr);});
  return t;
}

function secPanel(){
  const p=panel('ADB security flags','Marker-preserving — edits only the data byte at base+1. Markers are runtime-generated, so values are what matter.');
  const q=document.createElement('div');q.className='quick row';
  q.innerHTML=`<span class="mut small">Quick:</span>
    <button class="good" onclick="action('adb_bypass')">Apply ADB bypass</button>
    <button class="danger" onclick="action('adb_relock')">Re-lock</button>
    <button onclick="action('debug_on')">Debug ON</button>
    <button onclick="action('debug_off')">Debug OFF</button>`;
  p.appendChild(q);
  p.appendChild(flagRows(S.security));
  return p;}

function idPanel(){const p=panel('Vehicle / module identity');
  // VIN editor (highlighted)
  const vin=S.strings.find(s=>s.vin);
  if(vin){const box=document.createElement('div');box.className='quick';
    const chk = vin.learn ? '' :
      (vin.check_ok===true ? '<span class="pill good">check digit OK</span>'
       : vin.check_ok===false ? '<span class="pill bad">check digit INVALID</span>' : '');
    box.innerHTML=`<div class="row">
      <b>VIN</b> <span class="addr mono">${hx(vin.data_addr,4)}</span>
      <span class="pill ${vin.learn?'warn':'good'}">${vin.learn?'LEARN MODE (all 0xFF)':'PROGRAMMED'}</span>
      ${chk}
      ${vin.modified?'<span class="modbadge">MOD</span>':''}
      <input id="vinInput" class="mono" style="width:200px" maxlength="17"
        value="${esc(vin.learn?'':vin.value)}" placeholder="17-char VIN">
      <button class="good" onclick="setVin()">Set VIN</button>
      <button class="danger" onclick="vinLearn()">Set learn mode (0xFF)</button>
    </div>${vin.decoded?('<div class="note">'+esc(vin.decoded)+'</div>'):''}`;
    p.appendChild(box);}
  // Other identity strings (read-only)
  const t=document.createElement('table');
  t.innerHTML='<tr><th>Field</th><th>Base</th><th>Marker</th><th>Value (ASCII)</th></tr>';
  S.strings.filter(s=>!s.vin).forEach(f=>{const tr=document.createElement('tr');
    tr.innerHTML=`<td>${esc(f.name)}${f.modified?'<span class="modbadge">MOD</span>':''}</td>
      <td class="addr mono">${hx(f.base,4)}</td>
      <td class="mono mut">${f.marker!=null?hx(f.marker):'—'}</td>
      <td class="mono">${esc(f.value)||'<span class=mut>(empty)</span>'}</td>`;
    t.appendChild(tr);});
  p.appendChild(t);
  const n=document.createElement('div');n.className='note';n.style.marginTop='8px';
  n.textContent='Non-VIN identity strings are read-only here — use the Raw byte editor below to change them (each char = one ASCII byte starting at base+1).';
  p.appendChild(n);return p;}

function featPanel(){
  const p=panel('Feature flags & undocumented candidates','Suspected values shown as buttons even where ON/OFF semantics are unproven. The outlined button is the default (pre-edit) value.');
  p.appendChild(flagRows(S.features));return p;}

function uiPanel(){
  const p=panel('UI flags block @ 0x0E80','Marker '+hx(S.ui_marker)+'. Bitfield rows expose the hex input only.');
  p.appendChild(flagRows(S.ui));return p;}

function crcPanel(){const p=panel('CRC / integrity','Structure: [marker][3-byte version counter][2-byte CRC16][marker].');
  const t=document.createElement('table');
  t.innerHTML='<tr><th>Field</th><th>Base</th><th>Version counter</th><th>CRC16</th><th>Raw</th></tr>';
  S.crcs.forEach(f=>{const tr=document.createElement('tr');
    if(f.kind==='std'){
      tr.innerHTML=`<td>${esc(f.name)}</td><td class="addr mono">${hx(f.base,4)}</td>
        <td class="mono">${hx(f.counter,6)} <span class="mut">(${f.counter})</span></td>
        <td class="mono">${hx(f.crc16,4)}</td><td class="mono mut">${f.raw}</td>`;
    }else{
      tr.innerHTML=`<td>${esc(f.name)}</td><td class="addr mono">${hx(f.base,4)}</td>
        <td class="mut">—</td><td class="mut">—</td><td class="mono mut">${f.raw}</td>`;}
    t.appendChild(tr);});
  p.appendChild(t);
  const n=document.createElement('div');n.className='infonote';n.style.marginTop='10px';
  n.innerHTML='<b>Can these CRCs be regenerated/corrected? No — and it is not necessary.</b> '
    +'Confirmed by reverse-engineering the VIP firmware (Y181, RH850): the firmware contains exactly <b>one</b> '
    +'CRC engine — a table-driven CRC16-CCITT at 0x8059a — and it is used <b>only by the HDLC/IPC serial link</b> '
    +'(TX 0x80712 / RX 0x80d9e), never by the EEPROM. No cal/NVM/EEPROM code computes or verifies a CRC. '
    +'Brute-forcing every standard CRC16 against the stored field/counter pairs yields no match, so the 2-byte '
    +'value here is <b>not a standard CRC</b> of the counter. On the read side the SBI/cal bytes are taken raw into '
    +'the RAM mirror (0xfebd38ea) with no checksum and a non-fatal fallback to ROM defaults; VIP_BOOT enforces no '
    +'EEPROM CRC at boot (a VIN wiped to 0xFF still boots). The tool therefore deliberately does <b>not</b> fabricate '
    +'a "fix CRC" button. A stale CRC is harmless for boot; re-lock of edits happens via signed SPS cals, not a CRC.';
  p.appendChild(n);return p;}

function comparePanel(){const p=panel('Compare against a reference dump','Diff the working buffer vs. another dump; security-relevant bytes are flagged.');
  const sel=(S.files||[]).map(f=>`<option value="${esc(f)}">${esc(f)}</option>`).join('');
  const bar=document.createElement('div');bar.className='row';bar.style.marginBottom='10px';
  bar.innerHTML=`<span class="mut">Reference:</span> <select id="cmpSel">${sel}</select>
    <button onclick="runCompare()">Compare</button>
    <span class="grow"></span>
    <button onclick="downloadReport()">Download change report</button>`;
  p.appendChild(bar);
  const out=document.createElement('div');out.id='cmpOut';out.className='mut small';
  out.textContent='Pick a reference dump and click Compare.';
  p.appendChild(out);return p;}
async function runCompare(){const ref=$('#cmpSel').value;if(!ref)return;
  const j=await api('/api/compare',{path:ref});
  const out=$('#cmpOut');
  if(!j.deltas.length){out.innerHTML='<span class=good>Identical</span> to '+esc(j.ref)+'.';return;}
  let rows=j.deltas.map(d=>`<tr class="${d.security?'secrow':''}">
    <td class="addr mono">${hx(d.addr,4)}</td><td class="mono">${hx(d.cur)}</td>
    <td class="mono">${hx(d.ref)}</td>
    <td>${d.security?'<span class="pill bad">SEC</span> ':''}${esc(d.label)||'<span class=mut>—</span>'}</td></tr>`).join('');
  out.innerHTML=`<div class="note" style="margin-bottom:6px">${j.deltas.length} differing byte(s) vs <b>${esc(j.ref)}</b>`
    +`, ${j.sec_count} in security regions. (current → reference)</div>`
    +`<table><tr><th>Addr</th><th>Current</th><th>Reference</th><th>Field</th></tr>${rows}</table>`;}
function downloadReport(){window.location='/api/report';}

function diffPanel(){const p=panel('Pending edits (vs. loaded original)');
  if(!S.diff||!S.diff.length){p.innerHTML+='<div class="mut small">No changes in memory.</div>';return p;}
  const t=document.createElement('table');
  t.innerHTML='<tr><th>Address</th><th>Was</th><th>Now</th></tr>';
  S.diff.forEach(d=>{const tr=document.createElement('tr');
    tr.innerHTML=`<td class="addr mono">${hx(d.addr,4)}</td><td class="mono">${hx(d.was)}</td>
      <td class="mono"><span class="pill warn">${hx(d.now)}</span></td>`;
    t.appendChild(tr);});
  p.appendChild(t);return p;}

function hexPanel(){const p=panel('Raw hex viewer / editor');
  const d=document.createElement('div');
  d.innerHTML=`<div class="row" style="margin-bottom:10px">
     <span class="mut">Write:</span> addr <input id="rawAddr" class="val mono" placeholder="0x0441" value="0x0000">
     bytes <input id="rawBytes" class="mono" style="width:200px" placeholder="FF 00 5A">
     <button onclick="writeRaw()">Write bytes</button>
     <span class="grow"></span>
     <span class="mut">View:</span> from <input id="hexStart" class="val mono" value="0x0400">
     len <input id="hexLen" class="val mono" value="0x100">
     <button onclick="loadHex()">Show</button></div>
     <div class="hexview" id="hexout">…</div>`;
  p.appendChild(d);return p;}
async function loadHex(){const s=$('#hexStart'),l=$('#hexLen');if(!s||!l)return;
  const j=await api('/api/hex?start='+encodeURIComponent(s.value)+'&len='+encodeURIComponent(l.value));
  $('#hexout').textContent=j.text;}
boot();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="GM IOK EEPROM editor (local web UI)")
    ap.add_argument("file", nargs="?", help="EEPROM .bin to load on start")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if args.file:
        try:
            EE.load(args.file)
            print(f"Loaded {args.file}")
        except Exception as e:
            print(f"Could not load {args.file}: {e}", file=sys.stderr)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), Handler) as srv:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"EEPROM editor → {url}  (Ctrl-C to stop)")
        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
