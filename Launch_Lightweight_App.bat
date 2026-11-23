@echo off
setlocal enabledelayedexpansion
title Resume Extractor (Lightweight Edition)
cd /d "%~dp0"

echo =====================================================================
echo    RESUME EMAIL & PHONE EXTRACTOR (LIGHTWEIGHT EDITION)
echo    * Optimized for older laptops and low-spec PCs (< 30 MB RAM)
echo =====================================================================
echo.

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] Python is not installed on this machine.
    echo [INFO] Automatically downloading Python 3.11...
    echo Please wait 1-2 minutes...
    
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; " ^
        "$dest = Join-Path $env:TEMP 'python_installer.exe'; " ^
        "(New-Object System.Net.WebClient).DownloadFile($url, $dest); " ^
        "Start-Process -FilePath $dest -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1' -Wait; " ^
        "Remove-Item $dest -Force -ErrorAction SilentlyContinue"

    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'User')"') do set "USERPATH=%%a"
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine')"') do set "SYSPATH=%%a"
    set "PATH=!USERPATH!;!SYSPATH!;!PATH!"
)

:: 2. Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] First-time setup: installing dependencies...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Launching native desktop window...
python gui_app.py

if %ERRORLEVEL% neq 0 (
    pause
)
