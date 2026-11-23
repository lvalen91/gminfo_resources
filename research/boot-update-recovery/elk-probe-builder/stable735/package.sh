#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
exec podman run --rm --security-opt label=disable -v "$root:/work" localhost/elk-build-tools:repro bash -ec '
gcc -Os -static -s -Wall -Wextra /work/stable735/init.c -o /work/stable735/artifacts/init
gcc -Os -static -s -Wall -Wextra -Werror /work/stable735/panel.c -o /work/stable735/artifacts/panel-stock
for name in busybox busybox.applets vip-link vip-uart-probe elk-select; do
 cp /work/upstream/artifacts/$name /work/stable735/artifacts/$name
done
python3 /work/stable735/package.py'
