# Intel APL External Resources Reference

## Overview

Index of publicly available Intel Apollo Lake (APL) platform resources applicable to GM Info 3.7 reverse engineering. All clones placed in ~/Downloads/github/ unless noted.

Target platform: Intel Atom x7-A3960 (Apollo Lake / Goldmont microarchitecture), running Android 12 AAOS under GHS INTEGRITY IoT hypervisor.

---

## Project Celadon (Intel's Android-on-x86 Reference)

Closest public equivalent to the GM Info 3.7 software stack. No dedicated AAOS branch; AAOS support delivered as patches.

### Cloned Repositories

| Repo | Branch | Path | Value |
|---|---|---|---|
| kernelflinger | celadon/s/mr0/apollo | ~/Downloads/github/kernelflinger | ABL integration, HECI/CSE, AVB, ELK trigger code |
| vendor-intel-utils | celadon/s/mr0/apollo | ~/Downloads/github/vendor-intel-utils | SELinux baseline, AAOS patches (aosp_diff/aaos_iasw) |
| device-androidia | celadon/p/mr0/master | ~/Downloads/github/device-androidia | Gordon Peak config lineage (caas/mixins.spec) |
| device-intel-sepolicy | master | ~/Downloads/github/device-intel-sepolicy | SELinux policy baseline for Intel AAOS |
| celadon-manifest | master | ~/Downloads/github/celadon-manifest | All build manifests (A10–A15) |

### Key Files Within kernelflinger (celadon/s/mr0/apollo)

- `kf4abl.c` — ABL boot integration, HECI messaging, IOC/CAN flags (`IOC_USE_SLCAN`, `IOC_USE_CBC`)
- `libheci/` — HECI protocol: Host Embedded Controller Interface between Linux guest and Intel TXE/CSE
- `avb/` — AVB2 verification implementation (compare against GM vbmeta chain)
- `libqltipc/` — Trusty TEE IPC
- `doc/crashmode.md` — Crash mode ADB, EFI variable dump
- `kernelflinger.c` — Boot flow; BCB read at offset 0x800 (matches GM misc/vda9 layout)

### AAOS Content in vendor-intel-utils

Path: `aosp_diff/aaos_iasw/` and `aosp_diff/base_aaos/`

- Base AAOS AOSP patch overlay for Intel x86 platforms
- Per-release SELinux patches under `aosp_diff/*/system/sepolicy/`
- NOTE: No dedicated AAOS lunch target; AAOS is patches on top of standard Celadon

### Reference Build (A12, matches GM info37 era)

Manifest: `CIV_01.22.03.32_A12.xml` (AOSP android-12.0.0_r28 base)

Build command:

```bash
repo init -u https://github.com/projectceladon/manifest -b celadon/s/mr0/stable \
  -m stable-build/CIV_01.22.03.32_A12.xml
repo sync -c -j8
lunch caas-userdebug && make -j$(nproc)
```

Note: celadon-binary repo (prebuilts) returns HTTP 404 — must build from source.

---

## Slim Bootloader (Gordon Peak MRB Reference)

**Local:** ~/Downloads/slimbootloader (sparse: `Platform/ApollolakeBoardPkg` + `Silicon/ApollolakePkg`)
**Source:** https://github.com/slimbootloader/slimbootloader

Key file: `Platform/ApollolakeBoardPkg/Library/Stage2BoardInitLib/Stage2BoardInitLib.c`

- Defines `PLATFORM_ID_GPMRB` (Gordon Peak MRB explicit reference)
- IOC IPC reset over UART
- Platform ID detection via GPIO 25/26/30
- Reference for HECI/ABL/IOC integration on this exact board family

Build: `python BuildLoader.py build apl`

---

## Intel FSP Apollo Lake

**Local:** ~/Downloads/intel-FSP/ApolloLakeFspBinPkg (sparse clone)
**Source:** https://github.com/intel/FSP/tree/master/ApolloLakeFspBinPkg

Contains: `Fsp.fd`, `Fsp.bsf`, VBT (Video BIOS Table)

Value: Reference FSP for boot chain / IFWI structure understanding.

---

## Intel Official Documentation (PDFs)

| Document | Local Path | Value |
|---|---|---|
| UEFI Firmware Enabling Guide (E3900/A3960) | ~/Downloads/intel_apl_uefi_enabling_guide_671281.pdf | IFWI structure, HECI, TXE, Boot Guard config |
| TXE/IFWI Bring-Up Guide v1.1 | (3rd-party mirror) | PMC FW, FIT, MEU, HECI context |
| E3900/A3960 Datasheet Addendum | https://cdrdv2-public.intel.com/336256/ | SoC pinout, peripheral map |

---

## EDK2 and coreboot (Boot Chain References)

- **EDK2 APL:** https://github.com/tianocore/edk2-platforms/tree/devel-IntelAtomProcessorE3900
- **coreboot APL SoC:** https://github.com/coreboot/coreboot/tree/master/src/soc/intel/apollolake

---

## Patents

- **US 12,423,197** — GVM SMMU fault protection in automotive hosted hypervisor (GHS guest-VM safety model, most technical public GHS architectural description)
  URL: https://patents.google.com/patent/US12423197

---

## NDA-Gated (Not Obtainable Without Intel NDA)

- Gordon Peak Android BSP: docs #567191, #572371, #566285 — CNDA + RDC-gated
- E3900 binary objects R71: HTTP 403
- ACRN flashfile (mcg-depot.intel.com): internal host only
- Gordon Peak AOSP device tree (android.googlesource.com/device/intel/gordon_peak): 404, never public
- APL automotive Linux 4.19 kernel tree: NDA (Celadon has 5.15+; GM's 4.19 is not public)

---

## Kernel 4.19 Config (Live Device)

Not available from any public source. Extract from connected device:

```bash
adb shell "gzip -dc /proc/config.gz" > gm_kernel_4.19.305.config
```

`CONFIG_IKCONFIG_PROC=y` confirmed in Jun 2026 enumeration — the config IS accessible.

---

## Research Axis Mapping

| Research vector | Best external source |
|---|---|
| misc/BCB A/B layout | kernelflinger.c boot flow (celadon/s/mr0/apollo) |
| HECI/ABL/ELK trigger | kf4abl.c + libheci + Slim Bootloader Stage2BoardInitLib.c |
| ~~SELinux permissive (Y177) vs enforcing (Y181)~~ CORRECTED: both enforce (no stock permissive) | device-intel-sepolicy + aosp_diff/*/system/sepolicy |
| AVB2 verification chain | kernelflinger avb/ subtree |
| IFWI/Boot Guard structure | Intel UEFI guide #671281 + FSP ApolloLakeFspBinPkg |
| GHS guest isolation model | US patent 12,423,197 |
| Kernel 4.19 config | Pull from live device /proc/config.gz |

---

## A3960 Datasheet-Confirmed Specifications (2026-10-10)

Source: **Intel Atom Processor E3900 and A3900 Series Datasheet Addendum**, Doc `336256-004US`
(local copy: [`../hardware/datasheets/Intel_336256_Atom_E3900_A3900_datasheet_addendum_rev004.pdf`](../hardware/datasheets/Intel_336256_Atom_E3900_A3900_datasheet_addendum_rev004.pdf)); full
platform register map in the main E3900 datasheet `334819`. A3900 = the **automotive**, AEC-Q100
Apollo Lake-I line (customer = automotive only). The gminfo37 SoC is the top SKU **A3960**.

### SoC (A3960 column, datasheet-confirmed)
| Spec | A3960 | note |
|---|---|---|
| Cores (Goldmont) | **4** | no HT; 2 MB L2 shared |
| CPU freq LFM/HFM/**Burst** | 800 MHz / 1.6 GHz / **2.0 GHz** | **corrects the common "2.4 GHz" figure — datasheet burst is 2.0 GHz** |
| GPU | **HD Graphics 505** (Gen9 LP), **18 EU** | freq LFM/HFM/Burst 100/500/650 MHz; industrial-reliability 400 MHz |
| ISP (IPU) freq | 200/550/700 MHz | CSI D-PHY 1.1 imaging |
| TDP @ TjMax | **12 W** | S0i3/S3/S5 18/16/16 mW @30 °C |
| Memory | **LPDDR4 ≤2400 MT/s**, non-ECC; DDR3L-ECC option | max 8 GB, 4 channels (physical RAM here = 8 GB — see RAM reconciliation below) |
| Temp | **Tcase −40…+98 °C, Tj −40…+110 °C** | AEC-Q100 |
| Process | 14 nm | Apollo Lake-I |

### Platform I/O feature counts (A-series config, datasheet-confirmed)
- **HSUART (LPSS): 4 controllers**, automotive assignment = **`1× Discrete GNSS (UART1)`, `1× Host OS
  Debug (UART2)`, `2× Generic (UART0 and UART3)`**. ← This is the datasheet ground truth behind the
  live UART map: **UART2 = "Host OS Debug"** is exactly where the guest `console=ttyS2` lands, and GHS
  grants the two **Generic** UARTs (UART0+UART3 = boottable `Guest1_Uart0`/`Guest1_Uart3`) to the
  Android guest. GM repurposes Intel's GNSS UART1 for the **VIP IPC** (HDLC) instead of GNSS. See
  `hardware/teardown.md`/`platform/networking.md` UART tables.
- **SPI (LPSS): 3 controllers / 7 devices.** I2C (LPSS): multiple ports (I2C0–7). HD Audio + I2S.
- **PCIe Gen2**, **eMMC** (boot device lives at PCI `00:1c.0` per guest cmdline), SDIO.
- **MIPI-DSI** display ports + **CSI D-PHY 1.1** camera inputs; the IPU drives the RVC path.
- **Security:** Boot Guard + TXE/CSE (HECI) on the Intel CM side — the pre-GHS trust stage, stored in
  the module's ISSI SPI-NOR IFWI (separate from the carrier eMMC that holds GHS+Android).

### How this supplements existing findings
- **CPU/platform:** corrects the common "x7-A3960 ~2.4 GHz" figure — confirmed **4-core Goldmont,
  2.0 GHz burst** (HFM 1.6 GHz), HD 505 / 18 EU. (`platform/gminfo3.7_tech_specs.md` already carries
  the correct `A3960` model string; an earlier note here claiming it was "garbled" was a terminal
  display artifact, not the file content.) For gm_emu, this pins the QEMU `-cpu` family/model and
  `tsc-frequency`.
- **Memory:** SoC max is 8 GB LPDDR4-2400 / 4 ch — consistent with the fitted 8 GB. Verified split
  [FW 85098662; 3-Opus 2026-10-10]: GHS **grants the guest 7830 MiB** DRAM (byte-confirmed from the
  boottable, not an over-count) + 34 MiB RO IPU window; GHS reserves **~362 MiB** below 4 GiB; the
  guest kernel `MemTotal` is **5530 MiB (5.40 GiB)**. The 7830→5530 gap is a VMM-configured guest
  **E820 limit** whose exact cause is **[UNVERIFIED]** (needs a root `/proc/iomem`/dmesg). The old
  "604 MB reserved" / "6 GB to guest" figures are unsourced; "5.66 GB" is a unit slip.
- **UART/console:** the Host-OS-Debug(UART2) / Generic(UART0,3) / GNSS(UART1) assignment is the
  datasheet basis for the `ttyS2` console + the two guest UART grants.
- **Graphics (GVT-g):** HD 505 Gen9 is the GVT-g-capable IGD GHS mediates — the datasheet does not
  itself document GVT-g (an Intel software feature); [UNVERIFIED from the datasheet, confirmed in the
  GHS blob `.gvtg_server`/`gen9_passthru`].

### Sources
- Intel Doc 336256-004US (E3900/A3900 Datasheet Addendum) — local PDF above.
- Intel ARK Atom x7-E3950 (industrial twin, same silicon): HD 505, 18 EU, 2 MB L2, LPDDR4-2400, 8 GB.

---

*Date: 2026-06-29 (A3960 datasheet section added 2026-10-10)*
