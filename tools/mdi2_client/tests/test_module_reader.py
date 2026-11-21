"""Offline tests for mdi2.uds_generic + mdi2.module_reader with a fake transport.

FakeTransport is ported from gmtool's test harness (scripted request-hex ->
response, with a 0x78 responsePending follow-up queue). All identifiers here are
PLACEHOLDERS -- no real VIN/serial.
"""
import threading
import time
import unittest

from mdi2.can_transport import CanDependencyError
from mdi2.ecu_catalog import EcuCatalog
from mdi2.module_reader import ModuleReader, WAKE_NM_CAN_ID
from mdi2.security_cmac import GMSecurityAccess, SecurityCmacUnavailable
from mdi2.uds_generic import (GenericUdsClient, UDSNegativeResponse, UDSTimeout,
                              UDSError, parse_sw_inventory)

PLACEHOLDER_VIN = b"PLACEHOLDERVIN017"  # 17 chars, obviously fake


class FakeTransport:
    """Scripted responder: request-hex -> response bytes, or a list whose tail
    becomes recv() follow-ups (0x78 responsePending chains)."""

    def __init__(self, script=None):
        self.script = {k: (list(v) if isinstance(v, list) else v)
                       for k, v in (script or {}).items()}
        self.sent = []
        self._pending = {}

    def send_uds(self, ecu_addr, data, timeout=None):
        self.sent.append(bytes(data))
        resp = self.script.get(bytes(data).hex())
        if isinstance(resp, list):
            first = resp.pop(0) if resp else None
            if resp:
                self._pending.setdefault(ecu_addr, []).extend(resp)
                resp.clear()
            return first
        return resp

    def recv(self, ecu_addr, timeout=5.0):
        q = self._pending.get(ecu_addr)
        return q.pop(0) if q else None


class UdsGenericTests(unittest.TestCase):
    def test_rejects_wrong_or_truncated_did_echo(self):
        for response in (b"\x62\xf1\x98OTHER", b"\x62\xf1", b""):
            with self.subTest(response=response):
                client = GenericUdsClient(FakeTransport({"22f190": response}), 0x80)
                with self.assertRaises(UDSError):
                    client.read_did(0xF190)

    def test_rejects_wrong_did_after_pending(self):
        transport = FakeTransport({"22f190": [b"\x7f\x22\x78", b"\x62\xf1\x98OTHER"]})
        with self.assertRaises(UDSError):
            GenericUdsClient(transport, 0x80).read_did(0xF190)

    def test_rejects_malformed_or_unrelated_negative_response(self):
        for response in (b"\x7f", b"\x7f\x22", b"\x7f\x22\x31\x00", b"\x7f\x27\x78"):
            with self.subTest(response=response):
                client = GenericUdsClient(FakeTransport({"22f190": response}), 0x80)
                with self.assertRaises(UDSError) as error:
                    client.read_did(0xF190)
                self.assertNotIsInstance(error.exception, UDSNegativeResponse)

    def test_rejects_wrong_session_echo_without_changing_state(self):
        client = GenericUdsClient(FakeTransport({"1003": b"\x50\x02"}), 0x80)
        with self.assertRaises(UDSError):
            client.enter_extended()
        self.assertEqual(client.current_session, 1)

    def test_rejects_wrong_transfer_block_echo(self):
        client = GenericUdsClient(FakeTransport({"360141": b"\x76\x02"}), 0x80)
        with self.assertRaises(UDSError):
            client.transfer_data(1, b"A")

    def test_degenerate_security_requires_key_ack(self):
        request = "2702" + "00" * 12
        for response in (None, b"\x7f\x27\x35", b"\x67\x01", b"\x67\x02\x00"):
            with self.subTest(response=response):
                transport = FakeTransport({"2701": b"\x67\x01" + b"\xff" * 31,
                                           request: response})
                client = GenericUdsClient(transport, 0x80)
                client.security_unlocked = True  # A failed new attempt clears old state.
                with self.assertRaises(UDSError):
                    client.security_access(GMSecurityAccess())
                self.assertFalse(client.security_unlocked)
                self.assertEqual(transport.sent[-1], bytes.fromhex(request))

    def test_empty_or_wrong_level_seed_never_unlocks(self):
        for response in (b"\x67\x01", b"\x67\x03" + bytes(16)):
            with self.subTest(response=response):
                client = GenericUdsClient(FakeTransport({"2701": response}), 0x80)
                with self.assertRaises(UDSError):
                    client.security_access(GMSecurityAccess())
                self.assertFalse(client.security_unlocked)

    def test_failed_direct_key_exchange_clears_previous_unlock_state(self):
        client = GenericUdsClient(FakeTransport({"270200": b"\x67\x01"}), 0x80)
        client.security_unlocked = True
        with self.assertRaises(UDSError):
            client.send_key(b"\x00")
        self.assertFalse(client.security_unlocked)

    def test_unverified_all_ff_shapes_do_not_send_key(self):
        for ecu, length, level in ((0x40, 31, 1), (0x80, 32, 1), (0x80, 31, 3)):
            with self.subTest(ecu=ecu, length=length, level=level):
                request = bytes([0x27, level])
                transport = FakeTransport({request.hex(): bytes([0x67, level]) + b"\xff" * length})
                client = GenericUdsClient(transport, ecu)
                with self.assertRaises(UDSError):
                    client.security_access(GMSecurityAccess(), level=level)
                self.assertEqual(transport.sent, [request])
                self.assertFalse(client.security_unlocked)

    def test_zero_seed_is_already_unlocked(self):
        transport = FakeTransport({"2701": b"\x67\x01" + bytes(16)})
        client = GenericUdsClient(transport, 0x80)
        self.assertTrue(client.security_access(GMSecurityAccess()))
        self.assertEqual(transport.sent, [b"\x27\x01"])

    def test_read_did_positive(self):
        t = FakeTransport({"22f190": b"\x62\xf1\x90" + PLACEHOLDER_VIN})
        c = GenericUdsClient(t, 0x80)
        self.assertEqual(c.read_did(0xF190), PLACEHOLDER_VIN)

    def test_negative_response_raises(self):
        t = FakeTransport({"22f187": b"\x7f\x22\x31"})  # requestOutOfRange
        c = GenericUdsClient(t, 0x80)
        with self.assertRaises(UDSNegativeResponse) as cm:
            c.read_did(0xF187)
        self.assertEqual(cm.exception.nrc, 0x31)

    def test_response_pending_then_positive(self):
        # first 0x78 (pending), then the real answer on recv()
        t = FakeTransport({"22f182": [b"\x7f\x22\x78", b"\x62\xf1\x82ABCD1234"]})
        c = GenericUdsClient(t, 0x80, p2_star=1.0)
        self.assertEqual(c.read_did(0xF182), b"ABCD1234")

    def test_timeout_when_no_response(self):
        t = FakeTransport({})  # no script -> None
        c = GenericUdsClient(t, 0x80)
        with self.assertRaises(UDSTimeout):
            c.read_did(0xF190)

    def test_parse_sw_inventory(self):
        blob = b"\x01ABCD1234\x00\x02WXYZ5678\xff"
        mods = parse_sw_inventory(blob)
        self.assertEqual([m.part_number for m in mods], ["ABCD1234", "WXYZ5678"])
        self.assertEqual([m.index for m in mods], [0, 1])

    def test_response_pending_runaway_is_bounded(self):
        # Y1: an ECU that floods 0x78 forever must not hang; the pending counter
        # caps it and raises UDSTimeout (not an infinite loop).
        class AlwaysPending:
            def __init__(self):
                self.recv_calls = 0

            def send_uds(self, ecu_addr, data, timeout=None):
                return b"\x7f\x22\x78"

            def recv(self, ecu_addr, timeout=5.0):
                self.recv_calls += 1
                return b"\x7f\x22\x78"

        t = AlwaysPending()
        c = GenericUdsClient(t, 0x80, p2_star=0.001, max_pending=4)
        with self.assertRaises(UDSTimeout):
            c.read_did(0xF190)
        self.assertEqual(t.recv_calls, 4)  # exactly max_pending recv cycles, then stop

    def test_read_did_uses_p2_star_first_frame_budget(self):
        # Y2: reads must get the P2* first-frame budget, not P2 (100 ms).
        class RecTransport:
            def __init__(self):
                self.timeouts = []

            def send_uds(self, ecu_addr, data, timeout=None):
                self.timeouts.append(timeout)
                return b"\x62\xf1\x90" + PLACEHOLDER_VIN

            def recv(self, ecu_addr, timeout=5.0):
                return None

        t = RecTransport()
        c = GenericUdsClient(t, 0x80, p2=0.10, p2_star=5.0)
        c.read_did(0xF190)
        self.assertEqual(t.timeouts[0], 5.0)

    def test_io_lock_serializes_keepalive_and_read(self):
        # R3: tester-present (keepalive) and a read go through one client; the
        # per-client I/O lock must keep their transport calls from overlapping.
        class ConcurrencyTransport:
            def __init__(self):
                self.lock = threading.Lock()
                self.cur = 0
                self.max = 0

            def send_uds(self, ecu_addr, data, timeout=None):
                with self.lock:
                    self.cur += 1
                    self.max = max(self.max, self.cur)
                time.sleep(0.003)
                with self.lock:
                    self.cur -= 1
                return b"\x62\xf1\x90OK" if data[0] == 0x22 else None

            def recv(self, ecu_addr, timeout=5.0):
                return None

        t = ConcurrencyTransport()
        c = GenericUdsClient(t, 0x80)
        stop = threading.Event()

        def keepalive():
            while not stop.is_set():
                c.tester_present()

        ka = threading.Thread(target=keepalive)
        ka.start()
        try:
            for _ in range(40):
                c.read_did(0xF190)
        finally:
            stop.set()
            ka.join(timeout=2.0)
        self.assertEqual(t.max, 1, "keepalive and read overlapped on the transport")


class ModuleReaderTests(unittest.TestCase):
    def _script(self):
        inv = b"\x01" + b"12345678" + b"\x00" + b"ABCDEFGH" + b"\xff"
        return {
            "1003": b"\x50\x03",
            "22f190": b"\x62\xf1\x90" + PLACEHOLDER_VIN,
            "22f0f3": b"\x62\xf0\xf3" + bytes(range(16)),   # ECUID
            "22f1a0": b"\x62\xf1\xa0" + inv,                 # SW inventory
            "22f187": b"\x7f\x22\x31",                       # unsupported
        }

    def test_read_ecu_parses_vin_ecuid_inventory(self):
        t = FakeTransport(self._script())
        reader = ModuleReader(t, catalog=EcuCatalog(), keepalive=False)
        read = reader.read_ecu(0x80, do_security=False)
        self.assertIsNone(read.error)
        self.assertEqual(read.info.name, "Radio")
        self.assertEqual(read.vin, PLACEHOLDER_VIN.decode())
        self.assertEqual(read.ecuid, bytes(range(16)).hex().upper())
        self.assertEqual(read.sw_inventory, ["12345678", "ABCDEFGH"])
        # unsupported DID recorded as not supported
        self.assertFalse(read.did(0xF187).supported)
        # a DID with no scripted response times out -> unsupported, no raise
        self.assertFalse(read.did(0xF180).supported)

    def test_security_degenerate_seed_completes_key_exchange(self):
        script = self._script()
        script["2701"] = b"\x67\x01" + b"\xff" * 31  # degenerate all-FF seed
        script["2702" + "00" * 12] = b"\x67\x02"
        t = FakeTransport(script)
        reader = ModuleReader(t, security=GMSecurityAccess(), keepalive=False)
        read = reader.read_ecu(0x80, do_security=True)
        self.assertTrue(read.security_unlocked)
        self.assertIn(b"\x27\x02" + bytes(12), t.sent)

    def test_security_cmac_key_response_sent(self):
        try:
            GMSecurityAccess.compute_cmac(bytes(16), b"")
        except SecurityCmacUnavailable:
            self.skipTest("no AES-CMAC backend")
        ecuid = bytes.fromhex("00000000000000000000000000000565")
        challenge = bytes(range(16))
        sec = GMSecurityAccess()
        sec.add_key(ecuid, b"\x33" * 16)
        key_resp = sec.compute_response(ecuid + challenge)
        script = self._script()
        script["2701"] = b"\x67\x01" + ecuid + challenge
        script["2702" + key_resp.hex()] = b"\x67\x02"
        t = FakeTransport(script)
        reader = ModuleReader(t, security=sec, keepalive=False)
        read = reader.read_ecu(0x80, do_security=True)
        self.assertTrue(read.security_unlocked)
        self.assertIn(b"\x27\x02" + key_resp, t.sent)

    def test_discover_via_broadcast(self):
        class BroadcastTransport(FakeTransport):
            def send_broadcast(self, data, timeout=2.0):
                return [(0x80, b"\x62\xf1\xb0\x01"), (0x28, b"\x62\xf1\xb0\x01")]
        reader = ModuleReader(BroadcastTransport(), catalog=EcuCatalog(), keepalive=False)
        self.assertEqual(reader.discover(), [0x28, 0x80])

    def test_discover_per_node_probe_fallback(self):
        # No broadcast; only 0x80 answers F190, others time out.
        class AddrFake(FakeTransport):
            def send_uds(self, ecu_addr, data, timeout=None):
                self.sent.append(bytes(data))
                if data[0] == 0x3E:        # tester present, suppressed
                    return None
                if ecu_addr == 0x80 and bytes(data).hex() == "22f190":
                    return b"\x62\xf1\x90" + PLACEHOLDER_VIN
                return None                # everything else times out
        reader = ModuleReader(AddrFake(), catalog=EcuCatalog(), keepalive=False)
        self.assertEqual(reader.discover(), [0x80])

    def test_discover_propagates_dependency_error_per_node(self):
        # Y4: can-isotp missing -> CanDependencyError must escape discover cleanly
        # (per-node probe path), not be mistaken for an empty/absent bus.
        class DepFail(FakeTransport):
            def send_uds(self, ecu_addr, data, timeout=None):
                raise CanDependencyError("can-isotp not installed")

        reader = ModuleReader(DepFail(), catalog=EcuCatalog(), keepalive=False)
        with self.assertRaises(CanDependencyError):
            reader.discover()

    def test_discover_propagates_dependency_error_broadcast(self):
        # Y4: same, raised from the broadcast path.
        class BcastDep(FakeTransport):
            def send_broadcast(self, data, timeout=2.0):
                raise CanDependencyError("can-isotp not installed")

        reader = ModuleReader(BcastDep(), catalog=EcuCatalog(), keepalive=False)
        with self.assertRaises(CanDependencyError):
            reader.discover()

    def test_wake_frame_constant(self):
        self.assertEqual(WAKE_NM_CAN_ID, 0x10400000)


if __name__ == "__main__":
    unittest.main()
