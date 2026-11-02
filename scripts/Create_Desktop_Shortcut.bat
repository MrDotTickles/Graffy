@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create_Desktop_Shortcut.ps1"
if errorlevel 1 echo Could not create the shortcut. Read the error above.
pause
