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
| Vehicle (test unit) | 2024 Chevrolet Silverado **2500 HD LTZ** (ICE, 6.6L L8T gas), RPO **IOK** (Infotainment 3 Premium, 13.4″, Google built-in) |
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
| **X5** | 35364134 | 13534974 | 29-Way F 0.5 NANO / 1.2 MCON stAK50h **(BK)** | **As-wired on this vehicle — harness populates only p1/3/9/10/11/12** (radio receptacle has all 29 cavities): Battery+ (p1, 2340 RD/YE), Signal Gnd (p3, 1051 BK/WH), cell-mic + VR-mic (p9/10, 655/5149 BU·GY/YE, 654/5152 BK/BN·BK/GY; `Opt GF2-GF5 / IOK+UE1`), Microphone ± (p11/12, 7043 VT/YE / 7044 BU/BK). **p8 (LR Spkr[-], 116 GN/BK) appears in the ALLDATA superset end-view but is NOT wired here** — confirmed by harness inspection, consistent with UQA (radio drives no speakers) † |
| **X6** | 35364137 | 13534971 | 29-Way F 0.5 NANO / 1.2 MCON stAK50h **(GY)** | **As-wired on this vehicle — harness populates only p9/10/13** (receptacle has all 29 cavities): **AUTOSAR CAN 5 ± (p9/10, 4985 BU/WH / 4984 BU/YE)** — VIP/SDV1-GB 29-bit, amp-control serial data, radio end of the CAN 5 link to the Bose amp (T3 X3); **Backup Lamp Control (p13, 24 GN/WH)**. Speaker-level outs (p1-6/8: LR+ 199, LF1+ 201, RF−1 117, RR− 115, LF−1 118, RF1+ 200, RR+ 46) are in the ALLDATA superset end-view but **NOT wired on this UQA truck** (radio drives no speakers) †. Per ALLDATA X6 end-view + `05_ALLDATA_WIRING_REFERENCE.md §8` [C] |
| **X7** | 13511515 | by cable | **12-Way M 2.0 HSAL-2 (GY)** | Infotainment display — FPD-Link III ("LVDS") |
| **X8** | 13545174 | by cable | **12-Way M 2.0 HSAL-2 (BK)** | USB serial data → console USB receptacle(s) |
| **X9** | 33340320 | by cable | 1-Way F Coax **(OG)** | Video Processing Module coax video (cameras) |
| **X10** | 33340317 | by cable | 1-Way F Coax **(BG)** | Wi-Fi antenna |
| **X11** | 35068239 | 13529935 | 12-Way F 050 CTS **(BK)** | **As-wired on this vehicle — fully populated (all 6 occupied pins wired, unlike sparse X5/X6):** Ethernet Bus 2 ± (p3/4, 4758 YE / 4757 BU → K56 gateway), **Ethernet Bus 6 ± (p8/9, 7215 YE / 7214 GN → Bose amp)**, Ethernet Bus 4 ± (p11/12, 7211 BN / 7210 GY → K73 comm). p1-2/5-7/10 not occupied. **Harness-side mate 13529935 = Delphi/Aptiv drawing 33283033** ("TAXI ASM CONN 12 F CTS 050", 12-way female CTS-050, male-plug shell / female sockets, CPA) — datasheet: [`datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf`](datasheets/Delphi_33283033_TAXI_12way_F_CTS050_A11-X11_mate.pdf) |

† **X5/X6 speaker-level cavities are the non-amplified (U95-UQF) usage shown in the connector
superset.** This UQA truck routes audio digitally (see §Audio) — the radio's speaker pins are not
the active path. Confirmed by the `Speakers (UQA)` vs `Speakers (U95-UQF)` schematic split.

> **Two as-wired datasets — keep them distinct.** The per-pin "as-wired" notes above are the
> **in-vehicle harness** (owner inspection). A **bench** setup using the **OPU Wiring Tester +
> Emulator** (GM 85633185, HMI 3.7-3.8) wires even less: **X5 p1/p3 only** (Battery+/Gnd), **X6
> p9/p10 only** (CAN 5 ±, injected by the tester's emulator board), **X7 LVDS** to the display —
> no X6 p13 backup lamp, no X5 mics, and X11 Ethernet not populated. With a 12 V PSU the radio +
> display boot and are operational within limits (no audio — AVB→amp absent on bench; USB WIP).
> Bench-build detail lives in GM_research `carplay/gm_pi/docs/07_BENCH_TEST_GUIDE.md`.

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

> **A sparsely-populated big header is normal.** This "three thin wires" observation is now
> confirmed to be **X6 as-wired on this vehicle**: only **AUTOSAR CAN 5 + (p9, 4985), CAN 5 − (p10,
> 4984), and Backup Lamp Control (p13, 24 GN/WH)** are populated in the 29-way shell — GM loads only
> the cavities a trim needs (this UQA truck routes audio digitally, so none of the p1-6/8 speaker
> cavities are wired). A big connector with 3 wires is *not* necessarily power; confirm by gauge
> (heavy red/black = power; thin twisted pair = CAN).

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
the radio header is a 12-way HSAL2 shell (**2 rows of 6**), but **both known cables wire only the
bottom row — one port** (owner-confirmed 2026-10-06 on the Molex `87813526` bench cable AND the
in-vehicle harness; the ALLDATA X8 end-view also draws all 12 cavities with only 6 populated). Of
that wired row, **USB uses 4** (VBUS/D+/D−/GND) = one complete USB 2.0 port, one D+/D− pair; the
remaining wired positions are not USB signals. **No CC and no OTG-ID conductor reaches the radio** —
X8 is 4-wire, so the radio cannot sense role/orientation electrically (the earlier "+ ID/CC-sense"
wording was wrong) [FW/HW, USB_ADB_SESSION_FINDINGS_2026-10-10 §1].
>
> **[C/I] OPEN QUESTION — is the unwired TOP row a second USB port/interface? (owner, 2026-10-06).**
> The earlier claim that "the remaining 6 positions never mate / not two lanes" was an inference
> from the harness, NOT proof the radio drives nothing there. The radio header physically has 12
> pins; only the bottom 6 are wired in any cable we have. Whether the top row is dead
> (mechanical/ground/NC) or a **live second USB 2.0 port** (or another interface) is **unresolved**
> and depends on the SoC USB routing, not on the cable. If live, plausible candidates for "something
> else exposed" are: a second **host** USB2 port (more accessories — low value); the
> **projection/DABridge** path; a **diagnostic RNDIS/ECM** USB (the MDI2 diag path uses USB RNDIS —
> security-relevant); or a **factory/test** port. Note the SoC has one physical device controller
> (XDCI = `dwc3.0.auto`; `dabr_udc.0` is dabridge's *virtual* UDC, not a second port), so the top row most likely maps to an xHCI **host** port (would let the
> radio host devices, not grant new access to it) unless a second gadget/port-mux exists.
> **Resolution path (authoritative):** the SoC USB port map in the extracted vendor **ACPI SSDT**
> (`SOC_ACPIO`) / DTB (xHCI `RHUB` port + xDCI definitions), cross-checked with a continuity probe
> of the top-row pins to the SoC/PHY and `/sys/bus/usb` + dmesg when a device is attached. Until
> then, treat "one USB 2.0 port" as "one *wired* port," not a hardware maximum. (Same PCB photo
> confirms the neighbouring silicon:
Intel Atom **A3960** Apollo Lake, Broadcom **BCM89551** Ethernet switch, TI **DS90UB954-Q1**
`AVG3 G4` deserializer — see [`teardown.md`](teardown.md).)

---

## USB

- **USB serial data** connector at the radio = **X8, 12-Way M 2.0 HSAL-2 (BK)**, OEM 13545174.
  Separate from the display link (X7). [C]
- Feeds the console/center USB port(s); GM service cable **PN 23103558** ("USB Data Cable HMI to
  Center") is one HMI→center run. [C]
- **Radio USB cable (bench, owner-sourced) — GM Molex PN `87813526`:** HSAutoLink connector
  (radio/X8 side) → **Male Mini-A USB** plug (receptacle side). This is the physical adapter from
  the radio's HSAL-2 header to the standard-USB world that the front receptacles mate to. [C owner]
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

### ADB is gated by receptacle MODEL — in-vehicle: H2H-bridge device identity (Path A); bench direct line: host-side CC `Rd` (Path B) — [C owner-tested 2026-10-06; mechanism corrected 2026-10-10 from firmware]
> **Two mechanisms, do not conflate (firmware-verified 2026-10-10, [FW 86331652 vmlinux dabridge id_table @0x1712290; FW 86331650 init.full_gminfo37_gb.rc:106-110]):**
> - **In-vehicle (Path A, `ro.product.system.brand` ≠ Android):** the ADB-capable receptacle is recognized by
>   **device identity** — it contains an **H2H bridge chip** matching the `dabridge` id_table
>   **VID `0x2996`, PID `0x0100–0x0105`**; `dabridge_probe` logs **"No H2H Bridge device for '%s'"** when absent.
>   Position-independent; no CC/ID signal is involved (none reaches the radio).
>   **VID `0x2996` = Aptiv [CROSS-CONFIRMED]** — a live USB-tree enumeration lists `2× Aptiv H2H bridges
>   VID:10646(0x2996) PID:261(0x0105)`, plus `2× GM V10 E2 PD hubs 0x2996:0132` and `2× DFU 0x2996:0120`
>   [`../research/GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt:798-800`]. So `dabridge` binds the Aptiv **H2H
>   bridge** (`0x0105`), not the hub (`0x0132`). (The snapshot shows 2× bridges, so it names the device
>   and vendor but does not alone prove the `13558185`/MCIP receptacle lacks one — [UNVERIFIED].)
> - **Bench direct line (Path B):** raw physical `dwc3.0.auto` host→device flip, no hub, no bridge. **Trigger
>   (RESOLVED, owner-confirmed 2026-10-10): the Developer-Options USB-debugging toggle** — ADB off + Mac VBUS
>   present = nothing enumerates; flip the toggle = ADB appears. It is **not** the `brand=Android`/GSI rule (that
>   rule exists in `init.full_gminfo37_gb.rc` but does not fire on the stock-GM AAOS bench) and **not** VBUS-sense
>   (**ruled out**). The CC `Rd` strap below is a **Mac/host-side** property only (it makes the *host* source VBUS);
>   it never reaches the radio, whose role is set in software (§"Two USB device-role paths").
> The owner bench results below are real; only the *explanation* ("radio senses CC/ID") was wrong.
Out-of-vehicle bench testing with discrete receptacles overturns the earlier "end-of-chain / daisy
required" reading and pins the mechanism:

| Receptacle GM P/N | Board silkscreen (Aptiv) | Type (field) | LED | Exposes ADB? |
|---|---|---|---|---|
| **`13550122`** | **APTIV V10 E2 PD `35497296` REV C** | floor/console A/V (= X83B-class, UBC) | no | **Yes** — direct to radio OR anywhere in a chain; position-independent (consistent with it containing the `2996:010x` H2H bridge — Path A; inferred, chip not yet teardown-confirmed) |
| **`13558185`** | **APTIV GM V10 E2 MCIP `35372688` REV E** | dash/infotainment (= X92IP-class) | yes (port illumination) | **No** — never, direct or any chain position (accessories still pass) (consistent with a plain hub, no `2996:010x` device → `dabridge` never binds) |

> **Board markings (owner, 2026-10-06).** The two receptacles carry **different Aptiv board part
> numbers** (`35497296` "PD" vs `35372688` "MCIP"), not merely different REV letters — i.e. they are
> **distinct board designs/programs**, not revisions of one board. (The `PD`/`MCIP` sub-designators
> are Aptiv program codes; not over-interpreted here.) This corroborates the finding that ADB
> capability is a **board-design property** — in-vehicle, the presence of the H2H bridge device
> (`2996:010x`) on the `PD`/`35497296` design and its absence on the `MCIP`/`35372688` design [INF — the
> chip itself is not yet confirmed on either board; the earlier "CC `Rd` strap wiring" explanation is
> withdrawn for the in-vehicle path] — rather than a software gate or a mere stuff/revision difference. Component-layout variation seen *within* a model is
> consistent with the REV letters (C vs E) and does not change the ADB behavior, which tracks the
> board P/N.

**Mechanism (corrected 2026-10-10).** GM did **not** put a software/crypto ADB gate in the receptacle,
and the radio does **not** read a role strap:
- The radio's rear USB (X8 HSAL-2) is plain **4-wire** USB 2.0 (VBUS/D+/D−/GND), broken out to a **Mini-A**
  plug by Molex cable `87813526`. **No ID/CC line reaches the radio**; the only external cues are VBUS and D±.
- Host-vs-device on the radio is a **software** decision: `vendor.sys.usb.role` → `/vendor/bin/usb_otg_switch.sh`
  → write `host`/`device` to `/sys/class/usb_role/intel_xhci_usb_sw-role-switch/role` → XDCI via the ACPI
  OpRegion `OTGD` in the GHS-supplied guest DSDT. The `/dev/cbc-signals` write in that script is a **CAN
  notification, not the flip** [FW 86331650 init.bxtp_gm.rc:952-956, usb_otg_switch.sh].
- The XDCI (`_ADR 0x00150001`) is a **dual-role controller whose role AND port power are software-commanded**
  through `OTGD`/`_DSM` **`SPPS`**: it writes `PUPS` (port power) / `UXPE` (enable) and reads `U2CP/U3CP` (connect)
  [FW decoded `dsdt_a.dsl:1290-1500`; CONFIRMED ×2]. The decision is a register write, **not a sensed pin** —
  which is why the 4-wire X8 (no ID/CC) suffices. Boot default is host (`SPPS` sources VBUS, powering the hubs);
  the dev-options ADB toggle drives it to device (`SPPS` removes radio port power; the radio sinks the Mac's VBUS).
- **VBUS "clash" is benign.** Boot-host radio and the Mac both idle ~5 V with nothing enumerating = low-energy,
  current-limited coexistence, not a short; on toggle→device `SPPS` drops the radio's port power, so the
  dual-source window is momentary. **VBUS-sense auto-role is RULED OUT** (VBUS alone did nothing).
- `adbd` is a USB **function** on configfs gadget `g1`; ADB appears only when the radio is in device role and a
  host (Mac/vehicle) supplies VBUS. **In-vehicle**, the receptacle that contains the `2996:010x` H2H bridge is
  the one `dabridge` binds, so ADB appears there (and not on the plain-hub receptacle); this is why it is
  **model-specific and position-independent** (a hub chain just passes the bridge device through) and why
  the LED on `13558185` is a red herring (port illumination, uncorrelated with the gate).
- Consequences: (a) model-specific & position-independent as above; (b) the **bench** can bypass the receptacle
  entirely (Path B, below) because the raw `dwc3.0.auto` flip needs no bridge device.

**Receptacle-free confirmation (owner, 2026-10-06).** ADB is exposed with **no GM receptacle in the
path at all**: HSAL-2 cable → Mini-USB board → bare wires → **USB-C breakout with CC pulled to GND
through a resistor** → USB-C cable → Mac. This is the **Path B** (bench direct line) mechanism, corrected: the CC pin on the breakout
is on the **Mac side of the cable only** and never reaches the radio (X8 is 4-wire). CC-to-GND-via-resistor
presents **`Rd`** to the **Mac**, which becomes the **DFP/host** and sources VBUS (the one external cue
the radio needs); the radio is placed in device role by the **software** path above, its raw `dwc3.0.auto`
gadget brings up `adbd`. The earlier reading — `Rd` "advertises the radio as a UFP" / "the role decision is at
the USB-C CC pin" — is **withdrawn**: the radio never sees CC. Spec `Rd` for a UFP sink = **5.1 kΩ to GND**
(a full Type-C receptacle wants it on each of CC1/CC2; a true 0 Ω is a short, not a valid `Rd`). The
Mini-USB board/bare wires are pure USB-2.0 passthrough (VBUS/D+/D−/GND). Net: this does **not** show that
`13550122` "hard-wires `Rd`" for the radio's benefit; the in-vehicle gate is the bridge device (Path A).

**But the link/role layer (Mac-side `Rd` on the bench) is necessary, NOT sufficient — there is a second, independent gate (owner,
2026-10-06).** Layer 1 only makes the radio *present* `adbd`; getting an actual **shell**
additionally requires the **EEPROM SBI bypass** (`0x0440` = all-`0xFF` → the `0xb67d0` VIP validator
authorizes adb without GM's private key — see `platform/security.md` ProtoKey/ADB-auth and
`research/EEPROM_*`). On a secured unit (SBI not bypassed), layer 1 alone gets a *connected* `adbd`
that returns **no shell / "Secure Client required."** So full bench ADB = **layer 1: link/role** (radio in device role by software, Mac-side `Rd` making the Mac host and source VBUS on the bench; in-vehicle, the `2996:010x` bridge present)  **AND layer 2: EEPROM SBI
authorization** (the real control; needs the EEPROM write via the seed/VIP path, consistent with
`ro.adb.secure=1`). This bench works because both are satisfied; `13550122` only ever supplied
layer 1 (in-vehicle, plausibly via the H2H bridge device — see above).

**Can an app enable ADB programmatically (vs the manual Dev-Options toggle)? (2026-10-06)**
- **Plain sideloaded `untrusted_app`: no.** It can't reach GM's `RDMSADBHandler.RDMSADBEnable(bool)`
  (SELinux `gm_domain_service` — untrusted blocked), and can't write `Settings.Global.adb_enabled`
  without `WRITE_SECURE_SETTINGS` (which is **not** auto-granted — it's `signature|privileged|development`,
  not `prot=normal`).
- **`priv_app`/`platform_app`:** can call **`RDMSADBEnable(true)`** — GM's own ADB-enable binder, **no
  caller check** (see `research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md` §PRIVESC-5) — to flip
  the USB gadget with no user action.
- **adb-grant lever (works for an ordinary app, one-time) — TESTED 2026-10-06 (`~/gm_adbkick`):**
  `WRITE_SECURE_SETTINGS` is `signature|privileged|**development**` on live Y175, so `adb shell pm
  grant --user 10 <pkg> android.permission.WRITE_SECURE_SETTINGS` succeeds (**must be `--user 10`** —
  the HMI runs as user 10; granting user 0 → SecurityException). The grant survives reboot. An app
  with it (`BOOT_COMPLETED` receiver) **does** re-set `adb_enabled=1` on boot — **necessary because GM
  wipes `adb_enabled` 1→0 on every boot** (proven: boot marker read `before=0`). **But it is NOT
  sufficient for hands-off ADB:** the Dev-Options switch shows **On**, yet the USB-ADB *transport*
  only activates when the user **enters the Developer-options USB-debugging submenu** (or re-plugs the
  USB-C breakout) — that UI action is what flips the USB gadget to ADB. A plain `untrusted_app`
  **cannot** trigger the transport switch (needs `MANAGE_USB`=`signature|privileged`, not grantable,
  or the `priv_app`-only `RDMSADBHandler.RDMSADBEnable`). **Net:** the app removes the toggle-hunt but
  a manual micro-action (submenu entry / re-plug) remains; **full hands-off requires the app to be
  `priv_app`/platform-signed** (then `RDMSADBEnable`). (`READ_LOGS`/`DUMP`/`CHANGE_CONFIGURATION` are
  likewise `development` → adb-grantable; `MANAGE_USB` is `signature|privileged`, not grantable.)

**Pre-OS USB on the direct OTG line (owner, 2026-10-06).** With ADB up on the direct line,
`adb reboot fastboot` exposes **fastbootd** (USB `8087:4ee0`, `is-userspace:yes`, persists);
`adb reboot bootloader`/`recovery`/`edl`/`dnx` expose **no** USB interface (dark until OS). fastbootd
is locked (`unlocked:no`/`secure:yes`) with **no fastboot OEM HAL** — read-only info disclosure only,
no flashing. Details + `getvar all` dump in [`../platform/security.md`](../platform/security.md)
§"fastbootd reachable over direct USB OTG".

### Two USB device-role paths — direct SoC xDCI vs DABridge hub (live-confirmed 2026-10-06)
On the bench **direct breakout line**, ADB *and* fastboot use the **SoC xDCI directly — no hub.**
Live reads (uid 2000): `/sys/class/udc/` → active controller **`dwc3.0.auto`**
(`pci0000:00/0000:00:15.1`, Intel VID `0x8087` — matches observed USB IDs `8087:09ef` ADB /
`8087:4ee0` fastboot); `sys.usb.controller=dwc3.0.auto`, config/state `adb`; and
**`sys.dabridge.dev.portnum`/`host.portnum` EMPTY** → the DABridge path is **not engaged**. This is
**Path B** (bench direct line): `vendor.sys.usb.role=device` flips the raw physical `dwc3.0.auto`
host→device, no hub, no bridge. On the bench the flip is triggered by the **Developer-Options USB-debugging
toggle** (owner-confirmed 2026-10-10), *not* the GSI-only `on sys.boot_completed=1 && brand=Android` rule
[FW init.full_gminfo37_gb.rc] — that rule is the Path-B behaviour on a true `brand=Android` image and does not fire on stock GM AAOS.
The controller choice is **software (`sys.usb.controller`), not a CC strap**; the Mac-side `Rd` only makes the
Mac host. This **confirms** the direct-line "no hub" description from live data. (Running Y175/Y181 units
in the property dumps instead report `sys.usb.controller=dabr_udc.0` — **Path A**, bridged ports Y175
`1-12.0→1-12.3`, Y181 `1-6.0→1-6.3` [LIVE all_properties.txt:482/510, 466-467/494-495]. Full firmware
trace: §"USB hardware & ADB logic" findings, `USB_ADB_SESSION_FINDINGS_2026-10-10.md`.)

Distinct from the **in-vehicle / GM-receptacle (DABridge) path**, where ADB is a *virtual*
`dabr_udc` on an **H2H bridge hub**: SoC xHCI **host** → fixed on-board `1-1` hub (hardcoded
`0000:00:15.0/usb1/1-1` in `product_sepolicy.cil`) → `1-1.4` H2H bridge (matched by `dabridge` on **VID `0x2996` PID `0x0100–0x0105`**) → CarPlay `1-1.4.2`, ADB
`1-1.4.3`; the receptacles are active hubs that daisy-chain; the physical xHCI stays host so hubs/accessories keep
working during ADB (`bridgeport` ← `host.portnum` then `dev.portnum`). *[in-vehicle topology = firmware/
kernel/sepolicy static analysis — single-source, flagged for second-agent concurrence]*

**So "hubs in the chain" is expected ONLY for the DABridge/receptacle path; the direct breakout
line needs no hub** (live-confirmed). The firmware agent's "ADB rides an H2H hub" is correct for the
in-vehicle path only and does **not** override the live direct-line result.

**X8 top-row (possible 2nd port) — firmware cannot answer it:** the guest DSDT Android boots has no
`XHC`/`RHUB`/port objects (only `XDCI`), and the physical DSDT is Intel's *generic* BXT reference,
not the GM PCB — so ACPI carries no connector/port metadata. Resolve only by **physical probe**:
feed a known device into the top-row pins and watch `/sys/bus/usb/devices` for a new node (root-port
`1-N` vs hub-port `1-1.x`); continuity of top-row D+/D− to the SoC vs a hub IC decides it.

**Security meaning.** GM's "ADB is limited to a specific receptacle" is a **device-identity /
physical-layer control only** (in-vehicle: the receptacle must contain the `2996:010x` H2H bridge for
`dabridge` to bind) — no key, fuse, or receptacle-side software check; on the bench it is sidestepped by
the direct `dwc3.0.auto` line (Path B), not by a role resistor. It gates *whether `adbd` is reachable at all*, not *whether it grants a shell* — the real
authorization control is the **EEPROM SBI bypass** (`0x0440`=all-`0xFF`; without it `adbd` returns
"Secure Client required"/no shell — see the two-gate note below), followed by adb RSA auth
(`ro.adb.secure=1`) and the `shell` uid-2000 domain on the locked `user` build (all confirmed live). The Mac-side CC resistor value is per
the owner's working breakout; the role direction (radio = device/gadget, Mac = host) is fixed by
how ADB works, and the radio's role is set in software (no CC/ID reaches it).

**PC-facing VID:PID (software, configfs `g1`, UDC/path-independent):** `0x8087` for data/debug configs
(ADB = `8087:09ef`) and **`0x18d1` (Google)** for accessory/audio_source (AOA) configs
[FW 86331650 init.bxtp_gm.rc:805-892]. This is **not** the radio-internal H2H bridge ID `2996:010x`
(seen only on the internal bus, Path A) — never conflate the two layers.

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
> a host port into **device mode**: `setprop vendor.sys.usb.role device` → `usb_otg_switch.sh p`
> (`host` → `h`) → write to `/sys/class/usb_role/intel_xhci_usb_sw-role-switch/role` → XDCI via ACPI OpRegion
> `OTGD` (GHS-supplied DSDT; its `_DSM` `SPPS` software-commands port power `PUPS`/`UXPE` and reads connect `U2CP/U3CP`,
> `dsdt_a.dsl:1290-1500` — role and VBUS sourcing are register writes, not sensed pins; **VBUS-sense auto-role is ruled out**; the bench trigger is the
> Developer-Options USB-debugging toggle, owner-confirmed 2026-10-10); on Path A, port bridging via `/sys/bus/usb/drivers/dabridge/bridgeport`. The
> `/dev/cbc-signals` write is a CAN notification, not the flip. Documented in
> [`../analysis/platform_faq.md`](../analysis/platform_faq.md) (§dabridge/UDC) and
> [`../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md).
> So ADB = the radio's own USB controller entering gadget mode; the receptacle's ID/CC pins are
> **not** what enable it (they can't — see §"why that doesn't fully explain ADB").
>
> **RESOLVED model (owner bench data, Sep 2026).** Field testing: ADB works over USB on the
> **floor-console Type-C ONLY**; it worked **even with the receptacle externally unpowered (no
> 12 V)** [still owner-only/[UNVERIFIED] as a wiring claim, but consistent with the software-toggle + `SPPS` model: the role/port-power change is a register write in the radio, independent of receptacle 12 V]; the same port also hosts USB drives/phones normally; and it requires an **OTG cable**
> (a plain C-to-C does not enumerate ADB). This locks the architecture:
> - **The ADB Type-C is NOT behind the A90 hub.** ADB with no 12 V ⇒ the hub is dead yet ADB runs ⇒
>   the port is on a **direct dual-role link from the radio to that connector, bypassing the hub.**
>   (Confirms the "separate DRD link" hypothesis; kills the hub-downstream reading for this port.)
> - **Dual-role, same connector:** host mode (drives/phones — radio supplies VBUS from its own
>   controller) and device mode (ADB — PC supplies VBUS). Neither needs the receptacle's 12 V; that
>   12 V only powers the A90 hub's Type-A ports + charging.
> - **OTG-cable requirement — observation stands, the ID/CC explanation is WRONG (2026-10-10).** No ID/CC
>   conductor reaches the radio (X8 is 4-wire) and the firmware reads none; the role flip is the software
>   path (`vendor.sys.usb.role`). The cable's ID/CC termination can matter only on the **host/receptacle
>   side** (e.g. the Type-C side deciding who sources VBUS); the radio-side cause of "plain C-to-C gives no
>   ADB" is not established [UNVERIFIED].
> - **Likely wire [superseded in part — in-vehicle ADB is Path A through an H2H bridge device, hubs stay live; an
>   un-powered-hub ADB result and a "direct DRD link" are not reconciled with that and remain [UNVERIFIED]]:** X83B has two Mini-B legs — **X2 (GY)** = host feed from the IP hub daisy;
>   **X3 (BK)** = destination never traced. A Mini-B carries an ID pin, but any such ID line stops at the receptacle (none reaches the radio), so
>   X83B X3 as a "dual-role/ID link" is a [UNVERIFIED] hypothesis. Only the
>   floor-console receptacle wires this to its Type-C; the IP receptacle's Type-C is hub-only →
>   host-only → no ADB.
> - **"X8 can't do ADB because it has no ID pin" — WITHDRAWN (2026-10-10).** X8 *is* 4-wire (VBUS/D+/D−/GND,
>   no ID/CC) but that is true of the radio end in every configuration, and role is software-set, so a missing
>   ID pin does not make X8 a permanent host. The owner's direct X8→Mac breakout line (Path B) does reach ADB.
>
> **Remaining to meter:** whether **X83B X3** runs to a *separate* radio USB connector or is part of the
> hub/bridge chain, and where the `2996:010x` H2H bridge sits in the receptacle — probe/teardown only.

**Bench takeaway for USB/ADB access:** power the receptacle hub (**2640 = 12 V + 1051 = gnd**), use
the **floor-console Type-C with an OTG cable** — not a Type-A port, not a single Mini-B data-only
break-out. A different-color data-cable P/N alone won't help if the hub is unpowered or you're on a
host port.

> **Owner bench symptom (Sep 2026) — confirms "meter X8", not "buy the right connector".** On a bench
> harness (OPU emulator: X5 p1/3 + X6 p9/10 + X7 LVDS, no factory USB hub), wiring **X8** to various
> breakouts exposing Micro-B / Type-A yields **VBUS (~5 V) only — no device ever enumerates**, and
> **buying visually-identical GM USB connectors changed nothing.** This is the predicted failure of
> an **unknown D+/D− pin position**: IOK X8 has no published per-pin map, and look-alike HSAL-2 shells
> differ in assignment. **Action: meter the 6-pin cable** (VBUS ≈ +5 V→GND; GND ≈ 0 Ω to shell; D+/D−
> = the twisted pair into the ESD/choke cluster) before wiring any port. Note also: X8 has no ID pin, **but that does not
> make it host-only** — role is a software flip (`vendor.sys.usb.role`), so X8 is also the bench ADB line
> (Path B); the in-vehicle ADB receptacle path is Path A (see §ADB mechanism), not CAN-gated.
> For a bench *host* test the A90 hub is optional — a correctly-pinned X8→Type-A should mount a drive
> directly (radio = host); "VBUS only" means the data pair is mis-pinned, not that the hub is missing.

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
| ADB device-mode mechanism = software role-switch (`vendor.sys.usb.role` → `usb_otg_switch.sh` → `intel_xhci_usb_sw-role-switch/role` → XDCI `OTGD` ACPI); Path A `dabridge`/`dabr_udc.0` (in-vehicle), Path B raw `dwc3.0.auto` (bench) | **[FW]** USB_ADB_SESSION_FINDINGS_2026-10-10 §4–§6; also analysis/platform_faq.md, SHELL_ACCESS_ESCALATION_Jun2026.md |
| No CC/ID conductor reaches the radio (X8 4-wire); CC `Rd` strap is host/Mac-side only | **[FW/HW]** findings §1, §4 |
| In-vehicle ADB receptacle = contains H2H bridge `2996:010x` (dabridge id_table); chip on `13550122` itself | **[FW]** id_table / **[I]** receptacle teardown OPEN |
| PC-facing ADB ID `8087:09ef` (VID `0x18d1` for AOA/audio_source) = configfs `g1`, path-independent | **[FW]** findings §5, §6.2 |
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
