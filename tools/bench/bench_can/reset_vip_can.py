#!/usr/bin/env python3
"""Validate the documented VIP reset schedule offline."""

import argparse
import math
from pathlib import Path
import sys

from bench_can_validation import (
    DEFAULT_PROFILE, DEFAULT_TOOLS, PROFILE_EVIDENCE, hold_live, load_bench, verified_profile,
)


DOCUMENTED_PERIOD = 0.320270
HOLD_SECONDS = 10.5


def captured_frame(source, can_id):
    matches = [frame for frame in source.frames if frame.can_id == can_id]
    if len(matches) != 1:
        raise ValueError(f'profile must contain exactly one {can_id:03X} frame')
    return matches[0]


def one_shot(bench, events, duration):
    events.sort(key=lambda item: item[0])
    offsets = tuple(time for time, _ in events)
    if any(right <= left for left, right in zip(offsets, offsets[1:])):
        raise ValueError('VIP reset event times overlap')
    return bench.Profile(tuple(frame for _, frame in events), offsets,
                         duration + 60.0, 1)


def build_plan(bench, source):
    if not math.isclose(source.period, DOCUMENTED_PERIOD,
                        rel_tol=0, abs_tol=0.005):
        raise ValueError('profile cycle differs from documented 320.270ms')
    wake = captured_frame(source, 0x145)
    keepalive = captured_frame(source, 0x529)
    held = bench.Frame(0, 0, 0x526, bytes.fromhex('0000000000800000'))
    released = bench.Frame(0, 0, 0x526, bytes(8))
    events = []

    # platform/can_network.md documents original 145/529 continuing while
    # synthetic 526 b5 bit7 repeats at about 100ms.
    cycles = math.ceil((HOLD_SECONDS + 0.1) / source.period)
    for cycle in range(cycles):
        base = cycle * source.period
        if base < HOLD_SECONDS:
            events.append((base, wake))
        if base + 0.040001 < HOLD_SECONDS:
            events.append((base + 0.040001, keepalive))
    reset_at = 0.080
    while reset_at < HOLD_SECONDS:
        events.append((reset_at, held))
        reset_at += 0.100
    release_at = HOLD_SECONDS + 0.050
    events.append((release_at, released))
    duration = release_at + 0.100
    release = bench.Profile((released,), (0.0,), 60.0, 1)
    return one_shot(bench, events, duration), duration, release


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=('Models original 145/529 and a 10.5s hold, then '
                'releases it. Source: platform/can_network.md.'),
    )
    parser.add_argument('--tools', type=Path, default=DEFAULT_TOOLS)
    parser.add_argument('--dry-run', action='store_true',
                        help='check the reference and reset schedule without opening the adapter')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE,
                        help='owner-local captured harness profile')
    args = parser.parse_args(argv)
    if not args.dry_run:
        return hold_live()
    try:
        bench = load_bench(args.tools)
        plan, duration, _ = build_plan(bench, verified_profile(bench, args.profile))
        print(f'{len(plan.frames)} scheduled events over {duration:.6f}s. '
              f'Profile {PROFILE_EVIDENCE}. '
              'Dry run completed. Zero frames sent. Hardware readiness HOLD.')
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

