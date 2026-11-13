# Cross-Verification Record

Every factual claim in this repo was cross-checked (8 parallel verification passes) against
ground-truth sources: the **POTATO** ADB/logcat/metrics corpus, the **Y181/Y177 update
packages** (partition manifests + decompiled ELK/GHS/VMM/VIP artifacts), the **EEPROM `.bin`
dumps**, the **DPS session logs**, the **SELinux policy CIL**, decompiled **GMSystemUI**, and
the in-repo **ADB enumeration** dumps (Y175, Y181 Dec-2025, Y181 Apr-2026, **Y181 Jun-2026 live**).

> **Y181B recovery-export update, 2026-11-12:** both external ZIPs are identified
> in [capture provenance and comparison](research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12).
> They establish an exercised encoded log-capture marker, missing homescreen
> evidence for users 0/10, recovery-mode/argument distinctions, enforced AVC
> records despite a permissive boot property, and MEC=227 with Secure-ADB
> disabled on a user build. The measured recovery E820 map replaces the
> previous lack of hardware map evidence; the static-grant mismatch remains
> unresolved. The exported calibration DB has 2574 rows and
> `SCREEN_RESOLUTION=4`. The second ZIP changes 58 recovery files only;
> the other 387 files are byte-identical, so it is not a second independent
> Android/calibration observation. Historical captures below keep their
> original build/scope; no new live ADB or emulator run is implied.

> **Jun-2026 live update:** a fresh capture against the running radio (`enumeration/Y181/jun2026/`,
> same Y181.3.2 firmware) reinforced 16 claims, closed 3 "unverifiable" gaps (GPU, touch 0x4B, virtio guest),
> and **withdrew two earlier corrections** (c2.android codecs, networking) — see those rows below and
> `enumeration/Y181/jun2026/CLAIMS_VERIFICATION.md`.

> **[C] live-Y175 2026-10-05 update:** a fresh disk-only capture against a running **Y175** radio
> (`W213E-Y175.5.2-SIHM22B-383.1`, Android 12/API 32, patch 2024-05-05, kernel 4.19.283 x86_64,
> `/tmp/radio_audit/20261005_232227/raw/`) CONFIRMED the live-observable security posture on the
> Y175 variant (not just Y181): verified-boot `green`, `flash.locked=1`, `vbmeta.device_state=locked`,
> `oem_unlock_allowed=0`, `ro.debuggable=0`/`ro.secure=1`, SELinux **Enforcing** at runtime despite
> `ro.boot.selinux=permissive` in cmdline, and root `diagnosticsd` LISTENing on TCP `0.0.0.0:49156`
> (uid 0). It also **flipped one firmware-doc row**: the "DABridge USB topology Y175=1-12.x" variant
> discriminator is refuted (same Y175 build enumerates 1-6.x live vs 1-12.x in the prior enum — a
> physical-port artifact, not a firmware difference). See `platform/firmware_versions.md`,
> `platform/boot_chain.md`, `diagnostics/ethernet_uds_diagnosticsd.md`. Boot-ROM/CSE/SBL/AVB-key
> internals remain UNVERIFIABLE-FROM-LIVE. This does not alter any Y181/Y177 fact.

> **[D] live-Y175 2026-10-30 update:** a passive, read-only adb session against the same running
> **Y175** bench radio (`CJUD4R243a5edf`, `W213E-Y175.5.2-SIHM22B-383.1`, uid 2000 shell, no root,
> no reboot) narrowed several open items and surfaced one operational fact not previously
> recorded:
> - **Decluttered unit:** `pm list packages -u` shows **98 system packages uninstalled for user
>   0** (reinstallable via `pm install-existing`, not stock-absent) — includes `com.gm.hmi.*`,
>   `com.android.car.{media,dialer,settings}`, `com.google.android.apps.automotive.templates.host`,
>   `com.google.android.gms`, most `brand.chevrolet.*` RROs. Any future "app/process X is absent"
>   observation on this bench unit must be checked against this list before being reported as a
>   platform fact. `com.gm.domain.server.delayed` (hosts `CarPlayService` /
>   `RemoteDeviceService.RemoteDeviceService`) remains installed and running.
> - **Port 6363 identity — CORRECTION of an error made in this same pass (2026-10-30, caught by
>   re-checking, not by the review agents):** an earlier edit in this block wrongly attributed port
>   6363 to `calserviced` on a loose `grep -i '6363|1041|cald'` match. Re-checked directly: `ps -A -o
>   PID,USER,NAME` shows `calserviced` (PID 584) actually runs as uid **2900** (`vendor_cald`), not
>   1041 — a different process entirely. `/proc/net/tcp` confirms port 6363 (`0x18DB`) is owned by
>   uid **1041**, and `cat /proc/611/status` confirms **1041 is the `audioserver` group uid**, held
>   by 7 processes on this unit: `daemon_cl`(318), `avb_streamhandler_app`(340), `pulseaudio`(502),
>   `audioserver`(611), `vendor.hardware.audio@5.0-harman-custom-service`(772), `gmvt`(856),
>   `vendor.harman.audio.tuning@1.0-service`(860) — which one specifically holds the 6363 listening
>   socket (inode 18019) was not pinned down to one PID. This actually **confirms**
>   `platform/networking.md`'s existing "AVB audio daemon (uid=1041 audioserver)" line rather than
>   contradicting it — `calserviced` was never the right answer. The `ethernet_uds_diagnosticsd.md`
>   open-identity question for this port is **narrowed, not closed**: it's one of the 7
>   audioserver-uid processes above, most plausibly `avb_streamhandler_app` given the AVB-audio
>   framing, but not confirmed to a single PID.
> - **Port 49156 (`diagnosticsd`) socket-layer reachability from shell:** `ps -Z` confirms
>   `u:r:gm_diagnosticsd:s0`, root, pid 596; a plain TCP connect from uid 2000 shell
>   (`nc -w2 127.0.0.1 49156`, no payload) **succeeds** (`exit=0`) — the socket itself is not
>   SELinux/firewall-gated from an untrusted shell. This answers part (b) of
>   `ethernet_uds_diagnosticsd.md:330-333` ("reachable from uid=2000 shell") at the TCP layer;
>   whatever permission gate exists on the $22 DID read is at the UDS/application layer, not the
>   socket layer — that part stays open.
> - **FSA UDP port `:3000` vs `:30490`** (`platform/fsa_protocol.md:422`): neither port appears
>   bound in `/proc/net/udp` on this idle unit (no active CarPlay/AA session) — consistent with
>   the doc's own note that FSA binding is session-dependent, not a resolution of which port
>   number is correct.
> - **CT5/VCU-style routes do not exist on this Y175 Silverado unit:** `ip route get
>   192.168.118.1` and `ip route get 172.16.5.101` both return `Network is unreachable` — confirms
>   `projection/cluster_navigation.md`'s HMIC/RHMI-discovery open question concerns the CT5/Cadillac
>   platform specifically and is not an open question on this Y175/Silverado hardware at all.
> - **Networking topology re-confirmed unchanged:** `eth0`→`vlan5 192.168.1.100/24`,
>   `vlan4 172.16.4.100/24`, `br0 192.168.5.1/24` (wlan1/wlan2 bridged, wlan0 dormant) — matches
>   the Jun-2026/Oct-2025 captures above.
> - Still blocked by shell permissions as expected (re-confirmed, not newly closed):
>   `/proc/iomem`, `dmesg`/`klogctl`, `/dev/i2c-7` (`0660` root:root-equivalent), `/proc/partitions`,
>   `/sys/class/usb_role/.../role` read — all `Permission denied`/`Operation not permitted` under
>   uid 2000 with SELinux Enforcing.
> - `/vendor` and `/product` are mounted **ext4, ro** (not EROFS as several docs assumed) and are
>   directly readable from shell. **Correction + now actually completed:** an earlier pass here
>   claimed a full `/vendor/etc/init/**/*.rc` sweep for `dabr_udc|dabridge|portnum` but had in fact
>   only grepped two named files (`init.bxtp_gm.rc`, `init.full_gminfo37_gb.rc`). A real recursive
>   `grep -rl 'dabr_udc|dabridge|portnum' /vendor/etc/init/` was run this pass and genuinely found
>   **zero matches across the whole directory** — confirming `sys.usb.controller`/`sys.dabridge.*`
>   are not set by any init script on this unit, consistent with the existing finding that this is
>   set from dabridge kernel driver code, not an rc file. Narrows but does not close
>   `VERIFICATION.md`'s existing "where these are set" gap.
>
> **[E] live-Y175 2026-10-30 audio/video/runtime pass** (verifying the docs classified
> LIVE-VERIFIABLE in the Oct-30 doc-classification sweep):
> - **`audio/audio_subsystem.md` "exactly 8 CarAudioService output buses" and "6 VolumeGroups
>   VG0–VG5"** — both **CONFIRMED**: `dumpsys car_service` lists exactly `CarVolumeGroup(0)`
>   through `(5)` (6 groups) and exactly `bus0_media_out`…`bus7_system_sound_out` (8 buses) under
>   `*CarAudioService*`. `audio.safemedia.bypass=true` also confirmed via `getprop`.
> - **`audio/audio_subsystem.md`'s specific `ro.audio.flinger_standbytime_ms=0` and
>   `speaker_drc_enabled=false` system-properties claim is NOT CONFIRMED on this unit** — neither
>   property appears at all in a full `getprop` dump (654 props total) on this Y175 build; either
>   they're set through a different mechanism than a plain sysprop on this build, or the claim is
>   stale for Y175. Flagged, not corrected — needs a second look (parameter-framework XML vs
>   sysprop) before editing the doc.
> - **HIDL audio interfaces are declared but not bindable from shell:** `lshal` shows
>   `android.hardware.audio@5.0::IDevicesFactory/default` etc. with flags `DM,FM,FC` (declared in
>   manifest, found in manifest, found in client — i.e. lshal's own bookkeeping says it located the
>   entry), but `lshal`'s own preceding line for that exact interface is `Warning: Skipping
>   "...IDevicesFactory/default": cannot be fetched from service manager (null)` — the flags describe
>   lshal locating the manifest entry, not successfully binding the live service; no interface in
>   the audio group was actually fetched. The underlying narrowing claim holds, but "shows ... as
>   `DM`" (corrected here) understated what lshal actually printed. And
>   `/vendor/lib64/hw/audio.primary.broxton.so` / `/vendor/lib64/libias-audio-smartx.so` are both
>   `Permission denied` to `ls` even though the `/vendor` mount itself is ext4 ro-readable — per-file
>   group permissions (audioserver-only) block shell, not the mount. Narrows
>   `audio/intel_audio.md`'s binary-analysis claims: the described libraries are real (manifest
>   declares them) but shell cannot read or `strings` them directly to re-verify the binary-analysis
>   details in that doc.
> - **`video/video_codecs.md` / `video/software_rendering.md` "OMX.Intel.hw_vd.* coexists with
>   c2.android.* SW decoders"** — **RE-CONFIRMED on Y175** (previously only Y181 Jun-2026 live):
>   `dumpsys media.player` lists `OMX.Intel.hw_vd.{h264,h264.secure,h265,h265.secure,vp8,vp9}` +
>   `OMX.Intel.hw_ve.{h264,h265}` alongside `c2.android.{aac,amrnb,amrwb,av1,avc,flac,g711.alaw,
>   g711.mlaw,h263,hevc,mp3,mpeg4,opus,raw,vorbis,vp8,vp9}.decoder`.
> - **`video/hardware_rendering.md` GPU string** — **RE-CONFIRMED on Y175**: `dumpsys SurfaceFlinger`
>   reports `Mesa Intel(R) HD Graphics 505 (APL 3), OpenGL ES 3.2 Mesa 21.1.5 (git-2f9118e594)` —
>   same GPU/driver string as the Y181 capture (different build hash suffix, same version).
> - **`video/display_subsystem.md` panel identity** — **RE-CONFIRMED on Y175**:
>   `dumpsys display` reports `DD134IA-01B`, `manufacturerPnpId=CMN`, 2400×960, density 200 —
>   matches the corrected Chimei-Innolux finding live.
> - **`runtime/memory_pressure.md` MemTotal** — re-confirmed unchanged: `/proc/meminfo` MemTotal =
>   5,663,436 kB (5530 MiB), matching the existing RAM-gap entry above.
> - **`runtime/known_issues.md` `ForegroundServiceStartNotAllowedException` boot race** — **NOT
>   CONFIRMED this pass**: zero hits in the current `logcat -d` buffer. Inconclusive, not a
>   refutation — the issue is boot-time-only. **Correction (caught by review agent):** the earlier
>   claim here that the buffer's oldest `boot_progress_*` entries are "from a prior boot in June,
>   not the unit's most recent boot" overlooked the buffer's actual oldest line,
>   `11-11 02:11:15.886 ... boot_progress_start: 4839`, dated *after* the June entries despite
>   appearing first in the dump — inconsistent with simple chronological ordering. Given this bench
>   radio's known clock-drift issue (no NTP source on the bench), that `11-11` timestamp is at least
>   as plausible a candidate for the *current* boot's `boot_progress_start` as it is stale data; the
>   buffer's actual boot coverage is genuinely unresolved, not confirmed either way. A clean re-test
>   of the exception itself would need a fresh reboot capture, which was intentionally not done this
>   session per the no-reboot constraint.
> - **`platform/fsa_protocol.md`'s "Android guest's own FSA servers (9002/9010/9016) keep
>   additional connections open and are fully queryable from the shell" claim is NOT CONFIRMED
>   right now on Y175** — a full `/proc/net/tcp` dump shows only ports 6363, 7000, 49156 (+ loopback
>   DNS) bound; **9002/9010/9016 are absent**, even though the FSA-hosting process
>   (`com.gm.domain.server.delayed`, plus its `:CarplayService`/`:GALService` children) **is
>   running**. Port 9011 ("dead code" claim) is consistent with this — also absent — but so is
>   everything else, so this isn't a clean confirmation of the 9011-specific claim either. Possible
>   explanations not yet distinguished: FSA TCP listeners bind lazily on first use/partition
>   handshake rather than at process start, or something else about this decluttered/idle state
>   suppresses them. Flagged, not corrected.
> - **`platform/gmsystemui_app_capability_gating.md`**: the cited `GMSystemUI.apk` is confirmed to
>   exist exactly where the doc implies — `/system/priv-app/GMSystemUI/GMSystemUI.apk` (+ oat/vdex)
>   — so the static-RE source material is real on this exact unit. The live behavioral claims (does
>   CarPlay actually fail to get the WhiteList capability) could not be exercised this pass: both
>   `com.gm.hmi.applecarplay` and `com.gm.hmi.androidauto` are currently in the declutter
>   uninstalled-package list (see `[D]` block above) — would need `pm install-existing` on both
>   first.
> - **`projection/carplay_vs_android_auto.md`**: all `libNme*.so` CarPlay libraries (including
>   `libNmeVideoSW.so`, `libNmeCarPlay.so`, `libNmeIAP.so`, `libNmeAppleAuth.so`, **25 total** —
>   corrected from an initial miscount of 19 by a review-agent audit) confirmed
>   present under `/system/lib64/` — these are shared system libraries, unaffected by
>   `com.gm.hmi.applecarplay` being in the declutter-uninstalled list.
> - **`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`**: this doc already carries its own
>   prior-session `[C] live-Y175 2026-10-05` annotations confirming uid=2000 shell groups
>   (`log/inet/readproc/uhid/readtracefs`), `ro.boot.selinux=permissive` cmdline vs Enforcing
>   runtime, and SBI/ADB posture on this exact Y175 unit — independently re-confirmed this pass
>   (`id`/`getenforce`/`getprop` match), no new edit needed. Did **not** attempt the kernel
>   KASLR-slide measurement, `perf_event_open` sampling, or any escalation vector in that doc's
>   §2/§4 — those are offensive-security actions out of scope for this information-gathering pass,
>   not just untested.
> - **[F] live-Y175 2026-10-30, extraction-agent-sourced batch — real hardware only, no VM
>   cross-check yet** (Y175 VM not running; Mac Pro has no copy of `y175_realk/` — see status note
>   at end of this file). Pending the ≥2-agent verification the owner requires before these count as
>   confirmed:
>   - `analysis/platform_faq.md` Cluster HAL flags — **CONFIRMED exact match**:
>     `mIsCoreSupported:false`, `mIsNavigationStateSupported:false`,
>     `mRenderingServiceConfig:com.gm.vmsplugin/.VMSClusterService`.
>   - `platform/ota_update_stack.md` "no permission check on read methods" — **CONFIRMED**:
>     `UpdateService` Tx1/2/3/6/30 all reachable from uid=2000 shell with no `SecurityException`;
>     Tx3 (`getUpdateHistory`) returned a real path — **correction (caught by review agent): the
>     parcel's own ASCII gutter decodes to `/update_cache/update/027` (slash before `027`), not
>     `/update_cache/update_027` (underscore) as first transcribed** — Tx30 (`getReflashAttempts`)
>     returned `4` (differs from the doc's Y181 value of 9 — expected, different unit/history, not a
>     contradiction).
>   - `projection/cluster_navigation.md` cluster-service naming reconciliation (`:220`) —
>     **RESOLVED, not either/or:** `com.gm.vmsplugin` (PID 2218) **and** `com.gm.cluster` (PID 2258)
>     are **both** running simultaneously, and `clusterService [gm.cluster.IClusterHmi]` is
>     registered — the doc's "superseded naming" framing was wrong; both exist concurrently.
>     `ClusterService.apk` (2,916,440 B) and `/system/framework/info3_cluster.jar` (338,174 B) both
>     confirmed present at the exact cited paths.
>   - **RESOLVED, corrected twice:** first pass guessed "absent" from the wrong registry
>     (`service list`, native Binder). Second pass checked `lshal` instead and read its "cannot be
>     fetched from service manager (null)" warning as "not bound." **That was also wrong** —
>     `ps -A` shows both processes genuinely running: `vehiclepanel` (PID 859, user `system`) and
>     `vendor.harman.navsens@1.0-service` (PID 602, user `vendor_navsens`). `lshal`'s "cannot be
>     fetched" is the same shell-side HIDL-introspection permission barrier already established for
>     the audio HAL interfaces earlier in this file (SELinux denies the *diagnostic dump* to shell,
>     which is not the same as the service being down) — it never meant "not running." Both
>     services are live; `lshal`'s failure to fetch them for display is expected and uninformative
>     about actual service state.
>   - **REFUTES, not just "flagged":** `md5sum`/`ls` on `/system/bin/init` and `cat /proc/cmdline`
>     both return explicit `Permission denied` from uid=2000 shell — the same strength of evidence
>     as the `br0` refutation above, so using the weaker "not confirmed" wording here (as an earlier
>     pass of this edit did) understated it. The cmdline denial matches existing doc annotations;
>     the `/system/bin/init` denial is new and directly contradicts
>     `Y175_OS_PARTITION_INVESTIGATION_AUG2026.md`'s assumption that this file is plainly
>     shell-readable/hashable — it is not, on this unit.
>   - `persist.vendor.harman.hardwareid` and `vendor.harman.ethernetswitch` — **NEITHER property is
>     set** on this unit (both return empty), so the board-variant (Broadcom/Marvell switch)
>     discriminator these props are supposed to carry could not be exercised here.
>   - `persist.vendor.audio.audioConf`, `persist.vendor.eavb.mode`, `init.svc.vendor.avbstreamhandler`,
>     `vendor.avb.streamhandler.ready` — **all four empty/unset** on this unit, contradicting
>     `vehicle_network.md`'s specific claims about these properties' values.
>   - `/dev/ghs/` — **re-enumerated with real differences from every doc's generic table:** present
>     nodes are `audit`, `cal`, `camera` (owner `system:system`, not `root:root`), `capture`
>     (**undocumented in any doc read this pass**), `chime` (owner `system:system`), `emmc-health`,
>     `ipc`, `ota-isys`, `tee-att` (mode `crw-rw----`, not root-only), `textlog`. **`gpu-dbg` is
>     absent entirely** (not just denied — not listed), and `snapshot-dbg` exists but `stat` fails on
>     it (`-?????????`, shown with no owner/perms/major/minor). This is the first real enumeration of
>     this directory on live Y175 — prior docs only confirmed the directory itself exists.
>   - `perf_event_paranoid = -1` — **CONFIRMED**, matches `SHELL_ACCESS_ESCALATION_Jun2026.md`'s
>     cited value exactly. `CapEff = 0000000000000000` — shell holds zero effective capabilities.
>     `ro.boot.bootreason = cold` (this boot was cold, not warm — relevant context for the
>     `gm_protokey` warm-boot-skip claim, which could not be exercised this way).
>   - `persist.vendor.gm.*` namespace — **CONFIRMED genuinely absent** (zero matches in a full
>     `getprop` dump), matching `props_calibrations.md`'s cross-Y181-session finding, now also true
>     on Y175.
>   - SOME/IP-SD multicast group `239.192.0.1` — **NOT joined** right now (`ip maddr show` empty) —
>     consistent with the already-established pattern that this unit's FSA/projection stack is
>     currently idle (ports 9002/9010/9016 also down, per the `[E]` block above — **correction: not
>     `[D]`**, which only covers the unrelated UDP `:3000`/`:30490` discovery-port question).
>   - `eth0` driver — **CONFIRMED** `igb_avb` (custom driver, not mainline `igb`), matching
>     `hardware.md`'s claim exactly. `/dev/block/by-name/misc` **CONFIRMED** symlinks to `vda9`,
>     matching `boot_chain.md`'s partition map.
>   - `br0` — **REFUTES in full** `T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md:26`'s claim
>     that it's "down with no IP" (verified against that file directly: it does say exactly that).
>     First check only grepped for `inet` lines and missed the flags line; re-run without the
>     filter: `11: br0: <BROADCAST,MULTICAST,UP,LOWER_UP> ... state UP`, `inet 192.168.5.1/24`. Both
>     halves of the doc's claim are refuted — `br0` is genuinely UP, not just IP-assigned. Matches
>     the WiFi-AP-bridge role already established elsewhere in this repo.
>   - ARP table has no `.106` entry — confirms IPC is absent/unreachable on this bench, as expected.
>   - `/dev/ttyACM1`, `/dev/i2c-{0,1,2,3}` — **re-confirmed** world-writable (`crw-rw-rw-`) for the
>     third time this session, now via a third independent extraction-agent-sourced check.
>   - `com.android.dynsystem` — confirmed absent from `pm list packages`; `gsi_tool` confirmed
>     present (`-rwxr-xr-x root shell`); `gsid` itself could not be `ls`'d (`Permission denied`), so
>     its presence is not independently re-confirmed this pass (only inferred from the doc + prior
>     `service list` evidence, not newly proven).
>   - `/dev/ttyACM1` passive read — **differs from the hypothesis in `UNTRIED_ATTACK_VECTORS.md`
>     vector #14**: the doc predicted a silent read (data-layer block, open succeeds, nothing
>     arrives); the actual result is an explicit `Permission denied` on the read itself — a DAC/MAC
>     block at open-time, not a silent data-layer gap. Refines, does not just confirm, that vector.
>   - FBE (`ro.crypto.state=encrypted`, `type=file`) and kernel string
>     (`4.19.283-PKT-230612T042614Z-ga53d763f5b0d`) — both re-confirmed, no change.
>   - Everything else attempted in this batch (`/config/usb_gadget`, `/vendor/bin/hw/gm_update_engine`,
>     `/vendor/bin/rb_ua`, `/data/vendor/gm/security/*`, `/data/gmprotokey/trigger/`,
>     `/sys/class/net/eth0/address`) returned `Permission denied` — consistent with the established
>     pattern that most `/vendor/bin`, `/data/vendor`, and individual device-node reads are
>     DAC/MAC-blocked for uid=2000 even though their parent mounts are readable.
>
> **[G] live-Y175 2026-10-30, further extraction-batch checks — NOT YET independently
> 2-agent-verified, pending that pass before treating as confirmed:**
> - **`research/OTA_MODULE_PROGRAMMING_ROLES.md`** FSA ports 9010/9011 — both **absent** right now
>   (`/proc/net/tcp` has no `0x2332`/`0x2333`), consistent with the whole FSA stack being idle on
>   this unit (per `[E]`). `fw_update_slota`/`fw_update_slotb` init services are **unset** — not
>   present on this Y175 build at all (possibly Y181-only). `cmd_fw_update_vendor` confirmed present
>   as a symlink to `abl-user-cmd_vendor`; `fw_update.sh` itself `Permission denied`.
> - **`research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`** serial device labels — **CONFIRMED exactly**:
>   `ttyS0` → `bluetooth_serial_device` (`crw-rw---- bluetooth:bluetooth`), `ttyS1` →
>   `ipc_serial_device` (`crw------- root:root`, static since boot), `ttyS2` → `serial_device`
>   (`crw------- root:root`, static since boot). `ttyS0`'s mtime is today, unlike the other two's
>   static 2011 epoch stamp — **correction (both review agents flagged this): that contrast does
>   not by itself prove "actively in use."** Android character-device nodes get their mtime at
>   `ueventd` (re)creation, not continuously from ongoing I/O — a one-off recent bluetooth
>   pairing/connect event or a bluetooth-stack restart explains the timestamp equally well.
>   Noted as a timestamp difference, not evidence of current activity.
>   `ro.boot.dynamic_partitions=true` — **CONFIRMED set**, alongside `ro.boot.slot_suffix=_b` —
>   consistent with `boot_chain.md`'s own correction that this prop exists but the real partition
>   layout underneath is static A/B, not actually dynamic/`super`.
> - **`research/session_logs/RESEARCH_STATE_MAP_JUN2026.md`** — GHS partitions (`ghs_isys`,
>   `teedata`, `cert_*`) **CONFIRMED not mounted** in Android (`mount` grep empty). Trusty-via-ACPI
>   claim **CONFIRMED**: `kworker/0:2-trusty-timer-wq` and `kworker/u8:5-trusty-check-wq` kernel
>   threads are both present and running, despite `/tos`/`/multiboot` being commented out of fstab —
>   exactly the "loaded via ACPI/SSDT, not fstab" mechanism the doc describes.
> - **`emu/y181_ref/unstub/vendor_daemons.md`** parity check (Y181-sourced claims, re-tested on
>   Y175) — **all CONFIRMED running**: `vendor.gm.gmlocation@1.0-service` (uid `vendor_gm_location`),
>   `vendor.harman.hardware.ame@1.0-service`, `vendor.harman.hardware.bluetooth@1.0-service`,
>   `vendor.harman.navsens@1.0-service` (uid `vendor_navsens`, PID 602 — see the panel/navsens
>   correction above), `vendor.hardware.audio@5.0-harman-custom-service`, `gmvt`,
>   `vendor.harman.audio.tuning@1.0-service`, `vendor.harman.tuner-service`,
>   `vendor.gm.ffsd@1.0-service` (root). All of these Y181-vintage claims hold on the older Y175
>   build too.
> - **`Y175_OS_PARTITION_INVESTIGATION_AUG2026.md`** md5 claims for
>   `gm_protokey_recovery`/`gm_protokey`/`diagnosticsd`/`libpal_security.so` — **could not be
>   re-checked**, all four `md5sum` attempts returned `Permission denied` from uid=2000 shell (same
>   DAC/MAC pattern as every other `/vendor/bin` binary this session). The
>   `plat_sepolicy_and_mapping.sha256` sidecar **was** readable: live value is
>   `fbf306ba054865d30c2315bdff08fe47aebf5120a2e6505eef45930b3bce4587` — **differs from the doc's
>   cited `66e115a7...`**, but that's expected, not a contradiction: the cited value is for a
>   different build (Y181), and sepolicy hashes are build-specific by design. Not independently
>   compared against this unit's own vendor-side sidecar (that half of the check wasn't run).
> - **i2c-4/5/6** — **CONFIRMED** root-only `crw-------`, matching every doc's generic i2c table.
> - **USB gadget `idVendor`/`idProduct` via `/sys/class/android_usb/android0/`** — both
>   `Permission denied`; this specific path/property pair could not be checked this way.
>
> **[H] Y175 real-kernel VM status + cross-check, 2026-10-30 — SOFTWARE/VM, NOT REAL HARDWARE,
> read everything below with that label attached. NOT YET independently 2-agent-verified.**
>
> Transferred `y175_realk/` (11 GB) + shared infra (`tools/`/`sdk/`/`jdk/`/`hy/`/`bin/`, ~45 GB) to
> the Mac Pro (`macPro.zcarp`, Intel x86_64, 381 GiB free); `gm.img` md5 verified identical
> pre/post-transfer (`b1f4f7969581bcf7b0fd4b41736749d1`). `gmemu`'s own path handling didn't support
> `y175-realk` out of the box (hardcoded absolute paths baked in at creation time, and `VERSIONS.md`
> itself already flagged y175/gmemu integration as "TBD") — remapped those paths in the *transferred
> copy only* and launched `y175_realk/boot.sh` directly (`GPU=swfb`, stock kernel, headless,
> Homebrew QEMU + HVF). Booted successfully (PID confirmed alive, `gmscreenready` broadcasts
> completing). `adb` requires on-device USB-debugging authorization that can't be tapped headless;
> used the documented serial root-shell (`ttyS3` via `gsh.py`) instead — this **is root**, unlike
> the real radio's uid=2000 shell.
>
> **Critical caveat found immediately, must govern every claim from this VM:** the shell's own
> SELinux domain (`u:r:vendor_init:s0`) is **permissive for several AVC classes even though
> system-wide `getenforce` reports Enforcing** — `dmesg` shows `avc: denied ... permissive=1` for
> `toybox` execute, `kmsg` read, and `syslog`/`syslog_read`, meaning those actions were logged as
> denied but **not actually blocked**. This is a VM-only debug accommodation for the serial
> root-shell mechanism, not representative of the real locked radio's enforcement. Every
> permission-looser result below is a property of this VM's dev-shell path, not evidence about the
> real unit's security posture.
>
> **What the VM could and couldn't actually resolve, against the real-radio open questions:**
> - `/proc/iomem` — **readable in the VM, but does NOT resolve the real unit's 7830→5530 MiB RAM
>   gap question.** The VM's guest RAM is a flat `qemu -m 5120` allocation (confirmed directly in
>   the live `qemu-system-x86_64` process args captured when it was launched) with no
>   GHS-hypervisor partitioning at all — a structurally different memory model from the real
>   hardware, not a smaller instance of the same one. Not usable evidence either way.
> - `/dev/i2c-7` (touch) and the EEPROM-relevant `/dev/i2c-0`–`i2c-3` — **don't exist in the VM at
>   this boot.** `ls /dev/i2c-*` shows only `i2c-6` and `i2c-8` — the VM's I2C hardware model looks
>   entirely synthetic. **Correction (both review agents converged on this): "not testable, full
>   stop — structurally" overclaimed permanence from one `ls` snapshot at one boot.** A single
>   enumeration can't rule out a later hotplug/deferred-probe node appearing; what's actually
>   established is "absent in this boot's device enumeration," not a structural guarantee across
>   all boots. The EEPROM-at-0x50 question stays untestable on the evidence gathered so far, not
>   proven untestable in principle.
> - `/system/bin/init` md5 (`5a6dfe236c3beafe28ca079c9a451d94`) — **readable, but not usable to
>   validate or refute any real-device init-hash claim.** `y175_realk/ramdisk_patched.cpio` is, by
>   its own filename, a **patched** first-stage ramdisk assembled for VM boot compatibility — its
>   `init` binary is not guaranteed byte-identical to the real device's.
> - `/proc/cmdline` (readable in the VM) — **not independent evidence about the real firmware's
>   cmdline either.** The `androidboot.selinux=permissive enforcing=0` tokens seen here were put
>   there by `boot.sh`'s own hardcoded `-append` flags (visible directly in the live `qemu-system-
>   x86_64` process args) — reading them back from `/proc/cmdline` is circular, not a cross-check.
> - `dmesg`/kernel log access that was `Permission denied` on the real radio **worked here** — but
>   per the caveat above, only because this domain is permissive for `syslog`/`kmsg`, not because
>   the real device's denial was somehow wrong.
>
> **Net assessment:** this VM is a genuinely useful tool for Android-guest-userspace-level
> exploration (same build-label fingerprint, a real root shell) — **correction (both review
> agents flagged this): "same SELinux policy file" was an unevidenced assumption, struck.** No
> sepolicy hash/file comparison between the VM and the real unit was ever run here (contrast `[G]`,
> where a sepolicy sidecar hash genuinely was pulled and compared on the real device) — the VM's
> policy is presumed similar because it ships the same build label, not independently verified
> byte-identical. But it does
> **not** have a faithful hardware model for the specific things the real radio's shell permissions
> were blocking in this session (RAM e820 layout, I2C/EEPROM, binary integrity of a possibly-patched
> ramdisk). None of it should be written into any doc as settled fact about the real Y175 unit
> without saying "per the Y175 VM, software only" every time, and without first getting the
> ≥2-agent verification the owner requires for every finding — none of this `[H]` block has that
> yet.
> - **`platform/security.md` / `platform/boot_chain.md` — 25-day stability re-check, no doc edit
>   needed:** both files already carry extremely dense 2026-10-05/06/08/10 `[C]` live-confirmation
>   annotations from a prior session. Spot-re-checked 5 items independently today (2026-10-30,
>   25 days later) rather than trusting the dated annotations unverified: all 5 "critical service
>   domain" processes (`gm_vnd_IPCServer`/`IPCServer`, `gm_diagnosticsd`, `gm_update_engine`,
>   `gm_vehicle_hal`, `gm_protokey`) still running under the same SELinux domains and root/
>   vehicle_network ownership (PIDs differ, as expected); `i2c-0/1/2/3` still `crw-rw-rw-` (0666)
>   world-writable; `/dev/trusty-ipc-dev0` still `crw-rw-rw-`; `com.android.dynsystem` still absent
>   from `pm list packages`; `com.gm.authtoken` still running as `system`. Zero drift found across
>   the 25-day gap.
> - **Cross-repo finding, not a Y175-session result:** `GM_research/.../docs/specs/
>   gminfo3.7_tech_specs.md` was flagged LIVE-VERIFIABLE by the classification pass, but reading it
>   shows its `build_fingerprint` is `W231E-Y177.6.1-SIHM22B-499.2` — **a Y177 unit, not this Y175
>   radio** — captured at a different time (its own `selinux: permissive`, `boot_count: 254`,
>   `uptime_stability: 4.8_days`, WiFi SSID/paired-phone fields are that other unit's point-in-time
>   state, not reproducible here). Only the hardware-platform-invariant fields (CPU/GPU model,
>   display panel, Aptiv USB VID 0x2996=10646 decimal) are meaningfully cross-checked by this
>   session's live data; the transient/build-specific fields are out of scope for this Y175 adb
>   session and were wrongly bucketed as straightforwardly live-verifiable. Flagged in that file
>   directly (see GM_research correction banner).
> - **Same pattern, second file:** `GM_research/.../ref_repo/gminfo37_network_research.md` (the
>   other doc the classification pass called plainly LIVE-VERIFIABLE) states build fingerprint
>   `W231E-Y181.3.2-SIHM22B-499.3` — again a different unit (Y181) than this Y175 radio. Its
>   topology/partition/MAC tables are that unit's capture, not re-verified against Y175 this pass;
>   only its general unprivileged-shell posture claims transfer across builds. Flagged in that file
>   directly.

> **[I] live-Y175 2026-11-02 Bus 2 direct T1 tap, bench-confirmed, 2-plus-source agreement
> (`T1_RADIO_core.txt` + `T1_RADIO_NETWORK_STRUCTURE.txt` (external bench corpus, not in this
> repo; full paths recorded in `research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`
> [S108]/[S110]) + the dated breakthrough note, all
> transcribed into `Y175_LIVE_RADIO_T1_SECURITY_ASSESSMENT_2026-11-02.md`):**
>
> - **Root cause, prior "duplex mismatch" theory refuted:** hours of failed inbound VLAN-tagged
>   injection on Ethernet Bus 2 (A11↔K56 gateway) were caused by a plain Ethernet switch in the
>   tap path silently stripping 802.1Q VLAN tags, not a duplex mismatch (untagged frames passed
>   the same 100-half link fine). Fix: a BUELEC 100/1000Base-T1-TX-L media converter (Marvell
>   88Q2112 + Realtek RTL8211FI) run at 100M, direct to a USB-GbE NIC, no switch in path.
>   Confirmed bidirectional into `vlan5` (tagged ARP frames both directions). T1 pair polarity
>   had to be manually swapped despite the datasheet's claimed auto-adaptivity.
> - **VLAN map, Bus 2:** VLAN 2/PCP 2 = AVB (~2,900 pps, harmless bench flood); VLAN 5/PCP 1 =
>   `192.168.1.0/24` Info3.x service plane (radio `.100`); VLAN 4/PCP 1 = `172.16.4.0/24`
>   internal/diag plane (radio `.100`); untagged = native. Radio MAC on both tagged VLANs =
>   `02:04:00:00:01:00`; no default gateway. `br0` (`192.168.5.1/24`) is the Wi-Fi/phone-
>   projection AP bridge (members `wlan1`/`wlan2`), **not** a diagnostic plane — this corrects an
>   earlier assumption in some docs.
> - **Full 1–65535 port scan per plane, all 253 source addresses per /24:** only
>   `192.168.1.100:9016` (NetworkAccessManager, allow-list `{.102,.112}`), `:9002`
>   (RemoteModuleHMI, allow-list `{.106,.109,.112}`), and `172.16.4.100:49156` (diagnosticsd,
>   allow-list `{.107,.112}`) are reachable. No undocumented allow-listed identity and no
>   undocumented listening port exist anywhere in either /24. `diagnosticsd` remains
>   UDS-application-layer locked (`generalReject` NRC `0x10`, source-IP-independent) regardless
>   of allow-list admission. CGM `.112` is the only identity reachable on both planes.
> - **Scope:** bench only (gateway peer absent, so discovery chatter/flooding is amplified
>   relative to an in-vehicle capture); the allow-list/port findings are bounded to the tested
>   source addresses and capture window, not proof the allow-list cannot be bypassed from an
>   authorized/compromised peer. Docs updated: `platform/vehicle_network.md`,
>   `diagnostics/ethernet_uds_diagnosticsd.md`, `research/MASTER_REFERENCE.md`,
>   `research/GM_REMOTE_ACCESS_ANALYSIS.txt`.

Bottom line: the bulk of the repo verified **CONFIRMED**. The errors found are listed below;
the **Corrected** ones have been fixed in-tree. CCPA/CPC200 adapter material was out of scope
(separate repo).

## Corrected (applied)

| Area | Was | Now (verified) |
|------|-----|----------------|
| RAM type/capacity | "6 GB DDR3L" (8 docs) | **8 GiB LPDDR4** physical; static GHS guest grant 7830 MiB (+34 MiB RO IPU window); historical Android `MemTotal` near 5530 MiB. Y181B recovery E820 usable **5743.55859375 MiB**, measured 2026-11-12; grant-to-visible cause unresolved. [Map and limits](research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory) |
| eMMC model | KLMBG2JETD-B041 (32 GB part #) | **KLMCG4JEUD** (64 GB, teardown-verified) |
| Display maker | Chunghwa | **Chimei Innolux** (PnP `CMN`) |
| Audio output buses | "14" / "12+" (README + 4 audio docs) | **8** CarAudioService buses (bus0–bus7), confirmed in `car_service.txt`; bus8–bus13 are Harman-HAL-internal graph nodes, not CarAudioService buses |
| Audio HAL name | `vendor.hardware.audio@5.0` "Titan" | `android.hardware.audio@5.0` (HarmanHAL); **"Titan" = SoC platform codename**, not the HAL |
| firmware_re fn count | 117 | **115** (`ls out_vip_app/*.c`) |
| VHAL: RANGE_REMAINING | "not present (ICE)" | **present** (0x11600308) |
| VHAL: FUEL_LEVEL_LOW | 0x11600308 | correct ID **0x11200405** (0x11600308 is RANGE_REMAINING) |
| VHAL: HVAC | "standard HVAC IDs ALL ABSENT, GM non-standard" | **standard AOSP HVAC IDs present** (0x15400500/501 fan, 0x15600502/503 temp); CarHvacManager fan/temp works |
| Networking ports | 9002/9010/9016 @ 192.168.1.100; 7000 ADB **[2026-11-12 CORRECTION: port 7000 is AirPlay/AirTunes per platform/networking.md (uid 1001000; `GET /` -> `Server: AirTunes/...`); ADB is 5555 and not listening (platform/security.md); the 'ADB' label is wrong, the listening-state re-confirmation below stands]** | **RE-CONFIRMED to original by live Jun-2026 capture**: guest IP is **192.168.1.100** (eth0/vlan5; no `.1` iface or route in guest), with **9002/9010/9016 + 7000 + 6363 + 49156 all LISTENING**. The earlier "9002/9016 @ .1, 9010 outbound, 7000 gone" correction was a single-dump artifact (state varies by projection session) and is withdrawn. WiFi-AP side: `br0 192.168.5.1/24` serves DNS :53; vlan4 `172.16.4.100`. |
| CAN tester ID | Req 0x14DA80**F1** / Rsp 0x145AF1**80** | captured DPS session uses **F2** (0x14DA80F2 / 0x145AF280); F1 = generic OBD tester address |
| EEPROM unlock guide | only 0x441/0xa81 documented | **(corrected 2026-11-12, per `eeprom/README.md`'s 2026-11-11 owner-corroborated recipe, which supersedes an earlier 4-byte claim in this row):** the minimal/sufficient Y181 edit is **0x0441→0xFF and 0x0A81→0xFF only**. `0x1A01` is not an established second SBI mirror, and `0x0B41` writes were tested across the full value range (`0x00`/`0x01`/`0xFF`) with no observed ADB/SELinux effect — neither is required. |
| 0x0A00/0x0B00 ref counts | 871/311 stated as fact | flagged: 871 vs 854 / 311 vs 305 across passes; RE-sourced, not dump-reproducible |
| `boot_chain.md:136` A/B metadata magic | comment said `"AVB0" or similar` | **(2026-09-10)** `\0AB0` — the misc/BCB slot-metadata magic is a **different, distinct magic** from the vbmeta `AVB0` magic used three lines above it in the same doc. Byte-confirmed via `vbmeta.img` (offset 0 = `41 56 42 30` = stock libavb `AVB_MAGIC`; header 100% upstream: RSA2048/SHA256, avbtool 1.2.0, flags=0x00000000 = verification NOT disabled, zero GM-specific fields). Raised by GitHub issue #1 (@DymOK93). |
| ELK boot target | implied Linux/USB-storage shell in places | **(2026-09-10)** ELK is **Intel Kernelflinger fastboot** (kernelflinger-07.02, titan_gm_my22): flash/erase/getvar + `oem set-storage`; explicitly **"USB storage is unsupported"** (no external USB rootfs path); libavb-linked, AVB ACTIVE in ELK; unlock is device-state-gated. Not a general-purpose shell. |
| VIP "Y177 stub" @0xb67d0 | "Y177 = 4-byte stub, Y181 = full 906 B" (stated as fact in 6+ docs) | **(2026-09-10, byte-verified — was previously "unverifiable")** NO stub ever existed. Direct binary compare of VIP firmware `86283151` (Y177) vs `86331656` (Y181): the validator is the **same full ~906-byte function relocated +4 bytes** — 502/512 leading bytes byte-identical (Y177 @0xb67d4 == Y181 @0xb67d0), the ~10 diffs are absolute-address operands offset by the relocation delta. Y175 @0xb6708 consistent. The "4-byte stub" was a fixed-address/frame-shift misread. Refutes `MASTER_REFERENCE`, `DPS_MASTER_REFERENCE`, `VIP_FIRMWARE_Y177_Y181_COMPARISON` §2, `EEPROM_*`. |
| Y177 SELinux mode | "permissive (regression)" in several docs | **(2026-09-10, byte-verified)** **Enforcing at runtime.** `system/bin/init` is byte-identical across Y175/Y177/Y181 and compiles `ALLOW_PERMISSIVE_SELINUX=0`, forcing Enforcing regardless of the `selinux=permissive` cmdline token; any live-permissive Y177 was a modified/eng unit. Same posture as Y181. |

## Confirmed against ground truth (high-value spot-checks)

- **Hardware:** CPU Goldmont 4-core (cpuinfo), display DD134IA-01B 2400×960@60 density 200
  (display_info), kernel 4.19.305/4.19.283, fingerprint Y181.3.2, ABI x86_64, WiFi 2.4 GHz lock,
  GLES 3.2 (`ro.opengles.version=196610`).
- **Boot/firmware:** GHS INTEGRITY IoT **2020.18.19 MY22-026** (ghs_analysis), kernelflinger-07.02
  (elk_strings), libavb chain, A/B-CRC failure strings, security-patch levels (Y175 2024-05-05,
  Y181 2025-06-05), VIP **RH850/F1K** G3KH core (the "V850" Ghidra label was an abandoned prior-analyst
  approximation), UDS $27 in DPS, identical VIP_BOOT/HOSTOS/ABL across Y177/Y181.
- **Security:** Y181 Enforcing at runtime (user build ignores `selinux=permissive` cmdline);
  `untrusted_app` has usb_device ioctl/read/write/getattr but **not open** (plat_sepolicy.cil);
  no carlink/usbmountreceiver rules; AVB locked/green/sha256, oem_unlock=0; ports 6363/49156/9002/9016.
- **EEPROM:** **(corrected 2026-11-12 — see the "EEPROM unlock guide" row above)** the
  Y181_stock→modified diff between dumps compared earlier included 4 changed bytes
  (0x441/0xa81→FF, 0x0B41→01, 0x1A01→FF), but the owner-corroborated 2026-11-11 minimal recipe
  shows only **0x0441→FF and 0x0A81→FF are required/sufficient**; 0x0B41 and 0x1A01 are not an
  established second SBI mirror and produced no observed ADB/SELinux effect when tested. CRC
  words present at 0x16E0/0x19E0/0x1A80/0x1B40/0x1B60/0x1B80 and untouched by redaction;
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
- **USB/ADB:** ADB role-entry is the **Developer-Options USB-debugging toggle** (owner-confirmed 2026-10-10: ADB off + Mac VBUS present = nothing enumerates; toggle = ADB) → software role-switch; **VBUS-sense auto-role RULED OUT**; not the `brand=Android` GSI rule (bench is GM AAOS) and not CC. Software role-switch (`vendor.sys.usb.role`→`usb_otg_switch.sh`; the `/dev/cbc-signals`
  write is only a CAN notification, the flip is the `intel_xhci_usb_sw-role-switch/role` node →
  XDCI `OTGD` ACPI OpRegion; `_DSM` `SPPS` software-commands port power `PUPS`/`UXPE` and reads `U2CP`/`U3CP` connect, XDCI `_ADR 0x00150001`, `dsdt_a.dsl:1290-1500`), dabridge dabr_udc.0 / bridgeport 1-6.0→1-6.3, adb props — verified in
  the Y181 vendor init blob (ext4 `/vendor` `init.bxtp_gm.rc`/`init.full_gminfo37_gb.rc`), **deepened
  2026-10-10** [FW/DIS]: kernel 4.19.305 `.rodata` + disassembly (dabridge `.text` runtime code,
  dabridge `id_table` VID `0x2996` PID `0x0100–0x0105`), and GHS `85098662` traced as a *mediated
  PCI passthrough* of the real xHCI `8086:5AA8`/XDCI `8086:5AAA` (`usb_passthru_emul.c` +
  `UsbRdReg/UsbWrReg/UsbPoll/UsbIrq`) supplying the `IGS_DSDT` `OTGD` surface, with no role/gadget/
  dabridge logic in GHS. GHS blob has no compressed/encrypted code (768 B key/signature tail only;
  `GHS_FILE_MAP_85098662.md`). The android ACPIO (`86331630`) is only the `ANDR0001` fstab/vbmeta
  descriptor (no USB config); USB governance is the GHS `IGS_DSDT`. VID `0x2996` = Aptiv (kernel id_table +
  live enumeration agree). Still [UNVERIFIED]: where `sys.usb.controller=dabr_udc.0` / `sys.dabridge.*.portnum`
  are set (system/product EROFS not extracted); in-vehicle Path A descriptor capture; whether the
  `13558185`/MCIP receptacle lacks a `2996:0105` bridge.
- **GMSystemUI §19:** WhiteList static-init class, VisibilityController 8 lists (a–h), list
  members, NAV_SCREEN_FULL/SPManager, Maps-only CardViewControl gate — all confirmed in the
  decompiled GMSystemUI.

## Unverifiable from available sources (not wrong — just not independently evidenced)

EEPROM I²C **0x50** (no raw read — `/dev/i2c-7` is `system:system 0660`, shell can't open);
`libNmeVideoSW.so` name (partition `strings` only).

**~~4-port USB topology / OTG-ID-pin (ALLData schematics)~~ — RESOLVED (Sep 2026)** via the IOK
ALLDATA connector set + GM Body Builder Manual + on-vehicle inspection + PCB photos, all folded
into `hardware/connectors.md`:
- **Topology:** three receptacles — X83B (UBC, floor console, data+ADB), X92IP (UBJ, IP, data),
  X92CD (UBI, charge-only); a *fourth* (X92CF/UBD) exists in the catalog but **not on this VIN**.
  Data is an **IP-first daisy chain** (radio X8 → X92IP → X226 → X83B), each receptacle an active
  hub; power is a parallel feed from fuse F32DR 15A, not the radio.
- **X8 = one USB 2.0 lane** (board silkscreen `USB2.0`, 12-way shell / 6-pin cable, 4 USB
  conductors) — not two lanes/controllers.
- **OTG/ID-pin question corrected:** the radio↔receptacle link carries **no OTG ID pin** (4-wire
  VBUS/D+/D−/GND); Type-C role is CC-based; ADB device-mode is a **SoC software role-switch**
  (`intel_xhci_usb_sw` + `dabridge dabr_udc.0`, reaching the XDCI via the GHS-supplied `OTGD` ACPI OpRegion), not a receptacle ID/CC function — CC is host-side only; the radio cannot sense it. The role is entered by the Developer-Options USB-debugging toggle (VBUS-sense ruled out) and applied via `OTGD`/`SPPS` port-power. Only the physical
  root-port→console-Type-C mapping remains open.

**Resolved by live Jun-2026 ADB capture** (`enumeration/Y181/jun2026/`):
- GPU **"HD 505 / Mesa 21.1.5"** → CONFIRMED via `SurfaceFlinger` GLES dump:
  `Mesa Intel(R) HD Graphics 505 (APL 3), OpenGL ES 3.2 Mesa 21.1.5 (git-4bdd81676b)`.
- Touch controller **I²C 0x4B** → CONFIRMED: `/sys/bus/i2c/devices/7-004b` bound (bus 7 also exposes 0x0c/0x12/0x28).
- Virtualized GHS guest → CONFIRMED: guest block device is `vda` (virtio-blk), no `mmcblk*` (eMMC sits behind the hypervisor).
- Vulkan **"1.0.64"** → CORRECTED to **1.1.0**: the raw value `4198400` (identical in repo dump and live `vkjson`)
  decodes to `0x401000` = `VK_MAKE_VERSION(1,1,0)`. "1.0.64" was a decode slip (1.0.64 would be `4194368`/`0x400040`).
  Source docs updated (`video/README.md`, `video/hardware_rendering.md`, `analysis/platform_faq.md`).

## Recommended but not yet applied (judgment calls / lower priority)

- **Rollback provenance:** the "separate GHS counter in misc" is inference (the *block* is
  field-observed). (The former Y177-permissive/VIP-stub hedge here is resolved — see the two
  byte-verified rows in "Corrected (applied)" above.)
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
