import gzip
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from mdi2.calibration_payloads import Calibration
from mdi2.calibration_transaction import TransactionError, TrustedContainer, UdsClient
from mdi2.ltz_workflow_simulation import simulate_ltz_workflow
from test_calibration_transaction import FakeTransport


class FakeLink(UdsClient):
    def __init__(self, transport):
        super().__init__(transport)
        self.closed = False

    def close(self):
        if self.closed:
            raise RuntimeError("simulated underlying link closed twice")
        self.closed = True


class LtzWorkflowSimulationTests(unittest.TestCase):
    def setUp(self):
        self.cals = []
        records = []
        for i in range(2, 16):
            header = bytearray(0x368)
            header[3], header[6:10] = i, b"CSM\x00"
            header[0x362:0x364] = b"AA"
            header[0x364], header[0x365:0x368] = 5, bytes([0, 0, i])
            xml = b'<x:CalOvrideFile xmlns:x="http://caltools.gm.com/calovride"/>'
            self.cals.append(Calibration(i, f"{i:08d}", bytes(header) + gzip.compress(xml)))
            records.append(bytes([i, 5, 0, 0, i]) + b"AA")
        self.cals = tuple(self.cals)
        self.manifest = tuple(TrustedContainer(c.slot, c.part, hashlib.sha256(c.container).hexdigest())
                              for c in self.cals)
        self.f182 = bytes.fromhex("62 f1 82 0e") + b"".join(records)

    def test_full_simulated_flow_with_one_voltage_sample_and_owned_links(self):
        links, released, samples = [], [], []
        def open_link():
            link = FakeLink(FakeTransport())
            links.append(link)
            return link
        def final_link(old):
            self.assertIs(old.transport, links[1].transport)
            old.close()
            link = FakeLink(FakeTransport())
            links.append(link)
            return link
        def release(link):
            released.append(link)
            link.close()
        def voltage():
            samples.append(12601)
            return samples[-1]
        def readback():
            self.assertTrue(all(link.closed for link in links))
            return (b"\x62\xf1\x90" + b"A" * 17, self.f182,
                    bytes.fromhex("62 f0 f1 00 00"), bytes.fromhex("62 f0 f2 00 00"))
        with patch("mdi2.ltz_workflow_simulation.validate_ltz_package", return_value=self.cals), \
             patch("mdi2.ltz_workflow_simulation.LTZ_REFERENCE", self.manifest):
            result = simulate_ltz_workflow(Path("unused"), expected_vin=b"A" * 17,
                      open_link=open_link, read_power_mode=lambda: 0, read_voltage_mv=voltage,
                      reconnect_finalization=final_link, release_finalization=release,
                      read_after_reboot=readback, adapter_max_request_length=4095, authorized=True)
        self.assertEqual(result.transaction.status, "RESET_ACCEPTED_NOT_VERIFIED")
        self.assertEqual(result.readback.mismatching_slots, ())
        self.assertEqual(len(result.readback.matching_slots), 14)
        self.assertEqual(samples, [12601])
        self.assertEqual(released, [links[2]])
        self.assertTrue(all(link.closed for link in links))
        self.assertIn(b"\x11\x01", links[0].transport.sent)
        self.assertEqual(links[2].transport.sent[-1], b"\x11\x01")

    def test_package_rejection_occurs_before_any_link(self):
        opened = []
        with patch("mdi2.ltz_workflow_simulation.validate_ltz_package", side_effect=ValueError("bad package")):
            with self.assertRaisesRegex(ValueError, "bad package"):
                simulate_ltz_workflow(Path("unused"), expected_vin=b"A" * 17,
                    open_link=lambda: opened.append(True), read_power_mode=lambda: 0, read_voltage_mv=lambda: 12601,
                    reconnect_finalization=lambda old: old, release_finalization=lambda link: None,
                    read_after_reboot=lambda: (), adapter_max_request_length=4095, authorized=True)
        self.assertEqual(opened, [])

    def test_invalid_closable_link_is_closed(self):
        class InvalidLink:
            closed = False
            def close(self):
                self.closed = True
        link = InvalidLink()
        with patch("mdi2.ltz_workflow_simulation.validate_ltz_package", return_value=self.cals), \
             patch("mdi2.ltz_workflow_simulation.LTZ_REFERENCE", self.manifest):
            with self.assertRaises(TransactionError):
                simulate_ltz_workflow(Path("unused"), expected_vin=b"A" * 17,
                    open_link=lambda: link, read_power_mode=lambda: 0, read_voltage_mv=lambda: 12601,
                    reconnect_finalization=lambda old: old, release_finalization=lambda final: None,
                    read_after_reboot=lambda: (), adapter_max_request_length=4095, authorized=True)
        self.assertTrue(link.closed)

    def test_static_programming_inputs_rejected_before_open(self):
        for override in ({"reconnect_finalization": None}, {"release_finalization": None},
                         {"adapter_max_request_length": 19}):
            with self.subTest(override=override):
                opened = []
                args = dict(expected_vin=b"A" * 17, open_link=lambda: opened.append(True),
                            read_power_mode=lambda: 0, read_voltage_mv=lambda: 12601,
                            reconnect_finalization=lambda old: old,
                            release_finalization=lambda link: None,
                            read_after_reboot=lambda: (), adapter_max_request_length=4095,
                            authorized=True)
                args.update(override)
                with self.assertRaises(ValueError):
                    simulate_ltz_workflow(Path("unused"), **args)
                self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()
