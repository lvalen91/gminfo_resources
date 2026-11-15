# diagnosticsd — DID/DTC Read Sweeps

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

---

## RH850 UART correlation with direct T1 DID reads (2026-11-14)

The owner attached an external UART adapter to the confirmed-output VIP TX
connection, reported as RH850 physical pin 52 (P1_9 / RLIN34TX), and retained
an existing `screen` logger in another terminal. The adapter/probe location
is owner-reported; the following console events and request correlations were
observed live. See the [hardware pinout](../hardware/teardown.md#rh850f1k-package--uart-pinout).
The analysis read only newly appended portions of the owner's existing capture;
it did not open/reconfigure the serial adapter or transmit on UART.

USB ADB was available after the power cycle. Android was 6008 seconds behind
the Mac; the clock and timezone were explicitly set from the Mac and the
post-sync discrepancy was zero seconds. TCP ADB was restored on an unused
firewall-allowed port and independently verified through T1. That remained
a UID-2000 shell, separate from the diagnostic daemon and VIP.

The correlation test used the corrected F4/0x0084 custom-TCP framing on the
T1 VLAN 4 diagnostic interface. Each DID was read separately, allowing about
11 seconds for the existing `screen` logger to flush before the next request.
No session transition, SecurityAccess, routine or ECU-reset request was used
in this read-only correlation test.

| Window / request | T1 result | Newly appended UART observation |
|---|---|---|
| Quiet baseline, about 11 seconds | No diagnostic request | No selected diagnostic event in two appended lines |
| `22 F1 81` | `62 F1 81` plus 15 data bytes, about 28 ms | No newly appended UART bytes in the observation window |
| `22 F1 A0` | Pending response followed by `62 F1 A0` plus one data byte, about 209 ms | J6_CDD reported internal `SID=0x9`, `ISID=0x0`, item `0xF1A0` |
| `22 F0 F3` | `62 F0 F3` plus 16 data bytes, about 68 ms | J6_CDD reported internal `SID=0x9`, `ISID=0x0`, item `0xF0F3` |

Returned data, identifiers and ProtoKey values are deliberately omitted.
The controlled timing and matching item IDs provide live correlation between
these **external T1 DID requests and RH850/VIP processing**. The console's
`SID=0x9` belongs to its internal API/IPC naming; do not equate it with wire
UDS SID 09 or with a similarly numbered native enum. The actual wire requests
used UDS service 22. F181 is consistent with local handling, but absence of a
UART line alone is not proof of an exclusively local path or a complete log.

The earlier broad claim that no direct-T1 request had been shown reaching the
VIP must now be narrowed: F1A0/F0F3 have this correlation. It does not trace
the intermediate GHS route, identify the SecurityAccess key-compare backend,
or establish that ECUReset, routines, programming or all other DIDs use the
same path. No externally reachable GHS endpoint was established by this test.

Startup output included CSM_Startup, `evPowerModeOn`, InfotainmentPN activation,
AnimationInit/HmiInit/Propulsion state transitions, and SoC power-level 1–4
IPC notifications. This shows the VIP-observed startup sequence; it does not
by itself identify the bench harness MCU's originating CAN frame or sender.
The bracketed console counter supplies event ordering; its units and an exact
Mac/Android epoch alignment were not independently calibrated.

Observed VIP RTC messages still carried a 2024 calendar date after Android's
wall clock was corrected to the Mac. Treat the Android wall clock and this
VIP RTC feed as separate observations; a successful Android set-time is not
proof that the VIP RTC was corrected or evidence of its source. Use ordered
request windows and counter values when correlating the console. The final
Android check still matched the Mac within zero seconds. The temporary
host diagnostic VLAN interface was removed while T1 ADB remained configured.

## Bounded read-only sweep and UART reset follow-up (2026-11-14)

The expanded live Y175 test covered 41 unique DIDs from the existing generic
catalog, native handler cases and explicit session/security-table entries.
It also tested 18 DTC-report subfunctions, two scaling identifiers, two timing
read selectors, a one-byte memory read and two file-service read modes. This
is a bounded known-identifier inventory, not every possible 16-bit DID,
address, file path, security level or UDS variant. Payload values containing
identifiers, tickets, MACs or other private data were omitted from retained
results; positive response status and byte counts were recorded.

### What was read, and from which component

DIDs are **logical diagnostic records**, not raw address-space reads. The TCP
endpoint is Android diagnosticsd. Native handlers serve some records locally;
other requests are bridged to another component. A locally served record can
still describe software installed on the VIP or GHS, so the subject of a
record must not be confused with the component that produced the response.

- Native DID5735 reads startup-time/startup-type listeners; DID573D reads a
  boot-time listener. Their live responses were 32 data bytes each.
- F180/F181/F182 return structured part/version or calibration-identification
  records. The fresh readout below contains real build metadata rather than
  an empty acknowledgment; it is not a flash or RAM dump.
- F1A0 and F0F3 have the isolated request/UART correlations described above,
  establishing VIP/RH850 participation for those reads. Other routes are not
  assumed to be identical merely because they use service 22.
- The memory and file probes returned **no memory byte and no file/directory
  content**. No raw AAOS, GHS or RH850 memory region was successfully read,
  and the component/address-space meaning of the memory request remains
  unestablished.

Non-sensitive readout reproduced after the sweep:

| DID | Returned structure / example |
|---|---|
| F180 | Two records: tag 47, part 85056831, version bytes 41 41; tag 48, part 85098661, version bytes 41 42 |
| F181 | Two records: tag 01, part 85759599, version bytes 43 4A; tag 15, part 85098662, version bytes 42 4D |
| F182 | 197 data bytes; leading count 28 and length consistent with 28 seven-byte records |
| F1A0 | One byte, FF (255), in the live VIP-correlated state read |

The F180/F181 records have a count byte and seven-byte entries comprising a
one-byte tag, four-byte big-endian part number and two version bytes. This
record view does not establish an address in the component described by a tag.

### DID results

**22 of 41 unique DIDs returned positive data** in at least one tested state.
All entries below except F0A7 succeeded in the default session. F0A7 required
the later validated security-level 09 or 0B state.

| DID(s) | Data bytes per positive response |
|---|---:|
| 5735, 573D | 32 |
| F081 | 6 |
| F084 | 14 |
| F0B4, F0F3 | 16 |
| F0F0 | 28 |
| F0F1, F0F2, F0FB | 2 |
| F180, F181 | 15 |
| F182 | 197 |
| F190 | 17; contents omitted |
| F198 | 10 |
| F199, F1CB, F1CC | 4 |
| F1A0, F1B0, F0A7 | 1 |
| F1E4 | 39 |

The remaining 19 unique DIDs gave:

- `7F 22 11`: F09A, F0F4, F1DB, F1DC.
- `7F 22 31`: F0AB, F0B3, F183, F186, F187, F188, F18A, F18C, F191,
  F192, F193, F194, F195, F197, F19D.

The 17 rejected entries from the initial catalog sweep were repeated after
level-1 SecurityAccess and remained rejected. F0A7 was separately discovered
in the static tables: default session gave `7F 22 7F`; higher-level grants
09/0B then produced `62 F0 A7` plus one byte. A negative result belongs to the
requested DID and tested state; it does not deny all reads or all other routes.

### DTC, scaling and timing reads

All 18 tested service-19 subfunctions returned positive responses: 01, 02,
03, 05, 07, 08, 0A, 0B, 0C, 0D, 0E, 0F, 11, 12, 13, 14, 15 and 16.
Explicit authenticated repeats of `19 01 FF` and `19 02 FF` reported a count
of zero and no DTC records respectively. This is the diagnostic view returned
by this endpoint; it does not prove that every VIP fault or log entry is absent.
No DTC clear, DTC-setting control or communication-control request was sent.

**Static interpretation refinement, 2026-11-14:**
`DTCRequestToResponsePipeline::processDtcReadMessage` at `0x2bb60` constructs
positive responses with zero-filled buffers selected by subfunction. Its
recovered path contains no DTC-store/PAL/backend read. For example, the switch
at `0x14acc` selects four zero payload bytes for 01 and one for 02; many other
selectors select an empty payload. Thus a positive 59 reply, or a returned
zero count, is not sufficient proof of a functioning fault-store query.
Correlating the live request with this particular handler remains necessary;
the static finding does not prove that every other DTC route uses the stub.

`24 F1 81` and `24 57 35` gave `7F 24 7F` in default session and `7F 24 11`
after extended session plus level-1 SecurityAccess. Timing reads `83 01` and
`83 03` gave `7F 83 11` in both tested contexts.

DTC-number-specific queries were not fabricated when the returned DTC list
was empty. Periodic-read setup, unknown-memory uploads and routine-result
requests with unverified side effects were not treated as one-shot read-only
queries; notably RID0249 results attempts to clear overrides.

### Memory access and additional security levels

The bounded memory request was `23 14 00 00 00 00 01`: one byte at logical
address zero, with four address bytes and one size byte. No component's
address space was assumed from the address alone.

| Context | Final result |
|---|---|
| Extended session plus level 01 grant | `7F 23 33` (securityAccessDenied), immediate |
| Extended session plus level 09 grant | Six `7F 23 78` replies, then `7F 23 25` at about 30 s |
| Extended session plus level 0B grant | Six `7F 23 78` replies, then `7F 23 25` at about 30 s |

The Y181B/Y175-matching native code explains this distinction. The map
initializer at `0x4a550` loads level/index pairs from `0x15174`: level 09 maps
to index 4, level 0B to index 5. The service-23 row in the security table at
`0x151d0` permits only those two indices; its session row at `0x154d0` permits
extended session. `checkSecurityLevelTable` at `0x49f80` constructs NRC 33 when
an applicable row denies the active index. This is permission-table evidence,
not proof that the downstream memory reader is operational.

Both `27 09 -> 67 09 + FF x31` and `27 0B -> 67 0B + FF x31` were followed
by the same documented 12-zero-byte response and accepted with `67 0A` and
`67 0C` respectively. No arbitrary key or real/non-degenerate seed calculation
was tested. The protected F0A7 DID also became readable after either grant.
Memory still ended in noResponseFromSubnetComponent (NRC 25), so passing the
security gate did not yield a successful memory read. Default session was
positively restored afterward.

### File/directory service probes

With extended session and the validated level-1 grant:

- ReadDir `/`: `38 05 00 01 2F` returned `7F 38 11`.
- ReadFile `/proc/version`, no compression/encryption: mode 04, two-byte path
  length, path bytes and DFI 00 returned `7F 38 11`.

No AddFile, DeleteFile or ReplaceFile mode was sent. Both read negotiations
failed before any transfer, so no file contents, directory entries,
TransferData or RequestTransferExit operation resulted from these probes.
Service 38 is a distinct file-transfer negotiation; the calibration path
using 34/36/37 does not establish a working service-38 filesystem interface.
The tested pathname is not proof of the namespace a successful server would
expose, nor does the failure establish support under every possible context.

### ECUReset with the RH850 UART attached

A fresh, separately bounded UART window repeated the validated F4 extended
session and level-1 grant, then `11 01`. It returned six pending replies and
final **`7F 11 25` at 29.991 seconds**, again without `51 01` or an observed
Android reboot. USB ADB boot-ID checks remained unchanged and uptime increased
from about 1105 to 1157 seconds. Default restoration returned `50 01`.

The preceding approximately 11-second quiet UART baseline appended zero bytes.
The reset window plus the subsequent logger-flush allowance appended 314 bytes,
but no matching SID/item-number, reset/reboot or selected power-state event.
Other UART output existed; neither an inactive logger nor a demonstrated
RH850 reset follows from this result. Absence of a selected console event
also does not prove the request never reached the VIP, because log coverage
is not established as complete. The final T1 response is NRC 25; the later
[concurrent-logcat correction](diagnosticsd_protocol.md#concurrent-uart-and-usb-logcat-correlation-2026-11-14)
locates an unknown-service conversion inside AAOS, so the earlier inference
of a received-but-unanswered downstream request is not established.

The radio remained operational after the read sweep and memory probes;
Android uptime was still increasing and diagnosticsd was running. Temporary
host diagnostic VLAN configuration was removed, leaving the established T1
ADB configuration in place. No calibration write or firmware transfer was sent.

## Exhaustive DID-number sweep and extended enumeration (2026-11-14)

A serialized service-22 sweep tested **every 16-bit DID, 0000 through FFFF**,
once in extended session with the validated security-level-09 grant, using
the accepted tester/ECU pair over the existing custom T1 transport. Wi-Fi
and USB RNDIS were not scanned. USB ADB supplied clock checks and concurrent
logcat observation; the existing screen UART file was monitored by append
offset without opening or reconfiguring the serial port. Radio/Mac clock
drift was approximately two seconds. UART file timestamps confirmed ongoing
capture. **Observer correction:** the original literal SID= counter missed
UART lines formatted as SID = with spaces. Its zero SID count does not establish
absence of diagnostic traffic. The later whitespace-tolerant observer detected
VIP diagnostic events; no component-ownership inference should use the earlier
zero count.

The full range completed in **1501.26 seconds**:

| Final response category | DID count |
|---|---:|
| Positive 62, with matching DID | 135 |
| NRC 31 / requestOutOfRange | 65376 |
| NRC 22 / conditionsNotCorrect | 21 |
| NRC 11 / serviceNotSupported | 4 |
| Transport errors or unmatched response shapes | 0 |

Five responsePending frames occurred across the sweep and were consumed before
the matching final replies. Requests were serialized; normal TesterPresent
was verified every 256 DIDs. Default session was positively restored, and
Android boot identity was unchanged. No raw response values, identifying data,
new packet captures or logcat files were saved.

This expands the earlier 22-positive catalog by **113 newly verified readable
DIDs**. The table below is the complete positive catalog for this particular
session/security state; counts exclude the response SID and two-byte DID.
Values and their interpretation remain separate work. A negative reply is
specific to the tested state and does not establish absence on every route.
The largest returned data field was 3960 bytes for 4FF0.

| DID prefix | Positive DID = data-byte count |
|---|---|
| 41xx | 41D8=1, 41DA=1, 41DB=1, 41DE=1, 41E2=1, 41E4=1, 41E7=1, 41E9=1, 41EA=1, 41EB=1, 41EC=1, 41EF=1, 41F5=190 |
| 42xx | 42AA=2, 42AB=2, 42AC=2, 42AD=1, 42B1=1, 42B2=1, 42B3=60, 42B4=8, 42B5=80, 42B6=4, 42B8=8, 42BA=6, 42BB=1, 42BC=2, 42BD=1, 42BF=1, 42C0=1, 42C1=1, 42C2=1, 42C3=1, 42C4=1, 42C5=1 |
| 43xx | 4394=113, 4395=113, 4396=1, 4398=1, 43A1=1, 43A5=24, 43A8=1, 43AA=1, 43AC=2, 43BB=1, 43FC=1 |
| 44xx | 440A=1, 440B=1, 440C=1, 4424=2, 4426=2, 4478=1, 447A=102 |
| 46xx | 4609=16 |
| 47xx | 4774=1, 4776=56, 4781=1, 4785=1, 478B=8, 4791=2 |
| 48xx | 489F=2, 48A0=1, 48A1=3 |
| 4Exx | 4EA8=2 |
| 4Fxx | 4F8E=75, 4F8F=75, 4FE2=1, 4FE3=1, 4FE4=1, 4FE5=1, 4FE6=10, 4FE7=6, 4FE8=1, 4FF0=3960, 4FFA=36, 4FFB=2 |
| 51xx | 5152=8, 5171=12 |
| 57xx | 572E=2, 5730=32, 5731=32, 5732=32, 5735=32, 5738=32, 573A=1, 573B=4, 573C=32, 573D=32, 573E=32 |
| 58xx | 5812=1, 5813=2, 5814=1, 5815=5 |
| 5Fxx | 5FA7=75, 5FA8=75, 5FA9=75, 5FAA=75, 5FAB=75, 5FAC=75, 5FAD=75, 5FAE=75 |
| C0xx | C002=2, C003=2, C004=6, C005=6, C006=1, C007=12, C008=6, C009=6, C00E=16, C00F=3 |
| F0xx | F081=6, F084=14, F08C=1, F0A7=1, F0B4=16, F0F0=28, F0F1=2, F0F2=2, F0F3=16, F0F6=24, F0FA=99, F0FB=2 |
| F1xx | F180=15, F181=15, F182=197, F190=17, F198=10, F199=4, F1A0=1, F1B0=1, F1CB=4, F1CC=4, F1DE=7, F1E4=39 |

This is exhaustive for the **DID-number space in one tested state**, not for
all UDS payloads, routines, sessions, ECU targets or backend namespaces.
SID conversion, session/security permission rows, native factories and the
live [Java handler inventory](diagnosticsd_protocol.md#java-handler-inventory-verified-against-the-live-apk-2026-11-14)
provide complementary coverage. No blind
SID-only or routine-start sweep was substituted for valid request formats.
Calibration erasure, DTC clearing, programming transfers and arbitrary writes
were not performed.

### Cross-state and service-variant verification

The retained supplementary pass rechecked 159 static/live candidate DIDs in
default session and after each successful tested grant. These checks enumerate
the known candidate set across states; the entire 65536-number range was
exhaustively swept only at level 09.

| Tested context | Positive DIDs among 159 candidates | Missing versus full level-09 positives |
|---|---:|---|
| default | 134 | F0A7 |
| level 01 | 134 | F0A7 |
| level 03 | 134 | F0A7 |
| level 09 | 135 | None |
| level 0B | 135 | None |
| level 0D | 135 | None |
| level 11 | 134 | F0A7 |
| level 05 | 134 | F0A7 |
| level 13 | 134 | F0A7 |
| level 15 | 134 | F0A7 |

The documented 31-FF-byte seed / 12-zero-byte response form produced grants
for levels **01, 03, 05, 09, 0B, 0D, 11, 13 and 15**. Seed selector **5F**
ended in **7F 27 25**; no key was submitted for that failure. No non-degenerate
seed/key derivation was performed. F0A7 was the only newly accessible DID in
this cross-state comparison: it succeeded at 09/0B/0D, gave NRC 7F in default
session and NRC 33 at the other granted levels.

A targeted replay of DID numbers 0000–07FF identified the two early-range
NRC-22 exceptions as **22 02 49** and **22 04 75**. These are DID requests;
their numeric overlap with native RID IDs is not proof that routines were
started or completed. Exact dispatch accounting for those two replies remains
to be traced.

| Additional request | Retained live result |
|---|---|
| 10 00, 10 04, 10 7F | 7F 10 12 / subFunctionNotSupported |
| 10 02 after extended session and level-01 grant | 7F 10 22 / conditionsNotCorrect; no programming transfer followed |
| 31 03 03 D8, extended / level 09 | 7F 31 22 / conditionsNotCorrect; no positive routine execution established |
| 3E 80 | No frame observed within 0.5 s |
| Following 3E 00 | 7E 00; normal keepalive still worked |
| Final 10 01 | Positive default-session restoration |

**DTC response-shape verification:** all 128 selectors 00–7F returned a 59
positive response echoing the selector, including reserved/unspecified selectors.
Known selectors received appropriate request fields where available; reserved
selectors and those without an established request format were header-only
probes. This was not a valid-format proof for every selector. The returned
data lengths below match the native zero-filling switch recovered statically:

| Selector(s), hex | Data bytes after 59 + selector |
|---|---:|
| 01, 04, 06, 07, 10, 11, 12, 42 | 4, all zero |
| 02, 05, 08, 09, 0A, 0B, 0C, 0D, 0E, 0F, 13, 15, 16 | 1, zero |
| 17 | 2, all zero |
| 18, 19 | 5, all zero |
| 55 | 3, all zero |
| All other tested selectors, including 00 and many reserved values | 0 |

Consequently these positives do not establish 128 implemented DTC operations
or a queried/empty real fault store. The matching static stub and indiscriminate
live positive shapes support that limitation much more strongly than positive
SID classification alone. Default session was restored after verification;
the USB observer was stopped and the owner's UART logger left running.

### Read-only calibration identity comparison with the supplied archive

A final default-session F182 read returned 28 seven-byte part-number records.
Native F182 code at 0x2a660 obtains calibration DLS/part numbers through
GMCalibrationManager.getModuleIDDLS / getModuleIDPartNumber and includes them
in the response. Comparing record tags with the supplied update-cache DB's
ModuleData.ModID found all 14 archive module IDs on the running radio: **13
part-number/DLS pairs matched; module 11 differed**. This is current selected
module-identity evidence, not a complete live CalSets.db dump or proof of
every applied row/file. It also demonstrates that the archive does not exactly
describe all current module identities. Default session was restored afterward.

The archive contains 982 nonzero OverRiden rows and records 14 applied .cmod
paths, but omits the actual .cmod files. It is not a complete recovery backup
for erasing overrides. This archive assessment preceded the later explicitly requested clear. See the
[owning calibration baseline](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12).
