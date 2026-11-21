import contextlib
import io
import queue
import struct
import threading
from types import SimpleNamespace
import unittest

import boot_radio_elk as elk


class KeepaliveValidationTests(unittest.TestCase):
    def profile(self, ids=(0x145, 0x529), period=0.320270):
        frames = tuple(SimpleNamespace(can_id=value, data=b'') for value in ids)
        return SimpleNamespace(frames=frames, period=period)

    def test_exactly_one_keepalive_at_documented_cadence(self):
        frame = elk.validate_keepalive(self.profile())
        self.assertEqual(frame.can_id, 0x529)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            elk.validate_keepalive(self.profile(ids=(0x145,)))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            elk.validate_keepalive(self.profile(ids=(0x529, 0x529)))
        with self.assertRaisesRegex(ValueError, 'cadence'):
            elk.validate_keepalive(self.profile(period=0.5))


class ReplayReadinessTests(unittest.TestCase):
    def setUp(self):
        self.raw = b''

        def read(_device, _endpoint, _size, *_args, **_kwargs):
            return self.raw

        usb = SimpleNamespace(core=SimpleNamespace(Device=SimpleNamespace(read=read)))
        self.transport = elk.CanDiagnostics(
            usb, threading.Event(), threading.Event(), 0.320270)
        self.device = object()

    def record(self, echo, ident, data=b''):
        self.raw = struct.pack('<IIBBBB8s', echo, ident, len(data),
                               0, 0, 0, data)
        return self.transport.observe(self.device, 0x81, 20)

    def test_only_standard_529_replay_echo_satisfies_readiness(self):
        aliases = (
            (1, 0x145),            # unrelated replay frame
            (0x70000000, 0x529),   # diagnostic echo namespace
            (1, 0x80000529),       # extended-frame flag with same low ID
            (1, 0x40000529),       # RTR flag with same low ID
            (1, 0x20000529),       # CAN error record
        )
        for echo, ident in aliases:
            with self.subTest(echo=echo, ident=ident):
                self.record(echo, ident)
                self.assertFalse(self.transport.ready.is_set())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.record(1, 0x529)
            self.record(2, 0x529)
        self.assertTrue(self.transport.ready.is_set())
        self.assertEqual(output.getvalue().count('Captured 0x529 keepalive active'), 1)

    def test_extended_diagnostic_response_routing_is_unchanged(self):
        payload = bytes.fromhex('027e00')
        self.record(0xFFFFFFFF, 0x80000000 | elk.CanDiagnostics.RESPONSE_ID, payload)
        self.assertEqual(
            self.transport.responses[elk.CanDiagnostics.RESPONSE_ID].get_nowait(), payload)
        with self.assertRaises(queue.Empty):
            self.transport.responses[elk.CanDiagnostics.RESPONSE_ID].get_nowait()


if __name__ == '__main__':
    unittest.main()

