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
    def addr(a): return af.getAddress(a)
    from ghidra.program.model.address import AddressSet

    windows = [(0x0,0x224ff),(0x68500,0x8a37f)]
    out = open("/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850/vipboot/all_disasm.txt","w")
    for s,e in windows:
        aset = AddressSet(addr(s), addr(e))
        for ins in listing.getInstructions(aset, True):
            fn = flat_api.getFunctionContaining(ins.getAddress())
            fname = fn.getName() if fn else "-"
            out.write("%08x %-16s %s\n" % (int(ins.getAddress().getOffset()), fname, str(ins)))
    out.close()
    print("done")
