# Type4 App — "Read Radio Controller Info" (ECU 0x80 / A11 CSM)

A GM DPS **Type4 application** that talks to the radio and prints its controller info — a
programmable stand-in for DPS's built-in "Get Controller Info / SBI" read. **Read-only**: it
issues only `$10 03` + a sequence of `$22` ReadDataByIdentifier requests (no `$27`, no writes,
no `$11` reset), which is exactly what a successful external DPS read-x80 capture
(`dps_readx80.Txt`, not in this repo) shows — the radio answers with no SecurityAccess.

## 1. What a Type4 app is (so the files make sense)
DPS loads a Type4 app as a pair (see the known-good example in `../canbus_reset/`):
- **`10018100.dll`** — a PE32 interpreter that drives UDS through `tisvcsv4.dll`. DPS copies it to
  `%USERPROFILE%\sps\type4\Type4App.dll`, `LoadLibrary`s it, and calls its exported
  `int Launch(void* pVcsUI, void* pCtx)` (confirmed in `dpsvcs.dll`). `0` = success.
- **`10018101.cfx`** — the workflow XML (button `Text` + `Action Id`). Our DLL keys off
  `Action Id="2200"`.

The VCS layer (`tisvcsv4.dll`) owns CAN/DoIP routing and TesterPresent based on the vehicle DPS
has loaded, so the app does **not** hardcode the ECU address — DPS already has the radio (ECU
`0x80`) selected as the target when it launches us.

## 2. Files
| file | role |
|---|---|
| `RadioControllerInfo.cpp` | the interpreter: `Launch` reads the DID list and formats the report; `GetResult` hands the text back to DPS |
| `tisvcsv4_iface.h` | reconstructed `tisvcsv4.dll` decls; each method's expected **decorated export name** is in a comment |
| `RadioControllerInfo.def` | undecorated exports DPS resolves (`Launch/GetResult/SetInternal/CMessage`) |
| `10018101.cfx` | Type4 workflow config (Action/Text `2200`) |
| `build.bat` | generates `tisvcsv4.lib` from the DLL, then compiles `10018100.dll` (x86) |

## 3. The DID sequence (exactly what DPS asked ECU 0x80)
`F190`(VIN) · `F1CB`/`F1CC`(end/base model no.) · `F180`/`F181`/`F182`(boot/app/cal module tables) ·
`F197`*(NRC 0x31)* · `F198`(repair-shop/SN) · `F199`(prog date, BCD) · `F09A`*(NRC)* · `F1A0`(MEC) ·
`F0F0`/`F0F1`/`F0F2`/`F0F3`(PSI/PEC/BIS/ECUID) · `E0B2`/`F0F4`/`F0F8`/`E0B5`*(NRC)* ·
`F0B4`(traceability) · `F0AB`(CVPPS) · `F0B3`(DUNS) · `F081`(MAC cfg).
DIDs marked *(NRC)* are the ones the real radio rejects; the app skips them silently, and it loops
on `7F xx 78` responsePending (as DPS does for `F0F0`/`F0F3`/`F0B4`). Golden decoded output to
compare against the external `CSM_Y181B_SBI.Txt` SBI readout (not in this repo).

## 4. Build & deploy (on the DPS/Windows box)
1. Open an **x86 Native Tools Command Prompt for VS**, `cd` into this folder.
2. `build.bat` — edit `TISDLL` first if your `tisvcsv4.dll` path differs. Produces `10018100.dll`.
3. Package the SPAT archive: `python make_spat.py` → `RadioControllerInfo_Type4.zip`.
4. **Load in DPS**: click the **"Type 4 Application"** button → **Browse** → select
   `RadioControllerInfo_Type4.zip` → **OK**. DPS lists the files by Mod ID (`0 = 10018100`,
   `1 = 10018101`); run the action. The report comes back through `GetResult`. (If the
   "Type 4 Application" button isn't visible, it must be enabled first — CameraLoops lesson 2.)

### 4a. SPAT archive — authoritative workflow vs. `make_spat.py`
The GM-taught build (CameraLoops "Create GM DPS Type4" lessons 1–2): a real SPS event downloads
the blobs into `%USERPROFILE%\sps\spsCache\spsCacheInternal`, you read the **`SPSToolBridge.LOG`
"SPS reprogramming info"** block for the Blob name/ID/order, then the **DPS Service Programming
Archive Tool (SPAT, `C:\DPS\SPAT`)** builds the ZIP from those files in **descending Blob-ID order**
against a `calfil0N.DTM` layout template (N = files-minus-one), emitting the `.tbl` manifest.

`make_spat.py` reproduces that tool's ZIP output directly (verified byte-structure-identical to the
real `A11_ECU_Reset.zip` type-4 application from the external GM DPS toolchain, not in this repo), so you don't need to drive the SPAT GUI. A
Type4-**app** archive is a flat, *stored* (uncompressed) zip of raw files named by part number
(no extension):

| entry | Mod/Blob ID | contents |
|---|---|---|
| `10018100` | 0 | Utility File — the interpreter DLL (raw MZ PE) |
| `10018101` | 1 | Description of Cal — the `.cfx` workflow XML (raw) |
| `radioinfo.tbl` | — | table manifest: `u32` entry-count(=2) + fixed 96-byte records (filename `@+0`, type tag `@+50`). Byte-cloned from GM's `a11reset.tbl` with the two part numbers swapped — shipped here. |

A read utility is a **2-file** set (Utility DLL ID 0 + cfx ID 1). Multi-file sets — a second `.dll`,
a `.cfg`, and a `.zip` at IDs 16/17/18 — are calibration-**flash** events, not reads
(`../DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` §4). `Vit2File.vit` / `SPSToolBridge.txt` /
`delivery_manifest.csv` / `.smd` are likewise flash-event artifacts, not needed here.

## 5. The ONE thing to verify before you trust the output
The setup calls (`CBuildService` ctor, `SetInitToType4Mode`, `BuildRequestedService`,
`CServiceInterface::GetInterface`) are **name-exported** and link cleanly. The actual `$22`
send/receive goes through the **`ISerUdsExp2` vtable**, which is *not* name-exported — its method
order in `tisvcsv4_iface.h` (`ReadDataByIdentifier` / `Execute` / `GetResponse`) is a best-effort
reconstruction. Confirm the real order before relying on results:
- `dumpbin /EXPORTS tisvcsv4.dll` won't show vtable slots; instead inspect the `ISerUdsExp2`
  vftable in the disassembly (`tisvcsv4.dll.pseudocode.txt` in the external GM DPS disassembly corpus, not in this repo; RTTI near the
  `ISerUdsExp2::vftable` sites ~line 97534), **or** use the GM `tisvcsv4` SDK header if you have it.
- Fix the three function-pointer slots in `struct ISerUdsExp2::VTable` to match, rebuild.
- Also confirm `IVcsUI::eProtocol` value for this vehicle's radio link (the `proto` in `Launch`)
  and the `SID_ReadDataByIdentifier` selector against a real `SPSToolBridge.LOG`.

Everything else — the export contract, the by-name service API, the DID list, NRC handling, and
the SBI decode — is taken from the RE and the two successful DPS reads and needs no guessing.

## 6. Scope / honesty
This is source you build on the DPS box; it is **not** a prebuilt binary (a Type4 DLL must link
against the machine's `tisvcsv4.dll`). It reads only. It does not compute `$27` — none is needed
for these DIDs. If a future variant needs writes/reset, the `$27` seed/key gate applies (see
`../DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` §6) and is out of scope here.
