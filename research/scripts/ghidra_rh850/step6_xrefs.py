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

    def addr(a):
        return af.getAddress(a)

    for target in [0xc8f6a, 0xc90c4]:
        print("=== xrefs TO 0x%x ===" % target)
        refs = refmgr.getReferencesTo(addr(target))
        cnt=0
        for r in refs:
            fromAddr = r.getFromAddress()
            fn = flat_api.getFunctionContaining(fromAddr)
            print(" from", hex(int(fromAddr.getOffset())), "in fn", fn, "type", r.getReferenceType())
            cnt+=1
        print("total refs:", cnt)
        print()

    # find the GetCal / CalGroup strings
    st = program.getListing().getDefinedData(True)
    print("=== searching defined strings for 'CalGroup' / 'GetCal' ===")
    from ghidra.program.model.data import StringDataType
    found=0
    for d in st:
        try:
            if d.hasStringValue():
                v = d.getValue()
                if v and ("CalGroup" in str(v) or "GetCal" in str(v)):
                    print(hex(int(d.getAddress().getOffset())), repr(str(v))[:120])
                    found+=1
                    if found>30: break
        except Exception:
            pass
    print("string hits:", found)
