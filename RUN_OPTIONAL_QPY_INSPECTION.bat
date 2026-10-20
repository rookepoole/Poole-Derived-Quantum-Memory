@echo off
setlocal
cd /d "%~dp0"
python scripts\verify_qpy_optional.py
if errorlevel 1 (
 echo QPY inspection requires Qiskit installed locally. No IBM account is required.
 pause
 exit /b 1
)
echo PASS: original submitted IBM QPY structure inspected.
pause
