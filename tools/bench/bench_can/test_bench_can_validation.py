import contextlib
from collections import namedtuple
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bench_can_validation as validation
import replay_can_keepalive as keepalive
import replay_can_power_on_keepalive as power
import replay_original_can_capture as original
import reset_vip_can as reset


def fixture_bench():
    return SimpleNamespace(Frame=namedtuple('Frame', 'host_ns device_us can_id data'),
                           Profile=namedtuple('Profile', 'frames offsets period cycles'))


def rx(host_ns=10000, device_us=10, *, ident=7, flags=0, echo=0xffffffff):
    data = struct.pack('<IIBBBB8s', echo, ident, 1, 0, flags, 0, b'A')
    if device_us is not None:
        data += struct.pack('<I', device_us)
    return dict(host_time_ns=host_ns, hardware_time_us=device_us, echo_id=echo,
                flags=flags, channel=0, dlc=1, can_id_raw=ident, usb_frame_hex=data.hex())


class OfflineChecks(unittest.TestCase):
    def setUp(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        self.path = Path(tempdir.name) / 'fixture'

    def write_lines(self, records):
        self.path.write_text(''.join(json.dumps(record) + '\n' for record in records))

    def test_all_received_frames_and_gaps_retained(self):
        self.write_lines([rx(device_us=0xfffffff0), rx(device_us=4),
                          rx(host_ns=2_000_010_000, device_us=2_000_004)])
        stats = validation.read_capture(self.path, 2.0)
        self.assertEqual(stats, validation.CaptureStats(3, 2_000_000_000, 3, 2, 2_000_000_000))

    def test_invalid_or_inconsistent_capture(self):
        invalid = [None, [], {}, rx(ident=0x20000001), rx(echo=1), rx(flags=1),
                   dict(rx(), hardware_time_us=5), dict(rx(), echo_id=True),
                   dict(rx(), event='usb_error'), {'event': 'overflow'},
                   dict(rx(device_us=None), hardware_time_us=10), rx(host_ns=1)]
        for record in invalid:
            with self.subTest(record_type=type(record)):
                self.write_lines([rx(), record])
                with self.assertRaisesRegex(ValueError, 'capture line 2'):
                    validation.read_capture(self.path)

    def test_malformed_duplicate_and_oversize_json(self):
        for data in (b'{"missing":', b'{"event":0,"event":1}',
                     b'{"extra":NaN}', b' ' * 65537):
            self.path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'capture line 1'):
                validation.read_capture(self.path)

    def test_capture_dry_run_never_enters_live_path(self):
        self.write_lines([rx(device_us=None)])
        with patch.object(original, 'hold_live', side_effect=AssertionError), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(original.main([str(self.path), '--dry-run']), 0)

    def test_reference_mismatch_including_payload_change(self):
        profile = {'version': 1, 'bitrate': 500000, 'period': 0.32, 'cycles_checked': 6,
                   'frames': [{'can_id': 7, 'data': '42', 'offset': 0.0}]}
        digest = hashlib.sha256(json.dumps(
            profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        bench = fixture_bench()
        with patch.object(validation, 'PROFILE_DIGEST', digest):
            self.path.write_text(json.dumps(profile, indent=4))
            result = validation.verified_profile(bench, self.path)
            self.assertEqual(result.frames[0].data, b'B')
            profile['frames'][0]['data'] = '43'
            self.path.write_text(json.dumps(profile))
            with self.assertRaisesRegex(ValueError, 'reference'):
                validation.verified_profile(bench, self.path)

    def test_three_profile_cli_dry_runs_cannot_call_replay(self):
        bench = fixture_bench()
        profile = bench.Profile(tuple(bench.Frame(0, 0, ident, bytes(8))
                                      for ident in power.STARTUP_OFFSETS),
                                tuple(power.STARTUP_OFFSETS.values()), power.DOCUMENTED_PERIOD, 6)
        for script in (keepalive, power, reset):
            with self.subTest(script=script.__name__):
                with patch.object(script, 'load_bench', return_value=bench), \
                        patch.object(script, 'verified_profile', return_value=profile), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(script.main(['--dry-run']), 0)

    def test_every_live_invocation_stops_before_opening_files_or_usb(self):
        for script in (original, keepalive, power, reset):
            args = [str(self.path)] if script is original else ['--profile', str(self.path)]
            output = io.StringIO()
            with self.subTest(script=script.__name__), contextlib.redirect_stderr(output), \
                    patch.object(validation.importlib.util, 'find_spec', return_value=None):
                self.assertEqual(script.main(args), 1)
                self.assertIn('HOLD', output.getvalue())
                self.assertIn('Zero frames sent', output.getvalue())
                self.assertIn('libusb_package', output.getvalue())


if __name__ == '__main__':
    unittest.main()

