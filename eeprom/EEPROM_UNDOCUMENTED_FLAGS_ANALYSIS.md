# GM EEPROM Undocumented Flags Analysis

**Date:** 2026-01-05
**Last Updated:** 2026-02-11
**Purpose:** Discover potentially undocumented EEPROM flags based on GM's targeted security fixes
**Source:** VIP Firmware comparison (Y177 vs Y181), Calibration file analysis, Post-reflash EEPROM diff analysis

---

## Executive Summary

By analyzing what GM specifically targets in their security fixes and calibration resets, we can infer which EEPROM addresses are security-relevant beyond the known bypass flags. This reverse-engineering approach reveals **10 potentially undocumented flags** in security-sensitive regions.

> **Provenance / accuracy note (added during verification; updated Aug–Sep 2026):** The
> firmware-reference counts cited below ("N firmware refs" for 0x04A0, 0x0A00, 0x0B00, etc.) come
> from an external radare2 **string-proximity** pass that is **not reproducible from the
> `firmware_re/` artifacts shipped in this repo** and disagrees with itself between passes
> (0x0A00 = 871 §2.2 vs 854 §10.2; 0x0B00 = 311 vs 305). **That entire "N refs" framing is now
> superseded.** A real Ghidra decompilation pass (`VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`,
> `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`) found the actual EEPROM-access mechanism — one generic
> "CalGroup cell" accessor `FUN_ram_000c8db6` (1,301 call sites / 170 handler functions / 1,050
> distinct cell IDs) — and checked every candidate against it directly. **Result: of the four
> "undocumented" candidates, `0x04A0`, `0x0A40`, `0x0BE0` have zero real code references, and all
> four (`0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0`) read `0xFF` (unwritten, no stored data) in both the
> stock and ADB_enabled dumps (confirmed by xxd of `csm_eeprom/gm_csm_stock.bin` &
> `.../gm_csm/Y181/ADB_enabled.bin` at each offset); `0x04C0` alone is referenced by a real
> CalGroup 0x44 handler (`FUN_ram_00091f82`), but the EEPROM cell is still empty.** Treat the
> candidate-flag tables below as historical. The §10 function addresses (0xb67d0, 0xb6652, 0xaee28)
> DO exist as real functions in the correct `86331656_ghidra` project (the earlier "only 0xecd84
> exists in the shipped decompilation" note reflected an incomplete project import — see
> `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` §0); **`0xecd84` itself is a generic RTOS mutex primitive
> (285 call sites), not a security-validation function.**

---

## 1. Known Security Flags (Documented)

| Address | Name | Bypass Value | Locked Value | Function |
|---------|------|--------------|--------------|----------|
| **0x0440** | Primary SBI | `[M] FF [M]` | `[M] 00 [M]` | Seed Bypass Indicator — 0xFF data byte forces the VIP's degenerate all-0xFF `$27` seed. **Broader than ADB:** the same degenerate seed appears on the VIP's plain CAN `$27` UDS stack, not just ADB/ICUSB. Storage: CalGroup `0x3b`, cells `0x43a–0x447`, read-only accessor `FUN_ram_00091938`. |
| **0x0A80** | Backup SBI | `[M] FF [M]` | `[M] 00 [M]` | Empirically mirrors 0x0440 — ADB_enabled.bin holds byte-identical `5A FF 5A FF` at both (xxd-confirmed). NOTE: the "both SBIs must match for the bypass to hold" *mechanism* is unverified/likely wrong — exhaustive static analysis found zero real code references to 0x0A80/0x0A81 in either VIP binary; only the mechanism is disputed, the empirical mirror pair is real. |
| **0x0B40** | Debug Mode (UNCONFIRMED, see note) | `[M] 01 [M]` | `[M] 00 [M]` | Developer/debug mode toggle |
| **0x1A00** | Tertiary Security | Unknown | `[M] 00 [M]` | Additional security layer |
| **0x0E80** | UI Flags Block | Varies | Varies | Contains UI feature flags |

> `[M]` = Marker byte (varies per EEPROM init cycle). See Section 13 for details.

> **0x0B41 "Debug Mode" status — OPERATOR-TESTED, unconfirmed (2026-09-10):** the "Debug
> Mode" label for 0x0B40/0x0B41 is a byte-diff inference (it changed between stock and
> modified Y181 dumps alongside the two SBIs), not a confirmed code read-site. An operator
> flipped 0x0B41 as part of the working bypass triad (`0x0441=FF / 0x0A81=FF / 0x0B41=01`,
> §Appendix A) and observed **no change in AAOS behavior** — adb remained `uid 2000` and
> SELinux stayed enforcing. No decompiled read-site has been found tying 0x0B41 to
> `ro.debuggable`, SELinux-permissive, or OEM-unlock. Treat 0x0B41's runtime effect as
> **OPEN / UNCONFIRMED**, under active VIP-disasm investigation; the ADB-enable effect of
> the bypass triad is produced by 0x0441/0x0A81 (the two SBIs), not by 0x0B41.

### Observed Marker Assignments

| Address | Stock (pre-reflash) | Post-Y181 Reflash | ADB_enabled |
|---------|--------------------|--------------------|-------------|
| 0x0440 | `0xC3` | `0x69` | `0x5A` |
| 0x0A80 | `0xFF` (empty) | `0xF0` | `0x5A` |
| 0x0B40 | `0x69` | `0x5A` | `0x69` |
| 0x1A00 | `0x69` | `0x69` | — |

---

## 2. Undocumented Flags in Security Regions

> **SUPERSEDED (Aug–Sep 2026 — see provenance note above).** The "Firmware Refs" counts in the
> tables in this section are string-proximity artifacts, not real code references. A real Ghidra
> pass found no genuine code reference for `0x04A0`, `0x0A40`, or `0x0BE0`, and an xxd of both the
> stock and ADB_enabled dumps shows `0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0` all `0xFF` (unwritten, no
> stored data). Only `0x04C0` is touched by a real code handler (CalGroup 0x44, `FUN_ram_00091f82`)
> — and even there the EEPROM cell itself is empty. The tables below are retained as historical
> record only; do not treat these as active flags. Detail:
> `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`.

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

### 3.1 File 85783460 (SW ID 07) — **RETRACTED 2026-09-10, see below**

> **RETRACTION (2026-09-10):** the "Security Config" framing and the address:value table below are
> **refuted** by a full byte-level decode of the real file (owner's own A11 calibration set,
> `diagnostics/gm_dps/calibrations/A11_calibration.zip`, external corpus — see
> `A11_CALIBRATION_FILES_COMPLETE_ANALYSIS_AUG2026.md`). The `0x0440`/`0x0A80` "match" below is a
> **coincidence**: those are plain DEFLATE-compressed bytes sitting at the same numeric *file offset*
> as the EEPROM SBI addresses — not an EEPROM address:value patch. Decompressing the gzip stream
> (offset `0x368`) shows the file is an ordinary **`calserviced` CalOvride XML** — 34 overrides: 12
> Booleans (all `true`), 1 Integer(0), and 21 `.scd` telephony/voice-DSP tuning blobs (SSE echo-
> cancellation sets for BT/CarPlay/Android Auto/OnStar). **Searched all 14 real A11 calibration files
> end-to-end for `0440`/`0a80`/`0b40`/`eeprom`/`security`/`SBI`/`bypass`/`VIN` — zero hits in any
> file.** There is a genuine unexplained artifact — a 792-byte, AES-CBC-shaped encrypted envelope
> (with a per-file 16-byte IV) present in *every* CSM calibration file's header (`0x050-0x367`),
> most consistent with a per-file signature/manifest (key not recovered; likely tied to the same
> `S84.dll`/`dllsecurity.dll` material in `eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`) — but it is
> fixed-size in every file (including two *empty* CalOvride files), so it cannot be a variable-length
> EEPROM address:value list. Preserving the original (wrong) text below for provenance; do not
> treat it as current.

<details><summary>Original (retracted) text</summary>

This is the primary security calibration file that resets EEPROM security flags. It's 4,285 bytes and contains:

1. **Encrypted EEPROM payload** (0x050-0x350) - targets specific addresses
2. **CalOvride XML** (0x370+) - Bluetooth/audio calibrations

**Key Finding:** The encrypted payload section contains address:value pairs that reset security state. While we cannot decrypt it, we know it targets:
- 0x0440 (Primary SBI) → Reset to C300 (locked)
- 0x0A80 (Backup SBI) → Reset to C300 (locked)
- 0x0B40 (Debug Mode) → Reset to 6900 (off)
- Potentially other addresses in the 0x0400-0x0C00 range

</details>

### 3.2 File 87846384 (SW ID 13) — **also retracted**

> Per the same 2026-09-10 decode: 87846384 is 19 ordinary CalOvride overrides (13 Boolean, 1
> Integer, 5 enum) — not security data. Original text below preserved for provenance only.

<details><summary>Original (retracted) text</summary>

Secondary security file (1,434 bytes) - also contains encrypted security payloads that may target additional addresses.

</details>

---

## 4. GM's Multi-Layered Security Reset Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GM SECURITY RESET MECHANISMS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: USB Update (VIP Firmware)                                          │
│  ├── VIP_APP re-init can restore EEPROM CalGroups to ROM defaults           │
│  ├── VIP validator @0xb67d0 is FULL (~906B) in ALL builds — NO stub         │
│  │     (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0; 3-way diff 2026-08-25) │
│  └── restore-to-defaults resets flags on re-init (see VIP_SBI_WRITE_...)    │
│                                                                              │
│  LAYER 2: SPS Calibration Files — **RETRACTED 2026-09-10, see §3.1/3.2**    │
│  ├── (was: 85783460/87846384 "Encrypted EEPROM reset payload" — refuted;    │
│  │    both are ordinary calserviced CalOvride overrides, no EEPROM refs)    │
│                                                                              │
│  LAYER 3: VIP Seed/Key SecurityAccess Function @0xb67d0                      │
│  ├── FULL ~906-byte impl in ALL builds (NO Y177 stub — corrected)           │
│  │   ├── Gates ADB/seed ($27) auth ONLY — NOT SELinux, NOT AVB              │
│  │   ├── Reads RAM 0x3e06 = module-init readiness flag (NOT the SBI value)  │
│  │   └── Returns UDS NRC on validation failure                             │
│  └── Shared multi-slot engine: CAN $27 path + ICUSB/PROTOKEY path           │
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
├── 0x04A0: 0xFF unwritten (both dumps); zero real code refs (SUPERSEDED — see §2)
├── 0x04C0: 0xFF unwritten; real CalGroup 0x44 handler FUN_ram_00091f82, empty cell
└── 0x04E0: Unknown flag (documented)

0x0500-0x05FF: Device Identification
├── 0x0500: Serial Number
├── 0x05C0: VIN Storage ★
└── Other: Part numbers, dates

0x0A00-0x0AFF: BACKUP SECURITY BLOCK ★
├── 0x0A00: ref count retired (string-proximity, superseded — see §2)
├── 0x0A20: ref count retired (string-proximity, superseded)
├── 0x0A40: 0xFF unwritten (both dumps); zero real code refs (SUPERSEDED)
├── 0x0A60: ref count retired (string-proximity, superseded)
├── 0x0A80: ★ BACKUP SBI - ADB BYPASS (documented)
├── 0x0AA0: Security backup data (documented)
├── 0x0AC0: ref count retired (string-proximity, superseded)
└── 0x0AE0: Additional security (documented)

0x0B00-0x0BFF: FEATURE FLAGS BLOCK ★
├── 0x0B00: ref count retired (string-proximity, superseded — see §2)
├── 0x0B20: ref count retired (string-proximity, superseded)
├── 0x0B40: ★ DEBUG/DEVELOPER MODE (label UNCONFIRMED — operator-tested, no effect; see §1)
├── 0x0B60: Security counter (documented)
├── 0x0B80: Feature enable #1 (documented)
├── 0x0BA0: Feature enable #2 (documented)
├── 0x0BC0: Feature toggle (documented)
└── 0x0BE0: 0xFF unwritten (both dumps); zero real code refs (SUPERSEDED)

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

> **SUPERSEDED:** `0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0` all read `0xFF` (unwritten) in the real dumps
> and are not live flags (see §2). The tests below are retained as historical record only.

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

### Address: 0x000b67d0 (Y181; Y177 @0xb67d4, Y175 @0xb6708)

> **CORRECTED 2026-08-25 (three-way VIP_APP diff, superseding the earlier "Y177 stub" reading):**
> there is **NO stub**. A full ~906-byte seed/key SecurityAccess validator exists in **ALL** builds
> (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0), confirmed byte-for-byte. This function gates
> **ADB/seed ($27) auth only — it does NOT set SELinux mode and does NOT touch AVB.** The primary
> ADB/seed gate is SoC-side (MEC / `is_secure_mode`, `gm_adb_auth_init`); the EEPROM SBI + this VIP
> function gate the seed/key path. See `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`.

#### Implementation (FULL — identical across all builds)
```asm
; ~906 bytes - Full validation, identical in Y175/Y177/Y181 (no stub)
; 1. Read RAM 0x3e06 = "security module initialized" readiness flag
;      (a module-init flag, NOT the processed EEPROM SBI value — corrected)
; 2. Range/bitmask-validate the requested SecurityAccess level (0x02-0x14)
; 3. Multiple conditional branches for different states
; 4. Call helper functions:
;    - 0xecd84  generic RTOS mutex acquire primitive (285 call sites — NOT a validator)
;    - 0xb6652  level-range mapping/validation
;    - 0xaee28  slot/state clear
; 5. Return UDS NRC (0x31/0x22) on validation failure
```

#### Callers
Reached via an indirect/dispatch mechanism — a multi-slot SecurityAccess dispatch shared by the
CAN `$27` path and the ICUSB/PROTOKEY path (same engine, not separate code). See
`VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` §6.

---

## 9. Conclusions

1. **There was no "validation-function security fix" — the Y177-stub premise is REFUTED**
   - Y175/Y177/Y181 all carry the SAME full ~906-byte validator (three-way diff 2026-08-25); no stub ever existed
   - Y177 and Y181 reference identical EEPROM addresses
   - The bypass is the degenerate all-0xFF `$27` seed handed out when the SBI data byte = 0xFF, not a stubbed function

2. ~~**Calibration files target multiple addresses for reset**~~ **RETRACTED 2026-09-10** — the
   real, fully-decoded calibration files contain no EEPROM/SBI/security references at all (see
   §3.1). This "defense-in-depth" model is not supported by the actual file contents.

3. ~~**10 potentially undocumented flags identified**~~ **REFUTED (Aug–Sep 2026)** — the "N refs"
   evidence was string-proximity, not real code references. Of the four security-region candidates,
   `0x04A0`/`0x0A40`/`0x0BE0` have zero real code refs, and `0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0` all
   read `0xFF` (unwritten) in both dumps. Only `0x04C0` is referenced by real code (CalGroup 0x44,
   `FUN_ram_00091f82`) — and even that cell is empty. See `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`.

4. ~~**High reference counts suggest active use**~~ **REFUTED** — the 0x0A00/0x0B00 "base address"
   ref counts came from the same superseded string-proximity pass; the real EEPROM access path is a
   single generic CalGroup-cell accessor (`FUN_ram_000c8db6`), not per-address literal references.

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

9. **0x0B41 "Debug Mode" write produced no observable effect (2026-09-10, OPEN)**
   - Operator set 0x0B41=0x01 as part of the working bypass triad and saw adb stay at
     `uid 2000` with SELinux enforcing — no behavioral change attributable to this byte
   - The "Debug Mode" name is unverified; no code read-site confirmed
   - Still under active VIP-disasm investigation — see note under §1 table

---

## Appendix A: Quick Reference

```
KNOWN BYPASS FLAGS (marker byte [M] varies per init cycle):
├── 0x0440: Primary SBI      → [M] FF [M] (bypass), [M] 00 [M] (locked)
├── 0x0A80: Backup SBI       → [M] FF [M] (bypass), [M] 00 [M] (locked)
└── 0x0B40: Debug Mode (UNCONFIRMED, no observed effect — §1 note) → [M] 01 [M] (on), [M] 00 [M] (off)

BYPASS PROCEDURE:
├── 1. Read current EEPROM to identify marker bytes at each address
├── 2. Change ONLY the data byte (offset+1) — preserve markers
├── 3. Write: 0x0441=0xFF, 0x0A81=0xFF, 0x0B41=0x01
└── 4. Marker bytes are irrelevant to security validation

UNDOCUMENTED CANDIDATES — REFUTED (Aug–Sep 2026; "N refs" was string-proximity):
├── 0x04A0: 0xFF unwritten (both dumps); zero real code refs
├── 0x04C0: 0xFF unwritten; real CalGroup 0x44 handler (FUN_ram_00091f82) but empty cell
├── 0x0A40: 0xFF unwritten; zero real code refs
└── 0x0BE0: 0xFF unwritten; zero real code refs

"BASE ADDRESSES" (0x0A00/0x0B00): ref counts retired — real EEPROM access is one generic
CalGroup-cell accessor (FUN_ram_000c8db6), not per-address literal references.
```

---

---

## 10. Radare2 Disassembly Analysis

### 10.1 Security Validation Function (0xb67d0)

The seed/key SecurityAccess function was analyzed with radare2 (originally decoded as V850; the
current authoritative disassembly uses the **RH850:LE:32** SLEIGH module — the V850 pass was only
an approximation, superseded by fresh RH850 projects).

> **CORRECTED:** there is no Y177 stub. The full ~906-byte implementation below exists in ALL
> builds (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0), confirmed by three-way diff 2026-08-25.

#### Implementation (FULL ~906 bytes, identical across Y175/Y177/Y181)
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

**Key Finding (CORRECTED):** RAM `0x3e06` is a generic **"security module initialized" readiness
flag** (1 = init complete, 0 = reset), **not** the processed EEPROM SBI value — it is mapped from
the 0x0440/0x0A80 region but does not carry the SBI data byte. The earlier "0x3e06 = processed
EEPROM SBI value" claim is refuted (see `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` §2).

### 10.2 Undocumented Address Context Analysis

> **SUPERSEDED (Aug 2026).** The "code context" below is string-proximity, not real cross-references.
> A real Ghidra pass (`VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`) found the `[IPC_S]` strings live
> in a different part of the binary (`ram:0001adfe–0001be06`) from any handler touching these cells,
> with no code link — the `0x04A0`/`0x04C0` ↔ `[IPC_S]` association is coincidental. `0x04A0` has no
> genuine code reference (its one apparent hit is a struct-relative false positive); `0x04C0` is
> referenced by CalGroup 0x44 (`FUN_ram_00091f82`) but the EEPROM cell reads `0xFF` (unwritten). The
> `0x0A00`/`0x0B00` "base address" ref counts are the same superseded string-proximity signal.

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
| 0xecd84 | Generic RTOS mutex acquire primitive (NOT a validator) | 285 call sites across unrelated subsystems; reused inside security code but not specific to it — see `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` §1/§7 |
| 0xb6652 | Security level range-mapping/validation | Returns based on input range checks |
| 0xb6680 | Feature state check | Loads from 0x71e0, compares against 3 |
| 0xb6690 | Debug state check | Loads from 0x71ed, checks if zero |
| 0xaee28 | Slot/state clear | Part of the seed/key state machine |

---

## 11. Testing Recommendations Based on Analysis

> **NOTE (Aug–Sep 2026):** the candidate addresses in this section (`0x04A0`, `0x04C0`, `0x0A40`,
> `0x0BE0`, and the `0x0A00`/`0x0B00` "base addresses") are superseded — see §2 and the provenance
> note. `0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0` all read `0xFF` (unwritten) in the dumps and are not
> usable flags; the ref counts below are the retired string-proximity figures. Retained as
> historical test log only.

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
│  │ 0x0440: Primary SBI  │ ─────────► │ 0x3e06: init-rdy flag│               │
│  │ 0x0A80: Backup SBI   │            │ 0x714f: ICUSB enable │               │
│  │ 0x0B40: Debug Mode(?)│            │ 0x71e0: Feature state│               │
│  │ 0x04A0: (empty 0xFF) │            │ 0x71ed: Debug state  │               │
│  │ 0x04C0: (empty 0xFF) │            └─────────┬────────────┘               │
│  └──────────────────────┘                      │                             │
│                                                 ▼                             │
│                              ┌─────────────────────────────────┐             │
│                              │ Security Validation @ 0xb67d0   │             │
│                              │ ┌─────────────────────────────┐ │             │
│                              │ │ FULL ~906B, all builds      │ │             │
│                              │ │   → identical, all builds   │ │             │
│                              │ │                             │ │             │
│                              │ │ Full ~906B; gates $27       │ │             │
│                              │ │   → NOT SELinux, NOT AVB    │ │             │
│                              │ │   → checks data byte only   │ │             │
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

> **⚠CORRECTED (2026-08-17 provenance audit):** The quoted hash `c381ed1c507d6ac6381c315fe94d9114`
> does NOT match the md5 of the shipped `.../update_packages/Y181/86331656`, which is
> `e47928d9f409834083abc9a068ce65e0`. The quoted value may be from a different packaging/extraction
> stage, but it is not reproducible from the artifact in this repo/tree — treat the PN-to-hash
> binding as unverified. The marker-rotation OBSERVATION itself (bytes changed, data identical) is a
> separate empirical claim and is not affected. See PROVENANCE_AUDIT_AUG2026.md #9.

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
  > **⚠CORRECTED (2026-08-17 provenance audit):** This specific statement is FALSE. A hex scan
  > of the shipped `86331656` finds `69 00 69` ×3 and `C3 00 C3` ×4 (only `5A FF 5A` = 0). The
  > broader conclusion — that markers are runtime-generated by the CalGroup system and not
  > validated — still holds on the independent two-variant-diff evidence (§13.6, and audit #4),
  > but do not cite "zero literal patterns" as support. See PROVENANCE_AUDIT_AUG2026.md #7.
- The firmware contains 15 CalGroups managed by a `[CAL]` module
- EEPROM writes go through CalGroup routines: `[CAL] EEPROM Write Failure for CalGroup-%d`
- Read failures trigger defaults: `read eeprom error !, Reinstating the default value`
- Marker bytes are generated at runtime during VIP_APP initialization, not stored as static data

### 13.5 Security Implication

The security validation function at `0xb67d0` validates the **data byte**, **not** the marker byte.
(Note: RAM `0x3e06`, which it reads, is now understood to be a generic "security module
initialized" readiness flag mapped from the 0x0440/0x0A80 region — **not** the SBI data value
itself; see §10.1 and `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` §2. The marker-agnostic conclusion is
unaffected.) This is supported by:
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
│  │ 0x0440: [M] val [M]  │ ─────────► │ 0x3e06: init-rdy flag│               │
│  │ 0x0A80: [M] val [M]  │    (only   │ 0x714f: ICUSB enable │               │
│  │ 0x0B40: [M] val [M]  │    val is  │ 0x71e0: Feature state│               │
│  │ 0x04A0: FF, empty    │   loaded)  │ 0x71ed: Debug state  │               │
│  │ 0x04C0: FF, empty    │            └─────────┬────────────┘               │
│  └──────────────────────┘                      │                             │
│    ▲ Markers [M] assigned                      ▼                             │
│    │ at runtime by CalGroup    ┌─────────────────────────────────┐           │
│    │ (15 groups, [CAL] module) │ Security Validation @ 0xb67d0   │           │
│    │                           │   Checks val (data byte) ONLY   │           │
│  ┌─┴──────────────────────┐   │   Does NOT check marker [M]     │           │
│  │ CalGroup System        │   │                                  │           │
│  │ ├─ Runtime marker gen  │   │ FULL ~906B, all builds           │           │
│  │ ├─ 15 CalGroups        │   │   → identical, all builds        │           │
│  │ ├─ EEPROM R/W mgmt     │   │ Full ~906B; gates $27            │           │
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
**Architecture:** Renesas RH850 (authoritative disassembly: RH850:LE:32 SLEIGH module; the earlier V850 pass was an approximation, now superseded)
**Classification:** Security Research

