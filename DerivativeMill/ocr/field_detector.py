"""
Field Detection and Supplier Templates

Provides supplier-specific templates for extracting Part Number and Value fields
from OCR-extracted text using pattern matching.
"""

import re
import json
from pathlib import Path


class SupplierTemplate:
    """
    Template for extracting Part Number and Value from invoice text.

    Each supplier may have a different invoice format. This class defines
    regex patterns and field positions for a specific supplier.
    """

    def __init__(self, supplier_name, patterns=None, field_positions=None):
        """
        Initialize a supplier template.

        Args:
            supplier_name (str): Name of supplier (e.g., "ACME Corp")
            patterns (dict): Regex patterns for field detection
            field_positions (dict): Optional positional info for fields
        """
        self.supplier_name = supplier_name
        self.patterns = patterns or self._default_patterns()
        self.field_positions = field_positions or {}

    def _default_patterns(self):
        """Default patterns that work for most invoices."""
        return {
            'part_number_header': r'(part\s*(?:number|num|no|#|code|id)|sku|product\s*(?:number|id|code)|item\s*(?:number|code))',
            'part_number_value': r'([A-Z0-9\-_\.]{3,25})',
            'value_header': r'(price|unit\s*price|value|amount|cost|rate|total|invoice|qty|quantity)',
            'value_pattern': r'\$?\s*(\d{1,10}(?:[,\.]?\d{1,3})*(?:\.\d{2})?)',
            'quantity_pattern': r'qty:?\s*(\d+)',
            'description': r'(description|desc|item\s*description)',
        }

    def extract(self, text):
        """
        Extract Part Number and Value entries from OCR text.

        Args:
            text (str): OCR-extracted text from invoice

        Returns:
            list: List of dicts with {'part_number': '...', 'value': '...', 'quantity': ...}

        Raises:
            Exception: If extraction fails
        """
        try:
            lines = text.split('\n')
            extracted_data = []

            # Find header line (contains "Part Number" or "Value")
            header_idx = self._find_header_line(lines)

            if header_idx is None:
                # Fallback: extract without header detection
                return self._extract_without_header(text)

            # Extract data lines after header
            part_col = None
            value_col = None

            for idx in range(header_idx + 1, len(lines)):
                line = lines[idx].strip()

                if not line:
                    continue

                # Try to extract Part Number and Value from this line
                part_num = self._extract_part_number(line)
                value = self._extract_value(line)

                if part_num or value:
                    extracted_data.append({
                        'part_number': part_num or '',
                        'value': value or '',
                        'raw_line': line
                    })

            return extracted_data

        except Exception as e:
            raise Exception(f"Field extraction error: {str(e)}")

    def _find_header_line(self, lines):
        """Find the line containing column headers."""
        header_pattern = self.patterns['part_number_header']

        for idx, line in enumerate(lines):
            if re.search(header_pattern, line, re.IGNORECASE):
                return idx

        return None

    def _extract_part_number(self, text):
        """Extract part number from a line of text."""
        # Look for patterns like "ABC-123" or "SKU12345"
        pattern = self.patterns['part_number_value']
        match = re.search(pattern, text)

        if match:
            return match.group(1).strip()

        return None

    def _extract_value(self, text):
        """Extract numeric value (price/amount) from text."""
        pattern = self.patterns['value_pattern']
        matches = re.findall(pattern, text)

        if matches:
            # Return the first numeric value found
            value_str = matches[0]
            # Remove commas and spaces
            value_str = value_str.replace(',', '').replace(' ', '')

            try:
                return float(value_str)
            except ValueError:
                return None

        return None

    def _extract_without_header(self, text):
        """Fallback extraction without header detection."""
        lines = text.split('\n')
        extracted_data = []

        for line in lines:
            line = line.strip()

            if not line or len(line) < 5:
                continue

            part_num = self._extract_part_number(line)
            value = self._extract_value(line)

            # Only add lines that have at least a part number or value
            if part_num and value:
                extracted_data.append({
                    'part_number': part_num,
                    'value': value,
                    'raw_line': line
                })

        return extracted_data

    def to_dict(self):
        """Serialize template to dict for JSON storage."""
        return {
            'supplier_name': self.supplier_name,
            'patterns': self.patterns,
            'field_positions': self.field_positions,
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize template from dict."""
        return cls(
            supplier_name=data['supplier_name'],
            patterns=data.get('patterns'),
            field_positions=data.get('field_positions'),
        )


class TemplateManager:
    """
    Manages supplier templates for field extraction.

    Stores and retrieves supplier-specific extraction templates.
    """

    def __init__(self, templates_dir=None):
        """
        Initialize template manager.

        Args:
            templates_dir (str): Directory to store/load templates (default: ./ocr/templates/)
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / 'templates'

        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.templates = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Load all templates from disk."""
        for template_file in self.templates_dir.glob('*.json'):
            try:
                with open(template_file) as f:
                    data = json.load(f)
                    template = SupplierTemplate.from_dict(data)
                    self.templates[template.supplier_name] = template
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")

    def get_template(self, supplier_name):
        """
        Get a template by supplier name.

        Returns default template if supplier not found.

        Args:
            supplier_name (str): Name of supplier

        Returns:
            SupplierTemplate: The template (or default)
        """
        if supplier_name in self.templates:
            return self.templates[supplier_name]

        # Return default template
        return SupplierTemplate('default')

    def save_template(self, template):
        """
        Save a template to disk.

        Args:
            template (SupplierTemplate): Template to save
        """
        template_file = self.templates_dir / f"{template.supplier_name}.json"

        with open(template_file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)

        self.templates[template.supplier_name] = template

    def list_templates(self):
        """
        List all available templates.

        Returns:
            list: List of supplier names
        """
        return list(self.templates.keys())


# Global template manager instance
_template_manager = None


def get_template_manager():
    """Get or create the global template manager instance."""
    global _template_manager

    if _template_manager is None:
        _template_manager = TemplateManager()

    return _template_manager


def extract_fields_from_text(text, supplier_name='default'):
    """
    Extract Part Number and Value fields from OCR text.

    Args:
        text (str): OCR-extracted text from invoice
        supplier_name (str): Name of supplier (for template selection)

    Returns:
        list: List of dicts with extracted fields

    Raises:
        Exception: If extraction fails
    """
    manager = get_template_manager()
    template = manager.get_template(supplier_name)
    return template.extract(text)
