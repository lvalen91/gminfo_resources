"""DPS-style multi-ECU "Read" / "Read All" operation (additive, generic).

Reproduces what GM DPS does on a module Read, over any ``UdsTransport``:
  1. (read-all) wake the bus with the GM network-management frame
  2. (read-all) discover present ECUs via F1B0 broadcast, else per-node probe
  3. per ECU: extended session -> optional SecurityAccess -> standard DID read
     -> SW-inventory + ECUID parse
  4. return ``EcuRead`` objects.

Separate from the radio-specific live write path. Ported from
carplay/gm_pi/gmtool/gm_module_reader.py, retargeted onto ``mdi2.ecu_catalog``,
``mdi2.uds_generic`` and ``mdi2.security_cmac``.

LIVE-REVALIDATION: WAKE_NM_CAN_ID / WAKE_NM_FRAME, the F1B0 discovery and the
per-node probe are best-effort and only exercised here against fake transports.
They must be revalidated on a vehicle/bench before being trusted live.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from .can_transport import CanDependencyError
from .ecu_catalog import DidResult, EcuCatalog, EcuInfo
from .uds_generic import (GenericUdsClient, UDSError, UDSLockout,
                          UDSNegativeResponse, UDSTimeout, parse_sw_inventory)

# GM network-management wake frame (DPS_MASTER_REFERENCE / task spec).
WAKE_NM_FRAME = bytes([0x00, 0x00, 0x01, 0x45, 0x45, 0x50, 0x80,
                       0x00, 0x00, 0x00, 0x00, 0x00])
WAKE_NM_CAN_ID = 0x10400000  # GM NM functional id (best-effort; ECU-agnostic)

# Standard DID set DPS reads for every module.
STANDARD_DIDS = [
    0xF190, 0xF180, 0xF181, 0xF182, 0xF187, 0xF198, 0xF199, 0xF1A0,
    0xF09A, 0xF0AB, 0xF0B3, 0xF0B4, 0xF0F3, 0xF0F4, 0xF081,
]


@dataclass
class EcuRead:
    info: EcuInfo
    security_unlocked: bool = False
    dids: List[DidResult] = field(default_factory=list)
    sw_inventory: List[str] = field(default_factory=list)
    ecuid: Optional[str] = None
    vin: Optional[str] = None
    error: Optional[str] = None

    def did(self, did: int) -> Optional[DidResult]:
        for d in self.dids:
            if d.did == did:
                return d
        return None


class ModuleReader:
    def __init__(self, transport, security=None,
                 catalog: Optional[EcuCatalog] = None,
                 verbose: bool = False, keepalive: bool = True):
        self.transport = transport
        self.security = security
        self.catalog = catalog or EcuCatalog()
        self.verbose = verbose
        self.keepalive = keepalive

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    # ------------------------------------------------------------ bus wake
    def wake_bus(self) -> None:
        """Send the GM NM wake frame on a raw-CAN transport; no-op otherwise."""
        bus = getattr(self.transport, "bus", None)
        if bus is None:
            self._log("[i] wake_bus: skipped (no raw CAN bus / link already active)")
            return
        try:
            import can
            bus.send(can.Message(arbitration_id=WAKE_NM_CAN_ID,
                                 data=WAKE_NM_FRAME, is_extended_id=True))
            self._log("[i] Sent NM wake frame")
            time.sleep(0.2)
        except Exception as e:
            self._log(f"[!] wake_bus failed: {e}")

    # ------------------------------------------------------------ discovery
    def discover(self) -> List[int]:
        present: List[int] = []
        send_broadcast = getattr(self.transport, "send_broadcast", None)
        if send_broadcast is not None:
            try:
                for addr, _ in send_broadcast(bytes([0x22, 0xF1, 0xB0]), timeout=2.0):
                    if addr not in present:
                        present.append(addr)
            except CanDependencyError:
                # can-isotp missing: no transport can work. Surface cleanly to
                # the caller (cli maps it to the install message + Exit(1))
                # rather than letting it look like an empty bus.
                raise
            except Exception as e:
                self._log(f"[!] broadcast discovery failed: {e}")
        if present:
            self._log(f"[+] Broadcast found {len(present)} ECUs")
            return sorted(present)

        self._log("[i] Falling back to per-node probe")
        for addr in self.catalog.all_addrs():
            client = GenericUdsClient(self.transport, addr, verbose=False)
            try:
                client.tester_present()
                client.read_did(0xF190)
                present.append(addr)
                self._log(f"  [+] 0x{addr:02X} {self.catalog.ecu_name(addr)} present")
            except CanDependencyError:
                # Dependency, not a per-node miss: abort the probe and propagate.
                raise
            except UDSNegativeResponse:
                present.append(addr)
                self._log(f"  [+] 0x{addr:02X} present (NRC)")
            except (UDSTimeout, UDSError):
                pass
        return sorted(present)

    # ------------------------------------------------------------ read one
    def read_ecu(self, addr: int, do_security: bool = True) -> EcuRead:
        info = self.catalog.ecu(addr) or EcuInfo(
            addr=addr, name="Unknown", desc="Unknown ECU", can_req=0, can_rsp=0)
        read = EcuRead(info=info)
        client = GenericUdsClient(self.transport, addr, verbose=self.verbose)

        try:
            try:
                client.enter_extended()
            except (UDSNegativeResponse, UDSTimeout) as e:
                self._log(f"  [!] 0x{addr:02X} extended session: {e}")

            if self.keepalive:
                client.start_tester_present()

            if do_security and self.security is not None:
                try:
                    if client.security_access(self.security, level=0x01):
                        read.security_unlocked = True
                        self._log(f"  [+] 0x{addr:02X} security unlocked")
                except UDSLockout as e:
                    self._log(f"  [!] 0x{addr:02X} security locked out: {e}")
                except Exception as e:
                    self._log(f"  [!] 0x{addr:02X} security error: {e}")

            for did in STANDARD_DIDS:
                raw = None
                supported = True
                try:
                    raw = client.read_did(did)
                except UDSNegativeResponse:
                    supported = False
                except (UDSTimeout, UDSError):
                    supported = False
                decoded = self.catalog.decode(did, raw) if raw is not None else None
                read.dids.append(DidResult(did=did, name=self.catalog.did_name(did),
                                           raw=raw, decoded=decoded, supported=supported))
                if did == 0xF190 and raw:
                    read.vin = decoded
                if did == 0xF0F3 and raw:
                    read.ecuid = raw.hex().upper()
                if did == 0xF1A0 and raw:
                    read.sw_inventory = [m.part_number for m in parse_sw_inventory(raw)]

            if not read.sw_inventory:
                f182 = read.did(0xF182)
                if f182 and f182.raw:
                    read.sw_inventory = [m.part_number for m in parse_sw_inventory(f182.raw)]
        except Exception as e:
            read.error = str(e)
        finally:
            client.stop_tester_present()
        return read

    # ------------------------------------------------------------ read all
    def read_all(self, addrs: Optional[List[int]] = None,
                 do_security: bool = True) -> List[EcuRead]:
        self.wake_bus()
        if addrs is None:
            addrs = self.discover()
            if not addrs:
                self._log("[!] discovery empty; reading full ECU map")
                addrs = self.catalog.all_addrs()
        reads: List[EcuRead] = []
        for addr in addrs:
            self._log(f"[*] Reading 0x{addr:02X} {self.catalog.ecu_name(addr)}")
            reads.append(self.read_ecu(addr, do_security=do_security))
        return reads
