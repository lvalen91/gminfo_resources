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
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()

    def addr(a):
        return af.getAddress(a)

    from ghidra.util.task import ConsoleTaskMonitor
    monitor = ConsoleTaskMonitor()

    blocks = mem.getBlocks()
    print("blocks:", [(b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset()))) for b in blocks])
    blk = blocks[0]

    # Prune the two huge FF regions to Uninitialized to speed up analysis.
    # gap1: 0x22500 .. 0x68500  (before bank B)
    # gap2: 0x8a380 .. EOF
    file_end = int(blk.getEnd().getOffset())
    print("file_end:", hex(file_end))

    txid = program.startTransaction("prune")
    try:
        # split at 0x22500
        mem.split(blk, addr(0x22500))
        blocks = mem.getBlocks()
        for b in blocks:
            print(b.getName(), hex(int(b.getStart().getOffset())), hex(int(b.getEnd().getOffset())))
    finally:
        program.endTransaction(txid, True)
