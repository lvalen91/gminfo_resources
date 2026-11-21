@echo off
REM Build the Type4 DLL (x86) with portable LLVM + lld, freestanding (no MSVC/SDK/CRT needed).
REM Run on the DPS box after portable LLVM is extracted to %LLVM%.
setlocal
set LLVM=C:\Users\zeno\llvm\bin
set TISDLL=C:\DPS\Type4 App Crash Optional Files\tisvcsv4.dll

if not exist "%LLVM%\clang.exe" ( echo [!] clang not at %LLVM% & exit /b 1 )
if not exist "%TISDLL%" ( echo [!] tisvcsv4.dll not at "%TISDLL%" & exit /b 1 )

REM --- 1) import lib for tisvcsv4.dll from the decorated names we call ---------
> tisvcsv4.def echo LIBRARY tisvcsv4.dll
>>tisvcsv4.def echo EXPORTS
>>tisvcsv4.def echo     ??0CBuildService@@QAE@AAVIVcsUI@@@Z
>>tisvcsv4.def echo     ??1CBuildService@@QAE@XZ
>>tisvcsv4.def echo     ?SetInitToType4Mode@CBuildService@@QAEXXZ
>>tisvcsv4.def echo     ?BuildRequestedService@CBuildService@@QAEPAVCServiceCollection@@W4eProtocol@IVcsUI@@GAAW4eRetCodeEve@ISpsEvent@@@Z
>>tisvcsv4.def echo     ?GetInterface@CServiceInterface@@QAE_NAAPAUISerUdsExp2@@@Z
"%LLVM%\llvm-lib.exe" /def:tisvcsv4.def /machine:x86 /out:tisvcsv4.lib
if errorlevel 1 ( echo [!] llvm-lib failed & exit /b 1 )

REM --- 2) compile + link the DLL (x86, freestanding) -------------------------
"%LLVM%\clang.exe" --target=i686-pc-windows-msvc -O2 -shared ^
   -fms-extensions -fms-compatibility -fdeclspec ^
   -fno-exceptions -fno-rtti -fno-stack-protector -mno-stack-arg-probe ^
   -ffreestanding -fno-builtin -nostdlib ^
   RadioControllerInfo.cpp tisvcsv4.lib ^
   -o 10018100.dll ^
   -Wl,/def:RadioControllerInfo.def -Wl,/noentry -Wl,/nodefaultlib -Wl,/subsystem:windows
if errorlevel 1 ( echo [!] clang/lld build failed & exit /b 1 )

echo [ok] built 10018100.dll
"%LLVM%\llvm-objdump.exe" -x 10018100.dll | findstr /i "Export DLL Name Launch GetResult"
endlocal
