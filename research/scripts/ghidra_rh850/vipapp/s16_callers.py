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
    refmgr = program.getReferenceManager()

    for t, label in [(0xc8f6a,'CalGroup accessor'), (0x4fb74,'descriptor table fn'), (0xf0a10,'computed jump fn')]:
        a = addr(t)
        fn = flat_api.getFunctionAt(a)
        print("===", label, hex(t), fn, "===")
        refs = list(refmgr.getReferencesTo(a))
        print("  callers count:", len(refs))
        callers=set()
        for r in refs:
            fa = r.getFromAddress()
            cfn = flat_api.getFunctionContaining(fa)
            if cfn:
                callers.add((int(cfn.getEntryPoint().getOffset()), cfn.getName()))
        for e,n in sorted(callers):
            print("   ", hex(e), n)
        print()
