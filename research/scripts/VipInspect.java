import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;
import java.io.*;
import java.util.*;

public class VipInspect extends GhidraScript {
    public void run() throws Exception {
        Program p = currentProgram;
        PrintWriter w = new PrintWriter(new FileWriter("/tmp/vip_inspect.txt"));
        w.println("NAME: " + p.getName());
        w.println("LANG: " + p.getLanguageID());
        w.println("COMPILER: " + p.getCompilerSpec().getCompilerSpecID());
        w.println("BASE: " + p.getImageBase());
        w.println();
        w.println("=== MEMORY BLOCKS ===");
        for (MemoryBlock b : p.getMemory().getBlocks()) {
            w.printf("%-30s %s-%s size=%d r=%b w=%b x=%b init=%b%n",
                b.getName(), b.getStart(), b.getEnd(), b.getSize(),
                b.isRead(), b.isWrite(), b.isExecute(), b.isInitialized());
        }
        w.println();
        FunctionManager fm = p.getFunctionManager();
        int total=0, named=0;
        List<String> namedList = new ArrayList<>();
        for (Function f : fm.getFunctions(true)) {
            total++;
            String n = f.getName();
            if (!n.startsWith("FUN_") && !n.startsWith("thunk_") && !n.startsWith("UndefinedFunction_")) {
                named++;
                namedList.add(f.getEntryPoint()+" "+n+" size="+f.getBody().getNumAddresses());
            }
        }
        w.println("FUNCTIONS: " + total + " (user-named: " + named + ")");
        w.println("=== NAMED FUNCTIONS ===");
        for (String s : namedList) w.println("  " + s);
        w.println();

        // Labels/symbols created by user
        w.println("=== USER LABELS ===");
        SymbolTable st = p.getSymbolTable();
        SymbolIterator it = st.getAllSymbols(false);
        int lcount = 0;
        while (it.hasNext() && lcount < 500) {
            Symbol s = it.next();
            if (s.getSource() == SourceType.USER_DEFINED) {
                w.println("  "+s.getAddress()+" "+s.getName()+" ["+s.getSymbolType()+"]");
                lcount++;
            }
        }
        w.println("USER_LABELS_TOTAL: " + lcount);
        w.println();

        // Bookmarks (user analysis notes)
        w.println("=== BOOKMARKS ===");
        BookmarkManager bm = p.getBookmarkManager();
        int bc = 0;
        Iterator<Bookmark> bIt = bm.getBookmarksIterator();
        while (bIt.hasNext() && bc < 200) {
            Bookmark b = bIt.next();
            w.println("  "+b.getAddress()+" ["+b.getType()+"/"+b.getCategory()+"] "+b.getComment());
            bc++;
        }
        w.println("BOOKMARKS_TOTAL: " + bc);
        w.println();

        // Comments
        w.println("=== PLATE/PRE/POST COMMENTS (user) ===");
        Listing lst = p.getListing();
        int cc = 0;
        for (CodeUnit cu : lst.getCodeUnits(true)) {
            for (int t : new int[]{CodeUnit.PLATE_COMMENT, CodeUnit.PRE_COMMENT, CodeUnit.POST_COMMENT, CodeUnit.EOL_COMMENT}) {
                String com = cu.getComment(t);
                if (com != null && !com.isEmpty()) {
                    w.println("  "+cu.getAddress()+" t="+t+" "+com.replace("\n","\\n"));
                    cc++;
                    if (cc > 200) break;
                }
            }
            if (cc > 200) break;
        }
        w.println("COMMENTS_TOTAL: " + cc);
        w.close();
        println("WROTE /tmp/vip_inspect.txt");
    }
}
