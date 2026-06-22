# GM Info 3.7 — OTA / SWU Update Stack & UpdateService Binder Surface

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026
**Access:** ADB shell uid=2000 (`service call` Binder probing) + Y181 firmware
package analysis on macOS

This documents the Android-side software-update stack: the `UpdateService`
Binder interface reachable from an unprivileged shell, the SWU state machine,
the Y181 delivery-package format and signing, the actual OTA engine, and the USB
install path. For the cross-version firmware diff (Y175/Y177/Y181), VIP_APP file
IDs, and build IDs see [`platform/firmware_versions.md`](firmware_versions.md);
for the signing/SELinux gate context see [`platform/security.md`](security.md).

---

## UpdateService Binder Interface

Service `com.gm.server.update.UpdateService`, impl `UpdateServiceImplGB.java`,
extends `IUpdateService.Stub`. **No permission check on most read methods** —
fully probeable from uid=2000 via `service call`.

| Tx# | Method | Return / Notes |
|-----|--------|----------------|
| 1 | `getAllPackages()` | Empty List |
| 2 | `getActivePackage()` | null |
| 3 | `getUpdateHistory()` | List of UpdateResult — **full install log with paths** |
| 4 | `registerListener(IUpdateListener)` | — |
| 5 | `unregisterListener(IUpdateListener)` | — |
| 6 | `checkUpdate()` | CheckUpdateResult `{available=1, state=1, version=414}` |
| 7 | `download(PackageDetails)` | NPE (needs Parcelable) |
| 8 | `resume(PackageDetails)` | — |
| 9 | `pause(PackageDetails)` | — |
| 10 | `initialInstall(PackageDetails)` | initial-install trigger |
| 11 | `install(PackageDetails)` | **install trigger** |
| 12 | `cancelInstall(PackageDetails)` | — |
| 13 | `decline(PackageDetails)` | — |
| 14 | `remind(PackageDetails)` | — |
| 15 | `startMADAI(PackageDetails)` | — |
| 16 | `schedule(int, PackageDetails)` | — |
| 17 | `getLastScheduleClockTime()` | null |
| 18 | `getModuleVersion(int)` | "" |
| 20 | `isNetworkAvailable()` | false |
| 21 | — | timestamp/state data |
| 23 | — | **update preferences Bundle** (below) |
| 24 | — | UpdateStatusData: firmware=SIHM22B-00499.03, Status=1 (COMPLETE), 99%, ProgrammingType=15 |
| 25 | — | PartNumbers `85056831.AA`, `85738845.AB` |
| 26 | — | `0.AA` (calibration) |
| 27 | — | bool true |
| 30 | `getReflashAttempts()` | **9** |

`install()` (Tx11) deserializes a `PackageDetails` Parcelable with no permission
gate, then NPEs in the internal install manager — i.e. the execution path is
reached but no caller-permission check guards it.

### Update Preferences Bundle (Tx 23)

Seven keys in `PersistStore.Key.PREFERENCES`:

| Key | Live value | Notes |
|-----|-----------|-------|
| RecoveryDebug | null | Debug-only |
| IgnoreNetwork | null | — |
| DownloadInBackground | "false" | Set |
| TestDiagnostic | null | — |
| WiFiPreferred | "false" | Set |
| IgnoreBattery | null | — |
| **AllowDevSignedVIP** | null | **dev-signing bypass flag** |

**AllowDevSignedVIP** — if true, UpdateService accepts developer-signed
(non-production) firmware. The setter is gated:
```java
if (!key.isDebug() || isDebugBuild()) { /* save */ }
// isDebugBuild() = Build.IS_DEBUGGABLE || !Build.TAGS.startsWith("release")
// production: ro.debuggable=0, ro.build.tags=release-keys → isDebugBuild()=false → not saveable
```
This is a catch-22: setting the flag needs a debug build; making a debug build
needs `ro.debuggable=1`, which needs root. (`GMSWUpdater.apk` also has
`changeDebugMode(true)`; `UpdateService.Tx13` returns success but Tx14 NPEs —
app-layer only, not confirmed to bypass signing at the UpdateService level.)

### IInstallRecovery (`gm.IRS.IIRS`) — not in service manager

Passed as a direct Binder reference inside UpdateService; **not registered**, so
not reachable via `service call`. Methods:

| Tx# | Method |
|-----|--------|
| 1 | `setNewManifestAvailable(String fileName)` — tells recovery to process a manifest (direct bootloader/kernel/recovery programming path) |
| 2 | `getRecoveryImagePartNumber(StringBuffer)` |
| 3 | `getKernelImagePartNumber(StringBuffer)` |
| 4 | `getABLPartNumber(StringBuffer)` |
| 5 | `getABLVersion(StringBuffer)` |

### Update History (Tx 3, live) — 10 entries, notable

- USB install from `/mnt/media_rw/4FE0-161D/857595955.mnf` → `SIHM22B-00383.01`
- OTA cache installs of SIHM22B-00499.02, .03, SIHM22B-00526
- OTA `GM Update N25-250552` (campaignId `pV7JR1D0EfCc7u7uCvix7Qcmp`) → Result=5
  (declined/failed)
- Latest: SIHM22B-00499.03 from `/update_cache/update/` → Result=0 (SUCCESS)

USB programming config: `mUSBProgrammingEnabled=true`,
`mSigningCertificateIssuer=CN=GPD, OU=GMNA GPD PRODUCTION, O=GENERAL MOTORS LLC`,
`mMaxOperationalProgFileSize=5000`, `mBackOfficeServerEnabled=true`.

---

## SWU State Machine

```
mIdleState → mDownloadAvailableState → mUpdateAvailableState → mSecureUnlockState
→ mProgrammingState → mPostProgrammingState → mUpdateCompleteState
```
Current device state: **IdleState**. **SecureUnlock** = a UDS SecurityAccess
seed-key challenge before ECU programming — see ProtoKey in
[`platform/security.md`](security.md#protokey-authentication) and the seed/key
tiers in [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md).

---

## Actual OTA Engine

**Correction to a prior assumption:** `data_wipe/85142410.bin` is a 589-byte
binary record table (magic `UT`), **not** an OTA-utility ELF, and **`gmext.*`
symbols do not exist anywhere** in the Y181 partitions (raw scan: SYSTEM 3.2 GB,
PRODUCT 2.7 GB, VENDOR 467 MB). The `gmext.*` extensions exist **only** as Edify
updater-script commands inside the package manifest (below), interpreted by the
recovery updater.

```
GMSWUpdater.apk (UI) + gm.update.* SDK (in APK dex)
  → HIDL: vendor.gm.swupdate@1.0.so
  → libpal_swupdate_ecu.so / libpal_swupdate_hostos.so
  → /vendor/bin/hw/gm_update_engine   (GM fork of AOSP A/B update_engine)
  → Integrity check: IECUInformation::verifyFCID() + libswupdate_fcid.so
```
(The update libraries are also listed in [`platform/networking.md`](networking.md#update-libraries).)
SELinux domain `gm_update_engine` carries `dontaudit gm_update_engine
gsi_metadata_file` — silently blocking GSI installs (see security.md GSI Blocker).

### GMSWUpdater.apk

`/system/app/GMSWUpdaterSrc/GMSWUpdater.apk` (46 MB, 2,047 decompiled Java
files). **Pure UI shell** — no signing verification, manifest parsing, or binary
execution. `UpdaterAppService` listens for `gm.update.action.CHECK_UPDATE_RESULT`
and fires on USB insert; `SDKManager.onReqUsbUpdate()` is an empty stub.
Debug-only Decline buttons gate on `Build.TAGS == "test-keys"`. The `gm.update.*`
SDK is in the APK dex (`UpdateManager`, `PackageDetails`, `Calibrations`,
`phone/PhoneManager`, `vdata/GMLANProxy`, etc.).

---

## Y181 Delivery Package Format & Signing

Package: **Y181 GAS Full Package**, Part# 86334732, EWO G3D7G, MY2022,
`DEV_REL` (development release).

**`delivery_manifest.csv` flags (all modules):** `Release Type=DEV_REL`,
`Bypass P/N & Module ID Check=TRUE`, `CVN=EMPTY`, Fill/Pad byte `0xFF`.

**Signing tiers:**

| Modules | Sign Type | Implication |
|---------|-----------|-------------|
| VIP_APP [1], SOC_HOSTOS [21], SOC_SYSTEM [22], SOC_VENDOR [26] | **TSS** | Requires GM GPD Production CA private key |
| all others (bootloaders, ACPIo, vbmeta, product, ETH_SWITCH, SXM, GPS, TUNER) | **NONE** | No TSS signing in package |

NONE-signed bootloaders: `SOC_ABL [72]` (Intel Automotive Bootloader),
`VIP_BOOT [71]` (Visteon IPC Bootloader), `SOC_BOOT [23]` (Android boot),
`SOC_VBMETA [56]`. The package-level manifest (`86331663.mnf`, module 92) and
signature (module 93) are themselves not TSS-signed. New modules vs. dumpsys:
Module 29 GPS (85121980.AB), Module 51 Digital Tuner (85155539.AB).

### Manifest file (`86331663.mnf`, module 92) — binary container, 3 sections

1. **Hash table:** per-module `module-ID + part-number (ASCII) + 32-byte SHA-256`
2. **Edify updater-script** (Android recovery dialect + GM extensions):
   `getprop("ro.product.device")=="gminfo37"`, `gmext.write_emmc_image`,
   `gmext.extract_logical_partition`, `gmext.update_ecu`, `gmext.switch_slot`,
   `gmext.update_dynamic_partition_config`. Target `SIHM22B-00499.03`, FCID
   `0x54f3`, `W231E-Y181.3.2`.
3. **JSON block:** dynamic-partition group config (`group_sys`: system
   3228360704, vendor 466915328, product 2700648448).

### Signature file (`86331665.smd`, module 93) — PEM-style ASCII-armored bundle

- X.509 cert: Subject `CN=GM Code Signature Server, OU=GM NA INFOTAINMENT,
  O=GM`; Issuer `CN=GPD, OU=GMNA GPD PRODUCTION, O=GENERAL MOTORS LLC`;
  **RSA-2048, sha256WithRSAEncryption**, EKU=Code Signing, validity 2014→2064.
- `-----BEGIN SHA256 MANIFEST-----`: base64 SHA-256 of the manifest.
- `-----BEGIN sha256WithRSAEncryption MANIFEST-----` sections: per-part
  RSA-SHA256 signatures (e.g. `-----END sha256WithRSAEncryption SW PN 85843750-----`).

The package-level signing cert (`CN=GPD, …`) gates what packages UpdateService
accepts — this is the **root gate** for flashing modified firmware. (This is the
same GPD Production CA documented in `platform/security.md` for AVB / VIP
validation.)

---

## USB Install Path & Flag Files

Two flag files read by `gm_update_engine` from the USB package root:

| Flag file | Function |
|-----------|----------|
| `gm_usb_ignore_battery` | bypass the battery-level check before install |
| `gm_usb_auto_install` | install automatically without user confirmation |

`data_wipe/` ships an empty `gm_usb_ignore_battery`. To trigger: insert a FAT32
drive with a valid `.mnf` manifest at root; `vold` auto-mounts to
`/mnt/media_rw/<UUID>/`; `UpdaterAppService` fires
`gm.update.action.CHECK_UPDATE_RESULT` immediately; with `gm_usb_auto_install`
present, install proceeds without a prompt. Confirmed: USB drive
`/mnt/media_rw/4FE0-161D/` with `857595955.mnf` (SIHM22B-00383.01) seen by
UpdateService. (Manifest filenames may carry a trailing DLS/format digit, e.g.
`863316635.mnf` for part `86331663.AA`.)

> All USB/OTA install paths still require a package signed by the GPD Production
> CA (private key not in any extracted artifact). `AllowDevSignedVIP` would relax
> this for VIP, but is unsettable on production (see above). This is consistent
> with the repo's standing Research Status: the signing barrier is the root gate.

---

## Cross-References

- [`platform/firmware_versions.md`](firmware_versions.md) — Y175/Y177/Y181 diff,
  VIP_APP IDs, build fingerprints, full firmware module inventory
- [`platform/security.md`](security.md) — signing chain, ProtoKey, SBI/EEPROM,
  GSI blocker, SELinux domains
- [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)
  — UDS SecurityAccess (SecureUnlock) channel
- [`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md)
  — full uid=2000 Binder access map and escalation gates
- Source: `enumeration/Y181/apr2026/raw/gm_update_service.txt` (dumpsys);
  Y181 firmware package analysis
