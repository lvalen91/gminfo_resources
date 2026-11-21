# OTA & Module Programming Roles

Scope: which component of the A11 (gminfo37) programs which module (ProgrammingMaster / CGM / VIP); the DPS module-ID, signing and package inventory with measured sizes; CalDef evidence for the orchestration role; the SXM CAN-write attempt; evidence status.
Not here: the on-radio OTA engine ([`ota_update_stack.md`](ota_update_stack.md)), Global B external write-up ([`external_references.md`](external_references.md)), security verdicts ([`security.md`](security.md)).

Evidence tags: **[V]** verified on this unit (live RE, port scan, on-radio file read, bench CAN test) · **[C]** CalDef static evidence (GIS-646 database) · **[P]** live-confirmed correction · **[U]** analysis verdict, not exhaustively verified · **[X]** external / other vehicle, not confirmed on this unit.

Related: [`ota_update_stack.md`](ota_update_stack.md) · [`firmware_versions.md`](firmware_versions.md) · [`fsa_protocol.md`](fsa_protocol.md) · [`vehicle_network.md`](vehicle_network.md) · [`vehicle_config.md`](vehicle_config.md) · [`ethernet_networking.md`](ethernet_networking.md) · [`security.md`](security.md) · [`external_references.md`](external_references.md) · [`can_bench_experiments.md`](can_bench_experiments.md)

Sources: [`../research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`](../research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md),
[`../research/eeprom-calibration/VIP_CONTROL_ANALYSIS.txt`](../research/eeprom-calibration/VIP_CONTROL_ANALYSIS.txt),
[`../research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt`](../research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt),
[`../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md`](../research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md); the
GIS-646 CalDef database ([`../reference/`](../reference/)); the DPS logs
([`../evidence/dps-logs/`](../evidence/dps-logs/)); the archived Y181 update package.

## Answer (reconciled)

Question: GM OTA pushed to the radio can include calibration of other modules — does a component of the A11 perform SPS/DPS-style programming itself, or hand off to something that can?

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

**CAN gateway `0x45` = the CGM (Central Gateway Module)** — GIS763 CalDef records
`GIS763_Gateway = 69 (0x45)` = "Diagnostic Address of the CGM" ([C], see
[CalDef evidence](#caldef-evidence-for-the-orchestration-role)), and the DPS scan confirms `0x45`
as the diagnostic gateway. What is **not** established is that this CGM (as opposed to the
radio's VIP MCU) *executes* foreign-ECU reflash: every file that names the programmer names the
**radio's VIP MCU**; telematics/CGM appears only as transport + an independent command path. Keep
"CGM executes reflash" as an unverified hypothesis pending a live multi-module OTA capture. The
separate open question of whether the CAN node `0x45` is the same physical module as the
Ethernet-side telematics (`.107/.112`) / inter-VLAN router (`.102`) is tracked in
[`vehicle_network.md`](vehicle_network.md) (Join points, open item #3); see
[Open conflicts](#open-conflicts) for how the earlier "0x45 not established" wording was resolved.

History: earlier hypothesis "cross-module reflash is handed off to the Bosch CGM" was corrected —
the CGM is `0x45`, but its role as executor is unproven.

### Programming machinery (summary)

Two parallel inputs (GM Cloud, and USB / DPS-TIS2WEB) both feed `gm_update_engine`; only the
cloud leg passes through telematics. Original diagram, restored verbatim from the pre-reorg document:

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

The AAOS-side update state machine and components are in
[`ota_update_stack.md`](ota_update_stack.md) (that doc does not carry this diagram).

- **SecureUnlock** = UDS SecurityAccess (`$27`); the CSM program log
  ([`../evidence/dps-logs/A11_CSM.ProgramLog.Txt`](../evidence/dps-logs/A11_CSM.ProgramLog.Txt))
  drives it, the **VIP enforces** it (PROTOKEY / MEC / SBAT on the VIP); GM backend supplies the key.
- The Android update stack (`gm_update_engine`, `rb_ua`, `libpal_swupdate_ecu.so`, `IECUUpdate`
  HAL, the GHS `OTA_InitialTask` + `/dev/ghs/ota-isys`) all live **on the radio**.
- Radio's CAN reach is **only via the VIP**; the CGM/telematics has **direct** CAN.

## DPS: authentication, services, module IDs and signing

DPS (Data Protection Service):

- Uses **AES-CMAC** for authentication.
- **Server-based key provisioning** — keys are not stored locally in plaintext.
- **Cannot write EEPROM directly** — EEPROM writes go through the VIP MCU's I2C interface.
- **Calibration / diagnostic authentication are separate mechanisms:** stock calibration containers use RSA-2048/SHA-256 signatures; DPS SecurityAccess has a backend-assisted CMAC path. Reusable server-key provisioning is unproven (corrected 2026-11-15). See [seed/key and calibration signature reference](../research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- Handles license verification and calibration integrity.

UDS service table and the CalDef/VIP-calibration tables (security calibrations such as
`GIS763_PROGRAMMING_ENABLED`, `GIS763_SigningCertificateIssuer`, the 31 VIP `cal_` values) live in
[`vehicle_config.md`](vehicle_config.md). Two separate calibration systems exist: CalDef
(Android/SoC, part of the OTA-updated system image) and VIP calibrations (RH850 firmware, updated
independently of Android OTA).

### Package inventory — the Y181 package

The last major release, **Y181** (`W231E-Y181.3.2-SIHM22B-499.3`, USB full package `86334732`),
is a **15-part** bundle (15 rows in the archived `delivery_manifest.csv`;
`UPDATE_PROCESS_ANALYSIS.txt:237` of the retired original, folded into `research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` and `ota_update_stack.md`) — **all parts are CSM/radio-domain**, none are foreign
vehicle ECUs. History: corrected 2026-11-12 from "18-part"; 18 is the radio's *installed-module*
inventory ([below](#installed-module-inventory-on-radio-18-modules)). Cross-ref
[`firmware_versions.md`](firmware_versions.md).

Module IDs are decimal here; the hex form (used in the size table and on the wire) is derived
(56=0x38, 55=0x37, 51=0x33, 28=0x1C, 29=0x1D, 52=0x34, etc.).

| Module ID (dec / hex) | Part # | Image | Sign |
|---|---|---|---|
| 1 / 01 | 86331656 | VIP_APP (RH850 app fw) | **TSS** |
| 21 / 15 | 85098662 | SOC_HOSTOS (GHS INTEGRITY) | **TSS** |
| 22 / 16 | 86331654 | SOC_SYSTEM (Android /system) | **TSS** |
| 23 / 17 | 86331652 | SOC_BOOT | NONE |
| 24 / 18 | 86331623 | SOC_UTILS | NONE |
| 26 / 1A | 86331650 | SOC_VENDOR (/vendor) | **TSS** |
| 28 / 1C | 85843750 | SXM | NONE |
| 29 / 1D | 85121980 | GPS | NONE |
| 51 / 33 | 85155539 | TUNER | NONE |
| 52 / 34 | 85759612 | ETH_SWITCH (switch cfg; Marvell 88Q5050 on this unit — see below) | NONE |
| 55 / 37 | 86331630 | SOC_ACPIO | NONE |
| 56 / 38 | 86331644 | SOC_VBMETA (AVB) | NONE |
| 57 / 39 | 86331636 | SOC_PRODUCT (/product) | NONE |
| 71 / 47 | 85056831 | VIP_BOOT | NONE |
| 72 / 48 | 85738845 | SOC_ABL (Intel bootloader) | NONE |

Signing summary (same data as the table, from `firmware_versions.md` DPS module list):
- **TSS-signed:** 1 VIP_APP, 21 SOC_HOSTOS, 22 SOC_SYSTEM, 26 SOC_VENDOR.
- **Unsigned:** 23 SOC_BOOT, 24 SOC_UTILS, 28 SXM, 29 GPS, 51 TUNER, 52 ETH_SWITCH, 55 SOC_ACPIO, 56 SOC_VBMETA, 57 SOC_PRODUCT, 71 VIP_BOOT, 72 SOC_ABL.

Package flags (every row): `Release Type = DEV_REL`, **`Bypass P/N & Module ID Check = TRUE`**,
`CVN = EMPTY`, `Fill/Pad = 0xFF`, signing issuer
`CN=GPD, OU=GMNA GPD PRODUCTION, O=GENERAL MOTORS LLC`. `Vit2File.vit` = ordered USB flash
descriptor; `gm_usb_ignore_battery` skips the battery check.

**Y181 vs Y177:** the whole SoC/Android side + VIP_APP were re-spun (VIP_APP rev CM→CN); HostOS,
VIP_BOOT, ABL, tuner/GPS/SXM/eth-switch are byte-identical part numbers.

**Conclusion:** "OTA that includes calibration of other modules" here = **the radio's own
multi-processor stack** (Intel SoC + Android partitions + Renesas VIP + tuner/GPS/SXM/eth-switch) —
a whole-ECU bundle the radio installs into itself. Foreign-ECU calibrations ship as
separate GM packages, not in this bundle.

### Installed-module inventory on radio (18 modules)

Source: live Y181B radio, `update_cache/update/moduleinfo` pulled from `/cache` (timestamp field
written 2026-11-12 13:10 AKST), directly read [V]. Corrected 2026-11-12.

- **Module 52** reports `MVL88Q5050_globalB_234702AB_02_09_1003` (part 85759612, DLS AA) =
  **Marvell 88Q5050**, not BCM89551. The switch IC is board-variant (BCM89551 on MY22/DV boards,
  88Q5050 on MY23+; see [`ethernet_networking.md`](ethernet_networking.md)); the part number is
  the same, so the former "BCM89551 cfg" label was a teardown-unit assumption. Module identity is
  the updater's report, not a chip read; live `init.svc.ethmvlctrlmgr=running` /
  `ethctrlmgr=stopped` (adb) agrees (inferred).
- **Not in the 15-row package table:** 53 `SOC_ANDROID_ODM` (part 0, DLS AA), 54
  `SOC_ANDROID_ACPI` (part 0, AA), 81 `FIDM` (84961617, AA, version `6`). Whether these ship as
  separate package parts or ride inside others is **not established**; names/signing tiers for
  them are not established by any package data.
- **Naming:** the radio calls module 72 (85738845, DLS AB, version `2344`) `SOC_BOOT` and module
  23 (86331652) `SOC_ANDROID_BOOT`; module 24 is `SOC_ANDROID_BOOTLOADER_UTILS`. The package-table
  labels `SOC_BOOT` (23) / `SOC_ABL` (72) / `SOC_UTILS` (24) are the package-side names.
- **Modules 28/29/51** are listed in the package table with the USB package's part numbers
  (85843750 / 85121980 / 85155539). The radio currently reports `TUNER_XM` 86404694 (DLS AC), `GPS`
  part 0, `TUNER_DIGITAL` part 0 (DLS AA each). The installed set differs from this package for
  those three; unreconciled (see [Open conflicts](#open-conflicts)).
- **Installed versions:** VIP_BOOT (71) 85056831 DLS AA `B2.9C.01.01` (build 23Jul28-1212, image
  `bolo`); VIP_APP (1) 86331656 DLS CN `2B.B5.01.01` (build 25Jun19-2209); SOC_HOSTOS (21)
  85098662 DLS BM `INTEGRITY IoT 2020.18.19 MY22-026`.

### Measured package component sizes (2026-11-17)

Read-only file-size checks of the local Y175 and Y181B `USB_Files` packages (module ID in hex):

| Component / module ID (hex) | Y175 part / file bytes | Y181B part / file bytes |
|---|---|---|
| SOC_VBMETA / 38 | 85759606 / 1,688 | 86331644 / 1,693 |
| SOC_ACPIO / 37 | 85759610 / 2,852 | 86331630 / 2,850 |
| TUNER / 33 | 85155539 / 673,191 | 85155539 / 673,191 |
| SXM / 1C | 84999468 / 824,608 | 86404694 / 2,237,910 |
| GPS / 1D | 85121980 / 936,516 | 85121980 / 936,516 |
| ETH_SWITCH / 34 | 85759612 / 1,497,632 | 85759612 / 1,497,632 |

These are packaged file sizes, not decoded payload sizes, flash allocations, or established CAN
transfer lengths. SXM is modest relative to Android images, but distinct from the roughly 1.5 KB
slot 0C feature-calibration container. Small size does not establish suitability for an isolated
write: VBMeta belongs to verified boot, and the update route for peripheral firmware must be
traced. No firmware-component write was attempted by this size check. CAN calibration acceptance
does not establish that module 1C uses the same programming path.

## SXM stock-file CAN attempt — 2026-11-17

**Result: no SXM firmware write.** A direct-CAN attempt against the current VIP application
reached RequestDownload but was rejected on the first TransferData block. This establishes
rejection on the tested application-mode calibration route, not impossibility through a different
bootloader or internal update route.

Fresh F182 identified SXM module 1C as part 84999468/DLSAC; all 14 LTZ calibration identities
matched the pinned stock set and baseline PEC was 0000. The matching Y175 USB file is 824608
bytes, SHA-256 `d9d30c1de45fae2beb66418c9bef74788770171d69357d40f4d3cf1f5873c094`. The file
starts with zero bytes rather than a 0301 calibration header. Moria found no recognized structure
or extractable payload; its entropy observation alone does not establish encryption.

The test retained the 32-frame CAN harness at 500 kbit/s, used tester F1, extended session and
granted security profile 01, then received positive FF01, 021E, 8502, 280301 and 1002 responses.
No verifier-marker RAM writes were made.

| Test | RequestDownload | First 1022 file bytes in 36 01 | Immediate F0F1 |
|---|---|---|---|
| Exact unmodified SXM OTA file; declared 824608 bytes | `34 00 44 00000000 000C9520` → `74 20 0F FF` | `7F 36 72` | `000A` |
| Separate target-gate probe: 1457-byte stock slot 0C container with only header module ID changed 000C→001C | `34 00 44 00000000 000005B1` → `74 20 0F FF` | `7F 36 72` | `000F` |

The second input was a diagnostic gate probe, **not an SXM firmware container**. Neither test sent
further blocks or TransferExit after rejection. A positive 34 response therefore did not establish
acceptance of the file type or target.

Static correlation in VIP_APP 85759599 (RH850, Ghidra image base 0; SHA-256
`d729fa4b59095b03b05ee26e09e3eb31dda36678055f77be11f24416dd1ad239`): file 56D2C requires the 0301
header and sets PEC 000A otherwise. File 56CCA accepts only module IDs 02–0F and sets PEC 000F
otherwise. These gates are called by 56D50 before signature validation; first-block handler 4F174
returns NRC 72 when that parser fails, before its payload-processing call 8615C. File offsets are
not runtime addresses (runtime = file + 27A7A for this image).

Cleanup rewrote the unchanged, pinned stock slot 0C: `76 01`, `76 02`, `77`. F182 remained
byte-identical. An immediate post-restart status read timed out; settled reads then confirmed all
14 F0F0 statuses 00 and F0F1/F0F2 both 0000. Immediate cleanup returned `7F 10 22`, `7F 28 7F`,
`7F 85 7F`; later 1003 and 8501 succeeded, 280001 returned `7F 28 22`, and 1001 succeeded. Do not
describe communication re-enable as positively acknowledged. Full harness replay remains active. No
power cycle or SXM audio-function test was performed in this attempt.

Separate mounted-image evidence: Y175 `libpal_swupdate_sxm.so`, SHA-256
`c4a0d8568154ac2f4b2471fb68e213b330d1fe63231f75143ed4961eca8facbf`, is x86-64 ELF. Export
`swu_update_sxm` at virtual address E4C30 consists of `mov eax,0xB; ret`; it performs no write
through that export. The meaning of return code 0B and any alternate SXM update implementation
remain unresolved. This is static image evidence, not a live call of that export.

**Full-USB follow-up:** the normal Y175 package later completed successfully with CAN-supplied RUN
and the USB battery-ignore marker. Android changed slot B→A; stored update status 1/99%/error 0
and clean CAN calibration status were verified after the final mute-hold restart. The recovery
script scheduled SXM 28/84999468, but the per-module log was not readable; rewriting versus
same-version skipping is unresolved. This is not a T1/CAN-only or SXM-only write. See the owning
full-update observation in [`ota_update_stack.md`](ota_update_stack.md) (Y175 full USB update
bench observation, 2026-11-17).

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

**[P] (2026-09):** live RE + a live port scan confirm the FSA `ProgrammingMaster` catalog entry
(`.100:9011`, serviceId 1006) is dead code on this build — never instantiated, port 9011 never
bound (only 9002/9010/9016 LISTEN). This reinforces the Phase-2 reading: Global B demoted
infotainment from Programming Master to an RRM/FSA HMI role, to the point the old Programming
Master service class ships unused. Detail (single copy): [`fsa_protocol.md`](fsa_protocol.md).
`RemoteReflash` is FSA `9012` (Android as client dialing `.102`, telematics).

**[U] OTA reflash-trigger verdicts (2026-09)** — network→install path analysis, the
`UpdateServiceImplGB.install()` missing permission check, `InstallRunner` trace, the
`DevCaloverrideInstaller` (containerType 2) signature-skip and `USBNotifier` check, and the
hardware-enforced GHS rollback counter — are not reproduced here. Net result relevant to the
roles question: no confirmed unauthenticated-Ethernet-peer path to triggering a reflash on this
build. See [`security.md`](security.md) and [`ota_update_stack.md`](ota_update_stack.md); research:
[`../research/mdi2-bench-sessions/AE_RESEARCH_HANDOFF.md`](../research/mdi2-bench-sessions/AE_RESEARCH_HANDOFF.md#where-the-facts-live-now-pointers-only),
[`../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).

## GM dealer service programming (SPS2) — official procedure

Short form (may be owned by `../diagnostics`; see ledger). From GM service data (ALLDATA *Control
Module References → Programming and Setup*):

- **A11 Radio — USB-mediated SPS, not a straight bus push.** SPS2 generates the payload, then it
  is **copied to a USB stick** ("USB File Transfer") and installed by the infotainment itself:
  requires an **EL-52100 MDI 2** (the older EL-47955 MDI **fails**), USB **FAT32 ≥16 GB** (USB
  3.x recommended), vehicle OFF/PARK/door-closed, stable voltage via a *maintainer*. Flow: SPS →
  *A11 Radio – Programming* → USB copy → move to vehicle → ignition/infotainment ON → on-screen
  "Update" → Clear DTCs → **reset the Manufacturer Enable Counter (MEC) via GDS2** → ignition OFF,
  RAP off, fob removed, 5-min wait. (Check *Settings → Updates* for a pending OTA first.)
  Failed-programming recovery = de-power the module ≥10 min (fuse/connector/battery) then retry.
- **T3 Audio Amplifier — standard SPS**, no USB, no MEC: ignition OFF → SPS *T3 – Programming* →
  Clear DTCs.
- **MDI 2 relevance:** the same dealer tool family the repo's `tools/mdi2_client/` speaks to — the
  USB-SPS/MEC detail explains why the radio's reflash path differs from a plain UDS `$34/$36` push
  and why MEC state matters after programming.

This dealer path is orthogonal to the GHS/`gm_update_engine` OTA machinery
([`ota_update_stack.md`](ota_update_stack.md)).

## Global B provisioning & SPS/DPS economics [X]

External write-up (Snipesy / Surreal Development, *The ABCs of Global B*, 2026-06-16, CC0 1.0) —
Global B lineage, circle of accountability / SDAC / DTC U1962, `$27` against the gateway vs
per-ECU, SPS3 pricing and bypass, cloud-auth composition — is summarized with caveats in
[`external_references.md`](external_references.md). Points that bear on this doc:

- The author's `$27`-always-against-the-central-gateway model is Cadillac-specific / unconfirmed
  here: on this platform the DPS captures show `$27` as a **per-ECU** exchange (seed/key direct to
  ECU `0x80` radio and `0x45` gateway — `LIVE_DPS_CAPTURE_ECU80_AUG2026.md`).
- Do not adopt the author's SDGM = SGM = CGM equation: "SGM" in this repo = Shanghai-GM (SAIC-GM
  regional key backend, `tisvcsv4.dll`), a false-friend collision. CGM = CAN `0x45` per CalDef
  (above).
- The author's "telematics module performs the actual OTA download, radio only kicks off the
  campaign" aligns with the Cloud → CGM → `gmConnectionService` → `gm_update_engine` chain above.

## Verification plan

Capture **CAN + VIP↔SoC HDLC IPC + FSA** simultaneously during a real multi-module OTA:
- Foreign-module `$34/$36/$37` transfers originating from the radio (via VIP → CAN → gateway
  `0x45`) ⇒ radio/VIP is the agent for foreign ECUs too.
- Transfers dispatched over FSA to a CGM/RRM that executes them on its direct CAN ⇒ radio is
  coordinator/HMI only and hands execution off.

Current evidence supports **radio-VIP for radio-domain modules**; **foreign-module execution is
unproven** (defined in CalDefs, not captured). Highest-value capture for closing the OTA question.

## Open conflicts

1. **CAN `0x45` = CGM? — resolved, residual open.** Source `ota_programming_roles.md` L31-36 and L211 assert `0x45` **is** the CGM (GIS763 "Diagnostic Address of the CGM"); L304-306 said CAN `0x45` as CGM was "not established" per `vehicle_network.md` Join-points #3. The later text of `vehicle_network.md` (Join points note, L273-279) and `security.md` L893 both state `0x45` **is** the CGM per GIS-763 and narrow open item #3 to whether this CAN node is the same *physical* module as the Ethernet-side telematics (`.107/.112`) / inter-VLAN router (`.102`). This doc adopts that: CAN `0x45` = CGM [C]; same-physical-node-as-Ethernet-faces = open; "CGM executes foreign reflash" = unverified. The L304-306 wording is dropped as stale.
2. **SXM part number across package/installed.** Package table module 28 SXM = 85843750 (source L53, `firmware_versions.md` DPS list); Y175 package SXM = 84999468 / 824,608 B and Y181B package SXM = 86404694 / 2,237,910 B (size table, source L132); the live radio reports `TUNER_XM` 86404694 (DLS AC). 85843750 matches neither the Y175 nor Y181B measured package. Unreconciled.
3. **Module 28/29/51 installed vs package.** Radio reports `GPS` part 0 and `TUNER_DIGITAL` part 0, vs package GPS 85121980 / TUNER 85155539 (source L156-158). Unreconciled.
4. **Module naming.** Package-side `SOC_BOOT` = module 23 (86331652), radio-side `SOC_BOOT` = module 72 (85738845); radio calls 23 `SOC_ANDROID_BOOT`. Name collision, not a data conflict; use module IDs.
5. **Whether modules 53/54/81 ship as package parts** — not established (source L152).
