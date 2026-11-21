"""900x service session: opens the 14-socket bank, does the per-channel control-frame
handshake, sends length-suffixed + Blowfish-framed app messages, reads whole frames."""
import socket, struct, time, random
from . import crypto, framing, messages
from .const import SERVICE_PORTS, DEVICE_IP_DEFAULT

CONTROL_CODE = {9011: 0x21}      # default 0x30
_CTRL_MAGIC = b"\x00\x53\x50\x00"

class Channel:
    def __init__(self, sock, key, port):
        self.sock, self.key, self.port = sock, key, port
        self.counter = random.getrandbits(31) | 0x80000000  # device requires high bit set
        self._recv_buffer = bytearray()

    def handshake(self, timeout=2.0):
        code = CONTROL_CODE.get(self.port, 0x30)
        self.sock.settimeout(timeout)
        self.sock.sendall(_CTRL_MAGIC + b"\x00" + bytes([code]) + b"\x00\x00")
        deadline = time.monotonic() + timeout
        reply = bytearray()
        try:
            while len(reply) < 8:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise socket.timeout()
                self.sock.settimeout(remaining)
                chunk = self.sock.recv(8 - len(reply))
                if not chunk:
                    raise ConnectionError("service stream closed during handshake")
                reply.extend(chunk)
        except socket.timeout:
            # Some service ports do not reply. Retain any partial control
            # frame so its tail cannot desynchronize subsequent app reads.
            self._recv_buffer.extend(reply)
            self._ctrl_reply = b""
        else:
            self._ctrl_reply = bytes(reply)
        time.sleep(0.25)   # device needs a brief settle before the first app message
        return self._ctrl_reply

    def send(self, plaintext: bytes):
        self.counter = (self.counter + 1) & 0xffffffff
        body = crypto.encrypt(self.key, messages.pack_body(plaintext))
        self.sock.sendall(framing.build_message(self.counter, body))

    def recv_frames(self, timeout=4.0, idle=1.0):
        """Read complete frames, retaining a partial frame across idle timeouts."""
        deadline = time.monotonic() + timeout
        out = []
        wait = timeout
        while True:
            buf = self._recv_buffer
            while len(buf) >= 8:
                if buf[:4] == _CTRL_MAGIC:
                    del buf[:8]
                    continue
                zero, length = struct.unpack_from(">II", buf)
                # Length includes the counter and block-aligned ciphertext.
                # Bound a declared frame before retaining its body (16 MiB).
                if zero != 0 or not 12 <= length <= 16 * 1024 * 1024 or (length - 4) % 8:
                    raise ValueError("invalid service frame header")
                size = 8 + length
                if len(buf) < size:
                    break
                counter = struct.unpack_from(">I", buf, 8)[0]
                enc = bytes(buf[12:size])
                body = messages.unpack_body(crypto.decrypt(self.key, enc))
                del buf[:size]
                out.append((counter, body))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self.sock.settimeout(min(wait, remaining))
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                if buf:
                    raise ConnectionError("service stream closed mid-frame")
                break
            buf.extend(chunk)
            wait = idle
        return out

class Session:
    def __init__(self, key, host=DEVICE_IP_DEFAULT):
        self.key, self.host = key, host
        self.channels = {}

    def connect(self, ports=SERVICE_PORTS, timeout=3.0):
        try:
            for p in ports:
                if p in self.channels:
                    continue
                s = socket.create_connection((self.host, p), timeout=timeout)
                try:
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    ch = Channel(s, self.key, p)
                    ch.handshake()
                except BaseException:
                    try:
                        s.close()
                    except OSError:
                        pass
                    raise
                self.channels[p] = ch
        except BaseException:
            self.close()
            raise
        return self

    def close(self):
        for ch in self.channels.values():
            try: ch.sock.close()
            except OSError: pass
        self.channels.clear()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
