# Boot Trust Anchor & Keys

Single owner for the **secure-boot / AVB trust anchor, its verification keys, and the
integrity-vs-authentication status of the GHS image that carries them**: the CSE/IFWI manifest keys,
the SOC_ABL (`.oemkeys`) key, the active vbmeta signing key, the GHS-embedded `current_android_key`,
AVB coverage, GHS-image authentication, and GHS self-integrity (Gate 1). Every other doc that touches
these keys/questions should point here rather than restate them.

**Evidence tags:** `[C]` confirmed by disassembly/live measurement · `[S]` static/structural
(binary/partition byte analysis) · `[FW]` firmware-stated string · `[I]` inferred · `[U]` unverified
hypothesis · `[X]` external. A dated per-claim correction overrides surrounding text.

**Build scope:** IFWI/eMMC/GHS byte facts are **Y175** (8 MiB reconstructed IFWI + full eMMC
user-area dump; byte-verified 2026-11-20) unless tagged. SOC Bootloader facts are **Y181/85738845**;
GHS string/section facts cross-check against **Y181/85098662**. VIP_BOOT/HOSTOS/ABL are byte-identical
across Y177/Y181 (`firmware_versions.md`), so Y181 key facts are treated as build-general unless noted.

**This doc does NOT own (pointers):**
- Downgrade/anti-rollback mechanism, OEM-key-extraction feasibility → [GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt](GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt)
- libavb/`.vmm1` parser RE, AVB-guard fuzz targets → [VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md](VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md)
- ELK/kernelflinger as a recovery/fastboot environment, lock state, Boot Guard/FPF → [`../platform/elk_recovery.md`](../platform/elk_recovery.md), [GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md)
- GHS hypervisor architecture, `/dev/ghs/*`, VMR grant table → [GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md)
- Full boot-phase walkthrough (VIP→CSE→ABL→GHS→AVB→AAOS) → [GM_INFO37_BOOT_CHAIN_ANALYSIS.md](GM_INFO37_BOOT_CHAIN_ANALYSIS.md)
- GHS-image tamper as a ranked attack vector → [HARDWARE_HYPERVISOR_ATTACK_VECTORS.md](HARDWARE_HYPERVISOR_ATTACK_VECTORS.md) (mechanism owned here, §9)

---

## 1. Trust-chain order

| # | Stage | Verifies | Root / key source | Tag |
|---|-------|----------|-------------------|-----|
| 0 | SoC fuse / OTP | — (immutable root) | Intel CSE fused keys, Boot Guard/FPF policy digest | `[I]` |
| 1 | Intel CSE (ME/TXE) | ME/ABL images (RSA + SHA-256, SVN anti-rollback) | CSE fused root keys | `[S]` |
| 2 | SOC_ABL / OBB (kernelflinger / ELK) | **loads** GHS; GHS image carries an RSA-2048/SHA-256 sig whose key is in the Boot-Guard OBB/ELK + CSE KM — chain closed; runtime enforcement measured via 1-byte sig-corrupt A/B boot test (§8) | CSE root → Boot Guard → OBB; OEM "OS Kernel" key | `[C]` |
| 3 | GHS INTEGRITY | Gate 1 self-integrity (§9); Android `vbmeta`+`boot` AVB (RSA-2048/SHA-256, rollback) | `current_android_key` (embedded in GHS image, §6) | `[C][FW]` |
| 4 | AAOS kernel / dm-verity | system/vendor/product (hashtree) | vbmeta descriptors | `[S]` |

- `[S]` GHS does **not** load `bootloader_a`; it directly reads GPT, `misc`, `vbmeta`, `boot`. ABL/
  firmware necessarily precedes GHS.
- `[I]` The hardware root is a fuse/policy digest, not an arbitrary key read from eMMC.

## 2. CSE / IFWI manifest keys (Y175)

CSE region identity (`research/decompiled/ifwi_Y175/README.md`): CSE **TXE gen 3**, chipset **APL
stepping B**, version **3.1.95.3140** (signed 2023-07-06), SVNs **TCB 3 / ARB 7 / VCN 112**; all
partition RSA signatures + module hashes **VALID**.

`[S]` Six IFWI manifest keys (`$MN2` headers @ `0x201074`, `0x205074`, …), byte-verified against raw
little-endian moduli. All **RSA-2048, exponent 65537**, **bare public keys** (no X.509):

| Manifest | IFWI offset | Covers |
|----------|-------------|--------|
| SMIP | `0x2010d8` | CSE firmware partition (Manifest-v2) |
| RBEP | `0x2050d8` | CSE firmware partition |
| PMCP | `0x210108` | CSE firmware partition |
| TXE OEM | `0x280080` | CSE firmware partition |
| ISHC | `0x2cb0d8` | CSE firmware partition |
| IUNP | `0x4130f0` | CSE firmware partition |

- `[S]` These `$MN2` manifests authenticate **Intel CSE firmware partitions** (FTPR/RBE/PMC/etc.),
  **not** eMMC content and **not** the GHS image (§8).
- `[S]` The reconstructed 8 MiB IFWI does **not** expose a FIT, Boot Guard Key Manifest (`$KEYM`), or
  Boot Policy Manifest (carved CSE region, not a full SPI; the flash-descriptor region at `0x0` is
  all `0xFF`).

## 3. SOC_ABL / ELK (kernelflinger) and `ghs_abl_update`

| Property | Value | Tag | Source |
|----------|-------|-----|--------|
| SOC_ABL file | `85738845`, ~6 MB signed, `ABL.secureboot=1` | `[FW]` | GM_INFO37 §5.2 |
| ABL binary | kernelflinger on efiwrapper (`efiwrapper-03.02-userdebug`), ELF32 x86 base `0x12800000` | `[S]` | ifwi_Y175 |
| Crypto | statically links **libavb** + **BoringSSL** (X509/RSA/ECDSA); `avb_slot_verify`, `avb_rsa`, rollback, public-key rejection, `.oemkeys` section | `[S]` | ifwi_Y175, Y175 analysis |
| ELK `.oemkeys` (inner ELF) | RSA-4096 AVB key blob | `[S]` | INVENTORY.md (`elk_inner.elf`) |
| SOC-Bootloader `.oemkeys` OEM key | **RSA-2048**, modulus `00:d8:04:af:e3:d3:84:6c:7e:0d:89:3d:c2:8c:d3:…`, ELF offset `0xfe8e0` (embedded ELF @ `0x301288`) | `[S]` | GHS_DOWNGRADE §8.3 |

- `[S]` The IFWI ABL ELF (base `0x12800000`) is **byte-identical** to the ABL ELF in `ghs_abl_update`.
- `[S]` `bootloader_a` and `bootloader_b` contain **byte-identical** ABL payloads.
- **`ghs_abl_update` is a firmware-reflash capsule, NOT a runtime boot stage** `[S]` (byte-verified
  2026-11-20): its IPK payload (`0x600000` = 6 MiB; header CRC `0x3597d84c`, `0x55aa` marker, **no
  signature**) is byte-identical to the top 6 MiB of IFWI/SPI (`0x200000..0x800000`). That block is
  the field-updatable Intel firmware region — `$CPD` @ `0x201000`, FTPR @ `0x20e7e0`, `$FPT` @
  `0x25ccb7`, the six RSA-2048 CSE/OEM manifests (§2), and the firmware-resident ABL ELF. The name
  reflects ABL as its headline component; the payload carries the whole updatable firmware block. The
  capsule is CRC-wrapped only — whether a reflash is authenticated depends on the updater and/or
  CSE/Boot Guard at next boot, not recoverable from this dump.
- `[C]` ELK/ABL is a fastboot-class bootloader with AVB active, **not** a Linux shell (corrected
  2026-09-10; owned by `../platform/elk_recovery.md`).

## 4. GHS AVB verification (what GHS checks on Android)

`[FW]` GHS contains Android/AVB verification code and error strings for: signer-identity match,
vbmeta signature, signed-boot presence, boot signature, rollback index, key-module presence, and
key modulus/exponent match; plus an Android signature format with **DER certificate parsing**
(version/subject/issuer/validity/RSA modulus/exponent).

| Check | Error string |
|-------|--------------|
| Signer identity | `VMM: Error: vbmeta signing key does not match known valid key` |
| vbmeta signature | `VMM: vbmeta: image verification failed!` |
| Signed boot present | `VMM: %s: no signed boot partition in vbmeta.` |
| boot signature | `VMM: Error: Android signature verification failed` |
| Rollback index | `VMM: ERROR: rollback index is too old: %lu in image, but stored is %lu` |
| Key module present | `Android signing key boot module not found` |
| Key modulus/exponent | `Signing key modulus mismatch` / `Signing key exponent mismatch` |

- `[S]` GHS CRC and SHA-1 failure paths are internal image/RAM/metadata integrity checks (see §9) —
  they do **not** replace the cryptographic Android checks.
- `[C]` vbmeta header is **stock upstream libavb**: magic `AVB0` (`41 56 42 30` @ offset 0), version
  1.1, `avbtool 1.2.0`, SHA256_RSA2048, `flags=0x00000000` (verification **not** disabled), zero
  GM-specific fields (byte-confirmed 2026-09-10). Distinct from the `\0AB0` misc/BCB A/B-metadata magic.

## 5. Active vbmeta signing key

| Field | Value | Tag |
|-------|-------|-----|
| Algorithm | AVB `SHA256_RSA2048` (RSA-2048 / SHA-256) | `[S]` |
| Public-key SHA-1 | `ccf9677f9683d9fec7dc372a9bc592a11d8e4000` (vbmeta_a/vbmeta_b) | `[S]` |
| Modulus identity | **byte-identical** to the `current_android_key` modulus embedded in GHS (§6) | `[S]` |
| Relationship to ABL `.oemkeys` | **differs** from the static ABL `.oemkeys` blobs examined | `[S]` |

- `[S]` GHS/ABL does **not** trust the key packaged inside vbmeta; it verifies against the separately
  stored `current_android_key` (§6), whose modulus matches this one.

## 6. `current_android_key` — the trust anchor, embedded in the GHS image

**RESOLVED (byte-verified 2026-11-20):** `current_android_key` is a **static key object bundled inside
each GHS IPK image** (A and B byte-identical), **not** an external/eMMC/CSE-supplied key. At runtime
GHS receives it as a Multiboot module, but the module's **origin is the GHS image itself**.

| Property | Value | Tag |
|----------|-------|-----|
| Location (ghs_isys_a) | object name @ file offset `0xe3ca7c`; 256-B RSA modulus @ `0xe3ca90`; exponent @ `0xe3cb90` = `01 00 01 00` (65537 LE) | `[S]` |
| A/B identity | GHS-A and GHS-B key regions byte-identical | `[S]` |
| vbmeta match | modulus byte-identical to the active vbmeta AVB public key (§5) | `[S]` |
| Container | payload size `0x2658` (9816 B), mapped @ vaddr `0x010dabc8`; **GHS-specific layout, NOT `AvbRSAPublicKeyHeader`**: 256-B **big-endian** modulus, LE exponent (65537), 4-B trailer tag `c6db1950` (purpose unidentified — not modulus CRC32, not AVB `n0inv`). AVB precomputed fields (`key_num_bits`, `n0inv`, Montgomery `rr`) **absent**. | `[S]` |
| On-flash region | the second **`.secinfo`** region (`vaddr 0x10dabc8`, len `0x2658`, **CRC32**-covered by Gate-1 §9) holds the key object | `[S]` |
| Runtime destination | GHS ELF section `.mr_r_mod_android_key`, NOBITS, size `0x1000`, vaddr `0x02201000` (the runtime map target; NOBITS/unchecked; key bytes live in the `.secinfo`/IPK payload, not this section) | `[S]` |
| Second embedded key | at payload offset `0x170`: apparent **RSA-4096** (512-B modulus, exponent 65537 @ payload `0x370`, then zero padding). Not the AVB key; role uncharacterized (possibly a second/OEM trust root) | `[S]` |

- `[S]` The **sole** proof that this equals the active vbmeta key is the byte-identical 256-B modulus
  plus matching exponent; no derived-field check adds to it (AVB precompute fields are absent).
- `[C]` `ProcessMultibootBootModules()` is **suggestive** of the GHS-side consumer/parser; its full
  call graph is **not** recovered. Whether the **AVB path** (`avb_slot_verify`) — vs. the legacy
  Android-signature path — consumes this module is not yet proven by a recovered call graph. The
  copy-or-map routine is not yet recovered.

## 7. AVB coverage (vbmeta_a descriptor inventory, Y175)

`[S]` vbmeta_a enumerated fully — **15 descriptors** (re-verified 2026-11-20):

| Type | Count | Covers |
|------|-------|--------|
| Property | 10 | fingerprint `gm/full_gminfo37_gb/gminfo37:12/W213E-Y175.5.2-SIHM22B-383.1`, `security_patch 2024-05-05`, etc. |
| HASH | 2 | `boot` (35,112,960 B, sha256), `acpio` (sha256) |
| HASHTREE | 3 | `product`, `system`, `vendor` (dynamic/super partitions) |

- `[S]` vbmeta contains **NO descriptor** for `ghs_isys` (nor `bootloader`, `misc`, or any `ghs_*`
  partition). **Therefore the Android AVB chain does not authenticate GHS: GHS is the AVB verifier,
  never an AVB-verified image.**

## 8. GHS-image authentication (is the verifier itself verified?)

> **CORRECTION `[C]` (2026-11-20, supersedes the verdict below): the GHS image IS cryptographically
> signed, and the public key that verifies it is rooted in the Boot-Guard chain.** The earlier "no
> signature demonstrable" verdict was wrong in one specific way — the detached-signature search (below)
> looked in sibling partitions and for a stored cleartext hash, but missed an **appended RSA signature
> block in the GHS image's own tail**, only `0x98` bytes past the `0xe3cb68` "image end" the prior pass
> had stopped at. Three findings, each re-derived from raw bytes (reproducible; re-run live 2026-11-20):
>
> 1. **A valid RSA-2048 / SHA-256 / PKCS#1-v1.5 signature over GHS exists** `[C]`. Layout in the IPK
>    image: signature @ `0xe3cc00` (256 B), modulus @ `0xe3cd00` (256 B), exponent `65537` (LE) @
>    `0xe3ce00` — the block ends at `0xe3ce04`, exactly the length of the stripped `payload.bin`
>    (14,929,412 B). Verifying `s^e mod n` (both big-endian) yields a well-formed PKCS#1 v1.5 pad with
>    the SHA-256 OID and embedded digest `7b02d1b7…113ed39db`, which equals **`SHA256(image[0:0xe3cb98])`
>    exactly**. Reproducible; confirmed ≥3× independently (`scratchpad/ias/rsa_verify.py`).
> 2. **The signing key is the OEM "OS Kernel" key, and it lives in the Boot-Guard-authenticated SPI
>    OBB** `[S]`. Key fingerprint `SHA256(reversed_modulus ‖ LE_exp)` = `e99d2f48…579beab7` (the GBUR
>    OEM "OS Kernel"/usage-0x27 key). The same modulus is embedded in the SPI **OBB/ELK @ `0x114000`**
>    (OBBP whole @ `0x114040`) and its fingerprint is in the **CSE FTPR Key Manifest @ `0x60354`**. It
>    is **absent** from IBBP and **absent** from the mutable eMMC ABL (`find_oskey.py`, re-run live).
>    So the GHS verifier's key is chained to the hardware root (CSE Boot Guard → OBB), not held in a
>    rewritable eMMC stage. **The trust chain is closed**: there is no mutable intermediate that both
>    loads GHS and carries the key to check it.
> 3. **Runtime enforcement IS empirically demonstrated by a controlled one-byte differential boot
>    test** `[C]` (2026-11-20). Two images flashed to both A/B slots, differing by **exactly one byte**
>    at the signature offset `0xe3cc00`:
>    - **Run A (stock GHS):** boots AAOS — T1 ramps to ~7,800 pkts/5 s, **no** fastboot USB device.
>    - **Run B (one signature byte flipped):** **rejected to fastboot** — `titan_gm_my22` (ABL
>      fastboot) USB device present the whole run, T1 pinned at the idle ~320 pkts/5 s, never boots.
>
>    The flipped byte is **outside** the IPK header CRC `[0:24]` and body CRC `[28:0xe3cb94]` ranges
>    (both still self-check to 0 on image B), in **no** `.secinfo`/loaded region, and covered by **no**
>    recomputable stored digest (exhaustive SHA-256/SHA-1/CRC32-MPEG2/zlib search over every
>    signature-covering range found none). So a "recomputable CRC+SHA only, no crypto" model predicts
>    B boots; it does not. The only construct the flipped byte invalidates is the RSA signature's math
>    — therefore something cryptographic gates on it. Two blind observer agents independently
>    classified the raw captures (A=booted, B=rejected). Captures:
>    `scratchpad/ias/runA_capture.txt`, `runB_capture.txt`.
>
>    **Scope of this result:** it proves a signature-dependent check *rejects* a tampered image;
>    it does **not** locate the verifying instruction. No RSA-verify routine over GHS was found on the
>    captured ABL/IAS path (a rigorous call-graph pass found none) — consistent with enforcement living
>    **upstream of the dump**, in the CSE/Boot-Guard/OBB stage that runs before ABL and was never
>    captured (SPI flash-descriptor reads all `0xFF`; RPMB not dumped). Residual: the OBB verify routine
>    is not disassembled, so a verifier logic bug is not ruled out; exact Boot-Guard fuse mode needs a
>    full SPI dump. These narrow *how/where*, not *whether* — enforcement itself is measured.
>
> Net effect on the "can a tampered GHS boot from the slot?" question: editing `ghs_isys` and passing
> the recomputable Gate-1 self-integrity (§9) is **necessary but not sufficient** — the modified image
> must also satisfy this OBB-rooted RSA signature, which is **enforced at boot** (pillar 3) and
> requires the OEM private key or a verifier logic bug. The fastboot/RAM-boot path (ELK, ACRN, custom
> kernel) remains the unauthenticated
> route for custom code and is unaffected by this. See GBUR for the signature-block layout and the
> boot-detection harness; §9 below (Gate-1 self-integrity) is unchanged and still correct.

---

**Superseded verdict `[S]` (2026-11-20, see correction above): GHS pre-execution authentication is NOT
demonstrable from the available eMMC/IFWI; the only integrity on the GHS image is a non-cryptographic
32-bit checksum.** Two anchoring mechanisms are affirmatively ruled out; the rest is "no positive
evidence from an incomplete image," not "proven absent." *(This paragraph and the bullets under it are
retained for the evidence trail; pillar 1 of the correction refutes the "not self-signed" bullet
specifically — the tail block it calls "no appended RSA signature" IS the signature.)*

- **Not self-signed** `[S]`: the ghs_isys IPK header carries a **checksum `0x5fffc6f3`**, not a
  signature (32-bit; does not reproduce as standard CRC32 over the obvious ranges; a 32-bit value
  cannot be a cryptographic authenticator). The partition past image end (`0xe3cb68`) holds **no**
  appended RSA signature or manifest — the only non-empty tail block is the `current_android_key`
  module (§6). On-eMMC GHS integrity is CRC-only. ELF starts at IPK offset `0x5c`.
- **ABL is the loader but no GHS-verification evidence** `[S]`: the ghs_isys type GUID
  `2568845d-2332-4675-bc39-8fa5a4748d15` appears in ABL (eMMC + firmware) only inside ABL's static
  **GPT partition-type/name table** — proving ABL *knows* the partition, not that it *verifies* it.
  ABL carries full crypto (AVB, `avb_rsa`, RSA/ECDSA self-tests, X.509, `Secure Boot Error - bad
  image path`, `ABL.secureboot=1`, Boot-Guard Integrity Intel/Non-Intel Key), but **no expected hash
  for ghs_isys** is in ABL tables and the whole-GHS SHA-256 is **not stored** anywhere in the IFWI.
  (`VerifyMR8onRAM` was examined and **rejected** as evidence: its neighbors are LPDDR4
  memory-training strings — "MR8" = DDR Mode Register 8, not an image check.)
- **IFWI crypto-coverage traced** `[S]`: `$MN2` manifests → CSE firmware (§2); CSE BXT IVB / Concatenated
  Manifest Hash Integrity keys → Boot Guard over Intel manifest hashes; Integrity/Confidentiality
  Intel/Non-Intel keys (adjacent to `rpmb_key`, `oem_sign`, `rot.key`, `rot_key_man`, `/home/mca`
  EOM flow) → CSE secure-storage/RPMB (HMAC+confidentiality), **NOT** image-verification (checked
  specifically because "Integrity" could be mistaken for Green Hills INTEGRITY — it is not);
  ABL AVB/`avb_rsa`/X.509 → vbmeta → boot+acpio (excludes ghs_isys). **ABSENT** from IFWI: any stored
  SHA-256/signature of ghs_isys; `$KEYM`/Boot-Policy/FIT; any SBL/FSP/OsLoader/Multiboot
  image-verification stage (SlimBoot/OsLoader/FSPH all absent); the component that loads ghs_isys is
  not in this image; flash descriptor at `0x0` is all `0xFF`.
- **Detached-signature search** `[S]`: GHS digests — whole 64 MiB partition, IPK image
  (`0..0xe3cb68`), ELF payload, and all **55 ELF LOAD segments ≥ 4 KiB**, each in SHA-256 **and**
  SHA-1 (**116 patterns**) — searched across `misc`, `vbmeta_a/b`, `ghs_storage`, `metadata`,
  `persistent`, `teedata`, `config`, `boot_a`, `ghs_log`, `update_cache` (~2 GiB OTA staging), and
  both IFWI mappings. **No match anywhere.** Since a signed manifest normally stores the covered
  component's hash in cleartext (as AVB and Boot Guard BPM do), this is a third independent line of
  evidence that no detached hash/signature over GHS exists in the captured data.
- **Blind spots** `[S]`: `super` and `data` not searched (by choice); a raw RSA/ECDSA signature that
  stores no cleartext hash is not greppable; **RPMB not captured** (`emmc_rpmb_data.bin.partial` = 0
  bytes) — the one authenticated/replay-protected store is unexamined.
- **What would settle it** `[I]`: the full SPI flash — flash descriptor, IBB/IBBL or SBL loader stage,
  and the Boot Guard FIT/KM/BPM region — or a pre-GHS boot trace. Until then, the trust in the
  embedded `current_android_key` is only as strong as the (currently unestablished) authentication of
  the GHS image carrying it.

## 9. GHS self-integrity (Gate 1) and tamper analysis

`[C]` Disassembly of the GHS self-check (x86-64; the ELF is **mislabeled `EM_386`** and must be
decoded as 64-bit). GHS protects its own image with two layered, per-region checks run over **both**
the on-flash image and the loaded RAM copy:

| Check | Routine (vaddr) | Compare | Failure string |
|-------|-----------------|---------|----------------|
| CRC32 | `0x22454c` (bitwise MSB-first, runtime polynomial) | vs 4-B trailer at region end (`0x224593`: `cmp dword [r14+r13-4], eax`) | `CRC error in FLASH, failing` |
| SHA-1 | table `__ghs_sha1digests` | vs expected per-region digest | `SHA-1 hash error in FLASH/RAM, failing` |

- Covered regions = the **`.secinfo` section** (@ vaddr `0x244000`), a linked list of **190** named
  descriptors (e.g. `.romstart` @ `0x200000`) each giving `{address, length}` and a method; the
  verify routine walks it (head @ vaddr `0x244168`). Per-region SHA-1 digest pointer is at descriptor
  `+0x28`. Full per-region table: [`../research/decompiled/ghs_isys_a_secinfo_region_map_Y175.txt`](decompiled/ghs_isys_a_secinfo_region_map_Y175.txt).
- `[S]` **Coverage breakdown (190 regions):** 52 CRC32 + 24 CRC32+SHA1 = **76 regions file-checked**;
  **89 NOBITS/runtime** (RAM-only, no file bytes to check on flash); **25** zero-length markers. The
  stronger CRC32+SHA1 covers `.rsyscall`, the pristine `.rom.*` per-task data copies, `.boottable`,
  and a few rodata regions; code/rodata get CRC32 only. (The RAM-side check at runtime uses the
  CRC32+SHA1 `.rom.*` pristine copies as the reference for each task's writable `.data`.)
- `[S]` The `current_android_key` container (§6) is the **second `.secinfo` region** (`vaddr
  0x10dabc8`, len `0x2658`, CRC32) — so the on-flash key object **is** inside Gate-1 CRC32 coverage,
  while its runtime copy `.mr_r_mod_android_key` (`0x2201000`) is NOBITS/unchecked. Per §9, a deliberate
  editor can still recompute that region's CRC32 trailer, so the coverage adds detection, not authentication.
- Enforcement is real: any mismatch loads the error string, logs it (`0x225a7b`), and calls a fatal
  handler (`0x21db20`) that halts. A corrupted or naively patched image is caught at boot.
- **Gate 1 is integrity, not authentication** `[C]`: every reference value it compares against is
  **unsigned data embedded in the same image** — the region-descriptor list, per-region CRC32
  trailers, the `__ghs_sha1digests` table, and the IPK header checksum `0x5fffc6f3`. No signature or
  asymmetric verification is on the self-check path (the only RSA/ECDSA in GHS is downstream AVB and
  the TEE/keymaster, neither reachable from these checks).

**Tamper consequence** `[S]`: an actor with `ghs_isys` write access can modify GHS (add/alter a
function, disable an internal check) and pass Gate 1 by any of: (1) recompute the affected region's
CRC32 trailer + SHA-1 digest + the IPK header checksum; (2) edit the region-descriptor list to exclude
the modified bytes or unlink a node; (3) NOP the fatal-halt call / flip the compare branches. None of
these touch `current_android_key` or any downstream AVB check, so **Android verified-boot state remains
valid while the verifier itself is modified.** Gate 1 provides **no** resistance to a deliberate editor;
whether a tampered image would execute reduces entirely to the upstream GHS-image authentication — and
per §8's 2026-11-20 correction, that authentication **exists**: an OBB-rooted RSA-2048/SHA-256 signature
over `image[0:0xe3cb98]` that a recomputed Gate-1 trailer does **not** satisfy. So passing Gate 1 is
necessary but not sufficient; a tampered image also needs the OEM private key or an OBB-verifier logic
bug. Enforcement is **empirically demonstrated** by the one-byte sig-corrupt A/B boot test (§8 pillar 3:
stock→AAOS, one flipped signature byte→rejected to fastboot).

## 10. Rollback / anti-downgrade key-state (pointer)

- `[FW]` `vbmeta.rollback_index = 0` in both Y177 and Y181 ⇒ not the enforcement lever.
- `[C]` GHS keeps its own rollback counter in `misc` (vda9); Y181→Y177 was written to the inactive
  slot, rejected at GHS verification, and A/B-fell-back (owner-tested FAILED).
- Full mechanism and OEM-pubkey-extraction feasibility → [GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt](GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt).

## 11. Established conclusions

1. `[S]` Not a CRC-only chain overall: IFWI/CSE, ABL, and GHS all contain cryptographic verification
   (RSA/SHA-256) **downstream**; but see §8–§9 for where only CRC/SHA-1 integrity (not authentication)
   is present.
2. `[S]` GHS verifies Android/vbmeta against `current_android_key`, whose modulus is **byte-identical**
   to the active vbmeta signer — and which is **embedded in the GHS image**, not externally supplied.
3. `[S]` The embedded modulus is present **only** in the GHS A/B images — not in `bootloader_a/b`,
   `ghs_storage`, `persistent`, or either IFWI mapping.
4. `[S]` Android AVB covers `boot`+`acpio` (hash) and `product`/`system`/`vendor` (hashtree); it does
   **not** cover `ghs_isys`/`bootloader`/`misc`/`ghs_*`. GHS is the verifier, not an AVB-verified image.
5. ~~`[S]` The GHS image is **not self-signed** (IPK CRC only); no mechanism authenticating the GHS
   image before execution is demonstrable…~~ **REVISED 2026-11-20 (see §8 correction):** the GHS image
   **is** cryptographically signed — an appended RSA-2048/SHA-256/PKCS#1-v1.5 signature over
   `image[0:0xe3cb98]` sits in the image tail (sig @ `0xe3cc00`, modulus @ `0xe3cd00`, exp 65537), and
   the signing modulus (OEM "OS Kernel" key, fp `e99d2f48…`) is rooted in the Boot-Guard-covered SPI
   OBB/ELK (@ `0x114000`) + CSE FTPR Key Manifest (@ `0x60354`), **not** in the mutable eMMC ABL. The
   chain is **closed** and runtime enforcement is **measured** `[C]` — a one-byte sig-corrupt A/B boot
   test rejects the tampered image to fastboot while stock boots AAOS (§8 pillar 3). What remains is
   only *where* the verify instruction runs (upstream/uncaptured CSE-BootGuard-OBB) and the OBB
   routine's logic, not *whether* it runs. The prior "not self-signed" line was a search miss: the
   detached-signature sweep looked in sibling partitions, not the image's own `0x98`-byte tail.
6. `[S]` `ghs_abl_update` is a firmware-reflash capsule for the top 6 MiB SPI/IFWI (CSE + ABL region),
   not a runtime boot stage.
7. `[C]` GHS Gate-1 self-integrity (per-region CRC32 + SHA-1, flash+RAM, halt-enforced) is entirely
   **unsigned/recomputable** — tamper **detection**, not authentication; no resistance to a deliberate
   editor with `ghs_isys` write access.
8. `[S]` No evidence in the analyzed eMMC or IFWI identifies **RH850 (VIP)** as the key source.

## 12. Open questions and theory *(unverified — not settled fact)*

- **GHS-IPK authentication (the root-of-trust question):** ~~unresolved~~ **largely resolved
  2026-11-20 (§8 correction).** The GHS IPK carries its own appended RSA-2048/SHA-256 signature, and
  the verifying OEM "OS Kernel" key is embedded in the Boot-Guard-authenticated SPI OBB/ELK (and
  hashed in the CSE Key Manifest). The preceding OBB stage is therefore the natural verifier, and the
  one-byte sig-corrupt A/B boot test **confirms enforcement** (stock → AAOS; one flipped signature
  byte → rejected to fastboot). What remains open is narrower: (a) **locating the verify instruction**
  — it is not on the captured ABL/IAS path (rigorous call-graph pass found none), consistent with the
  uncaptured upstream CSE/Boot-Guard/OBB stage; and (b) **disassembly of the OBB's actual RSA-verify
  routine** to rule out a verifier logic bug. Exact Boot Guard fuse/FPF mode still needs a full SPI
  dump (current IFWI region reads `0xFF`).
  >
  > **[ONLINE RESEARCH 2026-11-21] Known public CVEs / advisories for Apollo Lake TXE gen3 and Boot Guard:**
  >
  > **INTEL-SA-00086 (2017) — TXE firmware vulnerabilities:** Affects Apollo Lake Atom E3900 series (TXE 3.0.x). Fixed by **TXE 3.1.50.2222**. CVEs: CVE-2017-5705 through -5712 (buffer overflows, privilege escalation, one network-reachable via CVE-2017-5712). Attack vectors are mostly local/physical (AV:L); CVE-2017-5712 is AV:N but requires remote admin access. This unit's TXE is **3.1.95.3140** — well above the fix threshold; these CVEs are **patched**. Source: [INTEL-SA-00086](https://www.intel.com/content/www/us/en/security-center/advisory/intel-sa-00086.html).
  >
  > **INTEL-SA-00391 (2020) / CVE-2020-8705 — Boot Guard S3 sleep bypass (CVSS 7.1 High):** "Insecure default initialization of resource in Intel Boot Guard." Affects CSME/TXE **before 3.1.80**. Root cause: most OEM Boot Guard configurations validate firmware only on cold boot, not on S3 (sleep) resume. A local attacker with physical access can swap SPI flash contents during S3 sleep; the SPI flash is re-read on resume without re-verification, allowing unsigned firmware execution before OS protections are active. Intel's fix (TXE 3.1.80) reportedly adds a check on the S3 resume path. This unit's TXE **3.1.95.3140 > 3.1.80** — CVE-2020-8705 is **patched**. Sources: [INTEL-SA-00391](https://www.intel.com/content/www/us/en/security-center/advisory/intel-sa-00391.html); [Trammell Hudson's sleep attack write-up](https://trmm.net/Sleep_attack/).
  >
  > **Boot Guard FPF mode documentation:** No authoritative public document describing Apollo Lake Boot Guard FPF enforcement modes (Measured / Verified / Disabled) was located in this search pass. Intel document numbers 585819 / 632576 (Apollo Lake EDS) are not publicly available. The FPF/fuse mode question therefore **remains open** pending a full SPI dump or teardown with JTAG. The two advisories above confirm the firmware chain is in a patched state against the publicly known Boot Guard bypass vectors.
- **AVB-path consumption:** code-level proof (xrefs/decompilation) that `avb_slot_verify` — rather than
  the legacy Android-signature path — consumes the `current_android_key` module.
- **Copy-or-map routine:** the exact GHS routine that maps the embedded key into `.mr_r_mod_android_key`.
- **Second embedded key:** the role of the apparent RSA-4096 key at payload `0x170` (possibly a
  second/OEM trust root; relationship to the ELK `.oemkeys` RSA-4096 and the SOC-Bootloader OEM
  RSA-2048 not established).

## 13. Resolved (prior conflicts closed)

- **`current_android_key` storage** — *closed 2026-11-20.* Earlier docs split between "hardcoded in
  GHS at `0xe3ca34`" (`INVENTORY.md`) and "NOBITS, not in the binary, externally supplied at runtime"
  (`GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt §8.2`). Byte analysis shows each is partly correct:
  the key bytes **are** embedded in the GHS IPK payload (name @ `0xe3ca7c`, modulus @ `0xe3ca90` —
  INVENTORY's `0xe3ca34`/"hardcoded" is essentially correct), and the NOBITS `.mr_r_mod_android_key`
  is only the **runtime map destination** (GHS_DOWNGRADE's "not in the [ELF] binary" is true of the
  ELF sections but not of the IPK payload). The module's origin is the GHS image, not an external
  supplier. "BG-locked" is **not** established — GHS-image authentication is unproven (§8).

## Provenance / sources

- Y175 IFWI (8 MiB reconstructed, SPI window `0xFF800000`) + full eMMC user-area dump; CSE unpack in
  `research/decompiled/ifwi_Y175/`. GHS Gate-1 / key-object / AVB-coverage byte analysis: 2026-11-20.
- GHS `85098662`, SOC Bootloader `85738845` (Y181): `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`,
  `GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`, `BOOT_CHAIN_ANALYSIS.txt`, `INVENTORY.md`.
- Live Guest exposure (`AndroidKeyVMR`, 256-B RSA-2048): `USB_ADB_SESSION_FINDINGS_2026-10-10.md`.
- GHS string table: `research/decompiled/ghs_str.txt`. Boot-phase context: `GM_INFO37_BOOT_CHAIN_ANALYSIS.md`.

*Created 2026-11-20; revised 2026-11-20 with byte-verified GHS key-object, AVB-coverage, GHS-image
authentication, and Gate-1 tamper findings. Consolidates trust-anchor/key facts previously scattered
across the docs cited above; those docs are being converted to pointers to this one.*
