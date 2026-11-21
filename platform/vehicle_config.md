# Vehicle Configuration

Scope: identity and option set of the truck the bench IOK radio came from; the RPO -> calibration/prop mapping; CalSets.db facts; system properties, `hw.conf`, vehicle ID; Android services/VHAL list; behaviour when the radio is removed; CalDef/VIP-calibration and UDS tables.
Used to set emulator calibrations to this truck's real feature set (see [`emulator.md`](emulator.md)).

Evidence tags used: [V] verified on live radio/export, [read] read from a dump or live shell, [inferred], [VEH] measured on the vehicle, [FW] firmware-corroborated, [INF]/[GM] expected/not observed, [X] unknown/unverifiable.

Related: [`emulator.md`](emulator.md), [`gmsystemui_app_gating.md`](gmsystemui_app_gating.md), [`firmware_versions.md`](firmware_versions.md), [`ota_programming_roles.md`](ota_programming_roles.md), [`vehicle_network.md`](vehicle_network.md), [`fsa_protocol.md`](fsa_protocol.md), [`hardware_specs.md`](hardware_specs.md), [`vip_ipc_ghs.md`](vip_ipc_ghs.md).

## 1. Donor vehicle identity

**VIN is owner-held and deliberately NOT recorded here** (repo no-credentials/PII rule); the emulator uses a GM-format **placeholder** VIN for `INFO_VIN`. Derived from VIN/RPOs:
**2024 Chevrolet Silverado 2500HD LTZ**, ICE **6.6L gas V8 (L8T)**, 4WD (F48), Fleetside (E63), GVWR 10,850 lb (JGH), Flint MI plant (CMD). Test vehicle RPO **IOK**; the matching service manual is the 2024 Silverado 2500/3500HD Electrical Body Builder Manual (`24_Silverado_2500-3500HD_Body_Builder_Manual_2023May11.pdf`).

Per the VIN's factory RPO Code List this truck has **no Head-Up Display** (no UV6/HUD code) and **no rear-seat video**, so radio Ethernet buses **5** (P22F rear-seat video) and **14** (P29 HUD) are not equipped; only buses **2 / 4 / 6** are wired on X11. Present and relevant options: **IOK** radio, **UQA** Bose amp (Bus 6 / T3), **UE1** OnStar (K73 comm path), **UDV** full cluster (P16), **IVN** (cockpit uses radio family). Bus/circuit numbering is shared across the T1XX line, so a 1500 uses the same bus map; no 1500-only deviation is known. (Source: networking L897-904.)

### Vehicle identification (live radio)

| Field | Value |
|-------|-------|
| Vehicle | 2024 Chevrolet Silverado (ICE) |
| GMModel | 4 |
| GMBrand | 3 (Chevrolet) |
| GMTrim | 16 |
| Build | W231E-Y181.3.2-SIHM22B-499.3 |
| Hardware SKU | gv221 |
| Build Fingerprint | gm/full_gminfo37_gb/gminfo37:12/W231E-Y181.3.2-SIHM22B-499.3/231:user/release-keys |

History: GMTrim LTZ was originally an emulator placeholder 15 and the DB held 0=None; set to 16 on 2026-11-12 (emulator.md "RPO-matched calibrations [DONE]").

## 2. RPO -> feature -> GM calibration / prop

Radio/UI-relevant options (full RPO list retained by owner). Exact enum numbers for GMTrim/TraileringAppType/propulsion should be read from `CalSets.db` (`AllCalSets`) or GMHomeScreen before applying.

| RPO | Meaning | Emulator calibration / prop it grounds |
|---|---|---|
| X88 | Market brand Chevrolet | `GMBrand=3` (GM_Brand_Chevrolet); `persist.sys.cal.brand=GM_Brand_Chevrolet` - **confirmed** |
| GF9 | Trim package **LTZ** | `GMTrim` = LTZ enum (16, applied); `persist.sys.cal.model=Silverado` |
| AXK / E63 | Truck / Fleetside pickup box | vehicle-type cal (truck) |
| IOK | Radio 3.X Mid/High HMI (gminfo37) | the radio itself |
| URD | Display 13.4", **2400x960**, TFT | `SCREEN_RESOLUTION=4` (SIZE_2400_BY_960), density 200 - **confirmed** |
| UV2 / (rear cams) | 360 View HD, mono digital | `RVS_PRESENT_STATUS=2`; `APPLICATION_HOMESCREEN_CAMERA_ENABLED` - **confirmed present** |
| **Z82 / UET / JL1 / CTT / PZ8 / TRG / UKV** | Trailer provisions, smart-trailer integration, integrated trailer brake, hitch view/guidelines, trailer views | **Trailering equipped** -> `APPLICATION_HOMESCREEN_TRAILERING_ENABLED=1` + `TraileringAppType` (=2 FULL) -> the **4th home card** (resolved the emu's 3-vs-4 card gap) |
| FJW / L8T | Gasoline E15 / 6.6L gas V8 | propulsion type = **ICE gas** (not EV): `KeOCD_int_VEHICLE_PROPULSION_TYPE` = gas; no `CalSets.db` row (vendor-only prop); `FJW`/E15 fuel-blend cal stays factory 0 |
| UE1 / VV4 | OnStar / mobile-internet connectivity | `APPLICATION_HOMESCREEN_ONSTAR_ENABLED` (Wi-Fi Hotspot gate) - **confirmed present** |
| PPW | Wireless phone projection | AA/CarPlay tiles legitimate (need a paired phone to activate) |
| UQA | Premium audio, branded amplifier (Bose) | audio config; branded-amp path |
| U2K | S-band digital audio | **SiriusXM** present (ties to the Y181 -> Y181B SXM firmware delta) |
| K4C / KA1 / KA6 / KQV / KI3 | Wireless charger; heated front/rear + vented seats; heated wheel | Climate/seat feature cals |
| KSG / UHY / UFL / UEU / UFG / UKJ / UD5 | Adaptive cruise w/ stop-go, low-speed AEB, lane-departure, FCA, rear cross-traffic, ped detection, front+rear park assist | ADAS safety-indicator cals |
| UDV | Enhanced full multicolor cluster | IVN=NONE (cluster driven by radio family) - cluster HMI over FSA |

Applied to the emulator (2026-11-12; status owned by `emulator.md`): trailering enabled, GMTrim=16, propulsion=gas (no EV props), identity props set, camera/OnStar/Wi-Fi-Hotspot enables confirmed by UV2 / UE1 / VV4 (not guesses). These converted roughly half of the previously "not-dump-provable" `CalSets.db` overrides into config-confirmed values for this truck.

### Identity props: two namespaces
The real radio publishes `persist.sys.cal.brand=GM_Brand_Chevrolet` + `persist.sys.cal.model=Silverado` (from calserviced); separately the Chevrolet/SystemUI RROs gate on `requiredSystemPropertyName=persist.vendor.gm.brand`. Both namespaces are legitimate (not either/or); the emulator sets both. `persist.vendor.gm.brand/.model` are **absent on the real radio**. Emulator-side handling of the two namespaces: [emulator.md Un-stub roadmap](emulator.md#un-stub-roadmap--using-gms-real-files-verified-vs-the-real-radio-adb-dumps) (emulator.md is still an unconsolidated original).

## 3. CalSets.db

### Y181B exported baseline (2026-11-12)
The [recovery export](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12) contains `update_cache/bootup_log/vendor/CalSets.db`: **2574** `AllCalSets` rows, 982 with nonzero `OverRiden`. This describes the retained exported database, not a query of the running calibration HAL. The second ZIP has a byte-identical database.

**Verified 2026-11-12 (`sqlite3` on the exported file):**
- 2574 rows / 982 nonzero `OverRiden` re-counted exactly; `PRAGMA user_version` = **70008**.
- Tables: `AllCalSets`, `SubSets`, `EnumSets`, `ModuleData`. Every `ModuleData` row carries `PartNumber_D` = 70008 (the same number is the DB/cal-set revision), with per-module `applied_overrides/<part>.<DLS>.<n>.cmod` paths.
- VIP/`ghs.log`: `Calibrations: Info: Current CalTable Version: 3.5` and `Saved CalTable Version: 3.5` (equal, no pending migration).
- Live props `persist.sys.cal.brand=GM_Brand_Chevrolet`, `persist.sys.cal.model=Silverado` read via `adb shell getprop`.
- `OverRiden` is a numeric field, not interpreted as a Boolean or a human-edit count.

**Owner-supplied update-cache archive checked 2026-11-14:** in-memory `CalSets.db` query again 2574 rows / 982 nonzero `OverRiden`, user version 70008. Every nonzero `OverRiden` value matches a `ModuleData.ModID` in this snapshot. `ModuleData` records 14 applied `.cmod` paths; the ZIP contains none of those `.cmod` files and no calibration-directory subtree. Records can include production configuration packages, so the archive is not a complete backup from which to reverse a calibration-override erase. Its DB member's archive timestamp is in 2010 and does not establish the current radio state.

Baseline values (Y181B vehicle-specific, for emulator comparison):

| CalName | CalValue | OverRiden |
|---|---:|---:|
| `SCREEN_RESOLUTION` | **4 (`SIZE_2400_BY_960`)** | 8 |
| `GMBrand` | **3** | 4 |
| `GMModel` | **4** | 4 |
| `APPLICATION_HOMESCREEN_APPLECARPLAY_ENABLED` | 1 | 5 |
| `Apple_CarPlay_enableWireless` | 1 | 5 |
| `Enable_Application_Apple_Carplay` | 1 | 0 |
| `GIS864_USBProgrammingEnabled` | 1 | 0 |

Earlier 2573-row vendor/default databases and `SCREEN_RESOLUTION=2` snapshots remain historical sources, not the current exported radio baseline. A calibration enable does not prove feature operation or acceptance of a custom signed calibration package. The homescreen-removal experiment changes per-user package availability independently of these calibration values.

### Calibration-driven UI (emulator view)
Base boot renders the GM **base** look (red accent, no widget, GAS-default tiles). The real Silverado look (blue/gold + analog-clock widget) comes from `CalSets.db`:
- **Theme:** `GMBrand=3` + `GMModel=4` -> `CHEVY_THEME` (blue/gold); factory `GMBrand=2` (Cadillac) gave the red `GMC_THEME`.
- **Clock/widget panel:** `SCREEN_RESOLUTION=4` (SIZE_2400_BY_960). GMSystemUI builds CardView when its calibration reader returns 4, independently of actual VM display dimensions. The reader defaults to 3, so a 2400x960 VM can lack the panel when the effective calibration is missing/different; the recorded grid narrows to 1133dp. **Correction 2026-11-17:** on the physical radio, changing the global calibration 4->2 caused tearing; restoring stock 4 fixed it. A panel-only inverse should be tested at the SystemUI creation/visibility gate in the VM, not assumed safe through global display calibration.
- **Tiles:** `APPLICATION_HOMESCREEN_{AUDIO,PHONE,CAMERA,CLIMATE,SETTINGS,WIFIHOTSPOT}_ENABLED` + ordering; Cameras needs `RVS_PRESENT_STATUS=2`, Wi-Fi Hotspot needs `APPLICATION_HOMESCREEN_ONSTAR_ENABLED=1`; GAS tiles are hidden by disabling their launcher components (not calibration-gated).

CardView gate condition and the code-level app-capability/immersive allow-list: [`gmsystemui_app_gating.md`](gmsystemui_app_gating.md).

## 4. CalSets clear & recovery (2026-11-14)

Single narrative. Diagnostics may own the detailed record (see ledger); links give the evidence.

1. **Live-state limit.** UID-2000 USB ADB on the running Y175 radio returned `Permission denied` for metadata checks of `/mnt/vendor/calibration/overrides`, `/update_cache/calibrations`, `/update_cache/bootup_log/vendor/CalSets.db`. The exported Y181B row count therefore does not establish the running Y175 override count, loaded module state, or absence of overrides. No override was erased by those checks. Erase/reset paths: [routine inventory](../diagnostics/diagnosticsd_protocol.md#java-handler-inventory-verified-against-the-live-apk-2026-11-14).
2. **Read-only identity comparison.** Diagnostic DID F182 returned records for all 14 ModuleData IDs in the archive. Thirteen part-number/DLS pairs matched the recorded override identities; module 11 differed. The native F182 handler queries identities from GMCalibrationManager. This corroborates selected module metadata on the running radio, while the live database contents, loaded-row ownership and override package files remained unread, so the archive cannot be assumed to reproduce every current module. This comparison preceded the later explicit clear (step 3). [Details](../diagnostics/diagnosticsd_dids_and_dtc.md#read-only-calibration-identity-comparison-with-the-supplied-archive).
3. **Explicit clear.** T1 `31 01 02 49` returned `71 01 02 49`; the daemon logged ALL OVERRIDES CLEARED. All 14 F182 module identities (tags 02-0F) changed to part number 70008 / DLS 00; F182 record count stayed 28; MEC stayed FF/255; Android did not reboot. The 982 archived nonzero rows are historical export evidence, not a post-clear count; no live post-clear SQLite count was obtainable. [Completed clear](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).
4. **Post-clear failure.** A persistent J5 indicator was created. The owner's power-cycle entered RH850 `NoCalibration (0xe)` after a startup fault timeout and showed bad/incomplete calibration on the display. T1 still returned MEC FF and all 14 base identities; USB ADB did not reappear. The base-only state is insufficient for normal startup.
5. **Direct-T1 restoration attempt.** All 14 stock LTZ containers matched the pinned successful-transfer hashes. Level-01 access succeeded, but `10 02` returned `7F 10 22` and the first stock RequestDownload returned `7F 34 7F`. No calibration bytes transferred; MEC remained FF. [Attempt and access checks](../diagnostics/diagnosticsd_routines_and_recovery.md#direct-t1-stock-ltz-restoration-attempt-and-shell-checks-2026-11-14).
6. **MDI2 recovery completed.** The same A11 was restored with the pinned stock LTZ package using the main MDI2 client. Recovery accepted only the exact 14-slot base 70008/00 profile through a one-time in-memory classifier and restored the erased VIN from the owner's supplied value before programming. All slots 02-0F and VIN matched post-reset readback; F0F1/F0F2 were `0000`. Later UART boots reported calibration state `2` and reached HMI ready / Accessory; the owner confirmed normal display and radio operation. This supersedes the unresolved state in step 4. It does not establish the old archive's suitability or a post-recovery SQLite row count; ADB and final MEC were not rechecked at that recovery checkpoint. **Follow-up, 2026-11-15:** USB ADB and T1 ADB on radio TCP 9040 were subsequently operational; the final MEC value remains unverified. [Completed recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).

## 5. System properties, hw.conf, vehicle ID

| Property | Value |
|----------|-------|
| persist.sys.cal.brand | GM_Brand_Chevrolet |
| persist.sys.cal.model | Silverado |
| ro.product.name / ro.boot.hardware | full_gminfo37_gb |
| ro.boot.bootloader | 2344 |
| ro.soc.model | A3960 |
| ro.boot.product.hardware.sku | gv221 |
| persist.sys.wifi.only2g | 1 |
| config.disable_cameraservice | 1 |
| ro.radio.noril | true |

**Verified live 2026-11-12 (Y181 `W231E-Y181.3.2-SIHM22B-499.3`, `adb shell getprop`):** all rows above [read]; `ro.boot.product.hardware.sku=gv221`. The `androidboot.product.hardware.sku` spelling returns empty (only the `ro.boot.` form is populated). `persist.vendor.gm.brand` / `.model` are NOT present. `persist.vendor.harman.hardwareid` is unreadable from the shell uid (empty; `main.log` shows an avc denial on `persist_vendor_harman_hardwareid_prop` for `gm_update_engine`).
**Addendum 2026-11-12:** the value IS present in the `/cache` gmlogger `props` snapshots (29 of 30 boots): `persist.vendor.harman.hardwareid=MY23DV1` (also `persist.vendor.veh.variant=GB`, `persist.vendor.hw.variant=0xB1020260` in all 30) [read from the dump, not the live shell]. `MY23`-class id agrees with the Marvell module string; that the prop selects the switch driver remains [inferred].
Kernel `4.19.305-240125T145315Z-gf1edde901aa7` x86_64, `ro.build.version.security_patch=2025-06-05`.

### Hardware-variant word (`hw.conf`)
`/update_cache/update/hw.conf` holds the ASCII string `0xB1020260` (live Y181 bench, 2026-11-12). The recovery log decodes it:

| Field | Value |
|-------|-------|
| Variant | 177 (decoder's label; relation to the "Y177" firmware label undefined, forensic U13) |
| Global / Region | 0 / 0 |
| Project | 2 |
| HD radio / DAB / GPS option | 0 / 0 / 0 |
| AMP | 1 |
| SXM | 1 |
| Gyro+Accel / Gyro / Accel | 0 / 0 / 0 |

Source: `recovery/last_log*` line `Value: 0xB1020260  Variant: 177 Global: 0 Region: 0 Project: 2 HD: 0 AMP: 1 SXM: 1 DAB: 0 GPS: 0 ...` and `HW variant is 0xB1020260` [read]. Consistent with the donor truck's U2K (SiriusXM) and UQA (branded amp) RPOs [inferred]. Bit layout (nibble-to-field) is taken from the decoder's printout, not reverse-engineered.

**[ONLINE RESEARCH 2026-11-21] No public documentation found for `persist.vendor.hw.variant` or the value `0xB1020260`** (searches: "Harman hw.variant 0xB1020260", "persist.vendor.hw.variant automotive", "Samsung Harman infotainment hardware variant bitmask"). The recovery-log decoder output above is the only available decode; its field layout comes from Harman/GM internal tooling.

### GHS-dependent vs Android-dependent vehicle functions
- **GHS-dependent (work without Android, at hypervisor/VIP level):** turn-signal chimes, door chimes, seatbelt chimes, reverse backup camera, 360 surround view.
- **Android-dependent (need the guest VM):** climate display, steering-wheel button processing, navigation, audio playback/media, CarPlay/Android Auto.

(See section 7 for the measured radio-removal behaviour, which qualifies the chime statement.)

## 6. Android services and VHAL (from tech_specs sample)

```yaml
system_services:
  gm_specific: [GMLoggerService, ClusterService, CarPlayService, GALService,
    TCPS_privacy_service, GMAnalytics, TrustedDevice_phone_key,
    SubscriptionManager, OnStarServices_integrated]
  google_services: [GooglePlayServices_fragmented_1.3GB_ram, GoogleMaps_preinstalled, AutoTemplateHost]
  media_sessions: [TunerService_active, BluetoothMediaBrowser, LocalMediaPlayer_usb]

android_automotive:
  car_service: active
  vhal_properties: 156_registered
  occupant_zones: driver_only
  ux_restrictions: driving_state_monitoring
  power_policy: system_power_policy_all_on
  audio_zones: unverified  # Logical buses do not establish zone count.
  audio_output_buses: 12   # Live media.audio_policy, 2026-11-15: buses 0-8 and 11-13.
  projection_support: [AndroidAuto, CarPlay]
```
Neighbouring sample keys: `uptime_stability: 4.8_days`, `boot_count: 254`, `bottleneck_location: software_optimization`, `verified_boot: green_locked`, `selinux: permissive` - the last is the boot-cmdline arg (`androidboot.selinux=permissive`), NOT the runtime mode; stock Y177 runs `getenforce=Enforcing` (init ignores the cmdline value on a user build; research/security/KERNEL_CVE_ANALYSIS.txt Appendix E.8, note dated 2026-08-25). Posture owned by [`security.md`](security.md).

## 7. Removal-risk behaviour (OEM radio node)

**Measured: the owner has driven the truck with the radio module removed [VEH]:**
- **No RearCamera / 360 view.** Camera overlay/compositing runs on the **GHS partition of the radio's SoC** (guest ships `android.hardware.automotive.evs@1.0/1.1`, but compositing is GHS-side); no radio, no feed. [VEH]; firmware corroboration: EVS HALs present, guest is a GHS guest. [FW/VEH]
- **No vehicle audio at all**, including turn-signal ticks, door chimes and safety dings. The radio is the whole-vehicle audio hub/source, feeding the Bose amp (**T3**) over the **AVB Ethernet pair (bus 6, `A11<->T3`)** (`.103 = AMP_ETH`). Firmware corroboration: `vehicleaudiocontrol` registers a "chime-playback-status" callback and is gated on `vendor.gm.powermode ISystemStateListener`; `libgmaudiopowermode.so` exists; audio HAL + AVB/gPTP transport all live on the radio. [VEH + FW]
  - A Pi replacement must source ALL vehicle audio (chimes / turn-signal / seatbelt / safety dings), not just media, and drive the amp over AVB/TSN Ethernet. Audio HAL/amp details: [`avb_audio_transport.md`](avb_audio_transport.md).
- **Cluster gauges and safety info unaffected.** Speedometer, engine data and NHTSA-mandated displays run on the cluster's independent RTOS (IPC `.106` Visteon IPC); only the cards the radio feeds (time/temp, media, nav, calls) go blank. `.106 IPC` and the `.107` RTOS partition are separate nodes. [VEH]; [FW/VEH]

**Not yet observed, expected [INF]/[GM]:**
- The radio is CAN **ECU `0x80`** (via gateway `0x45`) and Ethernet node `.100` (SOME/IP-SD peer, `172.16.4.100`). On removal, other modules likely log "lost communication with radio / IVI" U-network DTCs and SOME/IP-SD peers lose the node. Driver-visible warning vs silent stored DTC: untested. [INF/GM]
- Telematics/OnStar (CGM `.107/.112`, EOCM `.12/.13/.15`) and remote features depend on the Ethernet fabric, not the radio, so should survive; any HMI rendered through the radio is gone. [INF]
- **SecOC is not a removal risk but is a replacement risk:** critical-control frames are authenticated with OEM-held keys, with no aftermarket provisioning path (Plane 1a). A Pi cannot forge SecOC'd frames; irrelevant if it stays on the Ethernet/FSA plane and never sources those CAN frames (recommended posture). [X->INF]

**Bottom line:** safety-critical function (cluster/RTOS) is independent of the radio; the radio is the camera compositor and whole-vehicle audio hub, riding GHS and AVB-Ethernet that a Pi does not natively reproduce. CAN is not the integration problem; Ethernet/FSA + AVB audio + GHS-hosted camera are. See [`pi_swap_feasibility.md`](pi_swap_feasibility.md), [`vehicle_network.md`](vehicle_network.md).

## 8. CalDef, VIP calibrations, UDS

The GM Info 3.7 maintains two distinct calibration systems.

### CalDef (Android/SoC calibration)
- Entries stored on the system partition; Android-level configuration and feature flags; part of the OTA-updated system image.

| CalDef Key | Type | Value |
|-----------|------|-------|
| DEVICE_REGISTRATION_ENABLE_CHECK_OVERRIDE | bool | FALSE |
| EXPIRATION_ENFORCEMENT | bool | TRUE |
| GIS763_PROGRAMMING_ENABLED | bool | TRUE |
| GIS763_SigningCertificateIssuer | string | CN=GPD/OU=GMNA GPD PRODUCTION/O=GENERAL MOTORS LLC |

(Related: `GIS864_USBProgrammingEnabled=1` in the CalSets.db baseline above.)

### VIP calibrations
- 31 `cal_` values stored in the RH850 VIP MCU firmware; control power management, CAN parameters, timing values; updated independently from Android OTA. VIP-side detail: [`vip_ipc_ghs.md`](vip_ipc_ghs.md).

### UDS diagnostic services used by DPS

| Service ID | Name | Notes |
|-----------|------|-------|
| $10 | DiagnosticSessionControl | Session management |
| $11 | ECUReset | Reset ECU |
| $22 | ReadDataByID | Read calibration/data |
| $27 | SecurityAccess | 32-byte seed: ECUID(16B) + random(16B) |
| $2E | WriteDataByID | Write calibration/data |
| $31 | RoutineControl | Start/stop/query routines |
| $34 | RequestDownload | Initiate firmware download |
| $36 | TransferData | Transfer firmware blocks |
| $37 | TransferExit | Complete firmware transfer |

DPS module IDs, signing tiers and package inventory: [`ota_programming_roles.md`](ota_programming_roles.md).

> **[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE.** The UDS service IDs, seed/key and CAN addresses above are off-SoC (CAN/DoIP) and were not (and must not be) probed in the disk-only shell capture. Only the Ethernet transport endpoint is observable: the `diagnosticsd` listener on `0.0.0.0:49156` (root) is live. The `gm.obd.IOBDService` (`OBDService`) and `gm.diagnostics_service.IDiagnosticsService` binders are registered (services.txt #63/#60).

## 9. FSA vehicle-telemetry property lists (DisplaysCoordination)

IPC serviceId 2027, port 9020, hosted by Visteon IPC (192.168.1.106:9020). Not connected on bench (SYN timeout, no RST; likely switch ACL or no response to unknown clients; distinct from "connection refused"). With the vehicle on it exposes:
- **READ (FSAProperty):** `getEngineOilLife`, `getTirePressure`, `getAirFilterLife`, `getBrakePadLife`, `getFuelEconomyKm_L`, `getFuelEconomyL_100km`, `getAverageVehicleSpeed`, `getBatteryVolts`, `getCoolantTemp`, `getOilPressure`, `getTransmissionFluidTemp`, `getTransmissionFluidLife`, `getDieselExhaustFluid`, `getEngineHours`, `getTrailerBrake`, `getTractionAndStability`, `getOffRoad`, `getTireLoad`, `getACCSpeedLimitStatus`, `getHUDOnOffStatus`, `getIPCLayout`, `getIPCSpeedConfig`, `getLifetimeFuelEconomyKm_L`, `getTrafficSignMemoryStatus` (+ more)
- **WRITE (RequestResponse):** `resetOilLife`, `resetFuelFilterLife`, `transmissionFluidReset`, `postTPMS_Relearn`, `setIPCLayout`, `setIPCSpeedConfig`, `postHUDUpDownButtons`, `postHUDIntensityButtons`, `postHUDOnOffButtons`, `postIPCNAV`, `postAugmentedReality`, `postTractionandStabilityRequest`, `postUnits` (+ more)

Wire format and service catalog: [`fsa_protocol.md`](fsa_protocol.md). (Owner of these lists is fsa_protocol per charter; kept here only as the vehicle-data view. Remove if the fsa_protocol copy is complete.)

## Open conflicts
1. **Gateway `0x45` identity.** Section 7 (VN L476-493 region) calls `0x45` "the gateway" for radio ECU `0x80`; CN/OPR/VN disagree on whether `0x45` is the CGM. Unresolved here; see [`vehicle_network.md`](vehicle_network.md).
2. **CGM `.107/.112` identity.** Section 7 cites telematics as "CGM `.107/.112`"; VN `.107/.112` identity is a flagged open conflict, while this doc also refers to `.107` as an RTOS partition separate from `.106` IPC. Not settled.
3. **`hw.conf` Variant 177 vs "Y177".** Relationship undefined (forensic U13); kept as decoder label only.
4. **Where CalDef lives vs CalSets.db.** Section 8 (FV) says CalDef is stored on the system partition and OTA-updated; CalSets.db was found under `update_cache/bootup_log/vendor/` and `/mnt/vendor/calibration/overrides`. Not reconciled whether CalDef == CalSets.db content; no source states it.
5. **SELinux mode.** tech_specs sample says `selinux: permissive` (cmdline arg, annotated as not runtime); emulator real-kernel reports permissive vs real radio Enforcing. Owned by security.md/emulator.md.
