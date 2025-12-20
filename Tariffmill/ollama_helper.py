"""
Ollama Integration for AI-Assisted Template Generation
Uses local Ollama LLM for privacy-focused template creation.
"""

import json
import re
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class ExtractionPattern:
    """Represents an extraction pattern suggested by AI."""
    field_name: str
    pattern: str
    description: str
    sample_match: str
    confidence: float


@dataclass
class TemplateAnalysis:
    """Results from AI analysis of invoice text."""
    company_name: str
    invoice_indicators: List[str]
    suggested_patterns: Dict[str, ExtractionPattern]
    line_item_pattern: str
    line_item_columns: List[str]
    notes: List[str]


class OllamaHelper:
    """
    Helper class for Ollama LLM integration.
    Provides AI-assisted template generation from sample invoice text.
    """

    DEFAULT_HOST = "http://localhost:11434"
    PREFERRED_MODELS = ["llama3.2", "llama3.1", "llama3", "mistral", "codellama", "qwen2.5"]

    def __init__(self, host: str = None, model: str = None):
        """
        Initialize Ollama helper.

        Args:
            host: Ollama API host URL (default: http://localhost:11434)
            model: Model to use (default: auto-detect best available)
        """
        self.host = host or self.DEFAULT_HOST
        self.model = model
        self._available_models = None

    def is_available(self) -> Tuple[bool, str]:
        """
        Check if Ollama is available and running.

        Returns:
            Tuple of (is_available, status_message)
        """
        if not HAS_REQUESTS:
            return False, "requests library not installed. Run: pip install requests"

        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    return True, f"Ollama running with {len(models)} model(s)"
                return False, "Ollama running but no models installed"
            return False, f"Ollama returned status {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Ollama not running. Start with: ollama serve"
        except Exception as e:
            return False, f"Error connecting to Ollama: {str(e)}"

    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if self._available_models is not None:
            return self._available_models

        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                self._available_models = [m['name'] for m in models]
                return self._available_models
        except Exception:
            pass
        return []

    def get_best_model(self) -> Optional[str]:
        """Get the best available model from preferred list."""
        if self.model:
            return self.model

        available = self.get_available_models()
        if not available:
            return None

        # Check preferred models in order
        for preferred in self.PREFERRED_MODELS:
            for available_model in available:
                if preferred in available_model.lower():
                    return available_model

        # Return first available model
        return available[0] if available else None

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate response from Ollama.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response
        """
        model = self.get_best_model()
        if not model:
            raise RuntimeError("No Ollama models available")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower for more consistent outputs
                "num_predict": 4096,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.host}/api/generate",
            json=payload,
            timeout=120  # LLMs can be slow
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")

        return response.json().get('response', '')

    def analyze_invoice_text(self, text: str) -> TemplateAnalysis:
        """
        Analyze invoice text and suggest extraction patterns.

        Args:
            text: Full text extracted from a sample invoice PDF

        Returns:
            TemplateAnalysis with suggested patterns
        """
        system_prompt = """You are an expert at creating regex patterns for extracting data from invoices.
Your task is to analyze invoice text and suggest Python regex patterns for data extraction.
Be precise and provide working Python regex patterns that can be used with re.search() or re.compile()."""

        prompt = f"""Analyze this invoice text and create extraction patterns.

INVOICE TEXT:
---
{text[:4000]}
---

Provide your analysis as a JSON object with this structure:
{{
    "company_name": "The company/vendor name on this invoice",
    "invoice_indicators": ["list of unique text markers that identify this invoice format"],
    "patterns": {{
        "invoice_number": {{
            "pattern": "Python regex pattern with capture group",
            "description": "What this matches",
            "sample_match": "Example of what this would extract"
        }},
        "project_number": {{
            "pattern": "Python regex pattern with capture group",
            "description": "What this matches",
            "sample_match": "Example value"
        }},
        "date": {{
            "pattern": "Python regex pattern",
            "description": "Date format used",
            "sample_match": "Example date"
        }}
    }},
    "line_item_pattern": "Multi-part regex for line items - explain each group",
    "line_item_columns": ["list", "of", "column", "names", "in", "order"],
    "notes": ["Any special considerations or edge cases"]
}}

IMPORTANT:
- Use raw string patterns (no extra escaping needed for JSON)
- Include capture groups () for values to extract
- For line items, explain what each group captures
- Be specific about the format you see"""

        response = self.generate(prompt, system_prompt)

        # Parse JSON from response
        return self._parse_analysis_response(response, text)

    def _parse_analysis_response(self, response: str, original_text: str) -> TemplateAnalysis:
        """Parse AI response into TemplateAnalysis object."""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)

        if json_match:
            try:
                data = json.loads(json_match.group())

                patterns = {}
                for field, info in data.get('patterns', {}).items():
                    patterns[field] = ExtractionPattern(
                        field_name=field,
                        pattern=info.get('pattern', ''),
                        description=info.get('description', ''),
                        sample_match=info.get('sample_match', ''),
                        confidence=0.8  # Default confidence
                    )

                return TemplateAnalysis(
                    company_name=data.get('company_name', 'Unknown'),
                    invoice_indicators=data.get('invoice_indicators', []),
                    suggested_patterns=patterns,
                    line_item_pattern=data.get('line_item_pattern', ''),
                    line_item_columns=data.get('line_item_columns', []),
                    notes=data.get('notes', [])
                )
            except json.JSONDecodeError:
                pass

        # Return empty analysis if parsing fails
        return TemplateAnalysis(
            company_name="Unknown",
            invoice_indicators=[],
            suggested_patterns={},
            line_item_pattern="",
            line_item_columns=[],
            notes=["Failed to parse AI response. Please try again."]
        )

    def refine_pattern(self, field_name: str, current_pattern: str,
                       sample_text: str, desired_output: str) -> str:
        """
        Refine an extraction pattern based on user feedback.

        Args:
            field_name: Name of the field being extracted
            current_pattern: Current regex pattern
            sample_text: Text containing the value to extract
            desired_output: What the user wants extracted

        Returns:
            Refined regex pattern
        """
        prompt = f"""Fix this regex pattern for extracting {field_name}.

Current pattern: {current_pattern}
Sample text: {sample_text[:500]}
Desired extraction: {desired_output}

Provide ONLY the corrected Python regex pattern with a capture group for the value.
Do not include any explanation, just the pattern."""

        response = self.generate(prompt)

        # Extract just the pattern from response
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip().strip('`').strip('"').strip("'")
            if line and 'r"' not in line and "r'" not in line:
                # Test if it's a valid regex
                try:
                    re.compile(line)
                    return line
                except re.error:
                    continue

        return current_pattern  # Return original if refinement fails

    def generate_line_item_pattern(self, sample_lines: List[str],
                                   column_mapping: Dict[str, int]) -> str:
        """
        Generate a regex pattern for line item extraction.

        Args:
            sample_lines: Example line item lines from invoice
            column_mapping: Dict mapping column names to their positions

        Returns:
            Regex pattern for line item extraction
        """
        prompt = f"""Create a Python regex pattern to extract line items from invoice lines.

Sample lines:
{chr(10).join(sample_lines[:10])}

I need to extract these columns in this order:
{json.dumps(column_mapping, indent=2)}

Create a regex pattern with named capture groups (?P<name>...) for each column.
The pattern should work with re.compile() and match each line.

Provide ONLY the regex pattern, nothing else."""

        response = self.generate(prompt)

        # Extract pattern
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip().strip('`')
            if line.startswith('r"') or line.startswith("r'"):
                line = line[2:-1]
            try:
                re.compile(line)
                return line
            except re.error:
                continue

        return ""

    def generate_template_code(self, analysis: TemplateAnalysis,
                               template_name: str, class_name: str) -> str:
        """
        Generate complete Python template code from analysis.

        Args:
            analysis: TemplateAnalysis from analyze_invoice_text
            template_name: Name for the template (e.g., "acme_corp")
            class_name: Python class name (e.g., "AcmeCorpTemplate")

        Returns:
            Complete Python template file code
        """
        # Build indicator checks
        indicator_checks = []
        for indicator in analysis.invoice_indicators[:5]:  # Limit to 5
            safe_indicator = indicator.lower().replace("'", "\\'")
            indicator_checks.append(f"'{safe_indicator}' in text.lower()")

        indicators_code = " and ".join(indicator_checks) if indicator_checks else "False"

        # Build pattern code for invoice number
        inv_pattern = analysis.suggested_patterns.get('invoice_number')
        inv_pattern_code = inv_pattern.pattern if inv_pattern else r"Invoice\\s*#?\\s*:?\\s*(\\w+)"

        # Build pattern code for project number
        proj_pattern = analysis.suggested_patterns.get('project_number')
        proj_pattern_code = proj_pattern.pattern if proj_pattern else r"Project\\s*:?\\s*(\\w+)"

        # Build line item extraction
        line_pattern = analysis.line_item_pattern or r"^([A-Z0-9\\-]+)\\s+(\\d+)\\s+\\$?([\\d,]+\\.?\\d*)"
        columns = analysis.line_item_columns or ['part_number', 'quantity', 'total_price']

        # Generate column extraction code
        column_extractions = []
        for i, col in enumerate(columns[:10]):  # Limit columns
            safe_col = col.lower().replace(' ', '_').replace('-', '_')
            column_extractions.append(f"                        '{safe_col}': match.group({i + 1}),")

        template_code = f'''"""
{class_name} - Auto-generated template for {analysis.company_name}
Generated by TariffMill AI Template Builder
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class {class_name}(BaseTemplate):
    """
    Template for {analysis.company_name} invoices.

    Auto-generated patterns - review and adjust as needed.
    """

    name = "{template_name.replace('_', ' ').title()}"
    description = "Invoice template for {analysis.company_name}"
    client = "{analysis.company_name}"
    version = "1.0.0"

    enabled = True

    extra_columns = {repr([c for c in columns if c not in ['part_number', 'quantity', 'total_price']])}

    def can_process(self, text: str) -> bool:
        """Check if this template can process the given invoice."""
        return {indicators_code}

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        # Add points for each indicator found
        indicators = {repr(analysis.invoice_indicators[:5])}
        for indicator in indicators:
            if indicator.lower() in text.lower():
                score += 0.1

        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        patterns = [
            r'{inv_pattern_code}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract project number."""
        patterns = [
            r'{proj_pattern_code}',
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

        # Line item pattern - adjust as needed
        line_pattern = re.compile(
            r'{line_pattern}',
            re.MULTILINE | re.IGNORECASE
        )

        for match in line_pattern.finditer(text):
            try:
                item = {{
{chr(10).join(column_extractions)}
                    }}

                # Create deduplication key
                item_key = f"{{item.get('part_number', '')}}_{{item.get('quantity', '')}}"

                if item_key not in seen_items:
                    seen_items.add(item_key)
                    line_items.append(item)

            except (IndexError, AttributeError):
                continue

        return line_items
'''

        return template_code

    def test_pattern(self, pattern: str, text: str) -> List[str]:
        """
        Test a regex pattern against text.

        Args:
            pattern: Regex pattern to test
            text: Text to search

        Returns:
            List of matches found
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = compiled.findall(text)
            # Flatten tuples if pattern has multiple groups
            result = []
            for m in matches[:20]:  # Limit results
                if isinstance(m, tuple):
                    result.append(" | ".join(str(x) for x in m))
                else:
                    result.append(str(m))
            return result
        except re.error as e:
            return [f"Regex error: {e}"]


def check_ollama_status() -> Tuple[bool, str, List[str]]:
    """
    Check Ollama installation and status.

    Returns:
        Tuple of (is_available, status_message, available_models)
    """
    helper = OllamaHelper()
    available, message = helper.is_available()
    models = helper.get_available_models() if available else []
    return available, message, models
