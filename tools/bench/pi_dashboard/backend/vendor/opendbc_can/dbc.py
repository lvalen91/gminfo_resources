"""DBC parser + signal bit-extraction, vendored from commaai/opendbc (opendbc/can/dbc.py).

STANDALONE TRIM: the upstream file imports a per-car checksum function from every
`opendbc.car.<brand>` module (honda/toyota/hyundai/tesla/ford/...), which transitively
pulls in numpy and the whole car-fingerprinting package -- exactly the heavy, car-specific
machinery this read-only bench panel must NOT drag in. We parse plain hand-written DBCs
with no checksum/counter signals, so the checksum table is dropped and `get_checksum_state`
always returns None. The Signal bit-extraction (`get_raw_value`) and the BO_/SG_/VAL_
parsing are copied byte-for-byte from upstream -- that is the load-bearing, correctness-
critical logic and is left untouched. Upstream commit: 66b4002. MIT-licensed (see LICENSE).
"""
import re
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache


class SignalType:
  DEFAULT = 0
  COUNTER = 1


@dataclass
class Signal:
  name: str
  start_bit: int
  msb: int
  lsb: int
  size: int
  is_signed: bool
  factor: float
  offset: float
  is_little_endian: bool
  type: int = SignalType.DEFAULT
  calc_checksum: 'Callable[[int, Signal, bytearray], int] | None' = None
  checksum_fields: tuple['Signal', ...] = ()
  max_counter: int = field(init=False)  # a counter's last value before it wraps to 0
  counter_shift: int = 0  # where this signal's bits go in a counter split across signals

  def __post_init__(self):
    self.max_counter = (1 << self.size) - 1

  def get_raw_value(self, dat: bytes | bytearray) -> int:
    ret = 0
    i = self.msb // 8
    bits = self.size
    while 0 <= i < len(dat) and bits > 0:
      lsb = self.lsb if (self.lsb // 8) == i else i * 8
      msb = self.msb if (self.msb // 8) == i else (i + 1) * 8 - 1
      size = msb - lsb + 1
      d = (dat[i] >> (lsb - (i * 8))) & ((1 << size) - 1)
      ret |= d << (bits - size)
      bits -= size
      i = i - 1 if self.is_little_endian else i + 1
    return ret


@dataclass
class Msg:
  name: str
  address: int
  size: int
  sigs: dict[str, Signal]


@dataclass
class Val:
  name: str
  address: int
  def_val: str


BO_RE = re.compile(r"^BO_ (\w+) (\w+) *: (\w+) (\w+)")
SG_RE = re.compile(r"^SG_ (\w+) : (\d+)\|(\d+)@(\d)([+-]) \(([0-9.+\-eE]+),([0-9.+\-eE]+)\) \[[0-9.+\-eE]+\|[0-9.+\-eE]+\] \".*\" .*")
SGM_RE = re.compile(r"^SG_ (\w+) (\w+) *: (\d+)\|(\d+)@(\d)([+-]) \(([0-9.+\-eE]+),([0-9.+\-eE]+)\) \[[0-9.+\-eE]+\|[0-9.+\-eE]+\] \".*\" .*")
VAL_RE = re.compile(r"^VAL_ (\w+) (\w+) (.*);")
VAL_SPLIT_RE = re.compile(r'["]+')


@cache
class DBC:
  def __init__(self, name: str):
    if os.path.exists(name):
      self._parse_file(name)
    else:
      raise FileNotFoundError(f"DBC not found: {name}")

  def _parse_file(self, path: str):
    self.name = os.path.basename(path).replace(".dbc", "")
    with open(path) as f:
      lines = f.readlines()
    self._parse_lines(lines)

  def _parse_content(self, name: str, content: str):
    self.name = name
    lines = content.splitlines(keepends=True)
    self._parse_lines(lines)

  def _parse_lines(self, lines: list[str]):

    self.checksum_state = checksum_state = get_checksum_state(self.name)
    be_bits = [j + i * 8 for i in range(64) for j in range(7, -1, -1)]
    self.msgs: dict[int, Msg] = {}
    self.addr_to_msg: dict[int, Msg] = {}
    self.name_to_msg: dict[str, Msg] = {}
    self.vals: list[Val] = []
    address = 0
    signals_temp: dict[int, dict[str, Signal]] = {}
    for line_num, line in enumerate(lines, 1):
      line = line.strip()
      if line.startswith("BO_ "):
        m = BO_RE.match(line)
        if not m:
          continue
        address = int(m.group(1), 0)
        msg_name = m.group(2)
        size = int(m.group(3), 0)
        sigs = {}
        self.msgs[address] = Msg(msg_name, address, size, sigs)
        self.addr_to_msg[address] = self.msgs[address]
        self.name_to_msg[msg_name] = self.msgs[address]
        signals_temp[address] = sigs
      elif line.startswith("SG_ "):
        m = SG_RE.search(line)
        offset = 0
        if not m:
          m = SGM_RE.search(line)
          if not m:
            continue
          offset = 1
        sig_name = m.group(1)
        start_bit = int(m.group(2 + offset))
        size = int(m.group(3 + offset))
        is_little_endian = m.group(4 + offset) == "1"
        is_signed = m.group(5 + offset) == "-"
        factor = float(m.group(6 + offset))
        offset_val = float(m.group(7 + offset))

        if is_little_endian:
          lsb = start_bit
          msb = start_bit + size - 1
        else:
          idx = be_bits.index(start_bit)
          lsb = be_bits[idx + size - 1]
          msb = start_bit

        sig = Signal(sig_name, start_bit, msb, lsb, size, is_signed, factor, offset_val, is_little_endian)
        set_signal_type(sig, checksum_state, self.name, line_num, address)
        signals_temp[address][sig_name] = sig
      elif line.startswith("VAL_ "):
        m = VAL_RE.search(line)
        if not m:
          continue
        val_addr = int(m.group(1), 0)
        sgname = m.group(2)
        defs = m.group(3)
        words = [w.strip() for w in VAL_SPLIT_RE.split(defs) if w.strip()]
        words = [w.upper().replace(" ", "_") for w in words]
        val_def = " ".join(words).strip()
        self.vals.append(Val(sgname, val_addr, val_def))
    for addr, sigs in signals_temp.items():
      self.msgs[addr].sigs = sigs


@dataclass
class ChecksumState:
  checksum_type: int
  calc_checksum: Callable[[int, Signal, bytearray], int] | None
  setup_signal: Callable[[Signal, str, int], None] | None = None
  ignore_checksum: bool = False
  ignore_counter: bool = False
  checksum_pattern: str = r"^CHECKSUM$"
  checksum_fields: dict[int, tuple[str, ...]] | None = None


def get_checksum_state(dbc_name: str) -> ChecksumState | None:
  # Trimmed: this vendored copy serves hand-written bench DBCs with no checksum/counter
  # signals, so no per-car checksum table is carried. Upstream returns a ChecksumState for
  # ~20 car brands here; we return None (no checksum/counter handling) for every DBC.
  return None


def set_signal_type(sig: Signal, chk: ChecksumState | None, dbc_name: str, line_num: int, address: int) -> None:
  sig.calc_checksum = None
  if sig.name == "COUNTER":
    sig.type = SignalType.COUNTER
