import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

with pyghidra.open_program(
    BIN,
    project_location=PROJ_LOC,
    project_name=PROJ_NAME,
    analyze=False,
    language="RH850:LE:32:default",
    loader="ghidra.app.util.opinion.BinaryLoader",
    program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    print("LANGUAGE:", program.getLanguage().getLanguageID())
    print("IMAGE BASE:", program.getImageBase())
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()

    def addr(a):
        return af.getAddress(a)

    # Probe the candidate vector table region at 0x780-0x980
    print("=== disasm probe 0x780..0x980 ===")
    flat_api.disassemble(addr(0x780))
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0x780), addr(0x980)), True)
    cnt = 0
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)
        cnt += 1
    print("instr count:", cnt)

    print()
    print("=== byte dump 0x780..0x980 for reference ===")
    n = 0x200
    bs = []
    for i in range(n):
        bs.append(mem.getByte(addr(0x780+i)) & 0xff)
    for off in range(0, n, 16):
        row = bs[off:off+16]
        print("%06x: %s" % (0x780+off, ' '.join('%02x'%x for x in row)))
