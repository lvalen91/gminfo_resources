# GHS INTEGRITY Hypervisor - Comprehensive Analysis

**Date:** 2026-01-05
**Binary:** SOC_HOSTOS (85098662)
**Size:** 14,929,320 bytes (extracted ELF)
**Format:** ELF 32-bit LSB executable, Intel 80386, statically linked, stripped

> Companion doc: `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` covers boot/update/recovery
> mechanics in depth (BCB/misc byte layout, USB/protokey/capsule trigger files,
> See-Dealer/ELK/Diagnostic boot modes, Lifecycle SoH handshake) — complementary to this
> RE inventory. The former `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` is consolidated here in §15.

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

### Boot Sequence

```
1. Hardware Reset
        │
        ▼
2. Intel ABL (Automotive Bootloader)
   └── Loads GHS INTEGRITY
        │
        ▼
3. GHS Kernel Initialization
   ├── BSP_InitializeOnBootCpu
   ├── ASP_PreCrtInitializeBootstrap
   ├── ASP_VMX_InitializeOnBootCpu
   ├── ASP_VTD_Init (IOMMU)
   ├── BSP_Initialize
   ├── BSP_BootSecondaryCpus
   └── RunInitialTasks
        │
        ▼
4. GHS Tasks Start
   ├── VMM1_InitialTask (Android VMM)
   ├── Camera_InitialTask
   ├── Audio_InitialTask
   ├── GPU_InitialTask
   ├── Chimes_InitialTask
   ├── VIP_InitialTask
   ├── Lifecycle_InitialTask
   ├── OTA_InitialTask
   └── [Other tasks...]
        │
        ▼
5. Android Boot
   ├── CheckRecoveryMode()
   ├── Read A/B slot from misc partition
   ├── Load vbmeta partition
   ├── VERIFY vbmeta signature
   ├── Load boot partition
   ├── VERIFY boot image
   ├── Check rollback index
   └── Launch Android kernel
```

### Boot Configuration Strings

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

### Android Verified Boot (AVB)

GHS implements full AVB verification:

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
├── ABL.secureboot=1
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

### Guest Memory Management

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

### GHS Controls

```
1. A/B Slot Management
   - Reads misc partition for BCB
   - Manages slot switching
   - Tracks boot attempts

2. Verified Boot
   - Validates vbmeta signature
   - Verifies boot image
   - Checks rollback counter

3. Recovery Mode
   - CheckRecoveryMode()
   - "boot-recovery" command
   - BCB parsing

4. OTA Interface
   - /dev/ghs/ota-isys
   - ConnToOTA connections
   - OTA_InitialTask
```

### Error Conditions

```
- "VMM: A/B Boot: ERROR: no valid boot slot"
- "VMM: ERROR: failed to read A/B metadata from 'misc'"
- "VMM: ERROR: both A/B and singleton boot partition found!"
- "VMM: Failed to load Android from %s (recovery = %d)"
- "VMM: I/O error loading boot slot: %d"
- "VMM: A/B Boot: No more remaining attempts for slot %d"
```

---

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

> Consolidated **verbatim** from the former standalone document
> `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` (now archived/superseded). §13 above carried the
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
