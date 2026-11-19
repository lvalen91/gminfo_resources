# GM Info 3.7 (A11 Module) Boot Chain Analysis

**Module:** A11 CSM (Central Stack Module) | **Vehicle:** 2024/2025 Chevrolet Silverado 2500 HD
(T1XX platform) | **Firmware:** Y181 primary analysis, Y175/Y177 compared where it matters.

**Scope:** the architectural, binary-RE walkthrough of one full boot — power-on through VIP,
Intel CSE/ABL, GHS INTEGRITY, AVB, and AAOS init — plus the security-boundary table this walkthrough
supports and the research-tier QEMU-portability evidence (raw kernel-config/GHS-coupling facts and
the per-dependency portability table) that `platform/emulator.md` itself points back into.

**What does NOT live here:** the raw byte-level forensic evidence base (hashes, hex dumps, string
offsets, full `cmp` diffs) — that's `BOOT_CHAIN_ANALYSIS.txt` (BCA), this doc's explicit companion;
neither supersedes the other. GHS hypervisor architecture detail (PCI driver table, full task/IPC
maps, `.boottable` config, `/dev/ghs/*`+SELinux labels, attack-surface catalog) is
`GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` (GIC). Live-tested recovery/ELK/update privilege
boundaries, the full SBI→MEC→ADB-cert bypass chain, and A/B+BCB+trigger-file mechanics are
`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` (GBUR). The canonical EEPROM map is
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` (ELA). Seed-key/SecurityAccess/ProtoKey crypto detail is
`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK). AVB/vbmeta parser fuzz-target RE is
`VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md` (VPF). QEMU bring-up narrative/current status and the
Y175/Y177/Y181(B) firmware-identity comparison live in `platform/emulator.md` and
`platform/firmware_versions.md` respectively — this doc cites them, not restates them.

**Evidence tags** (reused from `platform/README.md`): `[C]` confirmed live, `[V]` verified,
`[FW]`/`[S]` static firmware, `[inferred]`, `[U]` unverified, `[X]` external. Dated per-claim tags
override surrounding prose.

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
13. [Appendix A: Error Messages](#appendix-a-error-messages)
14. [Appendix B: Timing Specifications](#appendix-b-timing-specifications)
15. [Appendix C: IPC Protocol](#appendix-c-ipc-protocol)
16. [Appendix D: Binary Evidence (pointer)](#appendix-d-binary-evidence-pointer)
17. [Appendix E: Kernel Configuration + GHS Coupling](#appendix-e-kernel-configuration--ghs-coupling)
18. [Appendix F: QEMU Portability — Dependency Classification](#appendix-f-qemu-portability--dependency-classification)
19. [Open Conflicts](#open-conflicts)

---

## 1. Hardware Architecture Overview

The A11 module uses a dual-processor architecture: the Renesas VIP (Vehicle Interface Processor)
manages power and vehicle interfaces; the Intel Atom SoC runs the GHS hypervisor and the Android
guest VM.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     A11 CSM (Central Stack Module)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│   ┌─────────────────────────┐         ┌─────────────────────────────────┐   │
│   │  RENESAS VIP             │◄══════►│  INTEL ATOM x7-A3960 (J6/SoC)   │   │
│   │  R7F7015873AFP           │  HDLC   │  Apollo Lake (Broxton)          │   │
│   │  RH850/F1K, G3KH core    │   IPC   │                                  │   │
│   │  (trace marking TM52176) │         │  • SOC_ABL (bootloader)         │   │
│   │  • VIP_BOOT (~128KB)     │         │  • GHS INTEGRITY hypervisor      │   │
│   │  • VIP_APP (~1.9MB)      │         │  • Android AAOS (guest VM)       │   │
│   │  • EEPROM access (I2C)   │         │  • 8GB LPDDR4 / 64GB eMMC        │   │
│   │  • CAN/LIN interface     │         │                                  │   │
│   └────────────┬────────────┘         └──────────────┬──────────────────┘   │
│   ┌────────────▼────────────┐         ┌──────────────▼──────────────────┐   │
│   │  M24C64 EEPROM (8KB)    │         │  Samsung eMMC (64GB)            │   │
│   │  Security flags, VIN,   │         │  A/B partitions, boot_a/b,      │   │
│   │  calibrations, ProtoKey │         │  system, vendor, vbmeta, misc   │   │
│   └─────────────────────────┘         └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Component | Chip | Function |
|-----------|------|----------|
| **Main SoC** | Intel Atom x7-A3960 | 4-core CPU, GPU, runs GHS + Android |
| **VIP MCU** | Renesas R7F7015873AFP (RH850/F1K; trace marking TM52176) | Power control, CAN/LIN, security |
| **RAM** | LPDDR4, 8192 MiB physical | Static GHS guest grant / visible-memory split, E820 measurement, grant-vs-visible gap: owned by [GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md §7a3](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory) — not restated here. |
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

These are estimates derived from the timer/log evidence below (Appendix B), not an independently
sourced trace.

---

## 3. Phase 0: Power On

```
Vehicle Battery → A11 Power Supply
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
| `cal_startup_fault_timeout_sec` | 6000ms (see [Open Conflicts #1](#open-conflicts)) | Full boot timeout |

### Wake Sources

- GMLAN CAN message (network wake)
- Door ajar signal
- Remote start command
- Scheduled wake (OnStar)

---

## 4. Phase 1: VIP (Renesas RH850) Boot

**Duration:** T=0-50ms
**Processor:** Renesas R7F7015873AFP (RH850/F1K, G3KH core; trace marking TM52176)

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

| Property | Value | Source |
|----------|-------|--------|
| **VIP_APP version (Y181B, live `moduleinfo`)** | `2B.B5.01.01`, build `25Jun19-2209`, image `appl`, part 86331656 | `update_cache/update/moduleinfo`, direct read, 2026-11-12 |
| **VIP_BOOT version** ("Bolo") | `B2.9C.01.01`, build `23Jul28-1212`, part 85056831 | Same across Y175/Y177/Y181B — part number identical, per `platform/firmware_versions.md` |
| **SoC-side module (part 85738845)** | version `2344` | Live-read, module slot 72 — naming conflict with "SOC_ABL" used in §5.2/§10.1, see [Open Conflicts #3](#open-conflicts) |
| **FIDM** | version `6`, part 84961617 | module 81 |
| **ARXML Version** | 22.22.158 | — |
| **IPC Version** | 4.1.0 | — |
| **HwVariant** | 56 | — |

**History:** an earlier pass of this table carried a row labeled "Version (Y177)" = `2B.174.4.1`
(build `24Mar22-0256`). That string is from a UART capture (`enumeration/VIP_log_2B.174.4.1_10JUL24.txt`)
predating even Y175's own VIP_APP (`2B.175.1.5`, build `24Apr23-2202`, part 85759599); Y177's actual
VIP_APP (part 86283151) builds `25Feb28-0330` and has no confirmed version string in this repo
(`VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §1 lists it as `—`). Corrected 2026-11-12: do not read
`2B.174.4.1` as any Y177 value; the row above replaces it with the directly-read Y181B values.

### 4.3 VIP Module Initialization Sequence

```
VIP_APP Module Init:
├── SS_SWC      - System State Controller (sleep/wake/shutdown)
├── PLC         - Power Level Control (SoC power sequencing)
├── J6_CDD      - Intel Atom (J6) Communication Driver
├── IPC_S       - Inter-Processor Communication Server
├── AMP_MGR_SWC - Audio Amplifier Manager
├── PROTOKEY    - Security key management
├── SBAT        - Secure Boot anti-rollback (keyNBID/appNBID generation numbers)
├── IOHWAB_MIC  - Microphone Hardware Abstraction
└── NAV         - Navigation/GNSS interface
```

SBAT's full expansion is **unconfirmed** from firmware strings. The keyNBID/appNBID generation-number
scheme matches the UEFI/shim "Secure Boot Advanced Targeting" revocation model (per-component
generation numbers that revoke outdated/vulnerable components) — the leading interpretation, not a
confirmed one. SBAT/ProtoKey gate-independence detail: `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`.

### 4.4 EEPROM Read (M24C64)

VIP reads configuration from external EEPROM via I2C at these addresses (walkthrough-level; the
canonical map, including the settled 0x0A80-vs-0x0A81 marker/data correction, is
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` — read that for authoritative addresses, not this table):

| Address | Size | Content | Purpose |
|---------|------|---------|---------|
| 0x0440 | 2 | Primary SBI Flag | Security bypass indicator |
| 0x0A80 | 2 | Backup SBI Flag | Redundant security flag |
| 0x0B40 | 1 | Debug Mode Flag | Developer mode |
| 0x05C0 | 17 | VIN | Vehicle identification |
| 0x0600+ | Varies | Calibrations | ~30 `cal_*` parameters |

### 4.5 Security Validation Function (@ 0xb67d0)

A three-way VIP_APP diff (Y175/Y177/Y181) proves this validator is a **full ~906-byte function in
all three builds** — no stub (see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2 for the authoritative
diff).

| Version | Function entry | Function Size | Behavior |
|---------|----------------|---------------|----------|
| **Y175** | `0xb6708` | ~906 bytes | Full validation |
| **Y177** | `0xb67d4` | ~906 bytes | Full validation |
| **Y181** | `0xb67d0` | ~906 bytes | Full validation |

```
Validation function (Y181 @0x000b67d0; Y177 @0xb67d4; Y175 @0xb6708) — FULL in every build:
    ├── Load security/seed flag from memory 0x3e06 (0xFEBD3E06)
    ├── Compare against expected value
    ├── Multiple conditional branches
    ├── Calls to validation functions: 0xecd84, 0xb6652, 0xaee28
    └── Returns error codes on failure
```

**History (the "Y177 stub" retraction, settled 2026-08-25/26):** an earlier pass of this corpus
claimed Y177's build of this function was a 4-byte stub (`mov 0,r10; jmp [lp]`) and that permissive
Y177 units existed. Both claims are **retracted**. The "stub" reading was a fixed-absolute-address
misread: reading Y177 at the fixed offset `0xb67d0` lands 4 bytes early, on the *tail of the previous
function* (`00 52 7f 00 …`); the real function begins at `0xb67d4` (+4 bytes). Aligned body diffs are
only 15/906 bytes (Y177↔Y181) and 18/906 bytes (Y175↔Y181) — same source, recompiled. Entry bytes are
identical across all three builds: `88 07 e3 ff 06 c8 99 00 03 3d 05 45 07 4d 83 a7`. Corroborating:
SOC_HOSTOS (GHS) and SOC_ABL are byte-identical (MD5-matched) between the Y177 and Y181 update
packages — only VIP_APP differs build-to-build, and that difference is the 15-18 aligned bytes above,
not a stub. No stock build runs permissive: a previously reported live-permissive Y177 unit was a
false finding/misread — both CSMs sampled only ever ran stock packages (`research/security/KERNEL_CVE_ANALYSIS.txt`
Appendix E.8). This retraction is stated once here; every other place in this corpus that touched the
"Y177 stub"/permissive-Y177 claim (§10.1, §10.2, §11.2, Appendix D.1/D.4 below) now just points back
to this section instead of restating it.

**What this function gates:** see the resolved VIP-vs-SoC ADB-gate question in
[Open Conflicts](#open-conflicts) — summary: this is a `$27`/seed-access validator, not the ADB gate
and not SELinux. No `selinux`/`enforce`/`permissive` strings exist anywhere in the VIP image.

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

The crypto/IPC-chain detail downstream of this (the `gm_protokey` → `libpal_security.so` path,
16-byte-key handling) is owned by `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`'s ProtoKey section —
pointer only, not restated here.

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
| `cal_startup_fault_timeout_sec` | 15 (see [Open Conflicts #1](#open-conflicts)) | Boot timeout |
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
| **Secure Boot** | `ABL.secureboot=1` |

SOC_ABL is kernelflinger ("ELK"). Lock-state backend, Boot Guard/FPF fuse status, and the
`OEMLock` UEFI variable mechanism are owned by `platform/elk_recovery.md` §2.3 and
`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` — summarized, not restated, in §10.1 below.

```
ABL Execution:
├── Secure Boot validation against hardware root of trust
├── Load GHS INTEGRITY from eMMC partition
├── Verify GHS signature (cannot be bypassed)
├── Configure kernel command line
└── Transfer control to GHS kernel
```

Chain clarification: Intel Slim Bootloader hands off to SOC_ABL (kernelflinger), which loads and
verifies GHS INTEGRITY. GHS's own VMM1 task — not ABL directly — then performs AVB and launches the
Android guest VM (§7-§8 below).

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
| **Build Path** | `/home/mal/gm_release/MY22-026/final/iot/rtos/` |
| **Vendor** | Green Hills Software |
| **Target** | Intel Apollo Lake (gm-i35) |
| **File** | SOC_HOSTOS (85098662) — 14.9MB |

### 6.2 GHS Architecture (summary)

VMM (VMX/VT-d/EPT/guest memory) → kernel services (task/thread, memory, interrupts, IPC) → device
drivers (PCI, passthrough, I/O) → security services (Trusty TEE, secure boot, AVB). The full PCI
driver table, `.boottable` guest/VM config, and per-layer function lists are
`GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`'s charter — pointer only.

### 6.3 Stage A: CPU Initialization

```
1. BSP_InitializeOnBootCpu       — x86-64 feature detection, memory controller init
2. ASP_PreCrtInitializeBootstrap — C runtime init, stack setup, global constructors
3. ASP_VMX_InitializeOnBootCpu   — enable VMX, init VMCS, ASP_VMX_SetupMsrBitmap, setup EPT
4. ASP_VTD_Init                  — Vtd_Initialize, enable DMA remapping, per-device Vtd_EnableVtdForDevice
5. BSP_BootSecondaryCpus         — wake CPU cores 1-3 via INIT-SIPI, AP boot, multi-core sync barrier
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
7. RunInitialTasks — starts all GHS tasks in parallel: VMM1 (primary, Android VM manager),
   Lifecycle, VIP, OTA, plus hardware tasks (Camera, Audio, GPU passthrough, Chimes, Dirana,
   DisplayI2C), security tasks (TEE Keymaster/HW-Crypto/Storage), and Calibrations/Lines.
```

The full enumerated task list and the GHS IPC connection map (`ConnToAndroidVMM`, `ConnToVIP`,
`ConnToTEE_*`, etc.) are `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`'s charter; not re-tabulated here.
For this walkthrough, the only task that matters downstream is **VMM1_InitialTask**, which performs
AVB and launches the Android guest (§7).

### 6.6 GHS Device Interfaces

`/dev/ghs/{textlog,audit,snapshot-dbg,ipc,cal,camera,chime,tee-att,emmc-health,ota-isys,gpu-dbg}`,
SELinux-labeled `ghs_device` (camera: `ghs_camera_device`). Full device/label table:
`GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` §6.7-equivalent.

---

## 7. Phase 4: Android Verified Boot (AVB)

**Duration:** T=500-1500ms
**Task:** VMM1_InitialTask

### 7.1 Check Recovery Mode

```
CheckRecoveryMode():
├── Read BCB (Bootloader Control Block) from misc partition
├── Parse command field:
│   ├── "boot-recovery"    → Recovery mode
│   ├── "boot-see-dealer"  → Dealer mode
│   └── Empty              → Normal boot
└── Determine boot target
```

The full trigger-file/USB-marker mechanics behind these BCB states, and the dealer-recovery write
path, are `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`'s charter — pointer only.

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

**Security note:** A/B metadata uses only CRC32 for integrity, not cryptographic signature — a
genuine weak point ([inferred] impact: see §11.5), not a cryptographic verification gap in vbmeta
itself (§7.3-7.4).

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

`"AVB0"` is the stock upstream `libavb` `AVB_MAGIC` (`vbmeta.img` offset 0 = `41 56 42 30`), not a
GM-custom value — byte-confirmed 2026-09-10. The header is fully upstream (RSA2048/SHA256, `avbtool
1.2.0`, flags=0x00000000 i.e. verification NOT disabled), with zero GM-specific fields. Do not confuse
this with the separate `\0AB0` magic guarding the misc/BCB A/B-slot-metadata structure (§7.2) — two
different magics, two different structures. (The upstream libavb parser's own RE depth — guard
functions, TOCTOU/overflow fuzz targets against `.vmm1` — is `VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`'s
charter.)

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

The Y181→Y177 downgrade-block mechanism (rollback counter vs `vbmeta.rollback_index`, OEM RSA pubkey
extraction) is `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`'s charter — pointer only.

### 7.6 Load and Verify boot Image

```
boot Image Verification:
├── Read boot_a or boot_b from eMMC
│   └── Error: "VMM: A/B: no boot image for slot %s"
├── Parse Android boot image header (kernel/ramdisk offset+size, command line)
├── Verify boot image signature
│   └── Error: "VMM: Error: Android signature verification failed"
├── Hash kernel and ramdisk
└── Compare against vbmeta hash descriptors
```

### 7.7 Configure Android Kernel Command Line

```
Command Line Additions:
├── androidboot.slot_suffix=%s       ← "_a" or "_b"
├── androidboot.verifiedbootstate=%s ← green/yellow/orange/red
├── androidboot.vbmeta.avb_version=1.1
├── androidboot.trustyimpl=-ghs
└── [All ABL parameters passed through]
```

### 7.8 Launch Android Guest VM

```
VM Launch:
├── ASP_VMX_SetGuestKernelAddr — Set kernel entry point
├── Configure guest memory map via EPT
├── Setup virtio devices for guest
├── Initialize guest CPU state
└── ASP_RunGuestVM — Start Android kernel execution
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

The authoritative first-stage mount chain (ACPI SSDT `ANDR0001` static-A/B facts, the emulator-only
fstab patch) is owned by `platform/boot_chain.md` / `platform/partitions_storage.md` — pointer only
(see also Appendix E below for the unique raw evidence kept in this doc).

### 8.3 Key Init Scripts

| Script | Purpose |
|--------|---------|
| `init.bxtp_gm.rc` | Main GM initialization |
| `init.trusty-ghs.rc` | GHS Trusty integration |
| `init.protokey.rc` | ProtoKey security service |
| `init.audio.rc` | Audio subsystem |
| `init.crashlogd.rc` | Crash logging |

### 8.4 GHS Trusty Integration (`init.trusty-ghs.rc`)

```
on early-init
   setprop ro.hardware.gatekeeper trusty
   setprop ro.hardware.keystore trusty
```

### 8.5 ProtoKey Service (`init.protokey.rc`)

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
class core:  vold, apexd, servicemanager, hwservicemanager, watchdogd
class hal:   android.hardware.automotive.vehicle@2.0-service-gm, android.hardware.boot@1.1-service,
             vendor.harman.hardware.ame@1.0-service, camera provider, audio HAL, keymaster@3.0 (Trusty-GHS)
class main:  gmprotokey, GHSCalibrations, gm_update_engine, surfaceflinger, audioserver, bootanimation
```

`vold`/`apexd` both `reboot_on_failure` on crash.

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
│ PHASE 1: VIP (RENESAS RH850) BOOT                            T=0-50ms       │
│   VIP_BOOT → VIP_APP → Read EEPROM → Security Check (§4.5, FULL in all     │
│   builds) → Enable SoC Power                                                │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: INTEL SOC BOOT                                     T=50-200ms      │
│   Intel CSE (ME) → SOC_ABL (kernelflinger) → Load+verify GHS INTEGRITY      │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: GHS INTEGRITY HYPERVISOR                           T=200-500ms     │
│   BSP_Init → VMX_Init → VT-d Init → Boot CPUs 1-3 → Start all GHS tasks      │
│   (VMM1 = primary Android VM manager; Lifecycle/VIP/OTA/Camera/Audio/GPU/   │
│   TEE tasks run alongside)                                                  │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: ANDROID VERIFIED BOOT (AVB)                        T=500-1500ms    │
│   Check BCB → Select A/B slot (misc@0x800, CRC32 only) → Load vbmeta        │
│   (AVB0 magic, RSA-2048/SHA-256) → Verify sig → Check rollback → Load boot  │
│   → Configure cmdline → ASP_RunGuestVM                                     │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: ANDROID AAOS                                       T=1500-15000ms  │
│   Linux Kernel → init (dm-verity rootfs) → gmprotokey/GHSCalibrations/      │
│   gm_update_engine/keymaster@3.0 → Zygote → system_server → CarService →   │
│   HMI Ready                                                                 │
│   GHS monitors Android Sign-of-Health heartbeat; failure → reboot           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Security Boundaries

### 10.1 Security Layer Summary

| Layer | Mechanism | Bypassable? | Notes |
|-------|-----------|-------------|-------|
| **VIP_BOOT** | Harman checksum | Requires RE | Internal RH850 flash |
| **VIP_APP Security** | Function @ 0xb67d0 | Requires RE | Full ~906B in all builds (§4.5) — a `$27`/seed-access validator, not SELinux, not (per the resolved ADB-gate question, see Open Conflicts) the ADB gate itself |
| **EEPROM SBI Flags** | None (no CRC) | Yes (hardware) | I2C accessible — canonical map: `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` |
| **Intel CSE** | Hardware root of trust | No | OTP fuses |
| **SOC_ABL / Boot Guard** | Intel Boot Guard, FPF fuses | FPF fuses confirmed committed and IBB verification confirmed PASS live (2026-11-17); whether a hash mismatch would be *rejected* (Verified profile) vs only measured remains open — MSR 0x13A does not exist on this Apollo Lake core, the live FIT pointer window is closed post-boot, and the top 1 MiB of SPI-NOR (where KM/BPM live) is hardware Protected-Range-blocked (`FLOCKDN`) even with raw controller access. Only a physical SOIC-8 clip read could reach it. Full forensic detail: `platform/elk_recovery.md` §2.3 and `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` — not restated here. |
| **SOC_ABL lock state (`OEMLock`)** | UEFI NV variable, GUID `1ac80a82-4f0c-456b-9a99-debeb431fcc1` | Potentially, if varstore is SPI-backed rather than RPMB (open question) | SOC_ABL is kernelflinger; `USE_TPM` was not compiled in, so the lock is not fTPM/TPM2-backed and not RPMB. Full predicate/fallback detail: `platform/elk_recovery.md` §2.3 (F1). |
| **AVB vbmeta** | RSA-2048/SHA-256 | No | Without signing key |
| **A/B Metadata** | CRC32 only | Potentially | Weak integrity (§11.5) |
| **Rollback Index** | Secure storage | No | Cannot decrement |
| **dm-verity** | Hash tree | Conditional | Active in enforcing |
| **SELinux** | MAC policy | OS-side only | See the single statement below — not VIP/EEPROM-controlled |

**SELinux-enforcing statement (settled; replaces four separate restatements of the same claim):**
No stock build runs permissive. Y175, Y177, and Y181 share a byte-identical init that forces
enforcing; SELinux mode is decided OS-side (init/ramdisk), never by the VIP (`research/security/KERNEL_CVE_ANALYSIS.txt`
Appendix E.8). A previously reported live-permissive Y177 unit was a false finding; both sampled CSMs
ran only stock packages. **History:** corrected 2026-08-25, consistent with the Y177-stub retraction
in §4.5.

### 10.2 VIP Security Control (corrected — no Y177/Y181 divergence)

```
EEPROM Read (0x0440, 0x0A80)
         │
    ┌────┴────┐
    │ SBI=0x00│──→ Request seed from BCM ──→ Validate seed/key ──→ IPC to SoC: "normal mode"
    │(Normal) │
    └─────────┘
    ┌─────────┐
    │ SBI=0xFF│──→ Security function @0xb67d0 (FULL ~906B, same in Y175/Y177/Y181,
    │(Bypass) │    see §4.5) ──→ IPC: seed/auth state to SoC
    └─────────┘
         │
         ▼
SELinux mode decided OS-side (ramdisk/init) — independent of this function and of SBI state.
```

The earlier version of this diagram drew a Y177-vs-Y181 divergent branch under the retracted "stub"
theory; both builds run the identical full function, so there is no divergence to draw.

### 10.3 MEC Counter Behavior

```
[PLC] MEC is %d. Ignoring Hypervisor Startup Timeout
[PLC] MEC is 0. Processing Hypervisor Startup Timeout
```

- **MEC = 0** (normal): VIP monitors GHS startup, resets on failure.
- **MEC ≠ 0**: VIP ignores hypervisor-startup issues for that boot cycle.

Whether a nonzero MEC reading means "bypassed/unlocked" or "production/locked" (and the specific
"207" value sometimes quoted as a bypass marker, `[U]` in this doc) is an open, corpus-wide question
— see `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` and `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`'s own
Open Conflicts sections; not resolved here.

### 10.4 Three Consecutive Reset Behavior

**Distinction verified 2026-11-12:** this section describes VIP reset-timer suppression, not the GHS
lifecycle failed-Android-boot counter. Y181B lifecycle address `0x200E2D` compares that separate
counter with 3 and takes the dealer branch at >=3 — see `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` §2.2.1
for original-SPS provenance and instruction addresses.

```
[PLC] ****There have been 3 Consecutive SoC Startup Failures****
[PLC] ****Hypervisor Startup Timer will not be active for this boot cycle****

[SS_SWC] ****There have been 3 Consecutive SoC-Only resets****
[SS_SWC] ****CSM reset for SoC-Only reset will not be active for this boot cycle****
```

After 3 consecutive failures: hypervisor startup timer disabled, CSM reset disabled, system
continues booting without those two normal checks.

---

## 11. Key Findings

### 11.1 Dual-Processor Architecture

Two independent processors: VIP (always-on MCU; power, CAN, security) and Intel Atom x7-A3960 (GHS
hypervisor + Android guest). VIP boots first and controls SoC power sequencing.

### 11.2 VIP Does Not Control SELinux Posture

See §10.1's settled SELinux-enforcing statement and §4.5's Y177-stub-retraction History. In short:
the VIP security function is a full validator in every build and contains no SELinux logic; SELinux
mode is an OS-side property.

### 11.3 GHS Hypervisor is Mandatory

Android runs as a guest VM under GHS INTEGRITY: VMX (VT-x) virtualization, VT-d (IOMMU) device
isolation, EPT memory management. Cannot bypass GHS to run modified Android.

### 11.4 AVB Enforced by GHS

Implemented in the GHS VMM1 task: vbmeta signature verification (RSA-2048), boot-image hash
verification, rollback-index checking. Cannot bypass without signing keys.

### 11.5 A/B Metadata Uses Only CRC32

No cryptographic signature on the A/B slot metadata in `misc`. `[inferred]`: a potential
manipulation vector for forcing slot switching or boot failures — not demonstrated in this doc.

### 11.6 MEC Counter Affects Behavior

When MEC ≠ 0, VIP ignores the hypervisor startup timeout. `[inferred]`/`[U]`: whether this "may allow
modified boot paths" is unverified in this doc — see §10.3's pointer to the corpus-wide MEC-semantics
open conflict.

### 11.7 Failure Recovery Mode

After 3 consecutive boot failures: hypervisor timer disabled, CSM reset disabled, boot continues
without those normal validation checks (§10.4).

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

File hashes (SHA-256/MD5) for all of the above: `BOOT_CHAIN_ANALYSIS.txt` — not restated here except
the one comparison load-bearing for §4.5 (Appendix D.4).

### Documentation Files Consulted

| Path | Content |
|------|---------|
| `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` | GHS hypervisor analysis |
| `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` | Boot/recovery flow |
| `VIP_CONTROL_ANALYSIS.txt` | VIP boot control research |
| `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` | Y177 vs Y181 differences (carried unchanged) |
| `gm_pi/06_PROTOCOL_DECODER.md` | Hardware architecture (no longer locatable in the current corpus as of this consolidation pass; row kept for provenance) |

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

Estimates; no independent timing-trace source stated.

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

**Correction (2026-09, kernel `.config` extraction):** this HDLC/IPC framing is the VIP↔SoC link at
the GHS-task level above; on the Android guest side there is **no `N_HDLC` line discipline in the
kernel at all** — the guest never owns `/dev/ttyS1` as a kernel HDLC device. The link surfaces to
Android guest userspace only, via `IPCServer` fanning the channel into per-channel Unix sockets
(`/vendor/etc/ipc4.cfg`) that `libipc.so` clients (VHAL, powermode, rtcd, gmlocation) connect to. Full
wire-format confirmation: `platform/boot_chain.md` and `platform/emulator.md` (Un-stub roadmap).

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

Full channel enumeration: `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`.

---

## Appendix D: Binary Evidence (pointer)

The byte-level proof underlying this walkthrough — file hashes, hex dumps, string offsets with
addresses, full `cmp -l` diff counts, init-script captures, reproduction commands — lives in
`BOOT_CHAIN_ANALYSIS.txt`, this doc's designated raw-forensic-evidence companion (see header). It is
not duplicated here. The one exception is the direct evidence for this doc's own headline
finding, §4.5's stub retraction:

**Critical region @ 0xb67ce (security function), Y177 vs Y181, byte-for-byte:**

```
Y177 (86283151): 000b67ce: ff30 0052 7f00 8807 e3ff 06c8 9900 033d  .0.R...........=
Y181 (86331656): 000b67ce: 7f00 8807 e3ff 06c8 9900 033d 0545 074d  ...........=.E.M
```

The shared function bytes `7f 00 88 07 e3 ff …` appear at `0xb67ce` in Y181 but at `0xb67d2` in
Y177; the leading `ff 30 00 52` in Y177 is the tail of the *preceding* function, not a return stub
(§4.5).

Also note, for the record: SOC_HOSTOS (85098662) and SOC_ABL (85738845) are MD5-identical between
the Y177 and Y181 update packages; only VIP_APP (86283151 vs 86331656) differs. SHA-256:
Y181/85098662 (SOC_HOSTOS/GHS) `317ae85ccf759476755411e66593dde9f879a43732cd342b4e101e4026535ed3`;
Y181/85738845 (SOC_ABL) `77b866c6492aa0e8fd2aab8d986182bdef597820a63e0d688a06a12a67f4aed8`;
Y181/86331656 (VIP_APP) `dbdbb9da3dc14f93e37b94c0e1c5a42921c46fc6e89911159872a6e9e0f87acc`. The
MD5 trio proving GHS/ABL identity Y177<->Y181, VIP_APP differing: `ded73e3f9026fc8f802bd7485837fc45`
(85098662, both builds, identical), `61efd392e75660c3eafa92b01be8ed7b` (85738845, both builds,
identical), and VIP_APP `680b0e61aa6c39a28badbd73e5356af2` (Y177/86283151) vs
`e47928d9f409834083abc9a068ce65e0` (Y181/86331656, different). This doc's own designated
raw-evidence companion, `BOOT_CHAIN_ANALYSIS.txt`, does not actually carry this hash table
despite Appendix D's pointer above claiming it does — kept here instead until that gap is
closed. This confirms the build-to-build difference is confined to VIP_APP — it does **not**
mean "the security difference
between Y177 and Y181 is entirely in the VIP firmware" in the sense of a disabled check; per §4.5,
there is no VIP-side security difference between these builds beyond the 15-18 recompiled-source
bytes.

---

## Appendix E: Kernel Configuration + GHS Coupling

Extracted from the real Y181B boot image, cross-checked byte-identical against the live device's own
`.config`. **Most of this material is already stated verbatim in `platform/emulator.md`'s kernel
characterization and `platform/boot_chain.md` — only the facts unique to this research tier (raw
boot-image/kernel-identity evidence) are kept below; everything else is a pointer.**

### E.1 Boot Image (unique)

Android boot header v2, page size 2048. Kernel: x86_64 bzImage, 15,364,688 bytes, LZ4-compressed
vmlinux, load addr `0x10008000`. Ramdisk: 20,984,589 bytes, LZ4-legacy, load `0x11000000`. A "second"
8061-byte blob is an Intel NHLT audio-DSP ACPI table wrapper, not boot code. `dtb` size 0 (no device
tree — pure ACPI).

### E.2 Kernel Identity (unique)

`Linux version 4.19.305-240125T145315Z-gf1edde901aa7 ... SMP PREEMPT ... Tue Jul 22 07:52:16 EDT
2025`, clang 12.0.7 (Android r416183b1), x86_64, SMP, `NR_CPUS=32`, `HZ=1000`, X2APIC, KASLR on.
Android Common Kernel 4.19 base, heavily GM/Intel-patched (GHS drivers, Titan/Broxton Apollo Lake
program, IPU4 camera, Trusty TEE).

### E.3 GHS Coupling, Platform, Storage, virtio, Cmdline, First-Stage Mount (pointer)

`CONFIG_PARAVIRT` off / no pv-ops contract, the `ghs_comms` PCI driver (vendor `0x1B95`, device
`0xA000`) and its sibling GHS-coupled drivers, the Apollo-Lake platform config, the narrow
virtio-pci-legacy-only storage/console posture (no `VIRTIO_MMIO`/`VIRTIO_NET`, hence incompatible with
goldfish/ranchu), the full boot cmdline (base `enforcing=0 androidboot.selinux=permissive` tokens
followed by a later `enforcing=1 androidboot.selinux=enforcing` pair that wins), and the ACPI SSDT
(`ANDR0001`)/static-A/B first-stage-mount chain are all stated in full in `platform/emulator.md` and
`platform/boot_chain.md` — not restated here to avoid a fourth copy of material that already lives in
two platform docs.

---

## Appendix F: QEMU Portability — Dependency Classification

**Current status and milestone narrative (real GM kernel boots autonomously to a themed AAOS home
screen on plain `qemu-system-x86_64`/q35) is owned by `platform/emulator.md`** — read that doc for the
live state, the native-VHAL/no-shim-needed finding, and the software-rendering graphics stack that
replaced the originally-anticipated drm_hwcomposer retargeting. Not restated here.

The one table `platform/emulator.md` itself points back into this doc for (its own text: "see
`research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md` Appendix G for the full per-dependency portability
table") is kept below as the sole surviving unique content of the former Appendix G:

### F.1 Per-Dependency Classification

(providable = QEMU supplies it natively; patchable = needs a cmdline/config/ACPI tweak; stubbable =
needs a software shim; hard-blocker = genuinely absent, stays dead)

| Dependency | Class | Notes |
|---|---|---|
| CPU/entry/ACPI-fstab/storage(virtio-blk)/console/e1000e-networking/AVB | Providable/patchable | q35+virtio-pci+ACPI-SSDT-injection, no kernel source changes |
| Display (i915 expects real Gen9 GPU) | Stubbable / GPU-accelerable | `DRM_BOCHS` software path; superseded by a hardware-accelerated virtio-gpu build — see `platform/emulator.md` |
| VIP/IPC (ttyS1 userspace protocol) | Stubbable | reuses `libipc_shim.c`/frame-injection tooling verbatim — kernel-agnostic; superseded by the native IPCServer finding, see `platform/emulator.md` |
| GHS transport itself (`ghs_comms` PCI device, `/dev/ghs/*`) | Stubbable/absent | driver never binds; no panic |
| A/B boot-control (`GHS_VMM_BOOTLOADER_CONTROL`) | Stubbable | `androidboot.slot_suffix` on cmdline + a static/software `IBootControl` HAL |
| Hardware keymaster/attestation/RPMB (Trusty TEE, requires GHS) | Hard blocker | permanent — same as today's software-keymaster stub, no regression |
| Harman AVB audio (802.1BA + NXP TDF8532 codec) | Hard blocker | permanent — same as today's Google `audio@6.0` stub, no regression |
| GHS cal/chime/camera/emmc-health overlay tasks | Stubbable/absent | same posture as today |

Effort estimate, two-strategy comparison, and payoff framing (formerly G.1/G.3) are historical
planning notes fully resolved by the completed milestone above — not reproduced here.

---

## Open Conflicts

Per-doc-local contradictions found in this research tier that no dated correction settles, plus the
one corpus-wide item this doc is required to carry (PLAN item 2):

1. **`cal_startup_fault_timeout_sec`: 6000ms vs 15 (sec) — UNRESOLVED.** §3's PLC-timer table lists
   this variable at 6000ms; §4.8's "Key Calibration Values" table lists the same variable at 15,
   under a column implicitly in seconds given the variable's own `_sec` suffix and the surrounding
   rows (`cal_background_sleep_timeout_sec`=10, `cal_sleep_fault_timeout_sec`=900, both genuinely in
   seconds). No dated correction in this doc, or any cited source, addresses the discrepancy — it may
   be a units mismatch (6000ms = 6s ≠ 15s) or two genuinely different cal tables sampled from
   different units/builds. Not resolved here; both values kept, flagged at both table rows above.

2. **VIP-vs-SoC-side ADB gate — resolved by the later of two same-corpus dated corrections, applied
   above (§4.5, §10.1).** §4.5/§11.2 (dated 2026-08-25) state the VIP function + EEPROM SBI
   (0x0440/0x0A80) "actually gate... ADB/seed auth (CAN-confirmed)." §10.1's security-layer table
   (dated 2026-08-26, one day later) states the opposite for the same function: "NOT... the ADB gate
   (CORRECTED 2026-08-26: the ADB unlock is SoC-side MEC/`is_secure_mode` via DID 0xF1A0 — see
   EEPROM_LAYOUT §0.9/§0.10)." Per the latest-dated-correction rule, the 2026-08-26 reading governs:
   the VIP function is a `$27`/seed-access validator; the ADB-unlock decision itself is SoC-side
   (MEC/`is_secure_mode` via DID 0xF1A0), owned by `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` /
   `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`. §4.5 and §10.1 above reflect this resolution; listed here
   only so the superseded 08-25 phrasing isn't silently lost.

3. **Module 72 naming: "SOC_ABL" vs "SOC_BOOT" (PLAN corpus-wide item 2).** This doc's own §4.2 (the
   2026-11-12 live-`moduleinfo` correction block) reads module slot 72 / part 85738845 from the live
   Y181B unit and labels it only by its numeric version (`2344`), following that read's own "SoC boot"
   framing; §5.2 of this same doc calls the identical file (85738845) "SOC_ABL" (the DPS/manifest-role
   name used throughout this doc and `BOOT_CHAIN_ANALYSIS.txt`). No dated correction in this corpus
   reconciles "SOC_ABL" (manifest/DPS-role naming) against "SOC_BOOT" (the name the live radio itself
   reports for the same part, per the retired `UPDATE_PROCESS_ANALYSIS.txt`'s 2026-11-12
   live-moduleinfo correction). Routed to `platform/ota_programming_roles.md`'s Open Conflicts as well,
   per PLAN.

---

**Related documents:** `BOOT_CHAIN_ANALYSIS.txt` (raw forensic evidence companion),
`VIP_FIRMWARE_Y177_Y181_COMPARISON.md` (carried unchanged), `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`,
`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`, `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`,
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`, `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`,
`VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`, `VIP_CONTROL_ANALYSIS.txt`, `platform/boot_chain.md`,
`platform/emulator.md`, `platform/elk_recovery.md`, `platform/firmware_versions.md`,
`platform/security.md`.
