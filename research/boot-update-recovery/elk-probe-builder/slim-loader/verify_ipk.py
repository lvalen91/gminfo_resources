#!/usr/bin/env python3
# Y175 pre-flash verifier. Replays the ABL IAS loader acceptance gates against a
# packed .ipk, then sanity-checks the ELF the loader will actually execute.
# Pure read-only. Exit non-zero on any failure so the build/flow can gate on it.
import sys, struct

PART_SIZE = 64 * 1024 * 1024           # ghs_isys_a/b = 64 MiB
MAGIC     = 0x2e6b7069
MB1_MAGIC = 0x1BADB002

def u32(d, o): return struct.unpack_from("<I", d, o)[0]

def main():
    d = open(sys.argv[1], "rb").read()
    ok = True
    def check(cond, label, detail=""):
        nonlocal ok
        print(("  [PASS] " if cond else "  [FAIL] ") + label + (("  -- " + detail) if detail else ""))
        if not cond: ok = False

    print("== Loader acceptance gates (ABL IAS @0x128087e0) ==")
    check(len(d) >= 0x2c, "file >= header size", "len=0x%x" % len(d))
    check(u32(d, 0x00) == MAGIC, "gate 1: ipk. magic @0x00",
          "got 0x%08x" % u32(d, 0x00))
    size = len(d)
    check(size <= PART_SIZE, "gate 3: image_size <= 64 MiB partition",
          "0x%x <= 0x%x" % (size, PART_SIZE))
    hdr_img = u32(d, 0x0c)
    check(hdr_img == size, "header image_size == actual file size",
          "hdr=0x%x file=0x%x" % (hdr_img, size))

    mb1_ptr = u32(d, 0x28)
    reachable = (0 <= mb1_ptr <= len(d) - 12)
    check(reachable, "MB1 pointer @0x28 in-bounds", "ptr=0x%x" % mb1_ptr)
    if reachable:
        m, fl, ck = struct.unpack_from("<III", d, mb1_ptr)
        check(m == MB1_MAGIC, "gate 2: MB1 magic 0x1BADB002 @ptr",
              "got 0x%08x" % m)
        check(((m + fl + ck) & 0xffffffff) == 0, "MB1 checksum valid",
              "flags=0x%x" % fl)
        check((fl & 0x10000) == 0, "MB1 flags=ELF-load (no a.out-kludge)",
              "flags=0x%x" % fl)

    print("== ELF payload sanity (what the loader jumps into) ==")
    elf_off = 0x5c
    check(d[elf_off:elf_off+4] == b"\x7fELF", "ELF magic @0x5c")
    if d[elf_off:elf_off+4] == b"\x7fELF":
        ei_class = d[elf_off+4]; e_machine = u32(d, elf_off+18) & 0xffff
        e_type = struct.unpack_from("<H", d, elf_off+16)[0]
        e_entry = u32(d, elf_off+24)
        e_phoff = u32(d, elf_off+28); e_phnum = struct.unpack_from("<H", d, elf_off+44)[0]
        check(ei_class == 1, "ELFCLASS32")
        check(e_machine == 3, "EM_386 (x86)", "got %d" % e_machine)
        check(e_type == 2, "ET_EXEC", "got %d" % e_type)
        check(e_phnum >= 1, "has program headers", "phnum=%d" % e_phnum)
        # entry must fall inside some PT_LOAD
        in_load = False
        for i in range(e_phnum):
            o = elf_off + e_phoff + i*32
            p_type, p_off, p_va, p_pa, p_filesz, p_memsz = struct.unpack_from("<6I", d, o)
            if p_type == 1 and p_va <= e_entry < p_va + p_memsz:
                in_load = True
        check(in_load, "e_entry inside a PT_LOAD segment", "entry=0x%08x" % e_entry)
        # MB1 header must fall inside a loaded, file-backed PT_LOAD too
        mb1_va_ok = False
        for i in range(e_phnum):
            o = elf_off + e_phoff + i*32
            p_type, p_off, p_va, p_pa, p_filesz, p_memsz = struct.unpack_from("<6I", d, o)
            if p_type == 1 and p_off <= (mb1_ptr - elf_off) < p_off + p_filesz:
                mb1_va_ok = True
        check(mb1_va_ok, "MB1 header lands in a file-backed PT_LOAD")

    print("== Result: " + ("ALL GATES PASS -- image is loader-acceptable" if ok
                            else "FAILURES PRESENT -- do NOT flash"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
