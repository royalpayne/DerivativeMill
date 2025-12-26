"""
ICAT S.A. DE C.V. Template

Template for processing invoices from ICAT S.A. DE C.V. (El Salvador)
for Co-Expo Ltd shipments.

Invoice format: Multi-page customs invoices with line item tables
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class CoexpoIcatSaTemplate(BaseTemplate):
    """Template for ICAT S.A. DE C.V. invoices."""

    name = "ICAT S.A. DE C.V."
    description = "Invoices from ICAT S.A. DE C.V. (El Salvador) for Co-Expo Ltd"
    client = "Co-Expo"
    version = "2.1.0"
    enabled = True

    extra_columns = ['invoice_number', 'po_number', 'cut_number', 'unit_price', 'description', 'country_origin', 'producer', 'weight', 'raw_part_number', 'quantity_unit']

    # Keywords to identify this supplier
    SUPPLIER_KEYWORDS = [
        "icat s.a. de c.v.",
        "km 12 1/2 carretera troncal del norte",
        "frente a pericentro apopa",
        "complejo industrial insinca",
        "co - expo ltd",
        "co-expo ltd",
        "seaboard marine ltd",
        "santo tomas de castilla gt",
        "vidales larrañaga"
    ]

    def can_process(self, text: str) -> bool:
        """Check if this is a ICAT S.A. DE C.V. invoice."""
        text_lower = text.lower()
        match_count = 0
        for keyword in self.SUPPLIER_KEYWORDS:
            if keyword in text_lower:
                match_count += 1
        # Require at least 2 keyword matches for higher confidence
        return match_count >= 2

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        text_lower = text.lower()
        match_count = sum(1 for kw in self.SUPPLIER_KEYWORDS if kw in text_lower)

        # Higher score for more matches - ICAT invoices should have many keyword hits
        if match_count >= 5:
            return 0.98
        elif match_count >= 4:
            return 0.95
        elif match_count >= 3:
            return 0.92
        elif match_count >= 2:
            return 0.88
        return 0.80

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from SHIPPER'S REF. NO. section."""
        patterns = [
            r"INV\.\s*(\d+[A-Z]*)",
            r"SHIPPER'S REF\.?\s*NO\.?\s*(?:.*?)INV\.\s*(\d+[A-Z]*)",
            r"INV\.\s+(\d{5}[A-Z]?)",
        ]

        # Find all invoice numbers and return the first one
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()

        return "UNKNOWN"

    def extract_all_invoice_numbers(self, text: str) -> List[str]:
        """Extract all invoice numbers from the document."""
        pattern = r"INV\.\s*(\d+[A-Z]*)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        return list(set(matches)) if matches else []

    def extract_project_number(self, text: str) -> str:
        """Extract WK project number."""
        patterns = [
            r"(WK\d+-[A-Z0-9-]+)",
            r"WK(\d+[-\w]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1) if match.group(1).startswith('WK') else f"WK{match.group(1)}"
                return result
        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Return the manufacturer name."""
        return "ICAT S.A. DE C.V."

    def get_quantity_unit(self, part_number: str, description: str = "") -> str:
        """Determine the quantity unit based on part number prefix or description.

        Footwear items (14xx, 15xx prefixes) use PRS (pairs)
        Apparel items use DOZ (dozens)

        Args:
            part_number: The part/style number (base or concatenated)
            description: Optional description text for additional detection

        Returns:
            'PRS' for footwear, 'DOZ' for apparel (matching TariffMill unit codes)
        """
        # Check if part number starts with footwear prefixes (14 or 15)
        part_upper = part_number.upper().strip()
        if part_upper.startswith('14') or part_upper.startswith('15'):
            return 'PRS'

        # Also check description for footwear keywords
        if description:
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in ['footwear', 'boot', 'shoe', 'sandal']):
                return 'PRS'

        # Default to dozens for apparel
        return 'DOZ'

    def extract_base_style(self, concatenated_style: str) -> str:
        """Extract base style number from concatenated style-cut format.

        Concatenated format: 13C33070HERR01VS1100WHTI
        Base style format:   13C3-3070

        Pattern breakdown:
        - 2 digits (category): 13, 14, 15, 12, 10, 11, SK
        - 1-2 letters (type): C, L, F, S, B, H, PA, TP, HD, etc.
        - 1 digit (variant): 1, 2, 3, 4, etc.
        - 4 digits (style number): 3070, 3301, 7254, etc.
        - Remaining: cut/color/size variation (HERR01VS1100WHTI)

        Examples:
        - 13C33070HERR01VS1100WHTI -> 13C3-3070
        - 14S13301TAFF01CN0000WHTI -> 14S1-3301
        - 12L27254BEM001CC0000ROYI -> 12L2-7254
        - SK01YLC -> SK01YLC (already short format, no change)
        - 12F2-3165 -> 12F2-3165 (already has hyphen)
        """
        style = concatenated_style.strip()

        # If already has hyphen in the right place, return as-is
        if '-' in style and len(style) <= 12:
            return style

        # If it's a short SK-style code, return as-is
        if style.startswith('SK') and len(style) <= 8:
            return style

        # Try to extract base style from concatenated format
        # Pattern: (2 digits)(1-2 letters)(1 digit)(4 chars)(rest)
        # Examples: 13C3-3070, 14S1-3301, 12L2-7254, 13PA-6462, 12L1-54FC, 14P7-301G

        # First try 2-letter type codes with alphanumeric style (BC, LS, etc.)
        # e.g., 12BC10HSLAB01CC -> 12BC-10HS
        match = re.match(
            r'^(\d{2})([A-Z]{2})[-]?(\d{2}[A-Z]{2})',
            style,
            re.IGNORECASE
        )
        if match:
            prefix = match.group(1)      # 12
            type_code = match.group(2)   # BC
            style_num = match.group(3)   # 10HS
            return f"{prefix}{type_code}-{style_num}"

        # Try 2-letter type codes with 4-digit style (PA, TP, HD, CV, FA, SV, EQ, HU, BZ, HY, HZ)
        match = re.match(
            r'^(\d{2})([A-Z]{2})[-]?(\d{4})',
            style,
            re.IGNORECASE
        )
        if match:
            prefix = match.group(1)      # 13, 12, etc.
            type_code = match.group(2)   # PA, TP, HD, etc.
            style_num = match.group(3)   # 6462, 7158, etc.
            return f"{prefix}{type_code}-{style_num}"

        # Try 1-letter type codes with alphanumeric style (4 chars: digits + letters)
        # e.g., 12L154FCEKC601WK -> 12L1-54FC, 14P7301GTAFF01VS -> 14P7-301G
        match = re.match(
            r'^(\d{2})([A-Z])(\d)(\d{2}[A-Z]{2}|\d{3}[A-Z])',
            style,
            re.IGNORECASE
        )
        if match:
            prefix = match.group(1)      # 12, 14, etc.
            type_code = match.group(2)   # L, P, etc.
            variant = match.group(3)     # 1, 7, etc.
            style_num = match.group(4)   # 54FC, 301G, etc.
            return f"{prefix}{type_code}{variant}-{style_num}"

        # Then try 1-letter type codes with 4-digit style (C, L, F, S, B, H, M)
        match = re.match(
            r'^(\d{2})([A-Z])(\d)(\d{4})',
            style,
            re.IGNORECASE
        )
        if match:
            prefix = match.group(1)      # 13, 14, 12, etc.
            type_code = match.group(2)   # C, L, F, S, etc.
            variant = match.group(3)     # 1, 2, 3, etc.
            style_num = match.group(4)   # 3070, 3301, etc.
            return f"{prefix}{type_code}{variant}-{style_num}"

        # If no match, return original
        return style

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice, tracking invoice numbers per item.

        pdfplumber extracts data in single-line format:
        'SK01YLC 71132842 5.83 Knit Unisex Polo Shirt 100PL 90.738 529.31 24.00 ICAT S.A DE C.V'

        Validates parsed totals against invoice totals and rescans with alternative patterns if needed.
        """
        # First, extract expected totals from the PDF for each invoice
        expected_totals = self._extract_invoice_totals(text)

        # Try primary pattern
        items = self._parse_with_pattern(text, pattern_type='primary')

        # Validate totals
        if expected_totals:
            parsed_totals = self._calculate_parsed_totals(items)
            mismatched = self._check_totals_match(expected_totals, parsed_totals)

            if mismatched:
                # Try alternative patterns for mismatched invoices
                alt_items = self._parse_with_pattern(text, pattern_type='alternative')
                alt_totals = self._calculate_parsed_totals(alt_items)

                # For each mismatched invoice, use whichever parsing got closer
                for inv_num in mismatched:
                    expected = expected_totals.get(inv_num, 0)
                    primary_total = parsed_totals.get(inv_num, 0)
                    alt_total = alt_totals.get(inv_num, 0)

                    # If alternative is closer to expected, replace items for this invoice
                    if abs(alt_total - expected) < abs(primary_total - expected):
                        # Remove primary items for this invoice
                        items = [i for i in items if i['invoice_number'] != inv_num]
                        # Add alternative items for this invoice
                        items.extend([i for i in alt_items if i['invoice_number'] == inv_num])

        return items

    def _extract_invoice_totals(self, text: str) -> Dict[str, float]:
        """Extract expected totals for each invoice from TOTAL lines in the PDF."""
        totals = {}
        lines = text.split('\n')
        current_invoice = "UNKNOWN"
        inv_pattern = r'INV\.\s*(\d+[A-Z]*)'

        for line in lines:
            line = line.strip()

            # Track current invoice
            inv_match = re.search(inv_pattern, line, re.IGNORECASE)
            if inv_match:
                current_invoice = inv_match.group(1)

            # Look for TOTAL line: "184.08 TOTAL 13,917.84 637.82"
            # Format: DOZEN TOTAL AMOUNT WEIGHT
            total_match = re.search(r'[\d.]+\s+TOTAL\s+([\d,]+\.?\d*)\s+[\d.]+', line, re.IGNORECASE)
            if total_match and current_invoice != "UNKNOWN":
                total_val = float(total_match.group(1).replace(',', ''))
                totals[current_invoice] = total_val

        return totals

    def _calculate_parsed_totals(self, items: List[Dict]) -> Dict[str, float]:
        """Calculate totals from parsed items grouped by invoice."""
        totals = {}
        for item in items:
            inv = item.get('invoice_number', 'UNKNOWN')
            totals[inv] = totals.get(inv, 0) + item.get('total_price', 0)
        return totals

    def _check_totals_match(self, expected: Dict[str, float], parsed: Dict[str, float], tolerance: float = 0.50) -> List[str]:
        """Check which invoices have mismatched totals. Returns list of mismatched invoice numbers."""
        mismatched = []
        for inv_num, exp_total in expected.items():
            parsed_total = parsed.get(inv_num, 0)
            # Allow small tolerance for rounding differences
            if abs(exp_total - parsed_total) > tolerance:
                mismatched.append(inv_num)
        return mismatched

    def _parse_with_pattern(self, text: str, pattern_type: str = 'primary') -> List[Dict]:
        """Parse line items using specified pattern type."""
        items = []
        lines = text.split('\n')

        current_invoice = "UNKNOWN"
        inv_pattern = r'INV\.\s*(\d+[A-Z]*)'

        # Primary pattern - matches lines like:
        # SK01YLC 71132842 5.83 Knit Unisex Polo Shirt 100PL 90.738 529.31 24.00 ICAT S.A DE C.V
        # 14S13301TAFF01CN0000WHTI PO0049613-2 1.92 Woven Unisex Footwear ... 71.514 137.07 4.70 VIDALES ... 14S1-3301
        # 12L27254BEM001CC0000ROYI PO0048718 250.00 Woven Unisex Lab Coat 99PL/1CF 101.611 25,402.86 1,033.72 VIDALES...
        if pattern_type == 'primary':
            line_item_pattern = re.compile(
                r'^([A-Z0-9][A-Z0-9-]{4,})\s+'  # STYLE
                r'((?:PO)?\d{7,}[-\d]*)\s+'      # CUT/PO
                r'(\d+\.?\d*)\s+'                # DOZEN
                r'((?:Knit|Woven)\s+[A-Za-z].*?)\s+'  # DESCRIPTION (Knit/Woven followed by text)
                r'(\d+\.?\d{2,3})\s+'            # COST (like 90.738 or 71.514)
                r'([\d,]+\.\d{2})\s+'            # TOTAL (like 529.31 or 25,402.86)
                r'([\d,]+\.\d{2})\s+'            # WEIGHT (like 24.00 or 1,033.72 - can have commas)
                r'((?:ICAT|VIDALES)[^0-9]*)',    # PRODUCER (stop before trailing style code)
                re.IGNORECASE
            )
        else:
            # Alternative pattern - more flexible for edge cases
            line_item_pattern = re.compile(
                r'^([A-Z0-9][A-Z0-9-]{4,})\s+'  # STYLE
                r'((?:PO)?\d{7,}[-\d]*)\s+'      # CUT/PO
                r'(\d+\.?\d*)\s+'                # DOZEN
                r'([A-Za-z].*?)\s+'              # DESCRIPTION (any text)
                r'(\d+\.?\d{2,3})\s+'            # COST
                r'([\d,]+\.\d{2})\s+'            # TOTAL
                r'([\d,]+\.\d{2})\s*'            # WEIGHT (can have commas)
                r'((?:ICAT|VIDALES)[^0-9]*)?',   # PRODUCER (optional)
                re.IGNORECASE
            )

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for invoice number marker
            inv_match = re.search(inv_pattern, line, re.IGNORECASE)
            if inv_match:
                current_invoice = inv_match.group(1)

            # Skip header and footer lines
            if line.upper().startswith('STYLE CUT DOZEN'):
                continue
            if any(skip in line.upper() for skip in ['BOXES TOTAL', 'ROLLS FABRICS', 'RETURN PACKING',
                                                       'TOTAL BOXES', 'I DECLARE', 'KNOWLEDGE', 'CERTIFY']):
                continue

            # Try to match line item pattern
            match = line_item_pattern.match(line)
            if match:
                try:
                    raw_style = match.group(1).strip()
                    cut = match.group(2).strip()
                    dozen = float(match.group(3))
                    description = match.group(4).strip()
                    cost = float(match.group(5).replace(',', ''))
                    total = float(match.group(6).replace(',', ''))
                    weight = float(match.group(7).replace(',', ''))
                    producer = match.group(8).strip() if match.group(8) else ""

                    # Extract base style from concatenated format for HTS matching
                    # e.g., 13C33070HERR01VS1100WHTI -> 13C3-3070
                    base_style = self.extract_base_style(raw_style)

                    # Validate values
                    if dozen <= 0 or dozen > 500:
                        continue
                    if total <= 0:
                        continue

                    # Determine quantity unit (PRS. for footwear, DOZ. for apparel)
                    quantity_unit = self.get_quantity_unit(base_style, description)

                    # Convert dozen to pairs for footwear items
                    # Invoice reports in dozens, but footwear needs pairs (dozen * 12)
                    if quantity_unit == 'PRS':
                        quantity = round(dozen * 12)  # Convert dozens to pairs (whole numbers)
                    else:
                        quantity = round(dozen, 2)  # Keep 2 decimal places for dozens

                    items.append({
                        'invoice_number': current_invoice,
                        'part_number': base_style,  # Use base style for HTS matching
                        'raw_part_number': raw_style,  # Keep original for reference
                        'cut_number': cut,
                        'quantity': quantity,
                        'quantity_unit': quantity_unit,
                        'description': description,
                        'unit_price': cost,
                        'total_price': total,
                        'weight': weight,
                        'producer': producer,
                        'country_origin': 'SV',
                        'po_number': cut if cut.startswith('PO') else self.extract_project_number(text),
                    })

                except (ValueError, IndexError):
                    continue

        return items

    def _parse_line_by_line(self, text: str) -> List[Dict]:
        """Parse items line by line as fallback."""
        items = []
        lines = text.split('\n')

        # Track current invoice number
        invoice_pattern = r'INV\.\s*(\d+[A-Z]*)'
        current_invoice = "UNKNOWN"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line contains an invoice number marker
            inv_match = re.search(invoice_pattern, line, re.IGNORECASE)
            if inv_match:
                current_invoice = inv_match.group(1)

            # Skip header lines and totals
            if any(skip in line.upper() for skip in ['STYLE', 'CUT', 'DOZEN', 'DESCRIPTION', 'TOTAL', 'BOXES']):
                if 'STYLE' in line.upper() and 'CUT' in line.upper():
                    continue
                if line.strip().upper().startswith('TOTAL'):
                    continue

            # Try to match line item pattern
            # Look for lines starting with a style code
            style_match = re.match(r'^([A-Z0-9]{2,}[-A-Z0-9]*)\s+', line)
            if not style_match:
                continue

            # Try to extract numbers from the line
            numbers = re.findall(r'[\d,]+\.?\d*', line)
            if len(numbers) < 4:
                continue

            try:
                raw_style = style_match.group(1)
                # Extract base style from concatenated format
                base_style = self.extract_base_style(raw_style)

                # Find description (text between numbers)
                desc_match = re.search(r'((?:Knit|Woven)[^0-9]+(?:\d+[A-Z/]+)+)', line, re.IGNORECASE)
                description = desc_match.group(1).strip() if desc_match else ""

                # Find producer
                producer = ""
                if 'VIDALES' in line.upper():
                    producer = "VIDALES LARRAÑAGA, S.A. DE C.V"
                elif 'ICAT' in line.upper():
                    producer = "ICAT S.A DE C.V"

                # Try to identify cut/PO number
                cut_match = re.search(r'(PO\d+[-\d]*|\d{8})', line)
                cut_po = cut_match.group(1) if cut_match else ""

                # Parse numeric values (dozen, cost, total, weight)
                # Filter out very large numbers that are likely cut numbers
                numeric_values = [float(n.replace(',', '')) for n in numbers if float(n.replace(',', '')) < 100000]

                if len(numeric_values) >= 4:
                    dozen = numeric_values[0]
                    unit_price = numeric_values[1] if len(numeric_values) > 1 else 0
                    total_price = numeric_values[2] if len(numeric_values) > 2 else 0
                    weight = numeric_values[3] if len(numeric_values) > 3 else 0

                    if dozen > 0 and total_price > 0:
                        # Determine quantity unit (PRS. for footwear, DOZ. for apparel)
                        quantity_unit = self.get_quantity_unit(base_style, description)

                        # Convert dozen to pairs for footwear items
                        if quantity_unit == 'PRS':
                            quantity = round(dozen * 12)  # Convert dozens to pairs (whole numbers)
                        else:
                            quantity = round(dozen, 2)  # Keep 2 decimal places for dozens

                        items.append({
                            'part_number': base_style,  # Use base style for HTS matching
                            'raw_part_number': raw_style,  # Keep original for reference
                            'invoice_number': current_invoice,
                            'quantity': quantity,
                            'quantity_unit': quantity_unit,
                            'total_price': total_price,
                            'unit_price': unit_price,
                            'description': description,
                            'cut_number': cut_po,
                            'po_number': cut_po if cut_po.startswith('PO') else "",
                            'country_origin': 'SV',
                            'producer': producer,
                            'weight': weight
                        })
            except (ValueError, IndexError):
                continue

        return items

    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """Post-process - deduplicate and validate."""
        if not items:
            return items

        seen = set()
        unique_items = []

        for item in items:
            # Create unique key from style, cut, and total
            key = f"{item['part_number']}_{item.get('cut_number', '')}_{item['total_price']}"
            if key not in seen:
                seen.add(key)

                # Ensure country of origin is set
                if 'country_origin' not in item or not item['country_origin']:
                    item['country_origin'] = 'SV'  # El Salvador

                # Clean up description
                if 'description' in item:
                    item['description'] = re.sub(r'\s+', ' ', item['description']).strip()

                unique_items.append(item)

        return unique_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is only a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower and 'invoice' not in text_lower:
            return True
        return False

    def get_country_code(self) -> str:
        """Return the default country code for this template."""
        return "SV"  # El Salvador
