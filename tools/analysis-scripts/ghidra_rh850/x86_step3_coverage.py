#!/usr/bin/env python3
"""Step 3: byte-accounting coverage per memory block + disassemble-more pass for
undefined bytes inside executable/initialized blocks. Save results to TSV."""
import sys, time
import pyghidra

PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"

pyghidra.start(verbose=False)
from ghidra.base.project import GhidraProject
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.address import AddressSet
from ghidra.program.disassemble import Disassembler

monitor = ConsoleTaskMonitor()
proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = proj.openProgram("/", "hostos.elf", False)

mem = prog.getMemory()
lst = prog.getListing()

blocks = list(mem.getBlocks())
print("NUM_BLOCKS:", len(blocks))

rows = []
for b in blocks:
    name = b.getName()
    start = b.getStart()
    end = b.getEnd()
    size = b.getSize()
    initialized = b.isInitialized()
    execf = b.isExecute()
    if not initialized:
        rows.append((name, str(start), str(end), size, "NOBITS(uninit)", 0,0,0,0))
        continue
    # count code/data/undefined bytes using listing code unit iteration
    code_bytes = 0
    data_bytes = 0
    undef_bytes = 0
    addr_set = AddressSet(start, end)
    it = lst.getCodeUnits(addr_set, True)
    for cu in it:
        l = cu.getLength()
        from ghidra.program.model.listing import Instruction, Data
        if isinstance(cu, Instruction):
            code_bytes += l
        elif isinstance(cu, Data):
            if cu.isDefined():
                data_bytes += l
            else:
                undef_bytes += l
    rows.append((name, str(start), str(end), size, "exec" if execf else "data", code_bytes, data_bytes, undef_bytes, size-code_bytes-data_bytes-undef_bytes))

with open("/tmp/hostos_coverage.tsv","w") as f:
    f.write("name\tstart\tend\tsize\tkind\tcode_bytes\tdata_bytes\tundef_bytes\tother\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")

print("wrote /tmp/hostos_coverage.tsv")
proj.close()
print("DONE")
