# TariffMill

**Professional Customs Documentation Processing System**

TariffMill is a desktop application for import/export businesses, customs brokers, and trade compliance professionals. It automates invoice processing, manages parts databases, and ensures compliance with Section 232 and Section 301 tariff requirements.

## Key Features

### Invoice Processing
- Process commercial invoices (CSV, XLSX formats)
- Generate CBP-compliant upload worksheets
- Automatic value distribution and calculations
- Preview and edit data before export
- Split exports by invoice number

### PDF Processing - Invoice OCR
- AI-powered PDF invoice text extraction using Anthropic Claude
- Customizable template system for different invoice formats
- Automatic field mapping and data extraction
- Dynamic template discovery and hot-reload

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

### HTS Database Reference
- Built-in searchable HTS database
- Quick lookup of tariff codes and descriptions
- Quantity unit information for CBP compliance

### Flexible Configuration
- Save and reuse invoice mapping profiles for different suppliers
- Customizable output column mapping
- Export profiles for different broker requirements
- Multiple theme options (Light, Dark, Ocean, Muted Cyan, macOS)
- Configurable backup schedules with time selection

### Usage Statistics
- Track processing metrics by entry writer
- Monitor usage by client
- View historical processing data

## Data Flow

[![TariffMill Data Flow](marketing/data_flow_diagram_static.svg)](https://htmlpreview.github.io/?https://raw.githubusercontent.com/ProcessLogicLabs/TariffMill/main/marketing/TariffMill_Presentation.html)

*Click the diagram to view the full interactive presentation*

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

### Windows Installer (Recommended)

Download `TariffMill_Setup_x.xx.xx.exe` from the [Releases](https://github.com/ProcessLogicLabs/TariffMill/releases) page and run the installer.

### Windows Portable Executable

Download `TariffMill.exe` from the [Releases](https://github.com/ProcessLogicLabs/TariffMill/releases) page. No installation required - just run the executable.

#### Windows SmartScreen Warning

On first run, Windows may show a "Windows protected your PC" warning because the application is not yet widely distributed. This is normal for new software.

**To run the application:**
1. Click **"More info"** on the warning dialog
2. Click **"Run anyway"**

The application is safe to use. This warning will decrease as more users download and run the software.

### Linux/macOS (pip install)

Install directly from GitHub:
```bash
pip install git+https://github.com/ProcessLogicLabs/TariffMill.git
```

Then run:
```bash
tariffmill
```

### From Source

1. **Clone the repository:**
```bash
git clone https://github.com/ProcessLogicLabs/TariffMill.git
cd TariffMill
```

2. **Create virtual environment:**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python Tariffmill/tariffmill.py
```

## Usage

### Basic Workflow

1. **Configure Input/Output Folders** - Use Preferences menu to set your working directories
2. **Load Invoice** - Select a CSV or XLSX invoice file
3. **Map Columns** - Create or select a mapping profile for the invoice format
4. **Enter Values** - Set commercial invoice total and select MID
5. **Process** - Click "Process Invoice" to generate the preview
6. **Review** - Check the preview table, edit values if needed
7. **Export** - Click "Export Worksheet" to generate the final file

### Parts Database

- **Import**: Use the Parts Import dialog to bulk import from CSV
- **Search**: Quick search or use the Query Builder for advanced searches
- **Edit**: Double-click cells in the Parts View tab to edit
- **HTS Lookup**: Automatic CBP quantity unit lookup for HTS codes

### Output Mapping

Customize which columns appear in your export:
1. Go to Profiles → Output Mapping tab
2. Drag columns to reorder
3. Check/uncheck columns to include/exclude
4. Save as a profile for reuse

## File Structure

```
Tariffmill/
├── tariffmill.py         # Main application
├── version.py            # Version management
├── Resources/
│   ├── tariffmill.db     # SQLite database
│   └── icon.ico          # Application icon
├── Input/                # Invoice files to process
│   └── Processed/        # Archived processed files
└── Output/               # Generated export files
    └── Processed/        # Archived exports
```

## Configuration

Settings are stored in:
- **Database**: `Resources/tariffmill.db` (shared settings, parts data)
- **Registry**: Windows Registry (per-user preferences like theme, colors)

### Customizable Options

- Input/Output directory locations
- Preview table row colors (per material type)
- Font size and theme (Light, Dark, Ocean, Muted Cyan, macOS)
- Column visibility
- Auto-refresh interval
- Excel viewer application
- Backup schedule time

## Technology Stack

- **Python 3.12**: Core language
- **PyQt5**: Desktop GUI framework
- **Pandas**: Data processing
- **SQLite**: Local database
- **OpenPyXL**: Excel file handling
- **pdfminer**: PDF text extraction
- **Anthropic Claude**: AI-powered template generation
- **PyInstaller**: Executable packaging
- **Inno Setup**: Windows installer

## Version

**Current Version**: v0.97.24

Version is automatically derived from git tags. See [version.py](Tariffmill/version.py) for details.

## Recent Changes

### v0.97.24
- **Muted Cyan Theme**: Updated color palette to be more blue-toned for better appearance on Windows 11

### v0.97.23
- **pip Installation**: Added support for installing via pip directly from GitHub for Linux/Ubuntu users
- **UI Improvements**: Various interface refinements

### v0.97.22
- **Muted Cyan Theme**: Added new professional blue-cyan theme option
- **UI Cleanup**: Removed Format Code button, streamlined interface

### v0.97.21
- **Shared Templates**: Added debug logging for template discovery
- **Template Fixes**: Restored template functionality

### v0.96
- **Tab Reorganization**: Renamed tabs to Invoice Processing, PDF Processing, and Parts View
- **Removed Parts History**: Streamlined PDF Processing by removing unused Parts History tab
- **Documentation Update**: Updated all flowcharts and documentation to reflect current workflow

### v0.94.0
- **PDF Processing Integration**: AI-powered invoice OCR processing with template system
- **Copyright Protection**: Added proprietary license and copyright notices
- **Dark Theme Improvements**: Enhanced dark theme styling consistency
- **Result Preview Enhancements**: Improved column layout and value rounding fixes
- **Material Percentage Row Splitting**: Fixed value rounding errors in split calculations

## Support

- **Issues**: [GitHub Issues](https://github.com/ProcessLogicLabs/TariffMill/issues)
- **Documentation**: See this README and in-app help

## License

Proprietary software. See LICENSE file for details.

---

**Ready to streamline your customs documentation?** Download the latest release and get started!
