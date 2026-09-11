# GM Info 3.7 (gminfo37) — A11 Radio / CSM Module: Rear-Panel Connector Map

Companion to [`teardown.md`](teardown.md). Teardown covers what is **on the board**; this doc
covers what **plugs into the back** — the external harness connectors, FAKRA/coax antenna and
video feeds, the FPD-Link display link, USB, and the Automotive-Ethernet / power / CAN Stac64
headers.

**Source basis:** physical rear-panel photo of a test unit + three GM service wiring diagrams
(*Sound Systems – Low Level*, *Sound Systems – Mid/High Level W/ Amplifier*, *Computer Data
Lines*), cross-referenced to [`teardown.md`](teardown.md) and
[`platform/networking.md`](../platform/networking.md).
Compiled 2026-07-01.

> **Confidence key:** **[C]** confirmed against schematic circuit names/numbers or teardown
> silicon · **[I]** inferred from FAKRA color convention / pin count / harness shape (verify with
> a meter or the vehicle-specific service pinout). GM issues several harness variants for this
> radio; connector designators (`X1`…`X11`) and which cavities are populated differ by RPO/trim,
> so **locate connectors by function, not by X-number.**

---

## Module Identity (this connector set)

| Field | Value |
|-------|-------|
| Platform | gminfo37 (GM Info 3.7), Harman/Samsung |
| ECU address | `0x80` (A11 Radio) |
| GM Service P/N | 3765210 |
| Harman Assembly P/N | 91.UMAF2HG.GS6FAAG |
| HWID | ZQ68GEC80317, EC-Index 20 |
| Vehicle (test unit) | 2024 Chevrolet Silverado (ICE), RPO **IOK** (Infotainment 3 Premium, 13.4″, Google built-in) |
| Platform / EE arch | GM **T1XX-HD** / **Global B (VIP / SDV1-GB)** |
| CAN | GM VIP/SDV1 (GB), CAN 2.0 29-bit · Req `0x14DA80F2` / Rsp `0x145AF280` (HS-CAN, dedicated tester F2 — per `A11_CSM_x80.Txt`). The generic OBD tester address F1 (`0x14DA80F1` / `0x145AF180`) also reaches ECU 0x80 and is what the DPS bench read logs use (confirmed: GM_research/diagnostics/gm_dps/DPS_All_Module_Read/.../GCI_*.txt). |

---

## Build RPO Manifest (this vehicle — 2024 Silverado 2500 HD LTZ)

Anchors every "variant-dependent" claim below to real option codes. **Source:** full factory RPO
list for this VIN (`RPO Codes.pdf`) + ALLDATA vehicle profile CarId 65566.

| RPO | Meaning | Anchors |
|-----|---------|---------|
| **IOK** | Radio Infotainment 3.X Mid/High HMI, Enhanced Connectivity 2.0, Voice Recognition | This module; picks the IOK connector variant below |
| **UQA** | Speaker system **premium audio, branded amplifier** (Bose) | Audio path = AVB Ethernet → external amp (§Audio); radio drives **no** speakers |
| **URD** | Infotainment display TFT, **13.4″, 2400×960** | Confirms panel = Chimei Innolux DD134IA-01B ([`teardown.md`](teardown.md)) |
| **UV2 / UVN / TRG** | 360 mono HD vision / aux cargo-bed cam / trailer inside-rear view | FPD-Link camera feeds → OG coax **X9** → DS90UB954 deserializer |
| **U2K** | Digital audio S-Band (SiriusXM) | CU coax **X3** |
| **U73** | Fixed radio antenna | AM/FM (BK) coax |
| **UE1** | OnStar | Gates X5 pin9 VR/telematics-mic (`Option IOK+UE1`) — **proven populated** |
| **VV4** | Mobile internet connectivity (Wi-Fi hotspot) | BG coax **X10** |
| **PPW** | Wireless phone projection | `projection/` (wireless CarPlay/AA) |
| **UBC / UBI / UBJ** | USB armrest dual (chg+data) / rear floor-console dual (chg) / IP-lower dual (chg+data) | Destinations for USB **X8** (§USB) |
| **K4C** | Inductive wireless charger | — |
| **IVN** | Virtual cockpit: none, uses radio family | Cluster driven by radio family |
| **L8T / MKM / GF9 / F48 / NQH** | 6.6L gas · 10-spd · LTZ · 4WD · 2-spd transfer case | Matches ALLDATA vehicle folder |

---

## Authoritative IOK Connector Table (ALLDATA, per-cavity — [C])

The rear-panel layout below is the *physical* map from a bench photo (positions **[I]**). This
table is the **GM service pinout for RPO IOK specifically** — connector designators, OEM part
numbers, and cavity assignments are **[C]** from ALLDATA "Component Connector End Views" for this
VIN. Where a designator here disagrees with the photo-derived `X#` cross-reference at the bottom,
**this table wins.** (Coax connectors list a single summary function; multi-way connectors list
occupied cavities.)

| Conn (IOK) | OEM P/N | Service P/N | Type / housing | Signal(s) |
|------------|---------|-------------|----------------|-----------|
| **X2** | 33340311 | by cable | 1-Way F Coax **(BU)** | GPS/GNSS antenna |
| **X3** | 33340318 | by cable | 1-Way F Coax **(CU)** | SiriusXM / SDARS (+HD) antenna |
| **X5** | 35364134 | 13534974 | 29-Way F 0.5 NANO / 1.2 MCON stAK50h **(BK)** | Battery+ (p1, 2340 RD/YE), Signal Gnd (p3, 1051 BK/WH), LR Spkr[-] (p8, 116) †, cell-mic + VR-mic (p9/10, 655/5149, 654/5152; `Opt IOK+UE1`) |
| **X6** | 35364137 | 13534971 | 29-Way F 0.5 NANO / 1.2 MCON stAK50h **(GY)** | Speaker-level outs (p1-6: LR+ 199, LF1+ 201, RF−1 117, RR− 115, LF−1 118, RF1+ 200) — **base/U95-UQF variant only, NOT wired on this UQA truck** † |
| **X7** | 13511515 | by cable | **12-Way M 2.0 HSAL-2 (GY)** | Infotainment display — FPD-Link III ("LVDS") |
| **X8** | 13545174 | by cable | **12-Way M 2.0 HSAL-2 (BK)** | USB serial data → console USB receptacle(s) |
| **X9** | 33340320 | by cable | 1-Way F Coax **(OG)** | Video Processing Module coax video (cameras) |
| **X10** | 33340317 | by cable | 1-Way F Coax **(BG)** | Wi-Fi antenna |
| **X11** | 35068239 | 13529935 | 12-Way F 050 CTS **(BK)** | Ethernet Bus 2 ± (p3/4, 4758 YE / 4757 BU), **Ethernet Bus 6 ± (p8/9, 7215 YE / 7214 GN → Bose amp)**, Ethernet Bus 4 ± (p11/12, 7211 BN / 7210 GY) |

† **X5/X6 speaker-level cavities are the non-amplified (U95-UQF) usage shown in the connector
superset.** This UQA truck routes audio digitally (see §Audio) — the radio's speaker pins are not
the active path. Confirmed by the `Speakers (UQA)` vs `Speakers (U95-UQF)` schematic split.

### Connector-type note: X7 (display) and X8 (USB) are the *same* connector, keyed
These are the radio's **only two** 12-way HSAL-2 high-speed data ports. Both are **12-Way Male
2.0 mm HSAL-2** — identical mechanical shell, gender, and footprint. X7 (grey) is the confirmed
FPD-Link III display link, so **X8 is USB by elimination** — consistent with its BK keying and the
ALLDATA "USB Serial Data" function. The **only** differences are the keying **color (GY = display,
BK = USB)** and the resulting OEM P/N (13511515 vs 13545174). On the PCB there are two physically identical **female HSAL-2 12-way**
receptacles distinguished solely by GY/BK keying; that keying is the *sole* thing preventing a
USB cable from mating the display header (or vice-versa) — mechanically they would otherwise fit.
GM's rear-panel/teardown view could not name the family; the IOK connector view pins it exactly.

---

## Rear-Panel Layout (left → right, as installed)

```
[FAKRA×2]  [black wide     [black       [gray        [gray Stac64    [gray Stac64   [FAKRA×4]
 stacked    ~40-way         shrouded     shrouded      multi-bay       multi-bay      2×2
 pair       header]         fine-pitch]  fine-pitch]   ~56-way]        ~56-way]       block]
```

| # | Physical connector | Function (this unit) | Conf. |
|---|--------------------|----------------------|:----:|
| 1 | 2× single FAKRA, stacked (brown + beige) | RF/coax group A — see FAKRA table | [I] |
| 2 | Wide black low-profile header (~40-way, Molex Stac64 family) | Secondary vehicle-signal I/O (discretes, mic, controls) | [I] |
| 3 | Black shrouded fine-pitch (~12-pin) | Display FPD-Link III **or** USB — see note below | [I] |
| 4 | Gray/natural shrouded fine-pitch (~6-pin) | USB **or** display FPD-Link III — see note below | [I] |
| 5 | Large gray Stac64 multi-bay (~56-way) | Main power / ground / CAN / Automotive-Ethernet / controls | [C] |
| 6 | Large gray Stac64 multi-bay (~56-way) | Second main bay (CAN± + backup-lamp when sparsely populated) | [C] |
| 7 | 4× single FAKRA, 2×2 (black, ivory, blue, yellow) | RF/coax group B — see FAKRA table | [I] |

---

## FAKRA / Coax Connectors (USCAR-18 keyed)

GM service diagrams name each coax by a 2-letter color/keying code. Mapping of code → signal is
**[C]** from the schematics; which physical jack (left group vs right group) carries which is
**[I]** from observed housing colors.

| Code | Color | Signal | Notes |
|------|-------|--------|-------|
| `BK` | Black | AM/FM antenna | Also a *second* black coax carries **RR vision-camera video** in some variants — two distinct black feeds |
| `CU` | Curry | SDARS / SiriusXM (XM) antenna | |
| `BU` | Blue | GPS / GNSS antenna | |
| `GN` | Green | DAB antenna | |
| `BG` | Beige | Wi-Fi antenna | Broadcom BCM Wi-Fi module (`dhd` driver) |
| `OG` | Orange | Camera coaxial **video** → Video Processing Module / around-view | FPD-Link III RX at the deserializer (see Display/Camera) |

**Camera video path is FPD-Link III, not analog composite** — the coax video feeds land on the
**TI DS90UB954-Q1** deserializer hub on the PCB ([`teardown.md`](teardown.md) §Display Signal
Chain). GHS drives the backup/surround overlay directly, so camera works even during Android
reboot.

---

## Stac64 Signal / Power / Network Headers (#5, #6, #2)

The large multi-bay Stac64 housings carry the vehicle harness. Circuit names/numbers below are
**[C]** from the service diagrams; cavity numbers vary by variant.

### Power & ground
| Circuit | Wire (example) | Notes |
|---------|----------------|-------|
| Battery positive voltage | `RED/YEL 2340`, or dual `RED/GRY 28xx` | Heavy gauge; single or dual feed by variant |
| Signal ground (SIG GND) | `BLK/WHT 1051` | Multiple; e.g. G200 (right kick panel) |

### Bus / network
| Circuit | Wire | Notes |
|---------|------|-------|
| AUTOSAR CAN bus (+) | `BLU/WHT` | GM VIP/SDV1-GB, 29-bit — 5-series data |
| AUTOSAR CAN bus (−) | `BLU/YEL` | Twisted pair with (+) |
| Ethernet Bus 2 (±) | `YEL` / `BLU` (4757/4758) | Automotive Ethernet (BroadR-Reach via BCM89551) |
| Ethernet Bus 4 (±) | `BRN` / `GRY` (7211/7210) | " |
| Ethernet Bus 6 (±) | `YEL` / `GRN` (7215/7214) | " |

> **A sparsely-populated big Stac64 header is normal.** In one observed variant, connector #6
> carries only **AUTOSAR CAN (+), AUTOSAR CAN (−), and BACKUP LAMP CTRL** — three thin wires in a
> ~56-way shell (GM loads only the cavities a trim needs). A big connector with 3 wires is *not*
> necessarily power; confirm by gauge (heavy red/black = power; thin twisted pair = CAN).

### Controls & audio-adjacent discretes
| Circuit | Wire | Notes |
|---------|------|-------|
| Backup lamp ctrl | `GRN/WHT 24` | To exterior-lights system |
| Radio SW power/buttons/vol±  | `BRN/WHT`, `VIO/WHT`, `BLU`, `GRY/BRN` | Steering-wheel / panel switch pack |
| Infotainment display 5 V ref / low ref | `BLU/RED`, `BLK/WHT` | Display power/reference (panel is remote) |
| Display LCD enable / backlight enable / backlight dimming | `GRY/BLU`, `GRY/VIO`, `BLU/GRN` | |
| Radio switch dimming ctrl | `BLU/GRY` | |
| Cell-phone mic / voice-recognition mic (± / sig / low-ref) | `BLU`(655/5149), `BLK/BRN`(654/5152), `VIO/YEL 7043`, `BLU/BLK 7044` | Mic pairs |

### Speaker outputs — **variant-dependent**
| Config | Speaker wiring |
|--------|----------------|
| *Sound Systems – Low Level* | LF/RF/LR/RR ± driven **directly from the radio** (e.g. `199 GRN`, `201 BLU`, `200 YEL`, `115 BLU/BLK`, `118 BRN/BLU`, `117 YEL/BLK`, `46 WHT`) |
| *Sound Systems – Mid/High W/ Amplifier* (**this truck — Bose**) | **No speaker-level output from the radio.** Audio leaves the radio as **AVB over Automotive Ethernet** to the external Bose amp; the amp drives the speakers. See below. |

---

## Audio Architecture — Bose (Mid/High W/ Amplifier)

This unit's truck has the **Bose amplifier**, so it follows the *Mid/High W/ Amplifier* diagram.
The amp is a **networked AVB endpoint, not analog-driven** ([`platform/networking.md`](../platform/networking.md),
`research/GM_REMOTE_ACCESS_ANALYSIS.txt`):

```
SAF7751 tuner/DSP → A3960 SoC → Intel I210 GbE → BCM89551 Eth switch
   → (Automotive-Ethernet AVB pair, in the Stac64 harness) → Bose amp @ 192.168.1.103 (TDF8532) → speakers
```

- Amp presence is calibrated: **`External Amp = Present`, `AMPCAL=3`** (`research/session_logs/security_assessment_20DEC25.txt`).
- VIP boot order includes **`AMP_MGR_SWC`** (Audio Amplifier Manager).
- Implication for the harness: on this truck the speaker ± pairs live on the **Bose amp's**
  connector, not the radio's. The radio side uses an **Ethernet Bus ± pair** for the digital
  audio transport. [C]

### Confirmed radio ↔ amp trace (ALLDATA UQA schematic) — [C]
The **T3 Audio Amplifier** is the CSM in this truck's audio chain, confirmed by RPO **UQA**. The
ALLDATA *Audio Amplifier Power, Ground and Serial Data (UQA)* schematic + the T3 connector end
views give the exact wires — no longer inferred from silicon:

**Digital link (radio → amp):**

| Circuit | Wire | Radio side | Amp side | Role |
|---------|------|-----------|----------|------|
| **Ethernet Bus 6 [+]** | **7215 YE** | A11 **X11 pin 8** | T3 **X3** | AVB audio transport |
| **Ethernet Bus 6 [−]** | **7214 GN** | A11 **X11 pin 9** | T3 **X3** | AVB audio transport |
| AUTOSAR CAN 5 [+] SD | 4985 BU/WH | (VIP CAN) | T3 X3 | Amp control / serial data |
| AUTOSAR CAN 5 [−] SD | 4984 BU/YE | (VIP CAN) | T3 X3 | Amp control / serial data |

So the AVB audio pair the repo previously described generically **is Ethernet Bus 6 (7215/7214),
radio X11 ↔ amp T3 X3.** Amp power: T3 X1/X4 pin **Battery+ (3740 RD/YE)**, **Signal Gnd (1051
BK/WH)**.

**Amp-side pinout (T3, drives ALL speakers — [C], circuit numbers from ALLDATA T3 end-views):**

| T3 conn | OEM P/N | Housing | Pins (circuit) |
|---------|---------|---------|----------------|
| **X1** | 33223792 | 8-Way F 2.8 OCS (BK) | p1 Sub+ (346), p2 RF1+ (200), p3 LF1+ (201), p4 **Batt+** (3740), p5 Sub− (1794), p6 RF−1 (117), p7 LF−1 (118), p8 **Gnd** (1051) |
| **X4** | 33223792 | 8-Way F 2.8 OCS (BK) | **Identical table to X1** (same OEM P/N; source does not explain the duplication — one is likely a second housing/mating half, unconfirmed in-vehicle) |
| **X2** | 15512506 | 16-Way F 1.5 OCS (BK) | LF-mid ± (1857/1957), RF-mid ± (1853/1953), LR ± (199/116), RR ± (46/115), Front-Center ± (1860/1960) |
| **X3** | 35016343 | 16-Way F 0.64 OCS (BK) | **Eth Bus 6 ±** p1/2 (7215/7214), **ANC mic 1** sig/fb p5/13 (3005/3008), **AUTOSAR CAN 5 ±** p11/12 (4985/4984) |

This closes the earlier reconciliation: **radio drives no speakers on a UQA truck; the amp does.**
The radio's X6 speaker-level cavities belong to the base *U95-UQF* variant only.

---

## Display Link (FPD-Link III — GM labels it "LVDS")

- Silicon: **TI DS90UH949-Q1** FPD-Link III **serializer** on the PCB → remote **Chimei Innolux
  DD134IA-01B**, 2400×960 @ 60 Hz, ~13.4″ panel. [C] ([`teardown.md`](teardown.md))
- GM service diagrams label this "**LVDS / INFOTAINMENT DISPLAY SIG**" — that is FPD-Link III
  serialized over one cable, **not** classic parallel LVDS. [C]
- Display *power/enable/backlight* control lines ride the Stac64 harness (see Controls table);
  the *video* rides the dedicated display connector.

### The display is a discrete module: A22 Radio Control (center-stack HMI) — [C link] / [I role]
The 13.4″ panel is not a dumb display hung off the radio — GM designates it **`A22 Radio
Control`**, a separate addressable center-stack HMI assembly, fed by the X7 "LVDS" link (really
FPD-Link III off the DS90UH949 serializer). The GM Body Builder Manual gives a **point-to-point**
match:

| Circuit | Function | A11 Radio **X7 (IOK)** pin | A22 Radio Control **X2 (IOK)** pin |
|---------|----------|----------------------------|-------------------------------------|
| 7853 | Center Stack LVDS Low-Ref | 1 | 1 |
| 7854 | Center Stack LVDS Signal [+] | 2 | 2 |
| 7855 | Center Stack LVDS Signal [−] | 3 | 3 |
| 7847 | Center Stack LVDS **2** Low-Ref | 4 | 6 |
| 7848 | Center Stack LVDS **2** Signal [+] | 5 | 4 |
| 7849 | Center Stack LVDS **2** Signal [−] | 6 | 5 |

- Those six circuits appear at **only** these two connectors in the entire 1028-page BBM → a
  dedicated A11↔A22 link. A11 X7 (IOK) is a **12-Way HSAL-2 (GY)** OEM `13511515`; A22 X2 is a
  **6-Way M HSAL-2 (BK)** OEM `13522802`. **Two** LVDS pairs (LVDS + "LVDS 2") carry the 2400×960
  panel (dual-link).
- A22 **X1** (8-Way Mini-50, OEM `35068228`) = power only: Batt+ (p1, 1340 RD/WH), Signal Gnd
  (p8, 1051 BK/WH). A22 is on fuse **F30** (SDM/AOS, 10A).
- **Role is inferred** (LVDS video in + name "Radio Control"): the BBM has no prose stating A22 =
  the touchscreen/HMI. But the dedicated Center-Stack-LVDS link from the head unit is strong
  evidence it's the remote display/HMI assembly housing the Chimei panel. See
  [`teardown.md`](teardown.md) §Display Signal Chain (DS90UH949 serializer → this panel).

### RESOLVED: which shrouded connector is display vs USB — [C]
Previously flagged unresolved (color-code vs pin-count conflict). The IOK connector views settle
it and **refute the earlier pin-count inference**: both connectors are **12-Way M 2.0 HSAL-2**
(neither is 6-pin), so color-key decides cleanly:

- **X7 GY (gray)** = **FPD-Link III display** (OEM 13511515)
- **X8 BK (black)** = **USB serial data** (OEM 13545174)

The "gray ~6-pin USB" hypothesis was wrong — gray is the 12-way display link. No continuity
check needed; see the Authoritative IOK Connector Table above.

**Board silkscreen confirms it directly (PCB photo) — [C]:** the two HSAL-2 footprints are
silk-labeled **`LVDS`** (grey, X7) and **`USB2.0`** (black, X8), each numbered **6 … 1**. So the
assignment is now proven on the board, not just inferred from ALLDATA color-keying — and X8 is
explicitly **USB 2.0**. The **6-contact silkscreen numbering** reconciles the "12-Way" housing:
the radio header is a 12-way HSAL2 shell (2 rows of 6), but **the vehicle harness populates only
6 positions — one row** (confirmed on-vehicle, and the ALLDATA X8 end-view draws all 12 cavities
with only 6 populated). Of those 6, **USB uses 4** (VBUS/D+/D−/GND); the other 2 are ID/shield and
the remaining 6 header positions never mate. Net: **one USB 2.0 port, one D+/D− pair, not two
lanes.** (Same photo confirms the neighbouring silicon:
Intel Atom **A3960** Apollo Lake, Broadcom **BCM89551** Ethernet switch, TI **DS90UB954-Q1**
`AVG3 G4` deserializer — see [`teardown.md`](teardown.md).)

---

## USB

- **USB serial data** connector at the radio = **X8, 12-Way M 2.0 HSAL-2 (BK)**, OEM 13545174.
  Separate from the display link (X7). [C]
- Feeds the console/center USB port(s); GM service cable **PN 23103558** ("USB Data Cable HMI to
  Center") is one HMI→center run. [C]
- On-board debug USB-UART (Microchip MCP2200 → `/dev/ttyACM1`) is internal, not a rear harness
  connector — see [`teardown.md`](teardown.md).

### The three USB receptacles (ALLDATA + owner field data) — [C]
This truck has **three** front USB/charge receptacles, each a Type-A + Type-C pair. Two carry
data, one is charge-only — matching the RPO codes and the owner's bench observations:

| Receptacle | RPO | Location | Data? | ADB | Role (owner) |
|-----------|-----|----------|-------|-----|--------------|
| **X83B** Audio/Video Receptacle | **UBC** | Floor console | **Yes** (2× Mini-B, power) | **Yes — Type-C via OTG** | **Main / service** |
| **X92IP** USB 2-Port Receptacle | **UBJ** | Instrument-panel lower | Yes (2× Mini-B, power) | No | Secondary |
| **X92CD** Dual Charge-Only Receptacle | **UBI** | Floor console rear | **No** (power/dimming/gnd only) | No | Charge-only |

> **Not equipped on this truck:** ALLDATA also lists a *fourth* USB receptacle **`X92CF` USB
> 2-Port – Floor Console Front (RPO `UBD`)**, fed by a separate fuse **F26DR 10A** ("SEO/USB
> CHARGE"). This VIN's RPO set has **UBC/UBI/UBJ only — no UBD**, so X92CF is absent. Listed for
> completeness in case a future build carries it. (No connector view/schematic for X92CF exists in
> the archive.)

Both data receptacles enumerate USB drives and phones into AAOS; **only the floor-console (X83B)
Type-C exposes ADB** (owner-confirmed). Note the owner's *functional* "main vs secondary" (by ADB)
is the **opposite** of the *electrical* order: the D07 trace shows **X92IP (IP) is upstream**
(directly on the radio) and **X83B (console) is downstream** of the IP hub — see topology below.
So X83B (UBC) = data+ADB "main" by function but the downstream node by wiring; X92IP (UBJ) =
data-only secondary but the upstream hub; X92CD (UBI) = power-only.

Each data receptacle is an **active, separately-powered hub** with three connectors (an internal
`A90 Logic` controller). Connector detail:

| Recept. | Conn | OEM P/N | Type | Carries |
|---------|------|---------|------|---------|
| **X83B** (console, main) | X1 | 2035363-4 | 6-Way F 0.64 Gen-Y (BK) | Power/control — Battery+, LED dimming, Signal Gnd |
| | X2 | 13890926 | 5-Way M 2.0 Mini-B USB (GY) | USB serial data |
| | X3 | 13890925 | 5-Way M 2.0 Mini-B USB (BK) | USB serial data |
| **X92IP** (IP, secondary) | X1 | 13920633 | 6-Way F 0.64 Gen-Y (BK) | Power/control — Battery+ (2640 RD/VT), LED dimming (6817 YE), Signal Gnd (1051 BK/WH) |
| | X2 | 111014-9501 | 5-Way M 2.0 Mini-B USB (GY) | USB serial data |
| | X3 | VP000109 | 5-Way M 2.0 Mini-B USB (BK) | USB serial data |
| **X92CD** (rear, charge-only) | X1 | 2035363-4 | 6-Way F 0.64 Gen-Y (BK) | LED dimming + Ground only — **no USB** |

### USB topology: radio → active-hub receptacles, daisy-chained (ALLDATA *Auxiliary Inputs (D07)*)
Traced directly off the **D07 diagram** (`diagram-01.pdf`). The data path is a **single
IP-first daisy chain** through two active hub receptacles (each an internal `A90 Logic`
controller); power is a **separate** parallel feed from a fuse, not from the radio:

```
DATA (one radio USB link, daisy):
  A11 Radio X8 (BK) ──USB──▶ X92IP X2 (GY)  [IP receptacle IN, UBJ]  ── A90 Logic hub
  X92IP X3 (BK) [OUT, UBC] ──USB──▶ inline X226 ──▶ X83B X2 (GY)  [console receptacle IN] ── A90 Logic hub
     → X92IP is UPSTREAM (directly on the radio); X83B (console) is DOWNSTREAM

POWER (parallel, from fuse — NOT the radio):
  B+ ─▶ F32DR 15A (X51R IP junction block) ─▶ 2640 RD/VT ─┬─▶ X92IP X1 p1
                                        (J304/J337,        └─▶ X83B  X1 p1   (+ X92CD by same pattern)
                                         inline X227 c29 / X210 c59)
  Ground: X92IP/X83B X1 p3 = 1051 BK/WH ─▶ G200 · Dimming: 6817 YE ─▶ each X1 p2
```

- **Each data receptacle is an active hub**, not a socket: internal **`A90 Logic`** powered by
  **`2640` Battery+ (fused F32DR 15A)** + **`1051` ground (G200)** + **`6817` dimming**. No power →
  hub dead → **a plugged-in device does nothing** = the direct cause of the bench-break-out failure.
- **The two Mini-B on X92IP are IN (X2 GY, from radio) and OUT (X3 BK, daisy to console)** — the
  `A90` hub fans the IN link to its own Type-A + Type-C and forwards OUT to X83B downstream.
- **The radio uses ONE USB link for the whole chain** (X8 BK → X92IP X2). This D07 sheet shows no
  second radio USB link; X8 is a 12-way shell but only one USB pair is consumed here. **On-vehicle +
  board silkscreen confirm:** the X8 footprint is labeled **`USB2.0`** and numbered **1–6**, and the
  physical harness cable populates only **6 pins** in the 12-way shell (ALLDATA end-view draws 12
  cavities, 6 populated). USB = **4** of those 6 (VBUS/D+/D−/GND) → **a single USB 2.0 port, not
  two lanes.**
- **Power did not come from the radio** — it branches from **fuse F32DR 15A** to all receptacles in
  parallel. (Owner's instinct correct: X8 does not split to both; the *power* is what splits.)
- **X8 (IOK) per-pin pinout is NOT published anywhere found.** Both ALLDATA and the **2024
  Silverado 2500/3500HD Electrical Body Builder Manual** (`24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`)
  list IOK **X8** (OEM `13545174`, 12-Way HSAL-2 BK) as **summary-only** — `USB Serial Data`, no pin
  map. So the exact pin positions of VBUS/D+/D−/GND on *your* X8 are **undocumented** [I].
- **USB signal set + GM circuit numbers (proxy, from the IOR variant) — [C]:** the BBM *does* break
  out USB per-pin on the **IOR** combined connector **`A11 Radio X4 (IOR)`** (OEM `33358813`, 12-Way
  HSAL-2), where LVDS + USB share one shell. This is a **proxy for the signal set, not a map of IOK
  X8's pins**:

  | Pin (IOR X4) | Circuit | Function |
  |-----|---------|----------|
  | 1 / 2 / 3 | 4844 / 4845 / 4846 | Radio LVDS Low-Ref / Signal[+] / Signal[−] |
  | **7** | **7899** | USB Supply Voltage (**VBUS**) |
  | **9** | **7896** | USB [+] (**D+**) |
  | **10** | **7897** | USB [−] (**D−**) |
  | **12** | **7898** | USB Low Reference (**GND**) |
  | 4–6, 8, 11 | — | Not Occupied |

  Confirms the USB is **VBUS/D+/D−/GND, one D+/D− pair → one USB 2.0 lane** (consistent with the
  `USB2.0` silkscreen and the 6-populated-of-12 cable). But **IOK X8 splits LVDS off to `X7`**, so
  its 6-pin cable numbers the four USB conductors differently — the IOR pins 7/9/10/12 do **not**
  necessarily map to the same positions on IOK X8. (An earlier forum figure — contiguous "pins
  7–10 / red-white-green-black" — is likewise not the IOK X8 map; disregard for pin positions.)
- **To get the real IOK X8 pin positions: meter the 6-pin cable.** VBUS ≈ +5 V pad→GND (USB power
  on); D+/D− = the twisted pair into the ESD/choke cluster; GND = pad ~0 Ω to shell. That is the
  only way to pin IOK X8 exactly — no document publishes it.
- **ALLDATA has no per-pin USB anywhere** (full-archive search, 1,242 articles): every schematic
  bundles the four conductors as one opaque `USB Serial Data` net with generic cavity numbers — no
  `D+`/`D−`/`VBUS` labels exist in the dataset. The Upfitter/HSAL2 pinout above is therefore the
  best obtainable pin breakdown; ALLDATA cannot improve on it.
- **Inline `X226` is a real 5-Way Mini-B USB connector** (OEM 13699757 / VP000109) — the daisy pair
  physically passes through a standard USB Mini-B (VBUS/D−/D+/ID/GND). The other inline connectors
  on the D07 sheet, **`X227` (cav29) and `X210` (cav59), carry only the 2640 power feed, not USB** —
  the USB daisy transits X226 alone.

> **ADB mechanism — largely RESOLVED (SoC software role-switch, not a receptacle ID/CC pin).**
> The radio does not become a USB device via the harness or the receptacle — it does so in
> **software at the SoC**. The Apollo Lake **xHCI role-switch** (`intel_xhci_usb_sw` role node) plus
> Intel's **Device Authentication Bridge** (`dabridge`, exposing the virtual UDC `dabr_udc.0`) flips
> a host port into **device mode**: `setprop vendor.sys.usb.role device` → `usb_otg_switch.sh d`,
> peripheral↔host reversal via `/sys/bus/usb/drivers/dabridge/bridgeport`. Documented in
> [`../analysis/platform_faq.md`](../analysis/platform_faq.md) (§dabridge/UDC) and
> [`../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md).
> So ADB = the radio's own USB controller entering gadget mode; the receptacle's ID/CC pins are
> **not** what enable it (they can't — see §"why that doesn't fully explain ADB").
>
> **RESOLVED model (owner bench data, Sep 2026).** Field testing: ADB works over USB on the
> **floor-console Type-C ONLY**; it worked **even with the receptacle externally unpowered (no
> 12 V)**; the same port also hosts USB drives/phones normally; and it requires an **OTG cable**
> (a plain C-to-C does not enumerate ADB). This locks the architecture:
> - **The ADB Type-C is NOT behind the A90 hub.** ADB with no 12 V ⇒ the hub is dead yet ADB runs ⇒
>   the port is on a **direct dual-role link from the radio to that connector, bypassing the hub.**
>   (Confirms the "separate DRD link" hypothesis; kills the hub-downstream reading for this port.)
> - **Dual-role, same connector:** host mode (drives/phones — radio supplies VBUS from its own
>   controller) and device mode (ADB — PC supplies VBUS). Neither needs the receptacle's 12 V; that
>   12 V only powers the A90 hub's Type-A ports + charging.
> - **OTG-cable requirement ⇒ ID/CC role signaling.** The OTG cable asserts the ID/CC condition the
>   firmware watches, triggering the software role-switch to device (`vendor.sys.usb.role=device`).
>   A plain C-to-C doesn't assert it → no flip → no ADB. (The owner's original ID-pin intuition is
>   correct for *this* port.)
> - **Likely wire:** X83B has two Mini-B legs — **X2 (GY)** = host feed from the IP hub daisy;
>   **X3 (BK)** = destination never traced. A Mini-B carries an **ID pin**, so **X83B X3 is most
>   likely the direct dual-role/ID link** from the radio's role-switch root to the Type-C. Only the
>   floor-console receptacle wires this to its Type-C; the IP receptacle's Type-C is hub-only →
>   host-only → no ADB.
> - **Why X8 itself can't do ADB (⚠ unverified inference):** the X8 USB appears to be **VBUS/D+/D−/GND
>   with no ID pin** (from the IOR-X4 *proxy* pinout — not a literal IOK X8 map), so X8 would be a
>   **permanent host** — wiring X8 straight to a PC is host-to-host and should enumerate nothing.
>   The dual-role behaviour needs the **ID pin present on the console link** (X83B X3 Mini-B). This
>   ID-present-vs-absent contrast is the proposed reason only that one port does ADB — **not yet
>   metered on IOK X8**; treat as a working hypothesis.
>
> **Remaining to meter (only unconfirmed step):** does **X83B X3** run to a *separate* radio USB
> connector (the DRD root) rather than the X2/daisy, and is the Type-C CC/ID tied to X3's ID line?
> Confirming that closes the item fully.

**Bench takeaway for USB/ADB access:** power the receptacle hub (**2640 = 12 V + 1051 = gnd**), use
the **floor-console Type-C with an OTG cable** — not a Type-A port, not a single Mini-B data-only
break-out. A different-color data-cable P/N alone won't help if the hub is unpowered or you're on a
host port.

---

## Connector Designator Cross-Reference (variant-dependent)

Designators observed across the three service diagrams. **The same X-number is reused for
different connectors between harness variants** — treat this as indicative only.

| Designator (seen) | Typical contents in the diagram where it appeared |
|-------------------|----------------------------------------------------|
| `X1` | AM/FM coax (BK); in another variant, main power/control bay |
| `X2` | GPS coax (BU); in another variant, speaker + mic bay |
| `X3` | XM coax (CU); in another variant, Ethernet Bus 2 |
| `X4` | DAB coax (GN); in another variant, combined LVDS/USB |
| `X5` | RR vision-camera coax video (BK); or the 29-way signal/mic bay |
| `X6` | AM/FM coax; or AUTOSAR CAN + backup-lamp bay |
| `X7` | Display **LVDS/FPD-Link** (GY); or DAB coax |
| `X8` | USB serial data (BK); or Wi-Fi coax (BG) |
| `X9` | Video Processing Module coax video (OG) |
| `X10` | Wi-Fi coax (BG) |
| `X11` | Ethernet Bus 2/4/6 ± bay |

---

## Verification Status

| Item | Status |
|------|--------|
| Module identity (P/N 3765210, ECU 0x80, RPO IOK) | **[C]** teardown |
| Display link = FPD-Link III (DS90UH949-Q1) | **[C]** teardown silicon |
| Camera video = FPD-Link III (DS90UB954-Q1) | **[C]** teardown silicon |
| Bose amp = AVB Ethernet endpoint @ 192.168.1.103, AMPCAL=3 | **[C]** networking / security_assessment |
| Coax code→signal mapping (AM/FM/XM/GPS/DAB/WiFi/video) | **[C]** service diagrams |
| Stac64 power/CAN/Ethernet circuit names | **[C]** service diagrams |
| Coax designator→signal for IOK (X2 GPS, X3 XM, X9 video, X10 Wi-Fi) + OEM P/Ns | **[C]** ALLDATA IOK connector views |
| #3 vs #4 = display vs USB | **[C] RESOLVED** — board silkscreen `LVDS` (X7) / `USB2.0` (X8); both 12-way HSAL-2 |
| X8 = one USB 2.0 lane (not two): silkscreen `USB2.0`; 12-way shell, harness populates 6 pins, USB uses 4 (VBUS/D+/D−/GND) | **[C]** on-vehicle + PCB photo + ALLDATA end-view |
| Exact cavity numbers for RPO IOK | **[C]** ALLDATA per-cavity (X5/X6/X11 tabulated) |
| Radio↔Bose-amp audio = Ethernet Bus 6 (7215/7214), radio X11 ↔ amp T3 X3 | **[C]** ALLDATA UQA schematic |
| 3 USB receptacles: X83B/UBC (console, data+ADB), X92IP/UBJ (IP, data), X92CD/UBI (rear, charge-only) | **[C]** ALLDATA connector views + owner field data |
| Receptacles are active hubs (`A90 Logic`) needing 2640/1051 power; two Mini-B = IN/OUT daisy legs | **[C]** ALLDATA *Auxiliary Inputs (D07)* |
| Daisy-chain direction = **IP-first**: radio X8 → X92IP (upstream) → X226 → X83B console (downstream); power parallel from fuse F32DR 15A | **[C]** ALLDATA D07 diagram trace |
| ADB device-mode mechanism = SoC xHCI role-switch (`intel_xhci_usb_sw` + `dabridge dabr_udc.0`, `vendor.sys.usb.role=device`) | **[C]** analysis/platform_faq.md, SHELL_ACCESS_ESCALATION_Jun2026.md |
| Which SoC root port (`bridgeport 1-6.x`) physically maps to the console Type-C | **[I] OPEN** — port-mapping detail only |

## Sources
- Rear-panel photo of test unit (2024 Silverado 2500 HD LTZ, RPO IOK).
- **ALLDATA Component Connector End Views (CarId 65566, this VIN)** — per-cavity IOK pinouts for
  A11 Radio X2/X3/X5/X6/X7/X8/X9/X10/X11, T3 Audio Amplifier X1–X4, X92IP USB 2-Port Receptacle
  X1–X3. Authoritative for connector types, OEM/service P/Ns, and cavity assignments.
- **ALLDATA Radio-Navigation System Schematics (IOK)** — *Audio Amplifier Power, Ground and Serial
  Data (UQA)*, *Speakers (UQA)* vs *Speakers (U95-UQF)*, *Radio Power/Ground/Serial Data/Mic/
  Subsystem References*, *Antennas*, *Auxiliary Inputs (D07)*.
- **Factory RPO list for this VIN** (`RPO Codes.pdf`) — build manifest anchoring UQA/IOK/URD/UV2/
  UE1/VV4/UBJ etc.
- GM service wiring diagrams: *Sound Systems – Low Level*, *Sound Systems – Mid/High Level W/
  Amplifier*, *Computer Data Lines*.
- **GM Electrical Body Builder Manual:** `24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`
  (2024 Silverado 2500/3500HD, 1028 pp) — full IOK/IOR connector end-view set + receptacle pinouts.
  **IOK X8 is summary-only here too** (no pin map); the USB signal set + circuits (7899/7896/7897/7898
  = VBUS/D+/D−/GND) come from the IOR proxy connector `A11 Radio X4 (IOR)`, not IOK X8 itself.
- **Community (context / corroboration):** silveradosierra.com "2020 Silverado A11 Radio
  Connections"; gm-trucks.com "USB from aftermarket radio to console". Molex HSAutoLink II (HSAL2).
- **Community / ADB context:** XDA "General Motors Google Built-In – Tinkering" and "ADB on a GM
  infotainment system?" threads (Developer Options → USB Debugging over console USB-C; ADB
  enumeration reported inconsistent — no clean reproducible method).
- **PCB photos of the test unit:** X7/X8 board silkscreen (`LVDS` / `USB2.0`, contacts 1–6); silicon
  markings (Intel Atom A3960, BCM89551, DS90UB954-Q1 `AVG3 G4`, Harman P/N 3765210 / EC-Index 20).
- [`hardware/teardown.md`](teardown.md) — internal silicon (FPD-Link serializer/deserializer,
  I210, BCM89551, TDF8532, SAF7751).
- [`platform/networking.md`](../platform/networking.md) — AVB audio endpoint, internal networks.
- `research/GM_REMOTE_ACCESS_ANALYSIS.txt` — `192.168.1.103 AMP_ETH`.
- `research/session_logs/security_assessment_20DEC25.txt` — `External Amp: Present, AMPCAL=3`.

## See also
- [`platform/vehicle_network.md`](../platform/vehicle_network.md) — vehicle-wide two-plane network map (CAN + Ethernet) these connectors carry.
- [`platform/ota_programming_roles.md`](../platform/ota_programming_roles.md) — module programming / OTA over this network.
