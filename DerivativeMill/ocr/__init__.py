"""
OCR Module for Scanned Invoice Processing

Provides functionality to:
- Detect scanned PDFs vs digital PDFs
- Extract text from scanned invoices using pytesseract
- Match extracted text to supplier templates
- Return structured Part Number and Value data
"""

from .scanned_pdf import is_scanned_pdf, pdf_to_images
from .field_detector import extract_fields_from_text, SupplierTemplate
from .ocr_extract import extract_from_scanned_invoice, extract_with_confidence, preview_extraction

__all__ = [
    'is_scanned_pdf',
    'pdf_to_images',
    'extract_fields_from_text',
    'SupplierTemplate',
    'extract_from_scanned_invoice',
    'extract_with_confidence',
    'preview_extraction',
]
