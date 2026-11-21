"""Simulator-only orchestration of the owner-required pre-programming reset.

No MDI2 connection or live entrypoint is provided. Successful simulated checks
are not evidence of radio reboot, link freshness, or live programming readiness.
"""
from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Protocol, TypeVar

from .calibration_transaction import ProgramFailure, TransactionError, unlock_all_ff_seed

T = TypeVar("T")


class SimulatedLink(Protocol):
    """A simulated UDS link; request() returns a fully assembled response."""

    def request(self, payload: bytes, positive_prefix: bytes) -> bytes: ...
    def close(self) -> None: ...


def simulate_reset_then_program(
    open_link: Callable[[], SimulatedLink],
    program: Callable[[SimulatedLink], T],
    *,
    expected_vin: bytes,
    read_power_mode: Callable[[], int],
    read_voltage_mv: Callable[[], int],
    authorized: bool = False,
) -> T:
    """Require identity, hard-reset acknowledgement, reconnect, identity, then program.

    ``open_link`` must represent a fresh PDU/session/link startup. The returned
    simulated link instances must be distinct. The simulator does not establish
    that a real adapter has shut down its old cyclic COP, that a radio has
    rebooted, or that a response is fresh. A live integration needs those checks
    and independently pinned package/vehicle compatibility before use.
    The injected voltage reader is called once after reconnecting, immediately
    before programming, and must return integer millivolts from 12000 through
    30000. This is a data-validity bound and the user's minimum, not proof that
    any particular value, including 30000 mV, is safe for programming.
    The injected BCM power-mode reader must report the observed OFF value 00
    before the pre-programming reset. This is a test precondition, not a full
    specification of the vehicle's power modes.
    """
    if authorized is not True:
        raise ValueError("explicit authorization is required")
    if (type(expected_vin) is not bytes or len(expected_vin) != 17 or
            not all(0x20 <= byte < 0x7f for byte in expected_vin)):
        raise ValueError("an expected 17-byte printable VIN is required")
    if (not callable(open_link) or not callable(program) or not callable(read_voltage_mv)
            or not callable(read_power_mode)):
        raise ValueError("link, power-mode, voltage and programming callbacks are required")

    first: SimulatedLink | None = None
    second: SimulatedLink | None = None
    first_close_attempted = False
    voltage = None
    phase = "open initial link"
    try:
        first = open_link()
        phase = "verify identity before reset"
        if first.request(b"\x22\xf1\x90", b"\x62\xf1\x90") != b"\x62\xf1\x90" + expected_vin:
            raise TransactionError("target identity mismatch")
        phase = "check power mode before reset"
        mode = read_power_mode()
        if type(mode) is not int or mode != 0:
            raise TransactionError("power mode is not the observed OFF value")
        phase = "enter extended session"
        if not first.request(b"\x10\x03", b"\x50\x03").startswith(b"\x50\x03"):
            raise TransactionError("extended-session response mismatch")
        phase = "unlock pre-reset session"
        unlock_all_ff_seed(first)
        phase = "reset radio"
        if first.request(b"\x11\x01", b"\x51\x01") != b"\x51\x01":
            raise TransactionError("reset acknowledgement mismatch")
        phase = "close initial link"
        first_close_attempted = True
        first.close()
        phase = "open post-reset link"
        second = open_link()
        if second is first:
            raise TransactionError("post-reset link must be a distinct instance")
        phase = "re-establish extended session"
        if not second.request(b"\x10\x03", b"\x50\x03").startswith(b"\x50\x03"):
            raise TransactionError("extended-session response mismatch")
        phase = "verify identity after reset"
        if second.request(b"\x22\xf1\x90", b"\x62\xf1\x90") != b"\x62\xf1\x90" + expected_vin:
            raise TransactionError("target identity mismatch")
        phase = "check voltage before programming"
        voltage = None
        voltage = read_voltage_mv()
        if type(voltage) is not int or not 12000 <= voltage <= 30000:
            raise TransactionError("invalid or out-of-range battery voltage")
        phase = "program"
        return program(second)
    except ProgramFailure as exc:
        # Reconstruct: exception args and attributes can be modified after init.
        if phase == "program" and type(exc) is ProgramFailure:
            try:
                safe = ProgramFailure(phase=exc.phase, transferred=exc.transferred,
                                      slot=exc.slot, block=exc.block,
                                      safe_reason=getattr(exc, "safe_reason", "transaction failed"))
                if getattr(exc, "cleanup_failed", False) is True:
                    safe.cleanup_failed = True
                    safe.args = (f"{safe}; finalization link cleanup failed",)
            except (ValueError, AttributeError):
                raise TransactionError("programming failed with invalid progress metadata; no retry") from None
            raise safe from None
        raise TransactionError(f"pre-reset sequence stopped at {phase} (ProgramFailure); no retry") from None
    except Exception as exc:
        # Do not copy arbitrary adapter exception text or identifiers into logs.
        detail = type(exc).__name__
        if isinstance(exc, OSError) and isinstance(exc.errno, int):
            detail += f" errno={exc.errno}"
        if (phase.startswith("check voltage") and type(voltage) is int and
                voltage < 12000):
            detail += f" voltage_mv={voltage} minimum_mv=12000"
        if (phase.startswith("check voltage") and type(voltage) is int and
                voltage > 30000):
            detail += f" voltage_mv={voltage} maximum_data_value_mv=30000"
        raise TransactionError(f"pre-reset sequence stopped at {phase} ({detail}); no retry") from None
    finally:
        # No assumption is made that closing a socket tears down device-side COPs.
        cleanup_failed = False
        if second is not None and second is not first:
            try:
                second.close()
            except Exception:
                cleanup_failed = True
        if first is not None and not first_close_attempted:
            try:
                first.close()
            except Exception:
                cleanup_failed = True
        if cleanup_failed:
            active = sys.exc_info()[1]
            if active is None:
                raise TransactionError("link cleanup failed; no verified completion") from None
            if type(active) in (ProgramFailure, TransactionError):
                active.cleanup_failed = True
                active.args = (f"{active}; link cleanup failed",)
