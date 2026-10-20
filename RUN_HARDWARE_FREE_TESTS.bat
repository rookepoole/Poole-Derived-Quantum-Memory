@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto venv
where py >nul 2>nul
if errorlevel 1 goto basic
py -3 -m unittest discover -s tests -v
if errorlevel 1 goto failed
py -3 scripts\verify_reconstructed_circuits.py
if errorlevel 1 goto failed
goto passed
:basic
python -m unittest discover -s tests -v
if errorlevel 1 goto failed
python scripts\verify_reconstructed_circuits.py
if errorlevel 1 goto failed
goto passed
:venv
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\verify_reconstructed_circuits.py
if errorlevel 1 goto failed
:passed
echo.
echo Offline release checks PASSED; no IBM key or hardware time needed.
pause
exit /b 0
:failed
echo.
echo Offline checks FAILED. No IBM job submitted.
pause
exit /b 1
