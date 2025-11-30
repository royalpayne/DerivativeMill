"""
OCR Extraction Pipeline

Main entry point for extracting data from scanned invoices using pytesseract.
"""

import pytesseract
import pandas as pd
from .scanned_pdf import is_scanned_pdf, pdf_to_images
from .field_detector import extract_fields_from_text


def extract_from_scanned_invoice(pdf_path, supplier_name='default', progress_callback=None):
    """
    Extract Part Number and Value data from a scanned invoice PDF.

    Complete pipeline:
    1. Check if PDF is scanned
    2. Convert PDF to images
    3. Run OCR on first page
    4. Extract fields using pattern matching
    5. Return structured DataFrame

    Args:
        pdf_path (str): Path to scanned PDF invoice
        supplier_name (str): Supplier name for template selection (default='default')
        progress_callback (callable): Optional callback for progress updates

    Returns:
        tuple: (DataFrame with extracted data, dict with metadata)
               {
                   'columns': ['part_number', 'value'],
                   'rows': N,
                   'source': 'scanned_pdf',
                   'supplier': supplier_name,
                   'raw_text': extracted_text,
                   'method': 'pytesseract'
               }

    Raises:
        Exception: If extraction fails
    """
    try:
        # Step 1: Verify it's a scanned PDF
        if not is_scanned_pdf(pdf_path):
            raise ValueError("PDF appears to be digital. Use pdfplumber table extraction instead.")

        if progress_callback:
            progress_callback("Converting PDF to images...")

        # Step 2: Convert PDF to images (first page only for MVP)
        images = pdf_to_images(pdf_path, dpi=150, first_page=1, last_page=1)

        if not images:
            raise ValueError("Could not convert PDF to images")

        if progress_callback:
            progress_callback("Running OCR on invoice image...")

        # Step 3: Extract text using pytesseract
        raw_text = pytesseract.image_to_string(images[0], lang='eng')

        if not raw_text or not raw_text.strip():
            raise ValueError("OCR found no text in image. Check image quality and DPI.")

        if progress_callback:
            progress_callback("Extracting Part Number and Value fields...")

        # Step 4: Extract fields using template
        extracted_fields = extract_fields_from_text(raw_text, supplier_name)

        if not extracted_fields:
            raise ValueError(f"No Part Number/Value combinations found. Check supplier template '{supplier_name}'.")

        # Step 5: Create DataFrame
        df = pd.DataFrame(extracted_fields)

        # Ensure we have the expected columns
        if 'part_number' not in df.columns:
            df['part_number'] = ''
        if 'value' not in df.columns:
            df['value'] = ''

        metadata = {
            'columns': ['part_number', 'value'],
            'rows': len(df),
            'source': 'scanned_pdf',
            'supplier': supplier_name,
            'raw_text': raw_text,
            'method': 'pytesseract',
            'success': True,
        }

        return df, metadata

    except Exception as e:
        raise Exception(f"Scanned invoice extraction failed: {str(e)}")


def extract_with_confidence(pdf_path, supplier_name='default'):
    """
    Extract data and include confidence metrics.

    For MVP, confidence is based on:
    - Number of fields extracted
    - Consistency of data patterns

    Args:
        pdf_path (str): Path to scanned PDF
        supplier_name (str): Supplier template name

    Returns:
        dict: {
            'data': DataFrame,
            'confidence': float (0.0-1.0),
            'warnings': list,
            'metadata': dict
        }
    """
    try:
        df, metadata = extract_from_scanned_invoice(pdf_path, supplier_name)

        warnings = []
        confidence = 0.8  # Start with 80%

        # Check for empty fields
        empty_part_numbers = df['part_number'].isna().sum() + (df['part_number'] == '').sum()
        empty_values = df['value'].isna().sum() + (df['value'] == '').sum()

        if empty_part_numbers > 0:
            warnings.append(f"{empty_part_numbers} rows missing Part Number")
            confidence -= 0.1

        if empty_values > 0:
            warnings.append(f"{empty_values} rows missing Value")
            confidence -= 0.1

        # Check for suspicious patterns
        if len(df) == 0:
            confidence = 0.0
            warnings.append("No data extracted")

        elif len(df) > 1000:
            warnings.append(f"Very large number of rows ({len(df)}). May include non-data text.")
            confidence -= 0.15

        # Ensure confidence is in range
        confidence = max(0.0, min(1.0, confidence))

        return {
            'data': df,
            'confidence': confidence,
            'warnings': warnings,
            'metadata': metadata,
        }

    except Exception as e:
        return {
            'data': None,
            'confidence': 0.0,
            'warnings': [str(e)],
            'metadata': {'error': str(e), 'success': False},
        }


def preview_extraction(pdf_path, max_lines=20):
    """
    Preview OCR results before full extraction.

    Useful for debugging and verifying OCR accuracy.

    Args:
        pdf_path (str): Path to PDF
        max_lines (int): Maximum lines of text to show

    Returns:
        dict: {
            'is_scanned': bool,
            'text_preview': str,
            'line_count': int,
            'char_count': int
        }
    """
    try:
        is_scanned = is_scanned_pdf(pdf_path)

        images = pdf_to_images(pdf_path, dpi=150, first_page=1, last_page=1)
        raw_text = pytesseract.image_to_string(images[0], lang='eng')

        lines = raw_text.split('\n')
        preview_lines = lines[:max_lines]
        preview_text = '\n'.join(preview_lines)

        if len(lines) > max_lines:
            preview_text += f'\n\n... ({len(lines) - max_lines} more lines)'

        return {
            'is_scanned': is_scanned,
            'text_preview': preview_text,
            'line_count': len(lines),
            'char_count': len(raw_text),
        }

    except Exception as e:
        return {
            'is_scanned': None,
            'text_preview': f'Error: {str(e)}',
            'line_count': 0,
            'char_count': 0,
        }
