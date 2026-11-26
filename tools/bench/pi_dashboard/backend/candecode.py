"""Read-only CAN signal decoder: runs frames from the passive can0 observer through a
vendored opendbc CANParser against a hand-written, bench-verified stub DBC and keeps a
live snapshot of the decoded named signals for the dashboard to poll.

STRICTLY READ-ONLY / ADDITIVE. This module never opens its own CAN socket and never
transmits: it attaches to canbus.CanObserver's existing subscriber fan-out (the same
queue the /ws/can live view uses) and only ever reads. It touches nothing on the TX path
(sequences.py / the observer's own socket) -- feeding a second consumer off the observer
is exactly what its subscribe()/unsubscribe() fan-out was built for.

ZERO-GUESSING: every signal in gm_bench.dbc traces to a BENCH-VERIFIED row in
platform/can_network.md (see CATALOG below for the per-signal citation). Firmware-traced-
only or unconfirmed candidates (the 0x40B/0x264 PRNDL path, the unresolved time-sync
message, the accessory/service power modes) are deliberately NOT in the DBC: an
unverified layout would decode plausible-looking garbage, which is worse than nothing.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from .vendor.opendbc_can import CANParser, CANDefine, DBC

DBC_PATH = str(Path(__file__).with_name("gm_bench.dbc"))

# Per-signal provenance shown in the UI / API so a human or an LLM can see the exact
# evidence behind each decoded value and never mistake a stub for a guess. Keyed by
# (address, signal). "verified" quotes the platform/can_network.md BENCH-VERIFIED table.
CATALOG: dict[int, dict] = {
    0x284: {
        "name": "GM_SysPowerModeAuth", "dlc": 6,
        "note": "Authenticated system power mode (tester -> radio). VHAL signal 58A "
                "SPMP_SysPwrModeAuth. Appears on the bus when a power-mode frame is sent "
                "(e.g. the Power mode control above / an OTA sequence).",
        "signals": {
            "SysPwrModeAuth": "b4 bits3-5. BENCH-VERIFIED: raw 2 (00 00 00 00 10 00) drove "
                              "AAOS IGNITION_STATE->4/RUN and SystemPowerMode OFF->RUN; raw 0 "
                              "(all-zero) = Off, UART-confirmed PowerModeOff. "
                              "(can_network.md:65,498; ota_update_stack.md 2026-11-17). Only "
                              "raw 0 and 2 are confirmed; 1 and 4 are shown as their number.",
            "SysPwrModeValidity": "b4 bit2, documented validity bit (clear in both verified "
                                  "frames). Shown raw; its polarity semantics are not asserted.",
        },
    },
    0x529: {
        "name": "GM_PowerModeKeepalive", "dlc": 6,
        "note": "The 0x529 keepalive frame -- transmitted continuously on this bench, so "
                "these signals update live whenever the keepalive/radio is running.",
        "signals": {
            "PowerModeSelector": "b1 bit7. BENCH-VERIFIED: 1->PowerModeOn/internal mode 2, "
                                 "0->Off/internal mode 0 (can_network.md:66,490).",
            "IpcHmiReady": "b1 bit1, BENCH-VERIFIED field (can_network.md:490). Shown raw.",
            "AnimationStatus": "b0 bits5-7, BENCH-VERIFIED field (can_network.md:490). Shown raw.",
        },
    },
    0x4DA: {
        "name": "GM_DoorAndTop", "dlc": 8,
        "note": "Door / folding-top status input (tester -> radio).",
        "signals": {
            "DriverDoorOpen": "b7 bit0. BENCH-VERIFIED: 1=open, 0=closed; live open/close "
                              "drove RH850 DriverDoorOpen/Closed events (can_network.md:72,491).",
            "FoldingTopState": "b6 bits3-5, BENCH-VERIFIED field (can_network.md:491). Shown raw.",
        },
    },
    0x53B: {
        "name": "GM_InfotainmentActivation", "dlc": 8,
        "note": "Infotainment activation request (tester -> radio).",
        "signals": {
            "InfotainmentActivationReq": "b7 bit3, BENCH-VERIFIED (can_network.md:492). Shown raw.",
        },
    },
    0x4BE: {
        "name": "GM_KeyAndValet", "dlc": 8,
        "note": "Key/ID device presence and valet-mode response.",
        "signals": {
            "KeyDevicePresent": "b7 bit3, BENCH-VERIFIED (can_network.md:493). Shown raw.",
            "ValetModeResponse": "b6 bits6-7, BENCH-VERIFIED (can_network.md:493). Shown raw.",
        },
    },
    0x526: {
        "name": "GM_AudioInputs", "dlc": 8,
        "note": "Mute-hold reset and volume up/down inputs (tester -> radio).",
        "signals": {
            "MuteHoldReset": "b5 bit7, BENCH-VERIFIED (can_network.md:73,497). Shown raw.",
            "VolumeDown": "b5 bit3, BENCH-VERIFIED (can_network.md:497). Shown raw.",
            "VolumeUp": "b5 bit2, BENCH-VERIFIED (can_network.md:497). Shown raw.",
        },
    },
    0x20D: {
        "name": "GM_RemoteProgramming", "dlc": 6,
        "note": "Remote-programming-active authenticated input (the T1 programming-session "
                "precondition).",
        "signals": {
            "RemoteProgrammingActive": "b5 bit7, BENCH-VERIFIED (can_network.md:64,499). Shown raw.",
        },
    },
}


class CanDecoder:
    """Consumes the passive observer's frame fan-out and keeps the latest decoded signal
    values. Poll snapshot() for the current view (the UI refreshes it like any other
    live stat). Never transmits; never opens a socket."""

    def __init__(self, observer, dbc_path: str = DBC_PATH):
        self.observer = observer
        self.dbc_path = dbc_path
        self._dbc = DBC(dbc_path)
        self._defines = CANDefine(dbc_path)
        # bus 0 matches the (addr, data, src=0) tuples we feed below. CANParser(dbc_path)
        # resolves to the same @cache'd DBC instance as DBC(dbc_path) above.
        self._parser = CANParser(dbc_path,
                                 [(m.name, 0) for m in self._dbc.addr_to_msg.values()], 0)
        self._task: asyncio.Task | None = None
        self._q: asyncio.Queue | None = None
        # per-address runtime bookkeeping the parser does not keep for us
        self._seen: dict[int, dict] = {}   # addr -> {last_nanos, count, raw_hex, dlc}
        self.frames_decoded = 0

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._q = self.observer.subscribe()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._q is not None:
            self.observer.unsubscribe(self._q)
            self._q = None

    async def _run(self) -> None:
        assert self._q is not None
        known = set(self._dbc.addr_to_msg)
        while True:
            msg = await self._q.get()
            try:
                f = json.loads(msg)
                addr = int(f["id"], 16)
                if addr not in known or f.get("ext") or f.get("rtr"):
                    continue
                dat = bytes.fromhex(f["data"])
                nanos = int(float(f["t"]) * 1e9)
            except (ValueError, KeyError, TypeError):
                continue
            self._parser.update([(nanos, [(addr, dat, 0)])])
            rec = self._seen.setdefault(addr, {"count": 0})
            rec["count"] += 1
            rec["last_nanos"] = nanos
            rec["raw_hex"] = dat.hex()
            rec["dlc"] = f.get("dlc", len(dat))
            self.frames_decoded += 1

    def snapshot(self) -> dict:
        # The observer stamps frames with time.monotonic() (see canbus.py), so age must be
        # measured against the same clock -- not time.time(), whose epoch differs.
        now_ns = time.monotonic() * 1e9
        messages = []
        for addr, msg in sorted(self._dbc.addr_to_msg.items()):
            cat = CATALOG.get(addr, {})
            rec = self._seen.get(addr)
            vl = self._parser.vl.get(addr, {})
            defs = self._defines.dv.get(addr, {})
            sigs = []
            for sname in msg.sigs:
                raw = vl.get(sname, 0.0)
                raw_i = int(raw)
                label = defs.get(sname, {}).get(raw_i)
                sigs.append({
                    "name": sname,
                    "raw": raw_i,
                    "value": label if label is not None else raw_i,
                    "has_enum": sname in defs,
                    "note": cat.get("signals", {}).get(sname, ""),
                })
            messages.append({
                "id": f"{addr:03X}",
                "name": msg.name,
                "dlc": cat.get("dlc", msg.size),
                "note": cat.get("note", ""),
                "seen": rec is not None,
                "count": rec["count"] if rec else 0,
                "age_s": round((now_ns - rec["last_nanos"]) / 1e9, 2) if rec else None,
                "raw_hex": rec["raw_hex"] if rec else None,
                "signals": sigs,
            })
        return {
            "dbc": Path(self.dbc_path).name,
            "frames_decoded": self.frames_decoded,
            "message_count": len(messages),
            "messages": messages,
        }
