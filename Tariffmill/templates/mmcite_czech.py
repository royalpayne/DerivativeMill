"""
mmcité Czech Invoice Template
Handles invoices from mmcité Czech Republic in CZK/USD format.
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class MMCiteCzechTemplate(BaseTemplate):
    """
    Template for mmcité Czech Republic invoices.
    
    Formats handled:
    - Regular invoices with CZK and USD prices
    - Proforma invoices
    - Material composition data (steel/aluminum percentages, weights, values)
    """
    
    name = "mmcité Czech"
    description = "Czech invoices with CZK/USD pricing and material composition"
    client = "mmcité"
    version = "1.0.0"
    
    extra_columns = [
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
        """Check if this is a mmcité Czech invoice."""
        indicators = [
            'mmcité' in text.lower(),
            'CZK' in text,
            'USD' in text,
            re.search(r'variable\s+symbol', text, re.IGNORECASE) is not None,
        ]
        # Must have mmcité and either CZK or variable symbol
        return indicators[0] and (indicators[1] or indicators[3])
    
    def get_confidence_score(self, text: str) -> float:
        """Higher confidence if we see Czech-specific markers."""
        if not self.can_process(text):
            return 0.0
        
        score = 0.5
        if 'CZK' in text:
            score += 0.2
        if re.search(r'variable\s+symbol', text, re.IGNORECASE):
            score += 0.2
        if 'mmcité' in text:
            score += 0.1
        return min(score, 1.0)
    
    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from Czech invoice."""
        patterns = [
            r'Proforma\s+invoice\s+no\.?\s*:?\s*([A-Z0-9]+[a-z]?)',
            r'variable\s+symbol\s*:?\s*(\d+)',
            r'Invoice\s+n\.?\s*:?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "UNKNOWN"
    
    def extract_project_number(self, text: str) -> str:
        """Extract project number from Czech invoice."""
        patterns = [
            r'project\s+n\.?\s*:?\s*(US\d+[A-Z]\d+[a-z]?)',
            r'Customer\s+ref\.?\s+nr\.?\s*:?\s*\d+;\s*(\d+)',
            r'\b(US\d{2}[A-Z]\d{4}[a-z]?)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "UNKNOWN"
    
    def _extract_steel_aluminum_data(self, text: str) -> Dict:
        """Extract material composition data from description text."""
        data = {
            'steel_pct': '',
            'steel_kg': '',
            'steel_value': '',
            'aluminum_pct': '',
            'aluminum_kg': '',
            'aluminum_value': '',
            'net_weight': ''
        }
        
        # Steel percentage
        steel_pct_match = re.search(r'Steel:\s*(\d+(?:[,.]?\d*)?)%', text, re.IGNORECASE)
        if steel_pct_match:
            data['steel_pct'] = steel_pct_match.group(1).replace(',', '.')
        
        # Steel weight - two formats
        steel_kg_compact = re.search(r'Steel:\s*\d+(?:[,.]?\d*)?%[,\s]*(\d+[,.]?\d*)\s*kg', text, re.IGNORECASE)
        steel_kg_spaced = re.search(r'Weight of steel:\s*(\d+[,.]?\d*)\s*kg', text, re.IGNORECASE)
        if steel_kg_compact:
            data['steel_kg'] = steel_kg_compact.group(1).replace(',', '.')
        elif steel_kg_spaced:
            data['steel_kg'] = steel_kg_spaced.group(1).replace(',', '.')
        
        # Value of steel
        steel_value_match = re.search(r'Value of steel:\s*(\d+[,.]?\d*)\s*\$', text, re.IGNORECASE)
        if steel_value_match:
            data['steel_value'] = steel_value_match.group(1).replace(',', '.')
        
        # Aluminum percentage
        aluminum_pct_match = re.search(r'Aluminum:\s*(\d+(?:[,.]?\d*)?)%', text, re.IGNORECASE)
        if aluminum_pct_match:
            data['aluminum_pct'] = aluminum_pct_match.group(1).replace(',', '.')
        
        # Aluminum weight - two formats
        aluminum_kg_compact = re.search(r'Aluminum:\s*\d+(?:[,.]?\d*)?%[,\s]*(\d+[,.]?\d*)\s*kg', text, re.IGNORECASE)
        aluminum_kg_spaced = re.search(r'Weight of aluminum:\s*(\d+[,.]?\d*)\s*kg', text, re.IGNORECASE)
        if aluminum_kg_compact:
            data['aluminum_kg'] = aluminum_kg_compact.group(1).replace(',', '.')
        elif aluminum_kg_spaced:
            data['aluminum_kg'] = aluminum_kg_spaced.group(1).replace(',', '.')
        
        # Value of aluminum
        aluminum_value_match = re.search(r'Value of aluminum:\s*(\d+[,.]?\d*)\s*\$', text, re.IGNORECASE)
        if aluminum_value_match:
            data['aluminum_value'] = aluminum_value_match.group(1).replace(',', '.')
        
        # Net weight
        net_weight_match = re.search(r'Net weight:\s*(\d+[,.]?\d*)\s*kg', text, re.IGNORECASE)
        if net_weight_match:
            data['net_weight'] = net_weight_match.group(1).replace(',', '.')
        
        return data
    
    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from Czech invoice text."""
        line_items = []
        seen_items = set()
        
        lines = text.split('\n')
        
        # Main pattern: part_number project_code quantity unit price_czk vat price_usd
        line_pattern = re.compile(
            r'^([A-Z][A-Z0-9\-]+(?:-[A-Z0-9]+)?)\s+'  # Part number
            r'(US\d+[A-Z]\d+)\s+'                      # Project code
            r'(\d+[,.]?\d*)\s*(?:ks|pc)?\s+'           # Quantity with optional unit
            r'([\d.,]+)\s*(?:CZK)?\s+'                 # Price in CZK
            r'(\d+)\s+'                                 # VAT
            r'([\d.,]+)\s*USD',                        # Price in USD
            re.IGNORECASE
        )
        
        # Simpler pattern
        simple_pattern = re.compile(
            r'^([A-Z][A-Z0-9\-]+(?:-[A-Z0-9]+)?)\s+'  # Part number
            r'(US\d+[A-Z]\d+)\s+'                      # Project code
            r'(\d+[,.]?\d*)\s*(?:ks|pc)?',             # Quantity with optional unit
            re.IGNORECASE
        )
        
        # Proforma pattern (no project code)
        proforma_pattern = re.compile(
            r'^([A-Z][A-Z0-9\-]+(?:-[A-Z0-9]+)?)\s+'  # Part number
            r'(\d+[,.]?\d*)\s*(?:ks|pc)\s+'            # Quantity with unit
            r'([\d.,]+)\s*CZK\s+'                      # Price in CZK
            r'(\d+)\s+'                                 # VAT
            r'([\d.,]+)\s*USD',                        # Price in USD
            re.IGNORECASE
        )
        
        def get_material_data_from_context(start_idx):
            """Look at following lines to find Steel/Aluminum data."""
            context_text = ""
            for j in range(start_idx + 1, min(start_idx + 5, len(lines))):
                next_line = lines[j].strip()
                context_text += " " + next_line
                if 'Steel:' in next_line or 'Aluminum:' in next_line:
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
                if 'Steel:' in next_line or 'Aluminum:' in next_line or 'Net weight:' in next_line:
                    break
                # Skip lines that look like another part number (starts with pattern like XX123)
                if re.match(r'^[A-Z]{2,}[0-9]', next_line):
                    break
                # Skip lines with USD/CZK prices (likely totals or next items)
                if re.search(r'\d+[,.]?\d*\s*(USD|CZK)', next_line):
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

            # Skip header lines
            if 'type / desciption' in line.lower() or 'type / description' in line.lower():
                continue

            # Try main pattern
            match = line_pattern.match(line)
            if match:
                part_number = match.group(1)
                quantity = match.group(3).replace(',', '.')
                price_usd = match.group(6).replace('.', '').replace(',', '.')

                # Skip total lines (Czech word for total)
                if part_number.lower() == 'celkem':
                    continue

                # Skip service fee items (SLU prefix)
                if part_number.upper().startswith('SLU'):
                    continue

                # Skip packaging items (OBAL prefix)
                if part_number.upper().startswith('OBAL'):
                    continue

                material_data = get_material_data_from_context(i)
                description = get_description_from_context(i)

                item_key = f"{part_number}_{quantity}_{price_usd}"
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    item = {
                        'part_number': part_number,
                        'quantity': quantity,
                        'total_price': price_usd,
                        'description': description
                    }
                    item.update(material_data)
                    line_items.append(item)
                continue

            # Try proforma pattern
            proforma_match = proforma_pattern.match(line)
            if proforma_match:
                part_number = proforma_match.group(1)
                quantity = proforma_match.group(2).replace(',', '.')
                price_usd = proforma_match.group(5).replace('.', '').replace(',', '.')

                # Skip total lines (Czech word for total)
                if part_number.lower() == 'celkem':
                    continue

                # Skip service fee items (SLU prefix)
                if part_number.upper().startswith('SLU'):
                    continue

                # Skip packaging items (OBAL prefix)
                if part_number.upper().startswith('OBAL'):
                    continue

                material_data = get_material_data_from_context(i)
                description = get_description_from_context(i)

                item_key = f"{part_number}_{quantity}_{price_usd}"
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    item = {
                        'part_number': part_number,
                        'quantity': quantity,
                        'total_price': price_usd,
                        'description': description
                    }
                    item.update(material_data)
                    line_items.append(item)
                continue

            # Try simple pattern with USD lookup
            simple_match = simple_pattern.match(line)
            if simple_match:
                part_number = simple_match.group(1)
                quantity = simple_match.group(3).replace(',', '.')

                # Skip total lines (Czech word for total)
                if part_number.lower() == 'celkem':
                    continue

                # Skip service fee items (SLU prefix)
                if part_number.upper().startswith('SLU'):
                    continue

                # Skip packaging items (OBAL prefix)
                if part_number.upper().startswith('OBAL'):
                    continue

                usd_match = re.search(r'([\d.,]+)\s*USD\s*$', line)
                if usd_match:
                    price_usd = usd_match.group(1).replace('.', '').replace(',', '.')

                    material_data = get_material_data_from_context(i)
                    description = get_description_from_context(i)

                    item_key = f"{part_number}_{quantity}_{price_usd}"
                    if item_key not in seen_items:
                        seen_items.add(item_key)
                        item = {
                            'part_number': part_number,
                            'quantity': quantity,
                            'total_price': price_usd,
                            'description': description
                        }
                        item.update(material_data)
                        line_items.append(item)
                continue

            # Try proforma simple pattern
            proforma_simple = re.match(r'^([A-Z][A-Z0-9\-]+(?:-[A-Z0-9]+)?)\s+(\d+[,.]?\d*)\s*(?:ks|pc)?', line, re.IGNORECASE)
            if proforma_simple:
                part_number = proforma_simple.group(1)
                quantity = proforma_simple.group(2).replace(',', '.')

                # Skip total lines (Czech word for total)
                if part_number.lower() == 'celkem':
                    continue

                # Skip service fee items (SLU prefix)
                if part_number.upper().startswith('SLU'):
                    continue

                # Skip packaging items (OBAL prefix)
                if part_number.upper().startswith('OBAL'):
                    continue

                usd_match = re.search(r'([\d.,]+)\s*USD\s*$', line)
                if usd_match:
                    price_usd = usd_match.group(1).replace('.', '').replace(',', '.')

                    material_data = get_material_data_from_context(i)
                    description = get_description_from_context(i)

                    item_key = f"{part_number}_{quantity}_{price_usd}"
                    if item_key not in seen_items:
                        seen_items.add(item_key)
                        item = {
                            'part_number': part_number,
                            'quantity': quantity,
                            'total_price': price_usd,
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
            'proforma invoice' in text_lower,
            'variable symbol' in text_lower,
            bool(re.search(r'invoice\s+(?:number|n)\.?\s*:?\s*\d+', text, re.IGNORECASE))
        ])

        # Only mark as packing list if NO invoice markers found
        return not has_invoice_markers

    def extract_manufacturer_name(self, text: str) -> str:
        """
        Extract manufacturer/supplier name from Czech invoice.

        Looks for common patterns in Czech invoices:
        - Company name in header (typically mmcité or similar)
        - Supplier/Seller field

        Returns normalized name for database lookup (without legal suffixes).
        """
        # Pattern 1: Look for "mmcité" variations - capture full match then normalize
        mmcite_patterns = [
            r'mmcit[ée]\s+a\.?s\.?',     # mmcité a.s. -> return "MMCITE AS"
            r'mmcit[ée]\s+s\.?r\.?o\.?',  # mmcité s.r.o. -> return "MMCITE AS" (Czech entity)
            r'mmcit[ée]',                 # Just mmcité -> return "MMCITE AS"
        ]

        for pattern in mmcite_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return normalized name that matches database entry
                return "MMCITE S/A CZECH REPUBLIC"

        # Pattern 2: Look for "Supplier:" or "Seller:" or "Dodavatel:" (Czech for supplier)
        supplier_patterns = [
            r'(?:Supplier|Seller|Dodavatel)\s*:?\s*([A-Za-z0-9\s\.,]+?)(?:\n|$|ID|IČ)',
        ]

        for pattern in supplier_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name and len(name) > 2:
                    return name

        return ""
