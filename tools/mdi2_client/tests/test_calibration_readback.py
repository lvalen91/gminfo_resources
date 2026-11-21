import unittest

from mdi2.calibration_payloads import Calibration
from mdi2.calibration_readback import compare_post_reboot


class CalibrationReadbackTests(unittest.TestCase):
    def setUp(self):
        self.calibrations = []
        records = []
        for slot in range(2, 16):
            container = bytearray(0x368)
            container[3] = slot
            container[6:10] = b"CSM\x00"
            container[0x362:0x364] = b"AA"
            container[0x364] = 5
            container[0x365:0x368] = bytes([0, 0, slot])
            self.calibrations.append(Calibration(slot, f"{slot:08d}", bytes(container)))
            records.append(bytes([slot, 5, 0, 0, slot]) + b"AA")
        self.f182 = b"\x62\xf1\x82\x0e" + b"".join(records)
        self.pec = bytes.fromhex("62 f0 f1 00 00")
        self.bis = bytes.fromhex("62 f0 f2 00 00")

    def test_matching_metadata_and_statuses(self):
        result = compare_post_reboot(self.calibrations, self.f182, self.pec, self.bis)
        self.assertEqual(result.matching_slots, tuple(range(2, 16)))
        self.assertEqual(result.mismatching_slots, ())
        self.assertEqual(result.programming_error_count, b"\x00\x00")

    def test_changed_cvn_is_reported(self):
        data = bytearray(self.f182)
        data[8] ^= 1
        result = compare_post_reboot(self.calibrations, bytes(data), self.pec, self.bis)
        self.assertEqual(result.mismatching_slots, (2,))

    def test_truncated_data_and_invalid_status_are_rejected(self):
        with self.assertRaises(ValueError):
            compare_post_reboot(self.calibrations, self.f182[:-1], self.pec, self.bis)
        with self.assertRaises(ValueError):
            compare_post_reboot(self.calibrations, self.f182, self.pec[:-1], self.bis)


if __name__ == "__main__":
    unittest.main()
