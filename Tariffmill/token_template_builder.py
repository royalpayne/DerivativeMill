"""
Token-Based Template Builder for TariffMill

A smarter approach to template generation that uses data shape recognition
instead of rigid regex patterns or column positions.

Key Concepts:
- Tokenize text into classified tokens (DATE, CODE, INTEGER, DECIMAL, CURRENCY, etc.)
- Detect patterns by finding repeating token sequences
- User maps token types to field names
- Generates extraction code based on token patterns, not regex

This handles inconsistent layouts because it matches WHAT the data IS,
not WHERE it is positioned.
"""

import re
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class TokenType(Enum):
    """Classification of token data types."""
    # Dates
    DATE_ISO = auto()          # 2025-01-15
    DATE_US = auto()           # 01/15/2025, 1/15/25
    DATE_EU = auto()           # 15/01/2025, 15.01.2025
    DATE_COMPACT = auto()      # 20250115, 2025-0115

    # Numbers
    INTEGER = auto()           # 100, 1000, 1,000
    DECIMAL = auto()           # 100.50, 1,234.56
    CURRENCY = auto()          # $100.50, USD 100.50
    PERCENTAGE = auto()        # 15%, 15.5%

    # Codes and identifiers
    PART_CODE = auto()         # ABC-123, 18-123456, MS840.03F
    BRACKETED_CODE = auto()    # [MS840.03F], (ABC123)
    HTS_CODE = auto()          # 7325.10.00, 8481.80.9050
    PO_NUMBER = auto()         # 40012345 (8-digit), PO-12345
    INVOICE_CODE = auto()      # INV-2025-001, EXP/626/25-26

    # Text
    WORD = auto()              # Single word
    PHRASE = auto()            # Multi-word (quoted or descriptive)
    UNIT = auto()              # PCS, KG, EA, UNITS, M
    COUNTRY = auto()           # CHINA, INDIA, USA

    # Structural
    SEPARATOR = auto()         # |, -, :, etc.
    EMPTY = auto()             # Empty/whitespace
    UNKNOWN = auto()           # Unclassified


@dataclass
class Token:
    """A classified token from the text."""
    value: str
    token_type: TokenType
    position: int              # Position in line
    confidence: float = 1.0    # How confident in the classification

    def __repr__(self):
        return f"{self.token_type.name}({self.value!r})"


@dataclass
class TokenizedLine:
    """A line broken into classified tokens."""
    line_number: int
    raw_text: str
    tokens: List[Token]

    @property
    def token_signature(self) -> str:
        """Get the token type signature for pattern matching."""
        return " ".join(t.token_type.name for t in self.tokens if t.token_type != TokenType.EMPTY)

    @property
    def simplified_signature(self) -> str:
        """Get simplified signature (group similar types)."""
        type_map = {
            TokenType.DATE_ISO: 'DATE',
            TokenType.DATE_US: 'DATE',
            TokenType.DATE_EU: 'DATE',
            TokenType.DATE_COMPACT: 'DATE',
            TokenType.INTEGER: 'NUM',
            TokenType.DECIMAL: 'NUM',
            TokenType.CURRENCY: 'PRICE',
            TokenType.PART_CODE: 'CODE',
            TokenType.BRACKETED_CODE: 'CODE',
            TokenType.HTS_CODE: 'HTS',
            TokenType.PO_NUMBER: 'PO',
            TokenType.INVOICE_CODE: 'INV',
            TokenType.WORD: 'TEXT',
            TokenType.PHRASE: 'TEXT',
            TokenType.UNIT: 'UNIT',
            TokenType.COUNTRY: 'COUNTRY',
        }
        parts = []
        for t in self.tokens:
            if t.token_type in (TokenType.EMPTY, TokenType.SEPARATOR):
                continue
            parts.append(type_map.get(t.token_type, 'OTHER'))
        return " ".join(parts)

    def get_tokens_of_type(self, *types: TokenType) -> List[Token]:
        """Get all tokens matching the given types."""
        return [t for t in self.tokens if t.token_type in types]


@dataclass
class DetectedPattern:
    """A detected repeating pattern in the document."""
    signature: str                     # Token signature
    simplified_signature: str          # Simplified signature
    sample_lines: List[TokenizedLine]  # Lines matching this pattern
    frequency: int                     # How many times it appears
    confidence: float                  # Pattern confidence score

    # Field mapping (user-defined or auto-detected)
    field_mapping: Dict[int, str] = field(default_factory=dict)  # token_index -> field_name


class Tokenizer:
    """
    Tokenizes text into classified tokens based on data shapes.
    """

    # Countries commonly seen in invoices
    COUNTRIES = {
        'CHINA', 'INDIA', 'INDONESIA', 'BRAZIL', 'MEXICO', 'VIETNAM',
        'TAIWAN', 'KOREA', 'JAPAN', 'GERMANY', 'ITALY', 'SPAIN',
        'CZECH REPUBLIC', 'POLAND', 'TURKEY', 'USA', 'CANADA',
        'UNITED STATES', 'UNITED KINGDOM', 'UK', 'THAILAND', 'MALAYSIA',
    }

    # Common units
    UNITS = {
        'PCS', 'PC', 'UNITS', 'UNIT', 'EA', 'EACH',
        'KG', 'KGS', 'LB', 'LBS', 'G', 'GM',
        'M', 'MTR', 'METER', 'METERS', 'FT', 'FEET',
        'SET', 'SETS', 'PAIR', 'PAIRS', 'BOX', 'BOXES',
        'CTN', 'CARTON', 'CARTONS', 'PKG', 'PACKAGE',
        'DOZ', 'DOZEN', 'GROSS', 'ROLL', 'ROLLS',
    }

    # Patterns for token classification (ordered by specificity)
    PATTERNS = [
        # Dates
        (r'^\d{4}-\d{2}-\d{2}$', TokenType.DATE_ISO),
        (r'^\d{4}-\d{4}(?:-[A-Z]{2,3})?$', TokenType.DATE_COMPACT),  # 2025-0725, 2025-0725-NP
        (r'^\d{1,2}/\d{1,2}/\d{2,4}$', TokenType.DATE_US),
        (r'^\d{1,2}\.\d{1,2}\.\d{2,4}$', TokenType.DATE_EU),
        (r'^\d{8}$', TokenType.DATE_COMPACT),  # 20250115

        # HTS codes (must be before general decimals)
        (r'^\d{4}\.\d{2}\.\d{2,4}$', TokenType.HTS_CODE),
        (r'^HTS#?\d{10}$', TokenType.HTS_CODE),

        # Currency (must be before general decimals)
        (r'^\$[\d,]+\.?\d*$', TokenType.CURRENCY),
        (r'^USD\s*[\d,]+\.?\d*$', TokenType.CURRENCY),
        (r'^[\d,]+\.?\d*\s*USD$', TokenType.CURRENCY),
        (r'^€[\d,]+\.?\d*$', TokenType.CURRENCY),
        (r'^[\d,]+\.\d{2}$', TokenType.CURRENCY),  # Likely currency if exactly 2 decimals

        # Percentage
        (r'^[\d.]+%$', TokenType.PERCENTAGE),

        # Bracketed codes
        (r'^\[[\w\.\-/]+\]$', TokenType.BRACKETED_CODE),
        (r'^\([\w\.\-/]+\)$', TokenType.BRACKETED_CODE),

        # Invoice codes
        (r'^[A-Z]{2,5}[-/]\d+[-/]\d+', TokenType.INVOICE_CODE),
        (r'^INV[-#]?\d+', TokenType.INVOICE_CODE),

        # PO numbers (8 digits starting with 400 = Sigma style)
        (r'^400\d{5}$', TokenType.PO_NUMBER),
        (r'^PO[-#]?\d+$', TokenType.PO_NUMBER),

        # Part codes (alphanumeric with dashes/dots)
        (r'^[A-Z]{1,4}\d+[A-Z]?[-/]?[\w]*$', TokenType.PART_CODE),  # MS840, SLDE-Y6
        (r'^\d{2}-\d{5,7}$', TokenType.PART_CODE),  # 18-123456
        (r'^[A-Z]+-[A-Z0-9]+', TokenType.PART_CODE),  # PWPF-C24R-DR18M
        (r'^[A-Z]{2,}[\d\-\.]+[A-Z]*$', TokenType.PART_CODE),  # CB2436, MS840.03F

        # Numbers (must be after more specific patterns)
        (r'^[\d,]+\.\d{3,}$', TokenType.DECIMAL),  # 3+ decimals = likely unit price
        (r'^[\d,]+\.\d+$', TokenType.DECIMAL),
        (r'^[\d,]+$', TokenType.INTEGER),
    ]

    def tokenize_text(self, text: str) -> List[TokenizedLine]:
        """Tokenize all lines in the text."""
        lines = text.split('\n')
        result = []

        for i, line in enumerate(lines):
            tokenized = self._tokenize_line(line, i)
            result.append(tokenized)

        return result

    def _tokenize_line(self, line: str, line_number: int) -> TokenizedLine:
        """Tokenize a single line into classified tokens."""
        tokens = []

        # Split by whitespace but preserve quoted strings
        raw_tokens = self._split_preserving_quotes(line)

        for pos, raw in enumerate(raw_tokens):
            if not raw.strip():
                tokens.append(Token(raw, TokenType.EMPTY, pos))
                continue

            token_type = self._classify_token(raw)
            tokens.append(Token(raw, token_type, pos))

        return TokenizedLine(
            line_number=line_number,
            raw_text=line,
            tokens=tokens
        )

    def _split_preserving_quotes(self, line: str) -> List[str]:
        """Split line by whitespace but keep quoted strings together."""
        # First, handle bracketed content as single tokens
        # Replace spaces inside brackets temporarily
        protected = line

        # Protect bracketed content
        bracket_pattern = r'\[[^\]]+\]|\([^\)]+\)'
        brackets = re.findall(bracket_pattern, protected)
        for i, b in enumerate(brackets):
            protected = protected.replace(b, f'__BRACKET_{i}__')

        # Protect quoted content
        quote_pattern = r'"[^"]+"|\'[^\']+'
        quotes = re.findall(quote_pattern, protected)
        for i, q in enumerate(quotes):
            protected = protected.replace(q, f'__QUOTE_{i}__')

        # Split by 2+ spaces (column separator) or tabs
        parts = re.split(r'\s{2,}|\t', protected)

        # Restore protected content
        result = []
        for part in parts:
            restored = part
            for i, b in enumerate(brackets):
                restored = restored.replace(f'__BRACKET_{i}__', b)
            for i, q in enumerate(quotes):
                restored = restored.replace(f'__QUOTE_{i}__', q)
            result.append(restored.strip())

        return result

    def _classify_token(self, raw: str) -> TokenType:
        """Classify a single token based on its shape."""
        value = raw.strip()
        value_upper = value.upper()

        # Check for empty
        if not value:
            return TokenType.EMPTY

        # Check for country
        if value_upper in self.COUNTRIES:
            return TokenType.COUNTRY

        # Check for unit
        if value_upper in self.UNITS:
            return TokenType.UNIT

        # Check patterns
        for pattern, token_type in self.PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                return token_type

        # Check if it's a separator
        if value in '|-:;,':
            return TokenType.SEPARATOR

        # Check if single word or phrase
        if ' ' in value or len(value) > 30:
            return TokenType.PHRASE

        # Default to word if alphanumeric
        if re.match(r'^[\w\-\.]+$', value):
            return TokenType.WORD

        return TokenType.UNKNOWN


class PatternDetector:
    """
    Detects repeating patterns in tokenized text.
    Finds line item patterns, header patterns, etc.
    """

    def __init__(self, tokenized_lines: List[TokenizedLine]):
        self.lines = tokenized_lines

    def detect_patterns(self, min_frequency: int = 3) -> List[DetectedPattern]:
        """
        Detect repeating patterns in the tokenized lines.

        Args:
            min_frequency: Minimum times a pattern must appear to be considered

        Returns:
            List of detected patterns sorted by frequency
        """
        # Group lines by their simplified signature
        signature_groups: Dict[str, List[TokenizedLine]] = {}

        for line in self.lines:
            sig = line.simplified_signature
            if not sig or len(sig.split()) < 2:  # Skip very short signatures
                continue

            if sig not in signature_groups:
                signature_groups[sig] = []
            signature_groups[sig].append(line)

        # Create patterns from groups that meet minimum frequency
        patterns = []
        for sig, lines in signature_groups.items():
            if len(lines) >= min_frequency:
                # Calculate confidence based on consistency
                confidence = self._calculate_confidence(lines)

                patterns.append(DetectedPattern(
                    signature=lines[0].token_signature,
                    simplified_signature=sig,
                    sample_lines=lines[:10],  # Keep up to 10 samples
                    frequency=len(lines),
                    confidence=confidence,
                    field_mapping=self._auto_map_fields(lines[0])
                ))

        # Sort by frequency (most common first)
        patterns.sort(key=lambda p: (p.frequency, p.confidence), reverse=True)

        return patterns

    def _calculate_confidence(self, lines: List[TokenizedLine]) -> float:
        """Calculate confidence score for a pattern."""
        if not lines:
            return 0.0

        # Check consistency of token counts
        token_counts = [len(l.tokens) for l in lines]
        avg_count = sum(token_counts) / len(token_counts)
        variance = sum((c - avg_count) ** 2 for c in token_counts) / len(token_counts)

        # Lower variance = higher confidence
        consistency_score = 1.0 / (1.0 + variance * 0.1)

        # More samples = higher confidence
        frequency_score = min(1.0, len(lines) / 10)

        # Check if pattern has price-like values (good indicator of line items)
        has_prices = any(
            any(t.token_type in (TokenType.CURRENCY, TokenType.DECIMAL) for t in l.tokens)
            for l in lines
        )
        price_bonus = 0.2 if has_prices else 0.0

        return min(1.0, consistency_score * 0.5 + frequency_score * 0.3 + price_bonus)

    def _auto_map_fields(self, sample_line: TokenizedLine) -> Dict[int, str]:
        """Auto-detect field mapping based on token types."""
        mapping = {}

        code_count = 0
        num_count = 0
        price_count = 0

        for i, token in enumerate(sample_line.tokens):
            if token.token_type == TokenType.EMPTY:
                continue

            # Map based on token type
            if token.token_type in (TokenType.PART_CODE, TokenType.BRACKETED_CODE):
                if code_count == 0:
                    mapping[i] = 'part_number'
                else:
                    mapping[i] = f'code_{code_count + 1}'
                code_count += 1

            elif token.token_type == TokenType.INTEGER:
                if num_count == 0:
                    mapping[i] = 'quantity'
                else:
                    mapping[i] = f'number_{num_count + 1}'
                num_count += 1

            elif token.token_type in (TokenType.CURRENCY, TokenType.DECIMAL):
                if price_count == 0:
                    mapping[i] = 'unit_price'
                elif price_count == 1:
                    mapping[i] = 'total_price'
                else:
                    mapping[i] = f'price_{price_count + 1}'
                price_count += 1

            elif token.token_type == TokenType.HTS_CODE:
                mapping[i] = 'hs_code'

            elif token.token_type == TokenType.PO_NUMBER:
                mapping[i] = 'po_number'

            elif token.token_type in (TokenType.DATE_ISO, TokenType.DATE_US, TokenType.DATE_EU, TokenType.DATE_COMPACT):
                mapping[i] = 'date'

            elif token.token_type == TokenType.COUNTRY:
                mapping[i] = 'country_origin'

            elif token.token_type == TokenType.UNIT:
                mapping[i] = 'unit'

        return mapping

    def find_header_fields(self) -> Dict[str, str]:
        """
        Find single-occurrence fields typically in headers.
        Like "Invoice No: XXX" or "PO Number: XXX"
        """
        fields = {}

        # Keywords to look for
        keyword_patterns = {
            'invoice_number': ['invoice no', 'invoice #', 'invoice number', 'inv no', 'inv.'],
            'po_number': ['po no', 'po #', 'p.o.', 'purchase order', 'buyer order'],
            'bl_number': ['b/l no', 'bill of lading', 'bl #', 'b/l #'],
            'date': ['date:', 'invoice date', 'inv date'],
        }

        for line in self.lines:
            line_lower = line.raw_text.lower()

            for field_name, keywords in keyword_patterns.items():
                if field_name in fields:
                    continue

                for keyword in keywords:
                    if keyword in line_lower:
                        # Look for the value token after the keyword
                        for token in line.tokens:
                            if token.token_type in (
                                TokenType.INVOICE_CODE, TokenType.PO_NUMBER,
                                TokenType.PART_CODE, TokenType.INTEGER,
                                TokenType.DATE_ISO, TokenType.DATE_US
                            ):
                                fields[field_name] = token.value
                                break
                        break

        return fields


class TemplateCodeGenerator:
    """
    Generates Python template code from detected patterns.
    """

    def __init__(self, patterns: List[DetectedPattern], header_fields: Dict[str, str],
                 supplier_name: str = ""):
        self.patterns = patterns
        self.header_fields = header_fields
        self.supplier_name = supplier_name

    def generate(self, template_name: str, class_name: str = None) -> str:
        """Generate the template Python code."""
        if not class_name:
            class_name = ''.join(word.capitalize() for word in template_name.split('_')) + 'Template'

        # Find the best line item pattern
        line_item_pattern = self._find_line_item_pattern()

        code = f'''"""
{class_name} - Invoice template for {self.supplier_name or template_name}
Generated by Token-Based Template Builder
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class {class_name}(BaseTemplate):
    """
    Invoice template for {self.supplier_name or template_name}.
    Uses token-based extraction for robust pattern matching.
    """

    name = "{template_name.replace('_', ' ').title()}"
    description = "Commercial Invoice"
    client = "{self.supplier_name or template_name}"
    version = "1.0.0"
    enabled = True

    extra_columns = ['unit_price', 'hs_code', 'country_origin']

    # Supplier indicators for can_process()
    SUPPLIER_INDICATORS = {repr(self._get_supplier_indicators())}

    def can_process(self, text: str) -> bool:
        """Check if this template can process the invoice."""
        text_lower = text.lower()
        return any(ind in text_lower for ind in self.SUPPLIER_INDICATORS)

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        text_lower = text.lower()

        for ind in self.SUPPLIER_INDICATORS:
            if ind in text_lower:
                score += 0.15

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        {self._generate_invoice_extraction()}

    def extract_project_number(self, text: str) -> str:
        """Extract project/PO number."""
        {self._generate_po_extraction()}

    def extract_manufacturer_name(self, text: str) -> str:
        """Extract manufacturer name."""
        return "{self.supplier_name}"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items using token-based pattern matching."""
        {self._generate_line_item_extraction(line_item_pattern)}

    def is_packing_list(self, text: str) -> bool:
        """Check if document is a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower or 'packing slip' in text_lower:
            if 'invoice' not in text_lower:
                return True
        return False
'''
        return code

    def _get_supplier_indicators(self) -> List[str]:
        """Get supplier indicators for can_process."""
        indicators = []
        if self.supplier_name:
            # Add variations of supplier name
            indicators.append(self.supplier_name.lower())
            # Add individual words > 4 chars
            for word in self.supplier_name.split():
                if len(word) > 4:
                    indicators.append(word.lower())
        return indicators[:5] if indicators else ['unknown']

    def _generate_invoice_extraction(self) -> str:
        """Generate invoice number extraction code."""
        if 'invoice_number' in self.header_fields:
            sample = self.header_fields['invoice_number']
            return f'''# Sample found: {sample}
        patterns = [
            r'[Ii]nvoice\\s*(?:No\\.?|#|Number)\\s*[:\\s]*([A-Z0-9][\\w\\-/]+)',
            r'INV\\.?\\s*[:\\s]*([A-Z0-9][\\w\\-/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"'''
        else:
            return '''patterns = [
            r'[Ii]nvoice\\s*(?:No\\.?|#|Number)\\s*[:\\s]*([A-Z0-9][\\w\\-/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"'''

    def _generate_po_extraction(self) -> str:
        """Generate PO number extraction code."""
        if 'po_number' in self.header_fields:
            sample = self.header_fields['po_number']
            return f'''# Sample found: {sample}
        patterns = [
            r'P\\.?O\\.?\\s*(?:No\\.?|#)?\\s*[:\\s]*(\\d{{6,}})',
            r'(?:Purchase|Buyer)\\s+Order\\s*[:\\s]*([A-Z0-9]+)',
            r'\\b(400\\d{{5}})\\b',  # Sigma-style PO
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"'''
        else:
            return '''patterns = [
            r'P\\.?O\\.?\\s*(?:No\\.?|#)?\\s*[:\\s]*(\\d{6,})',
            r'\\b(400\\d{5})\\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"'''

    def _find_line_item_pattern(self) -> Optional[DetectedPattern]:
        """Find the best pattern for line items."""
        for pattern in self.patterns:
            # Look for patterns with prices (likely line items)
            sig = pattern.simplified_signature
            if 'PRICE' in sig or 'NUM' in sig:
                return pattern
        return self.patterns[0] if self.patterns else None

    def _generate_line_item_extraction(self, pattern: Optional[DetectedPattern]) -> str:
        """Generate line item extraction code."""
        if not pattern:
            return '''line_items = []
        # No line item pattern detected - manual configuration needed
        return line_items'''

        # Build extraction logic based on the pattern
        field_map = pattern.field_mapping
        sig = pattern.simplified_signature

        # Generate sample comment
        sample_lines = "\\n        # ".join(
            l.raw_text[:80] for l in pattern.sample_lines[:3]
        )

        code = f'''line_items = []
        seen_items = set()

        # Detected pattern: {sig}
        # Sample lines:
        # {sample_lines}

        lines = text.split('\\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:
                continue

            # Tokenize the line
            tokens = self._tokenize_line(line)

            # Check if line matches the expected pattern
            if not self._matches_line_item_pattern(tokens):
                continue

            # Extract fields from tokens
            item = self._extract_fields_from_tokens(tokens)

            if item and item.get('part_number'):
                # Deduplicate
                item_key = f"{{item.get('part_number', '')}}_{{item.get('quantity', '')}}_{{item.get('total_price', '')}}"
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)

        return line_items

    def _tokenize_line(self, line: str) -> List[Dict]:
        """Tokenize a line into classified tokens."""
        tokens = []
        # Split by multiple spaces
        parts = [p.strip() for p in re.split(r'\\s{{2,}}', line) if p.strip()]

        for part in parts:
            token = {{'value': part, 'type': self._classify_token(part)}}
            tokens.append(token)

        return tokens

    def _classify_token(self, value: str) -> str:
        """Classify a token by its data shape."""
        # Currency/Price
        if re.match(r'^\\$?[\\d,]+\\.\\d{{2,3}}$', value):
            return 'PRICE'
        # HTS code
        if re.match(r'^\\d{{4}}\\.\\d{{2}}\\.\\d{{2,4}}$', value):
            return 'HTS'
        # Integer
        if re.match(r'^[\\d,]+$', value):
            return 'NUM'
        # Part code (alphanumeric with dashes)
        if re.match(r'^[A-Z0-9]{{2,}}[\\w\\-\\./]*$', value, re.IGNORECASE):
            return 'CODE'
        # Bracketed code
        if re.match(r'^\\[[\\w\\.\\-/]+\\]$', value):
            return 'CODE'
        # Date
        if re.match(r'^\\d{{4}}-\\d{{2,4}}', value):
            return 'DATE'
        return 'TEXT'

    def _matches_line_item_pattern(self, tokens: List[Dict]) -> bool:
        """Check if tokens match the line item pattern."""
        types = [t['type'] for t in tokens]

        # Must have at least one code and one price/number
        has_code = 'CODE' in types
        has_price = 'PRICE' in types or types.count('NUM') >= 2

        return has_code and has_price and len(tokens) >= 3

    def _extract_fields_from_tokens(self, tokens: List[Dict]) -> Dict:
        """Extract field values from tokens."""
        item = {{}}

        prices = []
        numbers = []
        codes = []

        for token in tokens:
            t_type = token['type']
            value = token['value']

            if t_type == 'CODE':
                # Remove brackets if present
                value = value.strip('[]()').strip()
                codes.append(value)
            elif t_type == 'PRICE':
                prices.append(value.replace('$', '').replace(',', ''))
            elif t_type == 'NUM':
                numbers.append(value.replace(',', ''))
            elif t_type == 'HTS':
                item['hs_code'] = value

        # Map to fields
        if codes:
            item['part_number'] = codes[0]

        if prices:
            if len(prices) >= 2:
                item['unit_price'] = prices[0]
                item['total_price'] = prices[-1]
            else:
                item['total_price'] = prices[0]

        if numbers:
            # First number is usually quantity
            item['quantity'] = numbers[0]

        return item'''

        return code


class TokenTemplateAnalyzer:
    """
    Main class that orchestrates the token-based template analysis.
    """

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.tokenized_lines: List[TokenizedLine] = []
        self.patterns: List[DetectedPattern] = []
        self.header_fields: Dict[str, str] = {}
        self.raw_text: str = ""
        self.supplier_name: str = ""

    def analyze_pdf(self, pdf_path: str, pages: int = 3) -> bool:
        """
        Analyze a PDF and detect patterns.

        Args:
            pdf_path: Path to PDF file
            pages: Number of pages to analyze

        Returns:
            True if analysis successful
        """
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber required. Install: pip install pdfplumber")

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Extract text
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:pages]):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

        self.raw_text = "\n".join(text_parts)

        if not self.raw_text.strip():
            raise ValueError("No text extracted from PDF")

        return self.analyze_text(self.raw_text)

    def analyze_text(self, text: str) -> bool:
        """
        Analyze text and detect patterns.

        Args:
            text: Extracted text to analyze

        Returns:
            True if analysis successful
        """
        self.raw_text = text

        # Tokenize all lines
        self.tokenized_lines = self.tokenizer.tokenize_text(text)

        # Detect patterns
        detector = PatternDetector(self.tokenized_lines)
        self.patterns = detector.detect_patterns(min_frequency=2)

        # Find header fields
        self.header_fields = detector.find_header_fields()

        # Try to detect supplier name
        self.supplier_name = self._detect_supplier_name()

        return True

    def _detect_supplier_name(self) -> str:
        """Try to detect the supplier/company name."""
        # Look in first 15 lines for company-like names
        for line in self.tokenized_lines[:15]:
            text = line.raw_text.strip()

            # Look for company suffixes
            if re.search(r'\b(LTD|LLC|INC|CORP|CO\.|PVT|S\.?R\.?O\.?)\b', text, re.IGNORECASE):
                # Clean up
                name = re.sub(r'\s+', ' ', text).strip()
                if 5 < len(name) < 60:
                    return name

        return ""

    def generate_template(self, template_name: str, output_dir: str = None) -> str:
        """
        Generate template code from analysis.

        Args:
            template_name: Name for the template
            output_dir: Directory to save (optional)

        Returns:
            Generated Python code
        """
        generator = TemplateCodeGenerator(
            patterns=self.patterns,
            header_fields=self.header_fields,
            supplier_name=self.supplier_name
        )

        code = generator.generate(template_name)

        if output_dir:
            output_path = Path(output_dir) / f"{template_name}.py"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)

        return code

    def get_analysis_summary(self) -> Dict:
        """Get a summary of the analysis."""
        return {
            'supplier_name': self.supplier_name,
            'total_lines': len(self.tokenized_lines),
            'patterns_found': len(self.patterns),
            'header_fields': self.header_fields,
            'top_patterns': [
                {
                    'signature': p.simplified_signature,
                    'frequency': p.frequency,
                    'confidence': p.confidence,
                    'sample': p.sample_lines[0].raw_text[:80] if p.sample_lines else '',
                    'field_mapping': p.field_mapping
                }
                for p in self.patterns[:5]
            ]
        }

    def print_analysis(self):
        """Print analysis summary to console."""
        summary = self.get_analysis_summary()

        print("\n" + "=" * 70)
        print("TOKEN-BASED ANALYSIS SUMMARY")
        print("=" * 70)

        print(f"\nSupplier: {summary['supplier_name'] or 'Unknown'}")
        print(f"Total lines analyzed: {summary['total_lines']}")
        print(f"Patterns detected: {summary['patterns_found']}")

        if summary['header_fields']:
            print("\nHeader Fields:")
            for field, value in summary['header_fields'].items():
                print(f"  {field}: {value}")

        if summary['top_patterns']:
            print("\nTop Patterns (likely line items):")
            for i, p in enumerate(summary['top_patterns'], 1):
                print(f"\n  Pattern {i}:")
                print(f"    Signature: {p['signature']}")
                print(f"    Frequency: {p['frequency']} lines")
                print(f"    Confidence: {p['confidence']:.2f}")
                print(f"    Sample: {p['sample']}")
                if p['field_mapping']:
                    print(f"    Auto-mapped fields: {p['field_mapping']}")

        print("\n" + "=" * 70)


# Convenience function for command-line usage
def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description='Token-based template analyzer')
    parser.add_argument('pdf_path', help='Path to sample PDF')
    parser.add_argument('--name', '-n', default='new_template', help='Template name')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--analyze-only', '-a', action='store_true', help='Only analyze')

    args = parser.parse_args()

    analyzer = TokenTemplateAnalyzer()
    analyzer.analyze_pdf(args.pdf_path)
    analyzer.print_analysis()

    if not args.analyze_only:
        code = analyzer.generate_template(args.name, args.output)
        if not args.output:
            print("\nGENERATED CODE:")
            print(code)


if __name__ == '__main__':
    main()