# GM Info 3.7 Network Architecture

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - November 15, 2026

---

## Network Interfaces

| Interface | Purpose | Address |
|-----------|---------|---------|
| eth0 | Intel I210 physical (gPTP master, 1Gbps; "I211" was an unverified near-twin reading — see `hardware/teardown.md`) | 192.168.1.100/24 (Y181, same as vlan5); Y175 has no IPv4 on eth0 |
| vlan4 | Internal vehicle/service network; VIP↔SoC UART IPC is documented separately | 172.16.4.x |
| vlan5 | Vehicle network (NFSA) | 192.168.1.100 (IHU) |
| br0 | WiFi hotspot bridge (hostapd_bcm+dnsmasq); wlan1 membership supported, wlan2 membership unverified | — |
| wlan0-2 | Broadcom WiFi interface names; presence and roles depend on runtime state | — |
| wlan1 | WiFi AP; may serve a wireless projection adapter | `<PROVISIONED_SSID>` |

> `[C] live-Y175 2026-10-05: eth0 row CONFIRMED — eth0 carries inet6 link-local only
> (`fe80::6865:676d:2f1:e689/64`), NO IPv4 [net_ifaces.txt]. vlan4 CONFIRMED `172.16.4.100/24`,
> vlan5 CONFIRMED `192.168.1.100/24`, br0 CONFIRMED `192.168.5.1/24` [net_ifaces.txt]. Routes:
> `172.16.4.0/24 dev vlan4`, `192.168.1.0/24 dev vlan5`, `192.168.5.0/24 dev br0`; NO default
> route. hostapd_bcm **running**, AOSP hostapd stopped [props]. ADJUSTED: only **wlan1 + wlan2**
> exist live (both inet6 link-local only); **NO `wlan0` interface is present/up** — the "wlan0 STA"
> row is not borne out on Y175 live (STA iface absent in this capture). br0 and wlan1 share the same
> link-local/MAC-derived ID (`...fe87:d89e`) → wlan1 is the bridged member; wlan2 (`...fee7:d89e`)
> is separate (wlan2-in-br0 not confirmed). SSID: **not confirmed** — this bench unit's live SoftAP
> was `benchd89`, not `myChevrolet 32D4`; the raw capture holds no dumpsys-wifi SSID string, only
> `net.hostname=myChevrolet` [props:185]. Treat "myChevrolet 32D4" as UNVERIFIABLE-FROM-LIVE
> (per-unit/provisioned). `persist.sys.wifi.only2g=1` CONFIRMED [props].*

**MAC address:** historical configuration records a locally administered eth0
address; per-unit/runtime stability has not been established. The earlier
"always" claim was unsupported (corrected 2026-11-15).
**Net hostname:** `myChevrolet`

> `[C] live-Y175 2026-10-05: eth0 MAC UNVERIFIABLE-FROM-LIVE — no `link/ether` line captured
> (MACs redacted in digest). Net hostname `myChevrolet` CONFIRMED [props:185 net.hostname].*

---

## Bench Internet and automatic time feasibility — 2026-11-15

**Scope:** live Y175 Android 12, build increment 213; static checks against
the matching read-only OS tree. These findings establish local connectivity,
not a working Internet gateway or Play Store download.

- **[C] Bidirectional T1 IP traffic:** radio-originated VLAN-5 ICMP reached
  the bench host and received replies in approximately **0.47–0.54 ms**.
  Wire observation confirmed tagged requests and replies. This proves the
  local path; it does not prove Android application Internet connectivity.
- **[C] Android Ethernet state:** `EthernetTracker` matches `eth\d` and tracks
  `eth0`, whose capabilities include `INTERNET`, `NOT_RESTRICTED` and `TRUSTED`.
  Its `networkAgent` was null; link properties contained only IPv6 link-local
  addressing, no DNS, and no IPv4 gateway. ConnectivityService reported
  `Active default network: none`. A dummy-interface default in a separate
  routing table is not an application Internet connection.
- **[C] Configuration versus provisioning:** the Ethernet API returned
  `UNASSIGNED` for both IP assignment and proxy mode. IpClient nevertheless
  reported IPv4-enabled provisioning with no static configuration and logged
  completion of its pre-DHCP action. These observations do **not** establish
  why DHCP transmission is absent or prove that `UNASSIGNED` is the cause.
- **[C] Limited DHCP test:** a temporary DHCP server on the untagged bench
  link received no DHCP packets during a 35-second observation; no lease was
  issued. This does not establish DHCP rejection, behavior after a client
  restart, or DHCP reachability through every switch port/VLAN.
- **[C] Configuration permission barrier:** an attempt to select explicit
  DHCP through `IEthernetManager.setConfiguration()` returned:
  `Requires one of the following permissions: android.permission.NETWORK_STACK, android.permission.MAINLINE_NETWORK_STACK`.
  Shell's granted `NETWORK_SETTINGS` and `CONNECTIVITY_INTERNAL` permissions
  were insufficient for this method. Configuration remained unchanged.

**Automatic time:** live `time_detector` had automatic detection enabled,
priorities `[telephony,network,gnss]`, and empty suggestion histories for all
sources, including external. The network-time service had no cached NTP
sample. The static framework resource `config_ntpServer` is `time.android.com`;
the live global `ntp_server` setting was unset. The radio clock was roughly
871 days behind the Mac; setting it from the Mac restored agreement to the
one-second measurement resolution. This was a manual bench correction,
**not** evidence of automatic synchronization. The active GM vehicle-time
delivery path remains unresolved; AVB gPTP transmission does not establish
calendar-time synchronization.

**Next discriminator:** explain the non-transmitting DHCP client and identify
the supported path that provisions an Android Internet network. Then verify
DNS, default-network validation, application HTTPS/Play Store access, and
automatic time independently. Full telematics emulation is not yet shown to
be necessary. Temporary host addressing and DHCP/capture processes were
removed; USB ADB was verified with TCP ADB disabled after probing.

## Ethernet VLAN Detail

Managed automotive-Ethernet switch (board-variant IC — Broadcom BCM8953x/BCM89551 or Marvell 88Q5050, see the note below; the live Y181 bench radio reports Marvell 88Q5050, 2026-11-12). Historical switch-port labels (not reconciled to the firmware config numbering below):

> **Switch-vendor is board-variant, not a discrepancy.** The backbone switch IC is
> selected by `persist.vendor.harman.hardwareid`: **Broadcom BCM8953x/BCM89551** on
> ED/DV1/DV2/DV4/DV6/PV1/MY22 boards (the teardown unit), **Marvell 88Q5050** on
> MY23+/MY24 boards (`ETH_SWITCH` fw part `85759612.AA` = `MVL88Q5050_globalB_…`).
> Both variants serve the vehicle's 100BASE-T1 links; this does not imply a 100 Mbps
> ceiling for the switch silicon or prove identical firmware port numbering (see below). See
> `video/hardware_rendering.md` for the full hardwareid→switch-driver map.

| Port | Connected Node |
|------|---------------|
| 0 | RSI |
| 1 | AMP |
| 2 | CGM |
| 3 | TCP |
| 5 | Host (A11/IHU) |

### Shipped switch speeds — [C], 2026-11-13

Corrected from the actual `firmware/update_packages/Y175/extracted/85759612` package
(relative to `aaos/gm_aaos/2024_Silverado_ICE`), not inferred from the bus link rate.
This 1,497,632-byte ETH_SWITCH module contains the embedded name
`MVL88Q5050_globalB_234702AB_02_09_1003.bin`, matching the module identity already recorded in
[`firmware_versions.md`](firmware_versions.md) and [`ota_programming_roles.md`](ota_programming_roles.md).
Decoded `portCfg.intfCfg` (key starts at byte offset 182627, decimal):

| Config `intf` | `mode` (enabled) | `br` | `speed` (literal string) |
|---------------|------------------|------|--------------------------|
| 0, 1 | true | slave | `100` |
| 2 | true | master | `100` |
| 3, 4 | true | slave | `100` |
| 5 | true | auto | `1000` |
| 6, 8 | false | auto | `auto` |
| 100, 101 | false | slave | `100` |

**[C] The switch is multi-speed-capable, not hardware-limited to 100 Mbps.** GM's shipped
configuration fixes the vehicle-facing automotive-Ethernet entries (0–4, 100, 101) at
`"speed":"100"`, not `"auto"`; 100/101 are disabled. Exactly one entry, enabled `intf 5`,
is fixed at `"speed":"1000"`. Thus the vehicle's 100BASE-T1 links run at 100M by explicit
firmware configuration on silicon that also supports gigabit operation. The same package
contains the runtime CLI help `avb port speed set <port> <auto|100|1000>` at byte offset
164019: 1000 is an explicit driver/CLI option, not just a datasheet capability. This generic
command syntax does not independently establish that every physical T1 PHY accepts 1000,
or that changing a setting alone would make a vehicle endpoint operate at gigabit speed.

**[?] Strong inference:** `intf 5` is the internal SoC-facing uplink to the Intel I210 GbE
MAC: its sole 1000 setting fits the I210's documented 1 Gbps link and the existing table's
“Port 5 = Host” label. The file does not name `intf 5` as the host uplink; that identity is
not independently proven, especially while the numbering reconciliation below remains open.

### Configured VLANs and port-numbering reconciliation — [?] OPEN, 2026-11-13

**[C] Configuration evidence:** the same package's `dot1qCfg.vlanCfg` (key at byte offset
182024) contains these decimal bitmasks. Bit positions below belong to the config's own
numbering domain, not a proven mapping to the human-readable Port table above.

| VLAN | `tag` | `untag` | Tagged config bit positions |
|------|-------|---------|-----------------------------|
| 1 | 0 | 511 | none; native/default VLAN, all nine bits 0–8 untagged |
| 2 | 43 | 0 | 0, 1, 3, 5 |
| 4 | 47 | 0 | 0, 1, 2, 3, 5 |
| 5 | 47 | 0 | 0, 1, 2, 3, 5 |
| 6 | 13 | 0 | 0, 2, 3 |
| 9 | 10 | 0 | 1, 3 |

- **[?] VLAN 9 configured but never observed live:** full, unfiltered VLAN-ID sweeps on both
  the Bus-2/pins-3-4 tap and X11-pins-1/2 tap found only `{untagged, 2, 4, 5}`. Canonical
  live evidence: `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §14 in the
  `analysis/Y175_2026-11-02` tree. Open alternatives: VLAN 9 is tagged on ports not yet
  physically tapped; it carries a conditional/rare service; or it is defined but unused on
  this build. No alternative is selected.
- **[?] Numbering domains NOT reconciled:** the table above labels Port 2 as CGM, associated
  in the existing docs with Bus 2, where the VLAN 2 AVB flood is confirmed. Yet config VLAN
  2's mask 43 excludes bit 2 and includes only {0,1,3,5}. The config `intf`/bit indices may
  use a different domain (e.g. internal MDIO/register indices versus physical-connector
  labels), or one of the existing port-to-bus mappings may be wrong. **Do not transfer port
  numbers between this config and the table until tested.** A future bench session needs
  per-port live captures to reconcile the schemes; no physical-port assignment is resolved here.

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

**2026-11-14 scope:** both physical T1 taps reached the Android guest, but
none of the historically documented GHS candidates answered ARP. This does
not establish that GHS is stopped or absent. The direct Android diagnostic
listener did complete level-1 SecurityAccess; see the
[validated T1 sequence](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
A separate authenticated hard-reset request returned `7F 11 25` after about
30 seconds of pending replies; no Android reboot was observed. See the
[ECUReset result](../diagnostics/diagnosticsd_security_access.md#live-t1-ecureset-validation-2026-11-14).
The later [USB-logcat/UART correlation](../diagnostics/diagnosticsd_protocol.md#concurrent-uart-and-usb-logcat-correlation-2026-11-14)
shows an AAOS converter gap: wire 11 and 23 become DIAG_UNKNOWN_SERVICE.
Their NRC-25 replies therefore do not establish a physical subnet/GHS timeout
or transparent MDI2 equivalence.
The later [full DID-number sweep](../diagnostics/diagnosticsd_dids_and_dtc.md#exhaustive-did-number-sweep-and-extended-enumeration-2026-11-14)
verified 135 readable DIDs at level 09. This covers every 16-bit DID number
in that state; it does not establish every UDS service or programming route.
A later 03D8 start enabled AM/audio and made 4775 readable, bringing the
observed union across states to 136. The final explicitly requested 0249
calibration clear also completed: live module identities changed to 70008/00
while MEC remained FF. This confirms selected direct-T1 control operations;
programming-session entry still failed its authenticated vehicle-state gate.
See the [completed clear](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).

| Address | Node | Notes |
|---------|------|-------|
| 172.16.4.100 | VCU_AGVM / Android (vlan4 face) | this device |
| 172.16.4.14 | **ACP (Application Control Processor)** | Historically configured as a permanent neighbor. Corrected 2026-11-14: no external T1 ARP reply in the current bench test; see the diagnostic reference below. |
| 172.16.4.107 | Historical RTOS/GHS diagnostic candidate | Corrected 2026-11-14: the asserted symmetric diagnosticsd socket is disputed, not established. No external T1 ARP response or completed connection in the latest bench test. Historical identity is not proof of current reachability. |
| 172.16.4.112 | CGM_OTA (vlan4 face) | active, TTL=64 (Bosch JuP1, Linux) |
| 172.16.4.1 | **TCP (vlan4 face)** | **live 2026-07-01** — see note below |
| 172.16.4.12 | EOCM_HCP_SECONDARY / EOCM_HCP_2 | code-referenced |
| 172.16.4.13 | EOCM_HCB | code-referenced |
| 172.16.4.15 | EOCM_HCP_HOST / EOCM_HCP_1 | code-referenced |
| 172.16.4.104, .110 | additional vlan4 ECUs | code-referenced, not live on bench |

> **TCP module now dual-homed on vlan4 (2026-07-01).** `172.16.4.1` was
> previously dead on bench (see prior revision of this table). With the
> telematics module's cellular antenna connected, it answers TCP connects on
> ports 9010 (`DeviceInformation`, instant accept) and 9012 (`RemoteReflash`,
> instant accept); an unrelated/bogus port on the same host times out with no
> RST (silent filter, not a routing artifact — confirmed against both a truly
> dead vlan4 IP and a known-live host that does send RST for closed ports).
> Its MAC (`02:04:00:00:02:00`) is identical to `192.168.1.102` (TCP, see
> [`fsa_protocol.md`](fsa_protocol.md#deviceinformation-instanceid--partition)),
> confirming it's the same physical module, not a coincidence. Both new ports
> accept-then-silently-close under the standard single-client-limit behavior
> (`com.gm.domain.server.delayed` already holds the legitimate session) — this
> matches the already-documented vlan5-side behavior for the same instance,
> not a sign of a broken/proxy service. Working theory: the module only fully
> activates its network stack (including the vlan4 face) once it has an active
> cellular link to maintain. Not yet confirmed causally (would need an
> antenna-disconnect re-scan to see `172.16.4.1` go dark again).

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
| 0.0.0.0 (Y175 snapshot) | 6363 | TCP | **AVB audio daemon** (uid=1041 audioserver) — init-owned listen socket, text IPC bus for AVB audio routing; arbitrary data → `"ERROR"`. Low value. (Was "Unknown".) |
| 0.0.0.0 | 7000 | TCP | **AirPlay/AirTunes 320.17.8** (Cinemo `libNmeCarPlay` r14), br0/192.168.5.1, uid=1001000. `GET /` → `404; Server: AirTunes/320.17.8`. CarPlay audio bridge — see [`audio/carplay_audio_pipeline.md`](../audio/carplay_audio_pipeline.md). (Was mislabeled "ADB"; network ADB uses a separately configured listener.) |
| 0.0.0.0 | 49156 | TCP | **diagnosticsd UDS-over-TCP bridge** (root; PID is snapshot-dependent). Direct T1 level-1 SecurityAccess is live-verified with tester F4 and extended session (2026-11-14); direct forwarding to a GHS/RTOS endpoint is unproven. See [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md). (Was "Unknown".) |
| 192.168.1.100 | 9002 | TCP | **FSA RemoteModuleHMI** (serviceId 1007), IPv6-mapped IPv4 — guest's own FSA server (see [`fsa_protocol.md`](fsa_protocol.md)) |
| 192.168.1.100 | 9010 | TCP | **FSA DeviceInformation** (serviceId 1001), IPv6-mapped IPv4 |
| 192.168.1.100 | 9016 | TCP | **FSA NetworkAccessManager** (serviceId 1026), IPv6-mapped IPv4 |
| 127.0.0.1 / 192.168.5.1 | 53 | TCP/UDP | dnsmasq (loopback + br0 WiFi-AP side) |

**Network ADB correction, 2026-11-15:** the working radio listener is **TCP 9040**,
verified over T1; 5555 is the standard ADB port, not the verified accessible
bench port. The shipped firewall uses default-deny with source/destination,
interface and port allow-rules. A listener on 5555 alone does not grant access.
The working host setup uses a source-bound loopback relay on **19040** to the
radio's 9040 listener, preserving an allowed VLAN-5 source identity. These
are configured bench ports, not immutable factory service assignments.
Canonical procedure: `BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.2 in
the existing Y175 analysis/source_notes tree. No firewall change was needed.

> **Re-verified against live `enumeration/Y181/jun2026/` capture.** 9002/9010/9016 listen bound to the IHU's own **192.168.1.100** (IPv6-mapped IPv4), *not* 192.168.1.1 — the guest has no `.1` interface or route. **7000 is listening** (`0.0.0.0:7000` + `*:7000`; this is the AirPlay/AirTunes listener per the table above, NOT ADB; the standard ADB port is 5555, but working T1 ADB uses 9040; corrected 2026-11-15), and **9010 is a listener**, not outbound-only. DNS (dnsmasq, TCP/UDP 53) is served locally on **127.0.0.1** and **192.168.5.1 (br0, the WiFi-AP bridge)**.
>
> The earlier apr2026 note (only 9002/9016 @ .1; 9010 outbound; 7000 gone; DNS on .102) reflected one snapshot and is **withdrawn** — listener set varies with projection-session state; the Jun-2026 live set above supersedes it.

> `[C] live-Y175 2026-10-05: port table CONFIRMED on Y175 with two bind-address adjustments
> [net_sockets.txt]. **6363** LISTEN uid 1041 (audioserver) — live bind is **`0.0.0.0` only**
> (no separate 127.0.0.1 listener seen). **49156** LISTEN uid 0 (root) CONFIRMED `0.0.0.0`.
> **7000** LISTEN uid 1001000 (u10_system) CONFIRMED listening (`0.0.0.0:7000` + `:::7000`) —
> ADJUST: live bind is **wildcard `0.0.0.0`, not specifically `192.168.5.1`/br0** (it is reachable
> on br0 by virtue of the wildcard). **9002 / 9010 / 9016** all LISTEN uid 1000 (system) bound to
> `::ffff:192.168.1.100` (IPv6-mapped IPv4) CONFIRMED — 9010 IS a listener (not outbound-only).
> **53** dnsmasq (uid 1052) on `127.0.0.1` and `192.168.5.1` CONFIRMED. Note: the extra loopback/
> wildcard listeners present live (9112, 7011, 36103, 41365, 9001-9004) are the carlink PoC app
> `zeno.gmccpa` (uid 1010120), not platform services.*

---

### CarPlay mDNS fingerprint (2026-11-13)

**Separate post-factory-reset capture, 2026-11-14:**
`radio-en12-20261114.pcapng` contains CarPlay-control queries but no mDNS
responses or SRV advertisements. Android-12 DHCP Discover traffic is also
present. Its `_adb*` service names are queries from the other source, not
radio ADB advertisements. These observations do not supersede the earlier
advertised port-7000 fingerprint below; they describe a different, partial
boot capture. See the
[capture analysis](../diagnostics/diagnosticsd_routines_and_recovery.md#partial-post-factory-reset-ethernet-capture-2026-11-14).

**[C]** Live vlan5 mDNS at radio boot, in the same clean power-on capture described in
[Ethernet boot timing](../runtime/boot_timing.md#y175-ethernet-capture-boot-timing-2026-11-13),
advertised `CarPlay._airplay._tcp.local.` with SRV target `Android.local.:7000`.
A separate `_carplay-ctrl._tcp.local` PTR query pattern was also observed; the query
alone did not establish a second service advertisement. This added advertisement/TXT
detail to the port-7000 identification already recorded above and in
[VERIFICATION.md](../VERIFICATION.md), rather than a new port identification.

| TXT key | Observed content (sensitive identifiers redacted) |
|---|---|
| `deviceid` | `<AIRPLAY_DEVICE_MAC>` |
| `features` | `0x4040280,0x61` |
| `flags` | `0x4` |
| `model` | `myChevrolet` |
| `pi` | `<AIRPLAY_PERSISTENT_UUID>` |
| `srcvers` | `320.17.8` |

**[C]** `model=myChevrolet` was consistent with the already-documented
`net.hostname=myChevrolet` property above. `<AIRPLAY_DEVICE_MAC>` denotes the captured
TXT `deviceid`; `<AIRPLAY_PERSISTENT_UUID>` denotes the captured `pi` UUID.
The `pi` value was a persistent, stable per-device identifier, unchanged between observed
mDNS announcements; this observation did not establish stability across resets or
reprovisioning. Both identifiers received the project's existing sensitive-identifier
handling and were redacted here to avoid echoing them into externally pushed material.

**[?] Unexplained deviceid/wlan0 discrepancy:** the advertised deviceid closely resembled
the documented `wlan0` MAC, but its final octet was `a0`, versus `9e` in the
[existing wlan0 capture](../enumeration/Y175/raw/network_interfaces.txt)
(also recorded as `persist.sys.wifi.mac_addr` in the companion properties capture).
They were **not identical**. The interface relationship remained unverified; this was
neither established as the same interface nor dismissed as a typo.

---

## VIP-SoC IPC

- **Transport:** HDLC over UART `/dev/ttyS1`
- **Channels:** 20 IPC channels (numbered 1-20; confirmed: `hardware/teardown.md` IPC Channel Map)
- **Protocol:** Version 16
- **Line rate:** 1 Mbps (VIP `IPCServer`; confirmed: `hardware/teardown.md`. The earlier "4104" was a misread of the ~4104 ms channel-XON timing in the VIP UART log, not a baud rate)
- **PLC:** Power-level control / VIP↔SoC power handshake; the earlier
  "Programmable Logic Controller" expansion was unsupported (corrected 2026-11-15).
- **MEC:** Manufacturer Enable Counter; see [security.md](security.md#mec-manufacturer-enable-counter).
  The earlier "Mode/Event/Condition" expansion was incorrect (corrected 2026-11-15).

### IPC Channel Assignments

Corrected 2026-11-15 against the [owning UART-derived channel map](../hardware/teardown.md#ipc-channel-map-from-vip-uart-log).
The previous contiguous channel ranges contradicted that source.

| Channel | Observed role |
|---------|---------------|
| 2, 16 | PlayAnimation events |
| 5 | Ethernet state |
| 6 | Diagnostics (UDS SID/DID) |
| 8 | Calibration download |
| 9 | ProtoKey |
| 13 | OTA / remote reflash |
| 14 | Boot reason |
| Others | Initialization/XON observed; no complete service assignment established |

The VIP MCU communicates with the Intel SoC via a dedicated UART link using HDLC framing. The 20 IPC channels carry power management commands, CAN messages, calibration data, and vehicle state information between the two processors.

---

## UART Devices

| Device | Owner | Purpose |
|--------|-------|---------|
| /dev/ttyACM1 | root; crw-rw-rw- | Historical MCP2200 identity; live SELinux label `sxm_device`, not an unrestricted generic debug endpoint |
| /dev/ttyS0 | bluetooth:bluetooth | Bluetooth HCI |
| /dev/ttyS1 | root:root | VIP IPC (HDLC) |
| /dev/ttyS2 | root:root | serial_device / Android guest console (`console=ttyS2`) |
| /dev/ttyS3 | root:root | Live SELinux label `display_panel_device`; function not independently traced |

> `[C] live-Y175 2026-10-05: CONFIRMED with one label note [dev_listing.txt]. `ttyACM1` is indeed
> `crw-rw-rw-` (world-writable), owner root — but its SELinux label is **`sxm_device`** (SiriusXM),
> not a generic debug node; "MCP2200 debug" is the hardware identity, `sxm_device` is how policy
> labels it. `ttyS0` bluetooth (`bluetooth_serial_device`), `ttyS1` root (`ipc_serial_device` = VIP
> IPC), `ttyS2` root (`serial_device`) all CONFIRMED. `ttyS3` is root `display_panel_device` live
> (not blank). No `ttyACM0` present.*

---

## USB Identifiers

| Device | VID | PID | Notes |
|--------|-----|-----|-------|
| GM IHU (iAP) | 0x2996 | 0x0120 | iAP2 USB role |
| **Aptiv H2H (Head-to-Head) Bridge** | 0x2996 | `0x0100`–`0x0105` (match table; this radio enumerates `0x0105`) | **On-radio** USB bridge device — NOT a cross-ECU link. `dabridge` (kernel, GM custom) is a host-side driver that matches this VID/PID on the internal USB tree and, once bound, bridges a chosen host-side port to a device-side port (`/sys/bus/usb/drivers/dabridge/bridgeport`) so the physical xHCI host stays up for the hub/accessory tree while a virtual UDC (`dabr_udc.0`) presents the ADB (and CarPlay/AA) gadget on that one bridged port. `RDMSADBHandler` writes `1-6.3` (dev port) here on `ADB_Enable`. (= the "GM proprietary" 0x0105 entry.) |
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

> `[C] live-Y175 2026-10-05: CONFIRMED [props, mounts.txt]. `sys.usb.controller=dabr_udc.0`,
> `sys.usb.configfs=1`, `sys.usb.config=adb`, `persist.sys.usb.config=adb`;
> `sys.dabridge.host.portnum=1-6.0`, `sys.dabridge.dev.portnum=1-6.3` (matches the H2H bridge
> table above and FAQ §20). FunctionFS mounts present and rw: `iAPClient /dev/ffs`,
> `adb /dev/usb-ffs/adb`, `mtp /dev/usb-ffs/mtp`, `ptp /dev/usb-ffs/ptp`. Note Y175 current role is
> **device/adb** (this is the bench ADB session), not the boot-default host role.*

---

## NFSA / FSA (Feature Service Architecture)

> **Full protocol spec:** [`platform/fsa_protocol.md`](fsa_protocol.md) — wire
> format (20-byte BE header, magic `0x5AA5`, protobuf payload), opTypes,
> functionIDs, the connection handshake, the complete **service catalog** (port
> → serviceId → partition), recovered protobuf field tables, and live service
> sessions (RemoteModuleHMI, NetworkAccessManager, DeviceInformation,
> DisplaysCoordination). GM's code names this `com.gm.fsa.service` / `com.gm.nfsa.*`
> — "NFSA" here and "FSA" there are the same protocol.

NFSA/FSA provides the vehicle-internal network communication layer between the IHU and other vehicle computing nodes over VLAN 5. The following historical snapshots show IHU server and client endpoints;
this is not a complete or invariant six-port inventory:

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

> `[C] live-Y175 2026-10-05: client-side targets ADJUSTED from live snapshot [net_sockets.txt].
> The only non-LISTEN FSA rows captured are uid 1000 (system) in **SYN_SENT to 192.168.1.112:9010
> and 192.168.1.112:9018** (`.112` = CGM per the switch-port table, NOT `.102`), plus an
> established `192.168.1.100:9016 <-> 192.168.1.100:58814` loopback-on-vlan5 pair. The `.102:9005/
> 9012/9018` client targets were **not observed** in this capture; not refuted, mark
> UNVERIFIABLE-FROM-LIVE. **Confirmed bench artifact:** this is an out-of-vehicle bench (Radio +
> Display + GM USB receptacles, no vehicle bus/ECUs), so `.112` (CGM) and `.102` (TCP) are external
> vehicle nodes that are simply not present — the SYN_SENT to `.112:9010/:9018` is the IHU reaching
> an absent peer, expected, not a defect. See BENCH CONTEXT in `LIVE_Y175_FACTS.md`.*

---

## GM Cloud Endpoints

| Endpoint | Port | Purpose |
|----------|------|---------|
| vtmpub.oboservices.mobi | 443 | OTA / OMA-DM updates |
| vehicle.api.gm.com | 443 | Vehicle registration |
| vehicle.api.gm.com | 20445 | Security logging |
| vehicle.api.gm.com | 20647 | Auth / personalization |

Telematics (CGM module) is a separate vehicle node. The historical cloud
endpoint list above is not a fresh connectivity test, and end-to-end cloud
availability/dependencies were not established by the isolated radio bench
(corrected scope, 2026-11-15).

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
| Calibration / diagnostic authentication | Separate mechanisms: stock calibration containers use RSA-2048/SHA-256 signatures; DPS SecurityAccess has a backend-assisted CMAC path. Reusable server-key provisioning is unproven. See [seed/key and calibration signature reference](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md). Corrected 2026-11-15. |
| IPC | 20 channels (1-20) on /dev/ttyS1, HDLC protocol v16, 1 Mbps line rate |

---

## CAN Bus

- **ECU count:** historical inventory lists 24; not a universal count or a
  live bench discovery result.
- **CSM address:** 0x80
- **Gateway:** VIP MCU (RH850/F1K) acts as CAN gateway between vehicle bus and SoC

The VIP MCU bridges CAN messages to the Intel SoC over the HDLC IPC link, translating vehicle bus traffic into structured IPC messages for Android services. The module at CAN address 0x80 (CSM = Center Stack Module) is the radio/head unit itself; the audio **amplifier** is a *separate* AVB endpoint (`192.168.1.103`, `AMP_ETH`) that the radio streams to over Ethernet AVB. *(Corrects earlier text calling 0x80 "the primary audio amplifier endpoint".)*

---

## WiFi Configuration

The historical WiFi role map below is not proof of three simultaneously
active interfaces. The Y175 snapshot showed wlan1/wlan2 and no wlan0
(corrected in the primary summary, 2026-11-15):

| Interface | Mode | Usage |
|-----------|------|-------|
| wlan0 | Historically assigned STA | Absent in the cited Y175 snapshot; creation on demand is unverified |
| wlan1 | AP role supported by observed hotspot state | Provisioned SSID varies; adapter-specific use is configuration-dependent |
| wlan2 | Historically assigned P2P | Interface observed; exact live role/bridge membership not established |

> `[C] live-Y175 2026-10-05: ADJUSTED [net_ifaces.txt, props]. Live shows only **wlan1 and wlan2**
> up (both inet6 link-local only); **no `wlan0` STA interface present** in this capture — the
> three-concurrent-interface claim is not borne out on Y175 at capture time (wlan0 may be
> created on demand). `hostapd_bcm` running confirms the AP role is active and br0 (`192.168.5.1`,
> dnsmasq) is up, consistent with wlan1=AP. `persist.sys.wifi.only2g=1` CONFIRMED. SSID
> `myChevrolet 32D4` UNVERIFIABLE-FROM-LIVE (bench unit's SoftAP was `benchd89`; no SSID string in
> capture).*

---

## Ethernet AVB

### VLAN 2 audio transport reference

This section is the consolidated VLAN-2 wire reference. Findings below are
Audio recovery and usage-mapping measurements are dated 2026-11-15.
Hardware/software inventory and earlier captures retain their own dates below;
not every item in this section was freshly measured on that date.

- **NIC:** Intel I210, 1Gbps (only `I210` appears in artifacts; `WGI210CL` marking is prose-only; "I211" was an unverified near-twin reading — see `hardware/teardown.md`)
- **gPTP role:** Configured grandmaster; wire transmission observed, elected role not independently decoded.
- **AVB streamhandler:** v3.2.7.2 (GM3/CSM)
- **External audio endpoint:** Bose amplifier. Physical speaker count and the
  correspondence between AVTP sample positions and speaker outputs are unverified;
  the earlier four-speaker claim was not supported by the capture.

Firmware configures the IHU as gPTP grandmaster for the AVB domain feeding
the external Bose amplifier. Captured gPTP frames prove transmission, but
packet presence alone does not establish elected grandmaster status
(corrected evidence scope, 2026-11-15).

> **[2026-11-13] Live confirmation of gPTP transmission.** The configured role above was
> previously grounded in firmware structure (`igb_avb.ko`, `daemon_cl -GM` grandmaster — see
> `vehicle_network.md` §"Automotive Ethernet"), not a direct capture. A live Bus 2 T1 tap
> capture this session saw **146 frames** from the radio's own MAC to the IEEE 802.1 PTP
> multicast address `01:80:c2:00:00:0e` — a direct packet-level confirmation that the radio is
> transmitting gPTP on the wire. Same session also decoded the VLAN 2 AVB flood (see
> `vehicle_network.md` open item #1) as **3 IEEE-1722 AAF audio streams + 1 TSCF/ACF control
> stream**, not a generic "4 audio channels." See
> `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §5 in the `Y175_2026-11-02`
> analysis tree.

### Live AVTP player audio recovery 2026-11-15

**Audio payload recovered and matched to a known source.** While the owner
looped `sample-55s.mp3` in the radio's Audio Player, a 70-second live T1
observation decoded VLAN-2 IEEE-1722 AAF payloads in memory. The source MP3
is stereo **44.1 kHz**, duration **54.949887 s**. No raw packet file, Ethernet
addresses or stream identifiers were saved with the audio artifacts.

Three AAF streams were present. The **768-byte-payload stream** had 52,448
packets over approximately 69.930 s; 51,745 packets contained nonzero data.
The 512- and 128-byte-payload streams were entirely zero-filled during this
observation. All three streams had zero observed sequence discontinuities.

The active payload is **six interleaved signed 16-bit big-endian PCM
positions at 48 kHz**, with **64 sample frames per packet**, consistent with
approximately 750 packets/s. Positions **1 and 2** carried the player audio;
positions 3–6 were zero-filled. This describes payload positions, not a
verified Bose speaker-position map. The generic dissector's user-specified
sample-rate / channel-count fields were insufficient: packing and rate
were checked against packet cadence and the decoded reference waveform.

**Sample-rate scope, 2026-11-15:** the extracted audio policy configures the
media output mix port and other named output mix ports as 48 kHz PCM16;
some device-port profiles also list lower rates. The 44.1 kHz source reaching
T1 as 48 kHz confirms conversion somewhere inside the radio, but does not
isolate the converting component. Higher-rate media downsampling has not
been tested. Neither the active transport rate nor the policy establishes
the Bose amplifier's maximum accepted rate or internal DSP/DAC rate.
Source: extracted Y181 `pulled_files/audio_policy_configuration.xml` in the
existing `analysis/adb` enumeration tree.

The MP3 was decoded/resampled to 48 kHz for comparison. Aligned half-second
windows at recovered times **0, 10 and 30 s** had normalized waveform
correlations **0.999960, 0.999923 and 0.999959**, respectively. This directly
confirms that the player's audio reaches the external T1 stream; it is not
merely an idle audio-format advertisement. It does not establish which
component originally brought up the transport or prove amplifier playback.

A further half-second comparison at recovered time **60 s**, after the
player's loop transition, correlated **0.999939** after allowing an
additional **0.938104 s** timing offset. This is consistent with a short
player loop delay; the AVTP sequence remained continuous, so no transport
packet loss was observed at that transition.

Audio-only outputs were created in the owner's `Downloads/T1_audio`
directory: a **12-second stereo WAV preview**, **69.930667-second stereo
WAV**, the full six-position WAV, individual active-position mono WAVs and
the unwrapped six-position `.s16be.pcm` payload. WAVs use 48 kHz signed
16-bit little-endian PCM for macOS playback; amplitude was not normalized.
macOS `afinfo` recognized the preview as a valid stereo Int16 WAVE file.
The raw PCM file contains sample payloads only, not Ethernet/AVTP headers or
a directly replayable Bose wire stream. No exact physical speaker-channel
assignment or amplifier control/SRP procedure was recovered in this step.

### Public AAOS usage to AVTP mapping 2026-11-15

The lightweight [AAOS Audio Probe](../research/tools/aaos_audio_probe/README.md)
exercised **all 16 public Android 12 usage IDs**, including UNKNOWN and the
four deprecated notification variants. Each two-second probe received focus;
requested/effective usage IDs remained equal in the retained log observations.
Live decoding inspected all three AAF streams. Positions below are one-based
within the **768-byte stream**, not physical speaker labels.

| Usage ID | AudioAttributes usage | Actual AudioTrack bus | Nonzero PCM positions |
|---:|---|---|---|
| 0 | UNKNOWN | `bus0_media_out` | 1, 2 |
| 1 | MEDIA | `bus0_media_out` | 1, 2 |
| 2 | VOICE_COMMUNICATION | `bus4_call_out` | 1, 2 |
| 3 | VOICE_COMMUNICATION_SIGNALLING | `bus4_call_out` | 1, 2 |
| 4 | ALARM | `bus5_alarm_out` | 4 |
| 5 | NOTIFICATION | `bus6_notification_out` | 4 |
| 6 | NOTIFICATION_RINGTONE | `bus3_call_ring_out` | 1, 2 |
| 7 | NOTIFICATION_COMMUNICATION_REQUEST (deprecated) | `bus6_notification_out` | 4 |
| 8 | NOTIFICATION_COMMUNICATION_INSTANT (deprecated) | `bus6_notification_out` | 4 |
| 9 | NOTIFICATION_COMMUNICATION_DELAYED (deprecated) | `bus6_notification_out` | 4 |
| 10 | NOTIFICATION_EVENT (deprecated) | `bus6_notification_out` | 4 |
| 11 | ASSISTANCE_ACCESSIBILITY | `bus2_voice_command_out` | 1, 2 |
| 12 | ASSISTANCE_NAVIGATION_GUIDANCE | `bus1_navigation_out` | 3 |
| 13 | ASSISTANCE_SONIFICATION | `bus7_system_sound_out` | 4 |
| 14 | GAME | `bus0_media_out` | 1, 2 |
| 16 | ASSISTANT | `bus2_voice_command_out` | 1, 2 |

Media **left-only** isolated position 1; **right-only** isolated position 2.
The 128- and 512-byte AAF streams remained zero-filled throughout these tests;
positions 5/6 in the 768-byte stream remained zero. Alarm/notification/system
results establish another logical mix position, not a center/rear/chime speaker.
Earlier four-second tests independently confirmed media/navigation/assistant/call.
The call path changed amplitude relative to the source, so source amplitude is
not a direct predictor of amplifier gain. Real call state, simultaneous mixing,
volume groups, balance/fade and proprietary tags remain separate experiments.

The live policy exposes **12 output buses**, numbered 0–8 and 11–13:
`media`, `navigation`, `voice_command`, `call_ring`, `call`, `alarm`,
`notification`, `system_sound`, `ecall_ring`, `mix_unduck`, `audio_cue`,
`high_priority_mutex` (each named `busN_<name>_out`). The final four have not
been driven by a verified application-to-wire test. Bus count is not zone count.

The device also reports five supported **system** usages: CALL_ASSISTANT (17),
EMERGENCY (1000), SAFETY (1001), VEHICLE_STATUS (1002), ANNOUNCEMENT (1003).
The live dynamic-policy criteria list 1000–1003 on `bus0_media_out`, but this is
**configuration evidence only**, not a measured privileged playback result.
Android 12 defines these using `setSystemUsage`; public `setUsage` is not an
interchangeable way to test them. The probe attempted all five via `setSystemUsage`: each returned
`focus_result=0` (not granted), so no tone or wire route was produced.
These are attempted but **unmapped** system paths. The normal probe does not
grant itself privileged routing permission or change hidden-API policy. Usage 15 is not a
public playback usage in this SDK; no route is asserted for it. See the
[Android 12 AudioAttributes source](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android12-release/media/java/android/media/AudioAttributes.java)
and [AAOS audio configuration](https://source.android.com/docs/automotive/audio/audio-policy-configuration).

### VLAN, stream inventory and packet layout

| Captured traffic | Encapsulation | Measured content / limitation |
|---|---|---|
| AAF audio, subtype `0x02` | 802.1Q **VID 2, PCP 2**, EtherType `0x22f0` | Three distinct stream IDs; continuous PCM, including silence |
| TSCF, subtype `0x05` | 802.1Q **VID 2**, EtherType `0x22f0` | Small control frames; payload semantics unresolved |
| gPTP | **Untagged**, EtherType `0x88f7` | Clock traffic observed alongside tagged audio |

VLAN 2 audio is raw Ethernet AVTP, **not IP/UDP/RTP**. A UDP listener on the
service VLAN cannot receive/decode it. Stream IDs and destination MACs must
be learned from the actual link; the size labels below are local aliases,
not fixed protocol-assigned stream numbers. Classification must include
subtype, stream ID and declared payload length.

| Local stream alias | AAF payload bytes | Cadence | Packing evidence |
|---|---:|---|---|
| A768 | 768 | Approximately 750 packets/s | Validated 64 frames × 6 positions × 2 bytes, 48 kHz PCM16 BE |
| A512 | 512 | Approximately 750 packets/s | Silent; 64 × 4 × 2 is an **inference**, not validated channel packing |
| A128 | 128 | Approximately 750 packets/s | Silent; 64 × 1 × 2 is an **inference**, not validated channel packing |

For a tagged A768 frame (offsets exclude preamble and start at destination MAC):

| Byte offset | Bytes | Field / observed value |
|---:|---:|---|
| 0 | 6 | `<AUDIO_DESTINATION_MAC>` |
| 6 | 6 | `<RADIO_SOURCE_MAC>` |
| 12 | 2 | TPID `81 00` |
| 14 | 2 | TCI `40 02`: PCP 2, DEI 0, VID 2 |
| 16 | 2 | EtherType `22 f0` |
| 18 | 1 | AAF subtype `02` |
| 19 | 1 | Observed flags `81`: stream-ID valid, timestamp valid |
| 20 | 1 | Sequence number, modulo 256 |
| 21 | 1 | Timestamp-uncertain/reserved byte; observed `00` |
| 22 | 8 | `<STREAM_ID>` |
| 30 | 4 | AVTP timestamp; wrap and validity must be handled |
| 34 | 1 | Format `04` (PCM16) |
| 35 | 2 | Raw rate/channel word `00 05` |
| 37 | 1 | Bit depth `10` (16 decimal) |
| 38 | 2 | Stream data length `03 00` (768) |
| 40 | 2 | Observed tail `00 06` |
| 42 | 768 | Interleaved PCM sample bytes |

The corresponding format/length/tail bytes were `04 00 05 10 02 00 00 04`
for A512 and `04 00 05 10 00 80 00 01` for A128. A generic AAF dissector reports
user-specified sample rate and five channels from `00 05` **for all three**.
That header interpretation conflicts with empirically validated A768 packing.
Do not silently rewrite the header as six channels or assume the final byte is
a standardized channel count merely because its value matches the observed packing.
Preserve the raw bytes when implementing compatibility and resolve this vendor
convention before transmitting to an amplifier.

A768 payload addressing is `payload[2 * (6 * frame + position)]`, with
zero-based `frame=0..63`, `position=0..5`. Each signed sample is big-endian.
An illustrative **synthetic** sample frame is:

```text
03 e8  fc 18  00 00  00 00  00 00  00 00
 +1000  -1000      0      0      0      0
   P1     P2     P3     P4     P5     P6
```

After removing Ethernet/VLAN/AVTP headers, concatenate complete payloads by
stream ID and decode with this interleaving. Do not include padding/FCS as
PCM. A768's tagged frame is 810 captured bytes without FCS (18 + 24 + 768).
Sequence gaps require explicit handling; concatenation without gap handling
shortens audio and corrupts timing. The example is a payload decoding recipe,
not sufficient instructions for a synchronized AVTP talker.

The TSCF dissector's suggested LIN/ACF interpretation previously reported a
length mismatch (`expected: 1024 bytes, available: 12 bytes`). Its control
payload must remain **undecoded** until corroborated; this is not evidence
that ordinary LIN frames traverse this link.

### Diagnostic tone correlation follow-up (2026-11-15)

The [UDS live-control reference](../diagnostics/diagnosticsd_protocol.md#live-bench-controls-2026-11-15)
records four speaker selectors requesting475Hz. Two memory-only T1
correlation captures (74,126 and59,045 captured frames, zero kernel drops)
found all three AAF payloads zero in their selected LF/RF/RR/LR windows.
However, their same-run440Hz AAOS media-probe windows were also zero. These
experiments therefore do not establish missing tone transport or a speaker
map: the required known-signal positive control was not observed. Probe logs
separately showed focus granted and bus0_media_out, which is Android-side
admission, not proof of the downstream wire route.

A separate35,176-frame/zero-drop capture after source/tuner activation found
nonzero A768 bytes, with A128/A512 stillzero; it did not independently
identify440Hz. Changing source/backend state and restarting the probe were
not isolated variables, so no single cause for the differing result is
established. No raw packets or new audio files were saved. Earlier
known-source/usage mappings above retain their original measurement scope.

Current Java tracing shows tone frequency and channel-mute readbacks come
from Settings.Global even though setters also forward toward GMAudioService
and vendor IGMAudioControl. This reinforces why a positive UDS response plus
readback cannot establish acoustic output. A later three-second capture
again showed three AAF sizes plus60-byte subtype5 TSCF frames; the generic
ACF decoder reported type3 with an invalid1024-byte length. This remains an
unresolved vendor-control format, not a demonstrated LIN/CAN record.

### What a replacement endpoint still needs

A replacement amplifier can already extract the verified audio payloads.
A replacement radio must additionally produce the expected wire headers,
stream identity, sequence and presentation timing, and compatible control.
Neither direction is a verified drop-in replacement yet. Missing evidence:

- Bose output-speaker routing, EQ/crossover, gain/limiter and balance/fade behavior.
- Meaning and use of A128/A512, A768 positions 5/6 and proprietary audio buses/tags.
- AVTP presentation offset, clock recovery and exact timestamp semantics.
- TSCF control payloads, stream admission/discovery and whether SRP/MSRP or
  other negotiation is required with the actual amplifier attached.
- Amplifier wake/power/mute and vehicle/CAN sideband dependencies.

The measured flow is AAOS usage → logical bus → shared transport positions →
external amplifier. Final physical speaker processing is expected downstream,
but the captured traffic alone does not establish how much processing Bose
performs or exclude additional speaker-specific streams in other vehicle modes.

### Physical Automotive-Ethernet bus map (GM service data)

The AVB/Ethernet links are point-to-point automotive-Ethernet pairs (single twisted pair, 100/1000
Mbit in the service description; shipped speeds: [switch configuration above](#shipped-switch-speeds--c-2026-11-13), **no terminating resistors**) off the A11 Radio's on-board switch (BCM89551 on the MY22/DV teardown unit; Marvell 88Q5050 on the live Y181 bench radio — board variant, same spec; 2026-11-12). Two nodes host
switches — the **A11 Radio** and the **K56 Serial Data Gateway Module**; every other node is a leaf
`[Module ↔ Switch ↔ Module]`. GM service data names each bus and circuit: ALLDATA *Radio-Audio System
→ Data Link Communications* + connector end-view `A11 Radio X11`, corroborated by the **GM Silverado
2500/3500HD Electrical Body Builder Manual** (`24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`,
§*Data Communications → Ethernet Bus Description*), which enumerates the full bus list. This grounds
the IP-level endpoints above to physical wire (closes `vehicle_network.md` open item #1 for the amp pair).

> **Test vehicle:** 2024 Silverado **2500 HD LTZ**, RPO **IOK** — the HD BBM above is the matching
> service manual. Per the VIN's factory **RPO Code List**, this truck has **no Head-Up Display**
> (no UV6/HUD code) and **no rear-seat video** (no rear-entertainment code), so radio buses **5**
> (P22F rear-seat video) and **14** (P29 HUD) are **not equipped** here — only buses **2 / 4 / 6**
> are wired on X11. Present & relevant options: **IOK** radio, **UQA** Bose amp (Bus 6 / T3),
> **UE1** OnStar (K73 comm path), **UDV** full cluster (P16), **IVN** (cockpit uses radio family).
> Bus/circuit numbering is shared across the T1XX line, so a 1500 (light-duty) build uses the same
> bus map — any 1500-only deviation would be noted here explicitly; none is currently known.

**Radio (A11) Ethernet buses** — all land on connector **X11** (12-way F CTS-050):

| Bus | Circuits | Endpoints | On IOK 2500HD |
|-----|----------|-----------|---------------|
| Ethernet 2 | 4757 / 4758 | **A11 Radio ↔ K56 Serial Data Gateway** (radio X11 p3/4) | ✅ wired (harness-confirmed) |
| Ethernet 4 | 7210 / 7211 | **A11 Radio ↔ K73 Communication Interface Module** (radio X11 p11/12). *IOR-radio variant routes this as K56 ↔ K73 instead.* | ✅ wired (harness-confirmed) |
| Ethernet 5 | 7212 / 7213 | A11 Radio ↔ **P22F Video Display – Right Rear-Seat Back** | ❌ not equipped (no rear-ent RPO) |
| **Ethernet 6** | **7214 / 7215** | **A11 Radio ↔ T3 Audio Amplifier** — the Bose AVB audio pair (radio X11 p8/9 → amp T3 X3 p1/2) | ✅ wired (harness-confirmed) |
| Ethernet 14 | 7230 / 7231 | A11 Radio ↔ **P29 Head-Up Display** | ❌ not equipped (no UV6/HUD) |

**Other vehicle Ethernet buses (not on the radio — via K56 gateway):** Eth 1 (see below); Eth 3
(7208/7209) K56 ↔ K179 Auto-Driving Mapping Module; Eth 7 (7216/7217) K56 ↔ P16 IPC Cluster / K190
Off-Board Charger; Eth 11 (7224/7225) K124 Image Processing ↔ K179; Eth 15 (7232/7233) K56 ↔ K161
Perf Data Recorder ↔ P22F passenger-seat display.

- The amp is a leaf on **Bus 6**. Amp control/discovery is separate: **AUTOSAR CAN 5** (4985/4984),
  radio **X6 p9/10** ↔ amp T3 X3 p11/12 (see [`../hardware/connectors.md`](../hardware/connectors.md) X6 row).
  T3's two separate links (Bus 6 audio data-plane vs. CAN 5 control-plane) are summarized as a
  single paragraph in [`../hardware/connectors.md`](../hardware/connectors.md) §Audio
  Architecture — Bose (2026-11-13); don't restate it here.
- **Connector caution:** the radio's Ethernet lives on **X11** (12-way CTS-050). It is a *different*
  physical connector from **X6** (29-way, speaker outs + CAN 5) — do not conflate them; earlier notes
  that labeled the Ethernet connector "X6" were in error.

### Ethernet 1 — service diagnostics / programming (X84 DLC ↔ K56)

Not a radio bus, but the service-tool entry point into the Ethernet backbone. **Ethernet 1 = two
twisted pairs**: **1R** (circuits 4972/4973) and **1T** (4974/4975), run **X84 Data Link Connector ↔
K56 Serial Data Gateway**. Used to diagnose/flash control modules over Ethernet instead of CAN; the
**K56 gateway converts Ethernet serial data ↔ CAN both directions**. An **Ethernet-enable circuit
(7207)** wakes K56 for Ethernet diagnostics/programming.

**X84 DLC (16-cavity OBD) pinout (Ethernet + CAN):** T1 CAN 7 [+], T2 PP-CAN 1 [+], **T3 Eth 1R [+]**,
T4 scan-tool ground, T5 signal ground, T6 CAN 6 [+], T7 PP-CAN 2 [+], **T8 Eth 1 enable**, T9 CAN 7 [−],
T10 PP-CAN 1 [−], **T11 Eth 1R [−]**, **T12 Eth 1T [+]**, **T13 Eth 1T [−]**, T14 CAN 6 [−], T15 PP-CAN 2 [−],
T16 scan-tool B+. (CAN 6 = diagnostics/programming; CAN 7 = plant programming only; Private-Presentation
CAN 1/2 = Engineering-only, security-gated.) — BBM §*X84 Data Link Connector*.

- Physical harness/pinout detail: [`../hardware/connectors.md`](../hardware/connectors.md)
  §Audio Architecture and §Authoritative IOK Connector Table. Radio-side Ethernet connector **X11**
  mating plug (P/N 13529935) datasheet — Delphi/Aptiv drawing **33283033**:
  [`../hardware/datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf`](../hardware/datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf).

> **[2026-11-13] X11 p1/2, recorded "not occupied" above (`connectors.md` X11 row), carried
> live traffic when independently tapped — open, [?], not yet reconciled with the "not
> occupied" claim.** Same VLAN trunk and service allow-list as Bus 2, opposite PHY
> master/slave role, no matching GM circuit number for pins 1/2. Canonical writeup (do not
> restate here): `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §14 in the
> `Y175_2026-11-02` analysis tree.

**Post-power-cycle correction, 2026-11-14:** the owner subsequently rebooted
by removing/restoring power. RH850 entered `NoCalibration (0xe)` after the
startup fault timeout; the display reported bad/incomplete calibration.
T1 diagnostic reads still worked, MEC stayed FF, and all 14 cleared module
identities remained base 70008/00. USB ADB did not reappear. See the
[owning post-boot finding](../diagnostics/diagnosticsd_routines_and_recovery.md#owner-power-cycle-after-clear-nocalibration-fault-2026-11-14).

**Recovery completed, 2026-11-14:** the main MDI2 client restored the pinned
stock LTZ package to this cleared A11. The exact 70008/00 profile required a
one-time in-memory source exception; the erased VIN was restored from the
owner's supplied value before programming. All 14 slots and VIN matched
post-reset readback; F0F1/F0F2 were `0000`. Later UART boots reached HMI ready
with calibration state `2`, and the owner confirmed normal radio operation.
ADB and final MEC were not rechecked at that recovery checkpoint.
**Follow-up, 2026-11-15:** USB ADB and T1 ADB on radio TCP 9040 were
subsequently operational; the final MEC value remains unverified. See the
[completed MDI2 recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
