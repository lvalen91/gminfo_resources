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

    def handshake(self, timeout=2.0):
        code = CONTROL_CODE.get(self.port, 0x30)
        self.sock.sendall(_CTRL_MAGIC + bytes([code]) + b"\x00\x00")
        self.sock.settimeout(timeout)
        try:
            self._ctrl_reply = self.sock.recv(8)
        except socket.timeout:
            self._ctrl_reply = b""
        time.sleep(0.25)   # device needs a brief settle before the first app message
        return self._ctrl_reply

    def send(self, plaintext: bytes):
        self.counter = (self.counter + 1) & 0xffffffff
        body = crypto.encrypt(self.key, messages.pack_body(plaintext))
        self.sock.sendall(framing.build_message(self.counter, body))

    def recv_frames(self, timeout=4.0, idle=1.0):
        """Accumulate bytes until idle-after-data, then parse+decrypt all app frames."""
        buf=b""; self.sock.settimeout(timeout); t0=time.time(); got=False
        while time.time()-t0 < timeout+10:
            try:
                c=self.sock.recv(65536)
                if not c: break
                buf+=c; got=True
                self.sock.settimeout(idle)
            except socket.timeout:
                break
        out=[]
        for counter, enc in framing.iter_frames(buf):
            out.append((counter, messages.unpack_body(crypto.decrypt(self.key, enc))))
        return out

class Session:
    def __init__(self, key, host=DEVICE_IP_DEFAULT):
        self.key, self.host = key, host
        self.channels = {}

    def connect(self, ports=SERVICE_PORTS, timeout=3.0):
        for p in ports:
            s = socket.create_connection((self.host, p), timeout=timeout)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            ch = Channel(s, self.key, p); ch.handshake()
            self.channels[p] = ch
        return self

    def close(self):
        for ch in self.channels.values():
            try: ch.sock.close()
            except OSError: pass
        self.channels.clear()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
