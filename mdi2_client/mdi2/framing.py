"""900x/9052 wire framing via `construct` (declarative, reversible).

Message : [u32be 0][u32be payload_len][u32be counter (cleartext)][Blowfish-ECB body]
Control : 00 53 50 00 00 XX 00 00   (8-byte plaintext, per-connection)
"""
from construct import (Struct, Const, Int32ub, Bytes, this, GreedyRange, Select,
                       Peek, StopIf)

ControlFrame = Struct("magic" / Const(b"\x00\x53\x50\x00"), "code" / Bytes(4))

Message = Struct(
    "zero"    / Const(0, Int32ub),
    "length"  / Int32ub,
    "counter" / Int32ub,                 # cleartext, echoed by the device
    "body"    / Bytes(this.length - 4),  # Blowfish-ECB ciphertext
)

# a reassembled stream = interleaved control frames and messages
Frame  = Select(ControlFrame, Message)
Stream = GreedyRange(Frame)

def build_message(counter: int, enc_body: bytes) -> bytes:
    return Message.build(dict(length=len(enc_body) + 4, counter=counter, body=enc_body))

def iter_frames(buf: bytes):
    """Yield (counter, enc_body) for Message frames; skips control frames."""
    for f in Stream.parse(buf):
        if getattr(f, "counter", None) is not None:
            yield f.counter, f.body
