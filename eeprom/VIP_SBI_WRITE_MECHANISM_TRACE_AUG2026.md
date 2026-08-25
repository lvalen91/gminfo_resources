# VIP SBI write mechanism — full call-chain trace (2026-08-25)

Resolves the open question left by `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`: what actually
writes the SBI EEPROM flag, and what triggers the observed reset-to-secured behavior. Traced by
a dedicated deep firmware RE pass (raw V850 disassembly, `vip_app.bin`/GM part 86331656, Ghidra
project `vip_app_proj`, Ghidra 12.1.3 — 12.1.2 fails to load the project's V850 language
version). Full methodology and scripts referenced at the end.

## 0. Why the caller was never found before

Prior passes concluded `FUN_ram_00091938` (the SBI CalGroup `0x3b` accessor) was "reached only
via an unresolved indirect/table call." **This was a Ghidra auto-analysis gap, not a real
indirect call.** The entire calibration dispatch/reconcile region (`ram:000b9c00-000bb200`) and
the default-restore/setter cluster (`ram:000c6000-000c7400`) are undisassembled "undefined
bytes" in the project — Ghidra created no functions there, so it has no xrefs into
`0x91938` and the decompiler can't see the code at all. Pseudo-disassembling the raw bytes
directly (rather than trusting the existing analysis database) shows `FUN_ram_00091938` is
reached by a **plain direct `jarl`** inside an unrolled switch dispatcher — not an indirect call.

## 1. The real dispatch mechanism: a 106-entry switch, not a pointer table

`FUN_ram_00091938`'s address does not appear as a stored pointer anywhere in the image (full
memory scan, confirmed). It's invoked from **Dispatcher A**, entry `ram:000b9c5e`: allocates a
scratch buffer, reads a CalGroup **ordinal** (0-105, `zxb r6`), and jumps through a 106-entry
`jr` trampoline table at `0xb9c7a`. Each case does `movea <bufoff>,sp,r6; jarl <handler>`.

**SBI case** at `ram:000ba15e`: `movea 0x11c,sp,r6; jarl 0x00091938` (`@0xba162`) — the *only*
reference to `0x91938` in the whole binary. SBI's dispatch **ordinal is `0x45`**, distinct from
its EEPROM CalGroup ID `0x3b`.

## 2. The resolved SBI path is READ-only — no per-cell writer exists

`FUN_ram_00091938` calls the generic getter `FUN_ram_000c8db6(cellID, bufPtr)` per cell
`0x43a-0x447`. Fully disassembled: it looks up per-cell metadata (`0x4fba4 + cellID*0x18`),
reads a type byte, dispatches to one of 9 type handlers, all of which do
`sld.* [ep=<RAM-shadow-bank>+cellOffset], rX; st.* rX, [buffer]` — i.e. **RAM-shadow → caller
buffer, a pure getter.** Its epilogue checks a per-cell validity byte
(`0xfebdbf6a + cellOffset == 0x80`) and returns a status.

**A full-image scan for any code loading cell id `0x440` found exactly one hit: this same
getter call inside `FUN_ram_00091938`.** There is no per-cell SBI *writer* anywhere in the
firmware. The corresponding write-side accessor (`jmp 0xeef90[r12]` @ `ram:000c7294`) exists as
a general mechanism but is **never invoked with the SBI cell IDs**.

## 3. Full call chain to the SBI accessor

```
RTOS event-driven task (~ram:00098700)
  └ tst1 0x2,0xb[sp]; jarl 0xbb0a0            ; runs only when a specific event-flag bit is set
FUN_bb0a0 (ram:000bb0a0) — "reconcile ALL CalGroups"
  ; gated by *(byte)0xfebd3e07==1 && *(byte)0xfebe7721==1
  └ for r29=0..0x69: jarl FUN_baf4a(r29)      ; loops all 106 CalGroups, incl. SBI ordinal 0x45
FUN_baf4a — per-CalGroup validity state machine
  └ jarl FUN_ba8ca (orchestrator)
      ├ jarl 0xb9c5e (Dispatcher A = READ/validate) → jarl 0x91938  (SBI getter)
      └ jarl 0xba2ec / 0xba96c (Dispatchers B/C)     → st.b to 0xfebd3941 / 0xfebd3940
                                                        (per-CalGroup RAM "dirty/valid" bytes)
```

Dispatchers B/C **do not touch EEPROM** — they only set RAM state bytes. So this whole chain is
a **validity monitor**: event-driven (an internal RTOS flag, not a diagnostic message), it reads
and validates every CalGroup including SBI, and records a validity state in RAM. This matches
the observed behavioral signature exactly: no `$2E` write, no unsolicited message, purely
internal.

## 4. What actually writes SBI: bulk restore-to-ROM-defaults

Since no per-cell SBI writer exists, the value can only change via a bulk operation. Found by
scanning for stores into the SBI's RAM-shadow bank (`0xfebdaabe`):

**`FUN_ram_000c6564`** — a "restore ALL calibration defaults into the shadow" loop. Iterates a
cal-descriptor table (`0x68280`, stride `0x16`), and per entry copies the **factory ROM
default** over the RAM shadow (`ld.bu <ROM 0x5xxxx>, r16; sst.b r16, [shadow+cellOffset]`) —
including the SBI cells. This is the only writer of that shadow region in the entire image.

**Caller**: `FUN_ram_000c6564` has exactly one caller — `FUN_ram_000a35dc`, a re-initialization
sequence chaining multiple subsystem-init calls, operating on state at `0xfebe716c` — the same
`0xfebe71xx` security/NvM state pool already documented in `VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`
(seed state at `0xfebe71e0+`).

**Remaining gap**: `FUN_ram_000a35dc` itself is reached by a computed jump whose dispatch-table
base wasn't located (same class of unanalyzed-code obstacle as §0). So the *exact* trigger —
power-on/reset vs. a specific diagnostic session or RoutineControl transition — is not
statically pinned. Everything downstream of it is resolved.

## 5. Corroborating strings (persist layer)

- `[CAL] Retrying calibration Request:%4d`, **`[CAL] EEPROM Write Failure for CalGroup-%d`**
  (11 copies) — confirms a real per-CalGroup shadow→EEPROM writer with retry, downstream of the
  restore-defaults step.
- `[INT_DID] DID41EB NvM ReadError Status:%d`, `[INT_DID] DID4787 NvM ReadError Status:%d` —
  AUTOSAR NvM read-error/CRC status exposed via diagnostic DIDs.

## 6. Best-supported mechanism for the observed SBI reset

This matches standard **AUTOSAR NvM behavior**: on a block re-read/re-validate
(`NvM_ReadAll`-style), a CRC/validity failure triggers "restore ROM defaults" into the RAM
mirror, which the CAL layer then persists back to EEPROM. A tampered SBI is not a validly-CRC'd
calibration value — when an SPS operation causes the VIP's NvM/CAL state machine to re-validate
its blocks, the SBI CalGroup fails, `FUN_ram_000c6564` overwrites it with the factory-secured
default in RAM, and the CAL layer writes it back to EEPROM. **No `$2E` write and no unsolicited
message required — exactly as observed.**

## 7. Reconciling with the empirical dump evidence

Direct hex read of `gm_aaos/2024_Silverado_ICE/hardware/EEPROM/gm_csm/Y181/ADB_enabled.bin`
(2026-08-25, separate check) shows `0x0440-0x0443` and `0x0A80-0x0A83` holding **byte-identical**
`5A FF 5A FF` in a real ADB-enabled unit — directly contradicting the earlier
"zero code references to `0x0A80`" retraction taken at face value. This trace explains why: the
retraction was about a *literal* address reference, which genuinely doesn't exist — but a
paired/mirrored write pattern from a generic, offset-computed accessor (matching this trace's
finding that at least one other CalGroup, `0x400`/`0x420`, is also stored as an identical mirror
pair) would produce exactly this empirical signature without ever containing the literal
constant `0x0A80` in code. **Working synthesis**: the mirror-pair match is very plausibly *part
of the NvM CRC/validity check itself* — two copies must agree, and a mismatch (or an invalid
CRC) is what triggers the restore-defaults path in §4. This is inference, not confirmed by this
trace (which resolved the write mechanism, not the redundancy/CRC scheme specifically) — worth a
follow-up pass if pursued further.

## 8. Practical implication for a physical SPI EEPROM edit

**A raw SPI write to `0x0440`/`0x0441` (or the mirrored pair) is not guaranteed to persist.** If
this trace's mechanism is right, the ECU's own NvM/CAL layer re-validates these blocks on some
internal trigger (possibly every power-on/init, given `FUN_ram_000a35dc` is a re-init sequence)
and will overwrite an invalid/mismatched value with the factory-secured default automatically —
the same mechanism that (per this research) resets it after an SPS operation would just as
plausibly reset it again after the next power cycle following a manual SPI write, unless the
written value also satisfies whatever validity/CRC check gates the restore path. This wasn't
confirmed either way — the exact validity check wasn't reached — but it's the single biggest risk
factor for anyone planning a physical EEPROM modification: **the write may appear to succeed at
the SPI layer and then silently revert on the ECU's next boot or calibration cycle.**

## 9. Confidence and remaining open thread

**High, verified by disassembly**: no pointer table exists; `0x91938` reached by direct `jarl`
from switch-Dispatcher A; the resolved path is read-only through getter `c8db6`; no per-cell SBI
writer exists anywhere; the only writer of the SBI shadow region is the bulk restore-defaults
routine `FUN_ram_000c6564`, reachable from re-init handler `FUN_ram_000a35dc`.

**Medium, inferred**: that the specific reset is produced by a CRC-fail→restore-defaults path
(strongly implied by AUTOSAR NvM convention + the corroborating strings + restore-defaults being
the only writer of that memory, but the exact "if CRC bad then call c6564" branch sits in
unanalyzed bytes and wasn't decompiled).

**Open**: `FUN_ram_000a35dc`'s exact entry condition (power-on vs. session/RoutineControl
transition) — reached via a computed jump whose dispatch-table base wasn't located. This is the
one remaining step to name the precise UDS/session event, if pursued further.

## Methodology / tooling

Ghidra 12.1.3 required (12.1.2 fails to load `vip_app_proj`'s V850 language version). Decompiler
fails on these specific functions in this project (same issue noted in
`VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`) — all analysis here is from raw V850 disassembly, not
decompiled C. Scripts (not preserved in this repo, scratch): `ScanAddr.java` (V850-aware
movhi/movea + branch-target scan across raw bytes including undefined regions — the key
technique that unblocked this, since it doesn't rely on Ghidra's existing function boundaries),
`Dump.java` (range pseudo-disassembler), `SBIScan.java` (memory pointer-value scan), `ScanImm.java`
(immediate/shadow-bank scan).
