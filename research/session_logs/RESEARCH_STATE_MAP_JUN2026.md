# GM Info Research State Map — June 2026

**Document date:** 2026-06-29
**Prepared by:** Research session audit (Dec 2024 – Jun 2026)
**Platform:** GM Info 3.7 (gminfo37)

---

## Platform Summary

| Field | Value |
|---|---|
| SoC | Intel Atom x7-A3960 (Apollo Lake) |
| OS (Android) | Android 12 AAOS — W231E-Y181.3.2-SIHM22B-499.3 |
| Hypervisor | GHS INTEGRITY IoT 2020.18.19 |
| Linux kernel | 4.19.305 |
| VIP MCU | Renesas RH850/TM52176 |
| Current access | uid=2000 ADB shell (EEPROM SBI bypass applied) |
| Physical access | Full board access including RH850 |

**Research goal:** Downgrade Android build Y181 to Y177 to restore permissive SELinux environment and stubbed VIP security function at 0xb67d0.

**Primary blocker:** GHS AB0 rollback counter in misc/vda9. Counter is CRC32-only, and is written exclusively by the GHS hypervisor. Cannot be decremented from Android shell.

---

## Research Timeline

### Dec 2024
Y181 to Y177 downgrade attempted via USB/DPS. **FIELD-TESTED AND BLOCKED.** GHS rejected with `"rollback index is too old."` A/B fallback returned to Y181. Y177 via USB is a confirmed dead end.

### Dec 20 2025
Y181 first full enumeration (W231E-Y181.3.2-SIHM22B-499.3, build 231, kernel 4.19.305, bootloader 2344, slot _a). Bulk of security assessment produced (security_assessment_20DEC25.txt v2.4). Two fastboot attempts made this session: both returned "No fastboot device detected" — Intel ABL has no standard fastboot USB interface. **CRITICAL MISTAKE documented:** the user had previously updated from Y177 to Y181 voluntarily, losing the permissive SELinux environment.

### Jan 17 2026
Y175 baseline enumeration (W213E-Y175.5.2-SIHM22B-383.1, kernel 4.19.283, bootloader 2121-1, SELinux already Enforcing on this build). /dev/ttyACM1 had a live timestamp — accessed this session. Y175 VIP UART log captured (VIP version 2B.175.1.5).

### Apr 7 2026
Y181 second session. Boot slot found flipped to _b — unexplained, possibly a rolled-back OTA attempt. GHS attack surface analysis added. AVB digest captured: `537b0f4b5248b66ae9a6fb4f20ef7ff968d5720a925aaecf2545770dd9fbc45c`. /dev/ttyGS0 (USB gadget serial) appeared this session. Vehicle engine was running during capture.

### Jun 21 2026
Verification and reconciliation pass. Live ADB (serial CJUD4R4f1b5fd0), boot slot back to _a. Corrected repository errors: SW video decoders are present (not absent as previously noted), guest IP is 192.168.1.100 (not .1), port 9010 is a listener (not just outbound), port 7000 active during CarPlay session. No new offensive progress.

---

## What Was Tried

### Working

- **EEPROM SBI bypass:** Bytes 0x0441→0xFF, 0x0A81→0xFF, 0x1A01→0xFF, 0x0B41→0x01. Raw markers at 0x0440→`5A FF 5A`, 0x0A80→`5A FF 5A`. Yields ADB shell uid=2000, NOT root. OTA resets flags; must be re-applied after any update.
- **EEPROM CRC corruption test:** VIN bytes 0x05C0–0x5D1 wiped to all-0xFF; module booted normally. **CRC NOT enforced at boot** confirmed.
- **Y181→Y181 reinstall:** Succeeds.
- **DPS 4.56 diagnostic sessions:** UDS $27 SecurityAccess, $22 ReadDataByIdentifier (many DIDs), $31 RoutineControl on ECU 0x80.
- **FSA RemoteModuleHMI:** rmIdentification fn706 + clientFocus fn712 from shell — both returned success ("registered as HMI module").
- **UDS probe on port 49156 (diagnosticsd):** TCP handshake completes; all SIDs return NRC 0x10 generalReject.
- **pm disable --user 0 of critical packages:** Triggered return-to-dealer screen (recovered via datawipe USB).
- **KASLR estimation via simpleperf:** Slide ~0x0D000000.
- **vmlinux-to-elf:** 117,828 symbols recovered from 4.19.305 kernel.
- **9-pass Ghidra on VIP firmware:** Confirmed zero crypto in VIP (pure relay).
- **Binder service enumeration:** UpdateService (30 methods, OPEN), GALService (OPEN), RDMSADBHandler (OPEN), DiagnosticsService (partial).
- **Static RE of CAN bus reset DLL:** 10017908.dll / 10017909.cfx analyzed.

### Tried and Blocked

| Attack | Block Reason |
|---|---|
| Y181→Y177 downgrade via USB/DPS | GHS independent rollback counter in misc/vda9 blocks at boot. Field-tested Dec 2024. DEAD. |
| misc (vda9) read/write from shell | SELinux neverallow (domain.te:632) |
| /dev/ghs/* and /dev/trusty-ipc-dev0 | DAC is rw-rw-rw- but SELinux blocks from shell domain |
| /dev/i2c-0 and /dev/i2c-1 | World-accessible DAC; SELinux blocks read |
| /dev/ttyACM1 write | SELinux blocked despite crw-rw-rw-; passive read returned no data in 2s |
| 192.168.1.1:9002/9005/9010/9016 via nc | "No route to host" |
| AllowDevSignedVIP / changeDebugMode | isDebugBuild()=false |
| gm_protokey extraction | Permission denied from uid=2000 |
| RDMSADBHandler ADB_Disable USB role-reversal | Blocked by GM V10 E2 PD hub |
| GSI/DSU boot | Silently denied via dontaudit gm_update_engine gsi_metadata_file (vendor_sepolicy.cil:2672) |
| Fastboot | Never connected; Intel ABL has no standard fastboot USB interface |
| avb_audit.py against /elk_inner.elf | Ghidra failed — "Ghidra was not started with PyGhidra." Zero AVB findings. |

---

## Key Technical Discoveries

### GHS Binary

- **SOC_HOSTOS** (file 85098662, 14,929,956 bytes) is **byte-for-byte identical between Y177 and Y181.** The rollback counter in misc/vda9 is the sole discriminator between builds. Same hypervisor image; different counter value.
- **misc partition (vda9) layout:**
  - Offset 0x000: BCB (`command[32]` / `status[32]` / `recovery[768]` / `stage[32]`)
  - Offset 0x800: A/B metadata (magic `"AB0"`, version, `slot_info[2]{priority, tries_remaining, successful_boot, verity_corrupted}`, crc32)
  - CRC32 polynomial 0xEDB88320. **CRC32-only, no signature.**
- **CRITICAL:** The string `"VMM: Warning: A/B metatdata CRC failure!"` (note the typo: "metatdata") appears in ghs_str.txt at line 43973. This is a WARNING string, not a hard-stop abort. CRC failure may produce a warning and allow boot to continue rather than bricking. **Untested.**
- **ELK trigger functions in GHS binary:** BootELKSendAblUserCommand (0x0087452a), BootELKWaitForRespSent, ConnToOTA_BootELK, ConnToLifecycle_BootELK. ELK bypasses misc/BCB entirely — goes HECI→CSE→ABL with target OBBPELK.
- VIP J6_CDD has `"Diag Elk Reboot Req"` string but exact SID/DID is unknown.
- **Build path:** `/home/mal/gm_release/MY22-026/final/iot/cust-build_sb/gm-i35/rel/gm_i35_my22_gb/gm-i35-kernel`
- **Android signing key** (.mr_r_mod_android_key, 0x02201000–0x02201fff, 4KB NOBITS): NOT present in the file; delivered at runtime from Intel CSE via multiboot.
- **Keymaster log string:** `"VMM reported green boot state but device is not locked. Treating as unverified boot"` (offset 0x00eecdd8).
- **RSA-1024 private key** found in ghs_integrity.elf at byte offset 12924442 (609 bytes, sha1=78d9a50f). This is the only private key in the entire corpus. Function is unknown — candidates include attestation, IPC authentication, or signing.

### VIP Security Function 0xb67d0

**Y177 stub (4 bytes):**
```asm
mov 0, r10    ; always return success
jmp [lp]      ; return to caller
```

**Y181 full implementation (906 bytes):** Loads EEPROM→RAM mapping (0x0440→RAM 0x3e06), compares against expected value 1, calls validation subroutines at 0xecd84, 0xb6652, 0xaee28. On mismatch, returns error → VIP sends "normal mode" → SELinux stays enforcing.

Y177's permissive SELinux is not a boot cmdline artifact. It derives from VIP returning bypass state via `SERIAL_IPC_PROTO_KEY_CHANNEL`, which only occurs when the security function at 0xb67d0 is the stub. The EEPROM bypass achieves ADB access but does not replicate this VIP signaling path.

### Confirmed Open Ports

| Address | Service | Notes |
|---|---|---|
| 0.0.0.0:49156 | diagnosticsd (PID 599, UID=0) | ALL caps 0x3fffffffff, no seccomp, NoNewPrivs=0. Stack buffer 128KB; potential malloc-before-size-check in readHeader(). No OS-level peer credential check. |
| 0.0.0.0:7000 | Unknown | Present during active CarPlay/projection session only |
| 0.0.0.0:6363 | NFD/GMVT (Named Data Networking) | — |
| 192.168.1.100:9002 | RemoteModuleHMI (FSA) | No auth; shell-accessible |
| 192.168.1.100:9010 | GHS bridge listener | Confirmed listener in Jun 2026 |
| 192.168.1.100:9016 | FSANetCommsService | — |
| 192.168.1.100:9012 | Unknown | Persistent SYN_SENT; unexplained |

### Complete Partition Map

vda = virtio-blk (GHS guest view):

| Partition | Label |
|---|---|
| vda1 | ghs_isys_a |
| vda2 | ghs_isys_b |
| vda3 | ghs_storage |
| vda4 | ghs_abl_update |
| vda5 | bootloader_a |
| vda6 | bootloader_b |
| vda7 | boot_a |
| vda8 | boot_b |
| **vda9** | **misc** (rollback counter lives here) |
| vda10 | vbmeta_a |
| vda11 | vbmeta_b |
| vda12 | metadata |
| vda13 | super |
| vda14–17 | acpi/acpio A/B |
| vda18–19 | cert A/B |
| vda20 | persistent |
| vda21 | teedata |
| vda22 | config |
| vda23 | calibration |
| vda24 | ghs_log |
| vda25 | update_cache |
| vda26 | data |

GHS partitions not mounted in Android: ghs_isys_a/b, ghs_storage, ghs_abl_update, ghs_log, teedata, cert_a/b.

### Five Bypass Paths (INVENTORY.md)

| # | Path | Status |
|---|---|---|
| 1 | EEPROM 0x441=0xFF → ADB enable | **DONE** |
| 2 | /proc/cmdline `androidboot.bootreason=warm` → gm_protokey skips validation | NOT YET EXPLOITED |
| 3 | Delete /data/vendor/gm/security/.validation → TOFU re-provisioning with any PAL key | NOT YET TRIED |
| 4 | gm_protokey_recovery_prop → GM ProtoKey recovery override | Purpose TBD |
| 5 | /data/gmprotokey/trigger/ → recovery re-key oracle (shell-writable) | NOT YET TRIED |

### Kernel Configuration Highlights

- `CONFIG_TITAN_X86_BROXTON_PROGRAM=y`, `CONFIG_APL_MY22_ANDROID=y` (Apollo Lake, Model Year 2022)
- Security hardening enabled: KASLR, STACKPROTECTOR_STRONG, RETPOLINE, MODULE_SIG_FORCE
- Debug-friendly: KALLSYMS_ALL=y, IKCONFIG_PROC=y (`/proc/config.gz` accessible)
- CAN fully enabled: CAN_RAW, CAN_BCM, CAN_GW, CAN_SLCAN, CAN_8DEV_USB
- **IOMMU disabled** (`intel_iommu=off`) — DMA attacks are not hardware-blocked
- USER_NS not set, KEXEC not set, EFI not set

### Trusty Anomaly

`/tos` and `/multiboot` are commented out in fstab with the note "Commented out tos and multiboot for disabling trusty," yet `[kworker/0:1-trusty-timer-wq]` is running. Trusty appears to be loaded via an ACPI/SSDT path rather than the normal fstab mount. teedata (vda21) is present but not mounted from Android.

---

## Dead Ends — Confirmed Infeasible

| Vector | Reason |
|---|---|
| Y177 downgrade via USB/DPS | GHS rollback counter blocks. Field-tested. DEAD. |
| SOC_ABL modification | Intel CSE hardware root of trust, OTP-fused keys, SVN anti-rollback. Effectively impossible. |
| Boot Guard v2 / IFWI / custom OS | OTP antifuses burned at factory. |
| AES-CMAC master key extraction | Inside TXE Sealed Storage; hardware-fuse-derived. |
| GSI/DSU boot | dontaudit policy block; permanent. |
| ISSI SPI flash as AVB bypass | current_android_key hardcoded at GHS offset 0xe3ca34; BG-locked. |
| vmm1 GHS decompilation | 140 functions decompiled but unusable — Green Hills toolchain, no string cross-references. |
| Kernel CVE exploitation on Y181 | SELinux enforcing blocks all candidates reviewed. |
| DPS direct EEPROM write | No UDS service maps to EEPROM security addresses. |
| WiFi ADB | Compiled out. |
| GM Secure ADB | Absent on production builds. |

---

## Where Research Stopped

**Last offensive action:** VIP security function diff (0xb67d0) and GHS misc/AB0 rollback structure decode. The Jun 2026 session was verification and reconciliation only. No new attack surface has been opened since Dec 2025.

**Highest-priority next action** (teardown.md Option 3, "HIGHEST PRIORITY"): Re-trigger the return-to-dealer screen and check ADB UID, SELinux state, and misc partition accessibility during that mode. This was **never checked** during the prior incident when the screen was first encountered.

---

## ghs_probe.c — Written, Never Deployed

The GHS hypervisor probe tool (research/tools/ghs_probe/) is a complete, compilable Android JNI shared library. It probes 12 /dev/ghs/* nodes, brute-forces GHS ioctls `_IOR('g', 0x00–0x20, int)`, and tries 10 Trusty service names via `TIPC_IOC_CONNECT`. ioctl magic values ('g', 0x01–0x02) are admitted guesses, noted as such in-source.

The tool was **never compiled or deployed** — no output files exist. CMakeLists.txt is complete; requires an Android NDK build targeting arm64-v8a and x86_64.

---

*Document generated 2026-06-29. Covers all sessions Dec 2024 – Jun 2026.*
