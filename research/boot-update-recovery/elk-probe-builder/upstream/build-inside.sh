#!/bin/bash
set -euo pipefail
export PATH=/work/toolchain/bin:$PATH
export KBUILD_BUILD_USER=probe KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP='Tue Nov 17 12:00:00 UTC 2026'
cd /work/upstream/linux-4.19.283
out=/work/upstream/out
scripts/config --file "$out/.config" --set-str LOCALVERSION -upstream-probe02 --disable LOCALVERSION_AUTO --disable MODVERSIONS --disable MODULE_SIG --set-str SYSTEM_TRUSTED_KEYS '' --set-str INITRAMFS_SOURCE '' --set-str EXTRA_FIRMWARE 'i915/bxt_dmc_ver1_07.bin edid/harman0960p.bin' --set-str EXTRA_FIRMWARE_DIR /work/display-firmware
scripts/config --file "$out/.config" -e X86_MSR -e DEVMEM -e MTD -e SPI_MEM -e MTD_SPI_NOR -e SPI_INTEL -e SPI_INTEL_PCI -e IGB -e INTEL_MEI -e INTEL_MEI_ME -e INTEL_MEI_TXE -e TOUCHSCREEN_ATMEL_MXT -e I2C_HID -d DRM_I915_GVT -d DRM_I915_GVT_KVMGT
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- olddefconfig
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- -j40 bzImage
cp "$out/arch/x86/boot/bzImage" /work/upstream/artifacts/bzImage
make -C /work/upstream/busybox-1.37.0 mrproper
mkdir -p /work/upstream/busybox-out
cp /work/busybox.config /work/upstream/busybox-out/.config
make -C /work/upstream/busybox-1.37.0 O=/work/upstream/busybox-out oldconfig </dev/null
make -C /work/upstream/busybox-1.37.0 O=/work/upstream/busybox-out -j40
cp /work/upstream/busybox-out/busybox /work/upstream/artifacts/busybox
/work/upstream/artifacts/busybox --list > /work/upstream/artifacts/busybox.applets
gcc -Os -static -s -Wall -Wextra /work/upstream/init.c -o /work/upstream/artifacts/init
gcc -Os -static -s -Wall -Wextra -Werror /work/display-panel.c -o /work/upstream/artifacts/panel-stock
for name in vip-link vip-uart-probe elk-select; do
 gcc -Os -static -s -Wall -Wextra -Werror /work/probe-tools/$name.c -o /work/upstream/artifacts/$name
done
/work/upstream/artifacts/vip-link --selftest
/work/upstream/artifacts/elk-select --selftest
python3 /work/upstream/package.py
