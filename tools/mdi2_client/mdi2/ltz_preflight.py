"""Offline, fail-closed preflight for the captured unmodified LTZ package.

This module never opens a vehicle connection or starts programming.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .calibration_payloads import Calibration, load_stock_package
from .ltz_reference_manifest import LTZ_REFERENCE
from .calibration_readback import parse_f182, calibration_record

# Stock 26_HC_A11 CSM metadata, slots 02–0F, corroborated by the documented
# pre-write radio readback. This is a known SOURCE baseline, not the LTZ target
# and not proof of full payload contents or arbitrary vehicle compatibility.
HIGH_COUNTRY_F182 = bytes.fromhex(
    "62f1820e02053c6e0c4142030509a1bd4141040511b08a414105051e641a4141"
    "06053c6de3414107051cf3a4414108053c6e20414109053c6de841410a053c6de04141"
    "0b0524b69641410c05128ee841420d053c6df041420e0509a22a41410f053c6dec4141")


def identify_source_calibration(calibrations: tuple[Calibration, ...], f182: bytes) -> str:
    """Allow only the documented LTZ or High Country source metadata profiles.

    Unknown, incomplete and mixed profiles fail closed. The expected VIN and
    target package hashes are separate gates in the live workflow.
    """
    observed = parse_f182(f182)
    target = {cal.slot: calibration_record(cal) for cal in calibrations}
    if set(target) != set(range(2, 16)):
        raise ValueError("expected fourteen target calibration slots")
    for name, expected in (("LTZ", target), ("High Country", parse_f182(HIGH_COUNTRY_F182))):
        if all(observed.get(slot) == record for slot, record in expected.items()):
            return name
    raise ValueError("source calibration metadata is not a supported LTZ or High Country baseline")


def validate_ltz_package(folder: Path) -> tuple[Calibration, ...]:
    """Freeze 14 containers and compare them with independently captured hashes.

    A match proves identity with the captured containers, not compatibility
    with the currently connected vehicle or approval to program it.
    """
    loaded = load_stock_package(folder)
    frozen = tuple(Calibration(item.slot, item.part, bytes(item.container)) for item in loaded)
    if len(frozen) != len(LTZ_REFERENCE) or len(frozen) != 14:
        raise ValueError("expected the fourteen captured LTZ calibration slots")
    for item, expected in zip(frozen, LTZ_REFERENCE):
        if (item.slot != expected.slot or item.part != expected.part or
                hashlib.sha256(item.container).hexdigest() != expected.sha256):
            raise ValueError(f"LTZ package mismatch in slot {item.slot:02X}")
    return frozen
