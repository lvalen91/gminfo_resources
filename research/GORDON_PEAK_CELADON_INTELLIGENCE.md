# Gordon Peak MRB & Project Celadon Intelligence Report

**Research Date:** 2026-06-29 (amended 2026-08-25, 2026-09-10, 2026-11-17)
**Project:** GM Info 3.7 (gminfo37) Reverse Engineering — Y181 → Y177 Downgrade
**Platform:** Intel Atom x7-A3960 (Apollo Lake), Android 12 AAOS, GHS INTEGRITY IoT 2020.18.19, Linux 4.19 (bench-observed 4.19.283, see History)
**Classification:** Supporting Research / Open Source Intelligence

**Scope:** Celadon/Gordon-Peak OSINT only — the public Apollo-Lake analog of this platform (clone/build commands, kernelflinger/libheci/avb/crashmode/BCB source findings, CNDA-gated-vs-found source tables, dead ends). Does **not** own: the ELK identity/trigger payload (→ [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md), canonical, live-tested on the GM unit; catalog entry also at [HARDWARE_HYPERVISOR_ATTACK_VECTORS.md](HARDWARE_HYPERVISOR_ATTACK_VECTORS.md)); the SELinux-enforcing finding (→ `../platform/security.md`); GM-side boot-chain architecture (→ [GM_INFO37_BOOT_CHAIN_ANALYSIS.md](GM_INFO37_BOOT_CHAIN_ANALYSIS.md), [BOOT_CHAIN_ANALYSIS.txt](BOOT_CHAIN_ANALYSIS.txt)). No NDA-gated materials were accessed or reproduced for this doc.

**Related:** GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md, HARDWARE_HYPERVISOR_ATTACK_VECTORS.md, `../platform/security.md`, GM_INFO37_BOOT_CHAIN_ANALYSIS.md.

---

## Overview

Gordon Peak MRB (Mobile Reference Board) is Intel's Apollo Lake reference design, targeting the APL-I silicon family (E3900/A3900 series). The Atom x7-A3960 present in GM's infotainment unit is the same silicon generation — making Gordon Peak the closest publicly accessible hardware analog for reverse engineering purposes.

GM's device tree was never published and is not obtainable through open channels. However, the Project Celadon branch `celadon/s/mr0/apollo` is the Gordon Peak lineage built for Android 12 (S/Snow Cone, MR0). This branch is the highest-value public artifact for understanding how Intel configured Apollo Lake for automotive-class Android workloads.

**Project Celadon** is Intel's open-source Android-on-x86 reference stack. It ships as source repositories organized under the `projectceladon` GitHub org, with build manifests pinning component SHAs. **CiV** (Celadon-in-VM) is the virtualized variant that runs the Android guest inside ACRN hypervisor — structurally analogous to the GHS INTEGRITY + Linux + AAOS guest architecture on GM's unit, though the hypervisor differs.

Key constraints for this research axis:
- **Prebuilt images:** the `celadon-binary` repository and its releases API return HTTP 404 (reconfirmed 2026-11-17). No downloadable image validated for this GM board was found; current upstream instructions target newer NUC systems, not Gordon Peak. All usable artifacts require building from source. *History: the 2026-06-29 draft stated flatly "no prebuilt Celadon images are publicly available," reading the 404 as proof of non-existence; the 2026-11-17 pass corrected this — a 404 does not establish that Intel never released images, only that none is currently reachable.*
- The Gordon Peak BSP (Android BSP Getting Started guide, doc #567191; ABL Configuration guide, doc #572371; FSP MR5, doc #566285) is gated behind Intel CNDA + RDC access. There is no public route.
- **GM's 4.19 kernel tree:** an Intel-derived 4.19.283 reference tree (upstream: [intel/linux-intel-lts](https://github.com/intel/linux-intel-lts)) exists locally and is a legitimate platform-enablement reference; it contains prior emulator patches and is **not** the exact GM BSP — the GM TI949 serializer module and GHS integration remain distinct vendor dependencies not covered by it. *History: the 2026-06-29 draft stated "GM's automotive Linux 4.19 kernel tree is NDA-gated... the 4.19 branch exists only on the live device," framing the public-source question as closed; the 2026-11-17 pass corrected this as too broad — Celadon's own lineage still skips 4.9→5.15 with no 4.19 branch, but a public Intel 4.19 reference tree exists outside Celadon proper.*

---

## Immediately Actionable — Clone Commands

The following commands retrieve every publicly accessible Celadon component relevant to the Apollo Lake / Android 12 intersection. Run these to build the local reference corpus.

```bash
# Android 12 + Apollo Lake reference (not an exact GM BSP match)
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

The `CIV_01.22.03.32_A12` manifest is an Android 12-era reference candidate. Its platform/version overlap does not establish compatibility with the GM radio or equivalence to its vendor BSP (qualification added 2026-11-17).

---

## kernelflinger (celadon/s/mr0/apollo) — Highest-Value Asset

`kernelflinger` is Intel's EFI bootloader for Android-on-x86. The `celadon/s/mr0/apollo` branch is the direct Gordon Peak / Apollo Lake variant for Android 12. It is the single highest-value public artifact for this research because it exposes the full boot chain in source form.

### kf4abl.c — ABL Integration Layer

`kf4abl.c` implements the interface between kernelflinger and Intel's Android Bootloader (ABL). Key elements:

- **HECI/CSE messaging**: the handshake sequence between the Android boot environment and the Converged Security Engine (CSE, also known as TXE on Apollo Lake) — the firmware-level trust anchor for the boot chain.
- **IOC_USE_SLCAN / IOC_USE_CBC flags**: compile-time flags gating the in-vehicle IOC (I/O Controller) CAN bus integration paths. Their presence in Gordon Peak source confirms that automotive CAN integration is a first-class concern in this bootloader lineage — directly relevant to GM's use of the same silicon.
- **ELK identity and trigger**: `kf4abl.c` is the public-source upstream for GM's recovered symbol chain `OBBPELK` → `BootELKSendAblUserCommand` (`0x0087452a`) → `ConnToOTA_BootELK`. The identity of ELK (it is Intel Kernelflinger itself, a fastboot-class bootloader, not a Linux shell) and the live-tested VIP-side trigger (`SERIAL_IPC_CONTROL_CHANNEL`/"Channel-7", `RID=0xFF01`, `FUN_000641c2`@0x64208) are owned by [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) (canonical) with a catalog entry at [HARDWARE_HYPERVISOR_ATTACK_VECTORS.md](HARDWARE_HYPERVISOR_ATTACK_VECTORS.md) — see those docs, not restated here.

### libheci — HECI Protocol Implementation

`libheci` implements the Host Embedded Controller Interface protocol for communication between the Linux guest and TXE/CSE. This protocol underpins:

- Secure boot status reporting from CSE to the Android environment
- Anti-rollback version enforcement (the mechanism that blocks Y181 → Y177 downgrade at firmware level)
- OTA authorization messaging

The `libheci` source maps directly onto GM's recovered symbol chain above. Understanding the HECI message format at this layer is prerequisite to understanding what the ELK command authorizes and whether it can be replayed or spoofed (see GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md for the live-tested answer).

### avb/ Subtree — Android Verified Boot

The `avb/` directory contains AVB2 (Android Verified Boot 2.0) verification logic as integrated with Intel's boot chain. This is directly comparable to GM's vbmeta chain. Specific areas:

- `avb_slot_verify.c`: slot selection and verification flow
- `avb_vbmeta_image.c`: vbmeta structure parsing — compare against GM's vbmeta partition layout
- Hash descriptor handling: identifies which partitions are verified and with what algorithm

### doc/crashmode.md — Crash ADB Mode

Documents the crash mode entry path: a deliberate or fault-triggered boot state that enables ADB access over USB before the Android userspace is running. This mode allows:

- EFI-variable retrieval and partition-table inspection
- Bounded partition retrieval through `adb pull part:PART_NAME[:START[:LENGTH]]`
- ACPI and RAM retrieval through the bootloader's limited ADB implementation

This is a candidate recovery path for forensic imaging of the GM unit, not a confirmed GM capability. The documented interface is bootloader ADB, not an EFI shell — Intel documents it for userdebug/eng crashmode, separate from normal Fastboot. See [upstream crashmode documentation](https://github.com/projectceladon/kernelflinger/blob/celadon/s/mr0/apollo/doc/crashmode.md). *History: corrected 2026-11-17 to make the bootloader-ADB-vs-EFI-shell distinction explicit.*

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

- **`aosp_diff/aaos_iasw/`**: patches specific to the AAOS In-Vehicle Infotainment Software stack — automotive-specific system services, HALs, and vehicle property bindings.
- **`aosp_diff/base_aaos/`**: base AAOS patches applied on top of AOSP before automotive customizations — bridges stock Android 12 to the AAOS profile.

Both directories represent the delta between upstream AOSP and Intel's automotive Android configuration. Diffing these against GM's extracted filesystem reveals which Intel customizations GM adopted, discarded, or overrode.

### aosp_diff/*/system/sepolicy/ — SELinux Policy Delta

The SELinux policy patches within `aosp_diff/` were examined for the Y177 → Y181 downgrade analysis. The Y177-permissive-vs-enforcing finding and its correction are owned by `../platform/security.md` — not restated here. The surviving, undisputed content of this section is the **diff method**: Intel's `system/sepolicy` patches on the apollo branch show which rules Intel added for AAOS, and diffing the Celadon SELinux baseline against the Y177 policy identifies which rules were added or tightened between the two GM builds. That diff recipe remains useful for rule-delta analysis regardless of the enforcing/permissive question.

### device-intel-sepolicy

The standalone `device-intel-sepolicy` repository is Celadon's SELinux policy baseline for Intel AAOS platforms. It predates the patches in `vendor-intel-utils` and represents the platform-level policy layer before automotive customization is applied. Use as the baseline in a three-way diff: `device-intel-sepolicy` → `aosp_diff/base_aaos/system/sepolicy` → `aosp_diff/aaos_iasw/system/sepolicy`.

---

## device-androidia — Gordon Peak Config Lineage

`device-androidia` is Celadon's primary device configuration repository. It contains the board configurations, build mixins, and hardware abstraction layer bindings for all supported Intel Android platforms.

### Gordon Peak in the caas Target

Gordon Peak hardware configuration is not a standalone build target — it is folded into the **caas** (Celadon-as-a-Service / Celadon-in-VM) target via the mixin system:

- **`caas/mixins.spec`**: references `hardware=gordon_peak` as a mixin source
- **`device-androidia-mixins/`**: contains the hardware-specific configuration fragments for Gordon Peak, including swap configuration, thermal policy, and Bluetooth stack bindings

This architecture means that building `caas-userdebug` implicitly incorporates Gordon Peak hardware configuration. There is no separate `gordon_peak-userdebug` target in public sources.

### Board Revision Gate

A critical hardware constraint documented in the Gordon Peak MRB lineage:

- **Board revision -401 or later is required for ABL virtualization support** (ABL version 1729+)
- Earlier board revisions (e.g., J17532-400 and prior) cannot support the ACRN hypervisor / CiV configuration
- GM's A3960 unit is assumed (unverified) to be a production derivative of a -401 or later board revision, based on the AAOS/GHS architecture present

When referencing Intel documentation, filter for -401 board revision artifacts to ensure applicability.

---

## Slim Bootloader — GPMRB Reference

Slim Bootloader (SBL) is Intel's open-source modular firmware framework. The Apollo Lake board package contains explicit Gordon Peak MRB support and is the clearest public documentation of the GPMRB hardware initialization sequence.

### Stage2BoardInitLib.c — Key Artifacts

Path: `Platform/ApollolakeBoardPkg/Library/Stage2BoardInitLib/Stage2BoardInitLib.c`

- **`PLATFORM_ID_GPMRB`**: defined explicitly — the platform identifier that gates Gordon Peak-specific initialization paths throughout Stage 2 firmware.
- **IOC IPC reset over UART**: the IOC (I/O Controller) is reset via IPC messages over a UART channel during Stage 2 initialization — the same IOC that the `IOC_USE_SLCAN`/`IOC_USE_CBC` flags in kernelflinger reference, confirming the hardware path from firmware through bootloader to Android.
- **Platform ID detection via GPIO 25/26/30**: board variant identification is performed by reading the state of GPIOs 25, 26, and 30 during early boot.

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
| Exact GM automotive Linux 4.19 kernel tree | Exact vendor source not established. A public Intel Linux LTS 4.19 reference tree exists (see Overview); GM-specific drivers (TI949 serializer, GHS integration) must be distinguished from absence of *any* public 4.19 source — these are not the same claim. *History: this row read "NDA-gated" as fact until the 2026-11-17 correction (see Overview).* |

---

## Celadon CiV/AAOS — Source References and Prebuilt Availability

### What Is Available

- **All manifest XMLs**: the `celadon-manifest` repository contains all historical manifest files, including pinned-SHA manifests for stable builds. Every component version is recoverable via `repo sync`.
- **AAOS patches**: `vendor-intel-utils` `aosp_diff/` directories on the `apollo` branch are the primary AAOS artifact set.
- **A12 stable manifest**: `CIV_01.22.03.32_A12.xml` is an Android 12-era reference candidate, not a validated GM-compatible image.
- **Full source repos**: kernelflinger, device-androidia, device-intel-sepolicy, and all supporting repos are publicly cloneable with the commands above.

### What Is Not Available

- **Prebuilt images**: the official [CiV instructions](https://projectceladon.github.io/celadon-documentation/getting-started/on-vm.html) link `projectceladon/celadon-binary`, but that link and its releases API returned HTTP 404 on 2026-11-17. This does not establish that Intel never released images — see the Overview History note. Current instructions target newer NUC systems.
- **Linux 4.19 kernel as an exact match**: see Overview — a public Intel-derived 4.19.283 reference tree exists and is useful, but is not the exact GM BSP; the GM TI949 serializer module and GHS integration remain distinct vendor dependencies.
- **Dedicated AAOS lunch target**: there is no `gordon_peak_aaos-userdebug` or equivalent standalone AAOS target. AAOS support is implemented as patch overlays applied to the caas base target, not as a separate branch or product definition.

### Kernel 4.19 Workaround — Pull from Live Device

The GM unit's running kernel has `CONFIG_IKCONFIG_PROC=y` enabled (confirmed). This allows extraction of the complete kernel configuration directly from the running system:

```bash
adb shell "gzip -dc /proc/config.gz" > gm_kernel_config
```

This extracted config is authoritative only for the specific running kernel pulled, not every GM release — the Y175 bench returned version 4.19.283 on 2026-11-17 (header platform line above updated accordingly; an earlier draft of this doc cited 4.19.305 for the same filename convention). Use the matching config to:
- Identify enabled kernel modules relevant to the boot chain
- Confirm security configuration (LSM stack order, SELinux enforcement mode at kernel level)
- Identify enabled debug/trace facilities that may be exploitable during downgrade

### Bench applicability (2026-11-17)

The historical [cel_apl configuration](https://github.com/projectceladon/device-androidia/blob/celadon/p/mr0/master/cel_apl/mixins.spec) selects Gen9 graphics, a USB gadget, and an Apollo Lake boot architecture. This supports investigating those components but does not supply the GM display-serializer initialization. [Intel support](https://community.intel.com/t/gordon-peak-mbr-bsp-packages/122422) directs Gordon Peak BSP users to RDC documents 567191 and 567017 with Premier-account access; public source remains useful without claiming access to those restricted documents. Live boot tests and hardware observations belong in [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).

---

## Intel APL Supporting Materials

### Official Intel Documentation

- **UEFI Firmware Enabling Guide for Intel Atom Processor E3900 Series**
  URL: `https://cdrdv2-public.intel.com/671281/uefi-firmware-enabling-guide-for-the-intel-atom-processor-e3900-series.pdf`
  Document #671281. Covers UEFI firmware architecture, IFWI structure, and platform initialization for E3900/A3900.

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
  Describes the SMMU-based memory isolation mechanism used in GHS INTEGRITY's guest VM architecture — the theoretical foundation for understanding how the GHS hypervisor on GM's unit isolates the Linux guest from the INTEGRITY RTOS. Relevant to determining whether memory regions accessible from the Linux guest can be used to influence the hypervisor's boot authorization decisions.

---

## Research Axis Mapping

| Research Vector | Best Available Source |
|---|---|
| misc partition / BCB layout | `kernelflinger.c` + `hardware-intel-bootctrl` HAL + offset 0x800; GM misc (vda9) magic "AB0" at 0x800, CRC32 poly 0xEDB88320 |
| HECI/ABL/ELK trigger chain | `kf4abl.c` + `libheci` (celadon/s/mr0/apollo) + Slim Bootloader `Stage2BoardInitLib.c`; live-tested identity/trigger owned by GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md |
| SELinux baseline vs Y177 policy | `device-intel-sepolicy` + `aosp_diff/*/system/sepolicy` on apollo branch, three-way diff against extracted Y177 policy; enforcing/permissive finding owned by `../platform/security.md` |
| AVB implementation | `kernelflinger` `libkernelflinger/` + `avb/` subtree on celadon/s/mr0/apollo |
| Kernel 4.19 config | Pull from live device: `adb shell "gzip -dc /proc/config.gz"`; a public Intel LTS 4.19.283 reference tree also exists (see Overview) — not the exact GM BSP |
| VT-x guest isolation model | US Patent 12,423,197 (GHS INTEGRITY SMMU/GVM) |
| IFWI structure | Intel UEFI guide #671281 + `intel/FSP` → `ApolloLakeFspBinPkg` binaries |
| IOC/CAN integration | `kf4abl.c` IOC_USE_SLCAN/IOC_USE_CBC flags + `Stage2BoardInitLib.c` IOC IPC reset over UART |
| Board variant identification | GPIO 25/26/30 detection in `Stage2BoardInitLib.c` |
| Thermal / swap / BT config | `device-androidia-mixins` gordon_peak hardware mixin fragments |

---

## Dead Ends

The following research directions were pursued and found to be largely non-viable. Do not re-investigate without new information.

| Dead End | Status | Notes |
|---|---|---|
| `celadon-binary` prebuilts | HTTP 404, reconfirmed 2026-11-17 | Must build from source; 404 does not prove Intel never released images (see Overview History). |
| Gordon Peak Android BSP | CNDA-gated | Docs #567191, #572371, #566285 require Intel NDA. No public route exists. |
| `mcg-depot.intel.com` ACRN flashfile | Internal host only | No external DNS. Intel employee intranet only. |
| `android.googlesource.com/device/intel/gordon_peak` | HTTP 404 | Never published publicly. Path exists in some manifest references but returns 404. |
| `firmware.intel.com` / `01.org` | Both decommissioned | All Intel open-source firmware hosting has migrated; old URLs return 404. Use GitHub (`intel/` org) and `cdrdv2-public.intel.com` instead. |
| E3900 binary objects R71 | HTTP 403 | Access restricted. Not obtainable without authenticated Intel developer account. |
| Linux 4.19 as a Celadon lunch target | Does not exist in Celadon | Celadon lineage skips 4.9 → 5.15; no 4.19 branch inside Celadon proper. A public Intel LTS 4.19.283 reference tree exists *outside* Celadon (see Overview) and is not a dead end on its own — only the "Celadon ships 4.19" framing was. |
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

*Document generated: 2026-06-29. Research conducted as open source intelligence (OSINT) using publicly available repositories, documentation, and patent filings. No NDA-gated materials were accessed or reproduced. Amended in place 2026-08-25 (SELinux enforcing finding, now pointered to `../platform/security.md`), 2026-09-10 (ELK identity/trigger, now pointered to GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md), and 2026-11-17 (prebuilt-image and 4.19-source overstatements corrected in place, see Overview).*
