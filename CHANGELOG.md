# Changelog

All notable changes to DerivativeMill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
