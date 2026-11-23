@echo off
title Build Standalone ResumeExtractor.exe
cd /d "%~dp0"

echo =====================================================================
echo       BUILDING STANDALONE SINGLE-FILE RESUME EXTRACTOR (.EXE)
echo =====================================================================
echo.

call .venv\Scripts\activate.bat 2>nul

echo Compiling into dist\ResumeExtractor.exe...
pyinstaller --noconfirm --onefile --windowed --name "ResumeExtractor" ^
    --add-data "core;core" ^
    --exclude-module PyQt5 --exclude-module PyQt6 ^
    --exclude-module PySide2 --exclude-module PySide6 ^
    --exclude-module matplotlib --exclude-module scipy ^
    --exclude-module IPython gui_app.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================================
    echo [SUCCESS] Your standalone executable is ready at:
    echo           dist\ResumeExtractor.exe
    echo =====================================================================
) else (
    echo.
    echo [ERROR] Build failed.
)
pause
