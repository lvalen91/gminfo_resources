# CAN network message dictionary

Message/signal reference for the gminfo3.7 A11/OPU bench CAN5 bus: verified bit-level
field decodes, firmware RX/TX configuration, the full harness/radio ID inventories, and
comparison against public GM DBC sources. This document is the dictionary only — bench
experiment narrative (adapter timing, ADB-enable sweeps, calibration/LTZ trial logs,
animation/door-sequence test write-ups) lives in
[`can_bench_experiments.md`](can_bench_experiments.md); vehicle-wide topology (ECU
census, gateway addressing, diagnostic transport) lives in
[`vehicle_network.md`](vehicle_network.md).

## CAN mechanism (brief)

The A11 radio does not put CAN frames directly on the SoC. The VIP MCU (RH850/F1K)
is the radio's CAN node — CSM, diagnostic ECU address `0x80` — and bridges the vehicle
CAN bus to the Intel SoC over an internal HDLC IPC link; Android itself never sees raw
CAN frames ([`ethernet_networking.md`](ethernet_networking.md)#can-bus, [`vehicle_network.md`](vehicle_network.md)
join points). All IDs below are **standard 11-bit** data IDs on this bench's isolated
CAN5 segment unless marked extended (29-bit, written `0x14xxxxxx`/`0x10xxxxxx` style).
DLC is the byte count. Byte positions in field tables are zero-based (`b0` = first
transmitted byte) and bit numbers are from each byte's least-significant bit, preserving
wire transmission order — this is **not** a claim about Motorola/Intel (`@0`/`@1`) DBC
bit-numbering, which is noted separately where external sources are compared.

## Evidence and capture notation

`B:n` = record line `n` in the retained connected/startup capture `can5.jsonl`; `H:n` =
line `n` in the isolated-harness capture `can5-harness-only.jsonl`. These are local
capture-file roles, not machine paths; raw captures/payloads are not repository
attachments. **H** = observed from the isolated harness; **R** = received from the radio
with the harness MCU disconnected. All 40 originally provisional radio IDs were
subsequently confirmed in `radio-only-rx.can.jsonl` (TX echoes excluded; no missing or
extra IDs). `radio-only-rx.uart.jsonl` supplies Mac-clock-correlated UART events. **A** =
external ID+DLC match; **W** = name-only lead; **conflict** = format mismatch. An alias
does not by itself establish an A11 sender, recipient, scale, checksum, or wake/keep-alive
function — unknown entries remain unknown.

The full retained B capture has **265,214 data frames, 72 IDs, 39 adapter-status records**
through `B:265254`; no later data ID or DLC variant was found. Dictionary statistics below
use its first **60 seconds** (`B:2–8592`): **8,578 data frames**, **13 status records**,
**57 static-payload IDs**, **15 changing-payload IDs**. No extended/RTR frames, overflow
flags, or host TX echoes occurred in that B/H baseline window (later active tests contain
separately labelled TX echoes/diagnostics — see `can_bench_experiments.md`). The H snapshot
ends at `H:74804`. Periods below are median hardware-timestamp intervals at `t ≥ 2 s` in
that first minute (handling 32-bit wrap); one-second medians do not exclude event-triggered
updates. `U` is the distinct-payload count in that minute. Changed bytes are observations,
not decoded fields. Time zero is the first received B status record, not an electrical
power edge.

## Verified A11 signal translations

**Verified** means the specified observation or byte mapping was tested; it does not
validate unlisted bits, payload mutation, or every firmware version. Seed payload values
are not reproduced in this reference; no numeric scaling/signedness is defined for an
opaque seed byte array, and its observed byte order is not a claim about internal integer
endianness or cryptographic format.

| ID / direction | Field or effect | Radio-side mapping | Evidence and limits |
|---|---|---|---|
| `457`, harness → radio | b0–b7: opaque 8-byte Seed 1 | GMLAN reception → RH850 ProtoKey Seed 1 cache → ProtoKey delivery to SoC | All 8 bytes matched UART cached Seed 1 in 9/9 cache events, same order; original fixed payload only; bit substructure and checksum algorithm undecoded |
| `458`, harness → radio | b0–b7: opaque 8-byte Seed 2 | GMLAN reception → RH850 ProtoKey Seed 2 cache → ProtoKey delivery to SoC | All 8 bytes matched UART cached Seed 2 in 9/9 cache events, same order; original fixed payload only; bit substructure and checksum algorithm undecoded |
| `529`, harness → radio | **b1 bit 1**, mask `0x02`: IPC HMI Ready; 0=not ready, 1=ready | RH850 `CAN Event: IPC HMI Ready = 0/1`; relates to normal HmiInit progression | Fresh omission + single-frame restoration, then controlled clear/restore round trips; other mapped fields listed separately, remaining bits unresolved |
| `145`, harness → radio | Observed wake effect; NM-format interpretation remains candidate | Original single frame followed by SoC power-level reports and inbound T1 activity | Does not establish which PN bit wakes which component, or produce normal HmiInit/Propulsion alone |
| `20D`, tester → radio | b5 bit 7: protected remote-programming-active authenticated input, DLC 6 | Enables the documented T1 programming-session precondition | Captured companions retained, ~100 ms repetition; baseline `7F 10 22` changed to `50 02` in two T1 trials; original value restored; successful LTZ transfer and equivalent CAN5 entry remain unproven. Full trial narrative: `can_bench_experiments.md` |
| `284`, tester → radio | b4 bits 3–5: authenticated system-power-mode (raw 0=Off, 1=Accessory, 2=Run, 4=Propulsion; validity bit 2 clear). VHAL signal `58A` (`SPMP_SysPwrModeAuth`) maps to this frame. | All four raw values bench-verified (2026-11-26, `can_bench_experiments.md` "Power-mode Accessory/Propulsion resolved"): each produces a distinct, named UART `SystemState=` (`VehicleInitiated`/`Accessory`/`Run`/`Propulsion`), cross-checked against UDS DID `F085` (`diagnostics/GM_CAN_UDS_REFERENCE.md` §13) reading back the same raw value. Raw 2 alone was earlier confirmed via `IGNITION_STATE`→4/RUN, `SystemPowerMode` OFF→RUN. | No raw value produces a distinct Service/Technician state; "service" stays unverified. Full trial: `can_bench_experiments.md`; OTA-context confirmation: [`ota_update_stack.md`](ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17) |
| `529`, tester → radio | b1 bit 7: tested power-mode selector; 1→On/internal mode 2, 0→Off/internal mode 0 | Immediate PowerModeOn/Off and Propulsion/LocalInfotainment changes while packets continue | Two sustained clear/restore round trips; captured companion fields retained, including b0 bit 0=0; no Accessory/Service-mode claim. Bit also exercised in the OTA USB-update Off sequence: [`ota_update_stack.md`](ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17) |
| `529`, tester → radio | b0 bits 5–7: IPC Animation Status | RH850 animation-status log; full 3-bit field was swept through 0–7 | Eight cold starts plus a 2→1 transition distinguish not-ready (0), complete (1), and ready/incomplete (2–7); conditional on CSM readiness; OEM enum names unresolved. Full sweep/animation-player trial log: `can_bench_experiments.md` |
| `53B`, tester → radio | b7 bit 3: Infotainment Activation Request | RH850 activation-request log | Two 1/0 round trips plus an Off-state prewake: request=1 advanced Sleep → AnimationInit before the later door-open / request-1 candidate; actual video unverified. Full trial log: `can_bench_experiments.md` |
| `4BE`, tester → radio | b7 bit 3: Key/ID Device Present | RH850 true/false log | Synthetic payload; no claim of key authentication or theft-deterrent authorization |
| `4BE`, tester → radio | b6 bits 6–7: Valet Mode Response | RH850 raw value log | Values 0–3 observed. `[D]` Firmware trace (2026-11-22): VIP does **not** distinguish 1/2/3 — treats them as one "active" class (same event-flag, same two constant IPC posts), and forwards the raw byte unmodified to the SoC (message `0x59` on channels 2/`0x10`). Per-value enum meaning (active/pending/exiting) exists only on the SoC side, not recoverable from this firmware. |
| `4DA`, tester → radio | b6 bits 3–5: Folding Top State | RH850 raw value log | Values 0–2 observed. `[D]` Firmware trace (2026-11-22): collapsed to a single boolean (`value==1`) at the moment of reception — values 0 and 2 are indistinguishable everywhere downstream in this firmware. No "fully-closed vs. fault/unknown" distinction exists in VIP. |
| `4DA`, tester → radio | b7 bit 0: DriverDoorOpen; 1=open, 0=closed | RH850 DriverDoorOpen/Closed events; after PowerModeOff, ends LocalInfotainment and starts display shutdown | Live open/close control in Propulsion had no shutdown; opening after Off caused display off, HmiInactive, then Sleep and SoC-off; startup/shutdown animation request meanings documented in `can_bench_experiments.md`. Bit also exercised in the OTA USB-update Off sequence: [`ota_update_stack.md`](ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17) |
| `526`, tester → radio | b5 bit 7: mute-hold reset input, DLC 8 | Mute timer arming → SWC reset request after 9.998 s → coordinated SoC shutdown and VIP software reset | Synthetic frame, all other bits zero; ~100 ms repetition; original 145/529 continued; input released after reset detection, below the 20 s trial ceiling. Bit also exercised in the OTA post-install reset sequence: [`ota_update_stack.md`](ota_update_stack.md#y175-full-usb-update-bench-observation--2026-11-17) |
| `526`, tester → radio | b5 bit 3: volume down; b5 bit 2: volume up | Normal CAN button press/release → AAOS diagnostic volume readback | Separate 50 ms presses and all-zero releases gave 15→14→15; longer holds repeated; does not identify the physical button-source module |
| `560` | 6 | Signal `6B3` `VehIdNmDig1` | First VIN character + five zero bytes; companion fields unresolved. Native VHAL ARXML constructor-decoded; full NoVIN-recovery trial: `can_bench_experiments.md` |
| `45A` | 8 | Signal `6B5` `VehIdNmDig2_9` | VIN characters 2–9 in order. Same provenance/pointer as `560` above |
| `459` | 8 | Signal `6B4` `VehIdNmDig10_17` | VIN characters 10–17 in order. Same provenance/pointer as `560` above |

All three VIN IDs/DLCs also match the pinned VIP receive registry, callback slot 3 (see
firmware RX/TX configuration below); they are absent from the captured 32-ID harness
profile. Real VIN payload values were never captured in any retained document.

### ProtoKey seeds, VIN and diagnostic authorization are separate questions

The two CAN seed values (`457`/`458`) are opaque binary material used by the observed
RH850-to-SoC ProtoKey path. They have not been decoded as a VIN, shown to be VIN-derived,
or established as a theft-lock bypass. Their combined 16-byte length alone does not prove
the construction of the SoC's 16-byte ProtoKey. See
[`security.md`](security.md#bcm-replacement-factory-wipe-code-trace-2026-11-14) for the
native `gm_protokey` validator trace (does not compare a textual VIN; has a
BCM-replacement user-data-wipe branch). The CAN seeds are also distinct from the 31-byte
UDS `$27` seed and the MEC/ADB certificate gate.

For the verified `529` HMI-Ready field, decode `ready = bool(data[1] & 0x02)` from a
six-byte payload. For the animation-status field, `status = (data[0] >> 5) & 7`; to
change it while preserving other fields, `b0 = (original_b0 & 0x1F) | (status << 5)`.
For the `529` power-mode selector, extract `bool(data[1] & 0x80)`.

### Fresh omission controls — 2026-11-16

| Withheld ID, all other startup slots retained | Before late restoration | Late original after refreshing the other seven |
|---|---|---|
| `529` | No IPC HMI Ready=1, no HmiInit; startup-fault timeout at +16.231 s | IPC HMI Ready=1 at +31.5 ms from the probe |
| `20D` | Normal HmiInit at +7.909 s and Propulsion at +21.222 s; no startup fault | No new selected power-state marker in the eight-second probe window |

Omission of `20D` delayed AnimationInit in this trial but did not prevent normal startup —
conditional non-necessity, not the message's full function.

## Firmware receive/transmit configuration

Static-reference provenance: Y175 VIP_APP part `85759599`, SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`. This hash was not read
from live radio ROM; it is a build-matched reference, not the running radio's ROM hash.
Compiled address = file offset + `0x27A7A` for the traced strings/configuration tables
below (separate address domain from other firmware regions; not a universal mapping).

The receive table has **299 twelve-byte entries** through file `0x23CFA` (ID/mask lookup
`0xC2E6C`; receive dispatch `0xC2DFC` reads PDU index at +8, length/flags at +10, callback
slot at +11). **277 exact standard-ID entries route to callback slot 3**, 20 entries to
slot 2, one to slot 4, and one NM-style range entry to slot 1. Callback slots are software
dispatch indices, **not physical CAN channel numbers**. Slot 3's compiled callback pointer
`0xC6EE0` corresponds to wrapper file `0x9F466`.

The adjacent transmit configuration starts at file `0x23D06` (compiled `0x4B780`),
**58 entries**, including every one of the 40 baseline radio IDs with matching DLC.
Additional standard entries: `228` (DLC 6), `614` (8), `3F0` (8), `3F3` (8), `3FB` (8).
The other 13 are extended-format routes. Configured transmission is not evidence a message
has actually been emitted on this bench.

Remaining receive entries outside the 277-entry application group:

| Callback slot | Standard entries | Extended entries, wire IDs |
|---|---|---|
| 1 | NM-style range record: ID `100`, encoded mask/flags `600001FF`, length/flags `88` | None |
| 2 | `680`, `3FA`, `3F2`, `3F1`, all DLC 8 | `14DAF645`; `14DA80F1`–`14DA80F5`; `10EBFEF1`–`10EBFEF5`; `10DBFEF1`–`10DBFEF5`, all DLC 8 |
| 4 | `613`, DLC 8 | None |

13 additional extended transmit entries, all DLC 8: `14DCF180`, `14DCF280`, `14DCF380`,
`14DCF480`, `14DCF580`, `14DAFC80`, `14DAF180`, `14DAF280`, `14DAF380`, `14DAF480`,
`14DAF580`, `14DA45F6`, `10DBFEF6` (stored high-bit format flag removed from these wire
IDs). These inventories do not establish request/response pairing or service semantics;
`14DA80F2` → `14DAF280` diagnostic responses are independently confirmed live, other
listed routes are not all probed.

Only **17 of the 32 harness IDs** occur as exact slot-3 entries. The other 15 are
`01E 0AA 0C1 0C9 0F1 145 18E 1C6 1E5 1F1 1F5 26F 435 50F 551`. This does not prove they
are ignored — NM/range dispatch and other paths must be considered. In particular, the
external `1F1` power-mode interpretation has no exact slot-3 route here, consistent with
unsuccessful isolated power-mode experiments; `1F1` remains unvalidated on this radio.

### Signal-descriptor table decode

24-byte signal-descriptor table: compiled `0x4FB8C`, file `0x28112`. Signal `134` names
PDU `F0`, payload bit 9; the receive-table entry maps PDU `F0` to `529`, DLC 6 — matches
the independently verified b1 bit 1.

| CAN ID / DLC | Field, zero-based bytes | Signal index / PDU | Live observation |
|---|---|---|---|
| `529` / 6 | b0 bits 5–7: IPC Animation Status | `133` / `F0` | Clearing/restoring b0 bit 5 produced UART Animation Status 0/1; later full-field sweep confirmed raw values 0–7 |
| `53B` / 8 | b7 bit 3: Infotainment Activation Request | `84B` / `103` | Two 1/0 round trips, each logged by RH850 |
| `4BE` / 8 | b7 bit 3: Key/ID Device Present | `D93` / `CF` | RH850 logged true, then false |
| `4BE` / 8 | b6 bits 6–7: Valet Mode Response | `DE0` / `CF` | RH850 logged raw values 1, 2, 3, then 0; enum meanings undecoded |
| `4DA` / 8 | b6 bits 3–5: Folding Top State | `14A` / `26` | RH850 logged raw values 1, 2, then 0; enum meanings and hardware applicability unresolved |

The door signal `4DA` b7 bit 0 (DriverDoorOpen/Closed) is read at firmware offset
`5032C`: signal index `660`, PDU `26`, width 1, payload bit 56; it reaches `6F48C`
selector 0, posting event 15 (DriverDoorOpen) / 14 (DriverDoorClosed), matching the name
table at file `F9916`. Three other door selectors use signals `14C` (`4DB`, bit 56),
`8B7` (`4D9`, bit 59), `B05` (`4D8`, bit 6) — individual door positions not assigned or
live-tested.

Firmware `Com_ReceiveSignal` (file offset `C8F6A`) indexes the descriptor table by
**signal ID × 24**. Correct direct indexing maps button inputs C72–C77 to `526`, b5 bits
7–2: C72/b5-bit7 is the mute-hold reset timer-arming branch (see verified-signal table
above); guard signals `DC9`/`DD8` are referenced by the same timer branch, full
application meanings unresolved. Full button-mapping test log and reset-timing proof:
[boot timing](../runtime/boot_timing.md#mute-hold-reset-and-adb-reboot-boundaries-2026-11-15),
`can_bench_experiments.md`.

Smallest demonstrated **home-screen ID set**:

| ID | Proven role in this bench work |
|---|---|
| `145` | Observed wake effect; network-management field interpretation remains a candidate |
| `529` | IPC HMI Ready: b1 bit 1; IPC Animation Status: b0 bits 5–7, captured value 1 completes the startup animation handshake |
| `457` | Opaque eight-byte ProtoKey Seed 1 |
| `458` | Opaque eight-byte ProtoKey Seed 2 |

PlayAnimation IPC request values (VIP→display, distinct numeric domain from `529`'s CAN
animation-status field): static tracing resolves requests 1–4 to player events
`STOP_ANIMATION`/`SHOW_WELCOM_ANIM` (sic)/`SHOW_STARTUP_ANIM`/`SHOW_SHUTDOWN_ANIM`. Full
decode, animengine binary provenance, and the door/wake/shutdown CAN-triggered request
paths: `can_bench_experiments.md`.

### Exact standard-ID slot-3 inventory

Each token is `ID:DLC`, hex ID and decimal byte count. These are **configured receive
candidates**, not 277 decoded meanings or 277 successful live tests. Payload validity,
calibration, operating state, counter/checksum rules and optional equipment may constrain
actual use.

```text
016:8 023:8 028:8 029:8 02A:8 02B:8 02C:6 02D:8 032:8 037:6 08C:6 0B5:8 202:6 204:6 20D:6 227:6
229:7 22A:7 23B:5 24F:5 25E:8 25F:8 260:8 261:8 262:6 263:8 264:8 269:8 26A:8 26B:8 26C:8 26D:6
284:6 404:6 405:6 407:7 40B:5 40C:8 414:6 416:6 41C:5 41E:7 423:6 425:6 429:7 42A:8 430:7 432:7
433:8 434:7 436:6 43B:5 442:8 44D:5 452:6 453:8 454:7 455:7 456:8 457:8 458:8 459:8 45A:8 45B:8
45C:7 45D:7 45E:7 45F:7 460:7 461:7 462:7 463:7 464:7 465:6 466:7 467:7 468:7 469:7 46B:7 46C:7
46D:7 46E:7 46F:7 470:7 471:7 472:7 473:7 474:7 475:7 476:7 477:7 478:7 479:7 47A:7 47B:7 47C:7
47D:7 47E:7 47F:7 481:7 482:7 483:7 484:7 485:7 486:7 487:7 488:7 489:7 48A:8 48B:7 48C:7 48D:7
48E:7 48F:7 490:8 491:8 492:8 493:8 494:8 495:8 496:8 497:8 498:8 499:8 49A:8 49B:8 49C:8 49D:8
49E:8 49F:8 4A0:8 4A1:8 4A2:8 4A3:8 4A4:8 4A5:8 4A6:8 4A7:8 4A8:8 4A9:8 4AA:6 4AB:8 4AC:8 4AD:6
4AE:8 4AF:8 4B0:8 4B1:8 4B2:8 4B3:8 4B4:8 4B5:8 4B6:8 4B7:8 4B8:8 4B9:8 4BA:8 4BB:8 4BC:8 4BD:6
4BE:8 4BF:8 4C0:8 4C1:8 4C2:8 4C3:8 4C4:8 4C5:8 4C6:8 4C7:8 4C8:8 4C9:8 4CA:8 4CB:8 4CC:8 4CD:6
4CE:6 4CF:8 4D0:8 4D1:8 4D2:8 4D3:8 4D4:8 4D5:8 4D6:8 4D7:8 4D8:8 4D9:8 4DA:8 4DB:8 4DC:8 4DD:8
4DE:8 4DF:8 4E0:8 4E1:8 4E2:8 4E3:6 4EE:7 506:7 507:7 509:8 50C:7 50D:7 512:8 514:6 515:6 517:8
518:7 51B:7 51C:8 51D:6 51E:6 51F:8 520:8 521:6 523:7 524:6 526:8 527:6 528:8 529:6 52A:7 52B:7
52C:6 52E:7 52F:6 532:7 533:7 534:8 535:8 537:8 538:6 53A:6 53B:8 53C:6 53D:7 53E:7 53F:6 540:6
541:6 544:7 545:7 546:8 55E:8 55F:6 560:6 561:8 562:6 563:7 564:6 56A:8 56B:6 56D:7 573:7 578:6
579:6 57E:7 57F:7 580:7 583:7 584:7 586:6 588:7 589:6 591:6 592:6 593:6 594:7 597:5 5A1:6 5A9:8
5BA:8 5BE:8 5C3:8 5C9:6 5CE:8
```

## The 32 harness IDs

Every H payload matched its B counterpart and remained fixed across the isolated restart.
Complete identical cycles checked: **180 connected**, **655 isolated before restart**,
**1,681 isolated after restart**; median cycles were **320.203 / 320.308 / 320.294 ms**
(`B:403`, `H:2`, `H:21002`). A **23.166931-second quiet gap** ends at `H:21002`; no extra
startup-only harness ID appeared, first post-gap ID `0x145` (no proof of mandatory phase).
All rows below have `U=1`; source class H. H identifies the bench transmitter, not the
actual in-vehicle producer. Absence from the working four-ID recipe does not mean the
radio ignores an ID — individual application meaning/handler may still need decoding.

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

Cyclic order, anchored at `0x145`:

```text
145 521 20D 523 529 551 1F5 0C9 0F1 02C 4B6 016 023 028 02B 0B5
457 458 08C 037 22A 01E 435 26F 50F 1F1 0AA 1E5 1C6 18E 0C1 204
```

Initial connected startup contains **74 identical `0x145` frames** from `t=.004174–.023655 s`,
median spacing ~**266 µs** (`B:10–87`). After radio disconnection without an acknowledging
peer, the retained tail repeats `0x458` at ~**3,814–3,815 frames/s** through `B:265254`.
ACK-enabled H reception restores ~**100 frames/s** (`H:1–21001`) — acknowledgement-dependent
transmission behavior. CANable sent no application commands in this baseline; other
untriggered behavior remains possible.

## The 40 radio IDs

All rows are R. `U=1` means no payload change in the first minute of B. Changing-byte
lists identify investigation targets, not semantics. The two one-shot IDs occur once in
the entire retained B capture.

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

Only `0x4FA` gains distinct payloads later: **623 values in 638 occurrences**, last at
`B:90600`; other full-capture U values equal the first-minute values. Not decoded as time,
distance, or another quantity. Useful startup transitions: `0x4ED/0x4F1` near **8.554 s**
(`B:1340–1341`), `0x267/0x504` near **8.622 s** (`B:1351–1352`), `0x4F6/0x4F7` near
**30.57–30.67 s** (`B:4450–4464`), `0x4EF` at **40.081645 s** (`B:5790`). Temporal
coincidence alone does not decode the state.

### Radio-output candidates for the access transition

Six successful gate-transition windows and four failed single-ID/count windows were
compared using stable bits in the eight seconds before a probe and seconds 8–16 after it.
Candidate feedback fields, not named OEM signals; full probe methodology is in
`can_bench_experiments.md`.

| Radio ID | Observed stable-bit change | Successful windows | Negative windows with same bit change |
|---|---|---:|---:|
| `4ED` | b0 bit 0: 0→1; b1 bits 2/5/7: 0→1 | 6/6 each | 0/4 |
| `4ED` | b0 bit 1; b4 bits 2/4; b5 bit 6: 0→1 | 5/6 each | 0/4 |
| `4F1` | b0 bit 1: 0→1; b1 bit 7: 1→0 | 5/6 each | 0/4 |
| `504` | b1 bits 4/5: 0→1; bit 6: 1→0 | 4/6 each | 0/4 |

Each bit is numbered from the least-significant bit of its byte. Concurrent
power/network/application changes remain confounders — do not treat these as a
home-screen, login-success or ADB-state decoder without fresh controls.

## Published candidates (external DBC comparison)

**Global A**, not A11-specific, definitions match both ID and DLC in the pinned
[OpenDBC powertrain source][A]. DBC notation `start|length@endian`: `@0` Motorola bit
numbering, `@1` Intel; `-` signed, `+` unsigned. Start number is not a simple byte offset.

| ID | External candidate fields | Source location |
|---|---|---|
| 0C9 | RPM `15\|16@0+` ×0.25; throttle `39\|8@0+` ×0.392156863; brake `40\|1@0+` | [A:69][A69] |
| 0F1 | Brake switch `1\|1@0+`; pedal position `15\|8@0+` | [A:85][A85] |
| 1E5 | Steering angle `15\|16@0-` ×0.0625 degrees; rate `27\|12@0-` | [A:152][A152] |
| 1F1 | Primary power `1\|2@0+`; backup power `5\|2@0+`; parking brake `36\|1@0+` | [A:165][A165] |
| 1F5 | Selector `27\|4@0+`; transmission state `48\|4@1+`; manual mode `41\|1@0+` | [A:174][A174] |

For `0x1F1`, the DBC enumerates **0=Off, 1=Accessory, 2=Run, 3=Crank Request** for both
power fields ([A:324][A324]). The captured primary field is **2** (`B:150`); layout and a
plausible value do not prove a valid A11 wake command — required counters, checksums,
companion frames and shutdown behavior remain unresolved (full negative isolated
power-mode test record: `can_bench_experiments.md`).

The older E38/T43 [l77rodeo reference][L] additionally names accessory and run/crank
status, backup-mode enable, parking-brake availability, immobilizer pre-release
password/status and remote-start-related inputs for `1F1`, without byte/bit offsets —
not a second verified bit-layout decoder or an A11 control specification.

[GMLanDebug][G] supplies the W names without validated A11 layouts. [l77rodeo's first-hand
E38/T43 research][L] supplies older high-speed 11-bit examples; its shorter `0x4E9`
demonstrates why an ID/name match is insufficient. Original [PCM Hacking experiments][F1]
describe firmware TX/RX tables; a [later discussion][F2] distinguishes specification
families and missing convenience coverage. No complete OPU GM 85633185/A11 CAN-5
dictionary was found in these inspected sources — not a claim that none exists elsewhere.

### Additional older-platform conflicts checked — 2026-11-16

The [2008 Impala notebook][I08] and its [DBC][I08DBC] label `4F1` as PCM fuel rail
pressure, whereas GMLanDebug calls it powertrain configuration data; the notebook leaves
the pressure formula unconfirmed. Our `4F1` sender is the radio on the isolated bench, not
an identified PCM — both external names remain unresolved leads.

For `4E9`, l77rodeo's two examples are each **five bytes** (matches the existing
length-conflict entry); the Impala notebook lists **two bytes**; our radio emits **eight**.
These platform differences are reasons to reject automatic ID-based label transfer.

Surreal Development's [Cadillac Part 1][S1] explicitly excludes Intel Silverado/Sierra
radios from its studied Qualcomm hardware. Its `0x4F5` raw eight-byte example overlaps,
without a signal definition. Its vehicle VIN IDs `0x712/0x75F/0x49B` are absent here.
[Part 2][S2] describes CAN5 at 500 kbit/s and an external `0x370` field, `bit37:3`:
**Off=1, Accessory=2, Run=3, Crank=4, Propulsion=5**. `0x370` is absent here; this enum
must not be merged with Global A `0x1F1`. [The ABCs of Global B][S3] provides broader
vehicle context. These in-vehicle findings remain useful where bench validation is
unavailable; the article sources are not a complete DBC or replay package.

## Open conflicts

- `0x1F1` (Global A DBC Off/Accessory/Run/Crank enum, captured value 2/"Run") vs this
  bench's negative isolated/ordered Off/Accessory power-mode trials (no shutdown command
  effect observed) — unresolved on this radio; both values kept per source (`1F1` row
  above, Published candidates section). Do not merge with Surreal's in-vehicle `0x370`
  enum (absent here).
- Gateway/CGM addressing (`CAN 0x45` identity vs Ethernet `.107/.112`) is a topology
  question outside this dictionary's scope — tracked as an open item in
  [`vehicle_network.md`](vehicle_network.md) (join points / open item #3); not
  re-litigated here.

## Related
- [`vehicle_network.md`](vehicle_network.md) — topology, ECU census, diagnostic transport, gateway addressing.
- [`can_bench_experiments.md`](can_bench_experiments.md) — lab-notebook: calibration/LTZ trial narrative, adapter status/startup-reduction/keep-alive timing, ADB-enable sweeps, animation/door-sequence test logs.
- [`../hardware/bench_setup.md`](../hardware/bench_setup.md) — wiring and adapter configuration.
- [`ota_update_stack.md`](ota_update_stack.md) — OTA/USB-update bit-level frame confirmations (284/526/529/4DA) in context.
- [`security.md`](security.md) — ProtoKey/seed validator trace.
- [`ethernet_networking.md`](ethernet_networking.md) — VIP MCU as CAN↔IPC bridge, CSM address.

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
[N]: https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANNetworkManagement.pdf
[I08]: https://github.com/dwilson2547/robo-services/blob/5a9f6351fb2e0bd6e9ba976aefa7dbc3e87ff5eb/can_data/analysis/gm/chevy_impala_2008.md
[I08DBC]: https://github.com/dwilson2547/robo-services/blob/5a9f6351fb2e0bd6e9ba976aefa7dbc3e87ff5eb/can_data/dbc/custom/chevy_impala_2008_hscan.dbc

## Ranges not migrated from the original (archived)

These original `can_network.md` ranges are not reproduced in the consolidated docs; they remain in the archived original, [archive/can_network_original.md](archive/can_network_original.md):

- L476-514: four-ID startup recipe (offsets, +7.892 / +21.199 s timings, restricted-boot procedure).
- L1046-1091: activation-request hold, host-sleep confound, 62.519 / 62.385 s results.

The independent loss audit of the original covered only L1-600; L600-2129 is covered by the writers' ledgers for `can_network` and `can_bench_experiments` (not preserved in this repository) but not by a second reader.

## Complete RX catalog — every CAN ID VIP_APP is configured to receive

Consolidates the firmware RX table (§Firmware receive/transmit configuration, 299 entries
total) with every known-meaning decode elsewhere in this doc, into one reference. This is
the firmware's own configured-acceptance list — **configured does not mean tested**; most
rows below have never been individually driven on the bench.

**Status legend:** `BENCH-VERIFIED` = specific bit(s) decoded and live-tested ·
`BENCH-OBSERVED` = ID appears in a live capture (harness or radio) and has an exact slot-3
route, but no bit-level meaning decoded · `BENCH-CANDIDATE` = a Com signal descriptor maps
this ID to a named signal, but it was not independently live-tested · `FIRMWARE-CONFIGURED`
= present in the firmware's RX table with no bench correlation attempted in any retained
document.

### Dispatch breakdown (299 entries, by callback slot)

| Slot | Role (software dispatch index, not a physical channel) | Count | Entries |
|---|---|---:|---|
| 1 | NM-style range record | 1 | `100` (mask `600001FF`) |
| 2 | Diagnostic/UDS | 20 | `680`, `3FA`, `3F2`, `3F1` (standard, DLC 8) + extended `14DAF645`; `14DA80F1`–`14DA80F5`; `10EBFEF1`–`10EBFEF5`; `10DBFEF1`–`10DBFEF5` (all DLC 8) |
| 3 | Main application (signal/event consumption) | 277 | Full ID:DLC inventory already given verbatim in **§Exact standard-ID slot-3 inventory** above — not retyped here to avoid a transcription-risk duplicate of that code block |
| 4 | OBD | 1 | `613` (DLC 8) — the CAN613/614 XCP-style debug interface traced in `VIP_APP_FILE_MAP_85759599.md` |

### Known-meaning rows (every slot-3 ID with any decoded bit, named signal, or bench observation)

| CAN ID | DLC | Known meaning | Status |
|---|---:|---|---|
| `457` | 8 | ProtoKey Seed 1 (opaque 8B; GMLAN → RH850 cache → SoC) | BENCH-VERIFIED |
| `458` | 8 | ProtoKey Seed 2 (opaque 8B) | BENCH-VERIFIED |
| `560` | 6 | VIN digit 1 (signal `6B3` `VehIdNmDig1`) | BENCH-VERIFIED (pointer; real VIN value never captured) |
| `45A` | 8 | VIN digits 2–9 (signal `6B5` `VehIdNmDig2_9`) | BENCH-VERIFIED (pointer; real VIN value never captured) |
| `459` | 8 | VIN digits 10–17 (signal `6B4` `VehIdNmDig10_17`) | BENCH-VERIFIED (pointer; real VIN value never captured) |
| `529` | 6 | b1 bit1: IPC HMI Ready · b0 bits5-7: Animation Status · b1 bit7: power-mode selector | BENCH-VERIFIED |
| `53B` | 8 | b7 bit3: Infotainment Activation Request | BENCH-VERIFIED |
| `4BE` | 8 | b7 bit3: Key/ID Device Present · b6 bits6-7: Valet Mode Response | BENCH-VERIFIED |
| `4DA` | 8 | b7 bit0: DriverDoorOpen/Closed · b6 bits3-5: Folding Top State | BENCH-VERIFIED |
| `4DB` | 8 | Door-position signal (`14C`, bit56) | BENCH-CANDIDATE (signal mapped, position/live test not done) |
| `4D9` | 8 | Door-position signal (`8B7`, bit59) | BENCH-CANDIDATE |
| `4D8` | 8 | Door-position signal (`B05`, bit6) | BENCH-CANDIDATE |
| `526` | 8 | b5 bit7: mute-hold reset · b5 bit3: volume down · b5 bit2: volume up | BENCH-VERIFIED |
| `284` | 6 | b4 bits3-5: `SPMP_SysPwrModeAuth` candidate | BENCH-VERIFIED |
| `20D` | 6 | b5 bit7: remote-programming-active authenticated | BENCH-VERIFIED |
| `016` | 8 | — | BENCH-OBSERVED (harness capture, exact slot-3 match, meaning undecoded) |
| `023` | 8 | — | BENCH-OBSERVED |
| `028` | 8 | — | BENCH-OBSERVED |
| `02B` | 8 | — | BENCH-OBSERVED |
| `02C` | 6 | — | BENCH-OBSERVED |
| `037` | 6 | — | BENCH-OBSERVED |
| `08C` | 6 | — | BENCH-OBSERVED |
| `0B5` | 8 | — | BENCH-OBSERVED |
| `204` | 6 | External GM DBC conflict: a public battery-signal DBC lists this ID at DLC 8, not 6 | BENCH-OBSERVED |
| `22A` | 7 | — | BENCH-OBSERVED |
| `4B6` | 8 | — | BENCH-OBSERVED |
| `521` | 6 | — | BENCH-OBSERVED |
| `523` | 7 | — | BENCH-OBSERVED |

**Every other ID in the 277-entry slot-3 inventory, all 20 slot-2 entries, the slot-1 NM
range, and the slot-4 OBD entry (`613`) are `FIRMWARE-CONFIGURED`** — present in the
firmware's own acceptance table with no bench correlation attempted in any retained
document. This is the actual "known vs. untested" boundary: **17 of 277** application-slot
IDs have ever been individually observed on this bench, and only **14** of those have a
decoded bit-level meaning. The remaining ~260 are real, firmware-accepted messages whose
content this radio has never been sent and whose effect is unknown.

**Harness-observed IDs with no firmware RX route at all** (seen live on the bus, but absent
from VIP_APP's own 299-entry table — consuming path, if any, is unconfirmed, not negative):
`01E`, `0AA`, `0C1` (external DBC candidate: driven-wheel rotational status), `0C9`
(candidate `ECMEngineStatus`), `0F1` (candidate `EBCMBrakePedalPosition`), `145` (wake
effect, NM-format candidate), `18E`, `1C6`, `1E5` (candidate `PSCMSteeringAngle`), `1F1`
(candidate `BCMGeneralPlatformStatus`, Run-state), `26F`, `435`, `50F`, `551`.
`1F5` (external candidate `ECMPRDNL2`) was also in this no-route list — **superseded below**:
firmware tracing has now identified the real PRNDL/gear receive path, and it is not `1F5`.

### PRNDL/gear receive path

Traced by static firmware analysis (2026-11-21), not by DBC name-matching. Chain: SRAM
`_DAT_febd3434`/`_DAT_febd3438` (already read by the gear-status transmitter, see TX
catalog below) ← setter `FUN_0008c6d4` (`0x8c6d4`) ← Com-RX unpack function at `0x4da62`
← PRNDL decode `FUN_0004d7dc` (`0x4d7dc`) ← two Com signal descriptors, base **`0x2812A`**
(`+signalID*0x18`, 24-byte records; calibrated 2026-11-26 against the already-verified
`0x529` HmiReady/AnimationStatus bit positions, so the field offsets below are read from
the live descriptor bytes, not the AUTOSAR start-bit numbers originally quoted here):

| CAN ID | DLC | Com signal | Bit field | Role | Status |
|---|---:|---|---|---|---|
| `40B` | 5 | `0xDCB` | **byte4 bits5-7 (3-bit, mask 0xE0)** | Primary PRNDL input | `FIRMWARE-TRACED`, bench-live-confirmed reactive 2026-11-26 |
| `264` | 8 | `0xCAC` (validity) / `0xCAD` (value) | validity: byte3 bit6 (mask 0x40); value: byte3 bit7 + byte4 bits0-2, 4-bit | Validity gate + fallback (used when `40B`'s own byte3-bit6-equivalent validity reads 0) | `FIRMWARE-TRACED`; fallback field offset not bench-confirmed |

**Correction, 2026-11-26:** the original "2-bit @ start-bit 35" / "4-bit @ start-bit 45"
notation above (quoting the AUTOSAR ComSignal descriptor's own start-bit numbering
literally) was wrong about field width and conflated two different signals in the same
PDU — `0xDC8` (2-bit, byte4 bits3-4) is a *different*, still-unidentified signal in the
`40B` frame, not the gear value. The real gear VALUE field is `0xDCB`, 3-bit, byte4
bits5-7 — this is why the decode function's own remap table (`raw0→2, raw1→3, raw2→0,
raw3→1, raw4→4`, catch-all 0 for raw5-7) made no sense against a 2-bit field (max raw
value 3) but fits a 3-bit field cleanly. The `264`-side validity bit that gates
primary-vs-fallback is NOT inside `40B` itself (as the original wording implied); it is
`264` byte3 bit6.

Bench-confirmed live (2026-11-26, `platform/can_bench_experiments.md`): holding `40B` =
`00 00 00 00 <raw<<5>>` together with `264` = `00 00 00 40 00 00 00 00` (forcing
validity=1) is correctly received and decoded — the internal remap fires as predicted.
**What remains unconfirmed:** the mapping from the firmware's internal enum {0,1,2,3,4}
to the AAOS-side `android.car.VehicleGear` bitmask (Park=4/Reverse=2/Neutral=1/Drive=8,
confirmed present and consumed on this unit via `dumpsys car_service`'s
`propId 0x11400400` registration and "Supported gears" list) — no observable AAOS-side
reaction (logcat, screen, `com.gm.cluster` process output) was found during live testing,
so which raw value is which gear letter is still open. `FIRMWARE-TRACED` for the bit
positions above = two independent exact ComIPdu-handle matches (`0x10d`, `0x31`), DLC and
byte-offset consistent, now cross-calibrated against a known-good signal and bench-tested
live — not yet AAOS-reaction-verified. Assumes ComIPdu handle routes 1:1 to the CanIf PDU
field; no separate PduR indirection table was independently checked. No RX-side string
exists for either signal.

This explains why `1F5`/`ECMPRDNL2` had no slot-3 match: that was an external public-DBC
name for a different vehicle's signal layout, not this firmware's real (unnamed,
internally-numbered) gear inputs. Apply the same caution to every other external-DBC name
in the no-route list above — a public DBC name match does not predict this firmware's
actual signal IDs.


## Complete TX catalog — every CAN ID VIP_APP is configured to transmit

The firmware's transmit table has **58 twelve-byte entries** at file `0x23D06` (compiled
`0x4B780`), immediately following the RX table. Three groups:

### 1. Standard IDs matching the 40 bench-observed radio IDs (§The 40 radio IDs above)

All 40 are radio-transmit-confirmed by direct capture; DLC matches the firmware TX entry
exactly for every one. Meaning/confidence column reproduced from that section — not
retyped in full detail here to avoid a duplicate that could drift out of sync; see
**§The 40 radio IDs** for the complete per-ID changing-byte/period data. Status for all 40:
`BENCH-VERIFIED (sender confirmed)` — a frame being sent is confirmed live; its payload
*meaning* is mostly still undecoded except where noted:

| CAN ID | DLC | Decoded meaning (where any exists) |
|---|---:|---|
| `180` | 8 | NM-format candidate; external steering-command DBC conflicts |
| `4E9` | 8 | External candidate: platform configuration |
| `4F1` | 8 | External candidates: powertrain configuration (conflicting DBC sources, neither A11-validated) |
| `4F3` | 4 | External candidate: powertrain configuration 2 (one-shot) |
| `4FC`, `54E`, `54F` | 8 | Four recurring payload states each, meaning undecoded |
| `4FA` | 6 | Counter-like progression (623 distinct values over the full capture), meaning undecoded |
| all remaining 32 of the 40 (`267 424 427 4E4 4E6 4EA 4ED 4EE 4EF 4F0 4F2 4F4 4F5 4F6 4F7 4F8 4F9 4FB 4FD 4FE 4FF 500 501 502 503 504 505 54C 576 587 58B 59B`) | 4–8 | Sender confirmed, payload/function fully undecoded |

### 2. Additional standard-ID TX entries (configured, not in the 40-radio bench set)

| CAN ID | DLC | Status |
|---|---:|---|
| `228` | 6 | FIRMWARE-CONFIGURED — never observed as radio-sent in any retained capture |
| `614` | 8 | FIRMWARE-CONFIGURED — the CAN613/614 XCP debug-interface reply ID (see slot-4 RX `613`, `VIP_APP_FILE_MAP_85759599.md`) |
| `3F0` | 8 | FIRMWARE-CONFIGURED |
| `3F3` | 8 | FIRMWARE-CONFIGURED |
| `3FB` | 8 | FIRMWARE-CONFIGURED |

### 3. Extended-format (29-bit) diagnostic TX routes — 13 entries, all DLC 8

`14DCF180`, `14DCF280`, `14DCF380`, `14DCF480`, `14DCF580`, `14DAFC80`, `14DAF180`,
`14DAF280`, `14DAF380`, `14DAF480`, `14DAF580`, `14DA45F6`, `10DBFEF6`.

`[D]` Firmware trace (2026-11-22) resolves most of this family — J1939 29-bit diagnostic
addressing `14DA{TA}{SA}`, radio diagnostic address `0x80`, tester addresses F1–F5:

| Group | Finding |
|---|---|
| `14DA80F1`–`F5` (RX) ↔ `14DAF180`–`F580` (TX) | **Firmware-confirmed uniform pairing**, not just the one live-tested `F2` pair — RX handler `FUN_0006708a` and TX validity check `FUN_00067168` both treat all five tester channels identically (source-address latch `DAT_febd1ad1`, response set enumerated as a fixed list of 5) |
| `14DAFC80` | Not request-paired by design — a conditional **functional-response substitute**: `FUN_00067168` rewrites a normal response to this ID when a specific payload/flag condition holds |
| `14DAF645` ↔ `14DA45F6` | Self-evident tester/gateway (`0x45`) address swap pair |
| `10DBFEF1`–`F5` | Feed the same tester-channel latch as the `14DA80Fx` family |
| `10EBFEF1`–`F5` | J1939 TP.DT multi-packet transport RX (PGN `0xEB`) — no direct TX pair |
| `14DCF180`–`F580` | **Still unestablished** — no matching RX, and no code found that constructs them; present only in the static TX config table, not exercised by the traced SecurityAccess path |

### Egress paths not covered by this static table

Two transmit mechanisms exist outside the 58-entry TX config table and are **not** raw CAN
IDs resolvable from the static image:
- **Gear status** (internal "channel 4", 9-byte IPC-style record type `0x0C`/sub-id `0x05`,
  built by `FUN_0005c30e`) — see
  [`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`'s cold-entry selector trace](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#cold-entry-selector-trace--2026-11-17)
  for the shared channel-transmit primitive this reuses. Whether channel 4 egresses as a raw
  CAN frame or stays internal VIP↔SoC IPC is unresolved from static analysis.
- Any traffic routed through the **`CanIf` compiled callback wrapper** (file `0x9F466`) that
  isn't a static table entry — e.g. computed/runtime-built frames — is not enumerable
  without live tracing.


## CAN-received signal fate

Every received signal falls into one of five outcomes: not received (`0C1`, `0C9`, `0F1`);
received, NM-only, never decoded (`1E5`, `1F1`); received and consumed locally (`4DA` door,
`4BE` valet, gear); received and pushed to the SoC over a dedicated IPC channel (gear,
channel 4); received, decoded, and never read by anything (`4D8`/`49B`/`561`/`492`/`4D4` and
~250 others — no SoC pull path exists either; this firmware has no UDS
`ReadMemoryByAddress` service).

Full trace detail (SystemState HSM/audio-cue chain, SoC power-on/ELK gating, the idle-timer
system) is owned by
[`VIP_APP_FILE_MAP_85759599.md`](../research/boot-update-recovery/VIP_APP_FILE_MAP_85759599.md#can-received-signal-fate)
— not restated here.
