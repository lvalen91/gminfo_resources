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
    def addr(a): return af.getAddress(a)

    # scan backward from 0x91800 for a 'prepare' instruction (typical function prologue) within 0x2000 bytes
    a = addr(0x91800)
    found = []
    for _ in range(400):
        ins = listing.getInstructionBefore(a)
        if ins is None: break
        a = ins.getAddress()
        s = str(ins)
        if s.startswith('prepare'):
            found.append((int(a.getOffset()), s))
    print("prepare instrs found scanning back:", found[:5])

    # scan forward past 0x91d00 to find where this batch-reading pattern ends (search for 'dispose' followed by 'jr [lp]' i.e. real return)
    b = addr(0x91d00)
    count=0
    last_calgroup_call=None
    while count < 3000:
        ins = listing.getInstructionAt(b)
        if ins is None:
            ins = listing.getInstructionAfter(b)
            if ins is None: break
            b = ins.getAddress()
        s = str(ins)
        if 'c8f6a' in s:
            last_calgroup_call = int(b.getOffset())
        if s.strip() in ('jr [lp]',) or s.startswith('jr  [lp]'):
            print("possible return at", hex(int(b.getOffset())), s)
            break
        nxt = listing.getInstructionAfter(b)
        if nxt is None: break
        b = nxt.getAddress()
        count += 1
    print("last CalGroup(0xc8f6a) call seen while scanning forward:", hex(last_calgroup_call) if last_calgroup_call else None)
    print("scanned", count, "instrs forward, ended at", hex(int(b.getOffset())))
