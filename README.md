# DerivativeMill

**Derivative Tariff Compliance and Invoice Processing System**

DerivativeMill is a professional-grade application for processing customs invoices, managing parts databases, and ensuring Section 232 tariff compliance. It's designed for customs brokers, supply chain professionals, and enterprises managing complex tariff requirements.

## Features

- **Invoice Processing**: Automated extraction and processing of invoice data (PDF, CSV, XLSX)
- **Parts Database Management**: Import, search, and manage parts with HTS codes and tariff information
- **Tariff Compliance**: Integrated Section 232 tariff database for derivative content classification
- **Customizable Mapping**: Create and save invoice mapping profiles for different suppliers
- **Professional Reporting**: Export compliant CSV reports for customs documentation
- **Cross-Platform**: Runs on Windows, macOS, and Linux
- **No OCR Required**: Focuses on structured data extraction from tables

## Quick Start

### Windows 11 Users

**For Windows 11 installation, see [DerivativeMill_Win11_Install/README.md](DerivativeMill_Win11_Install/README.md)**

The Windows installer package includes:
- Automated build scripts (batch and PowerShell)
- Portable standalone executable
- Professional installer
- Complete installation documentation

### Minimum Requirements
- Python 3.8 or higher
- 4GB RAM, 500MB disk space

### Installation (5 minutes)

**1. Clone or download the application:**
```bash
cd /path/to/DerivativeMill
```

**2. Create virtual environment:**
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate.bat

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run the application:**
```bash
python DerivativeMill/derivativemill.py
```

See [QUICKSTART.md](QUICKSTART.md) for more details.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[SETUP.md](SETUP.md)** - Detailed platform-specific setup instructions
- **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - Quality assurance and testing guide

## Supported Platforms

| Platform | Version | Status |
|----------|---------|--------|
| Windows | 10, 11 | ✓ Fully Supported |
| macOS | 10.13+ | ✓ Fully Supported |
| Linux | Most distributions | ✓ Fully Supported |

## Key Capabilities

### Invoice Processing
- Load PDF, CSV, or Excel invoices
- Extract and validate data automatically
- Map invoice columns to standard fields
- Preview and edit extracted data before processing

### Parts Management
- Import parts database from CSV
- Search parts by number, HTS code, or description
- View derivative content ratios
- Track Section 232 classification

### Tariff Compliance
- Integrated HTS code lookup
- Section 232 derivative content database
- Material classification system
- Compliance documentation export

### Data Organization
- Supplier folder management
- Automatic file archiving
- Version-controlled exports
- Audit trail via Log View

## Architecture

```
DerivativeMill/
├── derivativemill.py      (Main application)
├── platform_utils.py      (Cross-platform utilities)
├── Resources/
│   ├── derivativemill.db  (SQLite database)
│   └── [...icons, data...]
├── Input/                 (Supplier invoice folders)
├── Output/                (Processed exports)
└── ProcessedPDFs/         (Archived files)
```

## Technology Stack

- **PyQt5**: Cross-platform desktop GUI
- **Pandas**: Data manipulation and analysis
- **pdfplumber**: PDF table extraction
- **SQLite3**: Local database
- **OpenPyXL**: Excel file handling
- **Pillow**: Image processing

## Installation Methods

### From Source
```bash
python DerivativeMill/derivativemill.py
```

### As Package
```bash
pip install -e .
derivativemill
```

### As Executable (Optional)
```bash
pip install PyInstaller
pyinstaller --onefile DerivativeMill/derivativemill.py
```

## Configuration

All settings are stored in a local SQLite database:
- Theme preferences
- Folder locations
- Column mappings
- Supplier configurations
- User preferences

Settings are automatically loaded on startup and saved when changed.

## Data Storage

### Windows
- Data: `%APPDATA%\DerivativeMill\`
- Application files: `.\Resources\`

### macOS
- Data: `~/Library/Application Support/DerivativeMill/`
- Cache: `~/Library/Caches/DerivativeMill/`

### Linux
- Data: `~/.local/share/DerivativeMill/` (XDG compliant)
- Config: `~/.config/DerivativeMill/`
- Cache: `~/.cache/DerivativeMill/`

## Troubleshooting

### Application won't start
1. Verify Python 3.8+: `python --version`
2. Activate virtual environment
3. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
4. Check Log View tab for errors

### File operations fail
1. Verify folder permissions (Settings → Folder Locations)
2. Check disk space (500MB+ required)
3. Avoid network drives for best performance

### Database issues
- Database is automatically backed up before updates
- Check Log View for database errors
- Delete `Resources/derivativemill.db` to reset (will lose settings)

See [SETUP.md](SETUP.md) for comprehensive troubleshooting.

## Performance

| Operation | Time |
|-----------|------|
| Startup | 5-15 seconds |
| Loading 5000-row CSV | 2-5 seconds |
| Processing invoice | 1-3 seconds |
| Exporting data | 2-5 seconds |

Performance depends on:
- File size
- System RAM and CPU
- Disk speed (local drives faster than network)

## System Specifications

**Minimum**:
- Python 3.8
- 4GB RAM
- 500MB disk space
- 1280x720 display

**Recommended**:
- Python 3.10+
- 8GB+ RAM
- SSD with 1GB+ free space
- 1920x1080+ display

## Compliance

- Section 232 tariff rules (August 18, 2025)
- HTS code classification
- Customs documentation standards
- Data validation and error checking

## Development

### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
```

### Install Development Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
See [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) for comprehensive testing.

### Build Executable
```bash
pip install PyInstaller
pyinstaller --onefile --windowed DerivativeMill/derivativemill.py
```

## Version

**Current Version**: v1.08

**Release Date**: December 2024

**Compatibility**: Python 3.8+, All major platforms

## License

See LICENSE file for details.

## Support

- **Documentation**: [SETUP.md](SETUP.md), [QUICKSTART.md](QUICKSTART.md)
- **Issues**: Check Log View tab for application errors
- **Testing**: Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)

## Contributing

For improvements or bug reports:
1. Test thoroughly using TESTING_CHECKLIST.md
2. Document platform-specific issues
3. Include version and platform information

## Changelog

### v1.08
- Removed OCR functionality
- Removed batch processing
- Cross-platform compatibility improvements
- Enhanced documentation
- Standardized file path handling
- Added platform utilities module
- Improved Linux XDG compliance

### v1.07 and earlier
See git history for details.

---

**Ready to process your first invoice?** Start with [QUICKSTART.md](QUICKSTART.md)!
