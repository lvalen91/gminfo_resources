import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

targets = set([0x60a6, 0x60d2, 0x60fe, 0x612a, 0x6156, 0x6182, 0x61ae, 0x61da,
               0x6206, 0x6232, 0x625e, 0x628a, 0x62b6, 0x62e2, 0x630e, 0x1344f])

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)
    from ghidra.program.model.address import AddressSet

    s, e = 0x0, 0xFFFFF
    aset = AddressSet(addr(s), addr(e))
    hits = []
    count = 0
    for ins in listing.getInstructions(aset, True):
        count += 1
        nops = ins.getNumOperands()
        for i in range(nops):
            try:
                scal = ins.getScalar(i)
            except Exception:
                scal = None
            if scal is not None:
                v = scal.getUnsignedValue()
                if v in targets:
                    hits.append((int(ins.getAddress().getOffset()), str(ins), v))
    print("scanned instructions:", count)
    print("scalar-operand hits:", len(hits))
    for a,s_,v in hits:
        fn = flat_api.getFunctionContaining(addr(a))
        print(hex(a), "fn=%s" % (fn.getName() if fn else None), hex(v), "|", s_)
