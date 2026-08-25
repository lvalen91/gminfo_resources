# MDI2 D-PDU API Protocol — Full Reconstruction from Real DPS Captures

**Date:** 2026-08-24
**Context:** Bench work to build a native macOS/Python client for the Bosch GM MDI2 that talks
UDS to the vehicle with **zero GM Windows software** (DPS/SPS/MDI Manager). No hardware was
available for this pass (MDI2 + vehicle not on the bench) — this is a from-capture protocol
reconstruction so implementation work can continue offline. Source: ~170MB of Wireshark
captures taken earlier the same day (`DPS+SPS.pcapng`, `SPS_radioCal_and_OS_UpdateCHeck.pcapng`,
plus three of our own failed native-client attempts), reduced to reassembled PDU-API messages
(`msgs.pkl`, 6528 messages) and a UDS record extract (`diag_records_fixed.pkl`, 257 requests),
then analyzed by four parallel agents (byte-level, frame-cited) plus a local-model cross-check.

## 0. The one finding that changes the plan

**CORRECTION (2026-08-24, later same day):** the original wording below ("real DPS never uses
raw DoIP") is too absolute and was refuted by cross-referencing a pre-existing analysis corpus
(`gm_dps/docs/`, specifically `DPS_MASTER_REFERENCE.md` §15.5 and `LIVE_DPS_CAPTURE_ECU80_AUG2026.md`)
that predates this doc. **Both transports are real and both carry live UDS diagnostics — which
one is used is a user/config choice in DPS, not a fixed rule.** A live-captured DPS session with
Vehicle Architecture = `GM VIP/SDV1 (GB)`, Subtype = `DoIP (Optimal)` ran genuine raw ISO-13400
DoIP through `GM_DOIP_32.dll` (source address `0x0EF5`) and captured real `$27 01`→`$67 01`
SecurityAccess directly on the DoIP wire for all 27 ECUs on that vehicle. Today's capture set
(below) happened to be entirely sessions that used the D-PDU/PDU-API subtype instead — that's
real and correctly documented, but it's evidence for "the D-PDU path exists and works," not for
"the DoIP path is never used." `mdi2_doip_query.py`'s approach was therefore NOT chasing a dead
end — it needs the same session-control fix originally suspected (retry `10 03` through NRC
`0x21`, etc.), not abandonment. Treat §9's "do not continue investing in raw DoIP" as WITHDRAWN.
The two transports should be thought of as parallel, both-real paths to reimplement, not a
right-answer/wrong-answer pair.

Original (2026-08-24, morning) finding, kept for the capture evidence it's still accurate about:
Across the 10 real DPS sessions captured that day (streams 106,131,183,215,244,296,317,360,415,438
— spanning a full radio recalibration/flash, several "read installed software" inventory passes,
and a bus-topology probe), **zero** UDS bytes travelled over `192.168.171.70:13400` — but this
was because none of those particular sessions happened to be running the `DoIP (Optimal)`
subtype, not because that subtype doesn't exist or doesn't work. The MDI2 *does* run its
Ethernet/DoIP-enable IOCTL sequence (`IOCTL 28` → `IOCTL 37` → `IOCTL 22`, see §5) once per DPS
launch, and `.70:13400` does come up (confirmed via UDP vehicle-announcement broadcasts); in the
sessions captured that day, DPS happened to route every diagnostic request through the
**D-PDU API (ISO 22900-2) tunnelled over the same TCP/10123 PDU-API socket** instead, via
`PDUCreateComLogicalLink` + `PDUStartComPrimitive` (fully documented below, still accurate for
that transport).

**Implication (revised):** `mdi2_doip_query.py` (dialing `.70:13400` and sending raw ISO-13400 DoIP
diagnostic messages) is chasing a transport DPS itself doesn't use for UDS. It's not wrong that
the relay/DoIP-entity comes up — it does — but getting a real ECU response through it is
unproven and off the path DPS actually takes. **`mdi2_replay.py`'s approach (PDU-API passthrough)
is the right transport; it was just missing most of the required setup.** All future native-client
work should target the D-PDU API flow documented below, not the raw-DoIP path.

---

## 1. Wire framing

TCP frame: `<u32 total_len LE><u32 mid LE><payload>` on port 10123 (`192.168.171.2`).
`total_len` includes the 8-byte header. `mid` request/response pairs are almost always
`N` / `N+1` (odd request → even response), matching **ISO 22900-2 D-PDU API** calls tunnelled
over TCP — confirmed by the `PDU_COPT_*` ComPrimitive type constants observed on the wire
(`0x8001`=STARTCOMM, `0x8003`=UPDATEPARAM, `0x8004`=SENDRECV/actual data).

## 2. Two-socket-per-session topology (confirmed independently by 3 of 4 agents)

Every DPS "session" (whether a quick identify pass or a full flash) opens **two** TCP
connections to `192.168.171.2:10123`, always adjacent stream ids (e.g. 317/318, 106/107,
183/184):

- **Command socket** (lower stream id): sends `mid 2180` (`0x884`) hello with channel field
  `0`; MDI assigns a session/channel id in the `mid 2181` (`0x885`) reply (payload byte 12,
  e.g. `0x25`, `0x1f`, `0x20`...). Carries **every** request mid: `PDUCreateComLogicalLink`,
  `PDUGetComParam`/`PDUSetComParam`, `PDUSetUniqueRespIdTable`, `PDUConnect`,
  `PDUStartComPrimitive`, `PDUIoCtl`, `PDUDisconnect`, `PDUDestroyComLogicalLink`.
- **Event socket** (stream id + 1): sends its own `mid 2180` hello, with the channel field
  **pre-filled to the command socket's assigned id** to bind to the same logical session.
  Carries **only** async result/event items: `mid 2147` (`0x863`) — every diagnostic RX/TX
  confirmation — and occasionally `mid 1505` (multi-frame length indication, precedes a
  multi-frame UDS response).

**A client that only opens one socket will never see a diagnostic response**, even if its
request goes out correctly — this is very likely why earlier native-client attempts saw silence.

## 3. D-PDU API mid opcode table (reconciled across all 4 agent reports; hex = decimal mid)

| mid (req/resp) | ISO 22900-2 call (best identification) | Notes |
|---|---|---|
| `0x884`/`0x885` (2180/2181) | session hello / assign channel | channel id in resp byte 12 |
| `0x886`/`0x887` | bind event channel | used on the event socket |
| `0x888`/`0x889` | capability query / keepalive ping | harmless to poll; carries no diag data |
| `0x44D`/`0x44E` (1101/1102) | GetVersion | |
| **`0x44F`/`0x450`** (1103/1104) | **PDUCreateComLogicalLink** | resource id at payload byte 9: `0x06`=raw CAN, `0x2A`=MDI-managed ISO-TP |
| `0x451`/`0x452` (1105/1106) | **PDUDestroyComLogicalLink** | payload = handle only |
| `0x457`/`0x458` (1111/1112) | **PDUGetComParam**(handle, paramId) | |
| `0x459`/`0x45A` (1113/1114) | **PDUSetComParam**(handle, paramId, value) | 34-byte payload, paramId @off17, value @off30 |
| **`0x45D`/`0x45E`** (1117/1118) | **PDUSetUniqueRespIdTable** | 24B = clear table, 174B = install 6-entry addressing table (see §4) |
| **`0x45F`/`0x460`** (1119/1120) | **PDUConnect**(handle) | resp = `00000000 <u32 timestamp>` |
| `0x461`/`0x462` (1121/1122) | **PDUDisconnect**(handle) | |
| **`0x463`/`0x464`** (1123/1124) | **PDUStartComPrimitive** | the only mid that carries UDS bytes out; see §4 layout |
| `0x467`/`0x468` (1127/1128) | **PDUIoCtl**(handle, ioctlId, data) | handle `0` + id `0x0B` = clear RX buf (before every CreateCLL); handle `0xFFFFFFFF` + id `0x06` = read battery voltage in mV (after every teardown, e.g. `0x2f6c`=12140mV) |
| `0x863` (2147, event socket only) | async diagnostic event | TX-confirm (`blockLen`=0) or RX data (`blockLen`>0); see §4 |
| `1505` (event socket only) | multi-frame length indication | precedes a multi-frame `0x863` response |

## 4. Per-operation bring-up sequence (gold-standard reconstruction, from stream 317 — a full
radio flash — cross-checked against streams 106/131/183/215/244/296/360/415/438)

DPS never reuses a ComLogicalLink across operations — every logical step (wake ECU, read a
DID, do the flash) gets its own fresh CLL, created and destroyed. Two CLL flavours:

**A. Resource `0x06` — raw-CAN link** (used briefly for bus-wide/monitor operations):
```
PDUIoCtl(0, 0x0B)                              # clear RX buffer
PDUCreateComLogicalLink(resource=0x06)          # -> handle H
PDUGetComParam(H, 0x09) -> baud (e.g. 0x0007A120 = 500000)
PDUGetComParam(H, 0x0C) / 0xAE / 0xB8
PDUSetUniqueRespIdTable(H, <24B clear>)
PDUSetComParam(H, 0x16=0) ; PDUSetComParam(H, 0x19=0x22)
PDUConnect(H)
StartComPrimitive(H, type=0x8004, dataLen=0, NumSendCycles=0, NumReceiveCycles=-1)   # persistent RX cop
StartComPrimitive(H, type=0x8001)               # STARTCOMM
StartComPrimitive(H, type=0x8003)               # UPDATEPARAM
PDUSetComParam(H, 0x74=1) ; PDUIoCtl(H, 0x0C, <54B>) ; PDUSetUniqueRespIdTable(H, <24B clear>)
StartComPrimitive(H, type=0x8003)
StartComPrimitive(H, type=0x8004, <first real CAN frame with ISO-TP PCI + UDS bytes>)
```
Raw-CAN payload is a padded 8-byte frame with PCI byte, e.g. `14da45f1 02 10 03 00 00 00 00 00`
(single-frame ISO-TP: length nibble `02`, then `10 03`).

**B. Resource `0x2A` — MDI-managed ISO-TP/UDS link** (used for everything addressed at one
ECU — this is what the native client needs):
```
PDUIoCtl(0, 0x0B)
PDUCreateComLogicalLink(resource=0x2A)          # -> handle H
PDUSetUniqueRespIdTable(H, <24B clear>)
PDUSetComParam(H, 0x15=0) ; 0x16=0 ; 0x19=0x22 ; 0x1B=0 ; 0xAB=1 ; 0xC6=1
PDUConnect(H)
StartComPrimitive(H, type=0x8004, dataLen=0, NumSendCycles=0, NumReceiveCycles=-1)   # persistent RX cop
StartComPrimitive(H, type=0x8001)               # STARTCOMM
StartComPrimitive(H, type=0x8003)               # UPDATEPARAM
PDUSetComParam(H, 0x1C=1)
PDUSetUniqueRespIdTable(H, <174B — installs req/resp CAN-id pair, see below>)
StartComPrimitive(H, type=0x8003)
StartComPrimitive(H, type=0x8004, dataLen=N, NumSendCycles=1, <CAN-id + bare UDS bytes>)  # actual request
```
Resource-0x2A payload has **no PCI, no padding** — just `<4-byte CAN id><raw UDS bytes>`, e.g.
`14da45f1 22 f0 f3`. The MDI handles ISO-TP segmentation/reassembly itself and delivers
complete multi-frame UDS responses as one `0x863` event (preceded by a `mid 1505` length
indication for anything long, e.g. the ~230-byte `F182` software-inventory record).

**`PDUStartComPrimitive` payload layout** (resource 0x2A, the actual send):
```
u32 CLLhandle | u16 copId | u16 0x2510 | u16 copType | u16 0x0000 | u32 dataLen
| dataLen bytes: [u32 CANid_BE][UDS payload]
| u8 0x01 | u32 Time_ms | u32 NumSendCycles | u32 NumReceiveCycles
| u32 0 | u32 0x00000004 | u32 flags | u32 0
```
`Time_ms`/`NumSendCycles`=-1 on a *separate* CLL is how DPS offloads **cyclic TesterPresent**
to the MDI hardware: `3E 80` on functional id `0x10DBFEF1`, Time=1000ms, NumSendCycles=-1 —
confirmed by `0x863` TX-confirm events landing at exactly 1.000s spacing for the life of the
flash.

**`0x863` event payload tail:** `... <u32 CANid_BE> <u32 blockLen> <u32 CANid_BE> <payload>`.
`blockLen==0` = TX confirmation only (no data). `blockLen>0` = the actual RX data, reported
against the **persistent RX cop id**, not the id of the request that triggered it.

## 5. Addressing (`PDUSetUniqueRespIdTable`, 174-byte form) — response IDs are asymmetric

Installed once per addressed CLL, 6 entries of 25 bytes each
(`05010000 00120000 <u32 paramId> 05010000 06000000 01 <u32 value>`):

| paramId | meaning | example (ECU 0x45) | example (ECU 0x80) |
|---|---|---|---|
| `0x1F` | physical request CAN id | `0x14DA45F1` | `0x14DA80F1` |
| `0x1E` / `0x1D` | request format / ext-addr | `0x37` / `0` | `0x37` / `0` |
| `0x22` | **physical response CAN id** | `0x14DAF145` | **`0x145AF180`** |
| `0x21` / `0x20` | response format / ext-addr | `0x37` / `0` | `0x37` / `0` |

**Critical: the response id is NOT a fixed transform of the request id.** Requests are always
`0x14DA<ECU>F1`. Response ids follow a per-ECU prefix table that must be *discovered*, not
assumed — confirmed by the functional `22 F1B0` sweep (24 nodes reply, each with its own
address byte):

| resp prefix | ECU addresses seen |
|---|---|
| `0x141A` | 0x31, 0x58, 0x59, 0x6D, 0xBF |
| `0x142A` | 0x11, 0x18, 0x1A, 0x28, 0x40, 0x41, 0xBD |
| `0x144A` | 0x75, 0xA4, 0xA8, 0xB9, 0xBA |
| `0x145A` | 0x60, 0x68, 0x80, 0x81, 0x97, 0xBE |
| `0x14DA` | 0x45 (the only ECU that responds on the "expected" prefix) |

Functional broadcast request id: `0x10DBFEF1` (used for `3E 80` TesterPresent and the `22 F1B0`
node-discovery sweep). A separate, unrelated functional id `0x18DB33F1` (OBD-II style, 11/29-bit)
appears only in a legacy-bus-probe stream and gets NRC `0x22 conditionsNotCorrect` — this
vehicle is GMLAN-only, the legacy probe is DPS being thorough, not a required step.

## 6. UDS session-control / SecurityAccess ordering (ground truth from stream 317's full flash
+ streams 183/215's read-only passes — supersedes the earlier "add 10 03/27 01 before every
read" hypothesis, which was based on incomplete data)

1. **Reads and routine calls generally do NOT require `10 03` or `27` first**, as long as a
   functional `3E 80` TesterPresent is being kept alive on `0x10DBFEF1` (explicitly, ~800ms
   apart, or via the hardware cyclic cop). Confirmed: `22 F0F3`, `22 F1B0`, `22 F190` (VIN),
   `22 F181/F182/F1CB/F081/F1A0/F0B4`, and `31 01 FF01` all succeed with **no** prior session
   control or security access, across 5 independent sessions (106,131,183,215,296,360,415,438).
2. **The one exception:** ECU `0x45` gets an explicit physical `10 03` (extended session) +
   `31 01 02 0E FF FF FF` (RoutineControl, routine `0x020E` = wakeUpNetworks) as the very first
   thing in every session that touches it — this is the network wake-up, not access control.
   `0x45` responded `7F 10 21` (busyRepeatRequest) 16-21 times in a row in some sessions before
   accepting — **a client must retry `10 03` on NRC `0x21`**, not treat it as failure.
3. **`27` SecurityAccess appears exactly twice in the entire day's data, both immediately before
   a WRITE-class operation**, never before a read:
   - Before the `34/36/37` download sequence (flashing new calibration data to ECU `0x80`).
   - Before a batch of `2E WriteDataByIdentifier` calls (writing `F198` repairShopCode, `F199`
     programmingDate, `F190` VIN) + `31 01 03 9B` + `11 01` ECUReset.
   Seed request: `27 01` → 31-byte seed response (`67 01 <31 bytes>` — first 16 bytes are a
   fixed challenge header, last 15 are random per-request). Key: `27 02 <12-byte key>`, computed
   by DPS in ~0.7-1.1s. Response is `7F 27 78` (responsePending) then `67 02` (unlocked) —
   **`0x78` must be treated as "keep waiting", not a failure.**
4. **`10 02` (programmingSession) is requested AFTER SecurityAccess succeeds, not before** —
   order is `27 01` → `27 02` → `31 01 02 49` → `10 02` → `34/36/37...`.
5. Bus-quiesce bracket around the flash: `10 03` (functional, all ECUs) → `85 02`
   (ControlDTCSetting off, functional) → `28 03 01` (CommunicationControl disableRxAndTx,
   functional) → SecurityAccess+flash → `10 01` (defaultSession, functional) implicitly restores
   both — **no explicit `85 01` or `28 00 01` is ever sent.**

## 7. Flash/download cycle structure (14 cycles observed, all to ECU 0x80)

Each cycle: `34 00 44 <u32 addr=0> <u32 size>` → `74 20 0F FF` (maxBlockLength 0x0FFF) →
one or more `36 <seq> <data>` (≤4093 bytes/frame) → `76 <seq>` → `37` → `77` (with `7F 37 78`
pending on the last block only, ~0.87s). `RequestDownload.size` always equals the total
`TransferData` payload for that cycle. Every `36 01` payload begins with a fixed GM SPS package
header: `03 01 00 <u16 blockId> 00 "CSM" 00×21 <32-byte digest>` followed by ASCII
`"Infotainment"`. Block IDs observed: `0x0002`-`0x000F` (14 blocks). After the last `37`, DPS
reads `22 F0F0` (pending, then positive) which returns the list of just-programmed block IDs —
a natural post-flash verification read to replicate.

## 8. What our native client is currently missing (both scripts — consolidated)

`mdi2_replay.py` and `mdi2_doip_query.py` together implement only the session hello
(`0x884`/`0x885`) and the device-global Ethernet-activation IOCTLs (28/37/22) — **neither ever
sends a `PDUCreateComLogicalLink`, so neither ever obtains a CLL handle, so neither can ever
call `PDUConnect` or `PDUStartComPrimitive`. Zero UDS bytes reach the wire in any of the three
captured attempts.** This is confirmed by direct comparison against real DPS traffic from the
identical `0x884` handshake onward — real DPS's very next calls are `PDUIoCtl(0,0x0B)` →
`PDUCreateComLogicalLink` (which our client never sends).

Additional bugs found in the existing scripts (secondary to the above, for when a proper D-PDU
implementation exists):
- `mdi2_replay.py` opens only **one** TCP connection; a second, channel-bound connection is
  required to ever see a response (`0x863` never arrives on the command socket).
- `mdi2_replay.py`'s `send_raw()` uses a flat 2.0s recv timeout; the real IOCTL 37 ack takes
  **3.26s**, so that specific call needs its own ≥5s timeout or the reply desyncs every
  subsequent request/response pairing by one frame.
- `mdi2_replay.py`'s preamble-replay only patches the channel id at frame offset 7; the
  `0x463`-family frames it's replaying (indices 13-17 of `PREAMBLE_HEX`) carry the channel id a
  **second time at frame offset 11**, which is left stale.
- Both scripts send a second, redundant `0x884` on the same socket; the channel-bound `0x884`
  belongs on the second (event) connection, not repeated on the first.

## 9. Recommended path forward (no hardware needed to prepare this)

Build a new client around the resource-`0x2A` CLL flow in §4, targeting ECU `0x45` first (it's
the only ECU that needs an explicit wake — `10 03` retried through `7F 10 21`, then
`31 01 02 0E FF FF FF`), then read `22 F0F3` as the simplest possible "did we get a real
response" smoke test (expected: `62 F0F3 <16 bytes>`). This exactly mirrors stream 317 frames
24531-24638 and needs two sockets, the full resource-0x2A bring-up sequence, and the
174-byte `PDUSetUniqueRespIdTable` with `0x1F=0x14DA45F1` / `0x22=0x14DAF145`. Once that round-
trips, the same skeleton generalizes to any ECU by discovering its response prefix via the
`22 F1B0` functional sweep first (§5) rather than assuming `0x14DAF1<ecu>`.

**Do not continue investing in the raw-DoIP-on-.70:13400 path** (`mdi2_doip_query.py`) for UDS
traffic — it's architecturally real (the MDI2 does bring up a DoIP entity there) but is not what
gets a working ECU response in any of today's 10 real-DPS sessions.
