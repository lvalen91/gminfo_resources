"""Strict parser for one observed MDI2 D-PDU 0x863 receive-event layout.

This capture-specific decoder is not a verified general D-PDU transport.
"""
from __future__ import annotations

import struct


def _strip_single_frame_padding(frame: bytes) -> bytes:
    """Strip the ISO-TP single-frame PCI + 0x55 padding of the padded/short CLL.

    Two confirmed CLL sub-encodings share this layout (see the Aug-2026 decode):
      * padded/short CLL wraps short UDS as an ISO-TP single frame
        ``[SF-len:1][UDS...][0x55 pad...]`` (``blockLen`` == 12);
      * exact-fit CLL carries raw UDS with no PCI and no padding.
    A real UDS response SID is always >= 0x40 (positive = request+0x40, negative
    = 0x7F), never 0x01..0x07, so the exact-fit path -- and a device-reassembled
    multi-frame response, whose first byte is likewise a response SID -- is left
    untouched. This mirrors ``scratch_decode/radio_cal_decode.clean_uds``.
    """
    if (frame and 1 <= frame[0] <= 7 and 1 + frame[0] <= len(frame)
            and all(b == 0x55 for b in frame[1 + frame[0]:])):
        return frame[1:1 + frame[0]]
    return frame


def parse_radio_rx(payload: bytes, *, handle: int, cop: int, can_id: int) -> bytes | None:
    """Extract a response for one CLL/RX COP, ignoring unrelated event types.

    Observed receive format: handle@0, event type@4, COP@20, CAN ID@70,
    LE block length@74, repeated CAN ID@78, UDS@82. The length includes
    the repeated CAN ID. Unknown events do not become UDS messages. The padded
    short-CLL ISO-TP single-frame wrapper (PCI + 0x55 pad) is stripped so short
    poll/keepalive responses parse to raw UDS; the exact-fit CLL is unchanged.
    """
    if len(payload) < 8:
        raise ValueError("truncated D-PDU event header")
    if struct.unpack_from("<I", payload, 4)[0] != 1 or len(payload) < 74:
        return None
    if struct.unpack_from("<I", payload, 0)[0] != handle:
        return None
    if struct.unpack_from("<H", payload, 20)[0] != cop:
        return None
    if int.from_bytes(payload[70:74], "big") != can_id:
        return None
    if len(payload) < 78:
        raise ValueError("truncated D-PDU receive-event block length")
    size = struct.unpack_from("<I", payload, 74)[0]
    if size < 5 or len(payload) != 78 + size:
        raise ValueError("invalid D-PDU receive-event block length")
    if int.from_bytes(payload[78:82], "big") != can_id:
        raise ValueError("inconsistent D-PDU receive CAN identifiers")
    return _strip_single_frame_padding(payload[82:])
