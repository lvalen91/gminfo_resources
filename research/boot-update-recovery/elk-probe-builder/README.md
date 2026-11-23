# ELK-Linux probe/display bench — build tooling

Custom source for the owner's bench RAM-boot Linux image used to drive the display/GPU and
probe the VIP/ABL/GHS boot chain directly on the bench Harman Info 3.7 unit (see
[y175-ghs-loader-model work](../GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) and the Y175 custom-loader
findings for context). Pulled from the build workstation (`macpro`) on 2026-11-23.

**Scope — only the custom/project code, not the base kernel.** The actual build also pulls and
extracts pristine Linux kernel source (4.19.283, 7.3.5) and BusyBox 1.37.0 tarballs; that vanilla
upstream source is intentionally **not** checked in here — it's freely available from
kernel.org / busybox.net at the versions pinned in the scripts below. Build artifacts, boot
images, firmware blobs, and raw research dumps from the same workstation are likewise excluded.

## Layout

- `init.c`, `display-init.c`, `display-panel.c` — custom PID-1 / display-bringup init for the RAM
  boot image. `display-init.c` is the current version: brings up `eth0.5` (VLAN 5), assigns
  `10.0.0.10/24`, starts `dropbear -R` and `udhcpd` automatically at boot.
- `build-display.sh`, `build-native.sh`, `display-build-inside.sh`, `display-tools-build.sh`,
  `rebuild-inside.sh`, `elk_linux_native_build.sh`, `mei-build-r06.sh` — build drivers/scripts for
  the various image variants (display, native, MEI probe).
- `package.py`, `display-package.py`, `display-qemu-check.py` — image packaging and a QEMU-based
  sanity check before flashing to real hardware.
- `kernel.config`, `probe03.config`, `busybox.config` — the kernel/BusyBox `.config`s used to
  build the images (apply on top of the pristine tarballs above).
- `probe-tools/` — standalone bench diagnostic tools run from the probe image: I2C
  (`i2creg*.c`, `i2cscan.c`, `i2cwr.c`), KMS/DRM (`kmsinfo.c`, `kmsshow.c`, `drm_min.h`,
  `gpu-render-test.c`), PCI/MMIO (`pcimem.c`), and VIP UART/link inspection
  (`vip-link.c`, `vip-link-inspect.c`, `vip-uart-probe.c`, `elk-select.c`).
- `ifwi-window-ro/` — kernel module source exposing a read-only IFWI SPI window.
- `msr-audit/` — `fpf-read.c`, a small tool to read Apollo Lake MSRs/FPF fuse state.
- `slim-loader/` — the custom IAS/`ipk.` loader shim and tooling built to test direct GHS-slot
  boot control: `boot.S`/`boot_min.S` + `linker.ld` (the shim itself, 64-bit long-mode entry per
  the loader-handoff finding), `pack_ipk.py` (ELF → `ipk.` container packer, CRC32C header/body),
  `verify_ipk.py` (replays the ABL loader's acceptance gates). See the Y175 memory notes for the
  milestone history (control-transfer proven, GHS RSA-2048/SHA-256 signature enforcement
  confirmed by controlled A/B experiment).
- `stable735/`, `upstream/` — the per-kernel-version build driver scripts and init variants for
  the two kernel lines tested (Linux 7.3.5 "stable735" and Linux 4.19.283 "upstream"); the
  matching kernel source trees themselves are not included (see Scope above).
