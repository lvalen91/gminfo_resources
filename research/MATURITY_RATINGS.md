# Research Maturity Ratings (fact vs speculation)

Assessed 2026-11-21. Paths are the current (post-restructure) locations. The ratings describe each whole document; the "speculative sections" column names the parts of a Verified or Mixed document that are less established, so no document has to be split. Referenced from [INDEX.md](../INDEX.md).
Rating rule: ratio = (C+FW+V)/(C+FW+V+I+U+?) using each doc's own equivalent tag forms. Verified >= 0.75 and few open conflicts; Mixed 0.40-0.75 or verified core + substantial unverified sections; Speculative < 0.40 or mainly hypotheses/plans/withdrawn guides. basis=content where <6 tagged claims.
"READ" = a reader agent read the whole file. "REGEX-ONLY (not read)" = mechanical tag counting only; no agent read the file (the readers for these were declined/blocked; not worked around). Regex counts under-count (many docs use prose/other tag forms) so regex-only buckets are PROVISIONAL.

## READ ratings (30 files; each file was read in full by a reader: 12 Verified, 15 Mixed, 3 Speculative)
| Final path | Rating | C/FW/V | I/U/? | ratio | basis | note / speculative sections |
|---|---|---|---|---|---|---|
| research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md | Mixed | 43 | 19 | 0.69 | content (prose labels) | speculative: §0.1 CVE-candidate table; §2.3.3 VIP-ELK-selector mega-section (~L860-3263), pm_trans-bit/S3 hypothesis ~L1439 |
| research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md | Mixed | 24 | 13 | 0.65 | tags | speculative: §12 privacy-capability (inferred from function names); §11 attack surfaces |
| research/boot-update-recovery/GHS_FILE_MAP_85098662.md | Verified | 2 | 2 | n/a | content | byte-by-byte re-derived, no gaps; 768 B key + signature tail [U] |
| research/boot-update-recovery/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt | Mixed | 8 | 9 | 0.47 | tags | speculative: §4.2/4.4/4.5 misc-partition counter theory; §8.4 options A-G; §9.2-9.4; §2.1 superseded model |
| research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md | Verified | 19 | 5 | 0.79 | tags | speculative: §12 open questions/theory; §1 row 0 fuse root [I]; §8 superseded verdict (struck through) |
| research/boot-update-recovery/BOOT_CHAIN_ANALYSIS.txt | Mixed (leans speculative) | 4 | 7 | 0.36 (strict ratio = Speculative band) | content | forensic groundwork solid; §10 exploitation paths all UNEXPLORED/untested |
| research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md | Verified | 0 | 5 | n/a | content | speculative: §10.3 MEC counter [U]; §11.5 CRC32 risk [inferred]; §11.6; Open Conflicts #1,#3 |
| research/boot-update-recovery/CSE_HECI_ORCHESTRATION_ANALYSIS.md | Mixed | 1 | 4 | 0.20 (n/a) | content | speculative: §5 fuzz targets (proposed), §6 reachability (inferred), §7 open RE items |
| research/boot-update-recovery/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md | Mixed | 20 | 10 | 0.67 | tags | speculative: §2 opcode dispatch table, §5 state machine, §6 fuzz targets |
| research/boot-update-recovery/GORDON_PEAK_CELADON_INTELLIGENCE.md | Mixed | n/a | n/a | n/a | content | external OSINT on a public analog platform; GM-unit equivalence (board revision -401, BSP/kernel tree) unverified |
| research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md | Verified | n/a | n/a | n/a | content | open: validator's external callers not identified; §9 downgrade-table row "Unknown" |
| research/security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md | Mixed | 8 | 4 | 0.67 | tags | speculative: §1-4 fuzz targets (untested); Open Conflict 32-vs-64-bit task code |
| research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md | Mixed | 44 | 28 | 0.61 | tags | speculative: §5.4 trim bytes [U]; §5.8 untested offsets; §6 unsolved CRC algorithms; §3 "working model (not proven)"; §7 marker taxonomy [U] |
| research/eeprom-calibration/EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md | Mixed | 3 | 2 | n/a | content | speculative: Tests 3, 4, 5 (unexecuted probing, unknown DIDs) |
| research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md | Mixed | ~13 | ~4 | ~0.76 | tags (own P/C/S/B/M/? alphabet) | two unresolved Open Conflicts (31-vs-32 seed length; MEC semantics); speculative: §2 "?" bullets, §8 competing-explanation, §9 RSA-1024 note |
| research/eeprom-calibration/CALDEF_VIP_CALIBRATION_ANALYSIS.txt | Mixed | 5 | 7 | 0.42 | tags | speculative: §7 remaining attack vectors, §8 research priorities (nothing executed) |
| research/eeprom-calibration/VIP_CONTROL_ANALYSIS.txt | Mixed | 22 | 8 | 0.73 | tags | speculative: §3.2, §3.3, §6.1 (unexecuted), §7 SUSPECTED rows |
| research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md | Verified | n/a | n/a | n/a | content | speculative: §5 "Other paths and unresolved questions"; XCP-style command inventory (mostly "Mapped; not live tested") |
| research/eeprom-calibration/DPS_AND_MODIFICATION_LANDSCAPE.txt | Speculative | 4 | 2 | 0.67 (n/a) | content | Dec 2025 core is a planning/exploitation-strategy doc with since-retracted claims; §8 (2026-09-10) markedly more evidence-backed |
| research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md | Verified | 6 | 1 | 0.86 | tags | speculative: §3d status-0x12 trace; §5 removed calseal.py (non-functional) |
| research/eeprom-calibration/calibration_glossary.md | Verified | n/a | n/a | n/a | content | 404-entry catalog from device DB/XML cross-matched to CalDef (398/404); caveat: CalDef text is documentation, not a behaviour test |
| research/security/SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md | Mixed | 8 | 5 | 0.62 | tags | speculative: Y175 policy-reuse [inferred]; updater caller boundary open |
| research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md | Verified | n/a | n/a | n/a | content | speculative: §6 seed length 31-vs-32 (Open Conflict #1); §3 L144 'unverified builders'; §10.5 IOCTL/ComParam IDs runtime-assigned |
| research/mdi2-bench-sessions/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md | Mixed | 4 | 2 | 0.67 | tags (6 tag hits) | speculative: §3 FTPS log path [U]; Open conflicts (keyring-table mismatch) |
| research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md | Speculative | n/a | n/a | n/a | content | Route A withdrawn/refuted; calibration write failed (NRC 72); ADB escape retry failed; §5 checklist unexecuted; 5 cited docs missing |
| research/mdi2-bench-sessions/AUG24_SESSION_FULL_PCAP_TIMELINE.md | Verified | n/a | n/a | n/a | content | speculative: Finding 5 SBI reset trigger unidentified; open threads; Open conflict #1 DoIP responder topology |
| research/mdi2-bench-sessions/AE_RESEARCH_HANDOFF.md | Speculative | n/a | n/a | n/a | content | open-items tracker + forward work plan of untried fuzz/injection targets |
| research/mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md | Verified | 25 | 4 | 0.86 | tags | speculative: §9 open items (8 [UNVERIFIED]; #5 xHCI PCI addr inferred; #8 ADB boot persistence) |
| research/provenance/INVENTORY.md | Verified | 0 | 0 | n/a | content | index/manifest; one inline claim cited to source |
| research/provenance/PROVENANCE_AUDIT_AUG2026.md | Verified | 6 | 1 | 0.86 | tags | ratio inflated: the tags are QUOTED from audited docs; rows left UNSUPPORTED/INFERRED: #5,#9,#10,#16,#19,#20,#28,#30,#32,#33 |

## REGEX-ONLY (not read) — PROVISIONAL, 14 files
No agent read these files (the readers assigned to them were declined or blocked). The buckets come from mechanical tag counting only and are provisional.
| Final path | counts C/FW : I/U/? : S/V/X | regex bucket | caveat |
|---|---|---|---|
| research/security/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md | 10 : 12 : 10 | Mixed (0.45) | |
| research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt | 3 : 4 : 6 | Mixed (0.43) | only 7 tags |
| research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md | 11 : 0 : 0 | Verified (1.00) | one-sided; sibling docs record it as the source that cleared a malloc "open" item |
| research/security/CVE_ATTACK_SURFACE_ANALYSIS.md | 6 : 1 : 0 | Verified (0.86) | KNOWN stale open items per cleanup findings (Boot Guard FPF "Critical Unknown", SELinux-blocks-USB-chain question, diagnosticsd malloc "open") — regex bucket likely too high |
| research/security/SHELL_ACCESS_ESCALATION_Jun2026.md | 6 : 0 : 0 | Verified (1.00) | stale "open" malloc item per cleanup findings |
| research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt | 1 : 0 : 0 | Unrated (<6 tags) | |
| research/security/archive/Y177_KERNEL_CVE_ANALYSIS.txt | 0 : 0 : 0 | Unrated (archived; superseded by KERNEL_CVE_ANALYSIS.txt Appendix E) | |
| research/security/KERNEL_CVE_ANALYSIS.txt | 0 : 0 : 0 | Unrated (no tags) | |
| research/security/DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026.md | 0 : 0 : 0 | Unrated (no tags) | |
| research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md | 0 : 0 : 0 | Unrated (no tags) | |
| research/security/Y177_KERNEL_CVE_ANALYSIS.txt (0.2 KB untracked stub) | 0 : 0 : 0 | Unrated | stub |
| research/security/UNTRIED_ATTACK_VECTORS.md | 2 : 2 : 3 | Unrated (4 tags) | title/purpose: untried vectors |
| research/rights-and-roadmap/AOSP_REPLACEMENT_RESEARCH.txt | 1 : 0 : 0 | Unrated | |
| research/rights-and-roadmap/GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS.txt | 0 : 0 : 0 | Unrated | |
Regex tags used: [C]/[FW] (confirmed) vs [I]/[inferred]/[U]/[?]/[unverified] (unverified); [S]/[V]/[X] counted separately.
Observations: (1) The README tag convention is applied inconsistently: 16 of the 30 READ docs were rated from content (basis=content) because they use no bracket tags or too few of them (prose labels such as "confirmed"/"UNVERIFIED" instead), and several use a different alphabet (GM_SEED_KEY uses P/C/S/B/M/?). (2) A tag ratio alone mis-ranks some docs (PROVENANCE_AUDIT quotes tags it disputes; BOOT_CHAIN_ANALYSIS strict ratio 0.36 but real forensic content). (3) Rating applies to the whole doc; the 'speculative sections' column lets INDEX.md flag sections without splitting files.
