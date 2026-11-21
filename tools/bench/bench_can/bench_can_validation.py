"""Offline checks for the owner-local bench profile and JSONL capture format."""

import hashlib
import importlib.util
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


# Identifies the installed 32-frame, 3,806-cycle reference at inspection time.
# The v1 export contains no source-capture hash or signature.
PROFILE_DIGEST = 'eb764b861bcd731f7a12f42ff298475d0a1738c4b6b9d8d6dddd90571d5c20a5'
PROFILE_EVIDENCE = 'matches installed reference; original capture provenance unverified'
BENCH_PYTHON = '~/.local/share/gminfo-bench/venv/bin/python'
DEFAULT_TOOLS = Path.home() / 'Downloads/github/gminfo_resources/tools/bench'
DEFAULT_PROFILE = Path.home() / '.local/share/gminfo-bench/harness-profile.json'


def load_bench(tools):
    spec = importlib.util.spec_from_file_location(
        'can_bench_emulator', tools / 'can_bench_emulator.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load can_bench_emulator.py')
    bench = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bench
    spec.loader.exec_module(bench)
    return bench


def json_object(data):
    def reject_constant(_):
        raise ValueError('non-finite JSON number')

    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('duplicate JSON field')
            obj[key] = value
        return obj

    try:
        obj = json.loads(data, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except RecursionError as error:
        raise ValueError('JSON nesting exceeds the supported depth') from error
    if not isinstance(obj, dict):
        raise ValueError('expected a JSON object')
    return obj


def verified_profile(bench, path):
    with Path(path).expanduser().open('rb') as source:
        data = source.read(65537)
    if len(data) > 65536:
        raise ValueError('profile exceeds 64 KiB')
    record = json_object(data)
    normalized = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if hashlib.sha256(normalized.encode()).hexdigest() != PROFILE_DIGEST:
        raise ValueError('profile contents differ from the installed bench reference')
    entries = record['frames']
    frames = tuple(bench.Frame(0, 0, item['can_id'], bytes.fromhex(item['data']))
                   for item in entries)
    return bench.Profile(frames, tuple(item['offset'] for item in entries),
                         record['period'], record['cycles_checked'])


@dataclass(frozen=True)
class CaptureStats:
    frames: int
    elapsed_ns: int
    timestamped: int
    window_frames: int
    longest_gap_ns: int


def read_capture(path, duration=0):
    """Validate raw receive records and measure the entire host-recorded timeline."""
    first_ns = last_ns = None
    count = timestamped = window_frames = longest_gap_ns = 0
    with Path(path).expanduser().open('rb') as source:
        for lineno, data in enumerate(iter(lambda: source.readline(65537), b''), 1):
            try:
                if len(data) > 65536:
                    raise ValueError('capture record exceeds 64 KiB')
                record = json_object(data)
                if 'event' in record and record['event'] not in ('rx', 'frame'):
                    raise ValueError('unsupported capture event (expected a clean RX record)')
                encoded = record.get('usb_frame_hex')
                if type(encoded) is not str:
                    raise ValueError('missing raw USB frame')
                raw = bytes.fromhex(encoded)
                if len(raw) not in (20, 24):
                    raise ValueError('invalid classic gs_usb frame length')
                echo, ident, dlc, channel, flags, reserved = struct.unpack_from('<IIBBBB', raw)
                fields = ('echo_id', 'can_id_raw', 'dlc', 'channel', 'flags')
                for key, value in zip(fields, (echo, ident, dlc, channel, flags)):
                    if type(record.get(key)) is not int or record[key] != value:
                        raise ValueError(f'{key} disagrees with raw USB frame')
                if echo != 0xffffffff or ident & 0x20000000 or flags:
                    raise ValueError('transmit echo, CAN error or flagged receive record')
                if ident > 0x7ff or dlc > 8 or channel or reserved:
                    raise ValueError('unsupported CAN frame format')
                if len(raw) == 24:
                    raw_us, = struct.unpack_from('<I', raw, 20)
                    if 'hardware_time_us' in record and (
                        type(record['hardware_time_us']) is not int
                        or record['hardware_time_us'] != raw_us
                    ):
                        raise ValueError('hardware timestamp disagrees with raw USB frame')
                    timestamped += 1
                elif record.get('hardware_time_us') is not None:
                    raise ValueError('USB frame has no hardware timestamp to verify')
                host_ns = record.get('host_time_ns')
                if type(host_ns) is not int or not 0 <= host_ns <= 2**64 - 1:
                    raise ValueError('invalid host timestamp')
                if last_ns is not None:
                    if host_ns < last_ns:
                        raise ValueError('host timestamps moved backwards')
                    longest_gap_ns = max(longest_gap_ns, host_ns - last_ns)
                if first_ns is None:
                    first_ns = host_ns
                last_ns = host_ns
                count += 1
                if not duration or (host_ns - first_ns) / 1e9 < duration:
                    window_frames += 1
            except ValueError as error:
                raise ValueError(f'capture line {lineno}: {error}') from error
    if not count:
        raise ValueError('empty capture')
    return CaptureStats(count, last_ns - first_ns, timestamped, window_frames, longest_gap_ns)


def hold_live():
    print('HOLD. The current transport cannot verify queue drainage and completed '
          'adapter admissions in one session. An adapter echo only confirms mailbox '
          'admission. Receiver behavior is unverified. Zero frames sent. '
          'Use --dry-run for offline validation.', file=sys.stderr)
    if importlib.util.find_spec('libusb_package') is None:
        print(f'This interpreter also lacks libusb_package. The bench interpreter is '
              f'{BENCH_PYTHON}. The transport HOLD applies there too.', file=sys.stderr)
    return 1

