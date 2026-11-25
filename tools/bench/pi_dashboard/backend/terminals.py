"""PTY bridges for the browser terminals (xterm.js <-> real pty + process).

Two uses: a Pi login shell, and `adb -s <serial> shell`. A single implementation
spawns a child on a pty, pumps pty->websocket and websocket->pty, and handles resize.
LAN-only, no auth (owner's explicit choice) - this is a full shell, intentionally.
"""
from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import signal
import struct
import termios

from . import config


class PtySession:
    def __init__(self, argv: list[str], env: dict | None = None):
        self.argv = argv
        self.env = env
        self.pid = -1
        self.sid = -1  # session id == leader pid; kept after the leader is reaped
        self.fd = -1

    def spawn(self) -> None:
        pid, fd = pty.fork()
        if pid == 0:  # child
            try:
                environ = dict(os.environ)
                environ.setdefault("TERM", "xterm-256color")
                if self.env:
                    environ.update(self.env)
                os.execvpe(self.argv[0], self.argv, environ)
            except Exception as e:  # pragma: no cover - child
                os.write(2, f"exec failed: {e}\r\n".encode())
                os._exit(127)
        self.pid, self.sid, self.fd = pid, pid, fd
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def resize(self, cols: int, rows: int) -> None:
        if self.fd >= 0:
            winsz = struct.pack("HHHH", rows, cols, 0, 0)
            try:
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsz)
            except OSError:
                pass

    def write(self, data: bytes) -> None:
        if self.fd >= 0:
            try:
                os.write(self.fd, data)
            except OSError:
                pass

    def _session_members(self) -> list[int]:
        """Every process still in the child's session (pty.fork makes it a session leader),
        including background jobs, which live in their own process groups."""
        members = []
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open(f"/proc/{d}/stat", "rb") as f:
                    stat = f.read()
                # field 6 (session) follows the ")" that ends the comm field
                if int(stat[stat.rindex(b")") + 2:].split()[3]) == self.sid:
                    members.append(int(d))
            except (OSError, ValueError, IndexError):
                continue
        return members

    def close(self) -> None:
        """Hang up the whole pty session, kill the leader, and reap it (no zombie)."""
        if self.sid > 0:
            for p in self._session_members():
                for sig in (signal.SIGHUP, signal.SIGCONT):  # CONT so stopped jobs see the HUP
                    try:
                        os.kill(p, sig)
                    except (ProcessLookupError, PermissionError):
                        pass
            self.sid = -1
        if self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass
            self.pid = -1
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1


async def pump(session: PtySession, websocket, on_input) -> None:
    """Bridge a spawned PtySession to a Starlette WebSocket until either side closes.

    `on_input(msg)` returns ("data", bytes) | ("resize", (cols, rows)) | None.
    """
    loop = asyncio.get_running_loop()
    closed = asyncio.Event()

    def reader():
        try:
            data = os.read(session.fd, 4096)
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            closed.set()
            loop.remove_reader(session.fd)
            return
        if not data:
            closed.set()
            loop.remove_reader(session.fd)
            return
        asyncio.create_task(_safe_send(websocket, data, closed))

    async def watch_leader():
        # A background job left running (`sleep 999 &`) keeps the pty slave open, so the
        # master never sees EOF after the shell exits; end the session when the leader dies.
        while not closed.is_set():
            await asyncio.sleep(1.0)
            if session.pid <= 0:  # never waitpid(-1): it would reap unrelated children
                return
            try:
                pid, _ = os.waitpid(session.pid, os.WNOHANG)
            except ChildProcessError:
                pid = session.pid
            if pid == session.pid:
                session.pid = -1  # reaped here; close() still hangs up the rest via sid
                closed.set()

    loop.add_reader(session.fd, reader)
    leader_task = asyncio.create_task(watch_leader())
    try:
        while not closed.is_set():
            recv_task = asyncio.create_task(websocket.receive())
            closed_task = asyncio.create_task(closed.wait())
            done, pending = await asyncio.wait(
                {recv_task, closed_task}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            if closed_task in done:
                break
            try:
                msg = recv_task.result()
            except Exception:
                break
            parsed = on_input(msg)
            if parsed is None:
                continue
            kind, payload = parsed
            if kind == "data":
                session.write(payload)
            elif kind == "resize":
                session.resize(*payload)
    finally:
        leader_task.cancel()
        try:
            loop.remove_reader(session.fd)
        except (OSError, ValueError):
            pass
        session.close()
        # When the shell exits (EOF on the pty) close the socket too, so the browser shows
        # "session closed" instead of a dead terminal that silently swallows keystrokes.
        try:
            await websocket.close()
        except Exception:
            pass


async def _safe_send(websocket, data: bytes, closed: asyncio.Event) -> None:
    try:
        await websocket.send_bytes(data)
    except Exception:
        closed.set()


def pi_shell_argv() -> list[str]:
    shell = os.environ.get("SHELL", "/bin/bash")
    return [shell, "-l"]


def adb_shell_argv(serial: str) -> list[str]:
    return [config.ADB, "-s", serial, "shell"]
