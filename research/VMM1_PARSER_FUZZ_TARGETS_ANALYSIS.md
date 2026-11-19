# `.vmm1` (GHS Hypervisor) AVB/vbmeta Parser — Fuzz Targets + Confirmed Guard RE

**Scope.** AVB/vbmeta parser security for the gminfo37 GHS INTEGRITY hypervisor image
(`85098662`, `SOC_HOSTOS`): TOCTOU/overflow fuzz targets against `.vmm1` (the AVB/libavb
port identified in its section strings) and the confirmed guard-function reverse
engineering that located and verified three of libavb's integrity checks inside a
*different* binary, `elk_inner.elf` (kernelflinger). **Not here:** GHS boot-phase/ELK/
recovery architecture and the Ghidra/PyGhidra tool-setup narrative behind this RE (see
[GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md), which absorbed
that session log as a dated history subsection); general AVB/A-B/BCB boot-chain flow beyond
what's needed as fuzz-target ground truth (`../platform/boot_chain.md`,
[GM_INFO37_BOOT_CHAIN_ANALYSIS.md](GM_INFO37_BOOT_CHAIN_ANALYSIS.md),
[BOOT_CHAIN_ANALYSIS.txt](BOOT_CHAIN_ANALYSIS.txt)); rollback-counter/downgrade policy
([GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt](GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt)); GHS
hypervisor architecture generally ([GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md)).

**Evidence legend:** `[V]` verified/measured directly, `[FW]`/`[S]` static-firmware-derived,
`[inferred]` reasoned from adjacent evidence, not directly observed, `[U]` unverified/stated
elsewhere not independently confirmed, `[X]` external reference. Untagged technical detail
below (addresses, byte values, decompiled code) is as directly read from the binaries cited.

**Related:** GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md (tool-setup/session history, ELK boundaries),
GM_INFO37_BOOT_CHAIN_ANALYSIS.md (A/B misc struct, vbmeta flow, boot-image header — same
ground-truth tables restated below are the fuzz-target basis, not a competing copy),
BOOT_CHAIN_ANALYSIS.txt (Android boot-image field offsets, raw evidence layer),
GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt (rollback_index@0x70, misc CRC-only, RSA-2048 key).

---

## 0. What the artifacts prove

**The `.vmm1` section strings match AOSP `libavb`, statically compiled into a 32-bit x86
ELF container** `[FW]`. Evidence:
- `research/scripts/avb_audit.py` enumerates the exact `libavb` error strings and
  CVE-class markers originally hunted for: `avb_safe_add` ("Overflow when adding
  values"), `avb_descriptor_foreach` ("Descriptor size is not divisible by 8"),
  "Descriptor payload size overflow", "Overflow while computing size of boot image",
  chain-partition `rollback_index_location` validation, etc.
- Confirmed vbmeta strings in `research/decompiled/vmm1_decomp.txt`:
  `VMM: vbmeta bad header: descriptors outside data block`,
  `VMM: ERROR: rollback index is too old: %lu in image, but stored is %lu`.
- `GM_INFO37_BOOT_CHAIN_ANALYSIS.md` + `BOOT_CHAIN_ANALYSIS.txt`: magic `AVB0`, version 1.1,
  RSA-2048/SHA-256 (alg_type 1 = SHA256_RSA2048; `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt:606,633,737`
  — 2048-bit key, alg=1/SHA256-RSA), boot-image header field offsets, A/B misc layout.
- **ELF container class `[V]`:** direct read at file offset 636 of `85098662` shows
  `ELFCLASS32`/`EM_386` (32-bit x86), statically linked (`7f 45 4c 46 01 …`,
  `e_machine=03 00`), consistent with the coherent 32-bit `libavb` decompile
  (`vmm1_all.c` EAX/EDI + `CONCAT44` dword-pair idioms).
- `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`: `rollback_index` field at header offset
  **0x70** — matches the standard `AvbVBMetaImageHeader` exactly, so the header layout
  below is known-good ground truth, not a guess.

**Two things this does *not* settle, kept apart deliberately:**
1. Whether the `.vmm1.text`/`.ota_update.text` *task code* that would execute this parser
   is itself 32-bit or 64-bit — disputed, not resolved here; see **Open Conflicts**.
2. Whether `.vmm1` is even the binary GHS actually runs this logic from at runtime — §6
   below found strong evidence it is **not**, and that the real, actively-referenced
   implementation lives in a separate binary, `elk_inner.elf`. This is a different
   question from (1): §6 answers *which binary* holds the real guards; it says nothing
   about the bit-width of `.vmm1`/`.ota_update`'s own task code. Do not read §6 as closing
   item (1).

**Why 32-bit (container-class) matters for the fuzz targets below:** every size/offset
field in the vbmeta header is `uint64_t` big-endian, but the `.vmm1` *container* is a
32-bit ELF. Each 64-bit compare/add synthesized from dword pairs (`CONCAT44(... >> 0x1f, ...)`
idiom throughout `vmm1_all.c`) is precisely where "signed-vs-unsigned length math" and
high-dword-truncation bugs live. No stack canaries + no ASLR means any linear overflow
past a stack buffer is directly exploitable (deterministic return-address/saved-pointer
overwrite). **If the task-code-bitness dispute resolves to 64-bit** (see Open Conflicts),
a genuine 64-bit `uint64_t` add would not have this truncation failure mode, and O1/O2
below would need re-scoping to whatever 64-bit-specific overflow classes apply instead.

### `AvbVBMetaImageHeader` (256 bytes, all multi-byte fields big-endian)
| Off | Size | Field | Fuzz relevance |
|-----|------|-------|----------------|
| 0x00 | 4 | magic `AVB0` | header-accept gate |
| 0x04 | 4 | required_libavb_version_major | version gate |
| 0x08 | 4 | required_libavb_version_minor | version gate |
| 0x0C | 8 | **authentication_data_block_size** | block-bound math |
| 0x14 | 8 | **auxiliary_data_block_size** | block-bound math |
| 0x1C | 4 | algorithm_type | selects key/hash sizes |
| 0x20 | 8 | hash_offset | offset+len into auth block |
| 0x28 | 8 | hash_size | " |
| 0x30 | 8 | signature_offset | offset+len into auth block |
| 0x38 | 8 | signature_size | " |
| 0x40 | 8 | public_key_offset | offset+len into aux block |
| 0x48 | 8 | public_key_size | " |
| 0x50 | 8 | public_key_metadata_offset | offset+len into aux block |
| 0x58 | 8 | public_key_metadata_size | " |
| 0x60 | 8 | **descriptors_offset** | offset+len into aux block |
| 0x68 | 8 | **descriptors_size** | " (drives the descriptor walk) |
| 0x70 | 8 | rollback_index | rollback compare (CONFIRMED offset) |
| 0x78 | 4 | flags | HASHTREE_DISABLED / VERIFICATION_DISABLED |
| 0x7C | 4 | rollback_index_location | chain-partition slot index |
| 0x80 | 48 | release_string | — |

### `AvbDescriptor` (per-descriptor header, big-endian)
| Off | Size | Field |
|-----|------|-------|
| 0x00 | 8 | tag |
| 0x08 | 8 | **num_bytes_following** (must be `% 8 == 0`) |

### Android boot image header (offsets confirmed in `BOOT_CHAIN_ANALYSIS.txt:425`)
`ANDROID!`@0x00, **kernel_size@0x08**, kernel_addr@0x0C, **ramdisk_size@0x10**,
**second_size@0x18**, tags@0x20, **page_size@0x24**, header_version@0x28.

### A/B metadata (misc partition `vda9`, struct @ offset 0x800)
Magic + version + per-slot `{priority, tries_remaining, successful_boot}` + **crc32
(no cryptographic signature — CRC only)**.

---

## 1. Identified TOCTOU windows

### T1 — `descriptors_size` / `num_bytes_following` double-read over guest-shared backing (PRIMARY)
The string `descriptors outside data block` is the `libavb` bound check
`descriptors_offset + descriptors_size <= auxiliary_data_block_size`. That check reads
the size field once; the subsequent `avb_descriptor_foreach` walk re-reads
`num_bytes_following` for each descriptor to advance the cursor. In a *hypervisor*, the
vbmeta/aux block is DMA'd from eMMC into a buffer that, unless explicitly copied to
VMM-private memory and fenced, is reachable by the guest VM or a co-scheduled DMA agent.
- **Check time:** header validated, `descriptors_size` sampled → passes bound.
- **Use time:** walk re-reads `num_bytes_following` from the same page; if flipped to a
  value that runs the cursor past `descriptors_offset+descriptors_size`, the loop reads
  and byteswaps out-of-bounds. This is the classic "verify a snapshot, iterate the
  live copy" race.
- **Exploitable race:** yes *iff* the aux block is verified in place rather than from an
  immutable private copy. The single most valuable thing to confirm on real silicon is
  whether `.vmm1` memcpys the aux block to private RAM before the descriptor walk. §6's
  decompilation of `elk_inner.elf` confirms the *descriptor-validity* check is intact
  there, but does not establish whether that check runs against a private copy or a
  live DMA/guest-shared buffer — this predicate is still unconfirmed.

### T2 — Rollback: stored index is CRC-only and re-read after check
Boot flow (`GM_INFO37_BOOT_CHAIN_ANALYSIS.md:549`, `GHS_DOWNGRADE_PROTECTION_...:201`):
read `stored_rollback` from misc → compare vbmeta.rollback_index → on success update
misc. misc integrity is **CRC32 only, no signature** (`:520`). Two races:
- The compare reads `stored_rollback`; the boot decision and the later "update stored
  index" read it again. An attacker who can write misc between those points (misc is a
  normal writable block device, CRC recomputable) desynchronizes check vs. commit.
- Cross-slot: A/B slot selection (`tries_remaining`, priority) is validated by CRC only,
  so the slot whose vbmeta was checked can differ from the slot actually booted if misc
  is rewritten in the window.

### T3 — vbmeta verify-then-boot on the payload partition
vbmeta signs a *digest* of boot_a/b (hash descriptor). The verifier computes/loads the
boot image hash, compares to the descriptor, then hands the image to the guest. If the
boot partition is re-read (or guest-mapped) for execution after the hash compare rather
than executed from the exact verified buffer, the hashed bytes ≠ executed bytes. Same
in-place-vs-copy question as T1.

**All three collapse to one testable predicate:** does the verifier operate on a *private
immutable copy*, or the live DMA/eMMC buffer? If the latter, T1–T3 are real. §6 does not
settle this predicate — it confirms the *logic* of the checks, not their memory model.

---

## 2. Length-overflow targets

### O1 — `descriptors_offset + descriptors_size` 64-bit add on a 32-bit build
`avb_safe_add` exists ("Overflow when adding values"), but the `.vmm1` container port is
32-bit. Targets:
- Set `descriptors_offset = 0xFFFFFFFF_FFFFFFF8`, `descriptors_size = 0x10`. If the add
  is done as a truncated 32-bit `off+len` the wrap yields a small sum ≤ aux_size and the
  "descriptors outside data block" gate passes, then the walk dereferences
  `base + 0xFFFFFFF8...` → wild read. Mutate the **low dword and high dword
  independently** — high-dword-only mutations are the ones `avb_safe_add` misses if only
  the low 32 bits are compared.
- Same pattern for every offset/size pair: hash(0x20/0x28), signature(0x30/0x38),
  public_key(0x40/0x48), public_key_metadata(0x50/0x58).

**Status update:** §6.3 below found and empirically verified the *logical* implementation
of `avb_safe_add_to` intact and correct in `elk_inner.elf` — 0 mismatches across 200,100
test cases against true 64-bit semantics. This is strong evidence the specific overflow
guard this target probes is not weakened **in that binary**. It does not confirm anything
about `.vmm1` itself, which §6.1 found has almost no trace of the real guard-string set at
all (2 of 24 markers, both likely vestigial) — so O1 remains open as a `.vmm1`-specific
question, now better framed as "does `.vmm1` even run this check:" see §6.1.

### O2 — `authentication_data_block_size` + `auxiliary_data_block_size` total-length
`libavb` computes `sizeof(header) + auth_block + aux_block` as the total vbmeta size
("Overflow while determining total length"). On 32-bit, two `uint64` blocks each near
`0x1_0000_0000` sum-wrap. Set both to `0x8000_0000`; if total is held/compared as 32-bit
the allocation or read length underflows while the two blocks are individually accepted.
Signed-vs-unsigned: if the total feeds a `signed int` length into a read/memcpy, values
> 0x7FFFFFFF become negative → giant `size_t` on the copy. Same status caveat as O1 — see
§6.1/§6.4 (the two-`avb_safe_add`-call total-size computation is confirmed present and
logically intact in `elk_inner.elf`'s `avb_vbmeta_image_verify`, but that is a different
binary from the one this target assumes).

### O3 — descriptor `num_bytes_following` % 8 + payload sub-fields
Per-descriptor: `num_bytes_following` must be `% 8 == 0` ("not divisible by 8") and must
fit the remaining descriptor block ("Descriptor payload size overflow"). Inside typed
descriptors, hash/hashtree descriptors carry their own `partition_name_len`,
`salt_len`, `digest_len`, `hash_block_size`, `image_size`. `image_size` is the eMMC read
length — a 64-bit value multiplied/aligned. Overstate `digest_len` vs. the fixed
"Digest in descriptor not of expected size" check, or set `partition_name_len` +
`salt_len` + `digest_len` to sum-wrap past `num_bytes_following`.

**Status update:** §6.2 confirms the `% 8 == 0` divisibility check itself (
`avb_descriptor_validate_and_byteswap`) is present, unmodified, and correctly implemented
in `elk_inner.elf` — a real, positive answer for that specific sub-check, on that specific
binary. The inner sub-field (`digest_len`/`salt_len`/`partition_name_len`) sum-wrap part
of O3 was not traced in §6 and remains open.

### O4 — partition size × 512 (block→byte) multiply
Partition/image sizes are stored in 512-byte sectors and converted to bytes by `<<9`
(`* 0x200`; note the literal `0x200` in `vmm1_all.c:4558,4574`). A sector count >
`0x7F_FFFF` (~4 GiB in bytes) overflows a 32-bit byte length. Set a hashtree/hash
descriptor `image_size` (or the partition sector count read from GPT) so `sectors*512`
wraps to a small byte length → hash computed over a truncated region while the guest
gets the full (unverified) partition. **Boundaries:** max safe sector count before
32-bit byte overflow = `0x7FFFFF` sectors (0xFFFFFFFF/512); alignment expected is
512-byte sectors and typically 4096-byte (page_size) rounding for boot images.

### O5 — boot-image `kernel_size` / `ramdisk_size` offset+len (STRONG, distinct strings)
Strings `Kernel extends past end of boot image` and `RAM disk extends past end of boot
image` are the explicit bound checks:
- kernel at `page_size` rounded up, length `kernel_size`;
- ramdisk after kernel, rounded to `page_size`, length `ramdisk_size`.
The offset of each region = `round_up(prev_end, page_size)`. Mutation: set
`page_size = 0` (div-by-zero / `round_up` overflow), or `page_size = 0x8000_0000`, or
`kernel_size = 0xFFFF_F000` so `page_offset + kernel_size` wraps below the image size and
the "extends past end" check is bypassed → the guest kernel copy over-reads or the
copy-out overflows the destination buffer (no canary/ASLR → deterministic).

### O6 — rollback compare high-dword + `%lu` format truncation
`rollback index is too old: %lu in image, but stored is %lu`. `rollback_index` is
`uint64`; on this 32-bit ABI `%lu` is 32-bit. If the compare is done 64-bit but only the
low dword is meaningfully used (or vice-versa), setting `rollback_index` high dword
nonzero (e.g. `0x00000001_00000000`) can make the value compare "new enough" while its
printed/low-32 form looks old — a rollback-check desync. Also test the format path itself
for arg-count/width mismatch (two `%lu` consuming 64-bit args).

---

## 3. Input mutation strategy (malformed bundle)

Fuzz a **correctly-signed baseline** (a real Y181 vbmeta + boot pair) and mutate fields
the signature does *not* cover, then separately mutate signed fields to exercise the
reject path and any pre-signature parsing. Ordered by payoff:

1. **Header offset/size dwords, high-dword first.** For each 8-byte offset/size pair,
   iterate: `{low=0, high=1}`, `{low=-8, high=-1}` (i.e. `0xFFFFFFF8_FFFFFFFF`),
   `{0x80000000,0}`, `{0,0x80000000}`. Targets O1/O2. The high-dword-nonzero cases are
   the ones a 32-bit-truncating check waves through.
2. **`descriptors_size` vs `num_bytes_following` mismatch** — craft the aux block so the
   first descriptor's `num_bytes_following` points exactly at `descriptors_offset+
   descriptors_size` boundary, then ±8, then a value that wraps. Targets O3/T1.
3. **`num_bytes_following` not `%8`** (e.g. `...F` or `...4`) to hit the divisibility
   check; then `%8`-valid but larger than remaining block.
4. **hash/hashtree descriptor inner lengths:** overstate `digest_len`, `salt_len`,
   `partition_name_len` so their sum exceeds `num_bytes_following`; set `image_size` to a
   sector count that overflows `×512` (O4).
5. **boot image header:** `page_size ∈ {0, 1, 0x80000000, 0xFFFFFFFF}`, `kernel_size` and
   `ramdisk_size` near `0xFFFFF000` and near `image_size − page_size` (O5).
6. **misc / A/B metadata:** flip a slot's `tries_remaining`/priority and recompute CRC32
   (trivially, no key) to force selection of an unverified slot; race a second write
   during the boot window (T2).
7. **rollback_index high dword nonzero** with low dword = 0 (O6).
8. **auth/aux block-size boundary:** `auxiliary_data_block_size` one byte smaller than
   `descriptors_offset+descriptors_size` needs, to probe off-by-one in the "outside data
   block" comparison (`<` vs `<=`).

For each mutation, also produce a **re-signed** variant (if you hold the test signing
key from `research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md`) so the parser proceeds
past signature verification into the descriptor/boot-image path where O3–O5 live —
otherwise the signature gate short-circuits most interesting overflows.

---

## 4. Expected outcome if a target triggers

| Target | Primary effect | Escalation |
|--------|----------------|------------|
| O1/O2 wrap | OOB read in aux/descriptor walk | info leak of adjacent VMM memory into descriptor handling; possible hang |
| O3 payload | OOB read; with `digest_len` write-back, controlled write | heap/stack corruption in VMM context |
| O4 ×512 wrap | hash computed over truncated region | **verification bypass**: unverified partition tail booted |
| O5 boot-hdr | copy-out past destination buffer during kernel/ramdisk load | **code execution in hypervisor context** (no canary/ASLR → deterministic ROP/overwrite) |
| O6 rollback | rollback compare desync | **rollback/downgrade re-enabled**: boot an old, vulnerable signed image |
| T1 TOCTOU | verified snapshot ≠ interpreted bytes | descriptor confusion → verification bypass |
| T2 misc race | check/commit or slot desync | **persistent rollback disable / boot unverified slot** |
| T3 payload race | hashed bytes ≠ executed bytes | **full AVB bypass**, boot arbitrary kernel |

Highest-value chain: **O5 (boot-header overflow) → hypervisor RCE**, because it is a
copy into VMM memory with no canary and no ASLR, and it sits *after* the boot-image hash
descriptor is validated but operates on attacker-controlled header fields inside the
signed image (so it needs the re-signed variant, or a T1/T3 race to substitute the
image). **Most reliable without RCE: O4/O6/T2 → rollback-disable + downgrade**, which
needs no memory corruption, only length/CRC math.

---

## 5. Feasibility: testing without GHS hardware

**You do not need the Infotainment unit to fuzz the parser itself.** Options, cheapest
first:

1. **Host-replica harness (recommended).** The identified strings match stock AOSP
   `libavb`. Compile upstream `libavb` **-m32** (matching the `.vmm1` container's
   32-bit x86 ELF class) and drive `avb_vbmeta_image_verify()`, `avb_descriptor_foreach()`,
   and the boot-image bound checks with libFuzzer/AFL++ over the mutation set in §3. This
   reproduces O1–O3, O5, O6 and the divisibility/overflow logic against upstream
   semantics. Any crash here is a candidate; then confirm the specific binary that
   actually runs this logic shares it (§6.1 — likely `elk_inner.elf`, not `.vmm1`). AOSP
   already ships `libavb` fuzzers (`avb_vbmeta_image_fuzzer`, `avb_slot_verify_fuzzer`) —
   reuse them as the corpus/harness base.

2. **Emulate the extracted module.** Load `.vmm1`'s sections into Unicorn/qiling and call
   the string-anchored parse functions by address — but see §6.1: this approach targets a
   binary that is likely **not** the real runtime parser, since `.vmm1.rodata` carries
   only 2 of the 24 standard `libavb` guard-marker strings and neither has a code-side
   cross-reference anywhere in the 14.9 MB firmware image. §6's decompilation of
   `elk_inner.elf` (reconstructed from `elk.asm`, imported fresh into Ghidra as
   `x86:LE:32:default`, all 2,293 functions decompiled) is the better target for this
   approach going forward.

3. **Differential check.** Diff the extracted guard routines against the matching
   upstream `libavb` tag to see which `avb_safe_add`/`avb_safe_mul` guards GHS kept,
   removed, or mis-ported. **Partially done, see §6:** three guards
   (`avb_descriptor_validate_and_byteswap`, `avb_safe_add_to`, `avb_vbmeta_image_verify`)
   have now been located and diffed against upstream in `elk_inner.elf` with a positive
   (intact, unmodified) result. The hash/hashtree sub-field checks (O3's inner lengths)
   and the boot-image bound checks (O5) have not yet been located in the decompiled
   corpus and remain open for the same technique.

4. **TOCTOU (T1–T3) can only be *confirmed* on hardware / full platform emulation**,
   because the race depends on whether the verifier operates on a private copy vs. the
   live DMA/eMMC buffer — a property of the surrounding hypervisor, not of the parser
   logic itself. §6's static decompilation does not and cannot settle this. Approximate
   it in emulation by backing the vbmeta/boot buffer with a memory hook that returns
   *different bytes* on the second read of the same address; if verification still passes
   and the walk/boot consumes the second value, the TOCTOU is structurally present. Full
   confirmation needs the misc-partition write race on a real/emulated GHS boot.

---

## 6. Confirmed guard-function RE: `elk_inner.elf` (absorbed from GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md)

The tool-setup, Ghidra/PyGhidra install, and the `.vmm1`/`.ota_update.text`
disassembly-methodology narrative behind this section lives as a dated history
subsection in `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`; this section carries only the
AVB-guard-verification result itself.

### 6.1 Wrong-binary finding: the real `libavb` almost certainly isn't in `.vmm1`

Scanning `.vmm1.rodata`/`.vmm1.data` for the full `avb_audit.py` marker set found only 2
of the standard 24 `libavb` overflow-guard strings present at all (the two vbmeta/rollback
strings already cited in §0) — the rest of the standard guard-string set (`avb_safe_add`'s
"Overflow when adding values.", `Descriptor size is not divisible by 8`, every
`INVALID_*`/chain-partition/hashtree guard string) is simply absent from `.vmm1.rodata`.
Both of the two strings that *are* present have **zero code-side cross-references**
anywhere in the 14.9 MB firmware image — not inside `.vmm1.text`, not via a pointer table
in `.vmm1.data`/`.vmm1.rodata`, not anywhere in the whole image, checked at both the
8-byte and 4-byte-low-half level `[V]`.

`research/decompiled/elk_strings.txt`, extracted from a separate binary —
`elk_inner.elf`, the "ELK"/kernelflinger component (per `INVENTORY.md`: *"Inner ELF:
kernelflinger + libavb + BoringSSL + .oemkeys RSA-4096"*) — contains the **full** guard
string set, including the exact `avb_safe_add` string `"Overflow when adding values."`
and the literal embedded source path
`hardware/intel/kernelflinger/avb/libavb/avb_vbmeta_image.c`, plus a richer vbmeta/
rollback string set generally (16 AVB-related matches vs. 2 in `.vmm1.rodata`) `[FW]`.

**Conclusion:** the real, actively-referenced `libavb` implementation almost certainly
lives in `elk_inner.elf` (kernelflinger), not `.vmm1`. The 2 matching strings in
`.vmm1.rodata` are most likely vestigial/dead data. This means the fuzz targets in §1–§4
above, framed against "`.vmm1` as the GHS-ported AVB parser," were very likely aimed at
the wrong binary component from the start — the targets' *logic* (the overflow/TOCTOU
classes themselves) still generalizes to whichever binary really runs this code, but
confirmation or refutation of any specific target now depends on `elk_inner.elf`, not
`.vmm1`.

**Provenance caveat:** `elk_inner.elf`'s source binary (`elk.bin`) is currently a broken
symlink (`elk.bin -> /tmp/elk.bin`, target gone) — the same documented-but-not-persisted
pattern seen elsewhere in this corpus. The full `objdump -d -M intel` disassembly
(`elk.asm`, 287k lines) does still exist on disk and was the basis for the reconstruction
used below (bytes parsed back into a flat buffer at `0x12800000`–`0x128dc285`, verified
byte-for-byte against the listing before use). `elk_inner.elf` itself (and the partition
it was carved from) cannot currently be re-extracted from scratch.

**Note on bitness, kept separate from the Open Conflict:** `elk_inner.elf` was
reconstructed and decompiled as `x86:LE:32:default` — a plain 32-bit import, with no
bitness dispute raised for this binary anywhere in the source session. This is consistent
with `elk_inner.elf` being an early-boot/UEFI-stage (kernelflinger) component, architecturally
distinct from `.vmm1.text`/`.ota_update.text`'s GHS INTEGRITY task code, where the bitness
dispute (see Open Conflicts) actually lives. The two are different binaries with (as far as
RE'd so far) different, non-conflicting bitness readings.

### 6.2 `avb_descriptor_validate_and_byteswap` — confirmed intact

Decompiled `FUN_128da780` (at `0x128da780` in the reconstructed `elk_inner.elf`):
```c
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
Line-for-line logical match, including the exact `& 0x07` mask; `FUN_128d5a00` (called
twice) is a 32-bit-halves byteswap combined via `CONCAT44` — the shape needed to byteswap
a big-endian `uint64_t` on a little-endian host (`avb_be64toh`'s job), matching §0's
documented "all multi-byte fields big-endian" format. Traced all 5 call sites; one sits
inside a `do { ...; idx++; } while (...)` loop with an error-log-and-jump-to-cleanup
pattern on failure — `avb_descriptor_foreach`'s real structure, not a coincidental
standalone match.

**Verdict: this specific integrity guard (`AvbDescriptor.num_bytes_following`
divisibility-by-8 check, O3's header-level check) is intact and unmodified in
`elk_inner.elf`.** Rules out undersized/misaligned-descriptor exploitation via a
corrupted `num_bytes_following`, for this specific check, on this specific binary.

### 6.3 `avb_safe_add_to` — confirmed intact, empirically verified correct

Found by tracing the caller context of the confirmed divisibility check rather than a
blind keyword search (Ghidra represents the real `uint64_t*` parameter as a plain
`uint*` with two-element indexing, so no `ulonglong` keyword appears in the function
body — the initial structural/pattern search over `elk.asm` for `add`+`adc`+overflow-jcc
shapes had found 15 candidates and ruled out all 15 as SHA-update counters, bignum
clamps, UEFI page-table arithmetic, GPT bound checks, and one disk-I/O LBA check — none
matched the defining trait of comparing the post-add sum against its *own* pre-add value).

`FUN_128d5bc0` is `avb_safe_add_to`:
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
This is `value_to_add` passed as two 32-bit halves (32-bit ABI) with the classic
add-with-carry idiom, and a return expression that is a correct 64-bit-via-32-bit-halves
comparison of `new_value >= original_value`.

**Empirically verified, not just structurally similar:** a Python re-implementation of
this exact arithmetic was tested against true 64-bit semantics
(`(value+add) & MASK64`, `new_value >= original_value`) across all relevant boundary
values (0, max, every 32/64-bit carry boundary, sign-bit boundaries) plus 200,000 random
64-bit pairs. **Result: 0 mismatches out of 200,100 test cases** `[V]`. The decompiled
logic is a mathematically faithful, non-broken implementation of the overflow check.

**Verdict: `avb_safe_add_to`'s overflow check (the guard O1/O2 target) is confirmed
present, unmodified, and correctly implemented in `elk_inner.elf`.** No evidence of
weakening.

### 6.4 `avb_vbmeta_image_verify` — full function match

`FUN_128d6b60` is `avb_vbmeta_image_verify` itself, confirmed by matching, in sequence,
multiple exact structures from real upstream `libavb/avb_vbmeta_image.c`:
- `if (param_2 < 0x100)` → `if (length < sizeof(AvbVBMetaImageHeader))` (0x100 = 256 =
  the real header size).
- A 4-byte compare call right before it → `avb_safe_memcmp(data, AVB_MAGIC, AVB_MAGIC_LEN)`.
- `if (((local_12c & 0x3f) == 0) && ((local_124 & 0x3f) == 0))` — the De Morgan-negated
  form of `(auth_block_size & 0x3f) != 0 || (aux_block_size & 0x3f) != 0`
  ("Block size is not a multiple of 64").
- Two calls to `FUN_128d5bc0(&running_total, size_a, size_b)` immediately after — exactly
  `avb_safe_add(&vbmeta_size, sizeof(AvbVBMetaImageHeader), auth_block_size)` followed by
  `avb_safe_add_to(&vbmeta_size, aux_block_size)` (§6.3's confirmed function).

Tracing the rest of the function's body confirmed: an algorithm-type branch matching
real libavb's `AvbAlgorithmType` enum (1-3 = SHA256 variants, 4-6 = SHA512 variants);
`FUN_128d5a50(...)` as the computed-hash-vs-stored-hash comparison
(`avb_safe_memcmp`); `FUN_128db250(...)` as the RSA signature-verification call
(matches `avb_rsa_verify()`'s signature); and output-parameter writes on success only.

**Verdict: `avb_vbmeta_image_verify` is present in full and matches real upstream
`libavb` end-to-end** — magic check, length check, version check, block-size-alignment
check, safe-add total-size computation (§6.3, empirically verified correct), algorithm-
based hash computation, hash comparison, RSA signature verification, and the
success/output path. A complete, not piecemeal, positive result.

### 6.5 Version skew: `elk_inner.elf` enforces libavb 1.1, live device reports 1.2

The local-variable struct layout feeding the version check in `FUN_128d6b60`
(`local_138`/`local_134`/`local_130`, populated by `FUN_128d7230` —
`avb_vbmeta_image_header_to_host_byte_order`) exactly matches
`magic`/`required_libavb_version_major`/`required_libavb_version_minor` in that order;
`local_134 != 1` is the major-version check (`AVB_VERSION_MAJOR == 1`) and
`1 < local_130` compares the image's `required_libavb_version_minor` against this
binary's own compiled-in `AVB_VERSION_MINOR = 1`.

**`elk_inner.elf` (kernelflinger, the early-boot-stage verifier) enforces compatibility
with libavb 1.1, not 1.2.** History: a live `/cache` dump of Y181.3.2 shows
`ro.boot.avb_version=1.2` and `ro.boot.vbmeta.avb_version=1.1` — the vbmeta prop matches
this kernelflinger-enforced value (**corrected 2026-11-12**; an earlier draft of this
finding had the two props' values swapped). Which component sets
`ro.boot.avb_version=1.2` is unverified (`[U]`, "a later-stage GHS-side check" is a
guess, not confirmed) — so "two boot stages verify against two different libavb minor
versions" remains an inference, not a confirmed security finding. Not yet explored:
whether any vbmeta feature/flag introduced between 1.1 and 1.2 would go unenforced by
kernelflinger's earlier-stage check.

### 6.6 Still open after this RE pass

- `avb_safe_add_to` was found by tracing a caller, not by a standalone-function search —
  worth checking whether every other call site is equally inlined/findable, or whether
  this was the only accessible instance.
- The hash/hashtree descriptor inner sub-fields (`partition_name_len`, `salt_len`,
  `digest_len` sum-vs-`num_bytes_following`, O3's remaining half) and the boot-image
  kernel/ramdisk bound checks (O5) have not been located in the decompiled corpus.
- TOCTOU (§1, T1–T3): unaffected by this section — still requires hardware or full
  platform emulation to confirm, per §5 item 4.
- `.ota_update.data` (700 bytes) was never dumped/searched for an indirect string-
  dispatch table in the parallel `.ota_update.text` investigation — out of scope for
  this doc (OTA opcode/frame-layout work belongs to
  `RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md`, not here).

---

## Open Conflicts

**VMM1/.vmm1 task-code bitness (unresolved, not closed by §6).** GT-verified 32-bit ELF
class for the `.vmm1` *container* (file offset 636 of `85098662`, `e_ident[CLASS]=01`,
`e_machine=EM_386`) vs. byte-level disassembly of `.vmm1.text`/`.ota_update.text` *task
code* that only decodes cleanly as 64-bit: 8 of 140 Ghidra-identified `.vmm1.text`
function entry points (`0x8ac, 0x92a, 0xb40, 0xc60, 0xdb0, 0x123f, 0x1468`, plus the
shared entry stub) decode under a 64-bit interpretation as complete, valid instructions
with textbook x86-64 prologues (`push rbp; mov rbp, rsp`, `push rbx; mov rbx, rdi`,
`mov rax, qword fs:[0x80]` — an x86-64-only TLS/stack-guard idiom with no 32-bit
equivalent), while the 32-bit interpretation of the same bytes desyncs into garbage
(stray `0x48` REX.W prefix bytes decoding as standalone `dec eax`). The same pattern was
independently confirmed for `.ota_update.text` (byte-for-byte identical shared entry
stub, same clean-64-bit/garbage-32-bit split, a `call` landing exactly on a
Ghidra-identified function in both modules). This is explicitly flagged
DISPUTED/UNRECONCILED by the source investigation itself and never closed.

**Do not read §6's `elk_inner.elf` pivot as resolving this.** §6 answers a different
question — *which binary* holds the real, actively-referenced AVB guard implementation
(`elk_inner.elf`, not `.vmm1`) — not *what bit-width* `.vmm1`/`.ota_update`'s own task
code executes as. `elk_inner.elf` itself was decompiled as a plain 32-bit import
(`x86:LE:32:default`) with no bitness dispute raised anywhere in that work (see §6.1's
closing note); the two findings sit side by side without one settling the other. Both
bitness readings for `.vmm1`/`.ota_update` task code are kept here, unresolved, pending
a real disassembler re-run under the 64-bit interpretation (`x86:LE:64:default` /
`r2 -b 64`) against the full corpus — tracked as a next step in
`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`'s absorbed history subsection, not here.

**Practical implication for this doc's fuzz targets, kept unresolved:** if the 64-bit
reading is correct for whichever binary actually runs this parser, the "32-bit build"
premise behind O1/O2's `CONCAT44`/dword-pair-arithmetic overflow theory (§2, §0's "why
32-bit matters") needs re-examination — a genuine 64-bit `uint64_t` add does not have the
same 32-bit-truncation failure mode being fuzzed for. This is noted as a consequence, not
resolved.

---

## Appendix — source artifacts

- `research/decompiled/vmm1_decomp.txt` — vbmeta/rollback error strings + `%lu` format.
- `research/scripts/avb_audit.py` — libavb CVE-pattern marker list (confirms libavb + which overflow strings are present).
- `research/reports/avb_audit.out` — archived run (failed: no PyGhidra originally; later rerun via PyGhidra against the real loaded `.vmm1` program produced zero xrefs, see §6.1).
- `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md:490-570` — A/B misc struct, vbmeta flow, boot-image header.
- `research/BOOT_CHAIN_ANALYSIS.txt:423-443` — Android boot image field offsets.
- `research/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt:160-390,664-701` — rollback mechanism, misc CRC-only, 32-bit x86 container class, rollback_index@0x70.
- `research/decompiled/vmm1_all.c` — 32-bit CONCAT44 dword-pair arithmetic idiom; `0x200` (×512) literals at lines 4558/4574.
- `research/decompiled/elk_strings.txt` — the full `libavb` guard-string set found in `elk_inner.elf`, not `.vmm1` (§6.1).
- `elk.asm` — the 287k-line `objdump -d -M intel` disassembly of `elk_inner.elf`, the only remaining copy of that binary's content (source `elk.bin` is a broken symlink); basis for the §6 reconstruction and decompilation.
- `GHS_VMM1_OTA_UPDATE_RE_STATUS_AUG2026.md` — retired; its tool-setup/status narrative is absorbed into `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` as a dated history subsection, its AVB-guard-verification findings are absorbed into this doc's §6.
