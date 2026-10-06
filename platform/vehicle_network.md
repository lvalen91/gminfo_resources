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
on MY23+ (per `persist.vendor.harman.hardwareid`); same port layout and spec. **The vehicle trim
carries three physical automotive-ethernet connections to this switch** (owner, in-vehicle; not
wired on the bench).

> **[C] Bench discovery result (2026-10-06, live Y175 via `gm_bench_agent` `mcast.listen`, strictly
> passive).** The ethernet **service-discovery plane is silent on the bench**: `/proc/net/igmp` shows
> the HU joins **mDNS `224.0.0.251`/`ff02::fb`** + all-hosts `224.0.0.1` on vlan4/vlan5/eth0 — but
> **NOT** the SOME/IP-SD group `239.192.0.1`. A 25 s passive listen on `239.192.0.1:30490` and `:3000`
> and a 20 s listen on mDNS `224.0.0.251:5353` **all returned 0 packets** (joins succeeded on
> vlan4/vlan5/eth0, no SELinux denial, `sends:0`). **Cause:** the three in-vehicle automotive-ethernet
> links are unconnected on the bench, so no AE peer ECU/switch is advertising — the HU is *ready* to
> participate but has no partners. SOME/IP-SD `239.192.0.1:30490` therefore reflects the *firmware/
> in-vehicle* config, not a bench-active service. The harness (`~/gm_bench_agent`, `untrusted_app`,
> listen-only) is validated and would map the real OfferService graph **in-vehicle** or with the bench
> AE links bridged to the vehicle backbone. (A 3P `untrusted_app` CAN join these groups + `MulticastLock`
> with no root — only the privileged `/proc/net/igmp`/netlink reads are SELinux-denied to it.)

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
| .112 | **CGM_ETH / CGM_OTA** — Connectivity Gateway Module / telematics | vlan4 face `172.16.4.112` has the only **real/universal-OUI MAC** `10:66:50:...` (vendor UNVERIFIED — not confirmed Bosch; raw scan "unknown, possibly Harman/Samsung"), heavily firewalled | [C] |
| 239.192.0.1 | SOME/IP-SD multicast (live scan: UDP **30490**) | — | [C] |

> **Synthetic MACs.** Most vlan5 peers use `02:0x:00:00:0x:00` locally-administered MACs =
> hypervisor virtual NICs / co-resident GHS partitions bridged onto the physical backbone.
> **[C] CORRECTION (2026-10-06):** an earlier version of this note claimed "the Bosch device (real
> OUI) **and the RTOS partition** are unambiguously separate hardware." The RTOS-partition half is
> **wrong**. ARP evidence (`enumeration/Y181/*/raw/arp_table.txt`,
> `enumeration/Y181/jun2026/enumeration_report.txt:7477-7482`): the RTOS/diagnostic endpoint
> `172.16.4.107` carries MAC **`02:05:00:00:02:00`** — locally-administered (bit-1 set), i.e. a
> hypervisor virtual NIC, **not** real silicon — and that **same** virtual NIC is dual-homed as
> `192.168.1.112` on vlan5 (`arp_table.txt` confirms identical MAC). A single co-resident GHS
> partition bridged onto both VLANs, exactly like the Android guest's own `.100`-on-both. So the
> **only** unambiguously-separate hardware on these VLANs is the real/universal-OUI device:
> **vlan4 `172.16.4.112` = `10:66:50:0c:ed:d3`** (universal OUI `10:66:50` — **vendor UNVERIFIED, not
> confirmed Bosch**; raw scan "unknown, possibly Harman/Samsung"), the external CGM/telematics
> module. The `.107` "RTOS partition" is **SoC-internal** (a GHS-hosted INTEGRITY partition on the
> same Intel A3960), corroborated by its response **TTL=255** vs the external `.112`'s **TTL=64**
> (Linux) — see [`networking.md`](networking.md) vlan4 table and the "vlan4 internal-vs-external"
> finding in [`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md#vlan4--internal-ghs-fabric-diagnosticsd-forwarding-target--bench-reachability-of-the-vipuds-path-2026-10-06).

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
  DisplaysCoordination). **`0x5AA5` framing now confirmed on the wire** — live unauthenticated
  interaction with the real cluster service on `9002` in the emulator (GET/SUBSCRIBE round-trips)
  plus jadx RE of ClusterService/DeviceInformationService. Full spec: 20B BE header (serviceId·
  instanceId·functionId·opType·clientHandle·magic `0x5AA5`·reserved·**payloadLength int32**) +
  protobuf; opTypes GET 421/SET 422/REQUEST 641/REQUESTRESPONSE 674/EVENT 1032; serviceId 9002=1007,
  9010=1001. **No auth of any kind** (see [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md)). [C]
  Cluster-injection surface (`REQUEST`/`REQUESTRESPONSE` `opType=641/674`, fktId ≥700 into
  `ClusterViewManager` via the method handler — **corrected 2026-09, was misattributed to
  EVENT/1032**) and the two parser bugs (unbounded int32 `payloadLength` → live-proven RAM-DoS
  against `com.gm.cluster`; reject-path framing desync) are documented in
  [`fsa_protocol.md`](fsa_protocol.md#f-inject-cluster-injection-surface), plus two new
  UDP/multicast discovery-listener findings (uncaught AIOOBE crash; connectionless injection
  bypassing all gates) at
  [`fsa_protocol.md#f-udp-udpmulticast-discovery-listener-crash-aioobe--high-unauthenticated`](fsa_protocol.md#f-udp-udpmulticast-discovery-listener-crash-aioobe--high-unauthenticated).
  `ProgrammingMaster`
  (port 9011, catalog serviceId 1006) is confirmed **dead code** — compiled in, never instantiated,
  never bound — resolving the catalog-vs-live-scan discrepancy (see
  [`fsa_protocol.md`](fsa_protocol.md#p-programmingmaster-9011-is-dead-code)). [C]
- **SOME/IP-SD** present (UDP 30490 / 239.192.0.1). [C]
- **`:49156`** — confirmed root `diagnosticsd`, a **custom 8-byte GM-header UDS bridge, NOT DoIP**
  (SRC/TGT addr + PAYLOAD_LEN; ECU `0x0084`, tester `0x0FA0`), bridging `172.16.4.100 ↔ 172.16.4.107`
  on vlan4 to the RTOS diagnostic partition
  ([`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)). The
  `MaxPayload 49156` the external DoIP tester prints at connect is a **coincidental numeral**, not this
  socket. Unauthenticated `$27/$10/$22` from the shell side return NRC `0x10` generalReject. [C]
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
4. ~~Identity of `:49156`; whether FSA `0x5AA5` framing is really on the wire (single-source).~~
   **RESOLVED (2026-09-26):** `:49156` = root `diagnosticsd`, custom 8-byte GM header (not DoIP);
   FSA `0x5AA5` framing confirmed live on `9002` + jadx RE. See §Service/protocol layer.
5. **SecOC on this Silverado:** confirm the CMAC-AES128/27-bit scheme and the $27 key algorithm
   (Plane 1a) against a live A11 capture; identify which frame IDs carry a MAC on gminfo37.
6. **VLAN-502 CAN mirror:** bench-pcap this unit for a 502 UDP-multicast CAN mirror (Plane 2);
   the Cadillac source was `172.16.50.207→239.192.0.9:59200`.

---

## CAN feasibility & radio-removal audit — Pi-swap side-project (firmware-grounded, 2026-09-27)

Scope: does the **head unit itself** speak CAN, what does its wake/vehicle-status path look like,
and what breaks if the OEM radio node is physically removed. Driven by the Pi-replacement theory
(reuse existing wiring, run AOSP-AAOS on a Pi 4/5). Evidence base: the **Y181B clean-room image**
(`.../update_packages/Y181B/mountables/Y181B_cleanroom.img`, build
`W231E-Y181.3.2-SIHM22B-499.3`, Android 12, kernel **4.19.305**, x86_64 Intel Gen8 CSM), read via
`7z` (no ext4 mount on this host). Confidence tags: **[FW]** confirmed in this firmware · **[INF]**
inferred from firmware structure · **[VEH]** confirmed by the owner's real-vehicle test · **[GM]**
general GM-platform knowledge, not specific to this unit.

### 1. The Android/AAOS guest has **no CAN interface** — it never touches CAN directly

- **No CAN driver anywhere.** Zero `can`/`socketcan`/`vcan`/`flexcan`/`slcan`/`j1939` kernel
  modules in either module set: the generic `os/vendor/lib/modules/` blob (**324 `.ko`**, an
  upstream x86 collection — `bcmdhd`, `ath3k`, `dell-smm-hwmon`, etc., not all loaded) and, more
  tellingly, the **actually-loaded** first-stage set in `boot/ramdisk_root/vendor/lib/modules/`
  (**11 modules**: `igb_avb, dwc3[-pci], xhci-{hcd,pci}, ti949_serdes, faceplate, atmel_mxt_ts,
  mei[-me], dynamic_spi_node`). Not one CAN driver. [FW]
- **No CAN netdev is ever brought up.** No `ip link ... type can`, `slcan`, `ifup can*`, or
  `/dev/can*` in any `.rc` or shell script in system/vendor. [FW]
- **No CAN symbols in the vehicle stack.** `strings` on `gmvt`, `gmvt_client`,
  `android.hardware.automotive.vehicle@2.0-service-gm` (the GM VHAL), `IPCServer`,
  `vehicleaudiocontrol` → no `socketcan`/`AF_CAN`/`gmlan`/`can0`/arbitration-ID handling. [FW]
- Kernel `CONFIG_CAN` could not be positively read (this bzImage's `IKCFG` block is inside the
  compressed payload and did not cleanly decompress with `xz`/`gzip`/`lz4`/binwalk here), so the
  built-in-vs-absent question for the CAN subsystem is **not settled from config**. It does not
  need to be: a built-in CAN stack with no driver, no netdev bringup and no consumer is inert.
  **[FW for the modules/netdev/strings; the config symbol itself is unresolved.]**
- **Caution / correction:** `gmvt` (runs as `audioserver`, cap `NET_RAW`) is **GM Voice**
  (VA/VR — see `/vendor/etc/gmvt.cfg`: PCM nodes, VTC voice-tuning configs), **not** "GM Vehicle
  Transport." Its `NET_RAW` is for a voice stream socket, not vehicle CAN. Don't cite it as a
  vehicle-network daemon. [FW]

**How the guest actually reaches the vehicle** (two paths, both already in this doc, now confirmed
from the guest side):

1. **GHS hypervisor IPC mux** — the box runs Android as a **Green Hills INTEGRITY guest**
   (`/vendor/bin/ghs_set_is_virt.sh`: `is_virt=true` iff `/dev/ghs` exists). `IPCServer`
   ("**GhsComms**", `GhsCommsRx/TxThread`) multiplexes numbered logical channels over a UART-backed
   link and exposes them as `/dev/ipc/ipcN` sockets. Config `/vendor/etc/ipc4.cfg`:
   `com_device=/dev/ttyS1`, `com_speed=1000000`, `protocol_version=0x10`, `socket_prefix=/dev/ipc/ipc`,
   control iface `/dev/ipc/ctrlif_s` (gid `vehicle_network`), **lchannels index 0–20**. The GM VHAL
   opens **`/dev/ipc/ipc3`** = lchannel **index 3, gid `vehicle_network`** — the vehicle-signal
   channel. (`IPCServer` strings also reference `/dev/ghs/ipc` and `/dev/ttyS4`; the authoritative
   backing device per config is `/dev/ttyS1`.) [FW]
   - This **confirms and refines** the "Join points" note above ("VIP↔SoC HDLC IPC `/dev/ttyS1`,
     20 channels 1-20 … Android never sees raw CAN"): same UART, same channel count. The peer on
     the far end of `/dev/ttyS1` (the VIP MCU / a GHS partition) owns the physical CAN; the Android
     guest sees only cooked signals over IPC channel 3. [FW confirms the guest half; the far-end
     "VIP MCU" identity is prior project analysis, **[INF]/[GM]** for this build.]
   - **2026-09-27, owner's domain knowledge [USER]/[INF], not yet independently confirmed in
     firmware:** the VIP/RH850 is also believed to be the **power sequencer** for the Intel Atom
     SoC, not just the CAN↔IPC bridge — i.e. the RH850 sits on CAN in its own low-power domain,
     and only powers on the Atom (which then boots GHS, which then boots AAOS as its guest) once it
     receives the correct wake condition/CAN message. If true, the head unit's CAN presence and its
     power-on sequencing are the **same off-SoC component and the same event**, not two separate
     things — which matters for a Pi replacement: whatever fires the Atom's power rail today is a
     CAN-side decision made entirely on the RH850, before Android/GHS exists at all. A Pi
     replacement's power-on trigger would need to either replicate that RH850 wake logic (to stay
     CAN-driven and power-efficient like the OEM part) or use a simpler always-on/ignition-line
     power source and accept it isn't reacting to the same wake condition. Verifying this needs
     either RH850 firmware (separate from the Atom-side Y181B image already extracted — not yet
     obtained) or a bench power-rail trace correlated with injected CAN wake frames.
2. **Automotive Ethernet** — `igb_avb.ko` (Intel IGB + AVB/TSN) on **`eth0`**, brought up by
   `/system/bin/init_ethernet.sh`: `vlan5` = `192.168.1.100/24`, `vlan4` = `172.16.4.100/24`
   ("legacy_network"), static routes/neighbors to the peer ECUs; `daemon_cl` runs **gPTP/802.1AS**
   (`-GM` grandmaster, `audio` group) and TSN Tspec — i.e. **AVB audio + FSA/SOME-IP**, exactly the
   Plane-2 topology documented above. Switch is Marvell (`vendor.harman.ethernetswitch=mrvl`). [FW]

**Answer to Q1:** For a Pi replacement, **you do not need to make the Pi speak CAN.** The OEM radio
node presents to the rest of the vehicle as (a) an **automotive-Ethernet** node (FSA/SOME-IP on
vlan4/vlan5, AVB audio) and (b) a CAN ECU (`0x80`) **only via the far side of the GHS/VIP IPC
boundary** — a boundary that lives inside the OEM radio's own SoC and is *not* reproducible on a
Pi. The realistic Pi integration surface is the **Ethernet/FSA plane** (largely reverse-engineered
in this doc), not CAN. [INF from FW + existing doc]

### 2. Wake-up and vehicle-status signalling (as seen by the guest)

- Power/ignition state arrives as a **HIDL service, not CAN NM frames**: `vendor.gm.powermode@1.0`
  (`IPowerModing`, `IPowerModeListener`, `ISystemStateListener`). The VHAL registers for power-mode
  updates ("Failed to register for power mode updates from Power Moding service"), logs
  "Current system state: %s power mode: %s", and runs an **acknowledge** handshake
  (`acknowledgePowerModeChanged`, "power mode change complete acknowledged"). It carries an explicit
  **`BPMM_START_STOP_IGNITION_SWITCH_PRESSED_REPORT`** and an `IGNITION` state. [FW]
- So on this platform the **network-management / wake decision is made on the far (GHS/VIP) side**
  and delivered to Android as discrete power-mode transitions over IPC channel 3; the Android guest
  neither sees nor generates CAN NM traffic. [FW for the guest interface; [INF] that NM lives on the
  far side.]
- The concrete on-wire GM power-mode frame (`0x370`, `bit37:3` = Off/Acc/Run/Crank/Propulsion) is
  documented in **Plane 1a** above — but that is an **[X] Cadillac capture**, not yet confirmed on
  this Silverado, and in any case is consumed on the CAN/VIP side, not by the Android guest.
- Vehicle-status signals (speed, gear, doors, accessory) reach apps through the **standard AAOS
  VHAL property model**, sourced over `/dev/ipc/ipc3`; the raw→property mapping is the bus-frame
  decode the project is already chipping at (see MEMORY: Y181 emulator VHAL write path = bus-frame
  injection via `/dev/ipc/ipc3`). [FW/INF]

### 3. Risk of physically removing the OEM radio node

**Empirically measured — the owner has driven the truck with the radio module removed [VEH]:**

- **No RearCamera / 360 view.** Camera overlay/compositing runs on the **GHS partition of the
  radio's own SoC** (the guest ships EVS HALs — `android.hardware.automotive.evs@1.0/1.1` — but the
  actual compositing is GHS-side); remove the radio and the feed is gone entirely. [VEH] (firmware
  corroboration: EVS HALs present, and the guest is a GHS guest per §1). [FW/VEH]
- **No vehicle audio *at all*** — including **turn-signal ticks, door chimes, and safety dings**,
  not just media. The radio is the **whole-vehicle audio hub/source**, feeding the Bose amp
  (**T3**) over the **AVB Ethernet pair (bus 6, `A11↔T3`)** — see Open-items #1 above and
  `.103 = AMP_ETH`. Firmware corroboration: `vehicleaudiocontrol` registers a
  **"chime-playback-status" callback** and is gated on `vendor.gm.powermode ISystemStateListener`;
  `libgmaudiopowermode.so` exists; audio HAL + AVB/gPTP transport all live on the radio. [VEH + FW]
  - **Cross-reference for the audio-HAL owner:** a Pi replacement must source **ALL** vehicle audio
    (chimes / turn-signal / seatbelt / safety dings), not merely media playback, and drive the Bose
    amp over AVB/TSN Ethernet — materially larger scope than "play music." Flagging here; the audio
    HAL/amp details are that agent's slice.
- **Cluster gauges & safety info are unaffected.** Speedometer, engine data and all NHTSA-mandated
  displays run on the **cluster's own independent RTOS** (IPC `.106` Visteon IPC); only the cluster
  "cards" (time/temp, media, nav, calls) that the radio *feeds* go blank. Removing the radio did
  **not** degrade safety-critical cluster function. [VEH] (consistent with the doc: `.106 IPC` and
  the `.107` RTOS partition are separate nodes.) [FW/VEH]

**Not yet observed but expected [INF]/[GM]:**

- The radio is CAN **ECU `0x80`** (via the gateway `0x45`) **and** Ethernet node `.100`
  (SOME/IP-SD peer). When it disappears, other modules that expect it on the bus are likely to log
  **"lost communication with radio / IVI" U-codes** (U-network DTCs) and SOME/IP-SD peers lose the
  `.100`/`172.16.4.100` node. Whether any of these produce a **driver-visible warning** vs. a silent
  stored DTC is untested here. [INF/GM]
- Telematics/OnStar (CGM `.107/.112`, EOCM `.12/.13/.15`) and remote features depend on the
  Ethernet fabric, not on the radio specifically, so they should survive the radio's removal — but
  any HMI they render *through* the radio is gone. [INF]
- **SecOC is not a removal risk** but is a *replacement* risk: critical-control frames are
  authenticated with OEM-held keys and there is **no aftermarket provisioning path** (Plane 1a).
  A Pi cannot forge SecOC'd frames — irrelevant if the Pi stays on the Ethernet/FSA plane and never
  needs to source those CAN frames, which is the recommended posture. [X→INF]

**Bottom line:** the good news is that safety-critical vehicle function (cluster/RTOS) is
independent of the radio; the hard news is that the radio is the **camera compositor and the
whole-vehicle audio hub**, both riding partitions/transports (GHS, AVB-Ethernet) that a Pi does not
natively reproduce. CAN is *not* the integration problem here — **Ethernet/FSA + AVB audio + GHS-hosted
camera** are.

### 4. Prioritised bench / in-vehicle capture plan (for a future hardware-enabled session)

Nothing below has been done — this is a plan. Redact VIN and any real MACs/IPs before sharing
captures (this doc already flags synthetic vs. real MACs).

1. **P0 — Ethernet is the real interface: capture it first.** Tap the radio's 100BASE-T1 pairs
   (bus 6 `A11↔T3` amp, bus 2/4 gateway/telematics per Open-items #1) with a **BroadR-Reach/100BASE-T1
   media converter** into a mirror port; `pcap` on `eth0`/vlan4/vlan5 during **power-on, ignition
   on→acc→run→crank, and ignition-off**. Goals: (a) observe the FSA `0x5AA5` power-mode/system-state
   exchange the `vendor.gm.powermode` service consumes; (b) map which SOME/IP-SD services vanish when
   the radio is pulled; (c) confirm/deny a **VLAN-502 CAN mirror** on this unit (Open-items #6).
2. **P0 — decode the IPC vehicle channel.** With the radio powered on a bench harness, log
   **`/dev/ipc/ipc3`** (lchannel 3) and correlate against known transitions (ignition, gear, speed)
   to finish the raw-frame→VHAL-property map (ties into the emulator VHAL work). This is the payload
   a Pi's VHAL backend would ultimately need to emulate.
3. **P1 — power/wake sequencing.** Scope the radio connector's **switched-battery / wake / accessory**
   pins during KL30/KL15 transitions to learn what actually powers the module and whether wake is a
   hard line or a bus event. Cross-check against `BPMM_..._IGNITION_SWITCH_PRESSED_REPORT` timing.
4. **P1 — CAN only if/when needed.** Only if the Pi must originate CAN (it likely must not): tap the
   vehicle CAN at the **gateway `0x45`** side with a USB-CAN adapter and log NM/wake + status frames
   during the same transitions. Expect the radio itself **not** to be a raw-CAN source (per §1), so
   this characterises the *gateway/VIP* behaviour, not the radio.
5. **P2 — removal-DTC survey.** With a GM-capable scan tool (MDI2/DPS, see `../diagnostics/`), pull
   DTCs from gateway `0x45` and neighbouring modules **before and after** radio removal to enumerate
   exactly which U-codes fire and whether any surface to the driver. Answers the real
   feasibility-blocker for the swap.
6. **P2 — audio-hub scope proof.** Confirm the amp (T3) is a pure AVB-Ethernet sink with no local
   chime generator, i.e. that a Pi would have to synthesise every chime/ding and stream it over AVB.
   (Coordinate with the audio-HAL slice.)

See also: [`../hardware/connectors.md`](../hardware/connectors.md) (physical harness that carries
these buses) and [`ota_programming_roles.md`](ota_programming_roles.md) (module programming over
this network).

---

## Plane 3 — Audio amp + LVDS panel/touch interconnects (Pi-swap feasibility) — added 2026-09-27

Scope: the physical transport of (a) audio between the A11 radio and the amp/speakers, and
(b) video + touch between the A11 radio and the center display. Goal is to judge whether a
Raspberry Pi (4/5) running custom AAOS could re-originate/terminate these same OEM
interconnects, or must fall back to commodity parts. Every claim below is tagged
**[confirmed-fw]** (seen in the extracted Y181B firmware), **[confirmed-vehicle]** (from the
owner's real radio-removal test), **[confirmed-service]** (GM ALLDATA / prior repo docs), or
**[inferred]** / **[general]** (automotive-platform knowledge, not this-vehicle-specific).

Firmware evidence base: `Y181B_cleanroom.img` (ext4, read via `7z`; not mountable on macOS —
no `debugfs` present). Platform is **Intel Apollo Lake / "broxton", x86_64, kernel 4.19.305**,
Android 12 under the GHS hypervisor — *not* an ARM/Qualcomm SoC. This matters: the audio and
display blocks are Intel-SoC peripherals (Intel SST/SOF DSP, i915 display), so a Pi (ARM,
VideoCore/DSI) is a different silicon family at both ends.

### 3a. Audio — transport to the amp

**Two amp paths exist in the firmware; this vehicle uses the Ethernet-AVB one.**

- **[confirmed-fw]** On-SoC audio is Intel SST DSP → I2S/TDM → **NXP TDF8532** 4-ch class-D
  amplifier-codec. Driver `snd-soc-tdf8532.ko` (`sound/soc/codecs/tdf8532.c`, `alias=i2c:tdf8532`)
  + Intel machine driver `snd-soc-sst_bxt_tdf8532.ko`. Amp control is I2C: `init.audio.rc`
  chowns `/dev/i2c-3` to `audioserver` (matches `hardware.md`: "i2c-3 = TDF8532 codec control").
- **[confirmed-fw]** A full **automotive Ethernet AVB** audio stack is present and is what gates
  audio bring-up:
  - `vendor/lib/modules/igb_avb.ko` — Intel I210 GbE driver with AVB/TSN extensions (mainline
    `igb` is disabled per `hardware.md`).
  - An **AVB StreamHandler** service (COVESA/GENIVI-style, IEEE 1722/AVTP). `init.audio.rc`
    blocks on `init.svc.vendor.avbstreamhandler=running` and `vendor.avb.streamhandler.ready=true`
    before starting PulseAudio and the audio HAL.
  - `service vendor.earlyavbaudio /vendor/bin/early_audio_alsa_avb.sh` — **early-boot AVB audio**,
    i.e. audio over AVB before Android is fully up. This is the likely carrier for
    safety-relevant early chimes.
  - Route/param configs select transport: default `persist.vendor.audio.audioConf =
    AudioParameterFramework-tdf8532-no-eavb.xml` (local I2S to TDF8532), with alternates
    `…-eavb-master-raw.xml`, `…-eavb-master.xml`, `…-eavb-slave.xml`, keyed on
    `persist.vendor.eavb.mode` and AVB profile names `MRB_Master_Audio` / `MRB_Slave_Audio`
    (IEEE 1722a compatibility flag `d6_1722a`). Same SST DSP, switchable output route.
- **[confirmed-service]** For *this* vehicle the active path is Ethernet AVB to an **external
  Bose T3 amplifier**: Open item #1 above records GM ALLDATA *Data Link Communications* data —
  physical Ethernet **bus 6 (ports 7214/7215) = A11↔T3 Bose amp, "the AVB audio pair."** The
  A11's Intel **I210 is gPTP grandmaster** for that AVB domain (`hardware.md`). So the default
  `no-eavb` config in the generic image is a base-trim/build fallback; the LTZ-with-Bose truck
  streams IEEE-1722 audio over Ethernet to T3. (The local TDF8532 I2S path is almost certainly
  the base-audio, no-Bose variant — **[inferred]**.)
- **[confirmed-vehicle] Scope increase — the radio is the whole vehicle's audio hub.** With the
  A11 radio physically removed the owner had **no audio at all — no media, and no turn-signal
  ticks or door chimes.** Chimes/turn-signal audio are generated by a body/chime module
  elsewhere but are *rendered to the speakers through the radio*. Mechanism is consistent with
  both firmware facts: the radio is either the mixer/source of that audio **or** the AVB gPTP
  grandmaster — remove it and the AVB clock domain collapses and T3 goes silent regardless of
  who sourced the stream. A Pi replacement therefore cannot just "play infotainment audio"; to
  preserve today's behavior it must also (i) act as gPTP grandmaster for bus 6, and (ii)
  carry/relay the chime/turn-signal audio path to the speakers. Dropping (ii) means **losing
  turn-signal and seatbelt/door chime audio** — an FMVSS/NHTSA-adjacent expectation
  (e.g. seatbelt-reminder audibility); flag as a real safety/legal tradeoff, not a nicety.

**Audio feasibility (Pi):**
- **AVB reuse is plausible and is the same physical network already decoded (FSA), just a
  different pair/protocol. [inferred, medium confidence]** Linux has the pieces: a TSN-capable
  NIC (Intel I210/I225/I226, or a USB/HAT with TSN), `linuxptp` for 802.1AS/gPTP (Pi would need
  to be grandmaster), the kernel `AF_PACKET`/ETF/TAS qdiscs + `libavtp`, and the **open-source
  COVESA AVB StreamHandler** — the very component this firmware runs. The Pi 4/5 on-board NIC is
  **not** TSN/AVB-capable, so this needs an add-on TSN NIC; the RPi CM4/CM5 + a carrier with an
  I210/I226 over PCIe is the realistic route. Hard parts are matching Bose T3's exact AVTP stream
  format/SRP reservations and the gPTP timing, which are undocumented — bench capture required.
- **The local-I2S TDF8532 path is not a realistic Pi target [inferred].** It presumes a directly
  wired NXP amp with proprietary I2C control; a Pi's I2S/TDM to a foreign amp is fragile and
  this truck's amp is external over AVB anyway.
- **Pragmatic fallback [general]:** don't preserve the OEM amp bus. Feed the existing speakers
  from a Pi audio out (analog line-out via a USB/HAT DAC, or the Pi driving a simple aftermarket
  class-D amp), accepting loss of Bose DSP tuning and — critically — arranging chime/turn-signal
  audio some other way (or accepting its loss, with the safety caveat above).

### 3b. Video panel + touch

- **[confirmed-service]** Panel is **Chimei Innolux DD134IA-01B, 2400×960 @ 60 Hz, ~13.4"**
  (`hardware.md`; system `lcd_density=200`, physical ~193 dpi).
- **[confirmed-fw]** The display link off the head unit is **TI FPD-Link III, not raw LVDS from
  the SoC.** Driver `ti949_serdes.ko` (`drivers/video/gm-serdes/ti-949.c`) is a **TI DS90UB949
  serializer**; its recovery routine `reinit_ti949_948` names the partner **DS90UB948
  deserializer** at the panel. Signal chain: i915 (eDP/DP or LVDS out of the Intel SoC) →
  **DS90UB949 serializer** → single FPD-Link III coax/STQ → **DS90UB948 deserializer** at the
  panel → LVDS into the panel TCON. The user's "LVDS" is the *last hop only*, downstream of the
  deserializer. Serializer control is I2C: `init.bxtp_gm.rc` chmods `/dev/i2c-7` and `insmod`s
  `ti949_serdes.ko`; a `949-errata-fix` service and `evs_app` run alongside (the serdes init
  lives in the **EVS/camera** mixin).
- **[confirmed-fw]** Touch = **Atmel maXTouch** (`atmel_mxt_ts.ko`, `insmod` at
  `init.bxtp_gm.rc:73`), on **I2C bus 7 at address 0x4B** (`.../atmel_mxt_ts/7-004b/reinit_mxt`;
  matches `hardware.md`: "Atmel maXTouch, 16-point, I2C-7 @ 0x4B"). 16-point multitouch.
- **[inferred, high confidence] Touch I2C is tunneled back over FPD-Link III.** The maXTouch and
  the DS90UB949 serializer share the *same* i2c-7 bus, and `reinit_mxt` is paired with
  `reinit_ti949_948` (re-init serdes → re-init touch after a link drop). In FPD-Link III the
  DS90UB948 bridges a remote I2C segment back over the coax to appear as a local bus on the head
  unit. So the display is an **integrated module** (LVDS panel + DS90UB948 deserializer + Atmel
  maXTouch), joined to the radio by **one FPD-Link III coax** carrying forward video + a
  bidirectional back-channel I2C (touch + serdes + backlight control).
- **[confirmed-vehicle]** With the radio removed there is **no rear/360-camera overlay** on the
  display — camera compositing (EVS: `evs_app`, `earlyEvs_harman`, the 949 errata service) runs
  on the radio's own Intel SoC/GHS. Independent confirmation that the panel is driven **directly
  by the radio unit's SoC**, with no separate video ECU in the path. (Owner also confirms the
  instrument cluster is a separate independent RTOS, unaffected — out of scope.)

**Panel/touch feasibility (Pi):**
- **Video: a bridge-chip problem, not raw LVDS. [inferred/general]** A Pi has no LVDS *or*
  FPD-Link III output. To drive this exact OEM panel the Pi would need to *originate* FPD-Link
  III — i.e. drive the panel's DS90UB948 deserializer from a Pi source. Practical route: Pi
  DSI/HDMI → an LVDS bridge (e.g. TI SN65DSI84 DSI→LVDS) → a DS90UB941/949-class serializer to
  the panel's 948; or replace the panel-side deserializer board. This is buildable from
  catalog TI FPD-Link III parts but is **bespoke integration** (link training, I2C-passthrough
  mapping, backlight/PWM, exact DS90UB948 strap config), not a plug-in. Panel timing for the
  2400×960 mode must be matched (not fully enumerated in firmware here — **open**).
- **Touch: the tractable half. [inferred, high confidence]** If the video path is otherwise
  solved, the Atmel maXTouch is a standard I2C device (0x4B) with a mainline `atmel_mxt_ts`
  driver; a Pi can read it directly on one of its I2C buses (plus the maXTouch CHG/interrupt
  line), independent of the FPD-Link back-channel, *if* the touch controller can be wired to the
  Pi's I2C rather than being trapped behind the deserializer. If it must stay behind the 948,
  the Pi gets it via the serializer's I2C passthrough — same bridge work as video.

### 3c. Recommendation

- **Audio:** the OEM path *is* worth considering because it rides the already-mapped automotive
  Ethernet — a CM4/CM5 + TSN NIC running linuxptp + the open COVESA AVB StreamHandler could, in
  principle, re-originate the bus-6 AVB stream to the Bose T3 amp and be gPTP grandmaster. But
  the stream-format/SRP details and the chime/turn-signal relay are unproven and safety-relevant.
  For a first cut, the **analog/USB-DAC-into-amp fallback** is far lower risk; escalate to real
  AVB only after a bench capture of the A11↔T3 stream.
- **Panel/touch:** preserving the OEM LVDS/FPD-Link III panel is the **higher-risk half** —
  bespoke serializer integration for fit/finish, and the panel is physically dash-integrated
  (~13.4" 2400×960 shaped module). Unless dash fit is a hard requirement, the far simpler path
  is a **commodity touchscreen driven natively by the Pi** (DSI/HDMI + USB/I2C touch), abandoning
  the OEM panel interconnect. Reuse OEM panel only if you accept custom FPD-Link III bridge
  hardware. Touch alone is easy; video is where the engineering risk concentrates.

**Confidence summary:** chip identities, buses, and transport *mechanisms* are **[confirmed-fw]**;
the this-vehicle amp topology (AVB→Bose T3) is **[confirmed-service]**; the radio-as-audio-hub and
local-panel-compositing facts are **[confirmed-vehicle]**. All Pi-side feasibility statements are
**[inferred]/[general]** — no Pi hardware was tested here.
