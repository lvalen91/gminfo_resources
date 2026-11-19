#!/usr/bin/env python3
"""
GM IOK (Info 3.7/3.8 CSM) EEPROM Editor — ST M24C64 (8 KB) dumps.

A zero-dependency, single-file local web UI for inspecting and editing
GM Harman infotainment EEPROM flash dumps. Built from the research in
EEPROM_Analysis_Report.md, EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md and
research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md (§0.15 = the 2026-10-15
clean-room triple-pass that added the ECU-ID / HW-part-number / F198 / F199 /
0x1DC0 fields below and corrected 0x14A0 + 0x0680).

KEY DESIGN PRINCIPLE — marker bytes are runtime-generated (CalGroup), so the
tool NEVER assumes a fixed framing marker. For every flag it reads the LIVE
marker at the base address and edits ONLY the data byte at base+1, preserving
whatever marker the firmware assigned. (Report §"Framing Protocol", Feb 2026.)

Field lists are data-driven: SECURITY_FLAGS / STRING_FIELDS / BINARY_FIELDS /
FEATURE_FLAGS / UI_FLAGS / CRC_FIELDS each feed build_state() (JSON for the
browser) and build_address_labels() (diff/compare annotation). Add a field to
the list and it renders; nothing is hard-wired in the HTML.

Every field carries a "conf" evidence tag (CONFIRMED / PLAUSIBLE / UNCONFIRMED)
that renders as a pill in the UI, so a confident-sounding label can never again
drift away from its backing silently. A 2026-10-15 six-agent survey (cross-checked
against 5 real dumps + the raw VIP firmware) corrected several claims this file
once asserted: 0x0500 is the MTC tail, NOT a part number (with 0x0520/0x0540/0x0560
being the other MTC fragments, not HW version/revision); the 0x1DC0 payload's two
u32s are UNIX timestamps, NOT a sequence/ID pair differing by 1; 0x0460/0x0480 are
the ECU_GCI End/Base Model Numbers. See the per-field notes for the evidence.

Usage:
    python3 eeprom_editor.py [path/to/dump.bin] [--port 8765] [--no-browser]

Runs at http://127.0.0.1:8765 (localhost only). Stdlib only — works under any
python3 (no tkinter, no pip). Upload a dump in the browser, or pick one of the
known dumps from the dropdown. The original file is never overwritten unless you
explicitly Save As to the same path; edits live in memory until you save.
"""

import argparse
import datetime
import hashlib
import http.server
import json
import os
import socketserver
import sys
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

# 2026-10-15: never write .pyc for this tool. A stale config_tool/__pycache__/*.pyc from an
# older revision was observed to be imported in preference to edited source, so the server
# silently served OLD bytecode (e.g. a build_state() missing the whole "binary" JSON key) with
# HTTP 200 and no error -- "it ran without exceptions" proved nothing. Single-file stdlib tool,
# no reason to cache bytecode; disabling it removes the footgun at the source. (Survey 6, Part A.)
sys.dont_write_bytecode = True

EEPROM_SIZE = 8192
# Marker values seen so far. Informational only (see KEY DESIGN PRINCIPLE) -- the
# tool never requires a marker to be one of these; it just flags an unusual one.
KNOWN_MARKERS = {0x5A, 0x69, 0xC3, 0xF0}
DIR = os.path.dirname(os.path.abspath(__file__))
# Dumps live in the parent EEPROM folder (this script sits in config_tool/).
# Relative load/save paths and the file dropdown resolve against DUMP_ROOT.
DUMP_ROOT = os.path.dirname(DIR)

# VIN: [marker][17 ASCII chars][marker][0xFF pad]
VIN_BASE = 0x05C0
VIN_DATA = 0x05C1
VIN_LEN = 17
# 2026-10-15: VIN-tail residual block (last 8 chars of a VIN + " A"), see STRING_FIELDS.
VIN_TAIL_BASE = 0x14A0
VIN_TAIL_LEN = 8

# ── Field definitions (grounded in the analysis docs) ───────────────────────
# Each flag is [marker][data][marker]; we read marker live, edit data at base+1.

SECURITY_FLAGS = [
    {"key": "sbi1", "base": 0x0440, "name": "Primary SBI — NOT ADB-only (field-proven, Aug26)",
     "conf": "CONFIRMED",
     "on": 0xFF, "off": 0x00, "on_label": "Bypass", "off_label": "Lock",
     "states": {0x00: ("LOCKED", "bad"), 0xFF: ("BYPASSED", "good")},
     "static": "Known effect: 0x0441=0xFF → non-zero MEC → ADB does not require the GM client. Y175 read path: Dispatcher A 0xBA316 → CalGroup 0x3B → FUN_00091AEC.",
     "note": "0x00 = secured; 0xFF opens ADB. Aug26: the ADB path IS now confirmed -- VIP "
             "transmits MEC=0xFF via DID 0xF1A0 at boot -> SoC is_secure_mode bypass (boot-log "
             "+ guest RE, EEPROM_LAYOUT §0.10/§0.14). The SBI is ALSO broader than ADB -- "
             "captured bench traffic already shows a "
             "plain CAN UDS $27 request to ECU 0x80 (VIP) returns the same degenerate "
             "all-0xFF seed with this flipped (diagnostics/dps/A11_CSM_x80.Txt). The "
             "VIP's seed/key logic is one shared function servicing >=18 security "
             "levels (FUN_ram_000b67d0 @ 0xb67d0, verified). Calibration-programming "
             "impact specifically is a strong hypothesis, not yet confirmed -- see "
             "eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md. Storage: CalGroup 0x3b, "
             "cells 0x43a-0x447 (vip_app.bin FUN_ram_00091938) -- see "
             "eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md."},
    {"key": "sbi2", "base": 0x0A80, "name": "Backup SBI — mechanism NOT located (Aug26)",
     "conf": "UNCONFIRMED",
     "on": 0xFF, "off": 0x00, "on_label": "Bypass", "off_label": "Lock",
     "states": {0x00: ("LOCKED", "bad"), 0xFF: ("BYPASSED", "good")},
     "note": "Was 0xFF (empty) pre-Y181; now actively initialized. Aug26 correction: "
             "the 'both SBIs must match' claim below is UNVERIFIED and likely wrong as "
             "stated -- exhaustive static analysis of BOTH vip_app.bin and vip_boot.bin "
             "found ZERO code references to 0x0A80/0x0A81 via the confirmed EEPROM-cell "
             "accessor, and zero as a literal operand anywhere in either binary (real "
             "neighboring CalGroup 0x9b proves the region isn't generally dead). The "
             "empirical bypass-works observation is NOT in question -- only the "
             "mechanism/claim about how it relates to sbi1 is. See "
             "eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md §5."},
    {"key": "debug", "base": 0x0B40, "name": "0x0B41 calibration byte — debug meaning unproven",
     "conf": "UNCONFIRMED",
     "on": 0x01, "off": 0x00, "on_label": "0x01", "off_label": "0x00",
     "states": {0x00: ("0x00", "neutral"), 0x01: ("0x01", "warn")},
     "static": "Y175: Dispatcher A 0xBA48A → CalGroup 0xA3 → FUN_0009414A (also recovered in FUN_0008EAE4). Read/validate path; no debug consumer found.",
     "note": "The cell is genuinely read by VIP_APP, but no recovered consumer names it as a "
             "developer/debug control. Bench tests of 0x00, 0x01, and 0xFF reported no observed "
             "effect. It must not be presented as Debug/Developer Mode or as an enable control."},
]

# Best-effort ASCII string fields: [marker][ascii...][marker][0xFF pad]
# Optional "note" renders under the name in the identity panel. Binary (non-ASCII)
# identity fields live in BINARY_FIELDS below -- never add them here, parse_string()
# stops at the first non-printable byte and would silently truncate them.
#
# "conf" = evidence confidence, surfaced in the UI as a pill (CONFIRMED / PLAUSIBLE /
# UNCONFIRMED). It exists so a confident-sounding label can never again drift away from
# its evidence silently -- if a claim is a guess, the UI says so. Keep it honest.
STRING_FIELDS = [
    {"key": "vin",      "base": VIN_BASE, "maxlen": 24, "name": "VIN", "vin": True,
     "conf": "CONFIRMED"},
    # ── Manufacturing Traceability Code (MTC) ────────────────────────────────
    # 2026-10-15 correction (survey 3, digit-exact): 0x0500 is NOT a GM "Part Number".
    # It is the 9-digit TAIL of the 16-digit MTC (SPSVCS.LOG `mtc` / `infokey`), and the
    # neighbouring 0x0520/0x0540/0x0560 "HW version/revision" guesses are the other MTC
    # fragments, not version fields. Assembled order region(0x04E1)+0x0561+0x0541+0x0521+
    # 0x0501 reproduces `4225051170003205` exactly (26_HC_A11 SPSVCS.LOG). The assembled
    # value is shown as a derived row (see assemble_mtc() / build_state()).
    {"key": "mtc_tail", "base": 0x0500, "maxlen": 24, "mtc": 5,
     "name": "MTC tail (9 digits, SPS `mtc`/`infokey` — NOT a part number)",
     "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): trailing 9 digits of the 16-digit Manufacturing Traceability "
             "Code, digit-exact against 26_HC_A11 SPSVCS.LOG `mtc`/`infokey`. The old 'Part Number' "
             "label was wrong -- no 8-digit GM part number in any SPS log matches these 9 digits."},
    {"key": "mtc_g3",   "base": 0x0520, "maxlen": 16, "mtc": 4,
     "name": "MTC fragment (3 digits; was mislabelled 'HW Version')", "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): MTC digits, not a HW version field. Position-confirmed in the "
             "16-digit reconstruction."},
    {"key": "mtc_g2",   "base": 0x0540, "maxlen": 16, "mtc": 3,
     "name": "MTC fragment (2 digits; was mislabelled 'Revision')", "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): MTC digits, not a revision field."},
    {"key": "mtc_g1",   "base": 0x0560, "maxlen": 16, "mtc": 2,
     "name": "MTC fragment (1 digit; was mislabelled 'HW Rev')", "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): MTC digits, not a HW-rev field."},
    # 2026-10-15: qualified "manufacture" to distinguish it from the BCD reprogramming
    # date (UDS DID F199) at 0x06A0 in BINARY_FIELDS (EEPROM_LAYOUT §2.5).
    {"key": "progdate", "base": 0x0580, "maxlen": 16, "name": "Programming Date (manufacture, ASCII)",
     "conf": "PLAUSIBLE"},
    # 2026-10-15: teardown.md reads the same bytes as a CVPPS "Calibration file ID";
    # EEPROM_Analysis_Report.md keeps "Serial Number". Unresolved -- both shown.
    {"key": "serial",   "base": 0x05A0, "maxlen": 24, "name": "Serial Number (CVPPS value; teardown: cal-file ID)",
     "conf": "UNCONFIRMED"},
    # 0x04E1 is both a plausible region/plant digit AND the first digit of the MTC (shared
    # storage, not an independent field -- survey 3). Kept as its own row because it is the
    # MTC's leading digit; "mtc": 1 wires it into the assembled value.
    {"key": "region",   "base": 0x04E0, "maxlen": 8,  "mtc": 1,
     "name": "Region/plant digit (also MTC digit 1)", "conf": "PLAUSIBLE",
     "note": "2026-10-15 (survey 3): a single digit that is also the leading character of the "
             "16-digit MTC -- shared storage, not a separately-stored region field. 'Region code' "
             "is a reasonable interpretation of the leading plant/region digit, not confirmed."},
    # 2026-10-15 correction (was key "unit" / "Unit Serial"): this is the SPS shop/dealer
    # code, UDS DID F198 -- the SPSVCS.LOG `shopcode` field. In the analyzed dump the
    # stored 10 chars were a truncation of the 11-digit code logged by the SPS tool
    # (EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md §0.15 / §2.5). Not a generic unit serial.
    {"key": "shopcode", "base": 0x0680, "maxlen": 24, "name": "Shop/dealer code (UDS DID F198, SPS `shopcode`)",
     "conf": "CONFIRMED",
     "note": "2026-10-15: confirmed against the SPS tool's `shopcode` field (UDS DID F198). The EEPROM "
             "holds 10 chars; the SPS log showed an 11-digit code, so the field is a truncation. "
             "Was labelled 'Unit Serial' here and 'Repair-shop SN' in eeprom/README.md -- the "
             "README name was closer."},
    # 2026-10-15: name tightened; full mechanism in "note". Not a Firmware ID (that label
    # was retired in a prior pass). Format observed: 8 VIN chars + " A" + 0x00.
    {"key": "vin_tail", "base": VIN_TAIL_BASE, "maxlen": 24,
     "name": "VIN-tail residual (last 8 of a VIN; can be STALE)",
     "conf": "CONFIRMED",
     "note": "2026-10-15 (EEPROM_LAYOUT §0.15): mirrors whichever VIN was active when its NvM block "
             "was last written -- it is NOT a live copy of 0x05C1. After a re-VIN/reprogram it can "
             "retain the PREVIOUS vehicle's VIN tail: proven by two SPS sessions on the same ECUID "
             "where the module moved vehicles and this field did not update. Firmware strings "
             "cal_vin_relearn_en / Theftlocked corroborate a VIN-relearn/theft-lock retention "
             "mechanism. The pill at right compares chars 1-8 with the current VIN's last 8."},
]

# MTC assembly order: list of STRING_FIELDS "mtc" rank -> fragment. The 16-digit code is
# region(rank1) + 0x0560(2) + 0x0540(3) + 0x0520(4) + 0x0500(5), per survey 3's digit-exact
# reconstruction (`4225051170003205`). Driven off the "mtc" keys above so it can't drift.
MTC_LEN = 16

# ── Raw binary identity fields (2026-10-15) ───────────────────────────────────
# [marker][len data bytes][marker]. NOT ASCII -- never route these through parse_string().
# "decode" picks the display decoder in decode_binary(); raw hex is always shown too.
# All from the clean-room triple-pass, EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md §0.15 / §2.3 / §2.5.
BINARY_FIELDS = [
    {"key": "ecuid", "base": 0x03A0, "len": 16, "decode": "hex",
     "name": "ECU-ID (16 bytes, SPS `ECUID`)", "conf": "CONFIRMED",
     "note": "2026-10-15: confirmed byte-exact against the SPS tool's SPSVCS.LOG `ECUID` field in two "
             "independent SPS sessions on the same physical module (§0.15). Raw binary, not ASCII. "
             "Module identity -- treat as a device serial. Probably the ECUID the VIP folds into the "
             "real (non-bypassed) UDS $27 seed (UNDOC doc: seed = ECUID + challenge), but that link "
             "is an inference, not independently confirmed."},
    # 2026-10-15 correction (survey 3): the value matches ECU_GCI_JSON "End Model Number", NOT the
    # SPS `ssecuhn` field (which reads 0 in every SPSVCS.LOG VIT2 record). Relabelled accordingly.
    {"key": "hwpn", "base": 0x0460, "len": 4, "decode": "be_u32",
     "name": "End Model Number (BE u32, ECU_GCI `End Model Number`)", "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): big-endian u32 = 85086705 (0x051251F1) in the analyzed dump; "
             "byte-exact match to ECU_GCI_JSON `End Model Number` for ecu_adr 80. Earlier passes "
             "called it SPS `ssecuhn` -- that is a DIFFERENT, separate field that reads 0 in the logs, "
             "so the ssecuhn label was wrong. (Also corrects the older 'Radio/Audio Settings' guess "
             "for the 0x0460 region.)"},
    # 2026-10-15 correction (survey 3): identified. Matches ECU_GCI_JSON "Base Model Number".
    {"key": "hwpn_b", "base": 0x0480, "len": 4, "decode": "be_u32",
     "name": "Base Model Number (BE u32, ECU_GCI `Base Model Number`)", "conf": "CONFIRMED",
     "note": "2026-10-15 (survey 3): big-endian u32 = 84999439 in the analyzed dump; byte-exact match "
             "to ECU_GCI_JSON `Base Model Number`. Same [marker][BE u32][marker] shape as 0x0460. "
             "Previously labelled UNIDENTIFIED (\"not found in any source\") -- now confirmed."},
    {"key": "progdate_f199", "base": 0x06A0, "len": 4, "decode": "bcd_date",
     "name": "Reprogramming date (UDS DID F199, BCD)", "conf": "CONFIRMED",
     "note": "2026-10-15: four BCD bytes YY YY MM DD -- e.g. 20 26 09 28 = 2026-09-28 -- matching the "
             "firmware's `DIDF199` NvM string and the SPS `progdate` field format. In the analyzed dump "
             "this POST-DATED the most recent logged SPS session (progdate 20260707): the module was "
             "reprogrammed again after the available logs end. Distinct from the ASCII manufacture "
             "date at 0x0580 (§0.15 / §2.5)."},
    {"key": "hwpn2", "base": 0x06E0, "len": 4, "decode": "hex",
     "name": "HW part-number word #2", "conf": "CONFIRMED",
     "note": "2026-10-15: raw bytes 60 02 02 B1, matched against the VIP boot-log line "
             "\"Send HW Partnum 0x60 0x2 0x2 0xb1\" (VIP_log_2B.174.4.1_10JUL24.txt, same log as "
             "§0.14). Previously unidentified in every prior pass (§0.15)."},
]

# Single-byte feature toggles (data byte at base+1). From report tables.
# Suspected values are surfaced as buttons even where on/off semantics are unknown.
FF = [0x00, 0x01, 0xFF]   # default option set
FEATURE_FLAGS = [
    {"base": 0x0000, "name": "Boot/Init complete flag", "risk": "high", "options": FF,
     "note": "Header. Corrupting may make EEPROM look virgin."},
    {"base": 0x0020, "name": "Byte 0x0021 — purpose unknown", "risk": "med", "options": FF,
     "conf": "PLAUSIBLE", "static": "Y175: Dispatcher A 0xBA46C → CalGroup 0x01 → FUN_0008FEA8. Read/validate path; semantic consumer unknown.",
     "note": "A real VIP_APP accessor cell, not a recovered boot-mode flag. No semantic action is proven."},
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
    {"base": 0x1A00, "name": "CLOSED — no code reference found (Aug26)", "risk": "low", "options": FF,
     "note": "Aug26 correction: the 'tertiary security' label was part of the retracted "
             "string-count taxonomy (EEPROM_LAYOUT §0). Full-coverage RH850 RE found no "
             "code reference to 0x1A00 as a security flag. Low-expected-value to test."},
    # Undocumented candidates (EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS §6) --
    # CORRECTED Aug26 against real Ghidra decompilation of vip_app.bin/
    # vip_boot.bin, superseding the original string-count-based "N refs"
    # framing. See eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md.
    {"base": 0x04A0, "name": "CLOSED — no code reference found (Aug26)", "risk": "low", "options": FF,
     "note": "Aug26: exhaustive instruction scan + full accessor-argument scan found "
             "ZERO code references to this address in vip_app.bin or vip_boot.bin. "
             "The one apparent hit is a confirmed false positive (a struct-relative "
             "offset inside an unrelated UDS-style dispatcher). Testing this address "
             "is now low-expected-value; kept here for completeness, not as a lead."},
    {"base": 0x04C0, "name": "Byte 0x04C1 — real calibration cell; purpose unknown", "risk": "high", "options": FF,
     "conf": "PLAUSIBLE",
     "static": "Y175: Dispatcher A 0xBA05E → CalGroup 0x44 → FUN_00092136. Read/validate path; semantic consumer unknown.",
     "note": "It is a real, separately loaded calibration cell. The consumer and external action "
             "are not recovered; it is not established as a security, debug, or feature enable flag."},
    {"base": 0x0A40, "name": "CLOSED — no code reference found (Aug26)", "risk": "low", "options": FF,
     "note": "Aug26: zero hits in either binary via the confirmed EEPROM-cell "
             "accessor or as a literal operand. Real neighboring CalGroups (0xa26, "
             "0xa5e) confirm the surrounding region isn't generally dead -- just not "
             "at this specific offset. Low-expected-value to test."},
    {"base": 0x0BE0, "name": "CLOSED — no code reference found (Aug26)", "risk": "low", "options": FF,
     "note": "Aug26: zero hits in either binary. Sits 3 bytes past the last real "
             "cell in this region (0xbdd) with nothing found through 0xC00. "
             "Low-expected-value to test."},
    # Trim/theme candidate (channel b) — Aug26. The VIP translates EEPROM config into GMTrim,
    # served to AAOS over IPC (VIPCALPAL) -> animengine AnimFlavor -> boot animation + theme.
    # base is target-1 so the tool edits the exact byte (data_addr shows the real 0x0AA0/0x0AE5).
    {"base": 0x0A9F, "name": "Trim/theme candidate → byte 0x0AA0 (UNCONFIRMED)", "risk": "med",
     "options": [0x69, 0xC3, 0xF0],
     "note": "Byte at 0x0AA0. Observed across trim dumps: stock=0x69, LTZ=0xC3, HighCountry=0xF0. "
             "Candidate for the value the VIP maps to GMTrim (HighCountry=1 / LTZ=16) → AnimFlavor "
             "→ boot animation + AAOS theme. NOT the raw enum (VIP applies an encoding) — UNCONFIRMED. "
             "TEST: on a stock dump set this (+ 0x0AE5) to 0xF0 (HC) or 0xC3 (LTZ), reboot, then "
             "`adb shell getprop persist.sys.anim.flavor` and `adb logcat | grep -i AnimFlavor` — "
             "if GMTrim/AnimFlavor flips, this is the byte. Paired with 0x0AE5."},
    {"base": 0x0AE4, "name": "Trim/theme candidate → byte 0x0AE5 (UNCONFIRMED)", "risk": "med",
     "options": [0x69, 0xC3, 0xF0],
     "note": "Byte at 0x0AE5 (paired with 0x0AA0, ~69 bytes apart — looks like a duplicated/"
             "redundant field). Same observed values: stock=0x69, LTZ=0xC3, HighCountry=0xF0. "
             "Set both 0x0AA0 and 0x0AE5 to match a full trim dump when testing."},
]

# Exact Y175 VIP_APP static-accessor result for editable single-byte candidates.
# Absence here means only that the cell is not in the recovered generic-accessor
# loader set; it is not proof that a raw/bulk or runtime-generated path cannot read it.
STATIC_CELL_EVIDENCE = {
    0x0001: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0021: "Y175: Dispatcher A 0xBA46C → CalGroup 0x01 → FUN_0008FEA8. Read/validate path; semantic consumer unknown.",
    0x04A1: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x04C1: "Y175: Dispatcher A 0xBA05E → CalGroup 0x44 → FUN_00092136. Read/validate path; semantic consumer unknown.",
    0x0A41: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0AA0: "Y175: no recovered generic-accessor loader for this cell; trim/theme meaning unproven.",
    0x0AE5: "Y175: no recovered generic-accessor loader for this cell; trim/theme meaning unproven.",
    0x0B41: "Y175: Dispatcher A 0xBA48A → CalGroup 0xA3 → FUN_0009414A. Read/validate path; no debug consumer found.",
    0x0B81: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0BA1: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0BC1: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0BE1: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x0C01: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x1501: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x15C1: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
    0x1A01: "Y175: no recovered generic-accessor loader for this cell; semantic action unknown.",
}

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

# CRC fields.
#  kind='std'    → [marker][3-byte version counter][2-byte CRC16][marker].
#                  2026-10-15 CONFIRMED (independently re-derived, EEPROM_LAYOUT §0.15, UNDOC
#                  §13.7): the leading counter byte has been 0x00 in every dump seen, so the
#                  3-byte counter == the docs' "[00][2-byte version word]" -- same thing. The
#                  three std blocks move in lockstep (0x0013→0x0104 stock→reflash; 0x0057/0x0058
#                  in the 2026-10-15 dump, e.g. 0x16E0 payload 00 00 58 96 98 → counter 88,
#                  crc16 0x9698). Decode left as-is on purpose.
#  kind='raw'    → opaque bytes. Optional "mirror": {src, off, len} asserts that bytes
#                  base+off.. equal src+1.. (2026-10-15: in both non-blank dumps on hand 0x1A80
#                  bytes +3..+7 are byte-identical to 0x19E0's counter+crc payload -- supports
#                  the "reference copy" label; teardown.md's "MEC NVM value" reading unresolved).
#  kind='seqcrc' → [marker][payload_len bytes][CRC-16 LE][marker]. The trailing CRC is a
#                  CONFIRMED CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, MSB-first, no
#                  refin/refout, no xorout) over the 16 payload bytes, stored little-endian --
#                  independently brute-forced to an exact match across 5 real images (survey 5).
#                  The tool recomputes it live (crc_ok).
#                  2026-10-15 CORRECTION (survey 5): the two leading 32-bit fields are NOT a
#                  "sequence/ID pair differing by exactly 1." Brute-force across 5 images decodes
#                  them as two big-endian u32 UNIX timestamps at payload offsets 6 and 11, with a
#                  gap that is NOT fixed (observed 11 / 421 / 1366 / 13799 s across images -- never
#                  1). The old Δ=1 reading was an artifact of reading one byte early (offset 5/10
#                  caught a leading 0x01 tag byte) on one dump where the boundary happened to line
#                  up; it does not reproduce. ts_offs are the two timestamp payload offsets.
CRC_FIELDS = [
    {"base": 0x16E0, "name": "Primary CRC #1", "kind": "std", "conf": "CONFIRMED",
     "note": "2026-10-15: [00][version word][hash] structure re-confirmed. The three std rows' "
             "version words CLUSTER TIGHTLY across reflashes (shared calibration-generation number) "
             "but do NOT move in exact lockstep -- survey 5 measured a ±1 drift between blocks in 2 "
             "of 5 images (e.g. ADB_enabled 0089/0089/008a). EEPROM_LAYOUT §0.15 / UNDOC §13.7."},
    {"base": 0x19E0, "name": "Secondary CRC #2", "kind": "std", "conf": "CONFIRMED"},
    {"base": 0x1B40, "name": "Data CRC", "kind": "std", "conf": "CONFIRMED"},
    {"base": 0x1A80, "name": "Config CRC (reference copy of 0x19E0)", "kind": "raw", "len": 10,
     "conf": "PLAUSIBLE", "mirror": {"src": 0x19E0, "off": 3, "len": 5}},
    {"base": 0x1DC0, "name": "Timestamp pair + CRC-16/CCITT-FALSE", "kind": "seqcrc",
     "payload_len": 16, "ts_offs": (6, 11), "conf": "PLAUSIBLE",
     "note": "2026-10-15 CORRECTION (survey 5, 5 images): the trailing CRC-16/CCITT-FALSE over the 16 "
             "payload bytes (stored LE) is CONFIRMED -- the only EEPROM block with a verified CRC "
             "algorithm, recomputed live here. The two leading 32-bit fields are two BE u32 UNIX "
             "timestamps (payload offsets 6 and 11), NOT a sequence/ID pair and NOT Δ=1: the gap is "
             "variable (11-13799 s across images). The earlier 'monotonic pair differing by 1' "
             "reading was a one-dump artifact of reading a byte early and does not reproduce. Which "
             "component writes the block (VIP, SoC or SPS tool) is not established."},
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
# Aug26 correction: SBI does NOT drive SELinux. Confirmed chain (boot-log + guest RE):
# SBI 0xFF -> VIP transmits MEC=0xFF (DID 0xF1A0) -> SoC gm_adb_auth_init sets is_secure_mode=1
# -> gm_adb_check_authentication returns ALLOWED with NO GM-cloud cert. SELinux stays ENFORCING
# on every stock build regardless of the SBI (byte-identical init forces enforcing).
SBI_INTERP = {
    0xFF: "ADB open (MEC=0xFF -> is_secure_mode, no cloud cert) · SELinux stays ENFORCING",
    0x00: "Secured · GM cloud-signed ADB policy (VIN/CSM/cert) required",
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


def hexs(buf):
    """'00 4B 41 ...' spaced-hex rendering used everywhere a raw span is shown."""
    return " ".join(f"{b:02X}" for b in buf)


def be_u32(data, addr):
    """Big-endian u32 at addr (the model-number words at 0x0461/0x0481 are stored this way)."""
    return int.from_bytes(data[addr:addr + 4], "big")


def unix_ts(v):
    """Render a u32 as a UTC timestamp string, or '' when it is 0 / not a plausible epoch.

    2026-10-15 (survey 5): the two u32 fields in the 0x1DC0 block are BE UNIX timestamps.
    Guard the range so an unwritten (0x00000000) or garbage field shows '' rather than 1970.
    """
    if not (1_000_000_000 <= v <= 4_000_000_000):  # ~2001-09 .. ~2096
        return ""
    try:
        return datetime.datetime.fromtimestamp(v, datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC")
    except (OverflowError, OSError, ValueError):
        return ""


def bcd_date(raw):
    """Decode 4 BCD bytes YY YY MM DD -> 'YYYY-MM-DD'. None if any nibble isn't 0-9.

    2026-10-15: UDS DID F199 at 0x06A1 (e.g. 20 26 09 28 -> 2026-09-28). Each byte is two
    BCD digits, NOT ASCII digits -- that is why it never belonged in STRING_FIELDS.
    """
    if len(raw) != 4:
        return None
    digits = []
    for b in raw:
        hi, lo = b >> 4, b & 0x0F
        if hi > 9 or lo > 9:
            return None
        digits.append(f"{hi}{lo}")
    s = "".join(digits)
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def crc16_ccitt_false(buf):
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout.

    2026-10-15: confirmed as the algorithm behind the 0x1DC0 block's trailing CRC
    (EEPROM_LAYOUT §0.15). Bitwise, not table-driven -- 16 bytes once per state build.
    """
    crc = 0xFFFF
    for b in buf:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def decode_binary(kind, raw):
    """Human-readable decode of a BINARY_FIELDS span; '' when the hex alone is the answer."""
    if kind == "be_u32":
        v = int.from_bytes(raw, "big")
        return f"{v} (0x{v:08X})"
    if kind == "bcd_date":
        return bcd_date(raw) or "(not valid BCD)"
    return ""


def vin_tail_matches(d):
    """2026-10-15 (§0.15): does the 0x14A1 residual match the CURRENT VIN's last 8 chars?

    True = matches, False = stale (previous vehicle's tail retained after a re-VIN /
    reprogram), None = not comparable (VIN in learn mode or residual empty/short).
    """
    vin, _ = parse_string(d, VIN_BASE, 24)
    tail, _ = parse_string(d, VIN_TAIL_BASE, 24)
    if len(vin) != VIN_LEN or len(tail) < VIN_TAIL_LEN:
        return None
    return tail[:VIN_TAIL_LEN].upper() == vin[-VIN_TAIL_LEN:].upper()


def assemble_mtc(d):
    """Reassemble the 16-digit Manufacturing Traceability Code from its scattered fragments.

    2026-10-15 (survey 3): the MTC (SPSVCS.LOG `mtc`/`infokey`) is stored split across
    region(0x04E1)+0x0561+0x0541+0x0521+0x0501. Concatenating the fragments in STRING_FIELDS
    "mtc"-rank order reproduces e.g. `4225051170003205` digit-for-digit. Returns a dict with
    the assembled value, the ordered pieces, and whether it looks complete (16 digits).
    """
    pieces = []
    for f in sorted((x for x in STRING_FIELDS if "mtc" in x), key=lambda x: x["mtc"]):
        s, _ = parse_string(d, f["base"], f["maxlen"])
        pieces.append({"base": f["base"], "value": s})
    code = "".join(p["value"] for p in pieces)
    return {"code": code, "pieces": pieces, "complete": len(code) == MTC_LEN,
            "conf": "CONFIRMED"}


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
        # Aug26: whether sbi2 must match sbi1 is UNVERIFIED (no code ref to 0x0A81 found) --
        # report the mismatch as a fact, not as a prediction that the bypass fails.
        tags.append(("Primary/backup SBI bytes differ — backup SBI's role is unverified (Aug26)", "warn"))
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
    # 2026-10-15 (§0.15): a stale residual is evidence of a re-VIN / reprogram history.
    if vin_tail_matches(d) is False:
        tags.append(("VIN-tail residual @0x14A1 is STALE — previous vehicle's VIN tail "
                     "(module was re-VIN'd / reprogrammed)", "warn"))
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
    for f in BINARY_FIELDS:
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
            "modified": val != o[base + 1], "conf": f.get("conf", ""),
            "label": label, "css": css, "note": f["note"],
            "static": f.get("static", ""),
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
                "marker": marker, "value": s, "note": f.get("note", ""),
                "conf": f.get("conf", ""),
                "modified": region_modified(f["base"], f["maxlen"])}
        if f.get("vin"):
            learn = all(d[VIN_DATA + i] == 0xFF for i in range(VIN_LEN))
            chk = None if learn else vin_check_digit_ok(s)
            item.update({"vin": True, "data_addr": VIN_DATA, "length": VIN_LEN,
                         "learn": learn, "check_ok": chk,
                         "decoded": "" if learn else decode_vin(s)})
        if f["key"] == "vin_tail":
            # 2026-10-15 (§0.15): surface stale-vs-current so a re-VIN'd module is obvious.
            m = vin_tail_matches(d)
            item["status"] = (
                None if m is None else
                {"label": "matches current VIN", "css": "good"} if m else
                {"label": "STALE — previous vehicle's VIN tail", "css": "warn"})
        strs.append(item)

    # raw binary identity fields (2026-10-15) -- hex + decoder, never parse_string()
    binf = []
    for f in BINARY_FIELDS:
        base, n = f["base"], f["len"]
        raw = bytes(d[base + 1:base + 1 + n])
        marker, marker_end = d[base], d[base + 1 + n]
        binf.append({"key": f["key"], "name": f["name"], "base": base,
                     "data_addr": base + 1, "length": n, "conf": f.get("conf", ""),
                     "marker": marker, "marker_end": marker_end,
                     "framed": marker == marker_end,          # live check, no fixed marker assumed
                     "known_marker": marker in KNOWN_MARKERS,
                     "raw": hexs(raw), "decoded": decode_binary(f["decode"], raw),
                     "modified": region_modified(base, n + 2), "note": f.get("note", "")})

    # feature flags
    feats = []
    for f in FEATURE_FLAGS:
        base = f["base"]
        val = d[base + 1]
        label, css = byte_state(val)
        feats.append({"name": f["name"], "base": base, "addr": base,
                      "data_addr": base + 1, "marker": d[base], "value": val,
                      "orig": o[base + 1], "modified": val != o[base + 1],
                      # Feature flags are guesses by nature -- default UNCONFIRMED unless a
                      # specific entry earned a higher tag (e.g. 0x04C0 = confirmed-real block).
                      "conf": f.get("conf", "UNCONFIRMED"),
                      "label": label, "css": css, "risk": f["risk"], "note": f["note"],
                      "static": f.get("static", STATIC_CELL_EVIDENCE.get(base + 1, "")),
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
                   # Survey 4: the 0x0E80 block bytes are confirmed but per-bit meanings have
                   # ZERO firmware-string/xref backing -- every row name here is an unverified gloss.
                   "conf": f.get("conf", "UNCONFIRMED"),
                   "options": opts})

    # CRCs
    crcs = []
    for f in CRC_FIELDS:
        base, kind = f["base"], f["kind"]
        item = {"name": f["name"], "base": base, "kind": kind, "marker": d[base],
                "conf": f.get("conf", ""), "note": f.get("note", "")}
        if kind == "std":
            # Unchanged decode -- re-confirmed 2026-10-15, see CRC_FIELDS header comment.
            counter = (d[base + 1] << 16) | (d[base + 2] << 8) | d[base + 3]
            crc16 = (d[base + 4] << 8) | d[base + 5]
            item.update({"counter": counter, "crc16": crc16,
                         "raw": hexs(d[base:base + 7]),
                         "modified": region_modified(base, 7)})
        elif kind == "seqcrc":
            # [marker][payload][CRC-16 LE][marker]; verify the CRC live. The CRC is the only
            # CONFIRMED part. The two BE u32 fields at payload offsets 6/11 are UNIX timestamps
            # (survey 5) -- NO Δ=1 check, their gap is not fixed. ts_a/ts_b carry decoded UTC.
            n = f["payload_len"]
            payload = bytes(d[base + 1:base + 1 + n])
            crc_addr = base + 1 + n
            stored = int.from_bytes(d[crc_addr:crc_addr + 2], "little")
            calc = crc16_ccitt_false(payload)
            a_off, b_off = f["ts_offs"]
            ts_a, ts_b = be_u32(d, base + 1 + a_off), be_u32(d, base + 1 + b_off)
            item.update({"ts_a": ts_a, "ts_b": ts_b,
                         "ts_a_addr": base + 1 + a_off, "ts_b_addr": base + 1 + b_off,
                         "ts_a_utc": unix_ts(ts_a), "ts_b_utc": unix_ts(ts_b),
                         "ts_gap": ts_b - ts_a,
                         "crc_addr": crc_addr, "crc_stored": stored, "crc_calc": calc,
                         "crc_ok": stored == calc, "marker_end": d[crc_addr + 2],
                         "raw": hexs(d[base:crc_addr + 3]),
                         "modified": region_modified(base, n + 4)})
        else:
            n = f.get("len", 8)
            item.update({"raw": hexs(d[base:base + n]),
                         "modified": region_modified(base, n)})
            mir = f.get("mirror")
            if mir:
                src, off, ln = mir["src"], mir["off"], mir["len"]
                item.update({"mirror_src": src,
                             "mirror_ok": d[base + off:base + off + ln] == d[src + 1:src + 1 + ln]})
        crcs.append(item)

    return {
        "loaded": True, "name": EE.name, "path": EE.path, "files": list_dumps(),
        "security": sec, "strings": strs, "binary": binf, "features": feats,
        "ui_marker": ui_marker, "ui": ui, "crcs": crcs, "diff": EE.diff(),
        "mtc": assemble_mtc(d),
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
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{row:04X}  {hexs(chunk):<47}  {asci}")
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
            try:
                start = int(q.get("start", ["0"])[0], 0)
                length = int(q.get("len", ["256"])[0], 0)
            except ValueError as e:  # bad hex in the view inputs -> 400, not a traceback
                return self._send_json({"error": f"Bad start/len: {e}"}, 400)
            if not EE.loaded():
                return self._send_json({"error": "No file loaded."}, 400)
            return self._send_json({"text": hex_dump(start, max(0, length))})
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
        if u.path == "/api/download":
            # Stream the current (edited) bytes back as a file download so the browser
            # shows its native Save dialog — no server-side path needed.
            if not EE.loaded():
                return self._send_json({"error": "No file loaded."}, 400)
            data = bytes(EE.data)
            base = EE.name or "dump.bin"
            if base.lower().endswith(".bin"):
                base = base[:-4]
            fname = base + "_edited.bin"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
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
 .cpill{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.4px;
   padding:1px 6px;border-radius:5px;margin-left:6px;vertical-align:middle;text-transform:uppercase}
 .cpill.confirmed{color:#7ee787;background:rgba(46,160,67,.16);border:1px solid rgba(46,160,67,.4)}
 .cpill.plausible{color:#f0c674;background:rgba(210,153,34,.16);border:1px solid rgba(210,153,34,.4)}
 .cpill.unconfirmed{color:#aab4c2;background:rgba(120,130,150,.16);border:1px solid rgba(120,130,150,.4)}
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
 .panel{scroll-margin-top:94px}
 nav.subnav{position:sticky;top:40px;background:#0b0e13;border-bottom:1px solid var(--line);
   padding:6px 14px;display:flex;gap:6px;flex-wrap:wrap;z-index:4;font-size:11px}
 nav.subnav a{color:var(--mut);text-decoration:none;padding:2px 9px;border-radius:6px;border:1px solid transparent}
 nav.subnav a:hover{color:#fff;border-color:var(--line);background:#10151c}
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
  <button onclick="saveAs()" title="Write to a path on this machine (resolves in the dump folder)">Save to folder…</button>
  <button class="primary" onclick="dl()" title="Download the edited .bin through your browser — choose where to save">⬇ Download .bin</button>
</header>
<nav class="subnav" id="nav" style="display:none"></nav>
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
// Confidence/evidence tag, surfaced so a label can never silently drift from its backing.
const CONF_TITLE={CONFIRMED:'CONFIRMED — backed by byte-exact match to a log/firmware string/CRC',
  PLAUSIBLE:'PLAUSIBLE — structurally supported but not independently confirmed',
  UNCONFIRMED:'UNCONFIRMED — label is a guess with no primary-evidence backing'};
function cpill(c){if(!c)return '';return '<span class="cpill '+esc(c.toLowerCase())
  +'" title="'+esc(CONF_TITLE[c]||'')+'">'+esc(c)+'</span>';}

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
function dl(){if(!S){toast('Load a dump first',false);return;}window.location='/api/download';}

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
  a.appendChild(diffPanel());
  a.appendChild(secPanel());
  a.appendChild(trimPanel());
  a.appendChild(idPanel());
  a.appendChild(featPanel());
  a.appendChild(uiPanel());
  a.appendChild(crcPanel());
  a.appendChild(comparePanel());
  a.appendChild(hexPanel());
  buildNav();
  loadHex();
}
function buildNav(){const nav=$('#nav');if(!nav)return;
  const ps=[...document.querySelectorAll('#app .panel')];
  nav.innerHTML=ps.map(p=>{const h=p.querySelector('h2');
    return h?('<a href="#'+p.id+'">'+esc(h.textContent)+'</a>'):'';}).join('');
  nav.style.display=ps.length?'flex':'none';}

function verdictPanel(){const p=panel('Configuration verdict','Auto-assessment of the loaded dump.');
  const wrap=document.createElement('div');wrap.className='row';
  (S.fingerprint||[]).forEach(t=>{const s=document.createElement('span');
    s.className='pill '+t.css;s.style.fontSize='12px';s.textContent=t.text;wrap.appendChild(s);});
  p.appendChild(wrap);return p;}
function panel(title,sub){const p=document.createElement('div');p.className='panel';
  p.id='sec-'+title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
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
    const stat=f.static?('<div class="note mono">'+esc(f.static)+'</div>'):'';
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${risk}${esc(f.name)}${cpill(f.conf)}${stat}${f.note?('<div class="note">'+esc(f.note)+'</div>'):''}${interp}${reset}</td>
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
    `;
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
    const st=f.status?(' <span class="pill '+f.status.css+'">'+esc(f.status.label)+'</span>'):'';
    tr.innerHTML=`<td>${esc(f.name)}${cpill(f.conf)}${f.modified?'<span class="modbadge">MOD</span>':''}${f.note?('<div class="note">'+esc(f.note)+'</div>'):''}</td>
      <td class="addr mono">${hx(f.base,4)}</td>
      <td class="mono mut">${f.marker!=null?hx(f.marker):'—'}</td>
      <td class="mono">${esc(f.value)||'<span class=mut>(empty)</span>'}${st}</td>`;
    t.appendChild(tr);});
  p.appendChild(t);
  // Assembled Manufacturing Traceability Code (derived from the MTC fragment rows above).
  if(S.mtc){const m=S.mtc;const d=document.createElement('div');d.className='quick';d.style.marginTop='10px';
    const okpill=m.complete?'<span class="pill good">16-digit MTC</span>':'<span class="pill warn">incomplete ('+m.code.length+'/16)</span>';
    const frag=(m.pieces||[]).map(p=>hx(p.base,4)+'="'+esc(p.value)+'"').join(' + ');
    d.innerHTML=`<div class="row"><b>MTC</b> ${cpill(m.conf)} <span class="mono">${esc(m.code)||'<span class=mut>(empty)</span>'}</span> ${okpill}</div>`
      +`<div class="note">Manufacturing Traceability Code, reassembled from fragments: ${frag}. Digit-exact vs SPS <span class="mono">mtc</span>/<span class="mono">infokey</span> (survey 3).</div>`;
    p.appendChild(d);}
  const n=document.createElement('div');n.className='note';n.style.marginTop='8px';
  n.textContent='Non-VIN identity strings are read-only here — use the Raw byte editor below to change them (each char = one ASCII byte starting at base+1).';
  p.appendChild(n);
  // Raw binary identity fields (2026-10-15) — hex, not ASCII; decoded column where an algorithm is confirmed.
  const bh=document.createElement('div');bh.className='sub';bh.style.marginTop='14px';
  bh.textContent='Binary identity fields (raw, not ASCII — added 2026-10-15 from the clean-room triple-pass, EEPROM_LAYOUT §0.15). Markers column shows open/close markers read live.';
  p.appendChild(bh);
  const bt=document.createElement('table');
  bt.innerHTML='<tr><th>Field</th><th>Base</th><th>Markers</th><th>Raw (hex, data bytes only)</th><th>Decoded</th></tr>';
  (S.binary||[]).forEach(f=>{const tr=document.createElement('tr');
    const mk=hx(f.marker)+'/'+hx(f.marker_end)
      +(f.framed?'':' <span class="pill warn" title="closing marker differs from opening marker">frame?</span>')
      +(f.known_marker?'':' <span class="pill warn" title="marker value not in the set seen so far">new marker</span>');
    tr.innerHTML=`<td>${esc(f.name)}${cpill(f.conf)}${f.modified?'<span class="modbadge">MOD</span>':''}${f.note?('<div class="note">'+esc(f.note)+'</div>'):''}</td>
      <td class="addr mono">${hx(f.base,4)}<div class="deftag">data ${hx(f.data_addr,4)} · ${f.length} B</div></td>
      <td class="mono mut">${mk}</td>
      <td class="mono">${f.raw}</td>
      <td class="mono">${f.decoded?esc(f.decoded):'<span class=mut>—</span>'}</td>`;
    bt.appendChild(tr);});
  p.appendChild(bt);return p;}

const TRIM_ADDRS=[0x0AA0,0x0AE5];
function trimPanel(){
  const rows=(S.features||[]).filter(f=>TRIM_ADDRS.includes(f.data_addr));
  const p=panel('Trim / theme (channel b)','VIP-translated GMTrim → boot animation + AAOS theme. UNCONFIRMED candidate bytes (stock 0x69 / LTZ 0xC3 / HighCountry 0xF0). Verify: set, reboot, then adb logcat | grep -i AnimFlavor.');
  if(!rows.length){p.innerHTML+='<div class="mut small">Trim candidate rows not present.</div>';return p;}
  p.appendChild(flagRows(rows));return p;}
function featPanel(){
  const p=panel('Feature flags & undocumented candidates','Suspected values shown as buttons even where ON/OFF semantics are unproven. The outlined button is the default (pre-edit) value.');
  p.appendChild(flagRows((S.features||[]).filter(f=>!TRIM_ADDRS.includes(f.data_addr))));return p;}

function uiPanel(){
  const p=panel('UI flags block @ 0x0E80','Marker '+hx(S.ui_marker)+'. Bitfield rows expose the hex input only. Per-bit names are UNCONFIRMED — the byte block is real but no firmware string/xref backs any individual meaning (survey 4).');
  p.appendChild(flagRows(S.ui));return p;}

function crcPanel(){const p=panel('CRC / integrity','std rows: [marker][00][2-byte version word][2-byte hash][marker] (re-confirmed 2026-10-15). 0x1DC0: [marker][16-byte payload][CRC-16/CCITT-FALSE, LE][marker] — recomputed live. The two u32s in the 0x1DC0 payload are UNIX timestamps, not a ±1 counter pair (survey 5).');
  const t=document.createElement('table');
  t.innerHTML='<tr><th>Field</th><th>Base</th><th>Version counter / timestamps</th><th>CRC16</th><th>Raw</th></tr>';
  S.crcs.forEach(f=>{const tr=document.createElement('tr');
    const name=esc(f.name)+cpill(f.conf)+(f.modified?'<span class="modbadge">MOD</span>':'')+(f.note?('<div class="note">'+esc(f.note)+'</div>'):'');
    if(f.kind==='std'){
      tr.innerHTML=`<td>${name}</td><td class="addr mono">${hx(f.base,4)}</td>
        <td class="mono">${hx(f.counter,6)} <span class="mut">(${f.counter})</span></td>
        <td class="mono">${hx(f.crc16,4)}</td><td class="mono mut">${f.raw}</td>`;
    }else if(f.kind==='seqcrc'){
      const gapTxt=(typeof f.ts_gap==='number')?('Δ '+f.ts_gap+' s'):'';
      const tsA=f.ts_a_utc?('<div class="note">'+esc(f.ts_a_utc)+'</div>'):'';
      const tsB=f.ts_b_utc?('<div class="note">'+esc(f.ts_b_utc)+'</div>'):'';
      const gap=`<span class="pill neutral" title="gap between the two BE u32 UNIX timestamps @${hx(f.ts_a_addr,4)} / @${hx(f.ts_b_addr,4)} — not fixed across units (survey 5)">${esc(gapTxt)}</span>`;
      const ok=`<span class="pill ${f.crc_ok?'good':'bad'}" title="CRC-16/CCITT-FALSE over the 16 payload bytes, stored LE @${hx(f.crc_addr,4)}">${f.crc_ok?'CRC OK':'CRC MISMATCH'}</span>`;
      tr.innerHTML=`<td>${name}</td><td class="addr mono">${hx(f.base,4)}</td>
        <td class="mono">${hx(f.ts_a,8)} / ${hx(f.ts_b,8)} ${gap}${tsA}${tsB}</td>
        <td class="mono">stored ${hx(f.crc_stored,4)} · calc ${hx(f.crc_calc,4)} ${ok}</td>
        <td class="mono mut">${f.raw}</td>`;
    }else{
      const mir=(f.mirror_ok==null)?'':(` <span class="pill ${f.mirror_ok?'good':'warn'}" title="bytes +3..+7 vs ${hx(f.mirror_src,4)} payload">${f.mirror_ok?'mirrors '+hx(f.mirror_src,4):'≠ '+hx(f.mirror_src,4)}</span>`);
      tr.innerHTML=`<td>${name}</td><td class="addr mono">${hx(f.base,4)}</td>
        <td class="mut">—${mir}</td><td class="mut">—</td><td class="mono mut">${f.raw}</td>`;}
    t.appendChild(tr);});
  p.appendChild(t);
  const n=document.createElement('div');n.className='infonote';n.style.marginTop='10px';
  n.innerHTML='<b>Can the std CRCs be regenerated/corrected? No — and it is not necessary.</b> '
    +'Confirmed by reverse-engineering the VIP firmware (Y181, RH850): the firmware contains exactly <b>one</b> '
    +'CRC engine — a table-driven CRC16-CCITT at 0x8059a — and it is used <b>only by the HDLC/IPC serial link</b> '
    +'(TX 0x80712 / RX 0x80d9e), never by the EEPROM. No cal/NVM/EEPROM code computes or verifies a CRC. '
    +'Brute-forcing every standard CRC16 against the stored field/counter pairs yields no match, so the 2-byte '
    +'value in the std rows is <b>not a standard CRC</b> of the counter. On the read side the SBI/cal bytes are taken raw into '
    +'the RAM mirror (0xfebd38ea) with no checksum and a non-fatal fallback to ROM defaults; VIP_BOOT enforces no '
    +'EEPROM CRC at boot (a VIN wiped to 0xFF still boots). The tool therefore deliberately does <b>not</b> fabricate '
    +'a "fix CRC" button. A stale CRC is harmless for boot; re-lock of edits happens via signed SPS cals, not a CRC.'
    +'<br><br><b>2026-10-15 (survey 5, brute-forced across 5 images):</b> one EEPROM block, <b>0x1DC0</b>, does carry a real '
    +'CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over its 16-byte payload — the row above recomputes it from the live bytes. '
    +'The two leading u32 fields in that payload are <b>UNIX timestamps</b> (big-endian, payload offsets 6 and 11), <b>not</b> a '
    +'monotonic sequence/ID pair — their gap is variable (11–13799 s observed), so no "Δ=1" check is made. '
    +'The block covers only itself, not the SBI/VIN/cal fields, and which component writes it (VIP, SoC, '
    +'or the SPS tool) is not established, so the "no fix-CRC button" conclusion for the security/identity edits stands. '
    +'If you hand-edit 0x1DC1–0x1DD0 the row will show CRC MISMATCH; the tool still will not auto-correct it.';
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
