#!/usr/bin/env python3
"""The bench's real keepalive: an independently-verified single frame on CAN 0x53B
(InfotainmentActivationRequest), held statically active -- not extracted from the
pinned harness-profile capture, because 0x53B never appears in that capture at all.

Superseded design (through 2026-11-25): this module used to pull the one 0x529 frame
(PowerModeSelector=On) out of the pinned harness profile and replay it. That worked only
as a side effect -- PowerModeSelector fires evPowerModeOn, forcing the VIP's HSM into
RunPropulsionAccessory/Run, which is not what an idle bench keepalive should do.

Live bench testing + VIP_APP firmware RE (2026-11-26; full trial log and firmware
citations: platform/can_bench_experiments.md "Keepalive-content bisection") established,
on real hardware:
  - `cal_background_sleep_timeout_sec` (the ~10-11 min no-traffic sleep timer) is an
    HMIInactive-scoped HSM dwell timer. No CAN frame resets it generically -- a negative
    control (an unrelated/undecoded id, 0x016, static repeat) still slept at the same
    ~608-630s mark as sending nothing at all.
  - 0x529 with PowerModeSelector cleared (HmiReady/AnimationStatus unchanged) also still
    slept at 613s: those two bits carry no independent HSM-transition input.
  - 0x53B byte7 bit3=1 (InfotainmentActivationRequest) moves the HSM into
    LocalInfotainment/InfotainmentActive instead -- out of HMIInactive, no Run/Propulsion
    -- but only held STATICALLY active: toggling it back to inactive drives a faster
    fault/exit path (slept at 311s, worse than doing nothing).
  - Bisected live: static-held at 1s/2s/3s repeat intervals never slept (803s test
    window each); at 5s it slept at 673s. Required interval is between 3s and 5s; 2s is
    used below for safety margin.
"""

import argparse
import math
from pathlib import Path
import sys

from bench_can_validation import (
    DEFAULT_PROFILE, DEFAULT_TOOLS, PROFILE_EVIDENCE, hold_live, load_bench, verified_profile,
)


KEEPALIVE_CAN_ID = 0x53B
KEEPALIVE_DATA = bytes.fromhex('0000000000000008')  # byte7 bit3 = InfotainmentActivationRequest
KEEPALIVE_PERIOD = 2.0  # bisected-good at 1-3s, bisected-bad at 5s; see module docstring


def keepalive_profile(bench, source):
    """Returns the real keepalive Profile (see module docstring) -- NOT derived from
    `source`'s frame content. `source` (the digest-verified harness-profile capture) is
    still accepted and still fully validated by its own caller (`verified_profile`); it
    is kept here only so can0_radio.py's call sites, and `source.cycles`, are unchanged."""
    frame = bench.Frame(0, 0, KEEPALIVE_CAN_ID, KEEPALIVE_DATA)
    return bench.Profile((frame,), (0.0,), KEEPALIVE_PERIOD, source.cycles)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Source: platform/can_bench_experiments.md, "Keepalive-content bisection" (2026-11-26).',
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

