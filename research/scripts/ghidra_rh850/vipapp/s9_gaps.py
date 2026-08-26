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
    from ghidra.program.model.address import AddressSet

    blk = mem.getBlocks()[0]
    s = int(blk.getStart().getOffset())
    e = int(blk.getEnd().getOffset())
    aset = AddressSet(addr(s), addr(e))
    used = AddressSet()
    for ins in listing.getInstructions(aset, True):
        used.add(ins.getMinAddress(), ins.getMaxAddress())
    for d in listing.getDefinedData(aset, True):
        used.add(d.getMinAddress(), d.getMaxAddress())
    undef = aset.subtract(used)
    gaps = []
    for r in undef.getAddressRanges():
        gaps.append((int(r.getMinAddress().getOffset()), int(r.getMaxAddress().getOffset())))
    gaps.sort(key=lambda x: -(x[1]-x[0]))
    print("num gap ranges:", len(gaps), "total gap bytes:", sum(b-a+1 for a,b in gaps))
    print("top 60 largest gaps:")
    for a,b in gaps[:60]:
        print(hex(a), hex(b), "size", hex(b-a+1))
