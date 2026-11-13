"""Live D-PDU programming transport for the Bosch GM MDI2 (TCP/10123).

This module wires a real resource-0x2A ISO-TP link to a UDS client so the
``calibration_transaction.program`` state machine can run against hardware. It
is the live counterpart of ``programming_adapter_simulation.SimulatedProgrammingAdapter``
and reuses the same correlation reasoning; the ONLY differences from the
simulated adapter are that this one (a) accepts real sockets, (b) performs the
real two-socket bring-up / CLL teardown, and (c) in ``receive`` SKIPS events
that ``captured_events.parse_radio_rx`` classifies as *not ours* (TX
confirmations, keepalive confirmations, D-PDU event type 2) instead of treating
them as fatal, exactly as ``capture_read_transport.CaptureReadTransport`` does.

RESPONSE CORRELATION — why strict serialization is sound (the documented blocker).
The ECU's reassembled UDS response is reported by the MDI against the *persistent
receive COP*, never the COP of the request that triggered it (see
``MDI2_DPDU_API_PROTOCOL_AUG2026.md`` §3-§4: ``0x863`` RX "reported against the
persistent RX cop id, not the id of the request that triggered it"). Therefore a
response cannot be attributed to a request by COP. DPS itself has no other
information and still flashes reliably, because the attribution rule is strict
serialization, not COP matching:

  * exactly one UDS request is ever in flight (``UdsClient.request`` sends, then
    blocks for that request's response before the next send);
  * ``parse_radio_rx`` is a strict allow-filter keyed on
    (radio handle, event type 1, persistent receive COP, response CAN id) with
    internal length/CAN-id consistency checks, so the single value it returns is
    necessarily a well-formed radio RX-data frame on our persistent COP;
  * the MDI performs ISO-TP reassembly and emits one ``0x863`` per complete ECU
    response; UDS is one-response-per-request (``7F..78`` pending excepted, which
    is the same request); TCP is reliable and in-order; and a
    ``PDUIoCtl(0,0x0B)`` RX-buffer clear precedes CLL creation. So no stale or
    duplicate response for a *prior* request can exist when the next one is sent;
  * on ANY timeout, malformed look-alike, or socket error the session is
    poisoned and no further request is sent. Because we never advance past an
    unanswered request, a late response can never be misattributed to a later
    same-prefix request (e.g. the repeated ``74``/``77`` of the 14 download
    cycles). This is the "strictly serialized one-request-at-a-time discipline"
    the correlation note requires, and it is what DPS does.

The residual that offline evidence cannot rule out — that the MDI/ECU might
spontaneously re-emit a stale response absent any protocol/firmware bug — is the
same residual DPS operates under and is excluded by UDS/ISO-TP/TCP semantics.

LIVE FRAGILITY (observed 2026-11-07, this bench). A single malformed D-PDU frame
causes the MDI2 to close the 10123 tunnel, and it does not self-rearm (recovery
= PDU START re-arm or USB power cycle). A read desync is harmless; a desync
during ``$36`` TransferData would strand the ECU in a programming session with a
partial calibration and the tunnel down. The live opener is therefore gated and
the owner-required hard-reset / readback / voltage preflight is mandatory.
"""
from __future__ import annotations

import logging
import math
import socket
import struct
import time
from typing import Protocol

from .captured_events import parse_radio_rx
from .programming_transport import (
    CorrelationUnproven,
    OfflineSerializedSession,
    ProgrammingUnavailable,
    _required_positive_prefix,
    build_one_shot,
)

log = logging.getLogger(__name__)

# D-PDU mids (little-endian TCP framing <u32 total_len><u32 mid><payload>).
_MID_HELLO = 0x884
_MID_IOCTL = 0x467
_MID_CREATE_CLL = 0x44F
_MID_DESTROY_CLL = 0x451
_MID_GET_PARAM = 0x457
_MID_SET_PARAM = 0x459
_MID_SET_RESPID = 0x45D
_MID_CONNECT = 0x45F
_MID_DISCONNECT = 0x461
_MID_START_PRIM = 0x463
_MID_EVENT = 0x863
_MID_LEN_IND = 1505

# ComPrimitive types.
_CT_SENDRECV = 0x8004
_CT_STARTCOMM = 0x8001
_CT_UPDATEPARAM = 0x8003

# Capture-pinned StartComPrimitive trailers (SPS_radioCal..._UpdateCHeck.pcapng
# stream 317: persistent RX cop = frame 11, STARTCOMM/UPDATEPARAM = frame 12).
_RX_TRAILER = bytes.fromhex(
    "010000000000000000ffffffff0000000004000000a00100000100000000000000342500000000000000000000")
_COMM_TRAILER = bytes.fromhex(
    "0100000000000000000000000000000000040000000000000000000000")
_UPDATE_TRAILER = bytes.fromhex("01000000000000000000000000000000000000000000000000")
# CreateComLogicalLink payload body AFTER the 4-byte client handle, resource 0x2A.
_CREATE_2A_BODY = bytes.fromhex(
    "01050000002a0000000200000006000000010000000e00000002000000feffffff0104000000a0010000")

# ComParam values for a resource-0x2A ISO-TP/UDS link (DPDU doc §4-B).
_RADIO_COMPARAMS = ((0x15, 0), (0x16, 0), (0x19, 0x22), (0x1B, 0), (0xAB, 1), (0xC6, 1))


class LiveDpduError(RuntimeError):
    """The live D-PDU link stopped; ECU/tunnel outcome may be ambiguous."""


def _frame(mid: int, payload: bytes) -> bytes:
    return struct.pack("<II", 8 + len(payload), mid) + payload


def _cop_marker(handle: int) -> int:
    """u16 following copId in 0x463: ``(channel << 8) | 0x10``, channel = handle high byte.

    Capture-verified for channel 0x25 (0x2510, vehicle-tested stream 317) and
    channel 0x1E (0x1E10, mdi2_direct_client_WIP capture). Not a fixed constant.

    Live 2026-11-10: the derivation generalized beyond 0x25 during the live LTZ
    calibration write — channels in 0x02-0x30 were observed on the session and all
    reads/writes on those channels succeeded, consistent with the formula above.
    """
    return (((handle >> 24) & 0xFF) << 8) | 0x10


def _start_prim(handle: int, cop: int, ctype: int, data: bytes, trailer: bytes) -> bytes:
    return (struct.pack("<IHHHHI", handle, cop, _cop_marker(handle), ctype, 0, len(data))
            + data + trailer)


def _periodic(handle: int, cop: int, can_id: int, uds: bytes, period_ms: int) -> bytes:
    data = can_id.to_bytes(4, "big") + uds
    return (struct.pack("<IHHHHI", handle, cop, _cop_marker(handle), _CT_SENDRECV, 0, len(data))
            + data + b"\x01" + struct.pack("<IiiIIII", period_ms, -1, 0, 0, 4, 0x40010020, 0))


def _setcomparam(handle: int, param_id: int, value: int) -> bytes:
    # 34-byte SetComParam payload, capture-pinned layout (stream 317 frames 6-11).
    return (struct.pack("<I", handle) + bytes.fromhex("0501000000120000")
            + bytes.fromhex("0100120000") + struct.pack("<I", param_id)
            + bytes.fromhex("0501000003000000") + b"\x01" + struct.pack("<I", value))


def _respid_clear(handle: int) -> bytes:
    return struct.pack("<I", handle) + bytes.fromhex("0017000000170000") + struct.pack("<I", 0)


def _respid_install(handle: int, request_can_id: int, response_can_id: int) -> bytes:
    """174-byte PDUSetUniqueRespIdTable (verified byte-exact vs the ECU-0x45 capture)."""
    def entry(param_id: int, value: int) -> bytes:
        return (bytes.fromhex("0501000000120000") + struct.pack("<I", param_id)
                + bytes.fromhex("0501000006000000") + b"\x01" + struct.pack("<I", value))
    return (struct.pack("<I", handle) + bytes.fromhex("0017000000170000")
            + struct.pack("<III", 1, 0, 6)
            + entry(0x22, response_can_id) + entry(0x21, 0x37) + entry(0x20, 0)
            + entry(0x1F, request_can_id) + entry(0x1E, 0x37) + entry(0x1D, 0))


class SocketLike(Protocol):
    def settimeout(self, value: float) -> None: ...
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


class LiveDpduSession:
    """Owns the command + event sockets, channel id, CLL index and COP counters.

    ``command`` and ``events`` are two already-connected, dedicated TCP sockets
    to the MDI2 D-PDU port (10123). The caller establishes the channel via
    ``hello``. CLL handles are client-assigned and deterministic:
    ``handle = (channel << 24) | index`` (DPDU doc §3 CORRECTION 2026-08-27).
    All methods are single-threaded; the caller must serialize use.
    """

    def __init__(self, command: SocketLike, events: SocketLike, *,
                 timeout: float = 6.0, max_frame: int = 262144):
        if command is events:
            raise ValueError("command and event sockets must differ")
        if (type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0 or
                type(max_frame) is not int or not 90 <= max_frame <= 1048576):
            raise ValueError("invalid session bounds")
        self.command, self.events = command, events
        self.timeout, self.max_frame = float(timeout), max_frame
        self.channel: int | None = None
        self._next_index = 2      # indices 0/1 reserved as in the capture
        self._next_cop = 1
        self._live_handles: list[int] = []  # CLLs to destroy on close (avoid RSC leaks)
        self.poisoned = False
        self.closed = False

    # -- framing -----------------------------------------------------------
    def _recv_exact(self, sock: SocketLike, size: int, deadline: float) -> bytes:
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

    def _recv_frame(self, sock: SocketLike, deadline: float) -> tuple[int, bytes]:
        length, mid = struct.unpack("<II", self._recv_exact(sock, 8, deadline))
        if not 8 <= length <= self.max_frame:
            raise ValueError("invalid D-PDU frame length")
        return mid, self._recv_exact(sock, length - 8, deadline)

    def fail(self, reason: str) -> None:
        self.poisoned = True
        self.close()
        raise LiveDpduError(reason)

    def close(self) -> None:
        if self.closed:
            return
        # Attempt CLL teardown even after a rejected send, while the command
        # socket may still be usable. A transport failure can prevent teardown;
        # closing the sockets alone is not proof the device released its CLLs.
        for handle in reversed(self._live_handles):
            try:
                self.command.settimeout(self.timeout)
                self.command.sendall(_frame(_MID_DISCONNECT, struct.pack("<I", handle)))
                self._recv_frame(self.command, time.monotonic() + self.timeout)
                self.command.sendall(_frame(_MID_DESTROY_CLL, struct.pack("<I", handle)))
                self._recv_frame(self.command, time.monotonic() + self.timeout)
            except (OSError, TimeoutError, ValueError, struct.error):
                break
        self._live_handles.clear()
        self.closed = True
        for sock in (self.command, self.events):
            try:
                sock.close()
            except OSError:
                pass

    # -- channel / CLL / COP allocation ------------------------------------
    def hello(self) -> int:
        if self.channel is not None:
            raise LiveDpduError("channel already established")
        deadline = time.monotonic() + self.timeout
        try:
            self.command.sendall(_frame(_MID_HELLO, struct.pack("<III", 1, 0, 0x1388)))
            mid, payload = self._recv_frame(self.command, deadline)
            if mid != _MID_HELLO + 1 or len(payload) < 16:
                raise ValueError("unexpected session hello reply")
            channel = struct.unpack_from("<I", payload, 12)[0]
            if not 0 < channel <= 0xFF:
                raise ValueError("implausible channel id")
            # Bind the event socket to the same logical channel.
            self.events.sendall(_frame(_MID_HELLO, struct.pack("<III", 1, channel, 0x1388)))
            self._recv_frame(self.events, deadline)
        except (OSError, TimeoutError, ValueError, struct.error) as exc:
            self.fail(f"session hello failed ({type(exc).__name__})")
        self.channel = channel
        if channel != 0x25:
            log.warning("D-PDU channel 0x%02x differs from the vehicle-tested 0x25; "
                        "0x463 marker will be 0x%04x (formula live-verified for channels "
                        "0x02-0x30 as of 2026-11-10; outside that range, treat as unverified)",
                        channel, (channel << 8) | 0x10)
        return channel

    def _command(self, mid: int, payload: bytes, expect_mid: int,
                 min_len: int = 4) -> bytes:
        if self.closed or self.poisoned:
            raise LiveDpduError("session is closed or poisoned")
        deadline = time.monotonic() + self.timeout
        try:
            self.command.sendall(_frame(mid, payload))
            rmid, rpay = self._recv_frame(self.command, deadline)
            if rmid != expect_mid or len(rpay) < min_len or rpay[:4] != bytes(4):
                raise ValueError(f"D-PDU command 0x{mid:x} rejected (reply 0x{rmid:x})")
            return rpay
        except (OSError, TimeoutError, ValueError, struct.error):
            self.fail(f"D-PDU command 0x{mid:x} failed; delivery ambiguous")

    def _allocate_cop(self) -> int:
        if self._next_cop > 0xFFFF:
            self.fail("COP identifier space exhausted")
        cop = self._next_cop
        self._next_cop += 1
        return cop

    def _allocate_handle(self) -> int:
        if self.channel is None:
            raise LiveDpduError("channel not established")
        if self._next_index > 0xFF:
            self.fail("CLL index space exhausted")
        handle = (self.channel << 24) | self._next_index
        self._next_index += 1
        return handle

    def clear_rx_buffer(self) -> None:
        self._command(_MID_IOCTL, bytes.fromhex("000000000b00000000"), _MID_IOCTL + 1)

    def _create_cll(self) -> int:
        handle = self._allocate_handle()
        self._command(_MID_CREATE_CLL, struct.pack("<I", handle) + _CREATE_2A_BODY,
                      _MID_CREATE_CLL + 1)
        self._live_handles.append(handle)
        return handle

    def _bring_link_up(self, handle: int) -> None:
        for param_id in (0x09, 0x0C, 0xAE, 0xB8):
            self._command(_MID_GET_PARAM, struct.pack("<II", handle, param_id), _MID_GET_PARAM + 1)
        self._command(_MID_SET_RESPID, _respid_clear(handle), _MID_SET_RESPID + 1)
        for param_id, value in _RADIO_COMPARAMS:
            self._command(_MID_SET_PARAM, _setcomparam(handle, param_id, value), _MID_SET_PARAM + 1)
        self._command(_MID_CONNECT, struct.pack("<I", handle), _MID_CONNECT + 1)

    def create_radio_cll(self, request_can_id: int, response_can_id: int) -> tuple[int, int]:
        """Full radio bring-up. Returns (handle, persistent_receive_cop)."""
        handle = self._create_cll()
        self._bring_link_up(handle)
        rx_cop = self._allocate_cop()
        self._command(_MID_START_PRIM, _start_prim(handle, rx_cop, _CT_SENDRECV, b"", _RX_TRAILER),
                      _MID_START_PRIM + 1)
        self._command(_MID_START_PRIM,
                      _start_prim(handle, self._allocate_cop(), _CT_STARTCOMM, b"", _COMM_TRAILER),
                      _MID_START_PRIM + 1)
        self._command(_MID_START_PRIM,
                      _start_prim(handle, self._allocate_cop(), _CT_UPDATEPARAM, b"", _UPDATE_TRAILER),
                      _MID_START_PRIM + 1)
        self._command(_MID_SET_PARAM, _setcomparam(handle, 0x1C, 1), _MID_SET_PARAM + 1)
        self._command(_MID_SET_RESPID, _respid_install(handle, request_can_id, response_can_id),
                      _MID_SET_RESPID + 1)
        self._command(_MID_START_PRIM,
                      _start_prim(handle, self._allocate_cop(), _CT_UPDATEPARAM, b"", _UPDATE_TRAILER),
                      _MID_START_PRIM + 1)
        return handle, rx_cop

    def create_keepalive_cll(self, functional_can_id: int, *, period_ms: int = 1000) -> int:
        """Create a SEPARATE CLL and offload cyclic 3E80 TesterPresent to it."""
        handle = self._create_cll()
        self._bring_link_up(handle)
        self._command(_MID_START_PRIM,
                      _start_prim(handle, self._allocate_cop(), _CT_STARTCOMM, b"", _COMM_TRAILER),
                      _MID_START_PRIM + 1)
        self._command(_MID_START_PRIM,
                      _periodic(handle, self._allocate_cop(), functional_can_id, b"\x3e\x80", period_ms),
                      _MID_START_PRIM + 1)
        return handle

    def destroy_cll(self, handle: int) -> None:
        # Best-effort; a teardown ACK does not prove offloaded TesterPresent stopped.
        self._command(_MID_DISCONNECT, struct.pack("<I", handle), _MID_DISCONNECT + 1)
        self._command(_MID_DESTROY_CLL, struct.pack("<I", handle), _MID_DESTROY_CLL + 1)
        if handle in self._live_handles:
            self._live_handles.remove(handle)

    def send_on_cop(self, handle: int, request_can_id: int, request: bytes) -> int:
        """Send one one-shot UDS request; returns the send COP. Reads the TX ACK.

        A zero 0x464 status means the MDI queued the operation, not that the ECU
        received it. Nonzero status is an adapter rejection; its cause cannot
        be inferred from ECU power mode. In particular, malformed nested frames
        previously returned 0x2830 before any ECU transmission.
        """
        if self.closed or self.poisoned:
            raise LiveDpduError("session is closed or poisoned")
        cop = self._allocate_cop()
        deadline = time.monotonic() + self.timeout
        try:
            # build_one_shot already includes the eight-byte wire header.
            self.command.sendall(build_one_shot(handle, cop, request_can_id, request))
            rmid, rpay = self._recv_frame(self.command, deadline)
        except (OSError, TimeoutError, ValueError, struct.error):
            self.fail("StartComPrimitive send failed; delivery ambiguous")
        if rmid != _MID_START_PRIM + 1 or len(rpay) < 4:
            self.fail("StartComPrimitive reply malformed")
        if rpay[:4] != bytes(4):
            status = int.from_bytes(rpay[:4], "little")
            self.fail(f"D-PDU SENDRECV rejected (StartComPrimitive status "
                      f"0x{status:04X}); ECU delivery not established")
        return cop

    def read_event_uds(self, *, radio_handle: int, receive_cop: int,
                       response_can_id: int, timeout: float) -> bytes | None:
        """Return one reassembled radio UDS response, skipping non-ours events.

        None events (TX confirmations, keepalive, D-PDU event type 2, other CLLs)
        are skipped as provably-not-ours; a malformed look-alike raises.
        """
        deadline = time.monotonic() + timeout
        while True:
            mid, payload = self._recv_frame(self.events, deadline)
            if mid == _MID_LEN_IND:
                continue  # multi-frame length indication precedes the data event
            if mid != _MID_EVENT:
                raise ValueError(f"unexpected event frame 0x{mid:x}")
            uds = parse_radio_rx(payload, handle=radio_handle, cop=receive_cop,
                                 can_id=response_can_id)
            if uds is None:
                continue
            return uds


class LiveRadioAdapter:
    """UDS transport over one radio CLL: ``send``/``receive`` for ``UdsClient``.

    Correlation is enforced by ``OfflineSerializedSession`` (one request in
    flight) plus the session's strict allow-filter. Any ambiguity poisons the
    adapter AND the session and tears the tunnel down (fail-closed).

    A well-formed ``7F <sid> <nrc>`` echoing the in-flight service id is NOT an
    ambiguity: it is the correlated terminal answer to that request. ``receive``
    returns it unchanged and ``UdsClient.request`` raises ``TransactionError``
    ("service XX NRC xx"); the link stays up for the next request. Only a
    malformed or sid-mismatched ``7F`` poisons (changed 2026-11-10 after a
    per-DID NRC forced a link re-open each time and wedged the MDI).
    """

    def __init__(self, session: LiveDpduSession, *, radio_handle: int,
                 receive_cop: int, request_can_id: int, response_can_id: int):
        self.session = session
        self.radio_handle = radio_handle
        self.receive_cop = receive_cop
        self.request_can_id = request_can_id
        self.response_can_id = response_can_id
        self._guard = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
        self.poisoned = False

    def _fail(self, reason: str) -> None:
        self.poisoned = True
        self._guard.fail()
        try:
            self.session.fail(reason)
        finally:
            raise LiveDpduError(reason)

    def send(self, request: bytes) -> None:
        if self.poisoned or self.session.poisoned or self.session.closed:
            raise LiveDpduError("adapter is poisoned or session is down")
        try:
            if type(request) is not bytes or not request:
                raise ValueError("UDS request must be nonempty bytes")
            prefix = _required_positive_prefix(request)
            self._guard.begin(request, prefix)
        except (ValueError, CorrelationUnproven):
            self._fail("request cannot be safely sent")
        self.session.send_on_cop(self.radio_handle, self.request_can_id, request)

    def receive(self, timeout: float) -> bytes | None:
        if self.poisoned or self.session.poisoned or self.session.closed:
            raise LiveDpduError("adapter is poisoned or session is down")
        if self._guard.pending is None:
            raise LiveDpduError("no request is pending")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            self._fail("invalid response timeout")
        try:
            uds = self.session.read_event_uds(
                radio_handle=self.radio_handle, receive_cop=self.receive_cop,
                response_can_id=self.response_can_id, timeout=timeout)
            self._guard.accept(uds)
            return uds
        except CorrelationUnproven as exc:
            self._fail(str(exc))
        except (OSError, TimeoutError, ValueError, LiveDpduError, struct.error):
            self._fail("D-PDU response failed or timed out; session cannot be reused")


def open_live_programming_transport(*args: object, authorized_live_write: bool = False,
                                    **kwargs: object) -> None:
    """Interlock. Live programming is gated behind the CLI write path.

    This keeps the historical explicit interlock: there is no unattended live
    programming entrypoint. The gated live flash is driven only by
    ``cli.write`` after the LTZ hash preflight, VIN/part match, battery-voltage
    check, owner-required hard reset and explicit confirmation. Constructing a
    live transport without those gates is refused.
    """
    raise ProgrammingUnavailable(
        "live D-PDU programming is only reachable through the gated cli.write flow")
