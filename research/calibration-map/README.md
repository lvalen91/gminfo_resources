# Calibration effect map

Links every row of the gminfo37 calibration database to what the **Y175** Android image does with it, as far as files
on disk can show. Written 2026-11-28. Two passes share one status ladder:

- **First slice** (100 settings: projection, Wi-Fi, Bluetooth, home screen): hand-traced rules, offline predictor.
- **Wide pass** (all 2573 image rows plus one bench-only row): automated classification of every name, with hand-traced
  rules added only where the code was read (framework launcher icons and icon ordering).

| File | Content |
|---|---|
| `map.json` | Per setting: group, type, image and bench value, override slot/part, status and its basis, rules, Java read sites, packages and native files naming it. Per group: status counts |
| `rules.py` | Hand-traced effect rules, runtime states, checks, code anchors, and the hand-checked wrapper and table lists |
| `predict.py` | Lists traced effects that differ after a calibration or state change (offline; touches no radio) |
| `build_map.py` | Rebuilds `map.json`; fails if a rule, wrapper or table anchor is missing from the decompiled sources |
| `tools/` | The extraction scripts for the wide pass (see [Rebuild](#rebuild)) |

```bash
./predict.py --set Apple_CarPlay_enableWireless=0
./predict.py --set TraileringAppType=1
```

## Result

| Status | All rows | First slice | Bench rows with an override slot | Bench value differs from image |
|---|---|---|---|---|
| effect traced | 129 | 27 | 63 | 12 |
| read, effect not traced | 198 | 1 | 111 | 44 |
| mentioned in decompiled Java, read not established | 54 | 0 | 21 | 9 |
| name only | 853 | 43 | 538 | 350 |
| not found outside bulk lists | 1340 | 29 | 249 | 90 |
| Total | 2574 | 100 | 982 | 505 |

Of the 198 "read" rows, 192 have a typed getter call in decompiled Java and 6 rest only on the native read-set check
(`animengine`, `vehiclepanel`).

## Value layers

1. **Image:** `vendor/calibrations/CalSets.db`, no overrides. Y175 and Y181 values match for every shared ID.
2. **Overrides:** the 14 applied payloads on the bench match the corresponding stock LTZ files (the supplied archive
   has a 15th file that is not applied).
3. **Live:** the bench `calibration` partition's `CalSets.db` (read from a copy of an eMMC dump). All 685
   single-value overrides compared match it. 297 more complex entries were not compared, one override ID is absent,
   5 rows without an override slot differ from the image, and one row exists only in the live database.

`bench` in `map.json` is the stored value at dump time, not proof of what a running process read.

Array, record and binary values are clipped in `map.json` (head plus length).

## Status of a setting

`effect traced` > `read, effect not traced` > `mentioned in decompiled Java, read not established` > `name only` >
`not found outside bulk lists`. `basis` in `map.json` states why a row has its status.

| Status | Meaning | What it does not mean |
|---|---|---|
| effect traced | A rule or value effect in `rules.py` connects the value to a behaviour; anchors verified in the sources | Tested. Other code paths can add to or override the rule |
| read, effect not traced | A typed getter call names it in decompiled Java, directly, through a checked wrapper, a checked table loop or an app constant; or a native binary's imported `CalId` set equals its getter-call set | That the value changes anything visible. The consequence was not followed |
| mentioned | Named in app Java as a table entry, constant or comparison, with no getter call found | Unused. Table and alias lookups are resolved at run time |
| name only | The name or GUID is in a native binary that imports a calibration getter, in the PAL table, or in a configuration file | A located read. No function was decompiled |
| not found outside bulk lists | Present only in the generated constant classes, `calserviced`, `libcalmgr.so` and the database | Unused in the vehicle. Non-Android controllers and by-group reads are invisible here |

## Evidence levels of a rule

- `traced`: code connects the setting to the effect. Not run.
- `observed`: supported by a saved record for **one** branch or combined change:
  - Hotspot: a Y181 truck log shows both Wi-Fi settings true, `Entered createWifiHotspot`, `Soft AP is started`.
    The false branch was not observed.
  - Projection tiles: owner record (2026-11-16) that both disappeared when both feature settings were false
    (not isolated, no cold-cycle test).

  - Home screen: owner recollection (2026-11-28, "might have forgotten some") of the Y175 bench with the LTZ set:
    Google apps, a GM projection app, trailering, hotspot, camera, SXM and Alexa.

| Listed app | Home-screen rule with bench values |
|---|---|
| Hotspot | Allows: all four settings true |
| Trailering | Allows if the app class matches the type selected by `TraileringAppType` = 2 (tile setting true) |
| Camera | Allows: tile setting true, `RVS_PRESENT_STATUS` = 2 |
| Alexa | Allows: tile setting true, `COUNTRY_CODE` = 49 (United States) |
| GM projection | CarPlay and Android Auto rules both allow; whether the listed app is one or both tiles is not recorded |
| SXM, Google apps | No specific case identified in this review; unlisted types default to allowed |

The same values also allow Audio, Phone, Users, Settings, Climate, OnStar and Off-road entries, if installed. They
disallow GM Navigation (`APPLICATION_HOMESCREEN_NAV_ENABLED` = false). Allowed by this rule does not prove an app is
installed or shown.

No rule has been confirmed by an isolated, controlled change.

## How names reach code on this platform

Checked on the Y175 image; each item changes what a search has to look for.

- **By name:** `gm.calibrations.CalibrationManager.getBoolean("Name", default)` and siblings. The dex holds the name.
- **By GUID:** `gm.calibrations.GMCalibrationsManager.getBoolean(GROUP.Name_CalID)`. The constant is inlined, so the dex
  holds only the row GUID (`_vZTHQMZZEeOEzdA9o_rOxw`). A name search misses these; 29 files on the image carry GUIDs.
- **Compatibility layer:** `gm.compat.calibrations.CalibrationManager` forwards to either API and holds a
  name-to-GUID map.
- **Native by GUID:** `android::GMCalibrationManager::getCalibration(const char*, ...)` and `getMultiCalibrations`;
  binaries keep name and GUID strings in pointer tables.
- **Native by symbol:** `libcalmgr.so` exports one `gm::calibrations::CalId::<Name>` object per calibration. A binary
  can read a calibration while holding no string for it (`animengine`, the vehicle HAL, `vehiclepanel`).
- **PAL table:** `libpal_calibrations.so` exports 336 `<GROUP>_<Name>` objects. No ELF file on the image imports them;
  `calserviced` imports only `calibration_pal_init`/`finalize`. Symbol names (`getCalDataRequest`,
  `palCalibrationCore::readRequest`) indicate a request server; its peer was not identified.
- **To the hypervisor side:** `GHSCalibrations` (230 names) writes calibration messages to `/dev/ghs/cal`.
- **Cached copies:** `gm.content.CalibrationShadow` persists values under the app cache directory (`calshadow/<name>`)
  and refreshes them when the calibration update indicator changes.

Twelve packages embed the full generated constant classes (all or nearly all 2573 names) and are not evidence of use:
info3.jar, diagnostics_pci_impl.jar, GMSXM, GMBugReportService, GMTrustedDevice, GMEcommPayment, GMAlexa, GMTCPS,
GMSubscriptionManager, GMNotifications, GMMyBrand, GMAnalytics. Their own code was still searched for reads.

## Per-group result

133 groups: 132 CalDef groups in the image database and one bench-only row. Groups are arranged in 13 families; each
table row is one group, each family has one note on what static files can and cannot show. "Named by" lists the
packages (Java read sites) and native files that name the most rows of the group.

### Home screen and launcher

6 groups, 179 rows: 98 traced, 3 read, 1 mentioned, 0 name only, 77 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS501_HOMESCREENUI` | 109 | 94 | 2 | 1 | 0 | 12 | info3 95, GMBugReportService 40, GMTrustedDevice 38 |
| `GIS674_MYMODE` | 55 | 1 | 0 | 0 | 0 | 54 | GMBugReportService 1, GMHomeScreen 1, GMTrustedDevice 1 |
| `GIS511_LVM` | 6 | 3 | 0 | 0 | 0 | 3 | DelayedWKSApp 3, GMBugReportService 3, GMEcommPayment 3 |
| `GIS521_APPSHOWUIWORKFLOW` | 5 | 0 | 0 | 0 | 0 | 5 | none |
| `GIS538_MYMODEUI` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `GIS1000_UIFRAMEWORKWIDGETS` | 1 | 0 | 1 | 0 | 0 | 0 | GMSubscriptionManager 1 |

The best-covered family. The framework class `gm.content.LauncherIconCalibrationHelper` (info3.jar) holds one switch
case per icon type and one ordering list, so 94 of the 109 `GIS501_HOMESCREENUI` rows have a traced rule (`icon.*`,
`ApplicationOrdering*`). GMHomeScreen bundles an obfuscated copy of the same switch; its hotspot case has one extra
term and its ordering list has 44 slots against the framework's 43. Not shown statically: which copy the running home screen uses for a given icon, whether an app is installed, and
the cached values in `calshadow/LauncherIcon` under the app cache directory. `GIS674_MYMODE` (54 of 55 rows) and the
other small groups have no reader on this image.

### Projection, connections, Wi-Fi, Bluetooth, phone

9 groups, 117 rows: 21 traced, 4 read, 1 mentioned, 36 name only, 55 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `HANDSFREE` | 22 | 0 | 0 | 0 | 22 | 0 | vehicleaudiocontrol 22 |
| `GIS512_CONNECTIONS` | 20 | 4 | 2 | 0 | 0 | 14 | DelayedWKSApp 6, GMSystemUI 2 |
| `GIS503_PHONEDOMAIN` | 18 | 0 | 1 | 0 | 0 | 17 | GMOnStar 1 |
| `BLUETOOTHFEATUREENABLES` | 14 | 0 | 0 | 0 | 14 | 0 | libpal_calibrations.so 14 |
| `GIS337_CONSUMERDEVICEPROJECTION` | 14 | 13 | 0 | 0 | 0 | 1 | DelayedWKSApp 17, CarService 2 |
| `WIFIINFO3` | 12 | 2 | 0 | 0 | 0 | 10 | DelayedWKSApp 2, GMBugReportService 2, GMEcommPayment 2 |
| `GIS513_DEVICEPROJECTION` | 6 | 2 | 1 | 0 | 0 | 3 | DelayedWKSApp 7, GMBugReportService 2, GMEcommPayment 2 |
| `USB` | 6 | 0 | 0 | 1 | 0 | 5 | none |
| `BLUETOOTHHMIPERFORMANCE` | 5 | 0 | 0 | 0 | 0 | 5 | none |

The first-slice rules live here (projection allowance, wireless listeners, hotspot, Settings). `BLUETOOTHFEATUREENABLES`
(profile enables, microphone setup) appears only in the table exported by `libpal_calibrations.so`, and `HANDSFREE`
only as a pointer table in `vehicleaudiocontrol`: both are name only, and no Java code reads the profile enables, so
static files do not show whether the Android Bluetooth stack honours them. Most of `WIFIINFO3` (DHCP range, transmit
power, device limits) and `GIS512_CONNECTIONS` has no reader on the image.

### Audio processing, volume, chimes

24 groups, 708 rows: 0 traced, 11 read, 8 mentioned, 441 name only, 248 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS631_CONFIGCHIMEPROD_STDTHEME0_GLOBALB` | 163 | 0 | 0 | 0 | 163 | 0 | GHSCalibrations 163 |
| `GIS631_CONFIGCHIMEPROD_CADTHEME1_GLOBALB` | 158 | 0 | 0 | 0 | 2 | 156 | GHSCalibrations 2 |
| `VEHICLESPECIFICEQUALIZATION` | 123 | 0 | 0 | 0 | 114 | 9 | vehicleaudiocontrol 114 |
| `REQUESTACTIONMAP` | 41 | 0 | 0 | 0 | 41 | 0 | vehicleaudiocontrol 35, vendor.harman.tuner-service 6 |
| `SINKLEVELCONTROLCALS` | 31 | 0 | 2 | 2 | 14 | 13 | vehicleaudiocontrol 17, CarService 1, DelayedWKSApp 1 |
| `GM_SR_TUNINGFILES` | 30 | 0 | 0 | 0 | 30 | 0 | vehicleaudiocontrol 30 |
| `CODEC` | 22 | 0 | 0 | 0 | 0 | 22 | none |
| `AOSPVOLUMEGROUPRAMPTIMES` | 20 | 0 | 0 | 0 | 20 | 0 | vehicleaudiocontrol 20 |
| `DISTORTIONLIMITING` | 19 | 0 | 0 | 0 | 19 | 0 | vehicleaudiocontrol 19 |
| `ROOMMODE` | 15 | 0 | 0 | 0 | 15 | 0 | vehicleaudiocontrol 15 |
| `DIRECTIONALAUDIOPROMPTRENDERING` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `VOLUMEGROUPRAMPTIMES` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `BRANDANIMATIONSAUDIOCUES` | 12 | 0 | 6 | 2 | 0 | 4 | animengine 5, GMSubscriptionManager 1 |
| `GIS1001_INCARCOMMUNICATION` | 7 | 0 | 0 | 0 | 0 | 7 | none |
| `AOSPSINKLEVELCONTROL` | 6 | 0 | 1 | 0 | 5 | 0 | vehicleaudiocontrol 6, CarService 1 |
| `AUDIOHMICALS` | 6 | 0 | 1 | 4 | 1 | 0 | vehicleaudiocontrol 1, GMAudioServer 1 |
| `GIS604_SAFETYRELATEDVOLUMEGROUPOVERRIDES` | 6 | 0 | 0 | 0 | 4 | 2 | vehicleaudiocontrol 4 |
| `GIS631_CONFIGSTDCHIMEPROD_GENERICCAL_GLOBALB` | 5 | 0 | 0 | 0 | 5 | 0 | GHSCalibrations 5, libpal_chime.so 4, vehicleaudiocontrol 3 |
| `GLOBALCHIMEGAINCALS` | 5 | 0 | 0 | 0 | 5 | 0 | GHSCalibrations 5, libpal_chime.so 5, vehicleaudiocontrol 5 |
| `FRONTZONEVOLUME` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `MUTEUNMUTERAMPTIMES` | 3 | 0 | 0 | 0 | 3 | 0 | vehicleaudiocontrol 3 |
| `GIS999_A2B_INTERFACE` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `TELEMATICSAUDIOCONTROLCALIBRATIONS` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `AMPINTERFACE` | 1 | 0 | 1 | 0 | 0 | 0 | GMAudioServer 2, GMSystemUI 2, DelayedWKSApp 1 |

Almost entirely native. `vehicleaudiocontrol` holds 297 names and 262 GUIDs in pointer tables and imports
`GMCalibrationManager::getCalibration`; the getter is reached through helper functions that take the GUID in a
register, so a per-name read was not established and the rows stay name only. The chime groups (`GIS631_*`,
`GLOBALCHIMEGAINCALS`) are in `GHSCalibrations`, which writes calibration messages to `/dev/ghs/cal`; their consumer is
outside Android. Values here are mostly arrays, records and binary tuning blobs, so even a located read would not give
a behaviour statement without the DSP semantics. Voice-tuning names also appear as file names under `vendor/etc/gmvt`.
`GIS631_CONFIGCHIMEPROD_CADTHEME1_GLOBALB` (156 of 158 rows), `CODEC` and `VOLUMEGROUPRAMPTIMES` have no reader here.

### Tuner

8 groups, 182 rows: 0 traced, 17 read, 34 mentioned, 50 name only, 81 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS502_TUNERHMI` | 53 | 0 | 1 | 27 | 0 | 25 | GMTunerService 1 |
| `GIS653_FMTUNER` | 41 | 0 | 6 | 1 | 30 | 4 | vendor.harman.tuner-service 36, GMTunerService 3, DelayedWKSApp 2 |
| `GIS655_DABTUNER` | 25 | 0 | 4 | 2 | 6 | 13 | vendor.harman.tuner-service 9, GMTunerService 4, GMMedia 1 |
| `GIS605_HDTUNER` | 23 | 0 | 0 | 3 | 0 | 20 | none |
| `GIS653_AMTUNER` | 18 | 0 | 4 | 0 | 10 | 4 | vendor.harman.tuner-service 14, DelayedWKSApp 2, GMTunerService 2 |
| `GIS625_SXMTUNER` | 9 | 0 | 2 | 0 | 0 | 7 | GMSXM 2, GMAlexa 1, GMMedia 1 |
| `GIS653_AMFMTUNERCOMMON` | 7 | 0 | 0 | 1 | 3 | 3 | vendor.harman.tuner-service 3, GHSCalibrations 1 |
| `GIS756_SXMAPP` | 6 | 0 | 0 | 0 | 1 | 5 | none |

Split three ways. `vendor.harman.tuner-service` carries 64 names in a pointer table and imports
`getMultiCalibrations` (name only). `GMTunerService` reads 11 by typed getter. GMAudio defines 51 names as
constants in `EnumCalibrations` and resolves them at run time through an alias map and a call into GMAudioServer
(`AudioCalibrationManager`), which is why 34 rows stop at "mentioned": the lookup key is built at run time and the
value crosses a process boundary. HD and SXM rows are largely unread on this image.

### Camera and video

8 groups, 175 rows: 2 traced, 11 read, 0 mentioned, 76 name only, 86 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `FRONTREARCAMERASTATIC` | 86 | 2 | 9 | 0 | 75 | 0 | libpal_calibrations.so 86, GHSCalibrations 50, DelayedWKSApp 11 |
| `GIS942_AUGMENTEDREALITY_GLOBALB` | 36 | 0 | 0 | 0 | 0 | 36 | none |
| `GIS738_RVCVIDEOROBUSTNESSREQUIREMENT` | 16 | 0 | 1 | 0 | 0 | 15 | DelayedWKSApp 4, GMSystemUI 3, GMTrustedDevice 3 |
| `IMAGE_ENHANCEMENT_TECHWELL_TW8845REGISTERS_WITH_DIGITAL_CAMERA` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `VIDEO_DECODER_TECHWELL_TW8845REGISTERS_WITH_ANALOG_CAMERA` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `GIS608_LVDS_I2C` | 5 | 0 | 1 | 0 | 0 | 4 | vehiclepanel 1 |
| `GIS1016_CAMERA` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `GIS742_DIGITALREARVIEWCAMERAINPUTFAULTDETECTION_VIDEOSWITCHREQUIREMENTS` | 2 | 0 | 0 | 0 | 1 | 1 | GHSCalibrations 1 |

`FRONTREARCAMERASTATIC` is in the PAL table (86 rows) and partly in `GHSCalibrations` (50): the rear-view pipeline that
uses crop, overlay and guideline geometry runs outside Android, so those rows are name only. Java reads 11 of them
(DelayedWKSApp camera model). The two `RVS_*` rows used by the launcher-icon switch are traced. The TW8845 register
groups and `GIS942_AUGMENTEDREALITY_GLOBALB` have no reader on the image.

### Diagnostics

9 groups, 279 rows: 0 traced, 1 read, 0 mentioned, 160 name only, 118 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS641_DIAGNOSTICCALDEF_GLOBALB` | 158 | 0 | 1 | 0 | 157 | 0 | libpal_calibrations.so 158, vendor.gm.diagnostics.ethernet@1.0-impl.so 158, DelayedWKSApp 1 |
| `GIS621_DIAGNOSTICCALDEF_GLOBALA` | 89 | 0 | 0 | 0 | 1 | 88 | none |
| `GIS641_INFO3_5C_CSM_DIAGNOSTICCALDEF_GLOBALB` | 15 | 0 | 0 | 0 | 0 | 15 | none |
| `GIS642_ONBOARDTESTERCOORD_GLOBALA` | 5 | 0 | 0 | 0 | 0 | 5 | none |
| `GIS888_DIAGNOSTICCALDEF_INFO3_5CSM_GLOBALA` | 4 | 0 | 0 | 0 | 0 | 4 | none |
| `CSM_ON_BOARD_TEST_DEVICE` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `CSM2IPCORTCP` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `ECUACTIVITYLEVELSELFREPORTING` | 2 | 0 | 0 | 0 | 2 | 0 | libpal_calibrations.so 2 |
| `ODI` | 1 | 0 | 0 | 0 | 0 | 1 | none |

`GIS641_DIAGNOSTICCALDEF_GLOBALB` (DTC and DID masks) is in the PAL table and in a pointer table of
`vendor.gm.diagnostics.ethernet@1.0-impl.so`: name only. `GIS621_DIAGNOSTICCALDEF_GLOBALA` (88 of 89 rows) and the CSM
groups are not referenced by any code on the image. Mask values gate which DTCs or DIDs a diagnostic server reports,
which a static read of the Android side cannot confirm.

### System state, display, controls

15 groups, 180 rows: 0 traced, 18 read, 2 mentioned, 56 name only, 104 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS618_SYSTEMSTATE` | 37 | 0 | 1 | 1 | 35 | 0 | libpal_calibrations.so 37, DelayedWKSApp 1 |
| `FACEPLATEBUTTONS_GLOBALA` | 29 | 0 | 2 | 0 | 0 | 27 | DelayedWKSApp 4 |
| `DISPLAYGESTURESANDTIMEOUTS` | 24 | 0 | 3 | 1 | 0 | 20 | GMSubscriptionManager 2, services 1 |
| `GIS619_BRIGHTNESSCONTROL_GLOBALA` | 19 | 0 | 0 | 0 | 0 | 19 | none |
| `GIS619_BRIGHTNESSCONTROL_GLOBALB` | 15 | 0 | 0 | 0 | 15 | 0 | libpal_calibrations.so 15 |
| `STEERINGWHEELSWITCHES_GLOBALA` | 13 | 0 | 0 | 0 | 0 | 13 | none |
| `GIS652_MULTIFUNCTIONCONTROLLER` | 12 | 0 | 6 | 0 | 0 | 6 | DelayedWKSApp 14 |
| `GIS611_SYSTEMPARAMETERS` | 9 | 0 | 0 | 0 | 1 | 8 | none |
| `CANHANDLERCALS` | 6 | 0 | 0 | 0 | 0 | 6 | none |
| `GIS651_TIMEOFDAY` | 6 | 0 | 6 | 0 | 0 | 0 | CriticalWKSApp 6, DelayedWKSApp 2 |
| `GARAGEMODECONFIGURATIONS` | 5 | 0 | 0 | 0 | 5 | 0 | android.hardware.automotive.vehicle@2.0-service-gm 5 |
| `TOUCHCONTROLLER` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `CUSTOMIZATIONGATEWAYTIMER` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS309_TOUCHLININTERFACE` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS549_MULTIFUNCTIONINFOTAINMENTCONTROLLER` | 1 | 0 | 0 | 0 | 0 | 1 | none |

`GIS618_SYSTEMSTATE` and `GIS619_BRIGHTNESSCONTROL_GLOBALB` (timeouts, brightness tables) are PAL-table rows: power
moding and backlight are handled below Android. Java reads cover time of day (CriticalWKSApp), the multifunction
controller and faceplate mapping (DelayedWKSApp) and a few gesture timeouts. `GARAGEMODECONFIGURATIONS` is imported by
the vehicle HAL as `CalId` symbols, but its five `CalibrationManager::get` calls go through a wrapper, so the reads are
not paired with names. Steering-wheel switch and most faceplate rows have no reader here.

### Climate, seats, energy, trailering, vehicle apps

13 groups, 230 rows: 4 traced, 68 read, 0 mentioned, 1 name only, 157 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS520_ENERGYUI` | 79 | 1 | 7 | 0 | 0 | 71 | DelayedWKSApp 8, GMBugReportService 1, GMHomeScreen 1 |
| `GIS539_TRAILERAPPUI` | 49 | 1 | 38 | 0 | 0 | 10 | GMTrailer 39, GMBugReportService 2, GMEcommPayment 2 |
| `OFFROADAPP` | 31 | 0 | 1 | 0 | 0 | 30 | GMHomeScreen 1, GMSystemUI 1 |
| `GIS550_CLIMATETOUCHSCREENUI_GLOBALB` | 20 | 2 | 16 | 0 | 1 | 1 | GMHvac 18, android.hardware.automotive.vehicle@2.0-service-gm 12, GMEcommPayment 3 |
| `HMIEXTERNALVEHICLEFEATURES` | 16 | 0 | 0 | 0 | 0 | 16 | none |
| `GIS517_SEATSTATUSPANEUI` | 7 | 0 | 6 | 0 | 0 | 1 | GMSeatStatusPane 6 |
| `GIS1050_REARCLIMATE` | 6 | 0 | 0 | 0 | 0 | 6 | none |
| `GIS550_CLIMATETOUCHSCREENUI_GLOBALA` | 6 | 0 | 0 | 0 | 0 | 6 | none |
| `GIS516_SAFETYSYSTEMSUI` | 5 | 0 | 0 | 0 | 0 | 5 | none |
| `GIS1062_VEHICLEINFORMATION` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `GIS551_AIRQUALITYUI` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `HYBRID` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `DRIVEMODEVISUALIZATIONANDCONFIGURATION_GLOBALB` | 2 | 0 | 0 | 0 | 0 | 2 | none |

Well covered for reads: GMHvac (through a checked wrapper), GMSeatStatusPane, GMTrailer (`TrailerCalibrationManager`
reads 39 rows into one object) and the DelayedWKSApp energy service. These are "read, effect not traced": the read is
located, the UI consequence of each value was not followed. `GIS520_ENERGYUI` (71 of 79 rows), `OFFROADAPP` and
`HMIEXTERNALVEHICLEFEATURES` are mostly unread, consistent with features for other propulsion types or vehicle lines,
but that reason is an inference.

### Navigation and location

4 groups, 136 rows: 0 traced, 3 read, 0 mentioned, 24 name only, 109 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `ADASIS` | 86 | 0 | 1 | 0 | 0 | 85 | DelayedWKSApp 1, VMSPlugin 1 |
| `GNSS_DR` | 23 | 0 | 1 | 0 | 22 | 0 | libnavsens_gm.so 23, libpal_calibrations.so 23, vendor.gm.gmlocation@1.0-service 7 |
| `NAVAPP` | 23 | 0 | 1 | 0 | 1 | 21 | DelayedWKSApp 1, GMSuperCruiseTTSService 1, VMSPlugin 1 |
| `GIS504_NAVIGATIONUI` | 4 | 0 | 0 | 0 | 1 | 3 | none |

`GNSS_DR` is read natively (`libnavsens_gm.so`, `vendor.gm.gmlocation@1.0-service`, pointer tables) and is in the
PAL table: name only. `ADASIS` (85 of 86 rows) and `NAVAPP` (21 of 23) have no reader; the embedded navigation they
configure is disabled by calibration on the bench set (`APPLICATION_HOMESCREEN_NAV_ENABLED` = 0).

### Speech

5 groups, 142 rows: 0 traced, 0 read, 0 mentioned, 0 name only, 142 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `SPEECHRECOGNITIONPERFORMANCE` | 55 | 0 | 0 | 0 | 0 | 55 | none |
| `GIS350_SPEECHADAPTATION` | 42 | 0 | 0 | 0 | 0 | 42 | none |
| `GIS582_SPEECH_RECOGNITION_SCREEN_FLOWS` | 25 | 0 | 0 | 0 | 0 | 25 | none |
| `GIS696_ASR_SSE` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `SPEECHRECOGNITIONCONTENTSETTINGS` | 6 | 0 | 0 | 0 | 0 | 6 | none |

No row in these five groups is referenced outside the bulk lists: not in Java, native code or configuration files.
Static files therefore say nothing about them beyond "no consumer found on this image".

### Settings, personalization, accounts, restrictions

15 groups, 112 rows: 1 traced, 13 read, 3 mentioned, 4 name only, 91 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS507_SETTINGS` | 28 | 1 | 3 | 2 | 1 | 21 | GMTeenMode 2, GMBugReportService 1, GMEcommPayment 1 |
| `GIS1007_SETTINGS_GLOBALB` | 23 | 0 | 0 | 0 | 2 | 21 | GHSCalibrations 1 |
| `GIS508_PERSONALIZATIONFBS` | 23 | 0 | 0 | 0 | 0 | 23 | none |
| `SFS1_PERSONALIZATIONFRD` | 15 | 0 | 3 | 0 | 1 | 11 | GMAuthTokenService 2, GMAPIManager 2, GMEcommPayment 2 |
| `GIS509_DRIVERWORKLOADRESTRICTIONS` | 4 | 0 | 0 | 0 | 0 | 4 | none |
| `GIS524_TERMSANDCONDITIONSDRIVERWORKLOAD` | 3 | 0 | 0 | 0 | 0 | 3 | none |
| `SFS2_SECURITYEXTENSIONSFRD` | 3 | 0 | 3 | 0 | 0 | 0 | GMAuthManagerService 2, GMRegistrationService 1 |
| `SFS5_TERMSANDCONDITIONSDEMOMODE` | 3 | 0 | 3 | 0 | 0 | 0 | GMSubscriptionManager 3 |
| `GIS1008_USERS` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `GIS507_SETTINGS_GLOBALB` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `GIS525_AUTHENTICATORDRIVERWORKLOADS` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `DRIVINGRESTRICTIONS` | 1 | 0 | 1 | 0 | 0 | 0 | GMSystemUI 1 |
| `GIS1024_TERMSANDCONDITIONS` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS525_AUTHENTICATORUI` | 1 | 0 | 0 | 1 | 0 | 0 | none |
| `SFS22_SECURITYEVENTLOGGINGFRD` | 1 | 0 | 0 | 0 | 0 | 1 | none |

A few reads in GMTeenMode, the account and registration services and GMSubscriptionManager. GMSettings and
GMConnections name 34 calibrations through a `CalItem` table whose entries are fetched on demand by generic
`getBooleanValue(CalItem)` calls; a table entry alone is counted as "mentioned". Most personalization and
driver-workload rows have no reader on the image.

### Connected services and updates

13 groups, 101 rows: 1 traced, 34 read, 3 mentioned, 3 name only, 60 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS668_REMOTEOMADMSERVERINTERFACE_GLOBALA` | 25 | 0 | 0 | 0 | 0 | 25 | none |
| `GIS658_INFOTAINMENTPROGMASTER_GLOBALA` | 16 | 0 | 0 | 0 | 0 | 16 | none |
| `REMOTESERVERSETTINGS` | 15 | 1 | 9 | 0 | 0 | 5 | GMAuthTokenService 5, GMSubscriptionManager 4, GMRegistrationService 3 |
| `GIS887_REMOTEPROGRAMMINGHMI_GLOBALB` | 12 | 0 | 12 | 0 | 0 | 0 | GMBugReportService 12, GMEcommPayment 12, GMTrustedDevice 12 |
| `GIS505_ONSTARUI` | 9 | 0 | 4 | 0 | 3 | 2 | GMSubscriptionManager 2, GMOnStar 2, GMBugReportService 1 |
| `GIS697_REMOTEREFLASHINFOTAINMENTFUNCTIONAL_GLOBALA` | 9 | 0 | 0 | 0 | 0 | 9 | none |
| `GIS864_USBPROG_GLOBALB` | 7 | 0 | 7 | 0 | 0 | 0 | GMBugReportService 7, GMTrustedDevice 7, info3 7 |
| `GIS609_LICENSECOMPLIANCEMATERIALDISPLAY_GLOBALB` | 3 | 0 | 0 | 3 | 0 | 0 | none |
| `GIS1009_UPDATER` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS506_ONSTARTBTUI` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS675_MYBRANDAPP_ACCESSVEHICLEDATA` | 1 | 0 | 1 | 0 | 0 | 0 | DelayedWKSApp 1 |
| `GIS675_VCA_COMMANDCONTROL` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `PARTNERAPPSCALS` | 1 | 0 | 1 | 0 | 0 | 0 | DelayedWKSApp 1 |

Good read coverage: `GIS887_REMOTEPROGRAMMINGHMI_GLOBALB` and `GIS864_USBPROG_GLOBALB` are read in full by the
framework update classes (`Calibrations.OTA`, `Calibrations.USB`), server names and timers by the token, registration
and subscription services. Effects were not traced. OMA-DM, reflash and programming-master groups are unread.

### Vehicle identity and region

3 groups, 32 rows: 2 traced, 15 read, 2 mentioned, 2 name only, 11 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GLOBAL_INFO3` | 17 | 1 | 8 | 2 | 2 | 4 | android.hardware.automotive.vehicle@2.0-service-gm 8, GMRSISrc 6, services 5 |
| `GIS500_UI` | 10 | 0 | 3 | 0 | 0 | 7 | GMSystemUI 9, DelayedWKSApp 8, GMVAC 8 |
| `LANGUAGEANDREGIONALIZATIONGLOBALA` | 5 | 1 | 4 | 0 | 0 | 0 | DelayedWKSApp 10, libnavsens_gm.so 5, GMBugReportService 2 |

`GMBrand`, `GMModel` and `GMTrim` are read by nearly every GM package (theme and feature selection) and by
`animengine`, where the read set was checked in disassembly. `COUNTRY_CODE` is traced for the Alexa icon and CarPlay
touch fidelity only; its many other reads are not followed. The fuel-type rows are imported by the vehicle HAL.

### Unassigned

1 groups, 1 rows: 0 traced, 0 read, 0 mentioned, 0 name only, 1 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `(row absent from the image database)` | 1 | 0 | 0 | 0 | 0 | 1 | none |

`UPDATE_INDICATOR` exists only in the bench database, not in the image database.

## What this method can and can't do, for next time

Independent of this vehicle. "Static" means firmware images, decompiled code, the calibration database and saved logs,
with nothing run.

**Reliable**

- Inventory: every row, its group, type, range, default and deployed value, and which override part supplies it.
- Finding Java readers. Typed getters with a constant key are easy to locate, including through thin wrappers once
  each wrapper is opened and checked. Sampling 22 of 862 read sites here found no false hit.
- Tracing an effect when the read and the decision sit in one method (a boolean gating a branch, a switch on an
  enumeration). One launcher-icon switch file accounts for most of the 94 traced home-screen rows.
- Proving absence of a mechanism on the image: for example that no code is stored only as `.vdex` (none of the 183
  packages without `classes.dex` here has a `.vdex` or `.odex`) and that no configuration file carries a row GUID.
- Showing which native binaries are involved, from strings, pointer tables and imported symbols.

**Reachable with more work, not automatically**

- Native read sites. Strings and imports show involvement; pairing a name with a call needs decompilation of each
  binary (helpers take the key in a register; Android packed relocations hide GOT targets from `objdump`). The
  set-level check used here works only when every call loads a distinct imported symbol directly.
- Effects of anything read into a field or object and used elsewhere. Each needs a manual data-flow trace; budget per
  setting, not per app.
- Obfuscated apps. Class and method names are gone, string keys survive, so reads are found but tracing costs more.

**Structurally out of reach**

- Controllers outside Android: the hypervisor side, the vehicle-interface processor, amplifier and tuner firmware.
  Rows that exist only in the PAL table or in the channel writer are consumed there.
- Keys built at run time: alias maps, loops over tables, keys passed across a process boundary, by-group or by-index
  reads. The name appears as data, the read does not.
- State under `/data` (encrypted at rest): cached calibration copies, user settings that mask a calibration,
  server-pushed configuration, feature flags.
- Whether a read value matters: defaults that equal the calibration, code paths not taken in this vehicle
  configuration, a second component that overrides the first.
- Values without semantics: equaliser coefficients, register tables, tuning blobs. Locating the reader does not
  yield a behaviour statement.
- Anything timing- or sequence-dependent (read once at boot versus on change; reboot or cold cycle needed).

**Traps met here**

- Searching by name only. The by-GUID API and the per-name exported symbols both hide readers from a name search.
- Catalog packages. Any package embedding the generated constants matches every name.
- Decompiler constant substitution. In a package that bundles the constant class, jadx prints any equal plain string
  as `CalId.<name>` (the UI string "Search" became `CalId.Search`). A `CalId` reference without a calibration getter
  nearby is not evidence.
- Generic names (`Search`, `Help`, `STREAM_MUSIC`) match unrelated code and binaries; they need a calibration link
  before they count.
- Same-shaped getters. `getBoolean(key, default)` is also SharedPreferences and Bundle; resolve the receiver type.
- Wrappers that read a calibration for some keys and an app preference for others (`RSIApplication.T`).
- Duplicate logic. The framework and an app can each carry a copy of the same gate with different terms.
- Logs rarely print calibration names. Saved logs here named 18 of 2573, ten of them generic stream names; they print
  derived values under the component's own wording, so a log check has to be designed per rule from the code.

**Expected yield.** On this image: 5% of rows traced to an effect, 13% with a located read (cumulative), 15% named in
app code, 48% tied to some component, 52% with no consumer on the Android side. The traced share grows only by manual
work and clusters where one file gates many rows. Treat "name only" and "not found" as unknown, never as no effect,
and plan a bench observation for any row that matters.

## Limits

- `predict.py` assumes every runtime state allows the feature unless `--state` says otherwise. "No difference" means
  no **traced** rule changed.
- Rules describe the named code path only. Other components can override or duplicate them.
- Read sites come from pattern matching on jadx 1.5.7 output, not data-flow analysis. Receiver type was resolved for
  698 of 706 direct reads; the other 8 sit in files that use calibrations.
- Native evidence comes from `nm`, `objdump` and string scans of x86-64 binaries. Nothing native was decompiled.
- 174 resource-overlay packages and the Google prebuilt apps were not examined for calibration-dependent behaviour.
- The scan covers the Y175 image. Y181 values match for shared IDs; Y181 code was not re-scanned.
- Rule anchors check that text exists, not that the logic is unchanged. Re-read the code for another build.
- Rebuild inputs (merged values, site lists, jadx trees) are derived from firmware and the bench dump and are not
  stored here.

## Rebuild

`IMG` is the mounted image root, `DB` its `vendor/calibrations/CalSets.db`, `SRC` one or more directories of jadx
output (`jadx --no-res -d SRC/<App> <package>` for each package `scan_image.py` reports with a name, a GUID or
`uses_api`; 82 trees here, framework.jar included).

```bash
tools/scan_image.py   DB IMG packages.json      # dex string tables, vdex/odex tokens, catalog detection
tools/native_refs.py  DB IMG native.json        # ELF strings, pointer tables, CalId imports, read-set check
tools/config_files.py DB IMG config.json        # names and GUIDs in other files
tools/java_sites.py   DB sites.json SRC...      # classified Java sites (uses rules.WRAPPERS and rules.TABLES)
tools/log_mentions.py DB logs.json LOGDIR...    # names in saved runtime text
./build_map.py scope.json values.json reads.json SRC --root SRC2 --db DB --sites sites.json \
    --packages packages.json --native native.json --config config.json --logs logs.json --groups-md groups.md
```

`scope.json`, `values.json` and `reads.json` are the first-slice inputs (name list, merged image/override/bench
values, first-slice read sites). A new wrapper or table goes into `rules.py` with an anchor only after its body has
been read.
