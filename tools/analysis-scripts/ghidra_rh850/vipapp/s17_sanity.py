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

    ins = listing.getInstructionAt(addr(0xe5930))
    print("instr @0xe5930:", ins)
    print("numOperands:", ins.getNumOperands())
    for i in range(ins.getNumOperands()):
        print(" op", i, "repr:", ins.getDefaultOperandRepresentation(i))
        try:
            sc = ins.getScalar(i)
            print("   scalar:", sc)
        except Exception as ex:
            print("   scalar err:", ex)
        try:
            objs = ins.getOpObjects(i)
            print("   opObjects:", list(objs))
        except Exception as ex:
            print("   opObjects err:", ex)

    # also check references from this instruction directly
    refs = ins.getReferencesFrom()
    print("refsFrom:", list(refs))
