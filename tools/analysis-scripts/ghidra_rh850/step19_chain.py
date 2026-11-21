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
    fm = program.getFunctionManager()
    refm = program.getReferenceManager()
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    def addr(a):
        return af.getAddress(a)

    def callers_of(ea):
        f = fm.getFunctionAt(addr(ea))
        if f is None:
            return []
        refs = refm.getReferencesTo(f.getEntryPoint())
        return [hex(int(r.getFromAddress().getOffset())) for r in refs]

    def decomp(ea, cap=3000):
        f = fm.getFunctionContaining(addr(ea))
        print("---- 0x%x : %s ----" % (ea, f))
        if f is None:
            print("(no fn)"); return
        res = di.decompileFunction(f, 90, None)
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC()[:cap])
        else:
            print("decompile failed:", res.getErrorMessage())

    print("### Caller of FUN_000c7472 (bitfield-extract-then-write-shadow) is at 0xc744e ###")
    decomp(0xc744e)
    print("callers of that:", callers_of(0xc7420) )
    # find function containing 0xc744e entry
    f = fm.getFunctionContaining(addr(0xc744e))
    print("callers of 0xc744e's function (%s):" % f, callers_of(int(f.getEntryPoint().getOffset())) if f else None)

    print()
    print("### Caller of FUN_000c8fc4 (shadow getter) is at 0xc8fa0 ###")
    decomp(0xc8fa0)
    f2 = fm.getFunctionContaining(addr(0xc8fa0))
    print("callers of 0xc8fa0's function (%s):" % f2, callers_of(int(f2.getEntryPoint().getOffset())) if f2 else None)

    print()
    print("### checking other orphaned funcs for spurious-split (fall-through) pattern ###")
    for ea in [0xc812e, 0xc6cb0, 0xc73f0]:
        f = fm.getFunctionAt(addr(ea))
        print("fn at 0x%x:" % ea, f)
        # find preceding instruction
        prev_insn = listing.getInstructionBefore(addr(ea))
        print("  preceding instr:", hex(int(prev_insn.getAddress().getOffset())) if prev_insn else None, prev_insn)
        prev_fn = fm.getFunctionContaining(prev_insn.getAddress()) if prev_insn else None
        print("  preceding fn:", prev_fn)
