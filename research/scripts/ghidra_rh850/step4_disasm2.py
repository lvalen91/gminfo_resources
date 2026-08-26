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
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()

    def addr(a):
        return af.getAddress(a)

    # reliable byte read
    n = 0x300
    bs = []
    for i in range(n):
        try:
            b = mem.getByte(addr(0xf0a1a + i)) & 0xff
        except Exception as e:
            b = -1
        bs.append(b)
    hexstr = ''.join('%02x' % b for b in bs)
    print("=== reliable byte dump 0xf0a1a..+0x%x ===" % n)
    for off in range(0, n, 16):
        row = bs[off:off+16]
        print("%06x: %s" % (0xf0a1a+off, ' '.join('%02x'%x for x in row)))

    print()
    print("=== disassembling 0xf0a1a .. +0x40 explicitly ===")
    ok = flat_api.disassemble(addr(0xf0a1a))
    print("disassemble() returned", ok)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0xf0a1a), addr(0xf0a1a+0x40)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)
