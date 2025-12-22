"""
VitechDevelopmentLimitedTemplate - Template for Vitech Development Limited commercial invoices
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class VitechDevelopmentLimitedTemplate(BaseTemplate):
    """
    Template for Vitech Development Limited invoices.

    Invoice format (from PDF text extraction):
    - Line items appear as: PO# PKGS QTY ITEM_CODE HS_CODE COUNTRY NET_WT GR_WT DIMENSION $UNIT_PRICE $TOTAL_VALUE
    - Description text appears on separate lines above/below the data line
    """

    name = "Vitech Development Limited"
    description = "Invoice template for Vitech Development Limited"
    client = "Vitech Development Limited"
    version = "1.0.2"

    enabled = True

    extra_columns = ['po_number', 'packages', 'hs_code', 'country_origin', 'net_weight', 'gross_weight', 'dimensions', 'unit_price']

    def can_process(self, text: str) -> bool:
        """Check if this template can process the given invoice."""
        text_lower = text.lower()
        return ('vitech development limited' in text_lower or
                ('commercial invoice' in text_lower and 'hfvt25-' in text_lower))

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        text_lower = text.lower()

        # Add points for each indicator found
        indicators = [
            'vitech development limited',
            'commercial invoice',
            'hfvt25-',
            'sigma corporation',
            '8431.20.0000'
        ]
        for indicator in indicators:
            if indicator in text_lower:
                score += 0.1

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        patterns = [
            r'INVOICE\s*#\s*([A-Z0-9-]+)',
            r'HFVT25-[A-Z]\d+',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.lastindex else match.group(0).strip()

        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract B/L number as project reference."""
        patterns = [
            r'B/L\s*#\s*([A-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "UNKNOWN"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        line_items = []
        seen_items = set()

        # Line item format from PDF text extraction:
        # 40049557 1 315 21-250464 8431.20.0000 CHINA 68 90 77X76X62 $2.18 $686.70
        # 40049557 6 288 21-250450 MODLE ASSEMBLY DWG 2540450 STEEL FAB GRAY 8431.20.0000 CHINA 3,398 3,788 152X115X124 $49.22 $14,175.36

        # Pattern to match line items - description may or may not be present between item code and HS code
        line_pattern = re.compile(
            r'(\d{8})\s+'                          # PO# (8 digits like 40049557)
            r'(\d+)\s+'                            # PKGS
            r'([\d,]+)\s+'                         # QTY (may have commas like 2,000)
            r'(\d{2}-\d{6})\s+'                    # ITEM CODE (format: 21-250464)
            r'(?:.*?)'                             # Optional description (non-capturing, non-greedy)
            r'(\d{4}\.\d{2}\.\d{4})\s+'            # HS CODE (format: 8431.20.0000)
            r'(CHINA)\s+'                          # COUNTRY OF ORIGIN
            r'([\d,]+)\s+'                         # NET WT
            r'([\d,]+)\s+'                         # GR WT
            r'(\d+X\d+X\d+)\s+'                    # DIMENSION (format: 77X76X62)
            r'\$([\d,.]+)\s+'                      # UNIT PRICE
            r'\$([\d,.]+)',                        # TOTAL VALUE
            re.IGNORECASE
        )

        for match in line_pattern.finditer(text):
            try:
                # Clean up quantity and values (remove commas)
                qty_str = match.group(3).replace(',', '')
                net_wt = match.group(7).replace(',', '')
                gr_wt = match.group(8).replace(',', '')
                unit_price = match.group(10).replace(',', '')
                total_value = match.group(11).replace(',', '')

                item = {
                    'part_number': match.group(4),           # ITEM CODE as part number
                    'quantity': int(qty_str),
                    'total_price': float(total_value),
                    'po_number': match.group(1),
                    'packages': match.group(2),
                    'hs_code': match.group(5),
                    'country_origin': match.group(6),
                    'net_weight': net_wt,
                    'gross_weight': gr_wt,
                    'dimensions': match.group(9),
                    'unit_price': unit_price,
                }

                # Create deduplication key using part_number, qty, and total_price
                item_key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"

                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)

            except (IndexError, AttributeError, ValueError) as e:
                print(f"Error parsing line item: {e}")
                continue

        # If the pattern didn't match all items, try line-by-line approach
        if len(line_items) < 5:  # We expect around 10 items
            # Try matching each line individually
            for line in text.split('\n'):
                # Look for lines that have the key components
                line_match = re.search(
                    r'(\d{8})\s+(\d+)\s+([\d,]+)\s+(\d{2}-\d{6}).*?(\d{4}\.\d{2}\.\d{4})\s+(CHINA)\s+([\d,]+)\s+([\d,]+)\s+(\d+X\d+X\d+)\s+\$([\d,.]+)\s+\$([\d,.]+)',
                    line,
                    re.IGNORECASE
                )
                if line_match:
                    try:
                        qty_str = line_match.group(3).replace(',', '')
                        net_wt = line_match.group(7).replace(',', '')
                        gr_wt = line_match.group(8).replace(',', '')
                        unit_price = line_match.group(10).replace(',', '')
                        total_value = line_match.group(11).replace(',', '')

                        item = {
                            'part_number': line_match.group(4),
                            'quantity': int(qty_str),
                            'total_price': float(total_value),
                            'po_number': line_match.group(1),
                            'packages': line_match.group(2),
                            'hs_code': line_match.group(5),
                            'country_origin': line_match.group(6),
                            'net_weight': net_wt,
                            'gross_weight': gr_wt,
                            'dimensions': line_match.group(9),
                            'unit_price': unit_price,
                        }

                        item_key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"
                        if item_key not in seen_items:
                            seen_items.add(item_key)
                            line_items.append(item)
                    except (IndexError, ValueError):
                        continue

        return line_items
