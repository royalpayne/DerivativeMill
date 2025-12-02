# DerivativeMill - Windows 11 Installation Guide

Complete installation instructions for Windows 11 PCs.

## System Requirements

- **OS**: Windows 10 or Windows 11
- **Disk Space**: 500MB free
- **RAM**: 4GB minimum, 8GB recommended
- **Display**: 1280x720 minimum resolution

## Installation Methods

There are several ways to install DerivativeMill on Windows 11:

### Method 1: Portable ZIP (Easiest - No Installation Required)

**Best for**: USB drives, quick deployment, portable use

1. **Download** `DerivativeMill_Windows11_Portable.zip`
2. **Extract** the ZIP file to your desired location:
   - Program Files: `C:\Program Files\DerivativeMill\`
   - USB Drive: `E:\DerivativeMill\` (drive letter may vary)
   - Desktop: `C:\Users\YourUsername\Desktop\DerivativeMill\`
3. **Run** `DerivativeMill.exe` directly
4. *(Optional)* Double-click `INSTALL.bat` to create a desktop shortcut

**Advantages**:
- No installation wizard
- Works on any Windows system
- Can run from USB drive
- Easy to uninstall (just delete folder)

**Disadvantages**:
- No Start Menu entry by default
- No automatic updates

---

### Method 2: Batch File Installation

**Best for**: Corporate deployment, consistent setup

1. **Extract** the ZIP file to your desired location
2. **Right-click** `INSTALL.bat` → "Run as Administrator"
3. Follow the on-screen prompts
4. A desktop shortcut will be created automatically

**What INSTALL.bat does**:
- Creates desktop shortcut
- Sets up file associations
- Creates Start Menu entry

---

### Method 3: Manual Installation to Program Files

**Best for**: System-wide installation

1. **Extract** ZIP to `C:\Program Files\DerivativeMill\`
2. **Right-click** `DerivativeMill.exe` → "Create shortcut"
3. **Move shortcut** to Desktop or Start Menu

**Verify Installation**:
```
C:\Program Files\DerivativeMill\
├── DerivativeMill.exe
├── Input/
├── Output/
├── ProcessedPDFs/
├── README.md
├── QUICKSTART.md
└── SETUP.md
```

---

## First Launch

### Initial Setup

1. **Double-click** `DerivativeMill.exe` (or `Run_DerivativeMill.bat`)
2. Wait 10-30 seconds for the application to start
3. The application window should open with default settings

### First-Time Configuration

1. **Click Settings** (gear icon) in the top-right
2. **Appearance Tab**:
   - Select your preferred theme (Fusion Light/Dark recommended)
   - Adjust font size if needed
3. **Folders Tab**:
   - Verify folder locations are correct
   - Create folders if prompted
4. **Suppliers Tab**:
   - Add your supplier names (optional)
5. **Click OK** to save

---

## File Organization

The application creates these directories:

```
C:\Program Files\DerivativeMill\    (or wherever you installed it)
├── DerivativeMill.exe
├── Input/                           (Place invoice PDFs/CSVs here)
├── Output/                          (Processed files saved here)
├── ProcessedPDFs/                   (Archived PDFs)
└── Resources/
    └── derivativemill.db            (Application database)
```

**Important**: These folders contain your data. Back them up regularly!

---

## Using the Application

### Step-by-Step Workflow

1. **Prepare Files**:
   - Save invoice PDFs or CSVs to the `Input/` folder
   - Or use "Load File" button in the application

2. **Import Parts Database**:
   - Click "Parts Import" tab
   - Load your parts CSV file
   - Map columns as needed
   - Click "Import"

3. **Process Invoices**:
   - Click "Process Shipment" tab
   - Load an invoice file
   - Map columns if required
   - Click "Process Shipment"

4. **Check Results**:
   - Processed files appear in `Output/` folder
   - Check "Log View" tab for any errors

5. **Archive**:
   - Move processed PDFs to `ProcessedPDFs/` folder

---

## Troubleshooting

### Application Won't Start

**Problem**: "DerivativeMill.exe has stopped responding"

**Solutions**:
1. Wait longer (first launch can take 30 seconds)
2. Check Windows Defender isn't blocking it:
   - Settings → Privacy & Security → Virus & threat protection
   - Add DerivativeMill.exe to allowed apps
3. Try running as Administrator:
   - Right-click `DerivativeMill.exe` → "Run as Administrator"
4. Restart your computer

---

### File Permission Errors

**Problem**: "Permission denied" when saving files

**Solutions**:
1. Run as Administrator:
   - Right-click `DerivativeMill.exe` → "Run as Administrator"
2. Check folder permissions:
   - Right-click folder → Properties → Security
   - Ensure your user has "Modify" permission

---

### Slow Performance

**Problem**: Application runs slowly or freezes

**Solutions**:
1. Check available disk space:
   - Should have at least 500MB free
2. Close other applications:
   - Applications running multiple background processes
3. Move to local drive:
   - If on network drive, copy to local C:\
4. Check Log View:
   - Click "Log View" tab for error messages

---

### Database Errors

**Problem**: "Database is locked" or corruption errors

**Solutions**:
1. Delete the database and restart:
   - Navigate to `Resources/derivativemill.db`
   - Delete the file
   - Restart the application
2. Close all instances:
   - Ensure only one copy of DerivativeMill is running
3. Check antivirus:
   - Antivirus may be blocking database access
   - Add DerivativeMill.exe to antivirus whitelist

---

### Files Not Appearing in UI

**Problem**: Input files not visible in application

**Solutions**:
1. Verify file path:
   - Click Settings → Folders Tab
   - Confirm Input folder path is correct
2. Check file format:
   - Supported: PDF, CSV, XLSX
   - File must have .pdf, .csv, or .xlsx extension
3. Refresh application:
   - Close and reopen DerivativeMill.exe

---

## Uninstallation

### Method 1: Delete Folder (Portable)
```
1. Close DerivativeMill
2. Delete the DerivativeMill folder
3. Delete the desktop shortcut (if created)
```

### Method 2: Using Windows Settings
```
1. Settings → Apps → Apps & features
2. Search for "DerivativeMill"
3. Click → Uninstall
```

**Important**: Uninstalling deletes the application but NOT your data files in the Input/Output folders unless they're in the installation directory.

---

## Backing Up Your Data

### Backup Important Files

1. **Database**:
   - Location: `Resources/derivativemill.db`
   - Contains: Settings, column mappings, supplier info

2. **Input Files**:
   - Location: `Input/` folder
   - Contains: Original invoice files

3. **Output Files**:
   - Location: `Output/` folder
   - Contains: Processed results

### Backup Procedure

**Manual Backup**:
```
1. Close DerivativeMill
2. Copy entire DerivativeMill folder to external drive
3. Or copy individual folders to cloud storage
```

**Recommended Tools**:
- Windows Backup & Restore
- OneDrive / Google Drive / Dropbox
- External hard drive

---

## Updating to New Version

### From Portable ZIP

1. **Backup** your current `DerivativeMill/` folder:
   ```
   Copy C:\Program Files\DerivativeMill to C:\Program Files\DerivativeMill_Backup
   ```

2. **Download** new version ZIP

3. **Extract** new ZIP to same location (overwrite)

4. **Run** new version

Your data will be preserved because it's in the same folder.

---

## Getting Help

### Check Application Help

- **User Guide Tab**: Built-in help and documentation
- **Log View Tab**: Detailed error messages
- **Keyboard Shortcuts**: Press Ctrl+H in application

### Documentation Files

- `README.md` - Project overview
- `QUICKSTART.md` - 5-minute quick start
- `SETUP.md` - Detailed setup instructions
- `TESTING_CHECKLIST.md` - Testing procedures

### Common Questions

**Q: Can I use this on a USB drive?**
A: Yes! Just extract to a USB drive and run DerivativeMill.exe

**Q: Can multiple people use the same installation?**
A: Yes, but not simultaneously. Close the app before another person uses it.

**Q: Where is my data stored?**
A: In the `Input/`, `Output/`, and `ProcessedPDFs/` folders, plus the database in `Resources/`

**Q: Can I use this on older Windows versions?**
A: Yes, Windows 10 and newer are supported.

**Q: Does it require internet connection?**
A: No, it runs completely offline.

---

## Performance Tips

1. **Keep it fast**:
   - Use local drives instead of network drives
   - Keep Windows updated
   - Close unnecessary background applications

2. **Organize your files**:
   - Use supplier folders in Input/
   - Archive processed files regularly
   - Clean up ProcessedPDFs/ periodically

3. **Regular maintenance**:
   - Back up your data monthly
   - Keep the application folder on C: drive
   - Monitor available disk space

---

## Technical Support

If you encounter issues:

1. **Check Log View** in the application for error details
2. **Review SETUP.md** for platform-specific guidance
3. **Check Windows Defender** isn't blocking the application
4. **Restart** your computer
5. **Reinstall** the application (backup data first)

---

## System Information

To provide to support, collect:

```
1. Windows version: Settings → System → About
2. Python version: python --version
3. Application version: Help → About (if available)
4. Log View contents: Copy from Log View tab
5. Error message: Screenshot or text
```

---

## Next Steps

- **Read QUICKSTART.md** for 5-minute setup
- **Visit User Guide Tab** in application for tutorials
- **Configure Folders** in Settings for your workflow
- **Import your first invoice** to get started

---

**Version**: 1.08
**Last Updated**: December 2024
**Platform**: Windows 10 / Windows 11

