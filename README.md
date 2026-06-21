# gminfo_resources

Canonical reference for the **GM Info 3.7** (`gminfo37`) infotainment system — 2024 Chevrolet/GMC ICE vehicles (Silverado, etc.).

**Hardware:** Harman/Samsung · Intel Atom x7-A3960 (Apollo Lake) · Android 12 AAOS · GHS INTEGRITY IoT hypervisor  
**Research builds:** Y175 (Jun 2024) · Y177 (Mar 2025) · Y181 (Jul 2025, baseline)

---

## Directory Layout

```
gminfo_resources/
├── platform/          Hardware specs, boot chain, security, networking, firmware versions, tech specs
├── hardware/          Physical teardown, BOM, photos, EEPROM/IFWI analysis
├── eeprom/            EEPROM mod guide, analysis reports, undocumented flags, .bin dumps
│   ├── bins/          EEPROM binary dumps (stock, modified, ADB-enabled, bricked Y177)
│   └── config_tool/   eeprom_editor.py + firmware_re/ (115 decompiled VIP_APP functions)
├── enumeration/       ADB + fastboot enumeration by firmware build
│   ├── Y175/          Jan 2026 enum, VIP UART log, SELinux policy
│   └── Y181/          Dec 2025 enum + Apr 2026 enum (apr2026/), fastboot enums
├── diagnostics/       DPS session logs, CAN bus traces
│   └── dps/           A11 Radio (ECU 0x80) DPS 4.56 logs
├── research/          Deep-dive analysis docs, decompiled artifacts, scripts, reports
│   ├── MASTER_REFERENCE.md, INVENTORY.md, 17 docs/research + Y177/Y181 VIP/GHS analyses
│   ├── security/      Security-specific CVE and threat analyses
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
└── analysis/          Debloat comparison, third-party API access, platform FAQ
```

---

## Quick Reference

### Platform Identity

| Field | Value |
|-------|-------|
| Module name | `gminfo37` (GM Info 3.7) |
| ECU address | `0x80` (A11 Radio) |
| Manufacturer | Harman/Samsung |
| CPU | Intel Atom x7-A3960, 4-core, 1.88–2.4 GHz, 14nm Goldmont |
| RAM | 8 GB LPDDR4 (6 GB visible; ~604 MB reserved by GHS hypervisor) |
| Storage | 64 GB Samsung eMMC (KLMCG4JEUD, BGA-153) |
| Display | Chimei Innolux DD134IA-01B, 2400×960 @ 60 Hz, density 200 |
| GPU | Intel HD Graphics 505 (Gen9, 18 EUs), Mesa 21.1.5, GLES 3.2 |
| Audio HAL | HarmanHAL `android.hardware.audio@5.0` ("Titan" = SoC platform codename, not the HAL); 8 CarAudioService output buses; AVB transport |
| OS | Android 12 (API 32) AAOS, guest VM under GHS INTEGRITY IoT 2020.18.19 |
| VIP MCU | Renesas RH850/TM52176, QFP-144+, V850 core |
| EEPROM | ST M24C64, 8 KB, I2C (SBI security flags) |
| Kernel | Linux 4.19.283 (Y175) / 4.19.305 (Y177, Y181) |
| CAN | GM VIP/SDV1 (GB), CAN 2.0 29-bit · ECU 0x80 · Req 0x14DA80**F2** / Rsp 0x145AF2**80** in the captured DPS session (F1 = generic OBD tester address) |

### Firmware Builds

| Build | Kernel | SELinux | VIP Security Fn | Bootloader |
|-------|--------|---------|-----------------|------------|
| Y175 `W213E-Y175.5.2-SIHM22B-383.1` | 4.19.283 | Enforcing | Present | 2121-1 |
| Y177 `W231E-Y177.6.1-SIHM22B-499.2` | 4.19.305 | **Permissive** | **Stubbed (4B)** | — |
| Y181 `W231E-Y181.3.2-SIHM22B-499.3` | 4.19.305 | Enforcing | Full (906B) | 2344 |

Y177 is a security regression (permissive SELinux + stubbed VIP validation). Y181→Y177 downgrade is blocked by GHS rollback counter in `misc` (CRC32-only, no AVB).

### EEPROM ADB Unlock (M24C64, XGecu)

Flip these bytes to `0xFF` to disable the authorized-ADB-client requirement (shell uid=2000, not root). OTA resets to `0x00`.

| Offset | Stock | Unlocked | Role |
|--------|-------|----------|------|
| `0x0441` | `0x00` | `0xFF` | Primary SBI flag |
| `0x0A81` | `0x00` | `0xFF` | Mirror |
| `0x1A01` | `0x00` | `0xFF` | Second mirror |
| `0x0B41` | `0x00` | `0x01` | Debug mode |

Framing bytes at ±1 vary per firmware version — locate by offset, not pattern. See [`eeprom/README.md`](eeprom/README.md) for programmer commands and [`hardware/teardown.md`](hardware/teardown.md) for the full 8 KB EEPROM map.

---

## Key Documents

| Document | What it covers |
|----------|----------------|
| [`hardware/teardown.md`](hardware/teardown.md) | Full BOM, PCB layout, security architecture, GHS analysis, research vectors, catch-22s |
| [`platform/security.md`](platform/security.md) | SELinux, dm-verity, FBE, EEPROM security, CVEs, ProtoKey |
| [`platform/boot_chain.md`](platform/boot_chain.md) | 5-phase boot, GHS tasks, A/B metadata, misc partition |
| [`platform/firmware_versions.md`](platform/firmware_versions.md) | Y175/Y177/Y181 diff, DPS/CalDef |
| [`platform/networking.md`](platform/networking.md) | Ethernet topology, VIP IPC channels, open ports, UART |
| [`analysis/platform_faq.md`](analysis/platform_faq.md) | Evidence-backed FAQ (APK decompilation, logcat, ADB) |
| [`projection/cpc200_integration.md`](projection/cpc200_integration.md) | CPC200-CCPA wireless adapter integration |
| [`video/cinemo_nme_framework.md`](video/cinemo_nme_framework.md) | CINEMO/NME CarPlay framework architecture |
| [`enumeration/Y181/`](enumeration/Y181/) | Full ADB enumeration dump, SELinux policy, logcat |
| [`enumeration/Y175/Y175_VIP.log`](enumeration/Y175/Y175_VIP.log) | VIP UART boot log (IPC timing, ProtoKey, SBAT) |
| [`research/MASTER_REFERENCE.md`](research/MASTER_REFERENCE.md) | Top-level index of the full GM AAOS research corpus |
| [`eeprom/EEPROM_Analysis_Report.md`](eeprom/EEPROM_Analysis_Report.md) | Full 8 KB EEPROM map: UI flags, checksums, calibration, factory-reset triggers |
| [`eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`](eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md) | 10 undocumented flag candidates, CalGroup marker rotation, VIP 0xb67d0 RE |
| [`research/VIP_FIRMWARE_Y177_Y181_COMPARISON.md`](research/VIP_FIRMWARE_Y177_Y181_COMPARISON.md) | VIP security-fn stub→full diff at 0xb67d0 |
| [`research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`](research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) | GHS INTEGRITY hypervisor, AB0 rollback, VMM analysis |
| [`enumeration/Y181/apr2026/vulnerability_assessment.txt`](enumeration/Y181/apr2026/vulnerability_assessment.txt) | Apr 2026 CVE/threat assessment (DNSpooq, SOME/IP, SELinux) |
| [`diagnostics/dps/`](diagnostics/dps/) | DPS 4.56 session logs for A11 Radio (ECU 0x80): SBI/seed-key, ECU map, Y177 update |
| [`reference/GIS-646_CalDef_Database_Info3.7_and_Info3.8_V7.0.8_19April2023/`](reference/) | GM official CalDef database (215 caldef/enumdef + XSD schema) |

---

## Research Status

**Current target:** Y177 downgrade (permissive SELinux + stubbed VIP security).  
**Blocker:** GHS AB0 rollback counter in `misc` (vda9) — CRC32-only, written at hypervisor level only.

**Ranked options (post-binary analysis):**

1. Return-to-dealer screen — check ADB/USB exposure during that state (easiest; already been there once)
2. EEPROM `0x0A00` — 871 VIP firmware references, completely unknown function
3. Offline eMMC modification — dump BGA-153 eMMC, find AB0 in misc, recalculate CRC32
4. ELK trigger via VIP J6_CDD diagnostic channel (OBBPELK via HECI → ABL)
5. 3× boot failure escalation → GHS lifecycle last resort → ELK
6. `/dev/ghs/ota-isys` HostOS streaming (highest risk — GHS likely signature-checked)

See [`hardware/teardown.md`](hardware/teardown.md) §Ranked Research Vectors and §Key Catch-22s for full analysis.

---

## Data Sources

- ADB enumeration: Y175 (Jan 2026), Y181 (Apr 2026) — [`enumeration/`](enumeration/)
- EEPROM dumps: Y181 stock + modified — [`eeprom/`](eeprom/)
- VIP UART log: Y175 boot — [`enumeration/Y175/Y175_VIP.log`](enumeration/Y175/Y175_VIP.log)
- Hardware photos: IC close-up, board overview, XGecu programmer — [`hardware/`](hardware/)
- Binary analysis: VIP firmware 86331656 (9 Ghidra passes), GHS HOSTOS 85098662, plmanager, gm_update_engine, ELK (kernelflinger-07.02)
- Logcat: 3.7 GB across 29 files (Feb 2026)
- Partition images: Y177 + Y181 fully extracted and analyzed
