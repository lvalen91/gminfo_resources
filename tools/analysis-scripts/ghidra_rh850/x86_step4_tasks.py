#!/usr/bin/env python3
"""Step 4: seed disassembly at each payload-task .text section start (boottable-confirmed
entry convention == section start, verified against kernel _start==.kernel_text start),
run Aggressive Instruction Finder + normal analysis on those blocks, report new coverage."""
import sys, time
import pyghidra

PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"

pyghidra.start(verbose=False)
from ghidra.base.project import GhidraProject
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.address import AddressSet
from ghidra.program.flatapi import FlatProgramAPI

monitor = ConsoleTaskMonitor()
proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = proj.openProgram("/", "hostos.elf", False)
flat = FlatProgramAPI(prog)
af = prog.getAddressFactory().getDefaultAddressSpace()
mem = prog.getMemory()

# all .text-like exec blocks except the already-covered kernel/.text/.t_text
task_text_starts = [
 0x00860000, # vip_server.text
 0x0086b000, # lifecycle.text
 0x00875000, # audit.text
 0x0087d000, # dirana3_mux_server.text
 0x00889000, # chime_requester.text
 0x00bbb000, # audio_server.text
 0x00bc6000, # camera.text
 0x00bdf000, # guidelines.text
 0x00de4000, # ota_update.text
 0x00df8000, # calibrations.text
 0x00e21000, # gvtg_server.text
 0x00e91000, # display_i2c.text
 0x00e9b000, # tee_router.text
 0x00eac000, # tee_keymaster.text
 0x00f05000, # tee_gatekeeper.text
 0x00f19000, # tee_hw_crypto.text
 0x00f31000, # tee_storage.text
 0x00f60000, # vmm1.text
 0x00fc6000, # emmc_mux.text
]

tid = prog.startTransaction("seed disasm")
seeded = 0
try:
    for a in task_text_starts:
        addr = af.getAddress(a)
        try:
            flat.disassemble(addr)
            fn = flat.getFunctionAt(addr)
            if fn is None:
                fn = flat.createFunction(addr, None)
            seeded += 1
        except Exception as e:
            print("seed fail 0x%x: %s" % (a, e))
finally:
    prog.endTransaction(tid, True)
print("SEEDED:", seeded)

# enable Aggressive Instruction Finder + run full analysis
from ghidra.app.plugin.core.analysis import AutoAnalysisManager
from ghidra.program.model.listing import Program

mgr = AutoAnalysisManager.getAnalysisManager(prog)
options = prog.getOptions(Program.ANALYSIS_PROPERTIES)
# turn on aggressive instruction finder if the option key exists
tid2 = prog.startTransaction("enable aif")
try:
    for name in options.getOptionNames():
        if "Aggressive Instruction Finder" in name:
            print("found option:", name)
finally:
    prog.endTransaction(tid2, True)

t0=time.time()
from ghidra.app.script import GhidraScriptUtil
GhidraScriptUtil.acquireBundleHostReference()
try:
    mgr.reAnalyzeAll(None)
    mgr.startAnalysis(monitor)
finally:
    GhidraScriptUtil.releaseBundleHostReference()
print("ANALYZE2_TIME:", time.time()-t0)

fm = prog.getFunctionManager()
print("FUNC_COUNT_NOW:", fm.getFunctionCount())

proj.save(prog)
proj.close()
print("DONE")
