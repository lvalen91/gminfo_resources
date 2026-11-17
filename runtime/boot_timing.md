# GM Info 3.7 Boot Timing Analysis

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (27 files, Feb 11-19, 2026), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## Native Linux 7.3.5 timing scope — 2026-11-17

Stable02 reaches USB shell and initializes the physical panel automatically;
no end-to-end cold-power-to-visible timing was measured for this image. BCM4359
firmware initialization occurs at about 62.9 seconds after kernel start, despite
the regulatory database now loading without missing/invalid-database errors.
Do not attribute that remaining Wi-Fi delay to the fixed regulatory-database
issue, or mix it with historical Probe05 IPU timeout or AAOS startup timings.
See [the stable02 evidence](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

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

## Synchronized RH850 UART and Ethernet power-on measurement (2026-11-14)

An owner-controlled radio power-on was observed with both readers armed in
advance: receive-only RH850 UART at **115200, 8N1**, and T1 Ethernet on the
Mac's connected USB adapter. The T1/USB equipment remained powered while the
radio was off. The readers observed approximately **258.823 seconds** before
the first UART bytes, with no frames from the previously identified radio
Ethernet source during that baseline. Acquisition and event decoding were
performed in memory; no raw UART or packet capture file was written.

The observation ended **240 seconds after the first received UART bytes**.
The live decoder processed **709,383 Ethernet frames**, of which **709,352**
matched the radio source, and **30,902 UART bytes / 537 parsed lines**.
Both readers closed and the UART's original settings were restored. These
are processed-event counts; packet-loss statistics were not retained.

The reference below is **first UART bytes received by the Mac**, not the
electrical 12 V edge or MCU reset release. UART events use Mac receive time;
Ethernet events use packet-capture timestamps on the same Mac clock. UART
serialization, USB buffering and scheduling introduce an unmeasured delay,
so the figures establish observed ordering rather than precise hardware
rail-to-rail timing. MCU bracketed uptime remains a separate timebase.

| Event | Time after first received UART bytes |
|---|---:|
| First UART bytes | +0.000 s |
| VIP firmware banner `2B.175.1.5` | +0.006 s |
| PLC `OnEntry_Startup` / `CSM_Startup` | +0.387 s |
| `evPowerModeOn` | +0.761 s |
| SoC power level `1` reported to RH850 | +0.966 s |
| SoC power level `2` reported to RH850 | +1.286 s |
| First matching radio Ethernet frame: IPv6 on VLAN 4 | +3.085 s |
| First PTP frame from that source | +3.645 s |
| First VLAN 2 AVTP subtype `0x05` / TSCF-classified frame | +3.901 s |
| First VLAN 2 AVTP subtype `0x02` / AAF-classified frame | +3.906 s |
| SoC power levels `3` / `4` reported to RH850 | +5.665 / +5.671 s |
| PLC `CSM_On` | +5.701 s |
| `ReportCalibrationState- 2` | +5.872 s |
| First VLAN 4 ARP request from radio source | +5.905 s |
| `SystemState=HmiInit` | +8.326 s |
| DHCP with vendor class `android-dhcp-12` | +20.519 s |
| First VLAN 5 ARP request from radio source | +20.578 s |
| `evHMIReady` | +21.172 s |
| `SystemState=Propulsion (0x6)` | +21.199 s |
| CarPlay-control discovery query | +28.191 s |

This establishes RH850 startup, then early SoC power-level responses, then
visible Ethernet and AVB transport, followed by HMI readiness. Network/AVB
activity preceded HMI readiness by roughly 17–18 seconds. The numerical SoC
power-level meanings were not decoded here and must not be relabeled as
specific GHS or AAOS startup milestones.

The result is consistent with an early SoC/GHS network path or an internal
audio endpoint using the onboard switch before the UI is ready. It does not
identify the component that initialized the switch/NIC, or establish that
AAOS had not yet started when the first frame appeared. DHCP and CarPlay
discovery are later userspace/network observations, not guest-kernel start
markers. No synchronized AAOS boot log, guest uptime reference or electrical
power-rail measurement was acquired in this observation.

The early-chime explanation has independent architectural support: the native
INTEGRITY image contains `Chimes_InitialTask`, `.chime_requester` code and
**71 embedded PCM WAV chime assets**, alongside `.audio_server` DSP/stream
control. See the [firmware map](../research/GHS_FILE_MAP_85098662.md) and
[native boot tasks](../platform/boot_chain.md). This places chime resources
outside the AAOS guest and supports availability before Android UI readiness.
It strengthens the GHS/native-audio hypothesis for the early AVB path, but
does not identify the producer or contents of the first observed AVB frames.
Those streams could include idle/silent transport; no specific chime request,
waveform or Bose-amplifier playback was correlated in this measurement.

**Static follow-up, 2026-11-14:** GHS has concrete PCI Ethernet registration
and Intel NIC setup routines, but also grants `GmEth` to Android Guest1
through its passthrough path. No GHS AVTP producer was tied to the first
captured frames. The early AAOS-kernel possibility therefore remains open;
see the [addressed code findings](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#ethernet-initialization-and-guest-ownership-code-trace-2026-11-14).

See the [A11 recovery and capture context](../diagnostics/diagnosticsd_routines_and_recovery.md#synchronized-power-on-follow-up-2026-11-14).
The earlier partial capture below remains a separate observation.

## Partial post-factory-reset Ethernet capture (2026-11-14)

The later `radio-en12-20261114.pcapng` is a partial post-reset capture: the
owner corrected T1 polarity during startup. Its 391.771-second duration
includes 186.628 seconds before the first radio-associated frame, followed
by about 205.143 seconds of radio traffic. Those initial 186.628 seconds
must not be reported as Android boot latency. No synchronized guest-uptime
measurement was taken for this capture.

Relative to the first radio-associated frame, Android DHCP Discover with
vendor class `android-dhcp-12` appears at +44.211 s and CarPlay-control mDNS
queries at +55.183 s. These are partial-capture network milestones, not
kernel-start or HMI-ready measurements. The three AAF-classified AVTP
streams remain present through capture end. The capture contains no TCP
sessions, Android logs or current factory-wipe reason. See the
[owning capture analysis](../diagnostics/diagnosticsd_routines_and_recovery.md#partial-post-factory-reset-ethernet-capture-2026-11-14).

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


## Mute-hold reset and adb reboot boundaries (2026-11-15)

**The captured mute hold supports an RH850 reset with orderly SoC shutdown.**
In the `inVehicle_Cal_Success` UART capture, a mute event at VIP uptime 76.122s
(line 3619) precedes `SWC Reset Button Press detected` at 86.121s (line 3753):
**9.999s**, consistent with a ten-second hold. The intervening continuous
button level is not fully logged, so the interval is evidence rather than a
complete electrical hold trace.

| Capture lines | Observed sequence | Interpretation |
|---|---|---|
| 3754–3756 | `evResetRequestCSM` → `SetShutdownAndResetCSM` → `IPC_ID_RequestShutdown` | VIP requests a coordinated SoC shutdown. |
| 3788–3790, 3798 | Power level 1, `SoC_ShutdownComplete`, then unmount request | Shutdown proceeds through the power/storage handshake. |
| 3818–3827 | Power level 0, unmount ACK, `SoC_UnmountComplete` | SoC completion is acknowledged before reset. |
| 3841, 3851, 3853 | `CSM Reset`; uptime 95.757s → 0.120s; `BRR_RESET_REASON_VIP_SOFTWARE` updated 3 | VIP/RH850 itself restarts; this exceeds an HMI-process restart. |

**VIP firmware confirms a sustained-condition timer, not a press counter.**
Y175 module85759599 function `0x78236` reads input signals `0xC72`–`0xC77`
and additional state. If their combined predicate is true and timer3 is
inactive, it logs `Mute buttons pressed` and arms the timer. While the timer
is active, valid samples do not reload it; a false predicate cancels the
active flag and remaining ticks. Exact meanings of all predicate inputs
remain partly untyped.

| Runtime function | Recovered behavior |
|---|---|
| `0x76FBA` | Loads the configured countdown and sets its active flag. |
| `0x78214` / `0x78220` | Reads active state / clears active state and remaining ticks. |
| `0x7861E` | Decrements active countdowns; expiry clears active state and invokes the timer callback. |
| `0x785AA`, index3 | Logs `SWC Reset Button Press detected`, then calls `0xB1558(2)` to store/dispatch the reset request. |

The UART mute message marks **timer arming**, not every held-state sample or
a distinct press/release pair. After expiry, a still-valid predicate can arm
again, consistent with the fifth mute message after the reset request
(capture line 3764). The 9.999s interval supports a ten-second configured hold,
but the initializer/calibration source and periodic tick interval remain
unrecovered: a literal `10000 ms` has not been statically proven. Repeated
300 ms IOCID41DB taps have no demonstrated cumulative effect, and its VHAL
path has not been shown to assert this VIP predicate.

Static provenance: module SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`;
extracted payload SHA-256
`c6b214a75b2139e344e796da46fb6a6ca23f2ca91a8a6b2ee9cf33fda389be55`.
The isolated RH850 little-endian image uses base `0x28000`; payload begins
at file offset `0x586`, so runtime address = file offset + `0x27A7A`.
These are static findings, with no live timer/input manipulation.

**Live CAN validation, 2026-11-16:** the descriptor table is indexed by the
Com signal ID, not by searching its typed-storage-index word. Signal C72 maps
to CAN `526`, DLC 8, b5 bit 7. Holding that bit with approximately 100 ms
repetition, other payload bits zero and original 145/529 active, produced
`Mute buttons pressed` at VIP 89.527 s and `SWC Reset Button Press detected`
at 99.525 s: **9.998 s**. The coordinated shutdown request followed immediately,
with SoC shutdown completion at 100.385 s and a subsequent VIP counter reset,
software-reset indication and new startup. The trial ceiling was 20 s; the
input was released as soon as reset was detected. No extra guard-message
mutation, calibration clear or diagnostic ECUReset was used. This supersedes
the earlier static-only boundary for this specific input and current bench
state; the configured initializer/tick derivation remains unrecovered.
See the [CAN campaign](../platform/can_network.md#expanded-validation-campaign--2026-11-16).

The exact GHS shutdown/restart boundary was not observed. Distinct VIP and
SoC reset domains and `plmanager` coordination prevent assuming that every
restart command has the same scope.

**Ordinary `adb reboot` enters Android init; its downstream reset extent is
unmeasured here.** In normal Y175 adbd, `daemon_service_to_fd` matches
`reboot:` at ELF VA `0xB5334`, builds `/system/bin/reboot` plus its suffix at
`0xB54DC`, and calls `StartSubprocess` at `0xB555A`. The reboot executable's
`main` (`0x17D0`) selects default reason `shell` (`0x1895`) and calls
`property_set("sys.powerctl", ...)` at `0x18B7`–`0x18C3`. This establishes the
Android-init entry, not a definition of a “hypervisor-only” reset. The
[historical shutdown record](known_issues.md) contains
`sys.powerctl=reboot,shell`; it does not identify its caller or prove which
reset domains restarted. No live reboot was performed for this analysis.

Reproducibility: normal adbd SHA-256
`6bfa2ba86ab2fe2a0ca0e2eb588139bc6402f687822b72b9c6d2efecda0de713`;
`/os/system/bin/reboot` SHA-256
`d5f442bb26432f4c9abb1a5072131e81b8fde23ee25efe3ade9f02d422b8375c`.
A future comparison needs synchronized UART and Android logs: record the
`sys.powerctl` request, VIP uptime/reset reason, PLC shutdown/unmount handshake,
SoC boot markers and GHS restart evidence. An Android reconnect alone cannot
establish an RH850 reset.
