"""
Hebei Shinyee Trade Co Template

Auto-generated template for invoices from Hebei Shinyee Trade Co.
Generated: 2025-12-26 00:30:10
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class HebeiShinyeeTemplate(BaseTemplate):
    """Template for Hebei Shinyee Trade Co invoices."""

    name = "Hebei Shinyee Trade Co"
    description = "Invoices from Hebei Shinyee Trade Co"
    client = "Sigma Corportation"
    version = "1.0.0"
    enabled = True

    extra_columns = ['po_number', 'unit_price', 'description', 'country_origin']

    # Keywords to identify this supplier
    SUPPLIER_KEYWORDS = [
        "hebei shinyee trade co",
        "huahai universal plaza",
        "xinhua road,shijiazhuang",
        "商 业 发 票",
        "commercial invoice"
    ]

    def can_process(self, text: str) -> bool:
        """Check if this is a Hebei Shinyee Trade Co invoice."""
        text_lower = text.lower()
        for keyword in self.SUPPLIER_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0
        return 0.8

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number using regex patterns."""
        patterns = [
            r'(SH\d+\-\d+)',  # Direct match for SH pattern first
            r'Invoice No\.\s*Date\s*(SH\d+\-\d+)',  # Invoice No. Date SH25-3081
            r'No\.\s+Date\s+(SH\d+\-\d+)',  # No. Date SH25-3081
            r'Invoice No\.\s*(SH\d+\-\d+)'  # Invoice No. SH25-3081
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract PO/project number."""
        patterns = [
            r'S/C No\.\s*L/C No\.\s*([A-Z0-9\-]+)',
            r'S/C No\.\s+([A-Z0-9\-]+)',
            r'(SH\d+\-\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Return the manufacturer name."""
        return "HEBEI SHINYEE TRADE CO"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        items = []
        
        # Pattern for line items with part number, unit price, quantity, and amount
        item_pattern = r'(\d+\-[A-Z0-9\-]+)\s+([0-9.]+)\s+(\d+)\s+USD\s+([0-9.]+)'
        
        matches = re.findall(item_pattern, text)
        
        for match in matches:
            part_number, unit_price, quantity, total_price = match
            
            item = {
                'part_number': part_number.strip(),
                'quantity': int(quantity),
                'unit_price': float(unit_price),
                'total_price': float(total_price),
                'description': 'CAST IRON PUMP COMPONENTS',
                'po_number': self.extract_project_number(text),
                'country_origin': 'CHINA'
            }
            items.append(item)

        return items

    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """Post-process - deduplicate and validate."""
        if not items:
            return items

        seen = set()
        unique_items = []

        for item in items:
            key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"
            if key not in seen:
                seen.add(key)
                # Add country of origin
                item['country_origin'] = 'CHINA'
                unique_items.append(item)

        return unique_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is only a packing list."""
        text_lower = text.lower()
        # Only consider it a packing list if it has packing list content but NO commercial invoice content
        has_packing_list = '装 箱 单' in text or 'packing list' in text_lower
        has_commercial_invoice = '商 业 发 票' in text or 'commercial invoice' in text_lower
        
        # If it has both, it's a combined document - process it as an invoice
        # Only skip if it's ONLY a packing list
        if has_packing_list and not has_commercial_invoice:
            return True
        return False