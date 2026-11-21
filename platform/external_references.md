# External References

Index of public and third-party resources used by this research: Intel Apollo Lake (APL) / Celadon / bootloader sources for the Intel gminfo37 radio, the NDA-gated list, the surrealdev.com (Snipesy) bibliography for the Global B / Cadillac radio, and patents.
Evidence tag used here: **[X]** = external, single-source, not verified against our own hardware. Untagged index entries are pointers to resources, not findings.

Related: [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md) (platform variant), [hardware_specs.md](hardware_specs.md) (Intel A3960 SoC/I-O datasheet facts), [boot_chain.md](boot_chain.md), [security.md](security.md), [ota_programming_roles.md](ota_programming_roles.md), [vehicle_network.md](vehicle_network.md), [vip_ipc_ghs.md](vip_ipc_ghs.md)

Target platform: Intel Atom x7-A3960 (Apollo Lake / Goldmont), Android 12 AAOS under GHS INTEGRITY IoT hypervisor. All clones are placed in `~/Downloads/github/` unless noted.
The A3960 datasheet-confirmed SoC / platform I/O spec (formerly appended to the source of this index) lives in [hardware_specs.md](hardware_specs.md); it is not repeated here.

## 1. Intel APL / Android reference sources

### 1.1 Project Celadon (Intel's Android-on-x86 reference)

Closest public equivalent to the GM Info 3.7 software stack. No dedicated AAOS branch; AAOS support is delivered as patches.

Cloned repositories:

| Repo | Branch | Path | Value |
|---|---|---|---|
| kernelflinger | celadon/s/mr0/apollo | ~/Downloads/github/kernelflinger | ABL integration, HECI/CSE, AVB, ELK trigger code |
| vendor-intel-utils | celadon/s/mr0/apollo | ~/Downloads/github/vendor-intel-utils | SELinux baseline, AAOS patches (aosp_diff/aaos_iasw) |
| device-androidia | celadon/p/mr0/master | ~/Downloads/github/device-androidia | Gordon Peak config lineage (caas/mixins.spec) |
| device-intel-sepolicy | master | ~/Downloads/github/device-intel-sepolicy | SELinux policy baseline for Intel AAOS |
| celadon-manifest | master | ~/Downloads/github/celadon-manifest | All build manifests (A10-A15) |

Key files within kernelflinger (celadon/s/mr0/apollo):

- `kf4abl.c` - ABL boot integration, HECI messaging, IOC/CAN flags (`IOC_USE_SLCAN`, `IOC_USE_CBC`)
- `libheci/` - HECI protocol: Host Embedded Controller Interface between Linux guest and Intel TXE/CSE
- `avb/` - AVB2 verification implementation (compare against GM vbmeta chain)
- `libqltipc/` - Trusty TEE IPC
- `doc/crashmode.md` - Crash mode ADB, EFI variable dump
- `kernelflinger.c` - Boot flow; BCB read at offset 0x800 (matches GM misc/vda9 layout; see [boot_chain.md](boot_chain.md) / [partitions_storage.md](partitions_storage.md))

AAOS content in vendor-intel-utils: `aosp_diff/aaos_iasw/` and `aosp_diff/base_aaos/`

- Base AAOS AOSP patch overlay for Intel x86 platforms
- Per-release SELinux patches under `aosp_diff/*/system/sepolicy/`
- No dedicated AAOS lunch target; AAOS is patches on top of standard Celadon

Reference build (A12, matches the GM info37 era): manifest `CIV_01.22.03.32_A12.xml` (AOSP android-12.0.0_r28 base).

```bash
repo init -u https://github.com/projectceladon/manifest -b celadon/s/mr0/stable \
  -m stable-build/CIV_01.22.03.32_A12.xml
repo sync -c -j8
lunch caas-userdebug && make -j$(nproc)
```

The celadon-binary repo (prebuilts) returns HTTP 404; the build must be made from source.

### 1.2 Slim Bootloader (Gordon Peak MRB reference)

- Local: `~/Downloads/slimbootloader` (sparse: `Platform/ApollolakeBoardPkg` + `Silicon/ApollolakePkg`)
- Source: https://github.com/slimbootloader/slimbootloader
- Key file: `Platform/ApollolakeBoardPkg/Library/Stage2BoardInitLib/Stage2BoardInitLib.c`
  - Defines `PLATFORM_ID_GPMRB` (Gordon Peak MRB explicit reference)
  - IOC IPC reset over UART
  - Platform ID detection via GPIO 25/26/30
  - Reference for HECI/ABL/IOC integration on this exact board family
- Build: `python BuildLoader.py build apl`

### 1.3 Intel FSP Apollo Lake

- Local: `~/Downloads/intel-FSP/ApolloLakeFspBinPkg` (sparse clone)
- Source: https://github.com/intel/FSP/tree/master/ApolloLakeFspBinPkg
- Contains `Fsp.fd`, `Fsp.bsf`, VBT (Video BIOS Table)
- Value: reference FSP for boot chain / IFWI structure understanding.

### 1.4 Intel official documentation (PDFs)

| Document | Local path | Value |
|---|---|---|
| UEFI Firmware Enabling Guide (E3900/A3960) | ~/Downloads/intel_apl_uefi_enabling_guide_671281.pdf | IFWI structure, HECI, TXE, Boot Guard config |
| TXE/IFWI Bring-Up Guide v1.1 | (3rd-party mirror; no URL recorded) | PMC FW, FIT, MEU, HECI context |
| E3900/A3960 Datasheet Addendum | https://cdrdv2-public.intel.com/336256/ | SoC pinout, peripheral map |

### 1.5 EDK2 and coreboot (boot chain references)

- EDK2 APL: https://github.com/tianocore/edk2-platforms/tree/devel-IntelAtomProcessorE3900
- coreboot APL SoC: https://github.com/coreboot/coreboot/tree/master/src/soc/intel/apollolake

### 1.6 Patents

- **US 12,423,197** - GVM SMMU fault protection in automotive hosted hypervisor. GHS guest-VM safety model; the most technical public GHS architectural description. URL: https://patents.google.com/patent/US12423197 (GHS usage: [vip_ipc_ghs.md](vip_ipc_ghs.md))

### 1.7 NDA-gated (not obtainable without Intel NDA)

- Gordon Peak Android BSP: docs #567191, #572371, #566285 - CNDA + RDC-gated
- E3900 binary objects R71: HTTP 403
- ACRN flashfile (mcg-depot.intel.com): internal host only
- Gordon Peak AOSP device tree (android.googlesource.com/device/intel/gordon_peak): 404, never public
- APL automotive Linux 4.19 kernel tree: NDA (Celadon has 5.15+; GM's 4.19 is not public)

### 1.8 Kernel 4.19 config (live device)

Not available from any public source. Extract from the connected device:

```bash
adb shell "gzip -dc /proc/config.gz" > gm_kernel_4.19.305.config
```

`CONFIG_IKCONFIG_PROC=y` was confirmed in the Jun 2026 enumeration (no further source recorded), so the config is accessible.

### 1.9 Research axis mapping

| Research vector | Best external source |
|---|---|
| misc/BCB A/B layout | kernelflinger.c boot flow (celadon/s/mr0/apollo) |
| HECI/ABL/ELK trigger | kf4abl.c + libheci + Slim Bootloader Stage2BoardInitLib.c |
| SELinux mode (both builds enforce; no stock permissive) | device-intel-sepolicy + aosp_diff/*/system/sepolicy |
| AVB2 verification chain | kernelflinger avb/ subtree |
| IFWI/Boot Guard structure | Intel UEFI guide #671281 + FSP ApolloLakeFspBinPkg |
| GHS guest isolation model | US patent 12,423,197 |
| Kernel 4.19 config | Pull from live device /proc/config.gz |

History: the SELinux row previously read "permissive (Y177) vs enforcing (Y181)"; corrected - both enforce, no stock build is permissive (see [security.md](security.md)).

## 2. surrealdev.com (Snipesy / Surreal Development) bibliography [X]

Canonical bibliography for the *"Rooting the Cadillac"* series and related posts by **Snipesy / Surreal Development LLC**. All other docs that cite this site (`vehicle_network.md` Plane 1a and vlan502, section 3 below / `ota_programming_roles.md` Global-B provisioning, `hardware_specs.md` VIP sleep, `research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md` section 7) draw from these and should point here.

| Article | Published | License | URL |
|---|---|---|---|
| Rooting the Cadillac Part 1: Lay of the Land | 2026-08-15 | author's commentary (no explicit license; "at your own risk") | `https://surrealdev.com/rooting-the-cadillac-part-1-lay-of-the-land/` |
| Rooting the Cadillac Part 2: SecOc | 2026-09-22 | author's commentary (no explicit license) | `https://surrealdev.com/rooting-the-cadillac-part-2-secoc/` |
| The ABCs of Global B | 2026-06-16 | **CC0 1.0** (public domain) | `https://surrealdev.com/the-abcs-of-global-b/` |
| Maybe you should decline OTAs? | 2026-07-30 | author's commentary (opinion; not integrated) | `https://surrealdev.com/maybe-you-should-decline-otas/` |

- **Author/credits:** posts by *Snipesy*; Part 1 also credits Jessie Hoogestraat, Stephanie Howanietz, and Kevin Pham (Deoxy). Disclaimed as personal/independent research, not official Surreal Development guidance.
- **License precision:** only *The ABCs of Global B* is released CC0 1.0 - its text/figures may be reused freely. The two *Rooting the Cadillac* posts carry no reuse license, so this repo paraphrases their facts (with attribution) rather than copying text.
- **Reliability:** single-source, other-vehicle (Cadillac Lyriq/CT5 + 2023 Colorado). Tagged [X] throughout and cross-checked against our own Intel-platform findings; see each citing doc for the agree/conflict caveats (notably the SDGM/CGM/SGM naming and the "$27-against-SDGM" framing, which conflict with this repo's captures - detailed in section 3).
- Primary vehicles of the source: 2025 Cadillac Lyriq / 2025 CT5-V (Qualcomm) and a 2023 Chevy Colorado (Intel).

### 2.1 Rooting the Cadillac Part 1 - quoted/derived items used elsewhere [X]

- **Low-power sleep.** Part 1 (Snipesy, 2026-08-15) reports the RH850 "VIP" powers itself down in deep sleep and wakes on a hardware signal direct from its **CAN phy**, letting the whole radio idle at **sub-milliamp** draw on the always-on 12 V feed. Consistent with this board's VIP role (power/CAN/early-boot); the sub-mA figure is the author's Cadillac measurement, **not independently confirmed on this A11 unit.** [X] Owner of the VIP-side description: [hardware_specs.md](hardware_specs.md) / [vip_ipc_ghs.md](vip_ipc_ghs.md).
- Platform, display, BOM and VIN-gate facts from Part 1: [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md).
- SecOC CAN authentication (Plane 1a) and VLAN-502 CAN-over-Ethernet mirror (Part 2 / same source): [vehicle_network.md](vehicle_network.md).

## 3. The ABCs of Global B - Global B provisioning and SPS/DPS economics (external corroboration) [X]

> **Source.** Snipesy / Surreal Development, *"The ABCs of Global B"*, 2026-06-16, **CC0 1.0** (`https://surrealdev.com/the-abcs-of-global-b/`). Independent public RE; primary vehicles a 2023 Chevy Colorado (Intel) and 2025 Cadillac Lyriq/CT5 (Qualcomm SA8155P). **[X]** = external/other-vehicle, not independently confirmed on this A11 unit; it corroborates the reconciled model in [ota_programming_roles.md](ota_programming_roles.md), but read the caveats.

- **Global B lineage.** GM's newer architecture (author says previously branded **Ultifi** / "VIP Architecture"), standard across the GM lineup **since 2023**, replacing Global A. This repo treats **Ultifi** as the GM *Android service layer* (`com.gm.ultifi.*`), so "Global B = Ultifi" is the author's naming, not a confirmed equivalence here. [X]
- **Circle of accountability.** Every significant module (30+ on some vehicles) handshakes the central gateway at start using a factory-provisioned secret; one failure gives whole-vehicle **no start** + DTC **U1962**. Proper module replacement requires GM's **Serial Data Authentication Configuration (SDAC)** run against GM's **"back office"** (Azure-hosted for NA), which holds the CA/private keys - the vehicle cannot self-provision. [X]
  - *Caveat / naming conflict:* the author uses **SDGM = SGM = CGM = "central gateway"** interchangeably. **Do not adopt that equation here** - this research has (a) *not* established CAN gateway `0x45` as the CGM (see [vehicle_network.md](vehicle_network.md) join points, item 3; `/Volumes/.../VEHICLE_NETWORK_TOPOLOGY.md`), and (b) uses **SGM = Shanghai-GM** (SAIC-GM regional key backend, `tisvcsv4.dll`), a false-friend collision. "SDGM" is the author's term.
- **$27 SecurityAccess.** Author states $27 is taken **against the SDGM/central gateway** (not the target module, unlike Global A); seed changes per request; the tester must round-trip GM's servers (SPS2/3) for the key; **secondary $27 blockers** (notably key reprogramming) use a *different* server-side key, so gateway access is not whole-vehicle access. *Caveat:* on **this** platform the DPS captures show $27 as a **per-ECU** exchange (seed/key direct to ECU `0x80` radio, `0x45` gateway - `LIVE_DPS_CAPTURE_ECU80_AUG2026.md`), so the "always against the SDGM" framing is Cadillac-specific / unconfirmed here. The per-VIN SPS-events cap and secondary-key detail are additive. [X]
- **SPS/DPS economics and bypass.** SPS3 about **$4,400/yr** or **$45** temporary single-VIN license; gives an SPS3 credential usable to obtain $27. **DPS** provisions $27 just-in-time for suppliers (privileged actions including key reprogramming, but not arbitrary-image install). Author: it is "trivial" to **spoof the SPS3/DPS flow** (pretend to be the vehicle) or **hijack a live SPS session** to grab the $27 key; GM has **rate-limited SPS events per VIN** to hamper tuners. [X]
- **GM cloud/OTA auth composition.** The head-unit's GM-server auth is built from **3 configurable values - gateway/CGM id + radio/CSM id + VIN** (~40 bytes entropy) - plus baked-in hardcoded values and an **obfuscated OAuth2 secret shared per Android build** (author notes the OAuth2 secret is low-value; the 3 config values are the real secret). A signed cert derived from these is then used for all subsequent API calls; the **telematics module performs the actual OTA download**, radio only kicks off the campaign. Aligns with the Cloud -> CGM -> `gmConnectionService` -> `gm_update_engine` chain in [ota_update_stack.md](ota_update_stack.md) / [ota_programming_roles.md](ota_programming_roles.md); the 3-value + OAuth2 composition is new/additive. [X]

## Open conflicts

None between sources in this document. Standing caveats (not conflicts between our own sources) are inline in section 3: author's SDGM=SGM=CGM equation vs this repo's unestablished `0x45`=CGM; author's "$27 against SDGM" vs per-ECU $27 in our DPS captures.
