# Hardware Rendering Specifications

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

## Native Linux GPU acceleration — verified 2026-11-17

**Build scope update (2026-11-17):** the later `7.3.5-probe-stable02` image has
verified i915 framebuffer/console output with automatic panel initialization,
but the Mesa/Vulkan/VA acceleration workloads below were not repeated on 7.3.5.
Do not transfer Probe06 acceleration or codec results to stable02 solely because
its panel works. See [stable02 evidence](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

This section describes native probe06 Linux, independent of the historical AAOS
capabilities below. Kernel i915 is bound to PCI8086:5a84 and exposes card0 plus
renderD128. A working fbcon/display was not treated as proof of GPU rendering.

Mesa23.2.1 (`23.2.1-1ubuntu3.1~22.04.4` packages), Intel iHD22.3.1,
libva2.14.0 and Vulkan loader1.3.204 were staged natively on the build machine.
They live under `/opt/graphics` with their own glibc loader/library path, leaving
the existing musl runtime intact. Dynamic driver roots and dependencies are
included explicitly: Mesa EGL/GBM/iris, Intel Vulkan, and iHD media driver.
Only the Intel Vulkan ICD is selected. Public-key SSH transferred the runtime
into the radio's RAM filesystem; no persistent radio storage was modified.

| Check | Live result | What it proves |
|---|---|---|
| EGL/OpenGL ES shader render | EGL1.5; vendor Intel; renderer `Mesa Intel(R) HD Graphics 505 (APL 3)`; OpenGL ES3.2 Mesa23.2.1 | Actual GPU rendering through renderD128 |
| Pixel readback | 256 triangle draws to a256×256 offscreen FBO; pixel(64,192) = RGBA64,192,64,255, exactly expected | Shader execution/readback, not just driver enumeration |
| i915 engine observation | Render sequence advanced from2 tohexD; reset count remained0 | Consistent with submitted GPU work; no reset observed |
| Vulkan | Intel open-source Mesa driver; device8086:5a84; device API1.3.255 | Hardware-device initialization; no Vulkan workload or presentation test yet |
| VA-API | iHD initialized successfully; API1.14; MPEG2/H264/JPEG/VP8/HEVC/VP9 decode profiles and selected H264/JPEG encode entrypoints | Driver/profile availability; no actual video decode/encode test yet |

The test uses GBM plus a surfaceless EGL context, compiles vertex/fragment
shaders, rejects llvmpipe/softpipe/swrast renderer strings, checks framebuffer
completeness, and verifies the readback. It does not acquire display scanout or
change the active console mode. The implementation is retained with the native
build sources as `probe-tools/gpu-render-test.c`.

Available commands in the live RAM environment and the prepared probe07 image:

```sh
gpu-render-test
vulkaninfo --summary
vainfo --display drm --device /dev/dri/renderD128
```

Wrappers invoke `/opt/graphics/run` with isolated driver and loader paths.
An initial Vulkan test failed because libvulkan.so.1 is dynamically loaded and was
missed by the first dependency pass; adding it fixed enumeration. VA-API
profile reporting must not be presented as an accelerated video-stream test.

Probe07 packages the verified runtime, console/panel fixes and diagnostic tools.
Kernel release `4.19.283-elk-linux-probe-r07`; boot image97,849,344 bytes,
SHA256 `197098cd51b0f76d87d5f6ca1f797a7a965b440aa365cbe14fd344c6340b8666`.
The final image passed QEMU boot/console/PTY/shell/block/NCM/SSH checks. Hardware
GPU tests ran on probe06 with the runtime installed live; probe07 itself has not
yet been booted on the radio. Source references: [Mesa EGL](https://docs.mesa3d.org/egl.html)
and [Intel media-driver supported platforms](https://github.com/intel/media-driver).

## Hardware Overview

### CPU Specifications

| Property | Value |
|----------|-------|
| Vendor | GenuineIntel |
| Model | Intel Atom x7-A3960 (Goldmont/Apollo Lake), IoT CPU 1.0 (Model 92, Stepping 10) |
| Architecture | x86_64 |
| Cores | 4 |
| Frequency | Base 800 MHz, Boost 2.4 GHz (1881.6 MHz nominal) |
| Cache | 1024 KB per core |
| Address Space | 39-bit physical, 48-bit virtual |

**CPU Features:**
- SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2
- AES-NI encryption acceleration
- AVX (not listed, likely disabled for automotive)
- SHA-NI (hardware SHA acceleration)
- PCLMULQDQ (carry-less multiplication)
- RDRAND/RDSEED (hardware RNG)

### GPU Specifications

| Property | Value |
|----------|-------|
| GPU Model | Intel HD Graphics 505 (APL 3) |
| Platform Codename | Apollo Lake (Broxton) |
| Driver | Mesa Intel 21.1.5 |
| OpenGL ES Version | 3.2 (196610 = 0x30002) |
| Vulkan Version | 1.1.0 (4198400 = 0x401000 = VK_MAKE_VERSION(1,1,0); live Jun-2026 `vkjson`) |
| Vulkan Compute | Supported (Level 1) |

---

## Graphics Driver Stack

### Hardware Abstraction Layer (HAL)

| Component | Implementation |
|-----------|----------------|
| Gralloc | minigbm CrosGralloc4 (`gralloc.broxton.so`, 96 KB) |
| HW Composer | iahwcomposer (Intel Automotive HWC @2.1/@2.2/@2.3, explicit sync, high quality scaling) |
| Vulkan ICD | `vulkan.broxton.so` (9.8 MB) |

### Driver Properties

```
ro.hardware.gralloc=broxton
ro.hardware.hwcomposer=broxton
ro.hardware.vulkan=broxton
ro.board.platform=broxton
```

---

## OpenGL ES Capabilities

### Version Information
- **EGL Version:** 1.4 Android META-EGL
- **GLES Version:** OpenGL ES 3.2 Mesa 21.1.5
- **GLES Vendor:** Intel
- **GLES Renderer:** Mesa Intel(R) HD Graphics 505 (APL 3)

### Supported EGL Extensions

| Extension | Purpose |
|-----------|---------|
| `EGL_ANDROID_native_fence_sync` | GPU fence synchronization |
| `EGL_KHR_fence_sync` | Fence sync objects |
| `EGL_KHR_wait_sync` | Wait for sync objects |
| `EGL_ANDROID_presentation_time` | Frame presentation timing |
| `EGL_ANDROID_get_frame_timestamps` | Frame timestamp queries |
| `EGL_ANDROID_recordable` | Screen recording support |
| `EGL_EXT_buffer_age` | Partial redraw optimization |
| `EGL_KHR_gl_colorspace` | Color space management |
| `EGL_KHR_image_base` | Image sharing |
| `EGL_KHR_surfaceless_context` | Headless rendering |

### Supported GLES Extensions (Key Extensions)

**Texture Compression:**
- `GL_EXT_texture_compression_s3tc` (DXT1/3/5)
- `GL_EXT_texture_compression_rgtc` (BC4/BC5)
- `GL_EXT_texture_compression_bptc` (BC6H/BC7)
- `GL_KHR_texture_compression_astc_ldr` (ASTC)
- `GL_OES_compressed_ETC1_RGB8_texture` (ETC1)

**Shader Capabilities:**
- `GL_EXT_geometry_shader`
- `GL_EXT_tessellation_shader`
- `GL_OES_shader_image_atomic`
- `GL_EXT_gpu_shader5`
- `GL_EXT_shader_framebuffer_fetch`
- `GL_NV_compute_shader_derivatives`

**Rendering Features:**
- `GL_EXT_draw_buffers_indexed` (MRT)
- `GL_EXT_blend_func_extended`
- `GL_KHR_blend_equation_advanced`
- `GL_EXT_clip_cull_distance`
- `GL_EXT_depth_clamp`
- `GL_INTEL_conservative_rasterization`

**External Textures:**
- `GL_OES_EGL_image_external`
- `GL_OES_EGL_image_external_essl3`
- `GL_EXT_EGL_image_storage`

---

## Vulkan Capabilities

### Version and Features

| Property | Value |
|----------|-------|
| Vulkan API Version | 1.1.0 (raw 4198400; live Jun-2026) |
| Feature Level | android.hardware.vulkan.level=1 |
| Compute Support | android.hardware.vulkan.compute |
| DEQP Level | 132383489 |

### Driver Information

- **ICD:** `vulkan.broxton.so`
- **Driver Type:** Mesa/Intel ANV
- **Usage:** **Available but NOT used at runtime** — SurfaceFlinger uses GLES backend exclusively. Vulkan driver exists (vulkan.broxton.so) but no components use it.

---

## Display Subsystem

### Primary Display

| Property | Value |
|----------|-------|
| Panel Model | DD134IA-01B |
| Manufacturer PNP ID | CMN (Chimei Innolux) |
| Resolution | 2400 x 960 pixels |
| Refresh Rate | 60.00 Hz |
| DPI | Physical: xDpi=192.911 yDpi=193.523; system lcd_density=200 (xhdpi) |
| Display Density | 200 dpi |
| VSYNC Period | 16.666 ms |
| Color Mode | Native (Mode 0) |
| Display Type | Internal LCD |
| Manufacture Date | Week 36, 2020 |

### SurfaceFlinger Configuration

```
Build configuration:
  PRESENT_TIME_OFFSET=0
  FORCE_HWC_FOR_RBG_TO_YUV=0
  MAX_VIRT_DISPLAY_DIM=0
  NUM_FRAMEBUFFER_SURFACE_BUFFERS=3
```

### Composition Pipeline

| Feature | Status |
|---------|--------|
| Client Composition | Enabled (GPU fallback) |
| Device Composition | Enabled (HW overlay) |
| Color Management | Enabled |
| Wide Color Gamut | Not Supported |
| HDR10 | Not Supported |
| HDR10+ | Not Supported |
| HLG | Not Supported |
| Dolby Vision | Not Supported |

### Rendering Statistics

| Metric | Value |
|--------|-------|
| Framebuffer Surface Buffers | 3 (triple buffering) |
| Max Graphics Buffer Producers | 4096 |
| RenderEngine Protected Context | Not Supported |
| Visible Layers (typical) | ~129 |

---

## Hardware Composer (HWC)

### HWC Version
- **Interface:** `android.hardware.graphics.composer@2.1`, `@2.2`, `@2.3`
- **Service Binary:** `composer.intel@2.3-service`
- **Implementation:** `iahwcomposer` (Intel Automotive Hardware Composer)

### Layer Composition Types

| Type | Description |
|------|-------------|
| `DEVICE` | Hardware overlay (zero-copy) |
| `CLIENT` | GPU composition (SurfaceFlinger RenderEngine) |

### HWC Capabilities

- Supports multiple hardware overlays
- YUV to RGB conversion in display controller
- Scaling and rotation in hardware
- Alpha blending in hardware
- No HDR tone mapping (not supported)

### HWC Configuration
- Only 1 DRM display active (3 defined in hwc_display.ini)
- VSYNC period: 16.666 ms, presentation deadline: 14.666 ms
- No DCI-P3, no wide color gamut, no HDR
- Max luminance: 500 nits

---

## Memory Allocation (Gralloc)

### Implementation
- **HAL:** `gralloc.broxton.so`
- **Fallback:** `gralloc.default.so`

### Buffer Formats Supported

| Format Code | Format Name |
|-------------|-------------|
| 0x1 | RGBA_8888 |
| 0x2 | RGBX_8888 |
| 0x3 | RGB_888 |
| 0x4 | RGB_565 |
| 0x5 | BGRA_8888 |
| 0x7f420888 | YUV420Flexible |
| 0x13 | YUV420Planar |
| 0x15 | YUV420SemiPlanar (NV12) |
| 0x14 | YUV420PackedPlanar |
| 0x27 | YUV420PackedSemiPlanar |
| 0x100 | Implementation-defined |

---

## Video Decode/Encode Pipeline

### Hardware Video Engine

The Intel HD Graphics 505 includes dedicated video processing hardware:

| Engine | Function |
|--------|----------|
| VPU (Video Processing Unit) | Hardware decode/encode |
| VPG (Video Post-Processor) | Scaling, color conversion |
| Display Engine | Overlay composition |

### OMX Service
- **Interface:** HIDL 1.0 (`android.hardware.media.omx@1.0`)
- **User:** `mediacodec`
- **Groups:** `camera`, `drmrpc`, `mediadrm`
- **I/O Priority:** `rt 4` (real-time, priority 4)

### Decode Path
1. **Input:** Compressed video bitstream
2. **MediaCodec API** → Intel OMX decoder
3. **VPU** decodes to YUV surface in graphics memory
4. **Gralloc buffer** holds decoded frame
5. **SurfaceFlinger** composites via HWC or RenderEngine
6. **Display Engine** outputs to panel

### Encode Path
1. **Input:** Camera/screen capture in graphics memory
2. **VPU** encodes from YUV/RGB surface
3. **Output:** Compressed bitstream via MediaCodec

---

## Performance Characteristics

### Measured Frame Rates (from codec benchmarks)

**H.264 Hardware Decode:**
| Resolution | FPS Range |
|------------|-----------|
| 320x240 | 740-980 |
| 720x480 | 830-1020 |
| 1280x720 | 460-590 |
| 1920x1088 | 320-360 |

**H.265 Hardware Decode:**
| Resolution | FPS Range |
|------------|-----------|
| 352x288 | 600-1000 |
| 640x360 | 450-800 |
| 720x480 | 400-700 |
| 1280x720 | 250-500 |
| 1920x1080 | 190-400 |
| 3840x2160 | 120-130 |

**VP8 Hardware Decode:**
| Resolution | FPS Range |
|------------|-----------|
| 320x180 | 600-1300 |
| 640x360 | 500-800 |
| 1280x720 | 200-400 |
| 1920x1080 | 150-330 |

**VP9 Hardware Decode:**
| Resolution | FPS Range |
|------------|-----------|
| 320x180 | 600-1300 |
| 640x360 | 500-800 |
| 1280x720 | 400-600 |
| 1920x1080 | 350-420 |
| 3840x2160 | 100-130 |

### GPU Loading Stats

```
GL driver loading time: ~45ms
Vulkan loading: Not commonly used
ANGLE: Not used
```

---

## Automotive-Specific Features

### Display Flags
- `FLAG_SECURE` - Protected content support
- `FLAG_SUPPORTS_PROTECTED_BUFFERS` - DRM buffer support
- `FLAG_TRUSTED` - System display
- `FLAG_ROTATES_WITH_CONTENT` - Auto-rotation capable

### System Services
- `automotive_display` service: Running
- `remote_display` service: Stopped (not in use)
  - Binary: `/vendor/bin/remote_display`
  - User: `system`
  - Type: `oneshot` (does not auto-restart)

### Hardware SKU
```
ro.boot.product.hardware.sku=gv221
ro.hardware.type=automotive
```

---

## Boot-Time GPU/Display Init (init.bxtp_gm.rc)

### GPU Configuration
- **GPU Min Frequency:** Forced to 300 MHz on `post-fs` phase (required for IPU camera integration)
- **Mesa Driver Environment:**
  - `INTEL_DEBUG=heur32` (heuristic tuning for Gen 3.2 / Apollo Lake)
  - `MESA_LOADER_DRIVER_OVERRIDE=iris` (forces Iris driver over i965)

### CPU Power States During Boot
- **C-states (C1-C3):** Disabled during boot for deterministic init timing
- **C-states:** Re-enabled on `boot_completed` trigger
- **Suspend:** Disabled permanently via `nosleeptillbrooklyn` wake_lock — the system never enters suspend *(init-script reading; qualified 2026-11-12: the update-engine log from the same unit counts 43 engine restarts/prefs reloads beyond its 1797 boots that the forensic parse labels "resume-from-suspend", and GM PowerMode `SLEEP` states appear, so "never" is not confirmed by runtime data; unresolved). Omitted counter-evidence to the doubt above, added 2026-11-12: the retained kernel logs (38 `kernel.log` files) contain 0 `PM: suspend entry`/`PM: suspend exit` lines, consistent with no kernel suspend, though the retained windows are short and do not prove it for the whole uptime)*

### GPIO Assignments (External Processors)
| GPIO | Function |
|------|----------|
| 466 | Dirana Reset |
| 460 | Dirana Bootstate |
| 458 | Saturn Reset |
| 464 | Saturn Bootmode |

---

## Ethernet Switch Hardware ID

The property `persist.vendor.harman.hardwareid` determines which Ethernet switch driver is loaded.

| Switch Vendor | Hardware IDs |
|---------------|-------------|
| Broadcom (`bcm`) | ED, DV1, DV2, DV4, DV6, PV1, MY22PV01-08 |
| Marvell (`mrvl`) | MY23DV0, MY23DV1, MY24DV1 |

MY23 and later hardware revisions use the Marvell switch.

---

## Recommendations for Video Rendering

### Optimal Video Playback Settings

1. **Preferred Codec:** H.264 or H.265 via hardware decoder
2. **Max Resolution:** 1920x1080 for smooth 60fps playback
3. **Color Format:** NV12 (YUV420SemiPlanar) for hardware path
4. **Surface Type:** SurfaceView or TextureView with hardware layers

### CarPlay/Android Auto Integration

For projection rendering:
- Use `OMX.Intel.hw_vd.h264` for video decode
- Render to SurfaceView for direct HWC overlay
- Avoid TextureView if possible (requires GPU composition)
- Use 1080p or 720p for optimal latency

### Memory Considerations

- Triple-buffered framebuffer (17ms latency overhead)
- Gralloc buffers in unified graphics memory
- No dedicated VRAM (shared system memory architecture)
