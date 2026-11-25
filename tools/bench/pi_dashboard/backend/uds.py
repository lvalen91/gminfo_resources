"""diagnosticsd UDS-over-TCP client for the bench dashboard.

Transport is the bench's own custom GM framing (diagnostics/diagnosticsd_protocol.md
:39-58), NOT DoIP / NOT ISO-TP:

    request  = [SRC:2 BE][TGT:2 BE][LEN:4 BE] + <UDS payload incl. SID>
    response = [SRC:2 BE][TGT:2 BE][LEN:4 BE] + <UDS payload>
    positive = (reqSID | 0x40) ...        negative = 7F <reqSID> <NRC>
    NRC 0x78 (responsePending) => keep reading until the final frame.

Every byte sent here is a documented, bench-observed UDS service on the owner's own
licensed bench ECU. The dashboard surfaces reads freely; it gates writes/routines
behind an explicit confirmation and a dry-run default (see routines.py / app.py).
"""
from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass, field

from . import config

HEADER = struct.Struct(">HHI")
NRC_RESPONSE_PENDING = 0x78
NRC_NAMES = {
    0x11: "serviceNotSupported", 0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat", 0x22: "conditionsNotCorrect",
    0x25: "noResponseFromSubnetComponent", 0x31: "requestOutOfRange",
    0x33: "securityAccessDenied", 0x35: "invalidKey", 0x36: "exceededNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired", 0x72: "generalProgrammingFailure",
    0x78: "responsePending", 0x7E: "subFunctionNotSupportedInActiveSession",
    0x7F: "serviceNotSupportedInActiveSession",
}


class UDSError(Exception):
    pass


class NegativeResponse(UDSError):
    def __init__(self, sid: int, nrc: int):
        self.sid, self.nrc = sid, nrc
        name = NRC_NAMES.get(nrc, "unknown")
        super().__init__(f"7F {sid:02X} {nrc:02X} ({name})")


@dataclass
class UDSResult:
    request: bytes
    response: bytes
    ok: bool
    nrc: int | None = None
    elapsed_ms: float = 0.0

    def as_dict(self) -> dict:
        d = {
            "request_hex": self.request.hex(),
            "response_hex": self.response.hex(),
            "ok": self.ok,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }
        if self.nrc is not None:
            d["nrc"] = f"{self.nrc:02X}"
            d["nrc_name"] = NRC_NAMES.get(self.nrc, "unknown")
        return d


@dataclass
class UDSClient:
    """One TCP connection = one UDS session. Session resets to default on reconnect,
    so callers re-enter extended session after connecting (diagnosticsd_protocol.md:286)."""
    host: str = config.DIAG_HOST
    port: int = config.DIAG_PORT
    src_bind: str = config.DIAG_SRC_BIND
    tester: int = config.UDS_TESTER
    ecu: int = config.UDS_ECU
    timeout: float = 5.0
    _sock: socket.socket | None = field(default=None, repr=False)

    def connect(self) -> None:
        self.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            if self.src_bind:
                s.bind((self.src_bind, 0))
            s.connect((self.host, self.port))
        except OSError as e:
            s.close()
            raise UDSError(f"cannot reach diagnosticsd at {self.host}:{self.port} "
                           f"from {self.src_bind or 'default'}: {e}") from e
        self._sock = s

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _recv_frame(self) -> bytes:
        assert self._sock is not None
        hdr = b""
        while len(hdr) < 8:
            chunk = self._sock.recv(8 - len(hdr))
            if not chunk:
                raise UDSError("diagnosticsd closed the connection")
            hdr += chunk
        _src, _tgt, length = HEADER.unpack(hdr)
        body = b""
        while len(body) < length:
            chunk = self._sock.recv(length - len(body))
            if not chunk:
                raise UDSError("diagnosticsd truncated a response frame")
            body += chunk
        return body

    def request(self, payload: bytes, raise_on_negative: bool = False,
                pending_deadline: float = 20.0) -> UDSResult:
        """Send one UDS request, walk past any 7F..78 pending frames, return the final."""
        if self._sock is None:
            self.connect()
        assert self._sock is not None
        start = time.monotonic()
        self._sock.sendall(HEADER.pack(self.tester, self.ecu, len(payload)) + payload)
        deadline = start + pending_deadline
        while True:
            body = self._recv_frame()
            if len(body) >= 3 and body[0] == 0x7F and body[2] == NRC_RESPONSE_PENDING:
                if time.monotonic() > deadline:
                    raise UDSError("responsePending never resolved")
                continue
            elapsed = (time.monotonic() - start) * 1000
            if len(body) >= 3 and body[0] == 0x7F:
                nrc = body[2]
                if raise_on_negative:
                    raise NegativeResponse(body[1], nrc)
                return UDSResult(payload, body, ok=False, nrc=nrc, elapsed_ms=elapsed)
            return UDSResult(payload, body, ok=True, elapsed_ms=elapsed)

    # --- high-level helpers -----------------------------------------------------
    def session(self, sub: int) -> UDSResult:
        return self.request(bytes([0x10, sub]))

    def tester_present(self) -> UDSResult:
        return self.request(b"\x3E\x00")

    def read_did(self, did: int) -> UDSResult:
        return self.request(bytes([0x22, (did >> 8) & 0xFF, did & 0xFF]))

    def read_dtc(self, sub: int = 0x02, mask: int = 0xFF) -> UDSResult:
        return self.request(bytes([0x19, sub, mask]))

    def security_request_seed(self, level: int) -> UDSResult:
        return self.request(bytes([0x27, level]))

    def security_send_key(self, level: int, key: bytes) -> UDSResult:
        return self.request(bytes([0x27, level]) + key)

    def routine(self, control: int, rid: int, params: bytes = b"") -> UDSResult:
        return self.request(bytes([0x31, control, (rid >> 8) & 0xFF, rid & 0xFF]) + params)


def build_request(tester: int, ecu: int, payload: bytes) -> bytes:
    """Return the exact on-wire bytes for a request (used by dry-run / introspection)."""
    return HEADER.pack(tester, ecu, len(payload)) + payload
