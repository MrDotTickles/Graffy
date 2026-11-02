@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo ======================================================================
echo  Packaging Graffy for Windows (Standalone Portable Distribution)
echo ======================================================================
echo.

:: 1. Check Python
if not exist ".venv\Scripts\python.exe" (
    call "%~dp0..\Setup_Graffy.bat"
    if errorlevel 1 exit /b 1
)
set "GRAFFY_PYTHON=.venv\Scripts\python.exe"
"%GRAFFY_PYTHON%" --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Ensure PyInstaller and dependencies
echo [1/4] Checking build dependencies...
"%GRAFFY_PYTHON%" -m pip install -r requirements-build.txt --quiet
if errorlevel 1 exit /b 1

:: 3. Generate icon files
echo [2/4] Ensuring application icons are up to date...
:: Icons are checked into source; no GUI is needed to regenerate them during build.

:: 4. Run PyInstaller
echo [3/4] Compiling standalone Windows executable with PyInstaller...
"%GRAFFY_PYTHON%" scripts\build_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Compilation failed.
    pause
    exit /b %ERRORLEVEL%
)

:: 5. Create Distribution ZIP
echo [4/4] Creating distribution ZIP package...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop'; Compress-Archive -Path 'dist\Graffy\*' -DestinationPath 'dist\Graffy_Windows.zip' -Force; " ^
    "Write-Host 'ZIP package created at dist\Graffy_Windows.zip' -ForegroundColor Green"
if errorlevel 1 exit /b 1

echo.
echo ======================================================================
echo  Build Complete!
echo  
echo  1. Portable Folder:  dist\Graffy\Graffy.exe
echo  2. Distribution ZIP: dist\Graffy_Windows.zip
echo  
echo  For GitHub installer releases, use Release_Graffy.bat. See RELEASING.md.
echo ======================================================================
echo.
pause
