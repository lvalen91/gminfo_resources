# MDI2 D-PDU API Protocol

**Scope:** The Bosch GM MDI2's D-PDU (ISO 22900-2) wire protocol tunnelled on TCP/10123 —
frame format, two-socket session topology, the mid-opcode table, per-operation bring-up
sequences, the `PDUSetUniqueRespIdTable` addressing scheme, UDS session-control/SecurityAccess
*ordering* over this transport, server-side RE of `DPDULib.dll`/`bvtx4j32.dll`
(DPDULib/bvtx4j32), the port-9xxx management-plane pre-activation sequence, and the
loopback ident service (TCP/8125) resolution.
**Does NOT live here:** the raw-DoIP (.70:13400) session-level narrative and the
DoIP-responder-topology question — see `AUG24_SESSION_FULL_PCAP_TIMELINE.md` (APT) finding #1;
the settled SecurityAccess key-derivation algorithm and canonical seed/key facts — see
`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK); raw UDS bypass technique — see
`MDI2_RAW_UDS_BYPASS_GUIDE.md` (carried unchanged, cited by name only); the MDI2 *Manager*
stack (GM_MDI_Ident.exe, Blowfish-ECB session JSON, log-pull) — see
`MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` (MML).

**Date:** 2026-08-24, corrected in place through 2026-11-14 (see History lines throughout).
Operator summary lives outside this tree at `tools/mdi2_client/docs/PROTOCOL.md`.
**Bench context:** MDI2 over direct USB RNDIS to radio ECU 0x80, never on a vehicle OBD2 port
(confirmed 2026-11-14; some capture-derived prose below still describes the original vehicle
capture, not the current bench — flagged inline where it matters).
**Evidence base:** §1-§9 reconstructed from DPS-side Wireshark captures (~170MB,
`DPS+SPS.pcapng`, `SPS_radioCal_and_OS_UpdateCHeck.pcapng`), reduced to `msgs.pkl` (6528
reassembled PDU-API messages) and `diag_records_fixed.pkl` (257 UDS requests), cross-checked by
4 parallel agents + a local-model pass. §10 is independent server-side binary RE (3 decompiled
Bosch VCI Software 9.1.2752.177 binaries, 170-function candidate subset, 6 Opus passes:
STRONG 157/MAJORITY 13/NONE 0). §11-§12 are live-hardware bench results layered on top of both.

---

## 0. Both transports are real — this doc covers only the D-PDU path

**Finding (2026-08-24, corrected same day):** an earlier draft of this section claimed "real
DPS never uses raw DoIP." That is wrong and is withdrawn. Cross-referencing a pre-existing
corpus (`gm_dps/docs/DPS_MASTER_REFERENCE.md` §15.5, `LIVE_DPS_CAPTURE_ECU80_AUG2026.md`) shows a
live DPS session (Vehicle Architecture `GM VIP/SDV1 (GB)`, Subtype `DoIP (Optimal)`) ran genuine
ISO-13400 DoIP through `GM_DOIP_32.dll` (source address `0x0EF5`) and captured real `$27 01` →
`$67 01` SecurityAccess directly on the DoIP wire, across 27 ECUs. **Both the D-PDU/PDU-API
path (TCP/10123) and the raw-DoIP path (`.70:13400`) are real, both carry live UDS, and which
one a given DPS session uses is a config/subtype choice, not a fixed rule.**

That 27-ECU DoIP sweep found the defect isolated to one ECU: only radio ECU `0x80` returns the
degenerate all-`0xFF` SecurityAccess seed; all 26 other swept ECUs return varied real seeds.
This confirms the all-`0xFF` behavior is specific to this one ECU's own `$27` implementation,
not a systemic transport or tooling artifact.

`GM_DOIP_32.dll` selects the tester source address from the DoIP version byte the entity announces: version `2` gives `0x0EF5`, version `3` gives `0x0E80`, and any other version aborts routing activation. `[FW]` (disassembly of `fcn.1000e540`, `0x1000ea08`-`0x1000ea4c`; source: external `GM_DOIP_32.dll` disassembly notes, §8). The live MDI2 bench uses `0x0EF5`.

**Hazard (live capture session, 2026-08-24).** An independent DoIP client that connected over MDI2's RJ45 port with the same default tester source address (`0x0EF5`) evicted the concurrent USB-side session instead of being refused with the ISO 13400 "source address already registered on a different socket" response; the USB-side session then logged `Ethernet network is down` and timed out, which aborted a read-only module scan. The MDI2 therefore behaves as if it keys DoIP routing-activation sessions by tester source address rather than per physical interface `[I]` (distinct from the session-table exhaustion in §11.4). `[C]` for the incident (source: external bench-session notes, §15.6). Do not run an independent DoIP client against an MDI2 that a DPS/SPS session may be using, even on the other interface, unless it uses a non-colliding source address.

**`J2534Wrapper.dll` is not a thin pass-through.** It independently performs DoIP discovery
(`DoIPSendDiscoveryRequest[Ex]`, a `CDHCPListener` class that listens for DHCP offers to learn
the MDI2's IP), device enumeration, and management of `GM_MDI_Ident.exe` as a Windows service
(`OpenSCManager`/`StartService`). It shares source path
`j2534-wrapper\win32\solutions\doip-stack\channel.cpp` with `GM_DOIP_32.dll` — same authored
codebase, confirming the raw-DoIP and D-PDU paths above are sibling implementations, not
independent ones. Separately confirmed: **actual UDS diagnostics never flow through the J2534
PassThru read/write API at all** (`j2534_api_log.txt` — only 6 distinct call types across the
whole file: Open/ReadVersion/Connect/Ioctl/Disconnect/Close, no
ReadMsgs/WriteMsgs/StartMsgFilter ever) — real UDS traffic goes exclusively over one of the two
paths above.

The 10 sessions this doc's captures are built from (streams 106,131,183,215,244,296,317,360,
415,438 — a full radio recalibration/flash, several inventory reads, a bus-topology probe) all
happened to use the D-PDU/PDU-API subtype. Zero UDS bytes crossed `.70:13400` in those sessions
**because none of them ran the `DoIP (Optimal)` subtype**, not because that path doesn't work —
the MDI2 still runs its Ethernet/DoIP-enable IOCTL sequence (`IOCTL 28`→`37`→`22`, §4/§10.4) once
per DPS launch regardless, and `.70:13400` does come up (confirmed via UDP vehicle-announcement
broadcasts).

**What this means for this doc:** everything below (§1-§12) documents the D-PDU/PDU-API
transport only, because that's what this capture set exercised end-to-end and server-side RE
confirmed independently. It is not a claim that D-PDU is "the right path" and raw DoIP "the
wrong path" — both are legitimate GM transports. The raw-DoIP session itself (topology,
responder behavior, `.70` ownership question) is out of scope for this doc; see
`AUG24_SESSION_FULL_PCAP_TIMELINE.md` finding #1, which carries that as its own open item.

> History: earlier text here and in §9 concluded "do not continue investing in the raw-DoIP
> path" / "mdi2_doip_query.py is chasing a dead end". That conclusion contradicts the correction
> above (both transports are real) and is withdrawn. `mdi2_doip_query.py` needs the
> session-control fix suspected at the time (retry `10 03` through NRC `0x21`, etc.); that
> investigation belongs to the raw-DoIP doc.

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
request goes out correctly.

**History:** to replay against a live MDI, capture the live channel id from the `0x885` reply
(payload offset 12) and substitute the channel byte in each command frame's leading handle word.

## 3. D-PDU API mid opcode table (reconciled across all 4 agent reports; hex = decimal mid)

| mid (req/resp) | ISO 22900-2 call (best identification) | Notes |
|---|---|---|
| `0x884`/`0x885` (2180/2181) | session hello / assign channel | channel id in resp byte 12 |
| `0x886`/`0x887` | bind event channel | used on the event socket |
| `0x888`/`0x889` | capability query / keepalive ping | harmless to poll; carries no diag data |
| `0x44D`/`0x44E` (1101/1102) | GetVersion | |
| **`0x44F`/`0x450`** (1103/1104) | **PDUCreateComLogicalLink** | resource id at payload byte 9: `0x06`=raw CAN, `0x2A`=MDI-managed ISO-TP. The `0x450` reply is status-only (`0c000000 50040000 00000000`) — it does **not** return a handle. The CLL handle is client-assigned and deterministic: `handle = (channel_id << 24) \| index` (high byte = channel from the `0x885` reply, low byte = sequential CLL index). |
| `0x451`/`0x452` (1105/1106) | **PDUDestroyComLogicalLink** | payload = handle only |
| `0x457`/`0x458` (1111/1112) | **PDUGetComParam**(handle, paramId) | |
| `0x459`/`0x45A` (1113/1114) | **PDUSetComParam**(handle, paramId, value) | 34-byte payload, paramId @off17, value @off30 |
| **`0x45D`/`0x45E`** (1117/1118) | **PDUSetUniqueRespIdTable** | 24B = clear table, 174B = install 6-entry addressing table (§5) |
| **`0x45F`/`0x460`** (1119/1120) | **PDUConnect**(handle) | resp = `00000000 <u32 timestamp>` |
| `0x461`/`0x462` (1121/1122) | **PDUDisconnect**(handle) | |
| **`0x463`/`0x464`** (1123/1124) | **PDUStartComPrimitive** | the only mid that carries UDS bytes out; see §4 layout |
| `0x467`/`0x468` (1127/1128) | **PDUIoCtl**(handle, ioctlId, data) | handle `0` + id `0x0B` = clear RX buf (before every CreateCLL); handle `0xFFFFFFFF` + id `0x06` = read battery voltage in mV (after every teardown, e.g. `0x2f6c`=12140mV) |
| `0x863` (2147, event socket only) | async diagnostic event | TX-confirm (`blockLen`=0) or RX data (`blockLen`>0); see §4 |
| `1505` (event socket only) | multi-frame length indication | precedes a multi-frame `0x863` response |

> History (2026-08-27, live bench, native macOS replay of stream 414 + DoIP x80 read): confirmed
> the client-assigned handle formula above against every `0x459/0x45D/0x45F/0x461/0x463` frame
> in stream 414 (channel `0x13` → handles `0x13000002…0x13000006`) — no handle needs to be
> scraped from any response. Same pass also established: `.70` DHCP lease requires the
> `br-usb` bridge to stay up **~18.85 s** (bare eth-enable IOCTLs alone do not lease `.70` if
> the session tears down promptly); the SET_BRIDGE-enable IOCTL blocks **~3.28 s** server-side
> while eth0 links; DoIP addressing confirmed live as tester `0x0EF5`, gateway `0x0C45`
> (answers from proxy source `0x0045`), radio ECU 0x80 physical target `0x0A80` (answers from
> `0x2580`), functional `0xEFFE`; `wakeUpNetworks` = `31 01 02 0E FF FF FF` (the `FF FF FF`
> suffix is required — omitting it gives `7F 31 13`); radio `27 01` seed on this path is a
> **null 31×`0xFF`**, and the ID/SBI DIDs read with no SecurityAccess unlock. Full bench log:
> `~/Desktop/MDI2_DPDU_DoIP_x80_bench_report.md` (outside this tree). Replay engine:
> `tools/mdi2_client/mdi2/dpdu_replay.py` supersedes the earlier guess-based `mdi2/dpdu.py`
> (unverified builders — recommended for deletion).

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
u32 CLLhandle | u16 copId | u16 (channel<<8)|0x10 | u16 copType | u16 0x0000 | u32 dataLen
| dataLen bytes: [u32 CANid_BE][UDS payload]
| u8 0x01 | u32 Time_ms | u32 NumSendCycles | u32 NumReceiveCycles
| u32 0 | u32 0x00000004 | u32 flags | u32 0
```
The u16 after `copId` is `(channel << 8) | 0x10`, where `channel` is the D-PDU channel = the CLL
handle's high byte (`handle >> 24`) — not a fixed `0x2510`. (History, 2026-11-08: the originally
captured `0x2510` was only the vehicle-tested channel-0x25 case; channel 0x1E gives `0x1E10`
(source capture: `mdi2_direct_client_WIP`), channel 0x2C gives `0x2C10`. Code derives this via
`_cop_marker(handle)` in `live_programming_transport.py` / `programming_transport.build_one_shot`.)

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

**Tester-source-byte reconciliation:** the table above is from this doc's D-PDU/PDU-API pcaps,
in which DPS uses tester byte `F1` (GMLAN-standard physical tester), e.g. ECU 0x80 =
req `0x14DA80F1` / resp `0x145AF180`, ECU 0x45 = req `0x14DA45F1` / resp `0x14DAF145`. A
separate GDS-side capture (`diagnostics/icloud_diag/dps_logs/A11_CSM_x80.Txt`) enumerates the
*same* ECU set with tester byte `F2` instead — ECU 0x80 = req `0x14DA80F2` / resp `0x145AF280`.
The **response prefix** (0x145A for 0x80, 0x14DA for 0x45) is identical in both; only the low
tester byte differs — it is tool/session-dependent, not a fixed vehicle property. When
targeting ECU 0x80 outside these pcaps, treat `0x14DA80F2 / 0x145AF280` (the GDS-captured pair)
as the canonical addressing.

Functional broadcast request id: `0x10DBFEF1` (used for `3E 80` TesterPresent and the `22 F1B0`
node-discovery sweep). A separate, unrelated functional id `0x18DB33F1` (OBD-II style, 11/29-bit)
appears only in a legacy-bus-probe stream and gets NRC `0x22 conditionsNotCorrect` — this
vehicle is GMLAN-only; the legacy probe is DPS being thorough, not a required step.

## 6. UDS session-control / SecurityAccess ordering (ground truth from stream 317's full flash
+ streams 183/215's read-only passes)

1. **Reads and routine calls generally do NOT require `10 03` or `27` first**, as long as a
   functional `3E 80` TesterPresent is being kept alive on `0x10DBFEF1` (~800ms apart, or via
   the hardware cyclic cop). Confirmed: `22 F0F3`, `22 F1B0`, `22 F190` (VIN),
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

   Seed request: `27 01` → seed response `67 01 <seed bytes>`. History (corrected 2026-09-10):
   RH850 VIP `$27` handler disasm (`FUN_000b67d0`) confirms the seed structure is a **16-byte
   fixed ECUID + random challenge**, not the pre-2026-09-10 "31-byte seed / 12-byte key" figure
   (that older figure, as applied to *this* non-degenerate ECUID+challenge seed, was a
   byte-offset misread of an earlier capture).

   **Clarifying note (2026-11-21):** the "31-byte seed / 12-byte key" figure appears in two
   distinct contexts that must not be conflated. (a) The misread described above concerns the
   **non-degenerate per-request seed** documented in this subsection (fixed ECUID + random
   challenge, per the RH850 disasm). (b) §11.4 reports a **degenerate all-`0xFF` seed /
   12-byte zero key** exchange (`27 01`/`27 02` → `67 02`) as a live bench result; the full
   exchange (`27 01` → `67 01` + 31 bytes of `0xFF`; `27 02` + 12 zero bytes → `67 02`) is
   documented in `diagnostics/diagnosticsd_security_access.md` (L80-81, 132, 163-164) as a
   distinct bypass-state response. (b) is not a misread. The two are different seeds that
   share the same byte counts (31 / 12). The disputed point in the
   Open conflict immediately below concerns only the non-degenerate seed's total length
   (31 vs 32 bytes), not the degenerate all-`0xFF` seed, whose length (31 bytes) is not in
   dispute.

   **Open conflict — see §Open Conflicts #1 below:** the exact total seed length is disputed
   between a 32-byte reading (16-byte ECUID `004B41DC…14AC` + 16-byte random, attributed to a
   live capture) and a 31-byte reading (16-byte ECUID `002642250000160006104145610114AC` +
   15-byte random, from an independently re-parsed capture,
   `module_dumps/10017909_canbus_reset/A11_sps_datareset_log.Txt`, a different physical unit).
   This doc's own re-check as of 2026-09-10 had high confidence in the 31-byte reading but could
   not re-verify the original 32-byte capture's raw bytes by script (only by eye) before closing
   the question, and is therefore unresolved on its own evidence — not resolved by picking
   GSK's 31-byte figure, since GSK's number comes from a different capture set than this doc's
   32-byte outlier. Carried forward rather than silently dropped.

   Key: `27 02 <key bytes>`, computed by DPS in ~0.7-1.1s. Response is `7F 27 78`
   (responsePending) then `67 02` (unlocked) — `0x78` must be treated as "keep waiting," not a
   failure. The handler is **SHA-256-based** (H0..H7 init constants + a CRC-32 poly-`0xEDB88320`
   table both present in the binary), not an LFSR or small-seed scheme — see
   `eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` for the full disasm writeup and
   `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK) for the canonical seed/key doc. The actual
   key-derivation algorithm (how the 16-byte key is computed from ECUID+challenge) was **not**
   recovered from this handler — no static secret/salt found in the VIP image — **OPEN**.
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

## 8. Native-client gap analysis (both existing scripts)

`mdi2_replay.py` and `mdi2_doip_query.py` together implement only the session hello
(`0x884`/`0x885`) and the device-global Ethernet-activation IOCTLs (28/37/22) — **neither ever
sends a `PDUCreateComLogicalLink`, so neither ever obtains a CLL handle, so neither can ever
call `PDUConnect` or `PDUStartComPrimitive`. Zero UDS bytes reach the wire in any of the three
captured attempts.** This is confirmed by direct comparison against real DPS traffic from the
identical `0x884` handshake onward — real DPS's very next calls are `PDUIoCtl(0,0x0B)` →
`PDUCreateComLogicalLink` (which the client never sends). This gap applies to both the D-PDU and
the raw-DoIP script equally — it says nothing about which transport is "right" (§0).

Secondary bugs found in the existing scripts:
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

## 9. Recommended path forward (D-PDU, no hardware needed to prepare this)

Build a client around the resource-`0x2A` CLL flow in §4, targeting ECU `0x45` first (it's the
only ECU that needs an explicit wake — `10 03` retried through `7F 10 21`, then
`31 01 02 0E FF FF FF`), then read `22 F0F3` as the simplest "did we get a real response" smoke
test (expected: `62 F0F3 <16 bytes>`). This mirrors stream 317 frames 24531-24638 and needs two
sockets, the full resource-0x2A bring-up sequence, and the 174-byte `PDUSetUniqueRespIdTable`
with `0x1F=0x14DA45F1` / `0x22=0x14DAF145`. Once that round-trips, the same skeleton generalizes
to any ECU by discovering its response prefix via the `22 F1B0` functional sweep first (§5)
rather than assuming `0x14DAF1<ecu>`.

> History: this section originally closed with "do not continue investing in the raw-DoIP-on-
> .70:13400 path," presented as a standing recommendation. That line is withdrawn per §0 — both
> transports are real GM paths; this section's actual contribution is the concrete D-PDU
> build-order recommendation above, not a verdict on DoIP.

---

## 10. Server-side confirmation from the MDI2 Manager binaries (2026-08-25)

Everything in §1-§9 was reconstructed **from the DPS side**, byte-by-byte, out of Wireshark
captures. This section is the **other half of the wire**: the same protocol read directly out of
the MDI2 Manager / Bosch VCI Software implementation, i.e. the code on the far end of the socket.
The two reconstructions were produced independently and they agree.

**Provenance.** Three decompiled binaries from the Bosch VCI Software (GM) 9.1.2752.177
installer — `DPDULib.dll` (Bosch's ISO 22900-2 D-PDU API implementation, 17,229 functions),
`bvtx4j32.dll` (the SAE J2534 PassThru DLL layered on top of it, 7,764 functions), and
`gm_mdi_manager.exe` (the MFC manager GUI, 4,477 functions). A 170-function protocol-candidate
subset was annotated by six independent Opus passes; consensus STRONG 157 / MAJORITY 13 /
NONE 0. Per-function detail: `gm_dps/disassembly/annotations/mdi2mgr_candidates.annotations.md`
(outside this tree). These binaries retain real C++ class/method names, `__FILE__` paths
(`D:\ws\Global_VCI\vtx-vci\GM_9_1\6\...`) and unstripped log literals, which is why convergence
was total.

### 10.1 The DoIP version check is computed, not a constant (`02 FD` explained)

`DoIPComm::ProcessHeader` (`DPDULib.dll`, entry `0x100de380`) is the real DoIP header gate.
The entire version test is one line:

```c
else if ((*param_1 == (byte)~param_1[1]) && (*param_1 < 3)) { return 0; }  /* accept */
else                                                        { return 1; }  /* reject */
```

- This confirms the capture-derived `02 FD` prologue: `~0xFD == 0x02`.
- It also extends it: the check is `hdr[0] == ~hdr[1] && hdr[0] < 3`, so protocol versions
  `0x00` (`00 FF`), `0x01` (`01 FE`) and `0x02` (`02 FD`) are **all** accepted by the MDI2;
  `0x03` and above are rejected. A native client must send a matching complement pair, but is
  not restricted to `02 FD`.
- It explains a long-standing dead end: grepping the binaries for a literal `0x02`/`0xFD`
  constant finds nothing, because the constant is never materialised.

A second, mode-aware version check exists separately in `DoIPUDPComm::ProcessVa`
(`0x10123230`): on the vehicle-announcement path it explicitly rejects a stored version byte of
`1` when running in ISO mode, logging `"ISO - But v1"`. So `0x01` is accepted by the generic
header parser but refused by the ISO-mode VA handler. Send `02 FD`.

### 10.2 `DoIPVCIProto::ChkMsgHdr` is a source-address filter, NOT the version check

`FUN_1012d960` — despite the name — never looks at the version bytes. It resolves the VCI's
logical address from ComParam `0x6b` (primary) falling back to ComParam `0x6c` (secondary) via
`FUN_101346e0` and filters the message on source address. Any prior note attributing the version
check to `ChkMsgHdr` is wrong; the version check is §10.1.

### 10.3 UDP port 13401 is transient, which is why captures never show it

Port `0x3459`/**13401** is written in exactly one place in the whole DLL:
`CModuleSystem::VehicleIdRequest` (`0x10037460`). For "combination mode 1" only, it sets
`this+0x1d6 = 0x3459` (13401), `this+0x1d8 = 0x3458` (13400), `this+0x1d4 = 1`, performs the
combined vehicle-ID scan, and then **restores `this+0x1d6 = 0`** before returning. The
constructor `CModuleSystem::CModuleSystem` (`0x10033270`) initialises `+0x1d8 = 0x3458` and
`+0x1d6 = 0`, i.e. 13400 is the steady state and 13401 exists only inside one call.

Related: in `ProcessEntityIdMsg` (full DLL, around `0x100eb580`) the port-13401 comparison only
selects a log label/bitmask ("VAM" vs "VId Response") — it is **not** an accept/reject gate.
Actual acceptance is gated by the `DoIPFilterNetworks` bit `0x40000000` plus `AllowedAddress()`.

**Practical upshot:** a native client should listen on 13400 and does not need to bind 13401.

### 10.4 The Ethernet/DoIP-enable IOCTL sequence, confirmed at the implementation level

The captures showed `IOCTL 28` → `IOCTL 37` → `IOCTL 22` once per DPS launch. The source of that
sequence: in `bvtx4j32.dll`, `CJ2534Channel_Ethernet::PassThruConnect` →
`SetProtocolConnectionComParameters` issues, in this order, all with `hCLL = 0xFFFFFFFF`
(module-level, no logical link):

| # | Captured IOCTL | Registered name | Notes |
|---|---|---|---|
| 1 | 28 (`0x1c`) | `PDU_IOCTL_MS_SET_ETH_PIN_OPTION` | id global `DAT_10147cd8`; selects the DoIP pin option |
| 2 | 37 (`0x25`) | `PDU_IOCTL_MS_SET_BRIDGE_SWITCH_STATE` | id global `DAT_10147cf8`; sets `this+0x568 = 1`, payload at `this+0x570` |
| 3 | 22 (`0x16`) | `PDU_IOCTL_GET_ETH_PIN_OPTION` | id global `DAT_10147cc0`; read-back / verification |

**Teardown** (not visible in captures): `CJ2534Channel_Ethernet::PassThruDisconnect` **reverses**
the activation order:
1. `this+0x568 = 0`, then `PDU_IOCTL_MS_SET_BRIDGE_SWITCH_STATE` (`DAT_10147cf8`) — bridge switch OFF
2. then `PDU_IOCTL_MS_SET_ETH_PIN_OPTION` (`DAT_10147cd8`) with a zeroed value — eth pin option OFF

There is no read-back on teardown. A native client that wants to leave the MDI2 in the state DPS
leaves it in should replay this reversed pair on shutdown.

Named configuration items behind these IOCTLs (the IOCTL-to-item pairing is inferred `[I]`): `EthernetActPinNumber` (struct `+0`) and `EthernetSenseState` (`+4`) for the pin option in the PDU layer; `VTX_RT_CFG_ETHERNET_ENABLE` (with `_IP`, `_MASK`, `_GATEWAY_*`, `_DHCP_STATIC`, `_HW_ADDR`) and `VTX_RT_CFG_DOIP_NAT_MODE` in `BVTX-VCI-RT.dll`; and `VCI:has_ethernet`, `VCI:doip_nat_mode`, `MGR:has_doip_mac_addr_support`, `MGR:has_doip_ip_addr_support`, `MGR:has_doip_ip_netmask_support` in the ident service. Source: external DoIP/VCI driver evidence notes, §6.

A static pass over `BVTX4J32.dll` found no anti-clone or device-authenticity check on this IOCTL path, only argument sanity checks `[I]`; any genuine-device validation would therefore sit lower: in the VTX runtime, the MDI2 firmware, or the ident service's encrypted module whitelist (`valid-module_*.bin`, source: external ident-service evidence notes, §7). Source: external IOCTL-activation evidence notes.

### 10.5 CAVEAT: the numeric IOCTL/ComParam IDs are MDF-assigned at runtime, not constants

This is the most important operational caveat in this section. `CJ2534Server::Initialize`
(`bvtx4j32.dll`) does **not** use compile-time IOCTL numbers. It registers 35 vendor IOCTL names
as strings, e.g.:

```c
(*vtbl+0x18)(0x8023, "PDU_IOCTL_RESET",                    &DAT_10147c70);
(*vtbl+0x18)(0x8023, "PDU_IOCTL_CLEAR_TX_QUEUE",           &DAT_10147c74);
...
(*vtbl+0x18)(0x8023, "PDU_IOCTL_GET_ETH_PIN_OPTION",       &DAT_10147cc0);
(*vtbl+0x18)(0x8023, "PDU_IOCTL_VEHICLE_ID_REQUEST",       &DAT_10147cc4);
...
(*vtbl+0x18)(0x8023, "PDU_IOCTL_MS_SET_ETH_PIN_OPTION",    &DAT_10147cd8);
(*vtbl+0x18)(0x8023, "PDU_IOCTL_MS_CLEAR_DOIP_ENTITY_LIST",&DAT_10147cdc);
...
(*vtbl+0x18)(0x8023, "PDU_IOCTL_MS_SET_BRIDGE_SWITCH_STATE",&DAT_10147cf8);
```

That vtable slot is `PDUGetObjectId(PDU_OBJ_IOCTL_ID = 0x8023, name, &out_id)`; the numeric id is
supplied **by the MDF (manufacturer definition file) at connect time** and written into a
per-name global. The same is done in bulk for ComParams a few lines earlier
(`PDUGetObjectId(0x8024, 0xab, ...)` over the `CP_*` name table).

**Therefore:** the hardcoded `0x1c` / `0x25` / `0x16` are correct **for the captured session and
that MDF**, but are not guaranteed stable across DPS versions, firmware versions or MDF
revisions. **The durable facts are the STRING names and the CALL ORDER, not the numbers.** A
robust native client should resolve ids by name (or at minimum re-derive them per session)
rather than baking in hex.

### 10.6 ADJUDICATED: positional index in the registration list is NOT the IOCTL id

One analysis pass proposed mapping `22 = PDU_IOCTL_VEHICLE_ID_REQUEST` and
`28 = PDU_IOCTL_MS_CLEAR_DOIP_ENTITY_LIST` by assuming the 1-based position of a name in the
35-name registration list equals its numeric id. **Rejected**, in order of strength:

1. **Arithmetically impossible.** The list has exactly 35 entries (globals `DAT_10147c70` …
   `DAT_10147cf8`, stride 4 ⇒ `(0xcf8-0xc70)/4 + 1 = 35`). No positional scheme, 0- or 1-based,
   yields **37** — one of the three ids actually captured.
2. **Contradicted by the mechanism (§10.5).** Each name gets its own out-parameter global that
   `PDUGetObjectId` fills at runtime from the MDF; position in the source listing carries no
   information about the assigned value.
3. **Contradicted by direct behavioural observation (§10.4).** `PassThruConnect` demonstrably
   calls `DAT_10147cd8` first, `DAT_10147cf8` second and `DAT_10147cc0` third, and the capture
   shows `28` then `37` then `22` in exactly those positions, fixing 28 =
   `MS_SET_ETH_PIN_OPTION`, 37 = `MS_SET_BRIDGE_SWITCH_STATE`, 22 = `GET_ETH_PIN_OPTION`. (The
   positional guess would have given 21/20 for `GET_ETH_PIN_OPTION` — it does not even
   self-consistently reproduce one of the three.)

Behavioural evidence beats name-position inference. §10.4's mapping stands.

### 10.7 Protocol identity and framing constants, confirmed

Independently confirmed on the MDI2 side, matching the capture reconstruction:

- Bus type string: `IEEE_802_3`. Protocol string: `ISO_14229_5_ON_ISO_13400_2` (UDS-on-DoIP).
  These are the exact literals to request when selecting a resource.
- DoIP framing: 8-byte header, payload length big-endian at offset +4, maximum accepted payload
  `0x100400` (1 MiB + 1 KiB) — anything larger is rejected before allocation.
- Routing Activation request: 15 bytes (19 with the optional OEM-specific field).
- Routing Activation response is validated as: source address `@+8`, entity address `@+10`,
  response code `@+12`.
- Client side, `GM_DOIP_32.dll` treats response code `0x10` as success and waits at most 2000 ms for the response (log text "Timed out while waiting for routing activation response", return code 9). `[FW]` Source: external `GM_DOIP_32.dll` disassembly notes, §8, §12.
- Vehicle announcement / VIR response layout: VIN `@+8` (17 bytes), logical address `@+0x19`,
  EID `@+0x1b` (6 bytes), GID `@+0x21` (6 bytes).
- Vehicle Identification Request sizes: 8 B (broadcast), 14 B (by EID), 25 B (by VIN).

### 10.8 `Port='8080'` in the PDUConstruct option string is the loopback ident-service default

`CJ2534Server::Initialize` builds the D-PDU API construct option string as:

```c
FUN_10034cb0(local_6c, "VCIName='%s' Port='8080'");   /* -> m_PduApi.Construct(local_6c, this) */
```

i.e. it hands `PDUConstruct` an option string containing `Port='8080'`, which does not match the
TCP/10123 PDU-API port in the captures (nor 13400/13401). `PDUConstruct`'s export wrapper
(`DPDULib.dll` `0x10083510`) treats the argument as free-form text and passes it straight to
`CPDUAPI::Construct`, so the value is consumed deeper in `DPDULib`/`bvtx_vci_rt`.

**Resolved (2026-08-25).** The `'8080'` literal is a hardcoded *default* in `bvtx4j32`'s option
string; it is **not** the port actually dialed. The value reaching `bvtx_vci_rt` is the loopback
ident-service port, computed at runtime as `8097 + ProductGroupId` (the only compile-time
constant is the offset `0x1fa1 = 8097`; `lea esi,[eax+0x1fa1]` at `0x1005f6d2`, both upstream and
downstream sockets to `127.0.0.1`). `ProductGroupId` is a small integer read from the Windows
registry (`HKLM\SOFTWARE\WOW6432Node\BOSCH\VTX-VCI\GM\ProductGroupId`); absent/0 → port `8097`.
For this bench's live `ProductGroupId = 0x1c = 28`, the port is **8125** — exactly the
`127.0.0.1:8125` loopback ident service in §12. The ident-service TCP client is
`BVTX-VCI-RT.dll` (`CIdentClient::Connect`); `dps.exe`/`dpsvcs.dll`/`tisvcsv4.dll`/`vcs_dps.dll`
are Winsock-free. This has no relation to the TCP/10123 D-PDU port or 13400/13401. (Confirmed:
`diagnostics/gm_dps/docs/BVTX_VCI_PROTOCOL_DETAIL_ports_and_config.txt:15-50`,
`CONFIG_ARCHAEOLOGY_AUG2026.md:15-17`, both outside this tree.)

### 10.9 What this section changes for the native-client plan

- §5's IOCTL sequence is confirmed, and now has a documented teardown (§10.4).
- The DoIP prologue is confirmed and slightly relaxed (`00`/`01`/`02` accepted, §10.1).
- Port 13401 can be ignored (§10.3).
- Hardcoded IOCTL numbers should be treated as session-specific, with the string names as the
  stable identifier (§10.5). This is the one place the existing scripts are silently fragile.

---

## 11. Port 10123 pre-activation, the management-plane handshake, and the loopback ident service

### 11.1 The 7-step pre-activation sequence (2026-08-25, capture + live replay)

Real capture `DPS+SPS.pcapng` (frames 7447-7791) shows port **10123 refuses connections until a
specific 7-step sequence completes on other ports first**. Reconstructed byte-for-byte from the
capture and replayed against live MDI2 hardware (IP `192.168.171.2`, our host `.10`, real capture
host was `.30`):

1. **13-port magic handshake**, standard ports `9052,9001,9006,9051,9007,9014,9009,9003,9012,
   9050,9008,9010,9013`: connect, send `0053500000300000` (8B), receive `0053500000310000` (8B).
2. **Port 9052 extra exchange #1**: send captured 212-byte blob, receive 92-byte response.
3. **Port 9011 handshake — non-standard magic**: send `0053500000210000` (not `...300000`),
   receive `0053500000200000` (not `...310000`). This port uses a different magic pair than the
   other 13 and was skipped in earlier partial reconstructions.
4. **Port 9052 extra exchange #2**: send captured 60-byte blob, receive 212-byte response.
5. **Port 9009 keepalive**: send captured 60-byte blob (structurally identical to 9052's traffic),
   receive 60-byte response.
6. **Port 9050, 4-message poll**: 3x identical 28-byte poll frames (only a 1-byte counter at
   buffer offset 11 increments: `f6,f7,f8`), each gets an identical-structure 116-byte response
   (counter echoed back at the same offset); then a 4th, differently-structured 108-byte "trigger"
   frame (counter `f9`), which gets a 108-byte response.
7. Real capture: TCP SYN to port 10123 **0.5ms after step 6 completes**, and it succeeds.

All request/response payloads share an 8-byte header: 4 zero bytes + a big-endian
length-of-remainder field (e.g. `...00cc` = 204 bytes follow → 212-byte total frame), followed by
a per-port session tag (4 bytes, e.g. `fba0ae42`, `a2404d1c`, `d177f3f6`) that increments by a
fixed +1 in its low byte on the 3 identical 9050 polls, then encrypted/opaque content.

**Live-hardware replay result (byte-verbatim, all 7 steps exactly as captured, run 2026-08-25)**:
every response byte matched the captured response byte-for-byte, for every step, including the
9052/9009 "encrypted" exchanges — strong evidence this layer is a deterministic function of input
bytes only, not a live random nonce/session key (a true nonce-based session would not reproduce
identical ciphertext for identical stale-request replay days later). Despite the byte-perfect
replay, **port 10123 remained refused (`ECONNREFUSED`)** in this live test — see §11.3/§11.4 for
the eventual explanation.

Reconstruction script: `mdi2_full_sequence.py` (scratchpad; implements all 7 steps with literal
captured bytes).

### 11.2 Cross-cycle confirmation (18 cycles in the same capture, frames 13039-13064)

The capture contains **18 repeats** of the §11.1 cycle before a 10123 connection (paired SYNs at
frames 7764/7774, 13064/13075, 15413/15425, … 47231/47244, etc.) — a **per-session ritual
repeated every time**, not a one-time device-boot unlock.

Diffing cycle 1 (frame 7743+) against cycle 2 (frame 13039+) byte-for-byte isolates the actual
variable: each TCP connection gets a 4-byte tag immediately after the 8-byte header (e.g.
`fba0ae42` cycle 1 vs `9e3e5132` cycle 2 on port 9052; `d177f3f6` vs `a8a7c135` on port 9050)
that increments by exactly +1 per subsequent message sent on that same connection, but the
encrypted payload content after the tag is byte-identical across cycles. This is consistent with
the tag being a client-chosen, per-connection nonce/counter that the device simply echoes and
increments against, not a device-issued session secret — i.e. the live replay's reuse of stale
tag values was not functionally wrong, since the device honored it and returned the
expected structurally-correct response both times. This rules out "wrong nonce" as the reason
10123 stayed refused in §11.1's live test.

### 11.3 `PDU START` resolved (2026-11-07) — port 10123's actual re-arm mechanism

Decrypting the original capture's port-9050 traffic using the documented per-device Blowfish key
reveals that the three preceding queries return a `PDU` application entry, and frame 7762
requests `APP_NAME=PDU`, `COMMAND=START`, ending in the current management session id as a
little-endian u32 (matching the preceding `session_open` response). The response echoes the
command, and the diagnostic port accepted connections immediately afterward.

Live follow-up, native Python client: after a full MDI2 power cycle, the client opened the 13
management channels, opened a session (`master=false`), opened the 9011 channel, queried the PDU
entry, and sent the captured `PDU START` request with the fresh session id. Port 10123 opened
and stayed open after the management session closed. The D-PDU client then opened its command and
event sockets and obtained a channel id. A resource-0x2A link to radio ECU 0x80 (request
`14DA80F1`, response `145AF180`) then produced a successful `22 F1 A0` read-only transmit
confirmation and ECU response `62 F1 A0 F2`; this validates native Python CAN transmit/receive
for this read, but does not validate the ADB routine or identify its domain byte.

This is reconstructed field-by-field in the live native client (`tools/mdi2_client/mdi2/`,
`live_calibration.rearm_dpdu_tunnel`): `session_open` on 9052 (`master=True`) returns
`{"session": <id>, "port": 9011}`; then on **9050** send three polls (`2e08000001000000`) and
the START message (`30080000…APP_NAME…PDU…COMMAND…START` + session id as trailing LE u32). This
reliably reopens TCP/10123. **Correction: `PDU START` lives on port 9050, not 9011** (§11.1's
step 3 handshake on 9011 is a separate, unrelated exchange).

This identifies a strong startup candidate, but does not prove that this command alone starts
the service. Replaying the old ciphertext also reuses the old session ID, so identical replies
do not establish that the request was authorized or took effect — a new request must use the
current session ID and key.

### 11.4 Session-table exhaustion, not device state corruption or a WiFi credential (resolved 2026-11-14)

§11.1's byte-perfect replay still left 10123 refused. At the time, the leading hypothesis was
that the device's internal state machine had been desynced by this session's earlier
partial/malformed replay attempts, recoverable only by a physical USB power-cycle. **That
explanation is superseded.** The actual mechanism, confirmed 2026-11-14: port 10123 (and the
9052/9050/9011/9009 management handshake) is non-idempotent and fragile — one malformed D-PDU
frame can close 10123 without self-rearming, and repeated reconnection attempts **exhaust the
device's session table** (9052 stops answering its control frame — normally silent until the
client sends it — and `session_open` returns no session id). The table does not drain on idle
(75 s tested); a USB power-cycle clears it only because it restarts the device, not because the
device was "wedged." **Releasing sessions (`session_close`) or letting the table drain is the
correct fix; power-cycling is a last resort, not the first one.**

After a power-cycle + `rearm_dpdu_tunnel`, full function returns. Operational note: after a USB
replug, macOS re-assigns `en17` a /32, so `sudo ifconfig en17 inet 192.168.171.30 netmask
255.255.255.0` is required before the device is reachable again (discovery keys off the subnet,
not the interface name).

A repeated bench sequence makes the pattern concrete: `10 03`→`50 03`, `27 01`/`27 02` (all-FF
seed, 12-byte zero key)→`67 02`, then `11 01` (hard reset) sometimes returned `51 01` (accepted)
and sometimes `7F 11 22` (conditions not correct) on consecutive attempts with a fresh `PDU
START` each time, including once after an engine-off/accessory-on setup, and once with the
engine off and ignition on for the `22 F1 A0` resource-0x2A validation read in §11.3 above. A
separate soft-reset attempt, `11 03`, returned `7F 11 12` (subfunction not supported); this was
repeated after the ADB routine-domain tests specifically, and the radio was observed turning off
immediately afterward — reboot completion was not verified, and the test did not include any
calibration write or programming routine. Vehicle power mode was not independently measured for
any of these attempts, so this establishes only that the sequence *can* succeed on this unit in
this observed state — not that SecurityAccess was the sole missing precondition on all units, nor
that repeating `PDU START` itself caused acceptance, nor that accessory-off is required. (The
separate SPS `Power Mode Control Off` Type 4 application establishes that such a workflow exists,
not that SPS used it here.) The SPS calibration capture independently shows `11 01` followed by
`51 01` (event frame 29532) after security access and programming operations — not a
standalone-reset capture.

**Clarifying note (2026-11-21):** the "all-FF seed, 12-byte zero key" exchange in this bench
sequence is the **degenerate bypass-state seed** — a real, directly observed live-bench result,
also documented in `diagnostics/diagnosticsd_security_access.md` (level-1 seed/key exchange:
`27 01` → `67 01` + 31 bytes of `0xFF`, then `27 02` + 12 zero bytes → `67 02`). It is **not**
the same seed as the non-degenerate, per-request ECUID+challenge seed discussed in §6.3, whose
disputed total length (31 vs 32 bytes, tracked in Open Conflicts #1) is a separate, still-open
question about the non-degenerate seed. §6.3's "misread" note refers only to that non-degenerate
seed and does not apply to, or call into question, the all-`0xFF` bypass result reported here.

### 11.5 Local loopback Manager IPC (127.0.0.1:8125) — ident service and the WiFi-credential finding

While investigating a frame gap (7516-7730) in §11.1's capture, this pcapng turned out to also
contain merged USB-level frames (Wireshark multi-adapter capture) revealing a second, unrelated
service: **TCP port 8125 on `127.0.0.1`** (loopback, tablet-local, not device traffic) — a local
IPC/RPC service exposed by the Windows MDI2 Manager background process, that DPS/SPS talk to
*while* the device-side low-port dance (§11.1) is still in progress. Per §10.8 this port is
`8097 + ProductGroupId`; for this bench (`ProductGroupId=28`) that's 8125. Decoded frames (format
`[u32 total_len][u32 opcode][...payload]`, opcodes pair as request N / response N+1 or N+3):

- `0x7f2`→`0x7f5`: client sends hostname + a sequence id; server responds "Identification
  Service" + three IPs: `192.168.171.30` (tablet), `192.168.171.2` (this MDI2), and a
  previously-unseen third IP `192.168.177.2` (different subnet — a second adapter/MDI unit or a
  diagnostic bridge, unexplored).
- `0x8bf`→`0x8c0`: capability/count query → responds `count=1`.
- `0x8d1`→`0x8d2` (capture frame 7650): client sends a string `"BSH:<SERIAL>:28:9.1.2752.177:08"`
  (Bosch format: serial = this unit's own serial, confirmed matching `GM VCIHistory
  ...-D<SERIAL>.txt`; `module_type=28`; firmware `9.1.2752.177`), followed by a 28-byte
  credential, hex-encoded as ASCII: **`<REDACTED_WIFI_PASSPHRASE>`**. Server responds with a bare
  status value (`3`).
- Two ~16.7KB responses list installed driver/module info per adapter
  (`ax9u_dlink_drivers-kernel_modules`, `ax9u_dlink_drivers-tools`, versions `0.1.2735.5` /
  `3.0.14`, serial-like `370A0A00`) — `ax9u_dlink` appears to be a gadget-side internal driver
  codename.

**What the 28-byte value actually is (resolved 2026-08-25):** owned by
`MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` (MML) §2, which traces it end-to-end in Ghidra
pseudocode (`gm_mdi_ident.exe`'s `CClientConnectionMgr::OnDataReceived` `0x8d1` branch /
`SID_WIFI_CREDENTIALS_SEND` / `CWifiCredentials_Send` / `CIdentWifi::SetWifiCredentials` /
`bvtx_vci_rt_j.dll` `CDeviceMgr::SetConfigItems`) to the conclusion that the 28-byte value is
the VCI's own WiFi access-point WPA passphrase, unrelated to TCP/10123 authorization. See MML
§2 for the full derivation. Details from this doc's own capture that MML §2 does not state
(MML §2 already states that the passphrase is only format-validated, never generated or looked
up from a registry/DPAPI/backend store): the `"SN:module:fw"` string (the
`BSH:<SERIAL>:28:<fw>:08` form captured in this doc) is the VCI's own WiFi SSID and the 28-byte
hex value is its WPA passphrase; the lengths accepted by that validation (`ifm::ValidateWifiConfig`) are hex 26/10 chars = WEP,
8-64 chars = WPA-PSK; and, as an inference from the format-only validation, the value is not
derivable from the network capture alone — a different reason than first suspected.

**This rules out** the original working theory (that this credential gates TCP/10123). With it
ruled out, and content/timing/source-IP/TCP-options/L2-MAC-identity/device-freshness all also
ruled out by direct live testing (2026-08-25), **the actual answer is §11.4's session-table
exhaustion** — the 10123 refusals in §11.1/§11.3 were not a missing credential or desynced device
state, they were a management-plane resource leak from repeated partial/malformed connection
attempts during the same debugging session.

> History: an earlier draft of this section led with "MAJOR FINDING... likely the actual
> blocker" around the credential theory above, and proposed next targeting the vehicle's raw-
> DoIP gateway (`192.168.171.70:13400`) instead of continuing to chase the 10123 unlock. Both the
> credential theory and that next step are superseded: the credential is a WiFi passphrase
> (above), and the live-validated bench (2026-11-14) runs the MDI2 over direct USB RNDIS with no
> vehicle DoIP gateway reachable at all — vehicle/OBD2 wording elsewhere in this doc describes
> the original capture environment, not the current bench. The `.70:13400` DoIP-responder-
> topology question itself remains open; it is `AUG24_SESSION_FULL_PCAP_TIMELINE.md`'s open item
> (finding #1), not this doc's.

### 11.6 Native in-package live client — further findings (2026-11-07, `tools/mdi2_client/mdi2/`)

Established on this bench's MDI2 (serial-derived Blowfish key, radio ECU 0x80, tester byte F1),
beyond the `PDU START` mechanism in §11.3:

- **Resource-0x2A bring-up + a radio read round-trips live.** A full bring-up (CreateCLL 0x2A,
  GetComParam×4, 174-byte SetUniqueRespIdTable for 0x80, SetComParam set, Connect, persistent-RX
  StartComPrimitive, STARTCOMM, UPDATEPARAM) followed by `22 F190` returned the real VIN
  (`62 F190` + 17 ASCII bytes) on the persistent RX cop (cop 1), event type 1, preceded by a
  `mid 1505` length indication — validating the correlation design against hardware. TX confirms
  are event type 2; the strict `parse_radio_rx` allow-filter + skip-None discipline classifies
  them correctly.
- **Corrected: malformed one-shot framing, not a proven power-mode gate.** `build_one_shot()`
  already returns the complete D-PDU frame, but the live sender had been wrapping it in another
  length/message header. That is now corrected, with a regression against the captured
  stream-317 seed request. ComParam `0x19` and UPDATEPARAM trailers also now match the capture
  (`0x22` and a 25-byte trailer, respectively). Previous `0x2830` adapter rejections do not
  establish ECU power mode or resource-lock state; no ECU response was obtained from those
  malformed sends. The calibration workflow checks BCM F085 directly for the observed OFF value
  `00`. The data-wipe Service Mode prerequisite must not be generalized to calibration.
- **CLL resource hygiene.** `LiveDpduSession.close` destroys its CLLs; partial link construction
  now closes the session too. Cleanup remains necessary, but the malformed-send rejection does
  not independently demonstrate a leaked CLL or identify a resource-lock status.
- **Not yet done:** the single live LTZ **write**. The corrected transport requires live
  revalidation; an open diagnostic port alone does not establish radio communication. The
  source-profile gate now accepts the documented High Country baseline as well as LTZ, while the
  target still requires all fourteen pinned, unchanged LTZ containers. Reset, reconnect, identity,
  BCM OFF and post-reset voltage checks precede any programming.

---

## Open Conflicts

1. **SecurityAccess seed length, 31 vs 32 bytes.** §6 explicitly leaves this unresolved on its
   own evidence: a 32-byte reading (16-byte ECUID `004B41DC…14AC` + 16-byte random, from a live
   capture) vs a 31-byte reading (16-byte ECUID `002642250000160006104145610114AC` + 15-byte
   random, from an independently and programmatically re-parsed capture,
   `module_dumps/10017909_canbus_reset/A11_sps_datareset_log.Txt`, a different physical unit).
   SecurityAccess seed length is an ECU firmware property, not per-unit-variable, so the two
   captures should agree and currently don't; the 32-byte capture's raw bytes were never
   re-verified by script (only by eye). `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK) states
   31 bytes (16B ECUID + 15B challenge) as settled, drawing on its own capture set — but this
   doc's reader could not confirm that GSK's number closes this doc's specific 32-byte outlier,
   since the two docs' disputed figures trace to different capture sets. Carried here (per
   PLAN.md Open Conflicts item 6) in addition to GSK's own Open Conflicts section, rather than
   treating GSK's settlement as automatically resolving this doc's unresolved reading.

---

## Related

- `AUG24_SESSION_FULL_PCAP_TIMELINE.md` (APT) — the 6-pcap Aug-24 session this doc's raw captures
  come from; owns the DoIP-responder-topology open item (its finding #1) and the full
  radio-calibration-flash wire sequence.
- `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (GSK) — canonical seed-key/SecurityAccess/
  calibration-signature doc; owns the settled SHA-256 handler framing and key-derivation status.
- `MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` (MML) — the separate MDI2 Manager stack (GM_MDI_Ident.exe,
  14-port bank, Blowfish-ECB session JSON, log-file pull), now live-validated end to end.
- `MDI2_RAW_UDS_BYPASS_GUIDE.md` — carried unchanged; raw UDS bypass technique via MDI2.
- `eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` (outside this tree) — full RH850 `$27` handler
  disassembly writeup.
