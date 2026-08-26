import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)
    fn = flat_api.getFunctionContaining(addr(0x91b48))
    print("containing fn:", fn)
    if fn:
        print(" entry:", hex(int(fn.getEntryPoint().getOffset())))
        print(" body size:", fn.getBody().getNumAddresses())
        print(" min/max:", fn.getBody().getMinAddress(), fn.getBody().getMaxAddress())

    # also find fn containing the loop start ~0x91a00 area, scan back for a prologue (prepare instr) before 0x91a80
    listing = program.getListing()
    ins = listing.getInstructionBefore(addr(0x91a84))
    cnt=0
    a = addr(0x91a84)
    while cnt < 60:
        ins = listing.getInstructionBefore(a)
        if ins is None: break
        a = ins.getAddress()
        cnt += 1
        if 'prepare' in str(ins) or 'jarl' in str(ins) and False:
            pass
    print("scanned back", cnt, "instrs, landed at", hex(int(a.getOffset())))

    # print refs to FUN at 0x91xxx region: who calls into this loop's start? find nearest function start via getFunctionBefore
    fm = program.getFunctionManager()
    fn_iter = fm.getFunctionContaining(addr(0x91800))
    print("fn containing 0x91800:", fn_iter)
    fn_before = fm.getFunctionBefore(addr(0x91b48)) if hasattr(fm,'getFunctionBefore') else None
