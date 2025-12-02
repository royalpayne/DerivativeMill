# DerivativeMill Windows 11 Installer Build Script (PowerShell)
# This script builds the standalone executable and creates an installation package
# Run with: powershell -ExecutionPolicy Bypass -File build_windows_installer.ps1

param(
    [switch]$SkipBuild = $false,
    [switch]$SkipCleanup = $false
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Console colors
function Write-Header {
    param([string]$Text)
    Write-Host "`n" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host $Text -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
}

function Write-Step {
    param([string]$Text, [int]$Step, [int]$Total)
    Write-Host "[$Step/$Total] $Text" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "✗ ERROR: $Text" -ForegroundColor Red
}

# Main execution
try {
    Write-Header "DerivativeMill Windows 11 Installation Package Builder"

    # Step 1: Check Python
    Write-Step "Checking Python installation" 1 5
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Python is not installed or not in PATH"
        Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Success "Python found: $pythonVersion"

    # Step 2: Check virtual environment
    Write-Step "Checking virtual environment" 2 5
    if (-not (Test-Path "venv\Scripts\activate.ps1")) {
        Write-Error-Custom "Virtual environment not found at venv\Scripts\activate.ps1"
        Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
        exit 1
    }
    Write-Success "Virtual environment found"

    # Step 3: Activate virtual environment and install dependencies
    Write-Step "Activating virtual environment and installing dependencies" 3 5
    & "venv\Scripts\activate.ps1"

    pip install -q PyInstaller wheel 2>&1 | Out-Null
    Write-Success "Build dependencies installed"

    # Step 4: Build executable
    if (-not $SkipBuild) {
        Write-Step "Building executable (this may take 2-5 minutes)" 4 5

        # Clean previous builds
        if (Test-Path "build") {
            Remove-Item -Path "build" -Recurse -Force | Out-Null
        }
        if (Test-Path "dist") {
            Remove-Item -Path "dist" -Recurse -Force | Out-Null
        }

        # Run PyInstaller
        Write-Host "`nRunning PyInstaller...`n"

        $icoPath = "DerivativeMill\Resources\derivativemill.ico"
        $icoOption = if (Test-Path $icoPath) { "--icon=$icoPath" } else { "" }

        & pyinstaller --onefile `
            --windowed `
            --name DerivativeMill `
            $icoOption `
            --add-data "DerivativeMill\Resources;DerivativeMill\Resources" `
            --add-data "README.md;." `
            --add-data "QUICKSTART.md;." `
            --hidden-import=PyQt5 `
            --hidden-import=pandas `
            --hidden-import=openpyxl `
            --hidden-import=pdfplumber `
            --hidden-import=PIL `
            DerivativeMill\derivativemill.py

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "PyInstaller build failed"
            exit 1
        }
        Write-Success "Executable built successfully"
    }

    # Step 5: Create installer package
    Write-Step "Creating installer package" 5 5

    # Create distribution directory structure
    $distDir = "dist\DerivativeMill"
    if (-not (Test-Path $distDir)) {
        New-Item -ItemType Directory -Path $distDir -Force | Out-Null
    }

    # Copy executable
    Copy-Item -Path "dist\DerivativeMill.exe" -Destination "$distDir\" -Force

    # Copy documentation
    Copy-Item -Path "README.md" -Destination "$distDir\" -Force
    Copy-Item -Path "QUICKSTART.md" -Destination "$distDir\" -Force
    Copy-Item -Path "SETUP.md" -Destination "$distDir\" -Force

    # Note: Data directories (Input, Output, ProcessedPDFs) are created automatically by the application on first run
    Write-Success "Data directories will be created automatically on first run"

    # Create batch file launcher - simplified to avoid parsing issues
    $batContent = @'
@echo off
setlocal
cd /d "%~dp0"
start "" "DerivativeMill.exe"
endlocal
'@
    Set-Content -Path "$distDir\Run_DerivativeMill.bat" -Value $batContent -Encoding ASCII

    # Create INSTALL.bat - simplified version
    $installContent = @'
@echo off
setlocal
title DerivativeMill Setup
color 0A
cls

echo.
echo ============================================================
echo DerivativeMill Installation
echo ============================================================
echo.
echo This will create shortcuts and set up the application.
echo.
echo Press any key to continue...
pause >nul

echo.
echo Creating desktop shortcut...
echo.

REM Create desktop shortcut using VBScript approach
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $desktop = [Environment]::GetFolderPath('Desktop'); $WshShell = New-Object -ComObject WScript.Shell; $shortcut = $WshShell.CreateShortcut($desktop + '\DerivativeMill.lnk'); $shortcut.TargetPath = (Get-Location).Path + '\DerivativeMill.exe'; $shortcut.WorkingDirectory = (Get-Location).Path; $shortcut.Save()"

if %errorlevel% equ 0 (
    echo.
    echo Successfully created desktop shortcut!
) else (
    echo.
    echo Note: Could not create desktop shortcut automatically.
    echo You can manually create one by right-clicking DerivativeMill.exe
)

echo.
echo Installation complete. You can now run DerivativeMill.exe
echo.
pause
endlocal
'@
    Set-Content -Path "$distDir\INSTALL.bat" -Value $installContent -Encoding ASCII

    # Create portable ZIP package
    Write-Host "`nCreating portable ZIP package..." -ForegroundColor Cyan
    $zipPath = "dist\DerivativeMill_Windows11_Portable.zip"

    if (Test-Path $zipPath) {
        Remove-Item -Path $zipPath -Force
    }

    Compress-Archive -Path $distDir -DestinationPath $zipPath -Force

    Write-Success "Portable ZIP package created"

    # Summary
    Write-Header "BUILD COMPLETE!"

    Write-Host "Output files:" -ForegroundColor Green
    Write-Host "  - $distDir\DerivativeMill.exe" -ForegroundColor White
    Write-Host "  - dist\DerivativeMill_Windows11_Portable.zip" -ForegroundColor White
    Write-Host ""

    Write-Host "Installation Options:" -ForegroundColor Green
    Write-Host "  1. Copy the $distDir folder to Program Files" -ForegroundColor White
    Write-Host "  2. Run INSTALL.bat to create desktop shortcut" -ForegroundColor White
    Write-Host "  3. Or simply copy the ZIP file to a USB drive (fully portable)" -ForegroundColor White
    Write-Host ""

    Write-Host "Documentation:" -ForegroundColor Green
    Write-Host "  - README.md        - Project overview" -ForegroundColor White
    Write-Host "  - QUICKSTART.md    - Quick start guide" -ForegroundColor White
    Write-Host "  - SETUP.md         - Detailed Windows setup" -ForegroundColor White
    Write-Host ""

    Write-Host "Next Steps:" -ForegroundColor Green
    Write-Host "  1. Test the executable: dist\DerivativeMill.exe" -ForegroundColor White
    Write-Host "  2. Create installers (MSI/NSIS) or distribute the ZIP" -ForegroundColor White
    Write-Host "  3. Share with Windows 11 users" -ForegroundColor White

    Write-Host ""
}
catch {
    Write-Error-Custom "An error occurred: $_"
    exit 1
}
finally {
    if (-not $SkipCleanup) {
        # Deactivate virtual environment
        deactivate 2>&1 | Out-Null
    }
}
