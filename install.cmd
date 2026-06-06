@echo off
setlocal EnableExtensions
title PyDoc Installer

REM ===========================================================================
REM  PyDoc · install
REM  - installs Python dependencies (pywebview + optional extras)
REM  - registers PyDoc to start automatically on Windows login
REM    (HKCU\...\Run  -> the same entry the in-app "Auto-start" toggle uses)
REM  - creates a Start Menu shortcut
REM ===========================================================================

cd /d "%~dp0"
set "APPDIR=%~dp0"
set "APPDIR=%APPDIR:~0,-1%"

echo.
echo  PyDoc installer
echo  =======================
echo.

REM --- locate pythonw (no console) / python ---------------------------------
set "PYW=pythonw"
where pythonw >nul 2>nul || set "PYW=python"
where python  >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH. Install Python 3.8+ first.
  pause & exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install -r "%APPDIR%\requirements.txt"
echo.

echo [2/3] Registering auto-start on login...
set "RUNCMD=\"%PYW%\" \"%APPDIR%\launcher.py\""
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v PyDoc /t REG_SZ /d "%RUNCMD%" /f >nul
if errorlevel 1 (echo     [WARN] could not write Run key.) else (echo     OK: starts at login.)
echo.

echo [3/3] Creating Start Menu shortcut...
set "SMDIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "LNK=%SMDIR%\PyDoc.lnk"
set "PS=$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%');$s.TargetPath='%PYW%';$s.Arguments='\"%APPDIR%\launcher.py\"';$s.WorkingDirectory='%APPDIR%';$s.IconLocation='%APPDIR%\Icons\app.ico';$s.Save()"
powershell -NoProfile -ExecutionPolicy Bypass -Command "%PS%" >nul 2>nul
if exist "%LNK%" (echo     OK: Start Menu shortcut created.) else (echo     [WARN] shortcut not created.)
echo.

echo  Done. Launch it now from the Start Menu, or it will start at next login.
echo  Default hotkeys:  Alt+Space = open,  Ctrl+Win+N = add shortcut.
echo.
choice /c YN /m "Start PyDoc now"
if errorlevel 2 goto :end
start "" %PYW% "%APPDIR%\launcher.py"

:end
echo.
pause
endlocal
