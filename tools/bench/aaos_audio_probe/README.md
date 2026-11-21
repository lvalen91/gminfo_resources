# AAOS Audio Probe

Small native Java app for comparing public Android audio usages, audio-focus
admission, actual output routing and external T1 audio. No AndroidX, Gradle
dependencies, network permission, microphone capture or bundled audio assets.

Select any of the 16 public Android 12 usages, or attempt one of the five
system usages advertised by this radio. Choose stereo, left-only or right-only source PCM, focus gain and
1–20% signal amplitude. Play an eight-second probe or hold until Stop. Focus
loss and leaving the Activity stop playback and release focus. A duck request
reduces the signal; it does not modify global radio volume. The signal is
48 kHz stereo PCM, with a distinct frequency per usage and a 500 ms on /
250 ms off pattern with short fades.

The status panel reports the requested usage separately from the actual
AudioTrack route, audio session number, frames written and underruns. Route
addresses are shown only for named audio buses. The app does not change call
mode, force a device, set hidden vendor tags or request privileged car-audio
permissions. Public USAGE_ASSISTANT/VOICE_COMMUNICATION may therefore fall back
to the media bus or be refused by focus policy; the observed result is the
experiment, not an assumed dedicated-bus mapping.

## Build

Use an installed Android SDK (platform 32, build tools 35.0.0), JDK and existing
standard Android debug keystore. Paths can be supplied with ANDROID_SDK_ROOT,
AAOS_BUILD_TOOLS, AAOS_ANDROID_JAR, AAOS_JAVA_HOME and AAOS_DEBUG_KEYSTORE.
The existing keystore is used in place and never copied into this project.

```sh
~/.Codex/bin/bt bash research/tools/aaos_audio_probe/build.sh
adb -s <ADB_TARGET> install -r research/tools/aaos_audio_probe/build/aaos-audio-probe.apk
adb -s <ADB_TARGET> shell am start -n org.gminfo.audioprobe/.MainActivity
```

For bounded, repeatable bench tests:

```sh
adb -s <ADB_TARGET> shell am start -n org.gminfo.audioprobe/.MainActivity --es usage navigation --ei seconds 8 --ez autoplay true
adb -s <ADB_TARGET> shell am start -n org.gminfo.audioprobe/.MainActivity --es command stop
adb -s <ADB_TARGET> logcat -s AudioUsageProbe:I
```

Accepted usage keys: media, navigation, assistant, call, ringtone, alarm,
notification, system, unknown, signalling, request, instant, delayed, event,
accessibility, game, call_assistant, emergency, safety, vehicle_status,
announcement. Optional `--ei channel 0|1|2` selects stereo/left/right. System
choices use the system setter through reflection and still obey platform
permissions and focus policy; failures do not fall back to a public usage.
Command playback is bounded to 1–30 seconds. Pressing
Hold in the UI keeps playing until Stop, focus loss or Activity pause.

Compare the logged route and a live media.audio_policy/media.audio_flinger
dump with T1 AAF sample positions. Media was independently recovered from
positions 1/2 of a six-position PCM payload before this app was created; that
does not establish routing for the other usages. See the existing
[AVTP audio findings](../../../platform/avb_audio_transport.md#3-live-avtp-player-audio-recovery-2026-11-15).

## Bench validation 2026-11-15

The APK was built, installed and run on the owner's A11.
The native UI was inspected on its **2400×960 display**; usage, channel,
focus and amplitude controls, action buttons and route/status text rendered.
The last probe details remain visible after playback stops.

Four public-usage probes each received audio focus and wrote **192,000
stereo source frames** (four seconds at 48 kHz). Live T1 decoding observed
the corresponding signal in the 768-byte AAF payload stream:

| Public usage | Probe frequency | Actual AudioTrack route | Active six-position AAF payload positions |
|---|---:|---|---|
| Media, `1` | 440 Hz | `bus0_media_out` | 1, 2 |
| Navigation guidance, `12` | 660 Hz | `bus1_navigation_out` | 3 |
| Assistant, `16` | 880 Hz | `bus2_voice_command_out` | 1, 2 |
| Voice communication, `2` | 550 Hz | `bus4_call_out` | 1, 2 |

The 512- and 128-byte AAF payloads remained zero-filled in those test windows.
These results demonstrate usage-dependent routing within one transport
stream; they do not identify physical speaker assignments or establish
behavior during a real phone call. The expanded sweep subsequently exercised all 16 public usages in two-second
windows. Notifications, alarm and sonification activated position 4;
left-only/right-only media isolated positions 1/2. All 16 produced audio.
The two smaller streams stayed silent. All five system usage attempts were
refused audio focus (`focus_result=0`), producing no signal. The complete
usage/bus/position table and raw packet layout are maintained in the single
[VLAN 2 reference](../../../platform/avb_audio_transport.md#4-vlan-stream-inventory-and-packet-layout).
Existing bus processing can change wire amplitude; the app's 5% signal
setting is source amplitude, not a guarantee of equal output gain per bus.

Hold was exercised through the actual UI, then stopped through the Stop
button; the observed run wrote 126,144 frames with zero reported underruns.
A second held run stopped when Home caused Activity pause, releasing its
focus/track. Bounded playback completed at the requested frame count.
A final two-second run completed at **96,000 frames**, zero reported
underruns, with its route and counters still visible after stopping.

An attempted external focus-interruption test through the platform shell
returned `java.lang.IllegalArgumentException: packageName may not be empty`
from `cmd media_session dispatch play`. That automation did not exercise the
app's focus-loss callback. UI Stop, bounded completion and background-stop
were verified; forced external focus loss and ducking remain unverified.
Probe playback was explicitly stopped after this test.

Later repeat measurements had silent AAF payloads even during their known
media-probe windows, despite focus/AudioTrack route admission. They did not
establish a diagnostic-tone speaker map; the [owning VLAN2 follow-up](../../../platform/avb_audio_transport.md#6-diagnostic-tone-correlation-follow-up-2026-11-15)
records those limits. Do not equate an accepted AudioTrack or a vendor
Settings.Global tone readback with measured T1 output.

**User10 media-session control:** the platform `cmd media_session` shell
listing saw no sessions in user0, while the radio's active sessions belonged
to user10. A bounded app_process controller using
`ISessionManager.getSessions(null,10)` and per-token MediaController transport
controls worked. Construct its Context for `com.android.shell`; use direct
ISessionManager rather than constructing MediaSessionManager in app_process,
which lacked MediaFrameworkInitializer initialization. Direct Stop changed
the tuner from PLAYING3 to STOPPED1. A later tuner
`playFromUri(broadcastradio://program/AMFM_FREQUENCY/87700)` restored87.7MHz,
confirmed in native tuner logs, then Stop restored STOPPED1. A plain Play
request to the stopped local USB player left it STOPPED1; a selected playable
item remains a prerequisite. This helper did not request root, modify call
mode or change calibration.
