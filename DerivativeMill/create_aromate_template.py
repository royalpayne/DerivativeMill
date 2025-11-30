#!/usr/bin/env python3
"""
Create AROMATE Supplier Template

This creates a specialized template for AROMATE invoices.
Your invoices have a clear pattern:
  1-1268 SKU# 1562485 @60P CS @1.50K GS @2.50 KGS
  1-420 SKU# 2641486 @36P CS @1.23K GS @1.53 KGS
  ...

Pattern breakdown:
  1-XXXX          = Line item number
  SKU# XXXXXXX    = SKU (part number)
  @XXXP CS        = Quantity per case
  @XXXK GS        = Weight in KGS
  @XXX KGS        = Total weight
"""

from ocr import SupplierTemplate, get_template_manager

# Create template for AROMATE
template = SupplierTemplate('AROMATE')

# Customize patterns for AROMATE's specific format
# These patterns are designed to match the exact format of your invoices

template.patterns['part_number_header'] = r'(SKU|PART|ITEM|Product)'
template.patterns['part_number_value'] = r'SKU#\s*(\d+)'  # Match "SKU# 1562485"
template.patterns['value_header'] = r'(CS|KGS|WEIGHT|AMOUNT|PRICE)'
template.patterns['value_pattern'] = r'@(\d+(?:\.\d{2})?)\s*(K GS|CS|KGS)'  # Match "@1.50K GS"

# Save the template
manager = get_template_manager()
manager.save_template(template)

print("""
✅ AROMATE Template Created Successfully!

Template Details:
- Supplier: AROMATE INDUSTRIES CO., LTD.
- Pattern: Line-based format with SKU# and weight indicators
- Extracts: SKU# and weight/quantity values

Location: DerivativeMill/ocr/templates/AROMATE.json

Testing the template...
""")

# Test the template
from ocr import extract_from_scanned_invoice

try:
    df, metadata = extract_from_scanned_invoice('Input/CH_HFA001.pdf', supplier_name='AROMATE')

    if len(df) > 0:
        print(f"\n✓ Extraction successful! Found {len(df)} items")
        print("\nExtracted Data:")
        print(df.to_string(index=False))
        print(f"\nMetadata:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
    else:
        print("⚠️  No data extracted. Pattern may need adjustment.")
        print("\nTip: Review the text preview to verify patterns match:")
        from ocr import preview_extraction
        preview = preview_extraction('Input/CH_HFA001.pdf', max_lines=20)
        print(preview['text_preview'])

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nDebug: Check the extracted text and adjust patterns if needed")
