# `.vmm1` (GHS Hypervisor) AVB/vbmeta Parser — Concrete Fuzz Targets

Derived from binary artifacts only: extracted strings, section boundaries, the AVB
CVE-pattern audit script, and the standard AOSP `libavb` structure layout. **No full
disassembly was used** — the Ghidra decompile (`research/decompiled/vmm1_all.c`) is
register-level noise; the load-bearing evidence is the string table and the known
`libavb` reference layout the strings pin the code to.

## 0. What the artifacts prove

**The parser is AOSP `libavb`, statically compiled into a 32-bit x86 ELF.**
Evidence:
- `research/scripts/avb_audit.py` enumerates the exact `libavb` error strings and
  CVE-class markers the researcher hunted: `avb_safe_add` ("Overflow when adding
  values"), `avb_descriptor_foreach` ("Descriptor size is not divisible by 8"),
  "Descriptor payload size overflow", "Overflow while computing size of boot image",
  chain-partition `rollback_index_location` validation, etc.
- Confirmed vbmeta strings in `research/decompiled/vmm1_decomp.txt`:
  `VMM: vbmeta bad header: descriptors outside data block`,
  `VMM: ERROR: rollback index is too old: %lu in image, but stored is %lu`.
- `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md` + `BOOT_CHAIN_ANALYSIS.txt`: magic
  `AVB0`, version 1.1, RSA-4096/SHA-256, boot-image header field offsets, A/B misc
  layout.
- `research/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt:243,386,701`: 32-bit x86,
  statically linked; `rollback_index` field at header offset **0x70** — this exactly
  matches the standard `AvbVBMetaImageHeader`, so the *whole* header layout below is
  known-good ground truth, not a guess.

**Why 32-bit matters:** every size/offset field in the vbmeta header is `uint64_t`
big-endian, but the module is a 32-bit build. Each 64-bit compare/add is synthesized
from dword pairs (Ghidra shows the `CONCAT44(... >> 0x1f, ...)` idiom throughout).
This is precisely where "signed-vs-unsigned length math" and high-dword truncation
bugs live. No stack canaries + no ASLR means any linear overflow past a stack buffer
is directly exploitable (deterministic return-address / saved-pointer overwrite).

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
  whether `.vmm1` memcpys the aux block to private RAM before the descriptor walk. If it
  reads eMMC/DMA buffer twice, the signature check (over the snapshot) and the descriptor
  interpretation (over the live buffer) diverge.

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
vbmeta signs a *digest* of boot_a/b (hash descriptor). `.vmm1` computes/loads the boot
image hash, compares to the descriptor, then hands the image to the guest. If the boot
partition is re-read (or guest-mapped) for execution after the hash compare rather than
executed from the exact verified buffer, the hashed bytes ≠ executed bytes. Same
in-place-vs-copy question as T1.

**All three collapse to one testable predicate:** does `.vmm1` verify a *private
immutable copy*, or the live DMA/eMMC buffer? If the latter, T1–T3 are real.

---

## 2. Length-overflow targets

### O1 — `descriptors_offset + descriptors_size` 64-bit add on a 32-bit build
`avb_safe_add` exists ("Overflow when adding values"), but the port is 32-bit. Targets:
- Set `descriptors_offset = 0xFFFFFFFF_FFFFFFF8`, `descriptors_size = 0x10`. If the add
  is done as a truncated 32-bit `off+len` the wrap yields a small sum ≤ aux_size and the
  "descriptors outside data block" gate passes, then the walk dereferences
  `base + 0xFFFFFFF8...` → wild read. Mutate the **low dword and high dword
  independently** — high-dword-only mutations are the ones `avb_safe_add` misses if only
  the low 32 bits are compared.
- Same pattern for every offset/size pair: hash(0x20/0x28), signature(0x30/0x38),
  public_key(0x40/0x48), public_key_metadata(0x50/0x58).

### O2 — `authentication_data_block_size` + `auxiliary_data_block_size` total-length
`libavb` computes `sizeof(header) + auth_block + aux_block` as the total vbmeta size
("Overflow while determining total length"). On 32-bit, two `uint64` blocks each near
`0x1_0000_0000` sum-wrap. Set both to `0x8000_0000`; if total is held/compared as 32-bit
the allocation or read length underflows while the two blocks are individually accepted.
Signed-vs-unsigned: if the total feeds a `signed int` length into a read/memcpy, values
> 0x7FFFFFFF become negative → giant `size_t` on the copy.

### O3 — descriptor `num_bytes_following` % 8 + payload sub-fields
Per-descriptor: `num_bytes_following` must be `% 8 == 0` ("not divisible by 8") and must
fit the remaining descriptor block ("Descriptor payload size overflow"). Inside typed
descriptors, hash/hashtree descriptors carry their own `partition_name_len`,
`salt_len`, `digest_len`, `hash_block_size`, `image_size`. `image_size` is the eMMC read
length — a 64-bit value multiplied/aligned. Overstate `digest_len` vs. the fixed
"Digest in descriptor not of expected size" check, or set `partition_name_len` +
`salt_len` + `digest_len` to sum-wrap past `num_bytes_following`.

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

1. **Host-replica harness (recommended).** The parser is stock AOSP `libavb`. Compile
   upstream `libavb` **-m32** (matching the 32-bit x86 target) and drive
   `avb_vbmeta_image_verify()`, `avb_descriptor_foreach()`, and the boot-image bound
   checks with libFuzzer/AFL++ over the mutation set in §3. This reproduces O1–O3, O5,
   O6 and the divisibility/overflow logic. Any crash here is a candidate; then confirm
   the specific `.vmm1` build shares it. AOSP already ships `libavb` fuzzers
   (`avb_vbmeta_image_fuzzer`, `avb_slot_verify_fuzzer`) — reuse them as the corpus/harness
   base. This isolates the "signed-vs-unsigned / offset+len" class directly.

2. **Emulate the extracted module.** The ELF is 32-bit x86, statically linked, base
   `~0x00f60000` (from `vmm1_all.c` addresses). Load the `.vmm1.text`/`.rodata` sections
   into **Unicorn** (or qiling), map a fake stack + a scratch buffer holding the mutated
   vbmeta, and call the string-anchored parse functions by address. Use the
   `avb_audit.py` string→function map (rerun it under PyGhidra — the archived run failed
   only because Ghidra lacked PyGhidra, see `research/reports/avb_audit.out:50`) to get
   the exact entry points for `avb_vbmeta_image_verify` / descriptor walk / boot-image
   validate, then fuzz register/memory inputs. This catches the port-specific 32-bit
   truncation bugs the upstream build won't have.

3. **Differential check.** Diff the extracted `.vmm1` `libavb` routines against the
   matching upstream `libavb` tag (version 1.1) to see which `avb_safe_add`/`avb_safe_mul`
   guards GHS kept, removed, or mis-ported — the removed/altered guards are the live
   overflow targets. Static, no execution needed.

4. **TOCTOU (T1–T3) can only be *confirmed* on hardware / full platform emulation**,
   because the race depends on whether `.vmm1` verifies a private copy vs. the live
   DMA/eMMC buffer — a property of the surrounding hypervisor, not of `libavb`. Approximate
   it in emulation by backing the vbmeta/boot buffer with a memory hook that returns
   *different bytes* on the second read of the same address; if verification still passes
   and the walk/boot consumes the second value, the TOCTOU is structurally present.
   Full confirmation needs the misc-partition write race on a real/emulated GHS boot.

**Immediate next step:** rerun `research/scripts/avb_audit.py` under a PyGhidra-enabled
Ghidra to recover the real entry points and the in-place-vs-copy behavior around the
descriptor walk — that single fact decides whether the TOCTOU windows (T1–T3) are
exploitable or merely theoretical, and it is obtainable statically.

---

## Appendix — source artifacts
- `research/decompiled/vmm1_decomp.txt` — vbmeta/rollback error strings + `%lu` format.
- `research/scripts/avb_audit.py` — libavb CVE-pattern marker list (confirms libavb + which overflow strings are present).
- `research/reports/avb_audit.out` — archived run (failed: no PyGhidra) — rerun needed.
- `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md:490-570` — A/B misc struct, vbmeta flow, boot-image header.
- `research/BOOT_CHAIN_ANALYSIS.txt:423-443` — Android boot image field offsets.
- `research/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt:160-390,664-701` — rollback mechanism, misc CRC-only, 32-bit x86, rollback_index@0x70.
- `research/decompiled/vmm1_all.c` — 32-bit CONCAT44 dword-pair arithmetic idiom; `0x200` (×512) literals at lines 4558/4574.
