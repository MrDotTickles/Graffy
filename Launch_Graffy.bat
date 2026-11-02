@echo off
cd /d "%~dp0"
title Graffy - Intuitive Scientific Graphing
echo Starting Graffy...
if not exist ".venv\Scripts\python.exe" (
    call "%~dp0Setup_Graffy.bat"
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
