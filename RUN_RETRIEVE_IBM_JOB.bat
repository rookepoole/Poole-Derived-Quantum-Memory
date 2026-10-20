@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto nosetup
set /p RUNDIR=Paste the full compiled run folder path: 
if "%RUNDIR%"=="" goto nofolder
".venv\Scripts\python.exe" -m hardware.ibm_runner retrieve --run-dir "%RUNDIR%"
if errorlevel 1 echo Retrieval failed or job is not yet completed. Existing IBM job was not resubmitted.
pause
exit /b 0
:nosetup
echo Please run SETUP_IBM_WINDOWS.bat first.
pause
exit /b 1
:nofolder
echo No run folder given. Nothing retrieved.
pause
exit /b 1
