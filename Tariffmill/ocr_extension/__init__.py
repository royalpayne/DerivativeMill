"""
OCR Extension - Modular document processing library
Processes PDF documents containing commercial invoices, packing lists, and bills of lading.
Extracts structured data into Pandas DataFrames for easy integration.

Usage:
    from ocr_extension import OCRProcessor

    processor = OCRProcessor()
    result = processor.process("invoice.pdf")

    # Access extracted data
    print(result.vendor)          # Vendor information dict
    print(result.references)       # Reference numbers dict
    print(result.line_items)       # DataFrame of line items
    print(result.totals)           # Totals dict

    # Get combined DataFrame with all data
    df = result.to_combined_dataframe()

Dependencies:
    - pytesseract: pip install pytesseract
    - Tesseract OCR: https://github.com/tesseract-ocr/tesseract
    - pdf2image or PyMuPDF: pip install pdf2image  OR  pip install pymupdf
    - Pillow: pip install Pillow
    - pandas: pip install pandas
"""

from .processor import OCRProcessor
from .models import (
    DocumentResult,
    InvoiceData,
    LineItem,
    InvoiceTotals,
    VendorInfo,
    ReceiverInfo,
    ReferenceNumbers,
    PackingListData,
    BillOfLadingData
)
from .extractors import (
    InvoiceExtractor,
    PackingListExtractor,
    BOLExtractor
)

__version__ = "1.0.0"
__all__ = [
    # Main processor
    'OCRProcessor',

    # Result container
    'DocumentResult',

    # Invoice models
    'InvoiceData',
    'LineItem',
    'InvoiceTotals',
    'VendorInfo',
    'ReceiverInfo',
    'ReferenceNumbers',

    # Other document models
    'PackingListData',
    'BillOfLadingData',

    # Extractors (for advanced usage)
    'InvoiceExtractor',
    'PackingListExtractor',
    'BOLExtractor',
]
