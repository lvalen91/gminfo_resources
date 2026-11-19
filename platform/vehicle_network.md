# Vehicle Network Topology — 2024 Silverado 2500 HD LTZ (ICE, gminfo37 / A11 Radio)

Two-plane vehicle topology: ECU census, gateway/radio diagnostic IDs, Ethernet vlan4/vlan5 plane map,
SecOC plane (external research), join points, resolved/open items. Topology only — message tables,
security findings, audio transport and Pi-swap analysis live in the linked docs.

**Evidence tags.** **[C]** = confirmed by ≥2 sources or a primary capture; **[?]** = single-source or
contested; **[X]** = external / other-vehicle source (e.g. surrealdev Cadillac captures), not yet
confirmed on this A11 unit. Sources disagree on several node labels; both values are shown where they do
(see [Open conflicts](#open-conflicts)).

**Related:** [ethernet_networking.md](ethernet_networking.md) (interfaces, VLAN tables, switch config, ports, bus map) ·
[can_network.md](can_network.md) (72-ID bench dictionary, harness isolation, public DBC comparisons) ·
[fsa_protocol.md](fsa_protocol.md) · [security.md](security.md) · [ota_programming_roles.md](ota_programming_roles.md) ·
[avb_audio_transport.md](avb_audio_transport.md) · [pi_swap_feasibility.md](pi_swap_feasibility.md) ·
[qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md) · [emulator.md](emulator.md) ·
[`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md) ·
[`../hardware/connectors.md`](../hardware/connectors.md)

Primary sources: the `A11_CSM_x80` DPS log ([`../diagnostics/dps/A11_CSM_x80.Txt`](../diagnostics/dps/A11_CSM_x80.Txt)),
the Y181 ADB enumeration ([`../enumeration/Y181/`](../enumeration/Y181/)),
[`../research/GM_REMOTE_ACCESS_ANALYSIS.txt`](../research/GM_REMOTE_ACCESS_ANALYSIS.txt),
[`../research/VIP_CONTROL_ANALYSIS.txt`](../research/VIP_CONTROL_ANALYSIS.txt),
[`../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md),
the FSA notes ([fsa_protocol.md](fsa_protocol.md)) and the ethernet-UDS notes
([`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)).
Originally consolidated 2026-07-01; content current through 2026-11-17.

---

## Headline

Two planes joined **inside the radio**, plus a physically-distinct gateway/telematics path:

1. **CAN diagnostic plane** — GM VIP/SDV1 (Global B), 29-bit UDS; radio reaches it *only through its VIP MCU*.
2. **Automotive-Ethernet service plane** — two VLANs, GM FSA + SOME/IP, bridged by an Ethernet gateway/router.

Radio is dual-homed: **ECU `0x80` on CAN** and **`192.168.1.100` on Ethernet**.

---

## Plane 1 — CAN (from the DPS scan)

DPS 4.56 over **LS-CAN through the central gateway**; **24 ECUs** enumerated
([`../diagnostics/dps/A11_CSM_x80.Txt`](../diagnostics/dps/A11_CSM_x80.Txt)). VIN present — redact when sharing.

- **Central gateway = ECU `0x45`** — wake-up + ECUID reads route through it; response uses the physical
  `14DAF245` pattern, unlike every other module's `14xAF2xx`. [C]
- **Radio = ECU `0x80`** — ECUID `004B41DC…14AC` (matches EEPROM/teardown); LS-CAN via the gateway with tester
  ID **F2**: ReqCANId `0x14DA80F2` / RspCANId `0x145AF280` (confirmed: `diagnostics/dps/A11_CSM_x80.Txt:160` —
  every ECU in the scan uses F2; F1 is the generic OBD tester address, not seen here). [C]
- **Segmented buses** behind `0x45`: HS-CAN + LS-CAN + AUTOSAR "SER DATA 5" (seen on the connector harness,
  see [`../hardware/connectors.md`](../hardware/connectors.md)). [C]
- **Naming equivalence (2026-11-13) [C]:** "SER DATA 5" and connectors.md's "AUTOSAR CAN 5" are the **same
  physical circuit pair** (4984/4985, radio X6 p9/10) — two GM naming conventions for one wire pair, not two
  buses. That pair also carries the amp's control/discovery link (CAN 5 is the control-plane half of T3's two
  separate links to the radio; the audio data-plane half is Ethernet Bus 6 — see
  [`../hardware/connectors.md`](../hardware/connectors.md) §Audio Architecture — Bose) and is reused for a
  distinct bench-only role by the OPU Wiring Tester + Emulator (same connectors.md section).
- **Diagnostic addressing summary** (CAN address ↔ module): **CSM** (Center Stack Module = the radio/head unit)
  `0x80`; **CGM** (Central Gateway Module) `0x45`. The two UDS paths to the radio are CAN/DPS
  ([`../diagnostics/dps/`](../diagnostics/dps/)) and Ethernet/TCP via root `diagnosticsd` on port 49156
  (GM Ethernet diag address `0x0084`, 8-byte header); trust tiers and seed/key behaviour are in
  [security.md](security.md) and [`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md). The UDS service-ID table is in [vehicle_config.md](vehicle_config.md#uds-diagnostic-services-used-by-dps).
- **VIN arbitration IDs `0x712`, `0x75F`, `0x49B`** are **[X] Cadillac captures** (Qualcomm radio VIN gate;
  see [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md) §Boot & VIN gate). This Silverado uses
  `0x80`/`0x45` diagnostic addressing; the IDs are absent from the bench dictionary
  ([can_network.md](can_network.md)) — do not assume they carry over.

### ECU census (diagnostic addresses)

The `A11_CSM_x80` DPS scan enumerated **24**; a later live MDI2 DoIP read (`dps_readx80`, F1B0 broadcast,
2nd pass) found **27**, adding **`0x6B` `0x84` `0x96`** (the three true Ethernet/DoIP nodes alongside gateway
`0x45`; every other address incl. radio `0x80` is CAN-via-gateway). Combined 27:

`0x11 0x18 0x1A 0x28 0x31 0x40 0x41 0x45(gw) 0x58 0x59 0x60 0x68 0x6B(eth) 0x6D 0x75 0x80(radio) 0x81 0x84(eth) 0x96(eth) 0x97 0xA4 0xA8 0xB9 0xBA 0xBD 0xBE 0xBF`

Response-ID priority nibbles group modules by bus/priority; the complete address→function map remains open
(Open item 2).

### SecurityAccess on the radio (summary; owner: security.md)

Corrected 2026-11-11: target radio `0x80` normal SecurityAccess is 31 seed bytes (16-byte fixed identifier +
15-byte varying suffix), 12 response bytes and `67 02`; the earlier 8/6 count was incorrect. The EEPROM/ADB,
UDS, ProtoKey and signing gates must remain separate. A returned MEC `F1A0=FF` lies in the 1–255 range that
bypasses the SoC's GM ADB client-certificate requirement; it is not enforced-secure mode, and the SPS
host-authorization error does not prove the cause of an all-FF ECU seed. Details and MEC `F1A0` semantics:
[security.md](security.md#mec-manufacturer-enable-counter);
central evidence guide: [`../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

---

## Plane 1a — SecOC (CAN frame authentication) [X]

> **Source.** External public research — Snipesy / Surreal Development, *"Rooting the Cadillac Part 2: SecOc"*,
> 2026-09-22 (`https://surrealdev.com/rooting-the-cadillac-part-2-secoc/`; bibliography:
> [external_references.md](external_references.md), [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md)),
> captured on **Lyriq / CT5** Global-B vehicles. Same Global-B platform as this Silverado, so the algorithm is
> expected to hold, but the frame IDs, keys and the VLAN-502 mirror are **Cadillac captures — not yet observed on
> this A11/gminfo37 unit.** Confirm before relying on it here.

Global B is *mostly* unsigned/unencrypted (especially CAN5), but selected **critical-control** frames carry a
**SecOC** message-authentication code. Frames are authenticated, **not encrypted** — anyone can parse them, and
many modules still act on a frame whose MAC fails. The Central Gateway selectively forwards between buses and
sometimes checks the MAC, sometimes not. MAC'd frames tend to be things like power steering — and the modules
that consume them may not even be on the radio's bus, so the radio itself rarely needs to satisfy SecOC. [X]

**MAC construction:**

```
MAC = CMAC_AES128_k( data_id(u8) ‖ BE32(can_id) ‖ BE64(freshness) ‖ payload )
```

- MAC on the wire is the CMAC **truncated to 27 bits** (3 bytes + 3 bits).
- Freshness is a 64-bit BE counter, often combined with a secondary companion ID; padding and payload position
  vary per frame.
- Donor-vehicle key and worked MAC values are omitted; they are not target-radio credentials.

**SecurityAccess formula scope (corrected 2026-11-11):** the Cadillac source's proposed CMAC construction is not
target-radio evidence. The gminfo37 capture independently establishes 31-byte normal seeds and 12-byte accepted
responses; the exact target key derivation and usable master secret remain unresolved. No Cadillac vector or key
is a gminfo37 signing/unlock credential.

**SecOC key provisioning** (UDS RoutineControl, after $27): the on-wire key is itself encrypted against a factory
key. Provisioning needs three secrets, all OEM-held: the module's unique **$27 unlock key**, the
**HSM/identifier ID**, and a factory/assembly-line **master key**. Install uses the **SHE KDF
(Matyas-Meyer-Oseas over AES-128)**: [X]

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

**Bottom line for aftermarket repair:** only the OEM servers hold the master keys and there is no aftermarket
provisioning path — a shared-key module cannot be swapped in without the OEM secrets. The author claims
(unpublished, zero-days withheld) that all SecOC keys are dumpable from any module "with no exploit, if you think
fast enough" — **unverified, no method given.** [X]

**Power-mode frame (external):** Surreal Part 2 describes CAN5 at 500 kbit/s and an external `0x370` field,
`bit37:3`: **Off=1, Accessory=2, Run=3, Crank=4, Propulsion=5**. [X] `0x370` is absent from the bench
dictionary and that enum must not be merged with Global A `0x1F1` — see [can_network.md](can_network.md)
(published-candidate comparison). It is consumed on the CAN/VIP side, not by the Android guest (the guest gets
discrete power-mode transitions over IPC channel 3; see [pi_swap_feasibility.md](pi_swap_feasibility.md)).

---

## Plane 2 — Automotive Ethernet (VLAN 4 / 5)

Backbone: 100BASE-T1 via on-board switch (host on port 5; gateway/telematics on port 2).

- **Switch IC is board-variant:** **Broadcom BCM89551** on MY22/DV boards, **Marvell 88Q5050** on MY23+ (selected
  per `persist.vendor.harman.hardwareid`; selector inferred — the prop is not shell-readable). Same port layout
  and spec. Variant detail: [hardware_specs.md](hardware_specs.md), [ethernet_networking.md](ethernet_networking.md).
- **Bench radio:** logged hardwareid `MY23DV1` per the `/cache` gmlogger props snapshots (2026-11-12). Live
  Y181 bench radio (2026-11-12) = **Marvell** (`ethmvlctrlmgr: Marvell firmware version: 02_09_1003, config
  version: 234702AB`, part 85759612).
- **The vehicle trim carries three physical automotive-ethernet connections to this switch** (owner, in-vehicle;
  not wired on the bench).

> **[C] Bench discovery result (2026-10-06, live Y175 via `gm_bench_agent` `mcast.listen`, strictly passive).**
> The ethernet **service-discovery plane is silent on the bench**: `/proc/net/igmp` shows the HU joins **mDNS
> `224.0.0.251`/`ff02::fb`** + all-hosts `224.0.0.1` on vlan4/vlan5/eth0 — but **NOT** the SOME/IP-SD group
> `239.192.0.1`. A 25 s passive listen on `239.192.0.1:30490` and `:3000` and a 20 s listen on mDNS
> `224.0.0.251:5353` **all returned 0 packets** (joins succeeded on vlan4/vlan5/eth0, no SELinux denial,
> `sends:0`). **Cause:** the three in-vehicle automotive-ethernet links are unconnected on the bench, so no AE
> peer ECU/switch is advertising — the HU is *ready* to participate but has no partners. SOME/IP-SD
> `239.192.0.1:30490` therefore reflects the *firmware/in-vehicle* config, not a bench-active service. The
> harness (`~/gm_bench_agent`, `untrusted_app`, listen-only) is validated and would map the real OfferService
> graph **in-vehicle** or with the bench AE links bridged to the vehicle backbone. (A 3P `untrusted_app` CAN
> join these groups + `MulticastLock` with no root — only the privileged `/proc/net/igmp`/netlink reads are
> SELinux-denied to it.)

### vlan5 · `192.168.1.0/24` ("Info3x" service network)

| IP | Node | Conflict / note | Conf. |
|----|------|-----------------|:----:|
| .100 | **CSM / IVI — this radio (Android guest)** | — | [C] |
| .102 | **Ethernet gateway/router** (DNS `dnsmasq`, SOME/IP-SD), labeled **`TCP_ETH`** | FSA notes call it "TCP = Telematic Comm Processor" hosting OnStar/TurnByTurn/RemoteReflash; live scan sees it as the DNS/SOME-IP **inter-VLAN router** (shares MAC with `172.16.4.1`). Likely a telematics-comm processor that *also* routes. | [?] |
| .103 | **AMP_ETH** — audio amplifier (**Bose**, owner-confirmed) | doc label is generic "Amplifier" | [C] |
| .104 / .105 | RSI1 / RSI2 (rear-seat) — offline on bench | — | [?] |
| .106 | **IPC — Instrument Panel Controller** (Visteon cluster; DeviceInfo `Company=Visteon, Module=IPC`) | older note mis-expands as "Inter-Process Communication" | [C] |
| .107 | **CGM host processor / telematics** | identity vs .112 and vlan4 `.107`: see [Open conflicts](#open-conflicts) #1 | [C] (label) / [?] (identity) |
| .108 / .110 | LOWRADIO / PDR — offline | — | [?] |
| .112 | **CGM_ETH / CGM_OTA** — Connectivity Gateway Module / telematics | vlan4 face `172.16.4.112` has the only **real/universal-OUI MAC** `10:66:50:...` (OUI `10:66:50` = **Robert Bosch "JuP1"** [C nmap-mac-prefixes; GM_research ref_repo/gminfo37_network_research.md:146-153]), heavily firewalled | [C] |
| 239.192.0.1 | SOME/IP-SD multicast (live scan: UDP **30490**) | — | [C] |

Most vlan5 peers use `02:0x:00:00:0x:00` locally-administered MACs = hypervisor virtual NICs / co-resident GHS
partitions bridged onto the physical backbone.

**Identity evidence (History: 2026-10-06 correction).** An earlier version of this note claimed the Bosch device
(real OUI) **and the RTOS partition** are unambiguously separate hardware. The RTOS-partition half is **wrong**.
ARP evidence (`enumeration/Y181/*/raw/arp_table.txt`, `enumeration/Y181/jun2026/enumeration_report.txt:7477-7482`):
the RTOS/diagnostic endpoint `172.16.4.107` carries MAC **`02:05:00:00:02:00`** — locally-administered (bit-1 set),
i.e. a hypervisor virtual NIC, **not** real silicon — and that **same** virtual NIC is dual-homed as
`192.168.1.112` on vlan5 (`arp_table.txt` confirms identical MAC): a single co-resident GHS partition bridged onto
both VLANs, like the Android guest's own `.100`-on-both. So the **only** unambiguously-separate hardware on these
VLANs is the real/universal-OUI device: **vlan4 `172.16.4.112` = `10:66:50:0c:ed:d3`** (Bosch "JuP1" [C
nmap-mac-prefixes; GM_research ref_repo/gminfo37_network_research.md:146-153]; the raw scan's "possibly
Harman/Samsung" guess is superseded), the external CGM/telematics module. The `.107` "RTOS partition" is
**SoC-internal** (a GHS-hosted INTEGRITY partition on the same Intel A3960), corroborated by its response
**TTL=255** vs the external `.112`'s **TTL=64** (Linux) — see [ethernet_networking.md](ethernet_networking.md) vlan4
table and the "vlan4 internal-vs-external" finding in
[`../diagnostics/diagnosticsd_network_topology.md`](../diagnostics/diagnosticsd_network_topology.md#vlan4--internal-ghs-fabric-diagnosticsd-forwarding-target-bench-reachability-of-the-vipuds-path-2026-10-06).
(Internal inconsistency of this evidence — vlan5 `.112` is both the virtual-NIC `02:05:...` partition and the
Bosch CGM — is listed in [Open conflicts](#open-conflicts) #1.)

### vlan4 · `172.16.4.0/24` (internal vehicle network)

`.100` IVI (radio's vlan4 face) · `.1` router (shares MAC with `.102`) · `.14` **ACP** · `.107` RTOS partition ·
`.12/.13/.15` **EOCM** (Enhanced OnStar). Other-variant subnets `192.168.118.x` / `172.16.5.x` are code-referenced,
not live. `br0` (`192.168.5.1/24`, members `wlan1`/`wlan2`) is the Wi-Fi/phone-projection AP bridge, **not** a
diagnostic plane.

### Physical bus ↔ VLAN map (ALLDATA *Data Link Communications* + live tap)

| Ethernet bus | Circuits | Peer | Notes |
|---|---|---|---|
| **2** | 4757/4758 | A11 ↔ K56 gateway | live-tapped; carries VLAN 2/5/4 + untagged (below) |
| **4** | 7210/7211 | A11/K56 ↔ K73 telematics | |
| **5** | 7212/7213 | A11 ↔ P22F rear video | |
| **6** | 7214/7215 | A11 ↔ T3 Bose amp | the AVB audio pair; see [avb_audio_transport.md](avb_audio_transport.md) |
| **14** | 7230/7231 | A11 ↔ P29 HUD | |

Full physical bus map (other buses Eth 1/3/7/11/15, X84 pinout, X11 connector caution): [ethernet_networking.md](ethernet_networking.md#physical-automotive-ethernet-bus-map).

**Bus 2 carries a tag-multiplexed trunk (direct T1 tap, Y175_2026-11-02, updated 2026-11-11).** The same
physical pair carries **VLAN 2** (PCP 2, AVB/TSN audio, ~2,900 pps flood, harmless bench artifact), **VLAN 5**
(PCP 1, `192.168.1.0/24` Info3.x service plane, radio `.100`), **VLAN 4** (PCP 1, `172.16.4.0/24` internal/diag
plane, radio `.100`) and untagged native traffic — not per-pair-segregated. Root cause of the earlier
"IP-segment↔bus correlation needs a per-pair capture" blocker: a plain Ethernet switch in the tap path silently
stripped 802.1Q tags (not a duplex mismatch); a direct media-converter → USB-GbE NIC link (no switch) preserves
tags end-to-end.

Second tap session (2026-11-13, same hardware):
- The T1 polarity swap is needed on **every** re-cabling of the converter, not just the first (treat as unreliable
  "adaptive polarity", not a one-time wiring mistake).
- The VLAN 2 flood decodes as **3 IEEE-1722 AAF audio streams + 1 TSCF/ACF control stream**.
- **gPTP:** 146 frames from the radio's MAC to `01:80:c2:00:00:0e` were live-captured, confirming gPTP
  *transmission*. The configured grandmaster role (`daemon_cl -GM`, `igb_avb.ko`) is firmware evidence; packet
  presence alone does not establish the elected role (corrected 2026-11-15; see
  [avb_audio_transport.md](avb_audio_transport.md) / [ethernet_networking.md](ethernet_networking.md)). Any
  statement elsewhere that the radio *is* the AVB grandmaster should be read as "configured grandmaster".
- The radio periodically (~4 s) SYNs *toward* the posed gateway identity on 9005/9012 — see
  [fsa_protocol.md](fsa_protocol.md).
- A second T1 adapter on **X11 pins 1/2** (previously "not occupied" per
  [`../hardware/connectors.md`](../hardware/connectors.md) X11 row) proved live, with the identical VLAN trunk and
  9016/49156 allow-list as Bus 2 but the **opposite PHY master/slave role**. Identity open [?]: spare internal
  switch port, an as-wired Bus 5/14 deviation, or a cavity-counting error are all still live.

Canonical tap writeup: `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` (§9.1 addendum, §14) and
`Y175_LIVE_RADIO_T1_SECURITY_ASSESSMENT_2026-11-02.md`.

### Reachable services and host firewall (topology summary; findings: security.md)

Exhaustive bench sweep (all 253 source IPs per /24 × full TCP 1–65535, direct tap; Y175_2026-11-02 §7.1–7.2,
2026-11-11) found exactly:

| Plane | Endpoint | Service | Allow-listed source IPs |
|---|---|---|---|
| vlan5 | `192.168.1.100:9016` | NetworkAccessManager (NAM) | `.102`, `.112` |
| vlan5 | `192.168.1.100:9002` | RemoteModuleHMI | `.106`, `.109`, `.112` |
| vlan4 | `172.16.4.100:49156` | `diagnosticsd` | `.107`, `.112` |

No undocumented allow-listed identity and no undocumented listening port exist in either /24;
`9010/9011/9012/9021/9022/9025/5555` are not even listening on the bench (absence, not a hidden plane).
`.112` (CGM) is the single identity reachable on both planes.

Firewall summary: `INPUT` is a bare default-DROP policy (no per-port DROP rule; no 5555 exception), `OUTPUT`
ACCEPT; every ACCEPT rule matches only `(source IP, dest port)` with no awareness of which daemon owns the port.
Consequences (live-proven 2026-11-13 [C]): ADB relocated onto an allow-listed-but-unbound port of a different GM
service (via port 9040 posed as `.104`) is passed unconditionally; `adb tcpip 5555` succeeds over USB and binds
`[::]:5555` but inbound TCP/5555 stays firewalled (DROP) on both Bus 2 and X11 pins 1/2. FSA servers are
single-client; NAM brokers **EAP-AKA** cellular attach + VLAN grants. The findings, the unauthenticated raw-shell
variant and its local-launch prerequisite are recorded in [security.md](security.md) and
`source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.2–9.3 (not restated here).

### Service / protocol layer (topology view; wire formats: fsa_protocol.md)

- **GM FSA** — 20-byte big-endian header, magic **`0x5AA5`**, protobuf; services by port: 9002 RemoteModuleHMI,
  9005 OnStarFunctions, 9010 DeviceInformation, 9011 ProgrammingMaster (confirmed **dead code**: compiled in,
  never instantiated or bound), 9012/9018 RemoteReflash(UI), 9016 NAM, 9020 DisplaysCoordination. Framing
  confirmed on the wire (live unauthenticated GET/SUBSCRIBE round-trips with the real cluster service on `9002` **in the emulator**; jadx RE of ClusterService/DeviceInformationService). No authentication of any kind
  (see [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md)). Header fields, opTypes,
  serviceIds, parser bugs and the cluster-injection surface: [fsa_protocol.md](fsa_protocol.md). [C]
- **SOME/IP-SD** present (UDP 30490 / 239.192.0.1). [C]
- **`:49156`** — confirmed root `diagnosticsd`, a **custom 8-byte GM-header UDS bridge, NOT DoIP** (SRC/TGT addr +
  PAYLOAD_LEN; ECU `0x0084`, validated tester `0x00F4`). Direct forwarding to the RTOS diagnostic partition is not
  established ([`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)). The
  `MaxPayload 49156` printed by the external DoIP tester at connect is a **coincidental numeral**, not this
  socket. **Corrected 2026-11-14:** the old NRC `0x10` probes used an invalid tester ID; tester F4 plus extended
  session yields the 31-FF seed and `67 02` after a 12-zero-byte response — not root or programming-write proof. [C]

### vlan502 · CAN-over-Ethernet mirror (Cadillac capture) [X]

The original [Cadillac SecOC research](https://surrealdev.com/rooting-the-cadillac-part-2-secoc/) reports CAN
mirroring on VLAN 502 using UDP multicast port 59200 on the examined Lyriq/CT5 network (source was
`172.16.50.207→239.192.0.9:59200`). This is cross-platform evidence, not proof that the A11 bench tap exposes the
same mirror; switch forwarding and vehicle state matter.

**Passive bench checks, 2026-11-15: no mirror observed.** An unfiltered 30.019 s T1 capture contained 89,385
frames: VLAN 2=89,176, VLAN 5=84, VLAN 4=9 and untagged=116. It contained zero VLAN 502 frames, zero UDP
source/destination port 59200 packets and zero packets to the article's mirror multicast group. AVTP (89,176) and
PTP (114) provided positive capture controls; kernel drops were zero (90,223 received by filter versus 89,385
captured at termination). The earlier `radio-en12-20261114.pcapng` also had zero matches for
`vlan.id == 502 || udp.port == 59200` across 615,366 frames/391.770719 s. These negatives apply only to the
sampled bench tap, interval and emulator CAN state, which was not independently established; they do not disprove
a vehicle-side mirror. No NIC reconfiguration, CAN injection, active probes or ADB was used.

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
No authentication of any form on the in-vehicle Ethernet at L2/L3 (no **IPsec**, no **MACsec**) on the vehicles
the author examined; only niche services use **TLS** — so this VLAN-502 mirror is readable by anything on the
switch fabric. [X]

---

## Join points

- **Radio** — CAN `0x80` (via VIP MCU) + Ethernet `.100`. VIP↔SoC HDLC IPC (`/dev/ttyS1`, 20 channels 1-20) is the
  CAN↔Android bridge; Android never sees raw CAN. In the emulator, `libipc.so` clients reach the same channels as
  Unix sockets per `/vendor/etc/ipc4.cfg` (ch3 = `vehicle_network`); VHAL write path is frame injection on
  `/dev/ipc/ipc3` (see [emulator.md](emulator.md); IPC channel detail: [vip_ipc_ghs.md](vip_ipc_ghs.md)).
- **CGM / telematics** — direct CAN access (unlike the radio) + Ethernet `.107/.112` + cellular link to GM cloud
  (`vtmpub.oboservices.mobi`). The real door to the wider bus + internet.

> **CAN gateway `0x45` = the CGM (Central Gateway Module).** The GIS763 CalDef (`InfotainmentProg_GlobalB`)
> records `GIS763_Gateway = 69 (0x45)` = "Diagnostic Address of the CGM" (see
> [ota_programming_roles.md](ota_programming_roles.md)), and the DPS scan confirms `0x45` as the diagnostic
> gateway (RspCANId `0x14DAF245`). **Open** (item 3): whether this CAN Central Gateway Module is the same physical
> unit as the Ethernet-side Connectivity Gateway / telematics (`.107/.112`, Bosch OUI) and/or the Ethernet
> inter-VLAN router (`.102`) is not settled — the CAN diagnostic address `0x45` and those Ethernet faces are not
> yet proven to be one node.

### Emulator stand-ins (cross-reference)

The emulator un-stubs the service mesh with synthetic peers: **vlan5** `.106` Visteon IPC dialing the CSM's
`9002`, `.102` telematics, `.112` CGM_OTA; **vlan4** `.107` RTOS diag bridge (`:49156` bridges
`172.16.4.100 ↔ 172.16.4.107`). FSA `9002`/`9010` LISTEN on vlan5; the client dials `9016`/`.112:9018`. Detail:
[emulator.md](emulator.md).

---

## Resolved findings

| # | Finding | Resolution |
|---|---|---|
| R1 | Identity of `:49156`; whether FSA `0x5AA5` framing is on the wire (was single-source) | **Resolved 2026-09-26:** `:49156` = root `diagnosticsd`, custom 8-byte GM header (not DoIP); FSA `0x5AA5` framing confirmed live on `9002` (in the emulator) + jadx RE. See §Service / protocol layer. |
| R2 | Full port-scan/allowlist sweep of vlan4/vlan5 from a direct physical tap | **Done 2026-11-11** (Y175_2026-11-02 Bus 2 tap): see §Reachable services. |
| R3 | IP-segment ↔ Ethernet-bus correlation (partial) | Bus 2 is a tag-multiplexed trunk (VLAN 2/5/4 + untagged); a switch in the tap path was stripping 802.1Q. §Bus 2 trunk. |
| R4 | VLAN-502 CAN mirror present on this unit? | **Not observed** on the sampled bench tap (2026-11-15); still open for the vehicle side (Open item 5). |

## Open items

1. **Per-pair capture of Ethernet buses 4/5/6/14 ↔ IP segment** — Bus 2 resolved (R3); the other pairs are
   mapped to peers from GM service data only (§Physical bus ↔ VLAN map). X11 pins 1/2 identity open.
2. CAN address→function decode for the other 22 ECUs.
3. Whether `.102` (router) and `.107/.112` (CGM/telematics) are one GM TCP/CGM function split across faces, or
   distinct modules; and whether CAN `0x45` is that same node.
4. **SecOC on this Silverado:** confirm the CMAC-AES128/27-bit scheme and the $27 key algorithm (Plane 1a) against
   a live A11 capture; identify which frame IDs carry a MAC on gminfo37.
5. **VLAN-502 CAN mirror:** bench negative recorded (R4); remaining question is a vehicle-side mirror.

---

## Open conflicts

1. **`.107` / `.112` identity (unresolved).**
   - This doc, vlan5 table: `.107` = "CGM host processor / telematics" [C] (also `networking.md:279` "CGM Host");
     `.112` = CGM_ETH/CGM_OTA, vlan4 face `172.16.4.112` = Bosch `10:66:50:0c:ed:d3`, TTL=64 (Linux).
   - Same doc, 2026-10-06 correction: vlan4 `172.16.4.107` = RTOS/GHS partition, MAC `02:05:00:00:02:00`
     (locally administered), TTL=255, "dual-homed as `192.168.1.112`" — which contradicts `.112` being the
     real-silicon Bosch CGM on vlan5, and contradicts `.107` being the CGM host on vlan5. Both cannot hold
     as written; the correction does not say whether vlan5 `.107` is a third face or the same virtual NIC.
   - `networking.md:310` (corrected 2026-11-14): `172.16.4.107` is a "historical RTOS/GHS diagnostic candidate"; no
     external T1 ARP response or completed connection in the latest bench test. (Consistent with an SoC-internal
     partition not being visible on the external tap, but not proof.) The port sweep (§Reachable services) still
     lists `.107` and `.112` as allow-listed sources for `:49156`.
   - `networking.md:339` (FSA DeviceInformation instanceId map, canonical for partition identity):
     7=CGM(`.112`), 8=LOWRADIO(`.108`), PDR=`.110`, 4=RSI1(`.104`), 5=RSI2(`.105`), 6=IPC(`.106`), 2=TCP(`.102`),
     1=CSM(`.100`); vlan5 switch table also has `.101` = ADB (`networking.md:275`), absent from this doc's table.
     `.109` appears only as an allow-listed `:9002` source (§Reachable services) and has no node label here.
2. **CAN `0x45` = CGM vs Ethernet faces.** All docs read (this one, security.md, ota_programming_roles.md:32-34)
   agree `0x45` *is* the CGM per the GIS763 CalDef; none establish it is the same physical module as `.107/.112`
   or `.102`. Not a contradiction, an unproven identity (Open item 3).
3. **`.102` role.** `TCP_ETH` telematics-comm processor (FSA notes) vs DNS/SOME-IP inter-VLAN router that shares
   its MAC with `172.16.4.1` (live scan). Kept as [?].
4. **gPTP grandmaster.** Firmware configures the radio's Intel I210 as gPTP grandmaster (`daemon_cl -GM`);
   146 gPTP frames from the radio were captured (2026-11-13), but the elected role is not decoded
   (correction 2026-11-15). Statements in the Pi-swap source (VN L435 "`-GM` grandmaster", L598-599 "I210 is gPTP
   grandmaster", L607-611 "act as gPTP grandmaster for bus 6") predate this correction and read as
   established fact; they are flagged for [pi_swap_feasibility.md](pi_swap_feasibility.md) to carry the
   "configured, not elected-verified" wording. This doc uses the corrected wording throughout.
5. **Ethernet Bus 5 = P22F rear video** (ALLDATA) vs the X11 pins 1/2 "as-wired Bus 5/14 deviation" hypothesis:
   self-consistent but unresolved (Open item 1).

## History

- 2026-11-18: reorganised from `vehicle_network.md` L1-347; Pi-swap content moved to `pi_swap_feasibility.md`;
  duplicated firewall/ADB-relocation and port-sweep text merged into §Reachable services; broken "Plane 1a above"
  reference (0x370 power-mode frame) resolved by adding the external-enum note in Plane 1a.
- 2026-11-15: gPTP role wording corrected (transmission observed, elected role not decoded); VLAN-502 bench
  negative.
- 2026-11-14: `:49156` NRC `0x10` probes found to have used an invalid tester ID (F4 + extended session now works).
- 2026-11-13: SER DATA 5 = AUTOSAR CAN 5 equivalence; second tap session; X11 pins 1/2 tap; firewall escalation.
- 2026-11-11: SecurityAccess seed/response lengths corrected (31/12); Bus 2 tap findings and port sweep folded in.
- 2026-10-06: `.107` RTOS-partition identity corrected; bench SOME/IP-SD discovery silent.
