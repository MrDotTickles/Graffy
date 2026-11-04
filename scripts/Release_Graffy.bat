@echo off
setlocal
cd /d "%~dp0.."
echo Graffy release helper - commit your code changes before continuing.
set /p "GRAFFY_VERSION=New version (example 1.0.1): "
if not defined GRAFFY_VERSION exit /b 1
if not exist ".venv\Scripts\python.exe" (
    call "%~dp0Setup_Graffy.bat"
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" scripts\release.py "%GRAFFY_VERSION%"
if errorlevel 1 echo Release stopped. Read the error above.
pause
