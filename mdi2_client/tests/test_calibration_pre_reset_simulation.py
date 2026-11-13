import unittest

from mdi2.calibration_pre_reset_simulation import simulate_reset_then_program as simulate
from mdi2.calibration_transaction import ProgramFailure, TransactionError


VIN = b"A" * 17


def simulate_reset_then_program(*args, **kwargs):
    kwargs.setdefault("read_voltage_mv", lambda: 12500)
    kwargs.setdefault("read_power_mode", lambda: 0)
    return simulate(*args, **kwargs)


class FakeLink:
    def __init__(self, *, vin=VIN, fail_at=None, reset_reply=b"\x51\x01", seed=b"\xff" * 31):
        self.vin = vin
        self.fail_at = fail_at
        self.reset_reply = reset_reply
        self.seed = seed
        self.requests = []
        self.close_count = 0

    def request(self, req, expected):
        self.requests.append(req)
        if req == self.fail_at:
            raise TransactionError("simulated failure")
        return {
            b"\x22\xf1\x90": b"\x62\xf1\x90" + self.vin,
            b"\x10\x03": b"\x50\x03\x00\x64\x01\xf4",
            b"\x27\x01": b"\x67\x01" + self.seed,
            b"\x27\x02" + bytes(12): b"\x67\x02",
            b"\x11\x01": self.reset_reply,
        }[req]

    def close(self):
        self.close_count += 1


class PreResetTests(unittest.TestCase):
    def test_non_off_power_mode_stops_before_reset(self):
        first = FakeLink()
        with self.assertRaises(TransactionError):
            simulate_reset_then_program(lambda: first, lambda link: None,
                                        expected_vin=VIN, authorized=True,
                                        read_power_mode=lambda: 2)
        self.assertNotIn(b"\x11\x01", first.requests)
        self.assertEqual(first.close_count, 1)

    def run_pair(self, first, second, *, authorized=True, expected_vin=VIN):
        links = iter((first, second))
        programmed = []
        def program(link):
            programmed.append(link)
            return "SIMULATED"
        result = simulate_reset_then_program(lambda: next(links), program,
                                             expected_vin=expected_vin,
                                             authorized=authorized)
        return result, programmed

    def test_success_requires_ack_and_post_reset_identity(self):
        first, second = FakeLink(), FakeLink()
        result, programmed = self.run_pair(first, second)
        self.assertEqual(result, "SIMULATED")
        self.assertEqual(first.requests, [b"\x22\xf1\x90", b"\x10\x03", b"\x27\x01",
                                          b"\x27\x02" + bytes(12), b"\x11\x01"])
        self.assertEqual(second.requests, [b"\x10\x03", b"\x22\xf1\x90"])
        self.assertEqual(programmed, [second])
        self.assertEqual((first.close_count, second.close_count), (1, 1))

    def test_negative_or_missing_reset_ack_never_programs(self):
        for reply in (b"\x7f\x11\x22", b"", b"\x51\x01\x00"):
            first, second = FakeLink(reset_reply=reply), FakeLink()
            invoked = []
            with self.subTest(reply=reply), self.assertRaises(TransactionError):
                simulate_reset_then_program(lambda: first, invoked.append,
                                            expected_vin=VIN, authorized=True)
            self.assertEqual(invoked, [])
            self.assertEqual(first.close_count, 1)
            self.assertEqual(second.requests, [])

    def test_first_or_second_identity_mismatch_never_programs(self):
        for a, b in ((b"B" * 17, VIN), (VIN, b"B" * 17)):
            first, second = FakeLink(vin=a), FakeLink(vin=b)
            links = iter((first, second))
            invoked = []
            with self.subTest(initial=a == VIN), self.assertRaises(TransactionError):
                simulate_reset_then_program(lambda: next(links), invoked.append,
                                            expected_vin=VIN, authorized=True)
            self.assertEqual(invoked, [])
            if a != VIN:
                self.assertNotIn(b"\x11\x01", first.requests)

    def test_reconnect_failure_or_same_link_never_programs(self):
        first = FakeLink()
        invoked = []
        links = iter((first, first))
        with self.assertRaisesRegex(TransactionError, "open post-reset link"):
            simulate_reset_then_program(lambda: next(links), invoked.append,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual(invoked, [])
        self.assertEqual(first.close_count, 1)
        first = FakeLink()
        links = iter((first,))
        with self.assertRaisesRegex(TransactionError, "open post-reset link"):
            simulate_reset_then_program(lambda: next(links), invoked.append,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual(invoked, [])

    def test_reset_failure_and_auth_refusal_prevent_programming(self):
        for fail in (b"\x10\x03", b"\x27\x01", b"\x27\x02" + bytes(12), b"\x11\x01"):
            first = FakeLink(fail_at=fail)
            invoked = []
            with self.subTest(fail=fail[:2]), self.assertRaises(TransactionError):
                simulate_reset_then_program(lambda: first, invoked.append,
                                            expected_vin=VIN, authorized=True)
            self.assertEqual(invoked, [])
            self.assertEqual(first.close_count, 1)

    def test_non_ff_seed_does_not_send_key_reset_or_programming(self):
        first = FakeLink(seed=bytes(31))
        invoked = []
        with self.assertRaisesRegex(TransactionError, "unlock pre-reset session"):
            simulate_reset_then_program(lambda: first, invoked.append,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual(invoked, [])
        self.assertNotIn(b"\x27\x02" + bytes(12), first.requests)
        self.assertNotIn(b"\x11\x01", first.requests)

    def test_program_failure_retains_structured_progress_without_adapter_text(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        failure = ProgramFailure(phase="transfer data", transferred=2, slot=4, block=3,
                                 safe_reason="service 36 NRC 31")
        def program(_):
            raise failure
        with self.assertRaises(ProgramFailure) as result:
            simulate_reset_then_program(lambda: next(links), program,
                                        expected_vin=VIN, authorized=True)
        self.assertIsNot(result.exception, failure)
        self.assertEqual((result.exception.phase, result.exception.transferred,
                          result.exception.slot, result.exception.block),
                         ("transfer data", 2, 4, 3))
        self.assertIn("service 36 NRC 31", str(result.exception))
        self.assertEqual((first.close_count, second.close_count), (1, 1))

    def test_modified_failure_text_is_not_propagated(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        failure = ProgramFailure(phase="transfer data", transferred=2, slot=4, block=3)
        failure.args = ("private marker",)
        failure.safe_reason = "private marker"
        def program(_):
            raise failure
        with self.assertRaises(ProgramFailure) as result:
            simulate_reset_then_program(lambda: next(links), program,
                                        expected_vin=VIN, authorized=True)
        self.assertNotIn("private marker", str(result.exception))
        self.assertEqual(result.exception.slot, 4)

    def test_modified_failure_metadata_is_rejected(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        failure = ProgramFailure(phase="transfer data", transferred=2, slot=4, block=3)
        failure.phase = "private marker"
        def program(_):
            raise failure
        with self.assertRaises(TransactionError) as result:
            simulate_reset_then_program(lambda: next(links), program,
                                        expected_vin=VIN, authorized=True)
        self.assertNotIn("private marker", str(result.exception))
        self.assertIn("invalid progress metadata", str(result.exception))

    def test_unknown_callback_exception_text_is_not_propagated(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        def program(_):
            raise RuntimeError("secret marker")
        with self.assertRaises(TransactionError) as result:
            simulate_reset_then_program(lambda: next(links), program,
                                        expected_vin=VIN, authorized=True)
        self.assertNotIn("secret marker", str(result.exception))
        self.assertIn("program", str(result.exception))

    def test_invalid_preconditions_send_nothing(self):
        for auth, vin in ((False, VIN), ("true", VIN), (True, b"short")):
            calls = []
            with self.subTest(auth=auth, length=len(vin)), self.assertRaises(ValueError):
                simulate_reset_then_program(lambda: calls.append("open"), lambda _: None,
                                            expected_vin=vin, authorized=auth)
            self.assertEqual(calls, [])

    def test_voltage_boundary_is_read_once_immediately_before_program(self):
        first, second = FakeLink(), FakeLink()
        events = []
        links = iter((first, second))
        def voltage():
            events.append("voltage")
            return 12000
        def open_link():
            events.append("open")
            return next(links)
        def program(_):
            events.append("program")
            return "SIMULATED"
        self.assertEqual(simulate_reset_then_program(open_link, program, expected_vin=VIN,
                                                     read_voltage_mv=voltage, authorized=True),
                         "SIMULATED")
        self.assertEqual(events, ["open", "open", "voltage", "program"])

    def test_low_or_invalid_voltage_prevents_programming(self):
        for value in (11999, 12, 12.6, 12000.0, True, None, 30001, 0xFFFFFFFF):
            first, second = FakeLink(), FakeLink()
            links = iter((first, second))
            invoked = []
            with self.subTest(value=value), self.assertRaises(TransactionError) as result:
                simulate_reset_then_program(lambda: next(links), invoked.append,
                                            read_voltage_mv=lambda: value,
                                            expected_vin=VIN, authorized=True)
            self.assertEqual(invoked, [])
            self.assertEqual((first.close_count, second.close_count), (1, 1))
            if value == 11999:
                self.assertIn("voltage_mv=11999 minimum_mv=12000", str(result.exception))
            if value == 30001:
                self.assertIn("voltage_mv=30001 maximum_data_value_mv=30000", str(result.exception))

    def test_voltage_data_range_upper_boundary_is_not_a_safety_claim(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        self.assertEqual(simulate_reset_then_program(lambda: next(links), lambda _: "SIMULATED",
                                                     read_voltage_mv=lambda: 30000,
                                                     expected_vin=VIN, authorized=True),
                         "SIMULATED")

    def test_voltage_reader_failure_prevents_programming(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        invoked = []
        def voltage():
            raise OSError(5, "private marker")
        with self.assertRaises(TransactionError) as result:
            simulate_reset_then_program(lambda: next(links), invoked.append,
                                        read_voltage_mv=voltage, expected_vin=VIN,
                                        authorized=True)
        self.assertEqual(invoked, [])
        self.assertEqual((first.close_count, second.close_count), (1, 1))
        self.assertIn("OSError errno=5", str(result.exception))
        self.assertNotIn("private marker", str(result.exception))

    def test_missing_voltage_reader_prevents_link_open(self):
        opens = []
        with self.assertRaisesRegex(ValueError, "callbacks"):
            simulate_reset_then_program(lambda: opens.append(True), lambda _: None,
                                        read_voltage_mv=None, expected_vin=VIN,
                                        authorized=True)
        self.assertEqual(opens, [])

    def test_low_voltage_after_reset_prevents_programming(self):
        first, second = FakeLink(), FakeLink()
        links = iter((first, second))
        invoked = []
        with self.assertRaises(TransactionError) as result:
            simulate_reset_then_program(lambda: next(links), invoked.append,
                                        read_voltage_mv=lambda: 11999,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual(invoked, [])
        self.assertIn(b"\x11\x01", first.requests)
        self.assertIn("voltage_mv=11999", str(result.exception))
        self.assertEqual((first.close_count, second.close_count), (1, 1))

    def test_cleanup_failure_prevents_success(self):
        class FailingClose(FakeLink):
            def close(self):
                self.close_count += 1
                raise OSError(5, "private marker")
        first, second = FakeLink(), FailingClose()
        links = iter((first, second))
        with self.assertRaisesRegex(TransactionError, "cleanup failed") as result:
            simulate_reset_then_program(lambda: next(links), lambda _: "SIMULATED",
                                        expected_vin=VIN, authorized=True)
        self.assertNotIn("private marker", str(result.exception))
        self.assertEqual((first.close_count, second.close_count), (1, 1))

    def test_initial_close_failure_aborts_without_retry_or_reopen(self):
        class FailingClose(FakeLink):
            def close(self):
                self.close_count += 1
                raise OSError(5, "private marker")
        first = FailingClose()
        opens, invoked = [], []
        def open_link():
            opens.append(True)
            return first
        with self.assertRaisesRegex(TransactionError, "close initial link") as result:
            simulate_reset_then_program(open_link, invoked.append,
                                        expected_vin=VIN, authorized=True)
        self.assertNotIn("private marker", str(result.exception))
        self.assertEqual((len(opens), first.close_count, invoked), (1, 1, []))

    def test_cleanup_failure_does_not_replace_program_failure(self):
        class FailingClose(FakeLink):
            def close(self):
                self.close_count += 1
                raise OSError(5, "private marker")
        first, second = FakeLink(), FailingClose()
        links = iter((first, second))
        def program(_):
            raise ProgramFailure(phase="transfer data", transferred=2, slot=4, block=3,
                                 safe_reason="service 36 NRC 31")
        with self.assertRaises(ProgramFailure) as result:
            simulate_reset_then_program(lambda: next(links), program,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual((result.exception.transferred, result.exception.slot,
                          result.exception.block), (2, 4, 3))
        self.assertIn("service 36 NRC 31", str(result.exception))
        self.assertTrue(result.exception.cleanup_failed)
        self.assertIn("link cleanup failed", str(result.exception))
        self.assertNotIn("private marker", str(result.exception))

    def test_cleanup_failure_keeps_reset_failure_and_reports_both(self):
        class FailingClose(FakeLink):
            def close(self):
                self.close_count += 1
                raise OSError(5, "private marker")
        first = FailingClose(fail_at=b"\x11\x01")
        invoked = []
        with self.assertRaises(TransactionError) as result:
            simulate_reset_then_program(lambda: first, invoked.append,
                                        expected_vin=VIN, authorized=True)
        self.assertEqual(invoked, [])
        self.assertTrue(result.exception.cleanup_failed)
        self.assertIn("reset radio", str(result.exception))
        self.assertIn("link cleanup failed", str(result.exception))
        self.assertNotIn("private marker", str(result.exception))
        self.assertEqual(first.close_count, 1)


if __name__ == "__main__":
    unittest.main()
