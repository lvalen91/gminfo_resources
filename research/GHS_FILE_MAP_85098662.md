# GHS SOC_HOSTOS `85098662` — 100% edge-to-edge byte map

Module: `…/Y181B/USB_Files/85098662`, **14,929,956 B (0x0–0xE3D024)**, sha256 `317ae85c…`.
Built from four independent FABLE cartographer agents (ranges A 0x0–0x3C0000, B–0x780000, C–0xB40000,
D–EOF); each parsed the ELF itself and walked its range byte-by-byte. **Coverage: contiguous, 0 gaps,
reaches EOF.** Every claim is traced to the file; purpose comes from the GHS symtab (kernel) or from
section names + `.boottable`/`.secinfo` records + in-section content (servers carry no symbols).

## Container & format (re-derived, not trusted)
- `0x0–0x27C` (636 B): GM **ipk wrapper** — `BM`@0x0a, `1SHG`@0x24 with length field, 128-bit hex
  digest@0x8c.
- `0x27C`→: a single **ELFCLASS32 / EM_386** image, `ET_EXEC`, entry 0x200000. **145 program headers**
  (`e_phoff`→file 0xE3ACE4) and **180 section headers** (`e_shoff`→file 0xE37FE4) — both tables sit at
  the **end** of the file.
- The 32-bit headers are a container convention: the real code is **x86-64, higher-half**, runtime
  `vaddr = 0xffff800000000000 + ELF vaddr` (verified `_start` 0x200000 ↔ 0xffff800000200000). Two
  **GHS extended 64-bit address tables** trail the standard tables to carry the real addresses.
- **symtab = section 66**, GHS **24-byte** entries (not 16), **18,035** symbols, `.strtab`@file 0x515278.
  It covers the **kernel address space only** (`0x200000`→`.romend`); the ~20 server address spaces
  below have **no symbols** — their purpose is from section name + `.boottable` paths + content.
- Build provenance (symtab paths): `/home/mal/gm_release/MY22-026/final/iot/rtos/…`, INTEGRITY IoT
  2020.18.19, Core 23739.

## Edge-to-edge map (file offset → section → purpose)
Segment/section granularity; interior alignment padding is all-zero and omitted for brevity (agents
confirmed every gap is zero-fill or interior WAV/BMP/const data — no unaccounted bytes).

| file range | section (vaddr) | kind | purpose (traced) |
|---|---|---|---|
| `0x000000–0x00027C` | — | wrapper | GM ipk header (`BM`/`1SHG`/digest) |
| `0x00027C–0x0002BC` | — | elf_header | ELF32/EM_386 + GHS aux fields |
| `0x0002BC–0x03C811` | `.kernel_text` (0x200000) | code | **INTEGRITY x86-64 microkernel** — paging/exception/IRQ/task/domain, PCI, **and the whole GHS USB stack** (xhc.c, xhc_vcontroller.c, xhc_ecm.c, xdci_passthru.c, kusb_dev.c, usb_onboard_vm.c): xHCI host, virtual-controller sharing, CDC-ECM, USB Debug Capability (DbC) — vaddr 0x236720–0x23b4ba, 96 fns / 193 USB syms |
| `0x03C814–0x040448` | `.text` (0x23c558) | code | kernel BSP + C runtime (`main`, `BSP_*`, boot banner) |
| `0x04127C–0x04327C` | `.t_text` (0x241000) | code | trap/interrupt vector stubs |
| `0x04327C–0x04427C` | `.rsyscall` (0x243000) | code | restartable-syscall gate page |
| `0x04427C–0x0452E4` | KernelSpace.secinfo | data | kernel section/security-info table |
| `0x0452E4–0x045342` | `.execname` | rodata | path `".../gm_i35_my22_gb/gm-i35-kernel"` |
| `0x04537C–0x048DAC` | `.rodata` (0x4000c0) | rodata | kernel RO constants/strings (incl. `xdci`@0x460ac) |
| `0x04927C–0x40C27C` | `.mr_r_mod_ipu_fw` (0x404000) | firmware_blob | **Intel IPU4 camera-ISP firmware** (`$CPD` code-partition-dir, `IUNM.man`). 3.94 MB. No x86 exec. |
| `0x40C27C–0x48799C` | `.mr_r_mod_dsp_fw` (0x7c7000) | firmware_blob | **Intel `$AE1` audio-DSP (cAVS/ADSP) firmware** |
| `0x48827C–0x4A485C` | kernel rodata/data cluster | rodata/data | `.rodata_protected_globalsb` (GDT, VMCS_RegMap), `.rdata`, `.rtdata` (incl. USB rodata `USBDev`/`UsbKbdAppClass`) |
| `0x4A485C–0x4AB7B0` | `.traceinfo/.osa/.rtosdir/.linfix` | metadata | non-allocated link metadata |
| `0x4AB7B0–0x515278` | `.symtab` (sec 66) | symtab | 18,035 × 24 B GHS symbols (kernel AS) |
| `0x515278–0x5CD17A` | `.strtab` + `.shstrtab` | strtab | symbol/section name pools |
| `0x5CD17A–0x5FCD11` | server AS: `.vip_server`, `.lifecycle`, `.audit`, `.dirana3_mux_server`, `.chime_requester` (`.text`+`.rodata` each) | code/rodata | INTEGRITY servers: VIP/vehicle-interface, lifecycle, audit log, **DiRaNA-3 radio/audio tuner mux**, chime producer |
| `0x5FCD11–0x92287D` | `.chime_requester.rodata` (0x895000) | audio_blob | **71 uncompressed PCM WAV chime clips** (2ch/24 kHz/16-bit; `CADILLAC_GONG`, `SEAT_BELT_1/2`, `COLL_FRNT`, `STANDARD_*`…), indexed by a 71×24 B table; `0x600DBEEF` end sentinel |
| `0x92287D–0x92CD68` | `.audio_server` (.text 0xbbb000 +.rodata) | code/rodata | Intel audio-DSP firmware loader/IPC, SSP/TDM stream start/stop |
| `0x92CD68–0x944F04` | `.camera` (.text 0xbc6000 +.rodata) | code/rodata | **RVC capture server** — TI DS90UB954 FPD-Link deserializer over I²C, IPU CSI-2 capture/dewarp, recovery FSM |
| `0x944F04–0x953362` | `.guidelines` (.text 0xbdf000 +.rodata) | code/rodata | dynamic-guideline/overlay renderer (`Lines`); 30-asset table |
| `0x953362–0xB48E92` | `.guidelines.rodata` (0xbec000) | image_blob | **30 BMP overlay images** in 8″/10″/13″ screen sets (10 icons each: UPA/pedestrian/caution alerts), 32bpp; `0x600DBEEF` sentinel |
| `0xB48E92–0xB5BF69` | `.ota_update` (.text 0xde4000 +.rodata) | code/rodata | OTA update server |
| `0xB5BF69–0xB84200` | `.calibrations` (.text 0xdf8000 +.rodata) | code/rodata | calibration server |
| `0xB84200–0xBABBA7` | `.gvtg_server` (.text 0xe21000 +.rodata) | code/rodata | **Intel GVT-g vGPU mediator** (graphics virtualization for the guest) |
| `0xBABBA7–0xBCF827` | `GuC_Firmware_MR` (0xe49000) | firmware_blob | i915 **GuC** GPU microcode (CSS header) |
| `0xBCF827–0xBF2DA7` | `HuC_Firmware_MR` (0xe6d000) | firmware_blob | i915 **HuC** GPU microcode |
| `0xBF2DA7–0xBFBF72` | `.display_i2c` (.text 0xe91000 +.rodata) | code/rodata | display-panel I²C control server |
| `0xBFBF72–0xCAC11A` | `.tee_router/.tee_keymaster/.tee_gatekeeper/.tee_hw_crypto/.tee_storage` (.text+.rodata each) | code/rodata | **Trusty-equivalent TEE** servers (keymaster/gatekeeper/hw-crypto/storage). rodata holds standard **AES T-tables (Te0–3/Td0–3) + SHA-256/512 constants** — identified, not secret |
| `0xCBBD7E–0xCF7960` | `.vmm1.text` (0xf60000; links @0x200000) | code | **hypervisor monitor** — VM lifecycle + **PCI passthrough** incl. USB (see below) |
| `0xCF7960–0xD214B0` | `.vmm1.rodata` (links @0x400000) | rodata | **guest ACPI DSDTs** (`IGS_DSDT` ×2), I440FX, NHLT audio, RPC name table, PCI-match descriptors |
| `0xD214B0–0xD2D30A` | `.emmc_mux` (.text 0xfc6000 +.rodata) | code/rodata | eMMC mux server |
| `0xD2D30A–0xDFA98A` | per-server `.data` (lifecycle/vip/**audit 540 K**/dirana3/chime/audio/camera/guidelines/ota/**calibrations**/gvtg/display_i2c/tee_*/**vmm1**) | data | writable init data per address space |
| `0xDFACEE–0xE34ECE` | `.boottable` (0x10a09e4) | data | INTEGRITY Connection/Resource table — binds `Guest1_XHCI0`, `Guest1_XDCI`, `AndroidKeyVMR`, `PassthruBootStatusIod`, GMETH/GMWIFI/SDHC/I2C to the Android VM |
| `0xE34ECE–0xE37526` | `.secinfo` (0x10dabc8) | data | 409 × 24 B image-layout records (dstVA, srcVA, size) |
| `0xE37526–0xE37FDE` | `.shstrtab` | strtab | section-name pool |
| `0xE37FE4–0xE39C04` | **section-header table** | headers | 180 × 40 B (authoritative) |
| `0xE39C04–0xE3ACE4` | GHS ext 64-bit section-address table | headers | 67 × 64 B full addrs |
| `0xE3ACE4–0xE3BF04` | **program-header table** | headers | 145 × 32 B (authoritative) |
| `0xE3BF04–0xE3CC9C` | GHS ext 64-bit segment-address table | headers | 62 × 56 B full LOAD vaddrs |
| `0xE3CC9C–0xE3CCB0` | — | string | ASCII `"current_android_key\n"` |
| `0xE3CCB0–0xE3CDB0` | — | **key (opaque)** | 256 B — RSA-2048-modulus-sized Android key (exposed to Guest1 via `AndroidKeyVMR`). Content UNVERIFIED |
| `0xE3CDB0–0xE3CE20` | — | trailer + fill | `01 00 01 00`, tag `c6 db 19 50` (not a reproducible CRC), then 0xFF fill |
| `0xE3CE20–0xE3D020` | — | **signature (opaque)** | 512 B — RSA-4096-sized signature block. Content UNVERIFIED |
| `0xE3D020–0xE3D024` | — | trailer | `01 00 01 00` |

## USB — what GHS actually does (traced in `.vmm1`, links @0x200000/0x400000/0x600000)
GHS does **not** run a device/role stack; it owns the two real USB PCI functions and exposes them to
the Android guest as a **mediated (para-virtual) passthrough**:
- **Claims the real hardware:** PCI-match predicates `cmp esi,0x5aa88086` (fn @file 0xcf205b → Intel
  **xHCI** 8086:5AA8) and `cmp esi,0x5aaa8086` (fn @0xcf2184 → Intel **xDCI** 8086:5AAA). `.boottable`
  grants `Guest1_XHCI0` + `Guest1_XDCI` to the VM.
- **Host side** `system_usb_passthru.c`: the guest never touches xHCI/xDCI MMIO directly; it issues
  RPC verbs `UsbRdReg`(43)/`UsbWrReg`(44)/`UsbPoll`(45)/`UsbIrq`(120)/`UsbBdf`(14) which the monitor
  executes against the real controller.
- **Guest side** `usb_passthru_emul.c`: presents an **emulated PCI function** (virtual config space +
  BAR0 0x200000-byte window + MSI) — `XHCIPThru`/`XHCIPassThruIRQ`, `"Too many xhci devices"` guard.
- **Guest ACPI `IGS_DSDT`** (two SKU variants, picked at runtime by CPUID-leaf-0x15 core frequency;
  XDCI block identical in both): `Scope(\_SB.PCI0){Device(XDCI){_ADR 0x00150001` (PCI 0x15 fn 1) …
  `OperationRegion(OTGD, PCI_Config,0,0x100)` fields `DVID/XDCB(64b MMIO base)/D0I3/PMEE/PMES`;
  `_DDN "Broxton XDCI controller"`; `_DSM` UUID `732b85d5-b7a7-4a1b-9ba0-4bbd00ffd511` (Intel
  USB-device/OTG DSM) whose `SPPS` method maps `SystemMemory` at the MMIO base to drive `U2CP/U3CP`
  connect-port state and `PUPS/PURC/UXPE` port power. **This `OTGD` OpRegion is the exact ACPI contract
  the Android `intel_xhci_usb_sw` role-switch driver calls to flip the OTG port host↔device** — i.e.
  GHS supplies the surface; the Android guest owns the role decision.
- **Absent everywhere in GHS:** `dabridge`, `dabr_udc`, `bridgeport`, `usb_otg_switch`,
  `intel_xhci_usb_sw`, `role-switch`, `cbc-signals`, `dwc3`, `gadget` — all the role/gadget logic is
  Android-side.

## Opaque-byte accounting (the honest residue)
Of 14,929,956 B, the **only** bytes whose content could not be read are **768 B**: the 256 B Android
key (0xE3CCB0) + the 512 B signature (0xE3CE20) at the tail. Everything else is traced — including the
TEE "high-entropy" blocks (standard AES T-tables + SHA constants) and all co-processor firmware
(identified by magic/header). The earlier "~13 KB opaque" estimate conflated the TEE crypto tables
(identified) with the tail; the true opaque payload is 768 B.

## One-line structure summary
GHS INTEGRITY monolith = **x86-64 microkernel** (incl. a full host-side USB/xHCI stack) + **~20
INTEGRITY server address spaces** (VIP, lifecycle, audit, DiRaNA audio, chime, audio-DSP, camera/RVC,
guidelines, OTA, calibrations, GVT-g vGPU, display-I²C, 5× TEE, **vmm1** hypervisor monitor, eMMC mux)
+ **co-processor firmware** (IPU camera ISP, audio DSP, GuC/HuC GPU) + **media assets** (71 chime WAVs,
30 overlay BMPs) + **guest ACPI/boottable** + header tables + a 768 B key/signature tail. Its USB role
is mediated passthrough of the real Intel xHCI/xDCI to the Android guest, with the `OTGD` ACPI surface
the guest uses for role-switch. No Android-side role/gadget logic lives here.
