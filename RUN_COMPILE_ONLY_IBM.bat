@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto nosetup
".venv\Scripts\python.exe" -m hardware.ibm_runner compile
if errorlevel 1 echo Preflight failed. NO IBM job submitted.
pause
exit /b 0
:nosetup
echo Please run SETUP_IBM_WINDOWS.bat first.
pause
exit /b 1
