"""Management sessions are released after successful and failed log pulls."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mdi2 import messages
from mdi2.logs import pull_logs


class LogCleanupTests(unittest.TestCase):
    def session(self, responses):
        channel = Mock()
        channel.recv_frames.side_effect = responses
        return SimpleNamespace(host="adapter.invalid", channels={9052: channel}), channel

    def test_releases_session_after_receive_failure(self):
        session, channel = self.session([
            [(1, b'{"data":{"session":123}}')], OSError("synthetic receive failure")])
        with self.assertRaisesRegex(OSError, "synthetic receive failure"):
            pull_logs(session, dialer_ip="dialer.invalid")
        self.assertEqual(channel.send.call_args.args, (messages.session_close(123),))

    def test_releases_session_after_parse_failure(self):
        session, channel = self.session([
            [(1, b'{"data":{"session":123}}')], [(2, bytes(501))]])
        with patch("mdi2.logs.parse_log_container", side_effect=ValueError("synthetic parse failure")):
            with self.assertRaisesRegex(ValueError, "synthetic parse failure"):
                pull_logs(session, dialer_ip="dialer.invalid")
        self.assertEqual(channel.send.call_args.args, (messages.session_close(123),))

    def test_cleanup_failure_does_not_mask_original_error(self):
        session, channel = self.session([
            [(1, b'{"data":{"session":123}}')], ValueError("original error")])
        channel.send.side_effect = [None, None, None, OSError("cleanup error")]
        with self.assertRaisesRegex(ValueError, "original error"):
            pull_logs(session, dialer_ip="dialer.invalid")

    def test_success_returns_files_and_releases_zero_session_id(self):
        session, channel = self.session([
            [(1, b'{"data":{"session":0}}')], [(2, bytes(501))]])
        files = [("synthetic.log", b"example")]
        with patch("mdi2.logs.parse_log_container", return_value=files):
            self.assertEqual(pull_logs(session, dialer_ip="dialer.invalid"), files)
        self.assertEqual(channel.send.call_args.args, (messages.session_close(0),))
