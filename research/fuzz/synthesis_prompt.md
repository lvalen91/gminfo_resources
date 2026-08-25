# PRIMED PROMPT — Next Course of Action Synthesis

<role>
You are an offensive-security research strategist supporting AUTHORIZED
vulnerability research. The operator owns the target hardware (GM Info 3.7
infotainment unit, 2024 Silverado ICE, Intel Atom x7-A3960, GHS INTEGRITY
hypervisor) and has physical bench access: ADB shell (uid=2000, via SBI EEPROM
bypass), the board itself, EEPROM read/write via XGecu programmer, and network
access to the vehicle's T1/Ethernet segment. Goal: identify and confirm
security findings for eventual coordinated disclosure to GM, historically
anchored around a Y181->Y177 downgrade goal but now broader (any confirmed
vuln in the platform).
</role>

<trust_filter>
This corpus mixes independently-audited findings with earlier AI-session
output that a skeptical provenance audit caught overclaiming in places. OBEY:
1. Preserve every confidence marker exactly as given: [C]/VERIFIED (confirmed
   against a real artifact), [I]/INFERRED (plausible, not directly measured),
   [O] (open/testable question), [U] (unknown), UNSUPPORTED, CONTRADICTED.
   When ranking, weight [C]/VERIFIED items far above [I]/[O]/UNSUPPORTED ones.
2. Do not invent new technical claims. Every recommendation must trace to a
   specific finding in the artifacts below.
3. Two of the three tracks below (AVB/.vmm1 fuzzing, OTA RPC/A-B-metadata
   tooling) were built THIS session and are validated as CODE (compiled/run
   successfully against real reference material or synthetic data) but have
   NOT yet produced a finding against the real target -- both are explicitly
   blocked on disassembly/RE work not yet done (see each RECON_TODO). Do not
   conflate "the tooling works" with "a vulnerability was found."
4. The third track (diagnosticsd/UDS-on-49156) comes from TWO independent
   analysis passes at different dates (2026-06-29 and 2026-08-17) that
   converged on the same target independently -- treat that convergence as a
   meaningfully stronger signal than a single analysis pass, and say so.
</trust_filter>

<artifact name="T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md §3c/§4/§7" provenance="Opus, 2026-08-17, post-provenance-audit corrected, [C]/[I]/[O] tagged">

### (b) Custom calibration ON the radio from a T1 tap — **path EXISTS; single gate is UDS `$27`**
- `[C]` A genuine self-write path to this module's own `CalSets.db` exists and is wire-reachable on
  `eth0:49156`: `diagnosticsd` UDS calibration-programming (`$27` → `$34/$36/$37` transfer;
  `CalibrationProgrammer.cpp`, `UDSTransferDataRequestHandler`) → writes to
  `/mnt/vendor/calibration/overrides/` → `calserviced` inotify picks it up → `processZippedModFile` /
  `apply_overrides` → `/mnt/vendor/calibration/database/CalSets.db`.
- `[C]` **The calibration blob is NOT signature-protected** — integrity only: a 16-bit checksum
  (`CAL_CHECKSUM_FAILURE`) + a SHA-256 (`CAL_MESSAGE_DIGEST_FAILURE`, `generateSHA256`). Both are
  recomputable by anyone editing the blob. No RSA/X.509/SecOC anywhere in the cal path.
- `[C]` **The single hard gate is UDS SecurityAccess `$27`** (`SecurityRequestToResponsePipeline.cpp`,
  `checkSecurityLevelTable`, seed/key). Per `CALDEF_VIP_CALIBRATION_ANALYSIS.txt` the programming-level
  access is validated **via the VIP** (`RID 021E converted to Security Access Request per IPC ver 2.6`),
  anchored in the **VIP PROTOKEY + EEPROM** — the algorithm is **not present in the SoC firmware** to
  derive. Reads (default-session DIDs, `$22/$1A`) are effectively open; the write is one auth barrier away.
- `[C]` **`SCREEN_RESOLUTION` is present and structurally writable** in `CalSets.db`: `CalType 4` enum,
  **current value 2 = 1280×768**, options `0:800×480 · 1:1280×720 · 2:1280×768 · 3:1920×1080 ·
  4:2400×960` (`CalDefFileName GIS738_RVCVIDEOROBUSTNESSREQUIREMENT` v7).
- `[C]`/`[O]` **Local-only bypass:** `calserviced` contains an `OVERRIDE_BACKDOOR` that applies
  `*.calovride` files **skipping the UDS/`$27` path entirely**, with a `!!!DISABLE BEFORE RELEASE!!!`
  warning at `main`. It needs `vendor_cald`-context filesystem write (dir mode 770) — **not** reachable
  from the net or an adb shell. Whether it is compiled out of this release is undetermined from strings —
  **checkable from `scratchpad/diagx/bin__calserviced` (the `main()` override path).** `[O]`

### (c) Escalation / reflash ON the radio from a T1 tap — **reflash sealed; one sharp RCE lead**
- `[C]` Self-reflash of Android partitions goes through `gm_update_engine` (direct eMMC writes), gated by
  **RSA/TSS module signing + AVB (locked/green) + GHS INTEGRITY rollback index** — sealed, downgrade-blocked
  (confirmed Y181→Y177). `diagnosticsd`'s `RequestDownload/TransferData` serve calibration+module data,
  **not** Android partition images. The `swupdate` HAL reflashes *peripheral ECUs via the VIP*, not the radio.
- `[C]`facts / `[I]`exploit — **the escalation convergence:** `diagnosticsd` runs **uid=0, all caps, no
  seccomp**, and parses **attacker-controlled framing on `49156` with the target address unvalidated**. A
  memory-safety bug in that parser = **root on the radio from the wire**, which would then reach the
  `*.calovride` vendor_cald backdoor and flip `SCREEN_RESOLUTION` **without ever needing `$27`**. This is
  the single highest-value target the three analyses surfaced. Unproven — needs a bug in the UDS/framing
  parser.
- `[C]` The other two wire listeners (6363 NFD, 49156) otherwise land in the **unprivileged Android guest**

  `$27` SecurityAccess that gates a `SCREEN_RESOLUTION` write (§3b). Per
  `CALDEF_VIP_CALIBRATION_ANALYSIS.txt`, cal-programming security access is validated by VIP firmware
  reading **PROTOKEY + EEPROM flags**. So the EEPROM the owner can already write is a **demonstrated lever
  over VIP security state** — the exact layer the calibration gate lives in.
- `[O]` **What is NOT yet proven (do not overclaim):** flipping the *ADB* SBI (`0x0441/0x0A81`) is **not
  shown** to also open the *calibration* `$27` gate — they share a subsystem and an anchor, not a proven
  single flag. The open, testable question is whether a **different** EEPROM flag governs the diagnostic/
  calibration security level the way `0x0440` governs ADB. The undocumented-flag candidates already
  flagged in the security region are the first place to look:
  - `0x04A0` (17 refs) / `0x04C0` (11 refs) — near `[IPC_S]` (VIP↔SoC secure IPC) strings.
  - `0x0A40` (28 refs), `0x0BE0` (24 refs) — feature-flag region.
  - (`0x0A00`/`0x0B00` are structure **base** addresses — do **not** poke.)
- `[O]` **In-band EEPROM access is plausible but unconfirmed:** `/dev/i2c-0` and `/dev/i2c-1` are
  **world-readable/writable** (`crw-rw-rw-`, `raw/i2c_devices.txt`). If either bus reaches the M24C64, an
  ADB shell (obtained via the SBI flip) could read/write the EEPROM **without a hardware programmer** and
  iterate the candidate-flag test above — subject to SELinux. Which bus maps to the EEPROM is the
  outstanding item. If proven, the loop becomes: physical SBI flip once → ADB → in-band I²C to probe
  whether a cal/diag security flag exists → if so, a `$27`-free calibration write from software.

**Net:** the `$27` wall on the calibration write is not a dead end for *this* owner the way it is for a
pure wire attacker — because the owner controls the VIP's EEPROM, which is the anchor layer. Whether that
control extends to the calibration gate specifically is the concrete next experiment, not a settled result.

---

## 5. Two distinct display-parameter stores (disambiguation for the CarPlay-fullscreen goal)

There are **two separate "display parameter" stores**, and conflating them wastes effort:

- **Store A — EEPROM `0x0E00`–`0x0FDF` (VIP-side, bit mapping GUESSED).** Scaled-pixel / timing / touch
  values (e.g. `0xE13=900` "display width", `0xE17=600` "height", `0xE1F=200` backlight max, brightness/
  color LUTs). Per `EEPROM_Analysis_Report.md` these readings are **inferred**, and they look like
  **touch-active-region / backlight / UI-timing** values — **not** application window bounds. Flipping
  these is unlikely to change CarPlay/app bounds. `[I]`
- **Store B — `CalSets.db` `SCREEN_RESOLUTION` (SoC-side, `$27`-gated).** The `CalType 4` enum in §3b
  (option `4 = 2400×960` is the panel's native res per `hardware/teardown.md`). This is the calibration
  actually consulted by the display/RRO/DisplayArea stack. `[C]`

**Implication:** the CarPlay-fullscreen/immersive lever most plausibly lives in **Store B**
(`SCREEN_RESOLUTION`) and/or the RRO/DisplayArea layer — reached via the diagnostic/calibration plane in
§3b — **not** in the EEPROM `0x0E13/0x0E17` display bytes. Don't burn cycles flipping EEPROM display bits
expecting window-bounds changes.

---

## 6. Corrections to prior corpus

- **"192.168.1.1 = GHS hypervisor bridge" is wrong.** The `9002/9005/9010/9012/9016/9018` endpoints on
  `::ffff:192.168.1.1` are the **paravirtual GHS↔Android IPC transport**, **not** a networked hypervisor
  service reachable from the T1 wire. Earlier notes (Dec-2025 compendium; apr2026 "GHS Hypervisor Bridge
  @ 192.168.1.1") that imply host services live at `.1` *on the wire* are superseded: the guest is `.100`,
  the 90xx ports are the VM↔host bridge, and no `.1` interface/route reaches off-box.
  **⚠CORRECTED — do not overstate reachability:** `.1` is **not** "unreachable even locally" — `open_ports.txt`
  shows the Android guest holding **ESTABLISHED** client connections to `.1:9005/9010/9012/9018`, so the
  guest reaches the bridge in the **client** direction. The correct claim is narrower: `.1` is a
  *paravirtual guest↔host IPC address*, reachable by the guest as a client but **not exposed on the
  physical T1 wire** and not a route to hypervisor code.
- **`diagnosticsd` = the `49156` UDS server (attribution caveat).** Two analyses conflicted: a SELinux
  read of `vendor_sepolicy.cil` shows the `gm_diagnosticsd` domain with **no `tcp_socket`/`node_bind`
  perms**, while the binary strings (`TCPServer.cpp`, `listen`/`bind`), the rc **"stop diagnosticsd for
  cts-on-gsi tcp port testcases"** hook, and the live `0.0.0.0:49156` all say `diagnosticsd` **is** the
  UDS-over-TCP server. The binary/rc/netstat evidence is stronger; the likely resolution is that
  `diagnosticsd` (`user root`, `class hal core`) binds under a different effective domain than the label
  the policy grep keyed on, or the CIL grep missed a rule. **Settleable in one live command:** `ss -tlnp`
  (map `49156` → pid → `/proc/pid/exe`) + `ps -Z` for the running domain. `[O]`

---

## 7. Open / testable items (prioritized)

1. `[O]` **Is the `*.calovride` OVERRIDE_BACKDOOR compiled into this release?** Analyze
   `scratchpad/diagx/bin__calserviced` `main()` path. If live, it's the `$27`-free cal-write route
   (contingent on a `vendor_cald` foothold).
2. `[O]` **Which I²C bus reaches the M24C64?** If `/dev/i2c-0`/`i2c-1` (world-writable) map to it, in-band
   software EEPROM R/W is possible from the SBI-enabled ADB shell — no programmer needed.
3. `[O]` **Does an EEPROM flag govern the calibration/diag `$27` gate** the way `0x0440` governs ADB? Probe
   candidates `0x04A0`, `0x04C0`, `0x0A40`, `0x0BE0` (one at a time, backup first). This is the crux for a
   software-only `SCREEN_RESOLUTION` write.
4. `[O]` **Confirm the `49156` owner/domain** live (`ss -tlnp` + `ps -Z`) — resolves the §6 attribution.
5. `[O]` **`diagnosticsd` parser as an RCE target** (root, no seccomp, unvalidated target address) — the
   sharpest escalation-on-the-radio lead if pursued.
6. `[O]` **`$27` seed/level structure** — capture a seed on `49156` in a programming session to
   characterize the challenge (even without the algorithm, the level map is useful).

---

## 8. Key evidence

`enumeration/Y181/apr2026/network_scan.txt`; `raw/{ip_addr,ip_route,network_interfaces,open_ports,
arp_table,init_services,gm_update_service,i2c_devices}.txt`; `ghs_attack_surface.txt`;
`pulled_files/vendor_sepolicy.cil`. Firmware vendor part `86331650` extracted to
`scratchpad/diagx/` (`bin__diagnosticsd`, `bin__calserviced`, `lib64__libpal_diagnostics.so`,
`lib64__vendor.gm.diagnostics.ethernet@1.0-impl.so`, `calibrations__CalSets.db`, `etc__init__*.rc`).
Corroborating: `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt`, `research/UPDATE_PROCESS_ANALYSIS.txt`,
`research/UNTRIED_ATTACK_VECTORS.md`, `eeprom/EEPROM_Analysis_Report.md`,
`eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`, `hardware/teardown.md`.

</artifact>

<artifact name="UNTRIED_ATTACK_VECTORS.md #9/#10 + execution order" provenance="analyst, 2026-06-29, status-tagged">
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


</artifact>

<artifact name="Bundle 1 (AVB/.vmm1) session result" provenance="this session, hand-verified by actual compilation/execution">
Built and compiled avb_bundle1_fuzzer.c against the real upstream libavb source
pinned to commit c0af371864984cddfb983c3b4cba42703b5ba58a (the exact commit
where AVB_VERSION_MAJOR/MINOR=1/2, matching the device's live
ro.boot.vbmeta.avb_version=1.2). Ran all 11 generated seeds (O1 header
offset/size overflow, O2 total-length overflow, O3 descriptor payload
overflow, O5-replica boot-header bound check, O6 rollback high-dword, T1
TOCTOU placeholder) with ASan against real libavb 1.2. Result: NO crash on any
seed -- upstream's own avb_safe_add/bounds-check guards correctly rejected the
naive overflow attempts (observed directly in the trace: "avb_util.c:131:
ERROR: Overflow when adding values", "avb_descriptor.c:97: ERROR: Invalid
descriptors offset"). This means: (1) the harness/tooling itself is proven
correct and working, (2) clean upstream libavb 1.2 is not naively vulnerable
to these classes, (3) the open question this does NOT answer is whether GHS's
`.vmm1` port kept those same guards intact when they statically compiled
libavb into the hypervisor -- confirming that requires disassembling
.vmm1.text (not done) and diffing against upstream, per the artifact's own
§5.1/§5.3 recommendation.

</artifact>

<artifact name="Bundle 2 (OTA RPC / A-B metadata) session RECON_TODO.md" provenance="this session, hand-verified">
```markdown
# RECON TODO — Validation Tasks for OTA/A-B Tooling

**Context:** The provided scripts (`ota_isys_frame_fuzzer.py`, `ab_metadata
`ab_metadata_crc_forge.py`) are 
structurally plausible but rely on [U] (Unknown) or [I] (Inferred) claims f
from the artifact. 
To move from "plausible" to "known-correct," the following RE tasks must be
be completed.

**Artifact Reference:** `RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md` §7 "Bottom
"Bottom line".

---

## 1. Disassemble `.ota_update.text` (71 KB)
- **Target:** `SOC_HOSTOS (85098662)` binary, section `.ota_update.text`.
- **Status:** Not disassembled in corpus (only section boundaries + rodata 
strings available).
- **Why Needed:** 
  - To confirm the **opcode table** for the `ota-isys` command frame.
  - To verify the **frame layout** (offset/width of length field, opcode po
position).
  - To identify specific validation logic beyond the "Bad command length" s
string [C].
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Allows removing `[U]` assumptions on frame 
structure.
  - Enables precise fuzzing of opcodes rather than just length fields.
- **Action:** Load binary into Ghidra/IDA, symbolize `.ota_update.text`, an
and analyze `OTA_InitialTask`.

## 2. RE `/system/lib64/libghs_lip.so`
- **Target:** GHS LIP kernel shim library on the Android guest side.
- **Status:** Not RE'd in corpus. Repo prior probe used guessed ioctl codes
codes (`_IOR('g', 0x01-0x02, int)`).
- **Why Needed:** 
  - To recover the real **ioctl dispatch table** for `/dev/ghs/ota-isys`.
  - To confirm if `write()` is sufficient or if specific `ioctl` commands a
are required to trigger the RPC path.
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Allows replacing raw `write()` with correct
correct `ioctl` calls if needed.
  - Confirms whether the "dumb pipe" assumption [I] holds or if there is hi
hidden validation in the shim.
- **Action:** Extract `libghs_lip.so`, analyze exported symbols and ioctl h
handlers.

## 3. Confirm A/B Metadata Sub-field Offsets
- **Target:** Live device `misc` partition (offset 0x800).
- **Status:** Artifact confirms offset 0x800 [C], but field widths/offsets 
are [U].
- **Why Needed:** 
  - To validate the `--crc-range` argument in `ab_metadata_crc_forge.py`.
  - To enable the `--field-offset` argument for precise mutation (currently
(currently defaults to demo bit-flip).
  - To ensure mutations target the correct fields (`priority`, `tries_remai
`tries_remaining`) without corrupting adjacent data.
- **Unblocks:** 
  - `ab_metadata_crc_forge.py`: Allows removing `--scan` dependency for pro
production use; enables hardcoded offsets behind verified `ASSUMPTION:` com
comments.
- **Action:** 
  1. Dump `misc` from live device (`adb pull /dev/block/by-name/misc`).
  2. Compare against known good state (e.g., after a successful boot).
  3. Use `strace` on `gm_update_engine` or direct hex inspection to correla
correlate field changes with slot state.

## 4. Verify SELinux Context for `/dev/ghs/ota-isys`
- **Target:** Device node permissions and SELinux policy.
- **Status:** Artifact notes DAC is `rw-rw-rw-` [C], but SELinux is the rea
real gate.
- **Why Needed:** 
  - To ensure `ota_isys_frame_fuzzer.py` can actually open/write the device
device without being blocked by policy.
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Ensures tool execution isn't blocked by sec
security policy during testing.
- **Action:** Run `ls -Z /dev/ghs/ota-isys` and check `audit.log` for denia
denials during test runs.

---

**Priority Order:** 
1. Task #2 (libghs_lip.so) — Critical for `ota_isys` tool correctness.
2. Task #3 (A/B Offsets) — Critical for `ab_metadata` tool safety/accuracy 
and enabling `--field-offset`.
3. Task #1 (Disassembly) — High value for deeper exploit dev, but length fu
fuzzing works without it.
```

</artifact>

<task>
Synthesize a single, ranked "next course of action" list across ALL THREE
tracks in the artifacts above:
  (A) diagnosticsd/UDS-on-49156 RCE lead (readHeader malloc-before-check,
      source-address spoofing, EEPROM<->$27 convergence) -- established by
      the older/newer corpus, NOT built this session.
  (B) AVB/.vmm1 fuzz harness (Bundle 1) -- built and validated against real
      upstream libavb 1.2 this session; blocked on .ota_update-equivalent
      disassembly of .vmm1 itself to know if GHS's port kept upstream's
      overflow guards.
  (C) OTA RPC / A-B-metadata tooling (Bundle 2) -- built and validated against
      synthetic/reference data this session; blocked on disassembly of
      .ota_update.text and RE of libghs_lip.so for real frame/ioctl layout.

For each of the top 5-7 recommended next actions, state:
  - Which track it belongs to (A/B/C) and the exact source finding/confidence
    marker it's based on.
  - What specifically to DO (a concrete, bounded action -- not "investigate more").
  - What it requires (existing bench access? new tooling? RE work? hardware?).
  - What it would prove or unlock if it succeeds.
  - Effort/cost estimate in the terms the source docs themselves use (e.g.
    "pure shell, 15 minutes" vs "requires Ghidra RE session").

Rank by: (1) confidence of the underlying finding, (2) whether it's blocked on
work not yet done vs. immediately actionable with current bench access, (3)
payoff if it succeeds. Be explicit about why track A currently outranks or
doesn't outrank tracks B/C given rule 4 of the trust filter. End with a single
clear recommendation for the very next action to take.
</task>
