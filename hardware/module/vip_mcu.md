# RH850/F1K VIP MCU

Scope: Renesas RH850/F1K VIP MCU package/identification, 176-pin UART (RLIN3) pinout and probe
history, VIP boot-log fields (AUTOSAR SWC modules, LEO/Ethernet-switch reset sequencing, PLC
power-level handshake, u-blox GNSS, SBAT/ProtoKey observations).
Related: [`identity_bom.md`](identity_bom.md) (module identity/BOM),
[`../interfaces/connectors.md`](../interfaces/connectors.md),
[`../../platform/security.md`](../../platform/security.md) (ProtoKey / ADB authentication,
SBAT security architecture), [`../../platform/vip_ipc_ghs.md`](../../platform/vip_ipc_ghs.md)
(VIP IPC/GHS detail), [`../../platform/boot_chain.md`](../../platform/boot_chain.md),
[`../../diagnostics/diagnosticsd_dids_and_dtc.md`](../../diagnostics/diagnosticsd_dids_and_dtc.md#rh850-uart-correlation-with-direct-t1-did-reads-2026-11-14)
(UART/DID correlation), [`../teardown.md`](../teardown.md) (index; full deep-EEPROM /
ProtoKey three-phase-sequence writeup lives there, past this document's scope).

Confidence tags: **[C]** confirmed · **[I]** inferred · **[FW]** firmware/kernel evidence ·
**[HW]** hardware observation · **[?]** open question.

## 1. Package and Identification

**[C]** The VIP MCU is Renesas **RH850/F1K, R7F7015873AFP** (G3KH core), **176-pin LFQFP**
(44 leads/side, 24 x 24 mm body, 0.5 mm pitch). Abbreviated board marking: **15873**.
**TM52176** is a manufacturing trace code, not the device model.

Identification basis: observed marking and pin count, the F1K product table (p. 75), and
Renesas [PCN HPLM-2024-0029, p. 4](https://www.renesas.com/en/document/pcn/addition-production-sites-and-material-changes-rh850f1k-seriespc-mcu-a034ae)
(abbreviated part-marking/trace-code layout). Packaging/order suffixes beyond
R7F7015873AFP are not established from the board marking. An earlier 144-pin identification
and its derived UART assignments were incorrect and are superseded by this entry
(corrected 2026-11-12).

Source: [RH850/F1K hardware manual, Rev. 1.10](../datasheets/Renesas_RH850_F1K_HW_manual_rev110.pdf)
(R01UH0562EJ0110, 2016-11-30). Device: 2 MB code flash, 64 KB data flash, 192 KB RAM, up to
120 MHz. Table 2.3 (pp. 89-93) supplies the 176-pin assignments.

### 1.1 Memory Map (R7F7015873AFP, Table 4.1, p.262)

| Region | CPU address range | Size |
|---|---|---|
| Main code flash | `0x00000000–0x001FFFFF` | 2 MiB |
| Extended user code flash | `0x01000000–0x01007FFF` | 32 KiB |
| Local RAM | `0xFEBD0000–0xFEBEFFFF` | 128 KiB |
| Retention RAM | `0xFEBF0000–0xFEBFFFFF` | 64 KiB |
| Data flash | `0xFF200000–0xFF20FFFF` | 64 KiB |

**[?]** These are memory-map facts, not confirmed remotely-readable ranges. Configuration/
option/security areas and the separate external EEPROM and update containers are distinct
from this table.

### 1.2 Serial Programming Mode (reference only)

**[C]** The hardware manual (section 6, p.290) distinguishes normal user-program execution
from serial programming. Serial programming is selected at reset by FLMD0=1/FLMD1=0; section
37.6 (p.2757) assigns the programming UART to **JP0_0/FPDR** and **JP0_1/FPDT**, not an
arbitrary RLIN port. For the 176-pin package, Table 2.3 identifies these as physical pins
**47** (FPDR) and **46** (FPDT), with FLMD0 on pin **63**. Board routing/access to these pins
is not verified; no mode-pin changes or programmer-mode entry were performed.

Table 37.3 (p.2753) and Table 37.4 (p.2754) of the same manual document flash-read support via
serial programming/user code and the existence of programmer authentication / connection
prohibition / read-command prohibition settings; this unit's settings are **[?]** unknown. The
[flash hardware-interface manual](https://www.renesas.com/en/document/mah/rh850f1k-users-manual-flash-hardware-interface?language=en)
(R01UH0622EJ0130, section 5.1, p.42) distinguishes CPU-readable flash in read mode from
program/erase modes. None of this establishes that Harman's IPC dispatcher exports those
bytes; the HDLC acknowledgments in §2.2 prove transport only, and no VIP firmware dump was
attempted or completed.

## 2. UART (RLIN3) Pinout

**[HW]** Owner-reported probe location for the previously captured VIP UART log: physical
**pin 52, P1_9 / RLIN34TX** (RLIN3 channel 4 transmit), 115200 baud, 8N1. The capture files
preserve VIP output but do not independently record probe location; attribution is
owner-reported. Matching RX (pin 53) is an available pin function only — reception/command
handling is not verified.

| Physical pin | Port / alternate function | Role |
|---|---|---|
| **52** | **P1_9 / RLIN34TX / DPIN20** | Owner-reported VIP console TX |
| 53 | P1_8 / RLIN34RX / INTP14 | Matching channel 4 RX function; enabled state unverified |
| 20 | P0_2 / RLIN30TX | Channel 0 TX alternative |
| 21 | P0_3 / RLIN30RX | Channel 0 RX alternative |
| 156 | P10_10 / RLIN30TX | Channel 0 TX alternative |
| 155 | P10_9 / RLIN30RX | Channel 0 RX alternative |
| 24 | P0_5 / RLIN31TX | Channel 1 TX alternative |
| 23 | P0_4 / RLIN31RX | Channel 1 RX alternative |
| 158 | P10_12 / RLIN31TX | Channel 1 TX alternative |
| 157 | P10_11 / RLIN31RX | Channel 1 RX alternative |
| 29 | P0_14 / RLIN32TX | Channel 2 TX alternative; candidate for a separate stream |
| 160 | P10_14 / RLIN32TX | Channel 2 TX alternative |
| 163 | P11_3 / RLIN32TX | Channel 2 TX alternative |
| 31 | P1_1 / RLIN33TX | Channel 3 TX; no other peripheral alternatives listed; priority probe candidate |
| 165 | P11_5 / RLIN33TX | Channel 3 TX alternative |
| 170 | P12_1 / RLIN34RX / INTP14 | Alternate RX location for channel 4; firmware selection unverified |
| 171 | P12_2 / RLIN34TX | Alternate location for known console channel 4, not a new channel |
| 8 | P11_8 / RLIN35TX | Channel 5 TX alternative; owner reports CP2102 RX tapped here |
| 74 | P1_5 / RLIN35TX | Channel 5 TX alternative; compare if pin 8 remains silent |
| 64 | P2_3 / RLIN28TX | RLIN2 channel 8 TX; not the console identification |
| 65 | P2_2 / RLIN28RX | RLIN2 channel 8 RX; not the console identification |

**[C]** Pin functions depend on firmware mux configuration. The old 144-pin numbering,
P5_10..P5_13 labels, and RLIN30/RLIN31 console guess do not apply to this board. The u-blox
GNSS UART channel (§4.3) is not resolved and must be traced separately from this table.

### 2.1 Channel-4 RX Gating (manual-verified, 2026-11-14)

**[C]** Physical pin 53 (P1_8) and physical pin 170 (P12_1) both provide RLIN34RX (Table 2.3,
pp. 90 and 93; port-function tables pp. 144 and 158) — alternate routes to the same channel-4
receiver, not two receivers. A given function is activated on only one pin at a time
(manual pp. 102, 122); current GM pin-mux selection is **[?]** unknown.

The UART operation-enable register `RLN34LUOER` (the n=4 instance of `RLN3nLUOER`) has
separate `UROE` (bit 1, reception) and `UTOE` (bit 0, transmission) bits (p. 907). `UROE=0`
disables reception, `UROE=1` enables it; the register resets to `00` and is held at `00` in
LIN reset mode. Reception additionally requires pin/input routing, matching baud/data format,
and exit from reset (p. 949). Working TX on pin 52 therefore does not establish that RX is
enabled on pin 53 or 170; live mux/UROE values and RX command handling are **[?]** unverified.
No register write was performed to resolve this.

### 2.2 Probe UART vs. Renesas Programming Access (2026-11-17)

**[C]** Probe's `/dev/ttyS1` accesses the running VIP application's HDLC/IPC endpoint — the
stock GHS `VipUART`/`SerialDev1` binding, with a live 1 Mbps CRC-valid reset/acknowledgment,
channel-flow-control and channel-3 exchange. It is not a shell, debugger, or established
ROM-programmer session. See the
[native transport analysis](../../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#native-probe-to-vip-transport-and-elk-prerequisites--2026-11-17)
for the transport trace. The Linux root shell belongs to the Intel SoC and confers no direct
RH850 CPU privilege. The exact VIP-side RLIN channel/pin for this IPC wire is **[?]** not
established; the SoC's `ttyS1` numbering must not be equated with RH850 RLIN1 or the separate
owner-reported RLIN34 diagnostic TX.

**[C]** The G3KH software manual (§§2.1, 2.7, 5) describes supervisor/user CPU modes and MPU
restrictions on top of the 32-bit memory-mapped address space; a UART peer cannot directly
address memory merely because the MCU exposes a readable address space, and this IPC
handler's PSW/MPU state was not measured.

### 2.3 VIP UART Read-Handler Trace (static analysis, 2026-11-17)

**[FW]** A fixed-record read service was traced in VIP_APP `85759599`; no full-firmware
readback handler was found. All addresses below are signed-container **file offsets**
(`runtime = file offset + 0x27A7A` for the mapped region; RAM addresses are already runtime
addresses). No request was transmitted during this analysis.

- Incoming diagnostics dispatcher `0x74F14` accepts message type `0x09`, operation selected
  from payload byte 5. Operation 0 requires an 8-byte message, combines bytes 6/7 into a
  16-bit identifier, calls `0x89D78` (queues event 7). Consumer `0x640E4` → `0x63E6E`, which
  selects fixed DID readers: `0000`, `F08C`, `F09A`, `F0B4`, `F0F1/F0F2/F0F3/F0F4/F0F6`,
  `F190/F198/F199`, `F1A0`, `F1CB/F1CC`, `F1DB/F1DC/F1DE`. Other identifiers take the
  error/zero-length path. Reply construction at `0x63B3C` passes identifier, result length and
  fixed buffer to `0x5C506` — not a generic address-plus-length memory service.
- `F0F4` sets result length `0x336` (822 bytes), calls `0x62F30`, reads fixed NVM block `0x86`
  through `0xE1362`. DID `0000` calls `0x637E4`, collecting a fixed set of NVM blocks. Neither
  accepts a flash source address or walks arbitrary code-flash ranges.
- Message type `0x17` queues at most 33 bytes through `0x89DFC`/event 10 into `0x65398`; its
  relocated branch table leads to security-access handling (`0x643A0` for supported even
  selectors), not a bulk-upload operation.
- Decoder correction: the installed RH850 SLEIGH decoder lacks the long `Bcond disp17` form
  and renders affected instructions as `ld.hu ...,r0`. Per the
  [G3KH software manual](https://www.renesas.com/en/document/mas/rh850g3kh-users-manual-software?language=en),
  section 7 (pp.161-163), `0x74F5C` branches to `0x75538` for message `0x09`, and `0x63E94`
  branches to `0x64060` for DID `0000`. A separate decompile failure at `0x65398`
  (`Low-level Error: Bad instruction count exceeded`, overlapping instructions at
  `0x8D04C`/`0x8D04A`) was checked against the load-map correction rather than trusted as-is.

## 3. UART Probe Observations (bench log)

**[HW]** 2026-11-14 dual-adapter receive-only check: FT232R (0403:6001, owner-reported pin 52)
and CP2102 (10c4:ea60, owner-reported pin 8 / P11_8). A bounded 95-second pre-power
observation at 8N1, flow control disabled: FT232R fixed at 115200; CP2102 swept 115200, 9600,
19200, 38400, 57600, 230400, 460800, 921600, 4800, 2400, 1200, 1000000 baud. Result: isolated
nonprintable bytes only (FT232R: 1 byte; CP2102: 12 bytes total), no valid log lines on either
device; no active-radio/boot interval was established for this run, so neither CP2102 logging
enablement, a difference in streams, nor the correct baud rate was determined — silence alone
does not distinguish firmware mux selection, disabled logging, wrong baud, an electrical/probe
issue, or an inactive radio, and a powered-on/boot sample was still needed. No data was
transmitted and no raw capture file was created.

**Powered follow-up (2026-11-14):** the owner had begun power-on before this reader was
opened, so the earliest boot interval was not guaranteed captured. After owner-reported radio
power-on, a fresh observation at 115200/8N1 received clean pin-52 output including
`[SS_LOG] st=NoCalibration` and periodic `IOC_Main_Temp` messages, 100% printable in multiple
windows, matching the established timestamp/severity/tag format — confirms 115200/8N1 as the
working setting for channel-4 console output. CP2102 on P11_8 received zero bytes across
>70 s of this run; this establishes no observed stream on pin 8, not proof that RLIN35
logging is disabled or that its alternate pin 74 is inactive. No raw capture file was
created. A subsequent 65-second powered baud sweep repeated all 12 CP2102 rates while FT232R
held 115200/8N1: CP2102 received **0 bytes at every rate**; FT232R received 221 bytes in the
same window. This is bounded live silence on the owner-reported P11_8 tap, not proof of
disabled channel-5 firmware logging, and the earliest boot interval was not covered at every
rate. Both ports were closed and their settings restored; no background reader or raw
capture file was left behind.

**Pin-31 clean-start follow-up (2026-11-14):** CP2102 moved to owner-reported pin 31 / P1_1 /
RLIN33TX; both readers armed at 115200/8N1 before announced power-on. Bounded 300-second
capture: FT232R (pin 52) received 108,012 bytes / 1,885 lines (99.9% printable, including
`NoCalibration`); CP2102 (pin 31) received 32 bytes (28 NULs, no recognizable log). Owner
reported a conformal coating over the MCU pins; pin-31 electrical contact is **[?]** unverified.
A silent/undecodable tap is not evidence of disabled logging; this boot observation tested
pin 31 at 115200 only, while the earlier multirate sweeps were on P11_8, not pin 31. Both
readers closed automatically and no raw capture file was written.

**Pin-170 RX burst test (2026-11-14):** FT232R opened at 115200/8N1 with TX wired to the
channel-4 RX alternative (physical pin 170); existing RX tap continued observing MCU TX52.
Transmission bounded to 90 seconds; only pattern sent was CR/LF/Ctrl-C (`0D 0A 03`), no command
words — 781 bursts / 2,343 bytes total (host-driver-accepted count, not confirmed-received).
Receiver collected 31,096 bytes of clean ASCII RH850 log, including power-on, HMI-ready and
`NoCalibration` markers. No login/password/U-Boot-style prompt was detected; no interactive
shell or boot interruption was demonstrated. Transmission stopped automatically after 90 seconds and the port was closed with settings restored; no
raw capture file was created. No
UDS or explicit MEC command was sent, and MEC was not re-read during this UART-only test —
failure to obtain a prompt does not distinguish an inactive pin-170 mux, disabled UROE,
absent command handling, an electrical-contact issue, or an untested boot-console protocol;
pin 53 remains the corresponding alternate RX candidate, with its enabled state still
unverified.

**Additional TX candidates:** Table 2.3 (pp. 89-93) and port alternate-function tables
(pp. 142, 144, 153, 155, 158) identify RLIN3 channels 0-5; Table 19.9 (p. 833) maps their
TX/RX signal names. Priority channel probes: pin 31 (channel 3), pin 29 (channel 2); pin 74
as an alternate route for channel 5 given pin 8 silence. Pins 8/74 both select channel 5;
pins 52/171 both select channel 4 — alternates are not necessarily simultaneously routed, and
another peripheral function can be selected on a listed UART-capable pin. This prioritization
is a pin-coverage choice, not firmware evidence that either channel logs; these pin labels
describe MCU logic signals, not an RS-232-level interface.

**2026-11-14 live console correlation:** with the FT232R adapter on pin 52 and an external
`screen` logger, direct T1 DID reads F1A0 and F0F3 were followed by matching J6_CDD item-ID
events in the RH850 output; startup/power-state and IPC notifications were also visible. The
physical probe location remains owner-reported; RX, command parsing and other TX pins were
not tested. See the
[diagnostic correlation](../../diagnostics/diagnosticsd_dids_and_dtc.md#rh850-uart-correlation-with-direct-t1-did-reads-2026-11-14).
Raw identifier/ProtoKey values are excluded from that finding; no serial adapter
configuration or UART transmit operation accompanied it.

**Later calibration recovery (2026-11-14):** a cleared A11 was restored with the pinned stock
LTZ package via MDI2. The resulting `inVehicle_Cal_Success` UART capture shows older
`NoCalibration` data followed by two successful boot sections (counters 118, 119), both
reporting calibration state `2` and HMI ready. See the
[MDI2 recovery record](../../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
This does not establish a UART shell, MCU RX reception, or ADB restoration.

## 4. VIP Boot Log Fields (Y175)

**[C]** From `diagnostics/Y175_session.log`:

| Field | Value |
|---|---|
| Application Version | 2B.175.1.5 (Build: 24Apr23-2202) |
| Bolo Version | B2.9C.01.01 (23Jul28-1212) |
| ARXML Version | 22.22.158 |
| IPC | v4.1.0, API 0404, HDLC window 5, IFRAME timeout 50 ms, UFRAME timeout 20 ms |
| HwVariant | 56, HwSubVariant: 0 |
| Suspend-to-RAM | enabled |
| SOC thresholds | 90% / 75% / 60%, temp threshold −10°C |
| Max suspend times | 84h / 24h / 16h (by SOC tier) |

**[C] Live Y181 cross-check (2026-11-12, bench radio `W231E-Y181.3.2-SIHM22B-499.3`):**
`/update_cache/update/moduleinfo` reports `MODULE_ID_VIP_BOOT` part 85056831 DLS AA,
`B2.9C.01.01 Build date: 23Jul28-1212 Image name: bolo` (identical to the Y175 Bolo Version
above — consistent with a byte-identical VIP_BOOT claim) and `MODULE_ID_VIP_APP` part 86331656
DLS CN, `2B.B5.01.01 Build date: 25Jun19-2209 Image name: appl`. `MODULE_ID_SOC_BOOT` =
85738845 / `2344`; `ro.boot.bootloader=2344` live.

**[I]** The HW-variant word lives in `/update_cache/update/hw.conf` (ASCII `0xB1020260`);
recovery `last_log` decodes it as `Variant: 177 Global: 0 Region: 0 Project: 2 HD: 0 AMP: 1
SXM: 1 DAB: 0 GPS: 0 Gyro+Accel: 0 Gyro: 0 Accel: 0`. This is a hardware-option word (amp
present, SiriusXM present, no HD/DAB/GPS-option bit), not a software build number — the "177"
value coincides with the "Y177" label by chance; it is a different unit/log context from the
Y175 `HwVariant: 56` above and is not directly comparable.

**[C]** `ghs.log` carries `VipBootCycle: 0x%02x` lines; this capture spans `0x31e..0x339`
(798..825 decimal) — the VIP has cycled ~800 times, versus the SoC-side recovery
`boot_cycle_counter` (a separate counter, 0..55 across the retained `last_log.*`).

### 4.1 AUTOSAR SWC Modules Observed in Boot Log

**[C]** `diagnostics/Y175_session.log` tags each line with an AUTOSAR software-component name.
Modules observed across the boot trace: `SS_SWC` (system state), `PLC` (power-level control),
`LSWTCH_SWC` (LEO/Ethernet-switch control), `J6_CDD` (CAN complex device driver), `DTC`,
`PROTOKEY`, `SBAT`, `UBLOX`, `NAV`, `RTC`, `IPC_S` (IPC core).

### 4.2 LEO / Ethernet-Switch Reset Sequencing

**[C]** `LSWTCH_SWC` ("Leo switch") is the VIP-managed control path for the Ethernet switch.
"LEO" itself is **the Intel A3960 SoC**, not the switch: the VIP toggles `IO_IOC_LEO_RESET`
(LOW/HIGH) around SoC reset, and logs `LEO_FIRMWARE is not running` /
`IOC initialized switch Configuration in the absence of LEO firmware` while the SoC has not
yet come up — the VIP brings the Ethernet switch up in a default configuration before the
SoC-hosted "LEO firmware" (switch-management agent running on the SoC) is available.

Source: `diagnostics/Y175_session.log` lines 90, 94, 129-130, 192-193, 231-232.

### 4.3 PLC Power-Level Handshake / BootCounter

**[C]** `PLC` logs the VIP↔SoC power-level handshake: `IPC RX: New Power Level 1 received from
SoC` (t=732 ms), `New Power Level 2 received from SoC` (t=1285 ms), and `plc_timer_value for
SoC SOH Timeout = 1500` (ms) — the VIP's watchdog window for SoC state-of-health. The same
module reads the boot counter from NVM at startup: `Rte_Pim_PLC_BootCounter_PIM is : 4067`
(`Nvm_ErrorStatus = 0`).

Source: `diagnostics/Y175_session.log` lines 80-82, 171, 204.

The [mute-hold reset sequence](../../runtime/boot_timing.md#mute-hold-reset-and-adb-reboot-boundaries-2026-11-15)
shows this handshake completing before the VIP uptime resets, and distinguishes the observed
hardware-button reset from the statically traced Android reboot entry.

### 4.4 u-blox GNSS on the VIP UART

**[C]** A u-blox GNSS receiver is wired to a VIP UART, not directly to the SoC. Boot log:
`UBLOX is not supported in the current hardware` (t=822 ms, logged as an error despite the
receiver being physically present and polled), followed by repeated baud-rate probing —
`Change the VIP UART BR to 115200 bps`, then after 15 failed `UBX_CFG_PRT` polls, `Change the
VIP UART BR to 9600 bps`, ending in `u-blox UART BR unknown`. This confirms GNSS rides a VIP
UART channel (§2); it does not identify which channel.

Source: `diagnostics/Y175_session.log` lines 173, 198, 270-271, 298-299.

### 4.5 SBAT Ticket Validation and ProtoKey Seed-from-BCM

**[C]** SBAT (Secure Boot Anti-Theft) module on the live boot trace:

```
keyNBID = 0x0000
appNBID = 0x0001
ECU_ID: = <ECU_ID>   (16 bytes, REDACTED — full unit identifier)
SbaTicketValidation validation failed: 0x0
```

Validation fails (ticket is effectively unprogrammed) but boot continues — consistent with the
"SBAT failure is non-blocking" finding documented in [`../teardown.md`](../teardown.md)
(deep-EEPROM section) and in [`../../platform/security.md`](../../platform/security.md). This
document does not reproduce that analysis; see those references for the full SBAT/ProtoKey
security-mechanism writeup.

Source: `diagnostics/Y175_session.log` lines 211-215.

**[C]** `PROTOKEY` on the same trace logs `Receives invalid seed [1] from BCM` /
`Receives invalid seed [2] from BCM` repeatedly before the BCM seed becomes valid later in
boot — on this airgapped bench (no live BCM/vehicle network — **[I]** inferred, not read from
the log), ProtoKey seed exchange with the BCM over CAN fails by default, consistent with the
three-phase ProtoKey sequence documented in [`../teardown.md`](../teardown.md) (deep-EEPROM
section) and [`../../platform/security.md`](../../platform/security.md).

Source: `diagnostics/Y175_session.log` lines 100-101, 197, 199.

**[C] Live Y181 confirmation (2026-11-12):** the bench radio's `viplog.log` + `viplog.log.rot`
(2026-11-11/12) contain **7113** `Receives invalid seed [n] from BCM` lines by raw `grep`
(7114 in the header-stripped re-derivation; 3556 for seed [1], 3557 for [2] raw — corrected
2026-11-12 from "3553/3556, remainder truncated", which the raw files do not support) against
only **9** `Seed %d taken from GMLAN` lines (all in `viplog.log`, none in the `.rot`). Repeating
every ~1 s with no BCM on the bench (**[I]** inferred, not read from the log), this reads as a
handshake no body-control module ever answers (bench artifact, not a fault) — counts read
directly, cause inferred.

The VIP power-state machine (`SS_LOG evt=` / `st=` lines) in the same log walks
`NormalInit -> StartupDelayWait -> FullOperationStartup -> InfotainmentActive`,
`Propulsion` / `Accessory` / `OffModeActive` vehicle states,
`INFOTAINMENT_ACTIVITY_TIMEOUT -> BackgroundSleepTimeout -> Shutdown`; events observed include
`evDriverDoorOpen`/`evDriverDoorClosed` (14/15 raw line counts, corrected 2026-11-12 from
14/14), `evRemoteReflashProgrammingEnd` (15), `evPowerModeOn/Off`,
`evKeyIdentificationDeviceRemoved`, `evResetLocalInfotainmentTimer` (576) — counts read over
both log files. The door events on a bench unit indicate the VIP receives (or synthesizes)
body state; their source is **[?]** not identified here.

- Calibrations referenced in the same trace: VIN relearn, cluster animation, shutdown
  animation failsafe (15 s).

## 5. Sources

- `diagnostics/Y175_session.log` (lines cited inline per section above).
- Bench radio `W231E-Y181.3.2-SIHM22B-499.3`: `viplog.log`, `viplog.log.rot` (2026-11-11/12),
  `/update_cache/update/moduleinfo`, `/update_cache/update/hw.conf`, `ghs.log`, recovery
  `last_log.*`.
- [RH850/F1K hardware manual, Rev. 1.10](../datasheets/Renesas_RH850_F1K_HW_manual_rev110.pdf)
  (R01UH0562EJ0110, 2016-11-30): Table 2.3 (pp. 89-93, 176-pin assignments), Table 4.1 (p.262,
  memory map), Table 19.9 (p.833, RLIN3 TX/RX signal names), §6 p.290 / §37.6 p.2757 (serial
  programming mode), Table 37.3 p.2753 / Table 37.4 p.2754 (flash read / programmer
  authentication), register `RLN34LUOER` p.907, p.949 (reception enable gating), port
  alternate-function tables pp. 142, 144, 153, 155, 158.
- [Renesas flash hardware-interface manual](https://www.renesas.com/en/document/mah/rh850f1k-users-manual-flash-hardware-interface?language=en)
  (R01UH0622EJ0130), §5.1 p.42.
- [Renesas G3KH software manual](https://www.renesas.com/en/document/mas/rh850g3kh-users-manual-software?language=en)
  (R01US0165EJ0120), §2.1, §2.7, §5, §7 pp.161-163 (branch-encoding correction).
- Renesas [PCN HPLM-2024-0029, p. 4](https://www.renesas.com/en/document/pcn/addition-production-sites-and-material-changes-rh850f1k-seriespc-mcu-a034ae).
- VIP_APP firmware `85759599` (static trace, §2.3): file offsets `0x74F14`, `0x89D78`,
  `0x640E4`, `0x63E6E`, `0x63B3C`, `0x5C506`, `0x62F30`, `0xE1362`, `0x637E4`, `0x89DFC`,
  `0x65398`, `0x643A0`, `0x74F5C`, `0x75538`, `0x63E94`, `0x64060`, `0x8D04C`, `0x8D04A`;
  load-map offset `0x27A7A`.
- [`../../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#native-probe-to-vip-transport-and-elk-prerequisites--2026-11-17)
  (native Probe-to-VIP transport trace).
- [`../../diagnostics/diagnosticsd_dids_and_dtc.md`](../../diagnostics/diagnosticsd_dids_and_dtc.md#rh850-uart-correlation-with-direct-t1-did-reads-2026-11-14).
- [`../../diagnostics/diagnosticsd_routines_and_recovery.md`](../../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
- [`../../runtime/boot_timing.md`](../../runtime/boot_timing.md#mute-hold-reset-and-adb-reboot-boundaries-2026-11-15).
- [`../teardown.md`](../teardown.md) — originating source document, lines 659-1035 (RH850/F1K
  package/pinout through VIP MCU boot-log details; deep-EEPROM/ProtoKey sequence detail
  continues past line 1035, out of this document's scope).
