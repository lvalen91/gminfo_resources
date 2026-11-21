import pyghidra, time

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85056831"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "vipboot_rh850"

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_BOOT_85056831",
) as flat_api:
    program = flat_api.getCurrentProgram()

    from ghidra.program.util import GhidraProgramUtilities
    from ghidra.app.plugin.core.analysis import AutoAnalysisManager
    mgr = AutoAnalysisManager.getAnalysisManager(program)

    from ghidra.framework.options import Options
    opts = program.getOptions("Analyzers")
    names = opts.getOptionNames()
    cand = [n for n in names if 'Aggressive' in n or 'ASCII' in n or 'String' in n]
    print("candidate analyzer options:", list(cand))

    txid = program.startTransaction("enable-analyzers")
    try:
        pass
        # try to enable Aggressive Instruction Finder if present
        target = None
        for n in names:
            if 'Aggressive Instruction Finder' in n:
                target = n
        print("target analyzer option key:", target)
        if target:
            opts.setBoolean(target, True)
            print("enabled:", target)
    finally:
        program.endTransaction(txid, True)

    t0=time.time()
    flat_api.analyzeAll(program)
    print("re-analyze done in %.1fs" % (time.time()-t0))
    fm = program.getFunctionManager()
    print("function count:", fm.getFunctionCount())
