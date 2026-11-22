"""Parse and reseal a GM "CSM" calibration container (the A11/gminfo37 SPS delivery format).

Container layout (after the outer gzip is stripped):
    bytes [0:0x368]    872-byte signed header. container[6:10] == b"CSM\\x00".
                        Digest field at [0x1e:0x1e+32] = SHA-256(container[858:]).
                        RSA header signature and CA signer record live inside this
                        header too (bytes [600:856] and [62:344] respectively) --
                        NOT recomputed here. See the caveat below.
    bytes [0x368:]      inner gzip stream -> the CalOvride XML (calovride.py).

THIS MODULE DELIBERATELY DOES NOT SIGN ANYTHING. reseal() recomputes only the one
mutable integrity field (the payload digest at 0x1e) and leaves the rest of the header
-- including the RSA signature -- byte-identical to whatever source container it was
given. That signature will therefore be stale relative to the new payload, exactly as
documented for every hand-edited candidate in DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md.
Getting a resealed-but-unsigned container accepted by real hardware requires the
separate CAN613/614 VIP-RAM bypass described there -- this module stops at producing a
correctly-structured, correctly-digested container, nothing more.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import zlib
from dataclasses import dataclass

HEADER_LEN = 0x368
DIGEST_OFF = 0x1E
DIGEST_SPAN = 858

# Real calibration payloads top out around 600KB (the largest, slot04's 404-entry LTZ
# document, is ~594KB). 16MiB is generous headroom for anything legitimate while still
# bounding memory against a small, highly-compressed file claiming to decompress to
# hundreds of MB.
MAX_DECOMPRESSED_SIZE = 16 * 1024 * 1024


def _bounded_decompress(data: bytes, cap: int = MAX_DECOMPRESSED_SIZE) -> bytes:
    """gzip.decompress() with a cap on the decompressed size, so a small, highly-compressed
    input can't be used to force an unbounded memory allocation. Reads incrementally rather
    than decompressing everything first and checking the length after."""
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
        out = gz.read(cap + 1)
    if len(out) > cap:
        raise ContainerError(f"decompressed payload exceeds the {cap} byte safety cap -- refusing to process")
    return out

# Every exception gzip.decompress can actually raise on malformed input: BadGzipFile for a
# bad magic/CRC/size trailer, EOFError for truncation, zlib.error for corrupted deflate
# data. All three must be caught at every decompress call, or "never raises" (parse_any)
# and "clean CLI/API errors" both silently break on exactly the kind of damaged-container
# input this tool exists to handle.
_GZIP_ERRORS = (gzip.BadGzipFile, EOFError, zlib.error, OSError)


class ContainerError(ValueError):
    pass


@dataclass
class Container:
    header: bytes          # 872 bytes, container[0:0x368], including the (possibly stale) signature
    inner_xml: bytes        # the decompressed CalOvride XML payload
    digest_ok: bool = True  # False if the container's own stored payload digest doesn't match
                            # its actual bytes -- i.e. it was tampered with or corrupted after
                            # being signed. Ingesting such a container still succeeds (so you can
                            # inspect what's in it), but callers should surface this prominently.

    @property
    def slot(self) -> int:
        """UDS calibration slot / SW-ID, read from header byte 0x03 (cross-validated
        against SPS logs and the pinned reference manifest -- see CALIBRATION_SLOT_MAP.md).
        Inferred field meaning; not documented by any GM tool."""
        return self.header[0x03]

    @property
    def alpha_code(self) -> str:
        """Two-byte ASCII design-level code at header offset 0x362 (e.g. 'AA', 'AB')."""
        return self.header[0x362:0x364].decode("ascii", errors="replace")

    @property
    def part_number(self) -> int:
        """Big-endian u32 at header offset 0x364 -- equals the container's own part number."""
        return int.from_bytes(self.header[0x364:0x368], "big")


def parse(raw_outer_gzip: bytes) -> Container:
    """raw_outer_gzip is the file exactly as stored under spsCacheInternal/ (outer gzip
    wrapping the container)."""
    try:
        container = _bounded_decompress(raw_outer_gzip)
    except _GZIP_ERRORS as e:
        raise ContainerError(f"not a valid gzip file (expected outer gzip wrapping a CSM container): {e}") from e
    return parse_unwrapped(container)


def parse_unwrapped(container: bytes) -> Container:
    """container is already outer-gunzipped (e.g. a decompressed/*.dec sibling file)."""
    if len(container) < HEADER_LEN + 3 or container[6:10] != b"CSM\x00":
        raise ContainerError("not a CSM container (missing CSM\\x00 magic at offset 6)")
    if container[HEADER_LEN:HEADER_LEN + 3] != b"\x1f\x8b\x08":
        raise ContainerError("no inner gzip stream found at offset 0x368")
    header = container[:HEADER_LEN]
    try:
        inner_xml = _bounded_decompress(container[HEADER_LEN:])
    except _GZIP_ERRORS as e:
        raise ContainerError(f"CSM header is valid but the inner gzip payload is corrupt: {e}") from e
    return Container(header=header, inner_xml=inner_xml, digest_ok=verify_digest(container))


def verify_digest(container_bytes: bytes) -> bool:
    """container_bytes is the full unwrapped container (header + inner gzip). Returns
    False (never raises) on input too short to contain a digest."""
    if len(container_bytes) < DIGEST_SPAN:
        return False
    stored = container_bytes[DIGEST_OFF:DIGEST_OFF + 32]
    actual = hashlib.sha256(container_bytes[DIGEST_SPAN:]).digest()
    return stored == actual


def reseal(header: bytes, new_inner_xml: bytes) -> bytes:
    """Rebuild an unwrapped container from a (possibly unmodified) header and a new
    CalOvride XML payload. Recomputes ONLY the payload digest at 0x1e; every other
    header byte -- including the now-stale RSA signature -- is carried forward
    unchanged. Returns the unwrapped container (header + fresh inner gzip); gzip it
    again yourself (gzip.compress(..., mtime=0)) to get the on-disk file form."""
    if len(header) != HEADER_LEN:
        raise ContainerError(f"header must be exactly {HEADER_LEN} bytes, got {len(header)}")
    inner = gzip.compress(new_inner_xml, mtime=0)
    out = bytearray(header + inner)
    out[DIGEST_OFF:DIGEST_OFF + 32] = hashlib.sha256(bytes(out[DIGEST_SPAN:])).digest()
    return bytes(out)


def pack_outer(unwrapped_container: bytes) -> bytes:
    """Wrap an unwrapped container back into the on-disk outer-gzip file form."""
    return gzip.compress(unwrapped_container, mtime=0)


def parse_any(data: bytes) -> Container | None:
    """Try every known on-disk form in turn: outer-gzip SPS file, an already-unwrapped
    container (e.g. a decompressed/*.dec sibling), or neither. Returns None (never
    raises) if data doesn't look like a CSM container in any known wrapping -- callers
    that also want to fall back to bare CalOvride XML should try calovride.parse() on
    the original bytes themselves when this returns None."""
    try:
        return parse(data)
    except ContainerError:
        pass
    try:
        return parse_unwrapped(data)
    except ContainerError:
        pass
    return None
