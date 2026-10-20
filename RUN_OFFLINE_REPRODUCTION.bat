@echo off
setlocal
cd /d "%~dp0"
echo Poole V207 two-generation v2.4 -- OFFLINE public reproduction
python reproduce.py
if errorlevel 1 goto :failed
python scripts\verify_reconstructed_circuits.py
if errorlevel 1 goto :failed
python -m unittest discover -s tests -v
if errorlevel 1 goto :failed
echo.
echo PASS: original counts, reconstructed circuits and release tests.
pause
exit /b 0
:failed
echo.
echo FAILED: a check above returned an error. No IBM submission was attempted.
pause
exit /b 1
