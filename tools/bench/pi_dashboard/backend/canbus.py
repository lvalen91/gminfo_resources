"""can0 observer (shared SocketCAN reader + stats) and CAN sequence runner.

The observer is a passive CAN_RAW reader on can0 - it never transmits, so it coexists
with the keepalive service and any one-shot sender (the whole point of the SocketCAN
migration). Sequences are run by invoking the existing can0_radio.py (which owns all
frame-selection logic); this module only supplies the IO orchestration and, for the
continuous keepalive, defers to the systemd unit.
"""
from __future__ import annotations

import asyncio
import json
import struct
import time
from collections import defaultdict, deque

from . import config

CAN_FRAME = struct.Struct("=IB3x8s")
CAN_ERR_FLAG = 0x20000000
CAN_RTR_FLAG = 0x40000000
CAN_EFF_FLAG = 0x80000000


class CanObserver:
    """Single reader task on can0, fanning frames out to subscriber queues and keeping
    rolling per-ID counts and a 1-second frame-rate / error estimate."""

    def __init__(self, iface: str = config.CAN_IFACE):
        self.iface = iface
        self._subs: set[asyncio.Queue] = set()
        self._task: asyncio.Task | None = None
        self.id_counts: dict[int, int] = defaultdict(int)
        self.total = 0
        self.errors = 0
        self._recent = deque(maxlen=4000)  # (monotonic, is_error) -- rate/error-rate stats only
        # Replay backlog for a brand-new subscriber: ~22 fps steady state measured on this
        # bench (2026-11-25), so 3000 frames is ~2-3 min of backlog -- enough that a fresh
        # page load (or the decode panel reopening) isn't empty while new frames trickle in,
        # without holding more than a bus-cycle or two's worth of history.
        self._replay: deque[str] = deque(maxlen=3000)
        self.last_error: str | None = None
        self.up = False

    def subscribe(self) -> asyncio.Queue:
        # maxsize comfortably covers the full replay seed plus live frames arriving while a
        # slow consumer (a laggy browser tab) drains it.
        q: asyncio.Queue = asyncio.Queue(maxsize=3500)
        for msg in self._replay:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                break
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def frame_rate(self) -> float:
        now = time.monotonic()
        return sum(1 for t, _ in self._recent if now - t <= 1.0)

    def stats(self) -> dict:
        now = time.monotonic()
        # `rate` only ever feeds the ok/zero state call below (the owner found the
        # frame-rate number itself useless and it has been dropped from the UI and
        # this dict; nothing else in the repo consumes a "frame_rate" field).
        rate = sum(1 for t, _ in self._recent if now - t <= 1.0)
        err_rate = sum(1 for t, e in self._recent if e and now - t <= 1.0)
        top = sorted(self.id_counts.items(), key=lambda kv: -kv[1])[:16]
        # Explicit three-way state so neither the UI nor an LLM infers "zero" from empty:
        #   ok    = reader attached and frames arriving
        #   zero  = reader attached, bus confirmed idle (radio absent/asleep)
        #   error = reader socket down / last error set
        #   stale = reader task not running (we are not actually observing)
        if self._task is None or self._task.done():
            state = "stale"
        elif not self.up:
            state = "error"
        elif rate > 0:
            state = "ok"
        else:
            state = "zero"
        return {
            "iface": self.iface, "up": self.up, "state": state, "total": self.total,
            "errors": self.errors, "error_rate": err_rate,
            "unique_ids": len(self.id_counts),
            "top_ids": [{"id": f"{cid:03X}", "count": n} for cid, n in top],
            "last_error": self.last_error,
        }

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        import socket as _s
        loop = asyncio.get_running_loop()
        while True:
            sock = None
            try:
                sock = _s.socket(_s.PF_CAN, _s.SOCK_RAW, _s.CAN_RAW)
                sock.setsockopt(_s.SOL_CAN_RAW, _s.CAN_RAW_ERR_FILTER, 0x1FFFFFFF)
                sock.bind((self.iface,))
                sock.setblocking(False)
                self.up = True
                self.last_error = None
                while True:
                    raw = await loop.sock_recv(sock, 16)
                    if len(raw) < 16:
                        continue
                    ident, dlc, data = CAN_FRAME.unpack(raw)
                    is_err = bool(ident & CAN_ERR_FLAG)
                    now = time.monotonic()
                    self._recent.append((now, is_err))
                    self.total += 1
                    if is_err:
                        self.errors += 1
                        continue
                    cid = ident & (0x1FFFFFFF if ident & CAN_EFF_FLAG else 0x7FF)
                    self.id_counts[cid] += 1
                    msg = json.dumps({
                        "t": round(now, 4), "id": f"{cid:03X}", "dlc": dlc,
                        "ext": bool(ident & CAN_EFF_FLAG), "rtr": bool(ident & CAN_RTR_FLAG),
                        "data": data[:dlc].hex(),
                    })
                    self._replay.append(msg)
                    for q in list(self._subs):
                        try:
                            q.put_nowait(msg)
                        except asyncio.QueueFull:
                            pass
            except asyncio.CancelledError:
                raise
            except OSError as e:
                self.up = False
                self.last_error = f"{type(e).__name__}: {e}"
                await asyncio.sleep(2.0)  # can0 may be mid-bounce; retry
            finally:
                if sock is not None:
                    sock.close()
