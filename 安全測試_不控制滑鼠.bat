@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "APP_FILE=%~dp0app.py"

if not exist "%PYTHON_EXE%" (
    echo Runtime not found. Starting setup...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
    if errorlevel 1 (
        echo.
        echo Setup failed.
        pause
        exit /b 1
    )
)

if not exist "%APP_FILE%" (
    echo Application file not found: "%APP_FILE%"
    pause
    exit /b 2
)

"%PYTHON_EXE%" "%APP_FILE%" --no-control %*
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo Application failed with exit code %APP_EXIT%.
    pause
)
exit /b %APP_EXIT%
