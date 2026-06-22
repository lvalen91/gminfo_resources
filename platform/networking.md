# GM Info 3.7 Network Architecture

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

## Network Interfaces

| Interface | Purpose | Address |
|-----------|---------|---------|
| eth0 | Intel I211 physical (gPTP master, 1Gbps) | 192.168.1.100/24 (Y181, same as vlan5); Y175 has no IPv4 on eth0 |
| vlan4 | VIP-SoC IPC | 172.16.4.x |
| vlan5 | Vehicle network (NFSA) | 192.168.1.100 (IHU) |
| br0 | WiFi hotspot bridge (wlan1+wlan2 bridged, hostapd_bcm+dnsmasq) | — |
| wlan0-2 | Broadcom WiFi (AP/STA/P2P) | — |
| wlan1 | WiFi hotspot for CPC200 | ssid=myChevrolet 32D4 |

**MAC address:** eth0 always `02:04:00:00:01:00` (locally administered, OUI bit set).
**Net hostname:** `myChevrolet`

---

## Ethernet VLAN Detail

Broadcom BCM8953x managed switch. Switch port assignments:

> **⚠ Switch-vendor discrepancy (unresolved).** This doc records a Broadcom
> BCM8953x, but the firmware module inventory reports `ETHERNET_SWITCH` part
> `85759612.AA` = **`MVL88Q5050_globalB_…`** — `MVL` = **Marvell 88Q5050**
> (an automotive 1000BASE-T1 switch). Either the unit has two switch stages
> (e.g. a Broadcom host NIC/PHY + a Marvell backbone switch), or one of these
> attributions is wrong. Flagged, not resolved — the firmware string is from the
> `dumpsys UpdateService pn version` inventory; the BCM8953x label predates it.

| Port | Connected Node |
|------|---------------|
| 0 | RSI |
| 1 | AMP |
| 2 | CGM |
| 3 | TCP |
| 5 | Host (A11/IHU) |

### VLAN 5 — Vehicle LAN (192.168.1.x/24)

| Address | Node |
|---------|------|
| 192.168.1.100 | CSM / IHU |
| 192.168.1.101 | ADB |
| 192.168.1.102 | TCP_ETH |
| 192.168.1.103 | AMP_ETH |
| 192.168.1.106 | IPC |
| 192.168.1.107 | CGM Host |
| 192.168.1.112 | CGM_ETH |

### VLAN 4 — VCS / EOCM Network (172.16.4.x/24)

| Address | Node | Notes |
|---------|------|-------|
| 172.16.4.100 | VCU_AGVM / Android (vlan4 face) | this device |
| 172.16.4.14 | **ACP (Application Control Processor)** | permanent ARP, no ping — hypervisor/control partition |
| 172.16.4.107 | RTOS partition | active, TTL=255; symmetric 49156↔49156 to diagnosticsd |
| 172.16.4.112 | CGM_OTA (vlan4 face) | active, TTL=64 (Bosch JuP1, Linux) |
| 172.16.4.12 | EOCM_HCP_SECONDARY / EOCM_HCP_2 | code-referenced |
| 172.16.4.13 | EOCM_HCB | code-referenced |
| 172.16.4.15 | EOCM_HCP_HOST / EOCM_HCP_1 | code-referenced |
| 172.16.4.1, .104, .110 | additional vlan4 ECUs | code-referenced, not live on bench |

> **Partition identity — canonical source.** The authoritative partition map is
> the FSA **DeviceInformation** service (serviceId 1001), whose `instanceId`
> field enumerates: 1=CSM(.100), 2=TCP(.102), 3=AMP(.103), 4=RSI1(.104),
> 5=RSI2(.105), 6=IPC(.106), 7=CGM(.112), 8=LOWRADIO(.108); PDR=.110. See
> [`platform/fsa_protocol.md`](fsa_protocol.md). The VLAN-5 switch-port table
> above (`.101 ADB`, `.107 CGM Host`) reflects the switch/host view; the
> DeviceInformation map reflects the service-addressable partitions — both are
> retained as observed.
>
> **Code-referenced VCU-variant subnets** (unreachable on bench, 100% loss):
> `192.168.118.1`=VCU_AGVM, `192.168.118.2`=IPC; `172.16.5.x` (new in VCU
> variant). See [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)
> for the VCU/CIP inter-VM topology.

---

## Listening Ports

| Bind Address | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| 0.0.0.0 / 127.0.0.1 | 6363 | TCP | **AVB audio daemon** (uid=1041 audioserver) — init-owned listen socket, text IPC bus for AVB audio routing; arbitrary data → `"ERROR"`. Low value. (Was "Unknown".) |
| 0.0.0.0 | 7000 | TCP | **AirPlay/AirTunes 320.17.8** (Cinemo `libNmeCarPlay` r14), br0/192.168.5.1, uid=1001000. `GET /` → `404; Server: AirTunes/320.17.8`. CarPlay audio bridge — see [`audio/carplay_audio_pipeline.md`](../audio/carplay_audio_pipeline.md). (Was mislabeled "ADB"; ADB is port 5555.) |
| 0.0.0.0 | 49156 | TCP | **diagnosticsd UDS-over-TCP bridge** (root, PID 599). Bridges GM Ethernet Diagnostics to RTOS `172.16.4.107:49156`. See [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md). (Was "Unknown".) |
| 192.168.1.100 | 9002 | TCP | GHS hypervisor bridge service (IPv6-mapped IPv4) |
| 192.168.1.100 | 9010 | TCP | GHS hypervisor bridge service (IPv6-mapped IPv4) |
| 192.168.1.100 | 9016 | TCP | GHS hypervisor bridge service (IPv6-mapped IPv4) |
| 127.0.0.1 / 192.168.5.1 | 53 | TCP/UDP | dnsmasq (loopback + br0 WiFi-AP side) |

> **Re-verified against live `enumeration/Y181/jun2026/` capture.** 9002/9010/9016 listen bound to the IHU's own **192.168.1.100** (IPv6-mapped IPv4), *not* 192.168.1.1 — the guest has no `.1` interface or route. **7000 (ADB) is listening** (`0.0.0.0:7000` + `*:7000`), and **9010 is a listener**, not outbound-only. DNS (dnsmasq, TCP/UDP 53) is served locally on **127.0.0.1** and **192.168.5.1 (br0, the WiFi-AP bridge)**.
>
> The earlier apr2026 note (only 9002/9016 @ .1; 9010 outbound; 7000 gone; DNS on .102) reflected one snapshot and is **withdrawn** — listener set varies with projection-session state; the Jun-2026 live set above supersedes it.

---

## VIP-SoC IPC

- **Transport:** HDLC over UART `/dev/ttyS1`
- **Channels:** 20 IPC channels (numbered 0-20)
- **Protocol:** Version 16
- **Baud:** 4104
- **PLC:** Programmable Logic Controller timers in VIP
- **MEC:** Mode/Event/Condition behavior framework

### IPC Channel Assignments

| Channels | Assignment |
|----------|-----------|
| 1-2 | PROTOKEY / Security |
| 3-5 | J6_CDD Diagnostics |
| 6-8 | PLC |
| 9-12 | Calibration |
| 13-16 | System state |
| 17-20 | Reserved |

The VIP MCU communicates with the Intel SoC via a dedicated UART link using HDLC framing. The 20 IPC channels carry power management commands, CAN messages, calibration data, and vehicle state information between the two processors.

---

## UART Devices

| Device | Owner | Purpose |
|--------|-------|---------|
| /dev/ttyACM1 | crw-rw-rw- | MCP2200 (world-writable debug) |
| /dev/ttyS0 | bluetooth:bluetooth | Bluetooth HCI |
| /dev/ttyS1 | root:root | VIP IPC (HDLC) |
| /dev/ttyS2 | root:root | — |
| /dev/ttyS3 | root:root | — |

---

## USB Identifiers

| Device | VID | PID | Notes |
|--------|-----|-----|-------|
| GM IHU (iAP) | 0x2996 | 0x0120 | iAP2 USB role |
| **Aptiv H2H (Head-to-Head) Bridge** | 0x2996 | 0x0105 | Cross-ECU USB bridge (CSM↔other ECU); kernel driver **`dabridge`** (GM custom); controlled via `/sys/bus/usb/drivers/dabridge/bridgeport`; `RDMSADBHandler` writes `1-6.3` here on ADB_Enable. (= the "GM proprietary" 0x0105 entry.) |
| **GM V10 E2 PD USB Hub** | 0x2996 | 0x0132 | USB hub; its presence **blocks** `RDMSADBHandler.ADB_Disable` (peripheral→host role reversal fails, ADB recovers). (= the "USB hub" 0x0132 entry.) |
| CPC200 adapter | 0x1314 | 0x1521 | manufacturer="Magic Communication Tec.", product="Auto Box" |
| dabr_udc | — | — | USB device controller for gadget mode |

VID `0x2996` (decimal 10646) = **Aptiv / Delphi Technologies**. The H2H bridge +
PD hub + `RDMSADBHandler` Binder service (#66) form the ADB-over-H2H routing
path — see [`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md).

### USB Gadget

- **Controller:** `sys.usb.controller=dabr_udc.0`
- **Kernel:** `CONFIG_USB_GADGET=y`
- **FunctionFS endpoints:** iAPClient, adb, mtp, ptp

The `dabr_udc.0` device controller supports USB gadget mode via FunctionFS. The kernel has `CONFIG_USB_GADGET=y` and exposes functionfs endpoints for iAPClient (iAP2 accessory role), adb, mtp, and ptp.

---

## NFSA / FSA (Feature Service Architecture)

> **Full protocol spec:** [`platform/fsa_protocol.md`](fsa_protocol.md) — wire
> format (20-byte BE header, magic `0x5AA5`, protobuf payload), opTypes,
> functionIDs, the connection handshake, the complete **service catalog** (port
> → serviceId → partition), recovered protobuf field tables, and live service
> sessions (RemoteModuleHMI, NetworkAccessManager, DeviceInformation,
> DisplaysCoordination). GM's code names this `com.gm.fsa.service` / `com.gm.nfsa.*`
> — "NFSA" here and "FSA" there are the same protocol.

NFSA/FSA provides the vehicle-internal network communication layer between the IHU and other vehicle computing nodes over VLAN 5. The IHU participates as both server and client across 6 ports:

### IHU as Server (listening)

| Bind Address | Port |
|-------------|------|
| 192.168.1.100 | 9002 |
| 192.168.1.100 | 9010 |
| 192.168.1.100 | 9016 |

### IHU as Client (connects to)

| Remote Address | Port |
|---------------|------|
| 192.168.1.102 | 9005 |
| 192.168.1.102 | 9012 |
| 192.168.1.102 | 9018 |

---

## GM Cloud Endpoints

| Endpoint | Port | Purpose |
|----------|------|---------|
| vtmpub.oboservices.mobi | 443 | OTA / OMA-DM updates |
| vehicle.api.gm.com | 443 | Vehicle registration |
| vehicle.api.gm.com | 20445 | Security logging |
| vehicle.api.gm.com | 20647 | Auth / personalization |

Telematics (CGM module) operates independently of the A11 radio stack — cloud connectivity does not depend on the IHU's WiFi or cellular state.

### Update Libraries

| Library | Purpose |
|---------|---------|
| libpal_swupdate_ecu.so | ECU software update PAL |
| libpal_swupdate_hostos.so | HostOS software update PAL |
| vendor.gm.swupdate@1.0.so | GM SWUpdate HIDL service |

---

## GM Service Architecture

| Service | Details |
|---------|---------|
| Power mode | State machine: Run, Accessory, Crank, Off — managed by VIP MCU |
| License/calibration | GHS cal service, DPS AES-CMAC with server key provisioning |
| IPC | 20 channels on /dev/ttyS1, HDLC protocol v16, baud 4104 |

---

## CAN Bus

- **ECU count:** 24
- **CSM address:** 0x80
- **Gateway:** VIP MCU (RH850/P1M-E) acts as CAN gateway between vehicle bus and SoC

The VIP MCU bridges CAN messages to the Intel SoC over the HDLC IPC link, translating vehicle bus traffic into structured IPC messages for Android services. The CSM (Chassis System Module) at address 0x80 is the primary audio amplifier endpoint connected via Ethernet AVB.

---

## WiFi Configuration

The Broadcom BCM WiFi module supports three concurrent interfaces:

| Interface | Mode | Usage |
|-----------|------|-------|
| wlan0 | STA (station) | Internet connectivity (tethered or hotspot client) |
| wlan1 | AP (access point) | CPC200 wireless adapter connection (ssid=myChevrolet 32D4) |
| wlan2 | P2P | WiFi Direct for wireless projection protocols |

---

## Ethernet AVB

- **NIC:** Intel I211, 1Gbps
- **gPTP role:** Master
- **AVB streamhandler:** v3.2.7.2 (GM3/CSM)
- **Audio endpoint:** NXP TDF8532 codec on CSM → external amplifier → 4 speakers

The IHU serves as the gPTP grandmaster on the AVB network, providing time synchronization for audio stream delivery to the CSM amplifier module.
