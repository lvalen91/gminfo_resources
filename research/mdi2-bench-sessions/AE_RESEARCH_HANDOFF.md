# Automotive-Ethernet Research Tracker

Scope: this doc is the **open-items/status tracker** for automotive-Ethernet / diagnostic-surface
research on the Y181 Silverado radio (emulator-as-harness + real-radio diag captures as ground
truth). It owns three things no other doc owns: (1) the forward work-plan-per-link, (2) the
redaction hard rule, (3) session/bench state (access, log locations, fidelity status) as of the
dates below. It does **not** own emulator internals, FSA wire format, UDS/diagnosticsd detail, or
OTA/rollback verdicts — those are restated here only as far as needed to keep the work plan
readable; follow the pointers for the facts themselves.

**Related:** [`../platform/emulator.md`](../platform/emulator.md) ·
[`../platform/fsa_protocol.md`](../platform/fsa_protocol.md) ·
[`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md) ·
[`../platform/ota_update_stack.md`](../platform/ota_update_stack.md) ·
[`../platform/ethernet_networking.md`](../platform/ethernet_networking.md) ·
[`../platform/vehicle_network.md`](../platform/vehicle_network.md) ·
[`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) (GSK) ·
[`GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](GM_INFO37_BOOT_CHAIN_ANALYSIS.md) (GIB)

## Access & assets (session state)

- **Emulator:** Mac Pro on the home LAN, reachable over the active VPN (ask the owner for the
  temp SSH password — never store it); `sudo` is passwordless there. SSH **ControlMaster**
  multiplexing required (the IPS flags repeated handshakes). Work tree `~/gm_emu`; AVD `y181gm` on
  port **5558**; `adb -s emulator-5558`. Full build/fidelity detail:
  [`../platform/emulator.md`](../platform/emulator.md) — do not restate here.
- **Real-radio diagnostic logs (ground truth):** `~/Desktop/New folder/` — GM J2534/D-PDU/RT API +
  `dps_readx80` DoIP sessions. **RAW: contain real VIN + `$27` seed/key + SPS creds — NEVER commit**
  (see Redaction below). Redacted analyses: `.../emu/y181_ref/diag/{doip_uds_surface.md,
  real_did_values.md}` and `.../emu/y181_ref/unstub/network_fsa.md`.
- Full build tree + screenshots + reports preserved at
  `/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/`.

## Where the facts live now (pointers only)

- **Emulator build/fidelity state** (VHAL frame-injection write path, navsens HIDL stub, DR-fusion
  gate, audio/TCC blocker, real-kernel boot status) → [`../platform/emulator.md`](../platform/emulator.md)
  and, for the full real-kernel boot-chain walkthrough, [GIB](GM_INFO37_BOOT_CHAIN_ANALYSIS.md).
- **Physical AE link map** (Ethernet-2/4/6 → K56/K73/T3, vlan4/vlan5 CIDRs, the AVB link, the
  `192.168.171.0/24` tester-subnet-vs-radio-link correction) →
  [`../platform/ethernet_networking.md`](../platform/ethernet_networking.md) (IPs/VLANs/ports) and
  [`../platform/vehicle_network.md`](../platform/vehicle_network.md) (ECU/gateway census).
- **FSA protocol** (20-byte header + protobuf(nano), opType/service/instance tables, port map, the
  two parser bugs, the UDP/multicast AIOOBE + connectionless-injection findings) →
  [`../platform/fsa_protocol.md`](../platform/fsa_protocol.md).
- **Link-2 diagnostic surface / UDS** (8-byte GM UDS header vs DoIP, NRC 0x10, vndbinder-bypass gap) →
  [`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md); seed/key
  byte-length and signature detail → [GSK](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- **Update/rollback/influence verdicts** (manifest signing gate, GHS hardware-enforced rollback,
  no-network-install conclusion) → [`../platform/ota_update_stack.md`](../platform/ota_update_stack.md)
  and [`../platform/ota_programming_roles.md`](../platform/ota_programming_roles.md).

Two corrections below are reproduced in full rather than pointered, because at the time of this
pass neither correction was confirmed to have landed in the owner doc it summarizes (see ledger —
flagged for the planner to verify against `fsa_protocol.md` and `ethernet_uds_diagnosticsd.md`).

### Correction: cluster-injection routing is REQUEST/REQUESTRESPONSE, not EVENT

**History (corrected 2026-09):** prior revisions of this doc misattributed the FSA
cluster-injection surface to `EVENT` (opType 1032). Deobfuscated FSA service-lib RE
(`com/gm/fsa/service/`, cross-checked against `ClusterService`'s router `f/d.java`/`f/h.java`/
`h/b.java`) shows opType 1032 (Event) in the router only ever drives OfferService/discovery
multicast, never `ClusterViewManager`. The correct routing: REQUEST/REQUESTRESPONSE (opType
641/674) via the method handler for fktId ≥700 dispatches straight into `ClusterViewManager` —
712 CLIENTFOCUS (moves cluster focus), 700/714 asset state, 707/708/710/711/713/715 widget data,
720/721 activity indicator. Any anonymous vlan5 peer can drive the instrument cluster (pending
each method's protobuf field validation, not yet examined). Full FSA wire format and the two
parser bugs: [`fsa_protocol.md`](../platform/fsa_protocol.md).

### Correction: `ProxyOfExtComp` attribution withdrawn (Link-2)

**History (corrected 2026-11-11):** `diagnosticsd` uses the custom 8-byte GM UDS header, not ISO
DoIP. Target shell and Bus-2 probes receive NRC `0x10` before a seed is issued; socket
reachability does not establish programming authority. The former `ProxyOfExtComp` symbol
attribution and asserted external forwarding topology were **withdrawn** by the diagnostic-source
correction — that external-forwarding route remains unproven. On the authorized target CAN path,
fresh radio `0x80` reconstruction shows 31-byte normal seeds (16-byte fixed ID + 15-byte varying
suffix), 12-byte responses, and `67 02`. `DPS+SPS.pcapng` programs amplifier `0x81`, not the
radio; its radio observations are DID reads and seed-only probes. An SPS host error banner does
not establish why the ECU returned an all-FF seed. Full detail and the SBI/ADB-cert distinctions:
[`ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md) and
[GSK](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

*(Note: the 31-byte seed figure above is cited elsewhere as disputed against an earlier 32-byte
claim — see GSK's Open Conflicts; this doc states the 31-byte figure as the correction-chain
result and does not re-litigate it.)*

## Premise to build for AE research (per link) — forward work plan

**Link-1 (vlan5 FSA) — READY, protocol solved.** Next: synthetic peers so the CSM's own FSA
clients init and can be driven both ways:
- `.106` Visteon IPC — an FSA **client** dialing the CSM's `9002` (highest value; drives
  RemoteModuleHMI).
- `.102` telematics FSA server (OnStar/TurnByTurn/RemoteReflash), `.112` CGM/OTA stub.

Targets: **cluster-injection** via REQUEST/REQUESTRESPONSE opType 641/674 fktId ≥700 (712
CLIENTFOCUS etc., not EVENT 1032 — see correction above) — craft the protobuf-nano payload each
`ClusterViewManager` method expects, then examine that method's field validation; the **int32
payloadLength RAM-DoS** and the **framing-desync** parser bugs; the new **UDP/multicast AIOOBE
crash** and **connectionless injection** findings (build a UDP sender — the existing tools
`fsaprobe`/`fsalisten4` are TCP-only); FSA wire-format fuzz; SOME/IP-SD (UDP 30490) fuzz.

**Link-2 (vlan4 diagnosticsd) — needs setup.** Confirm `diagnosticsd` actually runs in the hybrid
image (it is a `/vendor/bin` daemon tied to the real vendor firmware; may be absent), then stand
up a `.107` RTOS stub that answers the 8-byte GM-header UDS frames. Top payoff: the documented
worker-starvation DoS on `:49156`; `IDiagnosticsInternalService` vndbinder-bypass (biggest open
gap in `ethernet_uds_diagnosticsd.md`). The SBI/`$27` fail-open itself is resolved (see the
correction above) but not modelable on this emulator without a synthetic VIP endpoint (the
compare lives off-SoC). NAM EAP-AKA (Link-4/telematics).

**Link-3 (AVB audio) — hardware-only**, out of scope for the emulator (no PHY/switch/amp, audio
stubbed).

**Method:** replay/fuzz against the emulator's real FSA / `diagnosticsd` binaries (findings
transfer at the GM-software layer — same binaries as the radio). Instrument with root adb +
logcat under the enforcing policy.

**Fabric caveats needing the bench:** the physical vlan↔pair correlation, and whether the
OBD/DLC DoIP presence is a separate physical port on K56 or the same uplink NAT/firewalled — both
need a simultaneous per-pair scope/pcap.

## Fidelity caveats (current status)

The emulator is real GM software on substituted hardware with no real bus and no real peers
(until synthetic ones are added). AE-facing **software** findings (parser bugs, unauth handlers,
DoS, logic) transfer to the radio. The **fabric** (switch/VLAN segmentation, other ECUs, gPTP,
the documented no-MACsec/L2-L3-auth) and **crypto/TEE** still need real-bench validation
regardless of which kernel the emulator runs — both are hardware-bound (full hard-blocker list:
[`emulator.md`](../platform/emulator.md)). The real-kernel boot (see `emulator.md`/GIB) now
partially answers the boot-chain question — treat as still-open only the pieces that boot doesn't
cover (AVB/GHS trust anchors, the VIP MCU itself). Permissive-vs-enforcing and goldfish-vendor
differences can alter some paths — confirm promising hits on hardware.

## Redaction (hard rule)

Never commit the raw `Desktop/New folder` logs, or any real VIN / `$27` seed-key / MAC / SPS
credential, to this repo. Internal vehicle-network addresses (e.g. `192.168.1.x`, `172.16.4.x`,
`192.168.171.70`, `0x0C45`) are fine to cite.

## Open conflicts

None local to this doc. One cross-reference worth flagging: the 31-byte seed figure restated in
this doc's Link-2 correction (above) is the same figure [GSK](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
carries as disputed against a 32-byte claim traced to a retired doc — see GSK's own Open
Conflicts section; this doc does not attempt to settle it.

## Open items for the planner

- The two corrections reproduced in full above (cluster-injection opType fix; `ProxyOfExtComp`
  withdrawal) were folded inline in the *source* `AE_RESEARCH_HANDOFF.md` at the time of this
  pass. This tracker doc may currently be **the only place both corrections are recorded** —
  neither was confirmed, during this writing pass, to have also landed in
  `platform/fsa_protocol.md` (cluster-injection) or `../diagnostics/ethernet_uds_diagnosticsd.md`
  (`ProxyOfExtComp`), both of which this doc names as the authoritative owners of that content.
  Planner: verify both owner docs carry the corrected claim, not the pre-correction one, before
  treating this doc's copies as merely redundant.
- The `192.168.171.0/24` DoIP-tester-subnet-vs-radio-link correction (source doc's "NOT a radio
  link" note) should also be checked against `platform/ethernet_networking.md` for the same
  reason; not reproduced here in full since it is pure network-topology fact with no tracker role
  of its own, but flagged in case it too hasn't propagated.
