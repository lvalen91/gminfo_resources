# Audio Path

Scope: audio signal chain from tuner/SoC to the external Bose amplifier, with the wiring and
connector detail of the radio ↔ amplifier links.
Related: [`connectors.md`](connectors.md), [`../module/identity_bom.md`](../module/identity_bom.md),
[`../../platform/avb_audio_transport.md`](../../platform/avb_audio_transport.md),
[`../../audio/automotive_audio.md`](../../audio/automotive_audio.md).

Confidence tags: **[C]** confirmed · **[I]** inferred.

## 1. Configuration

The test vehicle (RPO UQA) uses the *Mid/High W/ Amplifier* configuration. The radio outputs no
speaker-level signals. The amplifier is a networked AVB endpoint.

- Amplifier address `192.168.1.103` (`AMP_ETH`; `research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt`).
- Calibration: `External Amp = Present`, `AMPCAL=3` (`evidence/session-logs/security_assessment_20DEC25.txt`).
- VIP boot order includes `AMP_MGR_SWC` (Audio Amplifier Manager).
- Speaker ± pairs terminate at the amplifier connectors (T3), not the radio. [C]

## 2. Signal Chain

```
AM/FM/HD antenna
  → NXP SAF7751 (tuner + audio DSP)
  → I2S/TDM → Intel A3960 SoC (AudioFlinger → PulseAudio)
  → Intel I210 GbE MAC (AVB, gPTP master, 1000 Mbit/s)
  → Ethernet switch (BCM89551 on MY22/DV unit; Marvell 88Q5050 on live Y181 radio)
  → AVB Ethernet pair in the Stac64 harness (Ethernet Bus 6)
  → NXP TDF8532 in the Bose amplifier (T3)
  → speakers
```

| Parameter | Value |
|-----------|-------|
| Native format | 48 kHz, PCM 16-bit stereo |
| CarAudioService | 8 buses (bus0–bus7), 6 volume groups (media, nav, call, alarm, notification, …). bus8–bus13 are Harman-HAL-internal graph nodes, not CarAudioService buses. |
| AVB streams | 3 RX + 3 TX, FIFO priority 50 |
| I2C control | SAF7751 / TDF8532 control on i2c-3 (`audioserver:audioserver`) |

Shipped Marvell port-speed settings and unresolved port numbering:
[`platform/ethernet_networking.md` §Shipped switch speeds](../../platform/ethernet_networking.md#23-shipped-switch-speeds-c-2026-11-13).

## 3. Radio ↔ Amplifier Links (ALLDATA UQA schematic) — [C]

T3 Audio Amplifier is the CSM in this audio chain (RPO UQA). Two independent links connect it to
the radio, on separate connectors and circuit families. Loss of one does not disable the other.

| Circuit | Wire | Radio side | Amp side | Role |
|---------|------|-----------|----------|------|
| Ethernet Bus 6 [+] | 7215 YE | A11 X11 p8 | T3 X3 | AVB audio data plane |
| Ethernet Bus 6 [−] | 7214 GN | A11 X11 p9 | T3 X3 | AVB audio data plane |
| AUTOSAR CAN 5 [+] | 4985 BU/WH | A11 X6 p9 (VIP CAN) | T3 X3 | Control plane: amp control / serial data |
| AUTOSAR CAN 5 [−] | 4984 BU/YE | A11 X6 p10 (VIP CAN) | T3 X3 | Control plane: amp control / serial data |

CAN 5 is also named "SER DATA 5" by the DPS gateway scan
([`../../platform/vehicle_network.md`](../../platform/vehicle_network.md), Plane 1).
Amplifier power: T3 X1/X4 pin 4 Battery+ (3740 RD/YE), pin 8 signal ground (1051 BK/WH).

## 4. Amplifier Connectors (T3) — [C]

Circuit numbers from ALLDATA T3 end views.

| Conn | OEM P/N | Housing | Pins (circuit) |
|------|---------|---------|----------------|
| X1 | 33223792 | 8-way F 2.8 OCS (BK) | p1 Sub+ (346), p2 RF1+ (200), p3 LF1+ (201), p4 Batt+ (3740), p5 Sub− (1794), p6 RF−1 (117), p7 LF−1 (118), p8 Gnd (1051) |
| X4 | 33223792 | 8-way F 2.8 OCS (BK) | Same table as X1. Duplication unexplained by source; probably a second housing or mating half [I]. |
| X2 | 15512506 | 16-way F 1.5 OCS (BK) | LF-mid ± (1857/1957), RF-mid ± (1853/1953), LR ± (199/116), RR ± (46/115), front-center ± (1860/1960) |
| X3 | 35016343 | 16-way F 0.64 OCS (BK) | Eth Bus 6 ± p1/2 (7215/7214); ANC mic 1 signal/feedback p5/13 (3005/3008); AUTOSAR CAN 5 ± p11/12 (4985/4984) |

## 5. Radio-Side Speaker Cavities

The radio's own X5/X6 speaker-level cavities belong to the *U95-UQF* non-amplified variant and
are not wired on the UQA truck. Per-pin circuit numbers: [`connectors.md`](connectors.md) §1.1
(X5), §1.2 and §4.4 (X6).

## 6. Sources

- ALLDATA *Audio Amplifier Power, Ground and Serial Data (UQA)*; *Speakers (UQA)* vs *Speakers
  (U95-UQF)*; T3 connector end views.
- `research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt`; `evidence/session-logs/security_assessment_20DEC25.txt`.
