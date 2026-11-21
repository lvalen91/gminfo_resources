# Audio System Reference

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

## Document Index

| Document | Description |
|----------|-------------|
| [audio_subsystem.md](audio_subsystem.md) | Core audio system, AudioFlinger, buses, timing |
| [audio_codecs.md](audio_codecs.md) | Audio codec specifications (AAC, MP3, Opus, etc.) |
| [audio_effects.md](audio_effects.md) | Audio effects (Harman preprocessing, NXP bundle) |
| [automotive_audio.md](automotive_audio.md) | AAOS multi-zone architecture, policies, focus |
| **[carplay_audio_pipeline.md](carplay_audio_pipeline.md)** | **CarPlay/AirPlay bidirectional audio processing (CINEMO framework)** |
| **[intel_audio.md](intel_audio.md)** | **Intel IAS SmartX + SST audio architecture (no official docs)** |
| [../projection/carplay_vs_android_auto.md](../projection/carplay_vs_android_auto.md) | CarPlay vs Android Auto audio/video comparison |

---

## Quick Reference

### Hardware Summary

| Component | Specification |
|-----------|---------------|
| Audio HAL | Version 5.0 (`android.hardware.audio@5.0`, HarmanHAL) |
| Sample Rate | 48000 Hz (primary) |
| Format | PCM 16-bit |
| Channels | Stereo |
| Latency | ~24 ms |
| Output Buses | **8** CarAudioService buses (bus0–bus7) |
| Input Buses | HAL-internal (Harman routing graph) |
| Effects | Harman preprocessing + NXP bundle |

### Audio Bus Overview

| Bus | Purpose | Usage |
|-----|---------|-------|
| bus0_media_out | Media playback | MEDIA, GAME |
| bus1_navigation_out | Navigation | NAV_GUIDANCE |
| bus2_voice_command_out | Voice assistant | ASSISTANT |
| bus3_call_ring_out | Call ringtone | RINGTONE |
| bus4_call_out | Voice calls | VOICE_COMMUNICATION |
| bus5_alarm_out | Alarms | ALARM |
| bus6_notification_out | Notifications | NOTIFICATION |
| bus7_system_sound_out | System sounds | SONIFICATION |

> **bus0–bus7 above are the only Android CarAudioService output buses (8 total).** The entries below (bus8/11/12/13) are **Harman-HAL-internal routing-graph nodes** (`AudioRoutingConfigParser`), not CarAudioService output buses — apps cannot target them via `CarAudioManager`:

| bus8_ecall_ring_out | Emergency call (HAL-internal) | eCall |
| bus11_mix_unduck_out | Unduckable audio (HAL-internal) | Priority |
| bus12_audio_cue_out | Audio cues (HAL-internal) | System |
| bus13_high_priority_mutex_out | Safety alerts (HAL-internal) | Critical |

### Audio Codec Support

| Category | Formats |
|----------|---------|
| Music | AAC, MP3, Opus, Vorbis, FLAC |
| Voice | AMR-NB, AMR-WB, Opus, G.711 |
| Lossless | FLAC, PCM |
| Encoding | AAC, AMR-NB/WB, FLAC, Opus |

### Audio Effects

| Type | Effects |
|------|---------|
| Preprocessing | AEC, NS, AGC (Harman) |
| Playback | EQ, Bass Boost, Virtualizer, Reverb (NXP) |
| Utility | Downmix, Loudness Enhancer, Visualizer |

---

## Key Findings

### Architecture
- Android Automotive multi-zone audio architecture
- Harman preprocessing tuned for vehicle acoustics
- 8 CarAudioService output buses (bus0–bus7); bus8/11/12/13 are Harman-HAL-internal routing nodes, not app-targetable
- External DSP handles mixing and ducking
- 8ms mix period

### Audio Features
- External focus policy support
- Fixed volume mode (DSP-controlled)
- Automatic ducking via DSP
- Echo reference for AEC
- Multiple microphone sources

### Codec Notes
- All codecs are software-based (no hardware audio decode)
- Full AAC profile support including xHE-AAC
- Opus support for low-latency VoIP
- G.711 for telephony compatibility

---

## CarPlay/Android Auto Audio Configuration

### Key Difference

| Aspect | CarPlay | Android Auto |
|--------|---------|--------------|
| Framework | CINEMO/NME (Harman) | Standard AOSP |
| Audio Library | libNmeAudioAAC.so | MediaCodec |
| Telephony Tuning | Dedicated SCD files | Standard BT HFP |
| Protocol | AirPlay | AAP |

Both share the same AudioFlinger bus routing and Harman preprocessing.

See [../projection/carplay_vs_android_auto.md](../projection/carplay_vs_android_auto.md) for detailed comparison.

### Recommended Settings

```
Media Playback:
  Sample Rate: 48000 Hz
  Format: PCM_16_BIT
  Channels: Stereo
  Usage: USAGE_MEDIA
  Destination: bus0_media_out

Navigation:
  Sample Rate: 48000 Hz
  Format: PCM_16_BIT
  Channels: Stereo
  Usage: USAGE_ASSISTANCE_NAVIGATION_GUIDANCE
  Destination: bus1_navigation_out

Voice:
  Sample Rate: 16000 Hz
  Format: PCM_16_BIT
  Channels: Mono
  Usage: USAGE_ASSISTANT
  Input: Built-In Mic (with AEC/NS)
```

### Audio Focus

| Source | Focus Type | Ducking |
|--------|------------|---------|
| Media | GAIN | N/A |
| Navigation | GAIN_TRANSIENT_MAY_DUCK | Ducks media |
| Voice Assistant | GAIN_TRANSIENT_MAY_DUCK | Ducks media |
| Phone Call | GAIN_TRANSIENT | Ducks/pauses media |

> **Y181B measured, 2026-11-12 (gm_ccpa; `main` log):** a third-party CarPlay app on this radio requested
> media focus as `GAIN` / `USAGE_MEDIA` and voice focus as `GAIN_TRANSIENT` / `USAGE_VOICE_COMMUNICATION`
> (both `REQUEST_GRANTED` by `CarAudioFocus`), and captured the mic as `VOICE_COMMUNICATION` 16 kHz mono.
> The "Voice" block above lists `USAGE_ASSISTANT`. [2026-11-12 correction: this is not a mismatch. Recount of
> `requestAudioFocus` from uid 1010123 in the merged `main` log gives 10 calls: 7 `USAGE_ASSISTANT/CONTENT_TYPE_SPEECH`
> (`VoiceRouter`, the Siri path; first 06:30:16), 2 `USAGE_VOICE_COMMUNICATION/CONTENT_TYPE_SPEECH` (18:13:19 and
> 06:14:51) and 1 `USAGE_MEDIA` (06:14:44). The Siri sink is `AudioTrack(usage=16 = ASSISTANT)`, AAC-ELD 16 kHz mono
> (06:30:16); the call sink uses usage 2 (VOICE_COMMUNICATION). So both usages occur and `USAGE_ASSISTANT` for Siri is
> largely right.] Details in [carplay_audio_pipeline.md](carplay_audio_pipeline.md).

### Below-HAL Audio Architecture

Audio from the 8 CarAudioService output buses (plus the Harman-HAL-internal routing nodes) passes through several layers below the Android HAL barrier:

| Layer | Component | Detail |
|-------|-----------|--------|
| HAL | HarmanAudioControl (HarmanHAL) | `android.hardware.audio@5.0`, Dirana3 plugin ("Titan" is the SoC platform codename, not the HAL) |
| Mixing | PulseAudio | 34-channel combine sink (crossbar mixing) |
| Transport (I2S) | TDM output | 8ch s32le 48kHz → broxtontdf8532 codec |
| Transport (AVB) | Ethernet AVB | 6ch s16le 48kHz → csm_amp (amplifier) |
| Transport (AVB) | Ethernet AVB | 1ch s16le 48kHz → csm_tcp (telemetry) |
| Hardware | NXP TDF8532 | Audio codec → external amplifier → 4 speakers |

See [intel_audio.md](intel_audio.md) for the complete Intel IAS SmartX + SST architecture.

---

## System Properties

```properties
audio.safemedia.bypass=true
init.svc.audioserver=running
init.svc.vehicleaudiocontrol=running
```

---

## Data Sources

All specifications obtained from GM AAOS research data:

**ADB Enumeration (`/analysis/adb_Y181/`):**
- `dumpsys media.audio_flinger`
- `dumpsys media.audio_policy`
- `dumpsys audio`
- `dumpsys media.player` (audio codecs)

**Extracted Partitions (`/extracted_partitions/`):**
- `/vendor/etc/audio_policy_configuration.xml`
- `/vendor/etc/audio_effects.xml`
- `/vendor/etc/scd/*.scd` - CarPlay telephony configurations
- `/system/lib64/libNmeAudio*.so` - NME audio libraries (binary analysis)
- `/system/lib64/libNmeCarPlay.so` - CarPlay audio integration

**Binary Analysis:**
- `strings`, `readelf`, `nm` on NME libraries

**Source:** external GM_research corpus (`gm_aaos/`), not in this repo.
