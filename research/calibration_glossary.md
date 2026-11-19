# calibration_glossary.md — A11 LTZ slot04 `OverrideValue` calibration-key catalog

Pure reference data, research-only: the full 404-entry calibration-key catalog (key /
description / type / value / CalID, 26 named groups, exactly 404 `OverrideValue` entries)
reverse-engineered from the A11 LTZ slot04 override and extracted verbatim from
`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` (source lines 547-1112, which now carries only a
one-line pointer here). This doc does not cover live RPO codes, `getprop` values, or
`CalSets.db` facts — those belong to `platform/vehicle_config.md`, which should carry a
one-line pointer to this doc for the full RE'd key catalog (not done by this writer — see
ledger).

No evidence-tag legend applies below: this is a single static RE snapshot (dated 2026-11-07
inline), not a live/firmware-split claim set. Group/online-method/public-context caveats below
are reproduced verbatim from the source and still apply.

---

## A11 LTZ slot 04 calibration glossary (2026-11-07)

Scope: all 404 `OverrideValue` entries in stock LTZ part `85045371`, including GMTrim.
Names, group names and enum labels come from the local Y177 `CalSets.db`; values and types come
from the LTZ XML. All 404 IDs also matched the local 2023 GIS-646 CalDef files; 398 have a
nonempty manufacturer description, reproduced below. Six use an explicitly labeled fallback.
Only 133 CalDef versions equal the corresponding override version; a version difference is
marked per entry and the description may not describe the exact installed revision. CalDef
text is documentation, not a live behavior test. Complex values are summarized; inspect the
original XML for their fields. String values are omitted. Do not infer undocumented units or
semantics.

Online method: a separate quoted exact-name-plus-calibration query was submitted for each of the
404 names using the available search engine (101 four-query requests). Ninety requests returned
no results; the 11 remaining requests returned mixed results, including unrelated uses of generic
names and Android documentation. This does not establish that every possible public source was
searched or that any individual GM-specific definition is absent. Android stream constants are
documented, but that does not prove how GM maps them.

Public context: [GM guidance on calibration-selected welcome animation](https://gm-techlink.com/wp-content/uploads/2020/12/GM_TechLink_23_December_2020.pdf),
[Chevrolet HUD guidance](https://www.chevrolet.com/support/vehicle/dashboard-lights-and-signals/how-to-use-the-head-up-display),
[Android Automotive volume management](https://source.android.com/docs/automotive/audio/volume-management),
[Android AudioManager stream constants](https://developer.android.com/reference/android/media/AudioManager), and
[ADASIS objectives](https://adasis.org/objectives/). These explain feature families, not the
exact behavior of GM's internal keys.

Calibration groups provide useful context: `GIS500_UI` is identity/trim; `GIS501_HOMESCREENUI`
is application visibility and ordering; `GIS631_CONFIGCHIMEPROD` is chime configuration;
`GIS621`/`GIS641` are diagnostic masks; `GIS619` is display/indicator brightness; `REQUESTACTIONMAP`,
`SINKLEVELCONTROL`, `AOSP` and `ROOMMODE` concern audio routing and levels. Group names are
labels, not proof of an individual setting's effects. Do not alter safety, diagnostics or audio
alert settings based only on their names.

### ADASIS (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `ADASIS_SUPPORT` | see GDMPRS-923, main switch between ADASIS variants [CalDef v5; override v1] | Enumeration | 0 (ADASIS_DISABLED) | `_yo_jQE1AEeO3UM5MzM17kw` |

### AMPINTERFACE (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `AmplifierType` | The CSM/Low Radio shall use the AmplifierType calibration to determine the type of amplifier within the vehicle. When no premium remote amplifier is present, this calibration notifies the CSM/Low Radio of whether a discrete amplifier or remote ANC module are present. [CalDef v5; override v3] | Enumeration | 3 (BosePremiumAmplifier) | `_skP0gMWPEeOaCvydzCgwdA` |

### AOSPSINKLEVELCONTROL (6)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `SourceOffsetCalibrationMap_DefaultAudioBus` | Map of AOSPBusEnum audio streams for each default audio bus source to the corresponding source offset in dB. [CalDef v2; override v1] | EnumFloatMap | EnumFloatMap (12 direct fields) | `_ez2NkM_mEemA27tS9SmuHQ` |
| `SourceOffsetCalibrationMap_AudioPatchBus` | Map of AOSPBusEnum audio streams for each patched audio bus source to the corresponding source offset in dB. [CalDef v2; override v1] | EnumFloatMap | EnumFloatMap (11 direct fields) | `_gyzqEM_lEemA27tS9SmuHQ` |
| `AOSPMinimumVolumeMap` | This is the map of minimum allowed volume index values for each volume group. | EnumIntegerMap | EnumIntegerMap (10 direct fields) | `_OWPYoM9XEemU596RWLqyBw` |
| `AOSPMaximumVolumeMap` | This is the map of maximum allowed volume index values for each volume group. [CalDef v2; override v1] | EnumIntegerMap | EnumIntegerMap (10 direct fields) | `_XZJHEc9YEemU596RWLqyBw` |
| `AOSPMinimumActivationVolumeMap` | This is the map of minimum activation volume index values for each volume group. | EnumIntegerMap | EnumIntegerMap (10 direct fields) | `_5Ubg0c9YEemU596RWLqyBw` |
| `AOSPVolumeGroupInitialDefaultsMap` | Initial default volume setting for each VolumeGroup. | EnumIntegerMap | EnumIntegerMap (11 direct fields) | `_RPPUIc9ZEemU596RWLqyBw` |

### AUDIOHMICALS (5)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `DEFAULT_DSP_MODE` | Determines default DSP mode to set based on requirements in UIS-202 and Audio Equalization function modules. Defaults to NORMAL, which is DSP_MODE_3 [CalDef v3; override v2] | Enumeration | 3 (DSP_MODE_3) | `_XRjNgMZAEeOsIMxD3Xbm-Q` |
| `ENABLE_NOISE_COMP_TEXT_STRING_OVERRIDE` | When this calibration is set to true, HMI shall show the Vehicle Noise Compensation for the branded audio solution. When this calibration set to false, HMI shall show SCV. [CalDef v5; override v3] | Boolean | false | `_yquBkU1AEeO3UM5MzM17kw` |
| `NOISE_COMP_TEXT_STRING` | When ENABLE_NOISE_COMP_TEXT_STRING_OVERRIDE is set to TRUE, the SMT shall set the required text string associated with branded vehicle noise compensation feature. If ENABLE_NOISE_COMP_TEXT_STRING_OVERRIDE set to FALSE, this cal is ignored. Current options: Bose Audio Pilot , Adaptive Volume. This can be changed to other string types using a cal override. [CalDef v5; override v3] | String | string (see source XML) | `_yrT3dU1AEeO3UM5MzM17kw` |
| `SIMULATED_SURROUND_DISPLAY_TEXT_ENABLE` | When this calibration is set to true, HMI shall show the surround mode UI for the branded audio solution. When this calibration set to false, the surround mode UI shall be removed. [CalDef v3; override v2] | Boolean | false | `_ysCQMU1AEeO3UM5MzM17kw` |
| `SIMULATED_SURROUND_DISPLAY_TEXT_STRING` | When SIMULATED_SURROUND_DISPLAY_TEXT_ENABLE is set to TRUE, the SMT shall set the required text string associated with branded surround mode feature. If SIMULATED_SURROUND_DISPLAY_TEXT_ENABLE set to FALSE, this cal is ignored. Current options: Bose Centerpoint , Surround. This can be changed to other string types using a cal override. [CalDef v4; override v3] | String | string (see source XML) | `_ysCQMk1AEeO3UM5MzM17kw` |

### BRANDANIMATIONSAUDIOCUES (12)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `AUDIO_CUE_ACUE_RUN_ENABLED` | This calibration controls whether or not a Run Audio Cue is played or not. This is reserved only for Electric/Hybrid vehicles. As long as any of the three Audio Cue CALs (Stop, Run, Welcome) are enabled, ‘Audio Cues’ and ‘Set Audio Cue Volume’ menus are available. If all three Audio Cue CALs are set to False, then the menu items should be hidden. [CalDef v5; override v3] | Boolean | false | `_ypM-oE1AEeO3UM5MzM17kw` |
| `AUDIO_CUE_ACUE_STOP_ENABLED` | This calibration controls whether or not a Stop Audio Cue is played or not. This is reserved only for Electric/Hybrid vehicles. As long as any of the three Audio Cue CALs (Stop, Run, Welcome) are enabled, ‘Audio Cues’ and ‘Set Audio Cue Volume’ menus are available. If all three Audio Cue CALs are set to False, then the menu items should be hidden. [CalDef v5; override v3] | Boolean | false | `_ypM-oU1AEeO3UM5MzM17kw` |
| `AUDIO_CUE_SHUTDOWN_ENABLE` | CueCalibrations [CueType] These are the boolean calibration flags for each of the cues defined within the AudioCues Fblock. There are currently 11 Cues defined. The CueType takes values from 0x01 - 0x0B. The diagram below defines the processing within the AudioCue FBlock for generating AudioCues relative to vehicle and system state changes All vehicles will have a Welcome Animation Only Hybrid vehicles would have Startup/Run and Shutdown/Goodbye AudioCues enabled. [CalDef v3; override v2] | Boolean | false | `_ypM-o01AEeO3UM5MzM17kw` |
| `AUDIO_CUE_STARTUP_ENABLE` | CueCalibrations [CueType] These are the boolean calibration flags for each of the cues defined within the AudioCues Fblock. There are currently 11 Cues defined. The CueType takes values from 0x01 - 0x0B. The diagram below defines the processing within the AudioCue FBlock for generating AudioCues relative to vehicle and system state changes All vehicles will have a Welcome Animation Only Hybrid vehicles would have Startup/Run and Shutdown/Goodbye AudioCues enabled. [CalDef v3; override v2] | Boolean | false | `_ypM-pE1AEeO3UM5MzM17kw` |
| `AUDIO_CUE_WELCOME_ENABLE` | See section <VERSION_OR_ADDRESS> in GIS. When enabled, an audio cue will play when welcome animation is played. As long as any of the three Audio Cue CALs (Stop, Run, Welcome) are enabled, ‘Audio Cues’ and ‘Set Audio Cue Volume’ menus are available. If all three Audio Cue CALs are set to False, then the menu items should be hidden. [CalDef v6; override v4] | Boolean | false | `_ypNlsE1AEeO3UM5MzM17kw` |
| `VEHICLE_ANIMATION_SHUTDOWN_TYPE` | Shutdown Animation type The shutdown animation shall be defined by a calibration setting as shown below [CalDef v4; override v3] | Enumeration | 2 (PLAY_ANIMATION) | `_ysLaM01AEeO3UM5MzM17kw` |
| `VEHICLE_ANIMATION_STARTUP_TYPE` | Start-up Audio Cues type The Start-up Audio Cues shall be defined by a calibration setting as shown below [CalDef v4; override v3] | Enumeration | 1 (CHEVY) | `_ysLaNU1AEeO3UM5MzM17kw` |
| `VEHICLE_ANIMATION_WELCOME_TYPE` | After powerup the silverbox shall display a Welcome Animation which is specific to the brand of the vehicle. The welcome animation shall be defined by a calibration setting as shown below [CalDef v4; override v2] | Enumeration | 1 (CHEVY) | `_ysMBME1AEeO3UM5MzM17kw` |
| `VEHICLE_AUDIOCUE_SHUTDOWN_TYPE` | Shutdown Audio Cues type The Shutdown Cues shall be defined by a calibration setting as shown below [CalDef v4; override v3] | Enumeration | 1 (CHEVY) | `_ysMBMk1AEeO3UM5MzM17kw` |
| `VEHICLE_AUDIOCUE_STARTUP_TYPE` | Start-up Audio Cues type The Start-up Audio Cues shall be defined by a calibration setting as shown below [CalDef v4; override v3] | Enumeration | 1 (CHEVY) | `_ysMBNE1AEeO3UM5MzM17kw` |
| `VEHICLE_AUDIOCUE_WELCOME_TYPE` | Welcome Audio Cues type The welcome Audio Cues shall be defined by a calibration setting as shown below [CalDef v4; override v3] | Enumeration | 1 (CHEVY) | `_ysMoQE1AEeO3UM5MzM17kw` |
| `WELCOME_ANIMATION_ENABLED` | This calibration controls whether or not a Welcome Animation is played or not. [CalDef v5; override v3] | Boolean | true | `_ysN2gU1AEeO3UM5MzM17kw` |

### DISPLAYGESTURESANDTIMEOUTS (8)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `ALERTWINDOWELEMENT_DELAYEDACTIONPRESENTATIONTIME` | Time for how long buttons on Alerts and Pop-ups should be delayed before being presented to prevent the user from inadvertently dismissing the pop-up unintentionally. The default time is 500ms. [CalDef v5; override v4] | Integer | 500 | `_ypCmk01AEeO3UM5MzM17kw` |
| `DEFAULT_AUDIO_TOUCH_FEEDBACK_SETTING` | Audible Touch Feedback specifies if sounds play when you press the touchscreen or a physical control on the radio faceplate. | Boolean | false | `_yp_o3E1AEeO3UM5MzM17kw` |
| `ENABLE_MENU_AUDIO_TOUCH_FEEDBACK` | Menu Configuration Settings This bit controls the presence of a user selectable menu for audible touchscreen feedback and shall be enabled for all NON-CADILLAC systems with audible beeps and disabled for Cadillac system with Haptic feedback. 2) Potentially need to add new calibration to allow calibration DEFAULTING of the selection of audible touch feedback Currently the MY2014 software defaults the touch feedback setting menu item to OFF. | Boolean | true | `_yqszek1AEeO3UM5MzM17kw` |
| `FACEPLATE_FLING_MIN_VOLUME_POSITIONS` | This defines the minimum number of volume positions that must be detected before it qualifies the action as a swipe/fling of the faceplate volume. [CalDef v6; override v2] | Integer | 5 | `_yq2kek1AEeO3UM5MzM17kw` |
| `FACEPLATE_TAP_MAX_TIME` | This defines the amount of time (in milliseconds) that still qualifies the action as a Tap and not a press and hold. Once a press and hold is detected based on this timer, the volume is incremented or decremented by one step, and the timer in VOLUME_PRESS_HOLD_VOLUMESLEWRATE is started to determine when the volume will be incremented or decremented again. [CalDef v5; override v2] | Integer | 500 | `_yq2ke01AEeO3UM5MzM17kw` |
| `FACEPLATE_SLIDER_POSITIONS_PER_VOLUME_STEP` | This Calibrations defines how sensitive the volume slider should be to obtain the desired effect for the number of swipes needed to reach max volume. It defines how many slider positions must be traversed before the volume is increased by one step. Higher numbers lead to a less sensitive volume bar. [CalDef v5; override v4] | Integer | 3 | `_yq2kfU1AEeO3UM5MzM17kw` |
| `MAX_FACEPLATE_VOLUME_POSITIONS` | This calibration defines the number of slider postitions that are used to communicate the position of the finger from the far left to the far right side of the slider. This is based on the interface between the faceplate and radio. [CalDef v4; override v3] | Integer | 63 | `_yrNJ1E1AEeO3UM5MzM17kw` |
| `VOLUME_PRESS_HOLD_VOLUMESLEWRATE` | This defines how quickly the volume should increase or decrease as the user presses and holds their finger. This calibration defines how many milliseconds should pass in between increasing or decreasing the volume by one step while the finger is held. [CalDef v6; override v3] | Integer | 50 | `_ysMoTk1AEeO3UM5MzM17kw` |

### DISTORTIONLIMITING (19)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `DDL_ENABLE` | All amplifier outputs including both the CSM and Low Radio’s internal amplifiers as well as those in a remote amplifier shall provide some form of Dynamic Distortion Limiting to minimize or eliminate clipping of the amplifier speaker output and minimize speaker distortions- The distortion limiting algorithm shall include the following capabilities: 1. The DDL algorithm shall be applied to all amplified speaker outputs. 2. It should be possible, to enable / disable the DDL. | Boolean | true | `_eQ3R4DLREeSm0acW-cA1AQ` |
| `AmplifierHardwareClipSignalType` | Defines the behavior of the amplifier hardware clip signal for a specific vehicle. | Enumeration | 0 (FrontOutputsOnly) | `_d3vEUHxzEeOvGYtg-Dwcrw` |
| `FrontSoftwareClipDetectorThreshold` | Threshold for front software clip detector. 0 dB is maximum amplifier output. | Float | 0.0 | `_67gBUX0qEeOrZo4Kbmzuxg` |
| `FrontSoftwareClipDetectorAttackTime` | No CalDef description; refer to calibration name and group | Integer | 10 | `_FIj48X0wEeOKR8CTsd92Kg` |
| `FrontSoftwareClipDetectorReleaseTime` | No CalDef description; refer to calibration name and group | Integer | 10000 | `_-3uXkX0wEeOKR8CTsd92Kg` |
| `FrontLimiterMinimumGain` | No CalDef description; refer to calibration name and group | Float | 0.0 | `_X93ngX0vEeOKR8CTsd92Kg` |
| `FrontLimiterAttackRate` | Rate at which the front limiter attack is applied in units of dB / ms. Note that the units are set to dB as dB / ms is only used for this calibration and is not defined as a standard unit. | Float | 10.0 | `_hz_XEH06EeOWiNX3NsDM5Q` |
| `FrontLimiterReleaseRate` | Rate at which the front limiter release is applied in units of dB / ms. Note that the units are set to dB as dB / ms is only used for this calibration and is not defined as a standard unit. | Float | 1.0 | `_WS5kMX-EEeOTAM8ORqTgOg` |
| `FrontClipSignalSelection` | Selects the clip signal selection for the front speaker amp outputs | Enumeration | 0 (Off) | `_YZUxQH-cEeOTAM8ORqTgOg` |
| `RearSoftwareClipDetectorThreshold` | Threshold for rear software clip detector. 0 dB is maximum amplifier output. | Float | 0.0 | `_7pDjgX0tEeOKR8CTsd92Kg` |
| `RearSoftwareClipDetectorAttackTime` | No CalDef description; refer to calibration name and group | Integer | 10 | `_4rFPIX0wEeOKR8CTsd92Kg` |
| `RearSoftwareClipDetectorReleaseTime` | No CalDef description; refer to calibration name and group | Integer | 1000 | `_VoPoMX-FEeOTAM8ORqTgOg` |
| `RearLimiterMinimumGain` | No CalDef description; refer to calibration name and group | Float | 0.0 | `_fqkNcX0vEeOKR8CTsd92Kg` |
| `RearLimiterAttackRate` | Rate at which the rear limiter attack is applied in units of dB / ms. Note that the units are set to dB as dB / ms is only used for this calibration and is not defined as a standard unit. | Float | 10.0 | `_485TgX-DEeOTAM8ORqTgOg` |
| `RearLimiterReleaseRate` | Rate at which the rear limiter release is applied in units of dB / ms. Note that the units are set to dB as dB / ms is only used for this calibration and is not defined as a standard unit. | Float | 1.0 | `_cs4lEX-EEeOTAM8ORqTgOg` |
| `RearClipSignalSelection` | Selects the clip signal selection for the rear speaker amp outputs | Enumeration | 0 (Off) | `_Vi9SAX-lEeOTAM8ORqTgOg` |
| `FrontRearLimiterCombination` | All amplifier outputs including both the CSM and Low Radio’s internal amplifiers as well as those in a remote amplifier shall provide some form of Dynamic Distortion Limiting to minimize or eliminate clipping of the amplifier speaker output and minimize speaker distortions | Enumeration | 0 (FrontRearIndependent) | `_Gfr7sDLREeSm0acW-cA1AQ` |
| `LOUDNESS_OFFSET` | The CSM and Low radio shall implement the LOUDNESS_OFFSET calibration within their ALC process to adjust loudness curves after sound tuning into the optimal position. As an example, in the table in the previous section, the -20dB row represents the frequency response for 82dB(A) sound pressure level on the driver seat, head position. If corrections are needed, the LOUDNESS_OFFSET calibration should be used to move the curve into the right position. The LOUDNESS_OFFSET calibration is defined in the DistortionLimiting.caldef file within GIS-646 with Range of -20dB ... +20dB (1dB Steps) and a default value of 0dB. | Integer | 0 | `_BUk-MDLQEeSm0acW-cA1AQ` |
| `LOUDNESS_COMP_ENABLE` | Enables / disables Automatic Loudness Compensation processing. True = Enabled, False = Disabled | Boolean | true | `_87iC8EWqEeSJbrP6o-dHmQ` |

### FACEPLATEBUTTONS\_GLOBALA (29)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `ILIN_FACEPLATE_SWITCH_1` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 23 (PowerSwitch) | `_j6qK8MAdEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_2` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 31 (MenuSwitch) | `_8PXsAMAdEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_3` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 9 (BandSwitch) | `_EUNsMMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_4` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 21 (TuneDownSwitch) | `_GmOyIMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_5` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 20 (TuneUpSwitch) | `_IzyO0MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_6` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 8 (HomeSwitch) | `_M49UcMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_7` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 22 (SourceAdvanceSwitch) | `_PVKRIMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_8` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 10 (BackSwitch) | `_SCbvsMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_9` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_UeaC4MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_10` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 28 (ToneSwitch) | `_WYtMYMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_11` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_ZV7ygMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_12` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_bJaiUMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_13` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_dgE3sMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_14` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_hsspIMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_15` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_jdkw4MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_16` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_lURz0MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_17` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_nXBHoMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_18` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_pUm1sMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_19` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_rhrKMMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_20` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_tEWd4MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_21` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_uyxHgMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_22` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_xJbc4MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_23` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_y49g0MAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_24` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_0uHroMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_25` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_2ZiEkMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_SWITCH_26` | Global A ILIN ICS Faceplate Switch Mapping [CalDef v3; override v1] | Enumeration | 0 (Unused) | `_38basMAeEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_ENCODER_1` | Global A ILIN ICS Faceplate Encoder Mapping [CalDef v3; override v1] | Enumeration | 1 (VolumeEncoder) | `_933o8MAfEeOV2KW0e9ssOw` |
| `ILIN_FACEPLATE_ENCODER_2` | Global A ILIN ICS Faceplate Encoder Mapping [CalDef v3; override v1] | Enumeration | 2 (TuneEncoder) | `_GjBbMMAgEeOV2KW0e9ssOw` |
| `BUTTON_BEEP_FEEDBACK` | The default Button Beep Feedback setting should be calibratable, with the intended default to be On. [CalDef v3; override v1] | Boolean | true | `_O-UzkMAgEeOV2KW0e9ssOw` |

### GIS1007\_SETTINGS\_GLOBALB (2)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `P_HUD_MENU_AVAILABLE` | Set when Vehicle is equipped with HUD. When not Set, hide “Head Up Display” menu under Display. Note: False= Menu Off; True=Menu ON | Boolean | false | `_yd3iYE1-EeibCblrVhJh5A` |
| `P_ADAPTIVE_CRUISE_FROM_SIGN_PRESENT` | For some vehicles, “Adaptive Cruise Speed from Signs” menu is not present under “Collision/Detection Systems” settings menu. Note: False= Menu Off; True= Menu ON | Boolean | false | `_CKeCUE14EeibCblrVhJh5A` |

### GIS500\_UI (3)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `GMTrim` | Trim calibration required for unique welcome animation | Enumeration | 16 (LTZ) | `_M7_ucBzvEeumObnnB0oIhw` |
| `GMModel` | Model calibration required for GAS integration. | Enumeration | 4 (Silverado) | `_71d3oP_TEemcM4o___siSA` |
| `GMBrand` | Brand calibration that define which graphics and highlighting will be utilized [CalDef v3; override v1] | Enumeration | 3 (GM_Brand_Chevrolet) | `_6jigAG6rEeSIp5iyPWbHnw` |

### GIS501\_HOMESCREENUI (33)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `APPLICATION_HOMESCREEN_GOOGLEASSISTANT_ENABLED` | This calibration is used to Enable/Disable the display of this Application on the HomeScreen and in the App Tray. When this calibration is set to True (Enabled), this HomeScreen Application shall be displayed on the HomeScreen. When this calibration is set to False (Disabled), this HomeScreen Application shall not be displayed on the HomeScreen. | Boolean | true | `_vzMekQTMEeuhM_xpS7qcsA` |
| `APPLICATION_HOMESCREEN_GOOGLEMAPS_ENABLED` | This calibration is used to Enable/Disable the display of this Application on the HomeScreen and in the App Tray. When this calibration is set to True (Enabled), this HomeScreen Application shall be displayed on the HomeScreen. When this calibration is set to False (Disabled), this HomeScreen Application shall not be displayed on the HomeScreen. | Boolean | true | `_7p18cQTMEeuhM_xpS7qcsA` |
| `APPLICATION_HOMESCREEN_PLAYSTORE_ENABLED` | This calibration is used to Enable/Disable the display of this Application on the HomeScreen and in the App Tray. When this calibration is set to True (Enabled), this HomeScreen Application shall be displayed on the HomeScreen. When this calibration is set to False (Disabled), this HomeScreen Application shall not be displayed on the HomeScreen. | Boolean | true | `__jFe4QTMEeuhM_xpS7qcsA` |
| `APPLICATION_HOMESCREEN_CAMERA_ENABLED` | This calibration is used to Enable/Disable the display of this Application on the HomeScreen and in the App Tray. When this calibration is set to True (Enabled), this HomeScreen Application shall be displayed on the HomeScreen. When this calibration is set to False (Disabled), this HomeScreen Application shall not be displayed on the HomeScreen. | Boolean | true | `_laqIAQTNEeuhM_xpS7qcsA` |
| `APPLICATION_HOMESCREEN_TEENDRIVER_ENABLED` | This calibration is used to Enable/Disable the display of this Application on the HomeScreen and in the App Tray. When this calibration is set to True (Enabled), this HomeScreen Application shall be displayed on the HomeScreen. When this calibration is set to False (Disabled), this HomeScreen Application shall not be displayed on the HomeScreen. | Boolean | true | `_k7bOUQTNEeuhM_xpS7qcsA` |
| `ApplicationOrdering1` | Application 1 on HomeScreen [CalDef v5; override v1] | Enumeration | 0 (Audio) | `_MbJEMbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering2` | Application 2 on HomeScreen [CalDef v5; override v1] | Enumeration | 30 (GoogleMaps) | `_M0qXcbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering3` | Application 3 on HomeScreen [CalDef v5; override v1] | Enumeration | 2 (Phone) | `_NENPUbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering4` | Application 4 on HomeScreen [CalDef v5; override v1] | Enumeration | 33 (Camera) | `_NUMMEbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering5` | Application 5 on HomeScreen [CalDef v5; override v1] | Enumeration | 31 (GoogleAssistant) | `_NfutsbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering6` | Application 6 on HomeScreen [CalDef v5; override v1] | Enumeration | 32 (PlayStore) | `_Nt3QUbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering7` | Application 7 on HomeScreen [CalDef v5; override v1] | Enumeration | 10 (AndroidAuto) | `_N5KhYbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering8` | Application 8 on HomeScreen [CalDef v5; override v1] | Enumeration | 8 (CarPlay) | `_OD5xwbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering9` | Application 9 on HomeScreen [CalDef v5; override v1] | Enumeration | 11 (Trailering) | `_OOssgbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering10` | Application 10 on HomeScreen [CalDef v6; override v1] | Enumeration | 13 (Climate) | `_ObImAbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering11` | Application 11 on HomeScreen [CalDef v6; override v1] | Enumeration | 20 (RearClimate) | `_OoE10bhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering12` | Application 12 on HomeScreen [CalDef v6; override v1] | Enumeration | 27 (APA) | `_OzeNgbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering13` | Application 13 on HomeScreen [CalDef v6; override v1] | Enumeration | 7 (Settings) | `_PN-YMbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering14` | Application 14 on HomeScreen [CalDef v7; override v1] | Enumeration | 5 (WiFiHotspot) | `_QTwUgbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering16` | Application 16 on HomeScreen [CalDef v7; override v1] | Enumeration | 19 (Video) | `_QsF8AbhtEeSmdeXBYRoUqg` |
| `ApplicationOrdering17` | Application 17 on HomeScreen [CalDef v6; override v1] | Enumeration | 34 (TeenDriver) | `_Q8vnIbhtEeSmdeXBYRoUqg` |
| `AppTray_ApplicationOrdering1` | Application 1 on the App Tray | Enumeration | 0 (Audio) | `_Dsa9sQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering2` | Application 2 on the App Tray | Enumeration | 30 (GoogleMaps) | `_OzxsoQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering3` | Application 3 on the App Tray | Enumeration | 2 (Phone) | `_OkG48QTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering4` | Application 4 on the App Tray | Enumeration | 11 (Trailering) | `_OVMTMQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering5` | Application 5 on the App Tray | Enumeration | 31 (GoogleAssistant) | `_ODopIQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering6` | Application 6 on the App Tray | Enumeration | 32 (PlayStore) | `_NuuJEQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering7` | Application 7 on the App Tray | Enumeration | 10 (AndroidAuto) | `_ifbX4QTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering8` | Application 8 on the App Tray | Enumeration | 8 (CarPlay) | `_iIoBcQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering9` | Application 9 on the App Tray | Enumeration | 33 (Camera) | `_h6naoQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering10` | Application 10 on the App Tray | Enumeration | 13 (Climate) | `_hokoYQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering11` | Application 11 on the App Tray | Enumeration | 20 (RearClimate) | `_jaWIAQTLEeuhM_xpS7qcsA` |
| `AppTray_ApplicationOrdering12` | Application 12 on the App Tray | Enumeration | 7 (Settings) | `_gaGDEQTLEeuhM_xpS7qcsA` |

### GIS502\_TUNERHMI (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `Album_Art_Menu_Item_On` | The Album_Art_Menu_Item_On calibration defines the HMI menu item default state for Album Art. When TRUE, Album Art images are displayed. When FALSE, Album Art images are not displayed. The default setting is TRUE. (On) [CalDef v3; override v1] | Boolean | false | `_UK-wwblJEeSMLcx9-dghJQ` |

### GIS507\_SETTINGS (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `TRANSMITTER_POCKET_LOCATION` | This CAL is used to show the corresponding image on the radio display of the pocket location for a given vehicle the user will be instructed to put their keyless transmitter in for teen driver key transmitter learning. For more information on this CAL see Sec¬tion <VERSION_OR_ADDRESS>.1 in the GIS-507. | Enumeration | 7 (Cup_Holder_ForeAndAfter) | `_XtdusFIjEeibCblrVhJh5A` |

### GIS508\_PERSONALIZATIONFBS (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `Last_Profile_Enable` | When enabled, the system will default to the last profile when no identifier is detected or assigned. When disabled, the system will default to the Default profile. [CalDef v4; override v2] | Boolean | true | `_z_620KmXEeSBV82hZ9UINQ` |

### GIS512\_CONNECTIONS (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `BluetoothModuleDeviceName` | The Bluetooth Module device name (user-friendly name) shall be based on the vehicle brand and model. The Bluetooth Module shall not allow changes of the device name. Starting MY18, possible Bluetooth friendly names are: Cadillac vehicles: myCadillac, Chevrolet vehicles: myChevrolet, Buick vehicles: myBuick, GMC vehicles: myGMC, Opel vehicles: myOpel, Vauxhall vehicles: myVauxhall, and Holden vehicles: myHolden [CalDef v3; override v1] | String | string (see source XML) | `_-ofJEG7gEeSssq_awwoZ3g` |

### GIS604\_SAFETYRELATEDVOLUMEGROUPOVERRIDES (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `SAFETY_VOL_OVRD_LEVEL` | A calibration parameter for the volume level to set each volume group to during an override. [CalDef v3; override v1] | Integer | 0 | `_94QswPO6EeavdZd7UaL_VA` |

### GIS619\_BRIGHTNESSCONTROL\_GLOBALA (7)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `INDICATOR_BRIGHTNESS_OUTPUT_TABLE` | Output axis values for indicator brightness. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (19 direct fields) | `_tlzP3vAHEeOg0Bw-hP6AxA` |
| `CONTROL_BRIGHTNESS_OUTPUT_TABLE` | Output axis values for control brightness. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (19 direct fields) | `_tlz27_AHEeOHWBw-hP6AxA` |
| `DISPLAY_BRIGHTNESS_OUTPUT_NIGHT_TABLE` | Output axis values for nighttime brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (19 direct fields) | `_tlz28_AHEeOMtBw-hP6AxA` |
| `DISPLAY_BRIGHTNESS_OUTPUT_DAYTIME_TABLE` | Output axis values for display brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (19 direct fields) | `_tl0eAPAHEeOzExw-hP6AxA` |
| `DISPLAY_CAMERA_IMAGE_OUTPUT_NIGHT_TABLE` | Output axis values for nighttime brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (19 direct fields) | `_3pwegXl3EeSLs4JOFbfKLg` |
| `LAG_FILTER_LOW_END_THRESHOLD` | Lag filter low end threshold. When FilteredValue <= this threshold, the output of the FilteredValue shall be set to zero. Default value is N-value, where E=(N/65535)*100 is the low end threshold. | Integer | 0 | `_zsYQQLQ1EeOvU4rhQ1TwqQ` |
| `INDICATOR_BRIGHTNESS_SOURCE` | This enumeration determines which CAN signal shall be used to compute the indicator brightness. It was specifically defined for Info3/Global B in order to properly handle deadfronted ICSs such as the MY13 and beyond Cadillac ICS. | Enumeration | 0 (NORMAL) | `_3ZChsLRVEeOvU4rhQ1TwqQ` |

### GIS619\_BRIGHTNESSCONTROL\_GLOBALB (7)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `INDICATOR_BRIGHTNESS_OUTPUT_TABLE_GLOBALB` | Output axis values for display brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (21 direct fields) | `_xBa40BMAEeappLMV3_fLfg` |
| `CONTROL_BRIGHTNESS_INPUT_TABLE_GLOBALB` | Input axis values for Indicator brightness level. Default value is N-value, where E=(N)*1.0 and E is brightness level in percent luminance. [CalDef v3; override v1] | IntegerArray | IntegerArray (11 direct fields) | `_xNC7UAywEeab4ezHobftRw` |
| `DISPLAY_BRIGHTNESS_INPUT_TABLE_GLOBALB` | Input axis values for brightness level. Default value is N-value, where E=(N)*1.0 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (21 direct fields) | `_sgcWYAy9Eea0_Ls20O9LdA` |
| `DISPLAY_BRIGHTNESS_OUTPUT_TABLE_GLOBALB` | Output axis values for display brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (21 direct fields) | `_JMmt8AzAEea0_Ls20O9LdA` |
| `DISPLAY_CAMERA_IMAGE_OUTPUT_TABLE_GLOBALB` | Output axis values for Camera brightness level. Default value is N-value, where E=(N/65535)*100 and E is brightness level in percent luminance. | IntegerArray | IntegerArray (21 direct fields) | `_TJvS4A4oEeaBr7QHlVyUoA` |
| `LAG_FILTER_LOW_END_THRESHOLD_GLOBALB` | Lag filter low end threshold. When FilteredValue <= this threshold, the output of the FilteredValue shall be set to zero. Default value is N-value, where E=(N/65535)*100 is the low end threshold. | Integer | 0 | `_UE2CcBPJEeappLMV3_fLfg` |
| `INDICATOR_BRIGHTNESS_SOURCE_GLOBALB` | This enumeration determines which CAN signal shall be used to compute the indicator brightness. It was specifically defined for Info3/Global B in order to properly handle deadfronted ICSs such as the MY13 and beyond Cadillac ICS. | Enumeration | 0 (NORMAL) | `_SKgeQUUBEeaX676o0O3GfQ` |

### GIS621\_DIAGNOSTICCALDEF\_GLOBALA (17)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `DTC_MASK_B1025_01` | B1025_01_LEFT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures vehicle system (battery positive) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_vkyzUJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1025_02` | B1025_02_LEFT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures ground (battery negative) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_yL7NoJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1025_04` | B1025_04_LEFT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU determines an open circuit via lack of bias voltage, low current flow, no change in state of an input in response to an output, etc. | Boolean | false | `_5mW-4JMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1035_01` | B1035_01_RIGHT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures vehicle system (battery positive) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_7EMO0JMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1035_02` | B1035_02_RIGHT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures ground (battery negative) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_773dsJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1035_04` | B1035_04_RIGHT_FRONT_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU determines an open circuit via lack of bias voltage, low current flow, no change in state of an input in response to an output, etc. | Boolean | false | `_33jTsJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1045_01` | B1045_01_LEFT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures vehicle system (battery positive) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_6Vk1UJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1045_02` | B1045_02_LEFT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures ground (battery negative) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_zDsjIJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1045_04` | B1045_04_LEFT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU determines an open circuit via lack of bias voltage, low current flow, no change in state of an input in response to an output, etc. | Boolean | false | `_4tSB0JMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1055_01` | B1055_01_RIGHT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures vehicle system (battery positive) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_3FhZ0JMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1055_02` | B1055_02_RIGHT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU measures ground (battery negative) potential for greater than a specified time period or when some other value is expected. | Boolean | false | `_1fgeQJMZEeOhNKe0zA3AsQ` |
| `DTC_MASK_B1055_04` | B1055_04_RIGHT_REAR_AUDIO_OUTPUT_CIRCUIT - This sub type is used for failures where the ECU determines an open circuit via lack of bias voltage, low current flow, no change in state of an input in response to an output, etc. | Boolean | false | `_13klsJMpEeOYeLJDBKsy1g` |
| `DTC_MASK_U150F_00` | U150F_00_TLIN_INTER_DEVICE_DEDICATED_BUS_DTC - The Master CSM shall wait 250ms after its first TLIN message to the Slave and then this DTC will be set after the Master has detected one of the following problems with 3 consecutive TLIN Transmission occurs: | Boolean | false | `_FfJQ8JVuEeO7UP4sq3M7sQ` |
| `DTC_MASK_U0186_00` | U0186_00_LOST_COMMUNICATION_WITH_AUDIO_AMPLIFIER | Boolean | false | `_fkz9QZKEEeOH48DtJo_c7Q` |
| `DTC_MASK_U18B1_00` | U18B1_00_LOSS_OF_LINK_WITH_AUDIO_AMPLIFIER_ON_ETHERNET_BUS - The Ethernet switch is unable to establish a link up with the Audio Amplifier. This generates a notification to the CSM application that a fault has occurred. | Boolean | false | `_P74OoJKGEeOH48DtJo_c7Q` |
| `DTC_MASK_U18B1_02` | DTC U18B0 – U18B1_02_LOSS_OF_LINK_WITH_AUDIO_AMPLIFIER_ON_ETHERNET_BUS - ~MY18 FTB: 02 – Short to Ground [CalDef v2; override v1] | Boolean | false | `_zT_y0La6EeSpA6W9o4B4Rg` |
| `DTC_MASK_U18B1_04` | DTC U18B0 – U18B1_04_LOSS_OF_LINK_WITH_AUDIO_AMPLIFIER_ON_ETHERNET_BUS - ~MY18 - FTB: 04 – Open Circuit [CalDef v2; override v1] | Boolean | false | `_Or1GoLa7EeSpA6W9o4B4Rg` |

### GIS631\_CONFIGCHIMEPROD\_STDTHEME0\_GLOBALB (159)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `K_THEME_0_VERSION` | String up to 255 characters providing versioning information about the theme. | String | string (see source XML) | `_zHiqAErbEeOF3P4e5N5VOg` |
| `K_THEME_0_LEVEL_OFFSET` | A Calibration that specifies the overall amplitude offset to apply when playing any chime event from the prescribed theme. [CalDef v2; override v1] | Integer | 0 | `_EiXiIErcEeOF3P4e5N5VOg` |
| `THEME0_CHIME_ID_100` | SEAT_BELT_REMINDER_GLOBAL [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhmRorkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_110` | SEAT_BELT_REMINDER_GLOBAL_TYPE_2 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_ypZvUryeEeaoE74EvTDyjQ` |
| `THEME0_CHIME_ID_111` | CLUSTER_CHIME_14 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCorkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_140` | FCA_IMMINENT_ALRT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCpbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_142` | TLA_WARNING [CalDef v2; override v1] | Record | Record (9 direct fields) | `_fjLWEiKzEeaKsqBcbUr-oQ` |
| `THEME0_CHIME_ID_165` | RR_CROSS_TRAFFIC_ALRT_LFT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCprkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_170` | RR_CROSS_TRAFFIC_ALRT_RGHT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCp7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_175` | FRNT_PED_CLSN_MTGN [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCqbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_176` | CLUSTER_CHIME_13 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCqrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_177` | REAR_PED_CLSN_MTGN_ALERT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCq7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_178` | RIM_INITIAL_COLLISION [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCrLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_179` | RIM_BRAKE_PULSE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCrbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_180` | CLUSTER_CHIME_9 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCrrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_181` | CLUSTER_CHIME_10 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCr7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_185` | PARK_ASSIST_REAR_FIRST_REPORT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCsLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_186` | APA_STOP_CHIME [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCsbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_187` | APA_SPOT_FOUND [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCsrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_188` | APA_COMPLETE_CHIME [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCs7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_189` | APA_CANCELED [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCtLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_190` | APA_FAILED [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCtbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_195` | PARK_ASSIST_FAIL [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCt7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_200` | PARK_ASSIST_REAR_ROGER [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCuLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_205` | PARK_ASSIST_FRONT_FIRST_REPORT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCubkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_220` | PARK_ASSIST_FRONT_ROGER [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCurkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_225` | PARK_ASSIST_REAR_LEFT_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCu7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_230` | PARK_ASSIST_REAR_LEFT_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCvLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_235` | PARK_ASSIST_REAR_LEFT_ZONE_3_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCvbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_240` | PARK_ASSIST_REAR_LEFT_ZONE_4_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCvrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_245` | PARK_ASSIST_REAR_RIGHT_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCv7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_250` | PARK_ASSIST_REAR_RIGHT_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCwLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_255` | PARK_ASSIST_REAR_RIGHT_ZONE_3_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCwbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_260` | PARK_ASSIST_REAR_RIGHT_ZONE_4_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCwrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_265` | PARK_ASSIST_REAR_FULL_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCw7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_270` | PARK_ASSIST_REAR_FULL_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCxLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_275` | PARK_ASSIST_REAR_FULL_ZONE_3_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCxbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_280` | PARK_ASSIST_REAR_FULL_ZONE_4_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCxrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_285` | PARK_ASSIST_FRONT_LEFT_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCx7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_290` | PARK_ASSIST_FRONT_LEFT_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCyLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_295` | PARK_ASSIST_FRONT_RIGHT_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCybkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_300` | PARK_ASSIST_FRONT_RIGHT_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PhwCyrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_305` | PARK_ASSIST_FRONT_FULL_ZONE_1_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MkLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_310` | PARK_ASSIST_FRONT_FULL_ZONE_2_NA [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MkbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_315` | PARK_ASSIST_REAR_LEFT_ZONE_1_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MkrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_320` | PARK_ASSIST_REAR_LEFT_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mk7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_325` | PARK_ASSIST_REAR_LEFT_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MlLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_330` | PARK_ASSIST_REAR_LEFT_ZONE_4_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MlbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_335` | PARK_ASSIST_REAR_LEFT_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MlrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_340` | PARK_ASSIST_REAR_LEFT_ZONE_6_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Ml7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_355` | PARK_ASSIST_REAR_RIGHT_ZONE_1_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MmLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_360` | PARK_ASSIST_REAR_RIGHT_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MmbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_365` | PARK_ASSIST_REAR_RIGHT_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MmrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_370` | PARK_ASSIST_REAR_RIGHT_ZONE_4_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mm7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_375` | PARK_ASSIST_REAR_RIGHT_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MnLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_380` | PARK_ASSIST_REAR_RIGHT_ZONE_6_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MnbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_395` | PARK_ASSIST_REAR_FULL_ZONE_1_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MnrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_400` | PARK_ASSIST_REAR_FULL_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mn7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_405` | PARK_ASSIST_REAR_FULL_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MoLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_410` | PARK_ASSIST_REAR_FULL_ZONE_4_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MobkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_415` | PARK_ASSIST_REAR_FULL_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MorkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_420` | PARK_ASSIST_REAR_FULL_ZONE_6_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mo7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_435` | PARK_ASSIST_FRONT_LEFT_ZONE_1_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MpLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_440` | PARK_ASSIST_FRONT_LEFT_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MpbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_445` | PARK_ASSIST_FRONT_LEFT_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MprkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_450` | PARK_ASSIST_FRONT_LEFT_ZONE_4_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mp7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_455` | PARK_ASSIST_FRONT_LEFT_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MqLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_460` | PARK_ASSIST_FRONT_LEFT_ZONE_6_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MqbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_475` | PARK_ASSIST_FRONT_RIGHT_ZONE_1_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MqrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_480` | PARK_ASSIST_FRONT_RIGHT_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mq7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_485` | PARK_ASSIST_FRONT_RIGHT_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MrLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_490` | PARK_ASSIST_FRONT_RIGHT_ZONE_4_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MrbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_495` | PARK_ASSIST_FRONT_RIGHT_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MrrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_500` | PARK_ASSIST_FRONT_RIGHT_ZONE_6_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Mr7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_515` | PARK_ASSIST_FRONT_FULL_ZONE_1_EU [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MsLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_520` | PARK_ASSIST_FRONT_FULL_ZONE_2_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MsbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_525` | PARK_ASSIST_FRONT_FULL_ZONE_3_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MsrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_530` | PARK_ASSIST_FRONT_FULL_ZONE_4_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5Ms7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_535` | PARK_ASSIST_FRONT_FULL_ZONE_5_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MtLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_540` | PARK_ASSIST_FRONT_FULL_ZONE_6_EU [CalDef v3; override v1] | Record | Record (9 direct fields) | `_Ph5MtbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_561` | CLUSTER_CHIME_11 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MtrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_565` | LANE_DTCTN_WRNG_CTRL_LFT_HAND_SDE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MuLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_566` | LANE_FOLLOW_WARNING_LFT_HAND_SDE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MubkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_570` | LANE_DTCTN_WRNG_CTRL_RGHT_HAND_SDE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MurkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_571` | LANE_FOLLOW_WARNING_RGHT_HAND_SDE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mu7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_575` | LANE_DTCTN_WRNG_CTRL_HANDS_OFF_1 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MvLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_576` | LANE_FOLLOW_WARNING_GENERAL [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MvbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_580` | LANE_DTCTN_WRNG_CTRL_HANDS_OFF_2 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MvrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_581` | KEY_IN_REMINDER [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mv7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_582` | SHIFT_TO_PARK [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9lrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_583` | REAR_PED_CLSN_MTGN_NOTIFY [CalDef v2; override v1] | Record | Record (9 direct fields) | `_fjeRACKzEeaKsqBcbUr-oQ` |
| `THEME0_CHIME_ID_584` | TRAILERING_PHASE_2 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_fjeRASKzEeaKsqBcbUr-oQ` |
| `THEME0_CHIME_ID_585` | ROLLOVER_DISABLE_STATUS [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8MqhgXRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_586` | LANE_DTCTN_WRNG_CTRL_HANDS_OFF_3 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Rt_iEPOwEeazar-1HUL3Ow` |
| `THEME0_CHIME_ID_587` | TRAILERING_PHASE_1 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_7-PO0fzCEem-guTQGLehsQ` |
| `THEME0_CHIME_ID_601` | CLUSTER_CHIME_1 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9l7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_607` | CLUSTER_CHIME_19 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9mLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_608` | CLUSTER_CHIME_8 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9mbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_615` | RR_CLSR_NOTIFICATION [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8Mp6dHRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_617` | RR_CLSR_NOTIFICATION_OFF [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8MqhgHRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_710` | LST_DR_CLOSED_LCKNG_DLYD_LCKNG [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9mrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_711` | LST_DR_CLOSED_LCKNG_DLYD_LCKNG_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mt7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_712` | CLUSTER_CHIME_2 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9m7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_713` | CLUSTER_CHIME_18 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9nLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_715` | HEADLAMP_REMINDER [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9nbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_716` | HEADLAMP_REMINDER_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mw7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_720` | ELC_PRK_BRK_REMINDER_FXD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9nrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_721` | ELC_PRK_BRK_REMINDER_CONT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9n7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_722` | ONE_SIDED_PARK_LAMP [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9oLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_723` | ONE_SIDED_PARK_LAMP_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MxLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_770` | CLUSTER_CHIME_3_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9k7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_771` | CLUSTER_CHIME_20 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9obkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_772` | CLUSTER_CHIME_7 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9orkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_773` | CLUSTER_CHIME_3 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9o7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_774` | CLUSTER_CHIME_4 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9pLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_776` | MEM_SEAT_SNGL_BEEP_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9pbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_777` | MEM_SEAT_DBL_BEEP_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9prkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_778` | MEM_SEAT_TRPL_BEEP_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9p7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_779` | WALK_AWAY_LOCK_INHIBIT_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MwLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_780` | WALK_AWAY_LOCK_INHIBIT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9qLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_781` | MEM_SEAT_SNGL_BEEP_CO_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9qbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_782` | MEM_SEAT_DBL_BEEP_CO_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9qrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_783` | MEM_SEAT_TRPL_BEEP_CO_DRV [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9q7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_784` | MEM_SEAT_SNGL_BEEP_LR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9rLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_785` | MEM_SEAT_DBL_BEEP_LR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9rbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_786` | MEM_SEAT_TRPL_BEEP_LR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9rrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_787` | MEM_SEAT_SNGL_BEEP_RR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9r7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_788` | MEM_SEAT_DBL_BEEP_RR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9sLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_789` | MEM_SEAT_TRPL_BEEP_RR [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9sbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_790` | MEM_SEAT_SNGL_BEEP_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MxbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_791` | MEM_SEAT_DBL_BEEP_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MxrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_792` | MEM_SEAT_TRPL_BEEP_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5Mx7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_793` | MEM_SEAT_SNGL_BEEP_CO_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MyLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_794` | MEM_SEAT_DBL_BEEP_CO_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MybkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_795` | MEM_SEAT_TRPL_BEEP_CO_DRV_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MyrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_796` | MEM_SEAT_SNGL_BEEP_LR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5My7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_797` | MEM_SEAT_DBL_BEEP_LR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MzLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_798` | MEM_SEAT_TRPL_BEEP_LR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MzbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_799` | MEM_SEAT_SNGL_BEEP_RR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9kLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_800` | MEM_SEAT_DBL_BEEP_RR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9kbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_801` | MEM_SEAT_TRPL_BEEP_RR_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9krkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_910` | TELEMATICS_TBT_ATT [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9srkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_925` | NO_REMOTE_DTCTED_WRNG [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9s7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_926` | REMOTE_LEFT_IN_VEHICLE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9tLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_927` | NO_REMOTE_DTCTED_WRNG_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MwbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_928` | REMOTE_LEFT_IN_VEHICLE_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_Ph5MwrkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_935` | RR_CLSR_NORMAL [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8Mp6cnRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_936` | RR_CLSR_OBSTACLE [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8Mp6c3RhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_937` | RR_CLSR_NORMAL_OFF [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8Mp6dXRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_938` | RR_CLSR_OBSTACLE_OFF [CalDef v2; override v1] | Record | Record (9 direct fields) | `_8Mp6dnRhEea_SczYsO8uNw` |
| `THEME0_CHIME_ID_1461` | CLUSTER_CHIME_16 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9tbkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1462` | CLUSTER_CHIME_17 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9trkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1465` | GO_NOTIFIER_ACC [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9t7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1495` | CLUSTER_CHIME_5 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9uLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1496` | CLUSTER_CHIME_6 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9ubkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1497` | CLUSTER_CHIME_12 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9urkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1498` | CLUSTER_CHIME_15 [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9u7kwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1499` | CLUSTER_CHIME_5_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9lLkwEeWlrfA9YQnlrw` |
| `THEME0_CHIME_ID_1500` | CLUSTER_CHIME_6_OFF_MD [CalDef v2; override v1] | Record | Record (9 direct fields) | `_PiC9lbkwEeWlrfA9YQnlrw` |

### GIS631\_CONFIGSTDCHIMEPROD\_GENERICCAL\_GLOBALB (1)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `K_TURN_SIGNAL_LEVEL_DB` | This is the fixed level of the turn-signal ('click-clack') sound per GIS-604. [CalDef v5; override v1] | Float | -37.0 | `_Trd-4YhLEeO2nca4zzuiVA` |

### GIS641\_DIAGNOSTICCALDEF\_GLOBALB (16)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `DTC_MASK_B1A23_00` | ETHERNET BUS 6 (+) GENERAL FAILURE. Time between Sync updates of ≥ 10 seconds occurs devices shall assume a failure of the gPTP Grand Master clock and report a DTC | Boolean | true | `_kNdFIBtmEeaVv4YxjvxKoQ` |
| `DTC_MASK_B1A23_11` | ETHERNET BUS 6 (+) SHORT TO GROUND. This sub type is used for failures where the control module measures ground (battery negative) potential for greater than a specified time period or when some other value less than the low voltage limit DTC Sub Type is measured. | Boolean | true | `_QAEwYBtnEeaVv4YxjvxKoQ` |
| `DTC_MASK_B1A23_13` | ETHERNET BUS 6 (+) CIRCUIT OPEN. This sub type is used for failures, where the control module determines an open circuit via lack of bias voltage, low current flow, no change in the state of an input in response to an output, etc. | Boolean | true | `_HQZOABtoEeaVv4YxjvxKoQ` |
| `DTC_MASK_U0186_00_GlobalB` | Lost Communication with Audio Amplifier – No Sub Type Information. Upon notification by the handler that the associated supervised signal has failed supervision (typically 2.5 times the nominal periodic rate of the monitored signal). An adjustable debounce time, i.e. X of Y strategy, is permitted at the time that notification of failed supervision has been received by the application to delay storing of the DTC. | Boolean | true | `_s5BDsAEUEeiDo-Dq14by9g` |
| `DTC_MASK_B1960_11` | LEFT FRONT SPEAKER (+) (1) CIRCUIT SHORT TO GROUND. This sub type is used for failures where the control module measures ground (battery negative) potential. [CalDef v2; override v1] | Boolean | false | `_ufm_MCGtEeaY4JYlyGk5Lw` |
| `DTC_MASK_B1960_12` | Left Front Speaker (+) (1) Circuit Short To Battery. This sub type is used for failures, where the control module measures vehicle system (battery positive) potential for greater than a specified time period or when some other value higher than the high voltage limit DTC Sub Type is measured.. [CalDef v2; override v1] | Boolean | false | `_DGVyoCGuEeaY4JYlyGk5Lw` |
| `DTC_MASK_B1960_13` | Left Front Speaker (+) (1) Circuit Open. This sub type is used for failures, where the control module determines an open circuit via lack of bias voltage, low current flow, no change in the state of an input in response to an output, etc. [CalDef v2; override v1] | Boolean | false | `_kFxysCGvEeaY4JYlyGk5Lw` |
| `DTC_MASK_B1961_11` | Right Front Speaker (+) (1) Circuit Short To Ground. This sub type is used for failures where the control module measures ground (battery negative) potential [CalDef v2; override v1] | Boolean | false | `_MTVe8CG0EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1961_12` | Right Front Speaker (+) (1) Circuit Short To Battery. This sub type is used for failures, where the control module measures vehicle system (battery positive) potential for greater than a specified time period or when some other value higher than the high voltage limit DTC Sub Type is measured. [CalDef v2; override v1] | Boolean | false | `_jFluwCG0EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1961_13` | Right Front Speaker (+) (1) Circuit Open. This sub type is used for failures, where the control module determines an open circuit via lack of bias voltage, low current flow, no change in the state of an input in response to an output, etc. [CalDef v2; override v1] | Boolean | false | `_Gqr-8CG1EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1962_11` | Left Rear Speaker (+) Circuit Short To Ground. This sub type is used for failures where the control module measures ground (battery negative) potential. [CalDef v2; override v1] | Boolean | false | `_ZtlBECG1EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1962_12` | Left Rear Speaker (+) Circuit Short To Battery. This sub type is used for failures, where the control module measures vehicle system (battery positive) potential for greater than a specified time period or when some other value higher than the high voltage limit DTC Sub Type is measured. [CalDef v2; override v1] | Boolean | false | `_uULRoCG1EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1962_13` | Left Rear Speaker (+) Circuit Open. This sub type is used for failures, where the control module determines an open circuit via lack of bias voltage, low current flow, no change in the state of an input in response to an output, etc. [CalDef v2; override v1] | Boolean | false | `_ML_HgCG5EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1963_11` | Right Rear Speaker (+) Circuit Short To Ground. This sub type is used for failures where the control module measures ground (battery negative) potential [CalDef v2; override v1] | Boolean | false | `_gTK4MCG5EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1963_12` | Right Rear Speaker (+) Circuit Short To Battery. This sub type is used for failures, where the control module measures vehicle system (battery positive) potential for greater than a specified time period or when some other value higher than the high voltage limit DTC Sub Type is measured. [CalDef v2; override v1] | Boolean | false | `_zYmQ8CG5EeaY4JYlyGk5Lw` |
| `DTC_MASK_B1963_13` | Right Rear Speaker (+) Circuit Open. This sub type is used for failures, where the control module determines an open circuit via lack of bias voltage, low current flow, no change in the state of an input in response to an output, etc.. [CalDef v2; override v1] | Boolean | false | `_DOegUCHBEeaY4JYlyGk5Lw` |

### REQUESTACTIONMAP (41)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `STREAM_VOICE_CALL` | Action Map for Active Stream Type of STREAM_VOICE_CALL | Record | Record (41 direct fields) | `_jit5oK3VEeOe_uWRKKMYzg` |
| `STREAM_SYSTEM` | Action Map for Active Stream Type of STREAM_SYSTEM | Record | Record (41 direct fields) | `_kEAo0K3VEeOe_uWRKKMYzg` |
| `STREAM_RING` | Action Map for Active Stream Type of STREAM_RING | Record | Record (41 direct fields) | `_j0Ad8K3VEeOe_uWRKKMYzg` |
| `STREAM_MUSIC` | Action Map for Active Stream Type of STREAM_MUSIC | Record | Record (41 direct fields) | `_i3H-8K3VEeOe_uWRKKMYzg` |
| `STREAM_ALARM` | Action Map for Active Stream Type of STREAM_ALARM | Record | Record (41 direct fields) | `_kFhEsK3VEeOe_uWRKKMYzg` |
| `STREAM_NOTIFICATION` | Action Map for Active Stream Type of STREAM_NOTIFICATION | Record | Record (41 direct fields) | `_kHKDcK3VEeOe_uWRKKMYzg` |
| `STREAM_BLUETOOTH_SCO` | Action Map for Active Stream Type of STREAM_BLUETOOTH_SCO | Record | Record (41 direct fields) | `_jkeNIK3VEeOe_uWRKKMYzg` |
| `STREAM_SYSTEM_ENFORCED` | Action Map for Active Stream Type of STREAM_SYSTEM_ENFORCED | Record | Record (41 direct fields) | `_kIp4QK3VEeOe_uWRKKMYzg` |
| `STREAM_DTMF` | Action Map for Active Stream Type of STREAM_DTMF | Record | Record (41 direct fields) | `_kKN-gK3VEeOe_uWRKKMYzg` |
| `STREAM_TTS` | Action Map for Active Stream Type of STREAM_TTS | Record | Record (41 direct fields) | `_jf3Z8K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_AUDIO_CUE` | Action Map for Active Stream Type of STREAM_NATIVE_AUDIO_CUE | Record | Record (41 direct fields) | `_j-IDQK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_LVM_PROMPT` | Action Map for Active Stream Type of STREAM_NATIVE_LVM_PROMPT | Record | Record (41 direct fields) | `_kClFcK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_RDS_TRAFFIC` | Action Map for Active Stream Type of STREAM_NATIVE_RDS_TRAFFIC | Record | Record (41 direct fields) | `_jyHnkK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_AM_TUNER` | Action Map for Active Stream Type of STREAM_NATIVE_AM_TUNER | Record | Record (41 direct fields) | `_i9N_4K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_FM_TUNER` | Action Map for Active Stream Type of STREAM_NATIVE_FM_TUNER | Record | Record (41 direct fields) | `_jBDXAK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_SDARS_TUNER` | Action Map for Active Stream Type of STREAM_NATIVE_SDARS_TUNER | Record | Record (41 direct fields) | `_jEFc4K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DABFM_TUNER` | Action Map for Active Stream Type of STREAM_NATIVE_DABFM_TUNER | Record | Record (41 direct fields) | `_jHEfcK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_BLUETOOTH_AUDIO` | Action Map for Active Stream Type of STREAM_NATIVE_BLUETOOTH_AUDIO | Record | Record (41 direct fields) | `_jJjLsK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_AUDIO_DISK_PLAYER` | Action Map for Active Stream Type of STREAM_NATIVE_AUDIO_DISK_PLAYER | Record | Record (41 direct fields) | `_jMLB4K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_AUX` | Action Map for Active Stream Type of STREAM_NATIVE_AUX | Record | Record (41 direct fields) | `_jOlcsK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_LVM_STEREO_AUDIO` | Action Map for Active Stream Type of STREAM_NATIVE_LVM_STEREO_AUDIO | Record | Record (41 direct fields) | `_jQ_3gK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_MEDIA_PLAYER` | Action Map for Active Stream Type of STREAM_NATIVE_MEDIA_PLAYER | Record | Record (41 direct fields) | `_jS24sK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_IPOD` | Action Map for Active Stream Type of STREAM_NATIVE_IPOD | Record | Record (41 direct fields) | `_jU0nkK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_INTERNET_APP_AUDIO` | Action Map for Active Stream Type of STREAM_NATIVE_INTERNET_APP_AUDIO | Record | Record (41 direct fields) | `_jW5rMK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_RSI1` | Action Map for Active Stream Type of STREAM_NATIVE_RSI1 | Record | Record (41 direct fields) | `_jaDs4K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_RSI2` | Action Map for Active Stream Type of STREAM_NATIVE_RSI2 | Record | Record (41 direct fields) | `_jdGZ0K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_HFM` | Action Map for Active Stream Type of STREAM_NATIVE_HFM | Record | Record (41 direct fields) | `_jmMEYK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_MUTEX_PROMPT` | Action Map for Active Stream Type of STREAM_NATIVE_MUTEX_PROMPT | Record | Record (41 direct fields) | `_joGv8K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DTCP_PROMPT` | Action Map for Active Stream Type of STREAM_NATIVE_DTCP_PROMPT | Record | Record (41 direct fields) | `_jp6GwK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DTCP_CALL` | Action Map for Active Stream Type of STREAM_NATIVE_DTCP_CALL | Record | Record (41 direct fields) | `_jrolEK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DTCP_ECALL` | Action Map for Active Stream Type of STREAM_NATIVE_DTCP_ECALL | Record | Record (41 direct fields) | `_jtb74K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_ATCP_ECALL` | Action Map for Active Stream Type of STREAM_NATIVE_ATCP_ECALL | Record | Record (41 direct fields) | `_jvua4K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_RING` | Action Map for Active Stream Type of STREAM_NATIVE_RING | Record | Record (41 direct fields) | `_j1xYgK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DTCP_RING` | Action Map for Active Stream Type of STREAM_NATIVE_DTCP_RING | Record | Record (41 direct fields) | `_j3vucK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_ATCP_RING` | Action Map for Active Stream Type of STREAM_NATIVE_ATCP_RING | Record | Record (41 direct fields) | `_j5KqwK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_SPEECH` | Action Map for Active Stream Type of STREAM_NATIVE_SPEECH | Record | Record (41 direct fields) | `_j6ybYK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_PHN_VR` | Action Map for Active Stream Type of STREAM_NATIVE_PHN_VR | Record | Record (41 direct fields) | `_j8o1gK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_MIX_PROMPT` | Action Map for Active Stream Type of STREAM_NATIVE_MIX_PROMPT | Record | Record (41 direct fields) | `_j_mp8K3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_DTCP_MIX_PROMPT` | Action Map for Active Stream Type of STREAM_NATIVE_DTCP_MIX_PROMPT | Record | Record (41 direct fields) | `_kBDbcK3VEeOe_uWRKKMYzg` |
| `STREAM_NATIVE_HFM_WB` | Action Map for Active Stream Type of STREAM_NATIVE_HFM_WB | Record | Record (41 direct fields) | `_smLWEF99EeSMT4bpkrv4Pw` |
| `STREAM_NATIVE_PROJ_ALT_AUDIO` | Action Map for Active Stream Type of STREAM_NATIVE_PROJ_ALT_AUDIO | Record | Record (41 direct fields) | `_01xPIbXPEeikJZsd_WAfzw` |

### ROOMMODE (8)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `RoomModeDelayFrontLeftMap` | This is a supplier-specific calibration. Delay value for each room mode for front left. | EnumFloatMap | EnumFloatMap (5 direct fields) | `_BzdjQcWbEeOaCvydzCgwdA` |
| `RoomModeDelayFrontRightMap` | This is a supplier-specific calibration. Delay value for each room mode for front right. | EnumFloatMap | EnumFloatMap (5 direct fields) | `_BeoiwcWbEeOaCvydzCgwdA` |
| `RoomModeDelayRearLeftMap` | This is a supplier-specific calibration. Delay value for each room mode for rear left. | EnumFloatMap | EnumFloatMap (5 direct fields) | `_AeoeUcWbEeOaCvydzCgwdA` |
| `RoomModeDelayRearRightMap` | This is a supplier-specific calibration. Delay value for each room mode for rear right. | EnumFloatMap | EnumFloatMap (5 direct fields) | `_0G66wMWaEeOaCvydzCgwdA` |
| `RoomModeLevelAttenuationFrontLeftMap` | This is a supplier-specific calibration. RoomModes attenuation level for front left | EnumFloatMap | EnumFloatMap (5 direct fields) | `_pHIVUIjyEeOKJbstwtEFKg` |
| `RoomModeLevelAttenuationFrontRightMap` | This is a supplier-specific calibration. RoomModes attenuation level for front right | EnumFloatMap | EnumFloatMap (5 direct fields) | `_1ab6AYjyEeOKJbstwtEFKg` |
| `RoomModeLevelAttenuationRearLeftMap` | This is a supplier-specific calibration. RoomModes attenuation level for rear left | EnumFloatMap | EnumFloatMap (5 direct fields) | `_4DdxwYjyEeOKJbstwtEFKg` |
| `RoomModeLevelAttenuationRearRightMap` | This is a supplier-specific calibration. RoomModes attenuation level for rear right | EnumFloatMap | EnumFloatMap (5 direct fields) | `_7YEWEYjyEeOKJbstwtEFKg` |

### SINKLEVELCONTROLCALS (22)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `MinimumVolumeMap` | This is the map of minimum allowed volume index values for each volume group. | EnumIntegerMap | EnumIntegerMap (8 direct fields) | `_IJUX8HPfEeOrWuwMpf0tEg` |
| `MaximumVolumeMap` | This is the map of maximum allowed volume index values for each volume group. | EnumIntegerMap | EnumIntegerMap (8 direct fields) | `_gNJkYXPfEeOrWuwMpf0tEg` |
| `MinimumActivationVolumeMap` | This is the map of minimum activation volume index values for each volume group. | EnumIntegerMap | EnumIntegerMap (8 direct fields) | `_gdLPUHPdEeOrWuwMpf0tEg` |
| `VolumeGroupInitialDefaultsMap` | Initial default volume setting for each VolumeGroup. [CalDef v5; override v1] | EnumIntegerMap | EnumIntegerMap (9 direct fields) | `_AToSwCR6EeOFAcqdxEN3jw` |
| `SourceOffsetCalibrationMap` | Map of AudioStreamEnum audio streams for each audio source to the corresponding source offset in dB. [CalDef v6; override v1] | EnumFloatMap | EnumFloatMap (43 direct fields) | `_ATpg4CR6EeOFAcqdxEN3jw` |
| `SeparationGainCalibrationTable` | Separation gain table that contains the dB separation used on the MixPrompt sink. [CalDef v4; override v1] | FloatArray | FloatArray (64 direct fields) | `_ATqvACR6EeOFAcqdxEN3jw` |
| `SCVEnabled` | Enables or disables the SCV algorithm as well as hides/shows the SCV menu within the HMI. [CalDef v4; override v1] | Boolean | true | `_SzS6MHSWEeONqtLMgOmNHg` |
| `SCVVolumeCompensationFactorStepTable` | Speed Comp Volume - Volume Compensation Factor Step Index table. [CalDef v4; override v1] | IntegerArray | IntegerArray (5 direct fields) | `_ATqvASR6EeOFAcqdxEN3jw` |
| `SCVVehicleSpeedUpdateDelta` | This is the minimum delta change in vehicle speed required to trigger a new calculation of the Speed Compensated Volume algorithm [CalDef v4; override v1] | Integer | 1 | `_NEM0MHP4EeOq8K11VvtDWw` |
| `SCVVolumeCompensationFactorLevelScaleTable` | Volume Compensation Factor Level Scale table within the Speed Compensated Volume algorithm [CalDef v4; override v1] | FloatArray | FloatArray (5 direct fields) | `_ATrWECR6EeOFAcqdxEN3jw` |
| `SCVLevelScaleTable` | Table of Speed Comp Level scale multipliers relating the level scale to the SCV setting. [CalDef v4; override v1] | FloatArray | FloatArray (6 direct fields) | `_ATrWESR6EeOFAcqdxEN3jw` |
| `SCVVolumeBoostTable` | Speed compensation volume boost level table. [CalDef v4; override v1] | FloatArray | FloatArray (11 direct fields) | `_ATrWEiR6EeOFAcqdxEN3jw` |
| `SCVVolumeBoostSpeedTable` | Speed compensation volume boost speed table. [CalDef v4; override v1] | IntegerArray | IntegerArray (11 direct fields) | `_ATrWEyR6EeOFAcqdxEN3jw` |
| `SCVBassBoostTable` | Speed compensation bass boost level table. [CalDef v4; override v1] | FloatArray | FloatArray (11 direct fields) | `_ATrWFCR6EeOFAcqdxEN3jw` |
| `SCVBassBoostSpeedTable` | Speed compensation volume bass boost speed table. [CalDef v4; override v1] | IntegerArray | IntegerArray (11 direct fields) | `_ATrWFSR6EeOFAcqdxEN3jw` |
| `SCVChimeBoostTable` | Speed compensation chime boost level table. [CalDef v3; override v1] | FloatArray | FloatArray (11 direct fields) | `_ATrWFiR6EeOFAcqdxEN3jw` |
| `SCVChimeBoostSpeedTable` | Speed compensation volume chime boost speed table. [CalDef v3; override v1] | IntegerArray | IntegerArray (11 direct fields) | `_ATrWFyR6EeOFAcqdxEN3jw` |
| `MaxChimeVolumeStep` | The volume index of the maximum chime level | Integer | 57 | `_ATr9ICR6EeOFAcqdxEN3jw` |
| `MaxMixPromptLevel` | The maximum level of the mix prompt sink. This value is defined in order to insure that mix prompts are never distorted and remain intelligable. | Float | 0.0 | `_ATskNCR6EeOFAcqdxEN3jw` |
| `MinAudibleFeedbackLevel` | The minimum level of the AudibleFeedback sink. [CalDef v6; override v1] | Float | -22.0 | `_ATskNSR6EeOFAcqdxEN3jw` |
| `MaxAudibleFeedbackLevel` | The maximum level of the AudibleFeedback sink. [CalDef v4; override v1] | Float | -6.0 | `_ATskNiR6EeOFAcqdxEN3jw` |
| `AudibleFeedbackBoostLevel` | The audible feedback boost level above the Mutex sink [CalDef v5; override v1] | Float | 20 | `_ATskNyR6EeOFAcqdxEN3jw` |

### WIFIINFO3 (2)

| Calibration key | CalDef description or labeled fallback | Type | LTZ value | CalID |
|---|---|---|---|---|
| `WiFiP2PDeviceName` | WiFiP2PDeviceName is the name of the Wi-Fi Module in the P2P mode. It shall be the same for the P2P Group Owner and Group Client roles. WiFiP2PDeviceName depends on the vehicle model and brand. The WiFiP2PDeviceName shall be the same as the Bluetooth_Module_Device_Name. [CalDef v3; override v1] | String | string (see source XML) | `_dQX7gMTDEeOzhbtZfiZNyg` |
| `WiFiClientDeviceName` | Name of the Wi-Fi Module in the Wi-Fi Client Mode (STA mode). The WiFi Client Device Name shall be dependent on the vehicle model and brand. The WiFiClientDeviceName shall be the same as the Bluetooth_Module_Device_Name. [CalDef v3; override v1] | String | string (see source XML) | `_wbtpoMSwEeOL876Etsd7Eg` |
