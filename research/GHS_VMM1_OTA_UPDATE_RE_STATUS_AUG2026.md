# `.vmm1`/`.ota_update` Static RE — Status (Aug 2026 session)

**Goal:** unblock Bundle 1 (does GHS's `.vmm1` port keep upstream `libavb`'s
overflow guards?) and Bundle 2 (`.ota_update.text` opcode/frame layout) by
getting real disassembly of the GHS INTEGRITY hypervisor image (module
`85098662`, `SOC_HOSTOS`). No hardware access this session — purely static.

**Bottom line: real progress, blocker fully diagnosed, not yet resolved.**

---

## What's confirmed

1. **Y181/Y177 `85098662` are byte-identical** (`md5` match) — corroborates
   `MASTER_REFERENCE.md`'s claim with an actual measurement, not just a
   citation.
2. **The raw container is a proprietary Green Hills INTEGRITY download
   image** — not a format any standard tool (`file`, `r2`, `objdump`)
   auto-parses. Manual reverse-engineering of its directory/symbol table
   (end-of-file, ~48KB region starting ~`0xe35000`) recovered a real record
   format: 64-bit canonical kernel VA (`0xFFFF8000_XXXXXXXX` pattern) + 32-bit
   size + name string, cross-validated against multiple known sections in
   `research/decompiled/ghs_analysis.txt` (`.ota_update.text`,
   `.ota_update.rodata`, `.calibrations.text` all matched exactly). This table
   appears to be a **debug symbol table**, not a load/extraction table — no
   file-offset field was found in it, so it doesn't by itself enable
   extracting section bytes.
3. **A prior analyst already solved this problem once.** Found (not
   documented anywhere previously surfaced in `gminfo_resources`) at
   `GM_research/.../analysis/extracted_artifacts/`:
   - `ghidra_projects/ghs32.rep` — an existing, working Ghidra project,
     program name `ghs_integrity.elf`, language `x86:LE:32:default`
     ("correct 32-bit i386" per `INVENTORY.md`; a prior `ghs_proj` 64-bit
     attempt was abandoned as wrong-arch).
   - `INVENTORY.md` documents a `firmware_carved/ghs_integrity.elf` (a
     converted, standard-ELF version of the same binary) — **this no longer
     exists on disk**, confirmed by search. Same provenance-drift pattern as
     elsewhere in this corpus: documented, not persisted/since cleaned up.
4. **Installed Ghidra 12.1.3 + PyGhidra** (`brew install ghidra`) on the
   research machine — new, reusable capability. Successfully opened the
   existing `ghs32` project headlessly via PyGhidra
   (`pyghidra.run_script()`/`open_program()`, needs
   `GHIDRA_INSTALL_DIR=/opt/homebrew/Cellar/ghidra/<ver>/libexec` and
   `nested_project_location=False` since it's a standalone-GUI-created
   project, not PyGhidra-nested).
5. **Cleanly extracted real section bytes** for `.vmm1.text` (244,706 B),
   `.vmm1.rodata` (170,832 B), `.ota_update.text` (71,451 B),
   `.ota_update.rodata` (6,588 B) directly from the loaded program's memory
   blocks — sizes match `ghs_analysis.txt` exactly. Saved at
   `GM_research/.../analysis/extracted_artifacts/section_dumps/`.

## The blocker (precisely diagnosed, not resolved)

Ran the corpus's own pre-written `research/scripts/avb_audit.py` against the
real loaded program via PyGhidra (the artifact's own recommended next step,
previously blocked for lack of PyGhidra). It produced **zero results** —
diagnosed why directly rather than guessing:

- `.vmm1.text` has **140 identified function boundaries** (matches
  `decompiled/vmm1_all.c`'s "140 vmm1 functions decompiled") but the actual
  bytes are mostly `getInstructionAt() == None` / `getDataAt() == None` —
  **undefined**, never walked by the disassembler.
- Directly checked reference counts to the known AVB string addresses
  (`getReferencesTo()`): **0 references**, confirming no xref exists because
  the referencing code was never disassembled.
- This is not a new problem — it's an **independent confirmation** of
  `INVENTORY.md`'s own note: `vmm1_all.c` — *"140 vmm1 functions decompiled
  (UNUSABLE due to Green Hills toolchain — no string refs)"*. The prior
  analyst hit and documented this exact wall already.

## CONFIRMED CORRECTION: `.vmm1.text`/`.ota_update.text` task code is x86-64, not x86-32

This overturns the existing corpus's architecture conclusion (`ghs32`
project's "correct 32-bit i386" verdict in `INVENTORY.md`, and by extension
the Bundle 1 artifact's "the module is a 32-bit build" claim, which traces
back to the same source). Evidence, not inference:

- Disassembled the raw `.vmm1.text` dump with `radare2` at **8 of the 140
  function entry points Ghidra itself already identified** (independently,
  not cherry-picked): `0x8ac, 0x92a, 0xb40, 0xc60, 0xdb0, 0x123f, 0x1468`,
  plus the shared entry stub. Under a 64-bit interpretation, **every single
  one** decodes as complete, valid instructions with no desync, and several
  show textbook x86-64 function prologues: `push rbp; mov rbp, rsp` (×2),
  `push rbx; mov rbx, rdi` (callee-save setup), and
  `mov rax, qword fs:[0x80]` — a `fs:`-segment TLS/stack-guard access, an
  x86-64-only idiom with no 32-bit equivalent.
- Under the 32-bit interpretation the *same* bytes produce garbage: stray
  `0x48` bytes decode as standalone `dec eax`, splitting what are actually
  `REX.W`-prefixed 64-bit instructions and desyncing the rest of the stream
  — this is exactly the failure mode that produces "register-level noise,"
  matching `INVENTORY.md`'s own complaint about `vmm1_all.c`.
- The 64-bit interpretation's instruction boundary at file offset `0x900`
  lands **exactly** on Ghidra's independently-identified function
  `FUN_00f60900` — the two facts (correct-looking disassembly, and landing
  precisely on a boundary someone else already found by different means)
  corroborate each other.

**Practical implication:** `.vmm1`/`.ota_update` (and likely every other
GHS INTEGRITY task in this image — the debug symbol table's uniform 64-bit
canonical-VA convention now makes sense under this correction, rather than
being an anomaly) execute in 64-bit long mode. This does not necessarily mean
every AVB-parser detail in the Bundle 1 artifact is wrong (e.g. the header
being big-endian is a data-format fact independent of host arch), but the
"32-bit build" premise behind the `CONCAT44`/dword-pair-arithmetic overflow
theory (O1/O2 in `VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md`) needs re-examination
once real disassembly exists — a genuine 64-bit `uint64_t` add doesn't have
the same 32-bit-truncation failure mode the artifact was fuzzing for.

## Attempted, inconclusive: locating the AVB string xrefs

With the architecture corrected, tried two byte-pattern scans over the raw
`.vmm1.text` dump (Python, not a real disassembler) for the standard
64-bit "load an absolute address" idioms:
- RIP-relative `LEA reg, [rip+disp32]` (`REX 8D /r`, mod=00 r/m=101): **zero
  hits anywhere in the file.** Plausible — GHS INTEGRITY kernel code likely
  isn't position-independent (fixed load address), so RIP-relative
  addressing may simply not be used.
- Absolute `MOVABS reg, imm64` (`REX.W B8+r`): **697 real hits**, but
  **none** target an address inside `.vmm1.rodata`'s real vaddr range
  (`0xf9c000`-`0xfc5b4f`).

**This is inconclusive, not a negative result** — byte-pattern grepping
without a real disassembler walking the instruction stream will miss
addressing forms it doesn't check for (e.g. `[reg+disp32]` off a
pre-loaded section-base register, `push imm64` sequences, or split
load-high/load-low constructions) and can't distinguish real instruction
starts from coincidental byte matches inside other instructions' operands.

**Follow-up with real analysis (same session): still zero xrefs, but now
a real negative result, not a tooling gap.** Two bugs/gaps fixed and ruled
out before accepting this:
1. The string addresses I was checking against were wrong by 5-12 bytes —
   copied from the artifact's citation text, which quotes the strings
   *without* their real `"VMM: "`/`"VMM: ERROR: "` prefix. Found the true
   string starts via `izz` (real 64-bit-aware string scan): `0xf9c93f`
   (`"VMM: vbmeta bad header..."`) and `0xf9cc4c`
   (`"VMM: ERROR: rollback index is too old..."`).
2. Built a single combined flat file (`.text` + real-size gap-padding +
   `.rodata`, matching their true relative vaddr layout) so `r2`'s analysis
   sees both regions at correct addresses in one session, ran full `aaa`
   (CFG-driven, not pattern-matching), then additionally forced `af`
   (analyze function) at **all 140** of Ghidra's already-known function
   entries explicitly, to rule out r2's own function-discovery heuristics
   missing coverage.

With both fixed, `axt` (cross-references-to) at the correct string
addresses still returns **nothing**. This now looks like a real result:
**no call site in `.vmm1.text` directly embeds either string's address.**
Working hypothesis, not yet checked: these are likely accessed through an
**indirect error-reporting mechanism** — a shared "report error N" function
indexing into a pointer table by an integer error code, rather than each
call site embedding a direct `movabs`/`lea` to its specific string. This is
a common embedded/kernel pattern and would explain the negative result
without implying a tooling failure. Not yet located; would need to find a
table of consecutive pointers (in `.vmm1.data` or `.vmm1.rodata`) whose
entries match known string vaddrs, then find what references the *table's*
base address instead.

## Table hypothesis: tested and ruled out. Real explanation found: wrong binary.

Chased the indirect-table hypothesis with a fresh fork. Result: **ruled out**,
and replaced with a much better-supported explanation.

**Table hypothesis, tested directly:**
- Extracted `.vmm1.data` (46,156 B, vaddr `0x01095234`) via the same
  PyGhidra approach as the other sections.
- Scanned `.vmm1.data` and `.vmm1.rodata` themselves (both aligned and
  unaligned 8-byte-qword reads) for any pointer-shaped value landing inside
  `.vmm1.rodata`'s real vaddr range (`0xf9c000`-`0xfc5b4f`): **zero hits** in
  `.vmm1.data`, zero self-referential hits in `.vmm1.rodata`.
- Checked whether the two known string addresses (`0xf9c93f`, `0xf9cc4c`)
  appear as a literal 8-byte (or 4-byte low-half) value **anywhere in the
  entire 14.9 MB `85098662` image** — not just `.vmm1.text`: **zero
  occurrences, full stop.** No table, no direct embed, no cross-task
  reference anywhere in this binary.
- Ruled out "relocation placeholder" as the explanation too: zero-immediate
  `movabs` (the shape a load-time-patched relocation would take) is rare —
  5 of 697 total `movabs` instructions in `.vmm1.text`. The other 692 carry
  real, already-resolved addresses baked into the static file, so this
  isn't a case of "the real value only exists after runtime relocation."

**Also found while building the marker list for this check:** of the full
24-string `avb_audit.py` marker set (`avb_safe_add`'s "Overflow when adding
values", "Descriptor size is not divisible by 8", every `INVALID_*`/
`Chain partition*`/hashtree/hash-descriptor guard string), **only 2 exist
anywhere in `.vmm1.rodata` at all** — the same two already known
(`"vbmeta bad header..."`, `"...rollback index is too old..."`). The entire
rest of the standard `libavb` overflow-guard string set is simply absent
from `.vmm1.rodata`.

**Real explanation, found and confirmed:** `research/decompiled/elk_strings.txt`
(already in this corpus, extracted from a *separate* binary — `elk_inner.elf`,
the "ELK"/kernelflinger component, per `INVENTORY.md`: *"Inner ELF:
kernelflinger + libavb + BoringSSL + .oemkeys RSA-4096"*) contains:
- The **full** guard-string set, including the exact `avb_safe_add` string
  `"Overflow when adding values."` (line 1388) that's absent from `.vmm1`.
- The literal embedded source path
  `hardware/intel/kernelflinger/avb/libavb/avb_vbmeta_image.c` (line 1393)
  — direct, unambiguous confirmation this is a real, complete upstream
  `libavb` build, not a stripped/partial one.
- A richer, more complete set of vbmeta/rollback strings generally (16
  AVB-related matches vs. 2 in `.vmm1.rodata`).

**Conclusion: the real, actively-referenced `libavb` implementation almost
certainly lives in `elk_inner.elf` (kernelflinger), not `.vmm1`.** The 2
matching strings in `.vmm1.rodata` are most likely vestigial/dead
data — either leftover from a shared build artifact, or genuinely
unreferenced in this compiled image, consistent with the zero-xrefs-anywhere
result above. **This means Bundle 1's original premise — fuzzing `.vmm1` as
"the GHS-ported AVB parser" — was very likely targeting the wrong binary
component from the start.**

**Caveat:** `elk.bin` (the source `elk_inner.elf` was extracted from) is
currently a **broken symlink** (`elk.bin -> /tmp/elk.bin`, target doesn't
exist) — same provenance-drift pattern noted elsewhere in this corpus
(documented/extracted in a prior session, not persisted). BUT: confirmed
`GM_research/.../analysis/extracted_artifacts/decompiled/elk.asm` **does
exist on disk** (the full `objdump -d -M intel` dump `INVENTORY.md`
describes, 287k lines) — so the disassembly Bundle 1's guard-diff actually
needs is *already available*, without needing to re-extract the binary at
all. This should be the starting point, not `.vmm1`.

## `elk.asm` structural search for `avb_safe_add_to`: exhaustive, negative

Followed the pointer from the previous section — went straight to `elk.asm`
(the real target's disassembly, no re-extraction needed) to try to locate
`avb_safe_add_to` directly. Ground truth (real upstream source,
`libavb/avb_util.c`):
```c
bool avb_safe_add_to(uint64_t* value, uint64_t value_to_add) {
  uint64_t original_value = *value;
  *value += value_to_add;
  if (*value < original_value) {
    avb_error("Overflow when adding values.\n");
    return false;
  }
  return true;
}
```
On 32-bit x86 this compiles to an `add`+`adc` pair (real uint64 add) followed
by an overflow check comparing the **new sum against its own pre-add
original value**, then on failure a call to an error/log function.

**Caveat discovered along the way:** `elk.asm` (`objdump -d`) only covers
`Disassembly of section .text:` — no `.rodata` bytes are in this artifact,
so the byte-level string→address resolution technique used for `.vmm1`/
`.ota_update` doesn't apply here; this had to be a pure structural/pattern
search over `.text` alone. `elk.bin`/`elk_inner.elf` themselves are gone
(broken symlink to a long-vanished `/tmp/elk.bin`), and the module they were
originally carved from (`SOC_ABL`/`OBBP` partition) isn't present anywhere
in this corpus either — confirmed by search — so this raw binary cannot
currently be re-extracted from scratch. `elk.asm` is genuinely all that's
left of this target.

**Method:** scanned all 1,417 `adc` instructions in `elk.asm`, filtered to
`add`+`adc` pairs immediately followed by an overflow-style conditional
jump (`jb`/`jc`/`jae`/`jnc`/`jl`/`jge`) within 8 instructions → **15 real
structural candidates**. Checked every one with full surrounding context
(self-checked 1, three parallel agents checked the other 14, each given the
exact false-positive shape already found so they wouldn't waste time
rediscovering it).

**Result: all 15 are real code, all 15 are NOT `avb_safe_add_to`.**
Breakdown of what they actually are:
- **4 instances of a SHA-family hash `update()` routine** (bit-length
  counter: `count += len*8`, carry into a second counter field) — same
  shape repeated once per digest context struct, distinguished only by
  field-offset shifts.
- **1 bignum/deadline bound-clamping comparison** (RSA/BoringSSL-style,
  compares an independently-computed product against the sum, not the sum
  against its own original).
- **2 instances of 512-bit bignum addition** (BoringSSL/RSA multi-limb add,
  8×64-bit unrolled; the trailing `jb`/`jae` is a loop-counter check, not an
  overflow guard).
- **4 instances of UEFI/page-table memory arithmetic** — confirmed by a
  `mov cr3, eax` a few instructions after one candidate (definitively
  page-table setup), and by another candidate's 40-byte iteration stride
  matching `sizeof(EFI_MEMORY_DESCRIPTOR)` exactly.
- **2 instances of an address-range/GPT-style bound-check loop** iterating a
  40-byte struct array, comparing against a caller-supplied bound argument
  (not the pre-add value) — most likely storage/partition enumeration.
- **1 disk-I/O sector-arithmetic bound check** (LBA×block-size 64×32→64
  multiply feeding an EFI protocol vtable call for a read operation) — the
  single closest-*looking* candidate structurally (an `offset+size`-shaped
  check), but the negation step and EFI-call context rule it out as AVB
  code.

**The decisive discriminator, identified during this pass:** every single
false positive compares the post-add sum against something **other than its
own pre-add value** — a constant, an argument, a separately-loaded struct
field, or an independent computation. `avb_safe_add_to`'s defining trait is
comparing the sum against the *same* memory location's value from
*immediately before* the add. None of the 15 candidates do that.

**Conclusion, not yet explained:** `avb_safe_add_to` was not found via this
structural search. Most likely explanations, neither confirmed: (a) it was
aggressively inlined at every call site with call-site-specific register
allocation, so no single canonical "add;adc;compare-to-original;call" shape
exists to pattern-match against — each inlined instance would need to be
found via its *caller's* context instead; or (b) the actual compiled shape
differs from the assumed post-add-compare pattern (e.g. a pre-add
UINT64_MAX-minus-b comparison instead), which this search would not catch.
**This specific technique (structural add/adc pattern matching) is now
exhausted for this target — a different approach is needed to make further
progress on Bundle 1's core question**, e.g. working from a known AVB
caller function's likely shape (e.g. `avb_descriptor_foreach`'s `% 8`
divisibility check, a much more distinctive and hard-to-confuse-with-crypto
instruction pattern), or reacquiring the raw binary for real
decompilation.

## BREAKTHROUGH: `elk_inner.elf` reconstructed and decompiled — first confirmed AVB guard found intact

Followed through on the plan to stop hand-reading `elk.asm` assembly and get
real decompiled pseudocode instead. Concretely:

1. **Reconstructed a loadable binary from `elk.asm` itself.** `objdump -d`
   prints raw hex bytes on every line; parsed all 286,645 instruction lines
   and wrote their bytes into a flat buffer at the correct addresses
   (`0x12800000`-`0x128dc285`). Verified byte-for-byte against `elk.asm`'s
   own listing before trusting it (`r2` disassembly of the reconstruction
   matches the original file exactly at the addresses checked).
2. **Imported into a fresh Ghidra project** as raw `x86:LE:32:default` at
   the correct base address (`analyzeHeadless ... -loader BinaryLoader
   -loader-baseAddr 0x12800000`), ran full auto-analysis (14s, clean).
3. **Decompiled all 2,293 identified functions** to one 171k-line C
   pseudocode file (Java `GhidraScript`, `DecompInterface`, 30s timeout per
   function, 0 failures).

**Searched the decompiled output (not raw asm) for small functions with a
64-bit type, a comparison, and a bool-shaped return — 10 candidates, all
manually inspected. None was `avb_safe_add_to`, but one, `FUN_128da780`,
is a confirmed, verified match for `avb_descriptor_validate_and_byteswap`:**

```c
// FUN_128da780 (decompiled, at 0x128da780)
bool FUN_128da780(undefined4 *param_1,undefined8 *param_2)
{
  undefined8 uVar2 = FUN_128d5a00(*param_1,param_1[1]);  // byteswap tag
  *param_2 = uVar2;
  ulonglong uVar3 = FUN_128d5a00(param_1[2],param_1[3]); // byteswap num_bytes_following
  param_2[1] = uVar3;
  if ((uVar3 & 7) != 0) {                                 // % 8 == 0 check
    FUN_128d5cb0(0x128f7248); FUN_128d4bf0(...);          // error/log call
  }
  return (uVar3 & 7) == 0;
}
```
vs. real upstream (`libavb/avb_descriptor.c`):
```c
bool avb_descriptor_validate_and_byteswap(const AvbDescriptor* src, AvbDescriptor* dest) {
  dest->tag = avb_be64toh(src->tag);
  dest->num_bytes_following = avb_be64toh(src->num_bytes_following);
  if ((dest->num_bytes_following & 0x07) != 0) {
    avb_error("Descriptor size is not divisible by 8.\n");
    return false;
  }
  return true;
}
```
**Line-for-line logical match**, including the exact `& 0x07` mask. Also
confirmed `FUN_128d5a00` (the byteswap helper it calls twice) is a real
32-bit-halves byteswap combined via `CONCAT44` — exactly the shape needed to
byteswap a big-endian `uint64_t` on a little-endian host (`avb_be64toh`'s
job), matching the artifact's documented "all multi-byte fields big-endian"
format.

**Corroborating context, not just an isolated match:** traced all 5 call
sites of `FUN_128da780`. One sits inside a `do { ...; idx++; } while (...)`
loop walking an array with an error-log-and-jump-to-cleanup pattern on
failure — exactly `avb_descriptor_foreach`'s real structure (validate each
descriptor, bail with an error on the first bad one), not a coincidental
standalone match.

**Verdict: this specific AVB integrity guard (`AvbDescriptor.num_bytes_following`
divisibility-by-8 check) is intact and unmodified in `elk_inner.elf`.** A
real, positive, disclosure-relevant answer to a piece of Bundle 1's original
question — this rules out a class of bug (undersized/misaligned descriptor
exploitation via a corrupted `num_bytes_following`) for this specific check,
on this specific binary.

**Still open:** `avb_safe_add_to` itself wasn't found by this same
small-function/64-bit-type search — either it's inlined at every call site
(no standalone function to find) or its exact decompiled shape didn't match
the search filter used (worth a second, differently-filtered pass — e.g.
without requiring the literal `ulonglong` keyword, since Ghidra sometimes
represents 64-bit pointer dereferences via paired 32-bit accesses instead).
`avb_vbmeta_image_verify`, the header magic/version checks, and the
hash/hashtree descriptor validators haven't been searched for yet either —
same decompiled corpus, same technique, not yet applied.

**Artifacts persisted** (not left in `/tmp`):
`GM_research/.../analysis/extracted_artifacts/elk_reconstructed/` —
`elk_inner_text.bin` (reconstructed flat binary), `elk_decompiled_all.c`
(171k-line full decompilation, all 2,293 functions), `ghidra_project/` (the
Ghidra project itself, reusable for further scripted analysis without
re-importing).

## SECOND CONFIRMED GUARD, EMPIRICALLY VERIFIED: `avb_safe_add_to` is intact — and found `avb_vbmeta_image_verify` itself

Continued past the descriptor-validator find. Rather than blind keyword
search (which is why the first pass missed this — Ghidra represents the
`uint64_t*` parameter as a plain `uint*` with two-element indexing, not a
`ulonglong*`, so no "ulonglong" keyword appears anywhere in the function
body), found it by **tracing the caller context** of the confirmed
block-size-multiple-of-64 check.

**`FUN_128d6b60` is `avb_vbmeta_image_verify` itself.** Confirmed by
multiple exact matches to real upstream `libavb/avb_vbmeta_image.c` found
in sequence in its decompiled body:
- `if (param_2 < 0x100)` → `if (length < sizeof(AvbVBMetaImageHeader))` —
  `0x100` = 256 = the real header's exact size.
- A 4-byte compare call right before it → `avb_safe_memcmp(data, AVB_MAGIC, AVB_MAGIC_LEN)`
  (not found via searching for the magic as an inlined integer constant —
  it's a real memcmp-style call against a byte string, which is why the
  earlier `0x30425641`/`0x41564230` integer search found nothing).
- `if (((local_12c & 0x3f) == 0) && ((local_124 & 0x3f) == 0))` — the exact
  De Morgan-negated form of
  `(auth_block_size & 0x3f) != 0 || (aux_block_size & 0x3f) != 0`
  ("Block size is not a multiple of 64").
- Immediately after, two calls to `FUN_128d5bc0(&running_total, size_a, size_b)`
  — exactly the shape of the real source's
  `avb_safe_add(&vbmeta_size, sizeof(AvbVBMetaImageHeader), auth_block_size)`
  followed by `avb_safe_add_to(&vbmeta_size, aux_block_size)`.

**`FUN_128d5bc0` is `avb_safe_add_to`, confirmed AND empirically verified
correct** (not just structurally similar — actually tested):
```c
bool FUN_128d5bc0(uint *param_1,uint param_2,uint param_3)
{
  uint uVar1 = *param_1, uVar2 = param_1[1];       // original_value (lo,hi)
  uVar8 = param_3 + uVar2 + CARRY4(param_2,uVar1); // new high word w/ carry
  *param_1 = param_2 + uVar1;                       // *value = ... (low)
  param_1[1] = uVar8;                               // *value = ... (high)
  if (CARRY4(param_3,uVar2) || CARRY4(param_3+uVar2, CARRY4(param_2,uVar1))) {
    ... FUN_128d4bf0(...);   // error/log call on overflow
  }
  return uVar2 <= uVar8 && (uint)(param_2 + uVar1 < uVar1) <= uVar8 - uVar2;
}
```
This is `value_to_add` passed as two 32-bit halves (32-bit ABI calling
convention) with the classic add-with-carry idiom, and a return expression
that's a non-obvious but correct 64-bit-via-32-bit-halves comparison of
`new_value >= original_value`.

**Wrote a Python re-implementation of this exact arithmetic and tested it
against true 64-bit semantics** (`(value+add) & MASK64`,
`new_value >= original_value`) across all relevant boundary values (0, max,
every 32/64-bit carry boundary, sign-bit boundaries) plus 200,000 random
64-bit pairs. **Result: 0 mismatches out of 200,100 test cases.** The
decompiled logic is a mathematically faithful, non-broken implementation of
the overflow check — not just "looks similar," actually proven equivalent.

**Verdict so far: two of libavb's core integrity guards
(`avb_descriptor_validate_and_byteswap`'s divisibility check,
`avb_safe_add_to`'s overflow check) are confirmed present, unmodified, and
correctly implemented in GM's shipped `elk_inner.elf` (kernelflinger)
bootloader.** No evidence of weakening for either. This is a real, positive,
disclosure-relevant answer to Bundle 1's original question — for these two
checks specifically.

**Traced the rest of `FUN_128d6b60`'s body — the full function matches, not
just the isolated guards above.** In sequence, confirmed:
- Algorithm-type branch (`local_11c - 4U < 3` vs. else) selecting between two
  different hash implementation call groups — matches real libavb's
  `AvbAlgorithmType` enum structure exactly (values 1-3 = SHA256 variants,
  4-6 = SHA512 variants, dispatched via `avb_algorithms[h.algorithm_type]`).
- `FUN_128d5a50(local_118 + iVar2, uVar8, iStack_110)` right after the hash
  computation — the computed-hash-vs-stored-hash comparison
  (`avb_safe_memcmp(computed_hash, header_block + h.hash_offset, h.hash_size)`).
- `FUN_128db250(...)` — the RSA signature verification call, taking the
  computed hash, the stored signature, and a public key pointer/length pair
  — matches `avb_rsa_verify()`'s real signature.
- On success, writes results into `*param_3`/`*param_4` — the real
  function's `out_public_key_data`/`out_public_key_length` output
  parameters, populated only on full success.

**Net: `avb_vbmeta_image_verify` is present in full, structurally
comprehensive, and matches real upstream `libavb` end-to-end** — magic
check, length check, version check, block-size-alignment check, safe-add
total-size computation (empirically verified correct, see above),
algorithm-based hash computation, hash comparison, RSA signature
verification, and the success/output path. This is a complete, not
piecemeal, positive result for Bundle 1's core question on this binary.

**Version discrepancy — resolved, confirmed real (not a misread).** Traced
the local variable layout in `FUN_128d6b60`: `local_138` (4 bytes) +
`local_134` (4 bytes) + `local_130` (4 bytes), populated by
`FUN_128d7230(param_1, local_138)` right before the version check — this
struct layout exactly matches `AvbVBMetaImageHeader`'s
`magic`/`required_libavb_version_major`/`required_libavb_version_minor`
fields in that exact order, and `FUN_128d7230` is
`avb_vbmeta_image_header_to_host_byte_order` (the whole-header byteswap
function). So `local_134 != 1` = the major-version check
(`AVB_VERSION_MAJOR == 1`, consistent) and `1 < local_130` = the minor
version check, comparing the *image's* `required_libavb_version_minor`
against **this binary's own compiled-in `AVB_VERSION_MINOR = 1`**.

**Conclusion: `elk_inner.elf` (kernelflinger, the early-boot-stage
verifier) enforces compatibility with libavb 1.1, not 1.2.** This is a real
version skew between boot-chain components, not a coincidence or misread —
the live device separately reports `ro.boot.vbmeta.avb_version=1.2`
elsewhere (a different, presumably later-stage GHS-side check). Two boot
stages verify against two different libavb minor versions. Not yet explored
further: whether this skew has any practical security implication (e.g. a
vbmeta feature/flag introduced between 1.1 and 1.2 that kernelflinger's
earlier-stage check wouldn't know to enforce) — worth a dedicated diff of
what changed in upstream `libavb` between the 1.1 and 1.2 tags if this
thread gets picked up again.

## Next steps (in order of leverage)

1. **Fix the architecture in a real disassembler and re-analyze.** Either
   reconfigure Ghidra's `ghs32` project's language to `x86:LE:64:default`
   (matching the abandoned-but-apparently-more-correct `ghs_proj` attempt)
   and re-run analysis, or build a fresh `r2` project with `-b 64` and run
   full `aaa` auto-analysis (proper CFG-driven, not byte-pattern grepping) —
   this replaces the inconclusive manual scan above with real
   instruction-level coverage and real xref detection.
2. Once real disassembly exists, rerun `avb_audit.py` via PyGhidra (tooling
   confirmed working this session) to get genuine string→function xrefs, and
   locate the real overflow-check logic for the O1/O2/O3 targets — re-examine
   whether they're even the right target classes for 64-bit code (per the
   correction above).
3. Apply the same architecture-first approach to `.ota_update.text` before
   any further opcode/frame-layout work for Bundle 2 — same correction
   almost certainly applies (identical shared entry stub, same disassembly
   behavior observed).

## `.ota_update.text` — same methodology applied (item 3 above, done)

Repeated the full `.vmm1.text` workflow against `.ota_update.text` /
`.ota_update.rodata` (reused the already-extracted dumps in
`section_dumps/`, sizes unchanged: 71,451 B / 6,588 B).

**Confirmed:**
- **Same architecture correction applies.** Built a combined flat file
  (text + real 2,277-byte gap-pad + rodata, matching the true
  `0x00de4000`/`0x00df6000` relative layout) and disassembled under `-b 64`.
  Clean, complete instructions, zero desync — and the shared entry stub is
  **byte-for-byte structurally identical** to `.vmm1.text`'s (same
  `xor edx,edx; mov eax,eax; or edx,edx; jne <fault>; movabs; cmp; jne
  <fault>; mov rcx/rdx/rsi,0; movabs rdi,imm; call; xor rbx,rbx; div rbx
  (deliberate fault); jmp $`), including a `call` landing exactly on a
  Ghidra-identified function (`FUN_00de5cb8`) — same cross-validation
  pattern as `.vmm1.text`'s `FUN_00f60900` alignment.
- Got the real function list from the existing `ghs32` Ghidra project: 36
  functions with entry points inside `.ota_update.text` (vs. 140 for the
  larger `.vmm1.text`), forced `af` at all 36 in `r2`.
- Real string scan (`izz`) recovered **true addresses** (not the
  artifact's citation-truncated ones) for every OTA-relevant string
  documented in `RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md`: `"Bad command
  length for OTA command.\n"` @ `0xdf60e8`, `"RPC channel error: %d\n"` @
  `0xdf610d`, plus the full ABL/CSE/HECI/attkb error-string set (all
  `"GHS: Error/Warning: ..."` lines, e.g. `"...ABL update command failed:
  %d\n"` @ `0xdf74d2`, `"...CSE did not enter prepare update mode"` @
  `0xdf75e2`, `"...Read more attkb bytes (%d) than expected (%d)\n"` @
  `0xdf7793`).

**Same negative xref result as `.vmm1.text` — now a cross-validated
pattern, not a one-off.** Checked `axt` (real xrefs, post-`aaa` +
all-36-functions-forced) against the OTA framing strings and every ABL/CSE
string above: **zero real code-side references.** The only hits were the
same false-positive class the parent flagged for `.vmm1.text` — spurious
`(nofunc)` jump instructions whose *source* address is itself inside
`.ota_update.rodata` (i.e. the analyzer briefly misreading ASCII string
bytes as code, not a real reference).

Also searched the combined `.text`+`.rodata` region for an **8-byte
pointer table** entry matching any of these string addresses (the
"indirect dispatcher" hypothesis from the `.vmm1.text` section) —
**zero hits.** If such a table exists, it isn't in `.text`/`.rodata`; the
next place to check is `.ota_update.data` (700 bytes per
`ghs_analysis.txt`, not yet dumped/searched — out of scope for this pass).

**Assessment:** this strengthens the `.vmm1.text` finding from "maybe
vmm1-specific" to "a consistent GHS INTEGRITY kernel-wide pattern" — two
independent modules, same shared entry stub, same complete absence of
direct string embeds from identified functions. Bundle 2's opcode/frame-
layout work is now blocked on the same open question as Bundle 1's AVB
guard-diff: find the indirect error-reporting mechanism (most likely a
small table in each module's `.data` section, keyed by an integer error
code) rather than continuing to search for direct per-site references,
which real CFG-driven analysis now rules out with reasonable confidence
across two modules.

## `.ota_update.text` follow-up: full decompilation, negative result strengthened further

Applied the same "reconstruct + decompile in Ghidra" technique that found
the two confirmed AVB guards in `elk_inner.elf` — genuine real decompiled C,
not `r2` asm reading. Result: the negative xref finding above is now backed
by much stronger coverage, not weakened by it.

- Imported `ghidra_dump__ota_update_text.bin` fresh as raw `x86:LE:64:default`
  at the correct base (`0x00de4000`), added `.ota_update.rodata` as a second
  memory block in the same program (`0x00df6000`) so string references could
  resolve if any existed.
- **CFG-driven discovery from the entry point alone found only 37
  functions** — traced them: every one is generic C-runtime boilerplate
  (`memcpy`/`memset`-shaped functions, `atexit`/startup glue). None is
  OTA-specific. This confirms the earlier `r2`-based negative wasn't a
  coverage artifact of stopping too early — the connected component from
  the entry point genuinely doesn't contain the real logic.
- **Brute-forced byte-level disassembly across the entire 71,451-byte
  region** (attempted disassembly at every unaddressed byte offset, 51,011
  attempts) plus a function-boundary sweep over every resulting instruction
  start: found **576 additional functions** the CFG walk missed (614
  total) — real, substantial additional coverage, most likely code reached
  only via indirect/function-pointer calls the static analyzer can't trace
  (the GHS init-array walker pattern already seen in this module supports
  this).
- **Decompiled all 614 functions to real C pseudocode** (18,041 lines,
  `section_dumps/ota_update_text_decompiled_full.c`). Searched for any
  reference to the `.ota_update.rodata` address range or the specific known
  string addresses (`0xdf60e8`, `0xdf610d`, etc.): **zero hits, across the
  full decompiled corpus, not just the CFG-reachable subset.**

**This substantially raises confidence in the negative result** — it's no
longer "36-or-37 functions checked," it's "614 functions, real coverage of
essentially the whole 71KB section, decompiled to readable C, still
nothing." The indirect-table hypothesis (checking `.ota_update.data`, still
not dumped) remains the most promising unexplored lead, now with much less
residual doubt that this is a coverage problem rather than a real fact
about how this module's error reporting works.

## Artifacts

- `GM_research/.../analysis/extracted_artifacts/section_dumps/*.bin` — raw
  extracted section bytes (see above).
- Ghidra install: `brew install ghidra` (12.1.3, bottled, ~1.1GB with
  `openjdk@21` dependency).
- PyGhidra python package installed via
  `pip3 install --break-system-packages <ghidra-libexec>/Ghidra/Features/PyGhidra/pypkg/dist/pyghidra-3.1.0-py3-none-any.whl`.
- `.ota_update.text`/`.ota_update.rodata` combined analysis file (not
  persisted — `/tmp/ota_update_combined.bin`, rebuild via the gap-pad
  method above from the existing `section_dumps/` `.bin` files if needed
  again).
