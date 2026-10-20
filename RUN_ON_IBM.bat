@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Hardware environment not installed. Run SETUP_IBM_WINDOWS.bat once.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m hardware.ibm_runner menu
if errorlevel 1 (
  echo Menu closed with an error. No automatic resubmission was attempted.
)
pause
