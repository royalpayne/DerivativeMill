"""
mmcité Brazilian Invoice Template
Handles invoices from mmcité Brazil with NCM/HTS codes.
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class MMCiteBrazilianTemplate(BaseTemplate):
    """
    Template for mmcité Brazilian invoices.
    
    Format: PartNumber NCM_Code HTS_Code UnitPrice VAT Quantity TotalPrice
    Example: SL505 94032090 9403.20.0080 105,60 USD 0,00 3,00 316,80 USD
    """
    
    name = "mmcité Brazilian"
    description = "Brazilian invoices with NCM/HTS codes"
    client = "mmcité"
    version = "1.0.0"
    
    extra_columns = [
        'ncm_code',
        'hts_code',
        'unit_price',
        'steel_pct',
        'steel_kg',
        'steel_value',
        'aluminum_pct',
        'aluminum_kg',
        'aluminum_value',
        'net_weight',
        'bol_gross_weight'
    ]
    
    def can_process(self, text: str) -> bool:
        """Check if this is a mmcité Brazilian invoice."""
        # Look for NCM and HTS code patterns
        has_ncm = bool(re.search(r'\b\d{8}\b', text))  # 8-digit NCM code
        has_hts = bool(re.search(r'\d{4}\.\d{2}\.\d{4}', text))  # HTS format
        has_brazil = 'brazil' in text.lower() or 'brasil' in text.lower()
        
        return has_ncm and has_hts
    
    def get_confidence_score(self, text: str) -> float:
        """Higher confidence if we see Brazilian-specific markers."""
        if not self.can_process(text):
            return 0.0
        
        score = 0.5
        if 'brazil' in text.lower() or 'brasil' in text.lower():
            score += 0.3
        if re.search(r'\d{4}\.\d{2}\.\d{4}', text):  # HTS code
            score += 0.2
        return min(score, 1.0)
    
    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from Brazilian invoice."""
        patterns = [
            r'Invoice\s+n\.?\s*:?\s*(\d+)',
            r'variable\s+symbol\s*:?\s*(\d+)',
            r'Nota\s+Fiscal\s*:?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "UNKNOWN"
    
    def extract_project_number(self, text: str) -> str:
        """Extract project number from Brazilian invoice."""
        patterns = [
            r'project\s+n\.?\s*:?\s*(US\d+[A-Z]\d+[a-z]?)',
            r'\b(US\d{2}[A-Z]\d{4}[a-z]?)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "UNKNOWN"
    
    def _extract_steel_aluminum_data(self, text: str) -> Dict:
        """Extract steel and aluminum material composition data from description text."""
        data = {
            'steel_pct': '',
            'steel_kg': '',
            'steel_value': '',
            'aluminum_pct': '',
            'aluminum_kg': '',
            'aluminum_value': '',
            'net_weight': ''
        }

        # Cost of steel: 109 USD
        steel_cost_match = re.search(r'Cost of steel:\s*(\d+(?:[,.]\d+)?)\s*USD', text, re.IGNORECASE)
        if steel_cost_match:
            data['steel_value'] = steel_cost_match.group(1).replace(',', '.')

        # Weight of steel: 20,72 kg
        steel_weight_match = re.search(r'Weight of steel:\s*(\d+(?:[,.]\d+)?)\s*kg', text, re.IGNORECASE)
        if steel_weight_match:
            data['steel_kg'] = steel_weight_match.group(1).replace(',', '.')

        # Cost of aluminium: 0 USD or Cost of aluminum: 0 USD
        aluminum_cost_match = re.search(r'Cost of alumin[iu]um:\s*(\d+(?:[,.]\d+)?)\s*USD', text, re.IGNORECASE)
        if aluminum_cost_match:
            data['aluminum_value'] = aluminum_cost_match.group(1).replace(',', '.')

        # Weight of aluminium: 0 kg or Weight of aluminum: 0 kg
        aluminum_weight_match = re.search(r'Weight of alumin[iu]um:\s*(\d+(?:[,.]\d+)?)\s*kg', text, re.IGNORECASE)
        if aluminum_weight_match:
            data['aluminum_kg'] = aluminum_weight_match.group(1).replace(',', '.')

        # Net weight: 7,9kg
        net_weight_match = re.search(r'Net weight:\s*(\d+(?:[,.]\d+)?)\s*kg', text, re.IGNORECASE)
        if net_weight_match:
            data['net_weight'] = net_weight_match.group(1).replace(',', '.')

        # Calculate percentages if we have weights
        try:
            if data['net_weight'] and data['steel_kg']:
                steel_kg = float(data['steel_kg'])
                net_kg = float(data['net_weight'])
                if net_kg > 0:
                    data['steel_pct'] = str(round((steel_kg / net_kg) * 100))

            if data['net_weight'] and data['aluminum_kg']:
                aluminum_kg = float(data['aluminum_kg'])
                net_kg = float(data['net_weight'])
                if net_kg > 0:
                    data['aluminum_pct'] = str(round((aluminum_kg / net_kg) * 100))
        except (ValueError, ZeroDivisionError):
            pass

        return data

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from Brazilian invoice text."""
        line_items = []
        seen_items = set()

        lines = text.split('\n')

        # Brazilian format pattern
        # part_number ncm_code hts_code unit_price_usd vat quantity total_price_usd
        brazilian_pattern = re.compile(
            r'^([A-Za-z0-9][A-Za-z0-9\-_\.]+(?:\s*\([^)]+\))?)\s+'  # Part number
            r'(\d{8})\s+'                              # NCM code (8 digits)
            r'(\d{4}\.\d{2}\.\d{4})\s+'                # HTS code
            r'([\d.,]+)\s*USD\s+'                      # Unit price in USD
            r'([\d.,]+)\s+'                            # VAT
            r'([\d.,]+)\s+'                            # Quantity
            r'([\d.,]+)\s*USD',                        # Total price in USD
            re.IGNORECASE
        )

        def get_material_data_from_context(start_idx):
            """Look at following lines to find Steel/Aluminum data."""
            context_text = ""
            for j in range(start_idx + 1, min(start_idx + 8, len(lines))):  # Look up to 7 lines ahead
                next_line = lines[j].strip()
                context_text += " " + next_line
                if 'Cost of steel:' in next_line or 'Weight of steel:' in next_line:
                    return self._extract_steel_aluminum_data(context_text)
            return self._extract_steel_aluminum_data(context_text)

        def get_description_from_context(start_idx):
            """
            Look at following 3 lines to find product description text.
            Descriptions typically appear on lines below the part number line.
            Skip lines that are material data, prices, or other part numbers.
            """
            description_parts = []
            for j in range(start_idx + 1, min(start_idx + 4, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue
                # Skip material composition lines
                if any(x in next_line for x in ['Steel:', 'Aluminum:', 'Net weight:', 'Weight of', 'Cost of']):
                    break
                # Skip lines that look like another part number with NCM code (8 digits)
                if re.match(r'^[A-Za-z0-9][A-Za-z0-9\-_\.]+\s+\d{8}\s+', next_line):
                    break
                # Skip lines with USD prices (likely totals or next items)
                if re.search(r'\d+[,.]?\d*\s*USD', next_line):
                    break
                # Skip lines that are just numbers
                if re.match(r'^[\d,.\s]+$', next_line):
                    continue
                # This looks like description text
                description_parts.append(next_line)

            return ' '.join(description_parts) if description_parts else ""

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            match = brazilian_pattern.match(line)
            if match:
                part_number = match.group(1).strip()
                ncm_code = match.group(2)
                hts_code = match.group(3)
                unit_price = match.group(4).replace('.', '').replace(',', '.')
                quantity = match.group(6).replace(',', '.')
                total_price = match.group(7).replace('.', '').replace(',', '.')

                # Get material composition data and description from following lines
                material_data = get_material_data_from_context(i)
                description = get_description_from_context(i)

                item_key = f"{part_number}_{quantity}_{total_price}"
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    item = {
                        'part_number': part_number,
                        'quantity': quantity,
                        'total_price': total_price,
                        'ncm_code': ncm_code,
                        'hts_code': hts_code,
                        'unit_price': unit_price,
                        'description': description
                    }
                    item.update(material_data)
                    line_items.append(item)

        return line_items

    def is_packing_list(self, text: str) -> bool:
        """
        Check if document is ONLY a packing list.
        mmcité PDFs often contain both invoice and packing list pages.
        Only skip if there's NO invoice data.
        """
        text_lower = text.lower()

        # Check if packing list text exists
        has_packing_list = 'packing list' in text_lower or 'packing slip' in text_lower

        if not has_packing_list:
            return False

        # Check if there's also invoice data
        has_invoice_markers = any([
            'invoice n.' in text_lower,
            'nota fiscal' in text_lower,
            'variable symbol' in text_lower,
            bool(re.search(r'invoice\s+(?:number|n)\.?\s*:?\s*\d+', text, re.IGNORECASE))
        ])

        # Only mark as packing list if NO invoice markers found
        return not has_invoice_markers

    def extract_manufacturer_name(self, text: str) -> str:
        """
        Extract manufacturer/supplier name from Brazilian invoice.

        Looks for common patterns in Brazilian invoices:
        - Company name in header (typically mmcité or similar)
        - Exporter/Supplier field

        Returns normalized name for database lookup (without legal suffixes).
        """
        # Pattern 1: Look for "mmcité" Brazil variations
        brazil_patterns = [
            r'mmcit[ée]\s+(?:do\s+)?brasil',  # mmcité do Brasil or mmcité brasil
            r'mmcit[ée]\s+ltda',               # mmcité Ltda
        ]

        for pattern in brazil_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "MMCITE S/A BRAZIL"

        # Pattern 2: Just "mmcité" without Brazil context - assume Czech
        if re.search(r'mmcit[ée]', text, re.IGNORECASE):
            # Check if Brazil is mentioned elsewhere
            if re.search(r'brasil|brazil', text, re.IGNORECASE):
                return "MMCITE S/A BRAZIL"
            return "MMCITE S/A CZECH REPUBLIC"

        # Pattern 3: Look for "Exporter:" or "Exportador:" or "Supplier:"
        supplier_patterns = [
            r'(?:Exporter|Exportador|Supplier|Fornecedor)\s*:?\s*([A-Za-z0-9\s\.,]+?)(?:\n|$|CNPJ|ID)',
        ]

        for pattern in supplier_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name and len(name) > 2:
                    return name

        return ""
