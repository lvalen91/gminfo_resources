import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    refmgr = program.getReferenceManager()
    def addr(a): return af.getAddress(a)

    targets = [0x1906, 0x2af2, 0x697be, 0x6a9aa, 0x1376, 0x2bda, 0x69232, 0x6aa92]
    for t in targets:
        a = addr(t)
        d = listing.getDataAt(a)
        print(hex(t), "data:", d, repr(str(d.getValue())[:60]) if d else None)
        refs = refmgr.getReferencesTo(a)
        cnt=0
        for r in refs:
            fromAddr = r.getFromAddress()
            fn = flat_api.getFunctionContaining(fromAddr)
            print("   xref from", hex(int(fromAddr.getOffset())), "fn:", fn)
            cnt+=1
        if cnt==0:
            print("   (no xrefs found)")
        print()
