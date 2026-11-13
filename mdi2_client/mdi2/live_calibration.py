"""Gated live orchestration: re-arm, identify, LTZ write, and recovery.

Everything that opens a socket to the MDI2 lives here. The gating policy for a
live calibration write (plan + explicit confirmation + VIN/part match + LTZ hash
validation + battery-voltage check + owner-required hard reset) is enforced in
``plan_ltz_write``/``write_ltz_calibration``; the actual UDS sequence is the
unchanged ``calibration_transaction.program`` state machine driven over the live
``LiveRadioAdapter``.

No VIN, serial, key or address is hard-coded here: the caller supplies the unit
serial (for the Blowfish key), the expected VIN, and the package folder.
"""
from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import crypto, messages
from .battery_voltage import read_battery_mv
from .calibration_payloads import Calibration
from .calibration_readback import Readback, compare_post_reboot
from .calibration_transaction import (
    ProgramFailure, ProgramResult, TransactionError, UdsClient, program,
)
from .const import DEVICE_IP_DEFAULT, DPDU_PORT, SERVICE_PORTS
from .discovery import resolve_device
from .ltz_preflight import validate_ltz_package, identify_source_calibration
from .ltz_reference_manifest import LTZ_REFERENCE
from .live_programming_transport import (
    LiveDpduError, LiveDpduSession, LiveRadioAdapter,
)
from .transport import Session

# Radio ECU 0x80 addressing on the MDI2 D-PDU (tester byte F1) path, confirmed
# live 2026-11-07 (DPDU doc §11 live follow-up): request/response CAN ids.
RADIO_REQUEST_CAN_ID = 0x14DA80F1
RADIO_RESPONSE_CAN_ID = 0x145AF180
FUNCTIONAL_CAN_ID = 0x10DBFEF1
BCM_REQUEST_CAN_ID = 0x14DA40F1
BCM_RESPONSE_CAN_ID = 0x142AF140

# Minimum programming supply, owner requirement; upper bound rejects bad samples.
MIN_PROGRAMMING_MV = 12_000
MAX_PLAUSIBLE_MV = 30_000

# Capture-pinned PDU START body; trailing u32-LE is the live management session id.
_PDU_START_BODY = bytes.fromhex(
    "3008000002000000000000004b080000000000000100000000000000020000004a"
    "08000001000000080000004150505f4e414d45030000005044554a080000010000"
    "0007000000434f4d4d414e4405000000535441525400000000")
_PDU_START_PREFIX = _PDU_START_BODY[:-4]
_PDU_POLL = bytes.fromhex("2e08000001000000")


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _resolve_target(serial: int | None, host: str | None) -> tuple[int, str]:
    """Fill a missing ``serial`` and/or ``host`` from a live announce beacon.

    Only a missing field triggers a beacon listen, so callers that pass both
    explicitly never touch the network here (keeps offline tests hermetic).
    Resolving ``host`` from the beacon source tracks the MDI2's RNDIS IP, which
    is not stable across reconnects/power cycles. Raises ``LookupError`` if no
    beacon is seen when one is needed.
    """
    if serial is not None and host is not None:
        return serial, host
    info = resolve_device()
    return (info.serial if serial is None else serial,
            info.ip if host is None else host)


def rearm_dpdu_tunnel(serial: int | None = None, host: str | None = None, *,
                      dialer_ip: str | None = None, force_start: bool = False) -> bool:
    """Re-open the D-PDU tunnel (TCP/10123) via the management PDU START flow.

    ``serial``/``host`` auto-resolve from the device announce beacon when
    omitted (see ``_resolve_target``). Returns True if 10123 accepts connections
    afterward. This recovers the tunnel only when the device's session service
    is still alive; a crashed/wedged session service (symptom: 9052 stops
    answering its control handshake) needs a USB power-cycle. Reconstructed from
    the capture and verified field-by-field.
    """
    serial, host = _resolve_target(serial, host)
    if not force_start and _port_open(host, DPDU_PORT):
        return True
    if dialer_ip is None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect((host, 9052))
            dialer_ip = route.getsockname()[0]
    key = crypto.derive_key(serial)
    bank = Session(key, host)
    session_id = None
    try:
        # The special 9011 handshake follows successful session_open.
        bank.connect(ports=[port for port in SERVICE_PORTS if port != 9011])
        ch52 = bank.channels[9052]
        date = time.strftime("%d%m%y%H%M%S") + "1234567"
        ch52.send(messages.session_open("macbench", dialer_ip, host, date, master=True))
        for _counter, body in ch52.recv_frames(5.0):
            if body[:1] == b"{":
                parsed = messages.parse(body)
                if isinstance(parsed, dict) and isinstance(parsed.get("data"), dict):
                    session_id = parsed["data"].get("session", session_id)
        if type(session_id) is not int or not 0 <= session_id <= 0xFFFFFFFF:
            raise LiveDpduError("management session_open returned no session id "
                                "(session service likely wedged; USB power-cycle required)")
        bank.connect(ports=[9011])
        ch50 = bank.channels[9050]
        for _ in range(3):
            ch50.send(_PDU_POLL)
        ch50.recv_frames(timeout=2.0)
        ch50.send(_PDU_START_PREFIX + struct.pack("<I", session_id))
        replies = ch50.recv_frames(timeout=3.0)
        if not any(b"PDU" in body and b"START" in body for _, body in replies):
            raise LiveDpduError("PDU START response did not echo PDU/START")
    finally:
        if type(session_id) is int and 9052 in bank.channels:
            try:
                bank.channels[9052].send(messages.session_close(session_id))
                bank.channels[9052].recv_frames(timeout=2.0)
            except (OSError, ValueError):
                pass
        bank.close()
    for _ in range(5):
        if _port_open(host, DPDU_PORT):
            return True
        time.sleep(1.0)
    return False


def _open_session(host: str, timeout: float) -> LiveDpduSession:
    command = socket.create_connection((host, DPDU_PORT), timeout=timeout)
    events = None
    try:
        command.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        events = socket.create_connection((host, DPDU_PORT), timeout=timeout)
        events.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        session = LiveDpduSession(command, events, timeout=timeout)
        session.hello()
        session.clear_rx_buffer()
        return session
    except Exception:
        command.close()
        if events is not None:
            events.close()
        raise


class LiveRadioLink:
    """A live radio link: session + current radio/keepalive CLLs + a UdsClient.

    ``reconnect`` models the captured finalization re-link (destroy both CLLs,
    create fresh radio + keepalive CLLs on the same sockets, restart cyclic
    TesterPresent) and returns a NEW adapter/client — satisfying ``program``'s
    requirement that finalization yields a distinct transport.
    """

    def __init__(self, session: LiveDpduSession):
        self.session = session
        self.radio_handle: int | None = None
        self.keepalive_handle: int | None = None
        try:
            self._bring_up()
        except Exception:
            session.close()
            raise

    def _bring_up(self) -> None:
        self.radio_handle, self.receive_cop = self.session.create_radio_cll(
            RADIO_REQUEST_CAN_ID, RADIO_RESPONSE_CAN_ID)
        self.keepalive_handle = self.session.create_keepalive_cll(FUNCTIONAL_CAN_ID)
        time.sleep(1.1)  # let at least one cyclic TesterPresent go out

    def adapter(self) -> LiveRadioAdapter:
        return LiveRadioAdapter(self.session, radio_handle=self.radio_handle,
                                receive_cop=self.receive_cop,
                                request_can_id=RADIO_REQUEST_CAN_ID,
                                response_can_id=RADIO_RESPONSE_CAN_ID)

    def client(self, **kw) -> UdsClient:
        return UdsClient(self.adapter(), **kw)

    def reconnect(self) -> None:
        if self.keepalive_handle is not None:
            self.session.destroy_cll(self.keepalive_handle)
            self.keepalive_handle = None
        if self.radio_handle is not None:
            self.session.destroy_cll(self.radio_handle)
            self.radio_handle = None
        self._bring_up()

    def close(self) -> None:
        self.session.close()


@dataclass(frozen=True)
class Identity:
    vin: bytes
    f18c: bytes
    f1a0: bytes
    f182: bytes


def _read_did(client: UdsClient, did: bytes) -> bytes:
    return client.request(b"\x22" + did, b"\x62" + did)


def _require_power_off(session: LiveDpduSession, timeout: float) -> None:
    """Read BCM F085; require the OFF value observed before calibration.

    This is distinct from the Service Mode precondition of the data-wipe RID.
    Keep the radio link alive while using a separate, temporary BCM CLL.
    """
    handle, cop = session.create_radio_cll(BCM_REQUEST_CAN_ID, BCM_RESPONSE_CAN_ID)
    try:
        adapter = LiveRadioAdapter(session, radio_handle=handle, receive_cop=cop,
                                   request_can_id=BCM_REQUEST_CAN_ID,
                                   response_can_id=BCM_RESPONSE_CAN_ID)
        response = _read_did(UdsClient(adapter, timeout=timeout), b"\xf0\x85")
        if response != b"\x62\xf0\x85\x00":
            raise TransactionError("BCM F085 is not the documented OFF value; aborting before programming")
    finally:
        if not session.closed:
            session.destroy_cll(handle)


def _require_voltage(session: LiveDpduSession) -> int:
    voltage = read_battery_mv(session.command)
    if type(voltage) is not int or not MIN_PROGRAMMING_MV <= voltage <= MAX_PLAUSIBLE_MV:
        raise TransactionError("battery voltage outside programming window")
    return voltage


def _probe_radio_reachable(link: "LiveRadioLink") -> bytes:
    """Direct F190 read that preserves the adapter rejection status.

    ``UdsClient`` deliberately masks transport errors, so a first read is done
    straight over the adapter: a ``LiveDpduError`` here carries the real reason
    without inferring a cause such as ECU power mode from that status alone.
    """
    adapter = link.adapter()
    adapter.send(b"\x22\xf1\x90")           # raises LiveDpduError with the real reason
    deadline = time.monotonic() + 6.0
    while True:
        uds = adapter.receive(max(0.2, deadline - time.monotonic()))
        if uds is None or time.monotonic() >= deadline:
            raise TransactionError("radio identity read timed out")
        if uds != b"\x7f\x22\x78":
            if not uds.startswith(b"\x62\xf1\x90"):
                raise TransactionError("unexpected F190 response")
            return uds[3:]


def identify(serial: int | None = None, host: str | None = None, *,
             timeout: float = 6.0) -> Identity:
    """READ-ONLY identification: open a radio link and read VIN/serial/MEC/cal meta.

    ``serial``/``host`` auto-resolve from the announce beacon when omitted.
    Sends only ``$22`` reads behind cyclic TesterPresent. No session control,
    security, reset or programming. Fails closed on any ambiguity.
    """
    serial, host = _resolve_target(serial, host)
    if not rearm_dpdu_tunnel(serial, host):
        raise LiveDpduError("D-PDU tunnel is not available (re-arm failed)")
    session = _open_session(host, timeout)
    link = LiveRadioLink(session)
    try:
        _probe_radio_reachable(link)  # preserves adapter rejection status
        client = link.client(timeout=timeout)
        vin = _read_did(client, b"\xf1\x90")[3:]
        f18c = _read_did(client, b"\xf1\x8c")[3:]
        f1a0 = _read_did(client, b"\xf1\xa0")[3:]
        f182 = _read_did(client, b"\xf1\x82")
        return Identity(vin, f18c, f1a0, f182)
    finally:
        link.close()


@dataclass(frozen=True)
class WritePlan:
    calibrations: tuple[Calibration, ...]
    expected_vin: bytes
    observed_vin: bytes
    battery_mv: int | None
    f182: bytes
    source_calibration: str


def plan_ltz_write(folder: Path, serial: int, expected_vin: bytes,
                   host: str = DEVICE_IP_DEFAULT, *, timeout: float = 6.0,
                   sample_voltage: bool = True, fresh_start: bool = False) -> WritePlan:
    """Validate the package + the connected module WITHOUT writing anything.

    Enforces every non-destructive gate: the 14 LTZ containers must match the
    pinned ``LTZ_REFERENCE`` hashes; the connected radio's VIN must equal the
    caller's expected VIN; its source profile must match the documented LTZ or
    High Country metadata; BCM power mode must be OFF. A dry-run voltage sample
    is optional: the actual writer takes its one sample after the reset.
    """
    if type(expected_vin) is not bytes or len(expected_vin) != 17:
        raise ValueError("expected VIN must be 17 bytes")
    calibrations = validate_ltz_package(folder)  # pinned-hash check, before any I/O
    if not rearm_dpdu_tunnel(serial, host, force_start=fresh_start):
        raise LiveDpduError("D-PDU tunnel is not available (re-arm failed)")
    session = _open_session(host, timeout)
    link = LiveRadioLink(session)
    try:
        observed_vin = _probe_radio_reachable(link)
        client = link.client(timeout=timeout)
        if observed_vin != expected_vin:
            raise TransactionError("connected module VIN does not match expected VIN")
        f182 = _read_did(client, b"\xf1\x82")
        source = identify_source_calibration(calibrations, f182)
        _require_power_off(session, timeout)
        battery_mv = _require_voltage(session) if sample_voltage else None
        return WritePlan(calibrations, expected_vin, observed_vin, battery_mv, f182, source)
    finally:
        link.close()


@dataclass(frozen=True)
class WriteOutcome:
    transaction: ProgramResult
    readback: Readback


def write_ltz_calibration(folder: Path, serial: int, expected_vin: bytes,
                          host: str = DEVICE_IP_DEFAULT, *, timeout: float = 8.0,
                          confirmed: bool = False,
                          adapter_max_request_length: int = 0x0FFF,
                          pre_reset: bool = False,
                          security: "object | None" = None) -> WriteOutcome:
    """Perform the ONE gated live LTZ write. Requires ``confirmed=True``.

    Default sequence (``pre_reset=False``) matches the decoded stock SPS
    transcript exactly: validate hashes, VIN, supported source metadata and BCM
    OFF on a fresh link, take one voltage sample, then run ``program`` (which
    performs the single radio ``11 01`` at finalization). No radio pre-reset.

    ``pre_reset=True`` is an OPT-IN fallback (NOT part of SPS): before the write
    it performs a radio hard reset (``10 03`` -> SecurityAccess -> ``11 01`` ->
    ``51 01``), reconnects and re-checks identity/source/OFF. Use it only to
    retry a failed SPS-method write. Its SecurityAccess uses the same
    probe-and-branch as ``program`` (``security``), not a hardcoded all-FF key.

    ``security`` (an ``mdi2.security_cmac.GMSecurityAccess`` or None) is threaded
    into both the optional pre-reset unlock and ``program``. With None (the
    default, and the SBI-flipped state of this radio) the degenerate all-FF
    unlock path runs; a real non-degenerate seed with no key aborts cleanly.

    Finally read back post-reboot F182 and compare every slot. Never retries;
    any failure leaves a ProgramFailure with sanitized phase info for the
    caller's recovery decision.
    """
    if confirmed is not True:
        raise ValueError("live write requires explicit confirmation")
    if type(adapter_max_request_length) is not int or not 20 <= adapter_max_request_length <= 0x0FFF:
        raise ValueError("adapter request limit must be between 20 and 4095 bytes")
    plan = plan_ltz_write(folder, serial, expected_vin, host, timeout=timeout,
                          sample_voltage=False, fresh_start=True)

    if pre_reset:
        # OPT-IN pre-reset fallback (NOT stock SPS). Fresh link: identity + OFF,
        # extended session, probe-and-branch SecurityAccess, hard reset, reboot.
        session = _open_session(host, timeout)
        link = LiveRadioLink(session)
        try:
            reset_client = link.client(timeout=timeout)
            if _read_did(reset_client, b"\xf1\x90")[3:] != expected_vin:
                raise TransactionError("pre-reset VIN mismatch")
            _require_power_off(session, timeout)
            reset_client.request(b"\x10\x03", b"\x50\x03")
            from .calibration_transaction import unlock_security_access
            unlock_security_access(reset_client, security)
            if reset_client.request(b"\x11\x01", b"\x51\x01") != b"\x51\x01":
                raise TransactionError("hard reset acknowledgement mismatch")
        except Exception as exc:
            link.close()
            raise TransactionError(f"owner-required hard reset failed: {type(exc).__name__}") from None
        link.close()
        time.sleep(12.0)  # allow the radio to reboot before reconnecting

    if not rearm_dpdu_tunnel(serial, host):
        raise LiveDpduError("tunnel unavailable; aborting before any write")
    session = _open_session(host, timeout)
    link = LiveRadioLink(session)
    try:
        client = link.client(timeout=timeout)
        client.request(b"\x10\x03", b"\x50\x03")
        if _read_did(client, b"\xf1\x90")[3:] != expected_vin:
            raise TransactionError("pre-write VIN mismatch; aborting before any write")
        _require_power_off(session, timeout)
        source = identify_source_calibration(plan.calibrations, _read_did(client, b"\xf1\x82"))
        if source != plan.source_calibration:
            raise TransactionError("source calibration changed; aborting before any write")
        _require_voltage(session)  # One sample, after reconnect and before program().

        def reconnect_finalization(_old: UdsClient) -> UdsClient:
            link.reconnect()
            return link.client(timeout=timeout)

        def release_finalization(_client: UdsClient) -> None:
            link.close()

        result = program(
            client, plan.calibrations, trusted_manifest=LTZ_REFERENCE,
            expected_vin=expected_vin, adapter_max_request_length=adapter_max_request_length,
            reconnect_finalization=reconnect_finalization,
            release_finalization=release_finalization, security=security,
            authorized=True)
    finally:
        link.close()
    # program's release callback already closed the finalization link.

    # Post-reboot readback on a brand new link.
    time.sleep(12.0)
    if not rearm_dpdu_tunnel(serial, host):
        raise LiveDpduError("tunnel unavailable for post-write readback")
    session = _open_session(host, timeout)
    verify = LiveRadioLink(session)
    try:
        vclient = verify.client(timeout=timeout)
        if _read_did(vclient, b"\xf1\x90") != b"\x62\xf1\x90" + expected_vin:
            raise TransactionError("post-write VIN mismatch")
        readback = compare_post_reboot(
            plan.calibrations, _read_did(vclient, b"\xf1\x82"),
            _read_did(vclient, b"\xf0\xf1"), _read_did(vclient, b"\xf0\xf2"))
        if readback.mismatching_slots:
            raise TransactionError(
                f"post-write readback mismatch in slots "
                f"{[f'{s:02X}' for s in readback.mismatching_slots]}")
        return WriteOutcome(result, readback)
    finally:
        verify.close()


def recover_state(serial: int, host: str = DEVICE_IP_DEFAULT, *, timeout: float = 6.0,
                  force_default_session: bool = False) -> dict:
    """Diagnose a module possibly left in programming mode; no blind retry.

    Reports VIN, F0F0 programming-status and F0F1/F0F2 counters. Only when
    ``force_default_session=True`` does it send a single ``10 01`` default-session
    request to bring the ECU out of a non-default session. It never re-sends
    programming data and never resets automatically.
    """
    if not rearm_dpdu_tunnel(serial, host):
        raise LiveDpduError("D-PDU tunnel unavailable for recovery diagnosis")
    session = _open_session(host, timeout)
    link = LiveRadioLink(session)
    report: dict = {}
    try:
        client = link.client(timeout=timeout)
        report["vin"] = _read_did(client, b"\xf1\x90")[3:].hex()
        report["f0f0"] = _read_did(client, b"\xf0\xf0")[3:].hex()
        report["f0f1"] = _read_did(client, b"\xf0\xf1")[3:].hex()
        report["f0f2"] = _read_did(client, b"\xf0\xf2")[3:].hex()
        if force_default_session:
            client.request(b"\x10\x01", b"\x50\x01")
            report["default_session"] = "requested (50 01 acknowledged)"
        return report
    finally:
        link.close()
