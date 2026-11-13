# GM Info 3.7 Memory Pressure Analysis

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (27 files, Feb 11-19, 2026), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## System Memory

- 8 GiB LPDDR4 physical (4× 2 GiB Micron MT53E512M32D2DS-053) [teardown]. GHS grants the Android guest 7830 MiB DRAM (+34 MiB read-only IPU frame window) [FW 85098662; 3-Opus verified 2026-10-10] and reserves ~362 MiB below 4 GiB (kernel + 19 servers + PMRs).
- Kernel-visible: historical `MemTotal` ~5,663,43x kB = 5530 MiB (5.40 GiB, 5.80 GB decimal) [/proc/meminfo, Y175/Y181; varies slightly per capture]. **Updated 2026-11-12:** the Y181B recovery export supplies an E820 usable total of **5743.55859375 MiB** and early Linux `Memory: 5638316K/5877304K available` (second export: 5638324K available). These early values are not a new normal-AAOS `MemTotal` measurement. The cause of the difference from the 7830 MiB static grant remains unresolved; the old 5780 MiB/RAM4-cap proposal is unconfirmed. [Map, sources and limits](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory).
- **`SwapTotal: 0` — no swap.** The LMK/OOM killer is the only relief valve under pressure.
- Available at boot: ~3.1GB (debloated) vs ~2.5GB (factory); load avg ~5-7 (debloated) / higher on factory
- Full debloat-vs-factory study: see [`analysis/debloat_vs_factory_analysis.md`](../analysis/debloat_vs_factory_analysis.md)

## LMK (Low Memory Killer)

- Uses PSI (Pressure Stall Information) monitors
- threshold_ms=100 for levels 1 and 2
- **513 total kills across 27 logcat files**
- Per-file range: 2 to 119 kills per session
- Worst session: logcat_20260214_182011.log with 119 kills (factory config)
- Max thrashing ratio: 3,700% (com.gm.teenmode)
- Settles to stable state within ~30s

### LMK Kill Reasons

- **"low watermark breached"** — majority of kills
- **"min watermark breached"** — severe memory pressure
- **"device is not responding"** — 19+ occurrences; victims at oom_adj=200: gmcarmediaservice (4x), alexa (2x), vac, hvac, inputmethod

### Y181B re-check (live + retained logs, 2026-11-12)

- Live `/proc/meminfo` on the bench radio: `MemTotal: 5663432 kB`, `SwapTotal: 0` -- identical to the
  historical 5,663,43x kB figure above, so the guest-visible total is stable on build
  `W231E-Y181.3.2-SIHM22B-499.3`. `MemAvailable` ~3.1 GB shortly after boot (uptime ~13 min). [read, live]
- Retained `main` log (2026-11-11 18:11 to 2026-11-12 13:10, the later boots of the 30 recorded; recount 2026-11-12 confirmed 25): only **25** `lowmemorykiller: Kill` lines (23 `low
  watermark is breached`, 2 `device is not responding`), all at `oom_score_adj` 975-999 (cached
  apps: `com.google.android.onetimeinitializer`, `configupdater`, `car.setupwizard`, Maps
  `server_recovery_process`, Templates Host, `com.gm.hmi.settings`). No `min watermark` kills and no
  `zeno.gmccpa` / foreground-app victim. This is a far lighter profile than the February 513-kill corpus
  (that corpus included the factory config and streaming sessions); the two are not comparable samples
  and the 25 should not be read as a new per-boot rate. [read]
- LMK still starts with `Using psi threshold_ms=100 for level=1/2`. [read]
- gm_ccpa runs inside the `android.car.usb.handler` process (pid name `android.car.usb.handler/u10a123`,
  uid 1010123 as user 10), so its memory is accounted under that process, not a `zeno.*` process name.
  The `zeno.carlink` thread/PSS table below is from the February CPC200 rig and has **not** been
  re-measured for gm_ccpa. The earlier note that "the package was not installed at the time of the live check"
  conflicts with the retained logs, where package `android.car.usb.handler` (gm_ccpa) was added 2026-11-10 17:06 and
  has `am_proc_start` entries through 2026-11-12 13:04 with no removal; the check probably looked for the name
  `zeno.gmccpa` rather than the package name. Live install state not re-read in the 2026-11-12 audit (no adb device attached).

## Debloat Analysis (CarLink Streaming vs Factory)

- Factory idle: HOTTER and HIGHER CPU load than debloated during CarPlay streaming
- 36 packages removed: 34% fewer packages, 36% fewer services
- Memory: debloated 3.1GB free at boot vs factory 2.5GB
- Google Services: ~443MB acting as LMK cushion
- CarLink memory: 76.6MB idle, 127.2MB peak, 38.6MB post-trim; NEVER killed by LMK
- Factory: 8 ALSA underruns, 4 Davey! events (worst 225s!); debloated: 0 underruns, 0 Davey!

## Streaming Session Resource Profile

Measured on the IHU during an active third-party CarPlay-adapter streaming session
(test rig; the adapter's own hardware/firmware is documented separately at
https://github.com/lvalen91/CPC200-CCPA_resources). Captured Feb 2026; source phone iPhone 18,4, iOS 26.4 beta
(build 23E5207q), CarPlay source version 940.19.1.

**Thread architecture (zeno.carlink during streaming):**

| Thread | Priority | Nice | CPU% |
|--------|----------|------|------|
| AudioPlayback | 1 (RT) | -19 | 3.8 |
| USB-ReadLoop | 10 (RT) | -10 | 5.7 |
| H264-Feeder | 16 | -4 | 3.8 |
| MediaCodec_loop | 10 (RT) | -10 | 1.9 |
| CodecLooper | 4 | -16 | 1.9 |

- Process: 58MB PSS / 178MB RSS, oom_adj 0 (foreground), 33-39 threads.
- AudioFlinger write latency (`bus0_media_out`): avg 69.6ms, std 3.0ms, min 57.4ms, max 118.5ms.
- System CPU during streaming: system_server 51%, pulseaudio 21%, surfaceflinger 16%, avb_streamhandler 14%.
- Connection reliability over the session corpus: 147/155 successful (94.8%), ~4s connect time,
  AirPlay video latency ~75ms, CPU 31-33°C.

## Crash Analysis

12 FATAL EXCEPTION events found across 3.7GB logcat corpus (3 distinct bugs):

1. **com.google.android.configupdater:** PendingIntent FLAG_IMMUTABLE crash (8 occurrences, non-fatal, restarts silently). Android 12 PendingIntent mutability enforcement — Google never patched this for AAOS.

2. **zeno.carlink:** MediaBrowserService session token crash (2 occurrences). Symptom of a structural AAOS limitation, not an isolated app bug. `MediaBrowserServiceCompat.setSessionToken()` is one-shot per Service lifetime — once set, a second call throws `IllegalStateException: The session token has already been set`. Carlink's `CarlinkManager.initialize` triggered this on display-mode reinit; guarded with a static `mediaSessionToken` + `updateSessionToken()` to prevent the double-set. The deeper issue (third-party app session destruction stranding the cluster on a dead token until reinstall/reboot) is structural and cannot be fully fixed from third-party scope. See `known_issues.md` § "Third-Party Media MediaSession Token Mismatch" for the full picture.

3. **com.google.android.apps.automotive.templates.host:** ForegroundServiceStartNotAllowedException (2 occurrences). Boot race condition — `BootCompleteReceiver` calls `startForegroundService` when not yet allowed. Google AAOS platform bug.
