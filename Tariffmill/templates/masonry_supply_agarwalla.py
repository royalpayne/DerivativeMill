"""
MasonrySupplyAgarwallaTemplate - Template for R. B. Agarwalla & Co. invoices to Masonry Supply Inc.
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .base_template import BaseTemplate


def get_sigma_part_number(msi_part: str, db_path: Path) -> Optional[str]:
    """
    Look up the Sigma Corporation part number for an MSI part number.

    Args:
        msi_part: The MSI part number (as extracted from invoice)
        db_path: Path to the tariffmill.db database

    Returns:
        The corresponding Sigma part number, or None if not found
    """
    if not msi_part or not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()

        # Normalize the MSI part number for comparison
        msi_upper = msi_part.upper().strip()

        # Try exact match first
        c.execute("SELECT sigma_part_number FROM msi_sigma_parts WHERE UPPER(msi_part_number) = ?", (msi_upper,))
        result = c.fetchone()

        if result:
            conn.close()
            return result[0]

        # Try without special characters (/ -> -, etc.)
        msi_normalized = msi_upper.replace('/', '-').replace('.', '')
        c.execute("SELECT sigma_part_number FROM msi_sigma_parts WHERE UPPER(REPLACE(REPLACE(msi_part_number, '/', '-'), '.', '')) = ?",
                  (msi_normalized,))
        result = c.fetchone()

        if result:
            conn.close()
            return result[0]

        # Try partial match - MSI part might be a substring
        c.execute("SELECT sigma_part_number FROM msi_sigma_parts WHERE UPPER(msi_part_number) LIKE ?",
                  (f"%{msi_upper}%",))
        result = c.fetchone()

        conn.close()
        return result[0] if result else None

    except Exception:
        return None


def get_msi_sigma_mapping(db_path: Path) -> Dict[str, str]:
    """
    Load the entire MSI-to-Sigma part number mapping from the database.

    Args:
        db_path: Path to the tariffmill.db database

    Returns:
        Dictionary mapping MSI part numbers (uppercase) to Sigma part numbers
    """
    mapping = {}
    if not db_path.exists():
        return mapping

    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT msi_part_number, sigma_part_number FROM msi_sigma_parts")
        for row in c.fetchall():
            if row[0] and row[1]:
                # Store with uppercase key for case-insensitive lookup
                mapping[row[0].upper().strip()] = row[1]
        conn.close()
    except Exception:
        pass

    return mapping


def fuzzy_match_part_number(part_number: str, db_path: Path, threshold: float = 0.6) -> Optional[Tuple[str, float]]:
    """
    Search for the closest matching part number in parts_master database.

    Args:
        part_number: The part number to search for
        db_path: Path to the tariffmill.db database
        threshold: Minimum similarity score (0.0-1.0) to consider a match

    Returns:
        Tuple of (matched_part_number, similarity_score) or None if no match found
    """
    if not part_number or not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT part_number FROM parts_master")
        all_parts = [row[0] for row in c.fetchall() if row[0]]
        conn.close()

        if not all_parts:
            return None

        # Normalize input for comparison
        search_upper = part_number.upper().strip()

        best_match = None
        best_score = 0.0

        for db_part in all_parts:
            db_upper = db_part.upper().strip()

            # Calculate similarity score using multiple methods
            score = _calculate_similarity(search_upper, db_upper)

            if score > best_score and score >= threshold:
                best_score = score
                best_match = db_part

        if best_match:
            return (best_match, best_score)
        return None

    except Exception:
        return None


def _calculate_similarity(s1: str, s2: str) -> float:
    """
    Calculate similarity between two strings using multiple methods.
    Returns a score between 0.0 and 1.0.
    """
    # Exact match
    if s1 == s2:
        return 1.0

    # One contains the other
    if s1 in s2 or s2 in s1:
        return 0.9

    # Remove common prefixes/suffixes and compare
    # For Masonry parts: MS prefix, -F/O suffix, etc.
    s1_clean = re.sub(r'^MS|^N\d+', '', s1).strip('-/')
    s2_clean = re.sub(r'^MS|^N\d+', '', s2).strip('-/')

    if s1_clean == s2_clean:
        return 0.95

    if s1_clean in s2_clean or s2_clean in s1_clean:
        return 0.85

    # Numeric portion match (for codes like 840.03, 2436, etc.)
    nums1 = re.findall(r'\d+', s1)
    nums2 = re.findall(r'\d+', s2)

    if nums1 and nums2:
        # Check if main numeric codes match
        if nums1[0] == nums2[0]:
            return 0.8
        # Check if any significant numbers match
        common_nums = set(nums1) & set(nums2)
        if common_nums:
            # Weight by length of matching numbers
            max_len = max(len(n) for n in common_nums)
            if max_len >= 4:
                return 0.75
            elif max_len >= 3:
                return 0.65

    # Levenshtein-like distance (simple approximation)
    len_diff = abs(len(s1) - len(s2))
    max_len = max(len(s1), len(s2))

    if max_len == 0:
        return 0.0

    # Count matching characters
    matches = sum(1 for a, b in zip(s1, s2) if a == b)

    # Calculate ratio
    ratio = matches / max_len

    # Penalize length differences
    penalty = len_diff / max_len * 0.2

    return max(0.0, ratio - penalty)


class MasonrySupplyAgarwallaTemplate(BaseTemplate):
    """
    Template for R. B. Agarwalla & Co. commercial invoices to Masonry Supply Inc.

    Invoice format (from PDF text extraction):
    - Line items appear with: PO_DATE DESCRIPTION [PART_CODE] QTY RATE AMOUNT
    - Example: 2025-0725 "840.03 'F' FRAME. GRATE, HOOD" [MS840.03F] 20 190.610 3,812.20
    """

    name = "Masonry Supply - Agarwalla"
    description = "Invoice template for R. B. Agarwalla & Co. to Masonry Supply Inc."
    client = "Masonry Supply Inc."
    version = "1.0.0"

    enabled = True

    extra_columns = ['po_date', 'hs_code', 'country_origin', 'unit_price']

    def can_process(self, text: str) -> bool:
        """Check if this template can process the given invoice."""
        text_lower = text.lower()
        return (('r. b. agarwalla' in text_lower or 'r.b.agarwalla' in text_lower) and
                ('masonry supply' in text_lower or 'masonry supply inc' in text_lower))

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        text_lower = text.lower()

        # Add points for each indicator found
        indicators = [
            'r. b. agarwalla',
            'masonry supply',
            'kolkata',
            'commercial invoice',
            '7325.10.00',
            'non-malleable cast',
            'sanitary casting',
            'tricast'
        ]
        for indicator in indicators:
            if indicator in text_lower:
                score += 0.08

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        patterns = [
            r'Invoice\s*No[:\s]+([A-Z]+/\d+/\d+-\d+)',  # EXP/626/25-26
            r'INVOICE\s+([A-Z]+/\d+/\d+-\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract B/L number as project reference."""
        patterns = [
            r'BILL\s+OF\s+LADING\s+NO[:\s]+([A-Z0-9]+)',
            r'B/L\s*#?\s*:?\s*([A-Z0-9]+)',
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
        # 2025-0725 "840.03 'F' FRAME. GRATE, HOOD" [MS840.03F] 20 190.610 3,812.20
        # 2025-0725 CB-2436 GRATE- HVY & 4"FRAME-TRICAST [MSCB2436/4] 30 127.100 3,813.00
        # Pattern with part code in brackets

        # Pattern 1: Lines with [MSI_PART_CODE] format from COMMERCIAL INVOICE
        # Format: PO_DATE DESCRIPTION [MSI_PART_CODE] SHIPPER_CODE QTY RATE AMOUNT
        # Example: 2025-0429 MBX-1118 Flip Reader Ductile Lid [MSMBX-1118-C-RD] D4592-WM-TC 52 17.760 923.52
        # The shipper code (e.g., D4592-WM-TC, N1509-100) appears after brackets and before quantity
        bracket_pattern = re.compile(
            r'(20\d{2}-\d{4}(?:-NP)?)\s+'                    # PO date (2025-0725 or 2025-0725-NP)
            r'(.+?)\s*'                                       # Description (non-greedy)
            r'\[([A-Z][A-Z0-9\.\-/]+)\]\s*'                  # MSI Part code in brackets [MSMBX-1118-C-RD]
            r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*(?:-TC)?\s+'      # Shipper code (D4592-WM-TC, N1509-100) - skip this
            r'(\d+)\s+'                                       # Quantity
            r'([\d,]+\.\d{2,3})\s+'                          # Unit price
            r'([\d,]+\.\d{2})',                               # Total price
            re.IGNORECASE
        )

        for match in bracket_pattern.finditer(text):
            try:
                po_date = match.group(1)
                description = match.group(2).strip()
                part_number = match.group(3)
                quantity = int(match.group(4))
                unit_price = match.group(5).replace(',', '')
                total_price = match.group(6).replace(',', '')

                item = {
                    'part_number': part_number,
                    'quantity': quantity,
                    'total_price': float(total_price),
                    'po_date': po_date,
                    'unit_price': unit_price,
                    'country_origin': 'INDIA',
                    'hs_code': '7325.10.00',
                }

                # Create deduplication key - use line number to allow true duplicates
                item_key = f"{len(line_items)}_{item['part_number']}_{item['quantity']}_{item['total_price']}"

                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)

            except (IndexError, AttributeError, ValueError) as e:
                continue

        # Debug: log how many items found with bracket pattern
        print(f"[MasonrySupplyAgarwalla] Bracket pattern found {len(line_items)} items")

        # Pattern 2: Lines with N-code at end (e.g., N1523L-F-TC)
        # Looking for lines like: 2025-0725 "840.03 'F' FRAME. GRATE, HOOD" [MS840.03F] 20 190.610 3,812.20
        # followed by: N1523L-F-TC
        # But since they're on different lines in the PDF, try another approach

        # If bracket pattern didn't work well, try a simpler approach
        if len(line_items) < 3:
            print(f"[MasonrySupplyAgarwalla] Bracket pattern found < 3 items, trying simple pattern...")
            # Look for lines with quantity and two prices at the end
            # Pattern: PO_DATE DESCRIPTION QTY RATE AMOUNT
            simple_pattern = re.compile(
                r'(20\d{2}-\d{4}(?:-NP)?)\s+'      # PO date
                r'(.+?)\s+'                         # Description (anything)
                r'(\d+)\s+'                         # Quantity
                r'([\d,]+\.\d{2,3})\s+'            # Unit price
                r'([\d,]+\.\d{2})',                 # Total price
                re.IGNORECASE
            )

            for match in simple_pattern.finditer(text):
                try:
                    po_date = match.group(1)
                    description = match.group(2).strip()
                    quantity = int(match.group(3))
                    unit_price = match.group(4).replace(',', '')
                    total_price = match.group(5).replace(',', '')

                    # Extract MSI part code from description if in brackets
                    # MSI codes look like: [MSMBX-1118-C-RD], [MS840.03F], [MSCB2436/4]
                    part_match = re.search(r'\[([A-Z][A-Z0-9\.\-/]+)\]', description, re.IGNORECASE)
                    if part_match:
                        part_number = part_match.group(1)
                    else:
                        # Skip items without MSI part codes in brackets - they're not from the commercial invoice
                        continue

                    item = {
                        'part_number': part_number,
                        'quantity': quantity,
                        'total_price': float(total_price),
                        'po_date': po_date,
                        'unit_price': unit_price,
                        'country_origin': 'INDIA',
                        'hs_code': '7325.10.00',
                    }

                    item_key = f"{item['part_number']}_{item['quantity']}_{item['total_price']}"

                    if item_key not in seen_items:
                        seen_items.add(item_key)
                        line_items.append(item)

                except (IndexError, ValueError):
                    continue

            print(f"[MasonrySupplyAgarwalla] Simple pattern found {len(line_items)} items total")

        # Convert MSI part numbers to Sigma part numbers
        line_items = self.convert_to_sigma_parts(line_items)

        return line_items

    def convert_to_sigma_parts(self, line_items: List[Dict], db_path: Path = None) -> List[Dict]:
        """
        Convert MSI part numbers to Sigma Corporation part numbers.

        Uses the msi_sigma_parts lookup table to find the corresponding Sigma
        part number for each MSI part extracted from the invoice.

        Args:
            line_items: List of line item dictionaries with 'part_number' field
            db_path: Path to tariffmill.db (if None, uses default location)

        Returns:
            Updated list with Sigma part numbers (original MSI number preserved in 'msi_part_number')
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "tariffmill.db"

        if not db_path.exists():
            return line_items

        # Load the MSI-to-Sigma mapping
        mapping = get_msi_sigma_mapping(db_path)

        if not mapping:
            return line_items

        for item in line_items:
            msi_part = item.get('part_number', '').strip()
            if not msi_part:
                continue

            # Store original MSI part number
            item['msi_part_number'] = msi_part

            # Look up Sigma part number
            msi_upper = msi_part.upper()

            # Try exact match
            if msi_upper in mapping:
                item['part_number'] = mapping[msi_upper]
                item['sigma_matched'] = True
            else:
                matched = False
                # Try with normalized characters (replace / with -, remove dots)
                msi_normalized = msi_upper.replace('/', '-').replace('.', '')
                for msi_key, sigma_value in mapping.items():
                    msi_key_normalized = msi_key.replace('/', '-').replace('.', '')
                    if msi_normalized == msi_key_normalized:
                        item['part_number'] = sigma_value
                        item['sigma_matched'] = True
                        matched = True
                        break

                if not matched:
                    # Try more aggressive normalization - remove ALL hyphens and slashes
                    # This handles cases like MSCB-3838-4 matching MSCB3838-4
                    msi_stripped = re.sub(r'[-/\.]', '', msi_upper)
                    for msi_key, sigma_value in mapping.items():
                        msi_key_stripped = re.sub(r'[-/\.]', '', msi_key.upper())
                        sigma_stripped = re.sub(r'[-/\.]', '', sigma_value.upper())
                        if msi_stripped == msi_key_stripped or msi_stripped == sigma_stripped:
                            item['part_number'] = sigma_value
                            item['sigma_matched'] = True
                            matched = True
                            break

                if not matched:
                    # Check if the part already IS a Sigma part number (reverse lookup)
                    # This handles cases where the invoice already has Sigma format
                    for msi_key, sigma_value in mapping.items():
                        sigma_normalized = sigma_value.upper().replace('/', '-').replace('.', '')
                        if msi_normalized == sigma_normalized:
                            # Part is already in Sigma format
                            item['part_number'] = sigma_value
                            item['sigma_matched'] = True
                            matched = True
                            break

                if not matched:
                    # No match in msi_sigma_parts - try fuzzy matching against parts_master
                    # This handles cases where the Sigma part exists in parts_master but
                    # isn't in the MSI-to-Sigma lookup table yet
                    fuzzy_result = fuzzy_match_part_number(msi_part, db_path, threshold=0.75)
                    if fuzzy_result:
                        matched_part, score = fuzzy_result
                        item['part_number'] = matched_part
                        item['sigma_matched'] = True
                        item['fuzzy_match_score'] = score
                        matched = True
                        print(f"MSI->Sigma: Fuzzy matched '{msi_part}' to '{matched_part}' (score: {score:.2f})")

                if not matched:
                    # No match found - keep original part number but log warning
                    item['sigma_matched'] = False
                    print(f"MSI->Sigma WARNING: No Sigma match found for '{msi_part}' - using original")

        return line_items

    def is_packing_list(self, text: str) -> bool:
        """Check if this is a packing list instead of invoice."""
        text_lower = text.lower()
        # Check for packing list indicators
        if 'packing list' in text_lower:
            # But make sure it's not just mentioned in an invoice
            if 'commercial invoice' not in text_lower:
                return True
        return False

    def get_sigma_part(self, msi_part: str, db_path: Path = None) -> Optional[str]:
        """
        Look up the Sigma Corporation part number for an MSI part number.

        Args:
            msi_part: The MSI part number
            db_path: Path to tariffmill.db

        Returns:
            The Sigma part number, or None if not found
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "tariffmill.db"

        return get_sigma_part_number(msi_part, db_path)

    def find_similar_part(self, part_number: str, db_path: Path = None) -> Optional[Tuple[str, float]]:
        """
        Search for a similar part number in the parts_master database.

        This is useful when a part number extracted from an invoice doesn't
        exactly match what's in the database, but a close match exists.

        Args:
            part_number: The part number to search for
            db_path: Path to tariffmill.db (if None, uses default location)

        Returns:
            Tuple of (matched_part_number, similarity_score) or None if no match
        """
        if db_path is None:
            # Default database location
            db_path = Path(__file__).parent.parent / "tariffmill.db"

        return fuzzy_match_part_number(part_number, db_path, threshold=0.6)

    def normalize_part_numbers(self, line_items: List[Dict], db_path: Path = None) -> List[Dict]:
        """
        Attempt to normalize part numbers by finding matches in the database.

        For each line item, if the part number doesn't exist in the database,
        try to find a similar one. If found, add a 'suggested_part' field.

        Args:
            line_items: List of line item dictionaries from extract_line_items()
            db_path: Path to tariffmill.db

        Returns:
            Updated list with 'suggested_part' and 'match_score' fields added
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "tariffmill.db"

        if not db_path.exists():
            return line_items

        # Get all existing part numbers from database
        try:
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute("SELECT part_number FROM parts_master")
            existing_parts = set(row[0].upper().strip() for row in c.fetchall() if row[0])
            conn.close()
        except Exception:
            return line_items

        for item in line_items:
            part_num = item.get('part_number', '').upper().strip()

            # Check if part already exists in database
            if part_num in existing_parts:
                item['in_database'] = True
                item['suggested_part'] = None
                item['match_score'] = 1.0
            else:
                item['in_database'] = False
                # Try to find a similar part
                match_result = self.find_similar_part(part_num, db_path)
                if match_result:
                    item['suggested_part'] = match_result[0]
                    item['match_score'] = match_result[1]
                else:
                    item['suggested_part'] = None
                    item['match_score'] = 0.0

        return line_items
