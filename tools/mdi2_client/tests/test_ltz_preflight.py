import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from mdi2.calibration_payloads import Calibration
from mdi2.calibration_transaction import TrustedContainer
from mdi2.ltz_preflight import validate_ltz_package, identify_source_calibration, HIGH_COUNTRY_F182
from mdi2.calibration_readback import parse_f182


class LtzPreflightTests(unittest.TestCase):
    def setUp(self):
        self.items = [Calibration(i, f"{i:08d}", bytes([i])) for i in range(2, 16)]
        self.reference = tuple(TrustedContainer(x.slot, x.part, hashlib.sha256(x.container).hexdigest())
                               for x in self.items)

    def validate(self):
        with patch("mdi2.ltz_preflight.load_stock_package", return_value=self.items), \
             patch("mdi2.ltz_preflight.LTZ_REFERENCE", self.reference):
            return validate_ltz_package(Path("unused"))

    def test_freezes_and_validates(self):
        mutable = bytearray(self.items[0].container)
        self.items[0] = Calibration(2, self.items[0].part, mutable)
        result = self.validate()
        mutable[0] ^= 1
        self.assertEqual(result[0].container, b"\x02")
        self.assertIsInstance(result, tuple)

    def test_changed_content_or_part_rejected(self):
        self.items[0] = Calibration(2, self.items[0].part, b"changed")
        with self.assertRaisesRegex(ValueError, "slot 02"):
            self.validate()


class SourceCalibrationTests(unittest.TestCase):
    def setUp(self):
        # Valid target containers whose slot 04 differs from the HC baseline.
        self.cals = []
        for slot, record in parse_f182(HIGH_COUNTRY_F182).items():
            data = bytearray(0x368)
            data[3] = slot
            data[6:10] = b"CSM\x00"
            data[0x362:0x364] = record[5:7]
            data[0x364] = record[1]
            data[0x365:0x368] = record[2:5]
            if slot == 4:
                data[0x365] ^= 1
            self.cals.append(Calibration(slot, str(slot), bytes(data)))
        self.cals = tuple(self.cals)

    def test_documented_high_country_source_allowed_for_ltz_target(self):
        self.assertEqual(identify_source_calibration(self.cals, HIGH_COUNTRY_F182), "High Country")

    def test_target_profile_also_allowed(self):
        from mdi2.calibration_readback import calibration_record
        response = b"\x62\xf1\x82\x0e" + b"".join(map(calibration_record, self.cals))
        self.assertEqual(identify_source_calibration(self.cals, response), "LTZ")

    def test_unknown_missing_or_duplicate_metadata_rejected(self):
        altered = bytearray(HIGH_COUNTRY_F182)
        altered[7] ^= 1
        missing = HIGH_COUNTRY_F182[:3] + b"\x0d" + HIGH_COUNTRY_F182[4:-7]
        duplicate = HIGH_COUNTRY_F182[:3] + b"\x0f" + HIGH_COUNTRY_F182[4:] + HIGH_COUNTRY_F182[4:11]
        for response in (bytes(altered), missing, duplicate):
            with self.subTest(response=response[:4]), self.assertRaises(ValueError):
                identify_source_calibration(self.cals, response)


if __name__ == "__main__":
    unittest.main()
