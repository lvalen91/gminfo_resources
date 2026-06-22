# Live ADB Claim Verification — Y181 (Jun 2026 datapoint)

**Device:** gminfo37, fingerprint `gm/full_gminfo37_gb/gminfo37:12/W231E-Y181.3.2-SIHM22B-499.3/231`
**Build date:** Tue Jul 22 2025 (same Y181.3.2 firmware as the `apr2026` dump — this is a fresh *runtime* snapshot, not new firmware).
**Capture date:** 2026-06-21. **Access:** `shell` uid 2000, SELinux **Enforcing**, no `su` (root-gated reads denied as expected).
**Sources:** `enumeration_report.txt`, `raw/`, `claims_probe.txt`, `security_check.txt` (this dir).

---

## A. Claims REINFORCED by live device (match repo)

| Claim (repo) | Live evidence |
|---|---|
| RAM 5.66 GB kernel-visible | `MemTotal: 5663432 kB` = 5.66 GB ✅ exact |
| CPU 4-core (Apollo Lake / Goldmont) | `/proc/cpuinfo` 4 cores; model masked `IoT CPU 1.0`; GL renderer `HD Graphics 505 (APL 3)` = Apollo Lake = Goldmont ✅ |
| ABI x86_64 | `ro.product.cpu.abi=x86_64` ✅ |
| GLES 3.2 (`ro.opengles.version=196610`) | `196610` ✅ |
| Display DD134IA-01B, 2400×960@60, density 200 | `dumpsys display`: name=DD134IA-01B, 2400×960, fps=60.001434, density 200 ✅ |
| Display maker **Chimei Innolux (CMN)** (the corrected value, not Chunghwa) | `manufacturerPnpId=CMN`, productId=41268, mfg week36/2020 ✅ |
| No HDR / no VRR | `mSupportedHdrTypes=[]`, `alternativeRefreshRates=[]`, `allmSupported false` ✅ |
| Audio: **8** CarAudioService buses bus0–bus7, **6** VolumeGroups, 48 kHz | `bus0_`…`bus7_` (exactly 8), 6×`VolumeGroup(`, `48000 2 2` ✅ — confirms the corrected count |
| Video HW decoder `OMX.Intel.hw_vd.h264` (+h265/vp8/vp9, .secure) | present in `dumpsys media.player` ✅ |
| Cluster: `com.gm.vmsplugin/.VMSClusterService`, channels 10002/10003, `mIsCoreSupported:false` | all three verbatim in `dumpsys car_service` ✅ |
| Verified boot green / locked / sha256 / oem_unlock=0 | `verifiedbootstate=green`, `flash.locked=1`, `vbmeta.hash_alg=sha256`, `device_state=locked`, `sys.oem_unlock_allowed=0` ✅ |
| USB role-switch / dabridge `1-6.0`→`1-6.3`, `dabr_udc.0` | `sys.dabridge.host.portnum=1-6.0`, `sys.dabridge.dev.portnum=1-6.3`, udc `dabr_udc.0` ✅ |
| Kernel 4.19.305 | `uname -r = 4.19.305-240125T145315Z-gf1edde901aa7` ✅ |
| GHS INTEGRITY guest | `ro.boot.trustyimpl=-ghs`, `init.svc.ghs_cal=running` ✅ |
| Ports 6363 / 49156 / 9002 / 9016 listening | all four LISTEN in `ss -tlnp` ✅ |
| SELinux Enforcing, restricted shell (untrusted posture) | `getenforce=Enforcing`; root-gated reads denied ✅ |

## B. Gaps NEWLY RESOLVED (were "Unverifiable from available sources")

| Item | Prior status | Live result |
|---|---|---|
| GPU "HD 505 / Mesa 21.1.5" | unverifiable, no GL dump | **Confirmed** — `Mesa Intel(R) HD Graphics 505 (APL 3), OpenGL ES 3.2 Mesa 21.1.5 (git-4bdd81676b)` + git hash |
| Touch controller I²C **0x4B** | unverifiable, no address grid | **Confirmed** — `/sys/bus/i2c/devices/7-004b` bound; bonus addrs on bus 7: `0x0c`, `0x12`, `0x28` |
| Virtualized guest (GHS hypervisor) | inferred from RE | **Confirmed live** — guest block device is `vda` (virtio-blk), no `mmcblk*`; storage is behind the hypervisor |

## C. DISCREPANCIES — live device REFUTES current repo text (review needed)

1. **c2.android.* SW video decoders are PRESENT, not absent.**
   `VERIFICATION.md`/video docs say "the 12 c2.android.* SW video codecs are absent (only OMX.Intel HW video exists)."
   Live `dumpsys media.player` lists `c2.android.avc.decoder`, `c2.android.hevc.decoder`, `c2.android.vp8.decoder`, `c2.android.vp9.decoder`; `/vendor/etc/media_codecs_google_video.xml` is present.
   → The blanket "absent" claim is **wrong for this image**. SW video *decoders* coexist with the OMX.Intel HW path. (Encoders not separately confirmed; the "12 absent" recommendation should be narrowed/dropped.)

2. **Networking: live matches the PRE-correction values, not the "corrected" ones.**
   `VERIFICATION.md` "corrected" networking to *"only 9002/9016 @ 192.168.1.1; 9010 is outbound; 7000 transient (gone by Apr-2026)."*
   Live (Jun 2026):
   - Guest IP is **192.168.1.100** (eth0/vlan5), **not .1**. There is no `.1` interface or route in the guest table.
   - **9002, 9010, 9016 all LISTEN** on `192.168.1.100` — 9010 is a listener here, not merely outbound.
   - **7000 is LISTENING again** (0.0.0.0:7000 and `*:7000`) — not gone.
   → The original repo text ("9002/9010/9016 @ 192.168.1.100; 7000 ADB") is closer to ground truth than the applied correction. Recommend reverting/reconciling the networking row, noting state can vary by session/projection activity.

## D. New runtime data (not previously in repo)

- **WiFi AP bridge:** `br0 = 192.168.5.1/24` (wlan1+wlan2 bridged), DNS (`:53`) served on br0 + loopback — the wireless CarPlay/AA projection side.
- **VLANs on eth0:** `vlan5=192.168.1.100`, `vlan4=172.16.4.100`.
- **Projection app live:** top activity `zeno.carlink/com.carlink.MainActivity` running during capture.
- **Boot-load note:** load avg ~5.5 at 2 min uptime (see runtime/memory_pressure analysis).

## E. Still NOT obtainable via adb (root / SELinux gated — bounds the method)

- Raw EEPROM contents & I²C addr `0x50`: `/dev/i2c-7` is `system:system 0660`; shell(2000) can't open. `i2cget`/`i2cdump` exist on-device but nodes are gated.
- eMMC part number (KLMCG4JEUD): guest sees `vda`, not the eMMC — stays teardown-sourced.
- `/proc/partitions`, `/proc/cmdline`, `/proc/version`, `/system|/vendor/build.prop`: Permission denied (consistent with the documented restricted-shell posture).
- Full VHAL property count (535): `CarPropertyService` dump not reachable as shell; the head-limited `car_service.txt` capture doesn't list all props.

## F. Vulkan — RESOLVED (was 1.0.64, is 1.1.0)

The raw value `4198400` appears in **both** the repo dump and live `vkjson`. It decodes to `0x401000` = `VK_MAKE_VERSION(1,1,0)` = **Vulkan 1.1.0**. The repo's "1.0.64" label was a decode slip (1.0.64 = `4194368` = `0x400040`; the doc even mis-wrote `4198400 = 0x400040`). Corrected in `video/README.md`, `video/hardware_rendering.md`, `analysis/platform_faq.md`, and `VERIFICATION.md`. Runtime usage still nil (GLES 3.2 backend only).
