# DerivativeMill Windows 11 Installation Package

Complete Windows installation solution for DerivativeMill derivative tariff compliance system.

## Package Contents

This package includes everything needed to install and run DerivativeMill on Windows 10/11:

```
DerivativeMill_Windows11_Package/
├── DerivativeMill.exe                    # Standalone executable
├── Run_DerivativeMill.bat               # Quick launch script
├── INSTALL.bat                          # Installation and setup script
├── README.md                            # Project overview
├── QUICKSTART.md                        # 5-minute quick start
├── SETUP.md                             # Detailed setup guide
├── WINDOWS_INSTALLATION.md              # Windows-specific guide
├── Input/                               # Input folder (place files here)
├── Output/                              # Output folder (results saved here)
├── ProcessedPDFs/                       # Archive folder for processed PDFs
└── Resources/
    └── derivativemill.db                # Application database
```

## Quick Start (2 Minutes)

### Option A: No Installation (Fastest)

1. Extract the ZIP file anywhere
2. Double-click `DerivativeMill.exe`
3. Application starts immediately

### Option B: With Desktop Shortcut

1. Extract the ZIP file to your desired location
2. Double-click `INSTALL.bat`
3. Follow the prompts (creates desktop shortcut)
4. Launch from desktop or Start menu

### Option C: Install to Program Files

1. Extract ZIP to `C:\Program Files\DerivativeMill\`
2. Create a shortcut manually or use INSTALL.bat
3. Application is now system-wide accessible

## System Requirements

- **Operating System**: Windows 10 or Windows 11
- **Processor**: Intel Core i3 or equivalent (or better)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB free space
- **Display**: 1280x720 minimum resolution

## What's Included

### Executable
- **DerivativeMill.exe** - Standalone executable, no installation required
  - All dependencies bundled
  - Runs on any Windows 10/11 PC
  - ~200MB file size

### Scripts
- **INSTALL.bat** - Interactive installation script
  - Creates desktop shortcut
  - Sets up file associations
  - Asks for installation location
- **Run_DerivativeMill.bat** - Quick launcher
  - Double-click to start application
  - No additional steps

### Uninstallation
- **uninstall_windows.ps1** - PowerShell uninstaller
  - Safe removal with data preservation
  - Cleans up shortcuts and registry
  - Optional data backup

### Documentation
- **README.md** - Project overview and features
- **QUICKSTART.md** - Get started in 5 minutes
- **SETUP.md** - Detailed cross-platform setup
- **WINDOWS_INSTALLATION.md** - Windows-specific guide
- **TESTING_CHECKLIST.md** - QA testing procedures

## Installation Methods

### Method 1: Portable (No Installation)
Perfect for testing or USB drives
- Extract ZIP anywhere
- Run `DerivativeMill.exe`
- No system changes
- Fully reversible (just delete folder)

### Method 2: With Desktop Shortcut
Recommended for regular use
- Extract ZIP to desired location
- Run `INSTALL.bat`
- Desktop shortcut created
- Start menu entry added

### Method 3: System-Wide Installation
For corporate/shared environments
- Extract to `C:\Program Files\DerivativeMill\`
- Run `INSTALL.bat`
- All users can access
- System registry entries created

## First Time Setup

1. **Launch Application**
   - Double-click `DerivativeMill.exe`
   - Wait for window to appear (10-30 seconds)

2. **Configure Settings**
   - Click Settings (gear icon)
   - Set theme, font size
   - Configure folder locations
   - Add suppliers (optional)

3. **Import Your Data**
   - Click "Parts Import" tab
   - Load your parts CSV
   - Map columns
   - Click Import

4. **Process Your First Invoice**
   - Click "Process Shipment" tab
   - Load an invoice
   - Click "Process Shipment"
   - Check results in Output folder

## Folder Structure

After installation, you'll have:

```
C:\Program Files\DerivativeMill\          (or extraction location)
├── Input/                 ← Place invoice files here
├── Output/                ← Processed files appear here
├── ProcessedPDFs/         ← Archive old PDFs here
└── Resources/
    └── derivativemill.db  ← Application settings & data
```

**Important**: These folders contain your data. Back them up regularly!

## Uninstallation

### Option 1: Simple Delete
```
1. Close DerivativeMill.exe
2. Delete the DerivativeMill folder
3. Delete desktop shortcut (if created)
```

### Option 2: Using PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File uninstall_windows.ps1
```

This will:
- Close running instances
- Remove shortcuts and registry entries
- Back up your data to a safe location
- Clean up completely

### Option 3: Windows Settings
```
Settings → Apps → Apps & features → Search for "DerivativeMill" → Uninstall
```

## Troubleshooting

### Application won't start
- **Wait longer** - First launch takes 10-30 seconds
- **Run as Administrator** - Right-click → Run as Administrator
- **Check Windows Defender** - May be blocking the exe
- **Restart Windows** - Sometimes needed for first-time setup

### Slow performance
- **Check disk space** - Need at least 500MB free
- **Use local drive** - Avoid network drives
- **Close other apps** - Free up RAM and CPU
- **Check logs** - Log View tab may show issues

### File permission errors
- **Run as Administrator** - Right-click → Run as Administrator
- **Check folder permissions** - Folder → Properties → Security
- **Disable antivirus temporarily** - May be blocking writes

### Database errors
- **Delete Resources/derivativemill.db** - Database will be recreated
- **Restart application** - Close and reopen
- **Check antivirus** - May be blocking database access

See **WINDOWS_INSTALLATION.md** for detailed troubleshooting.

## Features

✓ Process PDF invoices with automatic table extraction
✓ Handle CSV and Excel files
✓ Column mapping for flexible data formats
✓ Parts database import and management
✓ Section 232 tariff code lookup
✓ Cross-platform support (Windows, macOS, Linux)
✓ Multiple theme options
✓ Dark/Light mode support
✓ Real-time data editing
✓ CSV export with customization
✓ Comprehensive logging
✓ Help and documentation built-in

## Updates

To update to a newer version:

1. **Backup** your current folder:
   ```
   Copy C:\Program Files\DerivativeMill to C:\Program Files\DerivativeMill_Backup
   ```

2. **Download** new version ZIP

3. **Extract** to same location (overwrite)

4. **Run** updated application

Your data in Input/, Output/, and ProcessedPDFs/ will be preserved.

## Getting Help

### In the Application
- **User Guide Tab** - Built-in help and tutorials
- **Log View Tab** - Error messages and debugging info
- **Settings** - Configure application to your needs
- **Keyboard Shortcuts** - Press Ctrl+H

### Documentation
- **QUICKSTART.md** - Get started in 5 minutes
- **WINDOWS_INSTALLATION.md** - Windows-specific guide
- **SETUP.md** - Detailed technical setup
- **README.md** - Project overview and features

### Backup Your Data

**Important folders to back up**:
- `Input/` - Original invoice files
- `Output/` - Processed results
- `ProcessedPDFs/` - Archived PDFs
- `Resources/derivativemill.db` - Settings and database

**Backup procedure**:
```
1. Close DerivativeMill
2. Copy the entire DerivativeMill folder to:
   - External hard drive
   - USB drive
   - Cloud storage (OneDrive, Dropbox, etc.)
3. Reopen DerivativeMill
```

## Portable USB Drive Setup

DerivativeMill works great on USB drives!

1. **Extract** ZIP to USB drive:
   ```
   E:\DerivativeMill\         (where E: is your USB drive)
   ```

2. **Run** `DerivativeMill.exe` directly from USB

3. **All data stays on USB** - Take it anywhere

**Advantages**:
- Fully portable
- No installation on host computer
- Take your work anywhere
- Easy to share

**Note**: USB performance will be slower than local drive.

## System Information

### Supported Windows Versions
- Windows 10 (1909 or later)
- Windows 11 (all versions)

### Not supported
- Windows 7 or earlier
- Windows Server editions (untested)

### Hardware
- x86-64 bit processors only
- 32-bit Windows not supported
- ARM processors not supported (for now)

## Technology Stack

- **Python 3.12** - Application runtime
- **PyQt5** - User interface framework
- **pandas** - Data processing
- **openpyxl** - Excel file support
- **pdfplumber** - PDF extraction
- **SQLite3** - Database engine
- **Pillow** - Image processing

All dependencies are bundled in the executable.

## License

DerivativeMill is provided as-is. See README.md for full terms.

## Version Information

- **Version**: 1.08
- **Release Date**: December 2024
- **Package Type**: Windows 11 Standalone
- **Build Platform**: Python 3.8+

## File Manifest

```
Installation Size: ~200MB (executable)
Extracted Size: ~500MB (with resources and data)
Database Size: ~1.5MB (initial)
Runtime Memory: 150-400MB (depending on data size)
Disk Space Required: 500MB minimum free
```

## Next Steps

1. **Extract** the ZIP file
2. **Run** `DerivativeMill.exe` to start
3. **Read** QUICKSTART.md for first steps
4. **Configure** Settings for your workflow
5. **Import** your data and start processing

## Support Resources

- **WINDOWS_INSTALLATION.md** - Complete Windows guide
- **QUICKSTART.md** - 5-minute tutorial
- **SETUP.md** - Technical setup details
- **TESTING_CHECKLIST.md** - QA procedures
- **User Guide Tab** - Built-in help (in application)

## FAQ

**Q: Do I need Python installed?**
A: No! Everything is bundled in the executable.

**Q: Can I run this on a USB drive?**
A: Yes! Fully portable.

**Q: Can multiple people use this?**
A: Yes, but only one person at a time can use the application.

**Q: Is internet required?**
A: No, it runs completely offline.

**Q: Where is my data stored?**
A: In the Input/, Output/, ProcessedPDFs/ folders and the database.

**Q: Can I uninstall cleanly?**
A: Yes, either delete the folder or run uninstall_windows.ps1

**Q: What if I lose my data?**
A: Back up the Input/ and Output/ folders regularly.

**Q: Can I run this alongside other applications?**
A: Yes, but it requires ~200MB RAM and uses disk space.

---

**Ready to get started?** Run `DerivativeMill.exe` now!

For detailed instructions, see **WINDOWS_INSTALLATION.md**

