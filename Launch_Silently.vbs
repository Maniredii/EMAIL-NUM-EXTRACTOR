Set WshShell = CreateObject("WScript.Shell")
strPath = WshShell.CurrentDirectory
WshShell.Run """" & strPath & "\Launch_App.bat""", 0, False
Set WshShell = Nothing
