#!/usr/bin/env python3
"""Build an UNSIGNED IPK execution marker around the archived ELK image.

Offline only: never opens a device or flashes storage. The entry stub writes
a marker into its own ELF segment, then jumps to ELK with registers, flags and
stack unchanged. Requires the exact archived source, not a guessed GHS layout.
Authentication remains in force; a well-formed container is not authorization.
"""
import argparse
import hashlib
from pathlib import Path
import struct

SOURCE_SHA256 = "ed6b88e24606a4c75151c4c6f72482b113f43f3356be4bd45f17a026b58f9b9a"
MARKER = b"IPK_ENTRY_PROBE_V1_EXECUTED_OK!!"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def crc32c(data, state=0xffffffff):
    """Raw x86 CRC32 instruction semantics: initial all-ones, no final XOR."""
    for byte in data:
        state ^= byte
        for _ in range(8):
            state = (state >> 1) ^ (0x82f63b78 if state & 1 else 0)
    return state


def check_ipk(data):
    require(len(data) >= 28 and data[:4] == b"ipk.", "Missing IPK header")
    require(crc32c(data[:28]) == 0, "IPK header CRC mismatch")
    payload_len, header_len = struct.unpack_from("<II", data, 12)
    end = header_len + payload_len
    require(28 <= header_len <= end and end + 4 <= len(data), "IPK bounds")
    require(crc32c(data[28:end + 4]) == 0, "IPK body CRC mismatch")
    sizes = struct.unpack_from("<" + "I" * ((header_len - 28) // 4), data, 28)
    require(sum((s + 3) & ~3 for s in sizes) == payload_len, "Component lengths")
    return header_len, sizes, end


def build(source):
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA256,
            "Source is not the archived ELK image")
    header_len, sizes, end = check_ipk(source)
    require(len(sizes) == 4 and sizes[0] == 512, "Unexpected IPK components")
    elf_offset = header_len + sizes[0]
    elf = source[elf_offset:elf_offset + sizes[1]]
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", elf)
    require(h[0][:7] == b"\x7fELF\x01\x01\x01" and h[1:3] == (2, 3),
            "Expected ELF32 little-endian i386 executable")
    entry, phoff, phsize, phnum = h[4], h[5], h[9], h[10]
    require(phsize == 32 and phoff + phsize * phnum <= len(elf), "Program table bounds")
    headers = [struct.unpack_from("<8I", elf, phoff + i * phsize) for i in range(phnum)]
    first = headers[0]
    require(first[0] == 1 and first[2] == first[3] == entry and first[4] == first[5],
            "Unexpected entry segment")
    stub_delta = (first[4] + 15) & ~15
    stub_addr = first[2] + stub_delta
    stub_file = first[1] + stub_delta
    require(len(MARKER) == 32, "Marker must be eight dwords")
    stub_size = 8 * 10 + 5
    marker_addr = (stub_addr + stub_size + 15) & ~15
    marker_file = first[1] + marker_addr - first[2]
    new_size = marker_addr + len(MARKER) - first[2]
    require(first[1] + new_size <= len(elf), "Stub exceeds ELF file")
    for segment in headers[1:]:
        if segment[0] != 1:
            continue
        require(first[2] + new_size <= segment[2] or segment[2] + segment[5] <= first[2],
                "Extended segment overlaps another memory segment")
        require(first[1] + new_size <= segment[1] or segment[1] + segment[4] <= first[1],
                "Extended segment overlaps another file segment")
    require(not any(elf[first[1] + first[4]:first[1] + new_size]), "Padding is not zero")
    stub = bytearray()
    for i in range(0, len(MARKER), 4):
        # mov dword ptr [absolute address], immediate: no GPR/flag/stack changes.
        stub += b"\xc7\x05" + struct.pack("<I", marker_addr + i) + MARKER[i:i + 4]
    stub += b"\xe9" + struct.pack("<i", entry - (stub_addr + stub_size))
    result = bytearray(source[:end + 4])
    result[5] = 0  # No signature or public-key trailer; deliberately unsigned.
    struct.pack_into("<I", result, elf_offset + 24, stub_addr)
    struct.pack_into("<II", result, elf_offset + phoff + 16, new_size, new_size)
    struct.pack_into("<I", result, elf_offset + phoff + 24, first[6] | 2)
    result[elf_offset + stub_file:elf_offset + stub_file + len(stub)] = stub
    # The marker is zero in the file. Only running the entry stub produces MARKER.
    require(result[elf_offset + marker_file:elf_offset + marker_file + 32] == bytes(32),
            "Marker must initially be clear")
    struct.pack_into("<I", result, 24, crc32c(result[:24]))
    struct.pack_into("<I", result, end, crc32c(result[28:end]))
    check_ipk(result)
    return bytes(result), dict(entry=entry, stub_addr=stub_addr, marker_addr=marker_addr,
                               stub=bytes(stub), elf_offset=elf_offset, headers=headers,
                               new_size=new_size, marker_file=marker_file)


def emulate(image, info):
    """Load the output ELF segments, execute its entry, and check the handoff."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                                  UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI,
                                  UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS,
                                  UC_X86_REG_EIP)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    header_len, sizes, _ = check_ipk(image)
    offset = header_len + ((sizes[0] + 3) & ~3)
    elf = image[offset:offset + sizes[1]]
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', elf)
    require(h[4] == info['stub_addr'], 'Output ELF entry mismatch')
    for i in range(h[10]):
        ph = struct.unpack_from('<8I', elf, h[5] + i * h[9])
        if ph[0] != 1 or not ph[5]:
            continue
        require(ph[2] == ph[3] and ph[4] <= ph[5], 'Unexpected ELF load mapping')
        require(not ph[4] or ph[1] + ph[4] <= len(elf), 'ELF segment exceeds file')
        page = ph[3] & ~4095
        limit = (ph[3] + ph[5] + 4095) & ~4095
        uc.mem_map(page, limit - page)
        if ph[4]:
            uc.mem_write(ph[3], elf[ph[1]:ph[1] + ph[4]])
    require(bytes(uc.mem_read(info['marker_addr'], 32)) == bytes(32), 'Marker preset')
    regs = [UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
            UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
            UC_X86_REG_EFLAGS]
    for i, reg in enumerate(regs):
        uc.reg_write(reg, 0x202 if reg == UC_X86_REG_EFLAGS else 0x12340000 + i * 0x100)
    before = [uc.reg_read(r) for r in regs]
    uc.emu_start(info['stub_addr'], info['entry'], count=9)
    require(uc.reg_read(UC_X86_REG_EIP) == info['entry'], "Wrong handoff address")
    require([uc.reg_read(r) for r in regs] == before, "Handoff registers/flags changed")
    require(bytes(uc.mem_read(info['marker_addr'], 32)) == MARKER, "Marker not executed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--emulate', action='store_true', help='Require Unicorn stub test')
    args = parser.parse_args()
    require(not args.output.exists(), "Refusing to overwrite existing output")
    image, info = build(args.source.read_bytes())
    if args.emulate:
        emulate(image, info)
        print('PASS: executed marker and preserved registers, flags and original entry handoff')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as output:
        output.write(image)
    print('UNSIGNED IPK bytes:', len(image))
    print('SHA256:', hashlib.sha256(image).hexdigest())
    print('Entry stub: %#x; original ELK entry: %#x; marker: %#x' %
          (info['stub_addr'], info['entry'], info['marker_addr']))
    print('After execution, ELK crashmode can read: hexdump %#x 0x20' % info['marker_addr'])
    print('Expected ASCII:', MARKER.decode())
    print('No device modified. This does not satisfy or bypass image authentication.')


if __name__ == '__main__':
    main()
