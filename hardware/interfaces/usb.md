# USB Connector and Topology

Scope: X8 connector and cable, console USB receptacle wiring and topology.
Related: [`connectors.md`](connectors.md), [`display.md`](display.md),
[`../../analysis/platform_faq.md`](../../analysis/platform_faq.md) (§dabridge/UDC),
[`../../research/USB_ADB_SESSION_FINDINGS_2026-10-10.md`](../../research/USB_ADB_SESSION_FINDINGS_2026-10-10.md)
— for the USB role-switch mechanism and ADB-reachability conditions, see that research document
rather than this hardware reference.

Confidence tags: **[C]** confirmed · **[HW]** hardware observation · **[I]** inferred ·
**[?]** open.

## 1. X8 Connector and Cable — [C]

| Item | Value |
|------|-------|
| Radio connector | X8: 12-way M 2.0 mm HSAL-2, BK keying, OEM 13545174, "USB Serial Data" |
| Board silkscreen | `USB2.0` (black), contacts numbered 6…1 |
| Wired pins | 6 (bottom row) in every known cable: Molex `87813526` bench cable and in-vehicle harness. ALLDATA X8 end view draws 12 cavities, 6 populated. |
| USB conductors | 4 of the 6 wired: VBUS, D+, D−, GND |
| Bench cable | GM Molex PN `87813526`: HSAutoLink connector (radio) → male Mini-A USB plug — [C owner] |
| Service cable | PN 23103558 "USB Data Cable HMI to Center" (HMI → center receptacle run) |
| Mating shell | Same shell as display connector X7 (GY); keying color is the only difference ([`connectors.md`](connectors.md) §1.6) |

### 1.1 Pin positions — [I]

The per-pin map of IOK X8 is not published. ALLDATA (full archive, 1,242 articles) and the Body
Builder Manual list X8 as summary-only (`USB Serial Data`); no D+/D−/VBUS labels exist for IOK
in the dataset. The four conductors are VBUS, D+, D−, GND (§1); their positions in the 6-pin
wired row are not assigned by any available IOK document.

To establish IOK X8 positions, meter the 6-pin cable: VBUS ≈ +5 V to GND with receptacle power
on; GND ≈ 0 Ω to shell; D+/D− = the twisted pair into the ESD/choke cluster.

Bench observation: with X8 wired to Micro-B / Type-A breakouts on the OPU emulator harness (no
factory hub), VBUS (~5 V) appears but no device enumerates; substituting visually identical GM
connectors did not change this, consistent with a mis-pinned D+/D− pair. For a bench host test
the hub is optional: a correctly pinned X8 → Type-A should mount a drive directly.

### 1.2 Unwired top row — [?]

Whether the unwired top row of the 12-way header is dead (mechanical/ground/NC) or a live second
USB interface is unresolved. The SoC has one device controller (XDCI = `dwc3.0.auto`); a live top
row would most likely map to an xHCI host port. Firmware/ACPI data does not resolve this (the
guest DSDT has no port objects, and the physical DSDT is Intel's generic reference, not the GM
board). Resolution requires a physical continuity probe with a known device attached while
watching `/sys/bus/usb/devices` for a new node.

## 2. Console USB Receptacles — [C]

Three Type-A + Type-C receptacle pairs (ALLDATA + owner field data).

| Receptacle | RPO | Location | Data | Function |
|------------|-----|----------|------|----------|
| X83B Audio/Video Receptacle | UBC | Floor console | Yes (2× Mini-B, power) | Main / service |
| X92IP USB 2-Port Receptacle | UBJ | Instrument-panel lower | Yes (2× Mini-B, power) | Secondary |
| X92CD Dual Charge-Only Receptacle | UBI | Floor console rear | No (power, dimming, ground only) | Charge only |

Not equipped: X92CF (USB 2-Port, floor console front, RPO UBD, fuse F26DR 10 A "SEO/USB CHARGE").
The VIN has UBC/UBI/UBJ only. No connector view or schematic for X92CF exists in the archive.

Functionally the console receptacle (X83B) is treated as "main"; electrically it is downstream of
X92IP on the daisy chain (§3).

### 2.1 Receptacle connectors

Each data receptacle is an active, separately powered hub (internal `A90 Logic` controller).

| Receptacle | Conn | OEM P/N | Type | Carries |
|------------|------|---------|------|---------|
| X83B | X1 | 2035363-4 | 6-way F 0.64 Gen-Y (BK) | Power/control: Battery+, LED dimming, signal ground |
| | X2 | 13890926 | 5-way M 2.0 Mini-B USB (GY) | USB serial data |
| | X3 | 13890925 | 5-way M 2.0 Mini-B USB (BK) | USB serial data |
| X92IP | X1 | 13920633 | 6-way F 0.64 Gen-Y (BK) | Battery+ (2640 RD/VT), LED dimming (6817 YE), signal ground (1051 BK/WH) |
| | X2 | 111014-9501 | 5-way M 2.0 Mini-B USB (GY) | USB serial data |
| | X3 | VP000109 | 5-way M 2.0 Mini-B USB (BK) | USB serial data |
| X92CD | X1 | 2035363-4 | 6-way F 0.64 Gen-Y (BK) | LED dimming + ground only; no USB |

## 3. Topology (ALLDATA *Auxiliary Inputs (D07)*) — [C]

```
DATA (single USB link, daisy chain):
  A11 X8 (BK) ──USB──▶ X92IP X2 (GY) [IN, UBJ] ── A90 hub
  X92IP X3 (BK) [OUT] ──USB──▶ inline X226 ──▶ X83B X2 (GY) [IN, UBC] ── A90 hub
  X92IP upstream (on the radio); X83B downstream

POWER (parallel from fuse, not from the radio):
  B+ ─▶ F32DR 15 A (X51R IP junction block) ─▶ 2640 RD/VT ─┬─▶ X92IP X1 p1
                                      (J304/J337,           └─▶ X83B X1 p1   (X92CD by same pattern)
                                       inline X227 c29 / X210 c59)
  Ground: X92IP/X83B X1 p3 = 1051 BK/WH ─▶ G200 · Dimming: 6817 YE ─▶ each X1 p2
```

- Hub power: 2640 (Battery+, F32DR 15 A), 1051 (ground, G200), 6817 (dimming). An unpowered
  receptacle hub passes no data; devices plugged into it do not enumerate.
- The radio uses one USB link for the whole chain; the sheet shows no second radio USB link.
- X92IP X2 = IN (from radio), X3 = OUT (to X83B). The `A90` hub fans IN to its own Type-A and
  Type-C ports and forwards OUT downstream.
- Inline X226 is a real 5-way Mini-B connector (OEM 13699757 / VP000109). X227 (cav 29) and X210
  (cav 59) carry only the 2640 power feed.
- X83B X3 destination is untraced within this hardware survey.

## 4. On-Board USB-UART

The Microchip MCP2200 (`/dev/ttyACM1` under AAOS, native Linux `/dev/ttyACM0`) is an internal,
SXM-associated serial device, not a rear harness connector. See
[`../module/identity_bom.md`](../module/identity_bom.md) §4.2.

## 5. Sources

- ALLDATA Component Connector End Views: A11 X8, X92IP X1–X3; ALLDATA *Auxiliary Inputs (D07)*.
- GM Electrical Body Builder Manual (IOK X8 summary entry).
- GM Molex cable `87813526`; GM service cable PN 23103558.
- PCB photo: X8 silkscreen `USB2.0`.
