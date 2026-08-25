# VIP EEPROM Flag Scope Analysis — Aug 2026

**Date:** 2026-08-24
**Binary analyzed:** `vip_app.bin` (VIP_APP, GM part 86331656, Y181), Ghidra project
`vip_app_proj` at `/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/analysis/extracted_artifacts/ghidra_projects/`.
Also checked `vip_boot.bin` (`vip_boot_proj`) where noted.
**Method:** headless Ghidra 12.1.3 (`analyzeHeadless ... -noanalysis`, i.e. relying on the
project's pre-existing analysis, no re-analysis performed), Java `GhidraScript`s that (a) scan
every instruction in the program for scalar/immediate operands matching candidate EEPROM
offsets, and (b) batch-decompile functions of interest with `DecompInterface` to plain C
pseudocode, searched textually. Raw scripts are not preserved in this repo (scratch); the
addresses and decompiled snippets below are quoted directly from that tooling's output.
**Confidence markers:** `[C]` = confirmed from decompiled code/disassembly quoted here, `[I]`
= inferred from structural/naming evidence, `[O]` = open, not resolved by this pass.

---

## 0. Headline verdict

**The SBI bypass (`0x0441`/`0x0A81` → `0xFF`) is backed by a real, dedicated 14-byte EEPROM
field-group at `0x043A–0x0447` that is architecturally *private* to that one field-group
handler function — no code path was found in `vip_app.bin` where that same handler, or the
same underlying generic EEPROM-cell accessor call for cell `0x440`/`0x441`, feeds any *other*
CalGroup or security decision. `[C]` for the block's existence and isolation; `[O]` for what
consumes the block's output, because the handler's caller is reached only through an unresolved
indirect/table call (see §2).**

**Separately, and just as important: none of the four undocumented candidate offsets
(`0x04A0`, `0x04C0`, `0x0A40`, `0x0BE0`) nor the "backup SBI" pair (`0x0A80`/`0x0A81`) could be
shown to be read by *any* code in `vip_app.bin` via the one confirmed EEPROM-cell access
mechanism, and none of the eight target addresses appear as a literal instruction operand
anywhere in `vip_app.bin` or `vip_boot.bin` except for one of the four (`0x04C0`, confirmed
real — see §3) and two clear false positives (see §4). This is a solidly reproducible negative
result, not a guess: it comes from an exhaustive scan of every instruction's immediate operands
in both binaries, cross-checked against a second, independent discovery path (every literal
argument ever passed to the one proven EEPROM-cell accessor function, 1,050 distinct calls).**

**On the operator's core question — does flipping `0x0441`/`0x0A81` open doors beyond ADB — this
pass did not find evidence that it does, but it also could not fully close the question, because
the caller of the SBI's own field-group handler (what actually *consumes* the SBI data byte) is
reached only via an indirect call this static pass did not resolve. See §6 for the honest gap.**

---

## 1. Architecture discovered: EEPROM access is a generic "CalGroup cell" accessor, not raw I²C reads in-line

The single most useful structural finding: `vip_app.bin` does **not** read EEPROM offsets with
inline I²C calls scattered through the code. Instead there is one generic dispatcher:

```
FUN_ram_000c8db6 @ ram:000c8db6
void FUN_ram_000c8db6(uint param_1)
{
  (*(code *)((uint)*(byte *)((param_1 & 0xffff) * 0x18 + 0x4fbae) * 4 + 0xf0ae2))();
  return;
}
```

`param_1` is a 16-bit **cell ID**. The function looks up a type/handler byte from a metadata
table at RAM `0x4fbae` (stride `0x18` = 24 bytes per cell) and jumps through a second table at
`0xf0ae2` (stride 4) into a type-specific accessor. This is a classic auto-generated
signal/parameter table (Vector-CDD-style codegen), and it is used **everywhere**: across the
whole binary there are **1,301 call sites** to this one function, spread across **170 distinct
caller functions**, using **1,050 distinct literal cell-ID values** ranging from `0x1e` to
`0xe20`.

A paired function, `FUN_ram_000c8f10(uint calGroupId)`, is called at the top of essentially every
caller — it checks `DAT_ram_febd3db8` (a "programming session active" flag) and, if set, calls a
non-returning trap. This is a **CalGroup-ID guard**: each of the 170 caller functions represents
one "CalGroup" — a fixed, compile-time-unrolled sequence of `FUN_ram_000c8db6(cellID, bufOffset)`
calls that pack/unpack one CalGroup's EEPROM fields into/out of a small local buffer. This
directly matches the corpus's own "CalGroup" terminology (`[CAL] EEPROM Write Failure for
CalGroup-%d` strings, 15 instances, confirmed present).

**Working hypothesis, evidence-backed:** cell ID numerically equals the EEPROM byte offset. This
is supported by the SBI block below, whose cell-ID range (`0x43a`–`0x447`) exactly straddles the
well-established real EEPROM address `0x0440`/`0x0441`.

---

## 2. The Primary SBI block — confirmed, isolated, caller not resolved

```
FUN_ram_00091938 @ ram:00091938
char FUN_ram_00091938(int param_1)
{
  thunk_FUN_ram_000edd96();              // disable IRQ (critical section enter)
  FUN_ram_000c8f10(0x3b);                // CalGroup guard, group ID 0x3b (59)
  FUN_ram_000c8db6(0x43a,param_1);
  FUN_ram_000c8db6(0x43b,param_1 + 1);
  FUN_ram_000c8db6(0x43c,param_1 + 2);
  FUN_ram_000c8db6(0x43d,param_1 + 4);
  FUN_ram_000c8db6(0x43e,param_1 + 6);
  FUN_ram_000c8db6(0x43f,param_1 + 7);
  FUN_ram_000c8db6(0x440,param_1 + 8);   // <-- Primary SBI marker/data byte
  FUN_ram_000c8db6(0x443,param_1 + 9);
  FUN_ram_000c8db6(0x441,param_1 + 10);  // <-- Primary SBI data byte (confirmed real offset)
  FUN_ram_000c8db6(0x442,param_1 + 0xb);
  FUN_ram_000c8db6(0x444,param_1 + 0xc);
  FUN_ram_000c8db6(0x445,param_1 + 0xd);
  FUN_ram_000c8db6(0x446,param_1 + 0xe);
  FUN_ram_000c8db6(0x447,param_1 + 0xf);
  if ((DAT_ram_febd3b8b & 0x20) == 0) { DAT_ram_febd3b8b = DAT_ram_febd3b8b & 0xef; }
  else { DAT_ram_febd3b8b = DAT_ram_febd3b8b | 0x10; }
  thunk_FUN_ram_000eddb6();              // re-enable IRQ (critical section exit)
  return ((DAT_ram_febd3b00 & 4) != 0) * '@';
}
```

Findings `[C]`:
- CellIDs `0x43a`–`0x447` are a contiguous 14-byte block = **CalGroup `0x3b` (59)**, and this is
  the *only* function in the entire binary that touches cell `0x440` or `0x441` (confirmed by
  the exhaustive literal-operand scan across all instructions, and independently by grepping all
  1,301 accessor call sites for these exact values — one hit each, both inside this one
  function).
- The byte ordering into the local buffer is **not** sequential with the EEPROM offsets
  (`0x440`→buf+8, `0x441`→buf+10, `0x442`→buf+0xb, `0x443`→buf+9 — deliberately interleaved).
  This is consistent with the corpus's existing observation that the 4-byte marker pattern
  around the SBI is "CalGroup-assigned at runtime" — the marker/data bytes are scrambled between
  RAM-buffer layout and EEPROM layout, presumably to make raw EEPROM diffing harder to interpret
  without exactly this table.
- The function is a pure pack/unpack routine — it does not itself branch on the SBI value. It
  returns a bit derived from an unrelated status byte (`DAT_ram_febd3b00 & 4`), which looks like
  a generic "cal-write-ok" status shared by the CalGroup framework, not something specific to
  security.

**Gap `[O]`:** `FUN_ram_00091938` has **zero statically-resolved callers** (Ghidra's call graph
shows none). Given the architecture (170 handler functions, almost certainly invoked from one
generic "dispatch CalGroup N" routine via a jump/pointer table keyed by the same small integer
ID seen passed to `FUN_ram_000c8f10`, e.g. `0x3b` here), the actual caller — and therefore the
code that reads the packed buffer back out and decides what to do with the SBI data byte
(presumably the PROTOKEY/seed logic) — was **not reached by this static pass**. This is the
single biggest unresolved link in the whole investigation: I can show the SBI's storage is
structurally isolated from other CalGroups at the accessor level, but I could not trace forward
from "the buffer FUN_ram_00091938 fills" to "the function(s) that consume it," so I cannot
directly confirm or rule out a second consumer of that same buffer.

---

## 3. `0x04C0` is real and independently confirmed — but its consumer is equally unresolved

```
FUN_ram_00091f82 @ ram:00091f82
char FUN_ram_00091f82(int param_1)
{
  thunk_FUN_ram_000edd96();
  FUN_ram_000c8f10(0x44);                // CalGroup guard, group ID 0x44 (68) -- DIFFERENT group than SBI's 0x3b
  FUN_ram_000c8db6(0x4b8,param_1);
  FUN_ram_000c8db6(0x4b9,param_1 + 1);
  FUN_ram_000c8db6(0x4ba,param_1 + 2);
  FUN_ram_000c8db6(0x4bb,param_1 + 4);
  FUN_ram_000c8db6(0x4bc,param_1 + 6);
  FUN_ram_000c8db6(0x4bd,param_1 + 7);
  FUN_ram_000c8db6(0x4be,param_1 + 8);
  FUN_ram_000c8db6(0x4c1,param_1 + 9);
  FUN_ram_000c8db6(0x4bf,param_1 + 10);
  FUN_ram_000c8db6(0x4c0,param_1 + 0xb); // <-- one of the 4 undocumented candidates, CONFIRMED REAL
  FUN_ram_000c8db6(0x4c2,param_1 + 0xc);
  FUN_ram_000c8db6(0x4c3,param_1 + 0xd);
  FUN_ram_000c8db6(0x4c4,param_1 + 0xe);
  FUN_ram_000c8db6(0x4c5,param_1 + 0xf);
  if ((DAT_ram_febd3b8d & 8) == 0) { DAT_ram_febd3b8d = DAT_ram_febd3b8d & 0xfb; }
  else { DAT_ram_febd3b8d = DAT_ram_febd3b8d | 4; }
  thunk_FUN_ram_000eddb6();
  return ((DAT_ram_febd3b01 & 2) != 0) * '@';
}
```

Findings `[C]`:
- `0x04C0` is genuinely referenced by code, structurally identical in form to the SBI block
  (same 14-byte marker/data pattern, same interleaved buffer layout, same critical-section
  wrapper) but under a **different CalGroup ID (`0x44` vs `0x3b`)** and a **different status byte**
  (`DAT_ram_febd3b8d`/`DAT_ram_febd3b01` vs `DAT_ram_febd3b8b`/`DAT_ram_febd3b00`). This is strong
  evidence `0x04C0` is a distinct, independently-administered flag/CalGroup from the SBI, not an
  alias or shared structure.
- Like the SBI handler, this function also has **zero statically-resolved callers** — same gap.
  I cannot say what `0x04C0` gates. The corpus's "near `[IPC_S]` strings" framing for this
  address looks unrelated to what I actually found: the `[IPC_S]` strings (HDLC/serial IPC
  transport logging — dozens of them, all confirmed present) live in a completely different part
  of the binary (`ram:0001adfe`–`0001be06`) from the CalGroup `0x44` handler (`ram:00091f82`);
  I found no code link between them. Given the prior provenance audit already flagged the
  `[IPC_S]`-proximity "ref count" claims for this region as UNSUPPORTED, I'd treat the semantic
  link to `[IPC_S]` as unconfirmed/likely coincidental string-address proximity, not a functional
  one.

**Verdict for `0x04C0`: real and confirmed distinct from SBI `[C]`; what it controls: unknown
`[O]`.**

---

## 4. `0x04A0` — the one apparent hit is a false positive

The exhaustive full-instruction scalar scan found exactly one hit for `0x4a0` as an absolute
address, plus one more inside a large unrelated function as a struct-relative store offset:

```
ram:00074ec2  ld.hu 0x4a0[r10],r0     ; inside FUN_ram_00074d56
ram:000e2030  st.b r10,0x4a0[r29]     ; inside FUN_ram_000ba2ec (large function, offset is a
                                        local-struct field, not an absolute address — r29 is a
                                        frame/struct-base register here, confirmed by the
                                        companion hit `st.b r12,0x440[r29]` in the same function,
                                        which is NOT the SBI either, same reasoning)
```

`FUN_ram_00074d56` was decompiled in full. Its first parameter byte is checked against a small
set `{0,1,2,0x2f}` and the function goes on to build/dispatch what looks like a UDS-style
service-record structure (fixed 8-byte header copied from a per-caller constant, then
type/ID/length fields) — it is a **message/service dispatcher unrelated to EEPROM addressing**;
`0x4a0[r10]` is a load from an offset *within that local record*, not the absolute EEPROM
address `0x04A0`. One traced caller, `FUN_ram_000755a8`, builds a 14-byte local record containing
bytes `0x80`/`0x81` (not `0xA80`/`0xA81` — different, smaller values, most likely a 16-bit UDS
DID or similar), which is circumstantially close to "0xA80/0xA81" in digits but is not those
EEPROM addresses; I flag this explicitly because it would be an easy false lead to repeat.

**Verdict for `0x04A0`: no genuine EEPROM-offset reference found anywhere in `vip_app.bin`; the
one candidate hit is a false positive from an unrelated struct-relative addressing mode `[C]`.**

---

## 5. `0x0A40`, `0x0A80`/`0x0A81` (backup SBI), `0x0BE0` — none found, with real neighboring blocks as cross-check

Two independent search methods were used and agree:

1. **Exhaustive instruction scan** (every operand of every instruction in `vip_app.bin`, and
   separately in `vip_boot.bin`) for the literal values `0x0A40`, `0x0A80`, `0x0A81`, `0x0BE0`:
   **zero hits** in either binary.
2. **Every literal cell-ID ever passed to the confirmed generic accessor** `FUN_ram_000c8db6`
   (1,301 call sites / 1,050 distinct values, spanning `0x1e`–`0xe20`): **none of the four values
   appear.**

To make sure this isn't just "the 0xa00–0xc00 region is unused," here are the **real, confirmed**
CalGroup blocks found flanking each gap — proving the surrounding EEPROM space *is* actively used
by code, just never at exactly these four offsets:

| Region | Real cell IDs found (CalGroup) | Gap to target |
|---|---|---|
| below `0x0A40` | `0xa26` (single-byte CalGroup, `FUN_ram_00093cd0`) | next real cell after this is `0xa5e` — `0xa40` sits in an unused gap between them |
| around `0x0A80`/`0x0A81` | `0xa5e` (single-byte) ... `0xabd–0xac1` (5-byte block, **CalGroup `0x9b`**, `FUN_ram_00093e42`) | `0xa80`/`0xa81` fall in the gap between `0xa5e` and `0xabd` — not part of either block |
| around `0x0BE0` | `0xaf7–0xb00`, `0xb40–0xb44`, `0xb5c`, `0xb71–0xb74`, `0xbdd` (several small blocks) | `0xbe0` is 3 bytes past the last real cell (`0xbdd`) with nothing after it up to `0xc00` |

Example of one of these real, confirmed neighboring blocks (for cross-check reproducibility):

```
FUN_ram_00093e42 @ ram:00093e42
char FUN_ram_00093e42(int param_1)
{
  thunk_FUN_ram_000edd96();
  FUN_ram_000c8f10(0x9b);
  FUN_ram_000c8db6(0xabd,param_1 + 6);
  FUN_ram_000c8db6(0xabe,param_1 + 4);
  FUN_ram_000c8db6(0xabf,param_1 + 7);
  FUN_ram_000c8db6(0xac0,param_1);
  FUN_ram_000c8db6(0xac1,param_1 + 2);
  ...
}
```

**Verdict: in `vip_app.bin` as analyzed, `0x0A40`, `0x0A80`, `0x0A81`, and `0x0BE0` are not read
or written by any code reachable through the one confirmed EEPROM-cell access mechanism, and do
not appear as literal addresses anywhere else in the instruction stream of either `vip_app.bin`
or `vip_boot.bin` `[C]`.** This directly contradicts treating `0x0A80`/`0x0A81` as an
app-firmware-checked "backup SBI" in *this* build via *this* mechanism. Possible explanations,
none confirmed by this pass: (a) the backup SBI is validated by a different, non-code-generated
mechanism this scan can't see (e.g. a bulk/page I²C read into a RAM shadow struct with a
runtime-computed, not literal, offset — plausible but not found); (b) it's checked by a firmware
component not analyzed here (e.g. a different VIP module, or an entirely separate ASIC/CDD not
in `vip_app.bin`/`vip_boot.bin`); (c) it is genuinely dead/unused in this specific build. I did
not have evidence to pick between these `[O]`.

---

## 6. Seed/PROTOKEY subsystem — real evidence of a *multi-slot* seed cache, but no code-level link established to the SBI

`strings` on the raw firmware part (`86331656`, matching `vip_app.bin`) turned up a rich, explicit
PROTOKEY/seed vocabulary `[C]` (all present verbatim):

```
[PROTOKEY] No Seed %d received or cached
[PROTOKEY] Seed %d taken from GMLAN
[PROTOKEY] Seed %d taken from cache
[PROTOKEY] In GetSeed for Seed %d release failed for Bis_Seed_Cache_Lock
[PROTOKEY] Cache Seed %d failed checksum calculation, zeroing cache
[PROTOKEY] In GetSeed for Seed %d lock of Bis_Seed_Cache_Lock failed with code %d
[PROTOKEY] Receives invalid seed [%d] from BCM
[PROTOKEY] Updated cache for seed %d
[PROTOKEY] Bis_Seed_Cache_Lock release failed for seed %d update
[PROTOKEY] Bis_Seed_Cache_Lock lock for seed %d update failed with code %d
[PROTOKEY] ICUSB module enabled / disabled
[OTA_DIAG] Get Seed request failed / successful
[OTA_DIAG] Invalid Challenge length
[OTA_DIAG] Invalid subfunction received with the security Access request
[J6_CDD] J6_prv_ProtoKey:Protokey transmit to SoC Failed. SERIAL_IPC_PROTO_KEY_CHANNEL not available
[J6_CDD]  unknown security Access request received, hence not processed
```

The **`%d` seed-number parameter** on nearly every one of these strings (`GetSeed for Seed %d`,
`seed %d update`, `Cache Seed %d`, `Bis_Seed_Cache_Lock ... for seed %d`) is real, direct evidence
`[C]` that the PROTOKEY GetSeed/seed-cache mechanism is **explicitly parameterized by a numeric
seed/slot ID** — i.e. this is a multi-slot cache serving more than one seed context, not a single
hardcoded ADB-only seed. This is consistent with (and independently corroborates, at the
strings level) the corpus's separate claim that VIP/Ethernet/Notification SecurityAccess tiers
share a `$27` seed/key mechanism.

**What I could not do:** trace this to actual code. `getReferencesTo()` on each of these string
addresses returned **zero** cross-references, and a fallback scan of every instruction's resolved
operand references also found zero. This is not itself suspicious — the one function I *could*
fully trace end-to-end (`FUN_ram_000ecb08`/`FUN_ram_000ecb30`, §7 below) shows this firmware's
logger is **ID-indexed, not string-pointer-indexed** (`thunk_FUN_ram_000f2406(0xd8, ...)` — a
small integer, not the string's address, is what's passed at the call site; the string is looked
up later from that integer ID in a separate table I did not reverse). That means pivoting from
these PROTOKEY/Seed strings to their call sites requires reversing that log-ID table, which this
pass did not do. **So: the "multiple seed slots" finding is real and directly evidenced at the
strings level, but I have no decompiled code linking the SBI CalGroup (`0x3b`) to the seed-cache
mechanism, in either direction. This is the single most important open item for follow-up
work.**

---

## 7. Correction to prior corpus: `0xecd84` is a generic RTOS mutex primitive, not a security-validation function

The task brief flagged `0xecd84` as the one address the provenance audit considered
independently verified, with an existing decompile at
`.../out_vip_app/f_000ecd84_FUN_000ecd84.c`:

```c
uint FUN_000ecd84(undefined4 param_1)
{
  uint uVar1;
  undefined4 local_24 [6];
  uVar1 = FUN_000f5cb8();
  if (uVar1 != 0) {
    local_24[0] = param_1;
    thunk_FUN_000f2682(0xd8,uVar1,local_24);
  }
  return uVar1 & 0xff;
}
```

I found the **exact same pattern**, same constant `0xd8`, at a second address in the current
`vip_app.bin` build (`FUN_ram_000ecb08`), and its paired counterpart using constant `0xd9`
(`FUN_ram_000ecb30`), called as an acquire/release pair around a critical section:

```c
FUN_ram_000ecb08(uint param_1)  // acquire; logs 0xd8 on failure
{ uVar1 = FUN_ram_000f5a3c(); if (uVar1 != 0) thunk_FUN_ram_000f2406(0xd8,uVar1,local_24); return uVar1 & 0xff; }

FUN_ram_000ecb30(uint param_1)  // release; logs 0xd9 on failure
{ uVar1 = FUN_ram_000f5bae(); if (uVar1 != 0) thunk_FUN_ram_000f2406(0xd9,uVar1,local_24); return uVar1 & 0xff; }
```

Both take a small integer (`0x10` in the caller below, `0x12` elsewhere) that looks like a
**mutex/semaphore ID**, not a seed or ECU ID. The concrete caller I traced,
`FUN_ram_000a6524`, uses this lock/unlock pair to guard a completely unrelated subsystem — an
**audio amplifier MUTE-event state machine** (called from `FUN_ram_000543fc`, whose sibling
string constant is literally `s__EXT_DID__Amp_manager_MUTE_Event`):

```c
FUN_ram_000a6524(uint param_1, byte param_2)
{
  ...
  FUN_ram_000ecb08(0x10);   // lock mutex 0x10
  ... /* mutate amp-mute state flags */ ...
  FUN_ram_000ecb30(0x10);   // unlock mutex 0x10
  ...
}
```

**Correction: `0xecd84` (and its sibling instances) is a generic RTOS mutex acquire wrapper,
reused across unrelated subsystems (confirmed used by audio-amp-mute logic here) — it is not
part of a seed/PROTOKEY/security validation chain by itself `[C]`.** Its prior appearance next
to a supposed "VIP security validation chain" in the corpus is best explained by it simply being
a common utility function that many things call, including — plausibly, but *unconfirmed here* —
security code elsewhere. I did not find, and did not have budget to find, the actual PROTOKEY/
seed function(s) that call it. I did **not** attempt to re-derive or verify `0xb67d0`/`0xb6652`/
`0xaee28`; per the provenance audit's own finding, treat those as still unverified — nothing in
this pass changes that.

---

## 8. `vip_boot.bin` check

Ran the same exhaustive instruction scan against `vip_boot_proj` / `vip_boot.bin` for all 8
target addresses: only 2 raw hits, both `st.w r2,0x440[ep]` — an element-pointer-relative local
variable store (a stack/frame offset, same false-positive pattern as §4), not an EEPROM
reference. No `SEED`/`PROTOKEY`/`ICUSB`/`SBI`-related strings were found as Ghidra-typed data in
this project either. **No evidence any of the 8 target addresses, or the seed/SBI logic
generally, live in `vip_boot.bin` `[C]` (for the negative instruction-scan result) — consistent
with the SBI/PROTOKEY logic being entirely an app-side (not bootloader-side) concern, though this
is not a strong claim since `vip_boot.bin` is a much smaller image and boot-time code may use
different addressing/compilation that this scan handles less well.**

---

## 9. Summary map

| EEPROM offset | Real code reference found? | What it maps to | Confidence |
|---|---|---|---|
| `0x0440` (Primary SBI marker) | Yes — `FUN_ram_00091938`, CalGroup `0x3b`, cells `0x43a–0x447` | Packed into/out of a local buffer by a dedicated CalGroup handler; consumer function not reached (indirect call) | `[C]` block exists / `[O]` consumer |
| `0x0441` (Primary SBI data byte) | Yes — same function/block as `0x0440` | Same as above | `[C]`/`[O]` |
| `0x04A0` | No genuine hit; one false positive (struct-relative offset in an unrelated UDS-like dispatcher) | Not established | `[C]` negative |
| `0x04C0` | Yes — `FUN_ram_00091f82`, CalGroup `0x44`, cells `0x4b8–0x4c5`, structurally parallel to but administratively separate from the SBI block | Real, distinct flag/CalGroup; semantic meaning unknown, consumer not reached | `[C]` real / `[O]` meaning |
| `0x0A40` | No hit in either binary; real neighboring blocks (`0xa26`, `0xa5e`) confirm the region isn't dead in general | Not established | `[C]` negative |
| `0x0A80` (Backup SBI marker) | No hit in either binary; real neighboring block `0xabd–0xac1` (CalGroup `0x9b`) confirms the region isn't dead in general | Not established via this mechanism | `[C]` negative |
| `0x0A81` (Backup SBI data byte) | No hit in either binary | Not established via this mechanism | `[C]` negative |
| `0x0BE0` | No hit in either binary; real neighboring blocks (`0xaf7–0xb00`, `0xb40–0xb44`, `0xb5c`, `0xb71–0xb74`, `0xbdd`) confirm the region isn't dead in general | Not established | `[C]` negative |

---

## 10. Answer to the operator's core question

**Is the SBI bypass ADB-only, or does it open other doors?**

This pass did **not find evidence that it opens other doors**, but it also could **not fully
rule that out**, and the reasons are specific and worth stating plainly rather than rounding to
"probably fine":

- The Primary SBI's own storage is structurally **isolated** at the CalGroup/accessor level —
  no other CalGroup shares cells `0x43a–0x447`, and no other code in the binary references
  cell `0x440`/`0x441` `[C]`. That's real evidence *against* a shared-storage mechanism linking
  SBI to something else.
- But the function that actually *reads back* the SBI buffer and makes a decision from it (the
  PROTOKEY/seed logic) was **not reached** by this pass — its caller is invoked indirectly, not
  through a statically-resolvable call, so I cannot show what that decision function does with
  the value, nor whether it's also consulted by other privilege tiers.
- Separately, strings-level evidence **does** show the PROTOKEY seed-cache is a **multi-slot,
  numbered mechanism** (`Seed %d`, `Bis_Seed_Cache_Lock ... for seed %d`), which is exactly the
  shape you'd expect if one seed-generation code path served multiple SecurityAccess levels —
  but I have no code-level link between that mechanism and the SBI CalGroup, so this is
  suggestive, not proof.
- The specific worry that a *different*, undocumented EEPROM flag (`0x04A0`/`0x04C0`/`0x0A40`/
  `0x0BE0`) governs the calibration/diagnostic `$27` gate the way `0x0440` governs ADB is **not
  supported** by this pass for three of the four candidates (no code reference found at all), and
  for the fourth (`0x04C0`) is real but administratively separate from the SBI's CalGroup, with
  its actual function unknown.

**Practical recommendation for the operator:** the highest-value next step is resolving the
indirect call that reaches `FUN_ram_00091938` (SBI, `ram:00091938`) and `FUN_ram_00091f82`
(`0x04C0`, `ram:00091f82`) — almost certainly a jump table keyed by the same small CalGroup-ID
values (`0x3b`, `0x44`, `0x9b`, ...) already seen passed to `FUN_ram_000c8f10` at the top of all
170 handler functions. Finding that dispatch table (likely a straightforward data-table scan
once the jump-table base is located near the accessor's own tables at `0x4fbae`/`0xf0ae2`) would
directly answer both (a) what reads the SBI buffer, and (b) whether `0x04C0`'s CalGroup `0x44`
is a calibration/diagnostic security level, closing the operator's open question with actual
code rather than inference.
