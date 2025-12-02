# Building DerivativeMill Windows Installation Package

Complete guide for building the Windows 11 installation package from source.

## Overview

This document explains how to build the DerivativeMill Windows installation package using PyInstaller and batch/PowerShell scripts.

## Prerequisites

### On Windows 11 PC

1. **Python 3.8+** installed and in PATH
   - Download from: https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation

2. **Git** (optional, for cloning repository)
   - Download from: https://git-scm.com/download/win

3. **7-Zip or WinRAR** (for creating ZIP files)
   - Or use built-in Windows compression

### On Development Machine (Any OS)

For building on macOS or Linux (creating Windows package):
- Same Python and dependencies as above
- PyInstaller works cross-platform

## Project Structure

```
Project_mv/
├── DerivativeMill/
│   ├── derivativemill.py          # Main application
│   ├── platform_utils.py          # Cross-platform utilities
│   └── Resources/
│       ├── derivativemill.ico     # Application icon
│       └── derivativemill.db      # Application database
├── requirements.txt               # Python dependencies
├── build_windows.spec             # PyInstaller configuration
├── build_windows_installer.bat    # Build script (batch)
├── build_windows_installer.ps1    # Build script (PowerShell)
├── uninstall_windows.ps1          # Uninstaller script
├── README.md                      # Project overview
├── QUICKSTART.md                  # Quick start guide
├── SETUP.md                       # Setup instructions
├── WINDOWS_INSTALLATION.md        # Windows guide
└── WINDOWS_PACKAGE_README.md      # Package documentation
```

## Build Process

### Method 1: Using Batch Script (Windows)

**Easiest method for Windows users**

```bash
# 1. Open Command Prompt or PowerShell
# 2. Navigate to project directory
cd C:\path\to\Project_mv

# 3. Create virtual environment (if not exists)
python -m venv venv

# 4. Run the build script
build_windows_installer.bat

# 5. Wait for build to complete (2-5 minutes)
```

**What the script does**:
- Checks Python installation
- Activates virtual environment
- Installs PyInstaller
- Builds standalone executable
- Creates directory structure
- Generates portable ZIP package

**Output**:
```
dist/
├── DerivativeMill.exe
├── DerivativeMill_Windows11_Portable.zip
└── DerivativeMill/
    ├── DerivativeMill.exe
    ├── INSTALL.bat
    ├── Run_DerivativeMill.bat
    ├── README.md
    ├── QUICKSTART.md
    ├── SETUP.md
    ├── Input/
    ├── Output/
    ├── ProcessedPDFs/
    └── Resources/
        └── derivativemill.db
```

### Method 2: Using PowerShell Script

**Modern method with better error handling**

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to project directory
cd C:\path\to\Project_mv

# 3. Enable script execution (if needed)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser

# 4. Run the PowerShell build script
.\build_windows_installer.ps1

# 5. Optional parameters:
# Skip the build step (use previous build)
.\build_windows_installer.ps1 -SkipBuild

# Don't deactivate virtual environment after
.\build_windows_installer.ps1 -SkipCleanup
```

**Advantages**:
- Better error messages
- Color-coded output
- More reliable
- Optional parameters
- Better cleanup

### Method 3: Manual Build with PyInstaller

**For advanced users / debugging**

```bash
# 1. Activate virtual environment
# Windows:
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install PyInstaller wheel

# 3. Run PyInstaller with spec file
pyinstaller build_windows.spec

# 4. Create directory structure manually
mkdir dist\DerivativeMill
copy dist\DerivativeMill.exe dist\DerivativeMill\
copy README.md dist\DerivativeMill\
copy QUICKSTART.md dist\DerivativeMill\
copy SETUP.md dist\DerivativeMill\

# 5. Create empty data folders
mkdir dist\DerivativeMill\Input
mkdir dist\DerivativeMill\Output
mkdir dist\DerivativeMill\ProcessedPDFs

# 6. Create ZIP archive
# Using 7-Zip:
7z a dist\DerivativeMill_Windows11_Portable.zip dist\DerivativeMill

# Using PowerShell:
Compress-Archive -Path dist\DerivativeMill -DestinationPath dist\DerivativeMill_Windows11_Portable.zip -Force
```

## Configuration

### PyInstaller Spec File (build_windows.spec)

The spec file controls how PyInstaller builds the executable:

```python
# Key settings:
a = Analysis(
    ['DerivativeMill/derivativemill.py'],  # Entry point
    datas=[
        ('DerivativeMill/Resources', 'DerivativeMill/Resources'),  # Include resources
        ('README.md', '.'),  # Include docs
    ],
    hiddenimports=[...],  # Modules to include
    ...
)

exe = EXE(
    ...,
    name='DerivativeMill',  # Executable name
    windowed=False,  # No console window
    icon='DerivativeMill/Resources/derivativemill.ico',  # Application icon
)
```

### Customization Options

**Change application name**:
```
Edit: name='DerivativeMill'  →  name='YourAppName'
```

**Change application icon**:
```
Edit: icon='DerivativeMill/Resources/derivativemill.ico'  →  icon='path/to/your/icon.ico'
```

**Include additional files**:
```python
datas=[
    ('DerivativeMill/Resources', 'DerivativeMill/Resources'),
    ('path/to/extra/files', 'destination/in/bundle'),
]
```

**Add hidden imports**:
```python
hiddenimports=[
    'your_module',
    'another_module',
]
```

## Build Troubleshooting

### Issue: "Python is not installed"

**Solution**:
1. Check Python is in PATH: `python --version`
2. If not, add Python to PATH:
   - Settings → System → Environment Variables
   - Add Python installation directory to PATH
   - Restart command prompt

### Issue: Virtual environment not found

**Solution**:
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate.bat  # Windows
source venv/bin/activate   # macOS/Linux
```

### Issue: "PyInstaller not found"

**Solution**:
```bash
# Activate virtual environment first
venv\Scripts\activate.bat

# Install PyInstaller
pip install PyInstaller
```

### Issue: Build takes too long

**Normal**: First build takes 2-5 minutes
- All dependencies are analyzed and bundled
- Subsequent builds are slightly faster
- Check system resources if extremely slow

### Issue: Executable won't start

**Solutions**:
1. Check Windows Defender isn't blocking it
2. Add exception to antivirus software
3. Try running as Administrator
4. Check Event Viewer for error details

### Issue: Icon not appearing

**Solution**:
1. Verify icon file exists at correct path
2. Icon must be .ico format
3. Recommended size: 256x256 or 128x128 pixels
4. If no icon provided, Windows default is used

## File Manifest

### Included in build_windows.spec

These files are included in the built executable:

```
DerivativeMill/
├── derivativemill.py         ← Python bytecode compiled
├── platform_utils.py         ← Python bytecode compiled
├── Resources/
│   ├── derivativemill.db     ← SQLite database
│   └── derivativemill.ico    ← Application icon
├── README.md                 ← Project documentation
└── QUICKSTART.md            ← Quick start guide
```

### Created by build script

```
dist/
├── DerivativeMill.exe                    # Main executable (~200MB)
├── DerivativeMill/                       # Distribution folder
│   ├── DerivativeMill.exe               # Copy of executable
│   ├── Run_DerivativeMill.bat           # Quick launcher
│   ├── INSTALL.bat                      # Setup script
│   ├── README.md                        # Docs
│   ├── QUICKSTART.md                    # Docs
│   ├── SETUP.md                         # Docs
│   ├── Input/                           # Data folder
│   ├── Output/                          # Data folder
│   ├── ProcessedPDFs/                   # Data folder
│   └── Resources/
│       └── derivativemill.db            # Database
└── DerivativeMill_Windows11_Portable.zip # ZIP package
```

## Optimization

### Reduce Executable Size

**Current size**: ~200MB (typical)

**To reduce size**:

1. **Use UPX compression**:
   ```bash
   pip install upx
   # Already enabled in spec file (upx=True)
   ```

2. **Remove unused modules**:
   - Edit build_windows.spec
   - Remove from hiddenimports
   - Remove from datas

3. **Single-file vs directory**:
   - Single-file: Slower startup, larger file
   - Directory: Faster startup, smaller per-file size
   - Currently using single-file (--onefile)

### Improve Performance

1. **Rebuild caches**:
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt --upgrade
   ```

2. **Use latest PyInstaller**:
   ```bash
   pip install PyInstaller --upgrade
   ```

3. **Clear old builds**:
   ```bash
   rmdir /s build
   rmdir /s dist
   ```

## Distribution

### Package Contents

Include with the executable:

```
DerivativeMill_Windows11_Package/
├── DerivativeMill_Windows11_Portable.zip
├── WINDOWS_INSTALLATION.md
├── WINDOWS_PACKAGE_README.md
├── QUICKSTART.md
└── Setup_Instructions.txt
```

### Distribution Methods

1. **Direct Download** (Recommended)
   - Host ZIP on website
   - Users extract and run

2. **Installer EXE** (Professional)
   - Use NSIS or Inno Setup
   - Creates standard Windows installer
   - See below for details

3. **Windows Store** (Advanced)
   - Register application
   - Submit for review
   - Users install from Microsoft Store

4. **Portable USB**
   - Copy ZIP to USB drive
   - Works on any Windows PC
   - No installation needed

### Creating Professional Installer (NSIS)

For a professional `.msi` or `.exe` installer:

1. **Install NSIS**:
   - Download from: https://nsis.sourceforge.io/Download

2. **Create installer script** (`setup.nsi`):
   ```nsis
   ; DerivativeMill Windows Installer
   ; ... (detailed template provided)
   ```

3. **Build installer**:
   ```bash
   makensis setup.nsi
   ```

This creates `DerivativeMill_Setup.exe` for professional distribution.

## Testing the Build

### Before Release

1. **Test on clean Windows**:
   - Virtual machine or separate PC
   - Fresh Windows 11 installation
   - No Python installed (verify bundling works)

2. **Test functionality**:
   ```
   ✓ Application starts
   ✓ All tabs visible
   ✓ Load file works
   ✓ Process shipment works
   ✓ Settings dialog works
   ✓ Log view works
   ✓ No console errors
   ✓ Database persists between runs
   ```

3. **Test uninstallation**:
   ```
   ✓ Run uninstall_windows.ps1
   ✓ Shortcuts removed
   ✓ Files deleted
   ✓ Data backed up
   ```

4. **Test from different locations**:
   ```
   ✓ Program Files
   ✓ Desktop
   ✓ USB drive
   ✓ Network drive (if applicable)
   ```

## Performance Metrics

### Typical Build Statistics

| Metric | Value |
|--------|-------|
| Build Time | 2-5 minutes |
| Executable Size | ~200MB |
| Uncompressed Size | ~500MB |
| Startup Time | 2-10 seconds |
| Memory Usage | 150-400MB |
| Disk Space Used | 500MB+ |

### Build Requirements

| Resource | Requirement |
|----------|-------------|
| Disk Space | 2GB (for build) |
| RAM | 2GB minimum |
| CPU | Any modern processor |
| Network | For pip install |
| Time | 5-10 minutes total |

## Version Control

### What to commit

```
✓ build_windows.spec
✓ build_windows_installer.bat
✓ build_windows_installer.ps1
✓ uninstall_windows.ps1
✓ WINDOWS_INSTALLATION.md
✓ WINDOWS_PACKAGE_README.md
✓ BUILD_WINDOWS_PACKAGE.md
```

### What NOT to commit

```
✗ dist/               (too large)
✗ build/              (build artifacts)
✗ *.pyc               (compiled files)
✗ .spec files         (auto-generated)
✗ venv/               (virtual environment)
```

Update `.gitignore`:
```
# Build artifacts
build/
dist/
*.spec
*.pyc
__pycache__/
venv/
```

## Advanced Topics

### Code Signing

For professional distribution (optional):

1. **Obtain code signing certificate**
   - Comodo, DigiCert, etc.
   - Cost: $100-500/year

2. **Sign the executable**:
   ```bash
   signtool sign /f cert.pfx /p password /t http://timestamp.server /d "DerivativeMill" dist\DerivativeMill.exe
   ```

3. **Sign the installer**:
   - Same process for setup.exe

**Benefits**:
- No security warnings
- Higher trust
- Professional appearance
- Required for enterprise

### Auto-Update Capability

To enable auto-updates:

1. **Host update file** on web server
2. **Check for updates** at startup
3. **Download and apply** update
4. **Restart application** with new version

Example implementation in derivativemill.py:
```python
def check_for_updates(self):
    # Check version on server
    # Download if newer available
    # Apply update
    # Restart application
```

### Nightly Builds

For continuous deployment:

1. **GitHub Actions** workflow
2. **Automatic building** on commit
3. **Upload to releases**
4. **Users get updates** automatically

Example `.github/workflows/build.yml`:
```yaml
name: Build Windows Package
on: [push]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: build_windows_installer.ps1
      - uses: actions/upload-artifact@v2
```

## Support Resources

### Documentation
- **WINDOWS_INSTALLATION.md** - User guide
- **WINDOWS_PACKAGE_README.md** - Package info
- **SETUP.md** - Technical setup
- **QUICKSTART.md** - Quick start

### Tools
- PyInstaller: https://pyinstaller.org/
- NSIS: https://nsis.sourceforge.io/
- 7-Zip: https://www.7-zip.org/
- Python: https://www.python.org/

### References
- PyInstaller Docs: https://pyinstaller.readthedocs.io/
- Windows App Packaging: https://docs.microsoft.com/en-us/windows/apps/
- Code Signing: https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools

## Troubleshooting

See **WINDOWS_INSTALLATION.md** for common user issues.

For build-specific issues:

1. **Check logs**: PyInstaller logs are detailed
2. **Try manual build**: Debug with Method 3 above
3. **Check dependencies**: `pip list` vs requirements.txt
4. **Verify icon**: Test with invalid icon path to see error
5. **Test on clean VM**: Eliminates user environment issues

## Summary

**Quick Build**: `build_windows_installer.bat` or `.ps1`
**Output**: `dist/DerivativeMill_Windows11_Portable.zip`
**Test**: Extract and run `DerivativeMill.exe`
**Distribute**: Share the ZIP or create .msi installer

---

**Version**: 1.08
**Last Updated**: December 2024
**Platform**: Windows 10 / Windows 11

