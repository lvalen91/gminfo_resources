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

    a = addr(0xc916c)
    ins = listing.getInstructionAt(a)
    print("instr:", ins, "len:", ins.getLength())
    ba = bytearray(ins.getLength())
    mem.getBytes(a, ba)
    print("bytes:", ba.hex())

    # also next instr (add r11,r12) for context
    a2 = addr(0xc9110)
    ins2 = listing.getInstructionAt(a2)
    print("instr2 (mov 0x4fb8c,r14):", ins2, "len:", ins2.getLength())
    ba2 = bytearray(ins2.getLength())
    mem.getBytes(a2, ba2)
    print("bytes2:", ba2.hex())
