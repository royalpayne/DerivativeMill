# DerivativeMill - Quick Start Guide

Get DerivativeMill up and running in 5 minutes on any platform.

## Step 1: Install Python (if needed)

Check if Python 3.8+ is already installed:
```bash
python --version
# or
python3 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/) or use:
- **macOS**: `brew install python3`
- **Linux**: `sudo apt-get install python3`

## Step 2: Set Up Virtual Environment

Navigate to the application folder:
```bash
cd /path/to/DerivativeMill
```

Create and activate virtual environment:

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

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Wait for installation to complete (2-5 minutes).

## Step 4: Launch Application

```bash
python DerivativeMill/derivativemill.py
```

The application window should open in 10-30 seconds.

---

## Your First Invoice

1. **Prepare Your Data**:
   - Have an invoice PDF or CSV with invoice data ready

2. **Process Shipment Tab**:
   - Click "Load File" and select your invoice
   - Map columns if needed
   - Click "Process Shipment"

3. **View Results**:
   - Check the "Exported Files" section
   - Download the processed CSV

4. **Settings**:
   - Customize theme in settings gear icon
   - Configure folder locations
   - Set up your suppliers

---

## Common Tasks

### Adding a New Supplier
1. Click settings gear → Suppliers
2. Click "Add New Supplier"
3. Enter supplier name
4. Click OK

### Processing Multiple Files
1. Each file must be processed individually
2. Click "Load File" for each invoice
3. Results export to Output folder

### Customizing Theme
1. Click settings gear
2. Select preferred theme
3. Changes apply immediately

### Viewing Logs
1. Click "Log View" tab
2. Check for any errors or warnings
3. Use for troubleshooting

---

## Data Locations

Files are automatically organized in these folders (relative to application):
- `Input/` - Place supplier invoice folders here
- `Output/` - Processed data exports appear here
- `ProcessedPDFs/` - Archived PDF files
- `Resources/` - Database and application resources

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError" | Activate virtual environment: `source venv/bin/activate` |
| Application won't start | Check Python version is 3.8+: `python --version` |
| Can't find files | Check file locations in Settings → Folder Locations |
| Slow performance | Ensure sufficient disk space; avoid network drives |

---

## Next Steps

1. **Import Parts Database**:
   - Go to "Parts Import" tab
   - Load your parts CSV
   - Map required columns

2. **Create Mapping Profiles**:
   - Go to "Invoice Mapping Profiles" tab
   - Create profiles for your invoice formats

3. **Process Shipments**:
   - Use "Process Shipment" tab
   - Process each invoice one at a time

4. **Export & Archive**:
   - Check "Exported Files" for results
   - Move processed PDFs to archive

---

## Need Help?

- **Check Log View**: Contains detailed error messages
- **Settings Dialog**: Verify folder locations are correct
- **SETUP.md**: Detailed platform-specific instructions
- **User Guide Tab**: Built-in help documentation

---

**Ready to go!** 🚀

Start by loading your first invoice and processing it through the "Process Shipment" tab.
