# GM AAOS CarPlay Video Pipeline Technical Analysis

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Analysis Date:** January 2026
**Source:** `/Users/zeno/Downloads/misc/GM_research/gm_aaos/`

---

## Executive Summary

GM AAOS implements CarPlay video projection using the **CINEMO** multimedia framework (developed by Harman/Samsung). The video pipeline receives H.264 streams via AirPlay protocol, processes NAL units through Cinemo's **software** H.264 decoder module (named `NvdecSW`), and renders to Android native windows via EGL surfaces.

> **Scope (2026-11-12):** everything below describes the **stock GM CarPlay (Cinemo/NME)** path from static
> analysis. A third-party app on the same radio (gm_ccpa) uses the Intel HW HEVC decoder instead; see the
> scope correction before "Decoder Selection".

**Key Finding (stock GM CarPlay):** Despite having an Intel hardware H.264 decoder (`OMX.Intel.hw_vd.h264`), CarPlay video uses a **software decoder** path through CINEMO's `NvdecSW` library for AirPlay-specific NAL unit handling and timing synchronization.

> **Terminology — "NVDEC" in this document:** the names `NvdecSW`, `Cinemo/nvdec/H264DEC`,
> `NmeCreateCodecNvdecSW()`, and `NvdecError_*` are **Cinemo NME's own internal module/symbol
> names** for its **software** H.264 decoder. This is **NOT** NVIDIA's hardware NVDEC — gminfo37
> has an Intel HD Graphics 505 GPU and **no NVIDIA silicon**. Read every "NVDEC" below as
> "Cinemo's `NvdecSW` software decoder."

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        iPhone (AirPlay Source)                               │
│                     H.264 Video Stream @ 60fps                               │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ USB/WiFi
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Transport Layer (carplay.sh)                              │
│                 USB NCM (usb0) + IPv6 fe80::/64 routing                      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   libNmeCarPlay.so (1.0 MB)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  AirPlayReceiverServer                                               │    │
│  │  - AirPlayReceiverSession (per connection)                          │    │
│  │  - AirPlayReceiverSessionScreen (video frames)                      │    │
│  │  - AirPlay/320.17.8 protocol                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  OnFrame() → NAL unit extraction → H.264 frame validation                   │
│  - nalu_size extraction                                                      │
│  - syncframe detection                                                       │
│  - corrupt data validation                                                   │
│  - ForceKeyframe() for recovery                                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     libNmeVideo.so (121 KB)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  INmeVideoDecode Interface                                          │    │
│  │  - NmeVideoCodec abstraction                                        │    │
│  │  - QualityControl() - adaptive frame dropping                       │    │
│  │  - Clock synchronization (SwitchClock, OnClockChange)               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Options:                                                                    │
│  - video_hardware_decode (bool)                                             │
│  - video_software_decode (bool)                                             │
│  - video_max_h264_level (int)                                               │
│  - video_extra_surfaces (int)                                               │
│  - video_frame_drop_threshold (int)                                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   libNmeVideoSW.so (646 KB)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Cinemo NvdecSW Software H.264 Decoder (NOT NVIDIA hardware)       │    │
│  │  Module: Cinemo/nvdec/H264DEC                                       │    │
│  │  UUID: abce2648-0ba7-11ea-8d71-362b9e155667#F_VIDEO_H264*SW         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  NAL Unit Processing:                                                        │
│  - H264Create() → H264DeliverAnnexB() → H264Free()                          │
│  - RBSP (Raw Byte Sequence Payload) parsing                                 │
│  - SPS/PPS/SEI extraction and validation                                    │
│                                                                              │
│  Error Handling:                                                             │
│  - NvdecError_BitDepth                                                      │
│  - NvdecError_ChromaFormat                                                  │
│  - NvdecError_Profile                                                       │
│  - NvdecError_MaxVxdFileMemory                                              │
│  - NvdecError_MaxVxdTotalMemory                                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 libNmeVideoDevice.so (397 KB)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Surface/Device Management                                          │    │
│  │  - NmeCreateDeviceANW (Android Native Window)                       │    │
│  │  - NmeCreateSwapChain (buffer management)                           │    │
│  │  - ANativeWindow_fromSurface → acquire/release                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  EGL Context:                                                                │
│  - eglCreateWindowSurface / eglCreatePbufferSurface                         │
│  - Mesa Intel HD Graphics 505 renderer                                      │
│  - OpenGL ES 3.2                                                            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               libNmeVideoRenderer.so (277 KB)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Video Mixing Renderer (VMR)                                        │    │
│  │  - NmeCreateVmr / NmeCreateVmrClone                                 │    │
│  │  - DecideRenderFPS() - frame rate decision                          │    │
│  │  - DecideRenderQuality() - quality adaptation                       │    │
│  │  - Frame dropping for late frames                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Surface Callbacks:                                                          │
│  - OnSurfaceAllocate(subtype, native, attr, size, surfaces, device)         │
│  - OnSurfaceFreeze()                                                        │
│  - SignalOutputPreviousFrame()                                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SurfaceFlinger + HWC 2.1                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  iahwcomposer (Intel Automotive HWC)                                │    │
│  │  - DEVICE composition (hardware overlay)                            │    │
│  │  - CLIENT composition (GPU fallback)                                │    │
│  │  - Triple buffering (3 framebuffers)                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Display Output                                          │
│                   Chimei Innolux CMN DD134IA-01B                                   │
│                   2400x960 @ 60.00 Hz                                        │
│                   VSYNC: 16.666 ms                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. CarPlay Service Layer

**Service:** `com.gm.domain.server.delayed:CarplayService` (PID 2685)

**Binder Interfaces:**
| Service | Interface |
|---------|-----------|
| `com.gm.carplay.service.BINDER` | `gm.carplay.ICarPlayService` |
| `com.gm.phoneprojection.service.BINDER` | `gm.phoneprojection.IPhoneProjectionService` |
| `com.gm.server.screenprojection.RDMSADBHandler` | `gm.connection.IRDMSADBHandler` |

**Event Handling:**
```
CarPlay_PlayerManager: onCinemoEvent(): CINEMO_EC_GRAPH_STATUS
```

### 2. USB Transport Setup

**File:** `/system/bin/carplay.sh`
```bash
#!/system/bin/sh
ifconfig usb0 up
ip -6 route flush table local_network
ip -6 route add fe80::/64 dev usb0 proto static table local_network
```

- USB NCM (Network Control Model) interface
- IPv6 link-local addressing for CarPlay
- Aptiv USB bridges (VID 10646) handle USB connection

### 3. NME Library Stack

| Library | Size | Purpose |
|---------|------|---------|
| `libNmeCarPlay.so` | 1.0 MB | AirPlay protocol, session management |
| `libNmeVideo.so` | 121 KB | Video codec abstraction |
| `libNmeVideoSW.so` | 646 KB | NVDEC H.264 software decoder |
| `libNmeVideoDevice.so` | 397 KB | Surface/EGL management |
| `libNmeVideoRenderer.so` | 277 KB | VMR, quality control |
| `libNmeIAP.so` | 2.9 MB | iAP (Apple Accessory Protocol) |
| `libNmeAppleAuth.so` | 80 KB | Apple authentication |
| `libNmeBaseClasses.so` | 4.8 MB | Core framework |

**Source Path References:**
```
../../NmeLibs/Nvdec/vdec/vdec264.cpp
../../NmeLibs/Nvdec/vdec/vrbsp_sequence.cpp
../../NmeLibs/Nvdec/vdec/vrbsp.cpp
../../NmeCarPlay/r14/src/NmeCarPlayVideo.cpp
```

---

## H.264 Frame Processing

### NAL Unit Types Handled

| NAL Type | Description | Handling |
|----------|-------------|----------|
| SPS | Sequence Parameter Set | Parsed for resolution, profile, level |
| PPS | Picture Parameter Set | Parsed for encoding parameters |
| IDR | Instantaneous Decoder Refresh | Full frame decode, reference reset |
| P-Frame | Predicted Frame | Reference-based decode |
| SEI | Supplemental Enhancement Info | Multiple types supported |

### SEI Message Processing (libNmeVideoSW.so)

| SEI Type | Function | Purpose |
|----------|----------|---------|
| `rbsp_sei_full_frame_freeze` | Freeze display | Pause rendering |
| `rbsp_sei_full_frame_freeze_release` | Resume display | Resume rendering |
| `rbsp_sei_full_frame_snapshot` | Snapshot | Capture current frame |
| `rbsp_sei_deblocking_filter_display_preference` | Quality | Deblocking settings |
| `rbsp_sei_dec_ref_pic_marking_repetition` | Reference | Frame reference management |
| `rbsp_sei_scene_info` | Metadata | Scene change detection |
| `rbsp_sei_stereo_video_info` | 3D | Stereo video support |
| `rbsp_sei_user_data_registered_itu_t_t35` | User data | ITU-T T.35 metadata |

### Frame Reception (libNmeCarPlay.so)

```cpp
// Pseudo-code from string analysis
OnFrame() {
    // Validate NAL unit
    if (nalu_size invalid) {
        log("OnFrame() invalid nalu_size");
        return;
    }

    if (data corrupt) {
        log("OnFrame() corrupt video data");
        return;
    }

    // Extract frame metadata
    log("OnFrame() received video frame: %d (nalu_size:%u, header_len:%d)");

    // Check for sync frame (IDR)
    if (is_sync_frame) {
        log("OnFrame() -> syncframe");
    }

    // Append to decoder buffer
    if (append_data_failed) {
        log("OnFrame() append of data failed");
        ForceKeyframe();  // Request IDR for recovery
    }
}
```

---

## Error Recovery Mechanisms

### 1. Keyframe Request

When frame corruption or decode errors occur:
```cpp
AirPlayReceiverSessionForceKeyFrame()  // Request new IDR from iPhone
```

### 2. Late Frame Handling

```cpp
// From libNmeVideo.so
QualityControl(timestamp, flags) {
    if (clock_running && frame_late) {
        log("QualityControl -> %T late -> reference frames only");
        // Drop B-frames, only decode reference frames
    }
    if (catching_up_finished) {
        log("QualityControl -> catching up finished");
        // Resume normal decoding
    }
}
```

### 3. Timestamp Validation

```cpp
// From libNmeVideo.so
OnSurface() {
    if (no_pts) {
        log("OnSurface() - discard surface with no PTS!");
        return;
    }

    if (non_monotonic_timestamps) {
        log("non-monotonic video timestamps %T-%T -> %T-%T");
        // Handle timestamp discontinuity
    }
}
```

### 4. Decoder Errors (libNmeVideoSW.so)

| Error | Cause | Recovery |
|-------|-------|----------|
| `NvdecError_BitDepth` | Unsupported bit depth | Fallback/skip frame |
| `NvdecError_ChromaFormat` | Invalid chroma format | Skip frame |
| `NvdecError_Profile` | Unsupported H.264 profile | Request format change |
| `NvdecError_MaxVxdFileMemory` | Memory limit exceeded | Reduce buffer count |
| `NvdecError_MaxVxdTotalMemory` | Total memory exceeded | Restart decoder |

### 5. Surface Allocation Fallback

```cpp
// From libNmeVideoRenderer.so
OnSurfaceAllocate() {
    result = TryHardwareSurface();
    if (result == success) {
        log("Native surface allocation successful");
        log("Video device based HW decoder opened");
    } else {
        log("Video device based HW decoder not available, %e!");
        log("using decoder allocation");  // Fallback to SW allocation
    }
}
```

---

> **Scope correction, 2026-11-12 (live Y181B radio, `main` log, build `W231E-Y181.3.2-SIHM22B-499.3`):** the
> "software NvdecSW decoder" finding in this document describes the **stock GM CarPlay (Cinemo/NME)**
> path only. A third-party CarPlay app (gm_ccpa, `zeno.gmccpa`, wireless CarPlay via the OCBM box) on the
> same radio decodes with the **Intel hardware HEVC decoder** through ordinary MediaCodec:
> `NETPROBE ... video-decoder UP OMX.Intel.hw_vd.h265 video/hevc 2400x960 csd-0=105B` (45 periodic status lines plus 1 `(new) -> UP` transition; 3 periodic `DOWN (renderer stopped)` lines plus 1 `UP -> DOWN` transition at 06:54:50),
> `mediasdk_omx: mfx_omx_vdec_component: Created OMX.Intel.hw_vd.h265`, and
> frame counters such as `59100 frames rendered (332735539 B in)` and `seam ended - 62953 frames
> rendered, 0 AUs dropped`. So the radio's H.264/AirPlay table below is not the only video path, the
> negotiated stream on this rig is HEVC at 2400x960, and the Intel HW decoder is usable by a 3P app
> (see `analysis/third_party_access.md`). The stock path remains documented below from static analysis.
> [2026-11-12 correction: the earlier "25 create / 25 destroy" count for `Created OMX.Intel.hw_vd.h265` was wrong as
> evidence. The pattern also matches `h265.secure`: plain `h265` = 13 Created / 13 Destroyed, `.secure` = 12 / 12
> (reproduced from the merged `main` log). The same create/destroy pairs occur for h264, h264.secure, vp8 and vp9
> (98 `Created OMX.` lines in total), i.e. codec-list enumeration at each boot (e.g. 11-11 22:00:47.282 Created, then
> Destroyed within ms), not app decode sessions. Only 06:14:47.415 aligns with gm_ccpa (pid 3800,
> `MediaCodec: [OMX.Intel.hw_vd.h265]` at 06:14:47.419). The evidence that gm_ccpa decodes with the HW decoder is the
> NETPROBE `video-decoder UP ... h265 ... 2400x960` status lines, not the create/destroy count.]
> Also seen: `CarPlay_PlayerManager: HW decoder property detected. set player option
> is_zero_display_delay=1` (stock Cinemo player, 2 lines), i.e. the stock player has a HW-decoder
> property branch, which the "always software" wording below should not be read to exclude. [read from the
> retained `main` log, 2026-11-11 18:12 to 2026-11-12 13:04 (counts re-verified 2026-11-12: 45 status lines, 25 create/destroy, 2 `is_zero_display_delay` lines at 04:11 and 13:04). The earlier
> "gm_ccpa not installed at the 14:00 AKST check" is not reconciled with these logs, which show
> package `android.car.usb.handler` (gm_ccpa) added 11-10 17:06 and never removed in the retained streams; the
> live check may have searched for the name `zeno.gmccpa` instead of the package name. Live state not re-checked
> (device not attached during the 2026-11-12 audit).]

## Decoder Selection

### Why Software Decoder? (stock GM CarPlay only; rationale is inferred from library structure, not stated by Cinemo)

Despite Intel `OMX.Intel.hw_vd.h264` being available, stock CarPlay uses software NVDEC (gm_ccpa does not; see scope correction above):

1. **AirPlay Protocol Integration** - CINEMO framework handles AirPlay-specific timing/sync
2. **SEI Processing** - Custom SEI handling for freeze/snapshot/stereo
3. **Quality Control** - Adaptive frame dropping integrated with AirPlay session
4. **Latency Control** - Direct control over decode timing without OMX buffer queues

### Available Hardware Decoder

```xml
<!-- /vendor/etc/media_codecs.xml -->
<MediaCodec name="OMX.Intel.hw_vd.h264" type="video/avc">
    <Limit name="size" min="64x64" max="3840x2160" />
    <Limit name="bitrate" range="1-40000000" />
    <Limit name="performance-point-3840x2160" value="60" />
    <Feature name="adaptive-playback" />
</MediaCodec>
```

**Measured Performance (Hardware):**
| Resolution | FPS |
|------------|-----|
| 1280x720 | 460-590 |
| 1920x1088 | 320-360 |

---

## Rendering Pipeline

### Surface Management

```cpp
// ANativeWindow creation
ANativeWindow* window = ANativeWindow_fromSurface(env, surface);
ANativeWindow_acquire(window);

// EGL setup
EGLSurface eglSurface = eglCreateWindowSurface(display, config, window, attrs);
```

### VMR (Video Mixing Renderer)

```cpp
DecideRenderFPS() {
    // Initial frame timing
    log("DecideRenderFPS() -> initial npts=%T time=%T");

    // Frame dropping decision
    if (frame_too_late) {
        log("DecideRenderFPS() -> npts=%T diff=%T dropped!");
    }
}

DecideRenderQuality() {
    if (stream_behind) {
        log("DecideRenderQuality() -> npts=%T streamtime=%T dropped!");
    }
}
```

### Display Composition

| Stage | Component | Method |
|-------|-----------|--------|
| 1 | VMR | Software composition |
| 2 | SurfaceFlinger | Layer management |
| 3 | HWC 2.1 | `DEVICE` or `CLIENT` composition |
| 4 | Display | 2400x960 @ 60Hz output |

---

## Performance Characteristics

### Timing Targets

| Metric | Value |
|--------|-------|
| Target Frame Rate | 60 fps |
| VSYNC Period | 16.666 ms |
| Presentation Deadline | 14.666 ms |
| Frame Drop Threshold | Configurable |

### Latency Sources

| Stage | Estimated Latency |
|-------|-------------------|
| USB/WiFi Transport | 1-5 ms |
| NAL Parsing | < 1 ms |
| NVDEC Decode | 5-10 ms |
| Surface Copy | 1-2 ms |
| SurfaceFlinger | 0-16 ms (vsync aligned) |
| Display Scanout | 8 ms |
| **Total** | **~20-40 ms** |

---

## Configuration Options

### CINEMO Video Options

| Option | Type | Description |
|--------|------|-------------|
| `video_hardware_decode` | bool | Enable HW decode path |
| `video_software_decode` | bool | Enable SW decode path |
| `video_max_h264_level` | int | Maximum H.264 level |
| `video_extra_surfaces` | int | Additional surface buffers |
| `video_frame_drop_threshold` | int | Drop threshold (ms) |

### AirPlay Configuration

**File:** `/etc/airplay.conf`

---

## System Integration

### Kernel Support

```
CONFIG_VIDEO_INTEL_IPU=y
CONFIG_VIDEO_INTEL_IPU4=y
CONFIG_VIDEO_INTEL_IPU_SOC=y
CONFIG_VIDEO_INTEL_IPU_FW_LIB=y
CONFIG_VIDEOBUF2_CORE=y
CONFIG_VIDEOBUF2_V4L2=y
CONFIG_VIDEOBUF2_DMA_CONTIG=y
```

### User Accounts

```
vendor_carplay:x:2997:2997::/:/vendor/bin/sh
vendor_iap2:x:2994:2994::/:/vendor/bin/sh
```

---

## Comparison: CarPlay vs Android Auto

| Aspect | CarPlay | Android Auto |
|--------|---------|--------------|
| Protocol | AirPlay 320.17.8 | AOA + Projection |
| Video Codec | H.264 (AirPlay) | H.264 (AOA) |
| Decoder | CINEMO NVDEC (SW) | OMX.Intel (HW)* |
| Library | libNmeCarPlay.so | libNmeVideoGAVD.so |
| Transport | USB NCM + IPv6 | USB AOA |

*Android Auto may use hardware decoder through standard Android MediaCodec path.

---

## Related Documentation

- [video_codecs.md](video_codecs.md) - Hardware/software codec specifications
- [display_subsystem.md](display_subsystem.md) - Display and SurfaceFlinger details
- [hardware_rendering.md](hardware_rendering.md) - GPU and EGL specifications

---

## Data Sources

All specifications from analysis of:
- `/Users/zeno/Downloads/misc/GM_research/gm_aaos/extracted_partitions/system_extracted/`
- `/Users/zeno/Downloads/misc/GM_research/gm_aaos/analysis/adb_Y181/`
- Binary analysis: `strings`, `readelf`, `nm` on libNme*.so
- ADB dumps: processes, services, logcat

## MFi authentication I2C path — 2026-11-17

The Y175 cleanroom `vendor/lib64/vendor.harman.hardware.ame@1.0-hal.so`
contains `DiagnosticsHal::readAppleAuthChipId()` at ELF VA0x24d0
(Ghidra import address0x1024d0). SHA256:
`36c769fd7c2c856e63dc08bcc31ac563bc7f9eac1ed6ff4557321709904a941b`.
The function explicitly opens `/dev/i2c-2`, selects 7-bit slave0x10 with
`ioctl(fd,0x703,0x10)`, writes register selector0x00, then reads three bytes
with retries. This directly establishes **AAOS bus2 / slave0x10** as the
Apple authentication diagnostic path; generic Cinemo library support for other
I2C/SMSC backends does not identify the active board path on its own.

Native probe06 exposes DesignWare instance2 at PCI00:16.2 as `/dev/i2c-5`.
That is the candidate translation from guest bus numbering, not a confirmed
working MFi path. A bounded targeted transaction selecting0x00 at slave0x10
on native bus5 returned `i2ctransfer: I2C_RDWR: Remote I/O error`; the subsequent
read was not issued. No blind scan, authentication challenge, certificate read,
provisioning command or reset was sent. Physical mapping, power/reset/pinmux,
and native accessibility remain unresolved. Do not label native i2c-2 as MFi:
it is the i915 GMBUS misc adapter in this image.
