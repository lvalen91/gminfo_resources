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
firmware (Intel/GHS) can't boot on goldfish, so it's a source only. Blockers solved, in boot order:
Google `vbmeta_dis`; **swap GM `/system` VINTF manifest for Google's** (GM declared HIDL keymaster@3.0 +
an A/B `IBootControl` goldfish can't serve — the bootloop cause); Google userdebug `init`;
`ro.zygote=zygote64` (GM is 64-bit-only); **powermode** Java HIDL stand-in; swap Google `adbd`+`/adb_keys`
(GM "Secure ADB" refuses all hosts); AVD 2400×960@200; **VHAL = Java HIDL @2.0 `IVehicle` proxy**
(forwards standard props to goldfish, serves GM's vendor set from `GmVendorProps.json` — CarService is a
HIDL @2.0 client, so AIDL donors/JSON-config-add don't apply); run **GM's own `calserviced`** with the
shipped `CalSets.db` (HIDL @1.0, x86_64, no stand-in needed); dummy **`vlan5`@192.168.1.100 / `vlan4`@172.16.4.100**
(Info3.x FSA variant; vt3/4/5 must be absent); vendor SELinux policy stays **32.0**.

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

## Fidelity — emulator vs the actual radio
Real GM software rendering faithfully on **substituted emulator hardware with no vehicle bus**; a
software/UI/RE emulator, not a functional truck.

| Layer | Real radio | Emulator |
|---|---|---|
| SoC/kernel/vendor | Intel Apollo Lake + GM vendor firmware | Google goldfish android-32 kernel/vendor |
| Hypervisor/boot | VIP RH850 → CSE → ABL → **GHS INTEGRITY** → guest | none — Android on QEMU |
| VHAL | GM `@2.0-service-gm` on the **live CAN bus** | **GM's real `@2.0-service-gm`** via the libipc shim (540 configs, 486 GM; 141 props shared w/ the real radio) — no live bus behind it |
| Powermode/RTC/location | real GM daemons on the VCU | **GM's real `plmanager`/`rtcd`/`gmlocation`** run via libipc shim |
| Calibrations | **per-VIN provisioned** (SDAC/back office) | GM's real `calserviced` + shipped DB, **RPO-matched** to this truck (LTZ trim, Trailering FULL, 360 cams) |
| Network | real Ethernet/CAN + ECUs, telematics/OnStar | dummy `vlan5`/`vlan4`, no peers |
| Display/audio | FALD + touch + cluster/HUD; Bose/AVB | software GPU, one display; goldfish `audio@6.0` (real is `@5.0-harman` on AVB — must stay stubbed) |
| Security | locked, AVB+SELinux **enforcing**, no root | AVB-off, **SELinux ENFORCING** (matches the radio's posture; 0–2 stock-AOSP MLS denials/boot vs 0 on the radio), root adb (deliberate — enables RE) |

**Achieved (2026-09-26, FID-01→16 + RPO-01→03):** GM's real vendor daemons (VHAL/powermode/rtc/location/
calibrations) run in their proper GM SELinux domains with zero daemon denials, under **SELinux enforcing**,
RPO-matched to a 2024 Silverado 2500HD LTZ (Trailering 4th card, LTZ trim). Stable reproducible cold boot
(`hy/fid/verify.sh`); the Java VHAL/powermode stubs are retired. **Still faked/absent** (no vehicle bus):
live vehicle data (speed/gear/doors/HVAC/RVS/VIN theft-lock — VHAL props read unavailable, e.g. outside
temp `--`), telematics/OnStar/cloud/cellular, other ECUs, SecOC; the AVB/GHS/CSE boot-chain trust anchors;
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
- **`vendor.gm.gmlocation@1.0-service` + `vehicleaudiocontrol` → cheap net-new adds.** Pure calserviced-HIDL
  clients, **no `/dev/ipc` dep**; currently absent from the emu — add without a shim.
- **`calserviced` → already GM-real** (libipc only for the override path).
- **Audio HAL → stays stubbed permanently.** Real = `vendor.hardware.audio@5.0-harman-custom-service` on a real
  **AVB (802.1BA)** network (`daemon_cl`/`avb_streamhandler`/`eavbmgr`); a physical-network dep, no libipc fix.
  Emu substitutes stock Google `audio@6.0`.
- **powermode/`IPowerModing` → GM's real `plmanager` now runs [DONE]** (via the libipc shim; `IPowerModing`
  registered, "Power Moding service is ready"). Correction to the earlier note: `plmanager` **is** the real
  server (a libipc client), and it replaced the Java stand-in. `rtcd` (`IRemoteRtcService`) and `gmlocation`
  (`IGmLocation`) likewise run real via libipc.
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
- **Network/FSA (real service mesh) —** `:49156` diagnosticsd (UDS-over-TCP → RTOS `172.16.4.107`), FSA
  `9002`/`9010`/`9016` LISTEN + sessions to `9005`/`9016`/`9018`. Un-stub via **synthetic `vlan5` peers** (`.106`
  Visteon IPC dialing the CSM's `9002`; `.107` RTOS diag bridge; `.102` telematics; `.112` CGM_OTA). AE research
  avenues: FSA wire-format fuzz (no auth), the `:49156` UDS-bridge DoS/fuzz, RemoteModuleHMI cluster-injection,
  NAM EAP-AKA, SOME/IP-SD discovery fuzz, `IDiagnosticsInternalService` vndbinder-bypass.

See also: [`security.md`](security.md) (SELinux enforcing on all builds), [`vehicle_network.md`](vehicle_network.md)
(Info3.x/vlan5 addresses used for the FSA shim), [`hardware.md`](hardware.md) (the real 2400×960 panel).
