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
    from ghidra.program.model.address import AddressSet

    aset = AddressSet(addr(0x0), addr(0xFFFFF))
    hits = 0
    for ins in listing.getInstructions(aset, True):
        mnem = ins.getMnemonicString()
        if 'mov' in mnem.lower():
            nops = ins.getNumOperands()
            for i in range(nops):
                rep = ins.getDefaultOperandRepresentation(i)
                if rep == 'tp':
                    for j in range(nops):
                        if j==i: continue
                        try:
                            sc = ins.getScalar(j)
                        except Exception:
                            sc = None
                        rep2 = ins.getDefaultOperandRepresentation(j)
                        print(hex(int(ins.getAddress().getOffset())), ins, "| dest_is_tp op", i, "other_op", j, rep2, sc)
                        hits += 1
    print("total mov-to-tp hits:", hits)
