# gminfo_resources

Canonical reference for the **GM Info 3.7** (`gminfo37`) infotainment system — 2024 Chevrolet/GMC ICE vehicles (Silverado, etc.).

**Hardware:** Harman/Samsung · Intel Atom x7-A3960 (Apollo Lake) · Android 12 AAOS · GHS INTEGRITY IoT hypervisor
**Research builds:** Y175 (Jun 2024) · Y177 (Mar 2025) · Y181 (Jul 2025, baseline)

Start here:
- **[INDEX.md](INDEX.md)** — "where does X live?" routing page for the whole repo.
- **[research/README.md](research/README.md)** — the research corpus index and current investigation status.
- **[research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md)** — the consolidated Y181B investigation.

---

## Directory Layout

```
gminfo_resources/
├── platform/          Logical device reference: hardware, boot/partitions/recovery, networks and protocols, CAN, OTA, security, vehicle config, emulator (index: platform/README.md)
├── hardware/          Physical device: teardown, BOM, bench setup, module/ and interfaces/ docs, datasheets, schematics + board map
├── eeprom/            EEPROM mod guide, analysis reports, undocumented flags, .bin dumps
├── diagnostics/       Ethernet UDS, CAN/UDS reference, security access, DTC/DID docs
├── research/          Deep-dive analysis docs by topic (index: research/README.md)
│   ├── boot-update-recovery/   GHS hypervisor, boot chain, trust anchors/keys, OTA recovery, VIP firmware comparison
│   ├── security/               CVE and threat analyses, attack-vector catalogs, fuzz/
│   ├── eeprom-calibration/     EEPROM layout, seed-key, CalDef/CalSets, DPS Type4 workflow
│   ├── mdi2-bench-sessions/    MDI2 protocol notes, raw UDS guide, USB/ADB findings
│   ├── rights-and-roadmap/     AOSP replacement, lockdown and remote-access analyses
│   └── provenance/             Corpus inventory and provenance audit
├── evidence/          Raw captures and generated artifacts (not prose): enumeration/, decompiled/, reports/, session-logs/, dps-logs/, archives/
├── tools/             Executable code: analysis-scripts/, bench/, enumeration/, mdi2_client/
├── reference/         GM official CalDef GIS-646 database
├── audio/  video/  projection/  runtime/  analysis/   Android-side subsystem docs
└── PATH_MAP.md        Old path to new path for every moved file (2026-11-21 restructure)
```

---

## Quick Reference

| Field | Value |
|-------|-------|
| Module name | `gminfo37` (GM Info 3.7) |
| ECU address | `0x80` (A11 Radio) |
| Manufacturer | Harman/Samsung |
| SoC | Intel Atom x7-A3960, Apollo Lake, 4-core |
| OS | Android 12 (API 32) AAOS, guest VM under GHS INTEGRITY IoT |
| VIP MCU | Renesas RH850/F1K |

Full specs (RAM, storage, display, GPU, audio, kernel, firmware-build table):
[hardware/specs.md](hardware/specs.md), [platform/firmware_versions.md](platform/firmware_versions.md).

The [bench hardware setup baseline](hardware/bench_setup.md) owns the current OPU harness, VLAN/ADB access
and macOS privilege requirements. The [CAN message reference](platform/can_network.md) catalogs captured IDs.

---

## Current Research Focus

Native Linux hardware bring-up and a cold-power ELK recovery path independent of GHS/AAOS/Probe or
eMMC software. Status, test results and the full ranked research-vector list are maintained in
[research/README.md](research/README.md) and [hardware/teardown.md](hardware/teardown.md) §Ranked Research Vectors —
not duplicated here to avoid drift between copies.
