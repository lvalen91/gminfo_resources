"""Offline CLI tests for the additive `security` and `read-all` subcommands.

Existing subcommands (scan/key/connect/rearm/identify/recover/write) are not
touched here. `security` is a pure dry-run computation; `read-all` is exercised
only on its offline error paths (no CAN hardware)."""
import unittest

from typer.testing import CliRunner

from mdi2.cli import app
from mdi2.security_cmac import GMSecurityAccess, SecurityCmacUnavailable

runner = CliRunner()


def _have_backend():
    try:
        GMSecurityAccess.compute_cmac(bytes(16), b"")
        return True
    except SecurityCmacUnavailable:
        return False


class SecurityCliTests(unittest.TestCase):
    @unittest.skipUnless(_have_backend(), "no AES-CMAC backend")
    def test_security_with_explicit_key_matches_library(self):
        seed = bytes(range(32))
        key = bytes.fromhex("00112233445566778899aabbccddeeff")
        expected = GMSecurityAccess().compute_response(seed, key=key).hex()
        result = runner.invoke(app, ["security", seed.hex(), "--key", key.hex()])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(expected, result.output)

    def test_security_without_key_exits_nonzero(self):
        # All-zero ECUID is absent from the placeholder map -> KeyError -> exit 1.
        seed = (bytes(16) + bytes(range(16))).hex()
        result = runner.invoke(app, ["security", seed])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("no key", result.output.lower())

    @unittest.skipUnless(_have_backend(), "no AES-CMAC backend")
    def test_security_output_flags_unverified_shaping(self):
        # R2: the dry-run output must warn the shaping is unverified on hardware.
        seed = bytes(range(32))
        key = bytes.fromhex("00112233445566778899aabbccddeeff")
        result = runner.invoke(app, ["security", seed.hex(), "--key", key.hex()])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("UNVERIFIED", result.output)

    def test_keymap_help_does_not_claim_autoload(self):
        # Y5: the --key-map help must not claim the example is a loaded default.
        out = runner.invoke(app, ["security", "--help"]).output.lower()
        self.assertIn("key-map", out)
        self.assertNotIn("default: bundled", out)

    def test_help_lists_new_commands(self):
        out = runner.invoke(app, ["--help"]).output
        self.assertIn("security", out)
        self.assertIn("read-all", out)
        # existing commands still present
        for cmd in ("rearm", "identify", "recover", "write"):
            self.assertIn(cmd, out)


class ReadAllCliTests(unittest.TestCase):
    def test_unsupported_transport_rejected(self):
        result = runner.invoke(app, ["read-all", "--transport", "doip"])
        self.assertNotEqual(result.exit_code, 0)

    def test_can_connect_failure_exits_one(self):
        # No python-can / no bus -> connect() returns False -> exit 1.
        result = runner.invoke(app, ["read-all", "--interface", "can0"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("connect failed", result.output.lower())


if __name__ == "__main__":
    unittest.main()
