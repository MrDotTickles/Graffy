#!/bin/bash
# ==============================================================================
# Build Standalone macOS Application Bundle (Graffy.app)
# ==============================================================================
set -e

cd "$(dirname "$0")/.." || exit 1

echo "======================================================================"
echo " Packaging Graffy into a standalone macOS .app bundle"
echo "======================================================================"

PYTHON_BIN=""
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3 not found. Please install Python 3.10+."
    exit 1
fi

# Ensure dependencies & PyInstaller are installed
echo "Checking build prerequisites..."
"$PYTHON_BIN" -m pip install -r requirements-build.txt

# Ensure graffy.icns is up to date
# Icons are checked into source; no GUI is needed during builds.

echo "Running PyInstaller build..."
"$PYTHON_BIN" scripts/build_app.py
"$PYTHON_BIN" scripts/package_macos.py

echo "======================================================================"
echo " Build successful!"
echo " Standalone bundle located at: dist/Graffy.app"
echo " To test: open dist/Graffy.app"
echo "======================================================================"
