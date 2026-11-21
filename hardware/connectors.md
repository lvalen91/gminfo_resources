# Connector Map Index

**This file is now an index.** Its content has been split into topic-specific documents under
[`module/`](module/) and [`interfaces/`](interfaces/). See each section below for where its
material now lives.

---

## Module Identity (this connector set)

| Field | Value |
|-------|-------|
| GM Service P/N | 3765210 |
| ECU address | `0x80` (A11 Radio) |

Full identity fields (Harman assembly P/N, HWID, vehicle/RPO, platform, CAN addressing) and the
RPO build manifest now live at [`module/identity_bom.md`](module/identity_bom.md).

> **Confidence key:** **[C]** confirmed against schematic circuit names/numbers or teardown
> silicon · **[I]** inferred from FAKRA color convention / pin count / harness shape (verify with
> a meter or the vehicle-specific service pinout). GM issues several harness variants for this
> radio; connector designators (`X1`…`X11`) and which cavities are populated differ by RPO/trim,
> so **locate connectors by function, not by X-number.**

---

## Module identity, RPO manifest, board architecture, BOM

Moved to [`module/identity_bom.md`](module/identity_bom.md) — module identity fields, the
build RPO manifest for the test vehicle, board architecture, bill of materials, and the
photo-derived BOM cross-check.

## Rear-panel connector map, IOK per-cavity table, FAKRA, Stac64 headers

Moved to [`interfaces/connectors.md`](interfaces/connectors.md) — the authoritative IOK
per-cavity connector table (X5/X6/X7/X8/X9/X10/X11), the physical rear-panel layout, the
FAKRA/coax color-code table, the Stac64 power/CAN/Ethernet header tables, and the
variant-dependent connector-designator cross-reference.

## Audio architecture (Bose amp, AVB)

Moved to [`interfaces/audio.md`](interfaces/audio.md) — the radio↔amplifier signal chain, the
confirmed radio↔T3-amp wiring (Ethernet Bus 6 audio data-plane, AUTOSAR CAN 5 control-plane),
and the T3 amplifier connector pinouts.

## Display link (FPD-Link III / "LVDS")

Moved to [`interfaces/display.md`](interfaces/display.md) — the display/camera signal chain,
the X7 connector, the A22 Radio Control module and its point-to-point link to the A11, and the
resolved X7-vs-X8 (display-vs-USB) connector identity.

## USB

Moved to [`interfaces/usb.md`](interfaces/usb.md) — the X8 connector and bench cable, the
three console USB receptacles, the daisy-chain topology (ALLDATA *Auxiliary Inputs (D07)*), and
the on-board USB-UART. The ADB role-switch mechanism narrative is intentionally not duplicated
in the hardware docs; it remains in `research/mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md` and
`analysis/platform_faq.md`.

---

## Verification Status / Sources

Verification-status tables and sources for each topic above now live in the corresponding new
file's own "Verification Status" / "Sources" section — see
[`module/identity_bom.md`](module/identity_bom.md), [`interfaces/connectors.md`](interfaces/connectors.md),
[`interfaces/audio.md`](interfaces/audio.md), [`interfaces/display.md`](interfaces/display.md),
and [`interfaces/usb.md`](interfaces/usb.md).

## See also
- [`teardown.md`](teardown.md) — board-level silicon and internal signal chains (what's *on*
  the board, as opposed to what plugs into the back).
- [`platform/vehicle_network.md`](../platform/vehicle_network.md) — vehicle-wide two-plane
  network map (CAN + Ethernet) these connectors carry.
- [`platform/ota_programming_roles.md`](../platform/ota_programming_roles.md) — module
  programming / OTA over this network.
