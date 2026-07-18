@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 尚未建立執行環境，現在開始安裝...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
    if errorlevel 1 (
        echo.
        echo 安裝失敗。
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" "app.py"
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo 程式發生錯誤，錯誤碼：%APP_EXIT%
    pause
)
exit /b %APP_EXIT%
