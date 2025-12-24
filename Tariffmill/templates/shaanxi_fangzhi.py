"""
Shaanxi Fangzhi Trade Co., Ltd. Template

Template for invoices from Shaanxi Fangzhi Trade Co., Ltd. (Xi'an, China)
Uses SmartExtractor for reliable extraction with supplier-specific enhancements.
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from smart_extractor import SmartExtractor
except ImportError:
    try:
        from Tariffmill.smart_extractor import SmartExtractor
    except ImportError:
        SmartExtractor = None


class ShaanxiFangzhiTemplate(BaseTemplate):
    """
    Template for Shaanxi Fangzhi Trade Co., Ltd. invoices.

    These invoices have:
    - Header: Company name, address in Xi'an, China
    - Multiple PO sections within one invoice
    - Columns: Packaged Accessories | ITEMNO | QTY | Restrainer Ring1/Ring2/Rods/Bolts columns
    - ITEMNO is the Sigma part number (shorter code)
    - Packaged Accessories is the description (longer code with suffixes)
    """

    name = "Shaanxi Fangzhi Trade"
    description = "Invoices from Shaanxi Fangzhi Trade Co., Ltd. (Xi'an, China)"
    client = "Sigma Corporation"
    version = "1.0.0"
    enabled = True

    extra_columns = ['po_number', 'unit_price', 'description', 'country_origin']

    def __init__(self):
        super().__init__()
        self._extractor = None
        self._last_result = None

    @property
    def extractor(self):
        """Lazy-load SmartExtractor."""
        if self._extractor is None and SmartExtractor is not None:
            self._extractor = SmartExtractor()
        return self._extractor

    def can_process(self, text: str) -> bool:
        """Check if this is a Shaanxi Fangzhi invoice."""
        text_lower = text.lower()

        # Must contain Shaanxi Fangzhi
        if 'shaanxi fangzhi' not in text_lower and 'fangzhi trade' not in text_lower:
            return False

        # Should be for Sigma Corporation
        if 'sigma' in text_lower or 'messer.sigma' in text_lower:
            return True

        # Or have Xi'an China address
        if "xi'an" in text_lower or 'xian' in text_lower:
            return True

        return False

    def get_confidence_score(self, text: str) -> float:
        """Return high confidence for Shaanxi invoices."""
        if not self.can_process(text):
            return 0.0

        score = 0.7  # High base score for specific supplier match

        text_lower = text.lower()

        if 'shaanxi fangzhi trade' in text_lower:
            score += 0.15
        if 'sigma corporation' in text_lower:
            score += 0.1
        if "xi'an" in text_lower:
            score += 0.05

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        patterns = [
            r'INVOICE\s*(?:NO\.?)?\s*[:\s]*([A-Z]\d+[A-Z]+\d+)',  # I25SFTS11453
            r'Invoice\s*(?:No\.?|#)\s*[:\s]*([A-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract PO number (first one found)."""
        # Shaanxi invoices can have multiple POs - return the first one
        patterns = [
            r'P\.?O\.?\s*#?\s*:?\s*(400\d{5})',
            r'\b(400\d{5})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Return the manufacturer name."""
        return "SHAANXI FANGZHI TRADE CO., LTD."

    def extract_line_items(self, text: str) -> List[Dict]:
        """
        Extract line items using SmartExtractor.

        The SmartExtractor will:
        1. Find part codes and select the database-verified one (ITEMNO)
        2. Put the longer description code in description
        3. Extract quantities and prices
        """
        if not self.extractor:
            return []

        try:
            self._last_result = self.extractor.extract_from_text(text)

            # Extract all PO numbers for assignment
            po_numbers = re.findall(r'\b(400\d{5})\b', text)
            current_po = po_numbers[0] if po_numbers else ""

            items = []
            for item in self._last_result.line_items:
                # Try to find which PO this item belongs to
                # by looking for the PO number near the item in the raw text
                item_po = current_po
                for po in po_numbers:
                    # Check if this PO appears before this line item in text
                    po_pos = text.find(po)
                    item_pos = text.find(item.raw_line)
                    if po_pos >= 0 and item_pos >= 0 and po_pos < item_pos:
                        item_po = po

                items.append({
                    'part_number': item.part_number,
                    'quantity': item.quantity,
                    'total_price': item.total_price,
                    'unit_price': item.unit_price,
                    'description': item.description,
                    'po_number': item_po,
                    'country_origin': 'CHINA',
                })

            return items

        except Exception as e:
            print(f"SmartExtractor error: {e}")
            return []

    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """Post-process - deduplicate."""
        if not items:
            return items

        seen = set()
        unique_items = []

        for item in items:
            key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        return unique_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is only a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower and 'invoice' not in text_lower:
            return True
        return False
