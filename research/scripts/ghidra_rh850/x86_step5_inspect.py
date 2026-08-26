#!/usr/bin/env python3
"""Inspect functions/coverage gaps in calibrations.text and vip_server.text."""
import pyghidra
PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"
pyghidra.start(verbose=False)
from ghidra.base.project import GhidraProject
proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = proj.openProgram("/", "hostos.elf", False)
af = prog.getAddressFactory().getDefaultAddressSpace()
fm = prog.getFunctionManager()
lst = prog.getListing()

def dump_range(lo, hi, label):
    print("=====", label, hex(lo), "-", hex(hi), "=====")
    a1 = af.getAddress(lo); a2 = af.getAddress(hi)
    fns = list(fm.getFunctions(prog.getAddressFactory().getAddressSet(a1,a2), True))
    print("num functions:", len(fns))
    for fn in fns[:40]:
        body = fn.getBody()
        print(" fn %s @ %s size=%d" % (fn.getName(), fn.getEntryPoint(), body.getNumAddresses()))
    # dump last instructions before gap ends
    print("--- disasm near entry ---")
    cu = lst.getCodeUnitAt(a1)
    addr = a1
    for i in range(50):
        cu = lst.getCodeUnitAt(addr)
        if cu is None:
            print(" (no code unit at)", addr); break
        print(" ", addr, cu.toString())
        nxt = cu.getMaxAddress().next()
        if nxt is None or nxt.compareTo(a2) > 0:
            break
        addr = nxt

dump_range(0x00df8000, 0x00e0830a, "calibrations.text")
dump_range(0x00860000, 0x00869966, "vip_server.text")

proj.close()
print("DONE")
