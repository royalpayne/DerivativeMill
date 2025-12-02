# DerivativeMill - Complete Documentation Index

Welcome to DerivativeMill! This document serves as your starting point for understanding the application structure, setup, and usage.

## Quick Navigation

### For First-Time Users
1. **Start here**: [README.md](README.md) - Project overview
2. **Get running**: [QUICKSTART.md](QUICKSTART.md) - 5-minute setup
3. **Detailed setup**: [SETUP.md](SETUP.md) - Platform-specific instructions
4. **Need help?**: Scroll to Support section below

### For Developers
1. **Code structure**: [README.md](README.md#architecture) - Application architecture
2. **Platform utils**: [platform_utils.py](DerivativeMill/platform_utils.py) - Cross-platform utilities
3. **Package setup**: [setup.py](setup.py) - Installation configuration
4. **Testing**: [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) - Quality assurance

### For QA/Testing
1. **Test checklist**: [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) - Comprehensive validation
2. **All platforms**: Windows, macOS, Linux test procedures included
3. **Performance**: Benchmarking guidelines included
4. **Sign-off**: Document template for release approval

### For Deployment
1. **Setup instructions**: [SETUP.md](SETUP.md#building-executable-bundles) - Build executables
2. **Dependencies**: [requirements.txt](requirements.txt) - All required packages
3. **Distribution**: Multiple installation methods documented
4. **Version control**: [.gitignore](.gitignore) - Proper exclusions

---

## Document Structure

### Documentation Files

**[README.md](README.md)** (6.8 KB)
- Project overview and features
- Quick start instructions
- Technology stack
- System requirements
- Troubleshooting guide
- **Read this first for overall understanding**

**[QUICKSTART.md](QUICKSTART.md)** (3.7 KB)
- 5-minute setup on any platform
- Step-by-step installation
- First invoice processing
- Quick reference table
- **Read this to get up and running fast**

**[SETUP.md](SETUP.md)** (6.9 KB)
- Detailed platform-specific setup
- Windows 10/11 instructions
- macOS 10.13+ instructions  
- Linux setup (Ubuntu, Fedora, Arch)
- Building executables (PyInstaller)
- Troubleshooting for each platform
- **Read this for comprehensive setup details**

**[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** (6.6 KB)
- Installation verification procedures
- Feature testing matrix
- File operations validation
- Database testing
- Performance benchmarks
- Quality assurance sign-off
- **Use this for testing and QA**

### Code Files

**[DerivativeMill/derivativemill.py](DerivativeMill/derivativemill.py)** (Main Application)
- Core application (6000+ lines)
- PyQt5-based GUI
- PDF, CSV, Excel processing
- Tariff database integration
- All major features
- **The main application file**

**[DerivativeMill/platform_utils.py](DerivativeMill/platform_utils.py)** (Platform Utilities)
- Cross-platform file operations
- Platform detection
- Directory management (XDG compliant)
- Native file/folder opening
- **New utility module for cross-platform support**

### Configuration Files

**[setup.py](setup.py)** (2.2 KB)
- Python package installer
- Entry point configuration
- Package metadata
- **Enables: pip install -e .**

**[requirements.txt](requirements.txt)** (342 B)
- All Python dependencies
- Version specifications
- Platform-specific packages
- **Install with: pip install -r requirements.txt**

**[.gitignore](.gitignore)** (888 B)
- Version control exclusions
- Virtual environment directories
- Generated files
- User data
- **Proper repository hygiene**

---

## Installation Quick Links

### For Windows
```bash
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
python DerivativeMill/derivativemill.py
```
→ Full details: [SETUP.md#windows](SETUP.md#windows)

### For macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python DerivativeMill/derivativemill.py
```
→ Full details: [SETUP.md#macos](SETUP.md#macos)

### For Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python DerivativeMill/derivativemill.py
```
→ Full details: [SETUP.md#linux](SETUP.md#linux)

---

## File Organization

```
Project_mv/
├── README.md                  ← Start here
├── INDEX.md                   ← You are here
├── QUICKSTART.md              ← 5-min setup
├── SETUP.md                   ← Detailed setup
├── TESTING_CHECKLIST.md       ← QA guide
│
├── DerivativeMill/
│   ├── derivativemill.py      ← Main app
│   ├── platform_utils.py      ← Cross-platform utilities
│   └── Resources/
│       └── derivativemill.db  ← SQLite database
│
├── Input/                     ← User invoice folders
├── Output/                    ← Processed exports
├── ProcessedPDFs/             ← Archived files
│
├── setup.py                   ← Package installer
├── requirements.txt           ← Dependencies
├── .gitignore                 ← Git exclusions
└── run.sh                     ← Quick launch script
```

---

## Common Tasks

### Get Started Immediately
1. Read [README.md](README.md) (2 min)
2. Follow [QUICKSTART.md](QUICKSTART.md) (5 min)
3. Process your first invoice (5 min)

### Detailed Platform Setup
→ See [SETUP.md](SETUP.md) for your operating system

### Build Executable
→ See [SETUP.md#building-executable-bundles](SETUP.md#building-executable-bundles)

### Test on Your Platform
1. Follow [SETUP.md](SETUP.md) for installation
2. Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) for validation
3. Document results and sign-off

### Deploy to Users
1. Test using [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
2. Create installers (Windows MSI, macOS DMG, Linux AppImage)
3. Follow distribution instructions in [SETUP.md](SETUP.md)

---

## Platform Support

| Platform | Version | Support Status |
|----------|---------|-----------------|
| Windows | 10, 11 | ✓ Fully Supported |
| macOS | 10.13+ | ✓ Fully Supported |
| Linux | Most distributions | ✓ Fully Supported |

Each platform has dedicated setup instructions in [SETUP.md](SETUP.md).

---

## Key Features

- **Multi-Format Support**: PDF, CSV, Excel invoice processing
- **Tariff Database**: Integrated Section 232 compliance
- **Parts Management**: Import and manage parts catalog
- **Professional Reporting**: Export-ready CSV format
- **Cross-Platform**: Windows, macOS, Linux
- **No OCR Required**: Works with structured data tables
- **Local Processing**: All data stays on your computer

---

## Technology Stack

- **Python** 3.8+ - Core language
- **PyQt5** - Desktop application framework
- **pandas** - Data processing
- **pdfplumber** - PDF extraction
- **SQLite3** - Local database
- **openpyxl** - Excel support
- **Pillow** - Image processing

All dependencies are cross-platform compatible.

---

## Support & Help

### Getting Help
1. **Basic questions**: Check [QUICKSTART.md](QUICKSTART.md)
2. **Setup issues**: See [SETUP.md](SETUP.md#troubleshooting)
3. **Feature help**: Use built-in User Guide tab
4. **Errors**: Check Log View tab in application
5. **Testing**: Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)

### Troubleshooting Flowchart
```
Problem
├─ Won't start
│  └─ Check [SETUP.md#troubleshooting](SETUP.md#troubleshooting)
├─ File operations fail
│  └─ Check file permissions & disk space
├─ Processing errors
│  └─ Check Log View tab
└─ Performance issues
   └─ Check system resources
```

---

## What You Can Do With DerivativeMill

### Process Invoices
1. Load PDF, CSV, or Excel file
2. Map columns to invoice fields
3. Extract and validate data
4. Export as CSV for further processing

### Manage Parts Database
1. Import parts from CSV
2. Search by part number or HTS code
3. View tariff classification
4. Track derivative content

### Ensure Compliance
1. Check Section 232 requirements
2. Validate HTS codes
3. Confirm derivative content
4. Generate compliant documentation

---

## Version Information

- **Current Version**: 1.08
- **Released**: December 2024
- **Python Support**: 3.8, 3.9, 3.10, 3.11+
- **Platform Support**: Windows 10+, macOS 10.13+, Linux

---

## Next Steps

**New User?**
1. → [README.md](README.md) (overview)
2. → [QUICKSTART.md](QUICKSTART.md) (get running)
3. → Start processing invoices!

**Developer?**
1. → Read [README.md#architecture](README.md#architecture)
2. → Review [platform_utils.py](DerivativeMill/platform_utils.py)
3. → Check [setup.py](setup.py) configuration

**QA/Testing?**
1. → Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
2. → Test on your platform
3. → Document and sign off

**Ready to Deploy?**
1. → Test with [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
2. → Create installers (see [SETUP.md](SETUP.md))
3. → Distribute to users

---

## Document Last Updated

- **Date**: December 2024
- **Version**: 1.08
- **For**: Cross-platform distribution

---

**Happy invoicing! 🚀**

For immediate help, start with [QUICKSTART.md](QUICKSTART.md).
