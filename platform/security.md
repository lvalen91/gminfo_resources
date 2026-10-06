# GM Info 3.7 Security Architecture

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 2025 - February 2026

---

> **⚠ CORRECTED 2026-08-26 — this file predates the Aug-2026 corrections; several core claims below are RETRACTED.**
> Authoritative sources: `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0 and `research/security/KERNEL_CVE_ANALYSIS.txt` Appendix E.8.
> - **No stock build runs SELinux permissive.** Y175/Y177/Y181 share a byte-identical `init` that forces enforcing
>   (`ALLOW_PERMISSIVE_SELINUX=0`); the "Y177 permissive" rows/sections and every "CVE exploitable because permissive"
>   claim below are FALSE.
> - **There is no "4-byte stub."** The VIP `0xb67d0`-class validator is FULL in all three builds; the stub finding was a
>   fixed-absolute-address misread.
> - **The EEPROM "security" section is retracted:** `0x04A0/0x04C0/0x0A40/0x0BE0/0x1A00` are NOT security flags, the
>   ref-counts and "IPC Security Config" naming were fabricated, and "disasm-confirmed" on `0x0440/0x0A80` is wrong. The
>   real SBI is `0x0441`+`0x0A80` (empirically flips ADB).
> - **The ADB unlock is SoC-side and unrelated to SELinux or `0xb67d0`:** EEPROM SBI → VIP transmits MEC=0xFF (DID `0xF1A0`)
>   → `gm_adb_auth_init` sets `is_secure_mode=1` → adb allowed with no cloud cert. See EEPROM audit §0.9/§0.10/§0.14.

## Android Security by Firmware Version

| Feature | Y175 (June 2024) | Y177 (March 2025) | Y181 (July 2025) |
|---------|-------------------|---------------------|-------------------|
| SELinux | Enforcing | ~~**PERMISSIVE**~~ **Enforcing** (CORRECTED 2026-08-26 — stock Y177 forces enforcing, byte-identical init) | Enforcing (462 denials in logcat — CBC, RVC, SXM, but no USB/CarPlay denials) |
| dm-verity | Enabled | Enabled | Enabled |
| FBE (File-Based Encryption) | Yes | Yes | Yes |
| Security Patch | 2024-05-05 | 2025-03-05 | 2025-06-05 |
| Kernel | 4.19.283 | 4.19.305 | 4.19.305 |

> **[C] live-Y175 2026-10-05 (device `W213E-Y175.5.2-SIHM22B-383.1`, fingerprint `gm/full_gminfo37_gb/gminfo37:12/.../213:user/release-keys`):** Y175 column CONFIRMED end-to-end — Android `12` / `ro.build.version.sdk=32`; SELinux **Enforcing** (runtime `getenforce`=Enforcing, all 179 captured `avc` lines carry `permissive=0`) *despite* kernel-cmdline `ro.boot.selinux=permissive` in props — i.e. userspace/init overrides the cmdline, exactly as the "init forces enforcing" claim predicts; `ro.build.version.security_patch=2024-05-05`; kernel `4.19.283-PKT-230612T042614Z` x86_64; FBE present (`ro.crypto.volume.metadata.method=dm-default-key`, `persist.sys.gm.encryption=true`). dm-verity "Enabled" CONFIRMED-INDIRECT only: `/`,`/vendor`,`/product` mount from device-mapper nodes dm-6/7/8 and `verifiedbootstate=green`, but `verity.txt` captured no dm-verity status text. **Y177 and Y181 columns are UNVERIFIABLE-FROM-LIVE** (live radio is Y175; do not treat their patch/kernel/denial-count cells as confirmed here).

**CORRECTED 2026-08-26:** the earlier "Y177 runs SELinux permissive / is a security regression" claim is **FALSE and retracted**. Y175/Y177/Y181 ship a byte-identical `init` that forces enforcing (`ALLOW_PERMISSIVE_SELINUX=0`); all three run SELinux **enforcing**. The former "Y177 Attack Vectors (SELinux Permissive)" section below is reframed accordingly — the local hardware attack surface it lists is present on all builds and is not gated by a (nonexistent) permissive mode.

---

## Secure Boot Chain

The boot chain is a 5-layer trust hierarchy from hardware root to runtime filesystem integrity:

| Layer | Component | Mechanism | Details |
|-------|-----------|-----------|---------|
| 1 | Intel CSE | Hardware root of trust | OTP fuses, immutable, first code executed |
| 2 | SOC_ABL (SoC Application Boot Loader) | Intel IPK format | ~6MB signed image, `.oemkeys` contains RSA-2048 public key for chain validation |
| 3 | GHS INTEGRITY Hypervisor | SHA-1 + CRC validation | `BSP_CRCCheck`, `BSP_SHA1Check` verify hypervisor and VM images before launch |
| 4 | AVB (Android Verified Boot) | RSA-2048 / SHA-256 | `vbmeta` signature verified by GHS VMM1 before Android kernel loads |
| 5 | dm-verity | Runtime block integrity | Protects system, vendor, and product partitions; hash tree verified on read |

> **[C] live-Y175 2026-10-05:** Layers 1-3 (Intel CSE OTP, SOC_ABL, GHS INTEGRITY hypervisor internals) UNVERIFIABLE-FROM-LIVE (not observable from a locked user shell). Layer 4 (AVB) supported: `ro.boot.avb_version=1.2`/vbmeta 1.1, `vbmeta` hash_alg sha256, digest `76b736ea…bb585`, `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `verifiedbootstate=green`. Layer 5 (dm-verity) supported by dm-6/7/8 device-mapper mounts of `/`,`/vendor`,`/product` (all `ro,seclabel`); no dm-verity *status* text captured.

---

## VIP MCU Security

> **[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE.** VIP firmware version, the `0xb67d0`-class validator, called subroutines, RAM flags and byte-diffs are all off-SoC / teardown artifacts not observable from a locked Y175 user shell. Only corroboration available here: the `gm_protokey` native process is live (PID 889, root, SELinux domain `gm_protokey`), consistent with the ADB/seed-auth framing below.

VIP security function ADDRESS: `0x000b67d0` (NOT a firmware version). VIP firmware version: **2B.174.4.1** (Build 24Mar22-0256).

| Version | VIP_APP File ID | Security Function | Details |
|---------|-----------------|-------------------|---------|
| Y177 | 86283151 | ~~4-byte stub (always returns 0)~~ **FULL ~906-byte validator (CORRECTED 2026-08-26)** | ~~`mov 0, r10; jmp [lp]`~~ no stub in any build; the "stub" was a fixed-address misread (see EEPROM audit §2) |
| Y181 | 86331656 | 906-byte full implementation | Security function active, calls validation subroutines |

### Y181 VIP Security Function Detail

The 906-byte security function at `0x000b67d0` performs multi-stage validation:

- **Called subroutines:** `0x000b6652`, `0x000aee28`. (`0x000ecd84` is **not** part of a "validation chain" — it is a generic RTOS mutex primitive with 285 call sites; corrected per research/AUG24_25.)
- **RAM `0x3e06`:** a generic "security module initialized" readiness flag — **not** a processed EEPROM SBI value and unrelated to the SBI's actual value (corrected; it does not "control security bypass behavior")
- **Callers:** `0x000b6b06` (primary entry), `0x000b6e82` (secondary/fallback entry)
- **ADB/seed-auth gate (NOT SELinux):** this validator gates ADB/seed authentication only. The actual ADB unlock is SoC-side (`gm_adb_auth_init` / `is_secure_mode`) driven by the EEPROM SBI → VIP MEC=0xFF response on DID `0xF1A0` — it does **not** set SELinux mode (SELinux is OS-side ramdisk/init, enforcing on all builds). See [ProtoKey / ADB Authentication](#protokey--adb-authentication) (CORRECTED 2026-08-26)

Between Y177 and Y181, 549,518 bytes differ in VIP firmware — 28.4% of the total firmware image. **This is NOT a security re-enablement/hardening:** a three-way byte diff (2026-08-25) shows the full ~906-byte validator present in ALL builds (Y175 @0xb6708, Y177 @0xb67d4, Y181 @0xb67d0); the "Y177 stub" was a fixed-address misread. The 28.4% delta reflects unrelated VIP changes, not a fixed security function.

---

## ProtoKey / ADB Authentication

> **CORRECTED 2026-08-26.** This exchange gates **ADB / seed authentication**, not SELinux
> enforcement. SELinux is enforcing on all builds regardless (OS-side init). The former
> "→ SELinux ENFORCING/PERMISSIVE" outcomes are wrong and have been replaced with the
> real ADB-unlock outcome, confirmed from device logs (`GM_ADB: gm_adb_auth_init`) and the
> VIP DID `0xF1A0` trace.

The EEPROM SBI flag drives a VIP→SoC security-state response that determines whether ADB is
permitted without a cloud/PAL certificate:

### Secured Operation (EEPROM 0x0440 data byte = 0x00 / stock marker `C3 00 C3`)

1. `gm_protokey` runs at boot (`init.protokey.rc`, `post-fs-data`) and validates the stored
   security state (`/data/vendor/gm/security/.validation`), setting `vendor.gm.security.state`
2. VIP reports the secured SBI value; SoC-side `gm_adb_auth_init` leaves `is_secure_mode=0`
3. ADB requires the normal GM Secure-ADB cloud/PAL certificate path

### Bypassed Operation (EEPROM 0x0441 data byte = 0xFF / bypass marker `5A FF 5A`)

1. VIP reads the SBI DATA byte, sees `0xFF` (marker-agnostic — the check reads only the data byte)
2. VIP transmits MEC=0xFF in its DID `0xF1A0` response to the SoC
3. SoC-side `gm_adb_auth_init` sets `is_secure_mode=1` → ADB allowed with **no cloud cert**

> **Live-vehicle corroboration (2026, MDI2 DoIP `dps_readx80` read of radio `0x80`).** `$22 F1A0`
> returned **`0xFF`** on the vehicle — the first on-vehicle confirmation of the MEC=0xFF path above
> (prior evidence was EEPROM/teardown only). Nuance on `$27`: that read (SPS "security validation
> facility failed") got an **all-`0xFF` seed**, while valid SPS sessions used an **8-byte seed /
> 6-byte key** and succeeded (ECUs 0x80/0x81/0xBE, `67 02` grants). So the all-FF `$27` seed is the
> **SPS-credential-absent path**, not necessarily a hardware SBI flip — worth separating in
> `$27`/SBI analysis. (Redacted diagnostic-session reports: `/Volumes/.../2024_Silverado_ICE/emu/y181_ref/diag/`.)

The same degenerate `0xFF` value also appears on the VIP's plain diagnostic UDS stack, so the
effect is broader than ADB/ICUSB alone. It does **not** change SELinux mode.

## Ethernet UDS `$27` SecurityAccess — VIP-side forwarding, off-SoC (2026-09)

Distinct from the ADB/seed-auth bypass above: this is the `diagnosticsd`
Ethernet-diagnostic (`:49156`) `$27` SecurityAccess gate documented fully in
[`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md).
Recorded here because it resolves the same underlying SBI-fail-open question
from the diagnostic-Ethernet side and because an earlier revision of that doc
mis-attributed the seed/key algorithm to `gm_protokey` (retracted there — see
its `[D] CORRECTION`).

- **`ETHERNET`/`NOTIFICATION` tiers:** the `$27` compare is in-process, inside
  `diagnosticsd`'s statically-linked `libuds`
  (`UDSSecurityLevelCheckRequestHandler.cpp`, ISO-14229 attempt counter present).
  `checkSecurityLevelTable` is only the per-tier allowed-service table, not the
  seed/key gate.
- **`VIP` tier is forwarded off-SoC.** `diagnosticsd` holds no `VIP`-tier key
  material: `ProxyOfExtComp::handleUDSRequest` relays `MESSAGE_SECURITY_ACCESS_VIP`
  over a `SockAdaptor` TCP socket to the external VIP MCU, where the real
  compare — and the SBI EEPROM read — happen. **SBI EEPROM byte = `0xFF` =
  "Bypass Active"** relaxes the **VIP's own** key-compare, the same SBI flag
  documented under ProtoKey/ADB above, but enforced on a different component
  (the VIP's UDS stack, not `gm_adb_auth_init`). RE proves no SoC binary reads
  the SBI EEPROM directly — the SoC only ever *relays* the SBI/MEC-derived byte
  via `$22 F1A0` (`diagnosticsd` calls
  `vendor.gm.diagnostics.obd@1.0::IDiagnosticsObd::getManufacturingEnableCounter()`
  and returns it verbatim, unchecked).
- **Under normal (SBI-inactive) posture** an untrusted Ethernet peer's `$27`
  requestSeed still fails closed (`7F 27 10` generalReject) before any seed is
  issued — confirmed live, unprivileged shell probe (see the diagnosticsd doc).
- **This supersedes any earlier "possible fail-open (unconfirmed)" framing**
  for the SBI/`$27` relationship (see `research/AE_RESEARCH_HANDOFF.md`): the
  fail-open is **real**, gated on the SBI EEPROM byte, and enforced on the VIP
  MCU — not the SoC. It cannot be re-derived statically because the VIP MCU
  firmware's compare routine is not in this bench's artifact set.
- **Emulator note:** this bypass cannot be reproduced on the hybrid Android
  emulator (`platform/emulator.md`) — `IDiagnosticsObd` is unregistered,
  `diagnosticsd` is absent, and GM Secure-ADB is replaced by Google's stock
  `adbd`, so no secure-mode chain runs at all. The compare is off-SoC on real
  hardware, so it can only be *modeled* on the emulator (a synthetic external-
  component/VIP endpoint answering `$27`) — a substantial un-stub, not a quick
  one.

> **[C] live-Y175 2026-10-05:** The EEPROM-SBI→VIP MEC=0xFF→`is_secure_mode`→DID `0xF1A0` chain and the `$27`/`$22 F1A0` traces are **UNVERIFIABLE-FROM-LIVE** (EEPROM/VIP/DoIP, not reachable from a locked user shell). Posture note: this unit is in **secured** operation, not the bypass path — `ro.secure=1`, `ro.adb.secure=1`, `ro.debuggable=0`, and our adb shell is the normal authorized uid 2000 (`u:r:shell:s0`), i.e. adb via the standard path, not an `is_secure_mode=1` no-cert unlock. `diagnosticsd` is live as native `gm_diagnosticsd` (PID 590).

### gm_protokey Service

- **Binary:** `/vendor/bin/gm_protokey` (+ `gm_protokey_recovery`)
- **Init:** `init.protokey.rc`, class `main`, user `root`, oneshot
- **SELinux domain:** `gm_protokey` [C] live-Y175 2026-10-05: CONFIRMED — process `gm_protokey` PID 889, user root, context domain `gm_protokey` (ps.txt). Binary path and `init.protokey.rc` not in capture set (UNVERIFIABLE-FROM-LIVE).
- **Function:** validates the persisted GM security state and sets `vendor.gm.security.state`;
  it is part of the ADB/seed-auth path, **not** a SELinux enforcement selector. (Note:
  `androidboot.bootreason=warm` makes `gm_protokey` skip validation — a documented bypass path.)

---

## MEC (Module Event Counter)

The MEC counter tracks consecutive SoC boot failures and progressively disables recovery mechanisms:

| MEC Value | Behavior |
|-----------|----------|
| MEC = 0 | Normal operation. VIP monitors GHS hypervisor startup, enforces timeouts. |
| MEC != 0 (e.g. 207) | Ignores hypervisor startup timeout. Allows extended boot times. |
| MEC >= 3 | After 3 consecutive SoC failures: hypervisor timer **DISABLED**, CSM reset **DISABLED**. System enters degraded monitoring state. |

> **[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE** — MEC counter state/behavior is VIP-side, not observable from the user shell.

---

## EEPROM Security

**Device:** ST M24C64, 8KB, I2C address `0x50`

- Security flags located at offsets `0x0440`, `0x0A80`, `0x0B40`
- CRC is present but **NOT enforced** at boot (write-and-reboot bypass possible)
- CalGroup markers are runtime-generated, not static EEPROM values
- **I2C buses 0, 1, 2, AND 3 are world-writable** — this is a privilege escalation vector, as any process with filesystem access can read/write EEPROM contents
  - i2c-0: general purpose
  - i2c-1: general purpose
  - i2c-2: system bus
  - i2c-3: audioserver bus
  > **[C] live-Y175 2026-10-05: CONFIRMED** (dev_listing.txt): `i2c-0 crw-rw-rw- root:root u:object_r:saturnhd_device:s0`, `i2c-1 crw-rw-rw- root:root i2c_device`, `i2c-2 crw-rw-rw- system:system i2c_device`, `i2c-3 crw-rw-rw- audioserver:audioserver dirana3_device`. All four are mode `0666`. (i2c-4/5/6/8/9/10 are `crw-------` root; i2c-7 `crw-rw---- system` display_panel.) The EEPROM-at-0x50 contents, CRC-not-enforced, and SBI-flag claims below remain **UNVERIFIABLE-FROM-LIVE** — this DISK-ONLY audit did not (and must not) i2c-probe the live device.
- Empirically, the ADB-enabled dump shows **both** `0x0440` and `0x0A80` flipped to `5A FF 5A FF`. The claim that both cells *must* match for the bypass to hold is an **unverified mechanism** — there are zero code references to the literal address `0x0A80` in either VIP binary, and the security check reads only the DATA byte (marker-agnostic). The empirical bypass-works observation stands; only the hardcoded second-address mechanism is disputed.
- A post-Y181 reflash re-initializes the backup cell to `F0 00 F0` (initialized+locked). The earlier claim that a specific calibration file (85783460) targets and resets these flags is **REFUTED** (2026-08) — those bytes live inside a gzip-compressed CalOvride XML stream, not an EEPROM address:value table. SBI values change only via the VIP's bulk restore-to-ROM-defaults routine (`FUN_ram_000c6564`, reached on an AUTOSAR NvM CRC/validity failure), not a targeted cal payload.

### EEPROM Memory Map

| Offset Range | Function | Details |
|--------------|----------|---------|
| `0x0000`-`0x005F` | Header & Boot Flags | `0x0001` boot state: `0x00`=virgin, `0x01`=normal, `0xFF`=corrupted |
| `0x0400`-`0x045F` | Security Configuration | **OUTSIDE CRC protection** — modifications not detected |
| `0x0440` | Primary SBI Flag | Data byte at `0x0441`: `0x00`=secured, `0xFF`=bypass |
| `0x05C0`-`0x05D1` | VIN (Vehicle ID Number) | 17-byte VIN storage |
| `0x0A80` | Backup SBI Flag | Stock = uninitialized (`FF FF FF`); ADB-bypass = `5A FF 5A FF`; post-Y181 reflash = `F0 00 F0` (initialized+locked). Data byte `0xFF` = bypass; marker (`5A`/`69`/…) is variant/CalGroup-specific |
| `0x0B40` | Debug Mode Flag | Data byte at `0x0B41`: `0x00`=off, `0x01`=debug enabled |
| `0x16E0` | CRC Location 1 | NOT enforced at boot |
| `0x19E0` | CRC Location 2 | NOT enforced at boot |
| `0x1A80` | CRC Location 3 | NOT enforced at boot |
| `0x1B40` | CRC Location 4 | NOT enforced at boot |

**CRC bypass confirmed:** Tested with corrupted VIN at `0x05C0` — system boots normally, CRC mismatch ignored.

### EEPROM Framing Markers

| Marker Byte | Type |
|-------------|------|
| `0x5A` | Security |
| `0x69` | Configuration |
| `0xF0` | Data |
| `0xC3` | Calibration |

### EEPROM Attack Surface

The combination of unenforced CRC and world-writable I2C buses means that EEPROM contents (including security flags and calibration data) can be modified by any user-space process without requiring elevated privileges. Changes persist across reboots since CRC validation is not enforced during boot. The security configuration region (`0x0400`-`0x045F`) is deliberately outside CRC protection, meaning even if CRC were enforced, SBI flag modifications would not be detected.

---

## Kernel Security Mitigations

> **[C] live-Y175 2026-10-05:** Kernel string CONFIRMED: `4.19.283-PKT-230612T042614Z-ga53d763f5b0d #1 SMP PREEMPT Wed Jun 26 2024 x86_64`. The mitigation/CONFIG tables below are build-time kernel config and are **UNVERIFIABLE-FROM-LIVE** (no `/proc/config.gz` or `dmesg` in the capture set) — do not treat KASLR/SMEP/SMAP/retpoline/CONFIG_* rows as confirmed on this unit.

| Mitigation | Status |
|------------|--------|
| KASLR | Enabled |
| Stack Protector | Enabled |
| SMEP/SMAP | Enabled |
| Spectre v2 | Mitigated (IBRS/IBPB) |

### Kernel CONFIG Flags

#### Enabled (hardening active)

| Config Flag | Purpose |
|-------------|---------|
| `CONFIG_STACKPROTECTOR_STRONG` | Stack buffer overflow detection (strong variant) |
| `CONFIG_STRICT_KERNEL_RWX` | Kernel text/rodata marked read-only, data non-executable |
| `CONFIG_STRICT_MODULE_RWX` | Same protections applied to loadable kernel modules |
| `CONFIG_RANDOMIZE_BASE` | KASLR — randomize kernel base address |
| `CONFIG_RANDOMIZE_MEMORY` | Randomize physical memory mapping |
| `CONFIG_RETPOLINE` | Spectre v2 mitigation via retpoline thunks |
| `CONFIG_X86_SMAP` | Supervisor Mode Access Prevention — kernel cannot access userspace memory |
| `CONFIG_X86_INTEL_UMIP` | User-Mode Instruction Prevention — blocks SGDT/SIDT/SLDT/SMSW/STR from ring 3 |
| `CONFIG_X86_INTEL_MEMORY_PROTECTION_KEYS` | Hardware memory protection keys (PKU) |
| `CONFIG_SECCOMP` | Syscall filtering for sandboxed processes |
| `CONFIG_HARDENED_USERCOPY` | Runtime bounds checking on copy_to/from_user |
| `CONFIG_INIT_ON_ALLOC_DEFAULT_ON` | Zero-fill heap allocations (info leak prevention) |
| `CONFIG_SLAB_FREELIST_RANDOM` | Randomize SLAB freelist order (heap spray mitigation) |
| `CONFIG_BPF_JIT_ALWAYS_ON` | Force BPF JIT (disables interpreter, reduces attack surface) |
| `CONFIG_X86_INTEL_TSX_MODE_OFF` | TSX disabled (mitigates TAA/MDS side-channel attacks) |

#### Disabled (attack surface reduction)

| Config Flag | Significance |
|-------------|-------------|
| `CONFIG_USER_NS` is not set | No unprivileged user namespaces — blocks container escape primitives |
| `CONFIG_MODIFY_LDT_SYSCALL` is not set | No LDT modification — blocks certain exploitation techniques |
| `CONFIG_LEGACY_VSYSCALL_NONE` | No legacy vsyscall page — removes known-address gadget source |
| `CONFIG_KVM` is not set | No KVM virtualization — reduces hypervisor attack surface |
| `CONFIG_NF_TABLES` is not set | No nftables — eliminates entire class of netfilter vulnerabilities |
| `CONFIG_USERFAULTFD` is not set | No userfaultfd — blocks common race condition exploitation technique |
| `CONFIG_IO_URING` is not set | No io_uring — eliminates major recent vulnerability source |

#### Missing (gaps in hardening)

| Config Flag | Impact |
|-------------|--------|
| `CONFIG_SLAB_FREELIST_HARDENED` | Not set — freelist pointer obfuscation absent, heap metadata corruption easier |
| `CONFIG_SECURITY_YAMA` | Not set — no ptrace scope restrictions, any process can ptrace others |

#### SELinux Kernel Support

`CONFIG_SECURITY_SELINUX_DEVELOP=y` — the kernel **supports** permissive mode at compile time, but the stock userspace does not use it: Y175/Y177/Y181 ship a byte-identical `init` that forces enforcing (`ALLOW_PERMISSIVE_SELINUX=0`), so all three run **enforcing** at runtime. SELinux mode is set OS-side (ramdisk/init) and is **not** controlled by the VIP security function or `gm_protokey` (CORRECTED 2026-08-26; the old "Y177 stub → permissive" framing was a fixed-address misread — the VIP validator is full in all builds and gates ADB/seed auth, not SELinux).

> **[C] live-Y175 2026-10-05: CONFIRMED (strong).** The live radio carries `ro.boot.selinux=permissive` in props (kernel cmdline) yet runs **Enforcing** at runtime (`getenforce`=Enforcing; all 179 `avc` lines `permissive=0`). This is direct on-device proof that userspace/init overrides the cmdline permissive request — the exact mechanism this section asserts. (`CONFIG_SECURITY_SELINUX_DEVELOP=y` itself is UNVERIFIABLE-FROM-LIVE, no config capture.)

---

## File-Based Encryption (FBE)

| Property | Value |
|----------|-------|
| `ro.crypto.state` | `encrypted` |
| `ro.crypto.type` | `file` |
| Cipher | `aes-256-xts:aes-256-cts` |
| Metadata Encryption | `dm-default-key` |
| Keystore Backend | Trusty TEE via GHS (`ro.hardware.keystore=trusty`) |

> **[C] live-Y175 2026-10-05:** `ro.hardware.keystore=trusty`, `ro.hardware.gatekeeper=trusty`, `ro.boot.trustyimpl=-ghs` all CONFIRMED (props); `init.svc.keystore2=running`, `init.svc.gatekeeperd=running`; `/dev/trusty-ipc-dev0` present (`tee_device`). Cipher/`ro.crypto.*` string values (`aes-256-xts…`) not individually dumped — metadata method `dm-default-key` and `persist.sys.gm.encryption=true` CONFIRMED; the exact cipher line is UNVERIFIABLE-FROM-LIVE. **Note:** `/dev/trusty-ipc-dev0` is `crw-rw-rw-` (mode 0666, world-rw) — the TEE IPC node is DAC-open to any process (SELinux `tee_device` label gates actual access).
>
> **[C] Y181.3.2-ref 2026-10-06: still PARTIAL — the contents-cipher and active-FBE claims are NOT confirmable on this reference, because the emulator build has Trusty/FBE disabled.** Root readout on the Y181.3.2 reference: `ro.crypto.state=unencrypted` (NOT `encrypted`/`file`), and the `/data` line in `/vendor/etc/fstab` is `f2fs` with **no** `fileencryption=`/`metadata_encryption=` flag — so FBE is not configured or active on this VM. The fstab carries the comment *"Commented out tos and multiboot for disabling trusty"*, `ro.hardware.keystore` is unset, and there is **no `/dev/trusty*`/`tee` node** — this reference runs software crypto, not the GHS-Trusty TEE. Only the `filenames` half and the metadata method survive as build-default props: `ro.crypto.volume.filenames_mode=aes-256-cts`, `ro.crypto.volume.metadata.method=dm-default-key`, `ro.crypto.volume.options=::v2` — partially corroborating the `…:aes-256-cts` table cell, but the contents cipher `aes-256-xts` and active FBE **remain UNVERIFIABLE** even on root. Do not upgrade this row from the Y175 verdict.

---

## Trusty TEE (Trusted Execution Environment)

The Trusty TEE runs under GHS INTEGRITY hypervisor, providing hardware-backed key storage and cryptographic operations.

### TEE Services

| Service | Function |
|---------|----------|
| `TEE_Keymaster` | Hardware-backed key generation, storage, and operations |
| `TEE_HW_Crypto` | Hardware cryptographic acceleration |
| `TEE_Storage` | Secure storage via RPMB (Replay Protected Memory Block) |

### ELF Sections

TEE code is loaded from dedicated ELF sections in the hypervisor image:
- `.tee_keymaster.text` — Keymaster executable code
- `.tee_keymaster.data` — Keymaster mutable data
- `.tee_keymaster.rodata` — Keymaster read-only data

### HAL Configuration

- **HAL:** `keymaster@3.0` (Trusty-GHS implementation)
- **Init script:** `init.trusty-ghs.rc`
- **Properties set at init:**
  - `ro.hardware.gatekeeper=trusty`
  - `ro.hardware.keystore=trusty`

---

## GHS Device Interfaces

The GHS INTEGRITY hypervisor exposes the following device interfaces under `/dev/ghs/`:

| Interface | Purpose |
|-----------|---------|
| `textlog` | Hypervisor text logging |
| `audit` | Security audit log |
| `snapshot-dbg` | Debug snapshot capture |
| `ipc` | Inter-VM communication |
| `cal` | Calibration data interface |
| `camera` | Camera subsystem bridge |
| `chime` | Chime/alert audio interface |
| `tee-att` | TEE attestation |
| `emmc-health` | eMMC health monitoring |
| `ota-isys` | OTA update interface (ISYS) |
| `gpu-dbg` | GPU debug interface |

> **[C] live-Y175 2026-10-05:** `/dev/ghs` exists as a directory (`drwxr-xr-x root root u:object_r:device:s0`) and `/dev/ghscamerafb` (`crw------- root`) is present, but the capture did not enumerate `/dev/ghs/` children — the individual interface names (textlog/audit/ipc/cal/…) are **UNVERIFIABLE-FROM-LIVE**.
>
> **[C] Y181.3.2-ref 2026-10-06: still UNVERIFIABLE on this reference — the GHS hypervisor is absent from the emulator.** Root on the Y181.3.2 VM: `/dev/ghs` **does not exist** (`[ -e /dev/ghs ]` → absent), and there are no `/dev/ghs*` or `/dev/trusty*` nodes. This reference is a QEMU/HVF VM with no GHS INTEGRITY hypervisor and no TEE (see the FBE note above / the fstab "disabling trusty" comment), so the `/dev/ghs/` child interface names cannot be enumerated here. The table above (textlog/audit/ipc/cal/…) is NOT confirmed by this reference; it still needs a live GHS-backed unit. NOTE: the sibling `/dev/ipc/*` GHS-style IPC sockets DO exist on this VM (e.g. `ipc10`-`ipc15` `srw-rw---- system`, `ctrlif_s` `vehicle_network`) — a different interface family from the `/dev/ghs/` children claimed here.

---

## GM SELinux Domains

### Critical Service Domains

| Domain | Function | Notes |
|--------|----------|-------|
| `gm_vnd_IPCServer` | VIP MCU IPC communication | Runs as **ROOT**, handles HDLC protocol on `/dev/ttyS1` |
| `gm_diagnosticsd` | UDS diagnostic service | Handles $10/$22/$27/$2E/$31/$34/$36/$37 commands |
| `gm_update_engine` | OTA firmware updates | GM fork of AOSP A/B update_engine. (Note: the `dontaudit gm_update_engine gsi_metadata_file` rule in `vendor_sepolicy.cil` is **not** a GSI blocker — see GSI/DSU Status below.) |
| `gm_vehicle_hal` | Vehicle HAL implementation | Bridge between Android and VIP/CAN |
| `gm_protokey` | Security-state validation (ADB/seed auth) | Validates the persisted GM security state; part of the ADB/seed-auth path, NOT a SELinux enforcement selector (corrected 2026-08-26) |

> **[C] live-Y175 2026-10-05: all five service domains CONFIRMED live as running processes (ps.txt):** `gm_vnd_IPCServer` (procname IPCServer, PID 386, **root**) — consistent with the "runs as ROOT / VIP IPC" claim; `gm_diagnosticsd` (590, root); `gm_update_engine` (574, root); `gm_vehicle_hal` (`android.hardware.automotive.vehicle@2.0-service-gm`, PID 792, user **vehicle_network** — NOT root); `gm_protokey` (889, root). The `/dev/ttyS1` HDLC/20-channel and HDLC-v16 details are not probed here; `/dev/ttyS1` perms CONFIRMED `crw------- root:root u:object_r:ipc_serial_device:s0` (mode 0600, i.e. root-only — see IPC/Serial table note).

### Vehicle HAL Clients

The following domains have access to Vehicle HAL properties:

- `system_server`
- `gmConnectionService`
- `camerad`
- `plmanager`
- `vehicleaudiocontrol`

> **[C] live-Y175 2026-10-05:** `system_server`, `gmConnectionService`, and `vehicleaudiocontrol` (as `gm_vnd_vehicleaudiocontrol`, PID 588) are live processes; `camerad`/`plmanager` not separately confirmed. This is a sepolicy allow-list claim — no sepolicy file was pulled in this capture, so the *access-grant* itself is **UNVERIFIABLE-FROM-LIVE** (process presence is not policy proof).
>
> **[C] Y181.3.2-ref 2026-10-06: allow-list CONFIRMED against live on-device CIL (root).** The Vehicle HAL `android.hardware.automotive.vehicle::IVehicle` is labeled `u:object_r:hal_vehicle_hwservice:s0` (`/system/etc/selinux/plat_hwservice_contexts:16`). `hwservice_manager find` on it is granted to exactly one subject — the attribute **`hal_vehicle_client`** (`/system/etc/selinux/plat_sepolicy.cil:11213` `(allow hal_vehicle_client hal_vehicle_hwservice (hwservice_manager (find)))`), guarded by a neverallow at `:11223`. The five domains above are all members of that attribute: `system_server`, `gmConnectionService`, `camerad`, `plmanager`, `gm_vnd_vehicleaudiocontrol` are in the `hal_vehicle_client` typeattributeset in `/vendor/etc/selinux/vendor_sepolicy.cil`, and `carservice_app` is added in `/product/etc/selinux/product_sepolicy.cil` (one extra member not listed above). So the allow-list is correct for **Y181.3.2** (all five present; mechanism = single attribute-based `find` grant + neverallow). Only *inferred* for Y175/Y177 (no bootable Y175 policy). NOTE: this is the generic AOSP vehicle HAL (`hal_vehicle_hwservice`), distinct from the GM framework `gm_domain_service` vehicle services (`VehicleSettingsService`/`VehicleCompanionAppService` at `product_service_contexts:34/40`) and `gm_vehiclemanager_service` (`:50`).

### GSI/DSU Status (corrected)

**Earlier claim (wrong):** that `dontaudit gm_update_engine gsi_metadata_file` blocks GSI
installs. It does not. `dontaudit` only suppresses the audit log of a denial that already
happens from the absence of an allow rule — it is not an enforcement mechanism — and it
targets `gm_update_engine` (GM's OTA A/B engine), not the DSU path.

**What actually disables GSI/DSU on this unit:**

- `com.android.dynsystem` (the DSU installer app) is **removed** from the image — absent
  from the live 89-package set (Y181, Apr 2026). The `am start … VerificationActivity …
  START_INSTALL` intent fails with activity-not-found.
  > **[C] live-Y175 2026-10-05:** package-count "89 (Y181)" is Y181-SCOPE — live **Y175** has **100** packages (98 system, 2 third-party, 1 disabled `com.android.nfc`); `com.android.dynsystem` not seen in the Y175 package/perm/service captures (consistent with removal, but the Y175 set was not exhaustively grepped for it — treat as supported, not proven). The boot-gate half IS CONFIRMED on live Y175: `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `verifiedbootstate=green`, `sys.oem_unlock_allowed=0`, `ro.build.type=user`, `ro.debuggable=0`, shell uid 2000 — a staged GSI could not boot.
- The `gsid` daemon and `gsi_tool` are retained with **full stock SELinux policy**, so the
  block is not at the policy layer. The direct `gsi_tool` path is closed instead by the
  user build (`ro.build.type=user`, `ro.debuggable=0`, shell is uid 2000) and the
  `MANAGE_DYNAMIC_SYSTEM` signature-or-privileged permission the shell lacks.
- Booting any staged GSI is gated by locked verified boot (`ro.boot.flash.locked=1`,
  device_state `locked`, verifiedbootstate `green`, `sys.oem_unlock_allowed=0`). fstab
  trusts only the Google GSI keys (q/r/s), so only a Google-signed GSI could pass AVB.

Full detail and provenance in [`platform/boot_chain.md`](boot_chain.md#gsidsu-status).

---

## Key CVEs

> **CORRECTED 2026-08-26.** The prior table premised Y177 exploitability on "SELinux permissive."
> That premise is FALSE — Y177 and Y181 both run SELinux **enforcing** (byte-identical init). The
> kernel-vulnerability presence differs by **security-patch level and kernel version**, not by
> SELinux mode; SELinux enforcing provides the same MAC containment on both builds.

| CVE | CVSS | Description | Kernel status (Y177 & Y181) |
|-----|------|-------------|-----------------------------|
| CVE-2024-53104 | 7.8 | UVC (USB Video Class) vulnerability | Both enforce SELinux; patch status tracks the build's kernel (4.19.305) / patch level (Y177 2025-03-05, Y181 2025-06-05) |
| CVE-2024-36971 | 7.8 | dst_cache UAF (use-after-free) | Same — gated by patch level, not by SELinux mode |
| CVE-2024-53150 | 7.8 | USB out-of-bounds read (Cellebrite chain) | Same |
| CVE-2024-53197 | 7.8 | USB ALSA out-of-bounds access (Cellebrite chain) | Same |
| CVE-2023-2163 | 8.8 | BPF verifier range tracking | Requires `CAP_BPF`; SELinux enforcing (both builds) restricts BPF to authorized domains |
| CVE-2024-1086 | 7.8 | nf_tables use-after-free | **NOT APPLICABLE** — `CONFIG_NF_TABLES` not set |

> **[C] live-Y175 2026-10-05:** This table scopes to **Y177 & Y181** (kernel 4.19.305, patch 2025-03/06) — Y181-SCOPE relative to the live unit. Live **Y175** runs kernel `4.19.283` / patch `2024-05-05` (older than both), so per-build patch-status cells do NOT transfer to Y175. `CONFIG_NF_TABLES`/`CONFIG_BPF_JIT_ALWAYS_ON` config claims are UNVERIFIABLE-FROM-LIVE. SELinux-enforcing containment premise CONFIRMED for Y175 (runtime Enforcing).

**CVE-2024-53150 / CVE-2024-53197:** Part of the Cellebrite USB exploitation chain; added to CISA KEV in April 2025 and actively exploited for mobile forensics. On both Y177 and Y181 the SELinux enforcing policy restricts USB driver access to authorized domains; there is no permissive-Y177 window. Residual exposure depends on the kernel patch level for the specific build.

**CVE-2023-2163:** BPF verifier out-of-bounds memory access, requires `CAP_BPF`. On both builds SELinux enforcing restricts BPF access to authorized domains, and `CONFIG_BPF_JIT_ALWAYS_ON` reduces interpreter attack surface (though it does not prevent a verifier bypass).

**CVE-2024-1086:** Not applicable — `CONFIG_NF_TABLES` is not set in kernel config, so the vulnerable nf_tables subsystem is not compiled into the kernel.

The earlier claim that "both Y177 CVEs are exploitable due to SELinux permissive" is retracted: SELinux is enforcing on both builds, so exploitation containment is identical and any difference reduces to the kernel patch level.

---

## Attack Surface Analysis

> **[C] Phase 1 offensive audit (Sep 2026) — single most severe finding.** Static RE of decompiled
> Y181 APKs found `IGMAuthService` (host process `com.gm.authtoken`, uid `system`) gates
> `getAuthTokenByUserID`/`setAuthTokenByUserID`/`removeAccount`/`getGuestAccountToken` behind three
> custom permissions (`gm.permission.authentication.{ID|CLIENT|USER}`) that are shipped with
> `protectionLevel=normal` — auto-granted at install to any app that simply declares them, no
> signature match, no prompt. Any sideloaded third-party app can therefore exfiltrate live
> GM/OnStar bearer tokens from the on-device `authtokens` SQLite DB, forge/replace tokens for
> arbitrary users, or lock out an account. The `protectionLevel=normal` permission grant itself is
> confirmed live (`dumpsys package permissions`, not an emulator/root artifact). **[C] Corrected
> (2026-09-27):** the `service_manager find`-on-`gm_authToken_service`-granted-to-`untrusted_app` sepolicy
> line is confirmed at `product_sepolicy.cil:586` — but only in **Y177's** pulled sepolicy; Y181's own
> pulls never captured a product-partition sepolicy file (grep for "authtoken" across all Y181 pulls
> returns zero hits). GM likely reuses this component/policy across Y177→Y181, but that transferability
> is inferred, not independently confirmed on Y181 — do not cite this as "confirmed under SELinux
> Enforcing" for Y181 specifically until a Y181 product-partition sepolicy pull closes the gap. Full ranked findings (including a same-class
> systemic `prot=normal` issue across the `com.gm.vehicle.permission.READ_*` telemetry family, an
> unauthenticated cluster/HUD display-injection surface, and two new FSA UDP/multicast bugs):
> [`../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).
>
> **[C] live-Y175 2026-10-05:** the `prot=normal` core of this finding is CONFIRMED on live Y175 — `permissions_full.txt` shows `gm.permission.authentication.{ID,CLIENT,USER}` all `protectionLevel=normal`, owner `com.gm.authtoken`; host `com.gm.authtoken` runs as **system** (`system_app`, PID 2139); binder `gm_auth` (`gm.authtoken.IGMAuthService`) and `gmBOAgent` (`gm.authtoken.IGMBOAgentService`) are both registered (services.txt #108/#107). So a normal-tier auth-permission grant to any app is live-real on Y175, not Y181-only. The `product_sepolicy.cil:586` `service_manager find`→`untrusted_app` line remains **Y177-SCOPE / UNVERIFIABLE-FROM-LIVE** (no product-partition sepolicy pulled; see the doc's own 2026-09-27 caveat). The systemic `com.gm.vehicle.permission.READ_*` `prot=normal` family is likewise CONFIRMED live (59 GM-owned `normal` perms incl. 18 `READ_*` vehicle twins of `*_PROTECTED` sig|priv perms).
>
> **[C] Y181.3.2-ref 2026-10-06: VERDICT-FLIP — the `untrusted_app` → `gm_authToken_service` `find` grant IS present on Y181, at the exact line.** Read from the live on-device product CIL (root, Enforcing): `/product/etc/selinux/product_sepolicy.cil:586` is verbatim `(allow untrusted_app gm_authToken_service (service_manager (find)))`. It is not line-586-only — lines 583-588 grant `find` to the whole untrusted/app spread: `untrusted_app_all` (583), `ephemeral_app` (584), `mediaprovider` (585), `untrusted_app` (586), `untrusted_app_27` (587), `untrusted_app_25` (588); also `graphic_dump` (1200), `platform_app` (1405), `priv_app` (1409), `system_app` (1454). Service label: `gm_auth` **and** `gmBOAgent` → `u:object_r:gm_authToken_service:s0` (`product_service_contexts:65-66`); both registered live (`service list`: `gm_auth: [gm.authtoken.IGMAuthService]`, `gmBOAgent: [gm.authtoken.IGMBOAgentService]`). This **closes the 2026-09-27 gap for Y181 specifically**: the SELinux `find`-reachability half is now confirmed under Enforcing on Y181.3.2 (same line number 586 as the Y177 pull). The matching line number across Y177 and Y181.3.2 is strong evidence of the inferred Y177→Y181 policy reuse — but Y175 remains *inferred only* (no bootable Y175 policy). The `authtokens` SQLite store is `/data/gmauth/gmtokens.db`, DAC `-rw-rw---- system:system` (0660), SELinux `u:object_r:gm_authToken_system_data_file:s0` (file_contexts `/data/gmauth(/.*)? → gm_authToken_system_data_file`, `product_file_contexts:4`); the `/data/gmauth` dir is `drwxrwxrwx` (0777) but the DB file is 0660 and MAC grants file/dir access only to `system_app` (`product_sepolicy.cil:1452-1453`). So **direct file-read exfil of the DB is DAC+MAC-blocked for a sideloaded `untrusted_app`**; the real exposure is the Binder path — `untrusted_app` may `find` the service (line 586) and the three `gm.permission.authentication.*` gates are `prot=normal`, so the `getAuthTokenByUserID` route is reachable without a direct DB read.

### GMWlanService SoftAP credential exposure — SELinux-only gate (2026-10-05)

> **[C] Finding.** GM's custom binder service `com.gm.server.wlanservice` (interface
> `gm.wifi.IGMWlanService`, registered on Y175/Y177/Y181 — `service_list.txt` →
> `[gm.wifi.IGMWlanService]`) exposes transaction **7** `getWifiApConfiguration()`, which returns a
> full `android.net.wifi.SoftApConfiguration` — i.e. the head-unit SoftAP (hotspot) **SSID *and*
> passphrase**. The server applies **no application-level permission or uid/pid check**: on the CT5
> 2026 tree, `GMWlanService` publishes via `DomainService.publishBinderService` →
> `ServiceManager.addService(name, service, false)` (`allowIsolated=false` only, no permission
> string), `GMWlanServiceBinder extends IGMWlanService.Stub` does **not** override `onTransact`, and
> `GMWlanServiceImpl.getWifiApConfiguration()` (`.../2026_CT5/emu/re/loc/out/sources/com/gm/server/wlanservice/GMWlanServiceImpl.java:538-552`)
> builds and returns the config with zero guard. A package-wide grep for
> `enforceCall*|checkPermission|getCallingUid|getCallingPid|SecurityException|onTransact` over the
> server dir returns nothing. Contrast stock `WifiManager.getSoftApConfiguration()`, which is
> signature-gated (`NETWORK_SETTINGS`/`OVERRIDE_WIFI_CONFIG`/`READ_WIFI_CREDENTIAL`, all intact at
> `signature`/`system|signature` in `framework-res` AndroidManifest).
>
> **The only barrier is SELinux `service_manager:find`.** The service is labeled with the **base**
> type `gm_domain_service` (`.../gm_prod/product_service_contexts:30`). A normal third-party
> `untrusted_app` is granted `find` **only on the sibling** `gm_domain_service_nav`
> (`product_sepolicy.cil:855` Silverado / `:1446` CT5) — there is **no** `(allow untrusted_app
> gm_domain_service (service_manager find))` anywhere, and no attribute backdoor (`gm_domain_service`
> is only in `service_manager_type`, which carries neverallow on `add`). Policy is Enforcing on every
> capture. **So a plain sideloaded app is blocked at the SELinux layer and cannot reach the binder.**
>
> **Residual exposure (real):** `priv_app` and `platform_app` *are* granted find on the base type
> (`product_sepolicy.cil:851`/`:850`), and the server checks nothing — so **any
> privileged/preinstalled app (not necessarily GM-signed) reads the SoftAP passphrase with no
> permission.** This is a privilege-scoping defect of the same class as the `IGMAuthService`
> `prot=normal` finding above: reachability is decided purely by SELinux domain, with no in-service
> caller identity check.
>
> **[C] Server-guard confirmed on a Y181.3.2 image (2026-10-05).** Originally the server impl was
> decompiled only on the CT5 2026 tree. It is now independently confirmed on a booted **Y181.3.2**
> reference (`W231E-Y181.3.2-SIHM22B-499.3`, root via emulator): the registered server
> `com.gm.server.wlanservice.GMWlanServiceBinder` → `GMWlanServiceImpl.getWifiApConfiguration` lives
> in **`/system/priv-app/DelayedWKSApp/DelayedWKSApp.apk`** and is a pure delegate returning the
> `SoftApConfiguration` (SSID+passphrase) with **no `getCallingUid`/`enforce*`/`check*Permission`/
> `clearCallingIdentity`** in the chain (the APK uses such primitives ~300× elsewhere, zero here).
> `TRANSACTION_getWifiApConfiguration=7` on Y181 too; service index 71 (Y175 bench = 69). So the
> server-no-check half is now confirmed by **two independent sources across variants** (CT5 decompile
> + Y181.3.2 image). The SELinux half is confirmed three ways: emulator-policy trees, **Y181's own
> `product_sepolicy.cil`** (`untrusted_app` find only on `gm_domain_service_nav`, never the base
> `gm_domain_service`), and the **live Y175 bench avc denial** below.
>
> **[C] Caveats — do not over-cite / Y175 vs Y181.** The reference image is **Y181.3.2**, NOT the
> **Y175.5.2** bench — do not cross-assert. No bootable Y175 x86 image exists, so the **Y175 server
> body remains formally uninspected** (identical interface descriptor + transaction map; server index
> 69). This is moot for *untrusted* apps on Y175 — the live bench avc denial (below) blocks them at
> SELinux regardless — but the "privileged-app reaches an unchecked server" residual exposure is
> *proven on Y181.3.2* and only *inferred* for Y175. SELinux label evidence for Y175 is from the
> Silverado/CT5 emulator policy trees plus the live bench denial. A bench PoC lives at `~/gm_wlan_poc`
> (installs as `untrusted_app`; logs tag `GMWLAN_POC`).
>
> **[C] Live-hardware confirmation (2026-10-05, device `W213E-Y175.5.2-SIHM22B`, gminfo37, SoftAP up
> as `benchd89`).** The PoC installed as a genuine `untrusted_app` (`u:r:untrusted_app:s0:c121,...`)
> and the SELinux `find` denial is confirmed verbatim in the on-device audit log — upgrading the
> Y175/Y181 reachability chain from emu-policy inference to a live capture:
> `avc: denied { find } for ... name=com.gm.server.wlanservice scontext=u:r:untrusted_app:s0:...
> tcontext=u:object_r:gm_domain_service:s0 tclass=service_manager permissive=0`. A plain 3P app
> therefore cannot reach the binder; `ServiceManager.getService` returns null. Stock
> `WifiManager.getSoftApConfiguration()` returned null to the unprivileged caller despite the AP
> being active. The `priv_app` path (residual exposure) was **not** exercised on-device — it needs
> `/system/priv-app` placement (remount/eng build).
>
> **adb-permission angle (live-tested, answers "can a granted permission unlock it").** Every
> credential permission is signature-tier and **not grantable via `adb shell pm grant`** — confirmed
> live: `pm grant ... OVERRIDE_WIFI_CONFIG` →
> `SecurityException: ... is not a changeable permission type` (same class for `NETWORK_SETTINGS`
> `signature`, `READ_WIFI_CREDENTIAL`/`OVERRIDE_WIFI_CONFIG`/`LOCAL_MAC_ADDRESS` `signature|privileged`,
> `NETWORK_SETUP_WIZARD` `signature|setup`). So **no adb-issued grant gives a 3P app the SoftAP
> credentials.** Only `ACCESS_FINE_LOCATION`/`COARSE` are `dangerous` (adb-grantable); with location
> a 3P app reads **Wi-Fi channel/frequency/BSSID of visible APs** via `WifiManager.getScanResults()`
> (observed `freqMHz=2437`, ch 6) — standard location-gated AOSP behaviour, no passphrase, and the
> SoftAP's own config stays behind the GM/SELinux gate.

### fastbootd reachable over direct USB OTG — [C live-Y175 2026-10-06]

On the **direct OTG bench line** (no GM receptacle hub — HSAL-2 → breakout with CC→GND `Rd` strap →
Mac), `adb reboot fastboot` brings up **fastbootd** (userspace fastboot, `is-userspace:yes`),
enumerating as USB **`8087:4ee0`** (Intel VID + Android fastboot PID) and **persisting in mode**.
Captured live via a macOS `ioreg` watcher (device present ~1m50s). This is the **only** pre-OS USB
interface the unit exposes: `adb reboot bootloader` (ABL), `recovery`, `edl`, `dnx` all stay
**USB-dark** until the OS returns (matches the older hub-path tests; the hub never surfaced fastbootd
either — the direct OTG line is what exposes it).

Read-only `fastboot getvar all` succeeded (information disclosure); **writes are barred**:
- Lock/secure: **`unlocked:no`, `secure:yes`** — no flash/unlock (consistent with
  `flash.locked=1` / `oem_unlock_allowed=0`). `oem device-info` and `partition-type:*` → **"Fastboot
  HAL not found" / "Unable to open fastboot HAL"**: GM shipped **no fastboot OEM HAL**, so there is
  no vendor command surface and no flashing backend exposed here.
- **No read-out, no ephemeral boot, no image download at all (device-confirmed 2026-10-06):**
  `getvar max-fetch-size` → **FAILED "fetch not supported on user builds"** → `fastboot fetch`
  refused (no partition read-out). `fastboot boot <valid-header img>` → **FAILED (remote:
  "Download is not allowed on locked devices")** — the radio rejects at the **download primitive**,
  before AVB even applies. Since `flash`/`stage`/`boot` all require that download, the **only**
  fastbootd capability on this locked unit is `getvar` (read-only). Any image operation requires
  first defeating the lock (`unlocked:no`) via the SBI/seed/AVB path.
- **`flashing`/`oem` verbs absent (device-confirmed 2026-10-06):** `fastboot flashing
  get_unlock_ability` → **"Unrecognized command"** (the whole `flashing` group is unimplemented, so
  `flashing unlock` isn't even a recognized verb here); `oem help` → "Unable to open fastboot HAL".
  So fastbootd on this unit = **`getvar all` only** — no unlock path, no OEM surface, no HAL vars.
- Disclosed: A/B slots (`slot-count 2`, **`current-slot:b`**); dynamic `super` (0x465000000) with
  logical `system/vendor/product_{a,b}`; `boot/vbmeta/bootloader_{a,b}`, `misc`, `metadata`,
  `data` (0x9C1800000) sizes; `security-patch-level 2024-05-05`; fingerprint `W213E-Y175.5.2`;
  `version-bootloader 2121-1`; `first-api-level 29`; `version-vndk 32`; `max-download-size`
  0x10000000 (256 MB); `cpu-abi x86_64`; `treble-enabled:true`; `dynamic-partition:true`.

**Assessment:** fastbootd is a privileged ramdisk/root pre-OS environment and leaks the full
partition/version map, but on a stock locked unit it is an **information-disclosure + staging**
surface, **not a flashing path** (locked + no OEM HAL). Reaching it still requires the two ADB
gates (CC `Rd` strap + EEPROM SBI) to issue `adb reboot fastboot` in the first place — see
[`../hardware/connectors.md`](../hardware/connectors.md) §"Bench ADB … receptacle MODEL". Returning
to the OS (`fastboot reboot`) auto-disables ADB (re-enable via Dev Options), per this unit's behavior.

### Network Services

| Bind Address | Port | Risk | Notes |
|--------------|------|------|-------|
| `0.0.0.0` | 6363 | LOW | **AVB audio daemon** (uid=1041), init-owned text IPC bus; arbitrary input → `"ERROR"`. Binds all interfaces but low value. |
| `0.0.0.0` | 7000 | MEDIUM | **AirPlay/AirTunes 320.17.8** (Cinemo libNmeCarPlay r14), CarPlay audio bridge on br0. (Not ADB.) |
| `0.0.0.0` | 49156 | **HIGH** | **diagnosticsd** root UDS-over-TCP bridge — full caps, no seccomp. App-layer UDS trust only (no OS peer check); 0x27 SecurityAccess gate. See [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md). |

> **[C] live-Y175 2026-10-05 (net_sockets.txt):** all three listeners CONFIRMED present with wildcard `0.0.0.0` bind.
> - **6363** LISTEN, **uid 1041** (AOSP `audioserver`; ps shows `pulseaudio` as audioserver) — uid CONFIRMED; "AVB audio daemon" process name not independently pinned (no socket→pid map in capture).
> - **49156** LISTEN, **uid 0 (root)** — CONFIRMED root; owning process not pinned in capture but consistent with `gm_diagnosticsd` (PID 590) running.
> - **7000** LISTEN, **uid 1001000 = `u10_system`** (also `:::7000`) — uid CONFIRMED. ADJUST: the bind is wildcard `0.0.0.0`/`::`, **not** br0-scoped as the note states, and the "AirPlay/AirTunes 320.17.8" identity is UNVERIFIABLE-FROM-LIVE (not derivable from the socket table). Note it runs under **user 10's** system uid, not uid 1000.

#### Host firewall & network segmentation — [C] 2026-10-06 (Y181 ruleset primary; Y175 behavioral)

Authoritative ruleset = **`/system/etc/iptables.rules`** (Y181, applied at boot via `iptables-restore`
under `netd`) — primary-sourced twice (live Y181.3.2 `iptables-save` + the 2026-09-09 Y181 capture,
both SHA256 `edab150…`). **Y175's ruleset file is not on the assets drive** (locked unit, no root
dump) — all Y175 statements below rest on live sockets + behavioral tests and are **single-source /
inferred; do not assume byte-identical to Y181 until a Y175 root read confirms it.**

- **A local on-device app is NOT confined by the SoftAP client firewall.** `INPUT` policy is `DROP`,
  but `-A INPUT -i lo -j ACCEPT` (`iptables.rules:6`) accepts *all* local-origin traffic
  unconditionally, while the `-i br0` allowlist (`:37-48`) only governs packets ingressing from an
  external SoftAP client. So an `untrusted_app` connecting to `127.0.0.1` **or to any local IP incl.
  `192.168.5.1`** is ACCEPTed via `lo`; the br0 rules never apply to it. Live-proven on Y175: 6363 and
  the **root diagnosticsd 49156** (both `0.0.0.0`-bound, not in the br0 allowlist) are reachable by a
  local process yet filtered to an external SoftAP client.
- **No `uid-owner`/`gid-owner` egress gate.** The only `-m owner` rule in the entire applied baseline
  is a uid-1029 bandwidth exemption (`bw_mangle_POSTROUTING`, accounting, not access control).
  `OUTPUT` policy is `ACCEPT`; `fw_OUTPUT`/`oem_out` are empty. **⇒ any uid, including `untrusted_app`
  (group `inet`), can originate TCP/UDP onto vlan4/vlan5 toward ECU IPs** (e.g. `192.168.1.112`,
  `172.16.4.107`); replies return via the `RELATED,ESTABLISHED` INPUT rule.
- **SoftAP (`br0`) ingress allowlist** (Y181 ruleset text): tcp **53, 7000**, 5000, 5001, 6030,
  30515; udp 5020, 6000, 6003, 6011, 53; DHCP 67 — the extra tcp/udp are CarPlay/AA **projection**
  ports. **[C] RESOLVED live-Y175 2026-10-06 (during an ACTIVE wireless-CarPlay session):** from a Mac
  joined to the `benchd89` br0 SoftAP, **only `53` + `7000` are reachable** — the projection ports
  (5000/5001/6030/30515) and gm_ccpa's `7011` did **not** open even with CarPlay live (nmap-confirmed).
  Reason (from on-device `ss`): **wireless CarPlay runs on `wlan1` over IPv6 link-local** —
  `[fe80::…]:7011 ↔ phone [fe80::…]:…` — a **separate AP** from the IPv4 br0/benchd89 SoftAP, so the
  projection ports are never on br0 regardless of allowlist. Net: the **external br0 SoftAP surface on
  Y175 is just DNS (53) + 7000**, even under live load; the CarPlay/projection plane is on `wlan1`
  (IPv6-LL) reachable only by the paired phone, not a general SoftAP client. gm_ccpa's internal stack
  is loopback `9001/9002/9004/9112`.
- **VLAN INPUT** (default DROP) = tight per-flow allowlist keyed on **source ECU IP → radio's own VLAN
  IP + dport** (vlan5 `192.168.1.100` from `.102/.104/.106/.109/.112` + SOME/IP-SD multicast on
  9002/9010/9011/9016/9021/9022/9040/2942/9090/6060/12345/1234/1235, udp 3000/9026; vlan4
  `172.16.4.100` from `.112`→53/443/49156 and `.107`→49156).
- **FORWARD effectively DROP** (file `:FORWARD ACCEPT` but applied `tetherctrl_FORWARD -j DROP`; IPv6
  `FORWARD DROP`). **⇒ an external SoftAP client is NOT routed onto the automotive VLANs** — joining
  the hotspot does not bridge you to the vehicle network. Cross-segment isolation holds.

**Net for "can a 3P app reach the VLANs":** an on-device 3P app is gated by **SELinux + service
binds**, not the SoftAP firewall, and the host firewall imposes **no uid restriction on egress** — so
in-vehicle it can originate to ECU IPs on the VLANs (bench has no ECUs to answer). An *external*
SoftAP client cannot (FORWARD drop). See [`../hardware/connectors.md`] for the ADB/USB side.

### IPC / Serial

| Interface | Config | Permissions | Notes |
|-----------|--------|-------------|-------|
| `/dev/ttyS1` | 1 Mbps, HDLC v16 | `root:root` | 20 IPC channels to VIP MCU |
| `/dev/ttyACM1` | SXM serial (was labeled "Debug UART") | `crw-rw-rw-` | **World-writable** — any process can read/write |

> **[C] live-Y175 2026-10-05 (dev_listing.txt):**
> - `/dev/ttyS1` CONFIRMED owner `root:root`, SELinux `ipc_serial_device`, but mode is **`crw-------` (0600, root-only)** — NOT world-accessible; the IPC link to the VIP is DAC-closed. (1 Mbps/HDLC-v16/20-channel detail UNVERIFIABLE-FROM-LIVE.)
> - `/dev/ttyACM1` CONFIRMED `crw-rw-rw-` (0666, world-rw), owner root — but SELinux label is **`sxm_device`** (SiriusXM), not a debug UART. ADJUST: world-writable confirmed; "Debug UART" description REFUTED → it is the SXM tuner serial. No `/dev/ttyACM0` present.

### I2C Buses

| Bus | Permissions | Usage |
|-----|-------------|-------|
| i2c-0 | **World-writable** | General purpose (includes EEPROM at 0x50) |
| i2c-1 | **World-writable** | General purpose |
| i2c-2 | **World-writable** | System bus |
| i2c-3 | **World-writable** | Audioserver bus |

> **[C] live-Y175 2026-10-05: CONFIRMED** — i2c-0/1/2/3 all `crw-rw-rw-` (0666); owners root/root/system/audioserver; labels `saturnhd_device`/`i2c_device`/`i2c_device`/`dirana3_device` respectively. (See EEPROM section note for the full line.)

### GPIO (World-Writable — claim REFUTED on captured evidence, see note)

| GPIO | Function | Risk |
|------|----------|------|
| gpio458 | MCU control | MCU reset/boot mode manipulation |
| gpio460 | MCU control | MCU reset/boot mode manipulation |
| gpio464 | MCU control | MCU reset/boot mode manipulation |
| gpio466 | MCU control | MCU reset/boot mode manipulation |

These GPIOs control MCU reset and boot mode pins. World-writable access means any user-space process can force the VIP MCU into reset or bootloader mode.

> **[C] live-Y175 2026-10-05: "World-Writable" REFUTED on captured evidence.** The GPIO char devices `/dev/gpiochip0-3` are **`crw-------` root (0600)** — root-only, not world-writable. `gpio458/459/460/463/464/466` exist only as entries under `/sys/class/gpio/` and appear as **symlinks** (`lrwxrwxrwx` → `…/INT3452:00/gpiochip0/gpio/gpioNNN`); symlink mode bits are always 0777 and carry no access meaning, and the underlying `value`/`direction` node permissions were **not captured** (`export`/`unexport` read back as `?`). Independently, `world_writable.txt` enumerates exactly **two** world-writable nodes — both stock memcg `cgroup.event_control` — and **no** gpio path. **The missing datum was then captured directly (2026-10-05):** `ls /sys/class/gpio/gpio{458,460,464,466}/` returns **`Permission denied` to shell (uid 2000)**, and `export`/`unexport` read back as `?` (root-only) — the value/direction nodes are not even stat-able by a non-root process, let alone writable. Claim **REFUTED**: a non-root process cannot toggle these pins. Second-agent concurrence obtained 2026-10-05 (14-flip ledger).

### CAN / UDS Diagnostic Services

| Service ID | Function |
|------------|----------|
| `$10` | Diagnostic Session Control |
| `$22` | Read Data By Identifier |
| `$27` | Security Access (seed-key) |
| `$2E` | Write Data By Identifier |
| `$31` | Routine Control |
| `$34` | Request Download |
| `$36` | Transfer Data |
| `$37` | Request Transfer Exit |

> **[C] live-Y175 2026-10-05: UNVERIFIABLE-FROM-LIVE** — the UDS service IDs, seed/key, and CAN addresses are off-SoC (CAN/DoIP) and were not (and must not be) probed in this DISK-ONLY shell capture. Only the Ethernet transport endpoint is observable: `diagnosticsd` listener on `0.0.0.0:49156` (root) is live (see Network Services). `gm.obd.IOBDService` (`OBDService`) and `gm.diagnostics_service.IDiagnosticsService` binders are registered (services.txt #63/#60).

- **CSM (Center Stack Module — the radio/head unit itself):** CAN address `0x80`
- **CGM (Central Gateway Module):** CAN address `0x45` — per GM's GIS-763 caldef, `0x45` **is** the Diagnostic Address of the CGM (Central Gateway Module). The only open question is the narrower one of whether this CAN node is the *same physical module* as the Ethernet-side telematics gateway (`.107`/`.112`); see `platform/vehicle_network.md`.

> These UDS services are reachable two ways: over **CAN/DPS** (see
> [`diagnostics/dps/`](../diagnostics/dps/)) and over **Ethernet/TCP** via the
> root `diagnosticsd` daemon on port 49156 (GM Ethernet diag address `0x0084`,
> 8-byte header). The Ethernet path's wire format, tester-ID/SecurityAccess
> trust tiers, and a confirmed (unprivileged) generalReject probe are documented
> in [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md).
> Related shell-side surface (Binder UpdateService, kernel KASLR, GM Secure ADB
> `adbd` auth) is in
> [`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md),
> and the OTA/signing gate in [`platform/ota_update_stack.md`](ota_update_stack.md).

---

## Local Hardware Attack Surface (all builds)

> **CORRECTED 2026-08-26.** This section was formerly "Y177 Attack Vectors (SELinux Permissive)"
> and premised on Y177 running permissive. That premise is FALSE — Y175/Y177/Y181 all run SELinux
> **enforcing**. The DAC-level exposures below (world-writable I2C/GPIO/debug-UART nodes) exist on
> **all** builds regardless of SELinux mode; SELinux enforcing constrains which *domains* may reach
> them, but does not change the file-mode permissions themselves.

### Direct Hardware Access

- **I2C EEPROM manipulation:** A process in an allowed domain can read/write EEPROM security flags (`0x0440`, `0x0A80`) via `i2cset`/`i2cget` on the world-writable buses. SELinux enforcing (all builds) gates this by domain; the DAC world-writable bit does not.
- **GPIO MCU control:** earlier claimed as world-writable GPIOs (458/460/464/466) toggleable to force the VIP MCU into reset/bootloader. **[C] live-Y175 2026-10-05: REFUTED (concurred).** `/dev/gpiochip0-3` are `crw-------` root, and `/sys/class/gpio/gpio{458,460,464,466}/` return `Permission denied` to shell uid 2000 (value/direction nodes not stat-able by non-root; export/unexport root-only); `world_writable.txt` lists no gpio. Not a non-root DAC exposure. See the GPIO table note above.
- **Debug serial access:** `/dev/ttyACM1` with `crw-rw-rw-` permissions is world-writable at the DAC layer; SELinux enforcing restricts which domains may open it. **[C] live-Y175 2026-10-05:** `crw-rw-rw-` CONFIRMED, but the node is the **SXM serial** (`sxm_device`), not a debug UART — see IPC/Serial note.

### Kernel Exploitation

- **Kernel CVEs (CVE-2024-53104, -36971, -53150, -53197):** unpatched-kernel exposure tracks the build's kernel version / patch level, not SELinux mode. SELinux is enforcing on all builds, so MAC containment (neverallow rules) applies equally to Y177 and Y181.
- **BPF verifier bypass (CVE-2023-2163):** CAP_BPF plus SELinux enforcing domain restrictions apply on all builds.
- **ptrace:** `CONFIG_SECURITY_YAMA` is not set, so ptrace scope is unrestricted at the YAMA layer on all builds; SELinux domain rules still apply.

### Persistence

- **EEPROM SBI flag modification:** Writing `0xFF` to `0x0441` (and empirically `0x0A81`) persists the ADB/seed bypass across reboots since the SBI region is not CRC-enforced. A bulk restore-to-ROM-defaults on the VIP re-locks it; the bypass is re-applicable with I2C access.
- **Debug mode activation:** Write `0x01` to `0x0B41` to enable debug mode persistently.

---

## SELinux Denial Analysis (Y181)

> **[C] live-Y175 2026-10-05: Y181-SCOPE-ONLY** — the "462 denials, CBC/RVC/SXM" figures are Y181 logcat. Live **Y175** shows a different picture in this capture: **179** `avc: denied` lines (all `permissive=0`), dominated by `system_suspend→sysfs:dir read` (43), `system_server→shell:unix_stream_socket getopt` (13), `system_server→fs_bpf_tethering:dir search` (12), and benign `proc:file getattr` on `/proc/sys/dev/i915/perf_stream_paranoid`. The security-relevant ones are the `untrusted_app→gm_domain_service:service_manager find` denial (the GMWlanService gate) and `shell→oem_unlock_prop:file read` / `shell→gm_carplay:binder call` from our own probe. No CBC/RVC/SXM cluster and no USB/CarPlay denials observed here either (but this is a point-in-time shell capture, not a boot-to-now logcat).

The 462 SELinux denials observed in Y181 logcat are concentrated in three subsystems:

- **CBC** (Camera/Backup Camera) — access to hardware resources
- **RVC** (Rear View Camera) — video pipeline permissions
- **SXM** (SiriusXM satellite radio) — service communication

Notably, **no USB or CarPlay-related denials** were observed, indicating that the USB host stack and CINEMO/NME CarPlay framework operate within their assigned SELinux domains without policy violations.
