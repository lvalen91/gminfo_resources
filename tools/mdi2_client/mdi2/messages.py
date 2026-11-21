"""900x application messages. Under the Blowfish frame, services speak JSON
(common_service::generic_client<PORT, json_format::base_request/response>), plus a
few binary control commands. Field set below is from decrypted live captures."""
import json

def session_open(name: str, dialer_ip: str, listener_ip: str,
                 date: str, interface: int = 2, master: bool = True,
                 keep_alive: bool = False, msg_id: int = 1) -> bytes:
    """The connect/handshake message (target 'session', id 1)."""
    obj = {"data": {"date": date, "dialer": dialer_ip, "interface": interface,
                    "keep_alive": keep_alive, "listener": listener_ip,
                    "master": master, "name": name},
           "has_data": True, "id": msg_id, "target": "session"}
    return json.dumps(obj, separators=(",", ":")).encode()

def poll(msg_id: int, target: str = "session") -> bytes:
    return json.dumps({"has_data": False, "id": msg_id, "target": target},
                      separators=(",", ":")).encode()


def session_close(session_id: int) -> bytes:
    """Release the device session (id 2, data=session id). Sent before disconnect."""
    return json.dumps({"data": session_id, "has_data": True, "id": 2, "target": "session"},
                      separators=(",", ":")).encode()

def parse(payload: bytes):
    """Decode an application payload: JSON dict, or raw bytes for binary commands."""
    p = payload.rstrip(b"\x00")
    if p[:1] == b"{":
        try:
            return json.loads(p)
        except ValueError:
            pass
    return p  # binary command / log container

# observed binary "get logs" trigger on port 9052 (→ streams the log container back)
GET_LOGS_CMD = bytes.fromhex("a708000001000000000000000000000c")

import struct as _struct
def pack_body(plaintext: bytes) -> bytes:
    """App framing inside the Blowfish body: content + zero-pad + u32be(len), mult of 8."""
    n = len(plaintext); pad = (8 - (n + 4) % 8) % 8
    return plaintext + b"\x00" * pad + _struct.pack(">I", n)

def unpack_body(decrypted: bytes) -> bytes:
    """Strip the trailing u32be length + padding, return the content."""
    if len(decrypted) < 4: return decrypted
    n = _struct.unpack(">I", decrypted[-4:])[0]
    return decrypted[:n] if n <= len(decrypted) else decrypted
