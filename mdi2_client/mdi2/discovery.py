"""Passive device discovery: listen for the 225.1.1.1:8194 announce beacon."""
import socket, struct
from .const import DISCOVERY_GROUP, DISCOVERY_PORT

def discover(timeout: float = 5.0, iface_ip: str = "0.0.0.0"):
    """Return (device_ip, raw_beacon) for the first announce seen, or None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", DISCOVERY_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(DISCOVERY_GROUP), socket.inet_aton(iface_ip))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.settimeout(timeout)
    try:
        data, (ip, _port) = s.recvfrom(2048)
        return ip, data          # TODO: decode 106-byte beacon fields (serial?, model?)
    except socket.timeout:
        return None
    finally:
        s.close()
