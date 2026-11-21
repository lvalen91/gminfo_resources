# gminfo_resources

Canonical reference for the **GM Info 3.7** (`gminfo37`) infotainment system — 2024 Chevrolet/GMC ICE vehicles (Silverado, etc.).

**Hardware:** Harman/Samsung · Intel Atom x7-A3960 (Apollo Lake) · Android 12 AAOS · GHS INTEGRITY IoT hypervisor  
**Research builds:** Y175 (Jun 2024) · Y177 (Mar 2025) · Y181 (Jul 2025, baseline)

The consolidated Y181B investigation is maintained in
[research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).
Use [the research index](research/README.md) to find topic owners.

---

## Directory Layout

```
gminfo_resources/
├── platform/          Platform reference (index: platform/README.md): hardware, boot/partitions/recovery, networks and protocols, CAN, OTA, security, vehicle config, emulator
├── hardware/          Physical teardown, BOM, photos, EEPROM/IFWI analysis
├── eeprom/            EEPROM mod guide, analysis reports, undocumented flags, .bin dumps
│   ├── bins/          EEPROM binary dumps (Y181 ADB-enabled: HC + LTZ)
│   └── config_tool/   eeprom_editor.py + firmware_re/ (115 decompiled VIP_APP functions)
├── evidence/enumeration/       ADB + fastboot enumeration by firmware build
│   ├── scripts/       gm_aaos_enum.sh, quick_security_check.sh
│   ├── Y175/          Jan 2026 enum, VIP UART log, SELinux policy
│   └── Y181/          Dec 2025 enum + Apr 2026 (apr2026/) + Jun 2026 (jun2026/), fastboot enums
├── diagnostics/       DPS session logs, CAN bus traces, Ethernet UDS (diagnosticsd :49156)
│   └── dps/           A11 Radio (ECU 0x80) DPS 4.56 logs
├── research/          Deep-dive analysis docs, decompiled artifacts, scripts, reports
│   ├── README.md (topic index), INVENTORY.md, research topic docs + Y177/Y181 VIP/GHS analyses
│   ├── security/      Security-specific CVE and threat analyses
│   ├── fuzz/          VMM1/OTA parser fuzz bundles and synthesis outputs
│   ├── type4_radio_info/  Type-4 radio SPAT/calibration build kit
│   ├── canbus_reset/  CAN bus reset investigation (analysis + CFX config XML)
│   ├── decompiled/    Ghidra/radare2 string dumps and decompiled C (VMM, ELK, SA015, IVCS)
│   ├── scripts/       Analysis scripts (avb_audit.py, crypto_scan.py, ghs_dump.py, etc.)
│   ├── reports/       Automation output (crypto_findings.json, avb_audit.out, forensics)
│   ├── session_logs/  Dated research/security session notes
│   └── tools/         ghs_probe app source, DPS archive tool bridge docs
├── reference/         GM official CalDef GIS-646 database (215 .caldef/.enumdef, schema)
├── audio/             Audio subsystem, HAL, codecs, effects, CarPlay pipeline, AVB
├── video/             Video pipeline, CINEMO/NME, H.264, display, HWC, codecs
├── codecs/            Full media codec manifest
├── projection/        CarPlay vs Android Auto, cluster nav, CPC200 integration
├── runtime/           Boot timing, memory pressure, known issues
├── analysis/          Debloat comparison, third-party API access, platform FAQ
└── tools/mdi2_client/       Native macOS MDI2 diagnostic client (Python tooling, separate project)
```

---

## Quick Reference

The [bench hardware setup baseline](hardware/bench_setup.md) owns the current
OPU harness, T1/VLAN and dual-ADB access, RH850 RX-only UART, CAN listen-only
configuration, and macOS privilege requirements.

The [CAN message reference](platform/can_network.md) catalogs all 72 captured IDs
and separates bench observations from public in-vehicle signal definitions.

### Platform Identity

| Field | Value |
|-------|-------|
| Module name | `gminfo37` (GM Info 3.7) |
| ECU address | `0x80` (A11 Radio) |
| Manufacturer | Harman/Samsung |
| CPU | Intel Atom x7-A3960, 4-core, 0.8–2.4 GHz, 14nm Goldmont |
| RAM | 8 GiB LPDDR4 physical; static GHS guest grant 7830 MiB (+34 MiB RO IPU window); historical Android `MemTotal` near 5530 MiB. Y181B recovery E820 usable **5743.55859375 MiB**, measured 2026-11-12; grant-to-visible cause unresolved. [Map and limits](research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory) |
| Storage | 64 GB Samsung eMMC (KLMCG4JEUD, BGA-153) |
| Display | Chimei Innolux DD134IA-01B, 2400×960 @ 60 Hz, density 200 |
| GPU | Intel HD Graphics 505 (Gen9, 18 EUs), Mesa 21.1.5, GLES 3.2 |
| Audio HAL | HarmanHAL `android.hardware.audio@5.0` ("Titan" = SoC platform codename, not the HAL); 8 CarAudioService output buses; AVB transport |
| OS | Android 12 (API 32) AAOS, guest VM under GHS INTEGRITY IoT 2020.18.19 |
| VIP MCU | Renesas RH850/F1K (R7F7015873AFP, marking 15873; TM52176 is a trace code) |
| EEPROM | ST M24C64, 8 KB, I2C (SBI security flags) |
| Kernel | Linux 4.19.283 (Y175) / 4.19.305 (Y177, Y181) |
| CAN | GM VIP/SDV1 (GB), CAN 2.0 29-bit · ECU 0x80 · Req 0x14DA80**F2** / Rsp 0x145AF2**80** in the captured DPS session (F1 = generic OBD tester address) |

### Firmware Builds

| Build | Kernel | SELinux | VIP Security Fn | Bootloader |
|-------|--------|---------|-----------------|------------|
| Y175 `W213E-Y175.5.2-SIHM22B-383.1` | 4.19.283 | Enforcing | Full (~906B) @0xb6708 | 2121-1 |
| Y177 `W231E-Y177.6.1-SIHM22B-499.2` | 4.19.305 | Enforcing | Full (~906B) @0xb67d4 | — |
| Y181 `W231E-Y181.3.2-SIHM22B-499.3` | 4.19.305 | Enforcing | Full (~906B) @0xb67d0 | 2344 |

All three stock builds boot SELinux **Enforcing** and carry the **full ~906-byte** VIP security-validation function — the earlier "Y177 = permissive SELinux + 4-byte VIP stub" claim is refuted (three-way byte-level VIP_APP diff; `system/bin/init` is byte-identical across builds and forces Enforcing, so any live permissive Y177 was a modified/eng unit). The VIP function gates ADB/seed auth only, not SELinux or AVB. Y181→Y177 downgrade is blocked by GHS/AVB anti-rollback (the AB0 rollback counter in `misc`/vda9) — owner-verified 2026-08-17 bench re-test.

### EEPROM ADB research

The programmer workflow and supported edit scope are maintained in
[the EEPROM guide](eeprom/README.md). Certificate authentication, root gates,
historical MEC readings and unresolved registration behavior are maintained in
[the consolidated MEC section](research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).


---

## Key Documents

| Document | What it covers |
|----------|----------------|
| [`hardware/teardown.md`](hardware/teardown.md) | Full BOM, PCB layout, security architecture, GHS analysis, research vectors, catch-22s |
| [`hardware/connectors.md`](hardware/connectors.md) | Rear-panel connector map + **authoritative IOK connector pinouts** (ALLDATA + GM Body Builder Manual, this VIN): FAKRA/coax farm, Stac64 power/CAN/Ethernet, FPD-Link display (**A22 center-stack HMI**), USB (one USB 2.0 lane, 3-receptacle daisy chain, HSAL2 pinout, ADB role-switch), Bose-amp AVB trace (Ethernet Bus 6), RPO build manifest, X1–X11 cross-ref |
| [`platform/vehicle_network.md`](platform/vehicle_network.md) | Vehicle-wide two-plane network: 24-ECU CAN census (gateway 0x45, radio 0x80) from the DPS log + Ethernet vlan4/5 IP/partition map + FSA/SOME-IP; flags where sources disagree |
| [`platform/ota_programming_roles.md`](platform/ota_programming_roles.md) | Who reflashes what: radio = ProgrammingMaster/HMI + flashes own domain via VIP UDS/CAN; telematics/CGM = download conduit; Y181 package inventory; CalDef GIS-658/763/887 evidence |
| [`platform/qualcomm_cadillac_platform.md`](platform/qualcomm_cadillac_platform.md) | **[X] external** — the newer Qualcomm SA8155P + QNX Cadillac radio (Lyriq/CT5): platform split vs this Intel unit, RH850/SA8155P architecture, 33″ FALD/FPD-Link IV display, board BOM, VIN boot gate. From surrealdev "Rooting the Cadillac Part 1" (unverified on our hardware) |
| [`platform/vehicle_config.md`](platform/vehicle_config.md) | Bench-radio donor vehicle (2024 Silverado 2500HD LTZ): RPO-code → GM calibration map used to set the emulator to the truck's real feature set (trailering, LTZ trim, gas, 360 cams). VIN redacted |
| [`platform/emulator.md`](platform/emulator.md) | **Y181 Silverado AAOS booted in the x86_64 Android emulator** (hybrid: GM system/product on goldfish kernel/vendor); theme-matched to the real Silverado UI; fidelity vs the actual radio. Build tree lives in the /Volumes research tree |
| [`platform/security.md`](platform/security.md) | SELinux, dm-verity, FBE, EEPROM security, CVEs, ProtoKey |
| [`platform/boot_chain.md`](platform/boot_chain.md) | 5-phase boot, GHS tasks, A/B metadata, misc partition |
| [`platform/firmware_versions.md`](platform/firmware_versions.md) | Y175/Y177/Y181 diff, DPS/CalDef |
| [`platform/ethernet_networking.md`](platform/ethernet_networking.md) | Interfaces, backbone switch, VLAN 4/5 maps, open ports, network ADB, mDNS, WiFi/BT, physical Ethernet bus map, UART/USB |
| [`platform/fsa_protocol.md`](platform/fsa_protocol.md) | GM FSA/NFSA protocol: wire format (magic `0x5AA5`), service catalog, protobuf defs, live service sessions (RemoteModuleHMI/NAM/DeviceInfo/DisplaysCoordination) |
| [`platform/ota_update_stack.md`](platform/ota_update_stack.md) | UpdateService Binder map, SWU state machine, Y181 package format/signing (TSS/GPD CA), OTA engine, USB install path |
| [`platform/README.md`](platform/README.md) | Index of every platform doc, reading order, evidence-tag legend, "where does X live" table |
| [`platform/hardware_specs.md`](platform/hardware_specs.md) | SoC/GPU/RAM/storage/display/audio/USB/thermal specs, UART console map, I2C topology, Intel A3960 datasheet facts |
| [`platform/vip_ipc_ghs.md`](platform/vip_ipc_ghs.md) | RH850 VIP MCU, VIP-SoC IPC channel map, GHS INTEGRITY hypervisor, `/dev/ghs` |
| [`platform/partitions_storage.md`](platform/partitions_storage.md) | eMMC/GPT map, `super`/dynamic partitions (measured), first-stage mounts |
| [`platform/elk_recovery.md`](platform/elk_recovery.md) | ELK/kernelflinger, recovery/fastbootd, Boot Guard/TXE forensics, native-Linux probe bring-up |
| [`platform/eeprom_i2c_security.md`](platform/eeprom_i2c_security.md) | Pointer into `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` (EEPROM memory map, security flags, I2C-bus permissions, local hardware attack surface) |
| [`platform/avb_audio_transport.md`](platform/avb_audio_transport.md) | gPTP, AVTP AAF streams on VLAN 2, usage-to-bus mapping, firmware audio stack |
| [`platform/can_bench_experiments.md`](platform/can_bench_experiments.md) | CAN bench log: calibration writes, ADB-enable and keep-alive campaign, boot/door/wake behaviour |
| [`platform/gmsystemui_app_gating.md`](platform/gmsystemui_app_gating.md) | GMSystemUI WhiteList/predicates, CarPlay vs AA asymmetry, display-calibration gate |
| [`platform/pi_swap_feasibility.md`](platform/pi_swap_feasibility.md) | Replacing the radio with a Raspberry Pi running AAOS: CAN audit, removal consequences, capture plan |
| [`platform/external_references.md`](platform/external_references.md) | Intel APL/Celadon/bootloader sources, NDA-gated list, surrealdev bibliography |
| [`diagnostics/ethernet_uds_diagnosticsd.md`](diagnostics/ethernet_uds_diagnosticsd.md) | Root `diagnosticsd` UDS-over-TCP on :49156 — GM 8-byte wire format, UDS dispatch, tester/SecurityAccess trust tiers |
| [`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](research/security/SHELL_ACCESS_ESCALATION_Jun2026.md) | uid=2000 Binder access map, kernel extraction + KASLR slide, GM Secure ADB `adbd` auth, escalation gate inventory |
| [`analysis/platform_faq.md`](analysis/platform_faq.md) | Evidence-backed FAQ (APK decompilation, logcat, ADB) |
| [`projection/cpc200_integration.md`](projection/cpc200_integration.md) | CPC200-CCPA wireless adapter integration |
| [`video/cinemo_nme_framework.md`](video/cinemo_nme_framework.md) | CINEMO/NME CarPlay framework architecture |
| [`evidence/enumeration/Y181/`](evidence/enumeration/Y181/) | Full ADB enumeration dump, SELinux policy, logcat |
| [`evidence/enumeration/Y175/Y175_VIP.log`](evidence/enumeration/Y175/Y175_VIP.log) | VIP UART boot log (IPC timing, ProtoKey, SBAT) |
| [`research/README.md`](research/README.md) | Top-level index of the full GM AAOS research corpus |
| [`eeprom/EEPROM_Analysis_Report.md`](eeprom/EEPROM_Analysis_Report.md) | Full 8 KB EEPROM map: UI flags, checksums, calibration, factory-reset triggers |
| [`eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`](eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md) | Retired (2026-11-21): pointer to `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` and `eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`; raw data in ELA §13 |
| [`research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md`](research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md) | Three-way VIP security-fn diff (Y175/Y177/Y181): full ~906B in all builds, no stub |
| [`research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`](research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) | GHS INTEGRITY hypervisor, AB0 rollback, VMM analysis |
| [`research/boot-update-recovery/GHS_FILE_MAP_85098662.md`](research/boot-update-recovery/GHS_FILE_MAP_85098662.md) | 100% edge-to-edge byte map of GHS SOC_HOSTOS `85098662` (14,929,956 B, 0 gaps): confirms GHS's USB role is mediated xHCI/xDCI passthrough only (no `dabridge`/role-switch/gadget logic), supplies the guest `OTGD` ACPI surface, and the only unread bytes are a 768 B RSA key+signature tail (no hidden/compressed code) |
| [`research/mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md`](research/mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md) | Firmware-verified breakdown of the radio's USB hardware & ADB logic: 4-wire X8 (no CC/ID to radio), software role-switch via `OTGD`/`SPPS` ACPI, dev-options USB-debugging toggle as the ADB trigger, two UDC paths (dabridge virtual `dabr_udc.0` in-vehicle / raw `dwc3.0.auto` bench), Aptiv H2H bridge `2996:0105`, software-defined gadget VID/PID |
| [`evidence/enumeration/Y181/apr2026/vulnerability_assessment.txt`](evidence/enumeration/Y181/apr2026/vulnerability_assessment.txt) | Apr 2026 CVE/threat assessment (DNSpooq, SOME/IP, SELinux) |
| [`evidence/dps-logs/`](evidence/dps-logs/) | DPS 4.56 session logs for A11 Radio (ECU 0x80): SBI/seed-key, ECU map, Y177 update |
| [`reference/GIS-646_CalDef_Database_Info3.7_and_Info3.8_V7.0.8_19April2023/`](reference/) | GM official CalDef database (215 caldef/enumdef + XSD schema) |

---

## Research Status

**Current target (2026-11-17):** native Linux hardware support and a cold-power
ELK recovery path independent of working GHS/AAOS/Probe or eMMC software.

- Upstream Linux `7.3.5-probe-stable02` is running on hardware: automatic panel
  initialization, owner-confirmed display output, USB shell, T1 root SSH,
  native eMMC readback and `/dev/mem` presence verified. Earlier Probe builds
  separately established bidirectional VIP HDLC and GPU acceleration.
- Native Probe → CSE ELK selection → reset → ELK → RAM-boot Probe works.
- Cold power → captured CAN harness → stock boot → CAN ELK request works.
  A cold entry that skips stock software remains unverified.
- Radio is verified in stable02 with T1 SSH. The minimal CAN configuration
  remains original `529` keepalive at 320.270 ms; full harness replay is stopped.
- The image includes the radio-proven GPIO-v2/panel-path fixes, upstream signed
  regulatory database, and the preserved DEVMEM / `iomem=relaxed` changes.
  Touch binding, auxiliary MMC errors, audio/camera support and Wi-Fi startup
  delay remain open; no eMMC/SPI write was needed for these RAM boots.
- Exact image hash, tests, failures, retained tools and open work are maintained
  in the [current stable02 record](research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

**Historical target:** Y181→Y177 downgrade; GHS/AVB rollback remained a separate
constraint. The earlier permissive-SELinux/stubbed-VIP motivation was refuted.
The following older research options are background, not the current task list.

**Ranked options (post-binary analysis):**

1. Return-to-dealer screen — check ADB/USB exposure during that state (easiest; already been there once)
2. EEPROM `0x0A00` — 871 VIP firmware references, completely unknown function
3. Offline eMMC modification — dump BGA-153 eMMC, find AB0 in misc, recalculate CRC32
4. ELK trigger via VIP J6_CDD diagnostic channel (ConnToOTA_BootELK / ConnToLifecycle_BootELK
   IPC → HECI → ABL) — **(2026-09-10)**
   ELK is Intel Kernelflinger **fastboot** (kernelflinger-07.02), not a Linux shell; "USB
   storage is unsupported." **Updated 2026-11-17:** RAM `download`/`boot` of
   native Linux with a shell is now demonstrated; ELK itself remains fastboot
5. 3× boot failure escalation → GHS lifecycle last resort → ELK (same fastboot caveat as #4)
6. `/dev/ghs/ota-isys` HostOS streaming (highest risk — GHS likely signature-checked)

See [`hardware/teardown.md`](hardware/teardown.md) §Ranked Research Vectors and §Key Catch-22s for full analysis.

---

## Data Sources

- ADB enumeration: Y175 (Jan 2026), Y181 (Apr 2026) — [`evidence/enumeration/`](evidence/enumeration/)
- EEPROM dumps: Y181 stock + modified — [`eeprom/`](eeprom/)
- VIP UART log: Y175 boot — [`evidence/enumeration/Y175/Y175_VIP.log`](evidence/enumeration/Y175/Y175_VIP.log)
- Hardware photos: IC close-up, board overview, XGecu programmer — [`hardware/`](hardware/)
- Binary analysis: VIP firmware 86331656 (9 Ghidra passes, RH850:LE:32), GHS HOSTOS 85098662, plmanager, gm_update_engine, ELK (kernelflinger-07.02)
- Logcat: 3.7 GB across 29 files (Feb 2026)
- Partition images: Y177 + Y181 fully extracted and analyzed
