#!/bin/sh
# Replay the local harness sequence until Ctrl-C. No capture processes are started.
set -eu
bench_tools_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bench_python="$HOME/.local/share/gminfo-bench/venv/bin/python"
if [ ! -x "$bench_python" ]; then
    echo 'Missing local bench Python environment: ~/.local/share/gminfo-bench/venv' >&2
    exit 1
fi
exec "$bench_python" -u "$bench_tools_dir/can_bench_emulator.py" replay "$@"
