"""Log pull over port 9052: session_open -> get-logs -> decode -> session_close."""
import time, json
from . import messages
from .const import LOG_PORT
from .container import parse_log_container

def pull_logs(session, name="mdi2py", dialer_ip="192.168.171.30"):
    """Open a session on 9052, pull the log container, then cleanly close the session.

    Returns list of (filename, bytes), e.g. ('messages', <Varlog>). Sending the
    session_close (id 2) lets back-to-back pulls work without a power-cycle.
    """
    ch = session.channels[LOG_PORT]
    date = time.strftime("%d%m%y%H%M%S") + "1234567"
    ch.send(messages.session_open(name, dialer_ip, session.host, date))
    session_id = None
    for _c, body in ch.recv_frames(4.0):
        if body[:1] == b"{":
            try: session_id = json.loads(body).get("data", {}).get("session")
            except Exception: pass
    ch.send(messages.poll(4))
    ch.send(messages.GET_LOGS_CMD)
    files = []
    for _c, body in ch.recv_frames(8.0):
        if len(body) > 500:
            files += parse_log_container(body)
    if session_id is not None:
        try: ch.send(messages.session_close(session_id))   # release the session
        except Exception: pass
    return files
