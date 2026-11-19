import contextlib
import errno
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import radio_on as radio
import radio_owner as locks


class Input(io.StringIO):
    def __init__(self, response='', interactive=True):
        super().__init__(response)
        self.interactive = interactive

    def isatty(self):
        return self.interactive


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir='/tmp')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def start_owner(self):
        program = '''
import signal
import sys
import time
from pathlib import Path
from radio_owner import exclusive_owner
stopping = []
signal.signal(signal.SIGTERM, lambda *_: stopping.append(True))
with exclusive_owner(Path(sys.argv[1])) as owner:
    print('ready', flush=True)
    while not stopping:
        owner.poll()
        time.sleep(.002)
print('received SIGTERM', flush=True)
'''
        child = subprocess.Popen([sys.executable, '-c', program, str(self.directory)],
                                 cwd=Path(__file__).parent, stdout=subprocess.PIPE, text=True)

        def finish():
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            child.stdout.close()

        self.addCleanup(finish)
        self.assertEqual(child.stdout.readline(), 'ready\n')
        return child

    def test_current_owner_noninteractive(self):
        child = self.start_owner()
        with patch.object(sys, 'stdin', Input(interactive=False)):
            with self.assertRaisesRegex(RuntimeError, f'PID {child.pid}.*Noninteractive'):
                with locks.exclusive_owner(self.directory):
                    self.fail('lock acquired from a running owner')
        self.assertIsNone(child.poll())

    def test_declined_termination(self):
        child = self.start_owner()
        with patch.object(sys, 'stdin', Input('n\n')), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'declined'):
                with locks.exclusive_owner(self.directory):
                    self.fail('lock acquired after declined termination')
        self.assertIsNone(child.poll())

    def test_verified_owner_cooperatively_signals_itself_and_releases(self):
        child = self.start_owner()
        with patch.object(sys, 'stdin', Input('yes\n')), contextlib.redirect_stderr(io.StringIO()):
            with locks.exclusive_owner(self.directory):
                record = json.loads((self.directory / 'owner.lock').read_bytes())
                self.assertEqual(record['pid'], os.getpid())
                self.assertEqual((self.directory / 'owner.lock').stat().st_mode & 0o777, 0o600)
        self.assertEqual(child.stdout.readline(), 'received SIGTERM\n')
        self.assertEqual((self.directory / 'owner.lock').stat().st_size, 0)

    def test_stale_unlocked_record_and_socket_from_crash(self):
        record = self.directory / 'owner.lock'
        fd = os.open(record, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(dict(pid=1, start='outdated', token='bad'), handle)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as stale:
            stale.bind(str(self.directory / 'control'))
        with patch.object(locks, 'request_handoff', side_effect=AssertionError):
            with locks.exclusive_owner(self.directory):
                self.assertEqual(json.loads(record.read_bytes())['pid'], os.getpid())

    def test_held_lock_with_dead_or_reused_pid(self):
        self.start_owner()
        for replacement in (None, 'different start'):
            with self.subTest(identity=replacement), patch.object(locks, 'process_start', return_value=replacement):
                with patch.object(locks, 'request_control', side_effect=AssertionError):
                    with self.assertRaisesRegex(RuntimeError, 'stale owner identity'):
                        with locks.exclusive_owner(self.directory):
                            self.fail('PID mismatch permitted takeover')

    def test_recheck_after_confirmation(self):
        child = self.start_owner()
        original = locks.process_start(child.pid)
        with patch.object(locks, 'process_start', side_effect=[original, None]):
            with patch.object(sys, 'stdin', Input('yes\n')), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                    with locks.exclusive_owner(self.directory):
                        self.fail('identity changed')
        self.assertIsNone(child.poll())


class UsbError(OSError):
    pass


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.device = Mock()
        self.device.ctrl_transfer.side_effect = lambda request_type, num, value, index, data, **kw: len(data)
        self.adapter = Mock()
        self.adapter.device_capability.feature = 0x13
        self.usb = SimpleNamespace(core=SimpleNamespace(find=Mock(return_value=[self.device]),
                                                        USBError=UsbError, USBTimeoutError=TimeoutError),
                                   util=Mock())
        self.modules = self.usb, Mock(return_value=self.adapter), object()
        self.bench = Mock()
        self.frame = SimpleNamespace(can_id=0x529, data=b'test12')
        self.keepalive = SimpleNamespace(frames=[self.frame], period=.32)
        self.stop = radio.Stop()
        self.owner = Mock()
        self.totals = radio.Totals()

    def test_unsupported_drain_does_not_start_controller(self):
        self.adapter.device_capability.feature = 1
        with self.assertRaisesRegex(RuntimeError, 'silent loopback'):
            with radio.canable(self.bench, self.modules):
                self.fail('entered normal controller mode')
        self.bench.clear_stale_queue.assert_not_called()
        self.assertTrue(all(call.args[4][0] == 0 for call in self.device.ctrl_transfer.call_args_list
                            if call.args[1] == 2))
        self.usb.util.release_interface.assert_called_once_with(self.device, 0)

    def test_usb_busy_does_not_reset_unclaimed_controller(self):
        self.usb.util.claim_interface.side_effect = UsbError(errno.EBUSY, 'busy')
        with self.assertRaisesRegex(RuntimeError, 'foreign owner PID unknown'):
            with radio.canable(self.bench, self.modules):
                self.fail('unclaimed controller started')
        self.device.ctrl_transfer.assert_not_called()
        self.usb.util.release_interface.assert_not_called()
        self.usb.util.dispose_resources.assert_called_once()

    def test_stale_queue_drain_failure(self):
        self.bench.clear_stale_queue.side_effect = RuntimeError('queue did not become idle')
        with self.assertRaisesRegex(RuntimeError, 'queue did not become idle'):
            with radio.canable(self.bench, self.modules):
                self.fail('started after drain failure')
        self.assertFalse(any(c.args[1] == 2 and c.args[4][0] == 1
                             for c in self.device.ctrl_transfer.call_args_list))

    def test_drain_claim_and_release(self):
        with radio.canable(self.bench, self.modules) as (dev, size, timeout):
            self.assertIs(dev, self.device)
            self.assertIs(timeout, TimeoutError)
            self.assertEqual(size, 24)
        self.adapter.set_bitrate.assert_called_once_with(500000)
        self.assertEqual(self.bench.clear_stale_queue.call_count, 2)
        self.bench.clear_stale_queue.assert_called_with(self.device, 0x13)
        self.assertEqual(self.device.ctrl_transfer.call_args.args[4], bytes(8))
        self.usb.util.release_interface.assert_called_once()

    def packet(self, echo):
        return radio.PACKET.pack(echo, self.frame.can_id, 6, 0, 0, 0, self.frame.data)

    def error_packet(self, bits):
        return radio.PACKET.pack(radio.RX_MARKER, 0x20000000 | bits,
                                 0, 0, 0, 0, b'')

    def run_keepalive(self):
        events = radio.scheduled_events('keepalive', None, None, self.keepalive)
        radio.transmit((self.device, 20, TimeoutError), events, self.owner,
                       self.stop, self.totals)

    def test_unique_echo_ids_and_inflight_drain_after_stop(self):
        packets = iter((self.packet(radio.RX_MARKER), self.packet(0), self.packet(1)))
        times = iter((0., 0., 0., 0., .1, .1, .2, .2, .321, .321, .321, .321))
        def read(*_args, **_kwargs):
            if self.totals.admitted == 1 and self.totals.queued == 1:
                raise TimeoutError
            if self.totals.queued == 2:
                self.stop.handle(signal.SIGINT, None)
            return next(packets)
        self.device.read.side_effect = read
        self.device.write.return_value = 20
        with patch.object(radio.time, 'monotonic', side_effect=times):
            self.run_keepalive()
        self.assertEqual(self.totals, radio.Totals(queued=2, admitted=2, bus_rx=1))
        self.assertEqual([call.args[1] for call in self.device.write.call_args_list],
                         [self.packet(0), self.packet(1)])

    def test_missing_echo_times_out_with_only_one_pending(self):
        self.device.write.return_value = 20
        self.device.read.side_effect = TimeoutError
        with patch.object(radio.time, 'monotonic', side_effect=[0., 0., 0., 0., 1., 1., 2.1]):
            with self.assertRaisesRegex(RuntimeError, 'admission echo timed out'):
                self.run_keepalive()
        self.assertEqual(self.totals, radio.Totals(queued=1))

    def test_unexpected_echo_is_not_an_admission(self):
        self.device.write.return_value = 20
        self.device.read.return_value = self.packet(5)
        with self.assertRaisesRegex(RuntimeError, 'unexpected CANable'):
            self.run_keepalive()
        self.assertEqual(self.totals.admitted, 0)

    def test_wakeup_can_error_does_not_replace_admission_echo(self):
        self.device.write.return_value = 20
        self.device.read.side_effect = [self.error_packet(0x20), self.packet(0)]
        radio.transmit((self.device, 20, TimeoutError), iter([(0.0, self.frame)]),
                       self.owner, self.stop, self.totals)
        self.assertEqual(self.totals.queued, 1)
        self.assertEqual(self.totals.admitted, 1)
        self.assertEqual(self.totals.can_errors, 1)

    def test_bus_off_aborts(self):
        self.device.write.return_value = 20
        self.device.read.return_value = self.error_packet(0x40)
        with self.assertRaisesRegex(RuntimeError, 'bus-off'):
            radio.transmit((self.device, 20, TimeoutError), iter([(0.0, self.frame)]),
                           self.owner, self.stop, self.totals)

    def test_short_write_reports_uncertain_admission(self):
        self.device.write.return_value = 10
        with self.assertRaisesRegex(OSError, 'short USB CAN write'):
            self.run_keepalive()
        self.assertTrue(self.totals.uncertain_write)
        self.assertEqual(self.totals.queued, 0)

    def test_each_preview_avoids_usb_and_lock(self):
        with patch.object(radio, 'usb_modules', side_effect=AssertionError):
            with patch.object(radio, 'exclusive_owner', side_effect=AssertionError):
                for mode in radio.MODES:
                    with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()) as out:
                        self.assertEqual(radio.main([mode, '--dry-run']), 0)
                        self.assertIn('Zero frames sent.', out.getvalue())
                        self.assertIn('126 startup frames' if mode.startswith('startup') else
                                      ('32 frames' if mode == 'full' else 'one keepalive'), out.getvalue())

    def test_fixed_mode_event_shapes(self):
        a = SimpleNamespace(can_id=0x145, data=b'a')
        k = SimpleNamespace(can_id=0x529, data=b'k')
        profile = SimpleNamespace(frames=(a, k), offsets=(0.0, 0.2), period=0.5)
        startup = SimpleNamespace(frames=(a, k, k), offsets=(0.0, 39.9, 40.1))
        keepalive = SimpleNamespace(frames=(k,), period=0.5)
        full = radio.scheduled_events('full', profile, startup, keepalive)
        self.assertEqual([(next(full)[0]) for _ in range(5)], [0.0, 0.2, 0.5, 0.7, 1.0])
        once = list(radio.scheduled_events('startup', profile, startup, keepalive))
        self.assertEqual([value for value, _ in once], [0.0, 39.9])
        combined = radio.scheduled_events('startup-keepalive', profile, startup, keepalive)
        self.assertEqual([next(combined)[0] for _ in range(5)], [0.0, 39.9, 40.0, 40.5, 41.0])


if __name__ == '__main__':
    unittest.main()

