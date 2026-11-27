# CAN bench experiment log

Chronological lab-notebook record of CAN-bus bench experiments on the Y175
A11/OPU bench: calibration-write mechanism, factory-reset/ELK probing,
boot/animation/door/wake/shutdown CAN behaviour, and the adapter-status /
startup-reduction / ADB-enable / keep-alive validation campaign. Verified
signal mappings discovered here belong to the dictionary, not this log.

Evidence notation (`B:n`/`H:n`/`R`/`A`/`W`/conflict) is defined once in
[CAN network](can_network.md#evidence-and-capture-notation) — not repeated here.
[CAN network](can_network.md) owns the message dictionary and publishes every
verified signal surfaced by an experiment below. [Vehicle network](vehicle_network.md)
owns topology/diagnostic transport; [bench setup](../hardware/bench_setup.md)
owns wiring/adapter configuration/physical power control.

**Related:** [CAN network](can_network.md) (dictionary) ·
[DPS Type4 custom calibration workflow](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md)
(owns calibration-trial narrative) ·
[CalSetsDB hand-editing/checksum](../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) ·
[GHS boot/update/recovery analysis](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) ·
[MDI2 raw UDS bypass guide](../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md) ·
[diagnosticsd routines and recovery](../diagnostics/diagnosticsd_routines_and_recovery.md) ·
[diagnosticsd security access](../diagnostics/diagnosticsd_security_access.md) ·
[OTA update stack](ota_update_stack.md)

## Verified signals surfaced here (pointer)

The experiments below surfaced these signal mappings; they are owned and
published in [CAN network](can_network.md), not duplicated here:

- `529` b0 bits 5–7 — IPC animation-status field (0–7), decode `status = (data[0]>>5)&7`
- `529` b1 bit 7 (signal `828`) — direct power-mode selector (Off/On)
- `4DA` DLC 8 b7 bit 0 (signal index `660`, PDU `26`) — DriverDoorOpen/DriverDoorClosed
- `4DB`/`4D9`/`4D8` bit positions 56/59/6 — other door selectors, not individually assigned
- `20D` DLC 6, Motorola b5 bit 7 (VHAL signal D7 `BSPMP_RmtProgmActvAuth`) — remote-programming-active-authenticated gate
- `284` DLC 6 (VHAL signal 58A `SPMP_SysPwrModeAuth`), raw value 2 — authenticated system-power-mode Run, verified through the USB-update readback
- `560`/`45A`/`459` (signals 6B3/6B5/6B4) — VIN digit fields, see [Full genuine LTZ/HC rewrite](#full-genuine-ltzhc-rewrite-through-canable--2026-11-16) below

## Calibration-write mechanism (CAN613/614)

**Goal:** write a custom (non-stock) CSM calibration container through CAN
without MDI2, a calibration-clear, or an EEPROM/flash patch.

**Mechanism:** development-memory protocol on standard CAN613 (request)/614
(reply). Receive ID `613` (11-bit, DLC 8) uses VIP_APP callback slot 4
(compiled callback `10DA5A` → file `E5FE0`); replies use `614`. No
SecurityAccess gate was identified in this command path. After ordinary
profile01 UDS programming preparation (SecurityAccess, FF01, 021E,
DTC/communication prep, programming-session entry), the two VIP
header-verifier RAM words at `FEBF0BF8`/`FEBF0BFC` are temporarily written to
`A5163829`/`5AE9C7D6` — the complementary marker pair the signed-header
parser (`56D50`) consults on verification failure — then the modified
container is transferred (RequestDownload/TransferData/RequestTransferExit),
and the two RAM words are restored to zero and read back before session
cleanup. This is a temporary RAM condition, not a provisioned or
cryptographically validated SBA ticket; no ticket NVM write, EEPROM edit, or
flash patch is used. Full command-table inventory, address trace, and the
VIP signed-header-rejection root cause (PEC `0015`, NRC `72`) are owned by the
[custom calibration workflow doc](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#4-chronological-trial-log).

**Results (all through this CAN613/614 mechanism unless noted):**

| Date | Candidate | CAN5 transfer result | Owner-confirmed effect | Persistence tested | Record |
|---|---|---|---|---|---|
| 2026-11-16 | Slot0C, `SXM_Enabled` true→false | `76 01`/`76 02`/`77`, PEC `0000` | SXM option gone from AAOS Radio | One 10.505 s cold cycle: still disabled | [workflow §Successful custom SXM](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-successful-custom-sxm-calibration-through-can613614) |
| 2026-11-16 | Slot0C (1478 B), + CarPlay/Android Auto feature-enable false | `76 01`/`76 02`/`77`, PEC `0000` | Both projection entries gone from UI | Not cold-cycle tested | [workflow §CarPlay/AA](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-carplay-and-android-auto-custom-calibration-accepted) |
| 2026-11-16 | — (process-state check only) | n/a | SXM/CarPlay/AA packages and processes still present/running at default-enabled state — UI disappearance ≠ process shutdown | n/a | [workflow §process-state](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-process-state-verification--ui-disappearance-is-not-process-shutdown) |
| 2026-11-16 | Slot04/85045386, GMBrand3→0 | 13 positive transfer blocks, exit `77`, PEC `0000` | Theme changed; brand reads `GM_Brand_None` | Not cold-cycle tested | [theme trial](../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3e-standalone-xml-loader-themeui-inventory-and-gmbrandscreen_resolution-live-trials) |
| 2026-11-17 | Full stock LTZ (slots 02–0F, 46,162 B) | All 14 downloads/blocks/exits accepted | Supersedes the custom slots above | n/a (restoration) | [workflow §full stock LTZ restoration](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-full-stock-ltz-restoration-after-feature-trials) |
| 2026-11-17 | Slot08, `SCREEN_RESOLUTION` 4→2 (1280×768) | Both blocks + exit accepted, PEC `0000` | Display tearing observed; stock slot08 restored, tearing gone | n/a | [display trial](../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#screen_resolution-1280x768-can-trial--2026-11-17) |
| 2026-11-17 | Google (slot04)/Navigation (slot02)/Recorder (slot04) visibility=false/true | All transfers + exits accepted, PEC `0000` | No UI effect: icons/processes remained; recorder entry never appeared | n/a | [follow-ups](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-google-visibility-and-recorder-follow-ups) |
| 2026-11-17 | Porch_View_Enabled=true, slot04 | Transfer + exit accepted, PEC `0000` | UI effect unverified; display-size gate (`SCREEN_RESOLUTION`) can make it ineffective | n/a | [porch-view trial](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-explicit-porch-view-enable-trial) |
| 2026-11-16 | Slot0C SXM edit reconstructed (1448/1455 B variants), profiles 01/03/05/09, **no** CAN613/614 RAM intervention | `34 → 74 20 0F FF`; `36 01 → 7F 36 72`; immediate `F0F1=0015` | Rejected — signed-header verification failure, not a signature exemption | Genuine slot0C restored each time (`76 01`/`76 02`/`77`) | [header-signature rejection](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-direct-can5-repeat-and-header-signature-rejection-confirmed), [additional profiles](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-additional-can-security-profile-trials) |
| 2026-11-25 | Full 14-slot `LTZ_CustomCAL.zip`, **with** CAN613/614 RAM override (saved/overridden/verified once for the whole batch) | `34 → 74 20 0F FF` on all 14; `36 01 → 7F 36 72` on all 14; no exit sent on any slot | Rejected on every slot despite the override being applied and verified — first full-package custom test; all prior successful custom writes above were one slot with a small edit | Genuine stock LTZ confirmed unchanged on all 14 via post-attempt `F182` readback | [full-package custom rejection](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-full-14-slot-custom-package-rejected-first-full-package-custom-test) |
| 2026-11-25 | Slot0C, `SXM_Enabled` true→false (exact reproduction of the 2026-11-16 candidate), **with** the marker pair now packed little-endian on the wire + override written after `10 02` + 1022-byte `TransferData` chunks | `34 → 74 20 0F FF`; `36 01 → 76 01`; `36 02 → 76 02`; `37 → 77`; PEC `62 F0 F1 00 00` | Accepted — resolves the 2026-11-25 rejection above: the driver had been sending the override values byte-swapped (big-endian instead of RH850's native little-endian), a self-consistent-but-wrong write+verify bug, not a firmware/toolkit/scope issue | Not yet cold-cycle or AAOS-visually tested | [resolution](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-resolved--the-driver-was-sending-the-marker-pair-values-byte-swapped) |

All candidate/digest/hash values, the Type4/payload distinction, and the
exact signature-verification trace addresses are owned by the linked
workflow doc — not restated here.

### Not covered by the research doc — kept here

The following CAN-mechanism/security content from the same working-recipes
block (original L29–427) does **not** appear in
`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` (checked: no `NoVIN`, `VHAL`,
`20D`, `284`, `BSPMP`, `programming entry`, `F190`, `VehIdNmDig`, or
"security-profile matrix" hits in that file). It is kept in full below
rather than pointed.

### Verified procedure (2026-11-25) — how to actually do this

Both calibration-write paths below are implemented, fixed and live-verified in
[`tools/bench/bench_can/calibration_write_can5.py`](../tools/bench/bench_can/calibration_write_can5.py),
the source of truth for exact byte sequences. This is a HOWTO, not a trial log — for the
investigation history (bugs found, dead ends ruled out) see the dated 2026-11-25 entries
below in this file and in the
[custom calibration workflow doc](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md)
(search both for `2026-11-25`).

#### A. Genuine/stock full-package write

```
calibration_write_can5.py package --package-dir <dir> [--only <slots>]
```

Genuine is the default — no `--modified` flag. `--only 04,06,07` restricts to specific
hex slots.

What `write_package()` does, in order:

1. `enter_programming_session()` runs **once for the whole package**: `10 01` (pre-clear),
   `10 03`, SecurityAccess (`27 01` / `27 02` + 12 zero bytes), `31 01 FF01`, `31 01 021E`,
   `85 02`, `28 03 01`, `10 02`.
2. `transfer_one()` loops over every slot **inside that same open session**: `34`
   RequestDownload, `36 <ctr> <data>` TransferData in `0x0FFF - 2` = 4093-byte chunks,
   `37` TransferExit, `22 F0F1` PEC check.
3. `exit_programming_session()` runs **once**, after the last slot.

Two bugs this fixes and must never be reintroduced:

| Bug | Symptom | Rule |
|---|---|---|
| Re-running `enter_programming_session()` per slot | Alternating success/fail across slots — the VIP reads a mid-package `10 01` as "programming event ended" (`evRemoteReflashProgrammingEnd` → `Shutdown`) and races the next slot's re-entry; this is a driver bug, **not** a vehicle-side quirk | Open the session once for the whole package, never between slots |
| `TransferData` chunk = `0x0FFF` (4095) instead of `0x0FFF - 2` (4093) | Silent timeout (no NRC) on any slot whose container needs a full-size block (only slots 04/06/07 are large enough to hit it) | The ECU's advertised `maxNumberOfBlockLength` **includes** the `0x36` service byte and the block-counter byte; block size = `max_request_length - 2` |

Full root-cause writeup: [Full genuine LTZ rewrite — two driver-process bugs found and fixed, 14/14 verified — 2026-11-25](#full-genuine-ltz-rewrite--two-driver-process-bugs-found-and-fixed-1414-verified--2026-11-25).

**Verify:**

```
calibration_write_can5.py verify --package-dir <dir>
```

Reads live DID `F182` (`10 03` then `22 F1 82`, no SecurityAccess needed) and compares
every slot's identity record against its on-disk container, using mdi2's own validated
`parse_f182()`/`calibration_record()` parser (loaded directly by file, not through
`mdi2/__init__.py`, to avoid its unneeded `pycryptodome` import).

#### B. Custom/modified single-slot write via CAN613/614

Mechanism name to use: **the VIP development-memory diagnostic interface**. Never call
it a "bypass" — that phrasing is banned in this project.

```
calibration_write_can5.py package --package-dir <dir> --only <slot> --modified
```

What the driver does, in order, and why each exact detail matters:

1. `enter_programming_session(genuine=False)` runs the **same** session-open sequence as
   the genuine path (`10 01` / `10 03` / SecurityAccess / `31 01 FF01` / `31 01 021E` /
   `85 02` / `28 03 01` / `10 02`).
2. **Only after `10 02`** — not before the session-open sequence — it connects
   CAN613/614 (`FF 00`), saves the two VIP RAM words at `FEBF0BF8`/`FEBF0BFC`, and writes
   the override marker pair `0xA5163829`/`0x5AE9C7D6`.
3. `transfer_one()` runs with `block=1022` (**not** the genuine path's 4093).
4. `exit_programming_session()` restores both words to their saved values and
   disconnects CAN613/614 (`FE`).

**Byte order is load-bearing — this is the 2026-11-25 bug that must never come back.**
RH850 is a little-endian core and the firmware does a native 32-bit load of these words,
so the CAN613 `DOWNLOAD` (`F0`) command's 4 data bytes must go out **little-endian**:

```
FEBF0BF8  <-  F0 04 29 38 16 A5      (0xA5163829, little-endian)
FEBF0BFC  <-  F0 04 D6 C7 E9 5A      (0x5AE9C7D6, little-endian)
```

**Not** the naive big-endian encoding you'd get from `bytes.fromhex("A5163829")` directly
(`F0 04 A5 16 38 29`). A prior version of this driver sent the big-endian bytes, which put
the wrong 32-bit value in RAM (`0x29381 6A5`) — but because the write-then-read-back
verification check compared the readback against that same wrong big-endian constant, it
*always* printed "override+verify" success even though the real RAM value was never
correct. This made the bug invisible to live testing for most of a day; it was only found
by recovering the raw byte-level transcript of the one historically-successful write (see
[the 2026-11-25 resolution](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-resolved--the-driver-was-sending-the-marker-pair-values-byte-swapped)).
Current code (`MARKER_VALUES` in `calibration_write_can5.py`) packs both words with
`struct.pack('<I', ...)` — do not revert this to a direct hex-string decode.

**Chunk size:** the one proven-working recipe used a hardcoded 1022-byte `TransferData`
chunk, not the ECU's advertised `0x0FFF`. Whether 1022 is causally necessary (vs. the
byte-order fix alone being sufficient) was **not** independently isolated — until someone
proves otherwise, keep custom writes on `block=1022`.

**Verified live (2026-11-25):** reproducing the historical SXM_Enabled disable (CalID
`_ysOddU1AEeO3UM5MzM17kw`, slot `0C`/part `85102312`, `true`→`false`) through this exact
procedure was **accepted** — `34 → 74 20 0F FF`; `36 01 → 76 01`; `36 02 → 76 02`;
`37 → 77`; PEC `62 F0 F1 00 00` — and the owner visually confirmed SXM disappeared from
AAOS Radio.

**Known limit (open item, not evidence either way):** only this one custom edit has ever
been confirmed end-to-end. A full 14-slot custom *package* has never succeeded — the
[2026-11-25 full-package attempt](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-full-14-slot-custom-package-rejected-first-full-package-custom-test)
was rejected on every slot, and predates this byte-order fix; it has not been retried
since. Do not claim a full custom package would work now; there is no evidence either
way.

#### C. If you're debugging a rejection

- **`7F 36 72` on every slot, no exit sent** → check override byte order first. Confirm
  the on-wire `DOWNLOAD` bytes are little-endian (`29 38 16 A5` / `D6 C7 E9 5A`), not a
  direct hex-string decode of `A5163829`/`5AE9C7D6`. A write+verify that "always passes"
  is not proof the RAM value is correct if the verify compares against the same constant
  it wrote.
- **Timeout on one slot's first `36` block, no NRC** → check `TransferData` chunk size.
  Genuine path must use `0x0FFF - 2` (4093); custom path must use `1022`. Using the raw
  `0x0FFF` (4095) advertised by the ECU overflows its real limit by 2 bytes and is
  silently dropped.
- **Alternating success/fail/timeout across slots in the same package** → check that
  `enter_programming_session()` runs exactly once for the whole package, not once per
  slot. A mid-package `10 01` ends the VIP's programming event and races the next slot's
  re-entry.
- **Override applied before vs. after session-open** → the override must be written
  *after* `10 02`, not before the `10 03`/SecurityAccess/`FF01`/`021E`/`85 02`/`28 03 01`/
  `10 02` sequence.
- Still rejected after checking all of the above → you are likely hitting an
  unrecorded/unresolved precondition, not one of the four fixed bugs above; see the
  [root-cause isolation entries](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-25-root-cause-isolated--recompression-alone-triggers-rejection-not-the-edit)
  before re-deriving anything from scratch.

#### Expanded validation campaign — 2026-11-16

**Goal:** reach genuine programming-session entry over CAN5 and/or T1
without MDI2 and without the (at the time prohibited) calibration-wipe
routine `0249`.

**Method/result — Direct CAN5 probe sweep** (testers F1/F2, `14DA80Fx`/`14DAF80x`):

| Probe | Result |
|---|---|
| Default/extended session, TesterPresent | Accepted on both routes |
| `22 F181` | Positive, 18-byte response |
| `22 F182` | Positive, 200-byte response, 28 records |
| `22 F0F1`, `22 F0F2` | Positive, `0000` each |
| `22 F1A0` | Positive, read-only `FC` |
| `22 F085` | Positive, `00` from radio target — not a BCM read |
| `22 41E7`/`41DB`/`41DA`/`42AD` | Positive single-byte readbacks |
| `10 02` without grant | `7F 10 22` both routes |
| Level-1 grant + TesterPresent held | `85 02→C5 02`; `28 03 01→68 03`; `10 02` still `7F 10 22` |
| Cleanup | `85 01→C5 01`; `28 00 01→7F 28 22`; normal traffic resumed (38 IDs) |

An initial 5.2 s-unheld probe's `7F 85 7F`/`7F 28 7F` results are invalidated
by session-expiry (no TesterPresent); the table above is the
TesterPresent-held repeat. No `0249`, RequestDownload, or TransferData was
sent.

**Method/result — Same-operation transport comparison** (CAN5/tester F2 vs
direct T1/tester F4, over a separate VLAN-4 interface):

| Operation | CAN5 / F2 | Direct T1 / F4 |
|---|---|---|
| Read F182 | Positive, 28 records | Positive, 200-byte reply |
| Read radio-target F085 | `62 F0 85 00` | `7F 22 31` |
| `85 02`, `28 03 01` | `C5 02`, `68 03` | `C5 02`, `68 03` |
| `10 02` | `7F 10 22` (On and Off) | `7F 10 22` (On) |
| `28 00 01` | `7F 28 22` | `68 00` |
| SWC `2F 41DB 03 04`/`03 03` | Both `7F 2F 22`, volume unchanged | Both accepted, DID `41E7` 15→14→15 |
| SWC return-control | Accepted | Accepted, volume restored |

T1 positives cannot be copied into the CAN5 dictionary as working CAN5
controls.

**Method/result — T1/CAN5 seed-subfunction security-profile matrix**, all
nine previously confirmed T1 seed subfunctions, both transports, separate
default→extended exchanges, Run and Off:

| Seed subfunction | T1 Run | T1 Off | CAN5 F1 Run | CAN5 F1 Off |
|---|---|---|---|---|
| 01, 03, 05 | `7F 10 22` | `7F 10 22` | `7F 10 22` | `7F 10 22` |
| 09 | `7F 10 33` | `7F 10 33` | `7F 10 22` | `7F 10 22` |
| 0B | `7F 10 33` | `7F 10 33` | `7F 10 33` | `7F 10 22` |
| 0D, 11, 13 | `7F 10 33` | `7F 10 33` | `7F 10 22` | `7F 10 22` |
| 15 | `7F 10 33` | `7F 10 33` | `7F 10 33` | `7F 10 22` |

All 18 grants/replies independently recovered from capture; seeds/keys
redacted. Varying CAN NRC33 outcomes are observations, not proof that
security permission varies with power mode. No programming-session entry
succeeded in this matrix; it sent no RequestDownload/TransferData/clear.

**Finding — T1 programming-entry precondition:** `diagnosticsd`'s native
session-transition code queries internal index 5; Java
`SessionControlHandler` returns positive only when
`BackupSystemPowerModeProtectedRemoteProgrammingActiveAuthenticated`
(VHAL property `2120105C`) is true and available — distinct from the `529`
power-mode field. See [diagnosticsd routines and recovery](../diagnostics/diagnosticsd_routines_and_recovery.md).

**Result — programming entry resolved over T1:** Y175 VHAL ARXML maps
native signal D7 (`BSPMP_RmtProgmActvAuth`) to CAN `20D`, DLC 6, Motorola
start bit 47 width 1 (zero-based b5 bit 7); VIP Com signal FF maps the same
ID/DLC/bit independently. VHAL reference SHA-256
`3dcd9acccfa30aef7f5adfff0066dd69c71a163aa82b027b5e1359137fac7a88`; VHAL ELF
RVA `3BD86` sets FrameInfo ID `20D`/DLC 6, `3BDBC` adds signal D7 (Ghidra
base `100000` excluded from these RVAs).

In a granted T1 session, baseline `10 02 → 7F 10 22`. Preserving every
captured `20D` byte except setting b5 bit 7 (≈100 ms repeat), then
`85 02`/`28 03 01`/`10 02`, produced **`50 02`** (reproduced once). No
calibration clear sent; `20D` restored afterward. **Programming entry is
demonstrated with CAN input + T1 diagnostics, without MDI2** — an LTZ
transfer itself was not yet demonstrated at this point (see the full
rewrite below).

The equivalent F1/CAN5 attempt still returned `7F 10 22`; adding synthetic
`284`/DLC 6 authenticated-power-mode candidates (raw 0,1,2,4; b4 bits 3–5;
validity bit 2 clear) did not change that result. VHAL maps signal 58A
(`SPMP_SysPwrModeAuth`) to frame `284`; these tests do not establish VIP
acceptance of every authenticated-mode value.

**USB-update follow-up, 2026-11-17 (verified):** repeated `284`/DLC 6
`00 00 00 00 10 00` (raw candidate 2) changed AAOS `IGNITION_STATE` to
4/RUN, UpdateService `SystemPowerMode` OFF→RUN, and lifecycle
`STATE_PROPULSION`→`STATE_RUN` while `VehicleParked` stayed true, satisfying
the USB installer's vehicle-on prompt. See
[full USB observation](ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17).
This does not establish the other raw candidates.

The second T1 session's deliberately-invalid RequestDownload format probe
`34 00 00 02 00 00` returned `7F 34 22` (no module data sent); later tracing
identifies the TCP download interceptor/Java installer as the relevant T1
route, so this rejection doesn't validate native calibration-parser
reachability. The owner observed "Update unsuccessful / Vehicle Update
Failed" around these session tests. A later direct-T1 check found all 14
LTZ F182 identities still matching stock, all slot statuses `00`, F0F1/F0F2
`0000` — metadata/status verification only.

ADB enablement through CAN remains an open task; evidence clarification
2026-11-16: USB debugging had been manually enabled before this boot, so
continued ADB availability is not evidence of a CAN-triggered enable or
reboot persistence.

#### Full genuine LTZ/HC rewrite through CANable — 2026-11-16

**Goal:** demonstrate genuine LTZ (then HC) calibration transfer, VIN
learning, and post-restart recovery entirely over direct CAN5, without
MDI2, `0249`, `FF00`, or an override clear.

**Method/result:**

| Stage | Observed result |
|---|---|
| T1 F5 attempt (protected programming active, authenticated power mode Off, FF01/021E, SecurityAccess, DTC/comm prep) | `10 02 → 50 02`; first stock `34` still `7F 34 70`, zero bytes transferred (F4 attempt also NRC70) |
| CAN5 with minimal power traffic, same programming/power flags | FF01 `71 01 FF 01 00 86 04 07 00`; 021E `71 01 02 1E 00`; `10 02 → 7F 10 22` |
| CAN5 with captured harness companions present | `10 02 → 50 02`; first `34 → 74 20 0F FF` (which companion(s) resolved the gate not isolated) |
| Genuine LTZ transfer, slots 02–0F | 46,162 bytes; all 14 negotiations accepted, all blocks ack'd, all 14 exits `77` |
| Immediate readback | All 14 F182 match pinned LTZ; F0F0 all slots status `00`; F0F1/F0F2 `0000` |
| Finalization | F198/current-date F199 → `6E`; `31 01 03 9B → 71 01 03 9B`; `11 01 → 7F 11 22` |
| Identity restoration | F190 read 17 zero bytes post-finalization. T1 personalization → `6E F1 90` and matching readback, but next mute restart → NoVIN. CAN personalization also → `6E F1 90`; later post-mute T1 read had 17 printable bytes while VIP still entered NoVIN |
| Restart observations | Mute `526` b5-bit7 reset (~10 s); calibration state 2, HMI ready, then `SystemState=NoVIN (0xF)`. Full harness replay during another mute restart did not resolve NoVIN. Cold 12 V cycle (>10 s off) also reached NoVIN; F190 still 17 printable bytes |

Transfer environment: all captured profile IDs replayed except `20D`;
separate ~100 ms stream supplied original `20D` with b5-bit7 set plus `284`
candidate authenticated-Off field. Diagnostic sender stops application
repetition, so the captured-companion replay explicitly restarts at each
ISO-TP boundary — not proof of a required uninterrupted/minimum schedule.
`20D` restored afterward.

T1 public `34/36/37` uses the download interceptor/Java installer (F4=OTA,
F5=onboard, expects package manifest/signature) — distinct from the working
direct-CAN stock CSM transfer path. UpdateService at one point reported
installation with `mRunningInstaller=null`, empty installer list,
install-error status, `UpdateService-BackgroundInstaller invalid state 14`.

**NoVIN recovery analysis:** VIP getter at file offset `6EE76` calls
`6EE5A` on RAM `FEBD22C0`, testing eight bytes for all-FF; startup checks
this before logging NoVIN Active (`6F040–6F048`, log wrapper `50E6E`) — not
the same as testing the 17 F190 bytes directly. At `6EED6`, a separate
internal classification is 2 when the theft-locked flag at `FEBE092B` is
set, else 0 for all-FF / 1 for any non-FF byte in that eight-byte value —
internal classification values, not the SS `SystemState` enum (NoVIN=`0xF`).
No bench test established that writing a different VIN necessarily sets the
theft flag. Identification of the eight-byte value with a specific EEPROM
block is still open.

**VIN resolution — native VHAL ARXML signal/frame constructors:**

| CAN ID | DLC | Signal | Tested VIN input |
|---|---|---|---|
| `560` | 6 | Signal `6B3` `VehIdNmDig1` | First VIN character + five zero bytes; companion fields unresolved |
| `45A` | 8 | Signal `6B5` `VehIdNmDig2_9` | VIN characters 2–9, in order |
| `459` | 8 | Signal `6B4` `VehIdNmDig10_17` | VIN characters 10–17, in order |

All three IDs/DLCs also match the pinned VIP receive registry, callback 3,
and are absent from the 32-ID captured harness profile. A 10-second burst in
the already-NoVIN state produced no change. Repeating all three owner-VIN
inputs at ~320 ms across a mute restart, with full harness traffic,
reached calibration state 2 at 5.714 s VIP uptime, HMI ready/Propulsion at
21.938 s; owner confirmed homescreen. Individual necessity, minimum
duration, and learned-state persistence without continued VIN traffic are
not isolated — do not reduce this to an F190-write-alone claim or assume any
VIN mismatch sets the theft lock. Real VIN payloads were redacted from
capture and this document.

**HC package result:** HC (46,181 bytes) independently passed all
payload-digest/header-RSA/production-CA checks; all 14 downloads/exits
succeeded, F198/F199/039B/F190 finalized (one transient CAN ACK/queue
interruption recovered via silent loopback without repeating the transfer).
Owner observed the HC logo. Mute restart: calibration state 2, HMI
ready/Propulsion at 21.077 s VIP uptime; independent T1 readback matched all
14 HC identities + supplied VIN, all statuses `00`, F0F1/F0F2 `0000`.
Programming/finalization used CAN5/CANable; T1 stock-transfer attempts
failed pre-transfer, T1 used only for independent readback. Owner also
confirmed the HC moving welcome animation (see
[animation decode](#display-side-player-resolves-the-animation-command-numbers--2026-11-16)
below): an initial wake from incomplete shutdown produced request 1 (not
welcome request 2); after full shutdown, a fresh replay produced request 2
at 8.419 s, completion ~14.943 s later, then request 3 and Propulsion at
25.227 s. **Genuine LTZ/HC recovery is established on this bench** with
these inputs — not an exhaustive payload readback or a minimal recipe.

**Modified-module follow-up (header-signature rejection):** owned by
[workflow §header-signature rejection](../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-direct-can5-repeat-and-header-signature-rejection-confirmed)
— the direct CAN5-side observations here (`7F 36 72` on first data block,
genuine slot0C restored, PEC `0015`) match the research doc's trace and are
not repeated.

**Evidence:** B/H captures as above; VIN values never written to capture or
this document.

#### Full genuine LTZ rewrite — two driver-process bugs found and fixed, 14/14 verified — 2026-11-25

**Goal:** repeat the full genuine LTZ rewrite (all 14 slots) from the
[2026-11-16 campaign](#full-genuine-ltzhc-rewrite-through-canable--2026-11-16) over
CAN5/CANable, after the owner reported a repeating success/fail pattern across slots
on this bench that the prior campaign did not show, and asked whether the per-slot
process itself was correct.

**Driver:** [`tools/bench/bench_can/calibration_write_can5.py`](../tools/bench/bench_can/calibration_write_can5.py),
a mechanical adaptation of `boot_radio_elk.py`'s `CanDiagnostics`/keepalive-replay
architecture, chaining the already-validated UDS byte sequence from
`pi_dashboard/backend/app.py`'s `_uds_cal_transfer` and the CAN613/614
save/override/restore sequence from `can0_dev.py` — not new protocol logic.

**Issue 1 — per-slot session re-entry (the alternating success/fail cause).** The
driver re-ran the full `10 03`/SecurityAccess/`31 01 FF01`/`31 01 021E`/`85
02`/`28 03 01`/`10 02` session-open sequence for every slot, tearing down to the
default session (`10 01`) between each one.
[`tools/mdi2_client/mdi2/calibration_transaction.py`](../tools/mdi2_client/mdi2/calibration_transaction.py)'s
already-validated `program()` opens this sequence exactly once and loops all 14
transfers inside the same open session — the driver did not match that structure.
Live VIP console UART (115200 8N1, CP2102, DTR/RTS cleared) showed the real effect: a
`10 01` between slots is read by the module as "programming event ended"
(`evt=evRemoteReflashProgrammingEnd` → `st=Shutdown`), which raced the next slot's
session re-entry and once produced a real fault cascade (`evSuspendFault` →
`evUnmountTimeout` → `FAILURE DETECTED: Unmount Timeout` → `CSM_Sleep`) — not a
vehicle-side quirk. **Fix:** split `write_calibration()` into
`enter_programming_session()` (session-open, once), `transfer_one()` (`34`/`36`/`37`/
`22 F0F1` for one slot, touches no session state), and `exit_programming_session()`
(restore + close, once, at the end); `write_package()` now opens once, loops
`transfer_one()` over every slot, and closes once.

**Issue 2 — TransferData block-size off-by-two.** After fixing Issue 1, three slots
(04, 06, 07 — the only three of the fourteen whose decompressed container is
≥4095 bytes, needing at least one full-size block) still timed out, always on the
first `36` block, with no response at all — reproduced identically across two
separate retries (including one where only those three were attempted, ruling out a
bus-settle/ordering explanation). Root cause: the ECU's `74`
(RequestDownload-positive) response gave `maxNumberOfBlockLength=0x0FFF`, and per
ISO 14229-1 — confirmed byte-for-byte against
[`tools/mdi2_client/mdi2/calibration_payloads.py`](../tools/mdi2_client/mdi2/calibration_payloads.py)'s
own `transfer_requests()` ("max_request_length includes the service byte and
transfer block counter" / `block_size = max_request_length - 2`) — that figure is the
TOTAL block length including the `0x36` service byte and the block-sequence-counter
byte. The driver sliced a full `0x0FFF`-byte DATA chunk and prepended those 2 header
bytes, sending 4097 bytes for a full block: 2 bytes over the ECU's own stated limit,
which it silently dropped rather than rejecting with a `7F` (hence a timeout, not an
NRC). Every slot that fit in one block under 4093 data bytes never hit this ceiling,
which is why only slots 04/06/07 were ever affected. **Fix:** block size corrected to
`0x0FFF - 2` (4093 data bytes/block).

**Verification added.** A `verify` mode was added to the driver: read live DID
`F182` (calibration identity block) and compare every slot against its on-disk
container using
[`tools/mdi2_client/mdi2/calibration_readback.py`](../tools/mdi2_client/mdi2/calibration_readback.py)'s
own validated `parse_f182()`/`calibration_record()` (loaded directly by file,
bypassing `mdi2/__init__.py`'s `pycryptodome` import, a dependency this bench venv
does not have and this offline comparison does not need). The read needs only
`10 03`+`22 F1 82` (no SecurityAccess/RoutineControl), but still needs the module
held awake by the same precondition injector (modified `20D` + `284`=all-zero) used
for the write — a bare native-profile replay was tried first and the module went
unresponsive right after the session-control response.

**Result:** slots 04, 06 and 07 were written and reconfirmed under the fixed driver
in this session (clean `36`/`37` exits, PEC `62 F0 F1 00 00`); slots 02, 03, 05, 08,
0B–0F are single-block transfers that predate these two fixes in this same bench
session and were not individually re-exercised against the fixed code path. The
live `F182` readback below is the authoritative, current confirmation that all 14
slots are correct on the ECU as of this write-up, independent of which run wrote
each one:

| Slot | Part | F182 record (observed) | Match |
|---|---|---|---|
| 02 | 87863250 | `02 05 3c af d2 41 41` | yes |
| 03 | 84517309 | `03 05 09 a1 bd 41 41` | yes |
| 04 | 85045371 | `04 05 11 b0 7b 41 41` | yes |
| 05 | 87846416 | `05 05 3c 6e 10 41 42` | yes |
| 06 | 87846371 | `06 05 3c 6d e3 41 41` | yes |
| 07 | 85783460 | `07 05 1c f3 a4 41 41` | yes |
| 08 | 87846432 | `08 05 3c 6e 20 41 41` | yes |
| 09 | 87846376 | `09 05 3c 6d e8 41 41` | yes |
| 0A | 87846368 | `0a 05 3c 6d e0 41 41` | yes |
| 0B | 86292118 | `0b 05 24 b6 96 41 41` | yes |
| 0C | 85102312 | `0c 05 12 8e e8 41 42` | yes |
| 0D | 87846384 | `0d 05 3c 6d f0 41 42` | yes |
| 0E | 84517418 | `0e 05 09 a2 2a 41 41` | yes |
| 0F | 87846380 | `0f 05 3c 6d ec 41 41` | yes |

Every observed record matched its expected value — `calibration_record()` computed
from the same on-disk stock LTZ containers — byte-for-byte; no mismatches.

**Evidence:** live session logs captured this run (driver stdout, `--json-out`);
VIP console UART log cross-correlated the Issue-1 fault cascade in real time.

#### Factory-reset and ELK CAN-control attempts — 2026-11-17

**Goal (factory reset):** trigger a UDS user-data reset over CAN5.

**Method/result:** With stock LTZ restored, extended session + profile01
SecurityAccess succeeded. Initial `31 01 02 47` → `7F 31 22`, radio
`F085=04`. Prerequisite resolved: retaining the full harness, set standard
`20D`/DLC6 byte4 bits5–7 to 2 (other bits preserved) → VIP reset-gate
`FEBD3725` changed 4→2, radio `F085` became `02`. Extended
session/profile01, `31 01 02 47 → 71 01 02 47`; Android logged successful
customization restoration, ADB disconnected, owner observed the factory
reset occurring. Original `20D` restored afterward; no RAM writes or
calibration clears used. **Evidence:** B capture + UART; owner observation.
Final post-reset setup/completion is distinct from confirmed reset
initiation. See [reset evidence](../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md).

**Goal (ELK control):** find a CAN-reachable ELK/boot-mode control selector.

**Method/result:** On stock LTZ, extended session/profile01 granted.
`2F818003 → 7F 2F 31`; separate `AE818003 → 7F AE 11`. No positive
acceptance or ELK boot established; no RAM/calibration/firmware writes or
wipe performed. Read-only RAM tracing found API12 availability bytes both 1
and the transaction manager idle; no polled ELK request flag found — the
sender allocates/queues a message under synchronization, so no RAM-write
test was performed (no verified writable request field established). Later
static dispatch tracing: NRC31:`8180` is absent from the 221-entry CAN DCM
identifier table, and none of the 39 configured I/O-control callback entries
directly selects the ELK callback — the internal `8180` descriptor is not a
registered CAN identifier, so changing security/power state cannot repair
this lookup failure. Other proprietary/internal entry points remain
unestablished. **Evidence:** B capture; static firmware trace. See the
[ELK analysis](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15).

## IPC animation-status sweep and startup path — 2026-11-16

**Goal:** determine what `529` b0 bits 5–7 (IPC "animation status") control
during startup.

**Method:** post-boot sweep replaced only `529` b0 bits 5–7 with each raw
value 0–7, held 10 s at the captured 320.270 ms period, all other payload
bits (incl. IPC HMI Ready) preserved; original payload restored after. Then
eight full cold starts, one per value, using a fixed procedure: fresh UART,
original `145`, +0.5 s start selected-value `529` cyclically, at +30 s add
`145/529/457/458` for 12 s (only `529`'s animation field modified), stop at
+42 s, observe to +60 s, ≥10 s powered off between boots.

**Result — post-boot sweep:** every value queued 32 frames / 32 TX echoes,
produced the matching RH850 `IPC Animation Status = n` line, no CAN-status
or power-off events. Values are status codes, not yet identified as eight
distinct animation-selection commands.

**Result — cold-start comparison** (RH850 bracket timestamps, seconds from
boot counter origin):

| `529` value | Ready | Complete | HmiInit s | STARTUP_FAULT_TIMEOUT s | Propulsion s | Display |
|---|---|---|---:|---:|---:|---|
| 0 | false | not reported | — | 15.721 | 15.721 | Black until "Start Your Vehicle", then homescreen |
| 1 | true | true | 8.435 | none | 21.894 | Chevy logo |
| 2 | true | false | 8.445 | 23.441 | 23.441 | Chevy logo |
| 3 | true | false | 8.474 | 23.471 | 23.471 | Chevy logo |
| 4 | true | false | 8.333 | 23.321 | 23.321 | Chevy logo |
| 5 | true | false | 8.425 | 23.421 | 23.421 | Chevy logo |
| 6 | true | false | 8.530 | 23.521 | 23.521 | Chevy logo |
| 7 | true | false | 8.638 | 23.631 | 23.631 | Not physically reported |

Value 0 takes a 15 s AnimationInit fault-timeout path without HmiInit or a
logged PlayAnimation request. Values 2–7 enter HmiInit but never report
completion, timing out ~15 s after HmiInit. Value 1 completes the normal
handshake without fault. (**Correction, 2026-11-15:** the initial trial
filter missed the uppercase timeout event; raw UART was retained/checked and
the filter corrected for later trials.) Chevy logo physically confirmed for
values 1–6; value 7 measured but display not separately reported.

A ninth cold start began at value 2, then changed only this field to 1 when
RH850 emitted `evHMIReady`: Complete=false at VIP 21.657 s, animation status
1 at 21.688 s, Complete=true same timestamp, Propulsion 21.689 s, no
timeout — a completion update at that stage advances startup without a new
power cycle or full harness replay.

**Functional classes (observed roles under this calibration, not recovered
OEM names):** 0 = not ready; 1 = ready/complete; 2–7 = ready but incomplete.
Decode: `status = (data[0] >> 5) & 7`; set via
`b0 = (original_b0 & 0x1F) | (status << 5)`.

**Evidence:** B capture, 2,205 frames / 2,205 TX echoes across the nine
cold-start windows; UART state transitions and physical display observation
are the semantic evidence, not echoes alone.

## Door, wake and explicit shutdown paths — 2026-11-16

**Goal:** identify CAN-level door/wake/shutdown triggers distinct from the
animation-status sweep; find the actual welcome-video command.

**Background:** VIP outgoing PlayAnimation IPC request values **1, 2, 3,
4** (distinct from `529`'s CAN animation-status 0–7) trace through selector
chain `70498`→`50FFC`→`89B1E`→request word `FEBD3464`→`73D62` (opcode `43`).
Action wrappers: `704D0` requests 4, `7053A` requests 2, `70500/70516/70556`
request 3, `705AC` requests 1. The observed driver-door shutdown matches
GM's documented retained-accessory-power behaviour (driver door ends radio
RAP after Off) — [body-builder manual](https://www.gmupfitter.com/wp-content/uploads/2022/10/23_Silverado_1500_Electrical_Body_Builder_SM_en_US_2022OCT24.pdf)
§7-972, behavioural corroboration only.

**Wake test:** from Sleep, repeating `529` with animation status 2 did not
wake the radio (5 queued, 3 admission echoes, zero radio RX, no UART change
before a 1.596 s transport abort — a non-ACK result, not a validated
rejection). A single original `145` woke VIP (wakeup factor `400000`, reset
factor `400` vs `201` on preceding cold starts); SoC power levels 1–4
followed, 326 radio frames in an 8 s window; display stayed off.

**New verified signal: `4DA` DLC 8, b7 bit 0 = DriverDoorOpen/Closed**
(signal index `660`, PDU `26`, bit 56, read at `5032C`, posts event 15/14 at
`6F48C` selector 0; event-name table at `F9916`). Other door selectors
`14C`(`4DB` bit56), `8B7`(`4D9` bit59), `B05`(`4D8` bit6) observed but not
individually assigned.

**Continuous wake test:** `145`, then `145/529` status 1, seed pair at +30 s
→ display on, Chevy logo, driving-attention prompt, homescreen after OK.
After the startup sender stopped, `PowerModeOff`/`LocalInfotainment` at VIP
105.731 s; the subsequent `4DA` door-open frame at 105.949 s produced
DriverDoorOpen + PlayAnimation request **4** (channels 2/16), HmiInactive at
105.952 s, Requesting Shutdown at 105.954 s, display off confirmed. Follow-up
UART: `SHUTDOWN_ANIMATION_FAILSAFE_TIMEOUT` at 120.941 s (~15 s after door
open), Sleep at 135.942 s (~30 s), `BACKGROUND_SLEEP_TIMEOUT` at 145.941 s,
SoC power level 0 at 165.801 s (~60 s) — a working explicit door-triggered
shutdown, but its animation-completion failsafe means it is not a fully
clean shutdown-animation handshake. 343 queued/343 echoes.

A second away-from-display sequence: door-open→request 4/HmiInactive; close
→ DriverDoorClosed, no request 2; a later door-open while HmiInactive →
**PlayAnimation request 1** (channels 2/16) at VIP 112.254–112.255 s; close
→ DriverDoorClosed again, no request 2. Request 1 is a live-observed
alternative to request 3; visual effect unverified at this point (see
animation-decode result below). 346 queued/346 echoes, ended ACK-only.

**State-table trace:** 242 validated 28-byte descriptors at file `11236`,
12-byte transitions/debug names at `F9A06`. HmiInactive (state 125) owns
DoorOpen (event15, guard `70400`, action `705AC`→selector value 1) and
DoorClosed (event14, guard `70454`, action `7053A`). AnimationInit (state
213) instead clears an arm flag (`6FCA0`) on DoorOpen and sets it (`70646`)
on guarded DoorClosed; junction 233 can select request 2 via that flag;
DoorClosed guard `7036A` requires PowerMode Off — the bench's normal
power-on path uses the other branch (conditional, not unconditional CAN
video selectors).

**Verified signal: direct power-mode control, `529` b1 bit 7** (signal
`828`), with b0 bit0 (`829`, ready) clear and freshness/configuration gates
met: `50BA0` selects raw mode 0/4, table `2C574`→internal PowerMode 0/2,
setter `6F6A4` emits PowerModeOff/On.

| Bit 15 operation | RH850 observation, VIP s |
|---|---|
| Clear, round 1 | PowerModeOff + LocalInfotainment at 36.181 |
| Restore, round 1 | PowerModeOn at 40.201; Propulsion at 40.202 |
| Clear, round 2 | PowerModeOff at 44.211; LocalInfotainment at 44.212 |
| Restore, round 2 | PowerModeOn at 48.231; Propulsion at 48.232 |

A final clear → Off at 52.261 s; DriverDoorOpen at 54.264 s → request 4 +
HmiInactive at 54.267 s, no 60 s sender-expiry wait. 320 queued/320 echoes,
ACK-only end. Decode: `bool(data[1] & 0x80)`; clear only mask `0x80` for Off.
This mapping doesn't establish Accessory/Service-mode encodings or the
companion bits' names.

**Request 2 reached via vehicle-Off startup:** from Sleep, `145`, then
`145/529` with b1 bit7 clear, b1 bit1 retained, animation status 1;
door-open at +1.830 s → AnimationInit; close at first CSM state-0 →
DriverDoorClosed at 6.549 s; at 8.524–8.525 s VIP sent PlayAnimation **2**
(channels 2/16), HmiInactive at 8.527 s; CSM state 1 at 23.528 s; Sleep at
36.542 s. No request-3 logo in this trial. 341 queued/341 echoes. Owner
away — confirmed command/state path, **unverified visual output** at this
point.

**Request-1 entry-to-On candidate:**

| Step | Inputs / observation |
|---|---|
| Prewake, 12 V retained | `145`, then cyclic `145/529`: power-mode bit0, HMI Ready1, animation status1 |
| Request infotainment startup | `53B` b7 bit3=1; Sleep→AnimationInit at 1.749 s, HmiInactive at 8.383 s, no door-close arming edge |
| Simulate driver entry | `4DA` b7 bit0=1 at HmiInactive; DriverDoorOpen at 8.994 s → PlayAnimation **1** (channels 2/16) |
| Request vehicle On | +5 s, restore `529` b1 bit7; PowerModeOn at 14.111 s, request 3 at 14.302 s, HmiInit at 14.303 s |
| Finish startup | HMI Ready/Propulsion ~24.094 s |
| End test | Close door while On, clear power selector, open door; Off at 39.761 s, request 4/HmiInactive at 41.775–41.778 s |

312 queued/312 echoes, no `evSTARTUP_FAULT_TIMEOUT`; **neither the video nor
a homescreen was physically observed** in this unattended run (do not
transfer the earlier request-3 physical observation to this candidate).

**Supported request paths observed:**

| PlayAnimation request | Confirmed context | Visual evidence |
|---|---|---|
| 1 | DriverDoorOpen while HmiInactive; can be followed by PowerModeOn/normal startup | Unverified at capture time (see below) |
| 2 | PowerMode Off + armed early DriverDoorClosed edge during AnimationInit | Unverified at capture time; followed by HmiInactive/Sleep |
| 3 | Normal On startup or HmiInactive→HmiInit | Chevy logo observed |
| 4 | DriverDoorOpen ends vehicle-initiated LocalInfotainment after Off | Display off observed |

### Display-side player resolves the animation command numbers — 2026-11-16

**Goal:** identify the actual display-side meaning of PlayAnimation request
values 1–4 and find the welcome-video trigger.

**Method:** `system/bin/animengine` (owner's Y175 cleanroom, x86-64 ELF PIE,
SHA-256 `d28323285d8fcb8b48e324114bedbc7dc0d835cc4014c3d0891dd2156dac050c`)
decoded statically — live binary unreadable (`Permission denied`; `adb root`
blocked on production builds), so this is corroborated, not byte-matched,
against the live ROM via CAN-driven display tests.

**Result — command table.** `AnimEngine::showAnimation(AnimationType)` at
ELF VA `435FC0` maps input 1–4 through table `324F0` to internal events
`[11,1,2,3]`; event-name table `4F66E0` resolves:

| VIP/HIDL request | Player event |
|---|---|
| 1 | STOP_ANIMATION |
| 2 | SHOW_WELCOM_ANIM (sic) |
| 3 | SHOW_STARTUP_ANIM |
| 4 | SHOW_SHUTDOWN_ANIM |

So the earlier request-1 candidate was a stop/On-startup handshake, **not**
a welcome-play command (visual replay: Chevy logo then homescreen, no
moving welcome video) — this corrects the prior candidate interpretation
without changing the confirmed CAN power/door mappings.

The engine holds welcome-calibration gating, separate `welcomeanim.mp4`/ZIP
assets, and startup/shutdown paths; cleanroom has 31 welcome MP4 variants,
fallback `product/ro/anim/3/graphics/1/welcomeanim.mp4` (H.264, 1280×768,
180 frames/6 s) — an available reference asset, not necessarily the live
brand selection. `getPersistentData()` skips property overrides when
`persist.sys.anim.flavor` is absent/-1, leaving calibration-based config; no
animation property/calibration was modified in these tests.

**Result — request 2 is the welcome video (physically confirmed).** A
replay using the vehicle-Off/early-door-close path (above) **did play the
moving animation**, observed by the owner, possibly cut short, followed by
Chevy logo when On was asserted at +8 s. A follow-up waited for the first
post-playback CSM state-1 report (10 s min, 22 s fallback) instead of
forcing On at 8 s: report at VIP 23.311 s (~15 s after request 2); Run
asserted; HMI Ready at 23.430 s, request 3 at 23.581 s, Propulsion at
24.908 s. Completion did not suppress the subsequent startup request.

A follow-up waiting for both welcome completion and HMI Ready (bounded 30 s
after request 2): welcome completion at +14.892 s, HMI Ready not reported
before Run; radio returned to Sleep at +37.271 s, Run handoff at ~+37.4 s
→ request 3, HmiInit, Propulsion. Physical: welcome video → black screen →
Chevy logo → homescreen — waiting longer did not remove the logo; this trial
crossed the HmiInactive timeout.

**Recovered state-table support:** `evPowerModeOn` enters StartupDelayWait,
whose `evSTARTUP_DELAY_WAIT` branch reaches action `70500` (request 3)
before HmiInit — HMI readiness alone offers no alternate branch here.

A second follow-up kept status 1 through welcome playback, then at the first
post-playback CSM state-1 report (+14.871 s) changed only the animation
field to 0 and power-mode bit to On: UART confirmed status 0 /
`isAnimationReady=false` before `evPowerModeOn`, but request 3 still
followed ~0.2 s later with HmiInit; `evSTARTUP_FAULT_TIMEOUT` ~15 s later,
then Propulsion. Physical: welcome video→Chevy logo→homescreen, no black
interval — applying the cold-start logo-skip value after welcome does
**not** suppress the startup request on this HmiInactive path; it only adds
a fault timeout. No clean welcome-to-homescreen handoff without the logo was
established.

**Evidence:** CAN/UART captures correlate throughout; no permanent
player-setting change or background keep-alive was required for the trigger.

## Adapter status and bench validation campaign — 2026-11-15/16

Adapter-generated status records (not application IDs), interpreted per
[Linux CAN error definitions][E]: `2000000C` (controller+protocol class,
form-error bit) seen 10/24/34 times (startup/later/full), `20000004`
(controller class, unspecified) 3/2/5 times; startup status ends at
`.023833 s` (`B:88`); later clusters at `631.808224–631.811886 s` and
`637.551218–637.555347 s` precede the final retry stream (`B:89198`,
`B:90669`); no overflow reported.

### Active harness communication test — 2026-11-15

**Goal:** determine whether the radio decodes TesterPresent/generic
diagnostic probes beyond the 32-ID harness profile.

**Method:** before probing, 133,528 data frames over 22.65 min added no new
harness ID/payload. 66 s isolated-harness test: 5 s baseline, 45 s replay of
1,893 recorded radio-dependent frames, 5 s recovery, then three generic
TesterPresent requests (`3E 00`, ISO-TP single frame: standard
`0x7DF`/`0x7E0`, extended `0x18DB33F1` — not confirmed harness diagnostic
addresses).

**Result:** all 1,896 queued frames got adapter TX echoes, zero host-pending
entries/CAN errors/overflows (echoes are mailbox-admission, not bus-ACK
proof). RX counts 500/4,497/499/1,099 for baseline/replay/recovery/TesterPresent;
every phase retained only the same 32 IDs; zero new/changed RX payloads vs
the H baseline. Median per-ID periods 320.405/320.363/320.315/320.354 ms —
consistent with a fixed cyclic emulator, not proof of receiver-free
firmware. No EEPROM/reset/security/programming request used. See
[bench baseline](../hardware/bench_setup.md#harness-replacement-candidate)
for the later ground/termination fix.

### Radio-only single-cycle result

One controlled cycle (32 harness frames, 32 TX echoes) received 80 valid
radio frames across 39 IDs, 48 status records; adapter returned to
listen-only/ACK-disabled. UART: startup banner +0.30 s, `IPC RX: New Power
Level` from SoC for levels 1/2/3/4 at ~+1.17/+1.59/+5.72/+5.74 s,
`ReportCenterStackHMIReady` at +22.48 s; display stayed off physically.
Only Sleep was announced. Neither `CSM_On` nor HMI-ready alone proves
AAOS/display activation.

### Individual-frame and queue-recovery probes

With SoC at power level 0, one original `0x145` → SoC power-level reports
at +1.16 s, first inbound T1 traffic at +3.169834 s, SoC levels 3/4 +
`CSM_On` near +5.7 s, HMI-ready +21.25 s, SoC power level 1 at +22.62 s
(`radio-stepwise-t1.pcapng`). Subsequent single `0x521`/`0x20D`/`0x523`
probes echoed with no new UART/T1 activity; `0x529`/`0x551` queued without
TX echoes and were cancelled on controller cleanup — not a valid negative
test. Later one-shot attempts produced USB-queued frames with no echo/RX/UART/T1
change; MODE stop/start and a USB port reset did not clear it. Internal
silent loopback (`0x13`) drained 62 stale TX echoes, then normal delivery
resumed. [candleLight v2.0 transmit code][C] echoes a frame on bxCAN
mailbox entry, before ACK — three unacked frames fill the mailboxes;
feature mask `0xf3` matches that firmware family without identifying the
exact revision. "Completed" in earlier notes = adapter TX echo, not
confirmed wire delivery.

After recovery, one pass of all 32 frames at ~0.5 s spacing (15.765 s
first-to-last TX) produced radio traffic, HmiInit, Propulsion, display
physically on; AnimationInit at +1.309 s after only `145/521/20D` sent,
HmiInit +8.544 s, Propulsion +23.393 s — supports staged-arrival timing
without proving it's required (fast continuous replay also works). A later
half-second three-frame prefix restored Propulsion from warm
LocalInfotainment at +1.195 s; its power-mode timeout returned to
LocalInfotainment at +62.208 s.

### Startup reduction from verified SoC-off — 2026-11-15

**Goal:** find the minimum CAN frame subset needed to reach Propulsion from
a verified software SoC-off state (ADB offline, ≥5 s no T1, stale queues
drained via silent loopback).

**Method:** each selected harness-frame subset sent once, in captured
order, ~0.5 s apart, no cyclic repeat.

| Frames sent once | AnimationInit | HmiInit | HMIReady | Propulsion | Startup-fault timeout |
|---|---:|---:|---:|---:|---|
| Full 32 | 1.321 | 8.295 | 22.384 | 22.411 | None observed |
| First 3 | 1.305 | Not observed | 22.417 | 16.235 | `evSTARTUP_FAULT_TIMEOUT` 16.225 |
| First 4 | 1.318 | Not observed | 22.692 | 16.235 | `evSTARTUP_FAULT_TIMEOUT` 16.226 |
| First 16 | 1.312 | 8.734 | 23.373 | 23.400 | None observed |
| First 8 | 1.320 | 8.445 | 23.536 | 23.380 | `evSTARTUP_FAULT_TIMEOUT` 23.371 |
| First 12 | 1.312 | 8.351 | 23.182 | 23.211 | None observed |
| First 10 | 1.322 | 8.381 | 22.275 | 22.306 | None observed |
| First 8, software-off repeat | 1.318 | 8.732 | 23.161 | 23.188 | None observed |

First 8 IDs: `145 → 521 → 20D → 523 → 529 → 551 → 1F5 → 0C9`. 16-frame
reference adds `0F1 → 02C → 4B6 → 016 → 023 → 028 → 02B → 0B5`. All reduced
trials received the expected echoes, real radio traffic across the same 40
IDs, SoC level-4 and T1 activity.

**Result:** 3-frame activates InfotainmentPN but skips HmiInit, uses the
fault-timeout path to the backlight. 8-frame reaches
`evCenterStackAnimationReady` (+8.416 s)/HmiInit but its Propulsion
transition also crosses a fault timeout, just before HMIReady.
**Correction, 2026-11-15:** the initial 8-frame success classification
checked milestones but missed the timeout event; `log_criteria_success`
results require this additional check. First-16 shows the back half of the
loop (incl. `0x1F1`) was unnecessary under these conditions (not that each
of the first 16 is required). 4-frame prefix (`145→521→20D→523`) also skips
HmiInit via the timeout fallback. First-12 and first-10 each complete
*without* an observed fault timeout (12/10 TX echoes, same 40 IDs, SoC
level4, T1 active); extra frames beyond 8 are `0F1→02C→4B6→016` (12-case) and
`0F1→02C` (10-case) — individual necessity/reproducibility unestablished.
The later software-off 8-frame repeat completed cleanly (no timeout),
directly confirming frames 9–16 are not universally required for these
milestones; one trial per subset is not reproducibility proof.

### Eight-frame startup after physical 12 V removal — 2026-11-15

**Goal:** repeat the reduced-frame startup after a true physical power-cycle
baseline (distinct from software shutdown).

**Method/result:** after confirmed 12 V removal, fresh UART, 0.5 s delay,
then the first 8 original frames once at ~0.5 s spacing:

| Marker | s from first CAN TX |
|---|---:|
| Sleep, pre-TX | -0.269 |
| SoC power levels 1/2 | 0.267/0.585 |
| AnimationInit | 1.260 |
| SoC power levels 3/4 | 4.836/4.846 |
| HmiInit | 7.867 |
| HMIReady/Propulsion | 20.966/20.993 |
| USB ADB offline/authorized | 28.335/28.339 |

All 8 echoes, 38 radio IDs, no fault timeout; display showed a **Start Your
Vehicle** restriction coexisting with UART Propulsion. ADB became authorized
without a manual enable this boot: `adb_enabled=1`,
`development_settings_enabled=1`, `init.svc.adbd=running`,
`persist.sys.usb.config=...=adb`; `ro.boot.bootreason=cold`,
`sys.boot.reason=cold`, both boot-completed flags =1, `ce_available=true`,
fresh kernel uptime — weighs against a standby resume. Cause of automatic
ADB availability unresolved (persistent config / local boot-keyguard path /
prior UDS side effect despite NRC31 / an effect of the 8-frame traffic not
isolated); decompiled GM keyguard has a local `RDMSADBEnable` call but no
matching live enable event found in retained logs, not byte-matched.

### Full-sequence restriction clear and ADB disable — 2026-11-15

**Goal:** test whether continuing CAN traffic past the 8-frame boot clears
the vehicle-start restriction / changes ADB state without a reboot.

**Method/result:** same physical 8-frame boot (Android already boot-complete,
restriction shown, `adb_enabled=1`); a subsequent 10 s full-32-frame cyclic
replay (943 frames queued). UART: PowerModeOn/Propulsion + a ProtoKey-to-SoC
transmission; USB ADB went offline/disconnected 4.676 s after first
full-sequence TX; display changed to AAOS home screen, restriction gone,
Settings showed **USB Debugging Off**. No ADB-disable UDS request, local
setting write, ECU reset, or second power cycle used — only the earlier
Mac-clock sync preceded it. AAOS did not reboot; extra traffic completed/
changed state while already running. Trigger may be one of the 24 extra
IDs, a companion combination, or repetition/timing — not isolated.

### Split-frame isolation of the gate transition — 2026-11-15

**Goal:** isolate which of the 24 additional IDs (beyond the base 8) drives
the restriction-clear/ADB-disable transition.

**Method/result — added-message groups** (base-8 + listed additions, 10 s
each, 18 s observation, sequential not cumulative, same restricted boot):

| Added original IDs | ADB result |
|---|---|
| `0F1 02C 4B6 016` | Remained authorized, `adb_enabled=1` |
| `023 028 02B 0B5` | Remained authorized, `adb_enabled=1` |
| `457 458 08C 037 22A 01E 435 26F` | Offline +6.190 s, disconnected +6.193 s |
| `50F 1F1 0AA 1E5 1C6 18E 0C1 204` | Not sent this scan |
| Full 32 control | Not sent this scan |

Positive group: ProtoKey-to-SoC transmission +0.853 s; USB watcher recorded
ADB interface `8087:09ef` detaching +6.638 s; restriction cleared, AAOS home
visible. Not yet a proven minimal/sufficient set (earlier groups and `1F1`
already sent on this boot).

**Fresh-cycle splits (each a fresh cold 8-frame boot):**

| Split tested | Frames (+ base 8) | Result |
|---|---|---|
| First half | `457 458 08C 037` | 372 queued frames/10.004 s; ProtoKey-to-SoC +0.978 s; restriction cleared — **sufficient alone** |
| Pair | `457 458` | ProtoKey-to-SoC +0.017 s and +1.025 s; restriction cleared; ADB unavailable throughout (not an ADB toggle in this run) |
| `457` alone | `457` | Restriction NOT cleared; ADB stayed authorized; ~1 Hz ProtoKey-to-SoC activity |
| `458` after prior `457` same boot | `458` | Restriction cleared; ADB offline +4.425 s, disconnected +4.428 s |
| `458` alone, fresh boot (no prior `457`) | `458` | Restriction NOT cleared; ADB stayed authorized, ~1 Hz ProtoKey-to-SoC |
| `457` after prior `458` same boot (reverse order) | `457` | ADB offline +3.720 s, disconnected +3.727 s; home screen reported |
| One `457→458` pair only (11.733 ms gap) | pair once | Restriction NOT cleared after 18 s; ADB stayed enabled |
| Two pairs (4 frames) | 2×`457 458` | ADB remained authorized; `uiautomator` confirmed restriction/ProtoKey view still present |
| Four pairs (8 frames) | 4×`457 458` | ADB already absent pre-phase; UI outcome awaited physical confirmation |

**Result:** both orderings of the *repeated* base+pair addition clear the
gate; single isolated `457` or `458` alone do not; a single pair does not;
exact-count pair-only tests (without refreshed base traffic) also do not.
This fits a retained companion-value or multi-stage mechanism — minimum
repeat count, strict ordering requirement for single arrivals, and the role
of concurrent base-refresh traffic are not isolated. A base-only repeat
after four pairs also left the restriction visible.

**UART correlation:** `457` ↔ "Seed 1 cached", `458` ↔ "Seed 2 cached" in the
PROTOKEY logger; successful transitions show both seed-cache events, a
final ProtoKey-to-SoC transmission, and cessation of the ~1 Hz retry loop.
Restricted cases keep the missing-seed/retry report. Not a decoded
payload/checksum; missing/cached labels are not fully consistent across
windows, so this is a correlation, not a sufficient decoder. HmiInit/HMIReady/
Propulsion all occur while the restriction remains visible — none is a
home-screen acknowledgement.

**Caveat throughout this campaign:** manual USB-debugging enable was
re-verified (`adb_enabled=1`, persistent USB `adb`, boot-complete) before
each power cut where ADB state mattered; a separate physical-cycle control
with ADB starting disconnected reproduced the restriction with **ADB staying
disconnected** (8-frame repeat also left it disconnected) — establishing the
restriction is reproducible independent of ADB availability; these two
states must not be conflated. The exact prompt text is
`userprofile_5_4_engineCommand_csm`/`...engineDescription_csm`
(`keyguard_proto_key_view.xml`, `GMKeyguardProtoKeyView`); decompiled
`KeyguardProtoKeyViewController` resumes via `k(true)`/`k(false)` and routes
to a local ADB-handler path testing `persist.sys.gm.encryption` and
`vendor.gm.security.state` — static family-level evidence only, decompiled
control flow has invalid branches, not byte-matched live, and
`vendor.gm.security.state` read empty on this bench despite
`persist.sys.gm.encryption=true`.

### ACK-controlled repetition and keep-alive timing — 2026-11-15/16

**Goal:** find whether periodic application traffic (vs. passive ACK-only
reception) is required to sustain Propulsion, and identify a minimal
keep-alive set.

**Method/result — ACK-only vs repeated full-32:** ACK-enabled reception
with no application TX produced no new activity. A bounded 30 s repeat (2,894
frames, 90 complete cycles + partial, all echoed; controller warnings
present) turned the display on and produced HmiInit/Propulsion, absent from
the single-cycle case. After repeat TX stopped, ACK-only reception continued
62.61 s before `evPowerModeOff`/LocalInfotainment — periodic application
traffic matters to sustain that state; ACK-only participation alone does not.

**Isolating `0x1F1` and `0x145`** (ACK-enabled, original payloads, no bit
changes):

| Test | Result |
|---|---|
| One original `0x1F1` | Startup activity then return to power level 1; no Propulsion |
| `0x1F1`, repeated 30 s | No HmiInit/Propulsion or radio CAN data |
| `0x145`, repeated 30 s | Radio traffic + startup/HMI-ready; no HmiInit/Propulsion |
| `0x145`+`0x1F1`, repeated 30 s | Radio traffic + startup; still no HmiInit/Propulsion |
| Full 32-frame control | Reproduced HmiInit and Propulsion |
| Other 31 frames, omitting `0x1F1`, 90 s | Sustained Propulsion beyond the prior timeout, without `0x1F1` |

Do not treat `0x1F1` as a validated A11 Off/Run selector or assign it a
Service-Mode value (external DBC value 3 = Crank Request; UDS
session/programming prerequisites are separate). Byte-layout note: `0x145`
starts with node byte `0x45`, `0x180` with `0x80`, both second byte `0x40`;
fits [AUTOSAR CAN NM R24-11 §§7.6/7.11][N]'s byte0-node-ID/byte1-CBV layout
(bit6 = PN-info present) without proving the GM assignment — `0x40` is not
established as the generic active-wakeup bit.

**Post-boot keep-alive isolation, 2026-11-16** (known four-ID recipe
restored between trials):

| Periodic traffic after startup | Result |
|---|---|
| Original `145` only | PowerModeOff +62.303 s, LocalInfotainment +62.310 s (195 queued/echoed) |
| Original `529` only | Propulsion sustained 95.142 s, no PowerModeOff (297/297) |
| Original `457+458` only | PowerModeOff +62.599 s, LocalInfotainment +62.605 s (390/390) |
| Original `145+529` | Propulsion sustained 95.136 s (592/592) |
| `529` with only b1 bit1 cleared (HMI Ready=0) | Propulsion sustained 95.066 s (297/297) |

`529` alone sustains the post-boot hold; `145` alone and the seed pair alone
do not; the HMI-ready bit need not stay asserted post-startup. Both the
power-mode selector (b1 bit7, see door/wake section) and the message-freshness
timeout matter — arbitrary `529` payloads are not validated.

**Long-duration result:** a renewable `529`-only stream at the captured
period ran **43,131 s (11 h 58 min 51 s)** without a PowerModeOff/SoC
power-level-zero failure; 139,080 frames queued/echoed (echoes ≠ wire-ACK
evidence). Android uptime at that point 43,747.84 s (12 h 9 min 8 s),
boot-completed and ADB-enabled both 1, wall time within 1 s of the Mac.
UART bracketed timestamp wraps near 429,497 ms are counter artifacts, not
reboot evidence. (Observer bug note: the watcher required a fresh Propulsion
announcement and raised `RuntimeError: No verified Propulsion baseline
after four-ID restore` when the radio was already in that state; corrected
to initialize from retained UART state — no radio reset/programming command
involved.)

### Explicit Off/Accessory candidate tests — 2026-11-15

**Goal:** test candidate `0x1F1` Off/Accessory/Run values as an explicit
power-mode command (distinct from the natural timeout path).

**Method/result — Off (0):** after Propulsion restored via the first-12-frame
sequence, one `0x1F1` frame set both external-DBC primary/backup power
fields to 0 (byte0 mask `0x33` only, rest of payload retained), then 17 more
over a 5 s repeat 12 s later (29 total queued/echoed across the wake+Off
test). No immediate UART transition. `evPowerModeOff`/LocalInfotainment
occurred 58.973 s after the last wake TX — 34.429 s after the single Off
frame, 17.585 s after the last repeated Off frame — consistent with the
existing inactivity timeout, not an explicit Off response; the candidate
frames did not visibly reset the power-mode timer. (Measured timeout varies:
+62.221 s for the 3- and 4-frame SoC-off prefixes, +64.606 s for 8-frame,
+64.611 s for 12- and 16-frame — not a universal 62 s deadline.)

**Method/result — Accessory (1):** same procedure, one frame then 16 more
over 5 s, 12 s later (29 queued/echoed). No immediate transition;
PowerModeOff/LocalInfotainment ~65.6 s after the warm-wake test began,
matching the existing timeout. Does not validate Accessory control or
distinguish "ignored" from "unmet prerequisite."

**Method/result — ordered 0→1→2→1→0 (Off→Accessory→Run→Accessory→Off)**
from LocalInfotainment, no harness replay between steps, each value 5 s
repeat + 5 s observation (16 queued/echoed per step, 80 total): no new
UART transition over the 50 s test; state stayed LocalInfotainment. The
initial transmitted Off value did not establish an actual powered-off
baseline. Stateful sequencing remains plausible for the correct signals;
this negative test only shows the two candidate `0x1F1` fields alone,
without companion traffic, did not control the observed state.

### Direct CAN5 ADB-enable diagnostics — 2026-11-15

**Goal:** test a reported CAN5 UDS ADB-enable routine candidate directly on
CAN5 (bypassing earlier MDI2 attempts, which lacked the required external
12 V supply and cannot establish this physical result).

**Method:** powered CANable on the radio's X6 CAN5 pair, 500 kbit/s,
harness MCU absent, bounded diagnostic-frame support.

**Result — transport addressing** (after a 12-frame warm wake):

| Request CAN ID | Actual response CAN ID | TesterPresent |
|---|---|---|
| `0x14DA80F2` | `0x14DAF280` | `3E 00 → 7E 00` |
| `0x14DA80F1` | `0x14DAF180` | `3E 00 → 7E 00` |
| `0x18DA80F1` | None observed | No response in 2 s |
| `0x18DA80F2` | None observed | No response in 2 s |

**Correction, 2026-11-15:** direct CAN5 replies use `14DA`, not the archived
gateway-route `145A` pattern; an initial host filter expected `145A` and
missed the captured `14DA` reply — a host-filter miss, not radio
nonresponse.

**Result — ADB-enable candidate** `31 01 03 32 DD 42 10 01` (domain `DD`
unknown), transported via ISO-TP first/consecutive frames with real flow
control:

| Direct F2/CAN5 test | Result |
|---|---|
| Domain `00`, default session | `7F 31 31` |
| Extended session, `10 03` | `50 03 00 64 01 F4` |
| Domains `00,01,02,FF`, extended | Each `7F 31 31` |
| All 256 domains, extended, no grant | **256 × `7F 31 31`**, no timeout |
| Level-1 SecurityAccess | 31-byte all-FF seed; `67 02` accepted |
| All 256 domains, after grant | **256 × `7F 31 31`**, no timeout |
| Restore default, `10 01` | `50 01 00 64 01 F4` |

No disable/reset/EEPROM/calibration/programming request sent; ADB observer
stayed disconnected throughout. NRC `31` does not distinguish "unsupported
routine" from "invalid domain/parameter" or another unmet prerequisite —
this rejects the reported layout only in the tested default/extended/
level-1-granted contexts; other security levels, payloads, or OEM ADB
mechanisms remain untested on CAN5. See
[SecurityAccess validation](../diagnostics/diagnosticsd_security_access.md#live-direct-can5-securityaccess-validation-2026-11-15)
and [MDI2 raw UDS bypass guide](../research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md).

## Keepalive-content bisection (2026-11-26)

The bench's long-standing "keepalive" (continuous replay of the harness profile's one
`0x529` frame, `PowerModeSelector=On`) was never shown to be a true keepalive — only
that it worked. It forces `evPowerModeOn` → `RunPropulsionAccessory`, which is an
unwanted side effect for an idle bench (Run should be a deliberate choice, not a
byproduct of staying awake). Live bench testing, cross-checked against VIP_APP firmware
RE (static decompiled-source analysis; see [the 0x529/0x53B rows](can_network.md#known-meaning-rows)
for the underlying bit mappings), established the actual mechanism and a working
alternative. All sleep/wake detection below is ADB-independent: the authoritative
signal is VIP UART text (`GoToSleep`/`CSM_Sleep`/`evt=evBACKGROUND_SLEEP_TIMEOUT` =
asleep; `SystemState=Propulsion`/`HmiInit`/`InfotainmentActive` = awake), with T1
(`eth0.5`) `rx_packets` deltas logged as a cross-check (it tracked UART closely: flat
≥60s shortly before each confirmed sleep).

Firmware model (static RE, V850 disassembly of the decompiled VIP_APP image): the
background-sleep timeout (`cal_background_sleep_timeout_sec`, calibration param 0x9b,
firmware default 10s, EEPROM-provisioned in the 0-1800s range, observed ~608-630s on
this unit) is a 16-slot software-timer-service dwell timer scoped to state `HMIInactive`
— it only runs while the HSM is in that state, and it is armed/reset only by HSM
transition actions (`ss_start_timer`, ~22 call sites, all inside the HSM action cluster),
never by raw CAN reception of any ID. `PowerModeSelector=On` (`evPowerModeOn`) escapes
`HMIInactive` into `RunPropulsionAccessory`; `InfotainmentActivationRequest=1`
(`evInfoActivationRequest`, CAN `0x53B` byte7 bit3) escapes it into `LocalInfotainment`/
`InfotainmentActive` instead, with no Run/Propulsion transition. No generic
`evComm*`/`evNetwork*`/`evKeepAlive*` input exists anywhere in the firmware.

Live trials (each run until a UART sleep marker or an 803s cap; recovery via the
dashboard's `startup` oneshot sequence + 40s + UART awake confirmation):

| Candidate | Content | Period | Result |
|---|---|---|---|
| Real keepalive (control) | `529` `38 82 00 00 00 00` (PowerModeSelector=On, HmiReady=1, Animation=1) | 0.32027s | NO_SLEEP (803s) |
| PowerModeSelector cleared | `529` `38 02 00 00 00 00` (HmiReady=1, Animation=1, PMS=0) | 0.32027s | SLEPT @ 613s |
| InfoActivationRequest toggled | `53B` alternating `...08`/`...00` | 90s half-cycle | SLEPT @ 311s — toggling to inactive is *worse* than nothing (fast fault/exit path) |
| Negative control (unmapped id) | `016` `00 00 00 00 00 00 00 00` | 0.32027s | SLEPT @ 608s — matches doing nothing, confirms no generic-traffic effect |
| InfoActivationRequest held static | `53B` `00 00 00 00 00 00 00 08` | 0.32027s | NO_SLEEP (803s), state stayed `InfotainmentActive`, never Run |
| same, interval bisection | `53B` `00 00 00 00 00 00 00 08` | 1s / 2s / 3s | NO_SLEEP (803s each) |
| same | `53B` `00 00 00 00 00 00 00 08` | 5s | SLEPT @ 673s |

Required repeat interval is bounded between 3s (confirmed working) and 5s (confirmed
failing); `tools/bench/bench_can/replay_can_keepalive.py` uses 2s for margin. The bench's
keepalive is now this verified `0x53B` static hold, not the old `0x529`-derived frame —
see that module's docstring for the implementation and `can0_radio.py`'s module
docstring for the one exception this makes to "frame bytes come from the pinned
harness profile."

## Power-on/wake-trigger minimal-sequence bisection (2026-11-26) — negative result

The bench's `startup` sequence (126 captured frames over a 40s window, IDs `145`/`457`/
`458`/`529`) reliably wakes the SoC from genuine deep sleep (`CSM_Sleep`/`SoC power level
0`), but had never been reduced — it is "a known-working captured recording," not an
understood minimal trigger. Firmware RE (static V850 analysis) established the wake
architecture is layered: (1) NM/bus-wake, ID-agnostic within the `0x100-0x1FF` range,
(2) SoC rail re-power + boot, gated on battery voltage with **no vehicle-CAN-state
precondition when cold** (CAN is a wake *factor*, not a requirement, for a genuinely cold
unit) via CSM/PLC events `evPNActivated`/`evStartupRequest`, (3) Run/Propulsion via
`evPowerModeOn` — an unwanted side effect for a plain wake, not part of the actual
power-on step.

Live bisection from **genuine, fully-settled sleep** (confirmed via UART `GoToSleep`→
`CSM_Sleep`→`evt=evBACKGROUND_SLEEP_TIMEOUT`, not the T1-flat heuristic alone), each
candidate watched up to 90s for wake evidence (`AnimationInit`/`HmiInactive`/`HmiInit`/
`SystemState=Propulsion`/`InfotainmentActive`/`SoC power level` climb):

| Candidate | Content | Result |
|---|---|---|
| `53B` edge alone (InfoActivationRequest 0→1, one-shot) | `00 00 00 00 00 00 00 08` | **NO_WAKE** (90s) |
| `145` prewake (3 frames) then `53B` edge | real captured `145` bytes `45 40 F2 80 00 00 00 0C` ×3, then `53B` edge | **NO_WAKE** (90s) |
| `145` repeated for 10s, no `53B` | same `145` bytes, 0.32s period, 31 frames | **NO_WAKE** (90s) |
| `145` one-shot only | single frame | **NO_WAKE** (90s) |
| `529` alone (PowerModeSelector edge, one-shot) | `00 80 00 00 00 00` | **NO_WAKE** (90s) |

All five single/few-frame candidates failed, including a bare `0x529` edge — surprising,
since `0x529` is what forces Run once already awake. **Sanity-checked, not assumed**: the
full 126-frame `startup` sequence was sent immediately after (same sleep state) and
confirmed both the adapter (TX counter +126, zero `tx_errors`) and the wake itself
(normal J6_CDD/RTC telemetry resumed) — ruling out an adapter/methodology problem as the
explanation. Conclusion: from a long, fully-settled sleep, the real wake trigger needs
either sustained/repeated presence beyond a single edge (the `startup` sequence sends
`529` 16 times across its own window, not once), multiple distinct frame types together,
or something the 126-frame capture carries that none of the five reduced candidates
isolated. **Not yet found; the blunt full-sequence replay remains the only known-working
wake mechanism.** Next candidate worth trying: a *held/repeated* `529` (not one-shot) from
genuine sleep, matching the same "hold, don't edge" lesson the keepalive bisection above
already established for `53B`.

## Gear/PRNDL: CAN-side send confirmed correct, no observable AAOS reaction found (2026-11-26)

Following the PRNDL bit-layout correction above, swept all documented raw values
(0,1,2,3,4) on `0x40B` (byte4 bits5-7) with `0x264`'s validity bit forced (byte3 bit6=1),
both while idle (`InfotainmentActive`) and while held in `Run`/`Propulsion` via a
sustained `0x529`, checking three independent observation channels:

1. **UART**: zero new lines of any kind during the sweep windows (confirmed the unit was
   genuinely awake and logging normally immediately before/after, so this is a real
   negative, not a sleep artifact) — consistent with the earlier finding that no
   PRNDL/gear/transmission module tag exists anywhere in the firmware's UART logging.
2. **Screen capture**: the visible display (`com.gm.homescreen` center-stack UI) shows no
   gear indicator; no separate cluster/gauge display was found on this unit (single
   physical display, 2400x960, one `HWC display 0`). `com.gm.cluster` is a running
   process but produces no observable output (logcat filtered to its PID: silent).
3. **UDS `C0xx` telemetry block** (raw-CAN5, `diagnostics/GM_CAN_UDS_REFERENCE.md` §13):
   read `C002,C003,C004,C005,C007,C008,C009,C00E,C00F` at gear raw=0 and raw=4 (held in
   `Run`). **Every value was byte-for-byte identical** between the two gear states except
   `C00F`, which drifted by 3 in its last data byte (`A4`→`A1`) — far more consistent with
   ordinary sensor/counter noise than a categorical gear encoding.

**Conclusion: the CAN send itself is confirmed correct** (matches the firmware's own
decode-function remap exactly, per the bit-layout correction), but no AAOS-visible,
UART-visible, or UDS-visible reaction to a gear change has been found despite exhausting
every readily-available observation channel on this bench. `vehicle_state.py`'s
`GEAR_POSITIONS` stays unverified scaffolding.

**Why UDS can never show this (firmware RE, 2026-11-26, confirms the negative result
architecturally, not just empirically):** the gear decode writes to SRAM `0xfebd3434`
(setter `FUN_0008c79c`, file `0x8c79c`, sole caller `0x4dd9c` — directly after the PRNDL
decode call). Its only reader is `FUN_0005c30e`, which packages it as an **internal
VIP→SoC HDLC IPC record (channel 4, record type `0x0C`, sub-id `0x05`)** — **not a CAN
frame at all**. An exhaustive reference search of the entire UDS/DCM config block
(file `0x1CC40–0x1D400`, the same region holding the 220-entry DID table) found **zero
pointers to this SRAM page** — no DID handler on either transport can reach it, by
construction. So the `C0xx` UDS sweep above was guaranteed to find nothing; this isn't a
transport-reachability gap, it's that gear never touches the diagnostic responder at all.

This also reframes the open question: the VIP *does* correctly decode and package gear
for the SoC (per the firmware trace) — whether AAOS actually consumes that IPC record is
now the real unknown, not whether the CAN-side decode works. Next test, if pursued: trace
the VIP↔SoC HDLC link itself (channel 4, type `0x0C`, sub `0x05`) while driving the
already-verified gear RX frames, watching for that specific record to change in lockstep
— this would show directly whether the gap is SoC-side (record changes, AAOS ignores it)
or still VIP-side (record never changes).

## Power-mode Accessory/Propulsion resolved via live CAN + UDS cross-check (2026-11-26)

The long-standing "raw 1 and 4 on CAN 0x284 are not independently confirmed" gap
(`platform/can_network.md`'s `284` row; `vehicle_state.py`'s `accessory`/`service`
scaffolding) is now closed for 1 and 4, using the newly-proven raw-CAN5 UDS DID `F085`
(`diagnostics/GM_CAN_UDS_REFERENCE.md` §13) as a cross-check against direct UART
evidence — not either signal alone.

Swept all four known raw values on `0x284` byte4 bits3-5 (`00`/`08`/`10`/`20` = raw
0/1/2/4), each held briefly then immediately read back via both channels:

| Raw | CAN 0x284 data | UART (`[SS_LOG]`) | UDS `F085` readback |
|---:|---|---|---|
| 0 | `00 00 00 00 00 00` | `evt=evPowerModeOff` → `SystemState=LocalInfotainment (0x8)` → `st=VehicleInitiated` | `00` |
| 1 | `00 00 00 00 08 00` | `evt=evPowerModeOn` → **`SystemState=Accessory (0x7)`** → `st=Accessory` | `01` |
| 2 | `00 00 00 00 10 00` | `evt=evPowerModeOn` → `SystemState=Run (0x5)` → `st=Run` | `02` |
| 4 | `00 00 00 00 20 00` | `evt=evPowerModeOn` → **`SystemState=Propulsion (0x6)`** → `st=Propulsion` | `04` |

The UART `SystemState=` line is the firmware naming its own state — independent of, and
stronger than, F085's readback (which merely proved earlier that raw values are retained
distinctly, not what they mean). **Result: raw 1 = Accessory (confirmed), raw 4 =
Propulsion (a distinct, newly-identified named state — not "Service Mode" as a historical
BCM `F085` note from a different bench/context had suggested; that note is now understood
to describe something else, since raw 2 here independently produces both `F085=02` and
UART `SystemState=Run`, directly contradicting a "02=Service Mode" reading for this
platform).** `vehicle_state.py`'s `POWER_MODES` now marks `off`/`run`/`accessory`/
`propulsion` verified; `service` remains the only unconfirmed raw value — no distinct
Service/Technician HMI state has been observed on any tested raw value.

## Display backlight: not a CAN/UDS-reachable mechanism (2026-11-26)

Observed live: physical display backlight off while the SoC was confirmed fully awake
(Android `mWakefulness=Awake`, `boot_completed=1`, actively compositing a normal,
live-updating UI per `screencap`) and the VIP's own last logged backlight command was
`on` — ruling out the VIP simply having turned it off. Firmware RE (two independent
passes, cross-checked against each other) found display-on/off is **not driven by any CAN
message or UDS DID at all**: it is a one-way **SoC→VIP IPC flag**
(`RequestDisplayOnOff`/"Display On/Off Request - True/False", written to VIP RAM
`0xFEBD3675`), consumed by the firmware's own `SS_SWC`/`BCTL` backlight state machine
(physical setter take 0/1/2 = off/on/local, logged as `[SS_SWC] backlight cfg = `). A
specific predicted trigger (`evRemoteReflashStatusDisplayOff`, a programming-session
display-off path) was checked directly against the real UART log and does **not** appear
anywhere in this bench's session history — ruled out, not confirmed.

**Conclusion: there is no CAN-side fix for this.** "Display off while SoC stays on" is an
Android/AAOS display-policy decision (most plausibly a plain screen-timeout, same as a
phone going to sleep) relayed to the VIP over IPC, not something any CAN keepalive
message — current or undiscovered — can address. If the display needs to stay lit through
a long bench session, the lever is Android-side (a wake lock, or disabling AAOS's
display/screen timeout), not CAN protocol work. This closes the "does the keepalive need
a paired display-on CAN message" question raised during this investigation: no such
message exists to find.

## ECUReset 11 01 over raw CAN5 (2026-11-27)

UDS ECUReset hardReset to ECU `0x80` as single ISO-TP frames on can0, request
`14DA80F1`, response `14DAF180` (`diagnostics/GM_CAN_UDS_REFERENCE.md` §13e). All times
AKST; UART ticks are the VIP console `[tick_ms]`.

| Time | Condition | Request | Response | VIP UART |
|---|---|---|---|---|
| 01:33:57 | VIP asleep (no frames on can0) | `02 11 01` | none; can0 went ERROR-PASSIVE (no ACK) | no output |
| 01:35:30 | VIP awake, default session | `02 11 01` | `03 7F 11 7F` (serviceNotSupportedInActiveSession) | ticks continued (040129 -> 051595): no reset |
| 01:35:58 | VIP awake | `02 10 03` then `02 11 01` | `06 50 03 00 64 01 F4`, then `02 51 01` | `[000119]` restart, banner `2B.175.1.5`, `BRR_RESET_REASON_VIP_SOFTWARE updated to 109`, `reset_factor = 0x1`, `Unique_Boot_Counteris :434` |

**After the reset the VIP goes back to sleep unless a startup window follows.**
- 01:43:20, reset via the dashboard API, keepalive frames still sent: boot counter 438,
  `[000150] st=BackgroundSleepTimeout`, `[010148] st=Shutdown` (9998 ms later; the same
  boot's calibration dump prints `cal_background_sleep_timeout_sec = 10`),
  `[021477] ... CSM_Sleep`, `Sending EnableShutdown`. Same `[021477] GoToSleep` after the
  01:35:58 reset.
- 01:45:06, reset then `startup-keepalive` started immediately: boot counter 440,
  `[001537] st=NormalInit`, `[009739] st=FullOperationStartup`, then `st=Propulsion`;
  still awake at `[041132]`, no `GoToSleep`.
- 01:48:35, dashboard Controls-tab button (reset + automatic `startup-keepalive`): boot
  counter 441, `[001738] st=NormalInit`, `[009706] st=FullOperationStartup`,
  `st=Propulsion`; still awake at `[042077]`.

Related: the 2026-11-27 01:22 keepalive A/B "Phase A" run (after a `vip-reset` sequence,
0x53B keepalive only) shows the same `[021477] GoToSleep` at 01:22:29, and the keepalive
journal reports `bus_rx=0` from its first run at 01:22:30. That run never had an awake
VIP and is not a valid keepalive result.

Unknown: the effect of `11 01` on the SoC/AAOS side (not observed: T1/ADB were down
during these runs), and why the boot counter advanced by more than one between runs
(wakes from sleep are a candidate, not checked).

## Open conflicts

None identified within this document's own ranges. Two cross-doc items are
flagged for the respective charter owners, not resolved here:

- `0x1F1` is treated throughout this log as an unvalidated/rejected
  Off/Run/Accessory candidate (see Isolating `0x1F1`/`0x145` and the
  explicit Off/Accessory tests above) — if any other platform doc asserts
  `0x1F1` as a validated power-mode ID, that is a direct contradiction with
  this log's negative results; owned by [CAN network](can_network.md).
- `boot_timing.md` may carry its own startup-timing narrative; this log's
  startup-reduction/animation/door timing tables (above) are the bench
  source data — check for drift if `boot_timing.md` restates these numbers.

## Ranges not migrated from the original (archived)

These original `can_network.md` ranges are not reproduced in the consolidated docs; they remain in the archived original, [archive/can_network_original.md](archive/can_network_original.md):

- L476-514: four-ID startup recipe (offsets, +7.892 / +21.199 s timings, restricted-boot procedure).
- L1046-1091: activation-request hold, host-sleep confound, 62.519 / 62.385 s results.

The independent loss audit of the original covered only L1-600; L600-2129 is covered by the writers' ledgers for `can_network` and `can_bench_experiments` (not preserved in this repository) but not by a second reader.
