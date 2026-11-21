"""SocketCAN + ISO-TP UDS transport (non-MDI2 bench fallback).

Additive and OPTIONAL. ``python-can`` and ``can-isotp`` are imported lazily
inside the methods that need them, so this module imports cleanly with neither
installed; only ``connect()`` / ``_stack_for()`` require them at runtime.

Implements the ``mdi2.uds_generic.UdsTransport`` protocol (``send_uds`` /
``recv``) plus ``send_broadcast`` for F1B0 discovery, so a ``GenericUdsClient``
or ``ModuleReader`` can run against a Linux SocketCAN interface. 29-bit
normal-fixed GM addressing; ISO-TP stmin=0, blocksize=0.

Ported from carplay/gm_pi/gmtool/gm_transport.py (CANTransport, 215-348).

LIVE-REVALIDATION: untested offline except for import, addressing math and the
not-connected guards. Requires a real SocketCAN bus + hardware to validate.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)

TESTER_ADDR = 0xF1
FUNCTIONAL_REQ_ID = 0x18DB33F1

# ISO-TP stack params (GM bench): send as fast as the bus allows.
ISOTP_PARAMS: Dict[str, int] = {
    "stmin": 0,
    "blocksize": 0,
    "tx_padding": 0x00,
    "rx_consecutive_frame_timeout": 1000,
    "rx_flowcontrol_timeout": 1000,
}


def can_req_id(ecu_addr: int) -> int:
    """Physical request 29-bit id: 0x14DA<ECU><TESTER>."""
    return 0x14DA0000 | (ecu_addr << 8) | TESTER_ADDR


def can_rsp_id(ecu_addr: int) -> int:
    """FALLBACK response-id formula: 0x14DA<TESTER><ECU> (gateway-style 0xDA PF
    byte). WRONG for non-gateway GM modules, whose response id is module-specific
    (0x__5AF1<ecu>, PF byte 0x5A/0x1A/0x4A/0x2A). Prefer ``rsp_id_for`` which
    uses the catalog's authoritative per-ECU ``can_rsp``; this formula is only a
    last resort for addresses absent from the catalog. The low 16 bits
    (0xF1<ecu>) are correct regardless; only the upper bytes are unreliable."""
    return 0x14DA0000 | (TESTER_ADDR << 8) | ecu_addr


# ---------------------------------------------------------------- rxid resolver
# GM response CAN IDs are MODULE-SPECIFIC. The authoritative per-ECU response id
# is the catalog field ``can_rsp`` in mdi2/data/ecu_map.json; the formula above
# is only a fallback. Cache the catalog's {addr: can_rsp} once (static data, no
# secrets). Catalog load failure is non-fatal: fall back to the formula + log.
_RSP_IDS: Optional[Dict[int, int]] = None
_RSP_LOAD_FAILED = False


def _rsp_ids() -> Dict[int, int]:
    global _RSP_IDS, _RSP_LOAD_FAILED
    if _RSP_IDS is None and not _RSP_LOAD_FAILED:
        try:
            from .ecu_catalog import EcuCatalog
            cat = EcuCatalog()
            _RSP_IDS = {addr: info.can_rsp for addr, info in cat.ecus.items()}
        except Exception as e:  # static catalog; a load failure must not be fatal
            _RSP_LOAD_FAILED = True
            _RSP_IDS = {}
            log.warning("ECU catalog unavailable (%s); using 0x14DAF1<ecu> "
                        "response-id formula for all modules", e)
    return _RSP_IDS or {}


def rsp_id_for(ecu_addr: int) -> int:
    """Authoritative ISO-TP rxid for ``ecu_addr``: the catalog's ``can_rsp`` when
    known, else the ``can_rsp_id`` formula (logged — may be wrong for non-gateway
    modules)."""
    rsp = _rsp_ids().get(ecu_addr)
    if rsp is not None:
        return rsp
    fallback = can_rsp_id(ecu_addr)
    log.warning("ECU 0x%02X not in catalog; falling back to formula rxid 0x%08X "
                "(may be wrong for a non-gateway module)", ecu_addr, fallback)
    return fallback


def _known_rsp_ids() -> Set[int]:
    """Set of catalog ``can_rsp`` values, for recognizing discovery responders."""
    return set(_rsp_ids().values())


def recognize_responder(arb_id: int, known: Optional[Set[int]] = None) -> Optional[int]:
    """Return the ECU address if ``arb_id`` is a plausible GM UDS responder, else
    ``None``. A responder matches either the catalog's known ``can_rsp`` set OR
    the module-invariant low 16 bits ``0xF1<ecu>`` (the PF/upper byte is
    module-specific, so a single broad upper-byte mask is unreliable).

    LIVE-REVALIDATION: the low-16 heuristic can admit a non-UDS frame carrying
    those two low bytes; validate on bench traffic and tighten to the catalog-set
    match alone if false positives occur."""
    if known is None:
        known = _known_rsp_ids()
    if arb_id in known or (arb_id & 0xFF00) == 0xF100:
        return arb_id & 0xFF
    return None


class CanDependencyError(RuntimeError):
    """python-can / can-isotp is required for this operation but not installed."""


class CANTransport:
    """ISO-TP over SocketCAN, 29-bit extended IDs. One ISO-TP stack per ECU."""

    def __init__(self, interface: str, bitrate: int = 500000, timeout: float = 5.0):
        self.interface = interface
        self.bitrate = bitrate
        self.timeout = timeout
        self.bus = None
        self._stacks: Dict[int, object] = {}
        self.connected = False
        # Re-entrant lock serializing ALL bus/stack access. python-can and
        # can-isotp are not thread-safe: the keepalive (tester-present) thread
        # and a read loop drive the same stacks, so without this they could
        # interleave ISO-TP segments. Re-entrant so send_broadcast can call
        # send_uds while holding it.
        self._lock = threading.RLock()

    def connect(self) -> bool:
        try:
            import can
        except ImportError:
            return False
        with self._lock:
            try:
                self.bus = can.interface.Bus(channel=self.interface,
                                             bustype="socketcan", bitrate=self.bitrate)
                self.connected = True
                return True
            except (OSError, ValueError) as e:
                # Interface down / bad channel / bad bitrate: recoverable.
                self._stacks.clear()
                self.bus = None
                self.connected = False
                log.warning("CAN connect failed on %s: %s", self.interface, e)
                return False

    def _stack_for(self, ecu_addr: int):
        if ecu_addr in self._stacks:
            return self._stacks[ecu_addr]
        try:
            import isotp
        except ImportError as e:
            raise CanDependencyError("can-isotp not installed") from e
        addr = isotp.Address(addressing_mode=isotp.AddressingMode.Normal_29bits,
                             txid=can_req_id(ecu_addr), rxid=rsp_id_for(ecu_addr))
        try:
            stack = isotp.CanStack(bus=self.bus, address=addr, params=dict(ISOTP_PARAMS))
        except TypeError:
            p = isotp.Params()
            for k, v in ISOTP_PARAMS.items():
                setattr(p, k, v)
            stack = isotp.CanStack(bus=self.bus, address=addr, params=p)
        self._stacks[ecu_addr] = stack
        return stack

    def disconnect(self) -> None:
        with self._lock:
            self._stacks.clear()
            if self.bus:
                try:
                    self.bus.shutdown()
                except Exception:
                    pass
                self.bus = None
            self.connected = False

    # Programming errors we must NOT swallow as a transport "no response" — a
    # typo or contract violation here is a bug in our code, not a bus failure.
    _PROG_ERRORS = (TypeError, AttributeError, NameError, KeyError, IndexError,
                    AssertionError)

    def _flush_rx(self, stack) -> None:
        """Drain any already-buffered RX on this stack before a new request so a
        late response to a prior (timed-out) request is not returned for the next
        one. Bounded; best-effort."""
        try:
            for _ in range(8):
                stack.process()
                if not stack.available():
                    break
                stack.recv()
        except self._PROG_ERRORS:
            raise
        except Exception:
            pass

    def send_uds(self, ecu_addr: int, data: bytes,
                 timeout: Optional[float] = None) -> Optional[bytes]:
        if not self.connected:
            return None
        # _stack_for may raise CanDependencyError (can-isotp missing) — let it
        # propagate so callers can map it to a clean "install ..." message.
        with self._lock:
            stack = self._stack_for(ecu_addr)
            end = time.time() + (timeout or self.timeout)
            try:
                self._flush_rx(stack)
                stack.send(bytes(data))
                while time.time() < end:
                    stack.process()
                    if stack.available():
                        r = stack.recv()
                        return bytes(r) if r else None
                    time.sleep(0.001)
                return None
            except CanDependencyError:
                self._stacks.pop(ecu_addr, None)
                raise
            except self._PROG_ERRORS:
                self._stacks.pop(ecu_addr, None)
                raise
            except Exception as e:
                # Transport-level failure: drop the (possibly wedged) stack so the
                # next request rebuilds it, and report no-response.
                self._stacks.pop(ecu_addr, None)
                log.warning("send_uds 0x%02X transport error: %s", ecu_addr, e)
                return None

    def recv(self, ecu_addr: int, timeout: Optional[float] = None) -> Optional[bytes]:
        if not self.connected:
            return None
        with self._lock:
            stack = self._stack_for(ecu_addr)
            end = time.time() + (timeout or self.timeout)
            try:
                while time.time() < end:
                    stack.process()
                    if stack.available():
                        r = stack.recv()
                        return bytes(r) if r else None
                    time.sleep(0.001)
                return None
            except CanDependencyError:
                self._stacks.pop(ecu_addr, None)
                raise
            except self._PROG_ERRORS:
                self._stacks.pop(ecu_addr, None)
                raise
            except Exception as e:
                self._stacks.pop(ecu_addr, None)
                log.warning("recv 0x%02X transport error: %s", ecu_addr, e)
                return None

    def send_broadcast(self, data: bytes, timeout: float = 2.0) -> List[Tuple[int, bytes]]:
        """Functional F1B0 discovery: broadcast, harvest responders, then do a
        clean physical read of each. Best-effort.

        A responder is recognized by matching the catalog's known ``can_rsp`` set
        OR the module-invariant low 16 bits ``0xF1<ecu>`` (the upper/PF byte is
        module-specific — 0x5A/0x1A/0x4A/0x2A, 0xDA only for the gateway — so a
        single broad upper-byte mask is unreliable).

        LIVE-REVALIDATION: the low-16 ``0xF1<ecu>`` heuristic can in principle
        admit a non-UDS frame that happens to carry those two low bytes; it has
        NOT been validated against real bench traffic. Revalidate on hardware and
        tighten to the catalog-set match if false positives appear.
        """
        if not self.connected:
            return []
        import can
        with self._lock:
            payload = (bytes([len(data)]) + bytes(data)).ljust(8, b"\x00")
            self.bus.send(can.Message(arbitration_id=FUNCTIONAL_REQ_ID,
                                      data=payload, is_extended_id=True))
            known = _known_rsp_ids()
            responders: Set[int] = set()
            end = time.time() + timeout
            while time.time() < end:
                msg = self.bus.recv(timeout=0.1)
                if msg is None:
                    continue
                ecu = recognize_responder(msg.arbitration_id, known)
                if ecu is not None:
                    responders.add(ecu)
            results: Dict[int, bytes] = {}
            for ecu in sorted(responders):
                resp = self.send_uds(ecu, data, timeout=1.0)
                if resp:
                    results[ecu] = resp
            return list(results.items())
