import pyghidra

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

TARGET_SNIPPETS = [
    "read eeprom error",
    "Failed to read to LngSelSignal from EEPROM",
    "Failed to read to TimeDispFormat Signal from EEPROM",
    "EEPROM Write Failure for CalGroup",
]

with pyghidra.open_program(
    BIN, project_location=PROJ_LOC, project_name=PROJ_NAME,
    analyze=False, program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    listing = program.getListing()
    fm = program.getFunctionManager()
    refm = program.getReferenceManager()
    af = program.getAddressFactory().getDefaultAddressSpace()
    def addr(a): return af.getAddress(a)

    dl = listing.getDefinedData(True)
    found = []
    for d in dl:
        try:
            v = d.getValue()
        except Exception:
            continue
        s = str(v) if v is not None else None
        if not s:
            continue
        for snip in TARGET_SNIPPETS:
            if snip in s:
                found.append((d.getAddress(), s))
                break

    print("matched strings:", len(found))
    # For each xref site, walk backward up to 40 instrs to find nearest jarl (call) before the string load
    call_targets = {}
    site_addrs = []
    for daddr, s in found:
        refs = refm.getReferencesTo(daddr)
        for r in refs:
            froma = r.getFromAddress()
            site_addrs.append((froma, s))

    site_addrs.sort(key=lambda t: int(t[0].getOffset()))
    print("total xref sites:", len(site_addrs))
    for froma, s in site_addrs:
        # collect a short window of instrs around froma, and look for jarl (call) at/after
        instrs = []
        ai = listing.getInstructions(froma, True)
        cnt = 0
        for i in ai:
            instrs.append(i)
            cnt += 1
            if cnt >= 6:
                break
        calls = [str(i) for i in instrs if i.getMnemonicString() == 'jarl']
        print(hex(int(froma.getOffset())), "->", s[:55], "| next jarl(s):", calls)
        for c in calls:
            call_targets[c] = call_targets.get(c, 0) + 1

    print()
    print("=== call target histogram ===")
    for c, n in sorted(call_targets.items(), key=lambda kv: -kv[1]):
        print(" ", c, "x", n)
