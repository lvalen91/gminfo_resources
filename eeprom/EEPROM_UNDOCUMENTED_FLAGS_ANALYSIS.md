# EEPROM Undocumented Flags — Retired

**Status (2026-11-21): retired.** This file's "10 potentially undocumented flags" analysis
(Jan-Feb 2026, based on a string-proximity firmware-reference count) is superseded. A real Ghidra
decompilation pass found the actual EEPROM-access mechanism and checked every candidate against
it directly: three of the four security-region candidates (`0x04A0`, `0x0A40`, `0x0BE0`) have zero
real code references and read `0xFF` (unwritten) in both stock and ADB-enabled dumps; the fourth
(`0x04C0`) is touched by a real CalGroup handler but the EEPROM cell itself is still empty. The
"base address" framing for `0x0A00`/`0x0B00` and the retracted calibration-file/stub-validator
hypotheses are likewise superseded.

**Live conclusions now live in:**
- [`research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
  §2 (the SBI/ADB-bypass mechanism, settled), §5.2/§5.4 (security-region address table, including
  the retracted candidates), §5.8 (remaining untested offsets), §12 (History)
- [`VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`](VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md) — the
  Ghidra pass that retracted the candidate-flag framing

**Historical appendix:** the marker-rotation raw data (marker transition map, observed marker
samples, CRC version-counter samples, USB update-package manifest), a handful of VIP `$27`/ICUSB
subroutine addresses with no other home in this corpus, and the full correction/provenance trail
(what this file originally claimed vs. what replaced each claim, with dates and sources) are
preserved in
[`research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §13](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md#13-historical-appendix-retired-eeprom_undocumented_flags_analysismd-folded-in-2026-11-21).

Do not cite this file for live conclusions about EEPROM security flags; cite the two docs above.
