# tisvcsv4.dll's Multi-OEM SecurityAccess Key-Server Dispatch

**Date:** 2026-08-25
**Context:** Extension of today's full-function Ghidra disassembly of GM DPS (see
`MDI2_DPDU_API_PROTOCOL_AUG2026.md` and `gm_dps/disassembly/MANIFEST.md`). `tisvcsv4.dll`
(25,809 functions total) was identified as DPS's protocol engine. A scoped 30-function
security-relevant subset (keyword-matched + one-hop call-graph proximity to known
SecurityAccess functions + hand-rolled-crypto signal detection) was independently annotated by
6 parallel Opus passes, which converged extremely strongly (near-identical architecture across
all 6 independent reads). Full merged annotations at
`gm_dps/disassembly/annotations/tisvcsv4.dll.SECURITY_CANDIDATES.annotations.md`.

## Headline finding

`tisvcsv4.dll` is **not GM-only** — it's a shared multi-brand diagnostic protocol engine that
dispatches UDS `$27` SecurityAccess key computation to one of several **externally-loaded,
per-OEM key-server DLLs**, chosen upstream (by vehicle architecture / ECU config), not by a
single visible switch statement.

## Two layers of dispatch

**Layer 1 — GM-internal algorithm-class selector**, `FUN_10086bb0` (top-level dispatcher), keyed
on a method byte (`param_4 & 0xff`) combined with a 16-bit algorithm id (`uVar6`, built from a
config byte + the request param):
- `2`/`3` → hand-rolled inline algorithm bank (via `FUN_10087420` → `FUN_10002c50`)
- `4`/`5` → `FUN_10001670` (outside the scoped candidate set, not yet analyzed)
- `6`/`7` → `GetTickCount()`-seeded random challenge, mixed via byteswap/`+0x6187`/rotate/
  `+0x6f19`/rotate, then routed to standard `CSecurity::SetSeedAndGetKey`
- `0x10` → `CSecurity::SetSeedAndGetKey(uVar6 | 0x1000)`
- **default** → `CSecurity::SetSeedAndGetKey(uVar6)` — the standard GM path, and confirmed to be
  imported from `dllsecurity.dll`, not locally implemented (`FUN_100873b0` is a thin bridge; only
  one call site to the real method exists in the whole 25,809-function file, no definition)

**Layer 2 — hand-rolled algorithm table**, `FUN_10002c50`, keyed on a 16-bit algorithm ID read
from `*(ushort*)(in_ECX+2)` (sourced from the `CVIT1` seed table): IDs `0x201`–`0x305` are
bespoke inline transforms (LFSR bit-permutation, iterated LCG multiply-add loops, S-box/table
lookups, embedded key constants) — genuinely hand-rolled crypto, not calls to a library. IDs
`0x3f6`/`0x4f6`/`0x4fe` escape to yet another external DLL: `DllTzSale.dll::fnRequestOperation`
(not yet analyzed).

**Layer 3 — per-OEM external key-server DLLs**, each reached through its own dedicated leaf
function (the "brand switch" is which function gets called, decided by the caller above this
file — most plausibly by vehicle architecture / `CVIT1` id, not confirmed from this candidate
set alone):

| OEM / purpose | DLL | Export | Caller in tisvcsv4.dll | Entry |
|---|---|---|---|---|
| GM (standard) | `dllsecurity.dll` | `CSecurity::SetSeedAndGetKey` | `FUN_100873b0` (bridge only) | `0x100873b0` |
| SAIC | `Seed2Key.dll` | `SAIC_ComputeKeyFromSeed` | `FUN_1006bb50` (lazy loader) | `0x1006bb50` |
| GM 5-byte MAC | `IVCS5B.dll` (name is config-driven, not literal) | `RequestOperation` | `FUN_10086d50`, logged by `FUN_1006bbd0` | `0x10086d50` |
| (unclear OEM) | `IECS.dll` (name config-driven) | `getUnlockResponse` | `FUN_10086f90` | `0x10086f90` |
| (unclear OEM) | `IECS.dll` | `getKeyProvResponse` | `FUN_10087140` | `0x10087140` |
| PSA / Stellantis (Opel/Vauxhall) | `ivcspsa.dll` (hardcoded) | `GetPsaKey` | `FUN_10087530` (also branches on host exe being `dps.exe`) | `0x10087530` |
| Shanghai-GM | `ivcssgm.dll` (hardcoded) | `RequestOperation` | `FUN_10087cc0` | `0x10087cc0` |
| Nissan (reflash) | `sesame_GM.dll` → decrypts → `simsim_GM.dll` | `ExtractEncryptedDLL` → `GetKey` (class `CNissanKey`) | `FUN_10049ab0` — a full KWP2000 unlock+reprogram state machine, `'GMPS'`-tagged download block | `0x10049ab0` |
| Legacy algorithm escape | `DllTzSale.dll` | `fnRequestOperation` | inline in `FUN_10002c50` for IDs `0x3f6`/`0x4f6`/`0x4fe` | (inline) |

Two of the loaders (`IVCS5B.dll`, `IECS.dll`) pull their actual module name from a runtime
config/singleton object (`FUN_101bd974` → vtable+0xc) rather than a hardcoded string — a
configurable plugin architecture, meaning the literal DLL name seen in this binary's import
table may not be the only one ever loaded at that call site.

## What this means for research scope

- `Seed2Key.dll`, `sesame_GM.dll`, `simsim_GM.dll`, `ivcspsa.dll`, `ivcssgm.dll`, `IVCS5B.dll`,
  `IECS.dll` (already in our current 13-binary disassembly scope), and `DllTzSale.dll` are all
  real, load-bearing DLLs in the actual key-computation supply chain for one brand or another.
  Only `dllsecurity.dll`, `S84.dll`, and `IECS.dll` are in the current disassembly scope; the
  rest (`Seed2Key.dll`, `sesame_GM.dll`, `simsim_GM.dll`, `ivcspsa.dll`, `ivcssgm.dll`,
  `IVCS5B.dll`, `DllTzSale.dll`) have not been located on disk yet and are not part of today's
  64,105-function disassembly.
- `S84.dll`'s AES-CMAC (documented separately, see `MANIFEST.md` and this session's earlier
  security-chain findings) is one option among several the platform supports, not necessarily
  the one used for the specific vehicle/ECU this research is targeting (a 2024/2025 Chevrolet
  Silverado — almost certainly the GM-standard `dllsecurity.dll` path or the AES-CMAC `S84.dll`
  path, not the SAIC/PSA/Nissan branches, but this file doesn't itself resolve which — that
  selection happens upstream in the DPS architecture/subtype configuration).
- `FUN_10001670`, `FUN_10002a90`, `FUN_100031c0` (called by algorithm IDs `0x206`/`0x207`/`0x20a`
  with embedded key constants) are flagged by multiple passes as follow-up candidates just
  outside the current 30-function scope — worth a second scoping pass if deeper analysis of the
  hand-rolled algorithm bank is wanted.
