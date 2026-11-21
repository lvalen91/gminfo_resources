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
    fm = program.getFunctionManager()
    def addr(a): return af.getAddress(a)

    for base in [0x41376, 0x77b1a]:
        print("========= context around 0x%x =========" % base)
        f = fm.getFunctionContaining(addr(base))
        print("containing function:", f, f.getEntryPoint() if f else None, f.getBody().getNumAddresses() if f else None)
        lo = addr(base - 0x120)
        hi = addr(base + 0x40)
        try:
            flat_api.disassemble(lo)
        except Exception as e:
            print("disasm exc", e)
        it = listing.getInstructions(program.getAddressFactory().getAddressSet(lo, hi), True)
        for i in it:
            print(hex(int(i.getAddress().getOffset())), i)
