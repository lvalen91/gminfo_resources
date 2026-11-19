"""Profile validation and mocked USB transmission tests; no hardware access."""

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import struct
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import can_bench_emulator as emulator


def capture_frames(start=0, cycles=8):
    result = []
    for index in range(cycles * 3):
        stamp = start + index * 10_000_000
        ident = index % 3 + 1
        result.append(emulator.Frame(stamp, (stamp // 1000) % 2**32, ident, bytes([ident])))
    return result


class ProfileTests(unittest.TestCase):
    def test_local_profile_round_trip(self):
        original = emulator.derive_profile(capture_frames())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            emulator.save_profile(original, path)
            restored = emulator.load_profile(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(restored.period, original.period)
        self.assertEqual(restored.offsets, original.offsets)
        self.assertEqual([(f.can_id, f.data) for f in restored.frames],
                         [(f.can_id, f.data) for f in original.frames])

    def test_nonfinite_or_invalid_profile_is_rejected(self):
        original = emulator.derive_profile(capture_frames())
        for value in (float('nan'), float('inf'), -1):
            with self.subTest(period=value), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'profile.json'
                emulator.save_profile(original, path)
                record = json.loads(path.read_text())
                record['period'] = value
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, 'invalid profile'):
                    emulator.load_profile(path)

    def test_cycle_timing_across_hardware_timestamp_wrap(self):
        profile = emulator.derive_profile(capture_frames(start=(2**32 - 40_000) * 1000))
        self.assertEqual([frame.can_id for frame in profile.frames], [1, 2, 3])
        self.assertAlmostEqual(profile.period, 0.03)
        self.assertEqual(profile.offsets, (0.0, 0.01, 0.02))

    def test_latest_power_cycle_is_used(self):
        first = capture_frames()
        latest = [emulator.Frame(f.host_ns, f.device_us, f.can_id, b'new')
                  for f in capture_frames(start=2_000_000_000)]
        profile = emulator.derive_profile(first + latest)
        self.assertTrue(all(frame.data == b'new' for frame in profile.frames))

    def test_changing_payload_is_rejected(self):
        frames = capture_frames()
        old = frames[-1]
        frames[-1] = emulator.Frame(old.host_ns, old.device_us, old.can_id, b'changed')
        with self.assertRaisesRegex(ValueError, 'payloads vary'):
            emulator.derive_profile(frames)

    def test_missing_frame_breaks_cyclic_order(self):
        frames = capture_frames()
        del frames[15]
        with self.assertRaisesRegex(ValueError, 'frame order'):
            emulator.derive_profile(frames)

    def test_live_partial_record_does_not_hide_completed_data(self):
        raw = struct.pack('<IIBBBB8sI', 0xFFFFFFFF, 1, 1, 0, 0, 0, b'x', 100)
        record = dict(can_id_raw=1, dlc=1, channel=0, flags=0,
                      echo_id=0xFFFFFFFF, host_time_ns=100_000,
                      hardware_time_us=100, usb_frame_hex=raw.hex())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.jsonl'
            path.write_bytes(json.dumps(record).encode() + b'\n{"incomplete":')
            frames, events = emulator.load_capture(path)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, b'x')
        self.assertFalse(events)

    def test_raw_metadata_mismatch_is_rejected(self):
        raw = struct.pack('<IIBBBB8s', 0xFFFFFFFF, 1, 1, 0, 0, 0, b'x')
        record = dict(can_id_raw=2, dlc=1, channel=0, flags=0,
                      echo_id=0xFFFFFFFF, host_time_ns=0,
                      hardware_time_us=0, usb_frame_hex=raw.hex())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.jsonl'
            path.write_text(json.dumps(record) + '\n')
            with self.assertRaisesRegex(ValueError, 'disagree'):
                emulator.load_capture(path)


class ReplayTests(unittest.TestCase):
    def run_replay(self, complete=True, injected=None, duration=.2,
                   ack_timeout=.02, absent=False, timestamps=True):
        import usb.core

        device = Mock()
        device.sent_times = []
        adapter = Mock()
        adapter.device_capability = SimpleNamespace(feature=(0x10 if timestamps else 0) | 3)
        adapter.set_bitrate.return_value = True
        clock = [0.0]
        queue = []
        writes = []
        active = [False]
        did_inject = [False]

        def stop():
            active[0] = False
            queue.clear()

        adapter.stop.side_effect = stop

        def control(*args):
            if args[1] == 2:
                active[0] = struct.unpack('<II', args[4])[0] == 1

        device.ctrl_transfer.side_effect = control

        def status_frame(ident, flags=0, data=b''):
            raw = struct.pack('<IIBBBB8s', 0xffffffff, ident, 8, 0, flags, 0, data)
            return raw + (struct.pack('<I', 0) if timestamps else b'')

        def write(endpoint, raw, timeout):
            writes.append(bytes(raw))
            device.sent_times.append(clock[0])
            if complete:
                queue.append(bytes(raw))

        def read(endpoint, size, timeout):
            clock[0] += 0.001
            if active[0] and writes and injected and not did_inject[0]:
                did_inject[0] = True
                if injected == 'interrupt':
                    raise KeyboardInterrupt
                if injected == 'usb':
                    raise usb.core.USBError('simulated USB disconnect')
                if injected == 'busoff':
                    return status_frame(0x20000040)
                if injected == 'ack':
                    return status_frame(0x20000024, data=b'\x00\x0c')
                if injected == 'overflow':
                    return status_frame(0x600, flags=1)
                if injected == 'malformed':
                    return b'bad'
            if queue:
                return queue.pop(0)
            raise usb.core.USBTimeoutError('idle')

        device.write.side_effect = write
        device.read.side_effect = read
        profile = emulator.derive_profile(capture_frames())
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch('usb.core.find', return_value=[] if absent else [device]))
            stack.enter_context(patch('usb.util.claim_interface'))
            dispose = stack.enter_context(patch('usb.util.dispose_resources'))
            stack.enter_context(patch('gs_usb.gs_usb.GsUsb', return_value=adapter))
            stack.enter_context(patch('libusb_package.find_library'))
            stack.enter_context(patch('usb.backend.libusb1.get_backend'))
            stack.enter_context(patch.object(emulator.time, 'monotonic', side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(emulator.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)))
            stack.enter_context(contextlib.redirect_stdout(output))
            try:
                emulator.replay(profile, duration, ack_timeout, retry_delay=.01, status_interval=.02)
            except KeyboardInterrupt:
                if injected != 'interrupt':
                    raise
            else:
                if injected == 'interrupt':
                    self.fail('Ctrl-C was swallowed')
        if not absent:
            self.assertGreaterEqual(adapter.stop.call_count, 2)
            self.assertTrue(dispose.called)
            self.assertFalse(active[0])
        return writes, device, output.getvalue(), adapter

    def test_replay_sends_profile_order(self):
        writes, device, output, adapter = self.run_replay()
        identifiers = [struct.unpack_from('<I', raw, 4)[0] for raw in writes]
        self.assertEqual(identifiers[:6], [1, 2, 3, 1, 2, 3])
        self.assertTrue(all(len(raw) == 24 for raw in writes))
        for index, stamp in enumerate(device.sent_times[:6]):
            self.assertAlmostEqual(stamp - device.sent_times[0], index * .01, delta=.0011)
        device.ctrl_transfer.assert_any_call(0x41, 2, 0, 0, struct.pack('<II', 1, 0x10))
        self.assertIn('pending=', output)

    def test_delayed_echo_does_not_block_sequence_after_first_frame(self):
        writes, _, _, _ = self.run_replay(complete=False, duration=.075, ack_timeout=.05)
        self.assertEqual([struct.unpack_from('<I', raw, 4)[0] for raw in writes], [1, 2, 3])

    def test_missing_echo_recovers_and_continues(self):
        writes, _, output, adapter = self.run_replay(complete=False, ack_timeout=.005)
        self.assertGreater(len(writes), 1)
        self.assertGreater(adapter.stop.call_count, 2)
        self.assertIn('transmit echo timeout', output)
        self.assertIn('retrying', output)

    def test_busoff_usb_and_malformed_frames_recover(self):
        for failure in ('busoff', 'usb', 'malformed'):
            with self.subTest(failure=failure):
                writes, _, output, adapter = self.run_replay(injected=failure)
                self.assertGreater(adapter.stop.call_count, 2)
                self.assertGreater(len(writes), 3)
                self.assertIn('retrying', output)

    def test_ack_and_overflow_errors_are_reported_without_stopping(self):
        for status, message in [('ack', 'missing ACK'), ('overflow', 'overflow')]:
            with self.subTest(status=status):
                writes, _, output, adapter = self.run_replay(injected=status)
                self.assertEqual(adapter.stop.call_count, 2)
                self.assertGreater(len(writes), 3)
                self.assertIn(message, output)

    def test_missing_adapter_keeps_retrying(self):
        writes, _, output, _ = self.run_replay(absent=True)
        self.assertEqual(writes, [])
        self.assertGreater(output.count('found 0'), 1)

    def test_ctrl_c_resets_and_releases_adapter(self):
        self.run_replay(injected='interrupt')

    def test_adapter_without_hardware_timestamps(self):
        writes, _, _, _ = self.run_replay(timestamps=False)
        self.assertTrue(writes)
        self.assertTrue(all(len(raw) == 20 for raw in writes))


class ProcessControlTests(unittest.TestCase):
    def test_live_process_keeps_retrying_and_exits_on_interrupt(self):
        # Fake discovery in the child: this must never open a physical adapter.
        code = '''
import signal,sys
from unittest.mock import patch
import can_bench_emulator as e
signal.signal(signal.SIGTERM, e.interrupt)
with patch('usb.core.find', return_value=[]), patch('usb.backend.libusb1.get_backend', return_value=object()):
    sys.exit(e.main(['replay', '--profile', sys.argv[1], '--retry-delay', '0.02']))
'''
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'profile.json'
                emulator.save_profile(emulator.derive_profile(capture_frames()), path)
                child = subprocess.Popen([sys.executable, '-u', '-c', code, str(path)],
                                         cwd=Path(__file__).parent,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    # Read bytes rather than a buffered TextIOWrapper so select
                    # also observes lines already read from the OS pipe.
                    ready = b''
                    with selectors.DefaultSelector() as selector:
                        selector.register(child.stdout, selectors.EVENT_READ)
                        deadline = time.monotonic() + 5
                        while b'retrying' not in ready and time.monotonic() < deadline:
                            for key, _ in selector.select(.1):
                                import os
                                chunk = os.read(key.fd, 4096)
                                if not chunk:
                                    break
                                ready += chunk
                    self.assertIn(b'retrying', ready)
                    self.assertIsNone(child.poll())
                    child.send_signal(signum)
                    out, err = child.communicate(timeout=3)
                    self.assertEqual(child.returncode, 130)
                    self.assertIn(b'Stopped.', ready + out)
                    self.assertNotIn(b'Traceback', err)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate()


class QueueRecoveryTests(unittest.TestCase):
    def test_stale_records_drain_in_silent_loopback_without_new_transmit(self):
        import usb.core
        device = Mock()
        clock = [0.0]
        queue = [b'old-echo', b'old-internal-receive']

        def read(*args, **kwargs):
            clock[0] += .01
            if queue:
                return queue.pop(0)
            raise usb.core.USBTimeoutError('idle')

        device.read.side_effect = read
        with patch.object(emulator.time, 'monotonic', side_effect=lambda: clock[0]):
            self.assertEqual(emulator.clear_stale_queue(device, 0xf3), 2)
        self.assertEqual(device.ctrl_transfer.call_args_list,
                         [unittest.mock.call(0x41, 2, 0, 0, struct.pack('<II', 1, 0x13)),
                          unittest.mock.call(0x41, 2, 0, 0, struct.pack('<II', 0, 0))])
        device.write.assert_not_called()

    def test_nonquiescent_drain_resets_before_recovery(self):
        device = Mock()
        clock = [0.0]

        def read(*args, **kwargs):
            clock[0] += .01
            return b'continuous-records'

        device.read.side_effect = read
        with patch.object(emulator.time, 'monotonic', side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(RuntimeError, 'did not become idle'):
                emulator.clear_stale_queue(device, 0xf3)
        device.ctrl_transfer.assert_called_with(0x41, 2, 0, 0, struct.pack('<II', 0, 0))
        device.write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
