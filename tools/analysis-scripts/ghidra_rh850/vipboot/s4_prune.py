import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()
    def addr(a): return af.getAddress(a)

    txid = program.startTransaction("prune2")
    try:
        blocks = {b.getName(): b for b in mem.getBlocks()}
        print("before:", [(b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset()))) for b in mem.getBlocks()])
        big = blocks.get('ram.split')
        # split big block at 0x68500 and 0x8a380
        mem.split(big, addr(0x68500))
        blocks = {b.getName(): b for b in mem.getBlocks()}
        for name,b in blocks.items():
            print(name, hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())))
        # now find the middle-gap block (0x22500-0x68500) and split bankB block at 0x8a380
        for b in mem.getBlocks():
            if int(b.getStart().getOffset()) == 0x68500:
                mem.split(b, addr(0x8a380))
                break
        print("after all splits:")
        for b in mem.getBlocks():
            print(b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())))
    finally:
        program.endTransaction(txid, True)
