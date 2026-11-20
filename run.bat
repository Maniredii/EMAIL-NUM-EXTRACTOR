@echo off
title Resume Email Extractor
echo =====================================================================
echo         LAUNCHING LOCAL BULK RESUME EMAIL EXTRACTOR
echo =====================================================================
echo.

:: Check if .venv exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [NOTE] Virtual environment (.venv) not found. Using system Python...
)

echo Starting Streamlit application...
echo Opening in your browser shortly...
echo.

python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] The application stopped unexpectedly.
    echo Please make sure you have run setup.bat first.
    pause
)
