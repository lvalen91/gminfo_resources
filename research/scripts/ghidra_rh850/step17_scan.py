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
    mem = program.getMemory()
    fm = program.getFunctionManager()

    from jpype import JArray, JByte

    def addr(a):
        return af.getAddress(a)

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

    print("=== scan for 0xfebdaae2 immediate (E2 AA BD FE) ===")
    f1 = scan_pattern(bytes([0xE2,0xAA,0xBD,0xFE]))
    print("total:", len(f1))
    for a in f1[:80]:
        off = int(a.getOffset())
        fn = fm.getFunctionContaining(a)
        print(hex(off), "fn:", fn)

    print()
    print("=== scan for 0xfebd3e06 immediate (06 3e bd fe) - cross-check known writers/readers use split movhi+disp, expect FEW/no hits ===")
    f2 = scan_pattern(bytes([0x06,0x3e,0xbd,0xfe]))
    print("total:", len(f2))
    for a in f2[:40]:
        print(hex(int(a.getOffset())))
