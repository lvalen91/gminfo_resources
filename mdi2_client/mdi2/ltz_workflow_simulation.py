"""End-to-end LTZ programming model using only injected simulated links.

No live MDI2 adapter or command-line flash entrypoint is supplied here.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .calibration_pre_reset_simulation import SimulatedLink, simulate_reset_then_program
from .calibration_readback import Readback, compare_post_reboot
from .calibration_transaction import ProgramResult, TransactionError, UdsClient, program
from .ltz_preflight import validate_ltz_package
from .ltz_reference_manifest import LTZ_REFERENCE


@dataclass(frozen=True)
class SimulatedOutcome:
    transaction: ProgramResult
    readback: Readback


class _SimulatedLinkLease(UdsClient):
    """Close an injected simulated link at most once, even across two owners."""

    def __init__(self, link: UdsClient):
        self._link = link
        self.transport = link.transport
        self._close_attempted = False

    def request(self, payload: bytes, positive_prefix: bytes) -> bytes:
        if self._close_attempted:
            raise TransactionError("simulated link already closed")
        return self._link.request(payload, positive_prefix)

    def close(self) -> None:
        if not self._close_attempted:
            self._close_attempted = True
            self._link.close()


def simulate_ltz_workflow(
    folder: Path,
    *,
    expected_vin: bytes,
    open_link: Callable[[], SimulatedLink],
    read_power_mode: Callable[[], int],
    read_voltage_mv: Callable[[], int],
    reconnect_finalization: Callable[[UdsClient], UdsClient],
    release_finalization: Callable[[UdsClient], None],
    read_after_reboot: Callable[[], tuple[bytes, bytes, bytes, bytes]],
    adapter_max_request_length: int,
    authorized: bool = False,
) -> SimulatedOutcome:
    """Model stock-package verification, reset, voltage, programming and readback.

    ``read_after_reboot`` returns F190, F182, F0F1 and F0F2 positive responses
    from a fresh, reconnected simulated radio. The simulator cannot establish
    real reboot, response freshness, physical links or vehicle compatibility.
    The caller must separately verify animation and ADB; F182 metadata is not
    proof of the entire installed payload.
    """
    if authorized is not True:
        raise ValueError("explicit authorization is required")
    if not all(callable(callback) for callback in (open_link, read_power_mode,
            read_voltage_mv, reconnect_finalization, release_finalization, read_after_reboot)):
        raise ValueError("all workflow callbacks are required")
    if type(adapter_max_request_length) is not int or not 20 <= adapter_max_request_length <= 0x0FFF:
        raise ValueError("adapter request limit must be between 20 and 4095 bytes")
    calibrations = validate_ltz_package(folder)  # before any link or reset
    seen_links: list[UdsClient] = []

    def open_leased_link() -> _SimulatedLinkLease:
        link = open_link()
        if not isinstance(link, UdsClient) or not callable(getattr(link, "close", None)):
            if callable(getattr(link, "close", None)):
                link.close()
            raise TransactionError("simulated link must be a closable UDS client")
        if any(link is prior for prior in seen_links):
            raise TransactionError("simulated reconnect returned a previously used link")
        seen_links.append(link)
        return _SimulatedLinkLease(link)

    def run_program(link: SimulatedLink) -> ProgramResult:
        if not isinstance(link, UdsClient):
            raise TransactionError("simulated programming requires a UDS client")
        return program(link, calibrations, trusted_manifest=LTZ_REFERENCE,
                       expected_vin=expected_vin,
                       adapter_max_request_length=adapter_max_request_length,
                       reconnect_finalization=reconnect_finalization,
                       release_finalization=release_finalization, authorized=True)

    transaction = simulate_reset_then_program(
        open_leased_link, run_program, expected_vin=expected_vin,
        read_power_mode=read_power_mode, read_voltage_mv=read_voltage_mv, authorized=True)
    f190, f182, f0f1, f0f2 = read_after_reboot()
    if f190 != b"\x62\xf1\x90" + expected_vin:
        raise TransactionError("post-reboot target identity mismatch")
    readback = compare_post_reboot(calibrations, f182, f0f1, f0f2)
    return SimulatedOutcome(transaction, readback)
