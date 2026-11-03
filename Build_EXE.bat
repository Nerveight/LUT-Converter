@echo off
title Building LUT Converter.exe
cd /d "%~dp0"

echo [1/3] Installing build tools and dependencies...
python -m pip install --upgrade pyinstaller pyside6 pillow numpy
if errorlevel 1 goto :fail

echo.
echo [2/3] Building the .exe (this takes a few minutes)...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "LUT Converter" ^
    --icon "lut_icon.ico" ^
    --add-data "lut_icon.ico;." ^
    --exclude-module tkinter ^
    --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets ^
    --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtQml ^
    --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.QtCharts ^
    --exclude-module PySide6.QtDataVisualization ^
    --exclude-module PySide6.QtPdf ^
    lut_converter.py
if errorlevel 1 goto :fail

echo.
echo [3/3] Cleaning up...
rmdir /s /q build 2>nul
del /q "LUT Converter.spec" 2>nul

echo.
echo Done! Your app is here:
echo    %~dp0dist\LUT Converter.exe
explorer "%~dp0dist"
pause
exit /b 0

:fail
echo.
echo Something went wrong - scroll up to see the error.
pause
exit /b 1
