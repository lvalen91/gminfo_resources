"""UART relay: the backend is a CLIENT of the existing ser2net loopback TCP ports.

ser2net owns the serial device (kickolduser=true), so we keep at most ONE upstream
connection per port and fan its bytes out to all browser subscribers. config.UART_PORTS
is now just the one confirmed-working VIP console port; a port whose device turned out
to be absent would yield a ser2net "Device open failure" banner and an immediate close,
surfaced as unreachable rather than hidden.

Two ser2net facts shape the probe: kickolduser=true means a probe connection to a port
that is streaming would KICK the live stream, and two ports on the same device would lock
each other out while either is connected (the sibling-device backoff below exists for
that case, should a second real port ever be added). So the probe never touches a port,
or a device, that a live stream holds; it reports that stream's state instead.
"""
from __future__ import annotations

import asyncio

from . import config

BACKOFF_MIN, BACKOFF_MAX = 2.0, 30.0


def _is_open_fail(text: str) -> bool:
    return "Device open fail" in text  # ser2net: "Device open failure: ..."


class UartPort:
    def __init__(self, spec: dict):
        self.spec = spec
        self.id = spec["id"]
        self._subs: set[asyncio.Queue] = set()
        self._task: asyncio.Task | None = None
        self.reachable: bool | None = None
        self.connected = False
        self.last_line: str = ""
        self.status_note: str = ""

    @property
    def streaming(self) -> bool:
        return self._task is not None and not self._task.done()

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        # maxsize: the field-capture tap (capture.py) asks for a deeper queue than a browser
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subs.add(q)
        if not self.streaming:
            self._task = asyncio.create_task(self._run())
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)
        if not self._subs and self.streaming:
            self._task.cancel()  # release the ser2net port (and its device lock) now

    def _fanout(self, text: str) -> None:
        for q in list(self._subs):
            try:
                q.put_nowait(text)
            except asyncio.QueueFull:
                pass

    async def _run(self) -> None:
        backoff = BACKOFF_MIN
        last_note = None
        try:
            while self._subs:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(self.spec["host"], self.spec["port"]), timeout=4)
                except (OSError, asyncio.TimeoutError) as e:
                    self.reachable = False
                    self.status_note = f"connect failed: {type(e).__name__}"
                else:
                    self.connected = True
                    got_data = False
                    try:
                        while self._subs:
                            try:
                                data = await asyncio.wait_for(reader.read(512), timeout=30)
                            except asyncio.TimeoutError:
                                continue  # a silent line is normal; keep the connection
                            if not data:
                                break
                            text = data.decode("latin-1")
                            if _is_open_fail(text):
                                self.reachable = False
                                self.status_note = "ser2net: device open fail (serial device absent or busy)"
                                break
                            got_data = True
                            self.reachable = True
                            self.status_note = "streaming"
                            self.last_line = text.strip()[-200:] or self.last_line
                            self._fanout(text)
                    except OSError as e:
                        self.status_note = f"read error: {type(e).__name__}"
                    finally:
                        self.connected = False
                        writer.close()
                        try:
                            await writer.wait_closed()
                        except OSError:
                            pass
                    if got_data and self.reachable:
                        backoff = BACKOFF_MIN  # a healthy session ended (kicked / ser2net restart)
                if not self._subs:
                    break
                # Tell subscribers once per distinct failure rather than per retry.
                if self.status_note != last_note and self.status_note != "streaming":
                    self._fanout(f"\r\n\x1b[90m-- {self.status_note}; retrying every <= {int(BACKOFF_MAX)}s --\x1b[0m\r\n")
                last_note = self.status_note
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
        except asyncio.CancelledError:
            pass

    def status(self) -> dict:
        return {"id": self.id, "label": self.spec["label"], "port": self.spec["port"],
                "dev": self.spec["dev"], "baud": self.spec["baud"],
                "reachable": self.reachable, "note": self.status_note,
                "subscribers": len(self._subs)}


class UartHub:
    def __init__(self):
        self.ports = {p["id"]: UartPort(p) for p in config.UART_PORTS}
        self._probe_lock = asyncio.Lock()

    def get(self, pid: str) -> UartPort | None:
        return self.ports.get(pid)

    async def _probe_one(self, p: dict) -> tuple[bool | None, str]:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(p["host"], p["port"]), timeout=2)
        except (OSError, asyncio.TimeoutError) as e:
            return False, f"connect failed: {type(e).__name__}"
        try:
            try:
                data = await asyncio.wait_for(reader.read(256), timeout=1.2)
            except asyncio.TimeoutError:
                return None, "connected, no banner"  # listening but unconfirmed
            txt = data.decode("latin-1")
            if _is_open_fail(txt):
                return False, "device open fail (serial absent)"
            return True, "listening"
        except OSError as e:
            return False, f"read error: {type(e).__name__}"
        finally:
            writer.close()
            try:
                # wait for the close so ser2net releases the device lock before the
                # next probe opens a sibling port on the same device
                await writer.wait_closed()
            except OSError:
                pass

    async def probe(self) -> list[dict]:
        """Reachability probe of every port (for /api/status), without disturbing streams."""
        async with self._probe_lock:  # concurrent pollers must not race on shared devices
            busy_devs = {port.spec["dev"]: port for port in self.ports.values() if port.streaming}
            probed_devs: set[str] = set()
            out = []
            for p in config.UART_PORTS:
                port = self.ports[p["id"]]
                holder = busy_devs.get(p["dev"])
                if port.streaming:
                    reach = port.reachable
                    note = f"live stream ({len(port._subs)} viewer(s)): {port.status_note or 'connecting'}"
                elif holder is not None:
                    reach, note = None, f"not probed: {p['dev']} held by live stream {holder.id}"
                else:
                    sibling = p["dev"] in probed_devs
                    if sibling:
                        # ser2net frees the device lock ~<100 ms after the previous probe of
                        # a port on the same device closed; probing at once reads "busy" as
                        # "absent" (measured while this list still had multiple ttyS0 ports).
                        await asyncio.sleep(0.3)
                    reach, note = await self._probe_one(p)
                    if sibling and reach is False and "open fail" in note:
                        await asyncio.sleep(0.5)
                        reach, note = await self._probe_one(p)
                    probed_devs.add(p["dev"])
                # ok = listening + device open; error = device absent / connect fail; stale = unknown
                state = "ok" if reach else ("error" if reach is False else "stale")
                out.append({"id": p["id"], "label": p["label"], "port": p["port"],
                            "dev": p["dev"], "baud": p["baud"], "reachable": reach,
                            "state": state, "note": note})
            return out
