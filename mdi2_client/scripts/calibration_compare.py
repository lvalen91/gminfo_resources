#!/usr/bin/env python3
"""Compare an A11 F182 response with the metadata in cached stock CSM files.

This tool is offline and does not connect to a vehicle or write a calibration.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Record:
    slot: int
    kind: int
    cvn: bytes
    revision: bytes


def parse_f182(data: bytes) -> dict[int, Record]:
    if data.startswith(b"\x62\xf1\x82"):
        data = data[3:]
    if not data or len(data) != 1 + data[0] * 7:
        raise ValueError("F182 length does not match its record count")
    records = {}
    for offset in range(1, len(data), 7):
        slot, kind = data[offset:offset + 2]
        if slot in records:
            raise ValueError(f"duplicate F182 slot {slot:02X}")
        records[slot] = Record(slot, kind, data[offset + 2:offset + 5],
                               data[offset + 5:offset + 7])
    return records


def parse_dps_log(path: Path) -> bytes:
    lines = path.read_text(errors="replace").splitlines()
    for i, line in enumerate(lines):
        match = re.search(r"\b62\s+F1\s+82\s+", line, re.I)
        if not match:
            continue
        parts = [line[match.end():]]
        for continuation in lines[i + 1:]:
            if not continuation.startswith("\t"):
                break
            parts.append(continuation)
        # The terminal [length] is a decimal log annotation, not payload.
        raw = " ".join(parts).split("[")[0]
        values = re.findall(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{2}(?![0-9A-Fa-f])", raw)
        data = bytes.fromhex(" ".join(values))
        parse_f182(data)
        return data
    raise ValueError("no complete F182 response found in DPS log")


def read_package(folder: Path) -> dict[int, tuple[str, Record, str]]:
    records = {}
    for path in sorted(folder.iterdir()):
        if not path.is_file() or not re.fullmatch(r"\d{8}", path.name):
            continue
        try:
            data = gzip.decompress(path.read_bytes())
        except (OSError, EOFError):
            continue
        if len(data) < 0x36A or data[6:10] != b"CSM\x00" or data[0x368:0x36A] != b"\x1f\x8b":
            continue
        slot = data[3]
        if slot in records:
            raise ValueError(f"duplicate package slot {slot:02X}")
        # Mini-record: revision[2], type[1], CVN[3].
        record = Record(slot, data[0x364], data[0x365:0x368], data[0x362:0x364])
        records[slot] = (path.name, record, hashlib.sha256(data).hexdigest())
    if set(records) != set(range(2, 16)):
        raise ValueError("package does not contain exactly slots 02 through 0F")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--f182", help="F182 response as hex, with or without 62 F1 82")
    source.add_argument("--dps-log", type=Path, help="existing DPS communication log")
    parser.add_argument("packages", type=Path, nargs="+", help="stock calibration cache directories")
    args = parser.parse_args()
    radio = parse_f182(bytes.fromhex(args.f182) if args.f182 else parse_dps_log(args.dps_log))
    for folder in args.packages:
        package = read_package(folder)
        print(f"{folder.name}:")
        matches = 0
        for slot, (part, expected, _) in sorted(package.items()):
            observed = radio.get(slot)
            matched = observed == expected
            matches += matched
            print(f"  {slot:02X}  part {part}  {'MATCH' if matched else 'MISMATCH' if observed else 'NOT REPORTED'}")
        print(f"  {matches}/14 match type, CVN and revision; not a payload hash or vehicle compatibility check")


if __name__ == "__main__":
    main()
