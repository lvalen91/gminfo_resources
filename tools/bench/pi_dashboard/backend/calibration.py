"""Calibration + APK operations.

- APK install over a chosen adb transport.
- Offline caltool validation (ingest / pack --template) as the dry-run for a write.
- The DPS Type4 custom-calibration WRITE workflow, exposed as a documented, ordered
  step list the UI/LLM can see and (behind explicit confirm) drive. The backend never
  fires the live write itself; the "validate" path uses caltool offline only.
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


# --- caltool offline validation (the write dry-run) -----------------------------
async def caltool_ingest(path: Path) -> dict:
    """Parse a container/.calovride to JSON and report its payload digest_ok."""
    cli = str(config.CALTOOL_DIR / "cli.py")
    rc, out, err = await _run(config.BENCH_PYTHON, cli, "ingest", str(path),
                              timeout=60, cwd=str(config.CALTOOL_DIR))
    import json
    parsed = None
    try:
        parsed = json.loads(out)
    except ValueError:
        pass
    return {"exit_code": rc, "stderr": err.strip(),
            "meta": (parsed or {}).get("meta"),
            "entry_count": (parsed or {}).get("entry_count"),
            "digest_ok": (parsed or {}).get("meta", {}).get("digest_ok") if parsed else None}


async def caltool_pack_validate(entries_json: Path, template: Path, out_path: Path) -> dict:
    """Reseal entries under a genuine template header; caltool recomputes + verifies the
    payload digest. The RSA signature stays STALE (by design) - hardware acceptance still
    needs the live CAN613/614 VIP-RAM step, which this does NOT perform."""
    cli = str(config.CALTOOL_DIR / "cli.py")
    rc, out, err = await _run(config.BENCH_PYTHON, cli, "pack", str(entries_json),
                              "-o", str(out_path), "--template", str(template),
                              timeout=60, cwd=str(config.CALTOOL_DIR))
    text = out + err
    return {"exit_code": rc, "output": text.strip(),
            "digest_ok": "digest OK" in text,
            "signature_stale": True,
            "note": "Payload digest validated offline. RSA signature is stale; real-hardware "
                    "acceptance requires the live CAN613/614 VIP-RAM bypass (not performed)."}


# --- CAN613/614 VIP-RAM step (auto-run inside the calibration write + its test) --
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


def cal_write_execute(container_path: Path, slot: int, transfer) -> dict:
    """LIVE calibration write (destructive, confirm-gated by the caller). Runs the exact
    documented order: 613/614 connect -> save verifier words -> override with markers ->
    `transfer()` (the UDS RequestDownload/TransferData/TransferExit) -> RESTORE the words
    in a finally so a failed/err'd write never leaves them overridden -> disconnect.

    `transfer(dev_log)` is supplied by the caller (it performs the UDS programming prep +
    34/36/37 over diagnosticsd) and returns its own structured result. (Blocking.)"""
    can0_dev = _dev()
    dev = can0_dev.VipDevInterface()
    result = {"mode": "execute", "slot": f"{slot:02X}", "container": container_path.name,
              "overridden": False, "restored": False}
    saved = {}
    try:
        with dev:
            saved = can0_dev.connect_and_save(dev)             # connect + save
            result["saved_words"] = {f"{a:08X}": w.hex() for a, w in saved.items()}
            try:
                for addr in can0_dev.VERIFIER_WORDS:            # override with markers
                    dev.write_verify(addr, can0_dev.MARKER_VALUES[addr])
                result["overridden"] = True
                result["transfer"] = transfer(dev.log)          # UDS write
            finally:
                # GUARANTEED restore, even if the transfer raised.
                for addr, original in saved.items():
                    dev.write_verify(addr, original)
                result["restored"] = True
                dev.disconnect()
        result["ok"] = result.get("transfer", {}).get("ok", False)
        result["log"] = dev.log
        return result
    except Exception as e:  # noqa: BLE001
        result["ok"] = False
        result["error"] = f"{type(e).__name__}: {e}"
        result["log"] = dev.log
        return result


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
