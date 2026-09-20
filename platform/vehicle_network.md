# Vehicle Network Topology — 2024 Silverado 2500 HD LTZ (ICE, gminfo37 / A11 Radio)

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
- **Radio = ECU `0x80`** — ECUID `004B41DC…14AC` (matches EEPROM/teardown); LS-CAN via the
  gateway with tester ID **F2**: ReqCANId `0x14DA80F2` / RspCANId `0x145AF280` (confirmed:
  `diagnostics/dps/A11_CSM_x80.Txt:160` — every ECU in the scan uses F2; F1 is the generic OBD
  tester address, not seen here). [C]
- **Segmented buses** behind `0x45`: HS-CAN + LS-CAN + AUTOSAR "SER DATA 5" (seen on the
  connector harness, see [`../hardware/connectors.md`](../hardware/connectors.md)). [C]

**24-ECU census (diagnostic addresses):**
`0x11 0x18 0x1A 0x28 0x31 0x40 0x41 0x45(gw) 0x58 0x59 0x60 0x68 0x6D 0x75 0x80(radio) 0x81 0x97 0xA4 0xA8 0xB9 0xBA 0xBD 0xBE 0xBF`

Response-ID priority nibbles (`145A`/`142A`/`141A`/`144A`) group modules by bus/priority. Decode
of the other 22 → GM Global-B address table (**open**). Scanned unit: `SBI = Bypass Inactive`,
`MEC = 244`, fully programmed (stock/secure); secure $27 SecurityAccess path live.

---

## Plane 2 — Automotive Ethernet (VLAN 4 / 5)

Backbone: 100BASE-T1 via on-board switch (host on port 5; gateway/telematics on
port 2). Switch IC is board-variant — **Broadcom BCM89551** on MY22/DV boards, **Marvell 88Q5050**
on MY23+ (per `persist.vendor.harman.hardwareid`); same port layout and spec.

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
- **Radio** — CAN `0x80` (via VIP MCU) + Ethernet `.100`. VIP↔SoC HDLC IPC (`/dev/ttyS1`, 20
  channels 1-20) is the CAN↔Android bridge; Android never sees raw CAN.
- **CGM / telematics** — direct CAN access (unlike the radio) + Ethernet `.107/.112` + cellular
  link to GM cloud (`vtmpub.oboservices.mobi`). The real door to the wider bus + internet.

> **CAN gateway `0x45` = the CGM (Central Gateway Module).** The GIS763 CalDef
> (`InfotainmentProg_GlobalB`) records `GIS763_Gateway = 69 (0x45)` = "Diagnostic Address of the
> CGM" (see [`ota_programming_roles.md`](ota_programming_roles.md)), and the DPS scan confirms
> `0x45` as the diagnostic gateway (RspCANId `0x14DAF245`). **Open** (item #3): whether this CAN
> Central Gateway Module is the same physical unit as the Ethernet-side Connectivity Gateway /
> telematics (`.107/.112`, Bosch OUI) and/or the Ethernet inter-VLAN router (`.102`) is not settled
> — the CAN diagnostic address `0x45` and those Ethernet faces are not yet proven to be one node.

## Open items
1. Physical Ethernet Bus 2/4/6 pair ↔ IP-segment mapping (per-pair capture). **Partially closed
   from GM service data** (ALLDATA *Data Link Communications*): Ethernet **2** (4757/4758) =
   A11↔K56 gateway; **4** (7210/7211) = A11/K56↔K73 telematics; **5** (7212/7213) = A11↔P22F
   rear video; **6** (7214/7215) = **A11↔T3 Bose amp** (the AVB audio pair); **14** (7230/7231) =
   A11↔P29 HUD. IP-segment↔bus correlation still needs a per-pair capture. See
   [`networking.md`](networking.md) §Physical Automotive-Ethernet bus map.
2. CAN address→function decode for the other 22 ECUs.
3. Whether `.102` (router) and `.107/.112` (CGM/telematics) are one GM TCP/CGM function split
   across faces, or distinct modules.
4. Identity of `:49156`; whether FSA `0x5AA5` framing is really on the wire (single-source).

See also: [`../hardware/connectors.md`](../hardware/connectors.md) (physical harness that carries
these buses) and [`ota_programming_roles.md`](ota_programming_roles.md) (module programming over
this network).
