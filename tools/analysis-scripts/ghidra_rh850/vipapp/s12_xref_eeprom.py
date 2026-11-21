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
    refmgr = program.getReferenceManager()
    def addr(a): return af.getAddress(a)

    write_fail_strs = [0x60a6, 0x60d2, 0x60fe, 0x612a, 0x6156, 0x6182, 0x61ae, 0x61da,
                        0x6206, 0x6232, 0x625e, 0x628a, 0x62b6, 0x62e2, 0x630e]
    getcal_idx_str = 0x1344f

    print("=== [CAL] EEPROM Write Failure string xrefs ===")
    callers = set()
    for t in write_fail_strs:
        a = addr(t)
        refs = list(refmgr.getReferencesTo(a))
        if not refs:
            print(hex(t), "-> NO xrefs (data not defined? try align check)")
            continue
        for r in refs:
            fa = r.getFromAddress()
            fn = flat_api.getFunctionContaining(fa)
            fname = fn.getName() if fn else "NO_FUNCTION"
            faddr = hex(int(fn.getEntryPoint().getOffset())) if fn else "?"
            print(hex(t), "<- xref from", hex(int(fa.getOffset())), "in fn", fname, faddr)
            if fn: callers.add(int(fn.getEntryPoint().getOffset()))

    print()
    print("unique caller function entry points:", [hex(x) for x in sorted(callers)])

    print()
    print("=== GetCal Index string xref ===")
    a = addr(getcal_idx_str)
    refs = list(refmgr.getReferencesTo(a))
    for r in refs:
        fa = r.getFromAddress()
        fn = flat_api.getFunctionContaining(fa)
        print(hex(int(fa.getOffset())), "in fn", fn.getName() if fn else None, hex(int(fn.getEntryPoint().getOffset())) if fn else '?')
