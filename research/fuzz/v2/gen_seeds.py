#!/usr/bin/env python3
"""
gen_seeds.py (corrected)
Generates malformed vbmeta seeds targeting O1/O2/O3/O5-replica/O6.
Offsets are ground truth from VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md's
AvbVBMetaImageHeader/AvbDescriptor tables. All multi-byte header fields are
Big-Endian per the artifact.

Fix vs. previous draft: the O5 seed now places its fake Android boot header
at exactly the offset avb_bundle1_fuzzer.c actually reads (Data +
desc_offset, per the corrected harness's boot_header_bounds_check_REPLICA
call), instead of a location nothing in the harness inspects.
"""

import struct
import os

# Artifact: AvbVBMetaImageHeader Offsets (256 bytes)
OFF_MAGIC = 0x00
OFF_VER_MAJOR = 0x04
OFF_VER_MINOR = 0x08
OFF_AUTH_SIZE = 0x0C
OFF_AUX_SIZE = 0x14
OFF_ALGO_TYPE = 0x1C
OFF_HASH_OFF = 0x20
OFF_HASH_SZ = 0x28
OFF_SIG_OFF = 0x30
OFF_SIG_SZ = 0x38
OFF_PUBKEY_OFF = 0x40
OFF_PUBKEY_SZ = 0x48
OFF_PUBMETA_OFF = 0x50
OFF_PUBMETA_SZ = 0x58
OFF_DESC_OFF = 0x60     # Target O1; also where the harness reads for O5-replica
OFF_DESC_SZ = 0x68      # Target O1
OFF_ROLLBACK_IDX = 0x70 # Target O6 (CONFIRMED offset per artifact)
OFF_FLAGS = 0x78
OFF_ROLLBACK_LOC = 0x7C

# Artifact: AvbDescriptor offsets (generic header, common to all descriptor types)
DESC_TAG_OFF = 0x00
DESC_LEN_OFF = 0x08     # Target O3 (num_bytes_following)

# Artifact: Android boot image header offsets (BOOT_CHAIN_ANALYSIS.txt:425)
BOOT_MAGIC_OFF = 0x00      # "ANDROID!"
BOOT_KERNEL_SIZE_OFF = 0x08
BOOT_RAMDISK_SIZE_OFF = 0x10
BOOT_PAGE_SIZE_OFF = 0x24

HEADER_SIZE = 256
BUF_SIZE = HEADER_SIZE + 4096  # room for aux block + boot-header replica region


def write_be_u64(buf, offset, val):
    buf[offset:offset + 8] = struct.pack('>Q', val & 0xFFFFFFFFFFFFFFFF)


def write_be_u32(buf, offset, val):
    buf[offset:offset + 4] = struct.pack('>I', val & 0xFFFFFFFF)


def create_base_vbmeta():
    """Minimal structurally-plausible vbmeta buffer (unsigned -- these seeds
    are for the direct avb_descriptor_foreach()/boot-header-replica paths,
    not for passing avb_vbmeta_image_verify()'s signature check -- per the
    artifact, that needs a re-signed variant which requires the private
    test key, out of scope for seed generation)."""
    buf = bytearray(BUF_SIZE)
    buf[OFF_MAGIC:OFF_MAGIC + 4] = b'AVB0'
    write_be_u32(buf, OFF_VER_MAJOR, 1)
    write_be_u32(buf, OFF_VER_MINOR, 2)  # artifact correction: device is 1.2
    write_be_u64(buf, OFF_AUTH_SIZE, 0x100)
    write_be_u64(buf, OFF_AUX_SIZE, 0x400)
    write_be_u32(buf, OFF_ALGO_TYPE, 0x00000001)
    write_be_u64(buf, OFF_HASH_OFF, 0x100)
    write_be_u64(buf, OFF_HASH_SZ, 0x20)
    write_be_u64(buf, OFF_SIG_OFF, 0x120)
    write_be_u64(buf, OFF_SIG_SZ, 0x100)
    write_be_u64(buf, OFF_DESC_OFF, 0x200)
    write_be_u64(buf, OFF_DESC_SZ, 0x100)
    write_be_u64(buf, OFF_ROLLBACK_IDX, 1)
    return buf


def save_seed(name, data):
    path = f"seeds/{name}.bin"
    os.makedirs("seeds", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"[+] Generated {path}")


# --- O1: descriptors_offset / descriptors_size high-dword overflow ---

def target_O1_desc_off_highdword():
    buf = create_base_vbmeta()
    # {high=0xFFFFFFFF, low=0xFFFFFFF8} per artifact §3.1 case 2
    write_be_u64(buf, OFF_DESC_OFF, 0xFFFFFFFF_FFFFFFF8)
    save_seed("O1_desc_off_highdword", bytes(buf))


def target_O1_desc_sz_highdword():
    buf = create_base_vbmeta()
    write_be_u64(buf, OFF_DESC_SZ, 0x00000001_00000000)
    save_seed("O1_desc_sz_highdword", bytes(buf))


def target_O1_desc_off_smallwrap():
    """{low=0, high=1}: offset that's astronomically large as a true u64 but
    would look small if the check truncates to 32 bits first."""
    buf = create_base_vbmeta()
    write_be_u64(buf, OFF_DESC_OFF, 0x00000001_00000000)
    save_seed("O1_desc_off_smallwrap", bytes(buf))


# --- O2: auth_block_size + aux_block_size total-length overflow ---

def target_O2_total_len_overflow():
    buf = create_base_vbmeta()
    write_be_u64(buf, OFF_AUTH_SIZE, 0x80000000)
    write_be_u64(buf, OFF_AUX_SIZE, 0x80000000)
    save_seed("O2_total_len_overflow", bytes(buf))


# --- O3: descriptor num_bytes_following overflow / non-%8 ---

def target_O3_desc_payload_overflow():
    buf = create_base_vbmeta()
    desc_start = 0x200
    write_be_u64(buf, desc_start + DESC_TAG_OFF, 0x68736168)  # "hash" tag, AOSP hash-descriptor convention
    write_be_u64(buf, desc_start + DESC_LEN_OFF, 0xFFFFFFFF_FFFFFFFF)
    save_seed("O3_desc_payload_overflow", bytes(buf))


def target_O3_non_div8():
    buf = create_base_vbmeta()
    desc_start = 0x200
    write_be_u64(buf, desc_start + DESC_TAG_OFF, 0x68736168)
    write_be_u64(buf, desc_start + DESC_LEN_OFF, 0x00000000_0000000F)
    save_seed("O3_non_div8", bytes(buf))


# --- O5-replica: boot image header bound check ---
# FIX vs. previous draft: avb_bundle1_fuzzer.c's boot_header_bounds_check_
# REPLICA() reads from `Data + desc_offset` (the header's descriptors_offset
# field, @ 0x60). So the fake boot header must live exactly there for the
# harness to ever touch these bytes -- previously it was written to the
# same 0x200 offset as the descriptor seeds but nothing read it from there.

def _write_boot_header_at(buf, off, kernel_size, ramdisk_size, page_size):
    buf[off:off + 8] = b'ANDROID!'
    write_be_u32(buf, off + BOOT_KERNEL_SIZE_OFF, kernel_size)
    write_be_u32(buf, off + BOOT_RAMDISK_SIZE_OFF, ramdisk_size)
    write_be_u32(buf, off + BOOT_PAGE_SIZE_OFF, page_size)


def target_O5_boot_hdr_page_size_zero():
    buf = create_base_vbmeta()
    desc_off = 0x200
    write_be_u64(buf, OFF_DESC_OFF, desc_off)  # harness reads boot hdr from here
    _write_boot_header_at(buf, desc_off, kernel_size=0x1000, ramdisk_size=0x1000, page_size=0)
    save_seed("O5_boot_hdr_page_size_zero", bytes(buf))


def target_O5_boot_hdr_kernel_size_wrap():
    buf = create_base_vbmeta()
    desc_off = 0x200
    write_be_u64(buf, OFF_DESC_OFF, desc_off)
    _write_boot_header_at(buf, desc_off, kernel_size=0xFFFFF000, ramdisk_size=0x1000, page_size=0x1000)
    save_seed("O5_boot_hdr_kernel_size_wrap", bytes(buf))


def target_O5_boot_hdr_page_size_huge():
    buf = create_base_vbmeta()
    desc_off = 0x200
    write_be_u64(buf, OFF_DESC_OFF, desc_off)
    _write_boot_header_at(buf, desc_off, kernel_size=0x1000, ramdisk_size=0x1000, page_size=0x80000000)
    save_seed("O5_boot_hdr_page_size_huge", bytes(buf))


# --- O6: rollback_index high-dword truncation ---

def target_O6_rollback_highdword():
    buf = create_base_vbmeta()
    write_be_u64(buf, OFF_ROLLBACK_IDX, 0x00000001_00000000)
    save_seed("O6_rollback_highdword", bytes(buf))


# --- T1: TOCTOU placeholder (hardware/emulation-only per Trust Filter Rule 5) ---

def target_T1_toctou_placeholder():
    """Structurally valid seed. Cannot exercise the actual TOCTOU on a host
    harness -- the race depends on whether the real target verifies a
    private copy vs. the live DMA/eMMC buffer, a property of the
    surrounding hypervisor, not of libavb itself. Kept only as a documented
    marker, not a functional test case."""
    buf = create_base_vbmeta()
    save_seed("T1_toctou_placeholder", bytes(buf))


if __name__ == "__main__":
    target_O1_desc_off_highdword()
    target_O1_desc_sz_highdword()
    target_O1_desc_off_smallwrap()
    target_O2_total_len_overflow()
    target_O3_desc_payload_overflow()
    target_O3_non_div8()
    target_O5_boot_hdr_page_size_zero()
    target_O5_boot_hdr_kernel_size_wrap()
    target_O5_boot_hdr_page_size_huge()
    target_O6_rollback_highdword()
    target_T1_toctou_placeholder()
