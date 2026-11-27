"""Raw ISO-TP UDS on CAN5 (can0) to the VIP, ECU 0x80 -- independent of the T1/diagnosticsd
transport in uds.py.

Addressing (GMLAN extended 29-bit, bench-confirmed, diagnostics/GM_CAN_UDS_REFERENCE.md
sec 13a; same as tools/bench/bench_can/boot_radio_elk.py's CanDiagnostics): request
0x14DA80F1, response 0x14DAF180. Only single-frame requests/responses (<= 7 payload
bytes) are handled -- every request this module sends fits one frame.

ECUReset evidence (2026-11-27, live bench, platform/can_bench_experiments.md "ECUReset
11 01 over raw CAN5"):
  default session:  02 11 01 -> 03 7F 11 7F (serviceNotSupportedInActiveSession), no reset
  extended session: 02 10 03 -> 06 50 03 00 64 01 F4; then 02 11 01 -> 02 51 01, and the
  VIP UART tick restarted at [000119] with the application banner and
  "BRR_RESET_REASON_VIP_SOFTWARE updated to 109".

The keepalive schedule is deliberately left running: these frames use their own IDs, and
the VIP needs the keepalive to stay awake after it reboots.
"""
from __future__ import annotations

import socket
import struct
import time

from . import config
from .uds import NRC_NAMES

REQ_ID = 0x14DA80F1
RESP_ID = 0x14DAF180
_FRAME = struct.Struct("=IB3x8s")
_PAD = 0x00
_P2_STAR_S = 5.0   # from the 50 03 response: P2*max = 0x01F4 * 10 ms


def _open() -> socket.socket:
    s = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    s.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER,
                 struct.pack("=II", RESP_ID | socket.CAN_EFF_FLAG,
                             socket.CAN_EFF_MASK | socket.CAN_EFF_FLAG))
    s.bind((config.CAN_IFACE,))
    return s


def _exchange(s: socket.socket, payload: bytes, timeout_s: float = 1.0) -> dict:
    """Send one single-frame request; return the first final (non-0x78) response."""
    if not 1 <= len(payload) <= 7:
        raise ValueError("single-frame payload must be 1..7 bytes")
    data = (bytes([len(payload)]) + payload).ljust(8, bytes([_PAD]))
    s.send(_FRAME.pack(REQ_ID | socket.CAN_EFF_FLAG, 8, data))
    out = {"request_hex": payload.hex(" ").upper(), "frame_hex": data.hex(" ").upper()}
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            out.update(ok=False, response_hex=None, error=f"no response from {RESP_ID:08X} within {timeout_s}s")
            return out
        s.settimeout(remaining)
        try:
            _, dlc, raw = _FRAME.unpack(s.recv(_FRAME.size))
        except socket.timeout:
            continue
        n = raw[0]
        if n > 7 or n == 0:
            out.update(ok=False, response_hex=raw[:dlc].hex(" ").upper(),
                       error="not a single-frame ISO-TP response")
            return out
        resp = raw[1:1 + n]
        if len(resp) == 3 and resp[0] == 0x7F and resp[2] == 0x78:
            deadline = time.monotonic() + _P2_STAR_S   # responsePending: wait P2*
            continue
        out["response_hex"] = resp.hex(" ").upper()
        if resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else None
            out.update(ok=False, nrc=f"{nrc:02X}" if nrc is not None else None,
                       nrc_name=NRC_NAMES.get(nrc, "unknown") if nrc is not None else None)
        else:
            out["ok"] = resp[0] == payload[0] + 0x40
        return out


def ecu_reset_hard() -> dict:
    """Blocking: extended session (10 03) then ECUReset hardReset (11 01) to ECU 0x80."""
    with _open() as s:
        steps = {"extended_session": _exchange(s, b"\x10\x03")}
        if not steps["extended_session"]["ok"]:
            return {"ok": False, "steps": steps, "error": "extended session refused; reset not sent"}
        time.sleep(0.05)
        steps["ecu_reset"] = _exchange(s, b"\x11\x01")
    return {"ok": steps["ecu_reset"]["ok"], "steps": steps,
            "transport": f"raw ISO-TP on {config.CAN_IFACE}, {REQ_ID:08X} -> {RESP_ID:08X}"}
