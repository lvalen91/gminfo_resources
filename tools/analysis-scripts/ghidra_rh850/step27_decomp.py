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

    def addr(a):
        return af.getAddress(a)

    targets = [0x778f2, 0x77b1a, 0xbe66]
    fns = {}
    for t in targets:
        f = fm.getFunctionContaining(addr(t))
        print(hex(t), "-> function:", f)
        if f:
            fns[t] = f

    print()
    print("=== all functions found, entry/name/body range ===")
    seen = set()
    for t,f in fns.items():
        if f.getEntryPoint() in seen:
            continue
        seen.add(f.getEntryPoint())
        print(hex(int(f.getEntryPoint().getOffset())), f.getName(), f.getBody())

    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    di = DecompInterface()
    di.openProgram(program)
    mon = ConsoleTaskMonitor()

    for ep in sorted(seen, key=lambda a: a.getOffset()):
        f = fm.getFunctionAt(ep)
        print()
        print(f"========== DECOMPILE {f.getName()} @ {hex(int(ep.getOffset()))} ==========")
        res = di.decompileFunction(f, 60, mon)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC())
        else:
            print("DECOMP FAILED:", res.getErrorMessage())
