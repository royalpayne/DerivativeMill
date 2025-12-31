"""
Base Template Class for Invoice OCR Extraction
All invoice templates should inherit from this class.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple


class BaseTemplate(ABC):
    """
    Abstract base class for invoice OCR templates.
    
    To create a new template:
    1. Create a new file in the templates folder
    2. Inherit from BaseTemplate
    3. Implement all abstract methods
    4. Register in templates/__init__.py
    """
    
    # Template metadata
    name: str = "Base Template"
    description: str = "Base template class"
    client: str = "Unknown"
    version: str = "1.0.0"
    
    # Enable/disable this template
    enabled: bool = True
    
    # CSV columns this template produces (in addition to standard columns)
    extra_columns: List[str] = []
    
    # Standard columns all templates must produce
    STANDARD_COLUMNS = [
        'invoice_number',
        'project_number', 
        'part_number',
        'quantity',
        'total_price'
    ]
    
    @abstractmethod
    def can_process(self, text: str) -> bool:
        """
        Check if this template can process the given PDF text.
        Returns True if this template recognizes the invoice format.
        
        Args:
            text: Full text extracted from the PDF
            
        Returns:
            bool: True if this template should be used
        """
        pass
    
    @abstractmethod
    def extract_invoice_number(self, text: str) -> str:
        """
        Extract the invoice number from the PDF text.
        
        Args:
            text: Full text extracted from the PDF
            
        Returns:
            str: Invoice number or 'UNKNOWN'
        """
        pass
    
    @abstractmethod
    def extract_project_number(self, text: str) -> str:
        """
        Extract the project number from the PDF text.
        
        Args:
            text: Full text extracted from the PDF
            
        Returns:
            str: Project number or 'UNKNOWN'
        """
        pass
    
    @abstractmethod
    def extract_line_items(self, text: str) -> List[Dict]:
        """
        Extract line items from the PDF text.

        Each line item should be a dict with at least:
        - part_number: str
        - quantity: str (numeric)
        - total_price: str (numeric, in USD)

        Additional fields can be added based on extra_columns.

        Args:
            text: Full text extracted from the PDF

        Returns:
            List[Dict]: List of line item dictionaries
        """
        pass

    def extract_manufacturer_name(self, text: str) -> str:
        """
        Extract the manufacturer/supplier name from the PDF text.
        Override in subclass to implement manufacturer detection.

        Args:
            text: Full text extracted from the PDF

        Returns:
            str: Manufacturer name or empty string if not found
        """
        return ""
    
    def is_packing_list(self, text: str) -> bool:
        """
        Check if the document is a packing list (should be skipped).
        Override in subclass if needed.
        
        Args:
            text: Full text extracted from the PDF
            
        Returns:
            bool: True if this is a packing list
        """
        return 'packing list' in text.lower()
    
    def get_confidence_score(self, text: str) -> float:
        """
        Return a confidence score for how well this template matches.
        Used when multiple templates claim they can process a document.
        Higher score wins.
        
        Args:
            text: Full text extracted from the PDF
            
        Returns:
            float: Confidence score 0.0 to 1.0
        """
        return 0.5 if self.can_process(text) else 0.0
    
    def pre_process_text(self, text: str) -> str:
        """
        Pre-process text before extraction.
        Override to add custom text cleaning.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            str: Cleaned text
        """
        return text
    
    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """
        Post-process extracted items.
        Override to add validation, deduplication, etc.
        
        Args:
            items: List of extracted line items
            
        Returns:
            List[Dict]: Processed items
        """
        return items
    
    def get_all_columns(self) -> List[str]:
        """Get all columns this template produces."""
        return self.STANDARD_COLUMNS + self.extra_columns
    
    def extract_all(self, text: str, tables: List[List[List[str]]] = None) -> Tuple[str, str, List[Dict]]:
        """
        Main extraction method - extracts everything from the text and optional tables.

        Args:
            text: Full text extracted from the PDF
            tables: Optional list of tables from pdfplumber. Each table is a list of rows,
                   each row is a list of cell values (strings).

        Returns:
            Tuple of (invoice_number, project_number, line_items)
            Note: Each line item includes 'manufacturer_name' if detected
        """
        processed_text = self.pre_process_text(text)

        invoice_number = self.extract_invoice_number(processed_text)
        project_number = self.extract_project_number(processed_text)
        manufacturer_name = self.extract_manufacturer_name(processed_text)

        # Try table-based extraction first if tables are provided and template supports it
        if tables and hasattr(self, 'extract_from_tables') and callable(self.extract_from_tables):
            items = self.extract_from_tables(tables, processed_text)
            if items:  # If table extraction returned items, use those
                # Add manufacturer name to each item if detected
                if manufacturer_name:
                    for item in items:
                        if 'manufacturer_name' not in item or not item['manufacturer_name']:
                            item['manufacturer_name'] = manufacturer_name
                items = self.post_process_items(items)
                return invoice_number, project_number, items

        # Fall back to text-based extraction
        items = self.extract_line_items(processed_text)

        # Add manufacturer name to each item if detected
        if manufacturer_name:
            for item in items:
                if 'manufacturer_name' not in item or not item['manufacturer_name']:
                    item['manufacturer_name'] = manufacturer_name

        items = self.post_process_items(items)

        return invoice_number, project_number, items

    def extract_from_tables(self, tables: List[List[List[str]]], text: str) -> List[Dict]:
        """
        Extract line items from table data instead of text.
        Override this method in templates that want to use table detection.

        Tables are structured as: tables[table_index][row_index][column_index]
        Each cell is a string (may be None for empty cells).

        Args:
            tables: List of tables from pdfplumber
            text: Full text for reference (header detection, etc.)

        Returns:
            List[Dict]: Extracted line items, or empty list if table extraction
                       should not be used (falls back to text extraction)
        """
        # Default implementation: return empty to use text extraction
        return []

    def detect_table_header_row(self, table: List[List[str]], expected_headers: List[str]) -> int:
        """
        Utility method to find the header row in a table.

        Args:
            table: A single table (list of rows)
            expected_headers: List of header strings to look for (case-insensitive)

        Returns:
            int: Row index of header, or -1 if not found
        """
        if not table:
            return -1

        expected_lower = [h.lower() for h in expected_headers]

        for row_idx, row in enumerate(table):
            if not row:
                continue
            row_text = ' '.join(str(cell or '').lower() for cell in row)
            matches = sum(1 for h in expected_lower if h in row_text)
            if matches >= 2:  # At least 2 expected headers found
                return row_idx

        return -1

    def parse_table_rows(self, table: List[List[str]], header_row: int,
                         column_mapping: Dict[str, int]) -> List[Dict]:
        """
        Utility method to parse table rows into dictionaries.

        Args:
            table: A single table (list of rows)
            header_row: Index of the header row
            column_mapping: Dict mapping field names to column indices

        Returns:
            List[Dict]: List of parsed rows
        """
        items = []
        for row_idx in range(header_row + 1, len(table)):
            row = table[row_idx]
            if not row or all(not cell for cell in row):
                continue

            item = {}
            for field, col_idx in column_mapping.items():
                if col_idx < len(row):
                    value = row[col_idx]
                    item[field] = str(value).strip() if value else ''

            # Only add if we have at least some data
            if any(item.values()):
                items.append(item)

        return items
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name} v{self.version}>"
