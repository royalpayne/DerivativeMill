# Derivative Mill

**Version 1.08** - Section 232 Compliant

A comprehensive customs compliance application for processing shipment data and managing Section 232 tariff classifications.

## Features

### 1. Process Shipment
- Load CSV files from invoice data
- Apply custom mapping profiles to extract shipment details
- Validate invoice values (CI Value, Net Weight, MID)
- Automatic Section 232 tariff classification
- Generate Excel export files with detailed tariff breakdowns
- Real-time preview of processed parts

### 2. Invoice Mapping Profiles
- Create and manage reusable mapping profiles for different invoice formats
- Visual CSV column mapping interface
- Save, load, and delete custom profiles
- Profile-specific field mapping for Product No, Value, HTS, MID, Weight, etc.

### 3. Parts Import
- Import parts data from CSV/Excel files
- Bulk update parts master database
- Column mapping interface for flexible data sources
- Validation and duplicate detection

### 4. Parts View
- Search and view all parts in the master database
- Filter by Product No, HTS, MID, Weight, Declaration
- SQL query interface for advanced searches
- Export query results to CSV

### 5. Log View
- Real-time application logging
- Filter by log level (DEBUG, INFO, WARNING, ERROR)
- Search log entries
- Export logs to file

### 6. Customs Configuration
- **Section 232 Tariff List**: Manage HTS codes with Section 232 classifications
  - Filter by material type (Steel, Aluminum, Wood, Copper)
  - Color-coded rows by material (toggle on/off)
  - Import tariff data from CSV/Excel
  - Search by HTS code, classification, or chapter
- Custom declaration templates

### 7. Section 232 Actions
- **Chapter 99 Tariff Actions**: View and manage Section 232 tariff modifications
  - Filter by commodity type
  - Color-coded rows by material (toggle on/off)
  - Track effective and expiration dates
  - Import actions from CSV
  - Automatic expiration highlighting

### 8. User Guide
- Built-in documentation
- Feature explanations
- Usage instructions

## Themes

Six built-in themes with persistent preferences:
- System Default
- Fusion (Light)
- Windows
- Fusion (Dark)
- Ocean
- Teal Professional

Theme-aware UI elements:
- Status bars adapt to light/dark themes
- File display fields match theme palette
- Dynamic color schemes for better visibility

## Performance Features

- **Network Path Optimization**: Automatically detects network paths and uses temp-file strategy for 40x faster exports
- **Export Progress Indicator**: Real-time progress bar for export operations
- **Deferred Loading**: Non-blocking startup with background file list refresh
- **Auto-refresh**: Configurable automatic input file monitoring
- **Automatic File Cleanup**: Moves exported files older than 3 days to Output/Processed directory
- **Housekeeping on Startup**: Shows progress indicator during file maintenance operations

## Database

SQLite database (`derivativemill.db`) stores:
- Parts master data
- Section 232 tariff classifications
- Section 232 actions (Chapter 99)
- Mapping profiles
- Application configuration
- Theme preferences

## Requirements

- Python 3.8+
- PyQt5
- pandas
- openpyxl
- sqlite3
- loguru

## Configuration

Settings accessible via Settings button:
- Input folder path
- Output folder path
- Theme selection
- Auto-refresh intervals

## Status Bars

- **Top Status Bar**: Displays urgent alerts and warnings
- **Bottom Status Bar**: Shows routine status updates and export progress

## Export Features

- Generates formatted Excel files with:
  - Section 232 tariff breakdowns
  - Chapter 99 action details
  - Material classifications
  - Percentage calculations
  - Compliance declarations
- Automatic file naming with timestamps
- Move processed CSV files to Processed folder
- Network-optimized export strategy

## Material Color Coding

When enabled, rows are color-coded by material type:
- **Steel**: Light blue (#e3f2fd)
- **Aluminum**: Light orange (#fff3e0)
- **Wood**: Light green (#f1f8e9)
- **Copper**: Light bronze (#ffe0b2)

Toggle available on both Section 232 Tariff List and Section 232 Actions tabs.

## File Management

- **Input Files**: Processed CSV files automatically moved to Input/Processed folder after export
- **Output Files**: Exported Excel files older than 3 days automatically moved to Output/Processed folder
- **Cleanup Schedule**: Runs on startup and every 30 minutes during operation
- **Smart Detection**: Only moves files when conditions are met, maintains file integrity

## Text Visibility

- **Derivative Rows**: Display in medium charcoal gray (#4a4a4a) for optimal visibility on both light and dark themes
- **Non-232 Rows**: Display in red for easy identification
- **Theme-Aware Components**: File labels, status bars, and UI elements adapt to selected theme

## License

Proprietary - All rights reserved

## Author

Houston Payne
