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
    from jpype import JArray, JByte

    def addr(a):
        return af.getAddress(a)

    def scan_pattern(pattern):
        found = []
        for b in mem.getBlocks():
            if not b.isInitialized():
                continue
            size = int(b.getSize())
            start = b.getStart()
            arr = JArray(JByte)(size)
            b.getBytes(start, arr)
            data = bytes(x & 0xff for x in arr)
            i = 0
            while True:
                idx = data.find(pattern, i)
                if idx == -1:
                    break
                found.append(start.add(idx))
                i = idx + 1
        return found

    import struct
    targets = {
        "0xC812E": 0xc812e,
        "0xC6CB0": 0xc6cb0,
        "0xC73F0": 0xc73f0,
        "0xC90FC": 0xc90fc,
    }
    for name, ea in targets.items():
        pat = struct.pack("<I", ea)
        hits = scan_pattern(pat)
        print("=== pointer-value scan for %s (%s) ===" % (name, pat.hex()))
        print("total:", len(hits))
        for h in hits[:20]:
            off = int(h.getOffset())
            fn = fm.getFunctionContaining(h)
            print("  at", hex(off), "in fn:", fn)
        print()

    print("=== [CAL] EEPROM Write Failure string addresses -> functions referencing them ===")
    str_addrs = [0x60a6,0x60d2,0x60fe,0x612a,0x6156,0x6182,0x61ae,0x61da,0x6206,0x6232,0x625e,0x628a,0x62b6,0x62e2,0x630e]
    emitter_fns = set()
    for sa in str_addrs:
        refs = program.getReferenceManager().getReferencesTo(addr(sa))
        for r in refs:
            fa = r.getFromAddress()
            f = fm.getFunctionContaining(fa)
            print(hex(sa), "referenced from", hex(int(fa.getOffset())), "fn:", f)
            if f is not None:
                emitter_fns.add(int(f.getEntryPoint().getOffset()))
    print("unique emitter functions:", [hex(x) for x in sorted(emitter_fns)])
