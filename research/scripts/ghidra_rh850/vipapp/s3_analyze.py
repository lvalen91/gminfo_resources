import pyghidra, time

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    t0 = time.time()
    print("starting analyzeAll...")
    flat_api.analyzeAll(program)
    print("analyzeAll done in %.1fs" % (time.time()-t0))
    fm = program.getFunctionManager()
    print("function count:", fm.getFunctionCount())
