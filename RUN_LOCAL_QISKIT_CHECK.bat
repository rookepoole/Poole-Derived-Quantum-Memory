@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Qiskit environment missing. Run SETUP_IBM_WINDOWS.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\check_reconstructed_qiskit.py
if errorlevel 1 (
  echo FAILED. No IBM job submitted.
) else (
  echo SUCCESS. No IBM job submitted.
)
pause
