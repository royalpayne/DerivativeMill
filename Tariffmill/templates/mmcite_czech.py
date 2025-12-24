"""
MmciteCzechTemplate - Invoice template for mmcité a.s. (Czech Republic)
Handles both standard invoices and DownPayment Requests from mmcité Czech.
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class MmciteCzechTemplate(BaseTemplate):
    """
    Invoice template for mmcité a.s. Czech Republic invoices.

    Handles two formats:
    1. Standard Invoice format:
       - Line items: type/description | Project | Qty | Price | VAT (%) | Price after taxes
       - Example: ATP-spare part US25N0015 1,00 ks 2.003,76 CZK 0 96,12 USD

    2. DownPayment Request format:
       - Line items: Art. No. | Description | Project | Quantity | Unit price | VAT % | Price nett | Price gross
       - Example: LDP111-a5-5029-US25A0046 US25A0046 2 units 41.011,52 CZK 0% 3.917,80 USD 3.917,80 USD
    """

    name = "mmcité Czech"
    description = "mmcité a.s. Czech Republic invoices and DownPayment Requests"
    client = "mmcité a.s."
    version = "1.1.0"
    enabled = True

    extra_columns = ['unit_price', 'description', 'project', 'czk_price']

    def can_process(self, text: str) -> bool:
        """Check if this template can process the invoice."""
        text_lower = text.lower()

        # Look for mmcité a.s. - the Czech company
        has_mmcite = 'mmcité a.s' in text_lower or 'mmcite a.s' in text_lower

        # Look for Czech Republic origin
        has_czech = 'czech republic' in text_lower or 'uherské hradiště' in text_lower

        # Look for mmcité usa LLC as buyer (distinctive marker for these invoices)
        has_mmcite_usa_buyer = 'mmcité usa llc' in text_lower or 'mmcite usa llc' in text_lower

        return has_mmcite and (has_czech or has_mmcite_usa_buyer)

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        text_lower = text.lower()

        # Strong indicators
        if 'mmcité a.s' in text_lower or 'mmcite a.s' in text_lower:
            score += 0.2
        if 'czech republic' in text_lower:
            score += 0.15
        if 'uherské hradiště' in text_lower:
            score += 0.1
        if 'mmcité usa llc' in text_lower or 'mmcite usa llc' in text_lower:
            score += 0.1

        # Invoice format markers
        if re.search(r'invoice\s+n\.?\s*:?\s*\d+', text, re.IGNORECASE):
            score += 0.1
        if re.search(r'proforma\s+invoice', text, re.IGNORECASE):
            score += 0.1
        if re.search(r'project\s+n\.:', text, re.IGNORECASE):
            score += 0.05
        if 'downpayment request' in text_lower:
            score += 0.1

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice or DownPayment Request number."""
        patterns = [
            r'Invoice\s+n\.?\s*:?\s*(\d+)',              # Invoice n. 2025201516 or Invoice n.: 2025710144
            r'Proforma\s+invoice\s+n\.?\s*:?\s*(\d+)',   # Proforma invoice n.: 2025710144
            r'DownPayment\s+Request\s+Nr\.\s*(\d+)',    # DownPayment Request Nr. 2025750224
            r'variable\s+symbol:\s*(\d+)',               # variable symbol: 2025201516
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract project number."""
        patterns = [
            r'project\s+n\.:\s*(US\d{2}[A-Z]\d{4}[a-z]?)',  # project n.: US25A0046
            r'Project:\s*(US\d{2}[A-Z]\d{4}[a-z]?)',         # Project: US25A0046
            r'\b(US\d{2}[A-Z]\d{4}[a-z]?)\b',                # Standalone project code
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Extract manufacturer name."""
        return "MMCITE A.S. CZECH REPUBLIC"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        line_items = []
        seen_items = set()

        # Determine format type
        is_downpayment = 'downpayment request' in text.lower()

        lines = text.split('\n')
        current_description = ""

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip header and footer lines
            skip_patterns = [
                'type / desciption', 'art. no.', 'description project',
                'printed from sap', 'www.mmcite.com', 'tax recapitulation',
                'vat code', 'total:', 'exchange rate:', 'issued by:',
                'notes:', 'celkem', 'souhrn', 'please note', 'vývozce',
                'the exporter', 'taxable transaction', 'zdanitelné'
            ]
            if any(skip in line.lower() for skip in skip_patterns):
                continue

            # Try to match line items
            item = self._parse_line_item(line, lines, i, is_downpayment)
            if item:
                # Skip parts that start with SLU or OBAL (packaging/shipping items)
                part_upper = item['part_number'].upper()
                if part_upper.startswith('SLU') or part_upper.startswith('OBAL'):
                    continue

                # Create deduplication key
                item_key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)

        return line_items

    def _parse_line_item(self, line: str, all_lines: List[str], line_idx: int, is_downpayment: bool) -> dict:
        """Parse a single line item from the invoice."""

        if is_downpayment:
            # DownPayment Request format:
            # LDP111-a5-5029-US25A0046 US25A0046 2 units 41.011,52 CZK 0% 3.917,80 USD 3.917,80 USD
            pattern = re.compile(
                r'^([A-Z]{2,}[\w\-]+(?:-US\d{2}[A-Z]\d{4}[a-z]?)?)\s+'  # Part number (e.g., LDP111-a5-5029-US25A0046)
                r'(US\d{2}[A-Z]\d{4}[a-z]?)\s+'                         # Project code
                r'(\d+(?:[.,]\d+)?)\s*(?:units|ks|pcs)?\s+'             # Quantity
                r'([\d.,]+)\s*CZK\s+'                                   # CZK price
                r'\d+%?\s+'                                             # VAT %
                r'([\d.,]+)\s*USD\s+'                                   # Price nett USD
                r'([\d.,]+)\s*USD',                                     # Price gross USD
                re.IGNORECASE
            )
            match = pattern.match(line)
            if match:
                qty_str = match.group(3).replace(',', '.')
                czk_price = match.group(4).replace('.', '').replace(',', '.')
                unit_price = match.group(5).replace('.', '').replace(',', '.')
                total_price = match.group(6).replace('.', '').replace(',', '.')

                # Get description from previous lines
                description = self._get_description_before(all_lines, line_idx)

                return {
                    'part_number': match.group(1),
                    'quantity': qty_str,
                    'total_price': total_price,
                    'unit_price': unit_price,
                    'description': description,
                    'project': match.group(2),
                    'czk_price': czk_price,
                }
        else:
            # Standard Invoice format (with project on each line):
            # ATP-spare part US25N0015 1,00 ks 2.003,76 CZK 0 96,12 USD
            # SLU899 US25N0015 0,06 2.277,00 CZK 0 6,55 USD
            # ATP-Spojovací mat. US25A0274 4,00 ks 50,00 CZK 0 9,62 USD
            pattern_with_project = re.compile(
                r'^([A-Z][\w\-]+(?:[\s\-][\w\.]+)?)\s+'                 # Part number
                r'(US\d{2}[A-Z]\d{4}[a-z]?)\s+'                         # Project code
                r'(\d+(?:[.,]\d+)?)\s*(?:ks|units|pcs)?\s*'             # Quantity
                r'([\d.,]+)\s*CZK\s+'                                   # CZK price
                r'\d+\s+'                                               # VAT (0)
                r'([\d.,]+)\s*USD',                                     # USD price
                re.IGNORECASE
            )
            match = pattern_with_project.match(line)
            if match:
                qty_str = match.group(3).replace(',', '.')
                czk_price = match.group(4).replace('.', '').replace(',', '.')
                total_price = match.group(5).replace('.', '').replace(',', '.')

                # Calculate unit price
                try:
                    qty = float(qty_str)
                    price = float(total_price)
                    unit_price = f"{price / qty:.2f}" if qty > 0 else total_price
                except (ValueError, ZeroDivisionError):
                    unit_price = total_price

                # Get description from following lines
                description = self._get_description_after(all_lines, line_idx)

                return {
                    'part_number': match.group(1).strip(),
                    'quantity': qty_str,
                    'total_price': total_price,
                    'unit_price': unit_price,
                    'description': description,
                    'project': match.group(2),
                    'czk_price': czk_price,
                }

            # Proforma Invoice format (no project on line items):
            # ATP-Dřevo FSC 2,00 ks 3.359,00 CZK 0 318,46 USD
            # ATP-Spojovací mat. 2,00 ks 86,00 CZK 0 8,15 USD
            # ATP-Spojovací mat. 8,00 ks 50,00 CZK 0 16,41 EUR (EUR variant)
            pattern_no_project = re.compile(
                r'^([A-Z][\w\-]+(?:[\s\-][\w\.]+)?)\s+'                 # Part number
                r'(\d+(?:[.,]\d+)?)\s*(?:ks|units|pcs)?\s*'             # Quantity
                r'([\d.,]+)\s*CZK\s+'                                   # CZK price
                r'\d+\s+'                                               # VAT (0)
                r'([\d.,]+)\s*(?:USD|EUR)',                             # USD or EUR price
                re.IGNORECASE
            )
            match = pattern_no_project.match(line)
            if match:
                qty_str = match.group(2).replace(',', '.')
                czk_price = match.group(3).replace('.', '').replace(',', '.')
                total_price = match.group(4).replace('.', '').replace(',', '.')

                # Calculate unit price
                try:
                    qty = float(qty_str)
                    price = float(total_price)
                    unit_price = f"{price / qty:.2f}" if qty > 0 else total_price
                except (ValueError, ZeroDivisionError):
                    unit_price = total_price

                # Get description from following lines
                description = self._get_description_after(all_lines, line_idx)

                return {
                    'part_number': match.group(1).strip(),
                    'quantity': qty_str,
                    'total_price': total_price,
                    'unit_price': unit_price,
                    'description': description,
                    'project': '',  # No project on line
                    'czk_price': czk_price,
                }

        return None

    def _get_description_before(self, lines: List[str], current_idx: int) -> str:
        """Get description text from lines before the current line."""
        descriptions = []
        for i in range(current_idx - 1, max(0, current_idx - 5), -1):
            line = lines[i].strip()
            if not line:
                continue
            # Stop at another item line or header
            if re.match(r'^[A-Z]{2,}[\w\-]+\s+US\d{2}', line):
                break
            # Skip underscores (separator lines)
            if line.startswith('_') or line.endswith('_'):
                continue
            # Skip header lines
            if 'art. no.' in line.lower() or 'description' in line.lower() and 'project' in line.lower():
                continue
            if 'price' in line.lower() or 'discount' in line.lower():
                continue
            if re.match(r'^[\d.,]+\s*(?:CZK|USD|%)', line):
                continue
            # Skip lines with USD amounts (likely other items)
            if re.search(r'\d+[.,]\d+\s*USD\s+\d+[.,]\d+\s*USD', line):
                continue
            descriptions.insert(0, line)
        return ' '.join(descriptions) if descriptions else ""

    def _get_description_after(self, lines: List[str], current_idx: int) -> str:
        """Get description text from lines after the current line."""
        descriptions = []
        for i in range(current_idx + 1, min(len(lines), current_idx + 6)):
            line = lines[i].strip()
            if not line:
                continue
            # Stop at another item line
            if re.match(r'^[A-Z][\w\-]+\s+US\d{2}', line):
                break
            # Skip lines with USD amounts (likely next item)
            if re.search(r'\d+[.,]\d+\s*USD', line):
                break
            # Stop at summary lines
            if 'souhrn' in line.lower() or 'total' in line.lower():
                break
            descriptions.append(line)
        return ' '.join(descriptions) if descriptions else ""

    def is_packing_list(self, text: str) -> bool:
        """Check if document is a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower or 'packing slip' in text_lower:
            if 'invoice' not in text_lower and 'downpayment' not in text_lower:
                return True
        return False
