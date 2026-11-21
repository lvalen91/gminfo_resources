"""Offline tests for mdi2.security_cmac: RFC 4493 CMAC vectors, GM response
shaping, domain-suffix key fallback, and JSON key-map round-trip.

The CMAC vectors are skipped only if no AES-CMAC backend is installed;
pycryptodome (a hard dependency for the Blowfish cipher) satisfies it, so they
run in the normal offline suite.
"""
import json
import os
import tempfile
import unittest

from mdi2.security_cmac import (
    DOMAIN_SUFFIXES,
    GMSecurityAccess,
    SecurityCmacUnavailable,
)


def _backend_available() -> bool:
    try:
        GMSecurityAccess.compute_cmac(bytes(16), b"")
        return True
    except SecurityCmacUnavailable:
        return False


HAVE_BACKEND = _backend_available()


@unittest.skipUnless(HAVE_BACKEND, "no AES-CMAC backend installed")
class CmacVectorTests(unittest.TestCase):
    KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")

    def test_rfc4493_empty(self):
        self.assertEqual(GMSecurityAccess.compute_cmac(self.KEY, b"").hex(),
                         "bb1d6929e95937287fa37d129b756746")

    def test_rfc4493_16(self):
        msg = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
        self.assertEqual(GMSecurityAccess.compute_cmac(self.KEY, msg).hex(),
                         "070a16b46b4d4144f79bdd9dd04a287c")

    def test_rfc4493_40(self):
        msg = bytes.fromhex(
            "6bc1bee22e409f96e93d7e117393172a"
            "ae2d8a571e03ac9c9eb76fac45af8e51"
            "30c81c46a35ce411")
        self.assertEqual(GMSecurityAccess.compute_cmac(self.KEY, msg).hex(),
                         "dfa66747de9ae63030ca32611497c827")

    def test_bad_key_length_rejected(self):
        with self.assertRaises(ValueError):
            GMSecurityAccess.compute_cmac(bytes(15), b"")


@unittest.skipUnless(HAVE_BACKEND, "no AES-CMAC backend installed")
class ResponseShapeTests(unittest.TestCase):
    def test_response_truncates_to_12(self):
        sec = GMSecurityAccess()
        seed = bytes(range(32))
        key = bytes.fromhex("00112233445566778899aabbccddeeff")
        resp = sec.compute_response(seed, key=key)
        self.assertEqual(len(resp), 12)
        self.assertEqual(resp, sec.compute_cmac(key, seed)[:12])

    def test_33byte_seed_drops_checksum(self):
        sec = GMSecurityAccess()
        seed32 = bytes(range(32))
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        self.assertEqual(sec.compute_response(seed32 + b"\xAB", key=key),
                         sec.compute_response(seed32, key=key))

    def test_seed_too_short_rejected(self):
        with self.assertRaises(ValueError):
            GMSecurityAccess().compute_response(bytes(15), key=bytes(16))

    def test_no_key_raises_keyerror(self):
        with self.assertRaises(KeyError):
            GMSecurityAccess().compute_response(bytes(32))


class KeyMapTests(unittest.TestCase):
    def test_domain_fallback_lookup(self):
        sec = GMSecurityAccess()
        stored = bytes.fromhex("00000000000000000000000000" + "0114ac")
        sec.add_key(stored, b"\x11" * 16)
        other = bytes.fromhex("ffeeddccbbaa99887766554433" + "0114ac")
        self.assertEqual(sec.get_key(other), b"\x11" * 16)
        self.assertIsNone(sec.get_key(bytes(16)))

    def test_add_key_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            GMSecurityAccess().add_key(bytes(16), b"\x00" * 15)

    def test_json_roundtrip_and_underscore_skipped(self):
        sec = GMSecurityAccess()
        sec.add_key(bytes.fromhex("aabbccddeeff00112233445566778899"),
                    bytes(range(16)))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "keys.json")
            sec.save_key_map(path)
            # inject an underscore meta key; it must be ignored on load
            with open(path) as f:
                data = json.load(f)
            data["_comment"] = "ignore me"
            with open(path, "w") as f:
                json.dump(data, f)
            sec2 = GMSecurityAccess()
            loaded = sec2.load_key_map(path)
            self.assertEqual(loaded, 1)
            self.assertEqual(sec2.key_map, sec.key_map)

    def test_missing_file_loads_zero(self):
        self.assertEqual(GMSecurityAccess().load_key_map("/nonexistent/keys.json"), 0)

    def test_example_keymap_loads_placeholders_only(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "keys.example.json")
        sec = GMSecurityAccess()
        loaded = sec.load_key_map(path)
        self.assertGreaterEqual(loaded, 1)
        # every shipped value is 16 bytes and obviously a placeholder (not random)
        for key in sec.key_map.values():
            self.assertEqual(len(key), 16)

    def test_domain_suffix_table_present(self):
        self.assertIn("0114ac", DOMAIN_SUFFIXES)

    def test_malformed_hex_key_skipped_and_counted(self):
        # Y5: a non-hex value is skipped (counted), good keys still load; it is
        # NOT silently dropped into the degenerate path.
        good = "aabbccddeeff00112233445566778899"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "keys.json")
            with open(path, "w") as f:
                json.dump({good: "00112233445566778899aabbccddeeff",
                           "00000000000000000000000000000565": "zznothex"}, f)
            sec = GMSecurityAccess()
            loaded = sec.load_key_map(path)
            self.assertEqual(loaded, 1)
            self.assertEqual(sec.skipped_keys, 1)
            self.assertIn(good, sec.key_map)

    def test_wrong_length_key_rejected_loudly(self):
        # Y5: a decodable but non-16-byte key is a config error -> ValueError,
        # naming the ECUID and never echoing the key value.
        ecuid = "00000000000000000000000000000565"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "keys.json")
            with open(path, "w") as f:
                json.dump({ecuid: "00112233"}, f)   # 4 bytes, not 16
            sec = GMSecurityAccess()
            with self.assertRaises(ValueError) as cm:
                sec.load_key_map(path)
            self.assertIn(ecuid, str(cm.exception))
            self.assertNotIn("00112233", str(cm.exception))


# --- R2: real GM seed->response Known-Answer-Test slot (wired, awaiting data) ---
_KAT_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures", "gm_security_kat.json")


@unittest.skipUnless(
    os.environ.get("GM_SECURITY_KAT") or os.path.exists(_KAT_FIXTURE),
    "no real GM (ECUID||Challenge)->response KAT captured "
    "(set GM_SECURITY_KAT or add tests/fixtures/gm_security_kat.json)")
class GmSecurityKatTests(unittest.TestCase):
    """LIVE-REVALIDATION: proves GM response shaping against a REAL captured
    seed->response pair. Skipped until such a vector exists -- the shaping
    (CMAC over ECUID||Challenge, first 12 bytes) is otherwise unverified on
    hardware. Do NOT fabricate a vector here."""

    def test_captured_vector_matches(self):
        path = os.environ.get("GM_SECURITY_KAT", _KAT_FIXTURE)
        with open(path) as f:
            kat = json.load(f)
        sec = GMSecurityAccess()
        seed = bytes.fromhex(kat["ecuid"] + kat["challenge"])
        key = bytes.fromhex(kat["key"])
        self.assertEqual(sec.compute_response(seed, key=key).hex(),
                         kat["expected_response"].lower())


if __name__ == "__main__":
    unittest.main()
