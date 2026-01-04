# Changelog

All notable changes to TariffMill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.97.24] - 2026-01-04

### Changed
- Updated Muted Cyan theme color palette to be more blue-toned for better appearance on Windows 11
- Shifted primary accent from green-cyan (#4a7880) to blue-cyan (#4a7088)

## [0.97.23] - 2026-01-03

### Added
- pip installation support for Linux/Ubuntu users via direct GitHub install
- pyproject.toml for package distribution
- Entry point for running as `tariffmill` command after pip install

### Changed
- Various UI improvements and refinements

## [0.97.22] - 2026-01-02

### Added
- New Muted Cyan theme option - professional blue-cyan color scheme

### Removed
- Format Code button from UI (streamlined interface)

## [0.97.21] - 2026-01-01

### Added
- Debug logging for shared templates discovery
- Restored template functionality

### Fixed
- Template loading issues

## [0.97.0] - 2025-12-28

### Added
- Backup schedule time picker - configure what time daily backups run
- Usage Statistics dialog with metrics by Entry Writer and Client
- Statistics moved to Account menu

### Changed
- Settings renamed to Preferences
- Configuration renamed to Profiles
- View Log moved to Help menu
- Removed Log View menu (consolidated into Help)
- References dialog defaults to larger size (1200x700)
- HTS Database tab now first/default in References dialog
- Statistics dialog follows theme colors

## [0.96] - 2025-12-20

### Changed
- Tab reorganization: renamed to Invoice Processing, PDF Processing, and Parts View
- Streamlined PDF Processing by removing unused Parts History tab

### Updated
- All flowcharts and documentation to reflect current workflow

## [0.94.0] - 2024-12-18

### Added
- PDF Processing Integration with AI-powered invoice OCR
- Template system for different invoice formats
- Copyright protection and proprietary license notices

### Changed
- Enhanced dark theme styling consistency
- Improved Result Preview column layout

### Fixed
- Value rounding errors in material percentage row splitting

## [0.93.3] - 2024-12-16

### Fixed
- Startup ghost window flash
- Column names updated

### Changed
- Removed required field restriction from MID and Steel % in Parts Import
- Removed Export Profile dropdown and MID Management menu item
- Renamed Net Wt/Pcs columns to Qty1/Qty2 in Result Preview

### Added
- Profile linking, MID/Tariff tabs, and preview table enhancements

## [0.90.2] - 2024-12-14

### Added
- Landscape page setup for exported Excel worksheets
- Reprocess button to re-process invoices after database changes
- Animated spinner on splash screen during startup
- License system framework (disabled, for future use)
- Distribution database with pre-populated Section 232 tariff data

### Changed
- Database merge strategy now prefers database values over invoice values
- Repository cleanup and branch consolidation
- Improved packaging of reference data tables

### Fixed
- Version parsing for git describe format
- Merge strategy to properly prefer database values during processing

## [0.90.1] - 2024-12-01

### Added
- Export profiles for saving output column configurations
- Output column mapping customization
- Section 301 exclusion tariff tracking with symbol indicator
- Theme-specific color settings (Light/Dark modes)
- Split export by invoice number feature
- Color pickers for all Section 232 material types
- Color coding by Section 232 material type

### Changed
- Migrated to git-based versioning system
- Improved UI layout and responsiveness

### Fixed
- Export profile load error before Configuration dialog opened
- Non-232% column not displaying in Result Preview and Export
- Invoice total display and label text
- Country codes defaulting to MID when not in database
- DraggableLabel error when Excel has numeric column headers

## [0.90.0] - 2024-11-15

### Added
- Major refactoring and modernization of codebase
- Improved Parts Master management with advanced search
- Query builder for advanced database searches
- Multiple invoice mapping profiles support
- MID (Manufacturer ID) management system
- CBP quantity unit lookup for HTS codes

### Changed
- Modern tabbed interface design
- Real-time preview table with color-coded rows
- Configurable input/output directories

## [0.85.0] - 2024-10-01

### Added
- Initial public release
- Invoice processing (CSV, XLSX formats)
- CBP-compliant upload worksheet generation
- Parts Master database management
- Section 232 tariff tracking (steel, aluminum)
- Basic column mapping profiles
