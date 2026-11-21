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
    fm = program.getFunctionManager()

    targets = {0x2000, 0x1fff, 0x1ffe}
    hits = []
    it = listing.getInstructions(True)  # only over already-defined instructions, no forced disasm
    total = 0
    for i in it:
        total += 1
        nops = i.getNumOperands()
        for opi in range(nops):
            try:
                scalars = i.getScalar(opi)
            except Exception:
                scalars = None
            if scalars is not None:
                v = scalars.getUnsignedValue()
                if v in targets:
                    hits.append((i.getAddress(), str(i)))
    print("total existing instructions scanned:", total)
    print("hits on 0x2000/0x1fff/0x1ffe immediate:", len(hits))
    for a, s in hits[:80]:
        f = fm.getFunctionContaining(a)
        print(hex(int(a.getOffset())), s, "  fn=", f.getName() if f else None, f.getEntryPoint() if f else "")
