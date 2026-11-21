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

    def addr(a):
        return af.getAddress(a)

    types = [0,1,4,5,6,10,52,68,97,120,128,132,137,140,149,150,178,189,191,228]
    for t in sorted(set(types)):
        target = 0xf0a1a + t*4
        a = addr(target)
        print("========== type=%d target=0x%x ==========" % (t, target))
        try:
            flat_api.disassemble(a)
        except Exception as e:
            print("disasm exc:", e)
        it = listing.getInstructions(program.getAddressFactory().getAddressSet(a, addr(target+50)), True)
        cnt=0
        for i in it:
            print(hex(int(i.getAddress().getOffset())), i)
            cnt+=1
            if cnt>=14: break
