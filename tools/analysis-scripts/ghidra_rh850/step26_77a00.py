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
    refmgr = program.getReferenceManager()

    def addr(a):
        return af.getAddress(a)

    print("========== LEVEL 1: disasm 0x77800..0x77B80 (table region + surrounding dispatcher code) ==========")
    a0, a1 = addr(0x778f0), addr(0x77b80)
    flat_api.disassemble(a0)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0, a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("========== raw table bytes 0x77A00..0x77AA8 as u32 LE (jr targets encoded how?) ==========")
    ba = bytearray(0x77AA8 - 0x77A00 + 0x10)
    mem.getBytes(addr(0x77A00), ba)
    print(ba.hex())
