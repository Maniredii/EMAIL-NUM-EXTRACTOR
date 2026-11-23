@echo off
title Stop Resume Extractor
echo Stopping Resume Extractor background processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Resume Extractor*" >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
echo Done! App stopped.
timeout /t 2 >nul
