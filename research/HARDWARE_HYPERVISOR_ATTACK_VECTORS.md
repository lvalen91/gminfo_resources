# Hardware and Hypervisor Attack Vectors — GM Info 3.7 (gminfo37)
**Date:** 2026-06-29  
**Scope:** 37 hardware vectors + 53 hypervisor/GHS vectors analyzed  
**Synthesis note:** The Opus-level synthesis agent was safety-flagged; this document is synthesized from the raw agent output directly.

Platform: Intel Atom x7-A3960 (Apollo Lake/Goldmont), Android 12 AAOS, GHS INTEGRITY IoT 2020.18.19, Linux 4.19.305.  
Current physical access: board exposed, EEPROM (M24C64) already bypassed via XGecu, Renesas RH850 VIP MCU on board.

---

## Part 1 — Hardware Attack Vectors

### Intel DCI (Direct Connect Interface) — USB3 JTAG

**What it is:** On Apollo Lake, the PCH DFx block tunnels JTAG over the USB3 port if two conditions hold:
- HDCIEN=1 in P2SB_DCI.DCI_CONTROL_REG (PCR base 0xFDB8, offset 0x04, bit 4)
- IA32_DEBUG_INTERFACE MSR (0xC80): bit 0 (ENABLE)=1, bit 30 (LOCK)=0

**If enabled:** A USB Type-A to Type-A cable (VBUS pins cut) + Intel System Studio gives full JTAG: halt all CPU threads, read/write arbitrary physical memory, access SMM, read TXE/CSE-visible regions, set hardware breakpoints. Software-invisible.

**On production automotive builds:** Shipped with HDCIEN=0, MSR=0x40000000 (LOCK set, ENABLE clear). But confirm — may have been left open on this specific unit.

**Three ways to check / enable DCI:**

| Method | Difficulty | Notes |
|---|---|---|
| DbC (USB3 Debug Class) | Low | $15 cable; requires HDCIEN=1 already set |
| OOB via Intel SVT CCA | Medium | $300–2000 FPGA device; bypasses USB stack; works before OS boots |
| NVRAM variable modification | Medium | RU.efi sets hidden PchSetup/CpuSetup NVRAM vars; Boot Guard does NOT validate NVRAM content; requires UEFI shell boot |

**If NVRAM alone is blocked:** SPI flash programmer patches the SiInit PEI module that unconditionally writes IA32_DEBUG_INTERFACE to 0x40000000. Requires 1.8V SOIC-8 clip + CH341A + 1.8V adapter (critical — 3.3V destroys the flash).

**DCI capability if enabled:**
- Full memory R/W → read TXE-managed secrets in SRAM → defeat Boot Guard key chain
- Hardware breakpoints on the GHS hypervisor CRC32 comparison path
- Read/write misc/vda9 directly from host with jtag-target memory access

**Reference:** INTEL-SA-00127; Goryachy & Ermolov "Intel DCI Secrets" (33C3/HITB2017AMS); DCILeech (DFRWS 2021).

---

### CVE-2021-0146 — Apollo Lake Red Unlock (explicitly names x7-A3960)
- **CVSS:** 6.8 (AV:Physical, AC:Low, UI:None)
- **What:** Voltage fault injection against the DFX Aggregator via VNNLDO regulator achieves "Red Unlock" mode — full DCI JTAG with no other preconditions.
- **Method (published):** CVE-2021-0146 exploits the DFX Security Policy state machine's non-reset behavior after VFI. Once Red Unlock is achieved, DCI is active.
- **Impact:** From Red Unlock + DCI: set a hardware breakpoint on the GHS CRC32 comparison instruction, observe the computed CRC32 value in a register, patch it to match stored value before the comparison completes — online rollback counter modification without any software primitives.
- **GM applicability:** Unknown whether the Nov 2021 OEM BIOS patch was applied. Confirm by checking TXE firmware version via MEAnalyzer on IFWI dump.

---

### SPI Flash (IFWI) — Extraction and Analysis

**Flash chip:** 8MB IS25WP064A SPI NOR (or Winbond W25Q128.W on some units — confirm by PCB inspection).  
**Operating voltage:** 1.8V (critical — do NOT use 3.3V programmer directly).

**Extraction steps:**
1. Locate SOIC-8 flash chip near SoC on PCB.
2. Attach Pomona 5252 clip with 1.8V adapter board.
3. `flashrom -p ch341a_spi -r ifwi_dump.bin` (3× — compare SHA-256).
4. `ifdtool -x ifwi_dump.bin` → extracts TXE, BIOS/IFWI, GbE, Platform Data regions.
5. `MEAnalyzer ifwi_dump.bin -dfpt` → TXE version, SKU, SVN, VCN, production/pre-production status.

**What to look for:**
- TXE version → determine SA-00086 applicability (TXE 3.0.1.1107 is the PoC-tested target).
- FIT table at pointer stored at physical 0xFFFFFFC0 → Boot Guard Key Manifest → `BootGuardKeyHash` field.
- MSR 0x13A on live system (requires root): if returns 0 → FPF not burned → manufacturing mode → Boot Guard FPF key substitution possible.
- **If FPF not burned:** Substitute OEM key hierarchy (Matrosov technique: modify IBB, generate new RSA-2048, replace Key Manifest + Boot Policy Manifest, re-lock with attacker-controlled keys, write back via SPI clip).

**SA-00086 / CVE-2017-5707:** ptresearch/IntelTXE-PoC targets Apollo Lake TXE 3.0.1.1107. TXE 3.x has no FPF-backed SVN anti-rollback → SPI write downgrades TXE to vulnerable version → MFS buffer overflow → TXE JTAG via USB DCI.

**Leaked key — `bxt_dbg_priv_key.pem`:** Intel BXT (Broxton/Apollo Lake) OEM platform key leaked via MSI breach + AAEON public GitHub. If GM ships with Intel sample BPM/SMIP keys and FPF unclosed: sign a BPM that passes Boot Guard → Orange debug unlock → full JTAG over USB DCI. This is the single highest-value question to resolve from the IFWI dump.

---

### eMMC ISP — No Chip Removal

**Target:** Samsung KLMCG4JEUD, 153-FBGA (11.5×13mm automotive).

ISP via PCB test points is possible without reballing:
1. Locate vias adjacent to BGA footprint that break out CLK/CMD/DAT0/VCC/VCCQ/GND.
2. Connect ISP programmer to these 6 pins in 1-bit SD mode.
3. Read/write all eMMC partitions including misc/vda9.

**JEDEC Boot Mode:** Hold CMD LOW before RST_n de-assertion → eMMC drives BOOT partition on DAT0 unconditionally — useful for passive verification of eMMC content.

**Samsung vendor commands CMD60/CMD62:** Potential controller firmware/RAM dump path (high effort, Samsung-specific).

**Why eMMC ISP matters:** Direct offline access to misc/vda9 → modify AB0 rollback counter → recalculate CRC32 (poly 0xEDB88320, seed=0xFFFFFFFF per standard, verify against live read first) → reflash → attempt Y177 downgrade. Also enables offline vbmeta + boot partition analysis.

---

### Voltage Glitching — TPS65094 PMIC and misc CRC32

**Target:** Texas Instruments TPS65094 PMIC controls Vcore via I2C (not SVID) on Apollo Lake IVI.

**PMIC undervoltage during GHS CRC32:**
1. Tap I2C bus between SoC and TPS65094.
2. Monitor for misc partition SPI read burst (use logic analyzer on SPI CLK/CS lines as trigger).
3. At the moment the CRC32 comparison instruction executes, inject a crafted BUCK1/BUCK2 DVS command to undershoot Vcore transiently (~100ns).
4. Setup-time violation causes comparison result register to capture incorrect (passing) value.

**RH850 VFI (alternative):** Tap VCL power pins, remove decoupling caps, fast N-FET crowbar. Toyota RAV4 Prime RH850 EPS module was cracked via same technique (icanHack.nl). Enables firmware extraction from production-locked VIP.

**EMFI (EM Fault Injection):** Tool-intensive (Riscure or Langer EMV probe array, ChipWhisperer trigger sync); but works without board modification.

---

### EEPROM I2C Attack Surface

Current status: XGecu direct read/write access to M24C64 already established. These attacks extend capability.

| Attack | Difficulty | Value |
|---|---|---|
| Passive I2C sniff (logic analyzer on SDA/SCL) | Low | Maps exactly which offsets VIP reads at boot — resolves the 0x0A00 mystery |
| Active interposer (dual-bus, transparent proxy) | Medium | Injects modified bytes on read; VIP receives attacker-controlled data; no desoldering of M24C64 |
| Full EEPROM emulation (RP2040 replaces M24C64) | Medium | Pre-loaded with modified image; all flags pre-flipped; USB interface for hot-update |
| Write-blocking interposer (suppress EEPROM writes) | Medium | Prevents VIP from re-asserting lock bytes after session; persistent unlock across reboots |
| 0x0A00 behavioral profiling via byte-mutation | Medium | Systematically mutate 1 byte/session with emulator → map 871-ref data structure without firmware source |

**I2C passive sniff is the most valuable next step on the EEPROM axis** — it directly answers which bytes VIP validates at 0xb67d0 entry (loading from EEPROM→RAM 0x3e06/0x714f) and what the 0x0A00 structure means. *(CORRECTED 2026-08-26: `0xb67d0` is the `$27`/seed validator, not the ADB gate; the SBI's ADB effect is SoC-side MEC/`is_secure_mode` — §0.9/§0.10. The I²C sniff is still the way to see the physical EEPROM read the static passes couldn't locate.)*

---

### RH850 VIP JTAG

**Target:** Renesas RH850/TM52176, QFP-144+, physically accessible.  
**Tool:** Renesas E10A-USB debugger (~$150) + CS+ IDE (free download).

**Attack sequence:**
1. Probe QFP-144 for TCK/TMS/TDI/TDO/TRST pins (consult RH850/TM52176 datasheet).
2. Connect E10A-USB, attempt connection in CS+.
3. If OCD security fuse unblown (expected on most production IVI): full flash read/write, register access, live breakpoints.
4. If OCD fuse blown: attempt VFI (icanHack.nl RAV4 technique) to bypass security sync validation → gain debug access.

**With JTAG access:**
- Dump complete VIP firmware (no indirect Ghidra needed).
- Set hardware breakpoint at `0xb67d0` entry → observe inputs (EEPROM→RAM path, expected values). *(CORRECTED 2026-08-26: `0xb67d0` is the `$27`/seed validator, NOT the ADB gate — ADB is unlocked SoC-side via MEC/`is_secure_mode` (DID 0xF1A0), see EEPROM_LAYOUT §0.9/§0.10. Still useful for the `$27`/seed path.)*
- ~~Patch `0xb67d0` in-place: overwrite 906-byte validator with Y177 4-byte stub~~ — **VOID (2026-08-25):** there is no Y177 stub. The validator is a full ~906-byte function in Y175/Y177/Y181 alike (see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2), so there is nothing to copy in, and the VIP does not set SELinux mode regardless.
- ~~Observe J6_CDD OBBPELK handler live → extract exact ELK trigger format.~~ **ANSWERED (2026-09-10):** VIP disassembly locates the trigger without JTAG — see the "RH850 VIP IPC Injection" entry below. JTAG is no longer required to *find* the format; it remains useful to confirm live signaling and to probe whether an external path can emit it.

~~**This is the highest-leverage single action** — a successful patch of `0xb67d0` achieves permissive SELinux on Y181…~~ **RETRACTED:** the patch-to-stub premise is false (no stub exists) and SELinux mode is not decided on the VIP. JTAG remains useful for *observing* the ADB/seed gate, not for a SELinux bypass. The lever for runtime SELinux is OS-side (ramdisk/init).

---

### RH850 Serial Programming Mode — ID Code Bypass via Voltage Glitching (public precedent, 2026-09-10)

**Distinct from the JTAG vector above** — this targets the RH850's *Serial Programming Mode*
(2-wire UART, enabled via the `FLMD0` pin per the datasheet), not the JTAG/OCD debug port.
Public, detailed, reproduced writeup: Jerin Sunny & Shakir Zari (FEV Secure Lab),
["Renesas RH850 Voltage Glitching"](https://jerinsunny.github.io/blogs/2024/02/14/rh850-voltage-glitching.html),
Apr/May 2024 — a **second, independent, more recent and more detailed public precedent**
alongside the icanHack.nl RAV4 JTOAG-VFI technique already cited above. Same MCU family
(RH850/F1L, sibling to this project's RH850/TM52176), different automotive ECU (a BCM, not
a gatekeeper-CSM VIP), same manufacturer security scheme class.

**What it proved, end to end:**
1. RH850 Serial Programming Mode gates flash read/write behind a **16-byte ID Code**
   sent over the 2-wire UART (protocol: commands start `0x81`/`0x01`, end `0x03` w/
   1-byte checksum preceding it — decoded via logic-analyzer capture of the Renesas
   Flash Programmer (RFP) tool's own traffic, no datasheet secrecy involved).
2. The ID Code Check command is the fault-injection target. Glitch injection point:
   **ISOVCL pin** (the isolated-area voltage regulator rail, which powers flash memory
   specifically — distinct from AWOVCL/always-on rail). Decoupling caps at ISOVCL were
   swapped to raise glitch sensitivity.
3. Tool: **ChipWhisperer Lite** (~$250, cheaper than the $500 already budgeted for
   vector #9 in the priority matrix below — the same unit can serve both). Glitch width
   needed to be **under 100ns**, injected immediately after the ID Code Check command ends.
4. Once the glitch succeeds once, **no further authentication gates subsequent memory-read
   commands** — the whole code+data flash region is dumpable after a single successful bypass
   (multiple glitch attempts were still needed across the full dump because the target
   periodically stopped responding mid-read, not because re-authentication was required).
5. Reverse-engineering the extracted firmware **yielded the secret keys used to unlock
   Secure Diagnostic Services** on that BCM — i.e. this technique's proven end state is
   exactly the kind of key material this project has been unable to capture for `$27`
   (the S84.dll/AES-CMAC master key, see `eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`).

**Applicability to this project's VIP (RH850/TM52176):** unconfirmed but plausible —
same MCU family, same class of serial-programming-mode ID-code gate is documented across
the RH850 line generally (not F1L-specific). Would need: (a) confirming the VIP exposes
`FLMD0`/2-wire UART programming pins (datasheet + PCB probing, same reconnaissance style
as the JTAG vector above), (b) a ChipWhisperer Lite or equivalent, (c) the same
ISOVCL-rail glitch-point identification on TM52176's specific power-supply scheme (may
differ from F1L's). This is a **lower-barrier alternative to the JTAG vector** — serial
programming mode is a standard, datasheet-documented interface (no OCD security-fuse
question to resolve first), and the tool cost is lower than the E10A-USB debugger. Not
yet attempted on this project's hardware.

---

### UART Debug Access

**LPSS UART2** (Apollo Lake debug UART, MMIO base 0x82531000):
- On reference boards: exposed via header pins (115200 8N1).
- Carries: Intel FSP init messages (if debug FSP), GHS INTEGRITY serial console output, Android kernel printk (earlycon).
- On production units: may be unpopulated; probe adjacent pads for 1.8V TX signal at boot.

**GHS INTEGRITY Hypervisor Serial Console:**
- GHS publishes a serial console output partition accessible via UART.
- If UART2 carries GHS console: hypervisor debug output, partition state, task scheduling, IPC traces — all without OS access.

**Kernelflinger `SerialPort` EFI Variable:**
- If fastboot is available (it isn't on this unit): `fastboot oem setvar SerialPort ttyLP2,115200n8` adds `console=ttyLP2,115200n8` to kernel cmdline.
- Since fastboot is blocked: same variable can potentially be written via the NVRAM manipulation path (Section 1).
- **ELK identity, corrected (2026-09-10):** ELK is this same `fastboot`-class Intel Kernelflinger (`kernelflinger-07.02` / `titan_gm_my22`), **not a Linux shell/environment.** It implements `fastboot flash/erase/getvar` plus `oem set-storage`; it explicitly strings `"USB storage is unsupported"` (no external-USB-rootfs boot path). Standard libavb is linked and AVB verification is **active** in ELK. Unlock exists as a code path but is device-state-gated (`"Unlocking device not allowed"` / `"Enable OEM Unlock"`), consistent with "fastboot is blocked" above. GitHub issue #1 (GWMv2 sibling, @DymOK93) documents ELK as a minimal Linux shell with USB-rootfs boot on that sibling platform — that trait does **not** hold on GM; do not carry it over.

---

## Part 2 — GHS INTEGRITY IoT Hypervisor Vectors

### /dev/ghs/* IOCTL Interface

INTEGRITY Multivisor exposes a Linux kernel module in the Android guest that creates the `/dev/ghs/*` namespace. Each node marshals requests across VirtIO or GIPC channels into INTEGRITY native service partitions.

**Nodes of interest (ghs_probe.c targets):**
| Node | Function | Priority |
|---|---|---|
| `/dev/ghs/ota-isys` | OTA broker — owns misc/vda9 rollback counter | **Highest** |
| `/dev/ghs/tee-att` | TEE attestation protocol | High |
| `/dev/ghs/ipc` | General IPC routing | High |
| `/dev/ghs/audit` | Audit log forwarding (format string injection risk) | Medium |
| `/dev/ghs/snapshot-dbg` | Debug snapshot capture | Medium |
| `/dev/trusty-ipc-dev0` | Trusty TEE IPC (10 service names to probe) | Medium |

Current status: DAC is `rw-rw-rw-` on all nodes, but SELinux blocks access from the shell domain. The nodes are reachable from any context with a less restrictive domain.

**ghs_probe.c:** The probe tool is written (research/tools/ghs_probe/) but never built. Build with NDK r25+, deploy as APK with `android.hardware.type.automotive` permission.

**Known ioctl values are guesses** (`_IOR('g', 0x01-0x02, int)`) — need GHS LIP kernel module (`/system/lib64/libghs_lip.so`) RE for real dispatch table.

### /dev/ghs/ota-isys — Direct Rollback Downgrade Path

If `/dev/ghs/ota-isys` is accessible (requires: ghs_probe deployed in a less-restricted domain, or SELinux domain escalation), the OTA broker interface may accept an "OTA rollback" command that instructs GHS to lower the misc/AB0 rollback counter. This is the native interface GM's OTA stack uses for legitimate rollbacks.

**Expected format:** VirtIO or GIPC message; format unknown without GHS LIP kernel module RE. The kernelflinger `celadon/s/mr0/apollo` source (`kf4abl.c`) shows the ABL-side of this protocol.

### IOMMU/VT-d — guest kernel has `intel_iommu=off`; platform/hypervisor VT-d state UNVERIFIED

Correction: the driver is **compiled in** — `CONFIG_INTEL_IOMMU=y` (confirmed: GT enumeration_report.txt:5117), with `CONFIG_INTEL_IOMMU_DEFAULT_ON` **not** set. The guest Linux **boot cmdline** does carry `intel_iommu=off` (confirmed: GT `firmware/.../Y181B/mountables/BOOT_MOUNT_CHAIN.md:62`) — but that token governs **the guest kernel's own** use of the IOMMU, not the GHS hypervisor's platform-level VT-d. Whether GHS leaves platform VT-d disabled such that a device can DMA into **hypervisor** memory is **NOT established** (never captured; the wire→host DMA conclusion is unsupported as measured). GHS may still enforce SMMU/VT-d guest isolation — see US Patent 12,423,197 (GHS INTEGRITY SMMU/GVM model).

**Conditional DMA attack paths (contingent on platform VT-d actually being off — unverified):**
- USB DMA (via USB controller without IOMMU protection) — pair with CVE-2024-53197 LPE
- PCIe device DMA if any external PCIe is accessible

**If** platform VT-d is off, this would be a design-level isolation failure — even without guest kernel compromise, a malicious USB device could DMA-write into GHS memory space. Confirming the platform/hypervisor VT-d state is the prerequisite research question before treating this as a live vector.

### GHS Interpeak/Treck Network Stack CVEs

Green Hills PSA-2020-05 discloses that GHnet v2 (INTEGRITY IoT network stack) is derived from the **Treck TCP/IP stack** — the Ripple20 codebase.

Relevant CVEs if GHS network stack is reachable:
- CVE-2020-11896 (Ripple20 heap overflow, CVSS 10.0, IPv4/UDP tunneling)
- CVE-2019-7714 (IPWEBS HTTP Basic-Auth header parsing stack overflow, CVSS 9.8 — `auth_outbuf`
  fixed 60-byte stack buffer in `t_webserver_basic_auth_check`, no length check on the copied
  `auth_str`; disassembly available, see below)
- CVE-2019-7713 (**correction, 2026-09-10:** IPCOMShell **"prompt <new_prompt>" command** heap
  overflow — not TELNET-specific as previously stated here. The undocumented `prompt` command's
  custom modifiers (`\i`/`\p`/`\P`/`\w`/`\W` — IP, process name, PID, cwd) expand into a
  heap buffer without a bounds check, causing corruption + a process-address info leak)
- CVE-2019-7711 (IPCOMShell **undocumented `prompt` command**, format-string variant — the raw
  prompt value is passed as printf's format string, not just expanded via the modifier bug
  above; info leak via printf format specifiers)
- CVE-2019-7712 (IPCOMShell **`pwd` command handler**, format-string — current directory path
  passed directly as printf's first/format argument)
- CVE-2019-7715 (IPCOMShell **login greeting**, format-string — the `ipcom.shell.greeting`
  sysvar is user-settable via the `sysvar` command and is passed as printf's format string
  at login time, info leak)

All five 2019 CVEs are documented with disassembly (ARM, `t_webserver_basic_auth_check` for
7714) by Tobias Scharnowski and Ali Abbasi (Ruhr University Bochum),
[AlixAbbasi/GHS-Bugs](https://github.com/AlixAbbasi/GHS-Bugs) — found 2026-09-10, more detailed
than the bare NVD entries this doc previously relied on for the CVE-2019-77xx set; use this
source over NVD if re-deriving exploit specifics. Their framing: these bugs are meant to be
chained to **bypass the Interpeak IPShell jail and talk to INTEGRITY natively** — i.e. the
IPCOMShell is treated by GHS as a restricted/jailed shell, and prompt/pwd/greeting are the
escape surface. That framing (a jail *inside* the Interpeak/IPCOMShell partition, separate from
INTEGRITY's own partition boundary) is new information not previously captured in this repo.

**Reachability:** GHS network partition at 192.168.1.1 — `nc 192.168.1.1 <port>` returns "No route to host" from the Android guest network namespace. Accessible only if the GIPC/VirtIO path is bridged, or from a different network namespace. (Same caveat applies to all five CVEs above — they require reaching the Interpeak-based IPWEBS/IPCOMShell services on that partition first.)

### RFDS — CVE-2023-28746 (Intel Goldmont, Apollo Lake listed first)

Register File Data Sampling affects Intel Atom Goldmont (06_5CH = Apollo Lake die — listed first in affected processor table). This is a cross-hypervisor-domain leakage bug:
- Hypervisor-level data (stale register file contents) can be sampled by the Android guest via `RDMSR` and similar paths.
- Could leak GHS partition secrets (session keys, IPC routing state, hypervisor internal addresses) across the VM boundary.
- Exploit requires: ability to execute RDMSR (checked), cache priming, timing measurement.

### Shared Memory TOCTOU

GHS INTEGRITY configures static MemoryRegion objects shared between Android guest and INTEGRITY native partitions. TOCTOU attacks on these shared windows:
- Guest writes valid data, GHS reads it for validation
- Between validation-read and use-read, guest modifies data
- Requires: precise timing or a memory region where the window is wide (large batch operations)

### VIP RH850 IPC Injection (Software Path)

From Android guest, the VIP IPC channel (`SERIAL_IPC_PROTO_KEY_CHANNEL`) is the software path to the RH850. Replaying or crafting messages on this channel (mercedes-MBUX TCP-over-IPC pattern) may trigger RH850 actions without physical JTAG.

**J6_CDD "Diag Elk Reboot Req" — TRIGGER LOCATED (2026-09-10), fresh VIP RH850 + GHS INTEGRITY disassembly, HIGH confidence.** The VIP executes an ELK/reboot on an **unauthenticated** internal serial-IPC message on `SERIAL_IPC_CONTROL_CHANNEL` ("Channel-7"): `RID=0xFF01` (big-endian) + `subcommand=0x01`, handled by VIP function `FUN_000641c2` @0x64208. **No `$27`/session/dev-mode/EEPROM gate exists at the VIP for this command** — whatever authorizes the ELK happens (or doesn't) upstream of the VIP. The VIP only *receives* 0xFF01; the SoC is the emitter. Separately, on the SoC side, GHS INTEGRITY Lifecycle emits `BootELKSendAblUserCommand` over Intel HECI to CSE/ABL for boot-target selection — this is the ABL/fastboot-facing half of the chain, distinct from the VIP's Channel-7 handler. GM does **not** use GWM's UDS DID `0xFDF0` for this (see GORDON_PEAK_CELADON_INTELLIGENCE.md, GitHub issue #1 GWMv2 sibling, @DymOK93, for the DID GM does not share).

**OPEN (under active investigation, 2026-09-10):** whether an *external* DoIP/MDI2 tester, or the uid-2000 Android guest, can make the SoC emit the Channel-7 0xFF01 command — a `$31` RoutineControl bridge analogous to the documented GM ADB hatch (`31 01 0332 DD 42 10 EE`). No artifact so far answers this; do not assume it is reachable. RH850 JTAG (vector below) would settle it by observing live signaling on the channel during a real ELK cycle.

---

## Part 3 — Attack Vector Priority Matrix

| Rank | Vector | Type | Effort | Impact |
|---|---|---|---|---|
| 1 | ~~RH850 JTAG → patch `0xb67d0`~~ **VOID** | Hardware | — | No stub exists in any build; VIP does not set SELinux (corrected 2026-08-25). JTAG still useful to *observe* the ADB/seed gate |
| 1b | RH850 Serial Programming Mode ID Code bypass via ISOVCL voltage glitching (public precedent, FEV Secure Lab 2024) | Hardware/VFI | Medium (ChipWhisperer Lite ~$250) | Full flash dump + proven key extraction on a sibling RH850/F1L BCM; unconfirmed on TM52176 |
| 2 | CVE-2024-53197/53104 → misc write | Software/USB | Medium (USB gadget) | Online misc write path |
| 3 | SPI IFWI dump → Boot Guard FPF audit | Hardware | Low (SOIC-8 clip) | Determines if `bxt_dbg_priv_key.pem` works |
| 4 | DCI DbC (if HDCIEN already enabled) | Hardware | Low ($15 cable) | Full JTAG, game over |
| 5 | CVE-2021-0146 Red Unlock + DCI | Hardware/VFI | Medium | Full JTAG via fault injection |
| 6 | eMMC ISP → misc/AB0 write | Hardware | Medium (test points) | Offline rollback counter edit |
| 7 | I2C passive sniff (boot capture) | Hardware | Low (logic analyzer) | Maps 0x0A00 structure + `0xb67d0` inputs |
| 8 | ghs_probe + /dev/ghs/ota-isys | Software | Medium (NDK build) | Potential native rollback downgrade |
| 9 | PMIC I2C undervoltage glitch | Hardware/VFI | High (FPGA + timing) | CRC32 comparison bypass |
| 10 | UART2 tap → GHS console | Hardware | Low | GHS debug output, no exploitation |

---

## Part 4 — Required Tools Not Yet Acquired

| Tool | Purpose | Approx cost | Priority |
|---|---|---|---|
| Renesas E10A-USB | RH850 JTAG (vector #1) | ~$150 | **Critical** |
| SOIC-8 clip + 1.8V adapter | SPI IFWI dump (vector #3) | ~$30 | **Critical** |
| USB-A to USB-A cable (VBUS cut) | DCI DbC test (vector #4) | ~$15 | High |
| Logic analyzer (16ch) | I2C sniff, SPI trigger, UART | ~$30 (Saleae clone) | High |
| ChipWhisperer Lite (or equiv) | VFI trigger sync; also serves vector #1b (RH850 ISOVCL glitch) | ~$250-500 | Medium-High (now dual-purpose) |
| FPGA (Spartan-7 or equiv) | PMIC I2C interposer, TOCTOU | ~$100 | Low |
