# Open Questions Sweep — 2026-11-23

Consolidated from 5 parallel agent passes over the whole repo (`platform/`+`runtime/`+`analysis/`,
`eeprom/`+`diagnostics/`+`hardware/`, `research/`+`audio/`+`video/`+`projection/`+`reference/`,
`evidence/`, `tools/`). Each agent read its slice for explicit TODO/TBD/"unknown"/"unverified"
markers, unconfirmed hypotheses, doc-vs-doc contradictions, and references to files that don't
exist. This file is the raw merge — file:line citations are in the per-area sections below.
Treat it as a backlog, not a finished analysis; some items may already be stale by the time you
read this.

## How to use this
Each numbered item: **question** — `file:line` — why it's open — what would resolve it.
Pull the relevant section into a task list or close items out directly in the source doc as you
verify them (the repo already does this via `[CONFIRMED]`/`[UNVERIFIED]` tags and VERIFICATION.md).

---

## 1. Network topology (platform/)
- CAN `0x45` (CGM) identity vs. Ethernet `.107`/`.112`/`.102` — not established to be the same
  module. `platform/ota_programming_roles.md:337-343`, `platform/vehicle_network.md:379-405`.
- `.107` vs `.112` role: two docs give contradictory labels. `vehicle_network.md:381-396`,
  `ethernet_networking.md:364`.
- `.102` role unresolved (`[?]`). `vehicle_network.md:398`.
- Port-to-bus numbering doesn't reconcile with the VLAN 2 mask. `ethernet_networking.md:119,368`.
- Which bus actually carries the VLAN 2 AVB flood — forwarded copy, separate stream, or
  tag-multiplexed. `avb_audio_transport.md:267` (also cites stale line numbers in
  `vehicle_network.md` that have since moved).
- X11 pins 1/2 recorded "not occupied" but carry live VLAN traffic — conflicts with the ALLDATA
  connector reading. `ethernet_networking.md:314`, `vehicle_network.md:407`.
- VLAN 9 is configured but never observed on the wire. `ethernet_networking.md:110-115`.
- gPTP grandmaster election was never decoded from the capture, even though the Pi-swap
  feasibility argument depends on it. `vehicle_network.md:402`, `pi_swap_feasibility.md:124`.

## 2. Boot / partition / trust chain (platform/, hardware/, evidence/)
- Y181B `super` partition size is unmeasured (doc cites an unsourced 8.6GB vs Y175's measured
  18000 MiB). `platform/partitions_storage.md:184`.
- Whether Y181B mounts via SSDT vs plain-text fstab is unresolved on real hardware (QEMU and Y175
  contradict the SSDT path). `partitions_storage.md:20,185`.
- Boot Guard enforcement depends on FPF/OTP fuse state, not confirmed from any available package.
  `platform/boot_chain.md:261`; same gap independently flagged in `hardware/teardown.md:255,280`.
- `OEMLock` UEFI variable: SPI-NOR-backed (offline-settable) vs RPMB-backed (replay-protected) —
  called "the open question" for the whole unlock-feasibility assessment. `hardware/teardown.md:239-251`.
- Bootloader lock-state disagreement: ELK says unlocked, AAOS says locked, fastbootd says
  unlocked:no. Persistence across a cold power-cycle untested. `platform/elk_recovery.md:47-49,226-227`.
- SELinux mode on the cmdline carries both `permissive` and `enforcing` tokens; "later wins" is
  only inferred, not read live. `boot_chain.md:442`.
- Whether SOC_ABL's additive checksum is the *only* integrity check on GHS, or whether a signed
  manifest / RBE hash check exists elsewhere in the untraced CSE boot path.
  `evidence/decompiled/bootloader_a/ANALYSIS.md:66-75`.
- Purpose of 4 embedded RSA-1024 public keys and 1 RSA-1024 private-key candidate in
  `ghs_integrity.elf` — never matched against known cert/key material.
  `evidence/reports/forensic_out.txt:96-146`, `evidence/session-logs/RESEARCH_STATE_MAP_JUN2026.md:99-102`.
- Rollback/downgrade-protection counter storage location (misc partition vs vda9) — hypothesis
  only, the compare routine was never disassembled; a prior pass's own "confirmed" note
  contradicts its "open questions" list in the same document.
  `research/boot-update-recovery/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt:226-288,599-679`.
- Blank-eMMC emergency recovery entry and full restore are unverified end to end.
  `VERIFICATION.md:24-27`, `hardware/teardown.md:795,811-815`.

## 3. Diagnostics / UDS / calibration tooling (diagnostics/, eeprom/, tools/)
- Several SecurityAccess / EEPROM-flag mechanisms described in `eeprom/` and the
  `VIP_*_AUG2026.md` series remain **static-analysis-only**: the actual dispatch/consumer code
  paths were not fully traced, and two companion documents disagree on whether a key indirect-call
  gap was ever closed. See `hardware/module/eeprom.md:118-124` vs `hardware/teardown.md:921,988-996`
  (same evidence, opposite "is this lead still live" conclusion), and
  `eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md:138` vs
  `eeprom/VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md:25,31`.
- SecurityAccess seed length disagreement (31 vs 32 bytes) between two independent capture docs,
  on a value that should be a fixed firmware property. `research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md:636-650`
  vs `research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md` §6.
- `tools/mdi2_client`'s security/CMAC and D-PDU wire-format code is explicitly marked with
  `# GUESS:` comments throughout and has never been validated against a captured seed/response
  pair or a live D-PDU trace — the KAT test is skipped because its fixture doesn't exist.
  `mdi2_client/mdi2/security_cmac.py:19-30`, `mdi2_client/mdi2/dpdu.py` (multiple lines),
  `mdi2_client/tests/test_security_cmac.py:165-176`.
- `open_live_programming_transport` is a permanent stub that always raises, pending resolution of
  response-attribution and teardown-cleanup questions. `mdi2_client/mdi2/programming_transport.py:23,307`.
- Modified calibration packages fail with NRC `7F 36 72`; root cause (signature/hash/size) never
  isolated. `mdi2_client/docs/CALIBRATION_WRITE.md`, `mdi2_client/README.md:19-22`.
- `sweep_security_access.py` — the 19-level unlock-bitmask sweep has never been run against real
  hardware; its own docstring says so. `mdi2_client/scripts/sweep_security_access.py:19-20`.
- Several `diagnosticsd_*.md` docs keep their own running "still open" lists (worker-starvation DoS
  internals, vndbinder probing, concurrent-handler capacity, audio DID/IOCID subclass mapping,
  tone-sweep safety prerequisites) — see `diagnostics/ethernet_uds_diagnosticsd.md:70-110` and
  `diagnostics/diagnosticsd_protocol.md:150,175-195,268`.
- EEPROM offsets with unresolved function: `0x0B60`, `0x0C01`, `0x0BA0`, `0x0C00`, `0x15C0`,
  `0x1AC0`, plus a CRC algorithm over `0x16E0`/`0x19E0`/`0x1B40` that is explicitly unknown and the
  doc warns not to attempt forging against. `hardware/module/eeprom.md:71-72`,
  `eeprom/EEPROM_Analysis_Report.md:161-167,400-405,437-507`.

## 4. CAN / audio / video / display
- Only 17 of 277 application-slot CAN IDs have ever been driven/observed; ~260 untested.
  `platform/can_network.md:517-523`.
- Audio: A128/A512 packing, 44.1→48kHz conversion location, SRP/MSRP requirement, speaker map,
  and several bus roles remain open. `platform/avb_audio_transport.md:216,271`.
- `CSM` acronym expansion ("Cabin Sound Manager") is explicitly tentative/unconfirmed.
  `audio/carplay_audio_pipeline.md:126`.
- Video/media codec capability tables are internally inconsistent (benchmarks that are physically
  backwards, resolution ceilings that contradict themselves) across three separate files, never
  reconciled against real hardware limits. `video/video_codecs.md:10`, `video/media_codecs.md:9`,
  `video/README.md:40`, `video/software_rendering.md:10`.
- GPIO 449 falling-edge framebuffer-write theory is "plausible, not confirmed," replacing an
  earlier hypothesis that was itself never confirmed before being superseded.
  `video/display_subsystem.md:410`.
- Several video fixes (corrected framebuffer image, new display "readiness path", "Probe07") have
  only been validated in emulation or a single boot, not confirmed durable across a real cold boot.
  `video/display_subsystem.md:488,533,548`.
- CT5 cluster-navigation questions: whether HMIC discovers the RHMI server via spoofable multicast,
  whether the inter-VM FSA/NFSA plane is reachable from an unprivileged app, and the exact
  maneuver-icon URI mechanism — all static-analysis-only, no live CT5 capture exists in the repo.
  `projection/cluster_navigation.md:38-76,161-187`.

## 5. Process / documentation integrity gaps
- Five research documents cited as authoritative sources **do not exist** in the repo
  (`DPS_MASTER_REFERENCE.md`, `MDI2_LINUX_MACOS_ANALYSIS.md`, `OPENSOURCE_ECU_RESET_ANALYSIS.md`,
  `EEPROM_CALIBRATION_MAPPING.md`, `SBI_SECURITY_SCOPE_ANALYSIS.md`) — claims resting on them are
  logged as "uncited pending verification."
  `research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md:197,257,750-754`.
- 14 research files were only regex tag-counted for the maturity ratings, never read by a human or
  agent — their listed "open questions" are themselves unvetted.
  `research/MATURITY_RATINGS.md:41-58`.
- `PROVENANCE_AUDIT_AUG2026.md` itself leaves 10 claims UNSUPPORTED/INFERRED, undermining whatever
  elsewhere in the corpus cites them. `research/provenance/PROVENANCE_AUDIT_AUG2026.md` (per
  `research/MATURITY_RATINGS.md:39`).
- A 2026-10-30 `[F]`/`[G]` claim batch never got the required second-agent cross-check.
  `VERIFICATION.md:205-211,296-300`.
- Stale/retracted wording left in place after a correction, in at least two spots: Y177
  "VIP_APP-only difference" text (`platform/firmware_versions.md:146,158`), and
  `fsa_protocol.md`'s "fully queryable" port claim that `VERIFICATION.md:176-181` already flagged
  NOT CONFIRMED.
- Several evidence-review scripts/tools never actually ran to completion: `reports/avb_audit.out`
  (Ghidra PyGhidra invocation failed, never re-run), `bench/ghs_probe/ghs_probe.c` (compiled
  nowhere, ioctl magics admitted guesses), `analysis-scripts/ghidra_rh850/step12_groups.py` (loop
  body is a stub).

## 6. Smaller/misc unresolved items
- USB ID `8087:09EF` recorded for both ELK and AAOS ADB — not disambiguated.
  `platform/elk_recovery.md:219`.
- Camera hardware disagreement: ACPI reports ADV7481, board inspection suggests TI DS90UB954.
  `elk_recovery.md:222`.
- `deviceid` last octet (`a0`) doesn't match the captured `wlan0` MAC (`9e`) in any Y175 capture —
  never re-checked live. `platform/ethernet_networking.md:213,367`;
  independently flagged again in `evidence/session-logs/restructure_2026-11-21_link_corrections.md:2646-2647`.
- E820 total RAM vs. GHS static guest grant vs. "normal AAOS" memory map — three-way discrepancy,
  explicitly called unresolved/unsourced in two independent places.
  `hardware/specs.md:96`, `evidence/session-logs/restructure_2026-11-21_link_corrections.md:2701-2702`.
- Manufacturer Enable Counter (MEC) — no identified increment/reset mechanism.
  `hardware/teardown.md:361`; also referenced from a DPS log with no explanation
  (`evidence/dps-logs/A11_CSM_x80.Txt:52`).
- `eMMC` capacity field is literally "TBD" in the hardware comparison table. `hardware/teardown.md:159`.
- Two board_map.json components logged only as `"QFP (unknown)"` / `"Unknown storage."`.
  `hardware/schematics/board_map/board_map.json:268,646`.
- DPS captures: module slots 29/51/53/54 read `Module ID 00000000` in two independent sessions —
  unclear if genuinely unpopulated or a read failure. `evidence/dps-logs/A11_CSM_x80.Txt:46-50`.
- `crypto_findings.json` has 1716 raw crypto-constant hits with essentially no narrative
  cross-reference analysis — unclear how many are real implementations vs. coincidental byte
  matches. `evidence/reports/crypto_findings.json`.

---

## Suggested next steps
1. Triage §2 and §3 first — they bear most directly on claims elsewhere in the repo (trust chain,
   security-access mechanics) and several have ready-made bench experiments proposed in the
   source docs themselves.
2. Resolve the §5 documentation-integrity gaps before trusting anything that cites the five
   missing files or the 14 unread docs.
3. The doc-vs-doc contradictions (eeprom.md vs teardown.md on the "871 refs" lead; the two VIP SBI
   docs; the video codec tables) are cheap to close — just re-read both sides and reconcile.
