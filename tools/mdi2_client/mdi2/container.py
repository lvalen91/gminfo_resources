"""Decrypted 9052 log body = a sequence of SID-tagged records (construct).

Observed records (SID = little-endian u32):
  0x8a9  metadata : sid, _r, id, kind, namelen, name
  0x8a8  data     : sid, _r, id, namelen, name, datalen, data   (data = the log text)
`kind`/`_r` semantics and the full SID set need more samples; this covers the log pull.
"""
from construct import (Struct, Int32ul, Bytes, this, Switch, GreedyRange, Peek, Pass)

MetaRecord = Struct("sid"/Int32ul, "_r"/Int32ul, "id"/Int32ul, "kind"/Int32ul,
                    "namelen"/Int32ul, "name"/Bytes(this.namelen))
DataRecord = Struct("sid"/Int32ul, "_r"/Int32ul, "id"/Int32ul,
                    "namelen"/Int32ul, "name"/Bytes(this.namelen),
                    "datalen"/Int32ul, "data"/Bytes(this.datalen))

Record = Struct(
    "sid" / Peek(Int32ul),
    "rec" / Switch(this.sid, {0x8a9: MetaRecord, 0x8a8: DataRecord}, default=Pass),
)

def parse_log_container(plaintext: bytes):
    """Return list of (name:str, data:bytes) for DataRecords (e.g. 'messages' = Varlog)."""
    out, off = [], 0
    while off + 8 <= len(plaintext):
        sid = int.from_bytes(plaintext[off:off+4], "little")
        try:
            if sid == 0x8a8:
                r = DataRecord.parse(plaintext[off:])
                out.append((r.name.decode("latin1"), r.data))
                off += 4*5 + r.namelen + r.datalen
            elif sid == 0x8a9:
                r = MetaRecord.parse(plaintext[off:])
                off += 4*5 + r.namelen
            else:
                break
        except Exception:
            break
    return out
