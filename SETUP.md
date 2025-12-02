# DerivativeMill - Cross-Platform Setup Guide

DerivativeMill is designed to run on **Windows**, **macOS**, and **Linux**. This guide covers installation and setup for each platform.

## System Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for application and data
- **Display**: 1280x720 minimum resolution

## Quick Start (All Platforms)

### 1. Install Python 3.8+

**Windows**: Download from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation

**macOS**: Install via Homebrew
```bash
brew install python3
```

**Linux**: Use your package manager
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-venv python3-pip

# Fedora
sudo dnf install python3 python3-venv python3-pip

# Arch
sudo pacman -S python
```

### 2. Clone/Download the Application

```bash
cd /path/to/DerivativeMill
```

### 3. Create Virtual Environment

**Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt)**:
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS/Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python DerivativeMill/derivativemill.py
```

---

## Platform-Specific Notes

### Windows

**Additional Setup** (Optional):
- For native Windows file dialogs and better integration, the application uses standard PyQt5
- The application will create the following directories automatically:
  - `./Input/` - Supplier invoice folders
  - `./Output/` - Processed data exports
  - `./ProcessedPDFs/` - Archived PDFs
  - `./Resources/` - Database and resources

**Creating a Shortcut**:
1. Create a `.bat` file (e.g., `run_derivativemill.bat`):
   ```batch
   @echo off
   cd /d "%~dp0"
   call venv\Scripts\activate.bat
   python DerivativeMill\derivativemill.py
   pause
   ```
2. Right-click → Create shortcut → Move to Desktop

**Building an Executable** (Optional):
```bash
pip install PyInstaller
pyinstaller --onefile --windowed --icon=icon.ico DerivativeMill/derivativemill.py
```

---

### macOS

**Additional Setup**:
- Requires Xcode Command Line Tools
  ```bash
  xcode-select --install
  ```

**File Permissions**:
- The application creates config files in `~/Library/Application Support/DerivativeMill/`
- Ensure your user account has write permissions (usually automatic)

**Creating an App Bundle** (Optional):
```bash
pip install PyInstaller
pyinstaller --onefile --windowed DerivativeMill/derivativemill.py
# Result will be in dist/derivativemill.app
```

**Security Warning**:
- macOS may warn about unsigned applications on first run
- Click "Open" in Security & Privacy settings or use `xattr -d com.apple.quarantine ./derivativemill`

---

### Linux

**Additional Dependencies**:

**Ubuntu/Debian**:
```bash
sudo apt-get install python3-pyqt5 libqt5gui5 libqt5core5a
```

**Fedora/RHEL**:
```bash
sudo dnf install python3-qt5
```

**Arch**:
```bash
sudo pacman -S python-pyqt5
```

**File Manager Integration** (Optional):
The application will automatically use:
- `xdg-open` to open files and folders
- Desktop file manager (Nautilus, Dolphin, etc.)

**Desktop Entry** (Optional - for app menu):
Create `~/.local/share/applications/derivativemill.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Derivative Mill
Exec=/path/to/venv/bin/python /path/to/DerivativeMill/derivativemill.py
Icon=application-x-executable
Terminal=false
Categories=Utility;Office;
```

---

## Configuration

### Data Locations

The application stores data in platform-appropriate directories:

**Windows**:
- Data: `%APPDATA%\DerivativeMill\`
- Config: `%APPDATA%\DerivativeMill\`
- Invoices: `.\Input\` (relative to application)

**macOS**:
- Data: `~/Library/Application Support/DerivativeMill/`
- Config: `~/Library/Preferences/DerivativeMill/`
- Invoices: `./Input/` (relative to application)

**Linux**:
- Data: `~/.local/share/DerivativeMill/` (XDG compliant)
- Config: `~/.config/DerivativeMill/` (XDG compliant)
- Invoices: `./Input/` (relative to application)

### Settings

All settings are saved in the database:
- Theme preference
- Excel viewer (Linux only)
- Column mappings
- Supplier configurations

Settings are automatically loaded on startup.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt5'"
**Solution**: Ensure virtual environment is activated and requirements installed
```bash
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

### "Permission denied" on Linux/macOS
**Solution**: Ensure the script has execute permissions
```bash
chmod +x DerivativeMill/derivativemill.py
```

### Application won't start
1. Check Python version: `python --version` (should be 3.8+)
2. Verify all dependencies: `pip list`
3. Check logs in the application's Log View tab

### File operations slow on network drives
**Solution**: Work with local files, then copy to network locations:
1. Use local Input/ and Output folders
2. Copy processed files to network afterward
3. This is faster and more reliable

---

## Building Executable Bundles

### One-File Executable (All Platforms)

```bash
# Install PyInstaller
pip install PyInstaller

# Build executable
pyinstaller --onefile --windowed --name DerivativeMill \
  --icon=icon.ico \
  DerivativeMill/derivativemill.py

# On macOS/Linux, also copy the database
cp DerivativeMill/Resources/derivativemill.db dist/
```

### Distribution

1. Include `requirements.txt` with the application
2. Create a README with quick-start instructions
3. Test on clean systems before distribution
4. Consider code signing on macOS/Windows

---

## Support & Updates

- **Report Issues**: Check the Log View tab for error details
- **Check Version**: Application title shows current version
- **Database**: Located in `Resources/derivativemill.db`

---

## Uninstallation

**Windows**:
- Delete the application folder
- Use Control Panel → Programs → Uninstall if installed as app

**macOS**:
```bash
rm -rf /path/to/DerivativeMill
rm -rf ~/Library/Application\ Support/DerivativeMill/
```

**Linux**:
```bash
rm -rf /path/to/DerivativeMill
rm -rf ~/.local/share/DerivativeMill/
rm -rf ~/.config/DerivativeMill/
```

---

## Advanced: Custom Configuration

Edit `DerivativeMill/derivativemill.py` to customize:
- `APP_NAME`: Application display name
- `VERSION`: Version number
- `DB_NAME`: Database filename
- Path configurations (lines 69-95)

---

**Last Updated**: December 2024
**Compatible Platforms**: Windows 10+, macOS 10.13+, Linux (most distributions)
