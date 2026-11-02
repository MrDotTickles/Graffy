#!/bin/bash
# ==============================================================================
# Graffy - macOS Launcher (Double-clickable in Finder)
# ==============================================================================

# Change to the directory where this script is located
cd "$(dirname "$0")" || exit 1

echo "======================================================================"
echo " Starting Graffy - Scientific Graphing & Data Analysis"
echo "======================================================================"

# Determine Python 3 executable (check virtual environment, python3, or python)
PYTHON_BIN=""
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3 could not be found."
    echo "Please install Python 3.10+ from https://www.python.org or via Homebrew ('brew install python@3.11')."
    echo ""
    read -n 1 -s -r -p "Press any key to exit..."
    exit 1
fi

# Check for required packages (PyQt6, matplotlib, numpy, scipy, pandas)
"$PYTHON_BIN" -c "import PyQt6, matplotlib, numpy, scipy, pandas, openpyxl, PIL" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Notice: Installing required dependencies from requirements.txt..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies automatically."
        echo "Please run: pip install -r requirements.txt"
        echo ""
        read -n 1 -s -r -p "Press any key to exit..."
        exit 1
    fi
fi

# Launch Graffy with forwarded arguments
"$PYTHON_BIN" main.py "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Graffy exited with status code $EXIT_CODE."
    read -n 1 -s -r -p "Press any key to close this terminal window..."
fi

exit $EXIT_CODE
