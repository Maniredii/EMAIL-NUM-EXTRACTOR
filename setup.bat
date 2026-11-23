@echo off
setlocal enabledelayedexpansion
title Resume Email & Phone Extractor - Setup
cd /d "%~dp0"

echo =====================================================================
echo         RESUME EMAIL & PHONE EXTRACTOR - ONE-TIME SETUP
echo =====================================================================
echo.

:: 1. Check Python installation
echo [1/3] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] Python is not installed on this machine.
    echo [INFO] Automatically downloading and installing Python 3.11...
    echo Please wait 1-2 minutes...
    
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; " ^
        "$dest = Join-Path $env:TEMP 'python_installer.exe'; " ^
        "(New-Object System.Net.WebClient).DownloadFile($url, $dest); " ^
        "$proc = Start-Process -FilePath $dest -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1' -Wait -PassThru; " ^
        "Remove-Item $dest -Force -ErrorAction SilentlyContinue"

    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'User')"') do set "USERPATH=%%a"
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine')"') do set "SYSPATH=%%a"
    set "PATH=!USERPATH!;!SYSPATH!;!PATH!"
)

python --version
echo [OK] Python is available.
echo.

:: 2. Create Virtual Environment
echo [2/3] Setting up virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Existing virtual environment found.
)
echo.

:: 3. Install Dependencies
echo [3/3] Installing dependencies from requirements.txt...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to install dependencies! Please check internet connection.
    pause
    exit /b 1
)
echo [OK] All dependencies successfully installed.
echo.
echo =====================================================================
echo  SETUP COMPLETE! You can now launch the app anytime via Launch_App.bat
echo =====================================================================
pause
