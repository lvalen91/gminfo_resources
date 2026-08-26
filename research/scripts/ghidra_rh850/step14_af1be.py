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

    def addr(a):
        return af.getAddress(a)

    a = addr(0xaf1be)
    print("containing fn:", fm.getFunctionContaining(a))
    prev = None
    for f in fm.getFunctions(True):
        ep = f.getEntryPoint()
        if ep.getOffset() > 0xaf1be:
            print("first fn after:", f, hex(int(ep.getOffset())))
            break
        prev = f
    print("last fn before/at:", prev, hex(int(prev.getEntryPoint().getOffset())) if prev else None)

    print()
    print("=== wide raw disasm 0xaf0e0 .. 0xaf240 (find prologue / where r28 comes from) ===")
    a0,a1 = addr(0xaf0e0), addr(0xaf240)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0,a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)
