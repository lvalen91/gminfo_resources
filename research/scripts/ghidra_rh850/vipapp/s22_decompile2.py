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
    def addr(a): return af.getAddress(a)

    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    ifc = DecompInterface()
    ifc.openProgram(program)
    monitor = ConsoleTaskMonitor()

    targets = [0xc6cb0, 0xc73f0, 0xc812e, 0xc90fc]
    for t in targets:
        fn = flat_api.getFunctionAt(addr(t))
        print("=========", hex(t), fn, "body size", fn.getBody().getNumAddresses() if fn else None, "=========")
        if fn is None:
            print("no function")
            continue
        res = ifc.decompileFunction(fn, 60, monitor)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:6000])
        else:
            print("decompile failed:", res.getErrorMessage())
        print()
