# gminfo37 Research Artifacts — Inventory

Persistent storage of all derived/extracted artifacts from gminfo37 (2024 Silverado ICE) reverse-engineering project. Replaces volatile /tmp storage.

**Total size: 6.3 GB** (mostly firmware extractions in firmware_carved/)

## firmware_carved/ — 5.7GB
Carved/decompressed firmware from OTA modules

| File | Source | Description |
|------|--------|-------------|
| `ghs_integrity.elf` | Y181/85098662 | GHS INTEGRITY hypervisor (14.93MB ELF, stripped, x86, contains current_android_key at offset 0xe3ca34) |
| `elk.bin` | extracted from SOC_ABL OBBP partition | Intel kernelflinger-07.02 with Harman ipk wrapper (1.06MB) |
| `elk_inner.elf` | elk.bin offset 0x22C | Inner ELF: kernelflinger + libavb + BoringSSL + .oemkeys RSA-4096 |
| `vip_boot.bin` | Y181/85056831 stripped | Renesas RH850 VIP bootloader (1.93MB, contains Harman SBAT pubkey @ 0x29f1) |
| `vip_app.bin` | Y181/86331656 stripped | Renesas RH850 VIP application (1.93MB, AUTOSAR Classic + uC/OS) |
| `vmlinux_y181` | Linux kernel from boot.img | 42.6MB stripped ELF, 4.19.305-240125T-gf1edde901aa7 (CONFIG_GM_SIGNATURE=y) |
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

## decompiled/ — 17MB
Ghidra/r2 decompilation outputs

| File | Description |
|------|-------------|
| `sa015bcr_decomp.c` | Full decompilation of sa015bcr.dll (UDS $27 level 0x15 algorithm) |
| `ivcspsa_decomp.c` | Decompilation of ivcspsa.dll GetPsaKey + helpers (115KB) |
| `vmm1_all.c` | 140 vmm1 functions decompiled (UNUSABLE due to Green Hills toolchain — no string refs) |
| `vmm1_decomp.txt` | Initial VMM1 analysis report |
| `ghs_analysis.txt` | GHS section/function inventory |
| `vip_inspect.txt` | VIP_APP existing Ghidra project inspection |
| `elk_strings.txt` | All printable strings from elk_inner.elf |
| `elk.asm` | Full objdump -d -M intel of elk_inner.elf (287k lines) |

## ghidra_projects/ — 120MB
All Ghidra reverse-engineering projects

| Project | Target |
|---------|--------|
| `ghs_proj/` | GHS hypervisor (initial 64-bit attempt — wrong arch) |
| `ghs32/` | GHS hypervisor (correct 32-bit i386) |
| `sa015bcr_proj/` | sa015bcr.dll Security Access level 0x15 |
| `ivcspsa_proj/` | ivcspsa.dll GlobalB cloud client |
| `vip_boot_proj/` | VIP_BOOT (Renesas RH850, V850 SLEIGH) |
| `vip_app_proj/` | VIP_APP (Renesas RH850) |
| `86331656_ghidra/` | Original existing VIP_APP project (V850, abandoned by prior analyst) |
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

## ct5_extracted/ — 211MB
2026 Cadillac CT5 (VCUUM-371.5) OTA package extracted artifacts

| Contents |
|----------|
| Qualcomm SA8195AU bootloader bundle (xbl, abl_fastboot, tz, mifs_hyp, aop, cmnlib, km5virt, NON-HLOS, BTFM) |
| QNX 7.1.0 hypervisor (mifs_hyp_la.img) |
| VCU app + bootloader + HSM (Bosch-supplied AUTOSAR Vector FBL) |
| Android 14 AAOS partition references |
| Per-module signing certs |

## scripts/ — 72KB
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

## reports/ — 576KB
All analysis reports and logs

| File | Description |
|------|-------------|
| `forensic_out.txt` | Full forensic analysis output |
| `crypto_findings.json` | 1,716 crypto artifacts identified (mostly false positives, real keys catalogued separately) |
| `ghidra*.log`, `*.log` | Headless analysis logs |
| `file_map.tsv` | MSI File table → CAB GUID mapping |

---

# Key facts at a glance

## Trust chain (immutable software-only)
```
Intel CSE silicon (QFPROM OEM_PK_HASH)
  → rot.key (Intel ROT)
  → oem.key (Harman, modulus a178eb3e)
  → IBBL/IBB/ELK (BPM hash1/hash2/hash3)
  → ELK has baked-in RSA-4096 .oemkeys
  → GHS hypervisor (signed by Harman oem.key)
       ├── current_android_key HARDCODED at offset 0xe3ca34 (RSA-2048, beef8eee)
       │   → verifies vbmeta on eMMC
       │   → vbmeta hashes/hashtree gate Android partitions
       └── VMM1 (libavb parser — Green Hills compiled, decompilation blocked)
```

## Key locations (definitively mapped)
- **GM CSM cert chain root**: in 86331665.smd (X.509 PEM)
- **Harman OEM key**: SOC_ABL/oem.key (also embedded in VIP_BOOT @ 0x29f1)
- **ELK AVB anchor (4096-bit)**: ELK .oemkeys @ 0xfe8e0 (purpose unclear — not vbmeta verifier)
- **vbmeta verifier (current_android_key)**: HARDCODED in GHS @ 0xe3ca34
- **AOSP attestation chain (4× RSA-1024)**: GHS @ 14607467/489/153/175 — PUBLIC keys
- **GM signature kernel subsystem**: BUILT-IN to vmlinux @ ~0x1f61500

## Bypass paths (confirmed)
1. **EEPROM byte 0x441 = 0xFF** → ADB enable (single-byte flip, CRC not enforced)
2. **/proc/cmdline `androidboot.bootreason=warm`** → gm_protokey skips validation
3. **Delete /data/vendor/gm/security/.validation** → TOFU re-provisioning with any PAL key
4. **Set property `gm_protokey_recovery_prop`** → GM ProtoKey recovery override (purpose TBD)
5. **Touch /data/gmprotokey/trigger/** → free recovery re-key oracle (shell-writable)

## Definitive blockers for software-only trust replacement
- All trust roots in BG-locked binaries (Harman/Intel/GM HSM keys required)
- ISSI SPI replacement won't bypass AVB (current_android_key hardcoded in GHS, BG-locked)
- Modifying any partition triggers downstream signature/hash check
- Software-only path requires either HSM key compromise OR parse-bug exploit chain (volatile per-boot)

## Pending hardware experiments
1. **ISSI 2MB SPI flash dump** — discover what's stored there (BG-irrelevant config? Additional keys? Boot Policy backup? Attestation blobs?)
2. **64GB Samsung eMMC dump** — offline access to runtime state, GHS host_os partition, current vbmeta, FBE-encrypted /data structure (won't decrypt offline)
3. **Black-box vbmeta fuzzing** on test eMMC against VMM1 libavb parser

## Mempalace reference
Wing `gminfo37` contains ~22 drawers across rooms `architecture`, `security`, `attack-surface`, `tooling`, `references` with full project record.

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

## PDFs Downloaded (2026-06-29)
| Document | Path | Source |
|---|---|---|
| Intel APL UEFI Enabling Guide #671281 | ~/Downloads/intel_apl_uefi_enabling_guide_671281.pdf | cdrdv2-public.intel.com |

## Key Binary Finding (2026-06-29)
RSA-1024 private key in ghs_integrity.elf at byte offset 12924442 (609 bytes, sha1=78d9a50f). ONLY private key in the entire corpus. Function unknown. See research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md.

Last updated: 2026-06-29
