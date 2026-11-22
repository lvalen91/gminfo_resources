# Calibration Customization Guide — Safe-to-Try vs. Avoid

**Scope:** a practical risk triage for anyone planning a custom calibration write on this A11
(gminfo37 CSM) radio, built from the full slot inventory in
[`CALIBRATION_SLOT_MAP.md`](CALIBRATION_SLOT_MAP.md) and the live-trial record in
[`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md). This page
does not re-derive the slot contents, the write mechanism, or the signature/verification mechanics
— it only sorts what's already catalogued into "already proven," "plausible next step," and
"avoid," and names the one category of calibration that is categorically different from everything
tested so far.

**Does NOT live here:** the per-slot `OverrideValue` catalogs (owned by `CALIBRATION_SLOT_MAP.md`),
the signed-container format and verification mechanics (owned by
[`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)), the
scoped CAN613/614 VIP-RAM bypass procedure and its chronological trial log (owned by the workflow
doc), and the checksum/container-edit byte mechanics (owned by
[`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md)). This page
is a reading of those four, not a fifth independent source.

## 1. Already proven on this bench (2026-11-16/17 trial log)

| Change | Slot | Outcome | Caveat |
|---|---|---|---|
| SXM disable | 0C (custom build) | Accepted, UI effect confirmed, survived one cold power cycle | Stock slot 0C has no SXM-disable override of its own kind pre-built — this was an edited value on an existing CalID |
| CarPlay / Android Auto disable | 0C (custom build) | Accepted, UI effect confirmed | **Added** CalIDs absent from the stock container — not present in genuine slot 0C at all; no cold-cycle test run on this candidate |
| GMBrand 3→0 | 04 | Accepted, live readback + owner-confirmed theme change | No physical cold-cycle retention test run |
| Screen resolution 4→2 | 08 | Accepted — **but caused display tearing** | Transfer success is not display success; rolled back |
| Google app visibility (Assistant/Maps/Play Store) false | 04 | Accepted — **but had no visible effect**; icons and processes stayed as before | Transfer acceptance does not establish consumer behavior |
| Recorder enable, porch-view enable | 04 | Accepted | Porch-view has an independent gate — needs `SCREEN_RESOLUTION` = 1920×1080 or 1280×768; this unit's stock value (2400×960) may block it regardless of the flag |

**Reading these together:** "the radio accepted the write" has already been shown twice to mean
nothing about whether the change does what you want (tearing, and the no-op Google-visibility
case). Budget for a functional check after every write, not just a clean PEC.

## 2. Full slot inventory, triaged

Content detail for every row below is in `CALIBRATION_SLOT_MAP.md`; this is only the triage.

| Slot | Part | Content | Triage |
|---|---|---|---|
| 02 | 87863250 | Fuel type, GCWR, steering-wheel button map | **Mixed** — GCWR feeds trailering/towing math (avoid); button remap is pure UI (try) |
| 04 | 85045371 | 404 entries: GMBrand/Model/Trim, HUD availability, every app feature-enable (CarPlay/AA/Assistant/Maps/PlayStore/Nav), recorder, porch-view, Alexa | **Best candidate slot** — AAOS/UI feature territory, widest proven-safe track record |
| 05 | 87846416 | Region/market, language, AM/FM band plan, **driver-distraction lockout levels**, server hostnames | **Mixed** — lockout-level CalIDs are safety-adjacent (avoid); region/language/band-plan are cosmetic (try with care — may also affect legal radio-tuning compliance for your market) |
| 06 | 87846371 | Speech-recognition tuning (`.vtc` binaries) | Try — AAOS feature, no safety linkage found |
| 07 | 85783460 | Bluetooth feature switches + hands-free `.scd` tuning | Try — AAOS feature; hands-free audio quality only |
| 08 | 87846432 | **Rear-camera geometry, guidelines, parking-sensor/cross-traffic icon positions**, steering geometry, screen resolution, RVS status, DTC masks | **Avoid the geometry/guideline/icon-position entries** — they exist so the backup view and alerts line up with reality; screen-resolution alone already caused a visible defect |
| 09 | 87846376 | **DTC masks**, GNSS dead-reckoning, VIN-relearn switches | **Avoid the DTC masks** — this suppresses real fault reporting, not a feature |
| 0A | 87846368 | HVAC config (dual-zone, no HV coolant heater) | Try, except anything defrost-related |
| 0B | 86292118 | **OnStar**, WiFi, location services, **DTC masks**, remote-programming timers | **Avoid OnStar-capability CalIDs** — tied to automatic crash notification, not just connectivity UI; avoid DTC masks |
| 0C | 85102312 | SXM/HD/DAB/AM-FM antenna, speech-recognition radio domain, DTC masks | Try (proven) for the tuner-domain entries; avoid the DTC mask entries |
| 0D | 87846384 | **Trailer cameras, trailer height max**, rear-seat entertainment, DTC masks | **Avoid** trailer-height/camera entries if you ever tow with this unit; rear-seat entertainment is a plain feature (try) |
| 0F | 87846380 | Speaker EQ (VSE) | Try — but **currently a no-op on this Bose-equipped truck** (see `CALIBRATION_SLOT_MAP.md`'s `AmplifierType` gate); changing it will not audibly do anything until/unless that gate condition changes |
| 03, 0E | 84517309/18 | Empty | Nothing to customize; see `CALIBRATION_SLOT_MAP.md` for the open question of why GM ships a part-numbered empty container here |

## 3. Safety/chime domains with zero shipped presence — treat as off-limits

The platform's CalDef database defines roughly 215 calibration groups; only a fraction of them are
represented anywhere in this LTZ build's 14 slots. The groups below are present in `CalSets.db`
only as untouched base defaults (`OverRiden=0`) — **no override package on this vehicle, stock or
custom, has ever touched them**, meaning there is no bench precedent at all for what happens if one
does:

- `GIS604_SafetyRelatedVolumeGroupOverrides` — named for safety-chime volume behavior specifically
- `GIS631_ConfigChimeProd_CadTheme1_GlobalB`, `GIS631_ConfigChimeProd_StdTheme0_GlobalB`,
  `GIS631_ConfigStdChimeProd_GenericCal_GlobalB`, `GIS631_StandardChimeProd_db_GlobalB` — the actual
  chime/alert sound configuration
- `GlobalChimeGainCals`, `MuteUnmuteRampTimes`, `VolumeGroupRampTimes` — chime/alert audio-ducking
  behavior
- `DrivingRestrictions`, `GIS509_DriverWorkloadRestrictions` — the framework that gates
  interaction while driving
- `SFS22_SecurityEventLoggingFRD` — security event logging
- `ADASIS` — ADAS data interface

Every trial logged in §1 edited a CalID that already existed inside a **shipped** override package;
the CAN613/614 RAM-bypass method was proven against exactly that situation. Constructing a brand-new
override against a CalID from one of these never-shipped groups is a materially different
experiment: there's no evidence the radio's application layer even has an exercised code path for
it, and given what these groups are named for, an unexpected result would land on chime/alert/
driver-workload behavior rather than something cosmetic. Recommend leaving these alone rather than
treating them as the next item on the list.

## 4. Practical checklist before any new custom slot 04 (or other) write

1. Confirm you're editing a CalID that already exists in the **stock** container for that slot —
   adding an entirely new CalID (as the CarPlay/Android Auto trial did) is a step up in uncertainty
   from editing an existing one.
2. Keep the pinned stock container for that slot on hand as the recovery payload before you start
   (every logged trial did this).
3. Don't treat a clean `76`/`76`/`77` + PEC `0000` as proof of effect — verify the actual on-screen
   or functional behavior change, per the tearing and no-op-Google-visibility precedents in §1.
4. Run a cold-power-cycle check if persistence matters to you — most logged trials did not get one.
5. Stay out of §3 entirely unless you are specifically trying to characterize those groups as a
   research question, not as a feature customization — in which case treat it with the same
   methodology rigor as the rest of this corpus (control candidates, explicit hashes, documented
   rollback) rather than as a one-off bench change.

## Related

- [`CALIBRATION_SLOT_MAP.md`](CALIBRATION_SLOT_MAP.md) — full per-slot `OverrideValue` catalog, slot
  encoding, live-storage architecture.
- [`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) — the
  chronological trial log and the CAN613/614 bypass mechanism these recommendations are read from.
- [`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) — signed
  container format and verification mechanics.
- [`CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) —
  checksum/container-edit byte mechanics for hand-editing a candidate.
