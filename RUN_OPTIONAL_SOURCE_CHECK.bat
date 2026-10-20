@echo off
setlocal
cd /d "%~dp0"
python source\validate_source.py
if errorlevel 1 (
 echo Source check failed. Optional dependencies: python -m pip install numpy scipy
 pause
 exit /b 1
)
echo PASS: source-side V207 full-lattice checks.
pause
