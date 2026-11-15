"""CLI: discover, derive-key, decrypt a captured pcap, (later) live connect/pull."""
import sys, typer
from . import discover, derive_key, resolve_device, decode_beacon
from .const import DEVICE_IP_DEFAULT

app = typer.Typer(add_completion=False, help="macOS MDI2 Manager (foundation)")


def _target(serial: int | None, host: str | None) -> tuple[int, str]:
    """Resolve (serial, host), auto-populating either from the announce beacon.

    Pass --serial / --host to pin them; omit to track the device live (its RNDIS
    IP is not stable across reconnects). The serial itself is never echoed.
    """
    if serial is not None and host is not None:
        return serial, host
    info = resolve_device()
    s = info.serial if serial is None else serial
    h = info.ip if host is None else host
    typer.echo(f"(auto-resolved MDI2 at {h})", err=True)
    return s, h


@app.command()
def scan(timeout: float = 5.0):
    """Listen for the device announce beacon (225.1.1.1:8194)."""
    r = discover(timeout)
    if not r:
        typer.echo("no device seen")
        return
    ip, data = r
    try:
        decode_beacon(data)
        typer.echo(f"device at {ip} ({len(data)}B beacon); serial auto-resolvable")
    except ValueError:
        typer.echo(f"device at {ip} ({len(data)}B beacon); serial field absent")

@app.command()
def key(serial: int):
    """Compute the 56-byte Blowfish key from a unit serial (uint32)."""
    typer.echo(derive_key(serial).hex())

@app.command()
def connect(serial: int = typer.Argument(None), host: str = typer.Option(None, "--host")):
    """Open the 900x session (requires the MDI2 on this machine's network)."""
    from .transport import Session
    serial, host = _target(serial, host)
    with Session(derive_key(serial), host).connect() as s:
        typer.echo(f"connected {len(s.channels)} channels to {host}")


@app.command()
def rearm(serial: int = typer.Argument(None), host: str = typer.Option(None, "--host")):
    """Re-open the D-PDU tunnel (TCP/10123) via the management PDU START flow."""
    from .live_calibration import rearm_dpdu_tunnel
    serial, host = _target(serial, host)
    typer.echo("10123 armed" if rearm_dpdu_tunnel(serial, host)
               else "re-arm FAILED (no session id — likely session-table exhaustion; stop connect loops and let sessions drain, then retry; USB power-cycle only as last resort)")


@app.command()
def identify(serial: int = typer.Argument(None), host: str = typer.Option(None, "--host")):
    """READ-ONLY: bring up the radio link and read VIN / MEC / cal metadata."""
    from .live_calibration import identify as _identify
    serial, host = _target(serial, host)
    ident = _identify(serial, host)
    printable = len(ident.vin) == 17 and all(0x20 <= b < 0x7F for b in ident.vin)
    typer.echo(f"VIN: {'<17 printable bytes>' if printable else ident.vin.hex()} "
               f"(WMI {ident.vin[:3].decode(errors='replace')})")
    typer.echo(f"F1A0 (MEC/secure): {ident.f1a0.hex()}   F182 records: {ident.f182[3] if len(ident.f182) > 3 else '?'}")


@app.command()
def recover(serial: int = typer.Argument(None), host: str = typer.Option(None, "--host"),
            force_default_session: bool = False):
    """Diagnose a module possibly left in programming mode (no blind retry)."""
    from .live_calibration import recover_state
    serial, host = _target(serial, host)
    for key, value in recover_state(serial, host, force_default_session=force_default_session).items():
        typer.echo(f"{key}: {value}")


@app.command()
def write(folder: str, expected_vin: str, serial: int = typer.Argument(None),
          host: str = typer.Option(None, "--host"),
          confirm: bool = typer.Option(False, "--confirm",
                                       help="required to actually flash; without it only the plan is shown"),
          pre_reset: bool = typer.Option(False, "--pre-reset",
                                         help="opt-in fallback: hard-reset the radio before the write "
                                              "(NOT the stock SPS sequence; use only to retry a failed "
                                              "SPS-method write)")):
    """GATED live write of the stock LTZ package (plan unless --confirm)."""
    from pathlib import Path
    from .live_calibration import plan_ltz_write, write_ltz_calibration
    vin = expected_vin.encode()
    if len(vin) != 17:
        raise typer.BadParameter("expected VIN must be 17 characters")
    serial, host = _target(serial, host)
    if not confirm:
        plan = plan_ltz_write(Path(folder), serial, vin, host)
        typer.echo(f"PLAN: 14 pinned LTZ slots validated; module VIN matches; "
                   f"source {plan.source_calibration}; BCM power mode OFF; "
                   f"battery {plan.battery_mv/1000:.3f} V.")
        typer.echo("Dry run only. Re-run with --confirm to perform the single live write.")
        return
    outcome = write_ltz_calibration(Path(folder), serial, vin, host, confirmed=True,
                                    pre_reset=pre_reset)
    typer.echo(f"WRITE: {outcome.transaction.status}; "
               f"readback matched slots {[f'{s:02X}' for s in outcome.readback.matching_slots]}")


@app.command("security")
def security_cmd(
    seed: str = typer.Argument(..., help="0x27 0x01 seed as hex: ECUID(16)||Challenge(16)[||csum]"),
    key: str = typer.Option(None, "--key", help="AES-128 key hex (16 bytes), overrides the key map"),
    key_map: str = typer.Option(None, "--key-map", help="JSON key-map path; none is auto-loaded (the bundled keys.example.json is placeholders, not used unless passed here)"),
):
    """DRY-RUN: compute the AES-128-CMAC SecurityAccess key response for a seed.

    Pure computation -- never contacts a vehicle. Supply a real key map via
    --key-map (keep it git-ignored; see keys.example.json for the format).

    NOTE: the GM response shaping (CMAC over ECUID||Challenge, first 12 bytes) is
    UNVERIFIED on hardware -- see the warning in security_cmac.py. A wrong shape
    yields NRC 0x35 on a real ECU and may advance the SecurityAccess lockout.
    """
    from .security_cmac import GMSecurityAccess
    sec = GMSecurityAccess(key_map) if key_map else GMSecurityAccess()
    seed_b = bytes.fromhex(seed.replace(" ", "").replace("0x", ""))
    typer.echo(sec.format_seed(seed_b))
    key_b = bytes.fromhex(key.replace(" ", "")) if key else None
    try:
        resp = sec.compute_response(seed_b, key=key_b)
    except KeyError as e:
        typer.echo(f"no key available for this ECUID: {e}")
        raise typer.Exit(1)
    typer.echo(f"key response (12B): {resp.hex()}")
    typer.echo("note: GM response shaping is UNVERIFIED on hardware "
               "(dry-run only; see security_cmac.py)")


@app.command("read-all")
def read_all(
    interface: str = typer.Option("can0", "--interface", help="SocketCAN interface"),
    transport: str = typer.Option("can", "--transport", help="only 'can' is supported here"),
    addrs: str = typer.Option(None, "--addrs", help="comma-separated ECU addresses (hex), e.g. 80,28"),
    security_on: bool = typer.Option(False, "--security", help="attempt SecurityAccess (needs --key-map)"),
    key_map: str = typer.Option(None, "--key-map", help="JSON key-map path for SecurityAccess"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Read identification + SW inventory from GM modules over a SocketCAN bus.

    Bench fallback (non-MDI2). Requires python-can + can-isotp and a live CAN
    interface; does not touch the radio-specific MDI2 live path.
    """
    if transport != "can":
        raise typer.BadParameter("only --transport can is supported for read-all")
    from .can_transport import CANTransport, CanDependencyError
    from .module_reader import ModuleReader
    from .security_cmac import GMSecurityAccess
    want = [int(a, 16) for a in addrs.split(",")] if addrs else None
    t = CANTransport(interface)
    if not t.connect():
        typer.echo("CAN connect failed (install python-can/can-isotp; is the interface up?)")
        raise typer.Exit(1)
    sec = GMSecurityAccess(key_map) if (security_on and key_map) else None
    try:
        reads = ModuleReader(t, security=sec, verbose=verbose).read_all(
            addrs=want, do_security=security_on)
    except CanDependencyError:
        # python-can present but can-isotp missing: clean message, no stacktrace.
        typer.echo("CAN ISO-TP unavailable (install python-can/can-isotp)")
        raise typer.Exit(1)
    finally:
        t.disconnect()
    for r in reads:
        typer.echo(f"{r.info.addr_hex} {r.info.name}: VIN={r.vin or '-'} "
                   f"ECUID={r.ecuid or '-'} SW={len(r.sw_inventory)}"
                   + (f" ERR={r.error}" if r.error else ""))


if __name__ == "__main__":
    app()
