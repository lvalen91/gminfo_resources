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
- `VIP_InitialTask` — VIP MCU communication (HDLC over /dev/ttyS1)
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
| 4. ELK | Emergency Linux Kernel | Fallback Linux environment for diagnostics/recovery |
| 5. Diagnostic | Service tool | Factory/dealer diagnostic mode |

---

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

Placing specific files on a FAT32 USB drive root triggers special boot behavior:

| Filename | Action |
|----------|--------|
| `gm_reboot_normal` | Force normal reboot |
| `gm_usb_ignore_battery` | Ignore battery state during update |
| `gm_usb_auto_install` | Auto-install update from USB |

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
standing GM build policy, not a lockdown added in a later release. Note Y177 (the
permissive-SELinux build) also lacks the app, so a Y177 downgrade does not restore DSU.

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
  The only realistic route to a custom OS is: reach ELK (Intel Kernelflinger fastboot, see
  `research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` §2.3) → set `oem_unlock_allowed` → `fastboot
  flashing unlock` → flash unsigned images. **Both gates are currently OPEN:** (1) no confirmed
  path to reach ELK from a locked, running unit is documented; (2) no confirmed method to flip
  `oem_unlock_allowed` off-Android (normally an Android Settings toggle, unavailable here) has
  been demonstrated. Do not read this as a working unlock procedure.

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
