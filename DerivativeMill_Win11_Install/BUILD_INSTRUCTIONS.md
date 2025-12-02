# Building DerivativeMill Windows Installation Package

Step-by-step instructions for building the Windows 11 installation package.

⚠️ **Important**: Only include production files in the distribution. The `_Archive/` directory (containing old development files) is automatically excluded from the build.

## Prerequisites

1. **Windows 11 PC** with Python 3.8+ installed
2. **Python in PATH** - Verify with: `python --version`
3. **Project Directory** - Navigate to the main project directory
4. **Virtual Environment** - Must be created and ready

## Quick Setup (First Time Only)

### 1. Verify Project Structure

```
C:\path\to\Project_mv\
├── DerivativeMill/                 (Core application)
├── DerivativeMill_Win11_Install/   (This directory)
├── requirements.txt
└── setup.py
```

### 2. Create Virtual Environment

```batch
cd C:\path\to\Project_mv
python -m venv venv
```

### 3. Activate Virtual Environment

```batch
venv\Scripts\activate.bat
```

You should see `(venv)` in your command prompt.

### 4. Install Dependencies

```batch
pip install -r requirements.txt
pip install PyInstaller wheel
```

## Building the Package

### Method 1: Using Batch Script (Recommended)

**From Project Root Directory:**

```batch
cd C:\path\to\Project_mv
DerivativeMill_Win11_Install\scripts\build_windows_installer.bat
```

Or double-click: `build_windows_installer.bat`

**What it does:**
- Checks Python installation
- Activates virtual environment
- Installs PyInstaller
- Builds executable (2-5 minutes)
- Creates directory structure
- Generates ZIP package

**Output:** `dist\DerivativeMill_Windows11_Portable.zip`

### Method 2: Manual Build with PyInstaller

**From Project Root Directory:**

```batch
cd C:\path\to\Project_mv
venv\Scripts\activate.bat
pyinstaller DerivativeMill_Win11_Install\scripts\build_windows.spec
```

Then manually create the directory structure:

```batch
mkdir dist\DerivativeMill
copy dist\DerivativeMill.exe dist\DerivativeMill\
copy README.md dist\DerivativeMill\
copy QUICKSTART.md dist\DerivativeMill\
copy SETUP.md dist\DerivativeMill\
mkdir dist\DerivativeMill\Input
mkdir dist\DerivativeMill\Output
mkdir dist\DerivativeMill\ProcessedPDFs
```

Then create the ZIP:

```batch
cd dist
powershell -Command "Compress-Archive -Path DerivativeMill -DestinationPath DerivativeMill_Windows11_Portable.zip -Force"
cd ..
```

## Important Notes

### Path Issues

The scripts reference parent directories using relative paths. **Must run from Project Root:**
- ❌ WRONG: `cd DerivativeMill_Win11_Install\scripts` then run script
- ✅ CORRECT: `cd C:\path\to\Project_mv` then run script

### Virtual Environment Location

The scripts expect `venv\` in the project root:
```
C:\path\to\Project_mv\venv\  ← Must be here
```

### Python and Dependencies

Make sure all dependencies are installed:
```batch
pip install -r requirements.txt
pip install PyInstaller wheel
```

## Troubleshooting

### "Python not found"

**Solution:**
1. Verify Python is installed: `python --version`
2. Add Python to PATH:
   - Settings → System → Environment Variables
   - Add Python installation folder to PATH
   - Restart command prompt

### "Virtual environment not found"

**Solution:**
```batch
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### "PyInstaller not found"

**Solution:**
```batch
pip install PyInstaller wheel
```

### Build takes too long

**Normal:** First build takes 2-5 minutes
- Subsequent builds may be slightly faster
- Check available disk space (needs 2GB+)

### "Access denied" errors

**Solution:**
1. Close any open files from dist/ or build/ folders
2. Delete dist/ and build/ folders
3. Run antivirus scan (may be blocking file access)
4. Try again

## File Locations

**Input Files:**
- Main application: `DerivativeMill/derivativemill.py`
- Spec file: `DerivativeMill_Win11_Install/scripts/build_windows.spec`
- Requirements: `requirements.txt`
- Documentation: `README.md`, `QUICKSTART.md`, `SETUP.md`

**Explicitly Excluded from Distribution:**
- `_Archive/` - Old development files (not included in package)
- `venv/`, `build/`, `dist/` - Build artifacts (not included)
- `Input/`, `Output/`, `ProcessedPDFs/` - User data (recreated by app)
- Test files, temporary files, user-specific config

**Output Files:**
- Executable: `dist/DerivativeMill.exe`
- Distribution package: `dist/DerivativeMill_Windows11_Portable.zip`
- Directory package: `dist/DerivativeMill/`

## Build Process Summary

```
1. Check Python installation
2. Activate virtual environment
3. Install build tools (PyInstaller)
4. Compile Python code to executable
5. Bundle all dependencies
6. Create directory structure
7. Copy documentation
8. Generate ZIP distribution package
```

**Total time:** 2-5 minutes
**Output size:** ~200 MB executable + ~50 MB ZIP

## After Building

### Test the Executable

```batch
dist\DerivativeMill.exe
```

Application should start in 2-10 seconds.

### Create Distribution

```batch
REM Copy the ZIP file to distribution location
copy dist\DerivativeMill_Windows11_Portable.zip C:\share\installations\

REM Or compress further if needed
powershell -Command "Compress-Archive -Path dist\DerivativeMill_Windows11_Portable.zip -DestinationPath DerivativeMill_v1.08.zip -Force"
```

## Updating the Package

To build a new version after code changes:

1. Update version in `DerivativeMill/derivativemill.py`
2. Update version in `setup.py`
3. Make any code changes
4. Run build script again
5. Test new executable
6. Share new ZIP file

## Getting Help

**Build Issues:**
- See `docs/BUILD_WINDOWS_PACKAGE.md` for advanced configuration
- Check `docs/WINDOWS_INSTALLATION.md` for user issues

**Path Issues:**
- Ensure you're in the project root (where `requirements.txt` is)
- Check that `DerivativeMill_Win11_Install/` exists

**Dependency Issues:**
- Reinstall: `pip install -r requirements.txt --upgrade`
- Check installed packages: `pip list`

## Quick Reference

| Task | Command |
|------|---------|
| Check Python | `python --version` |
| Create venv | `python -m venv venv` |
| Activate venv | `venv\Scripts\activate.bat` |
| Install deps | `pip install -r requirements.txt` |
| Install PyInstaller | `pip install PyInstaller` |
| Build with batch | `DerivativeMill_Win11_Install\scripts\build_windows_installer.bat` |
| Build manual | `pyinstaller DerivativeMill_Win11_Install\scripts\build_windows.spec` |
| Test executable | `dist\DerivativeMill.exe` |

---

**Version:** 1.08
**Last Updated:** December 2024
**Platform:** Windows 10/11

