// @category GHS
import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class GhsDump extends GhidraScript {
    public void run() throws Exception {
        PrintWriter w = new PrintWriter(new FileWriter("/tmp/ghs_analysis.txt"));
        Program p = currentProgram;
        w.println("NAME: " + p.getName());
        w.println("LANG: " + p.getLanguageID());
        w.println("COMPILER: " + p.getCompilerSpec().getCompilerSpecID());
        w.println("IMAGEBASE: " + p.getImageBase());
        w.println();
        w.println("=== MEMORY BLOCKS ===");
        for (MemoryBlock b : p.getMemory().getBlocks()) {
            w.printf("%-20s %s-%s size=%d r=%b w=%b x=%b%n",
                b.getName(), b.getStart(), b.getEnd(), b.getSize(),
                b.isRead(), b.isWrite(), b.isExecute());
        }
        w.println();

        FunctionManager fm = p.getFunctionManager();
        int fcount = 0;
        List<Function> all = new ArrayList<>();
        for (Function f : fm.getFunctions(true)) { fcount++; all.add(f); }
        w.println("FUNCTION_COUNT: " + fcount);
        w.println();

        // Largest functions
        all.sort((a,b)->Long.compare(b.getBody().getNumAddresses(), a.getBody().getNumAddresses()));
        w.println("=== TOP 60 LARGEST FUNCTIONS ===");
        for (int i=0; i<Math.min(60,all.size()); i++) {
            Function f = all.get(i);
            w.printf("%8d  %s  %s%n", f.getBody().getNumAddresses(), f.getEntryPoint(), f.getName());
        }
        w.println();

        // Interesting symbols by keyword
        String[] kws = {"IPC","AddressSpace","Kernel","syscall","Hyper","Virt","VMExit","VMCS","Schedule","Init","Boot","Load","Auth","Verify","Crypto","Cert","Signature","Seed","Cse","Trusty","Attest","Secure","Debug","Trace","Panic","Fault","Exception","Connect","Send","Recv","Message","Object","Task","Activity","Link","Mutex","Clock","Timer","Interrupt","HECI","AVB","Sign","Hash","Rollback","Update","Recovery","Measured","Root","Policy","Ioctl","Hypercall","Vmcall"};
        w.println("=== INTERESTING SYMBOLS ===");
        SymbolTable st = p.getSymbolTable();
        int symc = 0;
        SymbolIterator it = st.getAllSymbols(false);
        Map<String,Integer> kwCounts = new TreeMap<>();
        List<String> found = new ArrayList<>();
        while (it.hasNext()) {
            Symbol s = it.next();
            String n = s.getName();
            for (String k : kws) {
                if (n.toLowerCase().contains(k.toLowerCase())) {
                    kwCounts.merge(k,1,Integer::sum);
                    if (found.size()<800) found.add(String.format("%s  %s  [%s]", s.getAddress(), n, s.getSymbolType()));
                    symc++;
                    break;
                }
            }
        }
        w.println("TOTAL_MATCH: " + symc);
        for (Map.Entry<String,Integer> e : kwCounts.entrySet()) w.printf("  %-15s %d%n", e.getKey(), e.getValue());
        w.println();
        w.println("=== SAMPLES (up to 800) ===");
        for (String s : found) w.println(s);

        // Strings
        w.println();
        w.println("=== NOTABLE STRINGS (containing keywords) ===");
        DataIterator di = p.getListing().getDefinedData(true);
        int sc = 0;
        while (di.hasNext() && sc < 500) {
            Data d = di.next();
            if (d.getDataType().getName().contains("string") || d.getDataType().getName().equals("string")) {
                Object v = d.getValue();
                if (v == null) continue;
                String sv = v.toString();
                if (sv.length() < 6 || sv.length() > 200) continue;
                String low = sv.toLowerCase();
                if (low.contains("ghs") || low.contains("integrity") || low.contains("addressspace") ||
                    low.contains("kernel") || low.contains("hyper") || low.contains("secure") ||
                    low.contains("verify") || low.contains("signature") || low.contains("cse") ||
                    low.contains("panic") || low.contains("ipc") || low.contains("avb") ||
                    low.contains("rollback") || low.contains("boot") || low.contains("heci")) {
                    w.printf("%s  %s%n", d.getAddress(), sv.replace("\n","\\n"));
                    sc++;
                }
            }
        }
        w.close();
        println("WROTE /tmp/ghs_analysis.txt");
    }
}
