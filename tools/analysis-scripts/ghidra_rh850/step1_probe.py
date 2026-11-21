import pyghidra, os, sys

BIN = "/Volumes/stuff/misc/research/GM_research/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y175/extracted/85759599"
PROJ_LOC = "/Users/zeno/Downloads/github/gminfo_resources/research/scripts/ghidra_rh850"
PROJ_NAME = "85759599_rh850"

with pyghidra.open_program(
    BIN,
    project_location=PROJ_LOC,
    project_name=PROJ_NAME,
    analyze=True,
    language="RH850:LE:32:default",
    loader="ghidra.app.util.opinion.BinaryLoader",
    program_name="VIP_APP_85759599",
) as flat_api:
    program = flat_api.getCurrentProgram()
    print("LANGUAGE:", program.getLanguage().getLanguageID())
    print("IMAGE BASE:", program.getImageBase())
    listing = program.getListing()

    from ghidra.program.model.address import AddressSet

    for addr in [0xc8f6a, 0xc90c4]:
        a = program.getAddressFactory().getDefaultAddressSpace().getAddress(addr)
        fn = flat_api.getFunctionAt(a)
        print("----", hex(addr), fn)
        if fn is None:
            # try to disassemble/create function
            flat_api.disassemble(a)
            fn = flat_api.createFunction(a, "FUN_%08x" % addr)
            print("created:", fn)

    # Decompile the two known functions
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)

    for addr in [0xc8f6a, 0xc90c4]:
        a = program.getAddressFactory().getDefaultAddressSpace().getAddress(addr)
        fn = flat_api.getFunctionAt(a)
        if fn is None:
            print("NO FUNCTION at", hex(addr))
            continue
        res = di.decompileFunction(fn, 60, None)
        print("=========== DECOMPILE", hex(addr), fn.getName(), "===========")
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC())
        else:
            print("decompile failed:", res.getErrorMessage())
