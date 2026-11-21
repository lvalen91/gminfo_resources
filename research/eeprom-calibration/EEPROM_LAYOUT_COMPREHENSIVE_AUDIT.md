# EEPROM Layout Audit

**Platform:** GM IOK/Harman INFO3.7-3.8 CSM. ST Microelectronics M24C64 (64-Kbit/8KB, I2C, TSSOP8,
typical address `0x50`), read by the Renesas RH850/F1K VIP MCU (`R7F7015873AFP`). VIP firmware
images: VIP_APP (Y175 `85759599`; later builds `86331656`), VIP_BOOT (`85056831`, byte-identical
across builds). Sample ECUID `004B41DC0000160006104145610114AC`.

**Scope — what lives here:** the complete EEPROM address/parameter map; the Seed-Bypass-Indicator
(SBI) ADB-bypass mechanism end to end on the VIP side; the VIP's CalGroup read/dispatch pipeline and
the limits of static RE against it; the trim/theme calibration channel's EEPROM-adjacent half; the
I2C bus/hardware attack surface for this chip; checksum/CRC status per block; the AUTOSAR NvM
descriptor-table structure the firmware uses.

**What does NOT live here (pointers only):**
- The guest-side ADB/MEC/certificate chain (`GMAuthManagerService`, `gm_adb_auth_init`,
  `is_secure_mode`, MEC per-unit readings, root/registration limits) →
  [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md §2.3.7](../boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).
- The live T1/Ethernet SecurityAccess (`$27`) correction for the calibration gate →
  [`../../diagnostics/diagnosticsd_security_access.md`](../../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
- `SIGNATURE_BYPASS_TICKET` / `SECURE_UNLOCK_LEVEL` / dev-signed VIP firmware installs: kept in
  §10.1 below — `../../platform/ota_update_stack.md` / `../../platform/ota_programming_roles.md` do
  not currently carry this level of detail, despite being the more natural OTA-topic owners.
- CalGroup/CalDef calibration-value catalogs and the VIP boot-log calibration-index table →
  `CALDEF_VIP_CALIBRATION_ANALYSIS.txt`.
- UDS `$27`/SecurityAccess seed-key algorithm, CMAC, signature-trust chain → `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`.
- VIP IPC channel catalog, PLC messages, ADB bypass's VIP-feature context, CRC-protection boundary
  table (as a VIP-control topic), DPS capabilities/limits → `VIP_CONTROL_ANALYSIS.txt` (this doc
  absorbs that doc's EEPROM-specific §2/§3/§8/Appendix A content; VCA keeps the rest and should
  point back here for the address map, CRC map, and I2C table it used to carry).
- Step-by-step bench test tiers/procedure (Tier 0-3), backup/rollback, the 5 live UDS/DID test
  recipes → `EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md` (methodology only; this doc is "which byte,"
  that doc is "how to test it").
- Platform's `../../platform/eeprom_i2c_security.md` is meant to keep only a one-line pointer to this
  doc for the deep RE/attack-surface content — the forensic depth here is research-only, not
  platform-owner material. **Fixed 2026-11-21:** the prior pass had left `eeprom_i2c_security.md`
  carrying the substantive SBI-reset mechanism (the `FUN_ram_000c6564` bulk-restore finding, §2
  above) and a full prose duplicate of the EEPROM memory map / I2C / GPIO / serial content instead
  of a pointer back here. That file is now trimmed to a short pointer plus its own live `[C]`
  capture citations; every fact it previously carried that was not already present here has been
  folded into this doc (§2, §5.1, §5.2, §5.4, §7, §8, §8.1) — see those sections and this doc's
  History (§12, 2026-11-21 entry) for what moved where. The duplication this note used to flag is
  resolved.

## Evidence legend
`[C]` confirmed (disassembly + CAN/empirical corroboration, or byte-exact match to an external
log/firmware constant) · `[S]` static/structural (firmware- or spec-derived, not independently
byte-matched) · `[I]` inferred (pattern/heuristic, not code- or byte-confirmed) · `[U]` unverified/
untested hypothesis · `[inferred]` same as `[I]`. Tags follow each claim; a dated correction
overrides an earlier tag on the same claim.

**Related:** `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`, `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`,
`VIP_CONTROL_ANALYSIS.txt`, `CALDEF_VIP_CALIBRATION_ANALYSIS.txt`, `EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md`,
`HARDWARE_HYPERVISOR_ATTACK_VECTORS.md`, `../../platform/eeprom_i2c_security.md`,
`../../diagnostics/diagnosticsd_security_access.md`.

---

## 1. Device & reader facts

- Chip: ST M24C64, 8192×8 bit, I2C, typical bus address `0x50`, 5ms write cycle, 4M write-cycle
  endurance `[S]` (compendium §3.3).
- **The VIP_APP firmware is the EEPROM reader, not VIP_BOOT.** A full-coverage RH850 disassembly of
  VIP_BOOT (`85056831`, 3193 functions, every byte classified) found it is a dual-bank on-chip flash
  updater with **zero** I2C/EEPROM read path — `RH850-IIC`/`RH850-CSIH` descriptor strings are inert
  Smart-Configurator BSP boilerplate with zero xrefs from any of its 3193 functions `[C]`. The actual
  physical I2C driver and write-path callers were never located even at full VIP_APP coverage (12,939
  functions, ~90% classified) — they sit behind computed-jump dispatch tables and ~10% of tabular
  residue that recursive-descent disassembly cannot fully carve. **Static RE is exhausted on this
  question**; the mechanism is proven empirically (3-year owner-reproducible bench recipe, below),
  not by a located read routine.
- The UDS `$27` SecurityAccess SendKey handler is `FUN_000b6708`/`0xb67d0` (906 bytes, present as a
  full function — not a stub — in Y175/Y177/Y181 alike, per `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`
  §2, carried-unchanged, cited not restated). **It validates the CAN `$27` seed/key, it does NOT gate
  ADB** — an early hypothesis attributing the ADB gate to this function is retracted; see §2 and §9.

## 2. The SBI (Seed-Bypass Indicator) mechanism — settled

Two independent SBI records exist in the security region, each with a 1-byte **marker/data/marker**
framing. **This is the one address identity this audit previously stated inconsistently across its
own sections; it is now settled by cross-checking the empirical dump diff against the descriptor
table (full account in §12 History, item 2026-10-15):**

| Record | Marker (pre) | **Data byte (the one that matters)** | Marker (post) |
|---|---|---|---|
| Primary SBI | `0x0440` | **`0x0441`** | `0x0442` |
| Backup SBI | `0x0A80` | **`0x0A81`** | `0x0A82` |

- Polarity: data byte `0xFF` = bypass, `0x00` = locked `[C]`.
- Marker bytes are **not** a fixed signature — they vary by firmware/unit (`0x69`/`0xF0`/`0x5A`/`0xC3`
  observed across dumps and states) and are CalGroup-assigned at runtime; only the data byte is
  validated. Locate each SBI by **offset**, not by marker value `[C]`.
- **Empirical isolation (strongest single piece of evidence in this map):** diffing a stock dump
  against a deliberately-modified one found **exactly one** changed byte: `0x0441: 00→FF` `[C]`. A
  second stock-vs-Y181-ADB-enabled diff showed the full marker/data/marker signature flip plus the
  backup pair, consistent with the same mechanism.
- **CONFIRMED ADB RECIPE (owner, 3-year reproducible):** set **`0x0441 = 0xFF`** and **`0x0A81 =
  0xFF`** — the two SBI data bytes — and nothing else. The `0x0440`/`0x0442`/`0x0A80`/`0x0A82` marker
  bytes are not required; no CRC recompute is needed (the single-byte `0x0441` edit in the minimal
  stock→modified pair changed no CRC bytes and worked standalone). Revert either data byte and ADB
  disables.
  - Pre-Y181 stock ships `0x0A81` already `0xFF`, so only `0x0441` needs flipping on those builds
    (matches the single-byte diff above).
  - **Y181 initializes `0x0A81` to a non-FF value** — on Y181, both data bytes must be set.
- **What the SBI does NOT do:** it does not unlock the bootloader, AVB/secure boot, or Android kernel
  SELinux. It is read by VIP_APP's CalGroup pipeline (§3) and, via a chain this doc does not own, ends
  up presented to the SoC as a Manufacturer Enable Counter (MEC) value that the SoC's ADB-auth stack
  treats as binary (0 vs nonzero) — full chain at
  [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md §2.3.7](../boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).
  Separately, on CAN, the SBI-bypass state also makes the CSM's own `$27` seed come back all-`0xFF`
  (an independent, VIP-$27-validator-side effect, not consumed by the ADB chain) `[C]`.
- **Not proven:** that flipping the ADB SBI also opens the *calibration* `$27` SecurityAccess gate.
  They share the VIP/EEPROM anchor layer but no single flag has been shown to govern both — see §11.
- **Marker-agnostic check, additional evidence (absorbed from platform doc, 2026-11-21):** an
  ADB-enabled dump shows **both** `0x0440` and `0x0A80` (the marker bytes) flipped to
  `5A FF 5A FF` alongside the data-byte flips. There are **zero code references to the literal
  address `0x0A80`** in either VIP binary — the security check reads only the data byte
  (`0x0A81`), marker-agnostic. This corroborates, rather than weakens, the "locate by offset, not
  marker" conclusion above: the marker's co-occurring flip is an artifact of how the bulk
  restore/write path touches the whole marker/data/marker record, not a separate hardcoded check
  on the marker address `[I]` (inferred; the platform source gave no code evidence for this mechanism).
- **Live Android security posture (`[C]` live-Y175 2026-10-05, absorbed from platform doc
  2026-11-21):** on the unit captured, `ro.secure=1`, `ro.adb.secure=1`, `ro.debuggable=0`, and the
  live adb shell is the normal uid 2000 (`u:r:shell:s0`) — i.e. this specific unit was captured in
  **secured** operation (adb via the standard, certificate-gated path), not the SBI-bypass
  (`is_secure_mode=1`, no-cert) path described above. The EEPROM/SBI bypass mechanism itself
  remains established independently per the rest of this section; this note only characterizes
  the posture of the one unit this particular capture pass examined.

## 3. VIP read/dispatch pipeline (CalGroup) — what static RE did and didn't find

**Y175 exact-build baseline revalidation — 2026-11-18:** fresh PyGhidra
analysis of the signed Y175 VIP_APP module `85759599` (payload SHA-256
`c6b214a75b2139e344e796da46fb6a6ca23f2ca91a8a6b2ee9cf33fda389be55`)
found 1,301 direct references to the generic accessor at `0xC8F6A`, from 170
caller functions. Decompilation resolves 1,300 literal accesses covering 1,060
distinct EEPROM cell IDs. The sole non-literal call is `FUN_00066CE4`, which
chooses cell `0xDA0` or `0xDA1` from its Boolean parameter; including those
two cells yields **1,062 directly recovered cells**. Earlier 1,050-cell counts
are superseded for this exact build.

The table beginning at `0x2475A` has **181 valid 12-byte EEPROM descriptors**
in this module; the two following 12-byte records are not EEPROM descriptors.
The valid records describe 2,377 of the 8,192 EEPROM bytes. This descriptor
coverage is metadata, not proof that every covered byte is consumed at runtime:
the direct reader map currently covers 1,062 bytes; 1,519 are descriptor-only;
and 5,611 have neither a direct-reader nor valid-descriptor ownership result.
Those categories must remain distinct while the computed read/write dispatch
is resolved.

**Caller-path correction — 2026-11-18:** the prior “computed caller
unresolved” conclusion was a Ghidra auto-analysis gap. Raw RH850 disassembly
recovers Dispatcher A: **106 direct `jarl` cases** from `0xB9FDA` through
`0xBA494`. They invoke 106 recovered accessors and cover **989 byte-cells**.
For example, the dispatcher calls the SBI CalGroup-`0x3B` accessor
`FUN_00091AEC` at `0xBA316`; CalGroup `0x44` at `0xBA05E`; CalGroup `0x01` at
`0xBA46C`; and the `0x0B41`-containing CalGroup `0xA3` at `0xBA48A`.

The dispatcher is an all-CalGroup read/validate/reconcile path. Direct entry
into it proves that those cells are loaded into a group scratch buffer; it does
not establish a field semantic, a writer, or an external effect. The verified
per-cell static result is currently:

| Evidence class | Cells | What is proven | What is not proven |
|---|---:|---|---|
| Dispatcher A direct reader | 989 | EEPROM cell → direct `jarl` case → accessor loader | field meaning; writer; external effect |
| Other named accessor reader | 73 | EEPROM cell is read by a recovered loader outside Dispatcher A | complete invocation context or field meaning |
| Valid descriptor only | 1,519 | descriptor metadata covers the cell | live read, write, or field meaning |
| Neither result | 5,611 | no assertion | unused versus indirect/bulk access |

This is the complete static evidence classification for all 8,192 addresses
of the supplied EEPROM size, not a semantic field map. A claim that assigns
an action to any class other than a traced consumer would overstate the binary
evidence. Resolving the remaining semantic consumers requires dataflow from
the group scratch buffers and passive I2C observations during each operating
mode; it must not be filled with inferred labels from EEPROM value differences.

- VIP_APP's calibration accessor is a table-driven dispatcher, `FUN_000C8F6A` at `0xc8f6a`, reading a
  24-byte descriptor table at `0x4FB8C` (type byte at `entry+0xA`) and jumping into handler bodies at
  `0xF0A1A + type*4` `[C]`. **`calItemId == raw EEPROM byte offset` is proven** — unrolled loaders at
  `0x91800+` walk every byte `0x40F-0x45A` through this call `[C]`.
- VIP_APP's *entire live* CalItem set is `0xB4-0xB5`, `0xF9-0x103`, `0xDC1-0xDC9` (20/20 call
  sites, exhaustive) — handlers are width-tags, `divqu` value-scaling, list-node reassembly,
  marker-rotation copy: ordinary calibration plumbing. **None of the 8 flagged security offsets
  are in the live set.** The `$27` validator (`FUN_000b67d0`) and the CalGroup accessor are
  **structurally independent** (direct negative xref — neither calls the other) `[C]`.
- `0x0440/0x0441/0x0442` **are read** through this pipeline (verified at `0x91B48/0x91B60/0x91B6C`,
  type-tag 5) `[C]` — but the type-5 handler (`0xF0A2E`) is a generic session/pointer validity check,
  and the call site that reads this specific range (`FUN_00091AEC`) **discards every result**
  (`mov rX,r0`). So `0x440/0x441` are real accessor *arguments*, but their value is not *consumed* on
  any statically-reachable path — "referenced" yes, "code-read as data" no `[C]`, correcting an
  earlier pass's over-read of the same evidence.
- The `$27` gate byte `DAT_febd3e06` has an exhaustive 47-reference, 2-writer static profile; both
  writers are hardcoded `0`/`1` constants (`0xB7A10`, `0xAF1BE`) — **no EEPROM-derived writer exists
  on any reachable path** `[C]`.
- The write/commit machinery (`0xC812E/C6CB0/C73F0`, the 15 `[CAL] EEPROM Write Failure` string
  emitters) has **zero recoverable callers** by static analysis — reachable only through a second,
  nested computed-jump dispatch layer (`FUN_C73F0`'s own table at `0xEEEC8`) that recursive-descent
  disassembly cannot fully resolve `[C]`. This, not a missing mechanism, is why no single instruction
  linking "read `0x0441`" to "set the gate" was ever found.
- Refuted/dead-end leads kept so they aren't re-chased: separate 2-byte calId catalogs at
  `0x3D998`/`0x3F6DE`/`0x3E0CA` (plus a mirror backup page) are the group-membership-list
  structure complementary to the CalGroup descriptor table, not a distinct security mechanism;
  `0x400780E0` is a plain RTOS event-flag/EIWR bitmask constant reached via `FUN_EF0D0`'s
  interrupt-disabled masked RMW, not a device register; the `0x77A00` `jr` jump-table dead end
  (`FUN_000778EA` has zero callers) has its real, statically-unreachable computed-jump targets at
  `0x9F3A2`/`0x9F466`/`0x9F540`, where the 15 `[CAL] EEPROM Write Failure` string copies live at
  `0x60A6` through `0x630E` with zero code xrefs.
- Working model (not proven, consistent with all evidence): the SBI most plausibly gates whether an
  *externally triggered* CAN/DoIP `$27` diagnostic succeeds, which then (via the MEC/DID `0xF1A0`
  path owned by GBUR §2.3.7) enables ADB — not a simple boot-time EEPROM→gate read `[I]`.

**History (mechanism resolved, 2026-08-25):** the SBI's observed self-reset (value flips back
with no `$2E` write and no unsolicited message) is explained by a separate VIP firmware trace.
`FUN_ram_00091938` (the SBI accessor) is **read-only** — no per-cell SBI writer exists anywhere
in `vip_app.bin`. The value only changes via a **bulk restore-to-ROM-defaults** routine
(`FUN_ram_000c6564`), reached from a re-init state machine, consistent with standard AUTOSAR NvM
behavior: a CRC/validity failure on the SBI CalGroup triggers a factory-default restore into the
RAM shadow, which the CAL layer then persists back to EEPROM `[C]`. One gap remains unresolved:
the precise trigger condition (power-on vs. a specific session/RoutineControl transition) — the
re-init handler is reached via an unresolved computed jump `[U]`. (This is the canonical home for
this mechanism; `../../platform/eeprom_i2c_security.md` no longer carries a prose duplicate — fixed
2026-11-21, see §12 History.)

- A previously-circulated claim that a specific calibration file (`85783460`) targets and resets
  the SBI cells is **REFUTED** (2026-08): those bytes live inside a gzip-compressed CalOvride XML
  stream, not an EEPROM address:value table. SBI values change only via the bulk
  restore-to-ROM-defaults routine above, not a targeted cal payload.
  Content of `85783460`, consistent with that refutation: 34 `OverrideValue` entries (12 Boolean, 1 Integer, 21 `BinaryFile`). Their `CalID`s are opaque EMF/Rhapsody GUIDs, so descriptive names such as Bluetooth-profile names were inferred, not extracted; the 21 `.scd` files are telephony/hands-free echo-cancellation (SSE, Speech Signal Enhancement) tuning sets. `[X]` byte-level extraction, source: external calibration-file extraction notes, §2.

**Candidate SBI-carrying DIDs (read-attempt result, not a confirmed mapping):** four DIDs were
probed for SBI content and all four failed in a read-only GCI session: `F0F4` ->
`7F 22 22` conditionsNotCorrect; `F0F8`, `E0B2`, `E0B5` -> `7F 22 31` requestOutOfRange `[U]`.
The NRCs mean these DIDs need a higher session/security context than a plain GCI read provides —
not evidence either way that any of the four actually carries SBI content.

## 4. EEPROM utilization map — what the VIP actually reads the EEPROM for

34 named calibration items, string-verified (per-byte caller wiring stays behind the dispatch wall
above; only 2 of 48 candidate cal-string addresses have real code xrefs, so the *string list* is
solid but *which function reads each item* is unresolved) `[S]`:

- **`[SS_SWC]` × 32 — power/sleep/offmode vehicle-lifecycle configuration:** sleep/suspend/offmode/
  startup/flush timeouts, `cal_max_suspend_time_{1,2,3}`, `cal_str_mode_soc_min_threshold_{1,2,3}`,
  `cal_str_min_temp_threshold`, `cal_suspend_to_ram_en`, `cal_vin_relearn_en`,
  `cal_critical_state_of_charge_ignore`, `cal_cluster_animation_ignore`/`cal_rsi_animation_ignore`/
  `*_hmiready_ignore`, `cal_local_valet_timeout_sec`, `cal_master_offmode_active_timeout_min`,
  `cal_remote_reflash_programming_complete_timeout_sec`, etc. This is the EEPROM's primary VIP role.
- **`[J6_CDD]` × 2 — HMI/display:** `LngSelSignal` (language), `TimeDispFormat` (time format).
- **Security region:** the two SBI records (§2) plus the `0x40F-0x45A` calItem block (empirically the
  ADB-adjacent gate region).
- **Write path:** 15 string copies of `[CAL] EEPROM Write Failure for CalGroup-%d` — all with zero
  recoverable code xrefs (§3).

A candidate 8KB ring at `0xFEBDDE28` is a trace/log buffer, **not** the EEPROM shadow (recorded so it
is not re-mistaken) `[C]`.

## 5. Complete address/parameter table

Consolidated and corrected against: this doc's own §0-era code audit and empirical dump diffs, the
2026-10-15 `EEPROM_MAPPING_FABLE_REPORT.md` verification pass (findings A-H applied below — see §12),
`VIP_CONTROL_ANALYSIS.txt` §2/Appendix A, `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt` §3.3/§7, and
`AOSP_REPLACEMENT_RESEARCH.txt` Appendix B. Retracted rows from the pre-code-audit era are **removed**
here, not struck through — see §12 History for what was dropped and why.

### 5.1 Boot/init (0x0000-0x03FF)
| Address | Field | Evidence |
|---|---|---|
| 0x0000 | Boot complete flag, `0x69` marker + `0x01` data | `[I]` |
| 0x0001 | Boot state byte (absorbed from platform doc, 2026-11-21): `0x00`=virgin, `0x01`=normal, `0xFF`=corrupted | `[U]` — unsourced in the originating doc, not independently byte-matched here |
| 0x0020 | Secondary boot flag, `0x69` marker | `[I]` |
| 0x0060-0x0397 | 822-byte region a firmware descriptor says is all-zero; actually reads a deterministic 9-bit-period "walking-zero" bit pattern | `[U]` — read-glitch vs. an actual EEPROM cell/row fault undetermined; re-dump on physical hardware recommended if this unit is accessible |
| 0x03A0-0x03B1 | ECU-ID, 16 bytes, `0x69`-framed | `[C]` byte-exact vs SPSVCS.LOG `ECUID`, confirmed in two independent SPS sessions |

### 5.2 Security configuration (0x0400-0x04FF)
| Address | Field | Evidence |
|---|---|---|
| **0x0441** (markers 0x0440/0x0442) | **Primary SBI data byte** — 0xFF=bypass/0x00=locked | `[C]` — see §2 |
| 0x0460-0x0465 | HW part number (`ssecuhn`), BE u32 `85086705` | `[C]` byte-exact vs SPSVCS.LOG `ssecuhn` — **not** "Radio/Audio Settings" as earlier docs guessed |
| 0x0480 | A second part-number-shaped BE u32 (`84999439`) | `[U]` — not found in any available source log |
| 0x04A0, 0x04C0 | ~~"IPC Security Config #1/#2"~~ — **retracted, not security flags** | `[C]` retraction: `[IPC_S]` is the IPC *serial-transport* HDLC log tag ("IFRAME Rx", "HDLC: CRC Failed"), not "IPC Security"; the cited 17/11 firmware xref counts do not reproduce (actual instruction-level refs: 2-3) — grep/byte-pattern noise, not semantic xrefs. Ordinary calibration-group bytes. |

**0x0400-0x045F as a whole (absorbed from platform doc, 2026-11-21):** this range is the
security-configuration region and is deliberately outside CRC protection — modifications within it
are not detected by the (already not-boot-enforced, §8) CRC mechanism `[I]`.

### 5.3 Device identification / manufacturing (0x0500-0x06FF, plus 0x14A0)
| Address | Field | Evidence |
|---|---|---|
| 0x0500 | MTC traceability-code tail (last 9 of 16-digit MTC) — **not** "Part Number" | `[C]` digit-exact vs SPSVCS.LOG `mtc`/`infokey` |
| 0x0580 | Programming date (manufacture) | `[S]` |
| 0x05A0-0x05AF | CVPPS value (e.g. `7310500000000X`) | `[C]` bytes read from dump; **meaning unresolved** — "Serial Number" vs "Calibration File ID" naming conflict across source docs, not settled here |
| 0x05C0-0x05D1 | VIN, 17 bytes | `[C]` |
| 0x0680-0x0689 | Shop/dealer code (UDS DID F198, `shopcode`) | `[C]` = `9999988888`, a 10-char truncation of the logged 11-digit value |
| 0x06A0-0x06A5 | Reprogram date (UDS DID F199), BCD | `[S]` e.g. `2026-09-28`; can post-date the most recently *logged* SPS session, implying a later unlogged reprogram |
| 0x06E0-0x06E5 | Second HW part-number word, `60 02 02 B1` | `[C]` matches VIP boot-log line "Send HW Partnum 0x60 0x2 0x2 0xb1" — unidentified in every earlier pass |
| 0x14A0 | VIN-tail residual — **not** a "Firmware ID" | `[S]` mirrors whichever VIN was active when its NvM block was last written; can go stale (retain a *previous* vehicle's VIN tail) after a re-VIN/reprogram event — proven by comparing two SPS sessions on one ECUID where the module changed vehicles |

### 5.4 Backup security & feature flags (0x0A00-0x0BFF)
| Address | Field | Evidence |
|---|---|---|
| 0x0A00 | Structure base address — **not a flag** | `[C]` retraction of an earlier "871 xref" claim (fabricated/non-reproducible) |
| **0x0A81** (markers 0x0A80/0x0A82) | **Backup SBI data byte** — 0xFF=bypass/0x00=locked. Sample full-record values (absorbed from platform doc, 2026-11-21): stock/uninitialized = `FF FF FF`; ADB-bypass = `5A FF 5A FF`; post-Y181-reflash (re-locked) = `F0 00 F0` | `[C]` — see §2 |
| 0x0A40, 0x0AC0, 0x0BE0 | ~~"Feature enable" / "late-region flag (danger zone)"~~ — **retracted** | `[C]` retraction: all three cells read all-`0xFF` (unwritten) in *both* stock and ADB-enabled dumps — no stored data at all, and the cited 28/14/24 xref counts do not reproduce. Not OTP, not a lock, not a flag. |
| 0x0AA0, 0x0AE5 | Candidate trim/model byte pair (channel (b), §9) — HC=`0xF0`, LTZ=`0xC3`, stock=`0x69` | `[U]` unconfirmed bench hypothesis; not a clean verbatim 1/16 GMTrim-enum decode, possibly obfuscated. Weak independent corroboration: a separate stock-vs-ADB-enabled diff recorded `0x0AA0: 69 00 xx → C3 00 xx` ("frame type change") in a different dump pair — consistent with a non-security, unit-varying byte at this offset, not confirmation of the trim hypothesis. |
| 0x0B00 | Feature structure base — **not a flag** | `[C]` retraction of an earlier "311 xref" claim |
| **0x0B41** (marker 0x0B40) | Member of five-cell CalGroup `0xA3` (`0x0B3E–0x0B42`), not a “Debug Mode” field | `[C]` raw Y175 Dispatcher A calls `FUN_0009414A` at `0xBA48A`; that function copies `0x0B41` to a temporary group buffer at `param+6` and returns a generic validity status. The per-group reconciliation path then writes that status to VIP RAM `0xFEBD39BF` (Dispatcher B case `0xBAA6A`). `FUN_000BB0FE` consumes it through ordinal→status accessor `FUN_000B866C`, compares generic validity states, and invokes generic validation/repair dispatchers. No instruction in the traced path branches on the byte or maps it to debug/ADB/SELinux; no export of this RAM status to eMMC-side software was recovered. `[O]` tests at `0x00`/`0x01`/`0xFF` observed no ADB, UI, or logged change. Its semantic field purpose remains unknown; its demonstrated end result is CalGroup read/validation/repair-state handling only. |

### 5.5 Display/UI & power-thermal struct (0x0E00-0x0EAF)
A single ~34-field struct. Only the **last 7** fields are confirmed against named VIP_APP firmware
constants (`cal_str_min_temp_threshold`, `soc_min_threshold_1-3`, `max_suspend_time_1-3` @
`0xf8126-0xf8141`) `[C]` — i.e. this struct is at least partly power/thermal/suspend-timer
calibration, **not** purely display/UI as first guessed. The other 27 fields (screen timeout `0x0E01`,
brightness threshold `0x0E09`, touch/gesture/animation timers, etc.) are **unconfirmed** `[I]`, and at
least one specific mapping (`cal_startup_delay_wait_timeout_msec`) was tested and is **wrong**.

- 0x0E80-0x0EAF — UI Flags Block, sample `5A 03 01 01 01 01 01 00 00 2C 01 00 00 01 00 00` `[I]`.
  Candidate individual-bit guesses (untested, `[U]`, from `AOSP_REPLACEMENT_RESEARCH.txt` Appendix B):
  `0xE82` touch input, `0xE83` haptic feedback, `0xE84` UI sound effects, `0xE85` transition
  animations, `0xE86` auto-brightness, `0xE87`/`0xE88` reserved (possible hidden feature).

### 5.6 Display calibration tables (0x0EC0-0x0F7F)
| Address | Field | Evidence |
|---|---|---|
| 0x0F00-0x0F3F | Brightness LUT (11-point) | `[S]` |
| 0x0F40-0x0F7F | Color/ambient calibration | `[S]` |

### 5.7 Backlight/display-dimming calibration tables (0x0FE0-0x12DF)
Corrected 2026-10-15; **was** mislabeled "Audio/Radio Tuning Tables" (Volume Curve / Fade-Balance /
EQ-DSP) in every prior pass. Byte-matched in *shape* (not byte-identical — different numeric
encoding) against VIP_APP firmware LUT defaults at `0xf8414-0xf8500`: 4 channels sharing one input-%
axis, each with its own output gamma curve (0-65535) `[S]`.

| Address range | Was labeled | Actually |
|---|---|---|
| 0x0FE0-0x103F | "Volume Curve" | Backlight dimming curve (11-point) |
| 0x1040-0x109F | "Fade/Balance Tables" | Backlight dimming curve (22-point) |
| 0x10A0-0x12DF | "EQ/DSP Calibration" | Backlight dimming curve, 4-channel, 576 bytes |

### 5.8 Other untested/unconfirmed offsets (completeness only)
From `AOSP_REPLACEMENT_RESEARCH.txt` Appendix B, carried over from an earlier pre-code-audit analysis
and never individually tested: `0x0B80` (frame `0xF0`), `0x0BC0` (frame `0x69`), `0x1500` (frame
`0x69`) — "unknown feature" guesses with no code or empirical confirmation `[U]`. Not prioritized;
most of this region's higher-confidence candidates from the same era (`0x04A0`/`0x04C0`/`0x0A40`/
`0x0BE0`) are the ones retracted in §5.2/§5.4 above.

Additional untested offsets, retired from `eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (folded in
2026-11-21): `0x0040` ("Hardware revision marker"), `0x0C00` ("Unknown, ACTIVE in sample dump"),
`0x1A00` ("Tertiary Security" — bypass value never specified, locked value `[M] 00 [M]`) — same
status: no code or empirical confirmation `[U]`.

## 6. Checksums & integrity fields (0x16E0-0x1FFF)

| Address | Name | Sample | Status |
|---|---|---|---|
| 0x16E0 | Primary integrity block | — | See structure note below |
| 0x19E0 | Secondary integrity block | — | See structure note below |
| 0x1A80 | "Config CRC" (uint24 LE, sample `0x000107`) | — | `[U]` coverage scope unclear; a separate source doc reads this address as a MEC-related NVM value instead — interpretation conflict, unresolved here |
| 0x1B40 | Third integrity block | — | See structure note below |
| 0x1B60, 0x1B80 | "Block CRC #1/#2" vs. "reflash/programming counters" | sample `0x00000001` both | `[U]` interpretation conflict between source docs, unresolved |
| 0x1DC0-0x1DD3 | Two 32-bit timestamp-shaped fields + CRC-16 | — | `[C]` for the CRC, `[I]` for the timestamp semantics — see below |

**Structure (0x16E0/0x19E0/0x1B40, confirmed 2026-10-15):** each decodes as `[00][2-byte version/
generation word][2-byte hash word]`, not a flat 32-bit CRC as first guessed `[S]`. This 5-byte
integrity-at-a-different-address structure is **not** an AUTOSAR NvM construct — AUTOSAR appends CRC
to the *same* NV slot as its payload (SWS_NvM_00522); origin is undetermined vendor Fee/Ea bookkeeping
or an application-level SWC.

- **Algorithm — split verdict.** `0x1DC0`: **CONFIRMED** CRC-16/CCITT-FALSE (poly `0x1021`, init
  `0xFFFF`, no reflect, no output XOR, little-endian) by byte-match, independently reproduced across 5
  images and independently re-verified by `EEPROM_MAPPING_FABLE_REPORT.md` the same day (stored
  `0xBFD4` = computed `0xBFD4` on payload `0130000000016abb1116016abb12bb01`) `[C]`. **`0x16E0`/`0x19E0`/
  `0x1B40`: algorithm and input-byte-range are UNRESOLVED** — proven *not* CRC-16/CCITT-FALSE of the
  version word alone (`0x16E0` and `0x1B40` can share the same version word, e.g. bytes `00 58`, while
  carrying *different* stored hash bytes, `0x9896` vs `0xAD9B` — one CRC input cannot produce two
  outputs) `[C]` by refutation. This is the **highest-priority open item blocking safe edits** to
  anything these three blocks cover — the only known-safe approach is template preservation: edit a
  known-good dump, touch only the SBI data bytes, leave these fields byte-for-byte as shipped (known
  to work for the single-byte `0x0441` flip).
  - Note: the shared version word above is the same two bytes (`00 58`) that earlier passes labeled
    inconsistently as `0x5800` vs `0x0058` (opposite endianness readings of the same bytes, from
    different docs). The structural conclusion (0x16E0 and 0x1B40 share it, 0x19E0 differs) holds
    under either reading; this doc standardizes on `0x5800` (big-endian-of-storage reading) to match
    its own §5.7-adjacent conventions, but a reader should treat the two labels as the same evidence.
- **Version/generation word:** clusters tightly across blocks but not in exact lockstep (±1 drift
  observed in 2 of 5 images checked); observed to step `0x0013→0x0104` across one reflash. Plausibly a
  shared calibration-generation counter; not pinned to a specific meaning `[I]`.
- **0x1DC0-0x1DD3 timestamps:** the gap between the two 32-bit fields is **not** a fixed Δ=1 — an
  independent brute-force check across 5 real EEPROM images found the gap varies 11-13799 seconds; one
  unit's dump happened to show Δ=1, which is not representative `[C]` by refutation of the earlier
  "sequence pair" reading.

## 7. AUTOSAR NvM block-descriptor structure (firmware-side, governs how the EEPROM is organized)

The VIP_APP firmware carries a 183-entry, 12-byte-stride descriptor table at `0x2475A-0x24FEE`:
`[u32 LE rel_addr][u16 LE payload_len][u8 type_byte][u8 copies][u32 0]`.

| Field | AUTOSAR parameter | Status |
|---|---|---|
| `rel_addr` (u32 LE) | role only resembles `NvMNvBlockBaseNumber` | Implementation-specific byte offset, not a spec-defined byte-address formula; all 183 entries have high 16 bits = `0x0000` (flat address, no embedded block ID) |
| `payload_len` (u16 LE) | `NvMNvBlockLength` | Stored payload length |
| `type_byte` (u8) | **none — vendor constant** | Invariant `0x01` across all 183 entries (including `copies=2` entries) — cannot carry management type; likely a format-version/valid flag |
| `copies` (u8) | `NvMNvBlockNum` (ECUC_NvM_00480) | **The real management-type discriminator**: `1`=NATIVE, `2`=REDUNDANT, `1..255`=DATASET (per AUTOSAR_SWS_NVRAMManager R22-11 `nvm.txt:7929-7940`). Caveat: `copies=2` alone is ambiguous between REDUNDANT and a 2-entry DATASET block without `NvMBlockManagementType`, which is **not** in this 12-byte descriptor. |
| trailing `u32 0` | unassigned, possibly `NvMRomBlockDataAddress`=NULL | Constant zero in every entry |

- **AUTOSAR defines no numeric values** for `NvMBlockManagementType` (ECUC_NvM_00062) — only symbolic
  literals `NVM_BLOCK_NATIVE`/`REDUNDANT`/`DATASET`; there is no "SINGLE" literal (the term is NATIVE).
  An earlier revision of this analysis invented a "SINGLE=0, REDUNDANT=1, DATASET=2" mapping — that is
  **wrong** and is retracted.
- **AUTOSAR defines no C struct** for the descriptor table; `NvM_BlockDescriptorType` is
  implementation-defined. The 12-byte layout's *size* (not its field semantics) is consistent with
  Renesas CC-RH natural struct packing (R20UT2846EJ ABI).
- **The `[marker][payload][marker]` EEPROM record framing is not an AUTOSAR NvM concept.** AUTOSAR NvM
  only defines an optional leading Static Block ID header (`NvMStaticBlockIDCheck`) and an optional
  *appended* per-block CRC — never leading+trailing markers. This framing belongs to the Fee/Ea layer
  below NvM, or is Harman-custom.
- **The 0x0400/0x0420 pair is the one and only `copies=2` descriptor entry** — standard AUTOSAR
  `NVM_BLOCK_REDUNDANT` behavior (both physical copies kept in sync, backup used on read failure).
  This is **distinct from the SBI primary/backup pair** (`0x0441`/`0x0A81`), which sit in two separate
  descriptor entries and are an application-level mirror, not an AUTOSAR REDUNDANT block — a GM_research
  sibling-tree doc outside this corpus miscites the SBI pair as the REDUNDANT entry; that is a factual
  error against this doc's own ground truth (per `EEPROM_MAPPING_FABLE_REPORT.md` finding B, out of
  scope to edit from here).
- **Melching Toyota-header hypothesis: REFUTED.** Willem Melching's (DEF CON 30) Toyota RH850 NvM
  research describes a 2-byte block-ID-first header. Tested against all 183 entries here: every
  `rel_addr` has high 16 bits `0x0000` — a flat address with no embedded block ID. Does not transfer to
  this unit.
- **Candidate marker-byte "type" mapping (absorbed from platform doc, 2026-11-21):** a per-byte
  type taxonomy was proposed for the four observed marker values — `0x5A`=Security, `0x69`=
  Configuration, `0xF0`=Data, `0xC3`=Calibration. This is **unsourced/untested** in the originating
  doc `[U]`; it is not confirmed against code and should not be treated as more than a naming
  convention someone applied to the observed marker quartet. §2 records that marker values are not a fixed signature (they vary by unit and CalGroup). It is consistent with, but adds no
  independent confirmation to, the marker-framing quartet finding below.
- **SBI `0x00`/`0xFF` polarity is a cross-platform RH850 convention, not Harman-specific** — matches
  the Nissan Leaf RH850 Virgin status byte (RAM `0xFEDE0C03`, same `0x00`=locked/`0xFF`=bypass)
  documented in CVE-2025-32058 (Black Hat Asia 2025). The INC-protocol port map (base `0xc700`,
  `NET_BROADCAST=0xc70f`, `DOWNLOAD=0xc70b`) is independently confirmed in VIP_BOOT at 4 instruction
  sites (`ori 0xc700,r0,r1` at `0x0001b6c2`/`0x0001b9ac`/`0x00083510`/`0x000837fa`) and also appears in
  the CVE slides. The marker-framing quartet (`0x69`/`0xF0`/`0x5A`/`0xC3`) and the CalGroup dispatch
  table are original to this research with no published Harman byte-level documentation.

## 8. I2C bus access & hardware attack surface

**Bus permissions** (from `/dev` enumeration, absorbed from `VIP_CONTROL_ANALYSIS.txt` §8):

| Device | Permissions | Owner | Access |
|---|---|---|---|
| `/dev/i2c-0` | `crw-rw-rw-` | root:root | **WORLD READABLE/WRITABLE**; general purpose; candidate bus for the EEPROM (M24C64 at `0x50`) — **unconfirmed**, see the open question below `[U]` |
| `/dev/i2c-1` | `crw-rw-rw-` | root:root | **WORLD READABLE/WRITABLE**; general purpose, ELMOS antenna controller |
| `/dev/i2c-2` | `crw-rw-rw-` | system:system | system access; system bus |
| `/dev/i2c-3` | `crw-rw-rw-` | audioserver:audioserver | audio access; TDF8532 codec control |
| `/dev/i2c-4/5/6/8/9/10` | `crw-------` | root | root only; reserved |
| `/dev/i2c-7` | `crw-rw----` | system | system access; Atmel maXTouch (`0x4B`) touchscreen |

**SELinux labels and live confirmation (absorbed from platform doc, `[C]` live-Y175 2026-10-05,
`dev_listing.txt`):** `i2c-0` `u:object_r:saturnhd_device:s0`; `i2c-1/2` `i2c_device`; `i2c-3`
`dirana3_device`; `i2c-7` `display_panel` (**not** `i2c_device`, correcting some prior copies'
implication). All of `i2c-0/1/2/3` confirmed mode `0666`; `i2c-4/5/6/8/9/10` confirmed
`crw-------` root; `i2c-7` confirmed `crw-rw---- system`. **Additional device:** a faceplate
controller at `0x12` sits on `i2c-7`, the same bus as the touchscreen; no GYRO/ACCEL sensors are
present on this platform.

**Live-capture limits:** the EEPROM-at-`0x50` contents, CRC-not-enforced, and SBI-flag claims in this document remain **UNVERIFIABLE-FROM-LIVE** — the originating disk-only audit did not (and must not) i2c-probe the live device. The `[C]` live-Y175 evidence in this document covers only device-node modes/labels, Android properties/shell context, and world-writable-node enumeration — not EEPROM contents or the VIP/MEC chain.

**Open question, never closed:** which bus (if either world-accessible one) connects to the M24C64,
and at what I2C address (candidate `0x50-0x57`) — raised independently by `VIP_CONTROL_ANALYSIS.txt`
§8.2, `HARDWARE_HYPERVISOR_ATTACK_VECTORS.md`'s EEPROM-I2C table, and
`T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` §4 — all three treat it as the key unresolved
software-bypass question and none closes it `[U]`.

**SELinux correction (supersedes all three source docs' original "may be permissive" framing):** no
stock build runs SELinux permissive — Y177 and Y181 both run **ENFORCING** (`security/KERNEL_CVE_
ANALYSIS.txt` Appendix E.8, carried by the kernel-CVE security tree outside this corpus). I2C device
access is SELinux-gated on all stock builds; `i2cdetect`/`i2cget`/`i2cset` from a shell are expected to
be denied regardless of the world-writable device-node permissions above. World-accessible node
permissions are therefore **necessary but not sufficient** for a software-only bypass.

**CRC is not boot-time-enforced (empirical, `VIP_CONTROL_ANALYSIS.txt` §3.4):** setting the VIN field
(`0x05C0-0x05D1`) to all `0xFF` still booted into AAOS normally — no factory reset, no boot failure, no
observable behavior change. CRC validation, if it exists at all for that region, is not checked at
boot; it may only apply during OTA/SPS programming or dealer service modes. This is consistent with,
and corroborates, §2's finding that the single-byte `0x0441` SBI flip needed no CRC recompute.

**EEPROM-I2C attack-vector catalog** (absorbed from `HARDWARE_HYPERVISOR_ATTACK_VECTORS.md`'s EEPROM
I2C table; that doc keeps a pointer here and retains its own priority-matrix/tool-shopping-list
framing):

| Attack | Difficulty | Value |
|---|---|---|
| Passive I2C sniff (logic analyzer on SDA/SCL) | Low | Directly observes which offsets the VIP reads at boot — resolves which structure-base region (§5.4) is actually touched |
| Active interposer (dual-bus, transparent proxy) | Medium | Injects modified bytes on read; VIP receives attacker-controlled data without desoldering the M24C64 |
| Full EEPROM emulation (RP2040 replaces M24C64) | Medium | Pre-loaded with modified image, all flags pre-flipped, USB interface for hot-update |
| Write-blocking interposer (suppress EEPROM writes) | Medium | Prevents the VIP from re-asserting lock bytes after a session — persistent unlock across reboots |
| Byte-mutation profiling of structure-base regions | Medium | Systematically mutate one byte per session via emulator to map the `0x0A00`/`0x0B00` structure-base regions (§5.4) without firmware source |

Note: the above table's framing of "the `0x0A00` mystery" / "871-ref data structure" predates this
doc's own §5.4 retraction of that reference count as fabricated; `0x0A00`/`0x0B00` are structure-base
addresses, not single flags — the sniff/profiling value above still holds, just against a
mapping-the-structure goal, not a single-byte-flag goal.

**Physical reference:** chip is located near the VIP MCU on the PCB; a Pomona-clip-class programmer
(e.g. XGecu) is sufficient for offline read/write without a logic-analyzer tap.

### 8.1 GPIO, serial, and kernel attack-surface findings (absorbed from platform doc, 2026-11-21)

This subsection folds in the platform-tree doc's GPIO/serial/kernel findings for the DAC-level
local hardware attack surface (I2C/GPIO/serial), which this doc previously did not cover. All
builds examined (Y175/Y177/Y181) run SELinux **enforcing** — an earlier "Y177 permissive" premise
is retracted; the DAC-level (file-mode) exposures below exist on all builds regardless of SELinux
mode, which instead constrains which SELinux *domains* may reach them.

**GPIO (MCU reset/boot-mode control, `gpio458/460/464/466`):** originally claimed world-writable,
letting any user-space process force the VIP MCU into reset/bootloader mode. **REFUTED on
captured evidence** (`[C]` live-Y175 2026-10-05): the GPIO char devices `/dev/gpiochip0-3` are
`crw-------` root (0600) — root-only, not world-writable. The `gpio458/459/460/463/464/466`
entries under `/sys/class/gpio/` are themselves **symlinks** (`lrwxrwxrwx`), and symlink mode bits
are always `0777` with no access meaning. `world_writable.txt` enumerates exactly two
world-writable nodes on the live unit — both stock memcg `cgroup.event_control` — and no GPIO
path. Direct capture closed the remaining gap: `ls /sys/class/gpio/gpio{458,460,464,466}/` returns
`Permission denied` to shell (uid 2000), and `export`/`unexport` read back as `?` (root-only) — the
value/direction nodes are not stat-able, let alone writable, by a non-root process. A non-root
process cannot toggle these pins; second-agent concurrence obtained 2026-10-05 (14-flip ledger).

**IPC/Serial:**
- `/dev/ttyS1` (1 Mbps, HDLC v16, 20 IPC channels to the VIP MCU — channel-count/speed detail
  itself `[U]`/unverifiable-from-live): owner `root:root`, SELinux `ipc_serial_device` confirmed,
  but mode is **`crw-------` (0600, root-only)** `[C]` live-Y175 2026-10-05 — **not**
  world-accessible as an earlier pass had documented; the IPC link to the VIP is DAC-closed.
- `/dev/ttyACM1`: `crw-rw-rw-` (0666, world-rw) confirmed, owner root, but SELinux label is
  **`sxm_device`** (SiriusXM tuner serial) `[C]` live-Y175 2026-10-05 — an earlier "Debug UART"
  label for this node is **REFUTED**. No `/dev/ttyACM0` is present on this unit.

**Kernel exploitation surface (pointer only — owned by `../../platform/security.md`'s Key CVEs
section, not restated here):** unpatched-kernel exposure (CVE-2024-53104, -36971, -53150, -53197)
tracks the build's kernel version/patch level, not SELinux mode; SELinux enforcing on all builds
means MAC containment (neverallow rules) applies equally regardless of build. CAP_BPF plus SELinux
domain restrictions apply to the BPF verifier bypass (CVE-2023-2163) on all builds.
`CONFIG_SECURITY_YAMA` is not set, so ptrace scope is unrestricted at the YAMA layer on all builds;
SELinux domain rules still apply on top of that.

**Persistence:** EEPROM SBI state persistence is already covered in §2 (bulk restore-to-ROM-defaults
path can re-lock the cells after re-validation) and `0x0B41`'s non-debug-mode disposition is
covered in §5.4 — not restated here.

## 9. Trim/theme calibration channel (channel b) — SoC side, code-verified

A second, independent EEPROM-adjacent channel exists alongside the SBI/ADB channel (a): the vehicle's
trim/model/brand drives the AAOS boot animation and UI theme. Code-traced SoC chain: `calserviced`
(HIDL `vendor.gm.calibrations@1.0::ICalibrationService`, backed by `VIPCALPAL` over IPC — **it gets
GMTrim/GMModel/GMBrand from the VIP, not from this EEPROM directly**) → `/system/bin/animengine`
computes an integer AnimFlavor from the three IDs (log format `GMTrim: %d, GMModel: %d, GMBrand: %d ->
AnimFlavor:%d`) → loads `/product/ro/anim/<N>/{graphics,audio}/…` → caches in
`persist.sys.anim.flavor`; `/vendor/bin/hw/plmanager` triggers playback. Brand RRO overlays key on
GMBrand only (make-level — High Country and LTZ share the Chevrolet theme) `[C]`.

Enum values (from `/vendor/calibrations/CalSets.db`): GMTrim HighCountry=1, LTZ=16; GMModel
Silverado=4; GMBrand Chevrolet=3 `[S]`.

**The EEPROM→GMTrim translation, if it exists, is on the VIP side** (same unlocated-reader territory
as §3) — the SoC only receives the already-resolved GMTrim over IPC, and a raw `(1,16)` GMTrim byte
pair appears nowhere in an 8KB dump, confirming the enum is not stored verbatim here `[C]`. The
candidate offset pair `0x0AA0`/`0x0AE5` (§5.4) remains an unconfirmed bench hypothesis for this
channel.

**Observation harness** (for flip-and-observe bench work once ADB is live via §2):

| Check | Shows |
|---|---|
| `adb logcat \| grep -i AnimFlavor` | Live `GMTrim/GMModel/GMBrand → AnimFlavor` at boot — reveals whether a flipped byte changed what the VIP reports |
| `getprop persist.sys.anim.flavor` | Active AnimFlavor index |
| `adb logcat -s calserviced`; `lshal \| grep -i calibrations` | VIP-sourced calibration values |
| `cmd overlay list` | Brand RRO (GMBrand) state |
| `ls /product/ro/anim` | Shipped flavor folders |

**Data-quality note:** one source dump (`Y181_ADB_enabled_HC.bin`) is valid only through `0x0B43`; past
that it is flat zero-fill (~65% blank). Re-dump the full 8KB before trusting any offset past `0x0B43`
in material sourced from that specific dump.

## 10. Guest-side ADB / MEC / reflash-security chain (pointer)

The complete SoC-side chain — `GMAuthManagerService`, the GM-cloud-signed ADB policy,
`gm_adb_auth_init`/`is_secure_mode`, MEC per-unit boot-log readings (Y175 stock `0x0`, bench-bypassed
`0xFF`), and the DID `0xF1A0` transmission/root/registration-limit analysis — is owned by
[GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md §2.3.7](../boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).
This doc continues to own EEPROM layout and VIP binary analysis only; do not restate that chain here.

One EEPROM-relevant fact worth stating at this seam: the VIP's DID `0xF1A0` (the MEC value it
transmits) does **not** appear in the extracted `vip_app_strings.tsv` INT_DID list (which runs
`F0F3/F0F4/F190/F198/F199/F1CB/F1CC/F1DB/F1DC/F0AB/41EB/4782/4787/F09A/F0B4`) — the "`0xF1A0` =
Manufacturer Enable Counter" binding rests on the RH850 boot-UART log evidence cited at
GBUR §2.3.7, not on this firmware string export (`EEPROM_MAPPING_FABLE_REPORT.md` finding E, applied
here as a caveat rather than a contradiction — the boot-log evidence is independent corroboration, not
undermined by the string-table gap).

### 10.1 `SIGNATURE_BYPASS_TICKET` / `SECURE_UNLOCK_LEVEL` reflash-security primitives

This detail was previously pointered to GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md §2.3.7 and
`../../platform/ota_update_stack.md`/`ota_programming_roles.md`; neither target carries it, so it
is kept here.

`SIGNATURE_BYPASS_TICKET` (DID CUSTOM 18, CAN) is issued by the VIP via `VIPRequestManager` and
trusted **presence-only** by the OTA installer: `isSignatureBypassTicketPresent()` returns
`payload > 0` with no signature/nonce/MAC check, and `DelayedWKSApp`'s `ModulePart.verify()`
accepts a development-signed `VIP_APP` (module ID 1) or `VIP_BOOT` (module ID 71) package on
that basis alone (Java, paraphrased from the decompile):
```
if (moduleId == 1 || moduleId == 71) {
    if (isSignatureBypassTicketPresent()) return VERIFIED; // presence-only, no crypto check
}
```
`SECURE_UNLOCK_LEVEL` (DID CUSTOM 17, Ethernet) is dead code —
`DiagnosticDispatcher.getSecurityLevel()` has no caller — exposing a graded enum ladder
(`None=0` ... `EndOfLife=95`) that is never read by any reachable path. `AllowDevSignedVIP` is
a debug-build-only SQLite flag, a separate mechanism from `UpdateService`'s own unrelated
dev-signing flag of the same name (do not conflate the two).

Empirically (`ecu80_READ.Txt`): the CSM's own `$27` seed comes back all-`0xFF` in the SBI-bypass
state. Closing the loop: EEPROM SBI flip (§2) trivializes the VIP's `$27` response -> the
ticket-present check passes with no cryptographic gate -> a development-signed `VIP_APP`/
`VIP_BOOT` package is accepted by the OTA installer. This is a reflash-security claim about the
OTA/update-engine path, not an EEPROM fact per se, which is why it was pointered out in the
first place — but since no OTA-topic doc currently carries it, it stays here until one does.

## 11. Calibration `$27` gate — open question (pointer)

Whether the ADB SBI flip (§2) also opens the calibration/diagnostic UDS `$27` SecurityAccess gate
(the lever behind calibration writes such as `SCREEN_RESOLUTION`) remains **open**. What is
established:

- ADB path: VIP PROTOKEY module, reads EEPROM SBI, returns all-`0xFF` seed when SBI=bypass — confirmed
  by disasm + CAN capture (§2).
- Calibration path: SoC `diagnosticsd`'s own SecurityAccess handler — **a different code path**, not
  proven to share a single EEPROM-stored flag with the ADB path (`CALDEF_VIP_CALIBRATION_ANALYSIS.txt`
  §6.1 independently confirms the ADB-side mechanism and corroborates that CalDef calibrations
  (`DEVICE_REGISTRATION_ENABLE_CHECK_OVERRIDE`, `EXPIRATION_ENFORCEMENT`, `GIS763_PROGRAMMING_ENABLED`,
  `SECURITY_EVENT_LOGGING_ENABLED`) do **not** affect ADB authentication — a one-way confirmation, not
  a mechanism-sharing proof).
- The historically-proposed "different flag" candidates for the calibration gate (`0x04A0`, `0x04C0`,
  `0x0A40`, `0x0BE0`) are the same four retracted in §5.2/§5.4 — they hold no data at all, so they
  cannot be the answer.
- The live-T1 Ethernet correction for this specific gate (31-byte all-FF seed, 12-zero-byte response
  accepted with `67 02`) is owned by
  [`../../diagnostics/diagnosticsd_security_access.md`](../../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14) —
  do not restate it here.
- In-band path if proven: if either world-writable I2C bus (§8) reaches the M24C64, an ADB shell
  (obtained via the §2 SBI flip) could probe for a separate calibration-gate flag without a hardware
  programmer — contingent entirely on the unresolved bus-mapping question in §8.

**Practical implication:** do not assume the ADB SBI flip opens the calibration gate. They share the
VIP/EEPROM anchor layer, not a proven single flag.

## 12. History (consolidated — replaces this doc's earlier scattered inline correction notes)

This doc was originally four merged sources (Dec-2025 raw byte map, Jan-Feb-2026 firmware-xref pass,
and two Aug-2026 convergence docs) and was corrected in place many times since. Each dated entry below
states what changed and why; it replaces roughly a dozen repeated parenthetical "[corrected
2026-11-12: ...]" notes that had accumulated at the point of use throughout the prior revision instead
of being fixed once.

- **2026-08-17** — Original audit assembled from 4 sources; heavy speculative "security flag" taxonomy
  (0x0440/0x0A80 as fixed ADB addresses, 0x04A0/0x04C0/0x0A40/0x0BE0/0x1A00 as additional "security flags"
  with firmware xref counts).
- **2026-08-25** — Code audit falsifies most of that taxonomy: xref counts (871/311/17/11/28/24) do not
  reproduce (actual instruction-level refs: 2-3); `[IPC_S]` is a serial-transport log tag, not "IPC
  Security"; "disasm-confirmed" for 0x0440/0x0A80 is unsupported — only ordinary calibration handling
  found at those literal addresses.
- **2026-08-26** — VIP_BOOT fully disassembled and ruled out as the EEPROM reader (§1); VIP_APP's
  CalGroup dispatcher found and decoded (§3); the real SBI isolated empirically via dump diff
  (`0x0441: 00→FF`, §2); the ADB-chain attribution corrected from the VIP `$27` validator (`0xb67d0`)
  to the SoC-side MEC/`is_secure_mode` path (propagated from here into `AOSP_REPLACEMENT_RESEARCH.txt`
  §5.2, `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt` §3.3, `CALDEF_VIP_CALIBRATION_ANALYSIS.txt` §6.1, and
  `PROJECT_MASTER_CHECKLIST.txt`, all dated 2026-09-26); channel (b) trim/theme pipeline traced (§9);
  the EEPROM-utilization map (§4) and the static-RE-exhausted conclusion (§3) reached.
- **2026-09-10** — ELK/reboot trigger (VIP Channel-7, RID `0xFF01`, `FUN_000641c2`@`0x64208`) located
  during a fresh RH850 pass; owned by `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`/
  `HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` — noted here only because the same disassembly pass touched
  this EEPROM's security region.
- **2026-10-15** — `EEPROM_MAPPING_FABLE_REPORT.md` verification pass (findings A-H) plus an
  independent clean-room triple-pass dump verification (§5.1/§5.3 offset corrections: 0x14A0 VIN-tail
  not firmware ID, 0x0FE0-0x12DF backlight not audio, 0x0460 HW part number not radio/audio, new
  0x03A0/0x0680/0x06A0/0x06E0 offsets) and the AUTOSAR NvM descriptor-table decode (§7, Melching
  hypothesis refuted). **Finding A (the governing correction for this revision): the backup SBI data
  byte is `0x0A81`, not `0x0A80`; `0x0A80`/`0x0A82` are its marker bytes.** The prior revision's own
  "CONFIRMED ADB RECIPE" line had drifted back to the wrong address and self-contradicted its own
  AUTOSAR/clean-room sections — **this is Open Conflict item 4 in the reorg plan's routing list, and it
  is settled by this entry**: §2 above states the corrected, final form directly, with no surviving
  "earlier text said X" parenthetical. Findings B/C/D/F/H concern documents outside this corpus
  (a GM_research sibling-tree copy, an `icloud_eeprom/` stale copy, a `diagnostics/gm_dps/` copy, and a
  V850-vs-RH850 symbol-drift note in a write-trace doc) and are not actionable from this file — noted
  in the ledger, not fixed here. Finding E (MEC acronym) is applied at §10. Finding G (endianness
  label) is applied at §6.
- **2026-10-16** — CRC algorithm split-verdict reached: `0x1DC0` confirmed CRC-16/CCITT-FALSE
  (independently re-verified the same window by the Fable report's own Python recomputation); `0x16E0`/
  `0x19E0`/`0x1B40` proven *not* that algorithm over the version word alone — still unresolved (§6),
  the Fable report's own "highest-priority open question."
- **2026-11-12** — Y181 VIP boot-log line-count recount corrected (internal arithmetic fix, not a
  finding change); the scattered "0x0A80" labels that had not yet inherited the 2026-10-15 correction
  were patched in place at the time, then re-collapsed into §2's single clean statement in this
  revision.
- **2026-11-14** — Live T1 Ethernet SecurityAccess correction for the calibration `$27` gate lands in
  `../../diagnostics/diagnosticsd_security_access.md`; this doc's §11 updated to point there instead of
  carrying the (now-superseded) NRC `0x10`/invalid-tester-ID reading.
- **2026-11-21** — Resolved the duplication this doc had flagged (§0 "Known discrepancy"):
  `../../platform/eeprom_i2c_security.md` is trimmed to a short pointer plus its own live `[C]`
  capture citations (SELinux device-node labels, Android security posture). Every fact it
  previously carried that was not already present here was folded in: the `0x0441`/`0x0A81`
  address-identity error that platform copy still carried (`0x0A80` cited as the backup SBI data
  byte, rather than its marker) is not propagated here — this doc's own Finding A (2026-10-15,
  above) already stated the corrected `0x0A81` identity and remains authoritative. New material
  absorbed: the `0x0001` boot-state byte guess (§5.1), the `0x0400-0x045F` CRC-exclusion framing
  (§5.2), backup-SBI sample record values across stock/bypass/post-reflash states (§5.4), the
  marker-byte "type" naming convention (§7), SELinux device-node labels and the faceplate
  controller/no-GYRO note for the I2C table (§8), and a new §8.1 covering GPIO, serial
  (`ttyS1`/`ttyACM1`), and kernel-exploitation findings that this doc did not previously carry.

**Dropped/out-of-scope corrections noted for completeness (not applied here):**
`EEPROM_MAPPING_FABLE_REPORT.md` findings B, C, D, F, H all name defects in documents outside this
reorg's 49-file research/ corpus (an external sibling tree, a stale copy in another external
location, a third external copy, and a V850/RH850 symbol-drift note) —
see the ledger for the full list; they are not fixed by this pass.
`AUG24_25_DOC_REVIEW_CORRECTIONS_AUG2026.md` item 2 (2026-08-25) proposed that the dual-SBI,
both-bytes-must-match mechanism had zero code references and that the real storage was a single
14-byte CalGroup block (`0x43a-0x447`) — this was an intermediate, code-RE-only reading that the later
empirical dump-diff work (2026-08-26, §2 above) and the owner's reproducible bench recipe superseded:
both data bytes genuinely matter on Y181. Noted here only as a historical dead end, not carried forward
as live doubt.

## 13. Historical appendix: retired `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (folded in 2026-11-21)

`eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (Jan-Feb 2026, "10 undocumented flags" framing) is
retired to a thin pointer at that path. Its live conclusions are already carried above (§2, §5.2,
§5.4, §5.8) and in `eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`. This section preserves the
raw data from that file that has no other home in this corpus or in
`VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`: the marker-rotation raw tables (§13.1), a few
RE subroutine addresses from the VIP `$27`/ICUSB chain not otherwise recorded here (§13.2), and a
compact correction/provenance trail (§13.3).

### 13.1 Marker-rotation raw data (Feb 2026, Y181 USB reflash of identical firmware PN `86331656`)

Observed marker-byte samples per address, across three dump states (stock pre-reflash /
post-Y181-reflash / ADB_enabled) — copied verbatim from the retired file. The retired file summarized the effect as marker/framing bytes changed at 31+ addresses while all data values stayed identical:

| Address | Stock (pre-reflash) | Post-Y181 Reflash | ADB_enabled |
|---------|--------------------|--------------------|-------------|
| 0x0440 | `0xC3` | `0x69` | `0x5A` |
| 0x0A80 | `0xFF` (empty) | `0xF0` | `0x5A` |
| 0x0B40 | `0x69` | `0x5A` | `0x69` |
| 0x1A00 | `0x69` | `0x69` | — |

Marker Transition Map — old-marker → new-marker pairs observed across the same reflash, with
occurrence counts and affected regions (table copied verbatim, including the retired file's own
column-count mismatch between header and data rows):

| Old Marker | New Marker | Count | Affected Regions |
|-----------|-----------|-------|-----------------|
| `0xC3` → `0x69` | 4 | Primary SBI, display/color calibration |
| `0x5A` → `0xF0` | 8 | VIN, display settings, brightness, volume, VIN suffix |
| `0x69` → `0x5A` | 3 | Secondary serial, debug mode, touch version |
| `0xF0` → `0x5A` | 4+ | Unknown toggle, all audio tables (0x1040-0x1280) |
| `0x69` → `0xC3` | 1 | Feature toggle (0x0BC0) |
| `0x69` → `0xF0` | 1 | CRC #1 (0x16E0) |

Not a consistent permutation — individual addresses map to different new markers.

Unchanged markers across the same reflash: boot/init flags `0x0000`/`0x0020`/`0x0040` (always
`0x69`); security configs `0x0400`/`0x0420` (always `0x69`); HW part number / unidentified
`0x0460`/`0x0480` (always `0xF0`); device ID strings `0x0500-0x05A0` (always `0xF0`); tertiary
security `0x1A00` (always `0x69`); secure boot hash `0x1F60` (always `0x69`).

CRC version-counter raw samples (stock vs. post-reflash; the upper-word step `0x0013→0x0104` is
already stated generically in §6 above — these are the specific per-block byte values behind it):

| CRC | Stock | Post-Reflash | Delta |
|-----|-------|-------------|-------|
| CRC #1 (0x16E0) | `00 0013 1531` | `00 0104 9F67` | Upper: 0x0013→0x0104 |
| CRC #2 (0x19E0) | `00 0013 0DB5` | `00 0104 17F8` | Upper: 0x0013→0x0104 |
| Data CRC (0x1B40) | `00 0013 189D` | `00 0104 A314` | Upper: 0x0013→0x0104 |

USB update package manifest (Y181, no SPS calibration files present):

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

**CRC-block sample, 2026-10-15 clean-room triple-pass on `dump.bin` (a `26_HC_A11` session dump)** — raw 5-byte blocks: `00 00 58 96 98` (`0x16E0`), `00 00 57 F2 74` (`0x19E0`), `00 00 58 9B AD` (`0x1B40`). Upper words (stored bytes `58 00`/`57 00`/`58 00`, LE u16 = `0x0058`/`0x0057`/`0x0058`) cluster tightly with ±1 drift, matching the `[00][upper version word][lower hash/CRC word]` structure in §6. An earlier single-dump pass that read the whole payload as one monotonic ~5.8M counter is superseded by this structural reading.

### 13.2 VIP `$27`/ICUSB subroutine addresses (raw RE detail, not found in this corpus or in
`VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md` during this retirement pass)

- `0xb6652`: level-range mapping/validation, called from the `$27` validator at `0xb67d0`.
- `0xaee28`: slot/state clear, called from the same validator.
- `0xb6680`: feature-state check — loads RAM `0x71e0`, compares against `3`.
- `0xb6690`: debug-state check — loads RAM `0x71ed`, checks if zero.
- ICUSB enable logic in VIP_APP at `0x9ce22`: loads RAM `0x714f`, compares to `1`, and on match
  calls ICUSB init at `0x97d78`. RAM `0x714f` is described as holding the processed ICUSB-enable
  state fed by the primary SBI plus the `0xb67d0` validation result.

These addresses are carried here without independent re-verification in this pass — ELA's §1
deliberately defers VIP `$27`-validator subroutine detail to `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`/
`VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` rather than restating it, but this specific ICUSB-chain detail
was not found in either of those during this pass, so it is preserved here rather than dropped.

### 13.3 Correction / provenance trail (what the retired file claimed vs. what replaced it)

- **"10 undocumented security flags"** (`0x04A0`, `0x04C0`, `0x0A40`, `0x0A60`, `0x0AC0`, `0x0B20`,
  `0x0BE0`, plus `0x0A20` ("System State Timer Configuration", "126 refs", MEDIUM; inferred from proximity to `[SS_SWC]`/`[GYROACCL]` debug strings; listed "do not modify — may affect power states"), plus "base addresses" `0x0A00`/`0x0B00`), ranked by "N firmware refs" string-proximity
  counts → **refuted (Aug-Sep 2026)**: the ref counts (as claimed in the retired file: `0x04A0`=17, `0x04C0`=11, `0x0A20`=126, `0x0A40`=28, `0x0A60`=15, `0x0AC0`=14, `0x0B20`=7, `0x0BE0`=24; the file's diagram also labeled `0x0B60` "Security counter", `0x0AE0` "Additional security" and `0x0BA0` "Feature enable #2" as "documented") do not reproduce and were never real code
  cross-references. A real Ghidra pass found zero genuine code reference for `0x04A0`/`0x0A40`/
  `0x0BE0`/`0x0A60`/`0x0AC0`/`0x0B20`, and all read `0xFF` (unwritten) in both stock and
  ADB-enabled dumps. `0x04C0` alone is touched by a real handler (CalGroup `0x44`,
  `FUN_ram_00091f82`), but the cell itself is still empty. `0x0A00`/`0x0B00` are structure-base
  addresses, not flags. See §5.2/§5.4 above and `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md` §2-5/§9.
- **Calibration files `85783460`/`87846384`** claimed to carry an "encrypted EEPROM reset payload"
  → **retracted 2026-09-10**: a full byte-level decode showed ordinary `calserviced` CalOvride XML
  overrides with zero EEPROM/SBI/security references. See §3 above.
- **Y177 VIP `$27` validator at `0xb67d0`** claimed to be a stub (a removed security check) →
  **refuted 2026-08-25** (three-way VIP_APP diff): the full ~906-byte validator is present,
  byte-identical, in Y175/Y177/Y181 alike. See §1 and §12's 2026-08-26 entry above.
- **RAM `0x3e06`** claimed to be "the processed EEPROM SBI value" → **corrected**: it is a generic
  "security module initialized" readiness flag, not the SBI data byte itself. See §2 above.
- **`0x0B41` "Debug Mode"** claimed to toggle a developer/debug mode, on a single-value (`0x01`)
  test → **closed as behaviorally inert, 2026-10-15**, after a full-range operator test
  (`0x00`/`0x01`/`0xFF`, no observed effect); the "Debug Mode" name is unconfirmed. See §5.4 above.
- **"Zero literal marker patterns in firmware"**, claimed as proof markers are pure
  runtime-generated noise → **corrected 2026-08-17**: a hex scan of the shipped `86331656` found
  `69 00 69` ×3 and `C3 00 C3` ×4 (only `5A FF 5A` = 0); the broader runtime-generation conclusion
  still holds on other evidence, but "zero literal patterns" is false.
- **VIP PN `86331656`** bound to md5 hash `c381ed1c507d6ac6381c315fe94d9114` → **unverified,
  2026-08-17**: does not match the actual shipped-package md5 (`e47928d9f409834083abc9a068ce65e0`);
  the marker-rotation observation itself (bytes changed, data identical) is unaffected.
- **CRC algorithm for `0x16E0`/`0x19E0`/`0x1B40`**, claimed reproducible as CRC-16/CCITT-FALSE of
  the version word alone, "independently reproduced by brute-force across 5 images" → **retracted
  2026-10-15**: the same version word (`0x0058`) maps to different stored hashes at `0x16E0` vs
  `0x1B40`, ruling that out; only `0x1DC0` is confirmed CRC-16/CCITT-FALSE. See §6 above.
- **"N firmware refs" self-disagreement**, noted at time of retirement: the retired file quoted
  different counts for the same two addresses in its own §2.2 vs §10.2 (`0x0A00` = 871 vs 854;
  `0x0B00` = 311 vs 305) — kept here only as evidence the counts were never a stable, reproducible
  measurement.
- **`0x04A0`/`0x04C0`** framed as "IPC Security Configuration" based on proximity to `[IPC_S]` debug
  strings → **retracted**: those strings are an ordinary HDLC serial-transport log tag ("IFRAME
  Rx", "UART read failed"), confirmed to live in a different part of the binary with no code link
  to the CalGroup handlers that actually touch `0x04A0`/`0x04C0`. See
  `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md` §3-4.

## Open conflicts

1. **MEC value semantics — nonzero = bypassed/unlocked, or production/locked?** This doc and
   `VIP_CONTROL_ANALYSIS.txt` §5.2 ("MEC increases to 244 after bypass") treat a nonzero MEC as the
   bypass/unlocked state, consistent with the Y181 boot-log evidence in §10 (MEC `0xFF` = SBI-set
   bench unit) and with `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` §2.3.6-7's per-unit MEC table (values
   207/227/241/244/0 observed across Y175/Y181/Y181B units). Several retired source docs (a
   `DPS_SECURITY_ANALYSIS.txt`-derived reading, `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt`, and
   `PROJECT_MASTER_CHECKLIST.txt`'s own pre-correction note) instead labeled MEC 244 specifically
   "production/locked" — a label that contradicts the very capture it was drawn from (ADB was
   accessible at MEC 244 in that capture). No source closes what, if anything, *graded* values like
   244 (vs. a plain nonzero) mean beyond "not zero, not a cert-required fail-closed `-1`" (§10's binary
   consumer behavior is itself the strongest evidence that no grading exists downstream, but the
   per-unit *source* of specific values like 244 vs 255 is not explained). Routed here and to
   `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` per the reorg plan; not settled by either doc.

No other open conflicts are carried in this doc: the 0x0A80/0x0A81 identity (reorg-plan item 4) is
settled in §2/§12 above, and the 0x0B40/0x0B41 debug-flag write-value question (reorg-plan item 5) is
`VIP_CONTROL_ANALYSIS.txt`'s own open conflict to settle in its Appendix A — this doc's §5.4 already
states the corrected `0x0B41=0x01` write value with no internal inconsistency.

## External sources / references

- **AUTOSAR_SWS_NVRAMManager R22-11**, Chapter 10 (ECUC) — `NvMBlockManagementType` (ECUC_NvM_00062,
  symbolic enumeration only) and `NvMNvBlockNum` (ECUC_NvM_00480, the REDUNDANT/NATIVE discriminator).
- **AUTOSAR_SWS_CRCLibrary** — `Crc_CalculateCRC16()`, seed `0xFFFF`, poly `0x1021`.
- **Renesas Application Note R01AN2296EJ** — RH850 Flash Self-Programming Library, same CRC-16/
  CCITT-FALSE for flash-block CRC verification.
- **Renesas R20UT2846EJ (CC-RH ABI)** — natural struct packing explaining the 12-byte descriptor size.
- **CVE-2025-32058 / Black Hat Asia 2025** — Nissan Leaf RH850 Virgin status byte and INC-protocol port
  map, cross-platform corroboration for the SBI 0x00/0xFF convention.
- **Willem Melching, DEF CON 30 Automotive Village (2022)** — Toyota EPS RH850 NvM header research;
  block-ID-first hypothesis tested and refuted against this platform's descriptor table.
