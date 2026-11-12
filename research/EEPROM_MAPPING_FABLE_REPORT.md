# GM IOK / Harman INFO3.7-3.8 EEPROM Mapping — Consolidated Verification Report

**Date:** 2026-10-15
**Scope:** Cross-check of every address/field/spec claim in the EEPROM documentation against (1) the
firmware descriptor-table facts, (2) AUTOSAR R22-11 spec text, (3) community research, (4) today's
binary/CRC re-computation.
**Target:** GM IOK/Harman INFO3.7-3.8 CSM. ST M24C64 8KB I²C EEPROM (0x0000–0x1FFF), read by Renesas
RH850/F1K (R7F7015873AFP), VIP_APP firmware 86331656. ECUID `004B41DC0000160006104145610114AC`.

> This is a **verification/audit deliverable**, not a second EEPROM map. It cites the canonical
> documents by `file:line` and does not restate their content. The substantive defects it finds in
> §3 should be corrected **in place** in the canonical docs (per the repo's correction-in-place
> rule), not left to live only here.

**What I re-verified independently today (not taken on trust):**
- CRC-16/CCITT-FALSE recomputed in Python from the config-tool implementation
  (`eeprom/config_tool/eeprom_editor.py:543-554`): spec check value `"123456789"` → `0x29B1` (matches
  AUTOSAR `crc.txt:1147`); 0x1DC0 payload `0130000000016abb1116016abb12bb01` → **0xBFD4** (matches
  stored). CRC of the 0x16E0/0x1B40 version word (bytes `58 00` → 0x9A19; `00 58` → 0xC6F2) matches
  **neither** stored hash (0x9896 / 0xAD9B) — independently reconfirming the refutation in finding #3.
- Firmware string table `eeprom/config_tool/firmware_re/vip_app_strings.tsv` grepped directly.
- AUTOSAR citations grepped against `/tmp/autosar_dl/nvm.txt` and `/tmp/autosar_crc_txt/crc.txt`.

---

## 1. Address Map (every row carries a confidence level + a one-line evidence citation)

Confidence legend: **BYTE-MATCH** = stored bytes reproduced by independent computation or matched
against an external log; **STRUCT** = layout/role confirmed structurally but exact value not
byte-reproduced; **STRONG** = multiple corroborating sources, no byte-match; **UNRESOLVED** = algorithm,
coverage or meaning unknown; **REFUTED** = claim disproved by evidence.

| Address | Field | Confidence | Evidence (file:line / firmware offset) |
|---|---|---|---|
| **0x03A0–0x03B1** | ECU-ID, 16 bytes, framed by 0x69 | **BYTE-MATCH** | byte-exact vs SPSVCS.LOG `ECUID`; `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md:736`; ground-truth #6 |
| **0x0400 / 0x0420** | AUTOSAR `NVM_BLOCK_REDUNDANT` pair, copies=2, payload `1900e4a4`, 0x20 spacing | **STRUCT** | the *only* copies=2 descriptor entry (ground-truth #1/#4); `eeprom/EEPROM_Analysis_Report.md:549` |
| **0x0441** (markers 0x0440/0x0442) | Primary SBI data byte, 0xFF=bypass / 0x00=locked | **BYTE-MATCH (empirical)** | single-byte stock→stock_modified diff `0x0441: 00→FF`; `AUDIT:94`; ground-truth #5 |
| **0x0A81** (markers 0x0A80/0x0A82) | Backup SBI data byte, 0xFF=bypass | **STRUCT** | separate descriptor entry (not the 0x0400 REDUNDANT mech); `hardware/teardown.md:261`; `EEPROM_Analysis_Report.md:177`; ground-truth #5 |
| **0x0460–0x0465** | HW part number (`ssecuhn`), BE u32 `85086705` | **BYTE-MATCH** | vs SPSVCS.LOG `ssecuhn`; `AUDIT:713`, `AUDIT:737` |
| **0x0480** | second part-number-shaped BE u32 (`84999439`) | **UNRESOLVED** | not found in any source log; `AUDIT:714` |
| **0x0500** | MTC traceability-code tail (last 9 of 16-digit MTC) | **BYTE-MATCH** | digit-exact vs SPSVCS.LOG `mtc`/`infokey`; assembled in `eeprom_editor.py:580`; `EEPROM_Analysis_Report.md:52-57` |
| **0x0580** | Programming date (manufacture) | **STRONG** | dump read; `EEPROM_Analysis_Report.md:26` |
| **0x05A0–0x05AF** | CVPPS value `7310500000000X` | **BYTE-MATCH (value); UNRESOLVED (meaning)** | bytes read from dump; "Serial Number" vs teardown "Calibration file ID" conflict flagged `EEPROM_Analysis_Report.md:80-82` |
| **0x05C0–0x05D1** | VIN, 17 bytes | **BYTE-MATCH** | dump read + VIN decode; `EEPROM_Analysis_Report.md:19` |
| **0x0680–0x0689** | Shop/dealer code (`shopcode`, DID F198) `9999988888` | **BYTE-MATCH** | 10-char truncation of logged 11-digit value; `AUDIT:738` |
| **0x06A0–0x06A5** | Reprogram date (DID F199, BCD `2026-09-28`) | **STRONG** | post-dates latest logged SPS session (`progdate 20260707`); `AUDIT:739`; decoder `eeprom_editor.py:525-540` |
| **0x06E0–0x06E5** | HW part-number word `60 02 02 B1` | **BYTE-MATCH** | vs VIP boot-log "Send HW Partnum 0x60 0x2 0x2 0xb1"; `AUDIT:740` |
| **0x0B40 / 0x0B41** | "Debug mode" flag | **UNRESOLVED** | §2.1 table still labels it `[C]` (`AUDIT:677`) but §0 calls it "1/5 of a scrambled composite value, not a boolean flag" (`AUDIT:43`); teardown "effect not directly verified…possibly a third SBI mirror" (`teardown.md:273`) — contested |
| **0x0E00–0x0E7F** | display/UI timing params | **UNRESOLVED** | inferred from dump; last 7 of 34 fields byte-match power/thermal cal constants @fw 0xf8126-0xf8141; early field-name guesses unconfirmed, ≥1 tested wrong (`AUDIT:951-960`) |
| **0x0F00 / 0x0F40 / 0x0F80** | brightness LUTs + color/ambient cal | **STRONG** | table-level, read from dump; `EEPROM_Analysis_Report.md:276-314` |
| **0x0FE0–0x12DF** | Backlight/display-dimming curves (4 channels, shared input-% axis) | **STRONG (structural)** | matched to VIP_APP LUT defaults @fw 0xf8414-0xf8500, *different numeric encoding — not byte-identical*; `AUDIT:651`, `AUDIT:715-717`. NOT audio (prior "Volume/Fade/EQ" labels refuted) |
| **0x14A0** | VIN-tail residual (NOT a firmware ID) | **STRONG** | cross-session SPS match on one ECUID; state varies live/stale/blank across 3 dumps; `EEPROM_Analysis_Report.md:29-50`, `AUDIT:524-528` |
| **0x16E0 / 0x19E0 / 0x1B40** | `[marker][00][version word][hash word][marker]` | **STRUCT (layout); UNRESOLVED (algorithm + coverage)** | structure confirmed `UNDOCUMENTED_FLAGS:698-714`; algorithm NOT CRC of version word alone — recomputed today; ground-truth #3 |
| **0x1A80** | "Config CRC" vs "MEC NVM value" | **UNRESOLVED** | interpretation conflict explicitly flagged `EEPROM_Analysis_Report.md:78-80`; values even differ by dump (0x0107 vs 0x0167) |
| **0x1B60 / 0x1B80** | "Block CRC" vs "reflash/programming counters" | **UNRESOLVED** | interpretation conflict flagged `EEPROM_Analysis_Report.md:79`; teardown `teardown.md:766` |
| **0x1DC0–0x1DD3** | 2× 32-bit timestamp-shaped fields + CRC-16/CCITT-FALSE over preceding 16 bytes | **BYTE-MATCH (CRC only)** | stored `0xBFD4` = computed `0xBFD4`, reproduced today across 5 images; `AUDIT:770`. The Δ between the two timestamp fields is NOT fixed (11–13799 s across images); `AUDIT:549-554` |
| **0x0060–0x0397** | 822-byte record that a descriptor says is all-zero, but reads as a 9-bit-period "walking-zero" pattern | **UNRESOLVED** | read-glitch vs cell fault undetermined; re-dump recommended; `AUDIT:562-565` |
| ~~0x04A0 / 0x04C0~~ | ~~"IPC Security Config"~~ | **REFUTED** | `[IPC_S]` is the serial-transport HDLC log tag, not "IPC Security"; "17/11 refs" fabricated; `AUDIT:32-37`, `AUDIT:678-679` |
| ~~0x0A40 / 0x0BE0~~ | ~~"feature/late-region flags"~~ | **REFUTED** | read 0xFF (unwritten) in both stock and ADB_enabled dumps; ref-counts fabricated; `AUDIT:648`, `AUDIT:680-681` |
| ~~0x1A00~~ | ~~"Tertiary Security"~~ | **REFUTED** | no code evidence it is a security byte; `AUDIT:682` |

**Descriptor table (firmware, not EEPROM):** 183 entries at VIP_APP 0x2475A–0x24FEE, 12-byte stride
`[u32 LE rel_addr][u16 LE len][u8 0x01][u8 copies][u32 0]`; all type=0x01; exactly one copies=2
(→0x0400/0x0420); all rel_addr high words 0x0000 (ground-truth #1). This is the structure described
in `AUDIT:572-608`.

---

## 2. AUTOSAR Conformance — what is standard vs vendor vs unknown-origin

Every spec citation below was checked against the downloaded spec text.

**Standard AUTOSAR NvM behaviour (conformant):**
- **Block management types** `NVM_BLOCK_NATIVE / REDUNDANT / DATASET` — `nvm.txt:1412-1414`
  (ECUC_NvM_00062 is a real SWS item, `nvm.txt:7598`). The 0x0400/0x0420 pair maps to
  `NVM_BLOCK_REDUNDANT` / `NvMNvBlockNum=2`, which is the standard "two copies kept in sync, backup
  used on read failure" feature.
- **NvMNvBlockNum (ECUC_NvM_00480)** — spec text verbatim `nvm.txt:7929-7940`: "1-255 … NVM_BLOCK_
  DATASET … 1 … NVM_BLOCK_NATIVE … 2 … NVM_BLOCK_REDUNDANT." This exactly matches the docs' mapping.
- **CRC-16/CCITT-FALSE** — poly 0x1021 (`crc.txt:1772`), Table 7.5 (`crc.txt:1150`), check value
  `0x29B1` (`crc.txt:1147`). Confirmed as the 0x1DC0 algorithm by byte-match.

**Vendor-specific (NOT defined by AUTOSAR):**
- **The 12-byte `(u32,u16,u8,u8,u32)` descriptor layout.** AUTOSAR specifies configuration
  *parameters*, not a C struct; `NvM_BlockDescriptorType` is implementation-defined. The docs state
  this correctly (`AUDIT:600-604`).
- **`type_byte = 0x01`** — invariant across all 183 entries, including copies=2 entries, so it cannot
  carry the management type. Vendor format-version/valid flag. Correctly stated (`AUDIT:583`).
- **`[marker][payload][marker]` record framing** (0x69/0xF0/0x5A/0xC3). AUTOSAR NvM defines only an
  optional *Static Block ID* header placed first in the block (SWS_NvM_00522, `nvm.txt:1389-1390`) and
  an optional appended CRC — never leading+trailing markers. This belongs to the Fee/Ea layer or is
  Harman-custom. Correctly stated (`AUDIT:605-608`).
- **SBI 0x00/0xFF polarity** — a cross-platform RH850 convention (Nissan Leaf CVE-2025-32058), not
  Harman-specific. Correctly stated (`AUDIT:625-631`).

**Unknown origin (explicitly NOT an AUTOSAR NvM construct):**
- **The 0x16E0/0x19E0/0x1B40 separate integrity block** — an integrity word at a *different address*
  from its payload, carrying its own version/generation counter. AUTOSAR NvM appends the CRC to the
  *same* NV slot (SWS_NvM_00522 / Figure 7.5); the Fee/Ea SWSs do not define this either. Origin
  undetermined — vendor Fee/Ea bookkeeping or an application-level SWC. Correctly stated
  (`AUDIT:766`, `UNDOCUMENTED_FLAGS:731-735`).

**Ambiguities the docs should flag more sharply:**
- **`copies` is not a *sole* discriminator.** `nvm.txt:7929-7940` shows DATASET spans 1-255, so
  `copies=2` is consistent with REDUNDANT **or** a 2-dataset DATASET block; disambiguation needs
  `NvMBlockManagementType`, which is **not** in the 12-byte descriptor. The docs' phrase "copies … is
  **the actual management-type discriminator**" (`AUDIT:584`, `AUDIT:598`) slightly overstates this.
- **rel_addr vs NvMNvBlockBaseNumber.** AUTOSAR's `NvMNvBlockBaseNumber` (ECUC_NvM_00478) is a *block
  number*, and the EA/FEE mapping is `FEE/EA_BLOCK_NUMBER = (NvMNvBlockBaseNumber << NvMDatasetSelection
  Bits) + DataIndex` (`nvm.txt:1235-1236`) — a *number* formula, not a byte-address formula. With 2
  selection bits the base-number range is `0x1..0x3FFE` (`nvm.txt:1241`). Whether the firmware's
  `rel_addr` stores a base number or a pre-computed byte offset is an implementation question AUTOSAR
  does not answer. The docs hedge this correctly (`AUDIT:581`).
- The "2-byte header" width is an inference from `NvM_BlockIdType` being uint16, **not** spec text —
  SWS_NvM_00522 names the header but gives no byte width (`nvm.txt:1389-1390`, `nvm.txt:2614-2618`).
  The docs state this correctly (`AUDIT:620`).

**Firmware-string evidence for the AUTOSAR stack (verified in `vip_app_strings.tsv`):**
- `Rte_Pim_PLC_BootCounter_PIM` is present (`vip_app_strings.tsv:90`) — a genuine AUTOSAR RTE-generated
  Per-Instance-Memory accessor name. Strong evidence of an AUTOSAR CP stack.
- **No `NvM_` / `Fee_` / `Ea_` / `Dem_` / `EcuM_` API-prefixed symbols appear.** The 45 "nvm" hits are
  all log-message words (`[INT_DID] … NvM ReadError Status`, `Nvm_ErrorStatus`, mixed-case) — not
  AUTOSAR API symbols. Caveat: the table is a 120-line Ghidra xref export, not a full strings dump, so
  absence is suggestive, not conclusive. The write-trace states this correctly
  (`VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md:91-92`).

---

## 3. Claims still overstated, under-sourced, or inconsistent (exact `file:line`)

Ordered by impact. Items **A** and **B** are the ones I'd fix first; both are bench-actionable errors.

### A. **Backup-SBI byte: the "CONFIRMED ADB RECIPE" names the wrong offset (`0x0A80` not `0x0A81`).**
The framing is `[marker 0x0A80][data 0x0A81][marker 0x0A82]`, exactly parallel to the primary
`[0x0440][0x0441][0x0442]`. The data byte is **0x0A81**. This is stated correctly by ground-truth #5
and by:
- `hardware/teardown.md:261` ("0x0A81 … Mirror"),
- `eeprom/EEPROM_Analysis_Report.md:177` ("the data byte at offset+1 (0x0441/0x0A81)") and `:551`,
- `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md:620` / §0.16 ("0x0441/0x0A81"),
- `AUDIT:867` (§5.2: "Flip 0x0A81 to 0xFF (backup SBI data byte)"),
- GM_research `…/hardware/EEPROM/EEPROM_Analysis_Report.md:191,599`.

But the **"CONFIRMED ADB RECIPE"** at `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md:156-161` says *"set
`0x0441 = 0xFF` AND `0x0A80 = 0xFF` — the two SBI data bytes"* and adds *"Y181 initializes `0x0A80`
to a non-FF value, so on Y181 both bytes must be set."* Per the same doc's own §13.6
(`UNDOCUMENTED_FLAGS:694`), Y181 backup reads `F0 00 F0`: marker `F0`@0x0A80, **data `00`@0x0A81**.
So on Y181 the byte that is non-FF and must become 0xFF is **0x0A81**, not 0x0A80 — flipping 0x0A80
would set a marker and leave the data byte locked. The recipe is internally inconsistent with §0.16,
§5.2, §13.6 and ground-truth. The §2.1 table row (`AUDIT:676`) and §0.14 inherit the same loose
"0x0A80" label. **This is the single most important correction** — it is the one that governs a
physical flip.

### B. **GM_research `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` §15.2 miscites the SBI pair as the REDUNDANT block.**
`/Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/hardware/EEPROM/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`
§15.2 says: *"Entries with `copies=02` are `NVM_BLOCK_REDUNDANT` … e.g. the Primary/Backup SBI pair at
0x0440 / 0x0A80."* This contradicts ground-truth #4/#5 (the **only** copies=2 entry maps to
0x0400/0x0420; the SBI pair is two *separate* entries) and contradicts its own sibling file
`…/EEPROM_Analysis_Report.md:598-599` and the canonical `AUDIT:615-616`. The SBI pair is an
application-level mirror, not an AUTOSAR REDUNDANT block. Factual error.

### C. **`csm_eeprom/icloud_eeprom/EEPROM_Analysis_Report.md` is a partially-stale parallel copy.**
Today's corrections were propagated to its CRC and redundancy sections but **not** to its memory map /
calibration sections. Stale claims that were refuted today still read as live:
- `:33` `| Firmware ID | … | 0x14A0 |` (should be VIN-tail residual),
- `:59` `0x0460-0x04FF │ Radio/Audio Settings` (0x0460 is the `ssecuhn` HW part number),
- `:81-85` "Audio Volume Curve / Audio Fade-Balance / Audio EQ-DSP Calibration" (all backlight dimming),
- `:268` "Audio Calibration Tables", `:287` "Audio EQ/DSP Bands".
It also carries an **un-redacted VIN tail** at `:33` where the gminfo copy uses `XXXXXXXX A`. Per the
repo's correction-in-place rule this file should be folded into / re-synced with the canonical map,
not left as a stale sibling.

### D. **`diagnostics/gm_dps/docs/EEPROM_CALIBRATION_MAPPING.md` — Audio labels not propagated.**
CRC section (§4.9, `:239-262`) is correctly updated (0x1DC0 confirmed, 0x16E0/19E0/1B40 unverified),
but the map still says "AUDIO CALIBRATION TABLES … [CRC Protected]" (`:106`), §4.8 "Audio Calibration
(0x1100-0x12DF)" (`:227`), and `:400/:422/:434`. Same unpropagated Audio→Backlight correction as C.
The "[CRC Protected]" tag on that region is also now unsupported (coverage of 0x16E0/19E0/1B40 is
unknown).

### E. **`MEC` is expanded three different ways across the trees.** [FIXED 2026-10-15]

> Standardized to **Manufacturer Enable Counter** across both trees (`platform/security.md`,
> `.../emu/y181_ref/security.md`, `hardware/teardown.md`, `.../ref_repo/teardown.md`), the reading
> with the strongest evidence trail (GDS2/AllData factory procedure; decompiled SoC class
> `ManufacturerEnableCounter`/`DiagnosticDataID.MANUFACTURER_ENABLE_COUNTER`; HIDL
> `IDiagnosticsObd::getManufacturingEnableCounter()`). "Module Event Counter" and "Reprogramming
> event count" are now flagged in place as unverified alternate readings rather than silently
> dropped. The DID `0xF1A0`/`vip_app_strings.tsv` gap noted below is now called out as a caveat at
> every place the chain is asserted without independent live-vehicle corroboration
> (`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0.10-0.14, the `icloud_eeprom/EEPROM_Analysis_Report.md`
> SUPERSEDED banner) — left untouched in `platform/security.md`'s ProtoKey/ADB section and
> `emu/y181_ref/diag/real_did_values.md`, which already cite an independent live on-vehicle
> `$22 F1A0` read (`dps_readx80.Txt`) as separate corroboration for that specific DID.

- `AUDIT:370` / §0.10-0.14: **"Manufacturer Enable Counter"**, manufacturing-mode relaxation, DID 0xF1A0.
- `…/emu/y181_ref/security.md:127-135`: **"Module Event Counter"**, tracks consecutive SoC boot
  failures, disables recovery at MEC≥3.
- `hardware/teardown.md:478`: **"Reprogramming event count"**.
These are different acronym expansions *and* different described mechanisms. The whole SBI→ADB chain in
§0.10-0.14 depends on the "Manufacturer Enable Counter ∈[1,255]→bypass" reading; the security.md
"boot-failure counter" reading is a separate mechanism. Note also that **DID `0xF1A0` does not appear
in `vip_app_strings.tsv`** (the extracted INT_DID list runs F0F3/F0F4/F190/F198/F199/F1CB/F1CC/F1DB/
F1DC/F0AB/41EB/4782/4787/F09A/F0B4 — not F1A0), so the "0xF1A0 = MANUFACTURER_ENABLE_COUNTER" binding
rests on the boot logs cited in §0.14, not on this firmware export. Reconcile the expansion.

### F. **GM_research aaos `EEPROM_Analysis_Report.md:652` (References) overstates the CRC finding.**
It calls CRC-16/CCITT-FALSE the *"Basis for the 0x16E0/0x19E0/0x1B40 hash-word algorithm
identification"* — but the same file's body (`:452-458`) correctly marks those three UNVERIFIED. The
References line should be softened to match the body (the icloud copy's References `:521` already does
this correctly; use it as the template).

### G. **Minor — endianness label drift for the version word.**
`AUDIT:772` / §2.6 and ground-truth call the shared 0x16E0/0x1B40 version word **`0x5800`**;
`UNDOCUMENTED_FLAGS:711` calls it **`0x0058`**. Same bytes (`00 58`), opposite endianness label. The
structural conclusion (0x16E0 and 0x1B40 share it, 0x19E0 differs) holds either way, but the two labels
should be unified to avoid a reader mis-deriving the CRC input.

### H. **Minor — V850 vs RH850 symbol drift in the write-trace.**
`VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md` names the getter `0xc8db6` and table `0x4fba4` from a
**V850** pass (`:151-157`), whereas the RH850 passes in `AUDIT:58` name `FUN_000C8F6A` / table `0x4FB8C`.
The trace flags itself as a V850 approximation, so this is disclosed, but the resulting addresses differ
by a few bytes and should not be cited as if cross-validated. The trace's §7 "working synthesis" that
the SBI mirror-pair is "part of the NvM CRC/validity check (two copies must agree)" (`:114-117`) leans
toward the same conflation as item B; it is hedged as "inference, not confirmed," which is acceptable,
but it should explicitly note ground-truth #5 (SBI pair ≠ REDUNDANT mechanism).

**Clean / no overclaim found (positive results):**
- The 0x1DC0 CRC claim is correct and byte-reproducible (recomputed today).
- The 0x16E0/19E0/1B40 "algorithm UNRESOLVED" correction landed consistently in the canonical AUDIT
  (§2.6, §5, §7, §0.15), `eeprom/EEPROM_Analysis_Report.md:427-444`, `UNDOCUMENTED_FLAGS:716-729`, and
  both GM_research `…/hardware/EEPROM/EEPROM_Analysis_Report.md:452-458` bodies and
  `EEPROM_CALIBRATION_MAPPING.md:256-262`. No surviving "RESOLVED/CONFIRMED" overclaim for these three
  addresses anywhere in either tree (only the References-line softening in item F).
- The Melching block-ID hypothesis is marked REFUTED everywhere it appears, consistent with the all-zero
  high-word evidence.
- The AUTOSAR descriptor-mapping corrections (`type_byte` invariant, no numeric management-type values,
  no C struct in spec) are spec-accurate and consistent across the canonical AUDIT §0.16 and GM_research
  aaos §15.1.
- The 0x0441/0x0A81 = ADB-bypass empirical finding, the ECU-ID byte-exact match, and the SBI 0x00/0xFF
  RH850 convention are all well-sourced and consistent.

---

## 4. Highest-priority open question

**The coverage range and algorithm of the 0x16E0 / 0x19E0 / 0x1B40 integrity blocks are UNKNOWN, and
this is the one unresolved item that blocks safe editing of anything these blocks protect.**

Precisely: each block decodes as `[marker][00][2-byte version/generation word][2-byte hash word][marker]`
(STRUCT-confirmed). The hash word is **proven not to be CRC-16/CCITT-FALSE of the version word alone**:
0x16E0 and 0x1B40 carry the *same* version word (`0x5800` / bytes `00 58`) but *different* hash words
(0x9896 vs 0xAD9B) — a single CRC input cannot yield two outputs. I reconfirmed today that CRC-16/
CCITT-FALSE of that version word (`0x9A19` or `0xC6F2` depending on byte order) equals neither stored
hash. Therefore:
1. The **input byte range** each hash covers is undetermined (it is clearly *not* just the 2-byte
   version word; candidates are a preceding data region, the whole EEPROM, or a per-block payload).
2. The **algorithm** is unverified (CRC-16/CCITT-FALSE is only a *candidate* by analogy to 0x1DC0, the
   one block where it is byte-confirmed).
3. The **version/generation word** semantics (observed to cluster tightly across blocks, ±1 drift, and
   to step 0x0013→0x0104 across a reflash) are a plausible calibration-generation counter but not pinned.

Until the coverage range is recovered (candidate method: brute-force CRC-16 input ranges against ≥2
images that share a version word but differ in data, then confirm the window that reproduces both
hashes), **any edit to a region potentially under 0x16E0/0x19E0/0x1B40 cannot have its integrity field
recomputed**, and the only safe path remains template-preservation (edit a known-good dump, touch only
the SBI data bytes, leave these three fields byte-for-byte as shipped — which is empirically known to
work for the single-byte 0x0441 flip).

---

## 5. Caveats on this verification

- I did **not** re-run Ghidra/radare2 against the 1.93 MB VIP_APP image; the 183-entry descriptor table,
  the 0x2475A–0x24FEE offsets, and the copies=2 mapping are taken from the stated binary verification
  (ground-truth #1-#6). I re-verified the two things cheaply checkable and load-bearing: the CRC math
  and the firmware string table.
- `/Volumes/stuff/...` (GM_research tree) was mounted and readable; `EEPROM_CALIBRATION_MAPPING.md`
  lives at `diagnostics/gm_dps/docs/`, not the `…/2024_Silverado_ICE/diagnostics/gm_dps/docs/` path in
  the brief.
- Raw VIN/serial values present in the GM_research copies were deliberately not reproduced here.
