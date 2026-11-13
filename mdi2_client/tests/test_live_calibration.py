"""Offline regressions for startup, source preflight and reset/write ordering."""
import struct
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mdi2 import live_calibration as live
from mdi2.calibration_readback import Readback
from mdi2.calibration_transaction import ProgramResult, TransactionError


VIN = b"A" * 17


class StartupTests(unittest.TestCase):
    def test_force_start_uses_fresh_session_and_releases_it(self):
        session = Mock()
        ch52, ch50 = Mock(), Mock()
        session.channels = {9052: ch52, 9050: ch50}
        ch52.recv_frames.return_value = [(1, b'{"data":{"session":123}}')]
        ch50.recv_frames.side_effect = [[], [(1, b"PDU START")]]
        with patch.object(live, "Session", return_value=session), \
             patch.object(live, "_port_open", return_value=True):
            self.assertTrue(live.rearm_dpdu_tunnel(123, "adapter.invalid",
                            dialer_ip="dialer.invalid", force_start=True))
        self.assertEqual(session.connect.call_args_list[1].kwargs, {"ports": [9011]})
        sent = [call.args[0] for call in ch50.send.call_args_list]
        self.assertEqual(sent[:3], [live._PDU_POLL] * 3)
        self.assertEqual(sent[3], live._PDU_START_PREFIX + struct.pack("<I", 123))
        self.assertEqual(ch52.send.call_count, 2)  # open and close
        session.close.assert_called_once()

    def test_missing_start_ack_fails_and_closes_management_session(self):
        session = Mock()
        ch52, ch50 = Mock(), Mock()
        session.channels = {9052: ch52, 9050: ch50}
        ch52.recv_frames.return_value = [(1, b'{"data":{"session":123}}')]
        ch50.recv_frames.return_value = []
        with patch.object(live, "Session", return_value=session), \
             self.assertRaisesRegex(live.LiveDpduError, "did not echo"):
            live.rearm_dpdu_tunnel(123, "adapter.invalid", dialer_ip="dialer.invalid", force_start=True)
        session.close.assert_called_once()

    def test_partial_socket_startup_is_closed(self):
        command = Mock()
        with patch.object(live.socket, "create_connection",
                          side_effect=[command, TimeoutError("injected")]), \
             self.assertRaises(TimeoutError):
            live._open_session("adapter.invalid", 1)
        command.close.assert_called_once()

    def test_partial_link_creation_closes_session(self):
        session = Mock()
        session.create_radio_cll.return_value = (2, 1)
        session.create_keepalive_cll.side_effect = live.LiveDpduError("injected")
        with self.assertRaises(live.LiveDpduError):
            live.LiveRadioLink(session)
        session.close.assert_called_once()


class PowerModeTests(unittest.TestCase):
    def test_only_bcm_off_is_allowed_and_link_is_destroyed(self):
        for mode in (0, 1, 2, 4):
            with self.subTest(mode=mode):
                session = Mock(closed=False)
                session.create_radio_cll.return_value = (9, 10)
                with patch.object(live, "LiveRadioAdapter"), patch.object(live, "UdsClient"), \
                     patch.object(live, "_read_did", return_value=b"\x62\xf0\x85" + bytes([mode])):
                    if mode == 0:
                        live._require_power_off(session, 1)
                    else:
                        with self.assertRaisesRegex(TransactionError, "OFF"):
                            live._require_power_off(session, 1)
                session.create_radio_cll.assert_called_once_with(
                    live.BCM_REQUEST_CAN_ID, live.BCM_RESPONSE_CAN_ID)
                session.destroy_cll.assert_called_once_with(9)


class PlanTests(unittest.TestCase):
    def test_high_country_source_is_reported_without_requiring_target_match(self):
        session, link = Mock(), Mock()
        with patch.object(live, "validate_ltz_package", return_value=()) as package, \
             patch.object(live, "rearm_dpdu_tunnel", return_value=True), \
             patch.object(live, "_open_session", return_value=session), \
             patch.object(live, "LiveRadioLink", return_value=link), \
             patch.object(live, "_probe_radio_reachable", return_value=VIN), \
             patch.object(live, "_read_did", return_value=b"metadata"), \
             patch.object(live, "identify_source_calibration", return_value="High Country"), \
             patch.object(live, "_require_power_off") as power, \
             patch.object(live, "_require_voltage") as voltage:
            plan = live.plan_ltz_write(Path("unused"), 123, VIN, sample_voltage=False)
        self.assertEqual(plan.source_calibration, "High Country")
        self.assertIsNone(plan.battery_mv)
        package.assert_called_once()
        power.assert_called_once_with(session, 6.0)
        voltage.assert_not_called()
        link.close.assert_called_once()

    def test_confirmed_cli_does_not_run_an_extra_voltage_preflight(self):
        from mdi2.cli import write
        outcome = SimpleNamespace(transaction=ProgramResult("complete", 14),
                                  readback=Readback(tuple(range(2, 16)), (), bytes(2), bytes(2)))
        with patch.object(live, "plan_ltz_write") as plan, \
             patch.object(live, "write_ltz_calibration", return_value=outcome) as writer, \
             patch("typer.echo"):
            write("unused", VIN.decode(), 123, host="adapter.invalid", confirm=True,
                  pre_reset=False)
        plan.assert_not_called()
        writer.assert_called_once_with(Path("unused"), 123, VIN, "adapter.invalid",
                                       confirmed=True, pre_reset=False)


class WriteSequenceTests(unittest.TestCase):
    def run_workflow(self, *, pre_reset=False, reset_reply=b"\x51\x01",
                     bad_write_vin=False, voltage_error=False):
        events = []
        count = 3 if pre_reset else 2
        clients = [Mock() for _ in range(count)]
        links = [Mock() for _ in clients]
        for link, client in zip(links, clients):
            link.client.return_value = client
        # Write link is links[1] under pre_reset (links[0] is the reset link),
        # else links[0]. Verify link is always the last.
        write_client = clients[1] if pre_reset else clients[0]

        def request(payload, prefix):
            if payload == b"\x11\x01":
                events.append("reset")
                return reset_reply
            return prefix

        for client in clients:
            client.request.side_effect = request

        def read_did(client, did):
            if did == b"\xf1\x90":
                if bad_write_vin and client is write_client:
                    return b"\x62" + did + b"B" * 17
                return b"\x62" + did + VIN
            return b"\x62" + did + bytes(2)

        def voltage(_session):
            events.append("voltage")
            if voltage_error:
                raise TransactionError("battery voltage outside programming window")
            return 12500

        def program(*args, **kwargs):
            events.append("program")
            return ProgramResult("complete", 14)

        plan = SimpleNamespace(calibrations=(), source_calibration="High Country")
        patches = {
            "plan_ltz_write": Mock(return_value=plan),
            "rearm_dpdu_tunnel": Mock(return_value=True),
            "_open_session": Mock(side_effect=[Mock() for _ in range(count)]),
            "LiveRadioLink": Mock(side_effect=links),
            "_read_did": Mock(side_effect=read_did),
            "_require_power_off": Mock(side_effect=lambda *_: events.append("off")),
            "_require_voltage": Mock(side_effect=voltage),
            "identify_source_calibration": Mock(return_value="High Country"),
            "program": Mock(side_effect=program),
            "compare_post_reboot": Mock(return_value=Readback(tuple(range(2, 16)), (), b"\x00\x00", b"\x00\x00")),
        }
        try:
            with ExitStack() as stack:
                for name, mock in patches.items():
                    stack.enter_context(patch.object(live, name, mock))
                stack.enter_context(patch.object(live.time, "sleep"))
                stack.enter_context(patch("mdi2.calibration_transaction.unlock_security_access"))
                self.result = live.write_ltz_calibration(Path("unused"), 123, VIN,
                                                         confirmed=True, pre_reset=pre_reset)
        finally:
            self.events, self.links, self.patches = events, links, patches

    def test_sps_default_takes_one_voltage_sample_and_no_pre_reset(self):
        self.run_workflow()
        # Stock SPS: no pre-reset; the only radio 11 01 happens inside program().
        self.assertEqual(self.events, ["off", "voltage", "program"])
        self.assertNotIn("reset", self.events)
        self.assertEqual(self.result.transaction.slots_transferred, 14)
        self.assertEqual(len(self.links), 2)
        self.patches["plan_ltz_write"].assert_called_once_with(
            Path("unused"), 123, VIN, live.DEVICE_IP_DEFAULT, timeout=8.0,
            sample_voltage=False, fresh_start=True)
        for link in self.links:
            link.close.assert_called_once()

    def test_pre_reset_opt_in_runs_hard_reset_then_program(self):
        self.run_workflow(pre_reset=True)
        self.assertEqual(self.events, ["off", "reset", "off", "voltage", "program"])
        self.assertEqual(self.result.transaction.slots_transferred, 14)
        self.assertEqual(len(self.links), 3)
        for link in self.links:
            link.close.assert_called_once()

    def test_pre_reset_mismatch_never_programs(self):
        with self.assertRaisesRegex(TransactionError, "hard reset failed"):
            self.run_workflow(pre_reset=True, reset_reply=b"\x51\x01\x00")
        self.assertNotIn("program", self.events)
        self.assertNotIn("voltage", self.events)
        self.links[0].close.assert_called_once()

    def test_pre_write_identity_failure_closes_without_programming(self):
        with self.assertRaisesRegex(TransactionError, "pre-write VIN mismatch"):
            self.run_workflow(bad_write_vin=True)
        self.assertNotIn("program", self.events)
        self.links[0].close.assert_called_once()

    def test_bad_voltage_never_programs(self):
        with self.assertRaisesRegex(TransactionError, "voltage"):
            self.run_workflow(voltage_error=True)
        self.assertNotIn("program", self.events)
        self.links[0].close.assert_called_once()

    def test_invalid_transfer_limit_fails_before_reset(self):
        with patch.object(live, "plan_ltz_write") as plan, self.assertRaises(ValueError):
            live.write_ltz_calibration(Path("unused"), 123, VIN, confirmed=True,
                                      adapter_max_request_length=19)
        plan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
