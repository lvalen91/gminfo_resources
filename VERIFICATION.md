# Cross-Verification Record

Every factual claim in this repo was cross-checked (8 parallel verification passes) against
ground-truth sources: the **POTATO** ADB/logcat/metrics corpus, the **Y181/Y177 update
packages** (partition manifests + decompiled ELK/GHS/VMM/VIP artifacts), the **EEPROM `.bin`
dumps**, the **DPS session logs**, the **SELinux policy CIL**, decompiled **GMSystemUI**, and
the in-repo **ADB enumeration** dumps (Y175, Y181 Dec-2025, Y181 Apr-2026, **Y181 Jun-2026 live**).

> **Jun-2026 live update:** a fresh capture against the running radio (`enumeration/Y181/jun2026/`,
> same Y181.3.2 firmware) reinforced 16 claims, closed 3 "unverifiable" gaps (GPU, touch 0x4B, virtio guest),
> and **withdrew two earlier corrections** (c2.android codecs, networking) — see those rows below and
> `enumeration/Y181/jun2026/CLAIMS_VERIFICATION.md`.

Bottom line: the bulk of the repo verified **CONFIRMED**. The errors found are listed below;
the **Corrected** ones have been fixed in-tree. CCPA/CPC200 adapter material was out of scope
(separate repo).

## Corrected (applied)

| Area | Was | Now (verified) |
|------|-----|----------------|
| RAM type/capacity | "6 GB DDR3L" (8 docs) | **8 GB LPDDR4** physical (4× Micron MT53E512M32D2DS-053, teardown); ~6 GB to guest, 5.66 GB kernel-visible |
| eMMC model | KLMBG2JETD-B041 (32 GB part #) | **KLMCG4JEUD** (64 GB, teardown-verified) |
| Display maker | Chunghwa | **Chimei Innolux** (PnP `CMN`) |
| Audio output buses | "14" / "12+" (README + 4 audio docs) | **8** CarAudioService buses (bus0–bus7), confirmed in `car_service.txt`; bus8–bus13 are Harman-HAL-internal graph nodes, not CarAudioService buses |
| Audio HAL name | `vendor.hardware.audio@5.0` "Titan" | `android.hardware.audio@5.0` (HarmanHAL); **"Titan" = SoC platform codename**, not the HAL |
| firmware_re fn count | 117 | **115** (`ls out_vip_app/*.c`) |
| VHAL: RANGE_REMAINING | "not present (ICE)" | **present** (0x11600308) |
| VHAL: FUEL_LEVEL_LOW | 0x11600308 | correct ID **0x11200405** (0x11600308 is RANGE_REMAINING) |
| VHAL: HVAC | "standard HVAC IDs ALL ABSENT, GM non-standard" | **standard AOSP HVAC IDs present** (0x15400500/501 fan, 0x15600502/503 temp); CarHvacManager fan/temp works |
| Networking ports | 9002/9010/9016 @ 192.168.1.100; 7000 ADB | **RE-CONFIRMED to original by live Jun-2026 capture**: guest IP is **192.168.1.100** (eth0/vlan5; no `.1` iface or route in guest), with **9002/9010/9016 + 7000 + 6363 + 49156 all LISTENING**. The earlier "9002/9016 @ .1, 9010 outbound, 7000 gone" correction was a single-dump artifact (state varies by projection session) and is withdrawn. WiFi-AP side: `br0 192.168.5.1/24` serves DNS :53; vlan4 `172.16.4.100`. |
| CAN tester ID | Req 0x14DA80**F1** / Rsp 0x145AF1**80** | captured DPS session uses **F2** (0x14DA80F2 / 0x145AF280); F1 = generic OBD tester address |
| EEPROM unlock guide | only 0x441/0xa81 documented | added **0x1A01→0xFF** and **0x0B41→0x01** (all 4 bytes the Y181 mod actually flips) |
| 0x0A00/0x0B00 ref counts | 871/311 stated as fact | flagged: 871 vs 854 / 311 vs 305 across passes; RE-sourced, not dump-reproducible |

## Confirmed against ground truth (high-value spot-checks)

- **Hardware:** CPU Goldmont 4-core (cpuinfo), display DD134IA-01B 2400×960@60 density 200
  (display_info), kernel 4.19.305/4.19.283, fingerprint Y181.3.2, ABI x86_64, WiFi 2.4 GHz lock,
  GLES 3.2 (`ro.opengles.version=196610`).
- **Boot/firmware:** GHS INTEGRITY IoT **2020.18.19 MY22-026** (ghs_analysis), kernelflinger-07.02
  (elk_strings), libavb chain, A/B-CRC failure strings, security-patch levels (Y175 2024-05-05,
  Y181 2025-06-05), VIP V850 core, UDS $27 in DPS, identical VIP_BOOT/HOSTOS/ABL across Y177/Y181.
- **Security:** Y181 Enforcing at runtime (user build ignores `selinux=permissive` cmdline);
  `untrusted_app` has usb_device ioctl/read/write/getattr but **not open** (plat_sepolicy.cil);
  no carlink/usbmountreceiver rules; AVB locked/green/sha256, oem_unlock=0; ports 6363/49156/9002/9016.
- **EEPROM:** Y181_stock→modified diff = exactly 4 bytes (0x441/0xa81→FF, 0x0B41→01, 0x1A01→FF);
  CRC words present at 0x16E0/0x19E0/0x1A80/0x1B40/0x1B60/0x1B80 and untouched by redaction;
  DPS shows `SBI $0000 Bypass Inactive`, all-FF seed; all bins 8192 B.
- **Audio:** exactly 8 buses, 6 VolumeGroups, 48 kHz/8 ms period, FAST flag denied to 3P,
  ECNR HAL absent, HalAudioFocus unsupported — all from car_service.txt + POTATO logcat.
- **Video/display:** OMX.Intel.hw_vd.h264 (HW path) **coexisting with c2.android.* SW video decoders** —
  live Jun-2026 `dumpsys media.player` lists `c2.android.{avc,hevc,vp8,vp9}.decoder` and
  `/vendor/etc/media_codecs_google_video.xml` is present, so the earlier "12 c2.android.* absent" claim is **withdrawn**;
  window geometry T:118/L:189/CardView/1416×842 verbatim in logcat, keyframe 2.5 s/30 s,
  Intel VPU workaround marker, iahwcomposer explicit-sync, no HDR/VRR.
- **VHAL/cluster:** 535 props (49 SYSTEM + 486 VENDOR), Cluster HAL mIsCoreSupported:false →
  VMS via com.gm.vmsplugin/.VMSClusterService, channels 10002/10003.
- **USB/ADB:** software role-switch (`vendor.sys.usb.role`→`usb_otg_switch.sh`→`/dev/cbc-signals`
  + intel_xhci_usb_sw role node), dabridge dabr_udc.0 / bridgeport 1-6.0→1-6.3, adb props — all
  verified in the Y181 vendor init blob.
- **GMSystemUI §19:** WhiteList static-init class, VisibilityController 8 lists (a–h), list
  members, NAV_SCREEN_FULL/SPManager, Maps-only CardViewControl gate — all confirmed in the
  decompiled GMSystemUI.

## Unverifiable from available sources (not wrong — just not independently evidenced)

EEPROM I²C **0x50** (no raw read — `/dev/i2c-7` is `system:system 0660`, shell can't open);
VIP stub @0xb67d0 4 B→906 B and Y177 permissive (no Y177 ADB dump — RE-sourced);
`libNmeVideoSW.so` name (partition `strings` only); 4-port USB topology / OTG-ID-pin (ALLData schematics).

**Resolved by live Jun-2026 ADB capture** (`enumeration/Y181/jun2026/`):
- GPU **"HD 505 / Mesa 21.1.5"** → CONFIRMED via `SurfaceFlinger` GLES dump:
  `Mesa Intel(R) HD Graphics 505 (APL 3), OpenGL ES 3.2 Mesa 21.1.5 (git-4bdd81676b)`.
- Touch controller **I²C 0x4B** → CONFIRMED: `/sys/bus/i2c/devices/7-004b` bound (bus 7 also exposes 0x0c/0x12/0x28).
- Virtualized GHS guest → CONFIRMED: guest block device is `vda` (virtio-blk), no `mmcblk*` (eMMC sits behind the hypervisor).
- Vulkan **"1.0.64"** → CORRECTED to **1.1.0**: the raw value `4198400` (identical in repo dump and live `vkjson`)
  decodes to `0x401000` = `VK_MAKE_VERSION(1,1,0)`. "1.0.64" was a decode slip (1.0.64 would be `4194368`/`0x400040`).
  Source docs updated (`video/README.md`, `video/hardware_rendering.md`, `analysis/platform_faq.md`).

## Recommended but not yet applied (judgment calls / lower priority)

- **Provenance hedging:** label Y177-permissive + VIP-stub as RE-sourced in `firmware_versions.md`
  & README (FAQ §12 already does); `boot_chain.md:136` AB0 magic comment says "AVB0" (should be
  `\0AB0`); rollback "separate GHS counter in misc" is inference (the *block* is field-observed).
- ~~**Video codec tables:** annotate the c2.android.* SW video codecs as absent.~~ **WITHDRAWN** —
  live Jun-2026 confirms `c2.android.{avc,hevc,vp8,vp9}.decoder` ARE registered (+ `media_codecs_google_video.xml`).
  The codec tables in `video/video_codecs.md`, `video/software_rendering.md`, `codecs/media_codecs.md`
  presenting them as available are **correct**; OMX.Intel HW and c2.android SW decoders coexist.
- **`video/carplay_video_pipeline.md` / `cinemo_nme_framework.md`:** "NVIDIA NVDEC" SW decoder on
  an Intel platform is dubious → "Cinemo NME software H.264 decoder".
- **FAQ §19 fine-points:** the whitelist keys on activity `…applecarplay…AppleCarPlayProjection
  Activity` (not the `CarplayService`/`GMCarPlaySrc` service names); the full-screen gate is
  `CardViewComponentUtils.q()` not `VisibilityController.q()`; Settings.Global panel keys are
  written by `GMCarStatusBar`/`GMMicPrivacyChip`, not `VisibilityController`.
- **`audio_subsystem.md` / `automotive_audio.md`:** still carry detailed bus8–bus13 tables — keep
  the data but relabel each as Harman-HAL-internal (headline counts already fixed).
