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
    def addr(a): return af.getAddress(a)

    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    for ea in [0x5dda6, 0x5de8e, 0x5df32]:
        f = fm.getFunctionAt(addr(ea))
        print("========", hex(ea), f, "========")
        if f is None:
            print("no function here")
            continue
        res = di.decompileFunction(f, 60, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:2500])
        else:
            print("decompile failed:", res.getErrorMessage())
        refs = refm.getReferencesTo(f.getEntryPoint())
        callers = set()
        for r in refs:
            cf = fm.getFunctionContaining(r.getFromAddress())
            if cf: callers.add(cf.getName()+"@"+str(cf.getEntryPoint()))
        print("callers:", sorted(callers)[:20], "total=", len(callers))
        print()
