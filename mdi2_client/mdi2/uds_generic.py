"""Transport-agnostic UDS (ISO 14229) client for generic GM ECU access.

Additive and SEPARATE from the radio-specific live D-PDU path: nothing here
touches ``live_programming_transport`` / ``calibration_transaction``. One
``GenericUdsClient`` is bound to a single ECU address and talks to any transport
implementing the small ``UdsTransport`` protocol below (the MDI2 D-PDU adapter,
the optional SocketCAN/ISO-TP ``can_transport``, or a test fake).

Ported from carplay/gm_pi/gmtool/gm_uds.py; the only change is dropping the hard
``gm_transport.GMTransport`` import in favour of a duck-typed Protocol so this
module imports with no transport backend installed.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

# --------------------------------------------------------------------- timing
P2_DEFAULT = 0.10      # 100 ms (extended session)
P2_STAR_DEFAULT = 5.0  # 5 s (responsePending window)
TESTER_PRESENT_INTERVAL = 2.0  # s
MAX_PENDING_DEFAULT = 10  # cap on consecutive 0x78 responsePending cycles

# --------------------------------------------------------------------- service IDs
SID_SESSION = 0x10
SID_READ_DID = 0x22
SID_SECURITY = 0x27
SID_WRITE_DID = 0x2E
SID_ROUTINE = 0x31
SID_REQ_DOWNLOAD = 0x34
SID_TRANSFER = 0x36
SID_TRANSFER_EXIT = 0x37
SID_TESTER_PRESENT = 0x3E
NEG_RESPONSE = 0x7F

SESSION_DEFAULT = 0x01
SESSION_PROGRAMMING = 0x02
SESSION_EXTENDED = 0x03

ROUTINE_START = 0x01
ROUTINE_STOP = 0x02
ROUTINE_RESULTS = 0x03

NRC_NAMES: Dict[int, str] = {
    0x10: "generalReject", 0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported", 0x13: "incorrectMessageLengthOrInvalidFormat",
    0x14: "responseTooLong", 0x21: "busyRepeatRequest", 0x22: "conditionsNotCorrect",
    0x24: "requestSequenceError", 0x31: "requestOutOfRange", 0x33: "securityAccessDenied",
    0x35: "invalidKey", 0x36: "exceededNumberOfAttempts", 0x37: "requiredTimeDelayNotExpired",
    0x70: "uploadDownloadNotAccepted", 0x71: "transferDataSuspended",
    0x72: "generalProgrammingFailure", 0x73: "wrongBlockSequenceCounter",
    0x78: "requestCorrectlyReceived-ResponsePending",
    0x7E: "subFunctionNotSupportedInActiveSession",
    0x7F: "serviceNotSupportedInActiveSession",
}


class UdsTransport(Protocol):
    def send_uds(self, ecu_addr: int, data: bytes, timeout: Optional[float] = ...) -> Optional[bytes]: ...
    def recv(self, ecu_addr: int, timeout: float = ...) -> Optional[bytes]: ...


class UDSError(Exception):
    pass


class UDSTimeout(UDSError):
    pass


class UDSNegativeResponse(UDSError):
    def __init__(self, sid: int, nrc: int):
        self.sid = sid
        self.nrc = nrc
        super().__init__(f"NRC 0x{nrc:02X} ({NRC_NAMES.get(nrc, 'unknown')}) "
                         f"to service 0x{sid:02X}")


class UDSLockout(UDSNegativeResponse):
    """Security lockout (0x36) or time-delay-not-expired (0x37)."""


@dataclass
class SWModule:
    index: int
    part_number: str
    raw: bytes


class GenericUdsClient:
    """UDS services bound to one ECU address over a ``UdsTransport``."""

    def __init__(self, transport: UdsTransport, ecu_addr: int,
                 p2: float = P2_DEFAULT, p2_star: float = P2_STAR_DEFAULT,
                 verbose: bool = False, max_pending: int = MAX_PENDING_DEFAULT):
        self.transport = transport
        self.ecu_addr = ecu_addr
        self.p2 = p2
        self.p2_star = p2_star
        self.max_pending = max_pending
        self.verbose = verbose
        self._tp_thread: Optional[threading.Thread] = None
        self._tp_stop = threading.Event()
        # Serializes a full request/response (incl. the 0x78 recv loop) against
        # the keepalive tester-present thread so the two can't interleave ISO-TP
        # segments on the shared transport+ECU. Re-entrant: nested calls are safe.
        self._io_lock = threading.RLock()
        self.current_session = SESSION_DEFAULT
        self.security_unlocked = False

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _request(self, payload: bytes, expect_sid: Optional[int] = None,
                 timeout: Optional[float] = None,
                 suppress_response: bool = False) -> bytes:
        sid = payload[0]
        to = timeout or self.p2
        with self._io_lock:
            self._log(f"  -> {payload.hex()}")
            resp = self.transport.send_uds(self.ecu_addr, payload, timeout=to)
            if suppress_response:
                return b""
            # Bound the responsePending (0x78) loop. Each 0x78 legitimately
            # re-arms P2* at the ECU, but we must NOT loop forever: a stuck ECU
            # flooding 0x78 would otherwise hang the caller. Cap the number of
            # consecutive 0x78 cycles instead of re-arming an unbounded deadline.
            pending = 0
            while True:
                if resp is None:
                    raise UDSTimeout(f"No response to 0x{sid:02X} from 0x{self.ecu_addr:02X}")
                self._log(f"  <- {resp.hex()}")
                if resp[0] == NEG_RESPONSE:
                    nrc = resp[2] if len(resp) > 2 else 0x00
                    if nrc == 0x78:
                        pending += 1
                        if pending > self.max_pending:
                            raise UDSTimeout(
                                f"0x78 response-pending exceeded "
                                f"{self.max_pending} cycles on 0x{sid:02X}")
                        resp = self.transport.recv(self.ecu_addr, timeout=self.p2_star)
                        continue
                    if nrc in (0x36, 0x37):
                        raise UDSLockout(sid, nrc)
                    raise UDSNegativeResponse(sid, nrc)
                if expect_sid is not None and resp[0] != (expect_sid + 0x40):
                    raise UDSError(f"Unexpected response SID 0x{resp[0]:02X} "
                                   f"(wanted 0x{(expect_sid + 0x40):02X})")
                return resp

    # 0x10 session
    def change_session(self, session: int) -> bytes:
        resp = self._request(bytes([SID_SESSION, session]), expect_sid=SID_SESSION,
                             timeout=self.p2_star)
        self.current_session = session
        return resp

    def enter_extended(self) -> bytes:
        return self.change_session(SESSION_EXTENDED)

    def enter_programming(self) -> bytes:
        return self.change_session(SESSION_PROGRAMMING)

    # 0x27 security
    def request_seed(self, level: int = 0x01) -> bytes:
        resp = self._request(bytes([SID_SECURITY, level]), expect_sid=SID_SECURITY,
                             timeout=self.p2_star)
        return resp[2:]

    def send_key(self, key_response: bytes, level: int = 0x02) -> bool:
        self._request(bytes([SID_SECURITY, level]) + key_response,
                      expect_sid=SID_SECURITY, timeout=self.p2_star)
        self.security_unlocked = True
        return True

    def security_access(self, security, level: int = 0x01, max_retries: int = 2) -> bool:
        """Full seed/key flow using a ``security_cmac.GMSecurityAccess`` instance."""
        key_level = level + 1
        attempt = 0
        while True:
            attempt += 1
            seed = self.request_seed(level)
            if all(b == 0x00 for b in seed) or all(b == 0xFF for b in seed):
                self._log("  [i] Trivial seed (already open / SBI bypass)")
                self.security_unlocked = True
                return True
            try:
                resp = security.compute_response(seed)
            except KeyError:
                self._log(f"  [!] No key for ECUID {seed[:16].hex()}")
                return False
            try:
                return self.send_key(resp, key_level)
            except UDSLockout as e:
                if attempt > max_retries:
                    raise
                self._log(f"  [!] {e}; backing off before retry")
                time.sleep(10.0)
            except UDSNegativeResponse as e:
                self._log(f"  [-] Security rejected: {e}")
                return False

    # 0x22 read DID
    def read_did(self, did: int) -> bytes:
        # Use the P2* first-frame budget like the other service helpers: a slow
        # module can take longer than P2 (100 ms) to return the first frame.
        resp = self._request(bytes([SID_READ_DID, (did >> 8) & 0xFF, did & 0xFF]),
                             expect_sid=SID_READ_DID, timeout=self.p2_star)
        return resp[3:]

    def read_dids(self, dids: List[int]) -> Dict[int, Optional[bytes]]:
        out: Dict[int, Optional[bytes]] = {}
        for did in dids:
            try:
                out[did] = self.read_did(did)
            except (UDSNegativeResponse, UDSTimeout, UDSError):
                out[did] = None
        return out

    # 0x2E write DID
    def write_did(self, did: int, data: bytes) -> bytes:
        return self._request(bytes([SID_WRITE_DID, (did >> 8) & 0xFF, did & 0xFF]) + data,
                             expect_sid=SID_WRITE_DID, timeout=self.p2_star)

    # 0x31 routine
    def routine_control(self, sub: int, rid: int, data: bytes = b"") -> bytes:
        req = bytes([SID_ROUTINE, sub, (rid >> 8) & 0xFF, rid & 0xFF]) + data
        return self._request(req, expect_sid=SID_ROUTINE, timeout=self.p2_star)

    def routine_start(self, rid: int, data: bytes = b"") -> bytes:
        return self.routine_control(ROUTINE_START, rid, data)

    def routine_stop(self, rid: int, data: bytes = b"") -> bytes:
        return self.routine_control(ROUTINE_STOP, rid, data)

    def routine_results(self, rid: int) -> bytes:
        return self.routine_control(ROUTINE_RESULTS, rid)

    # 0x34/0x36/0x37 download
    def request_download(self, addr: int, size: int, addr_len: int = 4,
                         size_len: int = 4, data_format: int = 0x00) -> int:
        alfid = (size_len << 4) | addr_len
        req = bytes([SID_REQ_DOWNLOAD, data_format, alfid])
        req += addr.to_bytes(addr_len, "big") + size.to_bytes(size_len, "big")
        resp = self._request(req, expect_sid=SID_REQ_DOWNLOAD, timeout=self.p2_star)
        lfid = (resp[1] >> 4) & 0x0F
        return int.from_bytes(resp[2:2 + lfid], "big")

    def transfer_data(self, block_seq: int, data: bytes) -> bytes:
        return self._request(bytes([SID_TRANSFER, block_seq & 0xFF]) + data,
                             expect_sid=SID_TRANSFER, timeout=self.p2_star)

    def request_transfer_exit(self, data: bytes = b"") -> bytes:
        return self._request(bytes([SID_TRANSFER_EXIT]) + data,
                             expect_sid=SID_TRANSFER_EXIT, timeout=self.p2_star)

    # 0x3E tester present
    def tester_present(self) -> None:
        self._request(bytes([SID_TESTER_PRESENT, 0x80]), suppress_response=True)

    def start_tester_present(self, interval: float = TESTER_PRESENT_INTERVAL) -> None:
        if self._tp_thread and self._tp_thread.is_alive():
            return
        self._tp_stop.clear()

        def _loop():
            while not self._tp_stop.wait(interval):
                try:
                    self.tester_present()
                except Exception:
                    pass

        self._tp_thread = threading.Thread(target=_loop, daemon=True)
        self._tp_thread.start()

    def stop_tester_present(self) -> None:
        self._tp_stop.set()
        if self._tp_thread:
            self._tp_thread.join(timeout=1.0)
            self._tp_thread = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop_tester_present()


def parse_sw_inventory(data: bytes) -> List[SWModule]:
    """Parse a GM SW module inventory blob (F1A0-style): tolerant split on runs
    of printable ASCII >= 4 chars."""
    modules: List[SWModule] = []
    idx = 0
    cur = bytearray()
    for b in data:
        if 0x20 <= b <= 0x7E:
            cur.append(b)
        else:
            if len(cur) >= 4:
                modules.append(SWModule(idx, cur.decode("ascii"), bytes(cur)))
                idx += 1
            cur = bytearray()
    if len(cur) >= 4:
        modules.append(SWModule(idx, cur.decode("ascii"), bytes(cur)))
    return modules
