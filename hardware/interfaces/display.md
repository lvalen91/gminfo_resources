# Display and Camera Path

Scope: display signal chain, FPD-Link III link (X7), A22 Radio Control module, and camera video
input (X9).
Related: [`connectors.md`](connectors.md), [`usb.md`](usb.md) (X8, same shell type),
[`../module/identity_bom.md`](../module/identity_bom.md), `../../video/display_subsystem.md`.

Confidence tags: **[C]** confirmed · **[I]** inferred.

## 1. Signal Chain

```
Intel A3960 GPU (HD Graphics 505)
  → internal display pipe → HWC 2.1 (hwcomposer.broxton), triple-buffered, VSYNC 16.67 ms
  → TI DS90UH949-Q1 FPD-Link III serializer
  → X7 (board silkscreen "LVDS", GY 12-way HSAL-2)
  → A22 Radio Control (center-stack HMI/display assembly): Chimei panel + touch, 2400×960 @ 60 Hz
  → LT3899 backlight LED driver (role unconfirmed, see §5)
```

GM service diagrams label the link "LVDS / INFOTAINMENT DISPLAY SIG". It is FPD-Link III over one
cable, not parallel LVDS. [C]

## 2. X7 Connector

| Item | Value |
|------|-------|
| Connector | 12-way M 2.0 mm HSAL-2, GY keying, OEM 13511515 |
| Board silkscreen | `LVDS` (grey), contacts numbered 6…1 |
| Shell | Same shell as X8 (USB, BK); keying color is the only difference ([`connectors.md`](connectors.md) §1.6) |
| Display power/control discretes | On the Stac64 harness ([`connectors.md`](connectors.md) §4.3) |

## 3. A22 Radio Control — [C] link, [I] role

GM designates the panel assembly `A22 Radio Control`, an addressable center-stack module fed from
A11 X7. The Body Builder Manual (BBM) gives a point-to-point match:

| Circuit | Function | A11 X7 (IOK) pin | A22 X2 (IOK) pin |
|---------|----------|------------------|------------------|
| 7853 | Center Stack LVDS low reference | 1 | 1 |
| 7854 | Center Stack LVDS signal [+] | 2 | 2 |
| 7855 | Center Stack LVDS signal [−] | 3 | 3 |
| 7847 | Center Stack LVDS 2 low reference | 4 | 6 |
| 7848 | Center Stack LVDS 2 signal [+] | 5 | 4 |
| 7849 | Center Stack LVDS 2 signal [−] | 6 | 5 |

- These six circuits appear only at A11 X7 and A22 X2 in the 1028-page BBM (dedicated link).
- A11 X7: 12-way HSAL-2 (GY), OEM 13511515. A22 X2: 6-way M HSAL-2 (BK), OEM 13522802.
- Two pairs (LVDS and LVDS 2) carry the 2400×960 panel (dual link).
- A22 X1 (8-way Mini-50, OEM 35068228) is power only: Battery+ p1 (1340 RD/WH), signal ground p8
  (1051 BK/WH). Fuse F30 (SDM/AOS, 10 A).
- Role is inferred from the LVDS input and the name "Radio Control"; the BBM contains no prose
  stating that A22 is the touchscreen/HMI. The dedicated Center-Stack-LVDS link from the head
  unit is strong evidence it is the remote display/HMI assembly housing the Chimei panel.

## 4. Runtime-Identified Components

Not read at physical teardown; from runtime enumeration (Jun-2026 Y181 capture).

| Item | Value | Source |
|------|-------|--------|
| Panel | Chimei Innolux (CMN) DD134IA-01B, 2400×960 @ 60 Hz, ~13.4 in, density 200 | EDID; no marking read off the assembly |
| Touch controller | Atmel maXTouch, i2c bus 7, address 0x4B | i2c enumeration |
| GPU stack | Mesa 21.1.5, OpenGL ES 3.2, Vulkan 1.1.0 | Runtime |

## 5. Backlight

The live backlight control path is an in-band I2C write (panel register `0x20`, faceplate
controller at `0x12`) over the FPD-Link I2C channel through the DS90UH949-Q1 serializer link,
write-gated by GHS (`video/display_subsystem.md`). No GHS- or native-Linux-controlled backlight
driver was found on the SoC/I2C side. The LT3899 (dual boost LED driver) function is therefore
unconfirmed; it may sit on the panel side of the link. The harness discretes named LCD enable /
backlight enable / dimming ([`connectors.md`](connectors.md) §4.3) are unconfirmed as the live
enable path.

## 6. Camera Input (X9)

```
Camera(s) → coax (OG, X9) → FPD-Link III → TI DS90UB954-Q1 deserializer hub → CSI-2 → A3960 ISP
```

- Camera video is FPD-Link III, not analog composite. [C]
- GHS drives the backup/surround overlay directly, so the camera works during an Android reboot.
- DS90UB954-Q1 identification is teardown-asserted [I]; the lid marking is not legible in the
  photo set.
- Options: UV2 (360° mono HD vision), UVN (cargo-bed camera), TRG (trailer inside-rear view).

## 7. Sources

- ALLDATA IOK connector views (A11 X7, X9); GM Electrical Body Builder Manual (A22 X1/X2).
- PCB photo: X7 silkscreen `LVDS`.
- `video/display_subsystem.md`; `platform/hardware.md`.
