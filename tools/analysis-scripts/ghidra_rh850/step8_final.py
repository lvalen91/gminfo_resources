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

    ids = [0xb4,0xb5,0xf9,0xfa,0xfb,0xfc,0xfd,0xfe,0xff,0x100,0x101,0x102,0x103,
           0xdc1,0xdc2,0xdc3,0xdc4,0xdc5,0xdc6,0xdc7,0xdc8,0xdc9]
    base = 0x4fb8c
    print("=== descriptor entries (24B stride) for every calItemId actually referenced in VIP_APP ===")
    print("id(hex) : entry_addr : dest_idx(u16@0) field@2(u16) src_idx(u16@4) type(u8@0xa) rest(0xb-0x17 hex)")
    for cid in ids:
        e = base + cid*0x18
        dest_idx = ru16(e+0)
        f2 = ru16(e+2)
        src_idx = ru16(e+4)
        f6 = ru16(e+6)
        f8 = ru16(e+8)
        typ = rb(e+0xa)
        rest = bytes(rb(e+i) for i in range(0xb,0x18))
        print("0x%04x : 0x%06x : dest=0x%04x f2=0x%04x src=0x%04x f6=0x%04x f8=0x%04x type=%d rest=%s" % (
            cid, e, dest_idx, f2, src_idx, f6, f8, typ, rest.hex()))

    print()
    print("=== decompile FUN_000b67d0 (SBI validator, per audit) ===")
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)
    a = addr(0xb67d0)
    fn = flat_api.getFunctionAt(a)
    print("fn at 0xb67d0:", fn)
    if fn is None:
        flat_api.disassemble(a)
        fn = flat_api.createFunction(a, "FUN_000b67d0")
        print("created:", fn)
    if fn is not None:
        res = di.decompileFunction(fn, 90, None)
        if res.decompileCompleted():
            code = res.getDecompiledFunction().getC()
            print(code[:6000])
        else:
            print("decompile failed:", res.getErrorMessage())

    print()
    print("=== search this function's body for calls to c8f6a/c90c4 or refs to febd3e06/febd4da0 ===")
    if fn is not None:
        body = fn.getBody()
        it = listing.getInstructions(body, True)
        for i in it:
            s = str(i)
            if 'c8f6a' in s or '90c4' in s or '3e06' in s or '4da0' in s or 'call' in s.lower():
                print(hex(int(i.getAddress().getOffset())), i)
