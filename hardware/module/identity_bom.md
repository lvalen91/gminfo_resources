# Module Identity, Architecture, BOM

Scope: module identification, build options, board architecture and bill of materials.
Related: [`interfaces/connectors.md`](../interfaces/connectors.md), [`audio.md`](../interfaces/audio.md),
[`display.md`](../interfaces/display.md), [`usb.md`](../interfaces/usb.md), [`teardown.md`](../teardown.md) (index).

Confidence tags: **[C]** confirmed (schematic, label or legible marking) · **[I]** inferred ·
**[FW]** firmware or driver evidence · **[?]** open.

## 1. Module Identity

| Field | Value |
|-------|-------|
| Platform | gminfo37 (GM Info 3.7), Harman/Samsung |
| ECU address | `0x80` (A11 Radio) |
| GM service P/N | 3765210 |
| Harman assembly P/N | 91.UMAF2HG.GS6FAAG |
| HWID | ZQ68GEC80317, EC-Index 20 |
| Production serial / mfg trace | `<PRODUCTION_SERIAL>` / `<MANUFACTURING_TRACE>` (redacted) |
| Device ID | `<DEVSERIAL_REDACTED>` (redacted) |
| Test vehicle | 2024 Chevrolet Silverado 2500 HD LTZ, 6.6 L L8T gas; VIN redacted (corrected 2026-11-12 from "1500") |
| RPO (radio) | IOK — Infotainment 3 Premium, 13.4 in, Google built-in |
| Platform / EE architecture | GM T1XX-HD / Global B (VIP / SDV1-GB) |
| CAN | CAN 2.0, 29-bit, HS-CAN |
| Diagnostic IDs (tester F2) | Req `0x14DA80F2` / Rsp `0x145AF280` (`A11_CSM_x80.Txt`) |
| Diagnostic IDs (generic OBD tester F1) | Req `0x14DA80F1` / Rsp `0x145AF180`; also reaches ECU 0x80; used by DPS bench read logs (confirmed: GM_research/diagnostics/gm_dps/DPS_All_Module_Read/.../GCI_*.txt) |

## 2. Build RPO Manifest

Source: factory RPO list for the VIN (`RPO Codes.pdf`) and ALLDATA vehicle profile CarId 65566.
Connector, audio and USB variants in this repository are anchored to these codes.

| RPO | Meaning | Effect |
|-----|---------|--------|
| IOK | Radio Infotainment 3.X Mid/High HMI, Enhanced Connectivity 2.0, voice recognition | Selects the IOK connector variant |
| UQA | Premium audio, branded amplifier (Bose) | Digital audio over AVB Ethernet to external amplifier; radio drives no speakers |
| URD | Infotainment display TFT, 13.4 in, 2400×960 | Panel: Chimei Innolux DD134IA-01B |
| UV2 / UVN / TRG | 360° mono HD vision / cargo-bed camera / trailer inside-rear view | FPD-Link camera feeds on OG coax X9 → DS90UB954 deserializer |
| U2K | Digital audio S-band (SiriusXM) | Coax X3 (CU) |
| U73 | Fixed radio antenna | AM/FM coax (BK) |
| UE1 | OnStar | Gates X5 pin 9 (VR / telematics mic); proven populated (Option IOK+UE1) |
| VV4 | Mobile internet (Wi-Fi hotspot) | Coax X10 (BG) |
| PPW | Wireless phone projection | `projection/` (wireless CarPlay/AA) |
| UBC / UBI / UBJ | USB armrest dual (charge+data) / rear floor-console dual (charge) / IP-lower dual (charge+data) | USB receptacles, see [`usb.md`](../interfaces/usb.md) |
| K4C | Inductive wireless charger | — |
| IVN | Virtual cockpit: none, uses radio family | Cluster driven by radio family |
| L8T / MKM / GF9 / F48 / NQH | 6.6 L gas / 10-speed / LTZ / 4WD / 2-speed transfer case | Matches ALLDATA vehicle folder |

## 3. Board Architecture

Three-processor design on a single PCB.

```
GM Info 3.7 main PCB — AT&S MX3 SH 94V-0, fab A922114, drawing G071-4010-03MN, board 4050897 REVA

  Intel SOM (soldered)
    Atom x7-A3960, Apollo Lake, 14 nm Goldmont, quad-core, SREKE (e1), J238G327, AEC-Q100
      CSE: own uC + SRAM, hardware root of trust; AES-CMAC master key (fuse-protected)
      GPU: HD 505    VPU: hardware decode
    4x Micron MT53E512M32D2DS-053 LPDDR4 (8 GB, 2400 MT/s)
    IFWI flash: IS25WP064A, 8 MB SPI NOR (BGA, CS0)

  RH850 VIP MCU (15873, LFQFP176) <--I2C--> M24C64 EEPROM (8 KB, TSSOP-8)
        |  IPC (HDLC)
  Samsung eMMC 64 GB (KLMCG4JEUD, BGA-153)

  BCM89551 Ethernet switch   Intel I210 GbE MAC (AVB)   NXP SAF7751 tuner + DSP
                                   |  AVB Ethernet
                             NXP TDF8532 (external DSP/amplifier)
```

Notes:
- VIP marking is `15873`; `TM52176` is the trace code only.
- `BCM89551` is the switch on the photographed MY22/DV unit. The live Y181 bench radio uses the
  Marvell 88Q5050 (same specification; see §4.2).
- Diagram label "(soldered)" is the schematic's own text; the A3960 module is actually a discrete
  sub-board, not soldered to the main carrier (photo-confirmed, see §5 Photo Cross-Check).

## 4. Bill of Materials

### 4.1 Compute and storage

| Component | Part number | Package | Notes |
|-----------|-------------|---------|-------|
| CPU | Intel Atom x7-A3960 (J238G327 e1, SREKE, 72MS459202251) | BGA on SOM | 14 nm Goldmont, quad-core. Hypervisor-reported clock 1.88 GHz; datasheet LFM/HFM/burst 0.8/1.6/2.0 GHz (`platform/hardware.md`) |
| RAM | 4× Micron MT53E512M32D2DS-053 (2TE77) | BGA on SOM | 8 GB LPDDR4, 2400 MT/s, dual-die 3733 Mbps |
| eMMC | Samsung KLMCG4JEUD (SEC 228, B04P, NT24G0046) | BGA-153 | 64 GB, eMMC 5.1 |
| IFWI/TXE boot flash | ISSI IS25WP064A-JHLA3 (P3B37364) | BGA | 8 MB NOR on CS0. Contains flash descriptor, TXE 3.0 firmware, UEFI, PMC firmware, microcode, SMIP, Boot Guard v2. Not dumped from this unit. |
| VIP MCU | Renesas RH850/F1K R7F7015873AFP (trace TM52176) | LFQFP176, 0.5 mm pitch, 24×24 mm | [C] G3KH core; 2 MB code flash, 64 KB data flash, 192 KB RAM, ≤120 MHz. System, power and vehicle-interface controller. Datasheet: `datasheets/Renesas_RH850_F1K_HW_manual_rev110.pdf` |
| VIP EEPROM | ST M24C64 (464RQ, K228) | TSSOP-8 | 8 KB I2C; SBI security flags |

### 4.2 Networking and connectivity

| Component | Part number | Package | Notes |
|-----------|-------------|---------|-------|
| Ethernet switch | Broadcom BCM89551B1BFBG (TN2224 P21, 395-34 P3 W) | BGA | BroadR-Reach automotive Ethernet. Board-variant IC: MY22/DV unit uses Broadcom, MY23+ boards use Marvell 88Q5050; same specification. Driver selection by `persist.vendor.harman.hardwareid` is [I]: the property is unreadable from shell uid, and `main.log` records an avc denial for `gm_update_engine` reading it. |
| Ethernet switch FW flash | ISSI IS25LP016D-JNLE | SOIC-8 | 2 MB NOR, BCM89551 firmware. Partial dump; IC damaged during extraction. |
| Ethernet MAC | Intel WGI210CL (I210) rev A3 (2214ASP) | QFN-48 | GbE for AVB audio; 25 MHz crystal. Some curated docs label it "I211"; the physical marking is I210. Port-speed settings: [`platform/ethernet_networking.md`](../../platform/ethernet_networking.md#23-shipped-switch-speeds-c-2026-11-13) |
| Wi-Fi / BT | Shielded module PN 4D+0847, EC-02 7A85H.G05 | Module, ~21.3×12.9×7.9 mm | — |
| Second RF module | Marked `7685H.G05` / `40488847` | Shielded module | [I] Adjacent to the A3960 module; separate from the Wi-Fi/BT module. Likely cellular or GNSS front end; not confirmed against a schematic. |
| USB-UART | Microchip MCP2200 | QFN | SXM-associated serial: AAOS `/dev/ttyACM1`, native Linux `/dev/ttyACM0`; 12 MHz crystal. Not a generic debug console (function corrected 2026-11-17 from SXeDL path and live policy). |
| CAN transceiver | NXP C26004 | TSSOP | HS-CAN interface |

Live Y181 radio (`W231E-Y181.3.2-SIHM22B-499.3`) carries the Marvell variant. Evidence (gmlogger
`main.log`, 2026-11-12 13:05): `ethmvlctrlmgr: vpdGetFwVersion: Marvell firmware version: 02_09_1003, config version:
234702AB`; `getModuleVersion module=52, version=MVL88Q5050_globalB_234702AB_02_09_1003`. Part
85759612 per `platform/firmware_versions.md`. Two physical units, two switch ICs, one spec. [C]

### 4.3 Audio and display

| Component | Part number | Package | Notes |
|-----------|-------------|---------|-------|
| Tuner / audio DSP | NXP SAF7751HN/207 (P0WR92.00, EtD22482) | BGA | AM/FM/HD tuner and audio processing |
| Audio amplifier | NXP TDF8532 | — | External; reached over AVB Ethernet |
| Display serializer | TI DS90UH949-Q1 (UH949Q, AT3S G4) | QFP-48 | FPD-Link III TX to display |
| Camera deserializer | TI DS90UB954-Q1 (UB954Q, AVG3 G4) | QFP-48 | FPD-Link III RX hub for cameras |
| Backlight driver | Analog Devices LT3899 (B64240) | QFN | Dual boost LED driver. [?] Role unconfirmed: no GHS- or native-Linux-controlled backlight driver was found on the SoC/I2C side. The live backlight path is an in-band I2C write (register `0x20`) to the faceplate controller at `0x12`, reached over FPD-Link through the DS90UH949-Q1/DS90UB948 serializer link (`video/display_subsystem.md`). The LT3899 may sit downstream of the faceplate controller, on the panel side of the link. |

### 4.4 Power

| Component | Part number | Package | Notes |
|-----------|-------------|---------|-------|
| Power MOSFET / regulator | 96E840 PEm (2305 E4, 5971) | D2PAK | ≥3 on board |
| Bulk capacitors | 470 µF/25 V, 220 µF/50 V, 47 µF/35 V | SMD electrolytic | Multiple |

## 5. Photo Cross-Check

Index of photos: `photos/README.md`.

| Item | Result |
|------|--------|
| A3960 compute module | Discrete sub-board carrying the SoC and all four LPDDR4 packages, with an adjacent shielded RF module (`photos/soc_a3960_ram_rf_module.jpeg`, `photos/soc_a3960_lpddr4_closeup.jpeg`). [C] |
| Module label | Service P/N 3765210 and Harman P/N 91.UMAF2HG.GS6FAAG legible (`photos/module_label_region.jpeg`, `photos/module_label_closeup.jpeg`). OCR variant "91.LUMAF2HG…" is the same part number. [C] |
| Second RF module | `7685H.G05` / `40488847`, see §4.2. [I] |
| PCB fabricator | AT&S; consistent with `photos/carrier_top_overview.jpeg`, `photos/carrier_bottom_overview.jpeg`. [C] |
| RH850, M24C64 | Legible close-ups: `photos/rh850_vip_region_on_board.png`, `photos/eeprom_m24c64_microscope.png`. [C] |
| Ethernet switch, DS90UB954, TDF8532 | Lid text not legible in any photo. Identification is from board-level teardown and firmware/driver cross-reference. [I] |

## 6. Sources

- ALLDATA vehicle profile CarId 65566 and factory RPO list for the test VIN.
- Teardown photographs listed in §5.
- Firmware logs: `main.log` (gmlogger), `platform/firmware_versions.md`.
