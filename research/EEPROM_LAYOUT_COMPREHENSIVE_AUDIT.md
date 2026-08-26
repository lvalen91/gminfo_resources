# EEPROM Layout Audit — Complete Inventory & SBI/Cal-Security Deep-Dive

**Date:** 2026-08-17  
**Source:** `eeprom/EEPROM_Analysis_Report.md` (Dec 2025), `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (Jan–Feb 2026), `T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md`, `S27_SOC_VALIDATION_BENCH_TEST.md`  
**Scope:** ST M24C64 8KB EEPROM; VIP (Renesas RH850) + SoC (Android IVI)

---

## 0. CODE AUDIT (2026-08-25) — most of the security map below is NOT code-backed

A ground-truth pass disassembled the Y175 VIP_APP (`85759599`) and grep-audited the SoC-side
binaries. It **falsifies or downgrades most of §1/§2.1's "security" claims.** Read this before
trusting any offset below.

**Verified structural facts (high confidence):**
- **VIP_APP does NOT perform the raw I²C read of the M24C64.** It has zero `RH850-IIC` strings;
  VIP_BOOT (`85056831`, byte-identical across builds) has them. **The physical EEPROM read and
  the EEPROM→RAM-shadow mapping live in VIP_BOOT, which has NOT yet been disassembled.** VIP_APP
  only consumes a RAM shadow left by boot.
- VIP_APP's calibration accessor is a **table-driven "CalGroup" dispatcher** `FUN_000c8f6a(offset,dest)`
  at `0xc8f6a` → 24-byte descriptor table at `0x4fb96` → handler pointer table at `0xf0a1a`.
  **This table is the real offset→field map and has not been decoded yet.** A scan for *literal*
  offset immediates cannot see computed/table-driven accesses, so "0 code hits" below is
  suggestive, not conclusive.
- The `0xFEBD4DA0 & 0x7FFFF` word is the **UDS `$27` SecurityAccess SendKey handler**
  (`FUN_000b6708`): 19 = the number of diagnostic security *levels* (2–20); each bit = "level N
  unlocked **this session**." It is a **session unlock accumulator, NOT 19 EEPROM-stored permission
  bits.** All 19 levels gate on one shared byte `DAT_febd3e06`, whose only VIP_APP writers set it
  to hardcoded 1/0 — **no VIP_APP code links it to an EEPROM read** (that link, if real, is in VIP_BOOT).

**CONFIRMED hallucinations / fabrications (retract on sight):**
- **"[IPC_S] = IPC Security"** (basis for calling 0x04A0/0x04C0 "IPC Security Config"): FALSE.
  `[IPC_S]` is the **IPC *Serial* transport log tag** (HDLC framing: `IFRAME Rx`, `UFRAME RESET`,
  `HDLC: CRC Failed`, `IPC-Version`). Nothing to do with security.
- **The "xref" counts** (0x0A00 "871 refs", 0x0B00 "311 refs", 0x04A0 "17", 0x04C0 "11",
  0x0A40 "28", 0x0BE0 "24") are **not reproducible** — actual instruction-level references number
  2–3. These counts are grep/byte-pattern noise, not semantic xrefs, and are not evidence of anything.
- **"0x0440 SBI — disasm-confirmed"**: the "disasm-confirmed" label is FALSE. The only code sites
  touching literal `0x440` show ordinary 14-byte calibration-group handling with no `==0xFF` bypass test.

**Per-offset verdict (VIP_APP literal-immediate evidence):** 0x0440 UNSUPPORTED-as-claimed;
0x0A80/0x0A40/0x0AC0/0x0BE0/0x1A00 ZERO code refs (likely fabricated); 0x04A0/0x04C0 ordinary
calibration bytes; 0x0B40 is 1/5 of a scrambled composite value, not a boolean flag.

**⚠ Consequence for bench testing:** the specific "flip 0x0440 / 0x0A80" SBI targets are **NOT
code-verified**. The true SBI byte(s) must be recovered from **VIP_BOOT disassembly + the CalGroup
descriptor table decode** before a bench flip has a known target. Until then, the offsets below are
historical hypotheses, not confirmed addresses.

**Caveats on the first audit:** it analyzed VIP_APP only, reused the older `V850` project, and its
literal-immediate method is blind to table-driven access. Pass 2 (below) addressed those.

### §0.1 CODE AUDIT PASS 2 (2026-08-26) — RH850, VIP_BOOT + CalGroup decoded. No EEPROM→security link found.

Two fresh RH850-decoder passes (proper `RH850:LE:32`, not V850):

- **CalGroup accessor fully decoded (VIP_APP).** Descriptor base is **`0x4fb8c`** (24-byte stride;
  `0x4fb96` was base+0xA, the type byte). `0xf0a1a` is a **computed jump**, not a pointer table.
  VIP_APP's *entire live* CalItem set is `0xB4–0xB5`, `0xF9–0x103`, `0xDC1–0xDC9` (20/20 call sites,
  exhaustive) — handlers are width-tags, `divqu` value-scaling, list-node reassembly, marker-rotation
  copy: **ordinary calibration plumbing.** **None of the 8 flagged security offsets are in the live
  set.** The `$27` validator (`FUN_000b67d0`) and the CalGroup accessor are **structurally
  independent** (direct negative xref — neither calls the other). *(Caveat: `calItemId == EEPROM byte
  offset` is unproven — that needs VIP_BOOT.)*
- **VIP_BOOT (`85056831`) disassembled under RH850.** Its actual role is a **signed application-image
  flash updater** ("Starting boot updater application", signed-header/message-digest/Harman-checksum
  validation, PSI/NBID over HDLC/IPC) — a different domain from calibration/security. **No I²C /
  M24C64 read routine found:** the `RH850-IIC` string is inert Smart-Configurator BSP boilerplate with
  **zero code references** (checked via 100%-coverage absolute-address + pointer scans). **`0xFEBD3E06`
  and `0xFEBD4DA0` do not appear anywhere in the 1.9 MB image** (100% byte-scan of both address-
  materialization idioms). No EEPROM/NVM/SBI/seed/security strings exist in it at all.
  ⚠ *Coverage caveat:* Ghidra reached only ~9% (raw import, no vector-table seeding); the address-
  constant and string negatives are 100%-coverage, but a read routine using gp-relative/computed
  addressing in the un-disassembled 91% cannot be fully excluded.

**BOTTOM LINE (all three domains analyzed — VIP_APP, VIP_BOOT, SoC):** *No code-verified path exists
from the config EEPROM to ADB authorization, the `$27` seed state, or SELinux.* VIP_APP does no I²C;
the `$27` gate byte `0xFEBD3E06` is written by hardcoded 0/1 constants, not an EEPROM read; VIP_BOOT
(where the I²C peripheral is configured) shows no located read routine and no reference to the seed-gate
addresses; the SoC has no EEPROM access and consumes only signed ProtoKey (anti-theft) state.

**UPDATE (§0.4, 2026-08-26): VIP_BOOT is now FULLY disassembled and is NOT the reader.** A complete-
coverage RH850 pass (3193 functions; every byte classified) proves VIP_BOOT is a **dual-bank on-chip
flash updater** with **no I²C/EEPROM read path at all**. So the EEPROM reader is in **VIP_APP** (or a
later stage), not VIP_BOOT — combined with the owner's 3-yr witness that the mechanism is real, the
search relocates to a full-coverage VIP_APP pass. See §0.4.

### §0.2 EMPIRICAL EEPROM DUMP DIFFS (2026-08-26) — the CORE SBI is real; the taxonomy was not

Diffing the actual 8 KB M24C64 dumps (`hardware/EEPROM/gm_csm/…` and `eeprom/bins/…`) against the
stock reference (`gm_csm_stock.bin`, sha `bbe4528c…`) resolves the code/empirical tension:

- **`stock` → `stock_modified`: EXACTLY ONE byte — `0x0441: 00 → FF`.** A deliberate minimal edit. This
  is the SBI *data* byte, empirically isolated. **Strongest single piece of evidence in the whole map.**
- **`stock` → `Y181/ADB_enabled`: 66 bytes** — the SBI signature `0x0440–42: C3 00 C3 → 5A FF 5A`
  (marker/data/marker) + backup `0x0A80/0x0A82: FF → 5A`, then a cluster in `0x16E0–0x1DCx` consistent
  with **CRC recomputation** after the edit.
- `debugging` and `ADB_HC`/`ADB_LTZ` dumps differ broadly (different VIN/trim units — VIN at 0x05C0,
  serial at 0x068x, whole-EEPROM deltas), so they are not clean stock+flip pairs; the two above are.

**Reconciliation — what is TRUE vs what was HALLUCINATED:**
- **TRUE / empirically corroborated:** the core SBI at **`0x0441`** (data), **`0x0440`/`0x0442`** (framing
  `C3↔5A`), and **`0x0A80`** (backup) — independently confirmed by two dump pairs. The minimal edit is a
  single byte `0x0441=0xFF`. CRC bytes in `0x16E0+` are real and appear to be recomputed on a persistent edit.
- **OWNER WITNESS — EEPROM→AAOS is PROVEN, not hypothetical (3 years, reproducible):**
  (1) **ADB access is gated by the two SBI bytes** — setting both `00→FF` enables ADB, every time; reverting
  disables it. (2) **Applying a different trim's calibration (e.g. a High Country CSM/Radio calibration) on
  the same CSM changes the AAOS boot animation AND the UI theme.** These are two *independent, empirically
  confirmed* EEPROM→AAOS channels. The code analysis below did not *locate* the reader — that is a **coverage
  gap**, **NOT** evidence against the mechanism. The reader provably exists (3-yr witness); it is unlocated.
  VIP_BOOT is now **fully disassembled and ruled out** (§0.4) — the search relocates to VIP_APP.
- **TWO channels now distinguished:** (a) **SBI bytes** (`0x0441`+`0x0A80`) → **ADB**; (b) **trim/model
  calibration** → **AAOS boot-animation + theme**. See §0.3 for channel (b) fully code-traced.

### §0.3 CHANNEL (b) — trim/theme pipeline, SoC side CODE-VERIFIED (2026-08-26)

SoC chain (traced in the extracted Y175 partitions): **`calserviced`** (HIDL
`vendor.gm.calibrations@1.0::ICalibrationService`, backed by `VIPCALPAL` over IPC — **it gets
GMTrim/GMModel/GMBrand from the VIP, not from this EEPROM directly**) → **`/system/bin/animengine`**
computes an integer **AnimFlavor** from those three IDs (literal log fmt
`GMTrim: %d, GMModel: %d, GMBrand: %d -> AnimFlavor:%d`; C++ syms `gm::calibrations::CalId::{GMTrim,GMModel,GMBrand}`)
→ loads `/product/ro/anim/<N>/{graphics,audio}/…` (shipped flavors: 0,1,3–10,20–23,31–33,default) → caches
in sysprop **`persist.sys.anim.flavor`**; `/vendor/bin/hw/plmanager` triggers playback. Brand RRO overlays
(`brand-<make>-theme-*`) key on **GMBrand only** (make-level — HC & LTZ share the Chevrolet theme); a
`GMSystemUI`/`GMUILib ThemeUtils` reference to `GMTrim` is an unconfirmed trim-theming lead.

Enum values (from `/vendor/calibrations/CalSets.db`): **GMTrim HighCountry=1, LTZ=16**; GMModel Silverado=4;
GMBrand Chevrolet=3. HC↔LTZ = GMTrim `1⇄16` → different AnimFlavor → different animation.

**Structural conclusion (mirrors the ADB channel):** the SoC receives GMTrim over IPC from the VIP; it does
NOT parse a trim byte from this EEPROM. So the **EEPROM→GMTrim translation is on the VIP side** (same dark
region as the SBI reader). A raw `(1,16)` GMTrim byte-pair appears **nowhere** in the 8 KB dump — confirming
the enum is not stored verbatim in EEPROM.

**Candidate EEPROM offset (bench hypothesis, UNCONFIRMED):** paired single bytes **`0x0AA0` & `0x0AE5`** —
HC=`0xF0`, LTZ=`0xC3`, stock=`0x69`. Not a verbatim enum (no clean decode to 1/16); possibly obfuscated.
Flip-and-observe to confirm/deny.

**⚠ DATA-QUALITY FLAG:** `eeprom/bins/Y181_ADB_enabled_HC.bin` is valid only `0x0000–0x0B43`; `0x0B44`→EOF is
flat zero-fill (~65% blank). **Re-dump the full 8 KB** before trusting any offset past `0x0B43`. (Most of the
raw 4186-byte HC↔LTZ diff was this blank-vs-real artifact. LTZ vs stock is only 110 bytes.)

**OBSERVATION HARNESS — the "where to look" for blind flips (once bench ADB is live):**
| Check | Shows |
|---|---|
| `adb logcat \| grep -i AnimFlavor` | live `GMTrim/GMModel/GMBrand → AnimFlavor` at boot — **the key hook: reveals if a flipped byte changed the trim/model/brand the VIP reports** |
| `getprop persist.sys.anim.flavor` | active AnimFlavor index |
| `adb logcat -s calserviced`; `lshal \| grep -i calibrations` | VIP-sourced calibration values |
| `cmd overlay list` | brand RRO (GMBrand) state |
| `ls /product/ro/anim` | shipped flavor folders |
- **HALLUCINATED (retract):** the ref-counts (871/311/17/11/28/24), the "IPC Security Config" naming for
  0x04A0/0x04C0, the "disasm-confirmed" labels, and the elaborated multi-flag taxonomy (0x04A0/0x04C0/
  0x0A40/0x0AC0/0x0BE0 as distinct "security flags"). None of those are corroborated by code OR by the
  clean dump diffs. The real modification is far simpler than the doc's taxonomy implied.

**CONFIRMED ADB RECIPE (owner, 3-yr reproducible):** set **`0x0441 = 0xFF` AND `0x0A80 = 0xFF`** — the two
SBI *data* bytes — and nothing else. ADB enables; revert either and it disables. The `0x0440`/`0x0442`
framing bytes are **NOT** required (their `C3→5A` change in `Y181/ADB_enabled.bin` is unrelated). No CRC
recompute is needed (the 1-byte `stock_modified` edit changed no CRC bytes and worked). Note on `0x0A80`:
pre-Y181 stock ships it already `0xFF` (so only `0x0441` is left to flip — matches the `stock_modified`
single-byte diff); **Y181 initializes `0x0A80` to a non-FF value, so on Y181 both bytes must be set.**

---

### §0.4 VIP_BOOT FULLY DISASSEMBLED (2026-08-26) — dual-bank flash updater, NOT the EEPROM reader

Complete-coverage RH850 pass on VIP_BOOT (`85056831`); project saved at
`research/scripts/ghidra_rh850/vipboot_rh850` (3193 functions, converged to fixpoint).

**Structure (the "1.9 MB image" is mostly erased flash):** it is a flash dump of **two firmware banks** —
Bank A `0x0–0x224FF`, Bank B `0x68500–0x8A37F` — with **85.5% of the file being erased `0xFF` flash**. The
two banks are the **same firmware relinked at different flash-bank base addresses** (dual-bank fail-safe
redundancy — *not* a byte-identical mirror; the earlier "mirror" guess was wrong). Reset vector Bank A
`0x786→0x1E9AC`; crt0 `FUN_00003322` with `gp=0xFEBDCEA4` at file `0x3344`.

**Byte accounting (every byte classified — "no dark %" achieved):** of 279,424 bytes of real content,
**code 88.5% / data+strings 9.8% / residual 1.7%** — the residual manually verified as vector-slot padding,
un-tagged format strings, version tags, and the RAM/BSS init table, **not missed code.**

**DEFINITIVE NEGATIVE — no EEPROM read exists in VIP_BOOT:**
- `RH850-IIC`/`RH850-CSIH` descriptor strings are inert Smart-Configurator BSP metadata with **zero xrefs**
  from any of the 3193 functions.
- Only peripheral drivers actually reached: the **on-chip code-flash programming** driver (`0xFFA0/FFA10xxx`
  SFRs — the signed flash-updater) and a **CSIH power-down-for-sleep** routine (`0xFFD8xxxx`, clears bits, no
  transfer). No `0x50`/`0xA0`/`0xA1` in any peripheral-register context.
- `0xFEBD3E06` (seed gate) and `GMTrim`/`GMModel`/`GMBrand`: **absent** — zero occurrences.

**Conclusion:** VIP_BOOT's entire role is dual-bank on-chip flash programming + signature validation. It does
**not** read the config EEPROM. Since the owner's witness proves the EEPROM→ADB/trim mechanism is real, and
VIP_BOOT is now excluded at full coverage, **the reader is in VIP_APP** (the prior VIP_APP passes checked the
CalGroup table and the `$27` validator but did not run a full-coverage hunt for the I²C/M24C64 read routine).
**Next: full-coverage VIP_APP pass (done — see §0.5).**

### §0.5 VIP_APP FULLY COVERED (2026-08-26) — read pipeline VERIFIED; gate/driver/trim resist static RE

Full-coverage RH850 pass on VIP_APP (`85759599`, 12,939 functions; ~90% of real content classified — the
file is 54% content `0x0–0xFFFFF` + 46% erased `0xFF` flash; ~10% tabular residue unresolved; whole-image
CRC32 `0x7FB2D59E` at EOF). Caveat: ~250 spurious `mov tp,r0` decodes slightly inflate the "code" figure.

**CODE-VERIFIED (⚠ partly walked back — see §0.6: `0x440/0x441` are *referenced* as accessor args but their value is *discarded* on reachable paths, not consumed as data):**
- Calibration accessor **`FUN_000C8F6A`** → 24-byte descriptor table **`0x4FB8C`** → computed-call into inlined
  handler bodies at **`0xF0A1A + tag*4`**. **`calItemId` == raw EEPROM byte offset — PROVEN** (unrolled loaders
  at `0x91800+` walk every byte `0x40F–0x45A` via `movea 0xNNN,r0,r6; jarl 0xC8F6A`).
- **`0x0440`/`0x0441`/`0x0442` ARE read** through this pipeline (verified at `0x91B48/0x91B60/0x91B6C`, type_tag
  5). This **overturns the earlier "likely fabricated / 0 hits."** Combined with the empirical dump (flip
  `0x0441=FF` → ADB), the SBI byte is now confirmed on **both** axes: empirically flipped **and** code-read.
- RAM-shadow arrays mapped: byte `0xFEBDAAE2`; u16 `0xFEBD6966/69C2/6C96/6ED2/6F34/6F52`; u32 `0xFEBD57A8/57BC`;
  staging `0xFEBDC212/C282`; dirty-status word `0xFEBD3B7C` — same RAM bank as the `$27` gate `0xFEBD3E06`
  (proximity only, no call-graph link).

**STILL UNLOCATED even at full coverage (the honest wall):**
- **Physical I²C driver + write-path callers** — the CalGroup commit siblings (`0xC812E/C90FC/C6CB0/C73F0`) and
  the 15 `[CAL] EEPROM Write Failure` string emitters have **zero recoverable callers** (reachable only via a
  computed-jump dispatcher static analysis couldn't surface). No `RH850-IIC/I2C/NvM/Fee` driver strings (the
  `[ELMOS_IC]` IIC strings belong to the ELMOS E522.40 antenna-diag IC — red herring).
- **`0x0441` read → `0xFEBD3E06` gate link:** no `==0xFF` compare, branch, or store into the gate byte anywhere
  reachable. If `0x0441` gates ADB, the logic is in a *consumer* of the RAM shadow, behind the same dispatch.
- **Trim/GMTrim IPC path:** `GMTrim/GMModel/GMBrand/VIPCALPAL` are **absent from VIP_APP** (0 occurrences); the
  only IPC catalog is 12 `[PLC]` power-lifecycle messages. Calibration served to the SoC is not string-named here.

**CONCLUSION — static RE is exhausted across all three images.** EEPROM bytes are provably *read* by VIP_APP's
calibration pipeline; the *consumer/gate* logic, the *write/I²C primitive*, and the *trim serve path* live in
computed-jump-dispatch code (`0xF0A1A`-style) + the ~10% tabular residue that recursive-descent + heuristic
disassembly cannot fully resolve. Further static digging has diminishing returns. **The productive path to the
remaining "how" is now DYNAMIC** — the bench harness (§0.3) + documented single-variable flip tests (`0x0441`,
then `0x0AA0/0x0AE5`), watching `getprop persist.sys.anim.flavor` / `logcat AnimFlavor` / adb reachability.

### §0.6 DISPATCH DECODE + RAW CROSS-CHECK (2026-08-26) — corrects §0.5's "code-read"; the wall is nested dispatch

Two follow-up passes (RH850 dispatch-handler decode + pure raw-byte cross-check) reconcile the structure:

- **Dispatch structure CONFIRMED (instruction-level):** `FUN_C8F6A` computes `entry=0x4FB8C+calId*0x18`, reads
  `type=*(entry+0xA)`, then `jmp 0xF0A1A[type*4]`. The 24-byte table + type-tag are real (the arithmetic is in
  the code). A raw-byte entropy test could not *detect* the tag column — a detection limit, not a refutation;
  the separate 2-byte calId catalogs at `0x3D998`/`0x3F6DE`/`0x3E0CA` (+ mirror backup page) are the group-
  membership lists, a complementary structure.
- **CORRECTION to §0.5 — `0x440/0x441` value is NOT consumed on reachable paths.** The type-5 handler
  (`0xF0A2E`) is a **generic session/pointer-chain validity check** (tests bits 0-1 of `*(ep+0x14)`; no shadow
  write; no `==0xFF`), and the call site `FUN_00091AEC` calls `C8F6A(0x43a..0x447)` in a batch and **discards
  every result** (`mov rX,r0`). So `0x440/0x441` are *accessor arguments* (real code references — not fabricated
  addresses) but their **value is not read/consumed** on any statically-reachable path. "code-read as data" ✗;
  "referenced" ✓.
- **`$27` gate `0xFEBD3E06` — EXHAUSTIVE negative:** 47 refs, only 2 writers, both hardcoded (`0` at `0xB7A10`,
  `1` at `0xAF1BE` via `mov 0x1,r28`); byte-pattern scan confirms no other encoding exists. **No calibration/
  EEPROM-derived writer.** The ADB gate is set by session-init constants, not by an EEPROM value, on any
  reachable path. (The real byte-shadow copier is `FUN_C90C4`; `0xFEBDAAE2` has exactly 4 accessors —
  `FUN_C8FC4` getter, `FUN_C7472/C6D04/C6E1C` bitfield writers — none touching the `$27` gate.)
- **The write/commit machinery hides behind a SECOND dispatch layer:** the genuinely-orphaned commit functions
  (`0xC812E/C6CB0/C73F0` — no pointer table anywhere holds their addresses) are reached only via nested
  computed-jump / interrupt context. `FUN_C73F0` contains its own table at **`0xEEEC8`** (same `type*4+base`
  shape); `FUN_C6CB0` writes a new per-item dirty bitmap at **`0xFEBDC212`**; `0xEEEC8` reaches `FUN_EF0D0`
  which does an interrupt-disabled (`di`) masked RMW on constant `0x400780E0` — **REFUTED (§0.7):** that is a
  plain 32-bit bitmask constant in RTOS event-flag/EIWR bookkeeping, not a device register.

**NET (reinforces §0.5, harder):** even two dispatch layers deep, **no statically-reachable path links EEPROM
`0x441` → the `$27`/ADB gate** — the gate is hardcoded 0/1 in reachable code, and the commit/consume machinery
lives behind nested computed-jump tables + interrupt-context peripheral access that recursive-descent cannot
follow. The mechanism is **empirically certain** (owner witness) yet **static-RE-opaque**. This fits the
"**$27 diagnostic action**" model: the SBI likely gates whether an *externally-triggered* CAN/DoIP `$27`
diagnostic *succeeds*, which then enables ADB via the dispatch-hidden path — not a boot-time EEPROM→gate read.
**The bench remains the arbiter.** (Open host-side possibility: the GHS `calibrations`/`vip_server` tasks —
under analysis — may consume the SBI the VIP forwards, explaining its absence from VIP_APP's reachable code.)

### §0.7 EEPROM UTILIZATION MAP + driver leads (2026-08-26) — reframed "find all EEPROM access"

A pass that hunted for *all* EEPROM access (not the SBI) delivered the functional map and resolved two leads:

**What the VIP actually reads the EEPROM FOR — 34 named calibration items** (string-verified; per-byte caller
wiring stays behind the dispatch wall). The EEPROM's primary VIP role is **power/sleep-state & vehicle-lifecycle
configuration**, plus a little HMI config, plus the security region:
- **`[SS_SWC]` × 32 — power/sleep/offmode lifecycle:** sleep/suspend/offmode/startup/flush timeouts,
  `cal_max_suspend_time_{1,2,3}`, `cal_str_mode_soc_min_threshold_{1,2,3}`, `cal_str_min_temp_threshold`,
  `cal_suspend_to_ram_en`, `cal_vin_relearn_en`, `cal_critical_state_of_charge_ignore`,
  `cal_cluster_animation_ignore`/`cal_rsi_animation_ignore`/`*_hmiready_ignore`, `cal_local_valet_timeout_sec`,
  `cal_master_offmode_active_timeout_min`, `cal_remote_reflash_programming_complete_timeout_sec`, etc.
- **`[J6_CDD]` × 2 — HMI/display:** `LngSelSignal` (language), `TimeDispFormat` (time format).
- **Security region:** the SBI (`0x0441`/`0x0A80`) + the `0x40F–0x45A` calItem block (empirically the ADB gate).
- **Write path (`[CAL]`):** `EEPROM Write Failure for CalGroup-%d`.
> Caveat: only 2 of 48 cal-string addresses have real code xrefs; Ghidra's function boundaries in that region
> are unreliable, so the *string list is solid* but *which function reads each item* is unresolved (dispatch wall).

**Driver leads — two refuted, one new:**
- `0x400780E0`: **REFUTED** — a plain 32-bit bitmask constant in RTOS event-flag/EIWR bookkeeping, not a register.
- The 32 interrupt vectors are **not** per-peripheral ISRs — all non-reset slots hit one RTOS entry/exit stub band
  (`0xEFBC0–0xF4AE4`); real device ISRs dispatch through a second OS-managed table static analysis can't reach.
  No `RIIC/IICA/ICCR/ICDR` register strings exist anywhere in the image.
- ~~**NEW best static lead:** a ~70-entry `jr` jump table at `0x77A00`…~~ **REFUTED (chase pass, 2026-08-26):**
  `FUN_000778EA` (which contains the `0x77A00` block) has **zero callers by every test** (dead/unreachable, or
  reached only via a runtime-populated RAM function pointer). The `jr` block is **filler physically adjacent to,
  but disconnected from,** the real computed-jump targets (`0x9F3A2/9F466/9F540` — which are themselves uncarved
  code with no containing function). Crucially, the earlier "EEPROM-string xref at `0x77B1A`" claim is **FALSE**:
  all **15** `[CAL] EEPROM Write Failure` string copies (`0x60A6…0x630E`) have **ZERO code xrefs** — Ghidra never
  linked the split `movhi`/`movea` immediate loads to the strings. The real callees off this chain are UDS
  session-state + DTC-setter plumbing, touching no peripheral/I²C register.
- **Remaining static technique (last resort):** manually scan for split-immediate (`movhi`+`movea`) loads that
  assemble the EEPROM-string / shadow / peripheral addresses Ghidra's ref manager missed — that's the only way to
  recover the emitters/driver reference. Also note the *known* dispatchers `0xF0A1A`/`0xEEEC8` are themselves
  **truncated switch-fragments** Ghidra couldn't fully carve ("too many branches") — the whole dispatch layer is
  under-analyzed, which is the real static wall.

A candidate 8 KB ring at `0xFEBDDE28` (0x2000) is a **trace/log buffer, NOT the EEPROM shadow** (recorded so it
isn't re-mistaken). Used calId ranges unchanged: `0x40F–0x45A` + CalGroup live set `0xB4–0xB5/0xF9–0x103/0xDC1–0xDC9`.

### §0.9 GUEST-SIDE ADB-UNBLOCK ARCHITECTURE — code-verified, FULL partitions (2026-08-26)

Traced on the **full** ext4 images (prior guest passes saw only a 14-file curated subset): system 3.1 GB /
vendor 465 MB / product 2.5 GB via `debugfs rdump` → 3273/1373/674 files.

**VIP IPC intake:** `/vendor/bin/IPCServer` owns the VIP link (`/dev/ipc/ipc`, `/dev/ttyS4`), demuxes logical
channels to Unix sockets. Clients via `libipc.so`: `gm_protokey` (ProtoKey→`vendor.gm.security.state`),
`diagnosticsd` (`$27` SecurityAccess), `calserviced`, and the **Vehicle HAL** (`…vehicle@2.0-service-gm`,
which sources VIN over the same transport).

**ADB-unblock decision (end-to-end):** ADB is gated by a **GM-patched `adbd`** (`com.android.adbd` apex;
`gm_adb_auth_init/verify/check_authentication`, `query_auth_manager`). It queries **`GMAuthManagerService`**
over the Unix socket **`gmauthmanagerservice.socket.adb`**, which validates a **GM-cloud-signed JSON policy**
in **`/data/gm_adb/policy`**: `TokenValidator → VinValidator(getVin) → CsmIdValidator(CSM ID) →
ExpirationValidator(vs NTP trusted time) → UserValidator`, signature `SHA256withECDSA` via
`GMTrustedADBCertificateStore`. Also a `/data/gm_adb/password` (PBKDF2/AES) path, and a **test-only override
`persist.gm.adb.secure`** ("Feature test Only!"). MEC (ManufacturerEnableCounter) + SETM (secure time)
sub-queries back the checks.

**VERDICT — the guest ADB gate does NOT depend on the SBI / `$27` / ProtoKey channel:**
- `vendor.gm.security.state` (ProtoKey state) is readable by `gm_authManager` but referenced by **0 of 492**
  decompiled classes — unused.
- `diagnosticsd` (`$27`) has **no adb symbol** — SecurityAccess does not enable adb.
- No GMAuthManager class references `vip/diagnostic/protokey/sbi/seed/SecurityAccess`.
- ADB unblock = **VIN + CSM-ID + cloud-signed policy + not-expired** (or the test property, or a local password).
- Nuance: VIN itself is VIP-forwarded (Vehicle HAL) — ordinary vehicle identity, not the SBI/seed channel.

**Reconciliation with the owner's SBI→ADB witness:** an EEPROM SBI flip **cannot forge a cloud ECDSA
signature**, so the SBI's ADB effect operates **outside** this guest gate — most likely the VIP-side `$27`/SBI
route writes/relaxes `/data/gm_adb/policy` or sets `persist.gm.adb.secure` via a path not present in these
binaries (dispatch-hidden VIP + external diagnostic). **Now a precise bench test:** with the SBI flipped, diff
`/data/gm_adb/policy`, `getprop persist.gm.adb.secure`, and `gmauthmanagerservice.socket.adb` traffic — that
shows exactly what the SBI changes. This is the definitive guest-side instrumentation the static wall couldn't reach.

### §0.10 THE COMPLETE SBI → ADB CHAIN — the local cloud-cert bypass, found (2026-08-26)

Backward-trace from the guest ADB gate found the exact local conditional that removes the cloud-cert
requirement — and it matches the owner's SBI witness (an EEPROM flip makes a *requirement* fail, so no cloud
signature is needed).

**The bypass (code-verified: `adbd` x86-64 disasm + jadx):**
- Master switch: static bool `is_secure_mode` (`.bss 0x219200`). `gm_adb_check_authentication` (`0xa5620`) and
  `gm_adb_auth_verify` (`0xa60f0`): **`if (is_secure_mode==1) return ALLOWED`** — the `GMAdbPolicy`/ECDSA cert
  chain is **never reached**. `==0` → full cert check. (Name inverted: `==1` = *enforcement off* = open.)
- `gm_adb_auth_init` (`0xa6650`) sets it from **MEC** (queried `"MEC\n"` over `gmauthmanagerservice.socket.adb`,
  `mec=atoi(reply+3)`). **Direct-disassembly VERIFIED (2026-08-26), fail-CLOSED:**
  - `cmp eax,0x100; jae 0xa6841` and `test eax,eax; je 0xa6841` → **`mec==0` OR `mec≥256` OR query-fail all →
    `xor ebx,ebx; is_secure_mode=0` = cert REQUIRED** (log `"GM Secure ADB enabled...MEC=%d"`).
  - **Only `mec ∈ [1,255]` → `mov bl,1; is_secure_mode=1` = cloud cert BYPASSED** (log `"GM Secure ADB
    disabled...MEC=%d"`).
  - `persist.gm.adb.secure=="1"` logs `"enabled via property... Feature test Only!"` → `is_secure_mode=0` =
    **force-ENFORCE** (a test hook to *lock* secure-adb ON — NOT an opener; the earlier "bypass/open" label was wrong).
  > Net: the gate **fails closed** — a broken/absent/out-of-range MEC keeps the cert requirement. The *only* local
  > path that opens adb is a genuine `MEC∈[1,255]` returned by the auth-manager, which reads DID `0xF1A0` off the VIP.

**The full chain (guest = code-verified; final hop = the VIP/EEPROM domain already established):**
```
EEPROM SBI (VIP)
 → VIP answer to UDS $22 / DID 0xF1A0 (MANUFACTURER_ENABLE_COUNTER) over CAN
 → IDiagnosticsService.requestDiagnosticData(CANBUS, 0xF1A0)   [vendor.gm.diagnostics*.so]
 → ManufacturerEnableCounter.getValue()                        [info3.jar]
 → GMMecHandler replies "MEC<n>" (plaintext, UNauthenticated socket)
 → gm_adb_auth_init: is_secure_mode = (mec != 0)
 → gm_adb_check_authentication short-circuits to ALLOWED, no cert
```

**MEC = Manufacturer Enable Counter:** nonzero during manufacturing/pre-delivery (security relaxed), zeroed at
vehicle delivery. So the SBI puts the VIP into a **manufacturing-mode MEC≠0 state**; the guest reads that as
"secure-ADB enforcement off," and adb opens with no cloud policy. **DID `0xF1A0` is the guest↔VIP crossover** —
the VIP's SBI-gated answer to that `$22` read is the single inferred hop (consistent with the proven VIP/EEPROM
gating). This resolves the whole "how the guest knows to unblock ADB" question end to end.

**Bench confirmation (now exact):** with the SBI flipped, (1) read DID `0xF1A0` via diagnostics — MEC should be
nonzero; (2) `getprop` / probe `gm_adb_is_secure_mode` — false; (3) inspect the `gmauthmanagerservice.socket.adb`
`"MEC"` reply. Also note: that MEC socket is **unauthenticated plaintext**, so it is independently spoofable on a
compromised guest (a separate finding).

### §0.11 SECURITY-RELAXATION LANDSCAPE — MEC domino + other permissive gates (2026-08-26)

**Domino of SBI→MEC≠0 is NARROW.** MEC travels as a 0–255 counter but every *gating* guest consumer collapses
it to **binary** (0 vs nonzero). Consumers: `ManufacturerEnableCounter` (reader; has an UNUSED `jni_Get_MEC`
native decl — dead), `GMVehicleData.getMec()` (fails closed → 0 on unavailable), `GMMecHandler` (echoes the raw
int to a paired diagnostic/dealer tool — the only graded passthrough), and the ADB cert gate (binary). **No
SELinux / feature-unlock cascade keyed on MEC was found** — MEC≠0's confirmed guest effect is essentially the
ADB-cert bypass.

**MEC levels: none.** `[0,255]`, out-of-range → `-1` (a third "unavailable" state → cert-required/fail-closed).
No `==N`/`>N` branching anywhere. It's a manufacturer-mode toggle, not a graded-permission field.

**Other permissive-state variables (ranked):**
| # | Variable | Source | Effect | Reachable? |
|---|---|---|---|---|
| 1 | **MEC≠0** | DID `0xF1A0` / VIP | removes the ADB cloud-cert requirement outright | yes (SBI) |
| 2 | **`persist.gm.trust_sys_time=1`** | property | bypasses NtpTrustedTime → clock rollback validates an **expired** ADB policy (MEC-independent) | if writable (untested) |
| 3 | `persist.gm.register.vin` / `.csm` | debug-only props | override vehicle VIN/CSM → satisfy a VIN/CSM-bound policy on the wrong unit | if writable (still needs a signed policy) |
| 4 | `sys.gmsec.ocsp_freq` / `exp_enforce` | properties | override OCSP/expiration values — **only on non-`user` builds** | build-gated |
| 5 | `ManageFleetFlag` (DID `MANAGED_FLEET_FLAGS`) | DID / VIP | fleet "remote enable" bit — narrow entitlement | — |
| 6 | **`SECURE_UNLOCK_LEVEL` (DID id17, Eth, graded int) + `SIGNATURE_BYPASS_TICKET` (DID id18, CAN)** | DID / VIP | `DiagnosticsInternalManager.getSecurityLockLevel()` / `isSignatureBypassTicketPresent()` — genuine **ECU reflash-security** primitives (the guest-facing UDS `$27` analog); **NO caller found in this build** | OPEN — likely used by an external flashing tool or `GMRegistrationService.apk` (only odex/vdex present, not decompiled) |
| 7 | `DEVICE_REGISTRATION_ENABLE_CHECK_OVERRIDE` (CalSets.db, `=0`) | signed calibration | if `1`, skips device/account registration binding — theoretically most powerful | needs cal-flash (not runtime) |

`VEHICLE_LOGISTICS_MODE=1` (CalSets.db) is a plausible ship/transport mode but no guest consumer was located
(inferred). `vendor.gm.security.state` / `gm_protokey` is anti-theft — **restrictive, not permissive**
(`data_locked` is the outcome to avoid).

**Takeaways:** (1) highest-leverage *reachable* unlock = **MEC≠0** (the SBI path) — the only one that removes a
whole auth requirement. (2) MEC-independent runner-up = **`persist.gm.trust_sys_time=1` + clock rollback**
(defeats ADB-policy expiration) — test writability with `setprop` once adb is up, watching for the SELinux
denial. (3) Most interesting open thread = **`SECURE_UNLOCK_LEVEL` / `SIGNATURE_BYPASS_TICKET`** — real reflash
primitives with no located caller; if wired up (via `GMRegistrationService.apk`, needs re-dex from odex/vdex)
they outrank MEC (gate ECU *programming*, not just a debug shell).

### §0.12 REFLASH-SECURITY PRIMITIVES — `SIGNATURE_BYPASS_TICKET` is LIVE (dev-signed VIP flashing) (2026-08-26)

> ⚠ **NAMING COLLISION:** this "SBI" = **Signature-Bypass ticket** (DID CUSTOM 18, CAN) — a DIFFERENT mechanism
> from the EEPROM **Seed-Bypass Indicator** (`0x0441`/`0x0A80`, the adb/MEC path). Same abbreviation, distinct things.

**`SECURE_UNLOCK_LEVEL` (DID CUSTOM 17, Ethernet): DEAD in this build** — `DelayedWKSApp.DiagnosticDispatcher.
getSecurityLevel()` wraps it but has **no caller** anywhere in the guest (consumed by an external SPS/DoIP
programming tool over Ethernet, not guest app code). Its enum is GM's graded **SecurityLevel ladder** (the
guest-visible UDS `$27` taxonomy — this answers "are there other/graded levels?"):
`None=0, Service=1, AssemblyPlant=3, OTA=5, Engineering=9, RemoteDiagnostics=11, SupplierSecurityAccess=13,
ExtendedReflash=17, ExtendedAssemblyPlant=19, ExtendedOTA=21, EndOfLife=95`.

**`SIGNATURE_BYPASS_TICKET` (DID CUSTOM 18, CAN): LIVE — highest-leverage primitive found.** Consumer:
`com.gm.server.update` (**DelayedWKSApp**, GM's OTA/wireless ECU-programming service), `ModulePart.verify()`:
```java
if (manifest.getSupplierData().isDevelopmentSecurity()) {
  boolean allowDev = PersistStore.get(AllowDevSignedVIP);
  boolean vip = moduleID == 1 /*VIP_APP*/ || moduleID == 71 /*VIP_BOOT*/;
  if (!allowDev && vip && !DiagnosticDispatcher.isSBISet())
     throw new InvalidException(526, "development signed package with vip without SBI");
}
```
**Effect: a valid Signature-Bypass Ticket on CAN — OR the `AllowDevSignedVIP` PersistStore flag — lets the OTA
programmer accept a DEVELOPMENT-SIGNED (non-production) firmware package targeting the head unit's own
`VIP_APP`(1)/`VIP_BOOT`(71), bypassing production-signature enforcement (`InvalidException 526`).** This gates
**arbitrary firmware installs to the VIP**, not just a debug shell — architecturally it outranks the MEC/adb unlock.

**DID sources (code-verified):** `SECURE_UNLOCK_LEVEL` ← Ethernet (`getEthSecLevel`); `SIGNATURE_BYPASS_TICKET` ←
CANBUS (`VIPRequestManager`, `RequestSource(CANBUS,255,255)`).

**Two new bench threads:** (1) the **`AllowDevSignedVIP`** PersistStore flag — if writable, it *alone* permits
dev-signed VIP firmware (no ticket needed) — test writability. (2) the **Signature-Bypass Ticket** is a CAN
value (DID 18) — same VIP/CAN territory as the EEPROM path; who issues/gates it (SPS tool? the VIP based on its
own SBI/manufacturing state?) is the next question, and would connect firmware-flash bypass back to the EEPROM.

### §0.13 EMPIRICAL `$27` ALL-FF SEED + `SECURE_UNLOCK_LEVEL` inference + DID-18 issuer (2026-08-26)

**Empirical CAN capture** (`gm_dps/misc/Aug24_session/ecu80_READ.Txt`, ECU `0x80`=CSM via MDI2/OBD-II):
```
10 03 → 50 03 …            extended diagnostic session opened
27 01 → 67 01 FF FF … FF   requestSeed L01 → seed = ALL 0xFF (~32 B)
22 F1 90 → 62 F1 90 …      ReadDataByIdentifier VIN
```
In the SBI-bypass state the CSM's `$27` **seed is all-FF** → the seed challenge is trivialized. **Gaps:** no
`27 02` sendKey in the capture, so "accepts any/stub key" is *inferred* (all-FF seed + known SBI effect), not
closed; and only **level 01** appears — powerful levels (OTA=5/Engineering=9/ExtendedReflash=17) not captured.

**DID-18 Signature-Bypass Ticket — issuer & trust (guest RE, code-verified):**
- **Issuer = the VIP** (`VIPRequestManager`, CANBUS). Guest→VIP crossover is native `libdiagnosticsbridge.so`
  (`MessageAccess`/`MessageValues` — real CAN arbitration ID resolved there, beyond guest visibility).
- **Trust = presence-only:** `isSignatureBypassTicketPresent()` = `payload>0` — **no signature/nonce/MAC/structural
  validation guest-side.** The guest trusts whatever the VIP answers on CAN.
- **Guest is read-only** (no `$2E`/`$31` mint path); provisioning is VIP-side or an external CAN tool→VIP.
- `AllowDevSignedVIP` = app-private SQLite flag, **debug-build-only writable, not exported, not adb-reachable** →
  dead on production. (NB the wire value "18" is service-manual nomenclature; the Android enum uses `mGBMessageId=2`.)

**Is `SECURE_UNLOCK_LEVEL` inferable as reachable?** Plausibly, with two unclosed gaps:
1. **Key + higher levels unproven** — need `27 02` sendKey (stub/FF key → `67 02` accept vs `7F 27 35` invalidKey)
   and `27 03/05/09/11` seeds to see if higher levels are also all-FF.
2. **Transport split** — the all-FF seed is **CAN** `$27` (CSM); `SECURE_UNLOCK_LEVEL` is **Ethernet/DoIP**
   (`getEthSecLevel`, `EthernetRequestManager`). Whether the CSM's `$27` state is shared CAN↔Ethernet (so a CAN
   unlock raises the Ethernet-read level) is unconfirmed — may be separate per-transport contexts.

**Delivery = exactly as hypothesized:** MDI2/OBD-II on **CAN** (proven — that's what `ecu80_READ.Txt` is) for the
CAN `$27`; a **DoIP tool on the T1 network** for `SECURE_UNLOCK_LEVEL` (Ethernet).

**The bigger convergence:** DID-18 is VIP-issued + presence-only-trusted, and the all-FF seed shows the SBI
trivializes the VIP's `$27`. If the VIP emits the ticket based on that same SBI/security state, then **EEPROM SBI
→ VIP `$27` trivialized → Signature-Bypass Ticket present → dev-signed VIP firmware install allowed, and the guest
cannot tell** — closing the loop from the EEPROM to arbitrary VIP firmware. The VIP-side "SBI→ticket" gate is
behind the native/firmware wall (inferred, not proven).

**Bench tests to close it (MDI2/DPS on CAN + a DoIP tool):** (a) `27 02` sendKey with a stub key at L01;
(b) `27 03/05/09/11` requestSeed — all-FF too?; (c) after a CAN `$27` unlock, read `SECURE_UNLOCK_LEVEL` over DoIP
(state-sharing test); (d) read the DID-18 ticket payload with the SBI set vs cleared.

### §0.14 EMPIRICAL CLOSURE — RH850 boot UART logs confirm SBI→MEC→adb (2026-08-26)

Passive RH850/VIP UART boot captures (owner: read-only, no commands sent) **directly confirm the previously-
inferred "VIP reports MEC≠0" hop** — the last unproven link in the SBI→ADB chain:

| Boot log | VIP build | `[J6_CDD] Transmitted MEC Value` | Meaning |
|---|---|---|---|
| `VIP_log_2B.174.4.1_10JUL24.txt` | 2B.174.4.1 (Jul 2024) | **`0x 0`** | stock / pre-EEPROM-mod → MEC==0 → adb cert REQUIRED |
| `Y175_session.log` = `Y175_VIP.log` | 2B.175.1.5 | **`0xff`** | SBI-set bench → MEC=255 (`∈[1,255]`) → `is_secure_mode=1` → adb cert BYPASSED |

The VIP **reads the EEPROM and transmits MEC** to the SoC at boot (`0x0` stock vs `0xff` SBI-set), and separately
logs `Transmitted Response for DID: 0xF1A0` (the MEC DID) repeatedly — **confirming the VIP is the ECU that
answers DID `0xF1A0`.** So the full chain is now closed end to end, no inferred hops:
**EEPROM SBI → VIP transmits MEC=0xFF → SoC `gm_adb_auth_init` sets `is_secure_mode=1` → adb opens, no cloud cert.**

Other boot-log notes: `[PROTOKEY] ICUSB module enabled` (the ADB/ICUSB module) + repeated `[PROTOKEY] Receives
invalid seed [1]/[2] from BCM` = the **anti-theft** VIP↔BCM ProtoKey handshake (failing on the disconnected bench
— the DATA_LOCKED channel, separate from the adb path). The VIP serves the manufacturer DID block
(`F1A0/F190/F0F3/F0B4/F1CB/F1DB/F1CC/F1DC`), but **no DID-18 Signature-Bypass Ticket appears at boot** (requested
on-demand during OTA programming) — that specific read still needs the bench.

---

## 1. EEPROM Layout Maturity & Detail Level

> **§0 supersedes the "Verified" / "Evidence" columns in this section for all security rows.**
> "disasm-confirmed" for 0x0440/0x0A80 is retracted; the xref counts are non-reproducible.

### Current documentation status:

| Region | Detail Level | Evidence | Verified | Gaps |
|--------|--------------|----------|----------|------|
| **Boot/Init (0x0000–0x03FF)** | Field-level | Byte reads + structure inference | Partial | Exact bit fields for boot flags unclear |
| **Security Config (0x0400–0x04FF)** | Byte-level (SBI only) | ~~`0x0440/0x0A80` SBI disasm-confirmed; 0x04A0/0x04C0 via xrefs (17/11 refs)~~ **RETRACTED (§0): SBI is empirical, not disasm-confirmed; 0x04A0/0x04C0 are NOT security flags (fabricated ref-counts)** | SBI empirical | Only `0x0441`+`0x0A80` real |
| **Device ID (0x0500–0x05FF)** | Field-level | VIN, serial, part# reads verified from dump | High | — |
| **Backup Security (0x0A00–0x0AFF)** | Byte-level (0x0A80 SBI) | ~~0x0A00 (871 refs), 0x0B00 (311 refs)~~ **ref-counts RETRACTED (§0) — fabricated/grep-noise, not semantic xrefs** | Low | Only 0x0A80 (SBI) is real |
| **Feature Flags (0x0B00–0x0BFF)** | Byte-level (0x0B40 debug mode), Field-guessed (0x0A40/0x0A60/0x0AC0/0x0BE0) | 0x0B40 documented; 0x0A40 (28 refs), 0x0BE0 (24 refs) via xref | Low-Medium | Undocumented flags need physical or RAM-shadow testing |
| **UI/Display Settings (0x0E00–0x0EBF)** | Field-level | Timing/threshold values (e.g., 0xE01=30 sec screen timeout) read from sample dump | Medium | Bit-field granularity guessed; interpretation inferred not verified |
| **Display Calibration (0x0EC0–0x0F7F)** | Table-level | Brightness LUTs (11-point, 22-point), color RGB calibration (0x0F40) | Medium | Ambient-light compensation logic guessed |
| **Audio Calibration (0x0FE0–0x12DF)** | Table-level | Volume curve (11 points), EQ/DSP (10 bands), fade/balance (22-point) | Medium | Link to actual audio codec/DSP unknown; calibration scale/units guessed |
| **Checksums/CRCs (0x16E0–0x1FFF)** | Byte-level | Six CRC words identified; values in sample dump recorded | Low | CRC algorithm (CRC16? CRC32?), polynomial, coverage scope **not documented** |

### Summary:
- **Enhanced since initial analysis:** Yes. Dec-2025 report = raw byte map. Jan–Feb 2026 = firmware xref analysis added undocumented flags. Aug-2026 = marker-rotation and CalGroup system discovery.
- **Current detail:** ~~Security-critical (`0x0440/0x0A80`) = disasm-confirmed, high fidelity.~~
  **RETRACTED per §0** — the "disasm-confirmed" claim was not reproducible; those offsets show only
  ordinary calibration handling in VIP_APP, and the real EEPROM read logic is in VIP_BOOT (not yet
  disassembled). Undocumented-flag "xref counts" are grep noise, not semantic references.

---

## 2. Complete EEPROM Parameter Inventory

### 2.1 Security & Access Control

> **⚠ SEE §0 — the "Evidence Level" column in this table is largely FALSE.** "Disasm-confirmed"
> for 0x0440/0x0A80 is retracted; "IPC Security Config" for 0x04A0/0x04C0 rests on a misread of the
> `[IPC_S]` *serial-transport* log tag; the ref-counts are non-reproducible. No security offset here
> is code-verified in VIP_APP. Treat every row as an UNVERIFIED historical hypothesis pending the
> VIP_BOOT + CalGroup-table decode.

| Address | Field | Documented | Polarity | Evidence Level | Notes |
|---------|-------|-----------|----------|----------------|-------|
| **0x0441** (data; framing 0x0440/0x0442) | Primary SBI (Seed Bypass Indicator) | Yes | 0xFF=bypass, 0x00=locked | ~~Disasm-confirmed (VIP 0xb67d0 validator)~~ **empirically flips ADB + code-read via CalGroup accessor; NOT via 0xb67d0 (retracted §0)** | ADB gate is SoC-side (MEC/`is_secure_mode`) |
| **0x0A80** | Backup SBI | Yes | 0xFF=bypass, 0x00=locked | ~~Disasm-confirmed~~ **empirical only; static reader not located (§0)** | Both SBI bytes required on Y181 (owner-verified) |
| **0x0B40** | Debug Mode Flag | Yes | 0x01=enabled, 0x00=disabled | Firmware refs (9 xrefs) | Enables additional diagnostic output or feature access |
| ~~**0x04A0**~~ | ~~IPC Security Config #1~~ **RETRACTED (§0)** | — | — | **Not a security flag** — `[IPC_S]`=serial-transport log, not "IPC Security"; the "17 refs" is fabricated | — |
| ~~**0x04C0**~~ | ~~IPC Security Config #2~~ **RETRACTED (§0)** | — | — | **Not a security flag** — "11 refs" fabricated | — |
| **0x0A40** | Feature Enable (mid-region) | Undocumented | Unknown | Firmware xrefs (28 refs) | Medium priority; likely hidden-feature enable, not the `$27` gate |
| **0x0BE0** | Late-Region Flag (danger zone) | Undocumented | Unknown | Firmware xrefs (24 refs) | **LOWEST priority.** Likely manufacturing lock / debug-interface disable (OTP-like). **Do not flip casually.** |
| ~~**0x1A00**~~ | ~~Tertiary Security~~ **RETRACTED (§0)** — no code evidence it is a security byte | — | — | — | — |

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

> **⚠ SUPERSEDED 2026-08-26 (§§3–4).** The mechanism described below — "VIP `0xb67d0` reads `0x0440/0x0A80` and
> returns an all-`0xFF` seed, disasm-confirmed" — is the pre-correction hypothesis and is **wrong on attribution.**
> `0xb67d0` is NOT the ADB gate. The real, verified ADB chain is **SoC-side**: EEPROM SBI → VIP transmits MEC=0xFF
> (DID `0xF1A0`) → `gm_adb_auth_init` sets `is_secure_mode=1` → adb allowed with no cloud cert (see §0.9/§0.10/§0.14).
> The `$27` all-FF seed on the CSM is real (§0.13) but does **not** drive the guest ADB gate. Read §§3–4 as archival.

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

> **⚠ SUPERSEDED 2026-08-26 (§§5–8).** These sections still treat `0x04A0/0x04C0/0x0A40/0x0BE0` as live cal-`$27`
> gate candidates (with the fabricated ref-counts) and `0x1A00` as "Tertiary Security", and still label `0x0440/0x0A80`
> "disasm-confirmed". All retracted — see §0 and §0.7. The only confirmed security bytes are the SBI `0x0441`+`0x0A80`;
> the four "undocumented flags" have **no code evidence**. Read §§5–8 as archival; do not use their testing-priority
> tables. The current bench targets/recipe are in `EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md`.

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

