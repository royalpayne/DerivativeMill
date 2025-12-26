@echo off
REM TariffMill Build Script for Windows
REM This script builds the application using PyInstaller and creates an installer with Inno Setup

echo ========================================
echo TariffMill Build Script
echo ========================================
echo.

REM Check Python
echo [1/4] Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

REM Install/upgrade dependencies
echo.
echo [2/4] Installing dependencies...
pip install -r Tariffmill\requirements.txt --quiet
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)

REM Build with PyInstaller
echo.
echo [3/4] Building with PyInstaller...
pyinstaller --clean --noconfirm tariffmill.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

REM Check if Inno Setup is available
echo.
echo [4/4] Creating installer with Inno Setup...
where iscc >nul 2>&1
if errorlevel 1 (
    echo WARNING: Inno Setup Compiler (iscc) not found in PATH
    echo You can install it from: https://jrsoftware.org/isinfo.php
    echo.
    echo Build completed without installer.
    echo Standalone application is in: dist\TariffMill\
    goto :done
)

REM Create installer
if not exist installer_output mkdir installer_output
iscc tariffmill_setup.iss
if errorlevel 1 (
    echo ERROR: Inno Setup build failed
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Standalone application: dist\TariffMill\TariffMill.exe
echo Installer: installer_output\TariffMill_Setup_*.exe
echo.

:done
pause
