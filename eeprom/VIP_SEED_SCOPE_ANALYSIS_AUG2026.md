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
  per-level implementations. **(2026-09-10 correction:** a follow-up disasm pass on
  `FUN_000b67d0` recovered the actual access-control structure sitting on top of this range
  check: a **19-level SecurityAccess bitmask**, one bit per level via `1<<(level-2)` for
  levels 2..20 inclusive (0x02–0x14 = 19 values, not 18 — the earlier count was off by one),
  with full-unlock tested as `mask & 0x7FFFF == 0x7FFFF`. This is why a live MDI2 `$27` sweep
  shows some levels unlocked and others still locked — it is per-bit state in this mask, not a
  single global locked/unlocked flag. See §7 below.)
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

## 3. Historical static-analysis limits (August 2026; current scope in §§4–7)

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

  **Live runtime evidence (2026-11-12, bench radio Y181 `W231E-Y181.3.2-SIHM22B-499.3`):** these strings do print at runtime, which
  supports reading them as the real seed path rather than dead rodata: `viplog.log`+`viplog.log.rot` contain 7113 `[PROTOKEY] Receives
  invalid seed [1|2] from BCM` lines versus 9 `Seed %d taken from GMLAN`, i.e. on a bench unit with no BCM the fetch almost never succeeds
  (read: counts; inferred: no BCM present). This corroborates the "seed is sourced from the BCM, not computed in the VIP" reading only; it does
  **not** locate the calling code and does not close the static-analysis gap in (b) above, since no program-counter correlation was captured.

  **Reconciliation note (2026-11-12):** the 7113/9 figures above are one counting method (raw grep,
  `viplog.log`+`viplog.log.rot` combined; 9 = forensic count in `viplog.log` only). A second,
  header-stripped forensic count gives 7114 total for the invalid-seed lines (`viplog.log` 2245 +
  `viplog.log.rot` 4869; `[1]`=3556, `[2]`=3558) against 10 `Seed %d taken from GMLAN` lines (10 in
  `viplog.log`, 0 in `.rot`). Both counting methods are retained here rather than reconciled to a
  single number; see `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` ~§3 (near line 479) for the
  fuller breakdown.

## 4. Captured target behavior (corrected 2026-11-11)

Fresh reconstruction of `SPS_radioCal_and_OS_UpdateCHeck.pcapng` identifies two complete
level-1 exchanges on **radio ECU `0x80`**: **31-byte normal seed → 12-byte response →
`67 02`**. The fixed 16-byte prefix matches the radio's DID `F0F3`; the remaining 15 bytes
vary. Seed/key/identity values are deliberately omitted here. See
[the capture timeline](../research/AUG24_SESSION_FULL_PCAP_TIMELINE.md).

`DPS+SPS.pcapng` instead programs **amplifier ECU `0x81`** (three containers); radio `0x80`
has DID reads and seed-only DoIP probes there. Do not turn other-ECU observations into
radio programming or cross-ECU key-sharing proof.

The target's separately bench-reported degenerate state is **31 all-FF seed bytes**.
The client sends **12 zero bytes**, receives `67 02`, and completed a 14-container
**stock signed** LTZ calibration write on 2026-11-10 with post-reset readback and ADB retained.
This establishes this exact response in that state, not acceptance of any arbitrary key.
[Bench report and code](../mdi2_client/README.md).

## 5. Security boundaries

The EEPROM data bytes `0x0441` and `0x0A81` are the owner-corroborated ADB recipe; framing
bytes, `0x1A01`, and `0x0B41` are not required changes. No CRC recomputation was needed
for the documented minimal edit; that is not a statement about all EEPROM records.

ADB opens through **VIP MEC reporting → SoC `gm_adb_auth_init` / `is_secure_mode`**:
MEC 1–255 bypasses the GM client certificate requirement; zero, query failure, and
out-of-range values fail closed. The all-FF UDS seed is not consumed to open ADB.
ProtoKey's status-plus-16-byte-key IPC and the Signature Bypass Ticket are separate
mechanisms. See [EEPROM audit §0.10–0.14](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md).

The parameterized validator and internal 19-bit mask described above do not establish
which wire subfunctions map to each internal slot. They do not prove arbitrary calibration
acceptance, root, SELinux changes, or signature bypass.

## 6. What the DLL and static analysis establish

The archived S84.dll analysis identifies Crypto++ AES/CMAC code and the
`generate27Response` / `generateMAC` exports. The runtime key-provisioning client is also
documented. These are DLL capabilities; the actual target selection and exact seed-input,
subfunction, derivation-stage and truncation shaping still require a target known-answer
check with a known secret and an accepted response.

SHA-256 or CRC constants in a firmware analysis do not alone establish the target's
SecurityAccess key derivation. The earlier claim that this proves a SHA-256-based scheme
is withdrawn. Likewise the earlier 32-byte normal-seed claim and one-stage
`CMAC(master, ECUID || challenge)[:12]` assertion are superseded as target conclusions.
The current client implements that candidate shaping but labels it unverified on hardware.

## 7. Remaining unknowns

No usable target master secret has been recovered in this research: the key map is a
template, and the documented Frida capture hook was not run. The exact target response
formula, selection of the applicable DLL branch, provisioning scope, and cross-module or
cross-vehicle key sharing are unresolved. The legacy `dllsecurity.dll` 16-bit-seed VM
is a different scheme and cannot be applied to this 31-byte target by analogy.

All 14 examined CSM calibration containers have independently verified RSA signatures.
That establishes signed package format; it does not isolate the active UDS verifier or
prove that a particular edited-transfer NRC was caused by signature rejection.
Current evidence, scope and source links:
[GM seed/key and calibration signatures](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

## 8. UPDATE (2026-09-10): Community/expert corroboration from CameraLoops.ru — Global-B key is server-issued, not crackable client-side; and a scope-check on the "GM Seed Key Generator" tool

Two findings from the site's forum/files sections (owner's own paid account, `mcOreos`),
describing a server-issued Global-B workflow, not proving the exact gminfo37 response formula in §§6–7:

- **Troy (CameraLoops site admin, self-described "GM Car Hacking Expert"), in
  [`forums/topic/1528-gm-dps-archive-on-global-b/`](https://www.cameraloops.ru/forums/topic/1528-gm-dps-archive-on-global-b/),
  responding to a 2022 GMC Yukon IPC-programming failure on Global-B:** *"The GM Global-B
  vehicles uses a much newer higher secured architecture and cannot be programmed with DPS
  as easy as the Global-A vehicles. You need to generate the Global-B Key externally, or
  have access to a legit DPS account. The cracked DPS won't work with Global-B vehicles."*
  This is independent community/expert confirmation — from someone running the largest
  dedicated GM SPS/DPS community, with no visibility into this repo's own RE — of exactly
  what §7 found structurally: the Global-B key is not a local/crackable secret sitting in
  DPS software, it has to come from GM's own backend (a "legit DPS account", consistent
  with the `IECS.dll` mTLS key-provisioning-server mechanism), and pirated/cracked DPS
  installs (the MHH-Auto-style licensing cracks documented in
  `research/DPS_AND_MODIFICATION_LANDSCAPE.txt`) do not bypass this. Troy states he
  personally "doesn't know much about Global-B" beyond this — not a source of algorithm
  detail, just confirms the shape of the problem.
- **The referenced deeper thread, `forums/topic/1311-gm-dps-certificate-to-global-b/`
  ("GM DPS Certificate to Global B"), is gated behind CameraLoops' "Private Top Secret GM
  Car Hacking Forum" — a "Contributor" membership tier above the account's current access
  level.** Likely the single most directly relevant thread on this exact open problem on the
  entire site; not read. **Actionable, owner's call:** upgrading CameraLoops membership tier
  would unlock this thread — flagging as a concrete next step rather than a dead end.
- **Scope-check, negative result:** CameraLoops sells a
  ["GM Seed Key Generator Tool"](https://www.cameraloops.ru/files/file/416-gm-seed-key-generator-tool/)
  (a popular/advertised tool, linked site-wide in the header ticker). Its own description:
  *"This tool can generate the seed key for all GM 5-Byte and 2-Byte seed electronic
  modules."* This is the **legacy short-seed `$27` algorithm family** (classic GM
  VATS/theft-deterrent-style modules — BCM/ECM/SDM etc., per its own module-ID examples) —
  it does **not** cover the CSM/A11's 31-byte seed or establish its precise response scheme. Confirmed not a shortcut around the master-key problem; ruling it
  out rather than leaving it as an unchecked lead. (A commenter in that thread separately
  notes "Gm uses 256 different algo's" — i.e. an 8-bit algorithm-selector code across GM's
  ECU population — consistent with this repo's own `dllsecurity.dll`
  table-selected-by-`(byte)param_3*0xd` finding in §7's reconciliation note; different
  algorithm families genuinely coexist across GM's module population, as already flagged.)
