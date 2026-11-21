#!/usr/bin/env python3
"""Step 2: apply GHS 24-byte symtab (FUNC+OBJ) as Ghidra function/label names.
Then create+disassemble functions at FUNC addresses not yet functions.
Re-run analysis, save."""
import sys, time
import pyghidra

PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"
SYMTSV = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850/hostos_symbols_funcobj.tsv"

pyghidra.start(verbose=False)

from ghidra.base.project import GhidraProject
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.symbol import SourceType
import ghidra.program.model.symbol as symmod

monitor = ConsoleTaskMonitor()

proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = None
for f in proj.getRootFolder().getFiles():
    print("file:", f.getName())
    if f.getName() == "hostos.elf":
        prog = proj.openProgram("/", "hostos.elf", False)
        break

if prog is None:
    print("ERROR: program not found")
    sys.exit(1)

from ghidra.program.flatapi import FlatProgramAPI
flat = FlatProgramAPI(prog)

af = prog.getAddressFactory()
fm = prog.getFunctionManager()
st = prog.getSymbolTable()
lst = prog.getListing()

rows = []
with open(SYMTSV) as f:
    next(f)
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4: continue
        addr_s, typ, name, size = parts
        addr = int(addr_s, 16)
        rows.append((addr, typ, name, int(size) if size else 0))

print("total symbol rows to apply:", len(rows))

tid = prog.startTransaction("apply symbols")
named = 0
func_created = 0
label_created = 0
errors = 0
try:
    for addr, typ, name, size in rows:
        try:
            a = af.getDefaultAddressSpace().getAddress(addr)
        except Exception as e:
            errors += 1
            continue
        # sanitize name: Ghidra disallows some chars but mostly ok; truncate absurd length
        safe_name = name[:2000]
        if typ == "FUNC":
            fn = fm.getFunctionAt(a)
            if fn is None:
                # try to create function if address looks executable/in a defined block
                block = prog.getMemory().getBlock(a)
                if block is not None and block.isInitialized():
                    try:
                        fn = flat.createFunction(a, safe_name)
                        if fn is not None:
                            func_created += 1
                    except Exception:
                        fn = None
            if fn is not None:
                try:
                    fn.setName(safe_name, SourceType.IMPORTED)
                    named += 1
                except Exception:
                    errors += 1
            else:
                # fallback: just place a label
                try:
                    st.createLabel(a, safe_name, SourceType.IMPORTED)
                    label_created += 1
                except Exception:
                    errors += 1
        else:  # OBJ
            try:
                sym = st.createLabel(a, safe_name, SourceType.IMPORTED)
                label_created += 1
            except Exception:
                errors += 1
finally:
    prog.endTransaction(tid, True)

print("RESULT named_functions=%d func_created=%d label_created=%d errors=%d" % (named, func_created, label_created, errors))

t0=time.time()
from ghidra.app.script import GhidraScriptUtil
GhidraScriptUtil.acquireBundleHostReference()
try:
    from ghidra.program.util import GhidraProgramUtilities
    from ghidra.app.plugin.core.analysis import AutoAnalysisManager
    mgr = AutoAnalysisManager.getAnalysisManager(prog)
    mgr.reAnalyzeAll(None)
    mgr.startAnalysis(monitor)
finally:
    GhidraScriptUtil.releaseBundleHostReference()
print("REANALYZE_TIME_SEC:", time.time()-t0)

print("FUNC_COUNT_AFTER_SYMBOLS:", fm.getFunctionCount())

proj.save(prog)
proj.close()
print("DONE")
