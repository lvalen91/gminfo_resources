# CVE and Attack Surface Analysis — GM Info 3.7 (gminfo37)
**Date:** 2026-06-29  
**Scope:** 68 CVEs analyzed, 33 key findings, 37 novel attack vectors  
**Analyst note:** Android 12 (API 32), kernel 4.19.305 (compiled 2024-01-25, rebuilt 2025-07-22), **SPL 2025-06-05** (confirmed: `ro.build.version.security_patch` from Jun 2026 live enumeration). CVE advisories assuming Android 10 or GKI 5.4/5.10 are inapplicable; flagged inline.

> **Correction (2026-06-29):** An earlier draft of this document stated "GM SPL Feb 2023." This was wrong. The confirmed SPL is **2025-06-05**. This moves CVE-2023-20963 from TIER 2 (VULNERABLE) to Section 6 (NON-APPLICABLE). SPL covers Android framework patches only — kernel-level CVEs are still governed by the kernel version (4.19.305).

Two facts dominate all CVE applicability decisions:
1. **GHS HOSTOS (85098662) is byte-for-byte identical between Y177 and Y181.** The misc/vda9 rollback counter is the only discriminator between builds.
2. **The cause of Y177 permissive SELinux is the VIP RH850 security function at `0xb67d0`** — a 4-byte stub in Y177, 906-byte validator in Y181. Patching `0xb67d0` achieves the permissive-SELinux goal without a downgrade.

---

## Section 1 — High-Priority CVEs

Ranked by: (a) version-confirmed applicability to 4.19.283/4.19.305 + Android 12, (b) reachability from uid=2000 ADB, (c) advancement of the downgrade/SELinux goal.

### TIER 1 — Version-Independent, Reachable, Directly Advance Goal

#### CVE-2024-53197 + CVE-2024-53150 — ALSA USB-audio OOB Write / OOB Read
- **Patch status:** Fixed in 4.19.325 (Dec 2024). **Both 4.19.283 and 4.19.305 are VULNERABLE.**
- **CISA KEV:** Yes — active in-the-wild Android exploitation.
- **Delivery:** Physical USB-A port. Crafted device with malformed `bNumConfigurations` / short `bLength` clock descriptor.
- **Impact:** Kernel code execution → disable SELinux enforcement and dm-verity in kernel memory → write path to misc/vda9 without eMMC chip-off.
- **Pairing:** CVE-2024-53150 (OOB read, KASLR defeat) + CVE-2024-53197 (OOB write, control flow). Best candidate because version-independent across both kernel targets.

#### CVE-2024-53104 — USB Video Class OOB Write
- **Patch status:** Android Feb 2025 bulletin. `CONFIG_USB_VIDEO_CLASS=y` confirmed in kernel_config.txt. Kernel compiled Jan 2024; CVE disclosed late 2024 → **patch not in this kernel build. VULNERABLE.**
- **Delivery:** Physical USB, malformed UVC descriptor.
- **Impact:** Same outcome as above. Parallel/backup to the USB-audio path on the same physical port.

### TIER 2 — Framework LPE Reachable from uid=2000 (Kernel-Agnostic)

> **This tier is now empty.** CVE-2023-20963, previously listed here, is patched (see Section 6 — Non-Applicable). No confirmed kernel-agnostic framework LPE has been identified that falls outside SPL 2025-06-05 coverage. Candidates for this tier in future research: Android framework CVEs disclosed in ASBs July 2025 – June 2026 (post-SPL window).

### TIER 3 — Only Applicable to Y175 Kernel (4.19.283); ALL PATCHED on Y181 (4.19.305)

Y181 runs 4.19.305. Every CVE in this tier is patched. Retained for reference in case Y175 access is re-established.

#### CVE-2023-6932 — IPv4 IGMP UAF *(would be tier leader on 4.19.283)*
- **Version:** Patched 4.19.301. **4.19.283 VULNERABLE; 4.19.305 PATCHED → NOT APPLICABLE TO Y181.**
- **Why it would lead:** `IP_ADD_MEMBERSHIP` on unprivileged multicast socket — no CAP_NET_ADMIN, no userns needed. Directly exploitable from uid=2000 on Y175.

#### CVE-2023-3390, CVE-2023-3776, CVE-2023-4623, CVE-2023-4921 — nf_tables + net/sched UAF Cluster
- **Version:** All patched 4.19.291–4.19.295. **4.19.283 VULNERABLE; 4.19.305 PATCHED → NOT APPLICABLE TO Y181.**
- Additionally: CVE-2023-3390 is doubly dead (`CONFIG_NF_TABLES is not set`); CVE-2023-4921 is doubly dead (`CONFIG_NET_SCH_QFQ is not set`).
- **Exploit:** Google kernelCTF PoCs (adaptable to 4.19).
- **Caveat even on Y175:** Require CAP_NET_ADMIN / user namespaces (`CONFIG_USER_NS is not set` — blocks most PoCs).

### TIER 4 — Present on Both Kernels, Gated or PoC-Immature

| CVE | Summary | Gating condition |
|---|---|---|
| CVE-2023-6931 | perf_events heap OOB write | `perf_event_paranoid` + CAP_PERFMON; PoC is panic-only, not a clean LPE |
| CVE-2024-1086 | nf_tables double-free (CISA KEV) | **Moved to Section 6 — `CONFIG_NF_TABLES is not set`, fully dead** |
| CVE-2024-36971 | net dst_cache UAF (CISA KEV) | Requires local socket context; `CONFIG_IP_MULTICAST=y` present; exploitability from uid=2000 unconfirmed |

### TIER 5 — Apollo Lake Silicon / TXE (Attacks Root of Rollback Blocker; Hardware Phase)

These attack the cryptographic root of GHS rollback enforcement.

#### CVE-2021-0146 — Apollo Lake Debug-Logic Activation *(explicitly names x7-A3960 / A39xx)*
- **CVSS:** 6.8 (AV:Physical). Physical access, ~10 minutes.
- **Impact:** Extracts per-chip FEK → derive CSE chipset key → forge CSE/TXE module auth and boot measurements.
- **GM applicability:** Unknown whether Nov 2021 OEM BIOS patch was applied.

#### CVE-2017-5707 / SA-00086 — TXE 3.0 MFS Buffer Overflow
- **PoC:** ptresearch/IntelTXE-PoC, built/tested on Apollo Lake TXE 3.0.1.1107.
- **Activation:** USB DCI → TXE JTAG.
- **Path:** Defeat TXE → spoof HECI/measured-boot to ABL → neutralize GHS rollback enforcement.

#### CVE-2019-0090 — CSME/TXE Boot-ROM (Architectural, Unpatchable)
- **Nature:** Permanent "checkm8-class" key-forgery primitive for this silicon generation.
- **Impact:** Physical DMA into unprotected CSME SRAM → forge any CSE/TXE module signature.

---

## Section 2 — Intel Key Infrastructure

**AOSP/Celadon test-key vector is REFUTED for the HLOS AVB chain.**

Evidence: OEM RSA-2048 public key extracted from SOC bootloader `.oemkeys` ELF section (file 85738845, offset 0x301288). Modulus begins `d8:04:af:e3:d3:84:6c:7e:0d:89:3d:c2:8c:d3:12:55…`, exp 65537. This is GM-specific — NOT `testkey_rsa4096.pem`, NOT `avb_releasekey.pem`. Do not pursue test-key signing for AVB.

GHS verifies vbmeta with `.mr_r_mod_android_key` (NOBITS) — delivered via Intel multiboot at boot, not present in the binary. Private key is in GM HSM; not software-extractable.

### Key Layer Posture

| Layer | Key | Replaceable? | Status |
|---|---|---|---|
| Intel CSE/TXE ROM root | Silicon-fused RSA-3072 | No | Only breakable via CVE-2019-0090 / 2021-0146 / SA-00086 |
| Boot Guard OEM KM hash | OEM RSA, hash in TXE FPF | Until `-closemnf` then permanent | **UNKNOWN** — FPF closure unconfirmed |
| BPM / SMIP signing | OEM RSA (BPMGEN2/MEU) | OEM-generated | **UNKNOWN** — possibly Intel BXT sample keys |
| HLOS AVB root | GM RSA (extracted modulus) | Build-time | **CONFIRMED GM-specific** |
| GHS HOSTOS / VIP_APP | GM TSS | Build-time | GM-controlled, private key not extractable |

### Critical Unknown: Boot Guard FPF Closure

`bxt_dbg_priv_key.pem` (Binarly "Intel OEM Platform Key / Orange Unlock" for Broxton/Apollo Lake) leaked via the MSI breach and an AAEON public GitHub repo. **If GM never generated its own BPM/SMIP keys and never closed FPF with a GM KM hash**, this key could sign a BPM/SMIP that passes Boot Guard, granting Orange debug unlock (JTAG over USB DCI) — rendering the GHS rollback counter irrelevant.

Yellow flag: SOC_BOOT (id 23) and SOC_ABL (id 72) are **UNSIGNED in the GM package** (MASTER_REFERENCE §3.1). Intel claims "CSE validates ABL internally," but this only holds under an enforcing Boot Guard profile with a GM-fused KM hash.

**Resolution:** Dump 8MB IS25WP064A IFWI SPI flash offline; run MEInfo/TXEInfo to read: Manufacturing-Mode bit, OEM Public Key Hash, Keybox provisioned status.

---

## Section 3 — New Attack Vectors (Not in Existing Ranked List)

### NEW-1 — Direct In-Place Patch of VIP `0xb67d0` via RH850 JTAG *(Highest Leverage)*
- **Hardware:** Renesas E10A-USB (~$150), CS+ IDE, QFP-144 probe points (TCK/TMS/TDI/TDO/TRST).
- **Precondition:** OCD security fuse unblown (moderate-to-high probability on production IVI).
- **Action:** Replace 906-byte Y181 validator at `0xb67d0` with Y177 4-byte stub (`mov 0,r10; jmp [lp]`).
- **Effect:** VIP reports "debug/permissive" over `SERIAL_IPC_PROTO_KEY_CHANNEL` exactly as Y177 → permissive SELinux on Y181, zero misc/AB0 modification required.
- **Bonus:** Reveals J6_CDD/OBBPELK ELK trigger format live.

### NEW-2 — Exploit CRC-Warning-Only Behavior in misc/AB0
- **Evidence:** `VMM: Warning: A/B metatdata CRC failure!` (ghs_str.txt:43973) is classified **Warning**, not Error/Fatal.
- **Hypothesis:** GHS warns-and-continues on CRC mismatch → no CRC recalculation required to lower the rollback counter.
- **Prerequisite:** Any write path to misc/vda9 (dealer mode, kernel LPE, or diagnosticsd RCE).

### NEW-3 — USB Kernel LPE (CVE-2024-53197/53104) → Online misc Write
- **Delivery:** Physical USB-A port; crafted malicious USB peripheral.
- **Effect:** Ring-0 → write misc/vda9 or reflash VIP_APP — provides the write primitive NEW-2 needs without chip-off.

### NEW-4 — gm_protokey Software Bypasses (uid=2000, Cheapest First)
- **(a)** `ro.boot.bootreason=warm` → gm_protokey reportedly skips seed→key validation.
- **(b)** Delete `/data/vendor/gm/security/.validation` → TOFU re-provisioning with researcher PAL key.
- **(c)** Write to `/data/gmprotokey/trigger/` → re-key oracle (path is shell-writable).
- **Effect:** Opens DiagnosticsService + UDS `$27` SecurityAccess → diagnosticsd.

### NEW-5 — diagnosticsd Source-Address Spoofing + readHeader malloc-before-check
- **(a)** 8-byte framing: `[SRC:2 BE][TGT:2 BE][LEN:4 BE][UDS payload]`. Send SRC=0x00FA (factory tester address); compare NRC vs SRC=0x0001. Changed NRC = trust-tier routing confirmed.
- **(b)** `readHeader()` may `malloc(PAYLOAD_LEN)` before bounds-checking — heap corruption in uid=0, ALL caps, no-seccomp, no-NoNewPrivs daemon. Confirm in Ghidra before exploiting.

### NEW-6 — RSA-1024 Private Key in ghs_integrity.elf (Offset 12924442)
- **Status:** Function unknown. Only private key in entire corpus. 609 bytes, sha1=78d9a50f.
- **Value:** If it signs any GHS-accepted artifact (lifecycle blob, ELK payload, IPC auth token), unique signing primitive present on every unit.
- See `research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md`.

---

## Section 4 — Existing Vector Re-Rankings

| Existing vector | Movement | Driver |
|---|---|---|
| **#3 Offline eMMC chip-off** | **Strongly elevated / de-risked** | NEW-2 may eliminate CRC recalc; NEW-3/NEW-5 provide online write path → chip-off becomes fallback |
| **#4 ELK via VIP J6_CDD → HECI → ABL** | **Elevated** | SA-00086 + CVE-2021-0146 enable HECI injection; ELK bypasses AVB + GHS misc rollback; NEW-1 yields OBBPELK trigger format |
| **#1 Return-to-dealer screen** | **Mildly elevated** | USB port is NEW-3 delivery surface; dealer domain may enable misc write |
| **#5 3× boot fail → ELK** | **Neutral** | Confirmed by GHS lifecycle strings; high risk to calibration state |
| **#2 EEPROM 0x0A00** | **De-prioritized** | On Y181, `0xb67d0` is fully implemented — EEPROM bypass no longer yields permissive SELinux. Pivot: "modify 0x0A00" → "patch 0xb67d0" (NEW-1) |
| **#6 /dev/ghs/ota-isys** | **Unchanged** | Still blocked on ghs_probe build + GHS LIP ioctl RE |

---

## Section 5 — Immediate Actions (uid=2000, Ordered by Effort)

```bash
# 1. Fingerprint kernel version — gates half the CVE list
uname -r                                           # 4.19.283 vs 4.19.305 decides Tier 3 CVEs
getprop ro.build.version.security_patch            # Confirmed 2025-06-05 from Jun 2026 enumeration
id && cat /proc/self/status | grep CapEff           # CAP_NET_ADMIN? CAP_PERFMON?
cat /proc/sys/kernel/perf_event_paranoid
ls /config/usb_gadget                              # USB gadget surface for NEW-3

# 2. Probe misc/AB0 layout and write path
getenforce
ls -laZ /dev/block/by-name/misc
dd if=/dev/block/vda9 bs=4096 count=2 | xxd        # confirm "AB0" at +0x800, map rollback field

# 3. gm_protokey bypass probes (15 min, may collapse the problem)
getprop ro.boot.bootreason
ls -laZ /data/vendor/gm/security/.validation
ls -laZ /data/gmprotokey/trigger/
logcat | grep -iE "protokey|TOFU|provision|PAL"

# 4. diagnosticsd source-address spoof (30 min, pure software)
# Send [SRC=0x00FA][TGT=0x0001][LEN=1][10] to 127.0.0.1:49156
# Compare NRC vs SRC=0x0001

# 5. Reproduce return-to-dealer screen, immediately capture state
# adb shell pm disable --user 0 <critical-package>
# Then: id, getenforce, ls -laZ /dev/block/by-name/misc

# 6. Pull kernel config (stages USB LPE planning)
adb shell "gzip -dc /proc/config.gz" > gm_kernel.config
grep -E "CONFIG_SND_USB_AUDIO|CONFIG_USB_VIDEO_CLASS|CONFIG_USB_GADGET" gm_kernel.config

# 7. Build ghs_probe (NDK r25+, 2–4 h)
# See research/tools/ghs_probe/CMakeLists.txt

# 8. Acquire Renesas E10A-USB for RH850 JTAG (NEW-1)
# Concurrently: dump 8MB IS25WP064A SPI flash for Boot Guard FPF audit (Section 2)
```

---

---

## Section 6 — Non-Applicable CVEs (Confirmed Dead on Y181)

Cross-referenced against confirmed kernel config (`enumeration/Y181/jun2026/raw/kernel_config.txt`), kernel version 4.19.305, and SPL 2025-06-05.

### 6.1 — `CONFIG_NF_TABLES is not set`

| CVE | CVSS | Why dead |
|---|---|---|
| CVE-2024-1086 | 7.8 | nf_tables double-free; universal PoC (99.4% success rate on 5.14–6.6); `NF_TABLES` not compiled |
| CVE-2024-53141 | 7.8 | IP sets privilege escalation; depends on nf_tables |
| CVE-2023-3390 | 7.8 | nf_tables reg_val OOB write UAF; `NF_TABLES` not compiled |

### 6.2 — `CONFIG_USER_NS is not set`

Blocks all PoCs that call `unshare(CLONE_NEWUSER)` or `clone(CLONE_NEWUSER)` — the setup gate for the vast majority of 2022–2024 public Linux kernel LPE chains.

| CVE | Why dead |
|---|---|
| CVE-2022-0847 (Dirty Pipe) | Requires kernel 5.8–5.16; Y181 is 4.19. Also requires userns for unpriv exploitation path |
| CVE-2023-3776 (net/sched cls_fw UAF) | Public PoCs require userns; also version-patched in 4.19.293 |
| CVE-2023-4921 (sch_qfq UAF) | Requires userns; also `CONFIG_NET_SCH_QFQ is not set` |
| Entire class of container-escape / namespace-pivot techniques | No unpriv namespace creation |
| Most kernelCTF/pwn2own-style 2022–2024 PoC chains | Virtually all use userns as the unprivileged entry gate |

### 6.3 — `CONFIG_USERFAULTFD is not set`

Userfaultfd is the standard timing primitive for race-condition exploitation. Its absence dramatically increases race window difficulty.

| CVE / Class | Why dead |
|---|---|
| CVE-2022-2590 (CoW dirty page UAF) | Explicitly requires userfaultfd |
| Pipe/splice uffd-race exploits (2020–2024 class) | Requires userfaultfd for timing control |

### 6.4 — `io_uring` Not Compiled

Not present in `kernel_config.txt`. Kills the entire 2021–2024 io_uring CVE wave.

| CVE | Why dead |
|---|---|
| CVE-2023-2598 | io_uring OOB write |
| CVE-2022-29582 | io_uring UAF |
| CVE-2022-2327, CVE-2022-1043, CVE-2021-41073 | io_uring family |
| All io_uring CVEs | Not compiled |

### 6.5 — Patched in 4.19.x Stable Before 4.19.305

| CVE | Patched in | Notes |
|---|---|---|
| CVE-2023-6932 (IPv4 IGMP UAF) | 4.19.301 | Patched; Y181 runs 4.19.305 |
| CVE-2023-4623 (sch_netem UAF) | ~4.19.293 | Patched |
| CVE-2023-3776 (cls_fw UAF) | ~4.19.293 | Patched + userns blocked |
| CVE-2023-4921 (sch_qfq UAF) | ~4.19.295 | Patched + `NET_SCH_QFQ` not compiled |
| CVE-2023-3390 (nf_tables) | ~4.19.291 | Patched + `NF_TABLES` not compiled |

### 6.6 — Android SPL 2025-06-05 Covers Framework CVEs

All Android Security Bulletin CVEs with disclosure/patch date on or before 2025-06-05 are patched at the framework level. This covers the full 2023 and 2024 Android bulletin waves.

| CVE | ASB date | Why dead |
|---|---|---|
| **CVE-2023-20963** (WorkSource parcel mismatch → system_server) | March 2023 | **Patched. Previously listed as VULNERABLE in this document in error — SPL was incorrectly assumed as Feb 2023.** |
| CVE-2023-21281, CVE-2023-21282 | August 2023 | Patched |
| CVE-2023-35659, CVE-2023-35674 | September 2023 | Patched |
| CVE-2023-40088, CVE-2023-40129 | October 2023 | Patched |
| All framework CVEs with ASB ≤ 2025-06 | — | Patched |

**Important distinction:** SPL only reflects Android *framework* patches. Kernel-level CVEs fixed in 4.19.x after January 2024 (the kernel compile timestamp) may not be applied regardless of SPL, because the kernel image itself was not rebuilt with those patches.

### 6.7 — Wrong Architecture (x86_64 Intel, Not ARM)

| CVE / Class | Why dead |
|---|---|
| Qualcomm SoC CVEs (Hexagon DSP, FastRPC, modem) | No Qualcomm silicon |
| MediaTek SoC CVEs | No MediaTek silicon |
| ARM TrustZone / SMC-based TEE CVEs | Platform uses Intel TXE, not ARM TrustZone |
| Samsung Exynos-specific CVEs | Not Exynos |
| ARM64-specific ISA exploits (PAC bypass, MTE bypass) | Intel Goldmont, no ARM ISA |

### 6.8 — GHS INTEGRITY Version / Service Mismatch

| CVE | Why dead |
|---|---|
| CVE-2019-7711 (INTEGRITY RTOS IPWEBS HTTP overflow) | Affects INTEGRITY RTOS **5.0.4**; GM runs INTEGRITY IoT **2020.18.19**; HTTP service not present in production IVI partition |
| CVE-2019-7712 (GHS INTEGRITY DNS) | Version mismatch; DNS service not confirmed running |
| CVE-2019-7713 (IPCOMShell Telnet heap overflow) | Telnet/shell not present in production automotive GHS partition |
| CVE-2019-7714 (IPWEBS auth header stack overflow) | Same — service not present |
| CVE-2019-7715 (INTEGRITY audit overflow) | Same |

### 6.9 — Feature / Module Not Compiled

| CVE | Config fact | Status |
|---|---|---|
| CVE-2023-4921 (sch_qfq) | `# CONFIG_NET_SCH_QFQ is not set` | Dead (also version-patched) |
| Any AOSP test-key AVB signing path | GM OEM RSA-2048 enrolled (`d8:04:af:e3…`); not `testkey_rsa4096.pem` | Dead |
| GSI/DSU boot escalation | `dontaudit gm_update_engine gsi_metadata_file` (vendor_sepolicy.cil:2672) | Silently blocked |
| WiFi ADB remote attack surface | WiFi ADB compiled out | No surface |

---

## Strategic Synthesis

**Fastest path to permissive SELinux (actual goal):** NEW-1 — patch VIP `0xb67d0` via RH850 JTAG. No downgrade, no misc modification.

**Fastest path to literal Y177 downgrade:** NEW-2 (exploit CRC-warning-only behavior in misc/AB0), enabled by a misc-write primitive from NEW-3, NEW-5, or dealer mode.

**TXE/Boot-Guard CVE cluster** (Tier 5 + Section 2 FPF unknown) defeats rollback at cryptographic root — run in parallel as the hardware-phase track.

**Cheapest next step:** NEW-4 gm_protokey probes (15 min, uid=2000, zero hardware). May collapse the entire problem stack.
