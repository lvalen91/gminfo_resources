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

    print("=== raw bytes/disasm dump 0xeeec8 .. +0x300, walking by instruction ===")
    a0,a1 = addr(0xeeec8), addr(0xeeec8+0x300)
    flat_api.disassemble(a0)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0,a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== xrefs TO 0xeeec8 table base ===")
    refs = program.getReferenceManager().getReferencesTo(a0)
    for r in refs:
        print(" from", hex(int(r.getFromAddress().getOffset())), r.getReferenceType())
