#!/usr/bin/env python3
"""Sweep UDS $27 SecurityAccess requestSeed across levels on ECU 0x80 (A11/CSM),
over DoIP through the MDI2 — to empirically map which levels are open (bypass /
all-0xFF seed) vs locked (real random challenge) vs not implemented (NRC) on
THIS unit, right now. No sendKey is ever issued — this cannot lock out the ECU
or trigger a write; it is a pure read/probe, safe to re-run freely.

Why: the VIP RH850 $27 handler (research/eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md)
tracks a 19-level SecurityAccess unlock bitmask. A prior single $27 probe via
this same MDI2 tooling showed "some levels unlocked, others locked" but was
never swept systematically level-by-level. This script does that sweep and
prints a table, so the result is first-hand/owner-verified rather than
RE-inferred or third-party-claimed.

Path: macOS -> MDI2 RNDIS gadget (192.168.171.x) -> vehicle DoIP gateway ->
routed onto CAN to ECU 0x80. See read_csm_x80.py for the base read-only tool
this borrows its DoIP connection setup from.

STATUS: untested by the owner as of authoring — this is new code, not yet
run against real hardware. Verify against a bench unit before trusting output.

Usage:
  ./.venv/bin/python sweep_security_access.py                  # sweep levels 1-20
  ./.venv/bin/python sweep_security_access.py --min 1 --max 10  # narrower range
  ./.venv/bin/python sweep_security_access.py --target 0x0A80   # override target
  ./.venv/bin/python sweep_security_access.py --gateway-ip 192.168.171.70
"""
import argparse
import sys
import time

from doipclient import DoIPClient

GATEWAY_IP = "192.168.171.70"
GATEWAY_LOGICAL = 0x0C45   # DoIP entity address the gateway announces
CLIENT_LOGICAL = 0x0EF5    # tester source address DPS uses

# NOTE ON TARGET ADDRESS: read_csm_x80.py's CSM_TARGET default (0x0C80, derived
# from a "0x0C00 | diag_addr" hypothesis) is documented there as unverified.
# A real captured DPS session (research/MDI2_DPDU_API_PROTOCOL_AUG2026.md §6,
# live-confirmed) shows ECU 0x80 physically answers as target 0x0A80, response
# source 0x2580. Default here to the live-confirmed value; override with
# --target if this unit differs.
CSM_TARGET = 0x0A80

# Standard UDS NRCs worth naming in output (RFC/ISO 14229 proprietary range
# and common ones only — anything else is printed as a bare hex code).
NRC_NAMES = {
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x22: "conditionsNotCorrect",
    0x24: "requestSequenceError",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceededNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x78: "responsePending",
}


def nrc_name(code: int) -> str:
    return NRC_NAMES.get(code, f"NRC_0x{code:02X}")


def send_recv(client: DoIPClient, target: int, req: bytes, timeout=3.0,
              max_pending_wait=15.0):
    """Send a UDS request to `target`, return the raw response payload bytes.
    Transparently loops on 0x78 responsePending (per this session's own
    established rule: 0x78 means "keep waiting", not failure) up to
    max_pending_wait seconds total. Raises TimeoutError / RuntimeError
    (with the raw NRC byte) otherwise. Does NOT interpret 0x7F as fatal --
    caller decides what a given NRC means for that DID/level."""
    if not _supports_target(client):
        raise RuntimeError(
            "this doipclient version's send_diagnostic has no target_address "
            "kwarg -- upgrade doipclient or add per-target framing here")
    client.send_diagnostic(req, target_address=target)
    deadline = time.monotonic() + max_pending_wait
    while True:
        msg = client.receive_diagnostic_message(timeout=timeout)
        if msg is None:
            raise TimeoutError(f"no response to {req.hex()}")
        payload = bytes(msg.user_data)
        if not payload:
            continue
        if payload[0] == 0x7F:
            svc = payload[1] if len(payload) > 1 else 0
            code = payload[2] if len(payload) > 2 else 0
            if code == 0x78:
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"NRC 0x78 responsePending never resolved within "
                        f"{max_pending_wait}s (service 0x{svc:02X})")
                continue  # keep waiting, this is not a failure
            raise RuntimeError(f"NRC 0x{code:02X} {nrc_name(code)} "
                                f"(service 0x{svc:02X})")
        return payload
        # (positive-response service-ID match is left to the caller;
        #  a stray unrelated frame -- e.g. a functional TesterPresent echo --
        #  would need filtering here if it turns out to be a problem in
        #  practice; not yet observed, flagging as untested)


def _supports_target(client):
    import inspect
    return "target_address" in inspect.signature(client.send_diagnostic).parameters


def session_control_extended(client: DoIPClient, target: int):
    """10 03 -- DiagnosticSessionControl, extendedDiagnosticSession.
    Required before $27 on most GM ECUs (read_csm_x80.py's $22 reads work
    without it per its own docstring, but $27 has not been confirmed to)."""
    resp = send_recv(client, target, bytes([0x10, 0x03]))
    if resp[0] != 0x50 or (len(resp) > 1 and resp[1] != 0x03):
        raise RuntimeError(f"unexpected DiagnosticSessionControl response: {resp.hex()}")
    return resp


def request_seed(client: DoIPClient, target: int, level: int):
    """27 <2*level-1> -- SecurityAccess requestSeed for the given level
    (level 1 -> subfunction 0x01, level 2 -> 0x03, level N -> 2N-1).
    Returns the seed bytes on success (positive response 67 <subfn> <seed>),
    or raises with the NRC. Never sends a key -- read-only by construction."""
    subfn = 2 * level - 1
    if not (0 < subfn <= 0xFF):
        raise ValueError(f"level {level} maps to out-of-range subfunction 0x{subfn:X}")
    req = bytes([0x27, subfn])
    resp = send_recv(client, target, req)
    if resp[0] != 0x67:
        raise RuntimeError(f"unexpected SecurityAccess response: {resp.hex()}")
    if len(resp) > 1 and resp[1] != subfn:
        raise RuntimeError(
            f"subfunction mismatch: sent 0x{subfn:02X}, got 0x{resp[1]:02X} "
            f"in response {resp.hex()}")
    return resp[2:]


def classify_seed(seed: bytes) -> str:
    if not seed:
        return "EMPTY (already unlocked? no seed needed)"
    if all(b == 0xFF for b in seed):
        return f"ALL-0xFF BYPASS ({len(seed)}B) -- likely open/degenerate"
    if all(b == 0x00 for b in seed):
        return f"ALL-ZERO ({len(seed)}B) -- unusual, note and investigate"
    return f"real random-looking challenge ({len(seed)}B): {seed.hex()}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway-ip", default=GATEWAY_IP)
    ap.add_argument("--gw-logical", type=lambda x: int(x, 0), default=GATEWAY_LOGICAL)
    ap.add_argument("--target", type=lambda x: int(x, 0), default=CSM_TARGET)
    ap.add_argument("--client", type=lambda x: int(x, 0), default=CLIENT_LOGICAL)
    ap.add_argument("--activation-type", type=lambda x: int(x, 0), default=0x00)
    ap.add_argument("--min", type=int, default=1, help="lowest level to probe")
    ap.add_argument("--max", type=int, default=20, help="highest level to probe "
                     "(VIP disasm found a 19-level bitmask, levels ~2-20; "
                     "probing 1-20 covers a margin either side)")
    ap.add_argument("--delay", type=float, default=0.3,
                     help="seconds between level probes (be polite to the bus)")
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
        sys.exit(2)

    print("Routing activation OK.")

    try:
        session_control_extended(client, args.target)
        print("Extended diagnostic session established.\n")
    except Exception as e:
        print(f"!! Could not establish extended session: {e}", file=sys.stderr)
        print("   (continuing anyway -- some ECUs allow $27 in default session)",
              file=sys.stderr)

    print(f"{'Level':>5}  {'Subfn':>5}  Result")
    print(f"{'-'*5}  {'-'*5}  {'-'*60}")

    results = []
    for level in range(args.min, args.max + 1):
        subfn = 2 * level - 1
        try:
            seed = request_seed(client, args.target, level)
            verdict = classify_seed(seed)
            print(f"{level:5d}  0x{subfn:02X}   OPEN-ISH: {verdict}")
            results.append((level, "seed_returned", verdict))
        except RuntimeError as e:
            msg = str(e)
            print(f"{level:5d}  0x{subfn:02X}   {msg}")
            results.append((level, "nrc_or_error", msg))
        except TimeoutError as e:
            print(f"{level:5d}  0x{subfn:02X}   TIMEOUT: {e}")
            results.append((level, "timeout", str(e)))
        time.sleep(args.delay)

    client.close()

    opened = [r for r in results if r[1] == "seed_returned"]
    print(f"\n{len(opened)}/{len(results)} levels returned a seed "
          f"(does not by itself mean 'unlocked' -- see classification per row "
          f"above; a real random challenge still needs the key).")


if __name__ == "__main__":
    main()
