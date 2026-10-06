# Third-Party App Access to Intel APIs

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Analysis Date:** December 2025 - February 2026

---

## Executive Summary

| API | Third-Party Access | Method |
|-----|-------------------|--------|
| **Intel Media SDK (Video)** | **YES** (indirect) | Standard Android MediaCodec API |
| **Intel IAS SmartX (Audio)** | **NO** | Below HAL barrier, not exposed |

---

## Video: Accessible via MediaCodec

### Overview

Third-party apps **CAN** use Intel hardware video codecs through the standard Android MediaCodec API. The Intel Media SDK (MFX) is abstracted behind Android's codec framework.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THIRD-PARTY VIDEO ACCESS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Third-Party App                                                    │
│       │                                                             │
│       │  Standard Android API                                       │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  MediaCodec.createDecoderByType("video/avc")                │   │
│  │                    or                                        │   │
│  │  MediaCodec.createByCodecName("OMX.Intel.hw_vd.h264")       │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                             │  Android automatically routes to:     │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  OMX.Intel.hw_vd.h264  (Hardware - preferred)               │   │
│  │          or                                                  │   │
│  │  c2.android.avc.decoder (Software - fallback)               │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Intel Media SDK (MFX) → VA-API → i965 → VPU                │   │
│  │  (Transparent to application)                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Available Codecs

| Codec | Component Name | Third-Party Access |
|-------|----------------|-------------------|
| H.264 Decode | `OMX.Intel.hw_vd.h264` | **YES** |
| H.265 Decode | `OMX.Intel.hw_vd.h265` | **YES** |
| VP8 Decode | `OMX.Intel.hw_vd.vp8` | **YES** |
| VP9 Decode | `OMX.Intel.hw_vd.vp9` | **YES** |
| VC-1 Decode | `OMX.Intel.hw_vd.vc1` | **YES** |
| MPEG-2 Decode | `OMX.Intel.hw_vd.mp2` | **YES** |
| H.264 Encode | `OMX.Intel.hw_ve.h264` | **YES** |
| H.265 Encode | `OMX.Intel.hw_ve.h265` | **YES** |
| H.264 Secure | `OMX.Intel.hw_vd.h264.secure` | **NO** (DRM only) |
| H.265 Secure | `OMX.Intel.hw_vd.h265.secure` | **NO** (DRM only) |

### Code Examples

#### Query Available Intel Codecs

```java
import android.media.MediaCodecList;
import android.media.MediaCodecInfo;

public List<String> getIntelCodecs() {
    List<String> intelCodecs = new ArrayList<>();
    MediaCodecList codecList = new MediaCodecList(MediaCodecList.ALL_CODECS);

    for (MediaCodecInfo info : codecList.getCodecInfos()) {
        if (info.getName().startsWith("OMX.Intel")) {
            intelCodecs.add(info.getName());
        }
    }
    return intelCodecs;
}
```

#### Create Decoder (Auto-Select Best)

```java
import android.media.MediaCodec;
import android.media.MediaFormat;

// Android will prefer hardware codec if available
MediaCodec decoder = MediaCodec.createDecoderByType("video/avc");

MediaFormat format = MediaFormat.createVideoFormat("video/avc", 1920, 1080);
decoder.configure(format, surface, null, 0);
decoder.start();
```

#### Create Decoder (Explicitly Request Intel)

```java
// Explicitly request Intel hardware decoder
MediaCodec decoder = MediaCodec.createByCodecName("OMX.Intel.hw_vd.h264");

MediaFormat format = MediaFormat.createVideoFormat("video/avc", 1920, 1080);
decoder.configure(format, surface, null, 0);
decoder.start();
```

#### Query Codec Capabilities

```java
import android.media.MediaCodecInfo.CodecCapabilities;
import android.media.MediaCodecInfo.VideoCapabilities;

MediaCodecList codecList = new MediaCodecList(MediaCodecList.ALL_CODECS);
MediaCodecInfo codecInfo = codecList.findDecoderForFormat(
    MediaFormat.createVideoFormat("video/avc", 1920, 1080));

if (codecInfo != null && codecInfo.getName().startsWith("OMX.Intel")) {
    CodecCapabilities caps = codecInfo.getCapabilitiesForType("video/avc");
    VideoCapabilities vidCaps = caps.getVideoCapabilities();

    // Check 4K support
    boolean supports4K = vidCaps.isSizeSupported(3840, 2160);

    // Check frame rate support
    boolean supports60fps = vidCaps.areSizeAndRateSupported(1920, 1080, 60);

    // Get bitrate range
    Range<Integer> bitrateRange = vidCaps.getBitrateRange();
}
```

#### Optimal Encoding Settings for GM AAOS

```java
MediaFormat format = MediaFormat.createVideoFormat("video/avc", 1920, 1080);

// Frame rate
format.setInteger(MediaFormat.KEY_FRAME_RATE, 60);

// Bitrate (15 Mbps recommended for 1080p60)
format.setInteger(MediaFormat.KEY_BIT_RATE, 15_000_000);

// I-frame interval (1 second)
format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);

// Color format (NV12 for hardware codec)
format.setInteger(MediaFormat.KEY_COLOR_FORMAT,
    MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar);

// Profile (High for better compression)
format.setInteger(MediaFormat.KEY_PROFILE,
    MediaCodecInfo.CodecProfileLevel.AVCProfileHigh);

// Level (4.1 for 1080p60)
format.setInteger(MediaFormat.KEY_LEVEL,
    MediaCodecInfo.CodecProfileLevel.AVCLevel41);

MediaCodec encoder = MediaCodec.createByCodecName("OMX.Intel.hw_ve.h264");
encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
encoder.start();
```

### Performance Specifications

| Resolution | Max FPS | Max Bitrate | Notes |
|------------|---------|-------------|-------|
| 3840x2160 (4K) | 60 | 40 Mbps | Full hardware acceleration |
| 1920x1080 (1080p) | 60 | 40 Mbps | Recommended for projection |
| 1280x720 (720p) | 60 | 40 Mbps | Lower latency |

### Limitations

1. **No Direct MFX Access** - Apps cannot call Intel Media SDK functions directly
2. **Secure Codecs** - `.secure` variants only available for DRM content
3. **Color Format** - Hardware codecs prefer NV12 (YUV420SemiPlanar)
4. **Surface Required** - Hardware decode typically requires output to Surface

---

## Audio: NOT Accessible

### Overview

Third-party apps **CANNOT** directly access Intel IAS SmartX, Intel SST, or audio routing. They must use standard Android AudioTrack/AudioRecord APIs.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THIRD-PARTY AUDIO ACCESS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Third-Party App                                                    │
│       │                                                             │
│       │  Standard Android API only                                  │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AudioTrack (playback)  /  AudioRecord (capture)            │   │
│  │  AudioAttributes.USAGE_MEDIA / USAGE_GAME / etc.            │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                             │  App has NO control over routing      │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AudioFlinger + AudioPolicyService                          │   │
│  │  (System decides bus based on AudioAttributes)              │   │
│  │                                                              │   │
│  │  USAGE_MEDIA        → bus0_media_out                        │   │
│  │  USAGE_ASSISTANCE   → bus2_voice_command_out                │   │
│  │  USAGE_NOTIFICATION → bus6_notification_out                 │   │
│  │  USAGE_VOICE_COMMUNICATION → bus4_call_out                  │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│              ═══════════════╪═══════════════════════════════════   │
│              BARRIER - Apps cannot access below this line           │
│              ═══════════════╪═══════════════════════════════════   │
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Intel Audio HAL (audio.primary.broxton.so)                 │   │
│  │  Intel IAS SmartX (libias-audio-smartx.so)                  │   │
│  │  PulseAudio                                                 │   │
│  │  AVB Stream Handler                                         │   │
│  │  Intel SST Kernel Drivers                                   │   │
│  │  Harman Audio Processing (SSE, AEC, NS, AGC)                │   │
│  │                                                              │   │
│  │  *** NOT ACCESSIBLE TO THIRD-PARTY APPS ***                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### What Apps CAN Do

| Capability | API | Notes |
|------------|-----|-------|
| Play audio | AudioTrack | Standard playback |
| Record audio | AudioRecord | Microphone access (with permission) |
| Set usage type | AudioAttributes | Affects routing decision |
| Set content type | AudioAttributes | Affects processing |
| Query capabilities | AudioManager | Sample rates, formats |

### What Apps CANNOT Do

| Capability | Reason |
|------------|--------|
| Select specific audio bus | AudioPolicy controlled |
| Access IAS SmartX APIs | Not exposed |
| Configure PulseAudio | System-level |
| Access AVB streams | Kernel-level |
| Modify preprocessing | Harman proprietary |
| Control Harman effects | System-level |
| Bypass AudioFlinger | Sandboxed |

### Code Examples

#### Optimal Audio Playback

```java
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;

// Set proper attributes for correct bus routing
AudioAttributes attrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_MEDIA)  // Routes to bus0_media_out
    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
    .build();

// Use native sample rate (48000 Hz for GM AAOS)
AudioFormat format = new AudioFormat.Builder()
    .setSampleRate(48000)  // Native rate - no resampling
    .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
    .build();

int bufferSize = AudioTrack.getMinBufferSize(
    48000,
    AudioFormat.CHANNEL_OUT_STEREO,
    AudioFormat.ENCODING_PCM_16BIT
);

AudioTrack track = new AudioTrack.Builder()
    .setAudioAttributes(attrs)
    .setAudioFormat(format)
    .setBufferSizeInBytes(bufferSize)
    .setTransferMode(AudioTrack.MODE_STREAM)
    .build();

track.play();
// Write audio data...
```

#### Audio Recording (with Permission)

```java
import android.media.AudioRecord;
import android.media.MediaRecorder;

// Requires RECORD_AUDIO permission
int sampleRate = 16000;  // Common for voice
int bufferSize = AudioRecord.getMinBufferSize(
    sampleRate,
    AudioFormat.CHANNEL_IN_MONO,
    AudioFormat.ENCODING_PCM_16BIT
);

AudioRecord recorder = new AudioRecord(
    MediaRecorder.AudioSource.MIC,
    sampleRate,
    AudioFormat.CHANNEL_IN_MONO,
    AudioFormat.ENCODING_PCM_16BIT,
    bufferSize
);

recorder.startRecording();
// Read audio data...
```

#### Usage Types and Bus Routing

```java
// USAGE_MEDIA → bus0_media_out
AudioAttributes mediaAttrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_MEDIA)
    .build();

// USAGE_ASSISTANCE_NAVIGATION_GUIDANCE → bus1_navigation_out
AudioAttributes navAttrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
    .build();

// USAGE_ASSISTANT → bus2_voice_command_out
AudioAttributes assistantAttrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_ASSISTANT)
    .build();

// USAGE_NOTIFICATION → bus6_notification_out
AudioAttributes notifAttrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_NOTIFICATION)
    .build();

// USAGE_VOICE_COMMUNICATION → bus4_call_out
AudioAttributes callAttrs = new AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
    .build();
```

### Audio Bus Routing (System Controlled)

| AudioAttributes.USAGE_* | Routed To | Notes |
|------------------------|-----------|-------|
| USAGE_MEDIA | bus0_media_out | Music, video |
| USAGE_GAME | bus0_media_out | Games |
| USAGE_ASSISTANCE_NAVIGATION_GUIDANCE | bus1_navigation_out | Nav prompts |
| USAGE_ASSISTANT | bus2_voice_command_out | Voice assistant |
| USAGE_NOTIFICATION_RINGTONE | bus3_call_ring_out | Ringtone |
| USAGE_VOICE_COMMUNICATION | bus4_call_out | Phone calls |
| USAGE_ALARM | bus5_alarm_out | Alarms |
| USAGE_NOTIFICATION | bus6_notification_out | Notifications |
| USAGE_ASSISTANCE_SONIFICATION | bus7_system_sound_out | System sounds |
| USAGE_UNKNOWN (audio cue) | bus12_audio_cue_out *(HAL-internal, not a CarAudioService bus)* | Audio cues |

### Optimization Tips

1. **Use Native Sample Rate (48000 Hz)** - Avoids resampling overhead
2. **Set Proper AudioAttributes** - Ensures correct bus routing
3. **Use Appropriate Buffer Size** - Balance latency vs stability
4. **Request Low Latency** - Use `AudioTrack.PERFORMANCE_MODE_LOW_LATENCY` if needed

---

## Comparison: Video vs Audio Access

| Aspect | Video (Intel Media SDK) | Audio (Intel IAS SmartX) |
|--------|------------------------|-------------------------|
| **Third-Party Access** | YES (via MediaCodec) | NO |
| **Direct API Access** | NO (abstracted) | NO |
| **Hardware Acceleration** | YES (accessible) | YES (but transparent) |
| **Can Select Specific HW** | YES (`createByCodecName`) | NO |
| **Routing Control** | N/A | NO (AudioPolicy) |
| **Configuration** | MediaFormat | AudioAttributes only |
| **Documentation** | Intel SDK docs apply | N/A |

---

## SELinux Context

From analysis of `vendor_sepolicy.cil`:

```
# MediaCodec service can access Intel OMX components
(typeattributeset hal_omx (mediacodec))
(typeattributeset hal_omx_server (mediacodec))

# Third-party apps (untrusted_app) use standard Android APIs
# They don't have direct access to HAL or vendor services
```

Third-party apps are sandboxed as `untrusted_app` and can only access:
- Standard Android framework APIs
- Registered system services via Binder

> `[C] live-Y175 2026-10-05: REFINED — "registered system services via Binder" is too permissive
> for GM services. Live PoC on Y175: a sideloaded `untrusted_app` (`com.poc.gmwlan`, uid 1010121,
> user 10) attempting to resolve `com.gm.server.wlanservice` was **SELinux-denied** —
> `avc: denied { find } ... tcontext=u:object_r:gm_domain_service:s0 tclass=service_manager
> permissive=0` [avc_denials.txt, 23:19:07]. The service **is registered** (binder service #69,
> `gm.wifi.IGMWlanService` [services.txt]) yet a 3P app cannot even `find` it, let alone bind —
> the `gm_domain_service` SELinux type gates it off from `untrusted_app` regardless of registration.
> So the accurate statement is: a 3P app reaches standard framework services and only those GM/
> vendor binder services whose SELinux type permits `untrusted_app` service_manager `find` — the
> GM-domain services (wlanservice and siblings under `gm_domain_service`) are NOT among them.
> Separately CONFIRMED: no GM-owned permission contains `wifi`/`wlan`/`tether` and the two live 3P
> packages define/hold no permissions [permissions_full.txt], so WLAN-service access is also not
> pm-grantable — there is no permission to request and the binder path is SELinux-blocked. Both
> doors are shut on Y175.*

---

## Recommendations for Third-Party Developers

### Video Applications

1. **Use MediaCodec API** - Standard and portable
2. **Query Codec Capabilities** - Check what's supported before configuring
3. **Prefer Hardware Codecs** - Better performance, lower power
4. **Use NV12 Color Format** - Native format for Intel HW
5. **Target 1080p or 2400x960 at 30fps (matches GM CarPlay behavior; 60fps supported by HW)** - Optimal for GM AAOS display (2400x960)

### Audio Applications

1. **Use Standard AudioTrack/AudioRecord** - Only option available
2. **Set Proper AudioAttributes** - Critical for correct routing
3. **Use 48000 Hz Sample Rate** - Native rate, no resampling
4. **Don't Fight the System** - Accept AudioPolicy routing decisions
5. **Test on Actual Hardware** - Audio behavior varies by OEM

---

## Exported Components & Open Content-Provider Hooks (firmware-verified 2026-06-06)

Enumerated by extracting all 259 system+product APK manifests from Silverado Y181 (module
86331654=system, 86331636=product) and cross-checked against CT5/AAOS 14 (`Radio-IVE-86384258`).
These are reachable by an unprivileged third-party app. Two classes: **orphaned authorities**
(referenced-but-unregistered → a 3P app can *claim* them) and **exported-no-permission**
components (a 3P app can *bind/read/write/spoof* them).

> `[C] live-Y175 2026-10-05: this entire subsection is **Y181-SCOPE-ONLY** — sourced from Y181/CT5
> APK manifests; no APK/manifest extraction exists in the Y175 live capture, so the exported/
> claimable status of these specific components is UNVERIFIABLE-FROM-LIVE on Y175. What live Y175
> does confirm: the owning packages exist (`com.gm.vmsplugin`, `com.gm.domain.server.delayed`,
> `com.gm.rhmi`, `com.gm.rsicc`, `com.gm.hmianalytics`, `com.gm.ddb_contentprovider` are all in
> `pkg_system` [pkg_system.txt]). IMPORTANT distinction for the reachability claim: the live SELinux
> `find`-denial PoC (above, §SELinux Context) is on the **service_manager/getService** path
> (registered binder services like `wlanservice`), which is a *different* IPC path from
> `bindService` on an exported app `<service>` component (NavigationClusterService et al., routed via
> ActivityManager). The live denial neither validates nor refutes the exported-component claims here
> — they remain Y181-manifest-asserted and untested on Y175. Do not mark them confirmed on Y175.*

### Orphaned / claimable ContentProvider authority

| Authority | Owner (references it) | State | Notes |
|---|---|---|---|
| `com.google.android.apps.automotive.templates.host.ClusterIconContentProvider` | GoogleTemplatesHost (`com.google.android.apps.automotive.templates.host`) | **Referenced in code, registered in NO manifest** (both gminfo37 AND CT5) | Authority computed as `getPackageName()+".ClusterIconContentProvider"`; the host's prebuilt omits the `<provider>`. Any 3P app may declare it. On gminfo37 this delivers cluster maneuver icons (carlink's `ClusterIconShimProvider`); on CT5 it is open but bypassed by VMSPlugin enum forcing (see `projection/cluster_navigation.md`). Bidirectional risk: exfiltrate maneuver-icon bitmaps passed to `insert()`, or inject images via `query→contentUri→openFile`. |

No other referenced-but-unregistered authority surfaced.

### Exported `<provider>` with no/weak permission (registered, so NOT claimable — but readable/writable)

| Provider | Package | Authority | Notes |
|---|---|---|---|
| `MapsContentProvider` | `com.gm.vmsplugin` (system uid, priv-app) | `google_maps_settings;google_maps_assisted_driving` (CT5 also `google_maps_vehicle_profile`) | **Highest interest** — system-uid, exported, fully unprotected; exposes the Maps↔cluster settings / assisted-driving bridge. |
| `NavStateImageProvider` | `com.google.android.apps.maps` | `com.google.android.apps.maps.car` | Google's own nav-state image provider, exported/no-perm. |
| `FavoritesContentProvider` | `com.gm.favoritesprovider` | `com.gm.favoritesprovider` | Destinations/favorites store. |
| `DbContentProvider` | `com.gm.hmianalytics` | analytics DB | |
| `DeviceConnectionProvider` | `com.gm.ddb_contentprovider` | device-connection state | |
| `RseProvider` | `com.gm.rsicc` | `com.lge.rseprovider` | |

**NOT open:** `com.gm.gtbt.maneuver.provider` (`ManeuversContentProvider`) and `com.gm.tbt.commonprovider` declare no `android:exported` → default `false` (closed).

> `[C] live-Y175 2026-10-06` — **ContentProvider reachability IS live-testable on Y175** (unlike the
> exported `<service>` components above, which route via ActivityManager `bindService` and remain
> Y181-manifest-only). Measured from `gm_bench_agent` `prov.query` as uid 1010122 `untrusted_app`,
> **query() only — no insert/update/delete**:
> - **`DbContentProvider` authority is the FQCN `com.gm.hmianalytics.db.DbContentProvider`, NOT the
>   bare package `com.gm.hmianalytics`** (corrects the "analytics DB" placeholder in the table above).
>   Manifest (`com.gm.hmianalytics.apk`, Silverado decompile): `android:exported=true`,
>   `grantUriPermissions=true`, **no `android:permission`/read/writePermission**. Real paths from the
>   `UriMatcher` (`DbContentProvider.java:39-58`): `registry/REGISTRY_QUERY`(101),
>   `registry/REGISTRY_DB_QUERY`(103), `tasks/TASKS_QUERY_{ALL,ACTIVE,EXPIRED}`(207/201/202),
>   `acknowledgeReconcile/ACKNOWLEDGE_RECONCILE_QUERY`(401). Live Y175 result: every read path returns
>   `ok:true`, **no SecurityException** (reach-without-permission CONFIRMED), but `cursor:null` / **zero
>   rows** — no analytics data materialized on this bench (live build's `query()` returns null for these
>   codes; the decompile is the Y181 variant). The bare authority and the unmatched `registry`(102) path
>   also return null (not a crash). **Inert on Y175: reachable, no data leaked.** The named
>   `*_INSERT`/`*_DELETE`/`*_BULK` paths were never exercised and hit `default`→Unknown URI if reached via
>   query() anyway; `update()` is a no-op stub returning 0.
> - **[C] `FavoritesContentProvider` — unprivileged-readable exported provider, CONFIRMED live-Y175
>   2026-10-06 (two independent confirmations).** Authoritative manifest pull of
>   `/system/app/FavoritesProvider/FavoritesProvider.apk`: `<provider
>   android:name="com.gm.favoritesprovider.FavoritesContentProvider" android:exported=true
>   android:authorities="com.gm.favoritesprovider">` with **NO `readPermission`, NO `writePermission`,
>   NO `grantUriPermissions`, no path-permission** — hosted in a **system-uid** app
>   (`sharedUser=android.uid.system`). Independently, `untrusted_app` (harness) read **3 real rows** from
>   `content://com.gm.favoritesprovider/favorites` (+ `/favorites/#` row path), no permission prompt.
>   So **any sideloaded app can read the favorites DB with zero permission**, and — since there is no
>   `writePermission` — almost certainly **write/delete** it too (integrity; not tested — destructive,
>   harness-blocked). On this bench the rows were **audio-station presets (low sensitivity)**, but the
>   `GMFavoritesContract` exposes the same no-permission path for **`FT_DESTINATION_HOME` /
>   `FT_CONTACT_NAME` / `FT_PHONE_NUMBER`** → on a used unit this leaks a saved **home address, contact
>   names, and phone numbers** to any app (and allows tampering). Class: exported provider missing
>   permissions (CWE-926). Fix: add a `readPermission`/`writePermission` (signature or at least a
>   gated custom perm) or set `exported=false`. Evidence: `BENCH_AGENT_SWEEP_RESULTS.md` + the APK
>   manifest.

### Exported `<service>` / `<receiver>` with no permission (nav / cluster / OnStar / media)

- **`NavigationClusterService`** (`com.gm.domain.server.delayed`, `DelayedWKSApp`) — exported, no perm; directly named cluster-nav service, bindable by any app. Its `ServiceReadyBroadcastReceiver` is also exported/no-perm.
- **GMRHMIService** (`com.gm.rhmi`): `PhoneClusterPresentationService`, `AudioClusterPresentationService`, `ClusterPresentationBroadCastReceiver` — exported/no-perm; cluster presentation surface bindable/spoofable.
- **`com.gm.onstar.RESUME`** broadcast → `PauseResumeReceiver` in GMOnStarTBT (`com.gm.hmi.onstar`) — exported/no-perm; any app can pause/resume turn-by-turn guidance.
- **GMOnStar** (`com.gm.hmi.onstarui`): `OnStarMessageReceiver`/`ButtonReceiver`/`OnStarCallReceiver`/etc. + `OnStarCallService`/`AIFService` — exported/no-perm; OnStar call/button events injectable.
- **Media browser services, exported (by design) with no permission gate:** `com.gm.gmaudio.server` (`AudioMediaBrowserService`, `MediaSourceBrowserService`, …), `com.gm.domain.server.delayed` (`GmCarMediaService`, `LocalMediaBrowserService`, `CarPlayMediaService`, …), AOSP `CarMediaApp.MediaConnectorService`, Bluetooth `BluetoothMediaBrowserService`.
- **`com.onstar.vttproxyserver`**: `VehicleServerService` + `WebServerService` — exported/no-perm in-vehicle web/vehicle proxy (notable attack surface).

> CT5/AAOS 14 mirrors the same `ClusterIconContentProvider` orphan and the same `MapsContentProvider` / `NavStateImageProvider` exposure. See `projection/cluster_navigation.md` (2026-06-06 firmware-verified block). Extraction artifacts: `/Users/zeno/Downloads/misc/GM_research/gm_aaos/_cluster_authority_analysis/`.

---

## `prot=normal` GM vehicle/cluster perms are INERT for a 3P app — SELinux reach denies them (2026-10-06)

A sideloaded `untrusted_app` is auto-granted several GM `prot=normal` perms (`READ_VEHICLE_STATE`/
`READ_CLIMATE`/`READ_VEHICLE_INFORMATION`/`ACCESS_VEHICLE_DATA_SERVICE`/`READ_PROJECTION_INFO`) — PoC
#1 confirmed the grant — **but they are useless**: the permission gates the binder *call* while
SELinux gates the *reach*, and the reach is denied first (`ServiceManager.getService()` → `null`).
Variant Y181.3.2 labels/CIL; live-Y175 AVC corroborates the one positive control. Do **not** build a
3P feature on these perms.

| Data wanted | Backing service | Label | `untrusted_app` find? | Result |
|---|---|---|---|---|
| speed/gear/fuel/EV/odo/temp/climate/TPMS/ignition | `vehiclemanagerservice` (`IVehicleManagerService.getVehicleData`) | `gm_vehiclemanager_service` | **No** (only gmBugReport/gmConnection/system_app) | perms inert |
| CarPlay session/mute/route | PhoneProjection (`READ_PROJECTION_INFO`) | `gm_domain_service` | **No** (matches live wlanservice AVC) | blocked |
| cluster nav metadata | `clusterService` (`IClusterHmi`) | `gm_cluster_service` | **No** (system_app/graphic_dump only) | blocked |
| nav launch intents / nav-app metadata | `NavigationService` | `gm_domain_service_nav` | **Yes** (the ONLY gm_* find untrusted_app gets) | reachable, but push methods are `PROVIDE_NAV_PLUGIN`=sig\|priv; only `NAV_SERVICE`(normal) getters work → no telemetry |

**CarPlay day/night** needs no GM perm (AOSP `UiModeManager.getNightMode()` / `Configuration.uiMode`).
**Cluster-nav hook cannot be dropped:** the "open hook" is `CarAppFocusManager.requestAppFocus(APP_FOCUS_TYPE_NAVIGATION)` (no perm, framework-mediated — why carlink embeds the Car library); actual cluster rendering is `sig|priv` (`CAR_NAVIGATION_MANAGER`/`CAR_INSTRUMENT_CLUSTER_CONTROL`/`CAR_DISPLAY_IN_CLUSTER`) + GM **VMS/IIC** (`com.gm.vmsplugin`, system-domain, 3P-unreachable); the `CarClusterManager` HAL path is **no-op on gminfo37**. `prot=normal` replaces none of it. Detail: `/tmp/radio_audit/20261005_232227/analysis/CCPA_VEHICLE_DATA_VIA_PROTNORMAL.md`.

## Data Sources

**SELinux Policy Analysis:**
- `/vendor/etc/selinux/vendor_sepolicy.cil`
- `/product/etc/selinux/product_sepolicy.cil`

**Codec Registration:**
- `/vendor/etc/media_codecs.xml`
- `/vendor/etc/mfx_omxil_core.conf`

**Audio Configuration:**
- `/vendor/etc/audio_policy_configuration.xml`
- `/vendor/etc/asound.conf`

**Source:** `/Users/zeno/Downloads/misc/GM_research/gm_aaos/`
