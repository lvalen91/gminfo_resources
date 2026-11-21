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

    def show(a):
        aa = addr(a)
        fn = fm.getFunctionContaining(aa)
        print("=========== 0x%x -> %s @ %s ===========" % (a, fn, fn.getEntryPoint() if fn else None))
        if fn is not None:
            res = di.decompileFunction(fn, 90, None)
            if res.decompileCompleted():
                print(res.getDecompiledFunction().getC()[:3500])
            else:
                print("decompile failed:", res.getErrorMessage())
            # xrefs to this function
            refs = program.getReferenceManager().getReferencesTo(fn.getEntryPoint())
            cnt=0
            callers=[]
            for r in refs:
                callers.append(hex(int(r.getFromAddress().getOffset())))
                cnt+=1
            print("callers(%d):" % cnt, callers[:20])
        else:
            print("(no function wrapper; nearest fn before:)")
            prev=None
            for f in fm.getFunctions(True):
                ep=f.getEntryPoint()
                if ep.getOffset() > a: break
                prev=f
            print(prev)
        print()

    for a in [0xc678e, 0xc68a6, 0xc6d06, 0xc6e1e, 0xc74fe, 0xc8fca, 0xc916e]:
        show(a)
