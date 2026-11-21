# GM Info 3.7 Partitions and Storage

**Scope:** eMMC device and GPT layout, the 26-partition map, dynamic partitions (`super`/LP metadata), first-stage mount and fstab mechanisms, and mounted-filesystem sizes.
**Out of scope:** boot phases, A/B and BCB structs, AVB flow ([boot_chain.md](boot_chain.md)); ELK/Probe native-Linux bring-up ([elk_recovery.md](elk_recovery.md)); update-engine and package flow ([ota_update_stack.md](ota_update_stack.md)).

**Evidence legend:** `[V]` read directly from hardware or a live radio; `[C]` cross-checked against a second source, or arithmetic derived from `[V]` values; `[U]` stated in a source without a measurement or inferred from static analysis.

**Related:** [boot_chain.md](boot_chain.md) | [firmware_versions.md](firmware_versions.md) | [hardware_specs.md](hardware_specs.md) | [elk_recovery.md](elk_recovery.md) | [ota_update_stack.md](ota_update_stack.md) | [emulator.md](emulator.md) | [security.md](security.md) | [../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md](../research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md)

---

## 1. Conclusion: `super` and static-vs-dynamic A/B

| Question | Answer | Evidence |
|---|---|---|
| Does the radio use a `super` partition with logical `system`/`vendor`/`product`? | **Yes, on Y175 [V]; on Y181B [V] by update-engine logs and package script (the `super` size itself was never measured on Y181B).** | Sections 4.1 and 4.2 |
| Y175 `super` size | **18000 MiB** (p13, LBA 741376), measured twice: GPT/LP dump 2026-11-17 and fastbootd `getvar` (`0x465000000` = 18,874,368,000 B = 18000 MiB) 2026-10-06 | [V], [C] |
| Y181B `super` size | **Not measured.** The earlier "8.6GB" figure carried in the old partition tables has no measurement behind it and is retained only under Open conflicts. | [U] |
| Is "static A/B, no `super`, no dm-linear" (SSDT reading) true of the radio? | **No on Y175 (refuted):** the stock cmdline carries no `androidboot.android_dt_dir` and kf4abl appends none, so `fs_mgr` never reads the SSDT fstab. Not directly tested on a Y181B GPT; the live Y181B update engine and package script contradict it (section 4.2). It holds only for the emulator/reference-image disk layout. | [V] Y175; [C] Y181B |
| Is the ACPI SSDT the first-stage fstab mechanism? | **No.** It loads into ACPI fine but `fs_mgr` `ReadFstabFromDt()` cannot read a fstab from it (QEMU real-kernel work, 2026-09-27). Whether real Y181B hardware resolves anything through it is unconfirmed (Open conflicts). | [V] QEMU; [U] Y181B hardware |

History: the 2026-09 boot-image extraction reading (SSDT describes static by-name partitions, so "static A/B, no super") was qualified 2026-11-12 (live Y181.3.2 update-engine logs, `super` in active use) and refuted for Y175 hardware 2026-11-17 (GPT + LP metadata read). The 2026-09-27 QEMU result had already shown the SSDT is not a usable DT-fstab source. Sources: boot_chain.md L358-401, emulator.md L16, L48-88, security.md L772.

---

## 2. eMMC device

| Item | Value | Evidence |
|---|---|---|
| Part | 64GB Samsung KLMCG4JEUD eMMC (hardware.md L25) | teardown |
| PCI location | `0000:00:1c.0`; guest cmdline `androidboot.diskbus=1c.0` | [V] |
| Holds | GHS + Android; separate from the module's ISSI SPI-NOR IFWI (Boot Guard + TXE/CSE stage) (intel_apl_external_resources.md L173-176) | |
| User area | 124,993,536 sectors = 63,996,690,432 B (63.997 GB) | [V] Y175 native Linux 2026-11-17 |
| GPT | 26 partitions | [V] Y175 native Linux |
| boot0 / boot1 | 65,280 sectors each; read-only | [V] |
| Block device name (native Linux) | `mmcblk2` in one 7.3.5 boot, `mmcblk1` in another; identify the physical device (PCI `00:1c.0`) before using a path | [V] |
| Guest device names (GHS virtio) | `vda1`-`vda26` | stated in boot_chain.md L321 |
| First 4096 bytes SHA256 | `f9285861c75b06d2d3838ef0638f4ab90eb3e85cadec25c3f68e67e7aedfe0ac` (matched the saved dump; not a second whole-device verification) | [V] |
| First 1 MiB hash | matched the saved backup | [V] |
| Full user-area image | all 63996690432 bytes read over Wi-Fi, SHA256 `e630b3cbb0b76f8f721e83956555cb84270046998ef4859e85c21ec55216cd86` matched independent source/file hash (an earlier USB read stopped at 23.44% and its partial was deleted) | [V] |
| boot0 / boot1 copies | matched independent source hashes | [V] |
| RPMB | counter read succeeded; first data read timed out; no RPMB dump verified; not retried in the 7.3.5 inventory pass | [V] |
| Mount state during native reads | no block filesystem mounted, no flash written | [V] |
| HS400 | native eMMC enumerates as HS400 under ELK RAM Linux | [V] |

Derived check [C]: 124,993,536 x 512 = 63,996,690,432 B, equal to the whole-image read length.

GHS exposes an `emmc-health` interface (`/dev/ghs/emmc-health`; absent in the emulator); see [vip_ipc_ghs.md](vip_ipc_ghs.md).

---

## 3. Partition map

26 partitions with A/B redundancy, exposed to the Android guest as virtio block devices `vda1`-`vda26` (guest view; native Linux sees the same GPT on `mmcblk*`). **Byte offsets and sizes below are from a GPT parse of the full Y175 user-area image (63,996,690,432 B / 60 GiB; 2026-11-20);** the row descriptions were carried from the original boot-chain analysis. The parse independently corroborates §4.1: `super` offset `0x16a00000` = 379,584,512 B matches the measured `super` byte offset.

| Device | Partition | Offset | Size | Description |
|--------|-----------|--------|------|-------------|
| vda1/2 | ghs_isys_a/b | a `0x100000` · b `0x4100000` | 64 MiB | GHS hypervisor image (SOC_HOSTOS 85098662) |
| vda3 | ghs_storage | `0x8100000` | 16 MiB | GHS persistent storage |
| vda4 | ghs_abl_update | `0x9100000` | 8 MiB | CSE+ABL SPI reflash capsule (top 6 MiB of IFWI; **not a runtime stage** — [BOOT_TRUST_ANCHOR_AND_KEYS.md §3](../research/BOOT_TRUST_ANCHOR_AND_KEYS.md#3-soc_abl--elk-kernelflinger-and-ghs_abl_update)) |
| vda5/6 | bootloader_a/b | a `0x9900000` · b `0xb700000` | 30 MiB | Intel ABL bootloader (kernelflinger, SOC_ABL 85738845) |
| vda7/8 | boot_a/b | a `0xd500000` · b `0x11500000` | 64 MiB | Android kernel + ramdisk (AVB-hash) |
| vda9 | misc | `0x15500000` | 1 MiB | GHS rollback counter, BCB, A/B metadata (A/B metadata at offset `0x800`, BCB at `0x000`; structs in [boot_chain.md](boot_chain.md)) |
| vda10/11 | vbmeta_a/b | a `0x15600000` · b `0x15800000` | 2 MiB | AVB verification metadata (signed by `current_android_key`) |
| vda12 | metadata | `0x15a00000` | 16 MiB | ext4, Android metadata (FBE encryption keys) |
| vda13 | super | `0x16a00000` | 18000 MiB | dynamic partitions (system, vendor, product via dm-verity); **18000 MiB on Y175 [V]**, Y181B size unmeasured (section 4) |
| vda14/15 | acpi_a/b | a `0x47ba00000` · b `0x47bc00000` | 2 MiB | ACPI tables |
| vda16/17 | acpio_a/b | a `0x47be00000` · b `0x47c000000` | 2 MiB | ACPI overlay tables (AVB-hash; Android `ANDR0001` fstab/vbmeta descriptor SSDT; section 5) |
| vda18/19 | cert_a/b | a `0x47c200000` · b `0x47c400000` | 2 MiB | Certificate store (**empty** on this image) |
| vda20 | persistent | `0x47c600000` | 1 MiB | FRP (Factory Reset Protection) / AVB persistent props |
| vda21 | teedata | `0x47c700000` | 32 MiB | TEE persistent data (Trusty) |
| vda22 | config | `0x47e700000` | 8 MiB | ext4 -> `/mnt/vendor/oem_config` |
| vda23 | calibration | `0x47ef00000` | 16 MiB | ext4 -> `/mnt/vendor/calibration` |
| vda24 | ghs_log | `0x47ff00000` | 640 MiB | GHS log storage |
| vda25 | update_cache | `0x4a7f00000` | 2 GiB | ext4, OTA staging (GM `.mnf`/`.smd` packages) |
| vda26 | data | `0x524f00000` | 39960 MiB | f2fs ~39 GB, user data (file-based encryption) |

Critical partitions (subset of the rows above): `ghs_isys_a/b`, `boot_a/b`, `vbmeta_a/b`, `misc` (GHS rollback counter, BCB), `super`, `data` (~39GB f2fs).

Notes:
- No separate recovery partition: recovery uses the boot image (see the boot modes table in [boot_chain.md](boot_chain.md)).
- There are no `system_*`/`vendor_*`/`product_*` GPT entries on Y175 (those live inside `super`).
- The Y175 `misc` offsets match Intel kernelflinger's BCB read at `0x800` (intel_apl_external_resources.md L32).
- `data` on Y175 per fastbootd `getvar` is `0x9C1800000` = 39960 MiB [V]; the Y177 snapshot lists `data_partition` 39936 (section 6) [C, consistent within ~0.1%].
- Fastbootd `getvar all` on Y175 also disclosed sizes for `boot`/`vbmeta`/`bootloader_{a,b}`, `misc` and `metadata` (security.md L772-776); the individual values are not recorded in the platform docs.
- `update_cache` is the mount behind `/update_cache/...` paths (update staging, `recovery/command`, `calibrations` symlink, `bootup_log`, `update/moduleinfo`). Several docs read exports "from `/cache`"; whether `/cache` is the same filesystem is not stated (Open conflicts).
- Hardware areas outside the user GPT (Y175 image, 2026-11-20): the eMMC HW boot partitions `boot0`/`boot1` (2× 32 MiB) are **empty** (all-zero, unused); **RPMB** (~4 MiB, replay-protected) was **not captured** (0-byte stub) — the one authenticated/replay-protected store remains unexamined (relevant to the GHS-image-authentication question, [BOOT_TRUST_ANCHOR_AND_KEYS.md §8](../research/BOOT_TRUST_ANCHOR_AND_KEYS.md#8-ghs-image-authentication-is-the-verifier-itself-verified)).
- `cert_a/b` are present in the GPT but **empty** on this image.

---

## 4. Dynamic partitions (`super`)

`super` uses Android dynamic partitions to host `system`, `vendor` and `product`, all protected by dm-verity. `ro.boot.dynamic_partitions=true` is set. The ramdisk's `fstab.full_gminfo37_gb` marks these `logical,first_stage_mount` (originally read as an unused build-mixin default; superseded by the evidence below).

### 4.1 Y175 hardware measurement [V] (2026-11-17, read-only, Probe08 RAM boot, `dd` of GPT + first 128 KiB of `super`)

| Item | Value |
|---|---|
| `super` | p13, LBA 741376 (byte offset 379,584,512 [C]), 18000 MiB |
| LP metadata | v10.0, geometry `gDla`, 3 slots, 64 KiB each |
| Groups | `group_sys_a`, `group_sys_b`, 8996 MiB each |
| Group + reserved arithmetic [C] | 2 x 8996 = 17992 MiB; 18000 - 17992 = 8 MiB for LP geometry/metadata |
| Logical partitions (read-only), per slot X | `system_X` 3,148,877,824 B; `vendor_X` 465,694,720 B; `product_X` 2,547,740,672 B |
| Image match | byte-identical to the Y175 package images |
| GPT | no `system_*`/`vendor_*`/`product_*` entries |
| Cmdline | stock cmdline has no `androidboot.android_dt_dir`; kf4abl appends none |

Evidence files (outside the repo): `/tmp/aaos_y175/evidence/{gpt_live.txt,super_lpdump.txt}` (no unique GUIDs or serials recorded).

Independent corroboration [V] (fastbootd `getvar all`, Y175, 2026-10-06): `dynamic-partition:true`, `super` size `0x465000000` with logical `system/vendor/product_{a,b}`, `data` `0x9C1800000`, `treble-enabled:true`, `current-slot:b`, `slot-count 2`, `max-download-size 0x10000000`.

### 4.2 Y181B live radio [V] (2026-11-12, read from `/cache` update-engine logs and package contents)

- `gm_update_engine` logs `DynamicPartitionControlAndroid.cpp:223 ... Loaded metadata from source slot A|B in /dev/block/by-name/super` on every slot-history step (02-03 through 09-28). Slot history itself: [firmware_versions.md](firmware_versions.md), [ota_update_stack.md](ota_update_stack.md).
- The package install script calls `update_dynamic_partition_config()` and `extract_logical_partition` for system (module 22), vendor (26), product (57).
- `ro.boot.dynamic_partitions=true`.
- The Y181B update package (target `SIHM22B-00499.03`, FCID `0x54f3`, `W231E-Y181.3.2`) carries a JSON dynamic-partition group config: `group_sys`: system 3228360704, vendor 466915328, product 2700648448 (ota_update_stack.md L494-503). Edify extensions used: `gmext.write_emmc_image`, `gmext.extract_logical_partition`, `gmext.update_ecu`, `gmext.switch_slot`, `gmext.update_dynamic_partition_config`.
- Y181B package logical sizes (sum 6,395,924,480 B [C]) are larger than the Y175 per-slot images (sum 6,162,313,216 B [C]); the Y181B group maximum and `super` size are not recorded in these sources.

### 4.3 Verity

`system`, `vendor`, `product` are dm-verity protected (security.md L43, L64). On live Y175 the capture recorded only `verifiedbootstate=green` and flash-lock props, with an empty `===VERITY` section, so runtime dm-verity status is not independently evidenced by that capture (boot_chain.md L187-201).

---

## 5. First-stage mount, fstab and the ACPI SSDT

| Item | Fact | Evidence |
|---|---|---|
| Ramdisk fstab | `first_stage_ramdisk/fstab.full_gminfo37_gb` (also `/vendor/etc/fstab` at runtime) | [V] |
| Real-device `acpio.img` | 2 MiB; carries an ACPI SSDT (`_HID ANDR0001`, OEM Table ID "android") whose `_DSD` describes by-name partitions on PCI eMMC `0000:00:1c.0` with `wait,slotselect,avb` flags | [V] boot-image extraction, 2026-09 |
| Module IDs | SOC_ACPIO module 0x37 = 55 decimal (85759610 / 86331630): the Android ACPIO is only the `ANDR0001` fstab/vbmeta descriptor (no USB config) | security.md L513; ota_programming_roles.md L57, L130 |
| Consumed on Y175 radio? | No. `fs_mgr` does not read the SSDT fstab: no `androidboot.android_dt_dir` on the stock cmdline | [V] Y175 |
| Consumed in QEMU real-kernel build? | No. The extracted SSDT (`ssdt_android.aml`) loads into ACPI but `ReadFstabFromDt()` fails (its nested node layout does not match this platform's flat `_DSD` properties). | [V] QEMU, 2026-09-27 |
| Mechanism that worked in QEMU | patch the ramdisk plain-text first-stage fstab: drop `logical`/`avb`, point each `first_stage_mount` entry (system/vendor/product, the three `fs_mgr` resolves before vold exists) at `/dev/block/pci/pci0000:00/0000:00:1c.0/by-name/<partition>` with `slotselect`. Other partitions keep their plain `/dev/block/by-name/...` path. The flat `/dev/block/by-name/...` path is never created by first-stage init on that kernel. | [V] QEMU |
| Boot-control in QEMU | `androidboot.slot_suffix=_a` + `slotselect` resolve partitions with no GHS VMM bootctrl | [V] QEMU |
| Real-hardware cmdline | `clocksource=tsc tsc=reliable i915.avail_planes_per_pipe=0x000003 androidboot.diskbus=1c.0 androidboot.trustyimpl=-ghs androidboot.product.hardware.sku=gv221`, plus `slot_suffix`, `verifiedbootstate`, `vbmeta.avb_version=1.1`, `hash_alg=sha256` added during AVB (boot_chain.md L152-163). No `android_dt_dir` token is listed in the documented Y181B tokens either, but the lists are partial [C]. | |
| Runtime fstab on the Y181.3.2 emulator reference | `/data` is `f2fs` with no `fileencryption=`/`metadata_encryption=` flag; the fstab carries the comment "Commented out tos and multiboot for disabling trusty" | [V] emulator, 2026-10-06 (security.md L476) |

Emulator artifacts for this mechanism (`mkstatic.py`, `patch_cpio.py`, `ssdt_noavb.aml`/`.dsl`, `fstab.patched`, `serial.log`) and the `mkdisk.py` LP `super` packing are owned by [emulator.md](emulator.md). Note the emulator's own disk layout is an LP `super` built by `mkdisk.py`; its comment "Y181 is static A/B, no super" describes only that layout (emulator.md L16).

SELinux labels relevant to storage/serial in the real-kernel build (`ttyS0` = `bluetooth_serial_device`, `ttyS1` = `ipc_serial_device`) are in [emulator.md](emulator.md).

---

## 6. Mounted filesystem sizes (Y177.6.1 runtime snapshot, superseded build)

Values as recorded in `gminfo3.7_tech_specs.md` L74-89 (units not stated in the source; consistent with MiB). Y177 snapshot only; not re-measured on Y175 or Y181B.

| Key | Value |
|---|---|
| total | 65536 |
| available | 40960 |
| data_partition | 39936 |
| data_used | 4300 |
| data_available | 35636 |
| system_partition | 2969 |
| system_used | 2785 |
| system_available | 184 |
| vendor_partition | 438 |
| vendor_used | 428 |
| vendor_available | 1 |
| product_partition | 2458 |
| product_used | 2274 |
| product_available | 184 |
| utilization_warning | `vendor_100_percent_full` |

`total` 65536 is the nominal 64 GB eMMC; the measured user area is 63,996,690,432 B (section 2).

---

## 7. Access notes on storage paths (pointers)

- Native Linux/ELK reads of the eMMC are read-only and did not mount filesystems; these are not proof of ELK flash-write permission (security.md L743-755; [elk_recovery.md](elk_recovery.md)).
- UID 1000 `system_app` shell: `test -w` succeeded for `/update_cache/update` (Y175 write confirmed 2026-10-30 with an empty temp file) and failed for `/update_cache/calibrations`, a symlink to the calibration overrides directory (ota_update_stack.md L100-107).
- UID 2000 USB ADB on Y175 returned `Permission denied` for metadata checks of `/mnt/vendor/calibration/overrides`, `/update_cache/calibrations`, `/update_cache/bootup_log/vendor/CalSets.db` (vehicle_config.md L28-36).
- Calibration database and override semantics: [vehicle_config.md](vehicle_config.md). Update staging and USB flag files: [ota_update_stack.md](ota_update_stack.md).

---

## Open conflicts

1. **Y181B `super` size.** boot_chain.md L335 and L355 give "8.6GB dynamic" for `super` (the same note at L386 calls it unverified). Y175 measures 18000 MiB twice (section 4.1). No source measures Y181B `super`; no source explains the 8.6GB figure (it does not match the Y175 group size 8996 MiB = 8.79 GiB). Treat the Y181B size as unknown.
2. **Does real Y181B hardware resolve partitions via the SSDT or the plain-text fstab?** emulator.md L48-88 and boot_chain.md L389-401 mark it unconfirmed. Y175 evidence refutes the SSDT path (no `android_dt_dir`); the Y181B update engine proves `super` is in use at runtime but not how first-stage mount resolves it. No Y181B GPT read exists.
3. **`/cache` vs `/update_cache`.** Several docs say exports were "pulled from `/cache`" (ota_programming_roles.md L145; ota_update_stack.md L159, L411; vehicle_network.md L135) while the partition map has only `update_cache` (vda25). Whether `/cache` is a bind/symlink to it or a separate mount is not established.
4. **Partition-map row evidence.** Rows other than the count (26) and p13 `super` are from the original static/boot-chain analysis, not a per-name GPT read; Y181 vs Y175 GPT identity of names, order and sizes is not verified.
5. **`vda` vs `mmcblk` numbering.** The `vda1`-`vda26` numbering in the map is the guest view; native Linux naming changed between `mmcblk2` and `mmcblk1` across boots (hardware.md L48-50). Mapping between `vdaN` and native partition indices is assumed identical (p13 `super` agrees with vda13 on Y175).
