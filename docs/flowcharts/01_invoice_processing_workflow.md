# Invoice Processing Workflow

This flowchart shows the complete invoice processing workflow from file upload to export.

```mermaid
flowchart TD
    subgraph Input["1. Input Phase"]
        A[Start] --> B[Select Invoice File]
        B --> C{File Type?}
        C -->|CSV| D[Load CSV]
        C -->|XLSX| E[Load Excel]
        D --> F[Parse Data]
        E --> F
    end

    subgraph Mapping["2. Column Mapping Phase"]
        F --> G{Mapping Profile Exists?}
        G -->|Yes| H[Load Saved Profile]
        G -->|No| I[Create New Mapping]
        I --> J[Map Source Columns to Target Fields]
        J --> K[Save Profile]
        H --> L[Apply Mapping]
        K --> L
    end

    subgraph Configuration["3. Configuration Phase"]
        L --> M[Enter Invoice Total]
        M --> N[Select MID]
        N --> O[Set Processing Options]
    end

    subgraph Processing["4. Processing Phase"]
        O --> P[Click Process Invoice]
        P --> Q[Load Parts Master Data]
        Q --> R[Match Part Numbers]
        R --> S[Lookup HTS Codes]
        S --> T[Calculate Material Ratios]
        T --> U[Determine Section 232 Status]
        U --> V[Check Section 301 Exclusions]
        V --> W[Calculate Quantities]
        W --> X[Distribute Values]
    end

    subgraph Preview["5. Preview Phase"]
        X --> Y[Display Preview Table]
        Y --> Z{Values Match Total?}
        Z -->|No| AA[Edit Values in Table]
        AA --> AB[Recalculate Total]
        AB --> Z
        Z -->|Yes| AC[Ready for Export]
    end

    subgraph Export["6. Export Phase"]
        AC --> AD[Click Export Worksheet]
        AD --> AE{Split by Invoice?}
        AE -->|Yes| AF[Generate Multiple Files]
        AE -->|No| AG[Generate Single File]
        AF --> AH[Save to Output Directory]
        AG --> AH
        AH --> AI[Move Source to Processed]
        AI --> AJ[End]
    end

    style A fill:#4CAF50,color:#fff
    style AJ fill:#4CAF50,color:#fff
    style Z fill:#FFC107,color:#000
    style AC fill:#2196F3,color:#fff
```

## Process Steps

### 1. Input Phase
- User selects a CSV or XLSX invoice file
- System parses the file and loads data into memory

### 2. Column Mapping Phase
- If a saved mapping profile exists for this invoice format, it's loaded automatically
- Otherwise, user creates a new mapping to match source columns to target fields
- Mappings can be saved for reuse with similar invoices

### 3. Configuration Phase
- User enters the commercial invoice total
- Selects the appropriate MID (Manufacturer ID)
- Sets any additional processing options

### 4. Processing Phase
- System looks up each part number in the Parts Master database
- Retrieves HTS codes, material ratios, and country of origin data
- Calculates Section 232 tariff status based on material content
- Checks for Section 301 exclusions
- Calculates CBP quantities (Qty1, Qty2)
- Distributes values proportionally

### 5. Preview Phase
- Results displayed in editable preview table
- Color-coded rows indicate material classification
- User can edit values directly in the table
- System validates that line values match invoice total

### 6. Export Phase
- Generate CBP-compliant Excel worksheet
- Option to split output by invoice number
- Source files moved to Processed folder
