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

    for wa in [0xb7a10, 0xaf1be]:
        a = addr(wa)
        fn = fm.getFunctionContaining(a)
        print("=========== WRITE SITE 0x%x -> fn %s @ %s ===========" % (wa, fn, fn.getEntryPoint() if fn else None))
        if fn is not None:
            res = di.decompileFunction(fn, 90, None)
            if res.decompileCompleted():
                code = res.getDecompiledFunction().getC()
                print(code[:4000])
            else:
                print("decompile failed:", res.getErrorMessage())
        print()
        # also raw disasm +-0x20
        it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(wa-0x20), addr(wa+0x10)), True)
        for i in it:
            print(hex(int(i.getAddress().getOffset())), i)
        print()

    print("=== byte-pattern scan for immediate 0xfebdaae2 (LE bytes E2 AA BD FE) across program memory ===")
    mem = program.getMemory()
    from ghidra.program.model.address import AddressSet
    pattern = bytes([0xE2,0xAA,0xBD,0xFE])
    found = []
    blocks = mem.getBlocks()
    for b in blocks:
        if not b.isInitialized():
            continue
        start = b.getStart()
        try:
            data = bytearray(int(b.getSize()))
            b.getBytes(start, data)
        except Exception as e:
            continue
        n = len(data)
        i = 0
        while True:
            idx = data.find(pattern, i)
            if idx == -1:
                break
            faddr = start.add(idx)
            found.append(faddr)
            i = idx+1
    print("total occurrences:", len(found))
    for f in found[:60]:
        off = int(f.getOffset())
        print(hex(off))
