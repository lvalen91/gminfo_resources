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

## Known real AE / diagnostic surface (from the logs — redacted)
- **Transport:** two capture generations — native GM **DoIP proto 13401** straight to gateway `0x0C45`
  (IP `192.168.171.70`, MaxPayload → the `:49156` diagnosticsd port); newer **DoIP-UDP discovery 13400**
  then **CAN fallback (ISO15765)** for actual UDS. Radio `0x80` is CAN-via-gateway; the true
  Ethernet/DoIP nodes are `0x45`/`0x6B`/`0x84`/`0x96`.
- **FSA service mesh (ports on the CSM):** `9002` RemoteModuleHMI, `9005` OnStarFunctions, `9010`
  DeviceInformation, `9011` ProgrammingMaster, `9012` RemoteReflash, `9016` NAM, `9018` RemoteReflashUI,
  `9020` DisplaysCoordination. `diagnosticsd` `:49156` UDS-over-TCP bridges to RTOS peer `172.16.4.107`.
- **`$27` SecurityAccess:** valid SPS session = 8-byte seed / 6-byte key, **granted** on `0x80`/`0x81`/`0xBE`
  (`67 02`); a failed-SPS read returned an **all-`0xFF` seed** (a possible **fail-open** worth investigating —
  distinct from a hardware SBI flip). `F1A0=0xFF` (secure mode) live-confirmed on the radio.

## Premise to build for AE research
1. **Synthetic `vlan5` peers** at the real addresses so the CSM's AE stack initializes and can be driven:
   - `.106` Visteon IPC (an FSA **client** dialing the CSM's `9002`) — drives the cluster-HMI bridge.
   - `.107` RTOS diagnostic-bridge peer for `:49156`.
   - `.102` telematics (TCP), `.112` CGM_OTA.
   Sequence IPC-client-first, then the diagnostic stub, then telematics/OTA.
2. **Ranked targets:** FSA wire-format fuzz (`0x5AA5` protobuf framing, **no auth**); `:49156` UDS-bridge
   DoS/fuzz (reproduce the documented worker-starvation DoS in a sandbox); RemoteModuleHMI cluster-injection;
   NAM EAP-AKA state machine; SOME/IP-SD discovery fuzz; `IDiagnosticsInternalService` **vndbinder-bypass**
   (biggest open gap in `ethernet_uds_diagnosticsd.md`); DoIP-discovery→CAN-fallback replay; `$27`
   state-machine + the SPS **fail-open** follow-up.
3. **Method:** replay/fuzz against the emulator's **real** `diagnosticsd`/FSA binaries (findings transfer at
   the GM-software layer — same binaries as the radio). Instrument with root adb + logcat + the enforcing
   policy in place. Cross-check which handlers fire against the redacted log analyses.

## Fidelity caveats
The emulator is real GM software on substituted hardware with **no real bus and no real peers** (until you
add synthetic ones). **AE-facing software** findings (parser bugs, unauth handlers, DoS, logic) transfer to
the radio. The **fabric** (switch/VLAN segmentation, other ECUs, gPTP, the documented no-MACsec/L2-L3-auth),
**crypto/TEE**, and **boot-chain** must be validated on the real bench. Permissive-vs-enforcing and
goldfish-vendor differences can alter some paths — confirm promising hits on hardware.

## Redaction (hard rule)
Never commit the raw `Desktop/New folder` logs or any real VIN / `$27` seed-key / MAC / SPS credential.
Internal vehicle-network addresses (`192.168.1.x`, `172.16.4.x`, `192.168.171.70`, `0x0C45`) are fine.
