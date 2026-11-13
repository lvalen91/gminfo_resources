# Aug 24 2026 session — full pcap timeline (all 6 captures)

Consolidated timeline from 6 captures in `gm_dps/misc/Aug24_session/`, taken while GM DPS/SPS
and the MDI2 Manager were used against a real MDI2 (Bosch VCI) and a 2024/2025 Chevrolet
Silverado. Non-WiFi/internet traffic only (device subnet, loopback IPC, USB, multicast beacon;
GM backend TLS noted where relevant, generic internet/telemetry excluded). Six agents
(3 sonnet on the small connection-attempt files, 3 opus on the large SPS/DPS files) independently
extracted each file via tshark; this doc merges their findings. Complements §10-12 of
`MDI2_DPDU_API_PROTOCOL_AUG2026.md`, which covers the low-port unlock-dance mechanics in depth
(not re-derived here).

## Chronological file order (by mtime)

| Time | File | Size | Characterization |
|---|---|---|---|
| 12:07 | `capture_attempt1.pcapng` | 506 KB | Repeated-attempt session: 7 dance cycles in ~222s, DoIP UDS work against `<DOIP_RESPONDER_IP>` with SecurityAccess seed requested 3x but never keyed, ends with an unexplained 221 KB pull over port 9052 |
| 12:09 | `capture_attempt2.pcapng` | 75 KB | First **clean success**: dance → 10123 opens in ~2s → DoIP session to responder `<DOIP_RESPONDER_IP>` → VIN read, 26-ECU scan, clean teardown |
| 12:17 | `multiple_intefaces_attempt1.pcapng` | 2.3 MB | Another full success, 3x 10123 opens, DoIP session to `<DOIP_RESPONDER_IP>` with VIN `<VIN_REDACTED>`, confirms `<MANAGER_REPORTED_IP>` is a dormant/unused entry in the Manager's own IPC response (never seen live on the wire) |
| 12:34 | `DPS+SPS.pcapng` | 80 MB | Main working session — 18 full dance+10123 cycles over ~740s; bulk calibration writes (~60-63KB) and reads (~41-50KB) over D-PDU/10123; cycles 8/10/13 are byte-identical 60,675B writes (amplifier ECU `0x81` programming retries; corrected 2026-11-11); loopback 8125 IPC re-invoked at *every* cycle with a ~16.7KB blob each time; DoIP/13400 only 2 tiny probes near the end to `<DOIP_RESPONDER_IP>` |
| 12:45 | `SPS_radioCal_and_OS_UpdateCHeck.pcapng` | 87 MB | **The actual radio SecurityAccess + flash session** — two full seed/key/grant $27 unlocks (real bytes captured, see below), 14-segment RequestDownload/TransferData/RequestTransferExit flash sequence, GM TLC cloud backend involved in key delivery |
| 12:57 | `postOS_download_SPS.pcapng` | 118 MB | Not a vehicle flash — SPS staging the encrypted calibration package onto a **USB flash drive** (Kingston DataTraveler, 140MB via SCSI WRITE(10)); MDI2 tunnel idles; surfaced a second, JSON-based loopback API on `<LOOPBACK_IP>:31000/31010` |

## Key cross-cutting findings

### 1. Observed DoIP responder — ownership and forwarding topology unresolved
**Corrected 2026-11-11:** `<DOIP_RESPONDER_IP>` appears in four of six captures as an
observed DoIP responder on the captured network. The capture shows UDP/13400
vehicle-announcement traffic and a TCP/13400 diagnostic exchange with the tablet.
Hardware ownership and forwarding topology are not established: these packets do not
prove that the responder is a vehicle-owned gateway or an independent path bypassing
MDI2 authorization. The observed VIN response is retained only as `<VIN_REDACTED>`.
Absence of this port in an earlier radio-side scan does not refute captured traffic
from this responder on a different capture path.

### 2. Port 10123 opens reliably from a real Windows client — not vehicle- or SecurityAccess-gated
Across `capture_attempt1/2` and `multiple_intefaces_attempt1`, 10123 opens successfully multiple
times purely from the low-port dance + Manager IPC, **before** any vehicle is even present on the
bus. This confirms our live macOS replay's persistent `ECONNREFUSED` (see §11-12
of the protocol doc) is not a vehicle-presence issue — it's specifically the missing
per-installation credential handed to the Manager over loopback (see finding 3).

### 3. Loopback Manager IPC is per-cycle, not one-time, and has TWO protocols
- Binary protocol on **<LOOPBACK_IP>:8125** (`[u32 len][u32 opcode]...`, opcodes 0x7f2/0x7f5
  identification, 0x8bf/0x8c0 capability, 0x8d1/0x8d2 device pairing with the 28-byte credential
  — see protocol doc §12) — confirmed in `DPS+SPS.pcapng` to be **re-invoked at every one of the
  18 dance cycles**, each time staging a ~16.7KB blob, not just once at session start as originally
  documented.
- A **second, separate JSON/HTTP loopback API on <LOOPBACK_IP>:31000/31010** (`postOS_download_SPS.pcapng`):
  plaintext messages like `{"messageType":"HEALTH_CHECK"}` and, at teardown,
  `{"messageType":"SHUTDOWN"}` with a state object
  `{isDeviceConnected:false, isVehicleConnected:false, deviceSerialNumber:"", connectionVin:""}`.
  This looks like a higher-level session/health API, distinct from the low-level 8125 device-pairing
  protocol — worth targeting for a simpler read of connection state without the binary protocol.

### 4. Real SecurityAccess seed/key pairs captured — first genuine crypto material for this vehicle
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, radio ECU (D-PDU addr tag `f1/80`), two full
seed→key→grant $27 level-1 unlocks:

**Corrected 2026-11-11, fresh wire reconstruction:**

| Exchange | Request / seed / response / grant frames | Seed | Response | Result |
|---|---|---:|---:|---|
| Radio `0x80` #1 | 25884 / 25889 / 25946 / 25952 | 31 bytes | 12 bytes | `67 02` |
| Radio `0x80` #2 | 29381 / 29386 / 29437 / 29443 | 31 bytes | 12 bytes | `67 02` |

The fixed 16-byte prefix matches the target's DID `F0F3`; the final 15 bytes vary.
Unit identifiers and captured response values are omitted. Concurrent TLS activity is
consistent with backend participation, but encrypted traffic and timing do not establish
whether the backend returned a master secret, derived intermediate, response or authorization.
The exact target response formula and usable master secret remain unresolved.

`DPS+SPS.pcapng` contains **three-container amplifier `0x81` programming**, while radio
`0x80` has DID reads and seed-only DoIP probes, without radio CAN SendKey or
RequestDownload/TransferData/TransferExit. The former radio-recalibration retry attribution
was incorrect. The 14-container radio write belongs to the SPS capture above.

See [the central seed/key and signature evidence guide](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

### 5. SBI reset trigger remains unidentified (corrected 2026-11-07)
No DID is literally named "SBI" and no field reads back `0xFF`→default in this capture. What's
directly observed instead: the two $27 seed/key/grant unlocks above, each followed by
`WriteDataByIdentifier (0x2E)` to `0xF190` (VIN), `0xF198` (repair-shop code = ASCII
`"9999988888"`), `0xF199` (programming date). These observations do not isolate the trigger:
the former attribution to SecurityAccess itself was a hypothesis, not a result of this capture.
Repeated similar transfers likewise do not demonstrate why SBI changed. The owner reports that
SPS module-information reads, calibration updates, and OS updates have reset the EEPROM bypass
since 2025, whereas updates in 2024 did not. EEPROM dump comparisons establish the observed
change, but no particular command, internal validation path, or inverse operation is identified.
SecurityAccess was accepted in subsequent testing without an immediate loss of the observed ADB
shell; EEPROM was not read at that point, so delayed changes cannot be excluded.

### 6. Radio calibration flash sequence (full mechanics)
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, tester→radio, all over 10123:
- Radio requests in D-PDU stream 317: SecurityAccess level 1, `31 01 02 49`, then `10 02`
  programmingSession. The exact purpose of `0249` remains unverified.
- 14x `RequestDownload (0x34)` — segment sizes 989B up to 15,284B
- 19x `TransferData (0x36)` — up to 4095 bytes per UDS request, including service and block
  counter. The earlier 1460-byte figure described TCP segmentation, not UDS block size; the
  captured CSM containers' signing/encryption status is not established.
- 14x `RequestTransferExit (0x37)`, with expected `7F 37/36 78` responsePending mid-transfer
- After the transfer group: `22 F0 F0`, a second level-1 SecurityAccess, `2E F1 98`,
  `2E F1 99`, `31 01 03 9B`, `2E F1 90`, then `11 01`. Correction 2026-11-07: `039B`
  occurs in finalization, not before the download; its purpose is not established.
- Total: 385KB tester→device, 159KB device→tester, across write bursts at t≈17, 69, 79, 125,
  176-181, 207, 238s.
- Calibration payload itself is pulled from GM's backend first: `gspas-delivery.gm-cdn.com`
  (<GM_CDN_IP>) delivers ~84KB at t=149s, immediately before the flash bursts begin (~175s).
  "OS Update Check" = SPS querying the TLC backend (`tlc-dmz-gateway.ext.gm.com`,
  `gsitlc.ext.gm.com`) for target software levels — a cloud call, not vehicle-side.

### 7. Unexplained: 221KB pull over port 9052 (`capture_attempt1.pcapng`, t=190-208s)
One-way, MDI2→tablet, back-to-back full-MTU segments over the same "encrypted" low-port channel
used for the unlock dance — not diagnostic traffic (no 10123/13400 activity at that point). Best
guess: a log or device-state pull outside the D-PDU path, similar in spirit to the loopback
8125/31000 status APIs but over the network side. Not yet decoded; worth revisiting alongside the
S84.dll/dllsecurity.dll annotation work if log retrieval is a priority.

## Open threads for next session
- Decode the 221KB port-9052 blob (`capture_attempt1.pcapng`) — likely log/state pull.
- Attempt to correlate the two captured seed/key pairs against `dllsecurity.dll` `FUN_10001000`
  and `S84.dll` AES-CMAC directly (byte-level simulation), now that real input/output pairs exist.
- Probe the JSON loopback API (<LOOPBACK_IP>:31000/31010) directly — likely much easier to replicate
  than the binary 8125 protocol for basic session/connection-state queries.
- Characterize `<DOIP_RESPONDER_IP>` using capture-backed transport observations;
  establish hardware ownership and forwarding topology before proposing it as an
  independent diagnostic path or assuming different authorization requirements.
