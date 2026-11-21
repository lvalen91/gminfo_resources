#!/usr/bin/env python3
"""Validate the documented power-on and keepalive schedules offline."""

import argparse
import math
from pathlib import Path
import sys

from bench_can_validation import (
    DEFAULT_PROFILE, DEFAULT_TOOLS, PROFILE_EVIDENCE, hold_live, load_bench, verified_profile,
)


DOCUMENTED_PERIOD = 0.320270
STARTUP_OFFSETS = {
    0x145: 0.0,
    0x529: 0.040001,
    0x457: 0.160120,
    0x458: 0.170139,
}


def documented_frames(source):
    found = {}
    actual_offsets = {}
    for frame, offset in zip(source.frames, source.offsets):
        if frame.can_id in STARTUP_OFFSETS:
            if frame.can_id in found:
                raise ValueError(f'profile contains duplicate {frame.can_id:03X}')
            found[frame.can_id] = frame
            actual_offsets[frame.can_id] = offset
    missing = set(STARTUP_OFFSETS) - set(found)
    if missing:
        raise ValueError('profile lacks ' + ', '.join(f'{value:03X}' for value in sorted(missing)))
    if not math.isclose(source.period, DOCUMENTED_PERIOD,
                        rel_tol=0, abs_tol=0.005):
        raise ValueError('profile cycle differs from documented 320.270ms')
    for can_id, expected in STARTUP_OFFSETS.items():
        if not math.isclose(actual_offsets[can_id], expected,
                            rel_tol=0, abs_tol=0.005):
            raise ValueError(f'profile {can_id:03X} timing differs from documented capture')
    return found


def one_shot(bench, events, duration):
    events.sort(key=lambda item: item[0])
    offsets = tuple(time for time, _ in events)
    if any(right <= left for left, right in zip(offsets, offsets[1:])):
        raise ValueError('power-on event times overlap')
    return bench.Profile(tuple(frame for _, frame in events), offsets,
                         duration + 60.0, 1)


def build_plan(bench, source):
    frames = documented_frames(source)
    events = [(0.0, frames[0x145]), (0.5, frames[0x529])]
    # platform/can_network.md: wait to 30s, then repeat four IDs for 10s.
    complete_cycles = int(10.0 / source.period)
    for cycle in range(complete_cycles):
        base = 30.0 + cycle * source.period
        for can_id, offset in STARTUP_OFFSETS.items():
            events.append((base + offset, frames[can_id]))
    # Five seconds of 529 bridges USB adapter reinitialization before the
    # unbounded 529 replay begins.
    for index in range(16):
        events.append((40.0 + index * source.period, frames[0x529]))
    duration = 40.0 + 16 * source.period + 0.05
    startup = one_shot(bench, events, duration)
    keepalive = bench.Profile((frames[0x529],), (0.0,), source.period,
                              source.cycles)
    return startup, duration, keepalive


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=('Start immediately after fresh RH850 UART output following '
                'physical power-on. Source: platform/can_network.md.'),
    )
    parser.add_argument('--tools', type=Path, default=DEFAULT_TOOLS)
    parser.add_argument('--dry-run', action='store_true',
                        help='check the reference and both phases without opening the adapter')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE,
                        help='owner-local captured harness profile')
    parser.add_argument('--duration', type=float, default=0,
                        help='requested keepalive window in seconds (zero is unbounded)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not args.dry_run:
        return hold_live()
    try:
        bench = load_bench(args.tools)
        startup, startup_duration, keepalive = build_plan(bench, verified_profile(bench, args.profile))
        print(f'{len(startup.frames)} startup events over {startup_duration:.6f}s, '
              f'keepalive period {keepalive.period:.6f}s. Profile {PROFILE_EVIDENCE}. '
              'Dry run completed. Zero frames sent. Hardware readiness HOLD.')
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

