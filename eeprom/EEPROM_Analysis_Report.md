# GM IOK Infotainment EEPROM Analysis Report

**File Analyzed:** `ADB_enabled.bin`
**File Size:** 8,192 bytes (8KB)
**EEPROM Chip:** ST M24C64 (64-Kbit I²C EEPROM)
**Analysis Date:** December 2025

---

## Executive Summary

This EEPROM dump is from a **GM Infotainment 3 with Google Built-In** (RPO Code: **IOK**) system, specifically a **Harman INFO3.7-3.8 CSM** module. The binary contains vehicle identification, security configuration, display calibration tables, audio curves, and multiple feature flags. The ADB security bypass has been applied (both security flags set to 0xFF).

---

## Hardware Identification

| Field | Value | Address |
|-------|-------|---------|
| **VIN** | XXXXXXXXXXXXXXXXX | 0x5C0-0x5D1 |
| **Vehicle** | 2024 Chevrolet Silverado 2500HD | Decoded from VIN |
| **MTC traceability-code tail (corrected 2026-10-16; was "Part Number")** | <SN_REDACTED> | 0x500 |
| **Serial Number** | 7310500000000X | 0x5A0 |
| **Unit Serial** | <SN_REDACTED> | 0x680 |
| **VIN-tail residual (corrected 2026-10-15; was "Firmware ID")** | XXXXXXXX A | 0x14A0 |
| **Programming Date** | 20.02.2025 | 0x580 |
| **Region Code** | 34 (ASCII '4' - North America) | 0x4E1 |

> **CORRECTED 2026-10-15 (clean-room triple-pass + cross-session SPS-log match, two independent
> fable agents + an adversarial verification pass):** `0x14A0` is **not** a firmware ID. The field
> mirrors whichever VIN was active the last time its NvM block was written; it lags behind the
> primary VIN (`0x05C0`) after a re-VIN/reprogram event instead of updating immediately. Proven by
> comparing two SPS sessions on the same physical module (same ECUID
> `004B41DC0000160006104145610114AC`): the unit was moved from one vehicle's VIN to another, and
> this field retained the *old* vehicle's last-8-characters instead of tracking the new VIN.
> Firmware strings `cal_vin_relearn_en` / `Theftlocked` (present in VIP_APP) corroborate a
> VIN-relearn/theft-lock retention mechanism rather than a firmware-version field. `eeprom/README.md`
> already independently called this a "VIN-suffix mirror" — this correction refines that: it's not a
> live mirror, it's a residual field that can go stale.
>
> **STRESS-TESTED 2026-10-16** against a cross-tree research survey that initially rated this
> UNVERIFIABLE (the counter-evidence dump checked turned out to be a *different* file than the one
> this finding was built from — resolved by direct byte comparison). Three distinct real dumps now
> show three different states at this address: `ADB_enabled.bin` (the LTZ unit itself) reads its
> *own* current VIN tail (live, not stale — expected, since that unit was never re-VINed);
> `/Users/zeno/Downloads/dump.bin` (the HC unit, analyzed above) reads the *previous* vehicle's VIN
> tail (stale, as described); `Y181_ADB_enabled_HC.bin` (a third, separately-sourced HC dump) reads
> all-zero (blank). **Do not treat "always retains the old VIN" as a guaranteed behavior** — the
> field is evidently a separately-written NvM block that is not kept in lockstep with `0x05C0`, and
> its exact state (live/stale/blank) depends on write history, not a fixed rule.
>
> **CORRECTED 2026-10-16:** `0x0500` ("Part Number" above) is not a part number — it's the last 9
> digits of a 16-digit Manufacturing Traceability Code (MTC), confirmed digit-for-digit against the
> SPS tool's `mtc`/`infokey` log field. The full code assembles as
> `0x04E1`(1 digit, "Line") + `0x0561`(1, "Shift") + `0x0541`(2, "Year") + `0x0521`(3, "Doy") +
> `0x0501`(9, "Tn") — see `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0.15/§2.5 for the full
> derivation. The old "Part Number" label predates that finding and was never reconciled with it.

### System Specifications (IOK Platform)
- **CPU:** Intel Atom A3960
- **GPU:** Intel HD 500
- **RAM:** 6 GB
- **Storage:** 64 GB
- **OS:** Android Automotive 10-12
- **Display:** 13.4" HD Touchscreen

> CORRECTION (added during review; original values above left for archival fidelity): the
> Dec-2025 spec block is stale. Ground truth — GPU = Intel **HD 505** (not 500); RAM = **8 GB
> LPDDR4** physical, GHS grants the guest 7830 MiB, kernel `MemTotal` 5530 MiB / 5.40 GiB (not 6 GB); OS = **Android Automotive 12
> (API 32)** (not "10-12"); Storage = 64 GB **Samsung KLMCG4JEUD** eMMC; Display = 2400×960
> **Chimei Innolux DD134IA-01B**. See `hardware/teardown.md` and `VERIFICATION.md`.
>
> EEPROM doc set (all retained, complementary): this report = full 8 KB map + calibration/UI
> tables; `eeprom/README.md` = the hands-on flip procedure (minipro/XGecu); `eeprom/EEPROM_
> UNDOCUMENTED_FLAGS_ANALYSIS.md` = undocumented-flag RE + CalGroup marker rotation + 0xb67d0;
> `hardware/teardown.md` §EEPROM = consolidated headlines + extra structured-region readings.
> Unresolved interpretation conflicts with teardown.md (same bytes, different meaning, not
> settleable from bytes alone): **0x1A80** (here "config CRC" vs teardown "MEC NVM value"),
> **0x1B60** (here "block CRC" vs teardown "reflash/programming counters" — the latter aligns
> with the UNDOCUMENTED_FLAGS §13.7 CRC-version-counter finding), **0x05A0** (here "Serial
> Number" vs teardown "Calibration file ID"; the bytes are the `7310500000000X` CVPPS value).
> These remain UNVERIFIED — do not treat either reading as confirmed.

---

## Memory Map Overview

```
┌────────────────────────────────────────────────────────────────┐
│ 0x0000-0x005F │ Header & Boot Flags                           │
├────────────────────────────────────────────────────────────────┤
│ 0x0060-0x0397 │ Reserved/Scratch (zeroed - 824 bytes)         │
├────────────────────────────────────────────────────────────────┤
│ 0x0398-0x03BF │ Module Identification Codes                   │
├────────────────────────────────────────────────────────────────┤
│ 0x0400-0x045F │ Security Configuration & Flags                │
├────────────────────────────────────────────────────────────────┤
│ 0x0460-0x0465 │ HW Part Number (ssecuhn, confirmed 2026-10-15)│
├────────────────────────────────────────────────────────────────┤
│ 0x0466-0x04FF │ Unidentified (not Radio/Audio; 0x0480 holds a second part-number-shaped value) │
├────────────────────────────────────────────────────────────────┤
│ 0x0500-0x05FF │ String Data (VIN, Serial, Date, Part#)        │
├────────────────────────────────────────────────────────────────┤
│ 0x0600-0x07FF │ Additional Configuration                      │
├────────────────────────────────────────────────────────────────┤
│ 0x0800-0x0A7F │ Reserved (0xFF padding)                       │
├────────────────────────────────────────────────────────────────┤
│ 0x0A80-0x0AFF │ Backup Security Flags                         │
├────────────────────────────────────────────────────────────────┤
│ 0x0B00-0x0DFF │ Feature Flags & Runtime Config                │
├────────────────────────────────────────────────────────────────┤
│ 0x0E00-0x0EBF │ Display/UI Settings                           │
├────────────────────────────────────────────────────────────────┤
│ 0x0EC0-0x0EFF │ Calibration Block A                           │
├────────────────────────────────────────────────────────────────┤
│ 0x0F00-0x0F3F │ Brightness Lookup Table                       │
├────────────────────────────────────────────────────────────────┤
│ 0x0F40-0x0F7F │ Color/Display Calibration                     │
├────────────────────────────────────────────────────────────────┤
│ 0x0F80-0x0FDF │ Secondary Brightness Table                    │
├────────────────────────────────────────────────────────────────┤
│ 0x0FE0-0x103F │ Backlight Dimming Curve (was mislabeled "Audio Volume Curve")                            │
├────────────────────────────────────────────────────────────────┤
│ 0x1040-0x109F │ Backlight Dimming Tables (was mislabeled "Audio Fade/Balance")                     │
├────────────────────────────────────────────────────────────────┤
│ 0x10A0-0x12DF │ Backlight Dimming Calibration (was mislabeled "Audio EQ/DSP")                      │
├────────────────────────────────────────────────────────────────┤
│ 0x12E0-0x13FF │ Device Capabilities & Communication           │
├────────────────────────────────────────────────────────────────┤
│ 0x1400-0x15FF │ Runtime Data & Additional Flags               │
├────────────────────────────────────────────────────────────────┤
│ 0x1600-0x1FFF │ Checksums, CRCs, Reserved                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Framing Protocol

The EEPROM uses a proprietary framing protocol with four distinct marker bytes:

| Frame Byte | Purpose | Description |
|------------|---------|-------------|
| **0x5A** | Security/VIN | VIN storage, security flags, high-importance data |
| **0x69** | Configuration | System config registers, feature flags |
| **0xF0** | Data/Strings | ASCII strings, lookup tables, calibration data |
| **0xC3** | Calibration | Color tables, advanced calibration blocks |

### Structure Format
```
[FRAME_BYTE] [DATA...] [FRAME_BYTE]
```

Example: `5A FF 5A` = Security flag with value 0xFF

---

## Security Flags (ADB Bypass)

### Primary Security Flag
| Address | Raw Data | Value | Status |
|---------|----------|-------|--------|
| **0x0440** | `5A FF 5A FF` | 0xFF | **DISABLED** (ADB Enabled) |

### Backup Security Flag
| Address | Raw Data | Value | Status |
|---------|----------|-------|--------|
| **0x0A80** | `5A FF 5A FF` | 0xFF | **DISABLED** (ADB Enabled) |

### Security States
- `0x00` = Security ENABLED (ADB requires GM Secure Client authentication)
- `0xFF` = Security DISABLED (ADB accessible without authentication)

**CORRECTED 2026-09-26 (primary evidence: 7-dump byte compare + RH850 disasm + adb-auth binary +
ecu80_READ CAN capture):** the framing **marker** shown above (`5A`) is **not static per address** —
across 7 real dumps the 0x0440 marker was `C3` (stock/debugging) or `5A` (ADB-enabled) and 0x0A80 was
`FF`/`69`/`5A`/`F0`. Only the **data byte at offset+1** (0x0441/0x0A81) carries the lock state (the
`0x00`/`0xFF` above). Clearing SBI does not enable ADB *directly*: VIP reads SBI → transmits MEC via
DID `0xF1A0` → SoC `gm_adb_auth_init` sets `is_secure_mode` (the guest-side gate). The `$27` all-FF
seed is a **separate** CAN/UDS-only effect, not the ADB path. Canonical marker/mechanism detail:
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0.10-0.14. (This file duplicates that report; prefer it.)

**Note:** Both locations must be modified for the bypass to work. OTA updates reset these to 0x00.

---

## Feature Flags

### Identified Toggle Flags

| Address | Frame | Current Value | Status | Suspected Purpose |
|---------|-------|---------------|--------|-------------------|
| 0x0000 | 0x69 | 0x01 | ON | Boot/Init completed flag |
| 0x0020 | 0x69 | 0x00 | OFF | Unknown feature toggle |
| 0x0440 | 0x5A | 0xFF | DISABLED | **ADB Security #1** |
| 0x0A80 | 0x5A | 0xFF | DISABLED | **ADB Security #2** |
| 0x0B40 | 0x69 | 0x00 | OFF | Developer/Debug mode? |
| 0x0B80 | 0xF0 | 0x00 | OFF | Unknown feature |
| 0x0BA0 | 0xF0 | 0x00 | OFF | Unknown feature |
| 0x0BC0 | 0x69 | 0x00 | OFF | Unknown feature |
| **0x0C00** | 0xF0 | **0x01** | **ON** | Unknown (ACTIVE) |
| 0x1500 | 0x69 | 0x00 | OFF | Unknown feature |
| 0x15C0 | 0xF0 | 0x00 | OFF | Unknown feature |
| 0x1A00 | 0xC3 | 0x00 | OFF | Calibration flag |
| 0x1AC0 | 0xF0 | 0x00 | OFF | Unknown feature |

### UI Flags Block (0x0E80-0x0EAF)

This 0x5A-framed block contains UI configuration flags controlling display behavior, input methods, and visual effects.

```
0xE80: 5a 03 01 01 01 01 01 00 00 2c 01 00 00 01 00 00 ...
       ^  ─────────────────────────────────────────── ^
     Frame                   Data                   Frame
```

#### Individual Flag Analysis

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

#### Feature Mask Byte (0xE89 = 0x2C)

```
Bit:  7  6  5  4  3  2  1  0
      0  0  1  0  1  1  0  0  = 0x2C (44 decimal)
            │     │  │
            │     │  └── Bit 2: ENABLED
            │     └───── Bit 3: ENABLED
            └────────── Bit 5: ENABLED
```

#### UI Flag Experiments

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

#### Accessing UI Settings via Software

Some settings may be accessible without EEPROM modification:
1. **Hidden Diagnostic Menu**: Press `CONFIG + TONE` for 6 seconds
2. **Developer Mode**: Settings → About → tap Build Number repeatedly
3. **Service Menu**: Press `Home + << + Power + >> + Back` simultaneously

---

## Display Calibration Tables

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

## Backlight/Display-Dimming Calibration Tables (corrected 2026-10-15; previously mislabeled "Audio Calibration Tables")

### Dimming curve (0x0FE0, was "Volume Curve")
Non-linear volume response curve:

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
Frequency response calibration:

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
22-point linear fade curve for speaker balance.

---

## UI/Display Settings (0x0E00-0x0E7F)

This block contains timing values, thresholds, and display parameters. All values are 16-bit little-endian.

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

### Modifiable Timing Values

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

| Address | Name | Value | Purpose |
|---------|------|-------|---------|
| 0x16E0 | Primary CRC | 0xE2890000 | Main EEPROM CRC |
| 0x19E0 | Secondary CRC | 0xF1890000 | Backup CRC |
| 0x1A80 | Config CRC | 0x00000107 | Configuration block CRC |
| 0x1B40 | Data CRC | 0x128A0000 | Data section CRC |
| 0x1B60 | Block CRC #1 | 0x00000001 | Block validation |
| 0x1B80 | Block CRC #2 | 0x00000001 | Block validation |

> **REFINED 2026-10-15:** per `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` §13.7's stock-vs-post-reflash
> diff plus a 2026-10-15 clean-room cross-check, 0x16E0/0x19E0/0x1B40 decode as
> `[00][2-byte version/generation word][2-byte hash/CRC word]`, not one flat 32-bit CRC — the three
> blocks' version words cluster tightly (not exact lockstep — ±1 drift observed) across reflashes/dumps.
> Treat the single hex values above as one sample, not a fixed constant.
>
> **ALGORITHM UNVERIFIED (corrected 2026-10-15):** the 2-byte hash/CRC word in 0x16E0/0x19E0/0x1B40
> has NOT been verified by byte-match. Binary cross-check disproves the simplest hypothesis: 0x16E0
> and 0x1B40 share version word `0x5800` but their stored hash bytes differ (`0x9896` vs `0xAD9B`),
> so the hash/CRC is NOT simply CRC of the version word alone. Coverage range and exact algorithm
> remain UNKNOWN. Do not rely on earlier "confirmed" language — it was wrong.
>
> **This separate integrity-block structure (integrity word at a different address from its payload)
> is NOT defined by AUTOSAR NvM** (which appends CRC to the same slot), nor by the Fee/Ea SWSs.
> Origin undetermined.
>
> **0x1DC0 — ONLY CONFIRMED BYTE-MATCH:** CRC-16/CCITT-FALSE (poly `0x1021`, init `0xFFFF`, no
> reflect, no output XOR) confirmed by byte-match across 5 images. Stored `0xBFD4` = computed
> `0xBFD4`. This is the sole block where the algorithm and coverage are proven. See
> `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §2.6/§0.15 and References below.

**Warning:** The algorithm covering 0x16E0/0x19E0/0x1B40 is unknown — do not attempt to recalculate
those fields. For 0x1DC0 the algorithm is confirmed (CRC-16/CCITT-FALSE — see above); modifying
data it covers without recalculating may cause boot failures or factory reset behavior.

---

## Potential Modification Candidates

### High-Confidence Toggles
These follow the documented ADB flag pattern and are likely safe to experiment with:

| Address | Current | Try | Expected Effect |
|---------|---------|-----|-----------------|
| 0x0020 | 0x00 | 0xFF | Enable unknown feature #1 |
| 0x0B40 | 0x00 | 0xFF | Possible developer mode |
| 0x0B80 | 0x00 | 0xFF | Unknown feature |
| 0x0BC0 | 0x00 | 0xFF | Unknown feature |
| 0x1500 | 0x00 | 0xFF | Unknown feature |

### Calibration Adjustments
These tables can be modified to change display/audio behavior:

| Table | Address | Modification |
|-------|---------|--------------|
| Brightness | 0x0F00 | Adjust curve points for brighter/dimmer response |
| Dimming | 0x0FE0 | Adjust backlight dimming curve (not audio — corrected 2026-10-15, see above) |
| Color | 0x0F40 | Adjust ambient light color temperature |

---

## Factory Reset / Data Clear Triggers (UNVERIFIED)

> **DISCLAIMER:** The following analysis is based on reverse engineering patterns common to automotive EEPROMs and has **NOT been verified** on actual hardware. These are educated guesses based on byte patterns and industry conventions. **Test at your own risk** and always maintain a backup of your original EEPROM.

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

1. **OTA Updates**: Android OTA updates will reset security flags to 0x00, re-enabling ADB authentication requirements.

2. **Checksum Validation**: Some modifications may require CRC recalculation to prevent boot issues.

3. **Redundancy**: Settings are duplicated in two distinct ways — the mechanisms differ and must not be conflated:

   - **0x0400/0x0420 — single AUTOSAR `NVM_BLOCK_REDUNDANT` entry (`NvMNvBlockNum=2`).** Both addresses are managed automatically by the AUTOSAR NvM layer (it keeps them in sync and falls back to the backup on read failure). **Do NOT patch both addresses manually** — write only the primary; NvM propagates the copy. Both currently contain `1900e4a4`.

   - **0x0440/0x0A80 — two separate descriptor entries in different CalGroups (SBI primary / SBI backup).** These are an application-level mirror, not an AUTOSAR REDUNDANT block. They are NOT managed as a pair by NvM. **Update both independently** when modifying SBI data; failing to update both leaves mismatched copies.

   > **AUTOSAR NvM mapping (added 2026-10-15).** The config region is defined by a firmware block-descriptor
   > table of 12-byte entries `[u32 LE rel_addr][u16 LE payload_len][u8 type_byte][u8 copies][u32 0]`.
   > Correlation with AUTOSAR_SWS_NVRAMManager R22-11 (Chapter 10, ECUC): `rel_addr` is a flat address
   > (implementation-specific, not spec-stated: NvM spec defines NvMNvBlockBaseNumber range 1..65534 but not how the descriptor encodes it; role of `NvMNvBlockBaseNumber`; all 183 entries have high word `0x0000`, so the Melching
   > `[u16 block_id][u16 offset]` hypothesis is REFUTED); `payload_len`→`NvMNvBlockLength`;
   > `type_byte`=`0x01` in every entry — a **vendor constant** (format version / valid flag), **not** an AUTOSAR
   > field (AUTOSAR assigns no numeric values to `NvMBlockManagementType`, ECUC_NvM_00062 — it is a symbolic
   > `EcucEnumerationParamDef`; an earlier revision's "SINGLE=0, REDUNDANT=1, DATASET=2" packing was wrong);
   > `copies`→`NvMNvBlockNum` (ECUC_NvM_00480), the **actual management-type discriminator**: `1`=NATIVE,
   > `2`=REDUNDANT, `1..255`=DATASET; trailing `u32 0` unassigned. **AUTOSAR defines no C struct layout for the
   > descriptor table** — the 12-byte format is a Harman/BSP vendor artifact whose size happens to match CC-RH
   > natural packing of `(u32,u16,u8,u8,u32)` (Renesas R20UT2846EJ CC-RH ABI). Entries with `copies=02`
   > (e.g. **0x0400/0x0420**) are `NVM_BLOCK_REDUNDANT, NvMNvBlockNum=2` — the standard AUTOSAR redundancy
   > *behaviour* (both copies kept in sync, backup used on read failure); the descriptor *encoding* is
   > vendor-specific. The `[M][payload][M]` marker framing around records is a Fee/Ea-layer or Harman concept,
   > not AUTOSAR NvM (which defines only an optional Static Block ID header and an appended CRC). Full
   > mapping and correction history: `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0.16.

4. **Factory Reset Risk**: Invalid EEPROM data may trigger a factory reset or brick the module.

5. **Vehicle Safety**: Modifying infotainment settings should not affect vehicle safety systems, but proceed with caution.

---

## Tools Used

- **Programmer**: XGecu with minipro software
- **Chip**: ST M24C64 TSSOP8
- **Analysis**: Python struct, xxd hex dump

## References

### Technical Documentation
- [ST M24C64 Datasheet](https://www.st.com/resource/en/datasheet/m24c64-f.pdf)
- [NHTSA TSB - IOK Radio Software Y175](https://static.nhtsa.gov/odi/tsbs/2025/MC-11014087-0001.pdf)
- [Chevrolet Infotainment Support](https://www.chevrolet.com/support/vehicle/entertainment/displays-radio/infotainment)

### Standards & Cross-Platform Sources
- **AUTOSAR_SWS_NVRAMManager R22-11**, Chapter 10 (ECUC) — `NvMBlockManagementType` (ECUC_NvM_00062, symbolic only) and `NvMNvBlockNum` (ECUC_NvM_00480, REDUNDANT discriminator). No C struct layout for the descriptor table is specified.
- **AUTOSAR_SWS_CRCLibrary** — `Crc_CalculateCRC16()` (CRC-16/CCITT-FALSE, poly `0x1021`, init `0xFFFF`).
- **Renesas AN R01AN2296EJ** — RH850 Flash Self-Programming Library, flash-block CRC-16 verification.
- **Renesas R20UT2846EJ (CC-RH ABI)** — struct packing for the 12-byte descriptor entry.
- **CVE-2025-32058 / Black Hat Asia 2025** — Nissan Leaf RH850 Virgin status byte (`0x00`=locked/`0xFF`=bypass), INC-protocol port map.
- **Willem Melching, DEF CON 30 Automotive Village (2022)** — Toyota EPS RH850 NvM block-ID-first header hypothesis (REFUTED for this unit: all 183 `rel_addr` high words are `0x0000`).

### Community Research
- [XDA Forums - GM Google Built-In Tinkering](https://xdaforums.com/t/general-motors-google-built-in-tinkering.4668105/)
- [CameraLoops - ADB Access on gminfo 3.7-3.8](https://www.cameraloops.ru/forums/topic/6151-adb-access-on-gminfo-37-38-global-b/)
- [GM-Trucks - Developer Mode Enabled](https://www.gm-trucks.com/forums/topic/245317-developer-mode-enabled/)
- [ZR2zone - MyLink Hidden Developer Menu](https://zr2zone.com/mylink-hidden-developer-and-diagnositic-menu-t268.html)
- [G8Board - DIY VIM Unlock Discussion](https://www.g8board.com/threads/updated-discussion-on-real-diy-vim-unlock-radio-tweaks-eeprom-gmlan.260993/)

### VIN Decoding
- [Stat.vin - Chevrolet Silverado VIN Decoder](https://stat.vin/vin-decoding/chevrolet/silverado)

---

*Report generated from reverse engineering analysis of GM IOK EEPROM dump.*
