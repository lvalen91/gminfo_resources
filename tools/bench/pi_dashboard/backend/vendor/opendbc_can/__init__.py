"""Vendored subset of commaai/opendbc's `opendbc/can/` -- the pure-Python DBC parser and
CANParser only.

WHY ONLY `can/`, NOT THE WHOLE PACKAGE: the full `opendbc` package is a car-platform
fingerprinting/interface library -- it carries numpy, per-brand CAN definitions, safety
models and car state machines we have no use for on this read-only bench. We need exactly
one thing: take already-flowing CAN frames and decode named signals against a hand-written
DBC. That is `CANParser` + `DBC`, which are self-contained once the per-car checksum
imports are stripped (see dbc.py / parser.py headers). Upstream commit 66b4002, MIT (LICENSE).

Read-only: CANPacker (the send/encode side) is deliberately NOT vendored -- nothing in this
panel builds or transmits frames.
"""
from .parser import CANParser, CANDefine
from .dbc import DBC, Signal

__all__ = ["CANParser", "CANDefine", "DBC", "Signal"]
