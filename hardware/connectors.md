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
| CAN | GM VIP/SDV1 (GB), CAN 2.0 29-bit · Req `0x14DA80F1` / Rsp `0x145AF180` (HS-CAN) |

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

---

## Display Link (FPD-Link III — GM labels it "LVDS")

- Silicon: **TI DS90UH949-Q1** FPD-Link III **serializer** on the PCB → remote **Chimei Innolux
  DD134IA-01B**, 2400×960 @ 60 Hz, ~13.4″ panel. [C] ([`teardown.md`](teardown.md))
- GM service diagrams label this "**LVDS / INFOTAINMENT DISPLAY SIG**" — that is FPD-Link III
  serialized over one cable, **not** classic parallel LVDS. [C]
- Display *power/enable/backlight* control lines ride the Stac64 harness (see Controls table);
  the *video* rides the dedicated display connector.

### Open item: which shrouded connector (#3 vs #4) is display vs USB
Two data points conflict — resolve with a continuity check, don't assume:

| Evidence | Points to |
|----------|-----------|
| Schematic connector color code (LVDS = `GY` gray, USB = `BK` black) | gray #4 = display, black #3 = USB |
| Pin count (12-pin fits a serial display link + control; 6-pin fits USB VBUS/GND/D+/D−/shield/ID) | black #3 = display, gray #4 = USB |

**To settle:** ohm each shrouded connector's shield/pairs toward the 13.4″ panel vs. the
console USB port; whichever rings to the screen is the FPD-Link display link. [I]

---

## USB

- **USB serial data** connector (GM circuit label `USB`), separate from the display link. [C]
- Feeds the console/center USB port(s); GM service cable **PN 23103558** ("USB Data Cable HMI to
  Center") is the HMI→center run. [C]
- On-board debug USB-UART (Microchip MCP2200 → `/dev/ttyACM1`) is internal, not a rear harness
  connector — see [`teardown.md`](teardown.md).

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
| Which physical FAKRA jack = which signal (housing position) | **[I]** color convention — verify |
| #3 vs #4 = display vs USB | **[I] unresolved** — continuity check needed |
| Exact cavity numbers per RPO/trim | **[I]** variant-dependent |

## Sources
- Rear-panel photo of test unit (2024 Silverado 2500 HD LTZ, RPO IOK).
- GM service wiring diagrams: *Sound Systems – Low Level*, *Sound Systems – Mid/High Level W/
  Amplifier*, *Computer Data Lines*.
- [`hardware/teardown.md`](teardown.md) — internal silicon (FPD-Link serializer/deserializer,
  I210, BCM89551, TDF8532, SAF7751).
- [`platform/networking.md`](../platform/networking.md) — AVB audio endpoint, internal networks.
- `research/GM_REMOTE_ACCESS_ANALYSIS.txt` — `192.168.1.103 AMP_ETH`.
- `research/session_logs/security_assessment_20DEC25.txt` — `External Amp: Present, AMPCAL=3`.

## See also
- [`platform/vehicle_network.md`](../platform/vehicle_network.md) — vehicle-wide two-plane network map (CAN + Ethernet) these connectors carry.
- [`platform/ota_programming_roles.md`](../platform/ota_programming_roles.md) — module programming / OTA over this network.
