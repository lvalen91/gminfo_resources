#!/usr/bin/env python3
"""Start or maintain the owner-local GM bench radio with fixed captured schedules."""

import argparse
import contextlib
from dataclasses import dataclass
import errno
import math
import os
from pathlib import Path
import signal
import struct
import sys
import time

from bench_can_validation import BENCH_PYTHON, DEFAULT_PROFILE, DEFAULT_TOOLS, load_bench, verified_profile
from radio_owner import exclusive_owner
from replay_can_keepalive import keepalive_profile
from replay_can_power_on_keepalive import build_plan


MODES = ('full', 'startup', 'startup-keepalive', 'keepalive')
RX_MARKER = 0xFFFFFFFF
PACKET = struct.Struct('<IIBBBB8s')
KEEPALIVE_ID = 0x529
ECHO_TIMEOUT = 2.0


def summary(mode, bench, profile):
    if mode == 'full':
        return f'{len(profile.frames)} frames per {profile.period:.6f} s cycle, repeated continuously'
    if mode == 'keepalive':
        keepalive = keepalive_profile(bench, profile)
        return f'one keepalive per {keepalive.period:.6f} s until stopped'
    startup, _, keepalive = build_plan(bench, profile)
    # The old Desktop builder adds a 5 s bridge while reopening USB. The archive
    # linked by platform/can_network.md ends the startup sequence at 40 s.
    count = sum(offset < 40.0 for offset in startup.offsets)
    message = f'{count} startup frames in one 40 s window'
    if mode == 'startup-keepalive':
        message += f', followed by one keepalive per {keepalive.period:.6f} s'
    return message


def usb_modules():
    try:
        import libusb_package
        import usb.backend.libusb1
        import usb.core
        import usb.util
        from gs_usb.gs_usb import GsUsb
    except ImportError as error:
        raise RuntimeError(f'{error}. Bench interpreter: {BENCH_PYTHON}') from error
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    if backend is None:
        raise RuntimeError(f'libusb backend unavailable. Bench interpreter: {BENCH_PYTHON}')
    return usb, GsUsb, backend


def set_controller(device, mode, flags=0):
    data = struct.pack('<II', mode, flags)
    if device.ctrl_transfer(0x41, 2, 0, 0, data, timeout=1000) != len(data):
        raise OSError('short CAN controller mode transfer')


@contextlib.contextmanager
def canable(bench, modules):
    usb, adapter_class, backend = modules
    devices = list(usb.core.find(find_all=True, idVendor=0x1D50, idProduct=0x606F, backend=backend))
    if len(devices) != 1:
        raise RuntimeError(f'expected one CANable; found {len(devices)}')
    device = devices[0]
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(usb.util.dispose_resources, device)
        try:
            usb.util.claim_interface(device, 0)
        except usb.core.USBError as error:
            if error.errno == errno.EBUSY or getattr(error, 'backend_error_code', None) == -6:
                raise RuntimeError(f'CANable interface is busy; foreign owner PID unknown: {error}') from error
            raise
        cleanup.callback(usb.util.release_interface, device, 0)
        cleanup.callback(set_controller, device, 0)
        set_controller(device, 0)
        adapter = adapter_class(device)
        if device.ctrl_transfer(0x41, 0, 0, 0, struct.pack('<I', 0xBEEF), timeout=1000) != 4:
            raise OSError('short CANable host-format transfer')
        if not adapter.set_bitrate(500000):
            raise RuntimeError('CANable cannot configure 500 kbit/s')
        features = adapter.device_capability.feature
        if features & 3 != 3:
            raise RuntimeError('CANable cannot drain queued transmissions in silent loopback')
        bench.clear_stale_queue(device, features)
        timestamp_flag = features & 0x10
        # Reset normal mode before draining residual firmware TX internally.
        # The earlier reset callback also runs if either cleanup operation fails.
        cleanup.callback(bench.clear_stale_queue, device, features)
        cleanup.callback(set_controller, device, 0)
        set_controller(device, 1, timestamp_flag)
        yield device, (24 if timestamp_flag else 20), usb.core.USBTimeoutError


@dataclass
class Totals:
    queued: int = 0
    admitted: int = 0
    bus_rx: int = 0
    can_errors: int = 0
    timing_delays: int = 0
    uncertain_write: bool = False


class Stop:
    signum = 0

    def handle(self, signum, _frame):
        self.signum = signum


@contextlib.contextmanager
def stop_signals():
    stop = Stop()
    with contextlib.ExitStack() as cleanup:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous = signal.signal(signum, stop.handle)
            cleanup.callback(signal.signal, signum, previous)
        yield stop


def scheduled_events(mode, profile, startup, keepalive):
    """Yield relative deadlines and fixed captured frames for one selected mode."""
    if mode == 'full':
        cycle = 0
        while True:
            for offset, frame in zip(profile.offsets, profile.frames):
                yield cycle * profile.period + offset, frame
            cycle += 1
    elif mode == 'keepalive':
        (frame,) = keepalive.frames
        cycle = 0
        while True:
            yield cycle * keepalive.period, frame
            cycle += 1
    else:
        for offset, frame in zip(startup.offsets, startup.frames):
            if offset < 40.0:
                yield offset, frame
        if mode == 'startup-keepalive':
            (frame,) = keepalive.frames
            cycle = 0
            while True:
                yield 40.0 + cycle * keepalive.period, frame
                cycle += 1


def transmit(channel, events, owner, stop, totals):
    """Transmit a fixed schedule, admitting one USB mailbox entry at a time."""
    device, packet_size, timeout_error = channel
    origin = time.monotonic()
    events = iter(events)
    try:
        offset, frame = next(events)
    except StopIteration:
        return
    next_send = origin + offset
    expires = None
    while True:
        owner.poll()
        now = time.monotonic()
        if expires is not None and now >= expires:
            raise RuntimeError('CANable mailbox admission echo timed out')
        if expires is None:
            if stop.signum:
                return
            if now >= next_send:
                if now - next_send > .002:
                    totals.timing_delays += 1
                if totals.queued >= RX_MARKER:
                    raise RuntimeError('CANable echo identifiers exhausted')
                if not 0 <= frame.can_id <= 0x7ff or not 0 <= len(frame.data) <= 8:
                    raise ValueError('fixed schedule contains an unsupported CAN frame')
                packet = PACKET.pack(totals.queued, frame.can_id, len(frame.data),
                                     0, 0, 0, frame.data)
                if packet_size == 24:
                    packet += bytes(4)
                totals.uncertain_write = True
                if device.write(0x02, packet, timeout=100) != packet_size:
                    raise OSError('short USB CAN write; admission unknown')
                totals.uncertain_write = False
                totals.queued += 1
                expires = time.monotonic() + ECHO_TIMEOUT
        deadline = expires if expires is not None else next_send
        wait_ms = max(1, min(20, math.ceil((deadline - time.monotonic()) * 1000)))
        try:
            raw = bytes(device.read(0x81, packet_size, timeout=wait_ms))
        except timeout_error:
            continue
        if len(raw) != packet_size:
            raise RuntimeError('invalid USB receive record size')
        echo, ident, dlc, channel_id, flags, _, _ = PACKET.unpack_from(raw)
        if channel_id != 0 or dlc > 8:
            raise RuntimeError('invalid CANable channel or DLC')
        if flags & 1:
            raise RuntimeError('CANable reports receive overflow; admission accounting uncertain')
        if ident & 0x20000000:
            totals.can_errors += 1
            if ident & 0x40:
                raise RuntimeError('CAN controller entered bus-off')
            # Missing-ACK/status records are expected while a powered radio wakes.
            # They are observations, never mailbox-admission acknowledgements.
            continue
        if echo == RX_MARKER:
            totals.bus_rx += 1
        elif expires is None or echo != totals.queued - 1:
            raise RuntimeError('unexpected CANable mailbox admission echo')
        else:
            totals.admitted += 1
            expires = None
            try:
                offset, frame = next(events)
            except StopIteration:
                return
            next_send = origin + offset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=MODES, help='fixed replay mode; all modes support --dry-run')
    parser.add_argument('--dry-run', action='store_true', help='validate the fixed local profile without opening USB')
    args = parser.parse_args(argv)
    totals = Totals()
    status = 'failed'
    try:
        bench = load_bench(DEFAULT_TOOLS)
        profile = verified_profile(bench, DEFAULT_PROFILE)
        if args.dry_run:
            print(f'{args.mode}: {summary(args.mode, bench, profile)}. Dry run. Zero frames sent.')
            return 0
        startup, _, keepalive = build_plan(bench, profile)
        keepalive = keepalive_profile(bench, profile)
        modules = usb_modules()
        with exclusive_owner() as owner, stop_signals() as stop, canable(bench, modules) as channel:
            print(f'{args.mode} active at 500 kbit/s: {summary(args.mode, bench, profile)}. '
                  'Ctrl-C stops.', flush=True)
            transmit(channel, scheduled_events(args.mode, profile, startup, keepalive),
                     owner, stop, totals)
        status = 'stopped'
        return 0
    except KeyboardInterrupt:
        status = 'interrupted'
        return 130
    except (ImportError, OSError, RuntimeError, ValueError, KeyError, struct.error) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    finally:
        if not args.dry_run:
            print(f'status={status} queued={totals.queued} admitted={totals.admitted} '
                  f'pending={totals.queued - totals.admitted} uncertain_write={int(totals.uncertain_write)} '
                  f'bus_rx={totals.bus_rx} can_errors={totals.can_errors} '
                  f'timing_delays={totals.timing_delays}. '
                  'Admission is a CANable mailbox echo. ECU processing is unverified.', file=sys.stderr)


def cli():
    installed = Path(BENCH_PYTHON).expanduser()
    if ('--dry-run' not in sys.argv[1:] and Path(sys.prefix) != installed.parents[1]
            and installed.is_file()):
        os.execv(installed, [str(installed), str(Path(__file__).resolve()), *sys.argv[1:]])
    return main()


if __name__ == '__main__':
    sys.exit(cli())

