# GM CAN / UDS Reference — 2024 Silverado ICE (Y175 Platform)

> Assembled from: DBC files (gm_global_a_*), GateKeeperESP_services.h, diagnosticsd live sweep docs, gminfo_resources diagnostics docs.  
> **Coverage:** A11 infotainment (Y175/Y181B) Ethernet UDS endpoint + Global A powertrain/chassis CAN buses.  
> Values already confirmed live on the T1 endpoint are marked **[live]**; spec-only entries are **[spec]**; CAN-capture only **[CAN]**.

---

## 1. Wire Transport — GM Ethernet Diagnostics

**NOT** ISO-TP CAN or DoIP. Custom GM TCP framing:

```
[SRC_ADDR : 2 bytes BE] [TGT_ADDR : 2 bytes BE] [PAYLOAD_LEN : 4 bytes BE] [UDS payload]
```

| Parameter | Value |
|-----------|-------|
| TCP port | 49156 |
| Tester address | `0x00F4` (also `0x00F5` for basic reads) |
| ECU address | `0x0084` |
| Process | `/vendor/bin/diagnosticsd`, PID ~599, runs as root (UID 0) |
| Session P2 timing | `50 03 00 64 01 F2` → P2=100ms, P2*=498ms |
| CAN5 physical | 500 kbit/s, request `0x14DA80F2`, response `0x145AF280` |

---

## 2. UDS Service Map

### Native Ethernet converter map (from diagnosticsd ELF `0x14cf8`)

| Native enum | Wire SID | Standard service |
|------------:|---------|-----------------|
| 1 | `0x22` | ReadDataByIdentifier |
| 2 | `0x2E` | WriteDataByIdentifier |
| 4 | `0x2F` | InputOutputControlByIdentifier |
| 6 | `0x31` | RoutineControl |
| 7 | `0x10` | DiagnosticSessionControl |
| 8 | `0x28` | CommunicationControl |
| 9 | `0x27` | SecurityAccess |
| 10 | `0x34` | RequestDownload |
| 11 | `0x36` | TransferData |
| 12 | `0x37` | RequestTransferExit |
| 13 | `0x19` | ReadDTCInformation |
| 17 | `0x14` | ClearDiagnosticInformation |
| 18 | `0x85` | ControlDTCSetting |

**Not in native map** (SID → unknown service conversion, NRC 25): `0x11` ECUReset, `0x23` ReadMemoryByAddress, `0x24`, `0x35`, `0x38`, `0x83`.  
`0x3E` TesterPresent is handled separately (confirmed live: `3E 00` → `7E 00`).

### Full UDS service reference (GateKeeperESP_services.h + ISO 14229)

| SID | Rsp SID | Service | Live T1 result |
|-----|---------|---------|---------------|
| `0x10` | `0x50` | DiagnosticSessionControl | **[live]** `01` default ✓, `03` extended ✓, `02` → NRC 22, `04` → NRC 12 |
| `0x11` | `0x51` | ECUReset | **[live]** `11 01` → NRC 25 (no subnet response) |
| `0x14` | `0x54` | ClearDiagnosticInformation | mapped |
| `0x19` | `0x59` | ReadDTCInformation | **[live]** all 128 subfunctions positive (stub — zero-filled) |
| `0x22` | `0x62` | ReadDataByIdentifier | **[live]** 135 DIDs positive (see §4) |
| `0x23` | `0x63` | ReadMemoryByAddress | **[live]** passes gate at lvl 09/0B → NRC 25 |
| `0x24` | `0x64` | ReadScalingDataByIdentifier | **[live]** NRC 11 |
| `0x27` | `0x67` | SecurityAccess | **[live]** levels 01,03,05,09,0B,0D,11,13,15 granted |
| `0x28` | `0x68` | CommunicationControl | mapped |
| `0x2A` | `0x6A` | ReadDataByIdentifierPeriodic | spec |
| `0x2C` | `0x6C` | DynamicallyDefineDataIdentifier | spec |
| `0x2E` | `0x6E` | WriteDataByIdentifier | mapped; select DIDs writable with SecurityAccess |
| `0x2F` | `0x6F` | InputOutputControlByIdentifier | **[live]** 24 of 25 IOCIDs operated (see §6) |
| `0x31` | `0x71` | RoutineControl | **[live]** native 0249/0475; Java 11 handlers (see §5) |
| `0x34` | `0x74` | RequestDownload | mapped (native 10) |
| `0x35` | `0x75` | RequestUpload | not in native map |
| `0x36` | `0x76` | TransferData | mapped (native 11) |
| `0x37` | `0x77` | RequestTransferExit | mapped (native 12) |
| `0x38` | `0x78` | RequestFileTransfer | not in native map; probes → NRC 11 |
| `0x3D` | `0x7D` | WriteMemoryByAddress | spec |
| `0x3E` | `0x7E` | TesterPresent | **[live]** `3E 00` → `7E 00` |
| `0x83` | `0xC3` | AccessTimingParameters | **[live]** NRC 11 |
| `0x85` | `0xC5` | ControlDTCSetting | mapped (native 18) |

### SAE J1979 (OBD-II mode bytes)

| Mode | Rsp | Function |
|------|-----|----------|
| `0x01` | `0x41` | Current data (standard PIDs) |
| `0x02` | `0x42` | Freeze frame |
| `0x03` | `0x43` | Stored DTCs |
| `0x04` | `0x44` | Clear DTCs |
| `0x07` | `0x47` | Pending DTCs |
| `0x09` | `0x49` | Vehicle information |

### Legacy/internal GMLAN SID labels (do not use as T1 wire SIDs)

| Native label | Wire SID (old/GMW3110) | Wire SID (UDS) |
|-------------|----------------------|----------------|
| `DIAG_DID_READ` | `0x1A` | `0x22` |
| `DIAG_DID_WRITE` | `0x3B` | `0x2E` |
| `DIAG_RID_CONTROL` | `0x70` | `0x31` |
| `MSG_RID` | `0x76` | `0x37` |
| `DIAG_CPID_CONTROL` | `0xAE` | `0x2F` |
| `DIAG_REQUEST_DATA_TRANSFER` | `0x35` | `0x34` |

---

## 3. DiagnosticSession & SecurityAccess Details

### Session types
| Sub | Session | Notes |
|-----|---------|-------|
| `01` | Default | Always available |
| `02` | Programming | Requires auth power mode; **[live]** NRC 22 without it |
| `03` | Extended | **[live]** `10 03` → `50 03 00 64 01 F2` |
| `04` | Safety-system diagnostic | **[live]** NRC 12 (subFunctionNotSupported) |

### SecurityAccess levels confirmed

Seed shape: 31 bytes all `0xFF`.  Response shape: 12 bytes all `0x00`.  
(Note: this is the documented degenerate exchange observed on this bench; not a general algorithm description.)

| Level pair | Grant name | Known extra permissions |
|------------|-----------|------------------------|
| `01`/`02` | ETHERNET tier | Programming session gate, 2E F190/F198/F199, RID 021E/0200/0205 |
| `03`/`04` | — | Programming session, RID 0200/0204/0205 |
| `05`/`06` | — | Programming session, RID 0475 |
| `09`/`0A` | Engineering | 22 F0A7, 23 memory gate, 2E E010 |
| `0B`/`0C` | — | 22 F0A7, 23 memory gate |
| `0D`/`0E` | — | 22 F0A7, 2E E010 |
| `11`/`12` | — | 2E F190/F198/F199 |
| `13`/`14` | — | 2E F190/F198/F199, RID 0200/0205 |
| `15`/`16` | — | 2E F190/F198/F199 |
| `5F`/`60` | — | Seed request → NRC 25 (path unresolved) |

Trust tier hierarchy: `VIP > ETHERNET > NOTIFICATION`

---

## 4. DID Catalog — Exhaustive Sweep Results

Sweep: all 65536 DIDs, extended session + SecurityAccess level 09, T1 Ethernet, 2026-11-14.  
**135 positive** out of 65536. All below returned `62 <DID> <data>`:

| DID | Bytes | Known meaning |
|-----|------:|--------------|
| `5735` | 32 | Native DID — startup-time/startup-type listeners |
| `573D` | 32 | Native DID — boot-time listener |
| `5730`–`573E` (10 DIDs) | 32 ea. | 57xx listener group |
| `573A` | 1 | — |
| `573B` | 4 | — |
| `F180` | 15 | Boot module IDs: 2 records (tag47=85056831/AA, tag48=85098661/AB) |
| `F181` | 15 | Software IDs: 2 records (tag01=85759599/CJ, tag15=85098662/BM) |
| `F182` | 197 | Cal+component IDs: 28 seven-byte records (see §4a) |
| `F190` | 17 | VIN (17 bytes, omitted) |
| `F198` | 10 | Programming date/time |
| `F199` | 4 | — |
| `F1CB` | 4 | — |
| `F1CC` | 4 | — |
| `F1A0` | 1 | VIP state byte (FF=255 normal) **[VIP-correlated]** |
| `F1B0` | 1 | — |
| `F1E4` | 39 | — |
| `F1DE` | 7 | — |
| `F081` | 6 | — |
| `F084` | 14 | — |
| `F08C` | 1 | — |
| `F0A7` | 1 | Protected read (level 09/0B/0D only) |
| `F0B4` | 16 | — **[VIP-correlated]** |
| `F0F0` | 28 | — |
| `F0F1` | 2 | — |
| `F0F2` | 2 | — |
| `F0F3` | 16 | — **[VIP-correlated]** |
| `F0F6` | 24 | — |
| `F0FA` | 99 | — |
| `F0FB` | 2 | — |
| `C002`–`C009` (6 DIDs) | 1–12 | C0xx group (SXM/HW revisions area) |
| `C00E` | 16 | — |
| `C00F` | 3 | — |
| `4FF0` | 3960 | Largest response (3960 bytes) |
| `4FFA` | 36 | — |
| `4FFB` | 2 | — |
| `4F8E`/`4F8F` | 75 ea. | — |
| `4FE2`–`4FE8` (6 DIDs) | 1–10 | — |
| `5FA7`–`5FAE` (8 DIDs) | 75 ea. | — |
| `5812`/`5813`/`5814`/`5815` | 1–5 | Audio source state |
| `5152` | 8 | — |
| `5171` | 12 | — |
| `572E` | 2 | — |
| `4EA8` | 2 | — |
| `4609` | 16 | — |
| `4774`/`4776`/`4781`/`4785`/`478B`/`4791` | 1–56 | — |
| `489F`/`48A0`/`48A1` | 2–3 | — |
| `4394`/`4395` | 113 ea. | — |
| `4396`/`4398`/`43A1`/`43A5`/`43A8`/`43AA`/`43AC`/`43BB`/`43FC` | 1–24 | 43FC = tune encoder IOCID |
| `4424`/`4426` | 2 ea. | FM/AM tuner frequency |
| `4478` | 1 | AF enable status |
| `447A` | 102 | — |
| `440A`–`440C` | 1 ea. | Diagnostic tone channel (RF/RR/LR) |
| `41D8`–`41EF` (13 DIDs) | 1 ea. | IOCID current state DIDs |
| `41F5` | 190 | — |
| `42AA`–`42C5` (22 DIDs) | 1–80 | — |

**NRC 11 (serviceNotSupported):** F09A, F0F4, F1DB, F1DC  
**NRC 22 (conditionsNotCorrect):** DID 0249, 0475 (and others needing prerequisites)  
**NRC 31 (requestOutOfRange):** 65376 DIDs (most of the space)

### 4a. F182 Component Identity Records

28 records, each 7 bytes: `[1-byte tag][4-byte part BE][2-byte version]`

| Tag (hex) | Component | Part number | DLS |
|-----------|-----------|-------------|-----|
| `16` | SOC_SYSTEM | 85759600 | GV |
| `17` | SOC_BOOT | 85759602 | GV |
| `18` | SOC_UTILS | 85759613 | GV |
| `1A` | SOC_VENDOR | 85759604 | GV |
| `1C` | SXM | 84999468 | AC |
| `1D` | GPS | 0 | AA |
| `33` | TUNER | 0 | AA |
| `34` | ETH_SWITCH | 85759612 | AA |
| `35` | SOC_ANDROID_ODM | 0 | AA |
| `36` | SOC_ANDROID_ACPI | 0 | AA |
| `37` | SOC_ACPIO | 85759610 | GV |
| `38` | SOC_VBMETA | 85759606 | GV |
| `39` | SOC_PRODUCT | 85759608 | GV |
| `51` | FIDM | 84961617 | AA |
| `02`–`0F` | Calibration modules (14) | base 70008/DLS00 | — |

---

## 5. Routine Control (RID) Catalog

Request format: `31 <start=01/stop=02/results=03> <RID-hi> <RID-lo> [params]`  
Positive response: `71 <sub> <RID-hi> <RID-lo> [data]`

### Native local handlers (diagnosticsd ELF)

| RID | Handler | Function | Notes |
|-----|---------|----------|-------|
| `0249` | `RID0249Handler` at `0x2acc0`–`0x2ad00` | `CalibrationAccessor::clearAllOverrides()` | start → results both execute clear; **[live]** completed |
| `0475` | `RID0475Handler` at `0x2ade0` | Authorized background file transfer | delegates to `gm_update_engine` DiagnosticsHandler; requires level 05 |

### Java handlers (DelayedWKSApp.apk classes2.dex — MY22/MY23)

| RID | Function | Prerequisite |
|-----|----------|-------------|
| `0209` | Check calibration programmed state | Programming session |
| `021E` | VIP pass-through request/response | Level 01/03/05; auth power mode 1 or 2 |
| `0247` | Vehicle-settings restore + wipeUserData | — |
| `0248` | GM favorites reset (00=audio, 01=phone, 02=nav, 03=no-op) | Level 09; option byte required |
| `0254` | LCM delete all records | Level 09; **[live]** `71 01 02 54` |
| `0260` | LCM reset download counters | Level 09; option 05 accepted; others NRC 31 |
| `0300` | Fixed one-byte response `10` | Programming session |
| `03D8` | Audio/HMI test enable (results: bit0=unmuted, bit1=screen, bit2=AM, bit3=FM) | — ; **[live]** result 07 |
| `0405` | Broadcast `com.gm.android.action.REGISTRATION_START` | — ; **[live]** `71 01 04 05` |
| `FF00` | `diagEraseOverrideFile` / `handleEraseMemoryRequest` | — |
| `FF01` | Programmed-state check / programming monitor check | Level 01; **[live]** `71 01 FF 01 00 86 04 03 00` |

### From MDI2 / CAN captures

| RID | Source | Function |
|-----|--------|----------|
| `020E` | MDI2 catalog | wakeUpNetworks (gateway-addressed, not A11) |
| `039B` | DPS CAN capture | Calibration finalization step |
| `FF02` | MDI2 catalog | eraseMemory |
| `0332` | Research candidate | ADB enable candidate — **NRC 31 on T1**, not in live APK |
| `F000`/`8180` | Research | ELK entry routine (profile 0D + application-word change required) |

---

## 6. I/O Control (IOCID) Catalog

Request format: `2F <IOCID-hi> <IOCID-lo> <control=00/01/02/03> [params]`  
Control params: `00`=returnControl, `01`=resetDefault, `02`=freeze, `03`=shortTermAdjustment.

| IOCID | Function | Live result |
|-------|----------|------------|
| `41D8` | Key simulation: `0A`=MediaPrev(88), `0B`=MediaNext(87), `0C`=Home(3), `0D`=Enter(66), `11`=Back(4), `12`=VolUp(24), `13`=VolDown(25) | **[live]** Home 0C accepted |
| `41DA` | Display test pattern: `00`=normal, `01`=SMPTE, `02`=Philips, `03`=Tux | **[live]** all patterns confirmed, hashes verified |
| `41DB` | Steering-wheel key sim: `01`=FavUp(137), `02`=FavDown(138), `03`=VolUp(24), `04`=VolDown(25), `05`=Speech(231), `06`=Mute(164) | **[live]** vol cycle 15→14→15 |
| `41DE` | OnStar broadcasts (includes emergency-call branch) | Not tested |
| `41E2` | Diagnostic tone — LF speaker, freq=`50*n+25` Hz | **[live]** 09→475Hz accepted |
| `41E4` | Unknown | — |
| `41E7` | Volume (diagnostic group) | **[live]** 15→14→15, DID readback |
| `41E9`/`41EA`/`41EC` | Equalizer bands | **[live]** 0→1→0, DID readback |
| `41EB` | Balance | **[live]** 0→1→0 |
| `41ED` | Surround | NRC 22 (unavailable) |
| `41EF` | Unknown | — |
| `41F5` | Unknown (190-byte DID) | — |
| `4424` | FM frequency (DID readback, units = `2242` = 87.7 MHz) | **[live]** 87.7→87.9→87.7 |
| `4426` | AM frequency (DID readback, units = `0212` = 530 kHz) | **[live]** 530→540→530 |
| `4428` | DAB control | NRC 22 |
| `4478` | AF enable | Positive response, no effect observed |
| `440A`/`440B`/`440C` | Diagnostic tone — RF / RR / LR speakers | **[live]** each accepted |
| `42AD` | Audio source: `00`=FM, `01`=AM, `03`=USB, `05`=MEDIA | **[live]** FM/AM switching confirmed |
| `4781` | Fader | **[live]** 0→1→0 |
| `4785` | LVM/PDR (stub — always positive) | Stub |
| `4838` | Rejected stub | NRC 31 |
| `43FC` | Tune encoder: 1-byte signed step count (>128 = negative) | **[live]** accepted; no measured tuning |
| `5812`/`5814` | Audio source update | **[live]** USB/MEDIA returned positive; source stayed FM |

---

## 7. CAN Message Dictionary

### 7a. GM Global A — Powertrain Bus (GMLAN / HSCAN)
Protocol: `ProtocolType=GMLAN`, `BusType=CAN`, `UseGMParameterIDs=0`

**ECU nodes:**
| Node ID | Description |
|---------|-------------|
| K16_BECM | Battery Energy Control Module |
| K73_TCIC | Telematics Communication Control Module |
| K9_BCM | Body Control Module |
| K43_PSCM | Power Steering Control Module |
| K17_EBCM | Electronic Brake Control Module |
| K20_ECM | Engine Control Module |
| K114B_HPCM | Hybrid Powertrain Control Module |
| K124_ASCM | Active Safety Control Module |
| EPB | Electric Parking Brake |

**Messages:**

| Dec | Hex | Name | ECU | Bytes | Key signals |
|-----|-----|------|-----|-------|-------------|
| 189 | 0x0BD | EBCMRegenPaddle | K17_EBCM | 7 | RegenPaddle[7\|4@0+] (1,0) |
| 190 | 0x0BE | ECMAcceleratorPos | K20_ECM | 6 | BrakePedalPos[15\|8], GasPedalAndAcc[23\|8] (baseline ACC=62) |
| 201 | 0x0C9 | ECMEngineStatus | K20_ECM | 8 | EngineTPS[39\|8] (×0.3922, 0–100 %), EngineRPM[15\|16] (×0.25 RPM), CruiseMainOn, BrakePressed, Standstill, CruiseActive |
| 209 | 0x0D1 | EBCMBrakePedalSensors | K17_EBCM | 7 | BrakePedalPosition1[5\|14], BrakePedalPosition2[21\|14], BrakeNormalized1/2 |
| 241 | 0x0F1 | EBCMBrakePedalPosition | K17_EBCM | 6 | BrakePressed[1\|1], BrakePedalPosition[15\|8] |
| 298 | 0x12A | BCMDoorBeltStatus | K9_BCM | 8 | RearLeftDoor, FrontLeftDoor, FrontRightDoor, RearRightDoor, LeftSeatBelt, RightSeatBelt |
| 309 | 0x135 | ECMPRDNL | K20_ECM | 8 | PRNDL[2\|3] (0=P,1=N,2=D,3=R), ESPButton |
| 320 | 0x140 | BCMTurnSignals | K9_BCM | 3 | TurnSignals[19\|2] (0=None,1=Left,2=Right), Intellibeam, HighBeamsActive, HighBeamsTemporary |
| 322 | 0x142 | BCMBlindSpotMonitor | K9_BCM | 7 | LeftBSM, RightBSM |
| 328 | 0x148 | PSCM_148 | K43_PSCM | 1 | (empty) |
| 352 | 0x160 | BCMImmobilizer | K9_BCM | 5 | ImmobilizerInfo[7\|32] (non-zero in ignition/accessory) |
| 381 | 0x17D | ESPStatus | K20_ECM | 6 | TractionControlOn[5\|1], MSG17D_AccPower[35\|12] |
| 384 | 0x180 | ASCMLKASteeringCmd | NEO→K124_ASCM | 4 | LKASteeringCmd[2\|11] (Nm), LKASteeringCmdActive, RollingCounter, LKASteeringCmdChecksum |
| 388 | 0x184 | PSCMStatus | K43_PSCM | 8 | LKATorqueDelivered[18\|11] (×0.01 Nm), LKADriverAppldTrq[50\|11] (×0.01 Nm, ±10.24 Nm), HandsOffSWDetectionMode, LKATorqueDeliveredStatus |
| 417 | 0x1A1 | AcceleratorPedal | — | 7 | AcceleratorPedal[55\|8] |
| 451 | 0x1C3 | GasAndAcc | — | 8 | GasPedalAndAcc2[55\|8] (baseline ACC=62) |
| 452 | 0x1C4 | AcceleratorPedal2 | — | 8 | CruiseState[15\|3] (0=Off,1=Active,3=Faulted,4=Standstill), AcceleratorPedal2 |
| 481 | 0x1E1 | ASCMSteeringButton | K124_ASCM | 7 | ACCButtons[46\|3] (1=None,2=Resume,3=Set,5=Main,6=Cancel), LKAButton, DistanceButton, RollingCounter |
| 485 | 0x1E5 | PSCMSteeringAngle | K43_PSCM | 8 | SteeringWheelAngle[15\|16] (×0.0625°, ±2047°), SteeringWheelRate[27\|12] (deg/s) |
| 489 | 0x1E9 | EBCMVehicleDynamic | K17_EBCM | 8 | LateralAcceleration[3\|10] (×0.161 m/s²), YawRate[35\|12] (×0.625), YawRate2[51\|12] (×0.0625 grad/s) |
| 497 | 0x1F1 | BCMGeneralPlatformStatus | K9_BCM | 8 | SystemPowerMode[1\|2] (0=Off,1=Acc,2=Run,3=Crank), ParkBrakeSwActive |
| 500 | 0x1F4 | SportMode | — | 6 | SnowIceMode, SportMode |
| 501 | 0x1F5 | ECMPRDNL2 | K20_ECM | 8 | PRNDL2[27\|4] (0=Shifting,1=P,2=R,3=N,4=D,5=L2,6=L,7=L3), TransmissionState[48\|4] (8=Disengaged,9=Forward,10=Reverse,11=Shifting), ManualMode |
| 532 | 0x214 | BRAKE_RELATED | — | 6 | UserBrakePressure[0\|9] (user-only; lower when pre-filled from ACC) |
| 560 | 0x230 | EPBStatus | EPB | 8 | EPBClosed[12\|1] |
| 562 | 0x232 | EBCMFrictionBrakeStatus | K17_EBCM | 8 | FrictionBrakeUnavailable (1 when ACC brake unavailable; latches if brake cmd blocked) |
| 608 | 0x260 | SPEED_RELATED | — | 8 | ClusterSpeed[31\|8] |
| 711 | 0x2C7 | BECMBatteryVoltageCurrent | K17_EBCM | 6 | HVBatteryVoltage[31\|12] (×0.125 V, 0–511.875 V), HVBatteryCurrent[12\|13] (×0.15 A, ±614 A) |
| 715 | 0x2CB | ASCMGasRegenCmd | K124_ASCM | 8 | GasRegenCmd[10\|19] (×0.125 Nm, offset −22534, range −22534..43002 Nm), GasRegenCmdActive, GasRegenFullStopActive |
| 717 | 0x2CD | ASCM_2CD | K124_ASCM | 5 | (empty) |
| 761 | 0x2F9 | BRAKE_RELATED_2 | — | 7 | UserBrakePressure2[47\|9] |
| 789 | 0x315 | EBCMFrictionBrakeCmd | K124_ASCM | 5 | FrictionBrakeCmd[3\|12], FrictionBrakeMode[7\|4], RollingCounter |
| 800 | 0x320 | AEBCmd | K124_ASCM | 6 | AEBCmd[2\|11], AEBCmdActive[3\|1], AEBCmd2[23\|8], RollingCounter |
| 810 | 0x32A | TCICOnStarGPSPosition | K73_TCIC | 8 | GPSLatitude[7\|32] (milliarcsecond), GPSLongitude[39\|32] (milliarcsecond, offset −2147483648) |
| 840 | 0x348 | EBCMWheelSpdFront | K17_EBCM | 5 | FLWheelSpd[7\|16] (×0.0311 km/h), FRWheelSpd[23\|16] (×0.0311 km/h) |
| 842 | 0x34A | EBCMWheelSpdRear | K17_EBCM | 5 | RLWheelSpd, RRWheelSpd (×0.0311 km/h), RRWheelDir/RLWheelDir (0=Stop,1=Fwd,2=Rev,4=Fault) |
| 869 | 0x365 | ASCM_365 | K124_ASCM | 4 | (empty) |
| 880 | 0x370 | ASCMActiveCruiseControlStatus | K124_ASCM | 6 | ACCSpeedSetpoint[19\|12] (×0.0625 km/h), ACCGapLevel[21\|2] (0=Inactive,1=Near,2=Med,3=Far), ACCCmdActive, ACCLeadCar, FCWAlert[41\|2] |
| 967 | 0x3C7 | EVDriveMode | — | 4 | SinglePedalModeActive, SinglePedalModeRisingEdge, SinglePedalModeFallingEdge |
| 977 | 0x3D1 | ECMCruiseControl | K20_ECM | 8 | CruiseActive[39\|1], CruiseSetSpeed[19\|12] (×0.0625 km/h) |
| 1001 | 0x3E9 | ECMVehicleSpeed | K20_ECM | 8 | VehicleSpeed[7\|16] (×0.01 mph, right-front wheel), VehicleSpeedLeft[39\|16] (×0.01 mph) |
| 1033 | 0x409 | ASCMKeepAlive | NEO | 7 | ASCMKeepAliveAllZero[7\|56] |
| 1034 | 0x40A | ASCM_40A | K124_ASCM | 7 | (empty) |
| 1217 | 0x4C1 | ECMEngineCoolantTemp | K20_ECM | 8 | EngineCoolantTemp[23\|8] (×1 −40°C) |
| 1249 | 0x4E1 | VIN_Part2 | K20_ECM | 8 | VINPart2[7\|64] |
| 1296 | 0x510 | ASCM_510 | K124_ASCM | 4 | (empty) |
| 1300 | 0x514 | VIN_Part1 | K20_ECM | 8 | VINPart1[7\|64] |
| 1912 | 0x778 | PSCM_778 | K43_PSCM | 8 | (empty) |
| 1930 | 0x78A | ASCM_78A | K124_ASCM | 7 | (empty) |

**TX overrides (NEO ↔ ASCM arbitration):**  
`384`, `715`, `789`, `800`, `880`, `1033` can be transmitted by either NEO or K124_ASCM.

---

### 7b. GM Global A — Chassis Bus

| Dec | Hex | Name | ECU | Bytes | Key signals |
|-----|-----|------|-----|-------|-------------|
| 368 | 0x170 | EBCMFrictionBrakeStatus | K17_EBCM | 8 | FrictionBrakePressure[23\|16] |
| 560 | 0x230 | EBCMRegen | K17_EBCM | 6 | Regen[1\|10] |
| 789 | 0x315 | EBCMFrictionBrakeCmd | K17_EBCM | 5 | FrictionBrakeCmd[3\|12], FrictionBrakeMode, RollingCounter |
| 823 | 0x337 | PACMParkAssistCmd | NEO→K43_PSCM | 7 | SteeringWheelCmd[23\|16], SteeringWheelChecksum[47\|16], RollingCounter |

**ECU nodes:** K182_PACM (Parking Assist), K43_PSCM, K17_EBCM, K124_ASCM

---

### 7c. GM Global A — Low Speed Bus (GMLAN extended 29-bit IDs)

Note: IDs are 29-bit extended CAN format (hex values in the ~0x10xxxxxx range).

| Hex ID | Name | ECU | Bytes | Key signals |
|--------|------|-----|-------|-------------|
| 0x1056E400 | DriverDoorStatus | GMLAN | 1 | DriverDoorOpened[0\|1] |
| 0x103E5000 | Chime | NEO→GMLAN | 5 | ChimeType[7\|8], ChimeRepeat[23\|8], ChimeDuration[15\|8] |
| 0x102A5000 | BlinkerStatus | GMLAN | 5 | RightBlinker[6\|1], LeftBlinker[7\|1], BlinkerLight[25\|1] |
| 0x1023F400 | SteeringWheelAngle | GMLAN | 8 | SteeringWheelAngle[39\|16] (×0.0625°, −540..540°) |
| 0x102AF800 | GearShifter | GMLAN | 8 | GearShifter[17\|2] (0=Drive/Low,3=Park) |
| 0x102AE000 | GasPedalRegenCruise | GMLAN | 8 | GasPedal[47\|8] (0–254), MaxRegen[12\|1], CruiseControlActive[56\|1] |
| 0x1023C000 | BrakePedal | GMLAN | 2 | BrakeLevel[2\|2] (0–3), BrakeSensor[15\|8] (0–255) |
| 0x1066C800 | WheelSpeed | GMLAN | 8 | WheelSpeedFL/FR/RL/RR[7,39,23,55\|16] (×0.01 yd/s, 0–70) |
| 0x1023C800 | VehicleSpeed | GMLAN | 8 | VehicleSpeed1[7\|16] (×0.01 mph), VehicleSpeed2[39\|16] |
| 0x1072A000 | CruiseButtons | GMLAN | 3 | CruiseButtons[3\|3] (1=None,2=Resume,3=Set,5=Main,6=Cancel) |
| 0x1072A400 | CruiseButtons2 | GMLAN | 1 | LKAGapButton[1\|2] |
| 0x10740299 | LeftRadar | GMLAN | 2 | BSM_Indicator_Light[4\|1] |
| 0x1074081B | RightRadar | GMLAN | 2 | BSM_Indicator_Light[0\|1] |

---

## 7d. T1XX ECU Diagnostic Address Map (from `mdi2_client/mdi2/data/ecu_map.json`)

Tester address: `0xF1`. Request pattern: `0x14DAxxF1` (xx = ECU addr). Response varies by ECU.

| ECU addr (hex) | Module | Request ID | Response ID |
|----------------|--------|------------|-------------|
| `0x11` | ECM | 14DA11F1 | 142AF111 |
| `0x18` | TCM | 14DA18F1 | 142AF118 |
| `0x1A` | EOCM | 14DA1AF1 | 142AF11A |
| `0x28` | BCM | 14DA28F1 | 142AF128 |
| `0x31` | TCM2 | 14DA31F1 | 142AF131 |
| `0x40` | VCM (61 sw modules) | 14DA40F1 | 145AF140 |
| `0x41` | TEHCM | 14DA41F1 | 145AF141 |
| `0x45` | CGM/gateway | 14DA45F1 | 14DAF145 (anomalous) |
| `0x58` | IPC | 14DA58F1 | 141AF158 |
| `0x59` | EBCM | 14DA59F1 | 141AF159 |
| `0x60` | RCDLR | 14DA60F1 | 141AF160 |
| `0x68` | HVAC | 14DA68F1 | 141AF168 |
| `0x6D` | TCCM | 14DA6DF1 | 141AF16D |
| `0x75` | SDM (airbag) | 14DA75F1 | 141AF175 |
| `0x80` | Radio / A11 (infotainment) | 14DA80F1 | 144AF180 |
| `0x81` | AMP | 14DA81F1 | 144AF181 |
| `0x97` | HUD | 14DA97F1 | 144AF197 |
| `0xA4` | TPMS | 14DAA4F1 | 144AF1A4 |
| `0xA8` | PDM | 14DAA8F1 | 144AF1A8 |
| `0xB9` | Camera | 14DAB9F1 | 144AF1B9 |
| `0xBA` | ParkAssist | 14DABAF1 | 144AF1BA |
| `0xBD` | TRLM | 14DABDF1 | 144AF1BD |
| `0xBE` | VGRS | 14DABEF1 | 144AF1BE |
| `0xBF` | PLGM | 14DABFF1 | 144AF1BF |

**Note:** The Y175 Ethernet endpoint uses a different transport than ISO-TP CAN. On T1 Ethernet (port 49156), tester `0x00F4`, ECU `0x0084`. CAN5 direct: request `0x14DA80F2`, response `0x145AF280`.

---

## 8. HIDL Interfaces Registered by diagnosticsd

| Interface | Function |
|-----------|----------|
| `vendor.gm.diagnostics.ethernet@1.0::IDiagnosticsEthernetService` | Ethernet diagnostic bridge (main) |
| `vendor.gm.diagnostics.bridge@1.0::IDiagnosticsBridgeService` | RTOS bridge |
| `vendor.gm.diagnostics.obd@1.0::IDiagnosticsOBDService` | OBD bridge (Binder, uid=2000) |
| `vendor.gm.diagnostics.internal@1.0::IDiagnosticsInternalService` | Internal/privileged channel |
| `vendor.harman.hardware.ame@1.0::IDiagnostics` | AME HAL (Apple auth chip, Google key, USB/WiFi/ETH status) |
| `vendor.gm.panel@1.0::IPanelDiagnostics` | Panel/cluster diagnostics |

VHAL key properties:
- `HW_KEY_INJECT` = `0x21410165`
- `HW_KEY_ENABLE` = `0x21410163`
- Mute 164 → internal 1003; Speech 231 → internal 1002

---

## 9. DTC Response Selector Map (from static stub analysis)

`19 <selector>` → `59 <selector> <zero-padded data>` — all 128 subfunctions positive but stub-filled.

| Selector(s) hex | Data bytes |
|-----------------|------------|
| 01, 04, 06, 07, 10, 11, 12, 42 | 4 (all zero) |
| 02, 05, 08, 09, 0A, 0B, 0C, 0D, 0E, 0F, 13, 15, 16 | 1 (zero) |
| 17 | 2 |
| 18, 19 | 5 |
| 55 | 3 |
| All others | 0 |

---

## 10. Coverage Gaps

| Gap | Notes |
|-----|-------|
| 2024 Silverado ICE-specific CAN messages | DBC files are for Bolt EV / ASCM-platform trucks. ICE-specific powertrain messages (TCM, EPS variants) may differ. |
| DID semantic labels for ~110 DIDs | 42xx/43xx/44xx/47xx/4Fxx/C0xx ranges positive but unlabeled |
| CAN5 / CAN-F1 bus topology | Physical bus addresses (0x14DA80F2/0x145AF280) documented but full node map unknown |
| VIP/GHS separate diagnostic space | F09A, F0F4, F1DB, F1DC show UART correlation but return NRC 11 at this endpoint |
| RID 039B finalization | From DPS CAN capture only; no live T1 routing established |
| IOCID 41E4, 41EF, 41F5 | Present, positive DIDs, function unknown |
| DID 4FF0 (3960 bytes) | Largest response; contents unknown |
| CalDef → DID mapping | 14 calibration modules in F182/CalSets.db; individual caldef → DID write path not established |
| MDI2 did_map.json | Contents not yet fully cataloged |
| Seed/key derivation | Backend component performing key comparison not traced to a specific binary |

---

## 11. Y175/Y181B Commands by Service — What's Supported vs. What Causes NRC 31/33

> This section answers: given a service SID + sub-id/DID/RID, what session and security level are required to avoid requestOutOfRange (NRC 31) or securityAccessDenied (NRC 33)?

### 11a. Service support matrix

| SID | Supported | Minimum context | NRC if wrong |
|-----|-----------|----------------|--------------|
| `0x10` | YES | None (default session always available) | NRC 12/22 for unsupported sub |
| `0x27` | YES | Extended session (`10 03`) for most levels | NRC 35 wrong key; NRC 7F wrong session |
| `0x3E` | YES | Any session | — |
| `0x22` | YES | Default session for 134 DIDs; extended+lvl09 for F0A7 | NRC 31 unknown DID; NRC 33 security |
| `0x2E` | YES (mapped) | Extended session + correct level (varies by DID) | NRC 33 wrong level |
| `0x2F` | YES | Extended session + lvl 01 for most IOCIDs | NRC 31 unknown IOCID; NRC 22 precond |
| `0x31` | YES | Varies by RID (see §11c) | NRC 31 unknown RID; NRC 7F wrong session |
| `0x19` | YES (stub) | Any session | NRC 31 would not occur (all 128 subfuncs accepted) |
| `0x14` | YES (mapped) | Extended session | — |
| `0x28` | YES (mapped) | Extended session | — |
| `0x34` | YES (mapped) | Extended session + programming conditions | NRC 22 conditions |
| `0x36` | YES (mapped) | Active download sequence | — |
| `0x37` | YES (mapped) | Active download sequence | — |
| `0x85` | YES (mapped) | Extended session | — |
| `0x11` | **NOT MAPPED** | — | NRC 25 (no subnet response) |
| `0x23` | **NOT MAPPED** | — | NRC 25 |
| `0x24` | **NOT MAPPED** | — | NRC 11 |
| `0x35` | **NOT MAPPED** | — | NRC 11 |
| `0x38` | **NOT MAPPED** | — | NRC 11 |
| `0x83` | **NOT MAPPED** | — | NRC 11 |

### 11b. DID read (`0x22`) — session and security level required

**Default session (no SecurityAccess needed):** 134 DIDs — all positive DIDs in §4 except F0A7.

**Extended session + SecurityAccess level 09, 0B, or 0D only:**
- `F0A7` (1 byte)

**DIDs returning NRC 11 (serviceNotSupported — VIP forwarding fails at this endpoint):**
- `F09A`, `F0F4`, `F1DB`, `F1DC` — UART correlation shows these reach the VIP but NRC 11 is returned.

**DIDs returning NRC 22 (conditionsNotCorrect — prerequisite not met):**
- `4838`, `5151`, `41ED`, `42B7`, `42BE`, `42A6`–`42A9`, `C001`, `C00A`–`C00F`, `4428`, `4775` (before 03D8 start)

**DIDs returning NRC 31 (requestOutOfRange — not in any handler):**
- Everything not in the §4 positive list (65376 DIDs)

### 11c. DID write (`0x2E`) — security level required

| DID | Security level(s) |
|-----|------------------|
| `F190` (VIN) | 01, 03, 05, 11, 13, 15 |
| `F198` (prog date) | 01, 03, 05, 11, 13, 15 |
| `F199` | 01, 03, 05, 11, 13, 15 |
| `E010` | 09, 0D |
| `F0F4` | 01, 0B, 11 |

### 11d. Routine control (`0x31`) — session and security level required

| RID | Start sub (`01`) | Stop sub (`02`) | Results sub (`03`) | Minimum session | Level |
|-----|-----------------|-----------------|---------------------|----------------|-------|
| `0249` | ✓ (clears cal overrides) | ✓ | ✓ (also clears) | Extended | 01 |
| `0475` | ✓ (background file transfer) | ✓ | ✓ | Extended | **05** |
| `0209` | Checks prog state | — | — | Programming | 01 |
| `021E` | VIP pass-through | — | — | Extended + auth power mode | 01, 03, 05 |
| `0247` | Settings restore + wipe | — | — | Extended | — |
| `0248` | Favorites reset (opt byte required: 00/01/02/03) | — | — | Extended | 09 |
| `0254` | LCM delete records | — | — | Extended | 09 |
| `0260` | LCM reset counters (option 05 only works) | — | — | Extended | 09 |
| `0300` | Returns `10` fixed | — | — | Programming session | — |
| `03D8` | Audio/HMI enable | — | ✓ (bit mask) | Extended | 01 |
| `0405` | Registration broadcast | — | — | Extended | — |
| `FF00` | Erase override file | — | — | Extended | — |
| `FF01` | Programming precheck (returns 8 bytes) | — | — | Extended | 01 |
| `FF02` | Erase memory | — | — | Extended | — |
| `020E` | Wake up networks | — | — | Extended | — |
| `039B` | Calibration finalization | — | — | Programming + CAN | — |
| `0200`, `0205` | — | — | — | Extended | 01, 03, 11, 13 |
| `0204` | — | — | — | Extended | 03, 13 |

**All other RIDs → NRC 31 (requestOutOfRange)** at this endpoint.

**Results sub-function caveat:** `AbstractRIDHandler.handleRequestResultRoutine` throws an exception by default; only `0249` (native, clears overrides), `03D8` (Java, returns state bits), and `0475` (native, delegates to update-engine) have implemented results handlers.

### 11e. I/O control (`0x2F`) — avoiding NRC 31/33

Request: `2F <IOCID-hi> <IOCID-lo> <control> [params]`

| IOCID | Control values | Level | Notes |
|-------|---------------|-------|-------|
| `41D8` | `03 <selector>` / `00` release | 01 | Key sim; selector must be in {0A,0B,0C,0D,11,12,13,...} |
| `41DA` | `03 <0-3>` / `00` | 01 | Display patterns |
| `41DB` | `03 <1-6>` / `00` | 01 | SWC key sim |
| `41E2` | `03 <n>` / `00` | 01 | LF tone; freq=50n+25 Hz |
| `41E7` | `03 <vol>` / `00` | 01 | Volume |
| `41E9`/`41EA`/`41EC` | `03 <val>` / `00` | 01 | EQ bands |
| `41EB` | `03 <val>` / `00` | 01 | Balance |
| `440A`/`440B`/`440C` | `03 <n>` / `00` | 01 | Tone RF/RR/LR |
| `4424` | `03 <freq-hi> <freq-lo>` / `00` | 01 | FM freq |
| `4426` | `03 <freq-hi> <freq-lo>` / `00` | 01 | AM freq |
| `42AD` | `03 <src>` / `00` | 01 | Audio source (00=FM,01=AM,03=USB,05=MEDIA) |
| `4781` | `03 <val>` / `00` | 01 | Fader |
| `43FC` | `03 <steps>` / `00` | 01 | Tune encoder; steps>128=negative |
| `5812`/`5814` | `03 <src>` / `00` | 01 | Audio source update |
| `41DE` | — | — | **Do not send** — OnStar/emergency-call branch |
| `41ED`, `4428` | `03 00` | — | NRC 22 (unavailable) |
| `4838` | `03 00` | — | NRC 31 |
| Any unlisted IOCID | — | — | NRC 31 |

### 11f. Programming session (`0x10 0x02`) — conditions required

The gate is `BackupSystemPowerModeProtectedRemoteProgrammingActive` VHAL signal (`0x2120105C`) = true.  
This signal is not injectable from the bench without the vehicle harness in a specific power state.  
Levels 01/03/05 all required (level 09 granted `021E` rejected with NRC 33).

---

## 12. Public CAN/UDS Resources (Online Research Summary)

### Available public DBC databases

| Resource | URL | Coverage | Limitation |
|----------|-----|----------|-----------|
| comma.ai opendbc | https://github.com/commaai/opendbc | Global A platform (2016–2022.4 Silverado) ADAS signals only | Not 2024 ICE; not VIP/Global B |
| karlyamashita GMLAN_CAN_ID.h | https://github.com/karlyamashita/common_libraries | LSCAN 29-bit body/infotainment IDs (older gen) | Pre-VIP only |
| GMLAN Bible spreadsheet | https://docs.google.com/spreadsheets/d/1qEwOXSr3bWoc2VUhpuIam236OOZxPc2hxpLUsV0xkn0 | LSCAN arbitration IDs (community curated) | HS IDs not covered |
| Opengarages GM 29-bit | Wayback: https://web.archive.org/web/20220124141625/http://opengarages.org/index.php/GM_LAN_29_Bit_ID | Older GMLAN 29-bit reference | Site dead |
| roffe/gocan gmlan | https://github.com/roffe/gocan | GMW3110 service IDs (pre-UDS era) | Legacy protocol, not ISO 14229 UDS |

### Key conclusion on public availability

**No publicly available DID dictionary, routine table, or CAN message database exists for 2024 Silverado ICE (Global B/VIP platform).** The authoritative sources are:
- **GMW8762** — HS CAN message ID definitions (for sale only via IHS/GlobalSpec)
- **GMW3110** — GMLAN diagnostic strategy (for sale, listed inactive)
- **GDS2/SPS/TIS2Web** — dealer-only tool databases, not publicly accessible

The `gminfo_resources` local files (this repo) are the most complete publicly undocumented reference for Y175/Y181B diagnostic behavior.

---

*Last updated: 2026-11-21. Sources: gminfo_resources diagnostics docs, DBC files, GateKeeperESP_services.h, online research (comma.ai opendbc, roffe/gocan, iDoka/awesome-automotive-can-id).*
