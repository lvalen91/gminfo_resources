# T1/Ethernet Inward Attack Surface + EEPROM↔Calibration Convergence

**Date:** 2026-08-17
**Unit:** gminfo37 / 2024 Silverado ICE / build W231E-Y181.3.2 / Android 12L (API 32)
**Method:** three parallel firmware/enumeration analyses (read-only) reconciled against the
existing `research/`, `eeprom/`, and `enumeration/Y181/apr2026/` corpus; plus integration of the
owner's physical M24C64 EEPROM-modification capability.
**Confidence markers:** `[C]` confirmed from a measured dump/binary, `[I]` inferred, `[O]` open/testable.

This document answers one focused question — *can T1/automotive-Ethernet access at the radio's pins
expose the hypervisor, allow custom calibration ON the radio, or enable escalation ON the radio itself*
— and then integrates it with the EEPROM lever the owner already holds. It supersedes the older
"192.168.1.1 = GHS hypervisor bridge" framing (see §5).

> **PROVENANCE CORRECTION (2026-08-17, post-audit).** A skeptical provenance audit against the
> on-disk ground-truth artifacts caught three overstated `[C]` claims in this doc's speculative
> hypervisor-wire section; they are corrected inline below and flagged `⚠CORRECTED`. Net effect: the
> "crafted-frame/DMA → hypervisor" wire→host vector is **weaker than first stated** (its IOMMU-off
> premise is unverified) — but none of the calibration/EEPROM/`$27` conclusions (§3b, §4) are
> affected; those were independently ground-truth-verified. Ledger: `scratchpad/provenance_audit.md`.

---

## 1. Interface / VLAN map (corrects the earlier eth0/br0 seed)

- `[C]` **`br0` is DOWN with no IP** in the captured dumps (`raw/ip_addr.txt`,
  `raw/network_interfaces.txt`); its bring-up services (`brctl_add`, `setip`) are stopped. The old
  "br0: 192.168.5.1/24" seed is stale — br0 is the Android Wi-Fi-hotspot bridge, inactive at capture.
- `[C]` The real IVI stack is **`eth0` (driver `igb_avb`, MAC `02:04:00:00:01:00`)** — the physical
  100BASE-T1 uplink — carrying two 802.1Q VLANs:
  | Iface | Subnet | Role |
  |---|---|---|
  | `eth0` | 192.168.1.100/24 (untagged) | physical T1 MAC; also L2 gPTP/AVB |
  | `vlan5@eth0` | 192.168.1.100/24 | GM "service network" (inter-ECU, SOME/IP, diag peers) |
  | `vlan4@eth0` | 172.16.4.100/24 | internal vehicle/telematics/AVB network |
- `[C]` On-board **Marvell 88Q5050** automotive-Ethernet switch (`vendor/etc/ethmvlctrl_globalB.cfg`),
  driven by `ethmvlctrlmgr`. It **enforces per-port VLAN membership** — an external T1 tap only reaches
  the VLAN(s) assigned to the physical port it lands on.
- `[C]` T1 peers seen (`network_scan.txt`, `raw/arp_table.txt`): a **gateway/router ECU at
  192.168.1.102 (= 172.16.4.1)** running `dnsmasq` + SOME/IP-SD (UDP 30490); other ECUs at .106/.112;
  a dual-homed telematics/TCU (only real-OUI MAC, `10:66:50:0c:ed:d3`). The IVI is one switched node.

---

## 2. Listener table (measured — `raw/open_ports.txt`)

| Port/proto | Bind | Owner / layer | External-T1 reachable? | Auth gate |
|---|---|---|---|---|
| TCP 49156 | `0.0.0.0` | **`diagnosticsd`** GM-custom UDS-over-TCP (see §3, attribution caveat) | **Yes** from an on-vlan5 port | app-layer source-address tier + **UDS SecurityAccess `$27`** |
| TCP 6363 | `0.0.0.0` | NFD (Named-Data-Networking fwd), Android guest | **Yes** | none observed |
| UDP 5353 | multicast | `mdnsd` | on-link only | none |
| TCP 9002/9005/9010/9012/9016/9018 | `::ffff:192.168.1.1` | GHS↔Android paravirtual IPC | **No** — hypervisor virtual IP; even the local guest shell gets *"No route to host"* | internal transport |
| UDP 30490 (SOME/IP-SD) | — | on gateway **.102**, not IVI | IVI is a client | out of scope |
| TCP 13400 (standard DoIP) | — | **not present on IVI** | — | — |

- `[C]` **No perimeter firewall** in vendor init (`init.full_gminfo37_gb.rc`, `init.bxtp_gm.rc` have no
  INPUT/DROP; `netd` runs stock bandwidth chains only) — so the two `0.0.0.0` listeners are genuinely
  wire-reachable from an on-VLAN tap.
- `[C]` It is **GM-custom UDS-over-TCP on 49156**, *not* standard DoIP — no `13400`, no
  vehicle-announcement / routing-activation. Framing: `[SRC:2 BE][TGT:2 BE][LEN:4 BE][UDS payload]`,
  target address unvalidated, app-layer source-address trust tiers (`0x00FA` factory tester, `0x00F1`,
  `0xF0`) with `generalReject (0x10)` for untrusted sources.
- `[C]` ADB-over-TCP is a capability (`on property:vendor.adb.tcp.enable=1 → restart adbd`) but **off**
  (`ro.debuggable=0`, `ro.adb.secure=1`, `sys.oem_unlock_allowed=0`, AVB locked/green).

---

## 3. Three-part verdict for the owner's question

### (a) Hypervisor from a T1 tap — **NO service; one hypothesized wire→host vector**
- `[C]` GHS owns the physical NIC (its binary carries the Intel `i8254x` driver + `gm_eth_passthru`) and
  passes it through to Android. **⚠CORRECTED:** the guest drives `eth0` with **`igb_avb`** (Intel
  I210-class AVB MAC), **not `e1000e`** as first written — `network_interfaces.txt`/`kernel_modules.txt`
  show `igb_avb` loaded and no `e1000e`. The passthrough thesis stands (the guest drives a real Intel MAC
  directly), only the driver name was wrong. Every wire-reachable listener terminates in the **Android
  guest** (least-privileged layer). Inter-partition IPC is non-IP / off-wire (`/dev/ghs/*`, Trusty
  virtio, INTEGRITY connections).
- `[C]` A real VLAN5 scan found only the Android IVI (.100) + separate physical ECUs — **no
  hypervisor-owned port on the wire.** The GHS IPC ports (9002/9016) bind the internal virtual IP and are
  unreachable even locally.
- `[I]`facts / `[I]`exploit — **⚠CORRECTED — the hypothesized wire→host vector, now weaker:** the earlier
  `[C]` claim that **IOMMU/VT-d is OFF (`intel_iommu=off`) is UNVERIFIED** — `/proc/cmdline` was never
  captured (permission-denied), and the only IOMMU artifact, `kernel_config.txt`, shows
  **`CONFIG_INTEL_IOMMU=y` (compiled IN)**; runtime enable-state is unknown. So the premise for a
  "crafted-frame/DMA → hypervisor" bug (GHS driving the NIC with no DMA isolation) is **not established**.
  IF IOMMU were runtime-disabled, a memory-safety bug in the NIC-passthru path tripped by crafted frames/
  DMA would be a hypervisor-layer bug reachable from T1 — but that is now doubly speculative (unverified
  premise + unproven bug). Treat as a research question, not a known vector. **To settle:** capture
  `/proc/cmdline` (needs root) or check the IOMMU state via `dmesg | grep -i iommu`.
- `[I]` Dormant host network code exists in the GHS binary (**GHnet/Treck** TCP/IP — the Ripple20 CVE
  codebase — and the **INDRT** Ethernet debugger) but nothing is shown bound/active; INDRT needs a debug
  build.
- **Reaching the hypervisor otherwise requires:** an Android-kernel LPE → drive `/dev/ghs/*` IPC
  (guest→host crossing, *not* network), or a hardware attack (RH850 JTAG/SPI, Intel DCI / CVE-2021-0146).

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
  — the same sandbox a sideloaded app already has; reaching `/dev/ghs/*` or Trusty from there still needs a
  separate kernel LPE (`untrusted_app` is `neverallow`'d `tipc_socket`).

**Bottom line:** the higher-value diagnostic/calibration surface is on the **CAN/VIP side**, not Ethernet.
From a T1 tap the radio exposes, at most, two Android-guest TCP daemons (6363, 49156) — a guest-level
surface. Calibration writes are reachable in *form* on 49156 but gated by `$27`; the wall isn't "no path,"
it's specifically the `$27` seed/key algorithm, anchored in the VIP/PROTOKEY/EEPROM.

---

## 4. EEPROM ↔ calibration-`$27` convergence (the owner's lever)

The owner physically modifies the **ST M24C64 I²C EEPROM** that sits next to the **Renesas RH850 VIP MCU**
(documented in `eeprom/EEPROM_Analysis_Report.md`, `eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md`). The
relevant facts, and the new integration:

- `[C]` **"adb flip 0xFF" = the SBI bypass.** Setting the data byte of the Seed-Bypass-Indicator flags —
  `0x0441` (Primary SBI) and `0x0A81` (Backup SBI) — to **`0xFF`** makes the VIP return an **all-`0xFF`
  seed** instead of the real ECUID+Challenge, so the **PROTOKEY / ICUSB module skips BCM authentication**
  → the traditional (limited, non-GM-cert) ADB the owner uses. Marker/frame bytes are CalGroup-assigned at
  runtime and are **not** checked by the validation at `0xb67d0` — only the data byte matters (bypass is
  marker-agnostic). OTA/SPS resets these to locked; must be re-applied.
- **The key integration this session establishes:** the **same VIP/PROTOKEY subsystem, reading the same
  M24C64**, anchors **both** (i) the ADB PROTOKEY auth the SBI flip defeats **and** (ii) the calibration
  `$27` SecurityAccess that gates a `SCREEN_RESOLUTION` write (§3b). Per
  `CALDEF_VIP_CALIBRATION_ANALYSIS.txt`, cal-programming security access is validated by VIP firmware
  reading **PROTOKEY + EEPROM flags**. So the EEPROM the owner can already write is a **demonstrated lever
  over VIP security state** — the exact layer the calibration gate lives in.
- `[O]` **What is NOT yet proven (do not overclaim):** flipping the *ADB* SBI (`0x0441/0x0A81`) is **not
  shown** to also open the *calibration* `$27` gate — they share a subsystem and an anchor, not a proven
  single flag. The open, testable question is whether a **different** EEPROM flag governs the diagnostic/
  calibration security level the way `0x0440` governs ADB. The undocumented-flag candidates already
  flagged in the security region are the first place to look:
  - ~~`0x04A0` (17 refs) / `0x04C0` (11 refs) — near `[IPC_S]` (VIP↔SoC secure IPC) strings.~~ **RETRACTED 2026-08-26:** the ref-counts are fabricated and `[IPC_S]` = serial-transport (HDLC) log tag, NOT "secure IPC"; these are not security flags (see EEPROM_LAYOUT §0).
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
   candidates `0x04A0`, `0x04C0`, `0x0A40`, `0x0BE0` (RETRACTED 2026-08-26 — no code evidence; do not test these. Real SBI = `0x0441`+`0x0A80`). Formerly the crux for a
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
