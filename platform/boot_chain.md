# GM Info 3.7 Boot Chain

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

## Boot Phases

The GM Info 3.7 uses a 5-phase boot sequence from VIP MCU power-on through Android verified boot:

```
1. VIP MCU (RH850) — power sequencing, CAN init, SoC power-on
2. Intel CSE — hardware root of trust, measured boot
3. SOC_ABL — Intel bootloader, loads GHS
4. GHS INTEGRITY — hypervisor init, AVB verification of Android images
5. Android AVB — verified boot into AAOS
```

### GHS Kernel Init Sequence (Phase 4 Detail)

Within Phase 4, the GHS INTEGRITY kernel performs the following initialization on the boot CPU before launching any tasks:

```
BSP_InitializeOnBootCpu
  → ASP_PreCrtInitializeBootstrap
  → ASP_VMX_InitializeOnBootCpu       (VT-x enable, VMCS setup, EPT page tables)
  → ASP_VTD_Init                      (IOMMU init, DMA remapping)
  → BSP_Initialize
  → BSP_BootSecondaryCpus             (cores 1-3 via INIT-SIPI sequence)
  → SetupBootTables
  → RunInitialTasks                   (launch all GHS tasks)
```

### GHS Task Inventory (RunInitialTasks)

All tasks launched at `RunInitialTasks` during GHS boot:

**Core:**
- `VMM1_InitialTask` — Android virtual machine manager (guest VM)
- `Lifecycle_InitialTask` — Android health monitoring, shutdown coordination
- `VIP_InitialTask` — VIP MCU communication (HDLC over /dev/ttyS1). **Confirmed (2026-09, real Y181B
  kernel `.config` extraction): no `N_HDLC` line discipline is compiled into the Android guest kernel at
  all.** The VIP/RH850 HDLC framing terminates below the Android guest (GHS-side task shown here); on
  the Android side the link is a **userspace** protocol — `IPCServer` fans the channel into per-channel
  Unix sockets (`/vendor/etc/ipc4.cfg`) that `libipc.so` clients connect to (see
  [`emulator.md`](emulator.md#un-stub-roadmap--using-gms-real-files-verified-vs-the-real-radio-adb-dumps)).
  Not a kernel driver dependency.
- `OTA_InitialTask` — Over-the-air update coordination

**Hardware:**
- `Camera_InitialTask` — IPU4 camera pipeline
- `Audio_InitialTask` — HDA (High Definition Audio) controller
- `GPU_InitialTask` — Gen9 GPU (i915)
- `Chimes_InitialTask` — Chime/alert audio playback
- `Dirana_InitialTask` — Dirana tuner/audio DSP
- `DisplayI2C_InitialTask` — Display controller via I2C

**Security:**
- `TEE_Keymaster` — Hardware-backed key generation/storage
- `TEE_HW_Crypto` — Hardware cryptographic operations
- `TEE_Storage` — Secure storage via RPMB (Replay Protected Memory Block)

**Other:**
- `Calibrations_InitialTask` — Vehicle calibration data
- `Lines_InitialTask` — Guideline/overlay rendering

---

## Special Boot Modes

GHS supports multiple boot modes selected via BCB (Boot Control Block) or external triggers:

| Mode | Trigger | Description |
|------|---------|-------------|
| 1. Normal A/B | Default | Standard A/B verified boot into Android |
| 2. Recovery | BCB `boot-recovery` | Recovery mode (no separate recovery partition — uses boot image) |
| 3. See-Dealer | BCB `boot-see-dealer` | Service required screen, directs user to dealer |
| 4. ELK | GHS lifecycle recovery target | Fallback boot target for diagnostics/recovery |
| 5. Diagnostic | Service tool | Factory/dealer diagnostic mode |

**Recovery fastbootd is separate from ELK** (verified 2026-11-12): Y181B
recovery recognizes `boot-fastboot`/`--fastboot`, sets `sys.usb.config=fastboot`,
and enters a persistent wait. This establishes a protocol mode, not a developer
build or root shell. [Code and init rules](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#231-recovery-fastbootd-path-verified-2026-11-12).


---

**Execution boundary (2026-11-12):** VMM maps both `boot-recovery` and
`boot-see-dealer` into the Linux/Android guest recovery flag. Ordinary recovery,
dealer UI and recovery-fastbootd therefore must not be classified as three
bare-metal environments. ELK's reciprocal lifecycle/OTA IPC and HECI request
are now traced, as is lifecycle's ACPI driver binding: its callback disables
interrupts, flushes caches, synchronizes four CPUs, writes the power-control
port and halts. This is a platform power-state transition, not just a guest
selection. ME/CSE acceptance, the next boot and GHS residency during actual
ELK execution remain unproven.
[Instruction-level evidence and limits](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#233-recovery-execution-boundary-and-mode-selection-verified-2026-11-12).

## Boot Timing

Approximate timing from kernel start to screen (~24.5s total):

| Milestone | Time |
|-----------|------|
| Kernel → zygote | ~8s |
| System server ready | ~15s |
| Screen enabled | ~24.5s |

- 13 `Davey!` events during boot (all SystemUI), none during streaming
- Boot performance is dominated by system server initialization and GM service startup

---

## Boot Configuration

Kernel cmdline (set by GHS via `ASP_VMX_SetGuestKernelAddr`):

```
clocksource=tsc tsc=reliable
i915.avail_planes_per_pipe=0x000003
androidboot.diskbus=1c.0
androidboot.trustyimpl=-ghs
androidboot.product.hardware.sku=gv221
```

Additional cmdline values set during AVB verification (see below):
`slot_suffix`, `verifiedbootstate`, `vbmeta.avb_version=1.1`, `hash_alg=sha256`

---

## AVB Verification

AVB (Android Verified Boot) is performed by GHS `VMM1_InitialTask`, NOT by Android itself:

```
1. CheckRecoveryMode()          — reads BCB from misc partition
2. A/B slot selection            — misc@0x800, CRC32 only (no crypto signature)
3. Load vbmeta                   — AVB0 magic, version 1.1, avbtool 1.2.0
                                   (2026-09-10: byte-confirmed stock upstream libavb —
                                   offset 0 = `41 56 42 30` = `AVB_MAGIC`, RSA2048/SHA256,
                                   flags=0x00000000 i.e. verification NOT disabled, zero
                                   GM-specific fields)
4. Verify signing key            — RSA-2048 from .oemkeys ELF section in SOC_ABL
5. Check rollback index          — GHS independent counter in misc
6. Load boot partition           — verify hash against vbmeta descriptor
7. Set kernel cmdline            — slot_suffix, verifiedbootstate,
                                   vbmeta.avb_version=1.1, hash_alg=sha256
8. ASP_VMX_SetGuestKernelAddr   → ASP_RunGuestVM (launch Android)
```

> **[C] live-Y175 2026-10-05 — runtime posture CONFIRMED (not the internals).** Against a running
> Y175 radio (`W213E-Y175.5.2-SIHM22B-383.1`, `/tmp/radio_audit/20261005_232227/raw/`) the
> live-observable end-state of this chain is confirmed: `ro.boot.verifiedbootstate=green`,
> `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `sys.oem_unlock_allowed=0`,
> `ro.oem_unlock_supported=` (empty), `ro.debuggable=0`, `ro.secure=1`, `ro.adb.secure=1`,
> `ro.build.type=user`, tags `release-keys` (security_props). vbmeta: `ro.boot.avb_version=1.2` /
> `ro.boot.vbmeta.avb_version=1.1`, `hash_alg=sha256`, `size=3328`,
> `digest=76b736eaf87d186de5f03f08176b67ae2cdcf91130b4350b328b0876c00bb585` (props). SELinux
> **Enforcing** at runtime (00_whoami; all 179 captured avc lines `permissive=0`) even though
> `ro.boot.selinux=permissive` is present in the kernel cmdline (props) — the cmdline token is
> overridden by the enforcing-init build, consistent with VERIFICATION.md. **UNVERIFIABLE-FROM-LIVE
> (shell uid 2000, no device access to earlier stages):** steps 1-6 internals — the `.oemkeys`
> RSA-2048 signing key, the AVB0/vbmeta parse, the CRC32 slot metadata, and the GHS rollback
> counter in `misc`. `verity.txt` captured only `green`/`1` and an empty `===VERITY` section — no
> dm-verity status line — so runtime dm-verity state is NOT independently evidenced by this capture.

> **[C] live-Y181B 2026-11-12 — same end-state on the current build (adb getprop, directly read).**
> `W231E-Y181.3.2-SIHM22B-499.3`, Android 12/SDK 32, patch `2025-06-05`, `ro.bootloader=2344`,
> `ro.boot.verifiedbootstate=green`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.flash.locked=1`,
> `ro.boot.slot_suffix=_a`, `ro.boot.product.hardware.sku=gv221`, `ro.boot.vbmeta.avb_version=1.1`,
> `ro.boot.avb_version=1.2` (the "AVB 1.1" shorthand applies only to the vbmeta-side token), kernel
> `4.19.305-240125T145315Z-gf1edde901aa7`. The kernel command lines retained in the boot logs and recovery
> `last_kmsg*` also carry `ABL.secureboot=1` (386 hits -- [2026-11-12: count not reproduced; ~188 per archive, 376 if the duplicate export is double counted; the token still appears only in retained kernel-log cmdlines, live getprop is empty]), `androidboot.selinux=permissive`/`enforcing=0` (early tokens; the same cmdlines ALSO carry a later
> `enforcing=1`/`androidboot.selinux=enforcing` pair -- corrected 2026-11-12; runtime is Enforcing, "later pair wins" is inferred; see
> [`security.md`](security.md)), `androidboot.trustyimpl=-ghs`, `androidboot.force_normal_boot=1`, `androidboot.bootreason=cold|reboot`;
> `getprop ro.boot.ABL.secureboot` is empty at runtime, so that flag is cmdline-only.
> **Slot history:** the recovery kernel logs retained on the radio (31 boots, `last_kmsg`..`.30`) read
> oldest->newest A x2, B x5, A x7, B x5, A x12 -- the radio did alternate slots (two B episodes in the window;
> the 2026-09-28 recovery install flipped active slot 1 -> 0), currently on A with `slot_switched=N`.
> Active slot per the update-engine logs (2026-11-12; `rg -n 'Loaded metadata from source slot' ~/Desktop/gminfo37_update_cache_FORENSIC_LLM.txt`, forensic ref 'Active slot per engine log'): A (from 02-03) -> B 02-10 10:45:17 -> A 04-30 20:46:48 -> B 08-25 07:09:17 -> A 09-28 17:33:45 -> still A at 11-12 13:10; four changes, matching the four USB installs. (Superseded 2026-11-12: the earlier 'cannot be derived from these exports' wording was wrong; the retained recovery kernel logs alone still cover only 31 boots.)

### A/B Metadata Structure

Located at `misc` partition (`vda9`) offset `0x800`. **CRC32-only protection** (no crypto signature on slot metadata).

```c
// A/B metadata at misc+0x800
struct ab_metadata {
    uint8_t  magic[4];          // "\0AB0" (misc/BCB slot-metadata magic — distinct from
                                 // the "AVB0" vbmeta magic above; corrected 2026-09-10,
                                 // GitHub issue #1 @DymOK93, confirmed by vbmeta.img byte
                                 // analysis: offset 0 = 41 56 42 30 = stock libavb AVB_MAGIC)
    uint8_t  version;           // metadata version
    uint8_t  reserved[3];
    struct {
        uint8_t  priority;
        uint8_t  tries_remaining;
        uint8_t  successful_boot;
        uint8_t  reserved;
    } slot_info[2];             // slot A, slot B
    uint32_t crc32;             // CRC32 of above fields
};
```

**BCB (Boot Control Block)** at `misc` offset `0x000`:

```c
struct bootloader_message {
    char command[32];    // "boot-recovery", "boot-see-dealer", etc.
    char status[32];
    char recovery[768];
    char stage[32];
};
```

**Note:** GHS contains a typo in its error string: `"metatdata"` (sic) when referring to this structure.

---

## Rollback Protection

- GHS maintains an independent rollback counter in the `misc` partition
- **Y181 → Y177 downgrade:** BLOCKED by GHS rollback counter
- Rollback protection is enforced at the hypervisor level, independent of Android's own AVB rollback index
- Both Y177 and Y181 `vbmeta` images have `rollback_index=0` — GHS maintains its OWN independent counter in the `misc` partition, separate from Android AVB rollback indices
- **Tested:** Y181 → Y177 downgrade FAILS (partitions are written successfully, but GHS rejects at boot; A/B fallback reverts to previous slot)
- **Tested:** Y181 → Y181 reinstall SUCCEEDS (same version, passes rollback check)
- `"version check disabled"` in OTA manifest only affects the write phase — GHS enforcement at boot is independent

---

## Signing Hierarchy

Boot trust is established through a 4-level signing chain:

| Level | Component | Signer |
|-------|-----------|--------|
| 1 | VIP (RH850 firmware) | GM |
| 2 | Intel ABL (SOC_ABL bootloader) | Intel / GM |
| 3 | GHS INTEGRITY (hypervisor) | Green Hills / GM |
| 4 | Android AVB (vbmeta keys, GSI keys q/r/s) | GM (RSA-2048 in .oemkeys) |

---

## Update Engine

- **Primary:** `gm_update_engine` + Red Bend UA (`/vendor/bin/rb_ua`)
- **Image format:** Raw partition images (all RAW, not delta)
- **Extension functions:** `gmext` functions for GM-specific update logic
- A/B slot switching is coordinated between GHS and Android boot control HAL

### Manifest Command Sequence

Updates are executed in 5 phases via `gmext` extension functions:

```
Phase 1 — Direct eMMC writes:
  gmext.write_emmc_image("23", boot)     # partition 23 = boot image
  extract vbmeta, acpio, bootloader      # from update package

Phase 2 — ECU updates via VIP MCU:
  gmext.update_ecu("71", VIP_BOOT)
  gmext.update_ecu("1",  VIP_APP)
  gmext.update_ecu("21", HOSTOS)
  gmext.update_ecu("72", ABL)

Phase 3 — Slot switch:
  gmext.switch_slot()                    # A↔B toggle in misc metadata

Phase 4 — Dynamic partition extraction:
  gmext.extract_logical_partition(system  ~3.0GB)
  gmext.extract_logical_partition(vendor  ~445MB)
  gmext.extract_logical_partition(product ~2.5GB)

Phase 5 — Peripheral firmware:
  TUNER, ETH_SWITCH, GPS, SXM
```

Red Bend UA (`/vendor/bin/rb_ua`) handles OTA delivery from GM Cloud.

---

## Partition Layout

26 partitions with A/B redundancy, exposed as virtio block devices (`vda1`-`vda26`):

### Full Partition Map

| Device | Partition | Description |
|--------|-----------|-------------|
| vda1/2 | ghs_isys_a/b | GHS hypervisor image |
| vda3 | ghs_storage | GHS persistent storage |
| vda4 | ghs_abl_update | ABL update staging area |
| vda5/6 | bootloader_a/b | Intel ABL bootloader |
| vda7/8 | boot_a/b | Android kernel + ramdisk |
| vda9 | misc | GHS rollback counter, BCB, A/B metadata |
| vda10/11 | vbmeta_a/b | AVB verification metadata |
| vda12 | metadata | ext4, Android metadata |
| vda13 | super | 8.6GB dynamic (system, vendor, product via dm-verity) |
| vda14/15 | acpi_a/b | ACPI tables |
| vda16/17 | acpio_a/b | ACPI overlay tables |
| vda18/19 | cert_a/b | Certificate store |
| vda20 | persistent | FRP (Factory Reset Protection) |
| vda21 | teedata | TEE persistent data (Trusty) |
| vda22 | config | ext4 → `/mnt/vendor/oem_config` |
| vda23 | calibration | ext4 → `/mnt/vendor/calibration` |
| vda24 | ghs_log | GHS log storage |
| vda25 | update_cache | ext4, OTA staging |
| vda26 | data | f2fs ~39GB, user data (file-based encryption) |

### Critical Partitions

| Partition | Description |
|-----------|-------------|
| ghs_isys_a/b | GHS hypervisor image |
| boot_a/b | Android kernel + ramdisk |
| vbmeta_a/b | AVB verification metadata |
| misc | GHS rollback counter, BCB (boot control block) |
| super | 8.6GB dynamic (system, vendor, product via dm-verity) |
| data | ~39GB f2fs (user data, file-based encryption) |

### Dynamic Partitions (within `super`)

The `super` partition uses Android's dynamic partition system to host `system`, `vendor`, and `product` partitions. All three are protected by dm-verity for integrity verification.

**Correction (2026-09, real Y181B boot-image extraction, cross-checked against the live device):** the
ramdisk's own `fstab.full_gminfo37_gb` does mark partitions `logical,first_stage_mount` (an unused
build-mixin default), and `ro.boot.dynamic_partitions=true` is set as a prop. The real device's `acpio.img`
(2MiB, confirmed) carries an **ACPI SSDT table** (`_HID ANDR0001`, OEM Table ID "android") whose `_DSD`
property describes real by-name **static** partitions on PCI eMMC (`0000:00:1c.0`, `wait,slotselect,avb`
flags). Net effect on this hardware: **static A/B, no `super`, no dm-linear** — consistent with the
static-A/B note already carried in [`emulator.md`](emulator.md#method-hybrid) (`mkdisk.py` comment: "Y181
is static A/B, no super").

> **Qualified 2026-11-12 (live Y181.3.2 radio, `/cache` update-engine logs, read):** the on-radio `gm_update_engine` logs
> `DynamicPartitionControlAndroid.cpp:223 ... Loaded metadata from source slot A|B in /dev/block/by-name/super` on every
> slot-history step (02-03 ... 09-28), the package install script calls `update_dynamic_partition_config()` +
> `extract_logical_partition` for system(22)/vendor(26)/product(57), and `ro.boot.dynamic_partitions=true`. On the real
> radio a `super` partition with logical system/vendor/product is therefore in active use; "static A/B, no `super`, no
> dm-linear" above holds at most for the emulator/reference-image path (it was inferred from the ACPI SSDT, which the
> 2026-09-27 note below already says is unconfirmed as the real mechanism). The partition map's `super` row stands.

**[C] Corrected (2026-09-27) — the SSDT is NOT the fstab mechanism actually consumed at boot, and does NOT
transfer to QEMU.** An earlier version of this note asserted the SSDT was "the AUTHORITATIVE first-stage
fstab actually consumed at boot" and that a QEMU port would just need an equivalent `-acpitable` injection —
that was an inference from static analysis, never confirmed on real hardware, and it is now **empirically
refuted** by the real-kernel QEMU boot work (see
[`../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md#appendix-g-qemu-portability-assessment-2026-09)
Appendix G): the extracted SSDT loads into ACPI fine but `fs_mgr`'s `ReadFstabFromDt()` fails to read a
fstab from it — it is **not a usable DT-fstab source** on this kernel. The mechanism that actually worked
was patching the ramdisk's plain-text `fstab.full_gminfo37_gb` directly (PCI-scoped `by-name` paths +
`slotselect`, dropping `logical`/`avb`). Whether the real (non-emulated) Y181B hardware genuinely resolves
partitions via this SSDT rather than the plain-text fstab remains **unconfirmed** — flag as open, not asserted
fact. Full kernel-config evidence:
[`../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md#appendix-f-kernel-configuration--ghs-coupling-2026-09).

---

## Lifecycle Management

GHS `Lifecycle_InitialTask` manages Android guest health and coordinates shutdown:

### Health Monitoring

| Condition | GHS Log Message |
|-----------|-----------------|
| SoH heartbeat lost | `"Lost Android SoH - rebooting"` |
| Boot failure tracking | `"Android failed to boot (count=%lu)"` |
| Panic recovery failure | `"Guest failed to reboot after panic"` |
| Slot mismatch | `"Android and INTEGRITY slot mismatch. INTEGRITY: %s Android: %s"` |

**Y181B threshold, verified 2026-11-12:** the failed-Android-boot handler
increments its count and compares it with **3** at task address `0x200E2D`
(`.lifecycle.text+0xE2D`); >=3 takes the see-dealer branch. This is separate
from VIP's three-failure timer suppression and recovery's boot-cycle file.
[Code and SPS provenance](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#221-y181b-failed-boot-threshold-verified-2026-11-12).

### Shutdown Sequence

```
SendShutdownRequest
  → WaitForAck          (Android acknowledges)
  → PreparationDone     (Android finishes cleanup)
  → WaitForGuestOff     (Android VM halted)
  → DoACPIShutdown      (hardware power-off)
```

---

## Reboot Triggers

Android can be rebooted by multiple sources:

### Property-based

| Property Value | Reboot Reason |
|----------------|---------------|
| `boot.reason=warm` | Warm reboot (software-initiated) |
| `boot.reason=watchdog` | Watchdog timeout |

### Service Failures

Critical service failures that trigger automatic reboot:
- `boringssl-self-check-failed`
- `bpfloader-failed`
- `vold-failed`
- `apexd-failed`

### GHS-initiated

- SoH (State of Health) heartbeat failure
- A/B slot mismatch between GHS and Android
- VIP MCU reset request

### USB Trigger Files

**Corrected 2026-11-12:** [GM PIT6209](https://static.nhtsa.gov/odi/tsbs/2024/MC-11007670-0001.pdf)
prescribes the encoded reboot filename below, without `.txt`. Y181B recovery
Base64-encodes the source label before matching; plain-name equivalence is not
established. Other listed update controls are not additional bulletin-backed
Base64 procedures. [Handler and evidence](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#45-known-usb-trigger-files).

When recovery reaches its USB scanner, the encoded markers below select
recovery actions. They do not independently enter recovery. The normal-AAOS
flags have separate consumers; their full effects were not reverified here.

| Filename | Action |
|----------|--------|
| `Z21fcmVib290X25vcm1hbA==` | Dealer recovery normal reboot; label `gm_reboot_normal` |
| `Z21fY2FwdHVyZV9sb2c=` | Recovery log capture under USB-root `update_cache/`; existing output files may be cleared |
| `gm_usb_ignore_battery` | Normal-AAOS updater flag; discovery/copy confirmed, full battery-bypass path not traced |
| `gm_usb_auto_install` | Normal-AAOS updater flag; discovery/copy confirmed, full automatic-install path not traced |

**Interpretation of `--show_return_to_dealer` (2026-11-12; read vs inferred):** *Read:* in the retained
recovery logs (counters 54/55) recovery logs `Not get boot-see-dealer mode, start normal update process.`
and then `Dump log to USB` / `Saving log completed.`; normal Android was up afterwards
(live `sys.boot_completed=1`, uptime 11 min at 13:59 AKST; `moduleinfo` timestamp 13:10:49 AKST).
*Inferred:* these recovery entries are the dealer-screen / USB log-export path, not a bricked or unflashable
state. The earlier wipe-reason boots (47-50: `bcm_replacement`, delayed GM server wipe 2026-11-07,
MasterClear 2026-11-10) are separate data-wipe recoveries.

**Bench verified 2026-11-12:** deliberately removing `com.gm.homescreen`
for users 0 and 10 produced incomplete startup; the operator observed automatic
dealer/recovery entry after three failed attempts. The encoded capture marker
then produced the retained USB export. Its final recovery records show
`boot-recovery` plus `--show_return_to_dealer`, not literal BCB
`boot-see-dealer`. A later export repeats capture with recovery counter 55
versus 54. Rotated logs include multiple saves from one recovery run; do not
count rotations as boots. [Provenance and startup limits](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#221-y181b-failed-boot-threshold-verified-2026-11-12).

---

## GHS-Android IPC Map

Inter-process communication channels between GHS tasks and Android:

### VMM Connections

| Connection Name | Purpose |
|-----------------|---------|
| `ConnToAndroidVMM` | Primary VMM control channel |
| `ConnToVMM_Camera` | Camera pipeline coordination |
| `ConnToVMM_Display` | Display/framebuffer management |
| `ConnToVMM_Chime` | Chime audio routing |
| `ConnToVMM_Cal` | Calibration data access |
| `ConnToVMM_OTA` | OTA update coordination |
| `ConnToVMM_TextLog` | Log forwarding to GHS |

### Camera

| Connection Name | Purpose |
|-----------------|---------|
| `ConnToCamera` (x6) | 6 camera connections (IPU4 pipeline) |

### Audio

| Connection Name | Purpose |
|-----------------|---------|
| `ConnToChimes` | Chime audio task |
| `ConnToDirana` | Dirana tuner/DSP |

### VIP MCU

| Connection Name | Purpose |
|-----------------|---------|
| `ConnToVIP` | Primary VIP communication |
| `ConnToVip_Lifecycle` | Lifecycle/shutdown coordination |

### TEE (Trusted Execution Environment)

| Connection Name | Purpose |
|-----------------|---------|
| `ConnToTEE_Keymaster` | Hardware keymaster operations |
| `ConnToTEE_Storage` | Secure storage (RPMB) |
| `ConnToTEE_Router` | TEE message routing |
| `tipc_conns` | Trusty IPC connections for TEE |

---

## Error Screen Architecture

The "return to dealer" / recovery screens are rendered by **GHS**, not Android. GHS has direct display access — it also draws the backup-camera overlay independently of the Android guest (which is why the camera works during an Android reboot). `gm_update_engine` on the Android side stages OTA packages and writes the BCB (`boot-recovery` / `--show_return_to_dealer`) to `misc`, but the on-screen rendering of the error/see-dealer screen itself is done by GHS. See `hardware/teardown.md` §GHS as Recovery Architecture. *(Corrects an earlier claim here that "GHS is headless / has no UI rendering.")*

---

## GSI/DSU Status

GSI (Generic System Image) and DSU (Dynamic System Updates) are **disabled by app
removal, not by the SELinux rule previously cited here.** *(Corrects an earlier claim
that `dontaudit gm_update_engine gsi_metadata_file` blocks GSI installs — see below.)*

**Consistent across Y175, Y177, and Y181.** All three USB full packages ship the stock
`gsid`/`gsi_tool` daemon and keep the `com.android.dynsystem` entry in
`privapp-permissions-platform.xml`, but none of the three include the `com.android.dynsystem`
APK in any app dir. The removal predates the oldest build in the sample (Y175) — it is a
standing GM build policy, not a lockdown added in a later release. Note Y177 (earlier
mislabeled "the permissive-SELinux build" — retracted 2026-08-26, it runs enforcing like the others) also lacks the app, so a Y177 downgrade does not restore DSU.

What is actually present vs. removed:

- **DSU daemon retained.** `gsid.rc` is still in init, and `gsid` / `gsi_tool` are on
  the image. `gsid` has its **full stock SELinux policy** (~50 allow rules in
  `plat_sepolicy.cil`): it can create/write `gsi_metadata_file`, `gsi_data_file`, and
  `ota_image_data_file`, drive `dm_device`/loop devices, touch `userdata_block_device`,
  hold `sys_admin`, set `gsid_prop`, and add/find `gsi_service`. Nothing is stripped from
  the daemon's policy. The `dynamic_system` service is registered.
- **DSU front-end app removed.** `com.android.dynsystem` is **absent** from the live
  package set (89 packages total on a Y181 Apr-2026 dump — heavily stripped AAOS). The
  intent path `am start-activity -n com.android.dynsystem/…VerificationActivity -a
  android.os.image.action.START_INSTALL` therefore fails with *activity-does-not-exist*,
  not a policy denial.
- **Why the old claim was wrong.** `dontaudit` never denies anything — it only suppresses
  the audit log of a denial that already occurs from the absence of an allow rule. And it
  targets `gm_update_engine` (GM's OTA A/B engine), which is not the DSU path. It has no
  effect on `gsid`. (The rule does exist, but in `vendor_sepolicy.cil`, and it is not a
  GSI blocker.)
- **Direct `gsi_tool` path is closed by other walls, not SELinux.** `ro.build.type=user`,
  `ro.debuggable=0` (shell is uid 2000, not root), and `gsid` requires the caller to hold
  `MANAGE_DYNAMIC_SYSTEM` (signature-or-privileged), which shell lacks.
- **GSI boot is gated by locked verified boot.** `ro.boot.flash.locked=1`,
  `ro.boot.vbmeta.device_state=locked`, `ro.boot.verifiedbootstate=green`,
  `sys.oem_unlock_allowed=0`. fstab trusts only the Google GSI keys
  (`avb_keys=/avb/q-gsi.avbpubkey:/avb/r-gsi.avbpubkey:/avb/s-gsi.avbpubkey`), so only a
  Google-signed GSI could pass AVB; a self-signed/unsigned GSI cannot, and verification
  can't be disabled on a locked unit.
- No dedicated recovery partition exists (recovery is embedded in boot image); all updates
  are A/B only.
- **(2026-09-10, assessment — OPEN) CSM-ownership / AOSP-replacement chain.** The device is
  locked (`ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`,
  `sys.oem_unlock_allowed=0`, dm-verity RO), so this is a gate description, not a solved path.
  Compiled ELK eligibility/provisioning checks and transition limits are maintained in
  [the consolidated source §2.3.2–§2.3.3](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#232-elk-unlock-eligibility-is-a-separate-gate-verified-2026-11-12).
  There is no demonstrated unlock procedure. Boot Guard, signature trust and
  varstore-backing questions remain owned by
  [the security architecture](security.md).

**Confirmed at firmware-image level (Sep 2026), not just runtime.** Unpacked the Y181
USB full package (SOC_SYSTEM 86331654, SOC_VENDOR 86331650, SOC_PRODUCT 86331636):

- `com.android.dynsystem` is absent from every app dir across all three images
  (`system/app`, `system/priv-app`, `system/system_ext/priv-app`, `product/app`,
  `product/priv-app`). No GM-renamed or variant DSU installer exists.
- The stock DSU daemon set is present and unmodified: `system/bin/gsid`, `gsi_tool`,
  `snapshotctl`, `lpdump`/`lpdumpd`, `libgsi.so`, and a byte-stock `gsid.rc` (creates
  `/metadata/gsi/dsu`, `/data/gsi/dsu`, etc.). The block is purely the missing app.
- The DSU Loader in Developer Options (`CarDeveloperOptions.apk`,
  `DSUTermsOfServiceActivity.installDSU()`) just calls
  `setClassName("com.android.dynsystem","…VerificationActivity")` + `startActivity` — so
  the button throws ActivityNotFound on this image. It is not a GM reimplementation.
- The only other "replace /system" path is `gm_update_engine` (GM fork of A/B
  update_engine, `/vendor/bin/hw/`). Its binary has zero GSI/dynamic-system/dev-signed/
  unsigned strings and a mandatory RSA+SHA+FCID verify path
  (`SignatureVerifier.cpp`, OpenSSL `EVP_DigestVerify`). It accepts only GM-signed
  packages; it cannot load a GSI. `GMSWUpdater.apk` is a pure UI shell with no DSU/GSI code.

*(Cross-checked against the 2024 Silverado ICE OS dump — live `packages.txt`,
`all_properties.txt`, `plat_sepolicy.cil`/`vendor_sepolicy.cil`, plus the unpacked Y181
system/vendor/product images decompiled with 7z + jadx.)*

---

## Module Signing Status

| Status | Modules |
|--------|---------|
| TSS-signed | VIP_APP, SOC_HOSTOS, SOC_SYSTEM/VENDOR |
| Unsigned | SOC_BOOT, SOC_UTILS, SXM, GPS, TUNER, ETH_SWITCH, SOC_ACPIO, SOC_VBMETA, SOC_PRODUCT, VIP_BOOT, SOC_ABL |

The unsigned status of several modules (including SOC_BOOT, SOC_VBMETA, and SOC_ABL) is notable — these are protected by the earlier boot stages (Intel CSE measured boot and GHS AVB verification) rather than by individual module signatures.
