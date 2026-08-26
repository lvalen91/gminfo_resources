"""Log pull over port 9052: session_open -> get-logs -> decode SID container."""
import time
from . import messages
from .const import LOG_PORT
from .container import parse_log_container

def pull_logs(session, name="mdi2py", dialer_ip="192.168.171.30"):
    """Open a session on 9052 and pull the device log container.

    Returns list of (filename, bytes) e.g. ('messages', <Varlog>). Validated live.
    NOTE: send session_open as the FIRST message on a fresh session; the message
    counter must have its high bit set (handled by Channel). The device holds ONE
    session, released on clean disconnect — close the session before reconnecting.
    """
    ch = session.channels[LOG_PORT]
    date = time.strftime("%d%m%y%H%M%S") + "1234567"
    ch.send(messages.session_open(name, dialer_ip, session.host, date))
    resp = ch.recv_frames(4.0)
    ch.send(messages.poll(4))
    ch.send(messages.GET_LOGS_CMD)
    files = []
    for _ctr, body in ch.recv_frames(8.0):
        if len(body) > 500:
            files += parse_log_container(body)
    return files
