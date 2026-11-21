# `ota_update` RPC Attack Surface

**Scope:** RE map of the RPC protocol between the Android recovery-side updater and the
GHS `ota_update` INTEGRITY partition — opcodes, parameter-validation gaps, error handling,
state-machine assumptions, and 7 ranked fuzz targets. **Secondary to
[GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) (GBUR) for binary
provenance and the verified ELK IPC/HECI path** — do not read this doc as primary on those;
it holds the older RPC/schema hypotheses. It **is** primary for the opcode table, the
parameter-validation-gaps table, and the fuzz-target ranking — none of which GBUR restates.

**Analyst model:** Opus. **Date:** 2026-08-17. **Corpus:** `gminfo_resources/` static artifacts,
no live device this session.

**Evidence tags:** `[C]` confirmed · `[I]` inferred · `[U]` unknown.

---

## 0. Scope and canonical evidence

This document owns the older RPC/schema hypotheses and their confirmed/inferred/unknown
labels. Current binary provenance, the verified ELK IPC/HECI path, and recovery behavior
are maintained in GBUR. A complete guest-to-host RPC schema remains unproven; the hypotheses
below must not be read as demonstrated vulnerabilities.

---

## 1. Channel topology (what talks to `ota_update`)

```
 ANDROID GUEST (recovery / gm_update_engine / rb_ua / Edify updater)
   │  gmext.write_emmc_image / extract_emmc_image / extract_logical_partition
   │  gmext.update_ecu / switch_slot / update_dynamic_partition_config
   ▼
 /dev/ghs/ota-isys        ← ghs LIP kernel shim; marshals guest calls into INTEGRITY IPC
   │   (ioctl dispatch table UNKNOWN — libghs_lip.so not RE'd)              [U]
   ▼
 INTEGRITY IPC:  ConnToVMM_OTA (data plane)  +  ConnToVMM_OTA_Control (control plane)  [C]
   │                                            ConnToOTA / ConnToOTA_OTA / ConnToOTA_OTA_Control
   ▼
 OTA_InitialTask  (the `ota_update` partition)                                          [C]
   ├── OtaUpdateBootArgsIod   → writes kernel/boot args for the guest                   [C]
   ├── OtaUpdateToHeciIod     → Intel CSE/ME + ABL firmware update over HECI            [C]
   ├── ConnToOTA_BootELK / ConnToLifecycle_BootELK  → ELK emergency-kernel command path [C]
   ├── ConnToEMMC / IodToEMMC → eMMC (misc / staging) access                            [C]
   └── ConnToCalibrations, ConnToTEE_Router, ConnToVMM_TextLog, Audit_*                 [C]
```

Two logically distinct planes: **data** (`ConnToVMM_OTA`) and **control**
(`ConnToVMM_OTA_Control`). The task also owns the **HECI** path to the Intel CSE (Converged
Security Engine) and the **ABL** (Automotive Bootloader) update — i.e. `ota_update` is the
broker that turns guest OTA calls into firmware-engine actions. `gmext.update_ecu` naming alone
does not prove an external VIP UDS/CAN route; downstream peripheral-update transport must be
established per module.

**History (2026-11-17):** the tested VIP-application CAN path rejected the stock SXM file
(`PEC000A`) and a module1C calibration-header-gate probe (`PEC000F`) — its header parser
accepts calibration IDs `02`–`0F` only — and the mounted Y175 `swu_update_sxm` export returns
`0B` without a write call. Other bootloader/internal routes remain unresolved. Owner doc for
this fact: [`platform/ota_programming_roles.md#sxm-stock-file-can-attempt--2026-11-17`](../../platform/ota_programming_roles.md#sxm-stock-file-can-attempt--2026-11-17).

---

## 2. Command opcodes

**No opcode enumeration table is directly recoverable from the available strings.**
**History:** `.ota_update.text` *was* disassembled and decompiled in a later session
(not reflected in an earlier draft of this doc) — CFG-driven discovery from the entry
point found only 37 functions (all generic C-runtime boilerplate); a brute-force
byte-level sweep of the full 71,451-byte section found 576 more (614 total); all 614
were decompiled to 18,041 lines of C. The full decompiled corpus has zero references
to `.ota_update.rodata`'s address range or any of its known string addresses
(`0xdf60e8`, `0xdf610d`, `0xdf74d2`, `0xdf75e2`, `0xdf7793`) — a cross-validated
negative result (same pattern independently found in `.vmm1.text`, see
[`VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`](../security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md)), not a
coverage gap. The opcode/length-field framing below is therefore real but its dispatch
table is not found in `.text`/`.rodata`; the next unexplored lead is `.ota_update.data`
(700 B, not yet dumped). What *is* recoverable from the strings:

**2.1 The `ota-isys` command frame is length-prefixed / opcode-dispatched [I].**
The single ingress-validation string proves a command frame with a length field:

- `"Bad command length for OTA command."`  (`ghs_str.txt:38092`)
- `"RPC channel error: %d"`                (`ghs_str.txt:38093`)

A "command length" check that can be *bad* implies `{ opcode/cmd-id, length, payload }` framing
and a dispatch on the id. The id space itself is **[U]**.

**2.2 Downstream HECI/CSE sub-commands the `ota_update` task issues (these ARE opcodes, on the
CSE/ABL side) [C].** From `.ota_update.rodata` (`ghs_str.txt:38115-38146`):

| Sub-command (HECI/CSE) | Evidence string |
|---|---|
| **ABL update** | `Failed to send ABL update command` / `ABL update command failed: %d` / `ABL update command returned invalid length: %d` |
| **CSE prepare update** | `Failed to send HECI command to prepare CSE update` / `CSE prepare update HECI command failed: %d` / `CSE did not enter prepare update mode` |
| **CSE clear data** | `Failed to send HECI command to clear CSE data` / `CSE clear data HECI command failed: %d` / `CSE clear data HECI command accepted` |
| **GET ATTKB SIZE** | `Failed to send GET ATTKB SIZE HECI command` |
| **GET ATTKB** | `Failed to send GET ATTKB HECI command` (attestation key blob; `attkb_magic_file`, `ghs_str.txt:40679`) |
| HECI transport primitives | connect / disconnect / get-client-properties / read-property / enumeration (`38120-38132`) |

**2.3 ELK / ABL-prompt alternate command path [C].** Symbols `BootELKSendAblUserCommand` and
`BootELKWaitForRespSent` (`ghs_analysis.txt:291-292`), plus `ConnToOTA_BootELK`. `ota_update` can
drive the **ABL "user command" prompt** — the rodata even carries the ABL prompt banner
(`Booted from ABL prompt.`, `gm_part_number=`, `ABL.version=`, `ABL.secureboot=`, …,
`ghs_str.txt:38155-38166`). This is a *second* command surface into the bootloader that bypasses
the normal OTA framing — see fuzz targets §6. The repo already flags this as attack vector
**#4 "ELK via VIP J6_CDD → HECI → ABL"**, noting ELK *bypasses AVB + GHS misc rollback*
(`research/security/CVE_ATTACK_SURFACE_ANALYSIS.md:148`).

**2.4 Guest-side high-level "opcodes" = the Edify `gmext.*` verbs [C]** (these are what the
recovery updater actually invokes; they descend into the ota-isys path). From the Y181 `.mnf`
(`UPDATE_PROCESS_ANALYSIS.txt:158-189`):

| Verb | Action |
|---|---|
| `gmext.write_emmc_image(mod, pn, /dev/block/by-name/X)` | raw write image → eMMC partition |
| `gmext.extract_emmc_image(mod, pn, dev)` | extract raw image → partition |
| `gmext.extract_logical_partition(mod, pn, name)` | write dynamic/super sub-partition |
| `gmext.update_ecu(mod, pn)` | target-specific update; transport requires tracing |
| `gmext.switch_slot()` | flip active A/B slot |
| `gmext.update_dynamic_partition_config()` | rewrite super partition table |
| `gmext.show_progress()` | progress UI |

**2.5 `/dev/ghs/ota-isys` ioctl numbers are UNKNOWN [U].** The repo's own probe notes the ioctls
are *guesses* (`_IOR('g', 0x01-0x02, int)`) and require RE of the GHS LIP kernel module
`/system/lib64/libghs_lip.so` to recover the real dispatch table
(`research/security/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md:182`). This is the single biggest gap to closing
the opcode map.

---

## 3. Parameter validation gaps

**The RPC layer itself does almost no semantic validation — the real gates are elsewhere (boot-time).**

| Field / object | Validation actually present | Gap |
|---|---|---|
| **OTA command length** | length sanity check only → `Bad command length for OTA command.` [C] | Only a length guard; **no evidence of per-field bounds/type checks** on the payload after length passes. [I] |
| **Partition / image size** | none at write time — writes are **raw** (system 3.0 GB, product 2.5 GB, vendor 445 MB) [C] | Write phase is a *"dumb pipe"*; the `version check disabled` manifest flag is honored (`UPDATE_PROCESS_ANALYSIS.txt:339-346`). No size/hash/signature check during the write RPC. |
| **CRC / A/B metadata** | **CRC32 only, no signature** → `VMM: Warning: A/B metatdata CRC failure!` [C] | Metadata = `{magic, version, slot_info[2], crc32}`. CRC32 is **forgeable** (recompute after edit). Magic + version + CRC32 is the entire integrity story on `misc`/vda9. (GBUR owns the full A/B-metadata layout/weakness writeup, [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md:344-391](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md)) |
| **Slot** | `switch_slot()` is unconditional; slot suffix trusted [C] | No binding between a *completed/verified* write and the slot flip. Mismatch only triggers a reboot (`GHS: Android and INTEGRITY slot mismatch … Rebooting`). |
| **HECI response length (egress)** | **checked** → `ABL update command returned invalid length`, `Invalid response length to CSE prepare/clear`, `Read more attkb bytes (%d) than expected` [C] | This is defensive on *replies from CSE*, not on *guest ingress*. Still, it shows the parser trusts a declared length then compares — a classic mismatch bug class if the CSE side is MITM'd. |
| **ATTKB buffer** | explicit size guard → `ATTKB is larger (%d bytes) than data buffer (%ld bytes)`, `Attempting to read too much data from HECI`, `Not enough free space in HECI write buffer` [C] | Guard exists, but the pattern (declared-size vs fixed-buffer) is exactly the shape that breaks on off-by-one / integer-width mismatch (`%d` vs `%ld`). Prime fuzz surface. |
| **Package signature** | **TSS / GPD Production CA** on VIP_APP, HOSTOS, SYSTEM, VENDOR [C] | Enforced at *package acceptance*, not in the ota-isys frame. Unsigned modules (BOOT, ABL, VBMETA, PRODUCT, ACPIo, ECUs) lean on AVB / UDS instead. |

**Net:** the guest→hypervisor OTA RPC path is effectively **unauthenticated within the guest**;
the *only* runtime gate on `/dev/ghs/ota-isys` is **SELinux domain** (DAC is `rw-rw-rw-` on the
node — `HARDWARE_HYPERVISOR_ATTACK_VECTORS.md:178`). All the strong checks (AVB signature, GHS
rollback index, TSS package signature, UDS SecurityAccess) fire **after** the RPC, at boot verify
or on the VIP — not on the command itself.

---

## 4. Error handling — what happens on RPC failure

**4.1 Per-message errors (logged, non-fatal to the host).**
- Malformed frame → `Bad command length for OTA command.` (drop; **[I]** command discarded).
- Transport fault → `RPC channel error: %d`.
- HECI layer: a discrete error string + `%d` result for every failure — send failures, invalid
  connect/disconnect/property status, enumeration failure, and **timeouts** on `H_IG` clear, HECI
  reset, and `IS`-to-host signaling (`ghs_str.txt:38115-38146`). HECI ops are **timeout-bounded**,
  not infinite-retry; no evidence of a bounded *retry counter* inside `ota_update`.
- CSE state precondition failure → `CSE did not enter prepare update mode` (abort the update leg).

**4.2 Whole-transaction failure = fail-safe at boot, NOT fail-secure at write.** The live
downgrade test (`UPDATE_PROCESS_ANALYSIS.txt:313-326`) is the ground truth for the error path:

1. Partition writes to the inactive slot **succeed** (write RPC never verifies).
2. Reboot → **GHS boot verify rejects** the slot (AVB and/or rollback index).
3. A/B logic **falls back to the original slot** (tries_remaining / priority).
4. Android renders an **"Update Failed"** screen (rendered by `gm_update_engine`, not GHS).
5. Operator uses the USB exit marker to return the system to the **unchanged** prior build.

**History (2026-11-12):** the exit-marker filename/handler stated here originally is stale.
GBUR is the current source of truth for the correct marker and handler — see
[GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md §4.5](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#45-known-usb-trigger-files).

So an RPC/verification failure is **recoverable and non-bricking by design** (A/B fallback), but
the failure is caught at *boot*, after blind writes — there is no write-time abort. Rollback-index
rejection is confirmed real: `VMM: ERROR: rollback index is too old: %lu in image, but stored is
%lu` (`UPDATE_PROCESS_ANALYSIS.txt:332`), stored in `misc`/vda9 independent of vbmeta.

---

## 5. State machine assumptions — re-entry, skip, replay

**Two coupled state machines.**
- **Android SWU:** `mIdle → mDownloadAvailable → mUpdateAvailable → mSecureUnlock → mProgramming
  → mPostProgramming → mUpdateComplete` (owner: [`platform/ota_update_stack.md`](../../platform/ota_update_stack.md), state-table detail there). `mSecureUnlock`
  = UDS SecurityAccess ($27) challenge.
- **GHS boot verify:** `CheckRecoveryMode → read A/B metadata → AVB (vbmeta→boot) → rollback index
  → run guest`.

**Assumptions and where they bend:**

| Question | Finding |
|---|---|
| **Replay commands?** | The ota-isys frame shows **no nonce/session token** in any string; writes are raw and idempotent-ish. Re-driving `write_emmc_image` / re-issuing the frame appears replayable within a session. **[I]** (no anti-replay evidence either way — needs `.text` RE to confirm). |
| **Re-enter stages?** | The write phase and the verify phase are **decoupled** (different components, different reboots). Nothing binds "verified" state to a slot before `switch_slot()`. A crafted manifest can order `switch_slot` before/without a complete valid write. |
| **Skip verification?** | At the **write RPC layer, verification is *inherently* absent** (dumb pipe, `version check disabled` honored). You cannot, however, skip the **GHS boot-time AVB + rollback** — that is a separate partition's job and is the confirmed hard gate (downgrade blocked live). |
| **Sequencing gaps** | Edify script ordering is the *only* sequencing for `gmext.*`; there is no enforced state guard that a slot was fully/validly written before the flip. GHS AVB then fails → fallback (contained). |
| **CSE leg preconditions** | `prepare update → (clear data) → ABL update` is gated: `CSE did not enter prepare update mode` shows a precondition that aborts if unmet. A reachable, replayable **`CSE clear data`** is a **data-loss primitive** if it can be issued out of sequence. |
| **ELK/ABL side-channel** | `BootELKSendAblUserCommand` is an alternate command entry that reaches the ABL prompt **outside** normal OTA framing and (per repo #4) **bypasses AVB + misc rollback**. Its state model is separate and under-analyzed — highest-leverage unknown. |

---

## 6. Fuzz targets (input mutations that break the protocol)

Ranked by evidence strength × leverage:

1. **`ota-isys` command-frame length field** — the sole ingress guard is `Bad command length`.
   Fuzz `declared_length` vs `actual_payload` (under/over/off-by-one, `INT_MAX`, zero-length with
   payload). Best target; **blocked on** a SELinux-permissive domain for `/dev/ghs/ota-isys`
   **and** RE of `libghs_lip.so` to learn the ioctl + frame layout. **[U layout / C guard]**
2. **ATTKB size field** — explicit `larger than data buffer` / `read more than expected` guards
   with `%d`↔`%ld` width mismatch. Fuzz declared-size vs actual to probe the bound (heap/stack
   overflow candidate). **[C guard]**
3. **A/B metadata on `misc`/vda9** — `{magic, version, crc32}` only. Mutate slot priority /
   tries_remaining / rollback and **recompute CRC32** (forgeable) to force slot selection or defeat
   the metadata check. This is the repo's vector **#6/#8** (needs offline eMMC or ota-isys write).
   **[C]**
4. **HECI reply-length fields** — multiple `invalid length: %d` checks on CSE/ABL replies; if the
   CSE response can be influenced (SA-00086 / CVE-2021-0146 HECI injection, repo #4), boundary
   values may desync the length-then-copy parser. **[C guard]**
5. **Edify `.mnf` argument fuzzing** — `write_emmc_image(mod, pn, dev)` device-path argument
   (arbitrary `/dev/block/by-name/*` / traversal), bogus module-id / part-number, reordered
   `switch_slot`. Gated by TSS package signature, so mostly reachable only with a signing bypass
   or on the unsigned-module legs. **[C]**
6. **ELK/ABL user-command channel** (`BootELKSendAblUserCommand`) — fuzz the ABL user-command
   string/args; this path is documented to skip AVB + rollback, so a parser bug here is
   disproportionately valuable. **[C symbol / U format]**
7. **Malformed vbmeta/boot** to exercise AVB error paths — all documented and handled (fail →
   fallback). Low yield; useful only for error-path coverage.

---

## 7. Bottom line

**Breaks (guest-reachable, weak/absent validation):** the `ota-isys` command framing (only a
length check), the raw write pipe (no write-time verify, `version check disabled` honored),
the CRC32-only A/B metadata (forgeable), and the decoupled/replayable write-then-`switch_slot`
sequence. The ELK/ABL user-command channel is a second, less-guarded entry into the bootloader.

**Holds (the real gates, all *after* the RPC):** GHS boot-time **AVB signature**; GHS **rollback
index** in `misc`/vda9 (confirmed to block Y181→Y177 live); **TSS/GPD Production CA** package
signature; **UDS SecurityAccess** on the VIP for ECU modules; and **SELinux** as the only runtime
gate on `/dev/ghs/ota-isys` (DAC is world-rw).

**Remaining gap, resolved:** `.ota_update.text` has been fully disassembled and decompiled
(§2 above) — this is complete, not outstanding. The opcode-table gap is a missing-dispatch-table
problem, not a missing-RE problem (see §2's "History" note: the negative result rules out
`.text`/`.rodata` as the dispatch mechanism; `.ota_update.data`, 700 B, is unexamined). What
remains outstanding is `libghs_lip.so` ioctl-dispatch RE, and any `.ota_update.data` table it
might hold — the opcode space at §2.1/§2.5 stays `[U]` for that reason, not for lack of
`.ota_update.text` coverage. GBUR is the canonical source for which binaries/paths are currently
verified.

---

## Open conflicts

None specific to this doc. (The corpus-wide items in the top-level plan — MEC semantics, module
72 naming, VMM1 bitness, EEPROM byte identities, seed length, DoIP topology, Y181→Y177 rejection
point — do not touch this doc's content and are not repeated here.)

---

## Appendix — evidence file paths

- `evidence/decompiled/ghs_str.txt` — OTA/HECI rodata strings (`:38092-38146`), section path
  (`:45605`), IPC connection names (`:45939-46075`), `.ota_update.*` sections (`:46261-46262`),
  `ota-isys` (`:44239`), `attkb_magic_file` (`:40679`).
- `evidence/decompiled/ghs_analysis.txt` — `.ota_update.*` section boundaries (`:37-69`),
  `BootELKSendAblUserCommand`/`WaitForRespSent` (`:291-292`), `OtaUpdateToHeciIod`/`BootArgsIod`
  (`:695-696`).
- [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) — OTA flow (§3.3), A/B metadata layout + CRC32
  weakness (§3.1), attack-surface table (§6), USB trigger-file truth (§4.5).
- Retired `UPDATE_PROCESS_ANALYSIS.txt` (content now in `platform/ota_update_stack.md` for the `gmext.*` manifest verbs
  (former §4.1) and raw-image confirmation, and in `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt` for the
  live downgrade test + rollback-index string (former §6)).
- [`platform/ota_update_stack.md`](../../platform/ota_update_stack.md) — SWU state machine, package signing tiers, USB flags.
- [`platform/ota_programming_roles.md`](../../platform/ota_programming_roles.md) — engine chain (`gm_update_engine → rb_ua → VIP RH850`), SXM-attempt history.
- `research/security/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` — ota-isys node, ioctl-guess note, rollback path.
- `research/security/CVE_ATTACK_SURFACE_ANALYSIS.md` — ELK/HECI (#4) and ota-isys (#6) status.
