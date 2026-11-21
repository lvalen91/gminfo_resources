"""Beacon decode + auto-resolve contract (no hardware, no real serial)."""
import struct
import unittest

from mdi2.discovery import decode_beacon, DeviceInfo


def _beacon(serial: int, length: int = 41) -> bytes:
    """Synthetic announce beacon with `serial` as LE u32 at byte offset 9."""
    b = bytearray(length)
    struct.pack_into("<I", b, 9, serial)
    return bytes(b)


class DecodeBeaconTests(unittest.TestCase):
    def test_offset9_le_u32(self):
        self.assertEqual(decode_beacon(_beacon(0x01020304)), 0x01020304)

    def test_full_u32_range(self):
        self.assertEqual(decode_beacon(_beacon(0xFFFFFFFF)), 0xFFFFFFFF)
        self.assertEqual(decode_beacon(_beacon(0)), 0)

    def test_minimum_length_is_13(self):
        # exactly offset(9)+4 bytes must decode; one short must raise.
        self.assertEqual(decode_beacon(_beacon(0xAABBCCDD, length=13)), 0xAABBCCDD)
        with self.assertRaises(ValueError):
            decode_beacon(b"\x00" * 12)

    def test_rejects_non_bytes(self):
        with self.assertRaises(ValueError):
            decode_beacon(None)  # type: ignore[arg-type]

    def test_deviceinfo_is_frozen(self):
        info = DeviceInfo(ip="192.168.171.2", serial=1, beacon=b"\x00" * 13)
        with self.assertRaises(Exception):
            info.serial = 2  # type: ignore[misc]


class ResolveTargetTests(unittest.TestCase):
    def test_both_explicit_skips_network(self):
        # _resolve_target must not touch the network when both are provided;
        # if it did, importing/calling here (no device) would block/raise.
        from mdi2.live_calibration import _resolve_target
        self.assertEqual(_resolve_target(1234, "10.0.0.9"), (1234, "10.0.0.9"))


if __name__ == "__main__":
    unittest.main()
