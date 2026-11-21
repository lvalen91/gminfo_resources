import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN,
    project_location=PROJ_LOC,
    project_name=PROJ_NAME,
    analyze=False,
    language="RH850:LE:32:default",
    loader="ghidra.app.util.opinion.BinaryLoader",
    program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    print("LANGUAGE:", program.getLanguage().getLanguageID())
    print("IMAGE BASE:", program.getImageBase())
    mem = program.getMemory()
    for b in mem.getBlocks():
        print(" ", b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())), b.isInitialized())
    print("file size:", int(mem.getBlocks()[0].getEnd().getOffset()) + 1)
