# PDF Processing Template System

This flowchart shows how the PDF Processing tab processes invoices using the template system.

```mermaid
flowchart TD
    subgraph Input["1. Document Input"]
        A[PDF/Image Invoice] --> B[OCR Engine]
        B --> C[Extract Raw Text]
    end

    subgraph TemplateDiscovery["2. Template Discovery"]
        D[Templates Directory] --> E[Scan for .py Files]
        E --> F[Load Template Classes]
        F --> G[Build Template Registry]
    end

    subgraph Matching["3. Template Matching"]
        C --> H[For Each Template]
        G --> H
        H --> I[Call can_process]
        I --> J{Match?}
        J -->|Yes| K[Calculate Confidence Score]
        J -->|No| L[Try Next Template]
        L --> H
        K --> M[Add to Candidates]
        M --> N{More Templates?}
        N -->|Yes| H
        N -->|No| O[Select Best Match]
    end

    subgraph Extraction["4. Data Extraction"]
        O --> P[Selected Template]
        P --> Q[extract_invoice_number]
        P --> R[extract_project_number]
        P --> S[extract_line_items]
        Q --> T[Invoice Data]
        R --> T
        S --> T
    end

    subgraph Output["5. Output"]
        T --> U[Structured Data]
        U --> V[Display in UI]
        U --> W[Export to CSV]
    end

    style A fill:#9C27B0,color:#fff
    style O fill:#4CAF50,color:#fff
    style U fill:#2196F3,color:#fff
```

## Template System Architecture

### Template Discovery
```
templates/
├── __init__.py          # Dynamic discovery logic
├── base_template.py     # Base class for all templates
├── sample_template.py   # Example template (excluded)
├── bill_of_lading.py    # Bill of Lading template
├── mmcite_brazilian.py  # Brazilian supplier template
├── mmcite_czech.py      # Czech supplier template
└── lacey_act_form.py    # PPQ Form 505 template
```

### Template Interface

Each template must implement:

```python
class MyTemplate(BaseTemplate):
    name = "Template Name"
    description = "Template description"
    client = "Client/Vendor name"
    version = "1.0.0"
    enabled = True

    def can_process(self, text: str) -> bool:
        """Check if this template can process the text"""
        pass

    def get_confidence_score(self, text: str) -> float:
        """Return 0.0-1.0 confidence score"""
        pass

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from text"""
        pass

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from text"""
        pass
```

## Matching Algorithm

1. **Load All Templates** - Scan templates directory for Python files
2. **Filter Enabled** - Only consider templates with `enabled = True`
3. **Test Each Template** - Call `can_process()` on extracted text
4. **Score Matches** - Calculate confidence scores for matching templates
5. **Select Best** - Choose template with highest confidence score

## Hot Reload

Templates support hot reload:
- Call `refresh_templates()` to rescan directory
- New templates are automatically discovered
- Modified templates are reloaded
- Deleted templates are removed from registry
