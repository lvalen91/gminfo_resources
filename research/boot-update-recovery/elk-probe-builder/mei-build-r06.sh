#!/bin/bash
set -euo pipefail
cd "$HOME/gm-elk-builder"
if [ ! -d out-mei-r06 ]; then cp -a out-display out-mei-r06; fi
podman run --rm --security-opt label=disable -v "$PWD:/work" -v "$PWD/lts:/home/zeno.guest/gm-kernel-y175/lts" -v "$PWD/out-mei-r06:/home/zeno.guest/gm-kernel-y175/out-elk-linux" -v "$PWD/toolchain:/home/zeno.guest/gm-kernel-y175/aosp-clang/clang-r416183b1" localhost/elk-build-tools:repro bash -c '
set -e
export PATH=/home/zeno.guest/gm-kernel-y175/aosp-clang/clang-r416183b1/bin:$PATH
cd /home/zeno.guest/gm-kernel-y175/lts
out=/home/zeno.guest/gm-kernel-y175/out-elk-linux
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r06 -j12 modules_prepare
make O="$out" ARCH=x86_64 CC=clang CROSS_COMPILE=x86_64-linux-gnu- LOCALVERSION=-r06 M=drivers/misc/mei -j12 modules
modinfo "$out/drivers/misc/mei/mei.ko" | grep vermagic
'
