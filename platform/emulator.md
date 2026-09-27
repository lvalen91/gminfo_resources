# Y181 Silverado gminfo37 AAOS in the Android emulator

The real Y181 GM `system`/`product` (Android 12 / SDK 32, `W231E-Y181.3.2`) **boots to a working,
theme-matched Silverado home screen in the x86_64 Android emulator** (goldfish/ranchu), cold-boot
reproducible. Done 2026-09-26 on an Intel Mac Pro (x86_64/HVF).

**The full build tree, scripts, screenshots and blow-by-blow are in the `/Volumes` research tree, not
here** (large binaries): `GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/` — `README.md` (the recipe),
`hy/` (rebuild.sh/boot.sh/mkdisk.py + `sys_add`/`vendor_add` cmds + the HIDL VHAL-proxy + powermode
stand-in), `relay/` (`status.md` BOOT/THEME board, `SUMMARY.md`, screenshots incl. `y181_themed_06.png`
and `reference/gminfo_homescreen.png`), `y181_ref/` (independent Fable static-RE). Vehicle-neutral
method + the CT5-vs-Y181 delta table: `GM_research/aaos/gm_aaos/EMULATOR_PLAYBOOK.md`.

## Method (hybrid)
GM `system`/`product` **as-is** on Google's **android-32** goldfish kernel + vendor + vbmeta +
system_dlkm, packed into an LP `super` (`mkdisk.py`; Y181 is static A/B, no super). GM's real vendor
firmware (Intel/GHS) can't boot on **goldfish/ranchu specifically** — that backend is virtio-mmio and
the wrong machine type (see Kernel characterization + portability below) — so it's a source only here. Blockers solved,
in boot order:
Google `vbmeta_dis`; **swap GM `/system` VINTF manifest for Google's** (GM declared HIDL keymaster@3.0 +
an A/B `IBootControl` goldfish can't serve — the bootloop cause); Google userdebug `init`;
`ro.zygote=zygote64` (GM is 64-bit-only); **powermode** Java HIDL stand-in; swap Google `adbd`+`/adb_keys`
(GM "Secure ADB" refuses all hosts); AVD 2400×960@200; **VHAL = Java HIDL @2.0 `IVehicle` proxy**
(forwards standard props to goldfish, serves GM's vendor set from `GmVendorProps.json` — CarService is a
HIDL @2.0 client, so AIDL donors/JSON-config-add don't apply); run **GM's own `calserviced`** with the
shipped `CalSets.db` (HIDL @1.0, x86_64, no stand-in needed); dummy **`vlan5`@192.168.1.100 / `vlan4`@172.16.4.100**
(Info3.x FSA variant; vt3/4/5 must be absent); vendor SELinux policy stays **32.0**.

## Kernel characterization + portability (2026-09-27)

Extracted and analyzed the real Y181B (gminfo37 CSM) boot image from the firmware update package,
cross-checked byte-identical against the live device's own `.config`. Key facts, refining the "can't
boot on goldfish" framing above:

- **`CONFIG_PARAVIRT` is NOT set.** `CONFIG_HYPERVISOR_GUEST=y` only enables optional detection — no
  `KVM_GUEST`/`XEN`/`HYPERV`/`PVH`/`JAILHOUSE_GUEST`. Core MMU/timekeeping/IRQ/scheduling is bare-metal
  x86_64 despite running as a GHS INTEGRITY guest. GHS coupling is entirely at the DEVICE DRIVER layer:
  `ghs_comms` is a PCI driver binding a GHS-presented virtual PCI function (vendor `0x1B95`, device
  `0xA000`, BAR-mapped rings, MSI-X, host/guest version handshake); `ghs_vmm_bc` handles A/B
  slot/boot-control and delivers guest TSC frequency from the VMM; `gm_ghs_mmc`/`snd_ghs_pcm`/
  `ghs_camera_memory_map` are paravirtual MMC/audio/camera drivers. All are ordinary probe()-based
  PCI/platform drivers that stay unbound (no panic) when their backing GHS device is absent.
- **virtio is present but narrow:** `VIRTIO_PCI=y` (**legacy**, not modern-only), `VIRTIO_BLK`,
  `VIRTIO_CONSOLE` back Trusty TEE only — no `VIRTIO_MMIO`, `VIRTIO_NET`, `VIRTIO_INPUT`,
  `VIRTIO_BALLOON`. Absence of `VIRTIO_MMIO` means this kernel is **incompatible with the
  goldfish/ranchu AVD backend** by construction, independent of GHS. `CONFIG_E1000`/`E1000E=y` and
  `DRM_BOCHS=y` (alongside `DRM_I915=y`) are both compiled in.
- **Verdict — CONFIRMED by real boot (2026-09-27):** GHS is a *service-layer* blocker (specific vendor
  daemons/HALs stay dead without it), not a *boot-layer* one — the real GM Y181B kernel (ACK 4.19.305
  x86_64) was booted on plain `qemu-system-x86_64` (q35, `-accel hvf`, virtio-blk-pci, e1000e, no
  display/nomodeset) on the Mac Pro, isolated from the goldfish AVD (separate process, port 5560 vs
  5558, workdir `~/gm_emu/realk/`). This is a real boot with a captured serial log, not a
  prepared/untested image. **Reached:** kernel boot → first-stage init → `/system`+`/vendor`+`/product`
  mounted from a real virtio-blk GPT disk (static A/B, verity-off) → second-stage init started; stops
  at a `vold-failed` reboot in second stage (SELinux-enforcing blocker, see below) — did not yet reach
  an interactive shell/zygote. All four previously-inferred risk points are now directly confirmed:
  GHS/i915/IPU4 graceful degrade (no panic; `CONFIG_GHS_*` probes fail cleanly, e.g. repeated
  `Unable to open file: /dev/ghs/emmc-health`; `CONFIG_PARAVIRT` confirmed unset at runtime — bare-metal
  VT-x boot), AVB verity-off path works, boot-control (`androidboot.slot_suffix=_a`+`slotselect`)
  resolves partitions correctly with no GHS VMM bootctrl, and TSC/timebase needs no override
  (`tsc: Refined TSC clocksource calibration: 2693.33 MHz` → `Switched to clocksource tsc`). Two
  assumptions from the original plan were proven wrong and corrected: the extracted ACPI SSDT
  (`ssdt_android.aml`) loads into ACPI fine but does **not** work as a DT-fstab source (`fs_mgr`'s
  `ReadFstabFromDt()` fails — its nested node layout doesn't match this platform's flat `_DSD`
  properties); the actual working fix is patching the ramdisk's plain-text first-stage fstab
  (`first_stage_ramdisk/fstab.full_gminfo37_gb`) directly, dropping `logical`/`avb` and pointing each
  entry at the PCI-scoped `/dev/block/pci/pci0000:00/0000:00:1c.0/by-name/<partition>` path with
  `slotselect` — the flat `/dev/block/by-name/...` path is never created by first-stage init on this
  kernel. New hardware-fidelity fact: vendor `file_contexts` labels `ttyS0` as
  `bluetooth_serial_device` and `ttyS1` as `ipc_serial_device` (confirming ttyS1 as the real VIP/libipc
  channel by SELinux label, not just convention) — the console must be on `ttyS2`+ (`serial_device`) or
  SELinux denies the write. **Remaining blocker:** GM's `user` build forces SELinux `enforcing=1`
  regardless of `androidboot.selinux=permissive` on the cmdline (and `selinux=0` outright breaks
  `mount(selinuxfs)`, so it can't be compiled out either) — `vold` gets AVC-denied and killed, causing
  the second-stage reboot loop; a recovery-mode follow-up reached the `console`/`adbd` service
  definitions but both abort/deny (`avc: denied { setcurrent }`) before a shell starts. Next concrete
  step (not yet attempted): use `secilc`/`sepolicy-inject` to make the `adbd`/`su` domains permissive in
  the ramdisk's compiled `/sepolicy`, or relabel the console device node. A full boot to zygote still
  needs a real `data`(f2fs)/`metadata` partition (both zeroed/absent in the test disk) and
  `system_ext_a` (currently missing, non-fatal so far), plus the previously-planned userspace shims
  (software keymaster for FBE) once a shell is reached. **Kernel/vendor-ABI portability is now
  empirically proven, not just theoretical** — the remaining work is pure userspace SELinux/partition
  plumbing, not a kernel or GHS-coupling problem. Artifacts (`run.sh`, `mkstatic.py`, `patch_cpio.py`,
  `ssdt_noavb.aml`/`.dsl`, `fstab.patched`, `serial.log`) preserved to
  `/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_integration/realk/`;
  full working tree (incl. the 6GB `gm.img`, not copied off) remains on the Mac Pro at
  `~/gm_emu/realk/`. Hardware keymaster/attestation/RPMB (Trusty+GHS) and real Harman AVB audio remain
  hard blockers either way, same as today's stubs. See `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`
  Appendix G for the full per-dependency portability table.

## Matching the real Silverado UI (calibration-driven)
Base boot renders the GM **base** look (red accent, no widget, GAS-default tiles). The real Silverado
(blue/gold + analog-clock widget) is reached by editing `CalSets.db`:
- **Theme:** `GMBrand=3` (GM_Brand_Chevrolet) + `GMModel=4` (Silverado) → `CHEVY_THEME` (blue/gold);
  factory `GMBrand=2` (Cadillac) gave the red `GMC_THEME`.
- **Clock/widget panel:** `SCREEN_RESOLUTION=4` (SIZE_2400_BY_960) — GMSystemUI only builds the `CardView`
  clock panel at 2400×960; grid then narrows to 1133 dp.
- **Tiles:** `APPLICATION_HOMESCREEN_{AUDIO,PHONE,CAMERA,CLIMATE,SETTINGS,WIFIHOTSPOT}_ENABLED` + ordering;
  Cameras needs `RVS_PRESENT_STATUS=2`, Wi-Fi Hotspot needs `APPLICATION_HOMESCREEN_ONSTAR_ENABLED=1`; GAS
  tiles are hidden by disabling their launcher components (not calibration-gated).

For the CardView clock panel's gate condition and the separate (code-level, non-calibration)
app-capability/immersive allow-list that governs whether an activity can hide it — including why
native CarPlay can't — see [`gmsystemui_app_capability_gating.md`](gmsystemui_app_capability_gating.md).

## Fidelity — emulator vs the actual radio
Real GM software rendering faithfully on **substituted emulator hardware with no vehicle bus**; a
software/UI/RE emulator, not a functional truck.

| Layer | Real radio | Emulator |
|---|---|---|
| SoC/kernel/vendor | Intel Apollo Lake + GM vendor firmware | Google goldfish android-32 kernel/vendor (real kernel **confirmed booted** on plain qemu-system-x86_64/q35 in a separate isolated process — see Kernel characterization above; stops at second-stage `vold-failed`/SELinux-enforcing, not yet at shell/zygote) |
| Hypervisor/boot | VIP RH850 → CSE → ABL → **GHS INTEGRITY** → guest | none — Android on QEMU |
| VHAL | GM `@2.0-service-gm` on the **live CAN bus** | **GM's real `@2.0-service-gm`** via the libipc shim (540 configs, 486 GM; 141 props shared w/ the real radio) — no live bus behind it; **frame injection into the shim now drives a subset live** (temp/speed/ignition/GPS — see Un-stub roadmap) |
| Powermode/RTC/location | real GM daemons on the VCU | **GM's real `plmanager`/`rtcd`/`gmlocation`** run via libipc shim |
| Calibrations | **per-VIN provisioned** (SDAC/back office) | GM's real `calserviced` + shipped DB, **RPO-matched** to this truck (LTZ trim, Trailering FULL, 360 cams) |
| Network | real Ethernet/CAN + ECUs, telematics/OnStar | dummy `vlan5`/`vlan4`, no peers |
| Display/audio | FALD + touch + cluster/HUD; Bose/AVB | software GPU, one display; goldfish `audio@6.0` (real is `@5.0-harman` on AVB — must stay stubbed) |
| Security | locked, AVB+SELinux **enforcing**, no root | AVB-off, **SELinux ENFORCING** (matches the radio's posture; 0–2 stock-AOSP MLS denials/boot vs 0 on the radio), root adb (deliberate — enables RE) |

**Achieved (2026-09-26, FID-01→16 + RPO-01→03):** GM's real vendor daemons (VHAL/powermode/rtc/location/
calibrations) run in their proper GM SELinux domains with zero daemon denials, under **SELinux enforcing**,
RPO-matched to a 2024 Silverado 2500HD LTZ (Trailering 4th card, LTZ trim). Stable reproducible cold boot
(`hy/fid/verify.sh`); the Java VHAL/powermode stubs are retired. **Still faked/absent** (no vehicle bus):
live vehicle data (doors/HVAC/RVS/VIN theft-lock — no live bus, so VHAL props read unavailable by default;
**frame injection into the libipc shim now drives a measured subset live — see Un-stub roadmap** for outside
temp, vehicle speed, ignition/power mode and GPS_POSITION; gear stays PARK/fallback-only), telematics/OnStar/
cloud/cellular, other ECUs, SecOC; the AVB/GHS/CSE boot-chain trust anchors;
real Bose/AVB audio. Climate/Cameras/Trailering tiles render but don't control/feed anything; AA/CarPlay
need a paired phone; **Carlink** (aftermarket) isn't in the stock image.

## Un-stub roadmap — using GM's real files (verified vs the real-radio ADB dumps)
Cross-checking the emulator's stubs against the running radio's dumps (`enumeration/Y181/raw/*`,
`analysis/adb/Y181/*`) and the GM images. Full reports: `/Volumes/.../2024_Silverado_ICE/emu/y181_ref/unstub/`.

- **VHAL `@2.0-service-gm` → GM's real one now runs [DONE].** `libipc.so` (ipcLib 3.0) is a **Unix-socket
  client of IPCServer** (the UART fanned into per-channel sockets per `/vendor/etc/ipc4.cfg`; ch3=`vehicle_network`),
  **not** a `/dev/ipc` char-dev client. Built `hy/ipc/libipc_shim.c` (socketpair per channel, logs+swallows writes,
  answers the ready handshake + VIP frames). GM's real VHAL registers `IVehicle/default`, 540 configs (486 GM),
  CarService subscribes 166 (141 shared with the real radio's 188). Java proxy retired.
- **Live-bus signal injection (write path) [DONE, partial].** GM's VHAL **rejects HIDL `IVehicle::set()`
  outright** (sensor props `ACCESS_DENIED`; RW props write-through to the swallowed bus) — the only way in is
  **frame injection on `/dev/ipc/ipc3`**: write raw frame bytes to `/data/vendor/ipcshim/ipc3.in` (shim pump
  delivers within ~1s; a `setprop` kick is optional). Wire format decoded from the vhalgm binary:
  `[0xC1][hdr=00][count]` then count×`[fidLo][fidHi][payLen 1..8][payload]`; `frameId=((fidHi&0x0f)<<8)|fidLo`
  (12-bit); payload **big-endian**; the handler validates `payloadSize==cfg[+8]` (else logs `Wrong size for
  frame 0x%X`); a dedup filter drops repeat values (inject fresh ones each time). Discovery oracle:
  `setprop log.tag.GMVHAL VERBOSE` → `Frame Message` / `SignalStore SignalName: <sig> Value: N` /
  `setPropFromVehicle Property: <PROP>`. Full **152-frame bus→VehicleProperty map** at
  `emu/y181_integration/framemap.txt` (reference, not reproduced here). **Landed signals (measured):**
  outside temp (frame `0x4A8`, signal `OATP_OtsAirTmpCrValAuth`, ENV_OUTSIDE_TEMPERATURE read-back 22.0°C;
  HMI status-bar render needs a sustained feed, see caveat below); vehicle speed (frame `0x229`, signal
  `VSADP_VehSpdAvgDrvnAuth`; full inject→VHAL→CarService chain confirmed, `CarDrivingStateService` 0→MOVING);
  ignition/power mode (frame `0x284`, signal `SPMP_SysPwrModeAuth`; IGNITION_STATE=4/RUN); GPS_POSITION (frame
  `0x26A`, signals `GPSC_PPSLat`/`GPSC_PPSLong`, 180/2^30 deg/LSB; Central Park round-tripped through VhalCtl +
  GMVHAL). **PARTIAL:** gear (frame `0x264`, `TEGP_TrnsEstGrAuth`) — GEAR_SELECTION only drives PARK/fallback
  on this build.
- **`vendor.gm.gmlocation@1.0-service` → now runs [DONE]** (real, via libipc shim; live pid confirmed), **and
  navsens HIDL wiring is now PROVEN [PARTIAL — GNSS path done, DR-fusion gate remains]** (2026-09-27): it
  sources position from the Harman **navsens** HAL (`GmLocationService::receiveGNSSLocation`), previously
  unregistered in the emulator (only stock `gnss@2.0-service.ranchu`). Reverse-engineered the exact interface
  gmlocation expects — `vendor.harman.hardware.navsens@1.0::INavsens/default`, `setCallback`=tx1,
  `setHighRateCallback`=tx2, callback `INavsensCallback::gnssLocationCB(GNSSLocation, GNSSUTCTime)`=tx1 —
  and the `GNSSLocation` struct layout (`mLatitude` @0x00, `mLongitude` @0x08, both double, struct size
  0x78/120 bytes; an initial reversed-offset guess corrupted latitude and was corrected). Implemented a Java
  `app_process` HIDL service (`Navsens.java`, mirroring the CT5 emulator's `LocD.java`) — no native
  C++ HIDL build tree available on this Mac, so this is a practical Java substitute — streaming
  `gnssLocationCB` at 1Hz. **Measured (live device):** `lshal` shows `INavsens/default` registered;
  gmlocation logs `connectNavsens` → `Connection to navsens HAL succeeded`; the injected fix (Central
  Park) is received and cached by gmlocation's own `NavsensCallback::gnssLocationCB` handler. Cold-boot
  durable via `scenario.sh` auto-relaunch/auto-reconnect. **Remaining gate (why PARTIAL not PASS):**
  `gnssLocationCB` only caches the fix — gmlocation's internal publish/fusion loop separately needs
  DR-calibration state (`DRCoefficient`/`CarWheelPulseResolution` currently invalid/defaulted) and three
  more navsens sub-interfaces the stub doesn't implement yet (`getSensorAccelerometerInterface`,
  `getSensorGyroscopeInterface`, `getSensorWheelInterface` — all currently HIDL-failure from the stub).
  `IGmLocation::start()` returns OK but produces no fused output yet, confirming the gate is the missing
  sensor sub-interfaces/DR state, not the GNSS path (which is proven working). Two caveats: Java-server
  two-way callback ACKs fail (`setCallback HIDL failure`, `lshal getDebugInfo` PID N/A) even though the
  data callback itself succeeds — a native C++ HIDL service would likely fix this and may also unblock
  DR fusion; and all measurements are under `SEL=permissive` — enforcing needs the stub in a real service
  domain (init `.rc` + sepolicy), not adb's `su` domain. Artifacts preserved to
  `/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_integration/navsens/`;
  live on the Mac Pro at `~/gm_emu/hy/navsens/`, wired into `~/gm_emu/hy/emu_integration/scenario.sh`.
  **`vehicleaudiocontrol`
  → still absent, next cheap net-new add.** Both are calserviced-HIDL clients with no `/dev/ipc` dep (verify vehicleaudiocontrol's
  import table before adding).
- **`calserviced` → already GM-real** (libipc only for the override path).
- **Audio HAL → stays stubbed permanently.** Real = `vendor.hardware.audio@5.0-harman-custom-service` on a real
  **AVB (802.1BA)** network (`daemon_cl`/`avb_streamhandler`/`eavbmgr`); a physical-network dep, no libipc fix.
  Emu substitutes stock Google `audio@6.0`. **Update (2026-09-26):** `-no-audio` removed from `boot.sh` — live
  PRIMARY mixer output now reaches host CoreAudio (confirmed via `dumpsys media.audio_flinger` `AudioOut_D`).
  Guest **mic** pipeline PASSES (`AudioRecord` captures at correct real-time pacing, not muted; consumers
  include `carassistant`, `com.gm.car.input`, `gmaudio.tuner`, BT-HFP). Host delivery is still **blocked** over
  headless SSH: the Mac Pro has no hardware audio input (a BlackHole 2ch virtual loopback was installed to give
  it one), and macOS mic-privacy (TCC) denies mic to SSH-launched processes and can't be granted over SSH.
  Closing it needs a GUI/Screen-Sharing console session on the Mac Pro to grant the emulator mic permission
  (same as how CT5's mic was closed) — not an emulator defect.
- **Memory/touch parity [DONE].** RAM now mirrors the radio: 6144M (guest `MemTotal` ~5.8GB vs radio 5.66GB),
  zram swap disabled (radio `SwapTotal=0`). Touch stays 2400×960@200 (already correct).
- **Durability.** `boot.sh` runs `emu_integration/scenario.sh` ~20s after `boot_completed`: re-pushes VhalCtl,
  injects temp/speed/ignition/GPS frames, deploys+bind-mounts the `libpal_tod` stub, restarts rtcd, re-asserts
  IGNITION=RUN, and runs `emu geo fix -73.9654 40.7829`. Survives `-wipe-data` cold boots. Artifacts under
  `emu/hy/emu_integration/` (`scenario.sh`, `inject.py`, `framemap.txt`/`.py`, `libpal_tod.so`, sweep tools) +
  `emu/hy/vhal` (VhalCtl harness).
- **Caveat — HMI rendering needs a sustained feed.** GM's VHAL gates status=AVAILABLE, HMI-widget rendering,
  MOVING, and vendor-mirror props behind a broad `_Auth`/validity + power-context signal set. One-shot
  injection sets raw property values deterministically (verifiable via VhalCtl) but persistent HMI rendering
  needs a periodic broad valid-signal feed replaying the companion `_Auth` bits.
- **powermode/`IPowerModing` → GM's real `plmanager` now runs [DONE]** (via the libipc shim; `IPowerModing`
  registered, "Power Moding service is ready"). Correction to the earlier note: `plmanager` **is** the real
  server (a libipc client), and it replaced the Java stand-in. `rtcd` (`IRemoteRtcService`) and `gmlocation`
  (`IGmLocation`) likewise run real via libipc.
- **RUN power state blocked by an RTC dependency — fixed.** `PowerPropertyManager` requires
  `IRemoteRtcService.getStatus()==1`, which only flips when `libpal_tod.so` sees a "remote ready" channel state
  from the VIP over IPC — swallowed by the shim, so it looped `Remote Alarm service is not ready` /
  `netlink_send_request error:-1` forever and blocked RUN. Fix: a drop-in stub **`libpal_tod.so`** (7
  `tod_pal_*` symbols; source `hy/ipc/src/libpal_tod_shim.c`) that fires rtcd's ready callback with 1;
  bind-mounted over `/vendor/lib64/libpal_tod.so`, rtcd restarted. Result: `onVehiclePowerMode: Off(0)→Run(2)`,
  RTC errors zero. Durable via `scenario.sh` (see Durability below).
- **SELinux enforcing → ACHIEVED [DONE].** Real GM domains `gm_vehicle_hal`/`plmanager`/`rtcd`/`gmlocation`/
  `calserviced` derived from `vendor_sepolicy.cil` (v**32.0**; `file_contexts` from `emu/hy/sepol/gm_vend/`), glue
  domains for the shim; init recompiles CIL each boot. **6 consecutive `-wipe-data` cold boots all `Enforcing`,
  boot_completed, 0 GM-daemon denials**; the only enforced denials are 0–2/boot of the same **stock-AOSP MLS
  cross-user-search** that AOSP denies by design (real radio: Enforcing, 0 avc). `hy/fid/verify.sh` is the harness.
  System/product enforcing ≈ the real posture; vendor-domain is emulator glue (no real GHS-IPC peer).
- **Identity props (reconciled) —** the real radio publishes **`persist.sys.cal.brand=GM_Brand_Chevrolet` +
  `persist.sys.cal.model=Silverado`** (from calserviced), and separately the Chevrolet/SystemUI **RROs gate on
  `requiredSystemPropertyName=persist.vendor.gm.brand`** — so both namespaces are legitimate (not an either/or).
  The emu sets both.
- **RPO-matched calibrations [DONE] —** grounded in the bench truck's RPO codes ([`vehicle_config.md`](vehicle_config.md)):
  `GMTrim=16` (LTZ; DB held 0=None), `TraileringAppType=2` (FULL — required for the SystemUI trailer card; Z82/UET/JL1),
  `APPLICATION_HOMESCREEN_TRAILERING_ENABLED=1` → the 4th home card; `RVS_PRESENT_STATUS=2` (UV2 360). Open: propulsion
  type has no `CalSets.db` row (vendor-only prop); the `FJW`/E15 fuel-blend cal stays factory 0.
- **Network/FSA (real service mesh) —** `:49156` `diagnosticsd` (**custom 8-byte GM header, NOT DoIP**; bridges
  `172.16.4.100 ↔ 172.16.4.107` on **vlan4**). FSA `9002`/`9010` LISTEN on vlan5, client dials `9016`/`.112:9018`.
  Un-stub via synthetic peers: **vlan5** `.106` Visteon IPC dialing the CSM's `9002`, `.102` telematics, `.112`
  CGM_OTA; **vlan4** `.107` RTOS diag bridge. **FSA protocol solved + proven unauthenticated live** (GET/SUBSCRIBE
  round-trips on `9002` from an anonymous peer; full spec in [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md)).
  AE avenues: cluster-injection via REQUEST/REQUESTRESPONSE opType 641/674 fktId ≥700 (**corrected
  2026-09, was misattributed to EVENT 1032** — see `fsa_protocol.md`); the two FSA parser bugs (int32 `payloadLength` RAM-DoS,
  reject-path framing desync); `:49156` UDS-bridge DoS/fuzz; NAM EAP-AKA; SOME/IP-SD fuzz; `IDiagnosticsInternalService`
  vndbinder-bypass. Tools: `~/gm_emu/ae/{fsaprobe,fsalisten4}` (raw-syscall connect/accept4 to bypass the netd fwmark handshake).
  **FSA int32-`payloadLength` RAM-DoS live-proven (2026-09):** one 20-byte header declaring
  `payloadLength=0x40000000` forced the real `com.gm.cluster` process into a 1,073,741,856-byte allocation
  attempt (`OutOfMemoryError` caught, process survives) — repeatable, one packet per shot. Full spec:
  [`fsa_protocol.md`](fsa_protocol.md#f-bugs-two-fsa-parser-bugs-shared-code-both-9002-and-9016).
- **`diagnosticsd` + the diagnostics HAL chain are ABSENT from the hybrid emulator.** No
  `/vendor/bin/diagnosticsd`, no `vendor.gm.diagnostics.obd@1.0::IDiagnosticsObd` registered, and GM
  Secure-ADB is replaced by Google's stock `adbd`. This is why the SBI/`$27` fail-open
  ([`security.md`](security.md#ethernet-uds-27-securityaccess--vip-side-forwarding-off-soc-2026-09)) cannot
  be exercised here — the compare lives off-SoC on the VIP MCU, which this emulator has no stand-in for; it
  would need a substantial synthetic external-component/VIP endpoint, not a quick stub.

See also: [`security.md`](security.md) (SELinux enforcing on all builds), [`vehicle_network.md`](vehicle_network.md)
(Info3.x/vlan5 addresses used for the FSA shim), [`hardware.md`](hardware.md) (the real 2400×960 panel).
