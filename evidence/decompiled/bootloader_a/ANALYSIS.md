# SOC_ABL Load/Verify Decompilation

> **CORRECTION (2026-11-18, later pass):** The checksum finding below is for the **kernelflinger
> ELF's `ipk.` handler** — the Android bootloader component, **NOT** the GHS loader. The actual
> OS/GHS loader is the **SlimBootloader Stage2 inside IBBP** (`0x8b01c`–`0xcc01c`), which does
> **verified boot with RSA signature + SHA-256 against `oem.key`/`BPM.met`** and sets a green/yellow
> boot state (strings `signature:`, `authentic…`, `oem.key`, `get key from FIT`, `sha256`,
> `retrieve hash`, `Set yellow`/`green`, `iasImage`, `native func+`, `virtual_`, `@jump`,
> `entry point`). So **GHS is signature-verified, not checksum-only.** See "Corrected chain" at end.
> codex's "IBB/SlimBootloader → GHS" was essentially right; the kernelflinger ELF is the Android
> loader, not the GHS loader.



**Date:** 2026-11-18 · **Tags:** `[C]` confirmed-from-binary, `[U]` unverified
**Source:** `bootloader_a` partition of the Y175 eMMC dump (`emmc_user_wifi.bin` @ LBA 313344, 30 MiB),
an `ipk.` package (`gm_part_number` = SOC_ABL/85738845 class). The x86 OS-loader ELF is at
container offset **`0x301288`** (matches the repo's prior SOC_ABL note).

Settles the previously-`[U]` question: *is GHS cryptographically authenticated by SOC_ABL, or
integrity-checked?* **Open Conflict #1 / the "Verifies GHS signature" label.**

## Artifacts in this folder
- `soc_abl.elf` — carved OS-loader (ELF32 x86, base `0x12800000`, 1047228 B, stripped, Multiboot1).
- `soc_abl_elf2.elf` — the second ELF32 at container `0x7d022c` (same base; secondary stage).
- `dispatch_table.txt` — the image-format recognizer table.
- `ipk_handler_fcn12808b00.disasm.txt` — full disasm of the ipk/multiboot container handler.
- `ipk_checksum_loop.disasm.txt` — the checksum routine.

## Key facts (all `[C]`)
- **GOT base = `0x128fd8d5`** (PIC/GOTOFF addressing; 1559 agreeing `add ebx,imm32` sites). Needed
  to resolve any data reference in this binary.
- **Format dispatch table @ `0x128dc2e8`** (.rodata) recognizes three image magics:
  `"ipk."` (`0x2e6b7069`), **Multiboot1** (`0x1badb002`), `"FB01"` (`0x31304246`). GHS (`ghs_isys`),
  `bootloader_a`, and `ghs_abl_update` are all `ipk.` containers. Dispatch is an indirect
  `call dword [handler+8]`.
- **The `ipk.` container handler is `fcn.12808b00`** (`0x128088e6`–`0x12808f02`).

## The verification is a checksum, not a signature  `[C]`
`fcn.12808b00` validates the `ipk.` container with a **32-bit additive checksum**, computed with SSE:

```
0x12808a74..0x12808b25   movdqu xmm,[ebx+esi*4] ; paddd ...   ; vectorized dword summation
0x12808b6a..0x12808b80   paddd/pshufd horizontal reduce → movd edi, xmm0   ; edi = Σ dwords
0x12808b88               cmp edx, eax                                        ; compare to stored
```

This matches the `ipk.` header checksum field (`+0x18`, e.g. `0x5fffc6f3` on `ghs_isys_a`). It is an
**integrity check, not a cryptographic hash or RSA signature**. The handler's call targets contain
no BoringSSL/SHA-256/RSA/AVB routine.

Corroborating structural facts from the dump:
- `ghs_isys_a` IPK header carries **only** a checksum — **no embedded RSA signature block**.
- **No vbmeta covers `ghs_isys`**: `vbmeta_a` is Android-only (boot/system/vendor/product/dtbo/acpio);
  no separate GHS vbmeta partition exists; the two `AVB0` hits inside `bootloader_a` are false
  positives (ASCII inside `.../intel/kernelflinger/...` path strings).
- SOC_ABL *does* link libavb (`avb_slot_verify.c` @ `0x128f5a08`) and BoringSSL RSA/SHA-256, but that
  machinery is on the **Android `boot_a`** path, not the GHS container load.

## Conclusion & status
**The SOC_ABL step that loads GHS authenticates the GHS container with a dword-sum checksum only —
integrity, not cryptographic authentication.** This *contradicts* the architectural label
"SOC_ABL verifies GHS signature" (`GHS_BOOT_…:323`) and resolves Open Conflict #1 toward
**integrity-gated, not signature-gated**, at the SOC_ABL→GHS boundary.

### Honest caveat (`[U]` — not yet closed)
The checksum is confirmed as the *container-level* gate. Not yet exhaustively ruled out:
1. a GHS image hash stored in a **signed manifest** checked elsewhere in the boot flow (e.g. an RBE
   `$MN2`/`RbeVerifyHashSha256` path — that string lives in the CSE portion of `bootloader_a`, not in
   `soc_abl.elf`), or
2. a hash check in the indirect `call [handler+8]` leaf loader not yet traced.

If neither exists, GHS is integrity-only → a modified `ghs_isys` with a corrected checksum would pass
SOC_ABL. The decisive confirmations: finish the caller/leaf-handler trace, **or** the empirical
bench test (flash a 1-byte-modified `ghs_isys_a`; boots ⇒ integrity-only).

Boot order confirmed this pass (independent of the above): **CSE/Boot Guard → IBB Stage1
(loads `bootloader_a`/`osloader.bin`) → SOC_ABL → GHS → `boot_a` → AAOS** — matches `boot_chain.md`,
not "IBB → GHS → bootloader_a".
