@echo off
cd /d "%~dp0"
python -c "import PySide6, PIL, numpy" 2>nul || (
    echo Installing required packages...
    python -m pip install pyside6 pillow numpy
)
start "" pythonw lut_converter.py %*
