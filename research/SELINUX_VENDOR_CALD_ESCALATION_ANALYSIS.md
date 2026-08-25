# `vendor_cald` / `calserviced` Reachability from `untrusted_app` — SELinux Audit

**Verdict: SEALED.** Neither `untrusted_app` (sideloaded app) nor `shell` (adb) can write
`/mnt/vendor/calibration/overrides/` or reach `calserviced`'s IPC. The `*.calovride`
OVERRIDE_BACKDOOR is real and (per provenance audit #37/#38) present in the binary, but it is only
triggerable by a domain that *already* holds calibration-write — it is not a `$27`-free path from
an app or an adb shell.

## Terminology correction (load-bearing)
The task conflates two distinct identities:
- **`vendor_cald`** = the Unix **user/uid** the daemon runs as. Confirmed live:
  `processes.txt` → `vendor_cald 585 1 ... S calserviced`.
- **`calserviced`** = the **SELinux domain** (`type calserviced`, entered via
  `typetransition init_32_0 calserviced_exec process calserviced`).

There is **no SELinux type named `vendor_cald`.** The overrides dir is gated by BOTH:
- **DAC:** `mkdir /mnt/vendor/calibration/overrides 770 vendor_cald system` (owner `vendor_cald`,
  group `system`, mode 770 → "others" = 0).
- **MAC:** the dir/file SELinux type is `calibration_data_file` (the label applied under
  `/mnt/vendor/calibration`, a locked ext4 partition — `fstab.txt` /
  `mounts.txt: /mnt/vendor/calibration ... rw,seclabel`).

Environment: **SELinux Enforcing** (`selinux_status.txt`); bootloader **locked**
(`ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`), verified boot **green**, AVB 1.2,
`ro.secure=1`, `ro.adb.secure=1`.

Source of truth: `enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` (compiled CIL,
neverallows retained). Cross-checked against `apr2026` and base `Y181` CILs — identical results.

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
The trust floor is **"system/vendor or above."** Notably `gm_diagnosticsd` = the UDS/`$27` path
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
fall inside the negated attribute sets, so even a policy-add mistake that granted an app `find`
would fail CTS/`checkpolicy`. hwbinder-to-app is a hard AOSP neverallow.

## (c) Side-channel vectors

- **Modify `calserviced.rc` / add an init service on disk:** `.rc` lives on `/vendor`
  (dm-verity + AVB, `verifiedbootstate=green`, device `locked`). Any edit breaks verity → won't
  boot. **Blocked.**
- **Runtime init trigger via property:** the writable calibration props
  (`exported_calibration_prop`, `exported_rvc_prop`) are `property_service set`-able **only by
  `calserviced`**, not by `shell`/`untrusted_app`. No app-settable property spawns a
  cald-context action. **Blocked.**
- **DAC group angle:** dir group is `system` (gid 1000). adb `shell` groups (from
  `current_user.txt`) are `shell,input,log,adb,sdcard_rw,sdcard_r,ext_data_rw,ext_obb_rw,net_bt*,
  inet,net_bw_stats,readproc,uhid,readtracefs` — **no `system`, no `vendor_cald`.** A sideloaded
  app's uid is likewise outside both. DAC denies regardless of MAC.
- **Exploit a whitelisted writer / `calserviced` itself:** the only genuine routes to a
  cald-context (or `calibration_data_file`) write are memory-corruption/RCE into `calserviced` or
  one of `{camerad, gm_diagnosticsd, gm_update_engine, gmloggervendorserviced, bootanim,
  plmanager, gm_vnd_vehicleaudiocontrol, system_app}`. That is an exploit-primitive requirement,
  not a reachability-by-design path — and if you already have `calibration_data_file:file create`
  you no longer need the backdoor.
- **Via `system_server`/`system_app`:** these can write the dir, so a confused-deputy Binder API
  that writes into the overrides dir on an app's behalf would matter — but no such
  `calserviced`-published framework service exists (see (a)), and no app→cald edge is in policy.

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

**Conclusion — SEALED.** The `*.calovride` OVERRIDE_BACKDOOR is a **local-privilege convenience for
a domain that already owns calibration-write**, not an app- or adb-reachable `$27` bypass. To use
it you must first *become* one of the whitelisted vendor domains (RCE) or already hold the
`calibration_data_file:file create` primitive — in which case the backdoor grants nothing new.
Given Enforcing SELinux + locked bootloader + dm-verity/AVB, there is no init-modification or
property side-channel from `shell`/`untrusted_app`. The realistic residual risk is (1) a bug in
`calserviced`'s HIDL surface reached from a *compromised whitelisted vendor peer*, or (2) the
backdoor being combined with an independent `system_app`/`system_server` cal-write confused-deputy
— both out of scope for an unprivileged sideloaded app.

### Evidence files
- `enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` (policy; apr2026 + base Y181 concur)
- `enumeration/Y181/jun2026/raw/processes.txt` (`vendor_cald` uid runs `calserviced`)
- `enumeration/Y181/jun2026/raw/current_user.txt` (adb `shell` uid/groups/context)
- `enumeration/Y181/jun2026/raw/selinux_status.txt` (Enforcing)
- `enumeration/Y181/jun2026/raw/all_properties.txt` (locked bootloader, AVB green)
- `enumeration/Y181/jun2026/raw/{fstab,mounts}.txt` (`/mnt/vendor/calibration` mount)
- `research/PROVENANCE_AUDIT_AUG2026.md` #36–38 (backdoor + `770 vendor_cald system` provenance)
- `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` L98–117 (backdoor description)
