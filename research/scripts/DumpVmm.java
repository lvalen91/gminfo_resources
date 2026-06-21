import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.MemoryBlock;
import java.io.*;
import java.util.*;

public class DumpVmm extends GhidraScript {
    public void run() throws Exception {
        Program p = currentProgram;
        MemoryBlock vmm1 = p.getMemory().getBlock(".vmm1.text");
        if (vmm1 == null) { println("no .vmm1.text"); return; }
        println("vmm1.text " + vmm1.getStart() + "-" + vmm1.getEnd());

        FunctionManager fm = p.getFunctionManager();
        List<Function> funcs = new ArrayList<>();
        for (Function f : fm.getFunctions(vmm1.getStart(), true)) {
            if (f.getEntryPoint().compareTo(vmm1.getEnd()) > 0) break;
            funcs.add(f);
        }
        println("functions: " + funcs.size());

        DecompInterface di = new DecompInterface();
        di.openProgram(p);

        PrintWriter w = new PrintWriter(new FileWriter("/tmp/vmm1_all.c"));
        int i = 0;
        for (Function f : funcs) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            w.println("//===== " + f.getName() + " @ " + f.getEntryPoint() + " size=" + f.getBody().getNumAddresses() + " =====");
            if (r != null && r.getDecompiledFunction() != null) {
                w.println(r.getDecompiledFunction().getC());
            } else {
                w.println("// decompile failed");
            }
            w.println();
            i++;
            if (i % 25 == 0) println("decompiled " + i + "/" + funcs.size());
        }
        w.close();
        di.dispose();
        println("WROTE /tmp/vmm1_all.c");
    }
}
