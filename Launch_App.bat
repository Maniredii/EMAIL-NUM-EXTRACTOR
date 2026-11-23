@echo off
setlocal enabledelayedexpansion
title Resume Extractor - Desktop Launcher
cd /d "%~dp0"

echo =====================================================================
echo         STARTING RESUME EMAIL & PHONE EXTRACTOR
echo =====================================================================
echo.

:: 1. Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] First time setup detected! Installing dependencies...
    echo This only happens once. Please wait 1-2 minutes...
    echo.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Installation failed. Please ensure Python is installed and connected to internet.
        pause
        exit /b 1
    )
    echo [OK] Setup complete!
) else (
    call .venv\Scripts\activate.bat
)

echo Starting application and opening browser...
echo.

:: Launch Streamlit in browser
python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

if %ERRORLEVEL% neq 0 (
    echo.
    echo [NOTE] App has closed.
    pause
)
