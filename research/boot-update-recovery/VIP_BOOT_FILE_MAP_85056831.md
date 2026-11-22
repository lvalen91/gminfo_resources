# VIP_BOOT File Map `85056831`

## Scope
Structural map of the Renesas RH850/F1K `VIP_BOOT` bootloader (part `85056831`, byte-identical
across Y175/Y177/Y181B — see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`): memory-block layout,
function-density distribution, and the concretely-identified integrity-check routines (the
"Harman checksum" and "Message digest" mechanisms named in `GM_INFO37_BOOT_CHAIN_ANALYSIS.md`
§10.1 and `BOOT_CHAIN_ANALYSIS.txt` §9, but not previously located to specific addresses). Pure
reference — does not restate boot-chain ordering (`GM_INFO37_BOOT_CHAIN_ANALYSIS.md`), the
VIP_APP calibration/SBA-ticket logic (`VIP_APP_FILE_MAP_85759599.md`), or RH850 hardware facts
(`hardware/module/vip_mcu.md`).

## Evidence legend
`[C]` confirmed via live Ghidra REST query against the project's existing (pre-analyzed) program
database · `[D]` confirmed via decompilation of the function body · `[U]` unverified / open
question. Unless noted otherwise, every address/size below is `[C]`, re-derived directly from
`evidence/ghidra-projects/vipboot_rh850` (program `VIP_BOOT_85056831`) via three independent
agent passes over disjoint function-index ranges (lowest third: index 0–1063, middle third:
1064–2127, top third: 2128–3192 of 3193 total), each re-verified for sort order and address-range
continuity.

**Methodology caveat:** one pass found the Ghidra REST backend can return mismatched
function-detail responses under concurrent requests; that pass re-verified every response's
returned address against its requested address and found no mismatches in its own data, but the
other two passes did not report doing the same check. Treat row-level details from the middle and
top thirds as `[C]` with a small residual risk of an occasional swapped entry, not re-verified
byte-for-byte here.

## Related
`GM_INFO37_BOOT_CHAIN_ANALYSIS.md` (boot-chain ordering, §10.1 Security Layer Summary — the
source of the "Harman checksum" / "Message digest" naming this doc resolves to addresses),
`BOOT_CHAIN_ANALYSIS.txt` (earlier, string-evidence-only pass on the same two mechanisms, rated
Mixed/leans-speculative — this doc supersedes its §9/§10 address-level claims with live-verified
function identification), `VIP_APP_FILE_MAP_85759599.md` (the application firmware this
bootloader hands off to), `../../hardware/module/vip_mcu.md` (RH850 silicon memory map),
`../../platform/vip_ipc_ghs.md` (VIP role in the dual-processor architecture).

## Module identity
USB delivery-package file `85056831` (`…/Y175/USB_Files/85056831` and the byte-identical
Y181B copy), 1,934,214 B container; unwrapped program `VIP_BOOT_85056831`: RH850:LE:32,
processor variant `Zeekr-RH850`, image base `0x00000000`, address range `0x00000000`–`0x001d8385`,
**3,193 functions**, SHA-256 `2792ac3a4e7d9d0a509cb283c43a0b70af2181208f5d2e8191ae693fc27f746b`
(matches the pinned reference hash cited in `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`).

## Memory layout

| Segment | Range | Size | Initialized | Notes |
|---|---|---|---|---|
| `ram` | `0x00000000`–`0x000224ff` | 140,544 B | yes | Reset vector, early boot, HDLC CRC/comms framing (functions below `0x1674b` traced here) |
| `ram.split` | `0x00022500`–`0x000684ff` | 286,720 B | **no** | Gap — no functions defined |
| `ram.split.split` | `0x00068500`–`0x0008a37f` | 138,880 B | yes | Dense code region: HDLC dispatch, SHA-256 implementation, main bootloader logic |
| `ram.split.split.split` | `0x0008a380`–`0x001d8385` | 1,368,070 B | **no** | Overwhelmingly sparse — handful of isolated 1-byte stub functions scattered up to `0x1bdac2`, consistent with "uninitialized" |

**Function density:** of 3,193 total functions, the overwhelming majority sit in
`0x00000000`–`0x0008ac82` (the two initialized segments); above `0x0008ac82` only a handful of
degenerate 1-byte stubs exist (`0x0008ac82`, `0x000d9e00`, `0x00122b36`, `0x001871d0`,
`0x0019b23c`, `0x001bdac2`) — Ghidra function markers in uninitialized/unmapped memory, not real
code.

## Integrity-check routines — located and function-identified

Per `GM_INFO37_BOOT_CHAIN_ANALYSIS.md` §10.1, `VIP_BOOT`'s security layer is listed only as
"Harman checksum," with the exact mechanism `Requires RE`. The retired `BOOT_CHAIN_ANALYSIS.txt`
had found the *strings* (`"Harman checksum is valid."`, `"Message digest is valid."`,
`actSHA256_SPEED_UP`) via static string extraction, but had not traced them to functions. This
pass does:

### SHA-256 implementation — confirmed real, not just advertised

| Function | Address | Size | Role |
|---|---|---|---|
| `FUN_000855a0` | `0x000855a0`–`0x0008598b` | 1,004 B | **SHA-256 compression round.** `[D]` Decompiled and verified: loads 8 32-bit state words and 16 big-endian message words, computes `Ch(e,f,g) = (e&f)^(~e&g)`, `Maj`, and the exact SHA-256 Σ1(e)=rotr(6,11,25) / Σ0(a)=rotr(2,13,22) rotation set, adds a round constant from a table at `0x00002878`, folds state back. This is a genuine SHA-256 block-compression function, not a lookalike. |
| `FUN_000859a4` | `0x000859a4`–`0x000859ab` | 8 B (thunk-sized wrapper into a larger absorb routine) | **SHA-256 Update/absorb.** `[D]` Maintains a 64-byte block buffer and a bit-length counter (context fields at `+0x20`/`+0x24`/`+0x28`), fills/flushes partial blocks, calls `FUN_000855a0` per full block — a standard streaming-hash update. |
| `FUN_000850d8`, `FUN_000852d8`, `FUN_00085492`, `FUN_00085e06` | `0x000850d8`, `0x000852d8`, `0x00085492`, `0x00085e06` | 30 B, 442 B, 122 B, 36 B | Supporting cluster in the same hash-context layout — `[U]` lower confidence on exact role (init/pad/finalize/copy plumbing around the two functions above), not individually decompile-verified. |

**Conclusion:** the "Message digest" check named in the boot-chain doc is a real, correctly-implemented SHA-256 — not a weak or fake hash. This narrows (but does not close) the open question from `GM_INFO37_BOOT_CHAIN_ANALYSIS.md` §10.1: the digest algorithm itself is confirmed sound; what it is computed *over* (all of `VIP_APP`? a signed header only?) and whether a mismatch actually halts the boot are still `[U]`, unestablished by this pass.

### HDLC CRC function identification — retracted (2026-11-22)

A prior pass in this doc identified `FUN_0001ea56`/`FUN_0001974c` as the HDLC frame-CRC
check behind the `"HDLC: CRC Failed 0x%X Last RSeq:%d"` string, based on address proximity
to that string (`0x1ea5`). Independent re-verification (decompile + `/xrefs_to`) does not
support this:

| Function | Address | Size | Actual role `[D]` |
|---|---|---|---|
| `FUN_0001ea56` | `0x0001ea56` | 1 B listed (Ghidra non-contiguous-body artifact) | Generic two-buffer byte comparison (`int FUN_0001ea56(byte*,byte*)`) — no xref to the CRC-Failed string |
| `FUN_0001974c` | `0x0001974c`–`0x0001979d` | 82 B | String-table lookup loop; calls `FUN_0001ea56` and `FUN_00009e06`; no CRC/logging role found |

`FUN_00000362` (`0x00000362`–`0x000005bd`, 480 B) and `FUN_000003da`
(`0x000003da`–`0x00000451`, 120 B), both near the reset-vector region, also have no
confirmed xref to the CRC string. **The function that actually logs `"HDLC: CRC Failed"`
is not identified in this pass.** The architectural claim (HDLC CRC protects the VIP↔SoC
serial transport per `vip_ipc_ghs.md`'s `/dev/ttyS1` link, separate from firmware/boot
integrity) is unaffected — that's established by the string's own content, not by this
function identification — but no specific address should be cited for it until re-traced.

### "Harman checksum" itself — still not isolated to a function

Unlike the SHA-256 pair, no function in any of the three passes was confidently identified as
the "Harman checksum" (as distinct from the SHA-256 digest) implementation. Two candidate
call sites containing the `"CRC Failed"` string reference (`FUN_000003da`, `FUN_00000362`,
both near the reset-vector region `0x362`–`0x451`) were examined and explicitly **not**
confirmed as a clean implementation — both are flagged by Ghidra as mis-analyzed
overlapping-jumptable stubs, so their decompilation is unreliable. **Open item carried forward
for future work:** isolate the "Harman checksum" (proprietary algorithm, per
`BOOT_CHAIN_ANALYSIS.txt` §10.1) as a function distinct from the now-confirmed SHA-256 pair —
it may be a separate lightweight pre-check, or the "Harman checksum" and "Message digest" labels
may both refer to stages of the same SHA-256-based routine with a naming overlap in the original
strings; this pass could not disambiguate that.

### SBA-ticket check — present here too, same family as `VIP_APP`

The live VIP boot log (`evidence/enumeration/Y175/Y175_VIP.log`) shows
`"SbaTicketValidation validation failed: 0x0"` during normal boot. Per `BOOT_CHAIN_ANALYSIS.txt`'s
exploitation table, this check "fails gracefully (`0x0`)" and "may not block boot" — consistent
with the same optional SBA-ticket exception mechanism documented in `VIP_APP` (see
`VIP_APP_FILE_MAP_85759599.md` and `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`). This pass did
not attempt to locate the ticket-check function within `VIP_BOOT` specifically — open for
follow-up.

## Candidates examined and cleared (not integrity-related)

- `FUN_000087ca` (`0x000087ca`, 812 B) — signature looked checksum-shaped; decompiles to a
  digital-I/O port bit-set/clear control routine. Not a CRC/integrity routine.
- `FUN_000144d4` (`0x000144d4`, 808 B) — flagged by an "error"-string string-match; decompiles to
  a buffer/descriptor-table initializer. Not integrity-related.

## Provenance
Live Ghidra REST queries (`/functions`, `/function`, `/decompile_function`, `/strings`,
`/xrefs_to`, `/read_memory`) against a headless-loaded instance of the existing
`evidence/ghidra-projects/vipboot_rh850` project (program `VIP_BOOT_85056831`), three
independent passes over disjoint function-index thirds, 2026-11-21. Full per-function
raw tables (3,193 rows, address/size/name/signature) were produced by each pass but are not
reproduced in full here, per this repo's convention that the Ghidra project itself (not a
markdown transcription) is the source of truth for exhaustive function listings; this doc
captures the functions of actual semantic interest plus the overall structural shape.
