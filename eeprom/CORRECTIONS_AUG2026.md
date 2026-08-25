# EEPROM Map / Editor Corrections — Aug 2026

Source: `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md` and
`VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` (real Ghidra decompilation of
`vip_app.bin`/`vip_boot.bin`/`86331656`, not string-count inference).

## Artifacts updated

1. **`GM_research/.../hardware/EEPROM/create_eeprom_map.py`** (generator
   script, source of truth) → regenerated
   **`VIP_Renesas_EEPROM_Map.xlsx`** in the same directory.
   - Also fixed a stale hardcoded save path (`~/Downloads/GM_research/...`,
     a location that no longer matches this corpus's layout) — now saves
     next to the script.
2. **`eeprom_editor.py`** (local web UI for editing EEPROM dumps) — synced
   identically to both copies in the corpus
   (`gminfo_resources/eeprom/config_tool/` and
   `GM_research/.../hardware/EEPROM/config_tool/`).

## What changed and why

| Address | Old claim | New, evidence-backed status |
|---|---|---|
| `0x0440`/`0x0441` (Primary SBI) | "ADB security flag" | **Confirmed broader than ADB** — field-captured CAN `$27` traffic (already in the corpus) shows the same degenerate seed on the VIP's plain diagnostic UDS stack, not just ADB/ICUSB. Storage location confirmed via real decompilation (CalGroup `0x3b`, `FUN_ram_00091938`). |
| `0x0A80`/`0x0A81` (Backup SBI) | "Both SBIs must match for the bypass to hold" | **That specific claim is unverified and likely wrong as stated** — exhaustive static analysis found *zero* code references to these addresses in either VIP binary. The empirical bypass-works observation isn't in question; the claimed mechanism is. |
| `0x04A0` | "Undocumented, 17 refs, security region" | **Closed** — zero real code references found; the one apparent hit is a confirmed false positive. |
| `0x04C0` | "Undocumented, 11 refs, security region" | **Upgraded to confirmed real** — genuine CalGroup `0x44` handler found (`FUN_ram_00091f82`), structurally parallel to the SBI block but administratively separate. What it gates is still unknown — now a real lead, not a guess. |
| `0x0A40` | "Undocumented, 28 refs" | **Closed** — zero real code references found. |
| `0x0BE0` | "Undocumented, 24 refs" | **Closed** — zero real code references found. |

## Why the "N refs" framing changed

The original notes (`EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`) counted string
occurrences near these addresses in raw firmware strings dumps — a proxy
signal, not a functional one. The Aug 2026 pass instead found the *real*
code mechanism (a single generic "CalGroup cell" accessor,
`FUN_ram_000c8db6`, 1,301 call sites / 170 handler functions / 1,050
distinct cell IDs across the binary) and checked every target address
against it directly, plus an independent full-instruction literal-operand
scan. Three of the four "undocumented" candidates turned out to have no
real reference at all; the fourth (`0x04C0`) is real.

## Still open (not fixed by this pass — don't treat as resolved)

- What calls the SBI handler (`FUN_ram_00091938`) and the seed/key state
  machine (`FUN_ram_000b67d0`) — both reached only via unresolved indirect
  calls. This is the single piece of evidence that would fully close the
  "does it affect calibration-programming specifically" question.
- What mechanism (if any) actually backs `0x0A80`/`0x0A81`'s empirically-observed
  effect, given no code reference was found.
- What `0x04C0` actually gates.

Full technical detail, decompiled evidence, and confidence markers for every
claim: `VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md`,
`VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`.
