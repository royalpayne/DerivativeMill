# Application Architecture

This flowchart shows the overall system architecture and component relationships.

```mermaid
flowchart TD
    subgraph UI["User Interface Layer (PyQt5)"]
        A[TariffMill Main Window]
        A --> B[Invoice Processing Tab]
        A --> C[PDF Processing Tab]
        A --> D[Parts View Tab]
        A --> E[Menu Bar]
        E --> F[Preferences]
        E --> G[Profiles]
        E --> H[Account]
        E --> I2[Help]
    end

    subgraph Business["Business Logic Layer"]
        B --> I[Invoice Processor]
        C --> J[OCR Engine]
        D --> K[Parts Manager]

        I --> L[Column Mapper]
        I --> M[Value Calculator]
        I --> N[Tariff Classifier]

        J --> O[Template Engine]
        O --> P[Template Registry]
    end

    subgraph Data["Data Access Layer"]
        L --> Q[(SQLite Database)]
        M --> Q
        N --> Q
        K --> Q
        P --> R[Template Files]

        Q --> S[parts_master]
        Q --> T[invoice_mappings]
        Q --> U[user_settings]
        Q --> V[hts_codes]
    end

    subgraph External["External Resources"]
        W[Input Files] --> I
        I --> X[Output Files]
        Y[Windows Registry] --> F
    end

    style A fill:#2196F3,color:#fff
    style Q fill:#4CAF50,color:#fff
    style R fill:#FF9800,color:#fff
```

## Component Overview

### User Interface Layer

| Component | Description |
|-----------|-------------|
| Main Window | Primary application window with tabbed interface |
| Invoice Processing | Invoice processing and export functionality (CSV/Excel files) |
| PDF Processing | OCR processing with AI template system for PDF invoices |
| Parts View | Database management for parts inventory |
| Menu Bar | Preferences, Profiles, Account, and Help menus |

### Business Logic Layer

| Component | Description |
|-----------|-------------|
| Invoice Processor | Core invoice processing engine |
| Parts Manager | CRUD operations for parts database |
| OCR Engine | Text extraction from PDF/images |
| Column Mapper | Map source columns to target fields |
| Value Calculator | Calculate quantities and distributions |
| Tariff Classifier | Determine Section 232/301 status |
| Template Engine | Match and apply OCR templates |

### Data Access Layer

| Component | Description |
|-----------|-------------|
| SQLite Database | Primary data storage |
| Template Files | Python template definitions |
| Windows Registry | User-specific preferences |

## Database Schema

```mermaid
erDiagram
    parts_master {
        text part_number PK
        text hts_code
        text country_of_origin
        text mid
        real steel_ratio
        real aluminum_ratio
        real copper_ratio
        real wood_ratio
        real auto_ratio
        text country_of_melt
        text country_of_cast
        text prim_country_of_smelt
    }

    invoice_mappings {
        integer id PK
        text profile_name
        text source_column
        text target_field
        text file_pattern
    }

    user_settings {
        text key PK
        text value
    }

    hts_codes {
        text hts_code PK
        text description
        text qty1_unit
        text qty2_unit
    }
```

## File Structure

```
Tariffmill/
├── tariffmill.py           # Main application
├── version.py              # Version management
├── Resources/
│   ├── tariffmill.db       # SQLite database
│   ├── icon.ico            # Application icon
│   └── References/
│       ├── hts.db          # HTS code reference database
│       └── CBP_232_tariffs.xlsx
├── templates/
│   ├── __init__.py         # Template discovery
│   ├── base_template.py    # Base template class
│   └── *.py                # Custom templates
├── Input/
│   └── Processed/          # Archived input files
└── Output/
    └── Processed/          # Archived output files
```

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python 3.12 | Core language |
| PyQt5 | Desktop GUI framework |
| Pandas | Data processing and manipulation |
| SQLite | Embedded database |
| OpenPyXL | Excel file read/write |
| pdfminer | PDF text extraction |
| Anthropic Claude | AI-powered template generation |
| PyInstaller | Executable packaging |
| Inno Setup | Windows installer |
