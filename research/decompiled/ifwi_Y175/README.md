# IFWI / TXE extraction — Y175 bench

Unpacked Intel IFWI (CSE/TXE region) and carved ELK bootloader from the Y175 bench eMMC dump.

**Source image:** `.../GM_research/aaos/gm_aaos/2024_Silverado_ICE/emmc_dump/Y175_bench/ifwi_mapped_ff800000_8MiB.reconstructed.bin`
(8 MiB, mapped to SPI window `0xFF800000`; carved CSE region, not a full SPI with descriptor/BIOS).

## Identification (MEAnalyzer v1.312.0 r378)

| Field | Value |
|---|---|
| Family | **CSE TXE** (gen 3), chipset **APL** stepping B |
| Version | **3.1.95.3140** (Flash Image Tool 3.1.95.3140), signed 2023-07-06 |
| Release | Production, Production-Ready yes |
| SVNs | TCB 3 / ARB 7 / VCN 112 |
| Validation | all partition RSA signatures + module hashes **VALID** |

Neither the CSE TXE nor the PMC is in MEAnalyzer's DB (expected for a GM OEM-configured part). PMC manifest version field reads `0.1.0.0` (placeholder in this reconstruction).

## Contents

- `cse_unpacked/` — full MEAnalyzer `-unp86` output: 10 partitions (SMIP, RBEP, PMCP, FTPR, UCOD, IBBP, UTOK, ISHC, NFTP, IUNP, OBBP) with per-partition `*.man.txt` manifests and per-module `*.met.txt` metadata/hashes. Key code modules: FTPR `bup`/`kernel`/`syslib`, NFTP `ptt`(fTPM)/`dal_*`(DAL/TEE)/`crypto`/`storage`, ISHC `ish_main`, IBBP `IBB`/`IBBL`, PMCP `PMCC003`.
- `elk/` — carved from `OBBP 0000 [0x501000]/ELK` (an Intel `ipk` package, 1.1 MB, 2 ELFs):
  - `abl_main.elf` — ELF32 x86, static, stripped, base `0x12800000`, ~2374 functions. **kernelflinger ABL on efiwrapper** (`efiwrapper-03.02-userdebug`). Statically links libavb (AVB) + BoringSSL (full TLS/X509/RSA/EC). A/B slots, RPMB, fastboot, secureboot, OEM-unlock, `ABL.svnseed` rollback.
  - `elf0_0x22c.elf` — same ELF32 stage, truncated at the naive split (use `abl_main.elf`).
  - `elf1_0x10a334.elf` — ELF64 x86-64, static, stripped, 40 KB; 64-bit hand-off stub.

The `ANDROID!` bytes in ELK are the boot-image magic *constant* kernelflinger compares against, not an embedded boot image.

## Reproduce

```sh
# MEAnalyzer needs: colorama, crccheck, pltable (venv). On Python 3.15 its OSC
# title write crashes colorama -> run via a shim that no-ops convert_osc; -duc
# disables a hanging online update check.
python MEA.py <image> -unp86 -skip -duc -exit   # output lands next to MEA.py

# carve ELK ELFs: ipk header 0x2c bytes; ELF#0 @0x22c..EOF, ELF#1 @0x10a334
```

Related: [`../elk_strings.txt`](../elk_strings.txt), [`platform/elk_recovery.md`](../../../platform/elk_recovery.md), [`platform/boot_chain.md`](../../../platform/boot_chain.md).
