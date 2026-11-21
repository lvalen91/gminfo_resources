import os
import pyghidra

BIN = os.path.join(os.environ["GM_RESEARCH_ROOT"], "gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599")
PROJ_LOC = os.path.join(os.environ["GMINFO_REPO_ROOT"], "evidence/ghidra-projects")
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)

    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0x91a80), addr(0x91d00)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)
