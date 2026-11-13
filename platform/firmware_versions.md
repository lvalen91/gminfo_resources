# GM Info 3.7 Firmware Versions

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

> **⚠ CORRECTED 2026-08-26:** the "SELinux Permissive" and "VIP security fn: Stubbed (4B)" claims for Y177 are FALSE.
> No stock build runs permissive (byte-identical init forces enforcing), and the VIP validator is FULL (~906 B) in all
> builds — there was never a stub. So "Y177 is a security regression" is retracted. HOSTOS is x86-**64**, not 32-bit.
> See `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0 and `research/security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8.

## Y181B runtime/export identity (2026-11-12)

The bench radio is identified by the operator as **Y181B**. Both
[recovery exports](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12)
retain the same `update/moduleinfo` and `recovery/props.log`. The version text
alone does not distinguish Y181 from Y181B; preserve package/module identities
and the capture provenance rather than silently renaming every Y181 artifact B.

| Exported component | Part number / version |
|---|---|
| Android system | `86331654`, `W231E-Y181.3.2-SIHM22B-499.3` |
| Android boot | `86331652`, same version |
| VIP application | `86331656`, `2B.B5.01.01` |
| GHS HostOS | `85098662`, `INTEGRITY IoT 2020.18.19 MY22-026` |
| SoC boot | `85738845`, version `2344` |
| VIP bootloader (module 71) | `85056831`, DLS `AA`, `B2.9C.01.01` (build 23Jul28-1212, image `bolo`) |
| VIP application build/DLS | DLS `CN`, build 25Jun19-2209 (image `appl`) |
| SoC boot (module 72) DLS | `AB` |
| FIDM (module 81) | `84961617`, DLS `AA`, version `6` |
| SXM tuner | `86404694`, DLS `AC` |
| Ethernet switch | `85759612`, `MVL88Q5050_globalB_234702AB_02_09_1003` |
| Kernel from recovery ring buffer | `4.19.305-240125T145315Z-gf1edde901aa7` |
| Recovery properties | `user/release-keys`, patch `2025-06-05`, `ro.debuggable=0` |

The database history includes manifest `86405527.mnf`, version
`SIHM22B-00499.03`; cached older manifests are not a current-module inventory.
The switch row is the updater's reported module identity/version. It does not
by itself resolve physical-chip identity against separate board teardown or
switch-flash evidence. **Corroboration 2026-11-12 (live adb):** `init.svc.ethmvlctrlmgr=running`,
`init.svc.ethctrlmgr=stopped`, and the `ethmvlctrlmgr` process is up under uid `vendor_ethctrlmgr`;
the `mvl` manager selection agrees with the Marvell module string (inferred: same board-variant
switch; still not a chip read).

**Live cross-check, 2026-11-12 (adb, build read directly from the running radio):**
`ro.build.display.id` = `full_gminfo37_gb-user 12 W231E-Y181.3.2-SIHM22B-499.3 231 release-keys`;
Android 12, SDK 32; `ro.build.version.security_patch=2025-06-05`; `ro.build.date` = Tue Jul 22 2025
(07:45 EDT); `uname -r` = `4.19.305-240125T145315Z-gf1edde901aa7`; `ro.bootloader` =
`ro.boot.bootloader` = `2344`; `ro.boot.product.hardware.sku` = `gv221`; `ro.boot.slot_suffix=_a`;
`ro.boot.verifiedbootstate=green`; `ro.boot.vbmeta.device_state=locked`; `ro.boot.flash.locked=1`;
`ro.boot.vbmeta.avb_version=1.1` (also the kernel-cmdline token in the retained kernel logs) **but
`ro.boot.avb_version=1.2`** on this build; `ro.boot.vbmeta.digest` present. The
`ABL.secureboot=1` token is in the retained kernel-log command lines (386 occurrences across the
decompressed boot logs and recovery `last_kmsg*` -- [2026-11-12 NOTE: the '386' count was not reproduced by an independent recount (~188 per archive; 376 if the duplicate export is double counted); count not reproduced, ~188 per archive]; the key point stands); `getprop ro.boot.ABL.secureboot` returns empty
on the live radio, so it is a cmdline-only indicator, not an Android property.
Module list, `ReflashCounter` and slot history below are from the exported `/update_cache` data
(moduleinfo has 18 modules; `moduleinfo` timestamp field = 2026-11-12 13:10:49 AKST, i.e. written
by the normal-Android updater, inferred from the 2026 wall clock vs. recovery's 2010/2011 clock).

**Update/slot history (directly read, 2026-11-12):**

| Item | Value | Source |
|---|---|---|
| `ReflashCounter` | 11 (10 -> 11 at 2026-09-28 17:25:28 local) | `UpdateDB` `NameValues`; gmlogger system log, `UpdateService-PersistStore` lines |
| `slot_switched` marker | `N` | `update/slot_switched` (both exports) |
| Last stored `ProgrammingStatus` | 2026-09-28 17:25:28 (-08:00), manifest `86405527`, `SIHM22B-00499.03`, Status=1, 99%, ErrorCode=0 | `UpdateDB` |
| `UpdateResults` rows that day | OTA `N25-250552` (2026-09-28 14:52 UTC) and `Important Update GM 661.10` (16:22 UTC), plus USB `86405527` row id 29 (17:34 local; see next-but-two row) | `UpdateDB` |
| USB `86405527.mnf` `00499.03` rows (two) | id 24: InstallDate 2026-08-25 15:09:45 UTC; id 29: InstallDate 2026-09-29 01:34:12 UTC = 2026-09-28 17:34 local (UTC-8), Result 0 (corrected 2026-11-12: an earlier note listed only the 08-25 row) | `UpdateDB` `UpdateResults` (re-read from the raw export) |
| Android active slot around the 09-28 recovery install | before = 1 (B), after = 0 (A), 17:27 -> 17:33 local | gmlogger system log, `UpdateService-RecoveryModeInstaller` lines |
| Current slot | `_a` | live `ro.boot.slot_suffix` |
| Slot in retained recovery kernel logs (`last_kmsg`..`.30`, oldest -> newest) | A x2, B x5, A x7, B x5, A x12 (4 transitions, two B episodes in the retained window) | `recovery/last_kmsg*` cmdline `androidboot.slot_suffix` |

Only the retained recovery kernel-log window (31 boots) is directly read from `last_kmsg*`; the year-long history comes from the update engine logs instead. Active slot per the update-engine logs (2026-11-12; `rg -n 'Loaded metadata from source slot' ~/Desktop/gminfo37_update_cache_FORENSIC_LLM.txt`, forensic ref 'Active slot per engine log'): A (from 02-03) -> B 02-10 10:45:17 -> A 04-30 20:46:48 -> B 08-25 07:09:17 -> A 09-28 17:33:45 -> still A at 11-12 13:10; four changes, matching the four USB installs. (Corrected 2026-11-12: this replaces the earlier 'not provable from these exports' wording.) The 2026-09-28
set is two OTA rows (14:52 and 16:22 UTC), the `00499.03` ProgrammingStatus (17:25:28 local) and the second
USB `86405527` result row (id 29, 2026-09-29 01:34 UTC); the earlier USB row (id 24) is dated 2026-08-25, so
"USB + 2 OTAs on 09-28" is supported (corrected 2026-11-12 — an earlier note here said only the 08-25 USB row existed).

## Firmware Version Comparison

| Field | Y175 (June 2024) | Y177 (March 2025) | Y181 (July 2025) |
|-------|-------------------|---------------------|-------------------|
| Build | W213E-Y175.5.2-SIHM22B-383.1 | W231E-Y177.6.1-SIHM22B-499.2 | W231E-Y181.3.2-SIHM22B-499.3 |
| Kernel | 4.19.283-PKT-230612T042614Z | 4.19.305 | 4.19.305 |
| Security Patch | 2024-05-05 | ~2025-03 | 2025-06-05 |
| Bootloader | 2121-1 | — | 2344 |
| Built | Wed Jun 26 2024 | — | Tue Jul 22 2025 (`ro.build.date`, live adb 2026-11-12; kernel 4.19.305 built the same day) |
| SELinux | Enforcing | ~~**Permissive**~~ **Enforcing** (corrected) | Enforcing |
| VIP security fn | Present | ~~**Stubbed (4B)**~~ **Full (~906B)** (corrected — no stub in any build) | Full (906B) |
| VIP firmware diff | — | 28.4% vs Y181 | Baseline |
| Rollback | — | Y181→Y177 blocked | — |

> **[C] live-Y175 2026-10-05:** entire Y175 column CONFIRMED against a running radio
> (`W213E-Y175.5.2-SIHM22B-383.1`, `/tmp/radio_audit/20261005_232227/raw/`). Exact matches:
> fingerprint `gm/full_gminfo37_gb/gminfo37:12/W213E-Y175.5.2-SIHM22B-383.1/213:user/release-keys`
> (security_props); kernel `4.19.283-PKT-230612T042614Z-ga53d763f5b0d` x86_64 (00_whoami); security
> patch `2024-05-05` (security_props); bootloader `2121-1` (`ro.boot.bootloader`=`ro.bootloader`=2121-1,
> props); build date Wed Jun 26 2024 (props); Android 12 / `ro.build.version.sdk=32`; SKU `gv221`.
> SELinux **Enforcing** at runtime (00_whoami) **despite `ro.boot.selinux=permissive`** in the kernel
> cmdline (props) — same enforcing-init posture already documented for Y177/Y181, now also confirmed
> live on Y175. No stale Y175 value found.

### Key Observations

- ~~**Y177 is a security regression** — both SELinux and VIP security function were weakened compared to Y175 and Y181~~
  **RETRACTED 2026-08-26:** neither was weakened — stock Y177 forces SELinux enforcing (byte-identical init) and its VIP
  validator is the full ~906 B function, same as Y175/Y181. No regression.
- **Kernel upgraded** from 4.19.283 (Y175) to 4.19.305 (Y177/Y181), gaining security patches
- **Rollback protection** prevents downgrading from Y181 back to Y177, enforced by GHS rollback counter in `misc` partition
- **VIP firmware delta** between Y177 and Y181 is 549,518 bytes (28.4%), indicating substantial changes beyond just the security function

### Y175 vs Y181 Behavioral Differences

| Area | Y175 | Y181 |
|------|------|------|
| Ethernet manager | `ethctrlmgr` | `ethmvlctrlmgr` (swapped) |
| Platform prefix | W213E | W231E |
| SIHM variant | 383 | 499 |
| Bootloader | 2121-1 | 2344 |
| DABridge USB topology | ~~1-12.x~~ **not a variant discriminator** (see note) | 1-6.x |

> **[C] live-Y175 2026-10-05 — DABridge row ADJUSTED (verdict flip).** The Y175 column value
> `1-12.x` is REFUTED as a Y175-vs-Y181 discriminator: the live Y175 radio (same exact build
> `W213E-Y175.5.2-SIHM22B-383.1`) reports `sys.dabridge.dev.portnum=1-6.3` / `host.portnum=1-6.0`
> (props.txt:482-483) — i.e. the value the doc attributed to Y181. The prior Y175 enum
> (`gm_enum_20260117_081801`, identical build) reported `1-12.3`/`1-12.0`. Same firmware, two
> different port numbers, so this tracks which physical USB receptacle the DA bridge enumerated on,
> not the firmware version. Treat like the networking-ports single-dump artifact in VERIFICATION.md.
> Ethernet-manager row CONFIRMED unchanged: live Y175 runs `ethctrlmgr` (ps PID 918,
> `init.svc.ethctrlmgr=running`), `ethmvlctrlmgr` absent — that discriminator holds.

---

## VIP Firmware File Details

| Field | Y177 | Y181 |
|-------|------|------|
| VIP_APP part number | 86283151 | 86331656 |
| VIP_APP build | 25Feb28-0330 | 25Jun19-2209 |
| VIP_BOOT | 85056831 | 85056831 (IDENTICAL) |
| SOC_HOSTOS | 85098662 | 85098662 (IDENTICAL) |
| SOC_ABL | 85738845 | 85738845 (IDENTICAL) |

VIP_BOOT, SOC_HOSTOS, and SOC_ABL are **identical** between Y177 and Y181. The security behavioral difference between Y177 and Y181 resides **entirely** in the VIP_APP firmware.

---

## GHS INTEGRITY Details

The GHS INTEGRITY hypervisor is **identical** between Y177 and Y181:

- **Version:** INTEGRITY IoT 2020.18.19 MY22-026
- **SOC_HOSTOS:** 14.9MB GHS INTEGRITY ELF — **x86-64** (corrected 2026-08-26; the ELF header claims EM_386/32-bit but the code is x86-64: `movabs`/REX, `crt_x64.86`), statically linked
- **Build path:** `/home/mal/gm_release/MY22-026/final/iot/rtos/`

The security difference between Y177 and Y181 is entirely in VIP firmware — the hypervisor layer is unchanged.

---

## DPS / CalDef (Two Separate Systems)

The GM Info 3.7 maintains two distinct calibration systems:

### CalDef — Android/SoC Calibration

- Calibration entries stored on the system partition
- Manages Android-level configuration and feature flags
- Part of the OTA-updated system image

#### Security Calibrations

| CalDef Key | Type | Value |
|-----------|------|-------|
| DEVICE_REGISTRATION_ENABLE_CHECK_OVERRIDE | bool | FALSE |
| EXPIRATION_ENFORCEMENT | bool | TRUE |
| GIS763_PROGRAMMING_ENABLED | bool | TRUE |
| GIS763_SigningCertificateIssuer | string | CN=GPD/OU=GMNA GPD PRODUCTION/O=GENERAL MOTORS LLC |

### VIP Calibrations

- 31 `cal_` values stored in the RH850 VIP MCU firmware
- Controls power management, CAN parameters, and timing values
- Updated independently from Android OTA

### DPS (Data Protection Service)

- Uses **AES-CMAC** for authentication
- **Server-based key provisioning** — keys are not stored locally in plaintext
- DPS **cannot write EEPROM directly** — EEPROM writes go through the VIP MCU's I2C interface
- Handles license verification and calibration integrity

#### DPS Module IDs and Signing

**TSS-signed modules:**

| Module ID | Name |
|-----------|------|
| 1 | VIP_APP |
| 21 | SOC_HOSTOS |
| 22 | SOC_SYSTEM |
| 26 | SOC_VENDOR |

**Unsigned modules:**

| Module ID | Name |
|-----------|------|
| 23 | SOC_BOOT |
| 24 | SOC_UTILS |
| 28 | SXM |
| 29 | GPS |
| 51 | TUNER |
| 52 | ETH_SWITCH |
| 55 | SOC_ACPIO |
| 56 | SOC_VBMETA |
| 57 | SOC_PRODUCT |
| 71 | VIP_BOOT |
| 72 | SOC_ABL |

> **Note 2026-11-12:** the two tables above list the 15 package-side modules (`delivery_manifest.csv`). The live radio's
> `moduleinfo` inventories **18**; the three not listed here are 53 `SOC_ANDROID_ODM` (part 0), 54 `SOC_ANDROID_ACPI`
> (part 0) and 81 `FIDM` (84961617, version `6`). Names/signing tiers for those three are not established by any package
> data. Details: [`ota_programming_roles.md`](ota_programming_roles.md) (corrected-2026-11-12 note).

#### UDS Diagnostic Services

DPS communicates via UDS (Unified Diagnostic Services):

| Service ID | Name | Notes |
|-----------|------|-------|
| $10 | DiagnosticSessionControl | Session management |
| $11 | ECUReset | Reset ECU |
| $22 | ReadDataByID | Read calibration/data |
| $27 | SecurityAccess | 32-byte seed: ECUID(16B) + random(16B) |
| $2E | WriteDataByID | Write calibration/data |
| $31 | RoutineControl | Start/stop/query routines |
| $34 | RequestDownload | Initiate firmware download |
| $36 | TransferData | Transfer firmware blocks |
| $37 | TransferExit | Complete firmware transfer |

---

## Build Identification

| Field | Value |
|-------|-------|
| Build Fingerprint | gm/full_gminfo37_gb/gminfo37:12/W231E-Y181.3.2-SIHM22B-499.3/231:user/release-keys |
| Hardware SKU | gv221 |
| Device | gminfo37 |
| Product | full_gminfo37_gb |
| Build Type | user |
| Tags | release-keys |

---

## Version Naming Convention

GM firmware versions follow the pattern: `W[platform]-Y[version].[minor].[patch]-[variant]-[build]`

- **W213E** — Platform identifier (213 = Y175 hardware generation, E = variant)
- **W231E** — Platform identifier (231 = Y177/Y181 hardware generation, E = variant)
- **Y181** — Major version (Y-series, version 181)
- **3.2** — Minor and patch version
- **SIHM22B** — Build variant identifier
- **499.3** — Build number (383.x for Y175, 499.x for Y177/Y181)
