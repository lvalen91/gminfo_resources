#!/usr/bin/env python3
"""Step 7: find code that references key strings (calibrations EMMC save, VIP HDLC),
decompile the containing functions, and dump to files for manual review."""
import pyghidra
PROJ_DIR = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "hostos_x86"
pyghidra.start(verbose=False)
from ghidra.base.project import GhidraProject
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.app.decompiler import DecompInterface
from ghidra.util.exception import CancelledException

monitor = ConsoleTaskMonitor()
proj = GhidraProject.openProject(PROJ_DIR + "/" + PROJ_NAME, PROJ_NAME, True)
prog = proj.openProgram("/", "hostos.elf", False)
af = prog.getAddressFactory().getDefaultAddressSpace()
fm = prog.getFunctionManager()
refmgr = prog.getReferenceManager()
lst = prog.getListing()

targets = {
 0x00e092f6: "Saving calibrations to EMMC",
 0x00e093f5: "PAL version mismatch",
 0x00e0943d: "Calibration table version mismatch",
 0x00e0960d: "Failed to load calibrations from EMMC",
 0x0086a3f0: "[VIP] received bad HDLC sequence number from VIP",
 0x0086a3b8: "Got IPC msg on invalid channel: %u",
 0x0086a3dc: "IPC Channels Opened",
 0x0086a358: "Disabling Android client, invalid message size of %u bytes",
 0x0086a394: "Dropped %u bytes from Android",
 0x0086a72c: "MainLoop",
 0x0086a0cd: "Cache IPC msg: Index=%u, toVip=%u, clientMask=0x%02x",
}

decomp = DecompInterface()
decomp.openProgram(prog)

out_lines = []
funcs_to_decompile = set()
for addr_int, label in targets.items():
    a = af.getAddress(addr_int)
    refs = refmgr.getReferencesTo(a)
    refs = list(refs)
    out_lines.append("STRING %s @ 0x%x : %d xrefs" % (label, addr_int, len(refs)))
    for r in refs:
        frm = r.getFromAddress()
        fn = fm.getFunctionContaining(frm)
        fname = fn.getName() if fn else "???"
        faddr = fn.getEntryPoint() if fn else frm
        out_lines.append("   from %s (in func %s @ %s)" % (frm, fname, faddr))
        if fn is not None:
            funcs_to_decompile.add(fn)

print("\n".join(out_lines))
print("FUNCS_TO_DECOMPILE:", len(funcs_to_decompile))

with open("/tmp/hostos_xref_report.txt", "w") as f:
    f.write("\n".join(out_lines) + "\n\n")
    for fn in funcs_to_decompile:
        f.write("==== %s @ %s ====\n" % (fn.getName(), fn.getEntryPoint()))
        res = decomp.decompileFunction(fn, 30, monitor)
        if res.decompileCompleted():
            f.write(res.getDecompiledFunction().getC())
        else:
            f.write("DECOMPILE FAILED: %s\n" % res.getErrorMessage())
        f.write("\n\n")

print("wrote /tmp/hostos_xref_report.txt")
proj.close()
print("DONE")
