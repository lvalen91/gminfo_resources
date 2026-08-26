# VIP Firmware Y175 / Y177 / Y181 Security Analysis (three-way)

**Date:** 2026-01-05 · **Corrected:** 2026-08-25
**Purpose:** Binary-diff of the Harman VIP (Renesas RH850) application across three GM builds,
and the security posture of its validation function.

> **MAJOR CORRECTION (2026-08-25).** The original version of this document (v1.0) claimed the
> VIP security validation function at `0x000b67d0` was a **4-byte stub in Y177** that was
> **fully implemented in Y181**, and that this stub was the mechanism by which Y177 ran
> permissive SELinux. **That finding was wrong.** A three-way diff adding the newly reacquired
> **Y175** VIP_APP shows all three builds carry the *same* full ~906-byte validation function.
> The "stub" was an artifact of reading a **fixed absolute address across recompiled, shifted
> images** — see §2. The stub-dependent narrative (bypass flow, GM-response timeline, hybrid
> attack) has been corrected accordingly. Evidence-backed reference material (ProtoKey IPC path,
> EEPROM addresses, strings, hardware, downgrade behavior) was verified still valid and retained.

> Companion doc: `VIP_CONTROL_ANALYSIS.txt` covers the broader EEPROM/board/DPS attack surface
> (8 KB EEPROM map, CRC-not-enforced-at-boot, framing bytes, world-accessible `/dev/i2c`,
> IS25LP016 SPI flash, ECUID/MEC/SBAT, DPS limits). EEPROM bypass values cross-checked against
> the shipped bins: `0x0441`/`0x0A81` value→`0xFF`, `0x0B41` value→`0x01`. The *framing* byte
> does not always become `5A` — Y181 stock/modified bins keep `F0` @0x440 and `C3` @0x0A80;
> only the value byte changes. Locate each byte by offset, not framing value.

---

## Executive Summary

All three VIP_APP builds — **Y175, Y177, and Y181** — contain the **same fully-implemented**
~906-byte security validation function. There is **no stub in any build**, and therefore the
VIP firmware is **not** the mechanism that made a live Y177 unit run permissive SELinux. The
earlier "Y177 stub → permissive" claim was a false positive from comparing the fixed absolute
address `0xb67d0` across images whose code shifted by a few bytes between recompiles.

**Stock Y177 does not run permissive at all.** Its `system/bin/init` is byte-identical to
Y175's and Y181's and forces enforcing on a `user` build (`ALLOW_PERMISSIVE_SELINUX=0`), ignoring
the `androidboot.selinux=permissive` cmdline (see `security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8); any past "permissive" observation was a false finding/misread (both CSMs only ever ran stock
offline packages — a userdebug/modified image or `setenforce` is ruled out), at most a misattributed
transient during EEPROM flag experimentation. SELinux mode is decided OS-side by init and is neither
EEPROM- nor VIP-driven, so no EEPROM/VIP experiment can produce a permissive runtime. Independently,
the shipped **Y175** `/system` is a `user`/`release-keys`
build whose init **forces enforcing despite an `androidboot.selinux=permissive` boot cmdline**
(see `../gm_aaos/.../analysis/Y175_OS_PARTITION_INVESTIGATION_AUG2026.md`), confirming the
permissive cmdline alone does not yield a permissive runtime.

---

## 1. Firmware Overview

| Property | Y175 | Y177 | Y181 |
|----------|------|------|------|
| **Part / File** | 85759599 | 86283151 | 86331656 |
| **Size** | 1,934,214 B | 1,934,214 B | 1,934,214 B |
| **Build Date** | 24Apr23-2202 | 25Feb28-0330 | 25Jun19-2209 |
| **VIP App Version** | 2B.175.1.5 | — | — |
| **SHA-256** | d729fa4b…dd1ad239 | ed2bdff7…f81144aa | dbdbb9da…e0f87acc |

**VIP_BOOT (85056831) is byte-identical across all three** (sha256 `2792ac3a4e7d…c27f746b`).

---

## 2. Security Validation Function — FULL in all three builds, now RH850-decoder-confirmed

**Status (2026-08-25, pass 2): re-disassembled with the real RH850 SLEIGH module
(`RH850:LE:32:default`), not the earlier V850 approximation.** `pyghidra` 3.1.0 was used to
open each raw image (`BinaryLoader`, load base `0x0`, `analyze=False`) and linear-disassemble
the routine, its two callers-in-context, and its three named callees in all three revisions.
Every instruction below is a live decode, not inferred from the V850 pass.

### The corrected finding — reconfirmed

| Build | Function entry | Body size | State |
|-------|----------------|-----------|-------|
| Y175 | `0xb6708` | ~906 bytes | **FULL** |
| Y177 | `0xb67d4` | ~906 bytes | **FULL** |
| Y181 | `0xb67d0` | ~906 bytes | **FULL** |

All three share an identical prologue and the `0xFEBD3E06` flag load, and call the same
validator set (`0xecd84`, `0xb6652`, `0xaee28`). Aligned body diffs:

- Y177 `@0xb67d4` vs Y181 `@0xb67d0` — **15 / 906 bytes** differ (relocated call operands only).
- Y175 `@0xb6708` vs Y181 `@0xb67d0` — **18 / 906 bytes** differ.
- Identical entry bytes at all three: `88 07 e3 ff 06 c8 99 00 03 3d 05 45 07 4d 83 a7`, which
  the RH850 decoder resolves as:
  `prepare {r20-r29,lp},0x4,sp` · `mov r6,r25` · `zxb r25` · `sst.w r7,0x4[ep]` ·
  `sst.w r8,0x8[ep]` · `sst.w r9,0xc[ep]` · `ld.bu 0x3c[sp],r20` — a normal C-function prologue
  saving 10 callee-saved registers + `lp` and pulling in 4 register args + 1 stack arg
  (`r20` = an 8-bit request/command code, tested later against 0–5). This confirms — at the
  instruction level, not just the byte level — that the function is a real, fully-bodied
  dispatcher in every build, not a stub.

### Why the original "Y177 stub" reading was wrong — and what the RH850 decode adds

The v1.0 disassembly locked onto the *absolute* address `0xb67d0` in every image. Between
recompiles the code shifts: Y181's function sits at `0xb67d0`, but Y177's identical function
moved to `0xb67d4` (+4) and Y175's to `0xb6708`. Reading Y177 at the fixed `0xb67d0` therefore
landed **4 bytes early**, on the *tail of the previous function*.

The RH850 decode confirms exactly what is at that tail address and settles the "stub" question
completely: at `entry-4` (`0xb67cc` in Y181, `0xb67d0` in Y177, `0xb6704` in Y175) sits

```
dispose 0x1,{r26,r27,r28,r29,lp},[lp]     ; epilogue+return of the PRECEDING function
mov 0x0,r10                                ; <- entry of an unrelated 4-byte helper
jmp [lp]                                   ;    "return 0"
```

So the "4-byte stub" from the v1.0 finding is **real code**, just not a truncated copy of the
906-byte validator — it is a **separate, trivial, shared `return 0` utility** that happens to
sit immediately before the validator in the image, and the validator itself calls it (`jarl
0x…67cc,lp`) once near its tail as a "set default/success status" helper. A naive byte compare
at the fixed offset shows 863/906 bytes "different" (pure misalignment) purely because it is
comparing this 4-byte stub-and-prologue region against the real validator body; realigning to
the true entry (`0xb67d4` for Y177) collapses that to 15/906.

### Methodology / tooling

- Three fresh linear disassembly passes at load base `0x0`, RH850 decoder, cross-checked with
  byte-level alignment (raw-file diff, independent of the disassembler).
- Ghidra 12.1.2 ships **no** RH850 module by default; a dedicated **RH850 SLEIGH module**
  (`RH850:LE:32:default`, from ZEEKRZERO/Ghidra-RH850, compiled against 12.1.2) is installed
  under `Ghidra/Processors/RH850/` and was used directly for this pass (via `pyghidra`), fully
  replacing the earlier `V850:LE:32:default` approximation. All decodes below (`prepare`,
  `sst.w`, `movhi`/`movea` hi/lo pairs, `jarl`, `sld.bu`/`sld.hu`/`sld.w` short-form loads,
  `cmovne`, `setfe`/`setfnh`) are RH850-specific encodings the V850 module would not resolve
  correctly, which is the confirmation that this pass is decoder-accurate rather than V850-approximated.
- The +4 / +0xc8 entry shift and the full-function-in-all-builds result remain confirmed at the
  raw byte level as well (the 15/906 and 18/906 aligned diffs above), independent of the
  disassembler — the RH850 pass corroborates rather than merely repeats that result.

### Callers — corrected

`0xb6b06` and `0xb6e82` (Y181 addressing, inherited from the pre-existing table) are **not**
external call sites into the validator's entry point (`0xb67d0`). Direct disassembly at both
addresses shows they are the instruction **immediately after** a `jarl` to the small `return 0`
helper at `entry-4` (`0xb67cc`):

- `0xb6b02: jarl 0x000b67cc,lp` → return lands at `0xb6b06`, **inside the validator's own body**
  (near its tail, storing `r10` into a status-struct field at `0xc[r29]`).
- `0xb6e7e: jarl 0x000b67cc,lp` → return lands at `0xb6e82`, inside a **structurally near-identical
  sibling function** starting around `0xb6bd0` that repeats the same
  bitmask-completeness-check / status-write pattern seen at the validator's tail.

So the two "caller" addresses are self-references to the shared `return 0` helper, one from
inside the validator itself and one from a sibling function with parallel logic — not evidence
of an outer function invoking the validator. Identifying the validator's own true caller(s) was
out of scope for this pass (it requires searching for `jarl` operands equal to the entry address
itself, `0xb67d0`/`0xb67d4`/`0xb6708`, across the wider VIP_APP image) and is flagged as an open
item below.

### Delta classification — every differing byte is a relocation, not a logic change

Each differing byte (raw file diff, aligned to each build's true entry) was mapped back to the
RH850 instruction it falls inside, in all three builds, and classified as either a **relocated
call/data operand** (address changed only because something moved between recompiles) or a
**genuine instruction/constant/logic change**.

**Y177 vs Y181 — 15/15 bytes are relocated call operands, 0 genuine changes:**

| # | Offset(s) | Y181 addr | Instruction (both builds) | Classification |
|---|-----------|-----------|----------------------------|-----------------|
| 1–15 | 60,268,280,342,354,402,410,418,430,438,570,708,720,874,886 | `0xb680c`…`0xb6b46` | `jarl 0x000ecd84,lp` or `jarl 0x000ecdac,lp` (low byte of the 22-bit PC-relative call displacement) | **Relocated call operand.** Same two callees (trace-enter/trace-exit, §3.3) at the *same* absolute addresses in both builds; only the caller-side instruction address shifted by the function's known `+4` entry offset, so the PC-relative displacement's low byte drops by exactly `4` at every one of the 15 sites. No mnemonic, register, or tag-argument differs. |

Every one of the 15 differing bytes is a `jarl` operand low byte; there is no cluster where the
opcode, addressing mode, or a non-address immediate changed. **Tally: 15 relocated / 0 logic.**

**Y175 vs Y181 — 18 bytes across 17 instructions; 15 relocated call operands + 2 relocated data-address operands, 0 genuine changes:**

| Category | Count (instructions) | Bytes | Example |
|----------|----------------------|-------|---------|
| Relocated call operand (`jarl`) | 15 | 15 | `jarl 0x000eccb4,lp` (Y175) vs `jarl 0x000ecd84,lp` (Y181) — same trace-enter callee, callee itself relocated between the ~14-month Y175→Y181 span, not a logic change (tag args identical at each site) |
| Relocated data-address operand (`mov <imm32>,reg`) | 2 | 3 (one 2-byte cluster) | `mov 0xfebe71dc,r29` (Y175) vs `mov 0xfebe71e4,r29` (Y181) — same struct, `+0x2f` field, same `cmp 0x1` test, base address moved 8 bytes; `mov 0x715b0,r8` (Y175) vs `mov 0x71600,r8` (Y181) — same table-index-and-load sequence, base moved `0x50` bytes |
| Genuine instruction/constant/logic change | 0 | 0 | none found |

**Tally: 17/17 differing instructions are address relocations (15 call-operand + 2 data-operand); 0/17 are logic changes.** This extends the existing "relocated call operands only" claim for Y177↔Y181 to Y175↔Y181 as well, with the RH850 decoder confirming operand types precisely (call vs. absolute-data-load) rather than relying on byte-position heuristics. Also notable: the two flag addresses central to §3.1 (`0xFEBD3E06`, `0xFEBD4DA0`, `0xFEBD4D9C`, `0xFEBDA50E`) are **not** among the relocated operands in either diff — they are byte-identical in all three builds, unlike the unrelated `0xFEBE71xx` struct and `0x71xxx` table bases which drifted with the rest of the binary's data layout.

**Confidence:** high for the classification (mnemonics, operand roles, and callee addresses were
read directly off the RH850 decode, not inferred). The one residual unknown is *why* the
`0xFEBE71xx` struct and the `0x7 15b0/71600` table moved between Y175 and Y181 while the
`0xFEBD3Exx`/`0xFEBD4Dxx` block did not — most likely explained by unrelated additions/removals
elsewhere in the RAM/data layout between the two builds' compiles, but this was not traced
further (out of scope for this pass).

---

## 3. What the validation function actually gates

The function loads a flag from `0xFEBD3E06` and branches on seed/security polarity; this is the
**ADB / seed-auth gate** described (and CAN-corroborated) in `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`
and `VIP_CONTROL_ANALYSIS.txt`. That EEPROM/seed behavior is real and unaffected by this
correction — what is retracted is only the claim that this function was **stubbed in Y177** and
that it drove **SELinux permissive**. The SELinux-permissive question is OS-side (§ Executive
Summary). Treat "EEPROM/seed → ADB gate" and "ramdisk/init → SELinux mode" as **separate**
mechanisms; v1.0 conflated them.

### 3.1 Verdict: does this routine read/branch on a firmware-version value? — **NO** (high confidence)

Full linear disassembly of all ~906 bytes in all three revisions, plus the routine's two
callers-in-context and its three named callees, turns up **no comparison against a
build-number/version constant anywhere**. Every `cmp`/`andi`/branch in the function is one of
four kinds, all enumerated below with addresses (Y181/`0xb67d0` addressing):

1. **Two single-byte security/seed flags, tested for equality to `1`, never for ordering:**
   - `movhi -0x143,r0,r9 ; ld.bu 0x3e06[r9],r9` (`0xb67ec`–`0xb67f0`) → byte at **`0xFEBD3E06`**,
     then `cmp 0x1,r9`. This byte address, and the `movhi -0x143` (→hi16 `0xfebd`) encoding that
     produces it, is **byte-identical across Y175/Y177/Y181** — it is not in either diff list.
   - `mov 0xfebe71e4,r29 ; ld.bu 0x2f[r29],r8` (Y181) → byte at `0xFEBE7213`, then `cmp 0x1,r8`.
     (Y175 reads the equivalent field at `0xFEBE720B` — see §3.2, this is a relocated struct
     base, same `+0x2f` field offset, same `cmp 0x1` test, not a different check.)
   - A companion status byte at a `0xFEBD3E04`-based struct (`r24`), touched via
     `ld.bu`/`st.b` at small fixed offsets (`0xa`, `0xe`, `0xf`, `0x10`, `0x2b`, `0x2c`) — again
     `ld.bu`+`cmp`-against-small-constant, no ordinal test.
2. **An 8-bit request/command code** (`r20`, loaded from `0x3c[sp]` in the prologue), dispatched
   with `cmp 0x1/0x3/0x4/0x5,r20` + `bc`/`bnc`/`be`/`bne` — a `switch(cmd)` over values `0..5`,
   not a version.
3. **A completeness/bitmask check**, at the routine's tail (`0xb6b06`–`0xb6b20`):
   `movhi -0x143,r0,r7 ; ld.w 0x4da0[r7],r7` loads the 32-bit word at **`0xFEBD4DA0`**, then
   `mov 0x7ffff,r13 ; and r13,r7 ; cmp r13,r7 ; setfe r18` — AND the word with mask `0x7FFFF`
   and test **equality** to the same mask. This is the idiom for "are all 19 low bits set"
   (an all-permissions/all-features-enabled test), the opposite shape of a version-floor check
   (which would use an *inequality* compare like `cmp`+`bnc`/`bc` against an ordinal threshold,
   not AND-then-equal against a constant bitmask).
4. **Small enumerated tag values** (`0x1b,0x1c,0x1d,0x1e,0x1f,0x22,0x31,0x10`, etc., loaded via
   `movea <tag>,r0,r6`) passed as arguments into the trace-wrapper calls (`0xecd84`/`0xecdac`,
   see §3.3) and the table-reset helper (`0xaee28`) — these are log/state-phase IDs and reset
   codes, confirmed by walking into those callees (§3.3), not version data.

No instruction in the routine ever loads a 16- or 32-bit value and compares it with `bgt`/`bge`/
`blt`/`ble`-style ordinal logic, and no address touched by the routine (`0xFEBD3E06`,
`0xFEBD3E04`-struct, `0xFEBE71E4`+`0x2f`, `0xFEBD4DA0`, `0xFEBD4D9C`, `0xFEBDA50E`,
`0xFEBD38EA`) decodes as a build-number field in either GM's own version strings (checked
elsewhere in this doc, §6) or in the routine's own access pattern (single bytes, or a bitmask
word tested for all-bits-set, never a multi-byte ordinal). **This finding should propagate to
`UNTRIED_ATTACK_VECTORS.md`, which already states this correctly in its "not a 'version floor'"
line — that line is now RH850-disassembly-confirmed, not just inferred from the byte-diff.**
(Not edited here per instruction — flagged for the operator.)

### 3.2 Return value and callers

The routine returns its status via `r10` (RH850's first return register) and also writes an
output status byte through pointer arguments (`r26`, `r27` — `st.b r0/r9/…,0x0[r26]` /
`[r27]` appear at every exit path, with values `0` = success, `0xa` = a specific error class,
plus tag bytes `0x22`/`0x31` for two other error paths). The shared `return 0` helper at
`entry-4` (see §2 "Callers — corrected") is called once near the tail and its `r10=0` result is
stored into a status-struct field — it supplies a default/success sub-status, it does not gate
entry to the routine. The routine's own external caller(s) were not identified in this pass
(see §2); this does not affect the version-floor verdict, which is intrinsic to the routine's
own comparisons.

### 3.3 The three named callees

- **`0xecd84` / `0xecdac`** — a matched **trace-enter / trace-exit** pair. Each is a thin
  wrapper: `prepare {r28,r29,lp},0x6` → call a lower-level record primitive (`0xf5cb8` for the
  "enter" wrapper, `0xf5e2a` for the "exit" wrapper) with the tag in `r6` → on non-zero
  (failure) return, format and emit a diagnostic via `0xec4be` with a fixed message-ID (`0xd8`
  enter-fail / `0xd9` exit-fail) → `dispose`. This is **instrumentation/state-phase logging**,
  not security logic — confirmed by walking both prologues.
- **`0xb6652`** — a small **input-range classifier/normalizer**: `zxb r6` then range-checks the
  byte against `0xff` (sentinel), `[1,10]` (→ return `input+3`), and `[0xf5,0xfe]`/`[-11,-2]`
  (→ return `input+9`); falls through to `jmp [lp]` otherwise. Its neighbors at `0xb6680` /
  `0xb6690` (also reached from the same call cluster) do simple `cmp`-against-fixed-constant
  capability-bit tests against a small table at `0xFEBD71E0`/`0xFEBD71ED`. All enumerated-value
  logic; no version data.
- **`0xaee28`** — a **table/session-state reset utility**, dispatched by a small integer code in
  `r6` (checked against `0x10`/`0x12`/`0x13`-ish offsets). For the `0x10` case (the one the
  validator invokes), it zeroes a 65-byte array at `0xFEBDA50E` and a 32-entry × 4-byte array at
  `0xFEBD4F20` — the **same** `0xFEBDA50E` table the validator populates elsewhere in its body
  (`mov 0xfebda50e,r15` + byte-copy loop). This is a "clear the session/permission table before
  repopulating (or on error)" helper, called by the validator on both a success path and several
  error paths.

---

## 4. Binary differences summary

| Pair | Bytes different | Note |
|------|-----------------|------|
| Y177 vs Y181 | 549,518 (28.4%) | mostly recompilation address/offset churn, not logic |
| Y175 vs Y177 | 762,492 | same — large shifted regions |
| Y175 vs Y181 | 760,594 | same |

The aligned function-body diffs (§2) are the meaningful signal: the security function is the
**same source recompiled**, not a semantic change, across the full Y175→Y181 span. No
"bypass introduced then closed" event exists at this function; the check has been present and
full continuously from Y175 (Apr 2024) through Y181 (Jun 2025).

---

## 5. EEPROM address references (identical across builds)

| Pattern | Addresses found | Purpose |
|---------|-----------------|---------|
| 0x0440 | 0x248aa, 0x24b26 | Security config (SBI) |
| 0x0A80 | 0x24b9e | Backup SBI |
| 0x0B40 | 0x24c22 | Debug mode flag |

---

## 6. Key strings (identical across builds)

| Address | String |
|---------|--------|
| 0x7c1a | `[AME_DIAG] ICUSB enabled and both key are provisioned.` |
| 0x7cf6 | `[AME_DIAG] ICUSB not enabled.` |
| 0xaf46 | `[PROTOKEY] ICUSB module disabled` |
| 0xaf6a | `[PROTOKEY] ICUSB module enabled` |
| 0x1658e | `[J6_CDD] J6_prv_ProtoKey:Protokey transmitted to SoC, status is %d` |

No `SELinux` / `permissive` / `enforce` strings exist anywhere in the VIP MCU image — another
indication SELinux mode is not decided on the VIP side.

---

## 7. VIP-to-SoC communication path

```
VIP reads EEPROM → PROTOKEY module → J6_CDD module → Serial IPC → SoC
ProtoKey data transmitted via SERIAL_IPC_PROTO_KEY_CHANNEL
```

This IPC path is real and unchanged across builds. Note the ProtoKey communicates seed/auth
state; it does not carry a "set SELinux permissive" instruction (no such string/logic on VIP).

---

## 8. Hardware architecture

### VIP MCU (Renesas RH850)

| Component | Location | Size |
|-----------|----------|------|
| VIP_BOOT | RH850 Internal Flash | ~128KB (byte-identical Y175/Y177/Y181) |
| VIP_APP | RH850 Internal Flash | ~1.9MB |
| Configuration Data | External M24C64 EEPROM | 8KB |

```
RH850 INTERNAL FLASH
├── VIP_BOOT: signature validation, flash routines, recovery
└── VIP_APP:  PROTOKEY · J6_CDD · ICUSB · security validation (FULL in all builds)

EXTERNAL M24C64 EEPROM
  0x0440 Primary SBI · 0x0A80 Backup SBI · 0x0B40 Debug flag · 0x05C0 VIN
  [full map in EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md]
```

---

## 9. Downgrade / upgrade behavior

| Scenario | Result |
|----------|--------|
| Y181 → Y177 full package | **BLOCKED** by GHS hypervisor rollback protection |
| Y181 → Y181 reinstall | Allowed |
| Y181 Android + Y177/Y175 VIP substitution | Unknown (blocked by manifest `.mnf` SHA-256 + `.smd` signature) |

Because the VIP security function is identical across builds, **swapping in an older VIP_APP
would not re-open any SELinux bypass** — there is nothing to revert to. This retires the v1.0
"hybrid package" idea (install Y181, substitute Y177 VIP) as a security bypass: its premise was
the (nonexistent) stub.

---

## Conclusion

The VIP security validation function is **fully implemented and materially identical in Y175,
Y177, and Y181**. GM did not "fix a stub" in Y181; there was no stub. Stock Y177 does not run permissive either
(byte-identical enforcing init); SELinux mode is decided OS-side, never by the VIP or the EEPROM/seed
ADB gate. The
Android-side init scripts and `gm_protokey` binary being identical across versions is consistent
with this: the VIP firmware is not where a SELinux-mode difference lives.

---

## Related documents

- `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` — EEPROM map + the 0xb67d0 validator's real (ADB/seed) behavior
- `VIP_CONTROL_ANALYSIS.txt` — broader EEPROM/board/DPS surface
- `security/KERNEL_CVE_ANALYSIS.txt` (Appendix E.8) — why no stock build (incl. Y177) runs permissive: byte-identical enforcing init
- `../gm_aaos/2024_Silverado_ICE/analysis/Y175_OS_PARTITION_INVESTIGATION_AUG2026.md` — Y175 shipped SELinux/adb posture

---

**Document Version:** 2.0 (three-way, stub finding retracted)
**Last Updated:** 2026-08-25
**Classification:** Security Research
