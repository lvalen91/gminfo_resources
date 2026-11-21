#!/usr/bin/env bash
#
# calibrate_ltz.sh — unattended-fallback driver for the gated LTZ calibration write.
#
# Wraps the mdi2.cli commands into one run: fixes the RNDIS netmask, confirms
# management health, identifies the radio, runs the gate dry-run, and — only
# with --write AND a typed-VIN confirmation — performs the single live write.
#
# This is a convenience wrapper. It adds NO protocol logic and bypasses NO gate:
# every safety check lives in mdi2/live_calibration.py and still runs. Use it
# when the operator must drive the write without an assistant available.
#
# Usage:
#   scripts/calibrate_ltz.sh [--write] [--pre-reset] <LTZ_FOLDER> <EXPECTED_VIN> [MDI2_SERIAL]
#
#   (no flag) prereqs + identify + DRY-RUN plan only (writes nothing).
#   --write   after the dry-run passes, prompt to type the VIN, then live-write.
#   --pre-reset   opt-in recovery fallback only (NOT stock SPS); passed through.
#
# Run from the mdi2_client directory. It self-elevates ONLY the netmask step via
# sudo; the Python client runs as the invoking user. Prints to stdout only — it
# writes no log files (logs can carry private identifiers).
#
set -euo pipefail

# --- locate the client + venv (script lives in mdi2_client/scripts/) ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$CLIENT_DIR/.venv/bin/python"
cd "$CLIENT_DIR"
[ -x "$PY" ] || { echo "FATAL: venv python not found at $PY" >&2; exit 2; }

run_cli() { "$PY" -B -m mdi2.cli "$@"; }
die() { echo "ABORT: $*" >&2; exit 1; }

# --- parse args ---------------------------------------------------------------
DO_WRITE=0; PRE_RESET=0; POS=()
for a in "$@"; do
  case "$a" in
    --write)     DO_WRITE=1 ;;
    --pre-reset) PRE_RESET=1 ;;
    --*)         die "unknown flag: $a" ;;
    *)           POS+=("$a") ;;
  esac
done
[ "${#POS[@]}" -ge 2 ] || die "usage: calibrate_ltz.sh [--write] [--pre-reset] <LTZ_FOLDER> <EXPECTED_VIN> [MDI2_SERIAL]"
LTZ_FOLDER="${POS[0]}"; EXPECTED_VIN="${POS[1]}"; MDI2_SERIAL="${POS[2]:-}"
[ -d "$LTZ_FOLDER" ] || die "LTZ folder not found: $LTZ_FOLDER"
[ "${#EXPECTED_VIN}" -eq 17 ] || die "expected VIN must be exactly 17 characters (got ${#EXPECTED_VIN})"

echo "=== MDI2 LTZ calibration driver ==="
echo "client:   $CLIENT_DIR"
echo "package:  $LTZ_FOLDER"
echo "VIN:      ${EXPECTED_VIN:0:3}<redacted>"
echo "mode:     $([ "$DO_WRITE" -eq 1 ] && echo 'WRITE (gated)' || echo 'dry-run only')"
echo

# --- step 0: RNDIS interface + /24 netmask (reverts to /32 on every replug) ----
echo "[0/4] RNDIS link"
RNDIS_IF="$(networksetup -listallhardwareports 2>/dev/null \
  | awk '/RNDIS\/Ethernet Gadget/{getline; print $2; exit}')"
[ -n "$RNDIS_IF" ] || die "no RNDIS/Ethernet Gadget interface found (MDI2 powered + USB connected?)"
LINK_IP="$(ifconfig "$RNDIS_IF" 2>/dev/null | awk '/inet /{print $2; exit}')"
[ -n "$LINK_IP" ] || die "$RNDIS_IF has no IPv4 address (DHCP from the MDI2 not seen yet)"
echo "      interface $RNDIS_IF at $LINK_IP — setting /24"
sudo ifconfig "$RNDIS_IF" inet "$LINK_IP" netmask 255.255.255.0
route -n get 2>/dev/null "$(echo "$LINK_IP" | sed 's/\.[0-9]*$/.2/')" >/dev/null 2>&1 || true

# --- step 1: discovery + 9052 management health -------------------------------
echo "[1/4] discovery + 9052 health"
run_cli scan || die "discovery failed (see 'no device seen' / beacon errors above)"
"$PY" -B - <<'PYCODE' || die "9052 session service not healthy — stop, let sessions drain, retry; USB power-cycle only as last resort"
from mdi2.discovery import resolve_device
from mdi2.crypto import derive_key
from mdi2.transport import Session
d = resolve_device()
with Session(derive_key(d.serial), d.ip).connect(ports=[9052]) as s:
    reply = s.channels[9052]._ctrl_reply
    if not reply:
        raise SystemExit("9052 control handshake returned NONE")
    print("      9052 control reply OK")
PYCODE

# --- step 2: arm tunnel + READ-ONLY identify ----------------------------------
echo "[2/4] identify (read-only)"
if [ -n "$MDI2_SERIAL" ]; then run_cli identify "$MDI2_SERIAL"; else run_cli identify; fi \
  || die "identify failed — radio not reachable / tunnel not armed (check radio power + CAN)"

# --- step 3: DRY-RUN plan (validates every gate, writes nothing) --------------
echo "[3/4] dry-run plan (all gates, no write)"
if [ -n "$MDI2_SERIAL" ]; then
  run_cli write "$LTZ_FOLDER" "$EXPECTED_VIN" "$MDI2_SERIAL"
else
  run_cli write "$LTZ_FOLDER" "$EXPECTED_VIN"
fi || die "dry-run gate FAILED (hashes / source profile / VIN / BCM F085=00 / voltage) — do not write"

# --- step 4: live write (only with --write AND typed-VIN confirmation) ---------
if [ "$DO_WRITE" -ne 1 ]; then
  echo
  echo "[4/4] dry-run complete. Gates passed. Re-run with --write to perform the single live write."
  exit 0
fi

echo
echo "[4/4] LIVE WRITE — this flashes radio 0x80 and resets it. This is hard to reverse."
echo "      Service Mode is NOT the gate: the write requires BCM F085 = 00, already checked above."
printf "      Type the full 17-char VIN to proceed (anything else aborts): "
read -r CONFIRM_VIN
[ "$CONFIRM_VIN" = "$EXPECTED_VIN" ] || die "VIN confirmation did not match — no write performed"

PRE_FLAG=(); [ "$PRE_RESET" -eq 1 ] && PRE_FLAG=(--pre-reset)
echo "      confirmed — performing the single live write"
if [ -n "$MDI2_SERIAL" ]; then
  run_cli write "$LTZ_FOLDER" "$EXPECTED_VIN" "$MDI2_SERIAL" --confirm ${PRE_FLAG[@]+"${PRE_FLAG[@]}"}
else
  run_cli write "$LTZ_FOLDER" "$EXPECTED_VIN" --confirm ${PRE_FLAG[@]+"${PRE_FLAG[@]}"}
fi
echo "=== done — verify the WRITE/readback line above shows matched slots ==="
