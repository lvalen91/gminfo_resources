# Security Architecture

**Device:** GM Info 3.7 (gminfo37) — Intel Apollo Lake (Broxton), Android 12 (API 32).
Scope: SELinux/FBE/Trusty/kernel hardening posture by firmware build, ADB/ProtoKey
authentication, service-level attack-surface findings, and host firewall/network
segmentation. EEPROM memory map, I2C/GPIO tables, CAN/UDS ID tables, and deep ELK/OEMLock
forensic trace live in their own charter docs — this file keeps the *security verdict*
and links out.

**Evidence legend:** `[C]` = live-captured/confirmed on a specific unit, with device+date.
`[U]`/`[P]` = scoped finding/correction from the named source doc. UNVERIFIABLE-FROM-LIVE =
claim is build-time/off-SoC and not observable from the captured shell. Per-claim tags are
authoritative over surrounding base prose; several sections below carry dated corrections —
only the latest dated correction for a given claim is kept (see History notes).

**Related:** [`boot_chain.md`](boot_chain.md) (AVB 8-step flow, A/B+BCB structs, rollback
counter, signing hierarchy, GSI/DSU mechanism, OEMLock/TXE/Boot Guard forensic detail),
[`elk_recovery.md`](elk_recovery.md) (ELK/fastbootd/kernelflinger recovery narrative),
[`eeprom_i2c_security.md`](eeprom_i2c_security.md) (EEPROM memory map, I2C-bus table, GPIO,
local-hardware attack surface), [`vip_ipc_ghs.md`](vip_ipc_ghs.md) (GHS `/dev/ghs/*`
interfaces, VIP IPC), [`can_network.md`](can_network.md) (CAN address/signal mechanism; the UDS
service-ID table is in [`vehicle_config.md`](vehicle_config.md#uds-diagnostic-services-used-by-dps)), [`ota_update_stack.md`](ota_update_stack.md) / [`ota_programming_roles.md`](ota_programming_roles.md)
(OTA signing, install/reflash reachability), [`gmsystemui_app_gating.md`](gmsystemui_app_gating.md)
(capability-gating mechanism), `../diagnostics/*.md` and `../research/*` (full forensic
traces for findings summarized below).

---

## History: the August 2026 retraction

> **CORRECTED 2026-08-26 — authoritative sources: `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`
> §0 and `research/security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8.**
> - **No stock build runs SELinux permissive.** Y175/Y177/Y181 share a byte-identical `init`
>   that forces enforcing (`ALLOW_PERMISSIVE_SELINUX=0`); every earlier "Y177 permissive" /
>   "CVE exploitable because permissive" claim is **FALSE** and is retracted throughout this
>   file.
> - **There is no "4-byte stub."** The VIP `0xb67d0`-class validator is the full ~906-byte
>   function in all three builds; the stub finding was a fixed-absolute-address misread.
> - **The EEPROM "security" section as originally written is retracted:** `0x04A0/0x04C0/
>   0x0A40/0x0BE0/0x1A00` are not security flags, and "disasm-confirmed" on `0x0440/0x0A80`
>   is wrong. The real SBI is `0x0441` + `0x0A80` (empirically flips ADB). Memory-map detail
>   now lives in [`eeprom_i2c_security.md`](eeprom_i2c_security.md).
> - **The ADB unlock is SoC-side and unrelated to SELinux or `0xb67d0`:** EEPROM SBI → VIP
>   transmits MEC=0xFF (DID `0xF1A0`) → `gm_adb_auth_init` sets `is_secure_mode=1` → adb
>   allowed with no cloud cert.

Every section below reflects this correction; where an earlier claim is quoted it is marked
retracted in place rather than deleted.

---

## Android Security by Firmware Version

| Feature | Y175 (June 2024) | Y177 (March 2025) | Y181 (July 2025) |
|---------|-------------------|---------------------|-------------------|
| SELinux | Enforcing | Enforcing (byte-identical init; "permissive" claim retracted 2026-08-26) | Enforcing (462 denials in one logcat window — CBC, RVC, SXM, no USB/CarPlay) |
| dm-verity | Enabled | Enabled | Enabled |
| FBE (File-Based Encryption) | Yes | Yes | Yes |
| Security Patch | 2024-05-05 | 2025-03-05 | 2025-06-05 |
| Kernel | 4.19.283 | 4.19.305 | 4.19.305 |

**Runtime vs. cmdline SELinux mode (consolidated).** Every captured unit carries
`ro.boot.selinux=permissive` (or an early `enforcing=0`/`androidboot.selinux=permissive`
cmdline token) yet runs **Enforcing** at runtime — userspace/init overrides the cmdline
token, it is not a reliable measurement of effective enforcement:
- **[C] live-Y175 2026-10-05** (`W213E-Y175.5.2-SIHM22B-383.1`): `getenforce`=Enforcing, all
  179 captured `avc` lines `permissive=0`, despite `ro.boot.selinux=permissive`.
- **[C] live-Y181.3.2 2026-11-12:** `getenforce`=Enforcing, `/sys/fs/selinux/enforce`=1; all
  3596 `avc` records in the `/cache` boot-log dump (kernel 194 + main 1055 + events 2347,
  overlapping streams, not de-duplicated) are `permissive=0`, none `granted`. The retained
  cmdlines carry BOTH an early `enforcing=0`/permissive pair AND a later `enforcing=1`/
  enforcing pair (all 30 retained cmdlines); "the later pair wins" is an inference about
  kernel parsing — the runtime read is what is directly confirmed.
  > **[ONLINE RESEARCH 2026-11-21] "Last pair wins" — confirmed for kernel `selinux=` parsing; operative mechanism is the Android init override:**
  > Two independent mechanisms produce the confirmed-enforcing result, with the second being the stronger one on user builds:
  >
  > 1. **Kernel `__setup` duplicate handling (confirmed):** The kernel's `__setup` mechanism invokes the registered handler once per matching occurrence in the cmdline — it does not deduplicate. The `selinux=` handler is `selinux_enabled_setup` (compiled under `CONFIG_SECURITY_SELINUX_BOOTPARAM`), which simply calls `kstrtoul()` on the argument and overwrites the global `selinux_enabled_boot` on each invocation with no guard check. For duplicate `selinux=` tokens the **last valid occurrence wins**. This confirms the "later pair wins" inference as the correct description of kernel-side parsing. Source: kernel source `security/selinux/hooks.c`, `selinux_enabled_setup` function; `__setup` dispatch in `init/main.c` (`do_early_param` runs the handler on each occurrence, `obsolete_checksetup` returns on first nonzero for non-early handlers — the overwrite-on-each-call behavior produces last-wins). ([`torvalds/linux`](https://github.com/torvalds/linux/blob/master/security/selinux/hooks.c))
  >
  > 2. **Android init override (the operative mechanism on user builds):** Android `init/selinux.cpp` implements `IsEnforcing()` and `SelinuxSetEnforcement()`. `IsEnforcing()` returns `true` unconditionally when `ALLOW_PERMISSIVE_SELINUX=0` — which is the case on all Y175/Y177/Y181 user builds (confirmed in this doc). `SelinuxSetEnforcement()` compares the kernel's current enforcement state (`security_getenforce()`) against `IsEnforcing()`'s result and calls `security_setenforce(1)` if they differ, **forcibly setting the kernel to enforcing regardless of what `selinux=` or `androidboot.selinux=` said**. The property `ro.boot.selinux` (derived from `androidboot.selinux=permissive` in the cmdline) is only consulted by `StatusFromProperty()` inside `IsEnforcing()`, which is bypassed entirely when `ALLOW_PERMISSIVE_SELINUX=0`. Source: AOSP `system/core/init/selinux.cpp` (`StatusFromProperty`, `IsEnforcing`, `SelinuxSetEnforcement`); [AOSP SELinux implement guide](https://source.android.com/docs/security/features/selinux/implement).
  >
  > **Net:** "last pair wins" is **confirmed** as the correct description of kernel `selinux=` parsing. The runtime Enforcing state on these user builds is **primarily driven by the Android init override** (`ALLOW_PERMISSIVE_SELINUX=0` → `SelinuxSetEnforcement` forces enforcing), which acts independently and after the kernel's own parameter parsing. The two mechanisms are consistent; either one alone would produce the observed Enforcing state. The boot logs also carry
  an `ABL.secureboot=1` token (count not reproducible across re-reads: 386 raw hits vs ~188
  per a second archive pass vs 376 if a duplicate export is double-counted); `getprop
  ro.boot.ABL.secureboot` is empty at runtime, so this flag is cmdline-only, not a live
  property. Full AVB-chain/cmdline mechanism: [`boot_chain.md`](boot_chain.md#avb-verification).
- **[C] live-Y181B recovery export 2026-11-12:** `recovery/props.log` shows
  `ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`, `ro.secure=1`,
  `ro.debuggable=0`; `recovery/last_kmsg` lines 679-680 record failed attempts to change the
  read-only `ro.boot.selinux` property, and later denials explicitly carry `permissive=0`.
  The same capture records **`GM Secure ADB disabled on user build, MEC=227`** — a
  certificate-gate result, separate from SELinux enforcement/UID-0/AVB-unlock state; see
  [MEC readings](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#target-readings-root-gate-and-registration-limits-2026-11-12).

Per-build scope note: the Y175/Y177/Y181 columns above are independently CONFIRMED only on
the unit actually captured each time (live radio = Y175 on 2026-10-05, Y181.3.2 reference on
2026-11-12); cells for the other builds on a given capture date are UNVERIFIABLE-FROM-LIVE,
not disproven. **This scope is limited to the stock Y175/Y177/Y181 firmware builds** — the
real-kernel hybrid emulator intentionally boots with SELinux **permissive** by design; see
[`emulator.md`](emulator.md).

---

## Secure Boot Chain — locked-radio posture

The 5-layer trust hierarchy (Intel CSE → SOC_ABL/kernelflinger ("ELK") → GHS INTEGRITY
hypervisor → AVB → dm-verity), the AVB 8-step verification flow, the A/B metadata + BCB
C structs, the GHS-side rollback counter, and the 4-level signing hierarchy are owned by
[`boot_chain.md`](boot_chain.md#avb-verification); OEMLock/TXE/Boot Guard forensic detail and
the ELK/kernelflinger recovery narrative are owned by [`elk_recovery.md`](elk_recovery.md)
and [`../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).
This section keeps only the security verdict.

**Locked-radio runtime posture, confirmed on two separate live units:**
- **[C] live-Y175 2026-10-05:** `ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`,
  `ro.boot.vbmeta.device_state=locked`, `sys.oem_unlock_allowed=0`,
  `ro.oem_unlock_supported=` (empty), `ro.debuggable=0`, `ro.secure=1`, `ro.adb.secure=1`,
  `ro.build.type=user`, tags `release-keys`. AVB: `ro.boot.avb_version=1.2` /
  `ro.boot.vbmeta.avb_version=1.1`, `hash_alg=sha256`, digest
  `76b736ea…bb585`. Layers 1-3 (Intel CSE OTP, SOC_ABL, GHS hypervisor internals) are
  UNVERIFIABLE-FROM-LIVE (not observable from a locked user shell); the GHS image is,
  however, fully mapped from extracted firmware `85098662` (no compressed/encrypted
  code, only a 768 B key/signature tail unreadable) — `GHS_FILE_MAP_85098662.md`.
  dm-verity is CONFIRMED-INDIRECT only (dm-6/7/8 mounts, `verifiedbootstate=green`); no
  dm-verity status text was captured.
- **[C] live-Y181B 2026-11-12:** same end-state — `verifiedbootstate=green`,
  `vbmeta.device_state=locked`, `flash.locked=1`, `ro.boot.slot_suffix=_a`,
  `ro.boot.product.hardware.sku=gv221`, `ro.bootloader=2344`. Kernel
  `4.19.305-240125T145315Z`. AVB version pair: `ro.boot.avb_version=1.2` /
  `ro.boot.vbmeta.avb_version=1.1` (READ from gmlogger props; not present in
  update/ tree) — same 1.2/1.1 split seen on Y175; the vbmeta header itself
  is libavb version 1.1 / avbtool 1.2.0 (byte-confirmed, `BOOT_TRUST_ANCHOR_
  AND_KEYS.md` §4), so this is avbtool-version vs format-version, not an error.
  > **[ONLINE RESEARCH 2026-11-21] AVB 1.2/1.1 split — mechanism confirmed, existing explanation refined:**
  > Per the AOSP VINTF match-rules documentation ([source.android.com/docs/core/architecture/vintf/match-rules](https://source.android.com/docs/core/architecture/vintf/match-rules)), these two properties are set by **different components** and reflect which libavb version each used to verify AVB metadata:
  > - **`ro.boot.vbmeta.avb_version`** = libavb version in the **bootloader** (ELK/ABL, here 1.1). Set by the bootloader on successful vbmeta verification. The vbmeta header's byte-confirmed "libavb version 1.1" matches directly — ELK carries libavb 1.1 and embeds that version in the header it creates/verifies.
  > - **`ro.boot.avb_version`** = libavb version in the **Android OS** (init/fs_mgr, here 1.2). Set by Android init/fs_mgr when it re-verifies AVB metadata at the AAOS stage.
  > The 1.2/1.1 split is **normal and expected** when AAOS has been updated to libavb 1.2 while the bootloader (ELK) still ships libavb 1.1. Both report the same vbmeta structures; the minor-version difference reflects a library update on the AAOS side only. The existing "avbtool-version vs format-version" shorthand is acceptable as-is — it captures that "avbtool 1.2.0" (the tool that produced the signed vbmeta, same as the AAOS libavb 1.2) differs from the bootloader's older libavb 1.1 that also validates it. The split is not an error or anomaly, and VINTF compatibility passes (major versions match).

**Rollback protection (security framing; full mechanism in `boot_chain.md`):** GHS maintains
its own rollback counter in `misc`, independent of Android's AVB rollback index (both Y177
and Y181 `vbmeta` carry `rollback_index=0`). **Tested:** Y181 → Y177 downgrade FAILS
(partitions write successfully, GHS rejects at boot, A/B fallback reverts slot); Y181 → Y181
reinstall succeeds. `"version check disabled"` in an OTA manifest only affects the write
phase — GHS enforcement at boot is independent of it and is not influenceable from any
network surface currently documented (see the RemoteReflash finding below).

**ELK/fastbootd — verdict only (full narrative in `elk_recovery.md`):** stock Android
fastbootd on a locked unit is read-only (`getvar` only; `unlocked:no`, `secure:yes`; no OEM
fastboot HAL; `fastboot boot`/`flash`/`fetch` all refused before AVB even applies) — an
information-disclosure + staging surface, not a flashing path. A separate, VIP-mediated
CAN-triggered excursion into Intel ELK (kernelflinger) reported transient `unlocked:yes`/
`secure:no` and positive unlock eligibility after a USB-device reset and a raw libusb
client; a subsequent ELK→AAOS→ELK round trip retained ELK's `unlocked=yes` report while
AAOS still reported `verifiedbootstate=green`/`flash.locked=1`/`vbmeta.device_state=locked`/
`oem_unlock_allowed=0`. Cold-power persistence of that ELK-side state, and whether it
predated the unlock attempt, are both unverified; no partition write was validated by these
state queries. RAM-only custom-kernel Linux boots (USB serial/NCM, public-key SSH, native
eMMC reads matched by independent SHA-256) are confirmed readback-only — a RAM-booted image
carries a green verified-boot cmdline value by construction, so that value alone does not
authenticate the image. See the [ELK analysis](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15)
and [`boot_chain.md`](boot_chain.md).

**GSI/DSU — corrected verdict (full policy/firmware-image detail in
[`boot_chain.md`](boot_chain.md#gsidsu-boot-gate)):** the earlier claim that
`dontaudit gm_update_engine gsi_metadata_file` blocks GSI installs is **wrong** — `dontaudit`
only suppresses an audit log for a denial that already happens from the absence of an allow
rule, and it targets GM's OTA engine, not the DSU path. GSI/DSU is actually disabled because
(a) `com.android.dynsystem` (the DSU installer app) is removed from the image on all of
Y175/Y177/Y181 while the `gsid`/`gsi_tool` daemon keeps full stock SELinux policy —
"removed app," not "policy block"; (b) the direct `gsi_tool` path is closed by
`ro.build.type=user`/`ro.debuggable=0` (shell uid 2000) plus the signature-or-privileged
`MANAGE_DYNAMIC_SYSTEM` permission shell lacks; (c) any staged GSI must still pass locked
verified boot trusting only Google's q/r/s GSI keys. Net: three independent, non-SELinux
gates, not the originally-cited `dontaudit` rule.

---

## VIP MCU Security

> **[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE.** VIP firmware version, the `0xb67d0`-class
> validator, subroutines and byte-diffs are off-SoC/teardown artifacts, not observable from a
> locked Y175 user shell. Corroboration available: `gm_protokey` is live (PID 889, root,
> SELinux domain `gm_protokey`). **VIP-side corroboration** [diagnostics/Y175_session.log]:
> the VIP boot log independently shows `J6_prv_ProtoKey:Protokey transmitted to SoC`
> (repeating), `SbaTicketValidation validation failed: 0x0`, `Receives invalid seed [1/2]
> from BCM` — the ProtoKey-transmit + SBAT-validation + seed-from-BCM path is observable from
> the VIP log even though the SoC-side validator internals are not.

VIP security function address: `0x000b67d0` (not a firmware version — build identities live
in [`firmware_versions.md`](firmware_versions.md)).

| Build | VIP_APP File ID | Security function | Detail |
|-------|------------------|--------------------|--------|
| Y177 | 86283151 | Full ~906-byte validator | The earlier "4-byte stub, always returns 0" claim is retracted (2026-08-26) — the "stub" was a fixed-address misread |
| Y181 | 86331656 | 906-byte full implementation | Active; calls validation subroutines |

- **Called subroutines:** `0x000b6652`, `0x000aee28`. (`0x000ecd84` is a generic RTOS mutex
  primitive with 285 call sites, not part of a "validation chain" — corrected per
  `research/AUG24_25`.)
- **RAM `0x3e06`:** a generic "security module initialized" readiness flag — not a processed
  EEPROM SBI value and does not "control security bypass behavior" (corrected).
- **Callers:** `0x000b6b06` (primary), `0x000b6e82` (secondary/fallback).
- **MEC/ADB certificate gate (not SELinux):** this validator belongs to the ADB/certificate
  path. `gm_adb_auth_init`/`is_secure_mode` is driven by EEPROM SBI → VIP MEC response on DID
  `F1A0`; it does not set SELinux mode. See [ProtoKey / ADB Authentication](#protokey--adb-authentication).
- Between Y177 and Y181, 549,518 bytes (28.4%) differ in VIP firmware — **not** a
  security re-enablement; a three-way byte diff (2026-08-25) shows the full ~906-byte
  validator present in ALL builds (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0). The delta is
  unrelated VIP changes.

---

## ProtoKey / ADB Authentication

> **[C] bench-unit note 2026-11-12:** live VIP logs carry thousands of `[PROTOKEY] Receives
> invalid seed [n] from BCM` lines — **7113** by raw grep (2244 + 4869), **7114** by a
> header-stripped re-derivation; both `[1]` and `[2]` indices run ~3556-3558 each, off by one
> for an undetermined reason. Consistent with a bench unit with no real BCM answering the
> seed request — a bench-unit result, not evidence about in-vehicle behaviour.

> **Scope, corrected 2026-11-16:** the BCM-to-radio ProtoKey material (CAN `457`/`458` supply
> the RH850's two eight-byte seed caches, correlated with the personal-information gate
> clearing) is distinct from the MEC/ADB certificate gate and from the Ethernet UDS `$27`
> SecurityAccess gate below. None of these observations changes SELinux enforcement — the
> former "→ SELinux ENFORCING/PERMISSIVE" framing remains retracted. See the
> [CAN signal dictionary](can_network.md#verified-a11-signal-translations).

The certificate range checks, secured/bypass behavior, Boolean inversion and historical
diagnostic readings are maintained in
[the consolidated MEC/ADB source](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).
EEPROM programming workflow: [the EEPROM guide](../eeprom/README.md) and
[`eeprom_i2c_security.md`](eeprom_i2c_security.md).

**CAN-side ADB-enable attempt (pointer only — full log in
[`can_bench_experiments.md`](can_bench_experiments.md#direct-can5-adb-enable-diagnostics--2026-11-15)):** a
direct CAN5 UDS `31 01 03 32 DD …` enable-only sweep across all 256 domains, with and without
a level-1 SecurityAccess grant (`67 02`), returned `7F 31 31` (NRC 31, service/subfunction
not supported) for every domain in both default and extended session. NRC 31 does not
distinguish "unsupported routine" from "wrong domain/parameter" — this rejects the tested
layout, it does not establish that no CAN-side ADB-enable routine exists. The
`KeyguardProtoKeyViewController`/`GMKeyguardProtoKeyView` decompiled ADB-retention-control
internals referenced alongside that sweep are Android-security-model detail, not a CAN
signal, and are catalogued at the same `can_bench_experiments.md` anchor rather than duplicated here.

<a name="ethernet-uds-27-securityaccess--vip-side-forwarding-off-soc-2026-09"></a>
### Ethernet UDS `$27` SecurityAccess — VIP-side forwarding, off-SoC

Distinct from the ADB/seed-auth bypass above: the `diagnosticsd` Ethernet-diagnostic
(`:49156`) `$27` SecurityAccess gate is fully owned by
[`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md).
Summary of the live finding: a firewall-allowed direct T1 client using the valid tester ID
`0x00F4` entered extended session, submitted a degenerate (all-zero) key against a 31-byte
all-FF seed, and was granted multiple SecurityAccess levels (`67 01/02/0A/0C`), making
protected DID `F0A7` readable; an exhaustive 65536-DID sweep at level 09 found 135 positive
reads. **This does not establish** a recovered key algorithm, the gateway routing chain,
arbitrary writes, calibration/signature bypass, partition writes, Android root, or a GHS
shell — matching CAN/Ethernet seed/response *formats* does not locate the key comparison.
An earlier `7F 27 10` result that looked like "SBI inactive" used an invalid tester ID
(`0x0FA0`) and is superseded; a valid tester in default session instead returns `7F 27 7F`.
**Emulator note:** this bypass cannot be reproduced on the hybrid Android emulator —
`IDiagnosticsObd` is unregistered, `diagnosticsd` is entirely absent, and GM Secure-ADB is
replaced by Google's stock `adbd`, so no secure-mode chain runs at all; modeling it there
would need a substantial synthetic external-component/VIP endpoint, not a quick stub (see
[`emulator.md`](emulator.md)).

> **[C] live-Y175 2026-10-05 — posture note:** the EEPROM-SBI→VIP MEC=0xFF→`is_secure_mode`→DID
> `0xF1A0` chain is UNVERIFIABLE-FROM-LIVE on this unit (EEPROM/VIP/DoIP, not reachable from a
> locked user shell). This unit is in **secured** operation, not the bypass path:
> `ro.secure=1`, `ro.adb.secure=1`, `ro.debuggable=0`, adb shell is the normal uid 2000
> (`u:r:shell:s0`) — adb via the standard path, not an `is_secure_mode=1` no-cert unlock.
> `diagnosticsd` is live as native `gm_diagnosticsd` (PID 590).

<a name="bcm-replacement-factory-wipe-code-trace-2026-11-14"></a>
### gm_protokey service — summary (full Ghidra trace in diagnostics doc)

- **Binary:** `/vendor/bin/gm_protokey` (+ `gm_protokey_recovery`); init class `main`, user
  `root`, oneshot. **SELinux domain:** `gm_protokey` — **[C] live-Y175 2026-10-05: CONFIRMED**
  live PID 889, user root, context domain `gm_protokey`.
- **Function:** validates received ProtoKey material against a persisted validation record,
  updates `vendor.gm.security.state`, and on a derived-value mismatch (or an unusable existing
  record) can request a **BCM-replacement user-data wipe**. It does not select SELinux
  enforcement.
- **Statically confirmed wipe path** (x86-64 ELF, SHA-256
  `627b8e22a1e318d5e4a3bc00c602f67e9a8ec857d007d66c1ee78c8c32dee88b`; matching
  `libpal_security.so` SHA-256 `a30e4064715e26c81871f46df05c057ddc074f381ca789d52352a4804eaa91f7`):
  on validator mismatch it logs `Protokey failed. (BCM_REPLACED)`, sets
  `vendor.gm.security.state=bcm_replaced`, writes `/update_cache/recovery/command` with:
  ```text
  --wipe_data
   --reason=bcm_replacement
  ```
  waits 5 s, then requests a `recovery` reboot via
  `vendor::gm::powermode::V1_0::IPowerModing` with reason `BR`. The Android daemon holds the
  decision; no direct RH850 or GHS wipe handler was located in either the VIP or GHS images.
- This explains a repeatable *possible* bench/vehicle cycle: a ProtoKey valid in environment A
  fails validation in environment B (different accepted key material) → recovery wipes user
  data → first-boot establishes B's record → returning to A can fail again. UART evidence
  shows the two 8-byte seed halves stable within an environment and differing across
  environments, and a bench boot where the recovery request followed accepted status by
  6.03 s (consistent with the 5 s wait + processing). Attribution of any *specific* observed
  wipe to this exact routine still needs the corresponding Android log/recovery record.
  Full code-address trace, jump-table recovery method, and UART correlation:
  [`diagnostics/diagnosticsd_routines_and_recovery.md`](../diagnostics/diagnosticsd_routines_and_recovery.md#uart-correlation-with-the-bcm-replacement-code-path-2026-11-14)
  and [`research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).

### MEC (Manufacturer Enable Counter)

The authentication chain, range checks, signed-byte conversion, historical readings, Boolean
inversion, root/registration limits and distinction from failed-boot counters are maintained
in [the consolidated MEC source](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration).
EEPROM layout and VIP code: [`eeprom_i2c_security.md`](eeprom_i2c_security.md) and
[the EEPROM audit](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md).

**`F1A0=FF` caveat (restored from the original vehicle_network.md; corrected 2026-11-11):** a returned MEC
`F1A0=FF` lies in the 1–255 range that bypasses the SoC's GM ADB client-certificate requirement; it is not
enforced-secure mode. The SPS host-authorization error does not prove the cause of an all-FF ECU seed. The
EEPROM/ADB, UDS, ProtoKey and signing gates must remain separate. Evidence guide:
[`../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

---

## EEPROM Security — pointer only

Memory map, framing markers, I2C-bus permission table, and the GPIO/local-hardware rollup
are owned by [`eeprom_i2c_security.md`](eeprom_i2c_security.md) (and
[`../eeprom/README.md`](../eeprom/README.md) for the programming workflow), not duplicated
here. Headline verdict still gates ADB/seed-auth above: the security configuration region
(EEPROM `0x0400`-`0x045F`) sits outside CRC protection and CRC is not enforced at boot, so a
flipped SBI persists across reboots until the VIP's bulk restore-to-ROM-defaults routine
re-locks it.

---

## Kernel Security Mitigations

> **[C] live-Y175 2026-10-05:** Kernel string CONFIRMED:
> `4.19.283-PKT-230612T042614Z-ga53d763f5b0d #1 SMP PREEMPT Wed Jun 26 2024 x86_64`. The
> mitigation/CONFIG tables below are build-time kernel config and are
> **UNVERIFIABLE-FROM-LIVE** (no `/proc/config.gz` or `dmesg` in the capture set) — do not
> treat any row below as confirmed on this unit.

| Mitigation | Status |
|------------|--------|
| KASLR | Enabled |
| Stack Protector | Enabled |
| SMEP/SMAP | Enabled |
| Spectre v2 | Mitigated (IBRS/IBPB) |

### Kernel CONFIG flags

#### Enabled (hardening active)

| Config Flag | Purpose |
|-------------|---------|
| `CONFIG_STACKPROTECTOR_STRONG` | Stack buffer overflow detection (strong variant) |
| `CONFIG_STRICT_KERNEL_RWX` | Kernel text/rodata read-only, data non-executable |
| `CONFIG_STRICT_MODULE_RWX` | Same protections for loadable kernel modules |
| `CONFIG_RANDOMIZE_BASE` | KASLR — randomize kernel base address |
| `CONFIG_RANDOMIZE_MEMORY` | Randomize physical memory mapping |
| `CONFIG_RETPOLINE` | Spectre v2 mitigation via retpoline thunks |
| `CONFIG_X86_SMAP` | Supervisor Mode Access Prevention |
| `CONFIG_X86_INTEL_UMIP` | Blocks SGDT/SIDT/SLDT/SMSW/STR from ring 3 |
| `CONFIG_X86_INTEL_MEMORY_PROTECTION_KEYS` | Hardware memory protection keys (PKU) |
| `CONFIG_SECCOMP` | Syscall filtering for sandboxed processes |
| `CONFIG_HARDENED_USERCOPY` | Runtime bounds checking on copy_to/from_user |
| `CONFIG_INIT_ON_ALLOC_DEFAULT_ON` | Zero-fill heap allocations (info-leak prevention) |
| `CONFIG_SLAB_FREELIST_RANDOM` | Randomize SLAB freelist order |
| `CONFIG_BPF_JIT_ALWAYS_ON` | Force BPF JIT, disables interpreter |
| `CONFIG_X86_INTEL_TSX_MODE_OFF` | TSX disabled (mitigates TAA/MDS) |

#### Disabled (attack-surface reduction)

| Config Flag | Significance |
|-------------|---------------|
| `CONFIG_USER_NS` not set | No unprivileged user namespaces — blocks container-escape primitives |
| `CONFIG_MODIFY_LDT_SYSCALL` not set | No LDT modification |
| `CONFIG_LEGACY_VSYSCALL_NONE` | No legacy vsyscall page |
| `CONFIG_KVM` not set | No KVM virtualization |
| `CONFIG_NF_TABLES` not set | No nftables |
| `CONFIG_USERFAULTFD` not set | Blocks a common race-condition exploitation technique |
| `CONFIG_IO_URING` not set | Eliminates a major recent vulnerability source |

#### Missing (gaps in hardening)

| Config Flag | Impact |
|-------------|--------|
| `CONFIG_SLAB_FREELIST_HARDENED` | Not set — freelist pointer obfuscation absent |
| `CONFIG_SECURITY_YAMA` | Not set — no ptrace scope restrictions |

#### SELinux kernel support

`CONFIG_SECURITY_SELINUX_DEVELOP=y` — the kernel *supports* permissive mode at compile time,
but stock userspace never uses it: Y175/Y177/Y181 ship a byte-identical `init` that forces
enforcing (`ALLOW_PERMISSIVE_SELINUX=0`). SELinux mode is set OS-side (ramdisk/init) and is
**not** controlled by the VIP security function or `gm_protokey` (the old "Y177 stub →
permissive" framing was a fixed-address misread — the VIP validator is full in all builds and
gates ADB/seed auth, not SELinux). Live confirmation: see "Runtime vs. cmdline" note above.

---

## File-Based Encryption (FBE)

| Property | Value |
|----------|-------|
| `ro.crypto.state` | `encrypted` |
| `ro.crypto.type` | `file` |
| Cipher | `aes-256-xts:aes-256-cts` |
| Metadata Encryption | `dm-default-key` |
| Keystore Backend | Trusty TEE via GHS (`ro.hardware.keystore=trusty`) |

> **[C] live-Y175 2026-10-05:** `ro.hardware.keystore=trusty`, `ro.hardware.gatekeeper=trusty`,
> `ro.boot.trustyimpl=-ghs` CONFIRMED; `init.svc.keystore2=running`,
> `init.svc.gatekeeperd=running`; `/dev/trusty-ipc-dev0` present (`tee_device`). Metadata
> method `dm-default-key` and `persist.sys.gm.encryption=true` CONFIRMED; the exact cipher
> string is UNVERIFIABLE-FROM-LIVE. **Note:** `/dev/trusty-ipc-dev0` is `crw-rw-rw-`
> (world-rw at the DAC layer) — the TEE IPC node is DAC-open to any process; the SELinux
> `tee_device` label gates actual access.
>
> **[C] Y181.3.2-ref 2026-10-06: PARTIAL — contents-cipher and active-FBE are NOT confirmable
> on this reference** (the emulator build has Trusty/FBE disabled). Root readout:
> `ro.crypto.state=unencrypted`, `/vendor/etc/fstab`'s `/data` line is `f2fs` with no
> `fileencryption=`/`metadata_encryption=` flag, `ro.hardware.keystore` unset, no
> `/dev/trusty*`/`tee` node — this reference runs software crypto, not the GHS-Trusty TEE.
> Only `ro.crypto.volume.filenames_mode=aes-256-cts` and `…metadata.method=dm-default-key`
> survive as build-default props. Do not upgrade this row from the Y175 verdict.

---

## Trusty TEE

The Trusty TEE runs under the GHS INTEGRITY hypervisor, providing hardware-backed key storage
and crypto operations.

| Service | Function |
|---------|----------|
| `TEE_Keymaster` | Hardware-backed key generation, storage, operations |
| `TEE_HW_Crypto` | Hardware cryptographic acceleration |
| `TEE_Storage` | Secure storage via RPMB |

ELF sections: `.tee_keymaster.text`/`.data`/`.rodata`. **[FW 85098662; 2026-10-10]:** the
high-entropy TEE rodata blocks are standard AES T-tables (Te0-3/Td0-3) and SHA-256/512
constants — identified, not secret and not encrypted code (`GHS_FILE_MAP_85098662.md`).

HAL: `keymaster@3.0` (Trusty-GHS implementation), `init.trusty-ghs.rc`, properties
`ro.hardware.gatekeeper=trusty` / `ro.hardware.keystore=trusty`.

GHS's own `/dev/ghs/*` device-interface table, the USB mediated-passthrough finding
(`usb_passthru_emul.c`/`OTGD`/`SPPS`), and live enumerability on Y175/Y181.3.2-ref are owned
by [`vip_ipc_ghs.md`](vip_ipc_ghs.md) — pointer only, not duplicated here.

---

## GM SELinux Domains

### Critical service domains

| Domain | Function | Notes |
|--------|----------|-------|
| `gm_vnd_IPCServer` | VIP MCU IPC communication | Runs as **root**, HDLC protocol on `/dev/ttyS1` |
| `gm_diagnosticsd` | UDS diagnostic service | Handles $10/$22/$27/$2E/$31/$34/$36/$37 |
| `gm_update_engine` | OTA firmware updates | GM fork of AOSP A/B update_engine. The `dontaudit gm_update_engine gsi_metadata_file` rule in `vendor_sepolicy.cil` is **not** a GSI blocker — see GSI/DSU verdict above |
| `gm_vehicle_hal` | Vehicle HAL implementation | Bridge between Android and VIP/CAN |
| `gm_protokey` | Security-state validation, BCM-replacement recovery | See gm_protokey summary above |

> **[C] live-Y175 2026-10-05: all five domains CONFIRMED as live processes** (ps.txt):
> `gm_vnd_IPCServer` (PID 386, root — consistent with "runs as root/VIP IPC");
> `gm_diagnosticsd` (590, root); `gm_update_engine` (574, root); `gm_vehicle_hal`
> (`…vehicle@2.0-service-gm`, PID 792, user **vehicle_network** — NOT root); `gm_protokey`
> (889, root). `/dev/ttyS1` perms CONFIRMED `crw------- root:root u:object_r:ipc_serial_device:s0`
> (0600, root-only); the 20-channel/HDLC-v16 claims are not independently probed in this
> capture.

### Vehicle HAL clients

`system_server`, `gmConnectionService`, `camerad`, `plmanager`, `vehicleaudiocontrol`.

> **[C] Y181.3.2-ref 2026-10-06: allow-list CONFIRMED against live on-device CIL (root).**
> `IVehicle` is `u:object_r:hal_vehicle_hwservice:s0`
> (`plat_hwservice_contexts:16`); `find` is granted to exactly one attribute,
> **`hal_vehicle_client`** (`plat_sepolicy.cil:11213`, guarded by a neverallow at `:11223`).
> All five domains above are members of that attribute in
> `vendor_sepolicy.cil`/`product_sepolicy.cil` (`carservice_app` is one extra member not
> listed above). Mechanism = single attribute-based `find` grant + neverallow, confirmed for
> **Y181.3.2**; inferred only (no bootable Y175/Y177 policy) for the other builds. Distinct
> from the GM framework `gm_domain_service` services (`VehicleSettingsService`/
> `VehicleCompanionAppService`) and `gm_vehiclemanager_service`.

### GSI/DSU status

See the corrected verdict under [Secure Boot Chain](#secure-boot-chain--locked-radio-posture)
above; full policy/firmware-image detail in [`boot_chain.md`](boot_chain.md#gsidsu-boot-gate).

---

## Key CVEs

> **CORRECTED 2026-08-26.** The prior table premised Y177 exploitability on "SELinux
> permissive." That premise is **FALSE** — Y177 and Y181 both run SELinux enforcing
> (byte-identical init). Kernel-vulnerability exposure differs by security-patch level and
> kernel version, not by SELinux mode; enforcing SELinux provides the same MAC containment on
> both builds.

| CVE | CVSS | Description | Kernel status (Y177 & Y181) |
|-----|------|--------------|-------------------------------|
| CVE-2024-53104 | 7.8 | UVC (USB Video Class) vulnerability | Both enforce SELinux; patch status tracks kernel 4.19.305 / patch level (Y177 2025-03-05, Y181 2025-06-05) |
| CVE-2024-36971 | 7.8 | dst_cache UAF | Same — gated by patch level, not SELinux mode |
| CVE-2024-53150 | 7.8 | USB out-of-bounds read (Cellebrite chain) | Same |
| CVE-2024-53197 | 7.8 | USB ALSA out-of-bounds access (Cellebrite chain) | Same |
| CVE-2023-2163 | 8.8 | BPF verifier range tracking | Requires `CAP_BPF`; enforcing SELinux (both builds) restricts BPF to authorized domains |
| CVE-2024-1086 | 7.8 | nf_tables use-after-free | **NOT APPLICABLE** — `CONFIG_NF_TABLES` not set |

> **[C] live-Y175 2026-10-05:** table scopes to Y177 & Y181 (kernel 4.19.305); live Y175 runs
> older kernel `4.19.283` / patch `2024-05-05`, so per-build patch cells do not transfer to
> Y175. `CONFIG_NF_TABLES`/`CONFIG_BPF_JIT_ALWAYS_ON` are UNVERIFIABLE-FROM-LIVE. The
> SELinux-enforcing containment premise is CONFIRMED for Y175 (runtime Enforcing).

**CVE-2024-53150 / -53197** are part of the Cellebrite USB exploitation chain (CISA KEV, April
2025); on all builds SELinux enforcing restricts USB driver access to authorized domains —
there is no permissive-Y177 window. **CVE-2023-2163** additionally needs `CAP_BPF`, and
`CONFIG_BPF_JIT_ALWAYS_ON` reduces interpreter attack surface (does not prevent a verifier
bypass). **CVE-2024-1086** is not applicable because `CONFIG_NF_TABLES` is not compiled in.
The earlier "exploitable due to SELinux permissive" framing is retracted across the board.

---

## Attack Surface Analysis

### IGMAuthService — `protectionLevel=normal` auth-token exposure

> **[C] Phase 1 offensive audit (Sep 2026) — single most severe finding.** Static RE of
> decompiled Y181 APKs found `IGMAuthService` (host `com.gm.authtoken`, uid `system`) gates
> `getAuthTokenByUserID`/`setAuthTokenByUserID`/`removeAccount`/`getGuestAccountToken` behind
> three custom permissions (`gm.permission.authentication.{ID|CLIENT|USER}`) shipped
> `protectionLevel=normal` — auto-granted at install to any app that declares them, no
> signature match, no prompt. A sideloaded third-party app can therefore exfiltrate live
> GM/OnStar bearer tokens from `authtokens`, forge/replace tokens, or lock out an account.
> Confirmed live via `dumpsys package permissions`. Full ranked findings (incl. the same-class
> `com.gm.vehicle.permission.READ_*` family, an unauthenticated cluster/HUD display-injection
> surface, and two FSA UDP/multicast bugs — the latter also summarized in
> [`emulator.md`](emulator.md) and [`fsa_protocol.md`](fsa_protocol.md)):
> [`../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).

> **[C] live-Y175 2026-10-05:** the `prot=normal` core is CONFIRMED live — all three
> permissions `protectionLevel=normal`, owner `com.gm.authtoken` runs as **system**
> (PID 2139); `gm_auth`/`gmBOAgent` binders registered. The 59-member
> `com.gm.vehicle.permission.READ_*` normal-permission family (18 `READ_*` vehicle twins of
> `*_PROTECTED` sig|priv perms) is likewise live-CONFIRMED. The `product_sepolicy.cil:586`
> `untrusted_app`→`gm_authToken_service` `find` grant was initially only confirmed on
> **Y177's** pulled policy (Y181 pulls never captured a product-partition sepolicy file) —

> **[C] Y181.3.2-ref 2026-10-06: VERDICT-FLIP — the grant IS present on Y181, same line.**
> Read from live on-device product CIL (root, Enforcing): `product_sepolicy.cil:586` is
> verbatim `(allow untrusted_app gm_authToken_service (service_manager (find)))`; lines
> 583-588 grant the same `find` to the whole untrusted/app spread
> (`untrusted_app_all`/`ephemeral_app`/`mediaprovider`/`untrusted_app`/`untrusted_app_27`/
> `untrusted_app_25`), plus `graphic_dump`/`platform_app`/`priv_app`/`system_app`. Both
> `gm_auth` and `gmBOAgent` are labeled `gm_authToken_service` and registered live. This
> closes the Y177→Y181 gap: the SELinux `find`-reachability half is now confirmed under
> Enforcing on Y181.3.2 specifically (Y175 remains *inferred only*, no bootable Y175 policy).
> The `authtokens` DB (`/data/gmauth/gmtokens.db`) is `-rw-rw---- system:system`, MAC-gated to
> `system_app` only — direct file-read exfil by a sideloaded `untrusted_app` is DAC+MAC-
> blocked. **The real exposure is the Binder path**: `untrusted_app` can `find` the service
> (line 586) and the three `gm.permission.authentication.*` gates are `prot=normal`, so
> `getAuthTokenByUserID` is reachable without a direct DB read.

### GMWlanService — SoftAP credential exposure, SELinux-only gate

> **[C] Finding.** `com.gm.server.wlanservice` (`gm.wifi.IGMWlanService`, registered on
> Y175/Y177/Y181) exposes `getWifiApConfiguration()` — the head-unit SoftAP (hotspot) **SSID
> and passphrase** — with **no application-level permission or uid/pid check**:
> `DomainService.publishBinderService`→`ServiceManager.addService(name, service, false)` (no
> permission string), `GMWlanServiceBinder` does not override `onTransact`, and
> `GMWlanServiceImpl.getWifiApConfiguration()` builds/returns the config with zero guard. A
> package-wide grep for `enforceCall*|checkPermission|getCallingUid|getCallingPid|
> SecurityException|onTransact` returns nothing. Contrast stock
> `WifiManager.getSoftApConfiguration()`, signature-gated.
>
> **The only barrier is SELinux `service_manager:find`.** The service is labeled base type
> `gm_domain_service`; a normal `untrusted_app` is granted `find` only on the sibling
> `gm_domain_service_nav`, never the base type (no attribute backdoor — `gm_domain_service`
> carries a neverallow on `add`). **So a plain sideloaded app is blocked at the SELinux
> layer.**
>
> **Residual exposure (real):** `priv_app`/`platform_app` *are* granted `find` on the base
> type, and the server checks nothing — so **any privileged/preinstalled app (not necessarily
> GM-signed) reads the SoftAP passphrase with no permission.** Same class of defect as
> `IGMAuthService`: reachability decided purely by SELinux domain, zero in-service caller
> check. Confirmed on **two independent sources**: the CT5 2026 decompile and an independently
> booted Y181.3.2 image (`/system/priv-app/DelayedWKSApp/DelayedWKSApp.apk`, zero
> `getCallingUid`/`enforce*`/`check*Permission`/`clearCallingIdentity` in the chain against
> ~300 uses elsewhere in the same APK).
>
> **[C] Live-hardware confirmation, 2026-10-05 (`W213E-Y175.5.2-SIHM22B`, SoftAP up as
> `benchd89`):** a PoC installed as a genuine `untrusted_app` produced the predicted SELinux
> denial verbatim in the on-device audit log:
> `avc: denied { find } for … name=com.gm.server.wlanservice scontext=u:r:untrusted_app:s0:…
> tcontext=u:object_r:gm_domain_service:s0 tclass=service_manager permissive=0`.
> `ServiceManager.getService` returns null; `WifiManager.getSoftApConfiguration()` returned
> null to the unprivileged caller despite the AP being active. The `priv_app` residual path
> was **not** exercised on-device (needs `/system/priv-app` placement, remount/eng build).
>
> **adb-permission angle (answers "can a granted permission unlock it"):** every relevant
> credential permission is signature-tier and **not grantable via `adb shell pm grant`**
> (`SecurityException: … is not a changeable permission type` for `OVERRIDE_WIFI_CONFIG`,
> `NETWORK_SETTINGS`, `READ_WIFI_CREDENTIAL`, `LOCAL_MAC_ADDRESS`, `NETWORK_SETUP_WIZARD`). So
> **no adb-issued grant gives a third-party app the SoftAP credentials.** Only
> `ACCESS_FINE_LOCATION`/`COARSE` are adb-grantable; with location a third-party app reads only
> Wi-Fi scan-result channel/frequency/BSSID (standard AOSP location-gated behaviour), no
> passphrase.
>
> **Caveat:** the reference image for the server-body confirmation is **Y181.3.2**, not the
> Y175.5.2 bench — do not cross-assert. No bootable Y175 x86 image exists, so the Y175 server
> body remains formally uninspected (identical interface descriptor + transaction map
> inferred). Moot for *untrusted* apps on Y175 (the live bench avc denial blocks them at
> SELinux regardless); the "privileged-app reaches an unchecked server" residual is *proven*
> on Y181.3.2 and only *inferred* for Y175. Bench PoC: `~/gm_wlan_poc` (logs tag
> `GMWLAN_POC`).

### RemoteReflash / UpdateService install path — no confirmed unauthenticated-network trigger

`RemoteReflash` (FSA `9012`) has Android as a **client** dialing the telematics node `.102`,
not a server; inbound events dispatch to `IRemoteReflashServiceEvents`, which is
**unsubscribed system-wide** (checked across 6 apps incl. `CriticalWKSApp`/`GMTCPS`).
`UpdateServiceImplGB.install()`'s missing permission check is reachable only from
`priv_app`/`platform_app`/`carservice_app` (SELinux `gm_domain_service` `find` grant), not
`untrusted_app`/shell — and even from there the caller's IPC `PackageDetails` argument is
never consumed (the install pipeline only accepts an internal `Package` object fetched via
`retrievePackageFromMessage()`); `InstallRunner.install(pkg)` always uses the vehicle's own
legitimately-staged package. Net effect of exploiting the missing check: forced/premature
triggering of an already-staged update (consent-bypass/DoS), **not** attacker-content
substitution. `.102` is IP-pinned with no TLS pinning — L2/L3 spoofing of `.102` remains a
bench-open item. Rollback stays hardware-enforced regardless (GHS's own misc-partition
counter, un-influenceable from any network surface documented here). One open item:
`DevCaloverrideInstaller` (containerType 2) skips signature verification entirely, but its
only trigger (`USBUpdateSource$1.onUSBMounted`) requires physical USB media and selects type 2
only on non-`user` builds — the tested Y175 is `user`; Y181's notifier and other entry points
remain to be independently verified. Full trace:
[`ota_update_stack.md`](ota_update_stack.md), [`ota_programming_roles.md`](ota_programming_roles.md#caldef-evidence-for-the-orchestration-role),
and [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md#where-the-facts-live-now-pointers-only).

### gmsystemui capability gating — locked-radio verdict

On a stock **locked** radio (AVB + enforcing SELinux + no root + no bootloader unlock) there
is **no** non-calibration, non-root lever for either removing/hiding the CardView panel or
granting native Cinemo CarPlay the whitelisted/immersive capability — both gates are
hardcoded Java (a calibration-value branch; a hardcoded class-name allow-list) with no
resource/RRO, system-property, or Settings-key fallback found in the decompiled path, and
every lever that could otherwise reach that code (installing an RRO, `setprop`,
Settings write) independently requires `CHANGE_OVERLAY_PACKAGES`/system/root privilege that
AVB + the locked bootloader + enforced SELinux deny. On the emulator (root available) the
working lever is a direct `CalSets.db` write or a root-required runtime hook — mechanism and
full capability-gating detail (`WhiteList`, predicates, display-calibration gate) owned by
[`gmsystemui_app_gating.md`](gmsystemui_app_gating.md#verdict-summary).

### Network services

| Bind Address | Port | Risk | Notes |
|--------------|------|------|-------|
| `0.0.0.0` | 6363 | LOW | AVB audio daemon (uid 1041), init-owned text IPC bus; arbitrary input → `"ERROR"` |
| `0.0.0.0` | 7000 | MEDIUM | AirPlay/AirTunes-class CarPlay audio bridge on br0 (not ADB) |
| `0.0.0.0` | 49156 | **HIGH** | `diagnosticsd` root UDS-over-TCP bridge — full caps, no seccomp, app-layer UDS trust only (no OS peer check), `$27` SecurityAccess gate above |

> **[C] live-Y175 2026-10-05 (net_sockets.txt):** all three listeners CONFIRMED wildcard
> `0.0.0.0`. 6363 is uid **1041** (AOSP `audioserver`; `ps` shows `pulseaudio`). 49156 is uid
> **0 (root)**, consistent with `gm_diagnosticsd` (PID 590). 7000 is uid **1001000**
> (`u10_system`, also bound on `::`) — the "br0-scoped"/"AirPlay 320.17.8" identity claims are
> adjusted/UNVERIFIABLE-FROM-LIVE; the bind is genuinely wildcard.

### Host firewall & network segmentation

Authoritative ruleset: **`/system/etc/iptables.rules`** (Y181, applied at boot via
`iptables-restore` under `netd`) — primary-sourced twice (live Y181.3.2 `iptables-save` +
2026-09-09 Y181 capture, both SHA-256 `edab150…`). Y175's ruleset file is not on the assets
drive (locked unit, no root dump); all Y175 statements below rest on live sockets +
behavioral tests and are single-source until a Y175 root read confirms byte-identity with
Y181.

- **A local on-device app is NOT confined by the SoftAP client firewall.** `INPUT` default
  policy is `DROP`, but `-A INPUT -i lo -j ACCEPT` (`:6`) accepts all local-origin traffic
  unconditionally; the `-i br0` allowlist (`:37-48`) governs only packets ingressing from an
  external SoftAP client. Live-proven on Y175: 6363 and root `diagnosticsd` 49156 (both
  wildcard-bound, neither in the br0 allowlist) are reachable by a local process yet filtered
  from an external client.
- **No `uid-owner`/`gid-owner` egress gate.** The only `-m owner` rule in the applied baseline
  is a uid-1029 bandwidth-accounting exemption, not access control. `OUTPUT` policy is
  `ACCEPT`; `fw_OUTPUT`/`oem_out` are empty. **⇒ any uid, including `untrusted_app` (group
  `inet`), can originate TCP/UDP onto vlan4/vlan5 toward ECU IPs** (e.g. `192.168.1.112`,
  `172.16.4.107`); replies return via `RELATED,ESTABLISHED`.
- **SoftAP (`br0`) ingress allowlist** (tcp 53/7000/5000/5001/6030/30515, udp
  5020/6000/6003/6011/53, DHCP 67). **[C] RESOLVED live-Y175 2026-10-06, active wireless
  CarPlay session:** from a Mac joined to the `benchd89` br0 SoftAP, only `53`+`7000` were
  reachable (nmap) — the projection ports and gm_ccpa's `7011` never opened even under live
  CarPlay, because wireless CarPlay runs on `wlan1` over IPv6 link-local, a separate AP from
  the IPv4 br0/benchd89 SoftAP. The external br0 surface on Y175 is DNS(53)+7000 only, even
  under load.
- **VLAN INPUT** (default DROP) is a tight per-flow allowlist keyed on source-ECU-IP →
  radio's own VLAN IP + dport (vlan5 `.100` from `.102/.104/.106/.109/.112` + SOME/IP-SD
  multicast on a fixed port set; vlan4 `.100` from `.112`→53/443/49156 and `.107`→49156).
- **FORWARD is effectively DROP** (file says `ACCEPT` but `tetherctrl_FORWARD -j DROP` applies;
  IPv6 `FORWARD DROP`). **⇒ an external SoftAP client is NOT routed onto the automotive
  VLANs** — joining the hotspot does not bridge to the vehicle network.
- **ADB port-relocation exploit — confirmed live via the Bus 2 direct-T1 tap
  (2026-11-13).** The `INPUT` policy above is a bare default-DROP with **zero awareness of
  which daemon owns a port** — every ACCEPT rule matches only `(source IP, dest port)`, not
  process identity. Live end-to-end exploit: ADB was relocated onto an allow-listed-but-
  currently-unbound `(IP, port)` pair belonging to a different legitimate GM service (port
  9040, posed as source `.104`) and the firewall passed it unconditionally. A second,
  independent check confirmed `adb tcpip 5555` succeeds over USB and binds `[::]:5555`, but
  inbound TCP/5555 itself stays firewalled (DROP) on both the Bus 2 tap point and a second
  tap on spare pins (X11 1/2) with the identical VLAN trunk/allow-list — i.e. the exposure is
  the allow-listed-port *relocation* technique, not an open 5555. An exhaustive sweep of all
  253 source IPs × full TCP 1-65535 on vlan4/vlan5 found exactly three reachable services —
  `.100:9016` (NetworkAccessManager, allow-listed from `.102`/`.112`), `.100:9002`
  (RemoteModuleHMI, from `.106`/`.109`/`.112`), and `172.16.4.100:49156` (diagnosticsd, from
  `.107`/`.112`) — no undocumented allow-listed identity and no undocumented listening port
  exists anywhere on either /24. A more severe unauthenticated raw-shell variant and its
  local-launch prerequisite are recorded only in the canonical bench write-up; not restated
  here. Canonical source (do not restate further):
  `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.1-§9.3, §7.1-§7.2, cited via
  [`vehicle_network.md`](vehicle_network.md#open-items).

**Net for "can a third-party app reach the VLANs":** an on-device 3P app is gated by
SELinux + service binds, not the SoftAP firewall, and the host firewall imposes no uid
restriction on egress — so in-vehicle it can originate to ECU IPs on the VLANs (the bench has
no ECUs to answer). An *external* SoftAP client cannot (FORWARD drop). ADB itself can be
relocated onto any allow-listed-but-idle port because the firewall is port-keyed, not
process-keyed. See [`../hardware/connectors.md`] for the ADB/USB physical side.

### CAN / UDS diagnostic services — pointer only

The `$10/$22/$27/$2E/$31/$34/$36/$37` UDS service-ID table and the CSM (`0x80`)/CGM (`0x45`)
CAN address assignments are in [`vehicle_config.md`](vehicle_config.md#uds-diagnostic-services-used-by-dps) (table) and
[`vehicle_network.md`](vehicle_network.md) (addressing); these services are
reachable both over CAN/DPS (`../diagnostics/dps/`) and over Ethernet via the root
`diagnosticsd` on `:49156` (GM Ethernet diag address `0x0084`, 8-byte header) described above.
**[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE** — the UDS service IDs, seed/key, and CAN addresses are
off-SoC (CAN/DoIP) and were not (and must not be) probed in a DISK-ONLY shell capture. Only the Ethernet
transport endpoint is observable: `diagnosticsd` on `0.0.0.0:49156` (root) is live. `gm.obd.IOBDService`
(`OBDService`) and `gm.diagnostics_service.IDiagnosticsService` binders are registered (services.txt #63/#60).
(Note kept here because vehicle_config.md, which owns the UDS table, does not carry it.)
Related shell-side surface (Binder UpdateService, kernel KASLR, GM Secure ADB auth):
[`../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md).
OTA/signing gate: [`ota_update_stack.md`](ota_update_stack.md).

---

## SELinux Denial Analysis (Y181)

The 462 SELinux denials observed in one Y181 logcat window are concentrated in three
subsystems — **CBC** (camera/backup-camera hardware access), **RVC** (rear-view-camera video
pipeline permissions), **SXM** (SiriusXM service communication) — with **no USB or
CarPlay-related denials**, indicating the USB host stack and Cinemo/NME CarPlay framework
operate within their assigned domains without policy violations in that window.

> **[C] live-Y175 2026-10-05: Y181-SCOPE-ONLY — do not transfer the 462/CBC/RVC/SXM figures.**
> Live Y175 shows a different picture in this capture: **179** `avc: denied` lines (all
> `permissive=0`), dominated by `system_suspend→sysfs:dir read` (43),
> `system_server→shell:unix_stream_socket getopt` (13),
> `system_server→fs_bpf_tethering:dir search` (12), and benign `proc:file getattr`. The
> security-relevant ones are the `untrusted_app→gm_domain_service:service_manager find` denial
> (the GMWlanService gate above) and `shell→oem_unlock_prop:file read` /
> `shell→gm_carplay:binder call` from our own probe. No CBC/RVC/SXM cluster and no USB/CarPlay
> denials in this point-in-time capture either (not a boot-to-now logcat, so absence here is
> weaker evidence than the Y181 figure).
>
> **[C] live-Y181.3.2 2026-11-12:** the live bench radio's retained logs hold far more denials
> than the 462 figure above (events stream 2347 `avc: denied` over 29 boots, 116 distinct
> tuples; streams overlap, not de-duplicated), all `permissive=0`. No `avc` line names
> `android.car.usb.handler` (gm_ccpa) as scontext/tcontext/app across the retained window
> (`rg` count 0) — the "no USB/CarPlay denials" observation still holds. These three denial
> counts (462 / 179 / 2347) are different capture windows and streams, not a reconciled single
> figure — they are not in tension, each is scoped to its own capture as stated.

A post-power-cycle owner recovery and an MDI2 LTZ reflash were subsequently performed on this
unit; that narrative is diagnostics/recovery content, not SELinux denial analysis, and is not
reproduced here — see
[`diagnostics/diagnosticsd_routines_and_recovery.md`](../diagnostics/diagnosticsd_routines_and_recovery.md#owner-power-cycle-after-clear-nocalibration-fault-2026-11-14).

---

## Open conflicts

None identified that are both (a) a genuine two-source disagreement and (b) owned by this
document's charter. Items on the master cross-doc conflict list (gateway `0x45`=CGM identity,
super-partition size/static-A-B, FSA discovery port, `.107`/`.112` identity, IPC version,
cal-group count, GPU boost clock) belong to `vehicle_network.md`/`boot_chain.md`/
`firmware_versions.md`/`hardware_specs.md`/`gminfo3.7_tech_specs.md` charters, not security
posture, and are not restated here. The one apparent security-adjacent tension — "SELinux
enforcing on all builds" (this doc) vs. the real-kernel emulator booting permissive
(`emulator.md`) — is a scope difference (stock firmware vs. a deliberately-permissive emulator
build), not a disagreement about the same object; both statements stand as scoped above.

---

## GHS INTEGRITY CVEs and public security research [ONLINE RESEARCH 2026-11-21]

Five CVEs are publicly assigned against GHS INTEGRITY RTOS (all 2019, all INTEGRITY RTOS 5.0.4, all in Interpeak networking components — CVE-2019-7711 through CVE-2019-7715). No CVE exists for GHS INTEGRITY IoT or any automotive INTEGRITY variant. No published conference paper, security advisory, or independent adversarial security evaluation for GHS INTEGRITY IoT was located. Full CVE table and analysis: [`../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` §6](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#known-cves-and-public-security-research-online-research-2026-11-21).

Implications for this platform: the publicly known GHS INTEGRITY bugs target Interpeak stack components that may or may not be present in this automotive build. The GHS hypervisor isolation layer (kernel, VMM, address space boundaries) has no public independent adversarial security evaluation. The attack surfaces cataloged in `research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md §11` (IPC channels, A/B metadata, Keymaster IPC, `/dev/ghs/snapshot-dbg`) remain unexercised in public research as of this date.
