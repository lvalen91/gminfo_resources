"""VIP development-memory protocol used by the isolated A11 CAN bench.

This is deliberately a narrow, fail-closed implementation of the CAN 0x613/
0x614 route documented in ``platform/can_bench_experiments.md``.  It supports
only connect, MTA selection, bounded reads, and bounded writes; it neither
discovers addresses nor provides a general RAM dumper.

The caller owns UDS programming-session setup and must always restore any
temporary words in a ``finally`` block.  The protocol is an XCP-like, classic
11-bit CAN exchange, distinct from the 29-bit ISO-TP UDS path.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol


DEV_REQUEST_ID = 0x613
DEV_RESPONSE_ID = 0x614
CONNECT = 0xFF
SET_MTA = 0xF6
UPLOAD = 0xF5
DOWNLOAD = 0xF0
POSITIVE = 0xFF
MAX_WRITE_BYTES = 6
MAX_READ_BYTES = 7


class DevMemoryError(RuntimeError):
    """The VIP development-memory endpoint rejected or did not answer a command."""


class DevCan(Protocol):
    def send(self, message: object, timeout: float | None = ...) -> object: ...
    def recv(self, timeout: float | None = ...) -> object | None: ...


@dataclass(frozen=True)
class WordPair:
    """A two-word temporary state whose original values must be restored."""

    first_address: int
    second_address: int
    first: bytes
    second: bytes


class VipDevMemory:
    """Small synchronous client for the verified 0x613/0x614 command subset."""

    def __init__(self, bus: DevCan, *, timeout: float = 0.5):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.bus = bus
        self.timeout = timeout

    @staticmethod
    def _frame(payload: bytes):
        if not 1 <= len(payload) <= 8:
            raise ValueError("development CAN payload must contain 1..8 bytes")
        try:
            import can
        except ImportError as exc:  # pragma: no cover - exercised by caller environment
            raise DevMemoryError("python-can is required for a live CAN operation") from exc
        return can.Message(arbitration_id=DEV_REQUEST_ID, is_extended_id=False,
                           data=payload)

    def _request(self, payload: bytes) -> bytes:
        self.bus.send(self._frame(payload), timeout=self.timeout)
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            message = self.bus.recv(timeout=max(0, deadline - time.monotonic()))
            if message is None:
                break
            if getattr(message, "arbitration_id", None) != DEV_RESPONSE_ID:
                continue
            if getattr(message, "is_extended_id", False):
                continue
            data = bytes(message.data)
            if not data or data[0] != POSITIVE:
                raise DevMemoryError(f"development command 0x{payload[0]:02X} failed: {data.hex()}")
            return data
        raise DevMemoryError(f"development command 0x{payload[0]:02X} timed out")

    def connect(self) -> bytes:
        """Connect to the documented callback-4 endpoint."""
        return self._request(bytes([CONNECT, 0x00]))

    def set_mta(self, address: int) -> None:
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError("address must be a u32")
        # Validated bench frame: F6, two reserved/address-extension bytes,
        # then a zero high-address byte and the 32-bit little-endian MTA.
        # Keep the full eight-byte form: the VIP callback rejects the shorter
        # generic-XCP encoding.
        self._request(bytes([SET_MTA, 0, 0, 0]) + address.to_bytes(4, "little"))

    def read(self, address: int, length: int) -> bytes:
        if not 1 <= length <= MAX_READ_BYTES:
            raise ValueError(f"read length must be 1..{MAX_READ_BYTES}")
        self.set_mta(address)
        response = self._request(bytes([UPLOAD, length]))
        data = response[1:]
        if len(data) != length:
            raise DevMemoryError(f"read 0x{address:08X}: expected {length} bytes, got {len(data)}")
        return data

    def write(self, address: int, data: bytes) -> None:
        if not 1 <= len(data) <= MAX_WRITE_BYTES:
            raise ValueError(f"write length must be 1..{MAX_WRITE_BYTES}")
        self.set_mta(address)
        self._request(bytes([DOWNLOAD, len(data)]) + data)

    def read_word_pair(self, first_address: int, second_address: int) -> WordPair:
        return WordPair(first_address, second_address, self.read(first_address, 4),
                        self.read(second_address, 4))

    def restore_word_pair(self, saved: WordPair) -> None:
        self.write(saved.first_address, saved.first)
        self.write(saved.second_address, saved.second)
        if self.read(saved.first_address, 4) != saved.first or self.read(saved.second_address, 4) != saved.second:
            raise DevMemoryError("VIP verifier-word restore readback mismatch")
