# ELK and Recovery

**Scope:** alternative boot targets of the GM Info 3.7 (gminfo37, Apollo Lake A3960) radio: Intel ELK (kernelflinger) and its automatic selection, ELK lock state / Boot Guard / TXE forensic depth, Android recovery and recovery-fastbootd, the "return to dealer" recovery path, and the native-Linux RAM-boot probe images (`4.19.283-*`, `7.3.5-probe-stable02`) with their hardware-coverage, T1 Ethernet, Wi-Fi and eMMC-readback results.
**Not here:** normal boot phases / AVB flow / BCB structs ([boot_chain.md](boot_chain.md)), partition map ([partitions_storage.md](partitions_storage.md)), update engine and the normal-AAOS `gm_usb_*` flag semantics ([ota_update_stack.md](ota_update_stack.md)). The recovery USB trigger-file table is in §5 here.

**Evidence legend:** `[C]` confirmed live or from binary; `[read]` / `[inferred]` as marked; `[U]` unverified/unknown; `[X]` external source. Dates are `YYYY-MM-DD`. Per-claim tags and dates are authoritative over surrounding prose. The long-form evidence and build provenance live in `../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` (cited per section below).

**Related:** [boot_chain.md](boot_chain.md) · [security.md](security.md) · [hardware_specs.md](../hardware/specs.md) · [ethernet_networking.md](ethernet_networking.md) · [can_bench_experiments.md](can_bench_experiments.md) · [can_network.md](can_network.md) · [ota_update_stack.md](ota_update_stack.md) · [emulator.md](emulator.md)

---

## 1. Boot modes and execution boundary

GHS selects boot modes via BCB (Boot Control Block) or external triggers (BCB structs: [boot_chain.md](boot_chain.md)).

| Mode | Trigger | Description |
|------|---------|-------------|
| 1. Normal A/B | Default | Standard A/B verified boot into Android |
| 2. Recovery | BCB `boot-recovery` | Recovery mode (no separate recovery partition; uses boot image) |
| 3. See-Dealer | BCB `boot-see-dealer` | Service-required screen, directs user to dealer |
| 4. ELK | GHS lifecycle recovery target | Fallback boot target for diagnostics/recovery |
| 5. Diagnostic | Service tool | Factory/dealer diagnostic mode |

**Recovery fastbootd is separate from ELK** (verified 2026-11-12): Y181B recovery recognizes `boot-fastboot` / `--fastboot`, sets `sys.usb.config=fastboot`, and enters a persistent wait. This establishes a protocol mode, not a developer build or root shell. [Code and init rules](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#231-recovery-fastbootd-path-verified-2026-11-12).

**Execution boundary (2026-11-12, extended 2026-11-17):**
- VMM maps both `boot-recovery` and `boot-see-dealer` into the Linux/Android guest recovery flag. Ordinary recovery, dealer UI and recovery-fastbootd therefore must not be classified as three bare-metal environments.
- ELK's reciprocal lifecycle/OTA IPC and HECI request are traced. Lifecycle's ACPI driver binding: its callback disables interrupts, flushes caches, synchronizes four CPUs, writes the power-control port and halts. This is a platform power-state transition, not just a guest selection.
- 2026-11-17: the next boot exposes Intel ELK (USB Fastboot returned `kernelflinger-07.02-userdebug` after the CAN F000/8180 request; see §2). A native Probe06 test reproduced the stock HECI selector-2 command through MEI, received CSE success `20870000`, and used Linux `reboot -f` to return directly to ELK without an AAOS boot. GHS residency during ELK execution remains unproven.
- ELK reports `unlocked=yes` across an AAOS round trip while AAOS reports locked/green. This does not establish disabled normal GHS verification or a globally unlocked SoC. Upstream Kernelflinger's `secure=no` variable is fixed, not a hardware secure-boot measurement.
- Later 2026-11-17: custom Linux kernel/initramfs execution through ELK RAM download/boot was confirmed by its distinct USB identity, serial shell and NCM/SSH access. It exposes native HS400 eMMC as `mmcblk1`, with user/boot regions readable without mounting. Panel initialization and explicit display-mode work then enabled the native framebuffer and Linux console (see `../video/display_subsystem.md`). None of this establishes persistent flash-write permission or disables normal GHS AVB checks.
- [Instruction-level evidence and limits](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#233-recovery-execution-boundary-and-mode-selection-verified-2026-11-12).

---

## 2. Intel ELK (kernelflinger)

### 2.1 Identity and entry

- SOC_ABL is kernelflinger ("ELK"; 32-bit x86 ELF at container offset `0x301288`, dedicated `.oemkeys` AVB keystore) [C 2026-10-08, binary SOC_ABL 85738845, SOC_VBMETA 86331644]. ELK is not "Emergency Linux Kernel" (see [security.md](security.md) for trust-layer table).
- **Entry via VIP-mediated CAN request (2026-11-17):** a distinct CAN F000/8180 request, with a temporary and restored application-security RAM gate, entered Intel ELK. USB identified `titan_gm_my22` at `8087:09EF`; the bootloader returned `kernelflinger-07.02-userdebug`. This is separate from the Android fastbootd observations at `8087:4EE0` (§4). See [ELK analysis](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15). (Open conflict C1: PID `09EF` is also recorded for AAOS ADB.)
- **Direct-CAN control attempts** (extended session / profile01 granted; `2F818003` -> `7F2F31`; `AE818003` -> `7FAE11`; no ELK boot established; 8180 absent from the 221-entry CAN DCM identifier table; none of the 39 I/O-control callbacks selects the ELK callback; no RAM-write test performed) are owned by [can_bench_experiments.md](can_bench_experiments.md) (source: CN L129-145).
- ELK reports unlock eligibility separately from lock state: [consolidated source §2.3.2-§2.3.3](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#232-elk-unlock-eligibility-is-a-separate-gate-verified-2026-11-12). There is no demonstrated unlock procedure on the locked production unit.

### 2.2 Observed state (2026-11-17, ELK via CAN)
- Initial repeated queries and an owner-requested unlock invocation timed out.
- After a USB-device reset and a raw libusb client: ELK reported `unlocked:yes`, `secure:no`, and positive unlock eligibility. Whether this state predated the unlock attempt is unverified.
- ELK -> AAOS -> ELK round trip retained ELK `unlocked=yes`, while AAOS reported `verifiedbootstate=green`, `flash.locked=1`, `vbmeta.device_state=locked`, `oem_unlock_allowed=0`.
- Cold-power persistence and any change to actual verification enforcement are unverified. Partition read/write operations are not validated by these state queries.
- The custom RAM boot also receives a green verified-boot command-line value, so that value alone does not authenticate the RAM image.

### 2.3 Lock-state backend and Boot Guard (per firmware revision)

**SOC_ABL 85738845 [C 2026-10-08, avbtool/binary]:**
- **F1: lock-state backend (CONFIRMED-FROM-BINARY).** Device lock state is read from the UEFI NV variable **`OEMLock`** (GUID `1ac80a82-4f0c-456b-9a99-debeb431fcc1`) via `read_device_state_efi()`. `USE_TPM` was NOT compiled (zero TPM2 NV-index constants or TPM2 calls in the 1 MB module), so the lock bit is **not fTPM/TPM2-backed and not RPMB** (`ABL.rpmb=` is only an androidboot cmdline token, not the lock store). The ordinary successful `OEMLock` read uses bit 0 (`0x01`), but this is not the complete state predicate: gated missing-state/provisioning fallbacks also exist (clarified 2026-11-12; research §2.3.2). Live EFI contents are not established by the static trace. A secondary provisioning-UNLOCKED path (`OEMLock` NOT_FOUND + non-virtual boot + life-cycle != ENDUSER) is gated by a manufacturing/SKU life-cycle fuse and stays LOCKED on a production ENDUSER unit. [U] whether the UEFI varstore holding `OEMLock` is SPI-NOR-backed (offline-settable) or RPMB-backed (replay-protected): a layer below kernelflinger, not resolvable from this binary.
- **F2: Boot Guard (verified-capable; enforcement FPF-dependent, [U]).** The IPK (85738845) is a full Apollo Lake IFWI containing a production-signed OEM Key Manifest (`oem.key`, `$MN2`, vendor `0x8086`, RSA-2048), a production-signed IBB manifest (`IBBP.man`, `$MN2`), and a Boot Policy (`BPM.met`) with three SHA-256 digests that exactly match the real boot-block bytes (IBBL, IBB, ELK/OBB). This is a verified-boot construction, so "SOC_ABL ... verified by/with Intel CSE secure boot" / "Hardware enforced" wording elsewhere understates capability, but categorical enforcement is not provable: whether a hash mismatch is REJECTED (verified profile) vs only measured depends on the Intel TXE FPF/OTP fuse state, outside this package (`fitc.cfg` shows build-time intent only).
- **Live TXE/FPF status (corrected 2026-11-17):** Apollo Lake TXE must not be decoded as desktop ME. Live MSR `0x13A` read returned `Input/output error`, not zero. In the standard SACM layout measured/verified flags are bits 5/6; bits 2:1 describe TPM type and bit 3 TPM success; no such bits were obtained from the failed read. Platform FWSTS6 bit 30 is set; the hardware-source `/fpf/intel/SocCfgLock` query returned 1 (platform fuse configuration committed/locked). FWSTS3 reports IBB verification done/pass. The exact rejection profile and individual key/policy fuse contents are not established; physical FPF fuses are not recovered merely by dumping SPI. [Live status evidence](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#live-apollo-lake-fusestatus-check--2026-11-17).
- **Corollary:** Boot Guard digests cover CODE (IBBL/IBB/OBB) only, not the UEFI NVRAM varstore; flipping the `OEMLock` variable would not break any Boot Guard hash.

**Revision boundary (corrected 2026-11-17):** the SOC_ABL 85738845 claims above must not be generalized to the mapped **Y175 ELK executable**. In Y175, lock-state callbacks select physical RPMB or emulation in `teedata`, despite retaining an `OEMLock` error string. Its missing-record provisioning branch tests lifecycle-query status, not the returned lifecycle boolean, and its non-User unlock handler continues after an eligibility refusal. No persistent unlock or change to IBB/GHS policy was demonstrated. [Y175 callback trace](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#y175-elk-lock-state-and-eligibility--callback-trace-2026-11-17).

Keep distinct from the MEC/ADB certificate and BCM ProtoKey material in [security.md](security.md): those mechanisms are not the `OEMLock` boot-lock state.

**Assessment note (2026-09-10, OPEN):** CSM-ownership / AOSP-replacement chain: device locked (`ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`, `sys.oem_unlock_allowed=0`, dm-verity RO); gate description, not a solved path. Boot Guard, signature trust and varstore-backing questions remain owned by [security.md](security.md).

### 2.4 Automatic selection and ELK startup (2026-11-17)

Static IBB/SMIP tracing gives the ordinary candidate order:

1. eMMC partition 1 (`ghs_isys_a`)
2. eMMC partition 2 (`ghs_isys_b`)
3. SPI ELK
4. partition 5 at offset `0x7D0000`
5. CLI

A returned load/authentication error permits the next candidate. This is evidence for an automatic SPI-ELK fallback, not a live test with erased/failed GHS partitions. ELK startup still has storage-initialization dependencies and enters fastboot; autonomous storage boot of Probe and recovery from completely erased eMMC remain [U]. [Selection trace](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#automatic-selection-and-elk-startup--2026-11-17).

Both kernel.org-based 4.19.283 and Linux `7.3.5-probe-stable02` have executed through ELK RAM download/boot. Stable02's packaged helper initializes the panel automatically; owner-visible output, USB shell and T1 root SSH were verified. This does not prove arbitrary unsigned normal-storage boot or disabled hardware/IBB verification. The observed eMMC block number varies across boots (§3.4).

---

## 3. Native Linux RAM boot (probe images)

### 3.1 Build lineage (all RAM-only, loaded through ELK download/boot)

| Image | Kernel | What was established | Source |
|---|---|---|---|
| probe03 | (4.19 tree; `CONFIG_IGB` disabled) | PCI `8086:157c` enumerated without driver; `igb.ko` and BCM4359 `brcmutil`/`brcmfmac` loaded as modules without reboot; earlier Wi-Fi transfer success | NET L97-186 |
| probe04 | `4.19.283-elk-linux-probe+` | packaged `igb.ko`, VLAN 5, Dropbear SSH as uid 0; no image rebuild, reboot or persistent radio-storage write was needed | NET L124-131 |
| upstream-probe01 | `4.19.283-upstream-probe01` (kernel.org-based, igb built in) | T1 SSH uid 0; no host network configuration or persistent radio storage changed | NET L133-141 |
| probe05 | (read-only inventory while probe06 was built) | subsystem inventory (§3.5) | HW L65-87 |
| probe06 | (corrected build with embedded stock IPU firmware) | IPU video nodes appear (§3.6); stock regulatory DB rejected by kernel | HW L89-94 |
| stable02 | `7.3.5-probe-stable02` | automatic 2400x960 panel, USB ACM shell, igb/VLAN-5 root SSH, MEI presence, native eMMC read; upstream signed regulatory DB embedded; host configuration unchanged | NET L143-156, HW L46-63, SEC L119-124 |

Build provenance and image hashes: [boot analysis](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md); [stable02 record](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

**Stable02 runtime options:** `CONFIG_MODVERSIONS=n`, `CONFIG_MODULE_SIG=n`, `CONFIG_DEVMEM=y`, `iomem=relaxed`; `/dev/mem` presence verified. These choices neither rewrite fuses nor establish disabled IBB/GHS authentication or unsigned normal-storage boot.

### 3.2 T1 Ethernet test procedure and results

Procedure (volatile; repeat after every RAM-image reboot; driver, IP and listener setup are not persisted; no persistent radio storage written):
1. Load `igb.ko` (built against the running kernel output and symbol versions; unsigned-module taint reported, not a load rejection) or use a kernel with igb built in. Raise `eth0` (PCI `8086:157c`, Intel I210 flashless SerDes, in the standard `igb` ID table).
2. Create `vlan5` (802.1Q ID 5) on `eth0`; assign a volatile address from the existing isolated bench T1 subnet (`<RADIO_T1_IP>/24`; host `<HOST_T1_IP>`). The Mac already had VLAN 5 on its T1 adapter, so no host change was needed.
3. Install the Mac's public key in RAM, generate a RAM-only Dropbear host key, start a password-disabled Dropbear listener bound to the T1 address. Bind the host SSH client to its T1 source address. The host key changes on every fresh RAM boot.

Results:

| Test | Result |
|---|---|
| Carrier | 1000 Mb/s on the internal uplink; Mac physical adapter negotiated 100baseTX full-duplex |
| probe03 ping | 3 replies, 0 loss, 0.887-1.265 ms |
| probe04 ping | 2 replies, 0 loss, 0.905-1.214 ms; `id` uid/gid 0; `uname -r` = `4.19.283-elk-linux-probe+` |
| upstream-probe01 | SSH login returned UID 0 and the new kernel release |
| stable02 | USB shell and T1 SSH both report `7.3.5-probe-stable02`, UID 0 |
| 64 MiB raw eMMC read over T1 | 3.98 MiB/s including connection overhead; SHA256 `d535d439f96a44419320f3dd85b185a3b386c69b29d46b662a4304ab510af578`, matching the earlier independently checked USB sample |

T1 readback functionality and sample integrity are established, not long-duration reliability. The path is slower than USB NCM (approximately 27-31 MiB/s); the internal gigabit carrier does not make the external 100 Mb/s path gigabit. The existing USB shell/SSH stayed available. Runtime addresses/keys are intentionally omitted. T1/VLAN 5 addressing context: [ethernet_networking.md](ethernet_networking.md).

### 3.3 Wi-Fi test (BCM4359, probe03)

- PCI `14e4:43ef` = BCM4359. No bound driver in the probe kernel. Matching `brcmutil` and PCIe/MSGBUF `brcmfmac` modules were built against the running kernel output and loaded without reboot.
- The stock Y175 Wi-Fi HAL explicitly selects `nvram_pcie_4359_cwm_76.cal`; its firmware, CLM blob and that board calibration were staged in the RAM filesystem under the filenames brcmfmac requests. Without the NVRAM file: `FW failed to initialize`; reloading with it created `wlan0` and initialized the stock firmware.
- Alpine v3.22 x86_64 `iw` and `wpa_supplicant` (with runtime libraries) provided scan/association. The user-authorized home WLAN was visible at 5200 MHz (~-48 dBm RSSI; 2.4 GHz ~-71 dBm). WPA2 association on 5200 MHz and DHCP succeeded. Credentials/addresses were volatile and are omitted. Public-key-only SSH reached the Mac on its wired LAN connection.
- 64 MiB eMMC read: 27.86 MiB/s including SSH setup; SHA256 `d535d439f96a44419320f3dd85b185a3b386c69b29d46b662a4304ab510af578` (matches the earlier sample). Post-transfer RSSI -47 dBm; zero transmit failures.
- 512 MiB read: 31.16 MiB/s; matched an independent source reread SHA256 `fe5a0b7347b8e5ac9634123e79dc9a3726a1be2633cbaa2e773b47f77be61ff2`. Not yet proof of full-image transfer reliability. eMMC stayed read-only and unmounted. No peer-to-peer Wi-Fi link was needed or tested.
- **Stable02 Wi-Fi:** the upstream signed regulatory database is embedded and packaged in the initramfs, signature enforcement retained; missing/invalid regulatory-database messages no longer occur. BCM4359 still completes firmware startup around 62.9 s and then exposes `wlan0` (separate startup delay remains). No stable02 association or throughput measurement is claimed.

### 3.4 eMMC identity and readback

- eMMC is on PCI `00:1c.0`; its name changed between `mmcblk2` and `mmcblk1` across the two 7.3.5 boots. Identify the physical device before using a block-device path. (ELK RAM boot also reported HS400 eMMC as `mmcblk1`.)
- Probe05: 124,993,536 user sectors; 26 partitions; boot0/boot1 each 65,280 sectors, read-only; no block-device mounts.
- First 1 MiB hash matched the saved backup (stable02); no block filesystem mounted, no flash written.
- First 4096-byte sample SHA256 `f9285861c75b06d2d3838ef0638f4ab90eb3e85cadec25c3f68e67e7aedfe0ac` matched the verified saved dump; not a second whole-device verification.
- 64 MiB sample SHA256 `d535d439f96a44419320f3dd85b185a3b386c69b29d46b662a4304ab510af578` (matched over USB, T1 and Wi-Fi); 512 MiB sample SHA256 `fe5a0b7347b8e5ac9634123e79dc9a3726a1be2633cbaa2e773b47f77be61ff2`.
- Boot0 and boot1 copies matched independent source hashes. A full user-area image initially stopped at 23.44% over USB; a fresh Wi-Fi read then completed all 63,996,690,432 bytes and matched independent source/file SHA256 (full hash: [partitions_storage.md](partitions_storage.md) full-user-area row). The obsolete interrupted partial was deleted.
- RPMB counter read succeeded; the first RPMB data read timed out; no RPMB dump is verified (RPMB was not retried in the probe05 pass).
- These are Linux readback results, not proof of ELK flash-write permission.

### 3.5 Hardware coverage (probe05 inventory; stable02 notes)

Probe05 read-only inspection covered PCI/platform bindings, I2C clients, USB host/gadget, DRM, input, ALSA, block devices, UARTs, SPI, GPIO, thermal, RTC, network and kernel failures. Enumeration is distinguished from functional testing. No blind I2C scan, GPIO toggle, device rebinding, storage write, or camera/audio stream was performed; the running display and T1 shell were preserved.

| Subsystem | Observed result | Limit / next requirement |
|---|---|---|
| CPU/RAM | Atom A3960, four cores; MemTotal 5,963,784 KiB, about 5,766,976 KiB available; no swap; intel_pstate performance, 800-2400 MHz limits | Frequency limits are driver-reported, not a sustained-load measurement |
| GPU/display | i915 8086:5a84; CRTC50 -> framebuffer106; HDMI-A-1/connector90, 2400x960@60, 153.98 MHz; physical console previously confirmed | Forced connector status alone is not detection evidence; serializer link and owner observation establish output |
| Display link/touch | Serializer register 5A = CD; maXTouch 16-bit-address reads begin `a4 3e 10 aa 21 40`; reset GPIO467 high | Only Power Button/event0 is registered as Linux input; maXTouch evdev/IRQ binding incomplete |
| eMMC | see §3.4 | RPMB not retried |
| T1 Ethernet | Intel I210 8086:157c bound to igb; eth0 and VLAN5 carrier up; root SSH working | End-to-end SSH verified; no new throughput/stress test |
| Wi-Fi | BCM4359 14e4:43ef enumerated, unbound in this boot | Matching modules/firmware included; probe03 transfer success is separate evidence |
| USB | xHCI host, DWC3 ACM/NCM gadget; downstream MCP2200 04d8:00df with CDC-ACM and HID bindings, ttyACM0; gadget ttyGS0 available | USB root shell works; MCP2200 is internal to the radio (see §3.7) |
| Camera capture | Intel IPU4 8086:5a88 probe attempted; missing `ipu4_cpd_b0.bin`, fallback waited from 0.266 s to 62.512 s and failed with -110; no /dev/video* or /dev/media* | IPU firmware-loading failure, not proof of an absent camera. ACPI ADV7481A/B entries are unbound declarations, not proof those chips are populated |
| Audio | HDA/SST-class 8086:5a98 enumerated without a bound PCI driver; ALSA reports no soundcards | Codec/DSP/board routing and driver/firmware unresolved; no audio output test |
| I2C | Eight DesignWare adapters plus three i915 GMBUS adapters and I801 SMBus; active display controller is PCI 00:17.3 / native i2c-10 | Other physical slave population not determined by enumeration |
| SPI/UART | Three SPI masters, no enumerated SPI slaves; four 16550A UARTs, zero recorded TX/RX in this pass | No arbitrary port opened or transmitted to; VIP/other endpoint assignment not proven |
| GPIO/PWM | Four INT3452 banks (43/47/77/78 lines), pwmchip0; GPIO467 requested/high | Controller availability does not establish every board signal's role |
| Thermal/RTC | acpitz and coretemp, both 33 C at sample; rtc_cmos present | One observation; no clock-setting or thermal stress |
| Other PCI | AHCI 8086:5ae3, three 8086:5a9a/5a9c/5a9e communications functions, and 8086:5aa2 unbound | Unbound does not mean fault: some need firmware, board services, or are unused on this variant |

**Stable02 additions (2026-11-17):** automatic 2400x960 panel output, USB ACM shell, igb/VLAN-5 root SSH, MEI presence, native eMMC read verified. The panel helper uses `/sys/bus/i2c/devices`, selects the physical controller, and retains a GPIO-v2 request for line 33 of the verified 78-line `INT3452:00` bank (global GPIO467 is an older-kernel mapping, not a portable number). maXTouch answers proper 16-bit-addressed reads but has no input-device/IRQ binding. Audio/IPU/decoder integration incomplete: no soundcards or video nodes on this build. Auxiliary MMC card-detect/initialization errors are separate from working eMMC. T1 counters were clean and sampled temperatures ~30-31 C (bounded observations, not stress tests). [Current evidence and limits](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

### 3.6 Probe06 follow-up
Embedded stock IPU firmware removed the firmware-request timeout. PID1 began at 0.437303 s and 25 video nodes, nine V4L subdevices and one media device appeared. No camera stream was captured; subdevice warnings remain. This supersedes the probe05 missing-video-node observation, not the unverified camera wiring/capture status. The stock regulatory database was rejected by the kernel (later fixed in stable02, §3.3). [Probe06 record](../video/display_subsystem.md#probe06-corrected-build-and-firmware-staging--2026-11-17).

### 3.7 Peripheral notes
- **USB topology (owner-confirmed 2026-11-17):** the only known externally connected radio USB port is wired to the host computer for ADB/USB shell. No user-attached USB peripheral accounts for MCP2200 `04d8:00df`; its xHCI-side CDC-ACM/HID enumeration is an internal radio device. The DWC3 device/gadget connection to the host is a separate USB role/path.
- MCP2200 `04d8:00df` is an internal radio bridge associated with the SXM serial path (AAOS `ttyACM1`, `sxm_device`), native `ttyACM0`; no SXM traffic sent or captured. Full topology reasoning: [hardware_specs.md](../hardware/specs.md) section 10 (USB), "MCP2200 topology".
- Not established as operational by the native pass: Bluetooth, GNSS, AM/FM, SXM, external amplifiers, camera feeds, VIP-side peripherals. Product existence does not imply a directly enumerated Linux device.
- Camera deserializer (TI DS90UB954, teardown board) vs SoC Intel IPU4: [hardware_specs.md](../hardware/specs.md) section 7; population on the running bench board is separate from teardown evidence.
- MFi diagnostic access (AAOS `/dev/i2c-2` 0x10; native bus 5 mapping did not acknowledge): [hardware_specs.md](../hardware/specs.md) section 12.
- Native GPU shader rendering, Vulkan device initialization and VA-API profile availability are verified separately: [hardware rendering](../video/hardware_rendering.md#native-linux-gpu-acceleration--verified-2026-11-17).

---

## 4. Android fastbootd (userspace fastboot) [C live-Y175 2026-10-06]

Not Intel ELK. Reached on the **direct OTG bench line** (no GM receptacle hub): HSAL-2 -> breakout with a Mac-side CC->GND `Rd` strap -> Mac. X8 is 4-wire so CC never reaches the radio, whose role switch is software (`intel_xhci_usb_sw-role-switch` -> XDCI `OTGD`/`SPPS` ACPI): VBUS sourcing and role are a register decision, not a sensed pin [FW `dsdt_a.dsl:1290-1500`]. ADB is entered by the Developer-Options USB-debugging toggle (owner-confirmed 2026-10-10: ADB off + Mac VBUS present = nothing enumerates; toggle on = ADB; VBUS-sense auto-role ruled out).

- `adb reboot fastboot` brings up fastbootd (`is-userspace:yes`), enumerating as USB **`8087:4ee0`** (Intel VID + Android fastboot PID), persisting in mode (captured with a macOS `ioreg` watcher, present ~1m50s).
- Only alternative-boot USB interface observed: `adb reboot bootloader` (ABL), `recovery`, `edl`, `dnx` all stayed USB-dark until the OS returned (matches older hub-path tests; the hub never surfaced fastbootd, the direct OTG line does).
- Returning to the OS (`fastboot reboot`) auto-disables ADB (re-enable via Developer Options).

Capabilities on the locked unit:

| Probe | Result |
|---|---|
| `getvar all` | succeeds (information disclosure) |
| lock/secure | `unlocked:no`, `secure:yes` (consistent with `flash.locked=1` / `oem_unlock_allowed=0`) |
| `oem device-info`, `partition-type:*`, `oem help` | "Fastboot HAL not found" / "Unable to open fastboot HAL": no vendor command surface, no flashing backend |
| `getvar max-fetch-size` / `fastboot fetch` | FAILED "fetch not supported on user builds" (device-confirmed 2026-10-06) |
| `fastboot boot <valid-header img>` | FAILED (remote: "Download is not allowed on locked devices"); rejected at the download primitive, before AVB applies (device-confirmed 2026-10-06) |
| `fastboot flashing get_unlock_ability` | "Unrecognized command": the `flashing` group is unimplemented (device-confirmed 2026-10-06) |

Since `flash`/`stage`/`boot` all require download, the only fastbootd capability on this locked unit is read-only `getvar`. Any image operation first requires defeating the lock via the SBI/seed/AVB path.

Disclosed by `getvar all`: A/B slots (`slot-count 2`, `current-slot:b`); dynamic `super` (0x465000000) with logical `system/vendor/product_{a,b}`; `boot/vbmeta/bootloader_{a,b}`, `misc`, `metadata`, `data` (0x9C1800000) sizes; `security-patch-level 2024-05-05`; fingerprint `W213E-Y175.5.2`; `version-bootloader 2121-1`; `first-api-level 29`; `version-vndk 32`; `max-download-size` 0x10000000 (256 MB); `cpu-abi x86_64`; `treble-enabled:true`; `dynamic-partition:true`. (Super size cross-check: [partitions_storage.md](partitions_storage.md).)

**Assessment:** fastbootd is a privileged ramdisk/root pre-OS environment leaking the full partition/version map, but on a stock locked unit it is an information-disclosure + staging surface, not a flashing path (locked + no OEM HAL). Reaching it needs the two ADB gates (Developer-Options USB-debugging toggle that software-switches the radio to device role via `OTGD`/`SPPS`, with the Mac-side CC `Rd` strap only so the Mac sources VBUS; plus EEPROM SBI) to issue `adb reboot fastboot`: see [`../hardware/connectors.md`](../hardware/connectors.md) section "Bench ADB ... receptacle MODEL".

---

## 5. Recovery, dealer screen and bench recovery tests

- **Recovery fastbootd entry:** see §1 (`boot-fastboot` / `--fastboot`, `sys.usb.config=fastboot`).
- **Error/dealer screen rendering:** "return to dealer" / recovery screens are rendered by **GHS**, not Android. GHS has direct display access and draws the backup-camera overlay independently of the Android guest (camera works during an Android reboot). `gm_update_engine` stages OTA packages and writes the BCB (`boot-recovery` / `--show_return_to_dealer`) to `misc`; the on-screen rendering is GHS. See `../hardware/teardown.md` section "GHS as Recovery Architecture". History: corrects an earlier claim that GHS is headless (BC L548).
- **USB trigger files** (Base64 recovery markers, PIT6209 correction, `gm_usb_*` flags): full table in [boot_chain.md](boot_chain.md#usb-trigger-files). The recovery scanner reads them; they do not independently enter recovery.
- **Interpretation of `--show_return_to_dealer` (2026-11-12; read vs inferred):**
  - *Read:* in the retained recovery logs (counters 54/55), recovery logs `Not get boot-see-dealer mode, start normal update process.` then `Dump log to USB` / `Saving log completed.`; normal Android was up afterwards (live `sys.boot_completed=1`, uptime 11 min at 13:59 AKST; `moduleinfo` timestamp 13:10:49 AKST).
  - *Inferred:* these entries are the dealer-screen / USB log-export path, not a bricked or unflashable state. The earlier wipe-reason boots (47-50: `bcm_replacement`, delayed GM server wipe 2026-11-07, MasterClear 2026-11-10) are separate data-wipe recoveries.
- **Bench verified 2026-11-12:** deliberately removing `com.gm.homescreen` for users 0 and 10 produced incomplete startup; the operator observed automatic dealer/recovery entry after three failed attempts. The encoded capture marker then produced the retained USB export. Final recovery records show `boot-recovery` plus `--show_return_to_dealer`, not literal BCB `boot-see-dealer`. A later export repeats capture with recovery counter 55 vs 54. Rotated logs include multiple saves from one recovery run; do not count rotations as boots. [Provenance and startup limits](../research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#221-y181b-failed-boot-threshold-verified-2026-11-12).
- **Failed-boot threshold / lifecycle** (Y181B threshold 3 at `0x200E2D`): [boot_chain.md](boot_chain.md).
- **Direct-CAN factory-reset attempt (2026-11-17)** and the ELK control candidates: [can_bench_experiments.md](can_bench_experiments.md).
- **MDI2 / post-power-cycle recovery narrative** (NoCalibration, LTZ recovery): diagnostics/bench docs, not here (see ledger).

---

## Open conflicts

- **C1: USB ID `8087:09EF`.** security.md L731 records ELK (`titan_gm_my22`, kernelflinger-07.02-userdebug) at `8087:09EF`; can_network.md L1623/L1632/L1663 record the same ID for AAOS ADB (interface FF/42/01). Not reconciled; may be a shared VID:PID with different interface class, or an error in one source. Android fastbootd is `8087:4EE0` (security.md L723).
- **C2: eMMC block name.** `mmcblk2` vs `mmcblk1` across 7.3.5 boots (HW L48-49); ELK RAM boot reports `mmcblk1` (BC L110). Treated as per-boot enumeration order; always identify by PCI `00:1c.0`.
- **C3: Display touch/reset numbering.** GPIO467 (reset, probe05 row; HW L76, L85) vs line 33 of the 78-line `INT3452:00` bank (stable02 helper, HW L54-56): the former is an older-kernel global mapping. Native display controller "native i2c-10" (HW L83) vs AAOS touch on i2c bus 7 @ 0x4B (HW L29/L168, owned by ../hardware/specs.md): bus numbering differs by kernel; no explicit reconciliation in source.
- **C4: Camera.** ACPI ADV7481A/B declarations vs TI DS90UB954 on the teardown board: not reconciled; tracked in [hardware_specs.md](../hardware/specs.md) Open conflicts item 5.
- **C5: RAM.** Probe05 MemTotal 5,963,784 KiB (HW L74) vs historical MemTotal ~5530 MiB / Y181B E820 5743 MiB (HW L24; owned by ../hardware/specs.md). Different builds, not reconciled. (5,963,784 KiB = ~5824 MiB.)
- **C6: CPU frequency.** probe05 intel_pstate 800-2400 MHz (HW L74) vs 800 MHz / 1.6 GHz / 2.0 GHz burst (HW L14) and 1881.6 MHz (HW L18); owned by ../hardware/specs.md.
- **C7: Lock-state backend by revision.** `OEMLock` UEFI NV variable, not RPMB (SOC_ABL 85738845, 2026-10-08) vs physical RPMB or emulation in `teedata` (Y175 ELK, 2026-11-17). The later dated correction scopes the first to its revision; both retained, not a settled generalization.
- **C8: ELK vs AAOS lock report.** ELK `unlocked:yes` while AAOS `locked/green` across a round trip (SEC L737-739); not reconciled, flagged by source as not establishing disabled verification. Android fastbootd separately reports `unlocked:no` (SEC L757).
- **C9: Super size** from fastbootd `getvar` (0x465000000 = 18000 MiB) vs 8.6 GB in boot_chain partition table: owned by [partitions_storage.md](partitions_storage.md).
