# gminfo37 (Silverado CSM) — board & component photos

Bench teardown photos of the 2024 Silverado GM Info 3.7 CSM (Harman, Intel Atom A3960 + Renesas
RH850/F1K VIP). All EXIF/GPS metadata stripped (location removed); hardware markings/serials are
left intact (airgapped bench — not sensitive). Cross-reference `../teardown.md` BOM and
`../connectors.md`.

## SoC / module
| File | Shows |
|---|---|
| `soc_a3960_lpddr4_closeup.jpeg` | Intel **Atom A3960** (heat spreader, `SREKE`) + the 4 **LPDDR4** packages (8 GB) on the AT&S carrier PCB |
| `soc_a3960_ram_rf_module.jpeg` | A3960 + RAM from another angle, with an adjacent shielded RF module |

## Carrier board overviews / regions
| File | Shows |
|---|---|
| `carrier_top_overview.jpeg` | Full carrier board, top face |
| `carrier_bottom_overview.jpeg` | Full carrier board, bottom face |
| `carrier_overview_center.jpeg` | Center board region, main BGAs |
| `carrier_overview_bga_crystals.jpeg` | Board overview, large BGA + crystals |
| `board_qfp_ribbon_region.jpeg` | Large QFP (Ethernet switch / deserializer area) + ribbon connector |
| `board_soic_flash_region.jpeg` | SOIC flash + passives region |
| `board_corner_fakra_bga.jpeg` | Board corner: FAKRA + large BGA |

## RF front-end / connectors
| File | Shows |
|---|---|
| `fakra_tuner_rf_corner.jpeg` | FAKRA coax (tuner) + RF shield can |
| `fakra_bga_ufl_region.jpeg` | FAKRA + large BGA + u.FL antenna |
| `harness_connectors_power.jpeg` | Rear harness connectors + power caps |

## Module labels
| File | Shows |
|---|---|
| `module_label_region.jpeg` | Module-with-label in board context (`P/N 91.UMAF2HG.GS6FAAG` / `3765210`; the label OCRs with a stray leading `L` — `teardown.md` treats it as the same single P/N, corrected 2026-11-12) |
| `module_label_closeup.jpeg` | Close-up of the same module label (P/N + PSN + DataMatrix) |

## IC close-ups
| File | Shows |
|---|---|
| `rh850_vip_region_on_board.png` | **Renesas RH850/F1K R7F7015873AFP VIP** (QFP-176; device `15873`, trace `TM52176`) + nearby EEPROM, on-board |
| `eeprom_m24c64_microscope.png` | **ST M24C64** EEPROM, digital-microscope close-up (markings `464RQ ST K228`) — the VIP EEPROM / SBI store |
| `eeprom_on_xgecu_programmer.png` | The EEPROM/SOIC seated on an **XGecu** programmer (SOP28→DIP adapter) for dump |

Identification corrected 2026-11-12: 176 pins (44 per side), not 144; `15873`
is the device marking and `TM52176` is the manufacturing trace code. See
[the corrected package and UART reference](../teardown.md#rh850f1k-package--uart-pinout).
