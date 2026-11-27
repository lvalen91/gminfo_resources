"""CAN sequence orchestration: keepalive start/stop and one-shot/continuous schedules.

All frame bytes/timings come from can0_radio.py (which reuses the digest-pinned profile
and the existing builders). This module only decides *when* to run them and how they
coexist with the supervised keepalive service. A single asyncio lock serializes the
stateful transitions so two sequences never fight over the bus.

Every result carries an explicit ``ok`` and, on failure, an ``error`` string taken from
can0_radio.py's own JSON ``detail`` (e.g. "can0 transmit queue stayed full"), so a
failed live run is never indistinguishable from a successful one.

Continuous modes (full, startup-keepalive) run until SIGTERM. They are started in the
background: the request waits only long enough to catch an early failure (no ACK, queue
full, lock busy), then returns ``status: running``. keepalive-start / keepalive-stop and
any later sequence terminate a running continuous schedule first.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import signal

from . import config

CAN0_RADIO = str(config.BENCH_CAN_DIR / "can0_radio.py")
_PROFILE = str(config.HARNESS_PROFILE)
_lock = asyncio.Lock()

# can0_radio.py fails a frame after a 2.0 s echo timeout; wait past that before declaring
# a continuous schedule "running".
_CONTINUOUS_GRACE_S = 3.5
_STOP_TIMEOUT_S = 10.0
# Hard ceiling for a one-shot / dry-run can0_radio.py run (longest bounded schedule is the
# 40 s startup window). It runs while holding _lock, so a hung child must not hold the bus
# lock forever.
_ONESHOT_TIMEOUT_S = 120.0
# systemd states in which the keepalive unit is (or is about to be) on the bus. With
# Restart=always and no radio ACK the unit cycles active -> auto-restart ("activating"),
# so checking only "active" misses it and the sequence then races it for the schedule lock.
_RUNNING_STATES = {"active", "activating", "reloading", "deactivating"}

_continuous: dict | None = None   # {"proc", "name", "mode", "resume", "watcher"}
_last_continuous: dict | None = None

# Modes exposed as dashboard/LLM actions. "continuous" modes keep the radio alive;
# "oneshot" modes play once. keepalive_* map to the systemd unit.
# `kind` drives the control the dashboard renders:
#   service-start/service-stop -> an instant one-shot (systemctl, sub-second);
#   oneshot                    -> a RUN control with an elapsed/progress indicator;
#   continuous                 -> an ON/OFF toggle (the run keeps transmitting until stopped).
# `duration_s` is the code-known bounded run length of a one-shot (drives a determinate
# progress ring); continuous modes have none (they run until SIGTERM).
SEQUENCES = {
    "keepalive-start": {"kind": "service-start", "destructive": False,
                        "desc": "Start the supervised 0x53B keepalive on can0 (systemd); stops a running continuous sequence first."},
    "keepalive-stop": {"kind": "service-stop", "destructive": False,
                       "desc": "Stop the keepalive sender and any running continuous sequence (radio sleeps after "
                               "~608-630s of total silence -- bench-measured, see platform/can_bench_experiments.md "
                               "'Keepalive-content bisection')."},
    "startup": {"kind": "oneshot", "mode": "startup", "destructive": False, "duration_s": 40,
                "desc": "126-frame power-on startup window (40 s), then returns to keepalive."},
    "startup-keepalive": {"kind": "continuous", "mode": "startup-keepalive", "destructive": False,
                          "desc": "Startup window then continuous keepalive (replaces the service keepalive until keepalive-start/stop)."},
    "full": {"kind": "continuous", "mode": "full", "destructive": False,
             "desc": "Full 32-frame captured cycle, repeated (replaces the service keepalive until keepalive-start/stop)."},
    "vip-reset": {"kind": "oneshot", "mode": "vip-reset", "destructive": True, "duration_s": 10.5,
                  "desc": "VIP reset: 10.5 s synthetic 526 hold then release, then back to keepalive."},
}


def _args(mode: str, dry_run: bool) -> list[str]:
    args = [config.BENCH_PYTHON, CAN0_RADIO, mode, "--profile", _PROFILE, "--json"]
    if dry_run:
        args.append("--dry-run")
    return args


def _parse(mode: str, dry_run: bool, code: int | None, out: bytes, err: bytes) -> dict:
    result = {"mode": mode, "dry_run": dry_run, "exit_code": code,
              "stderr": err.decode(errors="replace").strip()[-2000:]}
    text = out.decode(errors="replace").strip()
    for line in reversed(text.splitlines()):
        try:
            result["result"] = json.loads(line)
            break
        except ValueError:
            continue
    if "result" not in result:
        result["stdout"] = text[-2000:]
    inner = result.get("result") or {}
    result["ok"] = code == 0
    if not result["ok"]:
        stderr_tail = result["stderr"].splitlines()[-1] if result["stderr"] else ""
        result["error"] = (inner.get("detail") or stderr_tail
                           or f"can0_radio.py exited with status {code}")
    return result


async def _run_can0_radio(mode: str, dry_run: bool) -> dict:
    proc = await asyncio.create_subprocess_exec(
        *_args(mode, dry_run), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=_ONESHOT_TIMEOUT_S)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass  # exited between the timeout and the kill
        with contextlib.suppress(Exception):
            await proc.wait()
        return {"mode": mode, "dry_run": dry_run, "exit_code": 124, "stderr": "", "ok": False,
                "error": f"can0_radio.py {mode} did not finish within {_ONESHOT_TIMEOUT_S:.0f} s; killed"}
    return _parse(mode, dry_run, proc.returncode, out, err)


async def _systemctl(action: str, unit: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", "systemctl", action, unit,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    return {"action": action, "unit": unit, "exit_code": proc.returncode,
            "ok": proc.returncode == 0, "stderr": err.decode(errors="replace").strip()}


async def keepalive_state() -> str:
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "is-active", config.KEEPALIVE_UNIT,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    out, _ = await proc.communicate()
    return out.decode().strip()


async def keepalive_active() -> bool:
    return await keepalive_state() in _RUNNING_STATES


def continuous_status() -> dict:
    if _continuous is not None:
        return {"running": True, "sequence": _continuous["name"], "mode": _continuous["mode"],
                "pid": _continuous["proc"].pid}
    return {"running": False, "last": _last_continuous}


async def _resume_keepalive() -> dict:
    return await _systemctl("start", config.KEEPALIVE_UNIT)


async def _watch_continuous(entry: dict) -> None:
    """Collect a background continuous run's result and resume the keepalive after it."""
    global _continuous, _last_continuous
    proc = entry["proc"]
    out, err = await proc.communicate()
    result = _parse(entry["mode"], False, proc.returncode, out, err)
    result["sequence"] = entry["name"]
    if _continuous is entry:
        _continuous = None
        if entry["resume"]:
            result["keepalive_resume"] = await _resume_keepalive()
    _last_continuous = result


async def _stop_continuous() -> dict | None:
    """Terminate a running continuous schedule (SIGTERM, can0_radio's clean stop)."""
    global _continuous
    entry = _continuous
    if entry is None:
        return None
    _continuous = None  # the watcher must not resume the keepalive; the caller decides
    proc = entry["proc"]
    if proc.returncode is None:
        proc.send_signal(signal.SIGTERM)
    try:
        await asyncio.wait_for(asyncio.shield(entry["watcher"]), _STOP_TIMEOUT_S)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass  # already exited between the timeout and the kill; the watcher reaps it
        await entry["watcher"]
    return {"stopped": entry["name"], "pid": proc.pid, "result": _last_continuous,
            "resume_keepalive": entry["resume"]}


async def run_sequence(name: str, dry_run: bool = True) -> dict:
    global _continuous
    spec = SEQUENCES.get(name)
    if spec is None:
        raise KeyError(name)
    async with _lock:
        kind = spec["kind"]
        if kind in ("service-start", "service-stop"):
            if dry_run:
                return {"sequence": name, "dry_run": True, "ok": True, "note": "dry-run: no change",
                        "continuous": continuous_status()}
            stopped = await _stop_continuous()
            r = await _systemctl("start" if kind == "service-start" else "stop", config.KEEPALIVE_UNIT)
            r.update(sequence=name, dry_run=False, stopped_continuous=stopped,
                     keepalive_state=await keepalive_state(),
                     note="keepalive service started" if kind == "service-start" else "keepalive service stopped")
            if not r["ok"]:
                r["error"] = r["stderr"] or f"systemctl {r['action']} exited {r['exit_code']}"
            return r

        if dry_run:
            r = await _run_can0_radio(spec["mode"], dry_run=True)
            r["sequence"] = name
            r["note"] = "dry-run: schedule validated, zero frames sent, keepalive untouched"
            return r

        # Live oneshot / continuous: must own the bus schedule. Stop a continuous run
        # this dashboard started, then pause the service keepalive (also when it is only
        # cycling through auto-restart).
        stopped = await _stop_continuous()
        ka_running = await keepalive_active()
        resume = ka_running or bool(stopped and stopped["resume_keepalive"])
        if ka_running:
            stop = await _systemctl("stop", config.KEEPALIVE_UNIT)
            if not stop["ok"]:
                return {"sequence": name, "mode": spec["mode"], "dry_run": False, "ok": False,
                        "error": f"could not stop {config.KEEPALIVE_UNIT}: {stop['stderr'] or stop['exit_code']}",
                        "keepalive_stop": stop}

        if kind == "continuous":
            proc = await asyncio.create_subprocess_exec(
                *_args(spec["mode"], False), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            entry = {"proc": proc, "name": name, "mode": spec["mode"], "resume": resume}
            entry["watcher"] = asyncio.create_task(_watch_continuous(entry))
            _continuous = entry
            done, _ = await asyncio.wait({entry["watcher"]}, timeout=_CONTINUOUS_GRACE_S)
            if done:  # exited early: a real failure (or an immediate stop); report it
                r = dict(_last_continuous or {})
                r.setdefault("ok", False)
                r["note"] = "continuous sequence exited during start-up"
                r["stopped_continuous"] = stopped
                return r
            return {"sequence": name, "mode": spec["mode"], "dry_run": False, "ok": True,
                    "status": "running", "pid": proc.pid, "stopped_continuous": stopped,
                    "note": ("continuous schedule transmitting in the background; "
                             "keepalive-start or keepalive-stop ends it"
                             + (" (keepalive resumes when it ends)" if resume else ""))}

        try:
            r = await _run_can0_radio(spec["mode"], dry_run=False)
        finally:
            # One-shots finish and leave the bus idle -> resume keepalive.
            if resume:
                resumed = await _resume_keepalive()
        r["sequence"] = name
        r["stopped_continuous"] = stopped
        if resume:
            r["keepalive_resume"] = resumed
            r["note"] = "keepalive paused for the sequence, then resumed"
        else:
            r["note"] = "keepalive was not running; left stopped"
        return r


def _tx_one_frame(can_id: int, data: bytes, extended: bool = False) -> tuple[bool, str | None]:
    """Blocking: one raw SocketCAN CAN_RAW send on config.CAN_IFACE, using the exact same
    wire layout canbus.py's observer reads (struct '=IB3x8s': native uint32 id, uint8 dlc,
    3 pad bytes, 8-byte data -- the standard Linux struct can_frame). Classic (non-FD)
    data frame; 11-bit id, or 29-bit when extended=True (CAN_EFF_FLAG set). Opens and
    closes its own socket; never touches the passive observer's own socket."""
    import socket as _s
    import struct as _struct
    frame_struct = _struct.Struct("=IB3x8s")
    sock = None
    try:
        sock = _s.socket(_s.PF_CAN, _s.SOCK_RAW, _s.CAN_RAW)
        sock.bind((config.CAN_IFACE,))
        sock.settimeout(2.0)
        cid = (can_id | 0x80000000) if extended else can_id  # 0x80000000 = CAN_EFF_FLAG
        sock.send(frame_struct.pack(cid, len(data), data.ljust(8, b"\x00")))
        return True, None
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        if sock is not None:
            sock.close()


async def send_one_frame(label: str, can_id: int, data: bytes, extended: bool = False,
                         pause_keepalive: bool = True) -> dict:
    """Transmit ONE raw frame on can0 under the shared bus-ownership lock. By default it
    pauses the keepalive for the frame and resumes it (clean single-owner send). With
    pause_keepalive=False it CO-SENDS: one extra frame alongside the running keepalive
    (CAN arbitration handles it) without stopping/restarting the keepalive service -- which
    matters because the keepalive unit reconfigures (down/up) can0 on start, so pausing it
    repeatedly thrashes the interface. Co-send is the right mode for a periodic re-assert."""
    if not pause_keepalive:
        # Co-send: no bus lock and no _stop_continuous() -- it must not end a running
        # continuous sequence (which would also leave the keepalive un-resumed); the one
        # frame simply goes out alongside whatever is transmitting.
        ok, err = await asyncio.to_thread(_tx_one_frame, can_id, data, extended)
        result = {"label": label, "can_id": f"{can_id:08X}" if extended else f"{can_id:03X}",
                  "extended": extended, "data_hex": data.hex(), "dlc": len(data),
                  "dry_run": False, "ok": ok, "stopped_continuous": None,
                  "note": "co-sent alongside the keepalive (keepalive not paused)"}
        if not ok:
            result["error"] = err
        return result
    async with _lock:
        stopped = await _stop_continuous()
        ka_running = await keepalive_active()
        resume = ka_running or bool(stopped and stopped["resume_keepalive"])
        if ka_running:
            stop = await _systemctl("stop", config.KEEPALIVE_UNIT)
            if not stop["ok"]:
                return {"label": label, "ok": False,
                        "error": f"could not stop {config.KEEPALIVE_UNIT}: {stop['stderr'] or stop['exit_code']}",
                        "keepalive_stop": stop, "stopped_continuous": stopped}
        try:
            ok, err = await asyncio.to_thread(_tx_one_frame, can_id, data, extended)
        finally:
            resumed = await _resume_keepalive() if resume else None
        result = {"label": label, "can_id": f"{can_id:08X}" if extended else f"{can_id:03X}",
                  "extended": extended, "data_hex": data.hex(), "dlc": len(data),
                  "dry_run": False, "ok": ok, "stopped_continuous": stopped}
        if not ok:
            result["error"] = err
        if resume:
            result["keepalive_resume"] = resumed
            result["note"] = "keepalive paused for the frame, then resumed"
        else:
            result["note"] = "keepalive was not running; left stopped"
        return result


def bus_lock() -> asyncio.Lock:
    """The shared bus-ownership lock itself, for a short raw exchange that must not
    interleave with a sequence/calibration run but does NOT take over the schedule (the
    raw-CAN5 UDS in can_uds.py: its own IDs, keepalive and any continuous run left as is).
    Unlike exclusive_bus() this stops nothing."""
    return _lock


def bus_busy() -> bool:
    """True while a sequence, single-owner frame send, calibration run or raw UDS exchange
    holds the bus lock. A periodic poll checks this and skips instead of queueing.

    Also True when the lock is momentarily free but a woken waiter has not yet resumed to
    re-take it (asyncio.Lock.release() clears _locked before the next waiter runs). In that
    window locked() is False yet a fresh acquire() would queue behind the pending waiter and
    block -- so a caller that gates on bus_busy() and then acquires with no await in between
    (the F085 poll) would otherwise still queue behind a long op and transmit late. Reporting
    a live waiter as busy keeps that acquire on asyncio.Lock's synchronous fast path."""
    if _lock.locked():
        return True
    waiters = getattr(_lock, "_waiters", None)
    return bool(waiters) and any(not w.cancelled() for w in waiters)


@contextlib.asynccontextmanager
async def exclusive_bus():
    """Own the dashboard's CAN bus lock for an external can0 owner that manages the
    keepalive service itself (calibration_write_can0.py stops it and restarts it in a
    finally). Stops any continuous schedule this dashboard started, so it never holds the
    can0 schedule lock against that owner. Yields the stop record (or None)."""
    async with _lock:
        yield await _stop_continuous()


async def stop_current() -> dict:
    """Stop a running continuous CAN sequence on request, independent of keepalive-start/
    stop or starting another sequence. Non-destructive: it only ever halts transmission
    (SIGTERM, can0_radio's clean stop) and, if the service keepalive was paused for this
    run, resumes it -- it never itself puts new frames on the bus."""
    async with _lock:
        stopped = await _stop_continuous()
        if stopped is None:
            return {"ok": True, "running": False, "note": "no continuous sequence was active"}
        result = {"ok": True, "running": False, **stopped}
        if stopped["resume_keepalive"]:
            result["keepalive_resume"] = await _resume_keepalive()
            result["note"] = f"stopped {stopped['stopped']}; keepalive resumed"
        else:
            result["note"] = f"stopped {stopped['stopped']}; keepalive was not running before, left stopped"
        return result


async def shutdown() -> None:
    """Dashboard exit: stop a background continuous schedule so it is never orphaned."""
    async with _lock:
        stopped = await _stop_continuous()
        if stopped and stopped["resume_keepalive"]:
            await _resume_keepalive()
