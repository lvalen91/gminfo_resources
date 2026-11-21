"""Offline tests for mdi2.ecu_catalog against the bundled data files."""
import unittest

from mdi2.ecu_catalog import EcuCatalog


class EcuCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = EcuCatalog()

    def test_counts(self):
        self.assertEqual(len(self.cat.ecus), 24)
        self.assertGreaterEqual(len(self.cat.dids), 27)
        self.assertEqual(len(self.cat.routines), 4)

    def test_ecu_lookup_by_addr_and_name(self):
        radio = self.cat.ecu(0x80)
        self.assertIsNotNone(radio)
        self.assertEqual(radio.name, "Radio")
        self.assertEqual(radio.can_req, 0x14DA80F1)
        self.assertEqual(radio.can_rsp, 0x145AF180)
        self.assertEqual(radio.domain, "0114AC")
        self.assertEqual(self.cat.ecu("radio"), radio)
        self.assertEqual(self.cat.ecu("RADIO"), radio)

    def test_tester_addr(self):
        self.assertEqual(self.cat.tester_addr, 0xF1)

    def test_gateway_flag(self):
        self.assertTrue(self.cat.ecu(0x45).gateway)
        self.assertFalse(self.cat.ecu(0x80).gateway)

    def test_unknown_lookups(self):
        self.assertIsNone(self.cat.ecu(0xEE))
        self.assertIsNone(self.cat.ecu("NoSuchModule"))
        self.assertEqual(self.cat.ecu_name(0xEE), "Unknown(0xEE)")

    def test_did_metadata_and_decode(self):
        self.assertEqual(self.cat.did_name(0xF190), "VIN")
        self.assertEqual(self.cat.decode(0xF190, b"PLACEHOLDERVIN0001"), "PLACEHOLDERVIN0001")
        # bcd_date F199
        self.assertEqual(self.cat.decode(0xF199, bytes.fromhex("20261108")), "2026-11-08")
        # ecuid formatting
        self.assertEqual(self.cat.decode(0xF0F3, bytes(range(4))), "00010203")
        # unknown DID falls back to hex
        self.assertEqual(self.cat.did_name(0x1234), "DID_1234")
        self.assertEqual(self.cat.decode(0x1234, b"\xab\xcd"), "ABCD")

    def test_routine_name(self):
        self.assertEqual(self.cat.routine_name(0xFF02), "eraseMemory")
        self.assertEqual(self.cat.routine_name(0x0000), "RID_0000")

    def test_can_id_invariants_all_ecus(self):
        # R1: per-ECU CAN addressing invariants over all 24 catalog modules.
        #   can_req == 0x14DA0000 | (addr<<8) | 0xF1
        #   (can_rsp & 0xFFFF) == 0xF100 | addr   (low 16 bits always 0xF1<ecu>)
        self.assertEqual(len(self.cat.ecus), 24)
        for addr, info in self.cat.ecus.items():
            self.assertEqual(info.can_req, 0x14DA0000 | (addr << 8) | 0xF1,
                             f"can_req wrong for 0x{addr:02X}")
            self.assertEqual(info.can_rsp & 0xFFFF, 0xF100 | addr,
                             f"can_rsp low-16 wrong for 0x{addr:02X}")

    def test_hvac_can_rsp_pinned(self):
        # R1: HVAC 0x68 response id must be 0x145AF168 (was a 0x141A typo).
        self.assertEqual(self.cat.ecu(0x68).can_rsp, 0x145AF168)

    def test_gateway_only_uses_da_pf_byte(self):
        # The 0xDA PF byte in a response id is the gateway form; only the gateway
        # (0x45) may carry it. All others use a module-specific 0x5A/1A/4A/2A.
        for addr, info in self.cat.ecus.items():
            pf = (info.can_rsp >> 16) & 0xFF
            if pf == 0xDA:
                self.assertTrue(info.gateway, f"0x{addr:02X} has 0xDA PF but is not gateway")

    def test_no_secret_values_in_data(self):
        # Protocol identifiers only -- no 17-char VIN values in any ECU/DID name.
        for info in self.cat.ecus.values():
            self.assertNotRegex(info.name, r"^[A-HJ-NPR-Z0-9]{17}$")


if __name__ == "__main__":
    unittest.main()
