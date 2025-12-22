# User Workflow

This flowchart shows the end-to-end user journey for processing customs documentation.

```mermaid
flowchart TD
    subgraph Setup["Initial Setup (One-time)"]
        A[Install TariffMill] --> B[Launch Application]
        B --> C[Configure Settings]
        C --> D[Set Input/Output Folders]
        D --> E[Import Parts Master Data]
        E --> F[Create Mapping Profiles]
    end

    subgraph Daily["Daily Workflow"]
        G[Receive Invoice] --> H{File Format?}
        H -->|PDF| I[Use OCRMill]
        H -->|CSV/Excel| J[Use Process Shipment]

        I --> K[Select Template]
        K --> L[Extract Data]
        L --> M[Export to CSV]
        M --> J

        J --> N[Load Invoice File]
        N --> O[Select/Create Mapping]
        O --> P[Enter Invoice Total]
        P --> Q[Select MID]
        Q --> R[Click Process]
    end

    subgraph Review["Review & Edit"]
        R --> S[View Preview Table]
        S --> T{Data Correct?}
        T -->|No| U[Edit Values]
        U --> V[Reprocess if Needed]
        V --> S
        T -->|Yes| W[Verify Total Matches]
    end

    subgraph Export["Export & Archive"]
        W --> X[Click Export Worksheet]
        X --> Y[Choose Export Options]
        Y --> Z[Generate CBP Worksheet]
        Z --> AA[File Saved to Output]
        AA --> AB[Source Moved to Processed]
        AB --> AC[Done]
    end

    subgraph Maintenance["Periodic Maintenance"]
        AD[Update Parts Master] --> AE[Query Builder Search]
        AE --> AF[Edit/Delete Records]
        AF --> AG[Import New Parts]
        AG --> AH[Backup Database]
    end

    style A fill:#4CAF50,color:#fff
    style AC fill:#4CAF50,color:#fff
    style T fill:#FFC107,color:#000
```

## Detailed User Steps

### Initial Setup

1. **Install Application**
   - Run TariffMill_Setup.exe installer
   - Or use standalone TariffMill.exe

2. **Configure Settings**
   - Settings → Settings
   - Set input folder (where invoices are stored)
   - Set output folder (where exports are saved)
   - Choose theme (Light/Dark)

3. **Import Parts Data**
   - Parts Master tab → Import
   - Select CSV file with parts data
   - Map columns to database fields
   - Import records

4. **Create Mapping Profiles**
   - Process first invoice from each supplier
   - Create mapping for that invoice format
   - Save profile for future use

### Daily Invoice Processing

```mermaid
sequenceDiagram
    participant User
    participant TariffMill
    participant Database
    participant FileSystem

    User->>TariffMill: Load Invoice File
    TariffMill->>TariffMill: Parse CSV/Excel
    User->>TariffMill: Select Mapping Profile
    TariffMill->>TariffMill: Apply Column Mapping
    User->>TariffMill: Enter Invoice Total
    User->>TariffMill: Select MID
    User->>TariffMill: Click Process
    TariffMill->>Database: Lookup Part Numbers
    Database-->>TariffMill: Return Part Data
    TariffMill->>TariffMill: Calculate Tariffs
    TariffMill->>TariffMill: Distribute Values
    TariffMill-->>User: Display Preview
    User->>TariffMill: Verify & Edit
    User->>TariffMill: Click Export
    TariffMill->>FileSystem: Save Excel Worksheet
    TariffMill->>FileSystem: Archive Source File
    TariffMill-->>User: Confirm Complete
```

### Quick Reference

| Task | Location | Steps |
|------|----------|-------|
| Process Invoice | Process Shipment tab | Load → Map → Process → Export |
| Add New Part | Parts Master tab | Right-click → Add Row |
| Edit Part | Parts Master tab | Double-click cell |
| Search Parts | Parts Master tab | Use search box or Query Builder |
| Import Parts | Parts Master tab | File → Import |
| Change Theme | Settings menu | Select Light/Dark |
| View Logs | Log View menu | View Log |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open invoice file |
| Ctrl+S | Save/Export |
| Ctrl+P | Process invoice |
| Ctrl+F | Search parts |
| Ctrl+R | Refresh/Reprocess |
| F5 | Refresh file lists |

### Troubleshooting Common Issues

| Issue | Solution |
|-------|----------|
| Part not found | Add to Parts Master database |
| Values don't match | Edit in preview table |
| Wrong HTS code | Update in Parts Master |
| Missing MID | Add to MID list in Configuration |
| Export fails | Check output folder permissions |
