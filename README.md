# DerivativeMill

**Professional Customs Documentation Processing System**

DerivativeMill is a desktop application for import/export businesses, customs brokers, and trade compliance professionals. It automates invoice processing, manages parts databases, and ensures compliance with Section 232 and Section 301 tariff requirements.

## Key Features

### Invoice Processing
- Process commercial invoices (CSV, XLSX formats)
- Generate CBP-compliant upload worksheets
- Automatic value distribution and calculations
- Preview and edit data before export
- Split exports by invoice number

### Parts Master Database
- Maintain comprehensive parts inventory with HTS codes
- Track country of origin, melt, cast, and smelt locations
- Store material ratios (steel, aluminum, copper, wood, automotive)
- Import parts from CSV files
- Advanced search and query builder

### Tariff Compliance
- **Section 232**: Automatic tracking of steel, aluminum, copper, wood, and automotive tariffs
- **Section 301**: Identify products with exclusion tariffs
- Color-coded indicators for quick identification
- Material classification with customizable colors

### Flexible Configuration
- Save and reuse invoice mapping profiles for different suppliers
- Customizable output column mapping
- Export profiles for different broker requirements
- Theme support (Light/Dark modes)

## Screenshots

The application features:
- Modern tabbed interface
- Real-time preview table with color-coded rows
- Configurable input/output directories
- Integrated MID (Manufacturer ID) management

## System Requirements

- **OS**: Windows 10 or Windows 11
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 200MB free space
- **Display**: 1280x720 minimum (1920x1080 recommended)

## Installation

### Windows Executable (Recommended)

Download the latest `DerivativeMill.exe` from the [Releases](https://github.com/royalpayne/DerivativeMill/releases) page.

No installation required - just run the executable.

#### Windows SmartScreen Warning

On first run, Windows may show a "Windows protected your PC" warning because the application is not yet widely distributed. This is normal for new software.

**To run the application:**
1. Click **"More info"** on the warning dialog
2. Click **"Run anyway"**

The application is safe to use. This warning will decrease as more users download and run the software.

### From Source

1. **Clone the repository:**
```bash
git clone https://github.com/royalpayne/DerivativeMill.git
cd DerivativeMill
```

2. **Create virtual environment:**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python DerivativeMill/derivativemill.py
```

## Usage

### Basic Workflow

1. **Configure Input/Output Folders** - Settings menu to set your working directories
2. **Load Invoice** - Select a CSV or XLSX invoice file
3. **Map Columns** - Create or select a mapping profile for the invoice format
4. **Enter Values** - Set commercial invoice total and select MID
5. **Process** - Click "Process Invoice" to generate the preview
6. **Review** - Check the preview table, edit values if needed
7. **Export** - Click "Export Worksheet" to generate the final file

### Parts Database

- **Import**: Use the Parts Import dialog to bulk import from CSV
- **Search**: Quick search or use the Query Builder for advanced searches
- **Edit**: Double-click cells in the Parts Master tab to edit
- **HTS Lookup**: Automatic CBP quantity unit lookup for HTS codes

### Output Mapping

Customize which columns appear in your export:
1. Go to Configuration → Output Mapping tab
2. Drag columns to reorder
3. Check/uncheck columns to include/exclude
4. Save as a profile for reuse

## File Structure

```
DerivativeMill/
├── derivativemill.py     # Main application
├── version.py            # Version management
├── Resources/
│   ├── derivativemill.db # SQLite database
│   └── icon.ico          # Application icon
├── Input/                # Invoice files to process
│   └── Processed/        # Archived processed files
└── Output/               # Generated export files
    └── Processed/        # Archived exports
```

## Configuration

Settings are stored in:
- **Database**: `Resources/derivativemill.db` (shared settings, parts data)
- **Registry**: Windows Registry (per-user preferences like theme, colors)

### Customizable Options

- Input/Output directory locations
- Preview table row colors (per material type)
- Font size and theme
- Column visibility
- Auto-refresh interval
- Excel viewer application

## Technology Stack

- **PyQt5**: Desktop GUI framework
- **Pandas**: Data processing
- **SQLite**: Local database
- **OpenPyXL**: Excel file handling

## Version

**Current Version**: v0.90.2

Version is automatically derived from git tags. See [version.py](DerivativeMill/version.py) for details.

## Recent Changes

### v0.90.2
- Add landscape page setup for exported Excel files
- Add reprocess button for re-processing after database changes
- Fix merge strategy to prefer database values over invoice values
- Add animated spinner to splash screen
- Add license system framework (disabled, for future use)

### v0.90.1
- Export profiles and output column mapping
- Section 301 exclusion tariff tracking
- Theme-specific color settings
- UI improvements and bug fixes

### v0.90.0
- Major refactoring and modernization
- Improved Parts Master management
- Query builder for advanced searches
- Multiple invoice mapping profiles

## Support

- **Issues**: [GitHub Issues](https://github.com/royalpayne/DerivativeMill/issues)
- **Documentation**: See this README and in-app help

## License

Proprietary software. See LICENSE file for details.

---

**Ready to streamline your customs documentation?** Download the latest release and get started!
