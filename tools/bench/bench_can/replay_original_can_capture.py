#!/usr/bin/env python3
"""Validate the full chronology of an original harness capture offline."""

import argparse
import math
from pathlib import Path
import sys

from bench_can_validation import DEFAULT_TOOLS, hold_live, read_capture


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path,
                        help='original isolated-harness JSONL capture')
    parser.add_argument('--tools', type=Path, default=DEFAULT_TOOLS)
    parser.add_argument('--dry-run', action='store_true',
                        help='validate all capture records and report the recorded timeline offline')
    parser.add_argument('--duration', type=float, default=0,
                        help='requested replay window in seconds (zero is unbounded)')
    parser.add_argument('--status-interval', type=float, default=5)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not math.isfinite(args.status_interval) or args.status_interval <= 0:
        parser.error('status interval must be finite and positive')
    if not args.dry_run:
        return hold_live()
    try:
        stats = read_capture(args.capture, args.duration)
        print(f'{stats.frames} received frames, {stats.elapsed_ns / 1e9:.6f}s '
              f'host-recorded span, longest gap {stats.longest_gap_ns / 1e9:.6f}s, '
              f'{stats.timestamped} raw hardware timestamps. '
              f'{stats.window_frames} frames in the requested window. '
              'Dry run completed. Zero frames sent. Hardware readiness HOLD.')
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

