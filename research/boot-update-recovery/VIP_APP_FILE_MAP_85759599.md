# VIP_APP File Map `85759599`

## Scope
Structural map of the Renesas RH850/F1K `VIP_APP` application firmware (Y175 pinned reference,
part `85759599`): memory layout, function-density distribution, named-function inventory,
largest functions, security/protocol-string cross-reference, entry-point trace, and the
address-level location of the CAN613/614 debug interface previously traced only by file-offset
citation in `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`. Pure reference — does not restate the
calibration-signature/SBA-ticket bypass mechanism itself (`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`,
`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`) or the RH850 hardware facts
(`../../hardware/module/vip_mcu.md`) — cites them by address instead of repeating them.

## Evidence legend
`[C]` confirmed via live Ghidra REST query against the project's existing (pre-analyzed) program
database · `[D]` confirmed via decompilation/disassembly of the function body · `[U]` unverified
/ open question. Unless noted, every address/size below is `[C]`, re-derived directly from
`evidence/ghidra-projects/85759599_rh850` (program `VIP_APP_85759599`), 2026-11-21.

## Related
`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` (the SBA-ticket RAM-exception finding this doc's
CAN613/614 section supports), `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` (SBA ticket, signature
verifier, ProtoKey chain — central reference), `VIP_BOOT_FILE_MAP_85056831.md` (the bootloader
that hands off to this image), `../../hardware/module/vip_mcu.md` (RH850 silicon memory map),
`../../platform/vip_ipc_ghs.md` (VIP role in the dual-processor architecture).

## Module identity
USB delivery-package file `85759599` (`…/Y175/USB_Files/85759599`), 1,934,214 B container;
unwrapped program `VIP_APP_85759599`: RH850:LE:32, processor variant `Zeekr-RH850`, image base
`0x00000000`, address range `0x00000000`–`0x001d8385`, **12,932 functions**, 7 external imports,
one marked entry point (`0x000e5924`), SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239` (matches the pinned reference
hash cited throughout `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` and
`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`).

## Memory layout
One flat `ram` segment, `0x00000000`–`0x001d8385` (1,934,214 B, rwx, fully initialized) — a raw
flash dump with no separate code/data partitioning at the Ghidra block level.

**Function density** (20 buckets, ~`0x179c6` B each): essentially all code lives in
`0x00000000`–`0x00103b81` (~12,880 functions, 99.6%), peaking around `0x0008daa4`–`0x000bce2f`.
Everything above ~`0x00104000` (the top 55% of the image, ~870 KB) is almost entirely
calibration/const data tables, with only ~50 tiny (≈68 B) stub functions. The firmware is
front-loaded code, back-loaded data.

## Named functions — none; this is a fresh-analysis baseline
**This program database contains zero human-renamed functions.** All 12,932 names are Ghidra
or compiler defaults (`FUN_<addr>`, `thunk_FUN_<addr>`, `switchD_<addr>::caseD_<n>`). Of those,
667 are non-`FUN_<addr>`-pattern but still auto-generated: 506 `thunk_FUN_*` (354 distinct
targets — compiler jump/veneer thunks), 154 `switchD_*::caseD_*`/`::default` (Ghidra
switch-table stubs), 7 `thunk_EXT_FUN_*` (veneers to the 7 external imports at
`0x0003e3c0`–`0x0003f47c`). **None of the semantic findings elsewhere in this corpus (the
signature verifier, the SBA-ticket chain, CAN613/614) were persisted as renames into this
`.gpr`** — whatever prior tracing located those functions by file offset was never written back
into the Ghidra project's symbol table. This doc's address citations below close part of that
gap but do not rename the functions in the project itself.

## Largest functions (top of the size distribution)
Median function size is 18 B; mean 44 B; 1,820 functions exceed 68 B; 523 are `is_thunk`.

| Size | Address |
|---|---|
| 7,932 B | `0x000f5f02` |
| 5,964 B | `0x00086a1c` |
| 4,580 B | `0x0001e556` |
| 3,470 B | `0x000211a4` (non-contiguous body) |
| 2,664 B | `0x000b7bc6` |
| 2,442 B | `0x0001076a` |
| 2,080 B | `0x0003d404` |
| 2,064 B | `0x0004758c` (non-contiguous body) |
| 1,856 B | `0x000fd916` |
| 1,834 B | `0x000a9416` |

(Full top-30 list available via `/functions` re-query against the live project; not reproduced
further here — see Provenance.)

## CAN613/614 debug interface — located and structurally confirmed

Resolves the file-offset citations in `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`
("dispatch at file offset `E5348` indexes the compiled table at runtime `73524`"; "its compiled
callback at `10DA5A` maps to file offset `E5FE0`") against this live program.

| Cited address | Status |
|---|---|
| `0x000e5348` | `[D]` Confirmed. `FUN_000e5348`, 64 B. Reads the command byte from `*param_2`, checks mode flag `DAT_febd5d2d`, and for values `< 0xC0` does a 4-byte function-pointer lookup at `uVar1*4 - 0x142a310` (RAM `0xFEBD5CF0`) and tail-calls through it. The XCP-style command dispatcher. |
| `0x000e5fe0`–`0x000e6050` | `[D]` This is the receive handler itself, not a separate "callback registration" as earlier cited. Filters the incoming CAN ID against a runtime-configured 16-bit word at RAM `0x710b0`, copies ≤8 payload bytes into RAM buffer `0xFEBEBAE4`, then at `0x0e604a` tail-calls the dispatcher above with that buffer. |
| `0x0010da5a` | **Retracted — stale citation.** This address sits inside an 888,976-byte run of unprogrammed flash (`0xFF`, spanning `0x0FF2F2`–`0x1D8381`). It has no connection to CAN613/614; a decompiler can mis-render `0xFFFFFFFF` as a plausible-looking instruction. |

**Serviced CAN ID:** the RX filter value at RAM `0x710b0` is runtime-provisioned (loaded from
`.data`, not a hard-coded literal in the static image) — the identification as `613` comes
from prior research's external correlation, not from a value visible in this trace. Two
adjacent RAM config words (`0x710b2`, `0x710b4`) feed a sibling leaf function and the TX/poll
handler `FUN_000e5f78` (operates on adjacent struct `0xFEBEBADC`, called from the cyclic
scheduler at `0x99080` — the response/"614" side). RX is callback-driven; TX is scheduler-polled.

**Still open:** the call that installs the RX handler's address into the CAN driver's RAM
callback table was not located — the handler's address (`0xe5fe0`) never appears as a static
literal anywhere in the image (checked: no `mov imm32`, no `movhi`/`movea` pair, no
`jarl`/`jr`), consistent with runtime installation via a `.data` ROM-to-RAM copy rather than
a static reference. This is what defeated Ghidra's auto-analysis and every xref-based search
this session — not a dead end, just unresolved by this method.

**Opcode semantics:** the dispatcher is real and structurally confirmed, but carries no
human-readable name in this project — the XCP opcode meanings (`SET_MTA`/`DOWNLOAD`/etc.)
exist only as prose cross-referenced against Vector's open-source XCPlite header, never
written back as Ghidra renames.

**Public translation-table sources** (for closing the opcode-semantics gap formally): AUTOSAR's
own XCP module specification is freely downloadable per release from autosar.org (e.g.
[AUTOSAR CP SWS XCP, R24-11](https://autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_XCP.pdf))
and describes how the AUTOSAR "Xcp" BSW module (consistent with the AUTOSAR SWC tagging already
observed in the VIP boot log) implements this protocol. The underlying wire protocol's
normative spec, ASAM MCD-1 XCP Part 2 (Protocol Layer), sits behind an ASAM
membership/purchase paywall — not freely public. [pyXCP](https://pyxcp.readthedocs.io/en/stable/README.html),
an open-source Python implementation targeting ASAM MCD-1 XCP compatibility, is a second
practical open-source reference to cross-check the existing XCPlite-derived command table
against.

### Can CAN613/614 produce a *persistent* (reboot-surviving) calibration change? (2026-11-22)

Earlier this session the interface was shown to forge SBA-ticket **RAM** state. The question
of whether it can reach **EEPROM** was traced via a whole-image direct-call graph (every
`jarl`/`jr disp22` decoded, r2-cross-checked).

**Single-command persistent write: no.** `[D]` Zero call sites inside the CAN613/614 module
(`0xe3800`–`0xe6300`) target any write-path trigger (the per-CalGroup wrappers at `0x558ba+`,
`FUN_0005540c`, `FUN_00096900`, or `FUN_00072d00`). The module's outbound calls go only to
generic helpers. 613/614 is purely an XCP-style arbitrary-RAM read/write (`DOWNLOAD`/`UPLOAD`,
the byte-copy loop at `0xe53c8`–`0xe53fc`). It cannot, by one command, persist a calibration.
*Caveat:* the `cmd<0xC0` handler table at `0xFEBD5CF0` is runtime-populated by a callback
registry, so the handler set can't be statically enumerated to a mathematical "none" — but
613/614 handlers take a raw CAN buffer (`param_2 = byte*`) whereas every write-path function
takes a CalGroup-ID/struct and is wired only to the calibration subsystem; they are not
plausible 613/614 handlers. Conclusion is decisive on the balance of evidence, not absolute.

**The real per-CalGroup EEPROM writer, located.** `[D]` `"[CAL] EEPROM Write Failure for
CalGroup-%d"` (15 copies) → 15 near-identical wrappers at `0x558ba`–`0x55e60` (+ a 16th at
`0x55fba`) → `FUN_0005540c` (retry ≤3, emits the failure log) → `FUN_0005bf68` →
`FUN_00072d00`. The writer does **not** bit-bang I2C — it writes a 2-byte job record
(`DAT_febe196c = 0x10` opcode, `DAT_febe196d = group`) and polls an NvM-engine-ready
event-flag (`FUN_00076272(8)`). Physical persistence is **asynchronous**: the job is queued
to the NvM/MemIf engine; a background task performs the actual medium access. No `0x50`/`0xA0`
slave-address constant or RIIC register write appears in this writer's call tree — the medium
layer is abstracted behind the job queue (opcode `0x10` at `0xFEBE196C`), giving no positive
I2C evidence from the writer itself (ties to the still-open "how the RAM shadow reaches the
physical M24C64" question, §`[SFLASH]` below).

**The durable route exists, via a background commit task.** `[U]` strong-inference, not
end-to-end-proven. A periodic scheduler task (`FUN_000a32ec` MainFunction → `FUN_000d218e` →
`FUN_00096900`) autonomously scans a per-CalGroup dirty/pending table (indices `0x49fb2`/
`0x49fb3`, records `0x49d3c`) and, for any group marked pending, calls **every** CalGroup
wrapper in sequence — submitting the write jobs. So the realistic durable mechanism is:
**use 613/614's RAM-write to (a) overwrite a CalGroup's RAM shadow with the custom value and
(b) set that group's dirty/pending flag — then the background task persists it to EEPROM on
its own, surviving reboot.** This needs **no SecurityAccess** and is *more direct* than the
UDS `$36`/`$37` path, **if** the dirty-flag/shadow bookkeeping can be forged consistently
(write gate in `FUN_0005540c`: `DAT_febd0bbc != 0 && group < 0xf && DAT_febd0bba != group`).
The dirty-flag forge was **not** proven end-to-end — flagged strong-inference. The
firmware-intended path (UDS SecurityAccess `$27` → `$2E`/`$31`/`$36`-`$37` → the same
per-CalGroup writer) also reaches EEPROM and **is** confirmed, but requires a real seed/key.

## Security / protocol strings — present, but not auto-cross-referenced

Searched `/strings` for: checksum(5), signature(2), SBA(27), Ticket(19), ProtoKey(15),
CONNECT(9), DOWNLOAD(3), UDS(2), seed(18), unlock(3). Zero hits for Harman, digest, XCP,
SET_MTA, UPLOAD, SecurityAccess (consistent with the XCP interface dispatching by raw numeric
opcode, not descriptive strings — string search cannot locate it, matching the CAN613/614
finding above).

**Critical caveat:** this firmware loads log/format strings indirectly (pointer-table driven).
Of 1,731 defined strings, only 21 carry a Ghidra-resolved `/xrefs_to` reference; almost none of
the security strings below bind to a consuming function automatically.

| Subsystem (log tag) | Representative string address(es) | Resolved function | Purpose |
|---|---|---|---|
| `[SBAT]` SBA ticket validation | `0x000065fa`–`0x00006c02` (27 strings) | none real | ECU_ID + app/key NBID (anti-rollback) version checks — the SBA-ticket mechanism exploited via the RAM-exception finding |
| `[PROTOKEY]` GMLAN seed/key caching | `0x0000af46`–`0x0000b212` (15) | none | Fetches/caches seeds from BCM over GMLAN, checksum-validates, gated by `Bis_Seed_Cache_Lock` |
| `[OTA_DIAG]` OTA seed request | `0x0000a4f2`–`0x0000a5fe` (5) | none | SecurityAccess seed request for OTA; includes a test-only seed override |
| `[AME_DIAG]` ICUSB unlock | `0x00007bbe`–`0x00007d16` | **`FUN_000b9e12`** (420 B) | Master/Unlock key provisioning + checksum for the ICUSB (USB) feature enable — the one subsystem here with a resolved consuming function |
| `[EXT_DIAG]`/`[J6_CDD]` calibration download | `0x0000269e`, `0x000135e2`, `0x0001362a` | none | UDS `RequestDownload` (`0x34`) calibration transfer to the SoC |
| `[J6_CDD]` ProtoKey forwarding | `0x0001658e`, `0x000165d2` | none | Forwards ProtoKey to the SoC over `SERIAL_IPC_PROTO_KEY_CHANNEL` |
| `[PLC]` DCM session-state signature | `0x0000918a`–`0x000091e6` | none | 32-bit "Signature" guarding persisted DCM/session state across resets |

## Entry point (`0x000e5924`)

**Not a cold-boot reset vector.** `[D]` 38 B (`0x000e5924`–`0x000e5949`), referenced from a
data pointer slot at `0x00000788` (low vector-table region). Disassembly shows it conditionally
adjusts a global accumulator at on-chip SRAM address `0xFEBD5D30` (outside the 0–`0x1d8385`
image — real silicon address space), stores a register through a pointer, then tail-calls
`thunk_FUN_000ede90`, which reads the RH850 **EIWR** (exception-level working register) and
decrements a context counter. This is an **exception/interrupt-level handler reached through
the vector table**, not startup code — Ghidra labels it "the" entry point only because it is the
sole exported symbol; the true reset vector sits elsewhere near address 0.

## CAN-received signal fate

Classification of what happens to a signal after CAN reception. Five outcomes exist; every
RX-table entry falls into exactly one.

| # | Outcome | Example ID(s) | Mechanism | Evidence |
|---|---|---|---|---|
| 1 | Not received | `0C1`, `0C9`, `0F1` | Absent from the 299-entry CanIf table and outside the `0x100`–`0x1FF` NM range | `[D]` |
| 2 | Received, NM-only | `1E5`, `1F1` | Matches the slot-1 range entry only; treated as bus-active/partial-network keep-alive; zero payload bytes copied | `[D]` |
| 3 | Received, decoded, consumed locally | `4DA` (door), `4BE` (valet), `40B`/`264` (gear) | Reaches `Com_ReceiveSignal` (`FUN_000c8f6a`) via one of its 162 Ghidra-resolved callers; drives the SystemState HSM or a dedicated SRAM flag | `[D]` |
| 4 | Received, decoded, pushed to SoC | Gear/PRNDL (channel 4), accel/gyro/temp/wheeltick (`FUN_0009902e`) | A dedicated function reads the decoded SRAM value and transmits it over one fixed IPC channel | `[D]` |
| 5 | Received, decoded, never read by anything | `4D8`, `49B`, `561`, `492`, `4D4` (~250 signals total) | Decoded into shadow storage at `0xfebdaae2 + signal-offset`; zero consumers found, no SoC pull path exists (below) | `[D]` |

Outcome 5 is the largest bucket by signal count. `[U]` Working explanation: this is one
firmware image shared across multiple vehicle trims/configurations (consistent with the
CalDef/calibration architecture documented elsewhere in this corpus); these signals likely
apply to a trim other than this build. Not verified against another trim's firmware.

**Outcome is per-signal, not per-ID — re-verified 2026-11-22.** A whole-image scan (1,069
distinct consumed signal IDs across 1,309 consumer sites) re-confirmed 7 of the 9 richest
unnamed IDs (`492`, `495`, `496`, `497`, `49A`, `49B`, `561`) as fully outcome-5 — not one of
their 42–64 signals is consumed anywhere. Two corrections: **`4D8`** is mixed — signal
`0xB05` (its door-position bit, already known) is genuinely outcome-3; its other 48 signals
are outcome-5. **`4D4`** has one signal (`0x15D`) read into a local variable and immediately
discarded without use — a read-and-drop, functionally outcome-5 but not literally
"never read."

### No SoC pull-access to the Com shadow buffer

Checked whether the SoC reads outcome-5 signals on demand instead of VIP pushing them.

| Check | Result | Evidence |
|---|---|---|
| Callers of `Com_ReceiveSignal` (1,309 call sites) | 162 resolved to a Ghidra function; 1,147 unattributed (`from_function: null`). One resolved caller, `FUN_00066ce4` (reads signals `0xDA0`/`0xDA1`), sits inside the `0x56e00`–`0x84000` IPC-code range. Traced fully: it has **zero reachable callers** anywhere in the image (confirmed by scanning every branch and every 32-bit pointer word for its address and its two entry-wrapper addresses — none found, unlike sibling stubs in the same code region which are genuinely called). Dead/vestigial code. Its internal shape, if it were live, is one-way push (read Com buffer → SRAM → mailbox notify), not request/response. | `[D]` |
| Incoming IPC dispatch (J6_CDD control channel) | Fixed command switch (display, animation, valet, power-level, RTC, cal-download); unknown IDs rejected and logged | `[D]` |
| Channel-7 UDS/DID proxy | Exists, but serves only a fixed identity/calibration DID list from NvM/EEPROM — not the Com shadow buffer | `[D]` |
| UDS `ReadMemoryByAddress` (service `0x23`) | Not present anywhere in this firmware — no string, no handler | `[D]` |

**Conclusion `[D]`:** outcome-5 signals are write-only; no read path exists in either
direction, for all 1,309 `Com_ReceiveSignal` call sites.

## SystemState HSM and the audio-cue mechanism

`0xfebd22e8` is a QP-framework hierarchical state machine ("SystemState"), dispatched
synchronously by `FUN_00085cfe` (run-to-completion, not a queue). `[D]` Its vocabulary (~115
`ev*` strings; states include `HmiInactive`, `Propulsion`, `Accessory`, `LocalInfotainment`,
`LocalValet`, `TheftLocked`, `RemoteVehicleProgramming`) is power/lifecycle/activation only
— no chime event exists in it. Door open/close (`4DA` → `FUN_0006f48c`) posts into this
machine as a wake/activation input, not a chime signal.

| Fact | Status |
|---|---|
| No chime/tone/beep string anywhere in the image | `[D]` |
| `PlayAudioCue` (`FUN_00089b3e`, thunk `0x50fbe`) has exactly 3 call sites, hardcoded cue IDs 2/3/4 | `[D]` |
| Seatbelt/turn-signal chime support does not exist in this firmware | `[D]` |
| Every cue is sent as a 2-byte IPC message (opcode `0x42`, channel 2) to the SoC — VIP never renders audio | `[D]` |
| VIP's direct audio-hardware authority is the amplifier (TAS6424L: mute/enable/routing) plus relaying GMLAN chime-config fields (`ChimSnkLvl`, speaker position) | `[D]` |

**HSM structure fully recovered (2026-11-22).** `0xfebd22e8` is statically initialized from
ROM at file `0xf98ee` (242-state table at `0x11232`, 28 B/entry; 12 B transition records;
a 302-entry array at `0xF9916` cross-validated against known state names — state 125
checks out as `HmiInactive`). **The earlier premise was wrong: no state in this firmware
uses `PlayAudioCue` as an entry or exit action — all three cue sites are attached to
specific *transition* records instead,** confirmed by checking every state's entry/exit
fields across all 5 HSM instances in the image.

**`[CONFLICT]`, flagged rather than resolved:** a separate same-day pass (idle-timer trace,
below) read this same `0xF9916` region and reports it as an array of 32-bit values pointing
into code (`0x36xxx`–`0x38xxx`), *not* a name table, and could not use it to resolve an
event number. Both readings used independent `r2` ground-truth; this doc does not have a
third pass to adjudicate. Treat the door/chime HSM-structure conclusions above as
cross-validated by an independent behavioral check (state 125 matching the known
`HmiInactive` name) and therefore higher-confidence than the raw table-format claim, but
the `0xF9916` byte-layout question itself is open until re-checked.

**Door event, resolved exactly:** from the normal resting state `HmiInactive` (state 125):
- `evDriverDoorOpen` (15) → **internal transition** (no state change), action `0x705ac`
  (sets a wake flag) — **plays no cue**.
- `evDriverDoorClosed` (14) → internal transition, action `0x7053a` = **`PlayAudioCue(2)`**,
  guarded by `0x70454`.

So: **door-open is silent; door-close plays cue 2.** The other three cue call sites (3 and
4) are on HMI wake/sleep-animation-junction transitions unrelated to the door
(`Start`/`AnimationInit` entry junctions → cue 3/2; `LocalInfotainment`/`ValetMode`/
`LocalPhone` exit-to-inactive junctions → cue 4) — none are tied to shutdown/suspend
specifically, correcting the earlier "power-transition state" description.

`[U]` If chimes survive an AAOS/Android reboot as documented elsewhere in this corpus, the
most consistent explanation is a GHS-hosted audio domain outside the Android VM rendering
the cue. **Independently confirmed** by tracing the GHS HostOS binary (`85098662`,
2026-11-22): a standalone `Chimes_InitialTask` holds 71 embedded PCM clips, drives the
Dirana-3 DSP, and explicitly blocks the Android guest's own amp/DSP control messages — the
concrete mechanism. See `GHS_FILE_MAP_85098662.md` for the GHS-side trace (channel/opcode
match to VIP's `channel 2`/`0x42` not byte-confirmed on either side — both independent
traces hit the same specific gap).

## SoC power-on and the ELK boot-mode trigger

Question: does vehicle CAN state (gear, Park, ignition) gate SoC power-on or the
CAN-reachable ELK/Fastboot trigger (`../boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`'s
cold-entry selector trace)? **No, for both.**

| Claim | Status | Evidence |
|---|---|---|
| Gear SRAM value has exactly one consumer (channel-4 SoC transmitter) | `[D]` | No power-sequencing, shutdown, reset-reason, or ELK function reads it |
| SoC power-on preconditions are wake-factor/power-button/battery-SOC/EEPROM-timer-driven (`cal_startup_delay_wait_timeout_msec`, `cal_startup_fault_timeout_sec`, `cal_str_mode_soc_min_threshold_1..3`) | `[D]` | 2026-11-17 cold-power bench test: SoC reached `evSoC_StartupComplete` (~5.5s) with zero CAN frames on the bus |
| ELK trigger reachable only via UDS RoutineControl `31 01 F0 00 81 80 03` on the diagnostic interface | `[D]` | Not one of the 299 application RX IDs; absent from the 221-entry I/O-control DID table |
| ELK dispatcher `FUN_000571e8` enforces diagnostic SecurityAccess + a separate app-security SRAM word (`_DAT_febd0cf8`) — no vehicle-state check | `[D]` | Scans 131 descriptors at `DAT_0002e700`, matches selector `0x8180` |
| On success: `FUN_000757d4` → `FUN_00075794` sends IPC byte `0xE0` to the SoC on channel 12, then VIP controlled-reset, steering SoC boot into `kernelflinger`/ELK | `[C]` live-tested | Forcing the app-security word produced `Diag Elk Reboot Req` → `Elk Reboot Response 0` → controlled reset → SoC re-enumerated in `kernelflinger-07.02-userdebug`/ELK |

**SoC power rail, resolved.** VIP asserts SoC power via direct RH850 GPIO/port-register
writes — **not** a PMIC/I2C transaction. Register base `0xFFC10100`+4×port (PSRn,
set/reset) / `0xFFC10200`+4×port (PPRn, read). A two-stage sequence: `0x71c04` gates purely
on battery-voltage ADC (~9–16 V window, no vehicle-CAN-state check, consistent with the row
above), then `0x71d64` asserts the SoC-side rails and sets flag `0xFEBD2A04`. The
`"[Power]MCU power On and resume Soc"` log string belongs only to the **S2R-resume** pulse
(`0x71ce6`), not the cold-boot path — a prior draft of this doc over-attributed it. `[D]`

**No VIP influence over the SoC's own platform firmware (IFWI/BIOS/ME) — actively searched,
not just absent from other passes (2026-11-22).** VIP's only SoC-facing actions are power/
reset GPIO gating, the `SoCReqType` reset-reason record (which, per a later pass, governs
*VIP's own* next boot stage — shutdown/controlled-reset/VIP-bootloader-reentry/over-temp —
not the SoC's boot target; see `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`'s "Boot Reason
Record" section), and the ELK/`0xE0` trigger above — none write into a storage medium the
Atom's own firmware loads from. Specifically ruled out: zero hits across
both VIP_APP and VIP_BOOT for `IFWI`/`BIOS`/`UEFI`/`capsule`/`ME_RST`/`PLTRST`/`RTCRST`/
`flash descriptor`; no eSPI/LPC controller — the only SPI master found (`CSIH`,
`0xFFCA`/`0xFFCB`) drives VIP's own `[SFLASH]` serial-NOR chip and a Marvell/"Leo"
automotive Ethernet switch, neither shared with the SoC; no GPIO pin beyond the documented
power/reset/amp/Ethernet-switch set resembles a BIOS-recovery or ME-disable strap; the
Remote Reflash (SWDL) and UDS 0x34/0x36/0x37 download paths move **VIP calibration data**,
never an SoC firmware image. Notably, the dependency runs the other way: VIP_BOOT's own
flash-update strings show *the SoC drives VIP's bootloader update*
(`"Waiting for the SOC to intiate a reset to complete the bootloader update"`), not the
reverse. VIP's profile here matches a companion/gateway MCU on a UART/CAN link; it has
neither the code nor the hardware interface of an EC/BMC-class supervisor with access to a
host's BIOS flash.

### `[SFLASH]` — VIP's own serial-NOR, pinned down, then corrected against physical ground truth (2026-11-22)

A complete generic SPI-NOR driver on CSIH channel 6 (file `0x6d490`–`0x6d930`; the string
base-delta `K=0x27A7A`, used throughout this doc, had to be independently re-derived here —
Ghidra's own auto-analysis of this region is wrong and `/xrefs_to` was non-functional for
it): `[D]` WREN `0x06`, RDSR `0x05`, WRSR `0x01`, 4 KB sub-sector erase `0x20`, 256 B page
program `0x02`, 256 B page read `0x03`, 24-bit addressing (≤16 MB), 5000-retry busy-poll —
a textbook generic SPI-NOR chip, not a proprietary device. The shared CSIH bus's other
channels are the Marvell/Leo Ethernet switch (CS4/5) — confirmed **not** another storage
device (16-bit register-swap traffic, no NOR command set).

**Retraction (2026-11-22), driven by physical ground truth:** the owner confirmed there is
only **one** TSSOP-8 storage IC on the real board, sitting beside the VIP — the ST M24C64
**I2C** EEPROM already fully mapped in `../../hardware/module/eeprom.md`. There is no second
discrete storage chip. A dedicated reconciliation pass resolved what this means for the
`[SFLASH]` driver below:

- The driver's "shared NvM primitives" claim was a **misreading of a device-agnostic admin
  layer**. `FUN_000e1258`/`FUN_000e13b2`/`FUN_000e040e` only manipulate RAM block-status
  tables — they never call into the SPI-NOR driver's actual transfer functions. The real
  cal write path is `FUN_000558ba` → `FUN_000e13b2`; the real cal read path is
  `FUN_0004f6ba` → `FUN_000555b0`, both RAM-shadow-only. **That RAM shadow is backed by the
  M24C64 I2C EEPROM** (per `hardware/module/eeprom.md`'s physically-confirmed byte-offset
  map), not by this SPI driver.
- **CSIH ≠ I2C and cannot address the M24C64 at all** — CSIH is clocked SPI (its opcode set
  WREN/RDSR/WRSR/erase/program/read is a SPI-NOR command set, electrically incompatible
  with an I2C part). The on-chip RIIC (I2C) peripheral (`0xFFCA0000`) is confirmed
  **disabled** — one reset-only write at init, its register table otherwise completely
  unreferenced. So nothing in this image's I2C path explains the EEPROM link either; see
  below.
- The SPI-NOR driver itself is real, compiled-in code (not dead — its handler sits in a
  live, populated dispatch table alongside other live NvM/SWC handlers, and CSIH is
  genuinely brought up and used for the Marvell/Leo Ethernet switch) — but on **this board
  variant** it has no populated storage chip to talk to. Best explanation: a generic
  MemStack backend compiled in for a hardware configuration this board doesn't use.

**So:** calibrations/SBAT/BootCounter/PIM are confirmed to live on the M24C64 (consistent
with `hardware/module/eeprom.md`'s offset map), reached through the RAM-shadow CalGroup/NvM
layer described above — **not** through this `[SFLASH]` SPI-NOR driver, which is real code
with no live storage target on this hardware.

**New genuine open question, not yet resolved by any pass:** *how* the RAM shadow actually
reaches the physical M24C64 — i.e. the last-mile bus — is still unknown. No bit-banged I2C
transaction to the EEPROM's slave address was found (the one confirmed bit-banged I2C in
this image targets a different, unrelated `[ELMOS_IC]` sensor/lighting device). Two
candidates, neither confirmed: a GPIO-bit-banged I2C path hidden in an undisassembled
region (same class of gap as elsewhere in this image), or the calibration data is actually
proxied through the SoC over the VIP↔SoC IPC link (`TrySendCalUpdateData`/`CalUpdateStatus
from J6` strings confirm calibration *updates* do arrive this way) with the SoC acting as
the real I2C master. This doesn't affect the resolution above — it's a "how," not a
"where" — but it's worth a dedicated pass if the mechanism matters.

## Idle/sleep timer system

Network Management was tested as the source of an idle-to-sleep timer and ruled out.

| Claim | Status | Evidence |
|---|---|---|
| NM module (`FUN_0009b03a`, `FUN_000c2a06`–`FUN_000c37f2`, 38 functions) has no timer | `[D]` | Fully decompiled; only decrement found is an unrelated loop index; globals `_DAT_febd56a0/a4/a8` hold only state codes 0–5 |

The real mechanism is a generic timer service: 16 numbered slots in three parallel RAM
arrays — deadline `u32 @ 0xFEBDD978[id*4]`, configured duration `u32 @ 0xFEBD0A88[id*4]`
(an NvM/cal RAM mirror — never written by any instruction in the static image, populated
by a runtime block copy; live values can't be read from this image), active flag
`u8 @ 0xFEBDD9B4[id]`. Primitives: `FUN_000514ba` Start, `FUN_000514a4` Stop, `FUN_000514de`
Restart (Stop then Start). **Restart has exactly 5 call sites in the whole image** — slots
**2, 3, 11, 12, 13** only. Slot 5 (below) uses Start only, with no Restart equivalent.

**Timer slot 2 = "local infotainment activity."**

| Claim | Status | Evidence |
|---|---|---|
| Reset action: `mov 2,r6; jarl FUN_000514de` at `0x7058a`/`0x7058c` (`0x70576` is the preceding log-setup instruction, not the restart itself) | `[C]` ground-truth disasm (`r2`, `v850`, raw image), address corrected 2026-11-22 | Confirmed unconditional — no branch between the preceding log call and the restart |
| Reset is triggered by CAN `0x53B` (`InfotainmentActivationRequest`) | `[C]` ground-truth disasm | Signal 0x84B consumer at `0x5051e`/`0x6f64a` |
| The consumer dispatches an event **only on value change** — not on every frame reception | `[C]` ground-truth disasm | `FUN_0006f64a`: compares new value against cached byte at `0xFEBE0924+2`; returns immediately with no dispatch if unchanged |
| On change, dispatches event 19 (`evInfoActivationRequest`) or 20 (`...Clear`) into the SystemState HSM (`0xfebd22e8`) | `[C]` ground-truth disasm | `cmov z,20,19,r7` then `jr FUN_00085cfe` |

**"Event 21 / `evInfotainmentActivity`" retracted (2026-11-22) — no such enum exists.** A
full string sweep confirms the real infotainment event names are `evINFOTAINMENT_ACTIVITY_TIMEOUT`,
`evInfoActivationRequest`, `evUSER_INITIATED_LOCAL_INFOTAINMENT_TIMEOUT` — there is no
`evInfotainmentActivity`. Signal 21 does exist, but it targets a *different* HSM instance
(`0xfebd2184`) via a UI-notification path with no Start/Stop/Restart call anywhere on it.
The slot-2 restart is driven by events 19/20 only, as above.

**Practical consequence (proven):** re-sending `0x53B` with an unchanged payload does
nothing after the first frame — the consumer requires an actual value transition, not
repetition. This rules out a "constant retransmission" keepalive model for this signal.

**Slot-2 cal-loader citation retracted.** `0x4fc40`–`0x4fc94` is **not** slot-2's duration
loader — that block belongs to a different loader (`FUN_0004f564`, base `0xFEBD0A0C`) whose
writes land at `0xFEBD0A0C`–`0xFEBD0A6B`, below the timer-duration array entirely (confirmed:
`0xFEBD0A50` is independently used by unrelated date/alarm code). The "default 30s, range
0–120s" figure was a misidentification of a different config value (param-ID 170, writing
`0xFEBD0A44`) — **withdrawn, not slot-2's duration.** Slot-2's real default/range is
unresolved (same NvM-mirror problem as all other slots).

## Timer slot 5 — "OffModeActive," the real idle-to-sleep candidate (2026-11-22)

Started (not restarted) at `0x70600` (`mov 5,r6; jarl FUN_000514ba`), reached by function
pointer from the statechart action table — `FUN_000705f4`, the `"StartOffModeActiveTimer"`
action. `[C]` ground-truth disasm.

Two distinct off-mode-active calibrations exist, governing this or a closely related slot:

| Calibration (exact ROM string) | Unit | Expiry event |
|---|---|---|
| `cal_offmode_active_timeout_sec` | seconds | `evOFF_MODE_ACTIVE_TIMEOUT` |
| `cal_master_offmode_active_timeout_min` | **minutes** | `evMASTER_OFF_MODE_ACTIVE_TIMEOUT` |

The minutes-unit calibration is the best structural fit for an ~11-minute idle-to-sleep
timer — an 11-minute period is naturally a minutes-scale value, not a seconds-scale one.
`[U]`, plausible, not proven.

**Exact default value: not statically recoverable from this image**, for three independent
reasons, each confirmed: (1) the duration array is an NvM/cal RAM mirror with no writer
anywhere in the static image; (2) the human-readable cal-name strings are never referenced
by any pointer in code — this firmware uses a tokenized/binary logging format, and the
strings exist only for a host-side log decoder, not for firmware string-xref tracing; (3)
the tick-rate/unit-conversion handler was not located, so even a raw stored value couldn't
be converted to real time with confidence. Getting the actual default would need the
EEPROM/NvM default block, a host-side log dictionary, or a live RAM read at `0xFEBD0A9C`
(slot 5's duration slot) on a running unit — not achievable from static analysis alone.

**Expiry chain for slot 2 (proven to the SoC shutdown request):** timeout → event 22
(`evINFOTAINMENT_ACTIVITY_TIMEOUT`) → `FUN_0006fc66` → `FUN_000513de(3)` (`"HMIInactive:
Requesting Shutdown"` or `"...Requesting S2R"` if under the max-suspend-hours cal) →
`SoCReqType` write at `0xFEBF0BC0` (`FUN_00074452`/`FUN_000741a4`/`FUN_00080ae4`). `[D]`
Slot 5's own expiry chain was not individually traced this pass.

**Method note, with a flagged conflict:** stored firmware pointers in log/event tables are
generally link addresses = file-offset + `0x27A7A` (this offset itself is confirmed
correct and used successfully throughout this doc). Whether the specific region at file
`0xF9916` is a usable flat event/state name table is **disputed between two independent
passes this session** — see the note in "SystemState HSM and the audio-cue mechanism"
above; not re-resolved here.

## VIP↔SoC communication map

Transport: HDLC over UART `/dev/ttyS1`, 21 logical channels (index `0`–`0x14`), each a 24 B
entry in the RAM channel table (`*_DAT_febd0cf0`). TX `FUN_000570fe(channel,buf,len)` →
`FUN_000837fc`; RX `FUN_0008374a`, wrapped by `FUN_00056e8c`/`FUN_00057138`. **Both
primitives are SoC-facing (IPC), not vehicle-CAN** — `FUN_000570fe` writes the same
per-channel HDLC endpoints the RX path reads; there is no path from it to the vehicle bus.
Channel-up gate `FUN_00076272(ch)` asserts `ch ≤ 0x14` and ANDs per-channel status bytes at
`0xfebd3000`/`0xfebd3018`. Confirmed on the AAOS side: `IPCServer` (`/dev/ipc/ipc0`–`20`,
`ipc4.cfg`, protocol v16) demultiplexes this same link; the Vehicle HAL reads `/dev/ipc/ipc3`
directly.

### VIP → SoC (push), by channel — 88 TX call sites traced

| Ch | Traffic | Mechanism |
|---|---|---|
| 2 | Audio/HMI: `PlayAudioCue` (opcode `0x42`) + broader HMI-request scheduler | `FUN_0004bec8` periodic scheduler, bitmap `0xfebdd6f4` |
| 3, 8, 9, 11, 13, 14, 15 | Small state flags, a 17 B state snapshot, a heartbeat (`0x85`), multi-opcode commands | Various single-purpose senders |
| 4 | Sensor telemetry: accel/gyro/temp/wheeltick, gear/PRNDL (`0x0C`/`0x05`) | Cyclic task `FUN_0009902e` |
| 5, 10 | Additional cyclic telemetry (indexed records) | `FUN_000730e2`+ (ch5); `0x56xxx` cluster, scheduler `0x99378` (ch10) |
| **7** | **Vehicle-signal/status broadcast — 22 distinct message IDs**, largest single channel | `0x74c…0x762` cluster (`[PLC]`-adjacent); best numeric candidate for the OBD/diagnostic proxy, not proven |
| 12 | Lifecycle/power/boot control: ELK-reboot (`0xE0`), two power-state opcodes (`0xA8`, `0x3D`) | `FUN_00075794`, `FUN_0005c59e`, `FUN_0007d0b8` |
| 0, 1, 6, 16–20 | No push sender found — RX-only or reserved | — |

### SoC → VIP (commands), primarily the J6_CDD control channel — 35 named handlers catalogued

The dispatcher lives in a Ghidra-unanalyzed region (`0x73000`–`0x77000`); handler names come
from the (pointer-free, catalog-only) log-string table, not from a resolved jump table —
exact numeric message IDs were not recovered. Unknown IDs/SIDs are logged and dropped
(`"RECEIVED UNSUPPORTED SID"`, `"unknown custom request... not processed"`) — a fixed
allow-list, not a generic command interpreter.

**[U] Adjacent raw disassembly, unattributed.** A standalone RH850 disassembly snippet exists at
[`evidence/decompiled/vip_app_85759599_disasm_0x77e20.txt`](../../evidence/decompiled/vip_app_85759599_disasm_0x77e20.txt),
addressing `0x77e20`–`~0x77e5e` — just past this dispatcher region's cited upper bound
(`0x77000`). Structurally it reads as an interrupt/exception-vector-stub cluster: the first 11
words are a jump table, six of them (`jr 0x1fffecce`, every other entry) point at an identical
target consistent with a shared "unhandled vector" default stub, while the other five point at
four distinct handlers spaced an even `0x22` bytes apart (`0x4e92`/`0x4eb4`/`0x4ed6`/`0x4ef8`),
consistent with a small table of fixed-size per-source interrupt entry stubs. This is a
structural read of the raw bytes only — it has **not** been matched to a named function, nor
confirmed to be inside/adjacent to the J6_CDD dispatcher specifically. Verification needs the
live `85759599_rh850` Ghidra project (`get_function_by_address`/`disassemble_function` at
`0x77e20`); attempted during this pass and blocked twice over — the checked-in project was
saved by Ghidra 12.2 and this machine only has 12.1.2 installed, and the Ghidra-12.2 host
(`macpro`, reachable over WireGuard) was unreachable at the time. Follow up with whoever next
has matching-version Ghidra access to either project.

| Category | Commands | Effect |
|---|---|---|
| Power/lifecycle | `RequestSuspendToRAMFeature`, `RequestDisplayOnOff`, `RequestOffModeActivation`, `ShutdownRequest6`, `ReportPowerLevel` | SystemState HSM events, S2R/power-level flags |
| HMI/display | `ReportAnimationState`, `ReportCenterStackHMIReady`, `LVDSPowerButtonPress`, `ReportDevScreenButtonPress` | HSM events, display/LVDS control |
| Valet/calibration | `ReportValetStateChange`, `ReportCalibrationState`, `Calibration Available Notice` | State flags into HSM |
| Audio/display hardware | AMP mute/unmute, Leo-switch control | Direct hardware control (amp, Leo display switch) |
| RTC | Set/Cancel Alarm, Set RTC time | RTC_CDD programming |
| Remote reflash | `RemoteReflashStatusDisplayOn/UpdateStatus/ProgrammingCPID_*/ReflashReminderStatus`, `ScheduledUpdateInactive` | Posts `evRemoteReflashProgramming*` to HSM |
| Diagnostics/health | `SendLastBootReason`, `SOH6` (SoC heartbeat — loss triggers reset reason `SoC_LOSS_OF_SOH`) | Status reply / reset-reason recording |
| **Network state** | `ControlPartialNetwork` (`IPC_ID_ControlPartialNetowrk`) | **Activates/deactivates a CAN partial network** — the one command with real vehicle-bus effect |

Separately, a UDS/DID diagnostic proxy (channel 7, fixed NvM DID list) and the ELK boot
trigger (UDS RoutineControl only, not a direct IPC command) are confirmed elsewhere in this
doc.

### Can AAOS reach anything CAN-bus/safety-adjacent through this surface?

**No arbitrary CAN injection; yes to a narrow, mediated set of network-state effects.**

- The vehicle CAN controller (RS-CANFD, register base `0xffd00000`) is driven by the
  AUTOSAR CanSM/Nm stack, never directly addressable from an IPC payload.
- `ControlPartialNetwork` can start/stop a CAN partial network (NM keep-alive traffic,
  bus-sleep gating) — a real, but narrow and mediated, vehicle-network effect.
- Power-level/shutdown/S2R commands drive CanSM controller mode and NM timing
  (`"NM Active after Shutdown Sent to SoC with CANSMMode"`) — AAOS can influence bus
  wake/sleep, not bus content.
- `[J6_CDD]` does transmit onto CAN (`"Transmit CAN ID: 0x%X"`), but only a fixed,
  compile-time signal set via Com/PduR — no evidence any IPC message supplies the CAN ID
  or payload.
- The arbitrary-command dispatcher (`FUN_000e5348`, the CAN613/614 interface) is fed by a
  CAN-RX callback and gated behind UDS RoutineControl/SecurityAccess — it is **not**
  reachable from the normal AAOS IPC control channel.

**Net:** the AAOS→VIP surface is a fixed, allow-listed command set. Its effects are
VIP-internal state, SoC-facing replies, and local hardware (display, amp, Leo switch, RTC,
power) — plus one narrow, mediated vehicle-network control (`ControlPartialNetwork`). No
path from AAOS reaches arbitrary CAN transmission or the diagnostic command dispatcher.

## Provenance
Live Ghidra REST queries (`/functions`, `/function`, `/decompile_function`,
`/disassemble_function`, `/strings`, `/xrefs_to`, `/segments`, `/read_memory`) against a
headless-loaded instance of the existing `evidence/ghidra-projects/85759599_rh850` project
(program `VIP_APP_85759599`), 2026-11-21. The full raw function listing (12,932 rows) and named/
largest-function dumps were produced during this pass but are not persisted in this repo
(scratch/temporary files only); re-run the same REST queries against the Ghidra project for a
fresh export if needed — the project itself is the source of truth for exhaustive listings.
