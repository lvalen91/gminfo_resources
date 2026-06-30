# Untried Attack Vectors — GM Info 3.7 (gminfo37) Y181→Y177 Downgrade

**Date:** 2026-06-29
**Project:** gminfo37 — downgrade GM Info 3.7 head unit from Y181 to Y177
**Current access:** uid=2000 ADB shell, physical board access, Renesas RH850 VIP MCU

---

## Overview

As of 2026-06-29, several high-value attack vectors identified in the research have never been attempted. This document tracks untried paths ranked by probability of advancing the Y177 downgrade goal.

The goal remains: achieve a successful Y181→Y177 software downgrade, ultimately to obtain a permissive SELinux enforcement posture (present in Y177, locked down in Y181). Blockers are the GHS rollback counter in the misc/vda9 partition and the VIP RH850 firmware security function at 0xb67d0 that enforces the version floor.

Vectors are ranked by: (1) likelihood of breaking the current blocker, (2) estimated effort, (3) available access level.

---

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
- Fine-pitch probe or soldered wires to QFP-144 JTAG pins (TCK, TMS, TDI, TDO, TRST)

**What JTAG access provides:**
- Full VIP firmware dump — no indirect Ghidra analysis from partial binary extraction
- Live breakpoints on security function at **0xb67d0** — observe exact inputs and branch logic
- Ability to **patch 0xb67d0 in-place** with a 4-byte stub (equivalent to the Y177 behavior), making the Y181-version VIP behave identically to Y177 without touching the GHS rollback counter at all — this sidesteps the entire misc/AB0 blocker
- Direct view of the J6_CDD channel message handler and the exact OBBPELK trigger format
- EEPROM 0x0A00 structure read behavior observable in-debugger under real execution conditions

**Why game-changing:** If RH850 JTAG is accessible (OCD fuse not blown, which is likely on production infotainment units that are not end-of-life secured), patching 0xb67d0 achieves the permissive SELinux goal without performing the downgrade at all. The downgrade becomes optional.

**OCD fuse status:** Unknown. Production RH850 units are frequently shipped without OCD fuse blown — the fuse is typically blown only in high-security applications. Probability of access: estimated moderate-to-high.

**Next action:** Acquire E10A-USB debugger. Identify TCK/TMS/TDI/TDO/TRST on the QFP-144 pinout against the RH850/P1M-C datasheet.

---

### 4. ELK Trigger via J6_CDD — Exact SID/DID Unknown

**Status:** NOT TRIED (exact trigger format unknown)
**Priority rationale:** ELK mode bypasses misc/BCB entirely via HECI→CSE→ABL path, which is independent of the GHS rollback counter.

**Findings:**
- VIP J6_CDD diagnostic channel contains the string "Diag Elk Reboot Req"
- GHS binary contains symbol `BootELKSendAblUserCommand` at **0x0087452a**
- ELK boot path goes through HECI→CSE→ABL, not through the standard GHS boot path that checks the misc/AB0 rollback counter

**Unknown:** The exact UDS SID/DID combination that triggers the ELK reboot request on J6_CDD. Without this, the channel cannot be exercised.

**How to find the trigger:**
- Option A (preferred): RH850 JTAG (vector #3) — set a breakpoint on the J6_CDD message dispatcher and observe which DID invokes the "Diag Elk Reboot Req" handler
- Option B: Brute-force diagnostic DIDs on J6_CDD channel using a UDS scanner; log NRC vs. positive response to identify live DIDs

**Why valuable:** ELK mode may allow loading a modified boot image without the rollback counter check that currently blocks the Y181→Y177 downgrade, since the ELK path was designed for factory and end-of-life reflash scenarios.

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

**Potential impact:** If `gm_protokey` can be bypassed, `DiagnosticsService` and UDS `SecurityAccess ($27)` unlock becomes accessible, opening the `diagnosticsd` code path running as root with full capabilities (see vector #9).

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

**Potential impact:** A researcher-controlled PAL key in the trust chain could be leveraged to sign update packages accepted by the GHS update path, or to unlock `SecurityAccess ($27)` without needing the original GM seed-to-key algorithm.

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

### 10. diagnosticsd 8-byte Header Source-Address Spoofing

**Status:** NOT TRIED
**Priority rationale:** May grant pre-authorized tester trust tier without needing the seed-to-key algorithm.

**Finding:** `diagnosticsd` uses a custom 8-byte framing header:
```
[SRC: 2 bytes, BE] [TGT: 2 bytes, BE] [LEN: 4 bytes, BE] [UDS payload]
```
Target address is NOT validated by `diagnosticsd`. Logical addresses `0x00FA` (factory tester), `0x00F1`, and `0xF0` may grant a pre-authorized trust tier that bypasses the `SecurityAccess ($27)` gate.

**Action:**
```python
# Python test frame — send to port 49156
import socket, struct
src = 0x00FA   # factory tester address
tgt = 0x0001   # head unit
payload = bytes([0x10, 0x03])  # DiagnosticSessionControl, extendedDiagnosticSession
header = struct.pack('>HHIH', src, tgt, len(payload), 0) + payload
s = socket.socket()
s.connect(('127.0.0.1', 49156))
s.send(header)
print(s.recv(256).hex())
```

**Observe:** Does the NRC change from `0x10` (generalReject) when SRC is `0x00FA` vs. `0x0001`? A different NRC indicates the source address is being used for trust tier routing.

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

**Note:** Even a VIP-layer behavioral change is useful — it may alter how 0xb67d0 evaluates the version check.

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
**Finding:** `IDiagnosticsInternalService` is exposed over vndbinder and may bypass the TCP generalReject gate that blocks port 49156 from untrusted callers. The vndbinder interface may skip the DoIP framing and source-address trust tier checks present in the TCP path.

**Prerequisite:** Access to a vendor SELinux domain — not achievable directly from the uid=2000 shell domain without a prior privilege escalation step. This vector becomes accessible if vectors #6, #7, or #9 yield a higher-privilege execution context.

---

## Research Tools Still Needed

| Tool | Purpose | Status |
|---|---|---|
| ghs_probe APK | Probe `/dev/ghs/*` ioctls and Trusty IPC ports | Written, not built |
| Frida S84.dll hooks | Capture gm_protokey seed→key transform | Script ready; needs Windows host + DPS + MDI2 hardware |
| Renesas E10A-USB debugger | RH850 VIP JTAG access | Not acquired (~$150) |
| XGecu T48 + BGA-153 ISP adapter | Dump Samsung KLMCG4JEUD eMMC without reballing | Not acquired |
| ChipWhisperer or equivalent | Voltage glitch misc/AB0 CRC check in VMM | Not acquired |

---

## Dependency Graph (Simplified)

```
Physical JTAG (E10A-USB)
  └── Vector #3: RH850 JTAG → patch 0xb67d0 directly    [HIGHEST LEVERAGE]
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
