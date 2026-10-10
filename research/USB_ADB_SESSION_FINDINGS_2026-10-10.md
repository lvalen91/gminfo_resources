# gminfo37 (Silverado CSM) — USB hardware & ADB logic, from direct firmware analysis

**Rule for this document:** every claim carries a direct, confirmed reference. Tags:
- **[FW …]** — byte/line in an extracted firmware file (file + offset or line).
- **[DIS vaddr]** — instruction traced by disassembly in the decompressed kernel.
- **[LIVE file:line]** — a value read from a live radio and captured in the repo enumeration dumps.
- **[HW doc]** — physical/connector fact from the hardware references (not firmware; marked as such).
- **[CONFIRMED ×N]** — independently reproduced by N FABLE verification agents this session.
- **[UNVERIFIED]** — not established; stated as open, never as fact.

## 0. Sources (what was opened, and how)
Y181B GAS USB Full Package, PN 86405303 — `delivery_manifest.csv` [FW USB_Files/delivery_manifest.csv].
Path: `…/2024_Silverado_ICE/firmware/update_packages/Y181B/USB_Files/`.

| Module | PN | sha256 (head) | Contents | Read by |
|---|---|---|---|---|
| SOC_VENDOR | `86331650` | `bff351f9…` | zip → ext4 `/vendor` (466,915,328 B) | `debugfs` dumps |
| SOC_BOOT | `86331652` | `792f66f0…` | Android bootimg → kernel 4.19.305 | `unpack_bootimg`, lz4, r2 |
| SOC_HOSTOS | `85098662` | `317ae85c…` | GHS INTEGRITY OS+hypervisor (one ELF) | ELF/symtab parse, r2 |
| (live) Y175/Y181 | — | — | `all_properties.txt` property dumps | repo `enumeration/` |

Kernel identity: `Linux version 4.19.305-240125T145315Z-gf1edde901aa7 … Tue Jul 22 07:52:16 EDT 2025`
[FW 86331652 vmlinux @0x15ffff0 banner; CONFIRMED ×1]. Boot cmdline sets
`androidboot.hardware=full_gminfo37_gb` and ends `enforcing=1 androidboot.selinux=enforcing
buildvariant=user` [FW 86331652 bootimg cmdline].

---

## 1. Hardware layer — the X8 connector (physical; HW-doc sourced)
These are connector/pinout facts, not firmware. Cited to the hardware references, marked [HW doc].

- The radio's rear USB is **X8**, a 12-way HSAL-2 (BK) header, OEM `13545174`; board silkscreen
  `USB2.0` [HW doc connectors.md §USB / teardown.md].
- Only the bottom row (6 of 12 cavities) is wired in any known cable; of that, USB uses **4 pins —
  VBUS/D+/D−/GND**. **No CC and no OTG-ID conductor reaches the radio** [HW doc connectors.md §"6-contact
  silkscreen"]. Consequence used throughout: *the radio cannot electrically sense cable orientation,
  role, or a CC resistor.* The only cues reaching the radio over X8 are VBUS (5 V) and the D± pair.
- Bench cable = GM Molex `87813526` (HSAutoLink → Male Mini-A) [HW doc connectors.md].

> Everything below (§2–§7) is the **firmware logic** that runs behind that 4-wire port.

---

## 2. The physical USB controllers
Two Intel/Broxton PCI USB controllers exist on the SoC; both are claimed by firmware by PCI ID:

- **XDCI** (device/gadget-capable dual-role controller) = PCI `8086:5AAA`. Traced in GHS as the match
  predicate `cmp dword [rsi+4], 0x5aaa8086` in `xdci_driver_match` [DIS 85098662 @0x23d6e9;
  CONFIRMED ×2]. In Android this is the platform device **`dwc3.0.auto`** (Synopsys DesignWare)
  [FW 86331650 init.bxtp_gm.rc:787; LIVE referenced below].
- **xHCI** (host controller) = PCI `8086:5AA8`. Match `cmp …,0x5aa88086` [DIS 85098662; CONFIRMED ×2].

The guest ACPI DSDT that GHS hands Android names the XDCI explicitly: `IGS_DSDT` declares
`\_SB.PCI0.XDCI`, `_ADR 0x00150001`, `_DDN "Broxton XDCI controller"` [FW 85098662 @~0xd1bfa8;
CONFIRMED ×2].

---

## 3. GHS (INTEGRITY) layer — passthrough only, no USB role logic
**Verdict: GHS contains no role-switch / gadget / dabridge / hub logic. It performs a MEDIATED
(para-virtual) passthrough of both USB controllers to the Android guest.** Four agents converge; the
full edge-to-edge byte map is in `GHS_FILE_MAP_85098662.md`.

**[REFINED] It is mediated passthrough, not raw assignment.** The monitor (`.vmm1`) claims the real
PCI functions (`cmp esi,0x5aa88086` xHCI / `cmp esi,0x5aaa8086` xDCI [DIS 85098662 @file 0xcf205b /
0xcf2184]) and exposes an **emulated PCI function** to the guest (`usb_passthru_emul.c`: virtual config
space + BAR0 + MSI); the guest's register accesses are trapped and forwarded as RPC verbs
`UsbRdReg`/`UsbWrReg`/`UsbPoll`/`UsbIrq` which the monitor runs against the real controller
(`system_usb_passthru.c`) [FW 85098662 .vmm1; CONFIRMED ×1, region D]. Net effect to Android is the
same (it drives a real-backed xHCI/xDCI), but GHS sits in the register path.

- Whole-blob token sweep (ASCII+UTF-16): **0** hits for `dabridge`, `dabr_udc`, `bridgeport`,
  `usb_otg_switch`, `intel_xhci_usb_sw`, `role-switch`, `usb_role`, `cbc-signals`, `dwc3`,
  `mux_state`, `gadget` [FW 85098662; CONFIRMED ×3].
- GHS's USB code is passthrough plumbing only: `XhcIOA_*` (I/O agent), `XhcVc_*` (virtual-controller
  sharing), `Usb_GrabEHCI`, and the `vmm1` passthrough path with sources
  `libpassthrudev/xdci_passthru`, `usb_onboard_vm.c`, `virtualization/src/sls/pc_emul/…/usb_passthru_emul.c`
  [FW 85098662 symtab/.vmm1.rodata; CONFIRMED ×2].
- The `.boottable` assigns **both** controllers to Guest 1: `Guest1_XHCI0`, `Guest1_XDCI`
  [FW 85098662 @~0xe34a1f; CONFIRMED ×2]. So Android owns the real xHCI and the real XDCI.
- **No hidden code.** Exhaustive compression-magic scan + ~1,000 brute decompression attempts across
  the blob and every high-entropy window → **0 compressed/encrypted streams** [FW 85098662;
  CONFIRMED ×2]. Every high-entropy region is identified data (see §8). **[CORRECTED]** the only bytes
  whose content could not be read are **768 B** at the tail — a 256 B RSA-2048-sized Android key
  (`current_android_key`, exposed to Guest1 via `AndroidKeyVMR`) + a 512 B RSA-4096-sized signature
  [FW 85098662 @0xE3CCB0 / 0xE3CE20; region D]. The earlier "~13 KB" figure wrongly counted the TEE
  blocks, which region D identified as **standard AES T-tables (Te0–3/Td0–3) + SHA-256/512 constants**
  — not opaque, not secret.

**Meaning:** GHS does not decide host vs device and does not bridge ports. It exposes the XDCI to
Android through the `OTGD` ACPI OpRegion (§4), and the role decision happens in the Android guest.

---

## 4. Role-switch logic — software, reaching hardware via ACPI (no CC pin)
The host↔device decision is made in software and applied through the XDCI's ACPI OpRegion — which is
exactly why no CC conductor is needed on X8.

1. Trigger is the property **`vendor.sys.usb.role`** [FW 86331650 init.bxtp_gm.rc:952-956]:
   ```
   on property:vendor.sys.usb.role=host    → exec … /vendor/bin/usb_otg_switch.sh h
   on property:vendor.sys.usb.role=device  → exec … /vendor/bin/usb_otg_switch.sh p
   ```
2. The script writes the role-switch node (the 4.19 branch is the live one — kernel is 4.19.305):
   [FW 86331650 /vendor/bin/usb_otg_switch.sh, inode 312, 940 B, sha256 `a916e26a…`; CONFIRMED ×2]
   ```sh
   if [[ $1 = "h" ]]; then echo -n -e "\x01\x3c\x4e\x1" > /dev/cbc-signals
     …  *) echo "host"   > /sys/class/usb_role/intel_xhci_usb_sw-role-switch/role ;;
   elif [[ $1 = "p" ]]; then echo -n -e "\x01\x3c\x4e\x0" > /dev/cbc-signals
     …  *) echo "device" > /sys/class/usb_role/intel_xhci_usb_sw-role-switch/role ;;
   ```
   - The 4-byte write to `/dev/cbc-signals` is a **CAN notification** (`01 3C 4E 01`=host /
     `01 3C 4E 00`=device). It informs other ECUs; it is **not** what flips the controller.
   - The role flip is the write to **`intel_xhci_usb_sw-role-switch/role`**. The driver backing that
     node is built in: `intel-xhci-usb-role-switch.ko` + `roles.ko` [FW 86331650 modules.builtin:618-619].
3. That role-switch driver reaches hardware through the XDCI ACPI OpRegion **`OTGD`** declared in the
   GHS-supplied `IGS_DSDT` (XDCI `_ADR 0x00150001` = PCI dev 0x15 fn 1 = the dual-role `dwc3.0.auto`;
   fields `DVID/XDCB/D0I3/PMEE/PMES`, `_DSM`) [FW decoded `dsdt_a.dsl:1290-1500`; CONFIRMED ×2].
   The `_DSM`'s **`SPPS`** ("set port power state") method maps the controller MMIO (`XDBA()`) and
   **software-commands port power + connect**: writes `PUPS` (port power up/down), `UXPE` (expose/enable),
   reads `U2CP/U3CP` (USB2/USB3 connect state) with `Stall(0x64)` spin loops. **So the XDCI's VBUS
   sourcing and role are a register/ACPI decision, not sensed from any pin** — which is exactly why the
   4-wire X8 (no ID/CC) is sufficient.
4. Boot default is **host**: `on boot … setprop vendor.sys.usb.role host` [FW 86331650
   init.full_gminfo37_gb.rc:95-101] → the driver `SPPS`-powers the XDCI port → sources VBUS (this is
   what powers the in-vehicle receptacle hubs at boot).

**What actually triggers ADB (RESOLVED, owner-confirmed 2026-10-10):** the **Developer-Options
USB-debugging toggle**. Observed on the GM-brand bench: with ADB **off**, the Mac's VBUS is present
and **nothing enumerates**; flipping the software toggle makes **ADB appear**. This (a) confirms the
trigger is **software** (GM's ADB-enable path → role device → `SPPS` reconfigures to peripheral →
gadget D+ pull-up), and (b) **RULES OUT** hardware VBUS-sense auto-role (VBUS alone did nothing). It
is **not** the `brand=Android` GSI rule — that rule exists [FW init.full_gminfo37_gb.rc] but does not
fire on a stock GM image; the bench is GM AAOS.

**CC correction (withdrawn claim):** any statement that "the radio watches CC" is false — CC never
reaches the radio (§1). The CC `Rd` resistor on a bench breakout only makes the **Mac** become host
and source VBUS; the radio's role/port-power is **software-commanded** via the path above. [HW doc + FW §4]

**VBUS clash — benign (owner-confirmed + electrical).** At boot the radio (host) `SPPS`-sources VBUS
and the Mac (host, via its CC `Rd`) also sources ~5 V. Two equal ~5 V rails with nothing enumerating/
loading is **not a short** (a short is 5 V→GND) — it is a low-energy, current-limited coexistence, and
the bench shows it does nothing. When the toggle flips the XDCI to **device**, `SPPS` removes the
radio's port power → the radio stops sourcing, sinks the Mac's VBUS, asserts D+, and the Mac
enumerates it. So the dual-source window is momentary and harmless.

---

## 5. Gadget / ADB logic — configfs, functions, UDC bind, VID/PID
Once the controller is in **device** role, Android brings up a USB gadget via configfs. This is the
machinery that actually exposes ADB on the wire. All [FW 86331650 init.bxtp_gm.rc; CONFIRMED ×2]:

- configfs is enabled and functions created [757-787]: `ffs.adb`, `ffs.mtp`, `ffs.ptp`; FunctionFS
  for adb mounted at `/dev/usb-ffs/adb` [783-786]; default controller set:
  `setprop sys.usb.controller dwc3.0.auto` [787].
- Per-config the gadget's identity + functions are written, then bound to a UDC
  `write /config/usb_gadget/g1/UDC ${sys.usb.controller}` [867]. `adbd` starts on the adb configs
  [840-856].
- **VID/PID table (line-verified):**

  | config | line | idVendor | idProduct |
  |---|---|---|---|
  | mtp / mtp,adb | 805-813 | `0x8087` | `0x0a5e` / `0x0a5f` |
  | rndis / rndis,adb | 818-823 | `0x8087` | `0x0a62` / `0x0a63` |
  | ptp / ptp,adb | 828-836 | `0x8087` | `0x0a60` / `0x0a61` |
  | **adb** | 841-842 | `0x8087` | **`0x09ef`** |
  | midi / midi,adb | 848-853 | `0x8087` | `0x0a65` / `0x0a67` |
  | adb,dvctrace | 857-858 | `0x8087` | `0x0a1f` |
  | accessory / accessory,adb | 871-876 | **`0x18d1`** | `0x2d00` / `0x2d01` |
  | audio_source (+accessory/adb) | 879-892 | **`0x18d1`** | `0x2d02`–`0x2d05` |

  So **VID is `0x8087` (Intel) for the data/debug configs and `0x18d1` (Google) for the AOA/
  audio_source configs** — not a single constant. ADB config = **`8087:09ef`**, matching the live
  bench capture [HW doc connectors.md §fastbootd; FW 86331650:841-842; CONFIRMED ×2].

---

## 6. DABridge — the virtual UDC, and the two device-mode paths
`dabridge` is a separate kernel driver that supplies a **virtual** UDC so a USB **host** port can keep
running while a gadget (e.g. ADB/NCM) is exposed — this is what lets in-vehicle hubs/accessories stay
live during ADB.

- Driver compiled into the kernel: `.rodata` source paths `drivers/usb/gadget/udc/dabridge.c`
  [FW 86331652 vmlinux @0x1fe070a] and `dabr_udc.c` [@0x1fe02c8], symbols `dabridge_port_role_reverse`
  [@0x1fe06ef], `dabr_udc_pullup` [@0x1fe0b85], `dabridge_probe` [@0x1fe0957], `bridgeport`
  [@0x1fe05a3]; also present in `modules.builtin` [FW 86331650 line 606]; CONFIRMED ×2.
- Real runtime code (not init-only): the role-switch wait returns `-110 (-ETIMEDOUT)` —
  `mov rsi, <"Timeout waiting for role-switch">; call printk; mov eax,0xffffff92; ret`
  [DIS 86331652 vmlinux @0xffffffff81a91294; in `.text`; CONFIRMED ×1]. A second site references
  "No dabridge_request corresponding to urb was found" [DIS @0xffffffff81a61b81].
- `dabr_udc.0` is a **distinct** platform device from `dwc3.0.auto` (own sepolicy context
  `sysfs_dabr_udc`, genfscon `/devices/platform/dabr_udc.0/gadget/net`) [FW 86331650 sepolicy;
  CONFIRMED ×1].

**Two paths (two UDCs)** [FW 86331650 init.full_gminfo37_gb.rc; CONFIRMED ×1]. The paths are defined by
*mechanism*, not by brand (see the brand caveat below):
- **Path A — virtual UDC via dabridge (in-vehicle).** On `sys.usb.ffs.ready=1 && sys.usb.config=adb`,
  init performs the bridge (comment: *"needs to perform rolereversal and gadget binding"*):
  `write …/dabridge/bridgeport ${sys.dabridge.host.portnum}` then `${sys.dabridge.dev.portnum}`
  [:106-110]. The xHCI host + receptacle hubs stay enumerated; ADB rides the bridged virtual UDC.
- **Path B — raw `dwc3.0.auto` gadget (bench direct line).** The physical XDCI flips host→device, no
  hub, no bridge.

**Brand caveat — do not equate Path B with "GSI".** There *is* an init rule
`on sys.boot_completed=1 && ro.product.system.brand=Android → setprop sys.usb.config adb +
vendor.sys.usb.role device` [FW init.full_gminfo37_gb.rc], but that rule **only fires on an
Android-brand/GSI image and does NOT fire on the stock GM AAOS bench.** On the GM bench, Path B's
device role is entered by the **Developer-Options USB-debugging toggle** (§4), not this rule. So
Path B = the raw-dwc3 mechanism; the `brand=Android` rule is just *one* (non-bench) way to reach it.

**Live override (both units):** the vendor configfs default is `dwc3.0.auto`, but running radios
report the active controller as **`dabr_udc.0`** [LIVE Y175 all_properties.txt:482;
LIVE Y181 all_properties.txt:510; CONFIRMED ×1]. The bridged ports differ by build:

| build | `sys.dabridge.host.portnum` | `sys.dabridge.dev.portnum` | ref |
|---|---|---|---|
| Y175 | `1-12.0` | `1-12.3` | [LIVE Y175 all_properties.txt:466-467] |
| Y181 | `1-6.0` | `1-6.3` | [LIVE Y181 all_properties.txt:494-495] |

[CONFIRMED ×2; exact property names, no aliasing.]

---

## 6.1 How ONE USB-2.0 link drives two daisy-chained hubs *and* exposes ADB at once
This is the architectural crux. It splits into two independent facts — one is plain USB, the other is
the dabridge trick — and they do not conflict because they happen on different logical entities.

**(a) The daisy chain is ordinary USB — the radio is the single host/root.**
A single USB host port fans out through standard USB hubs; cascading a second hub onto a downstream
port is textbook USB, not a GM invention. The firmware shows the host tree directly: the SoC USB host
root is `usb1` with an on-board hub at **`1-1`** and downstream ports `1-1.3`, `1-1.5`, … under PCI
`0000:00:15.0` [FW sepolicy product_sepolicy.cil:4-8; CONFIRMED ×1]. The two receptacle assemblies are
themselves USB hubs chained into that tree. Every accessory (USB stick, CarPlay/AA phone, charge port)
enumerates as a **device below the radio**, because in this direction the radio is the **host**. One
host port therefore "drives" an arbitrary hub/device tree by definition of USB — no special logic, no
per-port controller.

**(b) ADB coexists because it is a VIRTUAL device overlaid on one port — the physical host never flips.**
The problem ADB poses: to talk ADB to an external host, the radio must look like a *device*, yet the
same physical link is already a *host* for the hub tree. GM resolves this with `dabridge`, not by
flipping the port:
- `dabridge` registers a **virtual UDC `dabr_udc.0`** — a separate platform device from the physical
  `dwc3.0.auto` [FW 86331652 vmlinux `.rodata` dabr_udc.c @0x1fe02c8; FW 86331650 sepolicy genfscon
  `/devices/platform/dabr_udc.0/gadget/net`; CONFIRMED ×1]. It is also a USB **host-side driver** that
  binds to the H2H bridge device by VID/PID (id_table `2996:0100–0105`, see §6.1c) — so Path A needs
  that recognized device present; Path B (raw `dwc3.0.auto`) does not.
- It bridges a chosen **host-side** port to a **device-side** port by writing
  `host.portnum` then `dev.portnum` to `/sys/bus/usb/drivers/dabridge/bridgeport`
  [FW 86331650 init.full_gminfo37_gb.rc:106-110; FW sepolicy product_sepolicy.cil:10; CONFIRMED ×2].
  The init comment names it exactly: *"needs to perform rolereversal and gadget binding."*
- Net effect: the **physical host controller stays in host mode** (so `1-1` and every other downstream
  port keep serving accessories), while on **one** bridged branch the radio presents a USB **gadget**
  (ADB — and the same path carries CarPlay/AA) to whatever host is on that receptacle. Host tree and
  device endpoint run simultaneously because they are different logical nodes, not two states of one
  port.
- The actual bridged ports, live: Y181 **`1-6.0`(host) → `1-6.3`(dev)**, Y175 **`1-12.0` → `1-12.3`**
  [LIVE Y181/Y175 all_properties.txt]; the active gadget UDC on both running units is **`dabr_udc.0`**
  [LIVE Y181:510 / Y175:482; CONFIRMED ×1].

**(c) "ADB over one of its ports" = the receptacle that contains the recognized H2H bridge device.**
`dabridge` is a USB **host-side driver** with a device-ID match table [FW 86331652 vmlinux @file
0x1712290 / vaddr 0xffffffff82512290; CONFIRMED ×1] — 5 entries, each `match_flags=0x0003`
(match VENDOR+PRODUCT):

| idVendor | idProduct | driver_info |
|---|---|---|
| `0x2996` | `0x0100` | `0x82512480` |
| `0x2996` | `0x0101` | `0x825124a0` |
| `0x2996` | `0x0102` | `0x825124c0` |
| `0x2996` | `0x0104` | `0x825124e0` |
| `0x2996` | `0x0105` | `0x82512500` |

`dabridge_probe` [DIS @0xffffffff81a62e00] binds only to a device matching **VID `0x2996`, PID
`0x0100–0x0105`**, reads its descriptors, and runs the bridge; if the configured `bridgeport` has no
such device it logs **"No H2H Bridge device for '%s'"** [FW .rodata @0x1fe06a5]. **So the ADB-capable
path is recognized by a device identity — an H2H bridge chip enumerating as `2996:010x` — not a slot
or a CC strap.** This supersedes the earlier "host-side CC strap / receptacle model" framing as the
*in-vehicle* explanation (that owner-bench result was the direct-line Path B).

**[CROSS-CONFIRMED] VID `0x2996` = Aptiv.** A live enumeration snapshot of the radio's internal USB
tree independently lists it [repo `research/GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt:798-800`]:
- **2× Aptiv H2H bridges — VID `10646`(`0x2996`) PID `261`(`0x0105`)** ← what `dabridge` binds
- 2× GM V10 E2 PD hubs — `0x2996:0132`
- 2× Vendor DFU devices — `0x2996:0120`

So the `dabridge` id_table (`0x0100–0x0105`) targets exactly the **Aptiv H2H bridge** (`0x0105`), not
the Aptiv hub (`0x0132`) or DFU (`0x0120`) — two independent sources (kernel id_table + live enum)
agree, and VID `0x2996` is Aptiv (the receptacle board vendor, "APTIV V10 E2 PD"). **Nuance kept
honest:** the snapshot shows **2×** H2H bridges, so it confirms the *device* `dabridge` recognizes and
names the vendor, but it does **not** by itself prove the non-ADB receptacle *lacks* an H2H bridge —
so "why only one receptacle" is narrowed to device-identity but not fully closed. [UNVERIFIED: whether
the `13558185`/MCIP receptacle contains a `2996:0105` device or only a hub.]

So: one USB-2.0 host link → standard hub cascade drives both receptacle hubs and all accessories;
`dabridge` binds the `2996:010x` H2H bridge in one receptacle and overlays a virtual gadget on that
bridged port, so ADB runs device-side there without ever taking the host tree down. In-vehicle this is
**Path A** (§6); the bench direct line is **Path B** (raw `dwc3.0.auto` gadget, no hub, no bridge).

## 6.2 Why the PC sees the SAME VID:PID in both paths — software-defined, UDC-independent identity
The identity the PC enumerates is **not** the controller's and **not** the bridge's — it is the
**configfs gadget `g1`** descriptor, set in software: `write /config/usb_gadget/g1/idVendor 0x8087` /
`idProduct 0x09ef` [FW 86331650 init.bxtp_gm.rc:841-842], then bound with
`write /config/usb_gadget/g1/UDC ${sys.usb.controller}` [:867]. Because idVendor/idProduct live on the
**gadget**, not the UDC, the *same* `g1` descriptor is presented whether `g1` is bound to
`dwc3.0.auto` (Path B) or `dabr_udc.0` (Path A). The H2H bridge is descriptor-**transparent** — it
relays the gadget `g1` presents — so the PC sees `8087:09ef` (the gadget), **not** `2996:010x` (the
bridge device, which exists only on the radio's internal bus as the thing `dabridge` binds to).

**Answer: yes — the ADB identity to the PC is software-defined (configfs `g1`) and independent of how
it physically arrives.** Same gadget config ⇒ same VID:PID on both paths. Two VID:PIDs, two layers,
never conflate them:
- **PC-facing** `8087:09ef` = the ADB gadget (software, configfs `g1`). Path-independent.
- **Radio-internal** `2996:010x` = the H2H bridge device `dabridge` matches (Path A only).

**[UNVERIFIED] caveats:** (1) no in-vehicle `lsusb -v` was captured to empirically confirm Path A
shows `8087:09ef`; the configfs mechanism predicts it but it is not measured. (2) If the in-vehicle
active config is a composite (e.g. `ncm,adb`) rather than `adb`-only, the PID is that combo's
configfs value — still software-defined, but not necessarily `0x09ef`. The *principle* (software
identity, UDC-/path-independent) is firmware-supported; the exact in-vehicle PID is open.

---

## 7. What actually exposes ADB on a connection — the full logical chain
Combining §1–§6, ADB appears on a USB connection **only** when all of these hold:

1. **The Developer-Options USB-debugging toggle is flipped** — this is the actual trigger
   (owner-confirmed 2026-10-10: ADB off + Mac VBUS present = nothing; flip toggle = ADB). GM's ADB-enable
   path sets the XDCI to **device** role in software (`vendor.sys.usb.role=device` → `usb_otg_switch.sh p`
   → `intel_xhci_usb_sw-role-switch/role=device` → XDCI `OTGD`/`SPPS` ACPI reconfigures port power/connect)
   — §4. **No pin is sensed**; VBUS-sense auto-role is **ruled out**.
2. **A host is supplying VBUS.** The Mac (its CC `Rd` makes *it* host) — or the in-vehicle hub chain —
   provides 5 V. VBUS is a **prerequisite held ready**, not the trigger: with the toggle off it just
   sits there and nothing enumerates (step 1 is what asserts the gadget).
3. **adb gadget bound.** configfs `g1` with `ffs.adb`, `idProduct 0x09ef`, UDC bound — §5.
4. **`adb_enabled=1`.** Set by the Developer-options USB-debugging toggle; GM clears it to 0 every boot
   [repo-sourced connectors.md].
5. **RSA auth** (`ro.adb.secure=1`) — the key-accept step [repo-sourced].
6. **(for a shell, not just enumeration) EEPROM SBI bypass** — without it `adbd` enumerates but
   returns "Secure Client required" [HW doc / owner-bench connectors.md; not a firmware trace here].

On the bench a Mac-side CC `Rd` strap (receptacle or breakout) makes the Mac source VBUS; the radio is
put in device role by the software toggle. The receptacle "model that exposes ADB" is the
direct-line (Path B) **host-side** property [HW doc connectors.md]; the in-vehicle (Path A) ADB-capable
receptacle is instead recognized by the **Aptiv H2H bridge device** `2996:0105` (§6.1c).

---

## 8. GHS high-entropy regions — all identified (closes the "opaque blob" question)
No region hides USB logic. [FW 85098662; CONFIRMED ×2, the chime region decomposed ×1 further]
- `.chime_requester.rodata` (~0x5fcd11–0x922881, 3.3 MB) = **71 uncompressed PCM WAV chime clips**
  (`CADILLAC_GONG`, `SEAT_BELT_1/2`, `COLL_FRNT`, …); 99.7% of bytes are WAV; only code xref to its
  base is the OS memory-map descriptor, not USB/decompressor/crypto.
- `.guidelines.rodata` (~0x951dd2–0xb48e92) = 30 BMP camera-overlay images (124×142×32bpp).
- `.mr_r_mod_ipu_fw` (`$CPD`, camera ISP), `.mr_r_mod_dsp_fw` (`$AE1`, audio DSP),
  `GuC_/HuC_Firmware_MR` (i915 GPU microcode) — co-processor firmware, no path to the USB controllers.
- **768 B** tail = 256 B RSA-2048 `current_android_key` + 512 B RSA-4096 signature [UNVERIFIED
  content, bounded exactly; not USB].

*(The full edge-to-edge byte map of 85098662 is complete — see `GHS_FILE_MAP_85098662.md` (0x0→EOF,
0 gaps, 145 phdrs/180 shdrs accounted). It refined two points folded into §3: GHS does **mediated**
PCI passthrough (emulated PCI fn + RPC register verbs), and the only opaque bytes are the **768 B**
key+signature tail — the TEE "high-entropy" blocks are identified AES T-tables + SHA constants.)*

---

## 9. Status of former open items
**RESOLVED this session:**
- **Bench role-entry (was open #1/#3).** RESOLVED — the **Developer-Options USB-debugging toggle**
  drives GM's ADB-enable path, which sets the XDCI to device role in software and reconfigures port
  power/connect via `OTGD`/`SPPS`. Owner-confirmed (ADB off + VBUS = nothing; toggle = ADB). The
  `brand=Android` GSI rule is **not** the bench mechanism (bench is GM AAOS). **VBUS-sense auto-role is
  RULED OUT.**
- **VBUS clash.** RESOLVED — benign; dual ~5 V at boot is low-energy (not a short), and `SPPS` removes
  the radio's port power on device-role so there's no prolonged dual-source. See §4.
- **Android ACPIO (`86331630`).** Checked — it is only the `ANDR0001` fstab/vbmeta descriptor; no USB
  config. USB governance is the GHS `IGS_DSDT` XDCI/`OTGD` (§4).

**Still genuinely open [UNVERIFIED]:**
1. **Where `sys.usb.controller=dabr_udc.0` and `sys.dabridge.*.portnum` are set** — not in vendor;
   needs the system/product EROFS (`86331654`/`86331636`, not extracted).
2. **Live in-vehicle ADB descriptor** on `dabr_udc.0` vs bench `8087:09ef` — needs an in-vehicle capture.
3. **Whether the `13558185`/MCIP receptacle lacks a `2996:0105` H2H bridge** (the "why only one
   receptacle" closure) — snapshot shows 2× bridges; needs per-receptacle enumeration.
4. **Idle X8 VBUS current** during the momentary boot dual-source window — scope nicety; behavior
   already shown benign.
5. **Host xHCI PCI address** — docs carry `0000:00:14.0` while sepolicy roots `usb1` at `0000:00:15.0`
   and the DSDT XDCI `_ADR` is `0x00150001` (dev 0x15 fn 1). Needs a live `lspci`/DSDT cross-check.
6. **X8 top-row** (6 unwired pins): live 2nd USB port? Physical probe [HW doc].
7. **Bench CC resistor value** — spec `Rd` = 5.1 kΩ; a true 0 Ω is a short, not a valid `Rd` [HW doc].

---

## 10. Provenance of the verification
Four independent FABLE agents re-extracted from the raw modules (own workdirs, own hashes) and cross-
checked: (1) kernel/vmlinux dabridge + disasm; (2) vendor partition scripts + VID/PID + portnum delta;
(3) adversarial GHS carve + two-path; (4) a dedicated crack of the one high-entropy GHS region (chime
PCM). Corrections they forced over the first draft: VID is not always 0x8087 (AOA=0x18d1); the GHS
"opaque region" is chime audio, not undetermined; live controller is `dabr_udc.0` not the vendor
default; the role-switch reaches hardware via the `OTGD` ACPI OpRegion, not a CC pin.

Work trees: `/tmp/gm_usb_re` (primary), `/tmp/agent{1,2,3}`, `/tmp/ph44`.
