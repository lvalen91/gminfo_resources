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
}

DW = "DelayedWKSApp"
WLAN = "server/wlanservice/GMWlanServiceImpl.java"
DIM = "server/connection/DeviceInfoManager.java"
UBR = "server/screenprojection/RemoteDeviceService/UsbBroadcastReceiver.java"
HOT = "settings/repositories/WiFiHotspotRepository.java"
APPS = "settings/repositories/ApplicationsRepository.java"
BTR = "settings/repositories/BluetoothRepository.java"
CPC = "server/carplay/service/internals/utils/CarPlayConfiguration.java"


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
    rule("ui.settings_hotspot_available", "Settings: hotspot",
         "WiFiEnable and WiFiP2PEnable and APPLICATION_HOMESCREEN_WIFIHOTSPOT_ENABLED",
         "isWifiHotspotAvailable() returns true", "open Settings and look for hotspot",
         [("GMSettings", HOT, "isWifiHotspotAvailable()")]),
    rule("ui.settings_wifi_services_menu", "Settings: Wi-Fi services menu",
         "not (Apple_CarPlay_enableWireless or AndroidAuto_enableWireless)",
         "The Wi-Fi services menu is available only with BOTH wireless projection settings off; "
         "when hidden, Settings shows hotspot options regardless of hmi_hotspot_disable_status",
         "open Settings and look for the Wi-Fi services control",
         [("GMSettings", HOT, "isWifiServicesMenuAvailable()"), ("GMSettings", HOT, "Since WiFiServicesMenu is hidden")]),
    rule("ui.settings_wifi_networks", "Settings: Wi-Fi networks",
         "BACK_OFFICE_SERVER_ENABLED and WiFiEnable", "isWifiNetworksAvailable() returns true",
         "open Settings and look for Wi-Fi networks",
         [("GMSettings", "settings/repositories/WiFiNetworksRepository.java", "isWifiNetworksAvailable()")],
         note="First term is the app's isBackOfficeServerEnable(); its link to this calibration was not traced."),
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
    rule("ui.settings_carplay_app", "Settings: CarPlay apps",
         "Enable_Application_Apple_Carplay", "Settings treats com.gm.carplay and com.gm.hmi.carplay as enabled",
         "Settings application list", [("GMSettings", APPS, 'case "com.gm.hmi.carplay"')]),
    rule("ui.settings_bluetooth", "Settings: Bluetooth state",
         "bt_adapter_on and EnableBluetooth and BluetoothDevicePairLimit > 0",
         "Settings reports Bluetooth as enabled (UI state; this does not switch the adapter)",
         "log 'Bt adapter enabled: ..., calBtEnabled:'", [("GMSettings", BTR, "calBtPairLimit")]),
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
