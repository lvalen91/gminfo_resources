"""Offline comparison of A11 post-reboot calibration metadata.

Caller must obtain fresh responses after a confirmed reboot. Matching metadata
is not proof of full payload contents, boot animation, or ADB availability.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .calibration_payloads import Calibration


@dataclass(frozen=True)
class Readback:
    matching_slots: tuple[int, ...]
    mismatching_slots: tuple[int, ...]
    programming_error_count: bytes
    boot_information_status: bytes


def parse_f182(f182: bytes) -> dict[int, bytes]:
    """Validate all F182 records, including duplicates outside the cal slots."""
    if not f182.startswith(b"\x62\xf1\x82"):
        raise ValueError("invalid F182 positive response")
    data = f182[3:]
    if not data or len(data) != 1 + data[0] * 7:
        raise ValueError("invalid F182 record count")
    observed: dict[int, bytes] = {}
    for pos in range(1, len(data), 7):
        record = data[pos:pos + 7]
        if record[0] in observed:
            raise ValueError("duplicate F182 slot")
        observed[record[0]] = record
    return observed


def calibration_record(cal: Calibration) -> bytes:
    data = cal.container
    if len(data) < 0x368 or data[3] != cal.slot or data[6:10] != b"CSM\x00":
        raise ValueError("invalid calibration container metadata")
    return bytes([cal.slot, data[0x364]]) + data[0x365:0x368] + data[0x362:0x364]


def compare_post_reboot(calibrations: Sequence[Calibration], f182: bytes,
                        f0f1: bytes, f0f2: bytes) -> Readback:
    """Compare 14 slot metadata records and return raw diagnostic statuses."""
    if len(calibrations) != 14 or [x.slot for x in calibrations] != list(range(2, 16)):
        raise ValueError("expected ordered slots 02–0F")
    observed = parse_f182(f182)
    if not f0f1.startswith(b"\x62\xf0\xf1") or len(f0f1) != 5:
        raise ValueError("invalid F0F1 positive response")
    if not f0f2.startswith(b"\x62\xf0\xf2") or len(f0f2) != 5:
        raise ValueError("invalid F0F2 positive response")
    matching, mismatching = [], []
    for cal in calibrations:
        expected = calibration_record(cal)
        (matching if observed.get(cal.slot) == expected else mismatching).append(cal.slot)
    return Readback(tuple(matching), tuple(mismatching), f0f1[3:], f0f2[3:])
