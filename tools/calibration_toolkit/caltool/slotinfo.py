"""Static per-slot reference data, condensed from
docs/CALIBRATION_SLOT_MAP.md. Used to label a loaded module with
what its slot is generally for, independent of which specific part number was loaded.
Not a source of truth by itself -- read the slot map doc for citations and evidence."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlotInfo:
    slot: int
    ltz_part: str
    summary: str
    triage: str  # "safe", "mixed", "avoid", "n/a"


SLOTS: dict[int, SlotInfo] = {
    0x02: SlotInfo(0x02, "87863250", "Fuel type, GCWR, steering-wheel button map", "mixed"),
    0x03: SlotInfo(0x03, "84517309", "Empty on this build -- part-numbered but zero overrides", "n/a"),
    0x04: SlotInfo(0x04, "85045371", "GMBrand/Model/Trim identity, HUD availability, every app feature-enable (CarPlay/AA/Assistant/Maps/PlayStore/Nav), recorder, porch-view, Alexa -- the largest and most-tested slot (404 entries)", "safe"),
    0x05: SlotInfo(0x05, "87846416", "Region/market, language, AM/FM band plan, driver-distraction lockout levels, server hostnames", "mixed"),
    0x06: SlotInfo(0x06, "87846371", "Speech-recognition tuning (binary .vtc tables)", "safe"),
    0x07: SlotInfo(0x07, "85783460", "Bluetooth feature switches, hands-free audio tuning (binary .scd tables)", "safe"),
    0x08: SlotInfo(0x08, "87846432", "Rear-camera geometry/guidelines/parking-sensor icons, steering geometry, screen resolution, RVS status, DTC masks", "avoid"),
    0x09: SlotInfo(0x09, "87846376", "DTC masks, GNSS dead-reckoning, VIN-relearn switches", "avoid"),
    0x0A: SlotInfo(0x0A, "87846368", "HVAC configuration (dual-zone, HV coolant heater presence)", "safe"),
    0x0B: SlotInfo(0x0B, "86292118", "OnStar, WiFi, location services, DTC masks, remote-programming timers", "avoid"),
    0x0C: SlotInfo(0x0C, "85102312", "Radio tuner domains: SXM/HD/DAB/AM-FM antenna, speech-recognition radio domain, DTC masks", "safe"),
    0x0D: SlotInfo(0x0D, "87846384", "Trailer cameras, trailer height max, rear-seat entertainment, DTC masks", "avoid"),
    0x0E: SlotInfo(0x0E, "84517418", "Empty on this build -- part-numbered but zero overrides", "n/a"),
    0x0F: SlotInfo(0x0F, "87846380", "Speaker EQ (VehicleSpecificEqualization) -- confirmed inert while AmplifierType=BosePremiumAmplifier", "safe"),
}

TRIAGE_LABEL = {
    "safe": "try — proven or low-risk",
    "mixed": "mixed — some entries safety-adjacent",
    "avoid": "avoid specific entries — see help page",
    "n/a": "empty slot",
}


def describe(slot: int | None) -> SlotInfo | None:
    if slot is None:
        return None
    return SLOTS.get(slot)
