import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    fm = program.getFunctionManager()
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    def addr(a):
        return af.getAddress(a)

    for ea in [0xc812e, 0xc6cb0, 0xc73f0]:
        f = fm.getFunctionAt(addr(ea))
        print("=========== %s ===========" % f)
        res = di.decompileFunction(f, 90, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:2500])
        else:
            print("fail:", res.getErrorMessage())
        print()

    print("=== does any function in program directly call FUN_000c8fc4 (shadow getter) or FUN_000c7472 via jarl elsewhere (2nd search) ===")
    # brute string-based scan of movea/mov immediate = 0x60a6 etc as 2-byte LE pattern restricted to 'movea' mnemonic
    from jpype import JArray, JByte
    mem = program.getMemory()
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
                if idx == -1: break
                found.append(start.add(idx))
                i = idx+1
        return found

    import struct
    str_addrs = [0x60a6,0x60d2,0x60fe]
    for sa in str_addrs:
        pat = struct.pack("<H", sa)  # 2-byte LE, as it'd appear in a movea imm16 field
        hits = scan_pattern(pat)
        print("2-byte scan 0x%x: %d raw hits (noisy)" % (sa, len(hits)))
        # filter to ones where preceding bytes look like movea opcode pattern seen elsewhere (0x62 XX or similar) - just print instr text if disassembled
        shown=0
        for h in hits:
            off=int(h.getOffset())
            ins = listing.getInstructionContaining(h)
            if ins is not None and ins.getMnemonicString() in ('movea','mov'):
                print("  ", hex(off), ins, "@", hex(int(ins.getAddress().getOffset())))
                shown+=1
                if shown>=6: break
