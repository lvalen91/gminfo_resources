# Vehicle Network Topology — 2024 Silverado ICE (gminfo37 / A11 Radio)

Vehicle-wide network map (distinct from [`networking.md`](networking.md), which covers the
SoC-internal / inter-partition network). Consolidated 2026-07-01 from: the `A11_CSM_x80` DPS log
([`../diagnostics/dps/A11_CSM_x80.Txt`](../diagnostics/dps/A11_CSM_x80.Txt)), the Y181 ADB
enumeration ([`../enumeration/Y181/`](../enumeration/Y181/)),
[`../research/GM_REMOTE_ACCESS_ANALYSIS.txt`](../research/GM_REMOTE_ACCESS_ANALYSIS.txt),
[`../research/VIP_CONTROL_ANALYSIS.txt`](../research/VIP_CONTROL_ANALYSIS.txt),
[`../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md),
the FSA protocol notes ([`fsa_protocol.md`](fsa_protocol.md)), and the ethernet-UDS notes
([`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)).

> **Sources disagree on several node labels.** Both are shown where they do. **[C]** = confirmed
> by ≥2 sources or a primary capture; **[?]** = single-source or contested.

## Headline

Two planes joined **inside the radio**, plus a physically-distinct gateway/telematics path:

1. **CAN diagnostic plane** — GM VIP/SDV1 (Global B), 29-bit UDS; radio reaches it *only through
   its VIP MCU*.
2. **Automotive-Ethernet service plane** — two VLANs, GM FSA + SOME/IP, bridged by an Ethernet
   gateway/router.

Radio is dual-homed: **ECU `0x80` on CAN** and **`192.168.1.100` on Ethernet**.

---

## Plane 1 — CAN (from the DPS scan)

DPS 4.56 over **LS-CAN through the central gateway**; **24 ECUs** enumerated
([`../diagnostics/dps/A11_CSM_x80.Txt`](../diagnostics/dps/A11_CSM_x80.Txt)). VIN present — redact
when sharing.

- **Central gateway = ECU `0x45`** — wake-up + ECUID reads route through it; response uses the
  physical `14DAF245` pattern, unlike every other module's `14xAF2xx`. [C]
- **Radio = ECU `0x80`** — ECUID `004B41DC…14AC` (matches EEPROM/teardown); HS-CAN primary
  (`14DA80F1`/`145AF180`), also answered on LS-CAN via the gateway. [C]
- **Segmented buses** behind `0x45`: HS-CAN + LS-CAN + AUTOSAR "SER DATA 5" (seen on the
  connector harness, see [`../hardware/connectors.md`](../hardware/connectors.md)). [C]

**24-ECU census (diagnostic addresses):**
`0x11 0x18 0x1A 0x28 0x31 0x40 0x41 0x45(gw) 0x58 0x59 0x60 0x68 0x6D 0x75 0x80(radio) 0x81 0x97 0xA4 0xA8 0xB9 0xBA 0xBD 0xBE 0xBF`

Response-ID priority nibbles (`145A`/`142A`/`141A`/`144A`) group modules by bus/priority. Decode
of the other 22 → GM Global-B address table (**open**). Scanned unit: `SBI = Bypass Inactive`,
`MEC = 244`, fully programmed (stock/secure); secure $27 SecurityAccess path live.

---

## Plane 2 — Automotive Ethernet (VLAN 4 / 5)

Backbone: 100BASE-T1 via on-board **BCM89551** switch (host on port 5; gateway/telematics on
port 2).

### vlan5 · `192.168.1.0/24` ("Info3x" service network)

| IP | Node | Conflict / note | Conf. |
|----|------|-----------------|:----:|
| .100 | **CSM / IVI — this radio (Android guest)** | — | [C] |
| .102 | **Ethernet gateway/router** (DNS `dnsmasq`, SOME/IP-SD), labeled **`TCP_ETH`** | FSA notes call it "TCP = Telematic Comm Processor" hosting OnStar/TurnByTurn/RemoteReflash; live scan sees it as the DNS/SOME-IP **inter-VLAN router** (shares MAC with `172.16.4.1`). Likely a telematics-comm processor that *also* routes. | [?] |
| .103 | **AMP_ETH** — audio amplifier (**Bose**, owner-confirmed) | doc label is generic "Amplifier" | [C] |
| .104 / .105 | RSI1 / RSI2 (rear-seat) — offline on bench | — | [?] |
| .106 | **IPC — Instrument Panel Controller** (Visteon cluster; DeviceInfo `Company=Visteon, Module=IPC`) | older note mis-expands as "Inter-Process Communication" | [C] |
| .107 | **CGM host processor / telematics** | — | [C] |
| .108 / .110 | LOWRADIO / PDR — offline | — | [?] |
| .112 | **CGM_ETH / CGM_OTA** — Connectivity Gateway Module / telematics | vlan4 face `172.16.4.112` has the only **real MAC** `10:66:50:...` (Bosch OUI), heavily firewalled | [C] |
| 239.192.0.1 | SOME/IP-SD multicast (live scan: UDP **30490**) | — | [C] |

> **Synthetic MACs.** Most vlan5 peers use `02:0x:00:00:0x:00` locally-administered MACs =
> hypervisor virtual NICs / co-resident GHS partitions bridged onto the physical backbone. Only
> the Bosch device (real OUI) and the RTOS partition are unambiguously separate hardware.

### vlan4 · `172.16.4.0/24` (internal vehicle network)
`.100` IVI (radio's vlan4 face) · `.1` router (shares MAC with `.102`) · `.14` **ACP** ·
`.107` RTOS partition · `.12/.13/.15` **EOCM** (Enhanced OnStar). Other-variant subnets
`192.168.118.x` / `172.16.5.x` are code-referenced, not live.

### Service / protocol layer
- **GM FSA** — 20-byte big-endian header, magic **`0x5AA5`**, protobuf; catalog in
  [`fsa_protocol.md`](fsa_protocol.md) (9002 RemoteModuleHMI, 9005 OnStarFunctions, 9010
  DeviceInformation, 9011 ProgrammingMaster, 9012/9018 RemoteReflash(UI), 9016 NAM, 9020
  DisplaysCoordination). Live scan saw the proprietary framing on **port 9010** but could not
  confirm the `0x5AA5` signature — treat FSA specifics as single-source. [?]
- **SOME/IP-SD** present (UDP 30490 / 239.192.0.1). [C]
- **`:49156`** — the FSA notes call it root `diagnosticsd` UDS-over-TCP
  ([`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md));
  the live Y181 scan sees it as an **unknown, localhost-only** listener. Not confirmed as a
  vehicle-facing DoIP endpoint. [?]
- Firewall INPUT DROP / OUTPUT ACCEPT; FSA servers single-client; NAM brokers **EAP-AKA** cellular
  attach + VLAN grants.

---

## Join points
- **Radio** — CAN `0x80` (via VIP MCU) + Ethernet `.100`. VIP↔SoC HDLC IPC (`/dev/ttyS1`, 19
  channels) is the CAN↔Android bridge; Android never sees raw CAN.
- **CGM / telematics** — direct CAN access (unlike the radio) + Ethernet `.107/.112` + cellular
  link to GM cloud (`vtmpub.oboservices.mobi`). The real door to the wider bus + internet.

> **Correction to earlier working notes:** CAN gateway `0x45` is **not** established to be the
> CGM (it is simply "the CAN gateway" in the DPS flow); CGM/telematics is `.107/.112` on Ethernet;
> the observed Ethernet inter-VLAN router is a separate node (`.102`). Do not conflate without a
> capture.

## Open items
1. Physical Ethernet Bus 2/4/6 pair ↔ IP-segment mapping (per-pair capture).
2. CAN address→function decode for the other 22 ECUs.
3. Whether `.102` (router) and `.107/.112` (CGM/telematics) are one GM TCP/CGM function split
   across faces, or distinct modules.
4. Identity of `:49156`; whether FSA `0x5AA5` framing is really on the wire (single-source).

See also: [`../hardware/connectors.md`](../hardware/connectors.md) (physical harness that carries
these buses) and [`ota_programming_roles.md`](ota_programming_roles.md) (module programming over
this network).
