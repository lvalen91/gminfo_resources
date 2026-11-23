#!/bin/bash
set -euo pipefail
cd /tmp/elk-native/lts
mkdir -p /tmp/elk-native/out
cp /tmp/elk-native/kernel.config /tmp/elk-native/out/.config
scripts/config --file /tmp/elk-native/out/.config --disable GM_SIGNATURE --disable MODULE_SIG --disable SYSTEM_TRUSTED_KEYRING
export PATH="/tmp/elk-native/toolchain/bin:$PATH"
export KBUILD_BUILD_USER=probe KBUILD_BUILD_HOST=builder
make O=/tmp/elk-native/out ARCH=x86_64 CC=clang HOSTCC='gcc -std=gnu11' olddefconfig
make O=/tmp/elk-native/out ARCH=x86_64 CC=clang HOSTCC='gcc -std=gnu11' -j40 bzImage
sha256sum /tmp/elk-native/out/arch/x86/boot/bzImage
