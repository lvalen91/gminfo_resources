"""Calibration + APK operations.

- APK install over a chosen adb transport.
- The 0x613/0x614 VIP dev-link health check (cal_write_test) -- non-destructive.
- The live calibration write + F182 verify (run_can0_cal), delegated to the single proven
  implementation, tools/bench/bench_can/calibration_write_can0.py. A genuine (hash-matched
  stock) package writes with the ordinary genuine path; a modified package (any member that
  does not hash-match its stock reference) writes with the 0x613/0x614 VIP override path
  (genuine=False). The upload's own bytes decide which -- there is no user-facing toggle.
- The DPS Type4 custom-calibration workflow as a documented step list (reference only).
"""
from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path

from . import config

# Make caltool and the bench_can modules importable (both stdlib-only in the repo).
for _p in (str(config.CALTOOL_DIR), str(config.BENCH_CAN_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


async def _run(*args: str, timeout: float = 120.0, cwd: str | None = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # Guard the kill: the process may already be gone (ProcessLookupError) and that
        # must not escape as a 500. Reap it so no zombie/transport warning lingers.
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        with contextlib.suppress(Exception):
            await proc.wait()
        return 124, "", "timeout"
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


# --- APK install ----------------------------------------------------------------
async def adb_install(serial: str, apk_path: Path, reinstall: bool = True) -> dict:
    args = [config.ADB, "-s", serial, "install"]
    if reinstall:
        args.append("-r")
    args.append(str(apk_path))
    rc, out, err = await _run(*args, timeout=300)
    return {"serial": serial, "apk": apk_path.name, "exit_code": rc,
            "stdout": out.strip(), "stderr": err.strip(),
            "success": rc == 0 and "Success" in (out + err)}


# --- CAN613/614 VIP dev-link TEST (read-only; never part of a genuine write) ------
def _dev():
    import can0_dev
    return can0_dev


def cal_write_test() -> dict:
    """TEST / dry-run for a calibration write: connect the 613/614 VIP dev interface and
    save + verify-readback the two verifier words. Does NOT override, write, or restore -
    validates the live 613/614 link without touching calibration data. (Blocking.)"""
    can0_dev = _dev()
    dev = can0_dev.VipDevInterface()
    steps, saved = [], {}
    try:
        with dev:
            saved = can0_dev.connect_and_save(dev)
            # verify the link is stable by reading each word again
            for addr, w in list(saved.items()):
                again = dev.read_word(addr)
                steps.append({"addr": f"{addr:08X}", "value": w.hex(),
                              "readback_stable": again == w})
            dev.disconnect()
        ok = all(s["readback_stable"] for s in steps)
        return {"ok": ok, "mode": "test", "log": dev.log, "words": steps,
                "note": "613/614 link validated; no override/write/restore performed"}
    except Exception as e:  # noqa: BLE001 - surface any CAN/link error verbatim
        return {"ok": False, "mode": "test", "log": dev.log,
                "error": f"{type(e).__name__}: {e}",
                "note": "613/614 link unavailable (bus/VIP asleep, or radio power-cycling)"}


# --- LIVE calibration write: ONE implementation, shared with the CLI ---------------
# The write and its F182 verify are NOT implemented here. They run the live-verified
# tools/bench/bench_can/calibration_write_can0.py (SocketCAN port of calibration_write_
# can5.py's CalDiagnostics / write_package / verify_package), so the dashboard and the
# bench CLI can never drift apart again. That script:
#   * opens the UDS programming session ONCE (10 01/10 03/27/FF01/021E/85 02/28 03 01/
#     10 02), transfers every slot inside it, and closes it ONCE;
#   * uses TransferData blocks of 0x0FFF - 2 = 4093 bytes (the ECU's 0x0FFF includes the
#     0x36 SID + block counter) on the decompressed CSM container;
#   * never touches CAN 0x613/0x614 for genuine/stock containers (only --modified does,
#     which the dashboard never passes: every container it can plan is digest-matched to
#     the stock reference set);
#   * owns the can0 bus for the duration: stops pibench-can-keepalive, replays the
#     profile minus native 0x20D plus the 0x284/0x20D precondition stream, and restarts
#     the keepalive in a finally.
# It runs as a SUBPROCESS (not in-process): its replay/injector/RX threads then never
# share the uvicorn process's GIL or event loop, and a hang can be interrupted cleanly.
CAL_WRITE_SCRIPT = config.BENCH_CAN_DIR / "calibration_write_can0.py"
CAL_WRITE_TIMEOUT_S = 300.0   # proven package write is ~15-20 s of UDS + bus setup
CAL_VERIFY_TIMEOUT_S = 120.0


async def run_can0_cal(mode: str, package_dir: Path, slots: list[str] | None = None,
                       timeout: float = CAL_WRITE_TIMEOUT_S, genuine: bool = True) -> dict:
    """Run calibration_write_can0.py `mode` ("package" = write, "verify" = F182 readback)
    against `package_dir` (part-number-named containers), optionally restricted to `slots`
    (hex, e.g. ["02","0A"]). Non-blocking for the event loop.

    `genuine` selects the write path for mode="package": True (default) is the ordinary
    stock path (no 0x613/0x614, 4093-byte blocks); False passes --modified to the script,
    which first sets the header-verifier words over the 0x613/0x614 VIP dev interface and
    writes 1022-byte blocks. The caller decides this from the upload's own bytes (stock
    hash-match => genuine), never from a UI toggle. Ignored for mode="verify".

    The caller must hold the dashboard's CAN bus lock (sequences.exclusive_bus) so no
    dashboard sequence competes for the can0 schedule lock."""
    import json
    import os
    import signal
    import tempfile
    import time as _time

    if mode not in ("package", "verify"):
        raise ValueError(f"unsupported calibration mode {mode!r}")
    fd, out_name = tempfile.mkstemp(prefix=f"calwrite_{mode}_", suffix=".json")
    os.close(fd)
    out_path = Path(out_name)
    args = [config.BENCH_PYTHON, str(CAL_WRITE_SCRIPT), mode,
            "--package-dir", str(package_dir), "--profile", str(config.HARNESS_PROFILE),
            "--json-out", str(out_path)]
    if slots:
        args += ["--only", ",".join(s.upper() for s in slots)]
    if mode == "package" and not genuine:
        # Modified/custom container: route through the 0x613/0x614 VIP override path.
        args.append("--modified")
    # A dashboard restart must never kill a write mid-package (observed: SIGTERM 39 s in,
    # no finally -> session not closed, keepalive not restarted). So the script runs in
    # its own transient systemd scope, outside pibench-dashboard's cgroup (a unit stop
    # cannot reach it), under `trap '' TERM` (sudo relays a TERM it receives; an ignored
    # disposition survives exec). Output goes to a persistent log, not a pipe, so it
    # survives the dashboard too. The timeout path uses SIGINT, which unwinds the
    # script's finally blocks (session close, keepalive restart).
    log_dir = config.UPLOAD_DIR.parent / "cal_write_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = _time.strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"{stamp}_{mode}.log"
    inner = "trap '' TERM; exec \"$@\""
    wrapped = ["sudo", "-n", "systemd-run", "--scope", "--quiet", "--collect",
               f"--unit=pibench-calwrite-{mode}-{stamp}", f"--uid={os.getuid()}",
               f"--gid={os.getgid()}", "--", "/bin/sh", "-c", inner, "calwrite", *args]
    started = _time.monotonic()
    with open(log_path, "wb") as log_fh:
        proc = await asyncio.create_subprocess_exec(
            *wrapped, stdin=asyncio.subprocess.DEVNULL, stdout=log_fh,
            stderr=asyncio.subprocess.STDOUT, cwd=str(config.BENCH_CAN_DIR))
    timed_out = False
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        with contextlib.suppress(ProcessLookupError):
            proc.send_signal(signal.SIGINT)   # sudo relays it to the script
        try:
            await asyncio.wait_for(proc.wait(), timeout=20)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
    elapsed = round(_time.monotonic() - started, 1)
    try:
        out = log_path.read_bytes()
    except OSError:
        out = b""
    result = None
    try:
        text = out_path.read_text()
        result = json.loads(text) if text.strip() else None
    except (OSError, ValueError):
        result = None
    finally:
        with contextlib.suppress(OSError):
            out_path.unlink()
    output = out.decode(errors="replace") if out else ""
    ok = (not timed_out) and proc.returncode == 0 and bool(result and result.get("ok"))
    r = {"mode": mode, "ok": ok, "exit_code": proc.returncode, "elapsed_s": elapsed,
         "package_dir": str(package_dir), "slots": slots, "result": result,
         "write_path": ("genuine" if genuine else "modified (0x613/0x614 override)") if mode == "package" else None,
         "log": str(log_path), "output_tail": output[-4000:]}
    if timed_out:
        r["error"] = f"calibration_write_can0.py {mode} exceeded {timeout:.0f} s and was interrupted"
    elif not ok:
        r["error"] = (result or {}).get("error") or f"calibration_write_can0.py {mode} exited {proc.returncode}"
    return r


# --- DPS Type4 write workflow descriptor (doc-grounded, never auto-fired) --------
# research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md:209-262.
DPS_WRITE_WORKFLOW = {
    "name": "DPS Type4 custom-calibration write (CAN613/614 VIP-RAM bypass)",
    "destructive": True,
    "reversible": "overwrites a calibration slot; keep the pinned stock container as recovery payload",
    "offline_validation": "caltool ingest (digest_ok) + caltool pack --template (digest OK)",
    "steps": [
        {"n": 1, "phase": "prepare-offline",
         "detail": "Edit only the inner CalOvride XML; recompute payload digest "
                   "SHA-256(container[858:end]) at container[0x1e:0x1e+32]. RSA header "
                   "signature [600:856] + signer record [62:344] left byte-identical (stale)."},
        {"n": 2, "phase": "session", "uds": "10 03",
         "detail": "Enter extended session -> 50 03 00 64 01 F2."},
        {"n": 3, "phase": "security", "uds": "27 01 / 27 02 + 12x00",
         "detail": "SecurityAccess profile 01: all-FF seed -> 12 zero-byte key -> 67 02 "
                   "(SBI-bypass state only)."},
        {"n": 4, "phase": "prog-prep", "uds": "31 01 FF 01 ; 31 01 02 1E ; 10 02",
         "detail": "FF01 precheck, 021E VIP pass-through, DTC logging off, normal comm off, "
                   "then programming session 10 02."},
        {"n": 5, "phase": "vip-ram-bypass", "bus": "CAN 0x613->0x614 (XCP-style, no SecurityAccess)",
         "detail": "CONNECT FF 0C.. ; save words at FEBF0BF8/FEBF0BFC (read, were 0); "
                   "write FEBF0BF8=A5163829, FEBF0BFC=5AE9C7D6 (validated-SBA-ticket markers); "
                   "verify by readback. Commands: F6 SET_MTA, F5 UPLOAD, F0 DOWNLOAD."},
        {"n": 6, "phase": "transfer", "uds": "34 .. / 36 NN.. / 37",
         "detail": "RequestDownload (74 20 0F FF max block 0x0FFF), TransferData blocks "
                   "36 01/02.., RequestTransferExit 37."},
        {"n": 7, "phase": "restore", "bus": "CAN 0x613->0x614",
         "detail": "Restore FEBF0BF8/FEBF0BFC to 0 via the dev-memory route; verify; disconnect."},
        {"n": 8, "phase": "verify", "uds": "22 F0 F1",
         "detail": "Read PEC -> 62 F0 F1 00 00 (0000=accepted; 0015=rejected). F182 identity unchanged."},
    ],
    "caveats": [
        "A clean 76/76/77 + PEC 0000 proves the transfer was accepted, NOT that the change works.",
        "Without step 5 markers the write is rejected at 36 01 with 7F 36 72 and PEC 0015.",
        "Post-write cleanup (re-enable comm/DTC) is flaky in every logged trial; treat as best-effort.",
    ],
}
