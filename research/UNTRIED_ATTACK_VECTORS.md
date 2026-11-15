# Untried Attack Vectors — GM Info 3.7 (gminfo37) Y181→Y177 Downgrade

**Initial research:** 2026-06-29
**Control/import research updated:** 2026-11-15
**Project:** gminfo37 — downgrade GM Info 3.7 head unit from Y181 to Y177
**Current access:** uid=2000 ADB shell, physical board access, Renesas RH850 VIP MCU

---

## Overview

As of 2026-06-29, several high-value attack vectors identified in the research have never been attempted. This document tracks untried paths ranked by probability of advancing the Y177 downgrade goal.

The original goal was a Y181→Y177 software downgrade to obtain a permissive SELinux posture.
**CORRECTED 2026-09-26 (full primary-evidence extraction of the Y177 system image, `86283152`):** the
premise is **refuted** — stock **Y177 boots SELinux `Enforcing`**, not permissive. Verified against the
actual Y177 files, not documentation:
- **Boot cmdline** (signed boot image `86283154`): the early `enforcing=0 androidboot.selinux=permissive`
  is overridden by the extra_cmdline's final tokens **`enforcing=1 androidboot.selinux=enforcing buildvariant=user`** (last token wins).
- **`/system/build.prop`**: `ro.build.type=user`, `ro.secure=1`, `ro.debuggable=0`, release-keys →
  AOSP init forces enforcing on user builds and ignores `androidboot.selinux=permissive`.
- **Compiled policy**: all four CIL sources (plat/vendor/plat_pub_versioned/product) have **0 permissive
  domains**; the monolithic `sepolicy` is byte-identical to vendor `precompiled_sepolicy` (sha `027861ca…`).
- **Y177 `plat_sepolicy.cil` is byte-identical to Y181's** (0 diff) → there was **no "unintended
  permissive policy change" for GM to correct** between Y177 and Y181; both are the same enforcing policy.
- **No permissive lever exists**: `init` uses stock `security_setenforce`/`getenforce` with no VIP/MEC/gmauth
  hook, and across all 2093 system+vendor binaries the only `setenforce 0` caller is a manual Intel
  gfx-debug script behind an opt-in `--selinux_disable` flag (not boot- or VIP-gated).
- Adjacent real-device captures: Y175 (user build) and Y181 both `getenforce=Enforcing`.

**On the VIP-analogy (why ADB is influenceable but SELinux is not):** the ADB bypass works because GM
built a deliberate userspace lever — `gmauthmanagerservice` reads the VIP's MEC/`is_secure_mode` and
relaxes adb-auth. SELinux enforcement has **no analogous GM hook**: neither adbd nor gmauth is a
`setenforce` caller, and `is_secure_mode` does not touch SELinux. So the old "VIP forces permissive"
theory does not transfer. **Residual gap:** no Y177 *runtime* `getenforce` capture exists; static
evidence is conclusive, but an emulator/live-unit readout would close it 100%.
So **a Y177 downgrade would not yield a permissive posture**, and this doc's permissive-via-downgrade
rationale no longer holds. (The 2026-08-25 sub-finding stands: the VIP function at 0xb67d0 is a
~906-byte `$27`/seed validator in Y175/Y177/Y181 alike with no SELinux logic — and per the 2026-09-26
SBI verification it is **not** the ADB gate either; see item-3 note in `PROJECT_MASTER_CHECKLIST.txt`.)

Vectors are ranked by: (1) likelihood of breaking the current blocker, (2) estimated effort, (3) available access level.

---

## Current UDS and T1 priorities (2026-11-15)

**Useful controls remain partially tested.** The exhaustive prior experiment covered
65,536 SID22 DID numbers in one security/session profile, not every write,
I/O-control or routine payload. It produced 135 positive DIDs; 136 is the
later union after a state-changing audio routine exposed another read.
The 5,120-request ADB experiment enumerated variants of one reported RID0332
layout. It was not an all-services control sweep. The
[coverage audit](../diagnostics/diagnosticsd_routines_and_recovery.md#diagnostic-control-coverage-audit-2026-11-15)
owns the exact tested/discovered distinction. The subsequent authorized live
pass exercised 24 of 25 IOCID IDs with bounded operations. Subsequent actual
FM/AM switching and frequency round-trips worked. USB discovery/parser tests
established an eight-character native basename requirement, without
demonstrated single-brand override application. Calibration clearing remains
forbidden; no package installation or reboot was performed.

| Priority | Concrete lead | Work needed before a live claim |
|---|---|---|
| 1 | Working display/audio/input IOCIDs | Extend the now-verified bounded controls to useful selector/state coverage; do not infer untested speaker routing or VIP reset from Android input. |
| 2 | Partially tested source/AF/surround/DAB controls | FM/AM switching and tuning now verified with rollback. USB/media requests lacked a verified playback transition; AF stayeddisabled even with FM active; surround/DAB NRC22. Tone wire mapping remains inconclusive because same-run known-signal controls were also silent. |
| 3 | ABFT routine0475 | Install-plan JSON schema now recovered. Missing-field-only starts returned NRC31 at level05/NRC33 at level09; results NRC22. Review module writers, signatures and A/B selection before any complete plan; Stop invokes cancelUpdate(true), not a read-only query. |
| 4 | Native IECUUpdate.copyFile | Current shell lookup is denied by SELinux find on gm_update_engine_hwservice. Recover an authorized client/proxy path; the copier was not invoked. |
| 5 | Type2 package registration/restoration | Determine a supported caller path to the existing privileged installer on production builds. |
| 6 | FSA RemoteModuleHMI and coordination schemas | NAM requests now reach Wi-Fi/cellular trackers and return DOWN; peer emulation on9005/9012/9018 remains blocked by host T1 reachability, not protocol exhaustion. |

The [current IOCID inventory](../diagnostics/diagnosticsd_protocol.md#implemented-iocid-inventory-and-candidate-controls-2026-11-15)
contains 25 IDs, including key events, tones, equalizers, audio-source and
frequency controls. 41D8 is an input-control candidate rather than a root
shell; 41DB additionally selects SWC mute and other keys, with a fixed 300 ms
tap rather than a hold. 43FC injects the named GM tune-encoder key245.
FACEPLATE reaches a vendor panel interface whose downstream path remains open;
the traced SWC VHAL path emits Android-facing events with no VIP/CAN transmit.
The [live control table](../diagnostics/diagnosticsd_protocol.md#live-bench-controls-2026-11-15)
records actual display changes, restored audio readbacks and SWC volume
events; zero/nonzero encoder requests prove event routing but have not
demonstrated a controlled frequency step.
Return/reset/freeze semantics vary by handler,
and routine-results is not universally read-only: 0249 can clear data.

**The update mechanism does contain a protected file-placement step.**
Current Y175 DevCaloverrideInstaller copies registered calibration files and
reboots to recovery. Its USB discovery branch is gated to non-user builds;
normal install IPC is not a demonstrated arbitrary XML importer. MediaStore
did permit a byte-exact 308-byte XML write at the connected FAT32 USB root;
native selection requires an eight-character basename. A short-name manifest
marker reached staging and the parser; the valid XML now uses
`a11brand.calovride`. No calibration-discovery/install event or application
was demonstrated, including with a temporary auto-install marker. See the
[updater reference](../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15).
An original [2023 command gist](https://gist.github.com/NativeDevlopment/fb3683c94858ef2aee580aa1ac93e1a0)
uses calibration overrides but assumes root/remount and identifies no working
production A11 build. It supports terminology, not the missing privilege path.

**No independently reproduced GM A11 UID0 shell emerged from the bounded
community search.** A Harman GWM OEM root-property report is cross-platform:
the inspected GM adbd binaries lack its hooks, and current GM root-service
code checks Android debug capability before GM secure mode. The
[root/access assessment](security/SHELL_ACCESS_ESCALATION_Jun2026.md#community-root-reports-and-target-applicability-2026-11-15)
owns original forum links, the retrieval caveat and binary fingerprints.
The [Global B ADB article](https://surrealdev.com/the-abcs-of-global-b/) and
[GWM boot-target implementation](https://github.com/DymOK93/GWM-CAN-Tools/blob/master/uds.py#L351)
are useful leads, not demonstrated alternate root access on this unit.
The project's own repository is not independent corroboration.

The older downgrade-oriented rankings below retain their historical context.
Their presence is not a recommendation to brute-force writes, clear overrides,
induce repeated boot failures or try generic root recipes. Current priority
is tracing a known implementation and its real caller/state boundary.

## Critical Priority (Direct Impact on Downgrade Goal)

---

### 1. Return-to-Dealer Screen ADB/USB State

**Status:** NOT TRIED
**Priority rationale:** teardown.md marks this HIGHEST PRIORITY, Option 3.

**How to trigger:**
```bash
adb shell am broadcast -a android.intent.action.PACKAGE_NEEDS_VERIFICATION
# or replicate the prior pm disable trigger that produced the screen
adb shell pm disable --user 0 <critical-package>
```

**What to check once screen is active:**
- ADB UID during dealer mode — is it still uid=2000 or elevated to uid=0 or a privileged domain?
- SELinux enforcement state: `adb shell getenforce` — is it still Enforcing, or does dealer mode drop to Permissive?
- misc (vda9) partition read/write accessibility from this state
- `/dev/ghs/*` node accessibility and permission changes

**Why critical:** A different SELinux domain or reduced enforcement during dealer/recovery mode could directly expose misc partition writes, which is the primary technical blocker for the downgrade. The dealer screen is likely served from a separate init trigger that may run under a less-restricted SELinux context.

**Prior incident:** A `pm disable` command inadvertently triggered the Return-to-Dealer screen once. ADB connection was not used to probe system state during that window. This represents a missed opportunity that must be reproduced deliberately.

---

### 2. "A/B metatdata CRC failure!" is a WARNING not an Abort

**Status:** NOT TESTED
**Priority rationale:** If the CRC check is non-fatal, the primary cryptographic protection on the misc/AB0 rollback counter is bypassable without correct recalculation.

**Finding:** `ghs_str.txt` line 43973 contains the string:
```
VMM: Warning: A/B metatdata CRC failure!
```
Note the typo "metatdata" — this is verbatim from the binary. The word "Warning" (not "Error" or "Fatal") strongly implies the GHS VMM logs the CRC failure and continues, rather than halting the boot sequence.

**Test procedure:**
1. Obtain offline write access to misc/vda9 (via eMMC BGA-153 dump, or a writable path found via vector #1 above)
2. Modify the rollback counter field in the AB0 metadata to the Y177 target value
3. Write back with an intentionally incorrect CRC32
4. Boot and observe: does GHS warn-and-continue (confirming the bypass), or does it hard-stop?

**Prerequisite:** Offline eMMC modification (BGA-153 ISP dump, vector #16) OR a shell-writable path to vda9 discovered via dealer screen state (vector #1).

**Risk assessment:** If the warning is truly non-fatal, this eliminates the need to reverse-engineer the exact CRC32 algorithm and seed used in the AB0 metadata structure. This would reduce the misc bypass from a crypto problem to a field-offset problem.

---

### 3. RH850 JTAG — Direct VIP Firmware Extraction and Patch

**Status:** NOT TRIED
**Priority rationale:** Single highest-leverage hardware vector. If OCD fuse is unblown, this sidesteps the entire GHS rollback counter approach.

**Hardware required:**
- Renesas E10A-USB debugger (~$150 new, ~$40–80 used/clone)
- Renesas CS+ IDE (free download from Renesas website)
- Fine-pitch probe or soldered wires to QFP-176 JTAG pins (TCK, TMS, TDI, TDO, TRST)

**What JTAG access provides:**
- Full VIP firmware dump — no indirect Ghidra analysis from partial binary extraction
- Live breakpoints on security function at **0xb67d0** — observe exact inputs and branch logic
- ~~Ability to **patch 0xb67d0 in-place** with a 4-byte stub (equivalent to the Y177 behavior)~~ — **VOID (2026-08-25):** Y177 has no stub; the function is full in every build, so there is no "Y177 behavior" to reproduce and no VIP path to SELinux (see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2)
- Direct view of the J6_CDD channel message handler and the exact OBBPELK trigger format
- EEPROM 0x0A00 structure read behavior observable in-debugger under real execution conditions

**Why ~~game-changing~~ downgraded (2026-08-25):** the "patch 0xb67d0 → permissive SELinux" premise is refuted — no stub exists in any build and the VIP does not decide SELinux mode. RH850 JTAG (if the OCD fuse is unblown) is still useful for *observing* the ADB/seed validator's inputs and the J6_CDD/OBBPELK format, but it does not yield permissive SELinux and does not make the downgrade optional.

**OCD fuse status:** Unknown. Production RH850 units are frequently shipped without OCD fuse blown — the fuse is typically blown only in high-security applications. Probability of access: estimated moderate-to-high.

**Next action:** Acquire E10A-USB debugger. Identify TCK/TMS/TDI/TDO/TRST on the QFP-176 pinout against the RH850/F1K datasheet (marking TM52176; confirmed: /Volumes/stuff/misc/research/GM_research/csm_eeprom/RH850_Vol_Glitch_Tools.txt).

---

### 4. ELK Trigger via J6_CDD — Compiled Selector 8180; CAN Validation Pending

**Updated 2026-11-15:** the former "exact selector unknown / not tried" state
is superseded. Y175 VIP_APP has a descriptor/callback for selector `0x8180`
and a compiled branch that logs the ELK request and sends byte `E0` through
IPC API selector `0x0C`. The complete CAN request and outer authorization
checks remain unverified. Runtime/file offsets must use the corrected module
payload mapping; see the [owning ELK analysis](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15).

The GWM `FDF0` writes and candidate GM `2F 81 80 03` were **attempted through
Android diagnosticsd**, with level-1 SecurityAccess. All returned NRC 31;
Android logged missing DID/IOCID handler classes and did not reboot. This is
not a CAN-side rejection. See the [exact live test results](../diagnostics/diagnosticsd_routines_and_recovery.md#gwm-boot-target-and-gm-8180-follow-up-2026-11-15).

**Next:** validate the selector through the direct CAN adapter when delivered,
trace the descriptor/session/security/mode gates, and observe the control
response and actual boot environment. No broad DID-write sweep is required.
A successful request must not be presumed to bypass signatures, rollback,
bootloader lock state or ELK provisioning gates. The previous modified-image
loading claim was speculative; compiled ELK reachability alone does not
establish it.

---

### 5. Build and Deploy ghs_probe.c

**Status:** WRITTEN, NEVER BUILT
**Location:**
- `research/tools/ghs_probe/ghs_probe.c`
- `research/tools/ghs_probe/CMakeLists.txt`
- `research/tools/ghs_probe/AndroidManifest.xml`

**Build procedure:**
```bash
# Requires Android NDK r25+
cd research/tools/ghs_probe
mkdir build && cd build
cmake .. \
  -DANDROID_ABI=x86_64 \
  -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_PLATFORM=android-29
make
adb push ghs_probe /data/local/tmp/
adb shell chmod +x /data/local/tmp/ghs_probe
adb shell /data/local/tmp/ghs_probe
```

**What it probes:**
- 12 `/dev/ghs/*` nodes: `cal`, `camera`, `chime`, `ipc`, `ota-isys`, `tee-att`, `audit`, `capture`, `emmc-health`, `textlog`, `snapshot-dbg`
- `/dev/trusty-ipc-dev0` — 10 Trusty IPC service ports
- Brute-force ioctls `_IOR('g', 0x00–0x20, int)` on each accessible GHS node

**Caveat:** ioctl magic values are informed guesses based on GHS LIP driver naming conventions. Real values require RE of the GHS LIP kernel module (`ghs_lip.ko` or equivalent). Results from the probe will inform whether further RE of the kernel module is warranted.

**Deploy note:** May need packaging as APK with `android.hardware.type.automotive` permission if shell execution is blocked by SELinux on the binary path.

---

## High Priority

---

### 6. androidboot.bootreason=warm → gm_protokey Bypass

**Status:** NOT TRIED
**Finding source:** INVENTORY.md bypass #2

**Finding:** `/proc/cmdline` value `androidboot.bootreason=warm` causes `gm_protokey` to skip seed-to-key validation entirely.

**Current blocker:** `/proc/cmdline` is denied from uid=2000 shell context. However, the bootreason value is typically also exposed as an Android system property.

**How to probe:**
```bash
# Check if bootreason is readable as a property
adb shell getprop ro.boot.bootreason

# Check init.rc for bootreason conditionals
adb shell find /vendor/etc/init /system/etc/init -name "*.rc" 2>/dev/null

# Determine if gm_protokey reads /proc/cmdline or uses a property API
adb shell cat /proc/$(adb shell pidof gm_protokey)/maps 2>/dev/null | grep cmdline
```

**Potential impact:** If `gm_protokey` can be bypassed, the boot-time proto-key/disk-encryption (DATA_LOCKED)
gate it controls becomes accessible. **[C] Corrected (2026-09-27):** this does NOT unlock UDS `SecurityAccess
($27)` — `gm_protokey` is unrelated to the diagnosticsd UDS chain. `$27` for `ETHERNET`/`NOTIFICATION` tiers is
checked in-process by `diagnosticsd`'s own `libuds`; the `VIP` tier is forwarded off-SoC to the VIP MCU via
`ProxyOfExtComp`/`SockAdaptor`, gated by the SBI EEPROM byte there — see
`diagnostics/ethernet_uds_diagnosticsd.md`. Opening the `diagnosticsd` code path (vector #9) is a separate,
unrelated escalation, not something a `gm_protokey` bypass grants.

---

### 7. Delete /data/vendor/gm/security/.validation (TOFU Re-provisioning)

**Status:** NOT TRIED
**Finding source:** INVENTORY.md bypass #3

**Finding:** Deleting `/data/vendor/gm/security/.validation` triggers TOFU (Trust On First Use) re-provisioning, allowing injection of a researcher-controlled PAL key into the device trust chain.

**How to probe:**
```bash
adb shell ls -laZ /data/vendor/gm/security/
adb shell ls -laZ /data/vendor/gm/security/.validation 2>/dev/null
# If accessible:
adb shell rm /data/vendor/gm/security/.validation
# Then observe logcat for re-provisioning behavior on next boot
adb logcat | grep -i "protokey\|TOFU\|provision\|PAL"
```

**Potential impact:** A researcher-controlled PAL key in the trust chain could be leveraged to sign update
packages accepted by the GHS update path. **[C] Corrected (2026-09-27):** this would NOT unlock UDS
`SecurityAccess ($27)` — that gate is unrelated to `gm_protokey`/the PAL trust chain (see the correction on
vector #6, above, and `diagnostics/ethernet_uds_diagnosticsd.md`).

---

### 8. gm_protokey_recovery_prop + /data/gmprotokey/trigger/ Oracle

**Status:** NOT TRIED (purpose TBD)
**Finding source:** INVENTORY.md bypasses #4 and #5

**Finding:** `/data/gmprotokey/trigger/` is writable from the shell. Writing files to this directory may trigger behavioral changes in the `gm_protokey` process.

**Action:**
```bash
adb shell ls -laZ /data/gmprotokey/
adb shell ls -laZ /data/gmprotokey/trigger/
# Create a trigger file and observe
adb shell touch /data/gmprotokey/trigger/test_probe
adb logcat -s gm_protokey &
# Watch for property changes
adb shell while true; do getprop | grep protokey; sleep 1; done
```

**Goal:** Map what recovery re-keying behavior is triggered, and whether any trigger file name produces a state that bypasses normal validation.

---

### 9. diagnosticsd readHeader() malloc-before-check

**Status:** NEEDS GHIDRA CONFIRMATION
**Priority rationale:** `diagnosticsd` runs as UID=0 with ALL capabilities, no seccomp, no `NoNewPrivs`. A confirmed vulnerability here is full system compromise.

**Process profile:**
- PID: 599 (observed), UID=0
- Capabilities: ALL (full capability set)
- seccomp: NONE
- NoNewPrivs: NOT SET
- Listens on TCP port 49156

**Finding:** Preliminary Ghidra analysis suggests `readHeader()` may call `malloc(PAYLOAD_LEN)` before performing a bounds check on `PAYLOAD_LEN`. If confirmed, a crafted oversized UDS frame to port 49156 could trigger heap corruption.

**Additionally noted:** 128KB stack buffer in the UDS processing path — potential stack overflow surface.

**Action:**
1. RE `readHeader()` in Ghidra; confirm whether malloc precedes the size check
2. If confirmed: craft oversized UDS frame targeting port 49156
3. Test with OS-level peer credential check absent (trust is application-layer only: DoIP address + soft UDS `$27` gate — no kernel-enforced peer validation)

**Potential impact:** Root process, full capabilities, no seccomp — a working exploit yields complete system access (read/write to any partition, privilege escalation past SELinux via capability abuse).

---

### 10. diagnosticsd logical tester and session sequence

**Corrected 2026-11-14 — live-verified, not an untried trust-tier hypothesis.**
The old FA/F1/F0 source values and unvalidated-target claim were not the
accepted sequence. Use tester F4, target 0x0084 and the eight-byte `>HHI`
header; the old `>HHIH` example incorrectly inserted two extra bytes.
Extended session `10 03`, seed request `27 01` (31 all-FF bytes), and
`27 02` plus 12 zero bytes returned `67 02`. Default session was restored.
See the [owning diagnostic sequence](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14). No arbitrary-key,
calibration-write, Android-root or GHS-shell result follows from this grant.

---

### 11. 3x Boot Failure → GHS Lifecycle → ELK Escalation

**Status:** NOT TRIED
**Priority rationale:** Standard automotive OTA recovery escalation path — may reach ELK state without needing the exact J6_CDD DID (vector #4).

**Finding:** GHS disables the hypervisor timer and triggers a CSM reset after 3 consecutive boot failures. Repeated failures may escalate the GHS lifecycle state machine to ELK mode, which bypasses the standard rollback counter check.

**Risk:** Potentially destructive to calibration state in EEPROM or VIP persistent storage. The exact failure detection mechanism (what constitutes a "boot failure" in GHS state machine terms) must be mapped before attempting this deliberately.

**Prerequisite:** Document the GHS lifecycle state transitions from the GHS binary before attempting. Identify what state variables are written to persistent storage vs. volatile RAM only.

---

## Medium Priority

---

### 12. EEPROM 0x0B40 Developer Flag

**Status:** NOT TRIED
**Explicitly marked SAFE to test** in the project checklist (no CRC enforcement at boot confirmed).

**Details:**
- Address: `0x0B40`
- Modification: byte pattern `69 00 xx` → `69 FF xx`
- CRC protection: NONE confirmed — CRC is not enforced on this region at boot
- Risk level: Low — assessed as VIP-layer behavioral flag only per current analysis

**Action:** Flip bit with XGecu T48, reboot, observe any behavioral change in logcat, VIP diagnostic responses, or SELinux domain assignments.

**Note:** A VIP-layer behavioral change may alter how 0xb67d0 evaluates the **ADB/seed** check (not a SELinux "version check" — corrected 2026-08-25; see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2).

---

### 13. EEPROM 0x0A00 — Base Structure Testing

**Status:** NOT TRIED (despite being ranked vector #2 in early prioritization)
**Current understanding:** `0x0A00` is the Backup Security Block base pointer (range `0x0A00–0x0AFF`), not a single flag. The 871 VIP firmware references observed in the binary reflect structure member access patterns, not a single critical field.

**Internal tension:** The EEPROM analysis document says "Do NOT Modify 0x0A00" while teardown.md ranks it as High Feasibility / Low Risk. These assessments must be reconciled before proceeding.

**Resolution path:** Map VIP function at `0x9ce22` (which loads RAM address `0x714f` and branches to init at `0x97d78`) against the `0x0A00` structure layout in Ghidra. Identify which structure fields gate which behaviors before any modification.

**Action:** Complete the Ghidra mapping of `0x9ce22` before touching `0x0A00`.

---

### 14. ttyACM1 (MCP2200) Baud Rate Probing

**Status:** NOT TRIED (SELinux blocks shell write access)
**Finding:** `/dev/ttyACM1` is world-writable by DAC permissions, but SELinux blocks write from the shell domain. Passive `cat /dev/ttyACM1` produced no data in a 2-second window.

**Note from Jun 2026 session:** "Try manual probing with: `adb shell cat /dev/ttyACM1 &` then trigger activity on the device" — this passive read has not been attempted during active device operations (navigation input, audio, CAN bus activity).

**Hardware path:** The MCP2200 is gated by a 74LVC08A AND gate on the UART RX line. UART RX injection requires enabling the AND gate via a hardware control pin — shell-only access is insufficient for injection; physical board intervention is required.

**Action:** Attempt passive read during active device operation. If no data appears, deprioritize until hardware AND gate control is established.

---

### 15. ghs_abl_update (vda4) Content Analysis

**Status:** NOT ANALYZED
**Finding:** A dedicated ABL update partition (`vda4`, labeled `ghs_abl_update`) is routed through GHS. Content and update structure are unknown — no analysis has been performed.

**Action:**
```bash
adb shell ls -laZ /dev/block/by-name/ | grep vda4
adb shell dd if=/dev/block/vda4 bs=4096 count=256 2>/dev/null | xxd | head -100
```

**Why relevant:** If the ABL update partition has a different or absent signature verification scheme compared to the main OS partitions, it may represent an alternate code-injection path into the boot chain below GHS.

---

### 16. Offline 64GB eMMC Dump (BGA-153)

**Status:** NOT TRIED
**Hardware:** Samsung KLMCG4JEUD, BGA-153 package

**Hardware options:**
- XGecu T48 with BGA-153 ISP adapter (preferred — avoids reballing)
- Full reballing to BGA socket (last resort — high risk of pad damage)

**What offline dump provides:**
- Offline misc/AB0 modification for CRC warning test (vector #2 prerequisite)
- Full GHS `host_os` partition for analysis
- `vbmeta` partition for offline libavb fuzzing against VMM1
- `/data` partition (FBE-encrypted — will NOT decrypt offline without key material)

**What it does NOT provide:** /data decryption, live process behavior.

**Prerequisite for:** Vector #2 (CRC warning test), black-box vbmeta fuzzing, full GHS partition map.

---

### 17. IDiagnosticsInternalService via vndbinder

**Status:** NOT TRIED
**Corrected 2026-11-14:** the internal HIDL service is a separate surface;
  it is not needed to avoid the old invalid-tester TCP rejection. The direct
  F4/extended-session flow now obtains `67 02`. Live shell `lshal debug`
  could not connect to the internal service (missing service or permission);
  its methods and trust model remain unverified. The TCP format is custom GM
  framing, not DoIP.

**Prerequisite:** Access to a vendor SELinux domain — not achievable directly from the uid=2000 shell domain without a prior privilege escalation step. This vector becomes accessible if vectors #6, #7, or #9 yield a higher-privilege execution context.

---

## Research Tools Still Needed

| Tool | Purpose | Status |
|---|---|---|
| ghs_probe APK | Probe `/dev/ghs/*` ioctls and Trusty IPC ports | Written, not built |
| Frida S84.dll hooks | Capture the diagnosticsd/VIP `$27` seed→key transform (NOT gm_protokey — see the [C] corrections above; gm_protokey is the unrelated boot-time proto-key/disk-encryption gate) | Script ready; needs Windows host + DPS + MDI2 hardware |
| Renesas E10A-USB debugger | RH850 VIP JTAG access | Not acquired (~$150) |
| XGecu T48 + BGA-153 ISP adapter | Dump Samsung KLMCG4JEUD eMMC without reballing | Not acquired |
| ChipWhisperer or equivalent | Voltage glitch misc/AB0 CRC check in VMM | Not acquired |

---

## Dependency Graph (Simplified)

```
Physical JTAG (E10A-USB)
  └── Vector #3: RH850 JTAG → OBSERVE 0xb67d0 ADB/seed gate  [patch-to-stub VOID 2026-08-25]
  └── Vector #4: J6_CDD ELK DID discovery

Dealer Screen (software trigger)
  └── Vector #1: SELinux/UID state during dealer mode
      └── If SELinux=Permissive → direct misc write → downgrade

eMMC BGA-153 dump
  └── Vector #16: Offline misc/AB0 write
      └── Vector #2: CRC warning-only test

diagnosticsd exploit
  └── Vector #9: malloc-before-check → uid=0 shell
      └── Vector #10: Source-address spoofing (lower bar, try first)
          └── Vector #17: IDiagnosticsInternalService (post-escalation)

gm_protokey bypass
  └── Vector #6: bootreason=warm
  └── Vector #7: .validation delete → TOFU
  └── Vector #8: trigger/ directory oracle
```

---

## Recommended Execution Order (Next Session)

1. **Vector #1** — Reproduce the dealer screen trigger; immediately probe ADB UID and `getenforce` while in that state. Zero hardware cost, uses existing access.
2. **Vector #10** — Source-address spoofing on port 49156. Pure software, 30-minute test.
3. **Vector #5** — Build and deploy `ghs_probe.c`. Requires NDK setup, 2–4 hour effort.
4. **Vector #7 + #8** — Check `.validation` and `trigger/` directory. Pure shell, 15-minute test.
5. **Vector #6** — Probe `ro.boot.bootreason` and `gm_protokey` behavior. Pure shell, 15-minute test.
6. **Acquire E10A-USB** — Unblocks vectors #3 and #4, the highest-leverage hardware path.
7. **Vector #12** — EEPROM 0x0B40 flip. Low risk, confirmed safe to test per checklist.
8. **Vector #2** — After eMMC dump or misc write path confirmed via vector #1.

---

*Document generated: 2026-06-29. Update status fields as vectors are attempted.*
