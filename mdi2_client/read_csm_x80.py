#!/usr/bin/env python3
"""Read the CSM / A11 radio (vehicle ECU 0x80) over DoIP through the MDI2,
reproducing the DPS "Get Controller Info / SBI" readout on macOS — no Windows.

Path: macOS -> MDI2 RNDIS gadget (192.168.171.x) -> vehicle DoIP gateway at
192.168.171.70 (logical 0x0C45) -> routed onto CAN to ECU 0x80.

Addressing hypothesis (verified against the gateway itself): GM VIP DoIP logical
address = 0x0C00 | diagnostic_address. Gateway diag 0x45 announces as 0x0C45, so
CSM diag 0x80 -> target 0x0C80. Overridable with --target.

Reads do NOT need 10 03 / 27 first as long as a functional TesterPresent (3E 80)
is kept alive — doipclient does this automatically once activated.
(See ../research/MDI2_DPDU_API_PROTOCOL_AUG2026.md §6 and platform/vehicle_network.md.)

Usage:
  ./.venv/bin/python read_csm_x80.py                 # full SBI-style readout of 0x80
  ./.venv/bin/python read_csm_x80.py --target 0x0C80 # override target logical addr
  ./.venv/bin/python read_csm_x80.py --gateway-ip 192.168.171.70
  ./.venv/bin/python read_csm_x80.py --probe         # just activate + VIN, prove the path
"""
import argparse
import sys

from doipclient import DoIPClient
from doipclient.messages import DiagnosticMessage, DiagnosticMessagePositiveAcknowledgement

GATEWAY_IP = "192.168.171.70"
GATEWAY_LOGICAL = 0x0C45   # DoIP entity address the gateway announces
CLIENT_LOGICAL = 0x0EF5    # tester source address DPS uses
CSM_TARGET = 0x0C80        # 0x0C00 | 0x80 (CSM diag address)

# DID list mirrored from the DPS x80 SBI readout, with decoders.
# name, did, decoder-key
DIDS = [
    ("VIN",                 0xF190, "ascii"),
    ("ECU serial (F18C)",   0xF18C, "ascii"),
    ("Module ID table",     0xF182, "modtable"),
    ("Module IDs (F180)",   0xF180, "hex"),
    ("Module IDs (F181)",   0xF181, "hex"),
    ("End model / part F0B4", 0xF0B4, "ascii"),
    ("Part number F0AB",    0xF0AB, "ascii"),
    ("Broadcast code F0B3", 0xF0B3, "ascii"),
    ("Repair shop code",    0xF198, "ascii"),
    ("Programming date",    0xF199, "bcddate"),
    ("Manuf Enable Counter",0xF1A0, "u8"),
    ("PSI (F0F0)",          0xF0F0, "hex"),
    ("PEC (F0F1)",          0xF0F1, "hex"),
    ("BIS (F0F2)",          0xF0F2, "hex"),
    ("ECUID (F0F3)",        0xF0F3, "hex"),
    ("SBI status F081",     0xF081, "hex"),
]


def decode(kind, data: bytes) -> str:
    if kind == "ascii":
        return data.decode("latin-1").rstrip("\x00 ") + f"   [{data.hex()}]"
    if kind == "u8":
        return f"{data[0]}" if data else "(empty)"
    if kind == "bcddate" and len(data) >= 4:
        return f"{data[0]:02x}{data[1]:02x}-{data[2]:02x}-{data[3]:02x}"
    if kind == "modtable":
        # F182: <count> then 5-byte entries: <mod> <id u24?> <ac 2 bytes ascii>
        out = [f"raw[{len(data)}]={data.hex()}"]
        return "  ".join(out)
    return data.hex()


def read_did(client: DoIPClient, target: int, did: int, timeout=3.0):
    """Send 22 <did> to `target`, return the positive-response payload (bytes)
    or raise with the NRC. Uses raw DiagnosticMessage so we can vary target
    per-request without rebuilding the connection."""
    req = bytes([0x22, (did >> 8) & 0xFF, did & 0xFF])
    client.send_diagnostic(req, target_address=target) if _supports_target(client) \
        else _send_with_target(client, target, req)
    while True:
        msg = client.receive_diagnostic_message(timeout=timeout)
        if msg is None:
            raise TimeoutError(f"no response to 22 {did:04X}")
        payload = bytes(msg.user_data)
        if not payload:
            continue
        if payload[0] == 0x7F:
            nrc = payload[2] if len(payload) > 2 else 0
            raise RuntimeError(f"NRC 0x{nrc:02X} (service 0x{payload[1]:02X})")
        if payload[0] == 0x62 and payload[1:3] == req[1:3]:
            return payload[3:]
        # else: stray frame (e.g. functional TP echo) — keep reading


def _supports_target(client):
    import inspect
    return "target_address" in inspect.signature(client.send_diagnostic).parameters


def _send_with_target(client, target, data):
    # Fallback for doipclient versions whose send_diagnostic has no target arg:
    # build the DiagnosticMessage by hand with our source/target.
    src = client._client_logical_address
    client.send_doip(target, bytes(DiagnosticMessage(src, target, data).pack()
                                   if False else b""))  # placeholder, replaced below


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway-ip", default=GATEWAY_IP)
    ap.add_argument("--gw-logical", type=lambda x: int(x, 0), default=GATEWAY_LOGICAL)
    ap.add_argument("--target", type=lambda x: int(x, 0), default=CSM_TARGET)
    ap.add_argument("--client", type=lambda x: int(x, 0), default=CLIENT_LOGICAL)
    ap.add_argument("--activation-type", type=lambda x: int(x, 0), default=0x00)
    ap.add_argument("--probe", action="store_true", help="activate + read VIN only")
    args = ap.parse_args()

    print(f"Connecting DoIP {args.gateway_ip}  client=0x{args.client:04X} "
          f"gw=0x{args.gw_logical:04X} target=0x{args.target:04X}")
    try:
        client = DoIPClient(
            args.gateway_ip,
            args.gw_logical,
            client_logical_address=args.client,
            activation_type=args.activation_type,
        )
    except Exception as e:
        print(f"!! DoIP connect/activation failed: {e}", file=sys.stderr)
        print("   -> gateway .70 not present? vehicle bus not live, or netmask still /32.",
              file=sys.stderr)
        sys.exit(2)

    print("Routing activation OK.\n")
    dids = DIDS[:1] if args.probe else DIDS
    ok = fail = 0
    for name, did, kind in dids:
        try:
            data = read_did(client, args.target, did)
            print(f"  {name:24s} 0x{did:04X}: {decode(kind, data)}")
            ok += 1
        except Exception as e:
            print(f"  {name:24s} 0x{did:04X}: -- {e}")
            fail += 1
    print(f"\n{ok} read, {fail} failed.")
    client.close()


if __name__ == "__main__":
    main()
