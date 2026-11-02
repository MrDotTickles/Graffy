@echo off
setlocal
cd /d "%~dp0"
echo Setting up Graffy's local development environment.
echo This downloads the Python libraries used to run, test, and build Graffy.
echo The .venv folder will take several hundred megabytes and stays out of Git.
if exist ".venv\Scripts\python.exe" goto install
set "GRAFFY_BASE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%GRAFFY_BASE_PYTHON%" goto local_python
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo Install Python 3.13 from python.org, then run this button again.
    goto failed
)
py -3.13 -m venv .venv
if errorlevel 1 goto failed
goto install
:local_python
"%GRAFFY_BASE_PYTHON%" -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
echo Setup complete.
exit /b 0
:failed
echo Setup stopped. Read the error above.
pause
exit /b 1
