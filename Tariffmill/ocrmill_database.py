"""
OCRMill Database Extensions for TariffMill
Extends TariffMill's database with OCR invoice processing capabilities.
"""

import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
import re


class PartDescriptionExtractor:
    """
    Extracts product descriptions from part numbers and maps to HTS codes.
    """

    PREFIX_DESCRIPTIONS = {
        'SL': 'Seat/Seating element',
        'SLE': 'Seat element',
        'SLU': 'Seating unit',
        'BTT': 'Bench',
        'BEN': 'Bench',
        'STE': 'Bicycle stand/rack',
        'BIKE': 'Bicycle rack',
        'LPU': 'Planter/Flower pot',
        'PLT': 'Planter',
        'ND': 'Bollard',
        'BOL': 'Bollard',
        'PQA': 'Table',
        'TAB': 'Table',
        'TBL': 'Table',
        'KSA': 'Litter bin/Waste receptacle',
        'BIN': 'Litter bin',
        'WASTE': 'Waste receptacle',
        'MRU': 'Tree grate',
        'TREE': 'Tree grate',
        'BAR': 'Barrier',
        'FENCE': 'Fence/Fencing',
        'LIGHT': 'Light/Lighting',
        'LAMP': 'Lamp',
        'ACC': 'Accessory',
        'MOUNT': 'Mounting accessory',
        'ANCHOR': 'Anchor/Fixing',
        'OBAL': 'Packaging/Crating',
        'SIGN': 'Signage',
        'POST': 'Post',
    }

    DESCRIPTION_TO_HTS = {
        'SEAT': '9403.20.0080',
        'BENCH': '9401.69.8031',
        'BICYCLE': '9403.20.0082',
        'BIKE': '9403.20.0082',
        'STAND': '9403.20.0082',
        'RACK': '9403.20.0082',
        'PLANTER': '9403.20.0080',
        'FLOWER': '9403.20.0080',
        'POT': '9403.20.0080',
        'BOLLARD': '7308.90.6000',
        'TABLE': '9403.20.0080',
        'LITTER': '7310.29.0050',
        'WASTE': '7310.29.0050',
        'BIN': '7310.29.0050',
        'RECEPTACLE': '7310.29.0050',
        'TREE GRATE': '7326.90.8688',
        'GRATE': '7326.90.8688',
        'BARRIER': '7308.90.9590',
        'FENCE': '7308.90.9590',
        'FENCING': '7308.90.9590',
        'LIGHT': '9405.40.8000',
        'LAMP': '9405.40.8000',
        'LIGHTING': '9405.40.8000',
        'SIGN': '9405.60.8000',
        'SIGNAGE': '9405.60.8000',
        'POST': '7308.90.3000',
        'ANCHOR': '7318.15.2095',
        'BOLT': '7318.15.2095',
        'FIXING': '7318.15.2095',
        'MOUNT': '7326.90.8688',
    }

    def extract_description(self, part_number: str) -> str:
        """Extract description from part number."""
        if not part_number:
            return ""

        part_upper = part_number.upper()

        for prefix in sorted(self.PREFIX_DESCRIPTIONS.keys(), key=len, reverse=True):
            if part_upper.startswith(prefix):
                base_desc = self.PREFIX_DESCRIPTIONS[prefix]
                details = self._extract_details(part_number, prefix)
                if details:
                    return f"{base_desc} - {details}"
                return base_desc

        return f"Product {part_number}"

    def _extract_details(self, part_number: str, prefix: str) -> str:
        """Extract additional details from part number."""
        detail_part = part_number[len(prefix):]
        model_match = re.search(r'(\d{3,4})', detail_part)
        if model_match:
            return f"Model {model_match.group(1)}"
        return ""

    def find_hts_from_description(self, description: str) -> Optional[str]:
        """Find HTS code based on product description."""
        if not description:
            return None

        desc_upper = description.upper()
        for keyword in sorted(self.DESCRIPTION_TO_HTS.keys(), key=len, reverse=True):
            if keyword in desc_upper:
                return self.DESCRIPTION_TO_HTS[keyword]
        return None

    def match_with_hts_database(self, description: str, hts_database: List[Dict]) -> Optional[str]:
        """Match description against HTS database entries."""
        if not description or not hts_database:
            return None

        desc_words = set(description.upper().split())
        best_match = None
        best_score = 0

        for entry in hts_database:
            hts_desc = entry.get('description', '')
            if not hts_desc:
                continue

            hts_words = set(hts_desc.upper().split())
            overlap = len(desc_words & hts_words)

            if overlap > best_score:
                best_score = overlap
                best_match = entry.get('hts_code')

        return best_match if best_score > 0 else None


class OCRMillDatabase:
    """
    Database extensions for OCRMill invoice processing.
    Uses TariffMill's existing database with additional OCRMill tables.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.description_extractor = PartDescriptionExtractor()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def add_part_occurrence(self, part_data: Dict) -> bool:
        """
        Add a new part occurrence from invoice processing.

        Args:
            part_data: Dictionary containing part information

        Returns:
            bool: True if successful
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            part_number = part_data.get('part_number')
            if not part_number:
                conn.close()
                return False

            # Extract description if not provided
            if not part_data.get('description'):
                part_data['description'] = self.description_extractor.extract_description(part_number)

            # Check for FSC certification in description
            description = part_data.get('description', '')
            if 'FSC 100%' in description or 'FSC100%' in description.replace(' ', ''):
                part_data['fsc_certified'] = 'FSC 100%'
                part_data['fsc_certificate_code'] = 'PBN-COC-065387'
            elif 'FSC' in description.upper():
                part_data['fsc_certified'] = 'FSC'

            # Try to find HTS code if not provided
            if not part_data.get('hts_code'):
                hts_code = self.description_extractor.find_hts_from_description(part_data['description'])
                if not hts_code:
                    cursor.execute("SELECT * FROM hts_codes")
                    hts_database = [dict(row) for row in cursor.fetchall()]
                    hts_code = self.description_extractor.match_with_hts_database(
                        part_data['description'], hts_database
                    )
                if hts_code:
                    part_data['hts_code'] = hts_code

            # Calculate unit price if not provided
            unit_price = part_data.get('unit_price')
            if not unit_price and part_data.get('total_price') and part_data.get('quantity'):
                try:
                    unit_price = float(part_data['total_price']) / float(part_data['quantity'])
                except (ValueError, ZeroDivisionError):
                    unit_price = None

            # Insert occurrence
            cursor.execute("""
                INSERT INTO part_occurrences (
                    part_number, invoice_number, project_number, quantity, total_price, unit_price,
                    steel_pct, steel_kg, steel_value,
                    aluminum_pct, aluminum_kg, aluminum_value,
                    net_weight, ncm_code, hts_code, processed_date, source_file, mid, client_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                part_number,
                part_data.get('invoice_number'),
                part_data.get('project_number'),
                part_data.get('quantity'),
                part_data.get('total_price'),
                unit_price,
                part_data.get('steel_pct'),
                part_data.get('steel_kg'),
                part_data.get('steel_value'),
                part_data.get('aluminum_pct'),
                part_data.get('aluminum_kg'),
                part_data.get('aluminum_value'),
                part_data.get('net_weight'),
                part_data.get('ncm_code'),
                part_data.get('hts_code'),
                datetime.now().isoformat(),
                part_data.get('source_file'),
                part_data.get('mid'),
                part_data.get('client_code')
            ))

            # Update or create part master record
            self._update_part_master(cursor, part_number, part_data)

            conn.commit()
            conn.close()
            return True

    def _update_part_master(self, cursor, part_number: str, part_data: Dict):
        """Update the parts_master table with latest occurrence data."""
        # Check if part exists
        cursor.execute("SELECT part_number FROM parts_master WHERE part_number = ?", (part_number,))
        exists = cursor.fetchone() is not None

        # Get latest material percentages from most recent occurrence
        cursor.execute("""
            SELECT steel_pct, aluminum_pct, processed_date
            FROM part_occurrences
            WHERE part_number = ?
            ORDER BY processed_date DESC
            LIMIT 1
        """, (part_number,))
        latest = cursor.fetchone()

        if exists:
            # Update existing part - HTS_CODE is NEVER updated from PDF (database is master)
            def clean_value(value):
                if value is None:
                    return None
                str_val = str(value).strip()
                return str_val if str_val else None

            new_mid = clean_value(part_data.get('mid'))
            new_country = clean_value(part_data.get('country_origin'))
            new_client = clean_value(part_data.get('client_code'))
            new_fsc_cert = clean_value(part_data.get('fsc_certified'))
            new_fsc_code = clean_value(part_data.get('fsc_certificate_code'))
            new_description = clean_value(part_data.get('description'))

            # Convert percentages to TariffMill's 0-100 format if needed
            steel_ratio = latest['steel_pct'] if latest else part_data.get('steel_pct')
            aluminum_ratio = latest['aluminum_pct'] if latest else part_data.get('aluminum_pct')

            cursor.execute("""
                UPDATE parts_master SET
                    description = COALESCE(?, description),
                    steel_ratio = COALESCE(?, steel_ratio),
                    aluminum_ratio = COALESCE(?, aluminum_ratio),
                    mid = COALESCE(?, mid),
                    country_origin = COALESCE(?, country_origin),
                    client_code = COALESCE(?, client_code),
                    fsc_certified = COALESCE(?, fsc_certified),
                    fsc_certificate_code = COALESCE(?, fsc_certificate_code),
                    last_updated = ?
                WHERE part_number = ?
            """, (
                new_description,
                steel_ratio,
                aluminum_ratio,
                new_mid,
                new_country,
                new_client,
                new_fsc_cert,
                new_fsc_code,
                datetime.now().isoformat(),
                part_number
            ))
        else:
            # Insert new part
            cursor.execute("""
                INSERT INTO parts_master (
                    part_number, description, hts_code, steel_ratio, aluminum_ratio,
                    mid, country_origin, client_code, fsc_certified, fsc_certificate_code, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                part_number,
                part_data.get('description'),
                part_data.get('hts_code'),
                latest['steel_pct'] if latest else part_data.get('steel_pct'),
                latest['aluminum_pct'] if latest else part_data.get('aluminum_pct'),
                part_data.get('mid'),
                part_data.get('country_origin'),
                part_data.get('client_code'),
                part_data.get('fsc_certified'),
                part_data.get('fsc_certificate_code'),
                datetime.now().isoformat()
            ))

    def get_part_history(self, part_number: str) -> List[Dict]:
        """Get complete history of a part across all invoices."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM part_occurrences
            WHERE part_number = ?
            ORDER BY processed_date DESC
        """, (part_number,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_parts_by_invoice(self, invoice_number: str) -> List[Dict]:
        """Get all parts on a specific invoice."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM part_occurrences
            WHERE invoice_number = ?
            ORDER BY part_number
        """, (invoice_number,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_parts_by_project(self, project_number: str) -> List[Dict]:
        """Get all parts for a specific project."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.*, po.quantity, po.total_price
            FROM parts_master p
            JOIN part_occurrences po ON p.part_number = po.part_number
            WHERE po.project_number = ?
            ORDER BY p.part_number
        """, (project_number,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def search_parts(self, search_term: str) -> List[Dict]:
        """Search parts by part number or description."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM parts_master
            WHERE part_number LIKE ? OR description LIKE ?
            ORDER BY part_number
        """, (f'%{search_term}%', f'%{search_term}%'))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def find_hts_code(self, part_number: str, description: str = "") -> Optional[str]:
        """Find HTS code for a part using fuzzy matching."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # First check if part already has HTS code in parts_master
        cursor.execute("SELECT hts_code FROM parts_master WHERE part_number = ? AND hts_code IS NOT NULL", (part_number,))
        result = cursor.fetchone()
        if result and result['hts_code']:
            conn.close()
            return result['hts_code']

        # Try to match based on description keywords
        if description:
            keywords = description.upper().split()
            for keyword in keywords:
                if len(keyword) > 3:
                    cursor.execute("""
                        SELECT hts_code, description
                        FROM hts_codes
                        WHERE UPPER(description) LIKE ?
                        ORDER BY LENGTH(description)
                        LIMIT 1
                    """, (f'%{keyword}%',))
                    result = cursor.fetchone()
                    if result:
                        conn.close()
                        return result['hts_code']

        conn.close()

        # Use description extractor as fallback
        return self.description_extractor.find_hts_from_description(description)

    def load_hts_mapping(self, xlsx_path: Path) -> bool:
        """Load HTS code mapping from Excel file."""
        try:
            df = pd.read_excel(xlsx_path)
            conn = self._get_connection()
            cursor = conn.cursor()

            seen_hts = set()

            for _, row in df.iterrows():
                hts_code = str(row.get('HTS', row.get('hts_code', '')))
                if hts_code in seen_hts or not hts_code:
                    continue

                seen_hts.add(hts_code)

                cursor.execute("""
                    INSERT OR REPLACE INTO hts_codes (hts_code, description, suggested, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (
                    hts_code,
                    str(row.get('DESCRIPTION', row.get('description', ''))),
                    str(row.get('SUGGESTED', row.get('suggested', ''))),
                    datetime.now().isoformat()
                ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error loading HTS mapping: {e}")
            return False

    def get_statistics(self) -> Dict:
        """Get database statistics for OCRMill."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM parts_master")
        total_parts = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM part_occurrences")
        total_occurrences = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(DISTINCT invoice_number) as count FROM part_occurrences")
        total_invoices = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(DISTINCT project_number) as count FROM part_occurrences")
        total_projects = cursor.fetchone()['count']

        cursor.execute("SELECT SUM(total_price) as total FROM part_occurrences")
        result = cursor.fetchone()
        total_value = result['total'] if result['total'] else 0

        cursor.execute("SELECT COUNT(*) as count FROM parts_master WHERE hts_code IS NOT NULL AND hts_code != ''")
        parts_with_hts = cursor.fetchone()['count']

        conn.close()

        return {
            'total_parts': total_parts,
            'total_occurrences': total_occurrences,
            'total_invoices': total_invoices,
            'total_projects': total_projects,
            'total_value': total_value,
            'parts_with_hts': parts_with_hts,
            'hts_coverage_pct': (parts_with_hts / total_parts * 100) if total_parts > 0 else 0
        }

    def get_recent_occurrences(self, limit: int = 100) -> List[Dict]:
        """Get most recent part occurrences."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM part_occurrences
            ORDER BY processed_date DESC
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def export_occurrences_to_csv(self, output_path: Path, invoice_number: str = None) -> bool:
        """Export part occurrences to CSV."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if invoice_number:
            cursor.execute("SELECT * FROM part_occurrences WHERE invoice_number = ? ORDER BY part_number", (invoice_number,))
        else:
            cursor.execute("SELECT * FROM part_occurrences ORDER BY processed_date DESC")

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return False

        df = pd.DataFrame([dict(row) for row in rows])
        df.to_csv(output_path, index=False)
        return True

    def get_manufacturer_by_name(self, company_name: str) -> Optional[Dict]:
        """Get manufacturer by company name from mid_table."""
        if not company_name:
            return None

        import unicodedata
        def normalize(s):
            return ''.join(
                c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn'
            ).lower()

        normalized_search = normalize(company_name)

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mid_table")

        candidates = []
        for row in cursor.fetchall():
            db_name = row['manufacturer_name'] or ''
            normalized_db = normalize(db_name)

            if normalized_db == normalized_search:
                conn.close()
                return dict(row)

            if normalized_search in normalized_db or normalized_db in normalized_search:
                score = min(len(normalized_search), len(normalized_db)) / max(len(normalized_search), len(normalized_db))
                candidates.append((score, row))

        conn.close()

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return dict(candidates[0][1])

        return None

    def get_manufacturer_by_mid(self, mid: str) -> Optional[Dict]:
        """Get manufacturer by MID from mid_table."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mid_table WHERE mid = ?", (mid,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
