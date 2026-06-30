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
| SELinux permissive (Y177) vs enforcing (Y181) | device-intel-sepolicy + aosp_diff/*/system/sepolicy |
| AVB2 verification chain | kernelflinger avb/ subtree |
| IFWI/Boot Guard structure | Intel UEFI guide #671281 + FSP ApolloLakeFspBinPkg |
| GHS guest isolation model | US patent 12,423,197 |
| Kernel 4.19 config | Pull from live device /proc/config.gz |

---

*Date: 2026-06-29*
