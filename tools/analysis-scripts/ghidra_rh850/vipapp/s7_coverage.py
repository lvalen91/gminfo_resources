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
    mem = program.getMemory()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)

    blk = mem.getBlocks()[0]
    s = int(blk.getStart().getOffset())
    e = int(blk.getEnd().getOffset())
    from ghidra.program.model.address import AddressSet
    aset = AddressSet(addr(s), addr(e))
    total_bytes = e-s+1
    instr_bytes = 0
    for ins in listing.getInstructions(aset, True):
        instr_bytes += ins.getLength()
    data_bytes = 0
    for d in listing.getDefinedData(aset, True):
        data_bytes += d.getLength()
    undef_bytes = total_bytes - instr_bytes - data_bytes
    print("window", hex(s), hex(e), "size", hex(total_bytes))
    print("  instr_bytes:", instr_bytes, hex(instr_bytes), "%.1f%%"%(100.0*instr_bytes/total_bytes))
    print("  defined_data_bytes:", data_bytes, hex(data_bytes), "%.1f%%"%(100.0*data_bytes/total_bytes))
    print("  undefined_bytes:", undef_bytes, hex(undef_bytes), "%.1f%%"%(100.0*undef_bytes/total_bytes))
    fm = program.getFunctionManager()
    print("  function count:", fm.getFunctionCount())
