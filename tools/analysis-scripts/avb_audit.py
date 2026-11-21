# Ghidra post-script: locate libavb functions via string xrefs, dump callees, spot CVE patterns
from ghidra.program.model.symbol import RefType
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

fm = currentProgram.getFunctionManager()
mem = currentProgram.getMemory()
listing = currentProgram.getListing()
refmgr = currentProgram.getReferenceManager()
st = currentProgram.getSymbolTable()

# Find strings and map to functions using them (via references)
def find_str_addrs(substr):
    out = []
    it = mem.getAllInitializedAddressSet().getAddresses(True)
    # Use DataIterator for defined strings instead
    data_it = listing.getDefinedData(True)
    for d in data_it:
        try:
            v = d.getValue()
            if v is None: continue
            s = str(v)
            if substr in s:
                out.append((d.getAddress(), s[:80]))
        except:
            pass
    return out

def funcs_using_str(str_addr):
    funcs = set()
    refs = refmgr.getReferencesTo(str_addr)
    for r in refs:
        f = fm.getFunctionContaining(r.getFromAddress())
        if f: funcs.add(f)
    return funcs

markers = [
    ("avb_slot_verify",              "Error verifying vbmeta image"),
    ("avb_vbmeta_image_verify",      "INVALID_VBMETA_HEADER"),
    ("avb_descriptor_foreach_or_walk","Invalid data in descriptors array"),
    ("avb_descriptor_validate",      "Invalid descriptor length"),
    ("avb_descriptor_foreach_div8",  "Descriptor size is not divisible by 8"),
    ("avb_hashtree_descriptor_validate", "Invalid tag for hashtree descriptor"),
    ("avb_hash_descriptor_validate",     "Invalid tag for hash descriptor"),
    ("avb_chain_partition_descriptor_validate", "Invalid tag for chain partition descriptor"),
    ("avb_kernel_cmdline_descriptor_validate",  "Invalid tag for kernel cmdline descriptor"),
    ("avb_footer_parse_msg",         "Invalid vbmeta size in footer"),
    ("avb_slot_verify_chain_err",    "Chain partition descriptor is invalid"),
    ("avb_slot_verify_hashtree_err", "Hashtree descriptor is invalid"),
    ("avb_slot_verify_too_many",     "Too many vbmeta images"),
    ("avb_payload_overflow",         "Descriptor payload size overflow"),
    ("avb_overflow_adding",          "Overflow when adding values"),
    ("avb_overflow_total_len",       "Overflow while determining total length"),
    ("avb_overflow_bootimg",         "Overflow while computing size of boot image"),
    ("avb_overflow_sizes",           "Overflow while adding up sizes"),
    ("avb_chain_rollback",           "Chain partition has invalid rollback_index_location"),
    ("avb_chain_pubkey_mismatch",    "Public key used to sign data does not match"),
    ("avb_digest_size_mismatch",     "Digest in descriptor not of expected size"),
    ("avb_digest_mismatch",          "Hash of data does not match digest"),
]

print("=== STRING -> FUNCTION MAP ===")
results = {}
for label, marker in markers:
    hits = find_str_addrs(marker)
    for addr, s in hits:
        fs = funcs_using_str(addr)
        for f in fs:
            key = f.getEntryPoint().toString()
            results.setdefault(key, set()).add(label)
            print("%-50s @ %s  size=%d  str=%s" % (f.getName(), key, f.getBody().getNumAddresses(), label))

print("\n=== FUNCTION SUMMARY ===")
for ep, labels in sorted(results.items()):
    f = fm.getFunctionAt(currentProgram.getAddressFactory().getAddress(ep))
    if f:
        print("%s  size=%d  markers=%s" % (ep, f.getBody().getNumAddresses(), ",".join(sorted(labels))))

# Decompile key functions
di = DecompInterface(); di.openProgram(currentProgram)
mon = ConsoleTaskMonitor()

print("\n=== DECOMPILATION OF KEY FUNCTIONS ===")
targets_labels = ["avb_slot_verify", "avb_vbmeta_image_verify", "avb_descriptor_foreach_or_walk",
                  "avb_hashtree_descriptor_validate", "avb_chain_partition_descriptor_validate",
                  "avb_payload_overflow", "avb_footer_parse_msg", "avb_slot_verify_chain_err",
                  "avb_slot_verify_too_many"]
dumped = set()
for ep, labels in results.items():
    if not (labels & set(targets_labels)): continue
    if ep in dumped: continue
    dumped.add(ep)
    f = fm.getFunctionAt(currentProgram.getAddressFactory().getAddress(ep))
    if not f: continue
    dr = di.decompileFunction(f, 90, mon)
    if dr and dr.getDecompiledFunction():
        print("\n---- FUNC %s @ %s  (markers: %s) ----" % (f.getName(), ep, ",".join(sorted(labels))))
        print(dr.getDecompiledFunction().getC())

# Look for format string usage risk: find calls passing vbmeta-derived string to avb_print-like
# Look for memcpy/alloca
print("\n=== MEMCPY/MEMMOVE CALLS IN AVB FUNCS ===")
for ep in results:
    f = fm.getFunctionAt(currentProgram.getAddressFactory().getAddress(ep))
    if not f: continue
    called = f.getCalledFunctions(mon)
    for c in called:
        n = c.getName().lower()
        if "memcpy" in n or "memmove" in n or "alloca" in n or "strcpy" in n or "strcat" in n:
            print("%s -> %s" % (f.getName(), c.getName()))
