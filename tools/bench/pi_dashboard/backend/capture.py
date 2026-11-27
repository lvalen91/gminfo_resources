"""Field capture: total, indiscriminate raw capture of T1 Ethernet, CAN and the VIP UART
to an external USB drive (the "Capture" tab). For when the Pi rides in a real vehicle and
the traffic may include things this bench has never seen -- nothing here filters.

Additive and independent of every other feature:
  * T1  -- `dumpcap` (Wireshark's capture engine) on the PHYSICAL parent `eth0`, never a
           VLAN subinterface. eth0 (bcmgenet) reports rx-vlan-offload "off [fixed]", so
           802.1Q tags stay in the frame: a bench test captured VLAN 2 (IEEE 1722 AVTP),
           VLAN 4, VLAN 5 and untagged gPTP (0x88F7) in one file. Runs as this user: zeno
           is in the `wireshark` group, which Debian's dumpcap grants CAP_NET_RAW, so no
           sudo. Promiscuous (dumpcap default), full snaplen.
  * CAN -- its own `candump` process: a SECOND, independent CAN_RAW socket on can0 with no
           ID filter (every frame), all error-frame classes, RX/TX direction marker (-x: "T" =
           sent by this Pi, e.g. the 0x53B keepalive; "R" = from the bus), log-file format,
           -D so a can0 bounce does not end it. canbus.py's observer and candecode.py are
           not touched; this never transmits.
  * UART -- ser2net's port 4000 has kickolduser=true: a second TCP client KICKS the first
           (verified on this Pi), so a separate reader would cut the live UART tab. The
           capture instead subscribes to the dashboard's own single upstream connection
           (uart.UartPort fan-out): the live view and the file share it, nothing is kicked,
           ser2net's config is untouched. Bytes are written exactly as received (the
           dashboard's own in-band "-- connect failed --" notices are kept out of the
           file and logged as events), plus uart.timing.tsv (wall time, byte offset, length)
           so the console can be lined up with the pcap / CAN timestamps.

Storage is never the SD card: only a block device whose lsblk TRAN is "usb" and that hosts
no system mount is offered, and before any process is (re)started the session directory's
st_dev is re-checked against "/" and /boot/firmware (a failed mount would leave an empty
mountpoint directory ON the SD card -- this check is what makes that impossible to write
to). Every blocking filesystem call against the drive runs in this module's own small
thread pool under a timeout, so a yanked or wedged USB drive can stall only this feature,
never the event loop the rest of the dashboard (CAN observer, UDS, decode, Pi tab) runs on.

Lifecycle: Tier-2 plan -> execute starts one session (one timestamped folder, the chosen
streams together); Stop is a plain, always-available action (like stopping a continuous
CAN sequence): it ends every process cleanly, syncs and unmounts the drive, and only then
reports "safe to unplug". A stream that dies on its own is restarted into a new segment
(never on a missing / full drive). Drive removed -> session aborted, processes killed, the
stale mount lazily detached. Free space under RESERVE_BYTES -> clean stop.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import queue
import re
import shutil
import signal
import socket
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config

MOUNT_BASE = Path(os.environ.get("CAPTURE_MOUNT_BASE", "/media/pibench-capture"))
CAPTURE_DIRNAME = "pibench_captures"
T1_IFACE = os.environ.get("CAPTURE_T1_IFACE", "eth0")
CAN_IFACE = config.CAN_IFACE
UART_PORT_ID = config.UART_PORTS[0]["id"] if config.UART_PORTS else None
# Segment rotation: FAT32 (most USB sticks) caps a file at 4 GiB; T1 alone measured
# ~440 KB/s on the bench (1.6 GB/h), so files roll over well before that. A rollover
# starts the new process first and stops the old one after, so a boundary duplicates a
# few frames rather than losing any.
SEGMENT_BYTES = int(os.environ.get("CAPTURE_SEGMENT_BYTES", str(1 << 30)))
RESERVE_BYTES = int(os.environ.get("CAPTURE_RESERVE_BYTES", str(128 << 20)))   # stop below
LOW_BYTES = 1 << 30                                                            # warn below
POLL_S = 2.0
IO_TIMEOUT = 3.0
STOP_WAIT_S = 6.0
DUMPCAP = shutil.which("dumpcap") or "/usr/bin/dumpcap"
CANDUMP = shutil.which("candump") or "/usr/bin/candump"
STDBUF = shutil.which("stdbuf") or "/usr/bin/stdbuf"

# Bench self-test hook ONLY, unset in normal use: block devices (e.g. a loop device over an
# image in /tmp) treated as if they were USB, so the whole mount/capture/stop path can be
# exercised without a stick. The off-SD st_dev check still applies to them.
TEST_DEVICES = {p for p in os.environ.get("CAPTURE_TEST_DEVICES", "").split(",") if p}
SYSTEM_MOUNTS = {"/", "/boot", "/boot/firmware", "/usr", "/var", "/home", "[SWAP]"}
_UIDGID = f"uid={os.getuid()},gid={os.getgid()}"
# lsblk FSTYPE -> (mount -t, options). Others are listed but refused.
FS_MOUNT = {
    "vfat": ("vfat", f"{_UIDGID},umask=0022,noatime,flush"),
    "exfat": ("exfat", f"{_UIDGID},umask=0022,noatime"),
    "ntfs": ("ntfs3", f"{_UIDGID},umask=0022,noatime"),
    "ext4": ("ext4", "noatime"), "ext3": ("ext3", "noatime"), "ext2": ("ext2", "noatime"),
    "btrfs": ("btrfs", "noatime"), "xfs": ("xfs", "noatime"), "f2fs": ("f2fs", "noatime"),
}
STREAMS = {
    "t1": {"label": f"T1 Ethernet ({T1_IFACE}, raw, all VLANs + untagged)", "file": "t1", "ext": "pcap"},
    "can": {"label": f"CAN ({CAN_IFACE}, every frame + error frames)", "file": CAN_IFACE, "ext": "log"},
    "uart": {"label": "UART (VIP console ttyS0 via the dashboard's ser2net link)", "file": "uart", "ext": "log"},
}

_IO = ThreadPoolExecutor(max_workers=4, thread_name_prefix="capture-io")


async def _io(fn, *args, timeout: float = IO_TIMEOUT):
    """Blocking FS call on the USB drive, off the event loop, bounded. A call wedged in
    the kernel (dead device) only occupies one of this module's own worker threads."""
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(_IO, fn, *args), timeout)


async def _run(args: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(proc.wait(), 2)
        return 124, "", f"timed out after {timeout:.0f}s"
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


def _last_line(t: str) -> str:
    lines = [l.strip() for l in (t or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _mounts() -> dict[str, str]:
    """mountpoint -> source, from /proc (procfs: never blocks on a device)."""
    out = {}
    try:
        for line in Path("/proc/self/mounts").read_text().splitlines():
            f = line.split()
            if len(f) >= 2:
                out[f[1].replace("\\040", " ")] = f[0]
    except OSError:
        pass
    return out


def _system_devs() -> set[int]:
    devs = set()
    for m in ("/", "/boot/firmware", "/boot"):
        with contextlib.suppress(OSError):
            devs.add(os.stat(m).st_dev)
    return devs


# ============================ USB drive detection ===============================
async def list_volumes() -> list[dict]:
    """USB block volumes (partitions, or a whole-disk filesystem) that host no system
    mount. Polled (lsblk), not udev-driven: the UI polls while the Capture tab is open."""
    rc, out, err = await _run(["lsblk", "-J", "-b", "-o",
                               "NAME,PATH,TYPE,TRAN,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS,MODEL,VENDOR,SERIAL"],
                              timeout=5)
    if rc != 0:
        raise RuntimeError(f"lsblk failed: {_last_line(err) or rc}")
    vols = []
    for disk in json.loads(out).get("blockdevices", []):
        is_usb = disk.get("type") == "disk" and (disk.get("tran") or "").lower() == "usb"
        if not is_usb and disk.get("path") not in TEST_DEVICES:
            continue
        parts = [c for c in disk.get("children") or [] if c.get("type") == "part"]
        allmp = {m for d in [disk, *parts] for m in (d.get("mountpoints") or []) if m}
        if allmp & SYSTEM_MOUNTS:
            continue    # e.g. a USB-booted Pi's own root disk: never offered
        info = {"name": disk.get("name"), "model": (disk.get("model") or "").strip(),
                "vendor": (disk.get("vendor") or "").strip(), "size": disk.get("size")}
        for v in parts or ([disk] if disk.get("fstype") else []):
            mps = [m for m in (v.get("mountpoints") or []) if m]
            fs = v.get("fstype")
            vols.append({
                "id": v.get("uuid") or v.get("name"), "name": v.get("name"), "path": v.get("path"),
                "fstype": fs, "supported": fs in FS_MOUNT, "label": v.get("label"),
                "uuid": v.get("uuid"), "size": v.get("size"),
                "mountpoint": mps[0] if mps else None,
                "ours": bool(mps and mps[0].startswith(str(MOUNT_BASE) + "/")),
                "disk": info,
            })
    for v in vols:
        if v["mountpoint"]:
            try:
                st = await _io(os.statvfs, v["mountpoint"])
                v["free"], v["total"] = st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize
            except (OSError, asyncio.TimeoutError) as e:
                v["free"] = v["total"] = None
                v["space_error"] = f"{type(e).__name__}: {e}"
    return vols


def _safe_dirname(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:48] or "usb"


async def _verified_off_sd(path: str) -> None:
    """Raise unless `path` is on a filesystem other than the SD card's / and /boot."""
    st = await _io(os.stat, path)
    if st.st_dev in _system_devs():
        raise RuntimeError(f"{path} is on the Pi's own SD card filesystem -- refusing to write there")


def mount_target(vol: dict) -> str:
    return vol["mountpoint"] or str(MOUNT_BASE / _safe_dirname(vol["label"] or vol["id"]))


async def mount_volume(vol: dict) -> tuple[str, bool]:
    """Mount `vol` if it is not mounted; return (mountpoint, mounted_by_us)."""
    if vol["mountpoint"]:
        if not await _io(os.path.ismount, vol["mountpoint"]):
            raise RuntimeError(f"{vol['mountpoint']} is listed as mounted but is not a mount point")
        await _verified_off_sd(vol["mountpoint"])
        return vol["mountpoint"], False
    if not vol["supported"]:
        raise RuntimeError(f"filesystem {vol['fstype']!r} on {vol['path']} is not supported "
                           f"(supported: {', '.join(sorted(FS_MOUNT))})")
    fstype, opts = FS_MOUNT[vol["fstype"]]
    mnt = mount_target(vol)
    rc, _, err = await _run(["sudo", "-n", "mkdir", "-p", mnt], timeout=5)
    if rc:
        raise RuntimeError(f"mkdir {mnt}: {_last_line(err)}")
    if mnt in _mounts():
        raise RuntimeError(f"{mnt} already has something else mounted on it")
    rc, _, err = await _run(["sudo", "-n", "mount", "-t", fstype, "-o", opts, vol["path"], mnt], timeout=30)
    if rc:
        raise RuntimeError(f"mount {vol['path']} ({fstype}) failed: {_last_line(err) or rc}")
    if not await _io(os.path.ismount, mnt):
        raise RuntimeError(f"mount reported success but {mnt} is not a mount point")
    await _verified_off_sd(mnt)
    return mnt, True


async def unmount(mnt: str, lazy: bool = False) -> dict:
    if mnt not in _mounts():
        return {"ok": True, "mountpoint": mnt, "note": "was not mounted"}
    sync_rc = None
    if not lazy:
        sync_rc, _, _ = await _run(["sync", "-f", mnt], timeout=60)
    rc, _, err = await _run(["sudo", "-n", "umount", *(["-l"] if lazy else []), mnt], timeout=30)
    still = mnt in _mounts()
    if not still and mnt.startswith(str(MOUNT_BASE) + "/"):
        await _run(["sudo", "-n", "rmdir", mnt], timeout=5)
    ok = rc == 0 and not still
    return {"ok": ok, "mountpoint": mnt, "sync_exit": sync_rc, "lazy": lazy,
            "error": None if ok else (_last_line(err) or ("still mounted" if still else f"exit {rc}"))}


# ============================ streams ===========================================
class _Stream:
    key = ""

    def __init__(self, sess: "Session"):
        self.sess = sess
        self.spec = STREAMS[self.key]
        self.state = "pending"
        self.segments: list[dict] = []     # {file, started, ended, bytes}
        self.restarts = 0
        self.last_error: str | None = None
        self.bytes = 0
        self.rate_bps = 0.0
        self._last_sample: tuple[float, int] | None = None

    def seg_path(self, n: int) -> Path:
        s = self.spec
        name = f"{s['file']}.{s['ext']}" if n == 1 else f"{s['file']}.{n:03d}.{s['ext']}"
        return self.sess.dir / name

    def _new_segment(self) -> Path:
        p = self.seg_path(len(self.segments) + 1)
        self.segments.append({"file": p.name, "started": time.time(), "ended": None, "bytes": 0})
        return p

    def update_sizes(self, sizes: dict[str, int]) -> None:
        for seg in self.segments:
            if seg["file"] in sizes:
                seg["bytes"] = sizes[seg["file"]]
        total = sum(s["bytes"] for s in self.segments)
        now = time.monotonic()
        if self._last_sample and now > self._last_sample[0]:
            self.rate_bps = max(0.0, (total - self._last_sample[1]) / (now - self._last_sample[0]))
        self._last_sample = (now, total)
        self.bytes = total

    def status(self) -> dict:
        cur = self.segments[-1] if self.segments else None
        return {"key": self.key, "label": self.spec["label"], "state": self.state,
                "file": cur["file"] if cur else None, "bytes": self.bytes,
                "rate_bps": round(self.rate_bps), "segments": len(self.segments),
                "restarts": self.restarts, "last_error": self.last_error}


class _ProcStream(_Stream):
    """A capture child process writing straight to the drive (dumpcap / candump)."""

    def __init__(self, sess):
        super().__init__(sess)
        self.proc: asyncio.subprocess.Process | None = None
        self.tail: deque[str] = deque(maxlen=30)
        self._stopping = False
        self._restart_task: asyncio.Task | None = None
        self._backoff = 1.0
        self._spawned_at = 0.0

    to_stdout = False   # True: the capture is the process's stdout (we open the file)

    def argv(self, path: Path) -> list[str]:
        raise NotImplementedError

    async def _spawn(self) -> None:
        await _verified_off_sd(str(self.sess.dir))     # re-checked before EVERY (re)start
        path = self._new_segment()
        argv = self.argv(path)
        out_fd = None
        if self.to_stdout:
            # the process writes the capture to stdout; open the file here (off-loop)
            out_fd = await _io(os.open, str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdin=asyncio.subprocess.DEVNULL,
                stdout=out_fd if out_fd is not None else asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE if out_fd is not None else asyncio.subprocess.STDOUT,
                start_new_session=True)
        finally:
            if out_fd is not None:
                os.close(out_fd)
        self.proc = proc
        self._spawned_at = time.monotonic()
        self.state = "capturing"
        self.sess.event(f"{self.key}: started pid {proc.pid} -> {path.name}: {' '.join(argv)}")
        asyncio.create_task(self._watch(proc, path.name))

    async def _watch(self, proc, fname: str) -> None:
        try:
            pipe = proc.stderr if self.to_stdout else proc.stdout
            while True:
                line = await pipe.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip()
                if text:
                    self.tail.append(text)
                    self.sess.event(f"{self.key}[{proc.pid}]: {text}")
        except Exception:   # noqa: BLE001 -- a reader problem must never escape
            pass
        rc = await proc.wait()
        for seg in self.segments:
            if seg["file"] == fname and seg["ended"] is None:
                seg["ended"] = time.time()
        if proc is not self.proc or self._stopping or not self.sess.active:
            return          # rotated away, or a requested stop
        why = f"killed by {signal.Signals(-rc).name}" if rc < 0 else f"exit code {rc}"
        last = self.tail[-1] if self.tail else ""
        self.last_error = f"exited unexpectedly ({why})" + (f": {last}" if re.search(r"(?i)err|fail|denied|no such", last) else "")
        self.sess.event(f"{self.key}: {self.last_error}")
        if time.monotonic() - self._spawned_at > 60:
            self._backoff = 1.0     # it had been running fine: restart quickly
        self.state = "restarting"
        self._restart_task = asyncio.create_task(self._restart_later())

    async def _restart_later(self) -> None:
        await asyncio.sleep(self._backoff)
        self._backoff = min(self._backoff * 2, 30.0)
        if self._stopping or not self.sess.active or not self.sess.drive_ok:
            return
        try:
            self.restarts += 1
            await self._spawn()
        except Exception as e:   # noqa: BLE001
            self.last_error = f"restart failed: {type(e).__name__}: {e}"
            self.state = "failed"
            self.sess.event(f"{self.key}: {self.last_error}")
            if self.sess.active and self.sess.drive_ok:
                self.state = "restarting"
                self._restart_task = asyncio.create_task(self._restart_later())

    async def start(self) -> None:
        await self._spawn()

    async def rotate_if_needed(self) -> None:
        if self.state != "capturing" or not self.segments or self.segments[-1]["bytes"] < SEGMENT_BYTES:
            return
        old = self.proc
        await self._spawn()                 # new segment first: no gap
        await asyncio.sleep(0.5)
        await self._terminate(old)
        self.sess.event(f"{self.key}: rolled over to {self.segments[-1]['file']}")

    @staticmethod
    async def _terminate(proc, sig=signal.SIGINT, wait: float = STOP_WAIT_S) -> bool:
        if proc is None or proc.returncode is not None:
            return True
        with contextlib.suppress(ProcessLookupError):
            proc.send_signal(sig)
        try:
            await asyncio.wait_for(proc.wait(), wait)
            return True
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), 2)   # may hang in D state on a dead drive
            return False

    async def stop(self, hard: bool = False) -> None:
        self._stopping = True
        if self._restart_task:
            self._restart_task.cancel()
        clean = await self._terminate(self.proc, signal.SIGKILL if hard else signal.SIGINT,
                                      0.5 if hard else STOP_WAIT_S)
        await asyncio.sleep(0.2)   # let _watch drain the final stdout lines (dumpcap stats)
        self.state = "stopped" if clean and not hard else "killed"


class T1Stream(_ProcStream):
    key = "t1"

    def argv(self, path):
        # -F pcap: classic pcap (single interface; every tool reads it). -s 0 is dumpcap's
        # default full snaplen; promiscuous is its default. -q: no running counter on
        # stderr; the final received/dropped summary still prints and lands in events.
        return [DUMPCAP, "-i", T1_IFACE, "-F", "pcap", "-B", "16", "-q", "-w", str(path)]


class CanStream(_ProcStream):
    key = "can"

    def argv(self, path):
        # "can0,0:0,#FFFFFFFF": id 0 / mask 0 = every arbitration id (11- and 29-bit), plus
        # every error-frame class (-e is refused together with -L, so the error mask goes in
        # the filter spec). -x RX/TX marker; -D survive a can0 down/up; -r a large socket rx
        # buffer (capped by net.core.rmem_max, 4 MiB here). -L log-file format on stdout,
        # which is the file (to_stdout), line-buffered by stdbuf: candump's own -f file is a
        # 4 KiB stdio buffer, so a crash lost up to ~100 frames (measured on the bench);
        # line-buffered it loses at most the frame in flight.
        return [STDBUF, "-oL", CANDUMP, "-L", "-x", "-D", "-r", str(4 << 20), f"{CAN_IFACE},0:0,#FFFFFFFF"]

    to_stdout = True


_NOTICE = re.compile(r"^\r\n\x1b\[90m-- .* --\x1b\[0m\r\n$", re.S)   # uart.py's own in-band notice
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class UartStream(_Stream):
    """Taps the dashboard's single ser2net connection (see module docstring). A dedicated
    writer thread owns the files, so a stalled drive never blocks the event loop."""
    key = "uart"

    def __init__(self, sess, hub):
        super().__init__(sess)
        self.port = hub.get(UART_PORT_ID) if UART_PORT_ID else None
        self._q: asyncio.Queue | None = None
        self._tq: queue.Queue = queue.Queue(maxsize=8192)
        self._fwd: asyncio.Task | None = None
        self._thread: threading.Thread | None = None
        self.dropped = 0
        self._stop_evt = threading.Event()

    async def start(self) -> None:
        if self.port is None:
            raise RuntimeError("no UART port configured")
        await _verified_off_sd(str(self.sess.dir))
        self._thread = threading.Thread(target=self._writer, name="capture-uart", daemon=True)
        self._thread.start()
        self._q = self.port.subscribe(maxsize=4000, replay=False)
        self._fwd = asyncio.create_task(self._forward())
        self.state = "capturing"
        self.sess.event(f"uart: tapping dashboard ser2net link ({self.port.spec['host']}:{self.port.spec['port']}) -> uart.log")

    async def _forward(self) -> None:
        while True:
            text = await self._q.get()
            if _NOTICE.match(text):
                self.sess.event("uart link: " + _ANSI.sub("", text).strip())
                continue
            try:
                self._tq.put_nowait((time.time(), text.encode("latin-1", errors="replace")))
            except queue.Full:
                self.dropped += len(text)

    def _writer(self) -> None:
        f = tf = None
        seg_bytes = 0
        try:
            while not self._stop_evt.is_set() or not self._tq.empty():
                try:
                    ts, data = self._tq.get(timeout=0.5)
                except queue.Empty:
                    continue
                if f is None or seg_bytes >= SEGMENT_BYTES:
                    if f is not None:
                        f.close(); tf.close()
                        self.segments[-1]["ended"] = time.time()
                    p = self._new_segment()
                    f = open(p, "ab", buffering=0)
                    tf = open(p.with_name(p.stem + ".timing.tsv"), "a", buffering=1)
                    tf.write("# epoch_s\tbyte_offset\tlength\n")
                    seg_bytes = 0
                tf.write(f"{ts:.6f}\t{seg_bytes}\t{len(data)}\n")
                f.write(data)
                seg_bytes += len(data)
        except OSError as e:
            self.last_error = f"write failed: {type(e).__name__}: {e}"
            self.state = "failed"
        finally:
            for h in (f, tf):
                if h is not None:
                    with contextlib.suppress(OSError):
                        h.flush(); os.fsync(h.fileno()); h.close()
            if self.segments and self.segments[-1]["ended"] is None:
                self.segments[-1]["ended"] = time.time()

    async def rotate_if_needed(self) -> None:
        if self.state == "failed" and self.sess.active:
            self.sess.event(f"uart: {self.last_error}")

    async def stop(self, hard: bool = False) -> None:
        if self._q is not None and self.port is not None:
            self.port.unsubscribe(self._q)
        if self._fwd:
            self._fwd.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._fwd
        self._stop_evt.set()
        if self._thread is not None:
            loop = asyncio.get_running_loop()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(loop.run_in_executor(None, self._thread.join, 0 if hard else 5), 6)
        if self.state != "failed":
            self.state = "stopped" if not (self._thread and self._thread.is_alive()) else "killed"

    def status(self) -> dict:
        return {**super().status(), "dropped_bytes": self.dropped,
                "link": (self.port.status_note if self.port else None)}


# ============================ session ===========================================
class Session:
    def __init__(self, vol: dict, mnt: str, mounted_by_us: bool, sdir: Path, keys: list[str]):
        self.vol, self.mnt, self.mounted_by_us, self.dir = vol, mnt, mounted_by_us, sdir
        self.keys = keys
        self.started = time.time()
        self.stopped: float | None = None
        self.active = True
        self.drive_ok = True
        self.state = "starting"
        self.end_reason: str | None = None
        self.events: deque[str] = deque(maxlen=400)
        self.streams: dict[str, _Stream] = {}
        self.free: int | None = None
        self.total: int | None = None
        self.io_fail = 0
        self.unmount_result: dict | None = None
        # <session>/events.log is appended by this session's own thread, so the log on
        # the drive never blocks the loop and a dead drive stalls only this thread.
        self._evq: queue.Queue = queue.Queue(maxsize=10000)
        threading.Thread(target=self._event_writer, name="capture-events", daemon=True).start()

    def event(self, text: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {text}"
        self.events.append(line)
        with contextlib.suppress(queue.Full):
            self._evq.put_nowait(line)

    def _event_writer(self) -> None:
        while True:
            try:
                line = self._evq.get(timeout=5)
            except queue.Empty:
                if not self.drive_ok:
                    return
                continue
            if not self.drive_ok:
                return
            try:
                with open(self.dir / "events.log", "a") as f:
                    f.write(line + "\n")
            except OSError:
                pass

    def status(self) -> dict:
        return {"id": self.dir.name, "dir": str(self.dir), "mountpoint": self.mnt,
                "volume": {k: self.vol.get(k) for k in ("id", "path", "label", "fstype")},
                "state": self.state, "active": self.active, "started": self.started,
                "stopped": self.stopped, "end_reason": self.end_reason,
                "free": self.free, "total": self.total,
                "low_space": self.free is not None and self.free < LOW_BYTES,
                "streams": [s.status() for s in self.streams.values()],
                "events": list(self.events)[-25:], "unmount": self.unmount_result}

    def manifest(self) -> dict:
        return {"format": "pibench field capture v1", "host": socket.gethostname(),
                "boot_id": _read("/proc/sys/kernel/random/boot_id"),
                "clock_note": "wall-clock timestamps; the Pi has no RTC -- without NTP in a "
                              "vehicle the absolute time may be wrong, but all three streams "
                              "share the same clock",
                "started": self.started, "stopped": self.stopped, "end_reason": self.end_reason,
                "volume": self.vol, "mountpoint": self.mnt, "segment_bytes": SEGMENT_BYTES,
                "streams": {k: {**s.status(), "segment_list": s.segments,
                                **({"argv": s.argv(Path("<file>"))} if isinstance(s, _ProcStream) else {})}
                            for k, s in self.streams.items()},
                "link_info": getattr(self, "link_info", {})}


def _read(p: str) -> str | None:
    try:
        return Path(p).read_text().strip()
    except OSError:
        return None


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def _dir_sizes(d: str) -> dict[str, int]:
    out = {}
    with os.scandir(d) as it:
        for e in it:
            with contextlib.suppress(OSError):
                out[e.name] = e.stat().st_size
    return out


class CaptureManager:
    def __init__(self, uart_hub):
        self.uart_hub = uart_hub
        self.session: Session | None = None
        self.last: Session | None = None
        self._lock = asyncio.Lock()
        self._monitor: asyncio.Task | None = None

    # ---------------- preflight / plan ----------------
    async def preflight(self, volume_id: str | None, keys: list[str]) -> dict:
        if self.session and self.session.active:
            raise ValueError("a capture session is already running")
        keys = [k for k in STREAMS if k in set(keys or [])]
        if not keys:
            raise ValueError("pick at least one stream")
        checks = {}
        if "t1" in keys:
            if not Path(f"/sys/class/net/{T1_IFACE}").exists():
                raise ValueError(f"interface {T1_IFACE} does not exist")
            if not os.access(DUMPCAP, os.X_OK):
                raise ValueError("dumpcap is not installed")
            checks["t1"] = f"{DUMPCAP} on {T1_IFACE}"
        if "can" in keys:
            if not Path(f"/sys/class/net/{CAN_IFACE}").exists():
                raise ValueError(f"interface {CAN_IFACE} does not exist")
            if not os.access(CANDUMP, os.X_OK):
                raise ValueError("candump is not installed")
            checks["can"] = f"{CANDUMP} on {CAN_IFACE}"
        if "uart" in keys:
            if not UART_PORT_ID or self.uart_hub.get(UART_PORT_ID) is None:
                raise ValueError("no UART port configured")
            checks["uart"] = f"dashboard ser2net link {UART_PORT_ID}"
        vols = await list_volumes()
        if not vols:
            raise ValueError("no USB storage detected -- plug in a USB drive")
        if volume_id:
            vol = next((v for v in vols if v["id"] == volume_id), None)
            if vol is None:
                raise ValueError(f"USB volume {volume_id!r} is no longer present")
        else:
            usable = [v for v in vols if v["supported"] or v["mountpoint"]]
            if len(usable) != 1:
                raise ValueError(f"{len(usable)} usable USB volumes -- pick one" if usable
                                 else "no USB volume with a supported filesystem")
            vol = usable[0]
        if not vol["supported"] and not vol["mountpoint"]:
            raise ValueError(f"{vol['path']}: filesystem {vol['fstype']!r} not supported")
        if vol.get("free") is not None and vol["free"] < RESERVE_BYTES * 2:
            raise ValueError(f"only {vol['free'] >> 20} MiB free on {vol['path']}")
        return {"volume": vol, "streams": keys, "checks": checks}

    # ---------------- start ----------------
    async def start(self, volume_id: str, keys: list[str]) -> dict:
        async with self._lock:
            pre = await self.preflight(volume_id, keys)
            vol, keys = pre["volume"], pre["streams"]
            mnt, ours = await mount_volume(vol)
            try:
                root = Path(mnt) / CAPTURE_DIRNAME
                try:
                    await _io(lambda: root.mkdir(exist_ok=True))
                    if not await _io(os.access, str(root), os.W_OK):
                        raise PermissionError(str(root))
                except PermissionError:
                    rc, _, err = await _run(["sudo", "-n", "install", "-d", "-o", str(os.getuid()),
                                             "-g", str(os.getgid()), str(root)], timeout=10)
                    if rc:
                        raise RuntimeError(f"cannot create {root}: {_last_line(err)}")
                name = time.strftime("%Y%m%d-%H%M%S")
                sdir = root / name
                n = 1
                while await _io(sdir.exists):
                    n += 1
                    sdir = root / f"{name}-{n}"
                await _io(sdir.mkdir)
                await _verified_off_sd(str(sdir))
            except BaseException:
                if ours:
                    await unmount(mnt)
                raise
            sess = Session(vol, mnt, ours, sdir, keys)
            sess.link_info = await self._link_info(keys)
            self.session = sess
            sess.event(f"session start: {sdir} on {vol['path']} ({vol['fstype']}), streams {keys}")
            classes = {"t1": T1Stream, "can": CanStream}
            for k in keys:
                s = UartStream(sess, self.uart_hub) if k == "uart" else classes[k](sess)
                sess.streams[k] = s
                try:
                    await s.start()
                except Exception as e:  # noqa: BLE001 -- one stream failing must not block the others
                    s.state, s.last_error = "failed", f"{type(e).__name__}: {e}"
                    sess.event(f"{k}: start failed: {s.last_error}")
            sess.state = "capturing"
            with contextlib.suppress(Exception):
                await _io(_write_json, sdir / "session.json", sess.manifest())
            self._monitor = asyncio.create_task(self._watch())
            failed = [k for k, s in sess.streams.items() if s.state == "failed"]
            return {"ok": not failed, "session": sess.status(),
                    "error": f"stream(s) failed to start: {', '.join(failed)}" if failed else None,
                    "summary": f"Capturing to {sdir.name} on {vol['label'] or vol['path']}"}

    async def _link_info(self, keys) -> dict:
        info = {}
        cmds = {"t1": [["ip", "-d", "-s", "link", "show", T1_IFACE], ["/usr/sbin/ethtool", T1_IFACE]],
                "can": [["ip", "-d", "-s", "link", "show", CAN_IFACE]]}
        for k in keys:
            for c in cmds.get(k, []):
                rc, out, err = await _run(c, timeout=5)
                info[" ".join(c)] = (out or err).strip()
        if "uart" in keys:
            info["uart"] = {k: v for k, v in (config.UART_PORTS[0] if config.UART_PORTS else {}).items()}
        return info

    # ---------------- monitor ----------------
    async def _watch(self) -> None:
        sess = self.session
        dev = sess.vol["name"]
        last_manifest = time.monotonic()
        while sess.active:
            await asyncio.sleep(POLL_S)
            if not sess.active:
                break
            try:
                gone = not Path(f"/sys/class/block/{dev}").exists() or sess.mnt not in _mounts()
                if gone:
                    await self._abort("USB drive removed (or its mount disappeared) during capture")
                    break
                try:
                    st = await _io(os.statvfs, sess.mnt)
                    sizes = await _io(_dir_sizes, str(sess.dir))
                    sess.io_fail = 0
                except (OSError, asyncio.TimeoutError) as e:
                    sess.io_fail += 1
                    sess.event(f"drive I/O check failed ({sess.io_fail}/3): {type(e).__name__}: {e}")
                    if sess.io_fail >= 3:
                        await self._abort("USB drive stopped responding")
                        break
                    continue
                sess.free, sess.total = st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize
                for s in sess.streams.values():
                    s.update_sizes(sizes)
                if sess.free < RESERVE_BYTES:
                    sess.event(f"free space {sess.free >> 20} MiB < reserve {RESERVE_BYTES >> 20} MiB: stopping")
                    asyncio.create_task(self.stop(reason="USB drive full"))
                    break
                for s in sess.streams.values():
                    await s.rotate_if_needed()
                if time.monotonic() - last_manifest > 60:
                    last_manifest = time.monotonic()
                    with contextlib.suppress(Exception):
                        await _io(_write_json, sess.dir / "session.json", sess.manifest())
            except Exception as e:  # noqa: BLE001 -- the monitor itself must never die silently
                sess.event(f"monitor error: {type(e).__name__}: {e}")

    async def _abort(self, reason: str) -> None:
        sess = self.session
        if not sess or not sess.active:
            return
        sess.event(f"ABORT: {reason}")
        sess.active, sess.drive_ok = False, False
        sess.state, sess.end_reason, sess.stopped = "aborted", reason, time.time()
        await asyncio.gather(*(s.stop(hard=True) for s in sess.streams.values()), return_exceptions=True)
        sess.unmount_result = await unmount(sess.mnt, lazy=True)
        self.last, self.session = sess, None

    # ---------------- stop ----------------
    async def stop(self, reason: str = "stopped by user") -> dict:
        async with self._lock:
            sess = self.session
            if sess is None or not sess.active:
                return {"ok": True, "summary": "No capture running", "safe": await self.safe_state()}
            sess.state = "stopping"
            sess.event(f"session stop: {reason}")
            sess.active = False
            if self._monitor and self._monitor is not asyncio.current_task():
                self._monitor.cancel()
            await asyncio.gather(*(s.stop() for s in sess.streams.values()), return_exceptions=True)
            sess.stopped, sess.end_reason = time.time(), reason
            with contextlib.suppress(Exception):
                sizes = await _io(_dir_sizes, str(sess.dir))
                for s in sess.streams.values():
                    s.update_sizes(sizes)
            manifest_ok = True
            try:
                await _io(_write_json, sess.dir / "session.json", sess.manifest(), timeout=10)
            except Exception as e:  # noqa: BLE001
                manifest_ok = False
                sess.event(f"could not write session.json: {type(e).__name__}: {e}")
            # let the event thread write what is queued, then stop it touching the drive
            for _ in range(20):
                if sess._evq.empty():
                    break
                await asyncio.sleep(0.1)
            sess.drive_ok = False
            await asyncio.sleep(0.2)
            sess.unmount_result = await unmount(sess.mnt)
            killed = [k for k, s in sess.streams.items() if s.state == "killed"]
            sess.state = "stopped"
            self.last, self.session = sess, None
            ok = sess.unmount_result["ok"] and not killed
            totals = ", ".join(f"{k} {s.bytes:,} B" for k, s in sess.streams.items())
            return {"ok": ok, "session": sess.status(), "manifest_written": manifest_ok,
                    "error": None if ok else (f"stream(s) had to be killed: {', '.join(killed)}" if killed
                                              else f"unmount failed: {sess.unmount_result.get('error')}"),
                    "summary": f"Stopped ({totals}); drive unmounted -- safe to unplug"}

    async def unmount_volume(self, volume_id: str) -> dict:
        async with self._lock:
            if self.session and self.session.active:
                raise ValueError("stop the capture first")
            vol = next((v for v in await list_volumes() if v["id"] == volume_id), None)
            if vol is None:
                raise ValueError(f"USB volume {volume_id!r} not found")
            if not vol["mountpoint"]:
                return {"ok": True, "summary": f"{vol['path']} is not mounted -- safe to unplug"}
            r = await unmount(vol["mountpoint"])
            return {**r, "summary": f"{vol['path']} unmounted -- safe to unplug" if r["ok"] else None}

    async def shutdown(self) -> None:
        with contextlib.suppress(Exception):
            if self.session and self.session.active:
                await asyncio.wait_for(self.stop(reason="dashboard shutting down"), 40)

    # ---------------- status ----------------
    async def safe_state(self, vols: list[dict] | None = None) -> dict:
        if self.session and self.session.active:
            return {"safe": False, "reason": "capture running"}
        if self.session and self.session.state == "stopping":
            return {"safe": False, "reason": "stopping -- flushing files"}
        if vols is None:
            try:
                vols = await list_volumes()
            except Exception as e:  # noqa: BLE001
                return {"safe": None, "reason": f"cannot list drives: {e}"}
        mounted = [v for v in vols if v["mountpoint"]]
        if mounted:
            return {"safe": False, "reason": "mounted: " + ", ".join(
                f"{v['path']} at {v['mountpoint']}" for v in mounted) + " -- unmount before unplugging"}
        if vols:
            return {"safe": True, "reason": "no USB volume is mounted; all capture files are closed"}
        return {"safe": None, "reason": "no USB drive plugged in"}

    def brief(self) -> dict:
        s = self.session
        if s and s.active:
            return {"state": "capturing", "id": s.dir.name,
                    "streams": {k: x.state for k, x in s.streams.items()}}
        if self.last and self.last.state == "aborted":
            return {"state": "aborted", "id": self.last.dir.name, "reason": self.last.end_reason}
        return {"state": "idle"}

    async def status(self) -> dict:
        err = None
        try:
            vols = await list_volumes()
        except Exception as e:  # noqa: BLE001
            vols, err = [], f"{type(e).__name__}: {e}"
        cur = self.session
        return {"time": time.time(), "volumes": vols, "volumes_error": err,
                "session": cur.status() if cur else None,
                "last": self.last.status() if self.last else None,
                "safe_to_unplug": await self.safe_state(vols) if not err else {"safe": None, "reason": err},
                "streams": [{"key": k, "label": v["label"]} for k, v in STREAMS.items()],
                "config": {"t1_iface": T1_IFACE, "can_iface": CAN_IFACE, "uart_port": UART_PORT_ID,
                           "segment_bytes": SEGMENT_BYTES, "reserve_bytes": RESERVE_BYTES,
                           "mount_base": str(MOUNT_BASE)}}
