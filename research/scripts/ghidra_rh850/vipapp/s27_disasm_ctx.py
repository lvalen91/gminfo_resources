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
    def addr(a): return af.getAddress(a)

    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0x41350), addr(0x413f0)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== FUN_00061b5e decompile ===")
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    ifc = DecompInterface()
    ifc.openProgram(program)
    monitor = ConsoleTaskMonitor()
    fn = flat_api.getFunctionAt(addr(0x61b5e))
    print(fn)
    res = ifc.decompileFunction(fn, 60, monitor)
    if res.decompileCompleted():
        print(res.getDecompiledFunction().getC()[:3000])
    else:
        print("fail:", res.getErrorMessage())
