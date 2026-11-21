import pyghidra, struct

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

raw = open(BIN,'rb').read()

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()
    listing = program.getListing()
    def addr(a): return af.getAddress(a)

    txid = program.startTransaction("uninit+seed")
    try:
        for b in list(mem.getBlocks()):
            name = b.getName()
            start = int(b.getStart().getOffset())
            if name in ('ram.split','ram.split.split.split'):
                print("converting to uninitialized:", name, hex(start))
                mem.convertToUninitialized(b)
        for b in mem.getBlocks():
            print(b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())), b.isInitialized())

        # ---- Seed vector table entries in Bank A (0x780..0x980) ----
        seeds = []
        def scan_vectab(tab_start, tab_end):
            found = []
            off = tab_start
            while off < tab_end - 6:
                # jr instruction candidate at off, opcode bytes 0x81,0x07 (low 2 bytes of the 4-byte word at 'off')
                if raw[off] == 0x81 and raw[off+1] == 0x07:
                    ok = flat_api.disassemble(addr(off))
                    ins = listing.getInstructionAt(addr(off))
                    if ins is not None and ins.getFlowType().isJump():
                        flows = ins.getFlows()
                        if flows:
                            t = int(flows[0].getOffset())
                            found.append((off, t))
                    off += 4
                else:
                    off += 2
            return found

        bankA_vecs = scan_vectab(0x780, 0x9a6)
        bankB_vecs = scan_vectab(0x68580, 0x687a0)
        print("bankA vector entries:", len(bankA_vecs))
        for o,t in bankA_vecs: print(" ", hex(o), "->", hex(t))
        print("bankB vector entries:", len(bankB_vecs))
        for o,t in bankB_vecs: print(" ", hex(o), "->", hex(t))

        seeds = sorted(set(t for _,t in bankA_vecs) | set(t for _,t in bankB_vecs))
        print("unique seed targets:", len(seeds))

        created = 0
        for t in seeds:
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
        print("functions created from vector seeds:", created)
    finally:
        program.endTransaction(txid, True)
