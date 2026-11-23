#!/bin/bash
set -euo pipefail
cd /work/busybox-1.37.0
make defconfig
python3 - <<'PY'
from pathlib import Path
p=Path('.config');s=p.read_text().replace('CONFIG_MODPROBE_SMALL=y','# CONFIG_MODPROBE_SMALL is not set')
for key in ['STATIC','I2CGET','I2CSET','I2CDUMP','I2CDETECT','I2CTRANSFER','DEVMEM','LSPCI','LSUSB','HEXDUMP','XXD','TIMEOUT','FBSET','CHVT','SETFONT','DMESG','BLOCKDEV','DEPMOD','MODPROBE','FEATURE_MODPROBE_BLACKLIST','FEATURE_MODUTILS_ALIAS','FEATURE_MODUTILS_SYMBOLS']:
 s=s.replace('# CONFIG_'+key+' is not set','CONFIG_'+key+'=y')
p.write_text(s)
PY
make -j40
cp busybox /work/display-artifacts/busybox
./busybox --list > /work/display-artifacts/busybox.applets
cp .config /work/busybox.config
for name in i2cwr i2creg i2creg16 i2cscan pcimem kmsinfo kmsshow; do
 gcc -Os -static -s -Wall -Wextra /work/probe-tools/$name.c -o /work/display-artifacts/ssh_root/usr/sbin/$name
done

release=$(cat /work/out-display/include/config/kernel.release)
mkdir -p /work/display-artifacts/ssh_root/lib/modules/"$release"/extra
cp /work/display-artifacts/ssh_root/lib/modules/*.ko /work/display-artifacts/ssh_root/lib/modules/"$release"/extra/
./busybox depmod -b /work/display-artifacts/ssh_root "$release"
