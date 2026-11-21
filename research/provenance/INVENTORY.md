# Research Artifacts Inventory

**Scope:** directory manifest of derived/extracted artifacts from the gminfo37 (2024 Silverado
ICE) reverse-engineering project (replaces volatile `/tmp` storage), plus the external-tooling
clone/PDF appendix. **Not here:** trust-chain/boot-chain analysis (→ GM_INFO37_BOOT_CHAIN_ANALYSIS.md,
`../../platform/vip_ipc_ghs.md`), key-offset/EEPROM detail (→ EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md),
bypass-technique analysis (→ `../../platform/security.md`), or the VIP/ELK trigger finding
(→ GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) — those sections restated other docs and are pointers
only, see "Analytical sections" below.

**Total size at last count: 6.3GB**, of which 211MB was `ct5_extracted/` (2026 Cadillac CT5 /
Qualcomm SA8195AU — wrong platform, not gminfo37; omitted from this manifest per the reader report that flagged it mis-filed.
The directory is unchanged on disk; it belongs in a CT5/Cadillac-platform inventory, which
does not exist in this tree).

## firmware_carved/ — 5.7GB
Carved/decompressed firmware from OTA modules

| File | Source | Description |
|------|--------|-------------|
<!-- corrected 2026-11-21: "stripped" and "x86" were both wrong per GHS_FILE_MAP_85098662.md and GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md -->
| `ghs_integrity.elf` | Y181/85098662 | GHS INTEGRITY hypervisor (14.93 MB; ELF32/EM_386 container but **x86-64 code** — disassemble as `x86:LE:64`, not i386; **not stripped**: 18,035 kernel-AS symbols in section 66, server address spaces have no symbols; `current_android_key` name string at ELF offset 0xe3ca20, 256 B key at 0xe3ca34) |
| `elk.bin` | extracted from SOC_ABL OBBP partition | Intel kernelflinger-07.02 with Harman ipk wrapper (1.06MB). **Correction (2026-09-10):** this is a `fastboot`-class Intel Kernelflinger bootloader with AVB active, **not** a Linux shell/USB-rootfs environment — that trait belongs to the GWMv2 sibling platform only (GitHub issue #1, @DymOK93), not to GM. |
| `elk_inner.elf` | elk.bin offset 0x22C | Inner ELF: kernelflinger + libavb + BoringSSL + .oemkeys RSA-4096 |
| `vip_boot.bin` | Y181/85056831 stripped | Renesas RH850 VIP bootloader (1.93MB, contains Harman SBAT pubkey @ 0x29f1) |
| `vip_app.bin` | Y181/86331656 stripped | Renesas RH850 VIP application (1.93MB, AUTOSAR Classic; OS kernel unidentified) |
| `vmlinux_y181` | Linux kernel from boot.img | 42.6MB stripped ELF, 4.19.305-240125T-gf1edde901aa7 (CONFIG_GM_SIGNATURE=y, GM signature kernel subsystem built in at ~0x1f61500) |
| `y181_kconfig.txt` | IKCONFIG from vmlinux | 6456 lines of CONFIG_* flags |
| `SOC_BOOT_extracted/` | Y181/86331652 | Android boot.img unpacked: kernel, ramdisk (LZ4), second-stage VBT |
| `SOC_PRODUCT_extracted/` | Y181/86331636 | Android product partition (ext4) — 2.7GB raw image |
| `SOC_SYSTEM_extracted/` | Y181/86331654 | Android system partition (ext4) — 3.2GB raw image |

## keys_extracted/ — 52KB
All cryptographic keys extracted from various artifacts

| File | Origin | Type | Notes |
|------|--------|------|-------|
| `rot.key` | SOC_ABL FTPR @ 0x7f01c | $MN2 manifest, RSA-2048 | Intel CSE Root of Trust (vendor 0x8086, dated 2016-04-02) |
| `oem.key` | SOC_ABL FTPR @ 0x8001c | $MN2 manifest, RSA-2048 | Harman OEM enrollment (modulus a178eb3e..., dated 2018-06-26) |
| `ibbp.man` | SOC_ABL IBBP @ 0x8c08c | $MN2 manifest, RSA-2048 | IBB signing key (dated 2024-07-12) |
| `csm_cert.der` / `csm_pub.pem` | 86331665.smd cert chain | RSA-2048 X.509 | GM Code Signature Server (CN=GM, valid 2014-2064) |
| `ghs_pubkey_*.pem` (4 files) | ghs_integrity.elf @ 14607467/489/153/175 | RSA-1024 SPKI | AOSP Android Software Attestation Root + Intermediate (PUBLIC keys, private halves in AOSP source) |
| `KEY1.pem`, `KEY2.pem`, `.der` | Same as above (alt extraction) | RSA-1024 | Same keys, alternate format |

## ../../evidence/decompiled/ — 17MB
Ghidra/r2 decompilation outputs

| File | Description |
|------|-------------|
| `sa015bcr_decomp.c` | Full decompilation of sa015bcr.dll (UDS $27 level 0x15 algorithm) |
| `ivcspsa_decomp.c` | Decompilation of ivcspsa.dll GetPsaKey + helpers (115KB) |
| `vmm1_all.c` | 140 vmm1 functions decompiled (UNUSABLE due to Green Hills toolchain — no string refs) |
| `vmm1_decomp.txt` | Initial VMM1 analysis report |
| `ghs_analysis.txt` | GHS section/function inventory |
| `ghs_isys_a_secinfo_region_map_Y175.txt` | Y175 GHS (`ghs_isys_a`) `.secinfo` region table: all **190** regions with vaddr/len/type and per-region Gate-1 self-integrity method (CRC32 / CRC32+SHA1 / none). Interpretation + coverage breakdown: [BOOT_TRUST_ANCHOR_AND_KEYS.md §9](BOOT_TRUST_ANCHOR_AND_KEYS.md#9-ghs-self-integrity-gate-1-and-tamper-analysis) |
| `vip_inspect.txt` | VIP_APP existing Ghidra project inspection |
| `elk_strings.txt` | All printable strings from elk_inner.elf |
| `elk.asm` | Full objdump -d -M intel of elk_inner.elf (287k lines) |

## ghidra_projects/ — 120MB
All Ghidra reverse-engineering projects

| Project | Target |
|---------|--------|
<!-- corrected 2026-11-21: GHS code is x86-64 in an ELF32 container (corrected 2026-08-26 per COMPREHENSIVE_ANALYSIS); ghs_proj and ghs32 descriptions were both misleading -->
| `ghs_proj/` | GHS hypervisor (initial pass — tried pure x86-64 ELF; ELF32 container confused Ghidra) |
| `ghs32/` | GHS hypervisor (second pass — ELF32 loaded as i386, **also wrong**: real code is x86-64; use `x86:LE:64:default` language; image base 0x00200000; superseded by the 9,424-function `x86:LE:64` project in GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) |
| `sa015bcr_proj/` | sa015bcr.dll Security Access level 0x15 |
| `ivcspsa_proj/` | ivcspsa.dll GlobalB cloud client |
| `vip_boot_proj/` | VIP_BOOT (Renesas RH850 — use the `RH850:LE:32` SLEIGH module; V850 was only an approximation) |
| `vip_app_proj/` | VIP_APP (Renesas RH850) |
| `86331656_ghidra/` | Original existing VIP_APP project (V850 approximation — superseded by the fresh `RH850:LE:32` projects) |
| `ghidra_protokey/` | gm_protokey + gm_protokey_recovery |
| `ghidra_elk/` | ELK kernelflinger |
| `ghidra_proj/DPS/` | Combined DPS toolchain (dpsvcs + dps.exe) |
| `ghidra_logs/` | Headless analysis logs |

## dps_unpacked/ — 220MB
Complete extraction of GM DPS v4.56.0000 installer

| Subfolder | Contents |
|-----------|----------|
| `dps_v4.56_extracted_dlls/` | Renamed individual DLLs: tisvcsv4.dll (5.16MB), dpsvcs.dll (3.33MB), dps.exe (1.58MB), s84.dll, sa015bcr.dll, ivcspsa.dll, dllsecurity.dll, GM_DOIP_32.dll, sale.dll, iecs.dll, IVCS5B.dll, s84.dll, ClearSBAT_DID_FFdata*.bin |
| `cab_full_extraction/` | All 160 GUID-named files from MSI CAB |
| `msi_metadata/` | Complete MSI table exports (File, Component, Registry, etc.) |
| `dps_install/` | Original installer hierarchy |
| `dps_rar/` | RAR variant of installer |

## ../../tools/analysis-scripts/ — 72KB
Custom analysis scripts created during research

| Script | Purpose |
|--------|---------|
| `ghs_dump.py` | Initial GHS Python dump script (PyGhidra) |
| `GhsDump.java` | GHS Java Ghidra script |
| `Decomp.java` / `DecompExports.java` | Targeted decompilation scripts |
| `DumpVmm.java` | All-vmm1-functions decompiler |
| `VipInspect.java` | VIP project inspector |
| `r2script.txt` | radare2 batch commands |
| `avb_audit.py` | AVB CVE-pattern audit (Ghidra PyGhidra) |
| `forensic.py` | Trust artifact forensics |
| `crypto_scan.py` | Crypto material discovery |

## ../../evidence/reports/ — 576KB
All analysis reports and logs

| File | Description |
|------|--------------|
| `forensic_out.txt` | Full forensic analysis output |
| `crypto_findings.json` | 1,716 crypto artifacts identified (mostly false positives, real keys catalogued separately) |
| `ghidra*.log`, `*.log` | Headless analysis logs |
| `file_map.tsv` | MSI File table → CAB GUID mapping |

---

## Analytical sections (moved out — pointers only)

Four analytical sections that restated findings owned elsewhere were replaced with pointers
(corpus rule: contested topics get a pointer, not a copy):

- **Trust chain** (immutable software-only boot/signing chain, Intel CSE → rot.key → oem.key →
  IBBL/ELK → GHS → current_android_key/VMM1) → see GM_INFO37_BOOT_CHAIN_ANALYSIS.md and
  `../../platform/vip_ipc_ghs.md`.
- **Key locations** (cert/key offset table: GM CSM root, Harman OEM key, ELK AVB anchor,
  vbmeta verifier, AOSP attestation chain, GM signature kernel subsystem) →
  see EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md.
- **Bypass paths** (EEPROM byte flip, cmdline bootreason=warm, `.validation` delete,
  `gm_protokey_recovery_prop`, `/data/gmprotokey/trigger/`) → see `../../platform/security.md`.
- **VIP/ELK findings** (Channel-7 serial-IPC ELK/reboot trigger, RID=0xFF01/sub 0x01,
  `FUN_000641c2`@0x64208) → see GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md, which owns the
  live-tested ELK-trigger fact.

## Definitive blockers for software-only trust replacement
- ISSI SPI replacement won't bypass AVB (`current_android_key` hardcoded in GHS — **confirmed 2026-11-20**: embedded in the GHS IPK payload, ghs_isys_a name @`0xe3ca7c`/modulus @`0xe3ca90`, byte-identical to the active vbmeta key; see [BOOT_TRUST_ANCHOR_AND_KEYS.md §6](BOOT_TRUST_ANCHOR_AND_KEYS.md#6-current_android_key--the-trust-anchor-embedded-in-the-ghs-image)). **UPDATED 2026-11-20:** GHS-image authentication **is** demonstrated — the GHS IPK carries an appended RSA-2048/SHA-256 signature (sig @`0xe3cc00`) over `image[0:0xe3cb98]`, and the signing OEM "OS Kernel" key is rooted in the Boot-Guard-covered SPI OBB/ELK (@`0x114000`) + CSE Key Manifest (@`0x60354`), **not** in mutable eMMC. A `ghs_isys` write that passes the recomputable Gate-1 self-integrity (§9) still fails this OBB-rooted signature — so the key/verifier **cannot** be silently altered without the OEM private key or an OBB verify-routine bug. Enforcement is **empirically demonstrated** — a one-byte sig-corrupt A/B boot test boots AAOS from stock but is rejected to fastboot when a single signature byte is flipped. What is still open is only *locating* the verify instruction (upstream/uncaptured CSE-BootGuard-OBB) —
  see `evidence/session-logs/RESEARCH_STATE_MAP_JUN2026.md:201`.
- All trust roots sit in BG-locked binaries (Harman/Intel/GM HSM keys required).
- Modifying any partition triggers a downstream signature/hash check.
- A software-only path requires either HSM key compromise or a parse-bug exploit chain
  (volatile per-boot).

## Mempalace reference
Wing `gminfo37` contains ~22 drawers across rooms `architecture`, `security`,
`attack-surface`, `tooling`, `references` with full project record.

---

## External Resources Cloned (2026-06-29)
Location: ~/Downloads/github/

| Artifact | Path | Branch/Tag | Purpose |
|---|---|---|---|
| kernelflinger | ~/Downloads/github/kernelflinger | celadon/s/mr0/apollo | ABL/HECI/ELK trigger source, AVB implementation, misc/BCB boot flow |
| vendor-intel-utils | ~/Downloads/github/vendor-intel-utils | celadon/s/mr0/apollo | SELinux baseline, AAOS patch overlays (aosp_diff/aaos_iasw) |
| device-androidia | ~/Downloads/github/device-androidia | celadon/p/mr0/master | Gordon Peak config lineage (caas/mixins.spec) |
| device-intel-sepolicy | ~/Downloads/github/device-intel-sepolicy | master | Intel AAOS SELinux policy reference |
| celadon-manifest | ~/Downloads/github/celadon-manifest | master | All Celadon build manifests A10–A15 |
| intel-FSP (sparse) | ~/Downloads/intel-FSP/ApolloLakeFspBinPkg | master | Apollo Lake FSP binaries (Fsp.fd, VBT) |
| slimbootloader (sparse) | ~/Downloads/slimbootloader | master | Platform/ApollolakeBoardPkg — GPMRB reference, Stage2BoardInitLib.c |

### PDFs Downloaded (2026-06-29)
| Document | Path | Source |
|---|---|---|
| Intel APL UEFI Enabling Guide #671281 | ~/Downloads/intel_apl_uefi_enabling_guide_671281.pdf | cdrdv2-public.intel.com |

---

**Related:** GM_INFO37_BOOT_CHAIN_ANALYSIS.md, `../../platform/vip_ipc_ghs.md`,
EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md, `../../platform/security.md`,
GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md.

Last updated: 2026-09-10
