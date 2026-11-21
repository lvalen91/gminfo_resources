# Untried Attack Vectors — gminfo37 Y181→Y177 Downgrade (Status Tracker)

**Scope:** status tracker for the Y181→Y177 downgrade attack-vector catalog (17 ranked vectors,
dependency graph, execution order). What does NOT live here: live T1 UDS/SecurityAccess bench
status (owned by `../diagnostics/`, see pointer below), EEPROM mechanism detail (owned by
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`), the Y175/Y177/Y181 firmware-diff evidence itself (owned
by `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`, carried unchanged — cited by name/section only).

Evidence tags `[C]` confirmed live / `[V]` verified / `[FW]`/`[S]` static firmware / `[inferred]`
/ `[U]` unverified / `[X]` external, per `platform/README.md`'s legend.

**Related:** `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` (ELK trigger, live-tested), `VIP_FIRMWARE_Y177_Y181_COMPARISON.md`
(carried unchanged — the Y177-stub refutation), `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`,
`../diagnostics/diagnosticsd_security_access.md`, `../diagnostics/diagnosticsd_routines_and_recovery.md`,
`../diagnostics/diagnosticsd_protocol.md`.

---

## Overview — the founding premise is refuted

**The original goal — a Y181→Y177 software downgrade to obtain a permissive SELinux posture —
does not hold.** Full primary-evidence extraction of the Y177 system image (`86283152`, corrected
2026-09-26) shows stock **Y177 boots SELinux `Enforcing`**, not permissive:

- **Boot cmdline** (signed boot image `86283154`): the early `enforcing=0 androidboot.selinux=permissive`
  token is overridden by the extra_cmdline's final tokens `enforcing=1 androidboot.selinux=enforcing
  buildvariant=user` (last token wins).
- **`/system/build.prop`**: `ro.build.type=user`, `ro.secure=1`, `ro.debuggable=0`, release-keys →
  AOSP init forces enforcing on user builds and ignores `androidboot.selinux=permissive`.
- **Compiled policy**: all four CIL sources (plat/vendor/plat_pub_versioned/product) have **0
  permissive domains**; the monolithic `sepolicy` is byte-identical to vendor `precompiled_sepolicy`
  (sha `027861ca…`).
- **Y177 `plat_sepolicy.cil` is byte-identical to Y181's** (0 diff) — there was no "unintended
  permissive policy change" for GM to correct between Y177 and Y181; both are the same enforcing
  policy. See `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2 for the primary diff (cite only, carried
  unchanged).
- **No permissive lever exists**: stock `init` uses `security_setenforce`/`getenforce` with no
  VIP/MEC/gmauth hook; across all 2093 system+vendor binaries the only `setenforce 0` caller is a
  manual Intel gfx-debug script behind an opt-in `--selinux_disable` flag (not boot- or VIP-gated).
- Adjacent real-device captures: Y175 (user build) and Y181 both report `getenforce=Enforcing`.

**Why the VIP-ADB-bypass analogy does not transfer:** the ADB bypass works because GM built a
deliberate userspace lever — `gmauthmanagerservice` reads the VIP's MEC/`is_secure_mode` and
relaxes adb-auth. SELinux enforcement has no analogous GM hook: neither `adbd` nor `gmauth` is a
`setenforce` caller, and `is_secure_mode` does not touch SELinux. The old "VIP forces permissive"
theory does not transfer to SELinux.

**Residual gap:** no Y177 *runtime* `getenforce` capture exists; static evidence is conclusive,
but an emulator/live-unit readout would close it 100%.

**Conclusion: a Y177 downgrade would not yield a permissive posture.** This doc's original
permissive-via-downgrade rationale no longer holds; the vector catalog below is kept as a status
tracker (several vectors are independently useful for ADB/seed-validator/ELK research), not as an
active plan toward the original goal.

Vectors are ranked by: (1) likelihood of breaking the current blocker, (2) estimated effort, (3)
available access level. Historical rankings below retain their original framing for traceability;
their presence is not a recommendation to brute-force writes, clear overrides, induce repeated
boot failures, or try generic root recipes.

---

> **Outbound pointer — not edited in this pass.** The "Current UDS and T1 priorities (2026-11-15)"
> status block (original source lines ~46-113: SID22 DID coverage audit, IOCID inventory/live
> control table, ABFT routine0475, `IECUUpdate.copyFile`, Type2 package registration, FSA
> RemoteModuleHMI) is live bench-status tracking for the diagnostics tree, not an untried-vector
> catalog entry. It already cites and belongs under `../diagnostics/diagnosticsd_routines_and_recovery.md`
> (diagnostic control coverage audit) and `../diagnostics/diagnosticsd_protocol.md` (IOCID
> inventory / live bench controls). **This reorg has no authority to edit the diagnostics tree** —
> flagging for the user/planner to move that block there; it is not folded into this doc.

---

## Critical Priority (Direct Impact on Downgrade Goal)

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

### 3. RH850 JTAG — Direct VIP Firmware Extraction and Observation

**Status:** NOT TRIED — scope reduced; patch premise void (History below)
**Priority rationale:** still the single highest-leverage hardware vector for observing the VIP
ADB/seed validator and the ELK trigger format.

**Hardware required:**
- Renesas E10A-USB debugger (~$150 new, ~$40–80 used/clone)
- Renesas CS+ IDE (free download from Renesas website)
- Fine-pitch probe or soldered wires to QFP-176 JTAG pins (TCK, TMS, TDI, TDO, TRST)

**What JTAG access still provides:**
- Full VIP firmware dump — no indirect Ghidra analysis from partial binary extraction
- Live breakpoints on security function at `0xb67d0` — observe exact inputs and branch logic
- Direct view of the J6_CDD channel message handler and the exact OBBPELK trigger format
- EEPROM 0x0A00 structure read behavior observable in-debugger under real execution conditions

**History:** originally framed as patching `0xb67d0` in-place with a 4-byte stub "equivalent to
Y177 behavior." **Corrected 2026-08-25:** void — Y177 has no stub; the function is full in every
build, so there is no "Y177 behavior" to reproduce and no VIP path to SELinux (per
`VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2). JTAG remains useful for *observing* the ADB/seed
validator's inputs and the J6_CDD/OBBPELK format, but does not yield permissive SELinux and does
not make the downgrade optional.

**OCD fuse status:** Unknown. Production RH850 units are frequently shipped without OCD fuse blown — the fuse is typically blown only in high-security applications. Probability of access: estimated moderate-to-high.

**Next action:** Acquire E10A-USB debugger. Identify TCK/TMS/TDI/TDO/TRST on the QFP-176 pinout against the RH850/F1K datasheet (marking TM52176; confirmed: `/Volumes/stuff/misc/research/GM_research/csm_eeprom/RH850_Vol_Glitch_Tools.txt`).

---

### 4. ELK Trigger via J6_CDD — RESOLVED: Selector Compiled; Outer Gates Unverified

**Status:** RESOLVED (2026-11-15) — formerly "exact selector unknown / not tried"; the owning
record is `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`, this entry is a pointer, not a restated finding.

Y175 VIP_APP has a descriptor/callback for selector `0x8180` and a compiled branch that logs the
ELK request and sends byte `E0` through IPC API selector `0x0C`. The complete CAN request and
outer authorization checks remain unverified. Runtime/file offsets must use the corrected module
payload mapping; see the owning [ELK analysis](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15)
(owner of the live-tested RID=0xFF01/`FUN_000641c2` ELK-trigger fact per the corpus-wide pointer
rule — this doc does not restate it).

The GWM `FDF0` writes and candidate GM `2F 81 80 03` were attempted through Android `diagnosticsd`,
with level-1 SecurityAccess. All returned NRC 31; Android logged missing DID/IOCID handler classes
and did not reboot. This is not a CAN-side rejection. See the live results at
`../diagnostics/diagnosticsd_routines_and_recovery.md#gwm-boot-target-and-gm-8180-follow-up-2026-11-15`.

**Next:** validate the selector through the direct CAN adapter when delivered, trace the
descriptor/session/security/mode gates, and observe the control response and actual boot
environment. No broad DID-write sweep is required. A successful request must not be presumed to
bypass signatures, rollback, bootloader lock state, or ELK provisioning gates. The previous
modified-image-loading claim was speculative; compiled ELK reachability alone does not establish
it.

---

### 5. Build and Deploy ghs_probe.c

**Status:** WRITTEN, NEVER BUILT
**Location:**
- `research/tools/ghs_probe/ghs_probe.c`
- `research/tools/ghs_probe/CMakeLists.txt`
- `research/tools/ghs_probe/AndroidManifest.xml`

(Path kept as-is; `research/tools/` is an excluded subdirectory not opened in this reorg pass.)

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

### 6. androidboot.bootreason=warm → gm_protokey Bypass — CORRECTED, does not reach UDS SecurityAccess

**Status:** NOT TRIED as a probe; **corrected scope** (2026-09-27) — resolving the "what would it
even get you" question that made this vector worth tracking.
**Finding source:** INVENTORY.md bypass #2

**Finding:** `/proc/cmdline` value `androidboot.bootreason=warm` causes `gm_protokey` to skip
seed-to-key validation entirely. `/proc/cmdline` is denied from uid=2000 shell context; the
bootreason value is typically also exposed as an Android system property (`ro.boot.bootreason`),
and whether `gm_protokey` reads `/proc/cmdline` directly or via a property API is unresolved.

**How to probe:** `adb shell getprop ro.boot.bootreason`; `adb shell find /vendor/etc/init
/system/etc/init -name "*.rc"` and check for bootreason conditionals; `adb shell cat
/proc/$(adb shell pidof gm_protokey)/maps | grep cmdline` to determine whether `gm_protokey`
reads `/proc/cmdline` directly or via a property API.

**History:** originally framed as a path to unlocking UDS `SecurityAccess ($27)`.
**Corrected 2026-09-27:** this does NOT unlock `$27` — `gm_protokey` is unrelated to the
diagnosticsd UDS chain. `$27` for `ETHERNET`/`NOTIFICATION` tiers is checked in-process by
`diagnosticsd`'s own `libuds`; the `VIP` tier is forwarded off-SoC to the VIP MCU via
`ProxyOfExtComp`/`SockAdaptor`, gated by the SBI EEPROM byte there — see
`../diagnostics/ethernet_uds_diagnosticsd.md`. Opening the `diagnosticsd` code path (vector #9) is
a separate, unrelated escalation; a `gm_protokey` bypass does not grant it. What remains open here
is only the boot-time proto-key/disk-encryption (DATA_LOCKED) gate itself, not UDS access.

---

### 7. Delete /data/vendor/gm/security/.validation (TOFU Re-provisioning) — CORRECTED, same scope limit as #6

**Status:** NOT TRIED; **corrected scope** (2026-09-27)
**Finding source:** INVENTORY.md bypass #3

**Finding:** Deleting `/data/vendor/gm/security/.validation` triggers TOFU (Trust On First Use)
re-provisioning, allowing injection of a researcher-controlled PAL key into the device trust
chain.

```bash
adb shell ls -laZ /data/vendor/gm/security/
adb shell ls -laZ /data/vendor/gm/security/.validation 2>/dev/null
# If accessible:
adb shell rm /data/vendor/gm/security/.validation
# Then observe logcat for re-provisioning behavior on next boot
adb logcat | grep -i "protokey\|TOFU\|provision\|PAL"
```

**History:** originally framed as a lever that could get update packages signed and accepted by
the GHS update path. **Corrected 2026-09-27:** this would NOT unlock UDS `SecurityAccess ($27)` —
that gate is unrelated to `gm_protokey`/the PAL trust chain (same correction as vector #6; see
`../diagnostics/ethernet_uds_diagnosticsd.md`). The update-path-signing question itself remains
open, but is decoupled from the original UDS-escalation framing.

---

### 8. gm_protokey_recovery_prop + /data/gmprotokey/trigger/ Oracle

**Status:** NOT TRIED (purpose TBD)
**Finding source:** INVENTORY.md bypasses #4 and #5

**Finding:** `/data/gmprotokey/trigger/` is writable from the shell. Writing files to this directory may trigger behavioral changes in the `gm_protokey` process.

```bash
adb shell ls -laZ /data/gmprotokey/
adb shell ls -laZ /data/gmprotokey/trigger/
adb shell touch /data/gmprotokey/trigger/test_probe
adb logcat -s gm_protokey &
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

### 10. diagnosticsd logical tester and session sequence — RESOLVED: live-verified sequence

**Status:** RESOLVED (corrected 2026-11-14) — live-verified, not an untried trust-tier hypothesis.

The old FA/F1/F0 source values and unvalidated-target claim were not the accepted sequence. Use
tester F4, target `0x0084` and the eight-byte `>HHI` header; the old `>HHIH` example incorrectly
inserted two extra bytes. Extended session `10 03`, seed request `27 01` (31 all-FF bytes), and
`27 02` plus 12 zero bytes returned `67 02`. Default session was restored. See the owning record:
`../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14`.
No arbitrary-key, calibration-write, Android-root, or GHS-shell result follows from this grant.

---

### 11. 3x Boot Failure → GHS Lifecycle → ELK Escalation

**Status:** NOT TRIED
**Priority rationale:** Standard automotive OTA recovery escalation path — may reach ELK state without needing the exact J6_CDD DID (vector #4).

**Finding:** GHS disables the hypervisor timer and triggers a CSM reset after 3 consecutive boot failures. Repeated failures may escalate the GHS lifecycle state machine to ELK mode, which bypasses the standard rollback counter check.

**Risk:** Potentially destructive to calibration state in EEPROM or VIP persistent storage. The exact failure detection mechanism (what constitutes a "boot failure" in GHS state machine terms) must be mapped before attempting this deliberately.

**Prerequisite:** Document the GHS lifecycle state transitions from the GHS binary before attempting. Identify what state variables are written to persistent storage vs. volatile RAM only.

---

## Medium Priority

### 12. EEPROM 0x0B40 Developer Flag

**Status:** NOT TRIED
**Explicitly marked SAFE to test** in the project checklist (no CRC enforcement at boot confirmed).

**Details:**
- Address: `0x0B40`
- Modification: byte pattern `69 00 xx` → `69 FF xx`
- CRC protection: NONE confirmed — CRC is not enforced on this region at boot
- Risk level: Low — assessed as VIP-layer behavioral flag only per current analysis

**Action:** Flip bit with XGecu T48, reboot, observe any behavioral change in logcat, VIP diagnostic responses, or SELinux domain assignments.

**Note:** A VIP-layer behavioral change may alter how `0xb67d0` evaluates the ADB/seed check (not
a SELinux "version check" — corrected 2026-08-25; see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2).
See also `VIP_CONTROL_ANALYSIS.txt`'s own open conflict on whether the verified bypass byte is
`0x0B40` or `0x0B41` (routed in VCA's Open Conflicts, not restated here).

---

### 13. EEPROM 0x0A00 — Base Structure Testing

**Status:** NOT TRIED (despite being ranked vector #2 in early prioritization)
**Current understanding:** `0x0A00` is the Backup Security Block base pointer (range
`0x0A00–0x0AFF`), not a single flag. The 871 VIP firmware references observed in the binary
reflect structure member access patterns, not a single critical field.

**Resolution path:** Map VIP function at `0x9ce22` (which loads RAM address `0x714f` and branches
to init at `0x97d78`) against the `0x0A00` structure layout in Ghidra. Identify which structure
fields gate which behaviors before any modification.

**Action:** Complete the Ghidra mapping of `0x9ce22` before touching `0x0A00`.

(See **Open conflicts** below — this vector's own "Do NOT Modify" vs "Low Risk" tension between
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` and `hardware/teardown.md` is carried there rather than
resolved here, since it touches a doc outside this reorg's authority.)

---

### 14. ttyACM1 (MCP2200) Baud Rate Probing

**Status:** NOT TRIED (SELinux blocks shell write access)
**Finding:** `/dev/ttyACM1` is world-writable by DAC permissions, but SELinux blocks write from the shell domain. Passive `cat /dev/ttyACM1` produced no data in a 2-second window.

**Note from Jun 2026 session:** "Try manual probing with: `adb shell cat /dev/ttyACM1 &` then trigger activity on the device" — this passive read has not been attempted during active device operations (navigation input, audio, CAN bus activity).

**Hardware path:** The MCP2200 is gated by a 74LVC08A AND gate on the UART RX line. UART RX injection requires enabling the AND gate via a hardware control pin — shell-only access is insufficient for injection; physical board intervention is required.

**Action:** Attempt passive read during active device operation. If no data appears, deprioritize until hardware AND gate control is established.

---

### 15. ghs_abl_update (vda4) Content Analysis

**Status:** ANALYZED (2026-11-20)
**Finding:** `ghs_abl_update` (vda4) is a **firmware-reflash capsule, not a runtime boot stage.** Its IPK payload (`0x600000` = 6 MiB; header CRC `0x3597d84c`, `0x55aa` marker, **no signature**) is byte-identical to the top 6 MiB of IFWI/SPI (`0x200000..0x800000`) — the field-updatable Intel firmware block (`$CPD`, FTPR, `$FPT`, the six RSA-2048 CSE/OEM manifests, and the firmware-resident ABL ELF). It is CRC-wrapped only; whether a reflash through it is authenticated depends on the updater and/or CSE/Boot Guard at next boot (not recoverable from this dump). Full detail + the related GHS-image-authentication verdict: [BOOT_TRUST_ANCHOR_AND_KEYS.md §3, §8](BOOT_TRUST_ANCHOR_AND_KEYS.md#3-soc_abl--elk-kernelflinger-and-ghs_abl_update).

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

### 17. IDiagnosticsInternalService via vndbinder — RESOLVED: surface still unverified, but not a required path

**Status:** RESOLVED as a dependency question (corrected 2026-11-14); methods/trust model of the
internal service itself remain unverified — **not** a blanket "not tried."

The internal HIDL service is a separate surface; it is not needed to avoid the old invalid-tester
TCP rejection. The direct F4/extended-session flow (vector #10) now obtains `67 02` without it.
Live shell `lshal debug` could not connect to the internal service (missing service or
permission); its methods and trust model remain unverified. The TCP format is custom GM framing,
not DoIP.

**Prerequisite:** Access to a vendor SELinux domain — not achievable directly from the uid=2000
shell domain without a prior privilege escalation step. This vector becomes accessible if vectors
#6, #7, or #9 yield a higher-privilege execution context (note: #6/#7 no longer feed UDS
escalation per their corrections above — only #9 plausibly does).

---

## Research Tools Still Needed

| Tool | Purpose | Status |
|---|---|---|
| ghs_probe APK | Probe `/dev/ghs/*` ioctls and Trusty IPC ports | Written, not built |
| Frida S84.dll hooks | Capture the diagnosticsd/VIP `$27` seed→key transform (NOT gm_protokey — see the corrections on vectors #6/#7; gm_protokey is the unrelated boot-time proto-key/disk-encryption gate) | Script ready; needs Windows host + DPS + MDI2 hardware |
| Renesas E10A-USB debugger | RH850 VIP JTAG access | Not acquired (~$150) |
| XGecu T48 + BGA-153 ISP adapter | Dump Samsung KLMCG4JEUD eMMC without reballing | Not acquired |
| ChipWhisperer or equivalent | Voltage glitch misc/AB0 CRC check in VMM | Not acquired |

---

## Dependency Graph (Simplified)

```
Physical JTAG (E10A-USB)
  └── Vector #3: RH850 JTAG → OBSERVE 0xb67d0 ADB/seed gate  [patch-to-stub VOID 2026-08-25]
  └── Vector #4: J6_CDD ELK DID — RESOLVED selector, outer gates unverified

Dealer Screen (software trigger)
  └── Vector #1: SELinux/UID state during dealer mode
      └── If SELinux=Permissive → direct misc write → downgrade

eMMC BGA-153 dump
  └── Vector #16: Offline misc/AB0 write
      └── Vector #2: CRC warning-only test

diagnosticsd exploit
  └── Vector #9: malloc-before-check → uid=0 shell
      └── Vector #10: RESOLVED live-verified session sequence (not source-address spoofing)
          └── Vector #17: IDiagnosticsInternalService (post-escalation, methods unverified)

gm_protokey bypass (decoupled from UDS SecurityAccess — see #6/#7 corrections)
  └── Vector #6: bootreason=warm
  └── Vector #7: .validation delete → TOFU
  └── Vector #8: trigger/ directory oracle
```

---

## Recommended Execution Order (Next Session)

Kept for historical traceability; items referencing a now-resolved/corrected vector (#10 source-
address spoofing, #4 selector discovery) should be re-read against that vector's corrected entry
above before acting on this list.

1. **Vector #1** — Reproduce the dealer screen trigger; immediately probe ADB UID and `getenforce` while in that state. Zero hardware cost, uses existing access.
2. **Vector #10** — now resolved (live F4/extended-session sequence); any remaining interest here is port-49156 testing per vector #9, not source-address spoofing.
3. **Vector #5** — Build and deploy `ghs_probe.c`. Requires NDK setup, 2–4 hour effort.
4. **Vector #7 + #8** — Check `.validation` and `trigger/` directory (TOFU/oracle question only — decoupled from UDS per correction above). Pure shell, 15-minute test.
5. **Vector #6** — Probe `ro.boot.bootreason` and `gm_protokey` behavior (DATA_LOCKED gate only — decoupled from UDS per correction above). Pure shell, 15-minute test.
6. **Acquire E10A-USB** — Unblocks vectors #3 and #4's outer-gate tracing, the highest-leverage hardware path.
7. **Vector #12** — EEPROM 0x0B40 flip. Low risk, confirmed safe to test per checklist (see VCA's own 0x0B40-vs-0x0B41 open conflict before relying on the address).
8. **Vector #2** — After eMMC dump or misc write path confirmed via vector #1.

---

## Open conflicts

1. **EEPROM 0x0A00 "Do NOT Modify" vs teardown.md "High Feasibility / Low Risk" (source L407).**
   `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` states "Do NOT Modify 0x0A00" for the Backup Security
   Block base pointer (range `0x0A00–0x0AFF`); `hardware/teardown.md` independently ranks the same
   address as High Feasibility / Low Risk. No dated correction in either doc reconciles this.
   **Flagging only** — `hardware/teardown.md` is outside this reorg's authority to edit, and ELA's
   own in-pass correction trail (per PLAN.md's EEPROM charter) does not address this specific
   cross-doc tension. Route: the EEPROM-charter owner (`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`) and
   `hardware/teardown.md` need to reconcile which risk rating stands before vector #13 is attempted.
2. **EEPROM 0x0B40 vs 0x0B41 developer-flag byte** (touches vector #12 above) — owned and tracked
   in `VIP_CONTROL_ANALYSIS.txt`'s Open Conflicts per PLAN.md item 5; not restated here, see VCA.

---

*Document generated: 2026-06-29. Status tracker; update status fields as vectors are attempted.*
