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
> by ≥2 sources or a primary capture; **[?]** = single-source or contested; **[X]** = external /
> other-vehicle source (e.g. surrealdev Cadillac captures), not yet confirmed on this A11 unit.

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

**ECU census (diagnostic addresses).** The `A11_CSM_x80` DPS scan enumerated **24**; a later live
MDI2 DoIP read (`dps_readx80`, F1B0 broadcast, 2nd pass) found **27** — adding **`0x6B` `0x84`
`0x96`** (the three true Ethernet/DoIP nodes alongside gateway `0x45`; every other address incl.
radio `0x80` is CAN-via-gateway). Combined 27:
`0x11 0x18 0x1A 0x28 0x31 0x40 0x41 0x45(gw) 0x58 0x59 0x60 0x68 0x6B(eth) 0x6D 0x75 0x80(radio) 0x81 0x84(eth) 0x96(eth) 0x97 0xA4 0xA8 0xB9 0xBA 0xBD 0xBE 0xBF`

Response-ID priority nibbles (`145A`/`142A`/`141A`/`144A`) group modules by bus/priority. Decode
of the others → GM Global-B address table (**open**). Scanned unit (A11_CSM_x80): `SBI = Bypass
Inactive`, `MEC = 244`, fully programmed. **Live corroboration (`dps_readx80`, MDI2 DoIP read of the
radio):** `0x80` ECUID (`$22 F0F3`) = `004B41DC…14AC` **byte-identical** to the value above;
ProgrammedState (`$31 FF01`) = `00` fully programmed on both `0x45` and `0x80`; radio `F1A0` = `0xFF`
on that read (secure-mode; differs from the A11 scan's `MEC=244`, i.e. per-capture unit state — see
[`security.md`](security.md)). `$27` on that read returned an all-`0xFF` seed under a failed SPS
validation, whereas valid SPS sessions used an 8-byte seed / 6-byte key and succeeded (so the all-FF
seed is the **SPS-cred-absent path**, not necessarily a hardware SBI flip).

---

## Plane 1a — SecOC (CAN frame authentication)

> **Source.** External public research — Snipesy / Surreal Development, *"Rooting the Cadillac
> Part 2: SecOc"*, 2026-09-22 (`https://surrealdev.com/rooting-the-cadillac-part-2-secoc/`;
> canonical bibliography: [`qualcomm_cadillac_platform.md`](qualcomm_cadillac_platform.md) →
> Sources), captured on **Lyriq / CT5** Global-B vehicles.
> Same Global-B platform as this Silverado, so the algorithm is expected to hold, but the frame
> IDs, keys and the VLAN-502 mirror below are **Cadillac captures — not yet observed on this
> A11/gminfo37 unit.** Marked **[X]** = external/other-vehicle, confirm before relying on it here.

Global B is *mostly* unsigned/unencrypted (especially CAN5), but selected **critical-control**
frames carry a **SecOC** message-authentication code. Frames are authenticated, **not encrypted** —
anyone can parse them, and many modules still act on a frame whose MAC fails. The Central Gateway
selectively forwards between buses and sometimes checks the MAC, sometimes not. MAC'd frames tend to
be things like power steering — and the modules that consume them may not even be on the radio's bus,
so the radio itself rarely needs to satisfy SecOC. [X] (Qualcomm/Cadillac radio hardware context:
[`qualcomm_cadillac_platform.md`](qualcomm_cadillac_platform.md).)

**MAC construction:**

```
MAC = CMAC_AES128_k( data_id(u8) ‖ BE32(can_id) ‖ BE64(freshness) ‖ payload )
```

- MAC on the wire is the CMAC **truncated to 27 bits** (3 bytes + 3 bits).
- Freshness is a 64-bit BE counter, often combined with a secondary companion ID; padding and
  payload position vary per frame.
- Worked example — gateway status/power frame **`0x370`** (`bit37:3` = power mode):
  `Off E8EE8A69…` `Acc 68A66F49…` `Run 7C8CB069…` `Crank 69F65949…` `Propulsion 6BFE8B49…`
  ```
  data_id  01
  can_id   00000370
  freshness 000000005FEEE249
  payload  3810
  key      0814586a72522fd9b57685de676eb246   (real key, source's totaled donor car)
  CMAC     e8ee8a78 b7ba268d 25473fb3 5bf2067c
  trunc27  E8EE8A|011  -> on wire E8EE8A|011
  ```

**$27 SecurityAccess (level 1) key algorithm** — precondition for provisioning: [X]

```
$27 01                -> 67 01 <31B seed>   seed = ecuid(16B) ‖ nonce(15B)
$27 02 <12B key>      -> 67 02 accepted  |  7F 27 35 (NRC 0x35 invalidKey)

K1  = CMAC_AES128( root_key, subfn(1B) ‖ ecuid(16B) ‖ nonce(15B) )
key = CMAC_AES128( K1, 0xFF×16 )[0:12]
```

Worked vector (AES test key `root_key=2b7e1516…4f3c`, subfn `01`, ecuId `0102…0f10`, nonce
`1122…eeff`): `K1 = 344944c7c7a8e103f1c9703cca19bf52`, `key_response = ad3ccd21e367a121640b2a23`.

**SecOC key provisioning** (UDS RoutineControl, after $27): the on-wire key is itself encrypted
against a factory key. Provisioning needs three secrets, all OEM-held: the module's unique **$27
unlock key**, the **HSM/identifier ID**, and a factory/assembly-line **master key**. Install uses
the **SHE KDF (Matyas-Meyer-Oseas over AES-128)**: [X]

```
KDF(key,const) = AES_Enc(key,const) XOR const
K1 = KDF(auth_key, KEY_UPDATE_ENC_C=0x0101534845 0080…00B0)
K2 = KDF(auth_key, KEY_UPDATE_MAC_C=0x0102534845 0080…00B0)   ("SHE" = 0x534845)
M1 = UID(120b) ‖ ID(4b) ‖ AuthID(4b)                          16B
M2 = AES128_CBC_Enc(K1, IV=0, counter(28b)‖flags(4b)‖new_key(128b))   32B
M3 = CMAC_AES128(K2, M1‖M2)                                   16B
-> 31 01 <RID:2B> <slot:1B> M1 M2 M3   (M1|M2|M3 = 64B; with the slot byte the option
                                        record is 65B, param_4==0x41; response 71 01 <RID> <status>)
```

**Bottom line for aftermarket repair:** only the OEM servers hold the master keys and there is no
aftermarket provisioning path — a shared-key module cannot be swapped in without the OEM secrets.
The author claims (unpublished, zero-days withheld) that all SecOC keys are dumpable from any module
"with no exploit, if you think fast enough" — **unverified, no method given.** [X]

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

### vlan502 · CAN-over-Ethernet mirror (Cadillac capture) [X]
Per the surrealdev SecOC research (see Plane 1a): on Lyriq/CT5 the **entire CAN network is mirrored
onto VLAN 502 as UDP multicast** — the easiest whole-vehicle monitor is a single pcap on that VLAN.
Observed source `172.16.50.207` → `239.192.0.9:59200`. Some switches block the VLAN, much is open.
**Not yet observed on this A11/gminfo37 Silverado — a bench pcap should look for a 502 mirror.**
Frame encapsulation (little-endian element_id):
```
element header (7B):  type=0x02(CAN/CAN-FD) | body_len(2B BE) | element_id(4B LE = CAN ID)
type-0x02 body:       extended(1B: 0=11-bit,1=29-bit) | dlc(1B) | actual_len(1B)
  metadata[5]:  [0]=controller mirror(==[2]) [1]=FD marker(0x30) [2]=channel fca0..fca9
                [3]=flags (0x01/0x09 dominant; 0x04/0x0A/0x0B rare) [4]=reserved
  rolling[4]    timestamp-like counter
  data[actual_len]
  trailer[4]    = rolling byte-reversed (integrity check)
```
No authentication of any form on the in-vehicle Ethernet at L2/L3 (no **IPsec**, no **MACsec**) on
the vehicles the author examined; only niche services use **TLS** — so this VLAN-502 mirror is
readable by anything on the switch fabric. [X]

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
5. **SecOC on this Silverado:** confirm the CMAC-AES128/27-bit scheme and the $27 key algorithm
   (Plane 1a) against a live A11 capture; identify which frame IDs carry a MAC on gminfo37.
6. **VLAN-502 CAN mirror:** bench-pcap this unit for a 502 UDP-multicast CAN mirror (Plane 2);
   the Cadillac source was `172.16.50.207→239.192.0.9:59200`.

See also: [`../hardware/connectors.md`](../hardware/connectors.md) (physical harness that carries
these buses) and [`ota_programming_roles.md`](ota_programming_roles.md) (module programming over
this network).
