@echo off
REM ===== PyDoc (Windows) =====
cd /d "%~dp0"

REM First run? Install dependencies (pywebview required, others optional).
python -c "import webview" 2>nul
if errorlevel 1 (
  echo Installing dependencies (one-time)...
  python -m pip install -r requirements.txt
)

REM Launch with pythonw so no console window stays open.
start "" pythonw launcher.py
exit
