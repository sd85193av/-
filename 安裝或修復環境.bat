@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "SETUP_EXIT=%ERRORLEVEL%"
if not "%SETUP_EXIT%"=="0" (
    echo.
    echo Setup failed with exit code %SETUP_EXIT%.
)
pause
exit /b %SETUP_EXIT%
