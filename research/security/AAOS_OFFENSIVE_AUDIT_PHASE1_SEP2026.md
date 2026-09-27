# AAOS Offensive Audit — Phase 1 (Sep 2026)

**Device:** GM Info 3.7 (gminfo37), Y181
**Method:** Static reverse engineering of decompiled Y181 system APKs (`DelayedWKSApp`,
`GMAuthTokenService`, `GMSWUpdater`, `GMTCPS`, `ClusterService`/`com.gm.cluster`, the shared FSA
service library) plus extracted native binaries (`vhalgm`, `diagnosticsd`, `gm_protokey`).
**Scope note: read-only this phase — no live exploitation was performed.** Findings below are
proven from decompiled source/binary evidence and confirmed manifest/`dumpsys` state; anything
still requiring a live PoC is marked explicitly.
**Emulator-artifact exclusion:** the hybrid AAOS emulator runs root-adb / `ro.secure=0` /
`ro.debuggable=1` as a deliberate RE convenience — none of that applies to the real radio's
shell/untrusted_app SELinux domains. The PRIVESC findings below do **not** depend on those
emulator artifacts: they hold against the shipped `product_sepolicy.cil` under SELinux
**Enforcing**, the same posture as the real radio (see [`../../platform/security.md`](../../platform/security.md)).

---

## Ranked Findings

| # | Severity | Component | Unauth-reachable? | Real-radio transferable | Location | PoC shape |
|---|----------|-----------|--------------------|--------------------------|----------|-----------|
| 1 | **CRITICAL** | `IGMAuthService` (`com.gm.authtoken`, uid system) | Yes — any 3P app, auto-granted `normal` perms | **HIGH** — shipped APK + sepolicy, SELinux Enforcing | `a/f.java:363,690,666` | declare 3 permission strings, call `getAuthToken`/`setAuthToken`/`removeAccount` |
| 2 | HIGH | `IGMAuthService.invalidateAuthToken` | Yes — zero permission check at all | HIGH | `a/f.java:561,568` | malformed/crafted token string → DoS or SQLi against `authtokens` table |
| 3 | HIGH | `NavigationClusterService` (uid system, persistent) | Yes — exported, no permission | HIGH | `ClusterPresentationService.java:87-104`, `DisplayInfo.java:78-86` | `startService()` with forged `DisplayInfo` Parcelable |
| 4 | HIGH | GM permissions declared `prot=normal` (systemic) | Yes — telemetry/location READ family | HIGH | `dumpsys package permissions` | declare `com.gm.vehicle.permission.READ_*` etc., read live vehicle data |
| 5 | HIGH | FSA UDP/multicast discovery-listener crash (AIOOBE) | Yes — connectionless, spoofable | needs live confirm of `:3000` vs `:30490` | `NetCommsService.java:212-258`, `FSAMessage.java:55-77` | 20-byte UDP datagram, `payloadLength` in [237, N] |
| 6 | HIGH | FSA UDP/multicast connectionless injection (bypasses TCP gates) | Yes — no `validateHeader()` on UDP path | needs live confirm state-mutation fires with `sender=null` | `NetCommsService.java:253`, cf. `FSAServiceConnectedClient.java:253-260` | forged multicast datagram, opType 641/674, fktId ≥700 |
| 7 | HIGH | `UpdateService.install()` unauthorized-trigger | priv_app/platform_app/carservice_app only, not untrusted_app | HIGH | `UpdateServiceImplGB.java:434` | Binder call from a priv_app forces install of already-staged update (no content substitution — see INSTALLRUNNER trace) |
| 8 | MEDIUM-HIGH | `UpdaterAppService` UI/state-machine injection | needs confirmation of GMSWUpdater's SELinux label | HIGH | `UpdateManagerActionDispatcher.k(Intent)` | forged `extra_packagedetails` Parcelable drives fake update-available/downloaded UI |
| 9 | MEDIUM | `TcpsAcceptanceStatusService` `prot=normal` bypass | Yes | HIGH | GMTCPS manifest | declare `com.gm.tcps.permission.TCPS_STATUS`, read OnStar terms-acceptance status |
| 10 | LOW | `DeviceInformationService` exported, no intent-filter | Yes (explicit component) | HIGH | GM DeviceInformationService manifest | force (re)start only — resource-abuse nuisance |
| — | LOW/latent (native) | vhalgm 1-byte OOB read; gm_protokey unbounded 2nd memcpy (not reachable via current call graph) | no (DoS-only / unreachable) | see NATIVE-1 below | `fcn.0x87750`~0x877a0; `gm_protokey_decompiled.c:1604` | not exploitable this phase |

Cross-referenced, not re-described here: FSA opType correction and the two long-documented FSA TCP
parser bugs (unbounded-allocation RAM-DoS, reject-path framing desync) — see
[`../../platform/fsa_protocol.md`](../../platform/fsa_protocol.md#f-bugs-two-fsa-parser-bugs-shared-code-both-9002-and-9016);
`diagnosticsd` :49156 worker-starvation DoS — see
[`../../diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md).

---

## [PRIVESC-1] CRITICAL — GM/OnStar auth-token theft & forgery from an unprivileged third-party app

Chain: `untrusted_app` → SELinux `service_manager find` **granted** on `gm_authToken_service`
(`/product/etc/selinux/product_sepolicy.cil:586`) → `IGMAuthService` (host process
`com.gm.authtoken`, uid **system**) → `getAuthTokenByUserID` / `setAuthTokenByUserID` /
`removeAccount` / `getGuestAccountToken`.

The in-code guard (`a/f.java`, decompiled `IGMAuthService.Stub` impl) calls
`checkCallingOrSelfPermission("gm.permission.authentication.{ID|CLIENT|USER}")` before each
sensitive method (`a/f.java:363,690,666`) — but all three permissions are declared
`protectionLevel` = (unset →) **`normal`** in the shipped APK (confirmed via `dumpsys package
permissions`, sourcePackage=`com.gm.authtoken`, `prot=normal`). Normal permissions **auto-grant at
install time** to any app that lists a `<uses-permission>` for them — no signature match, no
runtime prompt.

Net effect: any ordinary sideloaded/third-party app can declare these 3 permission strings, pass
the in-code check trivially, then:
- `getAuthToken("id"/"client"/"user")` → exfiltrate live GM/OnStar bearer tokens from the on-device
  `authtokens` SQLite DB.
- `setAuthToken`/`setAuthTokenByUserID(uid,...)` → forge/replace tokens for arbitrary users.
- `removeAccount(uid)` → account-lockout DoS.

Real-radio transferability: **HIGH** — shipped `/system/app/GMAuthTokenService/GMAuthTokenService.apk`
+ shipped `product_sepolicy.cil`, confirmed under SELinux Enforcing. **Ranked #1 — the single most
severe finding of this audit.**

## [PRIVESC-2] HIGH — `invalidateAuthToken`: zero permission check + SQL injection

Same class (`a/f.java:561`). `invalidateAuthToken(String)` skips the permission gate entirely
(only a "DLM mode" internal-state check at lines 91-96), then runs
`getReadableDatabase().query("authtokens", ..., "token = \"" + str + "\"", ...)` (line 568) — the
caller-supplied string is concatenated directly into the SQL WHERE clause. Benign malformed input
= arbitrary token-deletion DoS; a crafted string breaking out of the quoted literal = SQL
injection against the token DB (impact bounded to that DB; full characterization deferred to
Phase 2). Reachable the same way as PRIVESC-1 — no permission needed at all for this one method.

## [PRIVESC-3] HIGH — `UpdateService.install()` reachable with no permission check, but cannot inject attacker content

`IUpdateService` (`com.gm.server.update.UpdateService`, host `com.gm.domain.server.delayed`, uid
system, SELinux domain `gmConnectionService`). `onTransact` case 11 (install) has no permission
enforcement; `UpdateServiceImplGB.install()` (`UpdateServiceImplGB.java:434`) forwards to the
source manager with zero checks. The only guarded method in the whole service is `dump()`
(`android.permission.DUMP`). Also unguarded: `initialInstall`, `download`, `cancelInstall`,
`schedule`, `setUpdatePreference`.

**Reachability correction:** SELinux `find` on `gm_domain_service` (the coarse label hosting this
+ Update/Diagnostics/Critical/Delayed) is granted to **platform_app, priv_app, carservice_app**
(`product_sepolicy.cil:850-852`) — **not** untrusted_app, **not** shell. So this is a
priv_app/platform_app/carservice_app → system escalation, not an ordinary-3P-app → system one.

Full INSTALLRUNNER trace (below) resolves the "can this deliver a malicious payload" question:
**no.** The caller's `PackageDetails` argument is never consumed by the install pipeline; the state
machine always falls back to its own internally-tracked, legitimately-downloaded `Package` object.
**Net verdict:** exploiting the missing permission check achieves forced/premature
install-triggering of whatever update the vehicle already has legitimately staged (a real bug —
consent-timing bypass, DoS/nuisance) — **not** payload-substitution. Downgraded from
"critical RCE-adjacent" to "HIGH: unauthorized-trigger / consent-bypass only."

## INSTALLRUNNER — full signature-verification trace (closes the code-execution question)

Traced `com.gm.server.update.installer.InstallRunner` + `UpdatePackage`/`Signature`/`Package`
(`com/gm/server/update/{installer,packages}/*` in `DelayedWKSApp`, plus `info3jar`).

- **Normal module/manifest path (containerType 0):** `InstallRunner.populateInstallers()`
  (`InstallRunner.java:577-578`) unconditionally runs a `Verifier` installer before
  `RecoveryModeInstaller`; `Verifier.run()` calls `UpdatePackage.verify()` (`UpdatePackage.java:179-208`):
  real X.509 chain check — extracts the embedded signing cert, loads a trust anchor from
  `/system/etc/security/production/signingCA.cer` (or `development/signingCA.cer` only if the
  manifest itself claims `isDevelopmentSecurity()=true`), calls
  `untrusted.verify(trusted.getPublicKey())` (`Signature.java:126-146`), then `Manifest.verify()`,
  then license/DRM checks, then per-module `ModulePart.verify()`. Any failure aborts before any
  apply step runs — genuine cryptographic verification, a second independent layer alongside the
  native `gm_update_engine` RSA-2048 whole-manifest check (see
  [`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md)).
- `UpdatePackage.parse(path, type)` — the only factory used by the normal OTA/USB manifest flow —
  hard-rejects any `type != 0` (`UpdatePackage.java:250-251`): an attacker cannot get a
  manifest-type package with forged content through this factory either; it must be a real signed
  manifest folder already on disk.
- **Real gap found, but not reachable via IPC/network (flagged open item):** for
  `containerType=2` (`CONTAINER_TYPE_DEV_CALIBRATION_OVERRIDE`), `UpdatePackage.verify()` returns
  `true` **unconditionally** (`UpdatePackage.java:210`), and `populateInstallers()` never adds a
  Verifier for this type (only Delay + `DevCaloverrideInstaller`, `InstallRunner.java:593-596`).
  `DevCaloverrideInstaller.copy()` copies whatever files are listed in `getDevCaloverrides()`
  straight into `/update_cache/calibrations` with **zero** signature/hash check, then reboots to
  recovery. But the only factory that builds such a package (`UpdatePackage.parseCaloverride`,
  `UpdatePackage.java:310-329`, itself validating nothing beyond `File.exists()`) is only ever
  called from `USBUpdateSource$1.onUSBMounted` (`USBUpdateSource.java:58`) — triggered by physical
  USB-media mount detection, not reachable via `IUpdateService.install()` or any other IPC method
  traced. **This is the single most promising remaining thread for a future update-path
  escalation** — closing it out requires RE of `USBNotifier.java` (what actually decides
  `container_type==2` and the file list on USB mount; not yet reviewed) to determine whether any
  non-removable-media path could be spoofed as a mounted USB volume.
- Downgrade/rollback: not directly evaluated via this trace (`PNVersionVerifier` compares against
  the manifest's own declared expected versions, protected by the same signature chain — state as
  inferred-absence, not proven-absence).

**Verdict: the update/install IPC surface is CLOSED for arbitrary-code-as-system /
attacker-content-injection.** The unguarded `install()` Binder call is a real bug
(unauthorized-trigger, consent-bypass, DoS) but not a payload-substitution vector. This refines,
without contradicting, the already-committed "no network→install path" finding — extend it with:
"and even the local (priv_app/platform_app) unguarded IPC path cannot substitute payload content;
the one theoretical zero-signature-check gap (`DevCaloverrideInstaller`/containerType 2) requires
physical USB media, not network/IPC, and its trigger path (`USBNotifier`) is not yet RE'd."

## [PRIVESC-4] HIGH, systemic root cause — GM permissions declared `prot=normal` en masse (telemetry/location exfil class)

`dumpsys package permissions` shows these GM-custom permissions at `protectionLevel=normal`
(auto-granted, no signature/prompt) guarding otherwise-sensitive data: the full
`com.gm.vehicle.permission.READ_*` family (`READ_VEHICLE_MOVEMENT`, `READ_VEHICLE_STATE`,
`READ_DOORS_AND_WINDOWS`, `READ_BRAKES`, `READ_SAFETY_SYSTEMS`, `READ_FUEL`, `READ_TIRES`,
`READ_ELECTRIC_VEHICLE`, `READ_SEAT_CONTROL`, etc. — live vehicle telemetry/location/speed exfil
by any app that lists them); `com.gm.apimanager.permission.ACCESS_VEHICLE_DATA_SERVICE`;
`com.gm.energy.permission.{READ,WRITE}_DATA`; `com.gm.lcm.provider.permission.{READ,WRITE}_LCM`;
`com.gm.hmi.radio.favoritesprovider...READWRITE`; `gm.permission.keystore.READ`;
`com.gm.subscription.permission.{BILLING,SUBSCRIPTION_UPDATE,ADAS_INFO}`; the
`com.gm.notification.SERVER_PUSH.*` family (server-push event spoofing).

`com.gm.apimanager.permission.ACCESS_VEHICLE_DATA_SERVICE` is flagged as a likely confused-deputy:
apimanager itself holds properly-protected `signature|privileged` permissions, but if its own data
service is exported and gates only on the normal-level permission, that's a privilege-laundering
path — **suspected, needs Phase-2 confirmation of the exported endpoint, not yet proven
end-to-end.**

**Confirmed-clean counterpoint (real negative result):** every
`com.gm.vehicle.permission.WRITE_*_PROTECTED` and `gm.vehicle.permission.WRITE_VEHICLE_DATA` **is**
properly `signature|privileged` — no normal-level vehicle WRITE exists. Also confirmed-clean: the
VHAL frame-injection primitive (`/data/vendor/ipcshim/*.in`) is **not** reachable from untrusted_app
or shell — the directory is `root:system 0770`, SELinux-labeled `gmy181_ipcshim_data_file`,
requiring `system` group membership or a domain with an explicit write allow-rule; this is not
reachable from an ordinary app despite root-adb being available in the emulator (a deliberate RE
convenience/artifact, does not apply to the real radio's shell/untrusted_app domains, which have
zero GM-service `find` grants at all).

## [APP-1] HIGH — `NavigationClusterService`: unauthenticated cluster/HUD display-state injection into a persistent system-UID process

Component: `com.gm.server.navigation.cluster.NavigationClusterService`, package
`com.gm.domain.server.delayed` (uid **system**, `android:persistent="true"`). Manifest:
exported=true, **no permission** (`DelayedWKSApp` AndroidManifest.xml:284-291), intent-filter
actions `gm.cluster.action.APP_SELECTED`/`SERVICE_READY`.

`onStartCommand()` (via `ClusterPresentationService.java:87-104`) reads
`intent.getParcelableExtra(EXTRA_DISPLAY_INFO)` directly off the raw Intent with zero
caller/UID/permission check; dispatches to `NavigationClusterService.onAppSelected(DisplayInfo)`
(44-73). The only internal gate is a string compare
`info.mControllingAppPkg.equalsIgnoreCase("com.gm.domain.server.delayed")` — trivially satisfiable
since the attacker constructs the whole Parcelable themselves. `DisplayInfo`
(`gm/cluster/DisplayInfo.java:78-86`) is a flat 7-field parcelable (width, height, displayId,
displayType, controllingAppPkg, controllingAppType, displayCapability) with no field validation.

**Important nuance:** these actions ARE declared `<protected-broadcast>` in ClusterService's
manifest, but protected-broadcast enforcement (`ActivityManagerService.broadcastIntentLocked`)
only gates `Context.sendBroadcast()` — it does **not** gate `Context.startService()`, which is how
this component is actually invoked. This is a general class of Android hardening gap: action-string
protected-broadcast declarations give a false sense of security against the `startService()` IPC
verb.

Impact: an unprivileged app (no special permission declared) can force cluster/HUD display-state
transitions inside a persistent system-UID process — a plausible display-spoofing and crash/DoS
vector (malformed displayType/displayId → NPE → persistent-process crash, which AOSP's watchdog may
then restart/reboot-adjacent). Safety-relevant since it's cluster/HUD-facing. Real-radio
transferability: **HIGH** (same shipped APK/manifest).

## [APP-2] MEDIUM-HIGH — `UpdaterAppService`: unauthenticated update-flow UI/state-machine injection

Component: `com.gm.updater.UpdaterAppService` (`GMSWUpdater.apk`). Manifest: exported=true, zero
permission, 15 intent-filter actions incl. `gm.update.action.PREPARE_AUTO_INSTALL`,
`DOWNLOAD_COMPLETED`, `UPDATE_RESULT`, `SCHEDULE_UPDATE_AVAILABLE`.

`onStartCommand()` dispatches on `intent.getAction()` with no caller check, reads
`extras.getInt("extra_reason")` unconditionally; several branches call
`UpdateManagerActionDispatcher.k(Intent)` which pulls a fully attacker-controlled Parcelable
`extra_packagedetails` (`PackageDetails`) and stores it as the app's live update-UI state, driving
notifications/navigation off it.

Per the INSTALLRUNNER trace above, no direct file-install/exec sink was found reachable from these
specific actions in this pass (`onPrepareAutoInstall`/`onDownloadComplete` only manipulate UI event
tags + `DataPoolDataHandler` state) — but this is a proven UI/state-spoofing surface: an attacker
app can fake "update available/downloaded/ready" states, force notification popups, or suppress
legitimate update prompts by injecting `UPDATE_IDLE`/`CANCELED`. Real-radio transferability: HIGH.

**Reachability note:** not reachable from untrusted_app per the same SELinux `gm_domain_service`
scoping as PRIVESC-3 (needs priv_app/platform_app/carservice_app) unless `GMSWUpdater` is labeled
differently — flag as needing confirmation of `GMSWUpdater`'s specific SELinux service label in
Phase 2 (may differ from `DelayedWKSApp`'s).

## [APP-3] MEDIUM — `TcpsAcceptanceStatusService` (GMTCPS): exported service gated by a `prot=normal` "permission"

Same defect class as PRIVESC-4. Manifest requires `com.gm.tcps.permission.TCPS_STATUS`,
exported=true — but that permission is declared with no `protectionLevel` attribute → defaults to
`normal` → any app can self-grant by listing it, defeating the apparent signature-looking
permission name. Lower severity than PRIVESC-1 (exposes TCPS/OnStar terms-acceptance status, not
raw control). **Confirmed-clean contrast (record so this doesn't read as "all of GMTCPS is
broken"):** GMTCPS's other exported components (`ViewTermsActivity`, `DemoActivity`, etc.) ARE
correctly protected with explicit `protectionLevel="signatureOrSystem"`.

## [APP-4] LOW — `DeviceInformationService` exported with no intent-filter

Exported=true (explicit-component-name reachable), no permission, but `onStartCommand` isn't
overridden (`onBind` always returns null) — only actionable effect is forcing a (re)start
(resource-abuse/keep-alive nuisance), not a data/control-plane bug. Informational/low-priority.

---

## FSA findings (AE-2 / AE-3 — see fsa_protocol.md for full mechanism)

Cross-ref only; full write-up lives in
[`../../platform/fsa_protocol.md`](../../platform/fsa_protocol.md#f-udp-udpmulticast-discovery-listener-crash-aioobe--high-unauthenticated):

- **AE-2 (HIGH):** `NetCommsService.DiscoveryListenTask.SocketRead()` UDP path has a fixed 256-byte
  receive buffer but trusts an attacker-controlled `payloadLength` in the `FSAMessage` constructor
  — an uncaught `ArrayIndexOutOfBoundsException` permanently kills the discovery-listener thread in
  every FSA-hosting process on the vlan5 multicast group, from one spoofed unauthenticated packet.
- **AE-3 (HIGH, state-effect needs live confirmation):** the same UDP path queues messages with
  `sender=null` without ever calling `validateHeader()` — a forged multicast datagram can drive the
  same unauthenticated cluster-injection primitives as the TCP path (opType 641/674 REQUEST/
  REQUESTRESPONSE, corrected from the earlier EVENT/1032 misattribution — see
  [`../../platform/fsa_protocol.md`](../../platform/fsa_protocol.md#f-inject-cluster-injection-surface)),
  but connectionlessly, spoofably, and without the TCP accept loop's 6-slot cap or source-IP dedup.

## NATIVE-1 — Native parser memory-safety audit: mostly CLEAN (negative result worth recording)

Audited: `vhalgm` (GM VHAL binary, vehicle-bus frame parser reached via `/dev/ipc/ipc3`),
`diagnosticsd` (the `:49156` UDS parser), `gm_protokey` (boot-time proto-key/disk-encryption
validator — **not** the UDS `$27` handler, per prior correction). **Correction:** all three native
GM vendor binaries are **x86-64**, not ARM — fix any doc that assumed ARM.

Findings:
- **LOW:** 1-byte OOB read in `vhalgm`'s multi-record frame loop (`onIpcData`→`fcn.0x87750`,
  instruction ~0x877a0): the record-count-driven loop reads the next record's length byte *before*
  validating the record fits in the remaining buffer; a crafted `count` byte exceeding actual
  records present causes up to ~2 bytes OOB read before the subsequent bounds check rejects and
  exits. DoS-only if it hits an unmapped page; no data disclosure to attacker (read result isn't
  returned).
- **LOW/latent:** unbounded second `memcpy` in `gm_protokey`'s `FUN_00105050`@0x105050
  (`gm_protokey_decompiled.c:1604`) into a fixed 0x110-byte heap buffer — the bound exists on the
  first `memcpy` (line 1601, `__memcpy_chk`, 0xff) but not the second. The only in-binary caller
  passes fixed-length arguments that can't reach the overflow condition, so this is a real code
  defect but **not reachable** via the current call graph. Would become HIGH if any other caller
  passes attacker-controlled length.
- **INFORMATIONAL:** `vhalgm` has deliberate assert-based aborts (`__android_log_assert` + int3) on
  out-of-range signalId/frameId table lookups — intentional guards (controlled crash), not
  corruption; don't conflate with real memory-safety bugs in any future fuzzing triage.
- **CONFIRMED-CLEAN (real negative result):** `vhalgm`'s frame registry lookup is a hashmap keyed
  by frameId (not raw array indexing) — unknown frames miss safely; `vhalgm`'s per-frame size gate
  rejects mismatched-length records before decode; `vhalgm`'s payload assembler has a guarded 8-byte
  read; `diagnosticsd`'s body-read bound (`length ≤ 0x3fffff`) exactly matches its fixed 4MB buffer,
  no overflow; `diagnosticsd`'s outbound `sendResponse` and several alloc/copy pairs (`createCopy`,
  `createCalibrationTransferRequest`, `setPurePayload`, `writePayload`) all size-match;
  `diagnosticsd`'s UDS TransferData handler streams to a file via `fwrite` with sequence+total-size
  checks, no memory buffer to overflow; `libpal_security`'s `CommIPC::readMessage` is properly
  length-guarded.

**Net takeaway:** GM's native C++ parsers are defensively coded; the real risk on this platform
sits at the Java/app/permission layer (PRIVESC/APP findings above), not native memory corruption. A
Phase-2 fuzzing plan is designed but not executed: libFuzzer harnesses for `diagnosticsd`'s UDS
pipeline and `gm_protokey`'s `FUN_00105050`, on-device ipcshim-injection fuzzing for `vhalgm`.

---

## Phase 2 Plan (top 3 priority)

1. **PRIVESC-1 token-theft PoC** — build a minimal sideloaded app declaring the 3 `normal`
   `gm.permission.authentication.*` strings, call `getAuthTokenByUserID`/`getGuestAccountToken`,
   confirm live token exfiltration against the `authtokens` DB.
2. **INSTALLRUNNER's open USBNotifier thread** — RE `USBNotifier.java` to determine whether any
   non-removable-media path can be spoofed as a mounted USB volume, which would reopen an
   app-reachable zero-signature-check path into `/update_cache/calibrations` (containerType 2,
   `DevCaloverrideInstaller`) plus forced reboot-to-recovery.
3. **AE-2/AE-3 UDP PoC** — build a UDP sender (no existing tool covers this; `fsaprobe`/
   `fsalisten4` are TCP-only), confirm the correct multicast port (`:3000` vs the live-scanned
   `:30490`), and empirically confirm both the AIOOBE discovery-listener crash and whether a
   state-mutating cluster-injection handler fires with `sender=null`.

---

## Cross-References

- [`../../platform/fsa_protocol.md`](../../platform/fsa_protocol.md) — FSA wire format, opType
  correction, cluster-injection surface, both TCP parser bugs, both new UDP findings
- [`../../platform/vehicle_network.md`](../../platform/vehicle_network.md),
  [`../../platform/emulator.md`](../../platform/emulator.md),
  [`AE_RESEARCH_HANDOFF.md`](../AE_RESEARCH_HANDOFF.md) — propagated opType correction
- [`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md),
  [`../../platform/ota_programming_roles.md`](../../platform/ota_programming_roles.md) — full
  INSTALLRUNNER verdict
- [`../../platform/security.md`](../../platform/security.md) — general security posture, PRIVESC-1
  cross-ref
- [`../../diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md)
  — AE-5 worker-starvation DoS (already fully documented there)
