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

## Y181B recovery export evidence (2026-11-12)

Source: both [recovery USB archives](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12).
Their entire `update/` trees are byte-identical. Exported `UpdateDB` has
15 `UpdateResults` rows, no `Packages` rows and `ReflashCounter=11`.
The stored `ProgrammingStatus` names manifest `86405527`, version
`SIHM22B-00499.03`, Status=1, Percentage=99 and ErrorCode=0. These are
persisted records, not a fresh installation result or an active-package query.
The history contains multiple versions/campaigns and must not be attributed
entirely to the deliberate homescreen-removal experiment. Retained manifests
and signature metadata do not constitute a complete restorable firmware image.

**Decoded 2026-11-12 (direct read of the exported `UpdateDB`; epochs converted to UTC):** the 15
`UpdateResults` rows have `InstallDate` from 2025-05-10 (manifests `85759595`, `SIHM22B-00383.01`)
through 2026-09-28; manifest `86405527` (`SIHM22B-00499.03`) appears twice — id 24 with InstallDate 2026-08-25
15:09 UTC and id 29 with InstallDate 2026-09-29 01:34 UTC (= 2026-09-28 17:34 local, UTC-8) — and two OTA-campaign rows (`GM Update N25-250552`, `Important Update GM 661.10`) are dated
2026-09-28 (14:52 and 16:22 UTC). `ProgrammingStatus` (2026-09-28 17:25:28 local) and the
`ReflashCounter` 10 -> 11 write at the same second are in the gmlogger system log
(`UpdateService-PersistStore`); the same log shows the active Android slot going 1 -> 0 across the
recovery install at 17:27-17:33. `LastCheckUpdateTime` = 2026-11-07 23:09 UTC. `slot_switched` = `N`
in both exports, i.e. no slot switch pending at export. Module inventory: 18 modules
(`moduleinfo`, see [`firmware_versions.md`](firmware_versions.md#y181b-runtimeexport-identity-2026-11-12)).
Corrected 2026-11-12: an earlier version of this note said only the OTA rows and the ProgrammingStatus were dated
2026-09-28 and the USB manifest row 2026-08-25; the raw `UpdateDB` also holds the second USB `86405527` row (id 29)
dated 2026-09-28 local, so "USB `00499.03` + 2 OTAs on 2026-09-28" is supported (the 08-25 row is an earlier USB install).

Recovery wipe reasons retained in the numbered `recovery/last_log` series (directly read, counter
order 47 -> 55): 47 and 48 `--wipe_data --reason=bcm_replacement` (from `/update_cache/recovery/command`);
49 `--wipe_data --reason=com.gm.domain.server.delayed,2026-11-07T12:45:35Z` (delayed GM server wipe;
args from the boot message; recovery's own wall-clock reads Sat Nov 7 2026 21:45, which is not reconciled
with the reason's 12:45Z stamp, and is the only entry with a plausible RTC); 50
`--wipe_data --reason=MasterClearConfirm,2026-11-10T15:54:27Z` (factory MasterClear, boot-message args;
the log line `unrecognized option` for the comma-suffixed reason is printed, outcome of the wipe itself
not traced here); 51-53 no arguments; 54 and 55
`--show_return_to_dealer` (see the GHS recovery analysis). Recovery's own clock reads 2010/2011
outside entry 49, so only the reason strings carry the dates.

The first archive preserves a concrete multi-reboot update sequence in
`update_cache/recovery/last_log.10`, `.9` and `.8`:

1. `.10`, lines 97–102: production certificate selected, `Security Check Passed.`,
   and build/manifest version comparison. `version check disabled` at line 113
   is a separate software comparison; it does not establish disabled signing
   or disabled GHS/AVB antirollback enforcement.
2. `.10`, lines 114–167: Android boot/vbmeta/acpio/bootloader writes and the
   VIP bootloader update request. `PAL_SWU_ERROR_VIP_BOOT_REQUIRED` is followed
   by `script is pending for VIP reset` and an IOC/SoC boot-target request.
   Within this successful retained sequence it is a reset checkpoint, not
   evidence by itself of a terminal flashing failure.
3. `.9`, lines 383–396: SoC boot update succeeds, Android next slot becomes 0,
   `slot_switched` is written `Y`, and reboot is requested to take effect.
4. `.8`, lines 403–442: SXM serial-read errors are followed by module-28
   success, `Update complete`, and successful calibration-service installation.
   Diagnose completion from the surrounding state/result, not an isolated
   error-labelled line.

The second archive's recovery rotations displace these older `.8`–`.10`
files, while retaining the cumulative log. Keep both archive fingerprints
when citing the numbered histories. The native updater is distinct from the
normal-AAOS service: the latter's current `ServiceLog_0.log` records OTA idle
state and production certificate configuration, not a new OS flash in this test.

`recovery/last_redbend_log` independently records a dealer-package dummy
`vbmeta_a` operation: `UpdateDummy`, opening the partition **for reading**,
and completion with Error 0. `Security: none` describes this Redbend agent
configuration; it does not negate the surrounding GM package verifier or AVB.
This supports the [dealer wipe package analysis](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#421-dealer-data-wipe-package-and-formatter-verified-2026-11-12),
not a claim that this dummy stage installed a replacement vbmeta image.

## UpdateService Binder Interface

**Y175 live build, 2026-10-30:** Read-only Binder calls from UID 1000
`system_app` returned empty `getAllPackages()` and null `getActivePackage()`;
this establishes the service's reported state at the time, not the absence of
all files in update storage. The installed `DelayedWKSApp.apk` was read and
decompiled for this build. Its `USBNotifier` considers `.calovride` files only
when `ro.build.type` is not `user`; the live radio reports `user`. It sends
container type 2 only on that development-build branch. Its `UpdatePackage`
also confirms that type 2 returns true from `verify()` without the normal
manifest checks, but the observed production USB path does not select it.
This is build-specific static analysis, not an installation test. A different
locally decompiled APK has a different hash and a notifier that passes only
type 0; its provenance must be established before attributing it to Y181.
The same UID 1000 shell's `test -w` succeeded for `/update_cache/update` and
failed for `/update_cache/calibrations` (a symlink to the calibration overrides
directory). This establishes an access check, not a successful file write or a
way around package verification. Whether update-cache contents can influence
staging without an already authorized package remains untested.

**Y175 cache trace, 2026-10-30:** The UID 1000 `system_app` shell created and
removed an empty temporary file in `/update_cache/update`, confirming real
write access; the update database also passed `test -w` but was not modified.
The installed app's `PersistStore.loadPackages()` reconstructs package records
from its SQLite database, and `UpdateSource.init()` loads those records into
memory. The normal `InstallRunner.install()` calls `populateInstallers(...,
false)`, which adds a verifier for manifest packages; the package verifier
checks the signature, manifest, license when required, and module parts.
The USB notifier searches for manifests upon a volume-mount event; these
findings do not establish that dropping an arbitrary file in the update cache
causes discovery or permits an unsigned payload to be installed. Other state
machine and native-engine paths have not been ruled out. Full APK decompilation
reported 13 errors, so conclusions are limited to the inspected classes.

**Y175 verifier probe, 2026-10-30:** A standalone harness invoked the installed
update app's `Signature.verify(false)` against an existing Y175 signature file;
the original signing certificate passed, while a replacement self-signed test
certificate failed with `Err_PublicSigningCert`. This tests certificate trust,
not installation or full package acceptance. The manifest verifier rejected even
the original control because its native `IECUUpdate` lookup was denied to the
`system_app` domain; the modified manifest result is therefore inconclusive.

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
| 30 | `getReflashAttempts()` | **9** (June 2026 read; the 2026-11-12 `/cache` export has `ReflashCounter=11`, 10 -> 11 on 2026-09-28) |

`install()` (Tx11) deserializes a `PackageDetails` Parcelable with no permission
gate, then NPEs in the internal install manager — i.e. the execution path is
reached but no caller-permission check guards it.

> **[U] No network→install path (resolved 2026-09).** The missing permission
> check on `install()` is local-Binder-reachable only — it is not itself a
> network attack surface, since Binder isn't reachable off-device. The
> network-adjacent candidate, FSA `RemoteReflash` (port 9012, serviceId 1025),
> has Android acting as a **client** dialing `.102` (telematics), not a
> server; inbound events from `.102` dispatch to
> `IRemoteReflashServiceEvents`, which is **unsubscribed system-wide** —
> verified across 6 decompiled apps including `CriticalWKSApp`/`GMTCPS`. So on
> this build there is no reachable path from an unauthenticated Ethernet peer
> to triggering an install. `.102` is pinned by static IP config with no TLS
> pinning; whether a rogue vlan5 node can spoof `.102` at L2/L3 to feed a
> subscribed listener (should one exist on another build/config) is an open
> bench item. See
> [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md#update--rollback--influence-verdicts-network-peer-over-ethernet-resolved-2026-09).

> **[U] INSTALLRUNNER trace (2026-09) — closes the code-execution question for the local IPC path.**
> Refines (does not contradict) the "no network→install path" verdict above. `IUpdateService.install()`
> (Tx11) has no permission check, but SELinux `find` on `gm_domain_service` (the coarse label hosting
> UpdateService/DelayedService/CriticalService) is granted only to **platform_app, priv_app,
> carservice_app** — **not untrusted_app, not shell** — so this is a priv_app/platform_app/carservice_app
> → system escalation, not an ordinary-3P-app one. Traced end-to-end
> (`com/gm/server/update/installer/InstallRunner.java`, `UpdatePackage`/`Signature`/`Package` in
> `DelayedWKSApp`):
> - The caller's `PackageDetails` IPC argument is **never consumed** by the install pipeline —
>   `retrievePackageFromMessage()` only accepts `msg.obj instanceof Package` (never true for a raw
>   IPC-supplied `PackageDetails`), so the state machine always falls back to its own internally-tracked,
>   legitimately-downloaded `Package` object. `InstallRunner.install(pkg)` uses that trusted internal
>   object, not the caller's argument.
> - **Verdict: exploiting the missing permission check achieves forced/premature install-triggering of
>   whatever update the vehicle already has legitimately staged — a real bug (bypasses user-consent
>   timing/state gating, a DoS/nuisance vector) — it does NOT allow substituting attacker-controlled image
>   content.** Downgrade from "critical RCE-adjacent" to "HIGH: unauthorized-trigger / consent-bypass only."
> - **Signature.verify() mechanism (normal manifest path, containerType 0):**
>   `InstallRunner.populateInstallers()` (`InstallRunner.java:577-578`, gated `if (!verified)`) runs a
>   `Verifier` installer before `RecoveryModeInstaller` — unconditional in effect on the real `install()`
>   path because its only caller there (`InstallRunner.install()`, `InstallRunner.java:672-676`) hardcodes
>   `verified=false`; a separate post-download-verification call site passes `verified=true` and is not the
>   traced path. `Verifier.run()` calls `UpdatePackage.verify()`
>   (`UpdatePackage.java:179-217`): real X.509 chain check — extracts the embedded signing cert, loads a
>   trust anchor from `/system/etc/security/production/signingCA.cer` (or `development/signingCA.cer` only
>   if the manifest itself claims `isDevelopmentSecurity()=true`), calls
>   `untrusted.verify(trusted.getPublicKey())` (`Signature.java:116-142`), then `Manifest.verify()`, then
>   license/DRM checks, then per-module `ModulePart.verify()`. Any failure aborts before any apply step.
>   This is a second independent layer alongside the native `gm_update_engine` RSA-2048 whole-manifest
>   check documented above. `UpdatePackage.parse(path, type)` — the only factory used by the normal
>   OTA/USB manifest flow — hard-rejects any `type != 0` (`UpdatePackage.java:250-251`): an attacker cannot
>   get a manifest-type package with forged content through this factory either; it must be a real signed
>   manifest folder already on disk.
> - **Open item, flagged not exploited: `DevCaloverrideInstaller` (containerType=2,
>   CONTAINER_TYPE_DEV_CALIBRATION_OVERRIDE).** `UpdatePackage.verify()` returns `true`
>   **unconditionally** for this type (`UpdatePackage.java:214-215`), and `populateInstallers()` never adds a
>   `Verifier` for it (only Delay + `DevCaloverrideInstaller`, `InstallRunner.java:593-596`).
>   `DevCaloverrideInstaller.copy()` copies whatever files are listed in `getDevCaloverrides()` straight
>   into `/update_cache/calibrations` with **zero signature/hash check**, then reboots to recovery. But
>   the identified factory for such a package (`UpdatePackage.parseCaloverride`,
>   `UpdatePackage.java:310-329`, itself validating nothing beyond `File.exists()`) was identified
>   at `USBUpdateSource$1.onUSBMounted` (`USBUpdateSource.java:58`) — triggered by physical USB-media
>   mount detection, not reachable via `IUpdateService.install()` or any other IPC method traced. **This is
>   a remaining update-path research thread** — it requires tracing
>   current package-registration and native mounted-media handling. The fresh
>   2026-11-15 Y175 trace below confirms the non-user discovery gate and a
>   protected mount broadcast; spoofing a volume is not an established method.
>   Other builds and alternate entry points still require independent verification.
> - Downgrade/rollback: not directly evaluated via this trace (PNVersionVerifier compares against the
>   manifest's own declared expected versions, protected by the same signature chain) — state as
>   inferred-absence, not proven-absence, alongside the hardware-enforced GHS rollback counter below.
> - **Inspected normal-install verdict:** no arbitrary-content substitution or
>   code-as-system path was demonstrated through that IPC call. The unguarded `install()` Binder call is a real bug (unauthorized-trigger,
>   consent-bypass, DoS) but not a payload-substitution vector. Full ranked writeup:
>   [`../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).

### Current Y175 development calibration import route (2026-11-15)

**A privileged file mover exists, but a working production-shell invocation
has not been established.** Fresh class analysis used the current cleanroom
DelayedWKSApp, previously byte-matched to the radio, SHA-256
`5916ad9f7d40d2683e4dac49b7cc5086104dd27042c7fc32716fc3094288e241`.
The older cached APK hashes `8a4fd60d…78cfb9`; its source must not be silently
attributed to this build. Current classes independently confirm the non-user
discovery gate described in the earlier Y175 audit.

| Stage | Current implementation | Gate / evidence limit |
|---|---|---|
| Mount notification | USBNotifier dynamically registers VOLUME_STATE_CHANGED and calls `IECUUpdate.onUsbMounted(origPath,path)`. | Native call precedes the Java gate, but copies USB metadata/override files to update staging, not the calibration watch directory. |
| Calibration discovery | `mDevelopmentBuild = !"user".equals(ro.build.type)`; when no normal manifest is found, `.calovride` discovery is attempted only on that development branch. | The radio reports user; normal production discovery does not select type2. |
| Package registration | USBUpdateSource calls `Package.parseCaloverride(files,2)`, inserts an accepted package into its internal campaign map and sends message206 if vehicle-off policy permits. | A registered package is required; arbitrary caller PackageDetails are not proven to create one. |
| Type2 handling | parseCaloverride collects existing files; type2 verification returns true; installation gets Delay + DevCaloverrideInstaller. | The shown routine does not authenticate XML; this is not proof of an externally reachable bypass. |
| Protected placement | DevCaloverrideInstaller requires `/update_cache/calibrations` and copies listed files there through UpdateFiles.copyFileToDir. | Legitimate updater path, not shell filesystem permission. |
| Activation | After successful copying it calls `reboot2recovery(false,10)`. | Recovery-mediated persistent calibration import, not an immediate runtime theme switch. |

The build-type gate is in discovery, not the shown installer body. Another
way to register a type2 package is therefore a precise research question;
its existence is not established by the installer's lack of an additional
build check. The APK manifest uses shared UID `android.uid.system`; that
does not grant the calling shell its identity or imply all UID1000 contexts
can write calibration data. The earlier system_app access checks remain valid.

The current UpdateServiceImplGB install wrapper forwards PackageDetails to
its selected source without a visible Java caller check. The existing audit
traced normal install IPC back to an internally tracked Package rather than
caller-supplied file contents. That is evidence for the inspected path, not
an exhaustive proof about every current state-machine/native entry. SELinux
service-discovery permissions are another gate. No separately declared
exported calibration-import component was identified in the current manifest.
VOLUME_STATE_CHANGED is a protected framework broadcast, so shell-spoofing
that action is not an established import method and would not remove the
non-user discovery check.

**Native mount handling stages files; it does not activate calibration overrides.**
In current Y175 `gm_update_engine`, `ECUUpdate.onUsbMounted` (`0x55670`)
dispatches through DaemonState vtable+`0x70` to `copyCoreFile` (`0x778D0`).
It copies `.mnf`, `.smd`, `.lic`, `gm_usb_auto_install`,
`gm_usb_ignore_battery` and `.calovride` from USB
`/mnt/media_rw/<FS_UUID>` into UPDATESTAGING
(`/update_cache/update/<FS_UUID>`). That destination is distinct from
`/update_cache/calibrations`; staging an override does not bypass Java's
production discovery gate or establish application of its contents.

A separate HIDL `ECUUpdate.copyFile` (`0x561C0`) dispatches through vtable+`0x80`
to `DaemonState.copyFile` (`0x75870`), a raw `rb`/`wb` file copier. This is a
concrete privileged primitive, but earlier service lookup was denied even
from UID1000 system_app. The later UID2000 shell lookup was also denied by
SELinux, as recorded below; an alternative authorized client/proxy remains
unproven. Native SHA-256:
`0f47923bf545394b9f1cf1d229061158af2c20c4038aa33e8c77e76ef6181f73`.

**Live USB follow-up, 2026-11-15:** the connected FAT32 public volume was
mounted for AAOS user10. Shell direct paths under `/mnt/media_rw` and
`/mnt/user/10` returned `Permission denied`; ExternalStorageProvider required
an ACTION_OPEN_DOCUMENT grant. This did **not** mean ADB could not write USB.
The shell's MediaStore permissions allowed `content insert/write/read`
against `content://media/<USB_VOLUME>/file` with `--user10` (command syntax:
`--user 10`). A root-level 37-byte text probe read back byte-exactly and was
deleted. Insert itself printed no URI; a display-name query recovered its
row ID for subsequent write/read/delete.

The previously prepared single-GMBrand GMC XML was then written at the USB
root as `a11_gmbrand_gmc_single.calovride`, 308 bytes, with byte-exact readback;
SHA-256 `5485498bcc4fdf849b3c81b57b58d66a657e84c5930cfe2bb6851e30da58befd`.
No indexed existing `.mnf` or `.calovride` file was found before insertion;
that query is not an inventory of unindexed files. A real `sm unmount` /
`sm mount` cycle succeeded. Logcat showed volume state2,
`UpdateService-USBNotifier: onUsbMounted: 0` and manifest search. No
calibration-discovery/type 2 install event was observed. Exact protected-cache
file placement was not independently read back, so callback success is not
proof that this particular XML was copied or applied. Production build type
remained `user`; no calibration application or reboot was demonstrated.
That initial descriptive USB filename was subsequently superseded by the
eight-character-basename experiment below. The earlier `/data/local/tmp`
copy remains inactive.

**Native filename selection and live parser proof, 2026-11-15:**
searchCopyFile (`0x760a0`, binary-relative) does not accept arbitrary
descriptive names for extension-based metadata. For patterns beginning with
`.` it compares the suffix and requires the extension's position to equal8;
assembly at `0x76acd` performs `cmp rax,8`. This requires an eight-character
basename. The native binary SHA above was rechecked. Ghidra's default import
base was `0x100000`, so its addresses for this trace are offset accordingly.
No numeric-only requirement was established: the live marker
`a11probe.mnf` has an alphanumeric basename and was accepted.

| Live USB input | Observed result |
|---|---|
| Long descriptive `.mnf` marker | Byte-exact USB readback and mount callback0, but no manifest discovery. |
| `a11probe.mnf`, deliberately non-installable text marker | Native staging proved by Java finding `/update_cache/update/<USB_UUID>/a11probe.mnf`; USBUpdateSource received container_type0; manifest parser threw EOFException and returnednull. No package registered. |
| Same308-byte XML renamed `a11brand.calovride` | Byte-exact USB readback. It now meets the native filename selector, but no type2 discovery/install event or application was demonstrated on this `user` build. Exact protected XML staging remains unverified. |
| `gm_usb_auto_install` alongside the valid-basename XML, no manifest | Callback0; Binder package list stayed empty and active package stayednull. Marker presence did not bypass production calibration discovery in this test. |

Both manifest markers and the auto-install marker were removed after their
tests. A clean remount stopped rediscovering the manifest; only
`a11brand.calovride` remains on USB, replacing the earlier descriptive-name
XML. The short manifest contained no module descriptor or payload. No
calibration clear, package installation or reboot was performed. The
USBUpdateSource pending-results gate exists statically, but did not block the
short-manifest parser experiment.

**Current shell access boundary:** read-only Binder transactions1/2 on
`com.gm.server.update.UpdateService` succeeded as UID2000, returning an empty
package list/null active package. A standalone Java HIDL lookup for
IECUUpdate/default failed with `java.util.NoSuchElementException: null`;
live AVC confirmed `{ find }` denied from `u:r:shell:s0` to
`gm_update_engine_hwservice`, permissive0. Thus the separate raw copier and
file-status methods were not invoked. Direct shell `ls`/`sha256sum` of the
protected staged XML and directory metadata returned Permission denied.
Temporary native logging properties were restored after observation.

The remaining static targets are HIDL dispatch/caller checks and SELinux
allowed clients, references creating/restoring type2 packages, and safe
ABFT0475 module/slot/signature behavior. The [ABFT follow-up](../diagnostics/diagnosticsd_routines_and_recovery.md#abft-handler-and-validation-only-follow-up-2026-11-15)
recovered its install-plan JSON schema; incomplete validation-only starts
returned NRC31 at level05/NRC33 at level09, without proving parser entry.
No complete plan or transfer was submitted. The earlier static pass performed no live mutation; the subsequent
USB discovery experiment above supersedes that historical scope statement.
No direct HIDL copier invocation or reboot was performed. USB testing is
authorized beyond discovery; calibration clearing remains forbidden.

An original [2023 calibration-command gist](https://gist.github.com/NativeDevlopment/fb3683c94858ef2aee580aa1ac93e1a0)
uses `.calovride` and an older cache path, but starts from root/remount and
identifies neither an A11 build nor successful output. It does not solve the
production UID2000 placement problem. GM's [USB programming guidance, page10](https://gm-techlink.com/wp-content/uploads/2021/05/GM_TechLink_08_Mid-April_2021.pdf)
distinguishes service USB programming from calibration-only programming;
it does not document unsigned single-value import. The
[calibration-application patent](https://patents.google.com/patent/US9495812B2/en)
is architectural evidence, not proof of an exposed A11 interface.

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

- USB install from `/mnt/media_rw/4FE0-161D/85759595.mnf` → `SIHM22B-00383.01` (corrected 2026-11-12 from `857595955.mnf`; both `enumeration/Y181/apr2026/raw/gm_update_service.txt:33` and the `/cache` `UpdateDB` read `85759595.mnf`)
- OTA cache installs of SIHM22B-00499.02, .03, SIHM22B-00526
- OTA `GM Update N25-250552` (campaignId `pV7JR1D0EfCc7u7uCvix7Qcmp`) → Result=5
  (**meaning undefined** — corrected 2026-11-12: the only `UpdateResults.Result` value any log names is `0` = `RESULT_SUCCESS`;
  the `/cache` export also has `Result` 1, 2 and 5 rows with no defining string, so "declined/failed" is a guess)
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
[MEC/ADB evidence](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration) and the seed/key
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
(The update libraries are also listed in [`ethernet_networking.md`](ethernet_networking.md).)
SELinux domain `gm_update_engine` carries `dontaudit gm_update_engine gsi_metadata_file`
in `vendor_sepolicy.cil`, but this does **not** block GSI installs — `dontaudit` only
suppresses audit logging and does not deny, and it targets the OTA engine, not the DSU
path. GSI/DSU is disabled instead by removal of the `com.android.dynsystem` app plus
locked verified boot. See [`platform/boot_chain.md`](boot_chain.md#gsidsu-status).

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
`VIP_BOOT [71]` (VIP Renesas RH850 bootloader; confirmed: `MASTER_REFERENCE.md` — "RH850 bootloader", not the Visteon cluster IPC), `SOC_BOOT [23]` (Android boot),
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

**(2026-09-10) Verified against the shipped `gm_update_engine` binary** (the
component that actually owns signature verification — `libpal_swupdate_ecu.so`,
the `gmext.update_ecu` HAL, does **no** crypto at all; it is pure part-info/IPC
transport). Findings:
- **Module `Sign Type: NONE` (e.g. `ETH_SWITCH`, module 52) is still bound by
  the root gate**, not informational-only: the RSA-2048 signature covers the
  whole manifest, including the per-module SHA-256 hash table for every
  module regardless of Sign Type ("Hash verify manifest OK/Failed",
  `DownloadOperationHashMismatch`/`ManifestSignatureMismatch` in
  `SignatureVerifier.cpp`/`Signature.cpp`). `TSS` adds an *additional* per-part
  RSA block on top; `NONE` modules lack that extra layer but their hash is
  still checked against the signed manifest before any write proceeds. No code
  path skips this regardless of Sign Type, and `Bypass P/N & Module ID Check`
  (delivery_manifest.csv) is a *different* control (relaxes part-number/module-ID
  matching only, not signature verification).
- **The verifier is dual-anchor by design, distinct from the app-layer
  `AllowDevSignedVIP`.** The native cert-loader has a runtime branch selecting
  `production/signingCA.cer` vs `development/signingCA.cer`. It is inert on a
  production image only because `development/signingCA.cer` is not shipped
  (`fopen` → NULL → "Update CERT is required" → verify fails → install aborts):
  it **fails closed**, not because the code is hardcoded to a single anchor.
  Correction to the framing above: describe this as "production-only because
  the dev CA file is absent," not "the code only trusts one anchor."

### [U] Rollback protection — hardware-enforced, not network-influenceable

GHS keeps its **own** rollback counter in the misc partition, independent of
AVB's rollback index. Empirically, a Y181→Y177 downgrade writes the A/B slots
successfully but GHS rejects the older image at boot and falls back to the
current slot. A manifest's "version check disabled" flag (see
`delivery_manifest.csv`'s per-module flags above) only affects the **write**
phase — it does not touch GHS's independent boot-time rollback check. No
network-reachable surface documented here can influence this counter.

### [U] FSA `ProgrammingMaster` (9011) is dead code

Cross-ref [`fsa_protocol.md`](fsa_protocol.md#p-programmingmaster-9011-is-dead-code):
the FSA catalog's `ProgrammingMaster` service (serviceId 1006, port 9011) is
compiled into the CSM image but never instantiated — a live scan shows only
9002/9010/9016 listening. This is consistent with the Global-B demotion of
infotainment from Programming Master to HMI-only role documented in
[`ota_programming_roles.md`](ota_programming_roles.md).

### [U] `DisplaysCoordination` writes — documented, not live-fired

The IPC-hosted `DisplaysCoordination` write methods (`resetOilLife`,
`setIPCLayout`, `postTPMS_Relearn`, etc. — see
[`fsa_protocol.md`](fsa_protocol.md#displayscoordination-ipc-serviceid-2027-port-9020--vehicle-telemetry))
are a documented FSA attack surface but were **not** live-fired this session:
the service is hosted on Visteon IPC `.106`, which was unreachable off-vehicle
on this bench (SYN timeout, no RST).

---

### Y175 full USB update bench observation — 2026-11-17

The authorized follow-up to the [SXM CAN rejection](ota_programming_roles.md#sxm-stock-file-can-attempt--2026-11-17)
uses the normal full Y175 USB package, not an SXM-only transfer. The removable
volume's17 required package files (15 component files,85759595.mnf and85759597.smd)
were read back and matched the local Y175 source by SHA-256, total3,118,500,573
bytes. An initial check during copying found partial/zero-length files; the
final completed-copy check matched all17. This verifies copy integrity, not
independent package authenticity.

Pre-update live Android build: Y175.5.2/SIHM22B-383.1, active slotB,
boot_completed1. ADB was available; the radio clock was corrected from the Mac
before monitoring. CAN F180/F181/F182 baselines were obtained; SXM remained
84999468/AC, VIP_APP85759599/CJ, HostOS85098662/BM. T1 connection returned
`[Errno 65] No route to host` despite an active Mac VLAN interface, the owner
confirming the cable attached, and ADB confirming the radio diagnostic address
present. Thus no combined T1/CAN SXM transfer was performed at this checkpoint.

RX-only115200-baud UART, all Android logcat buffers with reconnect detection,
and passive CAN receive capture alongside the32-frame bench harness were
prepared. Raw observations remain in bounded memory buffers, not durable raw
logs. UART bytes and CAN frames were arriving; the replacement CAN capture
reported zero error frames before USB insertion. Android logcat is unavailable
while ADB is disconnected; UART/CAN alone do not provide all recovery logs.

USB insertion discovered manifest85759595 and SXM module28/part84999468;
package verification reported STATUS_CODE_SUCCESS. The initial user-visible
Park prompt did not identify the backend blocker: the service dump showed
VehicleParked=true, ShiftParked=true, RemoteReflashPowerReadiness=0.0, and its
condition check returned STATUS_CODE_INSUFFICIENT_BATTERY. No gear frame was
changed.

The empty `gm_usb_ignore_battery` marker was created at the USB root using
shell-authorized MediaStore insert/write operations. A software unmount/mount
triggered rediscovery: mIgnoreBattery=true, mAutoInstall=false,
isBatterySufficient ignorebat=true, and checkCondition STATUS_CODE_SUCCESS.
This closes the earlier uncertainty about this marker's battery-gate effect on
this build. It does not remove signature checks or prove installation success.
The marker remains on the update USB; automatic installation was not enabled.

After the owner accepted, InitInstallState displayed a vehicle-on prerequisite.
The service reported SystemPowerMode=OFF although the separate lifecycle state
was STATE_PROPULSION. Repeating CAN284/DLC6 payload `00 00 00 00 10 00` alongside
the32-frame harness changed SystemPowerMode toRUN, lifecycle toSTATE_RUN, and
logged `handlePowerModeMessage RUN available? true`, `PowerMode: 4 is valid`,
and VehicleOffStateChanged=false. This is raw authenticated-power candidate2
in zero-based byte4 bits3–5, validity bit2 clear. Park remained true. No20D
remote-programming-bit override was sent for this USB update.

The owner then pressed Install now. The native-facing updater reported
startInstall ret=true, ProgrammingType15, manifest85759595 / SIHM22B-00383.01,
Status3, initial Percentage1 and ErrorCode0. Progress notifications subsequently
advanced through15% with error=null while UpdateFile verified component-file
digests. UART reported `st=RemoteReflashProgrammingActive`. ADB was still
connected at this checkpoint; recovery boot and SXM programming/completion
were not yet observed. A brief UART receiver replacement occurred before
these detailed state lines; this is not a gap-free raw capture. One observed
UART `HDLC: CRC Failed` line is not an updater failure verdict. CAN error-frame
count remained zero in the replacement capture.

The normal-AAOS stage then advanced through27%. RecoveryModeInstaller emitted
`Reboot To Recovery`, selecting85759595.mnf and current versionSIHM22B-00383.01;
it reported the package contains GHS and the pre-recovery active slot is1/B.
ADB disconnected during Android shutdown. The owner observed display-off/on
transitions and a separate recovery progress bar restarting at0 then advancing
through3,18 and22%. Those percentages are visual observations, not CAN-decoded
module progress. No factory-reset routine was sent for this experiment.

UART reset its timestamps, emitted evRemoteReflashProgrammingBegin,
SystemState=RemoteVehicleProgramming(0x10), and continued
RemoteReflashProgrammingActive. CAN error frames accumulated across the reset
interval to445 and then remained unchanged while RX traffic continued. The
capture does not classify those error frames as a programming failure; no
update-completion verdict was available. ADB remained absent in recovery,
so the normal-AAOS log stream does not contain recovery's per-module write log.

**Completed full-package result:** recovery UI advanced to97%, rebooted, and
AAOS displayed update success. The generated recovery script explicitly
scheduled VIP_BOOT71/85056831, VIP_APP1/85759599, HOSTOS21/85098662 and
SXM28/84999468, among the other package components. This records scheduled
operations, not per-module write-completion evidence.

The success UI requested vehicle Off, driver-door open/close and a two-minute
wait. CAN284 was set toall-zero authenticated-Off, captured529 byte1 bit7 was
cleared, and4DA byte7 bit0 was toggled0→1→0. UART confirmed PowerModeOff,
DriverDoorOpen, HmiInactive/Requesting Shutdown and DriverDoorClosed; later
Sleep and Shutdown were observed. RUN was restored only after the full120-second
interval following door-close. This was a simulated ignition/door sequence,
not a physical supply interruption; no explicit SoC power-level0 observation
was obtained here. The owner reported the finalization prompt persisted.

At the owner's request, CAN526 byte5 bit7 was held for11 seconds and released.
UART confirmed evResetRequestCSM, reset timestamps, HmiInit, HMIReady andRun.
The owner then confirmed the successful-update screen and accessible home
screen. ADB required manual off/on toggling; after reconnect the Mac clock
was reapplied as needed. Read-only verification returned:

| Check | Result |
|---|---|
| Android build | Y175.5.2 / SIHM22B-383.1 |
| Active slot | A, changed from pre-updateB |
| sys.boot_completed | 1 |
| Stored update manifest/version | 85759595 / SIHM22B-00383.01 |
| Stored Status / Percentage / ErrorCode | 1 / 99 / 0 |
| ReflashCounter | 10; no matching pre-update counter measurement for a delta |
| F180/F181/F182 | Expected Y175 identities unchanged, including SXM84999468/AC |
| F0F0 | All14 calibration slots status00 |
| F0F1/F0F2 | 0000 / 0000 |

Direct reading of the per-module recovery log failed with
`cat: /cache/recovery/last_log: Permission denied`. No USB volume was mounted
on the radio or Mac at final cleanup, so no USB-side log was read and the
created `gm_usb_ignore_battery` marker could not be removed; it remains on the
update drive. CAN RUN replay was retained. Raw observations were not exported.

This establishes a successful **full USB update with CAN-supplied bench
conditions**, including a B→A slot change and clean post-update calibration
status. It does not establish a T1/CAN-only transfer or an SXM-only update.
The unchanged SXM identity and scheduled update_ecu call do not distinguish
rewriting its existing version from skipping an unchanged component; a
per-module recovery completion/skip record remains unavailable.

## USB Install Path & Flag Files

**Evidence clarified 2026-11-12:** normal-AAOS `gm_update_engine` searches for
and copies these files from the USB package root:

| Flag file | Prior interpretation | Current verification limit |
|---|---|---|
| `gm_usb_ignore_battery` | Suppress battery-level check | Y175 bench2026-11-17: marker discovery changed mIgnoreBattery totrue and the condition result from INSUFFICIENT_BATTERY toSUCCESS; package signature checks still ran. See the full USB observation above. |
| `gm_usb_auto_install` | Install without confirmation | Discovery/copy is established; the complete no-prompt decision path was not traced here. |

A mounted USB package and `gm.update.action.CHECK_UPDATE_RESULT` have been
observed by the normal updater. That observation alone does not establish
automatic installation or that an unsigned package is accepted.
Manifest filenames may carry a trailing format digit, e.g.
`863316635.mnf` for part `86331663.AA`. [Qualified 2026-11-12: unsupported by the raw data — every manifest name in the 2026-11-12 `/cache` export, `UpdateDB` and recovery logs is the plain 8-digit form (`86331663.mnf`, `86405527.mnf`, `85759595.mnf`); no digit-suffixed name was found.]

These normal-AAOS flags are separate from recovery's two encoded markers,
its internal argument file, and fastbootd entry.
[Recovery scanner, log capture and options](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#4-trigger-files-and-reboot-mechanisms).

The existing signature-chain analysis remains applicable: package/module
acceptance is a separate gate. Neither a USB flag nor the dealer package's
`DummyPackage` field establishes a signature bypass.

### Dealer Data Wipe package (static verification 2026-11-12)

The package script, fingerprints, Red Bend/vbmeta limits, formatter disassembly
and package-acceptance boundary are maintained in
[the consolidated source §4.2.1](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#421-dealer-data-wipe-package-and-formatter-verified-2026-11-12).
This document owns the normal-AAOS update stack and Binder interface.


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
