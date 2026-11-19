#!/usr/bin/env python3
"""Enter Intel ELK from AAOS while continuously replaying the captured CAN sequence.

Run with ~/.local/share/gminfo-bench/venv/bin/python ~/Desktop/boot_radio_elk.py
Requires the existing gminfo_resources checkout and local harness profile.
The CANable must be free. Ctrl-C stops after any VIP RAM restoration completes.
"""

import argparse
import importlib.util
import math
from pathlib import Path
import queue
import signal
import struct
import sys
import threading
import time


class StopReplay(BaseException):
    """Exit the replay loop through its adapter cleanup handlers."""


KEEPALIVE_ID = 0x529
DOCUMENTED_PERIOD = 0.320270
PERIOD_TOLERANCE = 0.005


def validate_keepalive(profile):
    """Require the captured post-boot keepalive and its documented cadence."""
    frames = [frame for frame in profile.frames if frame.can_id == KEEPALIVE_ID]
    if len(frames) != 1:
        raise ValueError('profile must contain exactly one captured 0x529 keepalive frame')
    if (not math.isfinite(profile.period)
            or not math.isclose(profile.period, DOCUMENTED_PERIOD,
                                rel_tol=0, abs_tol=PERIOD_TOLERANCE)):
        raise ValueError(
            f'profile period {profile.period!r} differs from documented '
            f'{DOCUMENTED_PERIOD:.6f}s keepalive cadence')
    return frames[0]


class CanDiagnostics:
    REQUEST_ID = 0x14DA80F1
    RESPONSE_ID = 0x14DAF180
    SECURITY_ADDRESS = 0xFEBD0CF8

    def __init__(self, usb, stop_requested, finished, keepalive_period):
        self.usb = usb
        self.stop_requested = stop_requested
        self.finished = finished
        self.keepalive_period = keepalive_period
        self.ready = threading.Event()
        self.responses = {0x614: queue.Queue(), self.RESPONSE_ID: queue.Queue()}
        self.device = None
        self.timestamp = False
        self.restoring = False
        self.original_read = usb.core.Device.read

    def observe(self, device, endpoint, size, *args, **kwargs):
        if self.stop_requested.is_set() and self.finished.is_set():
            raise StopReplay()
        raw = self.original_read(device, endpoint, size, *args, **kwargs)
        if endpoint == 0x81 and len(raw) in (20, 24):
            echo, ident, length = struct.unpack('<IIB', bytes(raw[:9]))
            self.device = device
            self.timestamp = len(raw) == 24
            # Error records and unrelated replay echoes can arrive while the VIP
            # is asleep. Require admission of the standard 0x529 data frame.
            # Extended/error/RTR flag bits must not alias their low 29-bit ID.
            if echo < 0x70000000 and ident == KEEPALIVE_ID:
                if not self.ready.is_set():
                    print(f'Captured 0x529 keepalive active every '
                          f'{self.keepalive_period * 1000:.3f} ms', flush=True)
                self.ready.set()
            if not ident & 0x20000000 and echo == 0xFFFFFFFF:
                ident &= 0x1FFFFFFF
                if ident in self.responses:
                    self.responses[ident].put(bytes(raw[12:12 + length]))
        return raw

    def send(self, ident, payload):
        if self.stop_requested.is_set() and not self.restoring:
            raise RuntimeError('Stop requested')
        if ident > 0x7FF:
            ident |= 0x80000000
        raw = struct.pack('<IIBBBB8s', 0x70000000, ident, len(payload),
                          0, 0, 0, payload)
        if self.timestamp:
            raw += bytes(4)
        self.device.write(2, raw, timeout=100)

    def clear(self, ident):
        while True:
            try:
                self.responses[ident].get_nowait()
            except queue.Empty:
                return

    def receive(self, ident, timeout=3):
        try:
            return self.responses[ident].get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f'No CAN response on {ident:X}') from None

    def uds(self, payload):
        self.clear(self.RESPONSE_ID)
        if len(payload) <= 7:
            self.send(self.REQUEST_ID,
                      (bytes([len(payload)]) + payload).ljust(8, b'\0'))
        else:
            self.send(self.REQUEST_ID,
                      bytes([0x10 | (len(payload) >> 8), len(payload) & 255])
                      + payload[:6])
            flow = self.receive(self.RESPONSE_ID)
            if len(flow) < 3 or flow[0] != 0x30:
                raise RuntimeError('Unexpected ISO-TP flow control')
            count = (len(payload) - 6 + 6) // 7
            if flow[1] and flow[1] < count:
                raise RuntimeError('Unexpected ISO-TP block size')
            if flow[2] <= 127:
                delay = flow[2] / 1000
            elif 0xF1 <= flow[2] <= 0xF9:
                delay = (flow[2] - 0xF0) / 10000
            else:
                raise RuntimeError('Reserved ISO-TP separation time')
            for index, offset in enumerate(range(6, len(payload), 7), 1):
                time.sleep(max(delay, 0.001))
                self.send(self.REQUEST_ID,
                          (bytes([0x20 | (index & 15)])
                           + payload[offset:offset + 7]).ljust(8, b'\0'))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            data = self.receive(self.RESPONSE_ID)
            if not data:
                raise RuntimeError('Empty ISO-TP frame')
            kind = data[0] >> 4
            if kind == 0:
                length = data[0] & 15
                if not 1 <= length <= len(data) - 1:
                    raise RuntimeError('Invalid ISO-TP single-frame length')
                result = data[1:1 + length]
            elif kind == 1 and len(data) >= 2:
                length = ((data[0] & 15) << 8) | data[1]
                if not 8 <= length <= 4095:
                    raise RuntimeError('Invalid ISO-TP multi-frame length')
                result = data[2:]
                self.send(self.REQUEST_ID, bytes.fromhex('3000000000000000'))
                sequence = 1
                while len(result) < length:
                    fragment = self.receive(self.RESPONSE_ID)
                    if len(fragment) < 2 or fragment[0] != (0x20 | (sequence & 15)):
                        raise RuntimeError('ISO-TP sequence mismatch')
                    result += fragment[1:]
                    sequence += 1
                result = result[:length]
            else:
                raise RuntimeError('Unexpected ISO-TP response')
            if result[:3] == bytes([0x7F, payload[0], 0x78]):
                continue
            display = result.hex()
            if payload[0] == 0x27:
                display = f'{result[:2].hex()} length={len(result)}'
            print(f'UDS {payload[:2].hex()} response {display}', flush=True)
            if result[0] != payload[0] + 0x40:
                raise RuntimeError('UDS request rejected ' + result.hex())
            return result
        raise TimeoutError('UDS pending-response deadline exceeded')

    def xcp(self, payload):
        self.clear(0x614)
        self.send(0x613, payload.ljust(8, b'\0'))
        response = self.receive(0x614)
        if not response or response[0] != 0xFF:
            raise RuntimeError('XCP rejected ' + response.hex())
        return response

    def select_word(self):
        self.xcp(bytes.fromhex('f6000000')
                 + struct.pack('<I', self.SECURITY_ADDRESS))

    def read_word(self):
        self.select_word()
        response = self.xcp(bytes.fromhex('f504'))
        if len(response) < 5:
            raise RuntimeError('Short XCP memory read')
        return response[1:5]

    def write_word(self, value):
        self.select_word()
        self.xcp(bytes.fromhex('f004') + value)

    def enter_elk(self):
        saved = None
        changed = False
        try:
            if not self.ready.wait(30):
                raise TimeoutError('No admitted 0x529 keepalive replay within 30 seconds')
            time.sleep(1)
            deadline = time.monotonic() + 30
            while True:
                try:
                    self.uds(bytes.fromhex('3e00'))
                    break
                except TimeoutError:
                    if time.monotonic() >= deadline or self.stop_requested.is_set():
                        raise
                    time.sleep(1)
            self.uds(bytes.fromhex('1003'))
            seed = self.uds(bytes.fromhex('270d'))
            if seed[:2] != bytes.fromhex('670d') or len(seed) != 33 or seed[2:] != b'\xff' * 31:
                raise RuntimeError('Seed differs from verified 31-byte all-FF condition')
            if self.uds(bytes.fromhex('270e') + bytes(12)) != bytes.fromhex('670e'):
                raise RuntimeError('Unexpected SecurityAccess response')
            self.xcp(bytes.fromhex('ff00'))
            saved = self.read_word()
            print('Original VIP word saved in memory', flush=True)
            changed = True
            self.write_word(struct.pack('<I', 1))
            if self.read_word() != struct.pack('<I', 1):
                raise RuntimeError('Temporary VIP word readback mismatch')
            result = self.uds(bytes.fromhex('3101f000818003'))
            if result != bytes.fromhex('7101f000818003'):
                raise RuntimeError('Unexpected ELK routine response ' + result.hex())
            print('ELK reboot request accepted', flush=True)
        finally:
            self.restoring = True
            try:
                if changed:
                    self.write_word(saved)
                    if self.read_word() != saved:
                        raise RuntimeError('VIP word restoration readback mismatch')
                    print('Original VIP word restored and verified', flush=True)
            finally:
                if saved is not None:
                    try:
                        self.xcp(bytes.fromhex('fe'))
                    except Exception as error:
                        print(f'XCP disconnect failed: {error}', flush=True)
                self.restoring = False


def verify_elk(usb, backend, timeout):
    deadline = time.monotonic() + timeout
    last_error = 'ELK interface FF/42/03 absent'
    while time.monotonic() < deadline:
        for device in usb.core.find(find_all=True, idVendor=0x8087,
                                    idProduct=0x09EF, backend=backend):
            interface = None
            claimed = False
            try:
                interface = next((i for c in device for i in c
                                  if (i.bInterfaceClass, i.bInterfaceSubClass,
                                      i.bInterfaceProtocol) == (255, 66, 3)), None)
                if interface is None:
                    continue
                usb.util.claim_interface(device, interface.bInterfaceNumber)
                claimed = True
                tx = next(e for e in interface if not e.bEndpointAddress & 0x80)
                rx = next(e for e in interface if e.bEndpointAddress & 0x80)
                tx.write(b'getvar:version-bootloader', timeout=3000)
                for _ in range(8):
                    reply = bytes(rx.read(1024, timeout=3000)).rstrip(b'\0')
                    if reply.startswith(b'OKAYkernelflinger-'):
                        print('ELK verified: ' + reply.decode('ascii'), flush=True)
                        return
                    if reply.startswith((b'FAIL', b'OKAY')):
                        raise RuntimeError('Unexpected bootloader response ' + repr(reply))
            except (usb.core.USBError, RuntimeError, StopIteration) as error:
                last_error = str(error)
            finally:
                if claimed:
                    usb.util.release_interface(device, interface.bInterfaceNumber)
                usb.util.dispose_resources(device)
        time.sleep(1)
    raise TimeoutError(last_error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', type=Path, default=Path.home() /
                        'Downloads/github/gminfo_resources/research/tools')
    parser.add_argument('--profile', type=Path, default=Path.home() /
                        '.local/share/gminfo-bench/harness-profile.json')
    args = parser.parse_args()
    import usb.core
    import usb.util
    import usb.backend.libusb1
    import libusb_package

    spec = importlib.util.spec_from_file_location('can_bench_emulator',
                                                args.tools / 'can_bench_emulator.py')
    bench = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bench
    spec.loader.exec_module(bench)
    profile = bench.load_profile(args.profile)
    validate_keepalive(profile)
    stop_requested = threading.Event()
    finished = threading.Event()
    transport = CanDiagnostics(usb, stop_requested, finished, profile.period)
    failures = []
    original_find = usb.core.find

    def stop(signum, stack):
        stop_requested.set()

    def diagnostic():
        try:
            transport.enter_elk()
            backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
            verify_elk(usb, backend, 45)
        except Exception as error:
            failures.append(error)
            print(f'ELK PROCEDURE FAILED: {type(error).__name__}: {error}', flush=True)
        finally:
            print('Keepalive continues until Ctrl-C', flush=True)
            finished.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    # One USB reader owns the CANable. Diagnostic replies are routed from the
    # existing replay loop, preserving its keepalive timing and recovery logic.
    def observed_read(device, endpoint, size, *args, **kwargs):
        if device.idVendor == 0x1D50 and device.idProduct == 0x606F:
            return transport.observe(device, endpoint, size, *args, **kwargs)
        return transport.original_read(device, endpoint, size, *args, **kwargs)

    def observed_find(*args, **kwargs):
        # Permit shutdown while the replay loop is retrying an absent adapter.
        if (kwargs.get('idVendor') == 0x1D50
                and stop_requested.is_set() and finished.is_set()):
            raise StopReplay()
        return original_find(*args, **kwargs)

    usb.core.Device.read = observed_read
    usb.core.find = observed_find
    worker = threading.Thread(target=diagnostic)
    worker.start()
    try:
        bench.replay(profile, status_interval=60)
    except StopReplay:
        pass
    finally:
        stop_requested.set()
        worker.join()
        usb.core.Device.read = transport.original_read
        usb.core.find = original_find
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())

