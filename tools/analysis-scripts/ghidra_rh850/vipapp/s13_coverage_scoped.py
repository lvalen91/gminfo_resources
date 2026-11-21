import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"
raw = open(BIN,'rb').read()

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)
    from ghidra.program.model.address import AddressSet

    # true content window: 0x0 - 0xFFFFF (real content), erased tail 0x100000-0x1d8381, footer 0x1d8382-0x1d8385
    s, e = 0x0, 0xFFFFF
    aset = AddressSet(addr(s), addr(e))
    total = e-s+1
    instr_bytes = sum(ins.getLength() for ins in listing.getInstructions(aset, True))
    data_bytes = sum(d.getLength() for d in listing.getDefinedData(aset, True))
    used = AddressSet()
    for ins in listing.getInstructions(aset, True):
        used.add(ins.getMinAddress(), ins.getMaxAddress())
    for d in listing.getDefinedData(aset, True):
        used.add(d.getMinAddress(), d.getMaxAddress())
    undef = aset.subtract(used)

    # classify undefined gaps in this window
    pad0=padff=stringb=coderesid=0
    residue_list = []
    for r in undef.getAddressRanges():
        gs = int(r.getMinAddress().getOffset())
        ge = int(r.getMaxAddress().getOffset())
        b = raw[gs:ge+1]
        if all(x==0 for x in b): pad0 += len(b)
        elif all(x==0xff for x in b): padff += len(b)
        else:
            printable = sum(1 for c in b if 32<=c<127)
            nul = sum(1 for c in b if c==0)
            if len(b)>0 and (printable+nul)/len(b) > 0.85 and printable > len(b)*0.5:
                stringb += len(b)
            else:
                coderesid += len(b)
                residue_list.append((gs,ge,len(b)))

    print("=== SCOPED window 0x0-0xFFFFF (real content, %d bytes) ===" % total)
    print("  instr_bytes:      %8d  %.2f%%" % (instr_bytes, 100.0*instr_bytes/total))
    print("  defined_data:     %8d  %.2f%%" % (data_bytes, 100.0*data_bytes/total))
    print("  undef pad0:       %8d  %.2f%%" % (pad0, 100.0*pad0/total))
    print("  undef padff:      %8d  %.2f%%" % (padff, 100.0*padff/total))
    print("  undef string-like:%8d  %.2f%%" % (stringb, 100.0*stringb/total))
    print("  undef RESIDUE(code-candidate, unclassified): %8d  %.2f%%" % (coderesid, 100.0*coderesid/total))
    print()
    print("  function count:", program.getFunctionManager().getFunctionCount())
    print()
    print("=== whole-file accounting ===")
    print("  real content window:     0x0        - 0xFFFFF   (%d bytes, %.2f%% of file)" % (total, 100.0*total/len(raw)))
    print("  erased flash (0xFF pad): 0x100000   - 0x1D8381  (%d bytes, %.2f%% of file)" % (0x1d8381-0x100000+1, 100.0*(0x1d8381-0x100000+1)/len(raw)))
    print("  footer (CRC?):           0x1D8382   - 0x1D8385  (4 bytes)")
    print("  total file:", len(raw))

    print()
    print("=== residue ranges (top 40 by size) within real-content window ===")
    residue_list.sort(key=lambda x: -x[2])
    for gs,ge,ln in residue_list[:40]:
        print(hex(gs), hex(ge), "len=%d"%ln, raw[gs:min(ge+1,gs+48)].hex())
