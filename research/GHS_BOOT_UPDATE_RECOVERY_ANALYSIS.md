# GHS INTEGRITY Boot, Update, and Recovery Analysis

**Initial analysis:** 2026-01-05
**Consolidated findings updated:** 2026-11-12
**Binary Analyzed:** SOC_HOSTOS (85098662)
**OS Version:** INTEGRITY IoT 2020.18.19
**Platform:** Intel Apollo Lake (Broxton) / GM-i35

> Consolidated findings and source conventions: §0. Distinct inventory owners are linked there.

---

## 0. Scope, ownership and evidence conventions

**Canonical repository path:** `gminfo_resources/research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`.

This document owns the consolidated Y181B GHS/recovery investigation: primary
binary provenance, security-candidate limits, guest/dealer/fastbootd/ELK
boundaries, MEC and ADB privilege distinctions, recovery arguments, encoded USB
markers, log capture and dealer-wipe behavior. Update the owning section here;
other documents link here instead of carrying independent copies.

| Topic | Owning section |
|---|---|
| Binary fingerprints, extraction boundaries, debugger and CVE evidence | §0.1 |
| Y181B recovery USB export provenance, member fingerprints and time limits | §0.2 |
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
driver, device-grant and privacy inventories. The [EEPROM audit](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
owns EEPROM layout and VIP reverse engineering. The [update-stack reference](../platform/ota_update_stack.md)
owns the AAOS updater/Binder interface. Distinct inventories stay with those owners.
No complete live ELK transition, guest escape or accepted custom wipe package
is established by this static evidence.

### 0.1 Y181B binary provenance and security evidence (2026-11-12)

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
the [update-stack reference](../platform/ota_update_stack.md#y181b-recovery-export-evidence-2026-11-12),
and the [vehicle calibration baseline](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12).

**Recovery boot ledger across the retained `last_log` series (directly read from the second export, 2026-11-12):**

| Rotation | Recovery boot counter | Arguments / reason | `Dump log to USB` |
|---|---:|---|---|
| `.10`, `.9` | 47, 48 | `--wipe_data --reason=bcm_replacement` (from `/update_cache/recovery/command`) | no |
| `.8` | 49 | `--wipe_data --reason=com.gm.domain.server.delayed,2026-11-07T12:45:35Z` (boot message; recovery RTC read Sat Nov 7 2026 21:45, unreconciled with the 12:45Z stamp) | no |
| `.7` | 50 | `--wipe_data --reason=MasterClearConfirm,2026-11-10T15:54:27Z` (boot message; `unrecognized option` printed for the reason) | no |
| `.6`, `.5`, `.4` | 51, 52, 53 | none recorded | no |
| `.3`, `.2` | 54 | `--show_return_to_dealer`; `.2` also dumps | `.2` yes |
| `.1`, current | 55 | `--show_return_to_dealer`; current dumps | current yes |

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
│  POTENTIAL WEAKNESS:                                                         │
│  A/B metadata uses CRC32 only, not cryptographic signature                   │
│  "VMM: Warning: A/B metatdata CRC failure!"                                  │
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
│         │                                                                    │
│         │ IPC to Android                                                     │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Android VIP Services                              │    │
│  │                                                                      │    │
│  │   ├── gm_protokey (/vendor/bin/gm_protokey)                         │    │
│  │   │   └── Handles EEPROM-derived security state                     │    │
│  │   │                                                                  │    │
│  │   └── Power Mode Service                                             │    │
│  │       └── vendor.gm.powermode@1.0::IPowerModing                     │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Security Considerations

### 6.1 Potential Weaknesses Identified

| Area | Weakness | Evidence |
|------|----------|----------|
| **A/B Metadata** | CRC32 only (no signature) | `VMM: Warning: A/B metatdata CRC failure!` |
| **BCB Access** | Writable from Android | `misc` partition accessible |
| **Trigger Files** | File-based triggers | `/update_cache/recovery/command` |
| **IPC Channels** | Multiple exposed interfaces | `/dev/ghs/*` devices |

### 6.2 Attack Surface Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BOOT/UPDATE ATTACK SURFACE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. A/B METADATA MANIPULATION                                                │
│     ├── Risk: MEDIUM-HIGH                                                    │
│     ├── Vector: Modify misc partition A/B metadata                          │
│     ├── Protection: CRC32 only (weak)                                       │
│     └── Impact: Force boot to specific slot                                 │
│                                                                              │
│  2. BCB COMMAND INJECTION                                                    │
│     ├── Risk: MEDIUM                                                         │
│     ├── Vector: Write recovery command to BCB                               │
│     ├── Protection: Partition permissions                                    │
│     └── Impact: Force recovery/special boot modes                           │
│                                                                              │
│  3. TRIGGER FILE MANIPULATION                                                │
│     ├── Risk: LOW-MEDIUM                                                     │
│     ├── Vector: Create/modify trigger files                                 │
│     ├── Protection: File ownership checks                                    │
│     └── Impact: Trigger reboots, protokey recovery                          │
│                                                                              │
│  4. OTA INTERFACE                                                            │
│     ├── Risk: LOW (signature protected)                                      │
│     ├── Vector: /dev/ghs/ota-isys                                           │
│     ├── Protection: Package signatures, AVB                                  │
│     └── Impact: Limited without valid signatures                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

**Document Version:** 1.0
**Analysis Method:** Static binary analysis (strings, radare2), init script analysis
**Classification:** Security Research
