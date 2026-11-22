# Index: where to find things

Routing page for the whole repository. Paths are the current layout (restructure of 2026-11-21); [PATH_MAP.md](PATH_MAP.md) maps old paths to new ones. [README.md](README.md) describes the project and directory layout.

## Top-level map

| Directory | Contents |
|---|---|
| [platform/](platform/README.md) | Logical device reference: hardware specs, partitions, firmware versions, networks, CAN, vehicle config, boot, OTA, security posture, emulator |
| [hardware/](hardware/) | Physical device: teardown, connectors, bench setup, interfaces, modules, datasheets, schematics and board map |
| [eeprom/](eeprom/README.md) | EEPROM analysis docs, `bins/` (EEPROM dumps), `config_tool/` (editor; must stay next to `bins/`) |
| [diagnostics/](diagnostics/) | UDS, diagnosticsd and CAN reference docs |
| [audio/](audio/README.md), [video/](video/README.md), [projection/](projection/README.md), [runtime/](runtime/README.md), [analysis/](analysis/) | Subsystem and cross-cutting docs. Media codec specs: [video/media_codecs.md](video/media_codecs.md) (archival, see [video/video_codecs.md](video/video_codecs.md)) |
| [research/](research/README.md) | Deep-dive research, grouped into `boot-update-recovery/`, `security/`, `eeprom-calibration/`, `mdi2-bench-sessions/`, `rights-and-roadmap/`, `provenance/` |
| [evidence/](evidence/) | Raw captures and generated output: `enumeration/`, `decompiled/`, `ghidra-projects/` (gitignored), `reports/`, `session-logs/`, `dps-logs/`, `archives/`, `scratch/` |
| [tools/](tools/) | Executable code: `mdi2_client/`, `enumeration/`, `analysis-scripts/`, `bench/` |
| [reference/](reference/) | GM CalDef database (GIS-646) |

## Where does X live?

| Question | Start here |
|---|---|
| What are the SoC, RAM, storage, display and UART map? | [hardware/specs.md](hardware/specs.md) |
| What ports does the radio listen on? VLANs, switch, ADB over network | [platform/ethernet_networking.md](platform/ethernet_networking.md) |
| Which CAN IDs were captured? | [platform/can_network.md](platform/can_network.md), [diagnostics/GM_CAN_UDS_REFERENCE.md](diagnostics/GM_CAN_UDS_REFERENCE.md) |
| Vehicle network topology, ECU census, SecOC | [platform/vehicle_network.md](platform/vehicle_network.md) |
| Boot phases, A/B slots, AVB flow | [platform/boot_chain.md](platform/boot_chain.md) |
| Recovery, ELK, fastbootd, lock state | [platform/elk_recovery.md](platform/elk_recovery.md) |
| Partition map, `super`, filesystems | [platform/partitions_storage.md](platform/partitions_storage.md) |
| Y175 / Y177 / Y181 build differences | [platform/firmware_versions.md](platform/firmware_versions.md), [research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md](research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md) |
| OTA update stack and programming roles | [platform/ota_update_stack.md](platform/ota_update_stack.md), [platform/ota_programming_roles.md](platform/ota_programming_roles.md) |
| Security posture (SELinux, FBE, Trusty) | [platform/security.md](platform/security.md) |
| Trust anchors and verification keys | [research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md](research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md) |
| GHS hypervisor, downgrade protection, boot/update/recovery | [research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) |
| EEPROM layout, flags, SBI | [research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md](research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md) |
| Where are the EEPROM dumps? | [eeprom/bins/](eeprom/bins/) |
| SecurityAccess seed/key | [diagnostics/diagnosticsd_security_access.md](diagnostics/diagnosticsd_security_access.md), [research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md](research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) |
| diagnosticsd protocol, DIDs, routines | [diagnostics/diagnosticsd_protocol.md](diagnostics/diagnosticsd_protocol.md), [diagnostics/diagnosticsd_dids_and_dtc.md](diagnostics/diagnosticsd_dids_and_dtc.md), [diagnostics/diagnosticsd_routines_and_recovery.md](diagnostics/diagnosticsd_routines_and_recovery.md) |
| Custom calibration, DPS, CalSets | [research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md](research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md), [research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md](research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) |
| UDS calibration slot (02–0F) → part number → content map | [research/eeprom-calibration/CALIBRATION_SLOT_MAP.md](research/eeprom-calibration/CALIBRATION_SLOT_MAP.md) |
| Which calibration parameters are safe to customize vs. avoid | [research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md](research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md) |
| Full 404-key slot04 calibration catalog | [research/eeprom-calibration/calibration_glossary.md](research/eeprom-calibration/calibration_glossary.md) |
| MDI2 protocol and client | [research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md](research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md), [tools/mdi2_client/README.md](tools/mdi2_client/README.md) |
| Bench setup (OPU harness, T1/VLAN, CAN, UART) | [hardware/bench_setup.md](hardware/bench_setup.md) |
| Connectors, teardown, board map | [hardware/teardown.md](hardware/teardown.md), [hardware/interfaces/connectors.md](hardware/interfaces/connectors.md), [hardware/schematics/board_map/README.md](hardware/schematics/board_map/README.md) |
| CVEs, attack surface, escalation | [research/security/CVE_ATTACK_SURFACE_ANALYSIS.md](research/security/CVE_ATTACK_SURFACE_ANALYSIS.md), [research/security/KERNEL_CVE_ANALYSIS.txt](research/security/KERNEL_CVE_ANALYSIS.txt), [research/security/SHELL_ACCESS_ESCALATION_Jun2026.md](research/security/SHELL_ACCESS_ESCALATION_Jun2026.md) |
| CarPlay video decode | [video/carplay_video_pipeline.md](video/carplay_video_pipeline.md) |
| CarPlay vs Android Auto | [projection/carplay_vs_android_auto.md](projection/carplay_vs_android_auto.md) |
| Audio buses, HAL, effects | [audio/audio_subsystem.md](audio/audio_subsystem.md) (`audio/automotive_audio.md` is archival) |
| Boot timing, memory pressure, known issues | [runtime/README.md](runtime/README.md) |
| What third-party apps can access | [analysis/third_party_access.md](analysis/third_party_access.md), [analysis/platform_faq.md](analysis/platform_faq.md) |
| ADB/fastboot enumeration data by build | [evidence/enumeration/README.md](evidence/enumeration/README.md); scripts in [tools/enumeration/](tools/enumeration/) |
| Decompiled output and Ghidra data | [evidence/decompiled/](evidence/decompiled/), `evidence/ghidra-projects/` (gitignored), scripts in [tools/analysis-scripts/](tools/analysis-scripts/) — these read firmware/project paths from the `GM_RESEARCH_ROOT` and `GMINFO_REPO_ROOT` environment variables (unset by default; set them to your own checkout/working-tree locations before running) |
| Corpus-wide open conflicts, retired docs, evidence-tag convention | [research/README.md](research/README.md) |
| Provenance and verification | [research/provenance/INVENTORY.md](research/provenance/INVENTORY.md), [research/provenance/PROVENANCE_AUDIT_AUG2026.md](research/provenance/PROVENANCE_AUDIT_AUG2026.md), [VERIFICATION.md](VERIFICATION.md) |

## Research maturity (fact versus speculation)

Ratings of the documents under `research/`, assessed 2026-11-21. The full table, with the speculative sections of each document named, is in [research/MATURITY_RATINGS.md](research/MATURITY_RATINGS.md).

Rating rule: ratio = (C + FW + V) / (C + FW + V + I + U + ?), counting each document's own equivalent tag forms. **Verified**: ratio at least 0.75 and few open conflicts. **Mixed**: 0.40 to 0.75, or a verified core with substantial unverified sections. **Speculative**: below 0.40, or mainly hypotheses, plans or withdrawn guides. Documents with fewer than 6 tagged claims were rated from content.

**Rated by reading the document (30 files).**

| Rating | Documents |
|---|---|
| Verified | GHS_FILE_MAP_85098662, BOOT_TRUST_ANCHOR_AND_KEYS, GM_INFO37_BOOT_CHAIN_ANALYSIS, VIP_FIRMWARE_Y177_Y181_COMPARISON, DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW, CALSETSDB_HAND_EDITING_CHECKSUM_SHA256, calibration_glossary, MDI2_DPDU_API_PROTOCOL_AUG2026, AUG24_SESSION_FULL_PCAP_TIMELINE, USB_ADB_SESSION_FINDINGS_2026-10-10, INVENTORY, PROVENANCE_AUDIT_AUG2026 |
| Mixed | GHS_BOOT_UPDATE_RECOVERY_ANALYSIS, GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS, GHS_DOWNGRADE_PROTECTION_ANALYSIS, BOOT_CHAIN_ANALYSIS, CSE_HECI_ORCHESTRATION_ANALYSIS, RECOVERY_RAMDISK_RPC_ATTACK_SURFACE, GORDON_PEAK_CELADON_INTELLIGENCE, VMM1_PARSER_FUZZ_TARGETS_ANALYSIS, EEPROM_LAYOUT_COMPREHENSIVE_AUDIT, EEPROM_SECURITY_FLAG_TEST_PROTOCOL, GM_SEED_KEY_AND_CALIBRATION_SIGNATURES, CALDEF_VIP_CALIBRATION_ANALYSIS, VIP_CONTROL_ANALYSIS, SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS, MDI2_MANAGER_IDENT_LOG_PULL_AUG2026 |
| Speculative | DPS_AND_MODIFICATION_LANDSCAPE, MDI2_RAW_UDS_BYPASS_GUIDE, AE_RESEARCH_HANDOFF |

**Provisional: not read, rated by regex tag counting only (14 files).** No reader examined these documents, so the buckets below can be wrong. Tag counting under-counts documents that use prose labels or a different tag alphabet.

| Provisional bucket | Documents |
|---|---|
| Mixed (by tag count) | HARDWARE_HYPERVISOR_ATTACK_VECTORS, GM_REMOTE_ACCESS_ANALYSIS |
| Verified (by tag count; likely too high) | AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026, CVE_ATTACK_SURFACE_ANALYSIS, SHELL_ACCESS_ESCALATION_Jun2026. The last two have known stale open items. |
| Unrated (fewer than 6 tags or none) | GM_AAOS_Y181_SECURITY_ANALYSIS, KERNEL_CVE_ANALYSIS, DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026, RSA1024_PRIVATE_KEY_GHS_INTEGRITY, Y177_KERNEL_CVE_ANALYSIS (stub and archived copy), UNTRIED_ATTACK_VECTORS, AOSP_REPLACEMENT_RESEARCH, GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS |

Method notes: 16 of the 30 read documents were rated from content because they use few or no bracket tags. A tag ratio alone mis-ranks some documents; for example PROVENANCE_AUDIT_AUG2026 quotes tags from the documents it audits.

## External sources, not included in this repository

The owner keeps a separate, external working directory of raw captures, vendor installers/tools,
in-progress RE workspaces and other project material that predates or feeds this repo. It is not
mirrored here and its internal layout isn't repeated in this doc — a path on someone else's drive
tells another reader nothing useful and risks surfacing identifying detail, so this section
describes categories and conclusions only. This repo is the clean, organized distillation of that
material, not a copy of it: most of it is either superseded by a more-refined repo doc here,
vendor/licensed material kept out on purpose, or working material too raw to summarize. Surveyed
2026-11-21.

| Category | Distilled into (this repo) |
|---|---|
| Pre-repo project workspace for this exact vehicle/radio (session logs, bench handoffs, firmware analysis drafts) | `research/`, `platform/`, `diagnostics/` generally |
| Research tree for a **different vehicle platform** (Qualcomm SA8155 + QNX, Android 14) | `platform/qualcomm_cadillac_platform.md` only (flagged `[X] external`, unverified on this hardware) |
| Licensed ALLDATA/GM service manuals and captures | Cited as reference throughout; never copied in, per this repo's provenance policy |
| The original RE project this repo grew from, plus an early command-line precursor tool | `platform/pi_swap_feasibility.md`; otherwise superseded/stale (contradicted by later bench measurements) |
| Unrelated side tooling / an opaque device backup | Not cited; not relevant to this repo's scope |
| Active DPS/MDI2/calibration RE workspace (docs, disassembly, extracted installers, captures) | `research/mdi2-bench-sessions/`, `research/eeprom-calibration/` — the repo holds the distilled analysis, about 17 of its documents cited by name |
| A duplicate copy of that same RE workspace's logs | Already covered via `evidence/dps-logs/`, no separate action needed |
| Captures and RE scripts behind the Aug 2026 MDI2 work | `research/mdi2-bench-sessions/` |
| Stock module firmware, programming packages, data-wipe and CAN-bus-reset source material | `research/eeprom-calibration/canbus_reset/`, `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`, cited by name |
| Vendor installers (a DPS archive-creation tool, a VCAP interpreter, a GM dealer-tool installer) and the original CalDef database archive | `reference/` (CalDef, complete except one hash file); two small bridge-config notes already copied in byte-identical |
| Raw EEPROM dumps (stock, modified, debugging, a third ADB-enabled variant) and a glitch-tooling note | `eeprom/bins/` holds only 2 of these; kept external — see note below |

**Known gaps, not acted on:**
- One EEPROM dump there is already cited by name elsewhere in this repo (`research/eeprom-calibration/VIP_CONTROL_ANALYSIS.txt`) with an explicit note that it was deliberately **not preserved in this repository** — a prior editorial choice, not an oversight. A third ADB-enabled EEPROM variant differs from the repo's existing LTZ variant by only 44 of 8192 bytes (not meaningfully distinct); a "debugging" variant differs more (394 bytes) and is the one candidate that might be worth adding if someone wants to pursue it.
- One file in the external tree looks like a license-keygen for a GM dealer tool — deliberately not indexed, cited, or copied here.
- Several items in that external tree carry a real VIN or unit serial in their name or content — redact before citing or copying any of it into this repo.
