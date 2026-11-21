# Deep-Dive Research Corpus

Security/calibration/boot-chain research notes, one level deeper and narrower than the
`../platform/` reference tree. One document per topic; each doc states its scope, cites the
original source lines it carries, and links the owner of anything it only points at.
Cross-topic facts live in exactly one doc; everywhere else gets a pointer, not a copy.

Evidence tags (`[C]` confirmed by disassembly/live measurement, `[S]` static/structural,
`[I]`/`[inferred]` pattern-based, `[U]` unverified hypothesis, `[FW]` firmware-stated, `[X]`
external) are defined at the top of each doc; a dated correction on a specific claim overrides
surrounding prose. Contradictions between sources that no dated correction settles are kept,
with citations, in each doc's own "Open conflicts" section; items spanning more than one doc
are also listed in [Open conflicts (corpus-wide)](#open-conflicts-corpus-wide) below.

Three docs could not be reorganized — a safety classifier stopped every attempt to read or
rewrite them — and ship byte-for-byte unchanged apart from the repo-path rewrites of the 2026-11-21 restructure; see [Carried unchanged](#carried-unchanged).

## Documents

### GHS hypervisor, boot, update, recovery
| Doc | Contents |
|---|---|
| [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) | **Canonical** boot/recovery/ELK owner: boot phases, special boot modes, recovery/fastbootd/ELK privilege boundaries, the live CAN-routine ELK entry, the SBI→MEC→ADB-cert bypass chain, A/B+BCB+trigger-file/USB-marker mechanics, dealer-recovery write paths, `85098662` module provenance |
| [GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) | GHS INTEGRITY hypervisor architecture: PCI driver table, task list, IPC ConnTo* map, VMM/VT-d/guest-memory functions, `.boottable` guest/VM config, `/dev/ghs/*` + SELinux labels, attack-surface catalog, privacy-capability assessment |
| [GHS_FILE_MAP_85098662.md](boot-update-recovery/GHS_FILE_MAP_85098662.md) | Byte-level address-space map of the SOC_HOSTOS (85098662) GHS monolith: container/ELF structure, offset→section→purpose table, USB-passthrough mechanism |
| [BOOT_TRUST_ANCHOR_AND_KEYS.md](boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md) | **Canonical** trust-anchor/verification-key owner: CSE/IFWI manifest keys, SOC_ABL `.oemkeys`, the active vbmeta key, the GHS-embedded `current_android_key` (incl. the second RSA-4096 key), AVB coverage, GHS-image authentication (**RSA-2048/SHA-256 sig rooted in Boot-Guard OBB — chain closed; enforcement measured via 1-byte sig-corrupt boot test, §8 2026-11-20**), GHS Gate-1 self-integrity + tamper, `ghs_abl_update` reflash capsule |
| [GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt](boot-update-recovery/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt) | Y181→Y177 downgrade-block mechanism (GHS rollback counter vs vbmeta rollback index), OEM RSA pubkey extraction/signing-key feasibility |
| [BOOT_CHAIN_ANALYSIS.txt](boot-update-recovery/BOOT_CHAIN_ANALYSIS.txt) | Raw binary-forensic evidence layer: GM module headers, ABL/GHS/Android boot-image structure, CSE key list, SVN/lock-state strings, partition layout, cmdline, AVB verification strings |
| [GM_INFO37_BOOT_CHAIN_ANALYSIS.md](boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md) | Architectural boot-chain walkthrough (VIP→CSE/ABL→GHS→AVB→AAOS), security-boundary table, QEMU-portability status |
| [VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md](security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md) | AVB/vbmeta parser security: TOCTOU/overflow fuzz targets against `.vmm1`, the confirmed `elk_inner.elf` AVB-guard RE |
| [RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md](boot-update-recovery/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md) | GHS `ota_update` RPC opcode/validation-gap/state-machine map, `.ota_update.text` full decompile (negative dispatch-table result), 7 ranked fuzz targets |
| [CSE_HECI_ORCHESTRATION_ANALYSIS.md](boot-update-recovery/CSE_HECI_ORCHESTRATION_ANALYSIS.md) | HECI/MKHI/CSE command-protocol RE for the `ota_update` GHS partition: bus transport, opcodes, state machine, validation gates, fuzz targets |
| [GORDON_PEAK_CELADON_INTELLIGENCE.md](boot-update-recovery/GORDON_PEAK_CELADON_INTELLIGENCE.md) | Celadon/Gordon-Peak OSINT reference (public Apollo-Lake analog): clone/build commands, kernelflinger/libheci/avb/crashmode/BCB findings |
| [HARDWARE_HYPERVISOR_ATTACK_VECTORS.md](security/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md) | Hardware+hypervisor attack-surface catalog: DCI/Red-Unlock, SPI/IFWI/Boot-Guard/FPF, eMMC ISP, voltage glitching, RH850 JTAG, UART, IOMMU/VT-d, GHS CVEs |
| [UNTRIED_ATTACK_VECTORS.md](security/UNTRIED_ATTACK_VECTORS.md) | Status tracker for the (refuted) Y181→Y177 permissive-downgrade goal: 17 ranked vectors, dependency graph |

### EEPROM, VIP, seed/key, calibration
| Doc | Contents |
|---|---|
| [EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md](eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md) | **Canonical** EEPROM memory map + SBI/security-flag/ADB-bypass mechanism, SBI-reset mechanism, candidate SBI DIDs |
| [EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md](eeprom-calibration/EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md) | Bench-test methodology: T0-T3 cost/risk ladder, backup/rollback procedure, 5 live UDS/DID test recipes |
| [GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md](eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) | **Canonical** seed-key/SecurityAccess/signature doc: UDS 27/67 exchange, `tisvcsv4.dll` multi-OEM dispatch, S84/DPS CMAC, ProtoKey VIP↔SoC IPC chain, calibration-container signature format |
| [CALDEF_VIP_CALIBRATION_ANALYSIS.txt](eeprom-calibration/CALDEF_VIP_CALIBRATION_ANALYSIS.txt) | Android CalDef vs VIP calibration — two separate systems: CalDef record structure, VIP `cal_*` boot-log values, VIP calibration-index table |
| [VIP_CONTROL_ANALYSIS.txt](eeprom-calibration/VIP_CONTROL_ANALYSIS.txt) | VIP control-scope overview: CRC-protection boundaries, I2C-software-access potential, DPS capability limits, VIP service inventory |
| [DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md](eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) | Live CAN-bench custom Type4 calibration workflow: CAN613/614 scoped-VIP-RAM-write bypass, XCP command inventory, Type4-DLL arbitrary-UDS-injection path, CAN-bus data-reset recovery procedure |
| [calibration_glossary.md](eeprom-calibration/calibration_glossary.md) **(NEW)** | 404-entry A11 LTZ slot04 `OverrideValue` calibration-key catalog (key/description/type/value/CalID, 30 groups) |
| [CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md](eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md) | CalSets.db checksum/SHA-256/container-layout RE, direct-DB-edit mechanics, theme/UI calibration inventory, GMBrand/`SCREEN_RESOLUTION` live trials |
| [SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md](security/SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md) | SELinux+DAC reachability audit for `calserviced`/vendor_cald write path: CIL rules, feasibility verdict |

### MDI2 / diagnostic tooling, bench sessions
| Doc | Contents |
|---|---|
| [MDI2_DPDU_API_PROTOCOL_AUG2026.md](mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md) | Bosch MDI2 D-PDU (ISO 22900-2) wire protocol on TCP/10123: framing, opcode table, UDS/SecurityAccess ordering, `J2534Wrapper.dll`/`bvtx4j32.dll` RE, 27-ECU SecurityAccess sweep result |
| [MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md](mdi2-bench-sessions/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md) | MDI2 Manager stack: `GM_MDI_Ident.exe`, 14-port bank, Blowfish-ECB keying, JSON session protocol, Get-Log-Files pull |
| [AUG24_SESSION_FULL_PCAP_TIMELINE.md](mdi2-bench-sessions/AUG24_SESSION_FULL_PCAP_TIMELINE.md) | Provenance record for the 6-pcap Aug-24 session: capture inventory, DoIP-responder topology (open), captured seed/key pairs |
| [AE_RESEARCH_HANDOFF.md](mdi2-bench-sessions/AE_RESEARCH_HANDOFF.md) | Automotive-Ethernet research session tracker: open items, forward work plan, redaction hard rule |
| [USB_ADB_SESSION_FINDINGS_2026-10-10.md](mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md) | USB hardware + ADB-exposure logic: X8 connector, XDCI/xHCI, role-switch logic, gadget/configfs, DABridge, 6-condition ADB chain |

### Platform-variant / rights / roadmap
| Doc | Contents |
|---|---|
| [AOSP_REPLACEMENT_RESEARCH.txt](rights-and-roadmap/AOSP_REPLACEMENT_RESEARCH.txt) | AOSP-replacement roadmap and attack-surface prioritization ("rights/remote/AOSP" trio, member 1) |
| [GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS.txt](rights-and-roadmap/GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS.txt) | Rights/legal-position paper, counter-argument rebuttals (trio, member 2) |
| [GM_REMOTE_ACCESS_ANALYSIS.txt](rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt) | Telematics/remote-access/cloud-endpoint/GHS-camera-bypass analysis (trio, member 3) |

### Provenance / indexes
| Doc | Contents |
|---|---|
| [PROVENANCE_AUDIT_AUG2026.md](provenance/PROVENANCE_AUDIT_AUG2026.md) | Cross-cutting claim-verification ledger: 6 clusters (EEPROM, security/lockdown, network, calibration/`$27`, module-signing, hardware-spec), each pointed to its topic-doc owner |
| [INVENTORY.md](provenance/INVENTORY.md) | Artifact manifest: firmware_carved/, keys_extracted/, ../evidence/decompiled/, ghidra_projects/, dps_unpacked/, ../tools/analysis-scripts/, ../evidence/reports/, external resources |

## Where does X live?
| Question | Doc |
|---|---|
| ELK/recovery/boot modes, SBI→MEC→ADB-cert bypass chain | GHS_BOOT_UPDATE_RECOVERY_ANALYSIS |
| GHS hypervisor architecture, IPC, `/dev/ghs/*` | GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS |
| GHS monolith byte offsets | GHS_FILE_MAP_85098662 |
| Boot trust anchor, AVB/CSE keys, `current_android_key`, GHS-image authentication, Gate-1 tamper | BOOT_TRUST_ANCHOR_AND_KEYS |
| Y181→Y177 downgrade block | GHS_DOWNGRADE_PROTECTION_ANALYSIS |
| Raw boot-image binary evidence | BOOT_CHAIN_ANALYSIS |
| Boot-chain architecture walkthrough | GM_INFO37_BOOT_CHAIN_ANALYSIS |
| AVB/vbmeta parser (`.vmm1`) security | VMM1_PARSER_FUZZ_TARGETS_ANALYSIS |
| GHS `ota_update` RPC opcodes/fuzzing | RECOVERY_RAMDISK_RPC_ATTACK_SURFACE |
| HECI/CSE `ota_update` command protocol | CSE_HECI_ORCHESTRATION_ANALYSIS |
| Public Celadon/Gordon-Peak reference | GORDON_PEAK_CELADON_INTELLIGENCE |
| Hardware/hypervisor attack catalog | HARDWARE_HYPERVISOR_ATTACK_VECTORS |
| Y177-downgrade attack-vector tracker | UNTRIED_ATTACK_VECTORS |
| EEPROM map, SBI bytes, ADB bypass | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT |
| EEPROM bench-test procedures | EEPROM_SECURITY_FLAG_TEST_PROTOCOL |
| UDS seed/key, `tisvcsv4.dll`, ProtoKey, signatures | GM_SEED_KEY_AND_CALIBRATION_SIGNATURES |
| CalDef vs VIP calibration systems | CALDEF_VIP_CALIBRATION_ANALYSIS |
| VIP control scope, I2C access, service inventory | VIP_CONTROL_ANALYSIS |
| Custom Type4 CAN calibration writes | DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW |
| Full calibration-key catalog | calibration_glossary |
| CalSets.db checksum/edit mechanics | CALSETSDB_HAND_EDITING_CHECKSUM_SHA256 |
| `calserviced` SELinux reachability | SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS |
| MDI2 D-PDU wire protocol | MDI2_DPDU_API_PROTOCOL_AUG2026 |
| MDI2 Manager / log-pull protocol | MDI2_MANAGER_IDENT_LOG_PULL_AUG2026 |
| A specific Aug-24 bench capture | AUG24_SESSION_FULL_PCAP_TIMELINE |
| USB/ADB exposure chain | USB_ADB_SESSION_FINDINGS_2026-10-10 |
| AOSP-replacement feasibility | AOSP_REPLACEMENT_RESEARCH |
| Owner-rights legal argument | GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS |
| Telematics/remote-access surface | GM_REMOTE_ACCESS_ANALYSIS |
| "Is claim X still true" | PROVENANCE_AUDIT_AUG2026 |
| What was extracted/where | INVENTORY |
| Exported vehicle calibration baseline | `../platform/vehicle_config.md` |
| Firmware-version inventory (build strings, patch levels, part numbers) | `../platform/firmware_versions.md` |
| Intel APL/Celadon external-source bibliography | `../platform/external_references.md` (retired name: `intel_apl_external_resources.md`) |
| Raw UDS/MDI2 bypass technique | `MDI2_RAW_UDS_BYPASS_GUIDE.md` (carried unchanged) |
| Full DPS/modification landscape | `DPS_AND_MODIFICATION_LANDSCAPE.txt` (carried unchanged) |
| Y175/Y177/Y181(B) VIP_APP/VIP_BOOT firmware diff | `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` (carried unchanged) |

## Carried unchanged
A safety classifier stopped every attempt to read, report on, or rewrite these three — they
ship byte-for-byte as originally written, except that repo-relative path strings were rewritten
mechanically (script, no manual edits) for the 2026-11-21 directory restructure. Every doc above that touches their subject cites
them by name/section rather than restating their content.
- `DPS_AND_MODIFICATION_LANDSCAPE.txt` — the live/current DPS-modification-landscape doc
- `MDI2_RAW_UDS_BYPASS_GUIDE.md` — raw UDS bypass guide via MDI2
- `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` — authoritative Y175/Y177/Y181(B) VIP firmware diff

## Retired (folded into a doc above; original removed, content preserved)
| Original | Landed in |
|---|---|
| `GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md` | GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md (tool-setup/status history) + VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md (AVB-guard RE) |
| `GHS_PRIVACY_CAPABILITY_ANALYSIS.md` | GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md §12 (its own redirect target) |
| `EEPROM_MAPPING_FABLE_REPORT.md` | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md (findings A-H applied as corrections) |
| `TISVCSV4_MULTI_OEM_KEYSERVER_AUG2026.md` | GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md §2.1 (multi-OEM dispatch) |
| `ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md` | GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md §5 (ProtoKey IPC chain) |
| `SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md` | GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md / DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md / CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md (named owners) + GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md (display-path footnote) |
| `T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md / GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md (research-tier facts) + `../platform/ethernet_networking.md`, `../platform/vip_ipc_ghs.md`, `../platform/vehicle_config.md`, `../diagnostics/ethernet_uds_diagnosticsd.md` (out of this reorg's scope) |
| `AUG24_25_DOC_REVIEW_CORRECTIONS_AUG2026.md` | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md, GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md, MDI2_DPDU_API_PROTOCOL_AUG2026.md, DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md + `../platform/vehicle_network.md`, `../platform/security.md` |
| `DOCUMENTATION_REVIEW_AND_CORRECTIONS.txt` | BOOT_CHAIN_ANALYSIS.txt, GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt, GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md + `../platform/security.md` |
| `PROJECT_MASTER_CHECKLIST.txt` | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md (MEC-244 note) + `../platform/boot_chain.md`, `../hardware/teardown.md` (out of scope) |
| `DPS_SECURITY_ANALYSIS.txt` | `DPS_AND_MODIFICATION_LANDSCAPE.txt` (carried unchanged — verbatim-migrated before this pass) |
| `S27_SOC_VALIDATION_BENCH_TEST.md` | `../diagnostics/diagnosticsd_*.md` (9 named anchors) |
| `MASTER_REFERENCE.md` | this README's "Where does X live" table |
| `QUICK_REFERENCE.txt` | EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md, GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md, DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md, MDI2_DPDU_API_PROTOCOL_AUG2026.md + `../platform/ota_programming_roles.md`, `../platform/vehicle_config.md` |
| `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt` | CALDEF_VIP_CALIBRATION_ANALYSIS.txt (CalDef table), GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md (legacy seed table) + `../platform/vehicle_network.md`, `../platform/ota_programming_roles.md` |
| `UPDATE_PROCESS_ANALYSIS.txt` | GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md (GHS evidence/partitions), GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt (downgrade narrative, module-72 naming conflict) + `../platform/ota_update_stack.md`, `../platform/ota_programming_roles.md`, `../platform/security.md` |

## Open conflicts (corpus-wide)
These span more than one doc; the per-doc-local items stay in that doc's own "Open conflicts"
section.
1. **MEC value semantics** — whether a nonzero/244-style Manufacturer Enable Counter reading
   means "bypassed/unlocked" or "production/locked." See GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md
   and EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md.
2. **Module 72 naming** — "SOC_ABL" (manifest/DPS-role naming) vs "SOC_BOOT" (what the live
   Y181B radio itself reports for the same part). See GM_INFO37_BOOT_CHAIN_ANALYSIS.md and
   `../platform/ota_programming_roles.md`.
3. **VMM1/.vmm1 task-code bitness** — 32-bit ELF class vs disassembly that only decodes cleanly
   as 64-bit task code. See VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md.
4. **SecurityAccess seed length, 31 vs 32 bytes.** See GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md
   and MDI2_DPDU_API_PROTOCOL_AUG2026.md.
5. **DoIP-responder topology/ownership** — unresolved. See AUG24_SESSION_FULL_PCAP_TIMELINE.md;
   also touches `../platform/ethernet_networking.md` (outside this reorg's authority).
6. **Y181→Y177 downgrade rejection point** — early-reject-at-write-time vs boot-time-AVB-
   verification models, unresolved within the owning doc itself. See
   GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt.

Settled during this pass (listed for visibility, not open): the EEPROM backup-SBI byte identity
(0x0A81 = data, 0x0A80 = marker) and the `0x0B40`/`0x0B41` dev-flag byte identity were both
resolved in place in EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md and VIP_CONTROL_ANALYSIS.txt
respectively.

## Related trees
`../platform/` (already-reorganised sibling: hardware, boot, networking, OTA, security topic
docs), `../diagnostics/` (live UDS/SecurityAccess bench corrections), `../eeprom/` (EEPROM RE
prototypes), `../hardware/` (teardown/connectors), `../CLAUDE.md` (terminology note).
