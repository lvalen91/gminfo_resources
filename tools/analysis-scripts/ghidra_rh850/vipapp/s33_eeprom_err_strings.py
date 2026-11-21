import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

TARGET_SNIPPETS = [
    "read eeprom error",
    "Failed to read to LngSelSignal from EEPROM",
    "Failed to read to TimeDispFormat Signal from EEPROM",
    "EEPROM Write Failure for CalGroup",
]

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    fm = program.getFunctionManager()
    refm = program.getReferenceManager()
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    dl = listing.getDefinedData(True)
    found = []
    for d in dl:
        try:
            v = d.getValue()
        except Exception:
            continue
        s = str(v) if v is not None else None
        if not s:
            continue
        for snip in TARGET_SNIPPETS:
            if snip in s:
                found.append((d.getAddress(), s))
                break

    print("matched strings:", len(found))
    caller_funcs = {}
    for addr, s in found:
        refs = refm.getReferencesTo(addr)
        callers = set()
        for r in refs:
            f = fm.getFunctionContaining(r.getFromAddress())
            if f:
                callers.add(f)
        for f in callers:
            caller_funcs.setdefault(f, []).append(s[:70])

    print("unique caller functions:", len(caller_funcs))
    for f, strs in caller_funcs.items():
        print(" fn=%s @ %s  (%d strs)" % (f.getName(), f.getEntryPoint(), len(strs)))
        for s in strs[:2]:
            print("    ", s)

    # Decompile one representative function fully to see the read-API call pattern
    reps = list(caller_funcs.keys())
    print()
    print("=== decompiling up to 3 representative callers ===")
    for f in reps[:3]:
        print("---- ", f.getName(), f.getEntryPoint(), "----")
        res = di.decompileFunction(f, 60, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:3000])
        else:
            print("decompile failed:", res.getErrorMessage())
