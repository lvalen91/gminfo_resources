#!/usr/bin/env python3
"""Inspect an isolated harness capture or replay its fixed cyclic CAN sequence.

No payloads or private device identifiers are embedded in this tool. Replay is
for a powered bench radio with the original harness MCU disconnected from CAN.
Inspection never opens the USB adapter. Replay requires exclusive adapter access.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path
import signal
import statistics
import struct
import sys
import time

DEFAULT_PROFILE = Path.home() / '.local/share/gminfo-bench/harness-profile.json'


@dataclass(frozen=True)
class Frame:
    host_ns: int
    device_us: int
    can_id: int
    data: bytes


@dataclass(frozen=True)
class Profile:
    frames: tuple[Frame, ...]
    offsets: tuple[float, ...]
    period: float
    cycles: int


def load_capture(path):
    """Read only complete records present at open; tolerate a live final fragment."""
    frames = []
    events = Counter()
    with Path(path).open('rb') as source:
        limit = source.seek(0, 2)
        source.seek(0)
        while source.tell() < limit:
            remaining = limit - source.tell()
            line = source.readline(min(remaining, 65537))
            if len(line) > 65536:
                raise ValueError('capture record exceeds 64 KiB')
            if not line.endswith(b'\n'):
                break
            record = json.loads(line)
            if 'can_id_raw' not in record:
                events[record.get('event', 'other')] += 1
                continue
            raw = bytes.fromhex(record['usb_frame_hex'])
            if len(raw) not in (20, 24):
                raise ValueError('unsupported gs_usb frame length')
            echo, ident, dlc, channel, flags, reserved = struct.unpack('<IIBBBB', raw[:12])
            if (ident, dlc, channel, flags, echo) != (
                record['can_id_raw'], record['dlc'], record['channel'],
                record['flags'], record['echo_id'],
            ):
                raise ValueError('capture fields disagree with raw USB frame')
            if flags & 1:
                events['overflow'] += 1
            if echo != 0xFFFFFFFF:
                events['tx_echo'] += 1
                continue
            if ident & 0x20000000:
                events['can_error'] += 1
                continue
            if channel or ident & ~0x7FF or dlc > 8:
                raise ValueError('profile requires channel-0 classic 11-bit data frames')
            frames.append(Frame(record['host_time_ns'], record['hardware_time_us'], ident, raw[12:12 + dlc]))
    return frames, events


def derive_profile(frames):
    if not frames:
        raise ValueError('capture has no received data frames')
    # A new power-on may follow a long quiet interval; use the latest segment.
    start = 0
    for index in range(1, len(frames)):
        gap = frames[index].host_ns - frames[index - 1].host_ns
        if gap < 0:
            raise ValueError('host timestamps moved backwards')
        if gap > 500_000_000:
            start = index
    segment = frames[start:]
    payloads = defaultdict(set)
    order = []
    for frame in segment:
        if frame.can_id not in payloads:
            order.append(frame.can_id)
        payloads[frame.can_id].add(frame.data)
    if any(len(values) != 1 for values in payloads.values()):
        raise ValueError('payloads vary; fixed-pattern replay is not justified')
    size = len(order)
    # Ignore the first two cycles, which may include retries during receiver startup.
    tail = segment[2 * size:]
    if len(tail) < 3 * size:
        raise ValueError('need at least five cycles in the latest powered segment')
    anchor = order[0]
    indexes = [i for i, frame in enumerate(tail) if frame.can_id == anchor]
    cycles = [tail[a:b] for a, b in zip(indexes, indexes[1:])]
    expected = tuple(order)
    if not cycles or any(tuple(frame.can_id for frame in cycle) != expected for cycle in cycles):
        raise ValueError('frame order is not a repeating fixed cycle')
    starts = [tail[index].device_us for index in indexes]
    periods = [((b - a) % 2**32) / 1e6 for a, b in zip(starts, starts[1:])]
    period = statistics.median(periods)
    if not 0.001 <= period <= 10 or any(abs(value - period) > period * 0.05 for value in periods):
        raise ValueError('cycle timing is unstable or unsupported')
    offsets = tuple(statistics.median(
        ((cycle[index].device_us - cycle[0].device_us) % 2**32) / 1e6
        for cycle in cycles
    ) for index in range(size))
    if any(b <= a for a, b in zip(offsets, offsets[1:])) or offsets[-1] >= period:
        raise ValueError('invalid within-cycle timing')
    return Profile(tuple(cycles[0]), offsets, period, len(cycles))


def print_profile(profile, events):
    print(f'{len(profile.frames)} fixed-payload IDs; {profile.cycles} complete cycles checked')
    print(f'Cycle {profile.period * 1000:.3f} ms; {len(profile.frames) / profile.period:.2f} frames/s')
    print('Order: ' + ' '.join(f'{frame.can_id:03X}' for frame in profile.frames))
    print('Capture status: ' + (', '.join(f'{key}={value}' for key, value in sorted(events.items())) or 'no status records'))


def save_profile(profile, path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'version': 1, 'bitrate': 500000, 'period': profile.period,
        'cycles_checked': profile.cycles,
        'frames': [dict(can_id=f.can_id, data=f.data.hex(), offset=offset)
                   for f, offset in zip(profile.frames, profile.offsets)],
    }
    # Local captured payloads belong outside the source repository.
    import os
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as target:
        os.fchmod(target.fileno(), 0o600)
        json.dump(record, target, indent=2)
        target.write('\n')


def load_profile(path):
    record = json.loads(Path(path).expanduser().read_text())
    if record.get('version') != 1 or record.get('bitrate') != 500000:
        raise ValueError('unsupported profile version or bitrate')
    period = float(record['period'])
    entries = record['frames']
    if not math.isfinite(period) or not .001 <= period <= 10 or not 1 <= len(entries) <= 128:
        raise ValueError('invalid profile period or frame count')
    frames, offsets = [], []
    for item in entries:
        ident, offset = int(item['can_id']), float(item['offset'])
        data = bytes.fromhex(item['data'])
        if not 0 <= ident <= 0x7ff or len(data) > 8:
            raise ValueError('invalid profile CAN ID or payload length')
        if not math.isfinite(offset) or not 0 <= offset < period:
            raise ValueError('invalid profile frame offset')
        frames.append(Frame(0, 0, ident, data))
        offsets.append(offset)
    if offsets[0] != 0 or any(b <= a for a, b in zip(offsets, offsets[1:])):
        raise ValueError('profile offsets must start at zero and increase')
    if len({f.can_id for f in frames}) != len(frames):
        raise ValueError('profile contains duplicate IDs')
    return Profile(tuple(frames), tuple(offsets), period, int(record.get('cycles_checked', 0)))


def report(message, level='INFO'):
    print(f'{time.strftime("%H:%M:%S")} {level}: {message}', flush=True)


def describe_can_error(ident, data):
    labels = [(0x01, 'TX timeout'), (0x02, 'arbitration lost'),
              (0x04, 'controller status'), (0x08, 'protocol error'),
              (0x10, 'transceiver status'), (0x20, 'missing ACK'),
              (0x40, 'bus-off'), (0x80, 'bus error'), (0x100, 'controller restarted')]
    result = [name for bit, name in labels if ident & bit]
    if len(data) >= 2:
        flags = [(1, 'RX overflow'), (2, 'TX overflow'), (4, 'RX warning'),
                 (8, 'TX warning'), (0x10, 'RX passive'), (0x20, 'TX passive'),
                 (0x40, 'error-active')]
        result.extend(name for bit, name in flags if data[1] & bit)
    return ', '.join(result) or f'CAN status {ident:#x}'


def clear_stale_queue(device, features):
    """Drain old firmware TX work internally, without external CAN transmission.

    Some candleLight versions retain software TX queues across MODE_RESET and
    USB resets. Their echoes report hardware-mailbox admission, not bus ACK.
    Silent loopback allows stale queued work to complete without sending it to
    the radio. Discard its IN records; they are not radio observations.
    """
    import usb.core

    if features & 3 != 3:
        report('Silent loopback unavailable; stale firmware TX work cannot be flushed here.', 'WARNING')
        return 0
    timestamp_flag = features & 0x10
    device.ctrl_transfer(0x41, 2, 0, 0, struct.pack('<II', 1, timestamp_flag | 3))
    started = last_record = time.monotonic()
    count = 0
    try:
        while time.monotonic() - started < .5:
            try:
                device.read(0x81, 24 if timestamp_flag else 20, timeout=5)
            except usb.core.USBTimeoutError:
                now = time.monotonic()
                if now - started >= .05 and now - last_record >= .015:
                    return count
            else:
                count += 1
                last_record = time.monotonic()
        raise RuntimeError('silent-loopback queue drain did not become idle')
    finally:
        device.ctrl_transfer(0x41, 2, 0, 0, struct.pack('<II', 0, 0))


def replay(profile, duration=0, ack_timeout=2, retry_delay=1, status_interval=5):
    # Lazy imports keep inspect/test independent of the USB installation.
    import libusb_package
    import usb.backend.libusb1
    import usb.core
    import usb.util
    from gs_usb.gs_usb import GsUsb

    began = time.monotonic()
    end = began + duration if duration else float('inf')
    totals = Counter()
    next_status = began + status_interval
    last_error = {}

    def notice(key, message):
        now = time.monotonic()
        if now - last_error.get(key, float('-inf')) >= 1:
            report(message, 'ERROR')
            last_error[key] = now

    report('500 kbit/s continuous replay; Ctrl-C stops. USB/OS delays and CAN retries can delay delivery.')
    try:
        while time.monotonic() < end:
            device = adapter = None
            claimed = False
            pending = {}
            try:
                backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
                if backend is None:
                    raise RuntimeError('libusb backend unavailable')
                devices = list(usb.core.find(find_all=True, idVendor=0x1D50, idProduct=0x606F, backend=backend))
                if len(devices) != 1:
                    raise RuntimeError(f'expected one CANable; found {len(devices)}')
                device = devices[0]
                adapter = GsUsb(device)
                usb.util.claim_interface(device, 0)
                claimed = True
                adapter.stop()
                # Remove stale RX/error records from the preceding connection.
                for _ in range(256):
                    try:
                        device.read(0x81, 24, timeout=2)
                    except usb.core.USBTimeoutError:
                        break
                device.ctrl_transfer(0x41, 0, 0, 0, struct.pack('<I', 0xBEEF))
                if not adapter.set_bitrate(500000):
                    raise RuntimeError('adapter cannot configure 500 kbit/s')
                features = adapter.device_capability.feature
                timestamp_flag = features & 0x10
                stale = clear_stale_queue(device, features)
                if stale:
                    report(f'Drained {stale} old USB records in silent internal loopback.')
                device.ctrl_transfer(0x41, 2, 0, 0, struct.pack('<II', 1, timestamp_flag))
                report('CANable ready; starting captured sequence at its first frame.')
                origin = time.monotonic()
                index = cycle = 0
                while time.monotonic() < end:
                    now = time.monotonic()
                    if now >= next_status:
                        report(' '.join(f'{key}={totals[key]}' for key in
                               ('queued', 'tx_echo', 'radio_rx', 'can_errors', 'overflows', 'recoveries', 'timing_delays'))
                               + f' pending={len(pending)}')
                        next_status = now + status_interval
                    if pending and now - min(pending.values()) > ack_timeout:
                        raise RuntimeError('transmit echo timeout; resetting controller and retrying sequence')
                    deadline = origin + cycle * profile.period + profile.offsets[index]
                    # Keep the captured schedule without waiting after every USB echo.
                    # Bound queued work; loss of the receiver must not grow a backlog.
                    if len(pending) < len(profile.frames) and now >= deadline:
                        if now - deadline > .002:
                            origin += now - deadline
                            totals['timing_delays'] += 1
                        frame = profile.frames[index]
                        echo = totals['queued'] % 0xFFFFFFFF
                        raw = struct.pack('<IIBBBB8s', echo, frame.can_id, len(frame.data), 0, 0, 0, frame.data)
                        if timestamp_flag:
                            raw += struct.pack('<I', 0)
                        device.write(0x02, raw, timeout=100)
                        pending[echo] = time.monotonic()
                        totals['queued'] += 1
                        index += 1
                        if index == len(profile.frames):
                            index = 0
                            cycle += 1
                    try:
                        raw = bytes(device.read(0x81, 24 if timestamp_flag else 20, timeout=1))
                    except usb.core.USBTimeoutError:
                        continue
                    if len(raw) != (24 if timestamp_flag else 20):
                        raise RuntimeError('invalid USB receive frame')
                    echo, ident, dlc, channel, flags, reserved = struct.unpack('<IIBBBB', raw[:12])
                    if echo != 0xFFFFFFFF and echo in pending:
                        del pending[echo]
                        totals['tx_echo'] += 1
                    if flags & 1:
                        totals['overflows'] += 1
                        notice('overflow', 'CAN receive overflow; recording status and continuing')
                    if ident & 0x20000000:
                        totals['can_errors'] += 1
                        notice(('CAN', ident, raw[13]), describe_can_error(ident, raw[12:20]))
                        if ident & 0x40:
                            raise RuntimeError('CAN bus-off; resetting controller and retrying sequence')
                    elif echo == 0xFFFFFFFF:
                        totals['radio_rx'] += 1
            except (OSError, RuntimeError, ValueError, struct.error) as error:
                totals['recoveries'] += 1
                report(f'{type(error).__name__}: {error}; retrying in {retry_delay:g}s', 'ERROR')
            finally:
                if claimed:
                    try:
                        adapter.stop()
                    except Exception as error:
                        report(f'controller stop: {type(error).__name__}: {error}', 'ERROR')
                if device is not None:
                    try:
                        usb.util.dispose_resources(device)
                    except Exception as error:
                        report(f'USB release: {type(error).__name__}: {error}', 'ERROR')
            remaining = end - time.monotonic()
            if remaining > 0:
                time.sleep(min(retry_delay, remaining))
    finally:
        report('Stopped. ' + ' '.join(f'{key}={value}' for key, value in sorted(totals.items())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'replay', 'export-profile'))
    parser.add_argument('--capture', help='derive the sequence from an isolated-harness JSONL capture')
    parser.add_argument('--profile', default=str(DEFAULT_PROFILE), help='local sequence profile (also export destination)')
    parser.add_argument('--duration', type=float, default=0, help='replay seconds; 0 runs until Ctrl-C')
    parser.add_argument('--ack-timeout', type=float, default=2, help='recover after a missing transmit echo, in seconds')
    parser.add_argument('--retry-delay', type=float, default=1, help='seconds between recovery attempts')
    parser.add_argument('--status-interval', type=float, default=5, help='seconds between terminal counter summaries')
    args = parser.parse_args(argv)
    if not all(math.isfinite(value) for value in (args.duration, args.ack_timeout, args.retry_delay, args.status_interval)):
        parser.error('numeric options must be finite')
    if args.duration < 0 or min(args.ack_timeout, args.retry_delay, args.status_interval) <= 0:
        parser.error('duration must be nonnegative; other time options must be positive')
    try:
        events = Counter()
        if args.capture:
            frames, events = load_capture(args.capture)
            profile = derive_profile(frames)
            if events['overflow'] or events['usb_error'] or events['tx_echo']:
                raise ValueError('capture contains loss, USB failure, or host transmissions')
        else:
            profile = load_profile(args.profile)
        print_profile(profile, events)
        if args.action == 'export-profile':
            if not args.capture:
                raise ValueError('export-profile requires --capture')
            save_profile(profile, args.profile)
            print('Local sequence profile saved (mode 0600).')
        elif args.action == 'replay':
            replay(profile, args.duration, args.ack_timeout, args.retry_delay, args.status_interval)
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, KeyError, RuntimeError, struct.error) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


def interrupt(signum, frame):
    raise KeyboardInterrupt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupt)
    sys.exit(main())
