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
    def rb(a):
        return mem.getByte(addr(a)) & 0xff
    def ru16(a):
        return rb(a) | (rb(a+1)<<8)

    # group tables per FUN_000c90c4 decompile:
    #   iVar1 = &LAB_00069a18 + param_1*0xc  (per-group struct, stride 0xc)
    #   DAT_00069a16[param_1] range start ushort, DAT_00069a14[param_1] range end ushort
    #   &LAB_00064e74 + idx*2 -> ushort calItemId, for idx in [start,end)
    # scan groups 0..0x40 and dump their calId ranges, flag if 0x440/0x441/0xaa0/0xae5 present
    print("=== scanning groups for membership of 0x440/0x441/0xaa0/0xae5 ===")
    targets = {0x440,0x441,0xaa0,0xae5}
    hits = []
    for g in range(0, 0x60):
        gbase = 0x69a18 + g*0xc
        # per c90c4: puVar5 = ushort*(&DAT_0004fb8c + iVar1) where iVar1 = calId*0x18 -- not needed here
        # start/end ushort at DAT_00069a16+param_1*0xc? Actually decompile shows indexing as *(ushort*)(&DAT_00069a16 + param_1) NOT *0xc...
        # re-derive from raw disasm instead (more reliable) - done separately below
        pass

    print("(placeholder - see raw disasm derivation below)")

    print()
    print("=== raw disasm of FUN_000c90c4 header again for precise stride/offsets ===")
    a0,a1 = addr(0xc90c4), addr(0xc9120)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0,a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== xrefs TO 0xfebdaae2 (byte shadow) ===")
    refs = program.getReferenceManager().getReferencesTo(addr(0xfebdaae2))
    cnt=0
    for r in refs:
        print(" from", hex(int(r.getFromAddress().getOffset())), r.getReferenceType())
        cnt+=1
    print("total:", cnt)

    print()
    print("=== xrefs TO 0xfebd3e06 ($27 gate byte) ===")
    refs = program.getReferenceManager().getReferencesTo(addr(0xfebd3e06))
    cnt=0
    for r in refs:
        print(" from", hex(int(r.getFromAddress().getOffset())), r.getReferenceType())
        cnt+=1
    print("total:", cnt)
