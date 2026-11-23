#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
exec podman run --rm --security-opt label=disable -v "$root:/work" localhost/elk-build-tools:repro bash /work/upstream/build-inside.sh
