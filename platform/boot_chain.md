# Boot Chain

**Device:** GM Info 3.7 (gminfo37) | **Platform:** Intel Apollo Lake (Broxton) | **Android:** 12 (API 32) | **Research window:** Dec 2025 - Nov 2026 (the original header read "December 2025 - February 2026"; extended because the body carries dated Sep-Nov 2026 observations, consolidation 2026-11-18)

Scope: boot phases from VIP power-on to AAOS, GHS init tasks and lifecycle, boot modes, guest cmdline, AVB flow, A/B + BCB structures, rollback, signing/trust hierarchy, boot timing, GHS-guest connection map, update engine and manifest command sequence, recovery USB trigger files, GSI/DSU boot gate. ELK/Probe/recovery evidence and partitions are owned by other docs (pointers below).

Evidence tags: **[V]** verified on hardware/live read, **[C]** confirmed (dated live/binary observation), **[U]** unverified/inferred, **[X]** external-sourced. Dates are the observation date.

Related: [elk_recovery.md](elk_recovery.md), [partitions_storage.md](partitions_storage.md), [ota_update_stack.md](ota_update_stack.md), [ota_programming_roles.md](ota_programming_roles.md), [vip_ipc_ghs.md](vip_ipc_ghs.md), [security.md](security.md), [firmware_versions.md](firmware_versions.md), [hardware_specs.md](hardware_specs.md), [emulator.md](emulator.md), [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md), [`../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md), [`../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md).

---

## Boot Phases

5-phase sequence from VIP MCU power-on through Android verified boot:

```
1. VIP MCU (RH850) — power sequencing, CAN init, SoC power-on
2. Intel CSE — hardware root of trust, measured boot
3. SOC_ABL — Intel bootloader, loads GHS
4. GHS INTEGRITY — hypervisor init, AVB verification of Android images
5. Android AVB — verified boot into AAOS
```

Phase 2 detail (datasheet-side, [X] Intel 336256-004US as quoted in `intel_apl_external_resources.md` L173-176): Boot Guard + TXE/CSE (HECI) is the pre-GHS trust stage on the Intel compute-module side. It lives in the module's ISSI SPI-NOR IFWI, separate from the carrier eMMC that holds GHS + Android. The eMMC boot device is PCI `00:1c.0` (matches `androidboot.diskbus=1c.0`, see [Boot Configuration](#boot-configuration)). The HSUART assignment (UART1 GNSS repurposed by GM for VIP IPC, UART2 = Host OS Debug) is owned by [hardware_specs.md](hardware_specs.md).

### GHS Kernel Init Sequence (Phase 4 detail)

On the boot CPU, before any task launches:

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

**Core**
- `VMM1_InitialTask` — Android virtual machine manager (guest VM); performs AVB (see [AVB Verification](#avb-verification))
- `Lifecycle_InitialTask` — Android health monitoring, shutdown coordination (see [Lifecycle Management](#lifecycle-management))
- `VIP_InitialTask` — VIP MCU communication (HDLC over `/dev/ttyS1`). **[C] 2026-09, real Y181B kernel `.config` extraction: no `N_HDLC` line discipline is compiled into the Android guest kernel at all.** HDLC framing terminates below the Android guest (GHS-side task); on the Android side the link is a userspace protocol — `IPCServer` fans the channel into per-channel Unix sockets (`/vendor/etc/ipc4.cfg`) that `libipc.so` clients connect to (see [emulator.md](emulator.md)). Not a kernel-driver dependency. Channel/protocol detail: [vip_ipc_ghs.md](vip_ipc_ghs.md). (Which side owns `ttyS1`: see [Open conflicts](#open-conflicts) #3.)
- `OTA_InitialTask` — over-the-air update coordination

**Hardware**
- `Camera_InitialTask` — IPU4 camera pipeline
- `Audio_InitialTask` — HDA (High Definition Audio) controller
- `GPU_InitialTask` — Gen9 GPU (i915)
- `Chimes_InitialTask` — chime/alert audio playback
- `Dirana_InitialTask` — Dirana tuner/audio DSP
- `DisplayI2C_InitialTask` — display controller via I2C

**Security**
- `TEE_Keymaster` — hardware-backed key generation/storage
- `TEE_HW_Crypto` — hardware cryptographic operations
- `TEE_Storage` — secure storage via RPMB (Replay Protected Memory Block)
<!-- corrected 2026-11-21: GHS_FILE_MAP_85098662.md and boottable §7A.1 (2026-10-10) confirm two additional TEE server address spaces absent from earlier inventory -->
- `TEE_Gatekeeper` — gatekeeper server (.tee_gatekeeper section confirmed in GHS_FILE_MAP_85098662.md; §7A.1 boottable-derived)
- `TEE_Router` — fans tipc connections to TEE_* servers; `TEEAtt` is a VMM1-side connection to this server, not a separate AS (see GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md §7A.4)

**Other**
- `Calibrations_InitialTask` — vehicle calibration data
- `Lines_InitialTask` — guideline/overlay rendering
<!-- corrected 2026-11-21: two additional server address spaces confirmed by boottable §7A.1 -->
- `Audit` — security audit log (.audit section; confirmed in GHS_FILE_MAP_85098662.md and §7A.1)
- `EMMC` — eMMC mux server (.emmc_mux section; GHS keeps eMMC/SDHC, mediates to guest via this server)

### Guest-kernel coupling to GHS (boot-relevant facts)

Source: real Y181B (gminfo37 CSM) boot image extracted from the firmware package, cross-checked byte-identical against the live device `.config` ([C] 2026-09-27; `emulator.md` L29-87). Emulator-build results (QEMU home-screen milestone) are in [emulator.md](emulator.md); full per-dependency table: `../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md` Appendix G. Full kernel-config evidence: [Appendix F, kernel configuration / GHS coupling (2026-09)](../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md#appendix-e-kernel-configuration--ghs-coupling); QEMU portability: [Appendix G](../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md#appendix-f-qemu-portability--dependency-classification).

- `CONFIG_PARAVIRT` is **not set**. `CONFIG_HYPERVISOR_GUEST=y` enables only optional detection (no `KVM_GUEST`/`XEN`/`HYPERV`/`PVH`/`JAILHOUSE_GUEST`). Core MMU/timekeeping/IRQ/scheduling is bare-metal x86_64 although the kernel runs as a GHS INTEGRITY guest.
- GHS coupling is at the device-driver layer:
  - `ghs_comms` — PCI driver bound to a GHS-presented virtual PCI function, vendor `0x1B95` device `0xA000`, BAR-mapped rings, MSI-X, host/guest version handshake.
  - `ghs_vmm_bc` — A/B slot / boot-control; delivers guest TSC frequency from the VMM.
  - `gm_ghs_mmc`, `snd_ghs_pcm`, `ghs_camera_memory_map` — paravirtual MMC/audio/camera drivers.
  - All are ordinary probe()-based PCI/platform drivers; they stay unbound (no panic) when the backing GHS device is absent (e.g. `Unable to open file: /dev/ghs/emmc-health`).
- virtio is present but narrow: `VIRTIO_PCI=y` (legacy), `VIRTIO_BLK`, `VIRTIO_CONSOLE` back Trusty TEE only. No `VIRTIO_MMIO`, `VIRTIO_NET`, `VIRTIO_INPUT`, `VIRTIO_BALLOON` — kernel is incompatible with goldfish/ranchu by construction. `CONFIG_E1000`/`E1000E=y` and `DRM_BOCHS=y` (alongside `DRM_I915=y`) are compiled in.
- Timebase: no TSC override needed (`tsc: Refined TSC clocksource calibration: 2693.33 MHz` → `Switched to clocksource tsc`, observed on the emulated boot).
- First-stage fstab: the ramdisk `first_stage_ramdisk/fstab.full_gminfo37_gb` marks partitions `logical,first_stage_mount`. On the emulator boot the working fix was patching that plain-text fstab: drop `logical`/`avb`, point each `first_stage_mount` entry (system/vendor/product) at `/dev/block/pci/pci0000:00/0000:00:1c.0/by-name/<partition>` with `slotselect` (flat `/dev/block/by-name/...` is never created by first-stage init on this kernel). Dynamic-partition vs static-A/B conclusion: [partitions_storage.md](partitions_storage.md).
- Serial labels (vendor `file_contexts`): `ttyS0` = `bluetooth_serial_device`, `ttyS1` = `ipc_serial_device` (VIP/libipc channel; reserved for IPCServer, `/vendor/etc/ipc4.cfg`), consoles must be `ttyS2`+ (`serial_device`).
- Boot-control resolves partitions with `androidboot.slot_suffix=_a` + `slotselect` with no GHS VMM bootctrl present. AVB verity-off path works on the emulator. Hardware keymaster/attestation/RPMB (Trusty + GHS) remain hard blockers there. GHS is a service-layer blocker (vendor daemons/HALs stay dead), not a boot-layer one.

---

## Special Boot Modes

GHS selects the mode from BCB (Boot Control Block) or external triggers:

| Mode | Trigger | Description |
|------|---------|-------------|
| 1. Normal A/B | Default | Standard A/B verified boot into Android |
| 2. Recovery | BCB `boot-recovery` | Recovery (no separate recovery partition — uses the boot image) |
| 3. See-Dealer | BCB `boot-see-dealer` | Service-required screen, directs user to dealer |
| 4. ELK | GHS lifecycle recovery target | Fallback boot target for diagnostics/recovery |
| 5. Diagnostic | Service tool | Factory/dealer diagnostic mode |

Execution boundary ([V] 2026-11-12): VMM maps both `boot-recovery` and `boot-see-dealer` into the Linux/Android guest recovery flag, so ordinary recovery, the dealer UI and recovery-fastbootd are not three bare-metal environments. Recovery fastbootd is separate from ELK (Y181B recovery recognizes `boot-fastboot`/`--fastboot` and sets `sys.usb.config=fastboot`). Observed: recovery log of a see-dealer entry shows `boot-recovery` + `--show_return_to_dealer`, not literal BCB `boot-see-dealer` (see [elk_recovery.md](elk_recovery.md)).

**Owned by [elk_recovery.md](elk_recovery.md) (pointer only):** recovery fastbootd path, ELK reciprocal lifecycle/OTA IPC + HECI request, lifecycle ACPI power-state handler, Probe06/Probe08 RAM boot, custom Linux (4.19.283, `7.3.5-probe-stable02`) via ELK RAM download/boot, eMMC `mmcblk1`, native framebuffer, ELK unlocked-vs-AAOS-locked observation, and the automatic boot-candidate order (eMMC `ghs_isys_a` → `ghs_isys_b` → SPI ELK → partition 5 @ `0x7D0000` → CLI). Evidence: [`../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) §2.3.1-§2.3.3. Display bring-up: `video/display_subsystem.md`.

---

## Boot Timing

Approximate, kernel start to screen (~24.5 s total):

| Milestone | Time |
|-----------|------|
| Kernel → zygote | ~8 s |
| System server ready | ~15 s |
| Screen enabled | ~24.5 s |

- 13 `Davey!` events during boot (all SystemUI), none during streaming.
- Dominated by system-server initialization and GM service startup.

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

Added during AVB verification: `slot_suffix`, `verifiedbootstate`, `vbmeta.avb_version=1.1`, `hash_alg=sha256`.

Further tokens retained in Y181B boot-log / recovery `last_kmsg*` cmdlines ([C] 2026-11-12): `ABL.secureboot=1` (count: 386 as first reported; 2026-11-12 recount ~188 per archive, 376 if the duplicate export is double-counted; present only in retained kernel-log cmdlines, live `getprop ro.boot.ABL.secureboot` is empty so the flag is cmdline-only), `androidboot.selinux=permissive` / `enforcing=0` (early tokens) followed by a later `enforcing=1` / `androidboot.selinux=enforcing` pair, `androidboot.trustyimpl=-ghs`, `androidboot.force_normal_boot=1`, `androidboot.bootreason=cold|reboot`. Runtime is Enforcing; "later pair wins" is inferred [U]. On Y175, `ro.boot.selinux=permissive` appears in the cmdline while all 179 captured avc lines show `permissive=0` (runtime Enforcing). SELinux posture: [security.md](security.md). The stock Y175 cmdline carries no `androidboot.android_dt_dir` (kf4abl appends none), so `fs_mgr` never reads the SSDT fstab ([partitions_storage.md](partitions_storage.md)).

**Static GHS-slot corroboration [C] 2026-11-18:** extraction from a complete eMMC backup found `ghs_isys_a` at sectors 2048–133119 and `ghs_isys_b` at 133120–264191, both 64 MiB. They are byte-identical (`SHA-256 13e168dd9ff073f2c40ef1fb42ed44627474554dbf9d4a2f23879a8c77f525a0`) IPK-style containers. Each carries board/part metadata followed at offset `0x5c` by a 14,924,936-byte stripped, statically linked 32-bit x86 ELF (entry `0x200000`). Its `.bootargs`, `.boottable`, `.vmm1`, `Guest1_VM_Memory_RAM*`, and Android-key sections, plus `BootargsDev`, `OtaUpdateBootArgsIod`, `KeymasterBootArgsIod`, `kernel_boot_params`, and `parse_cmdline` symbols/string evidence, independently corroborate that GHS constructs guest boot inputs and runs a VMM guest. This static result does **not** by itself recover every cmdline field or establish its runtime dataflow; the concrete AAOS cmdline and `ASP_VMX_SetGuestKernelAddr` behavior above remain the controlling evidence. Console logging and Ethernet/ARP code are present, but no interactive GHS shell daemon (`ssh`, `dropbear`, `telnet`, or `inetd`) is demonstrated.

---

## AVB Verification

AVB is performed by GHS `VMM1_InitialTask`, not by Android:

```
1. CheckRecoveryMode()          — reads BCB from misc partition
2. A/B slot selection            — misc@0x800, CRC32 only (no crypto signature)
3. Load vbmeta                   — AVB0 magic, version 1.1, avbtool 1.2.0
                                   (2026-09-10: byte-confirmed stock upstream libavb —
                                   offset 0 = `41 56 42 30` = `AVB_MAGIC`, RSA2048/SHA256,
                                   flags=0x00000000 i.e. verification NOT disabled, zero
                                   GM-specific fields)
4. Verify signing key            — RSA-2048 `current_android_key`, embedded in the GHS
                                   image (not SOC_ABL `.oemkeys`; corrected 2026-11-21,
                                   research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md §5-6)
5. Check rollback index          — GHS independent counter in misc
6. Load boot partition           — verify hash against vbmeta descriptor
7. Set kernel cmdline            — slot_suffix, verifiedbootstate,
                                   vbmeta.avb_version=1.1, hash_alg=sha256
8. ASP_VMX_SetGuestKernelAddr   → ASP_RunGuestVM (launch Android)
```

### Live runtime posture (end-state of the chain)

**[C] Y175, 2026-10-05** — `W213E-Y175.5.2-SIHM22B-383.1`, capture `/tmp/radio_audit/20261005_232227/raw/`: `ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `sys.oem_unlock_allowed=0`, `ro.oem_unlock_supported=` (empty), `ro.debuggable=0`, `ro.secure=1`, `ro.adb.secure=1`, `ro.build.type=user`, tags `release-keys`. vbmeta: `ro.boot.avb_version=1.2` / `ro.boot.vbmeta.avb_version=1.1`, `hash_alg=sha256`, `size=3328`, `digest=76b736eaf87d186de5f03f08176b67ae2cdcf91130b4350b328b0876c00bb585`. SELinux Enforcing at runtime (all 179 avc lines `permissive=0`). **Unverifiable from a shell uid 2000:** steps 1-6 internals (the GHS-embedded `current_android_key` RSA-2048 key (corrected 2026-11-21; previously cited as `.oemkeys`), AVB0/vbmeta parse, CRC32 slot metadata, GHS rollback counter in `misc`). `verity.txt` captured only `green`/`1` and an empty `===VERITY` section, so runtime dm-verity state is not independently evidenced by that capture.

**[C] Y181B, 2026-11-12** (adb getprop, directly read) — `W231E-Y181.3.2-SIHM22B-499.3`, Android 12/SDK 32, patch `2025-06-05`, `ro.bootloader=2344`, `ro.boot.verifiedbootstate=green`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.flash.locked=1`, `ro.boot.slot_suffix=_a`, `ro.boot.product.hardware.sku=gv221`, `ro.boot.vbmeta.avb_version=1.1`, `ro.boot.avb_version=1.2` (the "AVB 1.1" shorthand applies only to the vbmeta-side token), kernel `4.19.305-240125T145315Z-gf1edde901aa7`.

**Slot history** (Y181B radio, 2026-11-12):
- Retained recovery kernel logs (31 boots, `last_kmsg`..`.30`), oldest → newest: A x2, B x5, A x7, B x5, A x12. The radio alternated slots (two B episodes in the window); the 2026-09-28 recovery install flipped active slot 1 → 0; currently A with `slot_switched=N`.
- Update-engine logs (`rg -n 'Loaded metadata from source slot' ~/Desktop/gminfo37_update_cache_FORENSIC_LLM.txt`, 'Active slot per engine log'): A (from 02-03) → B 02-10 10:45:17 → A 04-30 20:46:48 → B 08-25 07:09:17 → A 09-28 17:33:45 → still A at 11-12 13:10. Four changes, matching the four USB installs. History: an earlier "cannot be derived from these exports" wording was wrong (corrected 2026-11-12); the retained recovery logs alone still cover only 31 boots.

### A/B Metadata Structure

Located in `misc` (`vda9`) at offset `0x800`. **CRC32-only** (no crypto signature on slot metadata).

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

GHS contains a typo in its error string, `"metatdata"` (sic), when referring to this structure.

### Rollback Protection

- GHS keeps an independent rollback counter in `misc`, enforced at the hypervisor level, independent of Android AVB's rollback index.
- Both Y177 and Y181 `vbmeta` images have `rollback_index=0`; the GHS counter is separate.
- **Tested:** Y181 → Y177 downgrade FAILS (partitions are written successfully, GHS rejects at boot, A/B fallback reverts to the previous slot).
- **Tested:** Y181 → Y181 reinstall SUCCEEDS (same version passes the rollback check).
- `"version check disabled"` in the OTA manifest only affects the write phase; GHS enforcement at boot is independent. (Y181→Y177 downgrade-fail and Y181 reinstall-pass: owner-verified 2026-08-17 bench re-test.)
- OTA-side view of the same counter: [ota_update_stack.md](ota_update_stack.md).

---

## Signing Hierarchy and Secure-Boot Trust Layers

### Signing hierarchy

| Level | Component | Signer |
|-------|-----------|--------|
| 1 | VIP (RH850 firmware) | GM |
| 2 | Intel ABL (SOC_ABL bootloader) | Intel / GM |
| 3 | GHS INTEGRITY (hypervisor) | Green Hills / GM |
| 4 | Android AVB (vbmeta keys, GSI keys q/r/s) | GM (RSA-2048 vbmeta key = GHS-embedded `current_android_key`, not `.oemkeys`; corrected 2026-11-21, [`../research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md`](../research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md) §5-6) |

### Module signing status (package level)

| Status | Modules |
|--------|---------|
| TSS-signed | VIP_APP, SOC_HOSTOS, SOC_SYSTEM/VENDOR |
| Unsigned | SOC_BOOT, SOC_UTILS, SXM, GPS, TUNER, ETH_SWITCH, SOC_ACPIO, SOC_VBMETA, SOC_PRODUCT, VIP_BOOT, SOC_ABL |

Unsigned modules (including SOC_BOOT, SOC_VBMETA, SOC_ABL) are protected by the earlier boot stages (Intel CSE measured boot, GHS AVB) rather than per-module signatures. DPS package inventory: [ota_programming_roles.md](ota_programming_roles.md). See [Open conflicts](#open-conflicts) #1 on SOC_ABL.

### 5-layer trust hierarchy

| Layer | Component | Mechanism | Details |
|-------|-----------|-----------|---------|
| 1 | Intel CSE | Hardware root of trust | OTP fuses, immutable, first code executed |
| 2 | SOC_ABL (SoC Application Boot Loader) | Intel IPK format | ~6 MB signed image; `.oemkeys` holds the RSA-2048 public key for chain validation |
| 3 | GHS INTEGRITY hypervisor | RSA-2048/SHA-256 (ABL→GHS); Gate-1 self-integrity (CRC32+SHA-1 internally) | GHS image carries an appended RSA-2048/SHA-256/PKCS#1-v1.5 signature (sig @ `0xe3cc00`); signing OEM "OS Kernel" key is embedded in the Boot-Guard-authenticated OBB/ELK (@ `0x114000`) and hashed in the CSE FTPR Key Manifest — chain closed, enforcement empirically demonstrated (1-byte sig-corrupt boot test: rejected to fastboot) `[C 2026-11-20]`. `BSP_CRCCheck`/`BSP_SHA1Check` are GHS's own Gate-1 self-integrity checks over its in-memory image, a distinct and subordinate layer. Owned: [`../research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md`](../research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md) §8 |
| 4 | AVB | RSA-2048 / SHA-256 | `vbmeta` signature verified by GHS VMM1 before Android kernel loads |
| 5 | dm-verity | Runtime block integrity | Protects system, vendor, product; hash tree verified on read |

**[C] live-Y175 2026-10-05:** layers 1-3 unverifiable from a locked user shell. The GHS image itself is fully mapped from extracted firmware `85098662` (no compressed/encrypted code; only 768 B of key/signature tail unreadable) — [FW 85098662; 2026-10-10], `GHS_FILE_MAP_85098662.md`. Layer 4 supported by the props listed under [Live runtime posture](#live-runtime-posture-end-state-of-the-chain). Layer 5 supported by dm-6/7/8 device-mapper mounts of `/`, `/vendor`, `/product` (all `ro,seclabel`); no dm-verity *status* text captured.

### Boot-lock state and Boot Guard (SOC_ABL / kernelflinger analysis)

**Revision boundary (corrected 2026-11-17):** the SOC_ABL 85738845 findings below must not be generalized to the mapped Y175 ELK executable. Y175's lock-state callbacks select physical RPMB or emulation in `teedata`, despite retaining an `OEMLock` error string. Its missing-record provisioning branch tests lifecycle-query status, not the returned lifecycle boolean, and its non-User unlock handler continues after an eligibility refusal. No persistent unlock or change to IBB/GHS policy was demonstrated. Trace: [`../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#y175-elk-lock-state-and-eligibility--callback-trace-2026-11-17).

**[C] 2026-10-08, avbtool/binary on SOC_ABL 85738845 and SOC_VBMETA 86331644:**
- **F1 — ABL lock-state backend (confirmed from binary).** SOC_ABL is kernelflinger ("ELK"; 32-bit x86 ELF at container offset `0x301288`, dedicated `.oemkeys` AVB keystore). Lock state is read from the UEFI NV variable **`OEMLock`** (GUID `1ac80a82-4f0c-456b-9a99-debeb431fcc1`) via `read_device_state_efi()`. `USE_TPM` was NOT compiled (zero TPM2 NV-index constants/calls in the 1 MB module), so the lock bit is NOT fTPM/TPM2-backed and NOT RPMB (`ABL.rpmb=` is only an androidboot cmdline token). An ordinary successful `OEMLock` read uses bit 0 (`0x01`), but this is not the complete state predicate: gated missing-state/provisioning fallbacks exist (clarified 2026-11-12, `../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` §2.3.2). A secondary provisioning-UNLOCKED path (`OEMLock` NOT_FOUND + non-virtual boot + life-cycle != ENDUSER) is gated by a manufacturing/SKU life-cycle fuse and stays LOCKED on a production ENDUSER unit. Live EFI contents are not established by the static trace. **Unknown from files:** whether the varstore physically holding `OEMLock` is SPI-NOR-backed (offline-settable) or RPMB-backed.
- **F2 — Boot Guard (verified-capable; enforcement FPF-dependent, unknown from files).** The IPK (85738845) is a full Apollo Lake IFWI containing a production-signed OEM Key Manifest (`oem.key`, `$MN2`, vendor `0x8086`, RSA-2048), a production-signed IBB manifest (`IBBP.man`, `$MN2`), and a Boot Policy (`BPM.met`) with three SHA-256 digests that exactly match the real boot-block bytes (IBBL, IBB, ELK/OBB). This is a verified-boot construction, so "verified by/with Intel CSE secure boot" / "hardware enforced" wording elsewhere understates capability but is not provable as categorical enforcement: reject-vs-measure depends on the Intel TXE FPF/OTP fuse state, outside this package (`fitc.cfg` shows build-time intent only). Boot Guard digests cover CODE (IBBL/IBB/OBB) only, NOT the UEFI NVRAM varstore, so flipping `OEMLock` would not break any Boot Guard hash.
  - **Corrected 2026-11-17:** Apollo Lake TXE must not be decoded as desktop ME. Live MSR `0x13A` read returned `Input/output error` (not a zero value). In the standard SACM layout measured/verified flags are bits 5/6; bits 2:1 describe TPM type, bit 3 TPM success; no such bits were obtained from the failed read. Platform FWSTS6 bit 30 is set; hardware-source `/fpf/intel/SocCfgLock` returned 1 (platform fuse configuration committed/locked). FWSTS3 reports IBB verification done/pass. The exact rejection profile and individual key/policy fuse contents are not established; physical FPF fuses are not recovered merely by dumping SPI. Evidence: [live status](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#live-apollo-lake-fusestatus-check--2026-11-17).
- **Upstream Probe update (2026-11-17):** kernel.org 4.19.283 and 7.3.5 images have executed through ELK RAM boot. Stable02 uses `CONFIG_MODVERSIONS=n`, `CONFIG_MODULE_SIG=n`, `CONFIG_DEVMEM=y`, `iomem=relaxed`; `/dev/mem` presence verified. These runtime choices neither rewrite fuses nor establish disabled IBB/GHS authentication or unsigned normal-storage boot. Evidence: [stable02](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17). Selection-order trace: [elk_recovery.md](elk_recovery.md).
- Upstream Kernelflinger's `secure=no` variable is fixed, not a hardware secure-boot measurement. ELK reports unlocked=yes across an AAOS round trip while AAOS reports locked/green; this establishes neither disabled GHS verification nor a globally unlocked SoC ([elk_recovery.md](elk_recovery.md)).
- Kept distinct from the MEC/ADB certificate and BCM ProtoKey material ([security.md](security.md)): those are not the `OEMLock` boot-lock state.

---

## Lifecycle Management

GHS `Lifecycle_InitialTask` manages Android guest health and shutdown.

### Health monitoring

| Condition | GHS log message |
|-----------|-----------------|
| SoH heartbeat lost | `"Lost Android SoH - rebooting"` |
| Boot failure tracking | `"Android failed to boot (count=%lu)"` |
| Panic recovery failure | `"Guest failed to reboot after panic"` |
| Slot mismatch | `"Android and INTEGRITY slot mismatch. INTEGRITY: %s Android: %s"` |

**Y181B threshold ([V] 2026-11-12):** the failed-Android-boot handler increments its count and compares it with **3** at task address `0x200E2D` (`.lifecycle.text+0xE2D`); >=3 takes the see-dealer branch. Separate from VIP's three-failure timer suppression and recovery's boot-cycle file. [Code and SPS provenance](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#221-y181b-failed-boot-threshold-verified-2026-11-12).

### Shutdown sequence

```
SendShutdownRequest
  → WaitForAck          (Android acknowledges)
  → PreparationDone     (Android finishes cleanup)
  → WaitForGuestOff     (Android VM halted)
  → DoACPIShutdown      (hardware power-off)
```

### Reboot triggers

Property-based:

| Property value | Reboot reason |
|----------------|---------------|
| `boot.reason=warm` | Warm reboot (software-initiated) |
| `boot.reason=watchdog` | Watchdog timeout |

Critical service failures that trigger automatic reboot: `boringssl-self-check-failed`, `bpfloader-failed`, `vold-failed`, `apexd-failed`.

GHS-initiated: SoH heartbeat failure; A/B slot mismatch between GHS and Android; VIP MCU reset request.

### USB Trigger Files

**Corrected 2026-11-12:** [GM PIT6209](https://static.nhtsa.gov/odi/tsbs/2024/MC-11007670-0001.pdf)
prescribes the encoded reboot filename below, without `.txt`. Y181B recovery
Base64-encodes the source label before matching; plain-name equivalence is not
established. Other listed update controls are not additional bulletin-backed
Base64 procedures. [Handler and evidence](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#45-known-usb-trigger-files).

When recovery reaches its USB scanner, the encoded markers below select
recovery actions. They do not independently enter recovery. The normal-AAOS
flags have separate consumers; their full effects were not reverified here.

| Filename | Action |
|----------|--------|
| `Z21fcmVib290X25vcm1hbA==` | Dealer recovery normal reboot; label `gm_reboot_normal` |
| `Z21fY2FwdHVyZV9sb2c=` | Recovery log capture under USB-root `update_cache/`; existing output files may be cleared |
| `gm_usb_ignore_battery` | Normal-AAOS updater flag; discovery/copy confirmed, full battery-bypass path not traced (Y175 bench result: [ota_update_stack.md](ota_update_stack.md)) |
| `gm_usb_auto_install` | Normal-AAOS updater flag; discovery/copy confirmed, full automatic-install path not traced (Y175 bench result: [ota_update_stack.md](ota_update_stack.md)) |

The `--show_return_to_dealer` read/inferred interpretation and the 2026-11-12 homescreen-removal bench test (removing `com.gm.homescreen` for users 0 and 10 leads to automatic dealer/recovery entry after three failed attempts; counters 54/55) are in [elk_recovery.md](elk_recovery.md). Provenance: [`../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#45-known-usb-trigger-files).

### Error-screen rendering

The "return to dealer" / recovery screens are rendered by **GHS**, not Android; GHS has direct display access and also draws the backup-camera overlay independently of the guest (the camera works during an Android reboot). `gm_update_engine` stages OTA packages and writes the BCB (`boot-recovery` / `--show_return_to_dealer`) to `misc`; the on-screen rendering is GHS. See `hardware/teardown.md` §GHS as Recovery Architecture. History: corrects an earlier claim that "GHS is headless / has no UI rendering".

---

## GHS-Android Connection Map

Channels between GHS tasks and the Android guest (static RE of GHS strings).

| Group | Connection | Purpose |
|-------|------------|---------|
| VMM | `ConnToAndroidVMM` | Primary VMM control channel |
| VMM | `ConnToVMM_Camera` | Camera pipeline coordination |
| VMM | `ConnToVMM_Display` | Display/framebuffer management |
| VMM | `ConnToVMM_Chime` | Chime audio routing |
| VMM | `ConnToVMM_Cal` | Calibration data access |
| VMM | `ConnToVMM_OTA` | OTA update coordination |
| VMM | `ConnToVMM_TextLog` | Log forwarding to GHS |
| Camera | `ConnToCamera` (x6) | 6 camera connections (IPU4 pipeline) |
| Audio | `ConnToChimes` | Chime audio task |
| Audio | `ConnToDirana` | Dirana tuner/DSP |
| VIP | `ConnToVIP` | Primary VIP communication |
| VIP | `ConnToVip_Lifecycle_API` | Lifecycle/shutdown coordination |
| TEE | `ConnToTEE_Keymaster` | Hardware keymaster operations |
| TEE | `ConnToTEE_Storage` | Secure storage (RPMB) |
| TEE | `ConnToTEE_Router` | TEE message routing |
| TEE | `tipc_conns` | Trusty IPC connections for TEE |

VIP-side IPC channel numbering/protocol versions: [vip_ipc_ghs.md](vip_ipc_ghs.md).

---

## Update Engine

- **Primary:** `gm_update_engine` + Red Bend UA (`/vendor/bin/rb_ua`)
- **Image format:** Raw partition images (all RAW, not delta)
- **Extension functions:** `gmext` functions for GM-specific update logic
- A/B slot switching is coordinated between GHS and the Android boot control HAL

### Manifest Command Sequence

Updates are executed in 5 phases via `gmext` extension functions:

```
Phase 1 - Direct eMMC writes:
  gmext.write_emmc_image("23", boot)     # partition 23 = boot image
  extract vbmeta, acpio, bootloader      # from update package

Phase 2 - ECU updates via VIP MCU:
  gmext.update_ecu("71", VIP_BOOT)
  gmext.update_ecu("1",  VIP_APP)
  gmext.update_ecu("21", HOSTOS)
  gmext.update_ecu("72", ABL)

Phase 3 - Slot switch:
  gmext.switch_slot()                    # A<->B toggle in misc metadata

Phase 4 - Dynamic partition extraction:
  gmext.extract_logical_partition(system  ~3.0GB)
  gmext.extract_logical_partition(vendor  ~445MB)
  gmext.extract_logical_partition(product ~2.5GB)

Phase 5 - Peripheral firmware:
  TUNER, ETH_SWITCH, GPS, SXM
```

Red Bend UA (`/vendor/bin/rb_ua`) handles OTA delivery from GM Cloud. Broader update stack, flag files and programming roles: [ota_update_stack.md](ota_update_stack.md), [ota_programming_roles.md](ota_programming_roles.md) (restored here because the owner doc does not carry the manifest sequence).

---

<a name="gsidsu-status"></a>

## GSI/DSU Boot Gate

GSI (Generic System Image) and DSU (Dynamic System Updates) are **disabled by app removal, not by the SELinux rule previously cited** (History: corrects an earlier claim that `dontaudit gm_update_engine gsi_metadata_file` blocks GSI installs).

**Consistent across Y175, Y177, Y181.** All three USB full packages ship the stock `gsid`/`gsi_tool` daemon and keep the `com.android.dynsystem` entry in `privapp-permissions-platform.xml`, but none include the `com.android.dynsystem` APK in any app dir. The removal predates the oldest sampled build (Y175): standing GM build policy. Y177 (earlier mislabeled "the permissive-SELinux build", retracted 2026-08-26; it runs enforcing) also lacks the app, so a Y177 downgrade does not restore DSU.

- **DSU daemon retained.** `gsid.rc` in init; `gsid`/`gsi_tool` on the image. `gsid` has its full stock SELinux policy (~50 allow rules in `plat_sepolicy.cil`): can create/write `gsi_metadata_file`, `gsi_data_file`, `ota_image_data_file`, drive `dm_device`/loop devices, touch `userdata_block_device`, hold `sys_admin`, set `gsid_prop`, add/find `gsi_service`. The `dynamic_system` service is registered.
- **Front-end app removed.** `com.android.dynsystem` is absent from the live package set (89 packages on a Y181 Apr-2026 dump, heavily stripped AAOS). `am start-activity -n com.android.dynsystem/…VerificationActivity -a android.os.image.action.START_INSTALL` fails with *activity-does-not-exist*, not a policy denial.
- **Why the old claim was wrong.** `dontaudit` only suppresses the audit log of a denial that already exists from the absence of an allow rule. It targets `gm_update_engine` (GM's OTA A/B engine), not the DSU path, and has no effect on `gsid`. (The rule exists, in `vendor_sepolicy.cil`; it is not a GSI blocker.)
- **Direct `gsi_tool` path is closed by other walls:** `ro.build.type=user`, `ro.debuggable=0` (shell is uid 2000), and `gsid` requires `MANAGE_DYNAMIC_SYSTEM` (signature-or-privileged), which shell lacks.
- **GSI boot is gated by locked verified boot:** `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.verifiedbootstate=green`, `sys.oem_unlock_allowed=0`. fstab trusts only Google GSI keys (`avb_keys=/avb/q-gsi.avbpubkey:/avb/r-gsi.avbpubkey:/avb/s-gsi.avbpubkey`); only a Google-signed GSI could pass AVB and verification cannot be disabled on a locked unit.
- No dedicated recovery partition (recovery embedded in the boot image); all updates are A/B only.
- **[U] CSM-ownership / AOSP-replacement chain (2026-09-10 assessment, OPEN).** The unit is locked (green, `ro.boot.flash.locked=1`, `sys.oem_unlock_allowed=0`, dm-verity RO): this is a gate description, not a solved path. ELK eligibility/provisioning checks and transition limits: [`../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#232-elk-unlock-eligibility-is-a-separate-gate-verified-2026-11-12). No demonstrated unlock procedure. Boot Guard/signature trust/varstore questions: see [Boot-lock state and Boot Guard](#boot-lock-state-and-boot-guard-soc_abl--kernelflinger-analysis) and [security.md](security.md).

**Confirmed at firmware-image level ([C] Sep 2026).** Unpacked Y181 USB full package (SOC_SYSTEM 86331654, SOC_VENDOR 86331650, SOC_PRODUCT 86331636):
- `com.android.dynsystem` is absent from every app dir across all three images (`system/app`, `system/priv-app`, `system/system_ext/priv-app`, `product/app`, `product/priv-app`); no GM-renamed variant exists.
- Stock DSU daemon set present and unmodified: `system/bin/gsid`, `gsi_tool`, `snapshotctl`, `lpdump`/`lpdumpd`, `libgsi.so`, byte-stock `gsid.rc` (creates `/metadata/gsi/dsu`, `/data/gsi/dsu`, etc.). The block is purely the missing app.
- The Developer Options DSU Loader (`CarDeveloperOptions.apk`, `DSUTermsOfServiceActivity.installDSU()`) calls `setClassName("com.android.dynsystem","…VerificationActivity")` + `startActivity`, so the button throws ActivityNotFound. Not a GM reimplementation.
- The only other "replace /system" path is `gm_update_engine` (GM fork of A/B update_engine, `/vendor/bin/hw/`): zero GSI/dynamic-system/dev-signed/unsigned strings, mandatory RSA+SHA+FCID verify (`SignatureVerifier.cpp`, OpenSSL `EVP_DigestVerify`); accepts only GM-signed packages. `GMSWUpdater.apk` is a UI shell with no DSU/GSI code.
- Cross-checked against the 2024 Silverado ICE OS dump (live `packages.txt`, `all_properties.txt`, `plat_sepolicy.cil`/`vendor_sepolicy.cil`, plus unpacked Y181 images decompiled with 7z + jadx).

---

## Pointers to other owners

| Topic (source range) | Owner |
|----------------------|-------|
| Update engine, Red Bend UA, 5-phase manifest sequence | This doc ([Update Engine](#update-engine)); wider stack in [ota_update_stack.md](ota_update_stack.md), [ota_programming_roles.md](ota_programming_roles.md) |
| USB trigger files (Base64 recovery markers, `gm_usb_*`) | This doc ([USB Trigger Files](#usb-trigger-files)); `--show_return_to_dealer` and bench test in [elk_recovery.md](elk_recovery.md) |
| 26-partition map (vda1-26), critical partitions, dynamic partitions/`super`, SSDT static-A/B question | [partitions_storage.md](partitions_storage.md) |
| ELK/Probe/recovery fastbootd, boot-candidate order, bench recovery tests | [elk_recovery.md](elk_recovery.md) |
| Qualcomm Cadillac boot/VIN gate (VIN is the only boot gate, CAN IDs `0x712`/`0x75F`/`0x49B`, "Theft Locked" overlay, locked bootloader/efuses) — compare Intel unit's `Theftlocked Active` / `evTheftlockedCleared` VIP states | [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md), [vehicle_network.md](vehicle_network.md) |
| SELinux posture, kernel mitigations, FBE, Trusty | [security.md](security.md) |

---

## Open conflicts

1. **SOC_ABL signed vs unsigned.** Module Signing table lists SOC_ABL as *Unsigned* (`boot_chain.md` L633) while the trust table calls it a "~6MB signed image" in Intel IPK format and the 85738845 IPK contains production-signed `oem.key` and `IBBP.man` manifests (`security.md` L58-59, L87-95). Possible reconciliation (not established): "unsigned" refers to the TSS package-level signature; the image carries its own Intel IFWI signing. Not resolved in source.
2. **Super size / static-A/B** — `8.6GB` (source L335, L355) vs Y175 measured 18000 MiB (source L379-387); SSDT static-A/B reading (source L362-369) vs update-engine use of `super` (L371-377) vs refutation in QEMU 2026-09-27 and Y175 measurement 2026-11-17. Single conclusion owned by [partitions_storage.md](partitions_storage.md); real Y181B hardware resolution via the SSDT remains unconfirmed (source L398-400).
3. **Owner of `ttyS1` / VIP HDLC.** Here (source L44-50) HDLC is terminated in the GHS-side `VIP_InitialTask` with the guest using a userspace `IPCServer` protocol via `ipc4.cfg`; `emulator.md` L75-76 and `hardware.md` L195, L204, L279 describe the guest's `/dev/ttyS1` (`ipc_serial_device`) as the HDLC link used by `IPCServer`; IAP L167-170 assigns guest UART0+UART3 to Android and repurposes UART1 for VIP IPC. Unreconciled; owner [vip_ipc_ghs.md](vip_ipc_ghs.md).
4. **SELinux mode on cmdline vs runtime.** Retained Y181B cmdlines carry both `permissive` and later `enforcing` tokens; "later pair wins" is inferred [U]. `emulator.md` real-kernel build boots permissive by its own cmdline (`emulator.md` L48-87), while the goldfish hybrid enforces. Not a hardware contradiction; see [security.md](security.md) / [emulator.md](emulator.md).
5. **BCB `boot-see-dealer` (modes table) vs observed `boot-recovery` + `--show_return_to_dealer`** in retained recovery records of a see-dealer entry (source L492). Both kept; the table is from static RE, the latter from bench observation.
6. **`ABL.secureboot=1` hit count**: 386 vs ~188 (archive) vs 376 (duplicate-export double count). Recount dated 2026-11-12 is the latest; kept as stated.
