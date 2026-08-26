import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

targets = [0x3232, 0x7f0a, 0x9dce, 0x7fee]

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    refmgr = program.getReferenceManager()
    def addr(a): return af.getAddress(a)

    for t in targets:
        a = addr(t)
        d = listing.getDefinedDataAt(a)
        print(hex(t), "data:", d)
        refs = list(refmgr.getReferencesTo(a))
        print("  xref count:", len(refs))
        for r in refs[:10]:
            fa = r.getFromAddress()
            fn = flat_api.getFunctionContaining(fa)
            print("   from", hex(int(fa.getOffset())), "fn=", fn.getName() if fn else None)

    # also brute scalar scan for these + the write-fail strings once more with full window recheck
    from ghidra.program.model.address import AddressSet
    aset = AddressSet(addr(0x0), addr(0xFFFFF))
    hits = {t: [] for t in targets}
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
    print()
    print("scalar scan results:")
    for t,addrs in hits.items():
        print(hex(t), len(addrs), [hex(x) for x in addrs[:5]])
