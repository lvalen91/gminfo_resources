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

    print("=== bytes at 0xf0a1a (first 0x80) as hex ===")
    ba = bytearray(0x80)
    mem.getBytes(addr(0xf0a1a), ba)
    print(ba.hex())

    print()
    print("=== disasm 0xf0a1a .. +0x80, walking by instruction ===")
    a0, a1 = addr(0xf0a1a), addr(0xf0a1a+0x80)
    # ensure disassembled
    cu = listing.getCodeUnitAt(a0)
    it = listing.getCodeUnits(program.getAddressFactory().getAddressSet(a0, a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)
