import socket
import struct
import unittest

from mdi2.programming_adapter_simulation import AdapterError, SimulatedProgrammingAdapter


def frame(mid, payload=b""):
    return struct.pack("<II", len(payload) + 8, mid) + payload


def radio_event(uds):
    payload = bytearray(82)
    struct.pack_into("<II", payload, 0, 0x01000006, 1)
    struct.pack_into("<H", payload, 20, 0x29)
    payload[70:74] = bytes.fromhex("145af180")
    struct.pack_into("<I", payload, 74, len(uds) + 4)
    payload[78:82] = payload[70:74]
    return frame(0x863, payload + uds)


class FakeSocket:
    def __init__(self, incoming=b"", *, fragment=3, fail_send=False):
        self.incoming = bytearray(incoming)
        self.fragment = fragment
        self.fail_send = fail_send
        self.sent = []
        self.closed = False

    def settimeout(self, value):
        pass

    def sendall(self, data):
        if self.fail_send:
            raise TimeoutError("ambiguous partial send")
        self.sent.append(data)

    def recv(self, size):
        if not self.incoming:
            raise socket.timeout("injected timeout")
        size = min(size, self.fragment)
        result = bytes(self.incoming[:size])
        del self.incoming[:size]
        return result

    def close(self):
        self.closed = True


class AdapterSimulationTests(unittest.TestCase):
    def make(self, *, command=None, events=None, **overrides):
        command = command if command is not None else FakeSocket()
        events = events if events is not None else FakeSocket()
        kwargs = dict(radio_handle=0x01000006, keepalive_handle=0x01000007,
                      receive_cop=0x29, first_free_cop=0x2a,
                      reserved_cops=frozenset({0x29, 0x2b}),
                      request_can_id=0x14da80f1, response_can_id=0x145af180,
                      functional_can_id=0x10dbfef1,
                      assume_fresh_ordered_no_late_events=True, simulation_only=True)
        kwargs.update(overrides)
        return SimulatedProgrammingAdapter(command, events, **kwargs)

    def test_rejects_missing_assumption_and_real_os_socket(self):
        with self.assertRaises(ValueError):
            self.make(simulation_only=False)
        with self.assertRaises(Exception):
            self.make(assume_fresh_ordered_no_late_events=False)
        left, right = socket.socketpair()
        try:
            with self.assertRaisesRegex(ValueError, "fake sockets"):
                self.make(command=left)
        finally:
            left.close()
            right.close()

    def test_fragmented_ack_pending_and_captured_teardown(self):
        ack = frame(0x464, bytes(4))
        command = FakeSocket(ack + ack + frame(0x452, bytes(4)) +
                             frame(0x462, bytes(8)) + frame(0x452, bytes(4)))
        events = FakeSocket(frame(1505) + radio_event(b"\x7f\x34\x78") +
                            radio_event(b"\x74\x20\x0f\xff"))
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        adapter.send(b"\x34\x00\x44")
        self.assertEqual(adapter.receive(1), b"\x7f\x34\x78")
        self.assertEqual(adapter.receive(1), b"\x74\x20\x0f\xff")
        adapter.close()
        self.assertTrue(command.closed and events.closed)
        self.assertEqual([struct.unpack_from("<I", x, 4)[0] for x in command.sent],
                         [0x463, 0x463, 0x451, 0x461, 0x451])
        self.assertEqual(struct.unpack_from("<H", command.sent[0], 12)[0], 0x2a)
        self.assertEqual(struct.unpack_from("<H", command.sent[1], 12)[0], 0x2c)

    def test_ambiguous_send_or_receive_closes_and_forbids_retry(self):
        command = FakeSocket(frame(0x464, bytes(4)))
        events = FakeSocket()
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        command.fail_send = True
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            adapter.send(b"\x34\x00\x44")
        self.assertTrue(adapter.poisoned and command.closed and events.closed)
        with self.assertRaises(AdapterError):
            adapter.send(b"\x34\x00\x44")

        command = FakeSocket(frame(0x464, bytes(4)) * 2)
        events = FakeSocket()
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        adapter.send(b"\x34\x00\x44")
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            adapter.receive(0.01)
        with self.assertRaises(AdapterError):
            adapter.send(b"\x34\x00\x44")

    def test_malformed_status_counter_and_event_fail_closed(self):
        for data in (radio_event(b"\x76\x02"), frame(0x863, bytes(37)),
                     struct.pack("<II", 1, 0x863)):
            command = FakeSocket(frame(0x464, bytes(4)) * 2)
            events = FakeSocket(data)
            adapter = self.make(command=command, events=events)
            adapter.start_keepalive()
            adapter.send(b"\x36\x01\x00")
            with self.subTest(data=data[:8]), self.assertRaises(AdapterError):
                adapter.receive(1)
            self.assertTrue(adapter.poisoned and adapter.closed)

    def test_terminal_nrc_returned_without_poisoning(self):
        # Correlated 7F 22 31 is handed to UdsClient as-is; the adapter stays
        # usable and the next request on the same link succeeds.
        command = FakeSocket(frame(0x464, bytes(4)) * 3)
        events = FakeSocket(radio_event(b"\x7f\x22\x31") +
                            radio_event(b"\x62\xf1\x90" + b"1" * 17))
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        adapter.send(b"\x22\xf1\x8c")
        self.assertEqual(adapter.receive(1), b"\x7f\x22\x31")
        self.assertFalse(adapter.poisoned or adapter.closed)
        adapter.send(b"\x22\xf1\x90")
        self.assertEqual(adapter.receive(1), b"\x62\xf1\x90" + b"1" * 17)
        self.assertFalse(adapter.poisoned or adapter.closed)

    def test_uncorrelated_nrc_still_poisons(self):
        # 7F 34 xx while 22 is in flight is not ours: fail closed as before.
        command = FakeSocket(frame(0x464, bytes(4)) * 2)
        events = FakeSocket(radio_event(b"\x7f\x34\x31"))
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        adapter.send(b"\x22\xf1\x8c")
        with self.assertRaisesRegex(AdapterError, "negative response"):
            adapter.receive(1)
        self.assertTrue(adapter.poisoned and adapter.closed)

    def test_failed_teardown_never_sends_later_steps(self):
        command = FakeSocket(frame(0x464, bytes(4)) + frame(0x452, b"\x01\x00\x00\x00"))
        events = FakeSocket()
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        with self.assertRaisesRegex(AdapterError, "teardown"):
            adapter.close()
        self.assertTrue(adapter.poisoned and command.closed and events.closed)
        self.assertEqual([struct.unpack_from("<I", x, 4)[0] for x in command.sent],
                         [0x463, 0x451])

    def test_reserved_cop_exhaustion_closes_without_sending(self):
        command = FakeSocket()
        events = FakeSocket()
        adapter = self.make(command=command, events=events, first_free_cop=0xffff,
                            reserved_cops=frozenset({0x29, 0xffff}))
        with self.assertRaisesRegex(AdapterError, "COP identifier space exhausted"):
            adapter.start_keepalive()
        self.assertEqual(command.sent, [])
        self.assertTrue(command.closed and events.closed)

    def test_assumption_limit_late_duplicate_is_indistinguishable(self):
        ack = frame(0x464, bytes(4))
        command = FakeSocket(ack * 3)
        old = radio_event(b"\x74\x20\x0f\xff")
        events = FakeSocket(old + old)
        adapter = self.make(command=command, events=events)
        adapter.start_keepalive()
        adapter.send(b"\x34\x00\x44")
        adapter.receive(1)
        adapter.send(b"\x34\x00\x44")
        # A duplicated prior response is byte-identical to a fresh response.
        # This deliberately demonstrates why this adapter is simulation-only.
        self.assertEqual(adapter.receive(1), b"\x74\x20\x0f\xff")


if __name__ == "__main__":
    unittest.main()
