"""
Data Extractors for OCR Extension.
Parses OCR text and extracts structured data using regex patterns.
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from .models import (
    InvoiceData, LineItem, InvoiceTotals, VendorInfo, ReceiverInfo,
    ReferenceNumbers, PackingListData, BillOfLadingData
)


class BaseExtractor:
    """Base class for document extractors with common utilities."""

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_pattern(self, text: str, pattern: str, group: int = 1) -> str:
        """Extract first match of pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                return self.clean_text(match.group(group))
            except IndexError:
                return self.clean_text(match.group(0))
        return ""

    def extract_all_patterns(self, text: str, pattern: str) -> List[str]:
        """Extract all matches of pattern from text."""
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        return [self.clean_text(m) if isinstance(m, str) else self.clean_text(m[0]) for m in matches]

    def parse_number(self, text: str) -> float:
        """Parse a number from text, handling various formats."""
        if not text:
            return 0.0
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[^\d.,\-]', '', text)
        if not cleaned:
            return 0.0

        # Handle European format (1.234,56) vs US format (1,234.56)
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                # European: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # US: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Could be either 1,234 (thousands) or 1,23 (decimal)
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def parse_date(self, text: str) -> str:
        """Parse and normalize a date string."""
        if not text:
            return ""

        # Common date patterns
        patterns = [
            (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', '{0}-{1:02d}-{2:02d}'),  # 2024-01-15
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', '{2}-{0:02d}-{1:02d}'),  # 01/15/2024
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})', '20{2}-{0:02d}-{1:02d}'),  # 01/15/24
            (r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', None),  # January 15, 2024
        ]

        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                if fmt:
                    try:
                        groups = [int(g) for g in match.groups()]
                        return fmt.format(*groups)
                    except (ValueError, IndexError):
                        pass
                else:
                    # Month name format
                    return text.strip()

        return text.strip()


class InvoiceExtractor(BaseExtractor):
    """Extracts commercial invoice data from OCR text."""

    # Common patterns for invoice fields
    PATTERNS = {
        # Reference Numbers
        'invoice_number': [
            r'invoice\s*(?:no|number|#)[:\s]*([A-Z0-9\-/]+)',
            r'inv[:\s#]*([A-Z0-9\-/]+)',
            r'commercial\s*invoice[:\s]*([A-Z0-9\-/]+)',
        ],
        'invoice_date': [
            r'invoice\s*date[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
            r'date[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
            r'dated?[:\s]*(\w+\s+\d{1,2},?\s*\d{4})',
        ],
        'po_number': [
            r'(?:p\.?o\.?|purchase\s*order)\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)',
            r'order\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)',
        ],
        'bill_of_lading': [
            r'(?:b/?l|bill\s*of\s*lading)\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)',
            r'(?:bol|bl)\s*#?[:\s]*([A-Z0-9\-/]+)',
        ],
        'container_number': [
            r'container\s*(?:no|number|#)?[:\s]*([A-Z]{4}\d{7})',
            r'cntr[:\s]*([A-Z]{4}\d{7})',
            r'([A-Z]{4}\d{7})',  # Standard container format
        ],

        # Totals
        'total_amount': [
            r'(?:grand\s*)?total[:\s]*(?:amount)?[:\s]*\$?([0-9,]+\.?\d*)',
            r'total\s*(?:usd|value)[:\s]*\$?([0-9,]+\.?\d*)',
            r'(?:fob|cif|cfr)\s*(?:value|total)?[:\s]*\$?([0-9,]+\.?\d*)',
        ],
        'currency': [
            r'currency[:\s]*([A-Z]{3})',
            r'(USD|EUR|GBP|CNY|JPY|CAD)',
        ],

        # Shipping
        'incoterms': [
            r'((?:FOB|CIF|CFR|EXW|FCA|CPT|CIP|DAP|DPU|DDP)\s*[A-Za-z\s,]*)',
            r'terms[:\s]*(FOB|CIF|CFR|EXW|FCA|CPT|CIP|DAP|DPU|DDP)',
        ],
        'country_of_origin': [
            r'(?:country\s*of\s*)?origin[:\s]*([A-Za-z\s]+)',
            r'made\s*in[:\s]*([A-Za-z\s]+)',
        ],
    }

    def extract(self, text: str) -> InvoiceData:
        """Extract invoice data from OCR text."""
        invoice = InvoiceData(raw_text=text)

        # Extract reference numbers
        invoice.references = self._extract_references(text)

        # Extract vendor info
        invoice.vendor = self._extract_vendor(text)

        # Extract receiver info
        invoice.receiver = self._extract_receiver(text)

        # Extract line items
        invoice.line_items = self._extract_line_items(text)

        # Extract totals
        invoice.totals = self._extract_totals(text)

        # Extract shipping info
        invoice.incoterms = self._extract_field(text, 'incoterms')
        invoice.port_of_loading = self.extract_pattern(
            text, r'port\s*of\s*loading[:\s]*([A-Za-z\s,]+)'
        )
        invoice.port_of_discharge = self.extract_pattern(
            text, r'port\s*of\s*discharge[:\s]*([A-Za-z\s,]+)'
        )

        return invoice

    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract a field using multiple pattern attempts."""
        if field_name not in self.PATTERNS:
            return ""

        for pattern in self.PATTERNS[field_name]:
            value = self.extract_pattern(text, pattern)
            if value:
                return value
        return ""

    def _extract_references(self, text: str) -> ReferenceNumbers:
        """Extract reference numbers from invoice."""
        refs = ReferenceNumbers()
        refs.invoice_number = self._extract_field(text, 'invoice_number')
        refs.invoice_date = self.parse_date(self._extract_field(text, 'invoice_date'))
        refs.po_number = self._extract_field(text, 'po_number')
        refs.bill_of_lading = self._extract_field(text, 'bill_of_lading')
        refs.container_number = self._extract_field(text, 'container_number')
        return refs

    def _extract_vendor(self, text: str) -> VendorInfo:
        """Extract vendor/seller information."""
        vendor = VendorInfo()

        # Look for vendor section
        vendor_section = self._find_section(text, [
            r'(?:seller|shipper|exporter|vendor|from)[:\s]*([\s\S]*?)(?:buyer|consignee|importer|to|ship\s*to|\n\n)',
            r'(?:sold\s*by|shipped\s*from)[:\s]*([\s\S]*?)(?:sold\s*to|shipped\s*to|\n\n)',
        ])

        if vendor_section:
            vendor.name = self._extract_first_line(vendor_section)
            vendor.address = self._extract_address(vendor_section)
            vendor.country = self._extract_country(vendor_section)

        return vendor

    def _extract_receiver(self, text: str) -> ReceiverInfo:
        """Extract receiver/buyer/consignee information."""
        receiver = ReceiverInfo()

        # Look for receiver section
        receiver_section = self._find_section(text, [
            r'(?:buyer|consignee|importer|to|ship\s*to)[:\s]*([\s\S]*?)(?:notify|description|item|\n\n)',
            r'(?:sold\s*to|shipped\s*to)[:\s]*([\s\S]*?)(?:notify|description|item|\n\n)',
        ])

        if receiver_section:
            receiver.name = self._extract_first_line(receiver_section)
            receiver.address = self._extract_address(receiver_section)
            receiver.country = self._extract_country(receiver_section)

        return receiver

    def _find_section(self, text: str, patterns: List[str]) -> str:
        """Find a section of text matching patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_first_line(self, text: str) -> str:
        """Extract first non-empty line from text."""
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                return line
        return ""

    def _extract_address(self, text: str) -> str:
        """Extract address from a text section."""
        lines = text.strip().split('\n')
        if len(lines) > 1:
            return ' '.join(line.strip() for line in lines[1:4] if line.strip())
        return ""

    def _extract_country(self, text: str) -> str:
        """Extract country from text."""
        # Common country patterns
        countries = [
            'CHINA', 'UNITED STATES', 'USA', 'CANADA', 'MEXICO', 'JAPAN',
            'KOREA', 'TAIWAN', 'HONG KONG', 'VIETNAM', 'THAILAND', 'INDIA',
            'GERMANY', 'UNITED KINGDOM', 'UK', 'FRANCE', 'ITALY', 'SPAIN'
        ]
        text_upper = text.upper()
        for country in countries:
            if country in text_upper:
                return country
        return ""

    def _extract_line_items(self, text: str) -> List[LineItem]:
        """Extract line items from invoice text."""
        items = []

        # Strategy 1: Look for tabular data
        items = self._extract_tabular_items(text)

        if not items:
            # Strategy 2: Look for numbered items
            items = self._extract_numbered_items(text)

        if not items:
            # Strategy 3: Pattern-based extraction
            items = self._extract_pattern_items(text)

        return items

    def _extract_tabular_items(self, text: str) -> List[LineItem]:
        """Extract items from tabular format."""
        items = []

        # Pattern for common line item formats:
        # Description | Qty | Unit | Price | Total
        # Or: Item# | Description | Qty | Price | Amount
        patterns = [
            # Pattern: optional line#, description, qty, unit, price, total
            r'(\d*)\s*([A-Za-z][A-Za-z0-9\s\-\./]{10,}?)\s+(\d+(?:\.\d+)?)\s*(PCS?|EA|SET|CTN|KG|LB|M|FT|YD|DOZ)?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',

            # Pattern: description, qty, price, total (no unit)
            r'([A-Za-z][A-Za-z0-9\s\-\./]{10,}?)\s+(\d+(?:\.\d+)?)\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                for i, match in enumerate(matches):
                    item = LineItem()
                    item.line_number = i + 1

                    if len(match) == 6:
                        # Full pattern with line number
                        item.description = self.clean_text(match[1])
                        item.quantity = self.parse_number(match[2])
                        item.unit = match[3].upper() if match[3] else "EA"
                        item.unit_price = self.parse_number(match[4])
                        item.total_price = self.parse_number(match[5])
                    elif len(match) == 4:
                        # Pattern without unit
                        item.description = self.clean_text(match[0])
                        item.quantity = self.parse_number(match[1])
                        item.unit_price = self.parse_number(match[2])
                        item.total_price = self.parse_number(match[3])

                    item.raw_text = str(match)

                    # Extract HTS code if present
                    hts_match = re.search(r'(\d{4}\.\d{2}\.\d{4}|\d{10})', item.description)
                    if hts_match:
                        item.hts_code = hts_match.group(1)

                    if item.description and (item.quantity > 0 or item.total_price > 0):
                        items.append(item)

                if items:
                    break

        return items

    def _extract_numbered_items(self, text: str) -> List[LineItem]:
        """Extract items that are numbered (1. Item, 2. Item, etc.)."""
        items = []

        # Pattern for numbered items
        pattern = r'^\s*(\d+)[.\)]\s*(.+?)(?:\s+(\d+(?:\.\d+)?)\s*(?:pcs?|ea|units?)?\s*[@x]\s*\$?(\d+(?:\.\d{2})?)\s*=?\s*\$?(\d+(?:\.\d{2})?))?$'

        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            item = LineItem()
            item.line_number = int(match.group(1))
            item.description = self.clean_text(match.group(2))

            if match.group(3):
                item.quantity = self.parse_number(match.group(3))
            if match.group(4):
                item.unit_price = self.parse_number(match.group(4))
            if match.group(5):
                item.total_price = self.parse_number(match.group(5))

            item.raw_text = match.group(0)

            if item.description:
                items.append(item)

        return items

    def _extract_pattern_items(self, text: str) -> List[LineItem]:
        """Extract items using loose pattern matching."""
        items = []

        # Look for lines with both quantity and price indicators
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # Skip short lines or header-like lines
            if len(line) < 20 or re.match(r'^\s*(item|description|qty|quantity|price|amount)', line, re.I):
                continue

            # Look for quantity + price pattern
            qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:pcs?|ea|units?|sets?|ctns?)', line, re.I)
            price_match = re.search(r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*$', line)

            if qty_match and price_match:
                item = LineItem()
                item.line_number = len(items) + 1
                item.quantity = self.parse_number(qty_match.group(1))
                item.total_price = self.parse_number(price_match.group(1))

                # Description is text before quantity
                desc_end = qty_match.start()
                item.description = self.clean_text(line[:desc_end])
                item.raw_text = line

                if item.description:
                    items.append(item)

        return items

    def _extract_totals(self, text: str) -> InvoiceTotals:
        """Extract invoice totals."""
        totals = InvoiceTotals()

        # Total amount
        total_str = self._extract_field(text, 'total_amount')
        totals.total_amount = self.parse_number(total_str)

        # Currency
        totals.currency = self._extract_field(text, 'currency') or 'USD'

        # Subtotal
        subtotal = self.extract_pattern(text, r'sub\s*total[:\s]*\$?([0-9,]+\.?\d*)')
        totals.subtotal = self.parse_number(subtotal)

        # Freight
        freight = self.extract_pattern(text, r'freight[:\s]*\$?([0-9,]+\.?\d*)')
        totals.freight = self.parse_number(freight)

        # Insurance
        insurance = self.extract_pattern(text, r'insurance[:\s]*\$?([0-9,]+\.?\d*)')
        totals.insurance = self.parse_number(insurance)

        # Total quantity
        qty_patterns = [
            r'total\s*(?:qty|quantity)[:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:pcs?|pieces?|units?)\s*(?:total|in\s*total)',
        ]
        for pattern in qty_patterns:
            qty = self.extract_pattern(text, pattern)
            if qty:
                totals.total_quantity = self.parse_number(qty)
                break

        # Total weight
        weight_patterns = [
            r'(?:gross|total)\s*weight[:\s]*(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?',
            r'(?:g\.?w\.?|n\.?w\.?)[:\s]*(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?',
        ]
        for pattern in weight_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                totals.total_weight = self.parse_number(match.group(1))
                if match.group(2):
                    totals.weight_unit = 'LB' if 'lb' in match.group(2).lower() else 'KG'
                break

        return totals


class PackingListExtractor(BaseExtractor):
    """Extracts packing list data from OCR text."""

    def extract(self, text: str) -> PackingListData:
        """Extract packing list data from text."""
        packing = PackingListData(raw_text=text)

        # Extract references
        packing.references = ReferenceNumbers()
        packing.references.invoice_number = self.extract_pattern(
            text, r'invoice\s*(?:no|#)[:\s]*([A-Z0-9\-/]+)'
        )
        packing.references.po_number = self.extract_pattern(
            text, r'(?:p\.?o\.?|order)\s*(?:no|#)?[:\s]*([A-Z0-9\-/]+)'
        )

        # Extract totals
        packing.total_packages = int(self.parse_number(
            self.extract_pattern(text, r'(?:total\s*)?(?:packages?|cartons?|ctns?)[:\s]*(\d+)')
        ))

        packing.total_gross_weight = self.parse_number(
            self.extract_pattern(text, r'(?:total\s*)?gross\s*weight[:\s]*(\d+(?:\.\d+)?)')
        )

        packing.total_net_weight = self.parse_number(
            self.extract_pattern(text, r'(?:total\s*)?net\s*weight[:\s]*(\d+(?:\.\d+)?)')
        )

        packing.total_volume = self.parse_number(
            self.extract_pattern(text, r'(?:total\s*)?(?:volume|cbm|measurement)[:\s]*(\d+(?:\.\d+)?)')
        )

        # Detect weight unit
        if re.search(r'\blbs?\b', text, re.I):
            packing.weight_unit = 'LB'

        return packing


class BOLExtractor(BaseExtractor):
    """Extracts Bill of Lading data from OCR text."""

    def extract(self, text: str) -> BillOfLadingData:
        """Extract Bill of Lading data from text."""
        bol = BillOfLadingData(raw_text=text)

        # B/L Number
        bol.bl_number = self.extract_pattern(
            text, r'(?:b/?l|bill\s*of\s*lading)\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)'
        )

        # Vessel info
        bol.vessel_name = self.extract_pattern(
            text, r'vessel\s*(?:name)?[:\s]*([A-Za-z0-9\s]+)'
        )
        bol.voyage_number = self.extract_pattern(
            text, r'voyage\s*(?:no|number|#)?[:\s]*([A-Z0-9\-/]+)'
        )

        # Ports
        bol.port_of_loading = self.extract_pattern(
            text, r'port\s*of\s*loading[:\s]*([A-Za-z\s,]+)'
        )
        bol.port_of_discharge = self.extract_pattern(
            text, r'port\s*of\s*discharge[:\s]*([A-Za-z\s,]+)'
        )
        bol.place_of_delivery = self.extract_pattern(
            text, r'(?:place\s*of\s*delivery|final\s*destination)[:\s]*([A-Za-z\s,]+)'
        )

        # Parties
        bol.shipper = self._extract_party(text, 'shipper')
        bol.consignee = self._extract_party(text, 'consignee')
        bol.notify_party = self._extract_party(text, 'notify')

        # Container numbers (standard format: 4 letters + 7 digits)
        bol.container_numbers = self.extract_all_patterns(
            text, r'([A-Z]{4}\d{7})'
        )

        # Seal numbers
        bol.seal_numbers = self.extract_all_patterns(
            text, r'seal\s*(?:no|#)?[:\s]*([A-Z0-9\-]+)'
        )

        # Weights
        bol.gross_weight = self.parse_number(
            self.extract_pattern(text, r'gross\s*weight[:\s]*(\d+(?:\.\d+)?)')
        )
        bol.measurement = self.parse_number(
            self.extract_pattern(text, r'measurement[:\s]*(\d+(?:\.\d+)?)')
        )

        # Freight terms
        if re.search(r'freight\s*(?:prepaid|pre-paid)', text, re.I):
            bol.freight_terms = 'PREPAID'
        elif re.search(r'freight\s*collect', text, re.I):
            bol.freight_terms = 'COLLECT'

        # Issue info
        bol.issue_date = self.extract_pattern(
            text, r'(?:date\s*of\s*issue|issued?\s*(?:on|date)?)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        )
        bol.issue_place = self.extract_pattern(
            text, r'(?:place\s*of\s*issue|issued?\s*at)[:\s]*([A-Za-z\s,]+)'
        )

        return bol

    def _extract_party(self, text: str, party_type: str) -> str:
        """Extract a party (shipper/consignee/notify) from text."""
        pattern = rf'{party_type}[:\s]*([\s\S]*?)(?:consignee|notify|port|vessel|\n\n)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            lines = match.group(1).strip().split('\n')[:3]
            return ' '.join(line.strip() for line in lines if line.strip())
        return ""
