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
| 12:07 | `capture_attempt1.pcapng` | 506 KB | Repeated-attempt session: 7 dance cycles in ~222s, DoIP UDS work against `.70` with SecurityAccess seed requested 3x but never keyed, ends with an unexplained 221 KB pull over port 9052 |
| 12:09 | `capture_attempt2.pcapng` | 75 KB | First **clean success**: dance → 10123 opens in ~2s → DoIP session to vehicle gateway `.70` → VIN read, 26-ECU scan, clean teardown |
| 12:17 | `multiple_intefaces_attempt1.pcapng` | 2.3 MB | Another full success, 3x 10123 opens, DoIP session to `.70` with VIN `1GC4YPE70RF102143`, confirms `192.168.177.2` is a dormant/unused entry in the Manager's own IPC response (never seen live on the wire) |
| 12:34 | `DPS+SPS.pcapng` | 80 MB | Main working session — 18 full dance+10123 cycles over ~740s; bulk calibration writes (~60-63KB) and reads (~41-50KB) over D-PDU/10123; cycles 8/10/13 are byte-identical 60,675B writes (the radio recal-retry loop); loopback 8125 IPC re-invoked at *every* cycle with a ~16.7KB blob each time; DoIP/13400 only 2 tiny probes near the end to `.70` |
| 12:45 | `SPS_radioCal_and_OS_UpdateCHeck.pcapng` | 87 MB | **The actual radio SecurityAccess + flash session** — two full seed/key/grant $27 unlocks (real bytes captured, see below), 14-segment RequestDownload/TransferData/RequestTransferExit flash sequence, GM TLC cloud backend involved in key delivery |
| 12:57 | `postOS_download_SPS.pcapng` | 118 MB | Not a vehicle flash — SPS staging the encrypted calibration package onto a **USB flash drive** (Kingston DataTraveler, 140MB via SCSI WRITE(10)); MDI2 tunnel idles; surfaced a second, JSON-based loopback API on `127.0.0.1:31000/31010` |

## Key cross-cutting findings

### 1. `192.168.171.70` — the vehicle's own DoIP gateway
Appears in 4 of 6 captures. Broadcasts DoIP vehicle-announcement over UDP/13400, then holds a
**direct TCP/13400 UDS session with the tablet, bypassing the MDI2's D-PDU/10123 path entirely**.
This is a second, independent diagnostic route through the MDI2's bridged Ethernet segment —
worth targeting directly once 10123 is solved, since it doesn't need the low-port dance at all
(only DoIP routing activation). VIN confirmed twice: **`1GC4YPE70RF102143`**.

### 2. Port 10123 opens reliably from a real Windows client — not vehicle- or SecurityAccess-gated
Across `capture_attempt1/2` and `multiple_intefaces_attempt1`, 10123 opens successfully multiple
times purely from the low-port dance + Manager IPC, **before** any vehicle is even present on the
bus. This confirms our live macOS replay's persistent `ECONNREFUSED` (session `c702cbc7`, §11-12
of the protocol doc) is not a vehicle-presence issue — it's specifically the missing
per-installation credential handed to the Manager over loopback (see finding 3).

### 3. Loopback Manager IPC is per-cycle, not one-time, and has TWO protocols
- Binary protocol on **127.0.0.1:8125** (`[u32 len][u32 opcode]...`, opcodes 0x7f2/0x7f5
  identification, 0x8bf/0x8c0 capability, 0x8d1/0x8d2 device pairing with the 28-byte credential
  — see protocol doc §12) — confirmed in `DPS+SPS.pcapng` to be **re-invoked at every one of the
  18 dance cycles**, each time staging a ~16.7KB blob, not just once at session start as originally
  documented.
- A **second, separate JSON/HTTP loopback API on 127.0.0.1:31000/31010** (`postOS_download_SPS.pcapng`):
  plaintext messages like `{"messageType":"HEALTH_CHECK"}` and, at teardown,
  `{"messageType":"SHUTDOWN"}` with a state object
  `{isDeviceConnected:false, isVehicleConnected:false, deviceSerialNumber:"", connectionVin:""}`.
  This looks like a higher-level session/health API, distinct from the low-level 8125 device-pairing
  protocol — worth targeting for a simpler read of connection state without the binary protocol.

### 4. Real SecurityAccess seed/key pairs captured — first genuine crypto material for this vehicle
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, radio ECU (D-PDU addr tag `f1/80`), two full
seed→key→grant $27 level-1 unlocks:

**Unlock #1** (t≈174-175s, frames 25884-25952):
- Seed (`67 01`, 31 bytes): `00 4b 41 dc 00 00 16 00 06 10 41 45 61 01 14 ac 26 a7 af 86 09 5d 40 dc da f9 e3 b7 e0 6c a9`
- Key (`27 02`, 12 bytes): `7a 22 54 89 23 3b 23 e4 3b 45 8a 87`
- Grant: `67 02` accepted, no NRC.

**Unlock #2** (t≈193s, frames 29386-29443):
- Seed (31 bytes, shares the same 16-byte prefix as unlock #1):
  `00 4b 41 dc 00 00 16 00 06 10 41 45 61 01 14 ac bb b7 4b d6 c8 4f 89 a2 bd 00 84 91 47 8a 23`
- Key (12 bytes): `47 b6 46 10 c4 73 e8 59 9f ed db db`
- Grant: `67 02` accepted.

The fixed 16-byte prefix `00 4b 41 dc 00 00 16 00 06 10 41 45 61 01 14 ac` also reads back
verbatim from **DID 0xF0F3** — it's the ECU's static security-identity constant, not part of the
random challenge (only the trailing 15 bytes vary between the two seeds).

**The ~1s seed→key gap coincides with active TLS traffic to `tlc-dmz-gateway.ext.gm.com`**
(23.223.221.70) — strong evidence the key is computed server-side by GM's Techline Connect
backend, not locally by `dllsecurity.dll`/`S84.dll` on the tablet. This corroborates the existing
`TISVCSV4_MULTI_OEM_KEYSERVER_AUG2026.md` finding that `S84.dll`'s key is "supplied by caller,
not embedded — GM's servers provision it at runtime." With two real seed/key pairs now in hand
sharing a known-constant prefix, a third capture (or a captured pair from a different vehicle)
would let the varying 15-byte challenge → 12-byte key mapping be tested against both the
`dllsecurity.dll` `FUN_10001000` bytecode-VM and `S84.dll` AES-CMAC candidates directly — not
attempted yet.

### 5. The SBI reset mechanism, per the user's original account, is corroborated structurally
No DID is literally named "SBI" and no field reads back `0xFF`→default in this capture. What's
directly observed instead: the two $27 seed/key/grant unlocks above, each followed by
`WriteDataByIdentifier (0x2E)` to `0xF190` (VIN), `0xF198` (repair-shop code = ASCII
`"9999988888"`), `0xF199` (programming date). The working theory (unchanged from before this
analysis, now better evidenced): the SBI flag reset is an **internal EEPROM side-effect of
exercising $27 SecurityAccess itself**, not a directly-addressed DID — consistent with the
byte-identical repeated 60,675B writes seen 3x in `DPS+SPS.pcapng` (cycles 8/10/13), i.e. the
"check → SBI resets → recalibrate anyway" pattern the user described produces exactly this
signature: multiple near-identical flash operations close together.

### 6. Radio calibration flash sequence (full mechanics)
From `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, tester→radio, all over 10123:
- `RoutineControl (0x31)` — routine `0249` then `039b` (pre-erase/dependency check)
- `DiagnosticSessionControl (0x10 0x02)` — enter programmingSession
- 14x `RequestDownload (0x34)` — segment sizes 989B up to 15,284B
- 19x `TransferData (0x36)` — high-entropy (encrypted/signed) 1460B blocks
- 14x `RequestTransferExit (0x37)`, with expected `7F 37/36 78` responsePending mid-transfer
- Total: 385KB tester→device, 159KB device→tester, across write bursts at t≈17, 69, 79, 125,
  176-181, 207, 238s.
- Calibration payload itself is pulled from GM's backend first: `gspas-delivery.gm-cdn.com`
  (23.59.151.27) delivers ~84KB at t=149s, immediately before the flash bursts begin (~175s).
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
- Probe the JSON loopback API (127.0.0.1:31000/31010) directly — likely much easier to replicate
  than the binary 8125 protocol for basic session/connection-state queries.
- Consider targeting `192.168.171.70` (direct DoIP to the vehicle gateway) as an alternate path
  that doesn't require solving the 10123 low-port unlock at all, when a vehicle is present.
