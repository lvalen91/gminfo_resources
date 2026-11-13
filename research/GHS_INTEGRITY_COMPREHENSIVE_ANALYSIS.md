# GHS INTEGRITY Hypervisor - Comprehensive Analysis

**Date:** 2026-01-05
**Binary:** SOC_HOSTOS (85098662)
**Size:** 14,929,320 bytes (extracted ELF)
**Format:** ELF (header claims 32-bit LSB / Intel 80386) but **the code is x86-64** (CORRECTED 2026-08-26: `movabs`/REX-prefixed instructions, `crt_x64.86`/`libkernel.86_x64`; the EM_386 header is misleading — disassemble as `x86:LE:64`), statically linked; kernel symbols retained, application/task symbol coverage incomplete

> Companion doc: `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` covers boot/update/recovery
> mechanics in depth (BCB/misc byte layout, USB/protokey/capsule trigger files,
> See-Dealer/ELK/Diagnostic boot modes, Lifecycle SoH handshake) — complementary to this
> RE inventory. The former `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` is consolidated here in §15.
>
> Companion doc: `GHS_FILE_MAP_85098662.md` is the edge-to-edge byte map of the same image
> (sections, `.boottable`, `.secinfo`). The VM/partition configuration derived from `.boottable`
> is in §7A below; findings tagged `[FW 85098662; 3-Opus verified 2026-10-10]` were re-derived
> independently by three Opus agents from the firmware bytes. Anything marked `[UNVERIFIED]` was not.

---

## 1. System Overview

### Version Information

| Property | Value |
|----------|-------|
| **OS** | INTEGRITY IoT 2020.18.19 |
| **Core Version** | 23739 |
| **Modules Version** | 11500 |
| **GM Version** | MY22-026 |
| **Build Path** | /home/mal/gm_release/MY22-026/final/iot/rtos/ |
| **Vendor** | Green Hills Software |
| **Target Platform** | Intel Apollo Lake (gm-i35) |

### Architecture Summary

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

---

## 2. Boot Process

Boot sequence and boot-command construction are maintained in
[the consolidated boot/recovery source](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#1-ghs-boot-process).

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

---

## 4. GHS Tasks (Processes)

### Core Tasks

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

---

## 5. Inter-Process Connections

### Connection Map

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
│  ├── ConnToCamera_Camera                                          │
│  ├── ConnToCamera_Capture                                         │
│  ├── ConnToCamera_Display                                         │
│  ├── ConnToCamera_I2C                                             │
│  └── ConnToCamera_RvcStatus                                       │
│                                                                   │
│  Audio Subsystem                                                   │
│  ├── ConnToChimes                                                  │
│  ├── ConnToChimes_Chime                                           │
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

---

## 6. Security Mechanisms

### Verification scope and unresolved security candidates (2026-11-12)

Binary fingerprints, extraction boundaries, debugger evidence and historical CVE
applicability are maintained in the [consolidated research](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#01-y181b-binary-provenance-and-security-evidence-2026-11-12).

### Android Verified Boot (AVB)

Compiled VMM verification paths include the following checks; this inventory
does not alone establish their live enforcement state:

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

### Trusty TEE

GHS hosts a Trusty TEE implementation:

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

### Secure Boot

```
Boot Security:
├── ABL.secureboot=1   [NOTE 2026-11-12 CAVEAT: 'ABL.secureboot=1' appears only as a token in retained kernel-log cmdlines (live `getprop ro.boot.ABL.secureboot` is empty; hit count ~188 per archive, earlier '386' not reproduced); it is a cmdline indicator, not a verified secure-boot state. See platform/boot_chain.md.]
├── CRC error in FLASH, failing
├── SHA-1 hash error in FLASH, failing
├── CRC error in RAM, failing
└── SHA-1 hash error in RAM, failing
```

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
(va 0x23110b) indexes the root table by bus and the context table by dev*8+fn, allocating a 4 KiB context
table on demand from `vtdFreePages`. There is **no `.vtdpagetable` section** in the image; that string is
an error message only. The guest itself runs `intel_iommu=off` and sees no DMAR. See §7A.4.

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
memory-map tables). Full derivation: `/tmp/ghs_hv/GHS_HYPERVISOR_CONFIG_RE.md` (working notes);
section layout in `GHS_FILE_MAP_85098662.md`.

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

The scheduler claim rests on `__PartitionSchedulerInitPtr` (va 0x84a2a8) = 0 and every
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
| Guest-visible `MemTotal` | **5530 MiB** (5663432 kB, identical on Y175 and Y181) |

The 7830 MiB figure is byte-confirmed from the MR table and is **not an MMIO over-count**: the GPA hole
0x8000_0000-0xFFFF_FFFF (PCI window) is not part of any granted region. The ELF program headers under-report
(RAM0/RAM1 only; RAM2-4 are plain physical ranges), so the boottable MR table is authoritative.

**Corrected 2026-11-12 — measured Y181B recovery map:** the
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
IPU camera (Camera server), I2C3 (Dirana), I2C6 (Camera), I2C7 (DisplayI2C), all GPIO (VMM1 owns GPIO_0..30,
106, 203), RTC, P2SB, SerialDev0. DMA-visible memory for the passthrough set is confined to the guest GPA map.

**VT-d / IOMMU:** root/context tables are built at runtime (no `.vtdpagetable` section, see §7). Six unnamed
ASes are pure DMA domains: HDA, IPU, Lines, EMMC/SDHC, GPU_Dom_Gen9, GVTG_Dom. The guest runs
**`intel_iommu=off`**, so all isolation is host-side.

**GVT-g:** the GPU server (`gvtg_server`, AS15) mediates the Gen9 GPU (GuC/HuC firmware in the server) and maps the
whole of guest RAM; the guest sees a GVT-g vGPU (`ro.hardware.gralloc/hwcomposer=broxton`).

**TEE:** keymaster, gatekeeper, HW crypto and storage are GHS-side servers (TEE_Router fans tipc connections out to
them); the guest is told `androidboot.trustyimpl=-ghs`. (`TEEAtt` is a VMM1 connection to TEE_Router, not a separate
server; the "TEE_Attestation" box in §6 is a connection, not an address space.)

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

## 12. Update/Recovery Handling

Recovery, userspace fastbootd, ELK orchestration, USB markers and recovery
arguments are maintained in
[the consolidated source](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#23-special-boot-modes).

## 13. Privacy Capability Summary

### Data Access Capabilities

| Data Type | GHS Access | Method |
|-----------|------------|--------|
| Camera feeds | YES | Direct IPU4 driver |
| Screen content | YES | GPU/Display connections |
| Audio/Mic | YES | Audio passthrough |
| Android memory | YES | ReadGuestMemory |
| Network traffic | YES | kethernet stack |
| Storage | YES | SDHC passthrough |
| USB devices | YES | xHCI passthrough |

### Network Transmission

| Interface | GHS Direct Access |
|-----------|-------------------|
| Ethernet | YES (gm_eth_passthru) |
| WiFi | YES (gm_wifi_passthru) |
| Intel HECI | YES (ME interface) |

---

## 14. Recommendations

### For Security Researchers

1. **Focus on IPC channels** - Most accessible attack surface
2. **A/B metadata manipulation** - CRC-only validation may be weak
3. **Keymaster IPC fuzzing** - High-value target
4. **VIP communication channel** - EEPROM bypass coordination
5. **/dev/ghs/snapshot-dbg** - Accepts commands, needs investigation

### For Privacy Concerned Users

1. Assume GHS has access to all sensors and data
2. GHS operates below Android visibility
3. Network traffic can be sent without Android awareness
4. Physical inspection of serial UART may reveal more
5. Camera covers recommended for non-safety cameras

---

## 15. Privacy Capability Assessment (consolidated)

> Canonical privacy assessment; `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` is a pointer. §13 above carried the
> capability tables; this section adds the privacy-specific evidence strings, the
> cross-boundary data-flow diagram, the privacy-risk severity ratings, and the
> interpretive caveats that §13 did not contain.

### 15.1 Evidence strings

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

**Security-purpose implication:** The security features are designed to protect GM's code from inspection/modification, not to protect user privacy.

**Memory-access implication:** GHS can read ANY data from Android's memory - including photos, messages, authentication tokens, and encryption keys. It can also modify Android's memory without Android's knowledge.

### 15.2 Cross-boundary data-flow

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
│              └──► Covert: GHS can capture frames independently       │
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
│  ANDROID (GUEST VM) - NO VISIBILITY INTO GHS OPERATIONS             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 15.3 Privacy risk severity ratings

| Capability | Evidence | Privacy Risk |
|------------|----------|--------------|
| **Camera Capture** | Intel IPU4 driver, StartCapture, Heartbeat | CRITICAL |
| **Independent Networking** | kethernet TCP/IP stack, KETH_WritePacket | CRITICAL |
| **Guest Memory Access** | ReadGuestMemory, WriteGuestMemory | CRITICAL |
| **Audio Access** | gm_audio_passthru, Audio DSP | HIGH |
| **Screen Access** | ConnToVMM_Display, GPU connections | HIGH |
| **Covert Communication** | Intel HECI, IPC channels | HIGH |
| **WiFi Control** | gm_wifi_passthru, direct driver | HIGH |
| **Snapshot Capability** | snapshot-dbg, SnapshotDev | MEDIUM |

### 15.4 Conclusion

What GM Can Do (Technically):
1. **Capture camera feeds** without Android's knowledge using direct IPU4 access
2. **Transmit data remotely** via the independent TCP/IP stack (kethernet)
3. **Read all Android memory** including messages, photos, and credentials
4. **Record audio** via direct audio hardware access
5. **Capture screen contents** via display/GPU connections
6. **Communicate covertly** with remote servers via Intel HECI or dedicated network stack

What Prevents Detection:
1. GHS operates BELOW Android - Android cannot inspect GHS operations
2. GHS has its own network stack - traffic is invisible to Android
3. Secure boot prevents modification or inspection of GHS code
4. Intel Management Engine provides another covert channel

**Important Caveats:**
1. **Technical capability ≠ Active surveillance** - Having the capability doesn't prove GM is using it
2. **No evidence of exfiltration** - The analysis shows capability, not active data collection
3. **Legal constraints** - GM would face significant legal liability for unauthorized surveillance
4. **Legitimate uses** - Many capabilities are needed for features like backup camera, safety systems

Recommendations for Users Concerned About Privacy:
1. Assume the vehicle can access all sensors and data
2. The infotainment system should be treated as untrusted for sensitive activities
3. GM's privacy policy should be reviewed for data collection disclosures
4. Consider physical camera covers for non-safety-critical cameras

---

## Appendix A: Function Count

```
Total Functions (radare2): 8,209
Source Files Identified: 180+
PCI Device Drivers: 22
GHS Tasks: 14+
IPC Connections: 70+
```

---

## Appendix B: Key Memory Regions

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

**Document Version:** 1.0
**Analysis Method:** Static binary analysis (radare2, Ghidra, strings)
**Classification:** Security Research
