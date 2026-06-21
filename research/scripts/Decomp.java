// @category GHS
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.data.*;
import ghidra.program.model.mem.MemoryBlock;
import java.io.*;
import java.util.*;

public class Decomp extends GhidraScript {
    public void run() throws Exception {
        Program p = currentProgram;
        PrintWriter w = new PrintWriter(new FileWriter("/tmp/vmm1_decomp.txt"));

        // Key string addresses in VMM1
        long[] strs = {
            0xf9d24aL, // "Signing key modulus mismatch"
            0xf9d3d6L, // "Signing key exponent mismatch"
            0xf9d39fL, // "Android signing key boot module not found"
            0xf9c691L, // "vbmeta signing key does not match known valid key"
            0xf9c6cfL, // "vbmeta: image verification failed!"
            0xf9c93fL, // "vbmeta bad header: descriptors outside data block"
            0xf9cc4cL, // "rollback index is too old"
            0xf9d04aL, // "Failed to load Android signing key"
            0xf9c8f6L, // "green"
            0xf9c933L, // "locked"
            0xf9c92cL, // "orange"
        };

        AddressFactory af = p.getAddressFactory();
        ReferenceManager rm = p.getReferenceManager();
        FunctionManager fm = p.getFunctionManager();
        Listing lst = p.getListing();

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(p);
        decomp.setSimplificationStyle("decompile");

        Set<Function> seen = new HashSet<>();
        for (long a : strs) {
            Address addr = af.getDefaultAddressSpace().getAddress(a);
            w.println("==================================================");
            w.println("STRING @ " + addr);
            Data d = lst.getDataAt(addr);
            if (d != null) w.println("  -> " + d.getValue());
            ReferenceIterator it = rm.getReferencesTo(addr);
            int refCount = 0;
            while (it.hasNext()) {
                Reference r = it.next();
                refCount++;
                Address from = r.getFromAddress();
                Function f = fm.getFunctionContaining(from);
                w.println("  refFrom " + from + (f != null ? " in " + f.getName()+" @"+f.getEntryPoint() : " (no func)"));
                if (f != null && !seen.contains(f)) {
                    seen.add(f);
                }
            }
            if (refCount == 0) w.println("  (no xrefs — may be loaded via pointer table)");
        }

        w.println();
        w.println("==================================================");
        w.println("DECOMPILING REFERRING FUNCTIONS (" + seen.size() + ")");
        w.println("==================================================");
        for (Function f : seen) {
            w.println();
            w.println("### " + f.getName() + " @ " + f.getEntryPoint() + " (size=" + f.getBody().getNumAddresses() + ") ###");
            DecompileResults dr = decomp.decompileFunction(f, 90, monitor);
            if (dr != null && dr.getDecompiledFunction() != null) {
                w.println(dr.getDecompiledFunction().getC());
            } else {
                w.println("<< decompile failed >>");
            }
        }

        // Also scan vmm1 .rodata pointer tables that reference the strings (common with GHS compiler)
        w.println();
        w.println("=== POINTER TABLES IN vmm1.rodata REFERENCING KEY STRINGS ===");
        MemoryBlock vmm1_rodata = p.getMemory().getBlock(".vmm1.rodata");
        if (vmm1_rodata != null) {
            Address s = vmm1_rodata.getStart();
            Address e = vmm1_rodata.getEnd();
            for (Address a = s; a.compareTo(e) < 0; a = a.add(4)) {
                try {
                    int val = p.getMemory().getInt(a);
                    long v = val & 0xFFFFFFFFL;
                    for (long t : strs) {
                        if (v == t) {
                            w.println(a + " -> " + Long.toHexString(t));
                            break;
                        }
                    }
                } catch (Exception ex) { break; }
            }
        }

        w.close();
        decomp.dispose();
        println("WROTE /tmp/vmm1_decomp.txt");
    }
}
