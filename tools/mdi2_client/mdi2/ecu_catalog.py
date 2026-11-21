"""GM ECU and DID catalog: static protocol metadata, no secrets.

Additive, generic, offline. Data files live in ``mdi2/data/``:

  * ``ecu_map.json`` -- 24 GM T1XX modules: CAN request/response 29-bit IDs,
    security domain suffix, SW-module count, gateway flag.
  * ``did_map.json`` -- ~28 UDS DataIdentifiers (decode format + length) and 4
    routine IDs.

These are protocol identifiers only (addresses, DID numbers, format tags) -- no
VIN, serial, or key material. Ported from carplay/gm_pi/gmtool/gm_ecu.py.

API:
  cat = EcuCatalog()                     # loads both bundled data files
  cat.ecu(0x80)        / cat.ecu("Radio")   -> EcuInfo | None
  cat.did(0xF190)                            -> dict metadata
  cat.did_name(0xF199) / cat.decode(did, raw)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class EcuInfo:
    addr: int
    name: str
    desc: str
    can_req: int
    can_rsp: int
    domain: Optional[str] = None
    sw_modules: int = 0
    gateway: bool = False

    @property
    def addr_hex(self) -> str:
        return f"0x{self.addr:02X}"


@dataclass
class DidResult:
    did: int
    name: str
    raw: Optional[bytes]
    decoded: Optional[str]
    supported: bool

    @property
    def did_hex(self) -> str:
        return f"{self.did:04X}"


class EcuCatalog:
    """Loads ``ecu_map.json`` + ``did_map.json`` and decodes DID payloads."""

    def __init__(self, ecu_map_path: Optional[Path] = None,
                 did_map_path: Optional[Path] = None):
        with open(ecu_map_path or (DATA_DIR / "ecu_map.json")) as f:
            edata = json.load(f)
        self.tester_addr = int(edata.get("tester_addr", "0xF1"), 16)
        self.ecus: Dict[int, EcuInfo] = {}
        self._by_name: Dict[str, int] = {}
        for addr_str, e in edata["ecus"].items():
            addr = int(addr_str, 16)
            self.ecus[addr] = EcuInfo(
                addr=addr,
                name=e["name"],
                desc=e.get("desc", e["name"]),
                can_req=int(e["can_req"], 16),
                can_rsp=int(e["can_rsp"], 16),
                domain=e.get("domain"),
                sw_modules=e.get("sw_modules", 0),
                gateway=e.get("gateway", False),
            )
            self._by_name[e["name"].lower()] = addr

        with open(did_map_path or (DATA_DIR / "did_map.json")) as f:
            ddata = json.load(f)
        self.dids: Dict[int, dict] = {}
        for did_str, meta in ddata["dids"].items():
            base = did_str.split("_")[0]
            try:
                did = int(base, 16)
            except ValueError:
                continue
            self.dids.setdefault(did, meta)
        self.routines: Dict[int, str] = {
            int(k, 16): v["name"] for k, v in ddata.get("routines", {}).items()
        }

    # ------------------------------------------------------------------ ECU
    def ecu(self, key: "int | str") -> Optional[EcuInfo]:
        """Look up an ECU by numeric address or case-insensitive name."""
        if isinstance(key, str):
            key = self._by_name.get(key.lower())
            if key is None:
                return None
        return self.ecus.get(key)

    def all_addrs(self) -> List[int]:
        return sorted(self.ecus.keys())

    def ecu_name(self, addr: int) -> str:
        info = self.ecus.get(addr)
        return info.name if info else f"Unknown(0x{addr:02X})"

    # ------------------------------------------------------------------ DID
    def did(self, did: int) -> dict:
        return self.dids.get(did, {"name": f"DID_{did:04X}", "fmt": "hex"})

    def did_name(self, did: int) -> str:
        return self.did(did)["name"]

    def routine_name(self, rid: int) -> str:
        return self.routines.get(rid, f"RID_{rid:04X}")

    def decode(self, did: int, raw: Optional[bytes]) -> str:
        """Decode a DID payload to a display string per its declared ``fmt``."""
        if raw is None:
            return ""
        fmt = self.did(did).get("fmt", "hex")
        if fmt == "ascii" or fmt == "sw_inventory":
            return _ascii(raw)
        if fmt == "bcd_date":
            return _bcd_date(raw)
        if fmt == "ecuid":
            return raw.hex().upper()
        return raw.hex().upper()


def _ascii(raw: bytes) -> str:
    return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in raw).rstrip(". ")


def _bcd_date(raw: bytes) -> str:
    """GM F199 programming date: 4 BCD bytes YYYYMMDD or 3 bytes YYMMDD."""
    try:
        digits = "".join(f"{b:02X}" for b in raw)
        if len(digits) >= 8:
            return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
        if len(digits) == 6:
            return f"20{digits[0:2]}-{digits[2:4]}-{digits[4:6]}"
    except Exception:
        pass
    return raw.hex().upper()
