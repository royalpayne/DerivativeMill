"""
Scanned PDF Detection and Image Conversion

Detects whether a PDF is scanned (image-based) or digital (text-based),
and provides image conversion for OCR processing.
"""

import pdfplumber
from pdf2image import convert_from_path
from pathlib import Path


def is_scanned_pdf(pdf_path):
    """
    Determine if a PDF is scanned (image-based) or digital (text-based).

    A PDF is considered scanned if it contains no extractable text on any page.
    Digital PDFs have searchable/selectable text.

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        bool: True if PDF is scanned, False if digital

    Raises:
        Exception: If PDF cannot be read
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Check first 3 pages for text (optimization for large PDFs)
            pages_to_check = min(3, len(pdf.pages))

            for page_idx in range(pages_to_check):
                page = pdf.pages[page_idx]
                text = page.extract_text()

                if text and text.strip():
                    # Found extractable text = digital PDF
                    return False

            # No text found = scanned PDF
            return True

    except Exception as e:
        raise Exception(f"Cannot determine PDF type: {str(e)}")


def pdf_to_images(pdf_path, dpi=150, first_page=1, last_page=None):
    """
    Convert PDF pages to PIL Image objects for OCR processing.

    Args:
        pdf_path (str): Path to PDF file
        dpi (int): DPI for conversion (higher = better quality, slower)
        first_page (int): First page to convert (1-indexed)
        last_page (int): Last page to convert (None = all pages)

    Returns:
        list: List of PIL Image objects

    Raises:
        Exception: If PDF cannot be converted
    """
    try:
        # pdf2image returns list of PIL Images
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page
        )

        return images

    except Exception as e:
        raise Exception(f"Cannot convert PDF to images: {str(e)}")


def get_pdf_page_count(pdf_path):
    """
    Get the number of pages in a PDF.

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        int: Number of pages

    Raises:
        Exception: If PDF cannot be read
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)

    except Exception as e:
        raise Exception(f"Cannot read PDF: {str(e)}")


def detect_pdf_type(pdf_path):
    """
    Detailed PDF type detection with metadata.

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        dict: {
            'is_scanned': bool,
            'page_count': int,
            'has_text': bool,
            'estimated_dpi': str
        }
    """
    try:
        is_scanned = is_scanned_pdf(pdf_path)
        page_count = get_pdf_page_count(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            has_text = bool(first_page.extract_text(layout=False).strip())

        return {
            'is_scanned': is_scanned,
            'page_count': page_count,
            'has_text': has_text,
            'estimated_dpi': 'Low (scanned at ~100-150 DPI)' if is_scanned else 'N/A (digital)',
            'file_size': Path(pdf_path).stat().st_size,
        }

    except Exception as e:
        return {
            'is_scanned': None,
            'page_count': 0,
            'has_text': False,
            'error': str(e)
        }
