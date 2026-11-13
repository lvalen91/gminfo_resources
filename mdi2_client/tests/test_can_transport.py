"""Offline tests for mdi2.can_transport: imports cleanly without python-can /
can-isotp, addressing math, and not-connected guards. No hardware."""
import threading
import time
import unittest

from mdi2 import can_transport as ct
from mdi2.can_transport import (CANTransport, CanDependencyError, can_req_id,
                                can_rsp_id, recognize_responder, rsp_id_for)
from mdi2.ecu_catalog import EcuCatalog


class _FakeStack:
    """Minimal ISO-TP stack stand-in: scripted RX queue + send hook."""

    def __init__(self, preload=()):
        self.rx = list(preload)
        self.sent = []
        self.on_send = None          # callable(data) -> response bytes | None
        self.raise_on_send = None    # Exception to raise from send()

    def send(self, data):
        self.sent.append(bytes(data))
        if self.raise_on_send is not None:
            raise self.raise_on_send
        if self.on_send is not None:
            r = self.on_send(bytes(data))
            if r is not None:
                self.rx.append(r)

    def process(self):
        pass

    def available(self):
        return len(self.rx) > 0

    def recv(self):
        return self.rx.pop(0) if self.rx else None


class CanAddressingTests(unittest.TestCase):
    def test_module_imports_without_can_deps(self):
        # Reaching here means `import mdi2.can_transport` did not require python-can.
        self.assertTrue(hasattr(ct, "CANTransport"))

    def test_physical_addressing_ids(self):
        self.assertEqual(can_req_id(0x80), 0x14DA80F1)
        self.assertEqual(can_rsp_id(0x80), 0x14DAF180)
        self.assertEqual(can_req_id(0x11), 0x14DA11F1)
        self.assertEqual(can_rsp_id(0x11), 0x14DAF111)

    def test_isotp_params_bench_values(self):
        self.assertEqual(ct.ISOTP_PARAMS["stmin"], 0)
        self.assertEqual(ct.ISOTP_PARAMS["blocksize"], 0)

    def test_functional_id(self):
        self.assertEqual(ct.FUNCTIONAL_REQ_ID, 0x18DB33F1)


class CanGuardTests(unittest.TestCase):
    def test_not_connected_returns_none_or_empty(self):
        t = CANTransport("can0")
        self.assertFalse(t.connected)
        self.assertIsNone(t.send_uds(0x80, b"\x22\xf1\x90"))
        self.assertIsNone(t.recv(0x80))
        self.assertEqual(t.send_broadcast(b"\x22\xf1\xb0"), [])

    def test_disconnect_is_idempotent(self):
        t = CANTransport("can0")
        t.disconnect()
        t.disconnect()
        self.assertFalse(t.connected)

    def test_connect_without_python_can_returns_false(self):
        # python-can is not a hard dep; if absent, connect() must fail gracefully.
        try:
            import can  # noqa: F401
            self.skipTest("python-can is installed; graceful-absence path not exercised")
        except ImportError:
            self.assertFalse(CANTransport("can0").connect())


class RspIdResolverTests(unittest.TestCase):
    """R1: per-ECU response id comes from the catalog, formula is fallback only."""

    def setUp(self):
        self.cat = EcuCatalog()

    def test_rsp_id_uses_catalog_for_known_ecus(self):
        for addr, info in self.cat.ecus.items():
            self.assertEqual(rsp_id_for(addr), info.can_rsp,
                             f"rsp_id_for(0x{addr:02X}) must match catalog can_rsp")

    def test_hvac_rsp_id_is_corrected_value(self):
        # Regression for the 0x141A->0x145A typo fix.
        self.assertEqual(rsp_id_for(0x68), 0x145AF168)

    def test_radio_rsp_id_is_module_specific_not_gateway_form(self):
        self.assertEqual(rsp_id_for(0x80), 0x145AF180)
        self.assertNotEqual(rsp_id_for(0x80), can_rsp_id(0x80))  # not the 0xDA formula

    def test_unknown_ecu_falls_back_to_formula(self):
        # 0xEE is not in the catalog -> formula fallback (low-16 still correct).
        self.assertEqual(rsp_id_for(0xEE), can_rsp_id(0xEE))
        self.assertEqual(rsp_id_for(0xEE) & 0xFFFF, 0xF100 | 0xEE)


class RecognizeResponderTests(unittest.TestCase):
    """R1: discovery responder recognition (catalog set OR 0xF1<ecu> low-16)."""

    def test_catalog_response_id_recognized(self):
        self.assertEqual(recognize_responder(0x145AF168), 0x68)  # HVAC, 0x5A PF
        self.assertEqual(recognize_responder(0x142AF111), 0x11)  # ECM, 0x2A PF
        self.assertEqual(recognize_responder(0x14DAF145), 0x45)  # gateway, 0xDA PF

    def test_low16_invariant_recognized_regardless_of_pf(self):
        # Any PF byte with 0xF1<ecu> low 16 is accepted (module-specific PF).
        self.assertEqual(recognize_responder(0x149AF180), 0x80)
        self.assertEqual(recognize_responder(0x0000F128), 0x28)

    def test_non_responder_rejected(self):
        self.assertIsNone(recognize_responder(0x18DB33F1))  # functional request id
        self.assertIsNone(recognize_responder(0x14DA80F1))  # a REQUEST id, not rsp
        self.assertIsNone(recognize_responder(0x12345678))


class SendUdsBehaviorTests(unittest.TestCase):
    """Y3: stale-frame flush, stack reset on error, dependency propagation."""

    def _transport_with_stack(self, stack):
        t = CANTransport("can0")
        t.connected = True
        t.bus = object()            # non-None sentinel; stack is pre-injected
        t._stacks[0x80] = stack
        return t

    def test_stale_rx_flushed_before_send(self):
        # A late frame from a prior timed-out request is buffered; it must NOT be
        # returned for the new request.
        stack = _FakeStack(preload=[b"\x62\xf1\x11STALE"])
        stack.on_send = lambda data: b"\x62\xf1\x90FRESH"
        t = self._transport_with_stack(stack)
        resp = t.send_uds(0x80, b"\x22\xf1\x90", timeout=1.0)
        self.assertEqual(resp, b"\x62\xf1\x90FRESH")

    def test_transport_error_resets_cached_stack(self):
        stack = _FakeStack()
        stack.raise_on_send = OSError("bus-off")
        t = self._transport_with_stack(stack)
        self.assertIsNone(t.send_uds(0x80, b"\x22\xf1\x90", timeout=1.0))
        self.assertNotIn(0x80, t._stacks)   # dropped so next request rebuilds it

    def test_programming_error_not_swallowed(self):
        stack = _FakeStack()
        stack.raise_on_send = TypeError("bug in our code")
        t = self._transport_with_stack(stack)
        with self.assertRaises(TypeError):
            t.send_uds(0x80, b"\x22\xf1\x90", timeout=1.0)
        self.assertNotIn(0x80, t._stacks)

    def test_dependency_error_propagates_from_send_uds(self):
        # No cached stack + can-isotp absent -> _stack_for raises; must propagate
        # (so the CLI can map it to a clean install message), not return None.
        t = CANTransport("can0")
        t.connected = True
        t.bus = object()
        try:
            import isotp  # noqa: F401
            self.skipTest("can-isotp installed; dependency-missing path not exercised")
        except ImportError:
            with self.assertRaises(CanDependencyError):
                t.send_uds(0x80, b"\x22\xf1\x90", timeout=0.5)


class TransportLockSerializationTests(unittest.TestCase):
    """R3: the CANTransport RLock serializes concurrent bus access."""

    def test_concurrent_send_uds_never_overlaps(self):
        state = {"cur": 0, "max": 0}
        glock = threading.Lock()

        class CStack:
            def __init__(self):
                self.rx = []

            def send(self, data):
                with glock:
                    state["cur"] += 1
                    state["max"] = max(state["max"], state["cur"])
                time.sleep(0.02)
                self.rx.append(b"\x62\xf1\x90OK")
                with glock:
                    state["cur"] -= 1

            def process(self):
                pass

            def available(self):
                return len(self.rx) > 0

            def recv(self):
                return self.rx.pop(0) if self.rx else None

        t = CANTransport("can0")
        t.connected = True
        t.bus = object()
        t._stacks = {0x80: CStack(), 0x28: CStack()}

        threads = [threading.Thread(target=t.send_uds, args=(a, b"\x22\xf1\x90", 1.0))
                   for a in (0x80, 0x28)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=2.0)
        self.assertEqual(state["max"], 1, "two send_uds calls overlapped on the bus")


if __name__ == "__main__":
    unittest.main()
