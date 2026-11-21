import unittest
import gzip
import hashlib
from decimal import Decimal

from mdi2.calibration_payloads import Calibration
from mdi2.calibration_transaction import (
    ProgramFailure, TransactionError, TrustedContainer, UdsClient, max_block_length, program,
)


class FakeTransport:
    def __init__(self, *, seed=None, bad_counter=False, bad_psi=False, pending=False):
        self.sent = []
        self.queue = []
        self.seed = bytes([255]) * 31 if seed is None else seed
        self.bad_counter = bad_counter
        self.bad_psi = bad_psi
        self.pending = pending

    def send(self, req):
        self.sent.append(req)
        sid = req[0]
        if sid == 0x22:
            values = {b"\xf1\x90": b"A" * 17, b"\xf1\x98": b"B" * 10,
                      b"\xf1\x99": b"\x20\x26\x11\x07", b"\xf1\xb0": b"\x80",
                      b"\xf0\xf0": b"" if self.bad_psi else
                      b"".join(bytes([x, 0]) for x in range(2, 16))}
            reply = b"\x62" + req[1:3] + values[req[1:3]]
        elif req == b"\x27\x01":
            reply = b"\x67\x01" + self.seed
        elif req[:2] == b"\x27\x02":
            reply = b"\x67\x02"
        elif sid == 0x85 or sid == 0x28:
            reply = bytes([sid + 0x40, req[1]])
        elif sid == 0x10 or sid == 0x11:
            reply = bytes([sid + 0x40, req[1]])
        elif sid == 0x31:
            reply = b"\x71" + req[1:4]
        elif sid == 0x34:
            reply = b"\x74\x20\x00\x05"
        elif sid == 0x36:
            reply = b"\x76" + bytes([(req[1] + self.bad_counter) & 0xFF])
        elif sid == 0x37:
            reply = b"\x77"
        elif sid == 0x2e:
            reply = b"\x6e" + req[1:3]
        else:
            raise AssertionError(f"unexpected service {sid:02x}")
        if self.pending:
            self.queue.append(bytes([0x7F, sid, 0x78]))
        self.queue.append(reply)

    def receive(self, timeout):
        return self.queue.pop(0) if self.queue else None


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.cals = []
        for i in range(2, 16):
            header = bytearray(0x368)
            header[3] = i
            header[6:10] = b"CSM\x00"
            xml = b'<x:CalOvrideFile xmlns:x="http://caltools.gm.com/calovride"/>'
            self.cals.append(Calibration(i, f"{i:08d}", bytes(header) + gzip.compress(xml)))
        # Synthetic test fixture only; production manifests must be separately verified.
        self.manifest = tuple(TrustedContainer(c.slot, c.part, hashlib.sha256(c.container).hexdigest())
                              for c in self.cals)
        def reconnect_fake(client):
            transport = FakeTransport(pending=client.transport.pending)
            transport.sent = client.transport.sent
            return UdsClient(transport)
        self.args = {"trusted_manifest": self.manifest, "expected_vin": b"A" * 17,
                     "adapter_max_request_length": 4095,
                     "reconnect_finalization": reconnect_fake,
                     "release_finalization": lambda client: None}

    def test_full_sequence_pending_fragmentation_and_identity(self):
        transport = FakeTransport(pending=True)
        result = program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertEqual(result.status, "RESET_ACCEPTED_NOT_VERIFIED")
        self.assertEqual(result.slots_transferred, 14)
        self.assertEqual(sum(x[:1] == b"\x34" for x in transport.sent), 14)
        expected_blocks = sum((len(cal.container) + 2) // 3 for cal in self.cals)
        self.assertEqual(sum(x[:1] == b"\x36" for x in transport.sent), expected_blocks)
        self.assertTrue(all(len(x) <= 5 for x in transport.sent if x[:1] == b"\x36"))
        # SPS pre-transfer comm state: DTC logging off, normal comms off.
        self.assertIn(b"\x85\x02", transport.sent)
        self.assertIn(b"\x28\x03\x01", transport.sent)
        # Finalization re-reads the ECU id (22 F1B0), not F190, on the fresh
        # link; the only 22 F190 read is the pre-transfer read_identifiers.
        self.assertIn(b"\x22\xf1\xb0", transport.sent)
        self.assertEqual(sum(x == b"\x22\xf1\x90" for x in transport.sent), 1)
        self.assertIn(b"\x2e\xf1\x90" + b"A" * 17, transport.sent)
        # Fixed SPS repair-shop id, not the module read-back (which was B*10).
        self.assertIn(b"\x2e\xf1\x98" + b"9999988888", transport.sent)
        self.assertNotIn(b"\x2e\xf1\x98" + b"B" * 10, transport.sent)
        # F199 programming date: 4-byte BCD run date written, not the read-back.
        f199 = [x for x in transport.sent if x[:3] == b"\x2e\xf1\x99"]
        self.assertEqual(len(f199), 1)
        self.assertEqual(len(f199[0]), 7)  # 2E F1 99 + 4 BCD bytes
        self.assertEqual(transport.sent[-1], b"\x11\x01")

    def test_finalization_metadata_is_fixed_shop_and_run_date(self):
        import time as _time
        from mdi2.calibration_transaction import _current_programming_date
        transport = FakeTransport()
        program(UdsClient(transport), self.cals, authorized=True,
                programming_date=b"\x20\x26\x11\x10", **self.args)
        self.assertIn(b"\x2e\xf1\x98" + b"9999988888", transport.sent)  # fixed id
        self.assertIn(b"\x2e\xf1\x99" + b"\x20\x26\x11\x10", transport.sent)  # pinned date
        self.assertIn(b"\x2e\xf1\x90" + b"A" * 17, transport.sent)  # expected VIN
        # The default date is the 4-byte BCD YYYYMMDD of the run date.
        bcd = _current_programming_date(
            lambda: _time.struct_time((2026, 8, 24, 0, 0, 0, 0, 0, 0)))
        self.assertEqual(bcd, b"\x20\x26\x08\x24")

    def test_finalization_returns_to_default_session_before_extended(self):
        # Regression (live 2026-11-10): the finalization link-bounce must send
        # 10 01 (default session) then 22 F1B0 then 10 03. Jumping directly from
        # programming session (10 02) to 10 03 drew NRC 7E on the radio.
        transport = FakeTransport()
        program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertIn(b"\x10\x01", transport.sent)  # only occurs in finalization
        i = transport.sent.index(b"\x10\x01")
        self.assertEqual(transport.sent[i:i + 3],
                         [b"\x10\x01", b"\x22\xf1\xb0", b"\x10\x03"])

    def test_invalid_programming_date_rejected_before_io(self):
        for bad in (b"\x20\x26\x11", "20261110", 20261110):
            transport = FakeTransport()
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                program(UdsClient(transport), self.cals, authorized=True,
                        programming_date=bad, **self.args)
            self.assertEqual(transport.sent, [])

    def test_no_authorization_means_no_request(self):
        transport = FakeTransport()
        with self.assertRaises(ValueError):
            program(UdsClient(transport), self.cals, **self.args)
        self.assertEqual(transport.sent, [])

    def test_authorization_requires_literal_true(self):
        for flag in ("false", 1, object()):
            transport = FakeTransport()
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                program(UdsClient(transport), self.cals, authorized=flag, **self.args)
            self.assertEqual(transport.sent, [])

    def test_slot_numbers_must_be_integers_before_io(self):
        for bad_slot in (2.0, True):
            transport = FakeTransport()
            malformed = self.cals.copy()
            original = malformed[0]
            malformed[0] = Calibration(bad_slot, original.part, original.container)
            with self.subTest(slot=bad_slot), self.assertRaises(ValueError):
                program(UdsClient(transport), malformed, authorized=True, **self.args)
            self.assertEqual(transport.sent, [])
        for bad_slot in (2.0, True):
            transport = FakeTransport()
            first = self.manifest[0]
            malformed = (TrustedContainer(bad_slot, first.part, first.sha256),) + self.manifest[1:]
            with self.subTest(manifest_slot=bad_slot), self.assertRaises(ValueError):
                program(UdsClient(transport), self.cals, authorized=True,
                        **dict(self.args, trusted_manifest=malformed))
            self.assertEqual(transport.sent, [])

    def test_non_ff_seed_stops_before_programming_routine(self):
        transport = FakeTransport(seed=bytes(31))
        with self.assertRaisesRegex(TransactionError, "seed"):
            program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertNotIn(b"\x31\x01\x02\x49", transport.sent)
        self.assertFalse(any(x[:1] == b"\x34" for x in transport.sent))

    def test_wrong_block_counter_stops_without_reset(self):
        transport = FakeTransport(bad_counter=True)
        with self.assertRaisesRegex(TransactionError, "mismatched positive"):
            program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertFalse(any(x[:1] == b"\x37" for x in transport.sent))
        self.assertNotIn(b"\x11\x01", transport.sent)

    def test_unexpected_status_stops_before_finalization(self):
        transport = FakeTransport(bad_psi=True)
        with self.assertRaisesRegex(TransactionError, "status readback"):
            program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertFalse(any(x[:1] == b"\x2e" for x in transport.sent))
        self.assertNotIn(b"\x11\x01", transport.sent)

    def test_failed_finalization_reconnect_stops_before_security_and_writes(self):
        transport = FakeTransport()
        args = dict(self.args, reconnect_finalization=lambda client: client)
        with self.assertRaisesRegex(TransactionError, "fresh client"):
            program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertEqual(sum(x == b"\x27\x01" for x in transport.sent), 1)
        self.assertFalse(any(x[:1] == b"\x2e" for x in transport.sent))
        self.assertNotIn(b"\x11\x01", transport.sent)

    def test_wrapping_same_transport_is_not_a_fresh_link(self):
        transport = FakeTransport()
        args = dict(self.args, reconnect_finalization=lambda client: UdsClient(client.transport))
        with self.assertRaisesRegex(TransactionError, "fresh client"):
            program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertFalse(any(x[:1] == b"\x2e" for x in transport.sent))

    def test_wrong_vehicle_after_reconnect_stops_finalization(self):
        class WrongVehicle(FakeTransport):
            def send(self, request):
                super().send(request)
                if request == b"\x22\xf1\xb0":
                    self.queue[-1] = b"\x62\xf1\xb0\x81"  # wrong ECU id
        initial = FakeTransport()
        final = WrongVehicle()
        args = dict(self.args, reconnect_finalization=lambda client: UdsClient(final))
        with self.assertRaisesRegex(TransactionError, "reconnected target identity"):
            program(UdsClient(initial), self.cals, authorized=True, **args)
        # SPS link-bounce: 10 01 (default session) precedes the 22 F1B0 identity
        # check; the wrong-ECU-id abort fires before 10 03.
        self.assertEqual(final.sent, [b"\x10\x01", b"\x22\xf1\xb0"])

    def test_finalization_link_released_on_success_and_failure(self):
        for wrong_target in (False, True):
            class FinalTransport(FakeTransport):
                def send(self, request):
                    super().send(request)
                    if wrong_target and request == b"\x22\xf1\xb0":
                        self.queue[-1] = b"\x62\xf1\xb0\x81"  # wrong ECU id
            initial, final, released = FakeTransport(), FinalTransport(), []
            args = dict(self.args, reconnect_finalization=lambda client: UdsClient(final),
                        release_finalization=lambda client: released.append(client))
            if wrong_target:
                with self.assertRaises(TransactionError):
                    program(UdsClient(initial), self.cals, authorized=True, **args)
            else:
                program(UdsClient(initial), self.cals, authorized=True, **args)
            self.assertEqual(len(released), 1)
            self.assertIs(released[0].transport, final)

    def test_finalization_release_failure_cannot_report_success(self):
        def fail_release(client):
            raise RuntimeError("cleanup failed")
        transport = FakeTransport()
        args = dict(self.args, release_finalization=fail_release)
        with self.assertRaisesRegex(TransactionError, "cleanup finalization link"):
            program(UdsClient(transport), self.cals, authorized=True, **args)

    def test_finalization_failure_preserves_cleanup_failure(self):
        class WrongVehicle(FakeTransport):
            def send(self, request):
                super().send(request)
                if request == b"\x22\xf1\xb0":
                    self.queue[-1] = b"\x62\xf1\xb0\x81"  # wrong ECU id
        def fail_release(client):
            raise RuntimeError("private cleanup details")
        args = dict(self.args, reconnect_finalization=lambda client: UdsClient(WrongVehicle()),
                    release_finalization=fail_release)
        with self.assertRaises(TransactionError) as caught:
            program(UdsClient(FakeTransport()), self.cals, authorized=True, **args)
        self.assertTrue(caught.exception.cleanup_failed)
        self.assertIn("reconnected target identity", str(caught.exception))
        self.assertNotIn("private cleanup details", str(caught.exception))

    def test_bad_negotiated_limit_rejected(self):
        for value in (b"\x74\x20\x0f", b"\x74\x21\x0f\xff", b"\x74\x10\x02"):
            with self.subTest(value=value), self.assertRaises(TransactionError):
                max_block_length(value)

    def test_repeated_pending_cannot_extend_hard_deadline(self):
        class PendingTransport:
            now = 0.0
            def send(self, req):
                pass
            def receive(self, timeout):
                self.now += 1
                return b"\x7f\x31\x78"
        transport = PendingTransport()
        client = UdsClient(transport, timeout=2, pending_timeout=2,
                           max_elapsed=5, clock=lambda: transport.now)
        with self.assertRaisesRegex(TransactionError, "timed out"):
            client.request(b"\x31\x01\x02\x49", b"\x71\x01\x02\x49")
        self.assertEqual(transport.now, 5)

    def test_terminal_nrc_raises_and_transport_remains_usable(self):
        class NrcThenPositive:
            def __init__(self):
                self.sent = []
                self.queue = [b"\x7f\x22\x31", b"\x62\xf1\x90" + b"A" * 17]
            def send(self, req):
                self.sent.append(req)
            def receive(self, timeout):
                return self.queue.pop(0) if self.queue else None
        transport = NrcThenPositive()
        client = UdsClient(transport)
        with self.assertRaisesRegex(TransactionError, "service 22 NRC 31"):
            client.request(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertEqual(client.request(b"\x22\xf1\x90", b"\x62\xf1\x90"), b"\x62\xf1\x90" + b"A" * 17)
        self.assertEqual(transport.sent, [b"\x22\xf1\x8c", b"\x22\xf1\x90"])

    def test_mid_write_terminal_nrc_aborts_transfer(self):
        # Gated-write invariant: a terminal NRC on TransferData stops the
        # transaction at that block; nothing after it is sent.
        class NrcOnBlockThree(FakeTransport):
            def send(self, req):
                if req[:1] == b"\x36" and req[1] == 3:
                    self.sent.append(req)
                    self.queue.append(b"\x7f\x36\x31")
                    return
                super().send(req)
        transport = NrcOnBlockThree()
        with self.assertRaises(ProgramFailure) as ctx:
            program(UdsClient(transport), self.cals, authorized=True, **self.args)
        failure = ctx.exception
        self.assertEqual((failure.phase, failure.transferred, failure.slot, failure.block),
                         ("transfer data", 0, 2, 3))
        self.assertEqual(failure.safe_reason, "service 36 NRC 31")
        self.assertEqual(transport.sent[-1][:2], b"\x36\x03")
        self.assertFalse(any(x[:1] in (b"\x37", b"\x11", b"\x2e") for x in transport.sent))
        self.assertEqual(sum(x[:1] == b"\x36" for x in transport.sent), 3)

    def test_timeout_values_must_be_finite_before_io(self):
        for name in ("timeout", "pending_timeout", "max_elapsed"):
            for value in (float("nan"), float("inf"), -float("inf"), 0, -1, True):
                transport = FakeTransport()
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    UdsClient(transport, **{name: value})
                self.assertEqual(transport.sent, [])

    def test_malformed_package_stops_before_first_request(self):
        transport = FakeTransport()
        broken = self.cals.copy()
        broken[0] = Calibration(2, "00000002", b"bad")
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            program(UdsClient(transport), broken, authorized=True, **self.args)
        self.assertEqual(transport.sent, [])

    def test_wrong_vin_stops_before_session_change(self):
        transport = FakeTransport()
        args = dict(self.args, expected_vin=b"Z" * 17)
        with self.assertRaisesRegex(TransactionError, "identity does not match"):
            program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertFalse(any(req[0] == 0x10 for req in transport.sent))
        self.assertFalse(any(req[0] == 0x34 for req in transport.sent))

    def test_adapter_limit_lower_than_ecu_limit(self):
        class LargerEcu(FakeTransport):
            def send(self, req):
                super().send(req)
                if req[0] == 0x34:
                    self.queue[-1] = b"\x74\x20\x0f\xff"
        transport = LargerEcu()
        args = dict(self.args, adapter_max_request_length=64)
        program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertTrue(all(len(req) <= 64 for req in transport.sent if req[0] == 0x36))

    def test_transport_failure_reports_phase_without_payload(self):
        class FailingSend(FakeTransport):
            def send(self, req):
                if req[0] == 0x36:
                    raise OSError("sensitive transport detail")
                super().send(req)
        transport = FailingSend()
        with self.assertRaises(TransactionError) as caught:
            program(UdsClient(transport), self.cals, authorized=True, **self.args)
        self.assertIn("phase=transfer data", str(caught.exception))
        self.assertIn("slot=02", str(caught.exception))
        self.assertIn("block=01", str(caught.exception))
        self.assertIn("ambiguous", str(caught.exception))
        self.assertNotIn("sensitive", str(caught.exception))

    def test_too_small_adapter_limits_fail_before_any_io(self):
        for limit in range(3, 20):
            transport = FakeTransport()
            args = dict(self.args, adapter_max_request_length=limit)
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                program(UdsClient(transport), self.cals, authorized=True, **args)
            self.assertEqual(transport.sent, [])

    def test_adapter_limit_boundaries(self):
        transport = FakeTransport()
        args = dict(self.args, adapter_max_request_length=20)
        result = program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertEqual(result.status, "RESET_ACCEPTED_NOT_VERIFIED")
        transport = FakeTransport()
        args = dict(self.args, adapter_max_request_length=4096)
        with self.assertRaises(ValueError):
            program(UdsClient(transport), self.cals, authorized=True, **args)
        self.assertEqual(transport.sent, [])

    def test_adapter_limit_requires_integer_before_any_io(self):
        for limit in (20.5, 20.0, True, Decimal("20")):
            transport = FakeTransport()
            args = dict(self.args, adapter_max_request_length=limit)
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                program(UdsClient(transport), self.cals, authorized=True, **args)
            self.assertEqual(transport.sent, [])

    def test_verified_data_is_snapshotted_before_io(self):
        original = self.cals[0].container
        second_original = self.cals[1].container
        mutable = bytearray(original)
        self.cals[0] = Calibration(2, self.cals[0].part, mutable)
        cals = self.cals
        class MutatingTransport(FakeTransport):
            def send(self, req):
                if not self.sent:
                    mutable[:] = b"altered"
                    cals[1] = Calibration(3, "00000003", b"replacement")
                super().send(req)
        transport = MutatingTransport()
        program(UdsClient(transport), cals, authorized=True, **self.args)
        groups = []
        blocks = None
        for req in transport.sent:
            if req[0] == 0x34:
                blocks = []
            elif blocks is not None and req[0] == 0x36:
                blocks.append(req[2:])
            elif blocks is not None and req[0] == 0x37:
                groups.append(b"".join(blocks))
                blocks = None
        self.assertEqual(groups[0], original)
        self.assertEqual(groups[1], second_original)


class SecurityUnlockSeamTests(unittest.TestCase):
    """The generic unlock seam must leave the degenerate 0x80 all-FF path
    byte-identical when no key is supplied, and only use CMAC when a key exists.
    """

    def test_degenerate_path_is_byte_identical_to_unlock_all_ff(self):
        from mdi2.calibration_transaction import unlock_all_ff_seed, unlock_security_access
        baseline = FakeTransport()
        unlock_all_ff_seed(UdsClient(baseline))
        generic = FakeTransport()
        unlock_security_access(UdsClient(generic), None)
        self.assertEqual(baseline.sent, generic.sent)
        self.assertEqual(generic.sent, [b"\x27\x01", b"\x27\x02" + bytes(12)])

    def test_no_key_provider_still_uses_degenerate_path(self):
        from mdi2.calibration_transaction import unlock_security_access
        from mdi2.security_cmac import GMSecurityAccess
        transport = FakeTransport()  # default 31-byte all-FF seed
        unlock_security_access(UdsClient(transport), GMSecurityAccess())
        self.assertEqual(transport.sent, [b"\x27\x01", b"\x27\x02" + bytes(12)])

    def test_cmac_key_response_sent_when_key_available(self):
        from mdi2.calibration_transaction import unlock_security_access
        from mdi2.security_cmac import GMSecurityAccess, SecurityCmacUnavailable
        ecuid = bytes.fromhex("00000000000000000000000000000565")
        challenge = bytes(range(16))
        sec = GMSecurityAccess()
        sec.add_key(ecuid, b"\x22" * 16)
        try:
            expected = sec.compute_response(ecuid + challenge)
        except SecurityCmacUnavailable:
            self.skipTest("no AES-CMAC backend")
        transport = FakeTransport(seed=ecuid + challenge)
        unlock_security_access(UdsClient(transport), sec)
        self.assertEqual(transport.sent, [b"\x27\x01", b"\x27\x02" + expected])
        self.assertEqual(len(expected), 12)

    def test_program_default_security_none_unchanged_unlock_bytes(self):
        # program() with its default security=None must emit exactly the two
        # degenerate SecurityAccess rounds (before transfer, before finalization).
        transport = FakeTransport()
        base = TransactionTests()
        base.setUp()
        program(UdsClient(transport), base.cals, authorized=True, **base.args)
        self.assertEqual(sum(r == b"\x27\x01" for r in transport.sent), 2)
        self.assertEqual(sum(r == b"\x27\x02" + bytes(12) for r in transport.sent), 2)

    def test_real_seed_without_key_aborts_without_sending_a_key(self):
        from mdi2.calibration_transaction import unlock_security_access
        from mdi2.security_cmac import GMSecurityAccess
        # A non-degenerate seed with no usable key must abort cleanly after 27 01;
        # no key (not even the degenerate 12 zero bytes) is fabricated.
        for sec in (None, GMSecurityAccess()):
            transport = FakeTransport(seed=bytes(range(1, 32)))
            with self.subTest(security=type(sec).__name__), \
                    self.assertRaisesRegex(TransactionError, "SBI not flipped"):
                unlock_security_access(UdsClient(transport), sec)
            self.assertEqual(transport.sent, [b"\x27\x01"])

    def test_program_real_seed_no_key_aborts_before_transfer(self):
        transport = FakeTransport(seed=bytes(range(1, 32)))
        base = TransactionTests()
        base.setUp()
        with self.assertRaisesRegex(TransactionError, "real CMAC seed"):
            program(UdsClient(transport), base.cals, authorized=True, **base.args)
        self.assertNotIn(b"\x31\x01\x02\x49", transport.sent)
        self.assertFalse(any(x[:1] == b"\x34" for x in transport.sent))
        self.assertNotIn(b"\x27\x02" + bytes(12), transport.sent)


if __name__ == "__main__":
    unittest.main()
