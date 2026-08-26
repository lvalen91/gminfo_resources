"""MDI2 900x/9052 cipher: standard Blowfish-ECB (big-endian) with a per-device key.

Key derivation (bvtx_vci_rt.dll FUN_10268960, verified byte-exact):
    key[i] = base_key[module_type][i] + device_serial     # 14 dwords, 32-bit add mod 2^32
"""
import struct
from Crypto.Cipher import Blowfish   # pycryptodome

# static base key for MODULE_TYPE_ID_MDI_2 (DAT_10309d60 entry id 0x1c, +0xC4)
BASE_KEY_MDI_2 = bytes.fromhex(
    "42197fad58f363fe07cc137065da2a5604a89114b2fd3b2f57d1bbb5"
    "16cb75461f08260d1ac2465e584013641aba6176025816164629b007")

def derive_key(device_serial: int, base_key: bytes = BASE_KEY_MDI_2) -> bytes:
    """56-byte Blowfish key for a unit, from its serial (uint32)."""
    bd = struct.unpack("<14I", base_key)
    return struct.pack("<14I", *[(d + device_serial) & 0xffffffff for d in bd])

def decrypt(key: bytes, body: bytes) -> bytes:
    body = body[: len(body) - len(body) % 8]
    return Blowfish.new(key, Blowfish.MODE_ECB).decrypt(body)

def encrypt(key: bytes, plaintext: bytes) -> bytes:
    pad = (-len(plaintext)) % 8
    return Blowfish.new(key, Blowfish.MODE_ECB).encrypt(plaintext + b"\x00" * pad)
