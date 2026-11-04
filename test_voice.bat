@echo off
REM Tests both voice profiles: validation, offline generation with network blocked, and the test suite.
REM   test_voice.bat          quick run
REM   test_voice.bat --long   also narrates a ~5 minute script
setlocal
set "OV_HOME=%~dp0"
set "VPY=%OV_HOME%.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo ERROR: run "%OV_HOME%setup.bat" first. 1>&2
  exit /b 3
)
set "FAILED=0"
echo === Validate voice profiles ===
"%VPY%" "%OV_HOME%scripts\validate_voice.py" || set "FAILED=1"
echo.
echo === Offline generation (network blocked) ===
"%VPY%" "%OV_HOME%scripts\test_offline.py" %* || set "FAILED=1"
echo.
echo === Test suite ===
"%VPY%" -m pytest "%OV_HOME%tests" -q || set "FAILED=1"
echo.
if "%FAILED%"=="1" ( echo SOME TESTS FAILED & exit /b 1 )
echo ALL TESTS PASSED
exit /b 0
