#!/usr/bin/env python3
"""
Quick OCR Test Script

Use this to test OCR extraction on your scanned invoices.
Shows extracted text and helps debug pattern matching issues.
"""

import sys
from pathlib import Path
from ocr import preview_extraction, extract_from_scanned_invoice, is_scanned_pdf

def test_ocr():
    """Test OCR on a sample PDF"""

    # Configuration - adjust these to match your test file
    PDF_PATH = "Input/CH_HFA001.pdf"  # Change to your test file
    SUPPLIER_NAME = "AROMATE"  # Change to your supplier template name

    pdf_path = Path(PDF_PATH)

    print("\n" + "="*70)
    print("  OCR EXTRACTION TEST")
    print("="*70)

    # Check if file exists
    if not pdf_path.exists():
        print(f"\n❌ File not found: {PDF_PATH}")
        print("\nUsage:")
        print("  1. Place a scanned PDF in the Input folder")
        print("  2. Update PDF_PATH in this script")
        print("  3. Run: python test_ocr.py")
        return

    pdf_str = str(pdf_path)

    # Step 1: Check if PDF is scanned
    print(f"\n📄 File: {pdf_path.name}")
    print("-" * 70)

    try:
        is_scanned = is_scanned_pdf(pdf_str)
        print(f"Is Scanned: {'✓ Yes (OCR will be used)' if is_scanned else '✗ No (Digital PDF)'}")

        if not is_scanned:
            print("\nℹ️  This PDF has extractable text.")
            print("   Use 'Load Invoice File' in the app to extract with pdfplumber")
            return

    except Exception as e:
        print(f"❌ Error checking PDF type: {e}")
        return

    # Step 2: Preview extracted text
    print(f"\n🔍 PREVIEW OCR TEXT")
    print("-" * 70)

    try:
        preview = preview_extraction(pdf_str, max_lines=40)

        print(f"Total lines: {preview['line_count']}")
        print(f"Total characters: {preview['char_count']}")
        print(f"\nExtracted Text (first 40 lines):")
        print(preview['text_preview'])

    except Exception as e:
        print(f"❌ Error previewing: {e}")
        return

    # Step 3: Try full extraction
    print(f"\n📊 FULL EXTRACTION TEST")
    print("-" * 70)
    print(f"Supplier Template: {SUPPLIER_NAME}")

    try:
        df, metadata = extract_from_scanned_invoice(pdf_str, supplier_name=SUPPLIER_NAME)

        print(f"✅ Extraction successful!")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {metadata['columns']}")
        print(f"\nExtracted Data:")
        print(df.to_string(index=False))

        # Save to CSV for review
        output_file = Path("Input") / f"{pdf_path.stem}_extracted.csv"
        df.to_csv(output_file, index=False)
        print(f"\n💾 Saved to: {output_file}")

    except Exception as e:
        print(f"⚠️  Extraction failed: {e}")
        print("\nThis usually means:")
        print("  - The default pattern doesn't match your invoice format")
        print("  - You need to create a custom template")
        print("\nNext steps:")
        print("  1. Review the text preview above")
        print("  2. Run: python create_ocr_template.py")
        print("  3. This will guide you through creating a custom template")

    print("\n" + "="*70)

if __name__ == '__main__':
    test_ocr()
