# Enumeration Captures

ADB / fastboot enumeration snapshots of the GM Info 3.7 (gminfo37 / A11 Radio) head unit,
collected with `scripts/gm_aaos_enum.sh` + `scripts/quick_security_check.sh` from an
unprivileged shell (uid 2000, SELinux Enforcing). Each set has the same template:
`raw/` (individual command outputs) + summary files + `enumeration_report.txt` +
`pulled_files/*.cil` + `pull_failures.txt`.

## Capture sets (chronological)

| Set | Date | Firmware | Notes |
|-----|------|----------|-------|
| `Y181/` (root) | 2025-12-20 | Y181.3.2 (`W231E-Y181.3.2-SIHM22B-499.3`, kernel 4.19.305) | First Y181 dump |
| `Y175/` | 2026-01-17 | Y175 (`W213E-Y175.5.2-SIHM22B-383.1`, kernel 4.19.283) | Older build |
| `Y181/apr2026/` | 2026-04-07 | Y181.3.2 (same) | Adds `network_scan.txt`, `ghs_attack_surface.txt`, `vulnerability_assessment.txt`, `accounts.txt` |
| `Y181/jun2026/` | 2026-06-21 | Y181.3.2 (same) | **Newest / most authoritative.** Live runtime snapshot; see `CLAIMS_VERIFICATION.md` |
| `VIP_log_2B.174.4.1_10JUL24.txt` | 2024-07-10 | — | VIP MCU UART boot log |

**Authoritative capture:** `Y181/jun2026/` is the newest and its
[`CLAIMS_VERIFICATION.md`](Y181/jun2026/CLAIMS_VERIFICATION.md) cross-checks repo claims against
live evidence (GPU Mesa 21.1.5, Vulkan 1.1.0, c2.android SW decoders, listening ports). Prefer it
over the older sets when they disagree. For corrected facts across the whole repo, see
[`../VERIFICATION.md`](../VERIFICATION.md).

## Notes / caveats

- **The three Y181 sets are the same firmware** (`Y181.3.2`, build 2025-07-22), re-dumped to
  capture runtime deltas — they are *not* different builds. Consequently the static-image
  artifacts are duplicated across them: `raw/kernel_config.txt` (172 KB) and the pulled
  `plat_sepolicy.cil` (~1.8 MB) / `vendor_sepolicy.cil` (~458 KB) are byte-identical in all three,
  and ~60% of `raw/*` is byte-identical between the Dec-2025 and Jun-2026 sets. Only genuinely
  time-varying files differ (`processes`, `logcat`, `meminfo`, `open_ports`, `all_properties`, …).
  This is ~8–10 MB of redundancy retained for self-contained snapshots; it has **not** been
  de-duplicated (doing so would break each set's self-containment — a deliberate open choice).
- **Permission-limited files** (empty/stub): `dmesg.txt`, `world_writable.txt`,
  `rollback_index.txt`, `usb_devices.txt` are empty or denied because the
  capture shell is unprivileged (uid 2000). (`partitions.txt` is captured in most sets —
  a real `/dev/block/by-name` listing — but is denied in `Y181/apr2026/`.) `pull_failures.txt`
  in each set records what could not be pulled. These are expected, not collection errors.
- **PII/redaction:** device serial and VIN are redacted (`<DEVSERIAL_REDACTED>`,
  `XXXXXXXXXXXXXXXXX`) in most files. Redaction has been applied unevenly across sets — if you
  add or regenerate captures, run the redaction step over `serial.txt`, `all_properties.txt`,
  `accounts.txt`, `logcat.txt`, and `enumeration_report.txt`.

## Vehicle module inventory (GM service data — hardware side)

The captures above enumerate the **Android/software** side (ADB, props, packages) of the A11
Radio. For completeness, the **vehicle's ECU inventory** (the modules the radio talks to over
CAN/Ethernet) comes from GM service data (ALLDATA *SPS Control Module References* + *Data Link
References*, 2024 Silverado 2500HD, this VIN). **No UDS/GMLAN diagnostic addresses are published
in ALLDATA** — its "Code" column is the RPO/schematic designator, not a bus address; the repo's
`0x80` (A11) etc. come from captured DPS bus traffic, not these docs.

**Programmable modules (SPS, 32):** A11 Radio · B174W Frontview Camera · B218L/R Side Obstacle
Detection L/R · K4 Assist Step · K9 Body Control · K17 Electronic Brake · K20 Engine Control ·
K29FV Front Seat Heater/Vent · K36 Restraints · K38A Chassis Control Aux · K40D Driver Seat
Memory · K43 Power Steering · K44 Power Take-off · K56 Serial Data Gateway · K56U Special Purpose
Vehicle · K60 Column Lock · K61 Sunroof · K67 Trailer Brake · K68 Trailer Lighting · K69 Transfer
Case · K71 Transmission · K73 Telematics · K85P Restraints OCS Passenger · K111 Fuel Pump Power ·
K157 Video Processing · K182 Parking Assist · K194 Rear Gate · K219 Lighting Control · P16 IPC
Cluster · T1 Accessory AC/DC Power · T3 Audio Amplifier · T22 Wireless Accessory Charging.

**Bus assignments (sample, from *Data Link References*):** K56 gateway learns the CAN
module-address list (loss → DTC U1977 / U3000-42); CAN1 500 kbit/s classical … **CAN6 5 Mbit/s =
diagnostics/programming**, CAN7 = assembly-plant programming only. Ethernet is point-to-point off
the A11/K56 switches — see [`../platform/networking.md`](../platform/networking.md) §Physical
Automotive-Ethernet bus map (Bus 6 = A11↔T3 Bose amp).

**Scan-tool (GDS2) data parameters worth noting** (ALLDATA *Scan Tool Information*):
- **A11 Radio:** per-port (0–6) **Ethernet Rx/Tx failure counts + IP addresses**, Ethernet Bus
  Master Clock, **Manufacturer Enable Counter (MEC)**, Control Module Temp 1/2, Rearview Camera
  supply V/I, Bluetooth device 1–10 status/name, GPS last-fix lat/long, AM/FM freq, Infotainment
  switch 1–8 / knob 1–2 states.
- **T3 Audio Amplifier:** ANC on/off, Mic Status + Input Level 1/2/3 (0–65535), Cylinder
  Deactivation command (8/4-cyl), Calibration Part Number 1–10, End Model P/N, Diagnostic Data
  Identifier.
- **K9 BCM:** Battery Sensor Module (SOC, current, resistance, cranking V/I), theft-deterrent
  states, full exterior-lighting command set, load-shed/RVC modes.
