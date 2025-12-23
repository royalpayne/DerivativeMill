"""
OCR Processor - Main entry point for document processing.
Uses Tesseract OCR for text extraction and custom extractors for data parsing.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import subprocess

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from .models import (
    DocumentResult, InvoiceData, PackingListData, BillOfLadingData
)
from .extractors import InvoiceExtractor, PackingListExtractor, BOLExtractor


class OCRProcessor:
    """
    Main processor for OCR document extraction.

    Usage:
        processor = OCRProcessor()
        result = processor.process("invoice.pdf")

        # Access data
        df = result.line_items  # Pandas DataFrame
        print(result.vendor)
        print(result.totals)
    """

    def __init__(self, tesseract_path: Optional[str] = None, language: str = 'eng'):
        """
        Initialize OCR Processor.

        Args:
            tesseract_path: Path to tesseract executable. Auto-detected if None.
            language: OCR language code (default: 'eng')
        """
        self.language = language
        self.tesseract_path = tesseract_path

        # Initialize extractors
        self.invoice_extractor = InvoiceExtractor()
        self.packing_extractor = PackingListExtractor()
        self.bol_extractor = BOLExtractor()

        # Configure Tesseract path
        self._configure_tesseract()

    def _configure_tesseract(self):
        """Configure Tesseract OCR path."""
        if not TESSERACT_AVAILABLE:
            return

        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        else:
            # Auto-detect common paths
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract'
            ]
            for path in common_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Check if all required dependencies are available.

        Returns:
            Tuple of (all_ok, list of missing dependencies)
        """
        missing = []

        if not TESSERACT_AVAILABLE:
            missing.append("pytesseract (pip install pytesseract)")

        if not PDF2IMAGE_AVAILABLE and not PYMUPDF_AVAILABLE:
            missing.append("pdf2image or PyMuPDF (pip install pdf2image or pip install pymupdf)")

        # Check Tesseract installation
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                missing.append("Tesseract OCR not installed or not in PATH")

        return len(missing) == 0, missing

    def process(self, file_path: str, detect_documents: bool = True) -> DocumentResult:
        """
        Process a PDF or image file and extract structured data.

        Args:
            file_path: Path to PDF or image file
            detect_documents: Auto-detect document types (invoice, packing list, BOL)

        Returns:
            DocumentResult with extracted data
        """
        result = DocumentResult(source_file=file_path)

        # Check file exists
        if not os.path.exists(file_path):
            result.error_message = f"File not found: {file_path}"
            return result

        # Check dependencies
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            result.error_message = f"Missing dependencies: {', '.join(missing)}"
            return result

        try:
            # Extract text from document
            text, page_count = self._extract_text(file_path)
            result.page_count = page_count

            if not text or not text.strip():
                result.error_message = "No text extracted from document"
                return result

            # Detect document types
            if detect_documents:
                result.document_types = self._detect_document_types(text)
            else:
                result.document_types = ['invoice']  # Default

            # Extract data based on detected types
            if 'invoice' in result.document_types:
                result.invoice = self.invoice_extractor.extract(text)

            if 'packing_list' in result.document_types:
                result.packing_list = self.packing_extractor.extract(text)

            if 'bill_of_lading' in result.document_types:
                result.bill_of_lading = self.bol_extractor.extract(text)

            result.success = True

        except Exception as e:
            result.error_message = f"Processing error: {str(e)}"

        return result

    def _extract_text(self, file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF or image file.

        Returns:
            Tuple of (extracted_text, page_count)
        """
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']:
            text = self._extract_from_image(file_path)
            return text, 1
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    def _extract_from_pdf(self, pdf_path: str) -> Tuple[str, int]:
        """Extract text from PDF using Tesseract OCR."""
        all_text = []
        page_count = 0

        # Try PyMuPDF first (faster for text-based PDFs)
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(pdf_path)
                page_count = len(doc)

                for page_num in range(page_count):
                    page = doc[page_num]

                    # Try direct text extraction first
                    text = page.get_text()

                    if text.strip():
                        all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                    else:
                        # Fall back to OCR for scanned pages
                        pix = page.get_pixmap(dpi=300)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_text = pytesseract.image_to_string(img, lang=self.language)
                        all_text.append(f"--- Page {page_num + 1} ---\n{ocr_text}")

                doc.close()
                return '\n'.join(all_text), page_count

            except Exception:
                pass  # Fall through to pdf2image

        # Use pdf2image + Tesseract
        if PDF2IMAGE_AVAILABLE:
            try:
                images = pdf2image.convert_from_path(pdf_path, dpi=300)
                page_count = len(images)

                for i, img in enumerate(images):
                    text = pytesseract.image_to_string(img, lang=self.language)
                    all_text.append(f"--- Page {i + 1} ---\n{text}")

                return '\n'.join(all_text), page_count

            except Exception as e:
                raise RuntimeError(f"PDF extraction failed: {e}")

        raise RuntimeError("No PDF processing library available")

    def _extract_from_image(self, image_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        img = Image.open(image_path)

        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')

        text = pytesseract.image_to_string(img, lang=self.language)
        return text

    def _detect_document_types(self, text: str) -> List[str]:
        """
        Detect what types of documents are present in the text.

        Returns:
            List of detected types: 'invoice', 'packing_list', 'bill_of_lading'
        """
        text_lower = text.lower()
        detected = []

        # Invoice indicators
        invoice_patterns = [
            r'commercial\s*invoice',
            r'invoice\s*no',
            r'invoice\s*number',
            r'invoice\s*date',
            r'proforma\s*invoice',
            r'tax\s*invoice',
            r'unit\s*price',
            r'total\s*amount',
            r'fob\s*value',
            r'cif\s*value'
        ]
        for pattern in invoice_patterns:
            if re.search(pattern, text_lower):
                detected.append('invoice')
                break

        # Packing list indicators
        packing_patterns = [
            r'packing\s*list',
            r'packing\s*slip',
            r'gross\s*weight',
            r'net\s*weight',
            r'carton\s*no',
            r'package\s*no',
            r'number\s*of\s*packages',
            r'cbm',
            r'measurement'
        ]
        for pattern in packing_patterns:
            if re.search(pattern, text_lower):
                detected.append('packing_list')
                break

        # Bill of Lading indicators
        bol_patterns = [
            r'bill\s*of\s*lading',
            r'b/?l\s*no',
            r'ocean\s*bill',
            r'master\s*b/?l',
            r'house\s*b/?l',
            r'shipper',
            r'consignee',
            r'notify\s*party',
            r'port\s*of\s*loading',
            r'port\s*of\s*discharge',
            r'vessel\s*name',
            r'voyage\s*no'
        ]
        for pattern in bol_patterns:
            if re.search(pattern, text_lower):
                detected.append('bill_of_lading')
                break

        # Default to invoice if nothing detected
        if not detected:
            detected.append('invoice')

        return detected

    def process_text(self, text: str, document_type: str = 'invoice') -> DocumentResult:
        """
        Process already-extracted text (skip OCR step).
        Useful for testing or when text is already available.

        Args:
            text: Raw text to process
            document_type: Type of document ('invoice', 'packing_list', 'bill_of_lading')

        Returns:
            DocumentResult with extracted data
        """
        result = DocumentResult(source_file="<text_input>")
        result.document_types = [document_type]

        try:
            if document_type == 'invoice':
                result.invoice = self.invoice_extractor.extract(text)
            elif document_type == 'packing_list':
                result.packing_list = self.packing_extractor.extract(text)
            elif document_type == 'bill_of_lading':
                result.bill_of_lading = self.bol_extractor.extract(text)

            result.success = True

        except Exception as e:
            result.error_message = f"Extraction error: {str(e)}"

        return result

    def get_raw_text(self, file_path: str) -> str:
        """
        Extract raw OCR text without parsing.
        Useful for debugging or custom processing.

        Args:
            file_path: Path to PDF or image

        Returns:
            Raw extracted text
        """
        text, _ = self._extract_text(file_path)
        return text
