// Ghidra headless post-script (Java): extract CRC/EEPROM-relevant functions from VIP firmware.
// analyzeHeadless <proj> <name> -process -noanalysis -readOnly -scriptPath <dir> -postScript extract_crc.java <OUTDIR>
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.io.*;
import java.util.*;
import java.util.regex.*;

public class extract_crc extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String OUT = args.length > 0 ? args[0] : "/tmp/vip_out";
        String STRTSV = args.length > 1 ? args[1] : null;  // addr<TAB>content list (base=0)
        new File(OUT).mkdirs();

        FunctionManager fm = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        ReferenceManager rm = currentProgram.getReferenceManager();
        println("PROGRAM " + currentProgram.getName() + " lang=" + currentProgram.getLanguageID()
                + " base=" + currentProgram.getImageBase() + " nfunc=" + fm.getFunctionCount());

        Pattern RX = Pattern.compile("(?i)crc|cksum|checksum|eeprom|calgroup|reinstat|cal_|\\[cal\\]|harman|nvm");
        Pattern PRIMARY = Pattern.compile("(?i)crc|cksum|checksum|eeprom|calgroup|harman|nvm");

        Map<String, Set<String>> target = new TreeMap<String, Set<String>>();
        Set<String> primary = new HashSet<String>();

        // 1) candidate string addresses (from external TSV: addrHex<TAB>content) -> referencing funcs.
        //    Refs are resolved by address, independent of whether the string is typed as data.
        List<String[]> strRows = new ArrayList<String[]>();
        Map<Long, String> addr2content = new HashMap<Long, String>();   // string addr -> content
        Set<Long> primaryAddr = new HashSet<Long>();
        Map<Long, TreeSet<String>> addr2fns = new HashMap<Long, TreeSet<String>>();
        if (STRTSV != null) {
            BufferedReader br = new BufferedReader(new FileReader(STRTSV));
            String line;
            while ((line = br.readLine()) != null) {
                int tab = line.indexOf('\t');
                if (tab < 0) continue;
                String addrHex = line.substring(0, tab).trim();
                String s = line.substring(tab + 1);
                if (s == null || !RX.matcher(s).find()) continue;
                boolean isp = PRIMARY.matcher(s).find();
                Address sa;
                try { sa = toAddr(addrHex); } catch (Exception e) { continue; }
                long key = sa.getOffset();
                addr2content.put(key, s);
                addr2fns.put(key, new TreeSet<String>());
                if (isp) primaryAddr.add(key);
                // (a) explicit references, if any exist
                ReferenceIterator refs = rm.getReferencesTo(sa);
                while (refs.hasNext()) {
                    Reference r = refs.next();
                    Function f = fm.getFunctionContaining(r.getFromAddress());
                    if (f != null) {
                        String e = f.getEntryPoint().toString();
                        add(target, primary, e, "str:" + trim(s, 48), isp);
                        addr2fns.get(key).add(e);
                    }
                }
            }
            br.close();

            // (b) fallback: scan instruction scalar/address operands for these string addresses
            //     (V850 loads low addresses as a single movea/mov immediate -> appears as a scalar).
            InstructionIterator ii = listing.getInstructions(true);
            while (ii.hasNext()) {
                Instruction ins = ii.next();
                int nops = ins.getNumOperands();
                for (int op = 0; op < nops; op++) {
                    for (Object o : ins.getOpObjects(op)) {
                        Long v = null;
                        if (o instanceof Scalar) v = ((Scalar) o).getUnsignedValue();
                        else if (o instanceof Address) v = ((Address) o).getOffset();
                        if (v == null || !addr2content.containsKey(v)) continue;
                        Function f = fm.getFunctionContaining(ins.getAddress());
                        if (f == null) continue;
                        String e = f.getEntryPoint().toString();
                        add(target, primary, e, "ldstr:" + trim(addr2content.get(v), 48),
                            primaryAddr.contains(v));
                        addr2fns.get(v).add(e);
                    }
                }
            }
            for (Map.Entry<Long, String> en : addr2content.entrySet())
                strRows.add(new String[]{ Long.toHexString(en.getKey()),
                    trim(en.getValue().replace("\"", "'"), 160),
                    String.join(";", addr2fns.get(en.getKey())) });
        }

        // 2) function name matches
        FunctionIterator fit = fm.getFunctions(true);
        while (fit.hasNext()) {
            Function f = fit.next();
            String nm = f.getName();
            if (RX.matcher(nm).find())
                add(target, primary, f.getEntryPoint().toString(), "name", PRIMARY.matcher(nm).find());
        }
        println("after pass1/2: " + target.size() + " targets, " + primary.size() + " primary");

        // 3) expand 1-hop callees + callers of PRIMARY functions
        for (String e : new ArrayList<String>(primary)) {
            Function f = fm.getFunctionAt(toAddr(e));
            if (f == null) continue;
            for (Function c : f.getCalledFunctions(monitor))
                add(target, primary, c.getEntryPoint().toString(), "callee_of:" + e, false);
            for (Function c : f.getCallingFunctions(monitor))
                add(target, primary, c.getEntryPoint().toString(), "caller_of:" + e, false);
        }
        println("after expand: " + target.size() + " targets");

        // 4) decompile all targets
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        PrintWriter idx = new PrintWriter(new FileWriter(new File(OUT, "index.csv")));
        idx.println("entry,name,size,reasons");
        int done = 0;
        for (String e : target.keySet()) {
            Function f = fm.getFunctionAt(toAddr(e));
            if (f == null) continue;
            String name = f.getName();
            long size = f.getBody().getNumAddresses();
            String reasons = String.join(" | ", new TreeSet<String>(target.get(e)));
            idx.println(e + "," + name + "," + size + ",\"" + reasons.replace("\"", "'") + "\"");
            String code;
            try {
                DecompileResults res = dec.decompileFunction(f, 90, monitor);
                code = (res != null && res.getDecompiledFunction() != null)
                        ? res.getDecompiledFunction().getC() : "// DECOMP FAILED";
            } catch (Exception ex) { code = "// DECOMP EXC " + ex; }
            String safe = name.replaceAll("[^A-Za-z0-9_]", "_");
            if (safe.length() > 40) safe = safe.substring(0, 40);
            PrintWriter fh = new PrintWriter(new FileWriter(new File(OUT, "f_" + e + "_" + safe + ".c")));
            fh.println("// entry=" + e + " name=" + name + " size=" + size);
            fh.println("// reasons: " + reasons + "\n");
            fh.println(code);
            fh.close();
            done++;
        }
        idx.close();

        // 5) strings xref dump
        PrintWriter sf = new PrintWriter(new FileWriter(new File(OUT, "strings_xref.csv")));
        sf.println("addr,content,referencing_funcs");
        for (String[] row : strRows)
            sf.println(row[0] + ",\"" + row[1] + "\",\"" + row[2] + "\"");
        sf.close();

        println("=== DONE: decompiled " + done + " functions to " + OUT + " ===");
    }

    private void add(Map<String, Set<String>> target, Set<String> primary,
                     String entry, String reason, boolean isPrimary) {
        Set<String> s = target.get(entry);
        if (s == null) { s = new TreeSet<String>(); target.put(entry, s); }
        s.add(reason);
        if (isPrimary) primary.add(entry);
    }

    private String trim(String s, int n) { return s.length() > n ? s.substring(0, n) : s; }
}
