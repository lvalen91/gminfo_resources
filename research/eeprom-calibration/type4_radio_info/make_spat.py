#!/usr/bin/env python3
"""Package the Type4 blobs into a DPS SPAT archive.

A Type4-app SPAT archive (verified against the real gm_dps/type4_applications/A11_ECU_Reset.zip)
is just a flat zip of three RAW (uncompressed) files, named by part number without extension:

    RadioControllerInfo_Type4.zip
    +-- 10018100        Blob ID 0 : the interpreter DLL  (raw MZ PE, from build.bat's 10018100.dll)
    +-- 10018101        Blob ID 1 : the .cfx workflow XML (raw)
    +-- radioinfo.tbl   the table manifest (u32 entry-count + fixed 96-byte records:
                        filename @+0, type tag @+50; "Utility File" for the DLL, "Description of
                        Cal" for the cfx). Byte-cloned from the real GM a11reset.tbl.

Read-only app: NO Vit2File.vit / SPSToolBridge.txt / delivery_manifest.csv / .smd — those belong to
cal-FLASH events (DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md sec 4), not a Type4 read utility.

Usage (after build.bat produces 10018100.dll):
    python make_spat.py [--dll 10018100.dll] [--cfx 10018101.cfx] [--tbl radioinfo.tbl] [--out RadioControllerInfo_Type4.zip]
"""
import argparse, os, zipfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", default="10018100.dll")   # built by build.bat
    ap.add_argument("--cfx", default="10018101.cfx")
    ap.add_argument("--tbl", default="radioinfo.tbl")
    ap.add_argument("--out", default="RadioControllerInfo_Type4.zip")
    a = ap.parse_args()

    for f in (a.dll, a.cfx, a.tbl):
        if not os.path.exists(f):
            raise SystemExit(f"[!] missing {f}" + ("  (run build.bat first)" if f.endswith('.dll') else ""))

    dll = open(a.dll, "rb").read()
    if dll[:2] != b"MZ":
        raise SystemExit(f"[!] {a.dll} is not a PE/MZ image")
    cfx = open(a.cfx, "rb").read()
    tbl = open(a.tbl, "rb").read()
    if tbl[:4] != b"\x02\x00\x00\x00":
        print("[warn] table header != entry-count 2; continuing")
    # sanity: the table must reference our two part numbers
    for pn in (b"10018100", b"10018101"):
        if pn not in tbl:
            print(f"[warn] {pn.decode()} not found in {a.tbl}")

    # STORED (no compression) to match the real archive's raw payloads
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_STORED) as z:
        z.writestr("10018100", dll)      # DLL, part-number name, no extension
        z.writestr("10018101", cfx)      # cfx, no extension
        z.writestr(os.path.basename(a.tbl), tbl)
    print(f"[ok] wrote {a.out}: 10018100 ({len(dll)}B), 10018101 ({len(cfx)}B), "
          f"{os.path.basename(a.tbl)} ({len(tbl)}B)")

if __name__ == "__main__":
    main()
