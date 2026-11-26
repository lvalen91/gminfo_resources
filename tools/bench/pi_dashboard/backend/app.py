"""GM Info 3.7 bench dashboard - FastAPI backend.

LAN-only, no authentication (owner's explicit choice for this home-lab bench). Served
behind the existing nginx under /api and /ws. The REST surface is deliberately clean and
JSON-structured so it doubles as an LLM tool API; OpenAPI/Swagger is at /api/docs.

Destructive operations (ECU factory-reset routines, calibration writes) are WIRED but
never fire without an explicit confirm phrase; everything defaults to dry-run.
"""
from __future__ import annotations

import asyncio
import io
import json
import secrets
import time
import zipfile
from pathlib import Path

from fastapi import (FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import (calibration, canbus, candecode, capture, config, diagdata, elk, ltz_ref,
               pi_host, sequences, system_status, terminals, tier2, uart, vehicle_state)
from .uds import UDSClient, UDSError

app = FastAPI(title="GM Info 3.7 Bench Dashboard", version="1.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json",
              description="LAN-only diagnostic/control API for the owner's gminfo37 bench. "
                          "Reads are safe; destructive ECU/calibration actions require an explicit confirm phrase.")

CAN = canbus.CanObserver()
# Read-only signal decoder: a second consumer of CAN's existing subscriber fan-out (it
# never opens a socket and never transmits). See candecode.py.
CAN_DECODER = candecode.CanDecoder(CAN)
UART = uart.UartHub()
# Field capture (raw T1 pcap + raw CAN log + UART tap to a USB drive). Independent: its
# own dumpcap/candump processes, a read-only tap of UART's existing fan-out. capture.py.
CAPTURE = capture.CaptureManager(UART)
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def _startup():
    await CAN.start()
    await CAN_DECODER.start()


@app.on_event("shutdown")
async def _shutdown():
    await CAPTURE.shutdown()   # clean stop + unmount first; bounded, never raises
    await sequences.shutdown()
    await CAN_DECODER.stop()
    await CAN.stop()


# ============================ status / meta =====================================
@app.get("/api/status", tags=["status"])
async def api_status():
    can_s, t1, uart_probe, adb = await asyncio.gather(
        system_status.can_link_status(), system_status.t1_status(),
        UART.probe(), system_status.adb_devices())
    return {
        "time": time.time(),
        "can": {**can_s, "observer": CAN.stats()},
        "t1": t1,
        "uart": uart_probe,
        "adb": {"devices": adb, "count": len(adb)},
        "capture": CAPTURE.brief(),
    }


@app.get("/api/meta", tags=["status"])
async def api_meta():
    """Self-description for an LLM agent orienting itself to this bench."""
    return {
        "bench": "GM Info 3.7 (gminfo37) infotainment, owner's licensed research bench, LAN-only",
        "can": {"iface": config.CAN_IFACE, "transport": "SocketCAN 500kbit/s",
                "keepalive": "0x529 @ 0.320270s via systemd", "sequences": list(sequences.SEQUENCES),
                "decode": "GET /api/can/decode decodes already-flowing frames through a vendored "
                          "opendbc CANParser against backend/gm_bench.dbc (BENCH-VERIFIED signals "
                          "only); read-only, never transmits."},
        "uds": {"endpoint": f"{config.DIAG_HOST}:{config.DIAG_PORT}", "transport": "custom GM 8-byte header (not DoIP)",
                "tester": f"{config.UDS_TESTER:04X}", "ecu": f"{config.UDS_ECU:04X}", "vlan": "vlan4 via eth0.4"},
        "safety": "reads are safe/live; every destructive action (CAN sequences, UDS routines, "
                  "calibration writes, ELK enter/boot, vehicle power-mode frames) requires a "
                  "Tier-2 plan->execute single-use token",
        "vehicle_state": {
            "power_modes": "GET /api/vehicle/power-modes lists Off/Run/Accessory/Service; "
                           "only Off and Run have a verified CAN 0x284 frame and can be "
                           "planned/executed (Tier-2). Accessory/Service are scaffolding "
                           "only -- planning them is refused (409) with the reason why.",
            "gear_positions": "GET /api/vehicle/gear-positions lists Park/Reverse/Neutral/"
                              "Drive; NONE has a verified CAN frame on this platform yet "
                              "(RX path firmware-traced only). Scaffolding only -- never "
                              "transmits.",
        },
        "pi_host": "GET /api/pi/status (CPU/RAM/disk/interfaces/services) and GET /api/pi/wifi "
                   "are read-only; reboot, service restarts and Wi-Fi connect/disconnect are "
                   "Tier-2 (/api/pi/.../plan then .../execute). A Wi-Fi password is accepted "
                   "only in the connect execute body and is never returned.",
        "docs": "/api/docs",
    }


# ============================ CAN ===============================================
@app.get("/api/can/stats", tags=["can"])
async def can_stats():
    return {**CAN.stats(), "link": await system_status.can_link_status()}


@app.websocket("/ws/can")
async def ws_can(ws: WebSocket):
    await ws.accept()
    q = CAN.subscribe()
    try:
        # prime with current stats
        await ws.send_text(json.dumps({"type": "stats", "data": CAN.stats()}))
        last_stats = time.monotonic()
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=1.0)
                await ws.send_text(json.dumps({"type": "frame", "data": json.loads(msg)}))
            except asyncio.TimeoutError:
                pass
            if time.monotonic() - last_stats >= 1.0:
                await ws.send_text(json.dumps({"type": "stats", "data": CAN.stats()}))
                last_stats = time.monotonic()
    except WebSocketDisconnect:
        pass
    finally:
        CAN.unsubscribe(q)


@app.get("/api/can/decode", tags=["can"])
async def can_decode():
    """Read-only: the latest decoded named signals from the passive observer, run through
    a vendored opendbc CANParser against backend/gm_bench.dbc. Every signal is BENCH-
    VERIFIED (each carries its platform/can_network.md citation); this never transmits and
    only reads frames already flowing. Poll it for a live view (the UI refreshes it)."""
    return CAN_DECODER.snapshot()


@app.get("/api/can/sequences", tags=["can"])
async def can_sequences():
    return {"sequences": [{"name": k, **v} for k, v in sequences.SEQUENCES.items()],
            "continuous": sequences.continuous_status()}


class ExecuteBody(BaseModel):
    """Body for every Tier-2 .../execute endpoint: a single-use plan token + the exact
    literal confirmation string returned by the matching .../plan call."""
    token: str
    literal: str


class SequenceBody(BaseModel):
    dry_run: bool = True


@app.post("/api/can/sequence/stop", tags=["can"])
async def stop_sequence():
    """Stop a running continuous CAN sequence (full / startup-keepalive) on request.
    Non-destructive: only halts transmission and resumes the service keepalive if it
    was paused for the run. Registered before /{name} so "stop" is never matched as a
    sequence name."""
    return await sequences.stop_current()


@app.post("/api/can/sequence/{name}", tags=["can"])
async def run_sequence(name: str, body: SequenceBody):
    """Run a non-destructive sequence, or a dry-run of any sequence. A destructive
    sequence can only be *executed* through the Tier-2 plan->execute token flow below."""
    spec = sequences.SEQUENCES.get(name)
    if spec is None:
        raise HTTPException(404, f"unknown sequence {name!r}")
    if not body.dry_run and spec.get("destructive"):
        raise HTTPException(409, f"destructive sequence {name!r} must go through the Tier-2 token flow: "
                                 f"POST /api/can/sequence/{name}/plan then /api/can/sequence/{name}/execute")
    try:
        return await sequences.run_sequence(name, dry_run=body.dry_run)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.post("/api/can/sequence/{name}/plan", tags=["can"])
async def run_sequence_plan(name: str):
    """Plan a Tier-2 (destructive) CAN sequence: returns a single-use token + the literal
    confirmation the caller must echo to /execute. Same gate as cal-write/elk-*."""
    spec = sequences.SEQUENCES.get(name)
    if spec is None:
        raise HTTPException(404, f"unknown sequence {name!r}")
    if not spec.get("destructive"):
        raise HTTPException(400, f"sequence {name!r} is not destructive; "
                                 f"POST /api/can/sequence/{name} with dry_run=false")
    return {**tier2.REGISTRY.plan("can-sequence", literal=f"EXECUTE {name}", payload={"name": name}),
            "sequence": name, "will_do": spec.get("desc"),
            "risk": "DESTRUCTIVE: transmits live on the vehicle CAN bus."}


@app.post("/api/can/sequence/{name}/execute", tags=["can"])
async def run_sequence_execute(name: str, body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("can-sequence", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    if plan.payload.get("name") != name:
        raise HTTPException(400, "token was issued for a different sequence")
    try:
        return await sequences.run_sequence(name, dry_run=False)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# ============================ Vehicle state (engine power mode / gear) ========
# Zero-guessing: see backend/vehicle_state.py's module docstring for the exact evidence
# behind every verified value here, and why Accessory/Service and every gear position
# are scaffolding-only (no verified CAN frame exists for them on this platform).
@app.get("/api/vehicle/power-modes", tags=["can"])
async def vehicle_power_modes():
    return {"modes": [{"name": k, **v} for k, v in vehicle_state.POWER_MODES.items()]}


@app.get("/api/vehicle/gear-positions", tags=["can"])
async def vehicle_gear_positions():
    return {"positions": [{"name": k, **v} for k, v in vehicle_state.GEAR_POSITIONS.items()],
            "note": vehicle_state.GEAR_RX_NOTE}


@app.post("/api/vehicle/power-mode/{mode}/plan", tags=["can"])
async def vehicle_power_mode_plan(mode: str):
    """Plan a Tier-2 engine/ignition power-mode frame send. Only a mode with a directly
    verified CAN 0x284 byte pattern (currently: off, run) can be planned; an unverified
    mode (accessory, service) is refused here -- never issued a token -- so the UI/LLM
    path cannot accidentally transmit a guessed frame onto the real vehicle bus."""
    spec = vehicle_state.POWER_MODES.get(mode)
    if spec is None:
        raise HTTPException(404, f"unknown power mode {mode!r}")
    if not spec["verified"]:
        raise HTTPException(409, f"power mode {mode!r} has no verified CAN frame on this "
                                 f"platform ({spec['reason']}) -- refusing to plan an "
                                 "unverified transmit. See /api/vehicle/power-modes.")
    return {**tier2.REGISTRY.plan("vehicle-power-mode", literal=f"SET POWER MODE {mode.upper()}",
                                  payload={"mode": mode}),
            "mode": mode, "can_id": f"{spec['can_id']:03X}", "dlc": spec["dlc"],
            "data_hex": spec["data_hex"], "evidence": spec["evidence"],
            "will_do": f"transmit one CAN {spec['can_id']:03X} frame (DLC {spec['dlc']}, "
                       f"data {spec['data_hex']}) on {config.CAN_IFACE}; the keepalive is "
                       "paused for the send and resumed immediately after.",
            "risk": "DESTRUCTIVE: transmits live on the vehicle CAN bus."}


@app.post("/api/vehicle/power-mode/{mode}/execute", tags=["can"])
async def vehicle_power_mode_execute(mode: str, body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("vehicle-power-mode", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    if plan.payload.get("mode") != mode:
        raise HTTPException(400, "token was issued for a different power mode")
    spec = vehicle_state.POWER_MODES.get(mode)
    if spec is None or not spec["verified"]:
        raise HTTPException(409, f"power mode {mode!r} is not verified; refusing to transmit")
    try:
        return await sequences.send_vehicle_power_mode(mode, bytes.fromhex(spec["data_hex"]), spec["can_id"])
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.post("/api/vehicle/gear-position/{position}/plan", tags=["can"])
async def vehicle_gear_position_plan(position: str):
    """Always refuses: no gear position has a verified CAN frame on this platform yet
    (see vehicle_state.GEAR_RX_NOTE). This endpoint exists so the UI/LLM surface is
    complete and self-describing, not to ever issue a token."""
    spec = vehicle_state.GEAR_POSITIONS.get(position)
    if spec is None:
        raise HTTPException(404, f"unknown gear position {position!r}")
    raise HTTPException(501, f"gear position {position!r} has no verified CAN signal on "
                             f"this platform ({spec['reason']}) -- this control is UI/API "
                             "scaffolding only and will never transmit until a verified "
                             "signal exists. See /api/vehicle/gear-positions.")


# ============================ UART =============================================
@app.get("/api/uart/ports", tags=["uart"])
async def uart_ports():
    return {"ports": await UART.probe()}


@app.websocket("/ws/uart/{port_id}")
async def ws_uart(ws: WebSocket, port_id: str):
    port = UART.get(port_id)
    if port is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    q = port.subscribe()

    async def sender():
        while True:
            await ws.send_text(await q.get())

    async def watch_close():
        # A silent UART never triggers a send, so a closed browser would otherwise hold
        # the subscription (and the ser2net port + device lock) forever.
        while (await ws.receive())["type"] != "websocket.disconnect":
            pass

    tasks = [asyncio.create_task(sender()), asyncio.create_task(watch_close())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        port.unsubscribe(q)


# ============================ T1 / adb ========================================
@app.get("/api/t1", tags=["t1"])
async def t1():
    return await system_status.t1_status()


@app.get("/api/adb/devices", tags=["adb"])
async def adb_devices():
    return {"devices": await system_status.adb_devices()}


@app.post("/api/adb/connect-t1", tags=["adb"])
async def adb_connect_t1():
    return await system_status.adb_connect_t1()


@app.post("/api/adb/install", tags=["adb"])
async def adb_install(serial: str = Form(...), reinstall: bool = Form(True),
                      apk: UploadFile = File(...)):
    name = Path(apk.filename or "upload.apk").name
    if not name.lower().endswith(".apk"):
        raise HTTPException(400, "expected a .apk file")
    dest = config.UPLOAD_DIR / f"{int(time.time())}_{name}"
    data = await apk.read()
    # Up to client_max_body_size (128 MB) onto the Pi's SD card: off the event loop.
    await asyncio.to_thread(dest.write_bytes, data)
    try:
        return await calibration.adb_install(serial, dest, reinstall=reinstall)
    finally:
        try:
            dest.unlink()
        except OSError:
            pass


# ============================ terminals (pty) =================================
@app.websocket("/ws/shell")
async def ws_shell(ws: WebSocket):
    await ws.accept()
    sess = terminals.PtySession(terminals.pi_shell_argv())
    sess.spawn()
    await _bridge_pty(ws, sess)


@app.websocket("/ws/adb-shell")
async def ws_adb_shell(ws: WebSocket):
    serial = ws.query_params.get("serial")
    if not serial:
        await ws.close(code=4400)
        return
    await ws.accept()
    sess = terminals.PtySession(terminals.adb_shell_argv(serial))
    sess.spawn()
    await _bridge_pty(ws, sess)


async def _bridge_pty(ws: WebSocket, sess: terminals.PtySession):
    def on_input(msg):
        if "bytes" in msg and msg["bytes"] is not None:
            return ("data", msg["bytes"])
        text = msg.get("text")
        if text is None:
            if msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()
            return None
        if text.startswith("\x00resize:"):  # control frame: \x00resize:cols,rows
            try:
                cols, rows = (int(x) for x in text[len("\x00resize:"):].split(","))
                return ("resize", (cols, rows))
            except ValueError:
                return None
        return ("data", text.encode())
    try:
        await terminals.pump(sess, ws, on_input)
    except WebSocketDisconnect:
        sess.close()


# ============================ UDS / diagnostics ================================
def _uds_read_all(dids: list[int], enter_extended: bool) -> dict:
    """Blocking: open one diagnosticsd connection, optionally enter extended, read DIDs."""
    results = {}
    with UDSClient() as c:
        session = None
        if enter_extended:
            session = c.session(0x03).as_dict()
        for did in dids:
            r = c.read_did(did)
            results[f"{did:04X}"] = r.as_dict()
    return {"extended_session": session, "reads": results}


@app.get("/api/uds/dids", tags=["uds"])
async def uds_dids():
    return {"dids": diagdata.READ_DIDS, "note": "Safe, non-destructive reads. F0A7 needs SecurityAccess."}


class ReadBody(BaseModel):
    dids: list[str]
    extended_session: bool = True


@app.post("/api/uds/read", tags=["uds"])
async def uds_read(body: ReadBody):
    try:
        dids = [int(d, 16) for d in body.dids]
    except ValueError:
        raise HTTPException(400, "dids must be hex strings like 'F181'")
    try:
        return await asyncio.to_thread(_uds_read_all, dids, body.extended_session)
    except UDSError as e:
        raise HTTPException(502, str(e))


@app.get("/api/uds/calibration", tags=["uds"])
async def uds_calibration():
    """Live calibration identity read: DID F182, parsed against the slot map (safe)."""
    def work():
        with UDSClient() as c:
            c.session(0x03)
            r = c.read_did(0xF182)
            if not r.ok:
                return {"ok": False, "uds": r.as_dict()}
            records = diagdata.parse_f182(r.response)
            return {"ok": True, "uds": r.as_dict(), "records": records,
                    "slots": [rec for rec in records if "slot" in rec]}
    try:
        return await asyncio.to_thread(work)
    except (UDSError, ValueError) as e:
        raise HTTPException(502, str(e))


@app.get("/api/uds/slot-map", tags=["uds"])
async def uds_slot_map():
    return {"slots": [{"slot": f"{s:02X}", "slot_dec": s, **info,
                       "triage_label": diagdata.TRIAGE_LABEL[info["triage"]]}
                      for s, info in sorted(diagdata.SLOT_MAP.items())]}


@app.get("/api/uds/dtc", tags=["uds"])
async def uds_dtc(sub: str = "02", mask: str = "FF"):
    def work():
        with UDSClient() as c:
            c.session(0x03)
            r = c.read_dtc(int(sub, 16), int(mask, 16))
            return r.as_dict()
    try:
        return await asyncio.to_thread(work)
    except (UDSError, ValueError) as e:
        raise HTTPException(502, str(e))


class UnlockBody(BaseModel):
    level: int = 0x01


@app.post("/api/uds/security/unlock", tags=["uds"])
async def uds_unlock(body: UnlockBody):
    """Attempt the documented degenerate SecurityAccess (all-FF seed -> 12 zero bytes).
    Non-destructive; only gates protected reads. Returns the seed and grant."""
    def work():
        with UDSClient() as c:
            sess = c.session(0x03).as_dict()
            seed = c.security_request_seed(body.level)
            if not seed.ok:
                return {"extended_session": sess, "seed": seed.as_dict(), "unlocked": False}
            key = diagdata.DEGENERATE_KEY
            grant = c.security_send_key(body.level + 1, key)
            return {"extended_session": sess, "seed": seed.as_dict(),
                    "key_hex": key.hex(), "grant": grant.as_dict(),
                    "unlocked": grant.ok, "note": diagdata.SECURITY_NOTE}
    if body.level not in diagdata.SECURITY_LEVELS:
        raise HTTPException(400, f"level must be one of {[f'{l:02X}' for l in diagdata.SECURITY_LEVELS]}")
    try:
        return await asyncio.to_thread(work)
    except UDSError as e:
        raise HTTPException(502, str(e))


@app.get("/api/uds/routines", tags=["uds"])
async def uds_routines():
    return {"routines": diagdata.ROUTINES,
            "note": "Non-destructive routines run via POST /api/uds/routine/<RID> (dry_run=false). "
                    "Destructive routines require the Tier-2 token flow: POST .../plan then .../execute "
                    "echoing literal 'EXECUTE <RID>'. This backend will not fire them otherwise."}


class RoutineBody(BaseModel):
    control: str = "01"
    params: str = ""
    unlock_level: int | None = None
    dry_run: bool = True


def _routine_work(spec: dict, control: str, params: str, unlock_level: int | None):
    """Build the blocking UDS worker that actually fires routine `spec` (session ->
    optional unlock -> 31 request). Shared by the direct non-destructive path and the
    Tier-2 execute path so there is exactly one implementation of the send."""
    payload = diagdata.routine_request_bytes(control, spec["rid"], params or spec["params"])

    def work():
        with UDSClient() as c:
            steps = {"extended_session": c.session(0x03).as_dict()}
            if unlock_level is not None:
                c.security_request_seed(unlock_level)
                steps["unlock"] = c.security_send_key(unlock_level + 1, diagdata.DEGENERATE_KEY).as_dict()
            steps["routine"] = c.request(payload).as_dict()
            return steps
    return work


@app.post("/api/uds/routine/{rid}", tags=["uds"])
async def uds_routine(rid: str, body: RoutineBody):
    """Dry-run any routine, or run a NON-destructive routine live. A destructive routine
    (e.g. 0247 factory reset, 0249 calibration clear) can only be executed through the
    Tier-2 plan->execute token flow below."""
    spec = next((r for r in diagdata.ROUTINES if r["rid"] == rid.upper()), None)
    if spec is None:
        raise HTTPException(404, f"unknown routine {rid}")
    payload = diagdata.routine_request_bytes(body.control, spec["rid"], body.params or spec["params"])
    if body.dry_run:
        from .uds import build_request
        return {"routine": spec["name"], "rid": spec["rid"], "dry_run": True,
                "uds_payload_hex": payload.hex(),
                "wire_frame_hex": build_request(config.UDS_TESTER, config.UDS_ECU, payload).hex(),
                "would_require_security": spec["security"], "destructive": spec["destructive"],
                "note": "dry-run: nothing sent to the ECU"}
    if spec["destructive"]:
        raise HTTPException(409, f"destructive routine {spec['rid']} must go through the Tier-2 token flow: "
                                 f"POST /api/uds/routine/{spec['rid']}/plan then /api/uds/routine/{spec['rid']}/execute")
    work = _routine_work(spec, body.control, body.params, body.unlock_level)
    try:
        return {"routine": spec["name"], "rid": spec["rid"], "dry_run": False, "steps": await asyncio.to_thread(work)}
    except UDSError as e:
        raise HTTPException(502, str(e))


class RoutinePlanBody(BaseModel):
    control: str = "01"
    params: str = ""
    unlock_level: int | None = None


@app.post("/api/uds/routine/{rid}/plan", tags=["uds"])
async def uds_routine_plan(rid: str, body: RoutinePlanBody):
    """Plan a Tier-2 (destructive) UDS routine. The exact control/params/unlock are bound
    into the single-use token here, so /execute runs precisely what was planned."""
    spec = next((r for r in diagdata.ROUTINES if r["rid"] == rid.upper()), None)
    if spec is None:
        raise HTTPException(404, f"unknown routine {rid}")
    if not spec["destructive"]:
        raise HTTPException(400, f"routine {spec['rid']} is not destructive; "
                                 f"POST /api/uds/routine/{spec['rid']} with dry_run=false")
    payload = diagdata.routine_request_bytes(body.control, spec["rid"], body.params or spec["params"])
    from .uds import build_request
    return {**tier2.REGISTRY.plan("uds-routine", literal=f"EXECUTE {spec['rid']}",
                                  payload={"rid": spec["rid"], "control": body.control,
                                           "params": body.params, "unlock_level": body.unlock_level}),
            "routine": spec["name"], "rid": spec["rid"],
            "uds_payload_hex": payload.hex(),
            "wire_frame_hex": build_request(config.UDS_TESTER, config.UDS_ECU, payload).hex(),
            "would_require_security": spec["security"], "destructive": spec["destructive"],
            "risk": f"DESTRUCTIVE: {spec.get('reversible', 'irreversible ECU state change')}."}


@app.post("/api/uds/routine/{rid}/execute", tags=["uds"])
async def uds_routine_execute(rid: str, body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("uds-routine", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    if plan.payload.get("rid") != rid.upper():
        raise HTTPException(400, "token was issued for a different routine")
    spec = next((r for r in diagdata.ROUTINES if r["rid"] == plan.payload["rid"]), None)
    if spec is None:
        raise HTTPException(404, f"unknown routine {plan.payload['rid']}")
    work = _routine_work(spec, plan.payload["control"], plan.payload["params"], plan.payload["unlock_level"])
    try:
        return {"routine": spec["name"], "rid": spec["rid"], "dry_run": False,
                "steps": await asyncio.to_thread(work)}
    except UDSError as e:
        raise HTTPException(502, str(e))


# ============================ calibration write ================================
@app.get("/api/cal/workflow", tags=["calibration"])
async def cal_workflow():
    return calibration.DPS_WRITE_WORKFLOW


# ============================ calibration write (Tier 2, token-gated) ==========
# The live write and its F182 verify are delegated to the single proven implementation,
# bench_can/calibration_write_can0.py (see calibration.run_can0_cal): one programming
# session for the whole package, 4093-byte TransferData blocks for a genuine/stock write
# (no CAN 0x613/0x614), or the 0x613/0x614 VIP override path for a modified container. The
# write path is decided from the uploaded bytes (stock hash-match => genuine), never a UI
# toggle. The 613/614 TEST endpoint below is a separate, read-only link check, and also
# runs as the write's own pre-flight health check.
@app.get("/api/cal/ltz-reference", tags=["calibration"])
async def cal_ltz_reference():
    """Verify the stock LTZ reference set against the manifest SHA-256s (ground truth)."""
    return await asyncio.to_thread(ltz_ref.verify_all)


@app.post("/api/cal/write/test", tags=["calibration"])
async def cal_write_test():
    """TEST the live 613/614 VIP dev link (connect + save + verify-readback the two
    verifier words). Non-destructive: no override, no UDS write, no restore."""
    return await asyncio.to_thread(calibration.cal_write_test)


# --- upload staging: the write's primary input is an upload (a .zip or individual module
# files), each identified by its GM part-number filename. Detection cross-references the
# part number -> slot map (ltz_ref.slot_for_part); the file's own bytes decide genuine
# (hash-matches the stock reference) vs modified (does not, -> 0x613/0x614 override path).
# Staged packages live in-memory keyed by a stage id until a plan consumes them.
_CAL_STAGES: dict[str, dict] = {}
CAL_STAGE_TTL = 1800.0  # seconds


def _gc_cal_stages() -> None:
    now = time.time()
    for sid in [s for s, v in _CAL_STAGES.items() if now - v["created"] > CAL_STAGE_TTL]:
        _CAL_STAGES.pop(sid, None)


def _detect_module(name: str, data: bytes, pkg_dir: Path) -> dict:
    """Classify one uploaded module by its part-number filename and its bytes, writing it
    into pkg_dir under its bare part number (the --package-dir layout the writer reads)."""
    base = Path(name).name
    # The file is named by its GM part number; accept a bare part or one with an extension.
    part = base if ltz_ref.slot_for_part(base) else (
        Path(base).stem if ltz_ref.slot_for_part(Path(base).stem) else None)
    if part is None:
        return {"filename": base, "recognized": False, "slot": None, "part": None,
                "reason": "filename is not a known GM calibration part number"}
    slot = ltz_ref.slot_for_part(part)
    genuine = ltz_ref.is_stock_bytes(part, data)
    out = pkg_dir / part
    out.write_bytes(data)
    return {"filename": base, "recognized": True, "slot": slot, "part": part,
            "genuine": genuine, "bytes": len(data), "path": str(out)}


@app.post("/api/cal/write/stage", tags=["calibration"])
async def cal_write_stage(package: UploadFile | None = File(None),
                          modules: list[UploadFile] = File(default=[])):
    """Stage a calibration-write upload and report which slots it populates.

    Input is a full package `.zip` (part-number-named members) and/or one or more
    individual module files (each named by its GM part number). Each module is mapped to a
    slot via the part number and classified genuine (bytes hash-match the stock reference)
    or modified. With no upload at all, the pinned verified stock reference set is staged
    instead, so a stock-recovery write needs no file. Returns a stage id the plan step
    consumes plus the detected entries - nothing is written to the ECU here."""
    import tempfile
    config.PKG_STAGE_DIR.mkdir(parents=True, exist_ok=True)
    _gc_cal_stages()
    pkg_dir = Path(tempfile.mkdtemp(prefix="pkg_", dir=config.PKG_STAGE_DIR))
    entries: list[dict] = []
    unrecognized: list[dict] = []

    have_upload = bool((package and package.filename) or any(m.filename for m in modules))
    if package is not None and package.filename:
        raw = await package.read()
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    d = _detect_module(info.filename, zf.read(info), pkg_dir)
                    (entries if d["recognized"] else unrecognized).append(d)
        except zipfile.BadZipFile:
            raise HTTPException(400, "not a valid .zip archive")
    for m in modules:
        if not m.filename:
            continue
        d = _detect_module(m.filename, await m.read(), pkg_dir)
        (entries if d["recognized"] else unrecognized).append(d)

    if not have_upload:
        # No upload: stage the pinned verified stock reference set (a genuine recovery write).
        for e in ltz_ref.full_package():
            entries.append({"filename": e["part"], "recognized": True, "slot": e["slot"],
                            "part": e["part"], "genuine": True,
                            "bytes": Path(e["path"]).stat().st_size, "path": e["path"]})

    # Collapse duplicate slots (last wins), keep slot order.
    by_slot: dict[str, dict] = {}
    for e in entries:
        by_slot[e["slot"]] = e
    ordered = [by_slot[s] for s in sorted(by_slot)]
    if not ordered:
        raise HTTPException(422, "no recognizable calibration modules in the upload "
                                 "(each file must be named by a known GM part number)")

    source = ("pinned stock reference set" if not have_upload
              else "uploaded package" if package and package.filename and not modules
              else "uploaded modules" if not (package and package.filename)
              else "uploaded package + modules")
    sid = secrets.token_urlsafe(18)
    _CAL_STAGES[sid] = {"created": time.time(), "dir": str(pkg_dir),
                        "entries": ordered, "source": source}
    return {"stage_id": sid, "source": source,
            "package_genuine": all(e["genuine"] for e in ordered),
            "entries": [{"slot": e["slot"], "part": e["part"], "genuine": e["genuine"],
                         "bytes": e["bytes"], "recognized": True} for e in ordered],
            "unrecognized": [{"filename": u["filename"], "reason": u["reason"]} for u in unrecognized]}


class CalPlanBody(BaseModel):
    stage_id: str
    slots: list[str] | None = None  # None/[] -> every detected slot


@app.post("/api/cal/write/plan", tags=["calibration"])
async def cal_write_plan(body: CalPlanBody):
    """Plan a Tier-2 calibration write from a previously staged upload.

    `slots` restricts the write to a subset of the detected slots (omit for all). The write
    path (genuine stock vs 0x613/0x614 modified) is decided by the staged bytes, not here -
    if any selected module is modified the whole package write uses the override path."""
    _gc_cal_stages()
    stage = _CAL_STAGES.get(body.stage_id)
    if stage is None:
        raise HTTPException(400, "unknown or expired stage - re-detect the upload")
    detected = {e["slot"].upper(): e for e in stage["entries"]}
    if body.slots:
        want = [s.upper() for s in body.slots]
        missing = [s for s in want if s not in detected]
        if missing:
            raise HTTPException(404, f"staged upload has no module for slot(s) {', '.join(missing)}")
        entries = [detected[s] for s in sorted(want)]
    else:
        entries = [detected[s] for s in sorted(detected)]
    if not entries:
        raise HTTPException(422, "no slots selected to write")

    package_genuine = all(e["genuine"] for e in entries)
    plan_entries = [{"slot": e["slot"], "part": e["part"], "path": e["path"]} for e in entries]
    literal = entries[0]["part"] if len(entries) == 1 else f"PACKAGE {len(entries)}"
    path_desc = ("genuine stock path (no CAN 0x613/0x614, 4093-byte blocks)" if package_genuine
                 else "MODIFIED path: sets the header-verifier words over the CAN 0x613/0x614 "
                      "VIP dev interface first, 1022-byte blocks")
    return {**tier2.REGISTRY.plan("cal-write", literal=literal,
                                  payload={"entries": plan_entries, "genuine": package_genuine}),
            "entries": [{"slot": e["slot"], "part": e["part"],
                         "kind": "stock" if e["genuine"] else "modified"} for e in entries],
            "write_path": "genuine" if package_genuine else "modified (0x613/0x614 override)",
            "will_do": (f"613/614 VIP link pre-flight check, then one programming session for all "
                        f"{len(entries)} slot(s): 10 01/10 03/27 01/27 02/31 01 FF01/31 01 021E/"
                        f"85 02/28 03 01/10 02 once -> per slot 34/36/37/22 F0F1 ({path_desc}) -> "
                        "close once -> F182 verify against the stock reference. Runs "
                        "bench_can/calibration_write_can0.py (pauses the can0 keepalive service, "
                        "restarts it after)."),
            "risk": "DESTRUCTIVE: overwrites the calibration slot(s) on the real ECU."}


CAL_VERIFY_SETTLE_S = 15.0
CAL_VERIFY_ATTEMPTS = 4


def _package_args(entries: list[dict]) -> tuple[Path, list[str]]:
    """The planned entries as calibration_write_can0.py's (--package-dir, --only)."""
    dirs = {Path(e["path"]).parent for e in entries}
    if len(dirs) != 1:
        raise HTTPException(500, f"planned containers span several directories: {sorted(map(str, dirs))}")
    for e in entries:
        if Path(e["path"]).name != e["part"]:
            raise HTTPException(500, f"planned container {e['path']} is not named by its part {e['part']}")
    return dirs.pop(), [e["slot"].upper() for e in entries]


@app.post("/api/cal/write/execute", tags=["calibration"])
async def cal_write_execute(body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("cal-write", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    entries = plan.payload["entries"]
    genuine = plan.payload.get("genuine", True)
    package_dir, slots = _package_args(entries)
    # Serialized against every other dashboard CAN action; the script owns the bus and the
    # keepalive service for its run. Subprocess + await: the event loop stays free, so
    # /api/status and every other request keep being served during the write.
    async with sequences.exclusive_bus() as stopped:
        # Pre-flight: the non-destructive 0x613/0x614 VIP dev-link health check (the same
        # connect + save + verify-readback the standalone test runs), while the keepalive is
        # still up. Informational for a genuine write (which never touches 0x613/0x614) and a
        # link pre-check for a modified write (whose override path does). It does NOT gate the
        # write - the write script does its own 0x613/0x614 handling when genuine=False.
        preflight = await asyncio.to_thread(calibration.cal_write_test)
        write = await calibration.run_can0_cal("package", package_dir, slots, genuine=genuine)
        # After a reprogram the module stays in the programming session and then reboots
        # (observed: 10 03 -> 7F 10 7E ~3 s after, then F182 timeout and ~15-30 s off the
        # bus). Let it settle, then retry the F182 verify a few times.
        verify, verify_attempts = None, 0
        for verify_attempts in range(1, CAL_VERIFY_ATTEMPTS + 1):
            await asyncio.sleep(CAL_VERIFY_SETTLE_S)
            verify = await calibration.run_can0_cal("verify", package_dir, slots,
                                                    timeout=calibration.CAL_VERIFY_TIMEOUT_S)
            if verify["ok"]:
                break
    wres = write.get("result") or {}
    vres = verify.get("result") or {}
    return {"ok": bool(write["ok"] and verify["ok"]),
            "write_path": write.get("write_path"),
            "preflight_613_614_ok": bool(preflight.get("ok")),
            "write_ok": write["ok"], "verify_ok": verify["ok"],
            "write_elapsed_s": write["elapsed_s"], "verify_elapsed_s": verify["elapsed_s"],
            "verify_attempts": verify_attempts,
            "slots_planned": len(entries),
            "slots": [{"slot": r.get("slot"), "part": r.get("part"), "ok": r.get("ok"),
                       "error": r.get("error")} for r in wres.get("results", [])],
            "f182_verify": vres.get("slots"),
            "error": write.get("error") or verify.get("error"),
            "stopped_continuous": stopped,
            "preflight": preflight, "write": write, "verify": verify}


@app.post("/api/cal/verify", tags=["calibration"])
async def cal_verify(scope: str = Form("package"), slot: str = Form(None)):
    """Non-destructive: read live F182 and compare each slot to the stock reference set,
    via the same calibration_write_can0.py (pauses the can0 keepalive for ~10 s)."""
    if scope == "package":
        entries = ltz_ref.full_package()
    else:
        part = ltz_ref.part_for_slot(slot or "")
        path = ltz_ref.container_path(part) if part else None
        if path is None:
            raise HTTPException(404, f"no stock container for slot {slot}")
        entries = [{"slot": slot.upper(), "part": part, "path": str(path)}]
    if not entries:
        raise HTTPException(404, "no verified stock reference set present")
    package_dir, slots = _package_args(entries)
    async with sequences.exclusive_bus():
        verify = await calibration.run_can0_cal("verify", package_dir, slots,
                                                timeout=calibration.CAL_VERIFY_TIMEOUT_S)
    return {"ok": verify["ok"], "f182_verify": (verify.get("result") or {}).get("slots"),
            "error": verify.get("error"), "verify": verify}


# ============================ ELK recovery =====================================
@app.get("/api/elk/status", tags=["elk"])
async def elk_status():
    """Non-destructive: is the ELK USB fastboot interface present, and what does it report."""
    probe, fb = await asyncio.gather(elk.probe_elk(), elk.fastboot_probe())
    return {"usb_probe": probe, "fastboot_probe": fb, "known_good": elk.KNOWN_GOOD,
            "safety": "RAM image boot is volatile/non-persistent (no fuse risk). Flash/SPI writes "
                      "are NOT exposed here. The CAN F000/8180 entry trigger is a candidate."}


@app.post("/api/elk/check-transport", tags=["elk"])
async def elk_check():
    """Live, NON-destructive readiness: ISO-TP UDS + XCP read over can0. No write/reboot."""
    return await elk.check_transport()


@app.post("/api/elk/enter/plan", tags=["elk"])
async def elk_enter_plan():
    return {**tier2.REGISTRY.plan("elk-enter", literal="ENTER ELK"),
            "will_do": "candidate CAN ELK entry: 10 03 / 27 0D seed / 27 0E key / write VIP gate "
                       "FEBD0CF8=1 / 31 01 F000 818003 / restore gate. Reboots the unit if accepted.",
            "risk": "DESTRUCTIVE (reboots the unit into fastboot). CANDIDATE trigger - may be rejected "
                    "(routine absent from VIP table); confirmed entry route is MEI/HECI, not CAN."}


@app.post("/api/elk/enter/execute", tags=["elk"])
async def elk_enter_execute(body: ExecuteBody):
    try:
        tier2.REGISTRY.take("elk-enter", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return await elk.enter_elk()


@app.post("/api/elk/image/upload", tags=["elk"])
async def elk_image_upload(image: UploadFile = File(...)):
    """Store a custom .img for ELK RAM boot and validate it offline (hash/size). Does NOT boot."""
    config.ELK_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = Path(image.filename or "custom.img").name
    dest = config.ELK_IMAGE_DIR / name
    # A RAM-boot image is tens of MB: write it off the event loop.
    await asyncio.to_thread(dest.write_bytes, await image.read())
    validate = await elk.image_validate(dest)
    return {"stored": name, "path": str(dest), "validate": validate,
            "boot_how": "POST /api/elk/boot/plan then /execute with this filename",
            "warning": "An unsigned/wrong image may be rejected by ELK/AVB at boot. RAM boot is "
                       "volatile (no flash, no fuse), but confirm trust before booting a custom image."}


@app.get("/api/elk/images", tags=["elk"])
async def elk_images():
    config.ELK_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return {"images": [{"name": p.name, "size": p.stat().st_size}
                       for p in sorted(config.ELK_IMAGE_DIR.glob("*")) if p.is_file()]}


@app.post("/api/elk/boot/plan", tags=["elk"])
async def elk_boot_plan(image: str = Form(...)):
    path = config.ELK_IMAGE_DIR / Path(image).name
    if not path.is_file():
        raise HTTPException(404, f"no uploaded image {image!r} (upload it first)")
    validate = await elk.image_validate(path)
    return {**tier2.REGISTRY.plan("elk-boot", literal=f"BOOT {path.name}",
                                  payload={"path": str(path)}, min_delay_seconds=5),
            "image_validation": validate,
            "will_do": f"VOLATILE RAM download + boot of {path.name} via ELK fastboot (no flash).",
            "risk": "DESTRUCTIVE-tier: booting an arbitrary/unsigned image is a real risk. RAM boot "
                    "itself is non-persistent and cannot burn a fuse, but the unit must already be in "
                    "ELK and the image may be rejected by AVB. Reserved for the operator to trigger."}


@app.post("/api/elk/boot/execute", tags=["elk"])
async def elk_boot_execute(body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("elk-boot", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return await elk.image_boot(Path(plan.payload["path"]))


# ============================ Pi host (the Raspberry Pi itself) ================
# Reads are live and safe. Reboot, service restarts and Wi-Fi connect/disconnect are
# Tier-2 plan->execute, exactly like every destructive action above. See pi_host.py for
# the commands, the self-restart timer, and the Wi-Fi password handling.
@app.get("/api/pi/status", tags=["pi"])
async def pi_status():
    """Pi-side analog of /api/status: CPU, RAM, disks, interfaces, restartable services."""
    return await pi_host.status()


@app.post("/api/pi/reboot/plan", tags=["pi"])
async def pi_reboot_plan():
    allowed = await pi_host.sudo_allows(pi_host.REBOOT_ARGV)
    if not allowed:
        raise HTTPException(409, "sudo does not allow this user to run "
                                 f"'{' '.join(pi_host.REBOOT_ARGV)}' without a password")
    return {**tier2.REGISTRY.plan("pi-reboot", literal="REBOOT PI"),
            "command": f"sudo -n {' '.join(pi_host.REBOOT_ARGV)} "
                       f"(via a {pi_host.REBOOT_DELAY_S} s systemd-run timer)",
            "sudo_preflight": "allowed (sudo -n -l)",
            "will_do": f"Reboot the Raspberry Pi {pi_host.REBOOT_DELAY_S} s after confirming. "
                       "The dashboard, CAN keepalive, UART bridge and every terminal stop until "
                       "it is back (typically under a minute); this page waits and reconnects.",
            "risk": "DISRUPTIVE: the whole bench host goes offline; the radio loses its CAN "
                    "keepalive for the duration of the reboot."}


@app.post("/api/pi/reboot/execute", tags=["pi"])
async def pi_reboot_execute(body: ExecuteBody):
    try:
        tier2.REGISTRY.take("pi-reboot", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return await pi_host.reboot()


@app.post("/api/pi/restart/{target}/plan", tags=["pi"])
async def pi_restart_plan(target: str):
    spec = pi_host.TARGETS.get(target)
    if spec is None:
        raise HTTPException(404, f"unknown restart target {target!r}; one of {list(pi_host.TARGETS)}")
    extra = {}
    if target == "nginx":
        ok, msg = await pi_host.nginx_config_ok()
        if not ok:
            raise HTTPException(409, f"nginx -t fails, refusing to plan a restart: {msg}")
        extra["config_test"] = "nginx -t passed"
    return {**tier2.REGISTRY.plan("pi-restart", literal=f"RESTART {target.upper()}",
                                  payload={"target": target}),
            "target": spec["label"], "units": ", ".join(spec["units"]), **extra,
            "will_do": spec["desc"],
            "risk": "DISRUPTIVE: interrupts a running bench service."}


@app.post("/api/pi/restart/{target}/execute", tags=["pi"])
async def pi_restart_execute(target: str, body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("pi-restart", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    if plan.payload.get("target") != target:
        raise HTTPException(400, "token was issued for a different restart target")
    return await pi_host.restart(target)


@app.get("/api/pi/wifi", tags=["pi"])
async def pi_wifi():
    """NetworkManager Wi-Fi view: radio, Wi-Fi devices, saved profiles, visible networks
    (cached scan). Never returns a secret."""
    return await pi_host.wifi_state()


@app.post("/api/pi/wifi/rescan", tags=["pi"])
async def pi_wifi_rescan():
    """Non-destructive: ask NetworkManager for a fresh scan (it rate-limits)."""
    return await pi_host.rescan((await pi_host.wifi_state())["device"])


class WifiPlanBody(BaseModel):
    uuid: str | None = None        # connect a saved profile
    ssid: str | None = None        # or join by SSID
    hidden: bool = False
    with_password: bool = False    # the password itself is only sent to .../execute
    device: str | None = None


def _viewing_via(request: Request, ipv4: list[str]) -> bool:
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]")
    return any(a.split("/")[0] == host for a in ipv4)


async def _wifi_device(want: str | None) -> dict:
    st = await pi_host.wifi_state()
    devs = st["devices"]
    if not devs:
        raise HTTPException(409, "NetworkManager reports no Wi-Fi device on this Pi")
    dev = next((d for d in devs if d["device"] == want), None) if want else devs[0]
    if dev is None:
        raise HTTPException(404, f"no Wi-Fi device {want!r}")
    if st["radio"] != "enabled":
        raise HTTPException(409, f"the Wi-Fi radio is {st['radio']} (nmcli radio wifi)")
    return dev


@app.post("/api/pi/wifi/connect/plan", tags=["pi"])
async def pi_wifi_connect_plan(body: WifiPlanBody, request: Request):
    dev = await _wifi_device(body.device)
    device = dev["device"]
    if body.uuid:
        saved = await pi_host.find_saved(uuid=body.uuid)
        if saved is None:
            raise HTTPException(404, "no saved Wi-Fi profile with that id")
        payload = {"mode": "saved", "uuid": saved["uuid"], "ssid": saved["ssid"], "device": device}
        will = (f"Connect {device} to saved network \"{saved['ssid']}\" (profile "
                f"\"{saved['name']}\", using the password NetworkManager already stores).")
        ssid, password_rule = saved["ssid"], "none"
    elif body.ssid is not None:
        try:
            ssid = pi_host.validate_ssid(body.ssid)
        except pi_host.WifiInputError as e:
            raise HTTPException(400, str(e))
        seen = await pi_host.visible_entry(ssid, device)
        kind = seen["kind"] if seen else "wpa-psk"
        if kind == "enterprise":
            raise HTTPException(409, f"\"{ssid}\" uses 802.1X (enterprise) authentication, "
                                     "which this control does not set up")
        if seen is None and not body.hidden:
            raise HTTPException(404, f"\"{ssid}\" is not in the current scan; rescan, or tick "
                                     "'hidden network' to join it anyway")
        existing = await pi_host.find_saved(ssid=ssid)
        if kind == "open" and body.with_password:
            raise HTTPException(400, f"\"{ssid}\" is an open network; leave the password empty")
        if kind != "open" and not body.with_password and existing is None:
            raise HTTPException(400, f"\"{ssid}\" is secured ({seen['security'] if seen else 'WPA'}); "
                                     "a password is required")
        payload = {"mode": "join", "ssid": ssid, "device": device, "kind": kind,
                   "hidden": body.hidden, "with_password": body.with_password,
                   "existing_uuid": existing["uuid"] if existing else None}
        if existing:
            will = (f"Connect {device} to \"{ssid}\" using its existing saved profile "
                    f"\"{existing['name']}\"" + (", replacing the password NetworkManager stores "
                                                 "for it with the one you entered." if body.with_password else "."))
        else:
            will = (f"Create a NetworkManager profile \"{ssid}\" ({kind}, autoconnect on"
                    + (", hidden" if body.hidden else "") + f") and connect {device} to it"
                    + (". The password goes only to NetworkManager, which stores it in its own "
                       "root-only profile" if body.with_password else "")
                    + ". If the connection fails, the new profile is removed again.")
    else:
        raise HTTPException(400, "give either uuid (a saved profile) or ssid")
    risk = "Changes the Pi's network state (Wi-Fi only; the wired links are not touched)."
    if dev.get("connected") and dev.get("ssid") and dev["ssid"] != ssid:
        risk += f" {device} is currently on \"{dev['ssid']}\"; that link is dropped."
        if _viewing_via(request, dev.get("ipv4", [])):
            risk += " You are viewing this page through that Wi-Fi link and will lose it."
    return {**tier2.REGISTRY.plan("pi-wifi-connect", literal=f"CONNECT {ssid}", payload=payload),
            "network": ssid, "device": device,
            "password": "entered, sent with Execute only" if payload.get("with_password") else "not needed",
            "will_do": will, "risk": risk}


@app.post("/api/pi/wifi/connect/execute", tags=["pi"])
async def pi_wifi_connect_execute(request: Request):
    """Body: {token, literal, password?}. Parsed by hand, not by a pydantic model: FastAPI's
    422 validation error echoes the request body back (it would echo the password), so
    every error from this endpoint is a fixed message that never contains a value."""
    try:
        data = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(400, "body must be JSON: {token, literal, password?}")
    if not isinstance(data, dict) or not isinstance(data.get("token"), str) \
            or not isinstance(data.get("literal"), str):
        raise HTTPException(400, "body must be JSON: {token, literal, password?}")
    password = data.pop("password", None)
    if password == "":
        password = None
    try:
        if password is not None:
            pi_host.validate_psk(password)
        plan = tier2.REGISTRY.take("pi-wifi-connect", data["token"], data["literal"])
    except pi_host.WifiInputError as e:
        raise HTTPException(400, str(e))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    p = plan.payload
    if p["mode"] == "saved" and password is not None:
        raise HTTPException(400, "a saved profile connects with its stored password; none may be sent")
    if p["mode"] == "join" and bool(p.get("with_password")) != (password is not None):
        raise HTTPException(400, "the plan was made " + ("with" if p.get("with_password") else "without")
                                 + " a password; plan again")
    try:
        return await pi_host.connect(p, password)
    finally:
        password = None
        data.clear()


class WifiDisconnectBody(BaseModel):
    device: str | None = None


@app.post("/api/pi/wifi/disconnect/plan", tags=["pi"])
async def pi_wifi_disconnect_plan(body: WifiDisconnectBody, request: Request):
    dev = await _wifi_device(body.device)
    if not dev.get("connected"):
        raise HTTPException(409, f"{dev['device']} is not connected")
    risk = "Changes the Pi's network state (Wi-Fi only; the wired links are not touched)."
    if _viewing_via(request, dev.get("ipv4", [])):
        risk += " You are viewing this page through this Wi-Fi link and will lose it."
    return {**tier2.REGISTRY.plan("pi-wifi-disconnect", literal=f"DISCONNECT {dev['device']}",
                                  payload={"device": dev["device"]}),
            "device": dev["device"], "network": dev.get("ssid") or "?",
            "will_do": f"Disconnect {dev['device']} from \"{dev.get('ssid') or '?'}\" "
                       "(nmcli device disconnect). The saved profile is kept.",
            "risk": risk}


@app.post("/api/pi/wifi/disconnect/execute", tags=["pi"])
async def pi_wifi_disconnect_execute(body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("pi-wifi-disconnect", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return await pi_host.disconnect(plan.payload["device"])


# ============================ Field capture (USB) ==============================
# Total raw capture of T1 (eth0), can0 and the VIP UART to a USB drive; see capture.py.
# Start is Tier-2 (it mounts a drive with sudo and opens raw/promiscuous capture sockets);
# Stop and Unmount are plain actions, like stopping a continuous CAN sequence: they only
# end and flush things and must be reachable instantly before pulling the drive.
class CaptureStartBody(BaseModel):
    volume: str | None = None       # USB volume id (UUID or kernel name) from /status
    streams: list[str] = ["t1", "can", "uart"]


class CaptureUnmountBody(BaseModel):
    volume: str


@app.get("/api/capture/status", tags=["capture"])
async def capture_status():
    return await CAPTURE.status()


@app.post("/api/capture/start/plan", tags=["capture"])
async def capture_start_plan(body: CaptureStartBody):
    try:
        pre = await CAPTURE.preflight(body.volume, body.streams)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    v = pre["volume"]
    where = capture.mount_target(v)
    files = {"t1": "t1.pcap", "can": f"{capture.CAN_IFACE}.log", "uart": "uart.log + uart.timing.tsv"}
    return {**tier2.REGISTRY.plan("capture-start", literal="START CAPTURE",
                                  payload={"volume": v["id"], "streams": pre["streams"]}),
            "drive": f"{v['label'] or v['name']} ({v['path']}, {v['fstype']}, "
                     f"{(v['disk'].get('vendor') + ' ' + v['disk'].get('model')).strip() or 'USB'})",
            "free": f"{v['free'] >> 20:,} MiB" if v.get("free") is not None else "checked after mount",
            "mount": "already mounted" if v["mountpoint"] else "mounted now (sudo mount)",
            "on_stop": "files closed, synced, drive unmounted -> safe to unplug",
            "writes_to": f"{where}/{capture.CAPTURE_DIRNAME}/<YYYYmmdd-HHMMSS>/",
            "streams": ", ".join(capture.STREAMS[k]["label"] for k in pre["streams"]),
            "files": ", ".join(files[k] for k in pre["streams"]) + ", session.json, events.log",
            "will_do": "Mount the USB volume if needed, create one session folder and start raw, "
                       "unfiltered capture of the selected streams until you press Stop (or the "
                       "drive fills / is removed). Nothing is transmitted; the CAN observer, "
                       "decoder, keepalive, UDS and the live UART view keep running unchanged.",
            "risk": "Opens a promiscuous raw capture on eth0 and a raw CAN socket, and mounts a "
                    "drive with sudo. Captured files contain everything on the links."}


@app.post("/api/capture/start/execute", tags=["capture"])
async def capture_start_execute(body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("capture-start", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    try:
        return await CAPTURE.start(plan.payload["volume"], plan.payload["streams"])
    except (ValueError, RuntimeError, OSError, asyncio.TimeoutError) as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@app.post("/api/capture/stop", tags=["capture"])
async def capture_stop():
    """Stop every capture stream, flush, write session.json, sync and unmount the drive."""
    return await CAPTURE.stop()


@app.post("/api/capture/unmount", tags=["capture"])
async def capture_unmount(body: CaptureUnmountBody):
    try:
        return await CAPTURE.unmount_volume(body.volume)
    except ValueError as e:
        raise HTTPException(409, str(e))


# ============================ OpenAPI risk tiers ===============================
_RISK_TIER = {
    "status": 0, "can": 0, "uart": 0, "t1": 0, "adb": 1, "uds": 1, "calibration": 2, "elk": 2,
    "pi": 0, "capture": 0,
}
_TIER2_PATH_HINTS = ("/plan", "/execute", "/routine/", "/sequence/", "/write", "/enter", "/boot")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    for path, methods in schema.get("paths", {}).items():
        for method, op in methods.items():
            tags = op.get("tags", [])
            tier = max((_RISK_TIER.get(t, 0) for t in tags), default=0)
            # destructive actions carry the explicit tier regardless of tag
            if any(hint in path for hint in _TIER2_PATH_HINTS):
                tier = max(tier, 2)
            op["x-risk-tier"] = tier
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse("gminfo37 bench dashboard backend. UI at /, API at /api, docs at /api/docs.")
