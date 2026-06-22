# GHS INTEGRITY Boot, Update, and Recovery Analysis

**Date:** 2026-01-05
**Binary Analyzed:** SOC_HOSTOS (85098662)
**OS Version:** INTEGRITY IoT 2020.18.19
**Platform:** Intel Apollo Lake (Broxton) / GM-i35

> Companion doc: `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` is the full GHS reverse-engineering
> inventory (tasks, IPC, VMM, drivers, attack surface, and the consolidated privacy
> assessment in its §15). This document focuses on boot/update/recovery; the two are
> complementary (neither supersedes the other).

---

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

### 2.3 Special Boot Modes

| Mode | Trigger | String Evidence | Purpose |
|------|---------|-----------------|---------|
| **Normal A/B** | Default | `A/B Boot Slot: boot%s` | Standard boot to active slot |
| **Recovery** | BCB command | `boot-recovery` | Android recovery mode |
| **See-Dealer** | Service flag | `boot-see-dealer`, `GHS: [LIFECYCLE] Booting 'see-dealer' mode` | Dealer diagnostic mode |
| **ELK** | Emergency | `GHS: [LIFECYCLE] Got request to boot to ELK`, `BootELKWaitForRespSent` | Emergency/diagnostic kernel |
| **Diagnostic** | Service tool | `Diagnostic channel active` | Low-level diagnostics |

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

### 4.2 Reboot Trigger: /update_cache/recovery/command

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REBOOT TRIGGER FILE MECHANISM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRIMARY TRIGGER FILE:                                                       │
│  /update_cache/recovery/command                                              │
│                                                                              │
│  From gm_protokey binary strings:                                            │
│  ├── "Waiting for update in %s"                                             │
│  ├── "/update_cache/recovery"                                               │
│  ├── "/update_cache/recovery/command"  ← TRIGGER FILE                       │
│  ├── "rebooting into recovery"                                              │
│  ├── "system rebooting"                                                     │
│  ├── "warm_reboot"                                                          │
│  ├── "Detected Warm-reboot"                                                 │
│  └── "reboot status %d"                                                     │
│                                                                              │
│  TRIGGER FLOW:                                                               │
│                                                                              │
│  ┌──────────────────────┐                                                    │
│  │   Android Process    │                                                    │
│  │   (Update/Recovery)  │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             │ Write command to trigger file                                  │
│             ▼                                                                │
│  ┌──────────────────────────────────────────┐                                │
│  │  /update_cache/recovery/command          │                                │
│  │  Contents determine reboot type:         │                                │
│  │  ├── Empty or normal → Normal reboot     │                                │
│  │  └── Recovery command → Recovery boot    │                                │
│  └──────────────────────────────────────────┘                                │
│             │                                                                │
│             │ gm_protokey monitors file                                      │
│             ▼                                                                │
│  ┌──────────────────────┐                                                    │
│  │    gm_protokey       │                                                    │
│  │    Service           │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             ├── Read file content                                            │
│             ├── Validate command                                             │
│             │                                                                │
│             │ Set property:                                                  │
│             │ sys.shutdown.requested                                         │
│             ▼                                                                │
│  ┌──────────────────────┐                                                    │
│  │  Android Init        │                                                    │
│  │  (sys.powerctl)      │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             │ Initiate shutdown                                              │
│             ▼                                                                │
│  ┌──────────────────────┐                                                    │
│  │  GHS Lifecycle       │                                                    │
│  │  Manager             │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             ├── SendShutdownRequest                                          │
│             ├── WaitForGuestShutdownPreparationDone                          │
│             ├── WaitForGuestOff                                              │
│             ▼                                                                │
│  ┌──────────────────────┐                                                    │
│  │  DoACPIShutdown /    │                                                    │
│  │  BSP_Reset           │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             │ System reset                                                   │
│             ▼                                                                │
│  ┌──────────────────────┐                                                    │
│  │  GHS Boot            │                                                    │
│  │  (reads BCB/command) │                                                    │
│  └──────────────────────┘                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

### 4.4 USB Trigger Files (gm_update_engine)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    USB TRIGGER FILE MECHANISM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  IMPLEMENTATION: gm_update_engine (Android service, NOT GHS)                 │
│                                                                              │
│  Service: /vendor/bin/hw/gm_update_engine                                    │
│           class hal, user root                                               │
│                                                                              │
│  USB Detection Flow:                                                         │
│  ┌──────────────┐                                                            │
│  │  USB Drive   │                                                            │
│  │  Inserted    │                                                            │
│  └──────┬───────┘                                                            │
│         │                                                                    │
│         │ Kernel detects USB storage                                         │
│         ▼                                                                    │
│  ┌──────────────────────┐                                                    │
│  │  Android vold mounts │                                                    │
│  │  /mnt/media_rw/...   │                                                    │
│  └──────┬───────────────┘                                                    │
│         │                                                                    │
│         │ "USB mount called"                                                 │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  gm_update_engine scans USB root for trigger files:                   │   │
│  │                                                                       │   │
│  │  ├── gm_reboot_normal       → Exit failed screen, boot normal        │   │
│  │  │   (base64: Z21fcmVib290X25vcm1hbA==)                               │   │
│  │  │                                                                    │   │
│  │  ├── gm_usb_ignore_battery  → Skip battery level check               │   │
│  │  │                                                                    │   │
│  │  ├── gm_usb_auto_install    → Auto-install update without prompt     │   │
│  │  │                                                                    │   │
│  │  └── *.mnf files            → Update package manifests               │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         │ Trigger detected                                                   │
│         ▼                                                                    │
│  ┌──────────────────────┐                                                    │
│  │  Action Executed     │                                                    │
│  │  (reboot/update/etc) │                                                    │
│  └──────────────────────┘                                                    │
│                                                                              │
│  IMPORTANT: This is Android-side (gm_update_engine), NOT GHS hypervisor     │
│  GHS does NOT directly monitor USB for trigger files                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.5 Known USB Trigger Files

| Filename | Base64 Encoding | Location | Handler | Function | Empty OK? |
|----------|-----------------|----------|---------|----------|-----------|
| `gm_reboot_normal` | `Z21fcmVib290X25vcm1hbA==` | USB root | gm_update_engine | Exit failed/dealer screen, boot normal | Yes |
| `gm_usb_ignore_battery` | - | USB root | gm_update_engine | Skip battery level check during update | Yes |
| `gm_usb_auto_install` | - | USB root | gm_update_engine | Auto-install update without user prompt | Yes |

### 4.5.1 Filename Structure Requirements

```
USB Drive Root Directory:
├── gm_reboot_normal          ← Exact name, case-sensitive
├── gm_usb_ignore_battery     ← Exact name, case-sensitive
├── gm_usb_auto_install       ← Exact name, case-sensitive
└── [update_package.mnf]      ← Optional update files
```

**Requirements:**
- **Exact filename match** - must be exact, case-sensitive
- **File content** - can be empty (0 bytes)
- **Location** - must be in USB root directory (not in subdirectory)
- **Filesystem** - USB must be FAT32/vFAT (what vehicles expect)
- **No extension** - no `.txt` or other extension

### 4.5.2 Why Base64 Encoding Exists

The base64 equivalent (`Z21fcmVib290X25vcm1hbA==`) decodes to the same filename:
```bash
echo "Z21fcmVib290X25vcm1hbA==" | base64 -d
# Output: gm_reboot_normal
```

This is likely used in:
- Internal documentation/obfuscation
- Logging/debugging
- Possible alternative trigger mechanism

Both the plain filename and base64-encoded version should work as filenames.

### 4.5.3 Usage Instructions

1. Format USB drive as FAT32/vFAT
2. Create empty file with exact trigger filename in USB root
3. Insert USB into vehicle head unit
4. gm_update_engine detects file on "USB mount called"
5. Corresponding action is triggered

### 4.5.4 Security Notes

- Does NOT bypass GHS rollback protection
- Does NOT bypass AVB signature verification
- Only affects update engine behavior, not core security
- Provides recovery path from failed update screens

### 4.6 Trigger Files Summary Table

| Trigger File/Path | Purpose | Handler | Effect |
|-------------------|---------|---------|--------|
| **USB: `gm_reboot_normal`** | Exit error screen | gm_update_engine (Android) | Normal reboot |
| **USB: `gm_usb_ignore_battery`** | Skip battery check | gm_update_engine (Android) | Allow low-battery update |
| **USB: `gm_usb_auto_install`** | Auto-install | gm_update_engine (Android) | No confirmation dialog |
| `/update_cache/recovery/command` | Reboot trigger | gm_protokey (Android) | Normal or recovery reboot |
| `/data/gmprotokey/trigger/*` | Protokey recovery | gm_protokey_recovery (Android) | Install recovery protokey |
| `/sys/kernel/capsule/capsule_name` | Firmware recovery | Kernel | ABL firmware update + reboot |
| `sys.powerctl` property | System reboot | Android init | Immediate system reboot |
| `sys.shutdown.requested` property | Shutdown request | gm_protokey | Graceful shutdown |
| BCB (misc partition) | Boot mode | GHS VMM | Recovery/normal/ELK boot |

---

## 4.7 Error Screen Display Architecture

### Where Are Error Screens Displayed?

**The failed/see-dealer screens are displayed by Android, NOT by GHS.**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ERROR SCREEN DISPLAY ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GHS INTEGRITY HYPERVISOR                                                    │
│  ├── Knows about boot modes:                                                │
│  │   └── "GHS: [LIFECYCLE] Booting 'see-dealer' mode"                       │
│  ├── Controls boot flow and mode selection                                  │
│  ├── Does NOT render UI/graphics for error screens                          │
│  └── Passes boot mode info to Android                                       │
│                                                                              │
│                              │                                               │
│                              ▼                                               │
│                                                                              │
│  ANDROID (Guest VM)                                                          │
│  ├── Receives boot mode from GHS                                            │
│  ├── gm_update_engine handles update UI                                     │
│  │   ├── Displays "Update Failed" screen                                    │
│  │   ├── Displays "See Dealer" screen                                       │
│  │   ├── Monitors USB for trigger files                                     │
│  │   └── Can exit error state via gm_reboot_normal                         │
│  └── /sbin/slideshow displays verity warnings                              │
│      └── "exec u:r:slideshow:s0 -- /sbin/slideshow warning/verity_red_1"   │
│                                                                              │
│  EVIDENCE:                                                                   │
│  1. USB trigger files work via gm_update_engine (Android service)           │
│  2. If GHS displayed screens, Android couldn't detect USB trigger files     │
│  3. Slideshow binary is in Android recovery, not GHS                        │
│  4. Error strings in gm_update_engine confirm UI handling                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Boot Mode vs Display Responsibility

| Aspect | GHS Responsibility | Android Responsibility |
|--------|-------------------|------------------------|
| Mode Selection | ✓ Determines boot mode | - |
| Mode Signaling | ✓ Sends mode to Android | - |
| Error Detection | ✓ Detects boot failures | - |
| Screen Rendering | - | ✓ Displays error UI |
| USB Monitoring | - | ✓ gm_update_engine |
| Trigger File Detection | - | ✓ gm_update_engine |
| User Interaction | - | ✓ Touch/button handling |

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
