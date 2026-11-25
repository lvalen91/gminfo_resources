"""ELK-entry trigger ported to the shared can0 SocketCAN transport.

IO-only port of boot_radio_elk.py's CanDiagnostics (which owned the CANable via raw
libusb). Frame IDs, UDS/XCP byte sequences and the VIP-RAM gate are unchanged:

    UDS over ISO-TP: req 0x14DA80F1 / resp 0x14DAF180  (boot_radio_elk.py:45-46)
    3E 00 keepalive ; 10 03 extended ; 27 0D seed (67 0D + 31xFF) ; 27 0E +12x00 (67 0E)
    VIP gate via can0_dev XCP 0x613/0x614 at 0xFEBD0CF8 (write 1, restore)
    ELK routine: 31 01 F0 00 81 80 03 -> 71 01 F0 00 81 80 03

IMPORTANT (per platform/elk_recovery.md + boot-chain analysis): this exact CAN
F000/8180 frame is a CANDIDATE trigger - routine 8180 is absent from the VIP DCM
identifier table and direct-CAN attempts returned 7F..31; the bench-CONFIRMED ELK
entry used the native MEI/HECI route, not this CAN frame. A volatile ELK RAM image
boot (elk_raw_boot.py) is non-persistent and cannot burn a fuse; flashing can.

Modes:
    --probe       : is the ELK USB fastboot interface present? (non-destructive)
    --check       : live, NON-destructive readiness - ISO-TP 3E00/1003/read DID over
                    can0 + XCP connect + read the VIP gate word. No write, no reboot.
    --enter       : full candidate ELK entry (DESTRUCTIVE: writes the VIP gate word and
                    issues the reboot routine, then restores the word). Reboots the unit.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time

KEEPALIVE_ID = 0x529
REQ_ID = 0x14DA80F1
RESP_ID = 0x14DAF180
VIP_GATE_ADDR = 0xFEBD0CF8
ELK_USB = (0x8087, 0x09EF)
ELK_IFACE = (0xFF, 0x42, 0x03)


def _isotp_stack(iface="can0"):
    import can
    import isotp
    bus = can.interface.Bus(channel=iface, interface="socketcan")
    addr = isotp.Address(isotp.AddressingMode.Normal_29bits, txid=REQ_ID, rxid=RESP_ID)
    stack = isotp.CanStack(bus, address=addr, params={"rx_flowcontrol_timeout": 2000,
                                                      "rx_consecutive_frame_timeout": 2000,
                                                      "blocking_send": False})
    return bus, stack


def _raw_single_frame_uds(iface, req: bytes, timeout: float = 4.0):
    """Send a single-frame ISO-TP UDS request on the raw bus and read one response frame.
    Non-blocking send (bounded) so an absent/asleep bus reports quickly instead of hanging.
    Only valid for requests and responses that fit one CAN frame (<=7 UDS bytes)."""
    import errno
    import select as _sel
    import socket as _s
    import struct as _st
    fmt = _st.Struct("=IB3x8s")
    sock = _s.socket(_s.PF_CAN, _s.SOCK_RAW, _s.CAN_RAW)
    try:
        sock.setsockopt(_s.SOL_CAN_RAW, _s.CAN_RAW_FILTER, _st.Struct("=II").pack(RESP_ID, 0x1FFFFFFF))
        sock.bind((iface,))
        sf = bytes([len(req)]) + req
        try:
            sock.send(fmt.pack(REQ_ID | 0x80000000, 8, sf.ljust(8, b"\0")))
        except OSError as e:
            if e.errno == errno.ENOBUFS:
                return {"error": "no CAN ACK (bus/ECU absent or asleep)"}
            return {"error": f"send failed: {e}"}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r, _, _ = _sel.select([sock], [], [], deadline - time.monotonic())
            if not r:
                break
            raw = sock.recv(16)
            if len(raw) < 16:
                continue
            ident, dlc, data = fmt.unpack(raw)
            if (ident & 0x1FFFFFFF) == RESP_ID:
                pci = data[0] >> 4
                payload = data[1:1 + (data[0] & 0x0F)] if pci == 0 else data[:dlc]
                return {"frame": data[:dlc].hex(), "uds": payload.hex()}
        return {"error": "timeout (no response)"}
    finally:
        sock.close()


def uds(stack, payload: bytes, timeout: float = 8.0) -> bytes:
    stack.send(bytes(payload))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        stack.process()
        if stack.available():
            data = stack.recv()
            if data and data[:3] == bytes([0x7F, payload[0], 0x78]):
                continue  # responsePending
            return bytes(data)
        time.sleep(0.02)
    raise TimeoutError(f"no UDS response to {payload.hex()}")


def probe_elk() -> dict:
    """Check for the ELK fastboot USB interface (8087:09EF FF/42/03). Non-destructive."""
    try:
        import libusb_package
        import usb.backend.libusb1
        import usb.core
    except ImportError as e:
        return {"elk_present": None, "error": f"pyusb unavailable: {e}"}
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    found = []
    for dev in usb.core.find(find_all=True, idVendor=ELK_USB[0], idProduct=ELK_USB[1], backend=backend):
        for cfg in dev:
            for intf in cfg:
                sig = (intf.bInterfaceClass, intf.bInterfaceSubClass, intf.bInterfaceProtocol)
                if sig == ELK_IFACE:
                    found.append("FF/42/03 (ELK)")
                elif sig == (0xFF, 0x42, 0x01):
                    found.append("FF/42/01 (ADB)")
    return {"elk_present": any("ELK" in f for f in found), "interfaces": found,
            "note": "FF/42/03 = ELK fastboot; FF/42/01 = normal AAOS ADB (not ELK)"}


def check_transport(iface="can0") -> dict:
    """Live, NON-destructive readiness check - proves the ported can0 ELK transport works
    without writing the VIP gate or rebooting."""
    out = {"uds": {}, "vip_gate": None}
    # Single-frame UDS probes over a bounded raw socket (no isotp blocking).
    for name, req in (("3E00", b"\x3e\x00"), ("1003", b"\x10\x03")):
        out["uds"][name] = _raw_single_frame_uds(iface, req)
    # Read (not write) the VIP gate word over the 613/614 dev route.
    try:
        import can0_dev
        with can0_dev.VipDevInterface(iface) as dev:
            dev.connect()
            out["vip_gate"] = {"addr": f"{VIP_GATE_ADDR:08X}", "word": dev.read_word(VIP_GATE_ADDR).hex()}
            dev.disconnect()
    except Exception as e:  # noqa: BLE001
        out["vip_gate"] = {"error": f"{type(e).__name__}: {e}"}
    ok_uds = any(isinstance(v, dict) and "uds" in v for v in out["uds"].values())
    out["ready"] = ok_uds and isinstance(out["vip_gate"], dict) and "word" in out["vip_gate"]
    out["note"] = ("Non-destructive readiness. If ready, the candidate ELK entry is reachable; "
                   "entry itself is unproven over CAN (see module docstring).")
    return out


def enter_elk(iface="can0") -> dict:
    """DESTRUCTIVE candidate ELK entry. Writes VIP gate=1, issues the reboot routine, then
    restores the gate word in a finally. Reboots the unit into fastboot if it succeeds."""
    import can0_dev
    log, saved = [], None
    bus = stack = None
    try:
        bus, stack = _isotp_stack(iface)
        log.append("3e00 -> " + uds(stack, b"\x3e\x00").hex())
        log.append("1003 -> " + uds(stack, b"\x10\x03").hex())
        seed = uds(stack, b"\x27\x0d")
        if seed[:2] != bytes.fromhex("670d") or len(seed) != 33 or seed[2:] != b"\xff" * 31:
            raise RuntimeError(f"seed differs from verified 31-byte all-FF condition: {seed.hex()}")
        log.append("270d -> 670d + 31xFF (verified)")
        grant = uds(stack, b"\x27\x0e" + bytes(12))
        if grant != bytes.fromhex("670e"):
            raise RuntimeError(f"unexpected SecurityAccess response {grant.hex()}")
        log.append("270e+12x00 -> 670e (granted)")
        bus.shutdown(); bus = None
        with can0_dev.VipDevInterface(iface) as dev:
            dev.connect()
            saved = dev.read_word(VIP_GATE_ADDR)
            log.append(f"saved VIP gate {VIP_GATE_ADDR:08X}={saved.hex()}")
            try:
                dev.write_verify(VIP_GATE_ADDR, struct.pack("<I", 1))
                log += dev.log[-1:]
                bus2, stack2 = _isotp_stack(iface)
                try:
                    r = uds(stack2, bytes.fromhex("3101f000818003"))
                finally:
                    bus2.shutdown()
                log.append("3101 f000 818003 -> " + r.hex())
                if r != bytes.fromhex("7101f000818003"):
                    raise RuntimeError(f"ELK routine rejected: {r.hex()}")
                log.append("ELK reboot routine accepted")
            finally:
                dev.write_verify(VIP_GATE_ADDR, saved)   # guaranteed restore
                log.append("VIP gate restored")
                dev.disconnect()
        return {"ok": True, "log": log,
                "note": "Candidate CAN trigger accepted. Verify ELK with --probe; it may NOT boot "
                        "ELK over CAN (confirmed route is MEI/HECI)."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "log": log, "error": f"{type(e).__name__}: {e}"}
    finally:
        if bus is not None:
            bus.shutdown()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--enter", action="store_true")
    p.add_argument("--iface", default="can0")
    args = p.parse_args(argv)
    if args.probe:
        print(json.dumps(probe_elk()))
    elif args.check:
        print(json.dumps(check_transport(args.iface)))
    else:
        print(json.dumps(enter_elk(args.iface)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
