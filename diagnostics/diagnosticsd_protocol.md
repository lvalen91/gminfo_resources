# diagnosticsd — Protocol, Wire Format & Service Tables

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

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
  [concurrence-correction block](diagnosticsd_network_topology.md#vlan4--internal-ghs-fabric-diagnosticsd-forwarding-target-bench-reachability-of-the-vipuds-path-2026-10-06).

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

## Service IDs, variants and routine inventory (2026-11-14)

`10`, `27`, `22` and `31` are hexadecimal UDS **service identifiers** (SIDs),
not shell commands, TCP ports, interface-class numbers or routines themselves.
The bytes after a SID depend on that service. A DID identifies a data item;
a RID identifies a manufacturer-defined routine. Subfunctions, DIDs and RIDs
are different fields and must not be interchanged.

| Service | Meaning | Standard selector / request shape | Evidence on this T1 endpoint |
|---|---|---|---|
| `10` | DiagnosticSessionControl | `01` default, `02` programming, `03` extended, `04` safety-system diagnostic; OEM-specific sessions may exist | Default/extended accepted live; later programming-02 probe gave NRC 22 and session-04 probe gave NRC 12 |
| `27` | SecurityAccess | Odd subfunction requests a seed; paired even subfunction submits its response, e.g. `01/02`, `03/04`, `05/06` | Grants validated for odd levels 01, 03, 05, 09, 0B, 0D, 11, 13, 15; 5F seed request ended in NRC 25; access rights differ by level |
| `22` | ReadDataByIdentifier | No subfunction: `22 <DID high> <DID low>`; e.g. `22 F1 81` | F181 positive live; F186 gave DID-specific NRC `31` |
| `31` | RoutineControl | `01` start, `02` stop, `03` request results, followed by a two-byte RID and optional parameters | Native/Java handlers are mapped below; later controlled starts and results are recorded in the resolution and final-clear sections |
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
| `0249` | `RID0249Handler::handleResultsRoutine` at `0x2ad00` calls `CalibrationAccessor::clearAllOverrides()`; start at `0x2acc0` forwards via virtual slot `0x38` to that same results handler. Stop at `0x2ace0` constructs a positive response. | Local start/results path attempts to clear calibration overrides; failure maps to conditionsNotCorrect. **Request-results is not inherently read-only for this implementation.** A later direct-T1 start completed the clear; see the final-clear section. This does not prove that every captured CAN/VIP invocation takes this Android handler. |
| `0475` | `RID0475Handler::handleRoutine` at `0x2ade0`; start/stop/results wrappers delegate through `CorePluginManager::getRegisteredInternalServiceManager()`. Further tracing on 2026-11-14 resolves the registered manager to `DiagnosticsInternalService`: its secondary vtable at `0x635d8` starts with thunk `0x34fc0`, which adjusts the object pointer and jumps to `handleAuthorizedBackgroundFileTransferRequest` at `0x34eb0`. | The native path is an authorized background-file-transfer callback. The constructor initializes the HIDL callback pointer to null; `setBackgroundTransferHandler` (`0x34c40`) installs it. The transfer method calls the installed handler at virtual slot `0x68`, or returns internal code 7 when none is installed. The callback client was later identified in gm_update_engine. Its reference implementation handles start/stop, not results. A level-05 results query returned NRC 22; no transfer start or stop was sent. |

The RID0249 constructor at `0x2ac70` points to a vtable at `0x62910`; slot
`0x38` resolves to `0x2ad00`, corroborating the start-to-results forwarding.
No call to either routine was sent during this static analysis.

`generateDIDHandler(int)` at `0x2f5a0` contains dedicated cases for `5735`,
`573D`, `F081`, `F084`, `F180`, `F181`, `F182` and `F1B0`. This is a local
handler inventory, not a complete accessible-DID list. Unknown IDs can take
other dispatch paths, and finding a handler does not establish live access.

### Java handler inventory verified against the live APK (2026-11-14)

`DelayedWKSApp.apk` supplies the Java diagnostic server and MY22/MY23 DID,
RID and I/O pipelines. Its live `classes.dex` and `classes2.dex` differ from
the Y181B reference; `classes3.dex` matches. Consequently Java findings were
checked directly against the live APK, read into memory without saving a new
APK or raw capture. Both live and reference `classes2.dex` define handlers for
154 distinct named DID IDs and the 11 RID IDs below. These are class-definition
inventories, not proof of active registration, accepted payloads or live execution.
Additional handlers can be supplied through other routing/loading paths.

| Java RID | Direct live-code evidence; later live outcomes are recorded below |
|---|---|
| 0209 | Start checks calibration programmed state. |
| 021E | Checks authenticated system power mode; reference code includes VIP pass-through request/response handling. |
| 0247 | Start calls vehicle-settings restoration and `wipeUserData`. |
| 0248 | Start deletes GM favorites and calls per-user `resetRadioFavorites`. |
| 0254 | Start calls LCM resource `deleteAllRecords`; live DiagLcmResourceAccess code operates on the LCM licensing database. |
| 0260 | Start calls LCM resource `resetDownloadCounters`. Live DiagLcmResourceAccess selects a License.OwnerType and updates `downloadRetryCounter` / `transferRetryCounter` in the LCM database. This is licensing retry-counter control, not evidence of odometer or wear-counter access. |
| 0300 | Response-building handler exists; operational meaning remains unverified. |
| 03D8 | Start includes audio/HMI control. Its explicit request-results handler reads `getIsMessageStarted` and generates a response. |
| 0405 | Start broadcasts `com.gm.android.action.REGISTRATION_START`. |
| FF00 | Start can call `diagEraseOverrideFile` and `handleEraseMemoryRequest`. |
| FF01 | Start reads programmed state/security level and checks authenticated power-mode / protected remote-programming monitors. |

The live `AbstractRIDHandler.handleRequestResultRoutine` throws an exception;
03D8 is the explicit Java results override found among these named handlers.
The separate native 0249 results path can clear overrides, and native 0475
results delegates to the background-transfer callback. A blanket RID-results
sweep is therefore neither a reliable support inventory nor uniformly read-only.

The native Java-pipeline constructor at `0x2c090` selects its forwarding set
using `getElectricalArchitecture`. In the inspected binaries that getter at
`0x3f9d0` returns constant 1 and the string getter returns `globalb`; this is
not a live CAN-selected architecture. The set contains native IDs 1, 2, 4, 6,
7, 8, 9, 10, 11, 12, 13, 14, 16, 21 and 1000. This forwarding set is distinct
from the narrower Ethernet wire-SID conversion map.

Direct live-code inspection also resolves the Android API permission helper:
`DiagnosticServiceImpl.requestDiagnosticData` calls `permissionCheck`, which
uses `Permission.checkVINPermission` or `checkVehInternalPermission`. Those
helpers check `android.car.permission.CAR_VENDOR_EXTENSION` and
`com.gm.diagnostic.permission.READ_VEHICLE_INTERNAL_INFORMATION_PROTECTED`
respectively, through `Context.checkCallingOrSelfPermission`. Exact selector
branching and a callable UID-2000 request path remain unverified. The attempted
package-shell permission query returned `Unknown command: check-permission`;
it did not establish a grant or denial.

### Implemented IOCID inventory and candidate controls (2026-11-15)

**Static inventory, not a live control sweep.** The current Y175 cleanroom
DelayedWKSApp is byte-matched to the previously inspected radio APK: SHA-256
`5916ad9f7d40d2683e4dac49b7cc5086104dd27042c7fc32716fc3094288e241`.
Its `classes2.dex` defines **25 distinct named IOCID handlers** in the common
IOCID namespace. The nested 41D8 SimulatedKeyEvent class is not a 26th ID.
The failed `2F 81 80 03` request does not test these other implementations.

| Handler family | IOCID IDs | Evidence limit |
|---|---|---|
| Direct AbstractIOCIDHandler subclasses | 41D8, 41DA, 41DB, 41DE, 41E7, 41EB, 41ED, 4428, 4478, 4781, 4785 | 41D8/41DB key simulation, 41DA display patterns, 41DE OnStar actions and 41E7 volume traced below; remaining IDs not recovered here. |
| Audio-channel test tone | 41E2, 440A, 440B, 440C | 41E2 selects left-front; other subclass/channel assignments need confirmation. |
| Equalizer | 41E9, 41EA, 41EC | Classification by superclass; payload/effect not exercised. |
| Audio-source update | 42AD, 5812, 5814 | Classification by superclass; source and state prerequisites unresolved. |
| Event injector | 43FC | Fixed-key faceplate/encoder events, not general command execution. |
| Frequency update | 4424, 4426 | Classification by superclass; ranges and tuner prerequisites unresolved. |
| AbstractNRCIOCIDHandler | 4838 | Do not assume a functional control from the class name. |

**41D8 reaches Android input events.** `IOCID41D8Handler` reads one short-term
payload byte and maps it to a KeyUpdownEvent. Selected mappings are:

| Selector byte | Android keycode | Meaning |
|---:|---:|---|
| 0A / 0B | 88 / 87 | Media previous / next |
| 0C | 3 | Home |
| 0D | 66 | Enter |
| 11 | 4 | Back |
| 12 / 13 | 24 / 25 | Volume up / down |

The support check is `key != 0`; all 19 mapped selectors satisfy it. Their
sources are FACEPLATE or ANY; none uses SOURCE_SWC or mute key164. The
implementation sends down/up events 300 ms apart through the diagnostic
input resource and the mapped hardware source. It does not provide arbitrary
text, coordinates or a direct settings setter. It returns an empty response
for an unmatched selector, and its final "Unable to find key event simulation"
log is emitted unconditionally, including after a matching event. Actual UI
observation or paired event logs are needed to establish an effect.

**41DB simulates steering-wheel keys.** Its selector map is 01 favorite-up
(key137), 02 favorite-down (138), 03 volume-up (24), 04 volume-down (25),
05 speech (231), and 06 mute (164). It uses SOURCE_SWC and the same fixed
300 ms down/up simulation; it does not implement a held key. Candidate
`2F 41 DB 03 06` requests a mute tap, **not live tested**, and cannot reproduce
a ten-second mute hold by itself.

**Input injection uses vendor APIs, but the traced SWC path returns to Android.**
The FACEPLATE path runs through InputDiagnostics/InputManager to PanelDiagnostics
and `vendor.gm.panel@1.0::IPanelDiagnostics`; its native downstream behavior is
still untraced. SOURCE_SWC runs through PropertyInputDiags to VHAL
`HW_KEY_INJECT`, with integer values `[key, 1/0]` for down/up; supported keys
are 24, 25, 164, 231, 137 and 138. `HW_KEY_ENABLE` is `0x21410163`;
`HW_KEY_INJECT` is `0x21410165`.

In Y175 VHAL, `KeyInputPropertyManager.setPropertyFromClient` (`0x5D0E0`)
reaches `sendKeyEvent` (`0x5CBF0`), local handler posting (`0x5CE67`),
`onHandlerMessage` (`0x5C180`) and `setPropertyFromVehicle` (`0x5C2B6`).
`GMVehicleHal` (`0x332C0`) writes its store (`0x332FC`) and calls `doHalEvent`
(`0x3332B`). Mute 164 maps to internal 1003 and speech 231 to 1002; outbound
Android-facing properties are `0x11410A30` for special keys and `0x11410A10`
for others. **No VIP/CAN transmit appears in this traced path.** HW_KEY_ENABLE
controls local reporting. Local held/repeat state is not evidence of a
physical VIP input, and the fixed Java 300 ms tap remains unchanged.
VHAL SHA-256:
`3dcd9acccfa30aef7f5adfff0066dd69c71a163aa82b027b5e1359137fac7a88`.
Framework provenance: `info3.jar` SHA-256
`186de0cb65191c0d0711de58c0ddc7a16ac1c131336385042f837d7a75274497`;
`vendor.gm.vehicle-V1.0-java.jar` SHA-256
`17b23ca107a2b2d7607dd4b4d83e8ff380059ccbe56fb3b1318c2bf44ba2b741`.
No live injection was tested in this analysis.

**43FC injects the GM tune-encoder key.** Its subclass supplies keycode 245,
resolved by `gm.view.GMKeyEvent` as `KEYCODE_GM_TUNE_ENCODER`. The base reads
a one-byte step count, applies its signed conversion for values above 128,
sets input status and sends down/up 20 ms apart with SOURCE_FACEPLATE.
The named key resolves the earlier encoder uncertainty; live tuner behavior
and native delivery are still unmeasured. Return-control actively injects the
inverse stored step count and clears input status; it is not a no-op.

**Other traced controls have different consequences.** 41DA selects display
test patterns (normal, SMPTE, Philips or Tux). 41E7 saves the original volume
and restores it when releasing control. 41DE issues OnStar broadcasts and
contains an emergency-call branch; exclude it from benign UI experiments.
None of these static paths establishes current wire reachability.

**41E2 controls a diagnostic tone.** Its superclass acquires speaker-channel
access and enables a tone; the subclass selects LF and calculates frequency
as `50 * payloadInteger + 25`. Return-control releases speaker access and
disables the tone. Accepted payload width/range and audio-service prerequisites
remain unverified; this is not ready for an unattended tone sweep.

Handler-level candidate shapes are `2F 41 D8 03 <selector>` and
`2F 43 FC 03 <steps>`, with `2F <ID> 00` for return-control. **These were not
sent in this audit.** Active registration, converter behavior, per-ID security,
length and session/state checks must be confirmed before calling them working
wire recipes. Control parameters are 00 return-control, 01 reset-default,
02 freeze and 03 short-term adjustment. Generic reset-default throws a stub
exception; generic freeze sets user lockout true. Generic return-control is
empty, while subclasses can implement real cleanup. Neither an empty reply
nor a generically named results/reset operation establishes harmlessness.

### Live bench controls (2026-11-15)

The subsequent authorized bench pass used USB ADB transport to forward the
radio's TCP 49156 endpoint, tester `0x00F4`, target `0x0084`, extended session
and the documented level1 exchange. Each connection returned to default
session; temporary forwards were removed. No calibration clear, programming
request or reboot was issued. Earlier "not live tested" statements above
describe the static audit; the following results supersede them for these
specific payloads, not every selector/state/security profile.

| IOCID | Live operation and evidence | Limit |
|---|---|---|
| 41DA | Selectors00/01/02/03/00 accepted. SMPTE, Philips and Tux produced distinct 2400x960 screencap hashes; normal restored the exact baseline hash. SystemUI emitted DISPLAYCONTROL and confirmation broadcasts. Return-control accepted. | Full visual display control demonstrated without reboot. |
| 41E7 | Volume 15 -> 14 -> 15, verified with DID41E7; return-control restored15. | Diagnostic group volume, not every audio group. |
| 41E9/41EA/41EC | Each EQ value 0 -> 1 -> 0, verified through the matching DID after adjustment and release. | DSP/speaker output not independently measured. |
| 41EB/4781 | Balance/fader each 0 -> 1 -> 0 with matching DID readback and release. | Does not establish Bose physical-channel routing. |
| 41DB | Selector04 volume-down then03 volume-up yielded15 ->14 ->15; release accepted. | Android SWC input works; no sustained VIP hold/reset demonstrated. |
| 41D8 | Home selector0C and release accepted; Android logs showed keyCode3 processing. | Already on Home; no separate navigation transition claimed. |
| 41E2/440A/440B/440C | One-byte09 requested475Hz for LF/RF/RR/LR respectively. Each accepted; shared tone DID41E2 changed00 ->09 ->00 after release. | Getter reads Settings.Global, not generator/AMP telemetry; no acoustic or T1 channel verification. |
| 43FC | Zero-step and later nonzero01 adjustment/release accepted; Android encoder events logged. With active FM, the measured frequency stayed107.9MHz throughout that bounded test. | No successful tuning movement demonstrated. Release also injects an event; use an independent frequency snapshot/restore. |
| 42AD/5812/5814 | NONE branches accepted. Later42AD FM00/AM01 requests changed DID5812 to02/01 and DID42AD to00/01. USB5812 selector03 and MEDIA5814 selector05 returned positive, but source readback stayedFM. | FM/AM switching verified; USB/media playback transition not demonstrated. DAB42AD selector02 returned `7F 2F 22`. |
| 4478 | Same-value00 and attempted01 AF enable accepted; DID4478 remained00. Repeated with FM active, with the same result; release left00. | Positive reply did not establish AF mutation. |
| 41ED | Adjustment00 returned `7F 2F 22`; DID read `7F 22 22`; release accepted. | Surround unavailable/current precondition unsatisfied. |
| 4428 | Adjustment00 returned `7F 2F 22`; release accepted. | DAB inactive/current precondition unsatisfied. |
| 4424/4426 | After selecting the corresponding band: FM87.7 ->87.9 ->87.7MHz (`2242 ->2256 ->2242`); AM530 ->540 ->530kHz (`0212 ->021c ->0212`), verified through matching DIDs and return-control. | Initially both getters were0000 when the diagnostic source view wasNONE; that is not a valid hardware-frequency snapshot. |
| 4785 | Adjustment00/release accepted. Current code explicitly says LVM/PDR unsupported and returns positive. | Stub, not functional capability evidence. |
| 4838 | Adjustment00 returned `7F 2F 31`. | Rejected stub/control. |
| 41DE | Not sent. | OnStar/emergency-call branches excluded. |

Thus 24 of 25 named IDs received a bounded operation. The first pass tested
frequency releases only; the later pass verified actual FM/AM tuning above.
This is **not** an exhaustive functional sweep.
All changed volume/EQ/balance/fader/tone states read back at baseline; normal
display and default diagnostic session were restored.

**Tone evidence correction:** current DiagAudioResourceAccessUtil calls
`GMAudioManager.enableSineGenerator((short)0,475)` and channelMute for the
selected speaker. Current info3.jar GMAudioManager forwards to GMAudioService
when available but also writes frequency/channel state to Settings.Global;
its corresponding getters read those settings. GMAudioService was present
and forwards generator calls toward IGMAudioControl, but no successful
hardware generation follows merely from DID41E2=09. Volume0 is named
`volume_dB` at the service boundary; do not assume it means zero-percent
amplitude. Current vehicleaudiocontrol contains generator and AmpProxy /
IAmpControl / IDiagnostics paths; the final transport/generator location is
not recovered here. The [VLAN2 reference](../platform/avb_audio_transport.md#6-diagnostic-tone-correlation-follow-up-2026-11-15)
owns the inconclusive wire experiments.

**Per-user playback cleanup:** the stock `cmd media_session list-sessions`
returned no sessions from the shell's user0 view while dumpsys showed user10
sessions. A bounded app_process client successfully used
`ISessionManager.getSessions(null,10)` and MediaController tokens with a
`com.android.shell` Context. Direct stop changed the tuner from PLAYING3 to
STOPPED1; the local player remained STOPPED1. A conventional
MediaSessionManager constructed in app_process failed because
MediaFrameworkInitializer's MediaServiceManager was null; direct
ISessionManager avoided that initialization dependency. The tuner accepts
`playFromUri(broadcastradio://program/AMFM_FREQUENCY/87700)`; this restored
87.7MHz with native tuner-log confirmation, then direct stop restored
STOPPED1. A user10 local-player play request left it STOPPED1. Global key
injection was not sufficient cleanup. Final default diagnostic session and
Home were restored; no calibration clear, installation or reboot occurred.

Reproducibility anchors in current `classes2.dex`: 41D8 class_def `0x14CF68`,
43FC `0x14D228`, 41E2 `0x14D188`; the 41D8 nested class is `0x12B228`.
These are DEX offsets, not executable addresses. The
[test-coverage audit](diagnosticsd_routines_and_recovery.md#diagnostic-control-coverage-audit-2026-11-15)
separates the prior live results from this inventory.

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
  **Updated 2026-11-15:** the direct-T1 enable-only retry after reboot again
  returned NRC31 with ADB unavailable. The byte-matched APK lacks
  `RID0332Handler`, and its RID factory returns requestOutOfRange for a missing
  handler. See the [post-reboot test and static scope](diagnosticsd_routines_and_recovery.md#post-reboot-direct-t1-adb-enable-trial-2026-11-15).

A complete build-specific inventory requires tracing SID conversion,
address/session/security tables, the local DID/RID factories, registered
HIDL/Binder/Java callbacks, and any external VIP/GHS forwarding endpoint.
For each item record request format, subfunction/identifier, payload, caller
and security prerequisites, backend, effects, and evidence level (static,
captured CAN, or live T1). Firmware code can expose much of this mapping;
missing component firmware or runtime registration can leave gaps. There is
no verified universal UDS request that enumerates every OEM DID/RID.

## Concurrent UART and USB-logcat correlation (2026-11-14)

A subsequent instrumented test observed both sources concurrently: USB ADB
streamed all-buffer AAOS logcat into memory, and the owner's existing UART
capture was read by append offset. No serial adapter was opened or changed,
no extra capture/log file was created, and raw payload/identifier/key material
was excluded from retained findings. The USB clock check matched the Mac.
Each phase included an approximately 11-second UART flush allowance; Android
boot identity and uptime were observed through USB independently of T1.

### Positive control versus memory/reset failures

| Request / state | AAOS diagnostic events | UART / final result |
|---|---|---|
| `22 F1 81`, default session | Local software-identification read succeeds | Positive response; no matching item event required by its local handler |
| `22 F1 A0`, default session | Native `DIAG_DID_READ`, PAL/IPC activity, IPCWrapper reports bytes read and GB response-format conversion | Matching internal SID 09 / item F1A0 event; positive `62 F1 A0` response |
| `23` one-byte read, extended session and level 09 grant | EthernetConverter converts wire SID 23 to native **`0/DIAG_UNKNOWN_SERVICE`**; a local negative response is constructed with request ID 0 and response code 17 decimal (NRC 11) | No selected UART diagnostic event; six pending replies, then `7F 23 25` at 29.991 s |
| `11 01`, extended session and level 01 grant | EthernetConverter converts wire SID 11 to the same native **`0/DIAG_UNKNOWN_SERVICE`**; the same request-ID-0 / NRC-11 response construction occurs | No selected UART diagnostic/reset event; six pending replies, then `7F 11 25` at 29.991 s |

The relevant live messages are from diagnosticsd/native_diagnostics, including
EthernetConverter, PALDiagnosticAdaptor, IPCWrapper, UDSMessagesCreator and
ResourceManager. Messages from unrelated Android components can match broad
words such as callback/reset; their presence in an all-buffer window is not
proof of association with the request. No separate controlling-app failure
was established by these traces.

**Correction to the earlier NRC-25 interpretation:** the wire value still
means noResponseFromSubnetComponent, but the directly observed failure begins
inside the AAOS native conversion path. It is not evidence by itself that a
VIP/GHS component received the intended reset/memory request and failed to
reply. A permissive session/security row does not create a missing native
service mapping. The successful F1A0 control confirms that at least one PAL/IPC
path and the UART observation can work during the same test.

For both failures, conversion to the unknown native service and local
request-ID-0 unsupported-response construction occurred within about 25–30 ms
of phase start, before the later pending/timer sequence. The logs establish
that mismatch. **Inference, not a fully traced queue/drop branch:** loss of
the original SID in the native/UDS round trip may prevent that local response
from satisfying the outstanding wire request, leaving the timer to produce
NRC 25. Do not promote this into a proven response-correlation defect without
tracing the relevant ResourceManager path.

A follow-up memory probe recorded **every received T1 frame**, including
nonmatching replies, instead of silently filtering them in the client. It
received exactly six `7F 23 78` frames (about 0.110, 5.091, 10.071, 15.051,
20.031 and 25.011 seconds), then `7F 23 25` at 29.991 seconds. No unmatched
request-ID-0 negative response appeared on the wire. The unsupported ID-0
response remained visible internally in logcat; its absence was not an artifact
of the earlier client match filter. UART had no matching SID/item event in
this follow-up, and default-session restoration again succeeded. The exact
internal response queue/correlation branch is still untraced.

PAL send-error `-16` messages also occurred during authorization/state handling
before the memory/reset request conversion. The key responses still succeeded.
Their exact return-code meaning and causal role are not established; do not
label `-16` as a memory-read, reset, or missing-controller root cause merely
because it occurred in the same phase. Likewise, a null PAL-monitor poll
warning occurred in the successful control window.

### Exact native converter map recovered statically

`EthernetMessageAccess` initialization at `0x384c0` loads a 13-pair native/wire
bimap from `0x14cf8` (104 bytes). Its recovered entries are:

| Native service enum | UDS wire SID | Standard wire service |
|---:|---|---|
| 1 | 22 | ReadDataByIdentifier |
| 2 | 2E | WriteDataByIdentifier |
| 4 | 2F | InputOutputControlByIdentifier |
| 6 | 31 | RoutineControl |
| 7 | 10 | DiagnosticSessionControl |
| 8 | 28 | CommunicationControl |
| 9 | 27 | SecurityAccess |
| 10 | 34 | RequestDownload |
| 11 | 36 | TransferData |
| 12 | 37 | RequestTransferExit |
| 13 | 19 | ReadDTCInformation |
| 17 | 14 | ClearDiagnosticInformation |
| 18 | 85 | ControlDTCSetting |

`toEnum(DiagUDSRequestID)` at `0x382b0` searches the descriptor set and falls
back to the unknown descriptor when no wire-ID entry is found. Neither 11 nor
23 is present; 24, 35, 38 and 83 are absent from this native map as well.
TesterPresent 3E is a demonstrated separately handled service, so absence from
the native map must not be generalized into proof that every absent SID lacks
any local endpoint behavior. Conversely, a mapped SID does not prove a working
backend, authorization or successful execution; the write/control rows above
were not executed by this correlation test.

### Why the unknown service is selected: startup versus vehicle state

Focused static tracing on 2026-11-14 places the failure at a compiled SID
lookup, rather than establishing a missing or stopped backend process:

| Function / data | Recovered behavior |
|---|---|
| ELF `.init_array`, entry 7 (zero-based) | Contains `0x384c0`, the EthernetMessageAccess global initializer; initialization runs during process startup. |
| Global initializer `0x384c0` | Constructs message descriptors, inserts descriptor-set entries, constructs the fixed 13-pair bimap and registers destruction. Its recovered calls do not query CAN, vehicle state, Android properties or a configuration loader. |
| `EthernetConverter::convert(D2CMessage&)`, `0x36e20` | Calls the wire-SID `toEnum` overload at `0x36e79`, before constructing the native diagnostic message. |
| `toEnum(DiagUDSRequestID)`, `0x382b0` | Compares the SID argument against each descriptor's wire-ID field at offset `+4`; on no match returns the default descriptor at `0x66dd8`. There is no session, security or vehicle-state argument. |
| `UnsupportedRequestToResponsePipeline::processMessage`, `0x2ed80` | Sets `SERVICE_NOT_SUPPORT` and copies the incoming native service ID into the response through `setRequestServiceId`; it does not recover the original wire SID. |

Direct cross-references to the descriptor-set global `0x66a80` were limited
to initialization/helper code and the two `toEnum` lookups; references to the
bimap global `0x67008` were in the global initializer. No runtime service
registration or CAN-triggered insertion path was found in this focused trace.
This is a finding about the inspected executable, not proof against every
possible indirect memory mutation or a different firmware implementation.

Consequently, starting another backend process or supplying an ignition/CAN
state is not supported as a remedy for the observed **11/23-to-unknown
conversion**. Vehicle state may still gate services after a valid conversion,
and another CAN/MDI2 diagnostic route can have a different service catalog.
The successful mapped DID control on the same bench also shows that the
entire native bridge is not simply absent. The request reaches the local
unsupported-service fallback before any demonstrated reset/memory operation
on VIP/RH850. The exact reason that internal unsupported response does not
complete the outstanding Ethernet request remains untraced, as noted above.

This also resolves a legacy-label ambiguity: native request-data-transfer
service 10 maps to wire **34**, not to wire RequestUpload 35. Do not use older
service-description strings as the custom endpoint's wire-ID catalog. The
matching extracted Y175/Y181B code supports the static comparison; the live
11/23 conversion traces corroborate the relevant missing entries.

Both instrumented failure phases restored default session successfully.
Android boot identity remained unchanged, uptime increased, and diagnosticsd
retained its PID. The temporary host diagnostic VLAN was removed; existing
T1 ADB and the owner's external UART logger were left in place. The native
mapping result makes this endpoint a selective diagnostic bridge, not a proven
transparent replacement for the MDI2/CAN path. A further reset/memory attempt
needs an implemented route/mapping, rather than another identical unlock and
wire-SID retry.

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
[validated T1 sequence](diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).

| SID | Service | Response |
|-----|---------|---------|
| 0x10 0x01/02/03 | DiagnosticSessionControl (default/programming/extended) | `7F 10 10` |
| 0x27 0x01 | SecurityAccess requestSeed | `7F 27 10` |
| 0x3E 0x00 | TesterPresent | `7F 3E 10` |
| 0x22 0xF1 0x81/86/8A/90 | ReadDID (sw / session / sw number / VIN) | `7F 22 10` |
| 0xD9 0x00 | DIAG_INTERNAL_REQUEST | `7F D9 10` |
| 0x00 0x01 | MSG_VENDOR_START | `7F 00 10` (service 0x00 dispatched) |

---

## Calibration override scope (2026-11-15)

The proven `0249` clear and package-programming surface do not establish a
per-value UDS calibration setter. Stock packages are themselves override
modules; their verified signatures remain relevant. A Y175 PAL
`writeCalValueRequest` export was traced to a fixed-status response rather
than a calibration update. The consolidated [override reachability analysis](../research/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3d-uds-override-reachability-and-per-value-write-stub)
owns the code addresses, local `.calovride` distinction and remaining gates.

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
