# CPC200-CCPA Adapter — moved

The CPC200-CCPA wireless CarPlay adapter (Carlinkit A15W) is documented in its own repo:

**→ https://github.com/lvalen91/CPC200-CCPA_resources**

Adapter-internal facts (firmware `2025.10.15.1127`, iMX6UL kernel, NXP IW416 WLAN,
WiFi/BT firmware blobs, USB VID/PID `0x1314`/`0x1521`, AirPlay/web-server versions, box
identity JSON, and the **two observed hardware revisions WR2C and WN16**) now live there —
see `documentation/01_Firmware_Architecture/hardware_revisions.md` for the revision split.

The **gminfo-platform** measurements that were previously in this file (how the GM Info 3.7
IHU behaves while a third-party CarPlay adapter streams) were retained in gminfo, in their
topical docs:

| What | Now in |
|------|--------|
| Streaming thread/CPU/memory profile, AudioFlinger latency, connection reliability, test phone | `runtime/memory_pressure.md` § Streaming Session Resource Profile |
| CarLink MediaBrowserService session-token crash (exact stack frames) | `runtime/known_issues.md` § Third-Party Media MediaSession Token Mismatch |
| Adapter AAC stream identifiers (`type 102`/`audioFormat 8388608`, Siri `aot=39`/480 frames) | `audio/carplay_audio_pipeline.md` § AAC Formats |
| VC-1 `video/x-ms-wmv` boot role-mismatch note | `video/video_codecs.md` § VC-1/WMV Decoder |
| Video header layout, PTS handling, CSD SPS/PPS sizes, native-vs-adapter comparison | `video/pts_timing_strategies.md`, `projection/carplay_vs_android_auto.md` |

> Retained as a redirect (not deleted) so existing links resolve. Nothing was lost — every
> fact from the prior version was verified present in the CCPA repo or one of the gminfo docs
> above before this file was reduced to a pointer.
