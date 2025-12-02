# DerivativeMill Windows Uninstaller Script
# This script safely removes DerivativeMill while preserving user data

param(
    [switch]$KeepData = $true,  # Keep data files by default
    [switch]$RemoveAll = $false # Remove everything including data
)

# Colors for output
$colors = @{
    Header = "Yellow"
    Success = "Green"
    Warning = "Cyan"
    Error = "Red"
    Info = "White"
}

function Write-Header {
    param([string]$Text)
    Write-Host "`n============================================================" -ForegroundColor $colors.Header
    Write-Host $Text -ForegroundColor $colors.Header
    Write-Host "============================================================`n" -ForegroundColor $colors.Header
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor $colors.Success
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠ $Text" -ForegroundColor $colors.Warning
}

function Write-CustomError {
    param([string]$Text)
    Write-Host "✗ ERROR: $Text" -ForegroundColor $colors.Error
}

# Main execution
try {
    Write-Header "DerivativeMill Uninstaller"

    # Check if running as administrator (recommended)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warning "Running without administrator privileges. Some operations may fail."
        Write-Host "Recommended: Run this script as Administrator" -ForegroundColor $colors.Warning
        Write-Host ""
    }

    # Ask user for confirmation
    Write-Host "This will uninstall DerivativeMill from your computer." -ForegroundColor $colors.Info
    Write-Host ""

    if ($RemoveAll) {
        Write-Host "Data removal: ALL FILES AND DATA WILL BE DELETED" -ForegroundColor $colors.Error
        Write-Host "This includes: Input/, Output/, ProcessedPDFs/, and database" -ForegroundColor $colors.Error
        Write-Host ""
    } else {
        Write-Host "Data removal: User data will be PRESERVED" -ForegroundColor $colors.Success
        Write-Host "Your files in Input/, Output/, and ProcessedPDFs/ will be kept" -ForegroundColor $colors.Success
        Write-Host ""
    }

    Write-Host "Proceed with uninstallation? [Y/N]: " -NoNewline -ForegroundColor $colors.Warning
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "Uninstallation cancelled." -ForegroundColor $colors.Info
        exit 0
    }

    Write-Host ""

    # Find installation directory
    Write-Host "Looking for DerivativeMill installation..." -ForegroundColor $colors.Warning

    $possiblePaths = @(
        "C:\Program Files\DerivativeMill",
        "C:\Program Files (x86)\DerivativeMill",
        "$env:USERPROFILE\AppData\Local\Programs\DerivativeMill",
        "$env:USERPROFILE\Desktop\DerivativeMill",
        $PWD.Path
    )

    $installPath = $null
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            Write-Host "Found at: $path" -ForegroundColor $colors.Info
            $installPath = $path
            break
        }
    }

    if (-not $installPath) {
        Write-CustomError "DerivativeMill installation not found"
        Write-Host "Checked locations:" -ForegroundColor $colors.Info
        $possiblePaths | ForEach-Object { Write-Host "  - $_" -ForegroundColor $colors.Info }
        Write-Host ""
        Write-Host "Please manually delete the DerivativeMill folder" -ForegroundColor $colors.Warning
        exit 1
    }

    Write-Success "Installation found"
    Write-Host ""

    # Close running instances
    Write-Host "Closing any running DerivativeMill instances..." -ForegroundColor $colors.Warning
    Get-Process -Name "DerivativeMill" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Success "Application closed"
    Write-Host ""

    # Remove desktop shortcuts
    Write-Host "Removing shortcuts..." -ForegroundColor $colors.Warning

    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = "$desktopPath\DerivativeMill.lnk"

    if (Test-Path $shortcutPath) {
        Remove-Item -Path $shortcutPath -Force
        Write-Success "Removed desktop shortcut"
    }

    # Remove Start Menu shortcut
    $startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\DerivativeMill.lnk"
    if (Test-Path $startMenuPath) {
        Remove-Item -Path $startMenuPath -Force
        Write-Success "Removed Start Menu shortcut"
    }

    Write-Host ""

    # Preserve data if requested
    if ($KeepData -and -not $RemoveAll) {
        Write-Host "Preserving user data..." -ForegroundColor $colors.Warning

        $backupPath = "$env:USERPROFILE\DerivativeMill_Backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
        $dataFiles = @("Input", "Output", "ProcessedPDFs", "Resources\derivativemill.db")

        # Create backup directory
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

        # Copy data files
        foreach ($file in $dataFiles) {
            $sourcePath = Join-Path -Path $installPath -ChildPath $file
            if (Test-Path $sourcePath) {
                $destinationPath = Join-Path -Path $backupPath -ChildPath (Split-Path -Leaf $sourcePath)
                Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
            }
        }

        Write-Success "Data backed up to: $backupPath"
        Write-Host ""
    }

    # Remove installation directory
    Write-Host "Removing installation files..." -ForegroundColor $colors.Warning

    try {
        Remove-Item -Path $installPath -Recurse -Force -ErrorAction Stop
        Write-Success "Installation directory removed"
    }
    catch {
        Write-Warning "Could not fully remove installation directory"
        Write-Host "Error: $_" -ForegroundColor $colors.Error
        Write-Host "You may need to manually delete: $installPath" -ForegroundColor $colors.Warning
    }

    Write-Host ""

    # Cleanup registry entries (if they exist)
    Write-Host "Cleaning up system registry..." -ForegroundColor $colors.Warning

    $regPaths = @(
        "HKCU:\Software\DerivativeMill",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DerivativeMill"
    )

    foreach ($regPath in $regPaths) {
        if (Test-Path $regPath) {
            Remove-Item -Path $regPath -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Success "Registry cleanup complete"
    Write-Host ""

    # Final summary
    Write-Header "Uninstallation Complete"

    Write-Host "DerivativeMill has been successfully uninstalled." -ForegroundColor $colors.Success
    Write-Host ""

    if ($KeepData -and -not $RemoveAll) {
        Write-Host "Your data has been preserved at:" -ForegroundColor $colors.Info
        Write-Host "  $backupPath" -ForegroundColor $colors.Info
        Write-Host ""
        Write-Host "You can access these files anytime:" -ForegroundColor $colors.Info
        Write-Host "  - Input/ folder: Original invoice files" -ForegroundColor $colors.Info
        Write-Host "  - Output/ folder: Processed results" -ForegroundColor $colors.Info
        Write-Host "  - ProcessedPDFs/ folder: Archived PDFs" -ForegroundColor $colors.Info
        Write-Host "  - Resources/derivativemill.db: Application settings" -ForegroundColor $colors.Info
    } else {
        Write-Host "All files have been removed." -ForegroundColor $colors.Warning
    }

    Write-Host ""
    Write-Host "Thank you for using DerivativeMill!" -ForegroundColor $colors.Success

    Write-Host ""
}
catch {
    Write-CustomError "An error occurred during uninstallation: $_"
    Write-Host "Please manually delete the DerivativeMill folder at: $installPath" -ForegroundColor $colors.Warning
    exit 1
}
