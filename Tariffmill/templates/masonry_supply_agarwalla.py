"""
MasonrySupplyAgarwallaTemplate - Template for R. B. Agarwalla & Co. invoices to Masonry Supply Inc.
"""

import re
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .base_template import BaseTemplate

logger = logging.getLogger(__name__)


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
    Optimized for MSI-to-Sigma part number matching.
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

    # Strip all non-alphanumeric and compare
    s1_stripped = re.sub(r'[^A-Z0-9]', '', s1)
    s2_stripped = re.sub(r'[^A-Z0-9]', '', s2)

    if s1_stripped == s2_stripped:
        return 0.92

    if s1_stripped in s2_stripped or s2_stripped in s1_stripped:
        return 0.82

    # Numeric portion match (for codes like 840.03, 2436, etc.)
    nums1 = re.findall(r'\d+', s1)
    nums2 = re.findall(r'\d+', s2)

    if nums1 and nums2:
        # Check if main numeric codes match
        if nums1[0] == nums2[0]:
            # Also check if there's letter prefix match
            prefix1 = re.match(r'^[A-Z]+', s1_clean)
            prefix2 = re.match(r'^[A-Z]+', s2_clean)
            if prefix1 and prefix2 and prefix1.group() == prefix2.group():
                return 0.88  # Strong match: same prefix and number
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

        # R.B. Agarwalla invoice format from PDF:
        # The data is split across multiple lines:
        # Line 1: PO_DATE DESCRIPTION [MSI_PART_CODE]
        # Line 2: ADDITIONAL_DESC SHIPPER_CODE QTY RATE AMOUNT
        #
        # Example from PDF:
        # 2025-0429 MBX-1118 Flip Reader Ductile Lid [MSMBX-1118-C-RD]
        #           WATER METER/TRICAST D4592-WM-TC 52 17.760 923.52
        #
        # OCR may have issues with brackets - try multiple bracket-like characters

        logger.info(f"[MasonrySupplyAgarwalla] Processing text of length {len(text)}")

        # OCR often misreads brackets as letters. The actual format from PDF is:
        # [MSPART-CODE] QTY RATE AMOUNT
        # But OCR renders [MS... as lMs... or IMS... (bracket becomes I or l)
        #
        # Examples from actual OCR output:
        # - [MSMBX-1118-C-RD] 52 17.760 923.52
        # - lMs840.03El 8 188.560 1,508.48
        # - IMSCB,74] 32 190.650 6,100.80
        #
        # We only need: MSI part number, quantity, total price (and invoice number from header)

        msi_matches = []

        # Pattern: Look for MSI codes followed by QTY RATE AMOUNT
        # MSI codes start with [ or l or I (OCR'd bracket), then MS...
        msi_pattern = re.compile(
            r'[lI\[\(]\s*'                             # Opening bracket (OCR'd as l, I, [, or ()
            r'(MS[A-Z0-9\.\-/,]+)'                     # MSI Part code (starts with MS)
            r'[\]lI1\)]?\s+'                           # Optional closing bracket
            r'(\d+)\s+'                                # Quantity
            r'([\d,]+\.\d{2,3})\s+'                    # Unit price
            r'([\d,]+\.\d{2})',                        # Total price
            re.IGNORECASE
        )

        msi_matches = list(msi_pattern.finditer(text))

        if msi_matches:
            logger.info(f"[MasonrySupplyAgarwalla] Found {len(msi_matches)} items with MSI pattern")
        else:
            logger.info("[MasonrySupplyAgarwalla] No MSI codes found with primary pattern")

        # Process matches (4 groups: msi, qty, rate, amount)
        for i, msi_match in enumerate(msi_matches):
            try:
                msi_part = msi_match.group(1)
                quantity = int(msi_match.group(2))
                unit_price = msi_match.group(3).replace(',', '')
                total_price = msi_match.group(4).replace(',', '')

                # Clean up MSI part code - fix OCR artifacts
                # 1. Remove trailing characters that are OCR'd brackets
                msi_part = re.sub(r'[lI1]$', '', msi_part)
                # 2. Replace commas with hyphens (OCR often reads - as ,)
                msi_part = msi_part.replace(',', '-')
                # 3. Replace lowercase 's' at end of numbers with '5' (OCR error)
                msi_part = re.sub(r'(\d)s\b', r'\g<1>5', msi_part)
                # 4. Replace 'x' with 'X' for consistency
                msi_part = msi_part.replace('x', 'X')
                # 5. Replace '.s' with '.5' (common OCR error for decimals)
                msi_part = msi_part.replace('.s', '.5')
                # 6. Convert to uppercase for consistency
                msi_part = msi_part.upper()
                # 7. Fix common OCR patterns: rD -> RD, wH -> WH, etc.
                msi_part = re.sub(r'([A-Z])([a-z])', lambda m: m.group(1) + m.group(2).upper(), msi_part)

                item = {
                    'part_number': msi_part,
                    'quantity': quantity,
                    'total_price': float(total_price),
                    'unit_price': unit_price,
                    'country_origin': 'INDIA',
                    'hs_code': '7325.10.00',
                }

                item_key = f"{msi_part}_{quantity}_{total_price}"

                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)
                    logger.info(f"[MasonrySupplyAgarwalla] Extracted: {msi_part} qty={quantity} price={total_price}")

            except (IndexError, AttributeError, ValueError) as e:
                logger.info(f"[MasonrySupplyAgarwalla] Error processing match: {e}")
                continue

        logger.info(f"[MasonrySupplyAgarwalla] Total: Found {len(msi_matches)} matches, extracted {len(line_items)} items")

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
                    # Use lower threshold (0.5) to catch more potential matches
                    fuzzy_result = fuzzy_match_part_number(msi_part, db_path, threshold=0.5)
                    if fuzzy_result:
                        matched_part, score = fuzzy_result
                        item['part_number'] = matched_part
                        item['sigma_matched'] = True
                        item['fuzzy_match_score'] = score
                        matched = True
                        logger.info(f"MSI->Sigma: Fuzzy matched '{msi_part}' to '{matched_part}' (score: {score:.2f})")

                if not matched:
                    # Try matching by extracting core part identifier
                    # MSI format: MSMBX-1324-C-RD -> try matching "MBX-1324" or "1324"
                    core_match = re.search(r'MS([A-Z]+)-?(\d+)', msi_upper)
                    if core_match:
                        prefix = core_match.group(1)  # e.g., "MBX"
                        number = core_match.group(2)  # e.g., "1324"
                        # Search for parts containing this number
                        fuzzy_result = fuzzy_match_part_number(f"{prefix}-{number}", db_path, threshold=0.5)
                        if fuzzy_result:
                            matched_part, score = fuzzy_result
                            item['part_number'] = matched_part
                            item['sigma_matched'] = True
                            item['fuzzy_match_score'] = score
                            matched = True
                            logger.info(f"MSI->Sigma: Core matched '{msi_part}' to '{matched_part}' (score: {score:.2f})")

                if not matched:
                    # No match found - keep original part number but log warning
                    item['sigma_matched'] = False
                    logger.warning(f"MSI->Sigma: No match found for '{msi_part}' - using original")

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
