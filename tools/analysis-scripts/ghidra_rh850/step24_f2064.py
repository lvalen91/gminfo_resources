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
    fm = program.getFunctionManager()
    refm = program.getReferenceManager()

    def addr(a):
        return af.getAddress(a)

    for ea in [0xf2064, 0xf1ce8]:
        refs = refm.getReferencesTo(addr(ea))
        cnt=0
        for r in refs: cnt+=1
        f = fm.getFunctionAt(addr(ea))
        print("0x%x fn=%s xref_count=%d" % (ea, f, cnt))

    print()
    print("=== which function CONTAINS 0xef0d0 (the di/critsec block)? ===")
    fn = fm.getFunctionContaining(addr(0xef0d0))
    print(fn, fn.getEntryPoint() if fn else None)
    if fn:
        refs = refm.getReferencesTo(fn.getEntryPoint())
        cnt=0
        callers=[]
        for r in refs:
            callers.append(hex(int(r.getFromAddress().getOffset())))
            cnt+=1
        print("callers:", cnt, callers[:10])
