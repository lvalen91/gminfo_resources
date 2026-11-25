"""VIP development-interface (XCP-style) memory route over SocketCAN can0.

Ported, IO-only, from boot_radio_elk.py's CanDiagnostics (raw-libusb) so it rides the
shared can0 transport like everything else. Byte sequences are unchanged and grounded in
research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md (§2026-11-16) and
boot_radio_elk.py:179-192:

    TX request id 0x613 (DLC 8), replies on 0x614. No SecurityAccess on this route.
    connect : FF 00            -> reply[0]==0xFF (e.g. FF 0C 00 08 08 00 01 01)
    status  : FD               -> FF 20 00 08 00 00 01 01
    F6 <00 00 00> <addr:4 LE>  select memory transfer address (SET_MTA)
    F5 <04>                    upload 4 bytes            -> reply[1:5]
    F0 <04> <value:4>          download 4 bytes (write)
    FE                         disconnect

This module never decides WHAT to write - callers pass addresses/values. The calibration
and ELK flows supply the documented markers. The restore step is always run in a finally.
"""
from __future__ import annotations

import contextlib
import select
import socket
import struct
import time

CAN_FRAME = struct.Struct("=IB3x8s")
DEV_TX_ID = 0x613
DEV_RX_ID = 0x614
DEFAULT_IFACE = "can0"


class VipDevError(RuntimeError):
    pass


class VipDevInterface:
    def __init__(self, iface: str = DEFAULT_IFACE, timeout: float = 3.0):
        self.iface = iface
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self.log: list[str] = []

    def _note(self, msg: str) -> None:
        self.log.append(msg)

    def open(self) -> None:
        s = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        # Only accept replies on 0x614.
        fmt = struct.Struct("=II")
        s.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, fmt.pack(DEV_RX_ID, 0x7FF))
        s.bind((self.iface,))
        self._sock = s

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    def _send(self, data: bytes) -> None:
        assert self._sock is not None
        payload = data.ljust(8, b"\0")[:8]
        try:
            self._sock.send(CAN_FRAME.pack(DEV_TX_ID, 8, payload))
        except OSError as e:
            # ENOBUFS = the TX queue filled because nothing on the bus ACKs our frame
            # (the radio/VIP is absent, asleep, or power-cycling).
            import errno as _errno
            if e.errno == _errno.ENOBUFS:
                raise VipDevError("can0 TX queue full - no CAN ACK on the bus "
                                  "(VIP/radio absent or asleep)") from e
            raise VipDevError(f"can0 send failed: {e}") from e

    def _recv(self) -> bytes:
        assert self._sock is not None
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise VipDevError(f"no reply on 0x{DEV_RX_ID:03X} within {self.timeout}s "
                                  "(VIP dev interface silent - bus/VIP asleep?)")
            r, _, _ = select.select([self._sock], [], [], remaining)
            if not r:
                continue
            raw = self._sock.recv(16)
            if len(raw) < 16:
                continue
            ident, dlc, data = CAN_FRAME.unpack(raw)
            if (ident & 0x7FF) == DEV_RX_ID:
                return data[:dlc]

    def xcp(self, payload: bytes) -> bytes:
        self._send(payload)
        reply = self._recv()
        if not reply or reply[0] != 0xFF:
            raise VipDevError(f"VIP dev interface rejected {payload.hex()} -> {reply.hex()}")
        return reply

    def connect(self) -> bytes:
        reply = self.xcp(bytes.fromhex("ff00"))
        self._note(f"613/614 connected (reply {reply.hex()})")
        return reply

    def status(self) -> bytes:
        return self.xcp(bytes.fromhex("fd"))

    def disconnect(self) -> None:
        with contextlib.suppress(VipDevError, OSError):
            self._send(bytes.fromhex("fe"))
            self._note("613/614 disconnected")

    def _select(self, addr: int) -> None:
        self.xcp(bytes.fromhex("f6000000") + struct.pack("<I", addr))

    def read_word(self, addr: int) -> bytes:
        self._select(addr)
        reply = self.xcp(bytes.fromhex("f504"))
        if len(reply) < 5:
            raise VipDevError("short XCP memory read")
        return reply[1:5]

    def write_word(self, addr: int, value: bytes) -> None:
        if len(value) != 4:
            raise VipDevError("word value must be 4 bytes")
        self._select(addr)
        self.xcp(bytes.fromhex("f004") + value)

    def write_verify(self, addr: int, value: bytes) -> None:
        self.write_word(addr, value)
        back = self.read_word(addr)
        if back != value:
            raise VipDevError(f"readback mismatch at {addr:08X}: wrote {value.hex()}, read {back.hex()}")
        self._note(f"wrote+verified {addr:08X}={value.hex()}")


# --- Calibration verifier words (DPS_TYPE4 §2026-11-16) --------------------------
VERIFIER_WORDS = (0xFEBF0BF8, 0xFEBF0BFC)
# Validated-SBA-ticket marker pair written in their place (temporary RAM condition).
MARKER_VALUES = {0xFEBF0BF8: bytes.fromhex("A5163829"), 0xFEBF0BFC: bytes.fromhex("5AE9C7D6")}


def connect_and_save(dev: VipDevInterface) -> dict:
    """Non-destructive: connect, read + report the two verifier words. The TEST/dry-run
    path for a calibration write - validates the 613/614 link without overriding anything."""
    dev.connect()
    saved = {}
    for addr in VERIFIER_WORDS:
        w = dev.read_word(addr)
        saved[addr] = w
        dev._note(f"verifier word {addr:08X} = {w.hex()} (saved)")
    return saved
