# Cross-Platform Testing Checklist

Use this checklist to verify DerivativeMill functionality across Windows, macOS, and Linux.

## Installation Testing

### Windows
- [ ] Python 3.8+ installed correctly
- [ ] Virtual environment created: `python -m venv venv`
- [ ] Virtual environment activated: `.\venv\Scripts\activate.bat`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Application starts: `python DerivativeMill/derivativemill.py`
- [ ] No errors in console

### macOS
- [ ] Python 3.8+ installed (check: `python3 --version`)
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Application starts: `python DerivativeMill/derivativemill.py`
- [ ] No security warnings on first launch

### Linux
- [ ] Python 3.8+ installed (check: `python3 --version`)
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Application starts: `python DerivativeMill/derivativemill.py`
- [ ] Required libraries available (PyQt5, etc.)

---

## File Operations Testing

### Path Handling (All Platforms)
- [ ] Application creates required directories automatically
- [ ] Input folder accessible and writable
- [ ] Output folder accessible and writable
- [ ] ProcessedPDFs folder accessible and writable
- [ ] Resources folder contains database

### File Opening (All Platforms)
- [ ] Can open CSV files with "Edit" button
- [ ] Files open in system default application
- [ ] File changes reload correctly

### File Explorer Integration
**Windows**:
- [ ] Opening supplier folder works
- [ ] Explorer window shows correct folder
- [ ] Files visible in explorer

**macOS**:
- [ ] Opening supplier folder works
- [ ] Finder window shows correct folder
- [ ] Files visible in finder

**Linux**:
- [ ] Opening supplier folder works
- [ ] File manager opens correct folder
- [ ] Files visible in file manager

---

## UI/Theme Testing (All Platforms)

### Theme Selection
- [ ] "System Default" theme available
- [ ] "Fusion (Light)" theme available
- [ ] "Fusion (Dark)" theme available
- [ ] Switching themes works without restart
- [ ] All windows readable in each theme

### Windows-Specific Themes
**Windows Only**:
- [ ] "Windows" theme available
- [ ] "Windows" theme applies correctly
- [ ] Native Windows appearance works

**Linux Only**:
- [ ] Excel viewer dropdown available
- [ ] "System Default" option works
- [ ] "Gnumeric" option selectable (if installed)

---

## Data Processing Testing

### PDF Processing
- [ ] Load PDF file
- [ ] Table extraction works
- [ ] Data appears in grid
- [ ] Can edit extracted values
- [ ] Can export as CSV

### CSV Processing
- [ ] Load CSV file
- [ ] Columns visible in grid
- [ ] Can map columns correctly
- [ ] Can save mapping
- [ ] Mapping persists on reload

### Excel Processing
- [ ] Load XLSX file (if available)
- [ ] Data displays correctly
- [ ] Export to CSV works
- [ ] File format preserved

---

## Database Testing (All Platforms)

### Database Operations
- [ ] Database file created on startup
- [ ] Settings saved correctly
- [ ] Settings persist after restart
- [ ] Theme preference saved
- [ ] Column mappings saved
- [ ] No database corruption errors

### Database Location
**Windows**:
- [ ] `Resources/derivativemill.db` exists

**macOS**:
- [ ] `Resources/derivativemill.db` exists

**Linux**:
- [ ] `Resources/derivativemill.db` exists

---

## Settings Dialog Testing

### Appearance Tab
- [ ] Theme dropdown works
- [ ] Font size selector works
- [ ] Changes apply immediately
- [ ] Settings persist

### Folders Tab
- [ ] Can view current folder locations
- [ ] Can change Input folder
- [ ] Can change Output folder
- [ ] Can change ProcessedPDFs folder
- [ ] Folders created if missing

### Suppliers Tab
- [ ] Suppliers list displays
- [ ] Can add new supplier
- [ ] Can remove supplier
- [ ] Can open supplier folder
- [ ] Supplier changes reflect in main UI

---

## Export/Import Testing

### Parts Import
- [ ] Can load CSV parts file
- [ ] Column mapping dialog works
- [ ] Can drag columns to match
- [ ] Import saves configuration
- [ ] Parts display in grid

### Invoice Processing
- [ ] Can load invoice file
- [ ] Can map invoice columns
- [ ] Processing completes
- [ ] CSV exports correctly
- [ ] Exported file readable

---

## Log View Testing

### Logging
- [ ] Log View tab shows messages
- [ ] Info messages appear
- [ ] Warning messages appear
- [ ] Error messages appear clearly
- [ ] Log persists during session
- [ ] Can clear log

---

## Performance Testing

### Memory Usage
- [ ] Initial startup: < 200MB RAM
- [ ] Processing large file: < 500MB RAM
- [ ] No memory leaks on repeated use
- [ ] Application responsive during processing

### File Operations
- [ ] Opening files: < 2 seconds
- [ ] Processing files: Depends on size
- [ ] Exporting: < 5 seconds
- [ ] No freezing on file operations

---

## Error Handling Testing

### Invalid Inputs
- [ ] Loading non-existent file shows error
- [ ] Loading corrupted file shows error
- [ ] Invalid column mapping shows warning
- [ ] Database errors logged

### Recovery
- [ ] Application doesn't crash on errors
- [ ] Can continue after error
- [ ] Error messages are helpful
- [ ] Can retry failed operations

---

## Final Checks (All Platforms)

- [ ] No console warnings on startup
- [ ] No exceptions in Log View
- [ ] All tabs accessible
- [ ] Settings persist after restart
- [ ] Application closes cleanly
- [ ] No temporary files left behind
- [ ] Database integrity maintained

---

## Test Results Summary

| Platform | Version | Status | Notes |
|----------|---------|--------|-------|
| Windows  | 10/11   | ✓/✗   | |
| macOS    | 12+     | ✓/✗   | |
| Linux    | Ubuntu  | ✓/✗   | |
| Linux    | Fedora  | ✓/✗   | |

---

## Known Issues & Workarounds

Document any platform-specific issues found:

1. **Issue**:
   - **Platforms Affected**:
   - **Workaround**:

2. **Issue**:
   - **Platforms Affected**:
   - **Workaround**:

---

## Sign-Off

- **Tested By**: ___________________
- **Date**: ___________________
- **Overall Status**: ✓ Pass / ✗ Fail
- **Ready for Release**: ✓ Yes / ✗ No

**Notes**:

---

*Use this checklist before releasing new versions to ensure quality across all supported platforms.*
