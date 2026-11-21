"""Passive device discovery: listen for the 225.1.1.1:8194 announce beacon.

The MDI2 announces itself ~1 Hz on this multicast group. The beacon is
self-identifying: the device serial (the uint32 used to derive the Blowfish
management key, see ``crypto.derive_key``) is a little-endian u32 at byte
offset 9, and the UDP source address is the device's current link IP.

This lets every live entrypoint auto-resolve both ``host`` and ``serial`` from
the wire instead of hard-coding them. That matters in practice: the MDI2's
RNDIS gadget does not always re-appear at the same ``192.168.171.x`` address
across reconnects/power cycles, so a pinned ``DEVICE_IP_DEFAULT`` goes stale.
Resolving host from the beacon source tracks the device wherever it lands.

Offset-9 decode is empirically confirmed, not inferred: the serial it yields
derives the Blowfish key that successfully opens the 9052 management session
and arms the 10123 tunnel. A wrong serial fails the session_open handshake.
"""
import socket
import struct
import subprocess
from dataclasses import dataclass

from .const import DEVICE_IP_DEFAULT, DISCOVERY_GROUP, DISCOVERY_PORT

# device_serial = LE u32 at this byte offset in the announce beacon.
_BEACON_SERIAL_OFFSET = 9
_BEACON_MIN_LEN = _BEACON_SERIAL_OFFSET + 4  # 13 bytes to carry the serial

# The RNDIS link is a /24; the device and this Mac share it. Join multicast on
# the local address in that subnet, not the system default iface (WiFi/en0).
_RNDIS_PREFIX = DEVICE_IP_DEFAULT.rsplit(".", 1)[0] + "."  # "192.168.171."


def _auto_iface_ip(prefix: str = _RNDIS_PREFIX) -> str:
    """Return this host's IPv4 on the MDI RNDIS subnet, or "0.0.0.0" if none.

    The beacon is multicast; macOS joins the group on one interface, chosen by
    the membership address. The MDI is on a USB RNDIS link (its IP is not
    stable), so we pick the local address sharing its /24 rather than relying on
    the default-route interface, where the beacon never arrives.
    """
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True,
                             timeout=4).stdout
    except (OSError, subprocess.SubprocessError):
        return "0.0.0.0"
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("inet ") and prefix in line:
            return line.split()[1]
    return "0.0.0.0"


@dataclass(frozen=True)
class DeviceInfo:
    """A resolved MDI2: its current link IP and serial, plus the raw beacon."""
    ip: str
    serial: int
    beacon: bytes


def decode_beacon(data: bytes) -> int:
    """Return the device serial (uint32) carried by an announce beacon.

    Raises ``ValueError`` if the datagram is too short to carry the serial.
    """
    if not isinstance(data, (bytes, bytearray)) or len(data) < _BEACON_MIN_LEN:
        raise ValueError(
            f"beacon too short to carry a serial: need >= {_BEACON_MIN_LEN} bytes, "
            f"got {len(data) if isinstance(data, (bytes, bytearray)) else type(data).__name__}")
    return struct.unpack_from("<I", data, _BEACON_SERIAL_OFFSET)[0]


def discover(timeout: float = 5.0, iface_ip: str = "0.0.0.0"):
    """Return (device_ip, raw_beacon) for the first announce seen, or None.

    ``iface_ip`` "0.0.0.0" auto-selects this host's address on the MDI RNDIS
    subnet; pass an explicit address to override.
    """
    if iface_ip == "0.0.0.0":
        iface_ip = _auto_iface_ip()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", DISCOVERY_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(DISCOVERY_GROUP), socket.inet_aton(iface_ip))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.settimeout(timeout)
    try:
        data, (ip, _port) = s.recvfrom(2048)
        return ip, data
    except socket.timeout:
        return None
    finally:
        s.close()


def resolve_device(timeout: float = 6.0, iface_ip: str = "0.0.0.0") -> DeviceInfo:
    """Listen for one announce beacon and return the device's IP + serial.

    Raises ``LookupError`` if no beacon arrives within ``timeout`` (device off,
    USB link down, or multicast not reaching this interface), or ``ValueError``
    if a beacon arrives but is too short to carry a serial.
    """
    seen = discover(timeout=timeout, iface_ip=iface_ip)
    if seen is None:
        raise LookupError(
            "no MDI2 announce beacon seen (device off, USB/RNDIS link down, or "
            f"multicast {DISCOVERY_GROUP}:{DISCOVERY_PORT} not reaching iface {iface_ip})")
    ip, data = seen
    return DeviceInfo(ip=ip, serial=decode_beacon(data), beacon=data)
