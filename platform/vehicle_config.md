# Bench-radio donor vehicle — config & RPO → calibration map

Ground-truth configuration of the vehicle the bench IOK radio came from. Used to set the emulator's
GM calibrations to this truck's real feature set instead of guesses (see [`emulator.md`](emulator.md)).

**VIN is owner-held and deliberately NOT recorded here** (per the repo's no-credentials/PII rule); the
emulator uses a GM-format **placeholder** VIN for `INFO_VIN`. Vehicle model derived from the VIN/RPOs:
**2024 Chevrolet Silverado 2500HD LTZ**, ICE **6.6L gas V8 (L8T)**, 4WD (F48), Fleetside (E63),
GVWR 10,850 lb (JGH), Flint MI plant (CMD).

## Y181B exported calibration baseline (2026-11-12)

The [recovery export](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12)
contains `update_cache/bootup_log/vendor/CalSets.db`: **2574** `AllCalSets`
rows, 982 with nonzero `OverRiden`. This count describes the retained exported
database, not a query of the running calibration HAL. The second ZIP has the
byte-identical database. **Verified 2026-11-12 (`sqlite3` on the exported file):** 2574 rows / 982 nonzero `OverRiden` re-counted exactly; `PRAGMA user_version` = **70008**; tables `AllCalSets`, `SubSets`, `EnumSets`, `ModuleData` (every `ModuleData` row carries `PartNumber_D` = 70008, i.e. the same number is the DB/cal-set revision, with per-module `applied_overrides/<part>.<DLS>.<n>.cmod` paths); the VIP/`ghs.log` reports `Calibrations: Info: Current CalTable Version: 3.5` and `Saved CalTable Version: 3.5` (equal, no pending table migration). Live props `persist.sys.cal.brand=GM_Brand_Chevrolet`, `persist.sys.cal.model=Silverado` read via `adb shell getprop`; `persist.vendor.gm.brand/.model` are absent on the real radio. `OverRiden` is retained as a numeric field, not
interpreted here as a Boolean or a human-edit count.

**Owner-supplied update-cache archive checked 2026-11-14:** its in-memory
`CalSets.db` query again returns 2574 rows / 982 nonzero `OverRiden` values,
with DB user version 70008. Every nonzero `OverRiden` value matches a
`ModuleData.ModID` in this snapshot; it is not a Boolean or a count of manual
edits. `ModuleData` records 14 applied `.cmod` paths. The ZIP contains none of
those `.cmod` files and no calibration-directory subtree. These records can
include production configuration packages; the archive is not a complete
backup from which to reverse a calibration-override erase. Its DB member's
archive timestamp is in 2010 and does not establish the current radio state.

**Live-state limit, 2026-11-14:** UID-2000 USB ADB on the running Y175
radio returned `Permission denied` for metadata checks of
`/mnt/vendor/calibration/overrides`, `/update_cache/calibrations` and
`/update_cache/bootup_log/vendor/CalSets.db`. The exported Y181B row count above
therefore does not establish the running Y175 override count, loaded module
state or absence of overrides. No calibration override was erased by those metadata checks; the later explicit clear is recorded below. See the [routine inventory](../diagnostics/diagnosticsd_protocol.md#java-handler-inventory-verified-against-the-live-apk-2026-11-14)
for the distinct erase/reset paths.

**Read-only live identity comparison, 2026-11-14:** diagnostic DID F182
returned records for all 14 ModuleData IDs in the archive. Thirteen current
part-number/DLS pairs match the recorded override identities; module 11 differs.
The native F182 handler queries these identities from GMCalibrationManager.
This corroborates selected module metadata on the running radio, while the
live database contents, loaded-row ownership and override package files remain
unread. The archive therefore cannot be assumed to reproduce every current
module. This comparison preceded the later explicit clear. See the
[comparison details](../diagnostics/diagnosticsd_dids_and_dtc.md#read-only-calibration-identity-comparison-with-the-supplied-archive).

**Post-clear state, 2026-11-14:** the later explicitly requested T1
31 01 02 49 returned 71 01 02 49 and the live daemon logged ALL OVERRIDES
CLEARED. All 14 F182 calibration-module identities (tags 02–0F) changed to
part number 70008 / DLS 00; total F182 record count remained 28. MEC stayed
FF/255 and Android did not reboot. The archived 982 nonzero rows are therefore
historical export evidence, not a current post-clear row count. No live
post-clear SQLite count was obtainable. A persistent J5 indicator was created;
the owner's subsequent power-cycle entered RH850 `NoCalibration (0xe)` after
a startup fault timeout and showed bad/incomplete calibration on the display.
T1 still returned MEC FF and all 14 base module identities; USB ADB did not
reappear. The base-only state is therefore insufficient for normal startup. See the
[completed clear](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).

| CalName | CalValue | OverRiden |
|---|---:|---:|
| `SCREEN_RESOLUTION` | **4 (`SIZE_2400_BY_960`)** | 8 |
| `GMBrand` | **3** | 4 |
| `GMModel` | **4** | 4 |
| `APPLICATION_HOMESCREEN_APPLECARPLAY_ENABLED` | 1 | 5 |
| `Apple_CarPlay_enableWireless` | 1 | 5 |
| `Enable_Application_Apple_Carplay` | 1 | 0 |
| `GIS864_USBProgrammingEnabled` | 1 | 0 |

These are a Y181B vehicle-specific baseline for emulator comparison. Earlier
2573-row vendor/default databases and `SCREEN_RESOLUTION=2` snapshots remain
historical sources, not the current exported radio baseline. A calibration
enable does not prove feature operation or acceptance of a custom signed
calibration package. The homescreen-removal experiment changes per-user
package availability independently of these calibration values.

## RPO → feature → GM calibration / prop implication
Radio/UI-relevant options (full RPO list retained by owner). "cal" = the calibration or prop it grounds;
exact enum values still to be read from `CalSets.db`/GMHomeScreen where noted.

| RPO | Meaning | Emulator calibration / prop it grounds |
|---|---|---|
| X88 | Market brand Chevrolet | `GMBrand=3` (GM_Brand_Chevrolet); `persist.sys.cal.brand=GM_Brand_Chevrolet` — **confirmed** |
| GF9 | Trim package **LTZ** | `GMTrim` = LTZ enum (emu guessed 15 → confirm); `persist.sys.cal.model=Silverado` |
| AXK / E63 | Truck / Fleetside pickup box | vehicle-type cal (truck) |
| IOK | Radio 3.X Mid/High HMI (gminfo37) | the radio itself |
| URD | Display 13.4″, **2400×960**, TFT | `SCREEN_RESOLUTION=4` (SIZE_2400_BY_960), density 200 — **confirmed** |
| UV2 / (rear cams) | 360 View HD, mono digital | `RVS_PRESENT_STATUS=2`; `APPLICATION_HOMESCREEN_CAMERA_ENABLED` — **confirmed present** |
| **Z82 / UET / JL1 / CTT / PZ8 / TRG / UKV** | Trailer provisions, smart-trailer integration, integrated trailer brake, hitch view/guidelines, trailer views | **Trailering equipped** → `APPLICATION_HOMESCREEN_TRAILERING_ENABLED=1` + `TraileringAppType` → the **4th home card** (resolves the emu's 3-vs-4 card gap) |
| FJW / L8T | Gasoline E15 / 6.6L gas V8 | propulsion type = **ICE gas** (not EV): `KeOCD_int_VEHICLE_PROPULSION_TYPE` = gas |
| UE1 / VV4 | OnStar / mobile-internet connectivity | `APPLICATION_HOMESCREEN_ONSTAR_ENABLED` (Wi-Fi Hotspot gate) — **confirmed present** |
| PPW | Wireless phone projection | AA/CarPlay tiles legitimate (need a paired phone to activate) |
| UQA | Premium audio, branded amplifier (Bose) | audio config; branded-amp path |
| U2K | S-band digital audio | **SiriusXM** present (ties to the Y181→Y181B SXM firmware delta) |
| K4C / KA1 / KA6 / KQV / KI3 | Wireless charger; heated front/rear + vented seats; heated wheel | Climate/seat feature cals |
| KSG / UHY / UFL / UEU / UFG / UKJ / UD5 | Adaptive cruise w/ stop-go, low-speed AEB, lane-departure, FCA, rear cross-traffic, ped detection, front+rear park assist | ADAS safety-indicator cals |
| UDV | Enhanced full multicolor cluster | IVN=NONE (cluster driven by radio family) — cluster HMI over FSA |

## Actionable emulator corrections (from this config)
> **Status note 2026-11-12:** items 1-2 and 4 below were subsequently applied (`GMTrim=16` for LTZ, `TraileringAppType=2` +
> `APPLICATION_HOMESCREEN_TRAILERING_ENABLED=1`, identity props set) — see `emulator.md` "RPO-matched calibrations [DONE]". The "placeholder 15" is the pre-fix value.

1. **Enable Trailering** (`APPLICATION_HOMESCREEN_TRAILERING_ENABLED=1`, `TraileringAppType`) → the missing
   4th home card, since this truck is trailer-equipped (Z82/UET/JL1).
2. **Set `GMTrim` to the LTZ value** (GF9), not the placeholder 15.
3. **Propulsion = gas** (FJW/L8T) — ensure no EV props.
4. **Identity props** — set `persist.sys.cal.brand=GM_Brand_Chevrolet` + `persist.sys.cal.model=Silverado`
   (the real prop names; `persist.vendor.gm.*` is not present on the real radio — see emulator.md un-stub roadmap).
5. Camera/OnStar/Wi-Fi-Hotspot enables are **confirmed** by UV2 / UE1 / VV4 (not guesses).

These convert roughly half of the previously "not-dump-provable" `CalSets.db` overrides into
config-confirmed values for this specific truck. Exact enum numbers for GMTrim/TraileringAppType/propulsion
should be read from `CalSets.db` (`AllCalSets`) or GMHomeScreen before applying.

**Direct-T1 restoration attempt, 2026-11-14:** all 14 stock LTZ containers
matched the pinned successful-transfer hashes. Level-01 access succeeded,
but `10 02` returned `7F 10 22` and the first stock RequestDownload returned
`7F 34 7F`. No calibration bytes were transferred. MEC remained FF. See the
[attempt and access checks](../diagnostics/diagnosticsd_routines_and_recovery.md#direct-t1-stock-ltz-restoration-attempt-and-shell-checks-2026-11-14).

**MDI2 recovery completed, 2026-11-14:** the same previously cleared A11 was
subsequently restored with the pinned stock LTZ package using the main MDI2
client. Recovery accepted only the exact 14-slot base 70008/00 profile through
a one-time in-memory classifier and restored the erased VIN from the owner's
supplied value before programming. All slots 02–0F and VIN matched post-reset
readback; F0F1/F0F2 were `0000`. Later UART boots reported calibration state
`2` and reached HMI ready / Accessory; the owner confirmed normal display and
radio operation. This supersedes the unresolved post-clear state above; it
does not establish the old archive's suitability or a post-recovery SQLite
row count. ADB and final MEC were not rechecked. See the
[completed recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
