"""The Raspberry Pi host itself (the "Pi" tab): resource stats, bench-service restarts,
reboot, and Wi-Fi via NetworkManager. Distinct from the vehicle/VIP/radio hardware the
other tabs drive.

Every state-changing action here is a Tier-2 plan->execute action (see app.py); this
module only builds and runs the commands. All privileged commands use `sudo -n` (the
service runs as zeno; the Pi's sudoers grants zeno NOPASSWD), so a missing grant fails
fast with an error instead of hanging on a password prompt.

Self-disruptive actions (restarting this dashboard, restarting nginx which proxies this
very response, rebooting the Pi) are handed to systemd as a short transient timer
(`systemd-run --on-active=Ns`): the HTTP response is sent first, and the action does not
depend on this process surviving to carry it out.

Wi-Fi passwords: a password is accepted only on the Wi-Fi execute call and goes straight
to NetworkManager over the stdin of `nmcli connection edit` -- never on a command line
(argv is world-readable in /proc and sudo logs the full command line to the journal),
never logged, never written to a file here, never in a response. NetworkManager stores
it in its own root-only profile (/etc/NetworkManager/system-connections/). The editor
echoes its stdin to stdout when stdin is not a tty, so that stdout is only searched for
the success marker and then dropped; stderr is redacted before it is used.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
import socket
import time
from pathlib import Path

from . import config, sequences

STARTED = time.time()          # this dashboard process's start (wall clock)
SYSTEMCTL = shutil.which("systemctl") or "/usr/bin/systemctl"
REBOOT_ARGV = [SYSTEMCTL, "reboot"]
SELF_DELAY_S = 2               # dashboard / nginx self-restart delay
REBOOT_DELAY_S = 3
NM_WAIT_S = 45                 # nmcli --wait for an activation
DISK_MOUNTS = ["/", "/boot/firmware", str(config.UPLOAD_DIR.parent)]


async def _run(args: list[str], timeout: float = 10.0, stdin: bytes | None = None,
               keep_stdout: bool = True) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE if keep_stdout else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(stdin), timeout=timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()
        return 124, "", f"timed out after {timeout:.0f}s"
    return (proc.returncode, (out or b"").decode(errors="replace"),
            (err or b"").decode(errors="replace"))


def _last_line(text: str) -> str:
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _terse(line: str) -> list[str]:
    """Split one `nmcli -t` line on unescaped ':' (nmcli escapes ':' and '\\' in values)."""
    fields, cur, i = [], [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            cur.append(line[i + 1]); i += 2; continue
        if c == ":":
            fields.append("".join(cur)); cur = []
        else:
            cur.append(c)
        i += 1
    fields.append("".join(cur))
    return fields


# ============================ resource stats ====================================
_cpu_prev: tuple[float, int, int] | None = None   # (monotonic, total, idle)


def _cpu_sample() -> tuple[int, int]:
    with open("/proc/stat") as f:
        vals = [int(x) for x in f.readline().split()[1:9]]
    return sum(vals), vals[3] + vals[4]          # total, idle+iowait


async def _cpu_percent() -> float | None:
    global _cpu_prev
    try:
        now = time.monotonic()
        if _cpu_prev is None or now - _cpu_prev[0] > 30:
            t0, i0 = _cpu_sample()
            await asyncio.sleep(0.25)
            now = time.monotonic()
        else:
            _, t0, i0 = _cpu_prev
        t1, i1 = _cpu_sample()
        _cpu_prev = (now, t1, i1)
        dt = t1 - t0
        return round(100.0 * (1 - (i1 - i0) / dt), 1) if dt > 0 else None
    except (OSError, ValueError, IndexError):
        return None


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip("\0\n ")
    except OSError:
        return None


def _meminfo() -> dict:
    m = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            m[k] = int(v.split()[0]) * 1024
    except (OSError, ValueError):
        return {}
    total, avail = m.get("MemTotal", 0), m.get("MemAvailable", 0)
    st, sf = m.get("SwapTotal", 0), m.get("SwapFree", 0)
    return {"total": total, "available": avail, "used": total - avail,
            "percent": round(100.0 * (total - avail) / total, 1) if total else None,
            "swap_total": st, "swap_used": st - sf}


def _disks() -> list[dict]:
    out, seen = [], set()
    for mount in DISK_MOUNTS:
        try:
            st = os.stat(mount)
            if st.st_dev in seen:
                continue
            seen.add(st.st_dev)
            v = os.statvfs(mount)
        except OSError:
            continue
        total = v.f_blocks * v.f_frsize
        used = (v.f_blocks - v.f_bfree) * v.f_frsize
        free = v.f_bavail * v.f_frsize
        out.append({"mount": mount, "total": total, "used": used, "free": free,
                    "percent": round(100.0 * used / (used + free), 1) if used + free else None})
    return out


async def _nm_devices() -> dict[str, dict]:
    rc, out, _ = await _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], timeout=5)
    devs = {}
    if rc == 0:
        for line in out.splitlines():
            f = _terse(line)
            if len(f) >= 4:
                devs[f[0]] = {"type": f[1], "nm_state": f[2], "connection": f[3] or None}
    return devs


async def interfaces() -> list[dict]:
    """Every interface but lo: kernel up/operstate + addresses, merged with NM's view."""
    (rc, out, _), nm = await asyncio.gather(_run(["ip", "-json", "addr", "show"], timeout=5), _nm_devices())
    try:
        links = json.loads(out) if rc == 0 else []
    except ValueError:
        links = []
    res = []
    for l in links:
        name = l.get("ifname")
        if not name or name == "lo":
            continue
        flags = l.get("flags", [])
        info = nm.get(name, {})
        addrs = l.get("addr_info", [])
        res.append({
            "name": name,
            "type": info.get("type") or l.get("link_type"),
            "admin_up": "UP" in flags,
            "carrier": "NO-CARRIER" not in flags,
            "operstate": l.get("operstate"),
            "nm_state": info.get("nm_state"),
            "connection": info.get("connection"),
            "mac": l.get("address") if l.get("link_type") == "ether" else None,
            "ipv4": [f"{a['local']}/{a['prefixlen']}" for a in addrs if a.get("family") == "inet"],
            "ipv6": [f"{a['local']}/{a['prefixlen']}" for a in addrs
                     if a.get("family") == "inet6" and a.get("scope") == "global"],
        })
    # up first, then by name
    res.sort(key=lambda i: (not i["admin_up"] or i["operstate"] == "DOWN", i["name"]))
    return res


async def unit_states(units: list[str]) -> dict[str, dict]:
    rc, out, _ = await _run([SYSTEMCTL, "show", "-p", "Id,ActiveState,SubState,"
                             "ActiveEnterTimestampMonotonic,MainPID", *units], timeout=5)
    states: dict[str, dict] = {}
    for block in out.strip().split("\n\n"):
        kv = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        if kv.get("Id"):
            states[kv["Id"]] = {"active": kv.get("ActiveState"), "sub": kv.get("SubState"),
                                "since_mono": int(kv.get("ActiveEnterTimestampMonotonic") or 0),
                                "pid": int(kv.get("MainPID") or 0)}
    return states


# ============================ restartable bench services =========================
TARGETS: dict[str, dict] = {
    "dashboard": {
        "label": "Dashboard backend", "units": [config.DASHBOARD_UNIT], "self": True,
        "desc": f"Restarts {config.DASHBOARD_UNIT} (this FastAPI backend) {SELF_DELAY_S} s after "
                "confirming, via a systemd timer so the reply gets out first. The page stays "
                "loaded and its live sections reconnect by themselves; open Pi-shell / adb-shell "
                "terminals and the UART stream drop and must be reopened. A running continuous "
                "CAN sequence is stopped and the keepalive resumed (normal backend shutdown)."},
    "uart": {
        "label": "UART bridge (ser2net)", "units": [config.SER2NET_UNIT],
        "desc": f"Restarts {config.SER2NET_UNIT} (serial ttyS0 -> loopback TCP for the UART tab). "
                "The UART stream drops for a moment and the backend reconnects on its own."},
    "nginx": {
        "label": "Web server (nginx)", "units": [config.NGINX_UNIT], "self": True,
        "desc": f"Restarts {config.NGINX_UNIT} (serves this page and proxies /api and /ws) "
                f"{SELF_DELAY_S} s after confirming, only if `nginx -t` passes. Every open "
                "WebSocket drops for a moment; the page reconnects on its own."},
    "can0": {
        "label": "CAN link (can0 + keepalive)", "units": [config.CAN0_UNIT, config.KEEPALIVE_UNIT],
        "desc": f"For a stuck can0: takes the dashboard's CAN bus lock (stops any running "
                f"continuous sequence), stops {config.KEEPALIVE_UNIT}, bounces can0 "
                f"(`can0-setup bounce`: down, re-apply the pinned 500 kbit/s timing, up), then "
                "restarts the keepalive if it was running. The radio sees a TX gap of a few "
                "seconds (it tolerates ~694 s)."},
}


async def services() -> list[dict]:
    units = [u for t in TARGETS.values() for u in t["units"]]
    st = await unit_states(units)
    return [{"target": k, "label": t["label"], "desc": t["desc"],
             "units": [{"unit": u, **st.get(u, {"active": "unknown"})} for u in t["units"]]}
            for k, t in TARGETS.items()]


async def status() -> dict:
    cpu_pct, ifs, svcs = await asyncio.gather(_cpu_percent(), interfaces(), services())
    try:
        load = list(os.getloadavg())
    except OSError:
        load = None
    temp = _read("/sys/class/thermal/thermal_zone0/temp")
    uptime = _read("/proc/uptime")
    return {
        "time": time.time(),
        "hostname": socket.gethostname(),
        "model": _read("/proc/device-tree/model"),
        "kernel": os.uname().release,
        "boot_id": _read("/proc/sys/kernel/random/boot_id"),
        "uptime_s": float(uptime.split()[0]) if uptime else None,
        "cpu": {"percent": cpu_pct, "load": load, "cores": os.cpu_count(),
                "temp_c": round(int(temp) / 1000, 1) if temp and temp.isdigit() else None},
        "memory": _meminfo(),
        "disks": _disks(),
        "interfaces": ifs,
        "services": svcs,
        "dashboard": {"pid": os.getpid(), "started": STARTED},
    }


# ============================ privileged helpers ================================
def _sched_argv(name: str, delay_s: int, argv: list[str]) -> list[str]:
    # RemainAfterElapse=no unloads the timer once it fires, so the same unit name can be
    # reused next time; while one is still pending a second schedule fails instead of
    # queueing a duplicate.
    return ["sudo", "-n", "systemd-run", "--quiet", "--collect", f"--on-active={delay_s}s",
            "--timer-property=RemainAfterElapse=no", f"--unit={name}", *argv]


async def _schedule(name: str, delay_s: int, argv: list[str]) -> dict:
    cmd = _sched_argv(name, delay_s, argv)
    rc, _, err = await _run(cmd, timeout=10)
    return {"ok": rc == 0, "exit_code": rc, "command": " ".join(argv), "delay_s": delay_s,
            "error": None if rc == 0 else (_last_line(err) or f"systemd-run exited {rc}")}


async def _sudo(args: list[str], timeout: float = 30.0) -> dict:
    rc, out, err = await _run(["sudo", "-n", *args], timeout=timeout)
    return {"command": " ".join(args), "exit_code": rc, "ok": rc == 0,
            "stderr": err.strip()[-1000:], "error": None if rc == 0 else
            (_last_line(err) or _last_line(out) or f"exit code {rc}")}


async def sudo_allows(argv: list[str]) -> bool:
    """`sudo -n -l CMD` exits 0 iff sudoers lets this user run CMD without a password.
    Lists, never runs."""
    rc, _, _ = await _run(["sudo", "-n", "-l", *argv], timeout=5)
    return rc == 0


async def nginx_config_ok() -> tuple[bool, str]:
    rc, out, err = await _run(["sudo", "-n", "nginx", "-t"], timeout=10)
    return rc == 0, _last_line(err) or _last_line(out)


# ============================ restart / reboot ==================================
async def restart(target: str) -> dict:
    spec = TARGETS[target]
    if target == "dashboard":
        r = await _schedule("pibench-dash-restart-dashboard", SELF_DELAY_S,
                            [SYSTEMCTL, "restart", config.DASHBOARD_UNIT])
        return {**r, "target": target, "status": "scheduled" if r["ok"] else "failed",
                "previous_started": STARTED,
                "summary": f"Dashboard restart scheduled in {SELF_DELAY_S} s"}
    if target == "nginx":
        ok, msg = await nginx_config_ok()
        if not ok:
            return {"ok": False, "target": target, "error": f"nginx -t failed, not restarting: {msg}"}
        r = await _schedule("pibench-dash-restart-nginx", SELF_DELAY_S,
                            [SYSTEMCTL, "restart", config.NGINX_UNIT])
        return {**r, "target": target, "status": "scheduled" if r["ok"] else "failed",
                "summary": f"nginx restart scheduled in {SELF_DELAY_S} s"}
    if target == "uart":
        r = await _sudo([SYSTEMCTL, "restart", config.SER2NET_UNIT])
        st = (await unit_states(spec["units"])).get(config.SER2NET_UNIT, {})
        ok = r["ok"] and st.get("active") == "active"
        return {"ok": ok, "target": target, "restart": r, "unit_state": st,
                "error": r["error"] or (None if ok else f"ser2net is {st.get('active')} after restart"),
                "summary": "ser2net restarted"}
    if target == "can0":
        steps: dict[str, dict] = {}
        async with sequences.exclusive_bus() as stopped:
            ka_was = await sequences.keepalive_active()
            if ka_was:
                steps["keepalive_stop"] = await _sudo([SYSTEMCTL, "stop", config.KEEPALIVE_UNIT])
            steps["can0_bounce"] = await _sudo([config.CAN0_SETUP, "bounce"])
            # Also when a continuous sequence had replaced the keepalive (it was stopped
            # by exclusive_bus and owed a keepalive resume), else the bus is left silent.
            ka_restart = ka_was or bool(stopped and stopped.get("resume_keepalive"))
            if ka_restart:
                steps["keepalive_start"] = await _sudo([SYSTEMCTL, "start", config.KEEPALIVE_UNIT])
        bad = next(((k, v) for k, v in steps.items() if not v["ok"]), None)
        return {"ok": bad is None, "target": target, "steps": steps,
                "keepalive_was_running": ka_was, "stopped_continuous": stopped,
                "error": f"{bad[0].replace('_', ' ')}: {bad[1]['error']}" if bad else None,
                "summary": "can0 bounced" + ("; keepalive restarted" if ka_restart else
                                             "; keepalive was not running, left stopped")}
    raise KeyError(target)


async def reboot() -> dict:
    r = await _schedule("pibench-dash-reboot", REBOOT_DELAY_S, REBOOT_ARGV)
    boot_id = _read("/proc/sys/kernel/random/boot_id")
    return {**r, "status": "scheduled" if r["ok"] else "failed", "previous_boot_id": boot_id,
            "summary": f"Reboot scheduled in {REBOOT_DELAY_S} s"}


# ============================ Wi-Fi (NetworkManager) =============================
class WifiInputError(ValueError):
    """A user-input problem; its message never contains the password."""


def validate_ssid(ssid: str) -> str:
    if not isinstance(ssid, str) or not ssid:
        raise WifiInputError("SSID is required")
    if len(ssid.encode()) > 32:
        raise WifiInputError("SSID is longer than 32 bytes")
    if any(ord(c) < 32 or ord(c) == 127 for c in ssid):
        raise WifiInputError("SSID contains control characters")
    return ssid


def validate_psk(pw: str) -> None:
    """WPA passphrase: 8..63 printable ASCII, or a 64-hex raw key. Newlines would inject
    nmcli editor commands; leading/trailing spaces are stripped by the editor (the stored
    key would silently differ), so both are refused. Messages never echo the value."""
    if not isinstance(pw, str):
        raise WifiInputError("password must be a string")
    if len(pw) == 64 and all(c in "0123456789abcdefABCDEF" for c in pw):
        return
    if not 8 <= len(pw) <= 63:
        raise WifiInputError("password must be 8-63 characters (or a 64-hex-digit key)")
    if any(not (32 <= ord(c) <= 126) for c in pw):
        raise WifiInputError("password must be printable ASCII (no tabs, newlines or non-ASCII)")
    if pw != pw.strip():
        raise WifiInputError("password must not start or end with a space")


def _redact(text: str, secret: str | None) -> str:
    return text.replace(secret, "********") if secret and text else text


def _security_kind(sec: str | None) -> str:
    """nmcli SECURITY column -> key-mgmt we create a profile with."""
    s = (sec or "").strip()
    if s in ("", "--"):
        return "open"
    if "802.1X" in s:
        return "enterprise"
    if "WPA3" in s and "WPA2" not in s and "WPA1" not in s:
        return "sae"
    return "wpa-psk"


async def _wifi_devices() -> list[dict]:
    return [{"device": d, **v} for d, v in (await _nm_devices()).items() if v["type"] == "wifi"]


async def _saved_wifi() -> list[dict]:
    rc, out, _ = await _run(["nmcli", "-t", "-f", "NAME,UUID,TYPE,DEVICE,AUTOCONNECT,ACTIVE",
                             "connection", "show"], timeout=5)
    saved = []
    for line in out.splitlines() if rc == 0 else []:
        f = _terse(line)
        if len(f) >= 6 and f[2] == "802-11-wireless":
            saved.append({"name": f[0], "uuid": f[1], "device": f[3] or None,
                          "autoconnect": f[4] == "yes", "active": f[5] == "yes"})

    async def detail(c):
        rc, out, _ = await _run(["nmcli", "-t", "-f", "802-11-wireless.ssid,"
                                 "802-11-wireless-security.key-mgmt", "connection", "show",
                                 "uuid", c["uuid"]], timeout=5)
        kv = {}
        for line in out.splitlines():
            k, _, v = line.partition(":")
            kv[k] = v.replace("\\:", ":").replace("\\\\", "\\")
        c["ssid"] = kv.get("802-11-wireless.ssid") or c["name"]
        km = kv.get("802-11-wireless-security.key-mgmt") or ""
        c["security"] = km or "open"
    await asyncio.gather(*(detail(c) for c in saved))
    return saved


async def _visible(device: str | None) -> list[dict]:
    args = ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list",
            "--rescan", "no"]
    if device:
        args += ["ifname", device]
    rc, out, _ = await _run(args, timeout=8)
    best: dict[str, dict] = {}
    for line in out.splitlines() if rc == 0 else []:
        f = _terse(line)
        if len(f) < 5 or not f[1]:
            continue        # hidden networks have no SSID to show
        try:
            sig = int(f[2])
        except ValueError:
            sig = 0
        e = best.get(f[1])
        in_use = f[0].strip() == "*"
        if e is None or sig > e["signal"]:
            best[f[1]] = {"ssid": f[1], "signal": sig, "security": f[3] or "open",
                          "kind": _security_kind(f[3]), "channel": f[4],
                          "in_use": in_use or bool(e and e["in_use"])}
        elif in_use:
            e["in_use"] = True
    return sorted(best.values(), key=lambda v: (not v["in_use"], -v["signal"]))


async def wifi_state() -> dict:
    devs = await _wifi_devices()
    dev = devs[0]["device"] if devs else None
    (_, radio, _), saved, visible, ifs = await asyncio.gather(
        _run(["nmcli", "radio", "wifi"], timeout=5), _saved_wifi(), _visible(dev), interfaces())
    saved_ssids = {c["ssid"] for c in saved}
    for v in visible:
        v["saved"] = v["ssid"] in saved_ssids
    by_if = {i["name"]: i for i in ifs}
    for d in devs:
        i = by_if.get(d["device"], {})
        d["ipv4"] = i.get("ipv4", [])
        d["connected"] = d["nm_state"] == "connected"
        act = next((c for c in saved if c["active"] and c["device"] == d["device"]), None)
        d["ssid"] = act["ssid"] if act else None
    return {"radio": radio.strip() or "unknown", "devices": devs, "device": dev,
            "saved": saved, "visible": visible}


async def find_saved(uuid: str | None = None, ssid: str | None = None) -> dict | None:
    for c in await _saved_wifi():
        if (uuid and c["uuid"] == uuid) or (ssid and c["ssid"] == ssid):
            return c
    return None


async def visible_entry(ssid: str, device: str | None) -> dict | None:
    return next((v for v in await _visible(device) if v["ssid"] == ssid), None)


async def _set_psk(uuid: str, password: str) -> str | None:
    """Hand the passphrase to NetworkManager over the nmcli editor's stdin. Returns an
    error string (already redacted) or None."""
    data = f"set 802-11-wireless-security.psk {password}\nsave persistent\nquit\n".encode()
    rc, out, err = await _run(["sudo", "-n", "nmcli", "connection", "edit", "uuid", uuid],
                              timeout=20, stdin=data)
    ok = rc == 0 and "successfully updated" in out and "Error" not in out
    # the editor echoes the `set` line (with the password) to stdout: drop it here
    out = ""  # noqa: F841 -- intentionally discarded, never logged or returned
    del data
    if ok:
        return None
    return _redact(_last_line(err), password) or "NetworkManager refused the password"


async def _ipv4_of(device: str) -> list[str]:
    rc, out, _ = await _run(["ip", "-json", "addr", "show", "dev", device], timeout=5)
    try:
        (l,) = json.loads(out) if rc == 0 else [{}]
    except ValueError:
        return []
    return [f"{a['local']}/{a['prefixlen']}" for a in l.get("addr_info", []) if a.get("family") == "inet"]


async def _activate(uuid: str, device: str, secret: str | None = None) -> dict:
    rc, out, err = await _run(["sudo", "-n", "nmcli", "--wait", str(NM_WAIT_S), "connection",
                               "up", "uuid", uuid, "ifname", device], timeout=NM_WAIT_S + 15)
    if rc:
        # nmcli prints "Error: ..." then a "Hint: use journalctl ..." line; keep the error
        msg = next((l.strip() for l in err.splitlines() if l.startswith("Error")), _last_line(err))
        msg = re.sub(r"^Error:\s*", "", msg)   # the UI already says "Failed: "
    else:
        msg = _last_line(out)
    return {"ok": rc == 0, "exit_code": rc, "message": _redact(msg, secret)}


async def connect(payload: dict, password: str | None) -> dict:
    """Execute a planned connect. payload is the Tier-2 plan's (server-side) payload."""
    device, ssid = payload["device"], payload["ssid"]
    created_uuid, steps = None, {}
    try:
        if payload["mode"] == "saved":
            uuid = payload["uuid"]
        else:
            uuid = payload.get("existing_uuid")
            if uuid is None:
                args = ["sudo", "-n", "nmcli", "connection", "add", "type", "wifi", "ifname", device,
                        "con-name", ssid, "ssid", ssid, "autoconnect", "yes"]
                if payload.get("hidden"):
                    args += ["802-11-wireless.hidden", "yes"]
                if payload["kind"] != "open":
                    args += ["wifi-sec.key-mgmt", payload["kind"]]
                rc, out, err = await _run(args, timeout=15)
                m = re.search(r"\(([0-9a-f-]{36})\)", out)
                if rc or not m:
                    return {"ok": False, "ssid": ssid, "device": device,
                            "error": "could not create the profile: " + (_last_line(err) or _last_line(out))}
                uuid = created_uuid = m.group(1)
                steps["profile"] = {"ok": True, "created": True}
            if password is not None:
                perr = await _set_psk(uuid, password)
                steps["password"] = {"ok": perr is None, "stored_by": "NetworkManager", "error": perr}
                if perr:
                    raise RuntimeError(perr)
        act = await _activate(uuid, device, password)
        steps["activate"] = act
        if not act["ok"]:
            raise RuntimeError(act["message"] or "activation failed")
        ips = await _ipv4_of(device)
        created_uuid = None   # success: keep the new profile
        return {"ok": True, "ssid": ssid, "device": device, "uuid": uuid, "ipv4": ips,
                "steps": steps,
                "summary": f"Connected to {ssid} on {device}" + (f" ({ips[0].split('/')[0]})" if ips else "")}
    except RuntimeError as e:
        return {"ok": False, "ssid": ssid, "device": device, "steps": steps,
                "error": _redact(str(e), password),
                "profile_removed": created_uuid is not None}
    finally:
        if created_uuid is not None:
            # a profile we created for an attempt that failed (e.g. a mistyped password)
            # is removed, so a broken saved network is never left behind
            await _run(["sudo", "-n", "nmcli", "connection", "delete", "uuid", created_uuid], timeout=15)


async def disconnect(device: str) -> dict:
    r = await _sudo(["nmcli", "device", "disconnect", device], timeout=20)
    return {**r, "device": device, "summary": f"{device} disconnected"}


async def rescan(device: str | None) -> dict:
    args = ["nmcli", "device", "wifi", "rescan"] + (["ifname", device] if device else [])
    r = await _sudo(args, timeout=20)
    if not r["ok"] and "not allowed" in (r["error"] or "").lower():
        # NM rate-limits scans; the cached list is still fresh
        r = {**r, "ok": True, "note": r["error"]}
    if r["ok"]:
        await asyncio.sleep(2.5)   # let the scan results land before the caller re-reads
    return {**r, "summary": "Scan complete"}
