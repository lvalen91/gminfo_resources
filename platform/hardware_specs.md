# GM Info 3.7 (gminfo37) Hardware Specifications

Component spec sheet for the gminfo37 head unit: SoC, GPU, RAM, storage, display panel, input, audio/codec hardware, USB, thermal, power, UART console map, I2C bus topology, and Intel A3960 datasheet facts.
Excludes VIP/IPC/GHS (see [vip_ipc_ghs.md](vip_ipc_ghs.md)), boot flow, networking and native-Linux probe logs (pointers below). Merges the former `gminfo3.7_tech_specs.md` (retired to archive) and the datasheet section of `intel_apl_external_resources.md`.

**Device:** GM Info 3.7 (gminfo37) | **Platform:** Intel Apollo Lake (Broxton) | **Android:** 12 (API 32) | **Research:** Dec 2025 - Nov 2026

**Evidence legend:** `[C]` / `[C live]` live-captured; `[read]` read from artifact; `[inferred]`; `[X]` external; `[UNVERIFIED]` no supporting artifact found; `[Intel 336256]` Intel Atom E3900/A3900 Datasheet Addendum 336256-004US (local copy: [`../hardware/datasheets/Intel_336256_Atom_E3900_A3900_datasheet_addendum_rev004.pdf`](../hardware/datasheets/Intel_336256_Atom_E3900_A3900_datasheet_addendum_rev004.pdf); full register map in the main E3900 datasheet 334819); "teardown-verified" / "owner-confirmed" as stated.

**Related:** [vip_ipc_ghs.md](vip_ipc_ghs.md), [boot_chain.md](boot_chain.md), [partitions_storage.md](partitions_storage.md), [elk_recovery.md](elk_recovery.md), [firmware_versions.md](firmware_versions.md), [ethernet_networking.md](ethernet_networking.md), [avb_audio_transport.md](avb_audio_transport.md), [eeprom_i2c_security.md](eeprom_i2c_security.md), [vehicle_config.md](vehicle_config.md), [security.md](security.md), [external_references.md](external_references.md); [../hardware/teardown.md](../hardware/teardown.md), [../hardware/connectors.md](../hardware/connectors.md), [../video/display_subsystem.md](../video/display_subsystem.md).

---

## 1. Component summary

Platform-wide values; Y177 = snapshot build W231E-Y177.6.1, Y181B = W231E-Y181.3.2 (see [firmware_versions.md](firmware_versions.md)).

| Component | Spec |
|---|---|
| CPU | Intel Atom x7-A3960 (Goldmont / Apollo Lake), 4 cores, 4 threads, LFM 800 MHz / HFM 1.6 GHz / burst 2.0 GHz [Intel 336256], 14 nm, 12 W TDP @ TjMax [Intel 336256], AEC-Q100, Tcase -40..+98 C |
| Compute module | The Intel A3960 + RAM form a **discrete compute module** soldered on the Bosch/Harman carrier (photo-confirmed: `hardware/photos/soc_a3960_ram_rf_module.jpeg`); BGA1296, soldered |
| CPU part # | LH8066803226000 |
| CPU ID | "IoT CPU 1.0" (cpu family 6, model 92, stepping 10) |
| CPU clock | 1881.6 MHz (hypervisor-visible), BogoMIPS 3763.20 |
| CPU cache | 1024 KB L2 per core in guest view; datasheet: 2 MB L2 shared |
| CPU address | 39-bit physical, 48-bit virtual |
| DalvikVM ISA | x86_64, variant `silvermont` |
| GPU | Intel HD Graphics 505 (Gen9, 18 EUs) at PCI `00:02.0` [C: Mesa renderer `VERIFICATION.md:114-115`; 18 EU = datasheet 336256]. Datasheet freq LFM/HFM/Burst 100/500/650 MHz. See Open conflicts for 650 vs 750 MHz. |
| GPU driver | Intel iHD driver 2.0.0 [UNVERIFIED; full-project search 2026-10-10 found no iHD string in any Y175/Y181 capture]. Live evidence: Mesa 21.1.5 GLES renderer (`VERIFICATION.md:114-115`), `ro.hardware.gralloc/hwcomposer=broxton` (`all_properties.txt:464-465`). GLES backend; Vulkan driver exists but is NOT used at runtime. |
| OpenGL ES | 3.2 (Mesa 21.1.5) |
| RAM | 8 GiB LPDDR4 physical (4x 2 GiB Micron MT53E512M32D2DS-053, teardown-verified). Static GHS guest grant 7830 MiB (+34 MiB RO IPU window), ~362 MiB outside that grant. Guest visible memory: see section 3. |
| Storage | 64 GB Samsung KLMCG4JEUD eMMC (see section 4) |
| SPI flash | IS25LP016D SPI NOR, 16 Mbit / 2 MB, SOIC8, Quad SPI 3.3 V, week 43/2022. Purpose: **Ethernet-switch firmware** (BCM89551 on the MY22/DV teardown unit; the live Y181 bench radio carries a Marvell 88Q5050 and whether its switch firmware sits in the same NOR is not established, 2026-11-12). Corrected per `hardware/teardown.md`, confirmed via partial dump: NOT "logs/backup". A separate **8 MB IS25WP064A** (BGA) is the Apollo Lake IFWI/TXE boot flash (Flash Descriptor, TXE 3.0, UEFI, Boot Guard v2); see teardown. |
| Display | Chimei Innolux DD134IA-01B, 2400x960 @ 60 Hz, ~13.4" (section 6) |
| Touchscreen | Atmel maXTouch, I2C bus 7 @ 0x4B (section 8) |
| Kernel | Linux 4.19.305 LTS (Y181) / 4.19.283 (Y175) |
| VIP MCU | Renesas RH850/F1K (R7F7015873AFP; trace TM52176): power, CAN, early boot, EEPROM. Details: [vip_ipc_ghs.md](vip_ipc_ghs.md) |
| Hypervisor | GHS INTEGRITY IoT 2020.18.19 MY22-026 (Type-1 bare-metal). Details: [vip_ipc_ghs.md](vip_ipc_ghs.md) |
| WiFi | Broadcom BCM (802.11a/b/g/n/ac, 2.4 + 5 GHz, hotspot supported), driver `dhd`; native Linux enumerates BCM4359 14e4:43ef |
| Bluetooth | 5.0; profiles HFP, A2DP, AVRCP, PBAP, MAP, HID; name `myChevrolet` |
| Ethernet | Intel **I210** GbE, 1 Gbps, gPTP master, feeding the on-board automotive-Ethernet switch. **Board-variant switch IC:** Broadcom BCM89551 on the MY22/DV teardown unit, **Marvell 88Q5050 on the live Y181 bench radio** (part 85759612, `MVL88Q5050_globalB_234702AB_02_09_1003`; `ethmvlctrlmgr` / `UpdateService-ModuleVersionUtil module=52` in `main.log`, 2026-11-12 [read]). Same spec, not a contradiction. Only `I210` appears in artifacts; the `WGI210CL rev A3` variant marking is prose-only; "I211" was an unverified near-twin reading (see `hardware/teardown.md`). Kernel uses a custom `igb_avb` driver; mainline `igb`/`CONFIG_IGB` is disabled per the Jun-2026 capture. eth0 MAC `02:04:00:00:01:00`, VLANs vlan4 172.16.4.100 and vlan5 192.168.1.100 (Y177 snapshot). Switch speeds / numbering: [ethernet_networking.md](ethernet_networking.md). |
| Audio HAL | Harman HarmanAudioControl: HAL interface `android.hardware.audio@5.0`, provided by service instance `vendor.hardware.audio@5.0-harman-custom-service` (confirmed: `aaos/gm_aaos/2024_Silverado_ICE/analysis/adb/Y181/.../processes.txt`); Dirana3 amplifier plugin, speakerNum=4, micNum=0. ("Titan" is the SoC platform codename, not the HAL name.) |
| Audio transport | Ethernet AVB to NXP TDF8532 codec -> external amplifier (CSM). See [avb_audio_transport.md](avb_audio_transport.md). |
| GPS | u-blox receiver, GPS+DR fusion, UART to GENIVI pipeline |
| EEPROM | ST M24C64, 8 KB, I2C. See [eeprom_i2c_security.md](eeprom_i2c_security.md). |

---

## 2. CPU details

Kernel identifies the processor as **"IoT CPU 1.0"** (cpu family 6, model 92, stepping 10). Hypervisor-visible clock **1881.6 MHz**, BogoMIPS **3763.20**. **1024 KB** L2 per core (guest view). **39-bit physical, 48-bit virtual** address space. DalvikVM ISA variant **silvermont** (x86_64, 64-bit only).

### Datasheet-confirmed SoC (A3960 column, [Intel 336256])

A3900 = the **automotive**, AEC-Q100 Apollo Lake-I line (customer = automotive only). The gminfo37 SoC is the top SKU **A3960**.

| Spec | A3960 | Note |
|---|---|---|
| Cores (Goldmont) | **4** | no HT; 2 MB L2 shared |
| CPU freq LFM/HFM/**Burst** | 800 MHz / 1.6 GHz / **2.0 GHz** | corrects the common "2.4 GHz" figure; datasheet burst is 2.0 GHz |
| GPU | **HD Graphics 505** (Gen9 LP), **18 EU** | freq LFM/HFM/Burst 100/500/650 MHz; industrial-reliability 400 MHz |
| ISP (IPU) freq | 200/550/700 MHz | CSI D-PHY 1.1 imaging |
| TDP @ TjMax | **12 W** | S0i3/S3/S5 18/16/16 mW @ 30 C |
| Memory | **LPDDR4 <=2400 MT/s**, non-ECC; DDR3L-ECC option | max 8 GB, 4 channels (physical RAM here = 8 GB) |
| Temp | **Tcase -40..+98 C, Tj -40..+110 C** | AEC-Q100 |
| Process | 14 nm | Apollo Lake-I |

The earlier note that the `A3960` model string in the tech-specs file was "garbled" was a terminal display artifact, not file content. For `gm_emu`, this pins the QEMU `-cpu` family/model and `tsc-frequency`. Industrial twin with the same silicon: Intel ARK Atom x7-E3950 (HD 505, 18 EU, 2 MB L2, LPDDR4-2400, 8 GB).

Y177 snapshot cpu keys (cpufreq-observed): freq_base 800, freq_lfm 800, freq_hfm 1600, freq_boost 2000 (datasheet burst, not 2.4), cache_l2 2 (MB), tdp 12, tcase_range_c [-40, 98], memory_support LPDDR4_2400_max_8GB_4ch, gpu_burst_mhz 650.

### CPU flags

- **Virtualization:** `hypervisor` flag confirms GHS virtualization visible to the Linux guest
- **Hardware crypto:** `aes`, `sha_ni`, `rdrand`, `rdseed`
- **Spectre mitigations:** `ibrs`, `ibpb`, `stibp`, `ssbd`
- **Known CPU bugs:** `spectre_v1`, `spectre_v2`, `spec_store_bypass`

Native-Linux observation (different context): `intel_pstate` performance governor with 800-2400 MHz limits is driver-reported, not a sustained-load measurement (Probe05; see [elk_recovery.md](elk_recovery.md)).

---

## 3. Memory

| Item | Value | Source |
|---|---|---|
| Physical | 8 GiB LPDDR4 (4x Micron MT53E512M32D2DS-053), teardown-verified | `physical_capacity: 8192` |
| SoC max | 8 GB LPDDR4-2400, 4 ch (consistent with fitted 8 GB) | [Intel 336256] |
| GHS guest grant | **7830 MiB** DRAM (byte-confirmed from the boottable, not an over-count) + **34 MiB** RO IPU window | [FW 85098662; 3-Opus 2026-10-10] |
| GHS reserved | **~362 MiB** below 4 GiB | same |
| Guest `MemTotal` (historical, Y177-era) | **5530 MiB** (5.40 GiB / 5.80 GB) | Android |
| Y181B recovery E820 usable | **5743.55859375 MiB**; early Linux denominator 5877304K | exports, 2026-11-12 |
| Native Linux 7.3.5 Probe05 `MemTotal` | 5,963,784 KiB (~5,766,976 KiB available), no swap | native probe |
| Swap / commit | Historical `SwapTotal=0`, `Committed_AS` ~76 GB virtual (`committed_oversubscription: 88800`, unexplained in source) | |

The reason the E820 total differs from the static grant, and normal-AAOS map parity, are unresolved; the old 5780 MiB / RAM4-cap explanation is unconfirmed. The old "604 MB reserved" / "6 GB to guest" figures are unsourced; "5.66 GB" is a unit slip. Canonical measured map: [../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory).

Y177 snapshot (MiB): `total: 5530` `available: 3584` `utilization: 56%` `ram_model: LPDDR4_shared` `swap: 0`.

---

## 4. Storage

- **eMMC:** 64 GB Samsung KLMCG4JEUD; boot device at PCI `00:1c.0` per guest cmdline. In native Linux the node name changes between `mmcblk2` and `mmcblk1` across boots, so identify the physical device before using a path. Native Probe05: 124,993,536 user sectors, 26 partitions, boot0/boot1 each 65,280 sectors and read-only. First-4096-byte SHA256 `f9285861c75b06d2d3838ef0638f4ab90eb3e85cadec25c3f68e67e7aedfe0ac` matched the verified saved dump (not a second whole-device verification). RPMB was not retried.
- **SPI NOR:** see section 1 (IS25LP016D 2 MB switch firmware; IS25WP064A 8 MB IFWI/TXE boot flash).
- **Boot Guard / IFWI:** Boot Guard + TXE/CSE (HECI) sit on the Intel compute-module side, the pre-GHS trust stage, stored in the module's ISSI SPI-NOR IFWI (separate from the carrier eMMC holding GHS + Android). See [boot_chain.md](boot_chain.md).
- **Y177 snapshot partition usage (MiB):** total 65536, available 40960; data 39936 (used 4300, avail 35636); system 2969 (used 2785, avail 184); vendor 438 (used 428, avail 1; flagged `vendor_100_percent_full`); product 2458 (used 2274, avail 184). Partition map and Y175/Y181 reconciliation: [partitions_storage.md](partitions_storage.md).

---

## 5. GPU, graphics and video decode

| Item | Value |
|---|---|
| Model / PCI | Intel HD Graphics 505, `0000:00:02.0`, Gen9 Apollo Lake 14 nm, 18 EUs; native Linux PCI ID 8086:5a84 |
| Frequency (Y177 snapshot) | base 300, boost 750, current 300 MHz; datasheet 100/500/650 (Open conflicts) |
| Memory | shared system DDR |
| Max displays / interfaces | 3 (DP, eDP, HDMI 1.4); `hwc_display.ini` defines 3, only 1 DRM display active |
| API | OpenGL ES 3.2; Vulkan 1.1.128 in Y177 snapshot vs Y181 live (Jun-2026) API version Vulkan 1.1.0 (raw 4198400 = 0x401000), 1.1.128 likely a driver/conformance build; Vulkan unused at runtime (GLES 3.2 backend); Y177 `directx: 12.1` |
| Secure playback | true |
| GVT-g | HD 505 Gen9 is the GVT-g-capable IGD that GHS mediates. The datasheet does not document GVT-g (an Intel software feature) [UNVERIFIED from the datasheet; confirmed in the GHS blob `.gvtg_server` / `gen9_passthru`]. |
| Native Linux rendering | Native GPU shader rendering, Vulkan device initialization and VA-API profile availability verified: [../video/hardware_rendering.md#native-linux-gpu-acceleration--verified-2026-11-17](../video/hardware_rendering.md#native-linux-gpu-acceleration--verified-2026-11-17) |

### Hardware video decoders (Y177 snapshot, Android MediaCodec)

| Codec | Component | HW accel | Max res / fps | Profiles | Measured fps | Secure |
|---|---|---|---|---|---|---|
| H.264 | `OMX.Intel.hw_vd.h264` | yes | 3840x2160 / 60 | Baseline_5.1, Main_5.1, High_5.1, ConstrainedHigh_5.1 | 1280x720: 460-590; 1920x1088: 320-360 | yes |
| HEVC | `OMX.Intel.hw_vd.h265` | yes | 3840x2160 / 60 | Main_5.1, Main10_5.1 | 1280x720: 250-500; 1920x1080: 190-400; 3840x2160: 120-130 | yes |
| VP8 | `OMX.Intel.hw_vd.vp8` | yes | 3840x2160 / 60 | n/a | 1280x720: 200-400; 1920x1080: 150-330 | n/a |
| VP9 | `OMX.Intel.hw_vd.vp9` | yes | 3840x2160 / 60 | Profile_0_5.2, Profile_2_5.2, Profile_2HDR_5.2 | 1280x720: 400-600; 1920x1080: 350-420; 3840x2160: 100-130 | n/a |
| AV1 | `c2.android.av1.decoder` | **no (software only)** | 2048x2048 | Main8_5.3, Main10HDR10_5.3, Main10HDRPlus_5.3 | n/a | n/a |

Also decode flags: HEVC 8/10-bit, VP9, VC1 true. Gen9 HD505 has NO AV1 hardware decode.

---

## 6. Display panel

- **Panel:** Chimei Innolux **DD134IA-01B**, 2400x960 @ 60 Hz, ~13.4" (13.39" diagonal; 316x126 mm) [C live: Y181 `dumpsys_display.txt:26,49-52`, CMN/41268, 60.001434 fps, single mode]. Color depth 8 bit, native color mode only, landscape rotation 0, mode_id 1.
- **Panel PnP ID:** "CMN" (Chimei/Innolux), product ID 41268, manufactured week 36/2020.
- **Physical DPI:** xDpi=192.911, yDpi=193.523; system `lcd_density=200` (xhdpi); density 1.25 (200 DPI / 160 base).
- **Timing:** VSYNC 16.666 ms (vsync_offset 2,500,000 ns); presentation deadline 14.666 ms (14,666,268 ns). Native HDMI-A-1 mode 2400x960@60, 153.98 MHz pixel clock.
- **Link:** the DS90UB949 serializer chain takes **HDMI** input; native Y175 probe04 uses forced HDMI-A-1 (corrected 2026-11-17; see [display ownership and initialization](../video/display_subsystem.md#y175-panel-ownership-and-initialization--verified-2026-11-17)). The SELinux policy contains eDP/`intel_backlight` paths, but these are not active-connector proof.
- **HDR:** none; no wide color gamut, no VRR (single 60 Hz mode). **Max luminance** 500 nits. **Backlight** min=0.035, max=1.0, default=0.398 (`brightness_default 0.39763778`).
- **HWC:** 2.1 (`iahwcomposer`, Intel Automotive HWComposer), explicit sync, high quality scaling, no DCI-P3. DEVICE + CLIENT composition, triple buffering. **SurfaceFlinger:** GLES backend, no blur support. **Flags:** FLAG_SECURE and FLAG_SUPPORTS_PROTECTED_BUFFERS supported.
- **System UI geometry:** App Dock 189-190 px left, Status Bar 118 px top (`CardView_InitManager: cardViewHeight = 842, statusBarHeight = 118, heightPixels = 960`; see `analysis/platform_faq.md` CardView section), CardView 793 px right, windowed content 1416-1417x842 within 2400x960 full. History: corrected 2026-10-10; the earlier "95 px top/bottom -> 1416x770" contradicted the logged 842 and the CarPlay line.
- **GM CarPlay windowed area:** 1416x842 (after subtracting bars), rendered at 30 fps.
- Y177 touch_dimensions [2400, 960].

Gating of display behaviour by SystemUI: [gmsystemui_app_gating.md](gmsystemui_app_gating.md).

---

## 7. Camera capture hardware

- The SoC capture engine is **Intel IPU4** (PCI 8086:5a88). The external camera deserializer documented on the teardown board is **TI DS90UB954** (FPD-Link III -> CSI-2); see [camera connector evidence](../hardware/connectors.md) and [TI documentation](https://www.ti.com/product/DS90UB954-Q1). Exact population and wiring on the running bench board remain separate from teardown evidence.
- ACPI `ADV7481A/B` entries are unbound declarations, not proof those chips are populated.
- IPU firmware `ipu4_cpd_b0.bin` missing in native Probe05 caused a -110 fallback failure (not proof of an absent camera); the IPU drives the RVC path. CSI D-PHY 1.1 camera inputs are datasheet-confirmed. Native results: [elk_recovery.md](elk_recovery.md).

---

## 8. Input

| Device | Spec |
|---|---|
| Touchscreen | Atmel maXTouch, I2C bus 7 @ 0x4B (PCI `00:17.3` `i2c_designware.7`, `7-004b`) [C live: `vendor_sepolicy.cil:23`; IRQ thread `[irq/145-atmel_m]` Y181 `raw/processes.txt:123`; `CONFIG_TOUCHSCREEN_ATMEL_MXT=m` `kernel_config.txt:2397`]. Resolution 2400x960, event1, pressure 0-255, gestures true, palm rejection true. The **16-point** multitouch figure comes only from the Y177 snapshot [UNVERIFIED on Y181: full-project search 2026-10-10; no `getevent -p` / ABS_MT_SLOT artifact in any capture]. Native Linux: maXTouch responds to proper 16-bit-addressed reads (reads begin `a4 3e 10 aa 21 40`) but has no input-device/IRQ binding. |
| Faceplate controller | I2C bus 7 @ 0x12 (`i2c_7_0012`), event2, hardware buttons, keylayout `/system/usr/keylayout/Faceplate_Controller.kl` |
| Sensors | GYRO/ACCEL sensors not present |

---

## 9. Audio hardware

| Item | Value |
|---|---|
| HAL / service | `android.hardware.audio@5.0` via `vendor.hardware.audio@5.0-harman-custom-service`; Harman custom DSP; Dirana3 amplifier plugin, speakerNum=4, micNum=0 |
| Codec control | TDF8532 on i2c-3 (owner `audioserver`) |
| Sample rates | 8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 96000 |
| Channels / effects | max 8; AEC, NS, AGC, preprocessing |
| Virtual buses (Y177 snapshot) | 8; **live `media.audio_policy` 2026-11-15: 12 output buses (0-8 and 11-13)**; `audio_zones: unverified` (logical buses do not establish zone count) |
| Latency target | 50 ms |
| Outputs / inputs | speaker, bluetooth, usb, line_out / microphone, bluetooth, line_in |
| Transport | Ethernet AVB -> NXP TDF8532 -> external amplifier (CSM) |

Native Linux 7.3.5: HDA/SST-class 8086:5a98 enumerated without a bound PCI driver; ALSA reports no soundcards; codec/DSP/board routing unresolved. Kernel `HDA_CORE=m`. Audio path and AVB: [avb_audio_transport.md](avb_audio_transport.md).

---

## 10. USB

| Item | Value |
|---|---|
| Controller | Intel xHCI; native Linux also has a DWC3 device/gadget (ACM/NCM) |
| Mode | host mode true, OTG false, multiple ports, adb enabled |
| Aptiv bridges | 2x H2H, VID 10646 / PID 261 (decimal, as logged) |
| Aptiv PD hubs | 2x GM V10 E2, VID 10646 / PID 306 |
| Aptiv DFU | 2x Vendor DFU, VID 10646 / PID 288 |
| MCP2200 | VID 1240 / PID 223 (04d8:00df), SXM serial bridge; function corrected 2026-11-17; AAOS ttyACM1 |

Values are as written in the Y177 snapshot (`10646:261` H2H, `10646:306` PD hub, `10646:288` DFU, `1240:223` MCP2200).

**MCP2200 topology (owner-confirmed, 2026-11-17):** the only known externally connected radio USB port is wired to the host computer for ADB/USB shell. No user-attached peripheral accounts for MCP2200 04d8:00df, so its xHCI-side CDC-ACM/HID enumeration is an internal radio device; the DWC3 device/gadget connection to the host is a separate USB role/path. The historical device record maps VID 1240 / PID 223 (04d8:00df) to AAOS ttyACM1; the mounted Y175 SXeDL APK explicitly contains `/dev/ttyACM1`, and live-AAOS evidence labels that node `sxm_device`. Together these associate the internal bridge with the SXM serial path, not a generic debug console. Native Linux enumerates it as ttyACM0 (gadget ttyGS0 also available). No SXM protocol traffic was sent or captured to validate operation in native Linux.

Bluetooth, GNSS, AM/FM, SXM, external amplifiers, camera feeds and VIP-side peripherals were not established as operational by the native Linux pass; their existence in the product does not imply a directly enumerated Linux device.

---

## 11. UART / console map

Datasheet ground truth [Intel 336256]: **4 HSUART (LPSS) controllers**, automotive assignment `1x Discrete GNSS (UART1)`, `1x Host OS Debug (UART2)`, `2x Generic (UART0 and UART3)`.

| UART | Intel assignment | GM usage |
|---|---|---|
| UART0, UART3 | Generic | Granted by GHS to the Android guest (boottable `Guest1_Uart0` / `Guest1_Uart3`) |
| UART1 | Discrete GNSS | Repurposed by GM for the **VIP IPC** (HDLC) instead of GNSS |
| UART2 | Host OS Debug | Guest `console=ttyS2` |

Native Linux enumerated four 16550A UARTs with zero recorded TX/RX in the pass; VIP/other endpoint assignment not proven by enumeration. Physical UART tables: `hardware/teardown.md` and [ethernet_networking.md](ethernet_networking.md). VIP link details: [vip_ipc_ghs.md](vip_ipc_ghs.md).

---

## 12. I2C bus topology

AAOS guest view:

| Bus | Permissions | Owner | Use |
|---|---|---|---|
| i2c-0 | crw-rw-rw- | root | EEPROM (M24C64 at 0x50) |
| i2c-1 | crw-rw-rw- | root | ELMOS antenna controller |
| i2c-2 | crw-rw-rw- | system | General system |
| i2c-3 | crw-rw-rw- | audioserver | TDF8532 codec control |
| i2c-4 to i2c-6 | crw------- | root | Reserved |
| i2c-7 | crw-rw---- | system | Atmel maXTouch (0x4B) touchscreen |
| i2c-8 to i2c-10 | crw------- | root | Reserved |

**Additional devices:** faceplate controller at 0x12 (bus 7). Security note (i2c-0/i2c-1 world-writable): [eeprom_i2c_security.md](eeprom_i2c_security.md).

**Native Linux view (numbers differ by kernel):** eight DesignWare adapters, three i915 GMBUS adapters and an I801 SMBus; the active display controller is PCI `00:17.3`, reported as `native i2c-10` (AAOS numbers the touch bus 7). The native panel helper selects the physical controller via `/sys/bus/i2c/devices` and retains a GPIO-v2 request for line 33 of the verified 78-line `INT3452:00` bank; global GPIO467 is an older-kernel mapping, not a portable number (Probe05 showed reset GPIO467 high). Other physical slave population not determined by enumeration. Platform I2C (LPSS) is I2C0-7 per datasheet. The AAOS table above is the Android-guest numbering.

**MFi diagnostic access** is statically traced to AAOS `/dev/i2c-2`, address 0x10. The candidate native bus 5 mapping did not acknowledge a targeted register selector. See [MFi trace](../video/carplay_video_pipeline.md#mfi-authentication-i2c-path--2026-11-17).

---

## 13. Other platform I/O (datasheet-confirmed, A-series config)

- **SPI (LPSS):** 3 controllers / 7 devices (native Linux: three SPI masters, no enumerated slaves).
- **PCIe Gen2**, **eMMC** (00:1c.0), SDIO; HD Audio + I2S.
- **MIPI-DSI** display ports + **CSI D-PHY 1.1** camera inputs.
- **Security:** Boot Guard + TXE/CSE (HECI), see section 4.
- **Native GPIO/PWM:** four INT3452 banks (43/47/77/78 lines), pwmchip0; controller availability does not establish every board signal's role. Other PCI functions seen: AHCI 8086:5ae3, three communications functions 8086:5a9a/5a9c/5a9e, 8086:5aa2 unbound (not necessarily faults).
- **Native Linux hardware coverage / probe logs:** [elk_recovery.md](elk_recovery.md).

---

## 14. Thermal and power

| Item | Value |
|---|---|
| TDP | 12 W @ TjMax [Intel 336256]. History: the Y177 snapshot `thermal.tdp: 10` is superseded (corrected 2026-11-12); the same snapshot's `cpu.tdp: 12` agrees with the datasheet. |
| Cooling | passive; automotive qualified; extended temperature range |
| Y177 sample temps (runtime) | cpu 53 C, gpu 53 C, skin 25 C, battery 25 C; throttling none |
| Native Linux sample | `acpitz` and `coretemp` both 33 C at sample, ~30-31 C in stable02 with T1 counters clean; one observation, not a stress test; `rtc_cmos` present |
| Power | source vehicle 12 V direct; no battery; state always_on; automotive-grade management; suspend disabled |
| Sleep states | S0i3/S3/S5 18/16/16 mW @ 30 C (datasheet) |

---

## 15. Kernel and Android runtime configuration

(Unassigned by the plan; held here pending an owner decision, see ledger.)

| Category | Setting |
|---|---|
| Preemption | PREEMPT=y (full preemptive) |
| Timer | HZ=1000 |
| Scheduler | SCHED_TUNE + FAIR_GROUP_SCHED |
| Titan-specific | TITAN_X86_BROXTON_PROGRAM, APL_MY22_ANDROID, I2C_BUS_NUMBER_HACK |
| VirtIO | BLK / CONSOLE / PCI (GHS guest I/O) |
| DRM | I915 built-in |
| Audio | HDA_CORE=m (module) |
| Compression | LZ4 |
| Compiler | Clang 12.0.7 |

| DalvikVM parameter | Value |
|---|---|
| heapsize | 512m |
| heapgrowthlimit | 288m |
| dex2oat-threads | 2 (cores 0, 1) |
| usejit | true |
| zygote | zygote64 (64-bit only, no 32-bit) |

### Y177 snapshot bench-state and config keys (not platform facts)

Single-sample keys from the Y177 tech_specs snapshot, kept for completeness; they describe the state or configuration of the unit at sampling time, not fixed hardware properties:
- `bluetooth.active_hfp: true` - bench-state (an HFP link was active at sampling); the other sampled Bluetooth live values (rssi, ssid, paired device, MACs) are redacted/transient and not kept.
- `usb.adb_enabled: true` - bench-state/config (ADB enabled at sampling); see the USB table above.
- `thermal.extended_temp_range: true` - config flag (extended-temperature part); the datasheet range is the AEC-Q100 Tcase -40..+98 C in section 2.
- `carlink_optimization.codec_preference: OMX.Intel.hw_vd.h264` and `carlink_optimization.buffer_config: adaptive_playback_disabled` - Carlink codec **configuration choices** recorded in the snapshot, not measured platform capabilities (the component is the H.264 row in section 5). The snapshot's other `carlink_optimization` / `performance_analysis` keys are interpretive flags (e.g. `hardware_sufficient`, `cpu_adequate`) with no measurement behind them and were deliberately not carried over; `target_resolution` (2400x960 @ 60) and the 50 ms audio latency target are in sections 6 and 9.

---

## 16. Pointers (content owned elsewhere)

- Dual-processor architecture, VIP MCU, PLC timers, calibration values, IPC protocol, GHS binary / `/dev/ghs` / camera bypass: [vip_ipc_ghs.md](vip_ipc_ghs.md)
- Native 7.3.5 probe05/06 inventory, stable02 results: [elk_recovery.md](elk_recovery.md)
- System properties, hw.conf decode, vehicle ID: [vehicle_config.md](vehicle_config.md)
- Y177/Y181B build strings, fingerprints, patch levels (e.g. Y181B `W231E-Y181.3.2-SIHM22B-499.3`, security patch 2025-06-05, kernel `4.19.305-240125T145315Z-gf1edde901aa7`, bootloader 2344, SKU gv221): [firmware_versions.md](firmware_versions.md)
- SELinux / verified-boot posture (Y177 `androidboot.selinux=permissive` is the cmdline arg, not runtime; stock Y177 runs Enforcing): [security.md](security.md)
- Android services, VHAL (156 registered), car service: [vehicle_config.md](vehicle_config.md)
- Kernel 4.19 config extraction from live device and Intel/Celadon resource index: [external_references.md](external_references.md)

---

## Open conflicts

1. **GPU boost 650 vs 750 MHz.** Datasheet burst is 650 MHz (`intel_apl_external_resources.md:158`; tech_specs `gpu_burst_mhz: 650` at `gminfo3.7_tech_specs.md:39`). The Y177 snapshot `gpu.freq_boost: 750` (`gminfo3.7_tech_specs.md:49`; `hardware.md:22` "300-750 MHz range") is [UNVERIFIED]: no GPU frequency node is shell-readable (search 2026-10-10). Both kept.
2. **Visible RAM:** Y177-era `MemTotal` 5530 MiB (`hardware.md:24`, `gminfo3.7_tech_specs.md:67`) vs Y181B recovery E820 5743.55859375 MiB (`hardware.md:24`) vs native probe05 `MemTotal` 5,963,784 KiB (`hardware.md:74`). Different builds/contexts, unreconciled; grant 7830 MiB vs visible cause unresolved.
3. **CPU frequency:** 800 MHz LFM / 1.6 GHz HFM / 2.0 GHz burst (datasheet, `hardware.md:14`) vs 1881.6 MHz hypervisor-visible (`hardware.md:18`) vs native `intel_pstate` 800-2400 MHz limits (`hardware.md:74`). Not reconciled in source.
4. **I2C numbering:** AAOS touch on i2c-7 @ 0x4B (`hardware.md:29,168`) vs native "native i2c-10" display controller (`hardware.md:83`) and MFi AAOS `/dev/i2c-2` vs native bus 5 (`hardware.md:120-121`). Numbering differs by kernel; no per-bus mapping established.
5. **Camera hardware:** ACPI ADV7481A/B declarations (`hardware.md:81`) vs TI DS90UB954 deserializer on the teardown board (`hardware.md:114`). Not reconciled.
6. **Kernel version:** 4.19.305 (Y181) vs 4.19.283 (Y175) (`hardware.md:31`); `intel_apl_external_resources.md:128` filename uses 4.19.305. Different builds, listed for completeness.
7. **IPC version scheme** (HW L195/L204 "v16" vs L273 "4.1.0") belongs to [vip_ipc_ghs.md](vip_ipc_ghs.md); not stated here.
8. **Y177 vs Y181B security patch** (2025-02-05 `gminfo3.7_tech_specs.md:16` vs 2025-06-05 `:5`): different builds, retained in [firmware_versions.md](firmware_versions.md).
