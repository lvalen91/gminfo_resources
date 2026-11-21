"""Offline service-channel fragmentation and connection cleanup regressions."""
import socket
import struct
import unittest
from unittest.mock import Mock, patch

from mdi2 import crypto, framing, messages
from mdi2.transport import Channel, Session

KEY = b"test-key"
CONTROL = b"\x00SP\x00\x00\x30\x00\x00"


def wire(body=b"example", counter=1):
    return framing.build_message(counter, crypto.encrypt(KEY, messages.pack_body(body)))


class ChannelTests(unittest.TestCase):
    def test_frame_survives_timeout_at_every_split(self):
        data = wire()
        for split in range(1, len(data)):
            with self.subTest(split=split):
                sock = Mock()
                sock.recv.side_effect = [data[:split], socket.timeout(),
                                         data[split:], socket.timeout()]
                channel = Channel(sock, KEY, 9052)
                self.assertEqual(channel.recv_frames(), [])
                self.assertEqual(channel.recv_frames(), [(1, b"example")])

    def test_complete_frame_returned_while_next_frame_is_partial(self):
        first, second = wire(b"first", 1), wire(b"second", 2)
        sock = Mock()
        sock.recv.side_effect = [first + second[:13], socket.timeout(),
                                 second[13:], socket.timeout()]
        channel = Channel(sock, KEY, 9052)
        self.assertEqual(channel.recv_frames(), [(1, b"first")])
        self.assertEqual(channel.recv_frames(), [(2, b"second")])

    def test_fragmented_control_and_multiple_messages(self):
        data = CONTROL + wire(b"first", 1) + CONTROL + wire(b"second", 2)
        sock = Mock()
        sock.recv.side_effect = [bytes([byte]) for byte in data] + [socket.timeout()]
        self.assertEqual(Channel(sock, KEY, 9052).recv_frames(),
                         [(1, b"first"), (2, b"second")])

    def test_rejects_bad_or_oversized_headers(self):
        for zero, length in ((1, 12), (0, 4), (0, 13), (0, 16 * 1024 * 1024 + 4)):
            with self.subTest(zero=zero, length=length):
                sock = Mock()
                sock.recv.side_effect = [struct.pack(">II", zero, length)]
                with self.assertRaises(ValueError):
                    Channel(sock, KEY, 9052).recv_frames()

    def test_eof_with_partial_frame_is_an_error(self):
        sock = Mock()
        sock.recv.side_effect = [wire()[:15], b""]
        with self.assertRaises(ConnectionError):
            Channel(sock, KEY, 9052).recv_frames()

    def test_clean_eof_after_frame(self):
        sock = Mock()
        sock.recv.side_effect = [wire(), b""]
        self.assertEqual(Channel(sock, KEY, 9052).recv_frames(), [(1, b"example")])

    def test_handshake_reassembles_fragmented_reply(self):
        sock = Mock()
        sock.recv.side_effect = [CONTROL[:3], CONTROL[3:]]
        with patch("mdi2.transport.time.sleep"):
            self.assertEqual(Channel(sock, KEY, 9052).handshake(), CONTROL)
        self.assertEqual([call.args[0] for call in sock.recv.call_args_list], [8, 5])

    def test_handshake_timeout_retains_partial_control(self):
        sock = Mock()
        sock.recv.side_effect = [CONTROL[:3], socket.timeout(),
                                 CONTROL[3:] + wire(), socket.timeout()]
        channel = Channel(sock, KEY, 9052)
        with patch("mdi2.transport.time.sleep"):
            self.assertEqual(channel.handshake(), b"")
        self.assertEqual(channel.recv_frames(), [(1, b"example")])


class SessionTests(unittest.TestCase):
    def test_connect_failure_cleans_up_before_context_entry(self):
        sock = Mock()
        session = Session(KEY, "adapter.invalid")
        with patch("mdi2.transport.socket.create_connection",
                   side_effect=[sock, OSError("synthetic connection failure")]), \
             patch.object(Channel, "handshake"):
            with self.assertRaises(OSError):
                with session.connect(ports=[9001, 9002]):
                    self.fail("context must not be entered")
        sock.close.assert_called_once()
        self.assertEqual(session.channels, {})

    def test_setup_failure_closes_current_and_existing_channels(self):
        for stage in ("setsockopt", "handshake"):
            with self.subTest(stage=stage):
                old, current = Mock(), Mock()
                session = Session(KEY, "adapter.invalid")
                session.channels[9001] = Channel(old, KEY, 9001)
                if stage == "setsockopt":
                    current.setsockopt.side_effect = OSError("synthetic setup failure")
                with patch("mdi2.transport.socket.create_connection", return_value=current), \
                     patch.object(Channel, "handshake", side_effect=OSError("synthetic handshake failure")):
                    with self.assertRaises(OSError):
                        session.connect(ports=[9002])
                current.close.assert_called_once()
                old.close.assert_called_once()
                self.assertEqual(session.channels, {})

    def test_repeated_connect_does_not_replace_open_socket(self):
        sock = Mock()
        session = Session(KEY, "adapter.invalid")
        session.channels[9001] = Channel(sock, KEY, 9001)
        with patch("mdi2.transport.socket.create_connection") as connect:
            session.connect(ports=[9001])
        connect.assert_not_called()
        self.assertIs(session.channels[9001].sock, sock)
