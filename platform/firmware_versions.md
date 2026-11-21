# Firmware Versions

Version and identity reference for gminfo37 (Intel Apollo Lake / Broxton, Android 12 / API 32): Y175 / Y177 / Y181(B) comparison, build strings and fingerprints, patch levels, kernels, component part numbers, slot and update history, naming scheme.
Not here: module IDs and signing (see [ota_programming_roles.md](ota_programming_roles.md)), CalDef/UDS tables ([vehicle_config.md](vehicle_config.md)), security posture ([security.md](security.md)), boot flow ([boot_chain.md](boot_chain.md)).

Research date: December 2025 - February 2026 (original research window; capture dates below are later live reads).

Evidence tags: **[C]** confirmed live (adb getprop / running radio / recovery-export direct read), **[S]** static firmware or snapshot analysis only, **[I]** inferred from other facts, **[U]** unverified. Dates are capture dates.
Coverage: Y175 column [C] live 2026-10-05; Y181B [C] live adb + recovery export 2026-11-12; Y177 is [S] only (never read live; runtime-dump snapshot from the 2025 Y177.6.1 YAML, formerly in `gminfo3.7_tech_specs.md`).

Related: [boot_chain.md](boot_chain.md), [security.md](security.md), [ota_update_stack.md](ota_update_stack.md), [ota_programming_roles.md](ota_programming_roles.md), [vehicle_config.md](vehicle_config.md), [ethernet_networking.md](ethernet_networking.md), [hardware_specs.md](hardware_specs.md), [vip_ipc_ghs.md](vip_ipc_ghs.md), [partitions_storage.md](partitions_storage.md).

History (this doc):
- 2026-08-26: Y177 "SELinux permissive" and "VIP security fn stubbed (4B)" claims retracted (no stock build runs permissive; the VIP validator is the full ~906 B function in every build); the "Y177 is a security regression" conclusion is retracted. SOC_HOSTOS is x86-64, not 32-bit. Basis: `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` section 0, `research/security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8; three-way VIP byte diff 2026-08-25 (see [security.md](security.md), VIP security function section).
- 2026-10-05: live Y175 radio confirmed the whole Y175 column; DABridge port row refuted as a Y175/Y181 discriminator.
- 2026-11-12: Y181B live identity, update/slot history folded in; USB `86405527` row id 29 and update-engine slot sequence corrected into the history below.

## 1. Version comparison

| Field | Y175 (June 2024) [C] | Y177 (March 2025) [S] | Y181 / Y181B (July 2025) [C] |
|-------|----------------------|------------------------|-------------------------------|
| Build | W213E-Y175.5.2-SIHM22B-383.1 | W231E-Y177.6.1-SIHM22B-499.2 (Android string `..._2025-04-03`) | W231E-Y181.3.2-SIHM22B-499.3 |
| Kernel | 4.19.283-PKT-230612T042614Z-ga53d763f5b0d (x86_64) | 4.19.305_240125T145315Z_00094_Mar_5_2025 | 4.19.305-240125T145315Z-gf1edde901aa7 |
| Security patch | 2024-05-05 | 2025-02-05 (snapshot value; earlier table said "~2025-03", see Open conflicts) | 2025-06-05 |
| Bootloader (`ro.bootloader`) | 2121-1 | not read; SOC_ABL part identical to Y181 (see section 4) [I] | 2344 |
| Built | Wed Jun 26 2024 | 2025-03-05 01:42:54 EST | Tue Jul 22 2025 07:45 EDT (`ro.build.date`); the source states the 4.19.305 kernel was built the same day |
| SELinux (runtime) | Enforcing | Enforcing | Enforcing |
| VIP security function | Present (full ~906 B, @0xb6708) | Full ~906 B (@0xb67d4) | Full 906 B (@0xb67d0) |
| VIP firmware diff | not measured | 549,518 bytes (28.4% of the image) differ vs Y181 | Baseline |
| Rollback | not tested | Y181 -> Y177 blocked (GHS counter, see section 6) | n/a |
| SKU (`ro.boot.product.hardware.sku`) | gv221 | not read | gv221 |
| Android | 12 / `ro.build.version.sdk=32` | 12 / API 32 | 12 / SDK 32 |

Notes:
- SELinux: the kernel command line carries `ro.boot.selinux=permissive` / `androidboot.selinux=permissive` on Y175 and Y181B, yet runtime is Enforcing (Y175: 00_whoami, all 179 captured avc lines `permissive=0`; byte-identical init forces enforcing on stock builds). On Y181B the same retained cmdlines also carry a later `enforcing=1` / `androidboot.selinux=enforcing` pair; "later pair wins" is [I]. Posture details: [security.md](security.md).
- Y177 "VIP firmware diff" is the only structural difference measured between Y177 and Y181. Per section 7 it is not a security change.
- Y175 live confirmation 2026-10-05 (`/tmp/radio_audit/20261005_232227/raw/`): fingerprint (security_props), kernel (00_whoami), patch (security_props), bootloader `ro.boot.bootloader` = `ro.bootloader` = 2121-1 (props), build date (props), SKU gv221. No stale Y175 value was found.

### Y175 vs Y181 behavioural differences

| Area | Y175 | Y181 |
|------|------|------|
| Ethernet manager | `ethctrlmgr` | `ethmvlctrlmgr` (swapped) |
| Platform prefix | W213E | W231E |
| SIHM variant | 383 | 499 |
| Bootloader | 2121-1 | 2344 |
| DABridge USB topology | not a discriminator (see below) | 1-6.x |

- Ethernet manager row [C] unchanged on the live Y175: `ethctrlmgr` running (ps PID 918, `init.svc.ethctrlmgr=running`), `ethmvlctrlmgr` absent. Y181B live: `init.svc.ethmvlctrlmgr=running`, `init.svc.ethctrlmgr=stopped`, process up under uid `vendor_ethctrlmgr` (2026-11-12). Manager selection is consistent with the Marvell switch module string in section 2 [I]; it is not a chip read. Switch behaviour: [ethernet_networking.md](ethernet_networking.md).
- DABridge row refuted 2026-10-05: the live Y175 radio (same exact build 383.1) reports `sys.dabridge.dev.portnum=1-6.3` / `host.portnum=1-6.0` (props.txt:482-483), the value previously attributed to Y181. The earlier Y175 enumeration (`gm_enum_20260117_081801`, identical build) reported `1-12.3` / `1-12.0`. Same firmware, two port numbers: the value tracks which physical USB receptacle the DA bridge enumerated on, not the firmware version (same single-dump artifact class as the networking-ports note in `../VERIFICATION.md`). USB topology: [hardware_specs.md](hardware_specs.md).

## Y181B runtime/export identity (2026-11-12)

The bench radio is identified by the operator as **Y181B**. Both [recovery exports](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12) retain the same `update/moduleinfo` and `recovery/props.log`. The version text alone does not distinguish Y181 from Y181B; preserve package/module identities and capture provenance rather than renaming every Y181 artifact B.

| Exported component | Part number / version |
|---|---|
| Android system | `86331654`, `W231E-Y181.3.2-SIHM22B-499.3` |
| Android boot | `86331652`, same version (module 23, radio name `SOC_ANDROID_BOOT`; package-side label `SOC_BOOT`; see [ota_programming_roles.md](ota_programming_roles.md)) |
| VIP application (module 1) | `86331656`, `2B.B5.01.01`; DLS `CN`, build 25Jun19-2209 (image `appl`) |
| GHS HostOS (SOC_HOSTOS, module 21) | `85098662`, `INTEGRITY IoT 2020.18.19 MY22-026` |
| SOC_ABL (module 72; labelled "SoC boot" in the export) | `85738845`, version `2344`, DLS `AB` |
| VIP bootloader (VIP_BOOT, module 71) | `85056831`, DLS `AA`, `B2.9C.01.01` (build 23Jul28-1212, image `bolo`) |
| FIDM (module 81) | `84961617`, DLS `AA`, version `6` |
| SXM tuner | `86404694`, DLS `AC` |
| Ethernet switch | `85759612`, `MVL88Q5050_globalB_234702AB_02_09_1003` |
| Kernel (recovery ring buffer) | `4.19.305-240125T145315Z-gf1edde901aa7` |
| Recovery properties | `user/release-keys`, patch `2025-06-05`, `ro.debuggable=0` |

- The `UpdateDB` history includes manifest `86405527.mnf`, version `SIHM22B-00499.03`; cached older manifests are not a current-module inventory.
- The switch row is the updater's reported module identity/version. It does not resolve physical-chip identity against board teardown or switch-flash evidence. Ethernet switch silicon varies by board revision (Broadcom BCM89551 on the MY22 teardown unit vs Marvell 88Q5050 module string here): treat as board variant, not contradiction. Switch detail: [ethernet_networking.md](ethernet_networking.md), [hardware_specs.md](hardware_specs.md).
- `moduleinfo` inventories 18 modules; its timestamp field is 2026-11-12 13:10:49 AKST, i.e. written by the normal-Android updater [I] (2026 wall clock vs recovery's 2010/2011 clock). Module IDs, signing tiers, and the three modules not in the 15-module package list (53, 54, 81): [ota_programming_roles.md](ota_programming_roles.md).
- Part-number naming: 85738845 appears as "SoC boot" (export table), `SOC_ABL` (VIP file table, DPS list) and is module 72; the radio's `SOC_BOOT` name belongs to module 72 (85738845), while module 23 (86331652, the Android boot above) is `SOC_ANDROID_BOOT` radio-side and labelled `SOC_BOOT` only in the package table (a name collision, not a data conflict; use module IDs).

### 2.1 Live cross-check (adb, 2026-11-12, read directly from the running radio) [C]

| Property | Value |
|---|---|
| `ro.build.display.id` | `full_gminfo37_gb-user 12 W231E-Y181.3.2-SIHM22B-499.3 231 release-keys` |
| Android / SDK | 12 / 32 |
| `ro.build.version.security_patch` | 2025-06-05 |
| `ro.build.date` | Tue Jul 22 2025 (07:45 EDT) |
| `uname -r` | `4.19.305-240125T145315Z-gf1edde901aa7` |
| `ro.bootloader` = `ro.boot.bootloader` | 2344 |
| `ro.boot.product.hardware.sku` | gv221 |
| `ro.boot.slot_suffix` | `_a` |
| `ro.boot.verifiedbootstate` | green |
| `ro.boot.vbmeta.device_state` | locked |
| `ro.boot.flash.locked` | 1 |
| `ro.boot.vbmeta.avb_version` | 1.1 (also the kernel-cmdline token in the retained kernel logs) |
| `ro.boot.avb_version` | 1.2 on this build ("AVB 1.1" shorthand applies only to the vbmeta-side token) |
| `ro.boot.vbmeta.digest` | present |
| `ro.boot.ABL.secureboot` | empty at runtime |

`ABL.secureboot=1` appears only in the retained kernel-log command lines (decompressed boot logs and recovery `last_kmsg*`): ~188 occurrences per archive (376 if the duplicate export is double counted; an earlier "386" count was not reproduced). It is a cmdline-only indicator, not an Android property. Verified-boot flow: [boot_chain.md](boot_chain.md).

Y175 live equivalents [C] (2026-10-05): `verifiedbootstate=green`, `flash.locked=1`, `vbmeta.device_state=locked`, `ro.boot.avb_version=1.2` / `ro.boot.vbmeta.avb_version=1.1`, vbmeta `hash_alg=sha256`, `size=3328`, `digest=76b736eaf87d186de5f03f08176b67ae2cdcf91130b4350b328b0876c00bb585`.

## 3. Build identification (per build)

| Field | Y175 [C] | Y177 [S] | Y181B [C] |
|---|---|---|---|
| Build fingerprint | `gm/full_gminfo37_gb/gminfo37:12/W213E-Y175.5.2-SIHM22B-383.1/213:user/release-keys` | `gm/full_gminfo37_gb/gminfo37:12/W231E-Y177.6.1-SIHM22B-499.2/231:user/release-keys` | `gm/full_gminfo37_gb/gminfo37:12/W231E-Y181.3.2-SIHM22B-499.3/231:user/release-keys` |
| Hardware SKU | gv221 | not read | gv221 |
| Device | gminfo37 | gminfo37 | gminfo37 |
| Product / platform | full_gminfo37_gb | full_gminfo37_gb (platform `full_gminfo37_gb_broxton`) | full_gminfo37_gb |
| Build type / tags | user / release-keys | user / release-keys | user / release-keys |

The Y177 snapshot lists manufacturer `Harman_Samsung` and vehicles `Chevrolet_GMC_Cadillac_2023_onward`.

## 4. VIP and SoC component part numbers

| Field | Y175 | Y177 [S] | Y181 / Y181B |
|---|---|---|---|
| VIP_APP part number (module 1) | not recorded | 86283151 | 86331656 |
| VIP_APP version / build | `2B.175.1.5`, build 24Apr23-2202 (`evidence/enumeration/Y175/Y175_VIP.log:6-7`, cited in [security.md](security.md)) | build 25Feb28-0330 | `2B.B5.01.01`, build 25Jun19-2209 |
| VIP_BOOT (module 71) | not recorded | 85056831 | 85056831 (IDENTICAL) |
| SOC_HOSTOS (module 21) | not recorded | 85098662 | 85098662 (IDENTICAL) |
| SOC_ABL (module 72) | not recorded | 85738845 | 85738845 (IDENTICAL) |

- VIP_BOOT, SOC_HOSTOS and SOC_ABL are identical between Y177 and Y181. Y177's SOC_ABL part equals Y181's (version 2344), so Y177's bootloader is probably 2344 [I]; it was never read.
- An older VIP_APP, `2B.174.4.1` (build 24Mar22-0256), appears in the July 2024 UART capture `evidence/enumeration/VIP_log_2B.174.4.1_10JUL24.txt` (cited in [security.md](security.md)); it predates the Y175 radio's own `2B.175.1.5`.
- GHS INTEGRITY hypervisor: identical in Y177 and Y181. Version `INTEGRITY IoT 2020.18.19 MY22-026`; SOC_HOSTOS is a 14.9 MB statically linked GHS INTEGRITY ELF, **x86-64** (corrected 2026-08-26: the ELF header claims EM_386/32-bit but the code is x86-64: `movabs`/REX, `crt_x64.86`); build path `/home/mal/gm_release/MY22-026/final/iot/rtos/`. Hypervisor behaviour: [vip_ipc_ghs.md](vip_ipc_ghs.md).

## 5. Update and slot history (Y181B, directly read 2026-11-12)

Source: exported `/update_cache` data from both recovery archives. The `update/` trees are byte-identical; `UpdateDB` has 15 `UpdateResults` rows and no `Packages` rows. Stored records are persisted history, not a fresh installation result or an active-package query. The history spans multiple versions/campaigns and must not be attributed entirely to the deliberate homescreen-removal experiment. Retained manifests and signature metadata are not a complete restorable firmware image. Update mechanics and recovery-log narrative: [ota_update_stack.md](ota_update_stack.md).

| Item | Value | Source |
|---|---|---|
| `ReflashCounter` | 11 (10 -> 11 at 2026-09-28 17:25:28 local) | `UpdateDB` `NameValues`; gmlogger system log, `UpdateService-PersistStore` lines |
| `slot_switched` marker | `N` (no switch pending at export) | `update/slot_switched` (both exports) |
| Last stored `ProgrammingStatus` | 2026-09-28 17:25:28 (-08:00), manifest `86405527`, `SIHM22B-00499.03`, Status=1, 99%, ErrorCode=0 | `UpdateDB` |
| `UpdateResults` span | 15 rows, InstallDate 2025-05-10 (manifest `85759595`, `SIHM22B-00383.01`) through 2026-09-28 | `UpdateDB` |
| OTA rows 2026-09-28 | `GM Update N25-250552` (14:52 UTC), `Important Update GM 661.10` (16:22 UTC) | `UpdateDB` |
| USB `86405527.mnf` `00499.03` rows (two) | id 24: InstallDate 2026-08-25 15:09:45 UTC; id 29: InstallDate 2026-09-29 01:34:12 UTC = 2026-09-28 17:34 local (UTC-8), Result 0 | `UpdateDB` `UpdateResults` (re-read from the raw export) |
| Android active slot around the 09-28 recovery install | before = 1 (B), after = 0 (A), 17:27 -> 17:33 local | gmlogger system log, `UpdateService-RecoveryModeInstaller` lines |
| Current slot | `_a` | live `ro.boot.slot_suffix` |
| `LastCheckUpdateTime` | 2026-11-07 23:09 UTC | `UpdateDB` |

"USB `00499.03` + two OTAs on 2026-09-28" is supported by the set above: two OTA rows, the `00499.03` ProgrammingStatus (17:25:28 local) and USB row id 29; the earlier USB row (id 24) is the 2026-08-25 install.

### 5.1 Slot sequence

- **Update-engine logs** (year-long history; "Loaded metadata from source slot" lines in a forensic extract of the update cache; the forensic file is not in this repo): A (from 02-03) -> B 02-10 10:45:17 -> A 04-30 20:46:48 -> B 08-25 07:09:17 -> A 09-28 17:33:45 -> still A at 11-12 13:10. Four changes, matching the four USB installs.
- **Retained recovery kernel logs** (only 31 boots, `last_kmsg`..`.30`, oldest -> newest, from `androidboot.slot_suffix` in the cmdline): A x2, B x5, A x7, B x5, A x12 (four transitions, two B episodes in the window).

### 5.2 Y175 bench post-update check (2026-11-17)

After a full USB update with CAN-supplied bench conditions (narrative: [ota_update_stack.md](ota_update_stack.md)), read-only verification on the Y175 radio returned: build Y175.5.2 / SIHM22B-383.1; active slot A (changed from B); stored manifest/version `85759595` / `SIHM22B-00383.01`; Status/Percentage/ErrorCode 1 / 99 / 0; `ReflashCounter` 10 (no pre-update counter, so no delta). Manifest `85759595` is the same one that begins the Y181B `UpdateDB` history (2025-05-10).

## 6. Rollback

Rollback protection is a GHS counter in `misc`, independent of AVB (both Y177 and Y181 `vbmeta` have `rollback_index=0`). Y181 -> Y177 downgrade is blocked [tested: partitions write, GHS rejects at boot, A/B falls back to the previous slot]; Y181 -> Y181 reinstall succeeds. `version check disabled` in the OTA manifest affects only the write phase. Mechanism and tests: [boot_chain.md](boot_chain.md).

## 7. Retraction: "VIP_APP is the only difference / Y177 security regression"

Earlier text claimed the Y177 vs Y181 security behavioural difference "resides entirely in the VIP_APP firmware" (and, with the hypervisor identical, "entirely in VIP firmware"). That was written under the pre-2026-08-26 stub claim. Resolved: no security behavioural difference exists. The ~906 B validator is present in all builds (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0); the "Y177 stub" was a fixed-address misread. What stands: VIP_BOOT, SOC_HOSTOS and SOC_ABL are identical in Y177 and Y181, and the VIP_APP image differs by 549,518 bytes (28.4%) for unrelated reasons. Details: [security.md](security.md), VIP security function section.

## 8. Version naming convention

Pattern: `W[platform]-Y[version].[minor].[patch]-[variant]-[build]`

- **W213E** / **W231E**: platform identifier. 213 = Y175 and 231 = Y177/Y181 hardware generation, E = variant. [I]: inferred from the fingerprint suffixes `/213` and `/231`, not a documented GM scheme.
- **Y181**: major version (Y-series).
- **3.2**: minor and patch.
- **SIHM22B**: build variant identifier.
- **499.3**: build number (383.x on Y175; 499.x on Y177/Y181).

## Where the removed content went

| Topic | Home |
|---|---|
| CalDef security calibrations, VIP `cal_` values, UDS service table | [vehicle_config.md](vehicle_config.md) |
| DPS (AES-CMAC, server key provisioning, no direct EEPROM write), DPS module IDs / TSS-signed vs unsigned, 18-module note | [ota_programming_roles.md](ota_programming_roles.md) |
| Y181B recovery-log reboot sequence and wipe reasons | [ota_update_stack.md](ota_update_stack.md) |

## Open conflicts

1. Y177 security patch: this doc's earlier table said "~2025-03"; the Y177 runtime snapshot (`gminfo3.7_tech_specs.md` L16 `security_patch: 2025-02-05`) gives 2025-02-05. Both are [S]; 2025-02-05 is used above because it is a specific value, but the Y177 build date is 2025-03-05, so the "~2025-03" approximation may reflect the build date. Never read live.
2. Y181 "kernel built the same day" as `ro.build.date` (source `firmware_versions.md` L89): the kernel version tag `240125T145315Z` is identical in Y177 and Y181 and the Y177 uname build date is Mar 5 2025; the Y181 `uname -v` date is not recorded in any source. Claim retained as stated, [U].

Resolved (kept for traceability): VIP_APP-only security difference (section 7); DABridge discriminator (section 1); ABL.secureboot count (section 2.1); SoC boot / SOC_ABL naming (section 2); Android boot 86331652 = module 23 `SOC_ANDROID_BOOT` (formerly "no module ID established" here, contradicting ota_programming_roles.md; resolved from the pre-reorg OPR naming note, not a dated-source conflict).
