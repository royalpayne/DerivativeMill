# PDF Extraction Guide - Complete Workflow

## Understanding Your PDFs

Your PDF (CH_HFA001.pdf) is a **digital PDF with text but no structured tables**:
- ✓ Has extractable text (1218 characters)
- ✓ Is digitally created (not scanned)
- ✗ No bordered tables that pdfplumber can detect
- ✗ Layout uses images/formatting instead of table structure

## PDF Types Handled

| Type | Example | Extraction Method | What Happens |
|------|---------|-------------------|--------------|
| **Digital with tables** | Standard invoice with boxes | pdfplumber table extraction | Automatic column detection |
| **Digital without tables** | Text-based invoice | Text fallback extraction | Manual column mapping |
| **Scanned (image-based)** | Scanned document | OCR + pattern matching | Supplier template matching |

## Workflow for Your PDF

### Step 1: Diagnose the PDF

Use the diagnostic tool to understand your PDF:

```bash
cd DerivativeMill
../venv/bin/python debug_pdf.py Input/CH_HFA001.pdf
```

**Output tells you:**
- PDF structure (pages, content types)
- Whether tables are detected
- Whether text is present
- Recommended extraction method

### Step 2: Load in App

Click **"Load Invoice File"** in the Invoice Mapping Profiles tab:

1. Select your PDF
2. App automatically detects:
   - If it's scanned → Uses OCR
   - If it has tables → Extracts with pdfplumber
   - If no tables → Uses text fallback
3. Extracted data appears as draggable columns

### Step 3: Map Your Data

For PDFs without tables, you get a single column `text_line`:

```
text_line
-----------
AROMATE INDUSTRIES CO., LTD.
Address Line 1
Product SKU
Price: $99.99
... (more text lines)
```

**To use this data:**
1. Drag the `text_line` column to map it
2. You'll need to parse the text manually or:
3. Create a custom OCR template for pattern matching

## Text Extraction Fallback

When pdfplumber can't find tables, the app now:

1. **Extracts all text lines** from the PDF
2. **Creates a DataFrame** with one column: `text_line`
3. **Allows manual mapping** - you can drag this to your fields
4. **Returns 34 lines** from your CH_HFA001.pdf

### How to Use Text Lines

**Option 1: Manual Entry**
- Review the text lines
- Manually type the data you need
- Save to your shipping mapping

**Option 2: Parse with OCR Template**
If the text has a pattern:
```
Part: ABC-123
Price: $49.99
Part: XYZ-456
Price: $99.50
```

Create an OCR template to parse it:
```bash
../venv/bin/python create_ocr_template.py
```

**Option 3: Custom Python Script**
Parse the text programmatically:
```python
from pathlib import Path
import pandas as pd
from ocr import extract_pdf_text_fallback  # If exposed

# Load text lines
df = app.extract_pdf_table("Input/CH_HFA001.pdf")

# Parse the text_line column
for idx, row in df.iterrows():
    line = row['text_line']
    # Your parsing logic here
    if "SKU" in line:
        part_number = line.split(":")[1].strip()
    if "Price" in line:
        value = line.split("$")[1].strip()
```

## Diagnostic Tool Usage

### Command

```bash
cd DerivativeMill
../venv/bin/python debug_pdf.py <pdf_path>
```

### Examples

```bash
# Check your invoice
../venv/bin/python debug_pdf.py Input/CH_HFA001.pdf

# Check any PDF
../venv/bin/python debug_pdf.py Input/invoice_from_supplier.pdf
```

### Output Interpretation

**If you see:**
```
Tables found: 0
Text lines: 34
...
⚠️  No tables detected but text is present
   Options:
   1. Try OCR with custom template
   2. Use manual data entry
```

→ **Use text fallback** - load in app and map the `text_line` column

**If you see:**
```
Tables found: 2
Table 1: 15 rows × 5 cols
...
✓ Tables detected
```

→ **Use pdfplumber** - app will extract tables automatically

## For Your Specific Case (CH_HFA001.pdf)

### What We Know
- File size: 65.3 KB
- Pages: 1
- Text content: 1218 characters
- Structure: No tables, text-based layout
- Source: AROMATE INDUSTRIES CO., LTD.

### What To Do
1. **Test in app:**
   ```bash
   # In app: Go to Invoice Mapping Profiles → Load Invoice File
   # Select: Input/CH_HFA001.pdf
   # You should get a "text_line" column with 34 extracted lines
   ```

2. **If you need automatic extraction:**
   - Create an OCR template to parse the text:
   ```bash
   ../venv/bin/python create_ocr_template.py
   ```
   - Create a template named "AROMATE"
   - Define patterns to match your data format

3. **If you just need the text:**
   - Map the `text_line` column
   - You'll see all extracted text
   - You can manually select which lines contain your data

## PDF Extraction Architecture

```
PDF File
    ↓
[Determine PDF type]
    ↓ Digital with tables → pdfplumber extract_tables()
    ↓ Digital without tables → Text fallback (NEW)
    ↓ Scanned → OCR extraction
    ↓
[Return DataFrame]
    ↓
[Display draggable columns]
    ↓
[User maps to their fields]
```

## Troubleshooting

### Problem: "No valid table found in PDF"

**Before (Old Behavior):**
- Hard error
- Could not use the PDF

**After (New Behavior):**
- Falls back to text extraction
- Returns all text lines
- User can still map and use the data

### Problem: PDF has weird formatting

**Diagnostic:**
```bash
../venv/bin/python debug_pdf.py Input/your_pdf.pdf
```

**If no tables:**
- Use text fallback + manual mapping
- Or create OCR template

**If tables detected but wrong data:**
- pdfplumber is confused by layout
- Use text fallback as alternative

### Problem: Multiple suppliers with different formats

**Solution:**
Create templates for each supplier:
```bash
../venv/bin/python create_ocr_template.py  # Supplier A
../venv/bin/python create_ocr_template.py  # Supplier B
../venv/bin/python create_ocr_template.py  # Supplier C
```

Each template stored in `ocr/templates/` with custom patterns.

## Technical Details

### Text Fallback Function

Location: [derivativemill.py:2806-2852](DerivativeMill/derivativemill.py#L2806-L2852)

```python
def _extract_pdf_text_fallback(self, pdf_path):
    """Extract all text lines from PDF without table structure"""
    # Extracts text from all pages
    # Creates DataFrame with 'text_line' column
    # Returns 34 lines for CH_HFA001.pdf
```

### Diagnostic Tool

Location: [debug_pdf.py](DerivativeMill/debug_pdf.py)

- Analyzes PDF structure
- Shows content types
- Provides recommendations
- Helps troubleshoot issues

## Best Practices

1. **Always run diagnostic first** for new supplier PDFs
2. **Understand your PDF type** before expecting results
3. **Use templates for patterned data** (OCR templates)
4. **Use manual mapping for random text**
5. **Test with small sample** before production

## Examples

### Example 1: Standard Invoice (Has Tables)

```
PDF: invoice.pdf
Diagnostic: Tables found: 1
App Result: Automatic column extraction
Action: Just load and map!
```

### Example 2: Text-Based Invoice (Your Case)

```
PDF: CH_HFA001.pdf
Diagnostic: No tables, but 1218 chars text
App Result: text_line column with 34 lines
Action: Create OCR template or manual mapping
```

### Example 3: Scanned Invoice

```
PDF: scanned_invoice.pdf
Diagnostic: Scanned image, no text
App Result: OCR extraction with template
Action: Use create_ocr_template.py
```

## Next Steps

### For Testing:
1. Load CH_HFA001.pdf in the app
2. See `text_line` column with extracted text
3. Try mapping it to your fields

### For Production:
1. Create OCR templates for your suppliers
2. Test extraction accuracy
3. Deploy and use in production

### For Multiple Suppliers:
1. Diagnose each supplier's PDF format
2. Create templates as needed
3. Store in `ocr/templates/`
4. Reference by supplier name

---

**Status:** PDF extraction now handles all 3 PDF types
- ✓ Tables (pdfplumber)
- ✓ Text without tables (fallback)
- ✓ Scanned images (OCR)

**Next:** Test with your CH_HFA001.pdf invoice
