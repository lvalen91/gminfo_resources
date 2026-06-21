# Ghidra headless post-script: dump GHS INTEGRITY analysis summary
from ghidra.program.model.symbol import SymbolType
from ghidra.program.model.listing import Function
import json, os

prog = currentProgram
fm = prog.getFunctionManager()
st = prog.getSymbolTable()
mm = prog.getMemory()
out = {}

out['name'] = prog.getName()
out['lang'] = str(prog.getLanguageID())
out['compiler'] = str(prog.getCompilerSpec().getCompilerSpecID())
out['image_base'] = str(prog.getImageBase())
out['entry'] = str(prog.getSymbolTable().getSymbols("entry").next().getAddress()) if prog.getSymbolTable().getSymbols("entry").hasNext() else "n/a"

# Memory blocks
out['blocks'] = []
for b in mm.getBlocks():
    out['blocks'].append({'name': b.getName(), 'start': str(b.getStart()), 'end': str(b.getEnd()), 'size': b.getSize(), 'r': b.isRead(), 'w': b.isWrite(), 'x': b.isExecute()})

# Function counts
funcs = list(fm.getFunctions(True))
out['function_count'] = len(funcs)

# Interesting symbols: IPC, AddressSpace, Kernel, syscall, Hypervisor, hypercall, vmcs, vmexit, schedule, init
keywords = ['IPC','AddressSpace','Kernel','syscall','Hyper','Virt','VMExit','VMCS','Schedule','Init','Boot','Load','Auth','Verify','Crypto','Cert','Signature','Seed','Cse','Trusty','Attest','Secure','Debug','Trace','Panic','Fault','Exception','Connect','Send','Recv','Message','Object','Task','Activity','Link','Mutex','Semaphore','Clock','Timer','Interrupt']
out['interesting_syms'] = []
for s in st.getAllSymbols(False):
    n = s.getName()
    if any(k.lower() in n.lower() for k in keywords):
        if s.getSymbolType() == SymbolType.FUNCTION or s.getSymbolType() == SymbolType.LABEL:
            out['interesting_syms'].append({'name': n, 'addr': str(s.getAddress()), 'type': str(s.getSymbolType())})
out['interesting_syms_count'] = len(out['interesting_syms'])
# cap
out['interesting_syms'] = out['interesting_syms'][:500]

# Imported/exported
out['exports'] = [{'name': s.getName(), 'addr': str(s.getAddress())} for s in st.getExternalSymbols()][:200]

# Top functions by size
sized = [(f.getName(), str(f.getEntryPoint()), f.getBody().getNumAddresses()) for f in funcs]
sized.sort(key=lambda x: -x[2])
out['largest_funcs'] = sized[:50]

with open('/tmp/ghs_analysis.json','w') as fp:
    json.dump(out, fp, indent=2, default=str)
print("WROTE /tmp/ghs_analysis.json")
