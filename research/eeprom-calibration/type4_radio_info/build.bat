@echo off
REM ============================================================================
REM  Build the "Read Radio Controller Info" Type4 DLL (x86) on the DPS box.
REM  Run from an "x86 Native Tools Command Prompt for VS" so cl/lib/link are x86.
REM  Requires: tisvcsv4.dll present (from the Bosch VTX-VCI GM install).
REM ============================================================================
setlocal

REM --- point this at your tisvcsv4.dll (default GM install path) -------------
set TISDLL="C:\Program Files (x86)\Bosch\VTX-VCI\VCI Software (GM)\Products\MDI 2\Dynamic Link Libraries\tisvcsv4.dll"
if not exist %TISDLL% (
  echo [!] tisvcsv4.dll not found at %TISDLL% - edit TISDLL in this script.
  exit /b 1
)

REM --- 1) generate an import lib from the DLL's exports ----------------------
REM    dumpbin lists decorated names; we build a .def of the ones we call, then lib /def.
echo LIBRARY tisvcsv4 > tisvcsv4.def
echo EXPORTS >> tisvcsv4.def
for %%N in (
  "??0CBuildService@@QAE@AAVIVcsUI@@@Z"
  "??1CBuildService@@QAE@XZ"
  "?SetInitToType4Mode@CBuildService@@QAEXXZ"
  "?BuildRequestedService@CBuildService@@QAEPAVCServiceCollection@@W4eProtocol@IVcsUI@@GAAW4eRetCodeEve@ISpsEvent@@@Z"
  "?GetInterface@CServiceInterface@@QAE_NAAPAUISerUdsExp2@@@Z"
) do echo     %%~N >> tisvcsv4.def
lib /nologo /def:tisvcsv4.def /machine:x86 /out:tisvcsv4.lib
if errorlevel 1 (echo [!] lib failed & exit /b 1)

REM --- 2) compile + link the Type4 DLL --------------------------------------
cl /nologo /LD /EHsc /MT /O2 /DWIN32 ^
   RadioControllerInfo.cpp ^
   /Fe:10018100.dll ^
   /link /DEF:RadioControllerInfo.def /MACHINE:X86 tisvcsv4.lib
if errorlevel 1 (echo [!] build failed & exit /b 1)

echo.
echo [ok] Built 10018100.dll  (+ 10018101.cfx alongside it).
echo     Deploy per README section 4.
endlocal
