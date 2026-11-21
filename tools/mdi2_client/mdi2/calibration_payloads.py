"""Validate stock A11 CSM containers and construct their UDS transfer requests.

Pure offline helpers. This module never opens a connection or sends requests.
"""
from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree


@dataclass(frozen=True)
class Calibration:
    slot: int
    part: str
    container: bytes


def load_stock_package(directory: Path) -> list[Calibration]:
    by_slot: dict[int, Calibration] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file() or not re.fullmatch(r"\d{8}", path.name):
            continue
        try:
            data = gzip.decompress(path.read_bytes())
        except (OSError, EOFError):
            continue
        if len(data) < 0x36A or data[6:10] != b"CSM\x00":
            continue
        if data[0x368:0x36B] != b"\x1f\x8b\x08":
            raise ValueError(f"part {path.name}: missing inner gzip")
        try:
            xml = ElementTree.fromstring(gzip.decompress(data[0x368:]))
        except (OSError, EOFError, ElementTree.ParseError) as exc:
            raise ValueError(f"part {path.name}: invalid override XML") from exc
        if xml.tag != "{http://caltools.gm.com/calovride}CalOvrideFile":
            raise ValueError(f"part {path.name}: unexpected XML root")
        slot = data[3]
        if slot in by_slot:
            raise ValueError(f"duplicate slot {slot:02X}")
        by_slot[slot] = Calibration(slot, path.name, data)
    if set(by_slot) != set(range(2, 16)):
        raise ValueError("expected exactly the fourteen calibration slots 02–0F")
    return [by_slot[slot] for slot in sorted(by_slot)]


def transfer_requests(calibration: Calibration, max_request_length: int) -> Iterator[bytes]:
    """Generate one captured-format 34/36/37 sequence, honoring ECU's 74 limit.

    max_request_length includes the service byte and transfer block counter.
    It must be taken from the ECU's positive RequestDownload response when used
    live; 0x0FFF was observed in one historical transaction.
    """
    data = calibration.container
    if not data or len(data) > 0xFFFFFFFF:
        raise ValueError("invalid container size")
    if type(max_request_length) is not int or not 3 <= max_request_length <= 0xFFFF:
        raise ValueError("invalid maximum request length")
    yield b"\x34\x00\x44" + bytes(4) + len(data).to_bytes(4, "big")
    block_size = max_request_length - 2
    for index, offset in enumerate(range(0, len(data), block_size), 1):
        yield b"\x36" + bytes([index & 0xFF]) + data[offset:offset + block_size]
    yield b"\x37"
