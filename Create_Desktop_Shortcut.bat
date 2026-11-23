@echo off
setlocal
cd /d "%~dp0"

echo =====================================================================
echo         CREATING DESKTOP SHORTCUT FOR RESUME EXTRACTOR
echo =====================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$shortcutPath = Join-Path $desktop 'Resume Extractor.lnk'; " ^
    "$s = $ws.CreateShortcut($shortcutPath); " ^
    "$s.TargetPath = 'wscript.exe'; " ^
    "$s.Arguments = '\"%~dp0Launch_Silently.vbs\"'; " ^
    "$s.WorkingDirectory = '%~dp0'; " ^
    "$s.Description = 'Extract emails and phone numbers from resume PDFs'; " ^
    "$s.IconLocation = 'shell32.dll,23'; " ^
    "$s.Save(); " ^
    "Write-Host '[SUCCESS] Shortcut created at: ' $shortcutPath"

echo.
echo You can now launch the app anytime directly from your Desktop icon:
echo    "Resume Extractor"
echo.
pause
