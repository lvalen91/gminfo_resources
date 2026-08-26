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
    def addr(a): return af.getAddress(a)

    entry_addr = 0xf0a1a + 5*4  # type_tag=5
    print("jump table entry addr for type 5:", hex(entry_addr))
    flat_api.disassemble(addr(entry_addr))
    ins = listing.getInstructionAt(addr(entry_addr))
    print(hex(entry_addr), ins)
    if ins:
        flows = ins.getFlows()
        for fl in flows:
            print("  flow ->", hex(int(fl.getOffset())))
            target = int(fl.getOffset())
            it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(target), addr(target+0x60)), True)
            for i in it:
                print("     ", hex(int(i.getAddress().getOffset())), i)
