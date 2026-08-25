#!/usr/bin/env python3
"""
ota_isys_frame_fuzzer.py (corrected)

Black-box mutation tool for /dev/ghs/ota-isys targeting the length-prefixed
command frame described in RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md.

AUTHORIZATION: for AUTHORIZED vulnerability research on owned hardware only.
SAFETY: defaults to read-only/dry-run. --send is the ONLY way to write to
the device; there is no other flag that flips it.

ARTIFACT REFERENCES:
- [C] /dev/ghs/ota-isys node exists (ghs_str.txt:44239)
- [I] Command frame is length-prefixed ("Bad command length for OTA command.",
  ghs_str.txt:38092)
- [U] Ioctl numbers are unknown (repo prior probe used guesses _IOR('g', 0x01-0x02, int))
- [U] Exact frame layout (opcode offset, length width) is unknown
  (.ota_update.text not disassembled)

Fix log vs. the first draft:
  1. Removed the dead `--dry-run` argument. It was `action="store_true",
     default=True` with no negation flag, so it could never be set False and
     was never actually checked anywhere control flow depended on -- `--send`
     was always the real gate. Having both was confusing API surface for no
     functional benefit. `--send` (default False) is now the single toggle.
"""

import argparse
import os
import sys
import time
import struct
import logging
from datetime import datetime

# --- CONFIGURATION & CONSTANTS ---

# [U] Ioctl numbers are explicitly UNKNOWN per artifact §2.5.
# The repo's prior probe used GUESSED codes (_IOR('g', 0x01-0x02, int)).
# We do NOT hardcode these as truth. Default is raw write(); ioctl is opt-in
# and requires the operator to supply a real code.
IOCTL_GUESS_BASE = ord('g')  # [U] repo prior probe guess, reference only
IOCTL_GUESS_NUMS = [0x01, 0x02]  # [U] repo prior probe guess, reference only

# [I] Frame layout is inferred from "Bad command length" string.
# Parameterized so the operator can adjust once real layout is confirmed.
DEFAULT_LENGTH_OFFSET = 0      # [U] assumed start of frame
DEFAULT_LENGTH_SIZE = 4        # [U] assumed 32-bit integer (common for lengths)
DEFAULT_LENGTH_ENDIAN = '<'    # [U] assumed little-endian (x86 target)


def setup_logger(log_file):
    logger = logging.getLogger("ota_fuzzer")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


logger = logging.getLogger("ota_fuzzer")  # re-initialized in main() with real log path


def construct_frame(payload: bytes, length_field_offset: int, length_field_size: int,
                     declared_length: int, endian: str) -> bytes:
    """
    Constructs a command frame with a potentially mismatched length field.

    [I] Based on artifact §2.1: a command frame carries a length field that
    can be "bad" (rejected).
    [U] Exact layout (opcode vs length position) is unknown. This tool models
    Frame = [padding for length_field_offset bytes] + [length field] + [payload].
    If real RE (RECON_TODO #1/#2) shows an opcode field precedes the length
    field, set --length-offset accordingly; this tool fills that region with
    zero bytes as a placeholder, NOT a guessed opcode value.

    ASSUMPTION: the device expects the length field to literally be part of
    the byte stream written to the node (matches the "dumb pipe" raw-write
    description in artifact §3(b)); if libghs_lip.so turns out to require a
    specific ioctl framing instead (RECON_TODO #2), this model is wrong and
    --use-ioctl must be used.
    """
    if length_field_size == 2:
        fmt = f"{endian}H"
    elif length_field_size == 4:
        fmt = f"{endian}I"
    elif length_field_size == 8:
        fmt = f"{endian}Q"
    else:
        raise ValueError(f"Unsupported length field size: {length_field_size}")

    padding = b'\x00' * length_field_offset
    length_bytes = struct.pack(fmt, declared_length & ((1 << (length_field_size * 8)) - 1))
    return padding + length_bytes + payload


def generate_malformed_frames(payload: bytes, base_offset: int, base_size: int, endian: str):
    """Fuzz-target #1 (artifact §6): declared_length vs actual_payload mismatch."""
    cases = []

    cases.append((
        construct_frame(payload, base_offset, base_size, len(payload), endian),
        f"CONTROL: Len={len(payload)}"))

    cases.append((
        construct_frame(payload, base_offset, base_size, max(0, len(payload) - 1), endian),
        f"UNDERFLOW: Declared={max(0, len(payload) - 1)}, Actual={len(payload)}"))

    cases.append((
        construct_frame(payload, base_offset, base_size, len(payload) + 1024, endian),
        f"OVERFLOW: Declared={len(payload) + 1024}, Actual={len(payload)}"))

    cases.append((
        construct_frame(payload, base_offset, base_size, 0, endian),
        f"ZERO_LEN: Declared=0, Actual={len(payload)}"))

    max_val = (1 << (base_size * 8)) - 1
    cases.append((
        construct_frame(payload, base_offset, base_size, max_val, endian),
        f"MAX_VAL: Declared={max_val}, Actual={len(payload)}"))

    cases.append((
        construct_frame(payload, base_offset, base_size, len(payload) + 1, endian),
        f"OFF_BY_ONE: Declared={len(payload) + 1}, Actual={len(payload)}"))

    return cases


def check_device_permissions(device_path: str) -> bool:
    """
    [C] Artifact notes DAC is rw-rw-rw- on the node (HARDWARE_HYPERVISOR_
    ATTACK_VECTORS.md:178). SELinux domain is the real gate (RECON_TODO #4).
    This function only opens (permission probe) and immediately closes --
    it does not write.
    """
    try:
        stat_info = os.stat(device_path)
        perms = oct(stat_info.st_mode)[-3:]
        logger.info(f"[RECON] Device {device_path} permissions: {perms}")
        fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
        os.close(fd)
        logger.info("[RECON] Device opened successfully (R/W).")
        return True
    except PermissionError:
        logger.error("[RECON] Permission denied. Check SELinux context (ls -Z) or run as root.")
        return False
    except FileNotFoundError:
        logger.error(f"[RECON] Device {device_path} not found.")
        return False


def send_frame(device_path: str, frame: bytes, use_ioctl: bool = False, ioctl_code: int = None) -> bool:
    """
    [U] Ioctl numbers are unknown. If use_ioctl=True, operator must supply a
    real code (RECON_TODO #2). Default is raw write(), matching the "dumb
    pipe" description in artifact §3(b).
    """
    try:
        fd = os.open(device_path, os.O_RDWR)
        if use_ioctl and ioctl_code is not None:
            import fcntl
            logger.debug(f"[SEND] Attempting IOCTL {hex(ioctl_code)} (UNVERIFIED [U])")
            try:
                fcntl.ioctl(fd, ioctl_code, frame)
            except OSError as e:
                logger.error(f"[ERROR] IOCTL failed: {e}")
                os.close(fd)
                return False
        else:
            bytes_written = os.write(fd, frame)
            logger.debug(f"[SEND] Wrote {bytes_written} bytes")
        os.close(fd)
        return True
    except Exception as e:
        logger.error(f"[ERROR] Send failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="GHS ota-isys Frame Fuzzer (Authorized Research Only)")
    parser.add_argument("--device", default="/dev/ghs/ota-isys", help="Path to device node [C]")
    parser.add_argument("--log", default="fuzzer_log.log", help="Log file for hex dumps")
    parser.add_argument("--send", action="store_true", default=False,
                         help="EXPLICIT OPT-IN, required to actually write frames to the device. "
                              "Absent this flag, frames are generated and logged only (safe default).")
    parser.add_argument("--payload-size", type=int, default=64, help="Size of random payload")
    parser.add_argument("--length-offset", type=int, default=DEFAULT_LENGTH_OFFSET,
                         help="[U] Offset of length field in frame (default 0)")
    parser.add_argument("--length-size", type=int, default=DEFAULT_LENGTH_SIZE,
                         help="[U] Size of length field in bytes (default 4)")
    parser.add_argument("--use-ioctl", action="store_true",
                         help="[U] Use ioctl instead of write (requires --ioctl-code)")
    parser.add_argument("--ioctl-code", type=int, default=None,
                         help="[U] Ioctl number if using --use-ioctl -- unverified, operator-supplied")

    args = parser.parse_args()

    global logger
    logger = setup_logger(args.log)

    logger.info("=" * 60)
    logger.info("GHS ota-isys Frame Fuzzer")
    logger.info(f"Target: {args.device}")
    logger.info(f"Mode: {'SEND (live device writes)' if args.send else 'SAFE (log-only, no device writes)'}")
    logger.info("=" * 60)

    if not check_device_permissions(args.device):
        logger.warning("Device access failed.")
        if args.send:
            sys.exit(1)

    payload = os.urandom(args.payload_size)
    frames = generate_malformed_frames(payload, args.length_offset, args.length_size, DEFAULT_LENGTH_ENDIAN)
    logger.info(f"Generated {len(frames)} test cases.")

    if not args.send:
        logger.info("SAFE MODE: No data sent to device. Review log for frame structures.")
        for i, (frame, desc) in enumerate(frames):
            logger.debug(f"[CASE {i}] {desc}")
            logger.debug(f"HEX: {frame.hex()}")
        return

    logger.warning("SEND MODE ACTIVE: Writing to live device.")
    for i, (frame, desc) in enumerate(frames):
        timestamp = datetime.now().isoformat()
        logger.info(f"[{timestamp}] Sending Case {i}: {desc}")
        logger.debug(f"HEX: {frame.hex()}")
        success = send_frame(args.device, frame, args.use_ioctl, args.ioctl_code)
        if not success:
            logger.error(f"[CASE {i}] Send failed.")
        time.sleep(0.5)

    logger.info("Fuzzing session complete.")


if __name__ == "__main__":
    main()
