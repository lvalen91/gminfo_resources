#!/usr/bin/env python3
"""Transmit the fixed captured radio schedules through SocketCAN (can0).

This is the shared-bus counterpart of radio_on.py. Frame bytes, offsets and
periods come only from the digest-pinned harness profile through the existing
schedule builders (radio_on.scheduled_events, replay_can_power_on_keepalive,
replay_can_keepalive, reset_vip_can). Only the I/O layer differs: a CAN_RAW
socket on a kernel interface, so observers and other senders may share the bus.

Modes: full, startup, startup-keepalive, keepalive (as radio_on.py) and
vip-reset (the reset_vip_can.py plan). Every mode supports --dry-run.
"""

import argparse
import contextlib
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import struct
import subprocess
import sys
import time

from bench_can_validation import DEFAULT_PROFILE, DEFAULT_TOOLS, PROFILE_EVIDENCE, load_bench, verified_profile
import radio_on
from replay_can_keepalive import keepalive_profile
from replay_can_power_on_keepalive import build_plan
import reset_vip_can


MODES = (*radio_on.MODES, 'vip-reset')
CAN_FRAME = struct.Struct('=IB3x8s')
CAN_ERR_FLAG = 0x20000000
CAN_RTR_FLAG = 0x40000000
CAN_EFF_FLAG = 0x80000000
CAN_ERR_MASK = 0x1FFFFFFF
CAN_ERR_BUSOFF = 0x40
ECHO_TIMEOUT = radio_on.ECHO_TIMEOUT
EXIT_ECHO_TIMEOUT = 3
EXIT_BUSY = 4
EXIT_BUSOFF = 5
DEFAULT_LOCK = Path('/run/lock/pibench-can0-schedule.lock')
# Validated bench timing: 500 kbit/s from a 48 MHz adapter clock, sample point 0.875.
PINNED_TIMING = dict(bitrate=500000, tq=125, prop_seg=1, phase_seg1=12, phase_seg2=2, sjw=1, brp=6)


class EchoTimeout(RuntimeError):
    pass


class BusOff(RuntimeError):
    pass


class ScheduleBusy(RuntimeError):
    pass


def default_tools():
    local = Path(__file__).resolve().parents[1]
    return local if (local / 'can_bench_emulator.py').is_file() else DEFAULT_TOOLS


def check_interface(iface):
    """Refuse to transmit unless the interface is up with the pinned bit timing."""
    result = subprocess.run(['ip', '-details', '-json', 'link', 'show', 'dev', iface],
                            capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'{iface} is unavailable: {result.stderr.strip()}')
    (link,) = json.loads(result.stdout)
    if 'UP' not in link.get('flags', ()):
        raise RuntimeError(f'{iface} is down')
    info = link.get('linkinfo', {}).get('info_data', {})
    if 'LISTEN-ONLY' in info.get('ctrlmode', ()):
        raise RuntimeError(f'{iface} is listen-only')
    if 'LOOPBACK' in info.get('ctrlmode', ()):
        raise RuntimeError(f'{iface} is in loopback mode')
    timing = info.get('bittiming', {})
    wrong = {key: timing.get(key) for key, value in PINNED_TIMING.items() if timing.get(key) != value}
    if wrong:
        raise RuntimeError(f'{iface} bit timing differs from the validated bench timing: {wrong}')
    if info.get('clock') != 48000000:
        raise RuntimeError(f'{iface} adapter clock is {info.get("clock")}, expected 48 MHz')


def _ip_link(*args):
    command = ['ip', 'link', 'set', 'dev', *args]
    if os.geteuid():
        command = ['sudo', '-n', *command]
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'{" ".join(command)} failed: {result.stderr.strip()}')


def drain_adapter(iface):
    """SocketCAN counterpart of radio_on.py's bench.clear_stale_queue.

    candleLight keeps unconfirmed TX work in its hardware mailboxes and software
    queue across an interface down/up (MODE_RESET). With no ACK on the bus those
    frames retransmit forever, every later send() gets ENOBUFS, and their stale
    echo ids could falsely confirm new frames. Bringing the interface up briefly in
    listen-only loopback lets that work complete internally, never on the bus.
    """
    timing = ['tq', str(PINNED_TIMING['tq'])] + [
        item for key in ('prop_seg', 'phase_seg1', 'phase_seg2', 'sjw')
        for item in (key.replace('_', '-'), str(PINNED_TIMING[key]))]
    _ip_link(iface, 'down')
    try:
        _ip_link(iface, 'type', 'can', *timing, 'listen-only', 'on', 'loopback', 'on')
        _ip_link(iface, 'up')
        time.sleep(.5)
        _ip_link(iface, 'down')
    finally:
        _ip_link(iface, 'type', 'can', *timing, 'listen-only', 'off', 'loopback', 'off')
        _ip_link(iface, 'up')
    check_interface(iface)


@contextlib.contextmanager
def drained_adapter(iface, totals, enabled=True):
    """Start from an empty adapter queue; leave none of our unconfirmed frames retrying."""
    if enabled:
        drain_adapter(iface)
    try:
        yield
    finally:
        if enabled and (totals.queued > totals.admitted or totals.uncertain_write):
            try:
                drain_adapter(iface)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                print(f'exit drain failed: {error}', file=sys.stderr)


def open_can(iface):
    sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    try:
        # Own-frame echoes are the transmit confirmations; error frames are observations.
        sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_RECV_OWN_MSGS, 1)
        sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_ERR_FILTER, CAN_ERR_MASK)
        sock.bind((iface,))
    except BaseException:
        sock.close()
        raise
    return sock


@contextlib.contextmanager
def schedule_lock(path, mode):
    """Serialize fixed schedules. Observers and ad-hoc senders need no lock."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = os.pread(fd, 256, 0).decode(errors='replace').strip()
            raise ScheduleBusy(f'another fixed schedule holds {path}: {holder or "unknown"}') from None
        os.ftruncate(fd, 0)
        os.pwrite(fd, json.dumps(dict(pid=os.getpid(), mode=mode)).encode(), 0)
        try:
            yield
        finally:
            os.ftruncate(fd, 0)
    finally:
        os.close(fd)


def events_for(mode, bench, profile):
    """Select the fixed (offset, frame) schedule for one mode from the existing builders."""
    if mode == 'vip-reset':
        plan, _, _ = reset_vip_can.build_plan(bench, profile)
        return zip(plan.offsets, plan.frames)
    startup, _, _ = build_plan(bench, profile)
    keepalive = keepalive_profile(bench, profile)
    return radio_on.scheduled_events(mode, profile, startup, keepalive)


def summary(mode, bench, profile):
    if mode == 'vip-reset':
        plan, duration, _ = reset_vip_can.build_plan(bench, profile)
        return f'{len(plan.frames)} scheduled events over {duration:.6f} s, one shot'
    return radio_on.summary(mode, bench, profile)


def describe(bench, profile):
    """Machine-readable description of every mode, derived from the verified profile."""
    keepalive = keepalive_profile(bench, profile)
    (frame,) = keepalive.frames
    modes = {}
    for mode in MODES:
        entry = dict(summary=summary(mode, bench, profile),
                     continuous=mode in ('full', 'keepalive', 'startup-keepalive'))
        if mode in ('startup', 'vip-reset'):
            events = list(events_for(mode, bench, profile))
            entry.update(frames=len(events), last_offset=events[-1][0],
                         can_ids=sorted({f'{item.can_id:03X}' for _, item in events}))
        modes[mode] = entry
    return dict(profile_evidence=PROFILE_EVIDENCE, profile_frames=len(profile.frames),
                profile_period=profile.period,
                keepalive=dict(can_id=frame.can_id, id_hex=f'{frame.can_id:03X}',
                               data=frame.data.hex(), dlc=len(frame.data), period=keepalive.period),
                timing=PINNED_TIMING, modes=modes)


def transmit(sock, events, stop, totals, echo_timeout=ECHO_TIMEOUT, clock=time.monotonic):
    """Transmit a fixed schedule, one unconfirmed frame at a time, on absolute deadlines."""
    origin = clock()
    events = iter(events)
    try:
        offset, frame = next(events)
    except StopIteration:
        return
    next_send = origin + offset
    expires = None
    while True:
        now = clock()
        if expires is not None and now >= expires:
            raise EchoTimeout('can0 transmit confirmation timed out (no ACK on the bus?)')
        if expires is None:
            if stop.signum:
                return
            if now >= next_send:
                if now - next_send > .002:
                    totals.timing_delays += 1
                if not 0 <= frame.can_id <= 0x7ff or not 0 <= len(frame.data) <= 8:
                    raise ValueError('fixed schedule contains an unsupported CAN frame')
                packet = CAN_FRAME.pack(frame.can_id, len(frame.data), frame.data)
                expires = clock() + echo_timeout
                while True:
                    try:
                        totals.uncertain_write = True
                        sent = sock.send(packet)
                        break
                    except OSError as error:
                        # A full interface queue means earlier frames are still unconfirmed.
                        if error.errno != errno.ENOBUFS:
                            raise
                        totals.uncertain_write = False
                        if clock() >= expires:
                            raise EchoTimeout('can0 transmit queue stayed full') from error
                        time.sleep(.001)
                if sent != CAN_FRAME.size:
                    raise OSError('short CAN socket write; admission unknown')
                totals.uncertain_write = False
                totals.queued += 1
        deadline = expires if expires is not None else next_send
        wait = max(0.0, min(.020, deadline - clock()))
        readable, _, _ = select.select([sock], [], [], wait)
        if not readable:
            continue
        raw, _, flags, _ = sock.recvmsg(CAN_FRAME.size)
        if len(raw) != CAN_FRAME.size:
            raise RuntimeError('invalid CAN socket record size')
        ident, dlc, data = CAN_FRAME.unpack(raw)
        if ident & CAN_ERR_FLAG:
            totals.can_errors += 1
            if ident & CAN_ERR_BUSOFF:
                raise BusOff('CAN controller entered bus-off')
            # Missing-ACK/status records are expected while a powered radio wakes.
            continue
        if not flags & socket.MSG_CONFIRM:
            totals.bus_rx += 1  # Bus traffic or another local sender.
            continue
        if (expires is None or ident != frame.can_id or dlc != len(frame.data)
                or data[:dlc] != frame.data):
            raise RuntimeError('unexpected can0 transmit confirmation')
        totals.admitted += 1
        expires = None
        try:
            offset, frame = next(events)
        except StopIteration:
            return
        next_send = origin + offset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=(*MODES, 'describe'))
    parser.add_argument('--dry-run', action='store_true',
                        help='validate the fixed local profile and print the schedule head without opening a socket')
    parser.add_argument('--iface', default='can0')
    parser.add_argument('--virtual', action='store_true',
                        help='test only: allow a vcan interface and skip the bit-timing check')
    parser.add_argument('--tools', type=Path, default=default_tools())
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--lock', type=Path, default=DEFAULT_LOCK)
    parser.add_argument('--startup-if', type=Path, metavar='FLAG',
                        help='keepalive mode only: if FLAG exists, remove it and run startup-keepalive once')
    parser.add_argument('--json', action='store_true', help='print the final result as one JSON object')
    args = parser.parse_args(argv)
    if args.iface != 'can0' and not (args.virtual and args.iface.startswith('vcan')):
        parser.error('only can0 is a live transport; vcan* requires --virtual')
    if args.startup_if and args.mode != 'keepalive':
        parser.error('--startup-if applies to keepalive mode only')
    totals = radio_on.Totals()
    status, code, detail, mode = 'failed', 1, '', args.mode
    live = not args.dry_run and mode != 'describe'
    try:
        bench = load_bench(args.tools)
        profile = verified_profile(bench, args.profile)
        if mode == 'describe':
            print(json.dumps(describe(bench, profile), indent=None if args.json else 2))
            return 0
        if args.dry_run:
            head = [f'+{offset:.6f}s {frame.can_id:03X}#{frame.data.hex()}'
                    for (offset, frame), _ in zip(events_for(mode, bench, profile), range(6))]
            text = f'{mode}: {summary(mode, bench, profile)}. Dry run. Zero frames sent.'
            if args.json:
                print(json.dumps(dict(mode=mode, status='dry-run', summary=summary(mode, bench, profile), head=head)))
            else:
                print(text, 'Schedule head: ' + ', '.join(head), sep='\n')
            return 0
        if args.startup_if and args.startup_if.exists():
            args.startup_if.unlink()
            mode = 'startup-keepalive'
        if not args.virtual:
            check_interface(args.iface)
        with schedule_lock(args.lock, mode), radio_on.stop_signals() as stop, \
                drained_adapter(args.iface, totals, enabled=not args.virtual), \
                contextlib.closing(open_can(args.iface)) as sock:
            print(f'{mode} active on {args.iface}: {summary(mode, bench, profile)}. SIGTERM stops.',
                  file=sys.stderr, flush=True)
            transmit(sock, events_for(mode, bench, profile), stop, totals)
            status = 'stopped' if stop.signum else 'completed'
        code = 0
    except KeyboardInterrupt:
        status, code = 'interrupted', 130
    except BusOff as error:
        code, detail = EXIT_BUSOFF, str(error)
    except EchoTimeout as error:
        code, detail = EXIT_ECHO_TIMEOUT, str(error)
    except ScheduleBusy as error:
        status, code, detail = 'busy', EXIT_BUSY, str(error)
    except (ImportError, OSError, RuntimeError, ValueError, KeyError, struct.error,
            subprocess.TimeoutExpired) as error:
        detail = f'{type(error).__name__}: {error}'
    finally:
        if live:
            if detail:
                print(detail, file=sys.stderr)
            result = dict(mode=mode, iface=args.iface, status=status, exit_code=code, detail=detail,
                          queued=totals.queued, confirmed=totals.admitted,
                          pending=totals.queued - totals.admitted,
                          uncertain_write=totals.uncertain_write, bus_rx=totals.bus_rx,
                          can_errors=totals.can_errors, timing_delays=totals.timing_delays)
            if args.json:
                print(json.dumps(result), flush=True)
            print(' '.join(f'{key}={value}' for key, value in result.items() if key != 'detail')
                  + '. Confirmation is the adapter transmit echo. ECU processing is unverified.',
                  file=sys.stderr)
    if not live and detail:
        print(detail, file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())
