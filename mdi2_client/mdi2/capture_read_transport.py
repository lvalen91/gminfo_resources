"""Fail-closed, read-only D-PDU transport for an already configured radio link.

No connection, PDU startup or link configuration is performed here.  The
observed ECU receive events use a persistent receive primitive and do not
identify the initiating send primitive. In particular, repeated ``74`` and
``77`` replies cannot be correlated conclusively. This adapter therefore
rejects all programming, reset and security requests; it is not a flash tool.
Even a first read can consume a matching event already queued before the send;
fresh-session ownership and event ordering are unverified. Do not use this
adapter for a live baseline until those properties are established. Closing
sockets is not known to cancel an offloaded continuous TesterPresent primitive.
"""
from __future__ import annotations

import math
import socket
import struct
import time
from typing import Protocol

from .captured_events import parse_radio_rx


class SocketLike(Protocol):
    def settimeout(self, value: float) -> None: ...
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


class TransportError(RuntimeError):
    pass


def _frame(mid: int, payload: bytes) -> bytes:
    return struct.pack("<II", len(payload) + 8, mid) + payload


def _cop_marker(handle: int) -> int:
    """u16 after copId in 0x463: ``(channel << 8) | 0x10``, channel = handle high byte.

    Replicated from live_programming_transport._cop_marker; 0x2510 only for the
    vehicle-tested channel 0x25. Not a fixed constant.
    """
    return (((handle >> 24) & 0xFF) << 8) | 0x10


def _cop(handle: int, cop_id: int, data: bytes, *, period_ms: int = 0,
         continuous: bool = False) -> bytes:
    """Construct the observed send primitive, not a captured request replay."""
    return (struct.pack("<IHHHHI", handle, cop_id, _cop_marker(handle), 0x8004, 0, len(data))
            + data + b"\x01" + struct.pack("<IiiIIII", period_ms,
                    -1 if continuous else 1, 0, 0, 4, 0x40010020, 0))


class CaptureReadTransport:
    """UDS read adapter with bounded frames; all ambiguous sessions are poisoned.

    ``command`` and ``events`` must be dedicated, already connected sockets.
    Handles/COP must come from a verified link setup, and radio addresses from
    the caller. Keepalive uses a separate already-configured CLL. No original
    SecurityAccess key, VIN, captured frame or network address is embedded.
    The single-threaded caller must serialize all calls. The caller must verify
    fresh CLL provenance, event ordering and COP/CLL cleanup; none is proven by
    this adapter, and an ordinary queue drain is not a correlation guarantee.
    """

    def __init__(self, command: SocketLike, events: SocketLike, *, radio_handle: int,
                 receive_cop: int, first_free_cop: int, request_can_id: int, response_can_id: int,
                 keepalive_handle: int, functional_can_id: int,
                 timeout: float = 4.0, max_frame: int = 65536):
        if (type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0 or
                type(max_frame) is not int or not 90 <= max_frame <= 1048576):
            raise ValueError("invalid transport bounds")
        for value in (radio_handle, request_can_id, response_can_id,
                      keepalive_handle, functional_can_id):
            if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
                raise ValueError("invalid handle or CAN identifier")
        if type(receive_cop) is not int or not 0 <= receive_cop <= 0xFFFF:
            raise ValueError("invalid receive COP")
        if (type(first_free_cop) is not int or not 1 <= first_free_cop <= 0xFFFF or
                first_free_cop <= receive_cop):
            raise ValueError("an unused first COP identifier is required")
        if radio_handle == keepalive_handle:
            raise ValueError("keepalive must use a separate CLL")
        self.command, self.events = command, events
        self.radio_handle, self.receive_cop = radio_handle, receive_cop
        self.request_can_id, self.response_can_id = request_can_id, response_can_id
        self.keepalive_handle, self.functional_can_id = keepalive_handle, functional_can_id
        self.timeout, self.max_frame = float(timeout), max_frame
        self.closed = False
        self.keepalive_started = False
        self.keepalive_cop: int | None = None
        self.pending_did: bytes | None = None
        self.used_dids: set[bytes] = set()
        # The verified setup owner must supply a collision-free range.
        self.next_cop = first_free_cop

    def _fail(self, reason: str) -> None:
        self.close()
        raise TransportError(reason)

    def close(self) -> None:
        """Close sockets only; primitive/CLL cleanup remains unverified."""
        if self.closed:
            return
        self.closed = True
        for sock in (self.command, self.events):
            try:
                sock.close()
            except OSError:
                pass

    def _allocate_cop(self) -> int:
        if self.next_cop > 0xFFFF:
            self._fail("COP identifier space exhausted")
        cop = self.next_cop
        self.next_cop += 1
        return cop

    def _read_exact(self, sock: SocketLike, size: int, deadline: float) -> bytes:
        out = bytearray()
        while len(out) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("D-PDU frame timeout")
            sock.settimeout(remaining)
            part = sock.recv(size - len(out))
            if not part:
                raise ConnectionError("D-PDU stream closed")
            out.extend(part)
        return bytes(out)

    def _receive_frame(self, sock: SocketLike, deadline: float) -> tuple[int, bytes]:
        header = self._read_exact(sock, 8, deadline)
        length, mid = struct.unpack("<II", header)
        if not 8 <= length <= self.max_frame:
            raise ValueError("invalid D-PDU frame length")
        return mid, self._read_exact(sock, length - 8, deadline)

    def _start_primitive(self, payload: bytes) -> None:
        if self.closed:
            raise TransportError("transport is closed")
        deadline = time.monotonic() + self.timeout
        try:
            self.command.settimeout(self.timeout)
            self.command.sendall(_frame(0x463, payload))
            mid, result = self._receive_frame(self.command, deadline)
            if mid != 0x464 or len(result) < 4 or result[:4] != bytes(4):
                raise ValueError("PDUStartComPrimitive rejected or malformed")
        except (OSError, TimeoutError, ValueError):
            self._fail("D-PDU command failed; delivery is ambiguous")

    def start_keepalive(self) -> None:
        if self.keepalive_started or self.pending_did is not None:
            raise TransportError("invalid keepalive state")
        cop = self._allocate_cop()
        # Record before sending: a failed send can still start the primitive.
        self.keepalive_cop = cop
        data = self.functional_can_id.to_bytes(4, "big") + b"\x3e\x80"
        self._start_primitive(_cop(self.keepalive_handle, cop, data,
                                   period_ms=1000, continuous=True))
        self.keepalive_started = True

    def send(self, request: bytes) -> None:
        if self.closed:
            raise TransportError("transport is closed")
        if not self.keepalive_started or self.pending_did is not None:
            raise TransportError("keepalive or request state invalid")
        if len(request) != 3 or request[0] != 0x22:
            raise ValueError("read-only adapter permits only a single-DID 22 request")
        did = request[1:]
        if did in self.used_dids:
            raise ValueError("repeating a DID in the same session is prohibited")
        self.used_dids.add(did)
        self.pending_did = did
        cop = self._allocate_cop()
        data = self.request_can_id.to_bytes(4, "big") + request
        self._start_primitive(_cop(self.radio_handle, cop, data))

    def receive(self, timeout: float) -> bytes | None:
        if self.closed or self.pending_did is None:
            raise TransportError("transport is closed or no read is pending")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("receive timeout must be finite and positive")
        deadline = time.monotonic() + timeout
        try:
            while True:
                mid, payload = self._receive_frame(self.events, deadline)
                if mid == 1505:
                    continue
                if mid != 0x863:
                    raise ValueError("unexpected event frame")
                uds = parse_radio_rx(payload, handle=self.radio_handle,
                                     cop=self.receive_cop, can_id=self.response_can_id)
                if uds is None:
                    continue
                if uds == b"\x7f\x22\x78":
                    return uds
                if uds.startswith(b"\x62" + self.pending_did):
                    self.pending_did = None
                    return uds
                if len(uds) == 3 and uds[:2] == b"\x7f\x22":
                    self._fail(f"radio read NRC {uds[2]:02X}; session cannot be reused")
                raise ValueError("uncorrelated radio response")
        except (OSError, TimeoutError, ValueError):
            self._fail("D-PDU event failed or timed out; session cannot be reused")
