# A11 CSM Calibration Slot Map

**Scope:** the full UDS-slot (02–0F) → part-number → content map for the stock A11 LTZ CSM
calibration set of the gminfo37 radio (`0x80`). Fourteen signed CSM calibration containers, one
per slot, plus a fifteenth file (`85577468`) that is the SPS programming-sequence utility, not a
calibration. This doc gives the slot assignment, the per-slot override count / type breakdown, the
named settings resolved through the local CalDef database, and the evidence for the slot-encoding
method. Compiled 2026-11-21.

**Does NOT live here:**
- The complete 404-entry slot04 (`85045371`) calibration-key catalog is owned by
  [`calibration_glossary.md`](calibration_glossary.md); it is pointed to, not restated (see
  slot 04 below).
- The custom-write trial log, the signed-container RSA/SHA verification trace, the CAN613/614
  scoped-VIP-RAM-write path, and the Type4-vs-calibration-value distinction are owned by
  [`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) ("DTW")
  and [`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- Byte-level checksum/hash/container-edit mechanics for specific edits are owned by
  [`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) ("CHS").
- The EEPROM/SBI layout and the refutation of the "`85783460` resets the SBI" claim are owned by
  [`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md).

**Related:** `../../tools/mdi2_client/mdi2/ltz_reference_manifest.py` (the pinned per-slot
`TrustedContainer(slot, part, sha256)` manifest), `../../tools/mdi2_client/mdi2/calibration_payloads.py`
(the loader that reads `slot = data[3]`), `../../evidence/dps-logs/A11_CSM_x80.Txt` (DPS GCI module
readback), `../../tools/bench/tis2web.txt` (DPS Archive Creator part list).

## Resolution method (stated once; it applies to every slot below)

Each container is `outer gzip → CSM container → inner gzip at offset `0x368` → `CalOvride` XML`. The
override XML carries only `CalID` + `Version` + one typed value element; **it contains no
calibration names**. Every name, group and description below was resolved by **exact CalID match**
against the local GIS-646 CalDef database (Info3.7/3.8 V7.0.8, 19 April 2023, in
`../../reference/GIS-646_CalDef_Database_Info3.7_and_Info3.8_V7.0.8_19April2023/` (not bundled: `reference`)),
cross-checked against the `AllCalSets`/`EnumSets` tables of the Y177/Y181 `CalSets.db` emulator
copies. CalDef text is manufacturer documentation, not a live behavior test. Two standing caveats
from the source extraction are **not** upgraded here:

- **Version skew.** The 2023 CalDef database and the override `Version` fields frequently differ.
  Where they differ the description may not describe the exact installed revision. In most
  containers the override is the older of the two; in slot 0A (`87846368`) 12 of 23 overrides are
  *newer* than the 2023 CalDef, i.e. the local CalDef DB predates that container's definitions —
  CalID/name/type still match exactly, but descriptions and enum labels for those 12 may be stale.
- **Header tag `AA`/`AB`.** The two ASCII bytes at `container[0x362:0x364]` (the "alpha" / design-level
  code) match the alpha column of the DPS GCI readback for every container, but the meaning of
  `AA` vs `AB` is **not established** by this data.

Values below are the stock LTZ overrides as extracted. "CalDef default" means the value in the
CalDef file, not a live readback. Do not infer undocumented units or semantics, and do not change
diagnostic masks or audio/safety settings on the strength of a name alone.

## Slot summary

| Slot (hex) | SPS/GCI dec | Part | Alpha | Overrides | Content area (one line) |
|---|---|---|---|---|---|
| 02 | 2 | `87863250` | AA | 21 | Navigation/fuel-type config and the MFC steering-wheel switch map |
| 03 | 3 | `84517309` | AA | 0 | Empty override payload (valid, correctly digested, no overrides) |
| 04 | 4 | `85045371` | AA | 404 | UI / home-screen / chime / audio / distortion / diagnostics — owned by `calibration_glossary.md` |
| 05 | 5 | `87846416` | AB | 194 | Broad HMI policy: driver-workload lockout levels, projection (CarPlay/AA), tuner, region/language, server endpoints |
| 06 | 6 | `87846371` | AA | 34 | Speech-recognition configuration plus 10 `.vtc` GMVT tuning files |
| 07 | 7 | `85783460` | AA | 34 | Bluetooth profile enables plus 21 `.scd` hands-free audio tuning files |
| 08 | 8 | `87846432` | AA | 30 | Rear-vision-camera geometry/intrinsics plus screen resolution |
| 09 | 9 | `87846376` | AA | 48 | Diagnostic masks, GNSS dead-reckoning config, system-state timers |
| 0A | 10 | `87846368` | AA | 23 | HVAC/climate touch-screen UI plus air-quality UI |
| 0B | 11 | `86292118` | AA | 42 | Connectivity/telematics switches, GIS641 DTC masks, OMA-DM timers (supersedes `87846390`) |
| 0C | 12 | `85102312` | AB | 20 | Tuner / SXM / HD / DAB feature set plus antenna and voice-recognition DTC masks |
| 0D | 13 | `87846384` | AB | 19 | Trailering and trailer-camera features, rear-seat entertainment, DTC masks |
| 0E | 14 | `84517418` | AA | 0 | Empty override payload (inner XML byte-identical to slot 03) |
| 0F | 15 | `87846380` | AA | 114 | Vehicle-specific parametric EQ (per-channel acoustic tune) |
| — | 0 | `85577468` | — | n/a | Not a calibration: SPS programming-sequence utility (see below) |

Every CalID in every container resolved to a real GM name; **no container has an unresolved /
opaque CalID**. No CalID appears in more than one container (each CalID is assigned to a single
slot). No VIN, serial, or trim-name string appears inside any container's XML; what the containers
carry are feature/equipment-presence and configuration values, not identity tokens.

## Per-slot detail

### Slot 02 — `87863250` (AA, 21 overrides: 15 Enumeration, 5 Boolean, 1 Integer)

Navigation and fuel-type configuration plus the Multi-Function Controller steering-wheel switch
map. Fuel markers are consistent with a gasoline vehicle: `FuelType` = 1 (`FuelType_Unleaded`),
`VEHICLE_FUEL_TYPE_PETROL` true, `VEHICLE_FUEL_TYPE_DIESEL` false, `DEFAULT_POI_FUEL_STATION` = 0
(`Gasoline`). The MFC map sets switches 1–6 to Back / Phone / Navigation / Audio / SeekUp /
SeekDown with switches 7–8 and all indicators Unused (all equal to CalDef default).
`ENABLE_REVEALONAPPROACH` = 0 (OFF, CalDef default 1); navigation app and Predictive Cards enabled;
`GCWR` = 11111 (CalDef default 99999; the CalDef gives no unit, so the number is left
uninterpreted). Nothing VIN-specific.

### Slot 03 — `84517309` (AA, 0 overrides)

A valid, correctly digested CSM container whose inner XML is a self-closing
`<calovride:CalOvrideFile/>` root with **no overrides** — the module keeps its built-in CalDef
defaults for every key. No CalIDs are catalogued because none exist in the file. The container
differs from slot 0E (`84517418`) only in the slot bytes, the digest, the 256-byte OTA-only RSA
field, and the part-number low bytes; the inner XML is byte-identical between the two.

### Slot 04 — `85045371` (AA, 404 overrides)

The stock LTZ slot04 container: UI, home-screen application visibility/ordering, chime
configuration, audio routing/levels, distortion limiting, faceplate buttons, and diagnostic masks.
**Its full 404-entry catalog is owned by [`calibration_glossary.md`](calibration_glossary.md) and is
not duplicated here.** A fresh 2026-11-21 re-extraction of the live container was compared
programmatically against every row of that glossary: 404 rows vs 404 XML entries, identical CalID
sets, 0 name/type/group mismatches, 0 value mismatches across all 161 scalar values and enum
labels, and the glossary's "133 CalDef versions equal the override version" count reproduced. The
glossary describes this container accurately; no discrepancies were found. Its decompressed-container
SHA-256 equals the `LTZ_REFERENCE` pin for slot 4.

### Slot 05 — `87846416` (AB, 194 overrides: 94 Enumeration, 50 Integer, 41 Boolean, 8 String, 1 EnumIntegerMap)

The broadest container: an HMI-policy and connectivity set spanning ~30 CalDef groups. By name, a
large majority of entries are driver-workload / lockout levels across the GIS500–GIS539 UI groups
(including all 21 `GIS539_TrailerAppUI` entries); the remainder includes 13 CarPlay/Android Auto
projection flags (`GIS337_ConsumerDeviceProjection`: e.g. `Apple_CarPlay_enableWireless` true,
`AndroidAuto_enableWireless` true, various fidelity/keypad/content sub-flags), 46 AM/FM tuner values
plus 14 HD Radio (`GIS605`) and 1 SXM, and 4 language/regionalization entries.

Region/market markers (market-specific, not vehicle-specific) are present: `COUNTRY_CODE` = 49
(`UNITED_STATES`), `REGIONS` = 0 (`GMNA`), `DEFAULT_SYSTEM_LANGUAGE` = 0 (`ENGLISH_US`),
`Onstar_Regional_Brand_HMI_Logo` = 1 (`North_America`), and three of 36 target languages enabled
(US English, Canadian French, North-American Spanish); North-American tuner band plan. Eight String
entries carry server endpoints verbatim (`vehicle.api.gm.com` on ports 20443/20445,
`gm.secure.force.com`, `gminfo3-am-ncs-ssl.gm.nuancemobility.net`). Header tag is `AB`. Note the
prior one-line summary "Android Auto / Apple CarPlay connectivity settings" in the external
`EEPROM_CALIBRATION_MAPPING.md` covered only a small part of this container's 194 entries.

### Slot 06 — `87846371` (AA, 34 overrides: 10 BinaryFile, 10 IntegerArray, 9 Boolean, 3 Integer, 1 EnumIntegerMap, 1 Enumeration)

Speech-recognition configuration: disambiguation thresholds, per-language server-ASR enables,
server/embedded confidence-threshold arrays, maximum user speech time, voice barge-in, a
per-language static-text map, and 10 `GM_SR_TuningFiles` BinaryFile entries. The 10 BinaryFile
payloads are all `.vtc` "GMVT tuning file" blobs (default VA driver/passenger/mix, Android Auto,
CarPlay Siri, Bluetooth Siri/VR); each `Length` matches the base64-decoded size and each `Checksum`
equals the CRC-32 of the decoded bytes, but the internal `.vtc` format was not decoded. **Market
hint (inference, the data names no market):** server ASR is enabled for US English, Canadian French,
Mexican Spanish and Mandarin, and disabled for the EU languages — a language set that fits a
North-American calibration.

### Slot 07 — `85783460` (AA, 34 overrides: 21 BinaryFile, 12 Boolean, 1 Integer)

Bluetooth profile/feature enables plus hands-free audio tuning. All 11 Bluetooth booleans are true
(HFP, A2DP, AVRCP, PBAP, MAP, DIP, SPP, PAN, WBS, in-band ringing, and the
`BluetoothFeatureEnables`-grouped `K_AUTO_FAN_SPEED_REDUCTION_ENABLED` — whose own description
actually concerns HVAC fan-speed ODI calls). `ENABLE_CALL_TIMERS` true;
`IGNITION_OFF_IN_CALL_VIEW_DELAY` = 0 (CalDef default 3000). The 21 BinaryFile entries are all
`.scd` files in CalDef group `HandsFree`, `SSE_*` names, CalDef-described as "Default voice
parameters for app based VoIP calling" or "Tuning Parameter for SSE_HF_GM_INFO3_<use case>" (BT
telephony NB/WB, CarPlay Tel/FaceTime NB/WB/SWB wired and WiFi, Android Auto WB, OnStar
Advisor/eCall WB, 48 kHz downlink variants); each `Length` matches the decoded size (472–708 B,
11,712 B total) and each `Checksum` equals the CRC-32 (several payloads are byte-identical under
different names). The internal `.scd` format was not decoded, and the "SSE = Speech Signal
Enhancement / echo cancellation" gloss from older notes is **not** stated in the CalDef text — the
CalDef supports only "hands-free voice/tuning parameters." All 34 CalIDs resolve exactly; see the
correction to `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` recorded below.

### Slot 08 — `87846432` (AA, 30 overrides: 20 Integer, 5 Enumeration, 3 Boolean, 2 IntegerArray)

Rear-vision-camera (RVS) geometry and the display resolution. 26 `FRONTREARCAMERASTATIC` entries:
smart-tow feature, UPA zone type and icon pixel arrays, RCTA icon positions, camera
intrinsics/extrinsics (distortion coefficients, focal length, optical offsets, rotation),
hysteresis speeds/timers, steering geometry (wheelbase, rear-axle offset, steering
ratio/saturation), guideline availability, and `RVS_PRESENT_STATUS` = 2
(`PRESENT_VPM_CAMERA_PROCESSING_MODULE`, CalDef default 1); plus the home-screen camera-app enable,
two "wrong camera installed" DTC masks, and `SCREEN_RESOLUTION` = 4 (`SIZE_2400_BY_960`, CalDef
default 2 `SIZE_1280_BY_768`). `SCREEN_RESOLUTION` is the value DTW's 2026-11-17 trial changed to 2
and rolled back after display tearing. Geometry integers carry no units in the file; the CalDef
hints are reproduced but not extended. Decompressed-container SHA-256 equals the `LTZ_REFERENCE`
pin for slot 8.

### Slot 09 — `87846376` (AA, 48 overrides: 41 Boolean, 6 Integer, 1 Enumeration)

Diagnostic masks, GNSS dead-reckoning configuration, and system-state timers. 20
diagnostic-mask/counter entries (`GIS621` Global A: 9, `GIS641` Global B: 11, covering wireless
charger, Ethernet bus, cluster-link and display DTCs); 21 `GNSS_DR` entries (constellations GPS and
GLONASS on, BeiDou and Galileo off; sensor availability/utilization flags; `SBAS_DGPS` = 0 `NONE`;
`LOC_SHFT` false); 3 `GIS618_SystemState` timers/flags including `VIN_RELEARN_EN` true; 2 `GIS507`
settings; a welcome-message value; and `ValetMaskMenu`. `VIN_RELEARN_EN` and `DID_MASK_2F`
*concern* VIN handling but are configuration flags, not VIN data. The external
`EEPROM_CALIBRATION_MAPPING.md`'s "valet mode, TTS speed, welcome message, timeouts" one-liner
covers only a minority of the 48 entries.

### Slot 0A — `87846368` (AA, 23 overrides: 13 Boolean, 8 Enumeration, 2 Integer)

HVAC/climate touch-screen UI (`GIS550_ClimateTouchScreenUI_GlobalB`, 19 entries) plus air-quality
UI (`GIS551_AirQualityUI`, 3) and one home-screen air-quality switch. Several values describe
installed climate hardware: `KeHVC_Cnt_CfgNumOfFrontZones` = 2 (`Dual_Front_Zone`),
`Number_of_Rear_Temp_Zones` = 0, `Rear_Climate_Application_Available` false,
`Rear_Blower_Control_Available` false, `Air_Conditioning_Compressor_Type` = 1
(`NOT_Equal_to_None`), `HiVoltCoolHtrPresent` false, `Maximum_FanSpeed` = 8. These are
equipment-content markers, not a trim name. `APPLICATION_HOMESCREEN_AIRQUALITY_ENABLED` false is
consistent with RPO `USK` (Air Quality Sensor) absent. This is the container with the reversed
version skew noted in the method section (12 of 23 overrides newer than the 2023 CalDef).

### Slot 0B — `86292118` (AA, 42 overrides: 37 Boolean, 5 Integer)

Connectivity/telematics feature switches plus diagnostics and remote-programming timers. Content:
OnStar wrapper launch points, WiFi / WiFi P2P, data and location services, connected/local profiles,
global server-ASR switch, App Shop enables; 19 `GIS641` DTC-mask booleans (WiFi antenna, telematics
license-compliance, Ethernet Bus 4, cellular mic, GPS coax antenna); 3
`GIS668_RemoteOMADMServerInterface` retry timers and 2 `GIS887_RemoteProgrammingHMI` timers.
Feature-presence values such as `APPLICATION_HOMESCREEN_APPSHOP_ENABLED` false,
`APP_SHOP_SERVER_ENABLED` false, `APPLICATION_HOMESCREEN_ONSTAR_ENABLED` true describe software
content, not identity. 41 of 42 CalIDs are present in the emulator `CalSets.db` (the 42nd is absent
there, not contradicted). See the slot 0B history note below — this part superseded `87846390`.

### Slot 0C — `85102312` (AB, 20 overrides: 18 Boolean, 1 Enumeration, 1 IntegerArray)

The radio/tuner feature container: DAB/SXM/HD source-mode icons, speech-recognition radio domains,
HD Radio activation, AM/FM secondary-antenna type and phase diversity, DAB enable, SXM enable plus
default presets, and the antenna/XM/voice-recognition DTC masks that accompany those features.
Effective configuration: SXM on, HD and DAB off, FM antenna 2 not connected. `SXM_Enabled` = true
(CalDef default false) is the single value flipped in DTW's SXM-disable experiments. **Stock slot 0C
has exactly these 20 overrides** — see the CarPlay/Android Auto correction note below.

### Slot 0D — `87846384` (AB, 19 overrides: 13 Boolean, 5 Enumeration, 1 Integer)

Trailering and trailer-camera features plus rear-seat entertainment and DTC masks. `VEHICLE_TYPE` =
1 (`Full_Size_Truck`); `TraileringAppType` = 2 (`FULL`); rear and interior trailer camera, rear
trailer guidelines, load monitoring and ESBZA HMI all true; `TRAILER_HEIGHT_MAX` = 100 (CalDef
default 36; CalDef says inches); transparent-trailer and jackknife features at default; rear-seat
entertainment (`ENABLE_APPLICATION_RSE`, `RearSeatOverEthernet`) false; home-screen Video app false;
`LVM_TLIN_Node_Available` false; three `GIS641` B1A21 Ethernet-Bus-5 DTC masks false. This describes
a trailering-equipped full-size-truck configuration; nothing VIN-specific. This container shares no
CalIDs, groups or BinaryFile content with slot 07 (`85783460`) — their historical pairing under the
old "encrypted EEPROM reset payload" claim reflected the claim, not the data.

### Slot 0E — `84517418` (AA, 0 overrides)

A second empty override container. The inner XML is byte-for-byte identical to slot 03
(`84517309`); the two differ only in the slot bytes, digest, OTA-only RSA field, and part-number low
bytes. Slots 3 and 14 therefore receive the same empty payload, packaged separately.

### Slot 0F — `87846380` (AA, 114 overrides: 66 Float, 36 Integer, 12 Enumeration)

All 114 entries are in the single CalDef group `VehicleSpecificEqualization`: a per-channel
(LF/RF/LR/RR) 7-band parametric EQ (center frequency, Q factor, boost/cut, per-band function
selection), per-channel high-pass frequency/order/Q, per-channel level adjust, and two
`VSE_PARAM_EQ_F_HR`/`VSE_PARAM_EQ_R_HR` values. The earlier external inventory's per-type count
("36 int, 12 enum") omitted the 66 Float entries; the corrected breakdown is above.

A follow-up pass (three independent agents: channel mapping, trim/tier variance, runtime-consumer
trace) resolved most of what the family/parameter-level summary above left open. Full working
notes, filter-coefficient-level detail, and the cross-vehicle comparison table are kept external at
`module_map/87846380_channel_mapping.md`, `87846380_trim_variance.md`, and `87846380_runtime_path.md`
(not checked in here, per this doc's provenance convention); the following is the distilled result.

**Channel identity (directly documented, not just inferred from naming).** LF/RF/LR/RR are the
four door speakers — left-front, right-front, left-rear, right-rear. GM's own CalDef text names
them this way, and the shipped Y175 vendor audio service `/vendor/bin/vehicleaudiocontrol`
(disassembled; source file `vse.cpp`) maps LF/RF/LR/RR to internal channels 1–4 identically. The
ALLDATA Speakers (U95/UQF) schematic gives the matching radio-connector pins/circuits for each of
the four door speakers (plus dash speakers in parallel on UQF). The physical TI TAS6424 amplifier's
own internal channel ordering was not traced — that mapping step is inference, not confirmed.

**Runtime consumer (Y175 vendor image, from disassembly — not observed on a live radio).**
`vehicleaudiocontrol` reads the calibration DB values, converts headroom+level-trim into per-channel
gain, and sends one high-pass filter plus 7 EQ bands per channel over HIDL
(`IAmpControl::configPEQBand`) to the Harman audio HAL (`vendor.gm.audio@1.1-impl.so`), which routes
through `libhmampcontrol.so` / `ampcontrolplugin.json` to `Dirana3Plugin` in `libhmdirana3layer.so`.
That layer computes biquad coefficients on the main processor and writes them into the audio DSP's
coefficient memory via I²C (`/dev/i2c-3`). The hardware parts list elsewhere in this repo names that
DSP as an NXP SAF7751; the software side only ever says "Dirana3" — linking the two is inference,
not a confirmed identity. No GHS-host component, VIP_APP (either Y175 or Y181), `calserviced`, or
Java `info3` constant reads these values — each was checked and ruled out as a consumer.

**It is not applied on this truck.** `vehicleaudiocontrol` only sends the VSE values at boot/resume
when the calibration DB's `AmplifierType` is `InternalAmplifier` (0) or `RemoteANCModule` (2); it
explicitly skips this step for `AnalogRemoteAmplifier` (1) and `BosePremiumAmplifier` (3). Slot 04
(`85045371`) sets `AmplifierType` = 3 on this LTZ/UQA (Bose) truck — confirmed against a live
calibration database recovered from the Y175 bench radio's own eMMC dump. The radio's own
speaker-driver pins are not even wired on UQA; the separate Bose amplifier drives the same door
speakers with its own tuning. The two independent agents (channel-mapping and runtime-path) reached
this "skipped on Bose" conclusion by different methods (code-path gating check, and live-DB
readback) without coordinating, which is why it's carried here as confirmed rather than inferred.
The CalDef group's own description already stated it is scoped to "systems without a custom remote
amplifier" — this is now directly verified, not just read off the spec text.

**Trim/tier variance.** The content is NOT LTZ-specific: SPS logs for both an LTZ and a High
Country session program byte-identical `87846380` into slot 15 (only slots 02/04/05 differ between
those two trims — consistent with the rest of this doc). A second vehicle's calibration set (a
different archive in the raw workspace; VIN withheld) carries a different part number in slot 0F
with 82 of 114 values different, for a Chevrolet/non-NA-market/non-Bose (`AmplifierType`=0) vehicle
— so slot-0F content does vary by vehicle/market/amplifier configuration, just not by GM-truck trim
level specifically. No base-audio (non-Bose) Silverado reference exists anywhere in the corpus, so
whether a non-Bose Silverado gets a different tune (and actually uses it) remains undetermined.
87846380's values are a real custom tune, not factory defaults (97 of 114 differ from the CalDef
defaults) — authored for a configuration this specific truck does not run in.

**Still open:** TAS6424 physical channel ordering; the "UQF" rear-door wiring-flag meaning; whether
Y177 gates `AmplifierType` the same way Y175/Y181 do (binary-identical between those two, Y177
unchecked); how a stored high-pass Q of `0.0` is handled; the DSP coefficient memory layout (would
need NXP documentation); and direct confirmation from a live radio rather than disassembly alone.

## The 15th file — `85577468` (SPS programming utility, not a slot)

`85577468` is **not** a CSM calibration container and has no UDS calibration slot. Its decompressed
body (1818 bytes) begins `00 00 00 00 05 19 ce fc 41 41 …` with no `CSM\0` magic, no inner gzip, and
no `CalOvride` XML — it is a GM SPS/DPS utility (programming-interpreter) script, listed by SPS as
`#0: 0/85577468/817` (module 0) and by `tis2web.txt` as `A11 00 N/A 85577468`.
`MDI2_RAW_UDS_BYPASS_GUIDE.md` already calls it "the cached LTZ utility."

Structurally it is a header, 109 fixed 16-byte step records, and a trailer. Its step records
reference UDS services by their positive-response codes (`27` SecurityAccess, `10`
DiagnosticSessionControl, `34`/`36`/`37` RequestDownload/TransferData/RequestTransferExit, `22`
ReadDataByIdentifier, `2E` WriteDataByIdentifier, `31` RoutineControl, `11` ECUReset). The control
flow is: a SecurityAccess + session-setup sequence, then **14 download blocks**, one per data index
`02`…`0F` in order (each a `34`/`36`/`37` triple), then a readback of DID `F0F0`; a second sequence
writes DIDs `F198`/`F199`/`F190` (repair-shop code / programming date / VIN) and issues a hard
`ECUReset`. The trailer carries a 14-entry list of indices `02`…`0F` — the "14-slot list." This is
the programming sequence that drives the 14 slot downloads and verifies, which is why there are 15
part numbers for 14 calibration slots. Field-level meanings of several interpreter ops (`01`, `53`,
`e0`, `ee`, `fb`–`ff`) and the trailer words `0249`/`039b` are **not established**; the slot→part
pairing of its download indices is inferred by matching the two numbering schemes, since the utility
names no part numbers. No values for the F198/F199/F190 writes are stored in the file (the tool
presumably supplies them at runtime).

## Slot-encoding method and its cross-validation

The slot number is carried **inside the signed CSM header**, not in the XML: `container[0x03]` holds
the slot, repeated at `container[0x35F]`; `container[0x362:0x364]` holds the ASCII alpha code; the
big-endian u32 at `container[0x364]` equals the part number; ASCII `Infotainment` sits at
`container[0x3E]` in every container (so it names the module class, not the slot). The header begins
`03 01 00 <slot> 00 00 'CSM\0'`.

**The byte-offset *meaning* is inferred — no GM tool documentation confirms that `container[0x03]`
is "the slot" — but the slot values it produces are corroborated independently and by two different
methods:**

1. **Header-byte reading vs. the loader.** `container[0x03]` is the exact field the owner's loader
   uses (`tools/mdi2_client/mdi2/calibration_payloads.py`: `slot = data[3]`, which requires exactly
   one container per slot 02–0F), and each container's decompressed SHA-256 matches its pinned
   `TrustedContainer(slot, part, sha256)` row in `tools/mdi2_client/mdi2/ltz_reference_manifest.py`
   byte-for-byte.
2. **External logs, independent of the header.** The same slot→part set appears in the SPS
   programming log
   `misc/Aug24_session/spsCacheInternal/26_HC_A11/sps2.log` (lines ~1849–1863, `#n: <module>/<part>/<size>`
   format, file sizes matching the cached gzip sizes byte-for-byte); in the DPS Archive Creator part
   list `tools/DPS_Archive_Creator_V2/tis2web.txt`; and in the DPS GCI module readback
   `DPS_All_Module_Read/2025DEC30/read_*/GCI_0x80_*.txt` (also mirrored in this repo at
   `../../evidence/dps-logs/A11_CSM_x80.Txt` (not bundled: `evidence/dps-logs/A11_CSM_x80.Txt`), whose MOD
   column is decimal 02…15 = 0x02…0x0F). The alpha codes `AA`/`AB` in the header match the alpha
   column of that readback for every container.

These were produced by multiple independently-run agents, cross-checking the header byte against the
logs above and against this repo's own pinned manifest. The three slots that were already known
before this round (04, 08, 0C) agree with every source. The byte-offset interpretation remains an
inference; the slot assignment it yields is well corroborated.

## Slot 0B part-number history (`87846390` → `86292118`)

The DPS GCI reads (DPS PC clock stamped 02/18/24, folder `2025DEC30`),
`../../evidence/dps-logs/A11_CSM_x80.Txt` (not bundled: `evidence/dps-logs/A11_CSM_x80.Txt`),
`tools/bench/tis2web.txt` and the `icloud_diag` copy all record slot 11 as **`87846390` AB** — an
*older* part. By the 2026-07-07 SPS session (VIT1 readback) the radio already reported `86292118` in
that position, and SPS reprogrammed `86292118` there; the current `A11_extracted` cache (dated
Dec 30 2025) already contains `86292118`. So `86292118` superseded `87846390` in slot 0B at some SPS
programming in between; the exact date is not proven. **No local copy of `87846390` exists**, so it
could not be catalogued — only the current occupant `86292118` is detailed above. Note this is also
why `tools/bench/tis2web.txt` in this repo still lists the pre-update `87846390` for slot 11.

## Correction: no CarPlay / Android Auto override in stock slot 0C

The Apple CarPlay (`Enable_Application_Apple_Carplay`, `_vZTHQMZZEeOEzdA9o_rOxw`) and Android Auto
(`Enable_application_google_Automotive_link`, `_1pZzYMZZEeOEzdA9o_rOxw`) feature-enable overrides
described in DTW's
[2026-11-16 CarPlay/Android Auto trial](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-carplay-and-android-auto-custom-calibration-accepted)
are **not present in the stock slot 0C container** (`85102312`). Genuine stock slot 0C has exactly
the 20 overrides listed above, all in the radio-tuner / SXM / HD / DAB / antenna /
speech-recognition domain. The two projection overrides were **added** to a custom 1478-byte
candidate in that trial (version-3 Booleans, both set false); they do not exist in the 1457-byte
genuine container. The 2026-11-17 full stock LTZ restoration put the genuine 20-entry container
back. (The projection feature-enable CalIDs themselves are defined in `GIS513_DeviceProjection`; in
the stock set, the projection *policy* flags that do exist live in slot 05's
`GIS337_ConsumerDeviceProjection` group, which is a different group from the `GIS513` feature
enables.)

## Live storage: the `calibration` eMMC partition and `CalSets.db`

A bench eMMC dump (`emmc_user_wifi.bin`, GPT-partitioned) has a standalone 16 MB partition named
`calibration` (not folded into `super`/vendor), separate from the OTA-delivered `SOC_VENDOR` image —
calibration updates and full firmware/vendor-partition updates are two different update paths onto
two different storage locations. Its ext4 filesystem (volume name `mnt/vendor/calib[ration]`) was
captured mid-use ("needs journal recovery"); replaying the journal (`e2fsck -fy`) against a working
copy — never the original dump — produced a clean, consistent filesystem with no further repairs
needed, and `debugfs` (no native macOS ext4 mount) pulled the contents read-only.

**Directory layout on disk:**
- `/database/CalSets.db` (+ `-journal`) — the live calibration database, see below.
- `/applied_overrides/<part>.<alpha>.<slot-decimal>.cmod` — exactly 14 files, one per slot. Decimal
  slot numbers in these filenames (`.03`, `.04`, … `.15`) independently confirm the header-byte slot
  map above — a third, fully independent confirmation after the header bytes and the SPS logs.
- `/overrides` — present, empty on this dump.
- Raw `strings` across the *unallocated* space of the partition image (before journal replay) turned
  up three part-number-shaped fragments (`85102233`, `88102305`, a partial `…3140000`) that do **not**
  correspond to any of the 15 known containers or to any live file in `applied_overrides/` — leftover
  remnants of deleted/overwritten inodes, not current content. Not chased further.

**The `.cmod` format strips the signature, keeps the payload.** Each file is a 14-byte identity
header (slot number, alpha code, a short checksum field — no RSA/signer-record material) directly
followed by the *same* gzip stream that sits at offset `0x368` in the raw signed SPS container. Once
a container is accepted and locally cached, the heavy signature apparatus is dropped; the calibration
payload itself is not re-encoded.

**Result: the applied payload is byte-for-byte identical to the stock containers, 14/14.** Decompressing
all 14 `.cmod` files and hashing the inner XML reproduces the exact inner-XML SHA-256 already recorded
for every slot in this document — including slot 04's full 594,178-byte / 404-entry XML
(`d0ce7db9…`) and slot 0F's 114-entry VSE table (`5f119c9c…`). No adjustment, truncation, or
re-encoding at this layer; this bench unit is currently running the plain stock LTZ set across all 14
slots.

**`CalSets.db` itself is a different, expanded representation — not a mirror of the override XML.**
Its `AllCalSets` table holds **2,574 rows**: every CalDef-defined calibration on the platform (not
just the ones in the 14 slots), each resolved to a human-readable `CalName`/`CalDefFileName` plus
type, min/max, array length and enum reference — fields the opaque-CalID override XML never carries.
An `OverRiden` column records which slot owns a row: `OverRiden=0` for the 1,592 rows left at their
untouched base-calibration default, and `OverRiden=<slot>` for the rest, with per-slot counts matching
the override counts above exactly (`OverRiden=4`→404 rows, `=15`→114, `=12`→20, `=8`→30, `=5`→194,
etc.). So: the **delivery/wire format (14 signed containers) is a 1:1 mirror; the runtime format (one
merged table covering the whole platform, with resolved names and an ownership tag) is the
expanded/decompiled one.** These are two layers of the same system, not competing descriptions.

**Live values confirm the stock-restoration state directly, not just by inference:**

| CalName | Live value | `OverRiden` |
|---|---|---|
| `SXM_Enabled` | `1` (true) | `12` (slot 0C) |
| `Enable_Application_Apple_Carplay` | `1` (true) | `0` — base default, **not** slot-owned |
| `Enable_application_google_Automotive_link` | `1` (true) | `0` — base default, **not** slot-owned |
| `SCREEN_RESOLUTION` | `4` (2400×960) | `8` (slot 08) |

This bench unit is currently running fully stock calibration: SXM enabled, stock screen resolution,
and the CarPlay/Android Auto rows showing as plain platform defaults rather than slot 0C overrides at
all — consistent with (and a second, independent confirmation of) the 2026-11-17 full stock LTZ
restoration superseding the November custom trials; see the CarPlay/Android Auto correction above.

**Two loose ends from this pass, flagged rather than resolved:**
- 12 of the 14 `.cmod` files carry a 17-Nov-2026 mtime (matching the documented restoration date);
  slots 08 and 0C's files still carry the original 26-Jun-2024 factory mtime despite both having gone
  through custom edits and restoration per the trial log. Content is confirmed stock either way; why
  those two files' mtimes weren't bumped is unexplained (possibly a dedup-on-identical-content write
  path, not confirmed).
- Slot 0B (`86292118`) shows 41 `OverRiden` rows live vs. 42 entries in the earlier raw-container
  catalog above — a 1-entry discrepancy, not run down.

## Partition-wide sweep: no recoverable content outside the known 14 slots, but real history in deleted filenames

A follow-up pass checked whether the `calibration` partition holds any calibration content, feature
flag, or value not already accounted for above. Two different questions, two different answers:

**Recoverable payload: nothing new.** Every gzip-magic-prefixed byte sequence in the full 16 MB image
was located and decompressed (16 found total). All 16 hash to one of the stock inner-XML SHA-256
values already recorded in this document — no exceptions. Slots 08 and 0C each have **two** physical
copies of their own byte-identical stock payload sitting in different blocks (a second, independent
explanation for their stale-mtime oddity above: the content was evidently rewritten at some point
without the directory entry's mtime being bumped, not a sign the two copies ever differed). `CalSets.db`'s
three other tables (`SubSets`: 4,563 rows of array/composite field-layout metadata; `EnumSets`: 1,350
rows of enum labels; `ModuleData`: 14 rows, a third independent confirmation of the slot map, with a
constant non-vehicle-specific `PartNumber_D`/`DLS_D` placeholder of `70008`/`00` on every row) add
structure, matching the already-known CalDef schema — none of the three contributes content beyond
what's already catalogued.

**Directory-entry history: real, unrecoverable evidence of more part numbers than are currently live.**
Deleted/superseded directory entries for `applied_overrides/` survive in unallocated blocks, preserved
alongside literal `security.selinux` xattr context strings (`u:object_r:calibration_data_file:s0`) —
i.e. genuine past filenames, not database-journal noise. Scanning for every `8\d{7}\.A[A-Z]` pattern in
the full image surfaced 27 distinct part+alpha combinations, well beyond the 15 known containers:

- **Direct physical confirmation of the documented High Country bench writes on this exact unit:**
  `85045386.AA` (HC slot 04), `85877786.AA` (HC slot 05), and `87846412.AB` (HC slot 02) all appear in
  this partition's deleted-entry history — this bench radio really was programmed with genuine HC
  calibration at some point, independently of the SPS-log evidence already cited elsewhere in this
  doc.
- **An undocumented revision history for slot 0C:** at least seven distinct historical part numbers —
  `85102233`, `85102238`, `85102293`, `85102311`, `85102312` (current), `85102317`, `85102335` — far
  more GM-released revisions of this slot than anything previously catalogued in this corpus.
- **One genuinely unidentified lead: an `88102xxx` family** — `88102229.AC`, `88102305.AB`,
  `88102310.AB`, `88102312.AA`, `88102324.AA`. This does not match any of the 14 current slots, either
  trim's known part numbers, or anything referenced anywhere else in this entire corpus. Its payload is
  **not recoverable** — the directory entry survived, the underlying data blocks did not — so neither
  its slot assignment nor its content/purpose is known. Flagged here as an open lead, not resolved.

Net result: no new calibration *values* or feature sets exist anywhere in this image beyond the known
stock LTZ/HC set — but the filename-only remnants prove this unit's real calibration history is
considerably larger than what any single snapshot (this doc's 14-slot table, or any one SPS session)
shows, and the `88102xxx` family is a legitimately open question for anyone with a later image or a
fresh bench capture to chase.

## Sources and provenance

The complete per-part extracts — every `OverrideValue` row with CalID, type, value and verbatim
CalDef description, plus full container hashes, header dumps and the extraction/reproduction scripts
— remain in the **external research workspace**, one markdown file per part number plus a
`SLOT_MAPPING.md`, under the project's `diagnostics/gm_dps/calibrations/module_map/` tree. This repo
intentionally does **not** check in the raw containers, the full inner-XML dumps, or the full
per-part override tables — the same editorial split used for `calibration_prototypes/`,
`type4_radio_info/` and the other external-pointer material referenced elsewhere here: curated,
distilled analysis lives in the repo; bulk/raw material stays external.

Of the 14 calibration containers, **two are empty** (slot 03 = `84517309` and slot 0E = `84517418`,
zero overrides each); the other twelve are substantive. The fifteenth file (`85577468`) is the
programming utility, not a calibration. The stock set forms exactly one complete 02–0F slot
assignment with one part per slot; the High Country trim substitutes `87846412`/`85045386`/`85877786`
in slots 02/04/05 and lives outside this LTZ set.
