"""ELK recovery backend: CAN-driven entry (can0_elk.py) + volatile RAM image boot
(elk_raw_boot.py). Grounded in platform/elk_recovery.md and the boot-chain analysis.

Safety facts baked into the UI/notes here:
- A volatile ELK RAM boot (download+boot) is NON-persistent and cannot burn a fuse.
- The irreversible brick risk is flash/erase/SPI-capsule writes - NOT exposed here at all.
- The CAN F000/8180 entry trigger is a CANDIDATE (bench-confirmed entry is MEI/HECI).
- An unsigned/wrong custom image may still be rejected by ELK/AVB at boot.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from . import config

ELK_CAN = str(config.BENCH_CAN_DIR / "can0_elk.py")
ELK_RAW = str(config.BENCH_CAN_DIR / "elk_raw_boot.py")

# Known-good reference SHA-256s (research/boot-update-recovery), shown as guidance.
KNOWN_GOOD = {
    "probe_ram_image": "773ae54ca352c7236ada4f543f475084b576053020c8128a185c48cd9898fc56",
    "ghs_slot": "13e168dd9ff073f2c40ef1fb42ed44627474554dbf9d4a2f23879a8c77f525a0",
    "boot_a": "610ffec9c52ca0658d4c13663015e3496854d66c9be380b6161b563b765dbaf3",
}


async def _run(python: str, script: str, *args: str, timeout: float = 90.0) -> dict:
    proc = await asyncio.create_subprocess_exec(
        python, script, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        with contextlib.suppress(Exception):
            await proc.wait()
        return {"exit_code": 124, "error": "timeout"}
    text = out.decode(errors="replace").strip()
    res = {"exit_code": proc.returncode, "stderr": err.decode(errors="replace").strip()[-1500:]}
    for line in reversed(text.splitlines()):
        try:
            res["result"] = json.loads(line)
            break
        except ValueError:
            continue
    if "result" not in res:
        res["stdout"] = text[-1500:]
    return res


async def probe_elk() -> dict:
    return await _run(config.BENCH_PYTHON, ELK_CAN, "--probe", timeout=30)


async def check_transport() -> dict:
    return await _run(config.BENCH_PYTHON, ELK_CAN, "--check", timeout=40)


async def enter_elk() -> dict:
    return await _run(config.BENCH_PYTHON, ELK_CAN, "--enter", timeout=120)


async def fastboot_probe() -> dict:
    """ELK fastboot getvar version-bootloader + max-download-size (non-destructive)."""
    return await _run(config.BENCH_PYTHON, ELK_RAW, "--probe", timeout=30)


async def image_validate(img: Path) -> dict:
    """Hash + size validation only; does NOT open USB or boot (elk_raw_boot --dry-run)."""
    return await _run(config.BENCH_PYTHON, ELK_RAW, "--dry-run", str(img), timeout=60)


async def image_boot(img: Path) -> dict:
    """VOLATILE RAM download + boot of an image via ELK (non-persistent, no flash).
    DESTRUCTIVE-tier because an arbitrary image boot is a real risk; token-gated upstream."""
    return await _run(config.BENCH_PYTHON, ELK_RAW, str(img), timeout=180)
