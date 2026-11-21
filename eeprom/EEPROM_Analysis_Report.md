# EEPROM Analysis Report

**File Analyzed:** `ADB_enabled.bin`
**File Size:** 8,192 bytes (8KB)
**EEPROM Chip:** ST M24C64 (64-Kbit I²C EEPROM)
**Analysis Date:** December 2025

---

## Scope of this file (updated 2026-11-21)

This file is the GM IOK/Harman INFO3.7-3.8 EEPROM dump record for `ADB_enabled.bin`. The mechanism,
marker-byte, SBI/ADB-bypass, AUTOSAR NvM descriptor, CRC-algorithm, and address-map analysis that used
to be duplicated here now lives in `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` ("ELA") — see ELA
for current, more rigorously verified versions of that material. What remains here, kept because ELA
references these values but does not reproduce them, is:

- the raw numeric calibration-table appendix (brightness/color LUT values, backlight-dimming LUT
  values, UI-flag byte dump and per-offset breakdown, UI/display-timing raw values);
- facts, addresses, and correction notes that are not currently stated in ELA at all (flagged
  below as "not in ELA").

Each section below is marked **[Pointer]** (content verified present in ELA — kept short, cite ELA
section), or **[Kept]** (unique content, not in ELA, preserved in full/compact form).

---

## Executive Summary [Pointer]

GM Infotainment 3 with Google Built-In (RPO **IOK**), Harman INFO3.7-3.8 CSM module. For platform
identification, the SBI/ADB-bypass mechanism, and marker/CalGroup analysis, see ELA (header block and
§2-§3). This dump has the ADB security bypass applied (both SBI data bytes set to `0xFF`).

---

## Hardware Identification

Full address map for VIN, MTC, programming date, shop code, reprogram date, HW part numbers, and the
VIN-tail residual field is in ELA §5.3 — **[Pointer]**.

- **[Kept — not in ELA]** Vehicle decoded from VIN: 2024 Chevrolet Silverado 2500HD. Programming date at `0x0580`: `20.02.2025` (ELA §5.3 lists the field without the sample value).

**[Kept — not in ELA]** Two items from this file's own prior analysis are more granular than ELA's
one-line entries for the same addresses and are preserved here:

> **MTC digit derivation (not in ELA, which states only "0x0500 = MTC traceability-code tail, digit-
> exact vs SPSVCS.LOG `mtc`/`infokey`" without the sub-field breakdown):** the full 16-digit
> Manufacturing Traceability Code assembles as `0x04E1` (1 digit, "Line") + `0x0561` (1, "Shift") +
> `0x0541` (2, "Year") + `0x0521` (3, "Doy") + `0x0501` (9, "Tn"); `0x0500` stores only the trailing
> 9-digit "Tn" tail. The old "Part Number" label for `0x0500` and "Region Code" label for `0x04E1`
> (ASCII `'4'`, decimal 34) predate this derivation and are superseded by it — `0x04E1` is the MTC
> "Line" digit, not a region code.

> **VIN-tail residual (`0x14A0`) chain-of-custody detail (not in ELA, which states only the one-line
> "mirrors whichever VIN was active when its NvM block was last written; can go stale"):** three
> distinct real dumps show three different states at this address — `ADB_enabled.bin` (this file's
> subject, the LTZ unit) reads its own current VIN tail (live, never re-VINed); an external dump
> (the HC unit) reads the *previous* vehicle's VIN tail (stale); `Y181_ADB_enabled_HC.bin` (a third,
> separately-sourced HC dump) reads all-zero (blank). Do not treat "always retains the old VIN" as a
> guaranteed behavior. Corroborating evidence: firmware strings `cal_vin_relearn_en` / `Theftlocked`
> (present in VIP_APP) point to a VIN-relearn/theft-lock retention mechanism; same physical module
> ECUID `004B41DC0000160006104145610114AC` confirmed across the compared SPS sessions.

> **Unit Serial, `0x0680` (0x680) — unreconciled with ELA:** this file reads `0x0680` as "Unit Serial"
> (`<SN_REDACTED>`). ELA §5.3 instead reads `0x0680-0x0689` as the shop/dealer code (UDS DID `F198`,
> `shopcode` = `9999988888`, a 10-char truncation of the logged 11-digit value) `[C]`. The two
> readings are not reconciled against each other here — **[Kept, flagged conflict]**.

---

### System Specifications (IOK Platform) [Kept — not in ELA]
- **CPU:** Intel Atom A3960
- **GPU:** Intel HD 500
- **RAM:** 6 GB
- **Storage:** 64 GB
- **OS:** Android Automotive 10-12
- **Display:** 13.4" HD Touchscreen

> **CORRECTION (added during review; original values above left for archival fidelity; not covered by
> ELA, which does not discuss hardware specs):** the Dec-2025 spec block is stale. Ground truth — GPU
> = Intel **HD 505** (not 500); RAM = **8 GB LPDDR4** physical, GHS grants the guest 7830 MiB, kernel
> `MemTotal` 5530 MiB / 5.40 GiB (not 6 GB); OS = **Android Automotive 12 (API 32)** (not "10-12");
> Storage = 64 GB **Samsung KLMCG4JEUD** eMMC; Display = 2400×960 **Chimei Innolux DD134IA-01B**. See
> `hardware/teardown.md` and `VERIFICATION.md`.
>
> **EEPROM doc set (updated 2026-11-21):** this report = raw 8 KB calibration/UI-flag numeric
> appendix only, plus facts not carried elsewhere (mechanism and address-map narrative now lives in
> `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`); `eeprom/README.md` = the hands-on flip procedure
> (minipro/XGecu); `eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` = retired pointer (its raw data and correction
> trail are in ELA §13); `hardware/teardown.md` §EEPROM = consolidated headlines + extra
> structured-region readings.

**[Pointer — in ELA §6/§5.3]** Interpretation conflicts between this report and `teardown.md` (same
bytes, different meaning, not settled from bytes alone) are tracked in ELA: **0x1A80** ("config CRC"
vs. "MEC NVM value"), **0x1B60/0x1B80** ("block CRC" vs. "reflash/programming counters"), **0x05A0**
("Serial Number" vs. "Calibration file ID"). See ELA §6 and §5.3 for current status (still UNVERIFIED
either way).

---

## Memory Map Overview [Pointer, with exceptions kept]

The full per-range address map (0x0000-0x1FFF) is in ELA §5.1-§5.8. Two items from the original
box-diagram are **not** currently in ELA and are kept:

- **[Kept — not in ELA]** `0x12E0-0x13FF` ("Device Capabilities & Communication") and `0x1400-0x15FF`
  ("Runtime Data & Additional Flags") are not individually covered in ELA's §5 tables.
- **[Kept — not in ELA]** Original box-diagram labels with no individual ELA entry: `0x0398-0x03BF` Module Identification Codes (ELA §5.1 covers the narrower `0x03A0-0x03B1`), `0x0600-0x07FF` Additional Configuration, `0x0800-0x0A7F` Reserved (`0xFF` padding), `0x0EC0-0x0EFF` Calibration Block A. These are original labels; see ELA §5.4 (`0x0A00` is a structure base inside the `0x0800-0x0A7F` "Reserved" span) and §5.6 (`0x0EC0-0x0F7F` display calibration tables) for the more precise per-field entries.
- **[Kept — conflicts with ELA]** `0x0060-0x0397`: this report previously labeled the range
  "Reserved/Scratch (zeroed - 824 bytes)". ELA §5.1 instead reports an **822**-byte region that
  "actually reads a deterministic 9-bit-period 'walking-zero' bit pattern" `[U]`, not flat zero, and
  flags it as possibly a read glitch vs. an actual EEPROM cell/row fault — unresolved. The byte-count
  and zeroed-vs-pattern discrepancy between the two readings is not reconciled here.

---

## Framing Protocol [Pointer — superseded by ELA §2]

**Corrected 2026-11-21, per ELA §2:** marker bytes are **not** a fixed per-category signature as the
table below originally implied — they vary by firmware/unit and are CalGroup-assigned at runtime; only
the data byte at offset+1 is validated. Locate fields by **offset**, not by marker value. The legend is
kept below for reference to the frame-byte values actually observed in this dump, with that caveat:

| Frame Byte | Observed in this dump at | Caveat |
|------------|---------------------------|--------|
| **0x5A** | Security/VIN region framing | not a dedicated "security" marker — see ELA §2 |
| **0x69** | Config-region framing | not a dedicated "config" marker |
| **0xF0** | String/table-region framing | not a dedicated "data" marker |
| **0xC3** | Calibration-block framing | not a dedicated "calibration" marker |

Structure: `[FRAME_BYTE] [DATA...] [FRAME_BYTE]`, e.g. `5A FF 5A` = a data byte of `0xFF` framed by
`0x5A` markers.

---

## Security Flags (ADB Bypass) [Pointer — full mechanism in ELA §2]

Both SBI data bytes (`0x0441` primary, `0x0A81` backup) read `0xFF` (bypass) in this dump. See ELA §2
for the settled marker/data-byte identity, polarity, the confirmed owner-reproducible bench recipe, and
the SoC-side MEC chain this feeds into.

**[Kept — not in ELA]** OTA-reset behavior: Android OTA updates have been owner-reported to reset the
SBI data bytes to `0x00` (re-enabling ADB authentication) — **corrected 2026-11-12: not universal** (a
2026-11-10 stock calibration write retained ADB access); the actual reset trigger is unidentified. See
`eeprom/README.md`. This specific OTA-reset-not-universal finding is not currently stated in ELA.

---

## Feature Flags

### Identified Toggle Flags

`0x0000`, `0x0020` (boot flags), `0x0440`/`0x0A80` (SBI, see above), `0x0B40`/`0x0B41` (CalGroup `0xA3`
member, not a debug flag), `0x0B80`, `0x0BC0`, `0x1500` are covered in ELA §5.1/§5.4/§5.8 — **[Pointer]**.

**[Kept — not in ELA]** The following toggle-flag addresses from this file's original survey are not
individually listed in ELA:

| Address | Frame | Current Value | Status | Suspected Purpose |
|---------|-------|---------------|--------|-------------------|
| 0x0BA0 | 0xF0 | 0x00 | OFF | Unknown feature |
| **0x0C00** | 0xF0 | **0x01** | **ON** | Unknown (ACTIVE) |
| 0x15C0 | 0xF0 | 0x00 | OFF | Unknown feature |
| 0x1A00 | 0xC3 | 0x00 | OFF | Calibration flag |
| 0x1AC0 | 0xF0 | 0x00 | OFF | Unknown feature |

All five are untested guesses with no code or empirical confirmation, consistent with ELA §5.8's
treatment of the sibling addresses it does list.

### UI Flags Block (0x0E80-0x0EAF) [Kept — raw byte dump + per-offset breakdown not in ELA]

```
0xE80: 5a 03 01 01 01 01 01 00 00 2c 01 00 00 01 00 00 ...
       ^  ─────────────────────────────────────────── ^
     Frame                   Data                   Frame
```

ELA §5.5 reproduces this same raw hex sample and lists untested bit-guesses only for offsets
`0xE82-0xE88`. The full per-offset table, the `0xE89` feature-mask bit breakdown, and the offsets ELA
omits (`0xE81`, `0xE89`, `0xE8A`, `0xE8D`) are kept here as they are not reproduced in ELA:

| Offset | Hex | Binary | Status | Likely Purpose |
|--------|-----|--------|--------|----------------|
| **0xE81** | 0x03 | 00000011 | 2 bits ON | Display mode / Theme selector |
| **0xE82** | 0x01 | 00000001 | ON | Touch input enabled |
| **0xE83** | 0x01 | 00000001 | ON | Haptic/vibration feedback |
| **0xE84** | 0x01 | 00000001 | ON | UI sound effects |
| **0xE85** | 0x01 | 00000001 | ON | Transition animations |
| **0xE86** | 0x01 | 00000001 | ON | Auto-brightness / Night mode |
| **0xE87** | 0x00 | 00000000 | OFF | Reserved (hidden feature?) |
| **0xE88** | 0x00 | 00000000 | OFF | Reserved (hidden feature?) |
| **0xE89** | 0x2C | 00101100 | Bitfield | Feature mask (3 of 8 bits enabled) |
| **0xE8A** | 0x01 | 00000001 | ON | Input mode / gesture control |
| **0xE8D** | 0x01 | 00000001 | ON | Unknown toggle |

All entries `[I]`/`[U]` (untested bit-guesses), consistent with ELA's own confidence tagging for the
offsets it does carry.

#### Feature Mask Byte (0xE89 = 0x2C) [Kept — not in ELA]

```
Bit:  7  6  5  4  3  2  1  0
      0  0  1  0  1  1  0  0  = 0x2C (44 decimal)
            │     │  │
            │     │  └── Bit 2: ENABLED
            │     └───── Bit 3: ENABLED
            └────────── Bit 5: ENABLED
```

#### UI Flag Experiments [Kept — not in ELA; untested suggestions]

**Low risk (toggle existing features OFF):**
| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0xE83 | 0x01 | 0x00 | Disable haptic feedback |
| 0xE84 | 0x01 | 0x00 | Disable UI sounds |
| 0xE85 | 0x01 | 0x00 | Disable animations (may improve performance) |

**Medium risk (enable hidden features):**
| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0xE87 | 0x00 | 0x01 | Enable reserved feature #1 |
| 0xE88 | 0x00 | 0x01 | Enable reserved feature #2 |
| 0xE89 | 0x2C | 0xFF | Enable all bits in feature mask |

**Higher risk (change behavior):**
| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0xE81 | 0x03 | 0x07/0x0F | May unlock additional display modes |

#### Accessing UI Settings via Software [Kept — not in ELA]

Some settings may be accessible without EEPROM modification:
1. **Hidden Diagnostic Menu**: Press `CONFIG + TONE` for 6 seconds
2. **Developer Mode**: Settings → About → tap Build Number repeatedly
3. **Service Menu**: Press `Home + << + Power + >> + Back` simultaneously

---

## Display Calibration Tables [Kept — raw LUT values not reproduced in ELA]

ELA §5.6 identifies these ranges ("Brightness LUT (11-point)", "Color/ambient calibration") but does
not reproduce the numeric values. Preserved here as the primary numeric appendix content:

### Brightness Levels (0x0F00)
11-point lookup table for display brightness:

| Level | Value | Percentage |
|-------|-------|------------|
| 0 | 0 | 0% |
| 1 | 5 | 5% |
| 2 | 15 | 15% |
| 3 | 25 | 25% |
| 4 | 35 | 35% |
| 5 | 45 | 45% |
| 6 | 55 | 55% |
| 7 | 65 | 65% |
| 8 | 75 | 75% |
| 9 | 85 | 85% |
| 10 | 100 | 100% |

### Secondary Brightness (0x0F80)
22-point fine-grained brightness curve:
```
0, 5, 9, 13, 17, 21, 25, 29, 33, 37, 40, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 0
```

### Color Calibration (0x0F40)
Ambient light response color temperature adjustment:

| Index | RGB Value | R | G | B |
|-------|-----------|---|---|---|
| 0 | 0x000000 | 0 | 0 | 0 |
| 1 | 0x000CCD | 0 | 12 | 205 |
| 2 | 0x002666 | 0 | 38 | 102 |
| 3 | 0x004000 | 0 | 64 | 0 |
| 4 | 0x005999 | 0 | 89 | 153 |
| 5 | 0x007333 | 0 | 115 | 51 |
| 6 | 0x008CCC | 0 | 140 | 204 |
| 7 | 0x00A666 | 0 | 166 | 102 |
| 8 | 0x00BFFF | 0 | 191 | 255 |
| 9 | 0x00D999 | 0 | 217 | 153 |
| 10 | 0x00FFFF | 0 | 255 | 255 |

---

## Backlight/Display-Dimming Calibration Tables [Kept — raw LUT values not reproduced in ELA]

Corrected 2026-10-15; **was** mislabeled "Audio Calibration Tables" in every prior pass. ELA §5.7
confirms these ranges are backlight-dimming (byte-matched *in shape* against VIP_APP firmware LUT
defaults at `0xf8414-0xf8500`) but does not reproduce the raw table values — kept here:

### Dimming curve (0x0FE0, was "Volume Curve")
Non-linear dimming response curve:

| Level | Raw Value | Interpretation |
|-------|-----------|----------------|
| 0 | 66 | Base level |
| 1 | 328 | +5 dB |
| 2 | 655 | +10 dB |
| 3 | 983 | +15 dB |
| 4 | 1311 | +20 dB |
| 5 | 1966 | +25 dB |
| 6 | 2621 | +30 dB |
| 7 | 3932 | +35 dB |
| 8 | 6554 | +40 dB |
| 9 | 9830 | +45 dB |
| 10 | 13107 | Max |

### Dimming curve (0x1160, was "Audio EQ/DSP Bands")
Frequency-response-shaped calibration:

| Band | Value | Approximate Frequency |
|------|-------|----------------------|
| 0 | 3277 | Sub-bass |
| 1 | 3932 | Bass |
| 2 | 5898 | Low-mid |
| 3 | 9175 | Mid |
| 4 | 13107 | High-mid |
| 5 | 16384 | Presence |
| 6 | 19661 | High |
| 7 | 22937 | Brilliance |
| 8 | 26214 | Air |
| 9 | 29491 | Ultra-high |
| 10 | 32768 | Max |

### Dimming curve (0x1100, was "Fade/Balance Steps")
22-point linear curve (channel 4 of the backlight-dimming LUT set).

---

## UI/Display Settings (0x0E00-0x0E7F) [Kept — raw values not reproduced in ELA]

ELA §5.5 describes this as a single ~34-field struct and confirms only the **last 7** fields against
named VIP_APP firmware constants (`cal_str_min_temp_threshold`, `soc_min_threshold_1-3`,
`max_suspend_time_1-3` @ `0xf8126-0xf8141`) — i.e. at least partly power/thermal/suspend-timer
calibration, not purely display/UI. **The other 27 fields below, including every raw value, remain
unconfirmed `[I]` per ELA, and `cal_startup_delay_wait_timeout_msec` was specifically tested and found
wrong** — treat the "Setting" labels as unverified guesses; only the raw byte values and addresses are
solid. All values are 16-bit little-endian.

### Timing & Threshold Settings

| Address | Value | Setting | Unit | Notes |
|---------|-------|---------|------|-------|
| 0xE01 | 30 | Screen timeout A | seconds | Primary screen-off timer |
| 0xE05 | 60 | Screen timeout B | seconds | Secondary/extended timer |
| 0xE09 | 35 | Brightness threshold | level | Auto-brightness trigger |
| 0xE0D | 1 | Step increment | units | Brightness step size |
| 0xE0F | 10 | Repeat rate | ms | Button/touch repeat |

### Display Parameters

| Address | Value | Setting | Notes |
|---------|-------|---------|-------|
| 0xE13 | 900 | Display width | Scaled pixels |
| 0xE17 | 600 | Display height | Scaled pixels |
| 0xE1B | 600 | Active area height | Touch-active region |
| 0xE1F | 200 | Backlight max | Maximum brightness level |
| 0xE23 | 15 | DIM threshold | Night mode trigger level |
| 0xE27 | 30 | DIM timeout | Seconds until dim |

### Touch & Animation Settings

| Address | Value | Setting | Notes |
|---------|-------|---------|-------|
| 0xE31 | 500 | Touch timeout | ms - touch debounce |
| 0xE35 | 1 | Touch enable | Boolean flag |
| 0xE39 | 30 | Gesture timeout | Seconds |
| 0xE41 | 30 | Animation speed | ms per frame |
| 0xE45 | 60 | Fade duration | ms for transitions |
| 0xE49 | 30 | Popup timeout | Seconds until auto-dismiss |
| 0xE4D | 10 | Button repeat | Count before repeat |

### Modifiable Timing Values [Kept — not in ELA]

These can be adjusted to change UI behavior:

| Modification | Address | Default | Suggested | Effect |
|--------------|---------|---------|-----------|--------|
| Faster screen off | 0xE01 | 30 | 10 | Quicker power saving |
| Slower screen off | 0xE01 | 30 | 120 | Longer display time |
| Brighter max | 0xE1F | 200 | 255 | Increased max brightness |
| Faster animations | 0xE41 | 30 | 10 | Snappier UI feel |
| Disable animations | 0xE41 | 30 | 0 | Instant transitions |

---

## Checksums and Data Integrity

Full structure/algorithm analysis (the `[00][version][hash]` block structure, the split CRC verdict,
the `0x9896`/`0xAD9B` refutation evidence, the confirmed `0x1DC0` CRC-16/CCITT-FALSE match) is in
ELA §6 — **[Pointer]**. **[Kept — raw sample values for 0x16E0/0x19E0/0x1B40 not given in ELA, which
lists "—" for these]:**

| Address | Name | Value | Purpose |
|---------|------|-------|---------|
| 0x16E0 | Primary integrity block | 0xE2890000 | See ELA §6 for structure |
| 0x19E0 | Secondary integrity block | 0xF1890000 | See ELA §6 for structure |
| 0x1A80 | Config CRC | 0x00000107 | ELA §6 — unresolved vs. teardown's MEC NVM reading |
| 0x1B40 | Third integrity block | 0x128A0000 | See ELA §6 for structure |
| 0x1B60 | Block CRC #1 | 0x00000001 | ELA §6 — unresolved vs. teardown's counter reading |
| 0x1B80 | Block CRC #2 | 0x00000001 | ELA §6 — unresolved vs. teardown's counter reading |

**Warning (per ELA §6):** the algorithm covering 0x16E0/0x19E0/0x1B40 is unknown — do not attempt to
recalculate those fields. `0x1DC0`'s algorithm is confirmed (CRC-16/CCITT-FALSE); modifying data it
covers without recalculating may cause boot failures or factory-reset behavior.

---

## Potential Modification Candidates

### High-Confidence Toggles

| Address | Current | Try | Expected Effect |
|---------|---------|-----|-----------------|
| 0x0020 | 0x00 | 0xFF | Enable unknown feature #1 |
| 0x0B40 | 0x00 | 0xFF | **Corrected 2026-11-12:** operator-tested across the full value range (`0x00`/`0x01`/`0xFF`) with no observed effect — see ELA §5.4 (`0x0B40`/`0x0B41`; originally in the now-retired `eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` §"0x0B41"). Not a useful candidate for further testing. |
| 0x0B80 | 0x00 | 0xFF | Unknown feature |
| 0x0BC0 | 0x00 | 0xFF | Unknown feature |
| 0x1500 | 0x00 | 0xFF | Unknown feature |

**[Kept — not in ELA]** The `0x0B40` tested-no-effect finding (sourced from
`EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`, now retired into ELA §5.4/§13) is preserved as-is above.

### Calibration Adjustments
These tables can be modified to change display/audio behavior:

| Table | Address | Modification |
|-------|---------|--------------|
| Brightness | 0x0F00 | Adjust curve points for brighter/dimmer response |
| Dimming | 0x0FE0 | Adjust backlight dimming curve (not audio — corrected 2026-10-15, see above) |
| Color | 0x0F40 | Adjust ambient light color temperature |

---

## Factory Reset / Data Clear Triggers (UNVERIFIED) [Kept — not in ELA]

> **DISCLAIMER:** The following analysis is based on reverse engineering patterns common to automotive EEPROMs and has **NOT been verified** on actual hardware. These are educated guesses based on byte patterns and industry conventions. **Test at your own risk** and always maintain a backup of your original EEPROM.

None of this section's addresses or hypotheses are currently discussed in ELA; preserved in full.

### Boot State Flag (Most Likely Reset Trigger)

| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| **0x001** | 0x01 | **0x00** | Virgin/reset state - full initialization |
| 0x001 | 0x01 | 0xFF | Corrupted state - may trigger recovery |

```
Common automotive boot state pattern:
  0x00 = Virgin/First-boot state → Triggers full initialization, clears user data
  0x01 = Normal operation → Preserves all settings (CURRENT)
  0xFF = Corrupted/Erased → May trigger recovery mode
  0x02 = Recovery mode (speculative)
```

### Initialization Flag

| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| **0x021** | 0x00 | 0xFF | Force re-initialization |

### CRC/Checksum Invalidation

Corrupting checksums may force the system into recovery or factory reset:

| Address | Name | Current | Corrupt To | Risk Level |
|---------|------|---------|------------|------------|
| 0x16E1-0x16E4 | Primary CRC | 0xE2890000 | 0x00000000 | HIGH |
| 0x19E1-0x19E4 | Backup CRC | 0xF1890000 | 0x00000000 | HIGH |

### VIN Clearing

| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0x5C1-0x5D1 | VIN ASCII | All 0x00 | VIN reprogram mode, possible theft-lock |

> **Note:** ELA §8 reports that setting the VIN field to all `0xFF` booted into AAOS normally with no
> observable change — see ELA §8 for that empirical result, which bears on (but does not directly
> test) the all-`0x00` clearing hypothesis above.

### Data Valid Flag (Speculative)

| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0x1AE7 | 0x01 | 0x00 | May invalidate data partition only |

### Header Magic Corruption

| Address | Current | Change To | Expected Effect |
|---------|---------|-----------|-----------------|
| 0x000 | 0x69 | 0xFF | EEPROM appears virgin/invalid |

### Recommended Test Order (Least to Most Destructive)

1. **0x001 → 0x00** - Boot state reset (likely clears user data, preserves VIN)
2. **0x021 → 0xFF** - Init flag (may trigger first-run wizard)
3. **0x1AE7 → 0x00** - Data valid flag (speculative, may clear data partition)
4. **0x16E1 → 0x00000000** - CRC invalidation (aggressive, may need dealer recovery)
5. **Full 0xFF erase** - Complete virgin state (requires full reprogramming)

### Recovery Notes

- Always backup original EEPROM before modifications
- VIN, serial numbers, and calibration data may need dealer reprogramming if corrupted
- The system likely has recovery mechanisms in flash memory, not EEPROM
- OTA updates may restore corrupted EEPROM data automatically

---

## Warnings and Considerations

1. **[Kept — not in ELA] OTA Updates**: Android OTA updates have been owner-reported to reset security
   flags to 0x00, re-enabling ADB authentication requirements — **corrected 2026-11-12: not
   universal** (a 2026-11-10 stock calibration write retained ADB); the actual reset trigger is
   unidentified (see `eeprom/README.md`).

2. **[Pointer — ELA §8] Checksum Validation**: ELA §8 empirically confirms CRC is not boot-time
   enforced for at least the VIN region; do not assume other fields are safe to corrupt without
   recalculation.

3. **[Pointer — ELA §7] Redundancy**: the AUTOSAR NvM `copies`-field analysis, the 12-byte
   block-descriptor table, the `0x0400/0x0420` REDUNDANT-pair finding, and the distinction from the
   `0x0440/0x0A80` SBI application-level mirror pair are all in ELA §7 in more detail than this file
   previously carried — see ELA §7 rather than this file for that analysis. **[Kept — not in ELA]** Both `0x0400` and `0x0420` currently contain `1900e4a4`.

4. **Factory Reset Risk**: Invalid EEPROM data may trigger a factory reset or brick the module.

5. **Vehicle Safety**: Modifying infotainment settings should not affect vehicle safety systems, but proceed with caution.

---

## Tools Used

- **Programmer**: XGecu with minipro software
- **Chip**: ST M24C64 TSSOP8
- **Analysis**: Python struct, xxd hex dump

## References

**[Pointer — ELA's own "External sources / references"]** AUTOSAR_SWS_NVRAMManager, AUTOSAR_SWS_CRCLibrary,
Renesas AN R01AN2296EJ, Renesas R20UT2846EJ, CVE-2025-32058/Black Hat Asia 2025, and the Willem Melching
DEF CON 30 Toyota-header research are all cited with the same detail in ELA's references section — see
there rather than duplicating.

**[Kept — not in ELA]**

### Technical Documentation
- [ST M24C64 Datasheet](https://www.st.com/resource/en/datasheet/m24c64-f.pdf)
- [NHTSA TSB - IOK Radio Software Y175](https://static.nhtsa.gov/odi/tsbs/2025/MC-11014087-0001.pdf)
- [Chevrolet Infotainment Support](https://www.chevrolet.com/support/vehicle/entertainment/displays-radio/infotainment)

### Community Research
- [XDA Forums - GM Google Built-In Tinkering](https://xdaforums.com/t/general-motors-google-built-in-tinkering.4668105/)
- [CameraLoops - ADB Access on gminfo 3.7-3.8](https://www.cameraloops.ru/forums/topic/6151-adb-access-on-gminfo-37-38-global-b/)
- [GM-Trucks - Developer Mode Enabled](https://www.gm-trucks.com/forums/topic/245317-developer-mode-enabled/)
- [ZR2zone - MyLink Hidden Developer Menu](https://zr2zone.com/mylink-hidden-developer-and-diagnositic-menu-t268.html)
- [G8Board - DIY VIM Unlock Discussion](https://www.g8board.com/threads/updated-discussion-on-real-diy-vim-unlock-radio-tweaks-eeprom-gmlan.260993/)

### VIN Decoding
- [Stat.vin - Chevrolet Silverado VIN Decoder](https://stat.vin/vin-decoding/chevrolet/silverado)

---

*Report generated from reverse engineering analysis of GM IOK EEPROM dump. Mechanism/marker/address-map
narrative now owned by `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`; this file retains the raw
numeric calibration appendix and facts not currently carried there.*
