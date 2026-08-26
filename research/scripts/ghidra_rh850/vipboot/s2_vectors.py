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

    # Try forcing disasm exactly at each candidate slot base (0x780 + n*0x10) and at +6 offset
    print("=== per-slot disasm at slot_base and slot_base+6, stride 0x10, from 0x780 to 0xa00 ===")
    for slot in range(0x780, 0xa00, 0x10):
        for off in (0, 6):
            a = addr(slot+off)
            try:
                flat_api.clearListing(a, addr(slot+off+8))
            except Exception:
                pass
            ok = flat_api.disassemble(a)
            ins = listing.getInstructionAt(a)
            if ins is not None:
                print(hex(slot+off), "->", ins, " len=%d"%ins.getLength())

    print()
    print("=== raw 4-byte LE words at slot+6 for slots 0x780..0xb80, to see numeric pattern ===")
    for slot in range(0x780, 0xb80, 0x10):
        base = slot+6
        b = bytes(mem.getByte(addr(base+i))&0xff for i in range(4))
        val = b[0] | (b[1]<<8) | (b[2]<<16) | (b[3]<<24)
        print(hex(base), b.hex(), hex(val))
