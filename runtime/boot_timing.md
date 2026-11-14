# GM Info 3.7 Boot Timing Analysis

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (27 files, Feb 11-19, 2026), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## Y181B induced incomplete startup (2026-11-12)

The [recovery-export experiment](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#221-y181b-failed-boot-threshold-verified-2026-11-12)
was followed by removal of `com.gm.homescreen` (operator-observed; `deletePackageX` is logged for user 10
only, see the attribution note below). Retained Android logs report
the missing package for both users and `No home screen found`, even though
PLSS reports `reportHMIReady` and Android delivers `BOOT_COMPLETED` during
the affected startup. Those signals are not interchangeable with usable HMI
or GHS-accepted startup completion. The failed health/readiness condition
joining this experiment to the GHS counter remains untraced. Do not mix these
deliberately incomplete runs into the healthy-boot timing sample below.
Recovery's 2011/2010 clock resets and overlapping rotations also require
boot-relative timing and state-based ordering rather than wall-clock deltas.

### Attribution note on the homescreen removal (live logs, 2026-11-12)

Retained `system`/`main` logs (gmlogger rotation set pulled from the bench radio on 2026-11-12) show
`ActivityManager: Force stopping com.gm.homescreen appid=1000 user=10: deletePackageX` **twice**, at
13:04:07 and 13:04:48 (two different system_server boots inside the 13:03-13:10 reboot cluster), each
followed by `Force stopping ... user=10: pkg removed` / `PACKAGE_REMOVED`. Only **user 10** appears in
the `deletePackageX` lines; `user 0` appears only as
`CarPackageManagerService: com.gm.homescreen not installed! User Id: 0` (13:04:51, same cluster) plus
`WindowManager: No home screen found for Intent` (13:05:24, 6 lines across main+system). The log does
**not** name the caller of the delete, so tying it to the recovery-export experiment above rests on
timing alone [read: system.log/main.log; inferred: the attribution]. A live `pm list packages -u` at
2026-11-12 ~14:00 AKST was recorded here as showing no `com.gm.homescreen` for either user; the 2026-11-12 audit's
later ground-truth check has the package **present** on the radio (the adb device was not attached during
this audit pass, so neither state was re-read). Treat the live state as time-dependent and re-check before relying on it.

## Y181B 29-boot sample (retained logs, 2026-11-10 to 2026-11-12)

> Scope (2026-11-12 audit): the history log records 30 boots in this window; the `events` log covers 29 of them (the 30th began ~1 s before the dump was frozen) [2026-11-12: INFERRED, not measured; forensic reference tags it 0.5-0.6 confidence] and `main`/`kernel` cover only the later boots (`main` from 2026-11-11 18:11).

Build `W231E-Y181.3.2-SIHM22B-499.3`. Source: `events` log set (`all_events.txt`, `boot_progress_*`
EventLog tags; kernel-relative ms) plus `ghs.log` (GHS `Lifecycle`/`Audio`/`Camera` lines).
Wall-clock stamps in these logs are unreliable (clock is set late each boot); use the
kernel-relative values.

| Stage (ms from kernel start) | Y181B, n boots | Min | Median | Max |
|---|---|---|---|---|
| boot_progress_start | 29 | 4417 | ~4490 | 4700 |
| pms_ready | 28 | 12147 | ~12700 | 13143 |
| ams_ready | 28 | 15464 | ~16100 | 16799 |
| enable_screen | 27 (26 steady-state) | 22088 | 23512 | 25142 |

> [2026-11-12 footnote: `pms_ready`/`ams_ready` n=28 because the first post-flash outlier is dropped (raw n=29; raw `pms_ready` max 16973). The `enable_screen` row mixes bases: median 23512 is over all 27 boots (outlier 59795 included), min/max 22088-25142 are over the 26 steady-state boots; the 26-boot median is 23510 ms. Reproduced from the `events` logs.]

- Exception: the first post-flash boot is an outlier at `enable_screen` 59795 ms (`pms_data_scan_start`
  16604, `ams_ready` 44985; dexopt/first-run work [2026-11-12: this cause is an inference from the late `pms_data_scan_start`/`ams_ready`, not logged directly]), so the 22.1-25.1 s window applies to the 26
  steady-state boots only. This widens the February 5-boot range (22.0-24.1 s) slightly at the top; the
  ~23-23.5 s typical value is unchanged.
- The Phase 1-4 pre-kernel figures above remain **estimates**; the retained logs do not time them.
- `boot_progress_start` of ~4.4-4.7 s is also a little higher than the 4.27-4.46 s February sample.
- Early-boot services unchanged: `lowmemorykiller` (PSI, `threshold_ms=100` for levels 1 and 2) starts
  before `system_server`.
- **No watchdog backstop:** `watchdogd: Failed to open /dev/watchdog: No such file or directory`
  appears in the kernel log of every boot (first at ~4.5 s), and `/dev/watchdog*` is absent on the live
  radio (`ls /dev/watchdog*` -> No such file). `carwatchdogd` is running (Android car watchdog), but
  no hardware watchdog node exists in the guest.
- **Shutdown reasons are mixed:** `ghs.log` records 56 `Lifecycle: ShutdownReason` lines (logged twice per
  boot block, so 28 blocks; `ghs.log` has 29 "Logging started" headers, one a 10-line stub): `0x00` x22,
  `0x23` x10, `0x37` x24 lines (i.e. 11 / 5 / 12 blocks; the newer `ghs_new` copy adds a 30th block with `0x23`).
  PLSS_PMSvc `onReadShutdownReasonLogResponse` logs the same kind of value as "last power cycle reason" with
  a boot counter, i.e. it describes the **previous** cycle as seen at the start of this boot (`0x37` on boots 2-12 and 29,
  `0x00` on boots 13-20, 23, 25, 26, line absent on others). Correlation with how the previous boot ended
  (from the next boot's bootstat reason): `0x00` blocks follow boots that ended via the Android/PLSS shutdown path
  (`SHUTDOWN_PREPARE` + `RequestShutdown`, e.g. 11-11 18:15 `carwatchdogd: Received SHUTDOWN_PREPARE power cycle`);
  `0x37` blocks mostly follow boots whose next-boot reason is `cold` (no persisted shutdown reason, no shutdown
  path in the logs); `0x23` blocks follow boots that ended as `recovery`, `reboot,shell` (init reboot path, boots 26/27)
  and once an init `shutdown` (boot 29 -> block 30), so `0x23` is **not** simply "abrupt". The earlier wording that
  `0x23` boots end abruptly is withdrawn. **The meaning of `0x23` and `0x37` is not documented anywhere in the
  evidence** [inferred grouping only; forensic G2].
- **BOOT_COMPLETED latency** (`bootup.log`, user 0 post, n=28): min 19.7 s, median 20.5 s, max 56.8 s (first post-flash boot); next largest 25.9 s (boot 26). Measured from the log's own BOOT-TIME baseline, whose origin is not stated.
- No `FATAL EXCEPTION`, kernel panic, or `ANR in` line exists in the retained `main`/`system`/`kernel`
  logs (0 hits each; `tombstone` hits are only a `FileNotFoundException` for `/data/tombstones/tombstone_00`
  and the logger waiting on the directory). This is **weak evidence**: 8 collector files (`crash.log`, `GMCrashLog.log`, `Dumpstate.log`, ...) are 0 bytes, `tombstones/` is empty, and the ramoops/pstore content from previous boots was not captured.
- **Dirana DSP firmware load (ghs.log `Audio:`):** `Failed DSP Firmware Prepare` x57 (iteration 0 x28,
  1 x28, 2 x1) against 28 `DSP Firmware loading successful` lines (27 with `total attempts: 0x3`, one
  with `0x4`). Every complete boot reaches a successful load after 2-3 failed prepares, so the retry is
  normal for this build, not a fault.

## Y175 Ethernet-capture boot timing (2026-11-13)

**[C] Additional measurement, separate from the display/screen-based samples below.**
A clean, isolated power-on capture began with `tcpdump` already running and the radio
confirmed fully off. The Android guest kernel's boot-start wall-clock epoch was computed
from an ADB-shell `/proc/uptime` reading at a known wall-clock moment
(`boot_epoch = now - uptime`). The capture's absolute `frame.time_epoch` timestamps
(decoded with `tshark`), rather than capture-relative times, supplied the frame epochs.

| Observed event | Time from computed Android guest kernel start |
|---|---|
| Android guest kernel boot start (computed reference) | T+0 |
| First radio-sourced Ethernet frame, any traffic | T+2.25 s |
| First VLAN 2 / AVB frame | T+3.08 s |

These are compatible with the existing [kernel-to-screen figures](#android-boot-timing-5-boot-sample):
network initialization well before the screen appeared was consistent with that later
display milestone. This additional Ethernet measurement did not correct or replace the
screen-based results or validate the estimated pre-kernel phases.

**[?] OPEN QUESTION — Android guest versus GHS attribution.** `/proc/uptime` described
the **Android guest's own kernel uptime**, not necessarily physical SoC power-on or
GHS INTEGRITY hypervisor uptime. Android was understood to run as a GHS-hosted partition
([partition evidence](../platform/vehicle_network.md),
[boot-chain analysis](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md)). It remained unresolved
whether GHS/another partition initialized the Ethernet switch and started traffic before
the Android guest kernel, or the guest's early kernel/driver initialization triggered it.
The latter interpretation could be consistent with a near-power-on reference, but the
measurement did not establish that equivalence. Earlier GHS traffic could lie at a smaller
delay from physical power-on, or at a negative offset from the guest-kernel reference;
the first captured frames above remained at positive offsets.

**[C] Partial attribution check:** every distinct Ethernet source MAC in the clean capture
was enumerated. Only the already-known Android-guest MAC and the Mac's two tap-adapter
MACs (capture-side noise) appeared; no distinct, unidentified third radio-side MAC appeared.
**[?] This was inconclusive:** GHS/another partition could share the Android guest's MAC
through the single physical switch resource, so MAC-level attribution could not identify
which partition triggered the traffic.

## Pre-Kernel Boot Phases (estimated)

| Phase | Description | Time Range |
|-------|-------------|------------|
| Phase 0 | Power On | T=0ms |
| Phase 1 | VIP MCU Boot (Renesas RH850/F1K) | T=0-50ms |
| Phase 2 | Intel CSE + ABL (UEFI bootloader) | T=50-200ms |
| Phase 3 | GHS Hypervisor Init (cal_hypervisor_startup_timeout_ms=300) | T=200-500ms |
| Phase 4 | AVB Verification (cal_soc_soh_timeout_msec=1500) | T=500-1500ms |
| Phase 5 | Android Full Boot (kernel start → screen enabled) | T=1500-24000ms |

Estimated total power-on to screen: ~25.5s (1.5s pre-kernel + ~23s Android boot).

## Android Boot Timing (5-Boot Sample)

All times in ms from kernel start. Sources: logcat 20260212 (3 boots), 20260218 (2 boots).

| Stage | Boot1 | Boot2 | Boot3 | Boot4 | Boot5 |
|-------|-------|-------|-------|-------|-------|
| boot_progress_start | 4273 | 4336 | 4412 | 4458 | 4300 |
| preload_start | 5341 | 5564 | 5675 | 5520 | 5411 |
| preload_end | 8609 | 8754 | 8977 | 8849 | 8769 |
| system_run | 9206 | 9379 | 9595 | 9455 | 9437 |
| pms_start | 10105 | 10283 | 10560 | 10349 | 10594 |
| pms_system_scan_start | 11064 | 11234 | 11592 | 11268 | 11718 |
| pms_data_scan_start | 12081 | 12229 | 12514 | 12206 | 12618 |
| pms_scan_end | 12100 | 12249 | 12533 | 12243 | 12652 |
| pms_ready | 12468 | 12582 | 12943 | 12548 | 12993 |
| ams_ready | 15764 | 15682 | 16159 | 16167 | 16531 |
| enable_screen | 22026 | 22903 | 22792 | 23290 | 24149 |

### Key Observations

- **Zygote preload:** 13,900 classes in ~2,900ms, 64 resources in ~42ms
- **Zygote to SystemServer fork:** ~140ms
- **preload_end to enable_screen:** ~13-15s (consistent across all boots)
- **Total kernel-to-screen:** 22.0-24.1s range, ~23s average
- 13 Davey! events during boot (all SystemUI), none during streaming

## Service Start Order (from logcat)

- **Early:** hwservicemanager, lowmemorykiller, vold, installd
- **Mid:** system_server, SurfaceFlinger, AudioFlinger
- **Late:** CarPlay services, OnStar, third-party apps

## Boot Storm

- 513 LMK kills total across 27 logcat files (see memory_pressure.md for details)
- Memory pressure settles after ~30s
- All GM services stable after ~45s
