#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")" && pwd)
exec podman run --rm --security-opt label=disable \
 -v "$root:/work" \
 -v "$root/lts:/home/zeno.guest/gm-kernel-y175/lts" \
 -v "$root/out-display:/home/zeno.guest/gm-kernel-y175/out-elk-linux" \
 -v "$root/toolchain:/home/zeno.guest/gm-kernel-y175/aosp-clang/clang-r416183b1" \
 localhost/elk-build-tools:repro bash /work/display-build-inside.sh
