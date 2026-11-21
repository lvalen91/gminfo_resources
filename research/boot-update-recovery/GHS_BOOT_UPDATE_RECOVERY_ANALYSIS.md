# GHS Boot/Update/Recovery Analysis

**Initial analysis:** 2026-01-05
**Consolidated findings updated:** 2026-11-17
**Binary Analyzed:** SOC_HOSTOS (85098662)
**OS Version:** INTEGRITY IoT 2020.18.19
**Platform:** Intel Apollo Lake (Broxton) / GM-i35

> Consolidated findings and source conventions: §0. Distinct inventory owners are linked there.
> This document absorbed `GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md`'s tool-setup/status
> narrative as §0.4 (history); that session's confirmed AVB-guard RE findings
> (`elk_inner.elf`) live in [VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md](../security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md),
> not here.

---

## 0. Scope, ownership and evidence conventions

**Canonical repository path:** `gminfo_resources/research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`.

This document owns the consolidated Y181B GHS/recovery investigation: primary
binary provenance, security-candidate limits, guest/dealer/fastbootd/ELK
boundaries, MEC and ADB privilege distinctions, recovery arguments, encoded USB
markers, log capture and dealer-wipe behavior. It also owns the live-tested
ELK-trigger fact (the CAN routine-ID F000/selector-8180 RAM-assisted request —
candidate frame `31 01 F0 00 81 80 03`, callback chain `57BC8`→`4E08A`→`5C0C0`→
`757D4`→`75794`→`7F642`, confirmed live 2026-11-17 producing UART
`Elk Reboot Response 0` and a controlled reset into Kernelflinger — see the VIP
ELK control selector mega-section under §2.3.3) that
HARDWARE_HYPERVISOR_ATTACK_VECTORS.md, GORDON_PEAK_CELADON_INTELLIGENCE.md,
VIP_CONTROL_ANALYSIS.txt and INVENTORY.md also state; those documents keep
pointers here rather than independent copies. Update the owning section here;
other documents link here instead of carrying independent copies.

| Topic | Owning section |
|---|---|
| Binary fingerprints, extraction boundaries, debugger and CVE evidence | §0.1 |
| Y181B recovery USB export provenance, member fingerprints and time limits | §0.2 |
| `.vmm1`/`.ota_update` RE tooling history (Aug 2026 session) | §0.4 |
| Failed boots, modes, ELK IPC/HECI/ACPI transition and privilege gates | §2.2.1–§2.3.6 |
| MEC certificate gate, target readings, root and registration limits | §2.3.7 |
| Recovery argument parser and dealer-wipe package | §4.2–§4.2.1 |
| Encoded USB markers and diagnostic export | §4.4–§4.7 |

Repo paths are relative to `gminfo_resources/`; Markdown links are relative
to their containing document. Android paths such as `/update_cache/recovery`
refer to the radio, not this repository. Firmware and captured-device logs
that are not checked into the repo are external evidence under the research
archive, denoted `GM_RESEARCH/`; this is a role, not a Mac-specific location.
`GM_UPDATE_CAPTURE` denotes the externally retained `update_cache.zip`
identified in §0.2; paths beneath `update_cache/` in capture citations are
ZIP members, not a requirement that the original USB remain attached.

The separate [GHS inventory](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) owns task,
driver, device-grant and privacy inventories. The [EEPROM audit](../eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
owns EEPROM layout and VIP reverse engineering. The [update-stack reference](../../platform/ota_update_stack.md)
owns the AAOS updater/Binder interface. Distinct inventories stay with those owners.
No complete live ELK transition, guest escape or accepted custom wipe package
is established by this static evidence.

### 0.1 Y181B binary provenance and security evidence (2026-11-12)

Y181 and Y177's `85098662` module are byte-identical (`md5` match) — a direct
measurement, not just a citation of the same claim elsewhere.

Original Y181B module `85098662` is 14,929,956 bytes, SHA-256
`317ae85ccf759476755411e66593dde9f879a43732cd342b4e101e4026535ed3`.
The ELF begins at package offset `0x27C`. The offset-to-EOF analysis slice
is 14,929,320 bytes, SHA-256 `d900af484f466b35f4d9153ddf8adf19482f91d728b707f10fe89d326d4870df`.
A moria-delimited carve reported 14,924,936 bytes: a different extraction
boundary, 4,384 bytes shorter. The additional bytes have not been characterized
here and must not be presumed padding or ignored in hash comparisons.
The custom 24-byte symbol table contains 18,035 records including the null
entry; 18,034 named entries were parsed. The declared ELF32/i386 identity
must not override the decoded x86-64 kernel instruction set.

**Evidence limits:** guest-memory helper names such as `ReadGuestMemory`,
`WriteGuestMemory`, `ReadGuestVirtualAddress` and
`VMM_SetVirtioBufferAddr` identify host implementation functions, not APIs
a guest is automatically authorized to call. Trusty/TIPC virtio queue, index,
length and rejection diagnostics identify concrete review targets; they do
not establish an exploitable validation gap. The diagnostic
`VMCALL attempted when cpl!=0` demonstrates a privilege-check path exists,
not complete proof of every VMCALL branch's enforcement.

`BSP_DebugEnabled`, `BSP_DebuggerHaltSystem`,
`BSP_DebuggerRestartSystem` and the corresponding ASP halt/restart symbols
are undefined weak symbols (value zero, undefined section). Their names do
not prove a reachable MULTI/INDRT debug server. The compiled
`Safeplex_IsSecureBoot` at `0xFFFF80000023DB44` returns zero; its identified
direct call at `0xFFFF80000023DB98` is in `Usb_GrabEHCI`. This is not proof
that AVB or the platform boot chain is disabled. Verification/key/rollback
strings describe compiled paths; the unit's active state needs independent
runtime evidence.

| Historical candidate | Required evidence before claiming applicability |
|---|---|
| CVE-2019-7714, Interpeak IPWEBS authentication parsing | Matching vulnerable HTTP component and exposed request path |
| CVE-2019-7713 and CVE-2019-7711/7712/7715, IPCOMShell | Matching shell implementation/revision and reachable shell functionality |
| URGENT/11 IPnet family | Affected IPnet code and an exposed network path |

The [original IPCOMShell/IPWEBS research](https://github.com/AlixAbbasi/GHS-Bugs)
targets INTEGRITY 5.0.4, not a verified instance of this GM build.
[Armis's URGENT/11 disclosure](https://www.armis.com/blog/urgent-11-affects-additional-rtoss-highlights-risks-on-medical-devices/)
identifies historical INTEGRITY products using vulnerable IPnet; that alone
does not identify the stack in Y181B. No `IPnet`, `IPCOM`, `IPWEBS`,
`Interpeak`, `GHnet` or `Treck` identifier was found in the inspected
host string inventory. Absence of names is not proof of absence, and an
automated scan reporting zero recognized components/CVEs is not a clean bill
of health for an unrecognized proprietary RTOS image.

No confirmed guest escape, GHS privilege elevation, global permissive-mode
switch, or enabled debugger was established. The
[Green Hills architecture](https://www.ghs.com/products/rtos/integrity_virtualization.html)
uses separation and explicit resource access; Android UID 0 or a guest SELinux
change is not itself GHS authority. For verified recovery/fastbootd privilege
checks, reciprocal ELK IPC and the ACPI shutdown callback, use
§2.3 below.

### 0.2 Y181B recovery USB capture (verified 2026-11-12)

The bench operator identifies the radio as **Y181B**. The experiment removed
`com.gm.homescreen` for Android users 0 and 10 via ADB, deliberately causing
incomplete startup. The operator observed three failed attempts followed by
dealer/recovery entry on the next reboot, then used the encoded
`gm_capture_log` marker to export diagnostics. This is an induced-failure
experiment, not evidence of a spontaneous hardware or stock-software fault.

The retained evidence is `GM_UPDATE_CAPTURE` (`update_cache.zip`), SHA-256
`af151140d9c96a1966d79e6d0c478bf35a1b25379cd03ba40f9c4ae344842d56`.
Its 445 non-directory members total 144,173,387 uncompressed bytes:
72 recovery files, 43 update files and 330 bootup-log files. The archive is
external evidence; do not copy its raw logs, identifying filenames, properties
or databases into this repository. The version fields report
`W231E-Y181.3.2-SIHM22B-499.3`; they do not independently distinguish the
operator-supplied B designation. The update history includes `86405527.mnf`.

| ZIP member beneath `update_cache/` | SHA-256 |
|---|---|
| `recovery/last_log` | `6fa7beac68651606766eba3101cb70efca334a7047edcedc085333546f5add7b` |
| `recovery/last_kmsg` | `5bc0864e283895cdce64e699912952dd7a552eae090d9845cdb9e866eb1c0e5f` |
| `update/moduleinfo` | `c7c87550cd211a66fbf9c8233e188b1a6029d3796ddfd365e0508a9b3b7d223e` |
| `bootup_log/vendor/CalSets.db` | `563041cda0630975d55d20ad6bd24ab06a52f2059bd2bcc74998808e9125b833` |

The export includes historical recovery rotations and update records; these
are not all products of the homescreen-removal experiment. Recovery starts
with a 2011 clock and subsequently sets a 2010 time; filesystem timestamps
also show 2010. Order records using rotation, boot-relative time and explicit
state transitions before trusting wall-clock dates. File counts are not boot
counts. `bootup_log/vendor/ghs_new/ghs.log` has the entire `ghs.log` as a
byte-for-byte prefix plus 57,336 bytes; deduplicate before counting events.
The GHS logs are retained text logs, not a complete host-memory dump.

Member-specific conclusions belong in §2.2.1 (startup), §2.3.7 (MEC),
§4.5.4–§4.5.5 (capture), the [guest-memory inventory](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory),
the [update-stack reference](../../platform/ota_update_stack.md#y181b-recovery-export-evidence-2026-11-12),
and the [vehicle calibration baseline](../../platform/vehicle_config.md#y181b-exported-baseline-2026-11-12).

**Recovery boot ledger across the retained `last_log` series (directly read from the second export, 2026-11-12):**

| Rotation | Recovery boot counter | Arguments / reason | `Dump log to USB` |
|---|---:|---|---|
| `.10`, `.9` | 47, 48 | `--wipe_data --reason=bcm_replacement` (from `/update_cache/recovery/command`) | no |
| `.8` | 49 | `--wipe_data --reason=com.gm.domain.server.delayed,2026-11-07T12:45:35Z` (boot message; recovery RTC read Sat Nov 7 2026 21:45, unreconciled with the 12:45Z stamp) | no |
| `.7` | 50 | `--wipe_data --reason=MasterClearConfirm,2026-11-10T15:54:27Z` (boot message; `unrecognized option` printed for the reason) | no |
| `.6`, `.5`, `.4` | 51, 52, 53 | none recorded | no |
| `.3`, `.2` | 54 | `--show_return_to_dealer`; `.2` also dumps | `.2` yes |
| `.1`, current | 55 | `--show_return_to_dealer`; current dumps | current yes |

**Code attribution added 2026-11-14:** the selected Android `gm_protokey`
binary explicitly writes the `bcm_replacement` recovery command after a
ProtoKey validation failure, then requests recovery reboot through
PowerModing. Its first-time path establishes a validation record; later
mismatches or an unusable existing-record read can reach the replacement
branch. This statically identifies an initiator for the historical wipe
reason without proving which caller initiated each newer bench/vehicle
reset. See the [owning function-level trace](../../platform/security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14).

Only counter 49 has a plausible RTC; all others read 2010/2011, so the dates above come from the reason
strings. Recovery logs `Not get boot-see-dealer mode, start normal update process.` for 54/55 and then
saves logs to the USB volume (`DEBUG: Dump log to USB`). **Inferred (not proven):** `--show_return_to_dealer`
here is the dealer-screen argument that accompanies the log-export path, not evidence of a bricked radio:
Android was running afterwards (live adb 2026-11-12: `sys.boot_completed=1`, 11 min uptime at 13:59 AKST;
`update/moduleinfo` carries a 13:10:49 AKST stamp, which recovery's 2010/2011 clock cannot have produced).
The operator-described induced homescreen failure (below and in §2.2.1) remains the stated cause of entering
recovery; the log ledger neither confirms nor contradicts the "three failed attempts" count (51-53 carry no argument).

**A/B slot in the retained recovery kernel logs** (`last_kmsg` newest = index 0 ... `.30`, `androidboot.slot_suffix`
in each recovery kernel cmdline; directly read): oldest->newest A x2, B x5, A x7, B x5, A x12, i.e. two B
episodes inside the 31-boot window; recovery's mount table in the 47-55 logs shows `system_a`/`vendor_a`/`product_a`,
matching live `ro.boot.slot_suffix=_a`. The update-service log records the 2026-09-28 recovery install flipping
active slot 1 -> 0, and `slot_switched` is `N` in both exports (no pending switch). The ~4x A->B->A history for
the whole year is not reconstructible from these retained windows.

### 0.3 Second USB export: recovery-only changes (verified 2026-11-12)

The second external archive, `update_cache 2.zip`, has SHA-256
`f143d5b2e6b8c4ed4a0ce626b0a70a7b1cd43a00c00b61a6bedda469edc81fd3`.
It has the same 445 member paths and 144,129,520 uncompressed bytes.
A full member-byte comparison against §0.2 finds **58 changed, 387 identical,
zero added and zero removed**. All changes are beneath `recovery/`.
Every `bootup_log/` and `update/` file is byte-identical, including compressed
Android logs, GHS/VIP logs, `CalSets.db`, `UpdateDB`, manifests, module inventory
and status. This is additional recovery evidence, not a new Android runtime
capture, calibration revision or firmware update.

| Evidence | First export | Second export |
|---|---|---|
| Final `last_log` recovery counter | 54 | 55 |
| `recovery/boot_cycle_counter` raw file byte | `0x37` | `0x38` |
| BCB command / argument | `boot-recovery` / `--show_return_to_dealer` | Same |
| Reported update retries / global status | 7 / 3 | Same |
| Active slot / successful flag | 0 / 1 | Same |
| Early Linux available memory / total | `5638316K/5877304K` | `5638324K/5877304K` |
| Cumulative `recovery/log` | First baseline | Exact baseline prefix plus 6071 bytes |

Do not parse the one-byte counter file as decimal text `7`/`8`, or equate
it with the GHS failed-boot count. The runtime prints 54/55 while the retained
file bytes are `0x37`/`0x38`; their read/increment/write timing is not derived
here. Recovery's boot counter and update retry value demonstrably vary
independently in this pair.

Second-archive `recovery/last_log` SHA-256:
`3f09a2bc3c6555bc8b1ca9a00b1e9b71b57999114b92783a939f1784c11c6054`.
It adds `Dump log to USB`, `Saving log completed.` (line 111) and
`Syncing...` (line 112), followed by another log-save attempt. Both exports
retain `exec(logcat) failed: No such file or directory` and
`logcat: Failed with status 255`; copying retained diagnostics succeeded
despite failure of that optional current-logcat capture.

**Rotation is not reboot count:** second-archive `last_log.2` is a longer
counter-54 save, and `.3` is byte-identical to the first archive's final
`last_log`. Second-archive `last_log` and `.1` both report counter 55, with
different save cutoffs. `last_kmsg` and `.1` are byte-identical. These shifts
represent multiple saves plus a newly recorded counter-55 recovery run,
not three independently established boots. The fixed rotation window drops
older numbered installer histories; retain the first archive for those
member-specific citations. Unchanged properties, E820 ranges and calibration
data do not add independent confirmations from normal Android operation.

### 0.4 `.vmm1`/`.ota_update` RE tooling history (Aug 2026 session)

**History, absorbed from the retired `GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md`
(that document is retired with a pointer to this subsection).** This subsection
records only the tool-setup/status history of the session that first obtained
real disassembly of this binary. Its confirmed AVB-guard-verification findings
(the `elk_inner.elf` RE that matched `avb_descriptor_validate_and_byteswap`,
`avb_safe_add_to` and `avb_vbmeta_image_verify` against upstream libavb) are
owned by [VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md](../security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md)
and are not restated here.

| Blocker | Resolution |
|---|---|
| The raw `85098662` container is a proprietary Green Hills INTEGRITY download image, not a format any standard tool (`file`, `r2`, `objdump`) auto-parses. A manually reverse-engineered end-of-file directory/symbol table (~48 KiB region near `0xe35000`) is a 64-bit canonical-VA + 32-bit size + name-string debug symbol table, cross-validated against known sections in `evidence/decompiled/ghs_analysis.txt`; it has no file-offset field, so it does not by itself enable section-byte extraction. | An existing Ghidra project (`ghidra_projects/ghs32.rep`, program `ghs_integrity.elf`, language `x86:LE:32:default`) exists in the external research archive; the documented `firmware_carved/ghs_integrity.elf` (standard-ELF conversion) no longer exists on disk — the same provenance-drift pattern seen elsewhere in this corpus (documented, not persisted). Ghidra 12.1.3 + PyGhidra (`brew install ghidra`, `pip3 install` the bundled PyGhidra wheel) opened the existing `ghs32` project headlessly (`GHIDRA_INSTALL_DIR=/opt/homebrew/Cellar/ghidra/<ver>/libexec`, `nested_project_location=False`) and extracted real section bytes for `.vmm1.text` (244,706 B), `.vmm1.rodata` (170,832 B), `.ota_update.text` (71,451 B) and `.ota_update.rodata` (6,588 B) — sizes match `ghs_analysis.txt` exactly. |
| The corpus's pre-written `tools/analysis-scripts/avb_audit.py`, run against the real loaded program via PyGhidra, produced zero results. `.vmm1.text`'s 140 identified function boundaries were mostly undefined/never disassembled, and reference counts to known AVB string addresses were zero. | Diagnosed, not initially resolved — confirms `INVENTORY.md`'s own prior note that the decompiled `vmm1_all.c` is "UNUSABLE due to Green Hills toolchain — no string refs." |
| Bitness dispute surfaced while diagnosing the above: `radare2` disassembly of `.vmm1.text` at Ghidra-identified function entries decoded cleanly and idiomatically **only under a 64-bit interpretation** (`push rbp; mov rbp,rsp`, `fs:`-segment TLS access), even though the binary's ELF header is byte-verified EM_386/ELFCLASS32. | Not resolved here or in VPF. This is the corpus-wide **VMM1/.vmm1 task-code bitness** open conflict (32-bit ELF class vs. disassembled-64-bit task code); it is carried in [VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md](../security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md)'s own Open Conflicts — see this document's own [Open conflicts](#open-conflicts) section below for the pointer. |
| An exhaustive string/table/xref search found no AVB guard-string references anywhere in `.vmm1`/`.ota_update`. | The full guard-string set and the literal source path `hardware/intel/kernelflinger/avb/libavb/avb_vbmeta_image.c` trace into a *separate* binary, `elk_inner.elf` (the ELK/kernelflinger component, also covered live in §2.3.3 and the VIP-ELK mega-section below), reconstructed from its `objdump` listing, re-imported into Ghidra and decompiled there — producing VPF's confirmed guard matches (history only; see VPF for the finding itself). This identifies *which binary* carries the real AVB guards; it does not settle the bitness dispute above, which concerns a different binary/question and remains open. |

## 1. GHS Boot Process

### 1.1 Complete Boot Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GHS INTEGRITY BOOT SEQUENCE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE 1: HARDWARE INITIALIZATION                                            │
│  ════════════════════════════════                                            │
│                                                                              │
│  1. Hardware Reset (Intel Apollo Lake SoC)                                   │
│     └── Power-on reset, CPU initialization                                   │
│                         │                                                    │
│                         ▼                                                    │
│  2. Intel ABL (Automotive Bootloader)                                        │
│     ├── Secure Boot enabled (ABL.secureboot=1)                              │
│     │   [NOTE 2026-11-12 CAVEAT: 'ABL.secureboot=1' appears only as a token in retained kernel-log cmdlines (live `getprop ro.boot.ABL.secureboot` is empty; hit count ~188 per archive, earlier '386' not reproduced); it is a cmdline indicator, not a verified secure-boot state. See platform/boot_chain.md.]
│     ├── Loads GHS INTEGRITY from flash                                       │
│     ├── Verifies GHS signature                                               │
│     └── Transfers control to GHS kernel                                      │
│                         │                                                    │
│                         ▼                                                    │
│  STAGE 2: GHS KERNEL INITIALIZATION                                          │
│  ═══════════════════════════════════                                         │
│                                                                              │
│  3. BSP_InitializeOnBootCpu                                                  │
│     ├── CPU feature detection                                                │
│     ├── Memory controller initialization                                     │
│     └── Early hardware setup                                                 │
│                         │                                                    │
│                         ▼                                                    │
│  4. ASP_PreCrtInitializeBootstrap                                            │
│     ├── C runtime initialization                                             │
│     ├── Stack setup                                                          │
│     └── Global constructors                                                  │
│                         │                                                    │
│                         ▼                                                    │
│  5. ASP_VMX_InitializeOnBootCpu                                              │
│     ├── Intel VT-x (VMX) initialization                                      │
│     ├── VMCS (VM Control Structure) setup                                    │
│     ├── MSR bitmap configuration                                             │
│     └── EPT (Extended Page Tables) initialization                           │
│                         │                                                    │
│                         ▼                                                    │
│  6. ASP_VTD_Init                                                             │
│     ├── Intel VT-d (IOMMU) initialization                                    │
│     ├── DMA remapping unit activation                                        │
│     └── Device isolation setup                                               │
│                         │                                                    │
│                         ▼                                                    │
│  7. BSP_BootSecondaryCpus                                                    │
│     ├── Wake up CPU cores 1-3                                                │
│     ├── AP (Application Processor) boot                                      │
│     └── Multi-core synchronization                                           │
│                         │                                                    │
│                         ▼                                                    │
│  8. SetupBootTables                                                          │
│     ├── InitializeTheAddressSpaceTable                                       │
│     ├── InitializeTheTaskTable                                               │
│     └── InitializeTheODGTable                                                │
│                         │                                                    │
│                         ▼                                                    │
│  9. RunInitialTasks                                                          │
│     └── Start all GHS tasks (see Stage 3)                                   │
│                         │                                                    │
│                         ▼                                                    │
│  STAGE 3: GHS TASKS INITIALIZATION (PARALLEL)                                │
│  ═════════════════════════════════════════════                               │
│                                                                              │
│  10. Core System Tasks                                                       │
│      ├── VMM1_InitialTask      ← Primary: Android Virtual Machine Manager   │
│      ├── Lifecycle_InitialTask ← Power and boot state management            │
│      ├── VIP_InitialTask       ← VIP MCU communication                      │
│      └── OTA_InitialTask       ← OTA update handling                        │
│                                                                              │
│  11. Hardware Tasks                                                          │
│      ├── Camera_InitialTask    ← Intel IPU4 camera management               │
│      ├── Audio_InitialTask     ← Audio subsystem                            │
│      ├── GPU_InitialTask       ← Intel HD Graphics                          │
│      ├── Chimes_InitialTask    ← Alert sounds                               │
│      ├── Dirana_InitialTask    ← Audio DSP                                  │
│      └── DisplayI2C_InitialTask← Display control                            │
│                                                                              │
│  12. Security Tasks                                                          │
│      ├── TEE_Keymaster         ← Trusty Keymaster                           │
│      ├── TEE_HW_Crypto         ← Hardware crypto                            │
│      └── TEE_Storage           ← Secure storage (RPMB)                      │
│                         │                                                    │
│                         ▼                                                    │
│  STAGE 4: ANDROID BOOT (via VMM1_InitialTask)                                │
│  ════════════════════════════════════════════                                │
│                                                                              │
│  13. CheckRecoveryMode()                                                     │
│      ├── Read BCB from misc partition                                        │
│      ├── Check for "boot-recovery" command                                   │
│      └── Determine boot target (normal/recovery/ELK)                        │
│                         │                                                    │
│                         ▼                                                    │
│  14. A/B Slot Selection                                                      │
│      ├── Read A/B metadata from 'misc' partition                            │
│      ├── Check slot priority and attempts remaining                          │
│      ├── Select active slot (_a or _b)                                       │
│      └── "A/B Boot Slot: boot%s"                                            │
│                         │                                                    │
│                         ▼                                                    │
│  15. Android Verified Boot (AVB)                                             │
│      ├── Load vbmeta partition                                               │
│      │   └── "VMM: ERROR: no vbmeta partition found (slot %s)"              │
│      ├── Verify vbmeta signing key                                           │
│      │   └── "VMM: Error: vbmeta signing key does not match"                │
│      ├── Validate vbmeta header and descriptors                              │
│      │   └── "VMM: vbmeta: image verification failed!"                      │
│      ├── Load boot partition                                                 │
│      │   └── "VMM: A/B: no boot image for slot %s"                          │
│      ├── Verify boot image signature                                         │
│      │   └── "VMM: Error: Android signature verification failed"            │
│      ├── Check kernel and ramdisk hashes                                     │
│      └── Verify rollback index                                               │
│          └── "VMM: ERROR: rollback index is too old"                        │
│                         │                                                    │
│                         ▼                                                    │
│  16. Launch Android Kernel                                                   │
│      ├── Set kernel command line:                                            │
│      │   androidboot.slot_suffix=%s                                          │
│      │   androidboot.verifiedbootstate=%s                                    │
│      │   androidboot.vbmeta.avb_version=1.1                                  │
│      │   androidboot.trustyimpl=-ghs                                         │
│      ├── Configure guest memory map                                          │
│      ├── ASP_VMX_SetGuestKernelAddr                                          │
│      └── ASP_RunGuestVM → Android kernel starts                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Boot Configuration Strings

```
clocksource=tsc tsc=reliable
acpi_pm_good
i915.avail_planes_per_pipe=0x000003
i915.enable_pvmmio=0
androidboot.diskbus=1c.0
androidboot.boot_devices=pci0000:00/0000:00:1c.0
androidboot.trustyimpl=-ghs
androidboot.product.hardware.sku=gv221
```

### 1.3 Boot Timing Logging

GHS maintains boot time logs:
```
.boottimelog
.boottimelog_task_strings
BSP_BootTimeLog_Checkpoint
BSP_BootTimeLog_RangeStart
BSP_BootTimeLog_RangeEnd
AddressSpace_BootTimeLog_Task_Checkpoint
```

---

## 2. GHS Android Management

### 2.1 VMM Guest Control Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GHS VMM ANDROID CONTROL ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      GHS INTEGRITY HYPERVISOR                        │    │
│  │                                                                      │    │
│  │   VMM Control Functions:                                             │    │
│  │   ├── ASP_RunGuestVM           - Start/resume Android VM            │    │
│  │   ├── ASP_ResetVCpu            - Reset Android virtual CPU          │    │
│  │   ├── VMM_PendVCpu             - Pause Android execution            │    │
│  │   ├── VMM_UnpendVCpu           - Resume Android execution           │    │
│  │   ├── ASP_InjectInterruptInVCpu- Inject interrupt into Android      │    │
│  │   └── VMM_ExitVMCallback       - Handle VM exits                    │    │
│  │                                                                      │    │
│  │   Memory Access Functions:                                           │    │
│  │   ├── ReadGuestMemory          - Read Android RAM                   │    │
│  │   ├── WriteGuestMemory         - Write to Android RAM               │    │
│  │   ├── ReadGuestVirtualAddress  - Read guest virtual addresses       │    │
│  │   ├── WriteGuestLMA            - Write linear memory address        │    │
│  │   ├── DirectCopyIntoVAS        - Direct copy to address space       │    │
│  │   └── VMM_GuestRamOffsetToHostPAddr - RAM translation               │    │
│  │                                                                      │    │
│  │   Guest Register Access:                                             │    │
│  │   ├── ASP_VMX_GetRegister      - Read guest CPU registers           │    │
│  │   ├── ASP_VMX_SetRegister      - Write guest CPU registers          │    │
│  │   ├── GetGuestRegister         - Get specific register              │    │
│  │   └── SetGuestRegister         - Set specific register              │    │
│  │                                                                      │    │
│  │   EPT (Extended Page Tables):                                        │    │
│  │   ├── ASP_VMX_MapEptHelper     - Map guest memory                   │    │
│  │   ├── ASP_VMX_UnmapEptHelper   - Unmap guest memory                 │    │
│  │   └── XhcVc_SetGuestMemoryMap  - Set guest memory layout            │    │
│  │                                                                      │    │
│  └──────────────────────────────────┬──────────────────────────────────┘    │
│                                     │                                        │
│                                     │ VMX Control                            │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        ANDROID GUEST VM                              │    │
│  │                                                                      │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐     │    │
│  │   │ Linux Kernel│  │   Android   │  │    GM Applications      │     │    │
│  │   │             │  │  Framework  │  │                         │     │    │
│  │   └─────────────┘  └─────────────┘  └─────────────────────────┘     │    │
│  │                                                                      │    │
│  │   Android has NO visibility into GHS operations                      │    │
│  │   Android CANNOT inspect or modify GHS memory                        │    │
│  │   Android CANNOT detect GHS monitoring                               │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Lifecycle Management

GHS monitors Android health via **Sign of Health (SoH)** mechanism:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LIFECYCLE STATE MANAGEMENT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Lifecycle_InitialTask                                                       │
│         │                                                                    │
│         ├── Monitor Android Sign of Health (SoH)                            │
│         │   └── "GHS: [LIFECYCLE] Lost Android SoH - rebooting"             │
│         │                                                                    │
│         ├── Track boot attempts                                              │
│         │   └── "GHS: [LIFECYCLE] Android failed to boot (count=%lu)"       │
│         │                                                                    │
│         ├── Handle panic recovery                                            │
│         │   └── "GHS: [LIFECYCLE] Guest failed to reboot after panic"       │
│         │                                                                    │
│         ├── Safety critical use case tracking                                │
│         │   └── "GHS: [LIFECYCLE] inSafetyCriticalUseCase=%i"               │
│         │                                                                    │
│         ├── Shutdown coordination                                            │
│         │   ├── SendShutdownRequest                                          │
│         │   ├── WaitForShutdownRequestAcked                                  │
│         │   ├── SendShutdownPreparationDone                                  │
│         │   ├── WaitForGuestShutdownPreparationDone                          │
│         │   ├── WaitForGuestUnmountRequest                                   │
│         │   ├── WaitForGuestOff                                              │
│         │   └── DoACPIShutdown                                               │
│         │                                                                    │
│         └── VIP reset handling                                               │
│             ├── "GHS: Initiating VIP reset"                                  │
│             ├── "GHS: Initiating immediate VIP reset"                        │
│             └── "GHS: VMM: waiting for VIP system reset..."                  │
│                                                                              │
│  IPC Connections:                                                            │
│  ├── ConnToLifecycle_Lifecycle_API                                          │
│  ├── ConnToVMM1_Lifecycle_VMMControl                                        │
│  ├── ConnToCamera_Lifecycle_API                                             │
│  ├── ConnToChimes_Lifecycle_API                                             │
│  ├── ConnToVip_Lifecycle_API                                                │
│  ├── ConnToAudio_Lifecycle_API                                              │
│  ├── ConnToDirana_Lifecycle_Notify                                          │
│  └── ConnToDisplayI2C_Lifecycle_Notify                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2.1 Y181B failed-boot threshold (verified 2026-11-12)

The lifecycle failed-Android-boot handler increments its counter, logs
`Android failed to boot (count=%lu)`, then compares the incremented count with
**3**. Below 3 it takes the retry branch; at least 3 takes the branch logged as
`Booting 'see-dealer' mode`, which subsequently clears this counter.

Binary evidence (lifecycle task-space addresses): handler `0x200DFD`;
increment `[rbx+0xF0]` at `0x200E0D`; comparison with 3 at `0x200E2D`;
unsigned >= branch at `0x200E35` to `0x200E52`; dealer log at `0x200E61`;
count clear at `0x200E8B`. The comparison is `.lifecycle.text+0xE2D`,
ELF file offset `0x5D806E`.

Provenance: the 14,929,320-byte HostOS ELF is byte-identical to bytes starting
at offset `0x27C` in approved Y181B `USB_Files/85098662`. ELF SHA-256:
`d900af484f466b35f4d9153ddf8adf19482f91d728b707f10fe89d326d4870df`.

This GHS counter is separate from the VIP's three-failure startup/SoC-only-reset
**timer suppression**, and from recovery's incremented file
`/update_cache/recovery/boot_cycle_counter`. Successful-boot reset semantics and
whether a particular manually induced reboot counts as a failure remain untraced.
Recovery explicitly recognizes BCB command `boot-see-dealer`; ordinary
`adb reboot recovery` does not itself establish that persistent dealer state.

**Hardware evidence added 2026-11-12:** the §0.2 operator-observed
homescreen-removal experiment exercises the three-failure route. In
`bootup_log/gmlogger/26-system.log_2026_11_12_13_6_17.gz`, decompressed
lines 26257–26259 report `com.gm.homescreen not installed!` for users 10 and 0.
`46-main.log_2026_11_12_13_5_24.gz`, decompressed line 203365, reports
`No home screen found`. The same main log has `reportHMIReady` at line
200740 and delivery of Android `BOOT_COMPLETED` at line 203354. Neither
message alone demonstrates successful usable-radio startup. The exact failed
readiness/health condition and its join to the GHS counter remain untraced;
the exported GHS text logs do not contain the failed-boot count sequence.

The final `recovery/last_log` records BCB command `boot-recovery` (line 24),
recovery boot-cycle counter 54 (line 29), argument `--show_return_to_dealer`
(line 77), and `Not get boot-see-dealer mode, start normal update process.`
(line 96). All 74 boot-command records in cumulative `recovery/log` say
`boot-recovery`; none records literal `boot-see-dealer`. This limits what
the export proves about the command used at capture time, not the operator's
observed automatic dealer entry. The dealer UI argument, BCB mode, recovery
boot-cycle counter, update retries and GHS three-failure counter are distinct.

### 2.3 Special Boot Modes

| Mode | Trigger | String Evidence | Purpose |
|------|---------|-----------------|---------|
| **Normal A/B** | Default | `A/B Boot Slot: boot%s` | Standard boot to active slot |
| **Recovery** | BCB command | `boot-recovery` | Android recovery mode |
| **See-Dealer** | Service flag | `boot-see-dealer`, `GHS: [LIFECYCLE] Booting 'see-dealer' mode` | Dealer diagnostic mode |
| **ELK** | Emergency | `GHS: [LIFECYCLE] Got request to boot to ELK`, `BootELKWaitForRespSent` | **(2026-09-10)** Intel Kernelflinger **fastboot** (kernelflinger-07.02, titan_gm_my22) — flash/erase/getvar + `oem set-storage`; NOT a general Linux shell. "USB storage is unsupported" (no external USB rootfs path); libavb-linked, AVB ACTIVE in ELK; unlock is device-state-gated. GHS orchestrates an ELK request; the final execution boundary remains unresolved (§2.3.3). |
| **Diagnostic** | Service tool | `Diagnostic channel active` | Low-level diagnostics |

### 2.3.1 Recovery fastbootd path (verified 2026-11-12)

Y181B contains a separate **userspace fastbootd** path in Android recovery; do
not conflate it with the previously documented ELK/Kernelflinger target above.

- At recovery `0x2B3B38` the boot-command comparison recognizes `boot-fastboot`;
  `0x2B3B63` logs that command and `0x2B3B7F` synthesizes `--fastboot`.
- The fastboot entry block tests its mode flag at `0x2B438E`, logs
  `Enter fastboot mode` at `0x2B439B`, then sets `sys.usb.config=fastboot`
  at `0x2B447C`-`0x2B448A`. Hardware/PLC initialization occurs before this
  block and can fail; the block alone does not establish live reachability.
- After successful property setting it logs `Wait fastboot reboot command`
  at `0x2B4497` and loops through a five-second wait at `0x2B44B0`-`0x2B44BA`.
  This is a code-observed persistent fastboot wait, distinct from ordinary
  recovery returning to normal boot with no usable update input.
- Recovery ramdisk `system/etc/init/hw/init.rc` defines a disabled
  `/system/bin/fastbootd` service in `u:r:fastbootd:s0`. Its
  `sys.usb.config=fastboot` trigger starts that service and the boot HAL;
  configfs/FunctionFS rules configure the USB interface. The ramdisk contains
  the 1,383,696-byte fastbootd executable.

Fastbootd is a protocol service, not an interactive shell. The original
ramdisk binary's erase handler calls lock predicate `0xA9730` at `0x9B9F8`;
the flash handler calls it at `0x9E32B`. Both branch to denial when it returns
true. The predicate reads `ro.boot.verifiedbootstate` and returns false only
for the exact string `orange`; missing or different values remain restricted.
The download handler calls the same predicate at `0x9C356`, and
`set_active` calls it at `0x9C646`; both likewise deny a true result.
The fetch handler at `0x9EE70` is compiled as a refusal
(`Fetch is not allowed on user build`), rather than a runtime choice based
on a changed build-type string. These are verified code paths beyond merely
finding denial strings. No accepted unsigned-image path, unlocking command,
or root-shell command was established, and the handlers were not exercised
on hardware.

The ELK request log is separately referenced at lifecycle task address
`0x200B1F` (`Got request to boot to ELK`). Its previous Kernelflinger analysis
remains separate from this recovery-fastbootd verification. No GHS string naming
`ro.debuggable`, `ro.secure`, `force_debuggable`, or `userdebug` was found in this
pass; absence of those literals is not proof that indirect boot inputs cannot
influence developer state.

The recovery root console remains explicitly disabled and gated by
`ro.debuggable=1`; the shipped ramdisk has `ro.debuggable=0`. No USB filename
that changes that property or enables a root shell was established. The
fastboot entry path and the root-console path must therefore be treated as
separate mechanisms. This section records static code findings, not a tested
recovery/fastboot entry procedure.

### 2.3.2 ELK unlock eligibility is a separate gate (verified 2026-11-12)

Historical bench observation: `adb reboot fastboot` on the target radio entered
userspace fastboot with limited options. The exact command/response inventory
and firmware revision of that historical test are not pinned by this observation;
it corroborates fastbootd entry, not ELK entry or bootloader unlock.

The original Y181B SOC_ABL payload `USB_Files/85738845` contains an ELF at
package offset `0x301288` identifying Kernelflinger 07.02. Its PIC code uses
GOT base `0x128FD8D4`; these ELF virtual addresses establish actual unlock
checks, not just diagnostic strings:

- Eligibility routine `0x12805910` first calls the provisioning-state accessor
  at `0x128A64D0`. True returns eligibility result 0 before the ordinary checks.
- **Corrected 2026-11-12:** the earlier interpretation of `0x128A5500`
  was reversed. Its false return does **not** force eligibility result 2.
  At `0x12805953`, zero branches to `0x12805971`, the FRP permission check;
  only a true return takes the class-refusal result 2. This matches Intel's
  reference `get_unlock_ability()` control flow.
- The ordinary path looks up the GPT partition named `persistent` at
  `0x12805982`, then reads its final byte at `0x128059CC`. A successful read
  permits unlock only when that byte is exactly 1 (`0x128059D8`). A partition
  lookup error returns eligibility 0 at `0x128059E5`; a read error returns 1
  at `0x12805A09`. These are static branches, not measured target conditions.
- **Permission-byte writer identified 2026-11-12:** original Y181B
  `USB_Files/86331654` contains `/system/framework/services.jar`, whose
  `com.android.server.PersistentDataBlockService.doSetOemUnlockEnabledLocked`
  opens its configured block file for read/write, seeks to block size minus 1,
  writes one byte (`enabled ? 1 : 0`), and forces the channel to storage.
  The original vendor image `USB_Files/86331650` sets
  `ro.frp.pst=/dev/block/by-name/persistent` and `ro.oem_unlock_supported=1`.
  Thus the shipped Android-framework service supplies an exact writer for
  ABL's final-byte permission input. This is distinct from the actual ABL
  lock-state write callback below.
- The shipped `SystemServer.startOtherServices` bytecode starts
  `PersistentDataBlockService` when `ro.frp.pst` is nonempty and also selects
  `OemLockService`. The framework caller chain includes
  `OemLockService.setOemUnlockAllowedByUser` ->
  `PersistentDataBlockLock.setOemUnlockAllowedByDevice` ->
  `PersistentDataBlockService.setOemUnlockEnabled` -> the byte writer.
  When a vendor OEM-lock HAL is selected instead, `OemLockService` mirrors its
  allowed bit through `PersistentDataBlockManagerInternal.forceOemUnlockEnabled`,
  which reaches the same writer. These paths check privileged permissions and
  administrator/carrier restrictions. Public setters recompute the partition
  digest and update `sys.oem_unlock_allowed`. No live write or GM-specific UI
  action invoking them was observed; this is original-image code/configuration
  evidence. Normal Java decompilation of the large SystemServer startup method
  failed; its service-start conditions were verified with fallback bytecode.
- **Shipped UI caller identified 2026-11-12:** the original system image also
  contains `/system/system_ext/priv-app/CarDeveloperOptions/CarDeveloperOptions.apk`
  (runtime `/system_ext/priv-app/...`), package
  `com.android.car.developeroptions`. Its automotive Developer options dashboard
  retains the `oem_unlock_enable` switch, titled **OEM unlocking**, with summary
  **Allow the bootloader to be unlocked**. The parent dashboard constructs
  `OemUnlockPreferenceController` and forwards the confirmation callback to
  `onOemUnlockConfirmed()`, which calls `setOemUnlockAllowedByUser(true)`.
  Disabling the switch calls the setter with false. Original DEX evidence:
  controller confirmation method code item `0x3AC3BC`, invoke at code unit 3.
- `CarDevelopmentSettingsDashboardActivity` is exported but manifest-disabled
  by default. Original Car Settings config points to that component, and its
  `DevelopmentSettingsUtil` sets component-enabled state when developer options
  are enabled and user/debugging restrictions permit. The OEM switch additionally
  checks `ro.oem_unlock_supported=1`, current lock state, carrier permission and
  factory-reset restrictions, with keyguard/warning confirmation. The APK requests
  `MANAGE_USER_OEM_UNLOCK_STATE` and `OEM_UNLOCK_STATE`. This establishes a shipped
  screen-to-writer code path, not verified live navigation from GM's normal HMI
  or a documented dealer procedure.
- **Owner UI observation, 2026-11-12:** HomeScreen -> Settings -> Developer
  Options exposes USB debugging but no OEM unlocking entry for either user 0
  or user 10. Do not present the compiled CarDeveloperOptions preference as an
  available control in that GM menu. The image contains a separate GM Settings
  developer-options activity/repository and the manifest-disabled automotive
  developer-options module; a confirmed navigation or enablement path from the
  observed GM screen to the latter has not been established. Changing users
  did not expose the OEM-unlock control in the reported observation.
- **Shell/component reachability traced 2026-11-12:** original
  `PackageManagerService.setEnabledSetting` rejects caller UID 2000 changing
  individual component state in a non-test package. Its allowed shell subset
  concerns whole-package DEFAULT/ENABLED/DISABLED_USER transitions. The shipped
  CarDeveloperOptions manifest has no test-only flag, so direct shell
  `pm enable <package>/<activity>` is not an established enablement route;
  enabling the package alone does not override its activity's manifest default.
  The same manifest exports its dashboard, so shell launch can become possible
  after an authorized component enablement.
- The original standard Car Settings app supplies an app-owned route:
  `DeveloperOptionsEntryPreferenceController.handlePreferenceClicked()` checks
  module-enabled state, calls
  `DevelopmentSettingsUtil.setDevelopmentSettingsEnabled(context, true)` if
  needed, then starts the preference intent. That utility changes the component
  state through the privileged app, not through shell UID 2000. Its entry is
  available only when developer options/user restrictions permit. Standard
  Car Settings exports its HomepageActivity (`android.settings.SETTINGS`) and
  SystemSettingsActivity; opening that app and selecting its own Developer
  options entry is a static candidate for enabling/displaying the separate
  dashboard. Live launch, any GM redirection/overlay and current per-user state
  remain untested. This does not assert that GM's visible Developer Options
  menu calls this controller.
- A scan of 185 APK/JAR artifacts in the original system, system_ext and product
  images found the direct app setter reference in CarDeveloperOptions. The GM
  Settings APK instead has `ReturnToFactoryRepository.eraseSettingsAndPersonalData()`:
  when persistent-data service exists, OEM unlock is not allowed and the device is
  provisioned, it calls `PersistentDataBlockManager.wipe()` before factory reset.
  This is a separate erase path, not an enabling call. Direct-reference scanning
  does not exclude reflective, native or externally supplied callers.
- The unlock command at `0x128057F0` calls eligibility at `0x12805819` and
  rejects nonzero at `0x12805822`. On success it calls `0x12805530` with
  state 1 at `0x1280584E`. That routine reaches the state setter at
  `0x128A6360`, which accepts state 0/1, calls the state-write wrapper
  `0x128B4110` at `0x128A6395`, then updates cached state on success at
  `0x128A639E`. The wrapper dispatches through a platform callback; its final
  storage backend and persistence have not been resolved in this pass.
  This is a state-change path, not merely an orange-state predicate.
  Availability through a live ELK transport, and propagation to the ordinary
  GHS-managed Android boot, remain unproven.
- Cached device-state routine `0x128A6260` uses bit 0 of a successful stored-state
  read at `0x128A62D8`-`0x128A62E0`. But its missing-state/error handling also
  consults separate platform conditions and a life-cycle query at `0x128AE270`;
  one gated fallback at `0x128A633F` sets both the provisioning flag and state 1.
  Consequently shortened claims that unlocked state requires an existing,
  readable `OEMLock` with bit 0 set are incomplete. Detailed 2026-10-08 analysis
  in `platform/security.md` and `AOSP_REPLACEMENT_RESEARCH.txt` already describes
  the provisioning fallback (missing OEMLock, non-virtual boot, non-ENDUSER
  life-cycle). This pass corroborates the branch structure and records its
  addresses; it has not independently resolved every platform-condition helper
  or measured those conditions on the target.

[Intel's upstream fastboot documentation](https://github.com/intel/kernelflinger/blob/master/doc/fastboot.md)
also distinguishes provisioning state, lock state and build-limited development
commands. Upstream command availability must not be assumed for GM's compiled
07.02 module. No method to enter ELK/provisioning from the locked running target,
no link from MEC/SBI to these gates, and no root shell have been demonstrated by
this static trace. No EFI variables or device state were modified.

### 2.3.3 Recovery execution boundary and mode selection (verified 2026-11-12)

The original Y181B HostOS VMM task compares BCB fields with `boot-recovery`
at task address `0x204B1A` and `boot-see-dealer` at `0x204B32`, then repeats
those comparisons for the secondary field at `0x204B4A` and `0x204B69`.
Matching either mode reaches `0x204B83`, setting the same recovery flag at
`[r12+3]`. The following Android-loader calls use that state; their failure log
explicitly reports the recovery parameter (`0x204BC6`). VMM command-line
construction at `0x2038B8` also tests the recovery flag before adding
`skip_initramfs` / `androidboot.force_normal_boot=1` for normal boot.

Thus normal AAOS and recovery are alternative boots of the Linux/Android guest
managed by GHS VMM. Recovery is not established as a separate bare-metal OS that
replaces GHS. Ordinary recovery and dealer recovery use the same recovery
executable, which independently recognizes `boot-see-dealer` at `0x2B481C`-
`0x2B4849` to select the dealer UI. Userspace fastbootd is a separate executable
and service in that recovery environment, not the Kernelflinger implementation.

A brief ordinary recovery invocation is not established as a timeout of the
same dealer-screen state. The code has no-manifest/initialization failure paths
that return to normal boot, and a separate persistent fastboot wait. The exact
USB-scan/no-package/exit sequence of any historical short recovery session has
not been reconstructed from recovery logs. The encoded reboot marker is verified
in recovery's scanner; its existence does not prove it is checked on every
possible entry/error path before an early exit. BCB, recovery command files and
update manifests are separate inputs, not demonstrated debug/root switches.

**ELK request traced further; final execution boundary remains unresolved:**
the lifecycle state-name table identifies state 14 as
`BootELKWaitForRespSent` and state 15 as `BootELKSendAblUserCommand`.
State 15 sends a 32-byte buffer beginning `0x80` through `0x202C2C`.
Its second argument `0x1B` is a connection identifier, **not a message type
or byte count**. The original kernel's symbol-bearing `KernelCallTable`
at `0xFFFF80000084A7E0` maps selector `0x0F000000` to
`KernelAsynchronousSend` (`0xFFFF80000021161F`); that routine validates
the argument as an object and checks `ConnectionDriver`. The receive stub
selector `0x0EC00000` maps to `KernelAsynchronousReceive`.
This corrects the earlier interpretation of the API argument.

The OTA task's activity-4 branch calls `0x20D04F` with selector 2
at `0x201943`. That routine constructs a `0x85`-byte frame and submits it
through `0x20CEA5`, which uses the HECI transaction routine `0x20CC5A`
and checks transport success, a four-byte reply, and a zero reply-status byte.
Its failure paths explicitly report an ABL update-command failure. The event
branch returns a buffer beginning `0x80` plus the call result. The original
boot table proves the join: its pointer base is `0xFFFF80000F6A3000`;
address-space 2's 64-byte object table starts at section offset `0x4500`,
and address-space 12's starts at `0x148C0`. Lifecycle resource `0x1B`
at `0x4B80` names `ConnToOTA_BootELK` and targets AS 12/resource
`0x11`; the reciprocal record at `0x14CC0` names
`ConnToLifecycle_BootELK` and targets AS 2/resource `0x1B`.
OTA initializes receive activity 4 on connection `0x11` at
`0x201737`-`0x201786`, matching the activity-4 handler above.
Offsets here are relative to the original HostOS ELF's `.boottable` section.

Lifecycle activity `0x12` at `0x2018BF` clears the pending flag and dispatches
state 2, `VipResetInitiated`. That event branch does not test the returned HECI
success field; the only direct reference to its reply buffer `0x6090F0`
in the lifecycle text is the receive setup at `0x20182F`. Therefore a completed
IPC response and subsequent shutdown do not themselves prove CSE accepted
the ELK command. The subsequent state machine includes safety
checks and state 13, `DoACPIShutdown`. At `0x20068F` it invokes an I/O-device
write with resource ID `0x0C`, register 0 and value 0 or 1. Kernel selector
`0x13C00000` resolves to `KernelWriteIODeviceRegister`
(`0xFFFF800000216BC3`), which calls a device-specific callback.
The same boot table resolves resource `0x0C` at section offset `0x47C0`
to driver `AplAcpiSleep`, instance `AcpiSleepIod`. Kernel startup copy
metadata at `KernelSpace.secinfo+0x138` copies `0x15E0` bytes from
`0xFFFF80000085E000` to `0xFFFF800002206000`. The I/O object at
destination `0xFFFF8000022063D0` has its write callback at offset `0x30`:
the original initializer at ELF file offset `0x4A3400` points directly to
`AplAcpiSleep_WriteRegister` (`0xFFFF80000022BBB7`).

That callback accepts register 0 and values 0/1, selects internal sleep type
5/7, and invokes `BSP_InterruptCpu` with arguments `0x0F,5`.
Its IPI/callback path disables interrupts (`cli`), flushes caches
(`wbinvd`), counts four CPUs, and on CPU 0 calls
`AplAcpiSleep_Finish` at `0xFFFF80000022BAF9`. Finish writes
`(SleepType << 10) | 0x2000` to I/O port `0x404`; the callback then
executes `hlt` at `0xFFFF80000022BB57`. These are concrete platform
power-state operations, not just a shutdown state-name or a VM selection.

Thus the ELK request is connected through GHS IPC and an OTA-side HECI command
to a lifecycle path that can quiesce the CPUs and request an ACPI power-state
transition. This narrows the architecture: the requested transition does not
merely launch another Android guest while normal GHS scheduling continues.
Actual hardware acceptance, the ME/CSE-side command handling and the next boot
into Kernelflinger have not been observed in this pass. Consequently a
successful ELK transition, its exact post-transition execution environment,
and any GHS memory residency remain unproven. Retained memory must not be
confused with GHS continuing to execute.

### VIP ELK control selector and GWM comparison (2026-11-15)

**Result:** Y175 VIP_APP has a compiled ELK branch for control selector
**`0x8180`**. The contributor's GWM `FDF0` write and the candidate GM I/O-control
request were rejected on the tested Android Ethernet route. A later direct-CAN
test also rejected both bounded control candidates (see below). No live ELK
transition, bootloader unlock or CAN-side acceptance was demonstrated.

External lead: [repository issue #1](https://github.com/lvalen91/gminfo_resources/issues/1)
and [GWM-CAN-Tools `setBootTarget`](https://github.com/DymOK93/GWM-CAN-Tools/blob/master/uds.py#L351).
The GWM implementation enters extended session, unlocks level 1 and writes
DID `FDF0` with `04 00` / `04 01` / `04 03` for normal/recovery/ELK.
The helper also requires its local `Mode.Developer` setting for ELK; that
client-side check does not establish the radio's mode/security requirements. This is
cross-platform evidence, not proof that GM implements that DID or that its
ELK target supplies the GWM Linux/shell environment.

**Static provenance and address correction:** Y175 USB module `85759599`
SHA-256 is `d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`.
Its header contains load address `0x28000` at file offset `0x242`, length
`0x1D7E00` at `0x246`, and the payload SHA-256 at `0x24A`:
`c6b214a75b2139e344e796da46fb6a6ca23f2ca91a8a6b2ee9cf33fda389be55`.
That digest exactly matches the bytes from **file offset `0x586` to EOF**;
`0x586 + 0x1D7E00` equals the complete module length.

The saved RH850 project had loaded the entire signed container at zero.
Its addresses are therefore **file offsets**, not payload runtime addresses.
A separate RH850:LE:32 analysis loaded the payload at `0x28000`:
`runtime = file_offset - 0x586 + 0x28000`. This mapping recovers the three
ELK string pointers and avoids interpreting a scalar as a spurious string
label. A prior logger no-return annotation also hid the following ELK call;
the fresh analysis did not inherit that annotation. Existing unrelated VIP
address claims are not globally revalidated by this targeted correction.

| Function role (provisional name) | Container file offset | Payload runtime address |
|---|---:|---:|
| Selector-8180 callback wrapper | `0x57BC8` | `0x7F642` |
| Generic control pending-state adapter | `0x4E08A` | `0x75B04` |
| J6 control forwarding / ELK branch | `0x757D4` | `0x9D24E` |
| Send ELK control request | `0x75794` | `0x9D20E` |
| Update/report ELK result | `0x7575C` | `0x9D1D6` |

The descriptor at runtime `0x2E7C0` (file `0x6D46`) contains selector `8180`,
a neighboring 16-bit value `3`, a word `1` and callback `0x7F642`.
The later F000 dispatcher trace below identifies `3` as the command-buffer
length and `1` as the minimum application-security value. The wrapper hardcodes `8180` and passes the
request buffer after its first two bytes to the pending-state adapter.
The forwarding routine compares its 16-bit selector with `8180` using
`xori 0x8180,...` (file `0x7582C`, runtime `0x9D2A6`), logs
`[J6_CDD] Control Chan: Diag Elk Reboot Req`, then calls `0x9D20E`.

The request helper checks IPC API selector **`0x0C`**, then sends a one-byte
buffer **`E0`** through that API. If unavailable or the send fails, it calls
the ELK-result updater with value `3`. The API selector is not independently
mapped here to a numbered physical HDLC channel. A receive-side branch
recognizes opcode `E8`, logs the following result byte and forwards values
below `2` to the result updater. These are compiled request/response paths,
not an observed live GHS/ABL transition or proof that an `E0` frame can be
injected successfully from an unprivileged Android process.

**Direct-CAN follow-up,2026-11-17:** With the restored stock LTZ calibration set
and captured harness replay, extended session1003 and level1 SecurityAccess
succeeded. `2F 81 80 03` returned `7F 2F 31`. A separate authenticated attempt
using the legacy/native control-label candidate `AE 81 80 03` returned
`7F AE 11`. The latter confirms that this tested CAN route did not support AE;
the native AE/2F mapping is not proof of wire acceptance. No positive control
response or ELK boot was established. ADB was unavailable before these tests,
so it supplied no boot-identity comparison; no new UART observation was claimed.
No direct IPC injection, RAM write, firmware patch, calibration write or wipe
was performed in these ELK attempts. Default session was restored afterward.

The supplied forwarding trace and fresh callback inspection corroborate
57BC8→4E08A→5C0C0→757D4, with the selector8180 branch reaching75794 after
logging. Offsets here remain signed-container file offsets. The trace supports
an internal sender, not arbitrary execution of that function from CAN. The
remaining gap is the externally reachable dispatch/permission path to that
callback, and then proof that the receiver accepts E0 and boots ELK.

**RAM-trigger feasibility trace,2026-11-17:** The owner authorized investigation
of a VIP RAM-write route. Read-only CAN613/614 inspection found both availability
bytes used by76272 for API12 (FEBD300C andFEBD3024) equal1. Transaction-state
FEBD090C was0 (idle). Thus an unavailable-channel flag was not the observed
blocker, and forcing either availability byte was not needed.

7575C assembles an ELK **result** notification; it is not the E0 request sender.
75794 creates E0 in a stack-local byte and calls570FE. That helper resolves its
channel configuration through FEBD0CF0 and calls837FC. The inspected837FC path
checks channel state and length, allocates a message buffer, enters a protected
section, obtains a descriptor, copies payload, queues the descriptor, releases
the protection and notifies the transport. No polled RAM boot-request flag was
identified. FEBD090C–FEBD092A and FEBE1A30/34/36 are transaction/response
bookkeeping, not demonstrated command mailboxes. They must not be presented as
a proven ELK trigger merely because they are writable.

No RAM write was performed in this feasibility test: there was no verified
request field to set. Reproducing a transport enqueue would require establishing
allocator ownership, descriptor/list consistency, synchronization and task
notification; changing a state/result byte alone does not execute75794. These
findings do not prove that every possible RAM-assisted invocation is impossible.
ELK entry remains unverified, and the stock LTZ calibration was not changed.

**CAN dispatcher trace resolved,2026-11-17:** Static analysis of the pinned
VIP image locates the I/O-control parser at fileD1498 (runtimeF8F12). It reads
the requested identifier, then calls fileCC95E with operation mask4. CC95E
searches the count-prefixed identifier table at runtime44758 (file1CCDE),
whose221 entries begin at4475A. **8180 is absent.** D1498 converts the failed
lookup to NRC31 before parsing the requested control type or executing a callback.
This explains the observed `2F818003 → 7F2F31` without invoking ELK or inferring
a missing SecurityAccess grant. CC95E also contains operation/session filtering,
but an absent identifier fails earlier; changing power/security state cannot add
an identifier to this immutable table.

Table reconstruction identifies39 entries with I/O-control operation bit4 in
the10-byte metadata records (runtime4495C, flags at44964). Operation descriptors
at45200 (six-byte stride) specify the control mask/action base. Action boundaries
at458D4 resolve callbacks in the12-byte table at45C18. All39 permit the four
standard control types (mask0F); none of their short-term-control callback entries
points to ELK callback57BC8. The entries are41D8–41DB,41DE,41E2,41E7–41ED,
42AD,43FC,440A–440C,4411–4416,4418,4424,4426,4428,447B,447D,447F,4481,
4483,4487,4781,4785,4839,5812 and5814. These ranges describe only the listed
members, not every intervening numeric identifier.

A representative normal I/O callback6A2DC (41D8) uses4E1A8, which sets
transaction kind5 and calls5C104. ELK callback57BC8 instead hardcodes internal
selector8180, uses4E08A (transaction kind4), then5C0C0→757D4→75794. The
application descriptor containing8180 at runtime2E7C0 is therefore not evidence
of registration in the CAN DCM identifier table. The earlier wording that
2F818003 was a verified entry point is withdrawn: it was a candidate, now
explained as rejected at lookup. A native AE label is likewise not a supported
CAN entry, as the live7FAE11 response already showed.

This trace establishes why the tested CAN route cannot call the compiled ELK
sender. It does not establish that every proprietary/internal entry point is
unreachable. No new CAN request, RAM write or firmware patch was required for
this dispatcher analysis. A RAM state/result change cannot create the missing
flash-configured registration or substitute for controlled sender invocation.

**F000 dispatch and RAM-assisted ELK request,2026-11-17:** The missing external
route is routine control, not direct I/O control. The routine-ID table at
runtime4451C includes F000 at index12. Its record at44614 selects action16,
access record17 and StartRoutine. The action callback at4795C is7ED6A
(file572F0), which calls file571E8. That dispatcher searches131 sixteen-byte
command descriptors beginning at runtime2E700. Its8180 record requires a
three-byte command buffer and application-security value at least1, then
indirectly calls7F642 (file57BC8). The resulting candidate is
`31 01 F0 00 81 80 03`.

Access record17 at runtime44958 contains session mask0004 and security
mask0050. Profile0D was observed immediately before the request to produce
DCM session4 and security mask0040, satisfying that gate. The independent
application-security word at FEBD0CF8 remained0; file5726A–57278 compares
this word with the descriptor requirement and rejects insufficient values
with NRC33. A successful SecurityAccess exchange does not establish that
this second application gate has been updated.

| Bounded test | Result |
|---|---|
| T1, extended/profile01, F000/8180 candidate | `7F3131` |
| Direct CAN, extended, profiles01/09/0B/0D separately | `7F3133` |
| Direct CAN/profile0D, FEBD0CF8 temporarily changed from0 to1 and read back | `7101F000818003` |
| Restore the saved four-byte application-security word immediately afterward | Original zero value verified |

The RAM-assisted request produced UART `Control Chan: Diag Elk Reboot Req`
and `Elk Reboot Response 0`, followed by `Controlled reset`,
`evResetRequestVIP` and a new VIP boot. The display turned off and ADB
disconnected. Privileged T1 reconnect timed out. VIP remained accessible
through CAN613/614; post-reset inspection again found application-security0,
idle transaction state, API12 local availability0 and peer availability1.
No calibration transfer or flash programming was used for this request.

This establishes a working CAN invocation of the compiled ELK request and an
accepted response followed by reset. **Final SoC ELK/Kernelflinger execution
was subsequently confirmed:** after an initial enumeration delay, USB exposed
`titan_gm_my22`, VID8087/PID09EF, and fastboot detected one device.
Read-only `getvar version-bootloader` returned
`kernelflinger-07.02-userdebug` successfully. Subsequent separate queries for
`product`, `is-userspace` and `version` each exceeded a10-second timeout;
they supplied no values. The positive bootloader identity establishes ELK,
but reliable repeated command access and current flash/unlock permissions
remain unverified. No flash, erase, unlock or storage-selection command was sent.
Partition readback is also unverified. The existing ELK string inventory names
partition-size/type variables and OEM get-hashes/get-provisioning-logs, but no
fetch/upload/readback command was identified in that inventory. Strings alone
do not establish command registration or absence of another read path. A live
`getvar max-fetch-size` query exceeded an8-second timeout while one fastboot
device remained enumerated; this is not an explicit unsupported-command reply.
No partition contents were read or saved. The separate Android fastbootd fetch
refusal documented above must not be applied to this ELK target.

### Native Probe-to-VIP transport and ELK prerequisites — 2026-11-17

Native Probe06 established bidirectional UART communication with VIP without
running AAOS/GHS. This is separate from the Mac's receive-only VIP diagnostic
UART observer. The handshake alone does not select ELK; the subsequent direct
MEI selection and restart test below established a Probe-to-ELK transition.

- The original GHS boot table binds `VipUART` to `SerialDev1` (record at
  section offset `0x4180`; name pointer at `0x41A8`). Native `/dev/ttyS1`
  maps to PCI `00:18.1`. A bounded live exchange confirmed this candidate:
  a 1 Mbps HDLC U-reset received a CRC-valid U-ack, control byte `0x63`,
  with negotiated sequence modulus 5.
- Stock Y175 `IPCServer` SHA-256 is
  `0bbadfcaa219f4f5516f61e8a45c4793671cdb8f92cce61f312e50d191f0e9ae`.
  Its transport uses CRC-16 polynomial `0x1021`, initial `0xFFFF`,
  big-endian FCS, `0x7E` delimiters and `0x7D` escaping (XOR `0x20`)
  for `0x7E`, `0x7D`, `0x11`, `0x13`. `ipc4.cfg` specifies protocol
  `0x10`, `/dev/ttyS1`, and 1,000,000 baud.
- The native transport test sent channel-0 XON entries for channels 0–20.
  VIP acknowledged that information frame, returned a protocol-`0x10`
  flow-control message with 21 entries, and sent channel-3 messages.
  Over the bounded run: 9 valid frames, 0 bad-CRC frames, 1 channel-0
  information frame and 6 channel-3 information frames. Payload contents
  were not retained. No application-level ELK success response was sent.
- While that receiver was running, CAN `31 01 F0 00 81 80 03` reached
  VIP's diagnostic ELK path, but ended with
  `TimeoutError: CAN radio response timeout`. The temporary application
  security word was restored and readback verified. No one-byte `E0`
  application request was observed by this receiver. Physical HDLC
  channel mapping and any preceding lifecycle handshake remain unresolved;
  API selector 12 must not yet be equated with physical channel 12.
- Native `mei`/`mei-me` modules, built for Probe06 on the native x86 build
  machine, bound PCI `00:0F.0` (`8086:5A9A`) and exposed `/dev/mei0`.
  Device state was `ENABLED`; the stock command client UUID
  `8e6a6715-9abc-4043-88ef-9e39c6f63e0f` was enumerated. This establishes
  transport availability, not acceptance of an ELK-selection command.

Probe08 was built with built-in MEI/ME drivers and
`/usr/sbin/vip-link` plus `/usr/sbin/vip-uart-probe`. `vip-link <seconds>`
performs a bounded UART handshake, flow-control exchange and HDLC receive
acknowledgments; it intentionally does not issue an ELK success response or
reboot. It is an on-demand test tool, not a complete replacement for GHS
lifecycle processing. Its CRC/reset-frame/corruption self-check passed on
the native build machine and inside the packaged image under QEMU. QEMU also
passed framebuffer/console, PTY, shell, read-only block fixture, USB NCM
configuration and SSH-server checks. The final compact image includes `elk-select` and `elk-reboot`, is 26,750,976
bytes, SHA-256 `773ae54ca352c7236ada4f543f475084b576053020c8128a185c48cd9898fc56`.
It passed the QEMU checks and booted on the radio, reporting
`4.19.283-elk-linux-probe-r08`, working USB shell/T1 SSH and enabled MEI.

The earlier 98,949,120-byte image (SHA-256
`454cdbfc0b93ce65ff1599b6d293997506fc5a534509516435d1636decef948f`)
was accepted for RAM download but `boot` returned
`FAILFailed to stop transport`. This occurred after both direct native
MEI/reboot entry and stock/CAN ELK entry; retrying boot and resetting USB
transport did not resolve it. The 25,653,248-byte Probe06 control image
booted successfully from the same ELK state. Removing the large optional
Mesa/Vulkan/VA userspace bundle from the Probe08 initramfs then allowed
Probe08 to boot. The exact size/layout constraint is unresolved: the
advertised 128 MiB download limit is not proof that every image below it
can boot. Graphics kernel/panel support remains included; the optional
userspace graphics runtime can be loaded into RAM separately.
No direct eMMC block writes or erases were issued by these tools; the internal
storage backend of the CSE boot-selection state is not established.

**Direct native Linux → ELK entry verified, 2026-11-17:** The stock OTA
activity handler at runtime `0x20193E` loads selector `2` before calling
`0x20D04F`. Assembly establishes a zero-filled 133-byte HECI command with
initial bytes `20 07 00 00 01 12 0E 08 00 D0 04 E1 02 00 00`.
Offsets 15–18 contain little-endian `0x458DAE79`: reflected CRC32C over the
10 bytes at offsets 5–14, polynomial `0x82F63B78`, initial `0xFFFFFFFF`,
**no final complement**. Remaining bytes are zero. The CRC routines are
`0x20C3BC`, `0x20C3E8`, `0x20C494`; `0x20CEA5` submits the frame and
checks transport success, a four-byte reply and zero status. The UUID in
OTA task data at runtime `0x60017C` matches the native MEI client above.
These runtime addresses correspond to text-image offsets, not whole-package
offsets; the extracted OTA text was disassembled at base `0x200000`.

The native helper connected through `/dev/mei0` (client protocol 1, maximum
message length 3072), sent the command once, and received **`20 87 00 00`**.
Only after validating that exact reply, `sync; reboot -f` was issued from
Probe06. USB `8087:09EF` appeared within the 25-second observation window;
its fastboot interface answered `getvar:version-bootloader` with
**`OKAYkernelflinger-07.02-userdebug`**. No AAOS boot or GHS-mediated CAN
request was needed for this transition. This proves a working native Linux
selection-and-restart route; it does not establish where every ELK boot
component resides or whether ELK survives an erased eMMC.

The packaged `elk-reboot` helper runs `elk-select --select`, then syncs and
restarts only if selection succeeds. `elk-select --selftest` validates the
CRC without accessing MEI. No automatic startup reboot is configured. The
separate CAN→VIP→native application callback remains unfinished: this test
uses a command invoked inside Probe, not a completed CAN-only trigger. The
radio initially remained in ELK. A subsequent native selection/reboot followed
by RAM download/boot of compact Probe08 succeeded, completing a native
Probe → ELK → Probe round trip. No image was flashed or erased.

### Cold-power recovery test and current development state — 2026-11-17

**Recovery requirement:** enter ELK from cold power without relying on working
GHS, AAOS or native Probe, including after loss of eMMC software. ELK can
RAM-boot Probe, which exposes native eMMC block devices and a recovery shell.
That recovery environment is demonstrated; an independent emergency-entry
trigger and its complete storage dependencies are **not established**.
Successful reads/dumps and a writable-capable Linux block interface do not
constitute a verified full eMMC restore. No destructive restore test was run.

**Cold-start test, no ELK target deliberately selected:** Probe08 was normally
rebooted without `elk-select`, returning to the stock boot path. CAN replay
was stopped; the tester reported zero transmitted data-frame echoes. The
bench supply was turned off for more than 10.5 seconds. Radio CAN reception
ceased and neither Probe nor ELK USB was present. After restoring supply
with replay still disabled, VIP reported SoC power levels 3/4 and
`evSoC_StartupComplete` at approximately 5.5 seconds. No ELK or Probe USB
appeared in the initial 15-second observation. Thus this cold power-up
started stock SoC software even without the captured vehicle-message replay.
The CAN adapter could still acknowledge received frames; this was a
zero-tester-data-frame condition, not an electrically disconnected bus.

The first diagnostics-only ELK attempt failed with
`TimeoutError: CAN radio response timeout`. Enabling replay also initially
failed while adapter errors accumulated. After resetting the adapter and
restoring the captured harness replay, diagnostic session/security access
worked. CAN `31 01 F0 00 81 80 03` returned `71 01 F0 00 81 80 03`;
the temporary application-security word was restored and verified. VIP
reported HMI-ready at 21.006 seconds, the ELK request at 21.638 seconds,
result 0 at 21.639 seconds, and controlled reset at 21.774 seconds of that
VIP boot. USB then exposed `8087:09EF`, and fastboot returned
`OKAYkernelflinger-07.02-userdebug`.

**Interpretation:** cold power followed by CAN-mediated ELK entry works with
the stock boot path available. It does not demonstrate entry before GHS/AAOS,
and the initial timeout cannot be attributed solely to a missing radio
prerequisite because adapter recovery changed the outcome. No eMMC erase or
simulated boot corruption was used.

**Remaining boot-recovery work:** locate ELK and its prerequisite firmware in
the actual storage map; trace bootloader/CSE cold-entry conditions and VIP
reset/boot-selection signals; establish a trigger independent of installed
SoC software. Intel's upstream
[`kf4abl.c`](https://github.com/projectceladon/hardware-intel-kernelflinger/blob/master/kf4abl.c)
contains a `__FORCE_FASTBOOT` path described as SPI-resident RAM boot without
using eMMC for the image. It also performs storage/slot initialization, so
that comment alone does not establish blank-media independence. This is an
upstream lead, not a verified GM cold-entry method. The stock SoC bootloader
update blob contains a CPD partition named `OBBP` with an entry named `ELK`,
plus `DNXP` and Kernelflinger markers. The adjacent names explain the string
`OBBPELK`; they do not establish a literal boot-target identifier. At file
`0x30101C`, the one-entry CPD directory specifies entry offset `0x40` and
length `0x114104`, placing the ELK payload at `0x30105C`. This locates a
packaged component, not by itself its executing storage copy or a usable DnX trigger.

**Live readback update — 2026-11-17:** a read-only kernel module subsequently
read the entire CPU firmware window `0xFF800000–0xFFFFFFFF`. The 8 MiB
readback and an independent on-radio reread have matching SHA-256
`9eaeaf92fa6e747d6887af0e4fc00d3faf5ab9e798d4801b2df8e0d7a8c12221`.
The ELK container at file offset `0x501040` and embedded ELF at `0x50126C`
match the staged package byte for byte; IBBL and IBB also match. This
establishes a live mapped ELK copy, without reading it through eMMC. It does
not establish a complete physical SPI backup or blank-eMMC boot behavior.
**Physical-flash boundary corrected 2026-11-18:** the device is an 8 MiB SPI
part whose final 1 MiB is under protected space. Thus an 8 MiB CPU-mapped
window must not be described as a complete physical-SPI acquisition unless
the protected-region contents and its mapping/access semantics are separately
demonstrated. The readback above proves the mapped address window and the
reported ELK/IBB bytes, not coverage of protected physical flash. The final
1 MiB of this mapped artifact is all `0xFF`; that is consistent with
protected-read masking but cannot distinguish masking from genuinely erased
physical flash.

**Protected-tail dependency boundary, 2026-11-18:** no direct dependency on
physical `0xFFF00000`--`0xFFFFFFFF` has been demonstrated in the recovered
executable path. A literal-operand scan of decoded IBB stage 1 (loaded at
`0xE0000`) found no operand in that physical interval. The visible policy
chain instead uses IBBL SRAM/low-RAM handoff data (`0xC0200`) and a relocated
FIT view at `0xFEFFFFC0`; neither address is the physical final SPI MiB.
Likewise, the traced CSE RBE/BUP policy path uses its hardware window or a
readable stored `$UEP` record, not a demonstrated final-tail read.

The unknown tail can still contain an **earlier root of execution**. Apollo
Lake reference build logic places reset/FIT/flash-map anchors at the top of
the 4 GiB firmware address space (for example `0xFFFFFFF0`, `0xFFFFFFC0`,
and `0xFFFFFFF8`) and FIT records can describe the ACM, key manifest, boot
policy manifest, microcode, and initial boot block. That reference layout is
not proof of this unit's masked bytes. Because this unit's corresponding
mapped range is all `0xFF`, neither the reset vector nor physical FIT contents
can be parsed or attributed without a physical read or an authoritative flash
layout. Therefore the supported conclusion is: downstream IBB/IBBL/GHS/ELK
selection does not currently call the tail directly; the pre-IBBL cold-reset
root remains unknown.
See [the readback map](../../hardware/teardown.md#live-firmware-window-readback--2026-11-17).
The module was unloaded; no flash write or erase was performed.
No hardware strap or blank-eMMC recovery path has been validated on this
unit. Static tracing subsequently identified an automatic SPI-ELK fallback
after the two GHS image candidates; see the automatic-selection trace below.
That fallback has not been exercised with deliberately failed GHS images.

**Equipment/process state at the earlier Probe08 verification:**
The subsequent upstream-kernel Probe test below supersedes the running-image
and SSH state in this historical snapshot.

| Component | State |
|---|---|
| Radio SoC | Compact Probe08 running; USB root shell responsive; no AAOS/GHS userspace |
| Bench supply | On |
| CAN harness controller | Full replay stopped; original captured `0x529` only, every 320.270 ms, after confirmed ELK entry and Probe08 RAM boot |
| VIP diagnostic UART observer | Running, receive-only; separate from the native SoC↔VIP bidirectional UART |
| Native VIP link observer | Bounded test ended; not a continuously running service |
| Build workstation | Native x86 Mac Pro remains the build machine; no active image build or QEMU test at verification |
| Latest boot image | Compact Probe08, 26,750,976 bytes; hash and hardware verification above |
| Source/build artifacts | Retained in `<BUILD_WORKSPACE>`: `display-init.c`, `display-panel.c`, `display-package.py`, `display-build-inside.sh`, `display-qemu-check.py`, `probe-tools/vip-link.c`, `probe-tools/vip-uart-probe.c`, `probe-tools/elk-select.c` |
| Packaged commands | `vip-link`, `vip-uart-probe`, `elk-select`, `elk-reboot`; VIP observer is on-demand, not a full lifecycle daemon |
| Graphics userspace | Kept outside compact image; available for loading after boot; i915/panel support remains included |
| Independent Claude research | Ended without findings: `API Error: Opus 4.8's safeguards flagged this message.` No agent remains working on that task |

`<BUILD_WORKSPACE>` denotes the existing native build directory, not a host
address. This is a point-in-time technical status; verify live endpoints
before issuing commands. No credentials, infrastructure addresses or client
session identifiers are required in this record.

### Cold-entry selector trace — 2026-11-17

The known CAN routine is not a demonstrated hardware boot-select operation.
At `0x75794`, VIP checks API channel 12 via `0x76272`, then submits one-byte
`E0` through `0x570FE`. The availability check ANDs local and peer state arrays
(`0xFEBD3000` and `0xFEBD3018`); for channel 12 these are `0xFEBD300C` and
`0xFEBD3024`. The sender resolves a transport handle from the channel table.
Thus making a diagnostic gate pass does not replace the missing SoC recipient
or perform the CSE selector operation. This establishes the dependency of the
known path, not the absence of every possible alternative CAN path.

**Boot Reason Record correction:** `SoCReqType` at `0xFEBF0BC1` is not a
verified cold-boot target latch. `0x5CEBA` derives the reset reason from reset
flags and clears this byte. SoC shutdown-request handling around `0x74476`
writes values 3/4/5 and the over-temperature branch writes 6; the accompanying
strings identify shutdown, controlled reset and BOLO handling. `0x7363C`
also records a request type for a special-use BOLO/reset request. `0x741A4`
packages the record into the last-boot-reason IPC report. No traced consumer
selects Intel ELK from this field. The old inference that nonzero values imply
recovery/fastboot selection is withdrawn; a boot-selection consumer would need
separate evidence before any RAM modification is useful for this objective.

**Packaged ELK IOC-reset lead:** the extracted Y175 ELK ELF is 1,122,304
bytes, SHA-256 `3acbf174207a2c621d24ba5a1278c3b214b11c88e580228599057b4ad3a8951c`,
x86 32-bit little-endian, load/entry base `0x12800000`. Its `ioc_uart` driver
record is at `0x1290F1CC`. Initializer `0x128D0F20` installs reset callback
`0x128D1320`; the callback distinguishes `bootloader`/`fastboot`/`recovery`
from ordinary resets and emits different SLCAN-formatted strings through UART,
then chains the previous reset callback. Helper `0x128D1620` locates PCI
`8086:5ABE` and programs the UART. Separately, `0x128D1210` emits the logged
IOC-bootloader request before IOC firmware-transfer handling. These are
SoC-originated IOC commands, not evidence of an external CAN listener that
boots the SoC into ELK. The companion MCU's interpretation, applicability to
this VIP, and any cold-power persistence/boot-select effect remain unverified.
No experimental IOC reset/reflash message was transmitted. This is a specific
lead for receiver-side tracing, not a validated recovery recipe.

The remaining relevant question is an early firmware or physical boot-selection
path reachable from VIP CAN before a SoC IPC service exists. Neither the BRR
record nor the demonstrated IPC request answers that question. No cold-power
CAN-only recovery path independent of installed SoC software is verified.

### Native Probe without CAN replay — 2026-11-17

Compact Probe08 remained USB-present for the first five minutes of passive
observation after application CAN replay was disabled. A USB shell read showed
monotonically advancing uptime; no native VIP lifecycle/HDLC helper was running,
and native UART transmit/receive counters remained zero. The CAN controller's
transmit-echo counter stayed unchanged while radio-originated reception continued.
The adapter remained ACK-enabled: this tests no tester application replay, not
an electrically absent CAN bus. The external diagnostic UART observer reported
no new shutdown/power-mode events during that interval. No reset, diagnostic CAN
request, or VIP IPC stimulus was introduced during the observation.

This is a bounded observation in the state inherited from ELK entry. It does
not establish indefinite operation or isolate AAOS as the cause of prior
shutdowns. Historical Y175 startup logs report VIP power-mode-failure timeout
60 s, local-infotainment timeouts 600 s, sleep-fault timeout 900 s and master
Off-mode timeout 35 min; these are historical configuration evidence, not a
fresh read of this boot's active calibration. Their activation conditions
remain relevant; elapsed time alone does not prove each timer was armed.

Stock-system tests already show VIP participating in shutdown policy: after
replay stopped, PowerModeOff/LocalInfotainment occurred; a subsequent driver-door
CAN event led to Requesting Shutdown, animation failsafe, Sleep, and finally
SoC power level 0. See the [door/shutdown evidence](../../platform/can_bench_experiments.md#door-wake-and-explicit-shutdown-paths--2026-11-16).
Those observations do not assign every step solely to VIP or AAOS. Native Probe
surviving without the stock lifecycle handshake suggests a different active
policy/state after ELK entry; that mechanism is not yet traced.

### VIP parameter/control scope — 2026-11-17

Probe can transmit and receive binary VIP IPC. Verified outgoing operations
are currently HDLC reset/acknowledgment and channel flow control. This does
not grant a general parameter-write API, a VIP shell, or unrestricted CAN
transmission. The stock protocol has lifecycle, vehicle-signal, diagnostics
and calibration-related paths, but each message needs its own format,
permissions, response and persistence analysis before implementation.

Native Probe starts after VIP's earliest initialization. The external
receive-only diagnostic UART can observe that early interval; a complete
bidirectional wire capture from power-on would require an independent tap
or a sufficiently early receiver. Probe can then observe/reproduce later
startup negotiation and verified SoC replies. Changes must distinguish RAM
state from persistent calibration/EEPROM effects. The repeated channel-3
`E1` packets remain undecoded; no startup-policy or calibration setter was
implemented in this pass. The direct ELK selector uses SoC MEI/CSE, not a
VIP parameter write.

**Owner-requested unlock attempt,2026-11-17:** With one fastboot device still
enumerated, `getvar unlocked` and `flashing get_unlock_ability` each exceeded
a10-second timeout. A subsequent host invocation of `fastboot flashing unlock`
exceeded a20-second timeout without a protocol response. Delivery of the unlock
command to its device-side handler, eligibility, resulting lock state and any
data-erasure effect were not established. Do not classify this as either a
successful unlock or an explicit bootloader refusal. This attempt supersedes
the preceding no-unlock-command-sent checkpoint.

**Intel host-tool comparison,2026-11-17:** Intel Platform Flash Tool Lite5.8.9.0
for macOS was obtained from the official
[Project Celadon tools repository](https://github.com/projectceladon/tools)
and extracted without installation. Its x86_64 Fastboot reports
`3db08f2c6889-android`. Its help includes custom USB VID selection (`-i`),
`flashing get_unlock_bootloader_nonce`, `flashing unlock_bootloader <request>`,
`flashing lock_bootloader` and `reboot emergency`, which are absent from the
installed newer host binary's help. These establish host-interface differences,
not support for those operations by this GM ELK build or Intel-exclusive origins
for those commands.

After confirming no other Fastboot process was running, the Intel binary with
`-i 0x8087` enumerated one device. Separate read-only queries for
`version-bootloader`, `unlocked`, `secure` and `flashing get_unlock_ability`
each exceeded an8-second timeout. The alternate host binary therefore did not
resolve the observed command-response problem or establish additional device
capabilities. No erase, flash or unlock command was sent by the Intel binary.

**Online source investigation,2026-11-17:** No exact published GM
titan_gm_my22 failure match was established. These upstream findings are
diagnostic leads, not a byte-match to the installed Harman firmware:

- Intel's [Fastboot state machine](https://github.com/intel/kernelflinger/blob/master/libfastboot/fastboot.c)
  schedules the next command read from the transmit-completion callback.
  Unknown variables/commands and disallowed security states normally produce
  explicit FAIL responses. A response-completion or receive-rearming fault is
  therefore a candidate for the one-response-then-silence pattern, not a proven
  explanation. The default Android command table restricts erase to UNLOCKED;
  GM's compiled table still requires verification.
- AOSP's [macOS USB implementation at4997e024e](https://android.googlesource.com/platform/system/core/+/4997e024e/fastboot/usb_osx.cpp)
  clears both bulk endpoint stalls on opening, citing observed bad endpoint
  state on Mac. That revision leaves USB reset unsupported because of device
  ownership conflicts, and can use a blocking read when no timeout is set.
  Installed binaries were not matched to this revision. Host reopening and
  endpoint state are candidates requiring transport traces, not established causes.
- Google's [Platform Tools release notes](https://developer.android.com/tools/releases/platform-tools)
  document historical Mac Fastboot hang fixes and an increase to30-second
  command timeouts. The bounded8–20-second host terminations used here cannot
  prove that a slow erase or unlock failed. Identity reads timing out as well
  suggest testing general transport health first.
- Intel's [transport implementation](https://github.com/intel/kernelflinger/blob/master/libfastboot/fastboot_transport.c)
  includes Fastboot TCP port5554 with FB01 handshake. This is an alternative
  transport lead only; GM build enablement, address and reachability are unknown.

Discriminating next tests: after a fresh ELK entry, repeat a read-only identity
query on one retained USB connection, compare with separate process opens, and
compare a different host USB stack. Trace whether the command write completes
and whether any response bytes arrive. A physical USB reconnect may distinguish
endpoint/reopen state from a hung device loop; it does not itself prove command
support. Do not use another erase as a transport test. No new device command
or reset was issued during this online investigation.

**USB transport isolation and live state,2026-11-17:** A direct libusb client
claimed interface0 (FF/42/03), using bulk OUT02 and IN81, packet size512,
without setting configuration or clearing endpoint stalls. In the stalled
state its25-byte version command write completed immediately, but the read
returned `[Errno 60] Operation timed out` after5 seconds.

A mute-hold restart eventually returned the normal CAN diagnostic path. An
initial USB-reset attempt encountered no ELK device and stopped at its presence
assertion before resetting anything. After repeating the verified CAN ELK entry
(temporary application-security word restored), the waiting raw client obtained
three version replies on one retained connection in7–8ms each. Two additional
separate raw-client process opens also succeeded. A standard Mac Fastboot identity
query then timed out after8 seconds; a subsequent raw read timed out as well.
A libusb USB-device reset completed, after which three retained-connection
queries again succeeded in about7ms each. No radio power cycle or flash operation
was required for this recovery.

This bounds the fault to behavior associated with the standard client's USB
access in this test sequence, rather than an inherent one-command ELK limit or
interface reopening alone. Endpoint-clear/data-toggle handling remains a
hypothesis; no USB trace yet identifies the precise failing operation.

The working raw client then returned these live values:

| Read-only query | Result |
|---|---|
| unlocked | yes |
| secure | no |
| is-userspace | no |
| product | titan_gm_my22 |
| partition-type:userdata | ext4 |
| partition-size:userdata | 0x00000009C1800000 |
| flashing get_unlock_ability | INFO The device can be unlocked.; OKAY |

Some replies contained NUL-terminated values followed by stale text from the
prior response; interpret the value before the first NUL, not the full padded
buffer. These observations establish ELK's current reported unlocked state,
not its origin: no successful pre-attempt lock-state read exists, so the earlier
timed-out unlock cannot be credited with changing it. Userdata erase completion,
state persistence and effects on normal Android/GHS verified boot remain
unverified. No erase, flash or unlock was sent in this transport-isolation test.

### Early-firmware eMMC authentication gate — 2026-11-17

Analysis of the 8 MiB mapped-address readback identified an authentication
barrier **before ELK's downloaded-image policy**. This is not a certification
that every byte or security-engine module has been reverse engineered, nor
evidence that the physical SPI's protected final 1 MiB was acquired.
The live readback's IBB container is identical to its staged counterpart.
Its first compressed stage starts at container offset `0xEC`: a four-byte
output-size field (`0x1D440`), raw LZ4 data at `0xF0` through `0x15930`,
and a four-byte trailer whose semantics remain unverified. Both a bounded
LZ4 decoder and liblz4 produced 119,872 bytes, SHA-256
`06e4c0a30bc8c4ccd838149360f816dd3b02490da6600f693bdb7df23ea93345`.
Analysis at base `0xE0000` resolves absolute string pointers and code calls.
Addresses below refer to that decoded stage, not dump offsets or VIP RAM.

| Function | Observed behavior |
|---|---|
| `0xEBDEF` | `mmcbootX` path; retrieves an eMMC boot image, then calls `0xED792` |
| `0xEBE6B` / `0xEBF22` | File/raw-offset image-loading paths, including `mmc`, then call `0xED792` |
| `0xED792` | If policy byte `0xC0200` bit 0 is set, calls `0xF3F04(image, digest, 0x27)`; failure branches to `Error: authentication failed` |
| `0xF3F04` | Requires image-header byte 5 bit 1 (mask `0x02`); absent flag returns false. Resolves a permitted key hash, compares a 32-byte key digest, and invokes a 256-byte-signature verifier |
| `0xF3E06` | Selects a 32-byte key hash using a purpose bitmap and requested purpose (`0x27` for the image path) |
| `0xF6D40` | Signature-verifier wrapper with 2,048-bit key-size and 32-byte digest parameters |
| `0xEB30F` | IFWI-update path has version rollback rejection and policy-gated authentication with purpose `0x25`; this is separate from ordinary eMMC image boot |
| `0xEF196` | Policy-gated PDR authentication with purpose `0x28`; failure reaches a halt path |

The same policy bit is emitted as `ABL.secureboot` by `0xECC04`.
It is **not** the ELK OEMLock-derived `getvar secure` predicate. A subsequent
read-only check of the running Probe command line returned `ABL.status=0x9`
and `ABL.secureboot=1`. The traced IBB code emits these from its policy word:
bit 0 selects authentication; the low two bits are included in ABL.status.
This supports enabled image authentication for the observed boot, but is
inherited software reporting, not a direct fuse measurement. References in
the decoded stage read the policy rather than directly initializing it.
No runtime policy bytes or flash contents were modified.

**ELK storage handoff resolved further:** `0xEC001` initializes SPI access,
looks up the named component (default `ELK`, fallback `OBBX`), copies it with
SPI reader `0xE53BB`, logs `copy %s from SPI`, and calls `0xED792`.
This is actual SPI component-loading code, corroborating the mapped OBBP/ELK
readback, rather than merely identifying an eMMC update-staging copy.

**Consequence:** an unsigned eMMC image can be rejected before ELK, even while
ELK reports `secure=no` and permits RAM-booted Probe. If policy bit 0 is clear,
this particular authentication call is skipped; that alone does not remove
image-format, boot-selection, later-stage, or hardware-rooted checks.
The expanded audit below unpacks the CSE modules and all three IBB payloads.
Complete CSE control-flow analysis, hardware fuses, and the ROM-side policy
origin remain outside a completed end-to-end audit. Do not infer that
arbitrary unsigned eMMC replacements will boot, and do not erase the original
boot path based on ELK RAM-boot success.

#### IBB-stage1 reconstruction and handoff revalidation — 2026-11-18

The mapped IFWI's stage-1 LZ4 record has now been round-tripped at its actual
file location. The little-endian decoded-size field at `0x29052C` is
`0x1D440`; the raw LZ4 stream is `0x15841` bytes at `0x290530` through
`0x2A5D70` inclusive. Replacing precisely that range in a copy of the mapped
8 MiB image with the extracted original stream produced a byte-for-byte equal
IFWI (both SHA-256
`9eaeaf92fa6e747d6887af0e4fc00d3faf5ab9e798d4801b2df8e0d7a8c12221`).
The reconstructed image independently decompresses to the same 119,872-byte
stage-1 payload and SHA-256
`06e4c0a30bc8c4ccd838149360f816dd3b02490da6600f693bdb7df23ea93345`.
This is functional identity by construction; it is not a newly compressed
replacement stream.

Forward and backward tracing agree when that decoded payload is mapped at
`0xE0000`. The image-loader function begins at `0xED792`. Its candidate-entry
local is `[ebp-0x234]`: candidate/helper paths populate it (including the
default metadata-derived path), and `0xEE3ED` validates/prepares the chosen
image before writing its entry pointer through the address supplied for that
local. `0xEE03B` rejects a zero value. On the successful path, `0xEE0A1`
logs the entry/setup pair, `0xEE0C7`--`0xEE0D9` restore preserved registers,
`0xEE0DF` executes `cli`, and `0xEE0E0` performs `jmp dword [ebp-0x234]`.
Thus the final transfer target is readable decoded IBB logic and selected
image metadata, not an unresolved value in the protected final MiB. This is
static trace evidence; it does not itself prove a particular candidate was
successfully booted on hardware.

#### Live normal-boot policy corroboration and VIP boundary — 2026-11-17

Read-only T1 SSH checks on `7.3.5-probe-stable04` reproduced the retained
IBB policy dword `0xFEF92001` at `0xC0200`; the authentication bit is set.
Neighboring `0xC0204` and `0xC020C` are both `0x000055AA`. The boot arguments
still contain `ABL.secureboot=1` and `ABL.status=0x9`. These are surviving
handoff data, not observation of a new cold boot or proof that every byte
of low RAM is immutable after handoff.

HECI PCI configuration again reports FWSTS1 `0x80000245`, FWSTS2
`0x80100000`, FWSTS3 `0x30370608`, FWSTS4 `0x00080000`, FWSTS5 zero and
FWSTS6 `0x40000000`. The hardware-source MCA read of
`/fpf/intel/SocCfgLock` succeeded with result zero, one data byte, value 1.
This corroborates committed fuse configuration and completed successful IBB
verification. It does not decode every OEM security fuse or establish
host flash-write permissions. The exact eight-byte `pread` of MSR `0x13A`
returned `pread MSR 0x13a on cpu0: n=-1 errno=I/O error`; no usable value
was obtained. An earlier exploratory `dd` used a different offset and is
not counted as the `0x13A` test.

The saved GPT and live first 512 bytes agree for `ghs_isys_a`, `ghs_isys_b`,
`ghs_abl_update`, `bootloader_a` and `bootloader_b`. Both GHS headers start
with `ipk.` and have byte 5 = `0x03`, including the signed-image flag.
This is a header comparison, not a new full-partition integrity check.
The initial attempt used absent `mmcblk0p1` and generated empty-stream
hashes; those were discarded. Successful reads used this boot's discovered
`mmcblk1p*` devices with pipeline failure checking.

**Reject versus log-and-execute is resolved for this gate.** Reinspection
of decoded IBB-stage1 (SHA-256
`06e4c0a30bc8c4ccd838149360f816dd3b02490da6600f693bdb7df23ea93345`,
x86 little-endian 32-bit, loaded code region at `0xE0000`) confirms:

* `0xED837` reads the policy byte; `0xED83D` tests bit 0.
* With bit 0 set, `0xED84B` calls `0xF3F04` with purpose `0x27`.
* A false result reaches `0xED854`/`0xED859`, then the error-reporting
  path at `0xEE072` and function exit via `0xEE0E9`. It does not reach
  the image-entry transfer at `0xEE0E0`.
* `0xEC0EA` permits the next configured candidate after a loader returns.
  Thus rejection can lead to another GHS slot or SPI ELK; continued boot
  activity is not execution of the rejected image.

Consequently, a structurally valid but unsigned/incorrectly signed direct
GHS replacement is rejected under the observed policy. A raw Android
`boot.img` also lacks the required outer container. This conclusion is
static control-flow evidence corroborated by live policy; no intentionally
invalid image was written or booted from storage in this check.

**What would have to change:** an image could satisfy the existing purpose-
`0x27` trust chain with an authorized signature; alternatively, an accepted
CSE policy/token/context path would have to clear verification before FIT
publication, or the enforcing loader would need to be changed. The last
option is not self-authorizing: IBB is itself authenticated upstream.
Changing `0xC0200` after Linux starts would only alter old handoff RAM,
not the policy used to authenticate the next normal boot. No persistent,
authorized policy-setting interface or accepted custom signing key has
been demonstrated. Clearing this gate alone would not settle later GHS,
Android AVB, image-format or boot-selection requirements.

**VIP/RH850 influence:** VIP manages SoC power/reset and forwards the known
ELK request through channel 12. The traced `0x75794` sender requires peer
channel availability and sends `E0`; SoC-side lifecycle/OTA code performs
HECI/CSE selection before reset. This is a boot-target request, not a
verified CSE authentication-policy write. The temporary VIP diagnostic RAM
gate is separate from the Intel IBB policy byte. No traced VIP CAN/UART
operation writes CSE `SbPolicies`, installs an accepted unlock token, or
changes committed Intel fuses. VIP-driven power/reset events could affect
CSE transition context, so its indirect influence remains relevant; however,
no tested VIP sequence produces the qualifying `pm_trans` bit 3/context and
counter combination. Do not infer either that VIP can unlock the SoC or
that it has no possible influence beyond power management.

The radio remained in Probe with working key-authenticated T1 SSH. No
flash, eMMC, boot-selector, policy-memory or reset changes were made.

#### HECI selector acceptance test — 2026-11-17

From stable04 Probe, sent the established 133-byte MKHI user-command frame
with its selector byte changed from 2 to 3, then 4, recalculating the raw
CRC32C each time. CSE returned exactly `20 87 00 00` for both. A cleanup
command restored selector 2 and received the same acknowledgment. No reset
was performed; neither alternate selection was boot-tested. The next-boot
selection was deliberately left at the previously demonstrated ELK value 2.

| Selector | CRC32C | CSE response | Scope |
|---|---|---|---|
| 3 | `E0CC3C07` | `20 87 00 00` | Stored-command acceptance only |
| 4 | `943C586E` | `20 87 00 00` | Stored-command acceptance only |
| 2, cleanup | `458DAE79` | `20 87 00 00` | Known ELK selection restored |

The bounded test stopped before 5. Static IBB function `0xEC325` tests
`0xC0218 & 0x1F`: when configuration tag `0x5A` is present, value 5 enters
an infinite loop. Value 4 selects an alternate tag `0x60` if present,
otherwise clears the low five selector bits and uses ordinary tag `0x4B`.
This is a boot-index consumer, not a confirmed list of named HECI modes.
The complete connection from the stored command payload to this byte still
needs explicit tracing before assigning every selector a boot-mode name.
No rejection boundary was reached by the live test. A zero-status CSE reply
must not be treated as proof that the selected boot path exists or executes.

The temporary client restricted inputs to 2/3/4, passed its CRC self-test,
checked the MEI message-size limit and exact reply bytes, and contained no
reset operation. Local review flagged a possible device write overflow;
manual inspection found the existing `max_msg_length >= sizeof(frame)`
check and bounded 133-byte write, so that finding was not substantiated.

#### Selector 0/1 reboot trials — 2026-11-17

Selector 0 was sent from stable04 Probe with raw CRC32C `0AE2FC74`;
CSE replied `20 87 00 00`. After `sync; /bin/reboot -f`, the owner
confirmed the AAOS home screen. ADB did not enumerate, so the active Android
slot and exact GHS candidate were not independently read. This establishes
AAOS startup after selector 0, not a measured slot-A handoff.

The known CAN ELK procedure then returned `71 01 F0 00 81 80 03`; the
saved VIP application-security word was restored. USB exposed ELK's
FF/42/03 interface, and ELK accepted the hash-verified stable04 image for
RAM boot. The USB shell confirmed `7.3.5-probe-stable04`. CAN replay resumed
and reported increasing radio reception with its error count stable after
adapter recovery.

From that Probe, selector 1 was sent with CRC32C `AFA36E0A`. CSE returned
`20 87 00 00`. The client succeeded, followed by `sync; /bin/reboot -f`;
the SSH connection subsequently ended. The owner subsequently confirmed
AAOS booted after selector 1 as well. The actual selected partition remains
unverified: reaching AAOS does not distinguish first-candidate success from
fallback. Selectors 3, 4 and 5 were subsequently reboot-tested as recorded below.

`FEBD0CF8=1` is the separate VIP diagnostic application-security gate,
not the Intel selector value. Returning through that CAN procedure selects
ELK; selector 1 in this trial was set directly through MEI inside Probe.

#### Selector 3 reboot issued — 2026-11-17

After the confirmed selector-1 AAOS boot, the established CAN routine
returned `71 01 F0 00 81 80 03`; the VIP application gate was restored.
ELK enumerated as FF/42/03 and returned
`OKAYkernelflinger-07.02-userdebug`. Stable04 was RAM-booted again;
the USB console confirmed its kernel version and T1 SSH was re-established.
Selector 3 (CRC32C `E0CC3C07`) returned `20 87 00 00`, after which the
command chain issued `sync; /bin/reboot -f`. The owner reported a black
display. Subsequent checks found no Intel USB enumeration and no ICMP reply
from the former Probe endpoint (3 packets sent, 100% loss), despite an active
T1 link. A 20-second VIP UART observation received 1,080 bytes, repeatedly
reporting `[J6_CDD] Unable to Transmit RTE Date/Time` once per second;
VIP timestamps advanced monotonically from approximately 158 to 177 seconds.
CAN radio reception increased by 1,230 frames per 30 seconds (about 41/s)
with error count stable at 146 across the observed samples. Thus VIP/CAN
remained alive, while its time-message IPC send path was unavailable. No VIP
restart loop was observed in that bounded UART window. This does not identify
the exact SoC execution point or distinguish halted code from a loader that
has not initialized IPC/USB/networking. In particular, link LEDs and CAN
activity do not establish AAOS startup or execution of the proposed
bootloader-offset candidate. CAN replay remained enabled.

#### CAN reset request following selector 3 — 2026-11-17

At the owner's request, sent the previously verified CAN mute-hold pattern
(`526`, eight bytes, byte 5 bit 7) while retaining the harness replay. VIP
logged `Mute buttons pressed`, then `SWC Reset Button Press detected` after
10.01 seconds. The input was released with zero payloads. VIP then logged
`evResetRequestCSM` and `SetShutdownAndResetCSM`. No shutdown-completion,
new-boot or HMI-ready marker was observed in the following 25-second window.
A subsequent five-second UART observation captured a new VIP uptime
sequence (approximately 1–5 seconds) and `evSoC_StartupComplete` at 5.591
seconds, with `isResetPending = false` and `isShutdownPending = false`.
Thus the reset subsequently completed and VIP reported SoC startup; the
initial 25-second observation had been too short. The owner then confirmed
AAOS booted. This was a coordinated reset, not a VIP-only operation.
Normal CAN replay was resumed. No calibration/flash writes or new
boot-selector command were issued between the selector-3 black-screen state
and AAOS recovery. This is consistent with a consumed/cleared override or
reset-dependent selection/fallback, but does not establish which mechanism
occurred or which partition actually executed.

#### Selector 4 reboot trial — 2026-11-17

Following AAOS recovery, the established CAN ELK entry succeeded and restored
the temporary VIP application gate. ELK's FF/42/03 interface was verified,
and the unchanged stable04 image was RAM-booted. USB shell reported
`7.3.5-probe-stable04`; T1 SSH was established. Selector 4 with raw CRC32C
`943C586E` returned `20 87 00 00`, then the host executed
`sync; /bin/reboot -f`. A UART observer started before this restart captured
`evSoC_StartupComplete` at VIP time 76.433 seconds and `evHMIReady` at
91.970 seconds. These are VIP uptime values, not reboot durations.

This establishes post-selector-4 application-ready signaling, but neither
identifies the exact boot partition nor establishes that alternate tag
`0x60` was present or used. Static fallback to ordinary boot remains a
possible explanation. The owner subsequently confirmed AAOS loaded.
CAN replay remained active. No storage-image write was performed; selector 5
was subsequently tested in the separate trial below.

#### Selector 5 reboot trial — 2026-11-17

At the owner's explicit request after the halt-case discussion, returned
from AAOS through the established CAN ELK procedure, verified the FF/42/03
USB interface, and RAM-booted unchanged stable04. USB shell confirmed the
kernel version and T1 SSH worked. The temporary client's allowlist was
extended to selector 5; its build and on-device CRC self-test passed.
The local review tool failed with
`qrev: failed: Unterminated string starting at: line 1 column 12708 (char 12707)`;
no successful automated review is claimed for this revision.

Selector 5, raw CRC32C `317DCA10`, received `20 87 00 00`, followed by
`sync; /bin/reboot -f` and SSH disconnection. A 45-second UART observer
started before the restart received 2,925 bytes: `evStartupTimeout`,
`FAILURE DETECTED: SoC Startup Timeout`, and repeated
`Unable to Transmit RTE Date/Time`. No `evSoC_StartupComplete` or
`evHMIReady` marker was observed. No Intel USB interface appeared in a
30-second check. CAN reception continued with stable error count after the
adapter recovery associated with entering Probe.

The startup-timeout timestamp was VIP uptime around 60 seconds, and the
observer had started around 55 seconds while Probe was still running.
The timeout may include that preceding Probe interval, which lacks full
stock lifecycle processing; it is not independently proof of selector-5
execution at the static infinite loop. The observed absence of application
startup is consistent with that halt case, but the exact execution point
and display state were initially unverified. A subsequent owner-requested
coordinated reset recovered the boot sequence, as recorded below. CAN replay
remains active.

#### Reset recovery after selector 5 — 2026-11-17

The owner requested a VIP reset. The verified CAN mute-hold sequence
triggered `SWC Reset Button Press detected` after 10.01 seconds, followed
by `evResetRequestCSM` and `SetShutdownAndResetCSM` at VIP uptime 146.833
seconds. The input was released immediately. After roughly 43 seconds,
VIP logged pending-CSM-reset state and its uptime restarted; the new boot
reported `BRR_RESET_REASON_VIP_SOFTWARE updated to 39`, `AnimationInit`,
`evSoC_StartupComplete` at 5.702 seconds and `HmiInit` at 8.673 seconds.
Reset/shutdown pending flags were false. The owner reported AAOS booting.

This confirms coordinated-reset recovery from the post-selector-5 state
without a new HECI selector command or storage-image write. It does not
identify the selector-consumption/clearing mechanism or prove the CPU had
executed the static halt loop. CAN harness replay remains active.

#### Automatic selection and ELK startup — 2026-11-17

**Static finding:** the shipped SMIP configuration includes SPI ELK as an
ordinary automatic boot candidate. ELK selection is therefore not exclusively
an AAOS-requested action. This corrects the previous unresolved-selection
assessment. The live test below confirms fallback with both GHS images absent;
recovery with the entire eMMC erased remains untested.

**Live confirmation, 2026-11-17:** both 64 MiB GHS partitions were checked
against the saved eMMC backup, then zero-filled without changing the GPT or
other partitions. Full-partition readback SHA-256 for each erased partition:
`3b6a07d0d404fab4e23b6d34bc6696a6a312dd92821332385e5af7c01c421351`.
Intel selector 0 was acknowledged with `20870000`, followed by a Probe reboot.
USB fastboot enumerated and returned `OKAYkernelflinger-07.02-userdebug`.
This confirms automatic ELK recovery with both GHS images missing, rather than
an explicit selector-2 ELK request. The first trial also successfully RAM-booted
stable04 Probe and restored both partitions to the backup SHA-256
`13e168dd9ff073f2c40ef1fb42ed44627474554dbf9d4a2f23879a8c77f525a0`.
A second requested trial repeated the verified zero-fill and selector-0 reboot,
then left ELK running without downloading or booting Probe. Both GHS images
remain erased after that second trial; CAN keepalive remains active.
This was a warm reboot with the GPT, other eMMC partitions, boot areas and SPI
preserved. It does not demonstrate blank-eMMC or cold-power recovery.
Raw USB here carries the normal fastboot protocol; it exposes exact replies,
not a separate privileged debug interface.

**Subsequent raw-image placement test, 2026-11-17:** after returning to
RAM-booted stable04, the verified 30,306,304-byte Probe Android `boot.img`
was written directly at offset zero of `ghs_isys_a`, at the owner's request.
The original GHS backup was hash-verified before writing. Full 64 MiB readback
matched the Probe image followed by zeros, SHA-256
`30ad12e2cf1ad6dd7aa71c56b8f6f1bc1a3ccb6a509da9455cab576ab0487b84`.
`ghs_isys_b` remained verified zero-filled and the GPT was unchanged.
A subsequent test set HECI selector 0 (CSE acknowledgment `20870000`),
then issued `sync; /bin/reboot -f` from Probe. The Linux USB gadget disappeared;
approximately seven seconds later USB fastboot answered
`OKAYkernelflinger-07.02-userdebug`. No image was downloaded after that reboot.
The raw Probe placement did not produce an observed Linux boot; the radio
returned to ELK. This is consistent with rejection of the unsupported Android
boot-image container in an IPK slot. No early IBB error was captured, so this
test does not distinguish header/format rejection from authentication failure
or another loader failure, and does not test a properly wrapped custom image.
This supersedes the preceding trial's state of both GHS partitions being empty:
slot A now contains a raw Android boot image, without an IPK wrapper.

**Wrapped entry-probe experiment, 2026-11-17:**
`tools/bench/build_ipk_entry_probe.py` builds an unsigned IPK from the
hash-pinned archived ELK container. It preserves the four IPK components,
recomputes the raw CRC32C header/body checksums, strips the signature trailer,
and redirects the ELF32 entry to a new stub within verified zero file padding.
The extended first load segment contains a zero-initialized marker location
at `0x12901C50`. The stub writes `IPK_ENTRY_PROBE_V1_EXECUTED_OK!!` there and
jumps to the original `0x12800000` ELK entry without changing registers, flags
or stack. This is an execution test and does not bypass authentication.

The output ELF segments were loaded in Unicorn; execution of the actual stub
reached the original entry with all tested registers/flags unchanged and the
expected marker present. Output size: 1,130,124 bytes; image SHA-256:
`9bed567d121c1d93935306ce5af4abfbe5a9ecad8c07ae7b7b3436ee047209f3`.
Local model review produced an unsubstantiated slice-overflow finding; bounds
were manually checked. An independent FABLE review timed out after 240 seconds
without a verdict. Emulator success does not validate the entire IBB handoff
or prove that stock ELK will preserve the marker indefinitely.

The candidate replaced the raw Probe image in GHS A, padded with zeros to
64 MiB. Full readback SHA-256:
`38290db2d2638051411586d24026015cd2d5846f296006a7d3abf3c4c3e88784`.
GHS B remained zero-filled and GPT bytes were unchanged. Selector 0 returned
`20870000`; Probe then rebooted. ELK fastboot returned
`kernelflinger-07.02-userdebug`. Its built-in crashmode ADB memory reader showed
neither the stub nor the marker at the expected addresses; marker bytes were
`4c39cc89d9acdc389e29fd28ad38fe08c5945695e69f453a46805438c3945706`.
Policy bytes at `0xC0200` were `01 20 F9 FE` (authentication bit still set).
No custom entry execution was demonstrated. The result is consistent with
stock SPI-ELK fallback and the traced unsigned-image rejection gate; no early
IBB error was captured to distinguish every possible rejection stage.

A subsequent owner-reported full power cycle was checked before downloading
any RAM image. USB identified ELK fastboot; switching to its in-process
crashmode ADB reader again found no marker or stub. The 32 bytes at
`0x12901C50` were
`181789869d9299178b06b816f916b926cecd5dddede64e725cc84e41d9dc4c5c`.
Policy at `0xC0200` remained `0xFEF92001`. This adds a cold-power observation
consistent with fallback, but neither proves the precise IBB rejection stage
nor excludes a marker-lifetime defect. Partition contents were not reread
during this diagnostic-only observation.

Storage immediately after the experiment contained the unsigned entry-probe
IPK in GHS A and zeros in GHS B, superseding the raw-Probe placement.
**Restored after testing, 2026-11-17:** both GHS partitions were restored from
the original eMMC backup while running RAM-booted stable04. Each complete
64 MiB partition readback matched SHA-256
`13e168dd9ff073f2c40ef1fb42ed44627474554dbf9d4a2f23879a8c77f525a0`.
The live GPT header and entries were verified before writing and remained
byte-identical afterward. Current storage has both original GHS images;
no reboot was performed after restoration. Probe remained running in RAM.
The next successful milestone must distinguish authenticated container acceptance
from merely well-formed headers; passing an ELF emulator is insufficient.

**Separate Android boot-partition placement test, 2026-11-17:** after
restoring GHS and successfully reaching the stock HMI, ADB reported
`ro.boot.slot_suffix=_a`, `ro.build.type=user`, and `sys.boot_completed=1`.
The radio clock was synchronized from the host before subsequent work.
The documented CAN ELK-entry routine succeeded and its temporary VIP gate
was restored; stable04 Probe was then RAM-booted for the storage operation.

The live GPT identified `boot_a` at LBA 436224 (byte offset `0x0D500000`),
size 64 MiB. Before writing, the full live partition matched the saved eMMC
backup SHA-256
`610ffec9c52ca0658d4c13663015e3496854d66c9be380b6161b563b765dbaf3`.
The complete partition was zero-filled and its zero readback hash verified.
The 30,306,304-byte stable04 Probe boot image was written at partition offset
zero, leaving a zero tail. Full 64 MiB readback then matched SHA-256
`30ad12e2cf1ad6dd7aa71c56b8f6f1bc1a3ccb6a509da9455cab576ab0487b84`.
Independent before/after hashes confirmed `boot_b`, `ghs_isys_a`, and
`ghs_isys_b` unchanged; the GPT was also byte-identical. No reboot was issued
after this write. Current state: Probe running in RAM; stock GHS A/B and
stock boot B retained; boot A contains Probe. Successful guest boot or
recovery from a rejected Android boot image was not established by the
storage-only operation. A subsequent reboot reached VIP `evSoC_StartupComplete`,
`HmiInit`, and `evHMIReady`, without a Probe USB gadget. After ADB was enabled,
AAOS reported `ro.boot.slot_suffix=_b`, `ro.build.type=user`,
`sys.boot_completed=1`, and kernel
`4.19.283-PKT-230612T042614Z-ga53d763f5b0d`. Thus the observed result was a stock
slot-B boot after replacing active boot A with Probe, not execution of Probe.
No manual slot switch was issued. This establishes recovery to the intact B
slot in this trial, but does not identify the precise image rejection stage
or establish ELK recovery if both Android boot slots fail. At that checkpoint,
runtime was stock AAOS on B and boot A contained Probe. The clock was
resynchronized from the host during the ADB check.

**Restoration after the slot-B observation:** the documented CAN ELK entry
succeeded, its temporary VIP gate was restored, and stable04 was RAM-booted.
Only boot A was restored from the backup; the full 64 MiB readback matched
`610ffec9c52ca0658d4c13663015e3496854d66c9be380b6161b563b765dbaf3`.
Before/after hashes confirmed boot B, both GHS partitions, and misc unchanged;
GPT bytes also remained unchanged. HECI selector 0 was acknowledged with
`20870000`. No reboot followed this restoration. Current runtime is Probe
in RAM; boot A/B and GHS A/B contain stock images. Selector 0 requests the
normal firmware path and does not itself establish that Android slot A has
been reactivated; slot metadata was deliberately left untouched.

IBB main `0xE03E4` reaches the automatic selector `0xEC325`. Its ordinary
configuration tag is `0x4B`; `0xEF2BE` walks matching records and invokes
`0xEC0EA`. The configuration locator `0xEF255` follows the FIT SMIP entry and
selects section type 2. In the extracted, authenticated SMIP component this
section begins at `0x1AEA`, length `0x1374`. Its boot records have no condition
words and contain the following order (offsets relative to that section):

| Record offset | Source / partition | Image offset | Meaning against the saved GPT |
|---|---|---|---|
| `0x1C` | eMMC / 1 | `0` | `ghs_isys_a` |
| `0x28` | eMMC / 2 | `0` | `ghs_isys_b` |
| `0x34` | SPI / default component | `0` | `ELK`, with `OBBX` lookup fallback |
| `0x40` | eMMC / 5 | `0x7D0000` | IPK-wrapped Kernelflinger OS-loader image within `bootloader_a` |
| `0x4C` | CLI | — | Firmware command interface |

**Offset image identified, 2026-11-17:** the saved eMMC dump contains an
`ipk.` container at `bootloader_a + 0x7D0000` (absolute `0x0A0D0000`).
An ELF32 little-endian x86 header occurs at container offset `0x22C`, with
entry point `0x12800000`. Embedded strings identify
`hardware/intel/kernelflinger/kf4abl.c`, `kernelflinger-07.02`, Android boot
parameters and USB/TCP fastboot. This identifies a Kernelflinger OS-loader
component, not the Android kernel or GHS image. `bootloader_b + 0x7D0000`
(absolute `0x0BED0000`) has the same first 512 bytes and matching sampled
identifying strings; no full-image equality is claimed. The first-512-byte
SHA-256 for both is
`43bed592674ae8b86e81492f19ca7b0403f4174ac9f8f3ede2359062ccfa2938`.
The loader code's `osloader.bin` lookup and raw-offset fallback corroborate
the component role. Sharing Kernelflinger lineage and entry address with
SPI ELK does not establish binary identity or equivalent standalone startup.
The selector-3 black-screen trial does not prove this component's entry
point was reached; its authentication/handoff result was not captured.

The callback skips candidates preceding the requested boot index. When a
loader returns, including a returned authentication error, the callback returns
zero, allowing the walker to try the next candidate. A successful handoff need
not return. The ordinary raw-image path still requires a valid IPK header/CRC
and, with the observed authentication policy enabled, an authorized signature.
A raw Android Probe `boot.img` is not a direct replacement for these candidates.
SMIP tag `0x5A` has zero feature flags; do not substitute assumptions about the
optional A/B-metadata selector for these explicit partition records.

**ELK startup boundary:** the inspected ELK main path calls boot-device discovery
`0x128AB2B0`, slot initialization `0x128B3970`, RPMB initialization, and misc/slot
handling `0x128B4470`. Failed boot-device discovery returns an error before
fastboot. The slot code checks for `boot` slots and can reinitialize corrupt A/B
metadata; merely reaching ELK is not proof that an erased storage layout is
safe. RPMB initialization failure is logged and the main path continues.

After those steps, target 4 enters crash-mode ADB. The other traced targets
enter fastboot at `0x12801400`. The downloaded-image branch checks the unlocked
predicate before calling the Android/bzImage loader `0x1289FB70`. No automatic
storage-kernel load was found in this startup path. Thus automatic entry into
SPI ELK and autonomous boot of a custom kernel from eMMC are separate outcomes:
the former has static code/configuration evidence; the latter remains unproven.
Neither failed-GHS cold boot nor blank-GPT operation was tested, and no flash
contents were changed for this trace.

**Root filesystem boundary:** a trusted bootloader may permit a custom kernel,
or a trusted kernel may permit a modified root filesystem, depending on later
verification. This radio's observed ELK RAM-boot behavior establishes neither
permission for unsigned normal GHS images nor acceptance of a modified stock
AAOS root filesystem. GHS guest-image checks, AVB/dm-verity enforcement, and
mount policy must be assessed separately before claiming that route works.

#### Expanded readback audit and coverage — 2026-11-17

**Coverage:** a bounds-checked traversal of both BPDT roots and their secondary
headers accounts for every non-`FF` byte in the 8 MiB file. There are no
unclassified non-`FF` bytes outside declared regions or BPDT headers. This is
file-layout coverage, not proof of complete physical SPI coverage or complete
semantic analysis. The 8 KiB DEBUG_TOKENS allocation is all zero; IFP_OVERRIDE
(16 bytes) and UEP (264 bytes) contain data whose full policy semantics have
not been assigned.

[ME Analyzer](https://github.com/platomav/MEAnalyzer), commit
`d27ccdba0aadbad490f47b5b631c369b682a7ef5`, successfully unpacked the CSE
material. Its checks reported eight valid RSA partition signatures (SMIP,
RBEP, PMCP, FTPR, IBBP, ISHC, NFTP, IUNP), two valid RSA key-manifest
signatures (`rot.key`, `oem.key`), and 90 valid module/metadata hashes; none of
these checks reported INVALID. No firmware was uploaded to that project.
The original invocation failed with
`AttributeError: 'NoneType' object has no attribute 'set_title'`; rerunning
with terminal-color initialization disabled completed the analysis.

**Boot-policy binding:** IBBP's authenticated `BPM.met` (extension `0x13`)
contains SHA-256 digests matching the complete extracted IBBL, IBB and ELK
containers. The OBB digest is
`ed6b88e24606a4c75151c4c6f72482b113f43f3356be4bd45f17a026b58f9b9a`,
which matches ELK. This is evidence binding ELK into the signed boot policy,
not merely the existence of an unrelated signature. `IBB Flags=0` must not
be interpreted as authentication disabled without tracing that field's consumer.

**eMMC signature cross-check:** both saved `ghs_isys_a` and `ghs_isys_b`
containers have signed-image flag `0x02` set (header byte 5 is `0x03`). An
independent integer-RSA verification checked the entire PKCS#1 v1.5 encoded
block, SHA-256 DigestInfo and image digest; both pass RSA-2048/SHA-256.
The signature starts at partition-file offset `0xE3CC00`. The key hash
(SHA-256 of reversed stored modulus followed by stored little-endian exponent)
is `e99d2f484fd63e6846e1d2a8a624d1685d4c7fc8453e2851d8c36658579beab7`,
matching the OEM key-manifest **OS Kernel** usage. That usage is decimal 39
(`0x27`), the exact purpose supplied by the IBB loader to the key selector.
This connects the eMMC image, permitted signing key, verifier and policy gate.
Signature validity does not by itself prove enforcement; the separate live
`ABL.secureboot=1` observation supports that part of the chain.

### Full-dump GHS-slot structural corroboration — 2026-11-18

The complete eMMC backup GPT places `ghs_isys_a` at sectors 2048–133119 and
`ghs_isys_b` at 133120–264191; each is 64 MiB. Read-only extraction found both
slots byte-identical:

```text
SHA-256  13e168dd9ff073f2c40ef1fb42ed44627474554dbf9d4a2f23879a8c77f525a0
```

Both begin with an IPK-style header whose visible metadata includes
`board=harman_info35` and `gm_part_number=85098662BM`. At partition offset
`0x5c`, each contains the same 14,924,936-byte ELF: `ELFCLASS32`, little-endian
`EM_386`, statically linked and stripped, entry `0x200000`. This corroborates
the GHS/VMM model from the separately recovered boot flow; it is not a Linux
kernel or filesystem.

The ELF section map includes `.bootargs`, `.boottable`, `.vmm1.text`,
`.vmm1.rodata`, `Guest1_VM_Memory_RAM0` through `Guest1_VM_Memory_RAM4`, and
`.mr_r_mod_android_key`. Its retained names/string evidence include
`BootargsDev`, `OtaUpdateBootArgsIod`, `KeymasterBootArgsIod`, `IOD_Bootargs`,
`kernel_boot_params`, `parse_cmdline`, `VMM1_InitialTask`, and
`ASP_VMX_SetGuestKernelAddr`/`ASP_RunGuestVM` evidence documented in §1. This
is consistent with GHS assembling guest inputs, selecting/verifying the Android
boot image, allocating Guest1 memory, then launching the Android kernel as a
VM. It does not alone prove the precise producer/consumer path for every
Android cmdline token; the retained guest cmdlines and the VMM1 launch trace in
§1 remain the evidence for that behavior.

Static string inspection also found console-logging and Ethernet/ARP routines.
It found no demonstrated interactive shell daemon or service (`ssh`,
`dropbear`, `telnet`, or `inetd`). Console/network code therefore must not be
reported as a GHS shell or a retained management channel.

**Remaining IBB payloads:** four-byte alignment between compressed blocks
resolves the previously unparsed payloads. Their block starts are `0x15938`
and `0x19EB0` within IBB, with compressed allocations `0x4576` and `0x1C191`.
Their decompressed lengths exactly match their declared sizes:

| Payload | Decoded bytes | SHA-256 | Inspection |
|---|---:|---|---|
| 1 | 119,872 | `06e4c0a30bc8c4ccd838149360f816dd3b02490da6600f693bdb7df23ea93345` | IBB image-loading/authentication code |
| 2 | 37,312 | `2d525aaa4f8f46516eaf13bdb62ccba20fdf0bc563eb89e4cdc2db31dc9419ea` | Data including ACPI material; not exhaustively interpreted |
| 3 | 197,440 | `c7a6dbb46bbbe06401aaa90a1e0347f242abfb3cda64960a3a08e8e5ca6d8aa0` | DRAM initialization/training code; no claim of exhaustive control-flow analysis |

**IBBL handoff:** analysis of IBBL at SRAM base `0xFEFFC000` resolves its
absolute references. At `0xFEFFD283` it selects a copy descriptor containing
destination `0xC0000`, count `0x430` dwords, source `0xFEFFD500`; helper
`0xFEFFD1ED` performs `REP MOVSD`. Consequently policy location `0xC0200`
comes from SRAM `0xFEFFD700`. Startup then jumps to `0xE0080`.
**Initializer resolved further, 2026-11-17:** the calls outside IBBL resolve
into decoded IBB payload 3 at base `0xFEF82800`, not an inaccessible SPI tail.
At payload offset `0x1EA` (`0xFEF829EA`), the entry calls `0xFEF854F0`
(payload offset `0x2CF0`) with a local output word; instruction `0xFEF82A21`
stores that word at `0xFEFFD700`. The IBBL copy described above subsequently
places it at `0xC0200`. The base is corroborated by the caller destination,
function prologue, and absolute string pointers (`CPU: ` at `0xFEF8291E`,
`No CSE bp, halt` at `0xFEF854DF`).

`0xFEF854F0` reads the FIT pointer at `0xFEFFFFC0`, walks 16-byte records,
and selects `(record[14] & 0x7F) == 0x10` and `record[11] == 3`. It copies
up to two bytes from the selected record's address. The first byte's bits
2 and 3 replace bits 0 and 1 of the output byte:
`output = (output & ~3) | ((record_payload[0] >> 2) & 3)`.
Absence of the matching record prints `No CSE bp, halt` and enters a HLT loop.
Thus the immediate authentication-policy input is this CSE boot-policy FIT
record: its bit 2 supplies the IBB authentication-enable bit.

**Producer resolved, 2026-11-17:** CSE RBE creates the `ifp_uep` handoff;
CSE BUP reads `SbPolicies` from it and constructs the FIT record consumed by
IBB. The previous “creator unresolved” conclusion is superseded by the trace
below. No VIP, CAN, or external EEPROM writer was found in this chain.

#### CSE producer of IBB boot policy — 2026-11-17

Address spaces must remain separate: RBE code is based at `0x40000`, BUP code
at `0x26000`, and the host IBB payload-3 code at `0xFEF82800`. The RBE module
SHA-256 is `6e3e85b1b09a4af39310bfdcb6db6cf5bc2c8d1b207bc3439f8c55f678b11571`;
BUP is `d43565540bd95402d5ee99923ea93889da72873dc103836bbb87b47025a0ffda`.
These modules were extracted from the readable mapped IFWI.

1. **RBE creates the incoming object.** `0x43BB2` calls `0x416EE` to allocate
   named object `ifp_uep`, length `0x108` (264 bytes), in its outgoing handoff
   buffer. The payload is an eight-byte header followed by 256 bytes of data.
   It passes bits 27:24 of CSE register `0xF6170810` to `0x41F3B`.
   That predicate returns true when either upper nibble bit and either lower
   nibble bit are set: `((n & 0xC) != 0) && ((n & 3) != 0)`.
2. **Hardware versus stored source.** On true, RBE copies 256 bytes from
   CSE hardware window `0xF6170800–0xF61708FF` into the object after its header
   and writes header marker `REAL` (`0x4C414552`). These are CSE-space addresses,
   not addresses proven accessible through Probe `/dev/mem`. Otherwise
   `0x43A67` looks up record type `0x11` through `0x42048`, requires length
   `0x108`, reads it through `0x44CE2`, and validates `$UEP` plus a 16-bit CRC
   through `0x43A38`/`0x43A0D`. The CRC covers bytes 6 through 263, starts at
   `0xFFFF`, and uses the table at RBE `0x4890C`.
3. **BUP receives and initializes its reader.** `0x288EF` receives named handoff
   objects into a list; `0x28D32` looks up their names. Initializer `0x32F50`
   looks up `ifp_uep`, copies its eight-byte header and 256-byte data into its
   local context at `0xA47FC`, and records whether the marker is `REAL`.
   This is an incoming snapshot, not a filesystem lookup of `ifp_uep`.
4. **The policy item is named.** `0x3315D` calls
   `0x29D2E(0x23, 2, &0xA5D60)`. Reader `0x29C19` resolves item descriptors
   through `0x2ACFA`; item `0x23` is `SbPolicies`, a 16-bit type-2 field.
   Its 44-byte descriptor is at BUP file offset `0x32AD8`, corresponding to
   the descriptor-table address `0x9FAD8` used by the code. The table starts
   at file `0x324D4`; its named IDs and stride corroborate the mapping.
   `0x2CD4A` tests two validity bits at data-bit offset `0x86` through
   `0x2DFE4`, then reads through `0x28B0E`.
5. **Three-copy decoding.** Mapping at BUP `0x566F4` is `0x00100140`
   (16 bits, logical bit offset `0x140`). The mapping table selects copies at
   data byte offsets `0x28`, `0x6C`, and `0xC0`. `0x2B0ED` combines each bit
   by majority: `(a & b) | (a & c) | (b & c)`. The resulting word enters
   `0xA5D60`. Status `0x1C2` instead clears its low 16 bits. `0x3315D` also
   adds bit `0x200`, separate from the authentication bit.
6. **CSE can modify the effective policy.** BUP `0x3C51D` clears policy bits
   2 and 3 (`& 0xF3`) when global `0xA5EA0 & 0x01004000` is nonzero. The
   branch can also clear bits 0–1 and bit 8 when `0x4000` is set. These are
   internal startup conditions, not a demonstrated host command or runtime
   toggle. Static producers of both mask bits are traced below; their live CSE
   values remain unverified.
7. **BUP creates the exact FIT record.** `0x3A831` initializes the FIT header.
   At `0x320DF–0x320FE`, BUP copies the low word of `0xA5D60` into its mapped
   host handoff buffer at offset `0x420`, then calls `0x2F525` to append an
   entry with host address `0xFFFE0420`, size 2, type `0x10`, subtype 3.
   `0x2F525` explicitly fills those fields and increments the FIT count.
   IBBL later relocates the FIT and eligible payloads; the consumer follows
   the entry address rather than assuming its original address remains fixed.
8. **Host-side consumption.** IBB payload 3 `0xFEF854F0` maps payload bits 2–3
   to its policy bits 0–1; `0xFEF82A21` stores the result at `0xFEFFD700`.
   IBBL copies that handoff block to `0xC0000`, putting the policy at
   `0xC0200`. IBB's image-loader authentication gate reads bit 0 there.

**Stored-policy verification:** the actual `$UEP` record is at mapped IFWI
file offset `0x200210`, length 264, SHA-256
`558b0ab8659647a4c70f7323356e73c99b64fe793a649378007a261361f9dfa4`.
Using RBE's own CRC table and algorithm gives `0x3059`, matching its stored
CRC. Validity bits at `0x86` equal 1. All three `SbPolicies` copies are
`0x0117`; bit 2 is set, so this stored policy supplies authentication-enable=1
before any later CSE overrides. A second literal `$UEP` inside RBE code at
file `0x209A43` fails the record CRC and is not another policy record.

**Evidence boundary:** the creator and both possible backing sources are now
identified; the source is not established to reside in the blocked final MiB.
The stored-policy branch demonstrably requests authentication, and previously
observed `ABL.secureboot=1` is consistent with that. This does not independently
measure the live hardware snapshot, prove which RBE branch ran, or prove that
no CSE override applied on a different boot. A complete physical SPI read can
still contain additional relevant material. No fuse, RPMB, EEPROM, eMMC, SPI,
CAN state, or live policy values were written by this analysis.

**CSE bring-up:** metadata supplies x86 code base `0x26000` for `bup`,
`policy` and `fpf`. These are separate modules/address spaces, not one image
loaded at the same address. BUP's `0x52E4B` reports a secure-boot bad-image-path
error; callers include `0x2C74F` and `0x3323C`. The latter inspects platform
register-helper results and an FTPR manifest extension before invoking its
next stage. The register-helper meanings and ROM dependencies are not yet
fully resolved. The configuration record `/home/policy/IBB_sig` is empty in
the extracted Intel defaults; code at `0x37432` acts only on nonempty reads.
That empty default is not evidence that image authentication is disabled.

**Audit conclusion:** the evidence supports authenticated stock eMMC boot
and a distinct unlocked ELK RAM-boot path. It does not support a blanket
"secure=no platform" interpretation or assurance that an arbitrary unsigned
eMMC replacement will boot. The static inventory/integrity audit covers the
whole saved window; a complete ROM/fuse/CSE enforcement audit remains open.


**`SbPolicies` status `0x1C2` producer resolved, 2026-11-17.**
This status is generated by the validity check, not a general I/O-error fallback.
The item-`0x23` descriptor (type 2, BUP file offset `0x32AD8`) selects validity
bit offset `0x86`. Reader chain:
`0x29D2E -> 0x29C19 -> 0x2CD4A -> 0x2DFE4 -> 0x28A84`.
`0x28A84` extracts two bits from the selected in-memory UEP/fuse snapshot.
After a successful extraction, `0x2E012` tests the extracted byte against 3;
`0x2E018` executes `MOV AX,0x1C2` only when both bits are zero. Validity
pairs 01, 10, and 11 pass this check. On 00, `0x2CD4A` returns immediately
without reading the three policy-value copies through `0x28B0E`.

Initializer `0x3319B` compares the returned status to `0x1C2`; `0x331A2`
executes `MOV word ptr [0xA5D60],0`. Other nonzero read errors take the
`0x2B` error path instead. Initialization also reads item `0x16`; successful
or `0x1C2` handling there permits a success return. The policy word is later
ORed with `0x200`, so the immediate zero value should not be described as
its final published value. Source authentication bit 2 remains clear on this
path unless another later writer changes it.

`0x32F50` copies the 256 data bytes of incoming `ifp_uep` (payload + 8) to
`0xA47FC`; the validity bits are bits 6–7 of data byte `0x10`. Thus the
condition depends on the snapshot selected upstream by RBE: hardware-backed
`REAL` data or the validated stored `$UEP` record. It does not indicate an
ordinary failed SPI read, nor does it establish which snapshot this boot used.

The saved valid `$UEP` at mapped IFWI offset `0x200210` has data byte `0x10`
=`0x54` (absolute file offset `0x200228`). Its validity pair is **01**, so
that stored snapshot does **not** trigger `0x1C2` for `SbPolicies`. This was
verified by decoding the actual descriptor and saved record, without modifying
either. The RBE CRC/record checks still precede this reader; malformed storage
is not demonstrated to produce a benign zero-policy result.

**Override producers traced further, 2026-11-17.** The mask combines two
independent paths, rather than one unexplained enable flag:

- **Bit 14 (`0x4000`): token knob.** BUP `0x3C4B0` looks up incoming object
  `utknknobs`. Its payload is a count followed by key/value dword pairs.
  Key `0x80860030`, value `2`, sets byte `0xA5EA1` bit 6, equivalent to
  dword `0xA5EA0` bit 14. Value `1` sets bit 15 instead and does not by itself
  satisfy the override mask. Startup calls policy initialization `0x3315D`,
  then knob processing `0x3C4B0`, then override application `0x3C51D` at
  call sites `0x31967`, `0x3197D`, and `0x31982` respectively.
- **RBE supplies the knob object.** RBE `0x47E7C` obtains a token through
  `0x47038`, then processes it in `0x478D7`. Sources include an 8 KiB `UTOK`
  lookup path (`0x46FF4`) and record type `0x12`/selector `0xB` (`0x46F44`).
  The parser checks lengths and extension type `0x15`; it calls `0x47404`
  and applicability checker `0x476FC` before creating `utknknobs` at `0x47D8D`.
  `0x47861` filters permitted knob IDs by token class. The authentication
  path includes a SHA-256 key-material comparison (`0x41C6A`) and signed
  `$MN2` manifest verification (`0x4722D`, including modular exponentiation,
  digest and padding comparisons). One class-3 branch skips the key-hash
  comparison under additional internal conditions but still invokes manifest
  verification. No arbitrary unsigned token acceptance was established.
- **Bit 24 (`0x01000000`): context-gated counter.** In `0x3C51D`, this bit is
  set only when globals `0xA5E94 == 9`, `0xA5E98 == 3`, policy bit 9 is clear
  (`0xA5D61 & 2 == 0`), and helper `0x47FF5` returns a nonzero nibble.
  Assembly confirms that nibble is bits 11:8 of register offset `0x38`,
  read via service `0x11CD` using selector `0xA471C`. Initialization at
  `0x3B8D0` sets that selector to `0x17`. These are CSE register-service
  arguments, not established host physical addresses.
- **Counter handling.** The successful path calls `0x48017`, which selects
  operation `0x15` in `0x3CB4D`: `(counter + 15) & 0xF` decrements the nibble.
  Other paths call `0x4802A(0xF)`, selecting operation `0x16` to write nibble
  `0xF`. When the context gates pass but the counter is zero, bit 24 is
  explicitly cleared. When context gates fail, this function does not
  explicitly clear bit 24; its prior initialization therefore also matters.
- **Context provenance.** Writes at `0x375DA/0x375DF` copy offsets 8 and 6
  from the 24-byte context returned by `0x2AD35` into `0xA5E94/0xA5E98`.
  That reader uses cached context `0xA5860`, or `0x551BC` after initialization
  flag `0xA5710` is set. `0x55163` reads the CSE-internal object
  `/snowball/pm_ctxt`; fallback defaults include offset 8 = 9 but offset 6 = 5,
  which does not satisfy the required value 3. The producer of the qualifying context values and a counter initializer
  were subsequently traced as detailed below; live branch selection remains
  unverified. This CSE-internal object is not an AAOS or
  Probe filesystem path.

**Qualifying context and counter provenance, further trace 2026-11-17.**
BUP `0x369B1` produces the context pair directly from the nine-byte incoming
`pm_trans` record. `0x315C6` looks it up by name and copies it to context
base + `0x58`. Let `T` be its first little-endian dword and `F` its byte 8.
The branch producing context offset 8 = 9 and offset 6 = 3 requires:

- `F & 1` nonzero;
- `T & 0x3400 == 0`;
- `T & 0x110 != 0x110` and `T & 0x120 != 0x120`;
- `T & 8` nonzero.

It writes context base + `0x28` = 9 and base + `0x26` = 3. `0x3CDF1`
copies the 24-byte context at base + `0x20` to the cached context at `0xA5860`;
`0x2AD35` and `0x375DA/0x375DF` subsequently deliver those bytes to the override
predicate. The later `/snowball/pm_ctxt` path is therefore not the original
producer of this early pair.

RBE already receives `pm_trans`: `0x4033D` calls object lookup `0x4169C`, which
walks the existing handoff-object region at `0x08200000`. It saves the payload
pointer at `0x0604101C`. The examined RBE references consume this record rather
than constructing it. Consequently the unresolved upstream boundary is the
pre-RBE producer of this record and the physical event represented by bit 3;
calling it a specific reset type or a CAN command is not yet justified.

**Pre-RBE boundary audit, 2026-11-17.** Instruction-level confirmation in
BUP: `0x36A65` executes `TEST DL,8`; when the earlier gates pass, `0x36A6A`
writes byte `[EBX+0x28]=9` and `0x36A6E` writes `[EBX+0x26]=3`. These are
writers of the derived context, not writers of the incoming `pm_trans` bit.
Neighboring cases handle bits 2 and 1 separately, so the labels of those
transition classes must not be guessed from ordinary host reset terminology.

RBE metadata declares entry `0x40825`. Its initial path calls `0x4000C`
(copy eight bytes of initialized data), `0x4052E` (clear local BSS and capture
registers through `0x41F18`), `0x404AD` (early initialization), and then
`0x40556`. The latter first calls `0x4033D`, which requires existing `pm_trans`
and other handoff objects. `0x41F18` reads CSE addresses `0xF00B0200/204/208`
into local cached state; those loads do not construct `pm_trans` or establish
that its bit 3 equals any particular bit in these registers. Lookup `0x4169C`
walks the existing object list. Allocator `0x416EE` appends new objects and
increments the list length; the located `pm_trans` name reference invokes
lookup, not allocation. The audited path strengthens the pre-RBE provenance
boundary but does not identify an upstream writer instruction.

No standalone CSE ROM/ROM-bypass binary was found by filename searches of the
local research, downloaded and temporary artifacts, and no `pm_trans` definition
was found in the searched Apollo Lake Slim Bootloader/FSP references. This is a
bounded search, not proof that all archives or unread flash contain no copy.
Intel's Apollo Lake TXE bring-up guide, Appendix A, identifies a Broxton ROM-bypass
image in the firmware kit's `Image_Components\TXE` directory:
[manufacturer-authored guide hosted by Portwell](https://www.portwell.eu/index.php?download=&eID=dumpFile&f=10256&t=f&token=20c391849cdade3c09a5690b3108c9bddae1ac8b).
That is a candidate analysis artifact, not evidence this production radio uses
ROM bypass. Locating matching pre-RBE code or an authoritative record definition
is still required to name the physical event and give the originating writer PC.
No reset experiment or CSE/PMC register write was performed during this audit.

**Additional artifact search, 2026-11-17.** Raw byte searches found exactly
two literal `pm_trans` strings in the saved 8 MiB mapped IFWI, at offsets
`0x20E65D` (RBE) and `0x278C7C` (BUP). The independently captured 7 MiB BIOS
region has the corresponding two strings at `0x10E65D` and `0x178C7C`.
Neither saved eMMC boot-area image (`emmc_boot0_wifi.bin` and
`emmc_boot1_wifi.bin`, each 33,423,360 bytes) contains the literal `pm_trans`
or `ROMB`. No literal `ROMB` was found in either SPI-related artifact.
These searches do not exclude compressed code, constructed names, or code
outside the readable region; they did not locate a new writer.

[Intel support identifies TXE 3.1 firmware package 632453](https://community.intel.com/t/cant-find-txe-rom-spi-image/95861)
in response to a request for the ROM-bypass image. The referenced package URL
currently redirects to Intel's `404Redirector.aspx`; no matching package was
retrieved. The pre-RBE writer PC and physical-event mapping remain unresolved,
not newly established by the repeated searches. Access to matching ROM/ROM-bypass
code or a documented CSE transition-record definition is still needed for this
specific static trace. The existing ROM-origin attribution remains an inference.

**Transition interpretation and address-space qualification, 2026-11-17.**
Additional BUP string-pool inspection finds `GlobalReset`, `PsuedoGlobalReset`,
`CseReset`, `HPCR`, `HNPCR`, `CsePowerOff`, `CsePowerOn`, `HostSxEntry`,
`HostSxExit`, followed later by `CM0`/other CSE power-state names and
`S0`, `S1`, `S3`, `S4`, `S5`. There are no recovered direct references or
numeric lookup table binding these names to context enum values. Nonetheless,
BUP maps transition bits 3/2/1 to event value 9 and prior-state values 3/4/5,
respectively. Combined with the string vocabulary and allowed context-value
ranges, this supports **S3/S4/S5 exit** as a candidate interpretation, with
bit 3 indicating S3 exit. This is inference, not a proven event mapping.
Do not describe it as an arbitrary reset or a verified authentication-bypass
trigger. `0x3C47C` also distinguishes prior-state value 3, setting a context
flag to 2 versus 1 for other states; the downstream meaning is not resolved.

The RBE address `0x08200000` is an address in the CSE execution environment,
not an established host physical RAM address. RBE `0x460F9`/`0x4618C` manage
page mappings for the object buffer. Reading host `/dev/mem` at that numeric
address would not establish that the CSE handoff record had been read.
No direct host mapping, live `pm_trans` capture, or pre-RBE writer PC was
established in this follow-up.

The counter has a confirmed software initializer: BUP `0x3C51D` calls
`0x4802A(15)` when the qualifying context/policy gates fail, and also when the
qualifying path finds counter zero. `0x3CB4D` operation `0x16` writes this value
into register bits 11:8 through selector `0x17`, offset `0x38`. A qualifying
nonzero path instead uses operation `0x15` to decrement it modulo 16 and sets
bit 24 for that invocation. A zero-count invocation clears bit 24 and reloads
15. This proves BUP can initialize/reload the field; its silicon reset value
and retention across different reset/power events remain unverified. A live
CSE register read has not been performed.

Result: two concrete static mechanisms can suppress policy bits 2–3 before
FIT publication, but neither is a verified host-accessible command. This trace
performed no token installation, register writes, or boot-policy changes.

#### Local Apollo Lake reference survey — 2026-11-17

Searched extracted text from all 16 PDFs and the downloaded repository source
content in the Intel-Apollo-Lake reference collection. These references corroborate
several field meanings; they do not supply the missing pre-RBE `pm_trans` writer.
This was a local static survey, not a new hardware test.

* **Exact policy-field names:** Slim Bootloader
  `Silicon/ApollolakePkg/Include/Library/BootGuardLib20.h:16` defines
  `Pbe` bit 0, `Bbi` bit 1, `Vb` bit 2, `Mb` bit 3, `KmId` bits 4–7,
  `Dcd` bit 8, and **`Sb_S3_Opt` bit 9**. Its matching
  `Library/BootGuardLib20/BootGuardLibrary.c` consumes FIT type `0x10`,
  subtype `3` for this policy; subtypes `2`, `7`, `8` carry TXE, IBBL,
  and IBB hashes. Coreboot independently has the same policy layout in
  `src/soc/intel/apollolake/include/soc/measured_boot.h`.
  This directly corroborates the traced verification/measurement bits and
  identifies bit 9 as an S3-related option. The BUP condition requiring bit 9
  clear now has a named reference counterpart. It strengthens, but does not
  prove, the inferred S3-exit meaning of `pm_trans` bit 3; neither header
  defines that transition record or the option's polarity/complete behavior.
* **Token override semantics:** `Secure_Tokens_APL_GLK.pdf`, printed pages
  7 and 14, describes signed-token acceptance and a BIOS Secure Boot knob:
  0 production-key validation; 1 R&D keys/policies; 2 no BIOS BPM validation.
  Despite the local filename, its body explicitly describes GLK; therefore
  it is supporting family documentation, not alone proof for this APL unit.
  MEAnalyzer `MEA.py`, `CSE_Ext_15_Payload_Knob.ext_print`, maps the exact
  `0x80860030` identifier to these three values for its non-CSME-12+ branch.
  Together with the target's own authenticated-token parser and value-2
  consumer, this corroborates the traced override's intended role. It does
  not establish an accepted token or signing authority for this radio.
* **IBBL/IBB packaging:** `Signing_and_Manifesting_Guide.pdf`, printed pages
  19–20, places IBBL, IBB and BPM metadata in the IBB subpartition and
  describes hashes covering IBBL/IBB/OBB. `UEFI_Firmware_Enabling_Guide.pdf`,
  pages 9–13, describes BPDT logical boot partitions and TXE loading IBBL
  into shared SRAM before PMC releases the host from reset. IBB executes
  in cache-as-RAM and OBB in DRAM. This is not a first-GPT-partition boot rule;
  the GM-specific later eMMC/GHS selection still requires its own trace.
* **Two meanings of FIT:** the Flash Image Tool configures/stitches IFWI;
  the runtime Firmware Interface Table conveys the policy and hashes.
  These must not be treated as the same object. Slim Bootloader's
  `Platform/ApollolakeBoardPkg/Script/StitchLoader.py:506` checks a UEP
  component at relative offset `0x30`, rejecting a nonzero low nibble.
  This is a tool eligibility check, not a live fuse measurement, and its
  offset must not be transplanted into the GM image without layout matching.
* **ROM-bypass lead:** `559702_SPI_SMIP_Programming_Guide.pdf`, page 14,
  describes an optional TXE ROM-bypass region beginning at flash offset 4 KiB;
  absent ROM bypass has region size zero. The bring-up guide also describes
  this development component. Neither establishes that the production GM
  image contains it, or that the inaccessible SPI tail contains the writer.
* **ELK status caution:** upstream kernelflinger
  `libfastboot/fastboot.c:1272` publishes `secure=no` as a literal string.
  That reference behavior is not a fuse/policy measurement and requires
  binary matching before attributing the same implementation to GM ELK.

No exact `pm_trans` or `SbPolicies` definition was found in the searched
reference text/source. The SPI/SMIP guide's section titled “TPM Configuration
and Boot Guard OEM Policy” only documents TPM presence/location in the shown
table; its title is not evidence that it explains the missing override.
The most useful next static comparison is the newly named `Sb_S3_Opt` field
against the BUP bit-9 branch and the CSE transition-record producer. Policy
creation and publication are corroborated; the physical event/producer PC
and a persistent custom-image boot path remain unresolved.

#### Additional reference documents: recovery straps and VIP flash — 2026-11-17

Eight additional PDF filenames were inspected. The explicitly named Intel
334817 volume 1 revision 004 and 334819 volume 3 revision 005 files are
byte-identical to the earlier numeric filenames. The other six additions
are five Renesas manuals and a Bosch VCURH1 regulatory description.

A previously missed lead in Intel 334817, section 2.30/table 2-33, printed
page 44: `GPIO_47` selects **Force DnX FW Load**, described as recovery for
corrupted firmware; `GPIO_39` selects **CSE ROM bypass** to patch space;
`GPIO_44` allows SPI as a boot source. Straps are normally sampled about
95 ms after `RSM_RST_N` deassertion, with RTC-dependent qualifications.
These are Intel GPIO numbers, not connector pin numbers or established
Linux GPIO offsets. The manual is E3900-family reference material; A3960
applicability and this board's routing/strapping must be verified before
any experiment. No evidence yet connects these straps to VIP outputs.

Neither strap is documented here as an authentication-disable switch.
The Apollo Lake Signing and Manifesting Guide section 7.2 specifies that
DnX checks platform/OEM identifiers and requires a signed image when the
corresponding fused signed-image configuration applies. It identifies the
OEM Key Manifest signing key for DnX signing. Thus forced DnX is a possible
independent recovery lead, not proof of arbitrary image acceptance, ELK
entry, or recovery availability on this radio. No pins were manipulated.

Renesas `RH850 Code Flash Library` section 4.4.15 documents
`R_FCL_CMD_GET_READ_PROTECT_FLAG` (one means set, zero clear). This is an
on-MCU library operation, not a UART wire command. The F1K/F1KM/F1KH Flash
Memory Hardware Interface manual section 6.3.17 explains configuration-area
access using `BFASELR` from on-chip RAM; section 7.1 describes ID-gated
FACI operations. These supply useful targets when identifying existing VIP
firmware handlers, but do not establish that Probe's IPC UART exposes them
or determine this VIP's current protection state. No flash configuration,
protection flags or ID settings were changed.

The Bosch FCC document is for VCURH1 with Qualcomm 8195/8155, RH850F1KM/KH,
and QNX/Blackberry virtualization. It is not a description of this Intel/GHS
radio and cannot establish its reset wiring or key policy. The new references
do not establish a usable signing key or resolve the pre-RBE transition writer.

#### Live Apollo Lake fuse/status check — 2026-11-17

Read-only measurements from the running Probe provide hardware-status evidence
beyond the static image and inherited kernel command line:

| Register/query | Raw result | Interpretation using Apollo Lake definitions |
|---|---|---|
| HECI PCI FWSTS1, offset `0x40` | `0x80000245` | Manufacturing-mode bit 4 clear; firmware-init-complete bit 9 set |
| FWSTS2, `0x48` | `0x80100000` | Raw retained; not decoded as a desktop ME register |
| FWSTS3, `0x60` | `0x30370608` | IBB verification result bit 9 = 1; verification done bit 10 = 1 |
| FWSTS4, `0x64` | `0x00080000` | Coreboot's TXE verified-boot-valid/test bits 14/15 both clear; do not substitute this for an established rejection profile |
| FWSTS5, `0x68` | `0x00000000` | Reported error-status field zero |
| FWSTS6, `0x6C` | `0x40000000` | FPF committed bit 30 = 1 |
| MCA READ_FILE, hardware `/fpf/intel/SocCfgLock` | `0A 82 00 00 01 00 00 00 01` | Successful one-byte hardware-fuse result **1**; independently confirms committed/locked SoC fuse configuration |
| MSR `0x13A` | `pread MSR 0x13A: Input/output error` | No usable MSR value; neither zero nor a disabled profile |

Sources: coreboot's [Apollo Lake CSE implementation](https://github.com/coreboot/coreboot/blob/main/src/soc/intel/apollolake/cse.c),
[platform register fields](https://github.com/coreboot/coreboot/blob/main/src/soc/intel/apollolake/include/soc/cse.h),
and [common register offsets](https://github.com/coreboot/coreboot/blob/main/src/soc/intel/common/block/include/intelblocks/cse.h).
The fuse query used MKHI group `0x0A`, command `0x02`, offset 0, size 1,
flags `0x08` (hardware source), through the existing MKHI MEI client. It did
not invoke any fuse-programming, flash, boot-selection or reset operation.

The standard `msr.c` from the exact 4.19.283 Probe08 tree built as `msr.ko`
with the matching Android clang r416183b1 toolchain and existing module-symbol
versions; it loaded without disabling `CONFIG_MODVERSIONS`. A static reader
opened `/dev/cpu/0/msr` read-only and used an eight-byte `pread` at `0x13A`.
The first reader build failed with
`cc1: fatal error: /work/msr-audit/read-msr.c: Permission denied` because the
container invocation omitted the established label setting; rebuilding with
the existing `--security-opt label=disable` setup succeeded.

**What is now definitive:** platform fuse configuration is committed/locked,
and TXE reports IBB verification completed successfully. **What is not:** the
complete contents of individual security fuses, an exact desktop-style Boot
Guard profile number, or a negative boot test of a modified IFWI. Committed
fuses are not themselves proof that SPI writes are blocked. Authentication
of modified contents and permission to program the chip are distinct controls.
The earlier suggestion that MSR `0x13A` alone would unambiguously settle this
Apollo Lake/TXE platform, or that a SPI dump contains the physical FPF fuses,
is withdrawn.

**eMMC staging placement verified from the backup GPT:** partition 1
`ghs_isys_a` starts at `0x00100000` (64 MiB); partition 2 `ghs_isys_b` at
`0x04100000` (64 MiB); partition 3 `ghs_storage` at `0x08100000` (16 MiB);
partition 4 `ghs_abl_update` at `0x09100000` (8 MiB). IBBL/IBB/ELK copies in
partition 4 are update-staging components, not separate GPT entries or
pre-partition boot blocks. The observed early loader copies ELK from SPI.

The earlier Probe08 used `CONFIG_MODVERSIONS=y`, `CONFIG_MODULE_SIG=y`, and
`CONFIG_MODULE_SIG_FORCE` disabled; its working MSR module demonstrated that
matching modules can be added without relaxing version checks. Subsequent
upstream Probe builds, including the current 7.3.5 stable02, actually use
`CONFIG_MODVERSIONS=n` and `CONFIG_MODULE_SIG=n`. This is a build-time choice,
not a runtime toggle or change to IFWI authentication. Do not reuse old kernel
modules merely because symbol-version checking is disabled.

For the standard SACM layout, measured/verified boot are bits 5/6 of MSR
`0x13A`, not bits 2/3 (TPM type occupies bits 2:1; bit 3 is TPM success).
[Coreboot's decoder](https://github.com/coreboot/coreboot/blob/main/src/security/intel/cbnt/logging.c)
provides that layout. It does not produce a usable value for this radio's failed
MSR read or establish applicability of a desktop profile decoder to Apollo Lake.

### Meaning of ELK secure=no — mapped-firmware trace, 2026-11-17

The mapped firmware's ELK ELF matches the staged ELF byte for byte (SHA-256
`3acbf174207a2c621d24ba5a1278c3b214b11c88e580228599057b4ad3a8951c`).
The following addresses are x86 ELF virtual addresses, not VIP offsets.

- `0x12805B90` publishes `secure` using predicate `0x128A79F0` and
  `unlocked` using `0x128A79C0`.
- Both predicates call device-state getter `0x128A7550`: `secure` is true
  for state **0**, and `unlocked` is true for state **1**. Consequently these
  responses describe ELK lock state, not a direct measurement of Intel ROM,
  TXE authentication, fuses, or early-firmware signature enforcement.
- The getter caches its result at `0x12902A44` and reads through `0x128B5900`.
  **Corrected 2026-11-17:** the `OEMLock` diagnostic string does not identify an
  EFI-variable backend in this Y175 executable. The callback resolves to physical
  RPMB or an emulated record in `teedata`, as traced below. Missing-record fallback
  can report unlocked without a persisted unlocked byte. Do not attribute the
  observed state to the earlier timed-out unlock attempt.
- The fastboot command record at `0x12902030` points to downloaded-image boot
  handler `0x128044C0`. That handler copies the download into a buffer and
  schedules boot. In main `0x12800690`, the returned image proceeds to loader
  `0x1289FB70` only when `0x128A79C0` reports unlocked. This path also calls
  EFI CalculateCrc32; CRC32 is not cryptographic signature authentication.
  The loader checks Android image format and prepares execution; its complete
  transitive call graph has not yet been audited for every security check.
- Separate function `0x128B4E20` writes a `SecureBoot` firmware variable from
  parsed ABL boot arguments. This is distinct from the lock-state predicate
  behind fastboot `secure`.

#### Y175 ELK lock state and eligibility — callback trace, 2026-11-17

Target: x86 little-endian 32-bit ELF, image base `0x12800000`, SHA-256
`3acbf174207a2c621d24ba5a1278c3b214b11c88e580228599057b4ad3a8951c`.
These addresses apply to Y175; the older Y181B addresses in §2.3.2 are not
interchangeable. This pass used headless Ghidra and checked critical assembly.

- Publication at `0x12805B90` and registration at `0x12805D90` use
  `0x128A79C0` (state equals 1: unlocked) and `0x128A79F0` (state equals 0:
  secure). Both call cached getter `0x128A7550`; neither reads IBB enforcement
  fuses. Separately, `secureboot` uses `0x128B4C90` to read `SecureBoot`, whose
  writer `0x128B4E20` consumes ABL arguments. These names are not synonyms.
- Getter `0x128A7550` calls `0x128B5900`, which dispatches through
  `0x12E0413C`. Initializer `0x128B5C30` selects the backend. Its
  `0x128AB670` predicate is compiled false. A true virtual-media predicate
  (`0x128AB680`) or true `0x128B4D40` selects physical-RPMB initialization.
  The latter requires a successful lifecycle query reporting value 1 and
  `SecureBoot == 1`. Successful initialization selects reader `0x128B6050`;
  EFI_NOT_FOUND falls back to emulation; other initialization errors return.
  Otherwise emulation reader `0x128B6700` is selected directly.
- Physical reader `0x128B6050` reads one RPMB block at address 2 (or `0x82`
  for virtual media), through `0x128B7260` and the selected RPMB operations.
  Emulated reader `0x128B6700` reads 256 bytes at `teedata + 0x200`
  (or `+0x8200` for virtual media), through `0x128B6EE0` and the disk-I/O
  helper `0x128B6C30`. Assembly confirms the register-passed offset and read
  flag; a default decompiler prototype omits them. Both expect marker `0xDC`
  followed by the state byte. Missing marker returns EFI_NOT_FOUND; success
  supplies the byte whose bit 0 becomes the cached state.
- On EFI_NOT_FOUND and non-virtual media, the getter initially selects locked,
  then calls lifecycle helper `0x128AF830`. **This Y175 caller tests its return
  status, not its output lifecycle boolean:** success or EFI_NOT_FOUND sets
  provisioning flag `0x12A0D098 = 1` and cached state 1. Other errors leave
  locked. Therefore the older shorthand “non-ENDUSER only” must not be applied
  to this Y175 branch. Instruction range `0x128A75B2–0x128A75C9` confirms it.
- `flashing get_unlock_ability` handler `0x12805FB0` calls `0x12806030`.
  Provisioning accessor `0x128A7A20` short-circuits to allowed (result 0).
  The next class predicate `0x128A6640` is compiled false in this image.
  Otherwise it locates `persistent` and reads its final byte: exactly 1 allows,
  another value or read failure denies (result 1); lookup failure allows.
  Result 2 is the class-refusal branch, unreachable through that constant-false
  predicate. The handler prints the eligibility text and completes with OKAY.
- Y175 unlock handler `0x12805F10` returns immediately if already unlocked and
  not provisioning. Otherwise it checks eligibility; a refusal prints
  `Unlocking anyway since this is not a User build` and still calls
  `0x12805C10(1,1)`. This differs from the older Y181 refusal trace.
  The transition may erase userdata when not provisioning, then calls setter
  `0x128A7640` → `0x128B58D0` → callback `0x12E04138`.
  Physical writer `0x128B5F50` or emulated writer `0x128B6640` writes marker
  `0xDC` and the state byte; the cache changes after reported success.
  This is a genuine state-write path, not evidence it was exercised successfully.

Read-only backup cross-check: the saved Y175 eMMC user image has final
`persistent` byte `00` and marker/state bytes `00 00` at both `teedata + 0x200`
and `+0x8200`. These are not valid emulated state records. Together with the
previous live unlocked/eligible reports, this is consistent with provisioning
fallback, but does not identify the backend selected during that live ELK boot.
A runtime callback/lifecycle observation or equivalent boot trace is still needed
for that attribution. No lock command, userdata erase, RPMB write, or radio
parameter change was performed in this pass. ELK state does not establish that
GHS or IBB uses the same state or permits unsigned normal-storage boot.

The live dump contains `$MN2` manifest headers at `0x28C070` (IBBP),
`0x220130` (FTPR), and `0x30B688` (NFTP), plus `BPM.met` in IBBP. These
establish authentication-related structures, **not** whether this unit's
ROM/CSE enforcement policy requires them. Probe's demonstrated RAM boot and
ELK's unlocked predicate support permissive downloaded-image execution; they
do not establish permissive replacement of IBBL, IBB, TXE, or ELK itself.
No flash changes, lock changes, or corrupted-firmware boot tests were used.

Automated triage reported `error:decompress` for a putative LZ4 region and
extracted zero files there. Its zero security findings therefore are not
negative evidence; the conclusions above use the manually validated ELF and
CPD/manifest offsets instead.

**ELK → AAOS → ELK round trip,2026-11-17:** Raw USB `reboot` returned OKAY.
UART recorded renewed boot-reason/calibration exchanges and evHMIReady; the
owner observed the AAOS home screen. CAN F181 retained the expected software
identification and F0F1/F0F2 both returned0000. After manually toggling USB
debugging, ADB reconnected with a new Android boot identity; the radio clock was
resynchronized from the Mac before interpreting boot state.

| AAOS property/setting after ELK reboot | Value |
|---|---|
| sys.boot_completed | 1 |
| ro.boot.verifiedbootstate | green |
| ro.boot.flash.locked | 1 |
| ro.boot.vbmeta.device_state | locked |
| sys.oem_unlock_allowed | 0 |
| ro.boot.slot_suffix | _a |
| ro.crypto.state | encrypted |
| device_provisioned / current-user user_setup_complete | 1 / 1 |

The same CAN F000/8180 entry then returned7101F000818003, with UART ELK
response0 and controlled reset. The temporary application-security word was
again restored and verified. Three raw USB version queries succeeded in about7ms;
subsequent reads again reported unlocked=yes, secure=no, is-userspace=no and
positive unlock eligibility. Thus ELK's reported state survives this AAOS round
trip, while normal AAOS reports locked/green. A cold-power-cycle persistence
test and attribution of that state to any prior unlock attempt remain open.

The owner's earlier silent userdata-erase command remains unverified: there
is no captured erase completion, no pre/post data-content comparison, and the
home screen plus provisioned/setup-complete flags do not establish a wipe.
No additional erase or unlock was issued during the round trip. Final mode was
ELK with working raw USB access and CAN harness/UART observation active.

USB detection caveat: a VID/PID-only watcher initially failed to claim interface0
with `[Errno 13] Access denied (insufficient permissions)` before ELK transition.
Requiring interface class/subclass/protocol FF/42/03 before claiming resolved
that test's detection issue. Product ID alone must not be used as mode proof.

**Security-state interpretation,2026-11-17:** ELK's unlocked=yes and normal
AAOS's locked/green properties are observations of different boot paths, not
proof of one global SoC unlock state. Android receives verified-boot state from
its loader through command-line/bootconfig inputs; the normal GHS guest-launch
analysis includes AVB verification and construction of those inputs. The later
custom RAM boot also received `androidboot.verifiedbootstate=green`; therefore
that command-line string alone does not establish authentication of a downloaded
RAM image. This does not demonstrate that normal GHS verification is disabled.
Upstream [Kernelflinger fastboot_init](https://github.com/intel/kernelflinger/blob/master/libfastboot/fastboot.c)
publishes secure=no as a fixed string, so that variable must not be treated as
an Intel hardware-fuse or platform secure-boot measurement. This source behavior
still requires matching to the GM binary before attributing its exact origin.
The later probe02/probe03 tests below confirmed custom Linux execution through
ELK's boot/download path. The complete platform verification boundary and GHS
residency during ELK itself remain unproven. is-userspace=no distinguishes
ELK from Android fastbootd; it does not prove absence of a hypervisor.

**Custom RAM-boot probe,2026-11-17:** Built an unsigned Android boot image
from the mounted Y175 stock kernel and second-stage payload, replacing only
ramdisk prop.default and system/etc/init/hw/init.rc. The probe init configuration
has only ueventd/adbd services, no vendor imports, no recovery updater and no
block-device mount actions. Its marker is ELK_RAM_PROBE_01 (USB product and
sys.elk_ram_probe), with temporary debug properties and permissive SELinux
command-line requests confined to the downloaded image. Whether the stock
user-build binaries honor those requests is not established.

The stock module85759602 has boot-header version2 and dtb_size0. The probe
preserved that x86/ACPI layout, using a locally adjusted AOSP builder that allows
the stock zero-DTB case. Output size39100416, SHA256
`7ee5e8b18b16f9fd9e367abb535381d6c38174a77ab268058f1b44ae8b300fa7`.
The repacked433-entry CPIO changed only the two named entries.

Live raw USB returned unlocked=yes and max-download-size0x08000000.
`download:0254a000` returned `DATA0254A000`. The host initially rejected the
uppercase hexadecimal spelling before sending image bytes; numeric comparison
was corrected and the already-accepted transfer was completed without another
download header. All39100416 bytes transferred in approximately1.2 seconds,
followed by OKAY. The subsequent `boot` command also returned OKAY.

ELK USB then disappeared. During a90-second observation window, no probe USB
identity or ADB device appeared; the display remained black and VIP UART supplied
no custom-kernel execution evidence. CAN traffic continued. This proves RAM
download and boot-command acceptance, **not successful unsigned code execution,
hypervisor absence or disabled platform verification**. A loader rejection after
acknowledgment, image incompatibility, or a running but unobservable kernel are
not distinguished. In particular, the stock kernel may depend on its normal
GHS-provided boot environment. No flash, erase or partition-selection command
was issued. A mute-hold restart was requested after the observation window.
UART recorded Shutdown Timeout before the eventual new boot, HMIReady and
SystemState Run. The owner observed the AAOS home screen; CAN F181 matched
the expected software identification and F0F1/F0F2 were0000. Stock AAOS recovery
is therefore confirmed; that first probe's execution remains unverified.
The CAN harness and receive-only UART observer remained active, apart from
short controller replacement gaps before the accepted test. Earlier statements
that no RAM write was performed describe the preceding feasibility tests only.

**Direct-Linux compatibility inventory, 2026-11-17:** Live Y175 ADB reported
Linux 4.19.283 on x86_64. The graphics device exposed to Android is PCI
8086:5a84, bound to i915. HDMI-A-1 is connected at 2400x960; fb0 is
inteldrmfb with 32-bit pixels and a 9600-byte stride. The DWC3 device
controller is at PCI 00:15.1, with xHCI at 00:15.0 and an Intel USB-role
switch. These are guest-visible observations, not proof of the physical
device ownership or state available after an ELK handoff.

The running configuration enables ACPI, i915, USB configfs/ACM and Intel
USB-role switching, but DWC3/xHCI are modules and framebuffer console is
disabled. It also enables GHS paravirtual support. Firmware recovery init
explicitly loads `ti949_serdes.ko` and starts `recovery_panel`; the latter
references I2C bus 7. GHS independently has a DisplayI2C task. Thus an
active Android framebuffer does not establish that a generic Linux kernel
can initialize the serializer and panel without prior vendor setup.

The stock bzImage reports xloadflags 0x3 and handover_offset 0. Those fields
do **not** by themselves explain the failed observation: the inspected
[Apollo Kernelflinger source](https://github.com/projectceladon/kernelflinger/blob/celadon/s/mr0/apollo/libkernelflinger/android.c)
exits boot services and jumps to the protected-mode kernel entry. That
source path is a reference and still requires matching to the GM binary.
After stock recovery, ADB reported boot_completed=1 and its clock matched
the host. Retained kernel evidence was unavailable: `/sys/fs/pstore`
returned `Permission denied`, and `/proc/last_kmsg` did not exist.

A second, RAM-only Linux probe was built with built-in ACPI, i915,
framebuffer console, Intel I2C/pin control, DWC3/xHCI and USB ACM. Its
minimal static PID1 paints color bars and configures a USB serial gadget;
it has no storage mounts or updater. The source is an existing Intel-derived
4.19.283 tree with prior emulator patches, not an exact GM kernel source
release. The emulator-only GM_SIGNATURE stub was disabled. Source HEAD:
`0649a57484345a97884f010e93a159f4c1a1aec0` (local Intel-derived history).
The kernel has EFI/mixed-mode support, xloadflags 0xf, and no GHS-specific
driver configuration. The native workstation build encountered removed
OpenSSL ENGINE symbols; the established builder completed the kernel.

QEMU TCG reached the static PID1 and a 1024x768, 32-bit framebuffer. A
captured image contained red, green and blue sample pixels (255,0,0),
(0,255,0), (0,0,255). USB ACM configfs setup also completed. KVM on the
test workstation exited before kernel output with both the probe and an
older control kernel; that host-specific result was not treated as a
radio/kernel compatibility verdict. QEMU exposed no physical DWC3 device.

Final probe02 artifacts:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| bzImage | 12477248 | `d63314a50da64d60335d0b4e32a5360c624c686da3aaef8c9487f5178d9a3212` |
| initramfs.cpio.gz | 386942 | `a1fb4477a85c39bcc38f20b41113e3a0034b76a6baf7ec484dacdf58b89a6875` |
| Android-format RAM boot image | 12875776 | `d6c78cded24f150f8a92bf05dccff5b2ce91fd0bb2a5cd282172e18f767c16b6` |

**Live unsigned Linux execution confirmed, 2026-11-17:** The established
CAN ELK route returned 7101F000818003 and restored the temporary VIP RAM
word. The Fastboot interface appeared. Raw USB returned
`download:00c47800` -> `DATA00C47800` -> `OKAY`, followed by `boot` -> `OKAY`.
About 65 seconds after the USB observer started, a new 1d6b:0104 device
appeared with product `ELK_LINUX_PROBE_02` and CDC ACM interfaces. Its USB
serial output identified kernel `4.19.283-elk-linux-probe+`, x86_64,
`USB=dwc3.0.auto bound=1`, and increasing PID1 uptime. This proves execution
of the custom kernel/initramfs and functioning USB device mode, beyond
merely accepting a Fastboot command. It does not establish arbitrary
partition-write capability or the state of every platform trust boundary.

The physical display remained black. Linux reported `framebuffer=none
draws=0`; display initialization, rather than absence of kernel execution,
is the remaining visual-output failure. The kernel enumerated ACPI MCFG,
APIC, TPM2, NHLT, DSDT, PSDS, DMAR, FACP, HPET and FACS. VIP UART recorded
Hypervisor Startup Timeout (ignored for MEC249) and later SoC Startup
Timeout while the custom Linux USB interface continued operating. These
observations are consistent with bypassing the normal GHS/AAOS startup,
but are not by themselves proof of the absence of every hypervisor layer.
No partition was flashed or mounted by the probe. Native MMC/SDHCI drivers
are compiled in; eMMC discovery/readback was not yet demonstrated by this
initial probe. Its nonblocking USB log write truncated long kernel output,
so missing display/storage lines in that output are not negative evidence.

**Probe03: shell, NCM and raw eMMC access, 2026-11-17:** The same kernel was
repacked with BusyBox 1.37.0, Dropbear 2025.88 and their required runtime
libraries. The USB gadget exposes CDC-ACM plus CDC-NCM. An owner-authorized
public key, with its identifying comment removed, is included for SSH;
private client keys are not included. Password login is disabled and server
host keys are generated only in the RAM filesystem. QEMU validated shell
entry/exit, SHA256 on known input, block size against a read-only fixture,
NCM configfs setup, SSH-server startup and framebuffer drawing.

Probe03 boot image: 14336000 bytes, SHA256
`563b9543cb1fa211c7a4c8eaf6f35f84a22661543d923e01b466a53fbfcc3925`.
Its initramfs is 1846555 bytes, SHA256
`b1a38b6f17cf98975c92ba74f9dffb6e452de7d6cd95c3b689876cb9c7fadbbc`.
An initial re-entry attempt acknowledged the CAN request but returned to
AAOS without a confirmed ELK USB interface. After UART HMIReady/Run, the
same route entered ELK. Download `00dac000` and boot returned OKAY; the
new Linux shell and NCM interfaces subsequently appeared. A prior Linux
`reboot` command had also successfully returned to stock AAOS.

The live shell reports native SDHCI at PCI 00:1c.0 (8086:5acc), HS400 MMC,
and the following raw devices:

| Region | Linux interface | Exact bytes | Observed state |
|---|---|---:|---|
| User area | `/dev/mmcblk1` | 63996690432 | 26 partitions; set read-only before imaging |
| Boot0 | `/dev/mmcblk1boot0` | 33423360 | Read-only; full copy/source hash verified |
| Boot1 | `/dev/mmcblk1boot1` | 33423360 | Read-only; full copy/source hash verified |
| RPMB | `/dev/mmcblk1rpmb` | Kernel reports 4 MiB | Character device; separate authenticated protocol, not part of the above images |

Only rootfs/devtmpfs/proc/sysfs/tmpfs/configfs are mounted. A raw first-1024-byte
read succeeded. SSH public-key authentication over NCM then succeeded after
explicitly binding the host connection to its USB source address. The link
reports USB high-speed. A 64 MiB streamed sample transferred at 31.19 MiB/s
and matched an independently reread source SHA256. This validates read access
and the transport, not flash writes.

The initial USB user-area read stopped after 14997700077 bytes (23.44%).
A fresh Wi-Fi read subsequently completed all 63996690432 bytes, offsets 0
through 63996690431, without skipping partitions, gaps or unused space. Its
stream hash, local file reread hash and independent source-device SHA256 all
matched `e630b3cbb0b76f8f721e83956555cb84270046998ef4859e85c21ec55216cd86`.
The final image is `emmc_user_wifi.bin`; transfer duration was 2150.6 seconds.
Fresh boot0/boot1 Wi-Fi copies also passed verification. After this success,
the old 14997700077-byte `emmc_user.bin.partial` was deleted as requested. The imaging
tool checks expected capacity and read-only state, rejects short/overlong
streams, rereads the stored file for SHA256, independently hashes the source,
and only then promotes a `.partial` image to its final name. Boot0 and boot1
already passed those checks and both hash to
`f9c8b35f7002924d7b5cf21abbf0031d34404a5670717749403ec4b31bf17d16`.
User-area verification was performed independently of the boot-region results.
RPMB is not included in ordinary raw block images.

The host SSH client reported `Operation timed out` and `Broken pipe`; the
radio server reported `Error reading: Connection reset by peer`. Linux uptime
continued and a subsequent SSH connection succeeded. No USB disconnect, MMC
error, or kernel failure appeared in the available kernel log; both ends
reported zero interface errors/drops, and the host sleep log showed no sleep
during the transfer. These observations narrow the failure to the connection
but do not establish its trigger. Packet capture is needed on a repeat test.

After all ordinary regions passed verification, native mmc-utils read EXT_CSD
and confirmed a 4194304-byte RPMB region; `rpmb read-counter` returned zero.
The first data request (`rpmb read-block`, address 0, count 256) exceeded the
30-second client timeout. Subsequent SSH connection attempts, serial-shell
completion, and USB GET_STATUS control requests also timed out. This is
consistent with a radio/kernel stall following the request, but the precise
cause is unproven. No RPMB data was successfully acquired, and no key-programming
or data-write operation was issued. CAN control remained responsive. Recovery
was initiated only after the full eMMC images had passed hash verification.
The prepared readback plan compares two independent RPMB reads and a stored-file
hash; it cannot establish MAC authenticity without the RPMB authentication key.

A subsequent native T1 test loaded a matching standard `igb` module for PCI
`8086:157c`, established VLAN-5 IP/SSH connectivity, and read a hash-matching
64 MiB eMMC sample at 3.98 MiB/s. See [elk_recovery.md](../../platform/elk_recovery.md#32-t1-ethernet-test-procedure-and-results) (`platform/networking.md` was retired in the platform/ reorg; this result now lives there).
This proves an alternate readback path, not improved long-duration reliability.

The complete graphics log shows i915 bound successfully but both native
HDMI connectors are disconnected and the driver reports `Cannot find any
crtc or sizes`. Its DMC firmware request also failed before userspace and
timed out around 62 seconds, explaining a substantial boot delay. Presence
of the firmware file in the initramfs did not prove it was available at the
driver's request time. Display repair remains separate from the confirmed
USB, shell and native storage access. No display-driver reset is attempted
during the active eMMC transfer.

Intel source/image availability and the limits of crashmode partition
readback are tracked in [the Celadon reference](GORDON_PEAK_CELADON_INTELLIGENCE.md).

**Native x86 build reproduction (2026-11-17):** A native x86_64 workstation
with 24 physical cores / 48 threads and 235 GiB RAM rebuilt the kernel from
source, recreated the external initramfs from the same prebuilt payload
binaries, and packaged the Android boot image locally. All three outputs
passed byte-for-byte comparison against probe03, including final boot image
SHA256 `563b9543cb1fa211c7a4c8eaf6f35f84a22661543d923e01b466a53fbfcc3925`.
PID1, BusyBox, Dropbear and their libraries were retained as identical archive
inputs; this does not claim a source rebuild of those user-space dependencies.

The host OpenSSL 4.0.3 lacked ENGINE symbols required by the old kernel host
tools. A native Ubuntu 22.04 Podman userspace with OpenSSL 3 and the matching
AOSP Clang 12 toolchain resolved that build-environment incompatibility;
compilation ran on physical x86 CPUs, not under CPU emulation. The source
configuration extracted from the reference image disables `GM_SIGNATURE`;
an earlier saved configuration still enabled it. Reproducibility also required
matching build version 3, timestamp `Tue Nov 17 03:44:33 AKST 2026`, kernel
release suffix `+`, build paths, and the public build certificate. No signing
private key was copied. The final 35-byte decompressed-kernel difference was
20 build-ID bytes plus 15 bytes of fallback-initramfs timestamp text. Regenerating
the three-entry built-in archive with epoch `0x6AC743B8` removed that difference.
External archive reproduction required explicit gzip level 6 and preserving
mode 0700 for the four library symlinks that had that metadata on the original
packaging host. The final images were compared directly with `cmp`.

Local QEMU validation of the native output passed PID1 startup, framebuffer
rendering, BusyBox shell entry/exit, SHA256 operation, read-only block capacity,
USB ACM/NCM configuration, and SSH-server startup. This QEMU test does not prove
physical radio display initialization. The native build workspace and launcher
were saved on the build workstation's internal storage; the running radio and
its concurrent eMMC transfer were not rebooted or replaced.

**Upstream-kernel Probe build and physical RAM boot (2026-11-17):**
A separate build now uses the unmodified kernel.org Linux 4.19.283 source
archive, rather than the existing GM/Android kernel tree. Archive SHA-256
`047316d20c6c97ad41c40477c7e1ab0bea434243e17bfc72155801b123cc51f4`
matched the published kernel.org checksum. Matching the previous kernel version
isolates source-tree differences from a simultaneous version upgrade.

Build scripts and isolated outputs reside under `$BUILD_ROOT/upstream/` on the
native build workstation: `build.sh`, `build-inside.sh`, `package.py`,
`qemu-check.py`, and `artifacts/`. The existing Probe08 build remains separate.
The build used the existing Android Clang 12 toolchain, freshly compiled
BusyBox 1.37.0, and our panel/VIP/ELK-selection helpers. Other open-source
userspace binaries were retained from the earlier runtime. This is not a claim
of a wholly source-rebuilt userspace or a blob-free image: peripheral firmware
and panel EDID remain included. No stock Android second-stage payload is
included in this image.

Configuration adaptations include `CONFIG_MODVERSIONS=n`, built-in MSR, igb,
MEI and touch support, i915 plus panel EDID/DMC firmware, USB ACM/NCM gadget,
and the existing framebuffer-console command line. No kernel-source patch
was needed for the functionality verified below. BusyBox initially rejected
its previously built shared source directory; cleaning an isolated copy fixed
that build failure without changing the old build tree.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| bzImage | 12,092,224 | `995e9b5be4d15b2042277980cbf7a68b4830ae5cdcaf5bc87708292ee8e311bb` |
| initramfs.cpio.gz | 12,167,829 | `eb3c60c6e189e211ad8f814e8e0501e118b803a83e4624e851ce4ba2d45e8637` |
| boot.img | 24,264,704 | `23537a570fc7ef9a6179986c182558a3367406521bf8db0a896840efa8bcded5` |

QEMU passed PID1, shell, framebuffer-console text readback, PTY, SHA-256,
read-only block capacity, USB gadget configuration, SSH-server startup, and
VIP/ELK helper self-tests. Physical testing then selected ELK from running
Probe08 through the existing MEI helper; CSE returned `20870000`. ELK USB
enumerated, accepted the complete image download, and returned `OKAY` to boot.
Actual execution was independently established through USB shell and then T1
SSH: both reported `4.19.283-upstream-probe01`.

Physical results: i915 created `inteldrmfb` at 2400×960, HDMI-A-1 reported
`enabled`, the DWC3 USB console worked, `/dev/mei0` and `/dev/cpu/0/msr` existed,
and igb bound to the T1 interface. Framebuffer/connector state does not alone
prove visible panel output; no new visual confirmation was obtained in this
check. T1 VLAN 5 SSH was configured in RAM and a key-authenticated login returned
UID 0. Account/network configuration and SSH keys were not inherited into the
new archive; the public access key and SSH host key were installed/generated
in RAM after boot. Use the bench's current endpoints and key path rather than
persisting them in documentation.

The eMMC enumerated as **`mmcblk1`**, unlike the earlier image; never assume its
old device number. Its capacity was 124,993,536 sectors. A read-only first-1-MiB
sample matched the saved eMMC dump SHA-256
`a7bb8942da7132004c16be976d1eba32cca385f05f7a4dc628a41d38429b7d35`.
No eMMC partition was mounted and no eMMC/SPI write was issued. This establishes
an upstream-kernel RAM boot with storage access, not autonomous eMMC boot,
full hardware parity, or disabled firmware signature enforcement.

**Linux 7.3.5 stable build and radio test (2026-11-17):**
The next image uses kernel.org Linux 7.3.5, archive SHA-256
`8f293f83d54f0b7b9be56863ebc5e4ea79d73e530b4ae55c572be97ef39f0990`,
checked against the published checksum. Built with native GCC 16.2.1 for
`-march=x86-64 -mtune=generic`; the old Clang 12 does not meet this source's
Clang 17 minimum. Outputs are isolated under `$BUILD_ROOT/stable735/`.
All 34 required built-in configuration checks passed, including i915/fbdev,
GPIO character-device support, DesignWare I2C, LPSS UART, MEI, eMMC, igb/VLAN,
DWC3 ACM/NCM, maXTouch, and brcmfmac PCIe. Kernel compression was changed to gzip
after the host reported `lz4: command not found`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| bzImage | 18,031,616 | `fa86e358a31a0a817f0877c2ba9076e3f490c708b7367fe40d0c713187a7743a` |
| initramfs.cpio.gz | 12,168,095 | `7b91e98635a5b21e55f88fb722d3b901584c112d40faa7e6213d10e983536f1f` |
| boot.img | 30,203,904 | `34a92caf9eea8cc488531d47ecbca9f0b5fddf3eefbca663d5ae96ab14c220d6` |

QEMU booted this kernel and passed shell, PTY, framebuffer console text readback,
read-only block size/hash, SSH-server, gadget-configuration, and helper self-test
checks. The overall test nevertheless exited 1 because its final condition
required 1024×768 while this version selected 1280×800. A QEMU screenshot showed
Linux penguins and kernel text. QEMU also exposed missing `regulatory.db`.
Neither issue was fixed in the packaged image before builder work stopped.

A subsequently authorized physical test used the exact saved image above,
without modifying the shared builder. Running upstream Probe selected ELK via
MEI; CSE acknowledged `20870000`, and ELK accepted download and boot with `OKAY`.
USB shell and T1 SSH independently reported `7.3.5-probe-stable01`; root SSH
was restored with volatile VLAN/key/listener setup. This proves actual execution,
not merely fastboot acceptance. No eMMC/SPI write was issued.

The original packaged panel helper did not initialize the panel. Two runtime
compatibility corrections were required: use `/sys/bus/i2c/devices/i2c-N`
instead of the absent `/sys/class/i2c-adapter` class; accept the verified
pinctrl identity of reset pin 33 when the GPIO-v2 line-name field is empty.
Bank label `INT3452:00`, 78-line count, and reset-pin identity remain guarded.
The corrected helper was built outside the shared workspace, transferred into
RAM, returned status `CD`, and stays resident to retain GPIO-v2 line ownership.
The owner then confirmed **Display ON**. These corrections are NOT in the
r01 boot image. They were subsequently integrated into stable02 below;
automatic panel startup was subsequently verified on stable02 below.
See the display document for the runtime correction details.

Bounded hardware checks on this boot:

| Subsystem | Observation / limit |
|---|---|
| Display/GPU | 2400×960 `i915drmfb`, HDMI-A-1 enabled, DMC 1.7 loaded, visible output confirmed after runtime helper correction; GPU error state reports none collected |
| USB | ACM shell operational; gadget state `configured`; internal `04d8:00df` interfaces bound to cdc_acm/usbhid |
| T1 | igb bound, carrier present, root SSH working; RX/TX errors and drops all zero at inspection |
| eMMC | `mmcblk2` on PCI `00:1c.0`, 124,993,536 sectors; first-1-MiB SHA-256 matches backup (`a7bb8942da7132004c16be976d1eba32cca385f05f7a4dc628a41d38429b7d35`); no eMMC mounts |
| Other MMC hosts | `00:1b.0` card-detect IRQ request returned `-EPERM`; `mmc1` on `00:1e.0` failed non-removable-card initialization. These are not the working eMMC host; attached-device expectations remain unresolved |
| Wi-Fi | brcmfmac loaded BCM4359 firmware and created `wlan0`/`phy0`; missing `regulatory.db` caused an approximately 60-second request timeout; association/throughput not tested |
| Touch | No maXTouch input device registered; targeted 16-bit-addressed read at bus 10/address 0x4b returned the known valid 16-byte information block with zero errors. Controller reachable; Linux binding/IRQ setup remains unresolved |
| MEI/VIP | `/dev/mei0` exists; no new live VIP protocol exchange or 7.3.5-to-ELK re-entry test was performed |
| Audio/camera | No soundcards or video/media nodes; advertised PCI audio/IPU devices and ACPI decoder entries remain unbound. This is an integration gap, not proof of failed hardware |
| Health | About 30–31°C, ample available RAM, no deferred devices listed. Taint 64 is explained by i915 enable_guc/enable_fbc/enable_psr options; sampled logs contained no Oops/panic trace |

The eDP link-information warning refers to the disabled eDP path; the verified
panel uses HDMI-A-1. This bounded inspection is not a complete stress test or
an assurance that all peripherals operate correctly. The shared build workspace
was left untouched during the physical test and runtime correction.

#### Linux 7.3.5 stable04 — live boot verified 2026-11-17

The latest locally available image, `boot_r04/boot.img`, was RAM-booted after
AAOS readiness was verified (`sys.boot_completed=1`, Android slot `_a`) and
its clock synchronized to the host. CAN profile 0D returned `670E`; the scoped
F000/8180 request returned `7101F000818003`. The temporary application-security
word was restored to its saved zero value and read back. ELK was identified by
USB interface FF/42/03, not VID/PID alone: AAOS also exposed 8087:09EF with
ADB interface FF/42/01 during this round trip.

Image size 30,306,304 bytes; SHA-256
`3cbaee1718c4f368008fd1e735ea367fd787aa4cb906bab0682fb6d647598f38`.
Raw USB download completed in 0.85 seconds; `boot` returned OKAY. USB shell
and subsequent VLAN-5 T1 SSH both returned `7.3.5-probe-stable04`; SSH returned
UID 0. Framebuffer was i915drmfb, 2400×960. T1 addressing, public-key access and
Dropbear listener were configured in RAM. No partition flashing was performed.

The new boot again reports `ABL.status=0x9` and `ABL.secureboot=1`. These are
inherited boot arguments, not a direct CSE-register or surviving IBB-policy
memory measurement in that first round trip. A bounded full captured wake
replay (1,193 frames echoed; 520 radio frames) temporarily recovered CAN replies,
but errors recurred after reducing replay to `0x529`; the display subsequently
went off. This does not establish that `0x529` alone maintains this Probe boot.

After a user-performed power cycle on 2026-11-17, full captured replay was restored.
CAN extended session and profile 0D succeeded, followed by `7101F000818003`;
the temporary VIP word was restored. AAOS readiness was not independently
verified by ADB in this repeat. ELK interface FF/42/03 enumerated, accepted the
same stable04 image, and USB shell confirmed execution. Full replay was retained
through Probe operation. One transmit-echo timeout caused automatic controller
recovery; subsequent samples showed increasing radio RX and no additional errors.

Read-only live host-memory checks, repeated over root T1 SSH, returned byte
`0x01` at `0xC0200`; the containing dword was `0xFEF92001`. Neighboring dwords
`0xC0204` and `0xC020C` were both `0x000055AA`, consistent with reported BPDT
signatures. The tested authentication bit is therefore set in the surviving
memory, consistent with `ABL.status=0x9` and `ABL.secureboot=1`. Establishing that
this location was not repurposed after IBB remains necessary before treating
it as conclusive evidence of the original gate value. These reads do not identify
the RBE hardware-versus-stored-UEP selection or prove mismatch rejection by a
modified storage image. Framebuffer reported 2400×960 with blank state 4;
framebuffer registration alone does not establish visible display output.

The Mac VLAN and Probe VLAN-5 public-key SSH listener were restored using runtime
configuration. T1 SSH verified kernel identity, UID 0, and the same policy byte.
No persistent firmware or partition writes were performed.

#### Linux 7.3.5 stable02 — verified 2026-11-17

After authorization to resume
builder changes, existing edits enabling `CONFIG_DEVMEM=y` and appending
`iomem=relaxed` were preserved. The live-proven panel corrections were integrated
into `stable735/panel.c`; its compiled helper is byte-identical to the temporary
helper that restored physical display output (helper SHA-256
`2eb7f924ffb7f88fd92fe20660b4f94cd055c59eab36d8545e8ae6f9e8432790`).
The kernel/runtime revision is now `7.3.5-probe-stable02`. The original r01
artifacts remain under `stable735/artifacts/r01/`.

The inherited regulatory database failed the new kernel's verification with
`cfg80211: loaded regulatory.db is malformed or signature is missing/invalid`.
Its standalone CMS integrity check succeeded, which did not establish trust by
the kernel's built-in keys. Replaced it only in the stable735 build inputs with
[upstream wireless-regdb 2026.09.03](https://www.kernel.org/pub/software/network/wireless-regdb/wireless-regdb-2026.09.03.tar.xz),
archive SHA-256 `b22e0901227b820cd1c280abe681a15b773a5103a5e10dc442e94ebb34cbf58d`,
verified against the published checksum. Both `regulatory.db` and its `.p7s`
are embedded for early firmware loading and included in the initramfs.
`CFG80211_REQUIRE_SIGNED_REGDB=y` and `CFG80211_USE_KERNEL_REGDB_KEYS=y` remain
set; verification was not disabled. Shared display-firmware inputs were preserved.

| Final stable02 artifact | Bytes | SHA-256 |
|---|---:|---|
| bzImage | 18,035,712 | `2670353aa3bd07b9a9c70cb8135002c9c5a698c007668b0acc1fb5934e8f3ca1` |
| initramfs.cpio.gz | 12,172,221 | `9e8b8c4a39a6afa7371ecf782b8efa0ed289b1c37dac673b36d05dc4dd8dbdbb` |
| boot.img | 30,212,096 | `f9977c166122b86d0839cb253779dba2eb26166938624513d34b966fc886d885` |

The final QEMU test exited 0. It verifies that kernel/ramdisk bytes exactly
match the packaged boot-image payloads, uses that image's actual command line
(including `iomem=relaxed`), checks `/dev/mem` presence and regulatory files,
and rejects observed regulatory verification/load failures. Display verification
now compares actual framebuffer dimensions with the QMP screenshot rather than
requiring the old 1024×768 mode. The measured 1280×800 screenshot visibly showed
Linux logos and kernel messages, including the framebuffer-console test marker.
Shell, PTY, SHA-256, read-only block capacity, USB gadget configuration,
SSH-server startup, and VIP/ELK helper self-tests also passed. GPIO protocol
review confirms that the chip FD and returned line-request FD are independent;
closing the chip FD does not release the held line request.

**Stable02 physical boot verified (2026-11-17):** the exact final image above
was subsequently RAM-booted on the radio. Stable01 successfully selected ELK
through MEI (CSE response `20870000`); ELK accepted the full 30,212,096-byte
download and boot. USB shell and restored T1 root SSH independently reported
`7.3.5-probe-stable02`.

The packaged panel helper started automatically, remained resident, and held
GPIO-v2 line 33 high as `probe-panel-reset`. No temporary helper or manual link
initialization was needed. The i915 framebuffer is 2400×960, HDMI-A-1 is enabled,
and a read-only serializer status read returned `0xCD`. The owner confirmed the display is active on this stable02 boot.

`/dev/mem` and `/dev/mei0` exist. The missing/invalid regulatory-database messages
did not recur. eMMC enumerated as `mmcblk1` on PCI `00:1c.0` this time, with
124,993,536 sectors; its read-only first-1-MiB hash again matched the saved dump.
No eMMC partition was mounted and no eMMC/SPI write was performed. Enumeration
order changed from stable01: locate storage by physical device, not a remembered
`mmcblkN` number. T1 SSH remains active with volatile setup. Wi-Fi also created `wlan0`; BCM4359
firmware initialization completed around 62.9 seconds. Thus a separate Wi-Fi
firmware-startup delay remains despite the corrected regulatory database.

Touch device/IRQ binding, auxiliary MMC errors, audio/camera integration, and
Wi-Fi association remain open. No speculative fix for those was included.
This build enables physical-memory diagnostics; checks establish node presence,
not arbitrary hardware memory access or signature-policy changes.

**CAN-only ELK re-entry after backup (2026-11-17):** After recovery to AAOS
Run state, profile 0x0D security access succeeded. With the application-security
RAM word still zero, `31 01 F0 00 81 80 03` returned `7F 31 33`. Repeating
with the previously traced temporary application-security value 1 returned
`71 01 F0 00 81 80 03`; the original zero value was immediately restored and
read back. Intel USB `8087:09ef`, interface `FF/42/03`, then enumerated,
confirming actual ELK entry. Security access, the temporary RAM write, and the
routine request all used CAN. USB provided independent observation; T1 and ADB
were not used for this entry. No new image was booted as part of this check.

**Display probe04 preparation and hardware result (2026-11-17):**
Native analysis of stock `recovery_panel` shows `get_globalB()` opening
`/dev/i2c-7`; `panelB_init()` issues I2C_RDWR messages to 7-bit address 0x12.
For the 960p path the sequence is bytes `01 01`, a 300 ms delay, then
`20 ff ff` for brightness. The alternate 768p path includes firmware-version
handling and must not be conflated with 960p. A static helper exposes only the
traced 960p sequence, requires an explicitly supplied I2C device, and is not
run automatically. Bare-metal bus-number correspondence remains unverified:
current native i2c-7 is DesignWare instance 4 at PCI 00:17.0, which does not by
itself prove equivalence to recovery's bus 7. No panel writes were made while
the eMMC transfer or its verification was active.

The stock kernel embeds a checksum-valid 128-byte 2400x960 EDID at extracted
ELF file offset 0x16ac790. Its detailed timing specifies a 153.98 MHz pixel
clock. Extracted EDID SHA256:
`63befb894e4bad2246e80d7b257a30dac434112ab337ffcedea90b7b0e0d2f40`.
Probe04 embeds this EDID and `i915/bxt_dmc_ver1_07.bin` in the kernel firmware
store so early i915 probing does not depend on userspace firmware availability.
The command line selects `drm.edid_firmware=HDMI-A-1:edid/harman0960p.bin`
and `video=HDMI-A-1:e`. Forcing a connector and supplying stock timing was tested, but is not evidence of physical link initialization.

The image retains automatic framebuffer color bars, RAM-only storage policy,
USB ACM/NCM shell access and public-key SSH, and includes matching igb/brcmfmac
modules, stock Wi-Fi firmware, iw/wpa_supplicant, and a statically built
mmc-utils readback tool. Wireless credentials are not embedded. PID1 was
compiled natively for this iteration. Final boot image size is 20731904 bytes,
SHA256 `61ca7eaa26846262a9306bfe1783a0d4824517421ec51c2367afbd58a04f2133`.
Local QEMU checks passed for probe04. The captured 1024x768 framebuffer
contained exact red, green and blue center-band samples `[255,0,0]`,
`[0,255,0]`, `[0,0,255]`; shell, SHA256, read-only block capacity, NCM
configuration and SSH-server startup also passed. Probe04 subsequently booted on the radio, with DMC loaded and a 2400x960
inteldrmfb containing verified RGB samples; the physical display remained blank.
No backlight class device exposed a brightness reading. The stock panel helper
was later attempted through the existing USB root shell on native i2c-10
(PCI 00:17.3, matching the cleanroom display-controller path). Its first reset
transaction returned `panel I2C transfer: Remote I/O error`, exit 1, before
the brightness write. See the [display ownership trace](../../video/display_subsystem.md#y175-panel-ownership-and-initialization--verified-2026-11-17-extended-2026-11-17).

**Probe05 console follow-up (2026-11-17):** CAN ELK entry from the stock boot
environment was acknowledged and USB 8087:09ef interface FF/42/03 confirmed.
The new RAM image booted with USB shell access. Its initial panel helper aborted
on a too-small realpath destination; the PATH_MAX correction was rebuilt,
transferred over T1 SSH, and successfully initialized the link (status CD).
The owner confirmed visible display output. The corrected image includes Linux
boot logos/fbcon, removal of PID1's periodic RGB repaint, 403 BusyBox applets,
custom I2C/KMS tools, and matching maXTouch/network modules. See the
[owning console and tooling result](../../video/display_subsystem.md#probe05-console-and-diagnostic-tooling--2026-11-17)
for the final hash, validation and remaining cold-boot limit.

**Probe06 boot verified (2026-11-17):** stock boot reached HMI-ready;
direct CAN ELK entry was acknowledged, temporary VIP state restored, and ELK
USB confirmed. RAM boot reached `4.19.283-elk-linux-probe-r06`, USB shell and
T1 root SSH. Embedded IPU firmware eliminated the previous ~62s request wait:
PID1 started at0.437303s and video/media nodes appeared, without proving capture.
Panel initialization initially preceded stable link readiness; a live retry
returnedCD. A corrected bounded-wait helper/image has been built and the helper
installed in RAM; fresh-boot validation of that correction remains pending.
The [owning build record](../../video/display_subsystem.md#probe06-corrected-build-and-firmware-staging--2026-11-17)
distinguishes booted and subsequently corrected image hashes and records the
regulatory-database rejection. The broad hardware inventory remains a probe05
snapshot; probe06 camera-node availability supersedes its earlier missing-node state.

**Matched Android source:** the mounted Y175 cleanroom
`os/system/priv-app/DelayedWKSApp/DelayedWKSApp.apk` and live APK both hash to
`5916ad9f7d40d2683e4dac49b7cc5086104dd27042c7fc32716fc3094288e241`.
The static `MY22CsmDIDRequestResponsePipeline` uses reflection to find a DID
handler in common and MY22 namespaces, and returns `REQUEST_OUT_OF_RANGE`
if absent. Live `FDF0` requests logged `DIDFDF0Handler: ClassNotFoundException`.
The tested `2F 81 80 03` request was recognized as `DIAG_CPID_CONTROL`, then
logged `IOCID8180Handler: ClassNotFoundException` in both namespaces.
This explains the Android-route failures without treating them as a VIP
firmware rejection. The native `diagnosticsd` binary itself could not be
byte-matched: live hashing returned `Permission denied`.

The [diagnostic test record](../../diagnostics/diagnosticsd_routines_and_recovery.md#gwm-boot-target-and-gm-8180-follow-up-2026-11-15)
owns exact live requests/results. Remaining questions:

- Any additional receiver-side boot conditions after the accepted F000/8180 request.
- Whether the installed VIP matches this update payload byte-for-byte.
- Reliable repeated ELK command access and its current device-state restrictions.
- Actual GHS response, completed ABL transition and resulting ELK environment.

CAN validation is pending the owner's USB CAN adapter; the MDI2 is not
connected, and its prior CAN communication was unreliable. No repeat
adapter discovery is required until hardware availability changes.

### 2.3.4 Recovery privilege and debug-ramdisk gates (verified 2026-11-12)

These findings use `system/bin/init` and `system/bin/adbd` from the original
`USB_Files/86331652` boot ramdisk, rather than assuming the normal AAOS adbd
has the same behavior.

- Shipped `prop.default` sets `ro.secure=1`, `ro.debuggable=0` and
  `ro.adb.secure=1`. Recovery adbd's root-service handler calls `getuid`
  at `0xBBFBB`, then `__android_log_is_debuggable` at `0xBBFC8`.
  A non-root daemon with a non-debuggable result reaches the production-build
  refusal at `0xBC06E`; a debug-capable path sets `service.adb.root=1`.
  The original ramdisk's `system/lib64/liblog.so` exports the called function
  at `0x9500` (161 bytes): it reads `ro.debuggable` at `0x954A`,
  compares the returned value with `1\0` at `0x9582`, and caches the result.
  This proves the property dependency rather than inferring it from the
  imported function's name; changing a build-type label alone is not this check.
- Its startup path reads `ro.secure` with default true at `0x9E34E`-
  `0x9E393`, then combines debuggability with `service.adb.root`.
  The privilege-drop branch configures minijail GID 2000 at `0x9E532`-
  `0x9E537` and UID 2000 at `0x9E53F`-`0x9E544`.
  Thus the recovery binary does not prove an unconditional UID-0 ADB shell.
- First-stage init checks the ramdisk-root marker `/force_debuggable`
  at `0xFC662`, copies debug artifacts toward `/debug_ramdisk`, and sets
  `INIT_FORCE_DEBUGGABLE` at `0xFC8A4`. Second-stage handling at
  `0x10D70F`-`0x10D7CD` requires the environment value `true` **and**
  `android::fs_mgr::AvbHandle::IsDeviceUnlocked()` at PLT `0x211EC0`.
  The alternate SELinux-policy selection at `0x148344` repeats that unlocked
  check. The property loader checks and loads readable
  `/debug_ramdisk/adb_debug.prop` at `0x12B649`-`0x12B680`.
- **Predicate boundary traced 2026-11-12:** the original recovery
  `system/lib64/libfs_mgr.so` exports `android::fs_mgr::IsDeviceUnlocked()`
  at `0x7E080`. It requests `verifiedbootstate` at `0x7E096`, calls
  `fs_mgr_get_boot_config` at `0x7E0C0`, then compares the resulting six-byte
  value with `orange` at `0x7E13F`. The lookup checks device-tree data first;
  its property path builds `ro.boot.<key>` and calls `GetProperty` at
  `0x72FB8`, then falls back to bootconfig/kernel-command-line sources when
  empty. This predicate does not independently read ABL's stored lock state.
  An effective reported `orange` can satisfy this one predicate, but no
  unprivileged way to supply it was established. Debug environment, artifacts,
  property initialization, adbd privilege/authentication and SELinux gates
  remain separate; the string alone does not demonstrate a root shell or
  change the underlying bootloader lock.
- Neither `force_debuggable` nor `adb_debug.prop` is included in the shipped
  ramdisk inventory. This is a boot-ramdisk debug mechanism, not a discovered
  USB filename parser. No MEC, registration or SBI input to these checks was
  established.
- The imported `init.recovery.common.rc` root console is disabled until
  `ro.debuggable=1`. Shell and netcat applets exist in the ramdisk, but the
  inspected init scripts define no telnet/SSH/netcat shell listener. A shell
  executable or root daemon alone does not provide a reachable privileged shell.

### 2.3.5 Bounded result of CLI analysis (2026-11-12)

Original SPS HostOS, SOC_ABL and boot-ramdisk binaries were inspected with
ELF parsing, Capstone disassembly, symbol/relocation lookup and cross-references.
Previously reconstructed image files were read with read-only debugfs where
needed; the recovery binaries and init configuration were independently
byte-matched to the original boot payload. No target state was changed.

The USB scanner's loop at `0x2B5CB9` waits 500 ms, scans `/mnt/media_rw`,
checks the encoded-marker flag at `0x2B5CFC`, and branches to the normal-reboot
handler at `0x2B60DE`. Conversely the main no-manifest branch at `0x2B533A`
reaches `0x2B54EB`, then can take `0x2B4681` into reboot routine
`0x2B56B0`; that routine invokes `swu_system_reboot` at `0x2B58D3`.
Scanner entry is conditional (including dealer/command state); this does not
prove every brief invocation reaches the marker check, nor that absence of a
USB package is the sole cause of the observed few-second reboot.

| Question | Result with current evidence | Remaining boundary |
|---|---|---|
| Ordinary versus dealer recovery | Same guest recovery executable; distinct inputs and branches | Logs/BCB/command state from a specific brief invocation |
| Recovery versus fastbootd | Separate protocol executable inside recovery guest under GHS VMM | Live command inventory for this exact revision |
| Recovery root or developer override | Production gates and unlocked-device debug mechanism directly traced | No reachable override from MEC/USB established |
| ELK/Kernelflinger | Separate ABL code, FRP/provisioning eligibility and state-write path, GHS request/HECI/shutdown evidence | ME/CSE/platform response, next boot, successful transition and GHS residency |
| EEPROM/MEC changing build type | AAOS certificate gate proven separately; host MEC-reporting strings are not a traced end-to-end join (§2.3.6) | No MEC-to-debuggable/unlock/root hop established |

The targeted entry, marker, privilege and lock branches above have been
resolved as far as these traces support. This is not an exhaustive proof over
all firmware instructions, indirect calls, VIP firmware or runtime states;
unresolved joins remain explicitly unproven.

### 2.3.6 Boot authorities, seed inputs and MEC-reporting evidence (reconciled 2026-11-12)

This section reconciles an additional string/section inventory with the
instruction-level results in §2.3.3–§2.3.4. The offsets below are into the
original HostOS payload's ELF-bearing slice (package offset `0x27C`),
not task-runtime VMAs. Literal presence, a section assignment and an
end-to-end traced dataflow are different evidence levels.

| Evidence | Supported conclusion and limit |
|---|---|
| GHS identity at `0x491411`; VMM/VMX names at `0x569A2B` / `0x560B2D`; `Guest1.VCpu1` at `0xE31CE1` | GHS hosts the Android guest; §2.3.3 proves the normal/recovery guest-selection flag. |
| Recovery/normal command-line strings at `0xCF95ED`, `0x5DFB43`, `0xCF80A3`, `0xCF82C9` | Consistent with the disassembled VMM command-line construction, not independent proof of a new OS for each screen. |
| ABL Kernelflinger code versus recovery `fastbootd` | Separate firmware implementation and guest userspace executable. A successful transition into ELK and its post-transition environment remain bounded by §2.3.3. |
| `Booted from ABL prompt.` at `0xB5A57D`; `ABL.version`, `ABL.partnumber`, `ABL.bdev`, `ABL.dls` nearby | ABL-origin handoff/boot-device metadata is represented. The diagnostic's condition checks boot-device input; it is not proof of a live interactive ABL console. |
| VIP reset-request/wait diagnostics at `0x5DFA39`, `0x5DFA14`, `0xCF784A` | VIP participates in platform power/reset handling. These diagnostics do not alone prove the successful next boot of a particular ELK request. |

**Seed and boot authority evidence.** The HostOS inventory contains
`cseseed_iodevice.c` (`0x51513C`), `CseSeed_Init` (`0x529C4F`),
`HandleAblSeedArgument` (`0x52A0DD`),
`HandleAblSeedListArgument` (`0x52A380`), `AttestationSeedList`
(`0x529D6F`), and `ABL.seed` / `ABL.seed_list` / `ABL.oemkm`
(`0x492029` / `0x492032` / `0x491238`).
Together with `intel_heci.c` and `Intel HECI`, these identify ABL/CSE
handoff and live host-to-firmware interfaces worth tracing. The ELK-side HECI
call is independently disassembled in §2.3.3. Names alone do not reconstruct
all seed derivations, prove control of every derived key, or prove a method
for altering the authenticated handoff. No VIP-supplied key seed or reachable
Kernelflinger-to-running-GHS debugger was established.

**MEC reporting evidence, without merging different paths.** Original VIP_APP
`86331656` contains `[J6_CDD] Transmitted MEC Value - 0x%2x` at package
offset `0x8586`, the dev-phase extended-wakeup diagnostic at `0x8646`,
and `is_MecInPlantStation` at `0x8856`. Separate VIP diagnostics
distinguish processing versus ignoring the hypervisor startup timeout.
These support a VIP MEC-dependent power/liveness behavior; they do not
establish that MEC counts failed boots.

The HostOS has `Ignoring ReportMEC. Old: %d This: %d.` at ELF-slice
offset `0x94264A` and `MEC received (%d)` at `0x942671`, both in
`.camera.rodata`. They are consistent with host-side MEC reporting.
However, no instruction/wire trace here joins that camera-section handler
to the VIP's named transmitter or to the AAOS auth-manager. The previous
claim that the VIP→GHS end-to-end link was already proven from this pairing
was too strong.

The **AAOS certificate-authentication path is separately established**:
`ManufacturerEnableCounter` → `GMMecHandler` → `gm_adb_auth_init`
accepts MEC 1–255 to bypass the GM certificate requirement. A saved target
capture records MEC=241 on a user build. This contradicts the older appendix's
blanket claim that AAOS has no MEC handling. It does not establish that the
camera-section reporting path is an intermediate hop in ADB authorization.

No MEC-to-`ro.debuggable`, AVB-unlock or UID-0 dataflow was found.
§2.3.7 owns the auth-manager chain, Boolean inversion, historical MEC reading
and registration/reset limits. §2.3.4 owns the independent original-recovery
root/debug gates. Firmware display versions, bare symbol names and a
nonzero manufacturing value cannot replace these distinct checks.

### 2.3.7 MEC, ADB certificate authentication, root and registration

#### Certificate-authentication chain (original analysis 2026-08-26)

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
 → gm_adb_auth_init: bypass flag = (1 <= mec <= 255), subject to query/test-property gates
 → gm_adb_check_authentication short-circuits to ALLOWED, no cert
```

**MEC = Manufacturer Enable Counter:** nonzero during manufacturing/pre-delivery (security relaxed), zeroed at
vehicle delivery. So the SBI puts the VIP into a **manufacturing-mode MEC≠0 state**; the guest reads that as
"secure-ADB enforcement off," and adb opens with no cloud policy. **DID `0xF1A0` is the guest↔VIP crossover** —
the VIP's SBI-gated answer to that `$22` read is the single inferred hop (consistent with the proven VIP/EEPROM
gating). This resolves the whole "how the guest knows to unblock ADB" question end to end.

> **Caveat (added 2026-10-15):** DID `0xF1A0` is not present in the extracted firmware strings table
> (`eeprom/config_tool/firmware_re/vip_app_strings.tsv`, 120-line Ghidra xref export) — this specific DID
> value is unconfirmed by that source; the broader VIP→SoC `is_secure_mode` propagation mechanism may
> still be correct via a different/unobserved DID. (Note: `platform/security.md` §ProtoKey/ADB
> Authentication separately cites a live-vehicle `$22 F1A0` read returning `0xFF` — that is independent
> on-vehicle corroboration of DID `0xF1A0` specifically, not derived from this firmware-strings table, so
> the two findings are not in conflict: the string table's silence is simply not evidence either way.)

**Bench confirmation (now exact):** with the SBI flipped, (1) read DID `0xF1A0` via diagnostics — MEC should be
nonzero; (2) `getprop` / probe `gm_adb_is_secure_mode` — false; (3) inspect the `gmauthmanagerservice.socket.adb`
`"MEC"` reply. Also note: that MEC socket is **unauthenticated plaintext**, so it is independently spoofable on a
compromised guest (a separate finding).

#### Target readings, root gate and registration limits (2026-11-12)

A saved target Y181 log capture
`analysis/adb/Y181/gmccpa_probe_20260909_225421/logcat_main.txt` (path is relative to the external
`GM_research/aaos/gm_aaos/2024_Silverado_ICE/` tree, not this repo; 2026-11-12), lines
1084–1088, records a signed Java byte `-15`, its unsigned conversion to
**241 (`0xF1`)**, an auth-manager response `MEC241`, and Secure-ADB disabled
on a user build. Subsequent reads in that capture repeat 241. This corroborates
a nonzero value other than 255 and the certificate gate above. It does not
establish that all earlier MDI2/DPS/SPS reads were 241, that the value has never
changed, or that an earlier recollection of 219 was correct.

The §0.2 **Y181B** export adds another dated reading:
`bootup_log/gmlogger/46-main.log_2026_11_12_13_5_24.gz`, decompressed
lines 162205 and 163876, records
`GM Secure ADB disabled on user build, MEC=227`. The system logs also
record auth-manager replies `MEC227`. Retain the older 241 reading as
historical evidence; neither reading establishes a fixed value, the reason
for a change, UID-0 access or AVB unlock. The host Camera log's
`MEC received (1)` is a different consumer's message and must not be
substituted for the Android auth-manager's numeric reading.

The inspected normal-AAOS daemon's `gm_adb_is_secure_mode` at `0xA68C0`
inverts the stored bypass Boolean at `0x219200`. Consequently stored
`is_secure_mode=1` means certificate enforcement is bypassed, while the
named getter returns false. Its root-service path at `0xC2270` separately
calls `__android_log_is_debuggable` before the GM security gate; nonzero MEC
is not itself an `adb root` entitlement. This daemon was inspected from the
reconstructed Y181B filesystem (SHA-256
`6bfa2ba86ab2fe2a0ca0e2eb588139bc6402f687822b72b9c6d2efecda0de713`);
it has not independently been byte-matched here to the original compressed
system-module payload.

Original boot-payload recovery adbd/init/liblog provide separate verified
production/developer checks; see
§2.3.4 above.
The shipped recovery has `ro.secure=1`, `ro.debuggable=0`, a UID/GID-2000
drop branch, a production `adb root` refusal, and a disabled root console.
Relevant debug-ramdisk init branches check AVB device-unlocked state.
None of the verified USB markers changes these properties.

`GMMecHandler` forwards `ManufacturerEnableCounter` through the inspected
vehicle-data path; no registration-state decision was found in that handler.
The owner's observation that the radio reports unregistered after the EEPROM
change and changes state after MEC reset is a correlation, not a reconstructed
registration-to-ADB bypass. Additional radio/VIP reset-side effects remain
unresolved. No mapping from MEC values to CALDIS feature sets, no MEC-to-build-type
dataflow, and no EEPROM `0x0B41` root/developer switch were established.

`0xFF` numerically equals 255. An eight-bit reply can represent 0–255, and
the daemon accepts 1–255 for this authentication decision; neither fact proves
a supported operation can set every value. A reset-to-zero operation likewise
does not prove arbitrary writes or that its only effect is changing one byte.
Do not merge the Manufacturer Enable Counter, the GHS failed-boot counter and
the VIP consecutive-startup-failure condition without a demonstrated dataflow.

#### Other historical reading contexts

The following table was consolidated from the teardown's historical inventory.
Rows represent different builds, captures or access paths. Only the saved
MEC=241 target capture is independently rechecked in this pass; the remaining
rows retain their original reported context and are not evidence of a constant
MEC or a mapping from values to features.

| Unit/Build | MEC | Behavior |
|------------|-----|----------|
| Y175 (DPS A11_CSM_x80.Txt) | **244** | — |
| Y177 (via gateway) | **0** | Real seeds, SPS security validation failed |
| Y181 (bench, BSOB) | **207** | 0xFF seeds, GCI completed |
| Saved Y181 target auth-manager capture, 2026-09-09 | **241 (0xF1)** | Repeated ManufacturerEnableCounter/MEC241 readings; Secure-ADB disabled on user build |
| Y181B recovery USB export, 2026-11-12 (§0.2) | **227 (0xE3)** | Android auth-manager MEC227 replies and Secure-ADB disabled on user build; separate from Camera's MEC message |
| Y175 VIP UART log | **0xFF** (transmitted) | MEC at maximum — manufacturing/test mode? |

The earlier proposed EEPROM `0x1A80`/`0x0167` MEC mapping remains
unverified. Do not equate it with DID `0xF1A0` or the GHS failed-boot counter.

#### Historical diagnostic corroboration

The earlier security overview reported the following separate capture context.
It was not repeated in this static pass and must not be merged with the newer
31-byte seed/client observations as though they were one diagnostic session.

> **Live-vehicle corroboration (2026, MDI2 DoIP `dps_readx80` read of radio `0x80`).** `$22 F1A0`
> returned **`0xFF`** on the vehicle — the first on-vehicle confirmation of the MEC=0xFF path above
> (prior evidence was EEPROM/teardown only). Nuance on `$27`: that read (SPS "security validation
> facility failed") got an **all-`0xFF` seed**, while valid SPS sessions used an **8-byte seed /
> 6-byte key** and succeeded (ECUs 0x80/0x81/0xBE, `67 02` grants). So the all-FF `$27` seed is the
> **SPS-credential-absent path**, not necessarily a hardware SBI flip — worth separating in
> `$27`/SBI analysis. (Redacted diagnostic-session reports: `GM_RESEARCH/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/diag/`.)

### 2.4 Android-GHS IPC Channels

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ANDROID ↔ GHS COMMUNICATION CHANNELS                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  /dev/ghs/* Device Interfaces:                                               │
│  ├── /dev/ghs/textlog      - GHS kernel logs                                │
│  ├── /dev/ghs/audit        - Security audit log                             │
│  ├── /dev/ghs/snapshot-dbg - Debug snapshots (accepts 'P' command)          │
│  ├── /dev/ghs/ipc          - General IPC channel                            │
│  ├── /dev/ghs/cal          - Calibration data                               │
│  ├── /dev/ghs/camera       - Camera control                                 │
│  ├── /dev/ghs/chime        - Chime/alert sounds                             │
│  ├── /dev/ghs/tee-att      - TEE attestation                                │
│  ├── /dev/ghs/emmc-health  - eMMC health monitoring                         │
│  ├── /dev/ghs/ota-isys     - OTA update interface                           │
│  └── /dev/ghs/gpu-dbg      - GPU debug (commands: d, p, t)                  │
│                                                                              │
│  VMM IPC Connections:                                                        │
│  ├── ConnToVMM_Camera      - Camera passthrough                             │
│  ├── ConnToVMM_Capture     - Capture control                                │
│  ├── ConnToVMM_Display     - Display passthrough                            │
│  ├── ConnToVMM_Chime       - Chime control                                  │
│  ├── ConnToVMM_Cal         - Calibration                                    │
│  ├── ConnToVMM_OTA         - OTA updates                                    │
│  ├── ConnToVMM_OTA_Control - OTA control                                    │
│  ├── ConnToVMM_EMMCHealth  - eMMC health                                    │
│  ├── ConnToVMM_TextLog     - Text logging                                   │
│  └── ConnToVMM_Audit       - Audit logging                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Update and Recovery Handling

### 3.1 A/B Slot Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         A/B SLOT MANAGEMENT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MISC PARTITION LAYOUT:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Offset 0x000: Bootloader Control Block (BCB)                        │    │
│  │  ├── command[32]     - "boot-recovery", "boot-see-dealer", etc.     │    │
│  │  ├── status[32]      - Status string                                 │    │
│  │  ├── recovery[768]   - Recovery command arguments                    │    │
│  │  └── stage[32]       - Recovery stage                                │    │
│  │                                                                      │    │
│  │  Offset 0x800: A/B Metadata                                          │    │
│  │  ├── magic           - Magic number                                  │    │
│  │  ├── version         - Metadata version                              │    │
│  │  ├── slot_info[2]    - Per-slot information                          │    │
│  │  │   ├── priority    - Boot priority                                 │    │
│  │  │   ├── tries_remaining - Remaining boot attempts                   │    │
│  │  │   ├── successful_boot - Boot success flag                         │    │
│  │  │   └── verity_corrupted - Verity corruption flag                   │    │
│  │  └── crc32           - CRC32 checksum (WEAK!)                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  GHS A/B Boot Logic:                                                         │
│  1. Read A/B metadata from misc partition                                    │
│     └── "VMM: ERROR: failed to read A/B metadata from 'misc'"               │
│                                                                              │
│  2. Validate metadata                                                        │
│     ├── Check magic number                                                   │
│     │   └── "VMM: Warning: A/B metadata: magic number mismatch"             │
│     ├── Check CRC                                                            │
│     │   └── "VMM: Warning: A/B metatdata CRC failure!" ← CRC only!          │
│     └── Check version                                                        │
│         └── "VMM: ERROR: A/B metadata: version on disk too new"             │
│                                                                              │
│  3. Select boot slot                                                         │
│     ├── Check priority and tries_remaining                                   │
│     ├── "VMM: A/B Boot: No more remaining attempts for slot %d"             │
│     └── "VMM: A/B Boot: ERROR: no valid boot slot"                          │
│                                                                              │
│  4. Boot selected slot                                                       │
│     ├── "A/B Boot Slot: boot%s"                                             │
│     └── "androidboot.slot_suffix=%s"                                        │
│                                                                              │
│  5. Handle slot mismatch                                                     │
│     └── "GHS: Android and INTEGRITY slot mismatch. INTEGRITY: %s            │
│          Android: %s Rebooting..."                                          │
│                                                                              │
│  See §6.1 for the CRC32-only weakness assessment.                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Recovery Mode Handling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RECOVERY MODE HANDLING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Recovery Mode Entry Points:                                                 │
│                                                                              │
│  1. BCB Command (misc partition)                                             │
│     ├── Write "boot-recovery" to BCB command field                          │
│     └── GHS reads BCB at boot: CheckRecoveryMode()                          │
│                                                                              │
│  2. VIP-Initiated Recovery                                                   │
│     ├── VIP sends recovery request via IPC                                   │
│     └── GHS triggers recovery boot                                          │
│                                                                              │
│  3. Boot Failure Fallback                                                    │
│     ├── Android fails SoH check                                              │
│     ├── Boot attempts exhausted                                              │
│     └── Automatic recovery/slot switch                                       │
│                                                                              │
│  GHS Recovery Functions:                                                     │
│  ├── CheckRecoveryMode()        - Check for recovery boot request           │
│  ├── "boot-recovery"            - BCB command string                        │
│  └── "VMM: Error: Failed to read BCB" - BCB read error                      │
│                                                                              │
│  Recovery State Machine:                                                     │
│  ┌──────────┐     BCB="boot-recovery"    ┌──────────────┐                   │
│  │  Normal  │ ─────────────────────────► │   Recovery   │                   │
│  │   Boot   │                            │     Mode     │                   │
│  └──────────┘                            └──────────────┘                   │
│       │                                         │                            │
│       │ Boot failure                            │ Recovery complete          │
│       ▼                                         ▼                            │
│  ┌──────────┐                            ┌──────────────┐                   │
│  │  Retry   │                            │  Clear BCB   │                   │
│  │  Boot    │                            │  Normal Boot │                   │
│  └──────────┘                            └──────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 OTA Update Handling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OTA UPDATE HANDLING                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  OTA Components:                                                             │
│  ├── OTA_InitialTask          - GHS OTA handling task                       │
│  ├── /dev/ghs/ota-isys        - OTA interface to Android                    │
│  ├── ConnToVMM_OTA            - OTA IPC connection                          │
│  └── ConnToVMM_OTA_Control    - OTA control channel                         │
│                                                                              │
│  OTA Update Flow:                                                            │
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  Android OTA    │                                                         │
│  │  Client/Server  │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           │ Write update to inactive slot                                    │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │ /dev/ghs/ota-isys│ ──► GHS OTA Interface                                 │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           │ OTA commands via IPC                                             │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │  OTA_InitialTask │                                                        │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ├── Validate update package                                        │
│           │   └── "Bad command length for OTA command."                     │
│           │                                                                  │
│           ├── Update ABL (if needed)                                         │
│           │   ├── "GHS: Error: ABL update command failed: %d"               │
│           │   └── "GHS: Error: Failed to send ABL update command"           │
│           │                                                                  │
│           ├── Update CSE (Intel Management Engine)                           │
│           │   ├── "GHS: Error: CSE prepare update HECI command failed"      │
│           │   └── "GHS: Error: CSE did not enter prepare update mode"       │
│           │                                                                  │
│           └── Update A/B metadata                                            │
│               └── "VMM: ERROR: A/B boot metadta write failed."              │
│                                                                              │
│  Firmware Update Services (Android):                                         │
│  ├── fw_update_slota - "/vendor/bin/cmd_fw_update_vendor -s -i m1:@0"       │
│  ├── fw_update_slotb - "/vendor/bin/cmd_fw_update_vendor -s -i m2:@0"       │
│  └── fw_update       - "/vendor/bin/fw_update.sh"                           │
│                                                                              │
│  Capsule Update (ABL recovery):                                              │
│  on property:vendor.ota.recovery.fw=a                                        │
│      write /sys/kernel/capsule/capsule_name m1:@0                            │
│      setprop sys.powerctl reboot                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Verified Boot (AVB) Error Handling

| Error | Message | Cause |
|-------|---------|-------|
| Key mismatch | `VMM: Error: vbmeta signing key does not match known valid key` | Wrong signing key |
| Verification failed | `VMM: vbmeta: image verification failed!` | Signature invalid |
| No vbmeta | `VMM: ERROR: no vbmeta partition found (slot %s)` | Missing partition |
| Load failed | `VMM: ERROR: failed to load vbmeta partition from disk` | I/O error |
| Bad header | `VMM: vbmeta bad header: descriptors outside data block` | Corrupt vbmeta |
| No boot | `VMM: A/B: no boot image for slot %s` | Missing boot image |
| Rollback | `VMM: ERROR: rollback index is too old` | Downgrade attempt |
| Signature | `VMM: Error: Android signature verification failed` | Bad signature |

---

## 4. Trigger Files and Reboot Mechanisms

### 4.1 Protokey Trigger System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROTOKEY TRIGGER FILE SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRIGGER DIRECTORY:                                                          │
│  /data/gmprotokey/trigger/                                                   │
│                                                                              │
│  Created by init.protokey_recovery.rc:                                       │
│    mkdir /data/gmprotokey 0750 root shell                                    │
│    mkdir /data/gmprotokey/trigger 0770 shell root                            │
│                                                                              │
│  Trigger Detection (gm_protokey_recovery):                                   │
│  ├── Monitors /data/gmprotokey/trigger/ for files                           │
│  ├── Validates file ownership (must be shell or root)                        │
│  │   └── "Trigger file %s (uid %d) is not owned by shell or root"           │
│  ├── On valid trigger:                                                       │
│  │   └── "Trigger file %s (uid %d) present. Starting Protokey Recovery"     │
│  └── Installs recovery protokey                                              │
│      └── "Installing Recovery Protokey"                                      │
│                                                                              │
│  Protokey Recovery Process:                                                  │
│  1. Read recovery salt from file                                             │
│     └── "reading recovery salt from %s"                                     │
│  2. Generate/retrieve validation code                                        │
│     └── "Retrieving protokey recovery validation code"                      │
│  3. Validate recovery key                                                    │
│     └── "Protokey Recovery validation passed"                               │
│  4. Install via keymaster                                                    │
│     └── "keymaster decryption failed, Failed to install recovery Protokey"  │
│                                                                              │
│  Related Files:                                                              │
│  ├── .protokey_recovery              - Recovery key data                    │
│  ├── .protokey_recovery_validation   - Validation code                      │
│  └── .protokey_recovery_salt         - Recovery salt                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Internal recovery argument file and accepted options

**Corrected 2026-11-12:** `/update_cache/recovery/command` is a regular text
file on internal storage, supplying recovery startup arguments one per line.
The loader uses a 4,096-byte line buffer, strips CR/LF, and accepts up to
99 argument lines. It performs no shell expansion. It is not a shell script,
USB directory, or independently proven reboot watcher.
The earlier diagram claiming that `gm_protokey` monitors it and interprets
empty/normal contents as reboot commands was not supported by the traced code
and has been removed. Entering recovery is a separate operation.

The Y181B recovery long-option table is at executable VA `0x421AC0`
(13 entries plus a null sentinel); the parser call is at `0x2B3E61`.
There are eight required-value options and five without values:

| Option | Argument and downstream interpretation |
|---|---|
| `--update_package=<value>` | Registered, but its switch target returns directly to parsing; ignored in this build. |
| `--gm_manifest=<path>` | GM binary manifest path. Waits for/mounts storage; if missing, the USB search uses the original basename as a substring. Feeds manifest/status/security/version processing and `gm_updater`. |
| `--ota_update=<path>` | ZIP containing GM update files; extracts under `/tmp`, changes directory there, and selects a name containing `.mnf`. Not a Boolean switch. |
| `--current_version=<text>` | Unchanged string, default empty, compared to candidate manifest versions with `strcmp`; not parsed numerically. Manifest version-check flags also apply. |
| `--date_time=<seconds>` | Decimal Unix epoch seconds through `atoll`, then `timeval.tv_sec` with zero microseconds to `settimeofday`. No strict whole-string validation established. |
| `--buildinfo=<text>` | Extracts a build-version substring shorter than 21 bytes and normalizes it for minimum-version comparison; also participates in P-to-Q automatic data-wipe detection. |
| `--min_version_downgrade_to=<version>` | Version shaped as `PREFIX-N[.M]`; normalized with five-digit major and two-digit minor fields, then used as a string-comparison floor when manifest checks enable it. |
| `--updated_modules=<list>` | Comma-separated decimal module IDs consumed by `USF_InitializePartList`; initializes matching module status to 3 (already updated), not shell commands. |
| `--wipe_data` | Sets the wipe flag. |
| `--prompt_and_wipe_data` | Reaches the same wipe flag; no separate confirmation path is selected by this option in the traced build. |
| `--show_text` | Requests text UI conditionally on `ro.debuggable=1`; does not set that property or enable a shell. |
| `--show_return_to_dealer` | Selects the dealer UI path. |
| `--fastboot` | Selects the same recovery-fastbootd path reached from BCB `boot-fastboot`; see §2.3.1. |

For example, the version formatter turns `QIH22B-16.2` into
`QIH22B-00016.02`. This describes parsing, not an accepted downgrade.
Both wipe-option paths store 1 to `[rbp-0x3C]` (`0x2B3F1A` and
`0x2B40E9`-`0x2B40F3`). The `--update_package` jump-table entry
lands at `0x2B3E4E`, back at the parser loop.

The `--updated_modules` consumer is `USF_InitializePartList`
at `0x389870`: comma tokenization at `0x389935`, decimal `strtoq`
at `0x389987`, and bit `0x80` cleared before mapping. Mapped module IDs
are 1–15, 21, 22, 23, 24, 26, 28, 29, 51–57, 71, 72 and 81.
Matching initial-status entries become state 3 at `0x389CD8`-`0x389CDD`;
`USF_ModuleAlreadyUpdated` checks state 3 at `0x38B1ED`. Existing
status can skip initialization. These are module IDs, not SPS part numbers;
this processing input does not itself prove bypassed package validation.

Build-version extraction is `get_build_version` at `0x2B35D0`,
using the unanchored expression `[A-Z0-9]+[-][0-9]+([0-9]|[.])*`.
The shared formatter `get_fix_format_version` at `0x2B2260` uses
`atoi` and retains the prefix plus normalized major/minor fields, not
arbitrary later components. `--min_version_downgrade_to` uses that formatter
directly, without the buildinfo regex extraction. The minimum-version path
`0x2B6200` includes ESS/version/enable/input-dependent skip paths. These
guest software comparisons are distinct from GHS/AVB antirollback enforcement.
The P-to-Q forced-wipe call is at `0x2B5497`.

BCB command-field values `boot-see-dealer` and `boot-fastboot` are a different
input from this argument file. Copying an identically named file to USB does not
establish equivalent behavior. None of these arguments establishes a shell
interpreter, signature bypass, developer build, or GHS privilege change.
For the separately supplied dealer wipe package, see
§4.2.1 below.

### 4.2.1 Dealer data-wipe package and formatter (verified 2026-11-12)

Source: the research archive's `module_dumps/Data Wipe Dealer/94292067.mnf`
and adjacent `11110011.AA`; this is a separately supplied older dealer package,
not the Y181B OS payload. The manifest's embedded script begins at file offset
`0xB1`. It updates dynamic-partition configuration, copies the delta package,
calls `gmext.redbend_update` for module 56 with target label `vbmeta`
and recovery/no-reboot arguments, deletes temporary files, then directly calls:

```text
format("f2fs","EMMC","/dev/block/vda26","0","/data")
```

It does not rely on recovery's `--wipe_data` or `--prompt_and_wipe_data`
arguments. The block path is hardcoded for that package; it is not a general
partition mapping for every radio or firmware revision.

`11110011.AA` is 324 bytes and identifies itself as `RedBendEFDPackage`.
Its embedded script contains `update vbmeta`, `run UpdateDummy` and
`progress 20`. It is not a full AVB vbmeta image. Its exact resulting vbmeta
byte changes remain unresolved; these strings do not establish verification
disablement, new signing keys, or a bootloader unlock. The manifest's
`"DummyPackage": true` field likewise does not establish bypassed validation.

The original Y181B boot ramdisk's `system/bin/gm_updater` is 1,847,920 bytes,
SHA-256 `0c43c52ed294c0d9a751bc2f23430dc537bfd854016b9107e8a64d3f3c6809ea`.
Its retained `.gnu_debugdata` identifies `FormatFn` at VA `0xAAA40`
(3,381 bytes). The function requires five arguments, accepts the supplied block
path, and contains ext4 and F2FS formatting branches; executable paths
`/system/bin/mke2fs` and `/system/bin/make_f2fs` are referenced at
`0xAAB8B` and `0xAAE53`. No `/data`-only restriction was found within
that function. The interface agrees with the
[AOSP five-argument formatter](https://android.googlesource.com/platform/bootable/recovery/+/4177367a4a6391fa5bab9f89c9b00f634eb56843/updater/install.cpp).

This establishes a general formatting primitive and this package's explicit
`/data` target. Another **accepted** script might select another accessible
block device; acceptance of an edited/custom package, the complete validation
path and compatibility of this older dealer package with Y181B were not
demonstrated. Formatting a system partition would erase it; it would not
install a replacement OS or alter GHS resource permissions.

Package fingerprints:

| Artifact | SHA-256 |
|---|---|
| `94292067.mnf` | `5c8aeeef1b125c98f046a6010c741cf25e952ee6dacff1612c93d552e142465f` |
| `11110011.AA` | `d3f9804ce37704f83f2df6f3532f17340b45a073d80413d0f1b0835ac11e7a1f` |


### 4.3 Other Reboot Triggers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OTHER REBOOT TRIGGERS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. PROPERTY-BASED TRIGGERS (init.rc):                                       │
│                                                                              │
│  # Warm boot trigger (non-debuggable builds)                                 │
│  on property:ro.debuggable=0 && property:sys.boot.reason=warm                │
│      setprop sys.powerctl reboot                                             │
│                                                                              │
│  # Watchdog trigger                                                          │
│  on property:ro.debuggable=0 && property:sys.boot.reason=watchdog            │
│      setprop sys.powerctl reboot                                             │
│                                                                              │
│  2. CAPSULE FIRMWARE RECOVERY:                                               │
│                                                                              │
│  # Slot A firmware recovery                                                  │
│  on property:vendor.ota.recovery.fw=a                                        │
│      write /sys/kernel/capsule/capsule_name m1:@0                            │
│      setprop sys.powerctl reboot                                             │
│                                                                              │
│  # Slot B firmware recovery                                                  │
│  on property:vendor.ota.recovery.fw=b                                        │
│      write /sys/kernel/capsule/capsule_name m2:@0                            │
│      setprop sys.powerctl reboot                                             │
│                                                                              │
│  3. GHS-INITIATED REBOOTS:                                                   │
│                                                                              │
│  # Android SoH failure                                                       │
│  "GHS: [LIFECYCLE] Lost Android SoH - rebooting"                             │
│                                                                              │
│  # Slot mismatch                                                             │
│  "GHS: Android and INTEGRITY slot mismatch... Rebooting..."                  │
│                                                                              │
│  # VIP reset                                                                 │
│  "GHS: Initiating VIP reset"                                                 │
│  "GHS: VMM: waiting for VIP system reset..."                                 │
│                                                                              │
│  4. CRITICAL FAILURE REBOOTS:                                                │
│                                                                              │
│  # BoringSSL self-check failure                                              │
│  reboot_on_failure reboot,boringssl-self-check-failed                        │
│                                                                              │
│  # BPF loader failure                                                        │
│  reboot_on_failure reboot,bpfloader-failed                                   │
│                                                                              │
│  # Vold failure                                                              │
│  reboot_on_failure reboot,vold-failed                                        │
│                                                                              │
│  # APEX daemon failure                                                       │
│  reboot_on_failure reboot,apexd-failed                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 USB trigger handling: recovery versus normal AAOS

**Corrected 2026-11-12:** Y181B `/system/bin/recovery` itself handles the
encoded reboot and log-capture filenames below. The earlier attribution to
normal-AAOS `gm_update_engine` alone was unsupported. That service exists at
`/vendor/bin/hw/gm_update_engine`, but its USB permissions do not establish the
recovery handler. GHS selects recovery/dealer boot modes; it is not the verified
USB filename scanner.

The inspected recovery executable is byte-identical to `system/bin/recovery`
in the LZ4/newc ramdisk of approved Y181B `USB_Files/86331652`: 2,361,896 bytes,
SHA-256 `548ee019f42eb1920332605c8e118775de2038cc3038bc6a10f4170143eec714`.

### 4.5 Known USB trigger files

| Source label | Filename used by recovery | Evidence |
|--------------|---------------------------|----------|
| `gm_reboot_normal` | `Z21fcmVib290X25vcm1hbA==` | GM PIT6209 dealer procedure and Y181B code; return to normal boot |
| `gm_capture_log` | `Z21fY2FwdHVyZV9sb2c=` | Y181B code and successful bench USB export (§0.2, §4.5.4) |

The capture marker is bench-tested on Y181B; no comparable dealer bulletin for
log capture or a debug/root-shell filename was identified. Existing update controls
`gm_usb_ignore_battery` and `gm_usb_auto_install` are separate; their prior
normal-updater descriptions were not reverified by this recovery trace.

### 4.5.1 Dealer procedure and filename requirements

[GM PIT6209, 2024-07-31](https://static.nhtsa.gov/odi/tsbs/2024/MC-11007670-0001.pdf)
applies to IOK, including the 2024 Silverado. It prescribes a 16/32 GB FAT32
Type-C USB and an empty `Z21fcmVib290X25vcm1hbA==` file without `.txt`, then
A11 Programming and Setup after reboot. Its Windows File Explorer instructions
create and rename a blank text document. The bulletin prints the encoded name;
it does not prescribe the plain-text label. This is the only encoded-filename
dealer procedure established by the sources checked here.

[PIT6209C, 2024-11-01](https://static.nhtsa.gov/odi/tsbs/2024/MC-11011183-0001.pdf)
retains that name and distinguishes its software-anomaly concern from a failed
OTA update. Not every dealer-screen event is an update failure.

### 4.5.2 Base64 is part of the filename check

Recovery loads the 16-byte source label at `0x2B7A92`, then calls `0x4043B0`
at `0x2B7ABB`. This helper implements standard Base64 encoding, including the
alphabet and padding. The encoded output is supplied to the filename-search
routine at `0x2B7B9E`; detection logging is selected at `0x2B7BB7` and its flag
is set at `0x2B7BC7`. Addresses are executable virtual addresses.

The parallel log-capture path loads its 14-byte label at `0x2B7AD0`, encodes it
at `0x2B7AF9`, selects its detection log at `0x2B7BEF`, and sets its flag at
`0x2B7C29`.

```text
Base64("gm_reboot_normal") = "Z21fcmVib290X25vcm1hbA=="
Base64("gm_capture_log")   = "Z21fY2FwdHVyZV9sb2c="
```

The previous claim that plain and encoded filenames should both work is
withdrawn: this path searches using the encoded token. Follow the bulletin's
exact name. The string-search path also does not establish the previous blanket
claim that only an exact whole-filename match is accepted.

### 4.5.3 Recovery effect and limits

Recovery's normal-boot exit logs `The special file exist, boot to normal` at
`0x2B60DE`. It recognizes `boot-see-dealer` and logs dealer mode at `0x2B4849`;
`/update_cache/recovery/command` is another input. The marker selects normal boot;
it does not repair corrupt storage or failing hardware. No trigger that changes
`ro.debuggable`, starts a root shell, or guarantees a persistent recovery session
was established by these filename checks.

### 4.5.4 Verification scope

Static verification uses approved Y181B binaries matched to original SPS payload
bytes. The §0.2 capture additionally verifies the log-capture marker on hardware:
`recovery/last_log`, lines 100–102, records
`Found gm capture log file = Z21fY2FwdHVyZV9sb2c=` followed by
`Start to capture update log`. The resulting ZIP contains the three documented
output trees. This does not test every marker or every boot-mode transition.

### 4.5.5 Marker matching, volume names and log-capture contents

**Verified 2026-11-12:** callback `process_manifest_files_ftw` at
`0x2B79D0` accepts regular-file entries and counts slashes at
`0x2B7A64`-`0x2B7A8D`. Four slashes corresponds to
`/mnt/media_rw/<volume>/<filename>`. The encoded token is searched as a
substring of the full path, rather than by whole-basename equality. Both
source labels are encoded without a trailing NUL. The empty exact filenames
remain the unambiguous documented form; arbitrary marker contents are not
interpreted by these checks.

No volume-label or partition-name comparison selecting recovery/debug was found
in this scanner. Recovery fstab identifiers `usbdisk` and `sdcard1` are vold
configuration names, not required filesystem labels. The scan must first be
reached; a USB marker itself does not enter recovery.

The `gm_capture_log` flag is consumed at `0x2B5CDA`-`0x2B5CF7`,
calling `save_logs` at `0x2B2830`, which calls `copy_logs` at
`0x2B6AD0`. These names are recovered independently from the original
recovery executable's embedded `.gnu_debugdata`. The USB-copy path checks NTFS magic
at `0x2B310F` and rejects it, constructs `update_cache/recovery`
at `0x2B3132`, checks space, and copies available data. Recovery creates
the destination `update_cache/` directory; the user does not need to precreate it.
Existing contents in that USB directory may be cleared before copying:
`remove_file_ftw` is at `0x2B7280`; recursive `copy_dir` is at
`0x2B7290`. The update-file exclusion table is at VA `0x421C80`,
and `save_prop_log` is at `0x2B24E0`.

| Path beneath USB-root `update_cache/` | Code-observed source/content |
|---|---|
| `recovery/log`, `recovery/last_log` | Recovery output from `/tmp/recovery.log` |
| `recovery/last_kmsg` | Current Linux kernel ring buffer via `klogctl`, not necessarily a previous boot's kernel log |
| `recovery/last_logcat` | Verbose-filtered logcat snapshot using `threadtime` |
| `recovery/last_install` | Installer status from `/tmp/last_install` |
| `recovery/last_program_status` | `/tmp/program_status.log` |
| `recovery/props.log` | Recovery environment `getprop` output; path construction at `0x2B259B` |
| `recovery/...` | Other existing recovery files and available numbered histories |
| `update/...` | Existing update directory, excluding `RR_update_package.zip` and `download_placeholder` |
| `bootup_log/...` | Existing `/update_cache/bootup_log` contents |

Directory copies are recursive and available files depend on runtime state.
The path finishes with `sync`. No direct GHS memory-dump request or complete
GHS runtime-log export was established. Any GHS information must already be in
the copied logs or Android logging. The §0.2 USB export corroborates the
available recovery/update/bootup-log copy behavior, including retained GHS/VIP
logs and `CalSets.db`; it does not establish a new GHS collection request.
`recovery/last_logcat` is absent in this export. The recovery log reports
`exec(logcat) failed: No such file or directory` and
`logcat: Failed with status 255`; the saved compressed Android logs are
retained bootup logs, not proof that this final logcat command succeeded.

### 4.6 Trigger Files Summary Table

| Trigger File/Path | Purpose | Handler | Effect |
|-------------------|---------|---------|--------|
| **USB: `Z21fcmVib290X25vcm1hbA==`** | Exit dealer recovery | `/system/bin/recovery` (verified Y181B) | Normal reboot; label `gm_reboot_normal` |
| **USB: `Z21fY2FwdHVyZV9sb2c=`** | Capture diagnostics | Guest recovery | Writes available logs under USB-root `update_cache/`; existing files may be cleared |
| **USB: `gm_usb_ignore_battery`** | Normal-AAOS update flag | Android updater | Discovery/copy observed; full bypass effect not reverified |
| **USB: `gm_usb_auto_install`** | Normal-AAOS update flag | Android updater | Discovery/copy observed; full auto-install effect not reverified |
| `/update_cache/recovery/command` | Recovery startup arguments | Guest recovery | One argument per line; no proven file-watcher reboot |
| `/data/gmprotokey/trigger/*` | Protokey recovery | gm_protokey_recovery (Android) | Install recovery protokey |
| `/sys/kernel/capsule/capsule_name` | Firmware recovery | Kernel | ABL firmware update + reboot |
| `sys.powerctl` property | System reboot | Android init | Immediate system reboot |
| `sys.shutdown.requested` property | Shutdown request | gm_protokey | Graceful shutdown |
| BCB (misc partition) | Boot command | GHS VMM / recovery | Recovery/dealer/fastboot inputs; ELK requires the separate §2.3.3 transition |

---

## 4.7 Dealer-screen display and scanner ownership

**Corrected 2026-11-12:** the verified dealer recovery and encoded USB-marker
handler run in `/system/bin/recovery`, inside the Linux/Android guest.
Recovery recognizes `boot-see-dealer` and selects the dealer UI branch at
`0x2B481C`-`0x2B48AC`; its USB scanner and normal-reboot exit are traced
in §4.5. The previous diagram incorrectly assigned this verified recovery
scanner to the normal AAOS `gm_update_engine` service and treated Android's
ability to detect USB as proof that GHS cannot render anything.

| Responsibility | Component established by the inspected path |
|---|---|
| Failed-boot monitoring / dealer boot selection | GHS lifecycle/VMM; separate VIP monitoring also exists |
| Selecting the guest recovery boot | GHS VMM recovery flag |
| Dealer recovery UI branch and encoded marker scan | Guest `/system/bin/recovery` |
| Normal-AAOS update service and USB flag handling | AAOS updater stack; separate from the verified recovery scanner |
| Fastboot USB protocol service | Guest recovery `/system/bin/fastbootd` |

These findings do not prove that GHS has no display capability or cannot supply
other overlays/error indications. The normal AAOS update UI, guest init
verity-warning slideshow and recovery dealer UI are separate rendering paths.
See §2.3.3 for execution boundaries and §4.5 for the scanner's entry conditions.


### 4.7.1 GM Android-side dealer-recovery writer (verified 2026-11-12)

Y181B vendor `/vendor/bin/hw/plmanager` contains the recovered symbol
`vendor::gm::powermode::V1_0::implementation::PowerModing::rebootSeeDealer()`
at VA `0x20B40`. This is a producer of dealer-recovery input, rather than
only a consumer of the BCB dealer string:

1. Opens `/update_cache/recovery/command` with `O_RDWR | O_CREAT`
   (`0x42`) at `0x20B7F`; changes permissions to `0770` and ownership to
   the `system` account. It does not open with `O_TRUNC`.
2. Writes 24 bytes at `0x20BEF`: the 23-character
   `--show_return_to_dealer` argument followed by NUL, then closes and syncs.
3. Calls `pm_mgr_pal_request_power_cycle(0, 0, reason_bytes)` at
   `0x20C61`, with reason bytes `20 00`. The PAL builds a `boot-recovery`
   message, selects recovery target 3, uses `/dev/ghs/ota-isys` or the
   `/dev/block/by-name/misc` fallback, and sends the power-cycle request.
   The alternative target setter is `set_boot_target()` at `0x37D60`.

Its identified direct caller is `PowerModing::bootFailed()` at `0x208D0`.
After its GM-build and boot-state checks, that function increments its own
failure count and compares it with 3 at `0x20A73`. At least three reaches
`rebootSeeDealer()` at `0x20AAC`. `BootFailureTimer::trigger()` calls
`bootFailed()` at `0x241FE`. This counter is separate from the GHS lifecycle
counter in section 2.2.1; no induced failure or power cycle was performed.

Recovery's `show_return_to_dealer` option has getopt value `0x73`, whose
jump-table entry selects `0x2B3F26` and sets the local dealer flag.
The test at `0x2B487C` allows either this flag or BCB `boot-see-dealer`
to enter `wait_for_new_update()` at `0x2B48AC`, the USB-marker scan path.
Thus a dealer UI request through the internal command file can reach that
path without requiring the literal BCB command `boot-see-dealer`.

The shipped system `init` has `HandlePowerctlMessage()` at `0x13C4F0`.
Its inspected reboot-target comparisons and BCB writes handle the standard
recovery/bootloader/sideload/fastboot cases, with no dealer-specific mapping.
No direct `adb reboot see-dealer` or `adb reboot boot-see-dealer` alias was
established. Scans of extracted APK/JAR DEX contents and raw system/product/
vendor images found the dealer argument in `plmanager`, but no public shell
entry point to its private function. This does not establish that UID 2000
can write the protected internal command file or invoke the PAL/HAL route.

**Access permissions verified 2026-11-12:** vendor
`/vendor/etc/init/hw/init.full_gminfo37_gb.rc`, in `on post-fs-data`, assigns
`/update_cache` to `system:cache`, mode `0771`, and creates
`/update_cache/recovery` as `system:cache`, mode `0770`. Consequently an ordinary
UID-2000 shell without the cache supplementary group cannot traverse the recovery
directory or create its command file. `rebootSeeDealer()` gives its command file
`system:system` ownership and mode `0770`, also excluding that ordinary shell.
The file-context rule labels `/update_cache(/.*)?` as `update_cache_file`;
`plmanager` has explicit file write/create permissions, while no direct
shell-to-`update_cache_file` allow was found in the inspected CIL. A complete
attribute-expanded policy decision was not performed. Live ownership, groups,
ACLs, labels and enforcing state must be checked on the target before claiming
an exception to these shipped defaults. No live write was attempted.

---

## 5. VIP Communication and Reset

### 5.1 VIP-GHS Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VIP-GHS COMMUNICATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  VIP MCU (Renesas RH850)                                                     │
│         │                                                                    │
│         │ Serial UART (VipUART)                                             │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    GHS VIP_InitialTask                               │    │
│  │                                                                      │    │
│  │   IPC Connections:                                                   │    │
│  │   ├── ConnToVIP                    - Main VIP connection            │    │
│  │   ├── ConnToVip_Lifecycle_API      - Lifecycle control              │    │
│  │   ├── ConnToVIP_Audit_Crash        - Crash reporting                │    │
│  │   └── ConnToVIP_Audit_NewEvents    - Event reporting                │    │
│  │                                                                      │    │
│  │   VIP Message Handling:                                              │    │
│  │   ├── "Cache IPC msg: Index=%u, toVip=%u, clientMask=0x%02x"        │    │
│  │   ├── "Sending cached IPC message on CH%02u"                        │    │
│  │   ├── "Got IPC msg on invalid channel: %u"                          │    │
│  │   └── "[VIP] received bad HDLC sequence number from VIP"            │    │
│  │                                                                      │    │
│  │   VIP Reset Control:                                                 │    │
│  │   ├── "GHS: Initiating VIP reset"                                   │    │
│  │   ├── "GHS: Initiating immediate VIP reset"                         │    │
│  │   ├── "VipResetInitiated"                                           │    │
│  │   ├── "GHS: VMM: waiting for VIP system reset..."                   │    │
│  │   └── "VipBootCycle: 0x%02x"                                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

The "Android VIP Services" layer below this diagram in the original 2026-01-05
pass duplicated detail that §0.2 and §4.7.1 above now establish at instruction
level, and conflated two distinct dealer-recovery-reboot producers that write
similar-looking recovery arguments — they are not the same caller:

- `gm_protokey` (`/vendor/bin/gm_protokey`): writes `--wipe_data --reason=bcm_replacement`
  after a ProtoKey validation failure, then requests recovery reboot through
  PowerModing. See §0.2's code-attribution note (2026-11-14).
- `vendor.gm.powermode@1.0::IPowerModing`'s `plmanager`
  (`PowerModing::rebootSeeDealer()` / `PowerModing::bootFailed()`): writes
  `--show_return_to_dealer` after its own independent 3-failure counter. See §4.7.1.

Neither producer is the GHS lifecycle failed-boot counter in §2.2.1 or recovery's
own `boot_cycle_counter` file; do not merge these four counters.

---

## 6. Security Considerations

**History:** §6.1/§6.2 originally dated to the 2026-01-05 static-only pass and
described only coarse, qualitative risk categories (A/B metadata, BCB, trigger
files, OTA interface) without the confirmed live-ELK, MEC/ADB-cert or
dealer-recovery findings that the rest of this document now establishes at
instruction level. That coarse framing is folded into the dated findings below
rather than left standing beside them; §6.1's table keeps only the one item
(A/B metadata CRC32) that the later work has not superseded with a more specific
finding, since §3.1 already cross-references this section instead of repeating it.

### 6.1 Confirmed and assessed weaknesses (consolidated 2026-11-17)

| Area | Weakness/finding | Risk | Evidence / detail |
|------|----------|------|----------|
| **A/B Metadata** | CRC32 only, not a cryptographic signature | MEDIUM-HIGH for forcing a specific slot; GHS/AVB still verifies the loaded image itself | §3.1; `VMM: Warning: A/B metatdata CRC failure!` |
| **BCB / recovery command file** | Writable from Android by specific privileged callers only (not by an ordinary UID-2000 shell) | MEDIUM, bounded by permissions | §4.2, §4.7.1 (`system:cache 0770`/`system:system 0770`, UID-2000 shell excluded) |
| **MEC/ADB certificate gate** | Confirmed fail-closed bypass: VIP-reported MEC in [1,255] disables the GM cloud-certificate ADB requirement; MEC socket is unauthenticated plaintext | MEDIUM — depends on MEC value, not independently user-settable from Android; spoofable on an already-compromised guest | §2.3.7 (code-verified 2026-08-26, target readings 2026-11-12) |
| **ELK/Kernelflinger live entry** | Confirmed live CAN-driven (F000/8180) and native-Linux (HECI) entry into ELK fastboot; ELK reports `unlocked=yes`/`secure=no` as its own OEMLock device-state, not a platform authentication measurement; automatic SPI-ELK fallback exists when both GHS A/B images are blank | Access to ELK fastboot confirmed; unsigned-image/arbitrary-replacement acceptance NOT confirmed (early eMMC-image authentication gate rejects unsigned/incorrectly signed GHS replacements) | §2.3.2–§2.3.3 mega-section (2026-11-15/17) |
| **Dealer-recovery write path** | Two distinct Android-side producers (`gm_protokey`/bcm_replacement, `plmanager`/`rebootSeeDealer`) can request dealer/recovery boot; both write to a permission-gated file, not an open channel | LOW-MEDIUM, bounded by the same file permissions above | §0.2, §4.7.1, §5.1 |
| **Trigger files (USB markers, protokey)** | File-based triggers (`gm_reboot_normal`, `gm_capture_log`, protokey recovery) | LOW-MEDIUM; ownership/ACL and recovery-only reachability checked | §4.1, §4.5–§4.6 |
| **OTA interface** | Signature/AVB-protected; no accepted-unsigned-package path established | LOW | §3.3, §3.4 |
| **IPC channels** | Multiple exposed `/dev/ghs/*` nodes and VMM IPC connections (textlog/audit/cal/camera/ota-isys/etc.) | Unassessed beyond inventory — no exploitable validation gap demonstrated | §2.4 |

None of the rows above establish a confirmed guest escape, GHS privilege
elevation, accepted unsigned normal-boot image, or persistent unlock; see §0.1's
evidence-limits note and §2.3.3's root-filesystem-boundary caution, which both
apply across this table.

---

## 7. Related Files and Services

### 7.1 Android Init Scripts

| File | Purpose |
|------|---------|
| `init.protokey.rc` | gm_protokey service (vendor) |
| `init.protokey_recovery.rc` | Protokey recovery service |
| `init.bxtp_gm.rc` | Main GM init script |
| `init.trusty-ghs.rc` | GHS Trusty integration |

### 7.2 Key Binaries

| Binary | Location | Purpose |
|--------|----------|---------|
| `gm_protokey` | `/vendor/bin/` | EEPROM security handling |
| `gm_protokey_recovery` | `/system/bin/` | Protokey recovery |
| `GHSCalibrations` | `/vendor/bin/` | GHS calibration service |
| `cmd_fw_update_vendor` | `/vendor/bin/` | Firmware update tool |

### 7.3 Key Directories

| Directory | Purpose |
|-----------|---------|
| `/update_cache/` | Update staging area |
| `/update_cache/recovery/` | Recovery command staging |
| `/update_cache/security/` | Security file staging |
| `/data/gmprotokey/` | Protokey data |
| `/data/gmprotokey/trigger/` | Trigger files |
| `/calibration/` | Calibration data |

---

## Appendix A: GHS Boot Functions

**Index only — see §1.1 and §3.1 for the analysis.** This appendix condenses the
2026-01-05 boot-sequence/A/B-boot call trees already given in full in §1.1 and
§3.1 above, for grep convenience; it adds no evidence beyond those sections and
predates the 2026-08/11 live-boot findings elsewhere in this document.

```
Initialization Sequence:
├── BSP_InitializeOnBootCpu
├── ASP_PreCrtInitializeBootstrap
├── ASP_VMX_InitializeOnBootCpu
├── ASP_VTD_Init
├── BSP_Initialize
├── BSP_BootSecondaryCpus
├── SetupBootTables
│   ├── InitializeTheAddressSpaceTable
│   ├── InitializeTheTaskTable
│   └── InitializeTheODGTable
└── RunInitialTasks

VMM Android Boot:
├── CheckRecoveryMode
├── Read A/B metadata
├── Load vbmeta
├── Verify vbmeta signature
├── Load boot partition
├── Verify boot image
├── Check rollback index
├── ASP_VMX_SetGuestKernelAddr
└── ASP_RunGuestVM
```

## Appendix B: Error Messages Reference

**Index only — see §1, §2.2, §3.3, §3.4 for the analysis.** This appendix is a
flat grep-friendly list of literal strings already individually cited and
analyzed in the referenced sections; it adds no evidence of its own.

```
Boot Errors:
├── "VMM: ERROR: failed to read A/B metadata from 'misc'"
├── "VMM: A/B Boot: ERROR: no valid boot slot"
├── "VMM: ERROR: no vbmeta partition found (slot %s)"
├── "VMM: Error: vbmeta signing key does not match known valid key"
├── "VMM: vbmeta: image verification failed!"
├── "VMM: ERROR: rollback index is too old"
├── "VMM: Failed to verify slot %s"
└── "VMM: Error: Failed to read BCB"

Lifecycle Errors:
├── "GHS: [LIFECYCLE] Lost Android SoH - rebooting"
├── "GHS: [LIFECYCLE] Android failed to boot (count=%lu)"
├── "GHS: [LIFECYCLE] Guest failed to reboot after panic"
└── "GHS: [LIFECYCLE] Failed to write Lifecycle settings to EMMC"

VIP Errors:
├── "GHS: Initiating VIP reset"
├── "[VIP] received bad HDLC sequence number from VIP"
└── "GHS: VMM: waiting for VIP system reset..."

OTA Errors:
├── "Bad command length for OTA command."
├── "GHS: Error: ABL update command failed: %d"
└── "GHS: Error: CSE prepare update HECI command failed: %d"
```

---

## Open conflicts

This document's own evidence is internally reconciled throughout via inline
"Corrected YYYY-MM-DD" notes (see §2.3.2, §2.3.3, §2.3.6, §2.3.7, §4.2, §4.4,
§4.5.2, §4.7 above); none of those are left as stale dangling errata. Two items
that touch this document are owned and tracked elsewhere, not here:

1. **MEC value semantics** (nonzero/per-unit MEC meaning "bypassed/unlocked" vs.
   "production/locked") — this document's §2.3.6–§2.3.7 contribute the live
   per-unit MEC table (Y175=244, Y177=0, Y181 bench=207, Y181 target=241,
   Y181B=227, Y175 VIP UART=0xFF) and the code-verified MEC-gated ADB
   certificate-bypass chain, but does not itself settle the general semantic
   rule across builds. Tracked in GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md's
   and EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md's own Open Conflicts.
2. **VMM1/.vmm1 task-code bitness** (32-bit ELF class vs. disassembled-64-bit
   task code) — surfaced during the §0.4 tool-setup history absorbed from the
   retired `GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md`. Tracked in
   VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md's Open Conflicts; the §0.4 pivot to
   `elk_inner.elf` as the binary holding the real AVB guards answers a different
   question and does not resolve this one.

---

**Document Version:** 2.0 (consolidated 2026-11-17)
**Analysis Method:** Static binary analysis (strings, radare2, Capstone, Ghidra/PyGhidra
headless decompilation, symbol/relocation/xref analysis), init script analysis, Unicorn/QEMU
emulation, native x86 build reproduction, and live-hardware verification (CAN/UART/HECI/MEI/USB,
T1 SSH, read-only CPU-firmware-window and eMMC/RPMB readback). The 2026-01-05 baseline used
static-only methods; §0.1–§0.4, §2.2.1–§2.3.7 and §4.2–§4.7.1 add the later dynamic/live-hardware
layer dated throughout the body.
**Classification:** Security Research
