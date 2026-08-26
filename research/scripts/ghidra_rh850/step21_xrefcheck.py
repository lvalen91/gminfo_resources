import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    refm = program.getReferenceManager()

    def addr(a):
        return af.getAddress(a)

    for ea in [0xc812e, 0xc6cb0, 0xc73f0, 0xc90fc]:
        refs = refm.getReferencesTo(addr(ea))
        cnt=0
        print("=== ALL xrefs to 0x%x ===" % ea)
        for r in refs:
            print(" from", hex(int(r.getFromAddress().getOffset())), r.getReferenceType())
            cnt+=1
        print("total:", cnt)
