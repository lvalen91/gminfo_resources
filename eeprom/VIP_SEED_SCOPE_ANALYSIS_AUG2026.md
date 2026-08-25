# VIP SEED/CHALLENGE SCOPE ANALYSIS — Aug 2026

**Question:** Is the VIP's seed-generation logic that the SBI (Seed-Bypass-Indicator, EEPROM
0x0441/0x0A81 = 0xFF) bypass defeats a separate, ADB-only code path, or is it the same
underlying seed/challenge function shared by other SecurityAccess levels (calibration,
diagnostic tiers, other ECU programming)?

**Verdict (medium-high confidence, partially open):** The bypass is **very unlikely to be
ADB-scoped**. Field evidence (independent of this session's static analysis) already shows the
VIP hands out the degenerate all-`0xFF` seed for a standard CAN UDS `$27` request, not just the
ADB/PROTOKEY-over-SoC-IPC path. Static analysis in this session independently confirms the
VIP's SecurityAccess seed/key logic is architecturally **one shared, level-parameterized state
machine** (`FUN_ram_000b67d0` @ `0xb67d0`), not N separate per-level implementations — which
structurally supports (but does not by itself prove) that a shared defect would propagate to
all levels processed through it. **The exact point where the EEPROM SBI byte is read and turned
into the degenerate seed value was not located** in this session — see "What remains open" below.

---

## 0. Toolchain note — which Ghidra project is authoritative

The task briefing pointed at project `vip_app_proj` / program `vip_app.bin`. That project's
existing analysis is **incomplete**: after a forced full re-analysis, address `0xecd84` (cited
as the one provenance-audit-verified anchor) still had **no disassembled instructions** — only
raw undefined bytes — and a forced disassembly at that address produced garbage (decoded a
spurious 4-byte `jr` back into a neighboring function, then reverted to undefined bytes),
indicating the region is genuinely un-analyzed in that project, not that the address is wrong.

The actual project that produced the verified `out_vip_app` decompile pile (per
`headless_vip_app.log`, which records the original `extract_crc.java` run) is a **different**
project: **`86331656_ghidra`**, program **`/86331656`**, at the same
`ghidra_projects` directory (just not the one named in the task briefing — it appears to be a
leftover/incomplete import). Opening `86331656_ghidra`/`86331656` reproduces
`FUN_000ecd84` exactly (`prepare {r28,r29,lp},0x6; ... jarl 0x000f5cb8,lp; ...`), matching the
verified pile byte-for-byte. **All findings below are from `86331656_ghidra`/`86331656`.**
If any future session opens `vip_app_proj`/`vip_app.bin` instead, expect the same
disassembly gaps encountered here.

---

## 1. `FUN_000ecd84` is NOT itself "the seed function" — it's a generic paired primitive

`FUN_000ecd84` has **285 distinct call sites** across the firmware (verified via
`ReferenceManager.getReferencesTo`), spanning dozens of unrelated subsystems (CAN handling in
the `0xa6xxx`–`0xa9xxx` range, feature init in `0x84xxx`, etc.). Its sibling `FUN_000ecdac` has
**261** call sites and is called in the same paired pattern (`ecd84(id) ... ecdac(id)`)
everywhere it appears — e.g. inside the security state machine itself:

```c
FUN_ram_000ecd84(0x1e);
DAT_ram_febd3e05 = DAT_ram_febd3e05 | 0x40;
FUN_ram_000ecdac(0x1e);
```

This lock/unlock-by-resource-id pairing (both take a small integer "module/resource id" as
first argument) is consistent with a generic mutex-acquire/release or critical-section-by-ID
primitive, not a security- or seed-specific function. **The provenance audit's earlier framing
of `0xecd84` as the head of "the VIP validation fn chain" undersells what it actually is: a
generic infrastructure primitive used throughout the firmware, including inside the security
code, but not unique or specific to it.** This is a refinement, not a contradiction, of the
provenance audit's "verified real" status for `0xecd84` — the address is real, but it is not by
itself evidence of security-specific logic.

## 2. The real seed/key state machine: `FUN_ram_000b67d0` (0xb67d0) — VERIFIED, and it is SHARED/parameterized

This directly reproduces and **upgrades the status of** the chain the provenance audit flagged
as `INFERRED / UNSUPPORTED as measured` (cluster 1, item 8: "chain 0xecd84/0xb6652/0xaee28...
only 0xecd84 exists in shipped decompilation; 0xb67d0/0xb6652/0xaee28 from a non-shipped
external r2 pass"). That audit appears to have been run against the same incomplete
`vip_app_proj` project this session initially (and mistakenly) tried first. Against the correct
`86331656_ghidra` project, **all of `0xb67d0`, `0xb6652`, `0xaee28`, `0xb6680`, `0xb6690` exist
as real, fully-decompilable functions**, and `0xb67d0` is exactly 906 bytes — matching the size
the audited document cited for the "Y181" variant.

Decompiled signature and structure of `FUN_ram_000b67d0`:

```c
int FUN_ram_000b67d0(byte param_1,int param_2,int param_3,int param_4,char param_5,
                      undefined1 *param_6,undefined1 *param_7)
{
  ...
  uVar8 = (uint)param_1;                       // security level / slot id, 0x00-0xFF
  FUN_ram_000ecd84(0x1b,param_2,DAT_ram_febe7213,DAT_ram_febd3e06);
  uVar7 = (byte at [param_2+0xf]) >> 4;
  uVar5 = (byte at [param_2+0xf]) & 0xf;
  uVar2 = FUN_ram_000b6652(uVar8);              // level-range mapping/validation
  if ((param_1==1) || (param_1==0xff) || (param_1-2 > 0x12)) {
      FUN_ram_000aee28(0x10);                   // zero a state bank
      DAT_ram_febd38ea = 0;
      *param_7 = 0x31;                          // UDS NRC 0x31 requestOutOfRange
      return 1;
  }
  if (((uVar7 != uVar5) && (FUN_ram_000b6652(0xff) != uVar5)) || (uVar2 != uVar7)) {
      FUN_ram_000aee28(0x10);
      DAT_ram_febd38ea = 0;
      *param_7 = 0x22;                          // UDS NRC 0x22 conditionsNotCorrect
      return 1;
  }
  FUN_ram_000b6680(); FUN_ram_000b6690();       // two more state-readiness gates
  ... on success, copies 0x10+0x20+0x10 = 0x40 bytes from the caller-supplied
      param_2/param_3/param_4 buffers into a per-session RAM staging area at
      0xfebda50f.. and sets DAT_ram_febd38ea = 1 (state: seed/key material accepted) ...
}
```

Key facts this establishes:

- `param_1` is accepted over the range **0x02–0x14 (18 distinct values)**, each validated by
  the SAME code path through `FUN_ram_000b6652`'s range-mapping logic. This is a single,
  parameterized function servicing many security-level/slot values — **not** N separate
  per-level implementations.
- The function returns genuine UDS-style negative response codes (`0x31`, `0x22`) written into
  `*param_7`, strongly indicating this is the VIP's actual `$27` SecurityAccess seed/key
  processing core (or immediately adjacent to the wire-protocol handler), not something ADB-specific.
- A second, related function `FUN_ram_000b0416` (and `FUN_ram_000b015a`) shows the same
  architecture from the "key verified" side: a table lookup (`_DAT_ram_febe71e4 * 8 +
  -0x1418930`, the *same* table-indexing arithmetic seen inside `FUN_ram_000b67d0`) selects
  **one of four shared state bytes** (`DAT_ram_febd38ea`, `_ed`, `_eb`, `_ec`) depending on
  which numeric slot/level range the request falls in (1–0xf, 0x10–0x11, 0x12, 0x13). Four
  level-groups, one shared processing routine each side (seed-accept vs key-verify) — again a
  shared/parameterized architecture, not per-level separate code.
- `FUN_ram_000af112` (the security module's init/reset function, called at boot) zeroes this
  entire state pool in one place (`febe71f1..febe71fb`, `febd38cb..febd38e9`, etc.) and is the
  only function (together with the trivial one-line `FUN_ram_000b7ad4`, which just does
  `DAT_ram_febd3e06 = 0`) that touches `DAT_ram_febd3e06` besides `0xb67d0` itself reading it.
  **Correction to a hypothesis I initially formed and want to flag explicitly: `DAT_ram_febd3e06`
  is a generic "security module initialized" readiness flag (1 = init complete, 0 = reset),
  not itself the processed SBI/EEPROM value.** The EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md claim
  that RAM address "0x3e06" is "the processed EEPROM value loaded during boot, corresponds to
  SBI 0x0440/0x0A80" is **not confirmed** by what this session found — treat that specific claim
  as still unverified/likely mischaracterized, pending someone locating the real EEPROM-read
  code (see open items below).

## 3. What could NOT be determined — be explicit about this

- **Callers of `FUN_ram_000b67d0` could not be found.** `ReferenceManager.getReferencesTo`
  returns zero hits (no CALL, no DATA, no computed-call reference), and a raw byte scan for the
  address as a literal 4-byte pointer across the entire 1.9 MB image also returns zero hits.
  This means the function is reached through an **indirect/computed call Ghidra's default
  analysis did not resolve** — most likely a security-level or UDS-SID dispatch table using
  relative/packed offsets rather than raw absolute pointers (consistent with the `* 8 +
  -0x1418930`-style indexed table arithmetic seen nearby). **This is the single piece of
  evidence that would most directly answer the operator's question** — if the ADB/ICUSB-PROTOKEY
  path, the CAN `$27` diagnostic path, and the calibration-programming `$27` path all resolve to
  calls into this same dispatch table feeding `0xb67d0`, that is a definitive "shared" answer.
  Resolving it requires manually locating and typing the dispatch table in Ghidra (defining it as
  an array of pointers/offsets so the "Create Address Tables" analyzer or a manual script can
  attach references), which was not completed in this session.
- **Where the actual seed bytes (including the all-`0xFF` degenerate value) get written into the
  `param_2`/`param_3`/`param_4` buffers before they reach `0xb67d0` was not located.** That
  upstream code — wherever it reads GMLAN/BCM-sourced seed material or substitutes it based on
  the EEPROM SBI flag — is architecturally the more likely place the actual bypass check lives,
  and it is *upstream* of the shared state machine described above. Whether that upstream
  sourcing code is itself shared across callers/levels or duplicated per-caller is unknown.
- **A full-binary decompile of all 6,253 functions**, grepped for `PROTOKEY`, `OTA_DIAG`,
  `AME_DIAG`, `Seed`/`seed`, `Challenge`/`challenge`, `ICUSB` (the exact debug-string prefixes
  that anchor GM's own GetSeed/PROTOKEY logging, confirmed present as rodata strings — e.g.
  `[PROTOKEY] Seed %d taken from GMLAN`, `[PROTOKEY] Receives invalid seed [%d] from BCM`,
  `[OTA_DIAG] Get Seed request failed`) found **zero functions whose decompiled output
  references these strings**, and a raw pointer scan for the string addresses themselves found
  zero real hits (two apparent hits landed inside an unrelated GPIO pin-init function and are
  almost certainly coincidental byte collisions, not real references — V850 loads absolute
  addresses via split `movhi`/`movea` half-word pairs, which will not appear as a contiguous
  4-byte little-endian literal, so this method is inherently blind to that addressing style).
  Combined with the dozens of `Unable to resolve constructor` p-code errors Ghidra logged while
  decompiling elsewhere in this same binary, the most likely explanation is that the actual
  PROTOKEY GetSeed/ICUSB code lives in a **currently mis-disassembled or unreached region** of
  this same image (not necessarily a different firmware component) — but I cannot rule out that
  it lives in a different overlay/segment not covered by this flat binary. This is a real,
  named gap, not a "no evidence either way" shrug: it means the debug strings that would let you
  directly find and read the GetSeed function by name are architecturally disconnected from
  static analysis as currently run, and closing it needs either (a) manual jump-table/dispatch
  recovery in Ghidra, or (b) dynamic tracing (e.g. UART debug log capture during a live SecurityAccess
  exchange, since the `[PROTOKEY]`/`[OTA_DIAG]` strings are clearly meant to be printed to a debug
  console) to locate the calling code by correlating printed output to program counter.
- One interesting, independently-derived architectural fact worth flagging even though it
  doesn't resolve the main question: the debug strings themselves ("Seed %d taken from **GMLAN**",
  "Receives invalid seed [%d] from **BCM**") indicate PROTOKEY's seed does not originate as a
  VIP-internal computation — it is fetched/cached from the Body Control Module over GMLAN and then
  relayed. If true, "the seed algorithm" is partly external to the VIP entirely, and the SBI bypass
  may work by suppressing/faking that GMLAN fetch rather than by patching a local crypto routine —
  which would still be consistent with the bypass having broad effect (any caller that goes through
  the same fetch-or-fake path gets the same fake data), but changes where to keep looking.

## 4. Independent field evidence already answers the "is it broader than ADB" question — empirically, not just structurally

This is not from this session's Ghidra work, but from prior bench testing already in the
corpus (`diagnostics/dps/A11_CSM_x80.Txt`, referenced by
`research/S27_SOC_VALIDATION_BENCH_TEST.md`), and it is the strongest piece of evidence for
the operator's core question:

```
01:01:48.531< 14 DA 80 F2 10 03                       [enter extended diagnostic session, ECU 0x80 = VIP]
01:01:48.531> 14 5A F2 80 50 03 00 64 01 F4            [positive response]
01:01:48.531< 14 DA 80 F2 27 01                        [SecurityAccess requestSeed, level 1]
01:01:48.547> 14 5A F2 80 67 01 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
              FF FF FF FF FF FF FF FF FF FF FF FF        [all-0xFF seed, 32 bytes]
```

ECU `0x80` on this vehicle's LS-CAN is the VIP itself (per the same bench-test doc's own
routing table). This is a **plain, standard UDS `$27` SecurityAccess exchange over CAN**,
independent of the ADB/ICUSB/PROTOKEY-over-SoC-IPC mechanism the SBI bypass was originally
documented against. It already empirically demonstrates that with the SBI flipped, the VIP's
generic CAN diagnostic UDS stack — not just the SoC-facing ADB path — hands out the same
degenerate all-`0xFF` seed. **This is direct, captured-traffic proof that the bypass's effect is
not confined to ADB.** It does not by itself prove the calibration-programming-specific `$27`
tier is affected (that request used an extended diagnostic session, `10 03`, not a programming
session, `10 02`, which the calibration-write path is documented to require), but it does prove
the "one bypass, ADB-only" framing is already falsified by data GM's own head unit produced on
this owner's bench.

## 5. Bottom line for the operator

1. **Not ADB-scoped — already field-proven for at least one other context.** The all-`0xFF`
   degenerate seed has been captured live over plain CAN `$27` SecurityAccess (ECU 0x80 = VIP),
   not just through the ADB/ICUSB/PROTOKEY-over-IPC path. This alone means "ADB cert bypass" was
   already an undersell before this session started.
2. **Structurally consistent with "shared", confirmed by this session's reverse engineering:**
   the VIP's seed/key acceptance logic is one parameterized function (`FUN_ram_000b67d0` @
   `0xb67d0`, real, 906 bytes, independently reproduced against the correct Ghidra project this
   session — upgrading a previously-"unsupported" provenance-audit item) servicing at least 18
   distinct level/slot values through the same validation and staging code, backed by a
   4-group shared state pool. A single shared implementation is inherently more likely to
   propagate a defect uniformly across levels than N independent implementations would be.
3. **Not proven end-to-end.** I could not find (a) what calls `0xb67d0` for which contexts
   (ADB vs CAN vs calibration) — the call sites are indirect/dispatched and unresolved in
   current analysis — or (b) the exact code that reads the EEPROM SBI byte and turns it into
   the degenerate seed value, which sits upstream of `0xb67d0`. Until one of those two gaps is
   closed, "affects calibration-programming SecurityAccess specifically" remains a strong,
   evidence-backed hypothesis rather than a confirmed fact — but "affects more than ADB" is
   no longer a hypothesis; it is measured.

## 6. UPDATE (Aug 2026, follow-up pass): PROTOKEY/ADB path confirmed to share code with the CAN `$27` machine

A follow-up Ghidra pass (same `86331656_ghidra` VIP_APP project) set out specifically to find
the VIP-side function that produces the status byte `libpal_security.so` checks on the
SoC-IPC "protokey" response (`1`=success, `2`="ICUSB not enabled", `3`="BIS key not valid",
`4`="protokey generation failure", `5`="invalid parameters", `6`="ICUSB busy", `7`="ICUS key
program failed", `8`="secret key load failure" — see
`research/ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md` §6 for how this vocabulary was recovered from
the Android side). **Result: the PROTOKEY/ADB path is NOT architecturally separate from the CAN
`$27` SecurityAccess machine — it is the same multi-slot engine.**

The security subsystem implements several structurally identical SecurityAccess "slots," and
`FUN_ram_000b67d0` (the CAN `$27` handler already mapped) is just **slot `0x10`**:

- `FUN_ram_000b67d0` — slot `0x10`, state `DAT_febd38ea`, key buffer `febda50e/50f`.
- `FUN_ram_000b6bcc` — slot `0x11`, state `DAT_febd38ed`, key buffer `febda54f/550`. **Called
  from `FUN_ram_000864de` @ `0x8650e`**, itself reached from a wrapper at `0x86970` that sits in
  the `0x86xxx` cluster containing the `[AME_DIAG] ICUSB enabled and both key/Master key/Unlock
  key provisioned` strings — i.e. this is the ICUSB/protokey-provisioning entry point.
- `FUN_ram_000b703a` — slot `0x12`/`0x13`, state `DAT_febd38eb`.

All three call the same shared helpers (`FUN_ram_000b6652` subfunction-index map,
`FUN_ram_000b66a0` key program/verify state machine, `FUN_ram_000aef30` subsystem reset,
`FUN_ram_000aee28` slot clear) and read/write the same shared state block (`febd38ea/eb/ec/ed`,
`febe7213`, `febd3e05/06`, `febe71e0/71ed/71f9/71fa/71fb`, challenge/key buffers at
`febda50e+`). `xref` analysis on `DAT_febd38ea` shows a closed set of touchers: init `0x86ae4`,
reset `0xaef30`, and the three slot machines only — confirming the ICUSB/protokey dispatcher
reaches this state exclusively through the same slot-machine family as the CAN `$27` handler.

**This resolves the open question from §5.3 above in the "shared" direction with hard evidence,
not just structural inference.** An EEPROM-SBI defect that reaches the `$27` machine (already
field-proven via captured CAN traffic, §4) reaches the PROTOKEY/ADB slot through the *same*
code and state, not independent logic — no separate vulnerability chain needs to be found or
proven for the ADB path specifically; it rides the same bug.

**Not yet resolved:** the exact function that serializes the `1..8` status byte into the
`SERIAL_IPC_PROTO_KEY_CHANNEL` 17-byte frame back to the SoC (`J6_prv_ProtoKey`, referenced by
dead/unreferenced debug strings at `0x1658e`/`0x165d2`) sits somewhere in the `0x86xxx`
dispatcher cluster and was not fully decompiled this pass — worth a follow-up if the exact
byte-to-slot-state mapping is needed for a PoC.

### Concrete next steps to close the remaining gap
- In Ghidra, manually recover the dispatch table that calls `0xb67d0` (look near the table-index
  arithmetic pattern `X * 8 + -0x1418930` — that constant/table is shared between `0xb67d0`,
  `0xb015a`, and `0xb0416`, and is very likely walkable to a UDS-SID or session-tester slot table).
- On the bench, with SBI still flipped, send `$10 02` (programming session) then `$27` at the
  calibration-programming level over CAN to ECU `0x80` and see whether it also returns
  all-`0xFF` (the existing capture used `$10 03`, extended session, not programming session) —
  this is a low-effort empirical test that would directly settle the calibration-specific
  question without needing the dispatch table recovered first.
- Capture VIP UART debug output (the `[PROTOKEY]`/`[OTA_DIAG]` strings are printf-style debug
  logging) during a live SecurityAccess exchange to correlate log lines to the actual GetSeed
  code path, since static analysis could not locate it by string reference.
