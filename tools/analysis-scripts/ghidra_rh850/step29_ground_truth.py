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
    refmgr = program.getReferenceManager()

    def addr(a):
        return af.getAddress(a)

    print("=== block info for ram at 0x9f3a2 and 0x77928 ===")
    for a in (0x9f3a2, 0x77928):
        b = mem.getBlock(addr(a))
        print(hex(a), b.getName(), "initialized=", b.isInitialized(), "start=", b.getStart(), "end=", b.getEnd())

    print()
    print("=== fixed byte read via getByte loop, 0x9f3a2 (32 bytes) ===")
    vals = []
    for i in range(32):
        try:
            v = mem.getByte(addr(0x9f3a2 + i)) & 0xff
        except Exception as e:
            v = None
        vals.append(v)
    print(vals)

    print("=== fixed byte read via getByte loop, 0x77928 (32 bytes) ===")
    vals = []
    for i in range(32):
        try:
            v = mem.getByte(addr(0x77928 + i)) & 0xff
        except Exception as e:
            v = None
        vals.append(v)
    print(vals)

    print()
    print("=== disasm at 0x9f3a2 for 0x60 bytes (is this real coherent code?) ===")
    a0, a1 = addr(0x9f3a2), addr(0x9f3a2 + 0x60)
    flat_api.disassemble(a0)
    it = listing.getInstructions(program.getAddressFactory().getAddressSet(a0, a1), True)
    for i in it:
        print(hex(int(i.getAddress().getOffset())), i)

    print()
    print("=== find EEPROM Write Failure string ===")
    st_mgr = program.getListing()
    found = []
    dit = program.getListing().getDefinedData(True)
    cnt = 0
    for d in dit:
        cnt += 1
        if cnt > 2000000:
            break
        try:
            val = d.getValue()
        except Exception:
            continue
        if isinstance(val, str) and "EEPROM Write Failure" in val:
            found.append((d.getAddress(), val))
    print("found strings:", [(hex(int(a.getOffset())), v) for a, v in found])

    for saddr, sval in found:
        print()
        print(f"=== xrefs TO string @ {hex(int(saddr.getOffset()))} ===")
        refs = refmgr.getReferencesTo(saddr)
        for r in refs:
            frm = r.getFromAddress()
            f = fm.getFunctionContaining(frm)
            print(" from", hex(int(frm.getOffset())), r.getReferenceType(), "fn:", f)

    print()
    print("=== callers of FUN_000778ea (0x778ea) ===")
    f = fm.getFunctionAt(addr(0x778ea))
    if f:
        refs = refmgr.getReferencesTo(addr(0x778ea))
        for r in refs:
            frm = r.getFromAddress()
            cf = fm.getFunctionContaining(frm)
            print(" call from", hex(int(frm.getOffset())), r.getReferenceType(), "in fn:", cf)
    else:
        print("no function at 778ea?")
