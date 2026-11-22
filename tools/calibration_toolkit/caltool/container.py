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
from dataclasses import dataclass

HEADER_LEN = 0x368
DIGEST_OFF = 0x1E
DIGEST_SPAN = 858


class ContainerError(ValueError):
    pass


@dataclass
class Container:
    header: bytes          # 872 bytes, container[0:0x368], including the (possibly stale) signature
    inner_xml: bytes        # the decompressed CalOvride XML payload

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
        container = gzip.decompress(raw_outer_gzip)
    except gzip.BadGzipFile as e:
        raise ContainerError(f"not a gzip file (expected outer gzip wrapping a CSM container): {e}") from e
    return parse_unwrapped(container)


def parse_unwrapped(container: bytes) -> Container:
    """container is already outer-gunzipped (e.g. a decompressed/*.dec sibling file)."""
    if len(container) < HEADER_LEN + 3 or container[6:10] != b"CSM\x00":
        raise ContainerError("not a CSM container (missing CSM\\x00 magic at offset 6)")
    if container[HEADER_LEN:HEADER_LEN + 3] != b"\x1f\x8b\x08":
        raise ContainerError("no inner gzip stream found at offset 0x368")
    header = container[:HEADER_LEN]
    inner_xml = gzip.decompress(container[HEADER_LEN:])
    return Container(header=header, inner_xml=inner_xml)


def verify_digest(container_bytes: bytes) -> bool:
    """container_bytes is the full unwrapped container (header + inner gzip)."""
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
