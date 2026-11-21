import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.MemoryBlock;
import java.io.*;
import java.util.*;

public class DecompExports extends GhidraScript {
    public void run() throws Exception {
        Program p = currentProgram;
        String outFile = "/tmp/" + p.getName().replace(".dll","") + "_decomp.c";
        PrintWriter w = new PrintWriter(new FileWriter(outFile));
        w.println("// === " + p.getName() + " ===");
        w.println("// ImageBase: " + p.getImageBase());
        w.println();

        FunctionManager fm = p.getFunctionManager();
        SymbolTable st = p.getSymbolTable();

        // Collect named (non-FUN_) functions: exports, debug syms
        Set<Function> targets = new LinkedHashSet<>();
        Set<String> wantPrefix = new HashSet<>(Arrays.asList(
            "sa015bcr","getVersion","EscSha256","GetPsaKey","GetPsaVersion",
            "ConfigParser","WinInetClient","cwsdldecoder","ConnectToServer","StartHTTPS",
            "SendRequest","Process200OK","ProcessHttpStatus","WriteResponse","SetupServerInfo",
            "parseURL","parseConfigData","getConfigFilePath","Split","parseXMLServerInfo"
        ));
        for (Function f : fm.getFunctions(true)) {
            String n = f.getName();
            if (n.startsWith("FUN_") || n.startsWith("thunk_") || n.startsWith("UndefinedFunction_")) continue;
            for (String pref : wantPrefix) {
                if (n.contains(pref)) { targets.add(f); break; }
            }
            if (targets.size() >= 80) break;
        }
        w.println("// " + targets.size() + " functions matched name-filter");
        w.println();

        // Add called callees one level deep for context
        Set<Function> withCallees = new LinkedHashSet<>(targets);
        for (Function f : new ArrayList<>(targets)) {
            for (Function callee : f.getCalledFunctions(monitor)) {
                if (!callee.getName().startsWith("_") || callee.getName().contains("Sha")) {
                    withCallees.add(callee);
                }
                if (withCallees.size() > 150) break;
            }
        }
        w.println("// total with callees: " + withCallees.size());

        DecompInterface di = new DecompInterface();
        di.openProgram(p);

        for (Function f : withCallees) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            w.println("//===== " + f.getName() + " @ " + f.getEntryPoint() + " size=" + f.getBody().getNumAddresses() + " =====");
            if (r != null && r.getDecompiledFunction() != null) {
                w.println(r.getDecompiledFunction().getC());
            } else {
                w.println("// decompile failed");
            }
            w.println();
        }
        w.close();
        di.dispose();
        println("WROTE " + outFile);
    }
}
