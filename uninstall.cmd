@echo off
setlocal EnableExtensions
title PyDoc Uninstaller

REM ===========================================================================
REM  PyDoc · uninstall
REM  - stops any running instance
REM  - removes the auto-start (HKCU\...\Run) entry  [the "Ctrl+Win+N" app entry]
REM  - removes the Start Menu shortcut
REM  Your shortcuts, themes and settings files are left intact.
REM ===========================================================================

cd /d "%~dp0"
set "APPDIR=%~dp0"
set "APPDIR=%APPDIR:~0,-1%"

echo.
echo  PyDoc uninstaller
echo  =========================
echo.

echo [1/3] Stopping running instance(s)...
REM kill any pythonw/python process running launcher.py (best-effort)
for /f "tokens=2 delims=," %%P in (
  'wmic process where "name='pythonw.exe' or name='python.exe'" get ProcessId^,CommandLine /format:csv 2^>nul ^| findstr /i "launcher.py"'
) do (
  taskkill /pid %%P /f >nul 2>nul
)
echo     OK.
echo.

echo [2/3] Removing auto-start entry...
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v PyDoc >nul 2>nul
if not errorlevel 1 (
  reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v PyDoc /f >nul
  echo     OK: removed from login startup.
) else (
  echo     (no auto-start entry found)
)
echo.

echo [3/3] Removing Start Menu shortcut...
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\PyDoc.lnk"
if exist "%LNK%" ( del /f /q "%LNK%" & echo     OK: shortcut removed. ) else ( echo     (no shortcut found) )
echo.

echo  PyDoc has been unregistered.
echo  Settings/shortcuts kept in: %APPDIR%
echo  (Delete that folder manually to remove everything.)
echo.
pause
endlocal
