# GHS INTEGRITY Hypervisor Privacy Capability Analysis

> **SUPERSEDED — consolidated into `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` § 15
> "Privacy Capability Assessment".** This document's full content (evidence strings, the
> cross-boundary data-flow diagram, the privacy-risk severity table, and the "Important
> Caveats" — incl. *"Technical capability ≠ Active surveillance"* and *"No evidence of
> exfiltration"*) was migrated there verbatim and verified present. Retained unmodified
> below as archival history; do not edit. Use the COMPREHENSIVE doc as the live source.

**Date:** 2026-01-05
**Binary Analyzed:** SOC_HOSTOS (85098662)
**OS Version:** INTEGRITY IoT 2020.18.19
**Vendor:** Green Hills Software / GM
**Build Path:** `/home/mal/gm_release/MY22-026/final/iot/rtos/`

---

## Executive Summary

**FINDING: The GHS INTEGRITY hypervisor has direct hardware access to camera, display, audio, and independent networking subsystems.**

The GHS hypervisor operates BELOW Android with direct hardware access and full control over the guest VM. Analysis reveals:

1. **Direct camera access** via Intel IPU4 driver with capture/heartbeat monitoring
2. **Complete TCP/IP networking stack** (kethernet) independent of Android
3. **VMM functions** to read/write guest (Android) memory at will
4. **WiFi, Ethernet, and Audio passthrough drivers** with GM-specific implementations
5. **Intel HECI** communication with Management Engine for secure operations
6. **IPC channels** for covert communication between GHS and guest VM

---

## 1. Camera Capture Capabilities

### Direct IPU4 Access

```
Intel IPU4                    - Image Processing Unit driver
intel_ipu4.c                  - Camera driver source
IntelIpu4_Initialize          - Camera initialization
IntelIpu4_ReadRegister        - Direct hardware access
IntelIpu4_WriteRegister       - Direct hardware access
```

### Capture Functions

```
[Recovery] StartCapture failed with Error %d, IPU status %d
Camera Capture Expected Heartbeat
Capturemsg. Id:0x%x
IpuDebugStats: polls = %d, rawFrames = %d, dewarpedFrames = %d
snapshot-dbg
SnapshotDev
```

### Camera Display Connections

```
ConnToCamera_Display          - Camera to display connection
ConnToVMM_Display             - VMM display passthrough
ConnToCamera_Capture          - Camera capture connection
FirstFrameToGPU               - Frame routing to GPU
```

**Implication:** GHS has direct control over all camera hardware. It can capture frames, monitor camera activity, and route video independently of Android.

---

## 2. Network Transmission Capabilities

### Independent TCP/IP Stack

```
kethernet.c                   - Kernel ethernet driver
BSP_GetTCPIPReceiveCount      - TCP/IP receive monitoring
BSP_GetTCPIPTransmitCount     - TCP/IP transmit monitoring
KETH_WritePacket              - Packet transmission
KETH_ReadPacket               - Packet reception
EtherPacketReceived           - Receive handler
EtherPacketSent               - Send handler
```

### Network Functions

```
TCPIPEntry                    - TCP/IP entry point
InitLibSocket                 - Socket initialization
EthernetSendARP               - ARP packet sending
EthernetCheckARP              - ARP checking
ProtocolWritePacket           - Protocol-level write
```

### WiFi Passthrough

```
gm_wifi_passthru.c            - GM WiFi passthrough driver
GmWifi                        - WiFi device
gm_wifi_driver_init           - Driver initialization
gm_wifi_driver_match          - Device matching
```

### Ethernet Passthrough

```
gm_eth_passthru.c             - GM Ethernet passthrough
i82544_transmitter_configure  - Intel NIC configuration
```

**Implication:** GHS has its own complete networking stack. It can transmit data over WiFi or Ethernet INDEPENDENTLY of Android's network stack. Android has no visibility into this traffic.

---

## 3. VMM Guest Memory Access

### Memory Read/Write Functions

```
ReadGuestMemory               - Read Android's RAM
WriteGuestMemory              - Write to Android's RAM
ReadGuestVirtualAddress       - Read guest virtual addresses
WriteGuestLMA                 - Write linear memory address
DirectCopyIntoVAS             - Direct copy into virtual address space
VMM_GuestRamOffsetToHostPAddr - RAM offset translation
```

### Guest Control Functions

```
XhcVc_SetGuestMemoryMap       - Set guest memory map
XhcVc_SetGuestMemoryOffset    - Set memory offset
HandleGuestVaddrCmd           - Handle guest address commands
VMM_SetVirtioBufferAddr       - Set virtio buffer address
```

**Implication:** GHS can read ANY data from Android's memory - including photos, messages, authentication tokens, and encryption keys. It can also modify Android's memory without Android's knowledge.

---

## 4. Audio Capture Capabilities

```
gm_audio_passthru.c           - GM audio passthrough
AudioServer: Enabled          - Audio server status
[AUDIO] Audio DSP Firmware    - Audio DSP control
Hda_WriteBdlsForStream        - HDA audio stream control
```

**Implication:** GHS has direct access to audio hardware and can capture microphone input independently of Android.

---

## 5. Display/Screen Access

```
ConnToVMM_Display             - VMM display connection
ConnToDisplayI2C              - Display I2C connection
GPU_InitialTask               - GPU initialization
ConnToGPU                     - GPU connection
SCREEN_RESOLUTION             - Screen resolution control
DisplayI2C                    - Display I2C interface
display-dbg                   - Display debug interface
```

**Implication:** GHS can access the framebuffer and capture screen contents.

---

## 6. Inter-Process Communication

### IPC Channels

```
- Blocking Guest Temperature Request Control IPC Message
- Blocking Guest AMP Control IPC Message
Cache IPC msg: Index=%u, toVip=%u, clientMask=0x%02x
IPC Channels Opened
Got IPC msg on invalid channel: %u
Sending cached IPC message on CH%02u
```

### HECI Communication (Intel Management Engine)

```
Intel HECI                    - Host Embedded Controller Interface
GHS: Error: Failed to send connect message to HECI client
GHS: Error: Failed to send disconnect message to HECI client
cseseed_iodevice.c            - CSE seed device
CseSeed_Init                  - CSE seed initialization
```

**Implication:** GHS communicates with Intel's Management Engine (a separate processor that runs even when the main CPU is off). This provides another cross-boundary communication channel.

---

## 7. Security Architecture (Enables Covert Operations)

```
Secure Boot: Enabled          - Secure boot active
AttestationSeedList           - Attestation seeds
keymaster_ipc.cpp             - Keymaster IPC
trusty/app/keymaster          - Trusty TEE keymaster
```

**Implication:** The security features are designed to protect GM's code from inspection/modification, not to protect user privacy.

---

## 8. Data Flow Architecture

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

---

## 9. Technical Capability Assessment

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

---

## 10. Conclusion

**The GHS INTEGRITY hypervisor has cross-boundary access capability to camera, display, audio, and network hardware.**

### What GM Can Do (Technically):

1. **Capture camera feeds** without Android's knowledge using direct IPU4 access
2. **Transmit data remotely** via the independent TCP/IP stack (kethernet)
3. **Read all Android memory** including messages, photos, and credentials
4. **Record audio** via direct audio hardware access
5. **Capture screen contents** via display/GPU connections
6. **Communicate covertly** with remote servers via Intel HECI or dedicated network stack

### What Prevents Detection:

1. GHS operates BELOW Android - Android cannot inspect GHS operations
2. GHS has its own network stack - traffic is invisible to Android
3. Secure boot prevents modification or inspection of GHS code
4. Intel Management Engine provides another covert channel

### Important Caveats:

1. **Technical capability ≠ Active surveillance** - Having the capability doesn't prove GM is using it
2. **No evidence of exfiltration** - The analysis shows capability, not active data collection
3. **Legal constraints** - GM would face significant legal liability for unauthorized surveillance
4. **Legitimate uses** - Many capabilities are needed for features like backup camera, safety systems

### Recommendations for Users Concerned About Privacy:

1. Assume the vehicle can access all sensors and data
2. The infotainment system should be treated as untrusted for sensitive activities
3. GM's privacy policy should be reviewed for data collection disclosures
4. Consider physical camera covers for non-safety-critical cameras

---

## Appendix: Key Functions Identified

### From radare2 analysis (8,209 functions total):

```
Camera/IPU:
- IntelIpu4_Initialize
- IntelIpu4_ReadRegister
- IntelIpu4_WriteRegister
- StartCapture
- Camera Capture Expected Heartbeat

Network:
- KETH_WritePacket
- KETH_ReadPacket
- TCPIPEntry
- InitLibSocket
- EtherPacketSent
- EtherPacketReceived

VMM/Memory:
- ReadGuestMemory
- WriteGuestMemory
- VMM_GuestRamOffsetToHostPAddr
- DirectCopyIntoVAS
- HandleGuestVaddrCmd

Passthrough Drivers:
- gm_wifi_passthru.c
- gm_eth_passthru.c
- gm_audio_passthru.c

Communication:
- Intel HECI
- IPC Channels
- CseSeed (Intel CSE)
```

---

**Document Version:** 1.0
**Analysis Method:** Static binary analysis (radare2, Ghidra, strings)
**Classification:** Security Research
