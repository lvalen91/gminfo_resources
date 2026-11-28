# Calibration effect map

Links every row of the gminfo37 calibration database to what the **Y175** Android image does with it, as far as files
on disk can show. Written 2026-11-28. Three passes share one status ladder:

- **First slice** (100 settings: projection, Wi-Fi, Bluetooth, home screen): hand-traced rules, offline predictor.
- **Wide pass** (all 2573 image rows plus one bench-only row): automated classification of every name, with hand-traced
  rules added only where the code was read (framework launcher icons and icon ordering).
- **Settings pass** (the three packages that draw Settings, plus the time-of-day service): 25 hand-traced rules, 11
  value effects, 5 first-slice rules revised. See [Settings](#settings).

| File | Content |
|---|---|
| `map.json` | Per setting: group, type, image and bench value, override slot/part, status and its basis, rules, Java read sites, packages and native files naming it. Per group: status counts |
| `rules.py` | Hand-traced effect rules, runtime states, checks, code anchors, and the hand-checked wrapper, table and enum-catalog lists |
| `predict.py` | Lists traced effects that differ after a calibration or state change (offline; touches no radio) |
| `build_map.py` | Rebuilds `map.json`; fails if a rule, wrapper, table or enum-catalog anchor is missing from the decompiled sources |
| `tools/` | The extraction scripts for the wide pass (see [Rebuild](#rebuild)) |

```bash
./predict.py --set Apple_CarPlay_enableWireless=0
./predict.py --set TraileringAppType=1
./predict.py --set FM_RDS_Clocktime_enabled=1 --state onstar_subscription_valid=False
```

## Result

| Status | All rows | First slice | Bench rows with an override slot | Bench value differs from image |
|---|---|---|---|---|
| effect traced | 154 | 27 | 75 | 19 |
| read, effect not traced | 182 | 1 | 105 | 40 |
| mentioned in decompiled Java, read not established | 45 | 0 | 15 | 6 |
| name only | 853 | 43 | 538 | 350 |
| not found outside bulk lists | 1340 | 29 | 249 | 90 |
| Total | 2574 | 100 | 982 | 505 |

Of the 182 "read" rows, 177 have a typed getter call in decompiled Java and 5 rest only on the native read-set check
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
| read, effect not traced | A typed getter call names it in decompiled Java, directly, through a checked wrapper, a checked table loop, an app constant or a checked enum catalog; or a native binary's imported `CalId` set equals its getter-call set | That the value changes anything visible. The consequence was not followed |
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
- **Enum catalogs:** GMSettings, GMConnections and CarSettings bind each name to an enum entry (`CalItem.X`) and read
  it through `CalibrationRequest.getBooleanValue(CalItem.X)` and siblings. Values are cached in static maps for the
  life of the process, and a missing row reads as the entry's own default.

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

9 groups, 117 rows: 22 traced, 3 read, 1 mentioned, 36 name only, 55 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `HANDSFREE` | 22 | 0 | 0 | 0 | 22 | 0 | vehicleaudiocontrol 22 |
| `GIS512_CONNECTIONS` | 20 | 4 | 2 | 0 | 0 | 14 | DelayedWKSApp 6, GMConnections 3, GMSettings 3 |
| `GIS503_PHONEDOMAIN` | 18 | 1 | 0 | 0 | 0 | 17 | GMConnections 1, GMOnStar 1, GMSettings 1 |
| `BLUETOOTHFEATUREENABLES` | 14 | 0 | 0 | 0 | 14 | 0 | libpal_calibrations.so 14 |
| `GIS337_CONSUMERDEVICEPROJECTION` | 14 | 13 | 0 | 0 | 0 | 1 | DelayedWKSApp 17, GMConnections 6, GMSettings 6 |
| `WIFIINFO3` | 12 | 2 | 0 | 0 | 0 | 10 | GMConnections 3, GMSettings 3, DelayedWKSApp 2 |
| `GIS513_DEVICEPROJECTION` | 6 | 2 | 1 | 0 | 0 | 3 | DelayedWKSApp 7, GMBugReportService 2, GMConnections 2 |
| `USB` | 6 | 0 | 0 | 1 | 0 | 5 | none |
| `BLUETOOTHHMIPERFORMANCE` | 5 | 0 | 0 | 0 | 0 | 5 | none |

The first-slice rules live here (projection allowance, wireless listeners, hotspot, Settings); the Settings ones now
name the row they control ([Settings](#settings)). `BLUETOOTHFEATUREENABLES`
(profile enables, microphone setup) appears only in the table exported by `libpal_calibrations.so`, and `HANDSFREE`
only as a pointer table in `vehicleaudiocontrol`: both are name only, and no Java code reads the profile enables, so
static files do not show whether the Android Bluetooth stack honours them. Most of `WIFIINFO3` (DHCP range, transmit
power, device limits) and `GIS512_CONNECTIONS` has no reader on the image.

### Audio processing, volume, chimes

24 groups, 708 rows: 6 traced, 9 read, 4 mentioned, 441 name only, 248 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS631_CONFIGCHIMEPROD_STDTHEME0_GLOBALB` | 163 | 0 | 0 | 0 | 163 | 0 | GHSCalibrations 163 |
| `GIS631_CONFIGCHIMEPROD_CADTHEME1_GLOBALB` | 158 | 0 | 0 | 0 | 2 | 156 | GHSCalibrations 2 |
| `VEHICLESPECIFICEQUALIZATION` | 123 | 0 | 0 | 0 | 114 | 9 | vehicleaudiocontrol 114 |
| `REQUESTACTIONMAP` | 41 | 0 | 0 | 0 | 41 | 0 | vehicleaudiocontrol 35, vendor.harman.tuner-service 6 |
| `SINKLEVELCONTROLCALS` | 31 | 3 | 1 | 0 | 14 | 13 | vehicleaudiocontrol 17, GMConnections 5, GMSettings 5 |
| `GM_SR_TUNINGFILES` | 30 | 0 | 0 | 0 | 30 | 0 | vehicleaudiocontrol 30 |
| `CODEC` | 22 | 0 | 0 | 0 | 0 | 22 | none |
| `AOSPVOLUMEGROUPRAMPTIMES` | 20 | 0 | 0 | 0 | 20 | 0 | vehicleaudiocontrol 20 |
| `DISTORTIONLIMITING` | 19 | 0 | 0 | 0 | 19 | 0 | vehicleaudiocontrol 19 |
| `ROOMMODE` | 15 | 0 | 0 | 0 | 15 | 0 | vehicleaudiocontrol 15 |
| `DIRECTIONALAUDIOPROMPTRENDERING` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `VOLUMEGROUPRAMPTIMES` | 14 | 0 | 0 | 0 | 0 | 14 | none |
| `BRANDANIMATIONSAUDIOCUES` | 12 | 3 | 5 | 0 | 0 | 4 | animengine 5, GMConnections 3, GMSubscriptionManager 1 |
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
The six traced rows are Settings ones (chime and start-up volume limits, audio-cue rows); their audio-side use stays
untraced.

### Tuner

8 groups, 182 rows: 1 traced, 16 read, 34 mentioned, 50 name only, 81 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS502_TUNERHMI` | 53 | 0 | 1 | 27 | 0 | 25 | GMTunerService 1 |
| `GIS653_FMTUNER` | 41 | 1 | 5 | 1 | 30 | 4 | vendor.harman.tuner-service 36, GMTunerService 3, DelayedWKSApp 2 |
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

8 groups, 175 rows: 3 traced, 10 read, 0 mentioned, 76 name only, 86 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `FRONTREARCAMERASTATIC` | 86 | 3 | 8 | 0 | 75 | 0 | libpal_calibrations.so 86, GHSCalibrations 50, DelayedWKSApp 11 |
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

15 groups, 180 rows: 8 traced, 12 read, 0 mentioned, 56 name only, 104 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS618_SYSTEMSTATE` | 37 | 1 | 1 | 0 | 35 | 0 | libpal_calibrations.so 37, DelayedWKSApp 1, CarSettings 1 |
| `FACEPLATEBUTTONS_GLOBALA` | 29 | 0 | 2 | 0 | 0 | 27 | DelayedWKSApp 4 |
| `DISPLAYGESTURESANDTIMEOUTS` | 24 | 1 | 3 | 0 | 0 | 20 | GMSubscriptionManager 2, GMConnections 1, GMSettings 1 |
| `GIS619_BRIGHTNESSCONTROL_GLOBALA` | 19 | 0 | 0 | 0 | 0 | 19 | none |
| `GIS619_BRIGHTNESSCONTROL_GLOBALB` | 15 | 0 | 0 | 0 | 15 | 0 | libpal_calibrations.so 15 |
| `STEERINGWHEELSWITCHES_GLOBALA` | 13 | 0 | 0 | 0 | 0 | 13 | none |
| `GIS652_MULTIFUNCTIONCONTROLLER` | 12 | 0 | 6 | 0 | 0 | 6 | DelayedWKSApp 14 |
| `GIS611_SYSTEMPARAMETERS` | 9 | 0 | 0 | 0 | 1 | 8 | none |
| `CANHANDLERCALS` | 6 | 0 | 0 | 0 | 0 | 6 | none |
| `GIS651_TIMEOFDAY` | 6 | 6 | 0 | 0 | 0 | 0 | CriticalWKSApp 6, DelayedWKSApp 2, GMConnections 2 |
| `GARAGEMODECONFIGURATIONS` | 5 | 0 | 0 | 0 | 5 | 0 | android.hardware.automotive.vehicle@2.0-service-gm 5 |
| `TOUCHCONTROLLER` | 2 | 0 | 0 | 0 | 0 | 2 | none |
| `CUSTOMIZATIONGATEWAYTIMER` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS309_TOUCHLININTERFACE` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS549_MULTIFUNCTIONINFOTAINMENTCONTROLLER` | 1 | 0 | 0 | 0 | 0 | 1 | none |

`GIS618_SYSTEMSTATE` and `GIS619_BRIGHTNESSCONTROL_GLOBALB` (timeouts, brightness tables) are PAL-table rows: power
moding and backlight are handled below Android. Java reads cover time of day (CriticalWKSApp `TimeofDayService`,
traced in [Clock and time zone](#clock-and-time-zone)), the multifunction controller and faceplate mapping
(DelayedWKSApp) and a few gesture timeouts. `GARAGEMODECONFIGURATIONS` is imported by
the vehicle HAL as `CalId` symbols, but its five `CalibrationManager::get` calls go through a wrapper, so the reads are
not paired with names. Steering-wheel switch and most faceplate rows have no reader here.

### Climate, seats, energy, trailering, vehicle apps

13 groups, 230 rows: 5 traced, 67 read, 0 mentioned, 1 name only, 157 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS520_ENERGYUI` | 79 | 1 | 7 | 0 | 0 | 71 | DelayedWKSApp 8, CarSettings 1, GMBugReportService 1 |
| `GIS539_TRAILERAPPUI` | 49 | 1 | 38 | 0 | 0 | 10 | GMTrailer 39, GMBugReportService 2, GMEcommPayment 2 |
| `OFFROADAPP` | 31 | 1 | 0 | 0 | 0 | 30 | CarSettings 1, GMHomeScreen 1, GMSystemUI 1 |
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

15 groups, 112 rows: 4 traced, 13 read, 0 mentioned, 4 name only, 91 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS507_SETTINGS` | 28 | 3 | 3 | 0 | 1 | 21 | GMConnections 4, GMTeenMode 2, GMSettings 2 |
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
| `GIS525_AUTHENTICATORUI` | 1 | 1 | 0 | 0 | 0 | 0 | none |
| `SFS22_SECURITYEVENTLOGGINGFRD` | 1 | 0 | 0 | 0 | 0 | 1 | none |

A few reads in GMTeenMode, the account and registration services and GMSubscriptionManager. GMSettings and
GMConnections name 34 calibrations through a `CalItem` enum whose entries are fetched on demand by
`getBooleanValue(CalItem.X)` calls; these are now resolved as reads (`ENUM_KEYS` in `rules.py`) and all 34 are read
somewhere in the shared code. Most of them sit in other CalDef groups, so this family's counts understate what Settings
reads: see [Settings](#settings), which is organised by screen. Most personalization and driver-workload rows have no
reader on the image.

### Connected services and updates

13 groups, 101 rows: 3 traced, 32 read, 3 mentioned, 3 name only, 60 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GIS668_REMOTEOMADMSERVERINTERFACE_GLOBALA` | 25 | 0 | 0 | 0 | 0 | 25 | none |
| `GIS658_INFOTAINMENTPROGMASTER_GLOBALA` | 16 | 0 | 0 | 0 | 0 | 16 | none |
| `REMOTESERVERSETTINGS` | 15 | 1 | 9 | 0 | 0 | 5 | GMAuthTokenService 5, GMSubscriptionManager 4, GMRegistrationService 3 |
| `GIS887_REMOTEPROGRAMMINGHMI_GLOBALB` | 12 | 1 | 11 | 0 | 0 | 0 | GMBugReportService 12, GMEcommPayment 12, GMTrustedDevice 12 |
| `GIS505_ONSTARUI` | 9 | 0 | 4 | 0 | 3 | 2 | GMSubscriptionManager 2, GMOnStar 2, GMBugReportService 1 |
| `GIS697_REMOTEREFLASHINFOTAINMENTFUNCTIONAL_GLOBALA` | 9 | 0 | 0 | 0 | 0 | 9 | none |
| `GIS864_USBPROG_GLOBALB` | 7 | 0 | 7 | 0 | 0 | 0 | GMBugReportService 7, GMTrustedDevice 7, info3 7 |
| `GIS609_LICENSECOMPLIANCEMATERIALDISPLAY_GLOBALB` | 3 | 0 | 0 | 3 | 0 | 0 | none |
| `GIS1009_UPDATER` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS506_ONSTARTBTUI` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `GIS675_MYBRANDAPP_ACCESSVEHICLEDATA` | 1 | 1 | 0 | 0 | 0 | 0 | DelayedWKSApp 1, GMConnections 1 |
| `GIS675_VCA_COMMANDCONTROL` | 1 | 0 | 0 | 0 | 0 | 1 | none |
| `PARTNERAPPSCALS` | 1 | 0 | 1 | 0 | 0 | 0 | DelayedWKSApp 1 |

Good read coverage: `GIS887_REMOTEPROGRAMMINGHMI_GLOBALB` and `GIS864_USBPROG_GLOBALB` are read in full by the
framework update classes (`Calibrations.OTA`, `Calibrations.USB`), server names and timers by the token, registration
and subscription services. Effects were not traced. OMA-DM, reflash and programming-master groups are unread.

### Vehicle identity and region

3 groups, 32 rows: 4 traced, 13 read, 2 mentioned, 2 name only, 11 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `GLOBAL_INFO3` | 17 | 1 | 8 | 2 | 2 | 4 | android.hardware.automotive.vehicle@2.0-service-gm 8, GMRSISrc 6, services 5 |
| `GIS500_UI` | 10 | 2 | 1 | 0 | 0 | 7 | GMSystemUI 9, DelayedWKSApp 8, GMConnections 8 |
| `LANGUAGEANDREGIONALIZATIONGLOBALA` | 5 | 1 | 4 | 0 | 0 | 0 | DelayedWKSApp 10, libnavsens_gm.so 5, GMConnections 4 |

`GMBrand`, `GMModel` and `GMTrim` are read by nearly every GM package (theme and feature selection) and by
`animengine`, where the read set was checked in disassembly. `COUNTRY_CODE` is traced for the Alexa icon, CarPlay
touch fidelity and four Settings rows; its other reads are not followed. `GMBrand` and `GMModel` are traced only for
the Settings rows that test them. The fuel-type rows are imported by the vehicle HAL.

### Unassigned

1 groups, 1 rows: 0 traced, 0 read, 0 mentioned, 0 name only, 1 bulk lists only.

| CalDef group | Rows | Traced | Read | Mentioned | Name only | Bulk lists only | Named by (rows) |
|---|---|---|---|---|---|---|---|
| `(row absent from the image database)` | 1 | 0 | 0 | 0 | 0 | 1 | none |

`UPDATE_INDICATOR` exists only in the bench database, not in the image database.

## Settings

Organised by screen, not by CalDef group: the 46 calibrations named here come from 22 groups. Rule ids refer to
`rules.py`; "Bench" and "Image" are the rule's result with the bench dump values and the image defaults, every runtime
state assumed to allow the feature.

### Who draws what

| Package | Role | Calibration access |
|---|---|---|
| CarSettings (`com.android.car.settings`) | Home page and the AOSP-derived screens (Apps, System, About, Privacy, Security, Notifications). The launcher alias `Settings_Launcher_Homepage` and `android.settings.SETTINGS` open it | Own `CalItem` enum, 11 names, read in 2 classes |
| GMSettings (`com.gm.hmi.settings`) | GM screens opened by intent action: Vehicle, Date and time, Display, Sounds, Language, reset, quick start-up, location services, accounts and profiles | `com.gm.settings.data.calibration.CalItem`, 34 names |
| GMConnections (`com.gm.hmi.connection`) | Connections, Phones, Wi-Fi networks, Wi-Fi hotspot, projection pop-ups | Same `com.gm.settings.*` code as GMSettings (same `CalItem`) |
| GMSWUpdater, GMTCPS, GMOnStar, GMTrustedDevice | Updates, privacy statement, TTY, trusted device: opened from Settings rows | Own reads, effects not traced here |

Home page rows (CarSettings `homepage_fragment.xml`): Connections (`com.gm.settings.app.CONNECTIONS`, GMConnections),
Vehicle (`…VEHICLE`, GMSettings), Notifications, Apps, Date and time (`…DATETIME`, GMSettings), Display and Sounds
(`…DISPLAY`, `…SOUNDS`, GMSettings `DisplayActivity`), Profiles and accounts, Privacy, Security, System, Updates
(`…UPDATES`, GMSWUpdater), plus two groups filled from other packages' manifests. No home-page row is gated by a
calibration inside CarSettings; the Settings launcher icon itself is `icon.settings`
(`APPLICATION_HOMESCREEN_SETTINGS_ENABLED`).

Three mechanisms connect a calibration to a row:

1. **List filter.** A repository or signal class answers `isAvailable()`; the list builder leaves the row out.
2. **View visibility.** A data-binding class sets a row's views `VISIBLE` or `GONE` from an observable.
3. **Package manager.** GMSettings start-up enables or disables an activity (`setComponentEnabledSetting`). CarSettings
   builds some rows from `queryIntentActivitiesAsUser` by `com.android.settings.category`, so the row follows the
   component state. This state is stored under `/data` and changes only when GMSettings next starts as the Settings
   client.

### The obfuscated layer, resolved

GMSettings and GMConnections keep the Kotlin source-file name of every class ("compiled from" in jadx output), which
names the R8-renamed classes. Requests are dispatched by name: a view tag or activity call gives an event key,
`res/raw/eventmap.json` maps it to a method name, and `IManager.class.getMethod(name)` invokes it (GMSettings
`O/a.java`, GMConnections `T/a.java`). A handler method with no Java caller is therefore not dead until its event key
has been checked too.

| GMSettings class | Source file | Role |
|---|---|---|
| `Q/G` | `SDKManager.kt` | `IManager`: the reflective entry point; forwards to the handlers below |
| `Q/C0171q` | `BasicSettingsReqHandler.kt` | Date and time, sounds list, languages, about, quick start-up, system menu status |
| `Q/C0164j` | `AdvancedSettingsReqHandler.kt` | Developer options, remote devices, factory reset, running apps |
| `Q/C0165k` | `AppSettingsReqHandler.kt` | Memory data only |
| `Q/F` | `MultiUserProfileSettingsReqHandler.kt` | Users, accounts, sign-in |
| `Q/L` | `UserSettingsReqHandler.kt` | Privacy, permissions, location services |
| `Q/Q` | `VehicleSettingsReqHandler.kt` | Vehicle settings categories, options, lighting, volumes |
| `Q/A`…`Q/E`, `Q/C0155a`…`Q/C0163i`, `Q/C0166l`…`Q/C0170p`, `Q/H`…`Q/K`, `Q/N`…`Q/P`, `Q/w`…`Q/z` | `ExtensionFunctions.kt` | Use-case result callbacks (`Observer.Acceptor`, one `switch` per class): convert the result and call a `P/*` response handler |
| `Q/r`…`Q/u` | `EventBusHandler.java` | Event-bus consumers |
| `Q/M`, `Q/v` | none | Synthetic switch tables |
| `P/a`…`P/g` | `*ResHandler.kt` | Forward to `O/c`, then `Z/c` |
| `Z/c` | `ResponseListener.kt` | Builds the row lists and sets the observables the layouts bind to |
| `S/i` | `DataPoolDataHandler.kt` | The observable store (view model) |
| `V/*` | `*BindingImpl.java` | Data-binding classes, one per layout |

Callbacks read for this pass: `Q/C0162h` (cases 2, 3, 4), `Q/C0166l` (case 4), `Q/C0169o` (case 0), `Q/H` (case 3),
`Q/J` (case 2), `Q/z` (case 2), `Q/w` (case 2). The other `ExtensionFunctions.kt` classes were only checked for which
use cases they import (none of the calibration-dependent ones beyond those listed) and are not otherwise resolved.
GMConnections uses the same layout: `V/j` (`SDKManager.kt`), `V/b`, `V/e`, `V/g` (Bluetooth, hotspot, Wi-Fi network
request handlers), `p007d0/b` (`ResponseListener.kt`), `p000a0/*` (binding classes).

### Gates traced to a row

All are evidence level `traced`: code read, nothing run.

| Screen and row | True when | Effect of false | Bench | Image | Rule |
|---|---|---|---|---|---|
| Connections: Wi-Fi networks | `BACK_OFFICE_SERVER_ENABLED and WiFiEnable` | Row left out of the list | shown | shown | `ui.settings_wifi_networks` |
| Connections: Wi-Fi hotspot | `WiFiEnable and WiFiP2PEnable and APPLICATION_HOMESCREEN_WIFIHOTSPOT_ENABLED` | Row left out | shown | shown | `ui.settings_hotspot_available` |
| Connections: vehicle-to-phone sharing | `VCA_ACCESS_VEHICLE_DATA` | Row left out | shown | absent | `settings.connections.vehicle_to_phone_row` |
| Wi-Fi hotspot: Wi-Fi Services | neither `Apple_CarPlay_enableWireless` nor `AndroidAuto_enableWireless` | Row `GONE` | gone | shown | `ui.settings_wifi_services_menu` |
| Wi-Fi hotspot: Share Hotspot Data | `APPLICATION_HOMESCREEN_ONSTAR_ENABLED or BACK_OFFICE_SERVER_ENABLED` | Row `GONE` | shown | shown | `settings.hotspot.share_data_row` |
| Wi-Fi hotspot: password show/hide control | `COUNTRY_CODE == 4` | Control `GONE` | gone | gone | `settings.hotspot.password_reveal` |
| Phone details: Apple CarPlay on/off | `Apple_CarPlay_enableWireless` (CarPlay-type device) | Row not added | shown | absent | `settings.phone.carplay_toggle_row` |
| Phone details: Android Auto on/off | `AndroidAuto_enableWireless` (Android Auto-type device) | Row not added | shown | absent | `settings.phone.androidauto_toggle_row` |
| Date and time: Automatic Date / Time | `BACK_OFFICE_SERVER_ENABLED and GPS_DATA_SOURCE == 2`, or `not BACK_OFFICE_SERVER_ENABLED and GPS_DATA_SOURCE == 1` | Row `GONE`; GMSettings start-up writes `auto_time` = 0 | shown | shown | `settings.time.auto_datetime_row` |
| Date and time: Automatic Time Zone | the line above, and (`BACK_OFFICE_SERVER_ENABLED` and `APPLICATION_HOMESCREEN_ONSTAR_ENABLED` and a valid OnStar subscription, or `FM_RDS_Clocktime_enabled`) | Row `GONE` | shown if the subscription is valid | same | `settings.time.auto_timezone_row` |
| Sounds: audible touch feedback | `ENABLE_MENU_AUDIO_TOUCH_FEEDBACK` | Row left out | shown | absent | `settings.sounds.audible_touch_row` |
| Sounds: audio cue on/off and audio cue volume | `AUDIO_CUE_ACUE_RUN_ENABLED or AUDIO_CUE_WELCOME_ENABLE or AUDIO_CUE_ACUE_STOP_ENABLED` | Both rows left out | absent | absent | `settings.sounds.audio_cue_rows` |
| Sounds: wording of those two rows | `AUDIO_CUE_ACUE_STOP_ENABLED` | Start-up-only titles | n/a | n/a | `settings.sounds.audio_cue_shutdown_wording` |
| Privacy > Location: Location Services for OnStar | `APPLICATION_HOMESCREEN_ONSTAR_ENABLED and COUNTRY_CODE != 92` | Row left out | shown | shown | `settings.location.onstar_row` |
| System: quick start-up | `SUSPEND_TO_RAM_ENABLE` | Preference `UNSUPPORTED_ON_DEVICE` | shown | shown | `settings.car.quick_startup` |
| System: TTY | `TTYSetting` | OnStar TTY activity disabled in the package manager; row not built | shown | absent | `settings.car.tty_row` |
| System > About: device registration | `BACK_OFFICE_SERVER_ENABLED` | Registration activity disabled in the package manager; row not built | shown | shown | `settings.car.device_registration_row` |
| Apps: Alexa | `APPLICATION_HOMESCREEN_ALEXA_ENABLED and COUNTRY_CODE in (49, 5, 31)` | Entry dropped from the list | listed | listed | `settings.car.apps_alexa` |
| Apps: Off-road, Energy, Trailering, `com.gm.fse` | Always, unless `GMBrand == 3 and GMModel == 10`; then the app's own home-screen setting(s) | Entry dropped | listed | listed | `settings.car.apps_offroad`, `_energy`, `_trailering`, `_gmc_studio` |
| Vehicle: valet mode category | `ValetMaskMenu` | Category left out | absent | absent | `settings.vehicle.valet_mode` |
| Vehicle > Lighting: engine lighting | MY23 CSM product, `AmbientLightingEnable`, an auxiliary ambient signal available | Sub-row left out | absent | absent | `settings.vehicle.engine_lighting` |
| Vehicle: rear camera park assist symbols | `RVS_PRESENT_STATUS != 0`, and `RVS_FEATURE_AVAIL_UPA_SYMBOLS` (status 2: the vehicle property instead) | Sub-row left out | by property | shown | `settings.vehicle.rear_camera_park_assist` |
| Vehicle > Drive mode: selection overlay | `GMBrand == 3` | Sub-row left out | shown | absent | `settings.vehicle.drive_mode_overlay` |
| Account sign-in: network check | `DataServicesEnable` and `Settings.Global data_services_enabled` = 1 | Sign-in handlers get `NETWORK_SERVICE_DISABLED` | passes | disabled | `settings.account.network_service` |

Precision notes:

- "Left out of the list" was traced to the list the response listener or signal supervisor builds. For the Vehicle
  rows the final row view was not inspected.
- "Listed" in Apps says the entry passes this filter, not that the package is installed. For the four Corvette-only
  filters the bench set (`GMBrand` 3, `GMModel` 4) never reaches the calibration test.
- The two package-manager rows rest on one fact not read in code: that a disabled activity is not returned by the
  query (standard platform behaviour; the query passes no flag that would include disabled components).
- A listed Wi-Fi networks or hotspot row can still be greyed by `fid_wifi_disable_status`, `fid_hotspot_disable_status`
  and the MEC counter (runtime state, not calibrations).
- The Connections list also has a trusted-device row gated by `PlatformUtil.isGASBuild()` and the brand system
  property, not by a calibration read in these packages.

Value effects added (`VALUE_EFFECTS`): `MinChimeVolumeStep`, `MaxChimeVolumeStep` (chime volume slider ends),
`DefaultMaximumStartupVolume`, `GIS887_VehicleTransmissionType` (door-lock description text),
`GM_Account_Sign_In_Method` (1: e-mail and phone number, else e-mail only), and the six `GIS651_TIMEOFDAY` rows.

### Read in Settings code, effect not resolved

| Setting | Where | What is known |
|---|---|---|
| `DataServicesEnable` | `PermissionsRepository.isDataServicesCalibrationEnabled()` → `Q/H` → `Z/c.h0` (GM privacy list) | When false the list builder skips updating the Data Services row state; it does not remove the row. The visible result was not resolved, and no launcher of this screen's intent action (`…evG_PrivacyList`) was found in the 82 decompiled packages |
| `Apple_CarPlay_enableWireless`, `AndroidAuto_enableWireless` | `ProjectionRepository.isWirelessProjectionEnabled()` → GMConnections `V/b` → observable `t0` | Selects the "connect phone" header text of `ProjectionPopUpConnectPhone` and is bound into the projection phone lists; per-view effect not resolved |
| `EnableBluetooth`, `BluetoothDevicePairLimit` | `ui.settings_bluetooth` | Bound into three phone-list layouts; per-view effect not resolved |
| `GMBrand` | `WiFiHotspotRepository.getCollectionsName()`, `AuthenticationRepository.getOwnerCenterName()`, theme helper (`p038n0/b`, with `GMModel`) | Selects a store name string, the brand passed to sign-in screens and the UI theme; one theme (brand 9, model 7 or 8) changes a flag on the display-mode row. Not followed further |
| `REGIONS` | `TimeZoneManager.prepareTimeZones()` | Value 7 changes how the `Asia/Shanghai` entry of the time-zone list is labelled |
| `COUNTRY_CODE` | `GMAuthUtil` | Passed into account creation |
| `BTConnectionRequestTimer` | `BluetoothRepository.getConnectionRequestTimeout()` | Returned as the pairing timeout to the Phones screen (value effect) |

### Defined but not reached on this build

- **GMSettings "System" main menu.** `Z/c.a0` builds a 17-row list (date/time, phones, Wi-Fi networks, device remote
  access, Wi-Fi hotspot, privacy, …) with the same Wi-Fi, hotspot and remote-access filters. Its request
  (`onSystemMenuItemStatus`) is mapped from event key `evG_SystemMenuItems`, and no Java string, smali or layout in
  the package emits that key. CarSettings draws the home page instead. Static files do not exclude an emitter in
  another package.
- **GM application list.** `ApplicationsRepository.getAvailableApplications()` (with the CarPlay and Android Auto
  filter of `ui.settings_carplay_app`) has no caller: `GetAvailableApplicationsUseCase` is never instantiated in
  GMSettings or GMConnections.
- **Bluetooth, Wi-Fi, hotspot and projection use cases inside GMSettings.** Same code as GMConnections, no call sites
  in the GMSettings package; only GMConnections runs them.

### Clock and time zone

Question: can FM RDS clock time set the clock or the time zone without the telematics module?

**Implementation exists.** `com.gm.server.timeofday.TimeofDayService` in CriticalWKSApp observes `Settings.Global`
`auto_time` and `auto_time_zone` and is the component that calls `AlarmManager.setTime` and `setTimeZone`. It publishes
binder service `TimeofDay`; the framework's `NtpTrustedTime.getInstance()` returns `android.util.GMTrustedTime`, which
reads that binder instead of querying an NTP server.

| Quantity | Source | Selected by |
|---|---|---|
| Trusted (UTC) time, the only automatic input to the system clock | `GPS_DATA_SOURCE` 1: fix time of location updates (`GMLocationClient`). 2: vehicle property `VendorProperty.UTC`. 0: none | `GPS_DATA_SOURCE` (bench and image: 2) |
| Fallback clock | Remote real-time clock (`RemoteClockManager`), else 2020-01-01 | No trusted time |
| Local time, used only to derive a time zone | First choice: vehicle property `LOCAL_TIME`, available when `CELLULAR_NETWORK_DATE_AND_TIME_AVAILABLE` is true. Second: tuner RDS clock time | RDS allowed only if `FM_RDS_Clocktime_enabled` (bench and image: 0) |

What the code does with RDS (rule `time.rds_local_source`):

1. The broadcast-radio HAL `vendor.harman.tuner-service` exposes vendor parameter `com.gm.rds_time`. Its strings and
   symbols name `RdsClockTime`, `CTunerClientAdapter::processRdsClockTime`, `sendRdsTime`, `CTuner::updateRdsTime`,
   `localTimeOffset`, the text `RdsClockTime Disabled` and the calibration name
   `GIS653_FMTUNER_FM_RDS_Clocktime_enabled`; `vendor/etc/tuner/tuner.json` sets `FM_RDS_CLOCK_TIME_ENABLED` to 1. The
   binary was not decompiled: that it decodes the RDS clock-time group, and whether the calibration or the JSON value
   decides, is inferred from names only.
2. GMTunerService (`com.gm.gmaudio.tuner`, `k/m.java`) reads that parameter through `RadioTuner.getParameters` and
   parameter updates, adds an elapsed-time stamp and puts the JSON string into its media-session extras.
3. `GMTunerTimeSource` (CriticalWKSApp) reads the extras. It accepts a value when two successive values lie within
   180 s and either bit *country code* of `PI_CODE_CONFIGURATION` (bench 0) is set or the value is within
   `RDS_CLOCK_TIME_MAX_DIFF` (5) minutes of the system's own local clock.
4. `LocalTimeHandler` uses it as local time when `FM_RDS_Clocktime_enabled` is true and the vehicle's cellular local
   time is unavailable or invalid.
5. While `auto_time_zone` is 1, `TimeofDayService` rounds (local time minus trusted time) to half hours and, if the
   offset changed, sets the time zone to the first zone id for that raw offset whose id contains `GMT`, else the first
   id. After the first two minutes (and unless the current offset is zero) a change must lie between
   `TZDSTAdjust_LL` and `TZDSTAdjust_UL` seconds (1800 to 3600) and persist for `TZDSTAckWaitTime` (600) one-second
   polls. The media-session listener is registered on a user switch, not at service start.

Answers, with their basis:

- **RDS never sets the clock** (verified in code): every `AlarmManager.setTime` call in the service takes trusted
  time, the remote real-time clock or the default; local time is not an argument to any of them. Manual entry in
  Settings is the other writer.
- **RDS can set the time zone, only with `FM_RDS_Clocktime_enabled` = 1** (verified in code, not run). On the bench
  and image value 0 the tuner source is never selected and the Settings row falls back to the OnStar-subscription
  term.
- **The clock still needs a trusted source or manual entry.** With `GPS_DATA_SOURCE` = 2 that source is the vehicle
  property `UTC`. Which module feeds that property is outside this code (the enum calls it "ExternalOnStarGPS", the
  service "TCP_GPS"): inferred, not traced, that it is the telematics module. With no trusted time the service keeps
  the remote real-time clock's time; the time-zone offset is then computed against that clock.
- **Settings and the service use different conditions.** Settings shows the automatic rows only for
  `GPS_DATA_SOURCE` 2 with `BACK_OFFICE_SERVER_ENABLED`, or 1 without it, and forces `auto_time` to 0 otherwise. The
  service looks at `GPS_DATA_SOURCE` alone and applies trusted time in both modes (in manual mode it keeps the user's
  offset in `persist.sys.clockOffset`).
- **Unknown:** whether a location provider delivers fixes with `GPS_DATA_SOURCE` = 1 on this hardware; whether the HAL
  emits `com.gm.rds_time` when the calibration is 0; the zone id actually chosen for a given offset (a fixed-offset
  `GMT` zone has no daylight-saving rule); whether the AOSP time detectors also run (`services.jar` contains them and
  `framework-res` lists sources telephony, network, gnss with the GNSS time service enabled, but the system-server
  start-up method did not decompile).

### Not covered

- Rows whose availability comes from a vehicle property (most Vehicle settings): the property's own dependence on
  calibrations is in the vehicle HAL, not read.
- GMSWUpdater, GMTCPS, GMOnStar and GMTrustedDevice screens; the resource-overlay packages; `/data` state (component
  enable state, `Settings.Global` values, per-process calibration caches).
- GMSettings account, profile and security screens beyond the two calibrations named above.

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

**Expected yield.** On this image: 6% of rows traced to an effect, 13% with a located read (cumulative), 15% named in
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
- The Settings pass also read apktool output (layouts, `res/raw/eventmap.json`, smali) of GMSettings, GMConnections and
  CarSettings and `aapt2` manifest dumps of all 318 packages. Rule anchors cover the Java side only; layout and manifest
  facts are stated in rule notes and in [Settings](#settings).
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
values, first-slice read sites). A new wrapper, table or enum catalog goes into `rules.py` with an anchor only after
its body has been read.
