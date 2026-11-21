# DPS Type4 custom calibration workflow and current acceptance limits

**Scope:** the live CAN-bench record of what actually happens when a hand-edited Type4/
calibration payload is sent to the gminfo37 A11 CSM radio (`0x80`, Silverado gminfo37 /
Y17x / Y181/B) — the Type4-vs-calibration-value distinction, the chronological trial/
supersession log (2026-11-07 → 2026-11-17), and the one documented successful custom-write
path (a scoped temporary VIP-RAM write over CAN613/614). This is the workflow/evidence
record, not the crypto or protocol reference.

**Does NOT live here:** seed/key exchange, CMAC, the signed-container RSA/SHA verification
trace (Ghidra function/address level) and the SBA-ticket NVM-storage trace — all owned by
[`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
("GSK" below), pointer only. CAN bus-level session/profile mechanics and the stock-rewrite/
VIN-learning campaign are owned by `../platform/can_network.md`. The byte-level checksum/
hash/container-format mechanics for specific calibration edits (GMBrand, screen resolution,
the standalone XML loader) are owned by
[`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md)
("CHS" below), pointer only — this doc keeps just the write-sequence/outcome summary. The
full 404-entry A11 LTZ slot04 calibration-key glossary has moved out in full to
[`calibration_glossary.md`](calibration_glossary.md) — see the one-line pointer at the end
of this doc; nothing from it is restated here.

**Related:** GSK (central reference for signature/seed/key/certificate evidence), CHS
(checksum/container-edit mechanics), `calibration_glossary.md` (the 404-key catalog),
`../platform/can_network.md` (CAN campaign/bus mechanics), `../mdi2_client/README.md`
(MDI2 client evidence).

## Current state and correction history

**Current installed custom slot (2026-11-17):** SXM disabled plus Apple CarPlay/Android
Auto feature-enable overrides disabled; the owner independently confirmed both projection
entries disappeared from the UI. The SXM-only predecessor survived a cold power cycle;
projection persistence under a cold cycle has not yet been tested.

**History:**
- **2026-11-10:** stock LTZ write succeeded under the SBI-dependent all-FF seed; same-day
  modified-package attempts were rejected (`7F 36 72`). The rejection mechanism was not
  isolated at the time.
- **2026-11-11 (correction):** the earlier checksum-only deployment recipe was withdrawn as
  unsupported. All 14 stock CSM containers have independently verified RSA-2048 signatures
  and production-CA signer-record signatures. The prior claims that no RSA exists, that `$27`
  is the only gate, and that `Sign Type=NONE` or a catalog override permits unsigned custom
  calibrations are withdrawn, as is the claim that a malformed edit leaves the prior
  calibration untouched.
- **2026-11-16:** VIP signed-header verification failure confirmed as the live rejection
  path on the tested CAN5 route (signature-only control, immediate PEC `0015` readback,
  matching firmware-branch analysis — trace detail at GSK). A scoped temporary VIP-RAM write
  over CAN613/614 (not a provisioned ticket) then bypassed that path and produced the first
  accepted custom write, with an owner-confirmed runtime effect (see "Successful custom SXM
  calibration" below).
- **2026-11-16/17:** the bypass was reused for CarPlay/Android Auto disable, a GMBrand
  change, a full stock LTZ restoration, and several further calibration trials (screen
  resolution, Google-app visibility, recorder, porch-view) — see the chronological log below
  for the full supersession chain.

This page keeps the Type4/calibration-value distinction and the CAN-bench trial record; GSK
owns the seed/key/signature/certificate evidence.

## 1. Type4 workflow files and calibration data are different artifacts

A Type4 application is a PE32 diagnostic-driving DLL plus a `.cfx` XML workflow. The `.cfx`
contains action IDs and UI text, not the `SCREEN_RESOLUTION` value. Sending an arbitrary UDS
request through a DLL or raw MDI2 transport does not establish that the ECU will accept the
payload. Tool-catalog selection, diagnostic SecurityAccess, signed-container authenticity,
inner integrity, and application of the calibration are distinct checks.

The existing archive-format references describe different DPS/Type4 packaging workflows;
this document does not establish that a hand-written archive will load in DPS. See
[`DPS_ARCHIVE_CREATOR_ANALYSIS.md`](/Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/DPS_ARCHIVE_CREATOR_ANALYSIS.md),
[`SPS_TO_DPS_TYPE4_CONVERSION.md`](/Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/SPS_TO_DPS_TYPE4_CONVERSION.md),
and the worked [reset application](canbus_reset/CANBUS_RESET_ANALYSIS.txt) (links kept as-is;
the first two are absolute paths outside this repo and the third is in an excluded research/
subdirectory — not resolved here). A successful archive import would still not bypass
radio-side verification.

## 2. The actual calibration value

`SCREEN_RESOLUTION` is an enum in SoC-side `CalSets.db`, not a VIP EEPROM byte or Type4 action:

| Field | Recorded value |
|---|---|
| CalID | `__-Jk4IQIEeWHkIX-EVZFdA` |
| CalDef | `GIS738_RVCVIDEOROBUSTNESSREQUIREMENT`, version 7 |
| CalType | 4, enumeration |
| Recorded CalValue | 2 |
| EnumID | `_PWvKYIQHEeWHkIX-EVZFdA` |

Enum members are `0=800x480`, `1=1280x720`, `2=1280x768`, `3=1920x1080`, `4=2400x960`. The
existence of these enum members does not prove that selecting one changes the physical panel
timing or produces the desired UI. The calibration store is
`/mnt/vendor/calibration/database/CalSets.db`; override application and direct database
access require the appropriate filesystem and SELinux access.

## 3. Signed-container facts (pointer)

The stock container is protected by a payload digest plus a two-tier RSA-2048/SHA-256
signature and a production-CA signer record, each over defined byte ranges of the container.
All 14 stock containers pass these checks offline. **The full offset map, verifier
implementation, and Python re-implementation live in GSK** — not restated here to avoid
duplicating the charter owner.

The one fact load-bearing for this doc's trial log: recomputing the transport checksum/digest
after editing a payload does not, by itself, produce an accepted custom package, because
editing the payload invalidates the signature computed over the edited header bytes. This is
the operative constraint behind every custom-write attempt logged below. The old claims that
no RSA exists, that `$27` is the only gate, and that an unsigned or catalog-overridden
calibration would be accepted are withdrawn (2026-11-11 correction, above).

## 4. Chronological trial log

### 2026-11-10: stock write succeeds, modified package rejected

The documented 2026-11-10 stock LTZ write used the SBI-dependent all-FF seed and a 12-byte
zero response, transferred all 14 containers, finalized, reset, and passed metadata readback.
That demonstrates the stock programming sequence under that security state, not arbitrary
payload acceptance or a real-seed CMAC implementation. See the
[client's current evidence](../mdi2_client/README.md).

The same day's modified-package attempts were rejected with `7F 36 72` after the payload
digest was recomputed; an earlier stale-digest edit failed at transfer exit. NRC `0x72` is not
signature-specific on its own. Failed modified writes removed slots and required recovery
with stock LTZ.

### 2026-11-16: direct CAN5 repeat and header-signature rejection confirmed

After successful genuine LTZ and HC writes without MDI2, the earlier slot0C/part 85102312
experiment was reconstructed in memory: only `SXM_Enabled` (`_ysOddU1AEeO3UM5MzM17kw`) changed
true→false in the inner XML. Stock header RSA verified; the edited payload digest and
production-CA signer record verified, while edited-header RSA did not. The 1455-byte candidate
SHA-256 was `58ea702ae33c99543e75f1395da224c068bea9fb8d196746871aea48e7cf0e83`. No candidate
file or altered stock folder was created.

Only slot0C was attempted, because its genuine container is identical in LTZ and HC. With
known-good CAN5 preparation, `34` returned `74 20 0F FF`, but the first `36 01` carrying 1022
container bytes returned **`7F 36 72`**. No custom transfer exit was sent. In the same
programming session, the genuine 1457-byte slot0C container negotiated successfully, both
data blocks returned `76`, and exit returned `77`. Immediate readback matched all fourteen HC
identities, all module statuses 00, and F0F1/F0F2 = `0000`. The
[CAN campaign](../platform/can_bench_experiments.md#full-genuine-ltzhc-rewrite-through-canable--2026-11-16)
owns the stock-write, VIN-learning, and recovery setup. This reproduced the earlier failure
independently of the MDI2 tool; the old repacking script's claim that RSA is "UDS-inert" is
contradicted on this tested path and must not be used as a programming assumption.

A set of controls then confirmed the rejection is signature-driven rather than a generic
transport-checksum fault: a stock 1457-byte slot0C container with only one signature bit
flipped reproduced the same `7F 36 72` rejection and PEC `0015` (signature-only candidate
SHA-256 `e822a9f83d93d44b8e4939018be7696d12ebb6a91ae09fdb022c25c7a467479c`), while
genuine-container restoration in the same session passed both blocks and exit cleanly. (An
earlier control attempt stopped at `10 02 -> NRC22` before any download and is excluded from
these results; after a mute restart, preparation with approximately 700ms settling between
requests reached programming normally.) **Full Ghidra function/address trace for this
verification path** (kept here rather than GSK, which does not carry this level of detail):
wrapper file/runtime address `564D0`/`7DF4A`, parser runtime address `7E7CA`, PEC `0015`
setter address `86302` writing RAM address `FEBF0002`, boot crypto API pointer `0x844` (a
truncated Ghidra function body initially rendered it as an empty function; assembly confirms
it is not a no-op or a proven bypass). The operative conclusion for this doc: the original
edited package's failure is confirmed as **signed-header verification failure** on the tested
level-01 CAN5 path, not merely inferred from a generic NRC72. F0F1 is a programming-error
**code (PEC)**; older "error count" wording and the legacy client field name do not describe
this live value.

**Separate prerequisite/exception (bridges to the CAN613/614 result below):** the verifier
can accept a failed header-signature check if VIP RAM `FEBF0BF8`/`FEBF0BFC` already holds the
complementary validated SBA-ticket marker pair `A5163829`/`5AE9C7D6`. A dedicated ticket
validator sets that pair only after its own ticket/signature checks succeed — this is distinct
from a UDS `27` grant and is not established by the all-FF seed exchange. No valid SBA ticket
has ever been supplied here, and no CAN/T1 activation procedure for one has been demonstrated.
The signer-record check (§3) occurs before this exception is even reachable. Full NVM/RAM-flag
storage/revalidation trace for this ticket path (kept here, not GSK, which does not carry this
level of detail): NVM-block-86 reader offset `61AD2`, error string `DIDF0F4`; handler `61B72`
(descriptor size `0x336` bytes); flag-setter `56C8C` (sets RAM `FEBF0C00`); consumer `56C48`
(selects init state 7, reads block 86 into `FEBF0050`); validator `5667A` on `FEBF0052`;
success value `80` stored at `FEBF0C01`; logging routine `56B76` ("SbaTicketValidation
validation passed" for status 80); helper `563DA` (raw validation byte) and helper `56C98`
(bit7 boolean). The operative point carried forward here is that **an NVM write acknowledgment
is not proof of ticket acceptance**, and no valid ticket was available or loaded at any point
in this bench work. The CAN613/614 result below used only a temporary RAM overwrite of these two
words, not ticket issuance.)

The pinned Y175 VIP_APP 85759599 reference has SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`. Live CAN F181 identifies
module 01 as 85759599/DLS CJ; F180 identifies VIP_BOOT 85056831/AA. This matches module
identity, not a full live flash-byte readback.

### 2026-11-16: additional CAN security-profile trials

A fresh in-memory candidate changing only `SXM_Enabled` (`_ysOddU1AEeO3UM5MzM17kw`) true→false
was tried against three CAN security profiles before the scoped bypass was attempted:

| CAN security profile | Preparation and custom outcome | Recovery |
|---|---|---|
| 03 | Grant, `FF01`, `021E`, and programming session accepted; `34 → 74 20 0F FF`; first `36 01 → 7F 36 72`; immediate F0F1 = `0015`. | Pinned genuine slot0C: `76 01`, `76 02`, `77`; full F182 response unchanged. |
| 05 | Same preparation, negotiation, and first-block rejection; immediate F0F1 = `0015`. | Pinned genuine slot0C: `76 01`, `76 02`, `77`; full F182 response unchanged. |
| 09 (Engineering enum) | SecurityAccess granted; `FF01` positive; `31 01 02 1E → 7F 31 33`. | No download or custom block sent; F182 unchanged. Not a signature-acceptance test. |

The candidate is 1448 bytes, SHA-256
`4653a2e36754f0d1d6e2ef8f13a75d5d9d2688aaa0f285006c09537199c8fa84` (differs from the earlier
1455-byte repack; the requested XML edit is the same). Subsequent readback listed all 14
calibration slots 02–0F with status 00, F0F1 = `0000`, F0F2 = `0000`. Immediate cleanup was
not uniformly accepted: communication re-enable returned `7F 28 22`, and a delayed sequence
also returned session-specific `7F 28 7F`/`7F 85 7F`. A fresh extended-session sequence
accepted DTC logging enable (`C5 01`) and default session, but communication enable still
returned NRC22 — do not report communication cleanup as positively confirmed. The CAN adapter
was accessed directly after the old local control endpoint returned
`ConnectionRefusedError: [Errno 61] Connection refused`. No ticket, calibration-clear routine,
or alternate CAN development-enable bit was written. These three trials establish rejection
without the temporary RAM intervention; profiles 01/03/05 alone still do not establish a
signature exemption.

### 2026-11-16: successful custom SXM calibration through CAN613/614

**Result:** the 1448-byte candidate above was accepted, and the owner observed that SXM
disappeared from AAOS Radio. Candidate SHA-256:
`4653a2e36754f0d1d6e2ef8f13a75d5d9d2688aaa0f285006c09537199c8fa84`. Stock recovery source
remains the pinned 1457-byte slot0C container, SHA-256
`c8c36547fa2292b5aed6bb58b063e34da8b4490c60747dee5c40e50f6edf532e`. This candidate was
retained at that checkpoint; the later full stock LTZ restoration (below) superseded it. **This
is the only documented successful custom-calibration write path in this corpus.**

**Development-interface memory route:** receive ID 613 (standard 11-bit CAN, DLC 8) uses
callback slot 4; its compiled callback at `10DA5A` maps to file offset `E5FE0` in the pinned
VIP_APP 85759599. Replies use standard ID 614. Live connect `FF 00` returned
`FF 0C 00 08 08 00 01 01`; status `FD` returned `FF 20 00 08 00 00 01 01`. These exchanges
worked without a new Engineering-09 grant — do not attribute this route to `27 09`, or infer
every advertised capability from resource bits alone.

Static command dispatch at file offset `E5348` indexes the compiled table at `73524`. `F6`
selects a memory transfer address; `F5` reads bytes; `F0` writes bytes. Address-translation
helper `E4A76` returns its address argument; read helper `E4970` and write helper `E49F6`
directly copy memory with alignment-sensitive access — no SecurityAccess check was identified
in this traced command path. Live reads of the two verifier words and the validation-status
byte returned zero. This demonstrates reads at the tested addresses, not a complete VIP RAM
dump; the full valid RAM map and a coherent whole-memory snapshot were not verified. VIP memory
access does not expose AAOS/SoC RAM automatically.

**Scoped intervention:** after ordinary profile-01 programming preparation, the experiment
saved the two zero words at VIP RAM `FEBF0BF8`/`FEBF0BFC`, wrote `A5163829`/`5AE9C7D6` through
the development-memory route, and verified both by readback — these are the complementary
words consulted by the header-signature verifier on failure (§4, 2026-11-16 above). This was a
temporary RAM condition, **not a provisioned or cryptographically validated SBA ticket**. No
ticket NVM write, EEPROM edit, flash patch, or calibration-clear routine was used.

| Step | Observed result |
|---|---|
| Profile-01 grant; `FF01`; `021E`; DTC/communication preparation; programming session | All accepted. |
| Temporary verifier words | Both written and read back as expected. |
| Custom RequestDownload | `74 20 0F FF`. |
| Custom TransferData blocks 01 and 02 | `76 01`, `76 02`. |
| Custom RequestTransferExit | `77`. |
| Restore original verifier words | Both restored to zero and verified by readback; development connection disconnected. |
| Immediate programming error | `62 F0 F1 00 00`. |
| F182 | Full response unchanged from the pre-write baseline — expected, since part identity was retained. |
| Runtime application | Owner confirmed AAOS Radio no longer offers SXM. |

**Initial verification limits:** at the first-transfer checkpoint, no post-write reboot or
post-reboot calibration-value readback had been performed (the cold-cycle result below
supersedes the restart-pending portion). F182 alone does not establish the modified value; the
owner-observed application change is separate evidence. Immediate extended-session cleanup
returned `7F 10 22`; communication/DTC cleanup then returned `7F 28 7F`/`7F 85 7F`.
Default-session requests were accepted; a subsequent status request timed out. Do not infer
complete communication cleanup, restart persistence, or absence of pending state work from the
successful transfer — these limits do not retract the positive block/exit acknowledgments and
the observed SXM removal.

### 2026-11-17: development-interface (XCP-style) command inventory

Pinned VIP_APP 85759599 dispatch at file offset `E5348` indexes the 64-entry function table at
runtime `73524` by `(~command)&0xff` for commands `C0`–`FF`. The following 24 entries have
non-default targets. Addresses are signed-container file offsets; names follow
[Vector XCP protocol definitions](https://raw.githubusercontent.com/vectorgrp/XCPlite/master/src/xcp.h),
not a claim that every feature of the external implementation exists here.

| Command | Function | File offset | Evidence/limit |
|---|---|---|---|
| FF | CONNECT | E4B3C | Live verified |
| FE | DISCONNECT | E4BC0 | Live verified |
| FD | GET_STATUS | E4BC6 | Live verified |
| FC | SYNCH | E4BE4 | Mapped; not live tested |
| FB | GET_COMM_MODE_INFO | E4BEC | Mapped; not live tested |
| FA | GET_ID | E4C34 | Static response has zero identifier length |
| F6 | SET_MTA | E4C06 | Live address-selection verified |
| F5 | UPLOAD | E4C44 | Live reads at selected RAM addresses verified |
| F4 | SHORT_UPLOAD | E4C9C | Mapped; not live tested |
| F2 | TRANSPORT_LAYER_CMD | E4D10 | Empty return/no-op handler, not an IPC bridge |
| F0 | DOWNLOAD | E4D42 | Scoped live RAM writes/readback verified |
| EE | DOWNLOAD_MAX | E4D92 | Static memory-write path; not live tested |
| E2 | SET_DAQ_PTR | E4DD6 | Mapped; not live tested |
| E1 | WRITE_DAQ | E4E1E | Mapped; not live tested |
| E0 | SET_DAQ_LIST_MODE | E4EAA | Mapped; not live tested |
| DF | GET_DAQ_LIST_MODE | E4F08 | Mapped; not live tested |
| DE | START_STOP_DAQ_LIST | E4F4E | Mapped; not live tested |
| DD | START_STOP_SYNCH | E4FE0 | Mapped; not live tested |
| DA | GET_DAQ_PROCESSOR_INFO | E50C0 | Static info response; not live tested |
| D9 | GET_DAQ_RESOLUTION_INFO | E50E0 | Static info response; not live tested |
| D6 | FREE_DAQ | E5102 | Static state reset; not live tested |
| D5 | ALLOC_DAQ | E5118 | Mapped; not live tested |
| D4 | ALLOC_ODT | E514E | Static bounded allocation bookkeeping; not live tested |
| D3 | ALLOC_ODT_ENTRY | E51C0 | Static bounded allocation bookkeeping; not live tested |

All remaining 40 command entries map to `E4B32`, which generates error 20 (command unknown):
`F9`/`F8`/`F7`/`F3`/`F1`/`EF`/`ED`/`EC`/`EB`/`EA`/`E9`/`E8`/`E7`/`E6`/`E5`/`E4`/`E3`,
`DC`/`DB`/`D8`/`D7`, and `D2` through `C0` inclusive. **`GET_SEED`/`UNLOCK`, `USER_CMD`,
`BUILD_CHECKSUM`, calibration-page controls, and all listed flash-programming commands are not
implemented through these entries.** No execute-function or boot-ELK command was identified.
The supported RAM `DOWNLOAD` is not proof of a working flash-programming facility.

Bytes below `C0` enter a distinct configured data-buffer path after connection, not this
command table; DAQ/STIM operation was not live-tested. Advertised resource bits and mapped
handlers alone do not prove a complete acquisition or stimulation workflow. This interface
worked without a `27 09` grant and must not be counted as Engineering-profile permission.

### 2026-11-16: SXM cold-power persistence verified

The bench supply output was physically toggled off, application CAN TX was stopped, and 10.505
seconds elapsed after the completed off command before power-on; no radio CAN frames arrived
during that off interval, and ADB was absent. After power-on, with the captured full harness
schedule and existing VIN inputs supplied, at approximately 30 seconds F182 matched the
pre-cycle baseline, all 14 F0F0 calibration statuses were 00, and F0F1/F0F2 were `0000`. **The
owner confirmed SXM was still disabled after this cold power cycle.** No custom container was
retransferred and no verifier markers were re-applied for the restart. ADB had not yet
returned at the 30-second check, so Android boot-ID comparison and direct database readback
were unavailable. This verifies one cold-cycle retention of the observed feature change, not
repeated-cycle reliability.

### 2026-11-16: CarPlay and Android Auto custom calibration accepted

Following the owner-confirmed SXM cold-cycle result, slot0C was rebuilt again. The SXM-false
override was retained and two previously absent feature-enable Boolean overrides were added,
each at version 3:

| Feature | Calibration name / ID | Requested value |
|---|---|---|
| Apple CarPlay | `Enable_Application_Apple_Carplay` / `_vZTHQMZZEeOEzdA9o_rOxw` | false |
| Android Auto | `Enable_application_google_Automotive_link` / `_1pZzYMZZEeOEzdA9o_rOxw` | false |

The checked-in GIS513_DeviceProjection.caldef identifies these as **feature** enables,
explicitly distinct from GIS501 home-screen visibility calibrations (the reference
`LauncherIconCalibrationHelper` requires both the relevant home-screen flag and the
feature-enable flag; no home-screen visibility override was changed here). Only the existing
SXM value changed relative to stock, and only these two new version-3 overrides were added;
the earlier SXM-only candidate was retained in memory as the recovery payload.

The new container is 1478 bytes, SHA-256
`d58d353bbd11f945fe839be204dc2acadf23c2b67a796b50473f064bfe5c403f`. With profile-01
programming and the same temporary CAN613/614 verifier-word intervention, RequestDownload
returned `74 20 0F FF`; blocks 01/02 returned `76 01`/`76 02`; exit returned `77`; immediate
PEC was `0000`. Both verifier words were restored to zero and read back; F182 remained
unchanged. The custom projection/SXM container was retained at that checkpoint; the recovery
payload was not written — the later full stock LTZ restoration (below) superseded this
candidate.

**The owner confirmed that both CarPlay and Android Auto disappeared from the radio UI.** This
establishes accepted transfer plus the observed UI effect of the feature-enable overrides; an
attached-phone projection-session rejection has not been separately tested, and this candidate
has not had its own cold-power-cycle test (the earlier cold-cycle result applies only to the
SXM-only candidate). Immediate cleanup again returned `7F 10 22` for extended-session entry and
`7F 28 7F`/`7F 85 7F` for communication/DTC control; default-session requests were accepted. A
later settled check accepted extended session and DTC logging enable (`C5 01`) and default
session; communication enable still returned `7F 28 22`. All 14 slot statuses were 00 and
F0F1/F0F2 were `0000` — the transient status timeout did not persist into this later readback,
but communication re-enable itself still lacks a positive reply.

### 2026-11-16: process-state verification — UI disappearance is not process shutdown

Read-only ADB checks after the projection write found Android user 10 active.
`com.gm.hmi.sxm` and `com.gm.domain.server.delayed:CarplayService` were still running.
ActivityManager listed SxmMediaBrowserService, SXMService, CarPlayService,
CarPlayConnectionService, and RemoteDeviceService. PackageManager showed the SXM, CarPlay, and
Android Auto packages still installed with default enabled state (`enabled=0`, not a
disabled-user state). No separately named Android Auto process appeared in that snapshot;
shared projection services remained present, so this is not proof that Android Auto execution
was disabled.

**Correction of interpretation:** the custom writes and UI disappearance are confirmed, but
package/process shutdown and CPU/RAM savings are not. SXM's running process was observed after
its confirmed cold-cycle test; the projection candidate had not yet had its own cold-cycle
check. Feature-level connection blocking must be distinguished from package state and
background-service life.

For the related Google follow-up question: GIS501 defines version-1 home-screen/app-tray
visibility flags for Assistant (`_vzMekQTMEeuhM_xpS7qcsA`), Maps
(`_7p18cQTMEeuhM_xpS7qcsA`), and Play Store (`__jFe4QTMEeuhM_xpS7qcsA`). Reference
`LauncherIconCalibrationHelper` consumes these as visibility gates; Maps additionally checks
`ENABLE_APPLICATION_NAVIGATION`. No Google-Play-Services process-disable calibration was
identified in that search. Short live `top` samples showed Assistant and Maps CPU activity
alongside substantial audio/native-service activity; these samples do not establish a
before/after resource reduction or the cause of sustained load.

### 2026-11-16: GMBrand zero follow-up

The same scoped CAN613/614 method accepted a custom slot04/part 85045386 with only
GMBrand 3→0. All 13 data blocks and exit were accepted, PEC `0000`, verifier words
restored/read back, and F182 unchanged; the slot0C feature-disable module was untouched. On
2026-11-17, live property readback was `GM_Brand_None` with model still Silverado; all slot
statuses and F0F1/F0F2 were clean, and the owner confirmed a theme change. Brand-0 physical
cold-cycle retention remains untested. The
[owning theme trial](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3e-standalone-xml-loader-themeui-inventory-and-gmbrandscreen_resolution-live-trials)
records the candidate hash, baseline property, exact scope, and cleanup limits.

### 2026-11-17: full stock LTZ restoration after feature trials

Replaced the custom HC-based calibration set with all 14 stock LTZ containers, slots 02–0F,
validated against LTZ_REFERENCE before programming: 46162 bytes. All downloads, data blocks,
and 14 transfer exits were accepted. F182 matched all 14 pinned LTZ identities; all 14 F0F0
module statuses were 00 and F0F1/F0F2 were `0000`. The temporary verifier words were checked
zero before programming and were not modified; no calibration-clear or identity-write routine
was used. **This stock rewrite supersedes the custom SXM/projection, Brand-0, Google
visibility/navigation, recorder, and porch-view candidates below it in this log.** Immediate
cleanup returned `7F 10 22` for `1003`, `7F 28 7F` for `28 00 01`, and `7F 85 7F` for `85 01`.
Settled readback again showed the LTZ identities, all 14 module statuses 00, and F0F1/F0F2 =
`0000`; session `1003` and DTC-enable `85 01` succeeded, while communication-enable `28 00 01`
still returned `7F 28 22`. ADB was unavailable after restart, so Android property/UI
verification and a separate physical cold-cycle test remain pending.

### 2026-11-17: subsequent screen-resolution trial

After the stock LTZ restoration and owner-observed CAN factory reset, slot08 was changed only
from `SCREEN_RESOLUTION` 4 (2400×960) to 2 (1280×768). Both blocks and exit were accepted, PEC
`0000`, F182 unchanged, temporary verifier words restored. The owner reported display tearing.
Original stock slot08 was subsequently restored with both blocks and exit accepted, PEC `0000`,
without verifier-RAM modification; all slots are again stock LTZ, and the owner confirmed
normal display output after the rollback. Transfer success is not display success. The
[owning display trial](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#screen_resolution-1280x768-can-trial--2026-11-17)
records hashes, exact scope, and verification limits.

### 2026-11-17: Google visibility and recorder follow-ups

**Google trial:** slot04/85045386 retained Brand-0 and changed the Assistant, Maps, and
Play Store visibility overrides to false; slot02/87846412 changed only
`ENABLE_APPLICATION_NAVIGATION` to false. Both transfers and exits were accepted, PEC `0000`,
temporary verifier words restored, and F182 unchanged. The icons nonetheless remained visible,
and Assistant, Maps, Play Store, and Play Services packages remained enabled with live
processes — effective calibration-provider readback is unresolved; transfer acceptance does
not establish consumer behavior or resource savings. `Navigation_Zone_Enabled` was not
changed (remains true in source slot02; it controls the porch-view navigation zone
separately). Google slot04 candidate: 13241 bytes, SHA-256
`c8c8e5889be80c1fcb27701552bbeada23aa87c9d259d11237cfd4f6906649aa`. Google slot02 candidate:
1421 bytes, SHA-256 `d32fa1982954de45e5e4a988dedd0bfb6a3d3fd04b8b49e64a975c656b236f4d`. Record
comparison verified exactly the intended existing-value changes with no additional IDs; no
Play Services or whole-GAS process-disable flag was found.

**Recorder trial:** added `APPLICATION_HOMESCREEN_VIDEORECORDERLVM_ENABLED=true`, CalID
`_Mes-0Dz6EeaGEeA8k3J6-w`, override version 3, to the previously accepted slot04. Exact XML
record comparison verified one added override with every existing record preserved, including
Brand-0 and the three Google-false values. Candidate length 13266, SHA-256
`d02a1188c5ec054d7a721ad3abd6834c8a1869b6e1e4bec8e318da8bf1f2db99`. All 13 blocks and transfer
exit were accepted; PEC `0000`, temporary verifier words restored with readback, and F182
unchanged. Settled verification found all 14 slot statuses 00 and F0F1/F0F2 = `0000`; the
owner observed no recorder entry. Recording capability and cold-cycle retention remain
unverified. `RVS_PRESENT_STATUS` (`_ysAbAE1AEeO3UM5MzM17kw`) already equals 2 in the pinned
stock slot08/87846432 override version 1 (slot08 was not rewritten in this trial — this is
source-container evidence, not live per-CalID readback). Framework
`LauncherIconCalibrationHelper` requires both recorder visibility=true and
`RVS_PRESENT_STATUS`=2; the latter selects VPM camera processing, not proof of installed
recorder hardware/software. `Porch_View_Enabled` was not changed in this trial.

### 2026-11-17: explicit porch-view enable trial

Added `Porch_View_Enabled=true` (`_sIt3cGkUEeSgh9VY6ZvAyA`, version 2) to the accepted
recorder-enabled slot04, preserving every existing override. The reference definition defaults
true, but no source HC override was found. Candidate length 13290, SHA-256
`3e471ee507d2055652a0fe5aa69fd074b14f885ad25c361eeed4a5193866d7af`. All 14 transfer blocks and
exit (`77`) were accepted; PEC `0000`, temporary verifier words restored/read back, F182
unchanged. Visual effect and cold-cycle retention have not been verified; false has not been
tested (its defined behavior is to disable access and the page indicator).

The inspected HomeScreen `PorchViewService` (`T/X.java:a`) requires both the Boolean and a
separate display-support check: `T/C0129w.java:a` allows only `SIZE_1920_BY_1080` or
`SIZE_1280_BY_768`, and `T/A.java:b` derives that enum from `SCREEN_RESOLUTION`. Source slot08
specifies 2400×960 — a concrete additional gate that can make a true override ineffective;
live provider readback remains necessary to confirm running values.

## 5. Other paths and unresolved questions

**Type4 custom DLL -> arbitrary UDS service ID.** A custom Type4 PE32 DLL (exporting
`Launch`/`GetResult`/`SetInternal`/`CMessage`, confirmed via the real `GbPowerModeList.dll`
example) imports `tisvcsv4.dll`'s `CBuildService::BuildRequestedService(eProtocol,
uint16_t serviceID, long*)`, which accepts an arbitrary 16-bit UDS service ID — meaning a
custom Type4 DLL could inject arbitrary diagnostic commands (including `$27 02` SendKey)
through DPS's own already-authenticated session and local `tisvcsv4.dll` builder. This
doesn't hand over a missing key, but is a real capability for future custom tooling,
distinct from the CAN613/614 scoped-VIP-RAM-write path (§4) and from `tisvcsv4.dll`'s
SecurityAccess-algorithm-dispatch role (see
[GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md §2.1](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md#21-tisvcsv4dll--multi-oem-securityaccess-dispatch-architecture)
for that unrelated dispatch finding in the same DLL).

**CAN bus data reset recovery (2026-01-01, Y175, tested).** EEPROM bypass state blocks the
SPS/DPS connection itself: with the EEPROM bypassed (SBI all-`0xFF`, §2.3 of
[EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)) the `$27` seed
comes back all-`0xFF` and SPS refuses the connection outright; with the EEPROM locked (seed =
ECUID+challenge) SPS connects normally. Recovery procedure for a UI bricked via
`wm density`/`wm size`: (1) restore the EEPROM SBI bytes (`0x0441`/`0x0A81`) to locked state;
(2) verify the seed via DPS now shows ECUID, not `0xFF`; (3) apply SPS Type4 PIC6630 / Cal
`10017909` ("Reset ECU"); (4) post-reset the unit re-enters OOBE with ADB locked — re-apply the
EEPROM bypass afterward if ADB access is still wanted. Files: `10017909.cfx` (Reset ECU XML
config), `10017908.dll` (Security DLL, AES-CMAC), session log
`module_dumps/10017909_canbus_reset/A11_sps_datareset_log.Txt`. **The catch-22:** ADB access
needs the EEPROM bypassed, but the SPS recovery path above needs it locked — so this recovery
procedure itself is unusable from a state where ADB-only access already has the owner stuck
with a bricked UI and no locked-EEPROM fallback already staged.

A local `calserviced` override/database write is a different access path from UDS. Strings
such as `OVERRIDE_BACKDOOR` do not prove it is usable on a production build. An SBI-enabled
ADB shell is uid 2000 and does not automatically acquire `vendor_cald` filesystem access. The
named Signature-Bypass Ticket is also not a demonstrated usable bypass; its wire mapping,
authorization, and active target-verifier effect require proof. See the
[central reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

**2026-11-15 follow-up:** a compiled Y175 standalone XML application branch has been traced
through `calserviced_main` and its per-row SQL parser — a different entry point to persistent
calibration, not a temporary runtime override or a verified UDS setter. File permissions,
rebuild paths, ownership, and rollback remain gates. See the
[consolidated loader analysis](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3e-standalone-xml-loader-themeui-inventory-and-gmbrandscreen_resolution-live-trials).

## 6. Trim comparison and prototype status

The cached LTZ/High Country payload comparison found slot04 `85045371`/`85045386` with
`GMTrim=16/1` (LTZ/HighCountry in the Y177 database) and `P_HUD_MENU_AVAILABLE=false/true`.
Slot02 differs in fuel-related values and GCWR; slot05 adds an Alexa setting. These are also
different model-year/vehicle configurations, so the changes cannot all be attributed to trim.
The existing `calibration_prototypes/a11_ltz_gmtrim_highcountry.calovride.xml` (excluded
research/ subdirectory, link kept as-is, not resolved here) is standalone editable override
XML, not a signed SPS/CSM container or proof of a successful custom write, and does not
establish an EEPROM SBI write.

**Correction reason/date (2026-11-11):** this doc replaced earlier guessed archive/flash
instructions and unsigned-calibration assertions with verified signed-format facts, reported
write outcomes, and explicit runtime-enforcement gaps.

## 7. Calibration-key glossary

The full 404-entry A11 LTZ slot04 `OverrideValue` calibration-key catalog (key/description/
type/value/CalID across 26 named groups, CalDef-cross-matched, with online-search provenance
notes) has moved out of this workflow doc in its entirety. See
[`calibration_glossary.md`](calibration_glossary.md) for the complete catalog — nothing from
it is restated here.

## Open conflicts

None of this corpus's corpus-wide open conflicts (seed length, MEC semantics, module-72
naming, VMM1 bitness, EEPROM byte identity, DoIP topology, downgrade rejection point — see
PLAN.md) name this doc as a routing target. No unresolved contradiction specific to this
doc's own source ranges (lines 1-546 of the original) was found beyond the corrections already
folded above.
