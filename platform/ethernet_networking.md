# GM Info 3.7 Ethernet and Networking

Scope: the radio's (gminfo37, Intel Apollo Lake, Android 12) network architecture: interfaces and addressing, the backbone Ethernet switch, VLAN 4/5 address maps, listening ports and network ADB, mDNS, WiFi/Bluetooth, and bench connectivity/time-sync findings.
Also held here: USB identifiers/gadget, UART device table, physical Automotive-Ethernet bus map (X11/X84), GM cloud endpoints, CAN-bus gateway note (see the unnumbered sections after section 8).
Out of scope (pointers only): AVB/gPTP/AAF audio transport, ELK RAM-Linux network tests, UDS/MDI2 diagnostics beyond the compact summary in 3.2, IPC channel detail, FSA wire protocol, host-firewall security findings.

Evidence legend: `[C]` confirmed against a capture/artifact; `[?]` open or inference; `[read]` read from a dump rather than a live shell. "Y175" = bench radio build `W213E-Y175.5.2-SIHM22B-383.1` (live captures dated 2026-10-05/06); "Y181" = `W231E-Y181.3.2-SIHM22B-499.3`. Content dates run to 2026-11-17.

Related: [hardware_specs.md](hardware_specs.md), [vehicle_network.md](vehicle_network.md), [avb_audio_transport.md](avb_audio_transport.md), [fsa_protocol.md](fsa_protocol.md), [elk_recovery.md](elk_recovery.md), [security.md](security.md), [firmware_versions.md](firmware_versions.md), [ota_programming_roles.md](ota_programming_roles.md), [vip_ipc_ghs.md](vip_ipc_ghs.md). Bench host-side VLAN/ADB setup baseline (owns the repeatable host configuration and acceptance checks): [../hardware/bench_setup.md](../hardware/bench_setup.md). This document owns the radio's network architecture.

---

## 1. Interfaces and addressing

| Interface | Purpose | Address, Y175 live [C] 2026-10-05 | Address, Y181 / other |
|-----------|---------|-----------------------------------|-----------------------|
| eth0 | Intel I210 physical (gPTP master, 1 Gbps). Only `I210` appears in artifacts; the `WGI210CL rev A3` marking is prose-only; "I211" was an unverified near-twin reading (see `../hardware/teardown.md`) | inet6 link-local only (`fe80::6865:676d:2f1:e689/64`), **no IPv4** | `192.168.1.100/24` (same as vlan5) |
| vlan4 | Internal vehicle/service network (VCS/EOCM) | `172.16.4.100/24` | `172.16.4.x` |
| vlan5 | Vehicle network (NFSA/FSA) | `192.168.1.100/24` (IHU) | `192.168.1.100` |
| br0 | WiFi hotspot bridge (hostapd_bcm + dnsmasq) | `192.168.5.1/24` | wlan1 membership supported; wlan2 membership unverified |
| wlan0 | Historically assigned STA | **absent** (not present/up in the capture; creation on demand unverified) | role depends on runtime state |
| wlan1 | WiFi AP; may serve a wireless projection adapter | up, inet6 link-local only; shares link-local/MAC-derived ID (`...fe87:d89e`) with br0, so it is the bridged member | provisioned SSID varies |
| wlan2 | Historically assigned P2P | up, inet6 link-local only (`...fee7:d89e`); separate from br0 (wlan2-in-br0 not confirmed) | role not established |

Y175 routes [C]: `172.16.4.0/24 dev vlan4`, `192.168.1.0/24 dev vlan5`, `192.168.5.0/24 dev br0`; **no default route**. `hostapd_bcm` running, AOSP `hostapd` stopped. `persist.sys.wifi.only2g=1` [C]. Source: `net_ifaces.txt`, props.

- **SSID:** `myChevrolet 32D4` is UNVERIFIABLE-FROM-LIVE (per-unit/provisioned). This bench unit's live SoftAP was `benchd89`; the raw capture holds no dumpsys-wifi SSID string.
- **Net hostname:** `myChevrolet` [C] (`net.hostname`, props:185 on Y175).
- **eth0 MAC:** historical configuration records a locally administered address; per-unit/runtime stability is not established (the earlier "always" claim was unsupported, corrected 2026-11-15). Live Y175 eth0 MAC is UNVERIFIABLE-FROM-LIVE (no `link/ether` line captured; MACs redacted in the digest). The tech-specs snapshot lists `02:04:00:00:01:00` (see Open conflicts).
- **Kernel driver:** custom `igb_avb`; mainline `igb`/`CONFIG_IGB` is disabled per the Jun-2026 capture. In the native-Linux ELK bench the I210 (PCI `8086:157c`) binds to mainline `igb`; eth0 and VLAN5 carrier up, root SSH verified (see [elk_recovery.md](elk_recovery.md)).
- VIP-to-SoC UART IPC is a separate link: see [vip_ipc_ghs.md](vip_ipc_ghs.md).

## 2. Backbone Ethernet switch

### 2.1 Variants (board-variant, not a discrepancy)

The backbone switch IC is selected by `persist.vendor.harman.hardwareid`. Both variants serve the vehicle's 100BASE-T1 links; this implies neither a 100 Mbps silicon ceiling nor identical firmware port numbering (see 2.3).

| Variant | hardwareid classes | Ethernet manager (init service) | Evidence |
|---------|--------------------|----------------------------------|----------|
| Broadcom BCM8953x / BCM89551 | ED / DV1 / DV2 / DV4 / DV6 / PV1 / MY22 (teardown unit) | `ethctrlmgr` | MY22/DV teardown unit; SPI NOR IS25LP016D (16 Mbit, SOIC8, week 43/2022) holds the switch firmware on this unit ([hardware_specs.md](hardware_specs.md), `../hardware/teardown.md`) |
| Marvell 88Q5050 | MY23+ / MY24 | `ethmvlctrlmgr` | `ETH_SWITCH` fw part `85759612.AA` = `MVL88Q5050_globalB_234702AB_02_09_1003` (UpdateService module 52); live Y181 bench radio |

- Live Y181 (2026-11-12, adb): `init.svc.ethmvlctrlmgr=running`, `init.svc.ethctrlmgr=stopped`, `ethmvlctrlmgr` process under uid `vendor_ethctrlmgr` [C]; `UpdateService-ModuleVersionUtil module=52` in `main.log` [read]. The manager selection agrees with the Marvell module string (inferred same board-variant; not a chip read). The updater's reported module identity does not by itself resolve physical-chip identity.
- Live Y181 `persist.vendor.harman.hardwareid=MY23DV1` (29 of 30 gmlogger `props` snapshots in `/cache`; also `persist.vendor.veh.variant=GB`, `persist.vendor.hw.variant=0xB1020260` in all 30) [read]. The value is unreadable from the shell uid (avc denial on `persist_vendor_harman_hardwareid_prop` for `gm_update_engine`). That this prop selects the switch driver remains inferred.
- Live Y175 (2026-10-05): `ethctrlmgr` running (ps PID 918, `init.svc.ethctrlmgr=running`), `ethmvlctrlmgr` absent [C]. The Y175-vs-Y181 manager swap holds as a discriminator (see Open conflicts for the Y175 package contents).
- Full hardwareid-to-driver map: `video/hardware_rendering.md` (path relative to a different tree root; not verified from here).
- SPI NOR note: whether the Marvell variant's switch firmware sits in the same NOR is not established (2026-11-12).

### 2.2 Historical switch-port labels

Not reconciled to the firmware config numbering below.

| Port | Connected node |
|------|----------------|
| 0 | RSI |
| 1 | AMP |
| 2 | CGM |
| 3 | TCP |
| 5 | Host (A11/IHU) |

### 2.3 Shipped switch speeds [C] 2026-11-13

Decoded from the actual `firmware/update_packages/Y175/extracted/85759612` package (relative to `aaos/gm_aaos/2024_Silverado_ICE`), not inferred from the bus link rate. This 1,497,632-byte ETH_SWITCH module contains the embedded name `MVL88Q5050_globalB_234702AB_02_09_1003.bin`, matching the module identity in [firmware_versions.md](firmware_versions.md) and [ota_programming_roles.md](ota_programming_roles.md). `portCfg.intfCfg` key starts at byte offset 182627 (decimal):

| Config `intf` | `mode` (enabled) | `br` | `speed` (literal string) |
|---------------|------------------|------|--------------------------|
| 0, 1 | true | slave | `100` |
| 2 | true | master | `100` |
| 3, 4 | true | slave | `100` |
| 5 | true | auto | `1000` |
| 6, 8 | false | auto | `auto` |
| 100, 101 | false | slave | `100` |

- **[C] The switch is multi-speed-capable, not hardware-limited to 100 Mbps.** GM's shipped configuration fixes the vehicle-facing entries (0-4, 100, 101) at `"speed":"100"`, not `"auto"`; 100/101 are disabled. Exactly one enabled entry, `intf 5`, is fixed at `"speed":"1000"`. The vehicle's 100BASE-T1 links therefore run at 100M by explicit firmware configuration on silicon that also supports gigabit operation.
- The package contains CLI help `avb port speed set <port> <auto|100|1000>` at byte offset 164019: 1000 is an explicit driver/CLI option. This generic syntax does not establish that every physical T1 PHY accepts 1000, or that changing a setting alone would make a vehicle endpoint operate at gigabit speed.
- **[?] Strong inference:** `intf 5` is the internal SoC-facing uplink to the Intel I210 MAC (its sole 1000 setting fits the I210's 1 Gbps link and the "Port 5 = Host" label). The file does not name `intf 5` as the host uplink; not independently proven while the numbering reconciliation (2.4) is open.

### 2.4 Configured VLANs and port-numbering reconciliation [?] OPEN, 2026-11-13

`dot1qCfg.vlanCfg` (key at byte offset 182024) decimal bitmasks. Bit positions belong to the config's own numbering domain, not a proven mapping to the 2.2 table.

| VLAN | `tag` | `untag` | Tagged config bit positions |
|------|-------|---------|-----------------------------|
| 1 | 0 | 511 | none; native/default VLAN, all nine bits 0-8 untagged |
| 2 | 43 | 0 | 0, 1, 3, 5 |
| 4 | 47 | 0 | 0, 1, 2, 3, 5 |
| 5 | 47 | 0 | 0, 1, 2, 3, 5 |
| 6 | 13 | 0 | 0, 2, 3 |
| 9 | 10 | 0 | 1, 3 |

- **[?] VLAN 9 configured but never observed live:** full, unfiltered VLAN-ID sweeps on both the Bus-2/pins-3-4 tap and the X11-pins-1/2 tap found only `{untagged, 2, 4, 5}`. Canonical evidence: `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` section 14 in the `analysis/Y175_2026-11-02` tree. Open alternatives: VLAN 9 is tagged on ports not yet physically tapped; it carries a conditional/rare service; or it is defined but unused on this build. None selected.
- **[?] Numbering domains NOT reconciled:** the 2.2 table labels Port 2 as CGM, associated with Bus 2 where the VLAN 2 AVB flood is confirmed, yet config VLAN 2's mask 43 excludes bit 2 (includes {0,1,3,5}). The config `intf`/bit indices may be a different domain (internal MDIO/register indices vs physical-connector labels), or one of the port-to-bus mappings is wrong. **Do not transfer port numbers between this config and the 2.2 table until tested.** A future bench session needs per-port live captures; no physical-port assignment is resolved.
- VLAN 2 (AVB audio flood, gPTP) is documented in [avb_audio_transport.md](avb_audio_transport.md). Physical bus map, X84/X11 pinouts: [Physical Automotive-Ethernet bus map](#physical-automotive-ethernet-bus-map) below (5-row summary table and VLAN-tag findings: [vehicle_network.md](vehicle_network.md)); connector detail `../hardware/connectors.md`.

## 3. VLAN address maps

### 3.1 VLAN 5 - Vehicle LAN (192.168.1.x/24)

| Address | Node |
|---------|------|
| 192.168.1.100 | CSM / IHU |
| 192.168.1.101 | ADB |
| 192.168.1.102 | TCP_ETH |
| 192.168.1.103 | AMP_ETH |
| 192.168.1.106 | IPC |
| 192.168.1.107 | CGM Host |
| 192.168.1.112 | CGM_ETH |

The VLAN-5 table reflects the switch/host view; the FSA DeviceInformation map (partition identity, serviceId 1001) reflects service-addressable partitions. Both are retained as observed. Canonical map (instanceId): 1=CSM(.100), 2=TCP(.102), 3=AMP(.103), 4=RSI1(.104), 5=RSI2(.105), 6=IPC(.106), 7=CGM(.112), 8=LOWRADIO(.108); PDR=.110. See [fsa_protocol.md](fsa_protocol.md).

Firewall view of VLAN 5 sources (Y181 ruleset): `.102/.104/.106/.109/.112` to `192.168.1.100`; see [security.md](security.md).

### 3.2 VLAN 4 - VCS / EOCM network (172.16.4.x/24)

| Address | Node | Notes |
|---------|------|-------|
| 172.16.4.100 | VCU_AGVM / Android (vlan4 face) | this device |
| 172.16.4.14 | **ACP (Application Control Processor)** | Historically configured as a permanent neighbor. Corrected 2026-11-14: no external T1 ARP reply in the current bench test. |
| 172.16.4.107 | Historical RTOS/GHS diagnostic candidate | Corrected 2026-11-14: the asserted symmetric diagnosticsd socket is disputed, not established. No external T1 ARP response or completed connection in the latest bench test. Historical identity is not proof of current reachability. |
| 172.16.4.112 | CGM_OTA (vlan4 face) | active, TTL=64 (Bosch JuP1, Linux) |
| 172.16.4.1 | **TCP (vlan4 face)** | live 2026-07-01; see below |
| 172.16.4.12 | EOCM_HCP_SECONDARY / EOCM_HCP_2 | code-referenced |
| 172.16.4.13 | EOCM_HCB | code-referenced |
| 172.16.4.15 | EOCM_HCP_HOST / EOCM_HCP_1 | code-referenced |
| 172.16.4.104, .110 | additional vlan4 ECUs | code-referenced, not live on bench |

- **Bench scope (2026-11-14):** both physical T1 taps reached the Android guest, but none of the historically documented GHS candidates answered ARP. This does not establish that GHS is stopped or absent. Diagnostic results over this link are owned by `../diagnostics/`; compact summary (2026-11-14):
  - The direct Android diagnostic listener completed level-1 SecurityAccess: [validated T1 sequence](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
  - A separate authenticated hard-reset request returned `7F 11 25` after about 30 seconds of pending replies; no Android reboot was observed: [ECUReset result](../diagnostics/diagnosticsd_security_access.md#live-t1-ecureset-validation-2026-11-14).
  - **Converter gap:** the later [USB-logcat/UART correlation](../diagnostics/diagnosticsd_protocol.md#concurrent-uart-and-usb-logcat-correlation-2026-11-14) shows wire services 11 and 23 become `DIAG_UNKNOWN_SERVICE` in the AAOS converter. Their NRC-25 replies therefore do not establish a physical subnet/GHS timeout or transparent MDI2 equivalence.
  - The [full DID-number sweep](../diagnostics/diagnosticsd_dids_and_dtc.md#exhaustive-did-number-sweep-and-extended-enumeration-2026-11-14) verified **135 readable DIDs at level 09**, covering every 16-bit DID number in that state; it does not establish every UDS service or programming route. A later `03D8` start enabled AM/audio and made `4775` readable, bringing the observed union across states to **136**.
  - The final explicitly requested `0249` calibration clear completed: live module identities changed to `70008/00` while MEC remained `FF`. This confirms selected direct-T1 control operations; programming-session entry still failed its authenticated vehicle-state gate: [completed clear](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).
- **TCP module dual-homed on vlan4 (2026-07-01):** `172.16.4.1` was previously dead on bench. With the telematics module's cellular antenna connected it answers TCP connects on ports **9010** (`DeviceInformation`, instant accept) and **9012** (`RemoteReflash`, instant accept); an unrelated port on the same host times out with no RST (silent filter, not a routing artifact; confirmed against both a truly dead vlan4 IP and a known-live host that sends RST for closed ports). Its MAC (`02:04:00:00:02:00`) is identical to `192.168.1.102` (TCP; see [fsa_protocol.md](fsa_protocol.md#deviceinformation-instanceid--partition)), confirming the same physical module. Both ports accept-then-silently-close under the standard single-client limit (`com.gm.domain.server.delayed` already holds the legitimate session), matching the vlan5-side behavior for the same instance. Working theory: the module fully activates its network stack (including the vlan4 face) only with an active cellular link; not confirmed causally (needs an antenna-disconnect re-scan). These 9010/9012 listeners are on the TCP module, not the radio's own 192.168.1.100 listeners in section 4.
- **Code-referenced VCU-variant subnets** (unreachable on bench, 100% loss): `192.168.118.1`=VCU_AGVM, `192.168.118.2`=IPC; `172.16.5.x` (new in VCU variant). VCU/CIP inter-VM topology: [`../projection/cluster_navigation.md`](../projection/cluster_navigation.md).

## 4. Listening ports and network ADB

### 4.1 Radio listeners

Y175 live [C] 2026-10-05 (`net_sockets.txt`), cross-checked against Y181 `enumeration/Y181/jun2026/`. The listener set varies with projection-session state; an earlier apr2026 snapshot (only 9002/9016 @ .1; 9010 outbound; 7000 gone; DNS on .102) is **withdrawn**.

| Bind address (live) | Port | Proto | uid | Service |
|---------------------|------|-------|-----|---------|
| `0.0.0.0` only (no separate loopback listener) | 6363 | TCP | 1041 (audioserver) | **AVB audio daemon**: init-owned listen socket, text IPC bus for AVB audio routing; arbitrary data returns `"ERROR"`. Low value. "AVB audio daemon" process name not independently pinned (no socket-to-pid map in capture). |
| `0.0.0.0` + `:::7000` (wildcard, not br0-scoped; reachable on br0/`192.168.5.1` by virtue of the wildcard) | 7000 | TCP | 1001000 (`u10_system`, user 10's system uid, not uid 1000) | **AirPlay/AirTunes 320.17.8** (Cinemo `libNmeCarPlay` r14): `GET /` returns `404; Server: AirTunes/320.17.8`; advertised via mDNS (section 5) with SRV target `Android.local.:7000`. CarPlay audio bridge: [`../audio/carplay_audio_pipeline.md`](../audio/carplay_audio_pipeline.md); also [`../VERIFICATION.md`](../VERIFICATION.md). **Not ADB.** Identity rests on the banner/mDNS, not on the socket table, which alone cannot show it. |
| `0.0.0.0` | 49156 | TCP | 0 (root) | **diagnosticsd UDS-over-TCP bridge** (PID snapshot-dependent; consistent with `gm_diagnosticsd`, PID 590 on Y175). Direct T1 level-1 SecurityAccess live-verified with tester F4 and extended session (2026-11-14); direct forwarding to a GHS/RTOS endpoint unproven. See [`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md). |
| `::ffff:192.168.1.100` (IPv6-mapped IPv4; the guest has no `.1` interface or route) | 9002 | TCP | 1000 (system) | **FSA RemoteModuleHMI** (serviceId 1007), the guest's own FSA server |
| `::ffff:192.168.1.100` | 9010 | TCP | 1000 | **FSA DeviceInformation** (serviceId 1001). A listener, not outbound-only. |
| `::ffff:192.168.1.100` | 9016 | TCP | 1000 | **FSA NetworkAccessManager** (serviceId 1026) |
| `127.0.0.1`, `192.168.5.1` (br0) | 53 | TCP/UDP | 1052 (dnsmasq) | DNS, loopback + br0 WiFi-AP side (not on `.102`) |

Additional loopback/wildcard listeners seen live (9112, 7011, 36103, 41365, 9001-9004) belong to the carlink PoC app `zeno.gmccpa` (uid 1010120), not platform services.

The FSA server table above is a historical snapshot, not a complete or invariant six-port inventory. Wire protocol, service catalog and protobufs: [fsa_protocol.md](fsa_protocol.md).

### 4.2 FSA client-side targets (IHU as client, VLAN 5)

| Remote address | Port | Status |
|----------------|------|--------|
| 192.168.1.102 | 9005, 9012, 9018 | Historical snapshot; **not observed** in the Y175 live capture (not refuted; UNVERIFIABLE-FROM-LIVE) |
| 192.168.1.112 (CGM) | 9010, 9018 | **Observed live** Y175: uid 1000 in SYN_SENT |

Live also showed an established `192.168.1.100:9016 <-> 192.168.1.100:58814` loopback-on-vlan5 pair. Confirmed bench artifact: this is an out-of-vehicle bench (radio + display + GM USB receptacles, no vehicle bus/ECUs), so `.112` (CGM) and `.102` (TCP) are external nodes that are not present; the SYN_SENT is the IHU reaching an absent peer, expected, not a defect (see BENCH CONTEXT in `LIVE_Y175_FACTS.md`).

### 4.3 Network ADB (corrected 2026-11-15)

- The working radio listener is **TCP 9040**, verified over T1. 5555 is the standard ADB port, not the verified accessible bench port.
- The shipped firewall is default-deny with source/destination, interface and port allow-rules; a listener on 5555 alone does not grant access.
- The working host setup uses a source-bound loopback relay on **19040** to the radio's 9040 listener, preserving an allowed VLAN-5 source identity. These are configured bench ports, not immutable factory service assignments. No firewall change was needed.
- Canonical procedure: `BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` section 9.2 in the Y175 analysis/source_notes tree.
- Host firewall rules, SoftAP exposure and risk ratings: [security.md](security.md) (network services section).
- **Follow-up, 2026-11-15:** after the 2026-11-14 post-clear power cycle and MDI2 recovery (narrative: [vehicle_config.md](vehicle_config.md); [completed MDI2 recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14)), USB ADB and T1 ADB on radio TCP 9040 were subsequently operational; the final MEC value remains unverified. At the recovery checkpoint itself, ADB and final MEC had not been rechecked.

## 5. CarPlay mDNS fingerprint (2026-11-13)

**[C]** Live vlan5 mDNS at radio boot, in the same clean power-on capture described in [Ethernet boot timing](../runtime/boot_timing.md#y175-ethernet-capture-boot-timing-2026-11-13), advertised `CarPlay._airplay._tcp.local.` with SRV target `Android.local.:7000` (identification: section 4.1). A separate `_carplay-ctrl._tcp.local` PTR query pattern was also observed; the query alone did not establish a second service advertisement.

| TXT key | Observed content (sensitive identifiers redacted) |
|---|---|
| `deviceid` | `<AIRPLAY_DEVICE_MAC>` |
| `features` | `0x4040280,0x61` |
| `flags` | `0x4` |
| `model` | `myChevrolet` |
| `pi` | `<AIRPLAY_PERSISTENT_UUID>` |
| `srcvers` | `320.17.8` |

- `model=myChevrolet` matches `net.hostname=myChevrolet` (section 1). Placeholders denote the captured TXT `deviceid` and `pi` UUID, redacted to avoid echoing them into pushed material.
- `pi` was a persistent, stable per-device identifier, unchanged between observed announcements; stability across resets or reprovisioning is not established.
- **[?] Unexplained deviceid/wlan0 discrepancy:** the advertised deviceid closely resembles the documented `wlan0` MAC, but its final octet is `a0` versus `9e` in the [existing wlan0 capture](../enumeration/Y175/raw/network_interfaces.txt) (also `persist.sys.wifi.mac_addr` in the companion properties capture). Not identical; the interface relationship is unverified, neither established as the same interface nor dismissed as a typo.
- **Separate post-factory-reset capture, 2026-11-14:** `radio-en12-20261114.pcapng` contains CarPlay-control queries but no mDNS responses or SRV advertisements. Android-12 DHCP Discover traffic is also present. Its `_adb*` service names are queries from the other source, not radio ADB advertisements. These do not supersede the advertised-fingerprint above; they describe a different, partial boot capture. See the [capture analysis](../diagnostics/diagnosticsd_routines_and_recovery.md#partial-post-factory-reset-ethernet-capture-2026-11-14).

## 6. WiFi and Bluetooth

| Interface | Mode | Usage |
|-----------|------|-------|
| wlan0 | Historically assigned STA | Absent in the cited Y175 snapshot; creation on demand is unverified |
| wlan1 | AP role supported by observed hotspot state | Provisioned SSID varies; adapter-specific use is configuration-dependent |
| wlan2 | Historically assigned P2P | Interface observed; exact live role/bridge membership not established |

- The historical three-role map is not proof of three simultaneously active interfaces. Y175 live (2026-10-05): only wlan1 and wlan2 up; `hostapd_bcm` running confirms the AP role is active and br0 (`192.168.5.1`, dnsmasq) is up, consistent with wlan1=AP. Interface addressing: section 1.
- Chipset: Broadcom BCM (802.11a/b/g/n/ac, 2.4 + 5 GHz), AAOS driver `dhd`, hotspot supported. In the native-Linux ELK bench the card enumerates as BCM4359 `14e4:43ef` (unbound in the probe boot; probe03 transfer success is separate evidence); see [elk_recovery.md](elk_recovery.md). `persist.sys.wifi.only2g=1`.
- Tech-specs snapshot (Y177): `current_ssid`, RSSI -39 dBm, IP, WiFi MAC and BT MACs recorded but redacted (`<HOME_SSID_REDACTED>`, `<LAN_IP_REDACTED>`, `<WIFI_MAC_REDACTED>`, `<BT_MAC_REDACTED>`).
- Bluetooth 5.0; profiles HFP, A2DP, AVRCP, PBAP, MAP, HID; name `myChevrolet`; one paired iPhone and active HFP in the snapshot (MAC redacted).
- Wireless CarPlay and SoftAP exposure (CarPlay runs on `wlan1` over IPv6 link-local; external br0 SoftAP surface is DNS 53 + 7000): [security.md](security.md).

## 7. Bench connectivity and automatic time, 2026-11-15

Scope: live Y175 Android 12, build increment 213; static checks against the matching read-only OS tree. These establish local connectivity, not a working Internet gateway or Play Store download.

| Finding | Evidence |
|---------|----------|
| **[C] Bidirectional T1 IP traffic:** radio-originated VLAN-5 ICMP reached the bench host; replies in about **0.47-0.54 ms**; wire observation confirmed tagged requests and replies. Proves the local path, not Android application Internet. | ping + wire capture |
| **[C] Android Ethernet state:** `EthernetTracker` matches `eth\d` and tracks `eth0` (capabilities `INTERNET`, `NOT_RESTRICTED`, `TRUSTED`). `networkAgent` null; link properties only IPv6 link-local, no DNS, no IPv4 gateway. ConnectivityService: `Active default network: none`. A dummy-interface default in a separate routing table is not an application Internet connection. | dumpsys |
| **[C] Configuration vs provisioning:** Ethernet API returned `UNASSIGNED` for both IP assignment and proxy mode; IpClient nevertheless reported IPv4-enabled provisioning with no static configuration and logged completion of its pre-DHCP action. This does **not** establish why DHCP transmission is absent or that `UNASSIGNED` is the cause. | dumpsys / logcat |
| **[C] Limited DHCP test:** a temporary DHCP server on the untagged bench link received no DHCP packets in 35 s; no lease. Does not establish DHCP rejection, behavior after a client restart, or reachability through every switch port/VLAN. | host DHCP server |
| **[C] Configuration permission barrier:** `IEthernetManager.setConfiguration()` (explicit DHCP) returned `Requires one of the following permissions: android.permission.NETWORK_STACK, android.permission.MAINLINE_NETWORK_STACK`. Shell's granted `NETWORK_SETTINGS` and `CONNECTIVITY_INTERNAL` were insufficient; configuration unchanged. | shell call |

**Automatic time:** live `time_detector` had automatic detection enabled, priorities `[telephony,network,gnss]`, and empty suggestion histories for all sources including external. The network-time service had no cached NTP sample. Static framework resource `config_ntpServer` is `time.android.com`; live global `ntp_server` was unset. The radio clock was roughly 871 days behind the Mac; setting it from the Mac restored agreement to one-second resolution. This was a manual bench correction, **not** evidence of automatic synchronization. The active GM vehicle-time delivery path is unresolved; AVB gPTP transmission does not establish calendar-time synchronization (gPTP: [avb_audio_transport.md](avb_audio_transport.md)).

**Next discriminator:** explain the non-transmitting DHCP client and identify the supported path that provisions an Android Internet network; then verify DNS, default-network validation, application HTTPS/Play Store access, and automatic time independently. Full telematics emulation is not yet shown to be necessary. Temporary host addressing and DHCP/capture processes were removed; USB ADB was verified with TCP ADB disabled after probing.

## 8. Related runtime discriminators

- **DABridge USB port numbering (not a Y175/Y181 discriminator):** live Y175 (same exact build `W213E-Y175.5.2-SIHM22B-383.1`) reports `sys.dabridge.dev.portnum=1-6.3` / `host.portnum=1-6.0` (props.txt:482-483), the value previously attributed to Y181 only; the prior Y175 enum (`gm_enum_20260117_081801`, identical build) reported `1-12.3`/`1-12.0`. The value tracks which physical USB receptacle the DA bridge enumerated on, not firmware version. Y181 reference: `1-6.x`. USB detail: [hardware_specs.md](hardware_specs.md).
- Ethernet manager swap (`ethctrlmgr` vs `ethmvlctrlmgr`): section 2.1.

## USB Identifiers and Gadget

| Device | VID | PID | Notes |
|--------|-----|-----|-------|
| GM IHU (iAP) | 0x2996 | 0x0120 | iAP2 USB role |
| **Aptiv H2H (Head-to-Head) Bridge** | 0x2996 | `0x0100`-`0x0105` (match table; this radio enumerates `0x0105`) | **On-radio** USB bridge device, NOT a cross-ECU link. `dabridge` (kernel, GM custom) is a host-side driver that matches this VID/PID on the internal USB tree and, once bound, bridges a chosen host-side port to a device-side port (`/sys/bus/usb/drivers/dabridge/bridgeport`) so the physical xHCI host stays up for the hub/accessory tree while a virtual UDC (`dabr_udc.0`) presents the ADB (and CarPlay/AA) gadget on that one bridged port. `RDMSADBHandler` writes `1-6.3` (dev port) here on `ADB_Enable`. (= the "GM proprietary" 0x0105 entry.) |
| **GM V10 E2 PD USB Hub** | 0x2996 | 0x0132 | USB hub; its presence **blocks** `RDMSADBHandler.ADB_Disable` (peripheral-to-host role reversal fails, ADB recovers). (= the "USB hub" 0x0132 entry.) |
| CPC200 adapter | 0x1314 | 0x1521 | manufacturer="Magic Communication Tec.", product="Auto Box" |
| dabr_udc | - | - | USB device controller for gadget mode |

VID `0x2996` (decimal 10646) = **Aptiv / Delphi Technologies**. The H2H bridge + PD hub + `RDMSADBHandler` Binder service (#66) form the ADB-over-H2H routing path; see [`../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md). The decimal Y177 snapshot (10646:261/306/288) and port-numbering note: [hardware_specs.md](hardware_specs.md) section 10; section 8 above for the DABridge port-numbering note.

### USB Gadget

- **Controller:** `sys.usb.controller=dabr_udc.0`
- **Kernel:** `CONFIG_USB_GADGET=y`
- **FunctionFS endpoints:** iAPClient, adb, mtp, ptp

The `dabr_udc.0` device controller supports USB gadget mode via FunctionFS. The kernel has `CONFIG_USB_GADGET=y` and exposes functionfs endpoints for iAPClient (iAP2 accessory role), adb, mtp, and ptp.

**[C] live-Y175 2026-10-05: CONFIRMED** (props, `mounts.txt`). `sys.usb.controller=dabr_udc.0`, `sys.usb.configfs=1`, `sys.usb.config=adb`, `persist.sys.usb.config=adb`; `sys.dabridge.host.portnum=1-6.0`, `sys.dabridge.dev.portnum=1-6.3` (matches the H2H bridge row above and FAQ section 20). FunctionFS mounts present and rw: `iAPClient /dev/ffs`, `adb /dev/usb-ffs/adb`, `mtp /dev/usb-ffs/mtp`, `ptp /dev/usb-ffs/ptp`. Y175 current role is **device/adb** (this is the bench ADB session), not the boot-default host role.

## UART Devices

| Device | Owner | Purpose |
|--------|-------|---------|
| /dev/ttyACM1 | root; crw-rw-rw- | Historical MCP2200 identity; live SELinux label `sxm_device`, not an unrestricted generic debug endpoint |
| /dev/ttyS0 | bluetooth:bluetooth | Bluetooth HCI |
| /dev/ttyS1 | root:root | VIP IPC (HDLC) |
| /dev/ttyS2 | root:root | serial_device / Android guest console (`console=ttyS2`) |
| /dev/ttyS3 | root:root | Live SELinux label `display_panel_device`; function not independently traced |

**[C] live-Y175 2026-10-05: CONFIRMED with one label note** (`dev_listing.txt`). `ttyACM1` is indeed `crw-rw-rw-` (world-writable), owner root, but its SELinux label is **`sxm_device`** (SiriusXM), not a generic debug node; MCP2200 is the hardware identity (the old "debug" function label was incorrect), and `sxm_device` is how policy labels it. `ttyS0` bluetooth (`bluetooth_serial_device`), `ttyS1` root (`ipc_serial_device` = VIP IPC), `ttyS2` root (`serial_device`) all CONFIRMED. `ttyS3` is root `display_panel_device` live (not blank). No `ttyACM0` present. IPC link detail: [vip_ipc_ghs.md](vip_ipc_ghs.md).

## Physical Automotive-Ethernet bus map

(GM service data.) The AVB/Ethernet links are point-to-point automotive-Ethernet pairs (single twisted pair, 100/1000 Mbit in the service description; shipped speeds: [section 2.3](#23-shipped-switch-speeds-c-2026-11-13); **no terminating resistors**) off the A11 Radio's on-board switch (BCM89551 on the MY22/DV teardown unit; Marvell 88Q5050 on the live Y181 bench radio; board variant, same spec; 2026-11-12). Two nodes host switches, the **A11 Radio** and the **K56 Serial Data Gateway Module**; every other node is a leaf `[Module <-> Switch <-> Module]`. GM service data names each bus and circuit: ALLDATA *Radio-Audio System -> Data Link Communications* + connector end-view `A11 Radio X11`, corroborated by the **GM Silverado 2500/3500HD Electrical Body Builder Manual** (`24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`, *Data Communications -> Ethernet Bus Description*), which enumerates the full bus list. This grounds the IP-level endpoints above to physical wire (closes [vehicle_network.md](vehicle_network.md) open item #1 for the amp pair).

**Test vehicle:** 2024 Silverado **2500 HD LTZ**, RPO **IOK**; the HD BBM above is the matching service manual. Per the VIN's factory RPO Code List this truck has no Head-Up Display (no UV6/HUD code) and no rear-seat video, so radio buses **5** (P22F rear-seat video) and **14** (P29 HUD) are **not equipped**; only buses **2 / 4 / 6** are wired on X11. Options and the shared T1XX bus numbering: [vehicle_config.md](vehicle_config.md).

**Radio (A11) Ethernet buses** (all land on connector **X11**, 12-way F CTS-050):

| Bus | Circuits | Endpoints | On IOK 2500HD |
|-----|----------|-----------|---------------|
| Ethernet 2 | 4757 / 4758 | **A11 Radio <-> K56 Serial Data Gateway** (radio X11 p3/4) | wired (harness-confirmed) |
| Ethernet 4 | 7210 / 7211 | **A11 Radio <-> K73 Communication Interface Module** (radio X11 p11/12). *IOR-radio variant routes this as K56 <-> K73 instead.* | wired (harness-confirmed) |
| Ethernet 5 | 7212 / 7213 | A11 Radio <-> **P22F Video Display - Right Rear-Seat Back** | not equipped (no rear-ent RPO) |
| **Ethernet 6** | **7214 / 7215** | **A11 Radio <-> T3 Audio Amplifier**, the Bose AVB audio pair (radio X11 p8/9 -> amp T3 X3 p1/2) | wired (harness-confirmed) |
| Ethernet 14 | 7230 / 7231 | A11 Radio <-> **P29 Head-Up Display** | not equipped (no UV6/HUD) |

**Other vehicle Ethernet buses (not on the radio, via K56 gateway):** Eth 1 (below); Eth 3 (7208/7209) K56 <-> K179 Auto-Driving Mapping Module; Eth 7 (7216/7217) K56 <-> P16 IPC Cluster / K190 Off-Board Charger; Eth 11 (7224/7225) K124 Image Processing <-> K179; Eth 15 (7232/7233) K56 <-> K161 Perf Data Recorder <-> P22F passenger-seat display.

- The amp is a leaf on **Bus 6**. Amp control/discovery is separate: **AUTOSAR CAN 5** (4985/4984), radio **X6 p9/10** <-> amp T3 X3 p11/12 (see [`../hardware/connectors.md`](../hardware/connectors.md) X6 row). T3's two separate links (Bus 6 audio data plane vs CAN 5 control plane) are summarized in [`../hardware/connectors.md`](../hardware/connectors.md) Audio Architecture - Bose (2026-11-13).
- **Connector caution:** the radio's Ethernet lives on **X11** (12-way CTS-050). It is a *different* physical connector from **X6** (29-way, speaker outs + CAN 5); do not conflate them. Earlier notes that labeled the Ethernet connector "X6" were in error.

### Ethernet 1 - service diagnostics / programming (X84 DLC <-> K56)

Not a radio bus, but the service-tool entry point into the Ethernet backbone. **Ethernet 1 = two twisted pairs**: **1R** (circuits 4972/4973) and **1T** (4974/4975), run **X84 Data Link Connector <-> K56 Serial Data Gateway**. Used to diagnose/flash control modules over Ethernet instead of CAN; the **K56 gateway converts Ethernet serial data <-> CAN both directions**. An **Ethernet-enable circuit (7207)** wakes K56 for Ethernet diagnostics/programming.

**X84 DLC (16-cavity OBD) pinout (Ethernet + CAN):** T1 CAN 7 [+], T2 PP-CAN 1 [+], **T3 Eth 1R [+]**, T4 scan-tool ground, T5 signal ground, T6 CAN 6 [+], T7 PP-CAN 2 [+], **T8 Eth 1 enable**, T9 CAN 7 [-], T10 PP-CAN 1 [-], **T11 Eth 1R [-]**, **T12 Eth 1T [+]**, **T13 Eth 1T [-]**, T14 CAN 6 [-], T15 PP-CAN 2 [-], T16 scan-tool B+. (CAN 6 = diagnostics/programming; CAN 7 = plant programming only; Private-Presentation CAN 1/2 = Engineering-only, security-gated.) Source: BBM *X84 Data Link Connector*.

- Physical harness/pinout detail: [`../hardware/connectors.md`](../hardware/connectors.md) Audio Architecture and Authoritative IOK Connector Table. Radio-side Ethernet connector **X11** mating plug (P/N 13529935) datasheet, Delphi/Aptiv drawing **33283033**: [`../hardware/datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf`](../hardware/datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf).

**[?] [2026-11-13] X11 p1/2, recorded "not occupied" (`connectors.md` X11 row), carried live traffic when independently tapped.** Open, not yet reconciled with the "not occupied" claim. Same VLAN trunk and service allow-list as Bus 2, opposite PHY master/slave role, no matching GM circuit number for pins 1/2. Canonical writeup: `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` section 14 in the `Y175_2026-11-02` analysis tree (also section 2.4 above).

## GM Cloud Endpoints and Service Architecture

| Endpoint | Port | Purpose |
|----------|------|---------|
| vtmpub.oboservices.mobi | 443 | OTA / OMA-DM updates |
| vehicle.api.gm.com | 443 | Vehicle registration |
| vehicle.api.gm.com | 20445 | Security logging |
| vehicle.api.gm.com | 20647 | Auth / personalization |

Telematics (CGM module) is a separate vehicle node. The historical cloud endpoint list above is not a fresh connectivity test, and end-to-end cloud availability/dependencies were not established by the isolated radio bench (corrected scope, 2026-11-15). Update libraries (`libpal_swupdate_ecu.so`, `libpal_swupdate_hostos.so`, `vendor.gm.swupdate@1.0.so`): [ota_update_stack.md](ota_update_stack.md); [ota_update_stack.md](ota_update_stack.md)'s claim that they are also listed here is superseded by this pointer (they are not).

### Update Libraries

| Library | Purpose |
|---------|---------|
| libpal_swupdate_ecu.so | ECU software update PAL |
| libpal_swupdate_hostos.so | HostOS software update PAL |
| vendor.gm.swupdate@1.0.so | GM SWUpdate HIDL service |

| Service | Details |
|---------|---------|
| Power mode | State machine: Run, Accessory, Crank, Off, managed by VIP MCU ([vip_ipc_ghs.md](vip_ipc_ghs.md)) |
| Calibration / diagnostic authentication | **Separate mechanisms:** stock calibration containers use RSA-2048/SHA-256 signatures; DPS SecurityAccess has a backend-assisted CMAC path. Reusable server-key provisioning is unproven. See [seed/key and calibration signature reference](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md). Corrected 2026-11-15. |
| IPC | 20 channels (1-20) on /dev/ttyS1, HDLC protocol v16, 1 Mbps line rate ([vip_ipc_ghs.md](vip_ipc_ghs.md)) |

## CAN Bus

- **ECU count:** historical inventory lists 24; not a universal count or a live bench discovery result.
- **CSM address:** `0x80`
- **Gateway:** VIP MCU (RH850/F1K) acts as CAN gateway between vehicle bus and SoC.

The VIP MCU bridges CAN messages to the Intel SoC over the HDLC IPC link, translating vehicle bus traffic into structured IPC messages for Android services. The module at CAN address `0x80` (CSM = Center Stack Module) is the radio/head unit itself; the audio **amplifier** is a *separate* AVB endpoint (`192.168.1.103`, `AMP_ETH`) that the radio streams to over Ethernet AVB. *(Corrects earlier text calling `0x80` "the primary audio amplifier endpoint".)* CAN mechanism and signal dictionary: [can_network.md](can_network.md).

## Pointers (content owned elsewhere)

| Topic | Owner |
|-------|-------|
| gPTP, VLAN 2 AVB audio, AAF layout, usage-to-bus mapping, replacement endpoint | [avb_audio_transport.md](avb_audio_transport.md) |
| ELK RAM-Linux T1 and WiFi tests, probe kernels | [elk_recovery.md](elk_recovery.md) |
| UDS/MDI2 over T1, SecurityAccess, ECUReset, DID sweep, recovery | `../diagnostics/diagnosticsd_security_access.md`, `diagnosticsd_protocol.md`, `diagnosticsd_dids_and_dtc.md`, `diagnosticsd_routines_and_recovery.md` |
| IPC channels / HDLC link | [vip_ipc_ghs.md](vip_ipc_ghs.md) |
| USB identifiers and gadget, UART table | held here (sections USB Identifiers and Gadget, UART Devices); other USB hardware detail [hardware_specs.md](hardware_specs.md) |
| FSA wire format, service catalog | [fsa_protocol.md](fsa_protocol.md) |
| Host firewall, SoftAP exposure, listener risk | [security.md](security.md) |
| Physical Ethernet bus map, X84/X11 | held here ([Physical Automotive-Ethernet bus map](#physical-automotive-ethernet-bus-map)); 5-row summary and VLAN-tag trunk findings in [vehicle_network.md](vehicle_network.md) |
| Update libraries (`libpal_swupdate_ecu/hostos`, `vendor.gm.swupdate@1.0`) | [ota_update_stack.md](ota_update_stack.md) |
| Calibration / diagnostic authentication | row held here (GM Cloud Endpoints and Service Architecture); detail `../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` |

## Open conflicts

1. **Y175 switch package vs running manager.** `85759612` (Marvell `MVL88Q5050_globalB_...`) was extracted from the *Y175* update package (networking.md L210), yet live Y175 runs `ethctrlmgr` with `ethmvlctrlmgr` absent (firmware_versions.md L131) and the board-variant rule maps `ethctrlmgr` to Broadcom. Not settled by any dated correction; could be package-vs-bench-board difference or a manager selection not tied to the IC. Unresolved.
2. **eth0 IPv4 / MAC.** networking.md L18 gives `192.168.1.100/24` on eth0 for Y181 and no IPv4 on Y175; tech_specs L191 lists eth0 MAC `02:04:00:00:01:00` (build not stated) while the live Y175 MAC is unverifiable (L43). Not reconciled.
3. **Port-numbering domains** (section 2.2 vs 2.4) remain unreconciled by design; VLAN 9 unobserved.
4. **VLAN-5 .107 / .112 identity.** Section 3.1 lists `.107` = CGM Host and `.112` = CGM_ETH; FSA instanceId 7 = CGM(.112); section 3.2 lists `172.16.4.107` as a disputed RTOS/GHS diagnostic candidate and `172.16.4.112` as CGM_OTA. Cross-doc conflict is carried in [vehicle_network.md](vehicle_network.md).
5. **FSA client targets.** Historical `.102:9005/9012/9018` vs live SYN_SENT to `.112:9010/9018` (section 4.2): different snapshots; both retained.
6. **Network ADB port.** 5555 (standard) vs 9040 (verified over T1, with 19040 host relay): resolved by the 2026-11-15 correction as bench configuration, not a factory assignment; recorded for traceability.
7. **tech_specs vs live WiFi.** Tech-specs WiFi block is a Y177 snapshot (connected to a home SSID); live Y175 has an AP-only wlan1/wlan2 state with no wlan0 (section 6). Different capture states; not a refutation.
