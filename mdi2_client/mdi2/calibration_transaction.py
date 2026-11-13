"""Experimental A11 UDS programming transaction; transport intentionally absent.

This state machine has only been exercised against simulated transports. It is
not a complete MDI2 flash tool. No live transport is wired to this module.
"""
from __future__ import annotations

import time
import gzip
import hashlib
import math
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol
from xml.etree import ElementTree

from .calibration_payloads import Calibration, transfer_requests


class UdsTransport(Protocol):
    # Adapter owns verified TesterPresent/session timing, frame correlation,
    # bounded sends and receives. An interrupted send has an ambiguous result.
    def send(self, request: bytes) -> None: ...
    def receive(self, timeout: float) -> bytes | None: ...


class TransactionError(RuntimeError):
    """The operation stopped; an ECU may already be in programming mode."""


_PROGRAM_PHASES = frozenset({
    "read identifiers", "extended session", "disable DTC logging",
    "disable normal communication", "security access before transfer",
    "pre-programming routine", "programming session", "request download",
    "transfer data", "transfer exit", "programming-status readback",
    "reconnect finalization link", "verify identity after finalization reconnect",
    "re-enter extended session before finalization",
    "security access before finalization", "repair-shop identifier",
    "programming-date identifier", "finalization routine", "vehicle identifier",
    "ECU reset", "cleanup finalization link",
})
_SAFE_REASONS = frozenset({
    "SecurityAccess seed is not the observed all-FF state",
    "real CMAC seed but SBI not flipped and no key provided",
    "unexpected SecurityAccess response length",
    "invalid RequestDownload length format",
    "malformed RequestDownload maximum block length",
    "unsupported RequestDownload maximum block length",
    "target identity does not match expected vehicle",
    "unexpected transfer response length",
    "status readback differs from historical capture",
    "finalization link did not return a fresh client",
    "reconnected target identity does not match expected vehicle",
})
_SAFE_EXCEPTION_CLASSES = frozenset({
    "Exception", "OSError", "TimeoutError", "ConnectionError", "BrokenPipeError",
    "ConnectionResetError", "ConnectionAbortedError", "ConnectionRefusedError", "EOFError",
})

# Finalization 2E F198 repair-shop id: the stock SPS session writes a fixed
# ASCII "9999988888" (decoded Aug-2026 capture), NOT the module's read-back value.
_FINALIZATION_REPAIR_SHOP = b"9999988888"


def _current_programming_date(clock: Callable[[], time.struct_time] = time.localtime) -> bytes:
    """4-byte BCD YYYYMMDD for 2E F199, e.g. 2026-08-24 -> ``20 26 08 24``.

    SPS stamps the run date, not the module's previously-read F199 (echoing the
    old value would record a stale programming date).
    """
    now = clock()
    return bytes.fromhex(f"{now.tm_year:04d}{now.tm_mon:02d}{now.tm_mday:02d}")


class ProgramFailure(TransactionError):
    """Sanitized phase information for a possibly incomplete transaction."""

    def __init__(self, *, phase: str, transferred: int,
                 slot: int | None = None, block: int | None = None,
                 safe_reason: str = "transaction failed"):
        if type(phase) is not str or phase not in _PROGRAM_PHASES or type(transferred) is not int or not 0 <= transferred <= 14:
            raise ValueError("invalid programming failure context")
        if slot is not None and (type(slot) is not int or not 2 <= slot <= 15):
            raise ValueError("invalid programming failure slot")
        if block is not None and (type(block) is not int or not 0 <= block <= 255):
            raise ValueError("invalid programming failure block")
        if type(safe_reason) is not str:
            safe_reason = "transaction failed"
        transport_match = re.fullmatch(r"transport (?:send|receive) failed \(([A-Za-z][A-Za-z0-9_]*)(?: errno=-?[0-9]+)?\); ECU outcome unknown", safe_reason)
        safe_transport = transport_match is not None and transport_match.group(1) in _SAFE_EXCEPTION_CLASSES
        if (safe_reason not in _SAFE_REASONS and
                not re.fullmatch(r"service [0-9A-F]{2} (?:timed out|NRC [0-9A-F]{2}|malformed negative response|mismatched positive response)", safe_reason) and
                not safe_transport):
            safe_reason = "transaction failed"
        self.phase, self.transferred, self.slot, self.block = phase, transferred, slot, block
        self.safe_reason = safe_reason
        where = f"phase={phase} transferred={transferred}"
        if slot is not None:
            where += f" slot={slot:02X}"
        if block is not None:
            where += f" block={block:02X}"
        super().__init__(f"{where}: {safe_reason}; outcome may be ambiguous; no retry")


def _transport_failure(exc: Exception, action: str) -> TransactionError:
    # Error messages may contain vehicle identifiers, addresses or payloads.
    name = type(exc).__name__
    details = name if name in _SAFE_EXCEPTION_CLASSES else "Exception"
    if isinstance(exc, OSError) and isinstance(exc.errno, int):
        details += f" errno={exc.errno}"
    return TransactionError(f"transport {action} failed ({details}); ECU outcome unknown")


class UdsClient:
    def __init__(self, transport: UdsTransport, *, timeout: float = 5.0,
                 pending_timeout: float = 30.0, max_elapsed: float = 180.0,
                 clock: Callable[[], float] = time.monotonic):
        try:
            valid = all(type(value) in (int, float) and math.isfinite(value) and value > 0
                        for value in (timeout, pending_timeout, max_elapsed))
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("timeouts must be finite positive numbers")
        self.transport = transport
        self.timeout = timeout
        self.pending_timeout = pending_timeout
        self.max_elapsed = max_elapsed
        self.clock = clock

    def request(self, payload: bytes, positive_prefix: bytes) -> bytes:
        if not payload or not positive_prefix or positive_prefix[0] != (payload[0] + 0x40) & 0xFF:
            raise ValueError("invalid request/response pair")
        # A transport adapter must serialize requests, provide fully reassembled
        # ECU-specific responses, and prevent responses from earlier requests
        # from being delivered as a later response. This class cannot prove that.
        start = self.clock()
        hard_end = start + self.max_elapsed
        soft_end = min(start + self.timeout, hard_end)
        try:
            self.transport.send(payload)
        except Exception as exc:
            raise _transport_failure(exc, "send") from None
        while True:
            now = self.clock()
            remaining = min(soft_end, hard_end) - now
            if remaining <= 0:
                raise TransactionError(f"service {payload[0]:02X} timed out")
            try:
                response = self.transport.receive(remaining)
            except Exception as exc:
                raise _transport_failure(exc, "receive") from None
            if response is None:
                raise TransactionError(f"service {payload[0]:02X} timed out")
            if len(response) >= 2 and response[0] == 0x7F and response[1] == payload[0]:
                if len(response) != 3:
                    raise TransactionError(f"service {payload[0]:02X} malformed negative response")
                if response[2] == 0x78:
                    soft_end = min(self.clock() + self.pending_timeout, hard_end)
                    continue
                raise TransactionError(f"service {payload[0]:02X} NRC {response[2]:02X}")
            if response and response[0] == positive_prefix[0]:
                if not response.startswith(positive_prefix):
                    raise TransactionError(f"service {payload[0]:02X} mismatched positive response")
                return response
            # Ignore unrelated service traffic; hard deadline remains unchanged.


def max_block_length(response: bytes) -> int:
    if len(response) < 2 or response[0] != 0x74 or response[1] & 0x0F:
        raise TransactionError("invalid RequestDownload length format")
    width = response[1] >> 4
    if width < 1 or width > 4 or len(response) != width + 2:
        raise TransactionError("malformed RequestDownload maximum block length")
    result = int.from_bytes(response[2:], "big")
    if not 3 <= result <= 0xFFFF:
        raise TransactionError("unsupported RequestDownload maximum block length")
    return result


@dataclass(frozen=True)
class Identifiers:
    vin: bytes
    repair_shop: bytes
    programming_date: bytes

    def validate(self) -> None:
        if len(self.vin) != 17 or not all(0x20 <= b < 0x7F for b in self.vin):
            raise ValueError("VIN readback must be 17 printable bytes")
        if len(self.repair_shop) != 10 or len(self.programming_date) != 4:
            raise ValueError("unexpected repair-shop or programming-date length")


@dataclass(frozen=True)
class TrustedContainer:
    """Independently established unwrapped CSM slot, part number and SHA-256."""
    slot: int
    part: str
    sha256: str


@dataclass(frozen=True)
class ProgramResult:
    status: str
    slots_transferred: int


def read_identifiers(client: UdsClient) -> Identifiers:
    def read(did: bytes) -> bytes:
        return client.request(b"\x22" + did, b"\x62" + did)[3:]
    result = Identifiers(read(b"\xf1\x90"), read(b"\xf1\x98"), read(b"\xf1\x99"))
    result.validate()
    return result


def _complete_degenerate_unlock(client: UdsClient) -> None:
    """Send the degenerate ``27 02`` + 12 zero bytes and confirm ``67 02``.

    The caller has already read and confirmed the ``27 01`` seed is 31x0xFF.
    This is the vehicle-tested (2026-11-07) SBI-bypass key response; the exact
    bytes are load-bearing and must not change.
    """
    result = client.request(b"\x27\x02" + bytes(12), b"\x67\x02")
    if result != b"\x67\x02":
        raise TransactionError("unexpected SecurityAccess response length")


def unlock_all_ff_seed(client: UdsClient) -> None:
    seed = client.request(b"\x27\x01", b"\x67\x01")[2:]
    if seed != b"\xff" * 31:
        raise TransactionError("SecurityAccess seed is not the observed all-FF state")
    _complete_degenerate_unlock(client)


class _SecurityProvider(Protocol):
    def has_key(self, ecuid: bytes) -> bool: ...
    def compute_response(self, seed: bytes, key: bytes | None = ...) -> bytes: ...


def unlock_security_access(client: UdsClient, security: "_SecurityProvider | None" = None) -> None:
    """Probe the SecurityAccess seed and branch (SPS-matching; Aug-2026 decode).

    Sends ``27 01``, reads the ``67 01`` seed, then branches on the seed itself
    (no fixed assumption that the module is in the all-FF state):

      * seed == 31x0xFF  -> degenerate SBI-bypass unlock: ``27 02`` + 12 zero
        bytes. This is BYTE-IDENTICAL to ``unlock_all_ff_seed`` (vehicle-tested
        2026-11-07) and triggers while the EEPROM SBI bytes are flipped -- the
        current state of this radio.
      * real (non-all-FF) seed, with a ``security``
        (``mdi2.security_cmac.GMSecurityAccess``) holding a key for the seed's
        ECUID -> real AES-128-CMAC key response via ``compute_response``.
      * real seed, no usable key -> abort. No key is fabricated or hardcoded.

    The real stock SPS session caught a genuine 31-byte CMAC seed; the CMAC
    truncation shaping for a 31-byte seed is UNVERIFIED on hardware (see
    ``security_cmac`` -- no KAT vector), so that branch only engages when the
    caller explicitly supplies key material.
    """
    seed = client.request(b"\x27\x01", b"\x67\x01")[2:]
    if seed == b"\xff" * 31:
        _complete_degenerate_unlock(client)
        return
    if security is not None and security.has_key(seed[:16]):
        response = security.compute_response(seed)
        result = client.request(b"\x27\x02" + response, b"\x67\x02")
        if result != b"\x67\x02":
            raise TransactionError("unexpected SecurityAccess response length")
        return
    raise TransactionError("real CMAC seed but SBI not flipped and no key provided")


def program(client: UdsClient, calibrations: Sequence[Calibration], *,
            trusted_manifest: tuple[TrustedContainer, ...], expected_vin: bytes,
            adapter_max_request_length: int,
            reconnect_finalization: Callable[[UdsClient], UdsClient],
            release_finalization: Callable[[UdsClient], None],
            security: "_SecurityProvider | None" = None,
            programming_date: bytes | None = None,
            authorized: bool = False) -> ProgramResult:
    """Run the decoded stock SPS radio-0x80 recalibration sequence.

    This function is intentionally not exposed through a live CLI. It requires
    an independently verified adapter and operational power-mode/recovery plan.
    The stock SPS sequence performs exactly ONE radio hard reset, at
    finalization (``11 01`` below); it does NOT pre-reset the radio. An opt-in
    pre-reset fallback (not part of SPS) lives in
    ``live_calibration.write_ltz_calibration(pre_reset=True)`` for retrying a
    failed SPS-method write, and is the caller's responsibility, not this
    function's. ``programming_date`` defaults to the current run date (4-byte
    BCD YYYYMMDD) stamped into ``2E F199``.
    The manifest must be established independently from trusted stock artifacts,
    not generated from the package being checked; this cannot verify provenance.
    Any eventual LTZ live entrypoint must explicitly pin LTZ_REFERENCE rather
    than accepting an arbitrary manifest; no such entrypoint is provided.
    Its hashes establish identity, not ECU or vehicle compatibility. The adapter
    must provide bounded sends; a send failure can have an ambiguous outcome.
    The callback must tear down the transfer link and create a fresh finalization
    link as in the captured SPS session; passing a fresh object does not itself
    prove that the underlying hardware links were correctly re-established.
    The release callback owns the finalization link on every exit. Reconnection
    must clean up any partially opened link if it raises. It also retains
    ownership of any invalid return value: the release callback is invoked only
    for a fresh UdsClient with a distinct transport, so shared transports are
    never closed a second time by this transaction.
    A partial transfer or finalization failure requires OEM recovery procedures;
    never blindly retry or automatically reset after an error.
    """
    if authorized is not True:
        raise ValueError("programming requires explicit authorization")
    if not callable(reconnect_finalization) or not callable(release_finalization):
        raise ValueError("finalization-link reconnection and release callbacks are required")
    if not isinstance(trusted_manifest, tuple) or len(trusted_manifest) != 14:
        raise ValueError("an immutable independently established manifest is required")
    if not isinstance(expected_vin, bytes) or len(expected_vin) != 17:
        raise ValueError("an independently supplied 17-byte expected VIN is required")
    if type(adapter_max_request_length) is not int or not 20 <= adapter_max_request_length <= 0x0FFF:
        raise ValueError("adapter request limit must be between 20 and 4095 bytes")
    if programming_date is None:
        programming_date = _current_programming_date()
    elif not (isinstance(programming_date, bytes) and len(programming_date) == 4):
        raise ValueError("programming_date must be 4 bytes (BCD YYYYMMDD)")
    if any(type(cal.slot) is not int for cal in calibrations):
        raise ValueError("calibration slot numbers must be integers")
    # Pin all object fields and data before verification; never iterate the
    # caller's mutable sequence again after checking the trusted manifest.
    calibrations = tuple(Calibration(cal.slot, cal.part, bytes(cal.container))
                         for cal in calibrations)
    if (len(calibrations) != 14 or any(type(x.slot) is not int for x in calibrations) or
            [x.slot for x in calibrations] != list(range(2, 16))):
        raise ValueError("expected exactly ordered calibration slots 02–0F")
    for cal, trusted in zip(calibrations, trusted_manifest):
        data = cal.container
        if (not isinstance(trusted, TrustedContainer) or type(trusted.slot) is not int or
                trusted.slot != cal.slot or
                trusted.part != cal.part or not re.fullmatch(r"[0-9a-f]{64}", trusted.sha256) or
                hashlib.sha256(data).hexdigest() != trusted.sha256):
            raise ValueError(f"slot {cal.slot:02X}: trusted manifest mismatch")
        if (not re.fullmatch(r"\d{8}", cal.part) or len(data) < 0x36B or
                len(data) > 0xFFFFFFFF or data[3] != cal.slot or
                data[6:10] != b"CSM\x00" or data[0x368:0x36B] != b"\x1f\x8b\x08"):
            raise ValueError(f"slot {cal.slot:02X}: invalid CSM container")
        try:
            root = ElementTree.fromstring(gzip.decompress(data[0x368:]))
        except (OSError, EOFError, ElementTree.ParseError) as exc:
            raise ValueError(f"slot {cal.slot:02X}: invalid calibration XML") from exc
        if root.tag != "{http://caltools.gm.com/calovride}CalOvrideFile":
            raise ValueError(f"slot {cal.slot:02X}: invalid calibration XML root")

    phase, slot, block, transferred = "read identifiers", None, None, 0
    owned_finalization = None
    try:
        # Identity values are read from this ECU and retained only in memory.
        identifiers = read_identifiers(client)
        if identifiers.vin != expected_vin:
            raise TransactionError("target identity does not match expected vehicle")
        phase = "extended session"
        client.request(b"\x10\x03", b"\x50\x03")
        # SPS disables DTC logging then normal communication before the transfer.
        phase = "disable DTC logging"
        client.request(b"\x85\x02", b"\xc5\x02")
        phase = "disable normal communication"
        # 28 03 01: disableRxAndTx, communicationType=01 (normalCommunicationMessages).
        # The communicationType byte is mandatory; 28 03 alone -> NRC 13 (observed
        # live 2026-11-10). Captured SPS frame: 03 28 03 01. Response echoes only
        # the controlType -> 68 03.
        client.request(b"\x28\x03\x01", b"\x68\x03")
        phase = "security access before transfer"
        unlock_security_access(client, security)
        phase = "pre-programming routine"
        client.request(b"\x31\x01\x02\x49", b"\x71\x01\x02\x49")
        phase = "programming session"
        client.request(b"\x10\x02", b"\x50\x02")

        for cal in calibrations:
            slot, block, phase = cal.slot, None, "request download"
            initial = next(transfer_requests(cal, 0x0FFF))
            negotiated = max_block_length(client.request(initial, b"\x74"))
            requests = transfer_requests(cal, min(negotiated, adapter_max_request_length))
            next(requests)  # RequestDownload was already sent.
            for request in requests:
                block = request[1] if request[0] == 0x36 else None
                phase = "transfer data" if block is not None else "transfer exit"
                prefix = b"\x76" + request[1:2] if block is not None else b"\x77"
                reply = client.request(request, prefix)
                if len(reply) != len(prefix):
                    raise TransactionError("unexpected transfer response length")
            transferred += 1

        slot, block, phase = None, None, "programming-status readback"
        psi = client.request(b"\x22\xf0\xf0", b"\x62\xf0\xf0")[3:]
        if psi != b"".join(bytes([item, 0]) for item in range(2, 16)):
            raise TransactionError("status readback differs from historical capture")
        phase = "reconnect finalization link"
        next_client = reconnect_finalization(client)
        if (not isinstance(next_client, UdsClient) or next_client is client or
                next_client.transport is client.transport):
            raise TransactionError("finalization link did not return a fresh client")
        owned_finalization = next_client
        client = next_client
        phase = "verify identity after finalization reconnect"
        # SPS link-bounce: return to the DEFAULT session (10 01) FIRST, then read
        # the ECU id and re-enter extended. The module rejects a direct
        # 10 02 -> 10 03 with NRC 7E (subFunctionNotSupportedInActiveSession,
        # observed live 2026-11-10); 10 01 clears the programming-session state.
        # SPS re-reads 22 F1B0 (-> 62 F1B0 80) rather than F190; the VIN is
        # re-personalized below via 2E F190 <expected_vin>.
        client.request(b"\x10\x01", b"\x50\x01")
        if client.request(b"\x22\xf1\xb0", b"\x62\xf1\xb0") != b"\x62\xf1\xb0\x80":
            raise TransactionError("reconnected target identity does not match expected vehicle")
        phase = "re-enter extended session before finalization"
        client.request(b"\x10\x03", b"\x50\x03")
        phase = "security access before finalization"
        unlock_security_access(client, security)
        phase = "repair-shop identifier"
        client.request(b"\x2e\xf1\x98" + _FINALIZATION_REPAIR_SHOP, b"\x6e\xf1\x98")
        phase = "programming-date identifier"
        client.request(b"\x2e\xf1\x99" + programming_date, b"\x6e\xf1\x99")
        phase = "finalization routine"
        client.request(b"\x31\x01\x03\x9b", b"\x71\x01\x03\x9b")
        phase = "vehicle identifier"
        client.request(b"\x2e\xf1\x90" + expected_vin, b"\x6e\xf1\x90")
        phase = "ECU reset"
        client.request(b"\x11\x01", b"\x51\x01")
    except Exception as exc:
        # ProgramFailure admits only fixed, non-sensitive reason patterns.
        detail = str(exc) if isinstance(exc, TransactionError) else "transaction failed"
        raise ProgramFailure(phase=phase, transferred=transferred, slot=slot,
                             block=block, safe_reason=detail) from None
    finally:
        if owned_finalization is not None:
            active = sys.exc_info()[1]
            try:
                release_finalization(owned_finalization)
            except Exception:
                if isinstance(active, ProgramFailure):
                    active.cleanup_failed = True
                    active.args = (f"{active}; finalization link cleanup failed",)
                elif active is None:
                    raise ProgramFailure(phase="cleanup finalization link", transferred=transferred) from None
    return ProgramResult("RESET_ACCEPTED_NOT_VERIFIED", transferred)
