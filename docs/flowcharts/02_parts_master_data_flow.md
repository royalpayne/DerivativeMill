# Parts Master Data Flow

This flowchart shows how parts data is managed, imported, and used throughout the application.

```mermaid
flowchart TD
    subgraph DataSources["Data Sources"]
        A[CSV Import File]
        B[Manual Entry]
        C[Invoice Processing]
    end

    subgraph Import["Import Process"]
        A --> D[Parts Import Dialog]
        D --> E[Map CSV Columns]
        E --> F[Validate Data]
        F --> G{Valid?}
        G -->|No| H[Show Errors]
        H --> E
        G -->|Yes| I[Import to Database]
    end

    subgraph Database["SQLite Database"]
        I --> J[(parts_master)]
        B --> J
        J --> K[Part Number]
        J --> L[HTS Code]
        J --> M[Country of Origin]
        J --> N[MID]
        J --> O[Material Ratios]
        J --> P[Melt/Cast/Smelt Countries]
    end

    subgraph Usage["Data Usage"]
        C --> Q[Lookup Part Number]
        Q --> J
        J --> R[Return Part Data]
        R --> S[Apply to Invoice Line]
    end

    subgraph Query["Query & Search"]
        T[Quick Search] --> J
        U[Query Builder] --> V[Build SQL Query]
        V --> J
        J --> W[Display Results]
    end

    subgraph Maintenance["Data Maintenance"]
        X[Edit Cell] --> J
        Y[Delete Row] --> J
        Z[Bulk Update] --> J
    end

    style J fill:#2196F3,color:#fff
    style G fill:#FFC107,color:#000
    style I fill:#4CAF50,color:#fff
```

## Data Structure

### Parts Master Table Fields
| Field | Description | Used For |
|-------|-------------|----------|
| part_number | Unique part identifier | Primary lookup key |
| hts_code | Harmonized Tariff Schedule code | Duty calculation |
| country_of_origin | Country where product originated | CBP declaration |
| mid | Manufacturer ID | Customs identification |
| steel_ratio | Percentage of steel content | Section 232 |
| aluminum_ratio | Percentage of aluminum content | Section 232 |
| copper_ratio | Percentage of copper content | Section 232 |
| wood_ratio | Percentage of wood content | Section 232 |
| auto_ratio | Percentage classified as automotive | Section 232 |
| country_of_melt | Steel melt country | Section 232 declaration |
| country_of_cast | Steel cast country | Section 232 declaration |
| prim_country_of_smelt | Primary smelt country | Section 232 declaration |

## Import Process

1. **Select CSV File** - Choose a CSV file containing parts data
2. **Map Columns** - Match CSV columns to database fields
3. **Validate** - Check for required fields and data format
4. **Preview** - Review data before import
5. **Import** - Insert or update records in database

## Query Builder

The Query Builder allows complex searches:
- Multiple conditions (AND/OR)
- Field comparisons (equals, contains, starts with)
- Numeric ranges
- Export results to CSV
