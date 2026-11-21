"""Capture-derived D-PDU programming primitives, with live programming disabled.

This module builds frames and checks response eligibility without opening a
socket. The observed ECU response event contains a persistent receive COP,
not the originating send COP. Consequently repeated ``74`` and ``77``
responses in a programming session cannot presently be attributed safely.
Neither a queue drain nor the start-primitive acknowledgement proves otherwise.
No live writer or offloaded TesterPresent lifecycle is provided here.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .captured_events import parse_radio_rx


class CorrelationUnproven(RuntimeError):
    """The observed protocol cannot establish which request a response belongs to."""


class ProgrammingUnavailable(RuntimeError):
    """A live programming transport has not been verified."""


def _required_positive_prefix(request: bytes) -> bytes:
    """Return the minimum positive-response echo for supported UDS services."""
    sid = request[0]
    # 34 and 37 have no request-specific echo. Other services carry the
    # subfunction, DID, routine ID, or transfer block counter in the reply.
    echo_lengths = {0x10: 2, 0x11: 2, 0x22: 3, 0x27: 2, 0x28: 2, 0x2E: 3,
                    0x31: 4, 0x34: 1, 0x36: 2, 0x37: 1, 0x85: 2}
    min_lengths = {0x10: 2, 0x11: 2, 0x22: 3, 0x27: 2, 0x28: 2, 0x2E: 4,
                   0x31: 4, 0x34: 3, 0x36: 3, 0x37: 1, 0x85: 2}
    if sid not in echo_lengths:
        raise ValueError(f"unsupported UDS service {sid:02X}")
    if len(request) < min_lengths[sid] or (sid == 0x22 and len(request) != 3):
        raise ValueError(f"invalid UDS request length for service {sid:02X}")
    return bytes([(sid + 0x40) & 0xFF]) + request[1:echo_lengths[sid]]


def _transfer_positive_is_well_formed(sid: int, uds: bytes) -> bool:
    """Apply the transfer-response shapes observed in the A11 capture."""
    if sid == 0x34:
        if len(uds) < 3 or uds[1] & 0x0F:
            return False
        width = uds[1] >> 4
        return 1 <= width <= 4 and len(uds) == width + 2 and int.from_bytes(uds[2:], "big") >= 3
    if sid == 0x36:
        return len(uds) == 2
    if sid == 0x37:
        return len(uds) == 1
    return True


def _cop_marker(handle: int) -> int:
    """u16 following copId in 0x463: ``(channel << 8) | 0x10``, channel = handle high byte.

    Capture-verified for channel 0x25 (0x2510, vehicle-tested) and channel 0x1E
    (0x1E10, mdi2_direct_client_WIP capture). Replicated from
    live_programming_transport._cop_marker; NOT a fixed 0x2510 constant.
    """
    return (((handle >> 24) & 0xFF) << 8) | 0x10


def build_one_shot(handle: int, cop_id: int, can_id: int, uds: bytes) -> bytes:
    """Build a captured-format 0x463 D-PDU frame, without sending it.

    The 4095-byte UDS request limit is the maximum in the analyzed capture;
    this does not establish a limit for other adapters or ECU responses.
    """
    for value in (handle, can_id):
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise ValueError("handle and CAN identifier must be uint32")
    if type(cop_id) is not int or not 1 <= cop_id <= 0xFFFF:
        raise ValueError("COP identifier must be a nonzero uint16")
    if type(uds) is not bytes or not 1 <= len(uds) <= 4095:
        raise ValueError("UDS request must be 1 to 4095 immutable bytes")
    data = can_id.to_bytes(4, "big") + uds
    payload = (struct.pack("<IHHHHI", handle, cop_id, _cop_marker(handle), 0x8004, 0, len(data))
               + data + b"\x01" + struct.pack("<IiiIIII", 0, 1, 0, 0, 4, 0x40010020, 0))
    return struct.pack("<II", len(payload) + 8, 0x463) + payload


class OfflineFrameDecoder:
    """Bounded incremental decoder for little-endian D-PDU TCP frames.

    Pure offline helper. Framing does not establish channel ownership, response
    freshness or ECU acknowledgement. A framing error permanently poisons it.
    """

    def __init__(self, *, max_frame: int = 65536, max_buffer: int = 131072):
        if (type(max_frame) is not int or type(max_buffer) is not int or
                max_frame < 8 or max_buffer < max_frame):
            raise ValueError("invalid decoder bounds")
        self.max_frame, self.max_buffer = max_frame, max_buffer
        self._buffer = bytearray()
        self.poisoned = False

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        if self.poisoned:
            raise CorrelationUnproven("decoder is poisoned")
        if type(data) is not bytes:
            raise ValueError("frame input must be immutable bytes")
        if len(self._buffer) + len(data) > self.max_buffer:
            self.poisoned = True
            raise ValueError("D-PDU buffered data exceeds limit")
        self._buffer.extend(data)
        out = []
        while len(self._buffer) >= 8:
            length, mid = struct.unpack_from("<II", self._buffer)
            if not 8 <= length <= self.max_frame:
                self.poisoned = True
                raise ValueError("invalid D-PDU frame length")
            if len(self._buffer) < length:
                break
            out.append((mid, bytes(self._buffer[8:length])))
            del self._buffer[:length]
        return out

    def finish(self) -> None:
        if self.poisoned:
            raise CorrelationUnproven("decoder is poisoned")
        if self._buffer:
            self.poisoned = True
            raise ValueError("truncated D-PDU frame at end of stream")


@dataclass
class OfflineTeardown:
    """Model the successful captured CLL teardown; never writes to a socket.

    A zero command status shows only that an API request was acknowledged.
    It does not prove a hardware-cyclic TesterPresent stopped or a retry is safe.
    Failure poisons the model, preventing further commands or automatic retries.
    """

    radio_handle: int
    keepalive_handle: int
    _step: int = field(default=0, init=False)
    _awaiting: bool = field(default=False, init=False)
    poisoned: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for value in (self.radio_handle, self.keepalive_handle):
            if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
                raise ValueError("CLL handles must be uint32")
        if self.radio_handle == self.keepalive_handle:
            raise ValueError("radio and keepalive CLLs must differ")

    @property
    def complete(self) -> bool:
        return self._step == 3 and not self._awaiting and not self.poisoned

    def next_frame(self) -> bytes:
        if self.poisoned or self.complete or self._awaiting:
            raise CorrelationUnproven("teardown cannot issue another request")
        steps = ((0x451, self.keepalive_handle), (0x461, self.radio_handle),
                 (0x451, self.radio_handle))
        mid, handle = steps[self._step]
        self._awaiting = True
        return struct.pack("<III", 12, mid, handle)

    def acknowledge(self, mid: int, payload: bytes) -> None:
        if self.poisoned or not self._awaiting:
            raise CorrelationUnproven("no teardown acknowledgement is pending")
        expected = ((0x452, 4), (0x462, 8), (0x452, 4))[self._step]
        if (type(mid) is not int or type(payload) is not bytes or
                mid != expected[0] or len(payload) != expected[1] or payload[:4] != bytes(4)):
            self.poisoned = True
            raise CorrelationUnproven("teardown acknowledgement rejected or malformed")
        self._step += 1
        self._awaiting = False

    def fail(self) -> None:
        """Mark timeout, disconnect or ambiguous delivery; do not retry."""
        self.poisoned = True


class OfflineSerializedSession:
    """Simulate one-in-flight UDS handling under an explicit ordering assumption.

    This offline model permits repeated 74/77 replies ONLY under the caller's
    assumption that the dedicated event stream is fresh and does not deliver
    duplicate or late responses from previous requests. The capture does not
    prove that assumption. No sockets, timers, or live writer are provided.
    """

    def __init__(self, *, assume_fresh_ordered_no_late_events: bool):
        if assume_fresh_ordered_no_late_events is not True:
            raise CorrelationUnproven("fresh, ordered event delivery is not established")
        self.pending: tuple[int, bytes] | None = None
        self.poisoned = False

    def begin(self, request: bytes, positive_prefix: bytes) -> None:
        if self.poisoned or self.pending is not None:
            raise CorrelationUnproven("session is poisoned or a request is pending")
        if type(request) is not bytes or not request or type(positive_prefix) is not bytes or not positive_prefix:
            raise ValueError("request and response prefix must be immutable nonempty bytes")
        if not positive_prefix.startswith(_required_positive_prefix(request)):
            raise ValueError("response prefix omits or mismatches the required UDS echo")
        self.pending = (request[0], positive_prefix)

    def accept(self, uds: bytes) -> str:
        if self.poisoned or self.pending is None:
            self.poisoned = True
            raise CorrelationUnproven("no response can be safely accepted")
        if type(uds) is not bytes or not uds:
            self.poisoned = True
            raise ValueError("empty or invalid UDS response")
        sid, prefix = self.pending
        if uds[:1] == b"\x7f":
            if len(uds) != 3 or uds[1] != sid:
                self.poisoned = True
                raise CorrelationUnproven("unexpected or malformed negative response")
            if uds[2] == 0x78:
                return "pending"
            # A well-formed ``7F <sid> <nrc>`` echoing the in-flight service id
            # is a correlated, terminal response (UDS: one response per request,
            # exactly like the ``78`` pending case above). It completes the
            # request negatively; the session stays usable for the next begin().
            # Observed live 2026-11-10: poisoning here forced a link re-open per
            # unsupported DID and wedged the MDI after ~48 D-PDU channels.
            self.pending = None
            return "negative"
        if not uds.startswith(prefix) or not _transfer_positive_is_well_formed(sid, uds):
            self.poisoned = True
            raise CorrelationUnproven("unexpected positive response")
        self.pending = None
        return "positive"

    def fail(self) -> None:
        """Permanently stop on timeout, disconnection, or ambiguous delivery."""
        self.poisoned = True


@dataclass
class OfflineResponseGuard:
    """Fail closed if response prefixes could be confused within a session.

    The guard is an offline diagnostic, not an event-order barrier: even the
    first response can be stale if the supplied event stream is not fresh.
    Repeated positive prefixes are rejected before constructing the next send.
    That deliberately prevents a full LTZ transfer under current evidence.
    """
    used: set[bytes] = field(default_factory=set)
    pending: tuple[int, bytes] | None = None
    poisoned: bool = False

    def begin(self, request: bytes, positive_prefix: bytes) -> None:
        if self.poisoned or self.pending is not None:
            raise CorrelationUnproven("session is poisoned or a request is pending")
        if type(request) is not bytes or not request or type(positive_prefix) is not bytes or not positive_prefix:
            raise ValueError("request and response prefix must be immutable nonempty bytes")
        required_prefix = _required_positive_prefix(request)
        if not positive_prefix.startswith(required_prefix):
            raise ValueError("response prefix omits or mismatches the required UDS echo")
        if any(positive_prefix.startswith(old) or old.startswith(positive_prefix) for old in self.used):
            self.poisoned = True
            raise CorrelationUnproven("a prior response has an indistinguishable prefix")
        self.used.add(positive_prefix)
        self.pending = (request[0], positive_prefix)

    def accept(self, uds: bytes) -> str:
        if self.poisoned or self.pending is None:
            self.poisoned = True
            raise CorrelationUnproven("no response can be safely accepted")
        if type(uds) is not bytes or not uds:
            self.poisoned = True
            raise ValueError("empty or invalid UDS response")
        sid, prefix = self.pending
        if uds[:1] == b"\x7f":
            if len(uds) != 3 or uds[1] != sid:
                self.poisoned = True
                raise CorrelationUnproven("unexpected or malformed negative response")
            if uds[2] == 0x78:
                return "pending"
            # A well-formed ``7F <sid> <nrc>`` echoing the in-flight service id
            # is a correlated, terminal response (UDS: one response per request,
            # exactly like the ``78`` pending case above). It completes the
            # request negatively; the session stays usable for the next begin().
            # Observed live 2026-11-10: poisoning here forced a link re-open per
            # unsupported DID and wedged the MDI after ~48 D-PDU channels.
            self.pending = None
            return "negative"
        if not uds.startswith(prefix) or not _transfer_positive_is_well_formed(sid, uds):
            self.poisoned = True
            raise CorrelationUnproven("unexpected positive response")
        self.pending = None
        return "positive"

    def accept_event(self, payload: bytes, *, handle: int, cop: int, can_id: int) -> str | None:
        try:
            uds = parse_radio_rx(payload, handle=handle, cop=cop, can_id=can_id)
        except ValueError:
            self.poisoned = True
            raise
        return None if uds is None else self.accept(uds)

    def fail(self) -> None:
        """Record timeout, disconnect or ambiguous delivery; never permit retry."""
        self.poisoned = True


def open_live_programming_transport(*_args: object, **_kwargs: object) -> None:
    """Explicit interlock until response attribution and CLL teardown are verified."""
    raise ProgrammingUnavailable("live D-PDU programming transport is not verified")
