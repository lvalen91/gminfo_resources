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
    mem = program.getMemory()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)
    from ghidra.program.model.address import AddressSet

    blk = mem.getBlocks()[0]
    ws = int(blk.getStart().getOffset())
    we = int(blk.getEnd().getOffset())
    windows = [(ws, we)]
    gaps=[]
    for s,e in windows:
        aset = AddressSet(addr(s), addr(e))
        used = AddressSet()
        for ins in listing.getInstructions(aset, True):
            used.add(ins.getMinAddress(), ins.getMaxAddress())
        for d in listing.getDefinedData(aset, True):
            used.add(d.getMinAddress(), d.getMaxAddress())
        undef = aset.subtract(used)
        for r in undef.getAddressRanges():
            gaps.append((int(r.getMinAddress().getOffset()), int(r.getMaxAddress().getOffset())))
    gaps.sort(key=lambda x: -(x[1]-x[0]))
    print("total gaps:", len(gaps), "total bytes:", sum(e-s+1 for s,e in gaps))
    print()
    print("=== all gaps (addr,len,hex-prefix) ===")
    for s,e in gaps:
        b = raw[s:e+1]
        print(hex(s), hex(e), "len=%d"%len(b), b.hex()[:64])
