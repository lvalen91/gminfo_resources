"""Central configuration for the GM Info 3.7 bench dashboard backend.

LAN-only, no authentication (owner's explicit choice for this home-lab bench).
Nothing here reaches the public internet. All addresses/ports are the bench's own.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Filesystem layout on the Pi -------------------------------------------------
REPO_TOOLS = Path(os.environ.get("GMINFO_TOOLS", "/opt/pibench/tools/bench"))
BENCH_CAN_DIR = REPO_TOOLS / "bench_can"
CALTOOL_DIR = Path(os.environ.get("GMINFO_CALTOOL", "/opt/pibench/tools/calibration_toolkit"))
GMINFO_REPO_ROOT = Path(os.environ.get("GMINFO_REPO_ROOT", "/opt/pibench/repo"))
BENCH_PYTHON = os.environ.get("BENCH_PYTHON", "/opt/pibench/venv/bin/python")
HARNESS_PROFILE = Path(os.environ.get("HARNESS_PROFILE", "/var/lib/pibench/harness-profile.json"))
UPLOAD_DIR = Path(os.environ.get("DASH_UPLOAD_DIR", "/var/lib/pibench/uploads"))
LTZ_REF_DIR = Path(os.environ.get("LTZ_REF_DIR", "/var/lib/pibench/ltz_stock_cal"))
# Staging dir for an uploaded calibration-package .zip. The zip is a convenience carrier
# for the SAME verified containers (each must match a known stock part + digest); there is
# deliberately NO custom-calibration directory or source selector - custom cal is not a
# supported option on this bench.
PKG_STAGE_DIR = Path(os.environ.get("PKG_STAGE_DIR", "/var/lib/pibench/cal_pkg_stage"))
ELK_IMAGE_DIR = Path(os.environ.get("ELK_IMAGE_DIR", "/var/lib/pibench/elk_images"))

# --- CAN ------------------------------------------------------------------------
CAN_IFACE = os.environ.get("CAN_IFACE", "can0")
KEEPALIVE_UNIT = "pibench-can-keepalive.service"
CAN0_UNIT = "pibench-can0.service"

# --- diagnosticsd UDS-over-TCP (vlan4) ------------------------------------------
# Custom GM 8-byte big-endian header: [SRC:2][TGT:2][LEN:4] + raw UDS (NOT DoIP).
# diagnostics/diagnosticsd_protocol.md:39-55; endpoint diagnosticsd_network_topology.md:33-37.
DIAG_HOST = os.environ.get("DIAG_HOST", "172.16.4.100")
DIAG_PORT = int(os.environ.get("DIAG_PORT", "49156"))
DIAG_SRC_BIND = os.environ.get("DIAG_SRC_BIND", "172.16.4.107")  # allow-listed source (platform/vehicle_network.md:268)
UDS_TESTER = 0x00F4   # validated logical tester (diagnosticsd_protocol.md:48-50)
UDS_ECU = 0x0084      # ECU/target address (diagnosticsd_protocol.md:51-53)
VLAN4_IFACE = "eth0.4"
VLAN5_IFACE = "eth0.5"
T1_RADIO_IP = "192.168.1.100"      # radio VLAN5 address
T1_ADB_ENDPOINT = "192.168.1.100:9040"

# --- UART via ser2net (loopback TCP). Backend is a CLIENT of this. --------------
# Owner-confirmed on real hardware: /dev/ttyS0 @ 115200 8N1 is the RH850 VIP console
# (hardware/module/vip_mcu.md: pin 52/P1_9/RLIN34TX), observed receiving real traffic
# (e.g. "[334572][I][J6_CDD] IOC_Main_Temp : 2673"). ttyS1 does not exist on this Pi
# (ser2net reports "Device open failure" and closes immediately), and 9600/19200 on
# ttyS0 produced only unreadable output -- both are dead guesses, not alternatives,
# so only the one confirmed-working port is listed. Add a sibling entry here only for
# a genuinely separate, real device -- never another baud-rate guess at this same signal.
UART_PORTS = [
    {"id": "A115200", "label": "VIP console (ttyS0 @ 115200)", "host": "127.0.0.1", "port": 4000, "dev": "ttyS0", "baud": 115200},
]

# --- adb ------------------------------------------------------------------------
ADB = os.environ.get("ADB", "adb")

# --- server ---------------------------------------------------------------------
BIND_HOST = os.environ.get("DASH_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("DASH_PORT", "8088"))
