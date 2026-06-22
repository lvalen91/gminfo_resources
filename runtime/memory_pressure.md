# GM Info 3.7 Memory Pressure Analysis

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (27 files, Feb 11-19, 2026), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## System Memory

- 8GB LPDDR4 physical (~6GB allocated to Android guest)
- 5.66GB visible to kernel (~604MB reserved by GHS hypervisor); `MemTotal` ~5,663,424 KB (varies slightly per capture)
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
