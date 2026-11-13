"""Offline tests for the live D-PDU adapter: send/receive, correlation, skip-None.

No real sockets. A responsive fake command socket ACKs each StartComPrimitive;
the event socket plays back captured-format 0x863 events (plus noise the adapter
must skip). These prove the strict-serialization correlation discipline in code.
"""
import socket
import struct
import unittest

from mdi2.calibration_transaction import TransactionError, UdsClient
from mdi2.live_calibration import write_ltz_calibration
from mdi2.live_programming_transport import (
    LiveDpduError, LiveDpduSession, LiveRadioAdapter,
)

RADIO_HANDLE = 0x2A000002
RX_COP = 1
REQ_CAN = 0x14DA80F1
RESP_CAN = 0x145AF180


def frame(mid, payload=b""):
    return struct.pack("<II", len(payload) + 8, mid) + payload


def radio_event(uds, *, handle=RADIO_HANDLE, cop=RX_COP, can_id=RESP_CAN, event_type=1):
    payload = bytearray(82)
    struct.pack_into("<I", payload, 0, handle)
    struct.pack_into("<I", payload, 4, event_type)
    struct.pack_into("<H", payload, 20, cop)
    payload[70:74] = can_id.to_bytes(4, "big")
    struct.pack_into("<I", payload, 74, len(uds) + 4)
    payload[78:82] = payload[70:74]
    return frame(0x863, payload + uds)


class ResponsiveCommandSocket:
    """Fake command socket: ACKs every framed command with (mid+1, status 0)."""

    def __init__(self, *, fragment=7):
        self.buffer = bytearray()
        self.fragment = fragment
        self.closed = False
        self.sent = []

    def settimeout(self, value):
        pass

    def sendall(self, data):
        self.sent.append(data)
        length, mid = struct.unpack_from("<II", data)
        self.buffer += frame(mid + 1, bytes(4))  # status word 0

    def recv(self, size):
        if not self.buffer:
            raise socket.timeout("no queued ACK")
        n = min(size, self.fragment, len(self.buffer))
        out = bytes(self.buffer[:n])
        del self.buffer[:n]
        return out

    def close(self):
        self.closed = True


class PlaybackSocket:
    def __init__(self, data=b"", *, fragment=7):
        self.data = bytearray(data)
        self.fragment = fragment
        self.closed = False

    def settimeout(self, value):
        pass

    def sendall(self, data):
        pass

    def recv(self, size):
        if not self.data:
            raise socket.timeout("event stream idle")
        n = min(size, self.fragment, len(self.data))
        out = bytes(self.data[:n])
        del self.data[:n]
        return out

    def close(self):
        self.closed = True


def make_adapter(event_bytes):
    command = ResponsiveCommandSocket()
    events = PlaybackSocket(event_bytes)
    session = LiveDpduSession(command, events)
    session.channel = 0x2A
    session._next_cop = 5
    adapter = LiveRadioAdapter(session, radio_handle=RADIO_HANDLE, receive_cop=RX_COP,
                               request_can_id=REQ_CAN, response_can_id=RESP_CAN)
    return adapter, session


class LiveAdapterTest(unittest.TestCase):
    def test_one_shot_matches_real_capture_without_nested_header(self):
        # SPS stream 317 request 135, the seed request preceding the LTZ write.
        captured = bytes.fromhex(
            "3b000000630400000600002530001025048000000600000014da80f12701"
            "0100000000010000000000000000000000040000002000014000000000")
        adapter, session = make_adapter(b"")
        session._next_cop = 0x30
        session.send_on_cop(0x25000006, REQ_CAN, b"\x27\x01")
        self.assertEqual(session.command.sent[0], captured)

    def test_setup_matches_captured_comparam_and_update_trailers(self):
        command = ResponsiveCommandSocket()
        session = LiveDpduSession(command, PlaybackSocket())
        session.channel = 0x25
        session.create_radio_cll(REQ_CAN, RESP_CAN)
        frames = [data[8:] for data in command.sent
                  if struct.unpack_from("<I", data, 4)[0] == 0x463]
        updates = [data for data in frames if data[8:10] == b"\x03\x80"]
        self.assertEqual(len(updates), 2)
        for update in updates:
            self.assertEqual(update[16:], bytes.fromhex(
                "01000000000000000000000000000000000000000000000000"))
        values = [data[8:] for data in command.sent
                  if struct.unpack_from("<I", data, 4)[0] == 0x459]
        self.assertEqual([int.from_bytes(data[30:34], "little") for data in values
                          if int.from_bytes(data[17:21], "little") == 0x19], [0x22])

    def test_round_trip_read(self):
        vin = b"1" * 17
        adapter, _ = make_adapter(radio_event(b"\x62\xf1\x90" + vin))
        adapter.send(b"\x22\xf1\x90")
        self.assertEqual(adapter.receive(4.0), b"\x62\xf1\x90" + vin)

    def test_skips_tx_confirm_and_type2_noise(self):
        vin = b"2" * 17
        noise = (radio_event(b"\x62\xf1\x90" + vin, event_type=2)       # TX/type-2 -> skip
                 + radio_event(b"\x62\xf1\x90" + vin, cop=0x99)          # other cop -> skip
                 + radio_event(b"\x62\xf1\x90" + vin))                   # the real one
        adapter, _ = make_adapter(noise)
        adapter.send(b"\x22\xf1\x90")
        self.assertEqual(adapter.receive(4.0), b"\x62\xf1\x90" + vin)

    def test_pending_then_positive(self):
        adapter, _ = make_adapter(radio_event(b"\x7f\x22\x78") + radio_event(b"\x62\xf1\x90" + b"3" * 17))
        adapter.send(b"\x22\xf1\x90")
        # 7F..78 is responsePending: the adapter returns it; UdsClient keeps waiting.
        self.assertEqual(adapter.receive(4.0), b"\x7f\x22\x78")

    def test_terminal_nrc_returned_without_teardown(self):
        # Live 2026-11-10: F18C -> 7F 22 31. The correlated NRC is the answer;
        # the tunnel must stay up so the next DID reuses the same CLL.
        vin = b"4" * 17
        adapter, session = make_adapter(radio_event(b"\x7f\x22\x31") + radio_event(b"\x62\xf1\x90" + vin))
        adapter.send(b"\x22\xf1\x8c")
        self.assertEqual(adapter.receive(4.0), b"\x7f\x22\x31")
        self.assertFalse(adapter.poisoned)
        self.assertFalse(session.closed)
        adapter.send(b"\x22\xf1\x90")
        self.assertEqual(adapter.receive(4.0), b"\x62\xf1\x90" + vin)
        self.assertFalse(adapter.poisoned)

    def test_uds_client_sees_nrc_as_transaction_error_and_link_survives(self):
        vin = b"5" * 17
        adapter, session = make_adapter(radio_event(b"\x7f\x22\x31") + radio_event(b"\x62\xf1\x90" + vin))
        client = UdsClient(adapter, timeout=4.0)
        with self.assertRaisesRegex(TransactionError, "service 22 NRC 31"):
            client.request(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertFalse(adapter.poisoned)
        self.assertFalse(session.closed)
        self.assertEqual(client.request(b"\x22\xf1\x90", b"\x62\xf1\x90"), b"\x62\xf1\x90" + vin)

    def test_uncorrelated_nrc_poisons_and_tears_down(self):
        adapter, session = make_adapter(radio_event(b"\x7f\x34\x31"))  # sid 34 while 22 in flight
        adapter.send(b"\x22\xf1\x8c")
        with self.assertRaises(LiveDpduError):
            adapter.receive(4.0)
        self.assertTrue(adapter.poisoned)
        self.assertTrue(session.closed)

    def test_wrong_prefix_poisons_and_tears_down(self):
        adapter, session = make_adapter(radio_event(b"\x62\xf1\x8c" + b"x" * 4))  # answers F18C not F190
        adapter.send(b"\x22\xf1\x90")
        with self.assertRaises(LiveDpduError):
            adapter.receive(4.0)
        self.assertTrue(adapter.poisoned)
        self.assertTrue(session.closed)

    def test_timeout_poisons(self):
        adapter, session = make_adapter(b"")  # event socket idle
        adapter.send(b"\x22\xf1\x90")
        with self.assertRaises(LiveDpduError):
            adapter.receive(0.2)
        self.assertTrue(session.closed)

    def test_two_requests_same_prefix_serialized(self):
        # Repeated 74/77-style prefixes are fine under strict serialization.
        a1 = radio_event(b"\x74\x20\x0f\xff")
        a2 = radio_event(b"\x74\x20\x0f\xff")
        adapter, _ = make_adapter(a1 + a2)
        adapter.send(b"\x34\x00\x44" + bytes(4) + bytes(4))
        self.assertEqual(adapter.receive(4.0)[:1], b"\x74")
        adapter.send(b"\x34\x00\x44" + bytes(4) + bytes(4))
        self.assertEqual(adapter.receive(4.0)[:1], b"\x74")


class StartComPrimitiveMarkerTest(unittest.TestCase):
    """The u16 after copId in 0x463 is (channel << 8) | 0x10, not a fixed 0x2510."""

    @staticmethod
    def _start_prims(channel, *, keepalive=False):
        command = ResponsiveCommandSocket()
        session = LiveDpduSession(command, PlaybackSocket())
        session.channel = channel
        if keepalive:
            session.create_keepalive_cll(0x10DBFEF1)
        else:
            session.create_radio_cll(REQ_CAN, RESP_CAN)
        return [data for data in command.sent if struct.unpack_from("<I", data, 4)[0] == 0x463]

    def test_channel_0x25_bytes_unchanged(self):
        # Vehicle-tested path: handle 0x25000002, persistent RX cop 1, marker 0x2510.
        # Full frame pinned as a literal so any drift on the tested path fails here.
        frames = self._start_prims(0x25)
        self.assertEqual(frames[0], bytes.fromhex(
            "450000006304000002000025010010250480000000000000"
            "010000000000000000ffffffff0000000004000000a00100000100000000000000342500000000000000000000"))
        for data in frames:
            handle, cop, marker = struct.unpack_from("<IHH", data, 8)
            self.assertEqual(handle, 0x25000002)
            self.assertEqual(marker, 0x2510)
        self.assertEqual([struct.unpack_from("<H", d, 12)[0] for d in frames], [1, 2, 3, 4])

    def test_channel_0x1e_matches_wip_capture(self):
        # mdi2_direct_client_WIP capture, channel 0x1E: marker is 0x1E10, trailer bytes
        # (incl. the 0x2534 word) are identical to the 0x25 stream -> only the marker moves.
        captured = [
            "630400000200001e0100101e0480000000000000010000000000000000ffffffff0000000004000000"
            "a00100000100000000000000342500000000000000000000",
            "630400000200001e0200101e01800000000000000100000000000000000000000000000000040000000000000000000000",
            "630400000200001e0300101e038000000000000001000000000000000000000000000000000000000000000000",
            "630400000200001e0400101e038000000000000001000000000000000000000000000000000000000000000000",
        ]
        expected = [struct.pack("<I", len(h) // 2 + 4) + bytes.fromhex(h) for h in captured]
        self.assertEqual(self._start_prims(0x1E), expected)

    def test_other_channel_derives_marker(self):
        for keepalive in (False, True):
            frames = self._start_prims(0x2C, keepalive=keepalive)
            self.assertTrue(frames)
            for data in frames:
                handle, cop, marker = struct.unpack_from("<IHH", data, 8)
                self.assertEqual(handle >> 24, 0x2C)
                self.assertEqual(marker, (0x2C << 8) | 0x10)
                self.assertEqual(marker, 0x2C10)
        self.assertEqual(frames[-1][8 + 16:8 + 22], b"\x10\xdb\xfe\xf1\x3e\x80")


class WriteGateTest(unittest.TestCase):
    def test_write_requires_confirmation(self):
        with self.assertRaises(ValueError):
            write_ltz_calibration(__import__("pathlib").Path("/nonexistent"),
                                  12345, b"1" * 17, confirmed=False)


if __name__ == "__main__":
    unittest.main()
