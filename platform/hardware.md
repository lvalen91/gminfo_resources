# GM Info 3.7 Hardware Specifications

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

## Hardware Component Summary

| Component | Spec |
|-----------|------|
| CPU | Intel Atom x7-A3960 (Goldmont/Apollo Lake), 4 cores, base 800MHz / HFM 1.6GHz / burst 2.0GHz [Intel 336256], 14nm, 12 W TDP @ TjMax [Intel 336256; corrected 2026-11-12 from "10W" — the 10 W figure is only the Y177 snapshot `thermal.tdp` in `gminfo3.7_tech_specs.md`, which the same file's `cpu.tdp: 12` and `intel_apl_external_resources.md` contradict], AEC-Q100 |
| Compute module | The Intel A3960 + RAM form a **discrete compute module** soldered on the Bosch/Harman carrier (photo-confirmed — see `hardware/photos/soc_a3960_ram_rf_module.jpeg`) |
| CPU Part# | LH8066803226000 |
| CPU ID | "IoT CPU 1.0" (cpu family 6, model 92, stepping 10) |
| CPU Clock | 1881.6 MHz (hypervisor-visible), BogoMIPS 3763.20 |
| CPU Cache | 1024 KB L2 per core |
| CPU Address | 39-bit physical, 48-bit virtual |
| DalvikVM ISA | x86_64, variant: silvermont |
| GPU | Intel HD Graphics 505 (Gen9, 18 EUs) at PCI `00:02.0` [C: Mesa renderer `VERIFICATION.md:114-115`; 18 EU = datasheet 336256]. The 300-750 MHz range is the Y177 snapshot (`gminfo3.7_tech_specs.md:41-42`); datasheet burst is 650 MHz (`:32`, `intel_apl_external_resources.md:158`), so 750 is [UNVERIFIED] (full-project searched 2026-10-10; no GPU frequency node is shell-readable) |
| GPU Driver | Intel iHD driver 2.0.0 [UNVERIFIED — full-project searched 2026-10-10; no iHD string in any Y175/Y181 capture; live evidence is Mesa 21.1.5 GLES renderer `VERIFICATION.md:114-115`, `ro.hardware.gralloc/hwcomposer=broxton` `all_properties.txt:464-465`] (GLES backend — Vulkan driver exists but NOT used at runtime) |
| RAM | 8 GiB LPDDR4 physical (4× 2 GiB Micron MT53E512M32D2DS-053, teardown-verified); static GHS guest grant 7830 MiB (+34 MiB RO IPU window), ~362 MiB outside that grant; historical Android `MemTotal` near 5530 MiB (5.40 GiB / 5.80 GB). **Updated 2026-11-12:** Y181B recovery E820 usable **5743.55859375 MiB**; early Linux denominator 5877304K. Grant-to-visible cause and normal-AAOS map parity unresolved; [measured map](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory). Historical `SwapTotal=0`, `Committed_AS` ~76 GB virtual. |
| Storage | 64GB Samsung KLMCG4JEUD eMMC |
| SPI Flash | IS25LP016D SPI NOR, 16Mbit/2MB, SOIC8, Quad SPI 3.3V, week 43/2022. Purpose: **Ethernet-switch firmware (BCM89551 on the MY22/DV teardown unit; the live Y181 bench radio carries a Marvell 88Q5050 — whether its switch firmware sits in the same NOR is not established, 2026-11-12)** (corrected per `hardware/teardown.md`, confirmed via partial dump — NOT "logs/backup"). NOTE: a separate **8MB IS25WP064A** (BGA) is the Apollo Lake IFWI/TXE boot flash (Flash Descriptor, TXE 3.0, UEFI, Boot Guard v2) — see teardown. |
| Display | Chimei Innolux DD134IA-01B, 2400x960 @ 60Hz, ~13.4" [C live: Y181 `dumpsys_display.txt:26,49-52`, CMN/41268, 60.001434 fps, single mode]. SoC-side output is **eDP** (`00:02.0` `card0-eDP-1` + `intel_backlight`, `vendor_sepolicy.cil:21-22`) [C live]; the panel link continues through the FPD-Link III serializer chain (`platform/vehicle_network.md:545`) |
| Display DPI | Physical: xDpi=192.911 yDpi=193.523; system lcd_density=200 (xhdpi) |
| Touchscreen | Atmel maXTouch, I2C bus 7 @ 0x4B (PCI `00:17.3` i2c_designware.7, `7-004b`) [C live: `vendor_sepolicy.cil:23`; IRQ thread `[irq/145-atmel_m]` Y181 `raw/processes.txt:123`; `CONFIG_TOUCHSCREEN_ATMEL_MXT=m` `kernel_config.txt:2397`]; the **16-point** figure comes only from the Y177 snapshot `platform/gminfo3.7_tech_specs.md:115` [UNVERIFIED on Y181: full-project searched 2026-10-10; no `getevent -p`/ABS_MT_SLOT artifact in any capture] |
| OpenGL ES | 3.2 (Mesa 21.1.5) |
| Kernel | Linux 4.19.305 LTS (Y181) / 4.19.283 (Y175) |
| VIP MCU | Renesas RH850/F1K (R7F7015873AFP; trace TM52176) — power, CAN, early boot, EEPROM |
| Hypervisor | GHS INTEGRITY IoT 2020.18.19 MY22-026 (Type-1 bare-metal) |
| WiFi | Broadcom BCM (802.11ac), driver `dhd` |
| Bluetooth | 5.0 |
| Ethernet | Intel **I210** GbE, 1Gbps, gPTP master, feeding the on-board automotive-Ethernet switch — **board-variant IC**: Broadcom BCM89551 on the MY22/DV teardown unit, **Marvell 88Q5050 on the live Y181 bench radio** (part 85759612, `MVL88Q5050_globalB_234702AB_02_09_1003`; `ethmvlctrlmgr` / `UpdateService-ModuleVersionUtil module=52` in `main.log`, 2026-11-12 [read]). Same spec, not a contradiction (only `I210` appears in artifacts; the `WGI210CL rev A3` variant marking is prose-only, not artifact-backed; "I211" was an unverified near-twin reading — see `hardware/teardown.md`). Shipped switch speeds and numbering caveat: [`networking.md`](networking.md#shipped-switch-speeds--c-2026-11-13), 2026-11-13. Kernel uses a custom `igb_avb` driver; mainline `igb`/`CONFIG_IGB` is disabled per the Jun-2026 capture |
| Audio HAL | Harman HarmanAudioControl — HAL interface `android.hardware.audio@5.0`, provided by service instance `vendor.hardware.audio@5.0-harman-custom-service` (confirmed: `aaos/gm_aaos/2024_Silverado_ICE/analysis/adb/Y181/.../processes.txt`); Dirana3 amplifier plugin, speakerNum=4, micNum=0. ("Titan" is the SoC platform codename, not the HAL name.) |
| Audio Transport | Ethernet AVB to NXP TDF8532 codec → external amplifier (CSM) |
| GPS | u-blox receiver, GPS+DR fusion, UART to GENIVI pipeline |
| EEPROM | ST M24C64, 8KB, I2C |

---

## CPU Details

Kernel identifies the processor as **"IoT CPU 1.0"** (cpu family 6, model 92, stepping 10). The hypervisor-visible reported clock is **1881.6 MHz** with a BogoMIPS of **3763.20**. Each core has **1024 KB** of L2 cache. Address space is **39-bit physical, 48-bit virtual**.

The DalvikVM ISA variant is **silvermont** (x86_64 architecture, 64-bit only).

### CPU Flags

- **Virtualization:** `hypervisor` flag confirms GHS virtualization visible to Linux guest
- **Hardware Crypto:** `aes`, `sha_ni`, `rdrand`, `rdseed`
- **Spectre Mitigations:** `ibrs`, `ibpb`, `stibp`, `ssbd`
- **Known CPU Bugs:** `spectre_v1`, `spectre_v2`, `spec_store_bypass`

---

## Display Details

- **Panel PnP ID:** "CMN" (Chimei/Innolux), product ID 41268, manufactured week 36/2020
- **VSYNC:** 16.666 ms
- **Presentation deadline:** 14.666 ms
- **HWC:** 2.1 (iahwcomposer — Intel Automotive HWComposer), explicit sync, high quality scaling, no DCIP3
- **Composition:** DEVICE + CLIENT composition, triple buffering, only 1 DRM display active (3 defined in hwc_display.ini)
- **System UI:** App Dock 189-190px left, Status Bar 118px top (`CardView_InitManager: cardViewHeight = 842, statusBarHeight = 118, heightPixels = 960`, see `analysis/platform_faq.md` CardView section), CardView 793px right → windowed content 1416-1417x842, 2400x960 (full) [CORRECTED 2026-10-10: earlier "95px top/bottom → 1416x770" contradicted the logged 842 and the CarPlay line below]
- **GM CarPlay windowed area:** 1416x842 (after subtracting bars), rendered at 30fps
- **HDR:** No HDR, no wide color gamut, no VRR (single 60Hz mode)
- **Max luminance:** 500 nits
- **Backlight:** min=0.035, max=1.0, default=0.398
- **Density:** 1.25 (200 DPI / 160 base)
- **Flags:** FLAG_SECURE and FLAG_SUPPORTS_PROTECTED_BUFFERS supported
- **SurfaceFlinger:** GLES backend, no blur support

---

## I2C Bus Topology

| Bus | Permissions | Owner | Use |
|-----|-------------|-------|-----|
| i2c-0 | crw-rw-rw- | root | EEPROM (M24C64 at 0x50) |
| i2c-1 | crw-rw-rw- | root | ELMOS antenna controller |
| i2c-2 | crw-rw-rw- | system | General system |
| i2c-3 | crw-rw-rw- | audioserver | TDF8532 codec control |
| i2c-4 to i2c-6 | crw------- | root | Reserved |
| i2c-7 | crw-rw---- | system | Atmel maXTouch (0x4B) touchscreen |
| i2c-8 to i2c-10 | crw------- | root | Reserved |

**Security note:** i2c-0 and i2c-1 are world-writable, which is a potential security concern (EEPROM and antenna controller accessible by any process).

**Additional devices:** Faceplate controller at 0x12. GYRO/ACCEL sensors not present.

---

## Dual-Processor Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Intel Atom x7-A3960 (SoC)                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ GHS INTEGRITY IoT 2020.18.19 MY22-026 (Type-1, bare-metal) │ │
│ │ ┌───────────────────┐  ┌──────────────────────────────────┐ │ │
│ │ │ GHS Tasks (14+)   │  │ Android 12 (Guest VM)            │ │ │
│ │ │ AVB verify        │  │ AAOS + Harman + GM services      │ │ │
│ │ │ kethernet TCP/IP  │  │ CarPlay (CINEMO/NME)             │ │ │
│ │ │ IPU4 camera       │  │ Android Auto (AOSP)              │ │ │
│ │ │ TEE keymaster     │  │ OnStar / Diagnostics             │ │ │
│ │ │ GHS cal service   │  │                                  │ │ │
│ │ │ GHS logger        │  │                                  │ │ │
│ │ └───────────────────┘  └──────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HDLC over UART /dev/ttyS1 (20 IPC channels 1-20, protocol v16)
┌─────────────────▼───────────────────────────────────────────────┐
│ Renesas RH850/F1K (R7F7015873AFP) — VIP MCU                     │
│ Power management, CAN gateway, early boot, EEPROM, PLC timers  │
└─────────────────────────────────────────────────────────────────┘
```

The system uses a dual-processor architecture where the Intel Atom x7-A3960 SoC handles all application-level processing under a GHS INTEGRITY Type-1 hypervisor, while the Renesas RH850/F1K VIP MCU manages low-level vehicle functions including power sequencing, CAN bus gateway, early boot, EEPROM access, and PLC timers.

Communication between the two processors occurs over HDLC on UART `/dev/ttyS1` with 20 IPC channels (numbered 1-20; confirmed: `hardware/teardown.md` IPC Channel Map) using protocol version 16. The GHS hypervisor runs as bare-metal on the Intel SoC, with Android 12 running as a guest VM alongside 14+ native GHS tasks for AVB verification, Ethernet networking, camera processing, TEE keymaster, calibration services, and logging.

---

## VIP MCU (Renesas RH850/F1K)

Identification corrected 2026-11-12: **R7F7015873AFP**, marking **15873**, 176-pin LFQFP.
**TM52176 is a trace code.** Owner-reported VIP console TX is **pin 52 / P1_9 / RLIN34TX**;
pin 53 provides the matching RX function, with reception unverified. Package evidence,
manual and full UART table: [hardware teardown](../hardware/teardown.md#rh850f1k-package--uart-pinout).

> **Low-power sleep (external corroboration [X]).** Surrealdev *"Rooting the Cadillac Part 1"*
> (Snipesy, 2026-08-15; `https://surrealdev.com/rooting-the-cadillac-part-1-lay-of-the-land/` —
> canonical bibliography in [`qualcomm_cadillac_platform.md`](qualcomm_cadillac_platform.md) →
> Sources) reports the RH850 "VIP" powers *itself* down in deep sleep and wakes on a hardware signal direct
> from its **CAN phy**, letting the whole radio idle at **sub-milliamp** draw on the always-on 12 V
> feed. Consistent with this board's VIP role (power/CAN/early-boot); the sub-mA figure is the
> author's Cadillac measurement, **not independently confirmed on this A11 unit.** [X]

### PLC Timers

| Timer | Duration |
|-------|----------|
| SoH Timeout | 1500 ms |
| Shutdown | 3500 ms |
| Startup | 6000 ms |
| Unmount | 800 ms |
| Hypervisor Startup | 300 ms |

### VIP Calibration Values

31+ values stored in EEPROM/NVM, applied at every boot:

**Power:**
- `cal_background_sleep_timeout_sec` = 10
- `cal_sleep_fault_timeout_sec` = 900
- `cal_startup_fault_timeout_sec` = 15
- `cal_suspend_to_ram_en` = 1
- `cal_str_min_temp_threshold` = -10

**Infotainment:**
- `cal_veh_initiated_local_infotainment_timeout` = 600
- `cal_user_initiated_local_infotainment_timeout` = 600

**Display:**
- `cal_cluster_animation_ignore` = 0
- `cal_rsi_animation_ignore` = 1

**Debug:**
- `cal_vin_relearn_en` = 1
- `cal_maximum_flush_fault_time` = 36000

### VIP Calibration Index System

15 indexed groups sent VIP → SoC at every boot:

| Index | Size | Description |
|-------|------|-------------|
| 0 | 154 B | System config |
| 1 | 128 B | Audio/chime |
| 2 | 17 B | Mic |
| 3 | 21 B | DTC mask |

---

## IPC Protocol Details

| Parameter | Value |
|-----------|-------|
| Version | 4.1.0 |
| API | 0404 |
| Framing | HDLC |
| Window Size | 5 |
| IFRAME Timeout | 50 ms |
| UFRAME Timeout | 20 ms |
| Line rate | 1 Mbps (VIP `IPCServer` on /dev/ttyS1; confirmed: `hardware/teardown.md`) |

**Module init order:** SS_SWC → PLC → J6_CDD → IPC_S → AMP_MGR_SWC → PROTOKEY → SBAT → IOHWAB_MIC → NAV

---

## GHS Hypervisor Details

### Binary Format

GHS INTEGRITY binary: ELF header claims 32-bit LSB (Intel 80386) but **the code is x86-64** (CORRECTED 2026-08-26: `movabs`/REX, `crt_x64.86` — disassemble as `x86:LE:64`; the "32-bit compatibility mode" claim was an invented rationalization and is retracted), statically linked. VMM uses Intel VT-x with 64-bit EPT for Android guest.

### GHS Device Interfaces

Accessible under `/dev/ghs/`:

| Device | Purpose |
|--------|---------|
| ipc | Inter-processor communication |
| cal | Calibration service |
| chime | Turn signal/seatbelt/door chime generation |
| camera (ghs_camera_device) | Backup camera bypass |
| tee-att | TEE attestation |
| audit | Security audit log |
| textlog | Text logging |
| snapshot-dbg | Debug snapshots |
| emmc-health | eMMC health monitoring |
| ota-isys | OTA update interface |
| gpu-dbg | GPU debug |

### GHS Camera Bypass

Backup camera works **DURING Android reboot**. GHS receives CAN gear position and directly controls display overlay, independent of the Android guest. The `earlyEvs_harman` module exists but is **COMMENTED OUT** in the configuration — GHS handles camera directly without it.

---

## Kernel Configuration Highlights

| Category | Setting |
|----------|---------|
| Preemption | PREEMPT=y (full preemptive) |
| Timer | HZ=1000 |
| Scheduler | SCHED_TUNE + FAIR_GROUP_SCHED |
| Titan-specific | TITAN_X86_BROXTON_PROGRAM, APL_MY22_ANDROID, I2C_BUS_NUMBER_HACK |
| VirtIO | BLK / CONSOLE / PCI (GHS guest I/O) |
| DRM | I915 built-in |
| Audio | HDA_CORE=m (module) |
| Compression | LZ4 |
| Compiler | Clang 12.0.7 |

---

## DalvikVM Configuration

| Parameter | Value |
|-----------|-------|
| heapsize | 512m |
| heapgrowthlimit | 288m |
| dex2oat-threads | 2 (cores 0, 1) |
| usejit | true |
| zygote | zygote64 (64-bit only, no 32-bit) |

---

## System Properties

| Property | Value |
|----------|-------|
| persist.sys.cal.brand | GM_Brand_Chevrolet |
| persist.sys.cal.model | Silverado |
| ro.product.name / ro.boot.hardware | full_gminfo37_gb |
| ro.boot.bootloader | 2344 |
| ro.soc.model | A3960 |
| ro.boot.product.hardware.sku | gv221 |
| persist.sys.wifi.only2g | 1 |
| config.disable_cameraservice | 1 |
| ro.radio.noril | true |

> **Verified live 2026-11-12 (Y181 `W231E-Y181.3.2-SIHM22B-499.3`, `adb shell getprop`):** all rows above
> [read]; `ro.boot.product.hardware.sku=gv221`. The `androidboot.product.hardware.sku` spelling returns empty
> (only the `ro.boot.` form is populated). **`persist.vendor.gm.brand` / `.model` are NOT present** on the real radio —
> only `persist.sys.cal.brand/.model` (see `vehicle_config.md`). `persist.vendor.harman.hardwareid` is unreadable from
> the shell uid (empty; `main.log` shows an avc denial on `persist_vendor_harman_hardwareid_prop` for `gm_update_engine`).
> **Addendum 2026-11-12:** the value IS present in the `/cache` gmlogger `props` snapshots (29 of 30 boots): `persist.vendor.harman.hardwareid=MY23DV1` (also `persist.vendor.veh.variant=GB`, `persist.vendor.hw.variant=0xB1020260` in all 30) [read from the dump, not from the live shell]. `MY23`-class id agrees with the Marvell module string; that the prop is what selects the switch driver remains inferred.
> Kernel `4.19.305-240125T145315Z-gf1edde901aa7` x86_64, `ro.build.version.security_patch=2025-06-05`.

### Hardware-variant word (`hw.conf`)

`/update_cache/update/hw.conf` holds the ASCII string `0xB1020260` (live Y181 bench, 2026-11-12). The recovery log decodes it:

| Field | Value |
|-------|-------|
| Variant | 177 (decoder's label; its relation to the "Y177" firmware label is undefined — forensic U13) |
| Global / Region | 0 / 0 |
| Project | 2 |
| HD radio / DAB / GPS option | 0 / 0 / 0 |
| AMP | 1 |
| SXM | 1 |
| Gyro+Accel / Gyro / Accel | 0 / 0 / 0 |

Source: `recovery/last_log*` line `Value: 0xB1020260  Variant: 177 Global: 0 Region: 0 Project: 2 HD: 0 AMP: 1 SXM: 1 DAB: 0 GPS: 0 ...`
and `HW variant is 0xB1020260` [read]. Consistent with the donor truck's U2K (SiriusXM) and UQA (branded amp) RPOs in
`vehicle_config.md` [inferred]. The bit layout (which nibbles map to which field) is taken from the decoder's own printout, not reverse-engineered here.

---

## Vehicle Integration

### GHS-Dependent (work without Android)

These functions operate at the hypervisor/VIP level and remain functional even if Android is rebooting or crashed:

- Turn signal chimes
- Door chimes
- Seatbelt chimes
- Reverse backup camera
- 360 surround view

### Android-Dependent

These functions require the Android guest VM to be running:

- Climate display
- Steering wheel button processing
- Navigation
- Audio playback / media
- CarPlay / Android Auto

---

## Vehicle Identification

| Field | Value |
|-------|-------|
| Vehicle | 2024 Chevrolet Silverado (ICE) |
| GMModel | 4 |
| GMBrand | 3 (Chevrolet) |
| GMTrim | 16 |
| Build | W231E-Y181.3.2-SIHM22B-499.3 |
| Hardware SKU | gv221 |
| Build Fingerprint | gm/full_gminfo37_gb/gminfo37:12/W231E-Y181.3.2-SIHM22B-499.3/231:user/release-keys |
