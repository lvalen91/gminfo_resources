import pyghidra, time

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

raw = open(BIN,'rb').read()

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    listing = program.getListing()
    def addr(a): return af.getAddress(a)

    def slot_addr(off):
        return raw[off+8] | (raw[off+9]<<8) | (raw[off+10]<<16) | (raw[off+11]<<24)

    tab_start = 0x780
    tab_end = 0x980  # 32 entries * 16
    seeds = []
    off = tab_start
    while off < tab_end:
        t = slot_addr(off)
        seeds.append((off, t))
        off += 16

    print("vector table entries:", len(seeds))
    for o,t in seeds:
        print(" ", hex(o), "->", hex(t))

    txid = program.startTransaction("seed")
    created = 0
    try:
        for o,t in seeds:
            a = addr(t)
            try:
                flat_api.disassemble(a)
                fn = flat_api.getFunctionAt(a)
                if fn is None:
                    fn = flat_api.createFunction(a, None)
                if fn is not None:
                    created += 1
            except Exception as e:
                print("seed fail", hex(t), e)
        # Also mark slot 0 (reset, 0xe5924) as entry point
        entry = addr(seeds[0][1])
        try:
            flat_api.addEntryPoint(entry)
        except Exception as e:
            print("addEntryPoint failed:", e)
    finally:
        program.endTransaction(txid, True)
    print("functions created from vector seeds:", created)
    print("total function count now:", program.getFunctionManager().getFunctionCount())
