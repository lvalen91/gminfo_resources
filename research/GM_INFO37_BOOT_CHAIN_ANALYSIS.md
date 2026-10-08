# GM Info 3.7 (A11 Module) Complete Boot Chain Analysis

**Date:** 2026-01-05
**Module:** A11 CSM (Central Stack Module)
**Vehicle:** 2024/2025 Chevrolet Silverado 2500 HD (T1XX Platform)
**Firmware Version:** Y181 (Primary Analysis), Y177 (Comparison)

> Companion document: the binary-forensic evidence base (module file numbers, header
> magics `1NMH`/`1SHG`, payload hashes, ABL build metadata, CSE key list, SVN
> anti-rollback strings, `/dev/flash/*` paths, `CONFIG_GHS_*` flags, full embedded kernel
> cmdline, recovery SEPolicy types) lives in `research/BOOT_CHAIN_ANALYSIS.txt`. This
> document holds the architectural analysis built on that evidence; the two are
> complementary (neither supersedes the other).

---

## Table of Contents

1. [Hardware Architecture Overview](#1-hardware-architecture-overview)
2. [Boot Sequence Timeline](#2-boot-sequence-timeline)
3. [Phase 0: Power On](#3-phase-0-power-on)
4. [Phase 1: VIP (Renesas RH850) Boot](#4-phase-1-vip-renesas-rh850-boot)
5. [Phase 2: Intel SoC Boot](#5-phase-2-intel-soc-boot)
6. [Phase 3: GHS INTEGRITY Hypervisor Boot](#6-phase-3-ghs-integrity-hypervisor-boot)
7. [Phase 4: Android Verified Boot (AVB)](#7-phase-4-android-verified-boot-avb)
8. [Phase 5: Android AAOS Boot](#8-phase-5-android-aaos-boot)
9. [Complete Boot Chain Diagram](#9-complete-boot-chain-diagram)
10. [Security Boundaries](#10-security-boundaries)
11. [Key Findings](#11-key-findings)
12. [Files Analyzed](#12-files-analyzed)
13. [Appendix: Error Messages](#appendix-a-error-messages)
14. [Appendix F: Kernel Configuration + GHS Coupling (2026-09)](#appendix-f-kernel-configuration--ghs-coupling-2026-09)
15. [Appendix G: QEMU Portability Assessment (2026-09)](#appendix-g-qemu-portability-assessment-2026-09)

---

## 1. Hardware Architecture Overview

The GM Info 3.7 A11 module uses a **dual-processor architecture** with the Renesas VIP (Vehicle Interface Processor) managing power and vehicle interfaces while the Intel Atom SoC runs the GHS hypervisor and Android guest VM.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     A11 CSM (Central Stack Module)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────┐         ┌─────────────────────────────────┐   │
│   │  RENESAS VIP (TM52176)  │◄══════►│  INTEL ATOM x7-A3960 (J6/SoC)   │   │
│   │  RH850/P1M-E MCU        │  HDLC   │  Apollo Lake (Broxton)          │   │
│   │                         │   IPC   │                                  │   │
│   │  • VIP_BOOT (~128KB)    │         │  • SOC_ABL (Bootloader)         │   │
│   │  • VIP_APP (~1.9MB)     │         │  • GHS INTEGRITY Hypervisor     │   │
│   │  • EEPROM Access (I2C)  │         │  • Android AAOS (Guest VM)      │   │
│   │  • CAN/LIN Interface    │         │  • 8GB LPDDR4 / 64GB eMMC        │   │
│   └────────────┬────────────┘         └──────────────┬──────────────────┘   │
│                │                                      │                      │
│                │                                      │                      │
│   ┌────────────▼────────────┐         ┌──────────────▼──────────────────┐   │
│   │  M24C64 EEPROM (8KB)    │         │  Samsung eMMC (64GB)            │   │
│   │  • Security Flags       │         │  • A/B Partitions               │   │
│   │  • VIN, Calibrations    │         │  • boot_a/b, system, vendor     │   │
│   │  • ProtoKey Config      │         │  • vbmeta, misc partitions      │   │
│   └─────────────────────────┘         └─────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Chip | Function |
|-----------|------|----------|
| **Main SoC** | Intel Atom x7-A3960 | 4-core CPU, GPU, runs GHS + Android |
| **VIP MCU** | Renesas TM52176 (RH850) | Power control, CAN/LIN, security |
| **RAM** | LPDDR4 | 8192 MB physical (6144 MB to guest) |
| **Storage** | Samsung KLMCG4JEUD | 64GB eMMC |
| **EEPROM** | ST M24C64 | 8KB configuration storage |
| **CAN Transceiver** | NXP TJA1145T/FDJ | CAN with partial networking |
| **Ethernet PHY** | TI DP83TC811 (likely) | 100BASE-T1 automotive Ethernet |

---

## 2. Boot Sequence Timeline

| Phase | Component | Time | Description |
|-------|-----------|------|-------------|
| 0 | Power On | T=0ms | Vehicle battery applied |
| 1 | VIP Boot | T=0-50ms | Renesas MCU initialization |
| 2 | Intel SoC Boot | T=50-200ms | CSE + ABL execution |
| 3 | GHS Hypervisor | T=200-500ms | INTEGRITY kernel + tasks |
| 4 | Android AVB | T=500-1500ms | Verified boot validation |
| 5 | Android AAOS | T=1500-15000ms | Full Android boot |

---

## 3. Phase 0: Power On

```
Vehicle Battery → A11 Power Supply
         │
         ├── VIP MCU receives power first (always-on domain)
         ├── VIP monitors GMLAN for wake signals
         └── VIP controls SoC power rails via GPIO
```

### VIP Power Level Control (PLC) Timers

| Timer | Default Value | Purpose |
|-------|---------------|---------|
| `cal_soc_soh_timeout_msec` | 1500ms | State-of-Health check |
| `cal_hypervisor_startup_timeout_ms` | 300ms | GHS boot timeout |
| `cal_shutdown_timeout_msec` | 3500ms | Graceful shutdown |
| `cal_startup_fault_timeout_sec` | 6000ms | Full boot timeout |

### Wake Sources

- GMLAN CAN message (network wake)
- Door ajar signal
- Remote start command
- Scheduled wake (OnStar)

---

## 4. Phase 1: VIP (Renesas RH850) Boot

**Duration:** T=0-50ms
**Processor:** Renesas TM52176 (RH850/P1M-E core)

### 4.1 VIP_BOOT Execution

The VIP bootloader resides in internal RH850 flash (~128KB):

```
VIP_BOOT Sequence:
├── Hardware initialization (RH850 core)
├── Clock configuration
├── Internal signature validation (Harman checksum)
└── Jump to VIP_APP
```

### 4.2 VIP_APP Initialization

| Property | Value |
|----------|-------|
| **Version (Y177)** | 2B.174.4.1 |
| **Build Date** | 24Mar22-0256 |
| **Bolo Version** | B2.9C.01.01 |
| **ARXML Version** | 22.22.158 |
| **IPC Version** | 4.1.0 |
| **HwVariant** | 56 |

### 4.3 VIP Module Initialization Sequence

```
VIP_APP Module Init:
├── SS_SWC     - System State Controller (sleep/wake/shutdown)
├── PLC        - Power Level Control (SoC power sequencing)
├── J6_CDD     - Intel Atom (J6) Communication Driver
├── IPC_S      - Inter-Processor Communication Server
├── AMP_MGR_SWC - Audio Amplifier Manager
├── PROTOKEY   - Security key management
├── SBAT       - Secure Boot anti-rollback (keyNBID/appNBID generation numbers)
├── IOHWAB_MIC - Microphone Hardware Abstraction
└── NAV        - Navigation/GNSS interface
```

> SBAT full expansion is **unconfirmed** from firmware strings. The keyNBID/appNBID
> generation-number scheme matches the UEFI/shim "Secure Boot Advanced Targeting"
> revocation model (per-component generation numbers that revoke outdated/vulnerable
> components), which is the leading interpretation. Earlier docs guessed "Authorization
> Ticket" / "Authentication Table"; treat any full expansion as unverified.

### 4.4 EEPROM Read (M24C64)

VIP reads critical configuration from external EEPROM via I2C:

| Address | Size | Content | Purpose |
|---------|------|---------|---------|
| 0x0440 | 2 | Primary SBI Flag | Security bypass indicator |
| 0x0A80 | 2 | Backup SBI Flag | Redundant security flag |
| 0x0B40 | 1 | Debug Mode Flag | Developer mode |
| 0x05C0 | 17 | VIN | Vehicle identification |
| 0x0600+ | Varies | Calibrations | ~30 cal_* parameters |

### 4.5 Security Validation Function (@ 0xb67d0)

**CORRECTED 2026-08-25 — the earlier "Y177 stub" claim in this section was FALSE.** A three-way
VIP_APP diff (Y175/Y177/Y181) proves this validator is a **full ~906-byte function in all three
builds**. See `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2.

| Version | Function entry | Function Size | Behavior |
|---------|----------------|---------------|----------|
| **Y175** | `0xb6708` | ~906 bytes | Full validation |
| **Y177** | `0xb67d4` | ~906 bytes | Full validation |
| **Y181** | `0xb67d0` | ~906 bytes | Full validation |

~~Y177 = 4-byte stub `mov 0,r10; jmp [lp]`~~ — **retracted.** That "stub" was a
fixed-absolute-address misread: reading Y177 at the fixed `0xb67d0` lands 4 bytes early on the
*tail of the previous function* (`00 52 7f 00 …`); the real function begins at `0xb67d4` (+4).
Aligned body diffs are only 15/906 bytes (Y177↔Y181) and 18/906 (Y175↔Y181) — same source
recompiled. Identical entry bytes across all three: `88 07 e3 ff 06 c8 99 00 03 3d 05 45 07 4d 83 a7`.

```
Validation function (Y181 @0x000b67d0; Y177 @0xb67d4; Y175 @0xb6708) — FULL in every build:
    ├── Load security/seed flag from memory 0x3e06 (0xFEBD3E06)
    ├── Compare against expected value
    ├── Multiple conditional branches
    ├── Calls to validation functions:
    │   ├── 0xecd84
    │   ├── 0xb6652
    │   └── 0xaee28
    └── Returns error codes on failure
```

This function gates **ADB/seed auth** (EEPROM SBI at 0x0440), not SELinux mode — no
`selinux`/`enforce`/`permissive` strings exist anywhere in the VIP image. No stock build runs
permissive: Y175/Y177/Y181 share a byte-identical init that forces enforcing (see `security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8).

### 4.6 ProtoKey Processing

```
ProtoKey Flow:
├── If SBI = 0x00 (normal mode):
│   ├── Request seed from BCM via GMLAN
│   ├── Validate seed/key exchange
│   └── Transmit result to SoC
├── If SBI = 0xFF (bypass mode):
│   ├── Return 0xFF seed (bypass)
│   └── Skip BCM communication
└── Channel: SERIAL_IPC_PROTO_KEY_CHANNEL
```

### 4.7 SoC Power Enable

```
Power Sequence:
├── Assert power enable GPIO to Intel SoC
├── Start Hypervisor Startup Timer (300ms default)
├── Wait for SOC_READY signal
└── Begin IPC communication with GHS
```

### 4.8 Key Calibration Values

| Variable | Default | Purpose |
|----------|---------|---------|
| `cal_background_sleep_timeout_sec` | 10 | Background sleep delay |
| `cal_sleep_fault_timeout_sec` | 900 | Sleep fault timeout (15 min) |
| `cal_startup_fault_timeout_sec` | 15 | Boot timeout |
| `cal_suspend_to_ram_en` | 1 | S2R enabled |
| `cal_str_min_temp_threshold` | -10 | Min temp for S2R |
| `cal_hypervisor_startup_timeout_ms` | 300 | GHS boot timeout |
| `cal_vin_relearn_en` | 0 | VIN relearn mode |
| `cal_local_infotainment_cancel_mode` | 0 | Cancel infotainment |

---

## 5. Phase 2: Intel SoC Boot

**Duration:** T=50-200ms
**Processor:** Intel Atom x7-A3960 (Apollo Lake / Broxton)

### 5.1 Intel CSE (Converged Security Engine)

The Intel Management Engine initializes first:

```
CSE Initialization:
├── ME (Management Engine) firmware load from SPI flash
├── Hardware key derivation from OTP fuses
├── CSE boot policy enforcement
├── Measured boot (if enabled)
└── Prepare for ABL handoff
```

### 5.2 SOC_ABL (Automotive Bootloader)

| Property | Value |
|----------|-------|
| **File** | 85738845 |
| **Size** | ~6MB (signed) |
| **Secure Boot** | ABL.secureboot=1 |

```
ABL Execution:
├── Secure Boot validation against hardware root of trust
├── Load GHS INTEGRITY from eMMC partition
├── Verify GHS signature (cannot be bypassed)
├── Configure kernel command line
└── Transfer control to GHS kernel
```

### 5.3 ABL Boot Parameters

```
clocksource=tsc tsc=reliable
acpi_pm_good
i915.avail_planes_per_pipe=0x000003
i915.enable_pvmmio=0
androidboot.diskbus=1c.0
androidboot.boot_devices=pci0000:00/0000:00:1c.0
androidboot.trustyimpl=-ghs
androidboot.product.hardware.sku=gv221
androidboot.slot_suffix=%s
androidboot.verifiedbootstate=%s
androidboot.vbmeta.avb_version=1.1
```

---

## 6. Phase 3: GHS INTEGRITY Hypervisor Boot

**Duration:** T=200-500ms
**OS:** Green Hills INTEGRITY IoT 2020.18.19

### 6.1 GHS Version Information

| Property | Value |
|----------|-------|
| **OS** | INTEGRITY IoT 2020.18.19 |
| **Core Version** | 23739 |
| **Modules Version** | 11500 |
| **GM Version** | MY22-026 |
| **Build Path** | /home/mal/gm_release/MY22-026/final/iot/rtos/ |
| **Vendor** | Green Hills Software |
| **Target** | Intel Apollo Lake (gm-i35) |
| **File** | SOC_HOSTOS (85098662) - 14.9MB |

### 6.2 GHS Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GHS INTEGRITY LAYERS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ VMM (Virtual Machine Monitor)                                        │    │
│  │  • VMX (Intel VT-x)                                                  │    │
│  │  • VT-d (IOMMU)                                                      │    │
│  │  • EPT (Extended Page Tables)                                        │    │
│  │  • Guest Memory Management                                            │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ Kernel Services                                                      │    │
│  │  • Task/Thread Management                                            │    │
│  │  • Memory Management                                                  │    │
│  │  • Interrupt Handling                                                 │    │
│  │  • IPC (Inter-Process Communication)                                  │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ Device Drivers                                                       │    │
│  │  • PCI Device Drivers                                                 │    │
│  │  • Passthrough Drivers                                                │    │
│  │  • I/O Device Management                                              │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ Security Services                                                    │    │
│  │  • Trusty TEE (Keymaster, Gatekeeper)                                 │    │
│  │  • Secure Boot Validation                                             │    │
│  │  • Android Verified Boot (AVB)                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Stage A: CPU Initialization

```
1. BSP_InitializeOnBootCpu
   ├── x86-64 CPU feature detection
   ├── Memory controller initialization
   └── Early hardware setup

2. ASP_PreCrtInitializeBootstrap
   ├── C runtime initialization
   ├── Stack setup
   └── Global constructors

3. ASP_VMX_InitializeOnBootCpu (Intel VT-x)
   ├── Enable VMX (Virtual Machine Extensions)
   ├── Initialize VMCS (VM Control Structure)
   ├── ASP_VMX_SetupMsrBitmap
   └── Setup EPT (Extended Page Tables)

4. ASP_VTD_Init (Intel VT-d / IOMMU)
   ├── Vtd_Initialize
   ├── Enable DMA remapping
   ├── Vtd_EnableVtdForDevice (per device)
   └── Vtd_ActivateDmaRemappingUnit

5. BSP_BootSecondaryCpus
   ├── Wake CPU cores 1-3 via INIT-SIPI sequence
   ├── AP (Application Processor) boot sequence
   └── Multi-core synchronization barrier
```

### 6.4 Stage B: GHS Kernel Tables

```
6. SetupBootTables
   ├── InitializeTheAddressSpaceTable
   ├── InitializeTheTaskTable
   └── InitializeTheODGTable (Object Directory Group)
```

### 6.5 Stage C: GHS Tasks Launch

```
7. RunInitialTasks - Start all GHS tasks (parallel)

   Core Tasks:
   ├── VMM1_InitialTask       ← PRIMARY: Android VM Manager
   ├── Lifecycle_InitialTask  ← Power/boot state management
   ├── VIP_InitialTask        ← VIP MCU communication (UART IPC)
   └── OTA_InitialTask        ← OTA update handling

   Hardware Tasks:
   ├── Camera_InitialTask     ← Intel IPU4 camera processing
   ├── Audio_InitialTask      ← HDA audio subsystem
   ├── GPU_InitialTask        ← Intel HD Graphics 505 passthrough
   ├── Chimes_InitialTask     ← Alert sound generation
   ├── Dirana_InitialTask     ← Audio DSP control
   └── DisplayI2C_InitialTask ← Display backlight/control

   Security Tasks:
   ├── TEE_Keymaster          ← Trusty keymaster service
   ├── TEE_HW_Crypto          ← Hardware crypto acceleration
   └── TEE_Storage            ← Secure storage (RPMB)

   Other Tasks:
   ├── Calibrations_InitialTask
   └── Lines_InitialTask (graphics overlay)
```

### 6.6 GHS IPC Connections Established

```
┌──────────────────────────────────────────────────────────────────┐
│                    GHS IPC CONNECTIONS                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  VMM (Android Interface):                                         │
│  ├── ConnToAndroidVMM                                             │
│  ├── ConnToVMM_Camera                                             │
│  ├── ConnToVMM_Display                                            │
│  ├── ConnToVMM_Chime                                              │
│  ├── ConnToVMM_Cal                                                │
│  ├── ConnToVMM_OTA / ConnToVMM_OTA_Control                        │
│  ├── ConnToVMM_EMMCHealth                                         │
│  └── ConnToVMM_TextLog / ConnToVMM_Audit                          │
│                                                                   │
│  VIP MCU:                                                          │
│  ├── ConnToVIP                                                     │
│  └── ConnToVip_Lifecycle_API                                      │
│                                                                   │
│  Camera Subsystem:                                                 │
│  ├── ConnToCamera / ConnToCamera_Camera                           │
│  ├── ConnToCamera_Capture / ConnToCamera_Display                  │
│  └── ConnToCamera_I2C / ConnToCamera_RvcStatus                    │
│                                                                   │
│  TEE (Trusty):                                                     │
│  ├── ConnToTEE_Keymaster                                          │
│  ├── ConnToTEE_Storage                                            │
│  └── ConnToTEE_Router / ConnToTEE_TEEAtt                          │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 6.7 GHS Device Interfaces Created

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

---

## 7. Phase 4: Android Verified Boot (AVB)

**Duration:** T=500-1500ms
**Task:** VMM1_InitialTask

### 7.1 Check Recovery Mode

```
CheckRecoveryMode():
├── Read BCB (Bootloader Control Block) from misc partition
├── Parse command field:
│   ├── "boot-recovery" → Recovery mode
│   ├── "boot-see-dealer" → Dealer mode
│   └── Empty → Normal boot
└── Determine boot target
```

### 7.2 A/B Slot Selection

The A/B metadata is stored in the `misc` partition at offset 0x800:

```c
struct ABMetadata {
    uint32_t magic;           // Expected: specific magic number
    uint8_t  version;
    uint8_t  reserved[3];
    struct {
        uint8_t priority;
        uint8_t tries_remaining;
        uint8_t successful_boot;
        uint8_t reserved;
    } slot_info[2];           // Slot A and B
    uint32_t crc32;           // CRC32 checksum (WEAK!)
};
```

```
A/B Selection:
├── Read A/B metadata from misc @ 0x800
├── Validate magic number
│   └── Error: "VMM: Warning: A/B metadata: magic number mismatch"
├── Validate CRC32 (NOTE: CRC only, no cryptographic signature!)
│   └── Error: "VMM: Warning: A/B metatdata CRC failure!"
├── Check slot priority and tries_remaining
├── Select active slot (_a or _b)
└── Log: "A/B Boot Slot: boot%s"
```

**Security Note:** A/B metadata uses only CRC32 for integrity, not cryptographic signature.

### 7.3 Load and Verify vbmeta

```
vbmeta Verification:
├── Read vbmeta_a or vbmeta_b from eMMC
│   └── Error: "VMM: ERROR: no vbmeta partition found (slot %s)"
├── Parse vbmeta header:
│   ├── Magic: "AVB0"
│   ├── Version: 1.1
│   ├── Authentication block offset/size
│   └── Auxiliary block offset/size
├── Extract hash/hashtree descriptors
└── Prepare for signature verification
```

**(2026-09-10, byte-confirmed):** `"AVB0"` is the **stock upstream `libavb` `AVB_MAGIC`**, not a
GM-custom value — `vbmeta.img` offset 0 = `41 56 42 30`. The header is 100% upstream (RSA2048/SHA256,
`avbtool 1.2.0`, flags=0x00000000 i.e. verification NOT disabled), with zero GM-specific fields. Do
not confuse this with the separate `\0AB0` magic used by the misc/BCB A/B-slot-metadata structure
(§7.2 above) — the two are different magics guarding different structures. (GitHub issue #1, @DymOK93.)

### 7.4 Verify vbmeta Signature

```
Signature Verification (RSA-2048 / SHA-256):
├── Load embedded public key from GHS
├── Compare vbmeta signing key against known valid key
│   └── Error: "VMM: Error: vbmeta signing key does not match known valid key"
├── Verify RSA signature over vbmeta
│   └── Error: "VMM: vbmeta: image verification failed!"
└── Parse and validate all descriptors
```

### 7.5 Check Rollback Index

```
Rollback Protection:
├── Read stored rollback counter from secure storage
├── Compare vbmeta rollback index against stored value
│   └── Error: "VMM: ERROR: rollback index is too old"
└── Prevents firmware downgrade attacks
```

### 7.6 Load and Verify boot Image

```
boot Image Verification:
├── Read boot_a or boot_b from eMMC
│   └── Error: "VMM: A/B: no boot image for slot %s"
├── Parse Android boot image header:
│   ├── Kernel offset/size
│   ├── Ramdisk offset/size
│   └── Command line
├── Verify boot image signature
│   └── Error: "VMM: Error: Android signature verification failed"
├── Hash kernel and ramdisk
└── Compare against vbmeta hash descriptors
```

### 7.7 Configure Android Kernel Command Line

```
Command Line Additions:
├── androidboot.slot_suffix=%s      ← "_a" or "_b"
├── androidboot.verifiedbootstate=%s ← green/yellow/orange/red
├── androidboot.vbmeta.avb_version=1.1
├── androidboot.trustyimpl=-ghs
└── [All ABL parameters passed through]
```

### 7.8 Launch Android Guest VM

```
VM Launch:
├── ASP_VMX_SetGuestKernelAddr - Set kernel entry point
├── Configure guest memory map via EPT
├── Setup virtio devices for guest
├── Initialize guest CPU state
└── ASP_RunGuestVM - Start Android kernel execution
```

---

## 8. Phase 5: Android AAOS Boot

**Duration:** T=1500-15000ms
**OS:** Android Automotive 12 (API 32)
**Kernel:** Linux 4.19.305 (Broxton)

### 8.1 Linux Kernel Boot

```
Kernel Boot:
├── Decompress kernel from boot image
├── Initialize memory management
├── Start kernel threads
├── Probe device drivers
├── Mount rootfs (dm-verity protected)
└── Execute /init
```

### 8.2 Android Init (First Stage)

```
Init Execution:
├── Parse /init.rc and imported scripts
├── Mount filesystems (fstab.full_gminfo37_gb)
│   ├── /system (dm-verity)
│   ├── /vendor (dm-verity)
│   └── /product (dm-verity)
├── Create device nodes
├── Start ueventd
└── Set initial properties
```

### 8.3 Key Init Scripts

| Script | Purpose |
|--------|---------|
| `init.bxtp_gm.rc` | Main GM initialization |
| `init.trusty-ghs.rc` | GHS Trusty integration |
| `init.protokey.rc` | ProtoKey security service |
| `init.audio.rc` | Audio subsystem |
| `init.crashlogd.rc` | Crash logging |

### 8.4 GHS Trusty Integration (init.trusty-ghs.rc)

```
on early-init
   setprop ro.hardware.gatekeeper trusty
   setprop ro.hardware.keystore trusty
```

### 8.5 ProtoKey Service (init.protokey.rc)

```
on post-fs-data
    mkdir /data/vendor/gm 0771 system system
    mkdir /data/vendor/gm/security 0771 system system
    setprop vendor.gm.security.state init

service gmprotokey /vendor/bin/gm_protokey
    class main
    user root
    group root system cache
    oneshot
```

### 8.6 Critical Services Start Order

```
class core:
├── vold (storage daemon)
│   └── reboot_on_failure reboot,vold-failed
├── apexd (APEX daemon)
│   └── reboot_on_failure reboot,apexd-failed
├── servicemanager
├── hwservicemanager
└── watchdogd

class hal:
├── android.hardware.automotive.vehicle@2.0-service-gm
├── android.hardware.boot@1.1-service
├── vendor.harman.hardware.ame@1.0-service
├── camera provider
├── audio HAL
└── keymaster@3.0 (Trusty-GHS)

class main:
├── gmprotokey
├── GHSCalibrations
├── gm_update_engine
├── surfaceflinger
├── audioserver
└── bootanimation
```

### 8.7 GM Security Services

```
gmprotokey (/vendor/bin/gm_protokey):
├── Receives seed from VIP via GHS IPC (/dev/ghs/ipc)
├── Validates seed/key exchange
├── Creates /data/vendor/gm/security/
├── Sets vendor.gm.security.state property
└── Affects ADB shell access (uid=2000 vs root)

GHSCalibrations (/vendor/bin/GHSCalibrations):
├── Reads calibration data from GHS via /dev/ghs/cal
└── Applies runtime calibrations

gm_update_engine:
├── Monitors USB for update trigger files
├── Communicates with GHS OTA task
└── Manages A/B slot switching
```

### 8.8 Boot Animation

```
/system/bin/bootanimation:
├── Plays GM branded boot animation
├── Runs until sys.boot_completed=1
└── Transition to launcher
```

### 8.9 Boot Completed

```
on property:sys.boot_completed=1
├── sys.boot_completed=1
├── vendor.boot_completed=1
├── Enable CPU frequency governors
├── Enable cpuidle states
└── GHS Sign-of-Health monitoring active

GHS monitors Android heartbeat:
└── Failure: "GHS: [LIFECYCLE] Lost Android SoH - rebooting"
```

---

## 9. Complete Boot Chain Diagram

```
POWER ON (T=0ms)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: VIP (RENESAS TM52176) BOOT                         T=0-50ms        │
│                                                                              │
│   VIP_BOOT → VIP_APP → Read EEPROM → Security Check → Enable SoC Power      │
│                            │                │                                │
│                    ┌───────┴───────┐   ┌────┴────┐                          │
│                    │ EEPROM:       │   │ Sec fn: │                          │
│                    │ 0x0440: SBI   │   │ FULL in │                          │
│                    │ 0x0A80: SBI   │   │ all bld │                          │
│                    │ 0x0B40: Debug │   │ (~906 B │                          │
│                    │ 0x05C0: VIN   │   │ Y175/77 │                          │
│                    └───────────────┘   │  /81)   │                        │
│                                        └─────────┘                          │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: INTEL SOC BOOT                                     T=50-200ms      │
│                                                                              │
│   Intel CSE (ME) → SOC_ABL (Automotive Bootloader) → Load GHS INTEGRITY     │
│        │                    │                                                │
│   ┌────┴────┐        ┌──────┴──────┐                                        │
│   │ Hardware│        │ Secure Boot │                                        │
│   │ Root of │        │ Validation  │                                        │
│   │ Trust   │        │ (ABL.secure │                                        │
│   │ (OTP    │        │  boot=1)    │                                        │
│   │  Fuses) │        └─────────────┘                                        │
│   └─────────┘                                                               │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: GHS INTEGRITY HYPERVISOR                           T=200-500ms     │
│                                                                              │
│   BSP_Init → VMX_Init → VT-d Init → Boot CPUs 1-3 → Start All GHS Tasks     │
│                                                    │                         │
│                                        ┌───────────┴───────────┐            │
│                                        │                       │            │
│                                   ┌────▼────┐            ┌─────▼─────┐      │
│                                   │ VMM1    │            │ Tasks:    │      │
│                                   │ (Android│            │ Camera    │      │
│                                   │  VMM)   │            │ Audio     │      │
│                                   └────┬────┘            │ Lifecycle │      │
│                                        │                 │ VIP, TEE  │      │
│                                        │                 │ Chimes    │      │
│                                        │                 │ OTA...    │      │
│                                        │                 └───────────┘      │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: ANDROID VERIFIED BOOT (AVB)                        T=500-1500ms    │
│                                                                              │
│   Check BCB → Select A/B Slot → Load vbmeta → Verify Sig → Load boot        │
│       │             │                │              │            │           │
│  ┌────▼────┐   ┌────▼────┐    ┌──────▼──────┐ ┌─────▼─────┐ ┌────▼────┐    │
│  │ misc    │   │ misc    │    │ vbmeta_a/b  │ │ RSA-2048  │ │ boot_a/b│    │
│  │partition│   │ @0x800  │    │ partition   │ │ SHA-256   │ │partition│    │
│  │ (BCB)   │   │(CRC32!) │    │             │ │ verify    │ │         │    │
│  └─────────┘   └─────────┘    └─────────────┘ └───────────┘ └─────────┘    │
│                                                                              │
│   → Check Rollback Index → Configure cmdline → ASP_RunGuestVM               │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: ANDROID AAOS                                       T=1500-15000ms  │
│                                                                              │
│   Linux Kernel → init → Zygote → system_server → CarService → HMI Ready     │
│        │           │                                                         │
│  ┌─────▼─────┐  ┌──▼──────────────────────────────────────────────────┐     │
│  │ dm-verity │  │ Key Services:                                        │     │
│  │ protected │  │ • gmprotokey (seed validation → ADB/SELinux state)  │     │
│  │ rootfs    │  │ • GHSCalibrations (calibration data from GHS)       │     │
│  └───────────┘  │ • gm_update_engine (USB update triggers)            │     │
│                 │ • keymaster@3.0 (Trusty-GHS)                        │     │
│                 └─────────────────────────────────────────────────────┘     │
│                                                                              │
│   GHS monitors Android Sign-of-Health heartbeat                             │
│   Failure → "[LIFECYCLE] Lost Android SoH - rebooting"                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Security Boundaries

### 10.1 Security Layer Summary

| Layer | Mechanism | Bypassable? | Notes |
|-------|-----------|-------------|-------|
| **VIP_BOOT** | Harman checksum | Requires RE | Internal RH850 flash |
| **VIP_APP Security** | Function @ 0xb67d0 | Requires RE | **Full ~906 B in all builds (Y175/Y177/Y181)** — no stub. It is a `$27`/seed-access validator, NOT SELinux and NOT the ADB gate (CORRECTED 2026-08-26: the ADB unlock is SoC-side MEC/`is_secure_mode` via DID 0xF1A0 — see EEPROM_LAYOUT §0.9/§0.10) |
| **EEPROM SBI Flags** | None (no CRC) | Yes (hardware) | I2C accessible |
| **Intel CSE** | Hardware root of trust | No | OTP fuses |
| **SOC_ABL** | Intel Boot Guard | **UNKNOWN-FROM-FILES (enforcement is FPF-fuse-dependent)** | Sign Type NONE (not GM TSS-signed). **[C] 2026-10-08 (avbtool/binary, module 85738845):** verified-boot-**capable**, not merely "verified by/with Intel CSE secure boot" — the IFWI contains a production-signed OEM Key Manifest (`oem.key`, `$MN2`), IBB manifest (`IBBP.man`), and a Boot Policy (`BPM.met`) whose three SHA-256 digests match the real IBBL/IBB/OBB bytes exactly. Whether a hash mismatch is REJECTED vs only measured depends on the Intel TXE FPF/OTP fuse state (not in this package) — UNKNOWN-FROM-FILES; settle via MSR `0x13A` or an ISSI SPI dump of the Flash Descriptor/FPF region. Boot Guard digests cover IBBL/IBB/OBB *code* only, not the UEFI NVRAM varstore (see F1 below). |
| **GHS Signature** | ABL validation | **UNKNOWN-FROM-FILES** | Previously stated "Hardware enforced" — corrected 2026-10-08: not provable from files alone (see SOC_ABL row above); downgrade to "verified-boot-capable, enforcement FPF-dependent" until MSR 0x13A or an FPF-region dump settles it. |
| **SOC_ABL lock state (`OEMLock`)** | UEFI NV variable, GUID `1ac80a82-4f0c-456b-9a99-debeb431fcc1` | Potentially (if varstore is SPI-backed, not RPMB — open question) | **[C] 2026-10-08 (CONFIRMED-FROM-BINARY, F1):** SOC_ABL is kernelflinger ("ELK"); `read_device_state_efi()` reads `OEMLock` and `device_is_unlocked()` returns true iff it exists, is readable, and bit 0 (`0x01`) is set — predicate is INTACT/unpatched. `USE_TPM` was NOT compiled (zero TPM2 NV-index constants/calls in the 1 MB module): the lock is **NOT fTPM/TPM2-backed and NOT RPMB** (`ABL.rpmb=` is only an androidboot cmdline token). UNKNOWN-FROM-FILES: whether the varstore itself is SPI-NOR- or RPMB-backed. |
| **AVB vbmeta** | RSA-2048/SHA-256 | No | Without signing key |
| **A/B Metadata** | CRC32 only | Potentially | Weak integrity |
| **Rollback Index** | Secure storage | No | Cannot decrement |
| **dm-verity** | Hash tree | Conditional | Active in enforcing |
| **SELinux** | MAC policy | OS-side only | No stock build runs permissive; byte-identical init forces enforcing on Y175/Y177/Y181 (NOT VIP/EEPROM). Corrected 2026-08-25, `security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8 |

### 10.2 VIP Security Control

```
VIP Security Decision Tree:

EEPROM Read (0x0440, 0x0A80)
         │
         ▼
    ┌─────────┐
    │ SBI=0x00│ ────────────────────────────────────────┐
    │ (Normal)│                                          │
    └────┬────┘                                          │
         │                                               ▼
         │                                    Request seed from BCM
         │                                               │
         │                                               ▼
         │                                    Validate seed/key
         │                                               │
    ┌────┴────┐                                          ▼
    │SBI=0xFF │                              IPC to SoC: "normal mode"
    │(Bypass) │                                          │
    └────┬────┘                                          ▼
         │                                    SELinux: ENFORCING
         ▼
    Security Function @ 0xb67d0
         │
    ┌────┴────────────────────┐
    │                         │
   Y177                      Y181
    │  (fn @0xb67d4)          │  (fn @0xb67d0)
    ▼                         ▼
FULL (~906 bytes)      FULL (~906 bytes)     [Y175 @0xb6708 also FULL]
Validates ADB/seed      Validates ADB/seed   ← corrected 2026-08-25: no stub in any build
    │                         │
    ▼                         ▼
IPC: seed/auth state   IPC: seed/auth state  (VIP does NOT set SELinux mode)
    │                         │
    ▼                         ▼
SELinux mode decided OS-side (ramdisk/init), independent of this function
```

### 10.3 MEC Counter Behavior

```
[PLC] MEC is %d. Ignoring Hypervisor Startup Timeout
[PLC] MEC is 0. Processing Hypervisor Startup Timeout
```

- **MEC = 0** (normal): VIP monitors GHS startup, resets on failure
- **MEC ≠ 0** (bypass mode = 207): VIP ignores hypervisor issues

### 10.4 Three Consecutive Reset Behavior

```
[PLC] ****There have been 3 Consecutive SoC Startup Failures****
[PLC] ****Hypervisor Startup Timer will not be active for this boot cycle****

[SS_SWC] ****There have been 3 Consecutive SoC-Only resets****
[SS_SWC] ****CSM reset for SoC-Only reset will not be active for this boot cycle****
```

After 3 consecutive failures:
- Hypervisor startup timer DISABLED
- CSM reset DISABLED
- System continues booting without normal checks

---

## 11. Key Findings

### 11.1 Dual-Processor Architecture

The A11 module contains two independent processors:
- **VIP (Renesas TM52176)**: Always-on MCU handling power, CAN, and security
- **Intel Atom x7-A3960**: Main SoC running GHS hypervisor + Android guest

VIP boots first and controls SoC power sequencing.

### 11.2 VIP Controls Security Posture (CORRECTED 2026-08-25)

The VIP does **not** control SELinux mode. The prior claim — that permissive required a "Y177
stubbed security function" plus EEPROM bypass — is retracted: the VIP security function is a full
~906-byte validator in Y175, Y177, and Y181 alike (see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2),
and the VIP image contains no SELinux logic at all. What the VIP function + EEPROM SBI
(0x0440/0x0A80) actually gate is **ADB/seed auth** (CAN-confirmed). SELinux runtime mode is an
OS-side property (init/ramdisk), never the VIP. **Note (2026-08-25):** stock Y177 does NOT run
permissive either — its init is byte-identical to Y175/Y181 and forces enforcing; a live permissive
Y177 was a false finding/misread; a modified unit is ruled out — both CSMs only ever ran stock packages (see `security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8).

### 11.3 GHS Hypervisor is Mandatory

Android runs as a guest VM under GHS INTEGRITY:
- VMX (VT-x) hardware virtualization
- VT-d (IOMMU) for device isolation
- EPT for memory management
- Cannot bypass GHS to run modified Android

### 11.4 AVB Enforced by GHS

Android Verified Boot is implemented in the GHS VMM1 task:
- vbmeta signature verification (RSA-2048)
- boot image hash verification
- Rollback index checking
- Cannot bypass without signing keys

### 11.5 A/B Metadata Uses Only CRC32

The A/B slot metadata in the misc partition uses CRC32 for integrity:
- No cryptographic signature
- Potential manipulation vector
- Could force slot switching or boot failures

### 11.6 MEC Counter Affects Behavior

When MEC (Manufacturing Error Counter) ≠ 0:
- VIP ignores hypervisor startup timeout
- May allow modified boot paths

### 11.7 Failure Recovery Mode

After 3 consecutive boot failures:
- Hypervisor timer disabled
- CSM reset disabled
- Boot continues without normal validation checks

---

## 12. Files Analyzed

### Primary Firmware Files

| File | Size | Component |
|------|------|-----------|
| `85098662` | 14.9 MB | SOC_HOSTOS (GHS INTEGRITY) |
| `85738845` | 6.0 MB | SOC_ABL (Intel Bootloader) |
| `86331656` | 1.9 MB | VIP_APP (Y181 Renesas firmware) |
| `86331636` | 1.4 GB | SOC_ANDROID (Android system) |
| `86331654` | 1.5 GB | SOC_ANDROID_VENDOR (Vendor image) |
| `86331650` | 467 MB | SOC_ANDROID_PRODUCT (Product image) |

### Documentation Files

| Path | Content |
|------|---------|
| `gm_aaos/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` | GHS hypervisor analysis |
| `gm_aaos/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` | Boot/recovery flow |
| `gm_dps/VIP_BOOT_CONTROL_ANALYSIS.md` | VIP boot control research |
| `gm_aaos/VIP_FIRMWARE_Y177_Y181_COMPARISON.md` | Y177 vs Y181 differences |
| `gm_pi/06_PROTOCOL_DECODER.md` | Hardware architecture |

### Init Scripts Analyzed

| Path | Purpose |
|------|---------|
| `vendor_extracted/etc/init/hw/init.bxtp_gm.rc` | Main GM init |
| `vendor_extracted/etc/init/hw/init.trusty-ghs.rc` | GHS Trusty integration |
| `vendor_extracted/etc/init/init.protokey.rc` | ProtoKey service |
| `vendor_extracted/etc/init/hw/init.audio.rc` | Audio subsystem |

---

## Appendix A: Error Messages

### VIP Error Messages

```
[PLC] MEC is 0. Processing Hypervisor Startup Timeout
[PLC] ****There have been 3 Consecutive SoC Startup Failures****
[J6_CDD] Reboot to BOLO
[SS_SWC] Theftlocked Active
[SBAT] SbaTicketValidation: Loading keyNBID NVM with default value
```

### GHS/VMM Error Messages

```
VMM: Error: vbmeta signing key does not match known valid key
VMM: vbmeta: image verification failed!
VMM: ERROR: rollback index is too old
VMM: Error: Android signature verification failed
VMM: Failed to verify slot %s
VMM: A/B Boot: ERROR: no valid boot slot
VMM: ERROR: failed to read A/B metadata from 'misc'
VMM: Warning: A/B metadata CRC failure!
VMM: Warning: A/B metadata: magic number mismatch
VMM: I/O error loading boot slot: %d
VMM: A/B Boot: No more remaining attempts for slot %d
GHS: [LIFECYCLE] Lost Android SoH - rebooting
```

### Android Error Messages

```
vold: failed to mount
apexd: activation failed
keymaster: failed to initialize
init: critical process died, rebooting
```

---

## Appendix B: Timing Specifications

| Event | Typical Time | Timeout |
|-------|--------------|---------|
| VIP Boot Complete | 50ms | N/A |
| Intel CSE Init | 100ms | N/A |
| ABL Execution | 100ms | N/A |
| GHS Kernel Init | 200ms | 300ms |
| GHS Tasks Ready | 300ms | 1500ms |
| AVB Verification | 500ms | N/A |
| Android Kernel | 1000ms | N/A |
| Android Init | 3000ms | 6000ms |
| Boot Complete | 10000-15000ms | 120000ms |

---

## Appendix C: IPC Protocol

### VIP ↔ SoC Communication

| Parameter | Value |
|-----------|-------|
| **IPC Version** | 4.1.0 |
| **API Version** | 0404 |
| **Framing** | HDLC |
| **Window Size** | 5 |
| **IFRAME Timeout** | 50ms |
| **UFRAME Timeout** | 20ms |
| **Physical** | UART (115200 8N1) |

**Correction (2026-09, kernel `.config` extraction):** this HDLC/IPC framing is the VIP↔SoC link at the
GHS-task level shown above; on the Android guest side there is **no `N_HDLC` line discipline in the
kernel at all** — the guest never owns `/dev/ttyS1` as a kernel HDLC device. The link surfaces to
Android guest userspace only, via `IPCServer` fanning the channel into per-channel Unix sockets
(`/vendor/etc/ipc4.cfg`) that `libipc.so` clients (VHAL, powermode, rtcd, gmlocation) connect to. See
`platform/boot_chain.md` and `platform/emulator.md` (Un-stub roadmap) for the confirmed wire format.

### GHS IPC Channels

```
tipc_conns (Trusty IPC)
ConnToVIP
ConnToVMM_*
ConnToCamera_*
ConnToTEE_*
ConnToLifecycle
ConnToCalibrations
ConnToOTA
```

---

**Document Version:** 2.0
**Created:** 2026-01-05
**Updated:** 2026-01-05 - Added binary verification evidence
**Analysis Tools:** radare2, Ghidra, strings, file, hexdump, xxd
**Classification:** Security Research

---

## Appendix D: Binary Verification Evidence

This appendix provides cryptographic hashes and direct binary extractions that prove the findings in this document.

### D.1 Firmware File Identification

#### File Hashes (SHA-256)

| File | Component | SHA-256 Hash |
|------|-----------|--------------|
| Y181/85098662 | SOC_HOSTOS (GHS) | `317ae85ccf759476755411e66593dde9f879a43732cd342b4e101e4026535ed3` |
| Y181/85738845 | SOC_ABL | `77b866c6492aa0e8fd2aab8d986182bdef597820a63e0d688a06a12a67f4aed8` |
| Y181/86331656 | VIP_APP | `dbdbb9da3dc14f93e37b94c0e1c5a42921c46fc6e89911159872a6e9e0f87acc` |
| Y177/86283151 | VIP_APP | MD5: `680b0e61aa6c39a28badbd73e5356af2` |

#### Critical Finding: GHS and ABL Identical Between Y177/Y181

```
Y177/85098662 MD5: ded73e3f9026fc8f802bd7485837fc45
Y181/85098662 MD5: ded73e3f9026fc8f802bd7485837fc45  ← IDENTICAL

Y177/85738845 MD5: 61efd392e75660c3eafa92b01be8ed7b
Y181/85738845 MD5: 61efd392e75660c3eafa92b01be8ed7b  ← IDENTICAL

Y177/86283151 MD5: 680b0e61aa6c39a28badbd73e5356af2
Y181/86331656 MD5: e47928d9f409834083abc9a068ce65e0  ← DIFFERENT (VIP_APP)
```

**Implication:** The security difference between Y177 and Y181 is ENTIRELY in the VIP firmware.

---

### D.2 GHS INTEGRITY Version Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)
**Offset:** `0x49168d`

#### Hex Dump of Version Block

```
$ xxd -s 0x49168d -l 128 Y181/85098662

0049168d: 4f53 3a20 2020 2020 2020 2020 2020 2020  OS:
0049169d: 2020 494e 5445 4752 4954 5920 496f 5420    INTEGRITY IoT
004916ad: 3230 3230 2e31 382e 3139 0043 6f72 6520  2020.18.19.Core
004916bd: 5665 7273 696f 6e3a 2020 2020 2032 3337  Version:     237
004916cd: 3339 004d 6f64 756c 6573 2056 6572 7369  39.Modules Versi
004916dd: 6f6e 3a20 2031 3135 3030 0000 0000 0000  on:  11500......
```

#### String Extraction with Offsets

```
$ strings -t x Y181/85098662 | grep -E "(INTEGRITY|Green Hills|MY22)"

491666: Green Hills Software
49168d: OS:               INTEGRITY IoT 2020.18.19
4916b8: Core Version:     23739
4916d0: Modules Version:  11500
b5a812: INTEGRITY IoT 2020.18.19 MY22-026
```

---

### D.3 AVB Implementation Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)

#### AVB Error Strings with Offsets

```
$ strings -t x Y181/85098662 | grep -E "(vbmeta|rollback|A/B.*CRC)"

cf7ff1: VMM: Error: vbmeta signing key does not match known valid key
cf85ac: VMM: ERROR: rollback index is too old: %lu in image, but stored is %lu
cf8762: VMM: Warning: A/B metatdata CRC failure!
```

#### A/B Metadata Uses CRC32 Only (No Signature)

**Evidence:** Searching for "A/B signature" or "metadata sign" returns NO results:

```
$ strings Y181/85098662 | grep -iE "(A.B.*signature|metadata.*sign)"
[NO OUTPUT - confirming no cryptographic signature for A/B metadata]

$ strings Y181/85098662 | grep -i "CRC"
CalculateCRC32
VMM: Warning: A/B metatdata CRC failure!
BSP_CRCFailure
```

**Conclusion:** A/B slot metadata is protected by CRC32 checksum only, not cryptographic signature.

---

### D.4 VIP Y177 vs Y181 Binary Difference

#### Byte-Level Comparison

```
$ cmp -l Y177/86283151 Y181/86331656 | wc -l
549518

549,518 bytes differ (28.4% of 1,934,214 total bytes)
```

#### Critical Region at 0xb67ce (Security Function)

**Y177 (full fn, entry shifted to 0xb67d4):**
```
$ xxd -s 0xb67ce -l 20 Y177/86283151
000b67ce: ff30 0052 7f00 8807 e3ff 06c8 9900 033d  .0.R...........=
```

**Y181 (full fn, entry at 0xb67d0):**
```
$ xxd -s 0xb67ce -l 20 Y181/86331656
000b67ce: 7f00 8807 e3ff 06c8 9900 033d 0545 074d  ...........=.E.M
```

**Observation (CORRECTED 2026-08-25):** This is a **+4-byte alignment shift**, not a stub. The
shared function bytes `7f 00 88 07 e3 ff …` appear at `0xb67ce` in Y181 but at `0xb67d2` in Y177;
the leading `ff 30 00 52` in Y177 is the *tail of the preceding function*, not a `mov 0,r10;
jmp[lp]` return stub. The real validation function begins at `0xb67d0` (Y181) / `0xb67d4` (Y177) /
`0xb6708` (Y175) and is a full ~906-byte function in every build (see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2).

---

### D.5 VIP Module String Proof

**Source File:** `Y181/86331656` (VIP_APP)

#### Module Names with Offsets

```
$ strings -t x Y181/86331656 | grep -E "^\[(SS_SWC|PLC|PROTOKEY|J6_CDD)"

0x2dd6: [SS_SWC] VIP Application Version: %02X.%d.%d.%d
0x2e10: [SS_SWC] Bolo Version: %02X.%02X.%02X.%02X
0x2e3e: [SS_SWC] ARXML Version: %d.%d.%d
0xe656: [PLC] MEC is %d. Ignoring Hypervisor Startup Timeout
0xe6ba: [PLC] MEC is 0. Processing Hypervisor Startup Timeout
0xe6f2: [PLC] ****There have been 3 Consecutive SoC Startup Failures****
```

#### 3x Consecutive Reset Behavior

```
$ strings -t x Y181/86331656 | grep "3 Consecutive"

0x0e6f2: [PLC] ****There have been 3 Consecutive SoC Startup Failures****
0x1b32a: ****There have been 3 Consecutive SoC-Only resets****
```

#### MEC Counter Bypass Logic

```
$ strings -t x Y181/86331656 | grep "MEC is"

0x0e656: [PLC] MEC is %d. Ignoring Hypervisor Startup Timeout
0x0e6ba: [PLC] MEC is 0. Processing Hypervisor Startup Timeout
```

---

### D.6 IPC Protocol Proof

**Source File:** `Y181/86331656` (VIP_APP)

```
$ strings Y181/86331656 | grep -E "\[IPC_S\]"

[IPC_S] IPC: IPC-Version: %d.%d.%d %c
[IPC_S] IPC: API-Version: %04X
[IPC_S] HDLC: Init: Success: WindowSize-%d, Reset State-%d
[IPC_S] HDLC: Init: IFRAME Timeout-%d, UFRAME Timeout-%d
[IPC_S] IFRAME Rx %2d: Rx %d, Exp %d, %d
[IPC_S] UFRAME RESET, receive payload %d
[IPC_S] HDLC: CRC Failed 0x%X Last RSeq:%d
```

---

### D.7 ICUSB Key States Proof

**Source File:** `Y181/86331656` (VIP_APP)

```
$ strings Y181/86331656 | grep "ICUSB enabled"

[AME_DIAG] ICUSB enabled and both key are provisioned.
[AME_DIAG] ICUSB enabled and no key provisioned.
[AME_DIAG] ICUSB enabled and Master key provisioned.
[AME_DIAG] ICUSB enabled and Unlock key provisioned.
```

**Four distinct key states confirmed.**

---

### D.8 ProtoKey Transmission Proof

**Source File:** `Y181/86331656` (VIP_APP)

```
$ strings Y181/86331656 | grep -E "(PROTOKEY|ProtoKey)"

[PROTOKEY] ICUSB module disabled
[PROTOKEY] ICUSB module enabled
[PROTOKEY] Seed %d taken from GMLAN
[PROTOKEY] Seed %d taken from cache
[PROTOKEY] No Seed %d received or cached
[J6_CDD] J6_prv_ProtoKey:Protokey transmitted to SoC, status is %d
[J6_CDD] J6_prv_ProtoKey:Protokey transmit to SoC Failed. SERIAL_IPC_PROTO_KEY_CHANNEL not available
```

---

### D.9 GHS Task Names Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)

```
$ strings Y181/85098662 | grep -E "_InitialTask|ConnTo" | head -20

VMM1_InitialTask
ConnToVMM
ConnToVMM_TextLog
ConnToLifecycle
ConnToCamera
ConnToDisplayI2C
ConnToChimes
ConnToVIP
ConnToCalibrations
ConnToAudit_Crash
ConnToOTA_BootELK
ConnToEMMC
```

---

### D.10 VMX/VT-x Implementation Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)

```
$ strings Y181/85098662 | grep -E "(ASP_VMX|VMCS|VT-d)"

ASP_VMX_MapEptHelper
ASP_VMX_UnmapEptHelper
ASP_VMX_SetGuestKernelAddr
ASP_VMX_SetGuestKernelOffset
ASP_VMX_SetGuestKernelLength
VMCS page is the wrong size
VMCS memory type is wrong
VMX is not supported
VT-d does not support 2MB pages
VT-d is disabled
```

---

### D.11 Trusty TEE Source Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)

```
$ strings Y181/85098662 | grep "keymaster_ipc.cpp" | head -3

/home/mal/gm_release/MY22-026/final/iot/rtos/modules/tee/q/trusty/app/keymaster/ipc/keymaster_ipc.cpp, Line 125: error event (0x%x) for port (%d)
/home/mal/gm_release/MY22-026/final/iot/rtos/modules/tee/q/trusty/app/keymaster/ipc/keymaster_ipc.cpp, Line 138: failed to wait for outgoing queue to free up
/home/mal/gm_release/MY22-026/final/iot/rtos/modules/tee/q/trusty/app/keymaster/ipc/keymaster_ipc.cpp, Line 184: failed (%d) to send_msg for chan (%d)
```

---

### D.12 Android Init Script Verification

**File:** `/vendor/etc/init/hw/init.trusty-ghs.rc`

```bash
$ cat vendor_extracted/etc/init/hw/init.trusty-ghs.rc

# This file or init.trusty.rc is imported, based on the property
# value of ro.boot.trustyimpl.
# This file is used when trusty is provided by the GHS hyper-visor

on early-init
   setprop ro.hardware.gatekeeper trusty
   setprop ro.hardware.keystore trusty
```

**File:** `/vendor/etc/init/init.protokey.rc`

```bash
$ cat vendor_extracted/etc/init/init.protokey.rc

on post-fs-data
    mkdir /data/vendor/gm 0771 system system
    mkdir /data/vendor/gm/security 0771 system system
    setprop vendor.gm.security.state init

service gmprotokey /vendor/bin/gm_protokey
    class main
    user root
    group root system cache
    oneshot
```

---

### D.13 Boot Command Line Proof

**Source File:** `Y181/85098662` (SOC_HOSTOS)

```
$ strings Y181/85098662 | grep "androidboot\." | head -10

clocksource=tsc tsc=reliable acpi_pm_good i915.avail_planes_per_pipe=0x000003 i915.enable_pvmmio=0 androidboot.diskbus=1c.0 androidboot.boot_devices=pci0000:00/0000:00:1c.0 androidboot.trustyimpl=-ghs androidboot.product.hardware.sku=gv221
androidboot.force_normal_boot=1
androidboot.slot_suffix=%s androidboot.verifiedbootstate=%s
androidboot.vbmeta.avb_version=1.1 androidboot.vbmeta.device_state=%s androidboot.vbmeta.hash_alg=sha256
androidboot.bootreason=cold
androidboot.bootreason=warm
androidboot.bootreason=reboot
```

---

## Appendix E: Reproduction Commands

To reproduce any finding in this document, use the following commands:

```bash
# Navigate to update packages directory
cd /path/to/gm_aaos/update_packages

# 1. Verify file hashes
shasum -a 256 Y181/85098662 Y181/85738845 Y181/86331656

# 2. Extract GHS version
strings -t x Y181/85098662 | grep "INTEGRITY IoT"

# 3. Find AVB error messages
strings Y181/85098662 | grep -E "(vbmeta|rollback)"

# 4. Find A/B CRC messages (no signature)
strings Y181/85098662 | grep -i "A/B.*CRC"

# 5. Compare VIP firmware
cmp -l Y177/86283151 Y181/86331656 | wc -l

# 6. Extract VIP module strings
strings Y181/86331656 | grep -E "^\[(SS_SWC|PLC|PROTOKEY)"

# 7. Find 3x reset messages
strings Y181/86331656 | grep "3 Consecutive"

# 8. Find MEC counter messages
strings Y181/86331656 | grep "MEC is"

# 9. Dump specific hex region
xxd -s 0x49168d -l 128 Y181/85098662
```

---

## Appendix F: Kernel Configuration + GHS Coupling (2026-09)

Extracted and analyzed the real Y181B (gminfo37 CSM) boot image from the firmware update package,
cross-checked byte-identical against the live device's own `.config`.

### F.1 Boot Image

Android boot header v2, page size 2048. Kernel: x86_64 bzImage, 15,364,688 bytes, LZ4-compressed
vmlinux, load addr `0x10008000`. Ramdisk: 20,984,589 bytes, LZ4-legacy, load `0x11000000`. A "second"
8061-byte blob is an Intel NHLT audio-DSP ACPI table wrapper, not boot code. `dtb` size 0 (no device
tree — pure ACPI). Loaded by Intel Slim Bootloader → ABL (kernelflinger), not EFI-stub.

### F.2 Kernel Identity

`Linux version 4.19.305-240125T145315Z-gf1edde901aa7 ... SMP PREEMPT ... Tue Jul 22 07:52:16 EDT 2025`,
clang 12.0.7 (Android r416183b1), x86_64, SMP, `NR_CPUS=32`, `HZ=1000`, X2APIC, KASLR on. Android Common
Kernel 4.19 base, heavily GM/Intel-patched (GHS drivers, Titan/Broxton Apollo Lake program, IPU4
camera, Trusty TEE).

### F.3 The Crux Finding — No pv-ops Contract

`CONFIG_PARAVIRT` is **not set**. `CONFIG_HYPERVISOR_GUEST=y` exists but only enables optional
detection — there is no Linux pv-ops contract, no `KVM_GUEST`, `XEN`, `HYPERV`, `PVH`, or
`JAILHOUSE_GUEST`. The kernel's core MMU/timekeeping/IRQ/scheduling is bare-metal x86_64 — it is **not**
a paravirtualized-at-the-core guest despite running under GHS INTEGRITY. The only GHS coupling is via
ordinary Linux DEVICE DRIVERS (not core kernel infrastructure): `CONFIG_GHS_PARAVIRTUAL_SUPPORT=y`,
`CONFIG_GHS_GUEST_COMMS=y`, `CONFIG_GHS_VMM_BOOTLOADER_CONTROL=y`, `CONFIG_SND_GHS_PCM=y`,
`CONFIG_ANDROID_GM_GHS_MMC=y`, `CONFIG_TITAN_X86_BROXTON_PROGRAM=y`.

### F.4 GHS Transport Mechanism (from binary strings/disasm of `ghs_comms` in vmlinux)

`ghs_comms` is a PCI driver binding to a Green-Hills-presented **virtual PCI function, vendor
`0x1B95`, device `0xA000`** (subvendor/subdevice=ANY). Standard PCI enumeration
(`pci_enable_device`, `pci_request_regions`), BAR-mapped send/receive ring registers, MSI-X interrupts,
and a host/guest **version handshake** (log strings: "Host didn't accept driver version %d or fallback
version %d", "GHS_VMM: version incompatibility"). A companion driver `ghs_vmm_bc`
(`GHS_VMM_BOOTLOADER_CONTROL`) talks to the GHS VMM for A/B slot/boot-control and delivers the guest's
TSC frequency (log string "GHS_VMM: TSC_FREQ = %lld" — the guest's timebase comes from the VMM, not
native TSC calibration). Other GHS-coupled builtin drivers: `gm_ghs_mmc` (paravirtual MMC, exposes
`/dev/ghs/emmc-health`), `snd_ghs_pcm` (paravirtual audio PCM), `ghs_camera_memory_map` (IPU4 camera
buffer sharing). All are ordinary PCI/platform drivers that fail their own `probe()` gracefully (device
not found → driver stays unbound, no panic) when their backing GHS PCI function is absent — standard
Linux driver behavior, confirmed structurally from the driver code (probe-based binding, not a hard
init-time dependency).

### F.5 Platform, Storage, virtio, Networking, Console

- **Platform:** Apollo Lake/Broxton — `CONFIG_X86_INTEL_LPSS`, `PINCTRL_BROXTON`,
  `X86_INTEL_PSTATE`, `VIDEO_INTEL_IPU4` (camera), `DRM_I915=y` **and** `DRM_BOCHS=y` (both compiled
  in — `DRM_BOCHS` gives a plain framebuffer path independent of i915). `ACPI=y`, `CONFIG_OF` (device
  tree) not set — fully ACPI-driven, no DT fallback exists.
- **Storage/verified boot:** `DM_VERITY=y` + `DM_VERITY_FEC=y` (matches AVB hashtree+FEC posture),
  `DM_DEFAULT_KEY=y`, `MMC_SDHCI_PCI`/`ACPI=y`, EXT4/F2FS with FS encryption, `EFI_PARTITION=y` (GPT).
- **virtio — present but narrow:** `CONFIG_VIRTIO=y`, `VIRTIO_PCI=y`, **`VIRTIO_PCI_LEGACY=y`** (not
  modern-only), `VIRTIO_BLK=y`, `VIRTIO_CONSOLE=y`. Notably absent: `VIRTIO_MMIO`, `VIRTIO_NET`,
  `VIRTIO_INPUT`, `VIRTIO_BALLOON`, `VIRTIO_RPMB`. The existing virtio backs Trusty TEE
  (`TRUSTY_VIRTIO=m`), not the main rootfs. Absence of `VIRTIO_MMIO` means this kernel is
  **incompatible with Google's ranchu/goldfish AVD backend** (which uses virtio-mmio) — any real-kernel
  boot must target plain `qemu-system-x86_64` q35/i440fx (virtio-pci), never the AVD emulator binary.
- **Networking:** no `VIRTIO_NET`, but `CONFIG_E1000=y` and `CONFIG_E1000E=y` are present — a QEMU
  `e1000e` NIC would bind with the in-tree driver without any kernel rebuild.
- **Console:** full 8250 UART stack (`SERIAL_8250_CONSOLE`, `_DW`, `_LPSS`, `_MID` variants, 32 UARTs),
  `HVC_DRIVER=y`.

### F.6 Cmdline (captured from the boot image header)

Base: `video=HDMI-A-1:e loglevel=2 enforcing=0 androidboot.selinux=permissive no_timer_check noxsaves
reboot_panic=p,w i915.hpd_sense_invert=0x7 intel_iommu=off loop.max_part=7 rootfstype=ext4 gpt
console=tty0 androidboot.hardware=full_gminfo37_gb firmware_class.path=/vendor/firmware
relative_sleep_states=1 intel_pstate=disable pstore.backend=ramoops
memmap=0x400000$0x50000000 ramoops.mem_address=0x50000000 ramoops.mem_size=0x400000`; appended (later
tokens win) `i915.enable_guc=2 intel_ipu4_psys.async_fw_init=Y thermal.off=1 trace_buf_size=64M
enforcing=1 androidboot.selinux=enforcing buildvariant=user`. Net effective: SELinux enforcing (last
token wins), no explicit `root=` (system-as-root via first_stage_mount), `intel_iommu=off`,
`no_timer_check`.

### F.7 First-Stage Init / Mount Chain (also see `platform/boot_chain.md`)

System-as-root, `init -> /system/bin/init`. The ramdisk's own `fstab.full_gminfo37_gb` marks
partitions `logical,first_stage_mount` (an unused build-mixin default) — the AUTHORITATIVE
first-stage fstab is actually an **ACPI SSDT table** (`_HID ANDR0001`, OEM Table ID "android") whose
`_DSD` property gives real by-name **static** partitions on PCI eMMC at `0000:00:1c.0` with
`wait,slotselect,avb` flags — confirming **static A/B** (no dynamic-partitions `super`, no dm-linear),
consistent with the static-A/B note in `platform/emulator.md`. `ro.boot.dynamic_partitions=true` exists
as a prop but is overridden by this static SSDT layout in practice. The SOC_ACPIO firmware module is a
2MiB Intel ACPI-magic overlay partition carrying exactly this android SSDT plus Broxton platform ACPI
tables (LPSS, PMC/PUNIT IPC, SDHCI-ACPI). Any future QEMU port needs to inject an equivalent SSDT
(`-acpitable`) plus Broxton platform ACPI, since QEMU's default q35 ACPI does not provide `ANDR0001`.

The VIP link is a **userspace** protocol confirmed from this kernel config: no `N_HDLC` line discipline
is compiled in anywhere, so the VIP/RH850 protocol over `ttyS1` cannot be an in-kernel driver
dependency — see the Appendix C correction above and `platform/boot_chain.md`.

## Appendix G: QEMU Portability Assessment (2026-09)

**Verdict — MILESTONE CONFIRMED (2026-09-27), supersedes the earlier "reaches second-stage init,
blocked on SELinux-enforcing/vold-failed" interim status recorded in the previous pass of this
appendix:** the real GM kernel IS portable to plain `qemu-system-x86_64` (q35 machine type), and this is
now an empirical result at full-boot fidelity, not just a static-analysis claim or a partial-boot
result. GHS is a SERVICE-layer blocker (specific vendor daemons/HALs stay dead without it), **not** a
BOOT-layer blocker — the kernel boots without any GHS device present, per the `CONFIG_PARAVIRT`-off
finding (F.3) and the PCI-driver graceful-degrade structure (F.4), both directly observed at runtime.
This refines the `platform/emulator.md` claim "GM's real vendor firmware can't boot on goldfish": the
precise statement is **"can't boot on goldfish/ranchu specifically (virtio-mmio backend, wrong machine
type) — the real kernel boots on plain qemu-system-x86_64/q35 (virtio-pci backend), and now boots
AUTONOMOUSLY (no manual intervention) all the way to a fully rendered, themed AAOS home screen, in ~4
minutes cold boot (q35, `-accel hvf`, virtio-blk-pci, e1000e) on the Mac Pro, isolated from the goldfish
AVD. Reproduced twice (a manual-assisted first pass, then a clean hands-off autoboot) with matching
screencaps at different timestamps, confirming reproducibility; verified live via qemu screendump +
guest shell, not build-only. The previously-blocking `vold-failed`/SELinux-enforcing second-stage reboot
loop is resolved as part of reaching the home screen. Treat the kernel/vendor-ABI portability question
as settled at full-boot fidelity — remaining work is now UI/calibration parity with the goldfish hybrid
(see `platform/emulator.md`'s visual/calibration parity-gap note) and the still-open items below (VHAL
now runs NATIVELY with no shim needed at all — a further improvement over the "stubbable via
libipc_shim" classification in G.2 below, since the real IPCServer already provides the link), not a
kernel or GHS-coupling risk."**

**VHAL update:** the real IPCServer (userspace VIP-link daemon) runs and sets
`vendor.modules.ipcserver.ready`; `android.hardware.automotive.vehicle@2.0-service-gm` registers for
real (`lshal` shows `IVehicle/default`), with CarService running 34 real property-subscription clients
and driving-state correctly deriving PARKED. No `libipc_shim` port was needed here — see
`platform/emulator.md`'s "VHAL — native, no shim needed" subsection for the full writeup. **Graphics**
was solved via a from-scratch software-rendering stack (`gralloc.swfb.so` + patched
`hwcomposer.swfb.so` + SwiftShader sourced from the goldfish `google_apis` image) rather than the
drm_hwcomposer/SwiftShader retargeting anticipated in G.2 below — see `platform/emulator.md`'s
"Graphics stack" subsection for the full writeup; the anticipated approach in G.2's Display row is
superseded by this actually-implemented one.

Two assumptions in this plan were tested and found wrong, then corrected: (1) the extracted ACPI SSDT
(`ssdt_android.aml`, `_HID ANDR0001`) loads into ACPI fine but does **not** work as a DT-fstab source —
`fs_mgr`'s `ReadFstabFromDt()` fails because its nested `fstab/<part>/{dev,type,...}` node layout doesn't
match the flat dotted `_DSD` properties this ACPI path produces; do not rely on the SSDT for partition
discovery. (2) The actual working fix is patching the ramdisk's plain-text first-stage fstab
(`first_stage_ramdisk/fstab.full_gminfo37_gb`) directly: drop `logical`/`avb` from fsmgr_flags, point
each entry at the PCI-scoped `/dev/block/pci/pci0000:00/0000:00:1c.0/by-name/<partition>` path (matching
wherever virtio-blk attaches) with `slotselect` — the flat `/dev/block/by-name/...` path is never
created by first-stage init on this kernel. A new hardware-fidelity fact from vendor `file_contexts`:
`ttyS0`=`bluetooth_serial_device`, `ttyS1`=`ipc_serial_device` (confirms ttyS1 as the real VIP/libipc
channel by SELinux label); the console must be on `ttyS2`+ (`serial_device`) or SELinux denies the
write.

**Formerly the stopping point, now resolved:** GM's `user` build forces `enforcing=1` regardless of the
permissive cmdline arg (`selinux=0` outright breaks `mount(selinuxfs)`, so SELinux can't be compiled out
either — it's a hard build requirement). This previously caused `vold` to be AVC-denied and killed → a
second-stage reboot loop. That loop is now resolved as part of the full boot-to-home-screen milestone
above (see `platform/emulator.md` for the fix details); `data`(f2fs) and a live shell are both reached.
Remaining open items are UI/calibration parity with the goldfish hybrid and the 38-unidentified-crashes
item from the logcat analysis (see `platform/emulator.md`'s logcat comparative-analysis subsection), not
the SELinux/vold boot blocker.

Artifacts (`run.sh`, `mkstatic.py`, `patch_cpio.py`, `ssdt_noavb.aml`/`.dsl`, `fstab.patched`,
`serial.log`) preserved to
`/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_integration/realk/`;
full working tree (incl. the 6GB `gm.img`, not copied off) remains on the Mac Pro at `~/gm_emu/realk/`.

### G.1 Two Strategies Compared

- **(a) RECOMMENDED:** boot GM's real kernel binary as-is on `qemu-system-x86_64`/q35 with
  virtio-pci-legacy block+console, e1000e NIC, `DRM_BOCHS` framebuffer, ACPI SSDT injection (the
  extracted `ssdt_android.aml`), and a modified cmdline (add `androidboot.slot_suffix`, adjust display
  args for bochs instead of i915, handle AVB either via a matching vbmeta or a verity-off cmdline path
  like the current hybrid). This preserves the exact kernel-vendor ABI — GM's vendor HALs/modules (e.g.
  an out-of-tree `igb_avb` module) were built against THIS kernel's headers/KMI, and the current
  goldfish hybrid's whole fidelity problem is a kernel/vendor ABI mismatch that this strategy
  eliminates entirely for anything that doesn't specifically need a GHS-backed device.
- **(b) NOT RECOMMENDED:** rebuild an ACK 4.19 kernel retargeted to ranchu/virtio-mmio (flip on
  `VIRTIO_MMIO`/`VIRTIO_NET`/`DRM_VIRTIO_GPU`, drop GHS/Titan config). Boots "more cleanly" on the
  existing AVD but reopens exactly the kernel/vendor-ABI gap the project is trying to close (GM's
  vendor modules would no longer match). Only justified if (a) hits an unforeseen in-tree driver that
  hard-faults on QEMU (none found in this analysis).

### G.2 Per-Dependency Classification

(providable = QEMU supplies it natively; patchable = needs a cmdline/config/ACPI tweak; stubbable =
needs a software shim, same class as the existing libipc/libpal_tod work; hard-blocker = genuinely
absent, stays dead)

| Dependency | Class | Notes |
|---|---|---|
| CPU/entry/ACPI-fstab/storage(virtio-blk)/console/e1000e-networking/AVB | Providable/patchable | q35+virtio-pci+ACPI-SSDT-injection, no kernel source changes |
| Display (i915 expects real Gen9 GPU) | Stubbable / **GPU-accelerable** | `DRM_BOCHS` (already compiled in) + the same drm_hwcomposer/SwiftShader work the goldfish hybrid already solved — not a new problem, same effort retargeted. **(updated 2026-10-01: software rendering is no longer the only option — the kernel was rebuilt from the exact Intel LTS base with `CONFIG_DRM_VIRTIO_GPU` (CRC-matched, re-signed with its own key) and now runs hardware-accelerated virgl via a custom QEMU → ANGLE → Metal; see `platform/emulator.md`.)** |
| VIP/IPC (ttyS1 userspace protocol) | Stubbable | reuse the existing `libipc_shim.c`/frame-injection tooling verbatim — kernel-agnostic |
| GHS transport itself (`ghs_comms` PCI device, `/dev/ghs/*`) | Stubbable/absent | driver never binds; no panic. Only matters for what's downstream (next rows) |
| A/B boot-control (`GHS_VMM_BOOTLOADER_CONTROL`) | Stubbable | `androidboot.slot_suffix` on cmdline + a static/software `IBootControl` HAL (same manifest-swap technique the hybrid already used) |
| Hardware keymaster/attestation/RPMB (Trusty TEE, requires GHS) | Hard blocker | permanent — same as today's software-keymaster stub, no regression |
| Harman AVB audio (802.1BA + NXP TDF8532 codec) | Hard blocker | permanent — same as today's Google `audio@6.0` stub, no regression |
| GHS cal/chime/camera/emmc-health overlay tasks | Stubbable/absent | same posture as today |

### G.3 Payoff and Effort Estimate

Booting the real kernel (vs. the current goldfish hybrid) would run on the native kernel/vendor ABI
instead of goldfish's, unlocking: real vendor `init` + real vendor SELinux domains/policy loaded
natively (no VINTF-manifest surgery needed to make GM vendor fit a foreign kernel); `diagnosticsd`
(`:49156`, currently completely absent from the goldfish emulator because its vendor-lib dependency web
assumes the real kernel/vendor) becomes potentially runnable; the real VHAL's kernel-side dependencies
resolve natively (still needs a VIP peer via the existing shim, but no cross-kernel-ABI translation
layer); this is no longer needed via a shim at all, since the real IPCServer resolves natively (see
VHAL update above). Original effort estimate: ~2-4 focused days to first kernel-up/first-stage-mount/
adb-shell; +1-2 weeks to a stable AAOS UI (matching the current hybrid's maturity) — **superseded:** the
home-screen milestone above was reached within that estimate's window; remaining work is UI/calibration
parity (see `platform/emulator.md`), not additional bring-up.

**Framing for future work:** worth doing specifically for vendor-layer fidelity (`diagnosticsd`, native
vendor SELinux/HALs) — not a general shortcut over the existing goldfish hybrid, which remains
better/cheaper for UI/RE work that doesn't need those specific vendor daemons.

---

**Related Documents:**
- VIP_FIRMWARE_Y177_Y181_COMPARISON.md
- GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md
- VIP_BOOT_CONTROL_ANALYSIS.md
- EEPROM_CALIBRATION_MAPPING.md
- SBI_SECURITY_SCOPE_ANALYSIS.md
