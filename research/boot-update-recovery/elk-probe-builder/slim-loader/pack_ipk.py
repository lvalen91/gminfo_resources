#!/usr/bin/env python3
# Y175 IAS/"ipk." packer. Wraps an ELF32 x86 payload in the raw IPK directory
# container that the ABL IAS loader accepts on ghs_isys_a/b.
#
# Layout mirrors the real ghs_isys image (confirmed byte-for-byte from the
# extracted GHS payload):
#   0x00  magic        "ipk."            (0x2e6b7069)
#   0x04  version      0x00040300        (v4, GHS/host-OS slot)
#   0x08  0
#   0x0c  image_size   (total file length)
#   0x10  header_size  0x2c
#   0x14  image_size   (dup)
#   0x18  checksum     (NOT consumed by the loader -- disassembly-confirmed)
#   0x1c  config_len   (length of the config string = 0x2e)
#   0x20  loadmap_ptr  (GHS-internal module table; ABL does not deref it)
#   0x24  loadmap_cnt
#   0x28  mb1_ptr      (file offset of the Multiboot1 header; loader reads magic here)
#   0x2c  config string "board=harman_info35 gm_part_number=85098662BM\n"
#   0x5c  ELF32 payload (ET_EXEC, EM_386) -- loader maps PT_LOAD, jumps e_entry
#
# Loader acceptance gates (from ABL disassembly, vaddr 0x128087e0):
#   (1) "ipk." magic @0x00   (2) MB1 magic 0x1BADB002 reachable via [0x28]
#   (3) image_size <= partition size.  No checksum, no crypto on this path.
import sys, struct

MAGIC       = 0x2e6b7069
VERSION     = 0x00040300
HEADER_SIZE = 0x2c
ELF_OFF     = 0x5c                     # fixed, matches real image
CONFIG      = b"board=harman_info35 gm_part_number=85098662BM\n"
MB1_MAGIC   = 0x1BADB002
REAL_CKSUM  = 0x5fffc6f3               # cosmetic; loader never compares it


def find_mb1(elf):
    # scan first 8 KiB of the ELF for an aligned, checksum-valid MB1 header
    for off in range(0, min(len(elf), 8192) - 12, 4):
        magic, flags, cksum = struct.unpack_from("<III", elf, off)
        if magic == MB1_MAGIC and ((magic + flags + cksum) & 0xffffffff) == 0:
            return off, flags
    raise SystemExit("ERROR: no valid Multiboot1 header in first 8 KiB of ELF")


def main():
    elf = open(sys.argv[1], "rb").read()
    if elf[:4] != b"\x7fELF" or elf[4] != 1 or elf[18] != 3:
        raise SystemExit("ERROR: payload is not an ELF32 x86 (EM_386) image")
    mb1_off, mb1_flags = find_mb1(elf)
    if mb1_flags & 0x10000:
        print("WARN: MB1 AOUT_KLUDGE set; real GHS uses flags=0x2 (ELF load)")

    if len(CONFIG) > (ELF_OFF - HEADER_SIZE):
        raise SystemExit("ERROR: config string too long for fixed 0x5c ELF offset")
    config_region = CONFIG + b"\xff" * (ELF_OFF - HEADER_SIZE - len(CONFIG))

    # body = config + ELF; then an empty (benign) loadmap the ABL does not read
    body = config_region + elf
    loadmap_off = HEADER_SIZE + len(body)
    body += b"\x00" * 16                # empty module table
    mb1_ptr = ELF_OFF + mb1_off
    total = HEADER_SIZE + len(body)
    e_entry = struct.unpack_from("<I", elf, 24)[0]

    hdr = struct.pack("<11I",
                      MAGIC, VERSION, 0, total, HEADER_SIZE, total,
                      REAL_CKSUM, len(CONFIG), loadmap_off, 0, mb1_ptr)
    out = hdr + body
    assert len(out) == total
    open(sys.argv[2], "wb").write(out)
    print("packed %s: %d bytes (ELF@0x%x, MB1@0x%x flags=0x%x, e_entry=0x%08x)"
          % (sys.argv[2], total, ELF_OFF, mb1_ptr, mb1_flags, e_entry))


if __name__ == "__main__":
    main()
