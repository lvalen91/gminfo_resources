# Current bench: Raspberry Pi host (2026-11-25 onward)

**Status:** current. Supersedes [bench_setup.md](bench_setup.md) (the earlier
macOS-host, direct-adapter phase) as the live bench configuration. That
document's wiring/adapter facts are historical; this one is the current
process state.

## Host

Raspberry Pi 4, PiOS. Dashboard backend (FastAPI/uvicorn) and the UART tap run
as services on the Pi; static UI served by nginx. See
[tools/bench/pi_dashboard/](../../tools/bench/pi_dashboard/) for the
implementation and [deploy/](../../tools/bench/pi_dashboard/deploy/) for the
systemd units and nginx config. Owner-stated: the Pi reaches the owner's
home-lab network over a separate Ethernet connection, for SSH/dashboard
access — distinct from the automotive T1 link below. This management
connection's exact adapter/interface is not otherwise documented in this
repo.

## Adapters and wiring (owner-stated)

| Function | Adapter | Connection |
|---|---|---|
| CAN 5 | CANable (`gs_usb`, SocketCAN `can0`) | USB to the Pi; see [config.py](../../tools/bench/pi_dashboard/backend/config.py) `CAN_IFACE` |
| Automotive Ethernet (T1) | T1-to-RJ45 media converter | Converter to the Pi's onboard Ethernet (`eth0`); independently verified in this session's T1 captures: tagged VLAN 2 (AVTP/AVB), untagged gPTP, tagged VLAN 4 (diagnostics, 172.16.4.0/24), tagged VLAN 5 (radio ADB, 192.168.1.0/24) |
| VIP console (UART) | Pi GPIO UART | Pi UART RX wired to the radio VIP's UART TX output (RX-only, as in the prior macOS-phase baseline — the Pi does not transmit on this line) |
| ADB | USB cable | Direct USB between the Pi and the radio |
| Home-lab network | Separate Ethernet adapter | Pi to the owner's home-lab network, for SSH/dashboard management access |

This table reflects the owner's own description of the current physical
setup. No independent photographic or continuity-test verification of the
physical wiring (beyond the T1/VLAN capture evidence noted above) is recorded
in this repo.

## What is not yet documented here

- Exact CANable/converter/adapter model numbers and part identities.
- GPIO pin assignment for the UART tap (the radio-side VIP UART pin is
  tracked separately in [module/vip_mcu.md](../module/vip_mcu.md)).
- Home-lab network adapter identity and addressing.

## Related

- [bench_setup.md](bench_setup.md) — superseded macOS-host baseline (adapter
  acceptance checks, UART/CAN protocol settings that still apply to the
  adapters themselves, not the host).
- [tools/bench/pi_dashboard/](../../tools/bench/pi_dashboard/) — dashboard
  implementation (backend, static UI, deploy units).
- [platform/can_network.md](../../platform/can_network.md),
  [platform/can_bench_experiments.md](../../platform/can_bench_experiments.md)
  — CAN message dictionary and experiment log, both now driven from this
  bench.
- [research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md](../../research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md)
  — tool-chain history (DPS → MDI2 → this Canable bench) for the
  calibration-write work.
