#!/usr/bin/env python3
"""
gcs_gt.py -- G/T calibration assistant for Gilmore Creek, Fairbanks, Alaska.

Menu-driven text UI covering the whole sun/radio-star G/T workflow:

  * Solar flux bracketing (low/high RSTN frequencies -> band centres)
  * 7-day flux projection from the SWPC 27-day F10.7 outlook
  * Radio star az/el, transit times and flux, precessed to date
  * Method advisor: which source to use per dish per band, with pros/cons
  * Y-factor -> G/T solver
  * Procedure dos and don'ts

Site      : Gilmore Creek, 64.9736 N, 147.5158 W
Apertures : 5 m, 13 m, 21 m, 26 m
L-band    : 1650-1720 MHz, centre 1685   bracket 1415 / 2695 MHz
S-band    : 2200-2300 MHz, centre 2250   bracket 1415 / 2695 MHz
X-band    : 7800-8300 MHz, centre 8050   bracket 4995 / 8800 MHz

Feed coverage: the 13 m is L/S only (no X-band path). See DISH_BANDS.

Python 3, standard library only.

    python3 gcs_gt.py              interactive menu
    python3 gcs_gt.py --report     print everything and exit (non-interactive)
    python3 gcs_gt.py --json       machine-readable dump
    python3 gcs_gt.py --no-color   plain ASCII
"""

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import urllib.request

# ==========================================================================
# SITE AND HARDWARE
# ==========================================================================

SITE_NAME = "Gilmore Creek, Fairbanks, AK"
SITE_LAT = 64.9736
SITE_LON = -147.5158
# ==========================================================================
# ANTENNA INVENTORY
# Source: NOAA NESDIS "Antenna and RF Systems Capability Chart for Fairbanks
# and Barrow" (Table 1-2). Gains, 3 dB beamwidths, Tsys and published G/T are
# TAKEN FROM THAT CHART -- measured values beat any k*lambda/D estimate, so
# the beamwidth here is authoritative and no HPBW formula is used when it is
# present.
# ==========================================================================

ANTENNAS = [
    {"id": "26M", "status": "active", "label": "26 METER", "diam": 26.0, "mount": "XY",
     "mission": "", "bands": {
        "VHF": {"feed": "PRIME", "range": (136.0, 138.0), "gain": 27.4,
                "bw": 6.7, "tsys": None, "gt": None, "pol": "LINX/LINY"},
        "L": {"feed": "PRIME", "range": (1670.0, 1710.0), "gain": 48.7,
              "bw": 0.54, "tsys": 275.4, "gt": 24.3, "pol": "RCP/LCP"},
        "S": {"feed": "PRIME", "range": (2200.0, 2300.0), "gain": 51.8,
              "bw": 0.34, "tsys": 257.0, "gt": 27.7, "pol": "RCP/LCP"}}},

    {"id": "13M-1", "status": "active", "label": "13 METER 1", "diam": 13.0, "mount": "EL/AZ",
     "mission": "POES", "bands": {
        "L": {"feed": "PRIME", "range": (1670.0, 1710.0), "gain": 43.1,
              "bw": 0.8, "tsys": 190.0, "gt": 19.8, "pol": "RCP/LCP"},
        "S": {"feed": "PRIME", "range": (2200.0, 2400.0), "gain": 44.0,
              "bw": 0.6, "tsys": 110.0, "gt": 23.5, "pol": "RCP/LCP"},
        "X": {"feed": "CASS", "range": (7250.0, 8500.0), "gain": 58.0,
              "bw": 0.18, "tsys": 70.0, "gt": 37.8, "pol": "RCP/LCP"}}},

    {"id": "13M-2", "status": "active", "label": "13 METER 2", "diam": 13.0, "mount": "EL/AZ",
     "mission": "POES", "bands": {
        "L": {"feed": "PRIME", "range": (1670.0, 1710.0), "gain": 42.0,
              "bw": 0.8, "tsys": 190.0, "gt": 19.2, "pol": "RCP/LCP"},
        "S": {"feed": "PRIME", "range": (2200.0, 2400.0), "gain": 44.0,
              "bw": 0.6, "tsys": 110.0, "gt": 23.6, "pol": "RCP/LCP"},
        "X": {"feed": "CASS", "range": (7250.0, 8500.0), "gain": 55.0,
              "bw": 0.18, "tsys": 70.0, "gt": 36.5, "pol": "RCP/LCP"}}},

    {"id": "13M-3", "status": "active", "label": "13 METER 3", "diam": 13.0, "mount": "EL/AZ",
     "mission": "POES", "bands": {
        "L": {"feed": "PRIME", "range": (1670.0, 1710.0), "gain": 43.1,
              "bw": 0.8, "tsys": 190.0, "gt": 19.6, "pol": "RCP/LCP"},
        "S": {"feed": "PRIME", "range": (2200.0, 2400.0), "gain": 44.0,
              "bw": 0.6, "tsys": 110.0, "gt": 23.4, "pol": "RCP/LCP"},
        "X": {"feed": "CASS", "range": (7250.0, 8500.0), "gain": 58.0,
              "bw": 0.18, "tsys": 70.0, "gt": 36.4, "pol": "RCP/LCP"}}},

    {"id": "21M", "status": "active", "label": "21 METER", "diam": 21.0, "mount": "EL/AZ",
     "mission": "GOES", "bands": {
        "L": {"feed": "CASS", "range": (1670.0, 1710.0), "gain": 50.58,
              "bw": 0.48, "tsys": 41.1, "gt": 30.75,
              "pol": "ROTATABLE LINEAR"},
        "S": {"feed": "CASS", "range": (2200.0, 2300.0), "gain": 53.12,
              "bw": 0.34, "tsys": 48.95, "gt": 32.93,
              "pol": "ROTATABLE LINEAR"}}},

    {"id": "5M-MAL", "label": "5 METER MALIBU", "diam": 5.0, "mount": "XY",
     "mission": "COSMIC", "status": "active", "bands": {
        "S": {"feed": "PRIME", "range": (2200.0, 2290.0), "gain": 38.2,
              "bw": 1.75, "tsys": None, "gt": 16.2, "pol": "RCP/LCP"}}},
     # NOTE: chart lists an 8025-8400 X feed on Malibu. That feed has been
     # RELOCATED to 5M-A. Malibu is S-band only as of 2026-08.

    {"id": "5M-A", "label": "5 METER A", "diam": 5.0, "mount": "",
     "mission": "COSMIC", "status": "active", "bands": {
        "X": {"feed": "PRIME", "range": (8025.0, 8400.0), "gain": 49.4,
              "bw": 0.49, "tsys": None, "gt": 27.6, "pol": "RCP/LCP"}}},
     # X feed relocated here from Malibu. Specs carried over from the chart's
     # Malibu X row -- RE-VERIFY after the move; gain and Tsys do not
     # necessarily survive a feed transplant unchanged.

    {"id": "5M-C", "label": "5 METER C", "diam": 5.0, "mount": "",
     "mission": "", "status": "decommissioned", "bands": {}},
     # Permanently non-operational, scheduled for destruction. Listed so its
     # absence is explicit; excluded from every calculation.

    {"id": "5M-LEOT", "label": "5 METER LEO-T", "diam": 5.0, "mount": "EL/AZ",
     "mission": "COSMIC", "status": "active", "bands": {
        "S": {"feed": "PRIME", "range": (2200.0, 2300.0), "gain": 39.0,
              "bw": None, "tsys": None, "gt": 16.75, "pol": "RCP/LCP"}}},

    {"id": "4.06M", "status": "active", "label": "4.06 METER", "diam": 4.06, "mount": "",
     "mission": "", "bands": {
        "Ka": {"feed": "", "range": (26450.0, 26950.0), "gain": None,
               "bw": 0.163, "tsys": 363.0, "gt": 28.2, "pol": "RHCP"}}},
]

BAND_ORDER = ["VHF", "L", "S", "X", "Ka"]
BAND_NAMES = {"VHF": "VHF", "L": "L-band", "S": "S-band", "X": "X-band",
              "Ka": "Ka-band"}

# RSTN measurement frequencies. Flux at any test frequency is interpolated
# between the adjacent pair; above 15400 MHz there is no bracket at all.
RSTN_FREQS = [245.0, 410.0, 610.0, 1415.0, 2695.0, 4995.0, 8800.0, 15400.0]

APERTURE_EFF = 0.60          # fallback only, when the chart lacks a gain
MIN_TRACK_ELEV = 10.0
ATM_DB = {"VHF": 0.02, "L": 0.05, "S": 0.07, "X": 0.11, "Ka": 0.6}


def bracket_for(freq_mhz):
    """RSTN pair bracketing a test frequency, or None if out of range."""
    for lo, hi in zip(RSTN_FREQS, RSTN_FREQS[1:]):
        if lo <= freq_mhz <= hi:
            return lo, hi
    return None


def band_centre(ant, band_key):
    lo, hi = ant["bands"][band_key]["range"]
    return (lo + hi) / 2.0


def is_active(ant):
    return ant.get("status", "active") == "active"


def active_antennas():
    return [a for a in ANTENNAS if is_active(a)]


def antennas_with(band_key):
    return [a for a in ANTENNAS if is_active(a) and band_key in a["bands"]]


def get_antenna(ident):
    for a in ANTENNAS:
        if a["id"].upper() == str(ident).upper():
            return a
    return None


def eff_aperture(ant, band_key):
    """Effective aperture from the chart gain, else geometric x efficiency."""
    spec = ant["bands"][band_key]
    freq = band_centre(ant, band_key)
    lam = C_LIGHT / (freq * 1e6)
    if spec.get("gain") is not None:
        return 10.0 ** (spec["gain"] / 10.0) * lam ** 2 / (4.0 * math.pi)
    return APERTURE_EFF * math.pi * (ant["diam"] / 2.0) ** 2

# ==========================================================================
# DATA SOURCES
# ==========================================================================

RAD_URL = "https://services.swpc.noaa.gov/text/solar_radio_flux.txt"
OUTLOOK_URL = "https://services.swpc.noaa.gov/text/27-day-outlook.txt"

STATION_COLUMNS = [
    ("Learmonth", "0500"), ("San Vito", "1200"), ("Sag Hill", "1700"),
    ("Penticton", "1700"), ("Penticton", "2000"), ("Palehua", "2300"),
    ("Penticton", "2300"),
]
EXCLUDED_STATIONS = {"Sag Hill"}          # damaged, never repaired
STATION_PREFERENCE = ["San Vito", "Learmonth"]

STATION_NOTES = [
    ("Sagamore Hill", "OUT OF SERVICE",
     "Damaged and never repaired. Excluded from every calculation here. Its "
     "loss removed the only redundant source of 8800 MHz."),
    ("Palehua", "WRONG FREQUENCIES",
     "Reports 245/410/610 MHz only. Its 2300 UTC noon is the best time match "
     "to Gilmore Creek of any RSTN site, but it carries none of your "
     "bracketing frequencies. Do not plan around it."),
    ("San Vito", "SOLE X-BAND SOURCE",
     "Only remaining station reporting 8800 MHz. Measured at 1200 UTC, about "
     "10 h before Gilmore Creek solar noon. Single-station data with no "
     "cross-check: a burst there is undetectable."),
    ("Learmonth", "S-BAND ONLY",
     "Reports 1415/2695/4995 MHz but not 8800. Good S-band cross-check "
     "against San Vito. Noon at 0500 UTC, ~17 h before your run."),
    ("Penticton", "F10.7 ANCHOR",
     "2800 MHz only, at 1700/2000/2300 UTC. The 2300 UTC reading lands about "
     "1 h after Gilmore Creek solar noon -- the best time-matched solar "
     "measurement you can get. Use it to sanity-check the S-band "
     "interpolation, never as the S-band flux itself."),
]

K_BOLTZMANN = 1.380649e-23
C_LIGHT = 299792458.0
SFU = 1e-22
JY = 1e-26

MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

BURST_STATION_DISAGREE = 0.20
BURST_MEDIAN_DEVIATION = 0.25

# ==========================================================================
# RADIO STAR CATALOG
# ==========================================================================
#
# Positions are J2000 and are precessed to the date of use before display.
#
# Flux models: Baars et al. 1977 (A&A 61, 99), log10 S[Jy] = a + b log10 v[MHz],
# with the published secular decay applied from the epoch of the fit. Baars is
# the form ITU-R S.733 references. Cas A and Tau A reproduce modern published
# values to a few percent with these coefficients; Cyg A and Vir A are carried
# for POSITION ONLY because their published Baars fits are piecewise and easy
# to misapply across your bands.
#
# For a delivered, contractual G/T, take the flux from Perley & Butler 2017
# (ApJS 230, 7) polynomials, not from this approximation.

RADIO_STARS = {
    "CasA": {
        "name": "Cassiopeia A (3C461)",
        "ra_j2000_deg": 350.8500,        # 23h 23m 24.0s
        "dec_j2000_deg": 58.8150,        # +58d 48' 54"
        "size_arcmin": 5.0,
        "baars": {"a": 5.745, "b": -0.770, "epoch": 1965.0,
                  "decay_pct_per_yr_1ghz": 0.97, "decay_index": -0.30,
                  "valid_mhz": (300, 31000)},
        "polarization_pct": 1.0,
        "pros": [
            "Brightest radio source in the northern sky after the sun",
            "CIRCUMPOLAR at Fairbanks -- never sets, always above ~33.7 deg",
            "Transits near 84 deg elevation, minimal atmosphere and no "
            "horizon blockage",
            "Only ~5 arcmin across, so beam correction stays small even on "
            "the 26 m at X-band",
            "Essentially unpolarized -- single-pol measurement is safe",
        ],
        "cons": [
            "Decaying ~0.5-0.8 %/yr, faster at low frequency. A stale flux "
            "value is the single most common error with this source",
            "Steep spectrum: much weaker at X-band than at S-band",
            "Sits in the galactic plane, so the off-source reference "
            "background is not cold sky",
        ],
    },
    "TauA": {
        "name": "Taurus A / Crab Nebula (3C144, M1)",
        "ra_j2000_deg": 83.6331,         # 05h 34m 31.94s
        "dec_j2000_deg": 22.0145,        # +22d 00' 52.2"
        "size_arcmin": 5.0,
        "baars": {"a": 3.915, "b": -0.299, "epoch": 1965.0,
                  "decay_pct_per_yr_1ghz": 0.167, "decay_index": 0.0,
                  "valid_mhz": (1000, 35000)},
        "polarization_pct": 7.0,
        "pros": [
            "Flat spectrum (index -0.30), so it stays strong at X-band -- "
            "the standard X-band calibrator",
            "Compact, ~5 arcmin, small beam correction on every dish you own",
            "Very slow secular decay (~0.17 %/yr), so the flux model ages "
            "gracefully",
            "Well away from the galactic plane background",
        ],
        "cons": [
            "~7 % linearly polarized at cm wavelengths. If you measure a "
            "single polarization you MUST correct for it, or accept a "
            "systematic error of a few tenths of a dB",
            "Peaks at only ~47 deg elevation from Fairbanks, so slant "
            "atmosphere is always in play",
            "Weaker than Cas A at S-band",
        ],
    },
    "CygA": {
        "name": "Cygnus A (3C405)",
        "ra_j2000_deg": 299.8682,        # 19h 59m 28.36s
        "dec_j2000_deg": 40.7339,        # +40d 44' 02.1"
        "size_arcmin": 2.0,
        "baars": None,
        "polarization_pct": 1.0,
        "pros": [
            "CIRCUMPOLAR at Fairbanks -- never drops below ~15.6 deg",
            "Transits at ~65.9 deg elevation",
            "Compact, ~2 arcmin double, so beam correction is negligible on "
            "every one of your dishes",
            "Stable, no measurable secular decay",
        ],
        "cons": [
            "Steep spectrum -- marginal above ~5 GHz. Poor X-band choice",
            "Baars gives a piecewise fit around 2 GHz that is easy to "
            "misapply right at your S-band centre. No flux model shipped "
            "here; supply one from Perley & Butler 2017",
            "Resolved double structure matters on the 26 m at X-band",
        ],
    },
    "VirA": {
        "name": "Virgo A (3C274, M87)",
        "ra_j2000_deg": 187.7059,        # 12h 30m 49.4s
        "dec_j2000_deg": 12.3911,        # +12d 23' 28"
        "size_arcmin": 7.0,
        "baars": None,
        "polarization_pct": 2.0,
        "pros": [
            "Well clear of the galactic plane, genuinely cold reference sky",
            "Useful southern-sky check on a north-heavy calibration set",
        ],
        "cons": [
            "Peaks at only ~37 deg elevation from Fairbanks",
            "Weakest of the four; marginal on the 13 m and hopeless on the 5 m",
            "No flux model shipped here",
        ],
    },
}

# ==========================================================================
# METHOD ADVISOR CONTENT
# ==========================================================================

SUN_PROS = [
    "Enormous signal: Y-factors of 15-25 dB on your larger dishes, so "
    "receiver noise contributes almost nothing to the measurement",
    "Trivially easy to acquire and track -- no faint-source pointing search",
    "Flux is published daily by several independent observatories",
    "The method ITU-R S.733 and Intelsat IESS-207 both document in detail, "
    "so results are contractually recognised",
]
SUN_CONS = [
    "The sun is ~0.53 deg across. On a narrow beam it over-fills, and the "
    "beam correction stops being a correction and becomes the answer",
    "Flux varies day to day and can spike without warning during a burst",
    "Published flux is never at your exact frequency -- interpolation adds "
    "uncertainty",
    "At Fairbanks the sun never exceeds 48.5 deg elevation, and is unusable "
    "October through February",
    "Huge Y-factors stress receiver linearity; compression masquerades as a "
    "low G/T",
]
STAR_PROS = [
    "Effectively point sources for most of your apertures, so the extended-"
    "source correction is small and well behaved",
    "Constant flux -- no burst risk, no day-of measurement dependency",
    "Cas A and Cyg A are circumpolar at your latitude, so you can measure at "
    "high elevation any time of day, any season",
    "Small Y-factors keep the receive chain in its linear region",
]
STAR_CONS = [
    "Weak. Y-factors of 1-4 dB mean receiver noise and radiometer stability "
    "now dominate the error budget -- long integration and a stable reference",
    "Requires accurate pointing: precession, refraction and a real pointing "
    "model, not just catalog J2000 coordinates",
    "Cas A decays; a stale flux number is a silent systematic error",
    "Tau A is 7 % polarized -- matters for single-pol measurement",
    "Hopeless on the 5 m: the signal is below the noise",
]

DOS = [
    "Take the off-source reference at the SAME elevation as the on-source "
    "point, offset in azimuth. This cancels ground pickup and air mass.",
    "Offset the reference by at least 10 beamwidths so no sidelobe sees the "
    "source.",
    "Pull the solar flux at test time, not from yesterday's report, and "
    "record the exact UTC of the flux reading you used.",
    "Verify receive-chain linearity with a calibrated step attenuator across "
    "the full Y-factor range BEFORE the run. Confirm any AGC is disabled.",
    "Check GOES X-ray flux and the SWPC event list for the run window. Abort "
    "on any M-class or larger flare.",
    "Peak up on the source first. A half-beamwidth pointing error on the "
    "26 m at X-band costs you 3 dB.",
    "Correct gaseous attenuation per ITU-R P.676 at the ACTUAL source "
    "elevation, and report that elevation alongside the G/T.",
    "Record everything: station, both bracketing frequencies and their "
    "fluxes, UTC of each, source elevation, off-source position, beam "
    "correction and the constant used for it.",
    "For radio stars, precess to date. J2000 coordinates are 26 years stale "
    "-- about 0.36 deg, which is over 3 beamwidths on the 26 m at X-band.",
]
DONTS = [
    "Do NOT use the sun on the 26 m or 21 m at X-band. The sun is 4-5 "
    "beamwidths wide there and the correction exceeds 9 dB. You would be "
    "measuring your correction factor, not your antenna.",
    "Do NOT use the 1 AU adjusted F10.7. You want the observed flux. The "
    "difference is up to 3.4 %, about 0.15 dB.",
    "Do NOT compute a delivered G/T from a forecast flux. Forecasts are "
    "+/-10-15 sfu and cannot predict a burst.",
    "Do NOT trust a single-station flux without asking why there is no "
    "cross-check. Since Sagamore Hill went down, X-band has none.",
    "Do NOT extrapolate flux above 15400 MHz. Ka-band sun G/T is not "
    "defensible from RSTN data.",
    "Do NOT attempt a sun run at Fairbanks between October and February. "
    "The sun barely clears the horizon.",
    "Do NOT use a Cas A flux from an old document. Recompute for the current "
    "epoch or take it from Perley & Butler 2017.",
    "Do NOT ignore Tau A's polarization on a single-pol measurement.",
    "Do NOT take the off-source reference at a different elevation. You will "
    "fold a ground-noise and atmosphere delta straight into the Y-factor.",
]

# ==========================================================================
# TERMINAL
# ==========================================================================

class UI:
    def __init__(self, color=True):
        self.color = color and sys.stdout.isatty()

    def _c(self, code, text):
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def bold(self, t):   return self._c("1", t)
    def dim(self, t):    return self._c("2", t)
    def red(self, t):    return self._c("1;31", t)
    def yellow(self, t): return self._c("1;33", t)
    def green(self, t):  return self._c("1;32", t)
    def cyan(self, t):   return self._c("1;36", t)
    def blue(self, t):   return self._c("1;34", t)

    def title(self, text):
        print()
        print(self.cyan("=" * 78))
        print(self.cyan(f" {text}"))
        print(self.cyan("=" * 78))

    def section(self, text):
        print()
        print(self.bold(text))
        print("-" * 78)

    def warn(self, text):
        for i, line in enumerate(wrap(text, 72)):
            print(self.red(" [!] " + line) if i == 0 else self.red("     " + line))

    def caution(self, text):
        for i, line in enumerate(wrap(text, 72)):
            print(self.yellow(" [~] " + line) if i == 0
                  else self.yellow("     " + line))

    def tip(self, text):
        for i, line in enumerate(wrap(text, 72)):
            print(self.blue(" [i] " + line) if i == 0 else self.blue("     " + line))

    def ok(self, text):
        print(self.green(" [+] " + text))

    def bullets(self, items, marker="  - ", indent="    "):
        for item in items:
            lines = wrap(item, 70)
            print(marker + lines[0])
            for extra in lines[1:]:
                print(indent + extra)

    def verdict(self, tag):
        return {"GOOD": self.green, "OK": self.green, "MARGINAL": self.yellow,
                "INVALID": self.red, "BEST": self.green,
                "USABLE": self.yellow, "NO-GO": self.red,
                "POOR": self.yellow}.get(tag, lambda t: t)(tag)


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for word in words:
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


# ==========================================================================
# FETCH / PARSE
# ==========================================================================

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "gcs-gt/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_radio_flux(text):
    days, issued, current = {}, None, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(":Issued:"):
            issued = s.split(":", 2)[2].strip()
            continue
        if not s or s[0] in "#:":
            continue
        parts = s.split()
        if len(parts) == 3 and parts[1] in MONTHS:
            try:
                current = dt.date(int(parts[0]), MONTHS[parts[1]], int(parts[2]))
                days.setdefault(current, {})
            except ValueError:
                current = None
            continue
        if current is None or len(parts) != len(STATION_COLUMNS) + 1:
            continue
        try:
            freq = float(parts[0])
            values = [int(v) for v in parts[1:]]
        except ValueError:
            continue
        row = {}
        for (station, hour), value in zip(STATION_COLUMNS, values):
            if station not in EXCLUDED_STATIONS and value >= 0:
                row[(station, hour)] = float(value)
        days[current][freq] = row
    return days, issued


def parse_outlook(text):
    rows, issued = [], None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(":Issued:"):
            issued = s.split(":", 2)[2].strip()
            continue
        if not s or s[0] in "#:":
            continue
        parts = s.split()
        if len(parts) != 6 or parts[1] not in MONTHS:
            continue
        try:
            rows.append((dt.date(int(parts[0]), MONTHS[parts[1]], int(parts[2])),
                         float(parts[3]), float(parts[4]), float(parts[5])))
        except ValueError:
            continue
    return rows, issued


# ==========================================================================
# FLUX MATH
# ==========================================================================

def station_values(day_data, freq):
    out = {}
    for (station, hour), value in day_data.get(freq, {}).items():
        out.setdefault(station, (value, hour))
    return out


def pick_station(day_data, f_low, f_high):
    low, high = station_values(day_data, f_low), station_values(day_data, f_high)
    both = [s for s in STATION_PREFERENCE if s in low and s in high]
    both += sorted(set(low) & set(high) - set(both))
    if not both:
        return None
    s = both[0]
    return {"station": s, "low": low[s][0], "low_hour": low[s][1],
            "high": high[s][0], "high_hour": high[s][1],
            "alternatives": both[1:]}


def log_interp(f_low, phi_low, f_high, phi_high, f):
    frac = ((math.log10(f) - math.log10(f_low)) /
            (math.log10(f_high) - math.log10(f_low)))
    return phi_low + frac * (phi_high - phi_low), frac


def penticton_2800(day_data):
    vals = day_data.get(2800.0, {})
    ordered = sorted((h, v) for (s, h), v in vals.items() if s == "Penticton")
    if not ordered:
        return None, None, []
    lookup = dict(ordered)
    for hour in ("2300", "2000", "1700"):
        if hour in lookup:
            return lookup[hour], hour, ordered
    return ordered[0][1], ordered[0][0], ordered


def burst_check(days, target_date, freq, station, value):
    flags = []
    for other, (other_value, _) in station_values(days.get(target_date, {}),
                                                  freq).items():
        if other == station or other_value <= 0:
            continue
        delta = abs(other_value - value) / max(value, 1.0)
        if delta > BURST_STATION_DISAGREE:
            flags.append(f"{station} {value:.0f} vs {other} {other_value:.0f} "
                         f"sfu at {freq:.0f} MHz ({delta * 100:.0f}% apart)")
    history = [v[0] for d, data in days.items() if d != target_date
               for v in [station_values(data, freq).get(station)] if v]
    if len(history) >= 3:
        median = statistics.median(history)
        delta = abs(value - median) / max(median, 1.0)
        if delta > BURST_MEDIAN_DEVIATION:
            flags.append(f"{freq:.0f} MHz {value:.0f} sfu is "
                         f"{delta * 100:.0f}% off the 7-day {station} median "
                         f"of {median:.0f} sfu")
    return flags


def solve_flux(days, freq_mhz, target):
    """Interpolated solar flux at an arbitrary frequency, most recent day."""
    br = bracket_for(freq_mhz)
    if br is None:
        return None
    f_low, f_high = br
    for date in sorted((d for d in days if d <= target), reverse=True):
        pick = pick_station(days[date], f_low, f_high)
        if not pick:
            continue
        phi, frac = log_interp(f_low, pick["low"], f_high, pick["high"],
                               freq_mhz)
        return {
            "date": date, "age_days": (target - date).days,
            "freq_mhz": freq_mhz, "f_low": f_low, "f_high": f_high,
            "station": pick["station"], "alternatives": pick["alternatives"],
            "low_sfu": pick["low"], "low_hour": pick["low_hour"],
            "high_sfu": pick["high"], "high_hour": pick["high_hour"],
            "phi_sfu": phi, "k": frac,
            "burst_flags": (burst_check(days, date, f_low, pick["station"],
                                        pick["low"]) +
                            burst_check(days, date, f_high, pick["station"],
                                        pick["high"])),
        }
    return None


def flux_ratio_to_f107(days, freq_mhz):
    """Median Phi(freq)/F10.7 across the file, for forecast scaling."""
    br = bracket_for(freq_mhz)
    if br is None:
        return None, 0
    f_low, f_high = br
    ratios = []
    for date, data in days.items():
        pick = pick_station(data, f_low, f_high)
        f107, _, _ = penticton_2800(data)
        if pick and f107:
            phi, _ = log_interp(f_low, pick["low"], f_high, pick["high"],
                                freq_mhz)
            ratios.append(phi / f107)
    return (statistics.median(ratios), len(ratios)) if ratios else (None, 0)


# ==========================================================================
# ASTRONOMY
# ==========================================================================

def julian_day(when):
    """Julian Day from a UTC datetime."""
    y, m = when.year, when.month
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    day_frac = (when.hour + when.minute / 60.0 + when.second / 3600.0) / 24.0
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + when.day + day_frac + b - 1524.5)


def gmst_deg(jd):
    t = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * t * t - t * t * t / 38710000.0)
    return gmst % 360.0


def precess_j2000(ra_deg, dec_deg, jd):
    """IAU 1976 precession from J2000 to the epoch of jd."""
    t = (jd - 2451545.0) / 36525.0
    sec = 1.0 / 3600.0
    zeta = math.radians((2306.2181 * t + 0.30188 * t * t
                         + 0.017998 * t ** 3) * sec)
    z = math.radians((2306.2181 * t + 1.09468 * t * t
                      + 0.018203 * t ** 3) * sec)
    theta = math.radians((2004.3109 * t - 0.42665 * t * t
                          - 0.041833 * t ** 3) * sec)

    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    x = math.cos(dec) * math.cos(ra)
    y = math.cos(dec) * math.sin(ra)
    zc = math.sin(dec)

    # Rz(-zeta) then Ry(theta) then Rz(-z)
    cz, sz = math.cos(zeta), math.sin(zeta)
    x1, y1, z1 = cz * x - sz * y, sz * x + cz * y, zc
    ct, st = math.cos(theta), math.sin(theta)
    x2, y2, z2 = ct * x1 - st * z1, y1, st * x1 + ct * z1
    cZ, sZ = math.cos(z), math.sin(z)
    x3, y3, z3 = cZ * x2 - sZ * y2, sZ * x2 + cZ * y2, z2

    return math.degrees(math.atan2(y3, x3)) % 360.0, math.degrees(math.asin(z3))


def refraction_arcmin(elev_deg):
    """Bennett's formula. Returns the amount to ADD to true elevation."""
    if elev_deg < -1.0:
        return 0.0
    return 1.0 / math.tan(math.radians(elev_deg + 7.31 / (elev_deg + 4.4)))


def radec_to_azel(ra_deg, dec_deg, when, lat=SITE_LAT, lon=SITE_LON):
    jd = julian_day(when)
    lst = (gmst_deg(jd) + lon) % 360.0
    ha = math.radians((lst - ra_deg) % 360.0)
    dec, phi = math.radians(dec_deg), math.radians(lat)

    sin_alt = (math.sin(dec) * math.sin(phi)
               + math.cos(dec) * math.cos(phi) * math.cos(ha))
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))

    denom = math.cos(math.radians(alt)) * math.cos(phi)
    if abs(denom) < 1e-12:
        az = 0.0
    else:
        cos_az = (math.sin(dec) - math.sin(math.radians(alt)) * math.sin(phi)) / denom
        az = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
        if math.sin(ha) > 0:
            az = 360.0 - az

    return az % 360.0, alt, math.degrees(ha) / 15.0


def transit_utc(ra_deg, date, lon=SITE_LON):
    """UTC hour of upper culmination on the given UTC date."""
    midnight = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
    g0 = gmst_deg(julian_day(midnight))
    hours = ((ra_deg - lon - g0) % 360.0) / 360.0 * 24.0 / 1.0027379093
    return hours % 24.0


def hours_above(dec_deg, elev_limit, lat=SITE_LAT):
    """Hours per sidereal day above elev_limit. None => circumpolar/never."""
    dec, phi, h0 = math.radians(dec_deg), math.radians(lat), math.radians(elev_limit)
    denom = math.cos(phi) * math.cos(dec)
    if abs(denom) < 1e-12:
        return None
    cos_ha = (math.sin(h0) - math.sin(phi) * math.sin(dec)) / denom
    if cos_ha <= -1.0:
        return 24.0
    if cos_ha >= 1.0:
        return 0.0
    return 2.0 * math.degrees(math.acos(cos_ha)) / 15.0


def star_flux_jy(key, freq_mhz, when):
    """Baars 1977 flux with secular decay. None if no model is shipped."""
    star = RADIO_STARS[key]
    model = star.get("baars")
    if not model:
        return None
    lo, hi = model["valid_mhz"]
    log_s = model["a"] + model["b"] * math.log10(freq_mhz)
    flux = 10.0 ** log_s
    years = (when.year + when.timetuple().tm_yday / 365.25) - model["epoch"]
    rate = model["decay_pct_per_yr_1ghz"] * (freq_mhz / 1000.0) ** model["decay_index"]
    flux *= (1.0 - rate / 100.0) ** years
    return {"flux_jy": flux, "decay_pct_per_yr": rate, "years": years,
            "in_range": lo <= freq_mhz <= hi}


def sun_geometry(date, lat=SITE_LAT, lon=SITE_LON):
    jd = julian_day(dt.datetime(date.year, date.month, date.day, 12,
                                tzinfo=dt.timezone.utc))
    n = jd - 2451545.0
    mean_lon = (280.460 + 0.9856474 * n) % 360.0
    mean_anom = math.radians((357.528 + 0.9856003 * n) % 360.0)
    ecl = math.radians(mean_lon + 1.915 * math.sin(mean_anom)
                       + 0.020 * math.sin(2 * mean_anom))
    obl = math.radians(23.439 - 0.0000004 * n)
    dec = math.degrees(math.asin(math.sin(obl) * math.sin(ecl)))
    ra = math.degrees(math.atan2(math.cos(obl) * math.sin(ecl),
                                 math.cos(ecl))) % 360.0
    eot = 4.0 * (((mean_lon - ra) + 180.0) % 360.0 - 180.0)
    radius = (1.00014 - 0.01671 * math.cos(mean_anom)
              - 0.00014 * math.cos(2 * mean_anom))
    return {
        "declination_deg": dec,
        "solar_noon_utc": (12.0 - lon / 15.0 - eot / 60.0) % 24.0,
        "max_elevation_deg": 90.0 - abs(lat - dec),
        "equation_of_time_min": eot,
        "sun_diameter_deg": 0.533128 / radius,
        "earth_sun_au": radius,
        "hours_above_limit": hours_above(dec, MIN_TRACK_ELEV),
    }


def hhmm(hours):
    total = int(round(hours * 60.0)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


# ==========================================================================
# ANTENNA
# ==========================================================================

def ant_bw_deg(ant, band_key):
    """3 dB beamwidth: the chart value if present, else 70*lambda/D."""
    spec = ant["bands"][band_key]
    if spec.get("bw"):
        return spec["bw"], "chart"
    lam = C_LIGHT / (band_centre(ant, band_key) * 1e6)
    return 70.0 * lam / ant["diam"], "est 70L/D"


def ant_tsys(ant, band_key):
    """Operating Tsys. Prefer the value implied by gain and published G/T,
    since that is the one that reproduces the published figure."""
    spec = ant["bands"][band_key]
    if spec.get("gain") is not None and spec.get("gt") is not None:
        return 10.0 ** ((spec["gain"] - spec["gt"]) / 10.0), "implied"
    if spec.get("tsys"):
        return spec["tsys"], "listed"
    return None, "unknown"


def beam_correction(bw_deg, source_size_deg):
    ratio = source_size_deg / bw_deg
    factor = 1.0 + 0.38 * ratio ** 2
    if ratio <= 0.5:
        verdict, note = "GOOD", "source well inside the beam"
    elif ratio <= 1.0:
        verdict, note = "OK", "correction valid; keep it in the error budget"
    elif ratio <= 1.5:
        verdict, note = "MARGINAL", "quadratic fit at its limit"
    else:
        verdict, note = "INVALID", "source over-fills the beam"
    return {"bw_deg": bw_deg, "ratio": ratio,
            "correction_db": 10.0 * math.log10(factor),
            "verdict": verdict, "note": note}


def gt_from_y(y_db, phi_sfu, freq_mhz, correction_db):
    y_lin = 10.0 ** (y_db / 10.0)
    if y_lin <= 1.0:
        return None
    lam = C_LIGHT / (freq_mhz * 1e6)
    gt = (8.0 * math.pi * K_BOLTZMANN * (y_lin - 1.0)
          / (lam ** 2 * phi_sfu * SFU))
    return 10.0 * math.log10(gt) + correction_db


def predicted_y_db(ant, band_key, phi_sfu):
    """Expected raw Y-factor for a source of flux phi_sfu."""
    tsys, _ = ant_tsys(ant, band_key)
    if tsys is None:
        return None
    a_eff = eff_aperture(ant, band_key)
    return 10.0 * math.log10(
        1.0 + phi_sfu * SFU * a_eff / (2.0 * K_BOLTZMANN * tsys))


def predicted_y_star_db(ant, band_key, flux_jy):
    return predicted_y_db(ant, band_key, flux_jy * JY / SFU)


# ==========================================================================
# SESSION
# ==========================================================================

class Session:
    def __init__(self, ui, date=None):
        self.ui = ui
        self.days, self.rad_issued = {}, None
        self.outlook, self.outlook_issued = [], None
        self.errors = []
        self.today = dt.datetime.now(dt.timezone.utc).date()
        self.target = date or self.today
        self.flux = {}          # (ant_id, band) -> solve_flux result

    def load(self):
        try:
            self.days, self.rad_issued = parse_radio_flux(fetch(RAD_URL))
        except Exception as exc:
            self.errors.append(f"solar radio flux fetch failed: {exc}")
        try:
            self.outlook, self.outlook_issued = parse_outlook(fetch(OUTLOOK_URL))
        except Exception as exc:
            self.errors.append(f"27-day outlook fetch failed: {exc}")
        self.flux = {}
        for ant in active_antennas():
            for bk in ant["bands"]:
                self.flux[(ant["id"], bk)] = (
                    solve_flux(self.days, band_centre(ant, bk), self.target)
                    if self.days else None)
        return self

    def geom(self):
        return sun_geometry(self.target)

    def rows(self):
        for ant in active_antennas():
            for bk in BAND_ORDER:
                if bk in ant["bands"]:
                    yield ant, bk


# ==========================================================================
# VIEWS
# ==========================================================================

def view_inventory(sess):
    ui = sess.ui
    ui.title("ANTENNA INVENTORY -- NOAA NESDIS Fairbanks")
    print(f"  {'Antenna':<16}{'Msn':<7}{'Bd':<4}{'Feed':<6}{'Range MHz':>13}"
          f"{'Gain':>7}{'BW':>7}{'Tsys':>8}{'pub G/T':>9}  pol")
    for ant in ANTENNAS:
        if not is_active(ant):
            print(f"  {ant['label']:<16}" +
                  ui.red("DECOMMISSIONED -- permanently non-operational, "
                         "scheduled for destruction"))
            continue
        if not ant["bands"]:
            continue
        for bk in BAND_ORDER:
            if bk not in ant["bands"]:
                continue
            sp = ant["bands"][bk]
            g = f"{sp['gain']:.1f}" if sp.get("gain") else "-"
            bw = f"{sp['bw']:.3f}d" if sp.get("bw") else "-"
            ts = f"{sp['tsys']:.1f}" if sp.get("tsys") else "-"
            gt = f"{sp['gt']:.2f}" if sp.get("gt") else "-"
            print(f"  {ant['label']:<16}{ant['mission']:<7}{bk:<4}"
                  f"{sp.get('feed', ''):<6}"
                  f"{sp['range'][0]:>6.0f}-{sp['range'][1]:<6.0f}"
                  f"{g:>7}{bw:>7}{ts:>8}{gt:>9}  {sp.get('pol', '')}")

    ui.section("CHART SELF-CONSISTENCY")
    print("  Does gain - 10log10(Tsys) reproduce the published G/T?")
    print(f"  {'Antenna':<16}{'Bd':<4}{'G-10logT':>10}{'pub G/T':>9}"
          f"{'delta':>8}{'implied Tsys':>14}")
    bad = []
    for ant, bk in sess.rows():
        sp = ant["bands"][bk]
        if not (sp.get("gain") and sp.get("tsys") and sp.get("gt")):
            continue
        calc = sp["gain"] - 10.0 * math.log10(sp["tsys"])
        delta = calc - sp["gt"]
        imp = 10.0 ** ((sp["gain"] - sp["gt"]) / 10.0)
        flag = ui.red(f"{delta:+.2f}") if abs(delta) > 1.0 else f"{delta:+.2f}"
        print(f"  {ant['label']:<16}{bk:<4}{calc:>10.2f}{sp['gt']:>9.2f}"
              f"{flag:>8}{imp:>10.1f} K")
        if abs(delta) > 1.0:
            bad.append((ant["label"], bk, delta, imp, sp["tsys"]))
    if bad:
        ui.warn("Rows flagged above do not close. The consistent ~2.3x Tsys "
                "ratio on the 21 M (both bands) is the signature of a G/T "
                "published at a LOW ELEVATION while the Tsys column is a "
                "zenith figure.")
        ui.warn("RESOLVE THIS BEFORE USING THE CHART AS PASS/FAIL. On the "
                "21 M it moves the acceptance threshold by over 3 dB.")
    ui.tip("Predicted Y-factors in this tool use the IMPLIED Tsys "
           "(gain - published G/T), because that is the value that "
           "reproduces the published figure you will be measured against.")


def view_flux(sess):
    ui = sess.ui
    ui.title(f"SOLAR FLUX PER ANTENNA/BAND  --  {sess.target} UTC")
    print(f" Site: {SITE_NAME}   SWPC issued: {sess.rad_issued}")

    geom = sess.geom()
    ui.section("SUN RUN WINDOW")
    print(f"  Solar noon {hhmm(geom['solar_noon_utc'])} UTC   "
          f"dec {geom['declination_deg']:+.2f}d   "
          f"max elev {geom['max_elevation_deg']:.1f}d   "
          f"diameter {geom['sun_diameter_deg']:.4f}d")
    elev = geom["max_elevation_deg"]
    if elev < 10:
        ui.warn(f"NO-GO. {elev:.1f}d peak. Fairbanks sun runs are impossible "
                f"October through February.")
    elif elev < 20:
        ui.caution(f"POOR. {elev:.1f}d peak.")
    elif elev < 30:
        ui.caution(f"USABLE. {elev:.1f}d peak. Correct per ITU-R P.676 and "
                   f"state the elevation.")
    else:
        ui.ok(f"GOOD. {elev:.1f}d peak elevation.")

    ui.section("INTERPOLATED FLUX AT EACH TEST FREQUENCY")
    print(f"  {'Antenna':<16}{'Bd':<4}{'Ftest':>8}{'bracket':>13}"
          f"{'low sfu':>9}{'high sfu':>10}{'k':>7}{'PHI':>9}  src/age")
    for ant, bk in sess.rows():
        fc = band_centre(ant, bk)
        r = sess.flux.get((ant["id"], bk))
        if not r:
            reason = ("no RSTN bracket above 15400 MHz"
                      if bracket_for(fc) is None else "no station data")
            print(f"  {ant['label']:<16}{bk:<4}{fc:>7.0f}M  " +
                  ui.red(reason))
            continue
        age = "" if r["age_days"] == 0 else f" +{r['age_days']}d"
        print(f"  {ant['label']:<16}{bk:<4}{fc:>7.0f}M"
              f"{r['f_low']:>6.0f}/{r['f_high']:<6.0f}"
              f"{r['low_sfu']:>9.1f}{r['high_sfu']:>10.1f}{r['k']:>7.3f}"
              f"{r['phi_sfu']:>9.1f}  {r['station'][:8]}{age}")

    stale = [r for r in sess.flux.values() if r and r["age_days"] >= 2]
    if stale:
        ui.caution(f"{len(stale)} entries are 2+ days old. RSTN noon values "
                   f"post hours after each station's local noon; pull fresh "
                   f"at test time.")
    single = [r for r in sess.flux.values() if r and not r["alternatives"]]
    if single:
        ui.warn(f"{len(single)} entries come from a SINGLE station with no "
                f"cross-check. Since Sagamore Hill was lost, San Vito is the "
                f"only 8800 MHz source, so every X-band figure is unverifiable.")
    for r in sess.flux.values():
        for f in (r["burst_flags"] if r else []):
            ui.warn(f"POSSIBLE BURST: {f}")

    ui.section("SUN BEAM CORRECTION (measured beamwidths where available)")
    print(f"  {'Antenna':<16}{'Bd':<4}{'BW':>9}  {'src':<10}{'sun/beam':>9}"
          f"{'corr':>9}{'Y pred':>9}   verdict")
    for ant, bk in sess.rows():
        bw, src = ant_bw_deg(ant, bk)
        bc = beam_correction(bw, geom["sun_diameter_deg"])
        r = sess.flux.get((ant["id"], bk))
        y = predicted_y_db(ant, bk, r["phi_sfu"]) if r else None
        ystr = f"{y:.1f}dB" if y is not None else "-"
        print(f"  {ant['label']:<16}{bk:<4}{bw:>8.3f}d  {src:<10}"
              f"{bc['ratio']:>9.2f}{bc['correction_db']:>8.2f}dB{ystr:>9}"
              f"   {ui.verdict(bc['verdict'])}")
    ui.tip("Where the chart gives a measured beamwidth it is used directly -- "
           "it beats any k*lambda/D estimate. The 21 M runs ~84% efficient, "
           "so a 70L/D formula under-predicts its correction by ~1 dB.")


def view_forecast(sess):
    ui = sess.ui
    ui.title("7-DAY FLUX PROJECTION")
    if not sess.outlook:
        ui.warn("27-day outlook unavailable.")
        return
    print(f" SWPC 27-day outlook issued {sess.outlook_issued}")

    freqs = sorted({band_centre(a, b) for a, b in sess.rows()
                    if bracket_for(band_centre(a, b))})
    scale = {f: flux_ratio_to_f107(sess.days, f) for f in freqs}

    ui.section("SCALING BASIS  (Phi = ratio x predicted F10.7)")
    for f in freqs:
        r, n = scale[f]
        users = ", ".join(sorted({a["label"] for a, b in sess.rows()
                                  if abs(band_centre(a, b) - f) < 0.01}))
        print(f"  {f:>7.0f} MHz  ratio {r:.3f}  ({n} days)   {users}"
              if r else f"  {f:>7.0f} MHz  no basis")

    ui.section("PROJECTION")
    head = "".join(f"{f:>9.0f}" for f in freqs)
    print(f"  {'Date':<12}{'F10.7':>7}{head}{'SunEl':>8}{'Ap':>5}  window")
    for date, f107, ap, kp in [r for r in sess.outlook
                               if r[0] >= sess.today][:7]:
        g = sun_geometry(date)
        cells = "".join(
            f"{f107 * scale[f][0]:>9.0f}" if scale[f][0] else f"{'-':>9}"
            for f in freqs)
        el = g["max_elevation_deg"]
        tag = ("GOOD" if el >= 30 else "USABLE" if el >= 20
               else "POOR" if el >= 10 else "NO-GO")
        print(f"  {str(date):<12}{f107:>7.0f}{cells}{el:>7.1f}d{ap:>5.0f}  "
              f"{ui.verdict(tag)}")
    print()
    ui.warn("PLANNING ONLY. F10.7 forecasts run +/-10-15 sfu and cannot "
            "predict a burst. Never compute a delivered G/T from these.")


def view_stars(sess):
    ui = sess.ui
    now = dt.datetime.now(dt.timezone.utc)
    ui.title(f"RADIO STARS  --  {now:%Y-%m-%d %H:%M} UTC")
    jd = julian_day(now)

    ui.section("POSITION NOW (precessed to date, refraction included)")
    print(f"  {'Source':<8}{'RA(date)':>12}{'Dec':>10}{'AZ':>9}{'EL':>8}"
          f"{'Transit':>9}{'TrEl':>8}{'MinEl':>8}   status")
    for key, star in RADIO_STARS.items():
        ra, dec = precess_j2000(star["ra_j2000_deg"], star["dec_j2000_deg"], jd)
        az, el, ha = radec_to_azel(ra, dec, now)
        el_app = el + refraction_arcmin(el) / 60.0
        mn = dec + SITE_LAT - 90.0
        status = (ui.green("circumpolar") if mn >= MIN_TRACK_ELEV
                  else ui.green("UP") if el >= MIN_TRACK_ELEV
                  else ui.red("below limit"))
        rh = ra / 15.0
        print(f"  {key:<8}"
              f"{f'{int(rh):02d}h{int((rh % 1) * 60):02d}m':>12}"
              f"{dec:>9.3f}d{az:>8.2f}d{el_app:>7.2f}d"
              f"{hhmm(transit_utc(ra, now.date())):>9}"
              f"{90 - abs(SITE_LAT - dec):>7.2f}d{mn:>7.2f}d   {status}")

    ui.section("STAR OPTION PER ANTENNA/BAND")
    print(f"  {'Antenna':<16}{'Bd':<4}{'Ftest':>8}  " +
          "".join(f"{k:>14}" for k in RADIO_STARS if RADIO_STARS[k]["baars"]))
    for ant, bk in sess.rows():
        fc = band_centre(ant, bk)
        bw, _ = ant_bw_deg(ant, bk)
        cells = ""
        for sk in RADIO_STARS:
            if not RADIO_STARS[sk]["baars"]:
                continue
            m = star_flux_jy(sk, fc, now)
            y = predicted_y_star_db(ant, bk, m["flux_jy"])
            bc = beam_correction(bw, RADIO_STARS[sk]["size_arcmin"] / 60.0)
            if y is None:
                cells += f"{'-':>14}"
            else:
                mark = "" if y >= 1.0 else "!"
                cell = "{:.2f}dB{}/{:.2f}".format(
                    y, mark, bc["correction_db"])
                cells += "{:>14}".format(cell)
        print(f"  {ant['label']:<16}{bk:<4}{fc:>7.0f}M  {cells}")
    print("  cells are  Y / beam-correction dB.  ! = Y under 1 dB, "
          "radiometer-stability limited.")
    ui.caution("Baars 1977 + secular decay. Use Perley & Butler 2017 for a "
               "contractual result.")

    pol_linear = [a["label"] for a, b in sess.rows()
                  if "LINEAR" in (a["bands"][b].get("pol") or "")]
    if pol_linear:
        ui.warn("ROTATABLE LINEAR polarization on: " +
                ", ".join(sorted(set(pol_linear))) +
                ". Tau A is ~7% linearly polarized, so on a linear feed its "
                "apparent flux depends on feed rotation angle. Either use "
                "Cas A (~1% polarized) or record the rotation angle and "
                "correct for it.")

    ui.section("PER-SOURCE DETAIL")
    for key, star in RADIO_STARS.items():
        print(f"\n  {ui.bold(key)}  {star['name']}   "
              f"extent ~{star['size_arcmin']:.0f}'   "
              f"pol ~{star['polarization_pct']:.0f}%")
        print(f"    {ui.green('PROS')}")
        ui.bullets(star["pros"], marker="      + ", indent="        ")
        print(f"    {ui.yellow('CONS')}")
        ui.bullets(star["cons"], marker="      - ", indent="        ")


def view_advisor(sess):
    ui = sess.ui
    ui.title("METHOD ADVISOR -- PER ANTENNA, PER BAND")
    now = dt.datetime.now(dt.timezone.utc)
    sun_size = sess.geom()["sun_diameter_deg"]

    for ant, bk in sess.rows():
        fc = band_centre(ant, bk)
        bw, bwsrc = ant_bw_deg(ant, bk)
        sbc = beam_correction(bw, sun_size)
        r = sess.flux.get((ant["id"], bk))
        sun_y = predicted_y_db(ant, bk, r["phi_sfu"]) if r else None

        best, best_y, best_bc = None, -99.0, None
        for sk in RADIO_STARS:
            m = star_flux_jy(sk, fc, now)
            if not m:
                continue
            y = predicted_y_star_db(ant, bk, m["flux_jy"])
            if y is not None and y > best_y:
                best, best_y = sk, y
                best_bc = beam_correction(
                    bw, RADIO_STARS[sk]["size_arcmin"] / 60.0)

        print()
        print(f"  {ui.bold(ant['label'])}  {bk} @ {fc:.0f} MHz   "
              f"beam {bw:.3f}d ({bwsrc})")
        ys = f"{sun_y:.1f} dB" if sun_y is not None else "n/a"
        print(f"    SUN  : corr {sbc['correction_db']:+5.2f} dB, "
              f"sun/beam {sbc['ratio']:.2f}, Y ~{ys}   "
              f"[{ui.verdict(sbc['verdict'])}]")
        if best:
            print(f"    STAR : {best} corr {best_bc['correction_db']:+5.2f} dB,"
                  f" Y ~{best_y:.2f} dB   [{ui.verdict(best_bc['verdict'])}]")

        if r is None and bracket_for(fc) is None:
            ui.warn(f"No RSTN flux exists above 15400 MHz, so there is NO "
                    f"solar flux for {fc:.0f} MHz. And the sun over-fills "
                    f"this beam ({sbc['ratio']:.1f}x). Radio stars are far "
                    f"too weak here. Use a calibrated noise source or "
                    f"hot/cold load with a measured pattern.")
        elif sbc["ratio"] > 1.5:
            if best_y >= 1.0:
                ui.warn(f"USE {best}, NOT THE SUN. Sun is "
                        f"{sbc['ratio']:.1f} beamwidths wide and needs "
                        f"{sbc['correction_db']:.1f} dB of correction.")
            else:
                ui.warn(f"Neither source is clean: sun needs "
                        f"{sbc['correction_db']:.1f} dB, best star gives only "
                        f"{best_y:.2f} dB of Y. Use noise injection or a "
                        f"hot/cold load.")
        elif sbc["ratio"] > 1.0:
            if best_y is not None and best_y >= 1.0:
                ui.caution(f"Sun usable but {sbc['correction_db']:.1f} dB "
                           f"correction is at the fit limit. Prefer {best} "
                           f"({best_y:.2f} dB Y).")
            else:
                ui.caution(f"SUN, with care -- it is your only option. "
                           f"{sbc['correction_db']:.1f} dB correction is at "
                           f"the fit limit and stars are too weak "
                           f"({best} {best_y:.2f} dB). State the correction "
                           f"as your dominant uncertainty.")
        else:
            if best_y is not None and best_y < 0.5:
                ui.ok(f"SUN. Only {sbc['correction_db']:.2f} dB correction; "
                      f"stars too weak here ({best_y:.2f} dB).")
            else:
                ui.ok(f"SUN preferred ({sbc['correction_db']:.2f} dB). "
                      f"{best} is a valid independent check at "
                      f"{best_y:.2f} dB.")

    ui.section("SUN -- PROS");   ui.bullets(SUN_PROS, "  + ", "    ")
    ui.section("SUN -- CONS");   ui.bullets(SUN_CONS, "  - ", "    ")
    ui.section("STARS -- PROS"); ui.bullets(STAR_PROS, "  + ", "    ")
    ui.section("STARS -- CONS"); ui.bullets(STAR_CONS, "  - ", "    ")


def view_datron(sess):
    ui = sess.ui
    ui.title("DATRON ACU 'AUTO G/T' INPUT SHEET")
    ui.warn("The flux values MUST correspond to the frequencies typed in the "
            "same fields. Entering band edges as Low/High Freq while using "
            "raw RSTN flux values forces the interpolation to the midpoint "
            "and biases G/T by 0.3-0.6 dB.")
    ui.tip("Enter the RSTN frequencies below and let the ACU interpolate. "
           "That way the flux values are MEASURED, not derived.")

    for ant, bk in sess.rows():
        fc = band_centre(ant, bk)
        r = sess.flux.get((ant["id"], bk))
        bw, _ = ant_bw_deg(ant, bk)
        bc = beam_correction(bw, sess.geom()["sun_diameter_deg"])
        print()
        print(f"  {ui.bold(ant['label'])}   {bk}-band   "
              f"feed {ant['bands'][bk]['range'][0]:.0f}-"
              f"{ant['bands'][bk]['range'][1]:.0f} MHz")
        if not r:
            ui.warn("    no solar flux available -- see the advisor")
            continue
        print(f"      Low  Freq {r['f_low']:>7.0f} MHz    "
              f"Low  Flux {r['low_sfu']:>7.1f}")
        print(f"      Ctr  Freq {fc:>7.0f} MHz")
        print(f"      High Freq {r['f_high']:>7.0f} MHz    "
              f"High Flux {r['high_sfu']:>7.1f}")
        print(f"      -> ACU should interpolate {r['phi_sfu']:.1f} sfu "
              f"(k={r['k']:.3f})")
        note = (ui.red(f"ADD {bc['correction_db']:+.2f} dB")
                if bc["verdict"] in ("MARGINAL", "INVALID")
                else f"add {bc['correction_db']:+.2f} dB")
        print(f"      beam correction if the ACU does NOT apply it: {note}")
        if r["age_days"]:
            ui.caution(f"    flux is {r['age_days']} day(s) old "
                       f"({r['date']}, {r['station']}) -- refresh at test time")
    print()
    ui.section("VERIFY WHAT YOUR ACU ACTUALLY DOES  (two runs)")
    print("  1. Set Low Flux = High Flux = 100.0. The interpolated flux must")
    print("     then be exactly 100.0 regardless of frequencies. Hand-compute")
    print("     G/T with Phi=100 and compare to the display.")
    print("  2. Same fluxes, same centre, run once with the RSTN frequencies")
    print("     and once with your band edges. A ~0.3-0.6 dB difference means")
    print("     it genuinely interpolates and you MUST use RSTN frequencies.")
    print("     No difference means it ignores those fields entirely.")
    ui.tip("Also check the manual for a SECOND set of frequency fields. Some "
           "ACUs configure the feed/LNA band separately from the flux "
           "interpolation -- 'use your feed's band' may be correct advice "
           "about a different field.")


def view_calculator(sess):
    ui = sess.ui
    ui.title("Y-FACTOR -> G/T CALCULATOR")
    rows = list(sess.rows())
    choice = prompt_choice(ui, "Antenna / band", [
        (i, f"{a['label']}  {b} @ {band_centre(a, b):.0f} MHz")
        for i, (a, b) in enumerate(rows)])
    if choice is None:
        return
    ant, bk = rows[choice]
    fc = band_centre(ant, bk)
    now = dt.datetime.now(dt.timezone.utc)

    src = prompt_choice(ui, "Source", [("sun", "Sun (today's flux)")] +
                        [(k, f"{k}  {RADIO_STARS[k]['name']}")
                         for k in RADIO_STARS if RADIO_STARS[k]["baars"]])
    if src is None:
        return
    if src == "sun":
        r = sess.flux.get((ant["id"], bk))
        if not r:
            ui.warn("No solar flux available for this frequency.")
            return
        phi, size = r["phi_sfu"], sess.geom()["sun_diameter_deg"]
        print(f"\n  Flux {phi:.1f} sfu ({r['station']}, {r['date']})")
    else:
        m = star_flux_jy(src, fc, now)
        phi, size = m["flux_jy"] * JY / SFU, RADIO_STARS[src]["size_arcmin"] / 60
        print(f"\n  Flux {m['flux_jy']:.0f} Jy ({phi:.4f} sfu)")

    y_db = prompt_float(ui, "Measured Y-factor in dB", None)
    if y_db is None:
        return
    bw, bwsrc = ant_bw_deg(ant, bk)
    bc = beam_correction(bw, size)
    gt = gt_from_y(y_db, phi, fc, bc["correction_db"])

    ui.section("RESULT")
    if gt is None:
        ui.warn("Y must exceed 0 dB.")
        return
    print(f"  {ant['label']}  {bk} @ {fc:.0f} MHz   beam {bw:.3f}d ({bwsrc})")
    print(f"  source/beam {bc['ratio']:.2f}  [{ui.verdict(bc['verdict'])}]   "
          f"beam correction {bc['correction_db']:+.2f} dB")
    print()
    print(f"  {ui.bold(f'G/T = {gt:.2f} dB/K')}  (before atmosphere)")
    atm = ATM_DB.get(bk, 0.1)
    print(f"  + ~{atm:.2f} dB gaseous at 30d elevation (P.676) "
          f"-> {gt + atm:.2f} dB/K")
    pub = ant["bands"][bk].get("gt")
    if pub:
        d = (gt + atm) - pub
        verdict = (ui.green("within 1 dB of published")
                   if abs(d) <= 1.0 else ui.red(f"{d:+.2f} dB vs published"))
        print(f"  published G/T {pub:.2f} dB/K   ->  {verdict}")
        ui.tip("Confirm what elevation the published G/T is specified at "
               "before treating a delta as pass/fail.")
    if bc["verdict"] == "INVALID":
        ui.warn("Source over-fills the beam; this result is dominated by the "
                "extended-source correction and is not defensible.")
    if y_db > 20:
        ui.caution(f"Y = {y_db:.1f} dB -- verify receive-chain linearity with "
                   f"a calibrated step attenuator.")


def view_stations(sess):
    ui = sess.ui
    ui.title("DATA SOURCE AND STATION STATUS")
    for name, tag, text in STATION_NOTES:
        colour = (ui.red if "OUT OF SERVICE" in tag or "SOLE" in tag
                  else ui.yellow if "ONLY" in tag or "WRONG" in tag
                  else ui.green)
        print(f"\n  {ui.bold(name):<24} {colour(tag)}")
        for line in wrap(text, 70):
            print(f"    {line}")
    ui.section("LIVE ENDPOINTS")
    print(f"  7-day noon flux : {RAD_URL}")
    print(f"  27-day outlook  : {OUTLOOK_URL}")
    print("  Penticton       : https://spaceweather.gc.ca/solarflux/sx-4-en.php")
    if sess.days:
        ui.section("COVERAGE IN THE CURRENT FILE")
        freqs = [1415.0, 2695.0, 4995.0, 8800.0, 2800.0]
        print(f"  {'Date':<12}" + "".join(f"{f:>9.0f}" for f in freqs))
        for date in sorted(sess.days, reverse=True):
            cells = ""
            for f in freqs:
                names = sorted(station_values(sess.days[date], f))
                cells += f"{(names[0][:8] if names else '-'):>9}"
            print(f"  {str(date):<12}{cells}")


def view_procedure(sess):
    ui = sess.ui
    ui.title("PROCEDURE -- DOS AND DON'TS")
    ui.section("DO");     ui.bullets(DOS, "  + ", "    ")
    ui.section("DO NOT"); ui.bullets(DONTS, "  - ", "    ")
    ui.section("REFERENCES")
    for line in [
        "ITU-R S.733-2      Determination of G/T for FSS earth stations",
        "Intelsat IESS-207  Sun-method: Y-factor, interpolation, beam corr",
        "Eutelsat ESOG 120  European antenna verification equivalent",
        "Baars et al. 1977  A&A 61, 99 -- extended source + radio star scale",
        "Perley & Butler    ApJS 230, 7 (2017) -- current flux scale",
        "ITU-R P.676        Gaseous attenuation",
        "NOAA NESDIS        Antenna and RF Systems Capability Chart, Table 1-2",
    ]:
        print(f"  {line}")


# ==========================================================================
# PROMPTS / MENU
# ==========================================================================

def prompt_choice(ui, label, options):
    print()
    print(ui.bold(f"  {label}:"))
    for i, (_, text) in enumerate(options, 1):
        print(f"    {i}) {text}")
    while True:
        try:
            raw = input(f"  {label} [1-{len(options)}, q to cancel]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.lower() in ("q", ""):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print(ui.red("    not a valid choice"))


def prompt_float(ui, label, suggestions):
    hint = (f" (e.g. {', '.join(f'{s:g}' for s in suggestions)})"
            if suggestions else "")
    while True:
        try:
            raw = input(f"  {label}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.lower() in ("q", ""):
            return None
        try:
            return float(raw)
        except ValueError:
            print(ui.red("    enter a number, or q to cancel"))


MENU = [
    ("1", "Antenna inventory and chart consistency check", view_inventory),
    ("2", "Solar flux per antenna/band + beam corrections", view_flux),
    ("3", "7-day flux projection and sun-run window", view_forecast),
    ("4", "Radio stars: AZ/EL, per-antenna Y-factors, pros and cons",
     view_stars),
    ("5", "Method advisor: sun vs star, per antenna per band", view_advisor),
    ("6", "Datron ACU 'Auto G/T' input sheet", view_datron),
    ("7", "Y-factor -> G/T calculator", view_calculator),
    ("8", "Data sources and station status", view_stations),
    ("9", "Procedure: dos and don'ts", view_procedure),
]


def run_menu(sess):
    ui = sess.ui
    while True:
        ui.title(f"G/T CALIBRATION ASSISTANT -- {SITE_NAME}")
        now = dt.datetime.now(dt.timezone.utc)
        geom = sess.geom()
        print(f" {now:%Y-%m-%d %H:%M} UTC   "
              f"solar noon {hhmm(geom['solar_noon_utc'])}   "
              f"sun max el {geom['max_elevation_deg']:.1f}d")
        got = sum(1 for v in sess.flux.values() if v)
        print(f" flux resolved for {got}/{len(sess.flux)} antenna-band "
              f"combinations")
        for err in sess.errors:
            ui.warn(err)
        print()
        for tag, text, _ in MENU:
            print(f"   {ui.bold(tag)}) {text}")
        print(f"   {ui.bold('r')}) refresh data")
        print(f"   {ui.bold('q')}) quit")
        try:
            choice = input("\n select: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice in ("q", "quit", "exit"):
            return
        if choice == "r":
            print(" refreshing...")
            sess.errors.clear()
            sess.load()
            continue
        for tag, _, fn in MENU:
            if choice == tag:
                try:
                    fn(sess)
                except Exception as exc:
                    ui.warn(f"view failed: {exc}")
                try:
                    input("\n [enter to return] ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                break
        else:
            print(ui.red(" unrecognised selection"))


def run_report(sess):
    for _, _, fn in MENU:
        if fn is view_calculator:
            continue
        try:
            fn(sess)
        except Exception as exc:
            sess.ui.warn(f"section failed: {exc}")
    print()


def build_json(sess):
    now = dt.datetime.now(dt.timezone.utc)
    jd = julian_day(now)
    out = {"site": {"name": SITE_NAME, "lat_deg": SITE_LAT,
                    "lon_deg": SITE_LON},
           "generated_utc": now.isoformat(), "target_date": str(sess.target),
           "swpc_issued": sess.rad_issued, "sun": sess.geom(),
           "antennas": [], "radio_stars": {}, "errors": sess.errors}
    for ant, bk in sess.rows():
        fc = band_centre(ant, bk)
        r = sess.flux.get((ant["id"], bk))
        bw, bwsrc = ant_bw_deg(ant, bk)
        bc = beam_correction(bw, sess.geom()["sun_diameter_deg"])
        tsys, tsrc = ant_tsys(ant, bk)
        out["antennas"].append({
            "id": ant["id"], "label": ant["label"], "band": bk,
            "test_freq_mhz": fc, "range_mhz": ant["bands"][bk]["range"],
            "feed": ant["bands"][bk].get("feed"),
            "pol": ant["bands"][bk].get("pol"),
            "published_gt_db": ant["bands"][bk].get("gt"),
            "beamwidth_deg": bw, "beamwidth_source": bwsrc,
            "tsys_k": tsys, "tsys_source": tsrc,
            "sun_beam_correction_db": bc["correction_db"],
            "sun_verdict": bc["verdict"],
            "flux": (dict(r, date=str(r["date"])) if r else None),
        })
    for key, star in RADIO_STARS.items():
        ra, dec = precess_j2000(star["ra_j2000_deg"], star["dec_j2000_deg"], jd)
        az, el, ha = radec_to_azel(ra, dec, now)
        out["radio_stars"][key] = {
            "ra_of_date_deg": ra, "dec_of_date_deg": dec,
            "az_deg": az, "el_deg": el,
            "el_refracted_deg": el + refraction_arcmin(el) / 60.0,
            "transit_utc_h": transit_utc(ra, now.date()),
            "min_elevation_deg": dec + SITE_LAT - 90.0,
        }
    return out


def main():
    ap = argparse.ArgumentParser(
        description="G/T calibration assistant, NOAA NESDIS Fairbanks")
    ap.add_argument("--date", help="UTC day for the flux view, YYYY-MM-DD")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    ui = UI(color=not args.no_color)
    target = (dt.datetime.strptime(args.date, "%Y-%m-%d").date()
              if args.date else None)
    sess = Session(ui, target).load()
    if sess.errors and not sess.days:
        for err in sess.errors:
            ui.warn(err)
        return 1

    if args.json:
        print(json.dumps(build_json(sess), indent=2, default=str))
    elif args.report or not sys.stdin.isatty():
        run_report(sess)
    else:
        run_menu(sess)
    return 0


if __name__ == "__main__":
    sys.exit(main())

