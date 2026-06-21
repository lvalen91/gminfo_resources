# GM EEPROM Undocumented Flags Analysis

**Date:** 2026-01-05
**Last Updated:** 2026-02-11
**Purpose:** Discover potentially undocumented EEPROM flags based on GM's targeted security fixes
**Source:** VIP Firmware comparison (Y177 vs Y181), Calibration file analysis, Post-reflash EEPROM diff analysis

---

## Executive Summary

By analyzing what GM specifically targets in their security fixes and calibration resets, we can infer which EEPROM addresses are security-relevant beyond the known bypass flags. This reverse-engineering approach reveals **10 potentially undocumented flags** in security-sensitive regions.

> **Provenance / accuracy note (added during verification):** The firmware-reference
> counts cited below (0x0A00, 0x0B00, etc.) come from an external radare2 cross-reference
> pass over the full VIP_APP binary that is **not reproducible from the `firmware_re/`
> artifacts shipped in this repo**. Two analysis passes disagree — **0x0A00 = 871 (§2.2)
> vs 854 (§10.2)**, **0x0B00 = 311 vs 305** — so treat these as approximate RE-sourced
> figures, not dump-verified. The §10 function addresses (0xb67d0, 0xb6652, 0xaee28) are
> from that same external pass; only `0xecd84` exists in the shipped decompilation.

---

## 1. Known Security Flags (Documented)

| Address | Name | Bypass Value | Locked Value | Function |
|---------|------|--------------|--------------|----------|
| **0x0440** | Primary SBI | `[M] FF [M]` | `[M] 00 [M]` | Seed Bypass Indicator - enables ADB |
| **0x0A80** | Backup SBI | `[M] FF [M]` | `[M] 00 [M]` | Redundant security flag |
| **0x0B40** | Debug Mode | `[M] 01 [M]` | `[M] 00 [M]` | Developer/debug mode toggle |
| **0x1A00** | Tertiary Security | Unknown | `[M] 00 [M]` | Additional security layer |
| **0x0E80** | UI Flags Block | Varies | Varies | Contains UI feature flags |

> `[M]` = Marker byte (varies per EEPROM init cycle). See Section 13 for details.

### Observed Marker Assignments

| Address | Stock (pre-reflash) | Post-Y181 Reflash | ADB_enabled |
|---------|--------------------|--------------------|-------------|
| 0x0440 | `0xC3` | `0x69` | `0x5A` |
| 0x0A80 | `0xFF` (empty) | `0xF0` | `0x5A` |
| 0x0B40 | `0x69` | `0x5A` | `0x69` |
| 0x1A00 | `0x69` | `0x69` | — |

---

## 2. Undocumented Flags in Security Regions

### 2.1 Security Config Region (0x0400-0x0500)

| Address | Firmware Refs | Likely Purpose | Risk Level |
|---------|---------------|----------------|------------|
| **0x04A0** | 17 refs | Unknown security config | HIGH |
| **0x04C0** | 11 refs | Unknown security config | HIGH |

**Analysis:** These addresses are in the same region as 0x0440 (Primary SBI) and have significant firmware references, suggesting they're actively used security configuration flags.

### 2.2 Backup Security / Feature Flags Region (0x0A00-0x0C00)

| Address | Firmware Refs | Likely Purpose | Risk Level |
|---------|---------------|----------------|------------|
| **0x0A00** | 871 refs | Core security/feature base address | CRITICAL |
| **0x0A20** | 126 refs | SS_SWC timer configuration | MEDIUM |
| **0x0A40** | 28 refs | Unknown feature flag | HIGH |
| **0x0A60** | 15 refs | Unknown feature flag | MEDIUM |
| **0x0AC0** | 14 refs | Unknown feature flag | MEDIUM |
| **0x0B00** | 311 refs | Feature flags base address | HIGH |
| **0x0B20** | 7 refs | Unknown feature flag | MEDIUM |
| **0x0BE0** | 24 refs | Unknown feature flag | MEDIUM |

**Analysis:** The 0x0A80 backup SBI is in this region. The high reference count for 0x0A00 (871) and 0x0B00 (311) suggests these are base addresses for security/feature structures, not individual flags.

---

## 3. Calibration File Target Analysis

### 3.1 File 85783460 (SW ID 07 - Security Config)

This is the primary security calibration file that resets EEPROM security flags. It's 4,285 bytes and contains:

1. **Encrypted EEPROM payload** (0x050-0x350) - targets specific addresses
2. **CalOvride XML** (0x370+) - Bluetooth/audio calibrations

**Key Finding:** The encrypted payload section contains address:value pairs that reset security state. While we cannot decrypt it, we know it targets:
- 0x0440 (Primary SBI) → Reset to C300 (locked)
- 0x0A80 (Backup SBI) → Reset to C300 (locked)
- 0x0B40 (Debug Mode) → Reset to 6900 (off)
- Potentially other addresses in the 0x0400-0x0C00 range

### 3.2 File 87846384 (SW ID 13 - Security Flags)

Secondary security file (1,434 bytes) - also contains encrypted security payloads that may target additional addresses.

---

## 4. GM's Multi-Layered Security Reset Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GM SECURITY RESET MECHANISMS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: USB Update (VIP Firmware)                                          │
│  ├── VIP_APP initialization resets EEPROM to default state                  │
│  ├── Stubbed function (Y177) vs Full validation (Y181) @ 0xb67d0            │
│  └── ALWAYS resets security flags on firmware reinstall                     │
│                                                                              │
│  LAYER 2: SPS Calibration Files                                              │
│  ├── 85783460 (Security Config) - Encrypted EEPROM reset payload            │
│  ├── 87846384 (Security Flags) - Additional security resets                 │
│  └── Defense-in-depth: Added POST-disclosure to catch bypassed units        │
│                                                                              │
│  LAYER 3: VIP Security Validation Function                                   │
│  ├── Y177: 4-byte stub (always returns success)                             │
│  ├── Y181: 906-byte full implementation                                      │
│  │   ├── Loads debug/security flag from memory 0x3e06                       │
│  │   ├── Validates against expected security state                          │
│  │   └── Returns error if validation fails                                  │
│  └── Called by ICUSB/PROTOKEY modules before transmitting to SoC            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Complete EEPROM Security Map

### 5.1 Documented + Undocumented Addresses

```
EEPROM Address Map (M24C64 - 8KB)
═══════════════════════════════════════════════════════════════════════════

0x0000-0x03FF: Boot/Init Configuration
├── 0x0000: Boot complete flag
├── 0x0020: Secondary boot flag
├── 0x0040: Hardware revision marker
└── 0x03A0: ECUID block

0x0400-0x04FF: SECURITY CONFIGURATION BLOCK ★
├── 0x0400: Security config #1 (documented)
├── 0x0420: Security config #2 backup (documented)
├── 0x0440: ★ PRIMARY SBI - ADB BYPASS (documented)
├── 0x0460: Security level config (documented)
├── 0x0480: Security mode flags (documented)
├── 0x04A0: ? UNKNOWN - 17 firmware refs
├── 0x04C0: ? UNKNOWN - 11 firmware refs
└── 0x04E0: Unknown flag (documented)

0x0500-0x05FF: Device Identification
├── 0x0500: Serial Number
├── 0x05C0: VIN Storage ★
└── Other: Part numbers, dates

0x0A00-0x0AFF: BACKUP SECURITY BLOCK ★
├── 0x0A00: ? UNKNOWN - 871 firmware refs (likely base address)
├── 0x0A20: ? UNKNOWN - 126 refs (SS_SWC timer related)
├── 0x0A40: ? UNKNOWN - 28 firmware refs
├── 0x0A60: ? UNKNOWN - 15 firmware refs
├── 0x0A80: ★ BACKUP SBI - ADB BYPASS (documented)
├── 0x0AA0: Security backup data (documented)
├── 0x0AC0: ? UNKNOWN - 14 firmware refs
└── 0x0AE0: Additional security (documented)

0x0B00-0x0BFF: FEATURE FLAGS BLOCK ★
├── 0x0B00: ? UNKNOWN - 311 firmware refs (likely base address)
├── 0x0B20: ? UNKNOWN - 7 firmware refs
├── 0x0B40: ★ DEBUG/DEVELOPER MODE (documented)
├── 0x0B60: Security counter (documented)
├── 0x0B80: Feature enable #1 (documented)
├── 0x0BA0: Feature enable #2 (documented)
├── 0x0BC0: Feature toggle (documented)
└── 0x0BE0: ? UNKNOWN - 24 firmware refs

0x0C00-0x0DFF: Extended Configuration
└── 0x0C00: Unknown (ACTIVE in sample dump)

0x0E00-0x13FF: Display/Audio Calibration
├── 0x0E00: Display calibration
├── 0x0E80: ★ UI Flags Block
├── 0x1100: Audio calibration
└── Various: Brightness, color, volume curves

0x1600-0x1FFF: Integrity/Security
├── 0x16E0: CRC Checksum #1
├── 0x19E0: CRC Checksum #2
├── 0x1A00: ★ Tertiary security
└── 0x1F60: Secure Boot Hash (read-only)

═══════════════════════════════════════════════════════════════════════════
★ = Security-critical flag
? = Potentially undocumented, requires testing
```

---

## 6. Experimental Testing Recommendations

### 6.1 High Priority (Security Region)

| Address | Test | Expected Result |
|---------|------|-----------------|
| **0x04A0** | Set to `5AFF` | May enable additional debug feature |
| **0x04C0** | Set to `5AFF` | May enable additional debug feature |

### 6.2 Medium Priority (Feature Flags)

| Address | Test | Expected Result |
|---------|------|-----------------|
| **0x0A00** | Read current value, document | Understand base structure |
| **0x0A40** | Set to `5AFF` | May enable feature |
| **0x0A60** | Set to `5AFF` | May enable feature |
| **0x0AC0** | Set to `5AFF` | May enable feature |
| **0x0B00** | Read current value, document | Understand base structure |
| **0x0B20** | Set to `6901` | May enable feature |
| **0x0BE0** | Set to `5AFF` or `6901` | May enable feature |

### 6.3 Testing Protocol

1. **Backup original EEPROM** before any modifications
2. **Change ONE address at a time** to isolate effects
3. **Monitor VIP UART** for debug output changes
4. **Check Android properties** after boot (`getprop | grep debug`)
5. **Verify SELinux state** (`getenforce`)
6. **Test ADB** without GM Secure Client
7. **Document any visible changes** in UI/behavior

---

## 7. Why This Matters

### 7.1 Potential Hidden Features

GM may have additional debug/development modes controlled by these undocumented flags that could:
- Enable additional diagnostic outputs
- Unlock development features
- Provide lower-level system access
- Enable test modes for specific subsystems

### 7.2 Security Implications

If GM is resetting these addresses via calibration files, they consider them security-relevant. Modifying them could:
- Affect vehicle security state
- Enable features not intended for production
- Potentially bypass additional security layers

### 7.3 Firmware Correlation

The fact that Y177→Y181 fixed the security validation function without changing the EEPROM address table means:
- The EEPROM structure is stable across versions
- Fixes are in how values are validated, not what values exist
- Undocumented flags may work in both versions if found

---

## 8. VIP Firmware Security Function Analysis

### Address: 0x000b67d0

#### Y177 Implementation (STUBBED)
```asm
; 4 bytes - Always returns success
mov 0, r10      ; Return value = 0 (success)
jmp [lp]        ; Return to caller
```

#### Y181 Implementation (FULL)
```asm
; 906 bytes - Full validation
; 1. Load debug/security flag from memory 0x3e06
; 2. Compare against expected value
; 3. Multiple conditional branches for different states
; 4. Call validation functions:
;    - 0xecd84 (unknown)
;    - 0xb6652 (unknown)
;    - 0xaee28 (unknown)
; 5. Return error codes on validation failure
```

#### Callers
- 0xb6b06 (in fcn.000b67d4)
- 0xb6e82 (in fcn.000b6bd0)

These are in the ICUSB/PROTOKEY module code path.

---

## 9. Conclusions

1. **GM's security fix was in the validation function, not EEPROM structure**
   - Y177 and Y181 reference identical EEPROM addresses
   - The stubbed function at 0xb67d0 was the vulnerability

2. **Calibration files target multiple addresses for reset**
   - File 85783460 contains encrypted payload resetting security state
   - GM added this defense-in-depth after public disclosure

3. **10 potentially undocumented flags identified**
   - 2 in security config region (0x04A0, 0x04C0)
   - 8 in feature flags region (0x0A00-0x0BE0 range)

4. **High reference counts suggest active use**
   - 0x0A00 (871 refs) and 0x0B00 (311 refs) are likely base addresses
   - Others with 10+ refs are likely individual flags

5. **Testing required to determine function**
   - Addresses identified by analysis, function unknown
   - Safe testing protocol recommended

6. **Marker bytes are runtime-generated, not static (Feb 2026)**
   - Identical Y181 firmware produces different markers on each EEPROM init
   - 31+ marker assignments changed after USB reflash with identical binary
   - No literal marker patterns found in firmware binary
   - CalGroup system (15 groups) manages marker assignment at runtime
   - Security validation checks data byte only, not markers

7. **Backup SBI (0x0A80) now actively initialized**
   - Was previously `0xFF` (empty) in stock dumps
   - Latest Y181 init writes locked value with assigned marker
   - Both SBI locations now require modification for bypass

8. **Bypass procedure is marker-agnostic**
   - Read EEPROM → identify current markers → change only data bytes
   - `0x0441`=`0xFF`, `0x0A81`=`0xFF`, `0x0B41`=`0x01`
   - Preserves whatever markers CalGroup assigned

---

## Appendix A: Quick Reference

```
KNOWN BYPASS FLAGS (marker byte [M] varies per init cycle):
├── 0x0440: Primary SBI      → [M] FF [M] (bypass), [M] 00 [M] (locked)
├── 0x0A80: Backup SBI       → [M] FF [M] (bypass), [M] 00 [M] (locked)
└── 0x0B40: Debug Mode       → [M] 01 [M] (on), [M] 00 [M] (off)

BYPASS PROCEDURE:
├── 1. Read current EEPROM to identify marker bytes at each address
├── 2. Change ONLY the data byte (offset+1) — preserve markers
├── 3. Write: 0x0441=0xFF, 0x0A81=0xFF, 0x0B41=0x01
└── 4. Marker bytes are irrelevant to security validation

POTENTIALLY UNDOCUMENTED (High Priority):
├── 0x04A0: Security region, 17 refs
├── 0x04C0: Security region, 11 refs
├── 0x0A40: Feature flags, 28 refs
└── 0x0BE0: Feature flags, 24 refs

LIKELY BASE ADDRESSES (Not individual flags):
├── 0x0A00: 871 refs - probably structure base
└── 0x0B00: 311 refs - probably structure base
```

---

---

## 10. Radare2 Disassembly Analysis

### 10.1 Security Validation Function (0xb67d0)

The critical security validation function was analyzed using radare2 with V850 architecture support.

#### Y177 Implementation (STUBBED - 4 bytes)
```asm
; Function always returns success - NO VALIDATION
mov 0, r10      ; Return value = 0 (success)
jmp [lp]        ; Return to caller
```

#### Y181 Implementation (FULL - 906 bytes)
```asm
0x000b67d0  prepare {r20-r29, lp}, 4, sp    ; Save registers
0x000b67d4  mov r6, r25                      ; Store input parameter
0x000b67d6  zxb r25                          ; Zero-extend byte
...
0x000b67e4  movhi -323, r0, r9               ; Load base address
0x000b67e8  ld.bu 15878[r9], r9              ; Load flag from 0x3e06
0x000b67ec  mov 0, r28                       ; Initialize result
0x000b67f0  cmp 1, r9                        ; Compare flag against 1
0x000b67f2  <conditional branches based on security state>
...
; Calls to validation subroutines:
0x000b680a  jarl 0xecd84, lp                 ; Call validation function #1
0x000b6820  jarl 0xb6652, lp                 ; Call security level check
0x000b6844  jarl 0xaee28, lp                 ; Call validation function #2
```

**Key Finding:** The flag at memory address 0x3e06 is the processed EEPROM value loaded during boot. This corresponds to the SBI flags at EEPROM addresses 0x0440/0x0A80.

### 10.2 Undocumented Address Context Analysis

Using radare2 cross-reference analysis, we identified the code context for each undocumented address:

#### 0x04A0 & 0x04C0 - IPC Security Configuration

Found near `[IPC_S]` debug strings:
```
[IPC_S] UART read failed
[IPC_S] UART read done with incorrect size
[IPC_S] IPCCLIENT: ipcClose: ERROR Failed: %d
[IPC_S] IPCCLIENT: ERROR ipcCoreWriteCommand failed
```

**Inference:** These flags likely control IPC/UART communication security settings. The `IPC_S` module handles secure inter-processor communication between VIP and SoC.

**Test Recommendation:** Set to `5AFF` and monitor UART debug output for changes in IPC behavior.

#### 0x0A20 - System State Timer Configuration

Found near `[SS_SWC]` and `[GYROACCL]` debug strings:
```
[SS_SWC] STBC_WUF0WUF0 = 0x%lX, wakeup_factor = 0x%X
[GYROACCL] accel_reg_read call for Accelerometer failed
```

**Inference:** This address controls system state and possibly sensor calibration timers. The SS_SWC module manages sleep/wake states.

**Test Recommendation:** Read current value and observe changes during power state transitions.

#### 0x0A00 & 0x0B00 - Structure Base Addresses

These addresses have extremely high reference counts (854 and 305 respectively) and appear in pointer arithmetic patterns:

```asm
; Example pattern from code
movhi baseaddr, r0, r18
ld.bu offset[r18], r9    ; Load from base + offset
```

**WARNING:** These are base addresses for data structures, NOT individual toggle flags. Modifying them will corrupt multiple configuration values.

### 10.3 ICUSB Enable Logic Analysis

The ICUSB module (providing ADB access) enable state is controlled by this code path:

```asm
; At 0x9ce22
movhi -322, r0, r19              ; Load base address
ld.bu 29007[r19], r19            ; Load flag from memory 0x714f
cmp 1, r19                       ; Compare with 1
bne skip_icusb_enable            ; Skip if not 1
; ... ICUSB initialization code ...
jarl 0x97d78, lp                 ; Call ICUSB init
```

The memory address 0x714f contains the processed ICUSB enable state, which is determined by:
1. EEPROM flag at 0x0440 (Primary SBI)
2. Validation result from security function at 0xb67d0

### 10.4 Validation Subroutine Analysis

| Address | Purpose | Notes |
|---------|---------|-------|
| 0xecd84 | Unknown validation | Calls deeper functions at 0xf5cb8, 0xec4be |
| 0xb6652 | Security level check | Returns based on input range checks |
| 0xb6680 | Feature state check | Loads from 0x71e0, compares against 3 |
| 0xb6690 | Debug state check | Loads from 0x71ed, checks if zero |
| 0xaee28 | Unknown validation | Part of validation chain |

---

## 11. Testing Recommendations Based on Analysis

### 11.1 High Priority Tests (Security Region)

| Address | Current Value | Test Value | Expected Behavior |
|---------|---------------|------------|-------------------|
| **0x04A0** | Read first | `5AFF` | May enable IPC debug mode |
| **0x04C0** | Read first | `5AFF` | May enable UART security bypass |

### 11.2 Medium Priority Tests (Feature Flags)

| Address | Test Value | Rationale |
|---------|------------|-----------|
| **0x0A40** | `5AFF` | In feature flags region, moderate refs |
| **0x0A60** | `5AFF` | In feature flags region |
| **0x0AC0** | `5AFF` | In feature flags region |
| **0x0B20** | `6901` | Near 0x0B40 debug mode flag |
| **0x0BE0** | `5AFF` or `6901` | Unknown marker type |

### 11.3 Do NOT Modify

| Address | Reason |
|---------|--------|
| **0x0A00** | Base address for feature structure (854 refs) |
| **0x0B00** | Base address for feature structure (305 refs) |
| **0x0A20** | Timer configuration, may affect power states |

---

## 12. Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VIP SECURITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EEPROM (M24C64)                     RAM (after boot load)                   │
│  ┌──────────────────────┐            ┌──────────────────────┐               │
│  │ 0x0440: Primary SBI  │ ─────────► │ 0x3e06: Security flag│               │
│  │ 0x0A80: Backup SBI   │            │ 0x714f: ICUSB enable │               │
│  │ 0x0B40: Debug Mode   │            │ 0x71e0: Feature state│               │
│  │ 0x04A0: IPC Security │            │ 0x71ed: Debug state  │               │
│  │ 0x04C0: IPC Security │            └─────────┬────────────┘               │
│  └──────────────────────┘                      │                             │
│                                                 ▼                             │
│                              ┌─────────────────────────────────┐             │
│                              │ Security Validation @ 0xb67d0   │             │
│                              │ ┌─────────────────────────────┐ │             │
│                              │ │ Y177: STUBBED (4 bytes)     │ │             │
│                              │ │   → Always returns success  │ │             │
│                              │ │                             │ │             │
│                              │ │ Y181: FULL (906 bytes)      │ │             │
│                              │ │   → Validates security state│ │             │
│                              │ │   → Calls validation chain  │ │             │
│                              │ └─────────────────────────────┘ │             │
│                              └──────────────┬──────────────────┘             │
│                                             │                                │
│                                             ▼                                │
│                              ┌─────────────────────────────────┐             │
│                              │ ICUSB/PROTOKEY Module           │             │
│                              │ → ADB access control            │             │
│                              │ → Seed/Key authentication       │             │
│                              └─────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Marker Byte Rotation Discovery (Feb 2026)

### 13.1 Finding

After re-flashing the **identical Y181 firmware** (PN 86331656, hash `c381ed1c507d6ac6381c315fe94d9114`) via USB, the EEPROM marker/framing bytes changed at 31+ addresses while all data values remained identical. No SPS calibration files were included in the update.

### 13.2 Marker Transition Map

| Old Marker | New Marker | Count | Affected Regions |
|-----------|-----------|-------|-----------------|
| `0xC3` → `0x69` | 4 | Primary SBI, display/color calibration |
| `0x5A` → `0xF0` | 8 | VIN, display settings, brightness, volume, VIN suffix |
| `0x69` → `0x5A` | 3 | Secondary serial, debug mode, touch version |
| `0xF0` → `0x5A` | 4+ | Unknown toggle, all audio tables (0x1040-0x1280) |
| `0x69` → `0xC3` | 1 | Feature toggle (0x0BC0) |
| `0x69` → `0xF0` | 1 | CRC #1 (0x16E0) |

Not a consistent permutation — individual addresses map to different new markers.

### 13.3 Unchanged Markers

The following regions kept their original markers across reflash:
- Boot/init flags: 0x0000, 0x0020, 0x0040 (always `0x69`)
- Security configs: 0x0400, 0x0420 (always `0x69`)
- Security level/mode: 0x0460, 0x0480 (always `0xF0`)
- Device ID strings: 0x0500-0x05A0 (always `0xF0`)
- Tertiary security: 0x1A00 (always `0x69`)
- Secure boot hash: 0x1F60 (always `0x69`)

### 13.4 Root Cause: CalGroup Runtime Generation

Exhaustive binary search of the VIP_APP firmware confirmed:
- **Zero** instances of literal marker patterns (`69 00 69`, `C3 00 C3`, `5A FF 5A`) in the binary
- The firmware contains 15 CalGroups managed by a `[CAL]` module
- EEPROM writes go through CalGroup routines: `[CAL] EEPROM Write Failure for CalGroup-%d`
- Read failures trigger defaults: `read eeprom error !, Reinstating the default value`
- Marker bytes are generated at runtime during VIP_APP initialization, not stored as static data

### 13.5 Security Implication

The security validation function at `0xb67d0` loads the **data byte** from RAM address `0x3e06` (mapped from EEPROM 0x0440/0x0A80). It does **not** validate the marker byte. This is confirmed by:
1. Marker bytes aren't stored in the firmware as expected values
2. Different marker assignments across identical firmware flashes would break validation if markers were checked
3. The CalGroup system would need to communicate its marker choices to the security function — no such mechanism exists

### 13.6 Backup SBI Now Populated

| Dump | 0x0A80 Value | Status |
|------|-------------|--------|
| Stock (original) | `FF FF FF` | Uninitialized/empty |
| ADB_enabled | `5A FF 5A` | Bypassed |
| Post-Y181 reflash | `F0 00 F0` | **Now initialized, locked** |

GM's latest EEPROM init now actively writes a locked value to the backup SBI, closing the gap where it was previously uninitialized.

### 13.7 CRC Version Counter

CRC blocks contain what appears to be a calibration version counter in the upper word:

| CRC | Stock | Post-Reflash | Delta |
|-----|-------|-------------|-------|
| CRC #1 (0x16E0) | `00 0013 1531` | `00 0104 9F67` | Upper: 0x0013→0x0104 |
| CRC #2 (0x19E0) | `00 0013 0DB5` | `00 0104 17F8` | Upper: 0x0013→0x0104 |
| Data CRC (0x1B40) | `00 0013 189D` | `00 0104 A314` | Upper: 0x0013→0x0104 |

### 13.8 USB Update Package

| File | Module | Size | Identical to Previous Y181 |
|------|--------|------|---------------------------|
| 86331656 | VIP_APP | 1.84 MB | Yes (byte-for-byte) |
| 85056831 | VIP_BOOT | 1.84 MB | Yes (byte-for-byte) |
| 86331654 | SOC_SYSTEM | 1.45 GB | — |
| 86331636 | SOC_PRODUCT | 1.32 GB | — |
| 86331650 | SOC_VENDOR | 145 MB | — |
| 86331652 | SOC_BOOT | 64 MB | — |
| 85098662 | SOC_HOSTOS | 14 MB | — |
| + 8 more | GPS, Tuner, SXM, etc. | — | — |

No SPS calibration files (85783460, 87846384) present.

---

## 14. Updated Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VIP SECURITY ARCHITECTURE (Updated Feb 2026)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EEPROM (M24C64)                     RAM (after boot load)                   │
│  ┌──────────────────────┐            ┌──────────────────────┐               │
│  │ 0x0440: [M] val [M]  │ ─────────► │ 0x3e06: Security flag│               │
│  │ 0x0A80: [M] val [M]  │    (only   │ 0x714f: ICUSB enable │               │
│  │ 0x0B40: [M] val [M]  │    val is  │ 0x71e0: Feature state│               │
│  │ 0x04A0: [M] val [M]  │   loaded)  │ 0x71ed: Debug state  │               │
│  │ 0x04C0: [M] val [M]  │            └─────────┬────────────┘               │
│  └──────────────────────┘                      │                             │
│    ▲ Markers [M] assigned                      ▼                             │
│    │ at runtime by CalGroup    ┌─────────────────────────────────┐           │
│    │ (15 groups, [CAL] module) │ Security Validation @ 0xb67d0   │           │
│    │                           │   Checks val (data byte) ONLY   │           │
│  ┌─┴──────────────────────┐   │   Does NOT check marker [M]     │           │
│  │ CalGroup System        │   │                                  │           │
│  │ ├─ Runtime marker gen  │   │ Y177: STUBBED (4 bytes)          │           │
│  │ ├─ 15 CalGroups        │   │   → Always returns success       │           │
│  │ ├─ EEPROM R/W mgmt     │   │ Y181: FULL (906 bytes)           │           │
│  │ └─ Default reinstate   │   │   → Validates data byte state    │           │
│  └────────────────────────┘   └──────────────┬──────────────────┘           │
│                                               │                              │
│                                               ▼                              │
│                                ┌─────────────────────────────────┐           │
│                                │ ICUSB/PROTOKEY Module           │           │
│                                │ → ADB access control            │           │
│                                │ → Seed/Key authentication       │           │
│                                └─────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**Document Version:** 3.0
**Analysis Method:** Static firmware analysis, calibration file analysis, radare2 disassembly, post-reflash EEPROM diff
**Tools Used:** radare2 6.0.8, Python 3, strings, xxd
**Architecture:** Renesas RH850 (V850)
**Classification:** Security Research

