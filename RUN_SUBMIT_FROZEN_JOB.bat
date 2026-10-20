@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto nosetup
echo.
echo This is the ONLY step that can consume IBM QPU allocation.
echo Compile-only must have produced a private_runs\v24_... folder.
set /p RUNDIR=Paste the full compiled run folder path: 
if "%RUNDIR%"=="" goto nofolder
".venv\Scripts\python.exe" -m hardware.ibm_runner submit --run-dir "%RUNDIR%"
if errorlevel 1 echo Submission canceled or failed; check IBM account before any retry.
pause
exit /b 0
:nosetup
echo Please run SETUP_IBM_WINDOWS.bat first.
pause
exit /b 1
:nofolder
echo No run folder given. Nothing submitted.
pause
exit /b 1
