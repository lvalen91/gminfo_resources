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

    def addr(a):
        return af.getAddress(a)

    print("=== raw disasm 0x8ffe0 .. 0x90090 ===")
    flat_api.disassemble(addr(0x8ffe0))
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0x8ffe0), addr(0x90090)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== raw disasm 0x94700 .. 0x94790 ===")
    flat_api.disassemble(addr(0x94700))
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(addr(0x94700), addr(0x94790)), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== decompile FUN_0009597c ===")
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)
    fn = flat_api.getFunctionAt(addr(0x9597c))
    print("fn:", fn)
    if fn is not None:
        res = di.decompileFunction(fn, 90, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC())
        else:
            print("fail:", res.getErrorMessage())
