# VIP-SoC IPC & GHS Hypervisor

Scope: the dual-processor architecture of the GM Info 3.7 (gminfo37) radio, the Renesas RH850 VIP MCU and its PLC/calibration data, the VIP-SoC IPC link and channel map, and the GHS INTEGRITY Type-1 hypervisor (binary, `/dev/ghs`, GHS-Android connection map, VP crash decode).
Boot ordering and GHS init tasks live in [boot_chain.md](boot_chain.md); component specs in [hardware_specs.md](hardware_specs.md).

Evidence tags (as used in the sources): [C] live-confirmed on a running unit, [FW] firmware/static extraction, [INF] inferred, [X] external source, [UNVERIFIED] not established. "UNVERIFIABLE-FROM-LIVE" = not observable from a locked Y175 user shell.

Related: [boot_chain.md](boot_chain.md), [hardware_specs.md](hardware_specs.md), [security.md](security.md), [fsa_protocol.md](fsa_protocol.md), [ethernet_networking.md](ethernet_networking.md), [can_network.md](can_network.md), [firmware_versions.md](firmware_versions.md), [ota_programming_roles.md](ota_programming_roles.md), [vehicle_config.md](vehicle_config.md), [emulator.md](emulator.md), [eeprom_i2c_security.md](eeprom_i2c_security.md), [../hardware/teardown.md](../hardware/teardown.md) (owns the IPC Channel Map), [../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md).

---

## 1. Dual-Processor Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Intel Atom x7-A3960 (SoC)                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ GHS INTEGRITY IoT 2020.18.19 MY22-026 (Type-1, bare-metal) │ │
│ │ ┌───────────────────┐  ┌──────────────────────────────────┐ │ │
│ │ │ GHS Tasks (14+)   │  │ Android 12 (Guest VM)            │ │ │
│ │ │ AVB verify        │  │ AAOS + Harman + GM services      │ │ │
│ │ │ kethernet TCP/IP  │  │ CarPlay (CINEMO/NME)             │ │ │
│ │ │ IPU4 camera       │  │ Android Auto (AOSP)              │ │ │
│ │ │ TEE keymaster     │  │ OnStar / Diagnostics             │ │ │
│ │ │ GHS cal service   │  │                                  │ │ │
│ │ │ GHS logger        │  │                                  │ │ │
│ │ └───────────────────┘  └──────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HDLC over UART /dev/ttyS1 (20 IPC channels 1-20, protocol v16)
┌─────────────────▼───────────────────────────────────────────────┐
│ Renesas RH850/F1K (R7F7015873AFP) — VIP MCU                     │
│ Power management, CAN gateway, early boot, EEPROM, PLC timers  │
└─────────────────────────────────────────────────────────────────┘
```

The Intel Atom x7-A3960 SoC handles all application-level processing under a GHS INTEGRITY Type-1 hypervisor. The Renesas RH850/F1K VIP MCU manages power sequencing, the CAN bus gateway, early boot, EEPROM access and PLC timers. The two communicate over HDLC on UART `/dev/ttyS1` with 20 IPC channels (numbered 1-20; confirmed: `hardware/teardown.md` IPC Channel Map), protocol version 16. The GHS hypervisor runs bare-metal on the SoC; Android 12 runs as a guest VM alongside 14+ native GHS tasks (AVB verification, Ethernet networking, camera, TEE keymaster, calibration services, logging). The GHS task list and init order are in [boot_chain.md](boot_chain.md).

### 1.1 Functions that survive an Android reboot

GHS/VIP-dependent (operate at hypervisor/VIP level; remain functional while Android is rebooting or crashed):

- Turn signal chimes
- Door chimes
- Seatbelt chimes
- Reverse backup camera
- 360 surround view

Android-dependent (require the guest VM):

- Climate display
- Steering wheel button processing
- Navigation
- Audio playback / media
- CarPlay / Android Auto

### 1.2 GHS camera bypass

The backup camera works **during Android reboot**. GHS receives CAN gear position and directly controls the display overlay, independent of the Android guest. The `earlyEvs_harman` module exists but is **commented out** in the configuration; GHS handles the camera directly without it. GHS also renders the "return to dealer" / recovery error screens (see [boot_chain.md](boot_chain.md), Error Screen Architecture).

---

## 2. VIP MCU (Renesas RH850/F1K)

Identification (corrected 2026-11-12): **R7F7015873AFP**, marking **15873**, 176-pin LFQFP. **TM52176 is a trace code.** Owner-reported VIP console TX is **pin 52 / P1_9 / RLIN34TX**; pin 53 provides the matching RX function, with reception unverified. Package evidence, manual and full UART table: [hardware teardown](../hardware/teardown.md#rh850f1k-package--uart-pinout).

> **[ONLINE RESEARCH 2026-11-21] Pin-map discrepancy flagged for verification.** The closest publicly available datasheet — Renesas RH850/F1KH and F1KM 176-pin LQFP (Table 2A.1, farnell.com/datasheets/4165772.pdf; also renesas.com/document/dst/rh850f1kh-rh850f1km-datasheet) — lists pin 52 as **P1_9 / DPIN20 / INTP21 only**, with no RLIN alternate function. RLIN34TX in that document appears at:
> - **Pin 88** (P8_9 / CSIH3CSS2 / PWGA41O / ADCA0SEL2 / **RLIN34TX** / ADCA0I16S) — primary
> - **Pin 171** (P12_2 / INTP19 / **RLIN34TX** / PWGA58O / ...) — alternate
> RLIN34RX: pin 87 (P8_8) primary, pin 170 (P12_1) alternate. RLIN35TX: pin 8 (P11_8) primary, pin 74 (P1_5) alternate.
> **Caveat:** the R7F7015873AFP belongs to the RH850/F1KM-S4 subfamily; the publicly available datasheet covers F1KH/F1KM. Alternate-function assignments can differ between sub-families. The discrepancy (P1_9 without RLIN34TX in the public document vs. the owner's bench identification) should be verified against the R7F701587 hardware user's manual or confirmed against the bench UART by baud-rate and traffic correlation. **Do not change the existing bench-confirmed UART identification without that verification.**

Role: power, CAN gateway, early boot, EEPROM. Power mode state machine (Run, Accessory, Crank, Off) is managed by the VIP (networking.md L584-588).

> **Low-power sleep (external corroboration [X]).** Surrealdev *"Rooting the Cadillac Part 1"* (Snipesy, 2026-08-15; `https://surrealdev.com/rooting-the-cadillac-part-1-lay-of-the-land/`; bibliography in [external_references.md](external_references.md) / [qualcomm_cadillac_platform.md](qualcomm_cadillac_platform.md)) reports the RH850 "VIP" powers itself down in deep sleep and wakes on a hardware signal direct from its **CAN phy**, letting the whole radio idle at **sub-milliamp** draw on the always-on 12 V feed. Consistent with this board's VIP role (power/CAN/early-boot); the sub-mA figure is the author's Cadillac measurement, **not independently confirmed on this A11 unit.** [X]

Power/lifecycle independence of AAOS (updated 2026-11-17, from vehicle_network.md L403-409): VIP firmware and bench CAN tests establish that power/lifecycle processing runs independently of AAOS. The driver-door/off sequence can initiate SoC shutdown; a mute-hold CAN sequence can request reset. This supersedes the earlier owner-only inference; it does not replace a physical measurement of individual supply rails. See [can_network.md](can_network.md) and the VIP lifecycle evidence in `hardware/teardown.md`.

### 2.1 VIP firmware identity and security function

Summary only; the full security analysis is chartered to [security.md](security.md) and EEPROM/MEC to [eeprom_i2c_security.md](eeprom_i2c_security.md). Version/part tables: [firmware_versions.md](firmware_versions.md).

- VIP_APP part numbers/builds: Y177 86283151 (build 25Feb28-0330); Y181 86331656 (build 25Jun19-2209, live Y181 bench radio VIP_APP module 1 version `2B.B5.01.01`). VIP_BOOT 85056831, SOC_HOSTOS 85098662 and SOC_ABL 85738845 are identical across Y177/Y181 (firmware_versions.md L136-146).
- Y175 radio's own VIP_APP is `2B.175.1.5` (build 24Apr23-2202, `enumeration/Y175/Y175_VIP.log:6-7`). The July 2024 UART capture `enumeration/VIP_log_2B.174.4.1_10JUL24.txt` is `2B.174.4.1` (Build 24Mar22-0256), an older VIP_APP.
- VIP security-function **address** `0x000b67d0` (not a firmware version): full ~906-byte validator present in ALL builds (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0); the earlier "Y177 4-byte stub" was a fixed-address misread. Corrected 2026-08-26 (three-way byte diff 2026-08-25). Called subroutines `0x000b6652`, `0x000aee28`; callers `0x000b6b06` (primary), `0x000b6e82` (secondary/fallback). `0x000ecd84` is a generic RTOS mutex primitive (285 call sites), not part of a validation chain. RAM `0x3e06` is a generic "security module initialized" readiness flag, not an EEPROM SBI value.
- Y177 vs Y181 VIP firmware differs by 549,518 bytes (28.4% of the image); this is unrelated VIP change, not a security re-enablement. The hypervisor layer is unchanged between them.
- The validator belongs to the ADB/MEC certificate path: SoC-side `gm_adb_auth_init` / `is_secure_mode` is driven by EEPROM SBI -> VIP MEC response on DID `F1A0`; it does not set SELinux mode.
- Live evidence [C live-Y175 2026-10-05]: VIP internals are UNVERIFIABLE-FROM-LIVE, but the VIP boot log (diagnostics/Y175_session.log) shows the RH850 side of the handshake: `J6_prv_ProtoKey:Protokey transmitted to SoC` (repeating), `SbaTicketValidation validation failed: 0x0`, `Receives invalid seed [1/2] from BCM`. `gm_protokey` is live on the SoC (PID 889, root, domain `gm_protokey`).
  > **[ONLINE RESEARCH 2026-11-21] PROTOKEY / ProtoKey — no official GM documentation found.**
  > No GM service publication, TSB, or NHTSA filing uses the name "PROTOKEY." The only public
  > reference is third-party reverse-engineering (GitHub `lvalen91/gminfo_resources`,
  > `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`), which describes: PROTOKEY is the VIP's
  > **security key management module**, initialized after SBAT in the VIP module sequence; in
  > normal mode (SBI=0x00) the VIP requests a seed from the BCM over **GMLAN**, validates a
  > seed/key exchange, and transmits the result to the SoC via IPC channel
  > `SERIAL_IPC_PROTO_KEY_CHANNEL`; in bypass mode (SBI=0xFF) a fixed 0xFF seed is returned and
  > BCM communication is skipped. SoC-side service `/vendor/bin/gm_protokey` receives the seed
  > from the VIP over GHS IPC (`/dev/ghs/ipc`); the result affects ADB shell access. This is
  > consistent with the bench observation of "Receives invalid seed [n] from BCM" when no BCM is
  > present (normal mode, no BCM to answer the GMLAN seed request).
  >
  > **CAN IDs 0x457 / 0x458:** No public GM DBC file, opendbc repository, or teardown analysis
  > names these IDs. Global B / VIP platform DBC files are not publicly available (CAN bus
  > encryption on Global B; openpilot explicitly unsupported).
  >
  > **BCM supplier (2022-2024 Silverado 2500HD):** Not identified in any public source.
  > No Continental, Aptiv, ZF, or Delphi attribution found for the MY22-24 Silverado HD BCM.
- MEC = Manufacturer Enable Counter (see [security.md](security.md#mec-manufacturer-enable-counter)). The earlier "Mode/Event/Condition" expansion was incorrect (corrected 2026-11-15).
- PLC = power-level control / VIP-SoC power handshake. The earlier "Programmable Logic Controller" expansion was unsupported (corrected 2026-11-15).

### 2.2 PLC Timers

| Timer | Duration |
|-------|----------|
| SoH Timeout | 1500 ms |
| Shutdown | 3500 ms |
| Startup | 6000 ms |
| Unmount | 800 ms |
| Hypervisor Startup | 300 ms |

### 2.3 VIP Calibration Values

31+ values stored in EEPROM/NVM, applied at every boot (firmware_versions.md L183 says "31 `cal_` values stored in the RH850 VIP MCU firmware"; controls power management, CAN parameters, timing; updated independently from Android OTA). Full CalDef/VIP-cal tables belong to [vehicle_config.md](vehicle_config.md).

**Power:**
- `cal_background_sleep_timeout_sec` = 10
- `cal_sleep_fault_timeout_sec` = 900
- `cal_startup_fault_timeout_sec` = 15
- `cal_suspend_to_ram_en` = 1
- `cal_str_min_temp_threshold` = -10

**Infotainment:**
- `cal_veh_initiated_local_infotainment_timeout` = 600
- `cal_user_initiated_local_infotainment_timeout` = 600

**Display:**
- `cal_cluster_animation_ignore` = 0
- `cal_rsi_animation_ignore` = 1

**Debug:**
- `cal_vin_relearn_en` = 1
- `cal_maximum_flush_fault_time` = 36000

### 2.4 VIP Calibration Index System

Indexed groups sent VIP -> SoC at every boot (source text says 15 groups; only 4 are listed; see Open conflicts):

| Index | Size | Description |
|-------|------|-------------|
| 0 | 154 B | System config |
| 1 | 128 B | Audio/chime |
| 2 | 17 B | Mic |
| 3 | 21 B | DTC mask |

---

## 3. VIP-SoC IPC

### 3.1 Link parameters

| Parameter | Value |
|-----------|-------|
| Transport | HDLC over UART `/dev/ttyS1` |
| Channels | 20 IPC channels (numbered 1-20; confirmed: `hardware/teardown.md` IPC Channel Map) |
| Protocol | Version 16 (`protocol_version=0x10` in `/vendor/etc/ipc4.cfg`) |
| IPC version / API | 4.1.0 / API 0404 |
| Framing | HDLC |
| Window size | 5 |
| IFRAME timeout | 50 ms |
| UFRAME timeout | 20 ms |
| Line rate | 1 Mbps (VIP `IPCServer` on /dev/ttyS1; confirmed: `hardware/teardown.md`). The earlier "4104" was a misread of the ~4104 ms channel-XON timing in the VIP UART log, not a baud rate. |

**Module init order:** SS_SWC -> PLC -> J6_CDD -> IPC_S -> AMP_MGR_SWC -> PROTOKEY -> SBAT -> IOHWAB_MIC -> NAV

The 20 channels carry power management commands, CAN messages, calibration data and vehicle state between the two processors.

### 3.2 Channel assignments

Corrected 2026-11-15 against the owning UART-derived channel map ([../hardware/teardown.md](../hardware/teardown.md#ipc-channel-map-from-vip-uart-log)); the earlier contiguous channel ranges contradicted that source.

| Channel | Observed role |
|---------|---------------|
| 2, 16 | PlayAnimation events |
| 5 | Ethernet state |
| 6 | Diagnostics (UDS SID/DID) |
| 8 | Calibration download |
| 9 | ProtoKey |
| 13 | OTA / remote reflash |
| 14 | Boot reason |
| Others | Initialization/XON observed; no complete service assignment established |

Android-side channel 3 = vehicle signals (`/dev/ipc/ipc3`), see 3.3.

### 3.3 Android-side userspace stack

- **No N_HDLC in the guest kernel.** Confirmed 2026-09 from the real Y181B kernel `.config`: no `N_HDLC` line discipline is compiled into the Android guest kernel. The VIP/RH850 HDLC framing terminates below the Android guest (GHS-side `VIP_InitialTask`); on the Android side the link is a **userspace** protocol. Not a kernel driver dependency.
- `IPCServer` ("GhsComms", `GhsCommsRx/TxThread`) multiplexes numbered logical channels over the UART-backed link and exposes them as `/dev/ipc/ipcN` sockets; `libipc.so` (ipcLib 3.0) clients connect to those per-channel Unix sockets (not a `/dev/ipc` char-dev client; emulator.md L303).
- `/vendor/etc/ipc4.cfg`: `com_device=/dev/ttyS1`, `com_speed=1000000`, `protocol_version=0x10`, `socket_prefix=/dev/ipc/ipc`, control interface `/dev/ipc/ctrlif_s` (gid `vehicle_network`), **lchannels index 0-20**. `IPCServer` strings also reference `/dev/ghs/ipc` and `/dev/ttyS4`; the authoritative backing device per config is `/dev/ttyS1`. [FW]
- The GM VHAL (`android.hardware.automotive.vehicle@2.0-service-gm`, runs as user `vehicle_network`) opens **`/dev/ipc/ipc3`** = lchannel index 3, gid `vehicle_network`: the vehicle-signal channel. The Android guest sees only cooked signals over channel 3; the far end of `/dev/ttyS1` owns the physical CAN. Far-end "VIP MCU" identity is prior project analysis, [INF]/[GM] for this build. [FW for guest half]
- `/vendor/bin/ghs_set_is_virt.sh`: `is_virt=true` iff `/dev/ghs` exists.
- The guest has no CAN interface at all (no CAN driver modules, no CAN netdev, no CAN symbols in the vehicle stack; kernel `CONFIG_CAN=y` is built in but inert). Full evidence: [pi_swap_feasibility.md](pi_swap_feasibility.md) (vehicle_network.md L359-384). `gmvt` is GM Voice, not a vehicle transport.
- Device nodes/SELinux (live Y175 2026-10-05, dev_listing.txt): `/dev/ttyS1` owner `root:root`, label `ipc_serial_device`, mode `crw-------` (0600, root-only), so the IPC link to the VIP is DAC-closed (1 Mbps/HDLC-v16/20-channel detail UNVERIFIABLE-FROM-LIVE). `ttyS0` = bluetooth, `ttyS2` = `serial_device`/guest console (`console=ttyS2`), `ttyS3` = `display_panel_device`; `/dev/ttyACM1` is `crw-rw-rw-` with label `sxm_device` (SiriusXM tuner serial, MCP2200 hardware identity; "Debug UART" was refuted). Full UART table: [hardware_specs.md](hardware_specs.md).
- SELinux domains: `gm_vnd_IPCServer` runs as **root** (PID 386 live Y175), handles HDLC on `/dev/ttyS1`; `gm_vehicle_hal` runs as `vehicle_network` (PID 792), not root. Domain table: [security.md](security.md).
- `ttyS1` is reserved for IPCServer's real VIP serial link in the emulator and must not be repurposed (emulator.md L76-79). Emulator behaviour (no VIP peer -> IPCServer `Uframe timer expired` / `Sending Uframe RESET` loop; `pal_calibrations` "Timeout is expired in IPC Calibrations channel"; ipc3 frame injection wire format) is owned by [emulator.md](emulator.md) and [vehicle_config.md](vehicle_config.md).
- Real-radio `/dev/ipc/*` nodes also exist on the Y181.3.2 reference VM (e.g. `ipc10`-`ipc15` `srw-rw---- system`, `ctrlif_s` `vehicle_network`) even though `/dev/ghs` does not (security.md L533); different interface family from `/dev/ghs/*`.

### 3.4 Native Probe08 follow-up (2026-11-17)

With stock AAOS/GHS absent, `/dev/ttyS1` on PCI `00:18.1` exchanged CRC-valid HDLC traffic with the VIP at 1 Mbps. The bounded tool received a protocol-`0x10` channel-0 flow-control message (21 entries), then six channel-3 messages, with zero bad CRCs. The short channel-3 payloads were `E1 02 10 00 01`, `E1 03 10 00 01`, `E1 01 10 00 01`, followed by the same three variants ending in `02`. Application semantics remain unresolved; repetition may indicate negotiation/retry, but they are not yet decoded vehicle-property values.

During that test, changing the bench's CAN `284` candidate from value 2 to 4 and back to 2 produced VIP diagnostic state changes to `Propulsion` then `Run`; the original value was restored. No corresponding new vehicle signal payload was decoded by the native receiver. This confirms that the VIP continues CAN power-state processing without AAOS, while the SoC application handshake/subscription requirements remain unresolved. The confirmed CAN `4DA` driver-door path is documented in [can_network.md](can_network.md); engine RPM and turn-signal UART forwarding were not newly tested. The link exposes binary IPC, not a VIP shell, and does not establish unrestricted CAN injection, raw bus capture or unrestricted memory access.

---

## 4. GHS INTEGRITY Hypervisor

### 4.1 Identity and binary format

- Version: INTEGRITY IoT 2020.18.19 MY22-026, Type-1 bare-metal; identical between Y177 and Y181.
- SOC_HOSTOS (part 85098662): 14.9 MB GHS INTEGRITY ELF, statically linked. The ELF header claims 32-bit LSB (Intel 80386) but the code is **x86-64** (`movabs`/REX, `crt_x64.86`; disassemble as `x86:LE:64`). Corrected 2026-08-26: the "32-bit compatibility mode" claim was an invented rationalization and is retracted.
- VMM uses Intel VT-x with 64-bit EPT for the Android guest.
- Build path: `/home/mal/gm_release/MY22-026/final/iot/rtos/`.
- Rollback is enforced by a GHS rollback counter in `misc` (Y181 -> Y177 blocked); see [boot_chain.md](boot_chain.md).
- Memory grant (static guest grant 7830 MiB, E820 etc.) is a hardware/memory topic: [hardware_specs.md](hardware_specs.md), [../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory).

### 4.2 USB mediation [FW 85098662 `.vmm1`/`.boottable`/`IGS_DSDT`; 2026-10-10]

GHS performs a *mediated (para-virtual) PCI passthrough* of the real Intel xHCI (`8086:5AA8`) and XDCI (`8086:5AAA`) to the Android guest: an emulated PCI function (`usb_passthru_emul.c`) plus RPC register verbs `UsbRdReg`/`UsbWrReg`/`UsbPoll`/`UsbIrq` (`system_usb_passthru.c`), and supplies the guest ACPI `IGS_DSDT` whose XDCI `OTGD` OpRegion the Android `intel_xhci_usb_sw` role-switch driver uses. GHS contains **no** role-switch, gadget or dabridge logic (0 hits for `dabridge`/`dabr_udc`/`usb_otg_switch`/`cbc-signals`/`dwc3`/`gadget`); the role decision is made in the Android guest, in software. The XDCI is dual-role (`_ADR 0x00150001`); role and port power are commanded through the `OTGD` `_DSM` `SPPS` method (writes `PUPS` port-power / `UXPE` enable, reads `U2CP`/`U3CP` connect), a register/ACPI decision, not a sensed pin [FW decoded `dsdt_a.dsl:1290-1500`; CONFIRMED x2]. The android ACPIO (`86331630`) is only the `ANDR0001` fstab/vbmeta descriptor (no USB config); USB governance is the GHS `IGS_DSDT`. The blob is not opaque: the only unreadable bytes are the 768 B tail (256 B RSA-2048 Android key + 512 B RSA-4096 signature); high-entropy regions are chime PCM, camera/overlay images, IPU/DSP/GuC/HuC firmware and AES/SHA constant tables. Full map: `GHS_FILE_MAP_85098662.md`.

### 4.3 `/dev/ghs/` device interfaces

| Device | Purpose |
|--------|---------|
| ipc | Inter-processor / inter-VM communication |
| cal | Calibration service |
| chime | Turn signal/seatbelt/door chime generation |
| camera (ghs_camera_device) | Backup camera bypass / camera subsystem bridge |
| tee-att | TEE attestation |
| audit | Security audit log |
| textlog | Text/hypervisor logging |
| snapshot-dbg | Debug snapshots |
| emmc-health | eMMC health monitoring |
| ota-isys | OTA update interface (ISYS) |
| gpu-dbg | GPU debug |

Live status:
- [C] live-Y175 2026-10-05: `/dev/ghs` exists as a directory (`drwxr-xr-x root root u:object_r:device:s0`) and `/dev/ghscamerafb` (`crw------- root`) is present, but the capture did not enumerate the children; the individual interface names are UNVERIFIABLE-FROM-LIVE.
- [C] Y181.3.2-ref 2026-10-06: GHS is absent from the emulator; `/dev/ghs` does not exist and there are no `/dev/ghs*` or `/dev/trusty*` nodes (QEMU/HVF VM, no GHS INTEGRITY, no TEE). The table is not confirmed by this reference and needs a live GHS-backed unit. The sibling `/dev/ipc/*` sockets do exist (see 3.3).

### 4.4 GHS-Android IPC map (GHS connection names)

Inter-process channels between GHS tasks and Android. GHS task inventory and init sequence: [boot_chain.md](boot_chain.md).

| Group | Connection | Purpose |
|-------|-----------|---------|
| VMM | `ConnToAndroidVMM` | Primary VMM control channel |
| VMM | `ConnToVMM_Camera` | Camera pipeline coordination |
| VMM | `ConnToVMM_Display` | Display/framebuffer management |
| VMM | `ConnToVMM_Chime` | Chime audio routing |
| VMM | `ConnToVMM_Cal` | Calibration data access |
| VMM | `ConnToVMM_OTA` | OTA update coordination |
| VMM | `ConnToVMM_TextLog` | Log forwarding to GHS |
| Camera | `ConnToCamera` (x6) | 6 camera connections (IPU4 pipeline) |
| Audio | `ConnToChimes` | Chime audio task |
| Audio | `ConnToDirana` | Dirana tuner/DSP |
| VIP MCU | `ConnToVIP` | Primary VIP communication |
| VIP MCU | `ConnToVip_Lifecycle_API` | Lifecycle/shutdown coordination |
| TEE | `ConnToTEE_Keymaster` | Hardware keymaster operations |
| TEE | `ConnToTEE_Storage` | Secure storage (RPMB) |
| TEE | `ConnToTEE_Router` | TEE message routing |
| TEE | `tipc_conns` | Trusty IPC connections for TEE |

### 4.5 Virtual Processor crash decode (IPC ECUResetInfo, fn4, instanceId=6)

Obtained via an FSA DeviceInformation-style query to the IPC partition (protocol: [fsa_protocol.md](fsa_protocol.md)).

Raw response payload (63 bytes):
```
0a 3b 12 13 31 39 37 30 2d 30 31 2d 30 31 20 30 30 3a 30 33 3a 31 39
1a 24 56 50 20 46 61 69 6c 75 72 65 20 49 44 3a 20 30 30 37 2c 20 45
72 72 6f 72 20 49 44 3a 20 30 78 30 43 30 33 10 01
```

Decoded `ReadECUResetInfo_status`: field 1 `eCUResetInfo` { 2 timestamp `"1970-01-01 00:03:19"` (epoch+199 s, clock unset at crash); 3 reason **`"VP Failure ID: 007, Error ID: 0x0C03"`** }; field 2 = `1`.

Interpretation: "VP" = **Virtual Processor** in the GHS INTEGRITY hypervisor. The Visteon IPC logs GHS partition (VP) crashes; VP 007 failed with `0x0C03`. This confirms the IPC partition has visibility into hypervisor VP failure events. Open: correlate VP 007 with a partition name (`/dev/hvc*`, `/vendor/etc/init/*.rc`); decode `0x0C03` (likely an INTEGRITY kernel error code). See [GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md).

> **0x0C03 error code — online research note [ONLINE RESEARCH 2026-11-21]:** No public mapping found. Web searches across GHS product documentation, Common Criteria security targets (INTEGRITY-178B), academic literature, and public CVE databases found no published INTEGRITY kernel/VP error code table. GHS error code documentation is gated behind the customer support portal and is not publicly indexed. The only public hit for "0x0C03" is a Linux Bluetooth HCI command opcode (unrelated). The code remains undecoded. If a GHS INTEGRITY SDK or MULTI debugger session becomes available, the INTEGRITY kernel reference manual (`INTEGRITY_kernel_ref.pdf` or equivalent) would be the authoritative source for VP/AddressSpace error codes.

### 4.6 GHS ShutdownReason codes

The GHS firmware emits log entries of the form `"ShutdownReason: 0x%02x"` (format string confirmed in decompiled strings from SOC_HOSTOS 85098662). Three values have been observed in forensic log captures:

| Code | Observed frequency | Meaning |
|------|--------------------|---------|
| 0x00 | 11 occurrences | Unknown |
| 0x23 | 6 occurrences | Unknown |
| 0x37 | 12–24 occurrences | Unknown |

> **Online research note [ONLINE RESEARCH 2026-11-21]:** No public mapping found. Web searches for "GHS INTEGRITY ShutdownReason," "Green Hills INTEGRITY reboot reason codes," and related terms found no published enum table, header excerpt, or AUTOSAR BSW documentation covering these codes. The Windows shutdown reason code table (0x00 = Other Unplanned; completely different namespace) and Linux `reboot.h` are unrelated. GHS kernel shutdown/lifecycle APIs are documented in customer-only INTEGRITY reference manuals. If MULTI debugger SDK headers or INTEGRITY BSP sources become available, search for a `ShutdownReason` or `GHS_LIFECYCLE_SHUTDOWN` enum. The `0x00` code likely corresponds to a normal/clean shutdown (the most common semantics for code 0 across RTOS platforms), but this is inference, not a confirmed GHS mapping.

---

## Open conflicts

1. **IPC version scheme.** hardware.md L195/L204 and networking.md L440 and security.md L846 state "protocol v16" (HDLC); hardware.md L273 states IPC "Version 4.1.0 / API 0404". vehicle_network.md L393 gives `protocol_version=0x10` (= 16 decimal), which reconciles the "16" but not 4.1.0. Not established whether 4.1.0/API 0404 is a library/API revision distinct from the wire protocol; both values kept.
2. **Channel numbering.** 20 channels "numbered 1-20" (hardware.md L204, networking.md L439) vs `ipc4.cfg` lchannels "index 0-20" (vehicle_network.md L394), with channel 0 observed carrying flow control (Probe08, vehicle_network.md L413). Whether 1-20 are application channels with 0 as control is [INF], not stated by any source.
3. **Calibration index groups.** hardware.md L258 says "15 indexed groups"; only 4 (indices 0-3) are listed (L260-265). Remaining 11 undocumented.
4. **VIP calibration count.** hardware.md L235 "31+ values"; firmware_versions.md L183 "31 `cal_` values" (unsourced there). Only 11 listed.
5. **Y177 vs Y181 security difference.** firmware_versions.md L146 and L158 say the security behavioral difference "resides entirely in the VIP_APP"; the same file's L107-109 retraction and security.md L152 say the validator is the full function in all builds and the 28.4% delta is unrelated. This doc follows the retraction (2.1); L146/L158 wording is stale in the source.
6. **IPC peer identity on `/dev/ttyS1`.** vehicle_network.md L396-402: far end is "the VIP MCU / a GHS partition", with VIP identity [INF]; other sources assert VIP definitively. Native Probe08 (3.4) shows CRC-valid HDLC with the VIP, which supports the VIP but does not exclude a GHS intermediary on the stock path.
7. **`/dev/ghs` children** are documented from firmware/static (table 4.3) but UNVERIFIABLE on both Y175 live and the Y181.3.2 emulator reference (security.md L531-533).
