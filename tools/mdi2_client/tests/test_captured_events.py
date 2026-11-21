import struct
import unittest

from mdi2.captured_events import parse_radio_rx
from mdi2.calibration_payloads import Calibration, transfer_requests


class CapturedEventTests(unittest.TestCase):
    def event(self, uds=b"\x62\xf1\x82"):
        payload = bytearray(82)
        struct.pack_into("<II", payload, 0, 0x123, 1)
        struct.pack_into("<H", payload, 20, 7)
        payload[70:74] = bytes.fromhex("145af180")
        struct.pack_into("<I", payload, 74, 4 + len(uds))
        payload[78:82] = payload[70:74]
        return payload + uds

    def parse(self, payload):
        return parse_radio_rx(payload, handle=0x123, cop=7, can_id=0x145AF180)

    def test_can_id_bytes_inside_uds_are_not_truncated(self):
        uds = b"\x62\xf1\x82" + bytes.fromhex("145af180") + b"\x01"
        self.assertEqual(self.parse(self.event(uds)), uds)

    def test_padded_short_cll_single_frame_is_unwrapped(self):
        # Poll/keepalive CLL wraps short UDS as an ISO-TP single frame
        # [SF-len][UDS][0x55 pad]; the PCI byte and padding must be stripped.
        frame = b"\x04\x62\xf1\xb0\x80\x55\x55\x55"  # 62 F1 B0 80, padded to 7
        self.assertEqual(self.parse(self.event(frame)), b"\x62\xf1\xb0\x80")

    def test_exact_fit_cll_raw_uds_is_returned_unchanged(self):
        # Exact-fit CLL carries raw UDS whose first byte is a response SID
        # (>=0x40, never 0x01..0x07): returned as-is even when short.
        for uds in (b"\x62\xf1\xb0\x80", b"\x50\x03\x00\x64\x01\xf4",
                    b"\x7f\x27\x78", b"\x67\x02", b"\x77"):
            with self.subTest(uds=uds):
                self.assertEqual(self.parse(self.event(uds)), uds)

    def test_single_frame_without_full_0x55_padding_is_not_stripped(self):
        # Only a genuine SF-len + all-0x55 tail is unwrapped; anything else is raw.
        raw = b"\x04\x62\xf1\xb0\x80\x55\x00\x55"
        self.assertEqual(self.parse(self.event(raw)), raw)

    def test_truncated_or_inconsistent_receive_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "length"):
            self.parse(self.event()[:-1])
        with self.assertRaisesRegex(ValueError, "length"):
            self.parse(self.event()[:81])
        with self.assertRaisesRegex(ValueError, "length"):
            self.parse(self.event()[:76])
        event = self.event()
        event[81] ^= 1
        with self.assertRaisesRegex(ValueError, "identifiers"):
            self.parse(event)

    def test_other_events_are_not_responses(self):
        event = self.event()
        struct.pack_into("<I", event, 4, 2)
        self.assertIsNone(self.parse(event))
        self.assertIsNone(self.parse(bytes(37)))
        self.assertIsNone(parse_radio_rx(self.event(), handle=1, cop=7, can_id=0x145AF180))

    def test_invalid_transfer_limit_rejected_before_first_request(self):
        for limit in (20.5, True, 2):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                next(transfer_requests(Calibration(2, "00000002", b"x"), limit))


if __name__ == "__main__":
    unittest.main()
