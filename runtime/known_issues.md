# GM Info 3.7 Known Issues

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (27 files, Feb 11-19, 2026), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## SELinux Denials (7,811 total across 3.7GB corpus, 25 files)

Per-file range: 111-662. The previously reported "462" was from a single file (logcat_20260219).

- **CBC (Connected Body Control):** Most denials
- **RVC (Rear Vision Camera):** Camera-related denials
- **SXM (SiriusXM):** Radio service denials
- No USB or CarPlay-related denials observed

## Audio Issues

- **ECNR HAL:** `vendor.gm.audio@1.0::IECNRControl` fails 8 times per boot in rapid succession (~100ms intervals). Each attempt cycle: VAC -> hwservicemanager -> "not registered" -> "unable to set property" -> "not installed". The service is genuinely missing from the system image — not a timing issue.
- **Volume table:** XML load failure (volume control handled externally by amp/DSP)
- **Audio underruns:** 1,710 CARLINK_AUDIO [AUDIO_UNDERRUN] events across 16 files + 20 PulseAudio ALSA buffer underruns across 8 files. Per-session range: 2-456 underruns. Mostly during Siri transitions.
- Factory: 8 ALSA underruns, 4 Davey! events; debloated: 0 of each

## AVB Streamhandler Issues (404 events across 19 files)

- TX worker oversleep (scheduling jitter) — worst: 11.5ms (limit 2ms)
- ALSA engine oversleep — worst: 12.2ms (limit 4ms)
- Both are intermittent timing issues, not fatal
- Directly correlates with PulseAudio underruns (AVB scheduling miss -> downstream ALSA buffer starvation)

## Thermal Subsystem

4 zones from Thermal HAL v2.0:

| Zone | Boot Range | Streaming Range | Throttle | Shutdown |
|------|-----------|-----------------|----------|----------|
| TCPU | 15-39C | 28-33C | 108C | 109C |
| TGPU | tracks TCPU within 0-5C | tracks TCPU within 0-5C | 108C | 109C |
| TBATTERY | constant 25C (virtual stub) | constant 25C | N/A | N/A |
| TSKN | constant 25C (no real sensor) | constant 25C | N/A | N/A |

Only TCPU and TGPU are real thermal zones. TBATTERY and TSKN are stubs returning fixed values.

## Display/Graphics

- **iahwcomposer init:** EDID 640 bytes, CRTC id 35, DRM connector 37
- 3 physical displays configured but only display 0 exists
- EXPLICIT SYNC enabled, High Quality Scaling
- No DCIP3/wide gamut, no HDR, no VRR support
- Gralloc format conversion errors (intermittent)
- Wide color gamut init failures (display doesn't support wide gamut)

## Google Templates Host Crash

`com.google.android.apps.automotive.templates.host` throws ForegroundServiceStartNotAllowedException during boot. `BootCompleteReceiver` calls `startForegroundService` when the app is not yet in a state that allows foreground service starts. This is a Google AAOS platform bug (2 occurrences observed).

## Third-Party Media MediaSession Token Mismatch (AAOS structural bug)

User-visible symptom: any third-party media app — including carlink_native — that crashes, is force-closed, or has its session destroyed (OS sleep, USB disconnect, etc.) will keep producing metadata, but the cluster will go blank or stale while the in-dash native Media Player continues to display correct song info. The only fixes are app reinstall or a head unit reboot.

Root cause is a structural Android framework limitation, not a GM-specific bug:

- `MediaBrowserServiceCompat.setSessionToken()` is **one-shot per Service instance lifetime**. A second call on the same Service throws `IllegalStateException: The session token has already been set`.
- When the app's session is destroyed (`onSessionDestroyed`), the underlying MediaSession dies but the singleton `MediaBrowserService` keeps a stale reference to the dead token. The app cannot hand out a fresh token from the same Service.
- Privileged AAOS consumers (Media Center / GMCarMediaService / ClusterService) keep their bindings to the old token instead of rediscovering the new session.
- Google's official guidance ([Building a media browser client](https://developer.android.com/media/legacy/audio/mediabrowser)) confirms: *"the session cannot become functional again within the lifetime of the MediaBrowserService"* — clients must `disconnect()` so the OS can destroy the Service. On AAOS the clients are GM system services the third-party app cannot control.
- Why the in-dash player still works while the cluster doesn't: they read down different paths. The native Media Player goes via `MediaSessionManager` directly and recovers; the cluster path goes through `GMCarMediaService` → `ClusterService` and stays bound to the dead token.

Workaround applied in carlink_native: deactivate-and-reactivate the existing `MediaSession` rather than recreate it (`MediaSessionManager.refresh()`); on `DISCONNECTED` use `STATE_PAUSED` instead of `STATE_STOPPED` + cleared metadata so cluster controllers stay attached. Static `mediaSessionToken` with guarded `updateSessionToken()` prevents the double-set crash on display-mode reinit (observed FATAL stack: `CarlinkMediaBrowserService.updateSessionToken(CarlinkMediaBrowserService.kt:84)` ← `CarlinkManager.initialize(CarlinkManager.kt:420)`, triggered by a double `setSessionToken()` during rapid reconnection). None of this fully recovers from a process-death scenario — only the OS killing the Service does.

Crash references: see `runtime/memory_pressure.md` for the two `setSessionToken()`-double-call FATAL EXCEPTION events observed in the 3.7GB logcat corpus, and the surrounding section on broader AAOS media-token state.

Affects: all GM AAOS platforms (Info 3.x and VCU/CIP) — this is an Android-framework-level limitation, not platform-specific.

## VIP MCU Health Telemetry

PLSS_PMPAL reports at 1Hz via IPC: `health:48 10 0 0 0 0` (consistent across all sessions). Format: 6 integer fields, values stable — no anomalies detected.

## CPC200 Adapter Issues

> **Scope note (2026-11-12):** these items are from the February 2026 CPC200 + `zeno.carlink` rig. The
> radio currently on the bench runs the OCBM-box + `zeno.gmccpa` (gm_ccpa) path instead; its observed
> behaviour is in the Y181B section above and in `video/carplay_video_pipeline.md` /
> `audio/carplay_audio_pipeline.md`. gm_ccpa is CarPlay-only (no Android Auto); "Android Auto" strings
> in the logs are GM media-source labels.

- Unrecovered AirPlay packets during Siri to media transitions
- MFi IC: clone/compatible, fallback address works (not a real Apple MFi chip)
- WiFi channel 161 (5.8GHz) — may have interference issues in some environments

## Y181B live-radio observations (retained logs + live adb, 2026-11-12)

Build `W231E-Y181.3.2-SIHM22B-499.3`, 30 boots recorded over 2026-11-10..12 (events log covers 29; `main`/`kernel` only the later ones). Sources: gmlogger `main`/`system`/
`kernel`/`events` rotation set and `vendor/ghs.log` pulled 2026-11-12; live `getprop`/`getenforce`.
Timing, shutdown-reason and DSP-retry detail lives in [`boot_timing.md`](boot_timing.md).

- **SELinux is Enforcing at runtime even though the boot property says permissive.** Live:
  `getenforce` -> `Enforcing` while `getprop ro.boot.selinux` -> `permissive`. Also measured: all 3596
  retained `avc:` records show `permissive=0`; the kernel cmdline carries both an early `enforcing=0`/`selinux=permissive`
  pair and a later `enforcing=1`/`selinux=enforcing` pair. Consistent with the
  Y177 note below (init built with `ALLOW_PERMISSIVE_SELINUX=0` ignores the arg; that mechanism is from another doc and not re-derived here). Any doc claiming
  "permissive" for Y181 from the boot arg alone is wrong. [read, live]
- **No crash evidence:** 0 `FATAL EXCEPTION`, 0 kernel panic, 0 `ANR in` in the retained logs. The
  February "12 FATAL EXCEPTION" corpus (memory_pressure.md) is a different, older capture; do not read
  this as the Y181B crash rate. gm_ccpa (`zeno.gmccpa`) has no crash in these logs. [read]
- **`/dev/watchdog` does not exist** (`watchdogd: Failed to open /dev/watchdog: No such file or
  directory` every boot; absent live). [read, live]
- **Abrupt vs clean power-down:** `ghs.log` has `ShutdownReason 0x23` (10 lines = 5 boot blocks), `0x37`
  (24 lines = 12 blocks) and `0x00` (22 lines = 11 blocks); code meanings unknown, and the value describes the
  previous cycle (see `boot_timing.md`; `0x23` is not simply "abrupt": it also follows `reboot,shell` and
  recovery endings). Boots whose next-boot reason is `cold` have no Android shutdown path in the logs. [read counts; meaning unresolved]
- **dabridge UDC request loop (correlation only):** kernel log is dominated by
  `platform dabr_udc.0: Unhandled Setup(-95): 80.06 v0f00 i0000 l5 DATA_IN` -- a GET_DESCRIPTOR for the
  USB BOS descriptor (type 0x0f, wLength 5) rejected with -95 (EOPNOTSUPP), repeated ~3.8-3.9k times/s
  (21,575 lines per 5.5 s kernel-log rotation file). 813,398 `Unhandled Setup` lines in total = 761,122 on boot 26
  (retained kernel window t=633.9-828.5 s only; earlier part rotated out) + 52,276 on boot 27 (t=62.5-76.3 s); boots 28 and 29 show none, and
  earlier boots' kernel history is not retained. Boots 26 and 27 each ended with init `reboot,shell` within ~0.1-0.2 s of the last storm line
  (so they were shell-initiated reboots, not power loss), but who issued them is not logged at caller-identity/reason level, so **no causal link is established** [2026-11-12 qualification: init does log the requesting process: `Received sys.powerctl='reboot,shell' from pid: 23174 (/system/bin/reboot)` on boot 26 (t=828.434) and `from pid: 6759 (/system/bin/reboot)` on boot 27 (t=76.048); only who invoked `/system/bin/reboot` and why is unlogged. On boot 26 the `reboot,shell` request (t=828.434) precedes the last storm line (t=828.531) by ~0.1 s; on boot 27 the last storm line is t=76.266, after the request at 76.048. Correlation only]). What `dabr_udc`
  is wired to is not identified. [read; cause unknown]
- **Rear camera (`ghs.log` `Camera:`):** 39 `[Recovery] State->CableFault`, 20 `CableFault cleared`, 83
  sensor resets + 83 IPU resets, and 31 `Ignoring cable fault because frames were received`.
  Android side: `camera_cable_fault_daemon` logs 12 `CABLE_FAULT ... status changed 1` / 5 `changed 0`
  in `main`. [read]
- **homescreen removal:** see boot_timing.md; caller unlogged.
- **Box health (OCBM, gm_ccpa NETPROBE lines in `main`):** `BOX_HEALTH` normally `0x59
  [HCI|carplayd|btd|rootfs-ok]` (only 4 of the 29 retained BOX_HEALTH lines; recount 2026-11-12: `0x59` x4, `0x51` x11, `0x50` x4,
  `0x41` x4, `0x40` x6, of which only 3 carry `(replay)`: 06:09:41, 06:11:37, 06:13:36; the other 3 at 06:14:31, 06:55:26, 06:56:01 do not; corrected 2026-11-12, previously stated all 6 as replay). `0x51 [HCI|btd|rootfs-ok]` (carplayd bit clear) appears 11 times: 3 around the 11-11 18:16
  shutdown, 5 at 11-12 06:09-06:14 (06:09:49, 06:11:51, 06:13:49, 06:14:28, 06:14:35) and 3 at 06:55-06:56 (06:55:22, 06:55:28, 06:56:05) [2026-11-12 correction: was stated 3/4/4; recounted from the merged `main` log, total 11 unchanged], so the 18:16 coincidence is only part of it. Not proven causal. [read]
- **VHAL:** `VHAL-STATS: Frame 0x16 not handled, count 232025` (and many other unhandled frame ids)
  is routine in `main`; unhandled frames are the norm, not an error signature. [read]

## Bench: SoftAP / WLAN stuck off after `adb reboot` (owner, 2026-10-06)
On the bench, the WiFi SoftAP (br0 `192.168.5.1`) is not reliably brought up by the system process
after an `adb reboot` — it can stay stuck off, and **a full power cycle is required** to restore the
WLAN/SoftAP (an `adb reboot` alone does not fix it). Consequence for research: any SoftAP/CarPlay-AP
network probe must be done after a power cycle with the AP confirmed up (ideally during a live CarPlay
session). Pairs with the other post-reboot bench quirks: ADB auto-disables at boot (manual re-enable
via Dev-options/USB re-plug) and the clock resets (`adb_enabled` + time wiped at boot — the
workstation-sync hook re-corrects time on next adb use). Wired/loopback/binder testing over ADB is
unaffected by the SoftAP state.

## Y177 Notes

- **SELinux:** stock Y177 boots **Enforcing**, same as Y175/Y181. The long-held "Y177 runs permissive" belief is refuted — `system/bin/init` is byte-identical across Y175/Y177/Y181 and compiles with `ALLOW_PERMISSIVE_SELINUX=0`, so it ignores `androidboot.selinux=permissive` and forces Enforcing at runtime; any live permissive Y177 was a modified/eng unit. (confirmed: `aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_OS_PARTITION_INVESTIGATION_AUG2026.md:145`)
- **VIP security function:** Y177 carries the full ~906-byte validator (@0xb67d4), same as Y175 (@0xb6708) / Y181 (@0xb67d0). The "4-byte stub" was a fixed-address misread, refuted by a three-way byte-level VIP_APP diff — there was no VIP regression, and the function gates ADB/seed auth only, not SELinux or AVB.
- CVE-2024-53104 and CVE-2024-36971 are kernel CVEs against the 4.19.305 kernel shared by Y177 and Y181 — not Y177-specific.

---

**Data sources:** `/Volumes/POTATO/logcat/20260219/`, 3.7GB logcat corpus (27 files, Feb 11-19, 2026)
