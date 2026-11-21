"""GM ECU SecurityAccess (UDS 0x27) AES-128-CMAC response generator.

Additive, generic, offline-testable. This module is NOT wired into the
radio-specific live write/identify path; the vehicle-tested all-FF degenerate
0x80 unlock in ``calibration_transaction.unlock_all_ff_seed`` is unchanged. The
optional integration seam lives in ``calibration_transaction`` and only engages
when the caller supplies key material.

GM SecurityAccess (per DPS_MASTER_REFERENCE 5.4, and the richer
carplay/gm_pi/gmtool/gm_security.py copy this is ported from):

  * The 0x27 0x01 seed is ``ECUID(16) || Challenge(16) || [checksum(1)]`` --
    32 or 33 bytes. (The radio's degenerate 0x80 state instead returns 31
    all-FF bytes; that path is handled separately and NOT here.)
  * The key response is ``AES-128-CMAC(key, ECUID || Challenge)`` truncated to
    the first 12 bytes (96-bit). The trailing checksum byte of a 33-byte seed is
    NOT part of the MAC input.

*** UNVERIFIED-ON-HARDWARE (live-revalidation required) ***
The GM response shaping above -- CMAC over ECUID||Challenge, first 12 bytes -- is
ASSERTED from the ported carplay/gm_pi/gmtool/gm_security.py. It is NOT verified
against a real GM ECU: no captured (ECUID||Challenge) -> 12-byte response vector
exists in this repo, so the ``ResponseShapeTests`` only prove self-consistency
(output == CMAC(key, input)[:12]), not that the input/truncation GM actually uses
is correct. If the shaping is wrong, a real ECU returns NRC 0x35 (invalidKey) and
MAY increment the SecurityAccess attempt counter toward a 0x36/0x37 lockout.
Capture a real seed->response pair and wire it into the KAT fixture
(``tests/fixtures/gm_security_kat.json``, consumed by the skipped test in
``tests/test_security_cmac.py``) before trusting this on hardware.
  * One master key is shared across an ECUID "domain" (ECUID suffix); a key
    stored under any ECUID in the domain unlocks every module in that domain
    (``DOMAIN_SUFFIXES``).

Keys are NEVER committed. Ship ``keys.example.json`` (placeholders only) and load
the real map from a configurable, git-ignored path -- see ``load_key_map`` and the
``MDI2_KEYMAP`` note in the README. All values here are examples/placeholders.

CMAC backend: pycryptodome (already required for the Blowfish cipher) is used
when present; the ``cryptography`` package is accepted as an optional fallback.
Both are imported lazily so this module imports with neither installed.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)


# ECUID-suffix -> security domain name (DPS_MASTER_REFERENCE 5.4). A key stored
# under one of these suffixes unlocks every module sharing the domain. These are
# protocol identifiers (public ECUID structure), not secrets.
DOMAIN_SUFFIXES: Dict[str, str] = {
    "0114a6": "powertrain_body",   # ECM, TCM, EOCM, VCM, FSCM, TEHCM
    "000565": "body_control",      # BCM
    "614614b2": "chassis_safety",  # IPC, EBCM
    "0114ac": "infotainment",      # Radio 0x80
    "0114aa": "tcm2",              # TCM2
}


class SecurityCmacUnavailable(RuntimeError):
    """No AES-CMAC backend (pycryptodome or cryptography) is installed."""


def _compute_cmac(key: bytes, data: bytes) -> bytes:
    """AES-128-CMAC per RFC 4493 -> 16-byte tag. Lazy backend selection."""
    if len(key) != 16:
        raise ValueError(f"Key must be 16 bytes (AES-128), got {len(key)}")
    try:
        from Crypto.Cipher import AES          # pycryptodome (already a dep)
        from Crypto.Hash import CMAC
        c = CMAC.new(key, ciphermod=AES)
        c.update(data)
        return c.digest()
    except ImportError:
        pass
    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import algorithms
        from cryptography.hazmat.primitives.cmac import CMAC as CCMAC
        c = CCMAC(algorithms.AES(key), backend=default_backend())
        c.update(data)
        return c.finalize()
    except ImportError:
        raise SecurityCmacUnavailable(
            "install pycryptodome (preferred) or cryptography for AES-CMAC")


def _clean_hex(s: str) -> str:
    return s.lower().replace(" ", "").replace(":", "").replace("0x", "")


class GMSecurityAccess:
    """AES-128-CMAC response generator keyed by ECUID (with domain fallback)."""

    def __init__(self, key_map_path: Optional[str] = None):
        self.key_map: Dict[str, bytes] = {}
        self.skipped_keys = 0
        if key_map_path:
            self.load_key_map(key_map_path)

    # ------------------------------------------------------------------ keys
    def load_key_map(self, path: str) -> int:
        """Load ``{ecuid_hex: key_hex}`` JSON. Keys beginning with ``_`` (e.g.
        ``_comment``) are ignored. Missing file -> 0 loaded, no error.

        A value that is not valid hex is SKIPPED with a warning naming the ECUID
        (never the key value) and counted in ``self.skipped_keys`` -- silently
        dropping it would downgrade an unlock to the degenerate all-FF path
        without the operator knowing. A value whose decoded length is not 16
        bytes (AES-128) is REJECTED LOUDLY with ``ValueError`` (ECUID named, key
        value never echoed), because a wrong-length key is a configuration error,
        not a tolerable omission."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return 0
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in key map {path}: {e}")

        loaded = 0
        skipped = 0
        for ecuid_hex, key_hex in data.items():
            if ecuid_hex.startswith("_"):
                continue
            ecuid_clean = _clean_hex(ecuid_hex)
            try:
                key = bytes.fromhex(_clean_hex(key_hex))
            except (ValueError, AttributeError):
                skipped += 1
                log.warning("key map %s: skipping ECUID %s (value is not valid "
                            "hex)", path, ecuid_clean)
                continue
            if len(key) != 16:
                raise ValueError(
                    f"key map {path}: ECUID {ecuid_clean} has a {len(key)}-byte "
                    f"key; AES-128 requires exactly 16 bytes")
            self.key_map[ecuid_clean] = key
            loaded += 1
        self.skipped_keys = skipped
        if skipped:
            log.warning("key map %s: %d malformed entr%s skipped; those modules "
                        "will fall back to the degenerate unlock path",
                        path, skipped, "y" if skipped == 1 else "ies")
        return loaded

    def save_key_map(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({ecuid: key.hex() for ecuid, key in self.key_map.items()},
                      f, indent=2)

    def add_key(self, ecuid: bytes, key: bytes) -> None:
        if len(key) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(key)}")
        self.key_map[ecuid.hex().lower()] = key

    def get_key(self, ecuid: bytes) -> Optional[bytes]:
        """Exact ECUID match, then domain-suffix fallback."""
        ecuid_hex = ecuid.hex().lower()
        if ecuid_hex in self.key_map:
            return self.key_map[ecuid_hex]
        for suffix in DOMAIN_SUFFIXES:
            if ecuid_hex.endswith(suffix):
                for stored_ecuid, key in self.key_map.items():
                    if stored_ecuid.endswith(suffix):
                        return key
        return None

    def has_key(self, ecuid: bytes) -> bool:
        return self.get_key(ecuid) is not None

    # --------------------------------------------------------------- crypto
    @staticmethod
    def compute_cmac(key: bytes, data: bytes) -> bytes:
        """AES-128-CMAC per RFC 4493 -> 16-byte tag."""
        return _compute_cmac(key, data)

    def compute_response(self, seed: bytes, key: Optional[bytes] = None) -> bytes:
        """Return the 12-byte key response for an ECU seed.

        GM seed = ECUID(16) || Challenge(16) || [checksum(1)]. The CMAC is taken
        over ECUID||Challenge (a trailing 33rd checksum byte is NOT part of the
        MAC input) and truncated to the first 12 bytes (96-bit).
        """
        if len(seed) < 16:
            raise ValueError(f"Seed too short: {len(seed)} bytes (need >=16)")
        ecuid = seed[:16]
        if key is None:
            key = self.get_key(ecuid)
            if key is None:
                raise KeyError(f"No key for ECUID {ecuid.hex()}")
        mac_input = seed[:32] if len(seed) == 33 else seed
        return self.compute_cmac(key, mac_input)[:12]

    # ---------------------------------------------------------------- parse
    @staticmethod
    def parse_seed(seed: bytes) -> dict:
        out = {"raw": seed, "raw_hex": seed.hex(), "length": len(seed)}
        if len(seed) >= 16:
            out["ecuid"] = seed[:16]
            out["ecuid_hex"] = seed[:16].hex()
        if len(seed) >= 32:
            out["challenge"] = seed[16:32]
            out["challenge_hex"] = seed[16:32].hex()
        if len(seed) == 33:
            out["checksum"] = seed[32]
        return out

    def format_seed(self, seed: bytes) -> str:
        p = self.parse_seed(seed)
        lines = [f"Seed ({p['length']} bytes): {p['raw_hex']}"]
        if "ecuid_hex" in p:
            lines.append(f"  ECUID:     {p['ecuid_hex']}")
        if "challenge_hex" in p:
            lines.append(f"  Challenge: {p['challenge_hex']}")
        if "checksum" in p:
            lines.append(f"  Checksum:  {p['checksum']:02x}")
        return "\n".join(lines)
