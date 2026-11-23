@echo off
setlocal enabledelayedexpansion
title Resume Email & Phone Extractor - Launcher
cd /d "%~dp0"

echo =====================================================================
echo         STARTING RESUME EMAIL & PHONE EXTRACTOR
echo =====================================================================
echo.

:: 1. Check if Python is installed on this machine
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] Python is not installed on this computer.
    echo [INFO] Automatically downloading and installing Python for you...
    echo This is a one-time setup and takes about 1-2 minutes.
    echo Please wait, do NOT close this window...
    echo.

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Write-Host 'Downloading official Python installer...' -ForegroundColor Cyan; " ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; " ^
        "$dest = Join-Path $env:TEMP 'python_installer.exe'; " ^
        "(New-Object System.Net.WebClient).DownloadFile($url, $dest); " ^
        "Write-Host 'Installing Python quietly (no admin required)...' -ForegroundColor Cyan; " ^
        "$proc = Start-Process -FilePath $dest -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1' -Wait -PassThru; " ^
        "Remove-Item $dest -Force -ErrorAction SilentlyContinue; " ^
        "if ($proc.ExitCode -eq 0) { Write-Host 'Python installed successfully!' -ForegroundColor Green } else { Write-Host 'Installation error code: ' $proc.ExitCode -ForegroundColor Yellow }"

    :: Refresh PATH for the current command prompt
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'User')"') do set "USERPATH=%%a"
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine')"') do set "SYSPATH=%%a"
    set "PATH=!USERPATH!;!SYSPATH!;!PATH!"

    where python >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo.
        echo [ERROR] Automatic Python installation could not complete.
        echo Please download and install Python from: https://www.python.org/downloads/
        echo Make sure to check 'Add python.exe to PATH' during installation.
        pause
        exit /b 1
    )
)

:: 2. Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [INFO] Setting up virtual environment and required libraries...
    echo This is a one-time setup. Please wait a moment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
    echo [OK] Setup complete!
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo =====================================================================
echo  Starting application... Opening in your default browser!
echo =====================================================================
echo.

:: Launch Streamlit
python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

if %ERRORLEVEL% neq 0 (
    echo.
    echo [NOTE] App has closed.
    pause
)
