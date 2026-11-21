"""Standalone D-PDU-over-TCP radio-cal transcript decoder for the GM SPS capture.

Reuses the exact TCP-frame framing from mdi2/dpdu_replay.py (load_stream via
`tshark follow,tcp,raw`, [u32 len LE][u32 mid LE][payload] reframe) and the
0x863 receive-event layout from mdi2/captured_events.parse_radio_rx.

Decodes the RADIO ECU 0x80 (req CAN 0x14DA80F1 / resp 0x145AF180) UDS
request->response transcript in time order from one command/event stream pair.

Usage:
  python -I radio_cal_decode.py <pcap> <cmd_stream> <evt_stream> [--struct]

Pass the pcap path as argv; do not run from inside the capture directory.
"""
from __future__ import annotations
import struct, subprocess, sys

TSHARK = "/opt/homebrew/bin/tshark"
MID_REQ = 0x463          # client->device StartComPrimitive (send)
MID_EVENT = 0x863        # device->client receive-event
RADIO_REQ_CAN = 0x14DA80F1
RADIO_RESP_CAN = 0x145AF180
BCM_REQ_CAN = 0x14DA40F1
BCM_RESP_CAN = 0x142AF140


def _reframe(blob: bytes):
    frames, i, n = [], 0, len(blob)
    while i + 8 <= n:
        total, mid = struct.unpack_from("<II", blob, i)
        if total < 8 or i + total > n:
            # tolerate trailing junk rather than abort the whole stream
            break
        frames.append((i, mid, blob[i + 8:i + total]))
        i += total
    return frames, i, n


def load_stream(pcap: str, stream: int):
    out = subprocess.run([TSHARK, "-r", pcap, "-q", "-z", f"follow,tcp,raw,{stream}"],
                         capture_output=True, text=True).stdout.splitlines()
    start = next(i for i, l in enumerate(out) if l.startswith("Node 1:")) + 1
    cli, srv = bytearray(), bytearray()
    for l in out[start:]:
        if l.startswith("===") or not l.strip():
            continue
        if l.startswith("\t"):
            srv += bytes.fromhex(l.strip())
        else:
            cli += bytes.fromhex(l.strip())
    return bytes(cli), bytes(srv)


def dir_times(pcap: str, stream: int, src_ip: str):
    """byteoffset->frame.time_relative map for one direction of a stream."""
    rows = subprocess.run(
        [TSHARK, "-r", pcap, "-Y",
         f"tcp.stream=={stream} && ip.src=={src_ip} && tcp.len>0",
         "-T", "fields", "-e", "tcp.seq", "-e", "frame.time_relative", "-e", "tcp.len"],
        capture_output=True, text=True).stdout.splitlines()
    segs = {}
    for r in rows:
        parts = r.split("\t")
        if len(parts) != 3:
            continue
        seq, t, ln = parts
        segs.setdefault(int(seq), (float(t), int(ln)))
    off_time, off = [], 0
    for seq in sorted(segs):
        t, ln = segs[seq]
        off_time.append((off, t))
        off += ln
    def time_at(byteoff):
        best = off_time[0][1] if off_time else 0.0
        for o, t in off_time:
            if o <= byteoff:
                best = t
            else:
                break
        return best
    return time_at


def parse_req(pay: bytes):
    """Parse a 0x463 send-primitive: handle, cop, marker, can_id, uds.

    Layout per mdi2/programming_transport.build_one_shot:
      <IHHHHI handle, cop_id, marker, 0x8004, 0, datalen> + data(=can_id BE + uds) + ...
    """
    if len(pay) < 20:
        return None
    handle, cop_id, marker, tag, z, datalen = struct.unpack_from("<IHHHHI", pay, 0)
    data = pay[16:16 + datalen]  # <IHHHHI consumes 16 bytes, then can_id(BE)+uds
    if len(data) < 5:
        return None
    can_id = int.from_bytes(data[:4], "big")
    uds = data[4:]
    return dict(handle=handle, cop=cop_id, marker=marker, tag=tag,
                can_id=can_id, uds=uds)


def parse_evt(pay: bytes):
    """Parse a 0x863 receive-event per captured_events.parse_radio_rx layout."""
    if len(pay) < 8:
        return None
    etype = struct.unpack_from("<I", pay, 4)[0]
    handle = struct.unpack_from("<I", pay, 0)[0]
    if etype != 1 or len(pay) < 74:
        return dict(handle=handle, etype=etype, uds=None, raw=pay)
    cop = struct.unpack_from("<H", pay, 20)[0]
    can_id = int.from_bytes(pay[70:74], "big")
    size = struct.unpack_from("<I", pay, 74)[0]
    uds = None
    if 78 + size == len(pay) and size >= 5:
        if int.from_bytes(pay[78:82], "big") == can_id:
            uds = pay[82:]
    return dict(handle=handle, etype=etype, cop=cop, can_id=can_id, uds=uds, raw=pay)


SID = {0x10: "DiagSessionControl", 0x11: "ECUReset", 0x22: "ReadDID",
       0x27: "SecurityAccess", 0x2E: "WriteDID", 0x31: "RoutineControl",
       0x34: "RequestDownload", 0x36: "TransferData", 0x37: "RequestTransferExit",
       0x3E: "TesterPresent",
       0x50: "+DiagSession", 0x51: "+ECUReset", 0x62: "+ReadDID",
       0x67: "+SecurityAccess", 0x6E: "+WriteDID", 0x71: "+RoutineControl",
       0x74: "+RequestDownload", 0x76: "+TransferData", 0x77: "+TransferExit",
       0x7E: "+TesterPresent", 0x7F: "NegativeResponse"}


def summ(uds: bytes) -> str:
    if not uds:
        return "(empty)"
    s = uds[0]
    name = SID.get(s, f"SID{ s:02X}")
    if s == 0x7F and len(uds) >= 3:
        return f"7F {uds[1]:02X} NRC={uds[2]:02X} ({name} of {SID.get(uds[1],hex(uds[1]))})"
    head = uds[:8].hex()
    if s in (0x34,):
        if len(uds) >= 11:
            return f"34 RequestDownload fmt={uds[1]:02X}{uds[2]:02X} addr={uds[3:7].hex()} size={int.from_bytes(uds[7:11],'big')}"
    if s == 0x74 and len(uds) >= 2:
        width = uds[1] >> 4
        return f"74 +RequestDownload lenfmt={uds[1]:02X} maxblk={int.from_bytes(uds[2:2+width],'big') if width else '?'}"
    if s == 0x36:
        return f"36 TransferData blk={uds[1]:02X} payload={len(uds)-2}B"
    if s == 0x76:
        return f"76 +TransferData blk={uds[1]:02X}"
    if s in (0x10, 0x50, 0x11, 0x51, 0x27, 0x67, 0x3E, 0x7E):
        return f"{uds[0]:02X} {name} sub/args={uds[1:].hex() or '-'}"
    if s in (0x22, 0x62):
        return f"{uds[0]:02X} {name} DID={uds[1:3].hex()} data={uds[3:].hex()}"
    if s in (0x2E, 0x6E):
        return f"{uds[0]:02X} {name} DID={uds[1:3].hex()} data[{len(uds)-3}B]={uds[3:3+16].hex()}{'..' if len(uds)>19 else ''}"
    if s in (0x31, 0x71):
        return f"{uds[0]:02X} {name} sub={uds[1]:02X} RID={uds[2:4].hex()} rest={uds[4:].hex() or '-'}"
    if s == 0x37:
        return f"37 RequestTransferExit rest={uds[1:].hex() or '-'}"
    if s == 0x77:
        return "77 +RequestTransferExit"
    return f"{name} {head}"


def full_analysis(pcap, cmd_stream, evt_stream, CLIENT, DEVICE):
    cmd_cli, _ = load_stream(pcap, cmd_stream)
    _, evt_srv = load_stream(pcap, evt_stream)
    cmd_cli_t = dir_times(pcap, cmd_stream, CLIENT)
    evt_srv_t = dir_times(pcap, evt_stream, DEVICE)
    rc_frames, _, _ = _reframe(cmd_cli)
    es_frames, _, _ = _reframe(evt_srv)

    ev = []  # (t, dir, handle, cop, uds_clean, raw)
    for off, mid, pay in rc_frames:
        if mid != MID_REQ or len(pay) < 20:
            continue
        p = parse_req(pay)
        if p and p["can_id"] == RADIO_REQ_CAN:
            ev.append((cmd_cli_t(off), "REQ", p["handle"], p["cop"], clean_uds(p["uds"]), p["uds"]))
    for off, mid, pay in es_frames:
        if mid != MID_EVENT or len(pay) < 82:
            continue
        p = parse_evt(pay)
        if p and p.get("uds") is not None and p.get("can_id") == RADIO_RESP_CAN:
            ev.append((evt_srv_t(off), "RSP", p["handle"], p.get("cop"), clean_uds(p["uds"]), p["uds"]))
    ev.sort(key=lambda e: (e[0], 0 if e[1] == "REQ" else 1))

    handles = sorted({e[2] for e in ev})
    print(f"# radio CLL handles seen (req id 0x{RADIO_REQ_CAN:08x} / resp 0x{RADIO_RESP_CAN:08x}): "
          f"{[hex(h) for h in handles]}")
    for h in handles:
        reqs = sum(1 for e in ev if e[2] == h and e[1] == "REQ")
        rsps = sum(1 for e in ev if e[2] == h and e[1] == "RSP")
        t0 = min((e[0] for e in ev if e[2] == h), default=0)
        t1 = max((e[0] for e in ev if e[2] == h), default=0)
        print(f"#   handle {h:08x}: {reqs} req, {rsps} rsp, t={t0:.3f}..{t1:.3f}s")

    print("\n# ===== TIME-ORDERED RADIO TRANSCRIPT (all CLLs merged) =====")
    for t, d, h, cop, uds, raw in ev:
        print(f"{t:10.4f} {d} h{h & 0xff:02x} cop{cop or 0:04x}  {summ(uds)}")

    # ---- Serialization / correlation analysis per handle ----
    print("\n# ===== SERIALIZATION CHECK (one-response-per-request, in order) =====")
    for h in handles:
        seq = [e for e in ev if e[2] == h]
        inflight = None          # (sid, t)
        pend_seen = False
        violations = []
        req_count = rsp_final = pend_count = 0
        for t, d, _, cop, uds, raw in seq:
            if d == "REQ":
                req_count += 1
                if inflight is not None:
                    violations.append(f"t={t:.4f} REQ {uds[:1].hex()} sent while {inflight[0]:02X} still in flight")
                inflight = (uds[0], t)
                pend_seen = False
            else:  # RSP
                if not uds:
                    continue
                if uds[0] == 0x7F and len(uds) >= 3:
                    if inflight is None:
                        violations.append(f"t={t:.4f} RSP 7F {uds[1]:02X} with no request in flight")
                    elif uds[1] != inflight[0]:
                        violations.append(f"t={t:.4f} RSP 7F {uds[1]:02X} != in-flight {inflight[0]:02X}")
                    if len(uds) == 3 and uds[2] == 0x78:
                        pend_count += 1
                        pend_seen = True
                        continue           # pending: request stays in flight
                    rsp_final += 1
                    inflight = None         # terminal negative
                    continue
                # positive
                if inflight is None:
                    violations.append(f"t={t:.4f} positive RSP {uds[0]:02X} with no request in flight")
                elif uds[0] != (inflight[0] + 0x40) & 0xFF:
                    violations.append(f"t={t:.4f} RSP SID {uds[0]:02X} != echo of req {inflight[0]:02X}")
                rsp_final += 1
                inflight = None
        status = "STRICT 1:1 (pending=0x78 allowed)" if not violations else f"{len(violations)} VIOLATION(S)"
        print(f"  handle {h:08x}: {req_count} req, {rsp_final} final rsp, {pend_count} x 0x78 pending -> {status}")
        for v in violations[:12]:
            print(f"      ! {v}")

    # ---- Routine inventory + MEC (F1A0) scan ----
    print("\n# ===== RoutineControl (31) inventory =====")
    rc = {}
    for t, d, h, cop, uds, raw in ev:
        if uds[:1] == b"\x31" and len(uds) >= 4:
            rid = uds[2:4].hex()
            rc.setdefault((rid, "REQ" if d == "REQ" else "RSP"), []).append((t, h, uds.hex()))
        if uds[:1] == b"\x71" and len(uds) >= 4:
            rid = uds[2:4].hex()
            rc.setdefault((rid, "RSP"), []).append((t, h, uds.hex()))
    for (rid, d), lst in sorted(rc.items()):
        ex = lst[0]
        print(f"  RID 0x{rid} {d} x{len(lst)}  first t={ex[0]:.3f} h{ex[1]&0xff:02x} bytes={ex[2][:24]}")

    print("\n# ===== MEC / F1A0 scan (irreversible manufacturer-enable) =====")
    mec_hits = [(t, d, h, uds.hex()) for t, d, h, cop, uds, raw in ev
                if b"\xf1\xa0" in uds or uds[:3] == b"\x2e\xf1\xa0"]
    if not mec_hits:
        print("  NO F1A0 / MEC-touching UDS on the radio in this capture (no 2E F1A0, no 22 F1A0).")
    else:
        for t, d, h, hx in mec_hits:
            print(f"  t={t:.4f} {d} h{h&0xff:02x} {hx}")
    # explicit write-service scan
    writes = [(t, d, h, uds.hex()) for t, d, h, cop, uds, raw in ev if uds[:1] == b"\x2e"]
    print("  --- all 2E WriteDID on radio: ---")
    for t, d, h, hx in writes:
        did = hx[2:6]
        print(f"    t={t:.4f} {d} h{h&0xff:02x} DID={did} len={ (len(hx)//2) - 3 }B")


def clean_uds(raw: bytes) -> bytes:
    """Strip ISO-TP single-frame PCI + 0x55 padding used by the padded CLL encoding.

    Padded short encoding: [SF-len:1][uds...][0x55 pad...]. Exact-fit CLL carries
    raw UDS (first byte is the response SID) with no padding -> returned as-is.
    """
    if raw and 1 <= raw[0] <= 7 and 1 + raw[0] <= len(raw) and all(b == 0x55 for b in raw[1 + raw[0]:]):
        return raw[1:1 + raw[0]]
    return raw


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    pcap, cmd_stream, evt_stream = args[0], int(args[1]), int(args[2])
    CLIENT = "192.168.171.30"
    DEVICE = "192.168.171.2"
    if "--full" in flags:
        return full_analysis(pcap, cmd_stream, evt_stream, CLIENT, DEVICE)

    cmd_cli, cmd_srv = load_stream(pcap, cmd_stream)
    evt_cli, evt_srv = load_stream(pcap, evt_stream)
    cmd_cli_t = dir_times(pcap, cmd_stream, CLIENT)
    cmd_srv_t = dir_times(pcap, cmd_stream, DEVICE)
    evt_srv_t = dir_times(pcap, evt_stream, DEVICE)

    rc_frames, cend, clen = _reframe(cmd_cli)
    rs_frames, _, _ = _reframe(cmd_srv)
    es_frames, eend, elen = _reframe(evt_srv)

    if "--struct" in flags:
        print(f"# cmd stream {cmd_stream}: {len(rc_frames)} client frames "
              f"(reframed {cend}/{clen}); {len(rs_frames)} server frames")
        from collections import Counter
        print("client mids:", Counter(m for _, m, _ in rc_frames))
        print("server mids:", Counter(m for _, m, _ in rs_frames))
        print(f"# evt stream {evt_stream}: server {len(es_frames)} frames (reframed {eend}/{elen})")
        print("evt server mids:", Counter(m for _, m, _ in es_frames))
        # show the radio handle(s) / cops seen
        for off, mid, pay in rc_frames[:6]:
            if mid == MID_REQ:
                p = parse_req(pay)
                if p:
                    print(f"  REQ off={off} handle=0x{p['handle']:08x} cop=0x{p['cop']:04x} "
                          f"marker=0x{p['marker']:04x} can=0x{p['can_id']:08x} uds={p['uds'][:12].hex()}")
        for off, mid, pay in es_frames[:12]:
            if mid == MID_EVENT:
                p = parse_evt(pay)
                if p and p.get("uds") is not None:
                    print(f"  EVT off={off} handle=0x{p['handle']:08x} cop=0x{p.get('cop',0):04x} "
                          f"can=0x{p.get('can_id',0):08x} uds={p['uds'][:12].hex()}")
        return

    # Build a time-ordered transcript limited to the radio handle(s).
    radio_handles = set()
    events = []  # (t, dir, kind, info)
    byteoff = 0
    for off, mid, pay in rc_frames:
        if mid == MID_REQ:
            p = parse_req(pay)
            if p and p["can_id"] in (RADIO_REQ_CAN,):
                radio_handles.add(p["handle"])
                events.append((cmd_cli_t(off), "REQ", p["handle"], p["cop"], p["can_id"], p["uds"]))
    # events (0x863) from the event stream server side
    for off, mid, pay in es_frames:
        if mid == MID_EVENT:
            p = parse_evt(pay)
            if p and p.get("uds") is not None and p.get("can_id") == RADIO_RESP_CAN:
                events.append((evt_srv_t(off), "RSP", p["handle"], p.get("cop"), p.get("can_id"), p["uds"]))

    events.sort(key=lambda e: e[0])
    print(f"# radio request handle(s): {[hex(h) for h in sorted(radio_handles)]}")
    print(f"# {sum(1 for e in events if e[1]=='REQ')} radio requests, "
          f"{sum(1 for e in events if e[1]=='RSP')} radio responses")
    print(f"# {'t_rel':>9} dir hndl   cop  {'summary'}")
    for t, d, h, cop, can, uds in events:
        print(f"{t:10.4f} {d} {h & 0xffffffff:08x} {cop if cop else 0:04x} {summ(uds)}")


if __name__ == "__main__":
    main()
