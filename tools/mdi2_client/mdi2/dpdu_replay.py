"""Literal D-PDU-over-TCP session replayer for the Bosch GM MDI2 (port 10123).

DISCIPLINE: this does NOT reconstruct payloads from a spec. It replays the EXACT
client->device frames captured from a real GM DPS session in the pcap, in tcp.seq
order, and matches each device->client response. The ONLY bytes it rewrites are the
dynamic session values that the live MDI assigns differently than the capture did:

  * channel id  -- assigned by the MDI in the 0x885 reply (payload offset 12, u32).
                   Capture used 0x13; live may differ.
  * CLL handles -- these are CLIENT-assigned and DETERMINISTIC: handle = (channel<<24)|index.
                   So every handle's high byte == the channel id. Remapping the channel
                   byte in each command frame's leading handle word remaps every handle.
  * event hello -- the event socket's 0x884 hello carries the channel id as a u32 at
                   payload offset 4; rebuilt with the live channel.

Everything else (ioctls, comparams, resp-id tables, start-com-primitives, UDS) is
byte-for-byte the captured bytes. Generous recv timeouts cover the ~3.28s SET_BRIDGE
block during which the MDI builds br-usb and eth0 links. en17 is re-asserted after the
bridge poke because gmEtherGW resets usb0.
"""
from __future__ import annotations
import socket, struct, subprocess, threading, time, sys, os

PCAP = "/Volumes/stuff/misc/research/GM_research/gm_dps/misc/Aug24_session/DPS+SPS.pcapng"
TSHARK = "/opt/homebrew/bin/tshark"
DEVICE_IP = "192.168.171.2"
PORT = 10123

MID_HELLO   = 0x884   # /0x885
MID_IOCTL   = 0x467
MID_EVENT   = 0x863
MID_LEN_IND = 1505
IOCTL_SET_BRIDGE = 0x25
CLL_MIDS = {0x44f, 0x451, 0x457, 0x459, 0x45d, 0x45f, 0x461, 0x463}


def _reframe(blob: bytes) -> list[tuple[int, bytes]]:
    """Walk a one-direction byte blob into [u32 len LE][u32 mid LE][payload] frames."""
    frames, i, n = [], 0, len(blob)
    while i + 8 <= n:
        total, mid = struct.unpack_from("<II", blob, i)
        if total < 8 or i + total > n:
            raise ValueError(f"bad frame at {i}: total={total} mid=0x{mid:x} remain={n-i}")
        frames.append((mid, blob[i + 8:i + total]))
        i += total
    if i != n:
        raise ValueError(f"trailing {n-i} bytes after last frame")
    return frames


def load_stream(stream: int, pcap: str = PCAP):
    """Return (client_frames, server_frames) for a tcp.stream via `follow,tcp,raw`.
    Concatenates all client lines / all server lines (server lines are tab-prefixed),
    preserving per-direction tcp order, then re-frames each blob."""
    out = subprocess.run([TSHARK, "-r", pcap, "-q", "-z", f"follow,tcp,raw,{stream}"],
                         capture_output=True, text=True).stdout.splitlines()
    # header block ends at the "Node 1:" line
    start = next(i for i, l in enumerate(out) if l.startswith("Node 1:")) + 1
    cli, srv = bytearray(), bytearray()
    for l in out[start:]:
        if l.startswith("===") or not l.strip():
            continue
        if l.startswith("\t"):
            srv += bytes.fromhex(l.strip())
        else:
            cli += bytes.fromhex(l.strip())
    return _reframe(bytes(cli)), _reframe(bytes(srv))


def client_frame_times(stream: int, cli_frames, pcap: str = PCAP):
    """Wall-clock send time (frame.time_relative) for each client D-PDU frame.

    Rebuilds the client byte blob from per-packet payloads (dedup retransmits by seq)
    while tracking byteoffset->time, then assigns each reframed frame the time of the
    TCP segment carrying its first byte. Faithfully reproduces DPS's inter-frame pacing
    (esp. the ~18.85s the bridge stays up for the vehicle's DHCP)."""
    rows = subprocess.run(
        [TSHARK, "-r", pcap, "-Y", f"tcp.stream=={stream} && ip.src==192.168.171.30 && tcp.len>0",
         "-T", "fields", "-e", "tcp.seq", "-e", "frame.time_relative", "-e", "tcp.len"],
        capture_output=True, text=True).stdout.splitlines()
    segs = {}
    for r in rows:
        seq, t, ln = r.split("\t")
        segs.setdefault(int(seq), (float(t), int(ln)))  # first sighting wins (ignore retrans)
    off_time = []  # (cumulative_offset, time) at each segment boundary
    off = 0
    for seq in sorted(segs):
        t, ln = segs[seq]
        off_time.append((off, t))
        off += ln
    def time_at(byteoff):
        best = off_time[0][1]
        for o, t in off_time:
            if o <= byteoff:
                best = t
            else:
                break
        return best
    times, cur = [], 0
    for mid, pay in cli_frames:
        times.append(time_at(cur))
        cur += 8 + len(pay)
    return times


def capture_channel(server_frames) -> int:
    for mid, pay in server_frames:
        if mid == MID_HELLO + 1 and len(pay) >= 16:
            return struct.unpack_from("<I", pay, 12)[0]
    raise RuntimeError("no 0x885 in capture server frames")


def reassert_en17():
    subprocess.run(["sudo", "ifconfig", "en17", "inet", "192.168.171.30",
                    "netmask", "255.255.255.0"], capture_output=True)


class Replayer:
    def __init__(self, stream: int, host: str = DEVICE_IP):
        self.host = host
        self.cli_frames, self.srv_frames = load_stream(stream)
        self.cap_times = client_frame_times(stream, self.cli_frames)
        self.t_base = self.cap_times[0]
        self.cap_ch = capture_channel(self.srv_frames)
        self.live_ch = None
        self.cmd = None
        self.evt = None
        self.events = []
        self._evt_stop = threading.Event()
        self.log = []

    # -- channel/handle remap ------------------------------------------------
    def _remap_cmd(self, mid: int, pay: bytes) -> bytes:
        if self.live_ch is None or self.live_ch == self.cap_ch or mid not in CLL_MIDS:
            return pay
        if len(pay) < 4:
            return pay
        b = bytearray(pay)
        # leading handle word: LE bytes [idx,00,00,cap_ch]; remap high byte only
        if b[3] == self.cap_ch and b[1] == 0 and b[2] == 0:
            b[3] = self.live_ch
        return bytes(b)

    def _event_hello(self) -> bytes:
        # capture's event hello, with channel u32 at payload offset 4 set to live_ch
        pay = struct.pack("<III", 1, self.live_ch, 0x1388)
        return struct.pack("<II", 8 + len(pay), MID_HELLO) + pay

    # -- io ------------------------------------------------------------------
    @staticmethod
    def _send(sock, mid, pay):
        sock.sendall(struct.pack("<II", 8 + len(pay), mid) + pay)

    @staticmethod
    def _recv_frame(sock, timeout):
        sock.settimeout(timeout)
        hdr = Replayer._recv_exact(sock, 8)
        total, mid = struct.unpack("<II", hdr)
        pay = Replayer._recv_exact(sock, total - 8) if total > 8 else b""
        return mid, pay

    @staticmethod
    def _recv_exact(sock, n):
        buf = bytearray()
        while len(buf) < n:
            c = sock.recv(n - len(buf))
            if not c:
                raise ConnectionError("closed mid-frame")
            buf += c
        return bytes(buf)

    def _event_loop(self):
        while not self._evt_stop.is_set():
            try:
                mid, pay = self._recv_frame(self.evt, 1.0)
            except socket.timeout:
                continue
            except Exception:
                break
            self.events.append((time.time(), mid, pay))

    # -- run -----------------------------------------------------------------
    def _arp_watch(self, t0):
        """Poll the ARP cache for 192.168.171.70 for the whole session; record first hit."""
        while not self._evt_stop.is_set():
            out = subprocess.run(["arp", "-an"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                if "171.70" in line and "incomplete" not in line and "(incomplete)" not in line:
                    if self.arp70 is None:
                        self.arp70 = (time.time() - t0, line.strip())
                        print(f"[ARP-WATCH] .70 present at +{self.arp70[0]:.2f}s: {line.strip()}",
                              flush=True)
            time.sleep(0.4)

    def run(self, hold_after: float = 6.0, stop_before: int | None = None,
            on_bridge_up=None):
        t0 = time.time()
        self.arp70 = None
        n_frames = len(self.cli_frames) if stop_before is None else stop_before
        # flush any stale .70 arp entry so a hit means THIS session brought it up
        subprocess.run(["sudo", "arp", "-d", "192.168.171.70"], capture_output=True)
        threading.Thread(target=self._arp_watch, args=(t0,), daemon=True).start()

        def note(s):
            self.log.append(f"[{time.time()-t0:7.2f}] {s}")
            print(self.log[-1], flush=True)

        self.cmd = socket.create_connection((self.host, PORT), timeout=5)
        self.cmd.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        note(f"cmd socket up; {len(self.cli_frames)} client frames, cap_ch=0x{self.cap_ch:02x}")

        evt_started = False
        for idx, (mid, pay) in enumerate(self.cli_frames[:n_frames]):
            # honor DPS's send schedule: don't send frame i before its captured
            # relative offset. Keeps the bridge up as long as DPS did (~18.85s).
            target = self.cap_times[idx] - self.t_base
            slack = target - (time.time() - t0)
            if slack > 0.02:
                time.sleep(slack)
            spay = self._remap_cmd(mid, pay)
            self._send(self.cmd, mid, spay)
            is_bridge = (mid == MID_IOCTL and len(spay) >= 8 and
                         struct.unpack_from("<I", spay, 4)[0] == IOCTL_SET_BRIDGE)
            if is_bridge:
                note(f"  #{idx} SENT SET_BRIDGE ioctl; scheduling en17 re-assert; waiting (<=25s)")
                threading.Timer(1.0, reassert_en17).start()
            # read the paired response (mid+1). generous timeout for bridge block.
            to = 25.0 if is_bridge else 8.0
            try:
                rmid, rpay = self._recv_frame(self.cmd, to)
            except Exception as e:
                note(f"  #{idx} mid=0x{mid:x} NO RESPONSE ({e}); DIVERGENCE POINT")
                self._dump_divergence(idx, mid, spay)
                raise
            if rmid != mid + 1:
                note(f"  #{idx} mid=0x{mid:x} got 0x{rmid:x} (want 0x{mid+1:x}) pay={rpay.hex()}")
            if is_bridge:
                note(f"  #{idx} SET_BRIDGE reply after block: {rpay.hex()}")
                reassert_en17()
                if on_bridge_up is not None:
                    threading.Thread(target=on_bridge_up, daemon=True).start()
            # after learning the live channel from the command hello, bind the event socket
            if mid == MID_HELLO and not evt_started:
                self.live_ch = struct.unpack_from("<I", rpay, 12)[0] if len(rpay) >= 16 else self.cap_ch
                note(f"  live channel = 0x{self.live_ch:02x} (cap 0x{self.cap_ch:02x})"
                     + ("  [REMAP ACTIVE]" if self.live_ch != self.cap_ch else "  [identical]"))
                self.evt = socket.create_connection((self.host, PORT), timeout=5)
                self.evt.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.evt.sendall(self._event_hello())
                try:
                    self._recv_frame(self.evt, 5.0)  # 0x885 on event socket
                except Exception:
                    pass
                threading.Thread(target=self._event_loop, daemon=True).start()
                evt_started = True
                note("  event socket bound + reader started")

        note(f"all {len(self.cli_frames)} command frames replayed; holding {hold_after}s for events")
        time.sleep(hold_after)
        note(f"captured {len(self.events)} event frames "
             f"({sum(1 for _,m,_ in self.events if m==MID_EVENT)} x0x863)")
        self._evt_stop.set()
        for s in (self.cmd, self.evt):
            try: s and s.close()
            except OSError: pass

    def _dump_divergence(self, idx, mid, spay):
        lo = max(0, idx - 3)
        for j in range(lo, min(idx + 1, len(self.cli_frames))):
            m, p = self.cli_frames[j]
            mark = " <== FAILED HERE" if j == idx else ""
            print(f"    cli#{j} mid=0x{m:x} len={len(p)} {p[:32].hex()}{mark}", flush=True)


if __name__ == "__main__":
    stream = int(sys.argv[1]) if len(sys.argv) > 1 else 414
    r = Replayer(stream)
    print(f"stream {stream}: {len(r.cli_frames)} cmd frames, {len(r.srv_frames)} srv frames, "
          f"cap_ch=0x{r.cap_ch:02x}")
    r.run()
