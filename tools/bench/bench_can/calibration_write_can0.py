#!/usr/bin/env python3
"""Calibration write over SocketCAN can0 -- the Pi-bench transport of the proven path.

This is a faithful port of tools/bench/bench_can/calibration_write_can5.py (the Mac
raw-libusb/gs_usb transport, live-verified 2026-11-25) to the Pi's SocketCAN can0
interface. It reuses, VERBATIM, every byte sequence, timing value and the three bugs
fixed on the Mac that day:
  * per-slot session-reentry bug (one open programming session for the whole package),
  * TransferData block-size off-by-two (genuine block = 0x0FFF - 2 = 4093),
  * CAN613/614 marker-pair byte-order bug (MARKER_VALUES packed little-endian).
ALL of that logic lives in calibration_write_can5.py and is imported here unchanged:
CalDiagnostics (select/read/write_word, connect/disconnect_613_614,
enter_programming_session, transfer_one, exit_programming_session, write_calibration),
write_package, verify_package, load_container, SLOT_PARTS, MARKER_VALUES,
PRECONDITION_284, PRECONDITION_20D, STEP_DELAY, VERIFIER_WORDS -- plus boot_radio_elk's
pure-logic uds()/xcp(). NONE of that is re-derived here.

ONLY the transport changes. The Mac file monkeypatches usb.core.Device.read so a single
exclusive libusb handle can be shared between a background keepalive replay and the
foreground diagnostic session. SocketCAN has no such exclusivity: any number of sockets
may bind can0 at once. So the whole USB-sharing architecture is dropped and replaced with:

  1. A replacement full-profile replay (can0_radio.transmit over a CAN_RAW socket,
     echo-confirmed exactly as the pibench keepalive service does), with the native 0x20D
     frame EXCLUDED -- byte-for-byte the Mac's `bench.replay(profile-without-20D)`.
  2. A precondition injector thread on its own socket, sending 0x284 (all-zero) and the
     MODIFIED 0x20D (byte5 bit7 set, af176db58290) every ~100 ms -- the same stream the
     Mac file injects.
  3. A Can0CalDiagnostics transport whose send()/receive()/clear() are backed by a
     CAN_RAW socket (one RX dispatch thread routing 0x614 and 0x14DAF180 into per-id
     queues, exactly boot_radio_elk's responses-dict model) instead of the USB observe().

Because the always-running pibench-can-keepalive.service already replays the UNMODIFIED
native profile (0x20D included), this script STOPS that service for the duration of the
write and ALWAYS restarts it afterwards (try/finally), so the Mac's documented
precondition environment ("all captured profile IDs replayed EXCEPT 20D; separate ~100 ms
stream supplied original 20D with b5-bit7 set") is reproduced exactly and the bus is never
left unmaintained. It holds can0_radio's schedule lock for its own replay so it cannot race
the dashboard.

CLI mirrors calibration_write_can5.py: modes test613 / write / package / verify / pec,
with --package-dir, --only, --modified. The howto in platform/can_bench_experiments.md's
"Verified procedure (2026-11-25)" section applies unchanged except for the executable name
and that there is no --profile/--tools libusb machinery to think about (SocketCAN).
"""

import argparse
import json
import queue
import select
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Pure logic + the fixed constants, imported unchanged from the Mac source of truth.
import calibration_write_can5 as cw5  # noqa: E402
from calibration_write_can5 import (  # noqa: E402
    CalDiagnostics,
    PRECONDITION_20D,
    PRECONDITION_284,
    STEP_DELAY,
    load_container,
    verify_package,
    write_package,
)

# Replay + socket building blocks, reused rather than re-derived.
import can0_radio  # noqa: E402
import radio_on  # noqa: E402
from bench_can_validation import load_bench, verified_profile  # noqa: E402
from boot_radio_elk import validate_keepalive  # noqa: E402


CAN_FRAME = struct.Struct("=IB3x8s")
CAN_EFF_FLAG = 0x80000000
CAN_ERR_FLAG = 0x20000000
CAN_EFF_MASK = 0x1FFFFFFF
NATIVE_20D = 0x20D
SERVICE = "pibench-can-keepalive.service"
DEFAULT_PROFILE = Path("/var/lib/pibench/harness-profile.json")


class Can0CalDiagnostics(CalDiagnostics):
    """CalDiagnostics with its three IO primitives (send/receive/clear) backed by a
    SocketCAN CAN_RAW socket instead of the shared libusb handle. Every higher-level
    method -- uds(), xcp(), select/read/write_word, connect_613_614,
    enter_programming_session, transfer_one, exit_programming_session -- is inherited
    unchanged from CalDiagnostics/CanDiagnostics and only ever calls these primitives.
    """

    def __init__(self, iface="can0", timeout=3.0):
        # Deliberately NOT calling CanDiagnostics.__init__ (it wants a usb module and a
        # replay keepalive). Set up only what the inherited pure logic touches.
        self.iface = iface
        self.timeout = timeout
        # Same two-queue dispatch model boot_radio_elk uses: VIP dev replies on 0x614,
        # UDS/ISO-TP responses on the extended 0x14DAF180.
        self.responses = {0x614: queue.Queue(), self.RESPONSE_ID: queue.Queue()}
        self._stop = threading.Event()
        self._sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        # No CAN_RAW_FILTER: accept every id and dispatch by masked id below, so one
        # socket serves both 0x614 (standard) and 0x14DAF180 (extended). Default behaviour
        # excludes our own TX, so 0x613 sends never alias as replies.
        self._sock.bind((iface,))
        self._rx = threading.Thread(target=self._dispatch, name="can0-cal-rx", daemon=True)
        self._rx.start()

    def _dispatch(self):
        while not self._stop.is_set():
            try:
                r, _, _ = select.select([self._sock], [], [], 0.2)
            except (OSError, ValueError):
                return
            if not r:
                continue
            try:
                raw = self._sock.recv(16)
            except OSError:
                return
            if len(raw) < CAN_FRAME.size:
                continue
            ident, dlc, data = CAN_FRAME.unpack(raw)
            if ident & CAN_ERR_FLAG:
                continue
            key = ident & CAN_EFF_MASK
            box = self.responses.get(key)
            if box is not None:
                box.put(bytes(data[:dlc]))

    def send(self, ident, payload):
        # Mirror boot_radio_elk.CanDiagnostics.send's id/DLC handling: ids above the
        # 11-bit range are extended (set the EFF flag); DLC is the real payload length
        # (precondition frames are DLC 6, UDS/XCP frames DLC 8), data padded to 8.
        can_id = ident | CAN_EFF_FLAG if ident > 0x7FF else ident
        self._sock.send(CAN_FRAME.pack(can_id, len(payload), bytes(payload).ljust(8, b"\0")))

    def receive(self, ident, timeout=3):
        try:
            return self.responses[ident].get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"No CAN response on {ident:X}") from None

    def clear(self, ident):
        box = self.responses[ident]
        while True:
            try:
                box.get_nowait()
            except queue.Empty:
                return

    def close(self):
        self._stop.set()
        self._rx.join(timeout=1)
        try:
            self._sock.close()
        except OSError:
            pass


def _systemctl(*args):
    cmd = ["sudo", "-n", "systemctl", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20)


def stop_service():
    print(f"stopping {SERVICE} (releases the can0 schedule lock)", flush=True)
    r = _systemctl("stop", SERVICE)
    if r.returncode:
        raise RuntimeError(f"could not stop {SERVICE}: {r.stderr.strip()}")


def start_service():
    r = _systemctl("start", SERVICE)
    active = _systemctl("is-active", SERVICE).stdout.strip()
    print(f"restarted {SERVICE}: is-active={active!r} (start rc={r.returncode})", flush=True)
    return active == "active"


def build_filtered_profile(bench, profile_path):
    """The verified full profile with the native 0x20D frame dropped -- exactly the Mac
    file's `kept = [... if f.can_id != 0x20D]` step. verified_profile() still validates
    the UNMODIFIED on-disk profile against the pinned digest first."""
    profile = verified_profile(bench, profile_path)
    validate_keepalive(profile)
    kept = [(f, o) for f, o in zip(profile.frames, profile.offsets) if f.can_id != NATIVE_20D]
    filtered = bench.Profile(tuple(f for f, _ in kept), tuple(o for _, o in kept),
                             profile.period, profile.cycles)
    print(f"replay profile: {len(filtered.frames)} frames "
          f"(excluded native 0x20D; injector supplies the modified version)", flush=True)
    return filtered


def run(args):
    bench = load_bench(args.tools)
    filtered = build_filtered_profile(bench, args.profile)

    totals = radio_on.Totals()
    replay_stop = radio_on.Stop()
    replay_error = {}
    replay_ready = threading.Event()
    inject_stop = threading.Event()

    def replay_worker(sock):
        try:
            # Full-mode == continuous cycling of every (offset, frame) in the profile,
            # the SocketCAN counterpart of the Mac's bench.replay(profile). Echo-confirmed
            # one frame at a time, identical to the keepalive service's own transmit.
            events = radio_on.scheduled_events("full", filtered, None, None)
            can0_radio.transmit(sock, _ready_events(events, totals, replay_ready),
                                replay_stop, totals)
        except BaseException as error:  # noqa: BLE001 -- surfaced to the main thread
            replay_error["error"] = error
            replay_ready.set()

    transport = None
    inject_sock = None
    result = {"ok": False, "error": "no result"}
    with can0_radio.schedule_lock(args.lock, "calibration-write-can0"):
        if not args.virtual:
            can0_radio.check_interface(args.iface)
        with can0_radio.drained_adapter(args.iface, totals, enabled=not args.no_drain and not args.virtual):
            replay_sock = can0_radio.open_can(args.iface)
            replay_thread = threading.Thread(target=replay_worker, args=(replay_sock,),
                                             name="can0-replay", daemon=True)
            replay_thread.start()
            try:
                if not replay_ready.wait(30):
                    raise TimeoutError("no admitted full-profile replay within 30 s")
                if "error" in replay_error:
                    raise replay_error["error"]
                print(f"replay admitted (confirmed={totals.admitted}); bus is live", flush=True)

                transport = Can0CalDiagnostics(args.iface)

                inject_sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
                inject_sock.bind((args.iface,))

                def injector():
                    while not inject_stop.is_set():
                        try:
                            inject_sock.send(CAN_FRAME.pack(0x284, len(PRECONDITION_284),
                                                            PRECONDITION_284.ljust(8, b"\0")))
                            inject_sock.send(CAN_FRAME.pack(0x20D, len(PRECONDITION_20D),
                                                            PRECONDITION_20D.ljust(8, b"\0")))
                        except OSError as error:
                            print(f"precondition injector send failed: {error}", flush=True)
                        time.sleep(0.1)

                inject_thread = threading.Thread(target=injector, name="precondition", daemon=True)
                inject_thread.start()
                # Match the Mac worker: after ready, settle 1 s before the first UDS step.
                time.sleep(1)

                result = dispatch_mode(args, transport)
            except Exception as error:  # noqa: BLE001
                result = {"ok": False, "error": f"{type(error).__name__}: {error}"}
            finally:
                inject_stop.set()
                replay_stop.signum = 15  # graceful stop for can0_radio.transmit
                if transport is not None:
                    transport.close()
                if inject_sock is not None:
                    try:
                        inject_sock.close()
                    except OSError:
                        pass
                replay_thread.join(timeout=5)
                try:
                    replay_sock.close()
                except OSError:
                    pass
                if "error" in replay_error and result.get("ok"):
                    result = {"ok": False,
                              "error": f"replay failed: {replay_error['error']}",
                              "write_result": result}
    return result


def _ready_events(events, totals, replay_ready):
    """Pass-through generator that flips replay_ready once the replay has confirmed its
    first frame on the bus (totals.admitted increments inside can0_radio.transmit)."""
    for item in events:
        if not replay_ready.is_set() and totals.admitted >= 1:
            replay_ready.set()
        yield item


def dispatch_mode(args, transport):
    if args.mode == "test613":
        transport.test_613_614()
        return {"ok": True, "mode": "test613"}
    if args.mode == "package":
        only = [s.strip().upper() for s in args.only.split(",")] if args.only else None
        return write_package(transport, args.package_dir, genuine=not args.modified, only=only)
    if args.mode == "verify":
        only = [s.strip().upper() for s in args.only.split(",")] if args.only else None
        return verify_package(transport, args.package_dir, only=only)
    if args.mode == "pec":
        time.sleep(STEP_DELAY)
        s10 = transport.uds(bytes.fromhex("1003"))
        time.sleep(STEP_DELAY)
        pec = transport.uds(bytes.fromhex("22f0f1"))
        time.sleep(STEP_DELAY)
        f181 = transport.uds(bytes.fromhex("22f181"))
        return {"ok": True, "10 03": s10.hex(), "22 F0F1": pec.hex(), "22 F181": f181.hex()}
    data = load_container(args.container)
    return transport.write_calibration(args.slot, data, genuine=not args.modified)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("test613", "write", "package", "verify", "pec"))
    parser.add_argument("--package-dir", type=Path, help="directory of part-number-named containers")
    parser.add_argument("--only", help="comma-separated hex slots to (re)attempt, e.g. 03,04,05")
    parser.add_argument("--slot", help="hex slot id, e.g. 02 (write mode)")
    parser.add_argument("--container", type=Path, help="path to the container file to write (write mode)")
    parser.add_argument("--modified", action="store_true",
                        help="container is a modified/custom one -- use the VIP 0x613/0x614 "
                             "development-memory diagnostic interface to set the header-verifier "
                             "words first. Default (genuine/stock) skips it entirely.")
    parser.add_argument("--iface", default="can0")
    parser.add_argument("--virtual", action="store_true",
                        help="test only: allow a vcan interface and skip the bit-timing check")
    parser.add_argument("--no-drain", action="store_true",
                        help="skip the initial/exit adapter queue drain (interface already healthy)")
    parser.add_argument("--tools", type=Path, default=can0_radio.default_tools())
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--lock", type=Path, default=can0_radio.DEFAULT_LOCK)
    parser.add_argument("--keep-service", action="store_true",
                        help="do not stop/restart the keepalive service (caller manages it)")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if args.iface != "can0" and not (args.virtual and args.iface.startswith("vcan")):
        parser.error("only can0 is a live transport; vcan* requires --virtual")

    manage = not args.keep_service and not args.virtual
    stopped = False
    try:
        if manage:
            stop_service()
            stopped = True
        result = run(args)
    except Exception as error:  # noqa: BLE001
        result = {"ok": False, "error": f"{type(error).__name__}: {error}"}
    finally:
        if manage and stopped:
            # finally-equivalent service restoration: success, failure, or exception.
            if not start_service():
                print("!!! WARNING: keepalive service is NOT active after restart", flush=True)

    print(json.dumps(result, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
