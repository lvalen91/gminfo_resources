import pyghidra, time, sys

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"
raw = open(BIN,'rb').read()

def classify_gap(b):
    if len(b)==0: return 'empty'
    if all(x==0x00 for x in b): return 'pad0'
    if all(x==0xff for x in b): return 'padff'
    printable = sum(1 for c in b if 32<=c<127)
    nul = sum(1 for c in b if c==0)
    if (printable+nul)/len(b) > 0.85 and printable > len(b)*0.5:
        return 'string'
    return 'codecandidate'

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    af = program.getAddressFactory().getDefaultAddressSpace()
    mem = program.getMemory()
    def addr(a): return af.getAddress(a)
    from ghidra.program.model.address import AddressSet
    from ghidra.program.util import GhidraProgramUtilities

    windows = [(0x0,0x224ff),(0x68500,0x8a37f)]

    def get_gaps():
        gaps=[]
        for s,e in windows:
            aset = AddressSet(addr(s), addr(e))
            used = AddressSet()
            for ins in listing.getInstructions(aset, True):
                used.add(ins.getMinAddress(), ins.getMaxAddress())
            for d in listing.getDefinedData(aset, True):
                used.add(d.getMinAddress(), d.getMaxAddress())
            undef = aset.subtract(used)
            for r in undef.getAddressRanges():
                gaps.append((int(r.getMinAddress().getOffset()), int(r.getMaxAddress().getOffset())))
        return gaps

    MAX_ROUNDS = 6
    for rnd in range(MAX_ROUNDS):
        gaps = get_gaps()
        buckets = {'pad0':0,'padff':0,'string':0,'codecandidate':0,'empty':0}
        code_gaps = []
        for s,e in gaps:
            b = raw[s:e+1]
            cls = classify_gap(b)
            buckets[cls]+=1
            if cls=='codecandidate':
                code_gaps.append((s,e,len(b)))
        print("=== round %d: gaps=%d buckets=%s ===" % (rnd, len(gaps), buckets))
        sys.stdout.flush()
        if not code_gaps:
            print("no more code candidates, stopping sweep")
            break

        txid = program.startTransaction("sweep-round-%d"%rnd)
        created = 0
        tried = 0
        try:
            for s,e,ln in code_gaps:
                a = addr(s)
                if listing.getInstructionAt(a) is not None or listing.getDefinedDataAt(a) is not None:
                    continue
                tried += 1
                try:
                    ok = flat_api.disassemble(a)
                except Exception as ex:
                    ok = False
                ins = listing.getInstructionAt(a)
                if ins is not None:
                    fn = flat_api.getFunctionAt(a)
                    if fn is None:
                        try:
                            fn = flat_api.createFunction(a, None)
                        except Exception:
                            fn = None
                    if fn is not None:
                        created += 1
        finally:
            program.endTransaction(txid, True)
        print("  tried=%d created_functions=%d" % (tried, created))

        # re-run recursive descent / AIF to chase new xrefs
        txid = program.startTransaction("reset-flag-%d"%rnd)
        try:
            GhidraProgramUtilities.resetAnalysisFlags(program)
        finally:
            program.endTransaction(txid, True)
        t0=time.time()
        flat_api.analyzeAll(program)
        print("  re-analyze in %.1fs, function count now %d" % (time.time()-t0, program.getFunctionManager().getFunctionCount()))
        sys.stdout.flush()

    print("FINAL function count:", program.getFunctionManager().getFunctionCount())
