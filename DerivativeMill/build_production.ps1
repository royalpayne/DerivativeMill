# Build script for Derivative Mill application
# This script packages the application into a standalone executable

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Derivative Mill Production Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Use virtual environment Python
$venvPython = "C:\Users\hpayne\Documents\DevHouston\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Error: Virtual environment Python not found at $venvPython" -ForegroundColor Red
    exit 1
}

# Install PyInstaller if not already installed
Write-Host "Checking PyInstaller installation..." -ForegroundColor Yellow
& $venvPython -m pip show pyinstaller > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Green
    & $venvPython -m pip install pyinstaller
} else {
    Write-Host "PyInstaller already installed." -ForegroundColor Green
}

# Clean previous builds
Write-Host ""
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }

# Check for icon file
Write-Host ""
if (Test-Path "Resources/icon.ico") {
    Write-Host "Icon file found: Resources/icon.ico" -ForegroundColor Green
} elseif (Test-Path "Resources/icon.png") {
    Write-Host "Warning: icon.png found but icon.ico preferred for Windows" -ForegroundColor Yellow
    Write-Host "Consider converting PNG to ICO format" -ForegroundColor Yellow
} else {
    Write-Host "Warning: No icon file found in Resources folder" -ForegroundColor Yellow
    Write-Host "Application will use default Python icon" -ForegroundColor Yellow
}

# Build the executable
Write-Host ""
Write-Host "Building executable with PyInstaller..." -ForegroundColor Green
Write-Host "This may take a few minutes..." -ForegroundColor Yellow
Write-Host ""

& $venvPython -m PyInstaller --clean --onefile --windowed --add-data "Resources;Resources" --icon "Resources\icon.ico" --name "DerivativeMill" derivativemill.py

# Check if build was successful
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable location: dist\DerivativeMill.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the executable: .\dist\DerivativeMill.exe" -ForegroundColor White
    Write-Host "2. Ensure Input and Output folders exist where you deploy" -ForegroundColor White
    Write-Host "3. Deploy the entire 'dist' folder contents to target machine" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Build failed! Check errors above." -ForegroundColor Red
    Write-Host ""
}
