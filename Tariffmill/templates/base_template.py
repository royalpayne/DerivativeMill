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
    
    def extract_all(self, text: str) -> Tuple[str, str, List[Dict]]:
        """
        Main extraction method - extracts everything from the text.

        Args:
            text: Full text extracted from the PDF

        Returns:
            Tuple of (invoice_number, project_number, line_items)
            Note: Each line item includes 'manufacturer_name' if detected
        """
        processed_text = self.pre_process_text(text)

        invoice_number = self.extract_invoice_number(processed_text)
        project_number = self.extract_project_number(processed_text)
        manufacturer_name = self.extract_manufacturer_name(processed_text)
        items = self.extract_line_items(processed_text)

        # Add manufacturer name to each item if detected
        if manufacturer_name:
            for item in items:
                if 'manufacturer_name' not in item or not item['manufacturer_name']:
                    item['manufacturer_name'] = manufacturer_name

        items = self.post_process_items(items)

        return invoice_number, project_number, items
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name} v{self.version}>"
