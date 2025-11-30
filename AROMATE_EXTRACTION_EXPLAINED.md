# AROMATE Invoice Extraction - Complete Explanation

## What Your Invoice Contains

Your AROMATE invoice (CH_HFA001.pdf) has clear, structured data:

```
1-1268 SKU# 1562485 @60P CS @1.50K GS @2.50 KGS
1-420 SKU# 2641486 @36P CS @1.23K GS @1.53 KGS
1-1355 SKU# 2641487 @36P CS @1.23K GS @1.53 KGS
1-440 SKU# 2641488 @36P CS @1.23K GS @1.53 KGS
```

**Fields you need:**
- **Part Number**: SKU# (e.g., 1562485)
- **Value**: Weight or cost (e.g., 1.50K GS)

---

## How text_line Works

When you load the PDF, the fallback returns a `text_line` column:

```
text_line
---
AROMATE INDUSTRIES CO., LTD.
NO.59, LN. 156, ZHONGZHENG 3RD RD., YINGGE DIST., NEW TAIPEI CITY 23942, TAIWAN
(R.O.C.)
SEP.12,2025
2025091201
AS BELOW
-SEE ATTACHED-
YANKEE CANDLE CO., INC.
...
1-1268 SKU# 1562485 @60P CS @1.50K GS @2.50 KGS
1-420 SKU# 2641486 @36P CS @1.23K GS @1.53 KGS
...
TOTAL: 3,483C TNS 155,820P CS 4,626.45K GS 6,558.95 KGS
```

**Problem:** text_line has EVERYTHING - header, shipping info, items, totals

**Solution:** You need to **parse** the lines to find and extract what you need

---

## Three Ways to Extract Part Numbers & Values

### Option 1: Regex Pattern Matching (BEST)

Uses regular expressions to find lines matching your invoice pattern.

**How it works:**
```
Pattern: 1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K

Line:    1-1268 SKU# 1562485 @60P CS @1.50K GS @2.50 KGS
         └─ ┘ └─ ──  └──────┘ └───────  └─────┘
         Line Item  Part #   Qty      Weight
```

**Code:**
```python
import re
pattern = r'1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K'
matches = re.findall(pattern, text)
# Returns: [('1268', '1562485', '60', '1.50'), ...]
```

**Result:**
```
line_item | part_number | quantity_per_case | weight_kg
1268      | 1562485     | 60                | 1.50
420       | 2641486     | 36                | 1.23
1355      | 2641487     | 36                | 1.23
440       | 2641488     | 36                | 1.23
```

**Pros:**
- Fast and accurate
- Exact control over what you extract
- Works for any text-based PDF
- Can handle variations in formatting

**Cons:**
- Need to know the pattern
- Pattern breaks if supplier changes format

**Use this for:** Your AROMATE invoices!

---

### Option 2: OCR Template (For Scanned PDFs)

Uses pytesseract to extract text from **scanned images**, then pattern matching.

**When to use:** For actual scanned invoices (images), not digital PDFs

**How it works:**
```
Scanned PDF (image)
    ↓
[Tesseract OCR] → Extracts text from image
    ↓
[Regex patterns] → Finds SKU# and values
    ↓
[Returns DataFrame]
```

**For your PDF:** Not needed - your PDF is already digital text!

---

### Option 3: Manual Mapping (SIMPLEST)

Just use the text_line column and manually select the rows you need.

**How it works:**
```
1. Load PDF in app
2. Get text_line column with 34 rows
3. Look at which rows have "SKU#"
4. Map those rows to your fields
5. Ignore other rows (header, totals, etc.)
```

**Pros:**
- No coding required
- Works for any invoice format
- You understand exactly what's being mapped

**Cons:**
- Manual work every time
- Slower for large volumes
- Error-prone

---

## Comparison

| Method | Use Case | Accuracy | Speed | Setup Time |
|--------|----------|----------|-------|-----------|
| **Regex** | Digital PDF with clear format | 99% | Fast | 10 min |
| **OCR Template** | Scanned invoices | 85% | Slow | 20 min |
| **Manual** | Any format, one-time | 100% | Very slow | 5 min |

---

## For Your AROMATE Invoices

### Recommended: Use Regex Extraction

Your invoices have a **perfect** pattern:
```
1-XXXX SKU# XXXXXXX @XXP CS @X.XXK GS @X.XX KGS
```

This is ideal for regex matching!

### Implementation

**Script:** [extract_aromate.py](DerivativeMill/extract_aromate.py)

**Run it:**
```bash
cd DerivativeMill
../venv/bin/python extract_aromate.py
```

**Output:**
```
✅ Extracted 4 items!
line_item | part_number | quantity_per_case | weight_kg
1268      | 1562485     | 60                | 1.50
420       | 2641486     | 36                | 1.23
1355      | 2641487     | 36                | 1.23
440       | 2641488     | 36                | 1.23
```

### How to Use in the App

**Option A: Extend the PDF loader**
Modify `extract_pdf_table()` to detect AROMATE PDFs and use regex extraction.

**Option B: External script**
- Load PDF in app (get text_line column)
- Run `extract_aromate.py` separately
- Import the CSV with extracted data

**Option C: Create a custom importer**
Add a specialized "AROMATE" import button that handles both PDF loading and extraction.

---

## Understanding Regex

### Basic Pattern Syntax

| Symbol | Meaning | Example |
|--------|---------|---------|
| `\d` | Any digit | `\d{4}` = 4 digits |
| `\s` | Whitespace | `\s+` = one or more spaces |
| `()` | Capture group | `(\d+)` = capture a number |
| `+` | One or more | `a+` = aaa |
| `*` | Zero or more | `a*` = a or aa or empty |
| `{n}` | Exactly n | `{4}` = exactly 4 |

### Your AROMATE Pattern Explained

```regex
1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K
```

Breaking it down:
```
1-            → Literal "1-"
(\d+)         → Capture: one or more digits (line item)
\s+           → One or more spaces
SKU#          → Literal "SKU#"
\s*           → Zero or more spaces
(\d+)         → Capture: one or more digits (SKU number)
\s+           → One or more spaces
@             → Literal "@"
(\d+)         → Capture: one or more digits (quantity)
P CS          → Literal "P CS"
\s+           → One or more spaces
@             → Literal "@"
([\d.]+)      → Capture: digits and dots (weight)
K             → Literal "K" (at start of "K GS")
```

**Result:** Matches exactly your format and captures 4 groups:
1. Line item number
2. SKU
3. Quantity
4. Weight

---

## Customizing for Other Suppliers

### If Supplier Has Different Format

**Example: Different format**
```
Item: 1268
SKU: 1562485
Qty: 60
Price: $49.99
```

**New pattern:**
```python
pattern = r'Item:\s*(\d+)\s+SKU:\s*(\d+)\s+Qty:\s*(\d+)\s+Price:\s*\$?([\d.]+)'
```

**To create:**
1. Look at actual invoice text
2. Identify the pattern
3. Replace words/numbers with regex symbols
4. Test with your data

### Online Regex Tester

Use https://regex101.com to test patterns:
1. Paste your invoice text
2. Write a pattern
3. See what matches
4. Refine until perfect

---

## Next Steps

### Now:
1. Review the extraction results from `extract_aromate.py`
2. Verify the Part Numbers and Values are correct
3. Decide how to integrate into your workflow

### Integration Options:

**Option 1: Use in App (Recommended)**
- Modify the PDF loader to detect AROMATE
- Automatically use regex extraction instead of pdfplumber
- User clicks "Load Invoice" → Gets correct data automatically

**Option 2: External Script**
- Keep `extract_aromate.py` as standalone tool
- Run before importing to the app
- Export as CSV, then load CSV normally

**Option 3: Manual Processing**
- Load in app (get text_line column)
- Review the 34 lines
- Manually select rows with SKU data
- Save to CSV and process

---

## FAQ

**Q: Why not OCR for your PDF?**
A: OCR is for **scanned images**. Your PDF is already digital text, so OCR would be slower and less accurate than regex on the existing text.

**Q: Can the regex pattern break?**
A: Yes, if AROMATE changes their invoice format. But for now, it works perfectly for your current format.

**Q: How do I handle multiple suppliers?**
A: Create a separate regex pattern for each supplier and detect by "from:" or "supplier:" field in the text.

**Q: Can this be automated in the app?**
A: Yes! Add code to `extract_pdf_table()` to:
1. Extract text from PDF
2. Check if text contains "AROMATE"
3. If yes, use regex extraction instead of table extraction
4. Return the properly structured DataFrame

---

## Code Examples

### Simple Extraction
```python
import re
import pdfplumber

pdf_path = 'Input/CH_HFA001.pdf'
with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[0].extract_text()

pattern = r'1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K'
matches = re.findall(pattern, text)

for line_item, sku, qty, weight in matches:
    print(f"SKU: {sku}, Weight: {weight}kg")
```

### With DataFrame
```python
import re
import pandas as pd
import pdfplumber

with pdfplumber.open('Input/CH_HFA001.pdf') as pdf:
    text = pdf.pages[0].extract_text()

pattern = r'1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K'
matches = re.findall(pattern, text)

df = pd.DataFrame([
    {
        'part_number': sku,
        'weight_kg': float(weight)
    }
    for _, sku, _, weight in matches
])
print(df)
```

### Integrated with App
```python
def extract_pdf_table(self, pdf_path):
    # Existing table extraction...
    # ...

    # Check if AROMATE invoice
    text = self._get_pdf_text(pdf_path)
    if "AROMATE" in text:
        return self._extract_aromate_data(text)

    # Fall back to text extraction
    return self._extract_pdf_text_fallback(pdf_path)

def _extract_aromate_data(self, text):
    pattern = r'1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K'
    matches = re.findall(pattern, text)

    data = [{
        'part_number': sku,
        'value': weight
    } for _, sku, _, weight in matches]

    return pd.DataFrame(data)
```

---

**Summary:**
- Your AROMATE invoices have **perfect** structured data
- Use **regex extraction** (not OCR, not manual)
- Run `extract_aromate.py` to see it working
- Integrate into the app for full automation

Next step: Decide whether to use the script standalone or integrate it into the app!
