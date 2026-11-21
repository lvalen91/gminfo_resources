# CAN network message reference

Initial inventory 2026-11-15; signal dictionary updated 2026-11-16.
The original A11/OPU bench baseline contains **72 standard
11-bit data IDs**: **32 confirmed harness IDs** and **40 confirmed radio IDs**.
Radio-only RX observation subsequently established the latter senders. Later
firmware-guided probes validated additional receive IDs (`53B`, `4BE`,
`4DA`, `526`), documented separately below. Five public GM Global A definitions match both
ID and length; none is yet a validated A11 signal definition. The initial
`0x1F1` power-control hypothesis was not established by isolated-frame tests:
its external field reads Run, but it was neither sufficient alone nor required
to sustain the observed state after full-loop activation.
A fresh physical-cycle test reached normal startup with only `145` and `529`,
then cleared the ProtoKey access gate using repeated `145 529 457 458`.
`529` has a verified ready bit; `457` and `458` map byte-for-byte to two seed
caches. This is the smallest demonstrated working set, not a proven minimum.
Periodic original `529` alone sustained post-boot operation for almost 12 hours.
Firmware-guided probes have additionally verified activation-request, key-present,
valet-response, folding-top and animation-status fields; minimum frequency and
the remaining configured fields are unresolved.

This document owns the message dictionary and public-source comparison.
[Vehicle network](../vehicle_network.md) owns topology and diagnostic transport;
[bench setup](../../hardware/bench_setup.md) owns wiring and adapter configuration.
The fixed bench loop is not a complete vehicle CAN model. In-vehicle research
can describe signals the emulator never exercises. Absence from this bench does
not disprove those findings or validate their application here.

## Current working recipes and limits

### Custom SXM calibration accepted — 2026-11-16

**A custom CAN calibration write succeeded.** Slot0C was rebuilt with only
`SXM_Enabled` changed true→false. A separate development-memory protocol on
standard CAN613 (request)/614 (reply) temporarily set the two VIP header-verifier
RAM words after profile01 programming entry. The custom transfer returned
`76 01`, `76 02`, `77`; immediate PEC was0000. Both temporary words were restored
to their original zero values and read back. The owner independently confirmed
that **AAOS Radio no longer shows SXM as an option**. The custom slot remains
installed. A subsequent physical supply cycle held output off10.505 seconds;
no radio CAN RX occurred during off. Full captured harness traffic plus existing
VIN inputs restored startup. Post-cycle F182 matched and all slot/error statuses
were clean. **The owner confirmed SXM remained disabled after the cold cycle.**
This is one-cycle persistence evidence. Earlier communication re-enable returned
NRC22; do not relabel that response as a successful cleanup acknowledgment.

This is not an Engineering09 grant effect, a valid SBA-ticket load, or proof
that ordinary profile01 accepts unsigned data. No calibration clear, EEPROM
change or flash patch was used. The
[owning success record](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-successful-custom-sxm-calibration-through-can613614)
contains the candidate hash, firmware trace, temporary-state restoration,
protocol acknowledgments and verification limits.



### Projection-disable follow-up accepted — 2026-11-16

After the SXM cold-cycle confirmation, a1478-byte slot0C candidate retained SXM
false and added version3 false overrides for the GIS513 Apple CarPlay and
Android Auto feature-enable calibrations. Profile01 plus the same scoped
CAN613/614 temporary-RAM intervention returned `76 01`, `76 02`, `77`, with
PEC0000 and unchanged F182 metadata. Both temporary words were restored and
verified. **The owner confirmed both projection features disappeared from the
radio UI.** No home-screen-only flag was edited. Attached-phone behavior and
cold-cycle retention of this newer candidate remain untested. The
[projection record](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-carplay-and-android-auto-custom-calibration-accepted)
owns IDs, versions, candidate hash, exact scope and cleanup limits. Later
settled readback showed all fourteen slot statuses00 and F0F1/F0F2=0000;
DTC logging/default session were accepted, while communication enable still
returned NRC22.

**Process-state clarification (2026-11-16):** later ADB checks found SXM and
CarPlay processes/services still running and SXM/CarPlay/Android Auto packages
still installed with default enabled state. UI disappearance is not evidence
of process shutdown or resource savings. The [process-state verification](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-process-state-verification--ui-disappearance-is-not-process-shutdown)
records the distinction and the Google visibility-only findings.

### Brand-zero follow-up accepted — 2026-11-16

Custom slot04/85045386 changing only GMBrand3→0 was accepted through the same
profile01 plus temporary CAN613/614 RAM method: thirteen positive transfer
blocks, positive exit77, PEC0000, original verifier words restored and verified.
Slot0C feature-disable overrides were untouched. Settled verification on
2026-11-17 found live brand GM_Brand_None, model Silverado, all slot statuses00
and F0F1/F0F2=0000. The owner confirmed the theme changed. Brand0 has not yet
had a separate physical cold-cycle persistence test. See the [theme trial](../../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3e-standalone-xml-loader-themeui-inventory-and-gmbrandscreen_resolution-live-trials).

### Stock LTZ restored after custom trials — 2026-11-17

All14 pinned LTZ containers (slots02–0F,46162 bytes) were successfully written
through CAN. All14 F182 identities matched, module statuses00 and F0F1/F0F2=0000.
Verifier RAM words remained zero. This supersedes the custom calibration set
from the feature experiments. See [restoration evidence](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-full-stock-ltz-restoration-after-feature-trials).

### Subsequent1280×768 calibration trial — 2026-11-17

Following stock LTZ restoration and the CAN factory reset, custom slot08 changed
only SCREEN_RESOLUTION4→2. Download, both blocks and exit were accepted, PEC0000,
F182 unchanged, temporary verifier words restored. Other slots remain stock LTZ.
The owner observed display tearing. Stock slot08 was restored successfully
(both blocks and exit, PEC0000), returning the set to stock LTZ; the owner confirmed normal display output
after rollback. See the [display trial](../../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#screen_resolution-1280x768-can-trial--2026-11-17).

### Google, recorder and porch-view follow-ups — 2026-11-17

Google visibility=false and navigation=false writes were accepted, but icons
remained and Google processes continued. Recorder visibility=true was accepted,
but no recorder entry appeared. RVS_PRESENT_STATUS already equals2 in source
slot08; it was not rewritten. An explicit Porch_View_Enabled=true override was
subsequently accepted with clean settled calibration statuses; UI effect is
unverified. The launcher also gates porch view by display size. See the
[trial evidence](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-google-visibility-and-recorder-follow-ups)
for exact scope and limits. Transfer acceptance alone is not UI verification.

### Direct-CAN factory-reset attempt — 2026-11-17

With stock LTZ restored, extended session and profile01 SecurityAccess succeeded.
Initial user-data reset request `31 01 02 47` returned `7F 31 22` with radio
F085=04. The prerequisite was then resolved: retain the full captured harness,
set standard CAN20D/DLC6 byte4 bits5–7 to2, preserving other bits. VIP reset-gate
FEBD3725 changed4→2 and radio F085 became02. Extended session/profile01 followed
by31010247 then returned71010247. Android logged successful customization
restoration, ADB disconnected and the owner observed the factory reset occurring.
Original20D restored afterward; no RAM writes or calibration clears used.
Final post-reset setup/completion is distinct from confirmed reset initiation.
See the [reset evidence](../../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md) for the static
handler gate, status observations and exact scope.

### Direct-CAN ELK control candidates — 2026-11-17

On stock LTZ, extended session/profile01 granted. `2F818003` returned7F2F31;
a separate `AE818003` attempt returned7FAE11. No positive acceptance or ELK boot
was established. No RAM/calibration/firmware writes or wipe were performed.
See the [ELK analysis](../../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15)
for the internal sender and the unresolved external dispatch path. Subsequent
read-only RAM tracing found API12 availability bytes both1 and the transaction
manager idle. No polled ELK request flag was found; the sender allocates and
queues a message under synchronization. No RAM-write test was performed because
no verified writable request field had been established.
Later static dispatch tracing explained NRC31:8180 is absent from the221-entry
CAN DCM identifier table, and none of the39 configured I/O-control callback
entries directly selects the ELK callback. The internal8180 descriptor is not
a registered CAN identifier; changing security/power state cannot repair this
lookup failure. Other proprietary/internal entry points remain unestablished.

### Expanded validation campaign — 2026-11-16

Calibration clearing and calibration-override clearing are prohibited **until a
genuine LTZ write has succeeded and been verified working without NoVIN or other
issues**, per the owner's clarified
restriction. Until then, do not invoke routine `0249` through any
transport or subfunction, memory-erase routines or substitute calibration wipes.
Custom calibration trials follow genuine LTZ success and demonstrated stock recovery.
The historical stock transaction helper calls `31 01 02 49` before download;
it must not be run unchanged under this exclusion.

The genuine 14-container LTZ package was located and verified against the pinned
`LTZ_REFERENCE` hashes: slots 02–0F, 46,162 unwrapped bytes. A different candidate
directory failed with `ValueError: LTZ package mismatch in slot 0B` and was not
used. Fresh direct-CAN5 F182 metadata matches the LTZ profile; metadata matching
does not prove current payload bytes or recovery through the replacement transport.

| Direct CAN5 probe | Current result / boundary |
|---|---|
| Testers F1 and F2, `14DA80Fx` requests / `14DAFx80` replies | Default/extended sessions and TesterPresent accepted on both routes |
| `22 F181`, both testers | Positive, 18-byte UDS response |
| `22 F182`, both testers | Positive, 200-byte response containing 28 records |
| `22 F0F1`, `22 F0F2`, both testers | Positive; each returned status bytes `0000` |
| `22 F1A0`, both testers | Positive; observed read-only value FC; no MEC write sent |
| `22 F085`, both testers | Positive with 00 from the radio target; this is not a separately addressed BCM read or proof of the BCM programming gate |
| `22 41E7`, `41DB`, `41DA`, `42AD` | Positive single-byte readbacks; control effects not established by these reads |
| `10 02` without grant | `7F 10 22` on both tester routes |
| Level-1 grant with TesterPresent retained throughout redaction interval | Grant accepted; `85 02` → `C5 02`; `28 03 01` → `68 03`; subsequent `10 02` still → `7F 10 22` |
| Cleanup | `85 01` → `C5 01`, default session accepted; explicit `28 00 01` returned `7F 28 22`; subsequent normal radio CAN traffic observed (38 standard IDs in the checked window) |

An initial post-grant probe waited 5.2 seconds without TesterPresent to avoid
the capture redaction window. Its session-expiry confound invalidates the
`7F 85 7F` / `7F 28 7F` results as active-extended-session capability evidence.
The repeated probe above sent suppress-response TesterPresent throughout that
interval. No calibration-clear, RequestDownload or TransferData request was sent.

Repeating the granted CAN5 preparatory sequence after a fresh `529` Off update
logged `evPowerModeOff` and LocalInfotainment; programming entry still returned
`7F 10 22`. Radio-target F085 remained 00. Run was restored afterward. Thus
the tested infotainment power-mode change alone does not satisfy programming
entry, and the radio F085 read cannot substitute for an actual BCM response.

Direct T1 access was restored using a separate VLAN-4 interface on en12;
the existing VLAN-5 interface was retained. No private endpoint values are
included here. Packet capture was stopped before authentication; CAN/UART
payloads were redacted during the private exchange while ACK operation
continued. The diagnostic session was kept active during each probe.

| Same-operation transport comparison | CAN5 / tester F2 | Direct T1 / tester F4 |
|---|---|---|
| Read F182 | Positive, 28 records | Positive, 200-byte reply |
| Read radio-target F085 | `62 F0 85 00` | `7F 22 31` |
| Granted `85 02`, `28 03 01` | `C5 02`, `68 03` | `C5 02`, `68 03` |
| Subsequent programming `10 02`, no excluded pre-clear | `7F 10 22`, tested in On and Off | `7F 10 22`, initial On-state comparison |
| Communication re-enable `28 00 01` | `7F 28 22`; normal traffic subsequently observed | `68 00` |
| Diagnostic SWC `2F 41DB 03 04` / `03 03` | Both `7F 2F 22`; volume remained 15 | Both accepted; matching DID41E7 showed 15 → 14 → 15 |
| Diagnostic SWC return-control | Accepted | Accepted; volume restored to original 15 |

These differences demonstrate why positive T1 controls cannot be copied into
the CAN dictionary as working CAN5 controls. No result above establishes a
calibration download path without the prohibited clear operation. The genuine
package remains unchanged and custom-package testing has not begun.

#### Programming-session security-profile matrix

The priority is a genuine LTZ write using CAN5 and/or T1 without MDI2 and
without a preliminary calibration wipe. All nine previously confirmed T1
seed subfunctions were granted on **both transports**, in separate default →
extended-session exchanges; this is not every possible OEM security level.
CAN5 used physical tester F1, matching the stock client, plus functional
TesterPresent on `10DBFEF1` and physical TesterPresent during the capture
redaction interval. Both Run and Off inputs were tested. Every attempt sent
`85 02`, `28 03 01`, then `10 02`; the excluded `0249` was omitted. Cleanup
restored DTC logging/default session and the Run input.

| Seed subfunction | T1 Run | T1 Off | CAN5 F1 Run | CAN5 F1 Off |
|---|---|---|---|---|
| 01, 03, 05 | `7F 10 22` | `7F 10 22` | `7F 10 22` | `7F 10 22` |
| 09 | `7F 10 33` | `7F 10 33` | `7F 10 22` | `7F 10 22` |
| 0B | `7F 10 33` | `7F 10 33` | `7F 10 33` | `7F 10 22` |
| 0D, 11, 13 | `7F 10 33` | `7F 10 33` | `7F 10 22` | `7F 10 22` |
| 15 | `7F 10 33` | `7F 10 33` | `7F 10 33` | `7F 10 22` |

All 18 CAN5 grants and their programming replies were independently recovered
from the capture; keys/seeds remain redacted. The varying CAN NRC33 outcomes
are observations, not proof that security permissions change with power mode:
timing/state interactions remain possible. A numerically larger seed selector
is not necessarily a stronger privilege. No programming-session entry succeeded
in this matrix, and it sent no RequestDownload/TransferData or calibration clear.

The existing [programming-gate analysis](../../diagnostics/diagnosticsd_routines_and_recovery.md)
identifies a specific T1 precondition. Native `diagnosticsd` session transition
code sends internal query 5; Java `SessionControlHandler` returns positive only
when `BackupSystemPowerModeProtectedRemoteProgrammingActiveAuthenticated` is
true and available. Missing/unavailable/false returns conditionsNotCorrect.
The VHAL property is `2120105C`. This is distinct from the tested `529` power
mode; its CAN-to-VHAL mapping is being traced. An ordinary Off/Run value or
a successful SecurityAccess exchange does not prove this condition is met.

**Programming entry resolved over T1:** the Y175 VHAL ARXML tables map native
signal D7 (`BSPMP_RmtProgmActvAuth`) to CAN frame `20D`, DLC 6. Its signal
descriptor uses Motorola start bit 47, width 1: zero-based b5 bit 7. VIP Com
signal FF independently maps to that same ID, DLC and bit. The VHAL reference
SHA-256 is `3dcd9acccfa30aef7f5adfff0066dd69c71a163aa82b027b5e1359137fac7a88`.
VHAL ELF RVA `3BD86` sets FrameInfo ID 20D / DLC 6; `3BDBC` adds signal D7.
The Ghidra native analysis base is 100000; RVAs here exclude that base.

In a granted T1 session, the baseline `10 02` returned `7F 10 22`. Preserving
every captured `20D` byte except setting b5 bit 7, repeating at approximately
100 ms, then sending `85 02`, `28 03 01`, `10 02` produced **`50 02`**.
A second trial repeated the baseline rejection and successful entry. No
calibration clear was sent. The original 20D value was restored afterward.
Programming entry is therefore demonstrated with CAN environment input plus
T1 diagnostics, without MDI2; an LTZ transfer is not yet demonstrated.

The equivalent F1/CAN5 attempt still returned `7F 10 22`. Adding synthetic
CAN `284` / DLC 6 authenticated-system-power-mode candidates (raw 0, 1, 2,
4, b4 bits 3–5, validity bit 2 clear) did not change that CAN5 result. The
VHAL reference maps signal 58A (`SPMP_SysPwrModeAuth`) to frame 284; these
tests do not establish that the VIP accepted every authenticated-mode value.
**USB-update follow-up2026-11-17:** raw candidate2 was subsequently verified
through live updater readback: repeated284/DLC6 `00 00 00 00 10 00` changed
AAOS IGNITION_STATE to4/RUN, UpdateService SystemPowerMode fromOFF toRUN, and
lifecycle STATE_PROPULSION toSTATE_RUN while VehicleParked remained true. This
satisfied the USB installer's vehicle-on prompt; it does not establish the
other raw candidates. See the [full USB observation](../ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17).

The second T1 session included the deliberately invalid RequestDownload
format probe `34 00 00 02 00 00`, rejected with `7F 34 22`. It supplied no
module data. Later tracing identifies the TCP download
interceptor and Java installer as the relevant T1 route, so this rejection does
not validate native calibration-parser reachability. No valid download
initializer or TransferData was sent in that initial probe. The owner observed Update → Update unsuccessful / Vehicle Update Failed
around these session-entry/exit tests. A subsequent direct-T1 check found all
14 LTZ F182 identities still matching the pinned stock package, F0F0 listing
all slots 02–0F with status 00, and F0F1/F0F2 each 0000. This is metadata/status
verification, not a full calibration-payload readback. Cleanup explicitly
returned to default, entered extended, re-enabled communication (`68 00`) and
DTC logging (`C5 01`), then returned to default.

ADB enablement through CAN and any diagnostic development-mode selector remain
open research tasks, queued behind genuine LTZ programming. The expanded grants
above do not establish success of the ADB candidate under those profiles; the
earlier full-domain ADB sweeps remain scoped to level 01. No build-type switch
or new ADB-enable mechanism has been demonstrated.

Evidence clarification (2026-11-16): USB debugging was manually enabled after
the current boot. Continued ADB availability within that boot is therefore
consistent with manual enablement and is not evidence of a CAN-triggered ADB
enable or persistence across a reboot. Any persistence test must establish a
new boot and distinguish it from an unchanged running AAOS instance.

#### Full stock LTZ rewrite through CANable (2026-11-16)

**All fourteen genuine LTZ containers were transferred through direct CAN5,
including already-matching modules.** Download acceptance depends on preparation
and routing; matching F182 identities do not prohibit a rewrite. No MDI2,
`0249` clear-all, `FF00` per-module erase, or calibration-override clear was used.
**LTZ was subsequently verified working:** after the vehicle-VIN input test
and mute restart, VIP reported calibration state2, HMI ready and Propulsion;
the owner confirmed the homescreen. Fresh readback matched all fourteen LTZ
identities and the owner-supplied VIN, with all module statuses00 and
F0F1/F0F2=`0000`. The intermediate NoVIN failure below was resolved before
starting HC. This establishes a tested recovery on this bench with those
inputs, not an exhaustive payload readback or a minimal programming recipe.

| Stage | Observed result |
|---|---|
| Prepared T1 F5 attempt: protected programming active, authenticated power mode Off, FF01 / 021E checks, SecurityAccess, DTC/communication preparation | `10 02 → 50 02`; first stock `34` still `7F 34 70`, zero bytes transferred. Earlier F4 attempt also returned NRC70. |
| CAN5 with minimal power traffic and the same programming/power flags | FF01 `71 01 FF 01 00 86 04 07 00`; 021E `71 01 02 1E 00`; `10 02 → 7F 10 22`. |
| CAN5 with captured harness companions present | `10 02 → 50 02`; first `34 → 74 20 0F FF`. Which companion(s) resolved the gate is not isolated. |
| Genuine LTZ transfer, slots 02–0F | 46,162 bytes; all fourteen download negotiations accepted, all transfer blocks positively acknowledged, all fourteen exits returned `77`. |
| Immediate readback | All fourteen F182 identities match pinned LTZ; F0F0 lists all fourteen slots with status00; F0F1/F0F2 each `0000`. Metadata/status checks are not full payload readback. |
| Finalization | CAN F198 and current-date F199 writes returned `6E`; `31 01 03 9B → 71 01 03 9B`. CAN `11 01` returned `7F 11 22`. |
| Identity restoration | F190 read as seventeen zero bytes after finalization. T1 personalization returned `6E F1 90` and immediate matching readback, but the next mute restart still entered NoVIN. Subsequent private CAN personalization also returned `6E F1 90`; a later post-mute T1 read contained seventeen printable bytes, while VIP still entered NoVIN. |
| Restart observations | Mute input `526` b5-bit7 triggered reset after approximately10s; subsequent boots reported calibration state2 and HMI ready, then `SystemState=NoVIN (0xF)`. Complete captured harness traffic during another mute restart did not resolve NoVIN. A cold12V cycle with over10s off also reached NoVIN; its subsequent F190 read still contained seventeen printable bytes. Neither failed persistence nor a simple absent-VIN predicate is established by the display alone. |

The successful transfer environment replayed all captured profile IDs except
`20D`, while a separate approximately100ms stream supplied original `20D` with
b5-bit7 set and `284` with the candidate authenticated-Off field. The diagnostic
sender stops application repetition, so the runtime explicitly restarted the
captured companion replay after each ISO-TP frame. Replay cycles can therefore
restart at diagnostic boundaries; this is not proof that an uninterrupted or
minimum companion schedule is required. Original `20D` was restored afterward.

The T1 public `34/36/37` path uses the download interceptor and Java installer;
F4 selects OTA and F5 selects onboard programming. The latter expects package
manifest/signature preparation. This differs from the working direct-CAN stock
CSM transfer. The UpdateService screen previously reported installation while
the service had `mRunningInstaller=null`, an empty installer list, install-error
status and `UpdateService-BackgroundInstaller invalid state 14`.

**NoVIN recovery:** the VIP getter at file offset `6EE76` calls `6EE5A` on
RAM `FEBD22C0`; the helper tests eight bytes for all-FF. Startup calls this
predicate before logging NoVIN Active (`6F040–6F048`, log wrapper `50E6E`).
This differs from testing the seventeen F190 bytes directly. Identification of
that eight-byte value with a specific EEPROM block still needs tracing.
At `6EED6`, the separate internal classification is2 when the theft-locked
flag at `FEBE092B` is set; otherwise it is0 for the all-FF eight-byte value,
or1 when that value contains a non-FF byte. These are internal classification
values, not the SS SystemState enum (whose NoVIN state is0xF). No bench test
has established that writing any different VIN necessarily sets the theft flag.

Native VHAL ARXML signal/frame constructors independently map:

| CAN ID | DLC | Signal | Tested VIN input |
|---|---|---|---|
| `560` | 6 | Signal6B3 `VehIdNmDig1` | First VIN character followed by five zero bytes; companion fields unresolved. |
| `45A` | 8 | Signal6B5 `VehIdNmDig2_9` | VIN characters2–9 in order. |
| `459` | 8 | Signal6B4 `VehIdNmDig10_17` | VIN characters10–17 in order. |

All three IDs/DLCs also match the pinned VIP receive registry, callback3.
These IDs are absent from the captured32-ID harness profile. A ten-second
burst in the already-running NoVIN state produced no observed state change.
Repeating these owner-VIN inputs at approximately320ms across a mute restart,
with the captured harness traffic, reached calibration state2 at5.714s VIP
uptime, HMI ready and Propulsion at21.938s. The owner then confirmed the
homescreen. The three inputs were tested together; their individual necessity,
minimum duration and learned-state persistence without further VIN traffic are
not isolated. Do not reduce this to F190 write alone or claim that any VIN
mismatch necessarily produces theft-lock. Real VIN payloads were redacted.

The alternative genuine HC package has also passed all fourteen payload-digest,
header-RSA and production-CA signer-record checks (46,181 bytes). Its write is
complete: all fourteen downloads/transfer exits succeeded, followed by CAN
F198/F199/039B/F190 finalization. A transient CAN ACK/queue problem interrupted
the first finalization grant; silent internal loopback, ACK restoration and
captured traffic restored diagnostic replies, after which finalization was
completed without repeating the calibration transfer. The owner observed the
HC logo replacing the prior LTZ variant.

HC then passed mute restart with the vehicle-VIN inputs: calibration state2,
HMI ready and Propulsion at21.077s VIP uptime. Independent T1 readback matched
all fourteen HC identities and the supplied VIN; all module statuses were00,
F0F1/F0F2=`0000`. This is successful transfer, finalization and post-restart
metadata/status verification on the bench, not repeated-cycle reliability
qualification or full payload readback. Programming and finalization used
CAN5/CANable; T1 stock-transfer attempts failed before data transfer, and T1 was
used for independent readback. **The owner also confirmed the HC moving welcome
animation.** An initial wake from incomplete shutdown produced request1, not
welcome request2. After allowing shutdown to finish, replay from fresh startup
produced request2 at8.419s VIP uptime, completion approximately14.943s later,
then request3 and Propulsion at25.227s. A background update-observation helper
had earlier reasserted Run during an Off test; it was stopped before this
successful replay. Keepalive helpers must not override deliberate Off/testing
phases. Genuine LTZ/HC recovery is now established on this bench; the owner authorized the next modified-LTZ-package
experiment after these results.
Actual VIN values are used only in memory and excluded from capture payloads
and this document.

**Modified-module follow-up:** the owner-confirmed HC welcome video completed
stock visual verification. The prior LTZ-derived SXM-disable experiment was
then reconstructed in memory and attempted only for shared slot0C/part85102312.
Its recomputed digest verified; retained header RSA did not. Direct CAN5 accepted
download negotiation but rejected its first data block with `7F 36 72`. The
genuine slot0C container was restored in the same session (`76 01`, `76 02`,
`77`). Subsequent restart reached calibration state2/HMI ready/Propulsion;
independent readback matched all fourteen HC identities and the supplied VIN,
all module statuses00 and F0F1/F0F2=`0000`. No calibration clear was used.
The [custom-calibration workflow](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#4-chronological-trial-log)
owns the exact edit, candidate hash and rejection limits. Follow-up now
**confirms header-signature verification failure**: a one-bit signature-only
mutation with unchanged stock XML/digest/length was also rejected at block01;
repeating the SXM edit and reading F0F1 before restoration returned PEC0015.
The pinned VIP parser sets0015 on failed signed-header verification without
its separate validated-SBA-ticket marker, and its caller returns NRC72 before
SoC calibration init. The linked workflow records addresses and evidence.
F0F1 is an error code, not an error counter. Stock restoration returned it to
0000. The original control used profile01. Additional 2026-11-16 SXM-disable
trials under profiles03 and05 both reached programming/download, then returned
`7F 36 72` with immediate PEC0015. Genuine slot0C restoration completed after
each; F182 remained unchanged and later F0F0/F0F1/F0F2 were clean. Engineering
profile09 granted but denied021E with `7F 31 33`, before any download. No new
restart/visual verification was performed. Communication re-enable returned
NRC22 despite fresh extended-session entry; DTC logging enable and default
session were accepted. Do not claim fully confirmed cleanup. The
[additional-profile record](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-additional-can-security-profile-trials)
owns the candidate hash, exact outcomes and limits. Those profile-only attempts failed. The later CAN613/614 temporary-RAM
experiment accepted the custom slot and the owner confirmed SXM removal;
see the success record above. No general persistent development-mode selector
or Engineering09 signature exemption is established.

#### Button-input mapping and validation

Firmware `Com_ReceiveSignal` at file offset `C8F6A` indexes the descriptor table
by **signal ID × 24**; the descriptor's first word is a typed-storage index,
not the signal ID. Searching that word initially misidentified the mute input
as `49C`. A 20-second synthetic `49C` b2-bit1 hold produced no reset, but is
not a valid test of the recovered mute predicate. Correct direct indexing maps
inputs C72–C77 to `526`, b5 bits 7–2. The first input C72/b5-bit7 is checked by
the timer-arming branch; additional guards use signals DC9 and DD8. Their full
application meanings remain unresolved. See the existing
[mute-hold reset analysis](../../runtime/boot_timing.md#mute-hold-reset-and-adb-reboot-boundaries-2026-11-15).

**Live mute-hold reset confirmed:** `526`, DLC 8, synthetic payload with only
b5 bit 7 set, repeated at approximately 100 ms intervals while original `145`
and `529` continued, armed the mute timer. UART `Mute buttons pressed` at
VIP 89.527 s preceded `SWC Reset Button Press detected` at 99.525 s by
**9.998 seconds**. `evResetRequestCSM` / `SetShutdownAndResetCSM` followed,
then `evSoC_ShutdownComplete` at 100.385 s. The VIP counter restarted;
`BRR_RESET_REASON_VIP_SOFTWARE updated to 6` and reset factor 1 were reported,
followed by AnimationInit and HmiInit. This proves VIP reset as well as the
coordinated SoC shutdown request, rather than only an Android UI restart.
The planned hold limit was 20 seconds; the test released the input immediately
after detecting the reset request at approximately ten seconds. No explicit
40B/229 guard-field mutation, calibration clear or diagnostic ECUReset was
used. The release frame was all zero; the currently tested reset predicate
does not establish the functions of the other five button bits. CAN/UART
capture briefly restarted to add firmware-derived probe IDs and exact DLC
validation before this trial; captures continued in append mode.

Subsequent single-bit tests resolved two more `526` controls. With the radio
running, a 50 ms b5-bit3 press followed by an all-zero release changed diagnostic
volume readback 15 → 14. A 50 ms b5-bit2 press/release changed 14 → 15. Final
T1 DID41E7 readback was 15. This is normal CAN input control, distinct from the
CAN5 IOCID41DB adjustments rejected above. One-second holds with approximately
100 ms frame repetition produced larger repeated volume changes; press duration
and asynchronous release/readback matter. Bits 6, 5 and 4 each produced activity
timer-reset events during one-second probes, without a volume change or a named
button event in the selected UART observations. Their exact functions remain
unassigned. All six bits 7–2 have now been exercised individually, but only the
mute-hold reset and volume directions have established functional meanings.

The smallest **demonstrated home-screen set** has four distinct IDs:

| ID | Proven role in this bench work |
|---|---|
| `145` | Observed wake effect; network-management field interpretation remains a candidate |
| `529` | IPC HMI Ready: b1 bit 1; IPC Animation Status: b0 bits 5–7, captured value 1 completes the startup animation handshake |
| `457` | Opaque eight-byte ProtoKey Seed 1 |
| `458` | Opaque eight-byte ProtoKey Seed 2 |

On the validated physical power cycle, send original `145` then original `529`
once, roughly 0.5 seconds apart after fresh RH850 UART output. After the
30-second startup observation window, repeat all four for 10 seconds using the
captured 320.270-ms cycle and original relative offsets:
`145=0`, `529=40.001`, `457=160.120`, `458=170.139` milliseconds.
Normal HmiInit occurred at +7.892 seconds, HMIReady at +21.199 and Propulsion
at +21.228 from first CAN TX. Both seed-cache events followed the repeated
phase; ADB disconnected +4.268 seconds into that phase and the home screen was
physically confirmed. This excludes the other 28 harness IDs from necessity
for that tested startup. It does not decode their functions or establish
minimum frame count, required waiting time, cycle duration or long-term keep-alive.

After startup, original **`529` alone every 320.270 ms** sustained operation for
almost 12 hours; `145` alone and the seed pair alone failed the short hold test. This is the tested
post-boot keep-alive, separately scoped from the four-ID startup/access recipe.
Clearing `529`'s ready bit also sustained Propulsion for 95 seconds, so that
particular bit is not required to remain 1 after initialization. Later bit-level tests identified b1 bit 7 as the On/Off selector under the
captured companion fields; packet freshness and minimum usable cadence remain
separate constraints.

A **candidate restricted/debug boot** sends only those first eight frames once
at roughly 0.5-second spacing after fresh RH850 UART activity. Exclude `457`
and `458`. Multiple physical cycles reached Android boot-complete and the
ProtoKey **Start Your Vehicle** screen with authorized ADB when debugging had
been enabled manually and verified before the cut. This is a bench observation,
not a validated factory service/debug mode. Other cycles with the same verified
pre-cut setting did not enumerate ADB; retention is not yet deterministic.
The recipe is not validated for `adb reboot` or every software-reset path.

For this candidate, enable USB debugging on the normal home-screen boot, verify
`adb_enabled=1` and persistent USB configuration `adb`, stop application TX,
physically remove power, then run only the eight-frame startup after power-on.
Respect the smart-outlet 10-second minimum between completed toggles. Observe
both USB enumeration and the live ADB setting when available; the restriction
alone does not imply ADB is enabled. The complete home-screen recipe has
repeatedly coincided with the gate clearing and USB debugging being disabled.

## Evidence and confidence

`B:n` means record line `n` in the retained connected/startup `can5.jsonl`;
`H:n` means line `n` in `can5-harness-only.jsonl`. These local capture roles avoid
machine-specific paths. Raw captures and payloads are not repository attachments.
**H** means observed from the isolated harness; **R** means received from the
radio with the harness MCU disconnected. All 40 previously provisional radio IDs
were subsequently received in `radio-only-rx.can.jsonl`, with TX echoes excluded;
there were no missing or additional IDs in that comparison. The matching
`radio-only-rx.uart.jsonl` supplies Mac-clock-correlated UART events.
**A** is an external ID-and-DLC match, **W** a name-only lead, and **conflict** a
format mismatch. An alias does not establish an A11 sender, recipient, scale,
checksum or wake/keep-alive function. Unknown entries remain unknown.

The full retained B capture has **265,214 data frames, 72 IDs and 39 adapter-status
records** through `B:265254`; no later data ID or DLC variant was found. Dictionary
statistics use its first **60 seconds** (`B:2–8592`): **8,578 data frames**, **13
status records**, **57 static-payload IDs**, and **15 changing-payload IDs**.
This excludes the later disconnect/retry storm. No extended/RTR frames, reported
overflow flags, or host TX echoes occurred in those B/H baseline captures. Later
active tests contain separately labelled TX echoes and extended diagnostics;
the absence statement does not apply to them. The H snapshot ends at `H:74804`.

Periods are median hardware-timestamp intervals at `t ≥ 2 s` in that first
minute, handling 32-bit wrap. One-second medians do not exclude event-triggered
updates. `U` is the distinct-payload count in that minute; byte positions start
at `b0`. Changed bytes are observations, not decoded fields. Time zero is the
first received B status record, not an electrical power edge. DLC is bytes.

## Verified A11 translations

Byte positions below start at zero and preserve the CAN payload's transmitted
order. **Verified** means the specified observation or byte mapping was tested;
it does not validate unlisted bits, payload mutation, or every firmware version.

| ID / direction | Field or effect | Radio-side mapping | Evidence and limits |
|---|---|---|---|
| `457`, harness → radio | b0–b7: opaque 8-byte Seed 1 | GMLAN reception → RH850 ProtoKey Seed 1 cache → ProtoKey delivery to SoC | All 8 bytes matched UART cached Seed 1 in 9/9 cache events, same order; original fixed payload only; bit substructure and checksum algorithm undecoded |
| `458`, harness → radio | b0–b7: opaque 8-byte Seed 2 | GMLAN reception → RH850 ProtoKey Seed 2 cache → ProtoKey delivery to SoC | All 8 bytes matched UART cached Seed 2 in 9/9 cache events, same order; original fixed payload only; bit substructure and checksum algorithm undecoded |
| `529`, harness → radio | **b1 bit 1**, mask `0x02`: IPC HMI Ready; 0=not ready, 1=ready | RH850 `CAN Event: IPC HMI Ready = 0/1`; relates to normal HmiInit progression | Fresh omission + single-frame restoration, then controlled clear/restore round trips; other mapped fields listed separately, remaining bits unresolved |
| `145`, harness → radio | Observed wake effect; NM-format interpretation remains candidate | Original single frame followed by SoC power-level reports and inbound T1 activity | Does not establish which PN bit wakes which component, or produce normal HmiInit/Propulsion alone |
| `20D`, tester → radio | b5 bit 7: protected remote-programming-active authenticated input, DLC 6 | Enables the documented T1 programming-session precondition | Captured companions retained, approximately 100 ms repetition; baseline `7F 10 22` changed to `50 02` in two T1 trials; original value restored; successful LTZ transfer and equivalent CAN5 entry remain unproven |
| `529`, tester → radio | b1 bit 7: tested power-mode selector; 1→On/internal mode 2, 0→Off/internal mode 0 | Immediate PowerModeOn/Off and Propulsion/LocalInfotainment changes while packets continue | Two sustained clear/restore round trips; captured companion fields retained, including b0 bit 0=0; no Accessory/Service-mode claim |
| `529`, tester → radio | b0 bits 5–7: IPC Animation Status | RH850 animation-status log; full 3-bit field was swept through 0–7 | Eight cold starts plus a 2→1 transition distinguish not-ready (0), complete (1), and ready/incomplete (2–7); conditional on CSM readiness; OEM enum names unresolved |
| `53B`, tester → radio | b7 bit 3: Infotainment Activation Request | RH850 activation-request log | Two 1/0 round trips plus an Off-state prewake: request=1 advanced Sleep → AnimationInit before the later door-open / request-1 candidate; actual video unverified |
| `4BE`, tester → radio | b7 bit 3: Key/ID Device Present | RH850 true/false log | Synthetic payload; no claim of key authentication or theft-deterrent authorization |
| `4BE`, tester → radio | b6 bits 6–7: Valet Mode Response | RH850 raw value log | Values 0–3 observed; enum labels and actual valet behavior not established |
| `4DA`, tester → radio | b6 bits 3–5: Folding Top State | RH850 raw value log | Values 0–2 observed; optional equipment and enum meanings unresolved |
| `4DA`, tester → radio | b7 bit 0: DriverDoorOpen; 1=open, 0=closed | RH850 DriverDoorOpen/Closed events; after PowerModeOff, ends LocalInfotainment and starts display shutdown | Live open/close control in Propulsion had no shutdown; opening after Off caused display off, HmiInactive, then Sleep and SoC-off; startup/shutdown animation request meanings remain under investigation |
| `526`, tester → radio | b5 bit 7: mute-hold reset input, DLC 8 | Mute timer arming → SWC reset request after 9.998 s → coordinated SoC shutdown and VIP software reset | Synthetic frame, all other bits zero; approximately 100 ms repetition; original 145/529 continued; input released after reset detection, below the 20 s trial ceiling |
| `526`, tester → radio | b5 bit 3: volume down; b5 bit 2: volume up | Normal CAN button press/release → AAOS diagnostic volume readback | Separate 50 ms presses and all-zero releases gave 15 → 14 → 15; longer holds repeated; this does not identify the physical button-source module |

Seed payload values are not reproduced in this reference. A numeric scaling or
signedness is not defined for an opaque seed byte array. Its observed byte order
is not a claim about integer endianness or an internal cryptographic format.
The checksum printed by the UART logger has not been assigned a CAN payload
field or algorithm. The receive configuration and several descriptor-to-handler paths are now
recovered below; full handler semantics remain incomplete.

### ProtoKey seeds, VIN and diagnostic authorization are separate questions

The two CAN seed values are opaque binary material used by the observed
RH850-to-SoC ProtoKey path. They have not been decoded as a VIN, shown to be
VIN-derived, or established as a theft-lock bypass. Their combined 16-byte
length alone does not prove the construction of the SoC's 16-byte ProtoKey.
The native `gm_protokey` reference validates received material against persisted
validation state and has a BCM-replacement user-data-wipe branch; the traced
validator does not compare a textual VIN. See the
[native validation trace](../security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14).
No seed mutation, wipe or VIN-mismatch test was performed here. The CAN seeds
are also distinct from the 31-byte UDS `$27` seed and the MEC/ADB certificate gate.

For the verified `529` field, decode `ready = bool(data[1] & 0x02)` from a
six-byte payload. Clearing that bit and restoring the original each produced
the corresponding UART 0/1 transition; this was repeated three more times.
Clearing captured-set b0 bits 3/4/5 or b1 bit 7 produced no ready-state change
in those short windows. Follow-up firmware tracing and animation-specific
observation subsequently mapped b0 bits 5–7 below; the remaining bits are
unresolved. Original `529`
was restored at the end. The radio-side label is **IPC HMI Ready**; no expansion
of IPC or Android UI visibility is inferred from the label alone.

### Fresh omission controls on 2026-11-16

| Withheld ID, all other startup slots retained | Before late restoration | Late original after refreshing the other seven |
|---|---|---|
| `529` | No IPC HMI Ready=1, no HmiInit; startup-fault timeout at +16.231 s | IPC HMI Ready=1 at +31.5 ms from the probe |
| `20D` | Normal HmiInit at +7.909 s and Propulsion at +21.222 s; no startup fault | No new selected power-state marker in the eight-second probe window |

Omission of `20D` delayed AnimationInit in this trial but did not prevent normal
startup. This establishes conditional non-necessity, not the message's full
function or equivalence to a different frame. The initial `529` observation
was followed by the bit-level clear/restore tests above.

### Static-reference scope

The selected reference is Y175 VIP_APP part `85759599`, SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`.
The existing RH850 little-endian 32-bit project contains exactly those artifact
bytes, imported at analysis base 0. This hash was not read from live radio ROM.
Its logging strings include GMLAN seed fetch/cache and the observed ready input.
Automatic string cross-references were incomplete; the address relationship
recovered below enabled targeted configuration and handler tracing. Raw ordinal
arrays and coincidental ID/pointer patterns remain excluded. File offsets alone
are not runtime addresses.

### Firmware receive/transmit configuration recovered — 2026-11-16

This extends the captured 72-ID inventory; it does not turn every configured
message into a live-validated signal. The selected Y175 artifact remains a
build-matched reference, not a hash of the running radio's ROM.

Earlier automatic string xrefs missed a consistent address relationship:
for the traced strings and configuration tables, compiled address equals file
offset plus `0x27A7A`. For example, IPC-ready string file offset `0x47CE`
is referenced as `0x2C248` by the instruction at file offset `0x50302`.
The receive configuration is referenced as `0x4A97C`, corresponding to file
`0x22F02`. These are separate address domains; no claim is made that every
firmware region shares this mapping.

The receive table has **299 twelve-byte entries** through file `0x23CFA`.
The ID/mask lookup at file `0xC2E6C` uses that table; the receive dispatch at
`0xC2DFC` reads the PDU index at +8, length/flags at +10 and callback slot at
+11, then invokes the enabled callback. There are **277 exact standard-ID
entries routed to callback slot 3**, 20 entries to slot 2, one to slot 4 and
one NM-style range entry to slot 1. Callback slots are software dispatch
indices, **not physical CAN channel numbers**. Slot 3's compiled callback
pointer `0xC6EE0` corresponds to a wrapper at file `0x9F466`.

The adjacent transmit configuration starts at file `0x23D06`, compiled
`0x4B780`, and contains **58 entries** before the next data structure. It
includes every one of the 40 baseline radio IDs with matching DLC. Additional
standard entries are `228` (DLC 6), `614` (8), `3F0` (8), `3F3` (8), and
`3FB` (8). The other 13 are extended-format routes. Configured transmission
is not evidence that a message has actually been emitted on this bench.

The remaining receive entries, outside the 277-entry application group, are:

| Callback slot | Standard entries | Extended entries, wire IDs |
|---|---|---|
| 1 | NM-style range record: ID `100`, encoded mask/flags `600001FF`, length/flags `88` | None |
| 2 | `680`, `3FA`, `3F2`, `3F1`, all DLC 8 | `14DAF645`; `14DA80F1`–`14DA80F5`; `10EBFEF1`–`10EBFEF5`; `10DBFEF1`–`10DBFEF5`, all DLC 8 |
| 4 | `613`, DLC 8 | None |

The 13 additional extended transmit entries are `14DCF180`, `14DCF280`,
`14DCF380`, `14DCF480`, `14DCF580`, `14DAFC80`, `14DAF180`, `14DAF280`,
`14DAF380`, `14DAF480`, `14DAF580`, `14DA45F6`, and `10DBFEF6`, all DLC 8.
The stored high-bit format flag has been removed from these wire IDs.
These inventories do not establish request/response pairing or service
semantics. Previously observed `14DA80F2` → `14DAF280` diagnostic responses
are independent live evidence; other listed routes have not all been probed.

Only **17 of the 32 harness IDs** occur as exact slot-3 entries. The other 15
are `01E 0AA 0C1 0C9 0F1 145 18E 1C6 1E5 1F1 1F5 26F 435 50F 551`.
This does not prove they are ignored: NM/range dispatch and other paths must
be considered. In particular, the external `1F1` power-mode interpretation
has no exact slot-3 route here, consistent with our unsuccessful isolated
power-mode experiments. It remains unvalidated on this radio.

#### Newly mapped and actively checked fields

The 24-byte signal-descriptor table is referenced as compiled `0x4FB8C`,
file `0x28112`. Signal `134` names PDU `F0`, payload bit 9; the receive-table
entry maps PDU `F0` to `529`, DLC 6. This independently matches the previously
verified b1 bit 1. Following the same descriptor-to-PDU-to-ID chain recovered:

| CAN ID / DLC | Field, zero-based bytes | Signal index / PDU | Live observation |
|---|---|---|---|
| `529` / 6 | b0 bits 5–7: IPC Animation Status | `133` / `F0` | Clearing/restoring b0 bit 5 produced UART Animation Status 0/1; a later full-field sweep confirmed all raw values 0–7 |
| `53B` / 8 | b7 bit 3: Infotainment Activation Request | `84B` / `103` | Two 1/0 round trips, each logged by RH850 |
| `4BE` / 8 | b7 bit 3: Key/ID Device Present | `D93` / `CF` | RH850 logged true, then false |
| `4BE` / 8 | b6 bits 6–7: Valet Mode Response | `DE0` / `CF` | RH850 logged raw values 1, 2, 3, then 0; enum meanings are not decoded |
| `4DA` / 8 | b6 bits 3–5: Folding Top State | `14A` / `26` | RH850 logged raw values 1, 2, then 0; enum meanings and hardware applicability remain unresolved |

The three new IDs were probed with synthetic eight-byte payloads: all other
bits zero, each value repeated about every 320 ms for 2.3 seconds. Original
`529` continued separately. Across these probes, 120 candidate frames were
queued; the controller's final totals were 319 queued / 319 TX echoes,
zero CAN-status records and 1,383 received radio frames. UART showed no
SystemState transition or PowerModeOff during those short windows. Echoes
remain mailbox-admission evidence; the matching UART value changes establish
actual reception and application decoding. No claim about a visible UI change,
shutdown/wake sufficiency or continued effects without `529` follows from this
already-running-state test. Candidate transmission ended with tested fields at
zero; the original `529` keep-alive was resumed, then later stopped for the animation trials. The listener controller was
briefly restarted to add the bounded probe command; captures resumed in append
mode, and the earlier multi-hour hold result predates that restart.

#### IPC animation-status sweep and startup path — 2026-11-16

A post-boot sweep replaced only `529` b0 bits 5–7 with each raw value 0–7,
held for ten seconds at the captured 320.270-ms period. All other payload bits,
including IPC HMI Ready, were preserved. Each value produced the corresponding
RH850 `IPC Animation Status = n` line. Every stage queued 32 frames and received
32 TX echoes, with no CAN-status records or power-off events during this sweep.
The original payload was restored afterward. No physical power cycle occurred
within that sweep, so it does not establish a visible boot-animation effect.
Values are status codes; they have not been identified as eight animation
selection commands or assigned descriptive enum labels.

Static tracing identifies a separate PlayAnimation IPC path at file `73D62`:
it builds a two-byte message beginning with `43`. ReportAnimationState handling
at file `745E6` accepts a two-byte message and passes its second byte to
`8AB92`, which stores the CSM animation state consumed at `50946`. The RSI
animation logger at `50614` occurs in a reset-to-zero path. No independent
RSI/CSM CAN-frame mapping has been recovered from those strings.

The completed cold-start comparison used a value-1 control, then the other seven values.
After fresh UART, send original `145`; approximately 0.5 seconds later start
selected-value `529` cyclically. At +30 seconds from that cyclic phase, send
`145/529/457/458` for twelve seconds with original offsets and only `529`'s
animation field modified. Stop transmission at +42 seconds and observe through
+60 seconds. Maintain at least ten seconds powered off between boots. The
standalone keep-alive is stopped during this work, as requested by the owner;
trial completion leaves ACK-enabled reception, with no continuing application TX.
This differs from the earlier one-shot-then-wait recipe by keeping the selected
animation status available throughout initialization; the same timing is used
for the control and variants.

The value-1 control reached `AnimationInit`, received CSM animation state 0 then
1, and logged Animation Ready. It sent PlayAnimation on channels 2 and 16,
entered HmiInit, then reported Animation Complete, HMI Ready and Propulsion.
Both seed caches were observed. This places the observed PlayAnimation exchange
in startup, before HMI Ready; physical observations below identify the Chevy
logo in the tested ready-status boots. The control queued 245 frames with 245 echoes. Its 154
CAN-status records include missing ACK and protocol-error/controller warning/
passive indications during startup; no bus-off was recorded. These transport
records are retained rather than treating an echo alone as delivery proof.
Subsequent UART field, seed-cache and state changes establish actual reception.

The eight cold starts separated readiness from completion. Times below are
RH850 bracket timestamps in seconds after that boot's counter origin, not
host wall time or the outlet switching edge. Ready/Complete refer to the
overall startup checks after the SoC's CSM animation status became 1; they
are not claims that the CAN field alone can override missing CSM readiness.

| `529` animation value | Ready | Complete | HmiInit s | STARTUP_FAULT_TIMEOUT s | Propulsion s | Physical display observation |
|---|---|---|---:|---:|---:|---|
| 0 | false | not reported | — | 15.721 | 15.721 | Black until Start Your Vehicle, then homescreen |
| 1 | true | true | 8.435 | none | 21.894 | Chevy logo |
| 2 | true | false | 8.445 | 23.441 | 23.441 | Chevy logo |
| 3 | true | false | 8.474 | 23.471 | 23.471 | Chevy logo |
| 4 | true | false | 8.333 | 23.321 | 23.321 | Chevy logo |
| 5 | true | false | 8.425 | 23.421 | 23.421 | Chevy logo |
| 6 | true | false | 8.530 | 23.521 | 23.521 | Chevy logo |
| 7 | true | false | 8.638 | 23.631 | 23.631 | Not physically reported |

Value 0 therefore took a 15-second AnimationInit fault-timeout path without
HmiInit or the logged PlayAnimation request. Values 2–7 entered HmiInit but
never reported completion; their STARTUP_FAULT_TIMEOUT followed approximately
15 seconds after HmiInit. Value 1 completed the normal handshake without that
fault. The initial trial summary filter missed the uppercase timeout event;
raw UART was retained and checked, and the filter was corrected for later
trials. Logo appearance alone is not proof of successful animation coordination.
The Chevy logo was physically confirmed for values 1–6; value 7's UART behavior
was measured but its display was not separately reported.

A ninth cold start began with value 2 and changed **only** this field to value
1 when RH850 emitted `evHMIReady`. UART recorded HMI Ready / Complete=false at
VIP 21.657 s, the new CAN animation status 1 at 21.688 s, Complete=true at that
same timestamp, and Propulsion at 21.689 s. No STARTUP_FAULT_TIMEOUT occurred
in its observation window. This demonstrates that a completion update at that
stage can advance startup without a new power cycle or a full harness replay.
The trial then sent the same two seed frames at the same phase as the controls.
All nine trials logged both seed-cache paths; these seed timings were held
constant, not optimized by the animation experiment.

The tested functional classes are **0 = not ready**, **1 = ready/complete**,
and **2–7 = ready but incomplete**, under this radio's current calibration
and with CSM readiness present. These are observed roles, not recovered OEM
enum names. Status is the full three-bit value: values 3/5/7 also set b0 bit 5
but did not complete, so testing that bit alone is an incorrect completion
decoder. Extract `status = (data[0] >> 5) & 7`; to change it while preserving
other fields, use `b0 = (original_b0 & 0x1F) | (status << 5)`.

Across the nine cold-start windows, 2,205 frames were queued with 2,205 TX
echoes. Startup CAN-status records persisted in each trial (145 or 154 per
window), so the semantic evidence is the matching UART state transitions and
physical display observations, not echoes alone. The final 2→1 trial restored
the captured animation value, then stopped application transmission. Subsequent
PowerModeOff / LocalInfotainment after the sender stopped is the known CAN
freshness timeout, distinct from STARTUP_FAULT_TIMEOUT during boot. Listening
and UART recording remain enabled; the standalone keep-alive remains stopped.

#### Door, wake and explicit shutdown paths — 2026-11-16

The animation-status sweep did **not** exhaust animation commands. An actual
animated in-vehicle welcome video remains a separate target. Archived Y181
property captures have `persist.sys.welcomeanim.enable=1` and
`debug.sf.nobootanimation=1`; these are reference-build observations, not a
live read from the current boot. VIP tracing recovered outgoing PlayAnimation
request values **1, 2, 3 and 4**. They are VIP-to-SoC IPC values, distinct from
`529`'s CAN animation-status values. All prior cold-start trials sent request
3. Its selector chain is file `70498` → `50FFC` → `89B1E` → request word
`FEBD3464` → `73D62` (opcode `43`). Action wrappers at `704D0` request 4;
`7053A` requests 2; `70500/70516/70556` request 3; `705AC` requests 1. Request 1/2 trigger conditions are investigated below; their actual visible
assets remain unverified.

The observed in-vehicle driver-door shutdown matches GM's retained accessory
power behavior: the driver door terminates radio RAP after Off power mode.
This is documented in the [GM Silverado body-builder manual](https://www.gmupfitter.com/wp-content/uploads/2022/10/23_Silverado_1500_Electrical_Body_Builder_SM_en_US_2022OCT24.pdf),
section 7-972. It is behavioral corroboration, not a CAN layout for this image.

**Wake layers were tested separately with 12 V continuously applied.** From
observed Sleep, repeating `529` with animation status 2 did not wake the radio:
5 frames queued, 3 admission echoes, zero radio RX and no UART change before
the 1.596-second transport abort. Pending frames were drained using silent
internal loopback; its extra echo is not an external wake response. This is a
non-acknowledgement result, not a validated application-level rejection.

A single original `145` then woke VIP: UART restarted with wakeup factor
`400000` and reset factor `400`, versus reset factor `201` on the preceding
12-V cold starts. SoC power levels 1, 2, 3 and 4 followed, with 326 radio frames
received in the eight-second observation. The owner confirmed that the display
remained off. Thus `145` can wake VIP/SoC from the observed Sleep state; it is
not by itself a demonstrated display-on or welcome-video command. The first
late door-bit probe subsequently encountered a sleeping/non-acknowledging
receiver and was transport-inconclusive; its pending frames were drained
silently before the following continuous test.

**New live-confirmed field: `4DA`, DLC 8, b7 bit 0 = DriverDoorOpen.** Signal
index `660`, PDU `26`, width 1 at payload bit 56 is read at `5032C`. It reaches
`6F48C` with selector 0, which posts event 15 (DriverDoorOpen) for true and 14
(DriverDoorClosed) for false. These event IDs match the name table beginning at
file `F9916`. The three other selectors use signals `14C` (`4DB`, bit 56),
`8B7` (`4D9`, bit 59), and `B05` (`4D8`, bit 6); their individual door positions
have not been assigned or live-tested.

The continuous test woke using `145`, repeated `145/529` with animation status
1, then added the original seed pair at +30 seconds. The owner observed display
on, the Chevy logo, a Focus Your Attention on Driving prompt, and homescreen
after pressing OK. Those observations establish display/UI wake under the
combined sequence, not the animated welcome video. While UART reported
Propulsion, a `4DA` door 0→1→0 control produced DriverDoorOpen and
DriverDoorClosed events without leaving Propulsion. Other `4DA` bits were zero
and held constant throughout these synthetic probes.

After the startup sender stopped, PowerModeOff / LocalInfotainment appeared at
VIP 105.731 s. At 105.949 s the subsequent `4DA` door-open frame produced
DriverDoorOpen and PlayAnimation request **4** on channels 2 and 16;
HmiInactive followed at 105.952 s and Requesting Shutdown at 105.954 s. The
owner confirmed display off. Therefore this field provides a verified
state-dependent CAN path to end the LocalInfotainment/RAP-like display hold,
without waiting the additional 600 seconds. It did not force shutdown during
the Propulsion control. The test used 343 queued frames / 343 echoes overall;
UART changes and display observation, not echoes alone, establish the effect.
Follow-up UART confirmed `SHUTDOWN_ANIMATION_FAILSAFE_TIMEOUT` at VIP
120.941 s (about 15 seconds after door open), Sleep at 135.942 s (about
30 seconds after door open), BACKGROUND_SLEEP_TIMEOUT at 145.941 s, and SoC
power level 0 at 165.801 s (about 60 seconds after door open). Display-off,
VIP Sleep and SoC-off are therefore distinct observed milestones. The path
works as an explicit door-triggered shutdown, but its animation-completion
failsafe prevents calling it a fully clean shutdown-animation handshake.

A second state-dependent door sequence then tested these inputs while the
owner was away from the display. After the first door-open caused request 4
and HmiInactive, closing the door produced DriverDoorClosed but no request 2.
A subsequent door-open while HmiInactive produced **PlayAnimation request 1**
on channels 2 and 16 at VIP 112.254–112.255 s. A later close again produced
DriverDoorClosed without request 2. Thus request 1 is now a live-observed
alternative to request 3, but its actual video/display effect remains
unverified. The stateful sequence used 346 queued frames / 346 echoes and
ended ACK-only. It must not be documented as a successful visual animation.

The state table was recovered as 242 validated 28-byte descriptors at file
`11236`, with 12-byte transition records and debug names at `F9A06`.
HmiInactive (state 125) owns the door handlers: DoorOpen event 15, guard `70400`,
action `705AC`; DoorClosed event 14, guard `70454`, action `7053A`.
A previously undefined instruction range was decoded temporarily (not saved)
to establish that action `705AC` calls selector `70498` with value **1**.
AnimationInit (state 213) instead handles DoorOpen by clearing an arm flag
(`6FCA0`) and guarded DoorClosed by setting it (`70646`). Its junction 233
can select request 2 via that flag. The DoorClosed guard `7036A` requires
PowerMode 0 (Off). The bench's normal power-on path uses the other branch;
these are conditional transition paths, not unconditional CAN video selectors.

**Direct power-mode control is now live-confirmed: `529` b1 bit 7**, signal
`828`, while preserving the captured companion fields. With b0 bit 0 (`829`)
clear and the handler's normal freshness/configuration gates satisfied, code
at `50BA0` selects raw mode 0/4; table `2C574` maps these to internal PowerMode
0/2 and setter `6F6A4` emits PowerModeOff/On. Two four-second clear/restore
round trips verified the predicted behavior without stopping `529` repetition:

| Bit 15 operation | RH850 observation, VIP timestamp s |
|---|---|
| Clear, round 1 | PowerModeOff and LocalInfotainment at 36.181 |
| Restore, round 1 | PowerModeOn at 40.201; Propulsion at 40.202 |
| Clear, round 2 | PowerModeOff at 44.211; LocalInfotainment at 44.212 |
| Restore, round 2 | PowerModeOn at 48.231; Propulsion at 48.232 |

A final clear produced Off at 52.261 s; DriverDoorOpen at 54.264 s then caused
request 4 and HmiInactive at 54.267 s. There was no 60-second sender-expiry wait.
The complete trial queued 320 frames with 320 echoes and ended ACK-only. The
old brief bit probe's lack of HMI Ready change was not a power-mode test.
This mapping does not establish Accessory or Service-mode encodings, nor the
unmutated companion bits' OEM names. Extract the tested selector with
`bool(data[1] & 0x80)`; clear only mask `0x80` for the tested Off variant.

**Request 2 was subsequently reached during a vehicle-Off startup**, rather
than by replaying numeric CAN animation-status values. From Sleep, send one
`145`, then repeat `145/529` with b1 bit 7 clear, b1 bit 1 retained and CAN
animation status 1. A driver-door-open frame at +1.830 s caused AnimationInit;
a close at the first CSM state-0 report caused DriverDoorClosed at VIP 6.549 s.
At 8.524–8.525 s VIP sent PlayAnimation **2** on channels 2 and 16 and entered
HmiInactive at 8.527 s. CSM later reported state 1 at 23.528 s; Sleep followed
at 36.542 s. There was no initial request-3 logo command in this trial. All
341 queued frames produced echoes. The owner was away, so this is a confirmed
command/state path with **unverified visual output**; request 2 cannot yet be
named a welcome or farewell asset. Its observed path ends in inactivity/sleep.

**A separate request-1 entry-to-On candidate was also exercised.** All times
below are the observed VIP counter values; the five-second dwell is the test
choice, not a recovered OEM requirement:

| Step | Inputs / observation |
|---|---|
| Prewake, with 12 V retained | Original single `145`, then cyclic `145/529`: power-mode bit 0, IPC HMI Ready 1, CAN animation status 1 |
| Request infotainment startup | Single `53B` b7 bit 3=1; Sleep → AnimationInit at 1.749 s, then HmiInactive at 8.383 s; no DriverDoorClosed arming edge |
| Simulate driver entry | `4DA` b7 bit 0=1 at HmiInactive; DriverDoorOpen at 8.994 s produced PlayAnimation **1** on channels 2 and 16 |
| Request vehicle On | After five seconds, restore `529` b1 bit 7; PowerModeOn at 14.111 s, request 3 at 14.302 s and HmiInit at 14.303 s |
| Finish startup | HMI Ready / Propulsion at about 24.094 s; original seed pair joined at the same later phase as the controls |
| End the unattended test | Close door while On, clear the power selector, then open door; Off at 39.761 s and request 4 / HmiInactive at 41.775–41.778 s; application TX stopped |

The candidate queued 312 frames with 312 echoes and did not log
`evSTARTUP_FAULT_TIMEOUT`. HMI Ready and Propulsion are protocol milestones;
**neither the actual video nor a homescreen was physically observed in this
unattended candidate**. An earlier ordinary request-3 wake was physically
observed to show the Chevy logo, driving-attention prompt and homescreen after
OK; that observation must not be transferred to the request-1 candidate.

There are three distinct numeric domains: CAN `529` animation status (0–7),
VIP-to-display PlayAnimation request (observed 1–4), and display-to-VIP
ReportAnimationState. Equal numbers across those domains are not equivalent
commands. The supported request paths now observed are:

| PlayAnimation request | Confirmed context | Visual evidence |
|---|---|---|
| 1 | DriverDoorOpen while HmiInactive; can be followed by PowerModeOn and normal HMI startup | Unverified |
| 2 | PowerMode Off plus an armed early DriverDoorClosed edge during AnimationInit | Unverified; followed by HmiInactive/Sleep |
| 3 | Normal On startup or HmiInactive → HmiInit | Chevy logo observed |
| 4 | DriverDoorOpen ends vehicle-initiated LocalInfotainment after Off | Display off observed |

Current bench procedure has no standalone keep-alive between trials. Captures
continue in ACK-enabled receive mode; a visual replay is still needed to
identify the actual in-vehicle animated welcome asset.

#### Display-side player resolves the animation command numbers — 2026-11-16

The owner's Y175 cleanroom contains `system/bin/animengine`, x86-64 ELF PIE,
SHA-256 `d28323285d8fcb8b48e324114bedbc7dc0d835cc4014c3d0891dd2156dac050c`.
The running production radio reported `init.svc.animengine=running` and
`debug.sf.nobootanimation=1`. Shell could not read/hash the live executable:
`Permission denied`; `adb root` returned `adbd cannot run as root in production
builds`. The cleanroom component is therefore not byte-matched to live ROM,
but its command mapping is corroborated by the following CAN-driven display test.

At ELF VA `435FC0`, `AnimEngine::showAnimation(AnimationType)` maps input values
1–4 through table `324F0` to internal events `[11,1,2,3]`. The event-name table
at `4F66E0` resolves those events as:

| VIP/HIDL animation request | Player event |
|---|---|
| 1 | STOP_ANIMATION |
| 2 | SHOW_WELCOM_ANIM (literal spelling) |
| 3 | SHOW_STARTUP_ANIM |
| 4 | SHOW_SHUTDOWN_ANIM |

Thus the earlier request-1 entry candidate was a successful stop/On-startup
handshake, **not a welcome-play command**. Its visual replay showed a Chevy
logo then homescreen; repeating it on a fully booted SoC with an eight-second
hold also showed Off → On → logo/homescreen, without the moving welcome video.
This corrects the prior candidate interpretation without changing the confirmed
CAN power/door mappings or the observed request-1 packet.

The dedicated engine contains welcome-calibration gating and separate
`welcomeanim.mp4`/ZIP, startup and shutdown paths. The cleanroom has 31 welcome
MP4 variants; fallback `product/ro/anim/3/graphics/1/welcomeanim.mp4` is H.264,
1280×768, 180 frames / 6 seconds. This identifies an available reference asset,
not the currently selected live brand/flavor. The live welcome-enable property
was absent, but absence alone does not mean disabled: `getPersistentData()`
skips its property overrides when `persist.sys.anim.flavor` is absent/default
-1, leaving calibration-based configuration. No animation property or calibration
was modified during these tests.

A visual replay of **request 2** using the previously recovered vehicle-Off
and early door-close path **did play the moving animation**, as observed by
the owner, followed by the Chevy logo when the test asserted On after eight
seconds. The owner noted that the animation might have been cut short. This
is the first physically confirmed moving-video result; it establishes the
welcome-play command independently of the CAN status-field sweep. A subsequent
replay waited for the first post-playback CSM state-1 report (minimum ten-second
observation, 22-second fallback limit), instead of forcing On at eight seconds.
The owner confirmed that the animation completed. The post-playback report
arrived at VIP 23.311 s, approximately 15 seconds after request 2. Run was then
asserted; HMI Ready followed at 23.430 s and request 3 at 23.581 s, with
Propulsion at 24.908 s. Completion alone therefore did not suppress the
subsequent startup request. These IPC milestones do not establish whether a
static logo was physically visible during that particular handoff.

A follow-up waited for both welcome completion and HMI Ready before Run,
with a bounded 30-second wait after request 2. Welcome completion arrived
14.892 seconds after the request, but HMI Ready was not reported before Run.
The radio returned to Sleep at trial +37.271 s, just before the bounded Run
handoff at approximately +37.4 s. Run produced request 3, HmiInit and then
Propulsion. Physical observation was welcome video → black screen → Chevy
logo → homescreen. Waiting longer alone therefore did not remove the logo;
this trial also crossed the HmiInactive timeout and cannot establish the
behavior of a handoff immediately before that timeout.

The recovered HmiInactive state table supports the observed startup request:
`evPowerModeOn` enters StartupDelayWait, whose `evSTARTUP_DELAY_WAIT` branch
reaches action `70500` (request 3) before HmiInit. HMI readiness alone does not
provide an alternate branch in this part of the recovered table.

A second follow-up kept status 1 for welcome playback, then changed **only
the animation-status field to 0 and the power-mode bit to On** at the first
post-playback CSM state-1 report. That report arrived 14.871 seconds after
request 2. UART confirmed status 0 and `isAnimationReady = false` before
`evPowerModeOn`, but request 3 still followed approximately 0.2 seconds later,
with HmiInit. `evSTARTUP_FAULT_TIMEOUT` occurred approximately 15 seconds
afterward, followed by Propulsion. Physical observation was welcome video →
Chevy logo → homescreen, with no visible black interval. Thus applying the
cold-start logo-skip value after welcome does **not** suppress the startup
request on this HmiInactive path; it instead adds a startup fault timeout.
Neither follow-up established a clean welcome-to-homescreen handoff without
the logo. The normal status-1 completion path remains the confirmed handshake.

The temporary On hold used during player inspection was stopped before that
replay; no permanent player-setting change or background keep-alive is required
for the animation trigger. CAN/UART captures remain the correlation evidence.

#### Activation-request hold experiments and host-sleep confound

An initial `53B` request=1 stream ran for 95 seconds of the test driver's
monotonic clock without its watcher recording PowerModeOff. This is **not a
validated hold result**: the corresponding host-wall/UART interval was about
410 seconds, with approximately 314 seconds missing from the host monotonic
interval. A later interval differed by about 572 seconds. macOS power logs
confirmed sleep/wake events. The bounded `529` restoration also expired before
the next trial; UART recorded PowerModeOff and LocalInfotainment. The subsequent
single-request trials therefore lacked a verified Propulsion baseline and are
inconclusive. Matching short UART field transitions above remain valid.

A sleep inhibitor is now tied to the listener process. The guarded follow-up
compares host wall and monotonic elapsed time, aborts on a difference exceeding
two seconds, restores `529` between phases and starts its continuous renewer
automatically on exit. The completed guarded results were:

| `53B` request=1, with periodic `529` withheld | Result |
|---|---|
| One frame, then ACK-enabled reception only | PowerModeOff and LocalInfotainment at +62.519 s |
| Repeated about every 320 ms | PowerModeOff and LocalInfotainment at +62.385 s; 189 candidate frames queued |

Wall and monotonic elapsed times agreed in both trials; neither timing guard
fired. Between trials, original `529` restored Propulsion 200 ms after the first
PowerModeOff. The driver automatically restarted the continuous original `529`
renewer after the second result. Thus this tested activation-request encoding
**does not replace `529` for maintaining Propulsion**, even when repeated.
This does not resolve its effect on waking from other states or the later
LocalInfotainment timeout; those were not isolated here.

Post-test observation confirmed restored Propulsion, authorized ADB, boot-completed
and ADB-enabled both 1, and Android uptime 48,143.59 seconds. Android wall time
had reverted roughly 872 days behind the Mac despite the continuous uptime;
it was synchronized again. No causal link to a specific CAN field is established.
The synthetic payloads leave other fields undecoded, so absence of a reboot or
immediate power-state change must not be read as absence of other effects.

The sleep confound does not invalidate the earlier `529` long run: its final progress
sample was 45,386.5 monotonic seconds versus 45,386.285 wall seconds, with no
wall-minus-monotonic progress gap exceeding two seconds across 1,509 samples.

The firmware also contains `RSI HMI Ready`, theft-locked, NoVIN, partial-network,
clock/date and reflash-related logging. A string alone does not identify a
CAN input or its address. Reflash/programming routes are inventoried, not
exercised by these application-field tests.

#### Exact standard-ID slot-3 inventory

Each token is `ID:DLC`, hexadecimal ID and decimal byte count. These are
**configured receive candidates**, not 277 decoded meanings or 277 successful
live tests. Payload validity, calibration, operating state, counter/checksum
rules and optional equipment may constrain actual use. Their callbacks and
our five matching field tests are stronger evidence than a raw occurrence of
an ID-shaped number, but do not establish exhaustive physical-bus coverage.

`016:8 023:8 028:8 029:8 02A:8 02B:8 02C:6 02D:8 032:8 037:6 08C:6 0B5:8 202:6 204:6 20D:6 227:6`
`229:7 22A:7 23B:5 24F:5 25E:8 25F:8 260:8 261:8 262:6 263:8 264:8 269:8 26A:8 26B:8 26C:8 26D:6`
`284:6 404:6 405:6 407:7 40B:5 40C:8 414:6 416:6 41C:5 41E:7 423:6 425:6 429:7 42A:8 430:7 432:7`
`433:8 434:7 436:6 43B:5 442:8 44D:5 452:6 453:8 454:7 455:7 456:8 457:8 458:8 459:8 45A:8 45B:8`
`45C:7 45D:7 45E:7 45F:7 460:7 461:7 462:7 463:7 464:7 465:6 466:7 467:7 468:7 469:7 46B:7 46C:7`
`46D:7 46E:7 46F:7 470:7 471:7 472:7 473:7 474:7 475:7 476:7 477:7 478:7 479:7 47A:7 47B:7 47C:7`
`47D:7 47E:7 47F:7 481:7 482:7 483:7 484:7 485:7 486:7 487:7 488:7 489:7 48A:8 48B:7 48C:7 48D:7`
`48E:7 48F:7 490:8 491:8 492:8 493:8 494:8 495:8 496:8 497:8 498:8 499:8 49A:8 49B:8 49C:8 49D:8`
`49E:8 49F:8 4A0:8 4A1:8 4A2:8 4A3:8 4A4:8 4A5:8 4A6:8 4A7:8 4A8:8 4A9:8 4AA:6 4AB:8 4AC:8 4AD:6`
`4AE:8 4AF:8 4B0:8 4B1:8 4B2:8 4B3:8 4B4:8 4B5:8 4B6:8 4B7:8 4B8:8 4B9:8 4BA:8 4BB:8 4BC:8 4BD:6`
`4BE:8 4BF:8 4C0:8 4C1:8 4C2:8 4C3:8 4C4:8 4C5:8 4C6:8 4C7:8 4C8:8 4C9:8 4CA:8 4CB:8 4CC:8 4CD:6`
`4CE:6 4CF:8 4D0:8 4D1:8 4D2:8 4D3:8 4D4:8 4D5:8 4D6:8 4D7:8 4D8:8 4D9:8 4DA:8 4DB:8 4DC:8 4DD:8`
`4DE:8 4DF:8 4E0:8 4E1:8 4E2:8 4E3:6 4EE:7 506:7 507:7 509:8 50C:7 50D:7 512:8 514:6 515:6 517:8`
`518:7 51B:7 51C:8 51D:6 51E:6 51F:8 520:8 521:6 523:7 524:6 526:8 527:6 528:8 529:6 52A:7 52B:7`
`52C:6 52E:7 52F:6 532:7 533:7 534:8 535:8 537:8 538:6 53A:6 53B:8 53C:6 53D:7 53E:7 53F:6 540:6`
`541:6 544:7 545:7 546:8 55E:8 55F:6 560:6 561:8 562:6 563:7 564:6 56A:8 56B:6 56D:7 573:7 578:6`
`579:6 57E:7 57F:7 580:7 583:7 584:7 586:6 588:7 589:6 591:6 592:6 593:6 594:7 597:5 5A1:6 5A9:8`
`5BA:8 5BE:8 5C3:8 5C9:6 5CE:8`

## The 32 harness IDs repeat unchanged

Every H payload matched its B counterpart and remained fixed across the isolated
restart. Complete identical cycles checked: **180 connected**, **655 isolated
before restart**, **1,681 isolated after restart**; median cycles were
**320.203 / 320.308 / 320.294 ms** (`B:403`, `H:2`, `H:21002`). A
**23.166931-second quiet gap** ends at `H:21002`; no extra startup-only harness
ID appeared. Its first post-gap ID was `0x145`, without proof of a mandatory phase.
All rows below have `U=1`; their source class is H.
H identifies the bench transmitter, not the actual in-vehicle producer.
An ID absent from the working four-ID recipe is not necessarily ignored by the
radio; its individual application meaning and handler still require decoding.

| ID hex | DLC | Period ms | Meaning / confidence | Observed radio effect | Evidence B / H |
|---|---:|---:|---|---|---|
| 016 | 8 | 320.207 | Unknown | Absent from working four-ID recipe; individual application role untested | 133 / 21013 |
| 01E | 7 | 320.204 | Unknown | Absent from working four-ID recipe; individual application role untested | 146 / 21023 |
| 023 | 8 | 320.206 | Unknown | Absent from working four-ID recipe; individual application role untested | 134 / 21014 |
| 028 | 8 | 320.204 | Unknown | Absent from working four-ID recipe; individual application role untested | 135 / 21015 |
| 02B | 8 | 320.201 | Unknown | Absent from working four-ID recipe; individual application role untested | 139 / 21016 |
| 02C | 6 | 320.208 | Unknown | Absent from working four-ID recipe; individual application role untested | 120 / 21011 |
| 037 | 6 | 320.201 | Unknown | Absent from working four-ID recipe; individual application role untested | 144 / 21021 |
| 08C | 6 | 320.204 | Unknown | Absent from working four-ID recipe; individual application role untested | 143 / 21020 |
| 0AA | 8 | 320.204 | Unknown | Absent from working four-ID recipe; individual application role untested | 151 / 21028 |
| 0B5 | 8 | 320.200 | Unknown | Absent from working four-ID recipe; individual application role untested | 140 / 21017 |
| 0C1 | 8 | 320.206 | W: driven-wheel rotational status [G] | Absent from working four-ID recipe; individual application role untested | 155 / 21032 |
| 0C9 | 8 | 320.204 | A: ECMEngineStatus [A] | Not required in four-ID startup; engine/RPM semantics remain an external candidate | 93 / 21009 |
| 0F1 | 6 | 320.204 | A: EBCMBrakePedalPosition [A] | Absent from working four-ID recipe; individual application role untested | 94 / 21010 |
| 145 | 8 | 320.203 | NM-format candidate [N]; initial repetition burst | Original frame wakes SoC/T1; periodic 145 alone did not sustain initialized Propulsion beyond 62.31 s | 10 / 21002 |
| 18E | 8 | 320.202 | Unknown | Absent from working four-ID recipe; individual application role untested | 154 / 21031 |
| 1C6 | 8 | 320.202 | Unknown | Absent from working four-ID recipe; individual application role untested | 153 / 21030 |
| 1E5 | 8 | 320.202 | A: PSCMSteeringAngle [A] | Absent from working four-ID recipe; individual application role untested | 152 / 21029 |
| 1F1 | 8 | 320.206 | A: BCMGeneralPlatformStatus; candidate Run [A] | Not required by demonstrated four-ID recipe; isolated/ordered Off/Accessory candidates did not command shutdown | 150 / 21027 |
| 1F5 | 8 | 320.209 | A: ECMPRDNL2 [A] | Not required in four-ID startup; gear/selector semantics remain an external candidate | 92 / 21008 |
| 204 | 6 | 320.202 | Conflict: battery DBC has DLC 8 [V] | Absent from working four-ID recipe; individual application role untested | 156 / 21033 |
| 20D | 6 | 320.211 | b5-bit7: protected remote-programming-active authenticated; other fields unresolved | Omission still allowed startup; setting the bit enabled the documented T1 programming gate and was retained in the successful CAN5 preparation environment | 160 / 21004 |
| 22A | 7 | 320.203 | Unknown | Absent from working four-ID recipe; individual application role untested | 145 / 21022 |
| 26F | 5 | 320.202 | Unknown | Absent from working four-ID recipe; individual application role untested | 148 / 21025 |
| 435 | 5 | 320.204 | Unknown | Absent from working four-ID recipe; individual application role untested | 147 / 21024 |
| 457 | 8 | 320.204 | Verified opaque 8-byte ProtoKey seed mapping; see signal table | All b0–b7 match RH850 cached Seed 1; alone with base left access gate/ADB unchanged | 141 / 21018 |
| 458 | 8 | 320.204 | Verified opaque 8-byte ProtoKey seed mapping; see signal table | All b0–b7 match RH850 cached Seed 2; fresh single-ID phase left ADB enabled | 142 / 21019 |
| 4B6 | 8 | 320.205 | Unknown | Absent from working four-ID recipe; individual application role untested | 132 / 21012 |
| 50F | 8 | 320.203 | Unknown | Absent from working four-ID recipe; individual application role untested | 149 / 21026 |
| 521 | 6 | 320.206 | Unknown | Not required in four-ID startup; individual signal meaning unresolved | 158 / 21003 |
| 523 | 7 | 320.208 | Unknown | Not required in four-ID startup; individual signal meaning unresolved | 89 / 21005 |
| 529 | 6 | 320.207 | Verified: b1 bit 1 (`0x02`) = IPC HMI Ready | Controlled 0/1 round trips; omission caused HmiInit failure; original 529 alone sustained initialized Propulsion for 95 s | 90 / 21006 |
| 551 | 8 | 320.211 | Unknown | Not required in four-ID startup; earlier isolated probe had uncertain transport | 91 / 21007 |

The cyclic order, anchored at `0x145`, is:

```text
145 521 20D 523 529 551 1F5 0C9 0F1 02C 4B6 016 023 028 02B 0B5
457 458 08C 037 22A 01E 435 26F 50F 1F1 0AA 1E5 1C6 18E 0C1 204
```

Initial connected startup contains **74 identical `0x145` frames** from
`t=.004174–.023655 s`, median spacing approximately **266 µs** (`B:10–87`).
After radio disconnection without an acknowledging peer, the retained tail
repeats `0x458` at approximately **3,814–3,815 frames/s** through `B:265254`.
ACK-enabled H reception restores approximately **100 frames/s** (`H:1–21001`).
This establishes acknowledgement-dependent transmission behavior. CANable sent
no application commands; the fixed loop showed no application response to radio
feedback. Other untriggered behavior remains possible.

## The 40 radio IDs

All rows below are R. `U=1` means no payload change in the first minute of B.
Changing-byte lists identify investigation targets without assigning semantics.
The two one-shot IDs occur once in the entire retained B capture.

| ID hex | DLC | Period ms | U / changing bytes | Radio-transmit meaning / confidence | B line |
|---|---:|---:|---|---|---:|
| 180 | 8 | 1000.239 | 1 | NM-format candidate [N]; steering-command DBC DLC conflicts [A] | 183 |
| 267 | 8 | 250.060 | 3 / b0–b5 | Radio sender confirmed; payload/function undecoded | 97 |
| 424 | 6 | 1000.269 | 2 / b0,b1 | Conflict: vision-track DBC has DLC 8 [O] | 96 |
| 427 | 6 | 1000.245 | 1 | Conflict: vision-track DBC has DLC 8 [O] | 98 |
| 4E4 | 4 | one-shot | 1 | Radio sender confirmed; payload/function undecoded | 99 |
| 4E6 | 8 | 1000.258 | 1 | Radio sender confirmed; payload/function undecoded | 100 |
| 4E9 | 8 | 1000.258 | 1 | W: platform configuration [G]; external DLC 5 [L] and DLC 2 [I08] conflict with this DLC 8 | 101 |
| 4EA | 6 | 1000.249 | 1 | Radio sender confirmed; payload/function undecoded | 102 |
| 4ED | 8 | 1000.235 | 4 / b0,b1,b2,b4,b5,b6 | Radio sender confirmed; access-transition bit correlations below, semantics undecoded | 95 |
| 4EE | 7 | 1000.242 | 6 / b0,b2,b3,b4,b5,b6 | Radio sender confirmed; payload/function undecoded | 103 |
| 4EF | 6 | 1000.259 | 2 / b2 | Radio sender confirmed; payload/function undecoded | 104 |
| 4F0 | 8 | 1000.258 | 1 | Radio sender confirmed; payload/function undecoded | 105 |
| 4F1 | 8 | 1000.251 | 5 / b0,b1,b2,b3,b5 | Conflicting external names: powertrain configuration [G] versus older PCM fuel-pressure claim [I08]; neither A11-validated | 106 |
| 4F2 | 8 | 1000.261 | 1 | Radio sender confirmed; payload/function undecoded | 107 |
| 4F3 | 4 | one-shot | 1 | W: powertrain configuration 2 [G] | 108 |
| 4F4 | 8 | 1000.259 | 1 | Radio sender confirmed; payload/function undecoded | 109 |
| 4F5 | 8 | 1000.260 | 1 | Raw Cadillac-log occurrence only [S1] | 110 |
| 4F6 | 8 | 1000.239 | 3 / b0,b1,b2 | Radio sender confirmed; payload/function undecoded | 111 |
| 4F7 | 8 | 1000.234 | 3 / b2,b3 | Radio sender confirmed; payload/function undecoded | 112 |
| 4F8 | 6 | 1000.253 | 1 | Radio sender confirmed; payload/function undecoded | 113 |
| 4F9 | 6 | 1000.259 | 3 / b1 | Radio sender confirmed; payload/function undecoded | 114 |
| 4FA | 6 | 1000.254 | 45 / b1,b2,b3 | Counter-like progression; unknown meaning | 115 |
| 4FB | 8 | 1000.258 | 1 | Radio sender confirmed; payload/function undecoded | 116 |
| 4FC | 8 | 1000.257 | 4 / b7 | Four recurring payload states | 137 |
| 4FD | 8 | 1000.263 | 2 / b7 | Radio sender confirmed; payload/function undecoded | 117 |
| 4FE | 8 | 1000.248 | 1 | Radio sender confirmed; payload/function undecoded | 118 |
| 4FF | 8 | 1000.257 | 1 | Radio sender confirmed; payload/function undecoded | 119 |
| 500 | 6 | 1000.258 | 1 | Radio sender confirmed; payload/function undecoded | 121 |
| 501 | 8 | 1000.262 | 1 | Radio sender confirmed; payload/function undecoded | 122 |
| 502 | 8 | 1000.267 | 1 | Radio sender confirmed; payload/function undecoded | 123 |
| 503 | 8 | 1000.263 | 1 | Radio sender confirmed; payload/function undecoded | 124 |
| 504 | 8 | 1000.265 | 4 / b1,b6,b7 | Radio sender confirmed; payload/function undecoded | 125 |
| 505 | 6 | 1000.269 | 1 | Radio sender confirmed; payload/function undecoded | 126 |
| 54C | 6 | 1000.274 | 1 | Radio sender confirmed; payload/function undecoded | 127 |
| 54E | 8 | 1000.254 | 4 / b6,b7 | Four recurring payload states | 136 |
| 54F | 8 | 1000.253 | 4 / b6,b7 | Four recurring payload states | 138 |
| 576 | 6 | 1000.269 | 1 | Radio sender confirmed; payload/function undecoded | 128 |
| 587 | 8 | 1000.269 | 1 | Radio sender confirmed; payload/function undecoded | 129 |
| 58B | 6 | 1000.266 | 1 | Radio sender confirmed; payload/function undecoded | 130 |
| 59B | 6 | 1000.270 | 1 | Radio sender confirmed; payload/function undecoded | 131 |

Only `0x4FA` gains distinct payloads later: **623 values in 638 occurrences**,
last at `B:90600`; other full-capture U values equal the first-minute values.
Its progression is not decoded as time, distance or another quantity. Useful
startup transitions include `0x4ED/0x4F1` near **8.554 s** (`B:1340–1341`),
`0x267/0x504` near **8.622 s** (`B:1351–1352`), `0x4F6/0x4F7` near
**30.57–30.67 s** (`B:4450–4464`), and `0x4EF` at **40.081645 s** (`B:5790`).
Temporal coincidence alone does not decode the state.

### Radio-output candidates for the access transition

Six successful gate-transition windows and four failed single-ID/count windows
were compared using stable bits in the eight seconds before a probe and seconds
8–16 after it. These are candidate feedback fields, not named OEM signals:

| Radio ID | Observed stable-bit change | Successful windows | Negative windows with same bit change |
|---|---|---:|---:|
| `4ED` | b0 bit 0: 0→1; b1 bits 2/5/7: 0→1 | 6/6 each | 0/4 |
| `4ED` | b0 bit 1; b4 bits 2/4; b5 bit 6: 0→1 | 5/6 each | 0/4 |
| `4F1` | b0 bit 1: 0→1; b1 bit 7: 1→0 | 5/6 each | 0/4 |
| `504` | b1 bits 4/5: 0→1; bit 6: 1→0 | 4/6 each | 0/4 |

Each bit is numbered from the least-significant bit of its byte. Concurrent
power/network/application changes remain confounders. Do not implement these
as a home-screen, login-success or ADB-state decoder until fresh controls and
receiver/producer code establish the actual field meaning.

## Published candidates

These **Global A**, not A11-specific, definitions match both ID and DLC in the
pinned [OpenDBC powertrain source][A]. DBC notation is `start|length@endian`:
`@0` uses Motorola bit numbering, `@1` Intel; `-` is signed and `+` unsigned.
The start number is not a simple byte offset.

| ID | External candidate fields | Source location |
|---|---|---|
| 0C9 | RPM `15\|16@0+` ×0.25; throttle `39\|8@0+` ×0.392156863; brake `40\|1@0+` | [A:69][A69] |
| 0F1 | Brake switch `1\|1@0+`; pedal position `15\|8@0+` | [A:85][A85] |
| 1E5 | Steering angle `15\|16@0-` ×0.0625 degrees; rate `27\|12@0-` | [A:152][A152] |
| 1F1 | Primary power `1\|2@0+`; backup power `5\|2@0+`; parking brake `36\|1@0+` | [A:165][A165] |
| 1F5 | Selector `27\|4@0+`; transmission state `48\|4@1+`; manual mode `41\|1@0+` | [A:174][A174] |

For `0x1F1`, the DBC enumerates **0=Off, 1=Accessory, 2=Run, 3=Crank Request**
for both power fields ([A:324][A324]). The captured primary field is **2**
(`B:150`), which motivated the controlled tests below. Layout and a plausible
value do not prove a valid A11 wake command. Required counters, checksums,
companion frames and shutdown behavior remain unresolved.

The older E38/T43 [l77rodeo reference][L] additionally names accessory and
run/crank status, backup-mode enable, parking-brake availability, immobilizer
pre-release password/status and remote-start-related inputs for `1F1`.
It lists signal names **without byte/bit offsets**; this is not a second
verified bit-layout decoder or an A11 control specification. Those names do
not identify the missing prerequisite in the negative Off/Accessory trials.

[GMLanDebug][G] supplies the W names without validated A11 layouts.
[l77rodeo's first-hand E38/T43 research][L] supplies older high-speed 11-bit
examples; its shorter `0x4E9` demonstrates why an ID/name match is insufficient.
Original [PCM Hacking experiments][F1] describe firmware TX/RX tables; a [later
discussion][F2] distinguishes specification families and missing convenience
coverage. No complete OPU GM 85633185/A11 CAN-5 dictionary was found in these
inspected sources; this is not a claim that none exists elsewhere.

### Additional older-platform conflicts checked on 2026-11-16

The [2008 Impala notebook][I08] and its [DBC][I08DBC] label `4F1` as PCM fuel
rail pressure, whereas GMLanDebug calls it powertrain configuration data.
The notebook explicitly leaves the pressure formula unconfirmed; a plausible
constant value is not validation. Our `4F1` sender is the radio on the isolated
bench, not an identified PCM. Both external names therefore remain unresolved
leads, not an A11 fuel-pressure or configuration decoder.

For `4E9`, l77rodeo's two examples are each **five bytes**, supporting the
existing length-conflict entry. The Impala notebook lists **two bytes**;
our radio emits **eight**. These platform differences are reasons to reject
automatic ID-based label transfer. No raw external payload or password value
is needed in this reference. The checked sources add no new A11 translation
for the remaining unresolved frames, or for the access-gate candidates
`4ED`, `4F1` and `504`.

Surreal Development's [Cadillac Part 1][S1] explicitly excludes Intel Silverado/
Sierra radios from its studied Qualcomm hardware. Its `0x4F5` raw eight-byte
example overlaps, without a signal definition. Its vehicle VIN IDs
`0x712/0x75F/0x49B` are absent here. [Part 2][S2] describes CAN5 at 500 kbit/s and
an external `0x370` field, `bit37:3`: **Off=1, Accessory=2, Run=3, Crank=4,
Propulsion=5**. `0x370` is absent here; that enum must not be merged with Global A
`0x1F1`. [The ABCs of Global B][S3] provides broader vehicle context. These
in-vehicle findings remain useful where bench validation is unavailable; the
article sources are not a complete DBC or replay package.

## Adapter status and next validation

These are **adapter-generated status records**, not application IDs. Interpretation
follows [Linux CAN error definitions][E]. No bus-off, ACK-error or recovery-to-active
bit is set in these records; they must not be relabeled as such.

| Raw identifier | Interpretation | Startup / later / full count | First evidence |
|---|---|---|---|
| 2000000C | Controller + protocol class; form-error bit, zero controller detail | 10 / 24 / 34 | B:2 |
| 20000004 | Controller class, unspecified detail | 3 / 2 / 5 | B:11 |

Startup status ends at **.023833 s** (`B:88`). Later clusters at
**631.808224–631.811886 s** and **637.551218–637.555347 s** precede the final
retry stream (`B:89198`, `B:90669`). No overflow was reported.

### Active harness communication test — 2026-11-15

`P` is `can5-mcu-probe.jsonl`, containing both TX and RX; B/H remain unchanged.
Before probing, **133,528 data frames over 22.65 minutes** added no harness ID/payload.
A 66-second isolated-harness test used a 5-second baseline, 45-second replay of
**1,893 recorded radio-dependent frames**, 5-second recovery, then three generic
TesterPresent requests (`3E 00`, ISO-TP single frame): standard `0x7DF`/`0x7E0`
and extended `0x18DB33F1`. These are not confirmed harness diagnostic addresses.
All **1,896 queued frames** produced adapter TX echoes, with zero host-pending
entries, reported CAN errors or overflows. Echoes are mailbox-admission reports,
not proof of bus acknowledgement; see the firmware qualification below.
RX counts were **500 / 4,497 / 499 / 1,099** for baseline /
replay / recovery / TesterPresent; every phase retained **only the same 32 IDs**.
Comparison with H found **zero new or changed RX payloads** and no additional
diagnostic/application response. Median per-ID periods were **320.405 / 320.363 /
320.315 / 320.354 ms**; these small differences establish no semantic response.
This is consistent with a fixed cyclic emulator, not proof of receiver-free firmware:
transport participation is not application decoding, and other addresses/inputs remain
untested. No EEPROM, reset, security or programming request was used. After the probe,
all application TX stopped; ACK-enabled receive recording continued. The later
owner-reported working launcher and X5 pin 3 signal-ground configuration are
recorded in the [bench baseline](../../hardware/bench_setup.md#harness-replacement-candidate).
That early probe did not establish long-duration keep-alive; later isolated
`529` hold tests, including an almost-12-hour result, are documented below.

### Radio-only single-cycle result

With CANable ground connected to X5 pin 3 and termination at E, one controlled
cycle queued all 32 harness frames and received 32 adapter TX echoes. It received
80 valid radio frames across 39 IDs and 48 controller-status records. The adapter
then returned to listen-only mode with ACK disabled. Later repeated `0x180` and
`0x267` frames must be distinguished from new application messages.

The correlated UART records include a new startup banner at +0.30 s, explicit
`IPC RX: New Power Level` reports **from SoC** for levels 1/2/3/4 at approximately
+1.17/+1.59/+5.72/+5.74 s, and `ReportCenterStackHMIReady` at +22.48 s. The display
remained off according to physical observation. Thus the SoC was communicating;
neither `CSM_On` nor this HMI-ready event alone proves AAOS/display activation.
The only observed system-state announcement in that startup was Sleep.

### Individual frames with T1 observation

With the SoC previously at power level 0, one original `0x145` was followed by
SoC power-level reports at +1.16 s, first inbound T1 traffic at **+3.169834 s**,
and SoC levels 3/4 plus `CSM_On` near +5.7 s. HMI-ready appeared at +21.25 s,
then SoC power level 1 at +22.62 s. Early Ethernet is a power-path observation,
not proof that AAOS or the display is ready. The T1 record is
`radio-stepwise-t1.pcapng`, correlated with the existing CAN/UART Mac timestamps.

Subsequent single `0x521`, `0x20D` and `0x523` probes produced adapter TX echoes
without new UART state events or T1 traffic in their observation windows. The
starting state differed from the initial power-level-0 baseline. `0x529` and
`0x551` were queued without TX echoes and were cancelled during controller
cleanup: their lack of response must not be classified as a valid negative
application test. Stepping paused after those six attempted IDs, with ACK-only
reception restored and no periodic application TX. Receiver/network availability
must be controlled before interpreting the remaining one-shot probes.

### Queue recovery and slowed one-pass startup

Continuing the one-shot sweep eventually produced USB-queued frames without TX
echoes, CAN RX, UART changes or T1 traffic. These are transport-uncertain attempts,
not evidence that the radio ignores those messages. MODE stop/start and a USB
port reset did not clear the condition. Internal silent loopback (`0x13`, including
timestamps) then drained **62 old TX echoes** with internal RX, without external
application transmission. Internal-loopback records are explicitly classified
separately from radio RX. Normal-mode delivery and radio responses resumed.

Published [candleLight v2.0 transmit code][C] echoes a frame when it enters a
bxCAN hardware mailbox, before acknowledgement. Three unacknowledged frames can
fill the mailboxes; software queues can survive MODE/USB resets. Feature mask
`0xf3` matches that firmware family but does not identify the installed revision.
Thus historical words such as “completed” must be read as adapter TX echoes,
not confirmed wire delivery. The launcher now drains stale work in silent
loopback before normal replay/recovery.

After recovery, **one pass** of all 32 original frames at roughly **0.5-second
spacing** (15.765 seconds from first to last TX) produced radio traffic,
HmiInit and Propulsion, with the display physically reported on. This supports
staged-arrival timing; it does not establish that slow spacing itself is required,
because fast continuous replay also works. AnimationInit occurred at +1.309 s,
after only `0x145`, `0x521` and `0x20D` had been sent. HmiInit followed at +8.544 s
and Propulsion at +23.393 s. Nearest-message timing is a candidate, not a signal
decode.

A later half-second-spaced three-frame prefix restored Propulsion from warm
LocalInfotainment at +1.195 s; its power-mode timeout returned to LocalInfotainment
at +62.208 s. That warm restart is distinct from the SoC-off trials below.

### Startup reduction from verified SoC-off — 2026-11-15

Each trial waited for an explicit UART power-level-0 report from SoC after the
latest application TX, ADB offline/disconnected and at least five seconds without
inbound T1 activity. This is a software shutdown baseline with supply power
retained, not a battery-disconnected cold start. Stale CANable queues were drained
in silent internal loopback, then normal ACK-enabled reception was restored.
Each selected original harness frame was sent **once, in captured order, roughly
0.5 seconds apart**, without cyclic repetition. UART/CAN, passive ADB transport
and T1 observations remained active. Times below are seconds from first TX.

| Frames sent once | AnimationInit | HmiInit | HMIReady | Propulsion | Startup-fault timeout |
|---|---:|---:|---:|---:|---|
| Full 32 | 1.321 | 8.295 | 22.384 | 22.411 | None observed in the trial window |
| First 3 | 1.305 | Not observed | 22.417 | 16.235 | `evSTARTUP_FAULT_TIMEOUT` at 16.225 |
| First 4 | 1.318 | Not observed | 22.692 | 16.235 | `evSTARTUP_FAULT_TIMEOUT` at 16.226 |
| First 16 | 1.312 | 8.734 | 23.373 | 23.400 | None observed in the trial window |
| First 8 | 1.320 | 8.445 | 23.536 | 23.380 | `evSTARTUP_FAULT_TIMEOUT` at 23.371 |
| First 12 | 1.312 | 8.351 | 23.182 | 23.211 | None observed in the trial window |
| First 10 | 1.322 | 8.381 | 22.275 | 22.306 | None observed in the trial window |
| First 8, later software-off repeat | 1.318 | 8.732 | 23.161 | 23.188 | None observed in the trial window |

The first eight IDs are
`145 → 521 → 20D → 523 → 529 → 551 → 1F5 → 0C9`.
The 16-frame reference adds
`0F1 → 02C → 4B6 → 016 → 023 → 028 → 02B → 0B5`.
All three reduced trials received the expected adapter TX echoes (3/16/8), real
radio traffic across the same 40 IDs, SoC level-4 reports and inbound T1 activity.
These observations do not automatically verify the physical display; that was
reported on for the earlier equivalent full-pass experiment.

The three-frame trial activated InfotainmentPN at +1.300 s and powered the SoC,
but skipped HmiInit and enabled the backlight through the startup-fault timeout.
The eight-frame trial received `evCenterStackAnimationReady` at +8.416 s and
entered HmiInit, but its later Propulsion transition also followed a startup-fault
timeout, just before HMIReady. It improves on three frames without reproducing
the 16-frame transition path. **Correction, 2026-11-15:** the initial eight-frame
success classification checked state milestones but missed the timeout event;
milestones alone are insufficient to classify a clean startup. Historical
automated `log_criteria_success` results require this additional fault-event check.

The first-16 result establishes that the later half of the captured loop,
including `0x1F1`, was unnecessary for that SoC-off startup under these conditions.
It does not show that each of those first 16 frames is required. One
trial per subset does not establish reproducibility, a minimum set, required
ordering, or a requirement for slow timing. The four-frame prefix
(`145 → 521 → 20D → 523`) also skipped HmiInit and used the timeout fallback;
all four TX echoes, SoC level 4, T1 activity and the same 40 radio IDs were observed.
The first-12-frame trial also completed without an observed startup-fault timeout,
with 12 TX echoes, the same 40 radio IDs, SoC level 4 and T1 activity. Its extra
four frames beyond the first eight are `0F1 → 02C → 4B6 → 016`; their individual
necessity and the reproducibility of this reduced sequence remain unestablished.
The subsequent first-10-frame trial, ending with `0F1 → 02C`, also completed
without a startup-fault timeout: 10 TX echoes, SoC level 4, T1 activity and the
same 40 radio IDs. It began only after verified SoC power level 0 and shutdown;
the preceding CAN5 SecurityAccess test did not request an ECU reset. After the
10-frame startup, PowerModeOff/LocalInfotainment returned about +64.6 seconds
from first TX when no further application sequence was sent.

The eight-frame fault occurred just 0.165 seconds before its HMIReady report;
SoC/HMI readiness timing varies between trials. Its late timeout therefore does
not by itself prove a required message among frames 9–16. Repeat matching
eight-frame trials before attributing that difference to a missing signal.
The later software-off eight-frame repeat completed cleanly with all eight TX
echoes, SoC level 4 and the same 40 radio IDs, directly confirming that frames
9–16 are not universally required for these startup milestones.

Perfect and repeat the startup path before assigning keep-alive roles or testing
explicit Off payloads. Compare matching initial states and inspect startup-fault
events as well as AnimationReady, HmiInit, HMIReady, Propulsion, SoC and T1 markers.
Repetition can supply frames across initialization stages, but these observations
do not yet identify a particular stage's required frame or decode its signal.

### Eight-frame startup after physical 12 V removal — 2026-11-15

After confirmed physical 12 V removal, the test waited for fresh timestamped
RH850 UART lines, then delayed 0.5 seconds before sending the first eight
original frames once at approximately 0.5-second spacing. No UDS ADB-enable
request was sent during this boot. Application TX then stopped with ACK enabled.
This is a distinct initial condition from the software-shutdown trials above.

| Marker | Seconds from first CAN TX |
|---|---:|
| Sleep, before application TX | -0.269 |
| SoC power levels 1 / 2 | 0.267 / 0.585 |
| AnimationInit | 1.260 |
| SoC power levels 3 / 4 | 4.836 / 4.846 |
| HmiInit | 7.867 |
| HMIReady / Propulsion | 20.966 / 20.993 |
| USB ADB offline / authorized device | 28.335 / 28.339 |

All eight adapter TX echoes and 38 radio IDs were observed in the test window;
no startup-fault timeout occurred. Thus eight frames can complete this path
under a physical power-cycle baseline. This does not establish reproducibility,
minimum frame count or equivalence with the earlier software-off baseline.
The display showed a **Start Your Vehicle** restriction stating that a restart
required starting the vehicle before personal information could be accessed.
That display state coexisted with UART Propulsion; neither alone defines every
Android vehicle/security state.

ADB became authorized without a manual enable during this boot. Live reads
confirmed `adb_enabled=1`, `development_settings_enabled=1`, `init.svc.adbd=running`
and `persist.sys.usb.config=sys.usb.config=sys.usb.state=adb`. Android reported
`ro.boot.bootreason=cold`, `sys.boot.reason=cold`, both `sys.boot_completed` and
`dev.bootcomplete` equal to 1, and `sys.user.0.ce_available=true`; kernel uptime
matched the new boot. These observations weigh against a simple standby resume
or Android merely being early in boot. The radio clock was synchronized to the Mac.

The cause of automatic ADB availability is unresolved. Persistent configuration,
a local boot/keyguard path, a prior UDS side effect despite NRC `31`, and an effect
of the eight-frame traffic have not been isolated. Decompiled GM keyguard code
has a local `RDMSADBEnable` call, but no matching live enable event was found
in the retained Android log buffers; that code was not byte-matched here.
A discriminating repeat must explicitly establish ADB disabled before power-off,
control the post-power-on traffic and check Android boot completion. Do not
reinterpret the rejected UDS sweep as a successful ADB-enable command based
only on this later boot.

### Full sequence clears the restriction and disables ADB — 2026-11-15

On that same physical eight-frame boot, Android was already boot-complete with
the vehicle-start restriction displayed and `adb_enabled=1`. A subsequent
**10-second full 32-frame replay** queued 943 frames in the captured cyclic order.
UART reported PowerModeOn/Propulsion and a ProtoKey-to-SoC transmission during
the observation window. USB ADB became offline and disconnected **4.676 seconds
after the first full-sequence TX**. The display changed to the AAOS home screen,
the vehicle-start restriction disappeared, and the Settings UI showed
**USB Debugging Off**. No ADB-disable UDS request, local Android setting write,
ECU reset or second power cycle was issued for this comparison; the earlier
Mac-clock synchronization was the only preceding Android runtime change.

This demonstrates an observed CAN-influenced vehicle/UI and ADB-configuration
transition under the bench conditions. AAOS did not need to boot a second time:
the extra traffic completed or changed a state while Android was already running.
The eight-frame set does not establish a decoded vehicle-Off value, despite the
display restriction; UART had already reported Propulsion. The trigger may be
one of the 24 additional IDs, a companion combination, or repetition/timing.
ProtoKey transmission is correlated, not proof of the specific state machine or
a dedicated CAN ADB-control command. The earlier rejected UDS routine is not
needed to explain the immediate transition, but a retained earlier side effect
has not been excluded by a clean control.

Reproduce the restricted eight-frame boot, then repeat only those same eight
frames before adding any IDs. The comparison changed both the ID set and
one-pass versus cyclic transmission; repetition of the original eight could
be sufficient. If that preserves the restriction/ADB state, isolate additions.
Track the actual UI restriction and ADB state alongside boot completion and UART
power mode: HmiInit/Propulsion alone do not distinguish the two observed Android
states. Avoid calling the eight-frame case fully equivalent to the harness just
because it powers the SoC/display and reaches the UART startup milestones.

### Eight-frame repetition control from software shutdown — 2026-11-15

With UART SoC power level 0 and `ShutdownExit_Complete` already observed, supply
power was retained for another eight-frame one-pass startup. It reached HmiInit
at +8.732 seconds and Propulsion at +23.188 without a startup-fault timeout.
ADB was disconnected after the observation window. Repeating **only those same
eight IDs** for 10 seconds, followed by observation, left ADB disconnected;
the USB enumeration watcher recorded no new attachment or configuration change
during this comparison. Application TX then stopped with ACK enabled.

This did not reproduce the ADB-enabled, vehicle-restricted state seen after
physical 12 V removal. It therefore cannot determine whether eight-frame
repetition alone clears that state or whether one of the other 24 IDs is needed.
The next matched control requires physical 12 V removal, reproduction of the
ADB-enabled restricted boot, then eight-frame repetition before any additional
IDs. A difference between software shutdown and physical power loss is a lead,
not yet proof of a retained VIP/security state or the cause of automatic ADB.

### Physical-cycle repeat and manual-ADB retention control — 2026-11-15

A second physical power cycle again used the first eight frames once after
fresh RH850 UART activity. HmiInit occurred at +9.301 seconds, HMIReady at
+22.753 and Propulsion at +22.781, without a startup-fault timeout; eight TX
echoes and 38 radio IDs were observed. The same vehicle-start restriction was
reported, but **ADB stayed disconnected**. A subsequent 10-second repeat of
only those eight IDs also left ADB disconnected, with no USB attach/configuration
event. Thus the restriction is reproducible without ADB availability; these
states must not be treated as equivalent. That cycle did not provide an
ADB-enabled starting state for testing which traffic disables it.

The exact prompt is present in the external GMSystemUI resources as
`userprofile_5_4_engineCommand_csm` and
`userprofile_5_4_engineDescription_csm`, referenced by
`keyguard_proto_key_view.xml` using `GMKeyguardProtoKeyView`. Decompiled
`KeyguardProtoKeyViewController` resumes through the view's `k(true)` and calls
`k(false)` on detachment. The GM subclass routes these to its local ADB-handler
path. The reference security model tests `persist.sys.gm.encryption` and
`vendor.gm.security.state` to select ProtoKey mode. This is static family-level
evidence, not a byte-matched live trace; the helper-handler decompilation contains
invalid control flow and must not be used to assert exact enable/disable dispatch.
The prompt's restart wording alone does not establish a CAN restart flag.

For the next retention control, a 10-second full-32 replay restored the ordinary
interface and application TX then stopped. USB debugging was enabled manually
in Settings. Live reads verified `adb_enabled=1`, boot completion 1 and all three
USB configuration/state properties equal to `adb`. The USB watcher detected
**`8087:09ef`**, interface **FF/42/01 (ADB)**, and authorized ADB was available.
The radio clock was synchronized to the Mac. `persist.sys.gm.encryption=true`
but `vendor.gm.security.state` read empty, further limiting a direct application
of the unmatched static model.

The controlled physical power cycle after that manual enable reproduced the
restriction **and authorized ADB** using only eight frames once. HmiInit occurred
at +7.772 seconds, HMIReady at +21.328 and Propulsion at +21.355; no startup-fault
timeout occurred. Eight TX echoes and 38 radio IDs were observed. The USB watcher
again detected `8087:09ef`, FF/42/01. Live reads verified a cold, boot-complete
Android instance, `adb_enabled=1` and all three USB configuration/state properties
equal to `adb`; the clock was synchronized again. This supports retention of the
prior manual enable through the restricted startup, rather than requiring a fresh
ADB-enable UDS request. It does not exclude another persistent setting or local
boot action as part of the mechanism.

A 10-second repeat of **only the same eight IDs**, while ADB was enabled,
left ADB authorized with `adb_enabled=1`; the restriction was still reported.
Unlike the earlier control that started with ADB already off, this directly
shows that the tested eight-frame repetition alone did not reproduce the
full-sequence transition. Adding original `0x1F1` once, then repeating the base
eight plus original `0x1F1` for 10 seconds, also left ADB authorized with
`adb_enabled=1`; no candidate power bits were mutated.

### Added-message groups with retained ADB enabled — 2026-11-15

On that same restricted boot, each exploratory group repeated the original
eight-frame base plus the listed additions for 10 seconds, with an 18-second
observation window per group. Groups were sequential, **not cumulative**; however,
earlier messages may have left a retained effect. The scan stopped when ADB changed.

| Added original IDs | ADB result |
|---|---|
| `0F1 02C 4B6 016` | Remained authorized, `adb_enabled=1` |
| `023 028 02B 0B5` | Remained authorized, `adb_enabled=1` |
| `457 458 08C 037 22A 01E 435 26F` | Offline at +6.190 s, disconnected at +6.193 s from group start |
| `50F 1F1 0AA 1E5 1C6 18E 0C1 204` | Not sent by this scan |
| Full 32 control | Not sent by this scan |

During the positive group UART reported a ProtoKey-to-SoC transmission at
+0.853 seconds. The independent USB watcher recorded the `8087:09ef` ADB
interface detaching at +6.638 seconds. This is an application/USB transition
lead, not evidence of a power-cycle or physical cable removal. Physical
observation confirmed that the restriction cleared and the AAOS home screen
became visible after this group. Android was already boot-complete before it;
this is a vehicle/security-access transition, not a newly demonstrated kernel
or AAOS boot. ADB loss alone does not establish that USB Debugging was set Off
in this particular trial; unlike the earlier full-32 test, its Settings toggle
has not yet been checked.

These eight additions are the first positive group, not yet a proven minimal
or independently sufficient set: the earlier groups and `0x1F1` had already
been sent on this boot. Reproduce this group from a fresh, manually-ADB-enabled
restricted baseline, then split it while retaining the same eight-frame base.
The next planned split is `457 458 08C 037` versus `22A 01E 435 26F`, with a
fresh-cycle reproduction required before assigning causality to either half.
Keep the startup milestones, ProtoKey event, UI restriction, ADB setting and
USB enumeration as separate observations.

### Fresh-cycle first-half isolation — 2026-11-15

The next cold eight-frame startup again reached HmiInit/Propulsion without a
startup-fault timeout and showed the restriction, but ADB did not enumerate
despite verification of `adb_enabled=1` and persistent USB `adb` before power-off.
The ADB-dependent split driver therefore stopped before sending additions.
Manual ADB retention is not deterministic across these observed trials; it
remains a supported explanation for one boot, not a guaranteed startup behavior.

With the restriction physically confirmed, a separate test repeated **only the
original eight-frame base plus `457 458 08C 037`** for 10 seconds. CAN capture
recorded **372 queued frames** across 10.004 seconds from command start, and
UART reported ProtoKey-to-SoC transmission at **+0.978 seconds**. The display
cleared to the home screen. Neither `22A 01E 435 26F` nor the earlier unrelated
groups were transmitted on this fresh cycle. Thus this first half, with the
eight-frame base, is independently sufficient for the observed gate transition;
the individual required frame(s) and repeat count remain unknown.

The small observer helper failed after queueing the replay with
`ValueError: I/O operation on closed file.` because a log writer shadowed its
UART file handle. The independent bounded transmitter and CAN/UART captures
continued; their records establish the actual replay duration and ProtoKey event.
The helper handle collision was corrected. This was not a CAN/USB transport fault.

USB debugging was then manually re-enabled and verified authorized, with
`adb_enabled=1`, persistent USB `adb` and Android boot complete before the next
power cut. The next planned split tests `457 458` against `08C 037`, always
alongside the original eight-frame base and with the UI restriction as the
primary outcome when ADB is unavailable.

### Fresh-cycle 0x457 and 0x458 pair — 2026-11-15

Another physical eight-frame startup reproduced the restriction with ADB absent.
HmiInit occurred at +7.681 seconds and Propulsion at +21.093, without a
startup-fault timeout. The test then repeated **only the eight-frame base plus
`457 458`** for 10 seconds. Physical observation confirmed that the restriction
cleared to the AAOS home screen; `08C`, `037` and the remaining harness IDs were
not sent on this fresh cycle. ADB remained unavailable before and after the
addition, so this run establishes the gate transition rather than an ADB toggle.

UART recorded ProtoKey-to-SoC transmissions at +0.017 and +1.025 seconds from
the pair command. The first marker may precede the added IDs' original scheduled
slots and must not be attributed to them merely because it follows the command.
The UI outcome is the positive endpoint. Either ID, their combination, or repeated
arrival may be sufficient; the next fresh-cycle test adds only `457` to the base.

### 0x457 alone and subsequent 0x458 tests — 2026-11-15

On a fresh physical eight-frame boot, ADB was retained and the restriction was
confirmed. Repeating the base plus **only `457`** for 10 seconds did not clear
the restriction; ADB remained authorized with `adb_enabled=1`. UART reported
ProtoKey-to-SoC transmissions about once per second during its observation
window. These transmissions alone do not establish successful validation or
unlock, or prove that `457` caused the periodic activity.

On that same boot, **one original `458`** after the `457` trial left ADB enabled
over a 12-second observation window. The next phase repeated **base + `458`**
for 10 seconds. The restriction cleared to the home screen, and ADB became
offline at +4.425 seconds and disconnected at **+4.428 seconds** from that phase
start. The independent observer subsequently recorded reconnection after manual
USB-debugging enable. No later harness IDs or UDS ADB request were added.

This distinguishes the tested isolated single arrival from the successful
repeated phase, but `457` had already been sent on this boot. It may have primed
a retained state or supplied a companion value; `458`-only sufficiency from a
fresh restricted baseline remains untested. The next physical-cycle test adds
only repeated `458` to the original eight, with no `457` on that boot.

Before that next power cut, manual USB debugging was verified authorized again:
`adb_enabled=1`, persistent USB configuration `adb`, Android boot complete.
Application TX was stopped with ACK-enabled observation retained.

### Fresh-cycle 0x458-only addition — 2026-11-15

After a physical power cut with manual ADB enable verified beforehand, the
eight-frame startup reproduced the restriction and retained authorized ADB.
HmiInit occurred at +7.845 seconds and Propulsion at +21.146, without a startup
fault. Repeating **only base + `458`** for 10 seconds, with no `457` sent on this
boot, left ADB authorized with `adb_enabled=1`. UART again showed roughly
one-second ProtoKey-to-SoC transmissions during the observation window; those
events alone do not prove successful access-state transition. The independent
ADB endpoint remained enabled through that observation window.

Thus neither the fresh `457`-only nor fresh `458`-only test reproduced the pair's
ADB transition. The successful `458` repeat after an earlier `457` trial may
depend on a retained companion value or timing.

The reverse-order same-boot control then repeated **base + `457`**, with `458`
already received earlier. ADB went offline at +3.720 seconds and disconnected
at **+3.727 seconds** from this reverse phase. The home screen was reported
while this phase was being tested; no second `458` phase or full harness replay
was needed. USB ADB later returned after manual enable.

Both orderings of the exploratory repeated-message tests therefore produced
the transition, whereas each fresh single-ID phase left ADB enabled. This fits
a retained companion-value or multi-stage mechanism, but does not decode either
payload or establish that strict order is irrelevant for single arrivals. The
next fresh-cycle control sends one captured `457 → 458` pair, at its original
relative spacing, after the eight-frame restricted startup. If it fails, a bounded
pair repeat is the positive control. Manual ADB enable was verified again before
that next power cut, with application TX stopped.

### One closely spaced pair versus repeated pairs — 2026-11-15

A fresh eight-frame startup reproduced the restriction with ADB enabled.
Exactly **one `457 → 458` pair** was then queued, with a measured **11.733 ms
host-queue gap**, using the captured original relative scheduling. Both frames
received matching adapter TX echoes. After 18 seconds ADB remained enabled and
the restriction was physically confirmed still visible. The roughly one-second
ProtoKey-to-SoC reports continued; they are not an unlock-success indicator.

The same-boot positive control repeated **base + `457 458`** for 10 seconds.
The restriction cleared to the home screen and ADB disconnected, followed by
manual re-enable. Thus the tested single pair did not reproduce the successful
repeated profile. This does not yet establish the minimum count, required
on-wire timing, whether every single pair was acknowledged, or the role of
concurrent base traffic in the positive control. Application TX was stopped
and manual ADB enable verified before the next cycle. The next count control
sends exactly two pairs at approximately the captured 320-ms cycle interval.

### Exact-count pair controls with automated physical power — 2026-11-15

The smart outlet is now connected to the bench supply. Its toggle-only Shortcut
was validated, the starting Off state established, and subsequent transitions
tracked. At least **10 seconds after each completed toggle** separates commands.
Fresh UART confirms power-on, with application TX stopped before power-off;
see [bench power control](../../hardware/bench_setup.md#controlled-physical-power-cycling).

The two-pair fresh-cycle test sent exactly **four additional frames** after the
eight-frame startup. After observation ADB remained authorized with
`adb_enabled=1`. A read-only `uiautomator` hierarchy streamed through stdout
confirmed both the **Start Your Vehicle** text and ProtoKey view were still
present; the hierarchy itself was not saved. This establishes a negative UI
outcome independently of a human display report. The next fresh-cycle test
sent exactly four pairs (eight frames) at the captured cycle interval. ADB was
already absent before its pair phase; UART ProtoKey transmissions continued
roughly once per second afterward. Its UI outcome awaits physical confirmation.

The exact-count phases send only the selected pairs after the initial startup,
whereas the successful repeated controls also refresh the original eight-frame
base. Pair count alone is therefore not yet isolated. A same-boot base-only repeat
after receipt of both IDs can test whether refreshed companion traffic completes
the transition using retained pair values. A stricter count test must maintain
the same base traffic throughout and vary only the added pair count.

### UART correlation with the access gate — 2026-11-15

HmiInit, HMIReady and Propulsion occur while the restriction remains visible;
none is a home-screen acknowledgement. Controlled single-ID tests correlated
`457` with **Seed 1 cached** and `458` with **Seed 2 cached** in the PROTOKEY
logger. Successful gate transitions show both seed-cache events, a final
ProtoKey-to-SoC transmission and cessation of the roughly one-second retry loop.
Restricted cases continue missing-seed/retry reports. This is a useful observed
exchange-completion correlation, not a direct display/compositor message or a
decoded payload/checksum specification. Seed values are omitted here.

In particular, the isolated one-/two-/four-pair phases did not show the same
seed-cache events as the successful base-plus-pair repeats. USB TX echoes do
not prove those frames were consumed by the application. Receiver/network
state and refreshed companion traffic remain possible explanations; increasing
pair count alone is not yet justified as the fix. The base-only repeat after
four pairs also left the restriction visible, with the missing-seed/retry loop
continuing. That delayed probe does not exclude a requirement for simultaneous
fresh base and pair traffic. The literal missing-seed index is not a sufficient
decoder: missing/cached labels are not entirely consistent across these windows.

### ACK-controlled repetition comparison

The radio remained powered. Initial ACK-enabled reception with no application TX
produced no new CAN/UART activity. A bounded 30-second repeat phase, keeping ACK
enabled, queued **2,894 frames** in the captured order (90 complete cycles plus a
partial cycle); all received adapter TX echoes. Controller warnings were present,
so this was not an error-free run. The display turned on according to physical
observation. UART now reported **HmiInit (0x2)** and then **Propulsion (0x6)**,
which were absent from the single-cycle startup. No additional application ID or
changed payload was introduced: the same 32-frame profile was repeated.

After repeating TX ended, ACK-enabled reception continued. **62.61 seconds later**
UART reported `evPowerModeOff` and **LocalInfotainment (0x8)**. Thus ACK-only
participation did not sustain Propulsion; periodic application traffic matters for
that observed operating state. Whether the display remains lit in LocalInfotainment
is a separate physical observation. This does not identify the minimal keep-alive
frame set or prove that `0x1F1` alone controls the transition.

### Isolating 0x1F1 and 0x145

All tests retained ACK-enabled reception and used original captured payloads;
no candidate Off/Accessory bits were changed.

| Test | Observed result |
|---|---|
| One original `0x1F1` | RH850/SoC startup activity, then return to power level 1; no Propulsion |
| Original `0x1F1`, repeated 30 s | No HmiInit/Propulsion or radio CAN data observed |
| Original `0x145`, repeated 30 s | Radio CAN traffic and startup/HMI-ready events; no HmiInit/Propulsion |
| `0x145` + `0x1F1`, repeated 30 s | Radio CAN traffic and startup; still no HmiInit/Propulsion |
| Full 32-frame positive control | Reproduced HmiInit and Propulsion |
| Other 31 frames, omitting `0x1F1`, repeated 90 s | Sustained Propulsion beyond the previous power-mode timeout without `0x1F1` |

The 31-frame omission test concerns an already initialized state; separately,
the first-16 SoC-off startup above also excluded `0x1F1`. Neither establishes
requirements after a physical power disconnect. Other original frames or combinations
must account for the full loop's successful operating-state transition. Do not
implement `0x1F1` as a validated A11 Off/Run selector or invent a Service Mode
value: the external DBC's value 3 is Crank Request, and UDS session/programming
prerequisites are separate matters.

`0x145` begins with node byte `0x45` and `0x180` with `0x80`; both have second
byte `0x40`. [AUTOSAR CAN NM R24-11 §§7.6/7.11][N] supports a configurable
byte-0 node ID / byte-1 Control Bit Vector layout, where bit 6 is PN-information
present. This fits a partial-network-management hypothesis, but does not prove
the GM CAN-ID assignment or the meanings of remaining PN bits. In particular,
`0x40` is not the generic active-wakeup bit. No payload mutation follows from
this format match alone.

### ADB observation and power-state limits

`radio-only-rx.adb.jsonl` records USB transport state changes with the same Mac
wall/monotonic clocks as CAN/UART, excluding device identities. The observer uses
`adb track-devices`, with no periodic Android shell polling. One power snapshot
while RH850 reported LocalInfotainment showed Android Awake, `mStayOn=true`, and
held wake/display suspend blockers. Power settings were left unchanged.
LocalInfotainment is therefore not proof of AAOS shutdown, and an ADB disconnect
alone could also reflect USB/adbd changes or suspend. Correlate transport changes
with UART power transitions and physical display behavior. At that checkpoint,
Service Mode and an explicit Off command were unestablished. Later tests in this
document validated529 power On/Off and, on2026-11-17, the20D power-mode2 input
that satisfied the factory-reset gate; see the direct-CAN factory-reset section.

### Shutdown after application messages cease

After the 90-second, 31-frame omission test ended, no further application CAN
frame was queued. ACK-enabled reception and observation remained active; no
candidate Off payload or power-mode bit modification was sent. Relative to the
last application TX, UART and ADB recorded:

| Elapsed seconds | Observation |
|---:|---|
| 62.464 / 62.470 | `evPowerModeOff`, then LocalInfotainment (0x8) |
| 662.447 | HmiInactive (0x3) |
| 664.485 | Sleep (0x0) |
| 690.506 / 690.509 | USB ADB offline, then disconnected |
| 693.897 / 693.903 | Power level 0, explicitly reported from SoC |
| 694.431 | `ShutdownExit_Complete` |

The display was physically reported off. This establishes an observed timeout
shutdown path after messages stopped, including approximately 600 seconds in
LocalInfotainment, without a requested battery-power interruption. It does not
establish an immediate Off command, VIP sleep current, or the minimum message
set. Android's earlier Awake/stay-on snapshot did not prevent this later SoC
shutdown. Keep ADB loss as corroboration of the UART transitions, not sole proof.

### Post-boot keep-alive isolation — 2026-11-16

After establishing Propulsion with the known four-ID recipe, each candidate
retained normal ACK-enabled reception and the captured 320.270-ms per-ID cycle.
The full four-ID profile restored the operating baseline between trials.
No payload change was used in the initial two comparisons:

| Periodic traffic after startup | Observed result |
|---|---|
| Original `145` only | PowerModeOff at +62.303 s, LocalInfotainment at +62.310 s; 195 queued / 195 TX echoes |
| Original `529` only | Propulsion sustained for 95.142 s with no PowerModeOff; 297 queued / 297 TX echoes |
| Original `457+458` only | PowerModeOff at +62.599 s, LocalInfotainment at +62.605 s; 390 queued / 390 TX echoes |
| Original `145+529` | Propulsion sustained for 95.136 s; 592 queued / 592 TX echoes |
| `529` with only b1 bit 1 cleared | UART confirmed IPC HMI Ready=0; Propulsion sustained for 95.066 s; 297 queued / 297 TX echoes |

Thus original `529` alone is sufficient for the observed post-boot hold interval,
whereas `145` alone and the seed pair alone are not sufficient to hold Propulsion.
The ready bit does not have to remain asserted after startup. The later
sustained b1 bit 7 clear/restore test identified the power-mode selector while
packet repetition continued. Thus both the selector and the known message-
freshness timeout matter; arbitrary `529` payloads are not validated.
The seed pair's access-gate role is separate from the demonstrated keep-alive.

After the comparisons, the original ready=1 payload was restored. A renewable
`529`-only stream at the captured period was left active for longer observation,
with CAN/UART/USB monitoring retained. The 2026-11-16 follow-up confirmed
43,131 seconds (11 h 58 min 51 s) of continuous observation without the
watcher's PowerModeOff or SoC power-level-zero failure condition. At that point
139,080 frames had been queued with 139,080 adapter TX echoes; echoes alone
are not wire-level ACK evidence. This extends the original 95-second result to
almost 12 hours. Stop that transmitter before a physical power cycle to avoid
filling the adapter's unacknowledged TX queues.

At the follow-up, Android uptime was 43,747.84 seconds (12 h 9 min 8 s),
boot-completed and ADB-enabled both read 1, and Android wall time was within
one second of the Mac. UART remained active. Its bracketed timestamp repeatedly
wrapped near 429,497 ms: adjacent samples around four wraps implied periods of
429,491–429,497 ms after accounting for host elapsed time. These counter drops
are not reboot evidence; use host timestamps, Android uptime and actual boot/
power-state markers when correlating UART events. The underlying counter
implementation has not been verified.

The first phase watcher required a new Propulsion announcement when the radio
was already in that state and stopped between trials with
`RuntimeError: No verified Propulsion baseline after four-ID restore`.
It was corrected to initialize from the retained UART state and preserve a
verified unchanged baseline. Completed trial outcomes were retained; the
remaining tests resumed under that corrected observer. No radio reset or
programming command was involved in the observer correction.

### Candidate explicit Off test — 2026-11-15

After the first-12-frame sequence restored Propulsion from LocalInfotainment,
one experimental `0x1F1` frame set both external-DBC primary and backup power
fields to **0 (Off)**. Only byte-0 mask `0x33` changed; the remaining captured
payload was retained. This tests the candidate vehicle power-mode Off value,
not Accessory (1), Run (2), or a separate engine-stopped/RPM signal. The A11
interpretation, checksum and acceptance requirements remain unvalidated.

The single Off frame was followed 12 seconds later by a five-second repetition
at the captured per-ID period: **17 candidate Off frames total**. Across the
12-frame wake and 17-frame Off test, controller counters increased by 29 queued
frames and 29 TX echoes; echoes remain mailbox reports rather than ACK proof.
Normal ACK-enabled reception and the existing UART/CAN/T1/ADB observations stayed
active. There was no immediate UART power-mode transition after either Off phase.

`evPowerModeOff` and LocalInfotainment eventually occurred **58.973 seconds after
the last wake-sequence TX**, 34.429 seconds after the single Off frame and
17.585 seconds after the final repeated Off frame. This is consistent with the
existing inactivity path, not evidence of an explicit Off response or accelerated
SoC shutdown. The candidate Off frames did not visibly reset that power-mode timer.

Across the SoC-off prefix trials, PowerModeOff occurred at +62.221 seconds from
first TX for both the three- and four-frame sets, +64.606 for eight, and +64.611
for both 12 and 16. Thus the deadline is not universally 62 seconds after the
last arbitrary CAN frame. The traffic sustaining the operating state and the
specific timer-reset signal remain unidentified. None of these tests establishes
that any received CAN frame is a keep-alive or that the full shutdown grace
period can be bypassed with the candidate `0x1F1` value.

### Candidate Accessory and ordered mode transitions — 2026-11-15

With Propulsion restored using the first 12 original frames, the same controlled
test set both candidate `0x1F1` power fields to **1 (Accessory)**: one frame,
then 12 seconds later a five-second repeat (16 more frames). No immediate UART
power-state transition followed. PowerModeOff and LocalInfotainment appeared
about +65.6 seconds from the beginning of the warm-wake test, following the
existing timeout pattern. The 12-frame wake plus 17 Accessory frames produced
29 queued frames and 29 adapter TX echoes. This does not validate Accessory
control or distinguish an ignored value from an unmet acceptance prerequisite.

A subsequent ordered test started from the last UART-reported LocalInfotainment
state, with no full harness replay between steps. It sent candidate values
**0 → 1 → 2 → 1 → 0** (Off → Accessory → Run → Accessory → Off), each repeated
for five seconds at the captured per-ID period followed by five seconds of
observation. Every step produced 16 queued frames and 16 TX echoes, 80 total.
No new UART power-state transition was observed during the 50-second test;
the last reported state remained LocalInfotainment. The initial transmitted Off
value did not establish an actual powered-off baseline.

Stateful Off/Accessory/Run sequencing remains a plausible requirement for the
correct A11 signals. This negative test shows only that ordered changes to the
two candidate `0x1F1` fields, with the rest of that frame retained and no companion
application traffic, did not control the observed state. Wrong signal mapping,
integrity checks, companion messages or starting-state prerequisites remain
possible. Run is a candidate vehicle power mode, not proof of engine rotation;
no separate engine-stopped/RPM manipulation or Crank Request was tested.

First establish a reproducible reduced startup path; then isolate traffic that
prevents the power-mode timeout. A direct Off command remains to be identified
separately from the observed timeout path. Future vehicle captures should
retain bus/platform, operating state and timing so this reference can gain validated
mappings without treating the bench as a complete car.

### Direct CAN5 ADB-enable diagnostics — 2026-11-15

Earlier MDI2 diagnostic attempts cannot establish this physical CAN5 path: the
MDI2 attempt lacked its required external 12 V supply. Historical MDI2-labelled
response attribution requires verification against original transport records;
the separately documented T1-UDS rejection is not a CAN5 result. The direct test
below used the powered CANable connected to the radio's X6 CAN5 pair at 500 kbit/s,
with the harness MCU absent. The queued startup trial was cancelled before this
test, and the live CAN/UART controller was restarted with bounded diagnostic-frame
support; captures continued in their existing files with a brief restart gap.

After a 12-frame warm wake, actual received diagnostic responses established:

| Request CAN ID | Actual response CAN ID | TesterPresent result |
|---|---|---|
| `0x14DA80F2` | `0x14DAF280` | `3E 00` → `7E 00` |
| `0x14DA80F1` | `0x14DAF180` | `3E 00` → `7E 00` |
| `0x18DA80F1` | None observed | No response within 2 seconds |
| `0x18DA80F2` | None observed | No response within 2 seconds |

These are extended 29-bit CAN IDs, excluding gs_usb's host-side EFF flag.
**Correction, 2026-11-15:** direct CAN5 replies use `14DA`, not the archived
gateway-route `145A` response pattern. An initial host response filter expected
`145A` and missed a captured `14DA` reply; the filter was corrected before the
routine trials. That host-filter miss is not a radio nonresponse.

The reported ADB-enable candidate is UDS
`31 01 03 32 DD 42 10 01`, with unknown domain `DD`. Its eight-byte UDS payload
was transported using ISO-TP first/consecutive frames and actual radio flow
control, rather than placed into a single invalid classic-CAN frame.

| Direct F2/CAN5 test | Observed response |
|---|---|
| Domain `00`, default session | `7F 31 31` |
| Enter extended session, `10 03` | `50 03 00 64 01 F4` |
| Domains `00`, `01`, `02`, `FF`, extended session | Each `7F 31 31` |
| Enable-only sweep, all 256 domains, extended session | **256 × `7F 31 31`**, no other final response or timeout |
| Follow-up level-1 SecurityAccess over the same direct CAN5 path | 31-byte all-FF seed; documented response accepted with **`67 02`** |
| Enable-only sweep, all 256 domains, after that SecurityAccess grant | **256 × `7F 31 31`**, no other final response or timeout |
| Restore default session, `10 01` | `50 01 00 64 01 F4` |

The initial sweep had no SecurityAccess grant. A separate follow-up entered
extended session, completed level-1 SecurityAccess with **`67 02`**, kept that
session alive with TesterPresent and repeated all 256 enable-only requests.
Every request was again rejected with `7F 31 31`; default session was restored
afterward. The seed/key exchange used memory-only payload handling; CAN/UART
capture retained redacted exchange metadata and the grant result. The live
capture controller was briefly restarted to add that redaction and exchange
support. Raw seed/key bytes were not written by the new exchange path.

No disable, reset, EEPROM write, calibration or programming request was sent.
The passive ADB observer remained disconnected, with no subsequent transport
state event through completion. No positive ADB-enable routine response was
observed. NRC `31` does not distinguish an unsupported routine from an invalid
domain/parameter or another unmet prerequisite. This rejects the reported layout
in the tested default, extended and level-1-granted extended contexts; other
security levels, payloads or OEM ADB-control mechanisms remain untested on CAN5.
See [SecurityAccess validation](../../diagnostics/diagnosticsd_security_access.md#live-direct-can5-securityaccess-validation-2026-11-15)
for the separately scoped transport grant.
See [the owning diagnostic guide](../../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md)
for earlier candidate provenance and the separate T1 tests.

[A]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc
[A69]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L69
[A85]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L85
[A152]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L152
[A165]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L165
[A174]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L174
[A324]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/generator/gm/gm_global_a_powertrain.dbc#L324
[V]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/gm_global_a_high_voltage_management.dbc#L90
[O]: https://github.com/commaai/opendbc/blob/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2/opendbc/dbc/gm_global_a_object.dbc
[G]: https://github.com/Automotive-9/GMLanDebug/blob/5f82c3ec445c20829862eb15edaf564e53b54d95/util/translation/HsLan.cs#L27
[L]: https://github.com/l77rodeo/gmlan/blob/b24a9b4a7a0365fa54eecf55e0c58e72c5bf12d9/README.md#L83
[F1]: https://pcmhacking.net/forums/viewtopic.php?t=8534
[F2]: https://pcmhacking.net/forums/viewtopic.php?p=136055
[S1]: https://surrealdev.com/rooting-the-cadillac-part-1-lay-of-the-land/
[S2]: https://surrealdev.com/rooting-the-cadillac-part-2-secoc/
[S3]: https://surrealdev.com/the-abcs-of-global-b/
[E]: https://github.com/torvalds/linux/blob/master/include/uapi/linux/can/error.h
[N]: https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANNetworkManagement.pdf
[C]: https://github.com/candle-usb/candleLight_fw/blob/51637c9bf6b6317bdaf40fca80bbda150dc179b6/src/main.c#L112
[I08]: https://github.com/dwilson2547/robo-services/blob/5a9f6351fb2e0bd6e9ba976aefa7dbc3e87ff5eb/can_data/analysis/gm/chevy_impala_2008.md
[I08DBC]: https://github.com/dwilson2547/robo-services/blob/5a9f6351fb2e0bd6e9ba976aefa7dbc3e87ff5eb/can_data/dbc/custom/chevy_impala_2008_hscan.dbc
