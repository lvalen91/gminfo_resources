"""Read one MDI2 battery-voltage sample on an established D-PDU command socket.

The caller owns PDU startup, command-channel hello and request serialization.
An IOCTL response does not identify its originating IOCTL: a queued response
to another command can have the same frame layout. Fresh-channel provenance
and absence of late/queued responses must be established before use as a gate;
that property is not verified here. No socket is opened here and this module
does not issue programming commands.
"""
from __future__ import annotations

import math
import struct
import time
from typing import Protocol


class CommandSocket(Protocol):
    def settimeout(self, value: float) -> None: ...
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


def read_battery_mv(command: CommandSocket, *, timeout: float = 4.0) -> int:
    """Issue one captured-format battery-voltage IOCTL and return millivolts.

    A partial/failed exchange closes the socket: its framing cannot safely be
    reused. This function does not start cyclic voltage monitoring.
    """
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    payload = bytes.fromhex("ffffffff0600000000")
    frame = struct.pack("<II", len(payload) + 8, 0x467) + payload
    deadline = time.monotonic() + timeout

    def read_exact(size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("battery-voltage response timed out")
            command.settimeout(remaining)
            data = command.recv(size - len(result))
            if not data:
                raise ConnectionError("battery-voltage response closed mid-frame")
            result.extend(data)
        return bytes(result)

    try:
        command.settimeout(timeout)
        command.sendall(frame)
        length, mid = struct.unpack("<II", read_exact(8))
        if length != 34 or mid != 0x468:
            raise ValueError("unexpected battery-voltage response frame")
        response = read_exact(26)
        if response[:4] != bytes(4):
            raise ValueError("battery-voltage IOCTL returned status " + response[:4].hex())
        return struct.unpack_from("<I", response, 22)[0]
    except Exception:
        try:
            command.close()
        except OSError:
            pass
        raise
