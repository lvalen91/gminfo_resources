"""CLI: discover, derive-key, decrypt a captured pcap, (later) live connect/pull."""
import sys, typer
from . import discover, derive_key
from .const import DEVICE_IP_DEFAULT

app = typer.Typer(add_completion=False, help="macOS MDI2 Manager (foundation)")

@app.command()
def scan(timeout: float = 5.0):
    """Listen for the device announce beacon (225.1.1.1:8194)."""
    r = discover(timeout)
    typer.echo(f"device at {r[0]} ({len(r[1])}B beacon)" if r else "no device seen")

@app.command()
def key(serial: int):
    """Compute the 56-byte Blowfish key from a unit serial (uint32)."""
    typer.echo(derive_key(serial).hex())

@app.command()
def connect(serial: int, host: str = DEVICE_IP_DEFAULT):
    """Open the 900x session (requires the MDI2 on this machine's network)."""
    from .transport import Session
    with Session(derive_key(serial), host).connect() as s:
        typer.echo(f"connected {len(s.channels)} channels to {host}")

if __name__ == "__main__":
    app()
