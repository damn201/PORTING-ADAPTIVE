@echo off
REM Build Uncharted PC Installer untuk Windows -> dist\UnchartedPCInstaller.exe (satu file).
REM Jalankan di Windows (Command Prompt / PowerShell) dari folder proyek.
REM Syarat: Python 3.12 terpasang dan ada di PATH.
cd /d %~dp0..
if not exist .venv (
  py -3.12 -m venv .venv
)
.venv\Scripts\pip install -q -r requirements.txt
.venv\Scripts\pyinstaller build\uncharted_installer.spec --noconfirm --workpath .pyinstaller-tmp --distpath dist
echo.
echo Selesai. File siap pakai: dist\UnchartedPCInstaller.exe
echo Semua DLL runtime (Tk/Tcl) sudah terbundel di dalam exe.
echo Bila exe tidak mau jalan, pasang Microsoft Visual C++ Redistributable.
