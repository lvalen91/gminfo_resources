import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    import sys
    targets = [int(x,16) for x in sys.argv[1:]]
    for t in targets:
        a = addr(t)
        fn = flat_api.getFunctionAt(a)
        if fn is None:
            fn = flat_api.getFunctionContaining(a)
        print("=========== ", hex(t), fn, "===========")
        if fn is None:
            print("no function")
            continue
        res = di.decompileFunction(fn, 60, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:5000])
        else:
            print("decompile failed:", res.getErrorMessage())
        print()
