# Bench-radio donor vehicle — config & RPO → calibration map

Ground-truth configuration of the vehicle the bench IOK radio came from. Used to set the emulator's
GM calibrations to this truck's real feature set instead of guesses (see [`emulator.md`](emulator.md)).

**VIN is owner-held and deliberately NOT recorded here** (per the repo's no-credentials/PII rule); the
emulator uses a GM-format **placeholder** VIN for `INFO_VIN`. Vehicle model derived from the VIN/RPOs:
**2024 Chevrolet Silverado 2500HD LTZ**, ICE **6.6L gas V8 (L8T)**, 4WD (F48), Fleetside (E63),
GVWR 10,850 lb (JGH), Flint MI plant (CMD).

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
