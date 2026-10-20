@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo Poole V207 v1.1 - IBM hardware setup
 echo ============================================
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-hardware.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import qiskit, qiskit_ibm_runtime; print('IBM hardware dependencies installed. Qiskit:',qiskit.__version__)"
if errorlevel 1 goto failed
echo.
echo SETUP PASSED. Run RUN_ON_IBM.bat to use your own IBM account.
pause
exit /b 0
:failed
echo.
echo Setup FAILED. No IBM hardware job was submitted.
echo Check Python 3.10+ installation, internet connection and pip error above.
pause
exit /b 1
