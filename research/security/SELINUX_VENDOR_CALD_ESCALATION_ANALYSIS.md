# `vendor_cald` / `calserviced` Escalation Audit

**Target:** GM MY22/Y181 IVI (Intel Apollo Lake SoC, GHS INTEGRITY host + Android 12L guest),
2024 Silverado head unit — the owner's own module.

**Scope — what lives here:** can `untrusted_app` (sideloaded app) or adb `shell` reach the
`calserviced` daemon or write `/mnt/vendor/calibration/overrides/*.calovride`? CIL rule IDs
(write-allow list, neverallows), hwbinder/socket/Binder reachability gates, DAC (uid/gid/mode)
gates, a feasibility table, and the current verdict.

**What does NOT live here:**
- The `.calovride` container format, checksum/SHA-256 scheme, and the loader's version/rebuild
  behavior → owned by
  [`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](../eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md)
  (§3e). This doc states only the DAC/MAC facts needed to gate that write path.
- CAN613/614 scoped-VIP-RAM-write mechanism and the Ghidra signature-verification trace →
  owned by
  [`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](../eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md), which
  points seed/signature detail onward to
  [`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](../eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- CalDef record structure / VIP calibration-index tables → owned by
  [`CALDEF_VIP_CALIBRATION_ANALYSIS.txt`](../eeprom-calibration/CALDEF_VIP_CALIBRATION_ANALYSIS.txt).
- The updater's own package-provenance/install-IPC narrative (DevCaloverrideInstaller discovery
  rules, APK provenance) → owned by
  [`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15).
  This doc only states the SELinux/DAC consequence (a privileged writer does not relax shell's
  own permissions) and defers the caller-boundary question itself to that doc.
- The Android-framework `gm.permission.*_DIAGNOSTIC_CALIBRATION_DATA` Binder permission gate is a
  **different, non-SELinux** mechanism; it is noted below (§ Environment) as a cross-check only,
  not owned here.

Evidence tags: `[C]` = confirmed live on-device, `[inferred]` = transferred from a sibling
build's policy without independent live confirmation, `[U]` = explicitly unverifiable from a
locked shell.

---

## Verdict (current)

**No established route.** Direct `.calovride` writes to
`/mnt/vendor/calibration/overrides/` and direct `calserviced` IPC are unreachable from
`untrusted_app` or adb `shell` under every inspected identity and build. The caveat is scope,
not strength: a legitimate privileged updater path (DevCaloverrideInstaller) exists and its
caller boundary toward an unprivileged invoker has not been fully traced — see
[`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15)
for that open question. No calibration deployment via this path has been performed.

> **History:** the 2026-10-30 analysis stated an absolute "DENIED, no route" verdict. On
> 2026-11-15 it was revised to "no *established* route; the updater's caller boundary is a
> separate, unresolved question," because a legitimate privileged updater copier exists and an
> RCE prerequisite does not model every authorized import path. **The 2026-11-15 wording is the
> current verdict; the absolute "no route" framing is superseded.**

## Terminology correction (load-bearing)

Two distinct identities are frequently conflated:
- **`vendor_cald`** = the Unix **uid** the daemon runs as. `[C]` confirmed:
  `processes.txt` → `vendor_cald 585 1 ... S calserviced`.
- **`calserviced`** = the **SELinux domain** (`type calserviced`, entered via
  `typetransition init_32_0 calserviced_exec process calserviced`).

There is **no SELinux type named `vendor_cald`.** The overrides directory is gated by both:
- **DAC:** `mkdir /mnt/vendor/calibration/overrides 770 vendor_cald system` — owner `vendor_cald`,
  group `system`, mode 770 (others = 0 permissions).
- **MAC:** the directory/file SELinux type is `calibration_data_file`, applied under
  `/mnt/vendor/calibration`, a locked ext4 partition (`fstab`/`mounts`:
  `/mnt/vendor/calibration ... rw,seclabel`).

The `*.calovride` `OVERRIDE_BACKDOOR` string and per-row SQL application path are real and
present in the binary (per `PROVENANCE_AUDIT_AUG2026.md` #37/#38; container/loader mechanics
owned by CALSETSDB §3e), but it is only triggerable by a domain that **already** holds
calibration-write — it is not a `$27`(SecurityAccess)-free path from an app or adb shell.

## Environment

`[C]` SELinux **Enforcing**; bootloader **locked** (`ro.boot.flash.locked=1`,
`ro.boot.vbmeta.device_state=locked`); verified boot **green**; `ro.boot.avb_version=1.2`
(avbtool/property version — the AVB spec itself is 1.1 per `avb_version.h` MAJOR 1/MINOR 1);
`ro.secure=1`; `ro.adb.secure=1`.

`[C]` 2026-10-30, Y175: a UID 1000 shell in the `system_app` SELinux domain received
`Permission denied` when attempting to inspect `/mnt/vendor/calibration` and its `overrides`
directory. This is a metadata-access test, not a write or Binder authorization test; it does
not establish whether that identity can use another calibration interface.

Separately, `[C]` live-Y175 2026-11-13: ADB per-key authorization is not enforced on this radio
(same-radio finding, external source note, out of this doc's corpus); that finding is about ADB
**key** authorization scope and stays separately scoped from the root/SELinux conclusions here —
it does not change this doc's verdict.

The framework-level Binder permission gate on GM's calibration API (a **different** mechanism
from the filesystem/hwbinder path analyzed below) resolves on live Y175 as:
`gm.permission.WRITE_DIAGNOSTIC_CALIBRATION_DATA` = `dangerous`,
`gm.permission.READ_DIAGNOSTIC_CALIBRATION_DATA` = `normal` (`permissions_full.txt`).
`dangerous` is not auto-granted, which only reinforces the sealed verdict — but it is a distinct
gate from the `.calovride`/`calserviced` surface analyzed here, not restated further.

Source of truth: `evidence/enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` (compiled CIL,
neverallows retained). Cross-checked against `apr2026` and base `Y181` CILs — identical results.

## Live re-verification trail

Four dated live-verification passes re-confirm or upgrade the base analysis; each is folded
in place rather than left as a stacked patch.

**`[C]` live-Y175 2026-10-05** (`W213E-Y175.5.2-SIHM22B-383.1`,
`/tmp/radio_audit/20261005_232227/raw/`): re-confirms the sealing *preconditions* on a live Y175
radio — the CIL rule analysis itself stays Y181-scoped (a locked user shell cannot pull Y175's
sepolicy).
- SELinux **Enforcing** (`00_whoami.txt:3`; 179/179 avc `permissive=0`); locked bootloader;
  verified-boot green; `ro.secure=1`/`ro.adb.secure=1`/`ro.debuggable=0` — same posture as Y181.
- `calserviced` runs as uid **`vendor_cald`**, SELinux domain **`calserviced`**, on Y175 too:
  `u:r:calserviced:s0 vendor_cald 573 1 ... S calserviced` (`ps.txt:124`).
- `/mnt/vendor/calibration` is a live **rw,seclabel** ext4 mount on Y175 (`mounts.txt`).
- adb `shell` on Y175 is `uid=2000`, groups carry **no `system`(1000) and no `vendor_cald`**
  (`00_whoami.txt`) — the DAC floor denying the overrides-dir write holds on Y175.
- Live avc log has **zero** `untrusted_app`/`shell` denials against `calibration_data_file`,
  `mnt_vendor`, `cald`, or `calserviced` — consistent with no such edge existing, but this is a
  non-attempt, not positive proof of a grant/deny; it does not substitute for the CIL read.

`[U]` **Unverifiable from live Y175:** the actual allow/neverallow set in §(a)/(b) below is read
from Y181's `vendor_sepolicy.cil`; a locked user shell cannot pull Y175's own sepolicy, so the
per-rule claims (hwservice whitelist, `shell` → `dir getattr` only, the neverallows) transfer by
the usual Y177/Y181 policy-reuse inference (`[inferred]`), not by independent live Y175 evidence.

**`[C]` live-Y181.3.2 2026-11-12** (bench radio, read-only adb): `uid=2000(shell)` /
`u:r:shell:s0`, `getenforce`=Enforcing, patch level 2025-06-05, `user`/`release-keys`; all 3596
runtime `avc` records (194 kernel + 1055 main + 2347 events, overlapping streams) are
`permissive=0`.

> **History:** this note previously stated "8270 `avc` lines," which no source supports;
> corrected 2026-11-12 to the 3596 count per `gminfo37_update_cache_FORENSIC_LLM.txt` FACT lines.

The "Enforcing" premise holds today. The shell can read
`/vendor/etc/selinux/vendor_sepolicy.cil` (checked 2026-11-12), but the CIL rules cited below
were not re-diffed on that date.

**`[C]` Y181.3.2-ref 2026-10-06** — §(a)/(b)'s CIL rule set re-derived **verbatim from a live
Y181.3.2 root reference** (`W231E-Y181.3.2-SIHM22B-499.3`, SELinux Enforcing), not just the
jun2026 pull. Read directly from the on-device `/vendor/etc/selinux/vendor_sepolicy.cil`:
- `:2317 (allow calserviced gm_calibration_hwservice (hwservice_manager (add find)))` and
  `:2320 (allow calserviced gm_calibration_provider_hwservice (hwservice_manager (add find)))` —
  CONFIRMED verbatim.
- `find` whitelist: `gm_sxm_32_0` (`:2566`/`:2565`), `hal_calibration_client` (`:2949`),
  `hal_calibration_provider_client` (`:2938`), `gmlocation-hal-1_0d` (`:5156`). (The
  `hal_calibration_server`/`hal_calibration_provider_server` of §(a) reach their own service via
  the `add find` server grant, not a standalone `find` line — same net whitelist, finer
  mechanism.)
- `:2346 (allow shell_32_0 calibration_data_file (dir (getattr)))` — CONFIRMED verbatim as the
  **only** `shell` grant on `calibration_data_file` (no `file create`/`write`/`add_name`/`open`).
  The "`shell` is defanged" claim holds on Y181.3.2.
- `untrusted_app` has **zero** allow rules against `calibration`/`calserviced`/`mnt_vendor`/
  `hwservice`/`hwbinder` in the live CIL (only hits are the giant `domain`/`file_type`
  `typeattributeset` declarations, not allows) — total MAC denial CONFIRMED.
- Neverallows present but as **separate** statements, not the combined `(add find)` form:
  `gm_calibration_hwservice (add)` `:2952` / `(find)` `:2953`;
  `gm_calibration_provider_hwservice (add)` `:2322`/`:2941` / `(find)` `:2942`. Net effect
  identical (both `add` and `find` neverallowed for the negated base attribute).
- `/mnt/vendor/calibration` is a live `ext4 ... errors=panic ... wait,check,formattable,nofail`
  mount in `/vendor/etc/fstab` on Y181.3.2 too.

This upgrades §(a)/(b) from "Y181 jun2026 pull" to "live Y181.3.2 on-device CIL." Y175 per-rule
claims remain `[inferred]` (no bootable Y175 policy); Y175 live-environment preconditions were
separately confirmed above.

---

## (a) Does `calserviced` expose a socket / pipe / Binder interface an app can connect to?

**No app-reachable interface exists.**

**Binder / HIDL (hwbinder):** `calserviced` is a hwbinder **server**. It registers two HIDL
services with `hwservicemanager`:
```
allow calserviced gm_calibration_hwservice          (hwservice_manager (add find))
allow calserviced gm_calibration_provider_hwservice (hwservice_manager (add find))
```
The only domains permitted to **`find`** (and thus call) those services are a fixed vendor
whitelist:
```
gm_sxm, hal_calibration_client, hal_calibration_server,
hal_calibration_provider_client, hal_calibration_provider_server, gmlocation-hal
```
Direct binder call/transfer edges to `calserviced` come only from:
`gm_vnd_vehicleaudiocontrol`, `bootanim`, `plmanager`, `gmlocation-hal`, `hwservicemanager`.
**`untrusted_app` and `shell` appear in none of these.**

**No framework (service_manager) service:** grep for `calserviced ... service_manager` (non-hw)
returns nothing — `calserviced` publishes nothing to the app-facing `servicemanager`, so there is
no `Context.getSystemService`/`ServiceManager.getService` handle an app SDK could obtain.

**No listening UNIX socket / FIFO:** `calserviced` only ever appears as a socket **client**
(`connectto` init, `ipc_serverd`, `gm_vnd_IPCServer`; `sock_file write` to `property_socket`,
`ipc_device`). It creates no abstract/filesystem socket that another domain is allowed to
`connectto`. There is no named-pipe rule. Nothing for an app to open.

**hwbinder is categorically closed to apps:** `untrusted_app_32_0` has **zero** `hwbinder` /
`hwservice_manager` allows in the policy (AOSP baseline). An app cannot even talk to
`hwservicemanager`, let alone resolve `gm_calibration_hwservice`.

## (b) SELinux rules gating the write + neverallows

**Who can write `calibration_data_file` (the overrides dir/file type):**
```
init, vendor_init, vold, calserviced, camerad, gm_diagnosticsd,
gm_update_engine, gmloggervendorserviced, bootanim, system_app, shell(!)
```
The trust floor is **"system/vendor or above."** Notably `gm_diagnosticsd` is the UDS/`$27` path
the backdoor was meant to sidestep.

**`shell` is on that list but is defanged** — its only grant is:
```
allow shell_32_0 calibration_data_file (dir (getattr))
```
i.e. `stat()` the directory. **No** `file create`, `write`, `add_name`, or `open`. So even a full
adb shell **cannot drop a `.calovride` file.** No `shell → mnt_vendor_file` write either.

**`untrusted_app`:** grep for `untrusted_app` against `calibration`, `mnt_vendor`, `cald`,
`calserviced`, `hwservice`, `hwbinder` → **empty in every release.** Total MAC denial; DAC (mode
770, app not in `system`/`vendor_cald`) denies independently.

**Neverallows (retained in the CIL) that also block it:**
```
neverallow base_typeattr_* gm_calibration_hwservice          (hwservice_manager (add find))
neverallow base_typeattr_* gm_calibration_provider_hwservice (hwservice_manager (add find))
```
These are the compiled `neverallow { domain -<whitelist> } ...` forms — `untrusted_app`/`shell`
fall inside the negated attribute sets, so even a policy-add mistake granting an app `find` would
fail CTS/`checkpolicy`. hwbinder-to-app is a hard AOSP neverallow.

## (c) Side-channel vectors

- **Modify `calserviced.rc` / add an init service on disk:** `.rc` lives on `/vendor`
  (dm-verity + AVB, `verifiedbootstate=green`, device `locked`). Any edit breaks verity → won't
  boot. **Blocked.**
- **Runtime init trigger via property:** the writable calibration props
  (`exported_calibration_prop`, `exported_rvc_prop`) are `property_service set`-able **only by
  `calserviced`**, not by `shell`/`untrusted_app`. No app-settable property spawns a cald-context
  action. **Blocked.**
- **DAC group angle:** dir group is `system` (gid 1000). adb `shell` groups are
  `shell,input,log,adb,sdcard_rw,sdcard_r,ext_data_rw,ext_obb_rw,net_bt*,inet,net_bw_stats,
  readproc,uhid,readtracefs` — **no `system`, no `vendor_cald`.** A sideloaded app's uid is
  likewise outside both. DAC denies regardless of MAC.
- **Privileged writers exist; their caller boundary is the question.** An earlier statement that
  memory corruption was the only genuine route was too broad. The updater contains a legitimate
  DevCaloverrideInstaller that copies into the protected destination. Current Y175 USB discovery
  selects that package type only on non-user builds; invoking the normal install IPC has not been
  shown to register arbitrary shell-supplied files. See
  [`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15)
  for current-APK provenance, discovery/installer separation, and the open native boundaries —
  not restated here. **This does not relax shell DAC/MAC permissions.**
- **Via system services:** a supported privileged importer and an exploitable confused deputy are
  different claims. The calibration service itself has no newly demonstrated ordinary-app write
  API; the updater's independent package-registration and caller gates must be traced (owned by
  the OTA doc above) before claiming it can place a file on an unprivileged caller's behalf.

---

## Feasibility assessment

| Vector | Reachable from `untrusted_app`? | From adb `shell`? |
|---|---|---|
| Write `/mnt/vendor/calibration/overrides/*.calovride` (MAC) | No (no allow) | No (`dir getattr` only) |
| Write it (DAC, mode 770 `vendor_cald:system`) | No | No |
| hwbinder call to `gm_calibration[_provider]_hwservice` | No (no hwbinder at all) | No |
| Framework `servicemanager` handle to `calserviced` | No (none published) | No |
| UNIX socket / FIFO into `calserviced` | No (server has no listener) | No |
| Edit `calserviced.rc` / add init svc | No (verity + locked) | No |
| Property-triggered init action | No (props are cald-only) | No |

## Open conflicts

None specific to this doc. (The corpus-wide MEC/module-naming/VMM1-bitness/EEPROM-byte/seed-length
items in `PROVENANCE_AUDIT_AUG2026.md`/README.md's cross-doc Open Conflicts do not touch
`calserviced`/`vendor_cald` reachability.)

### Evidence files
- `evidence/enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` (policy; apr2026 + base Y181 concur)
- `evidence/enumeration/Y181/jun2026/raw/processes.txt` (`vendor_cald` uid runs `calserviced`)
- `evidence/enumeration/Y181/jun2026/raw/current_user.txt` (adb `shell` uid/groups/context)
- `evidence/enumeration/Y181/jun2026/raw/selinux_status.txt` (Enforcing)
- `evidence/enumeration/Y181/jun2026/raw/all_properties.txt` (locked bootloader, AVB green)
- `evidence/enumeration/Y181/jun2026/raw/{fstab,mounts}.txt` (`/mnt/vendor/calibration` mount)
- `research/provenance/PROVENANCE_AUDIT_AUG2026.md` #36–38 (backdoor + `770 vendor_cald system` provenance)
- `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` L98–117 (backdoor description; that doc has been retired and folded into other docs per the research/README.md "Retired" table, original removed; the `OVERRIDE_BACKDOOR` description now lives in `research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`)

## Related
- [`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](../eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) —
  `.calovride` container/checksum/loader format (this doc owns the write-path reachability only).
- [`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](../eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) — the
  one documented successful custom-write path (CAN613/614 scoped-VIP-RAM-write), unrelated to
  this filesystem/hwbinder surface.
- [`CALDEF_VIP_CALIBRATION_ANALYSIS.txt`](../eeprom-calibration/CALDEF_VIP_CALIBRATION_ANALYSIS.txt) — CalDef/VIP
  calibration record structure.
- [`../../platform/ota_update_stack.md`](../../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15) —
  updater caller-boundary / DevCaloverrideInstaller provenance (owner of the §(c) open question).
- [`../../platform/security.md`](../../platform/security.md) — general SELinux/FBE posture by firmware
  build; this doc is the research-tier deep dive on one specific daemon/path.
