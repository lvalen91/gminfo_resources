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
    refmgr = program.getReferenceManager()

    def addr(a):
        return af.getAddress(a)

    print("=== any instruction anywhere referencing/loading 0x778ea (search all refs, incl no-type) ===")
    # brute: scan all instructions for an operand scalar == 0x778ea
    found = 0
    ins = listing.getInstructions(True)
    for i in ins:
        try:
            s = i.toString()
        except Exception:
            continue
        if "778ea" in s:
            print(" ", hex(int(i.getAddress().getOffset())), s)
            found += 1
            if found > 40:
                break
    print("total matches:", found)

    print()
    print("=== does CalGroup dispatcher 0xf0a1a or commit dispatcher 0xeeec8 reference 778ea region (77000-78000) or 9f000-a0000? ===")
    for base, label in [(0xf0a1a, "CalGroupDispatch"), (0xeeec8, "CommitDispatch")]:
        f = fm.getFunctionContaining(addr(base))
        print(label, "fn:", f)

    print()
    print("=== decompile callees from 0x9f3a2 handler: 0x9ec66, 0xeccdc, 0xeccb4 ===")
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    di = DecompInterface()
    di.openProgram(program)
    mon = ConsoleTaskMonitor()
    for t in (0x9ec66, 0xeccdc, 0xeccb4):
        f = fm.getFunctionContaining(addr(t))
        print(f"-- {hex(t)} -> function {f}")
        if f:
            res = di.decompileFunction(f, 30, mon)
            if res.decompileCompleted():
                c = res.getDecompiledFunction().getC()
                print(c[:1500])
            else:
                print("decomp failed:", res.getErrorMessage())

    print()
    print("=== search whole program instructions for immediate 0xa0/0xa1/0x50 used with 'mov' near jarl to i2c-ish, cheap heuristic: search function names containing 'IIC','I2C','RIIC','EEPROM','M24' ===")
    fm_iter = fm.getFunctions(True)
    hits = []
    for fn in fm_iter:
        n = fn.getName()
        ln = n.lower()
        if any(k in ln for k in ("iic","i2c","riic","eeprom","m24","24c64","eep_")):
            hits.append((hex(int(fn.getEntryPoint().getOffset())), n))
    print(f"name-based hits ({len(hits)}):")
    for h in hits[:60]:
        print(" ", h)
