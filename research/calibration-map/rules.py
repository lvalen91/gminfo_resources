"""Hand-traced effect rules for Y175. Each anchor is (app, file, text that must be present).

The file is relative to <app>/sources/com/gm/, or to <app>/sources/ when it starts with "@". WRAPPERS and TABLES keys
are always relative to <app>/sources/. build_map.py fails if any anchor text is missing.

`expr` is a Python expression over calibration names (typed values) and runtime-state names from STATE.
`level`: traced = code connects the setting to the effect; observed = a saved log or owner record shows it.
"""

# Assumed "everything else allows it" runtime state; override with predict.py --state name=value.
STATE = {
    "bt_adapter_on": True, "fid_hotspot_disable_status": 0, "hmi_hotspot_disable_status": 0,
    "fid_wifi_disable_status": 0, "wifi_usable": True, "country_allows_wifi": True,
    "system_state_active": True, "system_state_not_disabled": True, "country_is_JP_or_KR": False,
    # Settings pass
    "onstar_subscription_valid": True, "product_is_my23_csm": True, "ambient_aux1_signal_available": True,
    "park_assist_property_available": True, "data_services_setting_on": True,
    # Bench pass
    "trailer_backoffice_allowed": True,
}

DW = "DelayedWKSApp"
WLAN = "server/wlanservice/GMWlanServiceImpl.java"
DIM = "server/connection/DeviceInfoManager.java"
UBR = "server/screenprojection/RemoteDeviceService/UsbBroadcastReceiver.java"
HOT = "settings/repositories/WiFiHotspotRepository.java"
APPS = "settings/repositories/ApplicationsRepository.java"
BTR = "settings/repositories/BluetoothRepository.java"
CPC = "server/carplay/service/internals/utils/CarPlayConfiguration.java"
BOR = "settings/repositories/BackOfficeRepository.java"
CONN = "GMConnections"
CONN_RL = "@p007d0/b.java"  # ResponseListener.kt of GMConnections


AUD = "GMAudio"
AUD_RL = "hmi/radio/events/listener/ResponseListener.java"
AUD_RL_FM_RDS = (AUD, AUD_RL, 'if (audioCalibrationManager.b("rds_radio_menu_item_on")) {')
AUD_ALIAS_RDS = (AUD, "@p003c/a.java", 'map.put("rds_radio_menu_item_on", EnumCalibrations.RDS_RADIO_MENU_ITEM_ON);')
AUD_CLIENT = (AUD, "@p017j/f.java", 'return f(e.o("calibration", str));')
AUD_SERVER = ("GMAudioServer", "gmaudio/server/model/SettingsSession.java", 'CalibrationManager.class.getDeclaredMethod("get", String.class)')
_AUD_NOTE = ("GMAudio (com.gm.hmi.radio) AudioCalibrationManager maps the key through an alias table and fetches the value "
             "from GMAudioServer, which calls CalibrationManager.get(name) by reflection; a value not yet delivered reads as "
             "false. Traced to the list onAddAudioSettingsList() builds; the row view was not inspected.")
TRL_NET = "trailercore/data/backoffice/Managers/TrailerNetworkConnectionManager.java"


def rule(id, feature, expr, effect, check, anchors, level="traced", note=""):
    return dict(id=id, feature=feature, expr=expr, effect=effect, check=check, anchors=anchors, level=level, note=note)


RULES = [
    rule("bt.carplay_listener", "CarPlay Bluetooth discovery",
         "bt_adapter_on and Apple_CarPlay_enableWireless",
         "CarService opens RFCOMM listeners for the CarPlay marker and accessory iAP2 UUIDs",
         "log 'CalibrationManager return WCP:'; scan EIR and SDP from outside",
         [("CarService", "bluetooth/impl/BtWPTransportImpl.java", '"Apple_CarPlay_enableWireless"')],
         note="Read when WPService is created."),
    rule("bt.androidauto_listener", "Android Auto Bluetooth discovery",
         "bt_adapter_on and AndroidAuto_enableWireless",
         "CarService opens the Android Auto RFCOMM listener",
         "log 'CalibrationManager return WAA:'; scan SDP",
         [("CarService", "bluetooth/impl/BtWPTransportImpl.java", '"AndroidAuto_enableWireless"')]),
    rule("usb.iap2_bt_declaration", "CarPlay USB iAP2 declaration",
         "Apple_CarPlay_enableWireless",
         "USB iAP2 identification adds the Bluetooth transport component and BTOOBPairing",
         "iAP2 identification trace",
         [(DW, "server/iap2/USBAccessory.java", "new BTOOBPairing(this)")]),
    rule("carplay.init_waits_for_radio", "CarPlay start waits for radio and WLAN",
         "Apple_CarPlay_enableWireless",
         "CarPlay initialisation waits (1 s retries) for a Bluetooth ID and GM WLAN service, then sets the Wi-Fi adapter name",
         "log 'retry initializeCarPlay after 1 sec..'",
         [(DW, "server/carplay/service/internals/CarPlayManager.java", "retry initializeCarPlay after 1 sec")],
         note="System property persist.carplay.disable=1 separately skips initialisation."),
    rule("carplay.allowance", "CarPlay connection allowance",
         "Enable_Application_Apple_Carplay",
         "Connection manager sets the CarPlay allowance bit and notifies CarPlay allowance listeners",
         "log 'Calibration CP enabled:' and 'updateProjectionUserAllowance service id 2'",
         [(DW, DIM, "updateProjectionUserAllowance(2, cpEnabled)")]),
    rule("androidauto.allowance", "Android Auto connection allowance",
         "Enable_application_google_Automotive_link",
         "Connection manager sets the Android Auto allowance bit",
         "log 'updateProjectionUserAllowance service id 3'",
         [(DW, DIM, "updateProjectionUserAllowance(3, galEnabled)")]),
    rule("usb.apple_state_machine", "Wired iPhone handling",
         "Enable_Application_Apple_Carplay",
         "USB attach is sent to the Apple state machine; when false it logs that the machine is disabled",
         "log 'RDMSAppleStateMachine disabled' (false) or 'ATTACH to AppleStateMachine sent' (true)",
         [(DW, UBR, "doAttachApple.RDMSAppleStateMachine disabled"),
          (DW, UBR, 'getBoolean("test.usb.rdms.CP", this.carplayEnabled)')],
         note="test.usb.rdms.CP, if set, overrides the calibration. Effect on a kernel NCM driver not shown by this code."),
    rule("carplay.wireless_device_listing", "Wireless CarPlay device list",
         "Apple_CarPlay_enableWireless",
         "Non-USB devices with wireless-projection support are added to the CarPlay device list",
         "log 'Adding BT connected device' / 'Adding WP profile capable device'",
         [(DW, DIM, "Adding WP profile capable device")],
         note="The current projection device and USB-connected devices can be listed anyway."),
    rule("wifi.station_allowed", "Wi-Fi client",
         "WiFiEnable and fid_wifi_disable_status == 0 and wifi_usable and country_allows_wifi "
         "and system_state_not_disabled and (BACK_OFFICE_SERVER_ENABLED or country_is_JP_or_KR)",
         "canWifiEnabled() returns true and GM WLAN service turns Wi-Fi on",
         "log 'isTcpDisabledWIFI: ... mWifiCal:'",
         [(DW, WLAN, "public boolean canWifiEnabled()")], note="Emulator path returns true."),
    rule("wifi.hotspot_allowed", "Hotspot start",
         "WiFiEnable and WiFiP2PEnable and fid_hotspot_disable_status == 0 and wifi_usable and country_allows_wifi "
         "and system_state_active and (Apple_CarPlay_enableWireless or AndroidAuto_enableWireless or hmi_hotspot_disable_status == 0)",
         "canWifiApEnabled() true; createWifiHotspot() calls WifiManager.startTetheredHotspot",
         "log 'Entered createWifiHotspot' then 'Soft AP is started'",
         [(DW, WLAN, "startTetheredHotspot"), (DW, WLAN, "AP creation is disabled by calibration")],
         level="observed",
         note="Observed (true branch only) in a Y181 truck log. createWifiHotspot() also refuses on an existing STA connection."),
    rule("ui.settings_hotspot_available", "Settings > Connections: Wi-Fi hotspot row",
         "WiFiEnable and WiFiP2PEnable and APPLICATION_HOMESCREEN_WIFIHOTSPOT_ENABLED",
         "isWifiHotspotAvailable() true: the Connections screen (GMConnections ConnectionsActivity) lists the Wi-Fi hotspot row; "
         "false: the row is left out of the list", "open Settings > Connections and look for Wi-Fi hotspot",
         [("GMSettings", HOT, "isWifiHotspotAvailable()"), (CONN, CONN_RL, "systemMenuItemStatus.getIsWifiHotSpotAvailable()"),
          (CONN, "hmi/connection/ui/activities/ConnectionsActivity.java", 'q().g("eSystemMenu")')],
         note="A listed row is greyed (not removed) when isHotspotEnableAllowed() is false. GMSettings carries the same list builder "
              "(Z/c.java a0) but no code or layout in it emits its trigger event evG_SystemMenuItems."),
    rule("ui.settings_wifi_services_menu", "Settings > Connections > Wi-Fi hotspot: Wi-Fi Services row",
         "not (Apple_CarPlay_enableWireless or AndroidAuto_enableWireless)",
         "The Wi-Fi Services row of the hotspot screen is VISIBLE only with BOTH wireless projection settings off, else GONE; "
         "when hidden, Settings shows hotspot options regardless of hmi_hotspot_disable_status",
         "open Settings > Connections > Wi-Fi hotspot and look for the Wi-Fi Services row",
         [("GMSettings", HOT, "isWifiServicesMenuAvailable()"), ("GMSettings", HOT, "Since WiFiServicesMenu is hidden"),
          (CONN, "@p000a0/C0192t.java", "i6 = mIsWifiServicesMenuAvailable ? 0 : 8;")],
         note="Binding ActivityWifiHotspotListImpl sets the visibility of group1 (lbid_primary_constraints, the Wi-Fi Services row)."),
    rule("ui.settings_wifi_networks", "Settings > Connections: Wi-Fi networks row",
         "BACK_OFFICE_SERVER_ENABLED and WiFiEnable",
         "isWifiNetworksAvailable() true: the Connections screen lists the Wi-Fi networks row; false: the row is left out",
         "open Settings > Connections and look for Wi-Fi networks",
         [("GMSettings", "settings/repositories/WiFiNetworksRepository.java", "isWifiNetworksAvailable()"),
          ("GMSettings", BOR, "getBooleanValue(CalItem.BACK_OFFICE_SERVER_ENABLED)"),
          (CONN, CONN_RL, "systemMenuItemStatus.getIsWifiNetworksAvailable()")],
         note="A listed row is greyed when fid_wifi_disable_status is not 0, or the MEC counter is non-zero outside developer mode."),
    rule("ui.home_hotspot_tile", "Home screen: hotspot",
         "APPLICATION_HOMESCREEN_WIFIHOTSPOT_ENABLED and WiFiEnable and WiFiP2PEnable and APPLICATION_HOMESCREEN_ONSTAR_ENABLED",
         "Home screen allows the hotspot tile", "home screen / app tray",
         [("GMHomeScreen", "@T/C0114g.java", 'g("WiFiP2PEnable") && c0129w.g("APPLICATION_HOMESCREEN_ONSTAR_ENABLED")')],
         level="observed", note="Owner recollection 2026-11-28 of the bench with the LTZ set: hotspot app shown (true branch only)."),
    rule("ui.home_carplay_tile", "Home screen: CarPlay",
         "APPLICATION_HOMESCREEN_APPLECARPLAY_ENABLED and Enable_Application_Apple_Carplay",
         "Home screen allows the CarPlay tile", "home screen / app tray",
         [("GMHomeScreen", "@T/C0114g.java", 'g("APPLICATION_HOMESCREEN_APPLECARPLAY_ENABLED")')],
         level="observed",
         note="Owner record 2026-11-16: UI disappeared with both projection feature settings false. Services kept running."),
    rule("ui.home_androidauto_tile", "Home screen: Android Auto",
         "APPLICATION_HOMESCREEN_ANDROIDAUTO_ENABLED and Enable_application_google_Automotive_link",
         "Home screen allows the Android Auto tile", "home screen / app tray",
         [("GMHomeScreen", "@T/C0114g.java", 'g("APPLICATION_HOMESCREEN_ANDROIDAUTO_ENABLED")')],
         level="observed", note="Same owner record as the CarPlay tile."),
    rule("ui.settings_carplay_app", "GM application list: CarPlay and Android Auto entries",
         "Enable_Application_Apple_Carplay",
         "ApplicationsRepository.isAppEnabled() returns true for com.gm.carplay and com.gm.hmi.carplay "
         "(Enable_application_google_Automotive_link does the same for com.gm.gal and com.gm.hmi.androidauto)",
         "none: no screen reached", [("GMSettings", APPS, 'case "com.gm.hmi.carplay"')],
         note="Not reached on this build: GetAvailableApplicationsUseCase is never instantiated in GMSettings or GMConnections. "
              "The Apps list opened from the Settings home page is CarSettings' own (settings.car.apps_* rules)."),
    rule("ui.settings_bluetooth", "Settings > Connections > Phones: Bluetooth state",
         "bt_adapter_on and EnableBluetooth and BluetoothDevicePairLimit > 0",
         "GMConnections reports Bluetooth as enabled to its Phones screens (UI state; this does not switch the adapter)",
         "log 'Bt adapter enabled: ..., calBtEnabled:'",
         [("GMSettings", BTR, "calBtPairLimit"), (CONN, "@V/b.java", "new GetBluetoothStateUseCase().execute(new n())")],
         note="Bound into the phone-list layouts (ActivityPhonesListImpl, DeviceListImpl, ProjectionDeviceListImpl); the per-view "
              "consequence was not resolved. The GMSettings copy of the use case has no caller."),
]

# Framework launcher-icon gate: gm.content.LauncherIconCalibrationHelper.isApplicationVisible() in info3.jar, one switch
# case per icon type. LauncherIconManager.buildIcon() marks the icon visible and gives it a default order only when the
# case returns true, and getAllKnown() skips a type whose case returns false. A missing calibration reads as false.
ICON = "@gm/content/LauncherIconCalibrationHelper.java"
HS = "APPLICATION_HOMESCREEN_"
ICONS = [
    ("AUDIO", f"{HS}AUDIO_ENABLED"), ("DMB_LVM", f"{HS}DMBLVM_ENABLED"), ("PHONE", f"{HS}PHONE_ENABLED"),
    ("NAV", f"{HS}NAV_ENABLED and ENABLE_APPLICATION_NAVIGATION"), ("NAV_LVM", f"{HS}NAVLVM_ENABLED"),
    ("WIFI_HOTSPOT", f"{HS}WIFIHOTSPOT_ENABLED and WiFiEnable and WiFiP2PEnable"),
    ("USERS", f"{HS}USERS_ENABLED"), ("SETTINGS", f"{HS}SETTINGS_ENABLED"),
    ("CARPLAY", f"{HS}APPLECARPLAY_ENABLED and Enable_Application_Apple_Carplay"),
    ("ANDROID_AUTO", f"{HS}ANDROIDAUTO_ENABLED and Enable_application_google_Automotive_link"),
    ("TRAILERING_FULL", f"{HS}TRAILERING_ENABLED and TraileringAppType == 2"),
    ("TRAILERING_LITE", f"{HS}TRAILERING_ENABLED and TraileringAppType == 1"),
    ("BAIDU_CARLIFE", f"{HS}BAIDUCARLIFE_ENABLED"), ("APP_SHOP", f"{HS}APPSHOP_ENABLED"),
    ("ENERGY", f"{HS}ENERGY_ENABLED and ENERGY_APPLICATION"), ("MY_MODE", "MyModeEnable"), ("ONSTAR", f"{HS}ONSTAR_ENABLED"),
    ("PDR_LVM", f"{HS}PDRLVM_ENABLED and (LVM_1 == 3 or LVM_2 == 3 or LVM_3 == 3)"), ("RSI", f"{HS}VIDEO_ENABLED"),
    ("AIR_QUALITY", f"{HS}AIRQUALITY_ENABLED"), ("CLIMATE", f"{HS}CLIMATE_ENABLED and Climate_Application_Available"),
    ("REAR_CLIMATE", f"{HS}REARCLIMATE_ENABLED and Rear_Climate_Application_Available"),
    ("INTERIOR_LIGHTING", f"{HS}INTERIORLIGHTING_ENABLED and AmbientLightingEnable"),
    ("VIDEO_RECORDER_LVM", f"{HS}VIDEORECORDERLVM_ENABLED and RVS_PRESENT_STATUS == 2"),
    ("GM_CAMERA", f"{HS}CAMERA_ENABLED and (RVS_PRESENT_STATUS == 2 or (RVS_PRESENT_STATUS == 1 and RVS_FEATURE_AVAIL_SMART_TOW == 1))"),
    ("AIR_DOWN_MODE", f"{HS}AIRDOWNMODE_ENABLED"), ("CAMERA", f"{HS}CAMERALVM_ENABLED"), ("CONTROLS", f"{HS}CONTROLS_ENABLED"),
    ("DRIVE_MODE", f"{HS}DRIVEMODE_ENABLED"), ("GOOGLE_ASSISTANT", f"{HS}GOOGLEASSISTANT_ENABLED"),
    ("GOOGLE_MAPS", f"{HS}GOOGLEMAPS_ENABLED and ENABLE_APPLICATION_NAVIGATION"), ("OFF_ROAD", f"{HS}OFFROAD_ENABLED"),
    ("GOOGLE_PLAYSTORE", f"{HS}PLAYSTORE_ENABLED"), ("SUPER_CRUISE", f"{HS}SUPERCRUISE_ENABLED"), ("SVR", f"{HS}SVR_ENABLED"),
    ("TEEN_DRIVER", f"{HS}TEENDRIVER_ENABLED"), ("THEMES", f"{HS}THEMES_ENABLED"), ("TIPS", f"{HS}TIPS_ENABLED"),
    ("APA", f"{HS}APA_ENABLED"), ("PERFORMANCEAPP", f"{HS}PERFORMANCEAPP_ENABLED"),
    ("ALEXA", f"{HS}ALEXA_ENABLED and COUNTRY_CODE in (49, 5, 31)"),
]
for _type, _expr in ICONS:
    RULES.append(rule(
        f"icon.{_type.lower()}", f"Launcher icon: {_type}", _expr,
        f"Framework LauncherIconManager builds the {_type} icon as visible with a default home-screen and app-tray order",
        "home screen / app tray",
        [("info3", ICON, f"CalId.{_expr.split()[0]}, false)"), ("info3", "@gm/content/LauncherIconManager.java",
                                                               "LauncherIconCalibrationHelper.isApplicationVisible(this.mCalibration, type)")],
        note="Values come through CalibrationShadow, a per-app cache file (cache dir, calshadow/LauncherIcon) refreshed when the "
             "calibration update indicator changes. Visible does not prove the app is installed. GMHomeScreen carries its own "
             "copy of this switch (ui.home_* rules); its hotspot case adds APPLICATION_HOMESCREEN_ONSTAR_ENABLED."))

# Settings pass. Three packages draw the Settings UI: CarSettings (com.android.car.settings, the home page and its AOSP
# screens), GMSettings (com.gm.hmi.settings, GM screens opened by intent action) and GMConnections (com.gm.hmi.connection,
# the Connections screens). GMSettings and GMConnections share com.gm.settings.* (repositories, use cases, CalItem).
# Their obfuscated request handlers are named by the "compiled from" tags jadx kept (README, Settings section).
SET, CAR, CRIT = "GMSettings", "CarSettings", "CriticalWKSApp"
SET_RL = "@Z/c.java"  # ResponseListener.kt of GMSettings
TDR = "settings/repositories/TimeAndDateRepository.java"
TDB = "@V/C0221o1.java"  # SettingstimedateactivitybindingImpl
SIG = "settings/data/vehicle/signals/"
SND = "settings/data/system/signals/sounds/"
SUP = (SET, SIG + "SignalsGroupSupervisor.java", "if (value.isAvailable()) {")
ALM = "@com/android/car/settings/applications/ApplicationListItemManager.java"
XSL = (CAR, "@com/android/car/settings/common/ExtraSettingsLoader.java",
       "this.mPm.queryIntentActivitiesAsUser(intent, 128, ActivityManager.getCurrentUser())")
TOD = "server/timeofday/"
GPS_OK = "((BACK_OFFICE_SERVER_ENABLED and GPS_DATA_SOURCE == 2) or (not BACK_OFFICE_SERVER_ENABLED and GPS_DATA_SOURCE == 1))"
CORVETTE = "(GMBrand == 3 and GMModel == 10)"
_APPS_NOTE = ("isLoaded() drops the entry from the list handed to the Apps screens (All apps, recently opened). Not a statement "
              "about whether the package is installed or enabled.")

RULES += [
    # CarSettings
    rule("settings.car.quick_startup", "Settings > System: quick start-up row",
         "SUSPEND_TO_RAM_ENABLE",
         "QuickStartupPreferenceController.getAvailabilityStatus() returns AVAILABLE (0); false: UNSUPPORTED_ON_DEVICE (2), "
         "the row is not shown", "open Settings > System",
         [(CAR, "@com/android/car/settings/system/QuickStartupPreferenceController.java", "return isSuspendRamEnable ? 0 : 2;")]),
    rule("settings.car.apps_alexa", "Settings > Apps: Alexa entry",
         "APPLICATION_HOMESCREEN_ALEXA_ENABLED and COUNTRY_CODE in (49, 5, 31)",
         "com.gm.info3.alexa is kept in the application list", "open Settings > Apps > all apps",
         [(CAR, ALM, "return isAlexaEnable && (countryCode == 49 || countryCode == 5 || countryCode == 31);")], note=_APPS_NOTE),
    rule("settings.car.apps_offroad", "Settings > Apps: Off-road entry",
         f"not {CORVETTE} or (APPLICATION_HOMESCREEN_OFFROAD_ENABLED and OFF_ROAD_APP_FEATURE_ENABLE)",
         "com.gm.offroad is kept in the application list (always, unless brand 3 and model 10)", "open Settings > Apps > all apps",
         [(CAR, ALM, "CalItem.OFF_ROAD_APP_FEATURE_ENABLE"), (CAR, ALM, "return brandEnum == 3 && modeEnum == 10;")], note=_APPS_NOTE),
    rule("settings.car.apps_energy", "Settings > Apps: Energy entry",
         f"not {CORVETTE} or (APPLICATION_HOMESCREEN_ENERGY_ENABLED and ENERGY_APPLICATION)",
         "com.gm.hmi.energy is kept in the application list (always, unless brand 3 and model 10)", "open Settings > Apps > all apps",
         [(CAR, ALM, "CalItem.ENERGY_APPLICATION")], note=_APPS_NOTE),
    rule("settings.car.apps_trailering", "Settings > Apps: Trailering entry",
         f"not {CORVETTE} or APPLICATION_HOMESCREEN_TRAILERING_ENABLED",
         "com.gm.hmi.trailer is kept in the application list (always, unless brand 3 and model 10)", "open Settings > Apps > all apps",
         [(CAR, ALM, "CalItem.APPLICATION_HOMESCREEN_TRAILERING_ENABLED")], note=_APPS_NOTE),
    rule("settings.car.apps_gmc_studio", "Settings > Apps: com.gm.fse entry",
         f"not {CORVETTE} or APPLICATION_HOMESCREEN_VIDEO_ENABLED",
         "com.gm.fse is kept in the application list (always, unless brand 3 and model 10)", "open Settings > Apps > all apps",
         [(CAR, ALM, "CalItem.APPLICATION_HOMESCREEN_VIDEO_ENABLED")], note=_APPS_NOTE),
    # GMSettings start-up enables or disables two activities in the package manager; CarSettings lists them by category.
    rule("settings.car.tty_row", "Settings > System: TTY row",
         "TTYSetting",
         "GMSettings start-up enables com.gm.hmi.onstarui/.ui.activities.TtySettingOverviewActivity in the package manager "
         "(setComponentEnabledSetting); false: disables it. CarSettings fills the System screen's TTY group from enabled "
         "activities with category com.gm.onstarui.app.tty.mode, so the row follows the component state",
         "adb shell pm dump com.gm.hmi.onstarui | grep -A3 disabledComponents; open Settings > System",
         [(SET, APPS, "enableComponent(ONSTAR_HMI_PKG_NAME, TTY_MODE_ACTIVITY_NAME);"),
          (SET, "settings/core/ExecConfig.java", "new SetupCalibrationBasedSettingsUseCase().execute(null);"), XSL],
         note="A package-manager state, persisted under /data: it outlives the calibration change until GMSettings starts again "
              "(not for the Connections client). That a disabled activity is not returned by the query is platform behaviour, "
              "not read here."),
    rule("settings.car.device_registration_row", "Settings > System > About: device registration row",
         "BACK_OFFICE_SERVER_ENABLED",
         "GMSettings start-up enables com.gm.hmi.settings/.ui.activities.SettingsAboutDeviceRegistrationActivity in the package "
         "manager; false: disables it. CarSettings fills the About screen's group from enabled activities with category "
         "com.gm.hmi.settings.device.registration",
         "adb shell pm dump com.gm.hmi.settings | grep -A3 disabledComponents; open Settings > System > About",
         [(SET, APPS, "enableComponent(SETTINGS_HMI_PKG_NAME, DEVICE_REGISTRATION_ACTIVITY_NAME);"), XSL],
         note="Same mechanism and caveats as the TTY row."),
    # GMSettings: date and time
    rule("settings.time.auto_datetime_row", "Settings > Date and time: Automatic Date / Time row",
         GPS_OK,
         "isAutomaticTimeAndDateAvailable() true: the Automatic Date / Time switch row is VISIBLE; false: the row is GONE and "
         "GMSettings start-up writes Settings.Global auto_time = 0",
         "open Settings > Date and time; adb shell settings get global auto_time",
         [(SET, TDR, "return isTCPGPSAvailable() || isInternalGPSAvailable();"), (SET, TDR, "setAutomaticTimeAndDateStatus(false);"),
          (SET, SET_RL, "ObservableBoolean observableBooleanL2 = this.f3564f.l2();"), (SET, TDB, "observableBooleanL3 = iVar2.l2();")],
         note="Visibility read in smali (V/o1): available -> 0, else 8, applied to the row's switch, two labels and dividers. "
              "FM_RDS_Clocktime_enabled is not a term. Manual time and date entry is ignored while auto_time is 1 and this is true. "
              "The write happens in ExecConfig.configHmiClient (SetupAutomaticTimeAndDateUseCase) for every HMI client except "
              "GMConnections. auto_time = 0 does not stop the time-of-day service applying trusted time: time.trusted_clock_sync."),
    rule("settings.time.auto_timezone_row", "Settings > Date and time: Automatic Time Zone row",
         f"{GPS_OK} and ((BACK_OFFICE_SERVER_ENABLED and onstar_subscription_valid and APPLICATION_HOMESCREEN_ONSTAR_ENABLED) "
         "or FM_RDS_Clocktime_enabled)",
         "isAutomaticTimeZoneAvailable() true: the Automatic Time Zone switch row is VISIBLE; false: GONE",
         "open Settings > Date and time",
         [(SET, TDR, "return (isTCPGPSAvailable() || isInternalGPSAvailable()) && (isActiveOnStarSubscription() || isRDSAvailable());"),
          (SET, SET_RL, "ObservableBoolean observableBooleanB0 = this.f3564f.B0();"), (SET, TDB, "observableBooleanB0 = iVar2.B0();")],
         note="onstar_subscription_valid is the runtime answer of OnStarRepository.isOnStarSubscriptionValid(). The setting is "
              "a UI gate only; the time-zone logic is time.rds_local_source."),
    # CriticalWKSApp: the service that sets the clock and the time zone
    rule("time.rds_local_source", "Time-of-day service: RDS as local-time source",
         "FM_RDS_Clocktime_enabled",
         "TimeofDayService may take the tuner's RDS clock time as its LOCAL time source when the vehicle's cellular local time "
         "is not available. Inside the service, local time is used only to derive a time zone (rounded half-hour difference "
         "to trusted time, or to the remote real-time clock when there is none, then AlarmManager.setTimeZone) while "
         "auto_time_zone is 1. It never sets the system clock",
         "log 'TimeOfDay:GMTuner: computed Local Time' / 'VehicleTime: Setting time zone to'",
         [(CRIT, TOD + "calibrations/TimeOfDayCalibrations.java", 'getBoolean("FM_RDS_Clocktime_enabled", false)'),
          (CRIT, TOD + "sources/GMTunerTimeSource.java", "return calibrations.isRdsSourceAvailable();"),
          (CRIT, TOD + "sources/GMTunerTimeSource.java", 'extras.getString("com.gm.rds_time")'),
          (CRIT, TOD + "LocalTimeHandler.java", "this.localTimeSource = this.tunerTimeSource;"),
          (CRIT, TOD + "TimeofDayService.java", "this.mAlarmManager.setTimeZone(zones.get(0));"),
          ("GMTunerService", "@k/m.java", 'arrayList.add("com.gm.rds_time");')],
         note="RDS time arrives as a JSON string in the media-session extras of com.gm.gmaudio.tuner, which reads vendor "
              "parameter com.gm.rds_time from the broadcast-radio HAL (vendor.harman.tuner-service; strings and symbols name "
              "RdsClockTime, sendRdsTime, updateRdsTime; not decompiled). Accepted only when two successive values lie "
              "within 180 s and either bit <country code> of PI_CODE_CONFIGURATION is set or it is within "
              "RDS_CLOCK_TIME_MAX_DIFF minutes of the system's local clock. Image and bench value: 0."),
    rule("time.trusted_clock_sync", "Time-of-day service: trusted time applied to the system clock",
         "GPS_DATA_SOURCE in (1, 2)",
         "TimeofDayService starts trusted-time updates and, once a value is verified, sets the remote real-time clock and the "
         "system clock from it in BOTH auto_time modes. Settings.Global auto_time (read at service start and on every change) "
         "selects only the offset: 1 = the clock is set to trusted time and persist.sys.clockOffset is reset to 0; 0 = the "
         "clock is set to trusted time minus persist.sys.clockOffset. false: no trusted-time updates; the clock comes from the "
         "remote real-time clock (else 2020-01-01) under the same offset rule",
         "log 'VehicleTime: Trusted time verified and locked' / 'VehicleTime: Setting time to'; adb shell getprop "
         "persist.sys.clockOffset; adb shell settings get global auto_time",
         [(CRIT, TOD + "TimeofDayService.java", 'return Settings.Global.getInt(this.mContext.getContentResolver(), "auto_time", 0);'),
          (CRIT, TOD + "TimeofDayService.java", 'this.TIME_MODE_URI = Settings.Global.getUriFor("auto_time");'),
          (CRIT, TOD + "TimeofDayService.java", "localTimeMillis -= offset;"),
          (CRIT, TOD + "TimeofDayService.java", "} else if (this.mTimeUpdateMode == 1) {"),
          (CRIT, TOD + "TimeofDayService.java", 'PROP_CLOCK_OFFSET = "persist.sys.clockOffset";'),
          (CRIT, TOD + "TimeofDayService.java", "this.mAlarmManager.setRepeating(3, start, 1800000L, pendingDriftIntent);"),
          (CRIT, TOD + "SystemTimeHandler.java", "VehicleTime: Trusted time source is not available"),
          (CRIT, TOD + "calibrations/TimeOfDayCalibrations.java", "timeSource = TrustedTimeSourceType.NONE;")],
         note="No branch on mTimeUpdateMode skips a clock write. updateSystemClock() subtracts the offset in manual mode and "
              "sets the clock when it is more than 1.5 s from the target; syncClocks() (first verified trusted time) and "
              "calculateDrift() call it in both modes. In manual mode the offset is recomputed at every TIME_SET / "
              "DATE_CHANGED as (trusted time, or the remote real-time clock when there is none) minus the system clock, so a "
              "manual entry survives later corrections; an offset taken against a wrong remote clock is kept when trusted time "
              "arrives. Switching auto_time to 1 sets the clock to trusted time and zeroes the offset; a time set from "
              "elsewhere in automatic mode is undone by the next drift check. Drift monitor: a repeating alarm every "
              "30 minutes (1800000 ms; started at boot-completed and resume, stopped on suspend) runs calculateDrift(), which "
              "re-sets both clocks when the remote clock is more than 1.5 s or the system clock more than 0.5 s from the "
              "expected value. That is a re-check period, not a limit on the size of a correction: this service has no "
              "upper bound on how far a trusted time may move the clock. It is unrelated to RDS_CLOCK_TIME_MAX_DIFF (minutes, "
              "RDS local time only) and to the half-hour rounding of the time-zone offset (time.rds_local_source). A trusted "
              "value is accepted after five further values each within 3 s of the one before, or at once when the first "
              "value is within 3 s of the remote clock. BACK_OFFICE_SERVER_ENABLED is not read by this service. Whether a location provider delivers "
              "fixes for value 1 on this hardware is unknown."),
    # GMSettings: sounds, privacy, vehicle
    rule("settings.sounds.audible_touch_row", "Settings > Sounds: audible touch feedback row",
         "ENABLE_MENU_AUDIO_TOUCH_FEEDBACK",
         "The audible touch feedback row is listed; false: left out. When true GMSettings also copies the user's "
         "sound_effects_enabled value to user 0",
         "open Settings > Sounds",
         [(SET, SND + "AudibleTouchFeedback.java", "getBooleanValue(CalItem.ENABLE_MENU_AUDIO_TOUCH_FEEDBACK)"),
          (SET, "@Q/C0162h.java", "if (soundsBundle.isAvailable()) {")]),
    rule("settings.sounds.audio_cue_rows", "Settings > Sounds: start-up sound rows",
         "AUDIO_CUE_ACUE_RUN_ENABLED or AUDIO_CUE_WELCOME_ENABLE or AUDIO_CUE_ACUE_STOP_ENABLED",
         "The audio cue on/off row and the audio cue volume row are listed; false: both left out",
         "open Settings > Sounds",
         [(SET, SND + "SoundsCalibrationImpl.java", "return isAudioCueRunWelcomeEnabled() || isAudioCueStopEnabled();"),
          (SET, SND + "StartupSounds.java", "return isAnyAudioCueEnabled();"), (SET, "@Q/C0162h.java", "if (soundsBundle.isAvailable()) {")],
         note="The maximum start-up volume row is always listed."),
    rule("settings.sounds.audio_cue_shutdown_wording", "Settings > Sounds: start-up/shut-down wording",
         "AUDIO_CUE_ACUE_STOP_ENABLED",
         "The two audio cue rows use the start-up-and-shut-down titles and descriptions; false: the start-up-only ones",
         "open Settings > Sounds",
         [(SET, SND + "StartupSounds.java", "return isAudioCueStopEnabled() ? R$string.settings_audio_cues_shutdown : R$string.settings_audio_cues;")]),
    rule("settings.location.onstar_row", "Settings > Privacy > Location: Location Services for OnStar row",
         "APPLICATION_HOMESCREEN_ONSTAR_ENABLED and COUNTRY_CODE != 92",
         "The Location Services for OnStar row is listed; false: left out",
         "open Settings > Privacy > Location",
         [(SET, "settings/repositories/PermissionsRepository.java", "return onStarAvailability && z2;"),
          (SET, SET_RL, "Location.LOCATION_SERVICES_FOR_ONSTAR.u(locationServicesBundle.a());"),
          (SET, "hmi/settings/ui/activities/SettingsSystemLocationServicesActivity.java", 'getEventHandler().h("evg_LocationServicesOnStarAvailable");')]),
    rule("settings.account.network_service", "Settings: GM account sign-in network check",
         "DataServicesEnable and data_services_setting_on",
         "ConnectivityStatus.getNetworkStatus() goes on to test the connection; false: it returns NETWORK_SERVICE_DISABLED "
         "to the account sign-in handlers before looking at any network",
         "log tag ConnectivityStatus",
         [(SET, "settings/data/auth/ConnectivityStatus.java", "return NetworkStatus.NETWORK_SERVICE_DISABLED;"),
          (SET, "@Q/F.java", "CheckNetworkStatusUseCase")],
         note="data_services_setting_on is Settings.Global data_services_enabled == 1. The screen shown for the disabled status "
              "was not resolved."),
    rule("settings.vehicle.valet_mode", "Settings > Vehicle: valet mode category",
         "ValetMaskMenu",
         "ValetModeSignal.isAvailable() true: the valet mode category is in the list of available vehicle settings; false: left out",
         "open Settings > Vehicle",
         [(SET, SIG + "valetmode/ValetModeSignal.java", "getBooleanValue(CalItem.VALET_MASK_MENU)"),
          (SET, SIG + "SignalsManager.java", "if (signalsGroupSupervisor.hasAvailableSignals()) {")],
         note="Traced to the list returned by SignalsManager.getAvailableVehicleSignals(); the row view was not inspected."),
    rule("settings.vehicle.engine_lighting", "Settings > Vehicle > Lighting: engine lighting row",
         "product_is_my23_csm and AmbientLightingEnable and ambient_aux1_signal_available",
         "EngineLightingSignal.isAvailable() true: the engine lighting sub-row is listed; false: left out",
         "log 'return isAvailable() false by cal.'",
         [(SET, SIG + "lightning/EngineLightingSignal.java", "getBooleanValue(CalItem.AMBIENT_LIGHTING_ENABLE)"), SUP],
         note="product_is_my23_csm: the product name contains the MY23 CSM marker. ambient_aux1_signal_available: either "
              "auxiliary ambient colour or animation vehicle signal is available."),
    rule("settings.vehicle.rear_camera_park_assist", "Settings > Vehicle > Collision/detection: rear camera park assist symbols row",
         "RVS_PRESENT_STATUS != 0 and (park_assist_property_available if RVS_PRESENT_STATUS == 2 else RVS_FEATURE_AVAIL_UPA_SYMBOLS)",
         "RearCameraParkAssistSignal.isAvailable() true: the row is listed; false: left out. With status 2 the option is the "
         "vehicle property, otherwise an on/off stored in Settings.Global rear_camera_park_assist_status",
         "open Settings > Vehicle",
         [(SET, SIG + "collisionanddetection/RearCameraParkAssistSignal.java", "getBooleanValue(CalItem.RVS_FEATURE_AVAIL_UPA_SYMBOLS)"), SUP],
         note="Status values above 2 keep the camera type of the previous call (initially the status-1 type)."),
    rule("settings.vehicle.drive_mode_overlay", "Settings > Vehicle > Drive mode: selection overlay row",
         "GMBrand == 3",
         "DriveModeSelectionOverlaySignal.isAvailable() true: the selection overlay on/off row is listed; false: left out",
         "open Settings > Vehicle",
         [(SET, SIG + "drivemodecustomization/DriveModeSelectionOverlaySignal.java", "return this.mCalibrationRequest.getEnumeration(CalItem.GMBrand) == 3;"), SUP],
         note="The stored value is Settings.Global drive_mode_selection_overlay; its default is on only for brand 3 with model 10."),
    # GMConnections
    rule("settings.connections.vehicle_to_phone_row", "Settings > Connections: vehicle-to-phone sharing row",
         "VCA_ACCESS_VEHICLE_DATA",
         "The Connections screen lists the device remote access row; false: left out",
         "open Settings > Connections",
         [(SET, "settings/repositories/DeviceRemoteAccessRepository.java", "getBooleanValue(CalItem.VCA_ACCESS_VEHICLE_DATA)"),
          (CONN, CONN_RL, "systemMenuItemStatus.getIsRemoteDevStatusAvailable()")]),
    rule("settings.hotspot.share_data_row", "Settings > Connections > Wi-Fi hotspot: Share Hotspot Data row",
         "APPLICATION_HOMESCREEN_ONSTAR_ENABLED or BACK_OFFICE_SERVER_ENABLED",
         "The Share Hotspot Data row is VISIBLE; false: GONE", "open Settings > Connections > Wi-Fi hotspot",
         [(CONN, HOT, "return new GetOnStarAvailabilityUseCase().executeSync().booleanValue() || isBackOfficeServerEnabled();"),
          (CONN, "@p000a0/C0192t.java", "i7 = mIsHotspotDataSharedAvailable ? 0 : 8;")]),
    rule("settings.hotspot.password_reveal", "Settings > Connections > Wi-Fi hotspot: password show/hide control",
         "COUNTRY_CODE == 4",
         "The hotspot password is hidden by default and the show/hide control is VISIBLE; false: the control is GONE",
         "open Settings > Connections > Wi-Fi hotspot",
         [(CONN, HOT, "return enumeration == 4;"), (CONN, "@p000a0/C0192t.java", "mIsPasswordHidden = wifiHotspotInfoK != null ? wifiHotspotInfoK.getMIsPasswordHidden() : false;")]),
    rule("settings.phone.carplay_toggle_row", "Settings > Connections > Phones > phone: Apple CarPlay on/off row",
         "Apple_CarPlay_enableWireless",
         "For a device whose projection type is CarPlay the phone-details list adds the Apple CarPlay on/off row; false: no row",
         "open a paired phone in Settings > Connections > Phones",
         [(CONN, BTR, "getBooleanValue(CalItem.Apple_CarPlay_enableWireless)"),
          (CONN, CONN_RL, "if (bTDeviceInfoT.getIsProjectionToggleOptionAvailable() == 1) {")]),
    rule("settings.phone.androidauto_toggle_row", "Settings > Connections > Phones > phone: Android Auto on/off row",
         "AndroidAuto_enableWireless",
         "For a device whose projection type is Android Auto the phone-details list adds the Android Auto on/off row; false: no row",
         "open a paired phone in Settings > Connections > Phones",
         [(CONN, BTR, "getBooleanValue(CalItem.AndroidAuto_enableWireless)"),
          (CONN, CONN_RL, "if (bTDeviceInfoT.getIsProjectionToggleOptionAvailable() == 1) {")]),
    # Bench pass: tuner audio-settings list (GMAudio) and the trailering back-office client (GMTrailer)
    rule("tuner.fm_settings_radio_text_row", "Audio settings list, FM source: RDS radio text on/off row",
         "RDS_Radio_Menu_Item_On",
         "onAddAudioSettingsList() adds the radio text on/off row (label audio_3_0_list_radioText_csm, event eSettingsRDSOnOff) "
         "to the FM list; false: the row is not added",
         "tune FM, open the audio settings list; log 'RDS Option show cal value -->'",
         [AUD_RL_FM_RDS, AUD_ALIAS_RDS, AUD_CLIENT, AUD_SERVER],
         note=_AUD_NOTE),
    rule("tuner.fm_settings_traffic_program_row", "Audio settings list, FM source: traffic program on/off row",
         "FM_RDS_TP_enabled",
         "The FM list gets the traffic program on/off row (audio_3_0_TP_csm, eSetTrafficProgram), and the DAB announcement "
         "category list gets a Traffic entry; false: neither is added",
         "tune FM, open the audio settings list",
         [(AUD, AUD_RL, 'if (audioCalibrationManager.b("traffic_program_enabled")) {'),
          (AUD, "@p003c/a.java", 'map.put("traffic_program_enabled", EnumCalibrations.RDS_TP_ENABLED);'), AUD_CLIENT, AUD_SERVER],
         note=_AUD_NOTE + " Traffic_Program_Menu_Item_On is defined as a constant in the same package but no code uses it: "
              "this row follows FM_RDS_TP_enabled."),
    rule("tuner.settings_region_rows", "Audio settings list, FM and DAB sources: RDS categories and region rows",
         "REGIONS in (2, 4)",
         "For region Europe (2) or Middle East (4) the FM list gets the RDS categories row (eSettingsRDSCategoryOnOff) and the "
         "region row (eSettingsRegionOnOff), and the DAB list gets the region row; any other region: not added",
         "tune FM, open the audio settings list; log 'isRegionEUOrME REGION value in Cal DataBase is'",
         [(AUD, AUD_RL, "if (audioCalibrationManager.h()) {"),
          (AUD, "@p003c/a.java", "iD == LANGUAGEANDREGIONALIZATIONGLOBALA_ENUM.REGIONS.EUROPE.ordinal() || iD == LANGUAGEANDREGIONALIZATIONGLOBALA_ENUM.REGIONS.MIDDLE_EAST.ordinal()"),
          AUD_CLIENT, AUD_SERVER],
         note=_AUD_NOTE + " Region_Setting_Menu_Item_On and RDS_PTY_Menu_Item_On are not referenced by any code on the image: "
              "these rows follow REGIONS."),
    rule("tuner.settings_fade_balance_row", "Audio settings list, every source: fade/balance row",
         "ENABLE_FADE",
         "The list gets the fade/balance row (eFadeOrBalanceScreen); false: not added",
         "open the audio settings list; log 'FadeBalance value -->'",
         [(AUD, AUD_RL, 'if (aVar.b("tone_settings_fade_enabled")) {'),
          (AUD, "@p003c/a.java", 'map.put("tone_settings_fade_enabled", EnumCalibrations.TONE_SETTINGS_FADE_ENABLED);'), AUD_CLIENT, AUD_SERVER],
         note=_AUD_NOTE),
    rule("trailer.backoffice_sync", "Trailering app: back-office (network) synchronisation",
         "TraileringAppType == 2 and trailer_backoffice_allowed",
         "The full trailering app creates its network connection manager. Once the network is up and the OnStar account "
         "reports the TRAILER entitlement, it runs a profile sync and repeats it every 30 minutes: HTTPS requests to "
         "https://<ACCOUNT_AUTHENTICATOR_SERVER_NAME>:<SECURITY_EVENT_LOGGING_SERVER_HOST_PORT>/api/v2/trailering/... with a "
         "bearer token; request paths carry the VIN and trailer ids, bodies carry trailer profiles, checklists, maintenance "
         "reminders, tyre-pressure sensor data and metrics (distance delta, fuel economy, transmission temperature). "
         "App type 1 (lite) or 0: the manager is never created",
         "logcat 'Backoffice URL  =', 'Trailering Entitlement is AVAILABLE, starting BO', 'Running 30 min Sync'; packet capture",
         [("GMTrailer", "trailercore/data/TrailerVehicleService.java", "trailerNetworkConnectionManager.initialize();"),
          ("GMTrailer", "trailercore/data/TrailerVehicleService.java", "if (2 != i) {"),
          ("GMTrailer", TRL_NET, 'BOUtils.API_URL += ":" + calibrationEvent.calTrailerBOPort + "/api/v2";'),
          ("GMTrailer", TRL_NET, 'int entitlementActivationState = onstarAccountInfo.getEntitlementActivationState("TRAILER");'),
          ("GMTrailer", TRL_NET, "startPeriodicBoSyncing(getSyncPeriodInMilliseconds(1800000));"),
          ("GMTrailer", "trailercore/data/backoffice/BOServiceGenerator.java", "setEndpoint(BOUtils.API_URL).setLogLevel(RestAdapter.LogLevel.FULL)"),
          ("GMTrailer", "trailercore/data/backoffice/ClientInterface/IBOProfileClient.java", '@POST("/trailering/trailers/{trailerId}/vehicles/{vin}/metrics")')],
         note="trailer_backoffice_allowed: demo mode off, an active network, and an OnStar account that is active with TRAILER "
              "entitlement state 1 (or 2 with type Data); without the entitlement no request adapter is built. System property "
              "persist.gm.bo.trailer.sync (minutes) replaces the 30-minute period. The client is built with Retrofit log level "
              "FULL, whose Android default writes requests and responses to logcat tag Retrofit. Read in code, nothing run: "
              "the link from the network check to the VIN event and the individual request builders were not followed line by "
              "line. Despite its name, SECURITY_EVENT_LOGGING_SERVER_HOST_PORT has no other reader on the image."),
]

# Settings whose value is passed through rather than gating a feature.
VALUE_EFFECTS = {
    "Apple_CarPlay_softKeyboard": ("CarPlay limited-UI element list includes soft keyboard when true", DW, CPC),
    "Apple_CarPlay_softKeypad": ("CarPlay limited-UI element list includes soft phone keypad when true", DW, CPC),
    "Apple_CarPlay_nonMusicLists": ("CarPlay limited-UI element list includes non-music lists when true", DW, CPC),
    "Apple_CarPlay_MusicLists": ("CarPlay limited-UI element list includes music lists when true", DW, CPC),
    "Apple_CarPlay_touchFidelity": ("Touch fidelity enum: 0 -> 4, 1 -> 8; read for COUNTRY_CODE 49, 5, 31, 22 (99 is forced to 4)", DW, CPC),
    "Android_Auto_no_video_playback": ("Adds NO_VIDEO to the Android Auto driving-status mask", DW, "@com/google/android/projection/sink/sensors/GearManager.java"),
    "Android_Auto_no_text_input": ("Adds NO_KEYBOARD_INPUT to the mask", DW, "@com/google/android/projection/sink/sensors/GearManager.java"),
    "Android_Auto_no_setup_config": ("Adds NO_CONFIG to the mask", DW, "@com/google/android/projection/sink/sensors/GearManager.java"),
    "Android_Auto_limit_disp_msg_length": ("Adds LIMIT_MESSAGE_LEN to the mask", DW, "@com/google/android/projection/sink/sensors/GearManager.java"),
    "Android_Auto_no_voice_input": ("Adds NO_VOICE_INPUT to the mask", DW, "@com/google/android/projection/sink/sensors/GearManager.java"),
    "Android_Auto_VEC_Whitelist": ("Android Auto vendor-extension package whitelist (built-in list if null)", DW, "@com/google/android/projection/sink/extension/GALVendorExtension.java"),
    "BluetoothModuleDeviceName": ("Read as the Bluetooth/host name by connection, CarPlay model name, Android Auto and WLAN code", DW, WLAN),
    "BTConnectionRequestTimer": ("Settings returns it as the Bluetooth connection-request timeout (via CalItem)", "GMSettings", "settings/data/calibration/CalItem.java"),
    "BluetoothDevicePairLimit": ("Paired-device limit in the connection manager", DW, DIM),
    # Settings pass
    "GPS_DATA_SOURCE": ("Time-of-day service trusted (UTC) time source: 0 none (clock from the remote real-time clock, else "
                        "2020-01-01); 1 location fix time through GMLocationClient; 2 vehicle property UTC. Apart from the remote "
                        "real-time clock and manual entry, nothing else sets the system clock in this service. Also a term "
                        "of the two Settings date/time rows",
                        CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "PI_CODE_CONFIGURATION": ("Bit mask over the RDS country code: a set bit accepts RDS clock time from that country without "
                              "the RDS_CLOCK_TIME_MAX_DIFF check", CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "RDS_CLOCK_TIME_MAX_DIFF": ("Minutes: RDS clock time further than this from the system's local clock is rejected unless "
                                "PI_CODE_CONFIGURATION accepts the country", CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "TZDSTAdjust_LL": ("Seconds: lower bound of a time-zone step the time-of-day service validates over repeated polls",
                       CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "TZDSTAdjust_UL": ("Seconds: upper bound of that step", CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "TZDSTAckWaitTime": ("Number of consecutive one-second polls a time-zone step inside the bounds must persist before it is applied",
                         CRIT, TOD + "calibrations/TimeOfDayCalibrations.java"),
    "MinChimeVolumeStep": ("Lower end of the chime volume slider in Settings (via CalItem)", SET, "settings/data/calibration/CalItem.java"),
    "MaxChimeVolumeStep": ("Upper end of the chime volume slider in Settings (via CalItem)", SET, "settings/data/calibration/CalItem.java"),
    "DefaultMaximumStartupVolume": ("Settings shows it as the maximum start-up volume until Settings.Global maximum_startup_volume "
                                    "is written, and as the audio cue volume if the audio manager call fails (via CalItem)",
                                    SET, "settings/data/calibration/CalItem.java"),
    "GIS887_VehicleTransmissionType": ("Value 1 selects the first of two description texts of the automatic door lock setting "
                                       "(via CalItem)", SET, "settings/data/calibration/CalItem.java"),
    # Bench pass
    "SECURITY_EVENT_LOGGING_SERVER_HOST_PORT": (
        "Port of the trailering app's back-office URL (https://<ACCOUNT_AUTHENTICATOR_SERVER_NAME>:<port>/api/v2); 0 leaves "
        "the URL without port and path. This is its only reader on the image: no security-event logging code uses it",
        "GMTrailer", "trailercore/managers/TrailerCalibrationManager.java"),
    "ACCOUNT_AUTHENTICATOR_SERVER_NAME": (
        "Host of the trailering app's back-office URL; empty leaves the URL unset. Also read by GMAuthTokenService "
        "(effect there not traced)", "GMTrailer", "trailercore/managers/TrailerCalibrationManager.java"),
    "GM_Account_Sign_In_Method": ("Value 1: account sign-in by e-mail and phone number; any other value: e-mail only (via CalItem)",
                                  SET, "settings/data/calibration/CalItem.java"),
}

# Methods that forward a String parameter straight to a calibration getter, so a call with a calibration name is a read.
# Key: (app, file under sources/). Value: (method names, text that must be present in that file).
# com/gm/rsicc/RSIApplication.T is deliberately absent: it reads the calibration for two names only and otherwise
# returns an app preference.
WRAPPERS = {
    ("GMHomeScreen", "T/C0129w.java"): (["g", "i", "k"], "((CalibrationManager) this.f1760a).getBoolean(str, false)"),
    ("GMHvac", "p023y/c.java"): (["a", "b", "c"], "Read calibration from CalibrationManager: key=%s"),
    ("GMSeatStatusPane", "o/b.java"): (["a", "b", "c", "d"], "Read calibration from SeatCalibrationManager: key=%s"),
    ("GMSystemUI", "com/gm/cardview/utils/a.java"): (["e", "f"], "return f40176a.getBoolean(str, false);"),
    ("GMTCPS", "t2/a.java"): (["a", "b"], "this.f6890a.getEnumeration(str, i3)"),
    ("GMVAC", "com/gm/android/vehicle/support/navigation/NavigationHelper.java"): (["readBooleanCal"], "this.calibrationManager.getBoolean(str)"),
    ("GMAlexa", "com/gm/android/vehicle/support/navigation/NavigationHelper.java"): (["readBooleanCal"], "this.calibrationManager.getBoolean(str)"),
    ("GMRSISrc", "com/gm/rsicc/RSIApplication.java"): (["K", "X"], "boolean z = L().getBoolean(str, d.i(str));"),
}

# Enum catalogs: each entry binds an identifier to one calibration name, and the listed methods forward the entry's name to
# a typed CalibrationManager getter. Key: (app, file under sources/). Value: (enum class, getter methods, text that must be
# present in the file holding the getters, that file). A call `getter(Enum.X)` is then a read-via-constant site.
ENUM_KEYS = {
    ("GMSettings", "com/gm/settings/data/calibration/CalItem.java"): (
        "CalItem", ["getBooleanValue", "getIntegerValue", "getEnumeration", "getBooleanCalibration"],
        "calibrationManager.getBoolean(calItem.getCalId(), ((Boolean) calItem.getDefault()).booleanValue())",
        "com/gm/settings/data/calibration/CalibrationRequest.java"),
    ("GMConnections", "com/gm/settings/data/calibration/CalItem.java"): (
        "CalItem", ["getBooleanValue", "getIntegerValue", "getEnumeration", "getBooleanCalibration"],
        "calibrationManager.getBoolean(calItem.getCalId(), ((Boolean) calItem.getDefault()).booleanValue())",
        "com/gm/settings/data/calibration/CalibrationRequest.java"),
    ("CarSettings", "com/android/car/settings/calibration/CalItem.java"): (
        "CalItem", ["getBooleanValue", "getIntegerValue", "getEnumeration"],
        "calibrationManager.getBoolean(calItem.getCalId(), ((Boolean) calItem.getDefault()).booleanValue())",
        "com/android/car/settings/calibration/CalibrationRequest.java"),
}

# Files whose list entries are all read by one loop. Key: (app, file under sources/). Value: text that must be present.
TABLES = {
    ("info3", "gm/content/LauncherIconCalibrationHelper.java"): "int appTypeOrdinal = calManager.getEnumeration(calId, -1);",
}

_ORDER = ("default {} order, slot {}: the enumeration value selects an icon type through CAL_IDS_APP_TYPE "
          "(0 audio, 2 phone, 3 nav, 5 hotspot, 7 settings, 8 CarPlay, 10 Android Auto, 11 trailering, ...); a slot whose "
          "type is not visible is skipped")
for _n in range(1, 44):
    VALUE_EFFECTS[f"ApplicationOrdering{_n}"] = (_ORDER.format("home-screen", _n), "info3", ICON)
for _n in range(1, 13):
    VALUE_EFFECTS[f"AppTray_ApplicationOrdering{_n}"] = (_ORDER.format("app-tray", _n), "info3", ICON)
