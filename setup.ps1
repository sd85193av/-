$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ModelDirectory = Join-Path $ProjectRoot "models"
$ModelPath = Join-Path $ModelDirectory "hand_landmarker.task"
$ModelUrl = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $PythonCandidates = @(
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    )
    $Python = $PythonCandidates |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
    if (-not $Python) {
        throw "找不到 Python 3.11 或 3.12。請先安裝 64 位元 Python。"
    }
    Write-Host "建立專案環境：$VenvPython"
    & $Python -m venv (Join-Path $ProjectRoot ".venv")
}

Write-Host "安裝／修復相依套件..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

if (-not (Test-Path -LiteralPath $ModelPath)) {
    New-Item -ItemType Directory -Force -Path $ModelDirectory | Out-Null
    Write-Host "下載 MediaPipe 手部辨識模型..."
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelPath
}

Write-Host ""
Write-Host "安裝完成。"
