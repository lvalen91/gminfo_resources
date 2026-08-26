#!/usr/bin/env python3
"""Compute a GM/Bosch MDI2 Blowfish session key from the device serial (no extraction).

Derivation (from bvtx_vci_rt.dll FUN_10268960, verified byte-exact):
    key[i] = base_key[module_type][i] + device_serial     # 14 dwords, 32-bit add mod 2^32
module_type 0x1c = MODULE_TYPE_ID_MDI_2. base_key is a static DLL constant (below).
device_serial = the unit's serial as a uint32 (e.g. hostname "2505-88985275" -> 88985275).
Feed the returned 56-byte key to mdi2_9052_decrypt.py.

Usage: mdi2_key.py <serial_uint32>
"""
import sys, struct
BASE_KEY_MDI_2 = bytes.fromhex(
    "42197fad58f363fe07cc137065da2a5604a89114b2fd3b2f57d1bbb5"
    "16cb75461f08260d1ac2465e584013641aba6176025816164629b007")
def key_for_serial(serial: int) -> bytes:
    bd = struct.unpack("<14I", BASE_KEY_MDI_2)
    return struct.pack("<14I", *[(bd[i] + serial) & 0xffffffff for i in range(14)])
if __name__ == "__main__":
    s = int(sys.argv[1])
    print(key_for_serial(s).hex())
