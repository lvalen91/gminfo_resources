# diagnosticsd — Ethernet UDS-over-TCP Diagnostic Bridge (port 49156)

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026
**Binary:** `/vendor/bin/diagnosticsd` (x86-64 ELF, stripped, 426,824 bytes)
**SELinux:** `gm_diagnosticsd_exec:s0` → domain `gm_diagnosticsd`

This documents the **Ethernet** diagnostic channel: the root daemon
`diagnosticsd` listening on TCP `0.0.0.0:49156`, which bridges GM Ethernet
Diagnostics (UDS / ISO 14229) between the Android guest and the RTOS diagnostic
endpoint. This is distinct from the **CAN/DPS** diagnostic path captured in
[`diagnostics/dps/`](dps/) (ECU 0x80, DPS 4.56) and from the FSA service layer
([`platform/fsa_protocol.md`](../platform/fsa_protocol.md)). The `gm_diagnosticsd`
SELinux domain and its UDS SID list are summarized in
[`platform/security.md`](../platform/security.md#can--uds-diagnostic-services);
this doc adds the live Ethernet wire format and trust model.

**2026-10-30, Y175:** A shell running as UID 1000 in `system_app` connected to
the UID 0 listener on port 49156 without sending protocol data. This confirms
TCP reachability from that domain, not service identity on that connection,
request authorization, or calibration-write access.

Binary obtained by extracting `/bin/diagnosticsd` from vendor ext4 image
`86331650` (`debugfs -R 'dump ...'`); a live pull is blocked by SELinux from the
`adbd` context.

> **[C] live-Y175 2026-10-05 — listener existence/owner/bind CONFIRMED on the Y175 variant.**
> Disk-only capture of a running Y175 radio (`W213E-Y175.5.2-SIHM22B-383.1`,
> `/tmp/radio_audit/20261005_232227/raw/`): `diagnosticsd` is live — `init.svc.diagnosticsd=running`
> (props), process in ps as **PID 590, root, SELinux domain `gm_diagnosticsd`** (`ps.txt:132`;
> note PID differs from the Y181 PID 599 in the header below — PID is capture-specific). It is
> **LISTENing on `0.0.0.0:49156`** (net_sockets.txt TCP row `00000000:C004` with `st=0A`, `uid=0`,
> inode 13683; `0xC004`=49156) — bind address is INADDR_ANY/`0.0.0.0`, **not** loopback, same as
> documented. Owner uid 0 confirmed. **UNVERIFIABLE-FROM-LIVE (shell uid 2000, no CAN/Ethernet diag
> access):** everything below about the UDS wire format, the 0x27 SecurityAccess seed/key gate, the
> VIP-tier relay, the privilege tiers, and the worker-starvation DoS — none of it is re-exercised by
> this capture; only the listener's existence, root ownership, and `0.0.0.0` bind are confirmed.

---

## Process Profile

- PID 599, PPid 1 (init), 10 threads, Sleeping. UID=0 GID=0.
- Groups: 1000 (system), 2001 (adb), 3003 (inet), 3004 (net_admin).
- `CapPrm/CapEff/CapBnd = 0000003fffffffff` → **all capabilities**.
- `NoNewPrivs = 0`, `Seccomp = 0` (no filter). `SigIgn: SIGPIPE`.
- VmSize ~10.4 GB virtual, VmRSS 9.9 MB.
- Network: LISTEN `0.0.0.0:49156` (root TCP **server**). **[C corrected 2026-10-06]** `.107`/`.112`
  connect *inbound* to it (firewall `iptables_rules_file.txt:35-36`); the earlier "ESTABLISHED
  `.100↔.107` forwarding" line was **unsupported** — no such socket in any Y181/Y175 capture. See the
  concurrence-correction block below.

**RC file (from vendor image):**
```
service diagnosticsd /vendor/bin/diagnosticsd
    class hal core
    user root
    group root system cache inet net_raw
    shutdown critical
    #seclabel u:r:su:s0      ← COMMENTED OUT (was planned as su domain)
on property:debug.cts.port.off=1 && property:ro.product.system.brand=Android
    stop diagnosticsd
on property:debug.cts.port.off=2 && property:ro.product.system.brand=Android
    start diagnosticsd
```
`ro.product.system.brand` is `"gm"` (not `"Android"`) on production, so the CTS
port kill-switch can never fire — diagnosticsd runs as root continuously. (RC
comment: *"stop diagnosticsd for cts-on-gsi tcp port testcases"* — flagged by
Android CTS as a root TCP listener.)

---

## Wire Format — GM Ethernet Diagnostics (NOT DoIP)

The TCP stream uses an 8-byte big-endian header, followed by the declared
number of UDS bytes (including the service ID):

```
[SRC_ADDR : 2 BE] [TGT_ADDR : 2 BE] [PAYLOAD_LEN : 4 BE] [UDS payload]
```

- **Corrected 2026-11-14:** use tester `0x00F4`; `0x00F5` also passed the live
  basic-read/TesterPresent checks. The earlier `0x0FA0` example is an invalid
  tester control, not a valid Techline identity for this endpoint.
- ECU diagnostic address: `0x0084`. The inspected binary checks tester and
  target fields; earlier claims that target addresses are never validated
  were too broad. Use the canonical target instead of relying on normalization.
- `SockAdaptor::readHeader` byte-swaps the address words and separates the
  SID from the remaining payload. Do not add ISO-TP PCI or DoIP headers.
- Read an entire reply frame, then wait through `7F <SID> 78` until the final
  response matching the request SID. A pending reply is not the final result;
  advancing early can misattribute the next response to the wrong request.

## Live T1 SecurityAccess correction (2026-11-14)

**Live target:** Y175 `W213E-Y175.5.2-SIHM22B-383.1`, owner's isolated bench,
with SBI modification reported by the owner. **Static reference:** Y181B
`W231E-Y181.3.2-SIHM22B-499.3`, processed `os/vendor/bin/diagnosticsd`.
The builds differ; the Y181B binary has not been byte-matched to the live Y175
executable. Its address checks predicted the successful live correction.

The direct T1 client used a firewall-allowed VLAN 4 source identity and tester
`0x00F4`, target `0x0084`, on one TCP connection. No controlling Android app,
root shell, MDI2, or separately registered tester was needed for this exchange:

| Step | UDS request | Final response / observation |
|---|---|---|
| Software-identification read | `22 F1 81` | `62 F1 81 <software data>` |
| TesterPresent | `3E 00` | `7E 00` |
| Enter extended session | `10 03` | `50 03 00 64 01 F2` |
| Request level-1 seed | `27 01` | `67 01` + **31 bytes of `FF`** |
| Submit documented bypass response | `27 02` + **12 zero bytes** | **`67 02`** |
| Restore default session | `10 01` | `50 01 00 64 01 F2` |

Two successful extended-session/seed exchanges were performed; the second also
included the 12-zero-byte response. Both restored the default session. Basic
requests with tester `0x00F5` also returned positive software/TesterPresent
responses; its default-session `27 01` returned `7F 27 7F`
(`serviceNotSupportedInActiveSession`). `22 F1 86` returned `7F 22 31`, which
is a DID-specific rejection, not a blanket denial of diagnostic access.

**Why the earlier probes failed:** tester `0x0FA0` returned `7F <SID> 10`
for DID reads, TesterPresent and requestSeed. In the Y181B binary,
`UDSAddressCheckRequestHandler::handleUDSRequest` at `0x49350` accepts tester
low bytes `F4`/`F5`; its invalid-tester branch constructs NRC `0x10`. The
big-endian decoding is in `SockAdaptor::readHeader` at `0x46260`. Thus the old
all-rejected tests did not establish a missing app, SBI-inactive state, or a
universal SecurityAccess barrier. Changing TCP source IP alone did not fix the
incorrect logical tester address. Extended-session entry was also necessary
for the tested seed request.

**Scope:** `67 02` proves acceptance of this exact level-1 response. It does
not prove arbitrary-key acceptance, programming-session entry, calibration or
partition writes, relaxed signature verification, Android UID 0, or a GHS
shell. No download/transfer/routine/reset request was sent during that
SecurityAccess validation; the separate ECUReset follow-up is documented below. The Android
UpdateService dump reported `SBI=false`, `MEC=-1` despite the accepted
exchange; those application values are not an authoritative VIP-state reading.

The MDI2/CAN reference also uses a 31-byte all-FF seed and a 12-zero-byte
response. This supports shared UDS behavior; the custom TCP framing is not
MDI2 transport, CAN ISO-TP, or DoIP. Neither identical payloads nor overlapping
service names prove the complete OBD connector → gateway → A11 internal route
or the component performing the key comparison.

Separate reachability checks on both external T1 adapters received replies
from the Android guest on both tagged networks, but no ARP reply from the
historically documented GHS candidates. Targeted candidate connections did
not complete. This bounds external reachability under the tested switch
configuration; it does not show that GHS is absent or stopped. Temporary host
VLAN interfaces were removed; no packet-capture file was created.

---

## Live T1 ECUReset validation (2026-11-14)

A separate follow-up tested whether the direct T1 path can perform the radio
hard reset used by the MDI2 workflow. The same live Y175 bench target,
firewall-allowed VLAN 4 identity, logical tester F4 and ECU target 0x0084 were
used. Extended-session entry and the documented SecurityAccess exchange both
succeeded before sending `11 01`.

| Stage | Observed response |
|---|---|
| Extended session `10 03` | `50 03 00 64 01 F2` |
| Seed `27 01` | `67 01` plus 31 all-FF bytes |
| `27 02` plus 12 zero bytes | `67 02` |
| Hard reset `11 01`, while processing | Repeated `7F 11 78`, approximately every 5 seconds |
| Final hard-reset result | **`7F 11 25` at approximately 30 seconds** |
| Restore default session `10 01` | `50 01 00 64 01 F2` |

NRC `0x78` is responsePending, not an acceptance acknowledgment. NRC `0x25`
is noResponseFromSubnetComponent. No `51 01` positive reset reply was received.
The Android guest's boot ID remained unchanged and its uptime increased from
about 4806 to 5072 seconds across the setup and observations; diagnosticsd
remained running with the same PID. No Android reboot or completed radio hard
reset was demonstrated. VIP/GHS partition state was not independently observed,
so these checks do not exclude an unobserved partial-component effect.

The first attempt stopped waiting after 15 seconds of pending replies; an
immediate default-session request received `7F 10 21` (busyRepeatRequest).
After the channel again answered TesterPresent/default-session requests, one
repeat allowed up to 90 seconds and obtained the final `7F 11 25` at 30 seconds.
Thus the reported result is the final wire response, not the shorter client's
timeout. Default session was then positively restored and the temporary host
VLAN interface removed. No reset was substituted through ADB; ADB was used
only to observe boot identity, uptime, daemon state and existing logs. A later
UART-instrumented repeat is recorded in the bounded read-sweep section below.

**MDI2 comparison:** successful session/SecurityAccess traffic proves that
some UDS services work through the custom T1 transport. This reset result
neither proves that `0x11` is unsupported nor demonstrates a working reset or
a drop-in MDI2 replacement. The downstream component, forwarding route and
reason for its missing response remain unresolved. No programming transfer,
partition write, firmware replacement or UID-0 shell was attempted by this reset
test.

---

## Service IDs, variants and routine inventory (2026-11-14)

`10`, `27`, `22` and `31` are hexadecimal UDS **service identifiers** (SIDs),
not shell commands, TCP ports, interface-class numbers or routines themselves.
The bytes after a SID depend on that service. A DID identifies a data item;
a RID identifies a manufacturer-defined routine. Subfunctions, DIDs and RIDs
are different fields and must not be interchanged.

| Service | Meaning | Standard selector / request shape | Evidence on this T1 endpoint |
|---|---|---|---|
| `10` | DiagnosticSessionControl | `01` default, `02` programming, `03` extended, `04` safety-system diagnostic; OEM-specific sessions may exist | Default/extended accepted live; programming/04 not validated by these tests |
| `27` | SecurityAccess | Odd subfunction requests a seed; paired even subfunction submits its response, e.g. `01/02`, `03/04`, `05/06` | `01/02`, `09/0A` and `0B/0C` grants validated; access rights differ by level |
| `22` | ReadDataByIdentifier | No subfunction: `22 <DID high> <DID low>`; e.g. `22 F1 81` | F181 positive live; F186 gave DID-specific NRC `31` |
| `31` | RoutineControl | `01` start, `02` stop, `03` request results, followed by a two-byte RID and optional parameters | Local native handlers below are statically mapped; no routine executed in this inventory work |
| `3E` | TesterPresent | `00` keepalive; `80` is the suppress-positive-response form | `3E 00 -> 7E 00` live-validated |
| `11` | ECUReset | Common standard types: `01` hard, `02` key-off/on, `03` soft; other types exist | Hard-reset request ended in NRC `25`, not a demonstrated reboot |

For example, `31 01 <RID high> <RID low> [parameters]` means start that
routine. `22 F1 81` means read DID F181, not subfunction F1 of service 22.
A positive response normally uses SID + 0x40. `7F 22 31` is a negative reply
to service 22 with NRC 31 (requestOutOfRange); its trailing `31` does not
mean RoutineControl. The transport remains the custom GM eight-byte header.

The broader UDS standard also defines clear/read DTCs (`14`, `19`), communication
control (`28`), DID writes (`2E`), I/O control (`2F`), download/upload and transfer
(`34`, `35`, `36`, `37`), and DTC-setting control (`85`). Memory read (`23`) and
file/directory transfer (`38`) exist in the standard, but no working T1 memory
or file-export implementation was established here. These are protocol
families to map, not a claim that every service/subfunction works on this radio.
In particular, a string naming a service or a parser accepting its SID does
not prove a registered backend, permission grant, or successful completion.

Protocol references: [udsoncan services](https://udsoncan.readthedocs.io/en/latest/udsoncan/services.html),
[UDS introduction](https://udsoncan.readthedocs.io/en/latest/udsoncan/intro.html),
and [AUTOSAR DCM specification, RoutineControl](https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf).
These document the public protocol, not GM's complete A11 RID/DID definitions.

### Direct static evidence in Y175 and Y181B

Both processed trees contain `diagnosticsd` (426,824 bytes). Their whole-file
SHA-256 values differ:

- Y181B: `03aace3b71db09f98d88c9dcbf4319d24a4a82dac775f46a0181c7a08ad7b6e6`.
- Y175: `35dc4b32432a4d80e466dbaf2430530591884bcb3e59b97aad0e37dc2b8af1c0`.

Nevertheless `.text` (245,731 bytes), `.rodata` (24,777 bytes) and
`.data.rel.ro` (11,552 bytes) are byte-identical between these extracted
binaries. This supports the following cross-build code comparison. It is
still not a byte-match of the running radio executable or proof that all
runtime plugins/configuration match.

`generateRIDHandler(int)` at `0x2fb80` explicitly selects two local handlers:
`0x0249` and `0x0475`; other IDs return an empty handler from **this local
factory**. `RIDRequestToResponsePipeline::canHandleMessage` at `0x2faf0`
checks that result. This is not a complete radio/VIP/GHS routine list: other
pipelines or backend components may process requests not handled locally.

| RID | Direct code evidence | What is / is not established |
|---|---|---|
| `0249` | `RID0249Handler::handleResultsRoutine` at `0x2ad00` calls `CalibrationAccessor::clearAllOverrides()`; start at `0x2acc0` forwards via virtual slot `0x38` to that same results handler. Stop at `0x2ace0` constructs a positive response. | Local start/results path attempts to clear calibration overrides; failure maps to conditionsNotCorrect. **Request-results is not inherently read-only for this implementation.** Runtime T1 invocation was not attempted. This does not prove that every captured CAN/VIP invocation takes this Android handler. |
| `0475` | `RID0475Handler::handleRoutine` at `0x2ade0`; start/stop/results wrappers delegate through `CorePluginManager::getRegisteredInternalServiceManager()` and its callback. | An internal-service hook exists. The registered implementation, payload semantics and live T1 support are not yet mapped; do not invent a routine name. |

The RID0249 constructor at `0x2ac70` points to a vtable at `0x62910`; slot
`0x38` resolves to `0x2ad00`, corroborating the start-to-results forwarding.
No call to either routine was sent during this static analysis.

`generateDIDHandler(int)` at `0x2f5a0` contains dedicated cases for `5735`,
`573D`, `F081`, `F084`, `F180`, `F181`, `F182` and `F1B0`. This is a local
handler inventory, not a complete accessible-DID list. Unknown IDs can take
other dispatch paths, and finding a handler does not establish live access.

### Existing catalogs and captured routines

- [MDI2 static catalog](../mdi2_client/mdi2/data/did_map.json) contains generic
  DID metadata and four RIDs: `020E` wakeUpNetworks, `FF00` eraseMemory_alt,
  `FF01` checkProgrammingDependencies, and `FF02` eraseMemory. It spans ECU
  contexts; membership is not proof that A11 supports the item or that a name
  is the correct meaning on every ECU. For example, the captured `020E`
  network-wakeup request is addressed to the gateway, not to the radio.
- [CAN/DPS reference](dps/A11_CSM_x80.Txt) records actual diagnostic exchanges;
  [seed/key and signing analysis](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
  identifies radio `0249` before programming and `039B` during finalization.
  Their presence in a CAN/SPS sequence does not establish equivalent direct-T1
  routing or completion. Exact CAN/VIP-side semantics remain distinct from
  the local Android RID0249 code traced above.
- [MDI2 routine research](../research/MDI2_RAW_UDS_BYPASS_GUIDE.md#7-gm-adb-escape-hatch-via-31-routinecontrol-2026-09-10)
  describes candidate `0332` for ADB control, but its correct parameters,
  applicability and working T1 behavior are not established. The earlier
  invalid-tester rejection is not proof that this RID is absent.

A complete build-specific inventory requires tracing SID conversion,
address/session/security tables, the local DID/RID factories, registered
HIDL/Binder/Java callbacks, and any external VIP/GHS forwarding endpoint.
For each item record request format, subfunction/identifier, payload, caller
and security prerequisites, backend, effects, and evidence level (static,
captured CAN, or live T1). Firmware code can expose much of this mapping;
missing component firmware or runtime registration can leave gaps. There is
no verified universal UDS request that enumerates every OEM DID/RID.

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
is not established as complete. The final T1 response remains a downstream
no-response result with unresolved routing/backend cause.

The radio remained operational after the read sweep and memory probes;
Android uptime was still increasing and diagnosticsd was running. Temporary
host diagnostic VLAN configuration was removed, leaving the established T1
ADB configuration in place. No calibration write or firmware transfer was sent.

## Legacy/internal service labels (binary strings)

The following older labels mix GM/native and legacy service representations.
They are retained as code-search leads, **not** a definitive list of wire SIDs
accepted by the custom T1 endpoint. In particular, do not substitute a legacy
RID label such as `70` for UDS RoutineControl `31` without tracing conversion.


| SID | Service |
|-----|---------|
| 0x10 | `DIAG_SESSION_CONTROL` |
| 0x27 | `DIAG_SECURITY_ACCESS` |
| 0x1A/0x22 | `DIAG_DID_READ` |
| 0x3B/0x2E | `DIAG_DID_WRITE` |
| 0x28 | `DIAG_COMMUNICATION_CONTROL` |
| 0x35 | `DIAG_REQUEST_DATA_TRANSFER` |
| 0x36 | `DIAG_DATA_TRANSFER` |
| 0x70 | `DIAG_RID_CONTROL` |
| 0x76/0x37 | `MSG_RID` |
| 0x22 | `DIAG_PID_READ` |
| 0xAE/0x2F | `DIAG_CPID_CONTROL` |
| 0x20 | `DIAG_CPID_RETURN` |
| 0xD9 | `DIAG_INTERNAL_REQUEST` |
| 0x00/0x15 | `DIAG_CUSTOM` / `MSG_VENDOR_START` |
| various | `DIAG_DTC_*` |

(Use the wire-service/variant table above for UDS meanings; these legacy/native
labels are not independent evidence that every listed SID is enabled over T1.)

**Historical invalid-tester results, superseded 2026-11-14:** the following
requests used an invalid logical tester identity. They are retained as negative
controls, not evidence that all unprivileged clients are rejected. See the
[validated T1 sequence](#live-t1-securityaccess-correction-2026-11-14).

| SID | Service | Response |
|-----|---------|---------|
| 0x10 0x01/02/03 | DiagnosticSessionControl (default/programming/extended) | `7F 10 10` |
| 0x27 0x01 | SecurityAccess requestSeed | `7F 27 10` |
| 0x3E 0x00 | TesterPresent | `7F 3E 10` |
| 0x22 0xF1 0x81/86/8A/90 | ReadDID (sw / session / sw number / VIN) | `7F 22 10` |
| 0xD9 0x00 | DIAG_INTERNAL_REQUEST | `7F D9 10` |
| 0x00 0x01 | MSG_VENDOR_START | `7F 00 10` (service 0x00 dispatched) |

---

## Trust Model (binary-confirmed)

**Live socket access and UDS authorization are separate.** An unprivileged
client can connect to the daemon and, with the corrected logical tester ID
and session sequence above, obtain positive UDS responses and `67 02`. Root
ownership of the daemon does not give the client a root shell. Import-table
absence of credential functions alone is not proof that every authorization
check is absent.

The inspected application checks include:

1. **Logical source/target validation:** tester low byte `F4`/`F5` is accepted
   by `UDSAddressCheckRequestHandler`; the old `0x0FA0` fails here.
2. **Active tester/session checks:** `UDSSessionControlCheckHandler` at
   `0x4a7c0` compares tester IDs and evaluates a mismatched tester in the
   default session. This is not proof that only an RTOS client can establish
   a session. The live external client entered extended session successfully.
3. **Session and security level:** the successful order is `10 03`, `27 01`,
   `27 02` plus 12 zero bytes. Keep the exchange serialized on one connection
   and explicitly restore `10 01`; connection closure alone was not tested as
   a session-reset mechanism. The static service uses shared active-tester/
   session state, so do not describe it as proven purely per-connection state.

**Privilege tiers:** `VIP` > `ETHERNET` > `NOTIFICATION`, each unlocking more
UDS services; the tier is granted by the 0x27 SecurityAccess response after a
correct seed/key exchange. `checkSecurityLevelTable` (string, above) is **only
the per-tier allowed-service lookup table** — which SIDs a tier may call once
granted — **not** an SBI/seed-key gate itself.

**[D] CORRECTION (2026-09):** an earlier version of this doc guessed the
seed→key algorithm was "likely implemented in `/vendor/bin/gm_protokey`." This
is **wrong** — `gm_protokey` is the boot-time proto-key / disk-encryption
(`DATA_LOCKED`) state validator (`init.protokey.rc`, kernel-netlink `setKey`,
sets `vendor.gm.security.state`); it is unrelated to UDS SecurityAccess. See
[`platform/security.md`](../platform/security.md#protokey--adb-authentication)
for what `gm_protokey` actually does (ADB/seed-auth state, not `$27`).

**Backend-location limit:** the binary contains in-process `libuds` address,
session and allowed-security-level handlers. A handler/table name does not by
itself identify the component performing the seed/key comparison. Historical
`ProxyOfExtComp` symbol and direct RTOS-forwarding claims are disputed in the
concurrence correction below. The live level-1 all-FF/12-zero/`67 02` exchange
establishes the observable Ethernet behavior, not the exact VIP/SoC/GHS call
chain or a normal non-bypass seed-to-key algorithm.

---

## Oversized-Payload Behavior

| PAYLOAD_LEN | Behavior |
|------------|---------|
| `0x00000000` | **Only closes immediately if the client also half-closes (FIN/`shutdown(SHUT_WR)`)** after the header. A `nc`/`printf` pipe does this implicitly on EOF, which is what earlier testing observed. Holding the socket open past the 8-byte header with **no** half-close hangs indefinitely (confirmed ≥8 s) even for a declared length of 0. |
| `0x1000`–`0x40000000` (tested up to 1 GiB) | Connection is held open, blocking, waiting for the declared byte count or EOF. **No response, no rejection, no RST.** |
| `0x7FFFFFFF` / `0xFFFFFFFF` | Same blocking behavior — no response, connection held open. |
| Unsigned-wrap boundary values (`0xFFFFFFF0`–`0xFFFFFFFF`, targeting the `payload_size + 9` arithmetic in `sendResponse`) | Behave identically to any other nonzero declared length — connection blocks, no distinguishing response. The wraparound in `sendResponse`'s check could not be triggered from the wire; that check is not reached until a *response* is being built, which never happens because `readAvailableData()` never gets enough bytes. |

**`SockAdaptor::sendResponse`** allocates a **128 KB stack buffer**
(`sub rsp, 0x20008`) with a stack canary; the size check
(`"Payload size too large: %d"` when `payload_size + 9 ≥ 0x20001`) is unsigned
and relies on `getPayloadSize()` being pre-bounded by `EthernetConverter`
(`"Reported Payload Size is incorrect (Payload Size %d vs Data Payload Size %d)"`)
before `sendResponse`.

**Confirmed live (Jul 2026 session), black-box, no binary access required:**

- **No pre-allocation.** Declaring PAYLOAD_LEN up to 1 GiB and sending zero
  payload bytes produces **no measurable `VmRSS` growth** (`9524 kB` flat,
  `/proc/598/status`, before/during/after) across 3 simultaneous such
  connections. This **rules out** a `malloc(PAYLOAD_LEN)`-before-check
  memory-exhaustion primitive — `readAvailableData()` reads into a bounded
  buffer incrementally rather than allocating the declared size up front.
- **Confirmed: trivial unauthenticated worker-starvation DoS.** The receive
  path blocks synchronously per-connection until either (a) the declared byte
  count arrives, or (b) the peer half-closes. There is **no read timeout** on
  this path. With as few as **3 concurrent connections** that send a valid
  8-byte header and then withhold the declared payload (never closing), a
  **4th, fully well-formed diagnostic request from a separate connection times
  out completely** (≥3 s, no response). A single stalled connection alone
  measurably serializes/delays (but does not fully block) a concurrent
  request (0.02 s → 1.32 s), consistent with a very small (~2–4 slot)
  concurrent-handler capacity despite the process having 10 OS threads total
  (thread count does not grow with stalled connections — the limit is a
  logical handler/queue depth, not the OS thread count).
  - **Effect:** the root `diagnosticsd` (UID 0, all capabilities, bridges to
    the RTOS diagnostic endpoint on vlan4/172.16.4.107) stops servicing
    **any** client — including the legitimate RTOS bridge and any real
    Techline/MDI tester — for as long as the attacker holds ≥3 incomplete
    connections open.
  - **Recovery:** fully recoverable. Closing the stalled connections restores
    normal ~20 ms response times immediately; the daemon PID, `VmRSS`, and
    thread count are unchanged after the test (no crash observed).
  - **Reachability:** exploitable from the unprivileged Android shell
    (uid=2000) over loopback, and — per the firewall rules in
    [`platform/networking.md`](../platform/networking.md) — from any
    partition permitted to reach `:49156` (172.16.4.107 RTOS, 172.16.4.112
    CGM) without any UDS session/SecurityAccess state, since the block
    happens before frame parsing ever completes.
- **Corrected 2026-11-14 — sequencing and tester identity both matter.**
  Earlier all-rejected sequences used invalid tester IDs. Tester `0x00F4`
  successfully entered extended session and completed level-1 SecurityAccess;
  see the [validated T1 sequence](#live-t1-securityaccess-correction-2026-11-14).
- **Corrected 2026-11-14 — old address sweep omitted the accepted testers.**
  `0x00FA`, `0x00F1`, `0x00F0`, `0x0000` and `0x0001` negative results do not
  establish that every wire-supplied tester ID is invalid. Basic live requests
  succeeded with `0x00F4` and `0x00F5`; the complete grant was tested with F4.
- **`DIAG_CUSTOM` (SID `0x15`) is rejected identically to other SIDs**
  (`7F 15 10`) regardless of sub-function (closes Open Question #5, negative
  result).

---

## Source Structure, Symbols & HIDL

**Inferred source layout (strings):**
```
libuds/src/ethfrmwk/SockAdaptor.cpp
socket/TCPServer.cpp  socket/TCPConnection.cpp  ConnectionManager.cpp
DiagnosticEthernetMonitor (class)   DiagnosticsEthernetService (HIDL impl)
DiagnosticMessageFactory  MessageAccess  PALDiagnosticAdaptor
JavaRequestToResponsePipeline  GMCalibrationManager
```

**Protocol internals (strings):** `readHeader` (fixed 8-byte header, hardcoded),
`readAvailableData`, `"target address(%d) invalid"`; SHA256
(`SHA256_Init/Update/Final` — module-identity auth for calibration uploads, NOT
the wire protocol); CRC16 (`"Calibration Request Checksum (0x%04X vs 0x%04X)
failed"`); `"Transfer - Received too many bytes, moduleSize = %d"` →
`CAL_RECEIVING_TOO_MANY_BYTES`. UDS strings: `"checkSecurityLevelTable"`,
`"setSecurityLevel"`, `"new sec seed level"`, `"DID payload size greater than
three"`, `"Calibration Request Payload Size is Invalid"`; jsoncpp config layer
`"Exceeded stackLimit in readValue()"`, `"keylength >= 2^30"`.

**Dynamic symbols (`nm -D`, partial):** `gm::diag::ResponseCode` (BSS enum:
`POSITIVE_RESPONSE`, `GENERAL_REJECT`, `SERVICE_NOT_SUPPORTED`,
`RESPONSE_TOO_LONG`, `VOLTAGE_TOO_LOW/HIGH`, `BUSY_REPEAT_REQUEST`,
`CAL_ERASE_FAILURE`, `CAL_SEQUENCE_ERROR`, `DEVICE_TYPE_ERROR`, `SCHEDULER_FULL`,
`INVALID_KEY`), `gm::diag::DiagnosticsBridgeServiceManager`,
`vendor::gm::diagnostics::ethernet::V1_0::implementation::DiagnosticsEthernetService`,
`...IDiagnosticsEthernetService::registerAsService`.

**HIDL interfaces registered by diagnosticsd:**
```
vendor.gm.diagnostics.ethernet@1.0::IDiagnosticsEthernetService   (Ethernet diag bridge)
vendor.gm.diagnostics.bridge@1.0::IDiagnosticsBridgeService        (RTOS bridge)
vendor.gm.diagnostics.obd@1.0::IDiagnosticsOBDService              (OBD bridge)
vendor.gm.diagnostics.internal@1.0::IDiagnosticsInternalService    (internal/privileged)
vendor.gm.powermode@1.0::IPowerModeListener                        (power state)
vendor.gm.powermode@1.0::ISystemStateListener                      (system state)
```
`IDiagnosticsInternalService` is a higher-trust channel — if reachable via
`vndbinder` with the right SELinux domain, it offers a separate application
interface. It is not required merely to avoid the historical invalid-tester
NRC `0x10`; the corrected external TCP sequence succeeds.

**Related HIDL diagnostic services (separate binaries):**
- `vendor.harman.hardware.ame@1.0::IDiagnostics` →
  `/vendor/bin/vendor.harman.hardware.ame@1.0-service`. Methods:
  `readAppleAuthChipId`, `getGoogleKeyStatus`, `getLeoSwitchVersion`,
  `getLeoSwitchFlashPartitionStatus`, `getUsbVersion`, `getWifiIpAddress`,
  `getEthernetIpAddress`. SELinux `ame_hal_service` (shell denied).
- `vendor.gm.panel@1.0::IPanelDiagnostics` → `/vendor/bin/hw/vehiclepanel`
  (see [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)).

**Debug artifacts (not dev keys):** `libdiagnosticsdebugproxy.so`,
`libdiagnosticsdebugproxyservice.so`, `persist.vendor.debug.dvc.protocol`
(unset), `persist.vendor.avb.debug.loglevel.*`.

---

## OBD via Binder (alternative path)

The Android Binder service `com.gm.server.obd.OBDService` (PID shared with
`DiagnosticsService`) exposes `Do_On_Board_Diagnostics_Simple_Request(OBDRequest)`
(Tx1). It executes from uid=2000 but the `OBDRequest` Parcelable carries an enum
typed in `gm.obd.message.*` (28-char class, starts "OBDR…", e.g. likely
`OBDRequestedDiagnosticParam`); passing an int → `EX_ILLEGAL_ARGUMENT`
("No enum constant gm.obd.message.…"). With the correct enum it would return
live OBD2 data over GMLAN. See
[`platform/ota_update_stack.md`](../platform/ota_update_stack.md) for the
sibling UpdateService Binder surface and
[`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md)
for the full uid=2000 Binder access map.

---

## Android → diagnosticsd → CAN UDS surface (non-MDI2, 2026-09-10)

A live Android→`diagnosticsd`→CAN UDS `$22` ReadDataByIdentifier surface exists, distinct
from the Ethernet-UDS bridge above: an observed `Incoming payload: 22 F1 A0 00` read (MEC /
DID `F1A0`) round-trips through `diagnosticsd` onto the CAN diagnostic bus. Access is gated
by an Android-side permission check ("Check Permission first ... any DiagnosticDataID")
before the DID read is dispatched — the exact permission string/holder is not yet
characterized (candidate: same uid=2000 Binder surface as OBD-via-Binder above, or a
distinct signature|privileged permission). This is a **potential non-MDI2 path** to drive
DID reads/routines directly from the Android guest; what needs characterizing next is (a)
the permission name/grant path, (b) whether it's reachable from uid=2000 shell or requires a
signed app, and (c) whether it exposes `$22`/`$2E`/`$31` beyond the single DID observed so
far. OPEN.

Separately, a **direct T1/DoIP bench approach** would replicate MDI2-equivalent bus access
without an MDI2 dongle at all: media-convert the vehicle's diagnostic T1 (BroadR-Reach) pair
to a standard Ethernet PHY, then repoint existing DoIP tooling (e.g. the fsa_protocol.md
stack) at the resulting IP endpoint. This bypasses the Android-guest permission question
entirely by talking to the vehicle's diagnostic network directly, same as a dealer MDI2
would. Route noted, not yet executed on this bench. OPEN.

**[Updated 2026-11-11 per Y175_2026-11-02 Bus 2 tap bench finding:]** This has now been
**executed** on the Y175 bench, specifically against `172.16.4.100:49156` (diagnosticsd,
vlan4, reached by posing as CGM `.112` or RTOS `.107` on a direct T1 tap — BUELEC media
converter, no switch in path, since a switch was found to silently strip the 802.1Q VLAN
tags needed to reach vlan4/vlan5 at all). Result: diagnosticsd **is** externally reachable
over this plane — it is a root TCP server bound `0.0.0.0:49156`, gated only by a source-IP
allow-list of exactly `{172.16.4.107, 172.16.4.112}` (an exhaustive sweep of all 253 vlan4
source addresses and the full TCP 1–65535 range found no other allow-listed identity or
listening port). **Corrected 2026-11-14:** the historical `$10/$27/$31`
NRC `0x10` results did not prove a source-independent application lock; the
corrected tester/session sequence now returns a level-1 `67 02` grant. The old
routine request was not rerun, so routine support/effects remain unproven.
No DoIP service was confirmed by the later probes; a silent UDP result is not
proof of absence. See
`Y175_LIVE_RADIO_T1_SECURITY_ASSESSMENT_2026-11-02.md` and
`source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.

---

## vlan4 = internal GHS fabric; diagnosticsd forwarding target; bench-reachability of the VIP/UDS path (2026-10-06)

> **[C] CONCURRENCE CORRECTION (2026-10-06, independent 2nd fable agent re-derived from the primary binary + captures). Read before the section below — several claims were disputed:**
> - **diagnosticsd does NOT "forward to `.107:49156`."** It is a root **TCP *server*** on `:49156`; the captured firewall rule is **inbound** — `.107`/`.112` connect *into* it (`iptables_rules_file.txt:35-36`). **No `ESTABLISHED 172.16.4.100↔172.16.4.107` exists in any Y181/Y175 capture;** that line traced to a *gminfo37* (different platform) ref doc. The "forwarding target"/ESTABLISHED framing throughout this section is **UNPROVEN** — read "`.107` is a client that connects in," not "diagnosticsd dials out to `.107`."
> - **`ProxyOfExtComp` is not in the binary** (misattribution). Real symbols: `libdiagnosticsdebugproxy.so`, `MESSAGE_SECURITY_ACCESS_VIP`, `toVIPResponseCode`. The VIP-tier `$27`-proxy *concept* stands; the symbol name does not.
> - **"Bosch" for `.112` is UNVERIFIED** — only the real/external-OUI vs synthetic/internal split is solid (raw scan OUI "unknown, possibly Harman/Samsung").
> - **Exact NRCs (`$10 03→7F 10 10`, `$27 01→7F 27 10`) and "the session gate is strictly upstream of the VIP forward"** are **inferred from libuds handler strings** (`UDSSessionControlCheckHandler`, `UDSSecurityLevelCheckRequestHandler`, `"tester id check differ, process req in default session"`), not a traced call order — single-source.
>
> **Corrected 2026-11-14:** diagnosticsd is a root TCP server; the direct
> external client completed the F4/extended-session/31-FF/12-zero exchange.
> Historical SELinux `name_connect` and OUTPUT rules describe permission to
> attempt a connection, not proof that a GHS endpoint is present or reachable.
> The later external T1 checks did not reach those candidates. Their own
> trust models remain untested; synthetic MACs alone do not prove a specific
> partition's identity. The successful Android endpoint does not establish
> arbitrary service/key acceptance or GHS access.

Answers the question: *does the automotive-Ethernet VLAN connect the Intel A3960 (AAOS) to the
internal radio components (RH850 VIP MCU and/or GHS hypervisor) such that a 3P app reaching
diagnosticsd:49156 could drive UDS to the VIP on the bench, with no vehicle network — and how does
the SBI/EEPROM `$27` bypass interact?*

**Is `172.16.4.107`/`.112` internal or external?** — RESOLVED from ARP + TTL (Y181 and Y175,
bench captures, no vehicle connected):

| vlan4 peer | MAC | Kind | Identity |
|---|---|---|---|
| `172.16.4.107` (diagnosticsd's forwarding target) | `02:05:00:00:02:00` | **locally-administered / synthetic → hypervisor virtual NIC** | **INTERNAL.** Co-resident GHS "RTOS diagnostic" partition on the same Intel A3960 SoC. The **same** virtual NIC is dual-homed as vlan5 `192.168.1.112` (`enumeration/Y181/*/raw/arp_table.txt` — identical MAC). Response **TTL=255** (`platform/networking.md:80`). |
| `172.16.4.14` (ACP) | `02:02:00:00:04:00` | locally-administered / synthetic | **INTERNAL.** GHS control/application partition; statically pinned (`init_ethernet.sh:97 ip neigh replace`). |
| `172.16.4.112` (CGM_OTA) | `10:66:50:0c:ed:d3` | **real/universal OUI → external hardware** (vendor UNVERIFIED — raw scan "unknown, possibly Harman/Samsung"; *not* confirmed Bosch) | **EXTERNAL.** Off-board telematics/CGM hardware. TTL=64 (Linux). |

So **vlan4 is not a pure physical PHY to the car** — it is a hypervisor virtual-switch fabric that
carries both SoC-internal GHS partitions (`.107`, `.14`) *and* a bridge out to one real external
module (`.112`, external real-OUI — vendor unverified). This corrects the vehicle_network.md claim
that the "RTOS partition" was separate hardware (fixed in place there, 2026-10-06).

**Forwarding-target correction:** the historical assertion of a live symmetric
RTOS socket contradicted the concurrence correction above and is withdrawn.
The latest external T1 probes did not reach the documented GHS candidates.
Do not infer a direct GHS endpoint, the VIP relay transport, or a complete
internal routing path solely from firewall client addresses or source strings.

**Does vlan4 reach the RH850 VIP MCU directly? NO.** The RH850 is **off-SoC**, reachable only over
**HDLC IPC on `/dev/ttyS1`** (20 channels; diag = channels 3–5, `platform/networking.md:151-169`).
vlan4 is not wired to the RH850. The VIP is reached only *indirectly*: `.107` RTOS partition →
internal SoC↔MCU IPC → RH850. **[single-source/INF — the `.107`→RH850 onward relay is inferred;
RH850 firmware is not in the artifact set, so it cannot be re-derived statically here.]**

**Bench results and internal-route limits (corrected 2026-11-14):**

- The external client reached Android `diagnosticsd`, read software identification,
  entered extended session and obtained a level-1 `67 02` grant with the documented
  31-FF/12-zero exchange. The old claim that an unregistered shell/app can never
  pass the default session is withdrawn; no app-registration step was needed
  for the successful direct T1 test.
- The original negative address sweep omitted F4/F5. Its all-rejected result
  does not show that a correct tester/session sequence fails or that SBI has
  no effect on Ethernet. Only the exact 12-zero-byte response was accepted;
  arbitrary format-valid, all-FF or differently sized keys were not tested.
- No UDS write, download, transfer, routine, ECU reset, Android root shell or GHS
  shell was demonstrated. Android UID 2000 and enforcing SELinux remained
  separate from the diagnostic SecurityAccess grant.
- The static reference contains diagnostic framework code, but no complete
  live path through GHS/RTOS to the VIP was established. Prior claims of an
  observed internal RTOS socket are explicitly disputed above. The external
  GHS candidates did not answer the later T1 reachability checks. Do not
  substitute historical addresses, permitted socket policy, or synthetic MACs
  for proof of a currently reachable partition or of its authorization rules.
- Direct IPC and HIDL paths are separate interfaces. Live shell queries to
  the diagnostic-internal and root file-service HALs returned
  `does not exist, or no permission to connect`; the updater returned
  `No shell command implementation.` No alternate UID-0 shell was obtained.

**Build scope:** the corrected UDS responses are live Y175 results, informed
by Y181B static address/session handlers. These binaries are not claimed
identical. Historical Y181/Y175 ARP observations do not replace current
reachability testing or prove the key-compare backend's location.

## Open Questions

1. ~~Ghidra `DiagnosticEthernetMonitor::readHeader()` — exact trust check and
   alloc-vs-size-check order (confirm/deny pre-allocation DoS).~~ **Answered
   black-box, no binary needed (Jul 2026):** no pre-allocation (RSS flat up to
   1 GiB declared), but confirmed a **worker-starvation DoS** — see Oversized-
   Payload Behavior above. Still open: the exact source line/loop structure
   (would need the binary — live `adb pull`/`cat` of `/vendor/bin/diagnosticsd`
   is SELinux-denied even from shell on Y181 Enforcing; would require
   inspecting the processed Y181B reference. That reference is now available;
   `readHeader` at `0x46260` was inspected for the 2026-11-14 framing correction.
   Worker-starvation call flow was not re-tested or fully traced in that work).
2. **Corrected 2026-11-14:** the old address sweep omitted accepted testers
   F4/F5. F4 is live-validated through a level-1 SecurityAccess grant.
3. **Corrected 2026-11-14:** F4 plus extended-session entry, requestSeed and
   a 12-zero-byte response succeeded; the old negative sequencing conclusion
   is superseded by the validated sequence above.
4. Probe `IDiagnosticsInternalService` via vndbinder (needs a vendor SELinux
   domain). **Still open.**
5. ~~`DIAG_CUSTOM (0x15)` SID...~~ **Answered — negative** (see above).
6. ~~find the exact concurrent-handler capacity~~ **Narrowed:** N=1 → 0.02s→1.32s
   delay; N=2 → 0.02s→2.55s delay; N=3 → full timeout (≥3s, no response within
   test window). Latency scales with N even below the failure point, which
   reads more like a serialized/polled accept-dispatch path (e.g. a single
   dispatcher thread iterating connections with blocking or long-interval
   reads) than a hard-capacity thread pool — a true fixed-size pool would show
   flat low latency until the pool fills, then a cliff, not a graded ramp.
   Exact structure still needs the binary to confirm.
7. **New:** does the same worker-starvation condition affect the sibling
   `vendor.gm.diagnostics.*` HIDL services (`bridge`, `obd`, `internal`,
   `powermode`) if they share the same accept loop / thread pool as the
   Ethernet TCP listener, or is `IDiagnosticsEthernetService` isolated?
8. **New:** does holding the connection-starvation condition open during an
   active vehicle diagnostic/programming session (e.g. mid-OTA `SecureUnlock`
   state) have a functional effect beyond delayed responses — untested,
   deliberately not attempted on this bench unit without further discussion.
9. **New (2026-09-10):** characterize the Android permission gate on the
   `diagnosticsd` CAN UDS `$22` ReadDataByIdentifier surface (see "Android →
   diagnosticsd → CAN UDS surface" above) — permission name, grant path, and
   whether uid=2000 shell can reach it directly. **Open.**

## GM service-data note (ALLDATA)

GM's ALLDATA for this vehicle publishes **no UDS/GMLAN diagnostic addresses** — the "Code"
column (A11, T3, K9…) is the RPO/schematic designator, not a bus address. So request/response
IDs like `0x14DA80F1` come from **captured bus traffic** (`dps/`), not GM docs. The dealer-side
scan-tool (**GDS2**) *data-parameter* lists for A11 Radio / T3 Amp / K9 BCM — Ethernet per-port
Rx/Tx fail counters + IPs, MEC, ANC/mic levels, battery-sensor stream, etc. — are catalogued in
[`../enumeration/README.md`](../enumeration/README.md) §Vehicle module inventory, and the
diagnostics/programming CAN bus is **CAN6 (5 Mbit/s)** per
[`../platform/networking.md`](../platform/networking.md).

> **Tester-ID note:** `0x14DA80F1`/`0x145AF180` is the **generic OBD tester (F1)** pair used by the
> DPS bench read logs (confirmed: GM_research/diagnostics/gm_dps/DPS_All_Module_Read/.../GCI_*.txt).
> The **dedicated tester (F2)** pair for ECU 0x80 is `0x14DA80F2`/`0x145AF280` (per `A11_CSM_x80.Txt`);
> both reach the radio on HS-CAN.
