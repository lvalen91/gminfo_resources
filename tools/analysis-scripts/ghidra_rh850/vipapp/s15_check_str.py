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

    for t in [0x60a6, 0x5f00, 0x5000, 0x4fb8c, 0xf0a1a, 0x13463, 0xc8f6a]:
        a = addr(t)
        cu = listing.getCodeUnitAt(a)
        cont = listing.getCodeUnitContaining(a)
        ins = listing.getInstructionAt(a)
        d = listing.getDefinedDataAt(a)
        fn = flat_api.getFunctionContaining(a)
        print(hex(t), "codeUnitAt=", cu, "| definedDataAt=", d, "| instrAt=", ins, "| fnContaining=", fn)
