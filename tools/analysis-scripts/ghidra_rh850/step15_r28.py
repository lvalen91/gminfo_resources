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
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    def addr(a):
        return af.getAddress(a)

    fn = fm.getFunctionAt(addr(0xaf04a))
    print("fn:", fn)
    print()
    print("=== raw disasm 0xaf04a .. 0xaf0e0 (prologue, find r28 source) ===")
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0xaf04a), addr(0xaf0e0)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== decompile FUN_000af04a ===")
    if fn is not None:
        res = di.decompileFunction(fn, 90, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:6000])
        else:
            print("decompile failed:", res.getErrorMessage())

    print()
    print("=== xrefs TO FUN_000af04a (0xaf04a) - who calls this reset/init fn ===")
    refs = program.getReferenceManager().getReferencesTo(addr(0xaf04a))
    cnt=0
    for r in refs:
        print(" from", hex(int(r.getFromAddress().getOffset())), r.getReferenceType())
        cnt+=1
    print("total:", cnt)
