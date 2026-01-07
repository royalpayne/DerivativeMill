# TariffMill User Guide

**Professional Customs Documentation Processing System**

Version 0.97.34 | Last Updated: January 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Getting Started](#getting-started)
5. [Invoice Processing](#invoice-processing)
6. [PDF Processing (OCRMill)](#pdf-processing-ocrmill)
7. [Parts Database Management](#parts-database-management)
8. [Reference Data](#reference-data)
9. [Configuration & Settings](#configuration--settings)
10. [Profile Management](#profile-management)
11. [e2Open Integration](#e2open-integration)
12. [Administration](#administration)
13. [Troubleshooting](#troubleshooting)
14. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Introduction

TariffMill is a desktop application designed for import/export businesses, customs brokers, and trade compliance professionals. It automates invoice processing, manages parts databases, and ensures compliance with Section 232 and Section 301 tariff requirements.

### Key Features

- **Intelligent Invoice Processing** - Transform commercial invoices into customs-ready upload sheets
- **AI-Powered PDF Extraction** - Extract invoice data from PDF documents using customizable templates
- **Section 232 Automation** - Automatic derivative line creation with prorated values for steel, aluminum, copper, wood, and automotive materials
- **Parts Master Database** - Centralized management of HTS codes, material compositions, and country of origin data
- **e2Open Integration** - Export files pre-mapped for direct upload to e2Open Customs Management

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Operating System | Windows 10 | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk Space | 200 MB | 500 MB |
| Display | 1280 x 720 | 1920 x 1080 |

### Supported Platforms

- **Windows**: Native installer or portable executable
- **Linux/macOS**: Python pip installation

---

## Installation

### Windows Installer (Recommended)

1. Download `TariffMill_Setup_x.xx.xx.exe` from the [Releases](https://github.com/ProcessLogicLabs/TariffMill/releases) page
2. Run the installer and follow the prompts
3. Launch TariffMill from the Start Menu or Desktop shortcut

### Windows Portable

1. Download `TariffMill.exe` from the Releases page
2. Place in your preferred location
3. Double-click to run (no installation required)

#### Windows SmartScreen Warning

On first run, Windows may display "Windows protected your PC" because the application is new. To proceed:

1. Click **"More info"**
2. Click **"Run anyway"**

### Linux/macOS (pip)

```bash
pip install git+https://github.com/ProcessLogicLabs/TariffMill.git
tariffmill
```

---

## Getting Started

### First Launch

1. **Login** - Enter your credentials or create a new account
2. **Configure Folders** - Set your input and output directories via **Preferences**
3. **Import Reference Data** - Load HTS database and Section 232 tariffs via **References**
4. **Set Up Parts Database** - Import your parts with HTS codes and material compositions

### Application Layout

TariffMill uses a tabbed interface with three main sections:

| Tab | Purpose |
|-----|---------|
| **Invoice Processing** | Process CSV/Excel invoices and generate upload worksheets |
| **PDF Processing** | Extract data from PDF invoices using AI-powered OCR |
| **Parts View** | Manage your parts master database |

### Menu Bar

| Menu | Contents |
|------|----------|
| **Preferences** | Application settings and configuration |
| **Account** | User info, statistics, sign out |
| **References** | HTS database, Section 232 tariffs, customs configuration |
| **Profiles** | Invoice mapping and export profile management |
| **Help** | License, updates, logs, about |

---

## Invoice Processing

The Invoice Processing tab is the primary workflow for converting commercial invoices into customs-ready upload worksheets.

### Processing Workflow

```
1. Select Invoice → 2. Enter Values → 3. Process → 4. Review → 5. Export
```

### Step-by-Step Guide

#### Step 1: Select Invoice File

1. Choose a **Folder Profile** from the dropdown (or use default folders)
2. Click **Refresh** to scan the input directory
3. Select an invoice file from the **Input Files** list
   - Supported formats: `.csv`, `.xlsx`, `.xls`

#### Step 2: Enter Invoice Values

| Field | Description | Required |
|-------|-------------|----------|
| **CI Value (USD)** | Total commercial invoice value | Yes |
| **Net Weight (kg)** | Shipment net weight for calculations | No |
| **MID** | Manufacturer ID from dropdown | Yes |
| **Division** | Your division (if applicable) | Conditional |
| **File Number** | Billing reference number | Yes |

The **Invoice Check** indicator shows validation status:
- **Green checkmark** - Values match the calculated totals
- **Red X** - Discrepancy detected; click **Edit Values** to correct

#### Step 3: Process Invoice

1. Click **Process Invoice**
2. TariffMill matches parts to your database and applies:
   - HTS codes and descriptions
   - Material compositions (steel, aluminum, copper, wood, auto percentages)
   - Section 232 derivative calculations
   - Declaration codes and country of origin data
   - CBP quantity units

#### Step 4: Review Results

The **Result Preview** table displays processed data with color-coded rows:

| Color | Material Type |
|-------|--------------|
| Gray | Steel (Declaration Code 08) |
| Blue | Aluminum (Declaration Code 07) |
| Orange | Copper |
| Brown | Wood |
| Dark Green | Automotive |
| White | Non-232 items |
| Highlighted | Section 301 exclusions |

**Preview Features:**
- Click column headers to sort
- Right-click for context menu options
- Double-click cells to edit values
- Use **Edit Worksheet** for bulk modifications

#### Step 5: Export Worksheet

1. Click **Export Worksheet** (button changes after processing)
2. Choose export location (defaults to output folder)
3. File is generated with timestamp: `InvoiceName_YYYYMMDD_HHMMSS.xlsx`

### Section 232 Derivative Processing

TariffMill automatically creates derivative line items for materials subject to Section 232 tariffs:

**How It Works:**
1. Each line item with material content is split into derivative lines
2. Values are prorated based on material percentages
3. Declaration codes are assigned automatically:
   - **08** - Steel derivatives
   - **07** - Aluminum derivatives
4. Country of melt/pour/cast/smelt codes are populated from parts database

**Example:**
A $1,000 part with 30% steel and 10% aluminum becomes:
- Original line: $600 (remaining value)
- Steel derivative: $300 (Declaration Code 08)
- Aluminum derivative: $100 (Declaration Code 07)

---

## PDF Processing (OCRMill)

The PDF Processing tab extracts invoice data from PDF documents using AI-powered templates.

### Features

- **Drag & Drop** - Drop PDF files directly into the application
- **Batch Processing** - Process multiple PDFs at once
- **Folder Monitoring** - Automatically process new files as they arrive
- **Template Library** - Pre-built and custom templates for different invoice formats

### Processing PDF Invoices

#### Single File Processing

1. Navigate to the **PDF Processing** tab
2. Set **Input Folder** (where PDFs are located)
3. Set **Output Folder** (where extracted data will be saved)
4. Select a PDF from the **Input Files** list
5. Click **Process Single File**
6. Review extracted data in the **Output Files** list

#### Batch Processing

1. Click **Process Multiple Files**
2. Select PDFs to process in the dialog
3. Click **Start Batch**
4. Monitor progress in the status area

#### Folder Monitoring

1. Configure input/output folders
2. Toggle **Monitor Folder** ON
3. Drop PDFs into the input folder
4. Files are automatically processed and results appear in output

### AI Template System

Templates define how TariffMill extracts data from specific invoice formats.

#### Using Existing Templates

1. Go to the **Templates** sub-tab
2. Browse the template list
3. Templates are automatically matched based on invoice content

#### Creating New Templates

1. Click **New Template**
2. Use the AI assistant to generate extraction rules:
   - Describe the invoice format
   - Identify key fields (part numbers, quantities, values)
   - Refine with the chat interface
3. Click **Save** when satisfied

#### Template Fields

Templates can extract:
- Part Number
- Description
- Quantity
- Unit Price
- Extended Value
- Country of Origin
- HTS Code (if present on invoice)

### Sending to Invoice Processing

After extraction:
1. Select output file in the **Output Files** list
2. Click **Send to Invoice Processing**
3. Data transfers to the Invoice Processing tab for tariff application

---

## Parts Database Management

The Parts View tab provides access to your parts master database.

### Parts Database Fields

| Field | Description |
|-------|-------------|
| **Part Number** | Unique identifier (required) |
| **HTS Code** | 10-digit Harmonized Tariff Schedule code (required) |
| **Description** | Part description |
| **MID** | Associated Manufacturer ID |
| **Country** | Country of origin |
| **Steel %** | Steel content percentage (0-100) |
| **Aluminum %** | Aluminum content percentage (0-100) |
| **Copper %** | Copper content percentage (0-100) |
| **Wood %** | Wood content percentage (0-100) |
| **Auto %** | Automotive content percentage (0-100) |
| **Country Melt** | Steel melt/pour country |
| **Country Cast** | Casting country |
| **Country Smelt** | Smelting country (aluminum/copper) |

### Importing Parts

1. Go to **Profiles** → **Parts Import** tab
2. Click **Load CSV/Excel File**
3. Map columns by dragging source columns to target fields
4. Click **Import Now**

**Required mappings:**
- Part Number
- HTS Code

### Editing Parts

1. In **Parts View**, locate the part to edit
2. Double-click the cell to modify
3. Press Enter to save changes

### Searching Parts

Use the search bar at the top of the Parts View to filter by:
- Part number
- HTS code
- Description
- Any visible column

---

## Reference Data

Access reference data via **References** menu → **References...**

### HTS Database Tab

The HTS database provides tariff code lookup and CBP quantity unit information.

#### Importing HTS Data

**Recommended Method (JSON):**
1. Click **Import from JSON File**
2. Select the CBP HTS export file
3. Wait for import to complete

**Alternative Method (CSV):**
1. Click **Open USITC Download Page**
2. Download the current HTS schedule
3. Click **Import from CSV File**
4. Select the downloaded file

#### Using HTS Lookup

1. Enter an HTS code in the search box
2. View:
   - Full tariff description
   - Unit of quantity (for CBP reporting)
   - Duty rates
   - Special program indicators

### Customs Config Tab

Manage Section 232 tariff classifications.

#### Importing Section 232 Tariffs

1. Click **Import Section 232 Tariffs**
2. Select your tariff classification CSV/Excel file
3. Columns should include: HTS Code, Material Type, Classification

#### Filtering Tariffs

- Use the **Material** dropdown to filter by: Steel, Aluminum, Copper, Wood, Auto
- Toggle **Color by Material** to visualize classifications
- Search by HTS code or description

### Section 232 Actions Tab

Manage Chapter 99 tariff action codes.

#### Importing Action Codes

1. Click **Import Actions CSV**
2. Select file containing tariff action codes and rates

---

## Configuration & Settings

Access via **Preferences** menu → **Preferences...**

### Appearance Tab

| Setting | Description |
|---------|-------------|
| **Theme** | Application color scheme (7 options) |
| **Font Size** | UI text size (8-16pt) |
| **Row Height** | Preview table row height (22-40px) |
| **Excel Viewer** | Application to open exported files |
| **Row Colors** | Customize colors for each material type |

**Available Themes:**
- System Default
- Fusion Light
- Fusion Dark
- Ocean
- Light Cyan
- Muted Cyan
- macOS

### Data Management Tab

| Setting | Description |
|---------|-------------|
| **Input Folder** | Default location for invoice files |
| **Output Folder** | Default location for exported worksheets |
| **Auto-refresh** | Automatically scan input folder for new files |
| **Delete Processed** | Remove input files after successful export |
| **Network Drive Support** | Enable for mapped network drives |

### Backup & Recovery Tab

| Setting | Description |
|---------|-------------|
| **Automatic Backup** | Enable scheduled database backups |
| **Backup Frequency** | Daily, weekly, or custom schedule |
| **Retention** | Number of backups to keep |

### Startup & Updates Tab

| Setting | Description |
|---------|-------------|
| **Check for Updates** | Automatically check on startup |
| **Auto-update** | Download and install updates automatically |

### Domain Configuration Tab

| Setting | Description |
|---------|-------------|
| **Shared Templates** | Network folder for shared PDF templates |
| **Custom Templates** | Local folder for personal templates |

---

## Profile Management

Access via **Profiles** menu → **Profiles...**

### Invoice Mapping Profiles

Save column mapping configurations for different invoice formats.

#### Creating a Mapping Profile

1. Process an invoice and configure column mappings
2. Go to **Profiles** → **Invoice Mapping** tab
3. Click **Save as Profile**
4. Enter a profile name
5. Click **Save**

#### Using a Mapping Profile

1. Select profile from the dropdown in Invoice Processing tab
2. Column mappings are automatically applied

### Output Mapping Profiles

Control which columns appear in exported worksheets.

#### Creating an Export Profile

1. Go to **Profiles** → **Output Mapping** tab
2. Configure:
   - Column visibility (check/uncheck columns)
   - Column order (drag to reorder)
   - Export colors per material type
3. Click **Save as New Profile**
4. Enter profile name

#### Switching Export Profiles

Use the export profile dropdown in the Invoice Processing tab to quickly switch between configurations.

### Folder Profiles

Save input/output folder combinations for quick switching.

#### Creating a Folder Profile

1. Click **Manage** next to Folder Profile dropdown
2. Click **New Profile**
3. Enter profile name
4. Set input and output folder paths
5. Click **Save**

---

## e2Open Integration

TariffMill exports are pre-mapped for e2Open's Customs Management Invoice Import module.

### Upload Mapping Reference

TariffMill export columns map directly to e2Open import fields:

#### Commercial Invoice Lines

| TariffMill Column | e2Open Field |
|-------------------|--------------|
| Part Number | Part Number |
| Value | Value |
| MID | Manufacturer |

#### Tariff Classification Lines

| TariffMill Column | e2Open Field |
|-------------------|--------------|
| HTS | Tariff No |
| Qty 1 Unit | Qty 1 Class |
| Qty 2 Unit | Qty 2 Class |

#### Additional Declarations

| TariffMill Column | e2Open Field |
|-------------------|--------------|
| Declaration Code | Declaration Type Cd |
| Country Melt Pour | Country Melt Pour Cd |
| Country Cast | Country Cast |
| Primary Country Smelt | Primary Country Smelt |
| Primary Country Applic | Primary Country Applic |

### Upload Configuration

In e2Open Customs Management:
1. Go to **Invoice Import** → **Upload Mapping**
2. Select or create mapping type: **PARTS PLUS**
3. Map fields according to the reference above
4. Save configuration

### Importing TariffMill Export

1. Export worksheet from TariffMill
2. In e2Open, navigate to **Invoice Import**
3. Select your upload mapping profile
4. Browse to the TariffMill export file
5. Click **Upload**
6. Review imported data

### Benefits of Integration

- **No Manual Line Splitting** - Derivative lines pre-created with prorated values
- **Skip Declarations Dialog** - Melt/Smelt/Cast codes pre-populated
- **Auto CBP Quantities** - Qty 1 & 2 units from HTS database
- **Direct Upload** - No reformatting required

---

## Administration

### User Statistics

View processing metrics via **Account** → **Statistics...**

- Total files processed
- Processing by date range
- OCRMill extraction statistics
- User activity summary

### Division Administration

Division administrators can manage users in their division:

1. **Account** → **Manage Division Users...**
2. View users assigned to your division
3. Edit user roles and permissions
4. Deactivate users as needed

### License Management

**Account** → **License & Activation...**

- View license status (Licensed, Trial, Expired)
- Enter activation key
- Check days remaining on trial

---

## Troubleshooting

### Common Issues

#### "File Number Required" Error

**Cause:** File number field is empty or invalid

**Solution:**
1. Enter a valid file number in the required format
2. Check division file number pattern requirements

#### Invoice Values Don't Match

**Cause:** Calculated total differs from entered CI Value

**Solution:**
1. Click **Edit Values** to review line items
2. Adjust values to match commercial invoice
3. Re-process invoice

#### Parts Not Found

**Cause:** Part numbers in invoice don't match database

**Solution:**
1. Import missing parts via **Profiles** → **Parts Import**
2. Verify part number format matches exactly
3. Check for leading/trailing spaces

#### PDF Extraction Fails

**Cause:** No matching template or poor PDF quality

**Solution:**
1. Try a different template
2. Create a custom template for this invoice format
3. Ensure PDF is not image-only (needs text layer)

### Application Logs

View detailed logs via **Help** → **View Log**

- Copy logs for support requests
- Clear logs to free space

### Support

- **GitHub Issues:** [github.com/ProcessLogicLabs/TariffMill/issues](https://github.com/ProcessLogicLabs/TariffMill/issues)
- **Documentation:** This guide and in-app help

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save current work |
| `Ctrl+P` | Process invoice |
| `Ctrl+E` | Export worksheet |
| `Ctrl+R` | Refresh file list |
| `F5` | Refresh current view |
| `Ctrl+F` | Search/Find |
| `Ctrl+Shift+A` | Admin panel (authorized users) |

---

## Appendix

### Supported File Formats

**Input:**
- CSV (.csv)
- Excel (.xlsx, .xls)
- PDF (.pdf) - via OCRMill

**Output:**
- Excel Workbook (.xlsx)

### Material Declaration Codes

| Code | Material | Description |
|------|----------|-------------|
| 07 | Aluminum | Aluminum and aluminum derivatives |
| 08 | Steel | Steel and steel derivatives |

### Data Privacy

TariffMill is designed with pass-through architecture:
- Commercial invoice data is **not stored** permanently
- Data passes through for transformation only
- Client-sensitive information remains transient

---

*TariffMill - Professional Customs Documentation Processing*

*Copyright ProcessLogicLabs. All rights reserved.*
