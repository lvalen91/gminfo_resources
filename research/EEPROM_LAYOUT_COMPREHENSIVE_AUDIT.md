# EEPROM Layout Audit — Complete Inventory & SBI/Cal-Security Deep-Dive

**Date:** 2026-08-17  
**Source:** `eeprom/EEPROM_Analysis_Report.md` (Dec 2025), `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (Jan–Feb 2026), `T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md`, `S27_SOC_VALIDATION_BENCH_TEST.md`  
**Scope:** ST M24C64 8KB EEPROM; VIP (Renesas RH850) + SoC (Android IVI)

---

## 1. EEPROM Layout Maturity & Detail Level

### Current documentation status:

| Region | Detail Level | Evidence | Verified | Gaps |
|--------|--------------|----------|----------|------|
| **Boot/Init (0x0000–0x03FF)** | Field-level | Byte reads + structure inference | Partial | Exact bit fields for boot flags unclear |
| **Security Config (0x0400–0x04FF)** | Byte-level (primary), Field-inferred (secondary) | `0x0440/0x0A80` SBI disasm-confirmed; undocumented 0x04A0/0x04C0 via firmware xrefs (17/11 refs) | High for SBI; low for others | Polarity unknown for undocumented flags; no live testing data |
| **Device ID (0x0500–0x05FF)** | Field-level | VIN, serial, part# reads verified from dump | High | — |
| **Backup Security (0x0A00–0x0AFF)** | Byte-level (0x0A80), Field-inferred (structure) | 0x0A00 (871 refs), 0x0B00 (311 refs) = base addresses (not flags) | Medium | Base-address counts are approximate; individual flag function unknown |
| **Feature Flags (0x0B00–0x0BFF)** | Byte-level (0x0B40 debug mode), Field-guessed (0x0A40/0x0A60/0x0AC0/0x0BE0) | 0x0B40 documented; 0x0A40 (28 refs), 0x0BE0 (24 refs) via xref | Low-Medium | Undocumented flags need physical or RAM-shadow testing |
| **UI/Display Settings (0x0E00–0x0EBF)** | Field-level | Timing/threshold values (e.g., 0xE01=30 sec screen timeout) read from sample dump | Medium | Bit-field granularity guessed; interpretation inferred not verified |
| **Display Calibration (0x0EC0–0x0F7F)** | Table-level | Brightness LUTs (11-point, 22-point), color RGB calibration (0x0F40) | Medium | Ambient-light compensation logic guessed |
| **Audio Calibration (0x0FE0–0x12DF)** | Table-level | Volume curve (11 points), EQ/DSP (10 bands), fade/balance (22-point) | Medium | Link to actual audio codec/DSP unknown; calibration scale/units guessed |
| **Checksums/CRCs (0x16E0–0x1FFF)** | Byte-level | Six CRC words identified; values in sample dump recorded | Low | CRC algorithm (CRC16? CRC32?), polynomial, coverage scope **not documented** |

### Summary:
- **Enhanced since initial analysis:** Yes. Dec-2025 report = raw byte map. Jan–Feb 2026 = firmware xref analysis added undocumented flags. Aug-2026 = marker-rotation and CalGroup system discovery.
- **Current detail:** Mixed. Security-critical (`0x0440/0x0A80`) = disasm-confirmed, high fidelity. Undocumented flags and checksums = inferred, medium-high fidelity.

---

## 2. Complete EEPROM Parameter Inventory

### 2.1 Security & Access Control

| Address | Field | Documented | Polarity | Evidence Level | Notes |
|---------|-------|-----------|----------|----------------|-------|
| **0x0440** | Primary SBI (Seed Bypass Indicator) | Yes | 0xFF=bypass, 0x00=locked | Disasm-confirmed (VIP 0xb67d0 validator) | ADB security gate. Marker byte [M] at 0x0440, data at 0x0441, marker at 0x0442 |
| **0x0A80** | Backup SBI | Yes | 0xFF=bypass, 0x00=locked | Disasm-confirmed | Redundancy. Now initialized in Y181 (was 0xFF/empty in stock) |
| **0x0B40** | Debug Mode Flag | Yes | 0x01=enabled, 0x00=disabled | Firmware refs (9 xrefs) | Enables additional diagnostic output or feature access |
| **0x04A0** | IPC Security Config #1 | Undocumented | Unknown | Firmware xrefs (17 refs); near `[IPC_S]` strings | High priority for cal-`$27` gate hypothesis |
| **0x04C0** | IPC Security Config #2 | Undocumented | Unknown | Firmware xrefs (11 refs); paired with 0x04A0 | Companion flag; may be access-level or variant selector |
| **0x0A40** | Feature Enable (mid-region) | Undocumented | Unknown | Firmware xrefs (28 refs) | Medium priority; likely hidden-feature enable, not the `$27` gate |
| **0x0BE0** | Late-Region Flag (danger zone) | Undocumented | Unknown | Firmware xrefs (24 refs) | **LOWEST priority.** Likely manufacturing lock / debug-interface disable (OTP-like). **Do not flip casually.** |
| **0x1A00** | Tertiary Security | Documented (stock=0x00) | 0x00=locked | Sample dump; undocumented full function | Modified in ADB-bypass sample (0x1A01=0xFF). Possibly secondary SBI mirror or lock counter |

### 2.2 Display/UI Parameters (0x0E00–0x0EAF)

| Address | Field | Type | Sample Value | Interpretation |
|---------|-------|------|--------------|-----------------|
| 0x0E01 | Screen timeout A | uint16 | 30 | Seconds until screen-off |
| 0x0E05 | Screen timeout B | uint16 | 60 | Extended timer |
| 0x0E09 | Brightness threshold | uint16 | 35 | Auto-brightness trigger level |
| 0x0E0D | Brightness step | uint16 | 1 | Increment size |
| 0x0E0F | Button repeat rate | uint16 | 10 | Milliseconds |
| 0x0E13 | Display width | uint16 | 900 | Scaled pixels (guessed) |
| 0x0E17 | Display height | uint16 | 600 | Scaled pixels (guessed) |
| 0x0E1B | Touch active height | uint16 | 600 | Touch-sensitive region |
| 0x0E1F | Backlight max level | uint16 | 200 | Max brightness value |
| 0x0E23 | Dim threshold | uint16 | 15 | Night-mode trigger |
| 0x0E27 | Dim timeout | uint16 | 30 | Seconds to dim |
| 0x0E31 | Touch debounce | uint16 | 500 | Milliseconds |
| 0x0E35 | Touch enable | uint16 | 1 | Boolean |
| 0x0E39 | Gesture timeout | uint16 | 30 | Seconds |
| 0x0E41 | Animation speed | uint16 | 30 | ms per frame |
| 0x0E45 | Fade duration | uint16 | 60 | ms for transitions |
| 0x0E49 | Popup timeout | uint16 | 30 | Seconds |
| 0x0E4D | Button repeat count | uint16 | 10 | Before repeat engages |

**Caveat:** These are **inferred** from sample dump analysis. No disasm confirmation; no firmware xrefs found. May not be the actual display/resolution gate (see §5).

### 2.3 Audio/Radio Tuning Tables

| Address Range | Type | Size | Documented | Notes |
|---------------|------|------|-----------|-------|
| 0x0460–0x04FF | Radio/Audio Settings | 160 bytes | Partial | Frequency tuning, codec config inferred |
| 0x0FE0–0x103F | Volume Curve | 96 bytes | Yes | 11-point non-linear response; verified in dump |
| 0x1040–0x109F | Fade/Balance Tables | 96 bytes | Yes | 22-point linear fade; front/rear balance |
| 0x10A0–0x12DF | EQ/DSP Calibration | 576 bytes | Yes | 10-band equalizer; frequency response tuning |

### 2.4 Calibration References & Pointers

| Address | Field | Value (sample) | Purpose |
|---------|-------|---|---------|
| 0x05A0–0x05AF | Calibration File ID (CVPPS) | 7310500000000X | Cross-reference to provisioning database |
| 0x0E80–0x0EAF | UI Flags Block | `5A 03 01 01 01 01 01 00 00 2C 01 00 00 01 00 00` | Feature toggles for display behavior |

### 2.5 Manufacturing/Version Info

| Address | Field | Sample | Documented |
|---------|-------|--------|-----------|
| 0x0500 | Part Number | \<REDACTED\> | Yes (structure) |
| 0x05C0 | VIN | XXXXXXXXXXXXXXXXX | Yes (17 bytes) |
| 0x0580 | Programming Date | 20.02.2025 | Yes |
| 0x4E1 | Region Code | 34 (ASCII '4') | Yes |
| 0x14A0 | Firmware ID | XXXXXXXX A | Yes |
| 0x5A0 | Serial Number | 7310500000000X | Yes (CVPPS) |

### 2.6 Checksums & Integrity Fields

| Address | Name | Type | Sample Value | Coverage |
|---------|------|------|---|---|
| 0x16E0 | Primary CRC | uint32 LE | 0xE2890000 | Full EEPROM? |
| 0x19E0 | Secondary CRC | uint32 LE | 0xF1890000 | Backup CRC |
| 0x1A80 | Config CRC | uint24 LE | 0x000107 | Config region? |
| 0x1B40 | Data CRC | uint32 LE | 0x128A0000 | Data section? |
| 0x1B60 | Block CRC #1 | uint32 LE | 0x00000001 | Calibration block? |
| 0x1B80 | Block CRC #2 | uint32 LE | 0x00000001 | Audio block? |

**Critical gap:** No CRC algorithm specification (polynomial, seed, initialization). After Y181 reflash, upper word of CRCs changed from 0x0013 → 0x0104 (calibration version counter?). **Do not flip EEPROM values without understanding checksum coverage and recomputation.**

---

## 3. ADB SBI Bypass Mechanism: Seed Behavior & Validation

### 3.1 Documented Mechanism

The VIP firmware's security validation function at **address 0xb67d0** (Y181, 906 bytes) performs the ADB gate:

1. **Load from EEPROM at boot:** Read `0x0440` (primary) and `0x0A80` (backup SBI data bytes) via I²C into RAM at address `0x3e06` + offset.
2. **Seed generation in ADB request:**
   - If SBI data byte = `0xFF`: return seed = `FF FF FF FF FF …` (all-0xFF, all bytes).
   - If SBI data byte = `0x00`: return seed = real ECUID + challenge bytes (no bypass).
3. **Key validation:**
   - If seed = all-0xFF: accept **any key** (typically dummy 0x00 bytes or random). Bypass is **complete** for seed *and* key.
   - If seed = real: validate key against PROTOKEY/BCM algorithm. Bypass **does not** apply.

### 3.2 Evidence Level

- **Seed behavior:** `[C]` Confirmed disasm (VIP 0xb67d0 validator loads 0x3e06, branches on seed polarity). Also confirmed by CAN capture (DPS log shows all-0xFF seed with SBI=0xFF at 0x0440).
- **Key acceptance:** `[C]` Confirmed in `S27_SOC_VALIDATION_BENCH_TEST.md` control test (CAN path, MDI2 to VIP, ECU 0x80: `27 01` → `67 01 FF FF FF…`; sendKey with dummy 0x00 bytes → `67 02` accepted).
- **Marker independence:** `[C]` Confirmed by Feb 2026 marker-rotation analysis: identical Y181 firmware produces different marker bytes (`0xC3`→`0x69`, `0x5A`→`0xF0`, etc.) across reflashes, but only the data byte (0x0441, 0x0A81) is validated. Markers are CalGroup-assigned at runtime, not stored in firmware.

### 3.3 Residual Gates After SBI Flip

- **ADB PROTOKEY/ICUSB module:** No residual gate once seed=0xFF and key is accepted. The module escalates to limited ADB (no GM-cert required). Session-level checks unknown; time-based gates not documented.
- **Other security layers:** Yes. The SBI flip **does not** unlock bootloader, secure boot, or Android kernel SELinux. It only bypasses the PROTOKEY seed/key for ADB (ICUSB module).
- **OTA/SPS resets:** Confirmed. Y181 stock → modified diff: both 0x0441 and 0x0A81 are reset by OTA. Must be re-applied after each update.

---

## 4. Calibration `$27` SBI Gate: Same Validator or Separate?

### 4.1 The Question

Does flipping the ADB SBI (`0x0440`/`0x0A80` → `0xFF`) also open the **calibration/diagnostic** UDS `$27` SecurityAccess gate (the lever on SCREEN_RESOLUTION writes)?

### 4.2 Evidence Summary

| Path | Transport | Handler | SBI Status | Seed Result | Evidence |
|------|-----------|---------|-----------|-------------|----------|
| **ADB** | CAN, ECU 0x80 | VIP firmware 0xb67d0 | Bypass confirmed | all-0xFF seed | Disasm + CAN capture (DPS log) |
| **Calibration** | Ethernet `:49156` or CAN | SoC `diagnosticsd` (Android app) | **Unknown** | Tested but inconclusive | `S27_SOC_VALIDATION_BENCH_TEST.md` |

### 4.3 Critical Finding: Two Different Validators

Per the CALDEF and firmware analysis:

- **ADB security:** Validated by **VIP PROTOKEY module**, reads EEPROM SBI at 0x0440, **returns all-0xFF seed** when SBI=0xFF.
- **Calibration `$27`:** Validated by **SoC `diagnosticsd`** (Android app layer), which has its **own SecurityAccess handler** (`SecurityRequestToResponsePipeline.cpp`, `checkSecurityLevelTable`). This handler **may** read a VIP-anchored flag, but it is **not** the same code path as the ADB PROTOKEY validator.

### 4.4 Evidence Level for Calibration Gate

| Claim | Level | Source | Status |
|-------|-------|--------|--------|
| Cal `$27` is gated by VIP/EEPROM | `[C]` | CALDEF_VIP_CALIBRATION_ANALYSIS.txt §4: "RID 021E converted to Security Access Request per IPC ver 2.6"; cal-programming validated via VIP | Established |
| ADB SBI flip opens cal `$27` | `[O]` | Untested. T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md §4 lists undocumented candidates (0x04A0, 0x04C0, 0x0A40, 0x0BE0) to probe | Open question |
| Cal `$27` uses same SBI byte (0x0440/0x0A80) as ADB | `[I]` | Logical (shared VIP layer), but not disasm-confirmed for the cal path | Inferred |
| Independent `$27` test via Ethernet shows different behavior from CAN | `[O]` | S27_SOC_VALIDATION_BENCH_TEST.md control test (MDI2/CAN returns all-0xFF; Ethernet `49156` from untrusted shell gets `7F 27 10` generalReject) | Testable; inconclusive from untrusted client |

### 4.5 Practical Implication

**Do not assume ADB SBI flip = calibration gate open.** They share an anchor (VIP/EEPROM), but the cal `$27` validator may be tied to a **different flag** (0x04A0, 0x04C0, or another). The T1/cal-convergence document explicitly flags this as the top priority experiment (§7 open item #3).

---

## 5. Checksum/Integrity Coverage: SBI Flip Impact

### 5.1 CRC Scope (Inferred, Unverified)

| CRC Address | Likely Coverage | Test Implication |
|-----------|---|---|
| 0x16E0 | Full EEPROM or main config block | Modifying 0x0440/0x0A80 may require recompute |
| 0x19E0 | Backup redundancy | Modify in parallel with 0x16E0? |
| 0x1A80 | Config region (0x0400–0x04FF?) | Security flags in this region; covers SBI? |
| 0x1B40, 0x1B60, 0x1B80 | Data/audio blocks | Separate from security flags? |

### 5.2 SBI Flip Procedure: Checksum Handling

**Current documented practice (eeprom/README.md):**
- Flip `0x0441` to 0xFF (primary SBI data byte).
- Flip `0x0A81` to 0xFF (backup SBI data byte).
- Optionally flip `0x0B41` to 0x01 (debug mode, observed in Y181 samples).
- **Checksums:** The shipped sample `Y181_modified.bin` had CRCs **already recomputed**, so the precise algorithm is not public. Empirically, the CRCs changed across the reflash.

**Risk:** If you flip SBI without recomputing the CRCs, the module may reject the image at boot (checksum validation failure) or trigger a factory reset.

### 5.3 Checksum Evidence

**Y181 stock → modified diff:**
- Data bytes (0x0441, 0x0A81, etc.): Changed as expected.
- CRC at 0x16E0: Changed from original.
- **Upper word** of CRCs: 0x0013 → 0x0104 (post-reflash). Suggests a **calibration version counter**, not just a data CRC.

**Gap:** No CRC-32 algorithm (polynomial, seed) is documented. Empirical options:
1. Use the shipped `Y181_modified.bin` as a template (extract intact, modify only the security bytes, preserve CRCs).
2. Reverse-engineer the CRC polynomial from the Y181 samples (XOR analysis).
3. Use a physical programmer with read-verify (minipro, XGecu) and test incrementally.

---

## 6. Undocumented Flags & Testing Priority

### 6.1 Candidates for Cal-`$27` Gate

From firmware xref analysis (EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md §10):

| Address | Refs | Region | Hypothesis | Test Priority | Risk |
|---------|------|--------|-----------|---|---|
| **0x04A0** | 17 | IPC security config | **Most likely** cal-`$27` gate. Early, tightly-packed config region (classic security descriptor). | **1st** | Low (early region, no OTP bits known) |
| **0x04C0** | 11 | IPC security config | Paired companion to 0x04A0 (access-level or variant selector). Test together if 0x04A0 alone fails. | **2nd** | Low |
| **0x0A40** | 28 | Feature flags region | Likely hidden-feature enable (cal menu, engineering mode). NOT the gate itself. | **3rd** | Medium (may boot into unstable feature) |
| **0x0BE0** | 24 | Late region (danger zone) | Probable manufacturing lock / debug-interface disable. OTP-like. **Do not flip without external recovery proven.** | **Never casually** | **HIGH** (may disable JTAG/SWD/I2C access) |

### 6.2 Testing Protocol (from EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md)

**Tier 0 (static analysis):** Extract VIP firmware, disasm, xref each address into the `$27` handler.  
**Tier 1 (dynamic, reversible):** Attach debugger, patch RAM shadow of EEPROM, test seed behavior. No EEPROM write.  
**Tier 2 (in-circuit reprogram):** I²C clip on the M24C64, flip one flag at a time, test, revert.  
**Tier 3 (physical desolder):** Last resort; requires external programmer for recovery.

**Stop condition:** Once any flag opens the cal `$27` gate (seed = all-0xFF or all-0x00, key accepted), **revert all others** to golden backup and stop.

---

## 7. Critical Gaps Before EEPROM Testing Starts

1. **CRC algorithm:** No polynomial or seed public. Empirical reverse-engineering or use shipped samples as templates.
2. **Undocumented flag polarity:** Which way to flip 0x04A0/0x04C0 (0xFF/0x00/0x01?)? Need static analysis or Tier-1 RAM test.
3. **Cal-`$27` gate ownership:** Is it the ADB SBI (0x0440), a different flag (0x04A0/0x04C0), or code-based (not EEPROM-governed)?
4. **Marker-byte independence:** Confirmed CalGroup assigns markers at runtime, not stored in firmware. Bypass is **marker-agnostic** — only data byte matters.
5. **In-band I²C access:** Can an SBI-enabled ADB shell write the M24C64 via `/dev/i2c-0`/`/dev/i2c-1`? Saves physical programming iterations.
6. **Y181 vs later:** Y181 is the last tested version. Newer OTA builds may have additional gates or re-locked SBI.

---

## 8. Complete Parameter Table

```
EEPROM MAP — ST M24C64 8KB (0x0000–0x1FFF)
═══════════════════════════════════════════════════════════════

0x0000–0x03FF  Boot/Init Configuration            [Byte-level, inferred]
  0x0000       Boot complete flag                 0x69 marker + 0x01 data
  0x0020       Secondary boot flag                0x69 marker
  
0x0400–0x04FF  SECURITY CONFIGURATION ★           [Disasm-confirmed + xref]
  0x0440       Primary SBI (ADB bypass)           0xFF=bypass, 0x00=locked [C]
  0x04A0       IPC Security Config #1 (?)         17 firmware refs [I]
  0x04C0       IPC Security Config #2 (?)         11 firmware refs [I]
  
0x0500–0x05FF  Device Identification              [Field-level, verified]
  0x0500       Part Number                        9 bytes
  0x05A0       Serial Number (CVPPS)              9 bytes
  0x05C0       VIN                                17 bytes
  
0x0A00–0x0AFF  BACKUP SECURITY & FEATURE FLAGS ★  [Mixed: 0x0A80 confirmed, others inferred]
  0x0A00       Structure base address             871 xrefs (not a flag) [I]
  0x0A40       Feature enable (?)                 28 refs [I]
  0x0A80       Backup SBI (ADB bypass)            0xFF=bypass, 0x00=locked [C]
  0x0AC0       Feature flag (?)                   14 refs [I]
  0x0B00       Feature structure base             311 xrefs (not a flag) [I]
  0x0B40       Debug Mode                         0x01=enabled [C]
  0x0BE0       Late-region flag (danger!) (?)     24 refs [I]
  
0x0E00–0x0EAF  Display/UI Settings                [Field-inferred, unverified]
  0x0E01–0x0E4D Timing/brightness/touch params    Guessed from dump [I]
  0x0E80–0x0EAF UI Flags Block                    Touch/haptic/animation toggles [I]
  
0x0EC0–0x0F7F  Display Calibration Tables         [Table-level, verified]
  0x0F00–0x0F3F Brightness LUT (11-point)
  0x0F40–0x0F7F Color/ambient calibration
  
0x0FE0–0x12DF  Audio Calibration Tables           [Table-level, verified]
  0x0FE0–0x103F Volume curve (11-point)
  0x1040–0x109F Fade/balance (22-point)
  0x10A0–0x12DF EQ/DSP (10 bands, 576 bytes)
  
0x16E0–0x1FFF  Checksums & CRCs ★                 [Byte-level, algorithm unknown]
  0x16E0       Primary CRC                        uint32 LE [I – no algorithm spec]
  0x19E0       Secondary CRC                      uint32 LE [I – backup]
  0x1A00       Tertiary security (?)              Modified in ADB bypass [I]
  0x1A80       Config CRC                         uint24 LE [I – coverage scope unclear]
  0x1B40–0x1B80 Data/Audio CRCs                   uint32 LE, three blocks [I]

[C] = Confirmed (disasm, CAN capture, empirical)
[I] = Inferred (firmware xref, byte patterns, educated guess)
```

---

## Summary

- **Enhancement:** EEPROM layout has evolved from a raw byte dump (Dec 2025) to a structured, xref-analyzed map (Feb 2026) with marker-byte discovery (Aug 2026).
- **SBI bypass:** Seed **fully disabled** (all-0xFF) when data byte = 0xFF; key **unconditionally accepted**. No residual ADB gate. Confirmed by disasm + CAN.
- **Calibration `$27`:** **NOT proven** to use the same SBI. Shares the VIP/EEPROM anchor, but validator may be separate code. Undocumented candidates (0x04A0, 0x04C0, 0x0A40, 0x0BE0) identified; Tier-0 static analysis needed before physical flip.
- **Checksum risk:** CRC algorithm unknown; shipping modified samples with recomputed CRCs suggests it is required. Do not flip SBI without addressing checksum coverage (either reverse-engineer or use template approach).
- **Top action:** Tier-0 static xref analysis of undocumented flags into the `$27` handler to pin the cal-security gate before EEPROM testing.

