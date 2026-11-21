import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
    nested_project_location=False,
) as flat_api:
    program = flat_api.getCurrentProgram()
    print("PROGRAM NAME:", program.getName())
    print("LANGUAGE:", program.getLanguage().getLanguageID())
    print("IMAGE BASE:", program.getImageBase())
    mem = program.getMemory()
    print("blocks:")
    for b in mem.getBlocks():
        print(" ", b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())), b.isInitialized())
    fm = program.getFunctionManager()
    print("function count:", fm.getFunctionCount())
