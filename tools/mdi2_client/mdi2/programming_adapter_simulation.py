"""Experimental injected-socket D-PDU programming adapter for simulation only.

This is not a live writer. No sockets are opened, OS sockets are rejected, and
the public live-opener interlock remains in place. Callers must explicitly
assume fresh ordered response delivery without late/duplicate events: captured
radio receive events do not identify the originating transmit primitive.
Tests with fake sockets cannot establish that assumption for actual hardware.
"""
from __future__ import annotations

import math
import socket
import struct
import time
from typing import Protocol

from .captured_events import parse_radio_rx
from .programming_transport import (
    CorrelationUnproven,
    OfflineSerializedSession,
    OfflineTeardown,
    _required_positive_prefix,
    build_one_shot,
)


class SocketLike(Protocol):
    def settimeout(self, value: float) -> None: ...
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


class AdapterError(RuntimeError):
    """Adapter stopped; delivery or hardware cleanup may be ambiguous."""


def _frame(mid: int, payload: bytes) -> bytes:
    return struct.pack("<II", 8 + len(payload), mid) + payload


def _cop_marker(handle: int) -> int:
    """u16 after copId in 0x463: ``(channel << 8) | 0x10``, channel = handle high byte.

    Replicated from live_programming_transport._cop_marker; 0x2510 only for the
    vehicle-tested channel 0x25. Not a fixed constant.
    """
    return (((handle >> 24) & 0xFF) << 8) | 0x10


def _periodic(handle: int, cop: int, can_id: int) -> bytes:
    data = can_id.to_bytes(4, "big") + b"\x3e\x80"
    payload = (struct.pack("<IHHHHI", handle, cop, _cop_marker(handle), 0x8004, 0, len(data))
               + data + b"\x01" + struct.pack("<IiiIIII", 1000, -1, 0, 0, 4, 0x40010020, 0))
    return _frame(0x463, payload)


class SimulatedProgrammingAdapter:
    """One-in-flight fake-socket adapter. Never use against a real MDI2.

    The owner supplies independently configured, dedicated fake command/event
    streams, CLL handles, persistent receive COP and an unused COP range. Raw
    socket.socket instances are rejected, but this is not a security boundary
    against arbitrary proxy objects. Production integration remains blocked.
    """

    def __init__(self, command: SocketLike, events: SocketLike, *,
                 radio_handle: int, keepalive_handle: int, receive_cop: int,
                 first_free_cop: int, reserved_cops: frozenset[int],
                 request_can_id: int, response_can_id: int, functional_can_id: int,
                 assume_fresh_ordered_no_late_events: bool,
                 simulation_only: bool, timeout: float = 4.0,
                 max_frame: int = 65536):
        if simulation_only is not True or isinstance(command, socket.socket) or isinstance(events, socket.socket):
            raise ValueError("adapter accepts fake sockets for simulation only")
        if command is events:
            raise ValueError("command and event sockets must differ")
        for val in (radio_handle, keepalive_handle, request_can_id, response_can_id, functional_can_id):
            if type(val) is not int or not 0 <= val <= 0xFFFFFFFF:
                raise ValueError("handle and CAN identifiers must be uint32")
        if radio_handle == keepalive_handle:
            raise ValueError("radio and keepalive CLLs must differ")
        if (type(receive_cop) is not int or not 1 <= receive_cop <= 0xFFFF or
                type(first_free_cop) is not int or not 1 <= first_free_cop <= 0xFFFF or
                type(reserved_cops) is not frozenset or receive_cop not in reserved_cops or
                any(type(cop) is not int or not 1 <= cop <= 0xFFFF for cop in reserved_cops)):
            raise ValueError("valid receive and reserved COP identifiers are required")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if type(max_frame) is not int or not 90 <= max_frame <= 1048576:
            raise ValueError("invalid maximum D-PDU frame length")
        self._guard = OfflineSerializedSession(
            assume_fresh_ordered_no_late_events=assume_fresh_ordered_no_late_events)
        self.command, self.events = command, events
        self.radio_handle, self.keepalive_handle = radio_handle, keepalive_handle
        self.receive_cop, self.next_cop = receive_cop, first_free_cop
        self.reserved_cops = set(reserved_cops)
        self.request_can_id, self.response_can_id, self.functional_can_id = (
            request_can_id, response_can_id, functional_can_id)
        self.timeout, self.max_frame = float(timeout), max_frame
        self.keepalive_cop: int | None = None
        self.started = False
        self.closed = False
        self.poisoned = False

    def _close_sockets(self) -> None:
        for stream in (self.command, self.events):
            try:
                stream.close()
            except OSError:
                pass
        self.closed = True

    def _fail(self, reason: str) -> None:
        self.poisoned = True
        self._guard.fail()
        self._close_sockets()
        raise AdapterError(reason + "; outcome or tester-present teardown may be ambiguous")

    def _allocate_cop(self) -> int:
        while self.next_cop <= 0xFFFF and self.next_cop in self.reserved_cops:
            self.next_cop += 1
        if self.next_cop > 0xFFFF:
            self._fail("COP identifier space exhausted")
        result = self.next_cop
        self.reserved_cops.add(result)
        self.next_cop += 1
        return result

    def _exact(self, stream: SocketLike, size: int, deadline: float) -> bytes:
        out = bytearray()
        while len(out) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("D-PDU frame timeout")
            stream.settimeout(remaining)
            chunk = stream.recv(size - len(out))
            if not chunk:
                raise ConnectionError("D-PDU stream closed")
            out.extend(chunk)
        return bytes(out)

    def _read_frame(self, stream: SocketLike, deadline: float) -> tuple[int, bytes]:
        length, mid = struct.unpack("<II", self._exact(stream, 8, deadline))
        if not 8 <= length <= self.max_frame:
            raise ValueError("invalid D-PDU frame length")
        return mid, self._exact(stream, length - 8, deadline)

    def _command(self, frame: bytes, expected_mid: int, expected_length: int) -> None:
        if self.closed or self.poisoned:
            raise AdapterError("adapter is closed or poisoned")
        deadline = time.monotonic() + self.timeout
        try:
            self.command.settimeout(self.timeout)
            self.command.sendall(frame)
            mid, payload = self._read_frame(self.command, deadline)
            if mid != expected_mid or len(payload) != expected_length or payload[:4] != bytes(4):
                raise ValueError("D-PDU command acknowledgement rejected or malformed")
        except (OSError, ValueError, struct.error):
            self._fail("D-PDU command failed")

    def start_keepalive(self) -> None:
        if self.closed or self.poisoned or self.started or self._guard.pending is not None:
            raise AdapterError("invalid keepalive state")
        self.keepalive_cop = self._allocate_cop()
        self._command(_periodic(self.keepalive_handle, self.keepalive_cop,
                                self.functional_can_id), 0x464, 4)
        # This acknowledges the command only; actual periodic operation is unverified.
        self.started = True

    def send(self, request: bytes) -> None:
        if self.closed or self.poisoned or not self.started:
            raise AdapterError("adapter is closed, poisoned, or keepalive is not started")
        try:
            if type(request) is not bytes or not request:
                raise ValueError("UDS request must be nonempty bytes")
            prefix = _required_positive_prefix(request)
            self._guard.begin(request, prefix)
            cop = self._allocate_cop()
            self._command(build_one_shot(self.radio_handle, cop, self.request_can_id, request), 0x464, 4)
        except (ValueError, CorrelationUnproven):
            self._fail("request cannot be safely sent")

    def receive(self, timeout: float) -> bytes | None:
        if self.closed or self.poisoned or self._guard.pending is None:
            raise AdapterError("adapter is closed, poisoned, or no request is pending")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            self._fail("invalid response timeout")
        deadline = time.monotonic() + timeout
        try:
            while True:
                mid, payload = self._read_frame(self.events, deadline)
                if mid == 1505:
                    continue
                if mid != 0x863:
                    raise ValueError("unexpected D-PDU event type")
                uds = parse_radio_rx(payload, handle=self.radio_handle,
                                     cop=self.receive_cop, can_id=self.response_can_id)
                if uds is None:
                    # Unclassified status/TX events can conceal a lost periodic COP.
                    raise ValueError("unclassified D-PDU event")
                result = self._guard.accept(uds)
                # "negative" is a correlated terminal NRC: hand the 7F bytes to
                # UdsClient (which raises TransactionError) without poisoning.
                # Omitting it here would loop for another frame with the guard's
                # pending already cleared and poison on the next event.
                if result in ("positive", "pending", "negative"):
                    return uds
        except CorrelationUnproven as exc:
            # OfflineSerializedSession emits only fixed text (no payload bytes).
            self._fail(str(exc))
        except (OSError, ValueError, struct.error):
            self._fail("D-PDU response failed")

    def close(self) -> None:
        if self.closed:
            return
        if self.poisoned or self._guard.pending is not None or not self.started:
            self._fail("teardown cannot be confirmed")
        teardown = OfflineTeardown(self.radio_handle, self.keepalive_handle)
        try:
            for mid, length in ((0x452, 4), (0x462, 8), (0x452, 4)):
                frame = teardown.next_frame()
                self._command(frame, mid, length)
                teardown.acknowledge(mid, bytes(length))
        except (AdapterError, CorrelationUnproven):
            self._fail("D-PDU CLL teardown failed")
        self._close_sockets()
        # ACKs do not prove that device-offloaded TesterPresent traffic stopped.
