# Section 232/301 Tariff Detection

This flowchart shows how TariffMill determines Section 232 and Section 301 tariff classifications.

```mermaid
flowchart TD
    subgraph Input["Input Data"]
        A[Part Number] --> B[Lookup in Parts Master]
        B --> C[Get Material Ratios]
        B --> D[Get HTS Code]
        B --> E[Get Country Data]
    end

    subgraph Section232["Section 232 Analysis"]
        C --> F{Steel Ratio > 0?}
        F -->|Yes| G[Flag as Steel]
        C --> H{Aluminum Ratio > 0?}
        H -->|Yes| I[Flag as Aluminum]
        C --> J{Copper Ratio > 0?}
        J -->|Yes| K[Flag as Copper]
        C --> L{Wood Ratio > 0?}
        L -->|Yes| M[Flag as Wood]
        C --> N{Auto Ratio > 0?}
        N -->|Yes| O[Flag as Automotive]

        G --> P[Determine Primary Material]
        I --> P
        K --> P
        M --> P
        O --> P

        P --> Q{Primary Material}
        Q -->|Steel| R[Check Melt/Cast/Smelt Countries]
        Q -->|Aluminum| S[Check Primary Smelt Country]
        Q -->|Other| T[Standard Processing]
    end

    subgraph CountryCheck["Country Declaration"]
        E --> R
        E --> S
        R --> U{US Melt/Cast?}
        U -->|Yes| V[Declaration: US Origin]
        U -->|No| W[Declaration: Foreign Origin]
        S --> X{US Smelt?}
        X -->|Yes| Y[Declaration: US Origin]
        X -->|No| Z[Declaration: Foreign Origin]
    end

    subgraph Section301["Section 301 Analysis"]
        D --> AA[Check HTS against 301 List]
        AA --> AB{On Exclusion List?}
        AB -->|Yes| AC[Apply Exclusion Tariff]
        AB -->|No| AD[Standard Tariff]
        AC --> AE[Flag for Review]
    end

    subgraph Output["Classification Output"]
        V --> AF[232 Flag]
        W --> AF
        Y --> AF
        Z --> AF
        T --> AF
        AD --> AG[301 Status]
        AE --> AG
        AF --> AH[Preview Row Color]
        AG --> AH
        AH --> AI[Display in Table]
    end

    style Q fill:#FFC107,color:#000
    style AB fill:#FFC107,color:#000
    style AI fill:#4CAF50,color:#fff
```

## Section 232 Steel/Aluminum Tariffs

### Material Classification
| Material | Tariff Rate | Declaration Required |
|----------|-------------|---------------------|
| Steel | 25% | Melt, Cast, Smelt countries |
| Aluminum | 10% | Primary smelt country |
| Copper | Varies | Country of origin |
| Wood | Varies | Country of harvest |
| Automotive | Varies | USMCA compliance |

### Country Declaration Logic

**Steel Products:**
```
If steel_ratio > 0:
    Require: country_of_melt, country_of_cast, prim_country_of_smelt
    Declaration Flag based on US vs Foreign origin
```

**Aluminum Products:**
```
If aluminum_ratio > 0:
    Require: prim_country_of_smelt
    Declaration Flag based on US vs Foreign origin
```

## Section 301 Exclusions

### Exclusion Check Process
1. Extract HTS code from part data
2. Compare against Section 301 exclusion list
3. If match found, apply exclusion tariff rate
4. Flag row for special handling in export

### Visual Indicators

| Color | Meaning |
|-------|---------|
| Blue | Steel product |
| Green | Aluminum product |
| Orange | Copper product |
| Brown | Wood product |
| Purple | Automotive product |
| Red Border | Section 301 exclusion |
| Gray | No special classification |

## Processing Flow

1. **Load Part Data** - Retrieve all material ratios from database
2. **Calculate Percentages** - Determine material composition
3. **Identify Primary Material** - Find highest ratio material
4. **Check Country Data** - Verify melt/cast/smelt declarations
5. **Apply 232 Rules** - Determine tariff applicability
6. **Check 301 List** - Compare HTS against exclusion list
7. **Set Display Colors** - Apply visual indicators
8. **Generate Declarations** - Create required declaration text
