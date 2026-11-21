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

    for t,label in [(0xc812e,'decode-buffer-into-shadow'), (0xc90fc,'shadow-copy-commit'),
                     (0xc6cb0,'sibling-A'), (0xc73f0,'sibling-B')]:
        a = addr(t)
        print("===", label, hex(t), "===")
        refs = list(refmgr.getReferencesTo(a))
        callers=set()
        for r in refs:
            fa = r.getFromAddress()
            cfn = flat_api.getFunctionContaining(fa)
            if cfn:
                callers.add((int(cfn.getEntryPoint().getOffset()), cfn.getName()))
            else:
                callers.add((int(fa.getOffset()), "NO_FN@"+hex(int(fa.getOffset()))))
        print(" caller count:", len(callers))
        for e,n in sorted(callers)[:30]:
            print("   ", hex(e), n)
        print()
