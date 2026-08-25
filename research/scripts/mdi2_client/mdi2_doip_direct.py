#!/usr/bin/env python3
"""Direct DoIP client to the vehicle's own gateway ECU, bypassing the MDI2's
D-PDU/10123 low-port unlock dance entirely (see AUG24_SESSION_FULL_PCAP_TIMELINE.md
finding #1 and MDI2_DPDU_API_PROTOCOL_AUG2026.md).

Confirmed from capture_attempt2.pcapng (frames 393-400), the real tablet talks
standards-compliant ISO 13400 DoIP directly to 192.168.171.70:13400 with:
  - client logical address:  0x0EF5
  - gateway logical address: 0x0C45  (routing-activation response source)
  - functional broadcast:    0xEFFE  (TesterPresent target)

Uses jacobschaer/python-doipclient for the DoIP transport and pylessard/udsoncan
for UDS request/response parsing, instead of hand-rolled framing.

Run:  <venv>/bin/python3 mdi2_doip_direct.py
Requires a vehicle connected through the MDI2 (not just the MDI2 itself) — the
gateway at .70 only appears once the vehicle bus is live.
"""
import logging

from doipclient import DoIPClient
from doipclient.connectors import DoIPClientUDSConnector
import udsoncan
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

logging.basicConfig(level=logging.INFO)

VEHICLE_GATEWAY_IP = "192.168.171.70"
CLIENT_LOGICAL_ADDRESS = 0x0EF5
GATEWAY_LOGICAL_ADDRESS = 0x0C45

CONFIG = dict(udsoncan.configs.default_client_config)
CONFIG["data_identifiers"] = {
    0xF190: udsoncan.AsciiCodec(17),  # VIN
    0xF1B0: "raw",
}


def main():
    doip_layer = DoIPClient(
        VEHICLE_GATEWAY_IP,
        GATEWAY_LOGICAL_ADDRESS,
        client_logical_address=CLIENT_LOGICAL_ADDRESS,
    )
    conn = DoIPClientUDSConnector(doip_layer)

    with Client(conn, config=CONFIG, request_timeout=5) as client:
        try:
            client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
            print("Extended session: OK")
        except (NegativeResponseException, TimeoutException) as e:
            print("Extended session failed:", e)
            return

        try:
            resp = client.read_data_by_identifier(0xF190)
            print("VIN:", resp.service_data.values.get(0xF190))
        except (NegativeResponseException, TimeoutException) as e:
            print("VIN read failed:", e)

        try:
            seed_resp = client.request_seed(1)
            print("SecurityAccess seed:", seed_resp.service_data.seed.hex())
        except (NegativeResponseException, TimeoutException) as e:
            print("Seed request failed (expected without a real key algorithm):", e)

    doip_layer.close()


if __name__ == "__main__":
    main()
