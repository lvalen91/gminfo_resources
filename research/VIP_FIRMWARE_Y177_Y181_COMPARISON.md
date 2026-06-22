# VIP Firmware Y177 vs Y181 Security Analysis

**Date:** 2026-01-05
**Purpose:** Document critical differences between Y177 and Y181 VIP firmware that explain the EEPROM bypass behavior

> Companion doc: `VIP_CONTROL_ANALYSIS.txt` covers the broader EEPROM/board/DPS attack
> surface (full 8 KB EEPROM memory map, CRC locations + "CRC not enforced at boot", framing
> bytes, world-accessible `/dev/i2c`, IS25LP016 SPI flash, ECUID/MEC/SBAT, DPS can/cannot
> limits). This document is the focused VIP firmware binary-diff; the two are complementary.
> EEPROM bypass values cross-checked against the shipped bins: `0x0441`/`0x0A81` value→`0xFF`,
> `0x0B41` value→`0x01` (this doc's "0x0B40: 6900 → 6901" is correct). Note the *framing*
> byte does not always become `5A` — the Y181 stock/modified bins keep `F0` @0x440 and `C3`
> @0x0A80; only the value byte changes. Locate each byte by offset, not framing value.

---

## Executive Summary

The Y177 VIP firmware contains a **STUBBED security validation function** that was **FULLY IMPLEMENTED in Y181**. This is the mechanism by which the EEPROM modification allowed permissive SELinux mode in Y177 but not in Y181.

---

## 1. Firmware Overview

| Property | Y177 | Y181 |
|----------|------|------|
| **File Name** | 86283151 | 86331656 |
| **Size** | 1,934,214 bytes | 1,934,214 bytes |
| **Build Date** | 25Feb28-0330 (Feb 28, 2025) | 25Jun19-2209 (Jun 19, 2025) |
| **Version Hash** | f96a2ca5bbbc97c3440840f35d73bb2f | c381ed1c507d6ac6381c315fe94d9114 |
| **Functions** | 10,340 identified | 10,350 identified |

---

## 2. Critical Finding: Stubbed Security Function

### Address: 0x000b67d0

#### Y177 Implementation (STUBBED - 4 bytes)

```asm
mov 0, r10    ; Always return 0 (success/no error)
jmp [lp]      ; Return to caller
```

**Effect:** This function ALWAYS RETURNS SUCCESS, bypassing any security validation that depends on it.

#### Y181 Implementation (FULL - 906 bytes)

```asm
; Full implementation including:
; - Load debug/security flag from memory 0x3e06
; - Compare against expected value (cmp 1, r9)
; - Multiple conditional branches for different security states
; - Calls to validation functions (0xecd84, 0xb6652, 0xaee28)
; - Returns error codes on validation failure
```

**Effect:** This function NOW PERFORMS ACTUAL VALIDATION of the security state, blocking unauthorized access.

### Callers of This Function

- 0xb6b06 (in fcn.000b67d4)
- 0xb6e82 (in fcn.000b6bd0)

---

## 3. How the EEPROM Bypass Worked in Y177

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Y177 EEPROM BYPASS FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User modifies EEPROM:                                           │
│     ├── 0x0440: C300 → 5AFF (Security bypassed)                     │
│     ├── 0x0A80: C300 → 5AFF (Security bypassed)                     │
│     └── 0x0B40: 6900 → 6901 (Debug mode ON)                         │
│                                                                     │
│  2. VIP boots and reads EEPROM values                               │
│                         │                                           │
│                         ▼                                           │
│  3. ICUSB module checks debug state                                 │
│     ├── Loads flag from memory (processed EEPROM value)             │
│     ├── Calls security validation function (0xb67d0)                │
│     └── Y177: Function returns 0 (STUBBED - always success)         │
│                         │                                           │
│                         ▼                                           │
│  4. VIP sends IPC message to SoC                                    │
│     ├── ProtoKey transmitted via SERIAL_IPC_PROTO_KEY_CHANNEL       │
│     └── Message indicates debug/permissive mode should be active    │
│                         │                                           │
│                         ▼                                           │
│  5. SoC (Android) receives message                                  │
│     ├── Honors the debug state from VIP                             │
│     └── Y177: SELinux stays PERMISSIVE                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Why Y181 Blocks the Bypass

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Y181 SECURITY ENFORCEMENT                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Same EEPROM modification made                                   │
│                         │                                           │
│                         ▼                                           │
│  2. VIP boots and reads EEPROM values                               │
│                         │                                           │
│                         ▼                                           │
│  3. ICUSB module checks debug state                                 │
│     ├── Loads flag from memory                                      │
│     ├── Calls security validation function (0xb67d0)                │
│     ├── Y181: Function PERFORMS ACTUAL VALIDATION                   │
│     │   ├── Validates against expected security state               │
│     │   └── Returns ERROR if validation fails                       │
│                         │                                           │
│                         ▼                                           │
│  4. VIP sends IPC message to SoC                                    │
│     ├── ProtoKey transmitted but validation failed                  │
│     └── Message indicates normal/enforcing mode                     │
│                         │                                           │
│                         ▼                                           │
│  5. SoC (Android) receives message                                  │
│     └── Y181: SELinux stays ENFORCING                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Binary Differences Summary

### Overall Changes

| Metric | Value |
|--------|-------|
| Total bytes different | 549,518 (28.4% of firmware) |
| Header region (<0x5000) | 340 bytes |
| Code region (0x5000-0xE0000) | 516,502 bytes |
| Data region (>0xE0000) | 32,676 bytes |

Most differences appear to be address/offset adjustments from recompilation rather than logic changes.

### Significant Function Size Changes

| Address | Y177 Size | Y181 Size | Change | Notes |
|---------|-----------|-----------|--------|-------|
| **0xb67d0** | 4 bytes | 906 bytes | +902 | **Security validation stub → full implementation** |
| 0x87e2c | - | - | -2424 | Optimized/removed code |
| 0xe839a | - | - | +660 | New checks |
| 0xd427e | - | - | +622 | New checks |
| 0x77fb8 | - | - | +530 | New checks |

---

## 6. EEPROM Address References (Identical in Both)

| Pattern | Addresses Found | Purpose |
|---------|-----------------|---------|
| 0x0440 | 0x248aa, 0x24b26 | Security config |
| 0x0A80 | 0x24b9e | Debug EEPROM |
| 0x0B40 | 0x24c22 | Debug mode flag |

---

## 7. Key Strings (Identical in Both)

### ProtoKey/ICUSB Related

| Address | String |
|---------|--------|
| 0x7c1a | `[AME_DIAG] ICUSB enabled and both key are provisioned.` |
| 0x7cf6 | `[AME_DIAG] ICUSB not enabled.` |
| 0xaf46 | `[PROTOKEY] ICUSB module disabled` |
| 0xaf6a | `[PROTOKEY] ICUSB module enabled` |
| 0x1658e | `[J6_CDD] J6_prv_ProtoKey:Protokey transmitted to SoC, status is %d` |

---

## 8. VIP-to-SoC Communication Path

```
VIP reads EEPROM → PROTOKEY module → J6_CDD module → Serial IPC → SoC

The ProtoKey data is transmitted from VIP to SoC via:
  SERIAL_IPC_PROTO_KEY_CHANNEL
```

---

## 9. Hardware Architecture

### VIP MCU (Renesas RH850)

| Component | Location | Size |
|-----------|----------|------|
| VIP_BOOT | RH850 Internal Flash | ~128KB |
| VIP_APP | RH850 Internal Flash | ~1.9MB |
| Configuration Data | External M24C64 EEPROM | 8KB |

### Memory Organization

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RH850 INTERNAL FLASH                              │
├─────────────────────────────────────────────────────────────────────┤
│  VIP_BOOT (Bootloader)                                               │
│  ├── Signature validation                                            │
│  ├── Flash programming routines                                      │
│  └── Recovery mode                                                   │
├─────────────────────────────────────────────────────────────────────┤
│  VIP_APP (Application)                                               │
│  ├── PROTOKEY module                                                 │
│  ├── J6_CDD (Communication Driver)                                   │
│  ├── ICUSB module                                                    │
│  └── Security validation @ 0xb67d0 (stubbed Y177, full Y181)        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL M24C64 EEPROM                            │
├─────────────────────────────────────────────────────────────────────┤
│  0x0440: Primary SBI Flag                                            │
│  0x0A80: Backup SBI Flag                                             │
│  0x0B40: Debug Mode Flag                                             │
│  0x05C0: VIN                                                         │
│  [Full memory map in EEPROM_Analysis_Report.md]                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Y177 SELinux Permissive Explanation

**Key Insight:** Y177 SELinux was always permissive when EEPROM bypass was active.

Users never noticed because:
1. Production radios were never expected to have EEPROM bypass enabled
2. The stub function at 0xb67d0 returned success regardless of input
3. VIP sent "debug mode active" IPC to SoC
4. SoC honored the debug state → SELinux permissive

This is a classic case of **"security by stub removal"** - during development, a security check was stubbed out for testing or because the validation logic wasn't ready. In Y177, it shipped with the stub still in place. Y181 replaced the stub with the actual implementation.

---

## 10.1 Disclosure Timeline and GM Response

### Observed Timeline

| Event | Approximate Date | Significance |
|-------|------------------|--------------|
| Y175 released | Early 2024 | EEPROM bypass worked |
| Y177 released | Feb 2025 | EEPROM bypass still worked (stubbed function) |
| **EEPROM findings published online** | Post-Y177 | Community disclosure |
| Y181 released | Jun 2025 | Security function implemented, bypass blocked |
| Calibration files updated | Post-Y181 | Security reset added to SPS calibrations |

### Correlation Analysis

**Before Public Disclosure (Y175-Y177):**
- USB updates reset EEPROM (standard firmware initialization behavior)
- SPS calibrations did NOT reset security flags
- VIP_APP contained stubbed security function
- EEPROM bypass → SELinux permissive

**After Public Disclosure (Y181+):**
- USB updates continue to reset EEPROM
- SPS calibrations NOW reset security flags (defense-in-depth)
- VIP_APP contains full security validation (906 bytes vs 4 bytes)
- EEPROM bypass → SELinux still enforcing

### GM's Multi-Layered Response

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GM SECURITY HARDENING (Y181)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LAYER 1: VIP Firmware Fix                                           │
│  ├── Replaced stubbed function at 0xb67d0 with full implementation   │
│  ├── Now validates security state before sending IPC to SoC          │
│  └── Effect: EEPROM bypass no longer triggers permissive SELinux     │
│                                                                      │
│  LAYER 2: Calibration File Defense-in-Depth                          │
│  ├── Added security flag reset to calibration file 85783460          │
│  ├── SPS calibrations now re-lock EEPROM addresses 0x0440/0x0A80     │
│  └── Effect: Even if bypass is applied, next calibration removes it  │
│                                                                      │
│  LAYER 3: Continued USB Update Reset                                 │
│  └── VIP firmware initialization continues to reset EEPROM           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Implications

This timeline suggests GM actively monitors community security research and responds with targeted fixes. The response was comprehensive:

1. **Root cause fix** - Implemented the security validation that should have been there
2. **Defense-in-depth** - Added redundant reset mechanism via calibrations
3. **No public acknowledgment** - Standard vendor practice for security fixes

**Note:** This correlation does not confirm causation, but the timing and specificity of fixes strongly suggest GM's security team reviewed the public EEPROM bypass documentation.

---

## 11. Hybrid Package Approach Analysis

### Concept

Install Y181 update package but substitute VIP firmware file with Y177 version.

### Update Package Contents (Y181)

| File | Component | Identical Y177? |
|------|-----------|-----------------|
| VIP_APP (86331656) | VIP Application | **NO** - Different |
| VIP_BOOT | VIP Bootloader | YES |
| SOC_HOSTOS | Android/GHS | YES |
| SOC_ABL | Android Bootloader | YES |

### Challenges

1. **Manifest Hash Mismatch**: Package manifest (86331663.mnf) contains SHA256 hashes
2. **Signature Validation**: .smd signature file validates manifest
3. **GHS Rollback Protection**: Hypervisor blocks full downgrade but may allow reinstall

### Potential Mitigation Flags

Found in update handling:
- `version check disabled`
- `Bypass P/N & Module ID Check`

These suggest validation may be relaxed in some configurations.

---

## 12. Downgrade/Upgrade Behavior

### GHS Hypervisor Rollback Protection

| Scenario | Result |
|----------|--------|
| Y181 → Y177 full package | **BLOCKED** by GHS |
| Y181 → Y181 reinstall | Allowed |
| Y181 Android + Y177 VIP | Unknown (needs testing) |

### Update Path Independence

```
USB Update Package:
├── SOC Components (Android, vbmeta, boot) → GHS validates, blocks downgrade
└── VIP_APP → Separate update path, may not have rollback protection
```

---

## Conclusion

GM fixed the EEPROM bypass in Y181 by implementing security validation code that was previously stubbed out in Y177. The stub function at 0xb67d0 that returned 0 (success) in Y177 was replaced with actual validation logic in Y181, preventing the EEPROM modification from enabling permissive SELinux mode.

The Android-side init scripts and gm_protokey binary are **IDENTICAL** between versions, confirming the change is definitively in the VIP firmware processing.

---

## Related Documents

- [EEPROM_Analysis_Report.md](EEPROM/EEPROM_Analysis_Report.md) - Full EEPROM memory map
- [EEPROM_CALIBRATION_MAPPING.md](../gm_dps/EEPROM_CALIBRATION_MAPPING.md) - Calibration file analysis
- [VIP_BOOT_CONTROL_ANALYSIS.md](../gm_dps/VIP_BOOT_CONTROL_ANALYSIS.md) - VIP boot control mechanisms

---

**Document Version:** 1.0
**Last Updated:** 2026-01-05
**Classification:** Security Research
