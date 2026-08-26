import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

targets = set([0x4fb96, 0x4fb8c, 0xf0a1a, 0x18])  # 0x18=24 stride, likely too common; keep for reference only

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
    hits = {t: [] for t in (0x4fb96, 0x4fb8c, 0xf0a1a)}
    for ins in listing.getInstructions(aset, True):
        for i in range(ins.getNumOperands()):
            try:
                sc = ins.getScalar(i)
            except Exception:
                sc = None
            if sc is not None:
                v = sc.getUnsignedValue()
                if v in hits:
                    hits[v].append(int(ins.getAddress().getOffset()))
    for t,addrs in hits.items():
        print(hex(t), "hit count:", len(addrs))
        for a in addrs[:20]:
            fn = flat_api.getFunctionContaining(addr(a))
            print("   ", hex(a), "fn=", fn.getName() if fn else None)
