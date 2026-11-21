#!/usr/bin/env python3
"""Step 1: import hostos.elf into Ghidra project, run full auto-analysis, save."""
import sys, time
sys.path.insert(0, '/opt/homebrew/lib/python3.14/site-packages')
import pyghidra

ELF = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/analysis/hostos_unpack/hostos.elf"
PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"

pyghidra.start(verbose=True)

t0 = time.time()
with pyghidra.open_program(ELF, project_location=PROJ_DIR, project_name=PROJ_NAME,
                            analyze=True, language="x86:LE:64:default",
                            program_name="hostos.elf") as flat_api:
    prog = flat_api.getCurrentProgram()
    print("IMPORTED:", prog.getName(), "min", prog.getMinAddress(), "max", prog.getMaxAddress())
    print("ANALYSIS_TIME_SEC:", time.time()-t0)
    fm = prog.getFunctionManager()
    print("FUNC_COUNT_AFTER_AUTOANALYZE:", fm.getFunctionCount())
    from ghidra.program.model.listing import CodeUnit
    print("SAVED via context manager exit")
print("DONE")
