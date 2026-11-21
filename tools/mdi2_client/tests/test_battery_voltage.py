import struct
import unittest

from mdi2.battery_voltage import read_battery_mv


class FakeSocket:
    def __init__(self, response):
        self.response = bytearray(response)
        self.sent = []
        self.closed = False

    def settimeout(self, value):
        pass

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        chunk = bytes(self.response[:min(size, 3)])
        del self.response[:len(chunk)]
        return chunk

    def close(self):
        self.closed = True


class BatteryVoltageTests(unittest.TestCase):
    def response(self, mv=12601, *, status=0, mid=0x468):
        payload = struct.pack("<I", status) + bytes(18) + struct.pack("<I", mv)
        return struct.pack("<II", 34, mid) + payload

    def test_fragmented_response_and_exact_ioctl(self):
        sock = FakeSocket(self.response())
        self.assertEqual(read_battery_mv(sock), 12601)
        self.assertEqual(sock.sent, [struct.pack("<II", 17, 0x467) + bytes.fromhex("ffffffff0600000000")])
        self.assertFalse(sock.closed)

    def test_invalid_status_or_truncated_response_closes_socket(self):
        for response in (self.response(status=1), self.response()[:-1], self.response(mid=0x999)):
            with self.subTest(response_length=len(response)):
                sock = FakeSocket(response)
                with self.assertRaises((ValueError, ConnectionError)):
                    read_battery_mv(sock)
                self.assertTrue(sock.closed)

    def test_invalid_timeout_sends_nothing(self):
        sock = FakeSocket(self.response())
        with self.assertRaises(ValueError):
            read_battery_mv(sock, timeout=float("nan"))
        self.assertEqual(sock.sent, [])


if __name__ == "__main__":
    unittest.main()
