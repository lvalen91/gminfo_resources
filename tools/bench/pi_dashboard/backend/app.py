"""GM Info 3.7 bench dashboard - FastAPI backend.

LAN-only, no authentication (owner's explicit choice for this home-lab bench). Served
behind the existing nginx under /api and /ws. The REST surface is deliberately clean and
JSON-structured so it doubles as an LLM tool API; OpenAPI/Swagger is at /api/docs.

Destructive operations (ECU factory-reset routines, calibration writes) are WIRED but
never fire without an explicit confirm phrase; everything defaults to dry-run.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import (calibration, canbus, config, diagdata, elk, ltz_ref, sequences,
               system_status, terminals, tier2, uart, vehicle_state)
from .uds import UDSClient, UDSError

app = FastAPI(title="GM Info 3.7 Bench Dashboard", version="1.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json",
              description="LAN-only diagnostic/control API for the owner's gminfo37 bench. "
                          "Reads are safe; destructive ECU/calibration actions require an explicit confirm phrase.")

CAN = canbus.CanObserver()
UART = uart.UartHub()
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def _startup():
    await CAN.start()


@app.on_event("shutdown")
async def _shutdown():
    await sequences.shutdown()
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
    }


@app.get("/api/meta", tags=["status"])
async def api_meta():
    """Self-description for an LLM agent orienting itself to this bench."""
    return {
        "bench": "GM Info 3.7 (gminfo37) infotainment, owner's licensed research bench, LAN-only",
        "can": {"iface": config.CAN_IFACE, "transport": "SocketCAN 500kbit/s",
                "keepalive": "0x529 @ 0.320270s via systemd", "sequences": list(sequences.SEQUENCES)},
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
    dest.write_bytes(data)
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


@app.post("/api/cal/validate", tags=["calibration"])
async def cal_validate(container: UploadFile = File(...),
                       template: UploadFile | None = File(None)):
    """Offline dry-run for a calibration write: ingest the container (digest_ok) and,
    if a genuine template is supplied, reseal + verify the payload digest via caltool.
    Never touches hardware; the RSA signature stays stale by design."""
    cpath = config.UPLOAD_DIR / f"{int(time.time())}_container.bin"
    cpath.write_bytes(await container.read())
    out = {"container": Path(container.filename or "container").name}
    try:
        out["ingest"] = await calibration.caltool_ingest(cpath)
        if template is not None:
            tpath = config.UPLOAD_DIR / f"{int(time.time())}_template.bin"
            tpath.write_bytes(await template.read())
            import json as _j
            entries = {"meta": out["ingest"].get("meta") or {}, "entries": []}
            # Re-ingest to JSON entries for packing round-trip
            ejson = config.UPLOAD_DIR / f"{int(time.time())}_entries.json"
            cli = str(config.CALTOOL_DIR / "cli.py")
            proc = await asyncio.create_subprocess_exec(
                config.BENCH_PYTHON, cli, "ingest", str(cpath),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                cwd=str(config.CALTOOL_DIR))
            data, _ = await proc.communicate()
            ejson.write_bytes(data)
            packed = config.UPLOAD_DIR / f"{int(time.time())}_packed.bin"
            out["pack"] = await calibration.caltool_pack_validate(ejson, tpath, packed)
            for p in (tpath, ejson, packed):
                try:
                    p.unlink()
                except OSError:
                    pass
        return out
    finally:
        try:
            cpath.unlink()
        except OSError:
            pass


# ============================ calibration write (Tier 2, token-gated) ==========
# The write auto-runs the CAN613/614 VIP-RAM step (save -> override -> UDS write ->
# restore in a finally). The TEST path runs only connect + save + verify-readback.
@app.get("/api/cal/ltz-reference", tags=["calibration"])
async def cal_ltz_reference():
    """Verify the stock LTZ reference set against the manifest SHA-256s (ground truth)."""
    return await asyncio.to_thread(ltz_ref.verify_all)


@app.post("/api/cal/write/test", tags=["calibration"])
async def cal_write_test():
    """TEST the live 613/614 VIP dev link (connect + save + verify-readback the two
    verifier words). Non-destructive: no override, no UDS write, no restore."""
    return await asyncio.to_thread(calibration.cal_write_test)


def _uds_cal_transfer(container_bytes: bytes, slot: int):
    """Build the UDS programming-transfer step for a calibration write (the part that
    runs between the 613/614 override and restore). Faithful to the DPS Type4 doc order;
    exact RequestDownload addressing per slot must be confirmed by the operator."""
    def transfer(dev_log: list) -> dict:
        steps = []

        def rec(entry: dict) -> None:
            # Contract (see calibration.cal_write_execute): thread each UDS step into
            # dev_log so the CAN 613/614 steps and these UDS steps form ONE ordered
            # cross-bus timeline, while still returning the structured UDS steps here.
            steps.append(entry)
            dev_log.append({"bus": "uds", **entry})

        with UDSClient() as c:
            for name, payload in (("10 03", b"\x10\x03"), ("27 01", b"\x27\x01")):
                rec({name: c.request(payload).as_dict()})
            # SecurityAccess key (27 02 + degenerate key). Its result MUST be checked:
            # if the ECU rejects the unlock, abort before any 34/36/37 download so we
            # never stream a container to a still-locked ECU, and log the outcome.
            key = c.security_send_key(0x02, diagdata.DEGENERATE_KEY)
            rec({"27 02 (key)": key.as_dict()})
            if not key.ok:
                return {"ok": False, "steps": steps,
                        "error": f"SecurityAccess key rejected (27 02 -> NRC "
                                 f"{key.as_dict().get('nrc', '?')}); aborted before "
                                 "any 34/36/37 write"}
            # Each precondition/session step MUST be checked: a rejection here (e.g.
            # conditionsNotCorrect on 021E/10 02 -- a vehicle/CAN-state precondition,
            # not a security-level problem) must abort before RequestDownload, never
            # fall through to a PEC read that can look clean for an unrelated reason
            # (PEC0000 just means "no pending programming error", which is also true
            # when nothing was ever attempted -- it is not proof a transfer happened).
            for name, payload in (("31 01 FF01", b"\x31\x01\xff\x01"),
                                  ("31 01 021E", b"\x31\x01\x02\x1e"),
                                  ("10 02", b"\x10\x02")):
                step = c.request(payload)
                rec({name: step.as_dict()})
                if not step.ok:
                    return {"ok": False, "steps": steps,
                            "error": f"{name} rejected (NRC {step.as_dict().get('nrc', '?')} "
                                     f"{step.as_dict().get('nrc_name', '')}); aborted before "
                                     "RequestDownload -- no container bytes were sent"}
            # RequestDownload / TransferData / RequestTransferExit of the container.
            rd = c.request(b"\x34\x00\x44" + b"\x00\x00\x00\x00" +
                           len(container_bytes).to_bytes(4, "big"))
            rec({"34 RequestDownload": rd.as_dict()})
            if not rd.ok:
                return {"ok": False, "steps": steps,
                        "error": f"RequestDownload rejected (NRC {rd.as_dict().get('nrc', '?')} "
                                 f"{rd.as_dict().get('nrc_name', '')}); no container bytes were sent"}
            block, idx = 0x0FFF, 1
            all_blocks_ok = True
            for off in range(0, len(container_bytes), block):
                td = c.request(bytes([0x36, idx & 0xFF]) + container_bytes[off:off + block])
                # Log EVERY block (not just failures), labeled with the index that was
                # actually sent (before the increment).
                rec({f"36 block {idx}": td.as_dict()})
                idx += 1
                if not td.ok:
                    all_blocks_ok = False
                    break
            exit_ = c.request(b"\x37")
            rec({"37 TransferExit": exit_.as_dict()})
            pec = c.read_did(0xF0F1)
            rec({"22 F0F1 (PEC)": pec.as_dict()})
            # Success requires every stage to have actually gone through -- not just a
            # clean-looking final PEC, which can be clean because nothing was sent.
            ok = all_blocks_ok and exit_.ok and pec.ok and pec.response.endswith(b"\x00\x00")
        return {"ok": ok, "steps": steps}
    return transfer


async def _package_from_zip(upload: UploadFile) -> list[dict]:
    """Ingest an uploaded calibration-package .zip into an ordered write list.

    Every member is matched BY CONTENT to the verified stock reference set (unwrapped
    SHA-256 vs the manifest); anything that is not a byte-identical known-stock container
    is rejected. The zip is only a carrier for the same verified containers - it can never
    introduce custom calibration bytes (custom cal is not a supported option)."""
    import zipfile
    config.PKG_STAGE_DIR.mkdir(parents=True, exist_ok=True)
    raw = await upload.read()
    stage = config.PKG_STAGE_DIR / f"{int(time.time())}_{Path(upload.filename or 'pkg.zip').name}"
    stage.write_bytes(raw)
    by_slot: dict[int, dict] = {}
    try:
        with zipfile.ZipFile(stage) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                data = zf.read(info)
                sha = ltz_ref._unwrapped_sha256(data)
                match = next(((slot, part) for slot, (part, exp) in ltz_ref.LTZ_REFERENCE.items()
                             if exp == sha), None)
                if match is None:
                    raise HTTPException(422, f"zip member {info.filename!r} does not match any "
                                             "verified stock container (custom cal is not allowed)")
                slot, part = match
                out = config.PKG_STAGE_DIR / f"{int(time.time())}_{part}"
                out.write_bytes(data)
                by_slot[slot] = {"slot": f"{slot:02X}", "part": part, "path": str(out)}
    except zipfile.BadZipFile:
        raise HTTPException(400, "not a valid .zip archive")
    finally:
        try:
            stage.unlink()
        except OSError:
            pass
    if not by_slot:
        raise HTTPException(422, "zip contained no verified stock calibration containers")
    return [by_slot[s] for s in sorted(by_slot)]


@app.post("/api/cal/write/plan", tags=["calibration"])
async def cal_write_plan(scope: str = Form("slot"), slot: str = Form(None),
                         package: UploadFile | None = File(None)):
    """Plan a Tier-2 calibration write in ONE flow.

    `scope` is "slot" (one slot) or "package" (every verified stock slot, in order). The
    bytes come either from the pinned verified stock reference set, or from an uploaded
    `package` .zip whose members must each match a known-stock container by digest. There
    is no custom-calibration source - unverified bytes are never planned."""
    if scope not in ("slot", "package"):
        raise HTTPException(400, 'scope must be "slot" or "package"')

    if package is not None and package.filename:
        entries = await _package_from_zip(package)          # verified-stock zip carrier
        if scope == "slot":
            if not slot:
                raise HTTPException(400, "scope=slot needs a slot")
            entries = [e for e in entries if e["slot"].upper() == slot.upper()]
            if not entries:
                raise HTTPException(404, f"uploaded zip has no verified container for slot {slot}")
    elif scope == "package":
        entries = ltz_ref.full_package()                    # pinned verified stock set
        if not entries:
            raise HTTPException(404, "no verified stock reference set present (use /api/cal/ltz-reference)")
    else:
        if not slot:
            raise HTTPException(400, "scope=slot needs a slot")
        part = ltz_ref.part_for_slot(slot)
        if part is None:
            raise HTTPException(404, f"slot {slot} is not a known calibration slot")
        path = ltz_ref.container_path(part)
        if path is None:
            raise HTTPException(404, f"no stock container for slot {slot} / part {part} (use /api/cal/ltz-reference)")
        entries = [{"slot": slot.upper(), "part": part, "path": str(path)}]

    # Validate every planned container offline before issuing a token.
    validations = []
    for e in entries:
        ingest = await calibration.caltool_ingest(Path(e["path"]))
        validations.append({"slot": e["slot"], "part": e["part"], "ingest": ingest})
    literal = entries[0]["part"] if scope == "slot" else f"PACKAGE {len(entries)}"
    return {**tier2.REGISTRY.plan("cal-write", literal=literal,
                                  payload={"scope": scope, "entries": entries}),
            "scope": scope, "entries": [{"slot": e["slot"], "part": e["part"]} for e in entries],
            "offline_validation": validations,
            "will_do": "per slot: 613/614 connect -> save words -> override markers -> "
                       "UDS 10/27/FF01/021E/10 02/34/36/37 -> restore words (finally) -> disconnect",
            "risk": "DESTRUCTIVE: overwrites the calibration slot(s) on the real ECU. Restore of the "
                    "two verifier words is guaranteed even on failure."}


@app.post("/api/cal/write/execute", tags=["calibration"])
async def cal_write_execute(body: ExecuteBody):
    try:
        plan = tier2.REGISTRY.take("cal-write", body.token, body.literal)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    entries = plan.payload["entries"]

    def run_all() -> dict:
        results, ok = [], True
        for e in entries:
            path = Path(e["path"])
            slot = int(e["slot"], 16)
            transfer = _uds_cal_transfer(path.read_bytes(), slot)
            r = calibration.cal_write_execute(path, slot, transfer)
            results.append(r)
            if not r.get("ok"):
                ok = False
                break  # abort the package on the first failed slot; do not keep writing
        return {"scope": plan.payload["scope"], "ok": ok, "slots_written": len(results),
                "slots_planned": len(entries), "results": results}

    return await asyncio.to_thread(run_all)


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
    dest.write_bytes(await image.read())
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


# ============================ OpenAPI risk tiers ===============================
_RISK_TIER = {
    "status": 0, "can": 0, "uart": 0, "t1": 0, "adb": 1, "uds": 1, "calibration": 2, "elk": 2,
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
