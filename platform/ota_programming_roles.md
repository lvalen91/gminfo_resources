# OTA & Module Programming Roles — Who Reflashes What (gminfo37 / A11)

Companion to [`ota_update_stack.md`](ota_update_stack.md) (the on-radio OTA engine) and
[`firmware_versions.md`](firmware_versions.md). Question: **GM OTA pushed to the radio can include
calibration of other modules — does a component of the A11 perform SPS/DPS-style programming
itself, or hand off to something that can?**

Sources: [`../research/UPDATE_PROCESS_ANALYSIS.txt`](../research/UPDATE_PROCESS_ANALYSIS.txt),
[`../research/VIP_CONTROL_ANALYSIS.txt`](../research/VIP_CONTROL_ANALYSIS.txt),
[`../research/GM_REMOTE_ACCESS_ANALYSIS.txt`](../research/GM_REMOTE_ACCESS_ANALYSIS.txt),
[`../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md); the
GIS-646 CalDef database ([`../reference/`](../reference/)); the DPS logs
([`../diagnostics/dps/`](../diagnostics/dps/)); the archived Y181 update package.

## Answer (reconciled)

**Both roles exist, split by target and by architecture generation:**

1. The A11 **is** a programming coordinator — GM's CalDefs cast the infotainment as the
   **Programming Master** (Global A) / **self-programming** module (Global B), and it runs the UDS
   SecurityAccess unlock. It performs SPS/DPS-style operations for **its own domain**.
2. The A11 flashes **its own sub-modules itself**: `gm_update_engine → IPC → VIP MCU (RH850) →
   UDS/CAN`. Well-attested.
3. **Telematics/CGM is the cellular download conduit** (Cloud → CGM → `gmConnectionService` →
   `gm_update_engine`) + an independent direct-CAN command path — **not**, on the evidence here,
   the module flasher.
4. Cross-module reflash of *foreign* ECUs is **defined** in the CalDefs (Programming Master / RRM
   addressing the central gateway `0x45`) but **not captured** in any log here — the only reflash
   traffic documented is radio-domain modules via the VIP.

> **Correction to an earlier hypothesis:** cross-module reflash is *not* shown to be "handed off
> to the Bosch CGM," and CAN gateway `0x45` is *not* established to be the CGM. Every file that
> names the programmer names the **radio's VIP MCU**; telematics/CGM appears only as transport +
> an independent command path. Keep "CGM executes reflash" as an unverified hypothesis pending a
> live multi-module OTA capture.

## What GM actually pushes — the Y181 package

The last major release, **Y181** (`W231E-Y181.3.2-SIHM22B-499.3`, USB full package `86334732`),
is an 18-part bundle — **all parts are CSM/radio-domain**, none are foreign vehicle ECUs
(from the archived `delivery_manifest.csv`; cross-ref [`firmware_versions.md`](firmware_versions.md)):

| Module ID | Part # | Image | Sign |
|---:|---|---|---|
| 1 | 86331656 | VIP_APP (RH850 app fw) | **TSS** |
| 21 | 85098662 | SOC_HOSTOS (GHS INTEGRITY) | **TSS** |
| 22 | 86331654 | SOC_SYSTEM (Android /system) | **TSS** |
| 23 | 86331652 | SOC_BOOT | NONE |
| 24 | 86331623 | SOC_UTILS | NONE |
| 26 | 86331650 | SOC_VENDOR (/vendor) | **TSS** |
| 28 | 85843750 | SXM | NONE |
| 29 | 85121980 | GPS | NONE |
| 51 | 85155539 | TUNER | NONE |
| 52 | 85759612 | ETH_SWITCH (BCM89551 cfg) | NONE |
| 55 | 86331630 | SOC_ACPIO | NONE |
| 56 | 86331644 | SOC_VBMETA (AVB) | NONE |
| 57 | 86331636 | SOC_PRODUCT (/product) | NONE |
| 71 | 85056831 | VIP_BOOT | NONE |
| 72 | 85738845 | SOC_ABL (Intel bootloader) | NONE |

Every row: `Release Type = DEV_REL`, **`Bypass P/N & Module ID Check = TRUE`**, `CVN = EMPTY`,
`Fill/Pad = 0xFF`, signing issuer `CN=GPD, OU=GMNA GPD PRODUCTION, O=GENERAL MOTORS LLC`.
`Vit2File.vit` = ordered USB flash descriptor; `gm_usb_ignore_battery` skips the battery check.
**Y181 vs Y177:** the whole SoC/Android side + VIP_APP were re-spun (VIP_APP rev CM→CN); HostOS,
VIP_BOOT, ABL, tuner/GPS/SXM/eth-switch are byte-identical part numbers.

So "OTA that includes calibration of other modules" here = **the radio's own multi-processor
stack** (Intel SoC + Android partitions + Renesas VIP + tuner/GPS/SXM/eth-switch) — a whole-ECU
bundle the radio installs into itself. Genuinely foreign-ECU calibrations ship as separate GM
packages, not in this bundle.

## The programming machinery on the radio

```
GM Cloud (vtmpub.oboservices.mobi)                     ── or ──   USB / DPS-TIS2WEB
        │ HTTPS/OMA-DM                                                │
   Telematics (CGM/EOCM)  ── cellular download conduit ──┐            │
        │ internal Ethernet                              ▼            ▼
   gmConnectionService → Binder IPC →      gm_update_engine  (root, block-device write)
                                                 │  exec()
                                          Red Bend UA (rb_ua)  → Android/GHS partition writes
                                                 │  UDS over IPC
                                          VIP MCU (RH850)  → UDS ($10/$27/$34/$36/$37/$31/$11)
                                                 │            over CAN / IPC
                                          radio sub-modules (VIP_APP/BOOT, HostOS, ABL, TUNER,
                                                             ETH_SWITCH, GPS, SXM)
```

- **SecureUnlock** = UDS SecurityAccess ($27); the CSM program log
  ([`../diagnostics/dps/A11_CSM.ProgramLog.Txt`](../diagnostics/dps/A11_CSM.ProgramLog.Txt))
  drives it, the **VIP enforces** it (PROTOKEY / MEC / SBAT on the VIP); GM backend supplies the key.
- The Android update stack (`gm_update_engine`, `rb_ua`, `libpal_swupdate_ecu.so`, `IECUUpdate`
  HAL, the GHS `OTA_InitialTask` + `/dev/ghs/ota-isys`) all live **on the radio**.
- Radio's CAN reach is **only via the VIP**; the CGM/telematics has **direct** CAN.

## CalDef evidence for the orchestration role

From [`../reference/GIS-646_CalDef_Database_Info3.7_and_Info3.8_V7.0.8_19April2023/caldefs/`](../reference/):

- **GIS-658 `InfotainmentProgMaster_GlobalA`** — infotainment as **"Programming Master"** over
  GMLAN: `DEREGISTER_DURATION` ("Master waits for other Networked Devices"), `WAITING_ON_GMLAN`,
  `WAITING_ON_CLIENT` ("client reset to go to boot mode"), `NO_SWITCH_PROG_MODE`,
  `PROGRAMMING_ENABLED`, signing cert. Other ECUs are "clients" it enables into programming mode
  and feeds files. [C]
- **GIS-763 `InfotainmentProg_GlobalB`** — "Infotainment self programming." Holds
  **`GIS763_Gateway` = 69 (0x45)** = "Diagnostic Address of the CGM"; SecurityAccess timers
  (`WAITING_FOR_SECURE_ACCESS`, `WAITING_ON_SESSION_KEYS`, `WAITING_FOR_SEED`),
  `WAITING_FOR_PROGRAMMING_SUPPORT`, `WAITING_FOR_ECUS_TO_WAKE`. Historical pared-down
  `Immobilizer1/2_Address` cals show per-ECU targeting existed. The infotainment addresses the
  **gateway** and does the seed/key unlock. [C]
- **GIS-887 `RemoteProgrammingHMI_GlobalB`** (OTA GB **Phase 2**) — introduces the **RRM (Remote
  Reflash Master)** + infotainment state **`RemoteReflashProgramming`**; infotainment (UIM)
  monitors the **RRM's FSA heartbeat** and is the **HMI/consent/scheduling/status** surface, with
  `DU_Progress = RunningInternal|RunningExternal` (flashing the infotainment itself vs external
  modules). Heavy lifting moves to an RRM/FSA actor; infotainment demoted to HMI. [C]
- **GIS-797 / GIS-787** — OTA update-check cadence + reflash-completion display timer (HMI only).
  `GIS768_Remote_Reflash_Feature = TRUE` + `IgnoreCurrentPartNumberCheck = TRUE` are the enabling
  flags. [C]

**Reading:** the orchestrator moves **infotainment Programming Master (Global A) → infotainment
self-programming addressing gateway 0x45 (Global B Phase 1) → RRM/FSA with infotainment as HMI
(Global B Phase 2)**. The FSA `ProgrammingMaster` service on the radio (`.100:9011`) and
`RemoteReflash`/`RemoteReflashUI` on other nodes match the Phase-2 RRM model.

## Verification plan

Capture **CAN + VIP↔SoC HDLC IPC + FSA** simultaneously during a real multi-module OTA:
- Foreign-module `$34/$36/$37` transfers originating from the radio (via VIP → CAN → gateway
  `0x45`) ⇒ radio/VIP is the agent for foreign ECUs too.
- Transfers dispatched over FSA to a CGM/RRM that executes them on its direct CAN ⇒ radio is
  coordinator/HMI only and hands execution off.

Current evidence supports **radio-VIP for radio-domain modules**; **foreign-module execution is
unproven** (defined in CalDefs, not captured). Highest-value capture for closing the OTA question.
