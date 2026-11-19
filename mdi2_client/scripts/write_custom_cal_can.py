#!/usr/bin/env python3
"""Write one pre-built CSM container through the verified isolated CAN bench path.

This runner is intentionally limited to the documented A11 bench ECU (0x80).
It is *not* a general-purpose calibration writer: it refuses non-CSM input,
does not calculate or forge signatures, and defaults to an offline plan.  A
live run requires both ``--apply`` and the acknowledgement phrase below.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from mdi2.calibration_payloads import Calibration, transfer_requests
from mdi2.can_transport import CANTransport
from mdi2.uds_generic import GenericUdsClient, UDSError
from mdi2.vip_dev_memory import VipDevMemory, WordPair

ECU = 0x80
VERIFIER_A = 0xFEBF0BF8
VERIFIER_B = 0xFEBF0BFC
MARKER_A = bytes.fromhex("293816A5")
MARKER_B = bytes.fromhex("D6C7E95A")
ACK = "OWNED-BENCH-CUSTOM-CAL"


def load_container(path: Path) -> Calibration:
    data = path.read_bytes()
    if len(data) < 0x36B or data[6:10] != b"CSM\0" or data[0x368:0x36B] != b"\x1f\x8b\x08":
        raise ValueError("input is not a raw CSM calibration container")
    slot = data[3]
    if not 2 <= slot <= 15:
        raise ValueError(f"invalid CSM slot 0x{slot:02X}")
    return Calibration(slot=slot, part=path.name, container=data)


def _uds(client: GenericUdsClient, request: bytes, prefix: bytes) -> bytes:
    # GenericUdsClient deliberately keeps its primitive private; the runner
    # needs exact historical request bytes and validates only their prefix.
    reply = client._request(request, expect_sid=request[0], timeout=client.p2_star)
    if not reply.startswith(prefix):
        raise UDSError(f"unexpected reply {reply.hex()} to {request.hex()}")
    return reply


def prepare(client: GenericUdsClient) -> None:
    _uds(client, b"\x10\x03", b"\x50\x03")
    _uds(client, b"\x85\x02", b"\xc5\x02")
    _uds(client, b"\x28\x03\x01", b"\x68\x03")
    seed = _uds(client, b"\x27\x01", b"\x67\x01")[2:]
    if not seed or not all(value == 0xFF for value in seed):
        raise UDSError("refusing non-degenerate SecurityAccess seed; no key is accepted by this runner")
    _uds(client, b"\x31\x01\xff\x01", b"\x71\x01\xff\x01")
    _uds(client, b"\x31\x01\x02\x1e", b"\x71\x01\x02\x1e")
    _uds(client, b"\x10\x02", b"\x50\x02")


def transfer(client: GenericUdsClient, calibration: Calibration) -> None:
    first = next(transfer_requests(calibration, 0x0FFF))
    reply = _uds(client, first, b"\x74")
    if len(reply) < 4 or int.from_bytes(reply[2:4], "big") < 3:
        raise UDSError("invalid RequestDownload maximum block length")
    maximum = int.from_bytes(reply[2:4], "big")
    requests = transfer_requests(calibration, maximum)
    next(requests)
    for request in requests:
        prefix = b"\x76" + request[1:2] if request[0] == 0x36 else b"\x77"
        _uds(client, request, prefix)
    _uds(client, b"\x22\xf0\xf1", b"\x62\xf0\xf1\x00\x00")


def apply(interface: str, calibration: Calibration) -> None:
    transport = CANTransport(interface)
    if not transport.connect():
        raise RuntimeError(f"cannot open SocketCAN interface {interface}")
    saved: WordPair | None = None
    try:
        uds = GenericUdsClient(transport, ECU, verbose=True)
        prepare(uds)
        dev = VipDevMemory(transport.bus)
        dev.connect()
        saved = dev.read_word_pair(VERIFIER_A, VERIFIER_B)
        dev.write(VERIFIER_A, MARKER_A)
        dev.write(VERIFIER_B, MARKER_B)
        if dev.read(VERIFIER_A, 4) != MARKER_A or dev.read(VERIFIER_B, 4) != MARKER_B:
            raise RuntimeError("verifier-word write readback mismatch")
        transfer(uds, calibration)
    finally:
        if saved is not None:
            dev.restore_word_pair(saved)
        transport.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("container", type=Path, help="one raw, hand-edited CSM container")
    parser.add_argument("--can-interface", default="can0")
    parser.add_argument("--apply", action="store_true", help="open CAN and perform the write")
    parser.add_argument("--ack", help=f"required with --apply: {ACK}")
    args = parser.parse_args(argv)
    calibration = load_container(args.container)
    print(f"slot=0x{calibration.slot:02X} bytes={len(calibration.container)}")
    if not args.apply:
        print("offline plan only; pass --apply and the acknowledgement phrase to transmit")
        return 0
    if args.ack != ACK:
        parser.error("--apply requires the exact owned-bench acknowledgement")
    apply(args.can_interface, calibration)
    print("transfer accepted and original verifier words restored/read back")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
