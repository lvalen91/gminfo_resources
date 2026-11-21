#!/usr/bin/env python3
"""Validate the documented post-boot keepalive schedule offline."""

import argparse
import math
from pathlib import Path
import sys

from bench_can_validation import (
    DEFAULT_PROFILE, DEFAULT_TOOLS, PROFILE_EVIDENCE, hold_live, load_bench, verified_profile,
)


DOCUMENTED_PERIOD = 0.320270


def keepalive_profile(bench, source):
    frames = [frame for frame in source.frames if frame.can_id == 0x529]
    if len(frames) != 1:
        raise ValueError('profile must contain exactly one 529 frame')
    if not math.isclose(source.period, DOCUMENTED_PERIOD,
                        rel_tol=0, abs_tol=0.005):
        raise ValueError(
            f'profile period {source.period:.6f}s differs from documented '
            f'{DOCUMENTED_PERIOD:.6f}s cycle'
        )
    return bench.Profile((frames[0],), (0.0,), source.period, source.cycles)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Source: platform/can_network.md, smallest demonstrated home-screen set.',
    )
    parser.add_argument('--tools', type=Path, default=DEFAULT_TOOLS)
    parser.add_argument('--dry-run', action='store_true',
                        help='check the reference and schedule without opening the adapter')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE,
                        help='owner-local captured harness profile')
    parser.add_argument('--duration', type=float, default=0,
                        help='requested replay window in seconds (zero is unbounded)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not args.dry_run:
        return hold_live()
    try:
        bench = load_bench(args.tools)
        profile = keepalive_profile(bench, verified_profile(bench, args.profile))
        print(f'Keepalive period {profile.period:.6f}s. Profile {PROFILE_EVIDENCE}. '
              'Dry run completed. Zero frames sent. Hardware readiness HOLD.')
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

