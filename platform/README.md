# GM Info 3.7 Platform Reference

Intel Apollo Lake (Broxton) radio, Android 12 / AAOS guest under GHS INTEGRITY, Y175 / Y177 / Y181(B) builds. One document per topic; each doc states its scope, what it does not cover, and links the owner of anything it only points at. Cross-topic facts live in exactly one doc.

Evidence tags (`[C]` confirmed live, `[V]` verified, `[FW]`/`[S]` static firmware, `[inferred]`, `[U]` unverified, `[X]` external) are defined at the top of each doc; dated per-claim tags override surrounding prose. Contradictions between sources that no dated correction settles are kept, with citations, in each doc's "Open conflicts" section.

## Documents

### Hardware and platform
| Doc | Contents |
|---|---|
| [hardware_specs.md](../hardware/specs.md) | SoC, GPU, RAM, storage, display panel, audio/codec, USB, thermal, power, UART console map, I2C topology, Intel A3960 datasheet facts |
| [vip_ipc_ghs.md](vip_ipc_ghs.md) | RH850 VIP MCU, PLC/calibration data, VIP-SoC IPC channels, GHS INTEGRITY hypervisor, `/dev/ghs`, VP-crash decode |
| [eeprom_i2c_security.md](eeprom_i2c_security.md) | Pointer to `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` (EEPROM map, I2C-bus permissions, attack surface) plus platform-specific live `[C]` capture citations |
| [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md) | Qualcomm SA8155P / QNX Cadillac radio vs this Intel unit (external, `[X]`) |

### Boot, storage, recovery
| Doc | Contents |
|---|---|
| [boot_chain.md](boot_chain.md) | Boot phases, GHS init tasks, boot modes, cmdline, AVB flow, A/B + BCB, signing hierarchy, boot timing |
| [partitions_storage.md](partitions_storage.md) | eMMC/GPT map, `super`/dynamic partitions (measured), first-stage mounts, filesystem sizes |
| [elk_recovery.md](elk_recovery.md) | ELK/kernelflinger, lock state and Boot Guard/TXE forensics, recovery/fastbootd, native-Linux probe bring-up |
| [firmware_versions.md](firmware_versions.md) | Y175/Y177/Y181B comparison, build strings, fingerprints, patch levels, kernels, part numbers, slot history |

### Networks and protocols
| Doc | Contents |
|---|---|
| [ethernet_networking.md](ethernet_networking.md) | Interfaces, backbone switch, VLAN 4/5 maps, listening ports, network ADB, mDNS, WiFi/BT |
| [avb_audio_transport.md](avb_audio_transport.md) | gPTP, AVTP AAF streams on VLAN 2, usage-to-bus mapping, firmware audio stack |
| [vehicle_network.md](vehicle_network.md) | Two-plane vehicle topology: ECU census, gateway/radio IDs, Ethernet plane map, SecOC, join points |
| [can_network.md](can_network.md) | CAN message dictionary: verified signals, firmware RX/TX config, ID inventories, DBC comparison |
| [can_bench_experiments.md](can_bench_experiments.md) | Chronological CAN bench log: calibration writes, factory-reset/ELK probing, boot/door/wake behaviour, ADB-enable and keep-alive campaign |
| [fsa_protocol.md](fsa_protocol.md) | FSA/NFSA wire format, service catalog, protobuf definitions, live sessions, parser/auth findings |

### Update and programming
| Doc | Contents |
|---|---|
| [ota_update_stack.md](ota_update_stack.md) | UpdateService Binder map, SWU state machine, package format/signing, update engine, USB install path. **Not yet consolidated** (see Status) |
| [ota_programming_roles.md](ota_programming_roles.md) | Who reflashes what (ProgrammingMaster / CGM / VIP), DPS module IDs, package inventory, CalDef evidence |

### Security
| Doc | Contents |
|---|---|
| [security.md](security.md) | SELinux, FBE, Trusty, kernel hardening, CVEs, ProtoKey/ADB auth, service findings, host firewall segmentation |

### Vehicle configuration, UI, emulation
| Doc | Contents |
|---|---|
| [vehicle_config.md](vehicle_config.md) | Donor vehicle, RPO to calibration map, CalSets.db, system properties, VHAL list, CalSets clear/recovery |
| [gmsystemui_app_gating.md](gmsystemui_app_gating.md) | GMSystemUI WhiteList/predicates, CarPlay vs AA asymmetry, display-calibration gate |
| [emulator.md](emulator.md) | Y181 AAOS in the Android emulator (goldfish hybrid and real-kernel builds). **Not yet consolidated** (see Status) |
| [pi_swap_feasibility.md](pi_swap_feasibility.md) | Replacing the radio with a Raspberry Pi running AAOS: CAN audit, removal consequences, capture plan |

### References
| Doc | Contents |
|---|---|
| [external_references.md](external_references.md) | Intel APL/Celadon/bootloader sources, NDA-gated list, surrealdev bibliography |

## Where does X live?
| Question | Doc |
|---|---|
| CPU/RAM/display/UART/I2C specs | hardware_specs |
| VIP MCU, IPC channels, GHS | vip_ipc_ghs |
| Why the radio boots into ELK/recovery; fastbootd | elk_recovery |
| Partition sizes, `super` | partitions_storage |
| Build strings, patch levels | firmware_versions |
| IPs, VLANs, open ports | ethernet_networking |
| Radio-to-amp audio | avb_audio_transport |
| ECU list, gateway 0x45, radio 0x80 | vehicle_network |
| CAN signal bit layouts | can_network |
| How a CAN experiment was run | can_bench_experiments |
| FSA service IDs, protobufs | fsa_protocol |
| Who flashes which module | ota_programming_roles |
| Update engine, Binder, SWU | ota_update_stack |
| SELinux, CVEs, ADB auth | security |
| EEPROM map, I2C permissions | eeprom_i2c_security |
| RPO codes, props, CalSets.db | vehicle_config |

## Status
- `ota_update_stack.md` and `emulator.md` are carried over unchanged from the previous layout; their consolidation was not completed. They still contain material owned elsewhere (FSA pointers, CAN decodes, kernel/GHS facts, calibration keys).
- `archive/can_network_original.md` is the unmodified original CAN doc. Two ranges (L476-514, L1046-1091) exist only there; see "Ranges not migrated" in [can_network.md](can_network.md) and [can_bench_experiments.md](can_bench_experiments.md). Its independent loss audit covers L1-600 only.
- Retired: `gminfo3.7_tech_specs.md` (folded into hardware_specs, firmware_versions, vehicle_config, ethernet_networking), `networking.md`, `hardware.md`, `can_network.md` (old, split into dictionary + bench log), `intel_apl_external_resources.md`.
- Related trees outside platform/: `../eeprom/`, `../diagnostics/`, `../research/`, `../hardware/`.
