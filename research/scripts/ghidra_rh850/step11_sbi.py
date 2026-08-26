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

    def addr(a):
        return af.getAddress(a)
    def rb(a):
        return mem.getByte(addr(a)) & 0xff
    def ru16(a):
        return rb(a) | (rb(a+1)<<8)

    base = 0x4fb8c
    print("=== descriptor entries for 0x43e..0x444 ===")
    for cid in [0x43e,0x43f,0x440,0x441,0x442,0x443,0x444]:
        e = base + cid*0x18
        dest_idx = ru16(e+0); f2 = ru16(e+2); src_idx = ru16(e+4); f6 = ru16(e+6); f8 = ru16(e+8)
        typ = rb(e+0xa)
        print("0x%04x : entry=0x%06x : dest=0x%04x f2=0x%04x src=0x%04x f6=0x%04x f8=0x%04x type=%d" % (
            cid, e, dest_idx, f2, src_idx, f6, f8, typ))

    print()
    print("=== what function (if any) contains 0x91b48 ===")
    a = addr(0x91b48)
    fn = fm.getFunctionContaining(a)
    print("containing fn:", fn)
    blk = listing.getInstructionContaining(a)
    print("instr:", blk)
    # find function before this address
    fn_before = fm.getFunctionBefore(a) if hasattr(fm,'getFunctionBefore') else None
    print("fn_before:", fn_before)
    it = fm.getFunctions(True)
    prev = None
    for f in it:
        ep = f.getEntryPoint()
        if ep.getOffset() > 0x91b48:
            print("first fn after 0x91b48:", f, hex(int(ep.getOffset())))
            break
        prev = f
    print("last fn before/at 0x91b48 in iteration:", prev, hex(int(prev.getEntryPoint().getOffset())) if prev else None)

    print()
    print("=== wider raw disasm 0x91a80 .. 0x91be0 to find function start / call context ===")
    a0,a1 = addr(0x91a80), addr(0x91be0)
    it2 = listing.getInstructions(program.getAddressFactory().getAddressSet(a0,a1), True)
    for i in it2:
        print(hex(int(i.getAddress().getOffset())), i)
