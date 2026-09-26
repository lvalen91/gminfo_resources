# Automotive-Ethernet (AE) Research — Handoff & Premise

Continuation doc for a fresh Claude session (post context-compaction). Read this + the referenced
docs before starting. Goal: security research on the **Y181 Silverado's automotive-Ethernet /
diagnostic surface**, using the emulator as a rooted, instrumentable harness and the real-radio
diagnostic captures as ground truth.

## Access & assets
- **Emulator:** Mac Pro on the home LAN (`192.168.4.233`, reachable over the active VPN; ask the
  owner for the temp SSH password — never store it). Use SSH **ControlMaster** multiplexing (one
  persistent connection — the IPS flags repeated handshakes) and `sudo` is passwordless there.
  Work tree `~/gm_emu`; AVD `y181gm` on port **5558**; `adb -s emulator-5558`.
- **Emulator state (already built):** real GM Y181 `system`/`product` on Google android-32 goldfish;
  **GM's real vendor daemons run** (VHAL `@2.0-service-gm`, `plmanager`, `rtcd`, `gmlocation`,
  `calserviced`) via a `libipc` shim (`~/gm_emu/hy/ipc`, a Unix-socket IPCServer client); **SELinux
  enforcing**; RPO-matched to a 2024 Silverado 2500HD LTZ. Dummy **`vlan5` 192.168.1.100 / `vlan4`
  172.16.4.100 are up but have NO peers** — the FSA/OnStar/diagnosticsd clients have nothing to talk to.
- **Full build tree + screenshots + reports preserved:** `/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/`.
- **Real-radio diagnostic logs (ground truth):** `~/Desktop/New folder/` — GM J2534/D-PDU/RT API +
  `dps_readx80` DoIP sessions. **RAW: contain real VIN + `$27` seed/key + SPS creds — NEVER commit.**
  Redacted analyses: `.../emu/y181_ref/diag/{doip_uds_surface.md,real_did_values.md}` and
  `.../emu/y181_ref/unstub/network_fsa.md`.
- **Repo docs:** `platform/vehicle_network.md` (network map, 27-ECU census), `platform/emulator.md`
  (emulator fidelity + un-stub roadmap), `diagnostics/ethernet_uds_diagnosticsd.md` (the on-radio bridge).

## The radio's three wired AE links (GM service data, this 2500HD LTZ ICE build)
The CSM (A11) has **three physical 100BASE-T1 pairs actually wired** on this vehicle; Android sees one
Intel I210 NIC (gPTP master) feeding an on-board AE switch that presents **two tagged VLANs (vlan4, vlan5)**.
- **Ethernet-2 → K56 Serial Data Gateway.** Carries **both vlan5 (`192.168.1.0/24`, FSA/Info3.x) and
  vlan4 (`172.16.4.0/24`, internal diag)** as tagged VLANs over the one trunk. Radio = `192.168.1.100`
  (vlan5) / `172.16.4.100` (vlan4). **Both vlans exist (empty) in the emulator.**
- **Ethernet-4 → K73 Communication Interface Module (telematics/NAM).** FSA/SOME-IP peers `.102`
  telematics, `.112` CGM/OTA (Bosch OUI, firewalled). Partially probeable (needs synthetic peers).
- **Ethernet-6 → T3 Bose amplifier.** **AVB (802.1BA) + gPTP + IEEE-1722 AVTP audio, no IP, no VLAN.**
  Hardware-only — the emulator stubs audio (`goldfish audio@6.0`); no shim path exists.
- (Ethernet-5→rear video, Ethernet-14→HUD: connector pairs present but **not equipped** on this build.)

**NOT a radio link (corrected):** `192.168.171.0/24` / gateway `0x0C45` / native DoIP **13401**(diag)+**13400**(discovery)
is the **external J2534/MDI2 tester's view at the OBD/DLC connector** — the VCI is `.30`, the gateway `.70`
(`MaxPayload 49156`). The **radio `0x80` is reached over CAN through the gateway, not native DoIP**; the true
Ethernet-native DoIP nodes are `0x45`(gw)/`0x6B`/`0x84`/`0x96`. This subnet is **not instantiated in the emulator**
and is tester-only. (Prior docs conflated the DoIP `MaxPayload:49156` numeral with the vlan4 `diagnosticsd` port.)

## FSA protocol (Link-1 vlan5) — authoritative (jadx RE + live-validated on the emulator)
GM **FSA** = TCP, **20-byte big-endian header + protobuf(nano) payload**, **no auth of any kind** (no TLS, no
crypto, no allow-list; the only gate is equality against `serviceId`/`instanceId`, which are public constants
shipped in every FSA client APK). Header: `serviceId`[0:2] · `instanceId`[2:4] · `functionId`[4:6] · `opType`[6:8]
· `clientHandle`[8:10] · magic `0x5AA5`[10:12] (written, **never checked**) · reserved[12:16] · **payloadLength
int32**[16:20] · payload. **opTypes:** GET 421, SET 422, REQUEST 641, REQUESTRESPONSE 674, EVENT 1032 (accepted
inbound); STATUS 343 / RESPONSE 595 / PROCESSING 836 (outbound only). serviceId 9002=**1007** (`0x03EF`),
9010=**1001**; instanceId=1. CSM FSA ports: 9002 RemoteModuleHMI, 9005 OnStar, 9010 DeviceInformation, 9011
ProgrammingMaster, 9012/9018 RemoteReflash(UI), 9016 NAM, 9020 DisplaysCoordination.
- **PROVEN unauthenticated:** an anonymous vlan5 TCP peer subscribed to StateOfHealth and streamed live
  HEARTBEAT data, and GET-read a live property value. Tools: `~/gm_emu/ae/{fsaprobe,fsalisten4}` (raw-syscall
  connect/accept4 to bypass the netd fwmark handshake — mandatory in this no-default-NIC emulator).
- **Cluster-injection surface:** EVENT (1032) for fktId ≥700 dispatches straight into `ClusterViewManager` —
  712 CLIENTFOCUS (moves cluster focus), 700/714 asset state, 707/708/710/711/713/715 widget data, 720/721
  activity indicator. Any anonymous peer can drive the instrument cluster (pending each method's protobuf
  field validation, not yet examined).
- **Two parser bugs (shared FSA code, both services):** (1) `payloadLength` (signed int32) checked only `≥0` →
  unbounded `new byte[20+len]` up to ~2 GiB (caught by `catch(OutOfMemoryError)`, but repeatable → RAM DoS);
  (2) on serviceId/instanceId rejection the payload bytes are **not drained** → next 20 bytes misread as a
  header → permanent TCP framing desync. Decompiled sources: `~/gm_emu/ae/re/`.

## Link-2 (vlan4 `172.16.4.x`) diagnostic surface — from the real-radio logs (redacted)
- `diagnosticsd` (root) `0.0.0.0:49156` TCP → RTOS peer `172.16.4.107`, **custom 8-byte GM header**
  (SRC/TGT addr + PAYLOAD_LEN; ECU `0x0084`, tester `0x0FA0`) — **not DoIP**. Unauthenticated `$27/$10/$22`
  from the shell side all return NRC `0x10` generalReject.
- **`$27` SecurityAccess (via the tester/CAN path):** valid SPS session = 8-byte seed / 6-byte key, **granted**
  on `0x80`/`0x81`/`0xBE` (`67 02`); a failed-SPS read returned an **all-`0xFF` seed** — this specific read is
  the **SPS-credential-absent path**, not necessarily a hardware SBI flip (see `vehicle_network.md`). `F1A0=0xFF`
  (secure mode) live-confirmed on the radio.
- **[S] RESOLVED (2026-09) — SBI/`$27` fail-open is real, off-SoC, VIP-side.** The Ethernet `diagnosticsd`
  (`:49156`) `$27` path for the `VIP` tier is *forwarded*, not locally checked: `ProxyOfExtComp::
  handleUDSRequest` relays `MESSAGE_SECURITY_ACCESS_VIP` via a `SockAdaptor` TCP socket to the external VIP
  MCU, where the real seed/key compare and the SBI EEPROM read happen. No SoC binary reads the SBI EEPROM
  directly; the SoC only relays the SBI/MEC-derived byte via `$22 F1A0`
  (`IDiagnosticsObd::getManufacturingEnableCounter()`, returned verbatim, unchecked). SBI EEPROM byte `0xFF` =
  "Bypass Active" relaxes the **VIP's own** key-compare (same SBI flag as the ProtoKey/ADB bypass in
  `platform/security.md`, different enforcement point). Under normal (SBI-inactive) posture, an untrusted
  Ethernet peer's `$27` requestSeed still fails closed (`7F 27 10`) before any seed is issued. VIP MCU
  firmware is not in the artifact set, so the VIP-side compare can't be re-derived statically. **This
  supersedes the "possible fail-open" hedge above and in earlier revisions of this doc.** Not reproducible on
  the hybrid emulator (`IDiagnosticsObd` unregistered, `diagnosticsd` absent, Secure-ADB replaced by stock
  `adbd`) — would need a modeled synthetic VIP/`$27` endpoint, a substantial un-stub. Full detail:
  [`../platform/security.md`](../platform/security.md#ethernet-uds-27-securityaccess--vip-side-forwarding-off-soc-2026-09)
  and [`../diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md).

## Update / rollback / influence verdicts (network peer over Ethernet, resolved 2026-09)

- **Unsigned update push: GATED.** `gm_update_engine` verifies an RSA-2048 whole-manifest signature (GM GPD
  Production CA) covering the per-module SHA-256 hash table even for `Sign Type: NONE` modules; fails closed
  because the dev CA file is absent on production. Independent GHS VMM1 AVB/vbmeta re-verify at boot + runtime
  dm-verity. UDS `$34`/`$36`/`$37` on `:49156` are gated behind `$27`.
- **Rollback: HARDWARE-ENFORCED, not network-influenceable.** GHS keeps its own rollback counter in the misc
  partition, independent of AVB's index; empirically a Y181→Y177 downgrade writes the slots but GHS rejects at
  boot and A/B falls back. A manifest's "version check disabled" flag only affects the write phase, not GHS's
  boot check.
- **System apps/services:** unauthenticated FSA influence of HMI/cluster display+consent state is **proven
  live** (see FSA protocol section above); binary replacement stays gated by the signature chain.
  `DisplaysCoordination` persistent-write methods (`resetOilLife`/`setIPCLayout`/`postTPMS_Relearn`/…) are
  documented-but-**not**-live-fired — hosted on Visteon IPC `.106`, unreachable off-vehicle on this bench.
- **Params/calibrations:** UDS `$2E` is behind `$10`/`$27` — an unauthenticated Ethernet peer can't reach it;
  EEPROM cal bytes are ungated but only reachable over local I2C (physically-adjacent, not network).
- **No network→install path.** `UpdateServiceImplGB.install()` (`DelayedWKSApp`) has no permission check but is
  only reachable via local Binder — not network. The `RemoteReflash` FSA `9012` path has Android as a
  **client** to `.102`; inbound events dispatch to `IRemoteReflashServiceEvents`, which is
  **unsubscribed system-wide** — verified across 6 apps including `CriticalWKSApp`/`GMTCPS`. `.102` is
  IP-pinned by static config with no TLS pinning; whether a rogue vlan5 node can spoof `.102` at L2/L3 is a
  bench open item.

**Conclusions:** (1) no network→install path exists on this build — the reachable FSA/RemoteReflash surface
either has no live subscriber or is local-Binder-only; (2) the SBI/`$27` fail-open is real but is **not**
reproducible on the emulator, since the compare lives off-SoC on the VIP MCU.

## Premise to build for AE research (per link)
**Link-1 (vlan5 FSA) — READY, protocol solved.** Next: synthetic peers so the CSM's own FSA clients init and
can be driven both ways:
- `.106` Visteon IPC — an FSA **client** dialing the CSM's `9002` (highest value; drives RemoteModuleHMI).
- `.102` telematics FSA server (OnStar/TurnByTurn/RemoteReflash), `.112` CGM/OTA stub.
Targets: **cluster-injection** via EVENT 1032 fktId ≥700 (712 CLIENTFOCUS etc.) — craft the protobuf-nano
payload each `ClusterViewManager` method expects, then examine that method's field validation; the **int32
payloadLength RAM-DoS** and the **framing-desync** parser bugs; FSA wire-format fuzz; SOME/IP-SD (UDP 30490) fuzz.

**Link-2 (vlan4 diagnosticsd) — needs setup.** Confirm `diagnosticsd` actually runs in the hybrid image (it is a
`/vendor/bin` daemon tied to the real vendor firmware; may be absent), then stand up a `.107` RTOS stub that
answers the **8-byte GM-header** UDS frames. Top payoff: the documented worker-starvation **DoS** on `:49156`;
`IDiagnosticsInternalService` **vndbinder-bypass** (biggest open gap in `ethernet_uds_diagnosticsd.md`). The
SBI/`$27` fail-open itself is **resolved** (see [S] above) but not modelable on this emulator without a
synthetic VIP endpoint (compare lives off-SoC). NAM EAP-AKA (Link-4/telematics).

**Link-3 (AVB audio) — hardware-only**, out of scope for the emulator (no PHY/switch/amp, audio stubbed).

**Method:** replay/fuzz against the emulator's **real** FSA / `diagnosticsd` binaries (findings transfer at the
GM-software layer — same binaries as the radio). Instrument with root adb + logcat under the enforcing policy.
**Fabric caveats needing the bench:** the physical vlan↔pair correlation, whether the OBD/DLC DoIP presence is
a separate physical port on K56 or the same uplink NAT/firewalled — both need a simultaneous per-pair scope/pcap.

## Fidelity caveats
The emulator is real GM software on substituted hardware with **no real bus and no real peers** (until you
add synthetic ones). **AE-facing software** findings (parser bugs, unauth handlers, DoS, logic) transfer to
the radio. The **fabric** (switch/VLAN segmentation, other ECUs, gPTP, the documented no-MACsec/L2-L3-auth),
**crypto/TEE**, and **boot-chain** must be validated on the real bench. Permissive-vs-enforcing and
goldfish-vendor differences can alter some paths — confirm promising hits on hardware.

## Redaction (hard rule)
Never commit the raw `Desktop/New folder` logs or any real VIN / `$27` seed-key / MAC / SPS credential.
Internal vehicle-network addresses (`192.168.1.x`, `172.16.4.x`, `192.168.171.70`, `0x0C45`) are fine.
