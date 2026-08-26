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

    def addr(a):
        return af.getAddress(a)
    def rb(a):
        return mem.getByte(addr(a)) & 0xff
    def ru16(a):
        return rb(a) | (rb(a+1)<<8)

    base = 0x4fb8c
    print("=== descriptor entries for trim candidates 0x0AA0 / 0x0AE5 ===")
    for cid in [0xaa0, 0xae5]:
        e = base + cid*0x18
        dest_idx = ru16(e+0); f2 = ru16(e+2); src_idx = ru16(e+4); f6 = ru16(e+6); f8 = ru16(e+8)
        typ = rb(e+0xa)
        rest = bytes(rb(e+i) for i in range(0xb,0x18))
        print("0x%04x : 0x%06x : dest=0x%04x f2=0x%04x src=0x%04x f6=0x%04x f8=0x%04x type=%d rest=%s" % (
            cid, e, dest_idx, f2, src_idx, f6, f8, typ, rest.hex()))

    print()
    print("=== raw disasm around callers 0x91b40..0x91b70 (SBI 0x440/0x441 reads) ===")
    a0,a1 = addr(0x91b30), addr(0x91b80)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0,a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== function containing 0x91b48, decompiled ===")
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)
    fn = flat_api.getFunctionContaining(addr(0x91b48))
    print("fn:", fn, fn.getEntryPoint() if fn else None)
    if fn is not None:
        res = di.decompileFunction(fn, 90, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:5000])
        else:
            print("decompile failed:", res.getErrorMessage())
