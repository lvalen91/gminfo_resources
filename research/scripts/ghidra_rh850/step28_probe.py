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
    fm = program.getFunctionManager()
    st = program.getSymbolTable()

    def addr(a):
        return af.getAddress(a)

    print("=== instruction detail at 0x77922 ===")
    ins = listing.getInstructionAt(addr(0x77922))
    print(ins)
    print("numOperands", ins.getNumOperands())
    for i in range(ins.getNumOperands()):
        print(" operand", i, ins.getDefaultOperandRepresentation(i), "refType", [str(r) for r in ins.getOperandReferences(i)])
    print("flowType", ins.getFlowType())
    for r in ins.getReferencesFrom():
        print(" refFrom ->", hex(int(r.getToAddress().getOffset())), r.getReferenceType())

    print()
    print("=== bytes at 0x9f3a2 (64 bytes hex) ===")
    ba = bytearray(64)
    mem.getBytes(addr(0x9f3a2), ba)
    print(ba.hex())
    print("=== bytes at 0x9f466 (64 bytes hex) ===")
    ba = bytearray(64)
    mem.getBytes(addr(0x9f466), ba)
    print(ba.hex())
    print("=== bytes at 0x9f540 (64 bytes hex) ===")
    ba = bytearray(64)
    mem.getBytes(addr(0x9f540), ba)
    print(ba.hex())

    print()
    print("=== what block/section contains 0x9f3a2, 0x77928 ===")
    for a in (0x9f3a2, 0x9f466, 0x9f540, 0x77928, 0x779ec, 0x77ac6):
        block = mem.getBlock(addr(a))
        print(hex(a), "-> block:", block.getName() if block else None,
              "code unit:", listing.getCodeUnitAt(addr(a)))

    print()
    print("=== defined data/instructions exactly AT 0x9f3a2 ===")
    cu = listing.getCodeUnitContaining(addr(0x9f3a2))
    print(cu, type(cu))
    f = fm.getFunctionContaining(addr(0x9f3a2))
    print("function containing 0x9f3a2:", f)

    print()
    print("=== symbols at/near 0x9f3a2 ===")
    for s in st.getSymbols(addr(0x9f3a2)):
        print(s)
