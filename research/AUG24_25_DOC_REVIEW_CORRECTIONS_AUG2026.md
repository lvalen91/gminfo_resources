# Cross-tree documentation review (2026-08-25) — corrections, new findings, SBI lead

Full read-through of every doc created 2026-08-24/25 across `gminfo_resources` and
`/Volumes/stuff/misc/research/GM_research` (six parallel agents, ~100 files). This doc records
what needs correcting, what's genuinely new, and consolidates the SBI-reset investigation status.

## Corrections to propagate

1. **`gm_dps/docs/DPS_MASTER_REFERENCE.md` §6.2/§7.4/§12.2 are stale and wrong.** They claim
   calibration file `85783460` contains an "Encrypted EEPROM Payload (0x050-0x367)" targeting
   `0x0440/0x0A80/0x0B40 → Reset to LOCKED". This is refuted byte-for-byte by
   `A11_CALIBRATION_FILES_COMPLETE_ANALYSIS_AUG2026.md` (same directory): the quoted bytes are
   inside the gzip-compressed CalOvride XML stream, not an EEPROM address:value table; all 14
   decompressed CSM cal files have zero hits for "0440/0a80/0b40/eeprom/security/SBI/bypass".
   `DPS_MASTER_REFERENCE.md` was never updated after this correction landed — treat §6.2/7.4/12.2
   as superseded, not authoritative.
2. **The `0x0A80`/`0x0A81` "backup SBI, both must match" claim is likely wrong.**
   `eeprom/CORRECTIONS_AUG2026.md` found zero code references to this dual-SBI mechanism in the
   VIP binaries via the confirmed accessor path. The empirical EEPROM-bypass behavior itself
   isn't disputed — only the claimed second-address mechanism. Real, confirmed SBI storage:
   **CalGroup `0x3b`, EEPROM cells `0x43a-0x447` (14 bytes), real bytes at `0x440`/`0x441`**,
   handled by a pure pack/unpack accessor (`FUN_ram_00091938`) that does not itself branch on
   the value.
3. **`eeprom/CORRECTIONS_AUG2026.md` also retracts**: RAM `0x3e06` (was claimed "processed
   EEPROM SBI value at boot" — actually a generic "security module initialized" readiness flag,
   unrelated to the SBI's actual value); `0xecd84` (was framed as head of a "VIP validation
   chain" — actually a generic RTOS mutex primitive, 285 call sites); `0x04A0`/`0x0A40`/`0x0BE0`
   (closed, zero real references — prior "N refs" counts were string-proximity artifacts, not
   functional analysis). `0x04C0` was upgraded to confirmed-real (CalGroup `0x44`, structurally
   parallel to SBI, purpose unknown).
4. **ECU `0x45` is the Central Gateway Module (CGM), not the radio.** The radio/head-unit (CSM)
   is **ECU `0x80`**, ECUID `004B41DC...0114AC` — this ECUID's 16-byte prefix is exactly what's
   already documented as the "static ECU identity constant" in the two captured SecurityAccess
   seed pairs (`AUG24_SESSION_FULL_PCAP_TIMELINE.md` §4). No correction needed there, just
   confirms the addressing.

## New findings worth keeping

- **Loopback ident-service ports are computed, not fixed**: `port = 8097 + ProductGroupId`,
  where `ProductGroupId` comes from `HKLM\SOFTWARE\WOW6432Node\BOSCH\VTX-VCI\GM\ProductGroupId`
  (confirmed live value `0x1c`=28 → `8097+28=8125`, exact match). Source:
  `gm_dps/docs/BVTX_VCI_PROTOCOL_DETAIL_ports_and_config.txt` /
  `CONFIG_ARCHAEOLOGY_AUG2026.md`. Resolves the "OPEN QUESTION — Port='8080'" item in
  `MDI2_DPDU_API_PROTOCOL_AUG2026.md` §10.8 (same runtime-supplied-port pattern, different
  registry key).
- **The actual ident-service TCP client living in `dps.exe`'s process is `BVTX-VCI-RT.dll`**
  (loaded into dps.exe), not dps.exe/dpsvcs.dll/tisvcsv4.dll/vcs_dps.dll themselves (all
  Winsock-free, confirmed by import-table check). Opens two loopback sockets ("upstream"
  req/resp, "downstream" subscriber/event), both encrypted at this layer separately from the
  network-side "encrypted" 9052-family channel.
- **A "Type4" DPS/SPS plugin mechanism exists**: a native PE32 DLL + `.cfx` XML, exporting
  `Launch`/`GetResult`/`SetInternal`/`CMessage`, importing `tisvcsv4.dll`'s
  `CBuildService::BuildRequestedService(eProtocol, uint16_t serviceID, long*)` — accepts an
  **arbitrary 16-bit UDS service ID**, confirmed from a real example (`GbPowerModeList.dll`).
  This means a custom Type4 DLL loaded by DPS could inject arbitrary diagnostic commands
  (including `$27 02` SendKey) through DPS's own already-authenticated session and local
  `tisvcsv4.dll` builder. Doesn't hand us a missing key, but is a real capability for future
  custom tooling. Source: `gm_dps/docs/TYPE4_CUSTOM_COMMAND_INTERFACE_AUG2026.md`.
- **`J2534Wrapper.dll` is not a thin pass-through** — independent DoIP discovery
  (`DoIPSendDiscoveryRequest[Ex]`, a `CDHCPListener` class that listens for DHCP offers to learn
  the MDI2's IP), device enumeration, and manages `GM_MDI_Ident.exe` as a Windows service
  (`OpenSCManager`/`StartService`). Shares source path
  `j2534-wrapper\win32\solutions\doip-stack\channel.cpp` with `GM_DOIP_32.dll` — same authored
  codebase. **Confirmed: actual UDS diagnostics never flow through the J2534 PassThru
  read/write API at all** (`j2534_api_log.txt` — only 6 distinct call types across the whole
  file: Open/ReadVersion/Connect/Ioctl/Disconnect/Close, no ReadMsgs/WriteMsgs/StartMsgFilter
  ever) — real UDS traffic goes over MDI2's proprietary port-10123 channel exclusively.
- **A third local SecurityAccess candidate exists and is ruled out for the radio ECU**:
  `tisvcsv4.dll FUN_10002c50` (hand-rolled 16-bit algorithm bank, ~15 bespoke transforms,
  selector `0x201-0x20b`/`0x301-0x305`) — same dimensional mismatch as `dllsecurity.dll`'s
  already-ruled-out `FUN_10001000` (16-bit seed/key, not 31-byte/12-byte). **No binary anywhere
  in the current 32-binary disassembly computes a 31-byte→12-byte transform locally** — S84.dll's
  server-provisioned AES-CMAC (`MDI2_DPDU_API_PROTOCOL...` — see prior session findings) remains
  the only dimensionally-matching, and only real, mechanism for this ECU.
- **Full 27-ECU SecurityAccess sweep exists**: only **ECU `0x80` (Radio/CSM)** returns the
  degenerate all-`0xFF` seed; all 26 others return varied real seeds. Confirms the defect is
  isolated to this one ECU's own `$27` implementation, not systemic. Source:
  `DPS_MASTER_REFERENCE.md` §15.8.
- **Candidate SBI-carrying DIDs identified** (all four fail with NRCs in read-only GCI sessions —
  `7F 22 22` conditionsNotCorrect on `F0F4`, `7F 22 31` requestOutOfRange on `F0F8`/`E0B2`/`E0B5`
  — meaning they need a higher session/security context than a plain GCI read provides):
  **`F0F4`, `F0F8`, `E0B2`, `E0B5`**. Source: `radio_possibly_seed_reset.Txt` /
  `ecu80_READ.Txt` cross-read.
- **Unrelated-but-adjacent security finding** (different research thread, AAOS head-unit side,
  not MDI2/DPS): a disclosure-ready DoS in `/vendor/bin/diagnosticsd` (root, TCP 49156, GM
  Ethernet UDS/ISO-14229 bridge) — 3 concurrent connections sending only an 8-byte header with no
  payload stall the daemon for all clients including the legitimate RTOS bridge, pre-parse, no
  auth required. Same UDS-over-TCP 8-byte-header wire format as the MDI2/DPS transport work, so
  worth keeping in view even though it targets a different component.
  `research/security/DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026.md`.
- **`ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md` is unrelated to the radio SecurityAccess question**
  (checked directly, per the user's implicit interest in any local-key-derivation lead): it
  traces a completely different mechanism — a 1-byte-request/17-byte-response (1 status +
  16-byte key) VIP→Android internal IPC handoff for data-encryption unlock, not the UDS `$27`
  CAN/DoIP exchange. Different transport, different byte lengths, different purpose. Notable
  independently: zero cryptographic validation of the 16-byte key on the Android side (any value
  accepted if VIP reports status=1) — a real finding, just not relevant to the seed/key question.

## SBI-reset investigation: consolidated status (still open)

**What's confirmed:**
- SBI EEPROM storage: CalGroup `0x3b`, cells `0x43a-0x447`, bytes `0x440`/`0x441` (per §1-2 above).
- Affected ECU: `0x80` (Radio/CSM) only, confirmed via full 27-ECU sweep.
- Two real seed/key pairs already captured for this ECU (documented in
  `AUG24_SESSION_FULL_PCAP_TIMELINE.md` §4) — key is server-computed (GM TLC backend), not
  locally derivable, confirmed independently by both a live algorithm test (`dllsecurity.dll`
  ruled out) and static analysis (`S84.dll`/`IECS.dll` fetch flow, no embedded key anywhere in
  32 binaries).
- The radio's seed was observed **locked** (real seed) at one read (01:00, session captured in
  `radio_possibly_seed_reset.Txt`) and **already unlocked** (all-`0xFF` seed convention, MEC=182)
  16 minutes later (`ecu80_READ.Txt`, 01:16) — confirms a state transition happened in that
  window, but both reads show `SBI $0000` (already secured) and the actual SBI-carrying DIDs
  (F0F4/F0F8/E0B2/E0B5) fail to read in both — so DPS's displayed "SBI $0000" may be a
  cached/default UI value, not a live byte-level read, in these particular captures.

**What's still missing:** no file read in this pass — GCI logs, evidence docs, or annotations —
contains an actual `$27 02` SendKey + `$2E`/`$31` write to ECU `0x80` touching one of the four
candidate SBI DIDs. These GCI sessions are all read-only by construction. **Next concrete step**
(not yet done): grep the three large SPS pcaps already on disk (`DPS+SPS.pcapng`,
`SPS_radioCal_and_OS_UpdateCHeck.pcapng`, `postOS_download_SPS.pcapng`) for UDS traffic touching
`F0F4`/`F0F8`/`E0B2`/`E0B5` on ECU `0x80`, specifically around the two already-located
SecurityAccess unlocks in `SPS_radioCal_and_OS_UpdateCHeck.pcapng` (frames ~25884-25952 and
~29386-29443, t≈174-194s) — and separately, decode the async D-PDU event channel (msg-id `0x863`)
that `SPS_RECAL_UDS_SEQUENCE_AUG2026.md` flags as unreverse-engineered, since that's the channel
most likely to carry an unsolicited/asynchronous SBI-state notification if one exists.
