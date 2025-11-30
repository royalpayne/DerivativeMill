#!/usr/bin/env python3
"""
Extract Part Numbers and Values from AROMATE Invoice

Your AROMATE invoice has clear patterns:
  1-1268 SKU# 1562485 @60P CS @1.50K GS @2.50 KGS
  1-420 SKU# 2641486 @36P CS @1.23K GS @1.53 KGS
  ...

We'll use regex to extract SKU# and the cost/weight values.
"""

import re
import pandas as pd
import pdfplumber

def extract_aromate_data(pdf_path):
    """
    Extract SKU and cost data from AROMATE invoice

    Returns:
        DataFrame with columns: line_item, sku, quantity, weight
    """

    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    # Pattern explanation:
    # 1-(\d+)           = Matches line number like "1-1268"
    # \s+SKU#\s*(\d+)   = Matches "SKU# 1562485"
    # @(\d+)P CS        = Matches quantity like "@60P CS"
    # @([\d.]+)K GS     = Matches weight like "@1.50K GS" or "@2.50 KGS"

    pattern = r'1-(\d+)\s+SKU#\s*(\d+)\s+@(\d+)P CS\s+@([\d.]+)K'

    matches = re.findall(pattern, text)

    if not matches:
        print("❌ No matches found. Checking available text...")
        # Show what's in the PDF for debugging
        lines = text.split('\n')
        print("\nText lines that might contain data:")
        for i, line in enumerate(lines):
            if 'SKU' in line or '1-' in line:
                print(f"{i}: {line}")
        return None

    # Convert matches to DataFrame
    data = []
    for line_item, sku, qty, weight in matches:
        data.append({
            'line_item': line_item,
            'part_number': sku,
            'quantity_per_case': int(qty),
            'weight_kg': float(weight)
        })

    df = pd.DataFrame(data)
    return df

# Test it
if __name__ == '__main__':
    print("="*70)
    print("AROMATE Invoice Data Extraction")
    print("="*70)

    df = extract_aromate_data('Input/CH_HFA001.pdf')

    if df is not None:
        print(f"\n✅ Extracted {len(df)} items!")
        print("\nData:")
        print(df.to_string(index=False))

        print("\n" + "="*70)
        print("This shows:")
        print("  - line_item: Item number (1-XXXX)")
        print("  - part_number: SKU# XXXXXXX")
        print("  - quantity_per_case: Units per case")
        print("  - weight_kg: Total weight in kg")

        print("\n" + "="*70)
        print("NEXT STEP:")
        print("In the app, when you load this PDF:")
        print("  1. You get a 'text_line' column with all extracted text")
        print("  2. Instead of using that, you could:")
        print("     - Parse with regex (like this script)")
        print("     - Or manually map the data")
        print("     - Or create a more sophisticated extractor")
    else:
        print("Could not extract data")
