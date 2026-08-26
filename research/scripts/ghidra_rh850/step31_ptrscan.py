import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    mem = program.getMemory()
    fm = program.getFunctionManager()
    af = program.getAddressFactory().getDefaultAddressSpace()

    def addr(a):
        return af.getAddress(a)

    from jpype import JArray, JByte

    def scan_pattern(pattern):
        found = []
        for b in mem.getBlocks():
            if not b.isInitialized():
                continue
            size = int(b.getSize())
            start = b.getStart()
            arr = JArray(JByte)(size)
            b.getBytes(start, arr)
            data = bytes(x & 0xff for x in arr)
            i = 0
            while True:
                idx = data.find(pattern, i)
                if idx == -1:
                    break
                found.append(start.add(idx))
                i = idx + 1
        return found

    print("=== scan for 32-bit LE pointer value 0x000778ea (ea 78 07 00) ===")
    f1 = scan_pattern(bytes([0xea, 0x78, 0x07, 0x00]))
    print("total:", len(f1))
    for a in f1[:40]:
        off = int(a.getOffset())
        fn = fm.getFunctionContaining(a)
        print(hex(off), "fn:", fn)

    print()
    print("=== scan for 0x000778eb (odd/thumb-like +1, ea 78 07 00 variant unlikely) skip ===")

    print()
    print("=== EEPROM string 0x60a6: scan for movhi/hi20 style split ptr construction nearby - search for byte pattern of address 0x60a6 as immediate anywhere (a6 60 00 00 LE16 or as part of movhi+andi) ===")
    f2 = scan_pattern(bytes([0xa6, 0x60]))
    print("total raw halfword matches (very noisy):", len(f2))

    print()
    print("=== does FUN_000f0a10 (CalGroup) or FUN_000eee60 (Commit) contain any jarl/jmp targeting 0x76000-0x7d000 or 0x9f000-0xa0000 range? dump their instructions ===")
    listing = program.getListing()
    for entry in (0xf0a10, 0xeee60):
        f = fm.getFunctionAt(addr(entry))
        print(f"-- function {f} body {f.getBody() if f else None}")
        if not f:
            continue
        it = listing.getInstructions(f.getBody(), True)
        for i in it:
            for r in i.getReferencesFrom():
                to = int(r.getToAddress().getOffset())
                if 0x76000 <= to <= 0x7d000 or 0x9f000 <= to <= 0xa0000:
                    print("  HIT", hex(int(i.getAddress().getOffset())), i, "->", hex(to))
