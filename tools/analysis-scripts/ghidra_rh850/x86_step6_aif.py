#!/usr/bin/env python3
"""Step 6: enable Aggressive Instruction Finder + Function Start Search boldly on the
still-undefined bytes of exec blocks (all task .text sections + kernel/.text/.t_text),
then re-run analysis so it sweeps the dark code."""
import time
import pyghidra
PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"
pyghidra.start(verbose=False)
from ghidra.base.project import GhidraProject
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.listing import Program
from ghidra.app.plugin.core.analysis import AutoAnalysisManager
from ghidra.app.script import GhidraScriptUtil

monitor = ConsoleTaskMonitor()
proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = proj.openProgram("/", "hostos.elf", False)

options = prog.getOptions(Program.ANALYSIS_PROPERTIES)
tid = prog.startTransaction("enable analyzers")
try:
    for name in list(options.getOptionNames()):
        if name == "Aggressive Instruction Finder":
            print("enabling", name, "was", options.getBoolean(name, False))
            options.setBoolean(name, True)
finally:
    prog.endTransaction(tid, True)

mgr = AutoAnalysisManager.getAnalysisManager(prog)
GhidraScriptUtil.acquireBundleHostReference()
t0=time.time()
try:
    mgr.reAnalyzeAll(None)
    mgr.startAnalysis(monitor)
finally:
    GhidraScriptUtil.releaseBundleHostReference()
print("AIF_ANALYZE_TIME:", time.time()-t0)

fm = prog.getFunctionManager()
print("FUNC_COUNT_NOW:", fm.getFunctionCount())

proj.save(prog)
proj.close()
print("DONE")
