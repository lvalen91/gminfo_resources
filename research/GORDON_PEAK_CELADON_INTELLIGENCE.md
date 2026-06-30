# Gordon Peak MRB & Project Celadon Intelligence Report

**Research Date:** 2026-06-29
**Project:** GM Info 3.7 (gminfo37) Reverse Engineering — Y181 → Y177 Downgrade
**Platform:** Intel Atom x7-A3960 (Apollo Lake), Android 12 AAOS, GHS INTEGRITY IoT 2020.18.19, Linux 4.19.305
**Classification:** Supporting Research / Open Source Intelligence

---

## Overview

Gordon Peak MRB (Mobile Reference Board) is Intel's Apollo Lake reference design, targeting the APL-I silicon family (E3900/A3900 series). The Atom x7-A3960 present in GM's infotainment unit is the same silicon generation — making Gordon Peak the closest publicly accessible hardware analog for reverse engineering purposes.

GM's device tree was never published and is not obtainable through open channels. However, the Project Celadon branch `celadon/s/mr0/apollo` is the Gordon Peak lineage built for Android 12 (S/Snow Cone, MR0). This branch is the highest-value public artifact for understanding how Intel configured Apollo Lake for automotive-class Android workloads.

**Project Celadon** is Intel's open-source Android-on-x86 reference stack. It ships as source repositories organized under the `projectceladon` GitHub org, with build manifests pinning component SHAs. **CiV** (Celadon-in-VM) is the virtualized variant that runs the Android guest inside ACRN hypervisor — structurally analogous to the GHS INTEGRITY + Linux + AAOS guest architecture on GM's unit, though the hypervisor differs.

Key constraints for this research axis:
- No prebuilt Celadon images are publicly available. The `celadon-binary` repository returns HTTP 404 (private or removed). All usable artifacts require building from source.
- The Gordon Peak BSP (Android BSP Getting Started guide, doc #567191; ABL Configuration guide, doc #572371; FSP MR5, doc #566285) is gated behind Intel CNDA + RDC access. There is no public route.
- GM's automotive Linux 4.19 kernel tree is NDA-gated. Celadon's kernel lineage skipped from 4.9 directly to 5.15; the 4.19 branch exists only on the live device.

---

## Immediately Actionable — Clone Commands

The following commands retrieve every publicly accessible Celadon component relevant to the Apollo Lake / Android 12 intersection. Run these to build the local reference corpus.

```bash
# Android 12 + Apollo Lake intersection (matches GM info37 exactly)
git clone --depth=1 -b celadon/s/mr0/apollo https://github.com/projectceladon/kernelflinger.git
git clone --depth=1 -b celadon/s/mr0/apollo https://github.com/projectceladon/vendor-intel-utils.git
git clone --depth=1 -b celadon/p/mr0/master https://github.com/projectceladon/device-androidia.git
git clone --depth=1 https://github.com/projectceladon/device-intel-sepolicy.git
git clone --depth=1 https://github.com/projectceladon/manifest.git celadon-manifest

# Reference board and firmware
git clone --depth=1 https://github.com/slimbootloader/slimbootloader.git
# Relevant path: Platform/ApollolakeBoardPkg/Library/Stage2BoardInitLib/Stage2BoardInitLib.c
# Defines PLATFORM_ID_GPMRB, IOC IPC reset over UART, platform ID via GPIO 25/26/30

# Intel FSP Apollo Lake (sparse — binaries only)
git clone --depth=1 --filter=blob:none --sparse https://github.com/intel/FSP.git intel-FSP
cd intel-FSP && git sparse-checkout set ApolloLakeFspBinPkg

# A12 reproducible reference build
repo init -u https://github.com/projectceladon/manifest -b celadon/s/mr0/stable -m stable-build/CIV_01.22.03.32_A12.xml
repo sync -c
lunch caas-userdebug && make -j$(nproc)
```

The `CIV_01.22.03.32_A12` manifest is the best available match for the Android 12 era of GM's build. It pins all component SHAs and produces a reproducible reference image that can be diffed against GM artifacts.

---

## kernelflinger (celadon/s/mr0/apollo) — Highest-Value Asset

`kernelflinger` is Intel's EFI bootloader for Android-on-x86. The `celadon/s/mr0/apollo` branch is the direct Gordon Peak / Apollo Lake variant for Android 12. It is the single highest-value public artifact for this research because it exposes the full boot chain in source form.

### kf4abl.c — ABL Integration Layer

`kf4abl.c` implements the interface between kernelflinger and Intel's Android Bootloader (ABL). Key elements:

- **HECI/CSE messaging**: The file contains the handshake sequence between the Android boot environment and the Converged Security Engine (CSE, also known as TXE on Apollo Lake). This is the firmware-level trust anchor for the boot chain.
- **IOC_USE_SLCAN / IOC_USE_CBC flags**: These compile-time flags gate the in-vehicle IOC (I/O Controller) CAN bus integration paths. Their presence in Gordon Peak source confirms that automotive CAN integration is a first-class concern in this bootloader lineage — directly relevant to GM's use of the same silicon.
- **ELK trigger chain**: `kf4abl.c` is the direct upstream source for understanding the ELK (Enter Linux Kernel?) trigger sequence. Cross-reference with GM's `OBBPELK` symbol → `BootELKSendAblUserCommand` (address `0x0087452a`) → `ConnToOTA_BootELK` call graph recovered from gminfo37 decompilation.

### libheci — HECI Protocol Implementation

`libheci` implements the Host Embedded Controller Interface protocol for communication between the Linux guest and TXE/CSE. This protocol underpins:

- Secure boot status reporting from CSE to the Android environment
- Anti-rollback version enforcement (the mechanism that blocks Y181 → Y177 downgrade at firmware level)
- OTA authorization messaging

The `libheci` source maps directly onto GM's recovered symbol chain: `OBBPELK` → `BootELKSendAblUserCommand` (0x0087452a) → `ConnToOTA_BootELK`. Understanding the HECI message format at this layer is prerequisite to understanding what the ELK command authorizes and whether it can be replayed or spoofed.

### avb/ Subtree — Android Verified Boot

The `avb/` directory contains AVB2 (Android Verified Boot 2.0) verification logic as integrated with Intel's boot chain. This is directly comparable to GM's vbmeta chain. Specific areas:

- `avb_slot_verify.c`: slot selection and verification flow
- `avb_vbmeta_image.c`: vbmeta structure parsing — compare against GM's vbmeta partition layout
- Hash descriptor handling: identifies which partitions are verified and with what algorithm

### doc/crashmode.md — Crash ADB Mode

Documents the crash mode entry path: a deliberate or fault-triggered boot state that enables ADB access over USB before the Android userspace is running. This mode allows:

- EFI variable enumeration and dump
- Partition table inspection
- Direct partition read via `dd` equivalents in the EFI shell

This is a candidate recovery path for forensic imaging of the GM unit.

### misc/BCB Boot Flow — BCB Layout Cross-Reference

`kernelflinger.c` reads the Bootloader Control Block (BCB) at offset **0x800** within the `misc` partition. The BCB is the Android-standard mechanism for communicating boot commands (recovery, bootonce, etc.) between the OS and bootloader.

**Cross-reference against GM misc partition (vda9):**
- Magic bytes "AB0" confirmed at offset 0x800 in GM's misc layout
- CRC32 polynomial: 0xEDB88320 (standard IEEE 802.3 / zlib polynomial)
- The kernelflinger BCB implementation provides the authoritative field layout for interpreting and potentially writing GM's misc partition to trigger alternative boot paths

---

## vendor-intel-utils — SELinux + AAOS Patches

`vendor-intel-utils` on the `celadon/s/mr0/apollo` branch contains the only concrete, publicly available AAOS patch artifacts in the entire Celadon organization.

### aosp_diff/ Directory Structure

- **`aosp_diff/aaos_iasw/`**: Patches specific to the AAOS In-Vehicle Infotainment Software stack. These cover automotive-specific system services, HALs, and vehicle property bindings.
- **`aosp_diff/base_aaos/`**: Base AAOS patches applied on top of AOSP before automotive customizations. These patches bridge stock Android 12 to the AAOS profile.

Both directories represent the delta between upstream AOSP and Intel's automotive Android configuration. Diffing these against GM's extracted filesystem reveals which Intel customizations GM adopted, discarded, or overrode.

### aosp_diff/*/system/sepolicy/ — SELinux Policy Delta

The SELinux policy patches within `aosp_diff/` are critical for the Y177 → Y181 downgrade analysis:

- **Y177 is permissive** (confirmed from VIP firmware analysis): SELinux in permissive mode logs denials but does not enforce them, enabling broader system access.
- **Y181 is enforcing**: SELinux enforcement was tightened in Y181.

The `system/sepolicy` patches in the apollo branch show exactly which rules Intel added for AAOS. Diffing the Celadon SELinux baseline against the Y177 permissive policy identifies the specific rules that were added or tightened between the two GM builds. This diff is the path to understanding what new restrictions block the downgrade path and what audit log entries to expect on a Y181 → Y177 attempt.

### device-intel-sepolicy

The standalone `device-intel-sepolicy` repository is Celadon's SELinux policy baseline for Intel AAOS platforms. It predates the patches in `vendor-intel-utils` and represents the platform-level policy layer before automotive customization is applied. Use as the baseline in a three-way diff: `device-intel-sepolicy` → `aosp_diff/base_aaos/system/sepolicy` → `aosp_diff/aaos_iasw/system/sepolicy`.

---

## device-androidia — Gordon Peak Config Lineage

`device-androidia` is Celadon's primary device configuration repository. It contains the board configurations, build mixins, and hardware abstraction layer bindings for all supported Intel Android platforms.

### Gordon Peak in the caas Target

Gordon Peak hardware configuration is not a standalone build target — it is folded into the **caas** (Celadon-as-a-Service / Celadon-in-VM) target via the mixin system:

- **`caas/mixins.spec`**: References `hardware=gordon_peak` as a mixin source
- **`device-androidia-mixins/`**: Contains the hardware-specific configuration fragments for Gordon Peak, including swap configuration, thermal policy, and Bluetooth stack bindings

This architecture means that building `caas-userdebug` implicitly incorporates Gordon Peak hardware configuration. There is no separate `gordon_peak-userdebug` target in public sources.

### Board Revision Gate

A critical hardware constraint documented in the Gordon Peak MRB lineage:

- **Board revision -401 or later is required for ABL virtualization support** (ABL version 1729+)
- Earlier board revisions (e.g., J17532-400 and prior) cannot support the ACRN hypervisor / CiV configuration
- GM's A3960 unit is assumed to be a production derivative of a -401 or later board revision based on the AAOS/GHS architecture present

When referencing Intel documentation, filter for -401 board revision artifacts to ensure applicability.

---

## Slim Bootloader — GPMRB Reference

Slim Bootloader (SBL) is Intel's open-source modular firmware framework. The Apollo Lake board package contains explicit Gordon Peak MRB support and is the clearest public documentation of the GPMRB hardware initialization sequence.

### Stage2BoardInitLib.c — Key Artifacts

Path: `Platform/ApollolakeBoardPkg/Library/Stage2BoardInitLib/Stage2BoardInitLib.c`

- **`PLATFORM_ID_GPMRB`**: Defined explicitly. This constant is the platform identifier that gates Gordon Peak-specific initialization paths throughout Stage 2 firmware.
- **IOC IPC reset over UART**: The IOC (I/O Controller) is reset via IPC messages over a UART channel during Stage 2 initialization. This is the same IOC that the `IOC_USE_SLCAN`/`IOC_USE_CBC` flags in kernelflinger reference — confirming the hardware path from firmware through bootloader to Android.
- **Platform ID detection via GPIO 25/26/30**: Board variant identification is performed by reading the state of GPIOs 25, 26, and 30 during early boot. Understanding this detection sequence explains how the firmware selects Gordon Peak configuration versus other Apollo Lake board variants.

### Building SBL for Reference

```bash
python BuildLoader.py build apl
```

This produces an Apollo Lake SBL image that can be inspected with standard binary tools. The resulting IFWI structure is the closest public reference to GM's IFWI layout.

---

## Gordon Peak MRB — What Was Found vs NDA-Gated

### Found — Publicly Available

| Artifact | Location / Notes |
|---|---|
| Hardware identity | APL-I, E3900/A3900 family. Product codes: GPMRBDEVKITPD, MM# 952380 |
| Board revision gate | -401 or later required for ABL virtualization (ABL 1729+); e.g., J17532-401 |
| Celadon build config | `device-androidia/caas/mixins.spec`, `hardware=gordon_peak` mixin |
| Boot/firmware stack | Slim Bootloader + Leaf Hill IFWI; Intel Platform Flash Tool (PFT) for flashing |
| ABL + kernelflinger source | Full source on `celadon/s/mr0/apollo` branch |
| SELinux policy | `device-intel-sepolicy` + `vendor-intel-utils` aosp_diff patches |
| FSP binaries | `intel/FSP` → `ApolloLakeFspBinPkg` (binaries, no source) |

### NDA-Gated — Not Obtainable Without Intel CNDA

| Artifact | Gating Mechanism |
|---|---|
| Android BSP Getting Started guide (doc #567191) | Intel CNDA + RDC access required |
| ABL Configuration Guide (doc #572371) | Intel CNDA + RDC access required |
| FSP MR5 source (doc #566285) | Intel CNDA + RDC access required |
| ACRN flashfile | `mcg-depot.intel.com` — internal Intel host, no external DNS resolution |
| `android.googlesource.com/device/intel/gordon_peak` | HTTP 404 — never published publicly |
| E3900 binary objects R71 | HTTP 403 — access restricted |
| GM automotive Linux 4.19 kernel tree | GM NDA / not derived from public Celadon sources |

---

## Celadon CiV/AAOS — Source Available, No Prebuilts

### What Is Available

- **All manifest XMLs**: The `celadon-manifest` repository contains all historical manifest files, including the pinned SHA manifests for stable builds. Every component version is recoverable via `repo sync`.
- **AAOS patches**: `vendor-intel-utils` `aosp_diff/` directories on the `apollo` branch are the primary AAOS artifact set.
- **A12 stable manifest**: `CIV_01.22.03.32_A12.xml` is the best available match for the Android 12 era of GM's infotainment build. Use this manifest for reproducible reference builds.
- **Full source repos**: kernelflinger, device-androidia, device-intel-sepolicy, and all supporting repos are publicly cloneable with the commands in the Clone Commands section.

### What Is Not Available

- **Prebuilt images**: The `celadon-binary` repository returns HTTP 404. These were either never public or were removed. All usable images must be built from source via the manifest + `repo sync` workflow.
- **Linux 4.19 kernel**: Celadon's kernel lineage progressed from 4.9 to 5.15, skipping 4.19 entirely. GM's automotive Linux 4.19.305 kernel does not correspond to any public Celadon kernel branch. It is sourced from GM's internal automotive BSP.
- **Dedicated AAOS lunch target**: There is no `gordon_peak_aaos-userdebug` or equivalent standalone AAOS target. AAOS support is implemented as patch overlays applied to the caas base target, not as a separate branch or product definition.

### Kernel 4.19 Workaround — Pull from Live Device

The GM unit's running kernel has `CONFIG_IKCONFIG_PROC=y` enabled (confirmed). This allows extraction of the complete kernel configuration directly from the running system:

```bash
adb shell "gzip -dc /proc/config.gz" > gm_kernel_4.19.305.config
```

This extracted config is the authoritative kernel configuration for GM's 4.19.305 build. No public source can substitute for it. Use it to:
- Identify enabled kernel modules relevant to the boot chain
- Confirm security configuration (LSM stack order, SELinux enforcement mode at kernel level)
- Identify enabled debug/trace facilities that may be exploitable during downgrade

---

## Intel APL Supporting Materials

### Official Intel Documentation

- **UEFI Firmware Enabling Guide for Intel Atom Processor E3900 Series**
  URL: `https://cdrdv2-public.intel.com/671281/uefi-firmware-enabling-guide-for-the-intel-atom-processor-e3900-series.pdf`
  Document #671281. Covers UEFI firmware architecture, IFWI structure, and platform initialization for E3900/A3900. Downloaded to `~/Downloads`.

- **E3900 / A3960 Datasheet Addendum**
  URL: `https://cdrdv2-public.intel.com/336256/`
  Document #336256. Contains silicon-level specifics for the A3960 variant including GPIO multiplexing, UART configuration, and power management states relevant to IOC integration.

### Third-Party / Community Documentation

- **TXE/IFWI Bring-Up Guide** (third-party, v1.1):
  `https://usermanual.wiki/Document/APLIntelRTXEFWBringupGuideV11.128793216/html`
  Covers TXE firmware bring-up procedures for Apollo Lake. Useful for understanding the TXE/CSE side of the HECI handshake documented in kernelflinger libheci.

### Open Source Firmware References

- **EDK2 APL Platform**:
  `https://github.com/tianocore/edk2-platforms/tree/devel-IntelAtomProcessorE3900`
  UEFI firmware implementation for E3900. Provides ACPI table definitions, PEI/DXE module structure, and platform initialization sequence in source form.

- **coreboot Apollo Lake SoC**:
  `https://github.com/coreboot/coreboot/tree/master/src/soc/intel/apollolake`
  Alternative open firmware implementation for APL. Useful for cross-referencing hardware initialization sequences, particularly GPIO pad configuration and PCH register layouts.

### Patent — GHS INTEGRITY Guest Isolation Model

- **US Patent 12,423,197** — GHS INTEGRITY SMMU / GVM guest isolation model
  `https://patents.google.com/patent/US12423197`
  Describes the SMMU-based memory isolation mechanism used in GHS INTEGRITY's guest VM architecture. This is the theoretical foundation for understanding how the GHS hypervisor on GM's unit isolates the Linux guest from the INTEGRITY RTOS. Relevant to: determining whether memory regions accessible from the Linux guest can be used to influence the hypervisor's boot authorization decisions.

---

## Research Axis Mapping

| Research Vector | Best Available Source |
|---|---|
| misc partition / BCB layout | `kernelflinger.c` + `hardware-intel-bootctrl` HAL + offset 0x800; GM misc (vda9) magic "AB0" at 0x800, CRC32 poly 0xEDB88320 |
| HECI/ABL/ELK trigger chain | `kf4abl.c` + `libheci` (celadon/s/mr0/apollo) + Slim Bootloader `Stage2BoardInitLib.c` |
| SELinux baseline vs Y177 permissive | `device-intel-sepolicy` + `aosp_diff/*/system/sepolicy` on apollo branch; three-way diff against extracted Y177 policy |
| AVB implementation | `kernelflinger` `libkernelflinger/` + `avb/` subtree on celadon/s/mr0/apollo |
| Kernel 4.19 config | Pull from live device: `adb shell "gzip -dc /proc/config.gz"` — not obtainable from any public source |
| VT-x guest isolation model | US Patent 12,423,197 (GHS INTEGRITY SMMU/GVM) |
| IFWI structure | Intel UEFI guide #671281 + `intel/FSP` → `ApolloLakeFspBinPkg` binaries |
| IOC/CAN integration | `kf4abl.c` IOC_USE_SLCAN/IOC_USE_CBC flags + `Stage2BoardInitLib.c` IOC IPC reset over UART |
| Board variant identification | GPIO 25/26/30 detection in `Stage2BoardInitLib.c` |
| Thermal / swap / BT config | `device-androidia-mixins` gordon_peak hardware mixin fragments |

---

## Dead Ends

The following research directions were pursued and confirmed non-viable. Do not re-investigate without new information.

| Dead End | Status | Notes |
|---|---|---|
| `celadon-binary` prebuilts | HTTP 404 / private | Repository removed or access-restricted. Must build from source. |
| Gordon Peak Android BSP | CNDA-gated | Docs #567191, #572371, #566285 require Intel NDA. No public route exists. |
| `mcg-depot.intel.com` ACRN flashfile | Internal host only | No external DNS. Intel employee intranet only. |
| `android.googlesource.com/device/intel/gordon_peak` | HTTP 404 | Never published publicly. Path exists in some manifest references but returns 404. |
| `firmware.intel.com` / `01.org` | Both decommissioned | All Intel open-source firmware hosting has migrated; old URLs return 404. Use GitHub (`intel/` org) and `cdrdv2-public.intel.com` instead. |
| E3900 binary objects R71 | HTTP 403 | Access restricted. Not obtainable without authenticated Intel developer account. |
| Linux 4.19 public kernel | Does not exist in Celadon | Celadon lineage: 4.9 → 5.15. The 4.19 branch is exclusive to GM's automotive BSP. Extract from live device via `/proc/config.gz`. |
| GHS CVEs (github.com/AlixAbbasi/GHS-Bugs) | Not applicable | All documented vulnerabilities target GHS INTEGRITY RTOS shell on version 5.0.4. None are hypervisor-level or applicable to INTEGRITY IoT 2020.18.19. |
| Dedicated AAOS Celadon lunch target | Does not exist | AAOS is implemented as patch overlays on caas target. No standalone AAOS product definition is published. |

---

## Notes on Build Environment

When building the A12 reference from `CIV_01.22.03.32_A12.xml`:

- Requires AOSP build environment: Ubuntu 20.04 LTS recommended, 16+ GB RAM, 300+ GB disk
- `lunch caas-userdebug` is the correct target — this implicitly pulls gordon_peak mixins
- The resulting `kernelflinger.efi` from this build is the reference artifact for comparing EFI binary structure against any kernelflinger variant recovered from the GM unit
- Build artifacts of interest: `kernelflinger.efi`, `vbmeta.img`, `boot.img`, `super.img` partition layout, `tos.img` (Trusty OS, if present)
- SELinux policy output: `out/target/product/caas/root/file_contexts`, `out/target/product/caas/vendor/etc/selinux/`

---

*Document generated: 2026-06-29. Research conducted as open source intelligence (OSINT) using publicly available repositories, documentation, and patent filings. No NDA-gated materials were accessed or reproduced.*
