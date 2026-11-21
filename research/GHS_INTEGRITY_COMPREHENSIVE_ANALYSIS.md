# GHS INTEGRITY Hypervisor — Comprehensive Analysis

**Binary:** SOC_HOSTOS (85098662), INTEGRITY IoT 2020.18.19, Core 23739 / Modules 11500,
GM Version MY22-026, target Intel Apollo Lake (gm-i35). Build path
`/home/mal/gm_release/MY22-026/final/iot/rtos/`.
**Format:** ELF header claims 32-bit LSB/Intel 80386, but the code is x86-64 (`movabs`/REX-prefixed
instructions, `crt_x64.86`/`libkernel.86_x64`; disassemble as `x86:LE:64`, not 32-bit — corrected
2026-08-26). Statically linked; kernel symbols retained, task/application symbol coverage incomplete.
**Image identity:** all available Y175/Y177/Y181/Y181B copies of `85098662` are byte-identical —
14,929,956 B wrapper, SHA-256 `317ae85ccf759476755411e66593dde9f879a43732cd342b4e101e4026535ed3`.
Stripping the 0x27c wrapper yields the analyzed `hostos.elf` byte-for-byte (SHA-256
`d900af484f466b35f4d9153ddf8adf19482f91d728b707f10fe89d326d4870df`, 14,929,320 B — the two sizes
reconcile exactly: `14,929,956 − 636 (0x27c) = 14,929,320`, not a conflict). Saved Ghidra project:
9,424 functions, language `x86:LE:64:default`, image base `0x00200000`, higher-half base
`0xffff800000000000` (kernel absolute references use this base; addresses below omit it unless noted).

## Scope

This is the GHS INTEGRITY hypervisor's own architecture and RE inventory: PCI driver table, task
list, IPC `ConnTo*` map, VMM/VT-d/guest-memory function lists, the `.boottable`-derived guest/VM
configuration (§7A), `/dev/ghs/*` + SELinux labels, the attack-surface catalog (§11), and the
consolidated privacy-capability assessment (§12, formerly split across old §13-15).

**Not here** — boot phases, special boot modes, recovery/fastbootd/ELK privilege boundaries, the
SBI→MEC→ADB-cert bypass chain, A/B+BCB+trigger-file mechanics, and live binary-provenance/security
evidence: see `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` (GBUR). Byte-level section/offset map of this
same image: see `GHS_FILE_MAP_85098662.md` (GFM). EEPROM memory map and SBI-bypass mechanism:
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` (ELA). SecurityAccess/seed-key/calibration-signature detail:
`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK). Y181→Y177 downgrade/rollback mechanism:
`GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt` (GDP). AVB/vbmeta parser fuzzing and the confirmed
`avb_*` guard-function RE (in `elk_inner.elf`, not `.vmm1`): `VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`
(VPF) — this doc's §6/§11 keep only the static AVB *function-name* inventory, not that guard RE.

**Retired into this doc:** `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` was a 9-line pure redirect stub
pointing at this doc's former §15 ("privacy-capability-assessment-consolidated"). Confirmed: that
target existed and is now folded, with former §13/§14 (which duplicated §15, see History), into
§12 below. The stub is retired; nothing else needed migrating from it.

## Evidence tags

Reuses the platform legend: `[C]` confirmed live, `[V]` verified, `[FW]`/`[S]` static firmware,
`[inferred]`, `[U]` unverified, `[X]` external. This doc's own `[FW 85098662; 3-Opus verified
2026-10-10]` tag (independently re-derived from firmware bytes by three Opus agents) is the
`[FW]`/`[V]` tier; `[UNVERIFIED]` is this doc's `[U]`. Only §7A carries per-claim tags in the
source material; §1, §3-§6, §8-§11 are untagged static string/symbol inventory (radare2/Ghidra) —
treat as `[FW]`-tier but behaviour-*unverified* unless a tag says otherwise. §12 (privacy
capability) is explicitly capability inference, not measured behaviour — see its own caveats.

## Related

`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`, `GHS_FILE_MAP_85098662.md`,
`GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`, `VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`,
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`, `USB_ADB_SESSION_FINDINGS_2026-10-10.md`,
`HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` (dual-owns the VIP-IPC/ELK-trigger catalog entry),
`../platform/boot_chain.md`, `../platform/security.md`, `../platform/ethernet_networking.md`,
`../video/display_subsystem.md`, `../runtime/boot_timing.md`.

---

## 1. System Overview

| Property | Value |
|----------|-------|
| **OS** | INTEGRITY IoT 2020.18.19 |
| **Core Version** | 23739 |
| **Modules Version** | 11500 |
| **GM Version** | MY22-026 |
| **Build Path** | /home/mal/gm_release/MY22-026/final/iot/rtos/ |
| **Vendor** | Green Hills Software |
| **Target Platform** | Intel Apollo Lake (gm-i35) |

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HARDWARE LAYER                                    │
│  Intel Apollo Lake SoC (Broxton)                                     │
│  • 4x CPU cores (x86-64)                                             │
│  • Intel IPU4 (Camera)                                               │
│  • Intel HD Graphics (Gen9)                                          │
│  • Intel HECI (Management Engine)                                    │
│  • Intel LPSS (UART, I2C, SPI)                                       │
├─────────────────────────────────────────────────────────────────────┤
│                    GHS INTEGRITY HYPERVISOR                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ VMM (Virtual Machine Monitor)                                │    │
│  │  • VMX (Intel VT-x)                                          │    │
│  │  • VT-d (IOMMU)                                              │    │
│  │  • EPT (Extended Page Tables)                                │    │
│  │  • Guest Memory Management                                    │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Kernel Services                                              │    │
│  │  • Task/Thread Management                                    │    │
│  │  • Memory Management                                          │    │
│  │  • Interrupt Handling                                         │    │
│  │  • IPC (Inter-Process Communication)                          │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Device Drivers                                               │    │
│  │  • PCI Device Drivers                                         │    │
│  │  • Passthrough Drivers                                        │    │
│  │  • I/O Device Management                                      │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Security Services                                            │    │
│  │  • Trusty TEE (Keymaster, Gatekeeper)                         │    │
│  │  • Secure Boot Validation                                     │    │
│  │  • Android Verified Boot (AVB)                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│                    GUEST VM (Android)                                │
│  • Linux Kernel                                                      │
│  • Android Framework                                                 │
│  • GM Applications                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

Boot sequence and boot-command construction are owned by
[GBUR §1](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#1-ghs-boot-process); not duplicated here.

### Guest-side hypervisor evidence and GHS partitions

*(Folded from retired `UPDATE_PROCESS_ANALYSIS.txt` §3.1-3.2, original analysis 2025-12-28, source
`analysis/adb_Y181/gm_enum_20251220_081558/raw/`.)*

Android-guest-side confirmation that it runs under GHS, independent of the hypervisor-side RE above:

- `cpuinfo`: `hypervisor` flag present on all 4 CPU cores.
- Kernel config: `CONFIG_GHS_GUEST_COMMS=y`, `CONFIG_GHS_PARAVIRTUAL_SUPPORT=y`,
  `CONFIG_GHS_VMM_BOOTLOADER_CONTROL=y`, `CONFIG_ANDROID_GM_GHS_MMC=y`, `CONFIG_SND_GHS_PCM=y`,
  `CONFIG_HYPERVISOR_GUEST=y`.
- Property `[ro.boot.trustyimpl]: [-ghs]` — Trusty implemented via GHS (see §6 Trusty TEE below).
- VIP log (`VIP_log_2B.174.4.1_10JUL24.txt`): `[PLC] plc_timer_value for Hypervisor Startup Timeout
  = 300`.

GHS image partitions (source: `partitions.txt`):

| Partition | Device | Purpose |
|----------------|--------|----------------------------|
| `ghs_isys_a` | vda1 | GHS INTEGRITY image (A) |
| `ghs_isys_b` | vda2 | GHS INTEGRITY image (B) |
| `ghs_storage` | vda3 | GHS persistent storage |
| `ghs_abl_update` | vda4 | CSE+ABL SPI reflash capsule, not a runtime stage ([BOOT_TRUST_ANCHOR_AND_KEYS.md §3](BOOT_TRUST_ANCHOR_AND_KEYS.md#3-soc_abl--elk-kernelflinger-and-ghs_abl_update)) |
| `ghs_log` | vda24 | GHS logging |

`ghs_storage` (vda3) is also where the Y175 `remote_display` task writes `EARLY_CALS`: it reads the
active screen-resolution calibration, compares it against the live EDID, and updates `EARLY_CALS`
in `ghs_storage` when they differ *(folded from retired `SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md`'s
2026-11-17 display-path-trace footnote)*. GHS brightness ownership and the actual LTZ/HC curves are
owned by [`../video/display_subsystem.md`](../video/display_subsystem.md#y175-panel-ownership-and-initialization--verified-2026-11-17-extended-2026-11-17),
not restated here.

---

## 3. PCI Device Drivers

| Driver | Hardware | Purpose |
|--------|----------|---------|
| `IntelIpu4` | Intel IPU4 | Camera image processing |
| `gen9` | Intel HD Graphics | GPU passthrough |
| `gmch` | Intel GMCH | Memory controller |
| `hda_mm_init` | Intel HDA | Audio controller |
| `heci` | Intel HECI | Management Engine interface |
| `LpssUart` | Intel LPSS UART | Serial ports |
| `LpssI2c` | Intel LPSS I2C | I2C bus |
| `spi` | Intel SPI | SPI bus |
| `sdhc` | SD Host Controller | eMMC/SD storage |
| `sdhc_passthru` | SD Passthrough | Storage virtualization |
| `i8254x` | Intel NIC | Ethernet controller |
| `xhc` / `xhci` | USB xHCI | USB 3.0 controller |
| `ehci` | USB EHCI | USB 2.0 controller |
| `xdci` | USB xDCI | USB device controller |
| `gpio` | Intel GPIO | GPIO controller |
| `p2sb` | Intel P2SB | Sideband interface |
| `gm_eth` | GM Ethernet | Ethernet passthrough |
| `gm_wifi` | GM WiFi | WiFi passthrough |
| `gm_audio` | GM Audio | Audio passthrough |
| `uart` | UART | Serial passthrough |
| `i2c` | I2C | I2C passthrough |

21 named drivers; Appendix A's function-count block states 22 — see Open Conflicts.

---

## 4. GHS Tasks (Processes)

<!-- corrected 2026-11-21: this table was a string-based inventory from early analysis; §7A.1 (boottable-derived, 2026-10-10) names 19 server address spaces. The 5 entries below marked [added 2026-11-21] were absent from the original string pass. -->

| Task | Purpose |
|------|---------|
| `VMM1_InitialTask` | Android Virtual Machine Manager |
| `Camera_InitialTask` | Camera subsystem management |
| `Audio_InitialTask` | Audio subsystem management |
| `GPU_InitialTask` | GPU/Display management |
| `Chimes_InitialTask` | Chime/alert sounds |
| `Dirana_InitialTask` | Dirana audio DSP |
| `DisplayI2C_InitialTask` | Display I2C interface |
| `VIP_InitialTask` | VIP MCU communication |
| `Lifecycle_InitialTask` | System lifecycle management |
| `OTA_InitialTask` | OTA update handling |
| `Lines_InitialTask` | Lines/graphics |
| `Calibrations_InitialTask` | Calibration data |
| `TEE_Keymaster` | Trusted keymaster |
| `TEE_HW_Crypto` | Hardware crypto |
| `TEE_Gatekeeper` | Gatekeeper server [added 2026-11-21; `.tee_gatekeeper` section confirmed GHS_FILE_MAP_85098662.md; §7A.1 boottable] |
| `TEE_Router` | TEE router — fans tipc to TEE_* servers (`TEEAtt` is a VMM1 connection here, not a separate AS; see §7A.4) [added 2026-11-21] |
| `TEE_Storage` | Secure storage server [added 2026-11-21; §7A.1 boottable] |
| `Audit` | Security audit log server (.audit section, GHS_FILE_MAP; §7A.1) [added 2026-11-21] |
| `EMMC` | eMMC mux server (.emmc_mux section; GHS mediates eMMC to guest; §7A.1) [added 2026-11-21] |

---

## 5. Inter-Process Connections

```
┌──────────────────────────────────────────────────────────────────┐
│                    GHS IPC CONNECTIONS                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  VMM (Android Interface)                                          │
│  ├── ConnToAndroidVMM                                             │
│  ├── ConnToVMM_Camera                                             │
│  ├── ConnToVMM_Capture                                            │
│  ├── ConnToVMM_Display                                            │
│  ├── ConnToVMM_Chime                                              │
│  ├── ConnToVMM_Cal                                                │
│  ├── ConnToVMM_OTA                                                │
│  ├── ConnToVMM_OTA_Control                                        │
│  ├── ConnToVMM_EMMCHealth                                         │
│  ├── ConnToVMM_TextLog                                            │
│  └── ConnToVMM_Audit                                              │
│                                                                   │
│  Camera Subsystem                                                  │
│  ├── ConnToCamera                                                  │
│  ├── ConnToCamera_Camera                                           │
│  ├── ConnToCamera_Capture                                          │
│  ├── ConnToCamera_Display                                          │
│  ├── ConnToCamera_I2C                                             │
│  └── ConnToCamera_RvcStatus                                       │
│                                                                   │
│  Audio Subsystem                                                   │
│  ├── ConnToChimes                                                  │
│  ├── ConnToChimes_Chime                                            │
│  └── ConnToDirana                                                 │
│                                                                   │
│  VIP MCU                                                           │
│  ├── ConnToVIP                                                     │
│  └── ConnToVip_Lifecycle_API                                      │
│                                                                   │
│  Trusted Execution Environment                                     │
│  ├── ConnToTEE_Keymaster                                          │
│  ├── ConnToTEE_Storage                                            │
│  ├── ConnToTEE_Router                                             │
│  └── ConnToTEE_TEEAtt                                             │
│                                                                   │
│  System Services                                                   │
│  ├── ConnToLifecycle                                              │
│  ├── ConnToCalibrations                                           │
│  ├── ConnToOTA                                                    │
│  ├── ConnToGPU                                                    │
│  ├── ConnToDisplayI2C                                             │
│  ├── ConnToEMMC                                                   │
│  └── ConnToAudit                                                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

The VIP IPC channel (`ConnToVIP`) coordinates EEPROM-bypass and ProtoKey transmission; mechanism
owned by ELA and GSK respectively, not restated here (see §11 item 7).

---

## 6. Security Mechanisms

Binary fingerprints, extraction boundaries, debugger evidence, historical CVE applicability, and
this image's live/verified security-evidence state are maintained in
[GBUR's 2026-11-12 provenance note](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#01-y181b-binary-provenance-and-security-evidence-2026-11-12);
what follows is this doc's own static function/string inventory only — an inventory of compiled
checks, not proof any of them are live-enforced on a given boot.

### Android Verified Boot (AVB)

```
VMM Validation Functions:
├── Load vbmeta partition
├── Verify vbmeta signing key
├── Validate vbmeta header
├── Parse vbmeta descriptors
├── Load boot partition
├── Verify boot image signature
├── Validate boot image header
├── Check kernel and ramdisk hashes
├── Verify rollback index
└── Set androidboot.verifiedbootstate

Error Messages:
• "VMM: Error: vbmeta signing key does not match known valid key"
• "VMM: vbmeta: image verification failed!"
• "VMM: ERROR: rollback index is too old"
• "VMM: Error: Android signature verification failed"
• "VMM: Failed to verify slot %s"
```

This is a name/string inventory only. The confirmed guard-function RE (`avb_descriptor_validate_and_byteswap`,
`avb_safe_add_to`, `avb_vbmeta_image_verify`, matched to upstream libavb and located in `elk_inner.elf`,
**not** `.vmm1`) is owned by VPF — not restated here.

### Trusty TEE

```
TEE Components:
├── TEE_Keymaster - Key generation, storage, crypto
├── TEE_HW_Crypto - Hardware crypto acceleration
├── TEE_Storage - Secure storage (RPMB)
└── TEE_Attestation - Device attestation

Key Files:
├── tee_keymaster.text/data/rodata
├── tee_hw_crypto.text/data/rodata
└── rom.tee_keymaster.data

IPC Channels:
├── tipc_conns (Trusty IPC)
└── ConnToTEE_* connections
```

`TEE_Attestation` above is the IPC label used in the string inventory; §7A.4 narrows this —
`TEEAtt` is a VMM1-side connection to `TEE_Router`, not its own address space (see §7A.4).

### Secure Boot

```
Boot Security:
├── ABL.secureboot=1
├── CRC error in FLASH, failing
├── SHA-1 hash error in FLASH, failing
├── CRC error in RAM, failing
└── SHA-1 hash error in RAM, failing
```

**History (2026-11-12):** `ABL.secureboot=1` is a cmdline token retained in kernel-log archives
(hit count ~188; an earlier reading of `386` did not reproduce) — it is a cmdline indicator, not a
verified secure-boot *state*: the live property `getprop ro.boot.ABL.secureboot` reads empty. Treat
every occurrence of "secure boot" below (including §12's) as this unverified cmdline token, not a
confirmed enforcement state; see `../platform/boot_chain.md`.

---

## 7. VMM (Virtual Machine Monitor)

### Intel VT-x Implementation

```
VMX Functions:
├── ASP_VMX_Init
├── ASP_VMX_InitializeOnBootCpu
├── ASP_VMX_InitVMCS
├── ASP_VMX_SetupMsrBitmap
├── ASP_VMX_MapEptHelper
├── ASP_VMX_UnmapEptHelper
├── ASP_VMX_PostInterrupt
├── ASP_VMX_GetRegister
├── ASP_VMX_SetRegister
└── VMX_Run

VT-d (IOMMU):
├── ASP_VTD_Init
├── Vtd_Initialize
├── Vtd_EnableVtdForDevice
├── Vtd_ActivateDmaRemappingUnit
└── Vtd_InvalidateAfterEnablingDevices
```

**VT-d tables are built at runtime** `[FW 85098662; 3-Opus verified 2026-10-10]`: `Vtd_EnableVtdForDevice`
(va `0x23110b`) indexes the root table by bus and the context table by `dev*8+fn`, allocating a 4 KiB
context table on demand from `vtdFreePages`. There is **no `.vtdpagetable` section** in the image;
that string is an error message only. The guest itself runs `intel_iommu=off` and sees no DMAR. See
§7A.4.

### Guest Memory Management

> Grant/visibility numbers (7830 MiB granted vs 5530 MiB guest-visible) are in §7A.3.

```
Memory Functions:
├── ReadGuestMemory
├── WriteGuestMemory
├── ReadGuestVirtualAddress
├── WriteGuestLMA
├── DirectCopyIntoVAS
├── VMM_GuestRamOffsetToHostPAddr
├── XhcVc_SetGuestMemoryMap
└── XhcVc_SetGuestMemoryOffset

VM Control:
├── ASP_RunGuestVM
├── ASP_ResetVCpu
├── ASP_InjectInterruptInVCpu
├── VMM_PendVCpu
├── VMM_UnpendVCpu
└── VMM_ExitVMCallback
```

---

## 7A. Guest/VM Configuration (boottable-derived)

All items `[FW 85098662; 3-Opus verified 2026-10-10]` unless marked `[UNVERIFIED]`. Source: the
`.boottable` section (section 177, 27 AddressSpace records, 23 Task records, per-AS object and
memory-map tables). Section layout: `GHS_FILE_MAP_85098662.md`. (Full byte-level derivation notes
were kept at a `/tmp` scratch path during this analysis and are not part of this repo — not a
resolvable link; the tables below are the durable record of that derivation.)

### 7A.1 Topology: exactly one VM

- **27 INTEGRITY address spaces** = kernel (AS0) + 19 named servers + 6 unnamed VT-d DMA domains + **Guest1 (AS25)**.
  Named servers: VIP, Lifecycle, Audit, Dirana, Chimes, Audio, Camera, Lines, OTA, Calibrations, GPU,
  DisplayI2C, TEE_Router, TEE_Keymaster, TEE_Gatekeeper, TEE_HW_Crypto, TEE_Storage, EMMC, plus **VMM1** (AS24).
- **Exactly ONE VM: Guest1 (Android).** AS25 is the only guest-flagged partition (flags 0x4411;
  servers 0x1001, VMM1 0x1011, DMA domains 0x2401; flag-bit meanings `[UNVERIFIED]`, grouping by observation).
- **No QNX / cluster guest.** The VIP is an external RH850 MCU reached over `SerialDev1`; the GHS `VIP`
  server is only its peer. Every other AS is a native INTEGRITY server or an IOMMU domain.
- VMM1 (`pc_emul`, prio 35) is the pass-through broker and console/log sink; it holds the `Guest_VCpu0..3` links to the vCPU tasks (the GPU server holds its own `Guest1_Core0..3Task` links).

### 7A.2 vCPUs and scheduling

| Item | Value |
|---|---|
| vCPUs | **4**: `Guest1.Initial` prio 30, `Guest1.VCpu1/2/3` prio 29 |
| Priority rank | the **lowest in the system** (TEE_* 40, VMM1 35 ... VIP 100; higher number = higher priority) |
| Guest `/proc/cpuinfo` | 4 processors, "IoT CPU 1.0", family 6 model 92, 1881.6 MHz (agrees) |
| Scheduler | **pure priority; no time partitioning / ARINC-653** |

The scheduler claim rests on `__PartitionSchedulerInitPtr` (va `0x84a2a8`) = 0 and every
`BSP_Partition*` / `__PartitionScheduler*` symbol being an undefined external. Android therefore
runs in whatever CPU time the servers leave and has no time budget. The vCPU count is data-driven
(`ASP_VMX_SetVcpuQueueAddr`, `ASP_ResetVCpu` with a 0x3000-byte per-vCPU block); the static source of "4"
is the boottable task list plus the DSDT `_PR` CPU0-3.

### 7A.3 Guest memory

| Quantity | Value |
|---|---|
| Physical DRAM | 8 GiB LPDDR4 |
| **Granted to Guest1 by GHS** | **7830 MiB** (0x1_E960_0000) in five RAM regions, plus a **34 MiB read-only IPU frame window** (`Kernel_IpuFbPMR` at GPA 0x3_fde0_0000) |
| Reserved by GHS | **~362 MiB** (8192 - 7830), the kernel, servers, GVT-g/Lines/VMM buffers and DMA PMRs below 4 GiB |
| Guest-visible `MemTotal` | **5530 MiB** (5663432 kB, identical on Y175 and Y181) — this is the AAOS-reported *runtime* figure, not the static grant; see the measured E820 map below for why it differs. |

The 7830 MiB figure is byte-confirmed from the MR table and is **not an MMIO over-count**: the GPA hole
0x8000_0000-0xFFFF_FFFF (PCI window) is not part of any granted region. The ELF program headers under-report
(RAM0/RAM1 only; RAM2-4 are plain physical ranges), so the boottable MR table is authoritative.

**History (2026-11-12) — measured Y181B recovery map:** the
[recovery USB export](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12)
supplies the previously unavailable kernel E820 evidence. In the first archive,
`update_cache/recovery/last_kmsg`, lines 3–10, advertises these usable ranges:

| Guest physical range, inclusive | Usable size |
|---|---:|
| `0x00000000–0x0009efff` | 0.62109375 MiB |
| `0x00100000–0x7ffeffff` | 2046.9375 MiB |
| `0x100000000–0x1e6ffffff` | 3696 MiB |
| Total | **5743.55859375 MiB** |

Line 94 reports `Memory: 5638316K/5877304K available`, including 238988K
reserved. The denominator is about 5739.55 MiB; neither this early boot value
nor its available numerator is a later `/proc/meminfo` `MemTotal`. The second
export retains the same E820 ranges and denominator; its available numerator
is 5638324K, an 8 KiB difference in this boot's reservations.

The observed map narrows the visibility gap without identifying why it differs
from the statically calculated 7830 MiB guest grant. The old 5780 MiB/RAM4-cap
proposal is a hypothesis, not the measured E820 total. Do not charge the entire
grant-to-`MemTotal` gap to GHS consumption, or treat emulator `-m` as an E820
reproduction. Normal-AAOS parity with this recovery map and the VMM1 builder's
range-selection logic still need verification.

The same first-archive kernel log confirms `Hypervisor detected: GHS VMM`
(line 23), four brought-up CPUs (line 157), Intel GVT-g virtual GPU detection
(line 392), and a 124,993,536-sector virtio block disk (line 405). This is guest
enumeration evidence; it does not expose the physical eMMC identity or prove
that every peripheral is directly assigned.

### 7A.4 Device grants (who owns what)

**Granted to Guest1 (18 IODevices):** XHCI0, XDCI, GmEth, GmWifi, GmWifi.1, I2C0, I2C1, I2C2, I2C4, I2C5,
UART0, UART3, SPI0, SPI1, SPI2, Gen9 (GVT-g mediated), DVFS_RESOURCE, PerfMon_Resource. VMM1 holds the same
IODevices (brokering interrupts for GmEth/GmWifi).

**Kept by GHS, mediated through VMM1:** eMMC/SDHC (EMMC server multiplexes), HDA audio (Audio server),
IPU camera (Camera server), I2C3 (Dirana), I2C6 (Camera), I2C7 (DisplayI2C), RTC, P2SB, SerialDev0,
and the VMM1-mediated GPIO passthrough set (GPIO_0..30, 106, 203). DMA-visible memory for the
passthrough set is confined to the guest GPA map.

**History (2026-11-17):** the GPIO list above is the *VMM1-mediated passthrough set*, not literally
every GPIO pin GHS exposes — `video/display_subsystem.md`'s `display_i2c` server disassembly holds
its own `IOD_GPIO_33` (panel serializer reset/PDB) and `IOD_GPIO_15` (panel serializer interrupt)
objects directly, not through VMM1. Treat the display path as the known exception to "VMM1 owns all
GPIO," not as evidence the rest of the list is wrong.

**VT-d / IOMMU:** root/context tables are built at runtime (no `.vtdpagetable` section, see §7). Six unnamed
ASes are pure DMA domains: HDA, IPU, Lines, EMMC/SDHC, GPU_Dom_Gen9, GVTG_Dom. The guest runs
**`intel_iommu=off`**, so all isolation is host-side.

**GVT-g:** the GPU server (`gvtg_server`, AS15) mediates the Gen9 GPU (GuC/HuC firmware in the server) and maps the
whole of guest RAM; the guest sees a GVT-g vGPU (`ro.hardware.gralloc/hwcomposer=broxton`).

**TEE:** keymaster, gatekeeper, HW crypto and storage are GHS-side servers (TEE_Router fans tipc connections out to
them); the guest is told `androidboot.trustyimpl=-ghs`. (`TEEAtt` is a VMM1 connection to TEE_Router, not a separate
server; the "TEE_Attestation" box in §6 is a connection, not an address space.)

#### Ethernet initialization and guest ownership code trace (2026-11-14)

| Normalized address / function | Located logic |
|---|---|
| `0x002251b6`, `PciInit` | Sets up MSI resources, creates the legacy PCI domain and calls `PciDomain_InitializeDevices`. |
| `0x002332d1` / `0x00233209` | `pci_initialize_devices` scans PCI and allocates MSI resources; `device_init` dispatches registered driver callbacks, including the initialization callback at driver-record offset `+0x20`. |
| `0x0023c6c0`, `gm_eth_driver_match` | Checks packed PCI vendor/device IDs `157c8086`, `15338086`, `10d38086`, `105e8086`, `15318086`, then calls `Passthru_PciDeviceMatch`. The set includes `8086:1533`, consistent with the documented Intel I210. |
| `0x0023e53e`, `Passthru_PciDeviceMatch` | Matches the device's PCI path against configured passthrough paths and returns the selected binding. This is host resource matching, not an AVTP packet producer. |
| `0x0023c6f8`, `gm_eth_driver_init` | Copies a six-word IO-device descriptor naming `GmEth`, stores device properties and calls `IOAccessor_InitFromList`. A counter limits this registration path to two instances. It does not directly call the PHY/link/RX/TX setup sequence below. |
| `0x02203958`, `__ghsentry_pci_device_driver_gm_eth` | PCI-driver registration record contains the match pointer at `+0x08` and `gm_eth_driver_init` at `+0x20`, matching the generic initialization dispatch above. Their higher-half encodings were checked in the image. |
| `0x0022ec30`, native i8254x initialization routine | Disables interrupts, requests device reset, and on reset success configures link/PHY, receive ring and transmitter, then enables interrupts and sets control bits. This routine's analysis label was temporary; it is not a recovered source-level name. |
| `0x0022e7a4`, `i82544_device_reset` | Performs a bounded reset-bit polling sequence, returning failure if the bits do not clear. |
| `0x0022e95f`, `i82544_link_configure` | Updates NIC control and, for the selected device capability, acquires the PHY software flag, accesses PHY registers and releases the flag. |
| `0x0022ea40` / `0x0022eb78` | `i82544_receiver_configure` / `i82544_transmitter_configure`, with separate RX/TX ring-reset helpers. |
| `0x0022cd26` / `0x0022c9c5` | `KETH_InitializationComplete` and its helper prepare Ethernet buffer/descriptor queues and driver callbacks. This is general host Ethernet infrastructure, not proof of a particular live NIC binding. |

**What this establishes:** GHS contains concrete PCI Ethernet provisioning, generic Intel NIC
link/reset/ring logic and a named GM Ethernet passthrough driver. The existing boottable analysis
grants `GmEth` to Android **Guest1**, with VMM1 brokering the resource and interrupts. Presence of
the native i8254x driver does not prove that this driver, rather than the GM passthrough path, owns
the physical I210 on the observed boot. No live driver-binding or function-execution trace was
obtained here.

**What remains unlocated:** an explicit GHS Audio Video Bridging / AVTP transmitter initialization
path tied to the first observed VLAN-2 frames, and the onboard automotive switch's precise
power/reset/configuration sequence. The native chime/audio code and audio-DSP/SSP/TDM resources are
real, but do not alone establish a GHS-to-Bose Ethernet packet call chain. `GmEth` being available
to the Android guest means an early AAOS kernel network path also remains possible, before DHCP,
CarPlay or HMI readiness. The kernel-side `igb_avb` observation is maintained in
[`../platform/ethernet_networking.md`](../platform/ethernet_networking.md) (fixed from a stale
`../platform/hardware.md` link — that file was retired; see ledger).

Do not treat a generic GHS `AVB`/verification reference as audio-network evidence: **Android
Verified Boot** is a separate use of that acronym, traced through VMM1. The
[synchronized power-on measurement](../runtime/boot_timing.md#synchronized-rh850-uart-and-ethernet-power-on-measurement-2026-11-14)
establishes early traffic timing but not the initializing software owner.

For the other investigation target, the explicit BCM-replacement wipe decision was located in
Android `gm_protokey`, reached through security PAL IPC, rather than in a directly recovered GHS
handler. See the
[validated code path](../platform/security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14).
This was static analysis only: no device commands, firmware changes or runtime breakpoints were
used. Temporary Ghidra inspection changes were rolled back; no speculative function name was
saved.

**This section's relevance to §12:** it is the only targeted live-binding trace attempted against
the "GHS can independently capture/transmit" capability claim below, and it found no AVTP producer
and no live driver-binding evidence. See Open Conflicts §3.

### 7A.5 Guest platform (what Linux sees)

- Emulated **i440FX** host bridge (8086:1237), **legacy CF8/CFC** PCI config access.
- **No MCFG, no HPET, no DMAR, no SPCR** table templates exist. Tables supplied: RSDP/RSDT/FACP/FACS, generated MADT, IGS_DSDT, NHLT.
- **IOAPIC with GSI 16-119** (`_PRT`: GSI = 16 + (dev*4+pin) mod 104); 8259 PIC and PIT emulated.
- **NHLT** audio topology: 6 SSP endpoints (SSP0 8/16 kHz mono voice, SSP2 8-slot 48 kHz TDM, SSP3 8-ch capture).
- **Two IGS_DSDT SKUs**, identical except the `_PR` P-state package: A = 17 states, top **2400 MHz**; B = 11 states,
  top **1800 MHz**. Both benches report `androidboot.product.hardware.sku=gv221`.
- Guest cmdline adds `no_timer_check` (boot.img) and `clocksource=tsc tsc=reliable acpi_pm_good` (VMM appendix).

---

## 8. Hardware Interfaces

### Camera (Intel IPU4)

```
Functions:
├── IntelIpu4_Initialize
├── IntelIpu4_InitializeResources
├── IntelIpu4_ReadRegister
├── IntelIpu4_WriteRegister
├── StartCapture
├── Camera Capture Expected Heartbeat
└── IpuDebugStats

Firmware: bxtB0_IPU4 (linked in kernel)
```

### Network Stack

```
Ethernet (kethernet):
├── KETH_WritePacket
├── KETH_ReadPacket
├── EtherPacketReceived
├── EtherPacketSent
├── BSP_GetTCPIPReceiveCount
├── BSP_GetTCPIPTransmitCount
└── EthernetSendARP

WiFi Passthrough:
├── gm_wifi_passthru.c
├── gm_wifi_driver_init
└── gm_wifi_driver_match
```

### Audio

```
Components:
├── HDA Audio Controller
├── Dirana Audio DSP
├── Chimes System
└── gm_audio_passthru

Functions:
├── Hda_WriteBdlsForStream
├── AudioServer: Enabled
└── Dirana_InitialTask
```

---

## 9. Android Device Interfaces (/dev/ghs/*)

| Device | Purpose | SELinux Label |
|--------|---------|---------------|
| `/dev/ghs/textlog` | GHS kernel logs | ghs_device |
| `/dev/ghs/audit` | Security audit log | ghs_device |
| `/dev/ghs/snapshot-dbg` | Debug snapshots | ghs_device |
| `/dev/ghs/ipc` | IPC channel | ghs_device |
| `/dev/ghs/cal` | Calibrations | ghs_device |
| `/dev/ghs/camera` | Camera access | ghs_camera_device |
| `/dev/ghs/chime` | Chime control | ghs_device |
| `/dev/ghs/tee-att` | TEE attestation | ghs_device |
| `/dev/ghs/emmc-health` | eMMC health | ghs_device |
| `/dev/ghs/ota-isys` | OTA interface | ghs_device |
| `/dev/ghs/gpu-dbg` | GPU debug | ghs_device |

### GPU Debug Commands

```
/dev/ghs/gpu-dbg supports:
  'd' - Print/log current display controller state
  'p' - Print PPGTT usage
  't' - Print/log TFM governor information
```

The deeper USB/ADB exposure logic (XDCI/xHCI role switch, gadget/configfs, DABridge paths, the
6-condition ADB chain) that these device files sit behind is owned by
`USB_ADB_SESSION_FINDINGS_2026-10-10.md` — not restated here.

---

## 10. Source Files Identified

### Kernel Core

```
kernel.c, task.c, activity.c, semaphore.c, hlmutex.c
timer_pit.c, clock.c, highrestimer.c, interrupt.c
adrspace.c, memreg.c, heap.c, object.c, link.c
transfer.c, connect.c, ipc.c, suspensionio.c
schedloop.c, yield.c, setuptask.c, exittask.c
```

### VMM

```
86_x64_vmx.c, vmm.c, guest_pmu.c, vtd.c
device_memory.c, usb_onboard_vm.c
```

### Device Drivers

```
intel_ipu4.c, gen9_passthru.c, intel_heci.c
kethernet.c, indether_min.c, eth_i8254x.c
kuart.c, intel_lpss_uart.c, serial_pc16550.c
i2c_lpss.c, gpio.c, sdhc.c, xhc.c, xhc_ecm.c
```

### Passthrough Drivers

```
gm_eth_passthru.c, gm_wifi_passthru.c, gm_audio_passthru.c
sdhc_passthru.c, uart_passthru.c, i2c_passthru.c
spi_passthru.c, xdci_passthru.c, p2sb_passthru.c
passthru.c, passthru_fallback.c
```

### Security/TEE

```
keymaster_ipc.cpp, trusty_keymaster.cpp
trusty_keymaster_context.cpp, trusty_keymaster_enforcement.cpp
secure_storage.cpp, provision_keybox.cpp
attestation_record.cpp, auth_encrypted_key_blob.cpp
aes_key.cpp, rsa_key_factory.cpp, ec_key_factory.cpp
hmac_key.cpp, hmac_operation.cpp, ocb_utils.cpp
```

---

## 11. Potential Attack Surfaces

### 1. Android ↔ GHS Device Interfaces

```
Attack Vector: /dev/ghs/* devices
Risk Level: MEDIUM
Details:
  - Multiple device files exposed to Android
  - SELinux restricts access but some apps have permissions
  - Potential for IPC message injection
  - snapshot-dbg accepts commands
```

### 2. Boot/Update Validation

```
Attack Vector: A/B metadata, BCB manipulation
Risk Level: MEDIUM-HIGH
Details:
  - "VMM: Warning: A/B metatdata CRC failure!" (CRC-only; "metatdata" sic — verbatim binary string, confirmed in decompiled ghs_str.txt)
  - "VMM: Warning: A/B metadata: magic number mismatch"
  - misc partition manipulation
  - Recovery mode triggering
```

A/B + BCB mechanics in depth: GBUR, not restated here.

### 3. VMM Guest Memory Access

```
Attack Vector: Guest memory corruption
Risk Level: HIGH (if exploitable)
Details:
  - ReadGuestMemory/WriteGuestMemory functions
  - EPT mapping vulnerabilities
  - Guest ↔ Host memory boundary issues
```

### 4. USB/PCI Passthrough

```
Attack Vector: Malicious USB/PCI devices
Risk Level: MEDIUM
Details:
  - USB passthrough to guest
  - PCI device virtualization
  - DMA attacks (mitigated by VT-d)
```

### 5. IPC Channel Manipulation

```
Attack Vector: IPC message injection/fuzzing
Risk Level: MEDIUM
Details:
  - Trusty IPC (tipc)
  - GHS internal connections (ConnTo*)
  - Message parsing vulnerabilities
```

### 6. Keymaster/TEE

```
Attack Vector: Keymaster IPC
Risk Level: HIGH (valuable target)
Details:
  - Key provisioning (provision_keybox.cpp)
  - Base64 decode vulnerabilities
  - Authorization set deserialization
```

### 7. VIP IPC Channel

```
Attack Vector: VIP ↔ GHS communication
Risk Level: MEDIUM
Details:
  - ConnToVIP connection
  - EEPROM bypass coordination
  - ProtoKey transmission
```

EEPROM-bypass mechanism: ELA. ProtoKey transmission/IPC-chain finding (`gm_protokey`→`libpal_security.so`,
zero crypto validation of the 16-byte key): GSK. The live-tested ELK-trigger (RID 0xFF01/`FUN_000641c2`)
that this item is sometimes conflated with is owned by GBUR — see also `HARDWARE_HYPERVISOR_ATTACK_VECTORS.md`'s
catalog entry (dual-owned by design: GBUR holds the live-tested version, that doc keeps the catalog
entry).

### 8. INDRT Debug Interface

```
Attack Vector: Debug protocol
Risk Level: LOW (requires physical access)
Details:
  - INDRT_ServerIP, INDRT_ServerEth
  - Green Hills MULTI debugger protocol
  - Requires debug enabled
```

---

## 12. Privacy Capability Assessment (consolidated)

*Absorbs former §13 (Privacy Capability Summary), §14 (Recommendations) and §15 (Privacy
Capability Assessment) — those three duplicated each other (the former §15 banner said as much);
this section is the single current version. `GHS_PRIVACY_CAPABILITY_ANALYSIS.md`'s redirect stub
pointed here and is retired.*

**Read this section as capability inference layered on top of the static RE above, not as a
behavioural finding.** Every capability below is backed by a named function/driver that genuinely
exists in the binary; whether GHS *exercises* any of them independently of Android, on any given
vehicle, is not established by this document. §7A.4's 2026-11-14 Ethernet-ownership trace is the
one place this corpus attempted a targeted live-binding check against one of these claims (camera→network),
and it found no corroborating evidence — see Open Conflicts §3 below.

### 12.1 Capability summary

| Data/Interface | GHS Access | Method | Evidence tier |
|-----------|------------|--------|---|
| Camera feeds | Capability present | Direct IPU4 driver (§8) | `[FW]` driver exists; independent-capture use `[inferred]` |
| Screen content | Capability present | GPU/Display connections (§5, §7A.4) | `[FW]` connections exist; capture-without-Android use `[inferred]` |
| Audio/Mic | Capability present | Audio passthrough (§8) | `[FW]` driver exists; independent-capture use `[inferred]` |
| Android memory | Capability present | `ReadGuestMemory`/`WriteGuestMemory` (§7) | `[FW]` functions exist; any use against a running guest `[inferred]` |
| Network traffic | Capability present | kethernet stack (§8) | `[FW]` stack exists; independent transmission `[inferred]`, see §7A.4's "what remains unlocated" |
| Storage | Capability present | SDHC passthrough (§7A.4: GHS keeps eMMC/SDHC, mediates to guest) | `[FW]` |
| USB devices | Capability present | xHCI passthrough (§3, §7A.4) | `[FW]` |
| Ethernet | Capability present | `gm_eth_passthru` (§7A.4: granted to Guest1, VMM1 brokers) | `[FW]`; no live AVTP/independent-TX binding found (§7A.4) |
| WiFi | Capability present | `gm_wifi_passthru` (§7A.4: granted to Guest1) | `[FW]` |
| Intel HECI | ME interface present | `heci` driver (§3) | `[FW]` driver exists; "covert channel" use `[inferred]`, uncorroborated — see Open Conflicts §4 |

### 12.2 Evidence strings

Camera capture functions:
```
[Recovery] StartCapture failed with Error %d, IPU status %d
Camera Capture Expected Heartbeat
Capturemsg. Id:0x%x
IpuDebugStats: polls = %d, rawFrames = %d, dewarpedFrames = %d
snapshot-dbg
SnapshotDev
```
Camera display connections:
```
ConnToCamera_Display          - Camera to display connection
ConnToVMM_Display             - VMM display passthrough
ConnToCamera_Capture          - Camera capture connection
FirstFrameToGPU               - Frame routing to GPU
```
Network functions:
```
TCPIPEntry                    - TCP/IP entry point
InitLibSocket                 - Socket initialization
EthernetSendARP               - ARP packet sending
EthernetCheckARP              - ARP checking
ProtocolWritePacket           - Protocol-level write
```
WiFi passthrough: `gm_wifi_passthru.c`, `GmWifi`, `gm_wifi_driver_init`, `gm_wifi_driver_match`.
Ethernet passthrough: `gm_eth_passthru.c`, `i82544_transmitter_configure` (Intel NIC configuration).
VMM guest memory: `ReadGuestMemory`, `WriteGuestMemory`, `ReadGuestVirtualAddress`, `WriteGuestLMA`, `DirectCopyIntoVAS`, `VMM_GuestRamOffsetToHostPAddr`, `XhcVc_SetGuestMemoryMap`, `XhcVc_SetGuestMemoryOffset`, `HandleGuestVaddrCmd`, `VMM_SetVirtioBufferAddr`.
Audio: `gm_audio_passthru.c`, `AudioServer: Enabled`, `[AUDIO] Audio DSP Firmware`, `Hda_WriteBdlsForStream`.
Display: `ConnToVMM_Display`, `ConnToDisplayI2C`, `GPU_InitialTask`, `ConnToGPU`, `SCREEN_RESOLUTION`, `DisplayI2C`, `display-dbg`.
IPC messages:
```
- Blocking Guest Temperature Request Control IPC Message
- Blocking Guest AMP Control IPC Message
Cache IPC msg: Index=%u, toVip=%u, clientMask=0x%02x
IPC Channels Opened
Got IPC msg on invalid channel: %u
Sending cached IPC message on CH%02u
```
HECI / CSE: `Intel HECI`, `GHS: Error: Failed to send connect message to HECI client`, `GHS: Error: Failed to send disconnect message to HECI client`, `cseseed_iodevice.c`, `CseSeed_Init`, `CseSeed (Intel CSE)`.
Security: `Secure Boot: Enabled`, `AttestationSeedList`, `keymaster_ipc.cpp`, `trusty/app/keymaster`.

**Security-purpose implication:** the security features above are designed to protect GM's code
from inspection/modification, not to protect user privacy — they gate *what Android can do to GHS*,
not what GHS can do to Android.

**Memory-access implication:** the `ReadGuestMemory`/`WriteGuestMemory` functions mean GHS *can*
read or write any guest memory it chooses, including photos, messages, authentication tokens and
encryption keys, from a position Android cannot inspect or prevent. This is a capability statement
about the function's existence and privilege level (`[FW]`), not evidence it has been used this way
(`[inferred]` if asserted as active behaviour).

### 12.3 Cross-boundary data-flow (illustrative)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CROSS-BOUNDARY DATA FLOW PATH                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CAMERAS                                                             │
│     │                                                                │
│     └──► Intel IPU4 (GHS Direct Control)                            │
│              │                                                       │
│              ├──► Normal: Display to user via Android app            │
│              │                                                       │
│              └──► Hypothetical: GHS capture path, not traced live    │
│                      │                                               │
│                      ▼                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 GHS INTEGRITY HYPERVISOR                      │   │
│  │                                                               │   │
│  │   Camera Capture ──► Frame Buffer ──► TCP/IP Stack            │   │
│  │                                            │                   │   │
│  │   Audio Capture ───► Audio Buffer ─────────┤                   │   │
│  │                                            │                   │   │
│  │   Screen Capture ─► Display Buffer ────────┤                   │   │
│  │                                            │                   │   │
│  │   Guest Memory ───► RAM Contents ──────────┤                   │   │
│  │                                            ▼                   │   │
│  │                                   KETH_WritePacket             │   │
│  │                                            │                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                               │                      │
│                                               ▼                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    NETWORK INTERFACES                         │   │
│  │   • WiFi (gm_wifi_passthru) ────────────┐                     │   │
│  │   • Ethernet (gm_eth_passthru) ─────────┤                     │   │
│  │   • Intel HECI (Management Engine) ─────┤                     │   │
│  │                                         ▼                     │   │
│  │                              REMOTE SERVER                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ANDROID (GUEST VM) - NO VISIBILITY INTO GHS OPERATIONS              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

This diagram composes real function names along a hypothetical path (originally labeled "Covert");
the "GHS capture path" and "REMOTE SERVER" legs are not independently traced — see §7A.4 and Open
Conflicts §3-4.

### 12.4 Capability vs. corroboration

| Capability | Evidence | Corroboration status |
|------------|----------|--------------|
| **Camera Capture** | Intel IPU4 driver, `StartCapture`, Heartbeat | `[FW]` driver exists; no independent-of-Android capture trace attempted |
| **Independent Networking** | kethernet TCP/IP stack, `KETH_WritePacket` | `[FW]` stack exists; §7A.4 found no AVTP producer / live binding for independent TX — **uncorroborated**, Open Conflicts §3 |
| **Guest Memory Access** | `ReadGuestMemory`, `WriteGuestMemory` | `[FW]` functions exist and are architecturally unavoidable for a Type-1 hypervisor; use against live secrets untested |
| **Audio Access** | `gm_audio_passthru`, Audio DSP | `[FW]` driver exists |
| **Screen Access** | `ConnToVMM_Display`, GPU connections | `[FW]` connections exist |
| **Covert Communication (HECI/IPC)** | Intel HECI, IPC channels | **Uncorroborated inference** — no independent trace of HECI as a covert channel exists anywhere in this corpus, Open Conflicts §4 |
| **WiFi Control** | `gm_wifi_passthru`, direct driver | `[FW]` driver exists; granted to Guest1 per §7A.4, so "direct" GHS control competes with the guest's own ownership |
| **Snapshot Capability** | `snapshot-dbg`, `SnapshotDev` | `[FW]` device exists, accepts commands (§9, §11.1) |

The original severity labels (CRITICAL/HIGH/MEDIUM) are dropped here in favor of the corroboration
column above: they were assigned without an evidence-scoring rubric and several (independent
networking, HECI covert channel) are contradicted or unsupported by the only targeted trace this
corpus ran (§7A.4). Risk *ranking* for research/testing priority stays in §11, which is explicitly
a static-surface catalog, not a privacy-risk rating.

### 12.5 Conclusion, caveats, and recommendations

**Technically possible, given the binary's contents:**
1. Capture camera feeds via direct IPU4 access, independent of the Android app layer.
2. Transmit data via the independent TCP/IP stack (kethernet) — not corroborated by a live trace; see above.
3. Read (and, per the same functions, write) all Android guest memory, including messages, photos, and credentials.
4. Record audio via direct audio hardware access.
5. Capture screen contents via display/GPU connections.
6. Use Intel HECI or the dedicated network stack as a channel Android cannot inspect — the HECI half of this is inference, not a traced channel.

**What limits detectability, if any of the above were exercised:**
1. GHS operates below Android; Android cannot inspect GHS operations by construction (this is how a Type-1 hypervisor works, not a GM-specific choice).
2. GHS has its own network stack, so traffic on it would be invisible to Android-side tools.
3. The `ABL.secureboot=1` cmdline token suggests a secure-boot intent, but its live enforcement state is unverified (§6 History, 2026-11-12) — this neither proves nor disproves that GHS code is unmodifiable.
4. Intel ME (HECI) is physically present and is a generic additional channel in principle; no GHS-specific use of it as a channel is traced here.

**Caveats (unchanged from the original assessment, still load-bearing):**
1. Technical capability ≠ active surveillance — having the capability doesn't establish GM is using it.
2. No evidence of exfiltration was found; this analysis is capability inventory, not a monitored-traffic or log-based exfiltration study.
3. GM would carry legal exposure for unauthorized surveillance via these paths.
4. Many of these capabilities (backup camera, safety systems, OTA, calibration, infotainment audio) are the documented, legitimate reason the driver/connection exists in the first place — see §3-§10 for what each one is actually wired to in the normal architecture.

**For researchers:** the IPC channels (§11.5), A/B metadata (§11.2, CRC-only), Keymaster IPC
(§11.6), and `/dev/ghs/snapshot-dbg` (§11.1) remain the most accessible, least-traced attack
surfaces in this inventory; the VIP channel (§11.7) is already deferred to ELA/GSK.

**For privacy-concerned users:** treat the infotainment system as untrusted for sensitive
activity, treat GM's own privacy-policy disclosures as the actual scope statement for what is
collected (this document only establishes what the hardware/hypervisor *could* do), physical
inspection of the serial UART may reveal more, and a physical camera cover remains the only
control that doesn't depend on any of the above being true or false.

---

## Appendix A: Function Count

```
Total Functions (radare2): 8,209
Source Files Identified: 180+
PCI Device Drivers: 22
GHS Tasks: 14+
IPC Connections: 70+
```

Two counts in this appendix are not reconciled elsewhere in this doc: the Ghidra project (§ Image
identity, header) reports 9,424 functions against this 8,209; and "22" PCI drivers here against 21
named rows in §3. See Open Conflicts §1-2.

---

## Appendix B: Key Memory Regions

Full per-region map (Y175 `ghs_isys_a`, all 190 `.secinfo` regions with vaddr/len/type and Gate-1
self-integrity method) → [`decompiled/ghs_isys_a_secinfo_region_map_Y175.txt`](decompiled/ghs_isys_a_secinfo_region_map_Y175.txt);
interpretation in [BOOT_TRUST_ANCHOR_AND_KEYS.md §9](BOOT_TRUST_ANCHOR_AND_KEYS.md#9-ghs-self-integrity-gate-1-and-tamper-analysis).

```
.tee_keymaster.text/data/rodata
.tee_hw_crypto.text/data/rodata
.mr_r_mod_android_key
.mr_r_mod_ipu_fw
.ipumem
.boottimelog
.auditlog
.eventlog
.debugbuffer
.gipctarget
.indrt_entity
```

---

## Open conflicts

1. **Function count:** radare2 reports 8,209 total functions (Appendix A); the Ghidra project used
   for the §7A.4 address-level trace reports 9,424 (header, "Image identity"). Different tools,
   different analysis passes; no dated correction reconciles the two. Keep both.
2. **PCI driver count:** Appendix A's summary block states 22 PCI device drivers; §3's table lists
   21 named rows. Not reconciled — could reflect an unlisted 22nd driver or a stale Appendix A
   count carried from an earlier pass.
3. **Independent camera-capture / independent-network-transmission capability (§12.1/§12.3-12.4)
   vs. the 2026-11-14 Ethernet-ownership trace (§7A.4):** the capability claim ("GHS can capture
   frames/transmit independently of Android") is an undated inference from function-name presence;
   §7A.4's dated, targeted RE pass found concrete PCI Ethernet provisioning and a named `GmEth`
   passthrough driver, but explicitly "no live driver-binding or function-execution trace," no
   located AVTP transmitter, and states `GmEth` is granted to the Android guest (not exclusively
   held by GHS). This narrows but does not refute the capability claim — absence of a trace is not
   proof of absence of the behaviour, but the capability claim should not be read as corroborated
   either. Keep both framings distinct; do not let §7A.4 be cited as either confirming or refuting
   §12's inference.
4. **Intel HECI as a "covert channel" (§12.1/§12.4):** asserted in the original privacy assessment
   and carried forward here as an explicitly uncorroborated inference. No document in this corpus
   independently traces GHS using HECI as a data channel (distinct from HECI/CSE boot-time
   handshake functions, which are separately and concretely traced — see `cseseed_iodevice.c`,
   `CseSeed_Init` in §12.2, and `CSE_HECI_ORCHESTRATION_ANALYSIS.md` for the actual HECI/MKHI
   protocol RE, which does not address a covert-channel use). Flagged here so it isn't silently
   restated as a finding elsewhere.

---

## History

- **2026-11-?? (this consolidation):** merged former §13 (Privacy Capability Summary), §14
  (Recommendations) and §15 (Privacy Capability Assessment) into one §12 — the former §15 banner
  already said §13/§14 were legacy duplicates; this pass finishes that fold and adds a
  corroboration column instead of the unscored CRITICAL/HIGH/MEDIUM ratings. Retired
  `GHS_PRIVACY_CAPABILITY_ANALYSIS.md`'s redirect stub into this section (confirmed its target
  anchor existed before folding). Dropped the former §2 and §12 (old) stub sections (pure pointers
  to GBUR) in favor of one-line pointers in the Scope header and §1 — not restated as their own
  numbered sections, since no other doc was found to cite them by anchor. Folded in the
  `UPDATE_PROCESS_ANALYSIS.txt` §3.1-3.2 guest-side hypervisor evidence and GHS-partitions table
  (retired doc; "GHS evidence/partitions" was this doc's assignment per the consolidation plan) and
  the `SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md` display-path/`EARLY_CALS` footnote (also retired).
  Folded the 2026-11-17 GPIO-ownership correction and the 2026-11-12 `ABL.secureboot` caveat into
  their claims in place rather than leaving them as trailing bracketed notes. Section numbers 3-11
  and all of §7A's subsection anchors are preserved byte-identical to the pre-consolidation
  headings, since other docs (`GM_INFO37_BOOT_CHAIN_ANALYSIS.md` at minimum) cite `§7A.3` and
  similar anchors directly.
- **2026-01-05 → 2026-11-17 (original doc):** see inline History notes under §6 and §7A for the
  dated corrections carried over from the source document (ABL.secureboot caveat, GPIO ownership,
  measured E820 map, Ethernet ownership trace).

**Analysis method:** static binary analysis (radare2, Ghidra, strings) across dated passes
2026-01-05 through 2026-11-17, plus the independent 3-Opus firmware re-derivation (2026-10-10)
noted on §7A's tagged items.
