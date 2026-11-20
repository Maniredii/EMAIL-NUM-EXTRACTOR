@echo off
setlocal enabledelayedexpansion

title Resume Email Extractor - Setup
echo =====================================================================
echo           LOCAL BULK RESUME EMAIL EXTRACTOR - SETUP
echo =====================================================================
echo.

:: 1. Check Python installation
echo [1/4] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.10 or 3.11 from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python --version
echo [OK] Python is installed.
echo.

:: 2. Create Virtual Environment
echo [2/4] Setting up Python virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Existing virtual environment found.
)
echo.

:: 3. Install Dependencies
echo [3/4] Installing required packages...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies! Please check your internet connection.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.
echo.

:: 4. Check OCR Status
echo [4/4] Checking optional Tesseract OCR status...
where tesseract >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] Tesseract OCR command detected in PATH.
) else (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo [OK] Tesseract OCR found in standard path: C:\Program Files\Tesseract-OCR\tesseract.exe
    ) else (
        echo [NOTE] Tesseract OCR is not installed. Standard PDF text extraction works 100%%.
        echo        If you need to OCR image-only scanned PDFs, install Tesseract from:
        echo        https://github.com/UB-Mannheim/tesseract/wiki
    )
)

echo.
echo =====================================================================
echo                       SETUP COMPLETED!
echo =====================================================================
echo You can now double-click "run.bat" to launch the application.
echo.
pause
