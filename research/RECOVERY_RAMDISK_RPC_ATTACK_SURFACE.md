# Recovery / OTA → GHS `ota_update` RPC Attack Surface Map

**Task:** reverse-engineer the RPC protocol between the recovery-side updater and the
GHS `ota_update` INTEGRITY partition — opcodes, validation, error handling, state machine,
fuzz targets.

**Analyst model:** Opus. **Date:** 2026-08-17.
**Corpus:** `/Users/zeno/Downloads/github/gminfo_resources` (no live device this session; static
artifacts only).

---

## 0. Provenance caveat — READ FIRST (the named binaries are not in this corpus)

The brief posits an extracted 46 MB recovery ramdisk containing `system/bin/gm_updater` and
`system/bin/recovery`. **Neither is present in this repository, and no ramdisk/cpio/img
artifact exists here.** Verified:

- `grep -rli gm_updater .` (incl. `.llm_index.jsonl`, `.serena/cache`) → **0 hits**. The string
  `gm_updater` appears nowhere.
- `find . \( -name '*ramdisk*' -o -name '*.img' -o -name '*.cpio*' \)` → **0 hits**. No recovery
  ramdisk was dumped into this tree.
- The update-process analysis states plainly: *"There is NO traditional Android recovery
  partition or fastboot mode … Updates occur while the system is running (A/B seamless updates)"*
  (`research/UPDATE_PROCESS_ANALYSIS.txt:88`). The live downgrade test nonetheless reports the
  system *"rebooted into recovery mode"* with a progress bar (`:317-318`), so an AOSP-style
  recovery/updater flow does execute — but the specific binary name `gm_updater` is **not
  attested** in any extracted material and is likely a mislabel.

**What the corpus actually contains, and what maps to the described role.** I mapped the real
components that fill the "recovery updater ↔ GHS ota_update RPC" slot:

| Described component | Real, extracted equivalent | Evidence file |
|---|---|---|
| GHS `ota_update` partition | INTEGRITY `ota_update` task/partition in **SOC_HOSTOS (85098662)**, INTEGRITY IoT 2020.18.19; dedicated ELF sections `.ota_update.text` (71,451 B), `.ota_update.rodata` (6,588 B), `.ota_update.data` (700 B), `.OTA.Initial.stack` (20 KB) | `research/decompiled/ghs_analysis.txt:37-69`, `ghs_str.txt:45605,46261` |
| recovery-side updater (`gm_updater`) | **Edify updater-script** (`gmext.*` verbs) in the `.mnf`, interpreted by AOSP recovery `updater`; **`gm_update_engine`** (`/vendor/bin/hw/`); **`rb_ua`** (Red Bend UA, `/vendor/bin/`) | `research/UPDATE_PROCESS_ANALYSIS.txt`, `platform/ota_update_stack.md`, `platform/ota_programming_roles.md` |
| RPC/IPC transport to `ota_update` | Android device node **`/dev/ghs/ota-isys`** → INTEGRITY IPC **`ConnToVMM_OTA`** (data) + **`ConnToVMM_OTA_Control`** (control) → **`OTA_InitialTask`** | `ghs_str.txt:44239,45939-45942,46074-46075` |

Everything below is derived from **string/symbol evidence of the GHS `ota_update` binary side**
plus the Android-side updater analyses. The actual `ota_update.text` was **not disassembled**
(only section boundaries + rodata strings are available), so opcode *numbers* are largely not
recoverable — I say so explicitly at each point. Confidence tags: **[C]** confirmed string/symbol,
**[I]** inferred from strings, **[U]** unknown / needs deeper RE.

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
Security Engine) and the **ABL** (Automotive Bootloader) update — i.e. `ota_update` is the broker
that turns guest OTA calls into firmware-engine actions. Downstream of this, ECU modules
(VIP_APP/BOOT, TUNER, GPS, SXM, ETH_SWITCH) are flashed by the **VIP RH850 over UDS/CAN**, not by
`ota_update` directly.

---

## 2. (a) Command opcodes

**No opcode enumeration table is directly recoverable from the available strings** — the
`.ota_update.text` was not disassembled. What *is* recoverable:

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

**2.3 ELK / ABL-prompt alternate command path [C].** Symbols
`BootELKSendAblUserCommand` and `BootELKWaitForRespSent` (`ghs_analysis.txt:291-292`), plus
`ConnToOTA_BootELK`. `ota_update` can drive the **ABL "user command" prompt** — the rodata even
carries the ABL prompt banner (`Booted from ABL prompt.`, `gm_part_number=`, `ABL.version=`,
`ABL.secureboot=`, …, `ghs_str.txt:38155-38166`). This is a *second* command surface into the
bootloader that bypasses the normal OTA framing — see fuzz targets. The repo already flags this
as attack vector **#4 "ELK via VIP J6_CDD → HECI → ABL"**, noting ELK *bypasses AVB + GHS misc
rollback* (`research/security/CVE_ATTACK_SURFACE_ANALYSIS.md:148`).

**2.4 Guest-side high-level "opcodes" = the Edify `gmext.*` verbs [C]** (these are what the
recovery updater actually invokes; they descend into the ota-isys path). From the Y181 `.mnf`
(`UPDATE_PROCESS_ANALYSIS.txt:158-189`):

| Verb | Action |
|---|---|
| `gmext.write_emmc_image(mod, pn, /dev/block/by-name/X)` | raw write image → eMMC partition |
| `gmext.extract_emmc_image(mod, pn, dev)` | extract raw image → partition |
| `gmext.extract_logical_partition(mod, pn, name)` | write dynamic/super sub-partition |
| `gmext.update_ecu(mod, pn)` | flash ECU via VIP/UDS |
| `gmext.switch_slot()` | flip active A/B slot |
| `gmext.update_dynamic_partition_config()` | rewrite super partition table |
| `gmext.show_progress()` | progress UI |

**2.5 `/dev/ghs/ota-isys` ioctl numbers are UNKNOWN [U].** The repo's own probe notes the ioctls
are *guesses* (`_IOR('g', 0x01-0x02, int)`) and require RE of the GHS LIP kernel module
`/system/lib64/libghs_lip.so` to recover the real dispatch table
(`research/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md:182`). This is the single biggest gap to closing
the opcode map.

---

## 3. (b) Parameter validation gaps

**The RPC layer itself does almost no semantic validation — the real gates are elsewhere (boot-time).**

| Field / object | Validation actually present | Gap |
|---|---|---|
| **OTA command length** | length sanity check only → `Bad command length for OTA command.` [C] | Only a length guard; **no evidence of per-field bounds/type checks** on the payload after length passes. [I] |
| **Partition / image size** | none at write time — writes are **raw** (system 3.0 GB, product 2.5 GB, vendor 445 MB) [C] | Write phase is a *"dumb pipe"*; the `version check disabled` manifest flag is honored (`UPDATE_PROCESS_ANALYSIS.txt:339-346`). No size/hash/signature check during the write RPC. |
| **CRC / A/B metadata** | **CRC32 only, no signature** → `VMM: Warning: A/B metatdata CRC failure!` [C] | Metadata = `{magic, version, slot_info[2], crc32}`. CRC32 is **forgeable** (recompute after edit). Magic + version + CRC32 is the entire integrity story on `misc`/vda9. (`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md:344-391`) |
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

## 4. (c) Error handling — what happens on RPC failure

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
5. Operator drops `gm_reboot_normal` on USB to exit; system returns to the **unchanged** prior build.

So an RPC/verification failure is **recoverable and non-bricking by design** (A/B fallback), but
the failure is caught at *boot*, after blind writes — there is no write-time abort. Rollback-index
rejection is confirmed real: `VMM: ERROR: rollback index is too old: %lu in image, but stored is
%lu` (`UPDATE_PROCESS_ANALYSIS.txt:332`), stored in `misc`/vda9 independent of vbmeta.

---

## 5. (d) State machine assumptions — re-entry, skip, replay

**Two coupled state machines.**
- **Android SWU:** `mIdle → mDownloadAvailable → mUpdateAvailable → mSecureUnlock → mProgramming
  → mPostProgramming → mUpdateComplete` (`platform/ota_update_stack.md:111-114`). `mSecureUnlock`
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

**To actually build the opcode table and fuzz harness you still need:** (1) disassembly of
`.ota_update.text` (71 KB, present in SOC_HOSTOS 85098662 but not decompiled here), and (2) RE of
`/system/lib64/libghs_lip.so` for the ota-isys ioctl dispatch + frame layout. Both are the
standing blockers noted in the repo, and neither the posited `gm_updater` binary nor a recovery
ramdisk is present to shortcut them.

---

## Appendix — evidence file paths

- `research/decompiled/ghs_str.txt` — OTA/HECI rodata strings (`:38092-38146`), section path
  (`:45605`), IPC connection names (`:45939-46075`), `.ota_update.*` sections (`:46261-46262`),
  `ota-isys` (`:44239`), `attkb_magic_file` (`:40679`).
- `research/decompiled/ghs_analysis.txt` — `.ota_update.*` section boundaries (`:37-69`),
  `BootELKSendAblUserCommand`/`WaitForRespSent` (`:291-292`), `OtaUpdateToHeciIod`/`BootArgsIod`
  (`:695-696`).
- `research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` — OTA flow (§3.3), A/B metadata layout + CRC32
  weakness (§3.1), attack-surface table (§6).
- `research/UPDATE_PROCESS_ANALYSIS.txt` — `gmext.*` manifest verbs (§4.1), raw-image confirmation,
  live downgrade test + rollback-index string (§6).
- `platform/ota_update_stack.md` — SWU state machine, package signing tiers, USB flags.
- `platform/ota_programming_roles.md` — engine chain (`gm_update_engine → rb_ua → VIP RH850`).
- `research/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` — ota-isys node, ioctl-guess note, rollback path.
- `research/security/CVE_ATTACK_SURFACE_ANALYSIS.md` — ELK/HECI (#4) and ota-isys (#6) status.
