@echo off
REM DerivativeMill Windows 11 Installer Build Script
REM This script builds the standalone executable and creates an installation package

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo DerivativeMill Windows 11 Installation Package Builder
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing build dependencies...
pip install -q PyInstaller wheel

echo.
echo [4/5] Building executable (this may take 2-5 minutes)...
echo.

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Run PyInstaller
pyinstaller --onefile ^
  --windowed ^
  --name DerivativeMill ^
  --icon=DerivativeMill\Resources\derivativemill.ico ^
  --add-data "DerivativeMill\Resources;DerivativeMill\Resources" ^
  --add-data "README.md;." ^
  --add-data "QUICKSTART.md;." ^
  --hidden-import=PyQt5 ^
  --hidden-import=pandas ^
  --hidden-import=openpyxl ^
  --hidden-import=pdfplumber ^
  --hidden-import=PIL ^
  DerivativeMill\derivativemill.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [5/5] Creating installer package...
echo.

REM Create distribution directory structure
if not exist "dist\DerivativeMill" mkdir "dist\DerivativeMill"

REM Copy executable
copy /Y "dist\DerivativeMill.exe" "dist\DerivativeMill\"

REM Copy documentation
copy /Y "README.md" "dist\DerivativeMill\"
copy /Y "QUICKSTART.md" "dist\DerivativeMill\"
copy /Y "SETUP.md" "dist\DerivativeMill\"

REM Create installation directories in the package
mkdir "dist\DerivativeMill\Input"
mkdir "dist\DerivativeMill\Output"
mkdir "dist\DerivativeMill\ProcessedPDFs"

REM Create a batch file launcher for convenience
(
  echo @echo off
  echo setlocal
  echo cd /d "%%~dp0"
  echo start "" "DerivativeMill.exe"
  echo endlocal
) > "dist\DerivativeMill\Run_DerivativeMill.bat"

REM Create a setup/installation batch file
(
  echo @echo off
  echo setlocal
  echo title DerivativeMill Setup
  echo color 0A
  echo cls
  echo.
  echo ============================================================
  echo DerivativeMill Installation
  echo ============================================================
  echo.
  echo This will create shortcuts and set up the application.
  echo.
  echo Press any key to continue...
  echo pause ^>nul
  echo.
  echo Creating desktop shortcut...
  echo.

  echo REM Create shortcut using VBScript
  echo powershell -Command ^
  echo   "$WshShell = New-Object -ComObject WScript.Shell; " ^
  echo   "$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\DerivativeMill.lnk'); " ^
  echo   "$Shortcut.TargetPath = '%~dp0DerivativeMill.exe'; " ^
  echo   "$Shortcut.WorkingDirectory = '%~dp0'; " ^
  echo   "$Shortcut.Save()"
  echo.

  echo if errorlevel 1 (
  echo   echo Failed to create desktop shortcut
  echo   echo You can manually create one by right-clicking DerivativeMill.exe
  echo ) else (
  echo   echo Successfully created desktop shortcut!
  echo )
  echo.
  echo echo Installation complete. You can now run DerivativeMill.exe
  echo pause
  echo endlocal
) > "dist\DerivativeMill\INSTALL.bat"

REM Create a portable ZIP package
echo Creating portable ZIP package...
cd dist
powershell -Command "Compress-Archive -Path DerivativeMill -DestinationPath DerivativeMill_Windows11_Portable.zip -Force"
cd ..

echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Output files:
echo   - dist\DerivativeMill\DerivativeMill.exe       (Standalone executable)
echo   - dist\DerivativeMill_Windows11_Portable.zip   (Portable ZIP package)
echo.
echo Installation Options:
echo   1. Copy the dist\DerivativeMill folder to Program Files
echo   2. Run INSTALL.bat to create desktop shortcut
echo   3. Or simply copy the ZIP file to a USB drive (fully portable)
echo.
echo Documentation:
echo   - README.md        - Project overview
echo   - QUICKSTART.md    - Quick start guide
echo   - SETUP.md         - Detailed Windows setup
echo.
echo ============================================================
echo.
pause
