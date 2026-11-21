# Runtime Interfaces

Scope: internal runtime interfaces of the module as enumerated from the live device — listening
network ports, internal network segments, UART interfaces, and I2C buses.
Related: [`identity_bom.md`](identity_bom.md), [`vip_mcu.md`](vip_mcu.md),
[`../../diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md),
[`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md), [`../teardown.md`](../teardown.md) (index).

Confidence tags: **[C]** confirmed (schematic, label or legible marking) · **[I]** inferred ·
**[FW]** firmware or driver evidence · **[?]** open.

## 1. Listening Ports

Enumerated via ADB.

| Port | Address | Service |
|------|---------|---------------|
| 53 | 127.0.0.1, 192.168.5.1, ::1, fe80:: | DNS (br0 WiFi-AP side) |
| 7000 | 0.0.0.0, [::] | phone-projection (AirPlay/CarPlay), on br0 — LISTENING |
| 6363 | 0.0.0.0 | AVB audio daemon (UID 1041, local IPC) |
| 49156 | 0.0.0.0 | **diagnosticsd** — GM Ethernet UDS-over-TCP bridge, root, on vlan4 (see [`../../diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md)) |
| 9016 | ::ffff:192.168.1.1 | NetworkAccessManager — VM↔host IPC |
| 9002 | ::ffff:192.168.1.1 | RemoteModuleHMI — VM↔host IPC |

Guest's own service listeners (9002/9010/9016 etc.) also bind the guest IP **192.168.1.100**
(eth0/vlan5); the `::ffff:192.168.1.1` binds above are the VM↔host IPC endpoint, not a networked
hypervisor bridge.

## 2. Internal Networks

| Network | Role |
|---------|------|
| 192.168.1.100 | Guest (Android) IP on eth0/vlan5 (driver `igb_avb`) |
| 192.168.1.1 | VM↔host IPC endpoint |
| 192.168.5.x | WiFi AP/hotspot (br0 192.168.5.1/24) |

## 3. UART Interfaces

| Device | Permissions | Notes |
|--------|------------|-------|
| /dev/ttyACM1 | crw-rw-rw- (world) | MCP2200 USB-UART — SXM-associated serial, not a generic debug console (corrected 2026-11-17) |
| /dev/ttyS0 | crw-rw---- bluetooth | Bluetooth HCI |
| /dev/ttyS1 | crw------- root | [C] VIP IPC (HDLC) — live-confirmed as `ipc_serial_device` in [`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md) |
| /dev/ttyS2 | crw------- root | [C] Console (`serial_device`) — live-confirmed in [`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md) |
| /dev/ttyS3 | crw------- root | [C] Display panel (`display_panel_device`) — live-confirmed in [`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md) |

## 4. I2C Buses

11 buses (i2c-0 through i2c-10), consistent across Y175/Y181.

| Bus | Owner | Notes |
|-----|-------|-------|
| i2c-0 | root:root | World-readable |
| i2c-1 | root:root | World-readable |
| i2c-2 | system:system | — |
| i2c-3 | audioserver:audioserver | SAF7751 / TDF8532 control |
| i2c-4 | root | Root-only |
| i2c-5 | root | Root-only |
| i2c-6 | root | Root-only |
| i2c-7 | system:system | — |
| i2c-8 | root | Root-only |
| i2c-9 | root | Root-only |
| i2c-10 | root | Root-only |

## 5. Sources

- ADB enumeration of the live device (listening ports, UART device permissions, I2C bus ownership), Y175/Y181.
- [`../teardown.md`](../teardown.md), "Network Topology (from ADB Enumeration)" section.
- [`../../diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md) — port 49156 detail.
- [`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md) — UART device role confirmation.
