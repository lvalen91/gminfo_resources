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
| VHAL | GM `@2.0-service-gm` on the **live CAN bus** | Java HIDL **proxy** + static props |
| Calibrations | **per-VIN provisioned** (SDAC/back office) | shipped DB, factory "GREEN" + Silverado/theme overrides |
| Network | real Ethernet/CAN + ECUs, telematics/OnStar | dummy `vlan5`/`vlan4`, no peers |
| Display/audio | FALD + touch + cluster/HUD; Bose/AVB | software GPU, one display; goldfish audio |
| Security | locked, AVB+SELinux **enforcing**, no root | **unlocked, permissive, root adb** (deliberate — enables RE) |

**Faked/absent:** live vehicle data (speed/gear/doors/HVAC/RVS/VIN theft-lock), telematics/OnStar/cloud/
cellular, other ECUs, SecOC, ProtoKey/powermode (stubbed). Climate/Cameras tiles render but don't
control/feed anything; AA/CarPlay need a paired phone; **Carlink** (aftermarket) isn't in the stock image.

## Un-stub roadmap — using GM's real files (verified vs the real-radio ADB dumps)
Cross-checking the emulator's stubs against the running radio's dumps (`enumeration/Y181/raw/*`,
`analysis/adb/Y181/*`) and the GM images. Full reports: `/Volumes/.../2024_Silverado_ICE/emu/y181_ref/unstub/`.

- **VHAL `@2.0-service-gm` → run GM's real one** (in progress). Links `libipc.so`, opens `/dev/ipc/ipc3`,
  rc gates on `vendor.modules.ipcserver.ready=true`. `/vendor/etc/ipc4.cfg`: IPCServer transport is a plain
  **UART `/dev/ttyS1` @1 Mbaud** fanned into per-channel Unix sockets; **channel 3 = `vehicle_network`** (the
  VHAL's user). Goldfish exposes virtual `ttyS*`, so a `libipc` shim is tractable → replaces the Java proxy.
- **`vendor.gm.gmlocation@1.0-service` + `vehicleaudiocontrol` → cheap net-new adds.** Pure calserviced-HIDL
  clients, **no `/dev/ipc` dep**; currently absent from the emu — add without a shim.
- **`calserviced` → already GM-real** (libipc only for the override path).
- **Audio HAL → stays stubbed permanently.** Real = `vendor.hardware.audio@5.0-harman-custom-service` on a real
  **AVB (802.1BA)** network (`daemon_cl`/`avb_streamhandler`/`eavbmgr`); a physical-network dep, no libipc fix.
  Emu substitutes stock Google `audio@6.0`.
- **powermode/`IPowerModing` → the current system-side Java stand-in is architecturally correct**, not a
  shortcut: no `/vendor/bin` IPowerModing daemon exists; the real server is the `plmanager` domain.
- **SELinux enforcing → feasible.** Real domains: `gm_vehicle_hal`, `plmanager`, `calserviced`/`GHSCalibrations`,
  stock `adbd`; policy **v32.0**. `file_contexts` source is in `emu/hy/sepol/gm_vend/`; init already **recompiles
  CIL every boot** (no delete-precompiled step); the 5 stand-ins at `u:r:su:s0` need real domains; `cildiff.py`
  reports only 12 inert Apollo-Lake genfscon symbols. **System/product enforcing ≈ the real posture; vendor-domain
  enforcing is a plausibility check only** (goldfish + proxies vs Apollo Lake + GHS; the real GHS-IPC rules
  `gm_vnd_IPCServer`/`ipc_device` have no emulator peer).
- **Identity props (fidelity fix) —** real radio uses **`persist.sys.cal.brand=GM_Brand_Chevrolet` +
  `persist.sys.cal.model=Silverado`**; **`persist.vendor.gm.*` does NOT exist on the real radio** (the emu's is
  guesswork that happens to render via the CalSets `GMBrand=3` + force-enabled RROs). Set the `persist.sys.cal.*`
  pair and re-verify RRO/theme gating.
- **Network/FSA (real service mesh) —** `:49156` diagnosticsd (UDS-over-TCP → RTOS `172.16.4.107`), FSA
  `9002`/`9010`/`9016` LISTEN + sessions to `9005`/`9016`/`9018`. Un-stub via **synthetic `vlan5` peers** (`.106`
  Visteon IPC dialing the CSM's `9002`; `.107` RTOS diag bridge; `.102` telematics; `.112` CGM_OTA). AE research
  avenues: FSA wire-format fuzz (no auth), the `:49156` UDS-bridge DoS/fuzz, RemoteModuleHMI cluster-injection,
  NAM EAP-AKA, SOME/IP-SD discovery fuzz, `IDiagnosticsInternalService` vndbinder-bypass.

See also: [`security.md`](security.md) (SELinux enforcing on all builds), [`vehicle_network.md`](vehicle_network.md)
(Info3.x/vlan5 addresses used for the FSA shim), [`hardware.md`](hardware.md) (the real 2400×960 panel).
