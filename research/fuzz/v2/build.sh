#!/bin/bash
# build.sh (corrected)
#
# Fix vs. previous draft: `system/core/libavb` is not the right repo path
# (libavb lives in external/avb) and there is no standalone `make
# libavb_static.a` target in AOSP's Soong-built tree -- confirmed by
# actually cloning the real repo and inspecting Android.bp; no matching
# make target exists. Also confirmed: this repo has NO cc_fuzz rule and no
# fuzz/ directory at HEAD -- the artifact's claim that AOSP "already ships
# libavb fuzzers (avb_vbmeta_image_fuzzer, avb_slot_verify_fuzzer)" could
# not be verified in this checkout. Rather than assume they exist
# elsewhere, this script compiles the real libavb .c sources directly with
# clang, mirroring how the host unittest (test/Android.bp) builds them.
#
# Commit pinning: the device reports `ro.boot.vbmeta.avb_version=1.2`
# (provenance-VERIFIED, live prop). Upstream external/avb's HEAD is 1.4.
# Bisected via `git log -p -- libavb/avb_version.h`: version was 1.2 from
# commit de53827b226bccef7407e4c253b0152e8d9f8e04 (2020-04-10) until
# a1fe228b86543a21739c51352f5ce72f134fccfa (2023-09-04) bumped it to 1.3.
# c0af371864984cddfb983c3b4cba42703b5ba58a (a1fe228's parent) is the last
# commit at 1.2 -- pinned below.

set -euo pipefail

AVB_COMMIT="c0af371864984cddfb983c3b4cba42703b5ba58a"
WORKDIR="$(pwd)/avb-1.2-checkout"

if [ ! -d "$WORKDIR" ]; then
    echo "[*] Cloning external/avb and checking out the 1.2-matching commit..."
    git clone https://android.googlesource.com/platform/external/avb "$WORKDIR"
    (cd "$WORKDIR" && git checkout "$AVB_COMMIT")
else
    echo "[*] Reusing existing checkout at $WORKDIR"
    (cd "$WORKDIR" && git rev-parse HEAD | grep -q "$AVB_COMMIT" || \
        { echo "[!] $WORKDIR is not at $AVB_COMMIT -- remove it and re-run"; exit 1; })
fi

LIBAVB="$WORKDIR/libavb"

# Real source list at this commit (verified: `ls libavb/*.c` at the pinned
# commit -- no avb_mldsa.c/boringssl at 1.2, that was added later).
LIBAVB_SRCS=(
    "$LIBAVB/avb_chain_partition_descriptor.c"
    "$LIBAVB/avb_cmdline.c"
    "$LIBAVB/avb_crc32.c"
    "$LIBAVB/avb_crypto.c"
    "$LIBAVB/avb_descriptor.c"
    "$LIBAVB/avb_footer.c"
    "$LIBAVB/avb_hash_descriptor.c"
    "$LIBAVB/avb_hashtree_descriptor.c"
    "$LIBAVB/avb_kernel_cmdline_descriptor.c"
    "$LIBAVB/avb_property_descriptor.c"
    "$LIBAVB/avb_rsa.c"
    "$LIBAVB/avb_slot_verify.c"
    "$LIBAVB/avb_sysdeps_posix.c"
    "$LIBAVB/avb_util.c"
    "$LIBAVB/avb_vbmeta_image.c"
    "$LIBAVB/avb_version.c"
    "$LIBAVB/sha/sha256_impl.c"
    "$LIBAVB/sha/sha512_impl.c"
)

echo "[*] Compiling libavb (host, -m32, matching target's 32-bit x86 ABI)..."
# NOTE: -m32 requires 32-bit glibc dev headers on Linux, or the
# corresponding Xcode/SDK 32-bit support on macOS -- verify your toolchain
# supports -m32 before running; this is an ASSUMPTION carried over from the
# artifact's own §5.1 recommendation, not independently re-verified here.
# -DAVB_COMPILATION: real requirement, not an invention -- confirmed via
# `grep AVB_COMPILATION Android.bp` (avb_defaults cflags). Without it every
# libavb .c file's own headers #error out ("Never include this file
# directly") even for in-library compilation; only libavb.h-based external
# consumers (avb_bundle1_fuzzer.c) get the AVB_INSIDE_LIBAVB_H path instead.
clang -m32 -O0 -g \
    -D_FILE_OFFSET_BITS=64 -D_POSIX_C_SOURCE=199309L -DAVB_COMPILATION \
    -I"$LIBAVB" \
    -fsanitize=address,fuzzer \
    "${LIBAVB_SRCS[@]}" \
    avb_bundle1_fuzzer.c \
    -o avb_fuzzer_32bit

echo "[*] Generating seed corpus..."
python3 gen_seeds.py

echo "[*] Running fuzz harness against seeds..."
./avb_fuzzer_32bit seeds/

echo "[+] Build complete. Any crash needs confirming against the actual"
echo "    .vmm1 binary / hardware before being treated as a finding --"
echo "    this harness proves the bug class exists in upstream libavb 1.2,"
echo "    not that GHS's specific build shares it (artifact §5, item 3)."
