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
    mem = program.getMemory()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)

    windows = [(0x0,0x224ff),(0x68500,0x8a37f)]
    from ghidra.program.model.address import AddressSet
    total_code=0; total_data=0; total_undef=0; total_bytes=0
    for s,e in windows:
        aset = AddressSet(addr(s), addr(e))
        total_bytes += (e-s+1)
        # code bytes
        cu_iter = listing.getCodeUnits(aset, True)
        code_bytes=0; data_bytes=0
        undef_ranges = []
        cur_undef_start = None
        addr_i = s
        # iterate code units for code/data totals
        for cu in listing.getCodeUnits(aset, True):
            ln = cu.getLength()
            if cu.__class__.__name__ == 'InstructionDB' or hasattr(cu, 'getPrototype') and False:
                pass
        # simpler: use InstructionIterator and DefinedDataIterator
        instr_bytes = 0
        for ins in listing.getInstructions(aset, True):
            instr_bytes += ins.getLength()
        data_iter_bytes = 0
        for d in listing.getDefinedData(aset, True):
            data_iter_bytes += d.getLength()
        print("window", hex(s), hex(e), "size", hex(e-s+1))
        print("  instr_bytes:", instr_bytes, hex(instr_bytes))
        print("  defined_data_bytes:", data_iter_bytes, hex(data_iter_bytes))
        undef_bytes = (e-s+1) - instr_bytes - data_iter_bytes
        print("  undefined_bytes (approx):", undef_bytes, hex(undef_bytes))
        total_code += instr_bytes
        total_data += data_iter_bytes
        total_undef += undef_bytes

    print()
    print("TOTALS over both content windows:")
    print("  total_bytes:", total_bytes, hex(total_bytes))
    print("  code:", total_code, hex(total_code))
    print("  defined_data:", total_data, hex(total_data))
    print("  undefined:", total_undef, hex(total_undef))
    fm = program.getFunctionManager()
    print("  function count:", fm.getFunctionCount())
