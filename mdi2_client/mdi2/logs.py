"""Log pull over port 9052 (JSON session + binary get-logs command)."""
from . import messages
from .const import LOG_PORT

def pull_logs(session, name="mdi2py", date="00000000000000000"):
    """Open a session on 9052, trigger the log stream, return decoded frames.

    Sequence (from decrypted capture): session_open -> poll* -> GET_LOGS_CMD -> stream.
    `date` is a client timestamp string (DDMMYYHHMMSS + fraction); value isn't validated.
    """
    ch = session.channels[LOG_PORT]
    ch.send(messages.session_open(name=name, dialer_ip="0.0.0.0",
                                  listener_ip=session.host, date=date))
    ch.send(messages.poll(4))
    ch.send(messages.GET_LOGS_CMD)
    frames = ch.recv_frames(timeout=6.0)
    return [(ctr, messages.parse(body)) for ctr, body in frames]

def parse_container(plaintext: bytes):
    """Inner file container: LE [size][id][namelen][name] sections + text.
    Heuristic split until the exact header layout is finalized."""
    idx = plaintext.find(b"Aug ")
    return [("log", plaintext[idx:] if idx >= 0 else plaintext)]
