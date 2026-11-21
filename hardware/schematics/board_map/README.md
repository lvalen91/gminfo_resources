# Board Map & Photos

Canonical photo archive for the 2024 Silverado GM Info 3.7 CSM (Harman carrier + Intel Atom
A3960 SoM + Renesas RH850/F1K VIP). All EXIF/GPS metadata stripped and images re-encoded to
bare pixel data (no embedded crop originals). Hardware markings and serial numbers are left
intact (airgapped bench — not sensitive). Cross-reference `../../teardown.md` BOM and
`../../connectors.md`.

## Board map reference images

Used with `board_map.json` (component overlay coordinates, `x`/`y`/`w`/`h` as % of image):

| File | Shows |
|---|---|
| `top.jpg` | Carrier board, top face — CPU/SoM side |
| `bottom.jpg` | Carrier board, bottom face — VIP/FAKRA side |

## `photos/` — full high-res collection

### Full-board shots
| File | Shows |
|---|---|
| `Top_CPU-Side.png` | Full carrier top (CPU side), high-res |
| `Bottom_VIP-Side.png` | Full carrier bottom (VIP side), high-res |

### Composite montages
| File | Shows |
|---|---|
| `MONTAGE_TOP_CPU-side.png` | Stitched montage, top/CPU side |
| `MONTAGE_BOTTOM_VIP-side.png` | Stitched montage, bottom/VIP side |

### Quadrant tiles — top (CPU side)
| File | Shows |
|---|---|
| `Top-UpperLeft.png` | Top face, upper-left quadrant |
| `Top-UpperRight.png` | Top face, upper-right quadrant |
| `Top-LowerLeft.png` | Top face, lower-left quadrant |
| `Top-LowerRight.png` | Top face, lower-right quadrant |

### Quadrant tiles — bottom (VIP side)
| File | Shows |
|---|---|
| `Bottom-UpperLeft.png` | Bottom face, upper-left quadrant |
| `Bottom-UpperRight.png` | Bottom face, upper-right quadrant |
| `Bottom-LowerLeft.png` | Bottom face, lower-left quadrant |
| `Bottom-LowerRight.png` | Bottom face, lower-right quadrant |

### IC close-ups
| File | Shows |
|---|---|
| `CPU-closeup.png` | Intel **Atom A3960** (`SREKE`) heat spreader close-up |
| `rh850_vip_region_on_board.png` | **Renesas RH850/F1K R7F7015873AFP** VIP (QFP-176; device `15873`, trace `TM52176`) + nearby EEPROM, in-board context |
| `eeprom_m24c64_microscope.png` | **ST M24C64** EEPROM, digital-microscope close-up (markings `464RQ ST K228`) — VIP EEPROM / SBI store |
| `eeprom_on_xgecu_programmer.png` | Same EEPROM seated on an **XGecu** programmer (SOP28→DIP adapter) for dump |

RH850 identification corrected 2026-11-12: 176 pins (44 per side), not 144; `15873` is the
device marking and `TM52176` is the manufacturing trace code. See
[the corrected package and UART reference](../../teardown.md#rh850f1k-package--uart-pinout).
