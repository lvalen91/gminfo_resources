"""adb transport control, T1/VLAN status, and the aggregate /api/status snapshot."""
from __future__ import annotations

import asyncio
import contextlib
import re

from . import config


async def _run(*args: str, timeout: float = 8.0) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # The process may have already exited in the race between the timeout firing and
        # this kill; proc.kill() then raises ProcessLookupError (uvloop surfaces it), which
        # would otherwise bubble out of /api/status and 500 the whole polled dashboard.
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        with contextlib.suppress(Exception):
            await proc.wait()
        return 124, "", "timeout"
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


async def adb_devices() -> list[dict]:
    """Parse `adb devices -l` into structured transports, tagging USB vs T1."""
    rc, out, _ = await _run(config.ADB, "devices", "-l")
    devices = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        serial, state = parts[0], parts[1] if len(parts) > 1 else "?"
        info = {"serial": serial, "state": state}
        for tok in parts[2:]:
            if ":" in tok:
                k, v = tok.split(":", 1)
                info[k] = v
        info["transport"] = "t1-vlan5" if serial == config.T1_ADB_ENDPOINT else (
            "network" if re.match(r"\d+\.\d+\.\d+\.\d+:", serial) else "usb")
        devices.append(info)
    return devices


async def adb_connect_t1() -> dict:
    rc, out, err = await _run(config.ADB, "connect", config.T1_ADB_ENDPOINT)
    return {"exit_code": rc, "output": (out + err).strip()}


async def iface_up(iface: str) -> tuple[bool, str | None]:
    rc, out, _ = await _run("ip", "-br", "addr", "show", iface, timeout=4)
    if rc != 0:
        return False, None
    # `ip -br addr` line: "<iface> <OPERSTATE> <addr>...": test the operstate token exactly,
    # not a substring of the whole line.
    parts = out.split()
    up = len(parts) > 1 and parts[1] == "UP"
    m = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", out)
    return up, (m.group(1) if m else None)


async def ping(host: str) -> bool:
    rc, _, _ = await _run("ping", "-c", "1", "-W", "1", host, timeout=4)
    return rc == 0


async def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        return True
    except (OSError, asyncio.TimeoutError):
        return False


async def t1_status() -> dict:
    v5_up, v5_addr = await iface_up(config.VLAN5_IFACE)
    v4_up, v4_addr = await iface_up(config.VLAN4_IFACE)
    radio_ping, diag_tcp, adb_devs = await asyncio.gather(
        ping(config.T1_RADIO_IP),
        tcp_open(config.DIAG_HOST, config.DIAG_PORT),
        adb_devices(),
    )
    adb_t1 = any(d["serial"] == config.T1_ADB_ENDPOINT and d["state"] == "device" for d in adb_devs)
    # three-way state: ok = iface up and peer answering; zero = up but peer silent; error = iface down
    v5_state = "error" if not v5_up else ("ok" if radio_ping else "zero")
    v4_state = "error" if not v4_up else ("ok" if diag_tcp else "zero")
    return {
        "vlan5": {"iface": config.VLAN5_IFACE, "up": v5_up, "addr": v5_addr, "state": v5_state,
                  "radio_ip": config.T1_RADIO_IP, "radio_ping": radio_ping, "adb_connected": adb_t1},
        "vlan4": {"iface": config.VLAN4_IFACE, "up": v4_up, "addr": v4_addr, "state": v4_state,
                  "diag_endpoint": f"{config.DIAG_HOST}:{config.DIAG_PORT}", "diag_tcp_open": diag_tcp},
    }


async def can_link_status() -> dict:
    import json
    rc, out, _ = await _run("ip", "-details", "-json", "link", "show", "dev", config.CAN_IFACE, timeout=4)
    if rc != 0:
        return {"iface": config.CAN_IFACE, "present": False}
    try:
        (link,) = json.loads(out)
    except (ValueError, IndexError):
        return {"iface": config.CAN_IFACE, "present": False}
    info = link.get("linkinfo", {}).get("info_data", {})
    bt = info.get("bittiming", {})
    rc2, actout, _ = await _run("systemctl", "is-active", config.KEEPALIVE_UNIT, timeout=4)
    return {
        "iface": config.CAN_IFACE, "present": True,
        "up": "UP" in link.get("flags", []),
        "state": info.get("state"), "bitrate": bt.get("bitrate"),
        "sample_point": bt.get("sample-point"),
        "keepalive_active": actout.strip() == "active",
    }
