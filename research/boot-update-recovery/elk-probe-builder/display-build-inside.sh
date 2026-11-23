#!/bin/bash
set -euo pipefail
root=/home/zeno.guest/gm-kernel-y175
out="$root/out-elk-linux"
export PATH="$root/aosp-clang/clang-r416183b1/bin:$PATH"
export KBUILD_BUILD_USER=probe KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=8
export KBUILD_BUILD_TIMESTAMP='Tue Nov 17 12:00:00 AKST 2026'
cd "$root/lts"
scripts/config --file "$out/.config" --set-str EXTRA_FIRMWARE 'i915/bxt_dmc_ver1_07.bin edid/harman0960p.bin ipu4_cpd_b0.bin regulatory.db regulatory.db.p7s' --set-str EXTRA_FIRMWARE_DIR /work/display-firmware
scripts/config --file "$out/.config" -e LOGO -e LOGO_LINUX_CLUT224 -e LOGO_LINUX_VGA16 -e LOGO_LINUX_MONO -e FONTS -e FONT_8x16 -e FONT_SUN12x22 -e DEBUG_FS -e INTEL_MEI -e INTEL_MEI_ME -e IGB
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r08 olddefconfig
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r08 -j40 bzImage
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r08 CONFIG_BRCMUTIL=m CONFIG_BRCMFMAC=m CONFIG_BRCMFMAC_PCIE=y CONFIG_BRCMFMAC_PROTO_MSGBUF=y KCFLAGS='-DCONFIG_BRCMFMAC_PCIE -DCONFIG_BRCMFMAC_PROTO_MSGBUF' M=drivers/net/wireless/broadcom/brcm80211 -j8 modules
cp "$out/arch/x86/boot/bzImage" /work/display-artifacts/bzImage
gcc -Os -static -s -Wall -Wextra /work/display-init.c -o /work/display-init
gcc -Os -static -s -Wall -Wextra -Werror /work/display-panel.c -o /work/display-artifacts/ssh_root/usr/sbin/panel-stock
cp "$out/drivers/net/wireless/broadcom/brcm80211/brcmutil/brcmutil.ko" "$out/drivers/net/wireless/broadcom/brcm80211/brcmfmac/brcmfmac.ko" /work/display-artifacts/ssh_root/lib/modules/
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r08 M=drivers/input/touchscreen -j8 atmel_mxt_ts.ko
cp "$out/drivers/input/touchscreen/atmel_mxt_ts.ko" /work/display-artifacts/ssh_root/lib/modules/
gcc -Os -static -s -Wall -Wextra -Werror /work/probe-tools/vip-link.c -o /work/display-artifacts/ssh_root/usr/sbin/vip-link
/work/display-artifacts/ssh_root/usr/sbin/vip-link --selftest
gcc -Os -static -s -Wall -Wextra -Werror /work/probe-tools/vip-uart-probe.c -o /work/display-artifacts/ssh_root/usr/sbin/vip-uart-probe
gcc -Os -static -s -Wall -Wextra -Werror /work/probe-tools/elk-select.c -o /work/display-artifacts/ssh_root/usr/sbin/elk-select
/work/display-artifacts/ssh_root/usr/sbin/elk-select --selftest
bash /work/display-tools-build.sh
R=/work/display-artifacts/ssh_root; mkdir -p "$R/etc/dropbear"
[ -f "$R/etc/dropbear/dropbear_ed25519_host_key" ] || LD_LIBRARY_PATH="$R/lib:$R/usr/lib" "$R/lib/ld-musl-x86_64.so.1" "$R/usr/bin/dropbearkey" -t ed25519 -f "$R/etc/dropbear/dropbear_ed25519_host_key"
python3 /work/display-package.py
