"""Native D-PDU-API-over-TCP client for the Bosch GM MDI2 (port 10123).

Implements the resource-0x2A ("MDI-managed ISO-TP/UDS") bring-up and DID reads
described in research/MDI2_DPDU_API_PROTOCOL_AUG2026.md §4, on macOS, with zero
GM Windows software.

Wire framing (LITTLE-ENDIAN — note this differs from the big-endian 900x/9052
log path in the rest of this package):

    [u32 total_len LE][u32 mid LE][payload]        total_len includes the 8-byte header

Request/response `mid`s pair N / N+1 (odd request -> even response).

TWO sockets per session are mandatory (§2):
  * command socket  — carries every request mid; gets a channel id in the 0x885 reply
  * event   socket  — carries ONLY async 0x863 diagnostic events (and 1505 length
                      indications); its hello must echo the command socket's channel id.
A one-socket client never sees a diagnostic response.

Everything marked `# GUESS:` is a field the source doc left ambiguous; the byte
LENGTHS and the documented offsets/values are honored, but the surrounding filler
and a few structural choices are best-effort and must be confirmed against a live
capture. See the module docstring's companion notes returned to the caller.
"""
from __future__ import annotations

import socket
import struct
import threading
import queue
import time
import logging

log = logging.getLogger("mdi2.dpdu")

DEVICE_IP_DEFAULT = "192.168.171.2"
DPDU_PORT = 10123

# --- mid opcode table (§3) --------------------------------------------------
MID_HELLO          = 0x884   # /0x885 session hello / assign channel
MID_BIND_EVENT     = 0x886   # /0x887 bind event channel (event socket)
MID_CREATE_CLL     = 0x44F   # /0x450 PDUCreateComLogicalLink
MID_DESTROY_CLL    = 0x451   # /0x452 PDUDestroyComLogicalLink
MID_GET_COMPARAM   = 0x457   # /0x458
MID_SET_COMPARAM   = 0x459   # /0x45A
MID_SET_RESPID     = 0x45D   # /0x45E PDUSetUniqueRespIdTable
MID_CONNECT        = 0x45F   # /0x460 PDUConnect
MID_DISCONNECT     = 0x461   # /0x462 PDUDisconnect
MID_START_COP      = 0x463   # /0x464 PDUStartComPrimitive
MID_IOCTL          = 0x467   # /0x468 PDUIoCtl
MID_EVENT          = 0x863   # async diagnostic event (event socket only)
MID_LEN_IND        = 1505    # multi-frame length indication (event socket only)

# --- ComPrimitive types (§1/§4) --------------------------------------------
COP_SENDRECV   = 0x8004
COP_STARTCOMM  = 0x8001
COP_UPDATEPARAM = 0x8003

# --- resources (§3/§4) ------------------------------------------------------
RESOURCE_RAW_CAN = 0x06
RESOURCE_ISOTP   = 0x2A       # MDI-managed ISO-TP/UDS — what this client uses

# --- IOCTL ids (§3) ---------------------------------------------------------
IOCTL_CLEAR_RX = 0x0B         # handle 0 + id 0x0B = clear RX buffer (before every CreateCLL)

# --- ComParam ids used in the 0x2A bring-up (§4) ----------------------------
CP_2A_PRE = [(0x15, 0), (0x16, 0), (0x19, 0x22), (0x1B, 0), (0xAB, 1), (0xC6, 1)]
CP_1C = (0x1C, 1)

# --- addressing (§5) --------------------------------------------------------
# ECU 0x80 (radio): physical request 0x14DA80F1, physical response 0x145AF180.
ECU80_REQ_CANID  = 0x14DA80F1
ECU80_RESP_CANID = 0x145AF180
# functional broadcast (TesterPresent, node-discovery)
FUNCTIONAL_REQ_CANID = 0x10DBFEF1

# UNINSTALL / clear table is 24 bytes; install (6 entries) is 174 bytes (§4/§5).
# GUESS: the 24-byte header layout below (handle + count + fixed filler) is not
# spelled out in the doc; only its total length (24B) and the 25-byte entry
# template are. Byte counts are exact; filler is a best-effort guess.
_TBL_HDR_LEN = 24


class DpduError(RuntimeError):
    pass


# ============================================================================
# framing
# ============================================================================
def pack_frame(mid: int, payload: bytes = b"") -> bytes:
    total = 8 + len(payload)
    return struct.pack("<II", total, mid) + payload


def read_frame(sock: socket.socket, timeout: float | None = None) -> tuple[int, bytes]:
    """Blocking read of exactly one [len][mid][payload] frame. Returns (mid, payload)."""
    if timeout is not None:
        sock.settimeout(timeout)
    hdr = _recv_exact(sock, 8)
    total, mid = struct.unpack("<II", hdr)
    if total < 8:
        raise DpduError(f"bad frame total_len={total}")
    payload = _recv_exact(sock, total - 8) if total > 8 else b""
    return mid, payload


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise DpduError("socket closed mid-frame")
        buf += chunk
    return bytes(buf)


def _u32le(v: int) -> bytes:
    return struct.pack("<I", v & 0xFFFFFFFF)


def _u16le(v: int) -> bytes:
    return struct.pack("<H", v & 0xFFFF)


def _u32be(v: int) -> bytes:
    return struct.pack(">I", v & 0xFFFFFFFF)


# ============================================================================
# payload builders
# ============================================================================
def _ioctl_payload(handle: int, ioctl_id: int, data: bytes = b"") -> bytes:
    # GUESS: layout is [u32 handle LE][u32 ioctlId LE][u32 dataLen LE][data].
    # The doc only gives (handle, ioctlId, data) semantics + that handle 0 / id
    # 0x0B clears the RX buffer; the exact envelope (esp. whether a dataLen word
    # is present) is not in the capture notes.
    return _u32le(handle) + _u32le(ioctl_id) + _u32le(len(data)) + data


def _create_cll_payload(resource: int) -> bytes:
    # Doc: "resource id at payload byte 9" (§3). Everything else is GUESS filler.
    buf = bytearray(13)          # GUESS: 13-byte create envelope
    buf[9] = resource & 0xFF     # confirmed: resource id lives at byte offset 9
    return bytes(buf)


def _comparam_record(param_id: int, value: int) -> bytes:
    # 25-byte param record, template from §5:
    #   05010000 00120000 <u32 paramId LE> 05010000 06000000 01 <u32 value LE>
    return (bytes.fromhex("0501000000120000")
            + _u32le(param_id)
            + bytes.fromhex("050100000600000001")
            + _u32le(value))


def _set_comparam_payload(handle: int, param_id: int, value: int) -> bytes:
    # 34-byte payload (§3): paramId @off17, value @off30. That is satisfied by
    #   [u32 handle LE][5 filler bytes][25-byte comparam record]
    # (handle=4, +5 -> record starts @9; record paramId @+8 = off17, value @+21 = off30).
    filler = b"\x00" * 5          # GUESS: 5-byte gap between handle and record
    payload = _u32le(handle) + filler + _comparam_record(param_id, value)
    assert len(payload) == 34, len(payload)
    return payload


def _resp_id_table_payload(handle: int, entries: list[tuple[int, int]]) -> bytes:
    # 24-byte header + N*25-byte entries. Clear table = header only (24B).
    # GUESS: header = [u32 handle LE][u32 count LE][16 filler bytes].
    hdr = bytearray(_TBL_HDR_LEN)
    hdr[0:4] = _u32le(handle)
    hdr[4:8] = _u32le(len(entries))          # GUESS: entry count at off 4
    body = b"".join(_comparam_record(p, v) for p, v in entries)
    payload = bytes(hdr) + body
    exp = 24 if not entries else 24 + 25 * len(entries)
    assert len(payload) == exp, (len(payload), exp)
    return payload


def resp_id_entries(req_canid: int, resp_canid: int,
                    req_fmt: int = 0x37, resp_fmt: int = 0x37) -> list[tuple[int, int]]:
    """The 6-entry addressing table (§5): request id/format/ext-addr + response
    id/format/ext-addr. ext-addr = 0 for this GMLAN-only vehicle."""
    return [
        (0x1F, req_canid),   # physical request CAN id
        (0x1E, req_fmt),     # request format
        (0x1D, 0),           # request ext-addr
        (0x22, resp_canid),  # physical response CAN id (NOT a fixed transform of req!)
        (0x21, resp_fmt),    # response format
        (0x20, 0),           # response ext-addr
    ]


def start_cop_payload(handle: int, cop_id: int, cop_type: int, data: bytes = b"",
                      time_ms: int = 0, num_send: int = 0, num_recv: int = 0,
                      flags: int = 0) -> bytes:
    """PDUStartComPrimitive payload, resource-0x2A layout (§4):

        u32 CLLhandle | u16 copId | u16 0x2510 | u16 copType | u16 0x0000 | u32 dataLen
        | dataLen bytes: [u32 CANid_BE][UDS payload]
        | u8 0x01 | u32 Time_ms | u32 NumSendCycles | u32 NumReceiveCycles
        | u32 0 | u32 0x00000004 | u32 flags | u32 0

    Inner multi-byte fields are little-endian (matching the frame header);
    only the CAN id inside `data` is big-endian (marked _BE in the doc). num_send /
    num_recv are signed: pass -1 for "forever".
    """
    return (
        _u32le(handle)
        + _u16le(cop_id)
        + _u16le(0x2510)          # fixed constant (§4)
        + _u16le(cop_type)
        + _u16le(0x0000)
        + _u32le(len(data))
        + data
        + b"\x01"                 # fixed u8 0x01 (§4)
        + _u32le(time_ms)
        + _u32le(num_send)
        + _u32le(num_recv)
        + _u32le(0)
        + _u32le(0x00000004)      # fixed constant (§4)
        + _u32le(flags)           # GUESS: flags = 0 (meaning not decoded)
        + _u32le(0)
    )


# ============================================================================
# link
# ============================================================================
class DpduLink:
    """One diagnostic session = command socket + event socket + one CLL handle.

    Typical use:
        link = DpduLink().open()
        link.bringup_ecu()                 # resource-0x2A CLL for ECU 0x80
        link.start_tester_present()        # hardware-cyclic 3E80 on functional id
        data = link.read_did(0xF190)       # -> VIN bytes
        link.close()
    """

    def __init__(self, host: str = DEVICE_IP_DEFAULT, port: int = DPDU_PORT):
        self.host, self.port = host, port
        self.cmd: socket.socket | None = None
        self.evt: socket.socket | None = None
        self.channel_id: int | None = None
        self.handle: int | None = None
        self._cop_id = 0
        self._rx_cop_id: int | None = None
        self._events: "queue.Queue[tuple[int, bytes]]" = queue.Queue()
        self._evt_thread: threading.Thread | None = None
        self._evt_stop = threading.Event()
        self._tp: DpduLink | None = None   # separate CLL for cyclic TesterPresent
        self._resp_canid = ECU80_RESP_CANID

    # -- lifecycle ----------------------------------------------------------
    def open(self, timeout: float = 5.0) -> "DpduLink":
        self.cmd = socket.create_connection((self.host, self.port), timeout=timeout)
        self.cmd.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.evt = socket.create_connection((self.host, self.port), timeout=timeout)
        self.evt.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # command hello -> channel id (§2: channel id in 0x885 reply payload byte 12)
        rmid, rpay = self._cmd_call(MID_HELLO, self._hello_payload(channel=0), timeout=timeout)
        if len(rpay) <= 12:
            raise DpduError(f"0x885 hello reply too short ({len(rpay)}B) to hold channel id")
        self.channel_id = rpay[12]           # confirmed: channel id at payload byte 12
        log.info("assigned channel id 0x%02x", self.channel_id)

        # event hello — must echo the command channel id to bind to the session (§2)
        self._send(self.evt, MID_HELLO, self._hello_payload(channel=self.channel_id))
        emid, _ = read_frame(self.evt, timeout=timeout)   # 0x885
        # GUESS: some captures also show an explicit 0x886/0x887 bind on the event
        # socket; send it too — harmless if the device treats the 0x884 echo as
        # sufficient, necessary if it does not.
        self._send(self.evt, MID_BIND_EVENT, self._hello_payload(channel=self.channel_id))
        try:
            read_frame(self.evt, timeout=timeout)          # 0x887 ack
        except (DpduError, socket.timeout):
            pass

        # background reader for async events on the event socket
        self._evt_thread = threading.Thread(target=self._event_loop, daemon=True)
        self._evt_thread.start()
        return self

    def _hello_payload(self, channel: int) -> bytes:
        # GUESS: the exact 0x884 hello bytes were not captured byte-for-byte. We
        # know only that a "channel field" is 0 on the command socket and the
        # assigned id on the event socket, and that the reply carries the channel
        # id at byte 12. Mirror that layout: a small struct with the channel byte
        # at offset 12. THIS IS THE FIELD MOST LIKELY TO NEED A CAPTURE FIX.
        buf = bytearray(16)
        buf[12] = channel & 0xFF
        return bytes(buf)

    def close(self):
        try:
            if self._tp is not None:
                self._tp.close()
                self._tp = None
        except Exception:
            pass
        self._evt_stop.set()
        for name in ("cmd", "evt"):
            s = getattr(self, name)
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
                setattr(self, name, None)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- low-level command socket i/o --------------------------------------
    def _send(self, sock: socket.socket, mid: int, payload: bytes = b""):
        sock.sendall(pack_frame(mid, payload))

    def _cmd_call(self, mid: int, payload: bytes = b"", timeout: float = 5.0) -> tuple[int, bytes]:
        """Send a request on the command socket, read its paired (mid+1) reply.

        The event socket is drained by a separate thread, so the command socket
        only ever carries request/response pairs — no interleaved async events.
        """
        assert self.cmd is not None
        self._send(self.cmd, mid, payload)
        rmid, rpay = read_frame(self.cmd, timeout=timeout)
        if rmid != mid + 1:
            raise DpduError(f"mid pairing off: sent 0x{mid:x}, got 0x{rmid:x} (expected 0x{mid+1:x})")
        return rmid, rpay

    def _next_cop_id(self) -> int:
        self._cop_id = (self._cop_id + 1) & 0xFFFF
        return self._cop_id

    # -- typed PDU calls ----------------------------------------------------
    def ioctl_clear_rx(self):
        self._cmd_call(MID_IOCTL, _ioctl_payload(0, IOCTL_CLEAR_RX))

    def create_cll(self, resource: int = RESOURCE_ISOTP) -> int:
        _, pay = self._cmd_call(MID_CREATE_CLL, _create_cll_payload(resource))
        self.handle = self._parse_handle(pay)
        log.info("CLL handle = 0x%08x (resource 0x%02x)", self.handle, resource)
        return self.handle

    @staticmethod
    def _parse_handle(pay: bytes) -> int:
        # GUESS: PDUConnect's reply is documented as "00000000 <u32 timestamp>",
        # i.e. these replies lead with a u32 status word. Assume CreateCLL replies
        # [u32 status=0][u32 handle LE] and take the handle at offset 4. If bring-up
        # fails, dump this payload and re-derive the offset.
        if len(pay) < 8:
            raise DpduError(f"CreateCLL reply too short ({len(pay)}B): {pay.hex()}")
        return struct.unpack_from("<I", pay, 4)[0]

    def set_comparam(self, param_id: int, value: int):
        assert self.handle is not None
        self._cmd_call(MID_SET_COMPARAM, _set_comparam_payload(self.handle, param_id, value))

    def clear_resp_id_table(self):
        assert self.handle is not None
        self._cmd_call(MID_SET_RESPID, _resp_id_table_payload(self.handle, []))

    def install_resp_id_table(self, req_canid: int, resp_canid: int):
        assert self.handle is not None
        entries = resp_id_entries(req_canid, resp_canid)
        self._cmd_call(MID_SET_RESPID, _resp_id_table_payload(self.handle, entries))

    def connect(self, timeout: float = 5.0):
        assert self.handle is not None
        _, pay = self._cmd_call(MID_CONNECT, _u32le(self.handle), timeout=timeout)
        if len(pay) >= 4 and struct.unpack_from("<I", pay, 0)[0] != 0:
            log.warning("PDUConnect status nonzero: %s", pay[:4].hex())

    def start_cop(self, cop_type: int, data: bytes = b"", time_ms: int = 0,
                  num_send: int = 0, num_recv: int = 0, cop_id: int | None = None,
                  timeout: float = 5.0) -> int:
        assert self.handle is not None
        cid = self._next_cop_id() if cop_id is None else cop_id
        payload = start_cop_payload(self.handle, cid, cop_type, data=data,
                                    time_ms=time_ms, num_send=num_send, num_recv=num_recv)
        self._cmd_call(MID_START_COP, payload, timeout=timeout)
        return cid

    # -- bring-up (§4 resource 0x2A) ---------------------------------------
    def bringup_ecu(self, req_canid: int = ECU80_REQ_CANID,
                    resp_canid: int = ECU80_RESP_CANID):
        """Full resource-0x2A bring-up for one physically-addressed ECU."""
        self._resp_canid = resp_canid
        self.ioctl_clear_rx()                                   # PDUIoCtl(0,0x0B)
        self.create_cll(RESOURCE_ISOTP)                         # -> handle
        self.clear_resp_id_table()                              # 24B clear
        for pid, val in CP_2A_PRE:                              # 0x15/0x16/0x19/0x1B/0xAB/0xC6
            self.set_comparam(pid, val)
        self.connect()                                          # PDUConnect
        # persistent RX cop: type 0x8004, dataLen 0, NumSendCycles 0, NumReceiveCycles -1
        self._rx_cop_id = self.start_cop(COP_SENDRECV, data=b"", num_send=0, num_recv=-1)
        self.start_cop(COP_STARTCOMM)                           # 0x8001
        self.start_cop(COP_UPDATEPARAM)                         # 0x8003
        self.set_comparam(*CP_1C)                               # 0x1C = 1
        self.install_resp_id_table(req_canid, resp_canid)      # 174B install
        self.start_cop(COP_UPDATEPARAM)                         # 0x8003
        log.info("ECU bring-up complete: req=0x%08X resp=0x%08X", req_canid, resp_canid)

    # -- diagnostic request/response ---------------------------------------
    def send_uds(self, uds: bytes, req_canid: int = ECU80_REQ_CANID):
        """Fire one UDS request as a one-shot send cop (§4 last StartComPrimitive)."""
        data = _u32be(req_canid) + uds
        # GUESS: NumReceiveCycles=0 on the send — the persistent RX cop set up in
        # bring-up is what actually delivers the 0x863 RX. NumSendCycles=1 per doc.
        self.start_cop(COP_SENDRECV, data=data, num_send=1, num_recv=0)

    def read_did(self, did: int, timeout: float = 4.0) -> bytes:
        """Send 22 <did>, wait for the matching 0x62 <did> positive response on the
        event socket. Raises DpduError on NRC (0x78 responsePending is waited out)."""
        req = bytes([0x22, (did >> 8) & 0xFF, did & 0xFF])
        self._drain_events()
        self.send_uds(req)
        deadline = time.time() + timeout
        while time.time() < deadline:
            uds = self._wait_uds(deadline - time.time())
            if uds is None:
                break
            if uds[0] == 0x7F and len(uds) >= 3:
                nrc = uds[2]
                if nrc == 0x78:           # responsePending — keep waiting (§6)
                    deadline = time.time() + timeout
                    continue
                raise DpduError(f"NRC 0x{nrc:02X} to 22 {did:04X} (service 0x{uds[1]:02X})")
            if uds[0] == 0x62 and uds[1:3] == req[1:3]:
                return uds[3:]
            # else: stray frame (functional TP echo, other ECU) — keep waiting
        raise TimeoutError(f"no response to 22 {did:04X}")

    # -- TesterPresent ------------------------------------------------------
    def start_tester_present(self, period_ms: int = 1000):
        """RECOMMENDED: offload cyclic 3E 80 to the MDI hardware (§4).

        A functional TesterPresent needs its own CLL (functional request id
        0x10DBFEF1, no expected response) regardless of whether we drive it from
        a Python thread or the device — so the second CLL is mandatory either way.
        Given that, the hardware-cyclic cop (NumSendCycles=-1, Time=period_ms) is
        both simpler and more robust than a software timer: it survives GIL stalls,
        keeps exact 1.000s spacing (confirmed in captures), and needs no thread.

        A software-thread alternative is provided as `start_tester_present_thread()`.
        """
        tp = DpduLink(self.host, self.port).open()
        tp.ioctl_clear_rx()
        tp.create_cll(RESOURCE_ISOTP)
        tp.clear_resp_id_table()
        for pid, val in CP_2A_PRE:
            tp.set_comparam(pid, val)
        tp.connect()
        # GUESS: install a table with the functional request id as 0x1F and no
        # meaningful response id (functional broadcast expects no unique response).
        tp.start_cop(COP_SENDRECV, data=b"", num_send=0, num_recv=-1)
        tp.start_cop(COP_STARTCOMM)
        tp.start_cop(COP_UPDATEPARAM)
        tp.install_resp_id_table(FUNCTIONAL_REQ_CANID, FUNCTIONAL_REQ_CANID)
        tp.start_cop(COP_UPDATEPARAM)
        # cyclic send: 3E 80, Time=period_ms, NumSendCycles=-1 (forever)
        data = _u32be(FUNCTIONAL_REQ_CANID) + bytes([0x3E, 0x80])
        tp.start_cop(COP_SENDRECV, data=data, time_ms=period_ms, num_send=-1, num_recv=0)
        self._tp = tp
        log.info("hardware-cyclic TesterPresent running (%d ms)", period_ms)

    def start_tester_present_thread(self, period_s: float = 0.8):
        """ALTERNATIVE: software timer. Sends 3E 80 functionally every period_s on a
        dedicated functional CLL. Simpler to reason about, but a stalled interpreter
        can let the ECU session lapse. Prefer start_tester_present()."""
        tp = DpduLink(self.host, self.port).open()
        tp.ioctl_clear_rx()
        tp.create_cll(RESOURCE_ISOTP)
        tp.clear_resp_id_table()
        for pid, val in CP_2A_PRE:
            tp.set_comparam(pid, val)
        tp.connect()
        tp.start_cop(COP_SENDRECV, data=b"", num_send=0, num_recv=-1)
        tp.start_cop(COP_STARTCOMM)
        tp.start_cop(COP_UPDATEPARAM)
        tp.install_resp_id_table(FUNCTIONAL_REQ_CANID, FUNCTIONAL_REQ_CANID)
        tp.start_cop(COP_UPDATEPARAM)
        self._tp = tp
        stop = self._evt_stop

        def _loop():
            payload = bytes([0x3E, 0x80])
            while not stop.is_set():
                try:
                    tp.send_uds(payload, req_canid=FUNCTIONAL_REQ_CANID)
                except Exception as e:
                    log.warning("TesterPresent thread send failed: %s", e)
                    return
                stop.wait(period_s)

        threading.Thread(target=_loop, daemon=True).start()
        log.info("software-thread TesterPresent running (%.2f s)", period_s)

    # -- event socket -------------------------------------------------------
    def _event_loop(self):
        assert self.evt is not None
        while not self._evt_stop.is_set():
            try:
                mid, payload = read_frame(self.evt, timeout=1.0)
            except socket.timeout:
                continue
            except (DpduError, OSError):
                break
            if mid == MID_EVENT:
                self._events.put((mid, payload))
            elif mid == MID_LEN_IND:
                # multi-frame length indication: the MDI reassembles and delivers
                # the full UDS as a single following 0x863, so just note it.
                log.debug("1505 length indication: %s", payload.hex())
            else:
                log.debug("unexpected event mid 0x%x: %s", mid, payload.hex())

    def _drain_events(self):
        try:
            while True:
                self._events.get_nowait()
        except queue.Empty:
            pass

    def _wait_uds(self, timeout: float) -> bytes | None:
        """Pop the next 0x863 event and extract its UDS payload, or None on timeout."""
        if timeout <= 0:
            return None
        try:
            _, payload = self._events.get(timeout=timeout)
        except queue.Empty:
            return None
        return self._extract_uds(payload)

    def _extract_uds(self, payload: bytes) -> bytes | None:
        """0x863 tail: ... <u32 CANid_BE><u32 blockLen><u32 CANid_BE><data> (§4).

        blockLen==0 -> TX confirmation (no data). We locate the response CAN id
        (known exactly, e.g. 0x145AF180) and take the bytes after its LAST
        occurrence as the UDS payload — robust against the undocumented header.
        """
        marker = _u32be(self._resp_canid)
        idx = payload.rfind(marker)
        if idx < 0:
            return None                       # TX confirm or a different responder
        data = payload[idx + 4:]
        return data if data else None


# convenience ----------------------------------------------------------------
def open_ecu80(host: str = DEVICE_IP_DEFAULT, tester_present: bool = True) -> DpduLink:
    """One-call bring-up of ECU 0x80 with cyclic TesterPresent running."""
    link = DpduLink(host).open()
    link.bringup_ecu(ECU80_REQ_CANID, ECU80_RESP_CANID)
    if tester_present:
        link.start_tester_present()
    return link
