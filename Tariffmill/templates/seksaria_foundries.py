"""
Seksaria Foundries Ltd. Template

Template for invoices from Seksaria Foundries Ltd. (India).
Includes MSI-to-Sigma part number conversion using database mappings.
Generated: 2025-12-29
"""

import re
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from .base_template import BaseTemplate


class SeksariaFoundriesTemplate(BaseTemplate):
    """Template for Seksaria Foundries Ltd. invoices with MSI-to-Sigma mapping."""

    name = "Seksaria Foundries Ltd."
    description = "Invoices from Seksaria Foundries Ltd. with MSI-to-Sigma part mapping"
    client = "SIGMAC"
    version = "1.1.0"
    enabled = True

    extra_columns = ['po_number', 'unit_price', 'description', 'country_origin', 'sigma_part_number', 'hts_code']

    # Keywords to identify this supplier
    SUPPLIER_KEYWORDS = [
        'seksaria foundries limited',
        'seksaria foundries ltd',
        'chittaranjan avenue',
        'kolkata-700 006',
        'info@seksariafoundries.com',
        'www.seksariafoundries.com',
        'cin : u28112wb1974plc029617',
        'gst : 19aaecs0948q1zn',
        'sfl/'
    ]

    def __init__(self):
        super().__init__()
        self.msi_sigma_mappings = {}  # msi_part -> sigma_part
        self.msi_hts_mappings = {}    # msi_part -> hts_code
        self._load_msi_sigma_mappings()

    def _get_database_path(self) -> str:
        """Get the correct database path for the application."""
        # Try AppData location first (installed app)
        appdata_path = Path(os.environ.get('LOCALAPPDATA', '')) / 'TariffMill' / 'tariffmill.db'
        if appdata_path.exists():
            return str(appdata_path)

        # Try relative to this file (development)
        dev_path = Path(__file__).parent.parent / 'Resources' / 'tariffmill.db'
        if dev_path.exists():
            return str(dev_path)

        # Try network path
        network_path = Path(r'Y:\Dev\Tariffmill\TariffmillDB\tariffmill.db')
        if network_path.exists():
            return str(network_path)

        return ""

    def _load_msi_sigma_mappings(self):
        """
        Load MSI to Sigma part number mappings and HTS codes from the msi_sigma_parts database table.

        The msi_sigma_parts table has columns:
        - msi_part_number: The MSI format part number (e.g., 'MS2001-F/O')
        - sigma_part_number: The Sigma format part number (e.g., 'MS2001-F-O')
        - hts_code: The HTS code for this part (e.g., '7325.10.0010')

        Key conversion patterns:
        - '/' in MSI becomes '-' in Sigma (e.g., F/O -> F-O)
        - '.' decimal points are removed (e.g., X1.5 -> X15)
        """
        db_path = self._get_database_path()
        if not db_path:
            print("Warning: Could not find TariffMill database for MSI-Sigma mappings")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Load all MSI to Sigma mappings with HTS codes
            cursor.execute("SELECT msi_part_number, sigma_part_number, hts_code FROM msi_sigma_parts")
            mappings = cursor.fetchall()

            for msi_part, sigma_part, hts_code in mappings:
                if msi_part and sigma_part:
                    # Store with uppercase key for case-insensitive matching
                    key = msi_part.strip().upper()
                    self.msi_sigma_mappings[key] = sigma_part.strip()
                    if hts_code:
                        self.msi_hts_mappings[key] = hts_code.strip()

            conn.close()
            print(f"Loaded {len(self.msi_sigma_mappings)} MSI-to-Sigma mappings from database")

        except Exception as e:
            print(f"Error loading MSI-to-Sigma mappings: {e}")

    def can_process(self, text: str) -> bool:
        """Check if this is a Seksaria Foundries Ltd. invoice."""
        text_lower = text.lower()
        for keyword in self.SUPPLIER_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        # Higher confidence if multiple keywords match
        text_lower = text.lower()
        matches = sum(1 for kw in self.SUPPLIER_KEYWORDS if kw in text_lower)
        return min(0.5 + (matches * 0.1), 0.95)

    def map_msi_to_sigma(self, msi_part: str) -> str:
        """
        Map MSI part number to Sigma part number.

        Conversion strategy:
        1. First try exact match from database
        2. Try normalized variations (uppercase, no spaces)
        3. Apply pattern-based conversion rules:
           - Replace '/' with '-'
           - Remove decimal points (X1.5 -> X15)

        Args:
            msi_part: The MSI format part number

        Returns:
            The Sigma format part number
        """
        if not msi_part:
            return msi_part

        # Normalize for lookup
        msi_clean = msi_part.strip().upper()

        # 1. Try exact database match
        if msi_clean in self.msi_sigma_mappings:
            return self.msi_sigma_mappings[msi_clean]

        # 2. Try variations
        variations = [
            msi_clean,
            msi_clean.replace(' ', ''),
            msi_clean.replace('-', ''),
            msi_clean.replace('/', '-'),
        ]

        for var in variations:
            if var in self.msi_sigma_mappings:
                return self.msi_sigma_mappings[var]

        # 3. Apply pattern-based conversion rules (fallback)
        # MSI uses '/' and '.' while Sigma uses '-' and removes decimals
        sigma_part = msi_clean

        # Replace '/' with '-' (e.g., MS2001-F/O -> MS2001-F-O)
        sigma_part = sigma_part.replace('/', '-')

        # Remove decimal points in version numbers (e.g., X1.5 -> X15)
        sigma_part = re.sub(r'(\d+)\.(\d+)', r'\1\2', sigma_part)

        # Check if our conversion matches a known Sigma part
        if sigma_part in [v for v in self.msi_sigma_mappings.values()]:
            return sigma_part

        return sigma_part

    def get_hts_code(self, msi_part: str) -> str:
        """
        Get the HTS code for an MSI part number from the database.

        Args:
            msi_part: The MSI format part number

        Returns:
            The HTS code or empty string if not found
        """
        if not msi_part:
            return ""

        msi_clean = msi_part.strip().upper()

        # Try exact match
        if msi_clean in self.msi_hts_mappings:
            return self.msi_hts_mappings[msi_clean]

        # Try variations
        variations = [
            msi_clean,
            msi_clean.replace(' ', ''),
            msi_clean.replace('-', ''),
            msi_clean.replace('/', '-'),
        ]

        for var in variations:
            if var in self.msi_hts_mappings:
                return self.msi_hts_mappings[var]

        return ""

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from Seksaria invoice."""
        patterns = [
            r'Exporter\s+Invoice\s+No\.\s*&\s*Date\s*\n?([^\n]+)',
            r'(SFL/\d+-\d+/E/\d+)',
            r'SFL/(\d+-\d+/E/\d+)',
            r'Invoice\s+No\.\s*[:\-]?\s*([A-Z0-9/\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                invoice_num = match.group(1).strip()
                # Clean up - remove date portion if present
                if 'DT.' in invoice_num.upper():
                    invoice_num = invoice_num.split('DT.')[0].strip()
                if 'DT ' in invoice_num.upper():
                    invoice_num = invoice_num.split('DT ')[0].strip()
                return invoice_num

        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract PO/project number from invoice."""
        # Look for Proforma Invoice reference first (most reliable)
        proforma_match = re.search(r'As\s+per\s+Proforma\s+Invoice\s*[-:]?\s*(\d+/\d+|\d+)', text, re.IGNORECASE)
        if proforma_match:
            return proforma_match.group(1).strip()

        # Look for Other Reference
        other_ref_match = re.search(r'Other\s+Reference\(s\)\s*\n\s*([A-Z0-9\-/]+)', text, re.IGNORECASE | re.MULTILINE)
        if other_ref_match:
            ref = other_ref_match.group(1).strip()
            if ref and not ref.startswith('As per'):
                return ref

        # Look for PO number
        po_match = re.search(r'P\.?O\.?\s*(?:No\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
        if po_match:
            return po_match.group(1).strip()

        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Return the manufacturer name."""
        return "SEKSARIA FOUNDRIES LTD."

    def extract_line_items(self, text: str) -> List[Dict]:
        """
        Extract line items from Seksaria Foundries invoice.

        Expected format varies but typically:
        PART-NUMBER   DESCRIPTION   QTY   UNIT   $UNIT_PRICE   $TOTAL

        Returns list of dicts with:
        - part_number: MSI format part number
        - sigma_part_number: Converted Sigma format
        - description: Item description
        - quantity: Integer quantity
        - unit_price: Float unit price
        - total_price: Float total price
        - country_origin: 'INDIA'
        """
        self.last_processed_text = text
        items = []

        # Multiple patterns to handle different invoice formats
        # Sample line: MS2001-SWR/S 2001-SAN SWR SOLID SET 15 SET $ 99.600 $ 1494.00
        patterns = [
            # Pattern 1: MS/MSMH part with $ signs (space after $)
            r'((?:MS|MSMH)[\w\-./]+)\s+(.+?)\s+(\d+)\s+(SET|PCS|EACH|EA|PC|NOS|SETS)\s+\$\s*([\d,]+\.?\d*)\s+\$\s*([\d,]+\.?\d*)',

            # Pattern 2: Without $ signs
            r'((?:MS|MSMH)[\w\-./]+)\s+(.+?)\s+(\d+)\s+(SET|PCS|EACH|EA|PC|NOS|SETS)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)

            for match in matches:
                try:
                    part_number = match[0].strip()
                    description = match[1].strip()
                    quantity = int(match[2].strip())

                    # Handle 5 or 6 group matches
                    if len(match) == 6:
                        unit = match[3].strip().upper()
                        unit_price = float(match[4].replace(',', ''))
                        total_price = float(match[5].replace(',', ''))
                    else:
                        unit = "SET"
                        unit_price = float(match[3].replace(',', ''))
                        total_price = float(match[4].replace(',', ''))

                    # Skip invalid entries
                    if quantity <= 0 or total_price <= 0:
                        continue

                    # Skip if description looks like numbers or junk
                    if not description or description.replace(' ', '').isdigit():
                        continue

                    # Convert MSI part number to Sigma format and get HTS code
                    sigma_part_number = self.map_msi_to_sigma(part_number)
                    hts_code = self.get_hts_code(part_number)

                    item = {
                        'part_number': part_number,
                        'sigma_part_number': sigma_part_number,
                        'description': f"{description} ({unit})".strip(),
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': total_price,
                        'country_origin': 'INDIA',
                        'hts_code': hts_code
                    }
                    items.append(item)

                    print(f"Extracted: {part_number} -> {sigma_part_number}, HTS: {hts_code}, Qty: {quantity}, Total: ${total_price:.2f}")

                except (ValueError, IndexError) as e:
                    print(f"Error parsing line item: {e}")
                    continue

            # If we found items with this pattern, stop trying others
            if items:
                break

        # If no items found with patterns, try line-by-line parsing
        if not items:
            items = self._extract_line_items_fallback(text)

        return items

    def _extract_line_items_fallback(self, text: str) -> List[Dict]:
        """Fallback line-by-line extraction for difficult formats."""
        items = []
        lines = text.split('\n')

        for line in lines:
            # Look for lines starting with MS or MSMH
            if not re.match(r'^\s*(MS|MSMH)', line, re.IGNORECASE):
                continue

            # Try to extract: part_number, description, quantity, prices
            # Pattern: MS2001-F/O followed by text, then numbers
            match = re.match(
                r'^\s*((?:MS|MSMH)[\w\-./]+)\s+(.+?)\s+(\d+)\s+.*?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s*$',
                line, re.IGNORECASE
            )

            if match:
                try:
                    part_number = match.group(1).strip()
                    description = match.group(2).strip()
                    quantity = int(match.group(3))
                    unit_price = float(match.group(4).replace(',', ''))
                    total_price = float(match.group(5).replace(',', ''))

                    if quantity > 0 and total_price > 0:
                        sigma_part_number = self.map_msi_to_sigma(part_number)
                        hts_code = self.get_hts_code(part_number)

                        items.append({
                            'part_number': part_number,
                            'sigma_part_number': sigma_part_number,
                            'description': description,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price,
                            'country_origin': 'INDIA',
                            'hts_code': hts_code
                        })
                        print(f"Fallback extracted: {part_number} -> {sigma_part_number}, HTS: {hts_code}")

                except (ValueError, IndexError):
                    continue

        return items

    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """Post-process items - deduplicate and add PO number."""
        if not items:
            return items

        # Deduplicate based on part number + quantity + price
        seen = set()
        unique_items = []

        # Get PO number once
        po_number = "UNKNOWN"
        if hasattr(self, 'last_processed_text'):
            po_number = self.extract_project_number(self.last_processed_text)

        for item in items:
            key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"
            if key not in seen:
                seen.add(key)
                item['po_number'] = po_number

                # Ensure sigma_part_number is set
                if not item.get('sigma_part_number'):
                    item['sigma_part_number'] = self.map_msi_to_sigma(item.get('part_number', ''))

                unique_items.append(item)

        return unique_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is a packing list (should be skipped)."""
        text_lower = text.lower()

        # Skip packing lists that don't have pricing info
        if 'packing list' in text_lower:
            if 'invoice' not in text_lower:
                return True
            if 'fob' not in text_lower and 'amount chargeable' not in text_lower:
                return True

        return False
