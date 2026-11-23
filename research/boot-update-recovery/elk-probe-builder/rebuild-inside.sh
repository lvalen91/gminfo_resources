#!/bin/bash
set -euo pipefail
root=/home/zeno.guest/gm-kernel-y175
out="$root/out-elk-linux"
mkdir -p "$out/certs"
cp /work/reference/vm.config "$out/.config"
cp /work/reference/x509.genkey "$out/certs/x509.genkey"
openssl x509 -inform DER -in /work/reference/signing_key.x509 -out "$out/certs/signing_key.pem"
export PATH="$root/aosp-clang/clang-r416183b1/bin:$PATH"
export KBUILD_BUILD_USER=probe KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=3
export KBUILD_BUILD_TIMESTAMP='Tue Nov 17 03:44:33 AKST 2026'
cd "$root/lts"
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=+ -j40 bzImage
cd "$out"
printf 'dir /dev 0755 0 0\nnod /dev/console 0600 0 0 c 5 1\ndir /root 0700 0 0\n' > /work/inputs/builtin-initramfs.list
usr/gen_init_cpio -t $((0x6AC743B8)) /work/inputs/builtin-initramfs.list > usr/initramfs_data.cpio
cd "$root/lts"
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=+ -j40 bzImage
cp "$out/arch/x86/boot/bzImage" /work/artifacts/bzImage
# Retain identical prebuilt PID1, BusyBox and SSH binaries as archive inputs.
cp /work/reference/elk_linux_init /work/init
python3 /work/package.py
for f in bzImage initramfs.cpio.gz boot.img; do
 cmp "/work/artifacts/$f" "/work/reference/$f"
 sha256sum "/work/artifacts/$f"
done
