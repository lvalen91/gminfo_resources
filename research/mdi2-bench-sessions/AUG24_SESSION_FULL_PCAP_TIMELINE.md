# Aug 24 Pcap Timeline

**Scope:** provenance/timeline record for the 6 pcap captures taken `gm_dps/misc/Aug24_session/`
on 2026-08-24 while GM DPS/SPS and the MDI2 Manager were used against a real MDI2 (Bosch VCI) and
a 2024/2025 Chevrolet Silverado. Covers only non-WiFi/internet traffic on the captured session
(device subnet, loopback IPC, USB, multicast beacon; GM backend TLS noted where it participates;
generic internet/telemetry excluded).

**Not here:** the MDI2 D-PDU wire-protocol mechanics (framing, mid-opcode table, bring-up
sequences, loopback-ident resolution) — owned by [MDI2_DPDU_API_PROTOCOL_AUG2026.md](MDI2_DPDU_API_PROTOCOL_AUG2026.md)
(§10-11), this doc only cites findings against it. The MDI2 *Manager* 900x/9052 log-pull
protocol (port bank, Blowfish-ECB, JSON session layer, Get-Log-Files container) — owned by
[MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md](MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md). The captured
seed/key material's cryptographic meaning (CMAC algorithm, gate-independence table, signature
verifier) — owned by [GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
This doc states only what each of the 6 captures independently shows and feeds those facts to the
three owners above by pointer, not by copy.

**Provenance:** six agents (3 Sonnet on the small connection-attempt files, 3 Opus on the large
SPS/DPS files) independently extracted each capture via tshark; this doc merges their findings.

## Capture inventory (chronological by mtime)

| Time | File | Size | Characterization |
|---|---|---|---|
| 12:07 | `capture_attempt1.pcapng` | 506 KB | Repeated-attempt session: 7 dance cycles in ~222s, DoIP UDS work against `<DOIP_RESPONDER_IP>` with SecurityAccess seed requested 3x but never keyed, ends with an unexplained 221 KB pull over port 9052 (see Finding 7) |
| 12:09 | `capture_attempt2.pcapng` | 75 KB | First clean success: dance → 10123 opens in ~2s → DoIP session to `<DOIP_RESPONDER_IP>` → VIN read, 26-ECU scan, clean teardown |
| 12:17 | `multiple_intefaces_attempt1.pcapng` | 2.3 MB | Another full success, 3x 10123 opens, DoIP session to `<DOIP_RESPONDER_IP>` with VIN `<VIN_REDACTED>`; confirms `<MANAGER_REPORTED_IP>` is a dormant/unused entry in the Manager's own IPC response, never seen live on the wire |
| 12:34 | `DPS+SPS.pcapng` | 80 MB | Main working session — 18 full dance+10123 cycles over ~740s; bulk calibration writes (~60-63KB) and reads (~41-50KB) over D-PDU/10123; loopback 8125 IPC re-invoked at every cycle with a ~16.7KB blob each time; DoIP/13400 only 2 tiny probes near the end to `<DOIP_RESPONDER_IP>` |
| 12:45 | `SPS_radioCal_and_OS_UpdateCHeck.pcapng` | 87 MB | The actual radio SecurityAccess + flash session — two full seed/key/grant $27 unlocks (real bytes captured, Finding 4), 14-segment RequestDownload/TransferData/RequestTransferExit flash sequence, GM TLC cloud backend involved in key delivery |
| 12:57 | `postOS_download_SPS.pcapng` | 118 MB | Not a vehicle flash — SPS staging the encrypted calibration package onto a USB flash drive (Kingston DataTraveler, 140MB via SCSI WRITE(10)); MDI2 tunnel idles; surfaced the second, JSON-based loopback API on `<LOOPBACK_IP>:31000/31010` |

## Key cross-cutting findings

### Finding 1 — DoIP responder topology (see Open Conflicts)
`<DOIP_RESPONDER_IP>` appears as an observed DoIP responder in four of the six captures (UDP/13400
vehicle-announcement traffic plus a TCP/13400 diagnostic exchange with the tablet). The observed
VIN response is retained only as `<VIN_REDACTED>`. Hardware ownership and forwarding topology are
not established by this capture set — unresolved, carried below under Open Conflicts rather than
assumed either way.

*History: an earlier pass read this responder as an independent diagnostic path bypassing MDI2
authorization; corrected 2026-11-11 to state only what the wire evidence supports (an observed
responder, not a proven ownership/bypass claim). Absence of this port in an earlier radio-side
scan does not refute captured traffic from this responder on a different capture path.*

### Finding 2 — Port 10123 opens pre-vehicle-presence, not SecurityAccess-gated
Across `capture_attempt1/2` and `multiple_intefaces_attempt1`, TCP/10123 opens successfully
multiple times from the low-port dance + Manager IPC alone, before any vehicle is present on the
bus. This confirms the persistent macOS-replay `ECONNREFUSED` documented in
[MDI2_DPDU_API_PROTOCOL_AUG2026.md](MDI2_DPDU_API_PROTOCOL_AUG2026.md) §11 is not a
vehicle-presence issue — it is the missing per-installation credential handed to the Manager over
loopback (Finding 3). Mechanics of that credential exchange live in that doc's §11.5; not restated
here.

### Finding 3 — Loopback Manager IPC is per-cycle, two independent protocols
- Binary protocol on `<LOOPBACK_IP>:8125` — opcode pairs `0x7f2/0x7f5` (identification),
  `0x8bf/0x8c0` (capability), `0x8d1/0x8d2` (device pairing with the 28-byte credential). Mechanics
  owned by [MDI2_DPDU_API_PROTOCOL_AUG2026.md](MDI2_DPDU_API_PROTOCOL_AUG2026.md) §11.5; this
  capture's contribution is behavioral, not structural: `DPS+SPS.pcapng` shows it **re-invoked at
  every one of the 18 dance cycles**, each time staging a ~16.7KB blob — not once at session start
  as earlier assumed.
- A second, separate JSON/HTTP loopback API on `<LOOPBACK_IP>:31000/31010` (seen in
  `postOS_download_SPS.pcapng`): plaintext messages such as `{"messageType":"HEALTH_CHECK"}` and,
  at teardown, `{"messageType":"SHUTDOWN"}` with a state object
  `{isDeviceConnected:false, isVehicleConnected:false, deviceSerialNumber:"", connectionVin:""}`.
  Looks like a higher-level session/health API distinct from the 8125 device-pairing protocol.
  Not part of the Manager's 14-port device bank (9001-9052) that
  [MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md](MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md) owns — recorded
  here as a capture fact; ownership of decoding it further belongs to whichever of those two docs
  picks it up next (neither currently claims it beyond citing its existence).

### Finding 4 — Real SecurityAccess seed/key pairs captured
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, radio ECU (D-PDU addr tag `f1/80`), two full
seed→key→grant $27 level-1 unlocks:

| Exchange | Request / seed / response / grant frames | Seed | Response | Result |
|---|---|---:|---:|---|
| Radio `0x80` #1 | 25884 / 25889 / 25946 / 25952 | 31 bytes | 12 bytes | `67 02` |
| Radio `0x80` #2 | 29381 / 29386 / 29437 / 29443 | 31 bytes | 12 bytes | `67 02` |

The fixed 16-byte prefix matches the target's DID `F0F3`; the final 15 bytes vary. Unit
identifiers and captured response values are withheld here. Concurrent TLS activity is consistent
with backend participation, but encrypted traffic and timing do not establish whether the backend
returned a master secret, derived intermediate, response, or authorization — the exact target
response formula and a usable master secret remain unresolved.

The 31-byte seed length (16B ECUID + 15B challenge) matches
[GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)'s stated
seed structure; the unresolved 31-vs-32-byte question itself is GSK's own Open Conflict (cites
`MDI2_DPDU_API_PROTOCOL_AUG2026.md` §6's doubt against an earlier, now-retired source's 32-byte
claim) — not restated or re-adjudicated here. Full CMAC/derivation analysis of this captured
seed/key material lives in GSK; this doc only supplies the frame-level provenance.

`DPS+SPS.pcapng` contains three-container amplifier `0x81` programming; radio `0x80` in that same
capture has DID reads and seed-only DoIP probes only, with no CAN SendKey or
RequestDownload/TransferData/TransferExit. The 14-container radio write belongs to the
`SPS_radioCal_and_OS_UpdateCHeck.pcapng` capture above, not `DPS+SPS.pcapng`.

*History: an earlier pass attributed the three byte-identical 60,675B writes in `DPS+SPS.pcapng`
cycles 8/10/13 to radio recalibration retries, and conflated which capture held the 14-segment vs.
3-container write. Corrected 2026-11-11 by fresh wire reconstruction: the 60,675B writes are
amplifier ECU `0x81` programming retries, and the 14-container radio write is in the SPS capture,
not `DPS+SPS.pcapng`.*

### Finding 5 — SBI reset trigger remains unidentified
No DID is literally named "SBI" and no field reads back `0xFF`→default in this capture set. What
is directly observed: the two $27 seed/key/grant unlocks in Finding 4, each followed by
`WriteDataByIdentifier (0x2E)` to `0xF190` (VIN), `0xF198` (repair-shop code, ASCII
`"9999988888"`), `0xF199` (programming date). These observations do not isolate the trigger.
Repeated similar transfers likewise do not demonstrate why SBI changed. The owner reports that SPS
module-information reads, calibration updates, and OS updates have reset the EEPROM bypass since
2025, whereas 2024-era updates did not; EEPROM dump comparisons establish the observed change, but
no particular command, internal validation path, or inverse operation is identified.
SecurityAccess was accepted in subsequent testing without an immediate loss of the observed ADB
shell; EEPROM was not read at that point, so a delayed change cannot be excluded.

*History: an earlier pass hypothesized SecurityAccess itself as the SBI-reset trigger. Corrected
2026-11-07: that attribution was a hypothesis, not a result demonstrated by this capture, and is
withdrawn — the trigger is unidentified, not SecurityAccess specifically.*

### Finding 6 — Radio calibration flash sequence (full mechanics)
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, tester→radio, all over TCP/10123:
- Radio requests in D-PDU stream 317: SecurityAccess level 1, `31 01 02 49`, then `10 02`
  programmingSession. The purpose of `02 49` is not established.
- 14x `RequestDownload (0x34)` — segment sizes 989B up to 15,284B.
- 19x `TransferData (0x36)` — up to 4095 bytes per UDS request (including service and block
  counter), with expected `7F 37/36 78` responsePending mid-transfer on the matching
  `RequestTransferExit (0x37)` calls (14x). The captured CSM containers' signing/encryption status
  is not established.
- After the transfer group: `22 F0 F0`, a second level-1 SecurityAccess, `2E F1 98`, `2E F1 99`,
  `31 01 03 9B`, `2E F1 90`, then `11 01`.
- Total: 385KB tester→device, 159KB device→tester, across write bursts at t≈17, 69, 79, 125,
  176-181, 207, 238s.
- Calibration payload is pulled from GM's backend first: `gspas-delivery.gm-cdn.com`
  (`<GM_CDN_IP>`) delivers ~84KB at t=149s, immediately before the flash bursts begin (~175s).
  "OS Update Check" is SPS querying the TLC backend (`tlc-dmz-gateway.ext.gm.com`,
  `gsitlc.ext.gm.com`) for target software levels — a cloud call, not vehicle-side.

*History: an earlier pass read the 19 TransferData segments as capped at 1460 bytes and read
`31 01 03 9B` as occurring before the download group. Corrected 2026-11-07: 1460 bytes was TCP
segmentation, not the UDS block size (actual cap ≤4095B per request); `03 9B` occurs during
finalization, after the transfer group, not before it. Its purpose remains unestablished either
way.*

### Finding 7 — Unexplained 221KB pull over port 9052 (`capture_attempt1.pcapng`, t=190-208s)
One-way, MDI2→tablet, back-to-back full-MTU segments over the same encrypted low-port channel used
for the unlock dance — not diagnostic traffic (no 10123/13400 activity at that point). Port 9052
is the same device port
[MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md](MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md) identifies as the
Manager's encrypted Get-Log-Files channel (§4.3/§4.20 there: 28-byte request, Blowfish-ECB body,
JSON-session-tagged log container). This capture's 221KB pull is consistent with a log/state pull
over that same channel but was not decoded against MML's now-solved Blowfish-ECB key/derivation at
the time of this timeline — routed to MML as the likely decoder, not re-derived here.

## Open threads for next session

1. Attempt to correlate the two captured seed/key pairs (Finding 4) against `dllsecurity.dll`
   `FUN_10001000` and `S84.dll` AES-CMAC directly (byte-level simulation against the already
   disassembled code), now that real input/output pairs exist — distinct from
   `UNTRIED_ATTACK_VECTORS.md`'s Frida S84.dll hooking plan, which captures a live transform
   rather than testing already-captured wire bytes offline.
2. Probe the JSON loopback API (`<LOOPBACK_IP>:31000/31010`, Finding 3) directly — likely much
   easier to replicate than the binary 8125 protocol for basic session/connection-state queries.

## Open conflicts

1. **DoIP-responder topology/ownership** (this doc's Finding 1). `<DOIP_RESPONDER_IP>` is observed
   as a DoIP responder in 4 of 6 captures; this capture set does not establish whether it is a
   vehicle-owned gateway, an independent diagnostic path, or something sharing authorization with
   the MDI2/Manager chain. An earlier pass's "independent bypass path" reading was walked back
   2026-11-11 (see Finding 1 History) but the underlying topology question is still open — no
   later capture or source in this corpus settles it.
   - **Cross-tree note:** this also touches `platform/ethernet_networking.md`, which is outside
     this reorg's authority to edit. That document should be checked for whether it independently
     names or maps this responder; this doc does not attempt to resolve the question there, only
     flags that the same open item crosses into that tree.

