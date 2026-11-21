# Rear-Panel Connectors

Scope: external harness connectors of the A11 radio (RPO IOK): per-cavity pinout, coax (FAKRA)
feeds, and the power / CAN / Ethernet / discrete signal headers.
Related: [`module/identity_bom.md`](../module/identity_bom.md), [`audio.md`](audio.md),
[`display.md`](display.md), [`usb.md`](usb.md).

Confidence tags: **[C]** confirmed against schematic circuit names/numbers or silicon · **[I]**
inferred from FAKRA color convention, pin count or harness shape · **[?]** open.

GM issues several harness variants for this radio. Designators (`X1`…`X11`) and populated
cavities differ by RPO and trim. Identify connectors by function, not by X-number.

Source basis: rear-panel photo of the test unit; GM service wiring diagrams (*Sound Systems –
Low Level*, *Sound Systems – Mid/High Level W/ Amplifier*, *Computer Data Lines*); ALLDATA
Component Connector End Views (CarId 65566).

## 1. IOK Connector Table (ALLDATA, per cavity) — [C]

Authoritative for RPO IOK. Where this table disagrees with the photo-derived layout in §2 or the
cross-reference in §6, this table applies. Coax connectors list one summary function.

| Conn | OEM P/N | Service P/N | Type / housing | Signals |
|------|---------|-------------|----------------|---------|
| X2 | 33340311 | by cable | 1-way F coax (BU) | GPS/GNSS antenna |
| X3 | 33340318 | by cable | 1-way F coax (CU) | SiriusXM / SDARS (+HD) antenna |
| X5 | 35364134 | 13534974 | 29-way F 0.5 NANO / 1.2 MCON stAK50h (BK) | See §1.1 |
| X6 | 35364137 | 13534971 | 29-way F 0.5 NANO / 1.2 MCON stAK50h (GY) | See §1.2 |
| X7 | 13511515 | by cable | 12-way M 2.0 HSAL-2 (GY) | Display, FPD-Link III ("LVDS"); see [`display.md`](display.md) |
| X8 | 13545174 | by cable | 12-way M 2.0 HSAL-2 (BK) | USB serial data; see [`usb.md`](usb.md) |
| X9 | 33340320 | by cable | 1-way F coax (OG) | Video Processing Module coax video (cameras) |
| X10 | 33340317 | by cable | 1-way F coax (BG) | Wi-Fi antenna |
| X11 | 35068239 | 13529935 | 12-way F 050 CTS (BK) | See §1.3 |

### 1.1 X5 — as wired on the test vehicle

Receptacle has 29 cavities; the harness populates p1/3/9/10/11/12 only.

| Pin | Circuit | Function |
|-----|---------|----------|
| 1 | 2340 RD/YE | Battery + |
| 3 | 1051 BK/WH | Signal ground |
| 9 / 10 | 655 / 5149 (BU, GY/YE); 654 / 5152 (BK/BN, BK/GY) | Cell-phone mic and voice-recognition mic (`Opt GF2-GF5 / IOK+UE1`) |
| 11 / 12 | 7043 VT/YE / 7044 BU/BK | Microphone ± |

p8 (LR speaker −, 116 GN/BK) appears in the ALLDATA superset end view but is not wired (see §1.4).

### 1.2 X6 — as wired on the test vehicle

Receptacle has 29 cavities; the harness populates p9/10/13 only.

| Pin | Circuit | Function |
|-----|---------|----------|
| 9 / 10 | 4985 BU/WH / 4984 BU/YE | AUTOSAR CAN 5 ± (VIP/SDV1-GB, 29-bit). Amp-control serial data; radio end of the CAN 5 link to the Bose amplifier (T3 X3). Called "SER DATA 5" by the DPS gateway scan (`platform/vehicle_network.md`, Plane 1). |
| 13 | 24 GN/WH | Backup lamp control |

Speaker-level outputs (p1–6/8: LR+ 199, LF1+ 201, RF−1 117, RR− 115, LF−1 118, RF1+ 200, RR+ 46)
appear in the ALLDATA superset end view but are not wired (see §1.4). Source: ALLDATA X6 end
view; `05_ALLDATA_WIRING_REFERENCE.md` §8.

### 1.3 X11 — as wired on the test vehicle

Six occupied pins, all wired.

| Pin | Circuit | Function |
|-----|---------|----------|
| 3 / 4 | 4758 YE / 4757 BU | Ethernet Bus 2 ± → K56 gateway |
| 8 / 9 | 7215 YE / 7214 GN | Ethernet Bus 6 ± → Bose amplifier |
| 11 / 12 | 7211 BN / 7210 GY | Ethernet Bus 4 ± → K73 comm |
| 1, 2 | — | Harness inspection: not occupied. **[?]** See below. |
| 5–7, 10 | — | Not occupied |

GM documents the A11 as a five-bus radio (Buses 2/4/5/6/14; `platform/ethernet_networking.md`
§Physical Automotive-Ethernet bus map). The test vehicle has no rear-seat video or HUD, so
Buses 5 and 14 are not optioned.

Mate: harness connector 13529935 = Delphi/Aptiv drawing 33283033 ("TAXI ASM CONN 12 F CTS 050"),
12-way female CTS-050, male-plug shell with female sockets, CPA. Datasheet:
[`datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf`](../datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf).

**Open item (2026-11-13), X11 p1/2 [?].** A T1-converter tap on p1/2 of the same radio showed
bidirectional traffic with the same VLAN trunk and the same 9016/49156 service allow-list as Bus 2
(p3/4), with the opposite PHY master/slave role. The traffic cannot be attributed to a GM circuit
number for a documented bus. Candidate explanations: spare internal switch test port, as-wired
Bus 5/14 deviation, or a cavity-counting error. Detail:
`source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §14 in the `Y175_2026-11-02`
analysis tree (`GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/`).

### 1.4 Speaker-level cavities

X5/X6 speaker cavities belong to the non-amplified (U95-UQF) variant. The UQA truck routes audio
digitally to the amplifier (see [`audio.md`](audio.md)); the radio's speaker pins are unused.
Confirmed by the `Speakers (UQA)` vs `Speakers (U95-UQF)` schematic split.

### 1.5 As-wired datasets: vehicle vs bench

| Item | In-vehicle harness | Bench (OPU Wiring Tester + Emulator, GM 85633185, HMI 3.7–3.8) |
|------|--------------------|------------------------------------------------------------------|
| X5 | p1/3/9/10/11/12 | p1/3 only (Battery+, ground) |
| X6 | p9/10/13 | p9/10 only (CAN 5 ±, injected by emulator board) |
| X7 | FPD-Link to display | FPD-Link to display |
| X11 | Ethernet Buses 2/4/6 | Not populated |

With a 12 V supply the bench radio and display boot and operate within limits. There is no audio
(no AVB path to the amplifier) and USB is work in progress. Bench build:
`carplay/gm_pi/docs/07_BENCH_TEST_GUIDE.md` (GM_research).

CAN 5 (X6 p9/10) has two roles on the same wires: in-vehicle it is the amplifier control link to
T3; on the bench tooling the emulator board uses it as the power-on/communication CAN to bring the
radio up. It is one circuit with two uses.

### 1.6 X7 / X8 connector identity

X7 (display) and X8 (USB) are the radio's only 12-way HSAL-2 ports. Both are 12-way male 2.0 mm
HSAL-2 with identical shell, gender and footprint. The PCB carries two identical female HSAL-2
12-way receptacles. Only the keying color distinguishes them (GY = display, BK = USB; OEM P/N
13511515 vs 13545174); keying alone prevents cross-mating.

## 2. Rear-Panel Layout (left to right, as installed)

```
[FAKRA×2]  [black wide     [black       [gray        [gray Stac64    [gray Stac64   [FAKRA×4]
 stacked    ~40-way         shrouded     shrouded      multi-bay       multi-bay      2×2
 pair       header]         fine-pitch]  fine-pitch]   ~56-way]        ~56-way]       block]
```

| # | Physical connector | Function | Conf. |
|---|--------------------|----------|:-----:|
| 1 | 2× single FAKRA, stacked (brown, beige) | RF/coax group A (§3) | [I] |
| 2 | Wide black low-profile header (~40-way, Molex Stac64 family) | Secondary vehicle-signal I/O (discretes, mic, controls) | [I] |
| 3 | Black shrouded fine-pitch (12-way HSAL-2) | USB (X8) | [C] |
| 4 | Gray shrouded fine-pitch (12-way HSAL-2) | FPD-Link III display (X7) | [C] |
| 5 | Large gray Stac64 multi-bay (~56-way) | Main power / ground / CAN / Automotive Ethernet / controls | [C] |
| 6 | Large gray Stac64 multi-bay (~56-way) | Second bay (CAN ± and backup lamp when sparsely populated) | [C] |
| 7 | 4× single FAKRA, 2×2 (black, ivory, blue, yellow) | RF/coax group B (§3) | [I] |

The photo-derived positions for #3/#4 were ambiguous (color code vs pin count). The IOK end views
resolve them: both are 12-way HSAL-2, and the board silkscreen labels the footprints `LVDS`
(grey, X7) and `USB2.0` (black, X8). Details in [`display.md`](display.md) and
[`usb.md`](usb.md).

## 3. FAKRA / Coax Connectors (USCAR-18 keyed)

Code-to-signal mapping is [C] from schematics. The assignment of a signal to a physical jack
(left or right group) is [I] from housing colors.

| Code | Color | Signal | Notes |
|------|-------|--------|-------|
| BK | Black | AM/FM antenna | A second black coax carries RR vision-camera video in some variants |
| CU | Curry | SDARS / SiriusXM antenna | |
| BU | Blue | GPS/GNSS antenna | |
| GN | Green | DAB antenna | |
| BG | Beige | Wi-Fi antenna | Broadcom Wi-Fi module (`dhd` driver) |
| OG | Orange | Camera coax video → Video Processing Module / around-view | FPD-Link III RX at the DS90UB954-Q1 (see [`display.md`](display.md) §6) |

## 4. Stac64 Signal / Power / Network Headers

Circuit names and numbers are [C] from service diagrams. Cavity numbers vary by variant.

### 4.1 Power and ground

| Circuit | Wire (example) | Notes |
|---------|----------------|-------|
| Battery positive | RED/YEL 2340, or dual RED/GRY 28xx | Heavy gauge; single or dual feed by variant |
| Signal ground | BLK/WHT 1051 | Multiple; e.g. G200 (right kick panel) |

### 4.2 Bus and network

| Circuit | Wire | Notes |
|---------|------|-------|
| AUTOSAR CAN (+) | BLU/WHT | GM VIP/SDV1-GB, 29-bit; CAN 5 series |
| AUTOSAR CAN (−) | BLU/YEL | Twisted pair with (+) |
| Ethernet Bus 2 ± | YEL / BLU (4757/4758) | Automotive Ethernet (BroadR-Reach) via the on-board switch: BCM89551 on the photographed MY22/DV unit, Marvell 88Q5050 on the live Y181 radio — board variant, same spec; confirmed 2026-11-12 |
| Ethernet Bus 4 ± | BRN / GRY (7211/7210) | Same |
| Ethernet Bus 6 ± | YEL / GRN (7215/7214) | Same |

A sparsely populated large header is normal. On the test vehicle X6 populates only CAN 5 ±
(p9, p10) and backup lamp control (p13) in a 29-way shell; GM loads only the cavities a trim
needs. Identify power by wire gauge (heavy red/black = power; thin twisted pair = CAN).

### 4.3 Controls and audio-adjacent discretes

| Circuit | Wire | Notes |
|---------|------|-------|
| Backup lamp control | GRN/WHT 24 | To exterior lighting |
| Radio switch power / buttons / volume ± | BRN/WHT, VIO/WHT, BLU, GRY/BRN | Steering-wheel / panel switch pack |
| Display 5 V reference / low reference | BLU/RED, BLK/WHT | Display power/reference (panel is remote) |
| Display LCD enable / backlight enable / backlight dimming | GRY/BLU, GRY/VIO, BLU/GRN | [?] BBM labels. The live backlight path is in-band over the FPD-Link I2C (serializer → panel register `0x20`, write-gated by GHS; `video/display_subsystem.md`). These wires may be a secondary enable or have another function; unconfirmed until traced to a schematic net. |
| Radio switch dimming control | BLU/GRY | |
| Cell-phone / voice-recognition mic | BLU (655/5149), BLK/BRN (654/5152), VIO/YEL 7043, BLU/BLK 7044 | Mic pairs |

### 4.4 Speaker outputs (variant dependent)

| Configuration | Wiring |
|---------------|--------|
| *Sound Systems – Low Level* | LF/RF/LR/RR ± driven directly by the radio (199 GRN, 201 BLU, 200 YEL, 115 BLU/BLK, 118 BRN/BLU, 117 YEL/BLK, 46 WHT) |
| *Sound Systems – Mid/High W/ Amplifier* (test vehicle, Bose) | No speaker-level output from the radio. Audio leaves as AVB over Automotive Ethernet to the external amplifier (see [`audio.md`](audio.md)). |

## 5. Verification Status

| Item | Status |
|------|--------|
| Coax code → signal (AM/FM/XM/GPS/DAB/Wi-Fi/video) | [C] service diagrams |
| Stac64 power/CAN/Ethernet circuit names | [C] service diagrams |
| IOK coax designators (X2 GPS, X3 XM, X9 video, X10 Wi-Fi) and OEM P/Ns | [C] ALLDATA IOK connector views |
| Cavity numbers for IOK X5/X6/X11 | [C] ALLDATA per-cavity |
| X7 = display, X8 = USB | [C] board silkscreen + ALLDATA |
| X11 p1/2 function | [?] open (§1.3) |
| Coax-group jack assignment (left/right), Stac64 bay roles | [I] photo |

## 6. Designator Cross-Reference (variant dependent)

The same X-number is reused for different connectors between harness variants. Indicative only.

| Designator | Typical contents |
|------------|------------------|
| X1 | AM/FM coax (BK); or main power/control bay |
| X2 | GPS coax (BU); or speaker + mic bay |
| X3 | XM coax (CU); or Ethernet Bus 2 |
| X4 | DAB coax (GN); or combined LVDS/USB |
| X5 | RR vision-camera coax (BK); or 29-way signal/mic bay |
| X6 | AM/FM coax; or AUTOSAR CAN + backup-lamp bay |
| X7 | Display LVDS/FPD-Link (GY); or DAB coax |
| X8 | USB serial data (BK); or Wi-Fi coax (BG) |
| X9 | Video Processing Module coax video (OG) |
| X10 | Wi-Fi coax (BG) |
| X11 | Ethernet Bus 2/4/6 ± bay |

## 7. Sources

- Rear-panel photo of the test unit (2024 Silverado 2500 HD LTZ, RPO IOK); PCB photos (X7/X8
  silkscreen, silicon markings).
- ALLDATA Component Connector End Views (CarId 65566): A11 X2/X3/X5/X6/X7/X8/X9/X10/X11, T3 Audio
  Amplifier X1–X4, X92IP USB 2-Port Receptacle X1–X3.
- ALLDATA Radio-Navigation System Schematics (IOK): *Radio Power/Ground/Serial Data/Mic/Subsystem
  References*, *Antennas*.
- Factory RPO list (`RPO Codes.pdf`).
- GM Electrical Body Builder Manual, 2024 Silverado 2500/3500HD
  (`24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`, 1028 pp).
- Molex HSAutoLink II (HSAL2) documentation.
- [`platform/ethernet_networking.md`](../../platform/ethernet_networking.md),
  [`platform/vehicle_network.md`](../../platform/vehicle_network.md),
  [`platform/ota_programming_roles.md`](../../platform/ota_programming_roles.md).
