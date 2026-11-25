# diagnosticsd — RoutineControl Outcomes

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

---

### CANable stock-write follow-up (2026-11-16)

The later direct CAN5 campaign transferred all fourteen genuine LTZ containers
without MDI2 or calibration clearing, including already-matching modules.
Working restart verification required the vehicle-VIN CAN input test after an
intermediate NoVIN failure. The owner confirmed the homescreen; fresh readback
matched all fourteen LTZ identities and the supplied VIN, all module statuses00,
and F0F1/F0F2=`0000`. Genuine HC has subsequently transferred all fourteen
containers and completed F198/F199/039B/F190 finalization. HC mute restart
reached calibration state2/HMI ready/Propulsion; all fourteen HC identities,
the VIN and module/error statuses were verified afterward. The distinct HC
logo and its moving welcome animation were owner-observed. A later
modified slot0C test was rejected with `7F 36 72`; genuine slot0C was restored
in the same session and HC restart/identity/status checks passed again. The owning
[CAN campaign](../platform/can_bench_experiments.md#full-genuine-ltzhc-rewrite-through-canable--2026-11-16)
records preparation, transport differences, NoVIN recovery and remaining limits.
Historical failed T1 attempts below are not a current claim that MDI2 is required.
No `0249`, `FF00`, or substitute calibration clear was used in this campaign.

### CANable full-package rewrite — driver bug fixes (2026-11-25)

A repeat of the above full-package genuine LTZ rewrite surfaced two real bugs in the
CAN5 driver itself (not a vehicle-side quirk): a per-slot session re-entry that the
VIP read as "programming ended" between slots, and a TransferData block-size
off-by-two that silently dropped any full-size (≥4095-byte) block. Both are fixed;
live `F182` readback now matches all 14 slots against their stock LTZ containers
byte-for-byte. Full root-cause analysis, fix detail and the per-slot verification
table are owned by the
[CAN campaign](../platform/can_bench_experiments.md#full-genuine-ltz-rewrite--two-driver-process-bugs-found-and-fixed-1414-verified--2026-11-25).

### CANable custom-slot write — byte-order bug resolved (2026-11-25)

The same session also resolved the separate custom (non-stock) single-slot write
through the CAN613/614 VIP development-memory interface: its blocking bug was the
marker-pair values being sent in the wrong byte order on the wire, not a firmware or
toolkit limit. The fix is verified both by a clean UDS transfer and the owner's own
visual confirmation that the modified feature (SXM) was gone from AAOS Radio.
Root-cause trace and reproduction are owned by the
[custom calibration workflow doc](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-resolved--the-driver-was-sending-the-marker-pair-values-byte-swapped);
the mechanism and full results table are owned by the
[CAN campaign](../platform/can_bench_experiments.md#calibration-write-mechanism-can613614).

### Resolution work and controlled actions

Follow-up tests retained concurrent USB logcat and append-only UART observation.
The corrected UART matcher accepts whitespace around SID/ISID separators.
No additional raw capture files were created; the owner's screen logger was
not reconfigured. Calibration clearing was reserved for the final state-changing diagnostic test; its completed result is recorded below.

**Negative-DID assignment correction:** the fresh per-ID baseline gives
22 48 38 -> 7F 22 31 and 22 51 51 -> 7F 22 22. An earlier chat table assigned
these two categories from aggregate counts without retained per-ID evidence;
that assignment is superseded. DID4838's live Java method explicitly generates
an out-of-range response. DID5151 attempts DAB signal-strength prerequisites;
logcat reported `pre-condition of signal strength failed`.

| Read group | Direct live-code finding |
|---|---|
| 41ED | Requires surround availability before reading surround level. |
| 42A6/42A7/42A8/42A9/C001 | Selects internal CSM or external TCP/OnStar location from GNSS_DR_SRC and GPS_DATA_SOURCE calibrations. Android reported no last location and stopped GNSS during the probe. |
| 42B7 | Requires AVB bridge-port information; live logcat reported `Array of PortBridgeInformation implementation is null or empty`. AVB processes were running, so process presence alone is insufficient. |
| 42BE | Reads persist.sys.clockOffset and derives a UTC clock-hours/minutes/seconds value from its absolute milliseconds; values above 4095 produce a HandlerException. The live large offset exceeds that range. A shell attempt to set a temporary zero offset was denied; the original property remained unchanged. |
| 4428/4775/5151 | Requires tuner source/command prerequisites. Launching Now Playing alone did not satisfy them; the successful 03D8 start below made 4775 readable. |
| C00A/C00B/C00C/C00D | Reads SXM hardware/software/baseband/decoder/RF revision APIs. These remained NRC 22 after launching Now Playing. |
| C012/C013/C014/C015 | Uses LCM ECU-status/info accessors. |
| F09A/F0F4/F1DB/F1DC | Inherits the VIP pass-through DID handler. The bounded phase containing these four requests produced four UART SID 09 / ISID 00 events, consistent with forwarding rather than a missing Ethernet SID mapping. Final replies remained NRC 11. |

**03D8 sequence resolved:** request-results before start returned 7F 31 22.
31 01 03 D8 then returned 71 01 03 D8 after one pending reply; following
31 03 03 D8 returned **71 03 03 D8 07**. The live implementation defines
result bits 0/1/2/3 as audio-unmuted, audio-screen displayed, AM enabled and
FM enabled. The returned 07 reports the first three. A subsequent 22 47 75
returned positive data (one byte). Thus 4775 is an additional readable DID in
the post-action state: 136 distinct positive DIDs have now been observed across
states, while the original exhaustive level-09 sweep remains 135 in its tested
state. This is a demonstrated direct-T1 control operation, not just a class
inventory. No calibration erase occurred.

**0248 favorites actions:** all requests used extended session / level 09.
The one-byte option record is mandatory. Option 03 is the no-op branch;
00 resets audio favorites, 01 phone favorites and 02 navigation favorites.

| Request | Final reply |
|---|---|
| 31 01 02 48 03 | 71 01 02 48 |
| 31 01 02 48 00 | 71 01 02 48, after one pending reply |
| 31 01 02 48 01 | 7F 31 22 |
| 31 01 02 48 02 | 7F 31 22 |

**Programming precondition check:** after a level-01 grant,
31 01 FF 01 returned **71 01 FF 01 00 86 04 03 00**. The parser checks
programmed state, authenticated backup/system power-mode monitors, security
state and UpdateManager's unlock timeout. Its programmed-state enum maps 00
to FULLY_PROGRAMMED. The five-byte result's remaining flags require their
precise field semantics; the succeeding 10 02 still returned 7F 10 22.
Executing FF01 alone therefore does not establish programming readiness.

**5F correlation:** a fresh 27 5F attempt produced six pending responses and
7F 27 25 at 29.991 seconds. It was mapped to native SecurityAccess; the corrected
observer counted no UART diagnostic event in that phase. This does not share
the proven missing-SID-map explanation of services 11/23. The specific
local/security forwarding path is still being traced. Default session was
restored after each bounded probe.

### Completed resolution actions, security profiles and access limits

All addresses below are offsets in the inspected native ELF. Ghidra imported
x86:LE:64 at image base 00100000; add that base to the listed offsets for its
listing. The installed ghidra-diag/PyGhidra workflow used separate temporary
projects for diagnosticsd, calserviced and gm_update_engine; the GUI MCP initially
reported NO_PROGRAM. Static conclusions remain distinguished from live tests.
The running native calibration/client/update-engine executables could not be
byte-matched: USB reads returned Permission denied. Their reference call chains
are supporting evidence, while wire responses and daemon logs are live evidence.

**Programming gate resolved in code:** native session handling sends its internal
state query 5 to SessionControlHandler.getEcuInternalProgrammingStateResponse.
That live Java method returns positive only when the authenticated
BackupSystemPowerModeProtectedRemoteProgrammingActive signal is true; missing,
unavailable or false signals give conditionsNotCorrect. Its VHAL property is
0x2120105C; authenticated system power mode is 0x11400409. CarService listed
clients for both properties. Shell get-property-value/help commands were denied
with `requires non-user build`; direct VHAL debug access also failed. No signal
injection was conducted. Grants 01, 03 and 05 each gave the same FF01 precheck
reply 71 01 FF 01 00 86 04 03 00 and 10 02 -> 7F 10 22. RIDs 0209 and 0300
returned 7F 31 7F in extended session, matching their programming-session gate.
Reference Java 0209 checks a selected partition's programmed state; 0300 builds
a fixed one-byte response 10. Neither was executed in programming mode.

**Security profiles are not an ascending privilege hierarchy.** The odd
SecurityAccess selectors identify independent permission profiles. Every row
below is a recovered native-table permission, not proof of a working operation.
Other session, payload, vehicle-state, backend and signature checks still apply.

| Selector or operation | Permitted non-default levels, hex |
|---|---|
| 10 02 programming-session request | 01, 03, 05 |
| 22 F0A7 protected read | 09, 0B, 0D |
| 23 memory-read service | 09, 0B |
| 2E F190 / F198 / F199 | 01, 03, 05, 11, 13, 15 |
| 2E E010 | 09, 0D |
| 2E F0F4 | 01, 0B, 11 |
| RID 021E | 01, 03, 05 |
| RID 0200 / 0205 | 01, 03, 11, 13 |
| RID 0204 | 03, 13 |
| RID 0475 | 05 |

Generic wildcard rows can allow level 00/default, but a specific row overrides
that general permission. No listed DID write was exercised. Nine grants were
validated; 5F never granted. Successful memory-read authorization still reaches
the missing converter mapping already documented, rather than a working reader.

**Further routine outcomes:**

| Routine / test | Actual result and limit |
|---|---|
| 0260 retry counters, option 05/NONE | 71 01 02 60 |
| 0260 options 00/ALL, 01/telematics, 02/cluster, 03/wireless charger, 04/V2V | 7F 31 31; no successful counter reset for these targets demonstrated. Live logs identify cluster and V2V as unsupported LCM types. |
| 0254 LCM-record clear | 71 01 02 54. The implementation treats an already-empty DB as success; a deleted-row count was not retained. Subsequent C012–C015 reads remained NRC 22, with live empty-record-set errors. |
| 0475 results, level 05 | 7F 31 22. Current Y175 gm_update_engine DiagnosticsHandler is at RVA64330, corrected from the earlier51910 attribution after byte-hash-checked inspection. It implements start/stop branches; no valid complete install plan or transfer was submitted. See the ABFT follow-up below. |
| 0200 / 0204 / 0205 / 0332 / 039B results, level 03 | All 7F 31 31. MY23's fixed RIDxxxxHandler lookup found no corresponding classes. This does not prove every start payload or another transport is unsupported. |
| 0405 registration trigger | 71 01 04 05. Tested with no active Android default network and registration service initially stopped. Its local service reads MEC; no MEC setter was found in that service. MEC remained FF and the service was stopped afterward; cleanup reported it was already not running. No completed remote registration was demonstrated. |
| 0247 full user-data wipe | Not sent in this routine campaign. Live code calls vehicle-settings restore followed by RecoverySystem.rebootWipeUserData asynchronously. Separate historical reset and2026-11-17 direct-CAN retest are recorded in MDI2_RAW_UDS_BYPASS_GUIDE: the latter initially returned7F3122; setting CAN20D byte4 bits5–7 to2 subsequently produced71010247 and an owner-observed factory reset. |
| 021E VIP pass-through | Its live handler requires authenticated system power mode 1 or 2 before forwarding; no unclassified VIP start was issued. |
| FF00 per-module calibration erase | Not sent; the later explicitly requested 0249 all-overrides clear was the calibration action. |

**Alternate Binder read trial:** live framework code identifies transaction 3,
bus values 2/CANBUS and 1/ETHERNET, and enum ordinal 13 for F181. Both correctly
encoded empty-option F181 requests from UID 2000 returned SecurityException:
`To Read Vehicle Internal Information Requires Privileged Permission if privileged, or Dangerous Permission if otherwise.`
The live permission helper checks CAR_VENDOR_EXTENSION for VIN and the protected
GM vehicle-internal-information permission for other DIDs. Thus the observed
Android/CAN interface exists but these shell calls are rejected before manager
dispatch; this is not proof of a missing daemon or a working UID-0 shell.

**LLDB runtime validation:** the NDK-30 server crashed with exit 139 during an
attach attempt; the Android Studio server (23.0.1) then worked with the installed
LLDB client. It successfully attached to an owned disposable UID-2000 sleep
process and detached. The same path against the identified root-owned
diagnosticsd returned `Operation not permitted`. The target daemon retained its
PID and sleeping state. Uploaded servers and temporary USB forwards were
removed. No successful trace of the root daemon or Ghidra Trace RMI mirroring
was claimed. All MEC checks around the attempts returned FF.

**Other remaining read limits:** 42BE's attempted temporary property write was
rejected (`Failed to set property 'persist.sys.clockOffset' to '0'.`); the original
value was unchanged. SXM C00A–C00D probes produced actual resource/handler
exceptions; their wrappers call SxmDiagnosticsManager revision APIs and parse
returned strings. Exact API-error/format causes are not fully resolved. GPS
source selection, missing fixes, unsupported DAB/source prerequisites and AVB
empty-port data were identified, but no GNSS signal, DAB hardware/source or AVB
endpoint was fabricated. A successful cold-start/full-wipe test was not claimed.

### Final calibration clear: completed, MEC preserved

The owner explicitly requested the clear after the other controlled tests,
with the additional requirement that MEC not be reset or set to zero.
22 F1 A0 returned **62 F1 A0 FF** immediately before the operation. Extended
session and the documented level-01 grant were established. Exactly one
**31 01 02 49** was sent. It produced one pending frame, then
**71 01 02 49**, with the final reply at **0.126 seconds**. No subsequent 0249
request-results was sent, because that path clears again.

Concurrent logcat confirmed:

```text
CalibrationStorage.cpp(596): clearAllOverrides - ALL OVERRIDES CLEARED!
calserviced.c(444): set_update_J5: Created Persistent J5 Indicator.
```

The full F182 payload comparison is decisive: all **14 module records with
tags 02–0F changed from their previously selected package identities to part
number 70008, DLS 00**. Total record count stayed 28; the other 14 records did
not change. Immediate and three-second readbacks matched. Counting records
alone would have missed the clear's effect. This is current selected-module
metadata evidence, not a direct post-clear SQLite row-count query.

MEC returned **62 F1 A0 FF** immediately afterward, at three seconds and on a
later final read. No MEC write/reset command was sent. Android boot identity
was unchanged, and default session was restored. The corrected UART observer
remained live and saw diagnostic SID events; no reboot was demonstrated.

The reference native path is CalibrationAccessor.clearAllOverrides (25F30) ->
GMCalibrationManager.clearAllOverrides -> CalibrationService/CalibrationServiceBase
-> CalibrationStorage.clearAllOverrides (50670). It erases override directories,
restores its base database, updates indicators and notifies listeners. Its
setExternalIndicators helper calls requestShutdownOnNextPowerCycle and creates
a persistent J5 indicator; in this reference the power helper logs NOOP until
VIP is ready rather than issuing a power command. No direct MEC write was found
in that traced path. The owner subsequently power-cycled the radio; the observed fault is recorded below. No automatic power-cycle was initiated.

A new, explicit follow-up request then authorized the separate full ADB-UDS
candidate sweep after this clear. That trial is documented independently below;
no additional calibration clear or MEC write is part of it.

### Full ADB-over-UDS candidate trial after calibration clear

At the owner's explicit follow-up request, the reported candidate
31 01 03 32 DD 42 10 EE was tested with every domain DD=00–FF and both
EE=01 (reported enable) / EE=00 (reported disable), in default session and
after each available granted security profile. This was a newly requested
post-clear test; no further calibration-clear or MEC-write request was sent.
The fixed tester/target and custom T1 transport from the validated procedure
were used. USB logcat and the owner's existing UART logger were monitored.
A 22 F1 A0 guard followed every candidate request and required FF throughout.

| Context | Candidate requests | Final NRC distribution / limitation |
|---|---:|---|
| default | 512 | `7F 31 31` × 512 |
| 01 | 512 | `7F 31 31` × 512 |
| 03 | 512 | `7F 31 31` × 512 |
| 05 | 512 | `7F 31 31` × 512 |
| 09 | 512 | `7F 31 31` × 512 |
| 0B | 512 | `7F 31 31` × 512 |
| 0D | 512 | `7F 31 31` × 512 |
| 11 | 512 | `7F 31 31` × 512 |
| 13 | 512 | `7F 31 31` × 512 |
| 15 | 512 | `7F 31 31` × 512 |

Total candidate requests: **5120**; MEC checks: 5121; elapsed seconds: 418.89.
Final MEC reply: `62 F1 A0 FF`. Default session restored.
Android `adb_enabled` before/after: `1` / `1`; USB ADB remained available.
No pending responses or transport errors occurred. The concurrent monitor
counted 41,193 diagnostic logcat lines and 5,123 UART events during the
trial phase. These counts include the interleaved MEC reads and session
setup; they do not establish that the RH850 received each ADB candidate.
The owned USB-logcat monitor was stopped afterward; the owner's UART logger
was left running. The subsequent owner power-cycle produced the fault documented below.
No positive candidate response was observed. This result is limited to the tested radio/build, target, transport, sessions and payload layout; it is not proof against every OEM ADB-control mechanism.
Programming session was not included because its authenticated vehicle-state gate remained unsatisfied. Seed profile 5F was not included because no grant was established.

#### Post-reboot direct T1 ADB-enable trial 2026-11-15

The owner rebooted the radio while retaining T1 connectivity and UART logging.
No authorized USB or TCP ADB device was available. An initial attempt to use
an ADB forward stopped at `adb: device offline`; no diagnostic request was
sent by that attempt. A direct source-bound VLAN-4 connection to port 49156
then reached diagnosticsd **without using ADB**. The temporary host interface
was configured from the cleanroom firewall rules and removed afterward.

| Step | Observed final response |
|---|---|
| `3E 00` | `7E 00` |
| MEC guard `22 F1 A0` | `62 F1 A0 FC` (initially responsePending) |
| Extended session `10 03` | `50 03 00 64 01 F2` |
| Documented level-1 FF31 / zero12 exchange | `67 01` plus FF31; `67 02` |
| Enable-only candidate `31 01 03 32 00 42 10 01` | **`7F 31 31`** |
| MEC guard after attempt | `62 F1 A0 FC` |
| Restore default `10 01` | `50 01 00 64 01 F2` |

The domain-zero enable candidate was sent once; no disable, broad sweep,
MEC write, calibration clear or flash/programming request was sent. Post-test
ADB enumeration found no authorized or unauthorized USB/TCP device. A
privileged source-bound check of the previously working radio TCP port 9040
returned `ConnectionRefusedError: [Errno 61] Connection refused`. The initial
unprivileged check's `OSError: [Errno 65] No route to host` was therefore a
host-access artifact, not evidence that the radio's T1 network was down.
The radio time could not be checked or set over ADB in this disconnected
state; no fresh Android logcat attribution is claimed for this trial.

**Static rejection path:** the Y175 cleanroom DelayedWKSApp, byte-matched to
the live APK before the reboot (SHA-256
`5916ad9f7d40d2683e4dac49b7cc5086104dd27042c7fc32716fc3094288e241`),
contains `MY22CsmRIDRequestResponsePipeline`. It constructs `RID%04XHandler`,
tries common and MY22 RID namespaces, and returns `REQUEST_OUT_OF_RANGE`
when neither supplies a handler. No `RID0332Handler` class descriptor was
present in the APK's three DEX files. This provides a static explanation
consistent with the T1 rejection; it is not a fresh runtime stack trace or
proof that VIP rejected the routine over CAN.

The same APK contains `RDMSADBHandler.RDMSADBEnable` and its USB-role/bridge
setup path. That Binder service is a separate local Android interface;
no call chain from RID0332 or an externally reachable T1 method to it has
been established. Its existence does not make an ADB-enable UDS command
available automatically. Firmware strings mentioning ICUSB also do not
identify such a command.

**Manual recovery follow-up, 2026-11-15:** enabling ADB through AAOS settings
restored an authorized USB connection with `adb_enabled=1`. The Android clock
was synchronized from the Mac and its timezone checked. The radio's ADB
listener was restored to TCP 9040 through USB; a fresh T1 shell returned UID
2000 and read back port 9040. The post-sync clock difference was approximately
0.4 seconds. This was manual UI enablement followed by ADB transport setup,
not successful UDS activation.

One instrumented enable-only retry after manual recovery again returned
`7F 31 31`; MEC remained FC, `adb_enabled` remained 1 and default session was
restored. No fresh `RID0332Handler` reflection log was captured, so the
missing-handler explanation remains grounded in the matched APK's factory
and class inventory rather than a newly observed exception for this retry.
The temporary diagnostic forward was removed; working USB/T1 ADB remained.

**Remaining open:** a build-specific diagnostic route that reaches the real
ADB-enable operation, its payload/gates, and a successful offline-to-online
ADB transition. Earlier CAN-side domain attempts are recorded in the
[MDI2 routine reference](../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md#7-gm-adb-escape-hatch-via-31-routinecontrol-2026-09-10);
further direct-CAN testing is pending the owner's USB CAN adapter.

#### AME8030 mechanism identified; CAN-level route still open (2026-11-20)

A live bench session (VIN redacted; confirmed 2024 model year from `22 F1 90`) found
the real ADB-enable mechanism is **not** RoutineControl `0332`. A non-mutating UDS
service-presence scan on `0x14DA80F1` (bare-SID probing, destructive SIDs excluded)
found every vendor-range SID (`0x80`–`0xFF`, including `0xDA`/`0xDB`) absent from the
VIP's CAN-served set, and both RDBI `22 80 30` and RID `31 03 80 30` return `7F ... 31`
(not a served DID/RID). The application-layer ADB frame `DA 80 30 03 xx xx 01`
(handler `AME8030Class`, mode `01` = enable) is confirmed real in the Android guest,
not on the VIP's CAN endpoint: `0xDA`/`0xDB` is a SoC-internal PCI vendor-message
selector (`AMEDispatcher`, item id `0x8030`), not a CAN SID.

A follow-up multi-agent firmware pass (VIP DID/RID tables, VIP transport, SoC
jadx/HostOS/critical.apk; five isolated agents) traced the end-to-end path: tester
CAN `0x14DA80F1` -> VIP DCM -> SPI-IPC diag channel -> J6/SoC -> Android guest VM
(HostOS `85098662` is the GHS INTEGRITY type-1 hypervisor; Android runs as its guest
VM, and the AME/ADB logic lives in that guest image, not in HostOS itself) ->
`PciVendorMessageHandlerImpl`/`AMEDispatcher` -> `AME8030Class` ->
`setprop sys.usb.config=adb`. Three agents
independently found no DoIP below the Android guest: the VIP is CAN-only and HostOS
is SPI-IPC-only, so a DoIP server for AME would have to live in the guest over the
Ethernet PCI-passthrough path — untested, unproven, and the current leading
hypothesis for whether this is reachable off-CAN at all.

**Still unresolved:** the exact CAN-level DID/RID (if any) that tunnels the
`80 30 ...` AME payload through the VIP — `0x8030` itself is confirmed absent from
both the VIP's served-DID table and the SoC's DiagnosticDataID table, so it is the
internal AME selector, not a wire identifier. This narrows, rather than replaces,
the "remaining open" item above, and additionally rules out RoutineControl `0332` as
the mechanism on this 2024 ICE build — consistent with the static finding that the
2026 EV's `RID0332Handler` is a different vehicle/stack and does not exist here either.

### Owner power-cycle after clear: NoCalibration fault (2026-11-14)

After the owner powered the radio back on, the display reported bad or
incomplete calibration and could not be used to enable ADB. The existing
RH850 UART capture showed `evPowerModeOn`, `SystemState=AnimationInit`,
`SystemState=HmiInit`, then at approximately 23.3 seconds
`evt=evSTARTUP_FAULT_TIMEOUT`, `SystemState=NoCalibration (0xe)` and
`st=NoCalibration`. The state persisted after HMI-ready events. Calibration
group responses were logged before the fault; receiving those groups does
not establish that the complete selected calibration set was accepted.

Fresh read-only T1 requests still worked: MEC returned `62 F1 A0 FF`;
F182 retained 28 records with all 14 tags 02–0F at part 70008 / DLS 00.
Thus the clear persisted across power loss and the resulting base-only set
was insufficient for normal startup. USB ADB returned `error: no devices found`;
a connection check of the previously known T1 ADB port also failed. No
post-boot Android clock synchronization or logcat inspection was possible
through ADB. T1 activity is not evidence that ADB is enabled.

The fault is consistent with removal of the applied calibration modules;
the exact startup validity check and cause of ADB unavailability remain
untraced. The preceding ADB-UDS trial had no positive responses and left
`adb_enabled=1` before power-off. At this stage no post-boot programming,
additional clear, MEC write, guessed calibration restoration or further ADB
toggle had been sent. The later successful MDI2 recovery is recorded below.
The supplied update-cache ZIP contains the database but none of the 14
applied `.cmod` packages, so it is not a complete restoration source.

### Direct-T1 stock LTZ restoration attempt and shell checks (2026-11-14)

At the owner's request after the NoCalibration boot, the GM LTZ package
was loaded from the existing stock cache. All 14 unmodified containers
matched the independently pinned LTZ_REFERENCE SHA-256 values; total
46,162 bytes. The existing MDI2 orchestration was not run because it
requires MDI2 and sends another clear before checking programming mode.
No source code was changed. An initial local helper import failed with
`ModuleNotFoundError: No module named 'Crypto'` before network I/O; loading
only the standard-library calibration validation helpers resolved it.

The direct custom-T1 endpoint returned:

| Request / check | Actual result |
|---|---|
| MEC before | `62 F1 A0 FF` |
| `10 03` | `50 03 00 64 01 F2` |
| Validated level-01 exchange | `67 02` |
| `10 02` | `7F 10 22` |
| First stock RequestDownload, `34 00 44 00000000 0000058D` | `7F 34 7F` |
| MEC after | `62 F1 A0 FF` |
| Restore `10 01` | `50 01 00 64 01 F2` |

No TransferData or TransferExit was sent, no calibration bytes were written,
and no additional clear, reset, DTC/communication control or MEC write was
sent. The first RequestDownload rejection confirms that a valid package alone
cannot pass the active-session gate. The previously traced authenticated
remote-programming property remains the known programming-mode gate; its
post-boot value could not be inspected without ADB.

Targeted TCP checks were bound to the existing T1 source addresses on both
VLANs; no Wi-Fi or USB RNDIS probes were used. SSH 22, telnet 23 and ADB 5555
timed out on both VLANs. Previous ADB port 9040 timed out on VLAN4 and returned
`Connection refused` on VLAN5. Other known allow-listed VLAN5 debug ports
2942, 9090, 6060, 12345, 1234 and 1235 all returned `Connection refused`.
No interactive network shell was established at that checkpoint. The later
[working T1 ADB setup](diagnosticsd_network_topology.md#working-t1-adb-follow-up-2026-11-15)
used radio TCP 9040 after configuring its listener; it supersedes any general
claim that network ADB is unavailable. Timeouts do not distinguish
filtering from absent listeners. The RH850 UART logger remained the owner's
existing output-only capture; no serial input or UART shell command was sent.

### Successful MDI2 LTZ recovery after calibration clear (2026-11-14)

**Result: the previously cleared A11 radio was restored with the stock LTZ
package and the owner confirmed normal display and radio operation.** All
14 calibration slots 02–0F matched post-reset F182 metadata, the supplied VIN
matched readback, and F0F1 programming-error code and F0F2 boot-information
status both returned `0000`. This supersedes the unresolved recovery status
after the direct-T1 attempt above; that attempt itself transferred no data.

The successful path used the main native Python package in `mdi2_client`,
its project venv, MDI2 USB RNDIS management and the TCP/10123 D-PDU CAN tunnel
to A11/ECU `0x80`. It did not use the custom direct-T1 programming endpoint,
the old MDI2 client or the file-logging bench wrapper. The package was the
existing stock `24_LTZ_A11` cache: all 14 unmodified containers matched the
independently pinned `LTZ_REFERENCE` SHA-256 values. No client source file
was changed during recovery.

#### Issues and resolutions

| Issue / actual result | Resolution and scope |
|---|---|
| Discovery: `LookupError: no MDI2 announce beacon seen` | The USB interface was active with IPv4 but had a /32 mask. Changing only its existing address's netmask to /24 did not by itself fix discovery. The same venv under `sudo -n` resolved the beacon and received 9052 control reply `0053500000310000`; that execution identity was retained. This is an observed difference in this Mac execution context, not a universal root requirement. |
| `LiveDpduError: D-PDU tunnel is not available (re-arm failed)` | Management answered and one adapter log stream was retrieved, but the diagnostic tunnel remained unavailable. After the owner power-cycled MDI2, re-arm opened the tunnel. Session-table exhaustion was not established as the cause. |
| Vehicle initially in service mode | The owner placed the vehicle OFF. The writer independently verified BCM F085=`00`; service mode `02` is not the accepted programming gate. |
| Full `identify` returned `TransactionError: service 22 NRC 31` | Separate mandatory reads succeeded: F190 returned 17 bytes and F182 returned 200 bytes / 28 records. The failing extra identity DID was not isolated; the recovery used those direct reads rather than requiring the full identity summary. |
| `ValueError: source calibration metadata is not a supported LTZ or High Country baseline` | Every slot 02–0F contained the exact documented post-clear record: slot byte followed by `00 01 11 78 30 30`, base part 70008 / DLS 00. A process-local source classifier accepted only that complete 14-slot cleared profile in addition to the existing LTZ/High Country profiles. Unknown or mixed profiles remained rejected. The target package hash gate was retained. |
| `ProgramFailure: phase=read identifiers transferred=0: transaction failed; outcome may be ambiguous; no retry` | Read-only diagnosis found F190 was 17 bytes of `FF`, while F198 and F199 had the expected 10- and 4-byte lengths. The main transaction requires a printable VIN; the erased VIN explained this validation failure. F0F0 still showed status `02` for each slot; F0F1/F0F2 were `0000`. No container had transferred. |
| Erased VIN blocked programming | The owner supplied `<EXPECTED_VIN>`. After package/source, BCM OFF and voltage checks, extended session and the existing SecurityAccess helper were followed by `2E F190 <EXPECTED_VIN>`. F190 was read back and matched before a fresh recovery plan and write. The real VIN was used only in memory and is omitted here. |

The source-profile exception was an explicitly authorized, in-memory recovery
adaptation. It was not a new CLI option, a persistent monkeypatch or a general
removal of source validation. An unmodified `mdi2.cli write --confirm` still
rejects the cleared baseline. Likewise, a 17-byte F190 response is not enough:
the pre-write VIN must be printable and equal the intended VIN.

#### Successful programming sequence

1. Validate all 14 stock LTZ hashes; resolve the adapter; confirm a real 9052
   reply; re-arm D-PDU. Use one diagnostic client at a time.
2. Confirm the radio VIN is either erased (`FF` × 17) or already equal to the
   supplied VIN. Validate the exact cleared source profile, BCM OFF and
   programming voltage before restoring an erased VIN. Stop on another VIN.
3. Restore and verify the supplied VIN as above. The pre-restoration voltage
   sample was **12.412 V**. A fresh `plan_ltz_write` then passed all gates at
   **12.359 V**, including a matching supplied VIN and the exact cleared profile.
4. Call the main `write_ltz_calibration(..., confirmed=True,
   pre_reset=False)` orchestration with the same narrow process-local source
   classifier. Its fresh-start preflight and immediate pre-programming checks
   retained package hashes, VIN, source stability, BCM OFF and voltage.
5. Run the existing SPS sequence: extended session, DTC logging off, normal
   communication off, SecurityAccess, pre-programming 0249, programming
   session, all 14 container transfers, and F0F0 status verification. The
   existing all-FF-seed SecurityAccess path succeeded; no real-seed CMAC key
   or MEC-write command was supplied.
6. Reconnect for finalization: default session, ECU identity F1B0, extended
   session and SecurityAccess; write F198 and current-date F199; finalize
   with 039B; personalize F190; issue the single final `11 01` reset.
   There was **no pre-reset** and no automatic programming retry.
7. After the built-in reboot wait, use a fresh link to verify the supplied
   VIN and compare every calibration slot. Slots **02, 03, 04, 05, 06, 07,
   08, 09, 0A, 0B, 0C, 0D, 0E and 0F** all matched; F0F1 and F0F2 were `0000`.

The transaction status string was `RESET_ACCEPTED_NOT_VERIFIED`. That string
describes the transaction's reset acknowledgement; the enclosing live writer
subsequently completed fresh post-reset VIN and metadata reads. Display
operation, startup completion and normal radio operation were also owner-observed.
Metadata matching does not constitute full payload readback.

#### RH850 UART confirmation and remaining messages

The owner-supplied `inVehicle_Cal_Success` capture contains older pre-recovery
data, including `ReportCalibrationState- 0` and `NoCalibration`. Those earlier
entries must not be attributed to the final successful boots. The two later
boot sections, identified by boot counters **118** and **119**, both report
`ReportCalibrationState- 2` and have no `NoCalibration` or
`evSTARTUP_FAULT_TIMEOUT` entry within their respective captured sections.

| Later boot | Calibration report | HMI ready | Subsequent operating state |
|---|---|---|---|
| 118 | State `2` at 5.789 s | `evHMIReady` at 24.580 s | `Accessory (0x7)` at 25.118 s |
| 119 | State `2` at 5.766 s | `evHMIReady` at 20.928 s | `Accessory (0x7)` at 20.928 s, then `LocalInfotainment (0x8)` at 57.075 s |

The later logs still contain SBAT NVM initialization, Leo-switch initialization
and u-blox UART-read failures, plus `Failed to read RVS_STATUS from NVM` and
invalid BCM protokey-seed messages. A shutdown-animation failsafe timeout also
appears in the last captured operating cycle. These were not demonstrated
to block the recovered radio, and no fixes for them were established by this
calibration operation. Neither USB ADB restoration nor the final MEC value
was measured as part of the successful MDI2 verification.

#### Later bench UART follow-up 2026-11-14

The subsequently supplied `benchMCU_bootsRadio_postVehicleCAL.log` covers
three MCU boot sections, counters **121–123**. It contains **zero
NoCalibration entries**. Boot 121 reports calibration state `2` at 5.956 s,
and boot 123 reports state `2` at 6.353 s. Boot 122 has no calibration-state
report in the captured section. These findings support persistence of the
restored calibration while capturing startup/shutdown activity during the
vehicle-to-bench transition. The owner subsequently clarified that a factory
reset was observed after moving this radio in both directions, bench to
vehicle and vehicle back to bench. The later bench reset/startup events must
be interpreted with that observed factory-reset context, rather than assumed
to be unprompted faults during otherwise steady operation.

| Boot | Observed sequence / actual messages | Interpretation |
|---|---|---|
| 121 | `Controlled reset` at 13.147 s; unmount requested at 13.192 s; HMI ready at 20.685 s; `FAILURE DETECTED: Unmount Timeout` at 21.183 s; CSM reset follows. | A requested reset encountered an approximately 8-second unmount timeout. Subsequent HDLC TX timeouts occur during the reset transition, not by themselves proof of a persistent IPC failure. |
| 122 | Reflash requests at 2.468–2.469 s; `FAILURE DETECTED: SoC Running Reset` at 2.470 s and entry to `CSM_Reflash`; startup timeout at 15.521 s; state `Propulsion (0x6)` at 15.522 s; `SoCM_SOH_Timeout Detected` at 16.721 s. | This boot did not complete the usual startup handshake in the captured interval. The reset label follows explicit reflash events; a spontaneous SoC crash is not established. |
| 123 | Calibration state `2` at 6.353 s; HmiInit at 8.896 s; startup timeout at 23.891 s and state `Propulsion (0x6)`; HMI ready only at 52.432 s. | HMI readiness arrived roughly 28.5 seconds after the startup timeout. The timeout led to Propulsion, not NoCalibration. A startup timeout alone does not prove that calibration was lost. |

The configured startup-fault timeout is 15 seconds. In boot 123 the observed
interval from HmiInit to timeout is 14.995 seconds, consistent with that
deadline; the log does not establish the underlying reason for late HMI
readiness. `Unknown PLC/SysState Message (0x66) received from J6` appears
once per boot, and boot 123 also reports
`Invalid IPC message recieved on DIAG channel`. These make SoC–MCU protocol
and lifecycle coordination useful follow-up targets; they do not prove a
particular firmware-version mismatch or a need to reflash calibration again.
The same `0x66` message also occurs in the in-vehicle captures, including the
successful boots, so it does not discriminate the bench transition or prove
a bench-only incompatibility.

The bench capture also reports RTC dates in June 2024 and 140 exact
`Unable to Transmit RTE Date/Time` messages. Cross-device chronology should
use the MCU uptime and boot sections rather than that calendar clock. No
clock correction or other live-device action was performed for this log
review. The successful in-vehicle boots 118/119 above and these later bench
startup faults are separate observations; no new calibration fix is claimed.

#### Diagnostic transfer and move-triggered factory resets 2026-11-14

The owner's identification of `EXT_DIAG` with the active calibration tool is
corroborated by `inVehicle_Cal_Success`: **989 EXT_DIAG lines** span MCU uptime
117.876–125.063 seconds, including **14 `evMode34` RequestDownload events**,
**14 `evMode37` TransferExit events**, `evMode36` transfer-data events and
`CAL_UPDATE_INIT_QUEUED` / `CAL_UPDATE_DATA_QUEUED` states. These are the
radio MCU's external-diagnostic calibration-transfer state machine, consistent
with the main MDI2 tool's 14-container write. `EXT_DIAG` is absent from
`inVehicle.log` and `benchMCU_bootsRadio_postVehicleCAL.log`. It is not itself
a factory-reset or calibration-failure indication.

The owner observed a factory reset when moving the same radio from bench
to vehicle, and again when returning it to the bench after vehicle-side
calibration. The current UART captures show controlled-reset, reflash and
startup transitions, but do not print an Android user-data wipe reason or
identify which vehicle/bench message requested it. The MDI2 recovery procedure
did not send UDS 0247 user-data wipe. Its 0249 calibration clear and final
`11 01` ECU reset are distinct operations from an Android user-data factory
reset.

A relevant independent lead already exists in the retained recovery export:
recovery boot counters 47/48 used
`--wipe_data --reason=bcm_replacement`. That establishes a historical
BCM-replacement wipe path in this software, not the cause of the present
move-triggered wipes. See the
[recovery boot ledger](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).
`cal_vin_relearn_en = 1` also appears in all supplied UART captures, but an
enabled relearn calibration is not evidence that relearning or wiping ran.

The radio's internal RH850/VIP MCU, the vehicle's K9 BCM and K56 gateway are
distinct roles. Moving an intact A11 changes its external vehicle-network
environment; it does not by itself replace its internal RH850. The
bench setup is documented as an external OPU CAN emulator on X6 p9/p10,
providing wake/keep-alive traffic to the radio RH850; the emulator's exact
BCM identity/security messages have not been captured or decoded. A change
in presented vehicle/BCM identity or security context remains the leading
move-related explanation. **Static follow-up, 2026-11-14:** the Android
`gm_protokey` daemon's ProtoKey validation-failure branch was subsequently
recovered: it declares `BCM_REPLACED`, writes a recovery command with
`--wipe_data` / `--reason=bcm_replacement`, and requests recovery reboot through
PowerModing. The compared value is derived ProtoKey validation, not a literal
BCM serial/VIN comparison. A failed existing validation-record read can reach
the same branch. The PAL accepts a status-plus-16-byte-key message on security
IPC channel 9; invalid seed UART lines alone do not establish that branch.
See the [owning code trace](../platform/security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14).
The bench UART's `Shutdown request = 0 0 B R` matches the branch's reboot
control tuple, but is not unique proof of its caller. Current Android logs
and a comparison of delivered emulator/vehicle key context are still needed
to attribute each observed move-triggered wipe. The LTZ metadata and calibration state `2`
in the later bench boots remain evidence that calibration recovery persisted.

#### UART correlation with the BCM replacement code path 2026-11-14

**The captured security material changes between vehicle and bench.** The two
8-byte seed halves logged immediately before ProtoKey status `1` were
compared in memory. Vehicle boots **118 and 119** report the same pair;
bench boots **121 and 123** report the same pair; **both halves differ between
the vehicle pair and the bench pair**. Thus the logs establish a stable,
environment-dependent security input rather than only missing/invalid BCM
responses. The values, checksums and hashes of those values are not retained
here. The exact 17-byte security IPC message was not independently captured.

| Capture / boot | MCU uptime | Event and code correlation |
|---|---:|---|
| Vehicle 118 | 7.210–7.212 s | Both seed halves are taken from cache, then ProtoKey status `1` is transmitted to the SoC. |
| Vehicle 119 | 7.253–7.254 s | Both halves are taken from GMLAN, then status `1` is transmitted. Values match vehicle boot 118. |
| Bench 121 | 7.114–7.116 s | Both halves are taken from GMLAN, then `J6_prv_ProtoKey:Protokey transmitued to SoC, status is 1` is logged. The spelling is as captured. Status `1` is the PAL's accepted/ready path. |
| Bench 121 | 13.146 s | `Shutdown request = 0 0 B R` exactly matches the control arguments/reason used by `gm_protokey`'s recovery requester `FUN_00103f80` when called from the replacement branch. |
| Bench 121 | 13.147 s | `Controlled reset`, `evResetRequestVIP` and `SetShutdownAndResetVIP`; RH850 then sends `IPC_ID_RequestShutdown` to the SoC. |
| Bench 121 | 13.192 s | RH850 sends `IPC_ID_RequestUnmount`. |
| Bench 121 | 21.183–21.422 s | `FAILURE DETECTED: Unmount Timeout`, followed by `CSM Reset`. The roughly eight-second unmount timeout follows the reset request; it does not identify the original wipe trigger. |
| Bench 123 | 7.687–7.689 s | The same bench seed pair is taken from GMLAN and status `1` is transmitted again. No explicit `Shutdown request` / `Controlled reset` is shown in this boot section through the last captured uptime, 162.702 s. |

The first bench accepted-key emission to reset request is **6.030 seconds**.
The traced `BCM_REPLACED` branch waits **five seconds** before its recovery
request. The extra 1.030 seconds could include IPC delivery, validation,
command-file I/O and scheduling; those components were not individually
timed. The timing is consistent with the path, not an exact callback-to-reset
measurement. Both events above use the same MCU uptime base, so the
comparison does not depend on the stale RTC or UART USB receive latency.

This produces a coherent static/runtime chain: a different accepted security
context is reported after moving to the bench; the SoC later issues the
same `0, 0, BR` request used by the Android replacement-wipe branch; RH850
executes the controlled shutdown/reset; a later boot reports the same bench
context without another recorded reset request. It supports the owner's
factory-reset observation and the new-environment validation-record model.
It does not make `BR` a unique caller identifier or directly show the Android
validator returning `2`, `bcm_replaced`, or the recovery command file on
that boot. Those remain the missing direct attribution records.

The vehicle capture does **not** contain an equally complete reset-request
sequence: boot 118 shows shutdown completion and unmount at 87.772–87.786 s,
but no captured `0 0 B R` request preceding it. Older vehicle boot 117 instead
has repeated invalid-seed/status-`3` messages, which the PAL does not forward
as a ready key. Do not equate those messages with the accepted-key validation
failure path. `inVehicle.log` is the first **1,262 parsed lines** of
`inVehicle_Cal_Success`; it is overlapping evidence, not a second independent
occurrence of those events.

The function-level decision and recovery-command construction are maintained
in the [security code trace](../platform/security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14).

#### Partial post-factory-reset Ethernet capture 2026-11-14

The owner supplied `radio-en12-20261114.pcapng` as a post-factory-reset boot
capture, with early radio traffic missed while T1 polarity was corrected.
The file contains **615,366 packets** over **391.771 seconds**. The first
radio-associated source appears at capture +186.628 s; earlier packets are
discovery queries from the other source. This gives approximately **205.143
seconds of radio-visible traffic**, not a measured power-on-to-boot interval.
There is no synchronized Android uptime anchor for this capture.

| Captured evidence | Result / interpretation |
|---|---|
| Source attribution | One source supplies 615,336 packets, including all AVTP frames and the Android DHCP client; the other supplies 30 mDNS queries. A shared radio-side source does not identify the originating hypervisor partition for every frame. |
| VLANs | VLAN 2: 613,778 packets; VLAN 5: 429; VLAN 4: 81; untagged: 1,078. |
| AVTP | Wireshark classifies 460,333 frames as AAF across three stream IDs and 153,445 as TSCF. All three AAF-classified streams remain visible through capture end; maximum inter-packet gaps are about 0.312 s. This supports a running AVB transport, not proof of audible output or correct generic decoding of the vendor payload. |
| Android DHCP | Eight untagged DHCP Discover messages contain vendor class `android-dhcp-12`. First Discover is capture +230.839 s, or 44.211 s after the first radio frame. No Offer, Request or ACK is captured. This establishes Android-12-associated DHCP activity; it does not prove the radio's static VLAN addresses are unusable. |
| CarPlay discovery | Thirty `_carplay-ctrl._tcp.local` queries are emitted across VLAN 4, VLAN 5 and untagged IPv6. First query is capture +241.811 s, or 55.183 s after the first radio frame. They establish discovery activity, not a CarPlay listener or successful projection session. |
| mDNS responses | All 60 captured mDNS packets are queries; there are no response records or SRV advertisements. In particular, `_adb`, `_adb-tls-connect` and `_adb-tls-pairing` appear as queries from the other source, not radio ADB advertisements. |
| External peer discovery | All 468 ARP packets are requests: 408 on VLAN 5 and 60 on VLAN 4, targeting four distinct addresses. No ARP replies are captured. This describes the observed tap traffic, not a complete inventory of internal partitions or CAN peers. |
| Diagnostics / wipe reason | No TCP, UDS-over-TCP, FSA sessions, Android logs or explicit factory-wipe reason appear. The capture does not contain a decoded BCM-identity change or the message that initiated the owner-observed wipe. |

The generic dissector also labels the first TSCF payload as ACF LIN but warns
`expected: 1024 bytes, available: 12 bytes`. That is insufficient to claim a
real LIN transaction, malformed radio firmware or carried BCM identity; the
vendor AVTP framing needs validation before interpreting that control payload.

This capture supports Android networking and AVB activity after the reported
factory reset. It does not establish a fresh OS installation, a new Android
build, the earlier wipe's cause or a complete reboot timeline. An Ethernet
tap also does not expose the OPU emulator's CAN exchange with RH850. Testing
the BCM-context hypothesis requires the current Android recovery wipe reason
and a comparison of the emulator/vehicle identity-security CAN traffic.

#### Synchronized power-on follow-up 2026-11-14

A later owner-controlled power-on was monitored with the T1/USB adapter
already powered and both Ethernet and receive-only RH850 UART readers armed
while the radio was off. Relative to the first received UART bytes, early
SoC power-level responses appeared at +0.966/+1.286 s, the first radio
Ethernet frame at +3.085 s, AVB at about +3.9 s, calibration state `2` at
+5.872 s and HMI ready at +21.172 s. Ethernet and AVB activity therefore
preceded HMI readiness. The measurement does not identify which component
initialized Ethernet or prove that AAOS had not started before the first
packet. The detailed timing and clock limitations are maintained in the
[existing boot-timing record](../runtime/boot_timing.md#synchronized-rh850-uart-and-ethernet-power-on-measurement-2026-11-14).
No raw capture files were written.

The subsequent [GHS code analysis](../research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#ethernet-initialization-and-guest-ownership-code-trace-2026-11-14)
located PCI Ethernet passthrough registration, generic Intel NIC reset/link/
ring setup and the `GmEth` resource granted to Android Guest1. It did not
identify the producer of the first VLAN-2 AVTP frames or establish that an
early Android kernel networking path was absent.

**Audio follow-up, 2026-11-15:** live T1 AAF payloads were subsequently
extracted while a known MP3 looped in the radio's player. The 768-byte
stream carried six-position 48 kHz / 16-bit big-endian PCM, with player
audio in positions 1/2. Decoded waveform comparisons exceeded 0.9999 in
aligned reference windows. macOS-playable WAVs and audio-only raw PCM were
created; no network identifiers or packet files were retained. See the
[owning audio extraction record](../platform/avb_audio_transport.md#3-live-avtp-player-audio-recovery-2026-11-15).

See the [main-client recovery notes](../tools/mdi2_client/docs/CALIBRATION_WRITE.md#cleared-a11-recovery-2026-11-14)
for the unchanged CLI limits. Raw UART data and private adapter/vehicle
identifiers are not copied into this repository.


#### UART checksum scope 2026-11-15

In-memory comparison of **378 logged seed-buffer/checksum records** matched
**Adler-32** over the associated eight-byte buffers. Eight zero bytes give
Adler-32 **524289** (`0x00080001`), consistent with the logged zero-buffer
case. Seed values, derived values and per-device checksums are not retained.

This identifies a logged buffer checksum, **not** the UDS `27` seed-to-key
algorithm, a secret key, or an accepted diagnostic response calculation.
The BCM ProtoKey input, its diagnostic checksum and a UDS SecurityAccess
challenge are separate objects. The available UART observations do not
recover the protected seed/key math. See the existing
[seed/key and calibration signatures reference](../research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
for the separately traced DPS/backend CMAC path.

#### Audio usage follow-up 2026-11-15

The known-MP3 recovery was followed by the installed AAOS Audio Probe.
All **16 public Android 12 usage IDs** produced live T1 PCM. Media/game/default,
assistant/accessibility and call/signalling/ringtone used positions 1/2;
navigation used position 3; alarm, notifications (including deprecated variants)
and sonification used position 4 in the same 768-byte AAF stream. Media
left-only/right-only isolated positions 1/2. The 128-/512-byte streams stayed
silent. These are logical transport positions, not Bose speaker labels.

All five advertised system usages (17, 1000–1003) were attempted using the
system setter. Their effective IDs matched the request, but each returned
`focus_result=0`; no signal was emitted and no wire mapping is established.
The probe was built, installed, run on the radio, and visually checked;
playback was stopped after testing. No privileged policy was changed.

Audio was tagged **VLAN 2 / PCP 2**, with EtherType `0x22f0`; accompanying
gPTP was **untagged** (`0x88f7`). The empirically validated active packing is
48 kHz signed PCM16 big-endian, 64 frames × six positions per payload.
Generic AAF channel fields conflict with that packing; control/TSCF semantics
remain unresolved. A 48 kHz transport does not establish Bose maximum rate.

The complete usage-ID/bus mapping, stream inventory, raw header layout,
synthetic PCM sample and replacement-endpoint limitations are maintained in
one [VLAN 2 reference](../platform/avb_audio_transport.md#4-vlan-stream-inventory-and-packet-layout).
These audio findings do not change diagnosticsd authorization, establish
GHS ownership of the first packets, or demonstrate amplifier playback.

#### GWM boot-target and GM 8180 follow-up 2026-11-15

Owner-authorized tests evaluated the GWM `FDF0` boot-target lead on the
isolated GM bench radio. A temporary ADB forward reached the same
`diagnosticsd` listener using custom TCP framing, tester F4 and target 0084;
this is an Android Ethernet diagnostic path, not a CAN transaction. The radio
clock was synchronized against the Mac before time-sensitive observations.

Extended session `10 03`, the documented FF31 seed path and its 12-zero-byte
level-1 response succeeded. No real seed/key calculation was attempted.

| Request / state | Final response |
|---|---|
| `22 FD F0`, default / extended / unlocked extended | `7F 22 31` (the initial read first returned responsePending) |
| `2E FD F0 04 00`, unlocked extended | `7F 2E 31` |
| `2E FD F0 04 01`, unlocked extended | `7F 2E 31` |
| `2E FD F0 04 03`, unlocked extended | `7F 2E 31` |
| `2F 81 80 03`, separate unlocked extended test | `7F 2F 31` |
| `3E 00` to alternative target `0080` | `7F 3E 31` |
| Restore default `10 01`, canonical target | `50 01 00 64 01 F2` |

Live Android logs show missing `DIDFDF0Handler` for the DID requests and
missing `IOCID8180Handler` for I/O control, in both common and MY22 namespaces.
The latter request was recognized natively as `DIAG_CPID_CONTROL`; it did not
fail because the service was converted to UNKNOWN. NRC 31 here does not
establish that the RH850 rejected either identifier over CAN.

Android boot identity was unchanged across both write experiments. A
receive-only 115200-baud UART observer saw **238 bytes** during the 8180 test
and no matching ELK/reset event in that bounded window. The earlier FDF0
observer had a shutdown/descriptor cleanup error, so it supplies no reliable
negative UART conclusion. Neither observation establishes complete MCU
silence or proves every partition remained unchanged.

No positive write/control response, reboot or ELK entry was observed; no
calibration transfer, flash erase or persistent Android configuration edit
was performed. The default diagnostic session was restored, UART reader
closed, and temporary ADB forward removed. The MDI2 was not connected; the
owner is awaiting a USB CAN adapter after unreliable MDI2/CAN communication.
CAN-side testing was pending at this checkpoint. The2026-11-17 follow-up below
records two rejected direct-CAN candidates.

The [owning firmware analysis](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15)
records the matched cleanroom APK, corrected VIP payload load map and compiled
selector-8180 → one-byte E0 control request. That compiled branch narrows the
next CAN test; it is not a verified universal boot-target command.

**Direct-CAN ELK follow-up,2026-11-17:** Extended session and profile01 granted.
`2F 81 80 03 → 7F 2F 31`; separate native-label candidate
`AE 81 80 03 → 7F AE 11`. Neither produced a positive ELK control response.
No ELK boot was established; no ADB boot comparison or new UART evidence was
available. Default session restored. The compiled internal sender alone does
not establish an external CAN invocation path. The owning firmware analysis
above records the callback chain. Subsequent static tracing resolved this
rejection: parserD1498 callsCC95E against the221-entry CAN identifier table;
8180 is absent, so NRC31 is returned before callback dispatch. None of the39
configured2F short-term-control callback entries points to57BC8. Normal I/O
forwarding uses transaction kind5; ELK8180 uses the distinct kind4 adapter.
This is not a missing security or power-mode prerequisite for the tested request.

**F000/8180 follow-up,2026-11-17:** A distinct routine path was subsequently
traced and exercised: `31 01 F000 8180 03`. T1/profile01 returned7F3131;
direct CAN profiles01/09/0B/0D returned7F3133. Immediate RAM readback under0D
showed the routine's required DCM access mask satisfied (session4, security40),
but its separate application-security word FEBD0CF8 remained0. Temporarily
setting that word to1 with verified readback yielded `7101F000818003`.
The original zero word was restored and verified immediately afterward.
UART recorded `Diag Elk Reboot Req`, `Elk Reboot Response 0`, controlled reset
and a new VIP boot; the display turned off and ADB disconnected. T1 reconnect
timed out. USB subsequently enumerated titan_gm_my22 (8087:09EF), and
`fastboot getvar version-bootloader` returned `kernelflinger-07.02-userdebug`,
confirming SoC ELK execution. Three subsequent variable queries timed out;
repeat-command reliability and write permissions remain unverified.
The owning firmware analysis above records the dispatcher,
two separate access gates and post-reset observations.

#### ABFT handler and validation-only follow-up (2026-11-15)

Current Y175 tracing resolves more than a generic background-file callback:

- `diagnosticsd` RVA2ade0 copies the routine payload into a string; RVA34eb0
  forwards it and the subfunction to the registered HIDL handler.
- Current gm_update_engine RVA64330 is
  `DiagnosticsHandler::handleAuthorizedBackgroundFileTransferRequest`.
  Start1 calls `onTransferAuthorized(true,string)`; Stop2 calls it withfalse.
  The previous51910 attribution is not this function in the inspected Y175
  binary. Its hash remains `0f47923bf545394b9f1cf1d229061158af2c20c4038aa33e8c77e76ef6181f73`.
- `DaemonState::onTransferAuthorized` RVA753b0 checks BootControl and the
  update-attempter instance, parses an InstallPlan and calls applyNewPlan on
  parse success. Stop calls `cancelUpdate(true)`; it is not a read-only query.
- InstallPlanUtils::parse RVA3bad0 uses JSON. It requires `filePath` and
  `partNumber`; iterated module entries require `modID`, `fileName`,
  `fileSize`. Module IDs are parsed as hexadecimal strings, sizes as decimal
  strings. Recognized optional fields include source_slot, localFile,
  downloaded and installed. Source-slot information participates in A/B
  selection. This is an update/install plan, not a proven arbitrary file copier.

Only mandatory-field rejection probes were sent, with explicit guards
preventing any other RID and with no partNumber/module list/source_slot.
The static missing-field branches return before applyNewPlan. No Stop was
sent, no complete plan was submitted and no transfer/install was attempted.

| Current profile / request | Result | Evidence limit |
|---|---|---|
| Extended, level05,0475 start with `{}` | `7F 31 31` | No matching native parser log retained; rejection is not proof of parser reachability. |
| Extended, level05,0475 start with only a generic temporary filePath | `7F 31 31` | Intentionally lacks partNumber; no actual payload file supplied. |
| Extended, level05,0475 results | `7F 31 22` | Reproduces earlier results outcome, not a transfer test. |
| Extended, level09,0475 start with `{}` | `7F 31 33` | Level09 does not imply superset permission over level05. |

Both security grants succeeded using the already documented bench exchange;
default session and temporary forwards were restored. A complete plan still
requires module-writer, signature and slot-selection review before a
non-clearing experiment. Calibration clearing remains forbidden.

#### Diagnostic control coverage audit 2026-11-15

**The complete sweep was a DID-read enumeration, not an exhaustive control
exercise.** The initial static/community audit performed no live operations.
A later authorized bounded bench pass exercised 24 of 25 IOCID IDs. The first
frequency tests were release-only; a subsequent pass verified actual FM/AM
source changes and tuning with readback/rollback. See the live results in the
[protocol reference](diagnosticsd_protocol.md#live-bench-controls-2026-11-15).
USB override discovery was also tested, without demonstrated application;
the [updater reference](../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15)
owns that experiment. Calibration clearing is forbidden; no programming or
reboot was performed in these passes.

| Surface | What was exercised | What remains untested/unproven |
|---|---|---|
| SID22 DID reads | All 65,536 IDs in extended session / level09: 135 positive, 65,376 NRC31, 21 NRC22, 4 NRC11; 159 candidates also checked in other profiles. | Other operations on those IDs; 136 is the later union across states after 03D8 made 4775 readable. |
| Non-calibration routines | 03D8 controlled audio/HMI/AM, results `71 03 03 D8 07`; 0248 audio-favorites reset accepted. | Not every option or precondition; 0248 option03 was a no-op and phone/nav paths returned NRC22. |
| ADB candidate0332 | 5,120 layout/profile combinations returned NRC31, followed by bounded retries. | Other ADB mechanisms or different native/controller routes. |
| DID writes | FDF0 normal/recovery/ELK layouts returned `7F 2E 31` with missing Android handler. | Catalogued permissions for F190/F198/F199/E010/F0F4 are not successful-write evidence; those write operations were not exercised. |
| I/O control | 8180 candidate returned `7F 2F 31`; later24 named IDs received bounded operations. Display, volume/EQ/balance/fader state readbacks, SWC volume, FM/AM switching and tuning were verified. | Tone getters read settings, not hardware telemetry; wire correlation inconclusive. USB/media and AF accepted without verified effect; surround/DAB NRC22;4838 NRC31;4785 stub;41DE excluded. Nonzero encoder accepted but no frequency change measured in its bounded active-FM window. |
| Memory/file operations | SID23 produced security denial or pending→NRC25; SID38 ReadDir/ReadFile returned NRC11. | No memory byte or generic file writer demonstrated. Add/Delete/Replace were not attempted; 23/38 are absent from the inspected Ethernet converter map. |
| DTCs | Multiple positive replies, including reserved selectors. | Inspected native paths build zero-filled/stub buffers; replies alone do not prove functional DTC storage/control. |
| Programming/update | 0475 results→NRC22; later mandatory-field-only JSON starts→NRC31 at level05 and NRC33 at level09. Static install-plan JSON schema recovered. | No complete plan, transfer or installation submitted; parser reachability not proven by the rejection replies. Module-writer/signature/slot behavior still needs review. |

The [IOCID inventory](diagnosticsd_protocol.md#implemented-iocid-inventory-and-candidate-controls-2026-11-15)
identifies UI-key injection, fixed faceplate events, tones, equalizer,
source and frequency controls. The live pass verifies specific working
paths rather than treating positive responses as sufficient evidence: AF,
source NONE and the unsupported4785 handler illustrate that distinction.
Do not blanket-test routine-results: 0249's results implementation itself
clears calibration data.

The [updater import analysis](../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15)
owns the privileged file mover and its discovery/caller gates. Root ownership
of diagnosticsd does not make the connected client a root shell. Existing
UID2000 Binder experiments hit diagnostic permission checks; debugger attach
to the root daemon returned `Operation not permitted`. FSA RemoteModuleHMI,
NetworkAccessManagement and DisplaysCoordination expose separate partially
mapped control surfaces, documented in the [FSA reference](../platform/fsa_protocol.md),
not established arbitrary-execution or filesystem-write endpoints.
