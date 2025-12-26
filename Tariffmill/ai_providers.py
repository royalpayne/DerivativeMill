"""
AI Provider Interface for OCRMill Template Builder
Supports multiple LLM backends: Claude, OpenAI, Google Gemini, Mistral, Groq, DeepSeek, xAI (Grok), and OpenRouter.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
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


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "Unknown"
    requires_api_key: bool = True

    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """Check if provider is available and configured."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a response from the LLM."""
        pass

    def analyze_invoice_text(self, text: str) -> TemplateAnalysis:
        """Analyze invoice text and suggest extraction patterns."""
        system_prompt = """You are an expert at creating regex patterns for extracting data from invoices.
Your task is to analyze invoice text and suggest Python regex patterns for data extraction.
Be precise and provide working Python regex patterns that can be used with re.search() or re.compile().
Always respond with valid JSON only - no markdown, no code blocks, just the JSON object."""

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
- Be specific about the format you see
- Respond with ONLY the JSON object, no other text"""

        response = self.generate(prompt, system_prompt)
        return self._parse_analysis_response(response, text)

    def _parse_analysis_response(self, response: str, original_text: str) -> TemplateAnalysis:
        """Parse AI response into TemplateAnalysis object."""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)

        if json_match:
            try:
                data = json.loads(json_match.group())

                patterns = {}
                patterns_data = data.get('patterns', {})

                # Handle case where patterns might be a dict of dicts or other format
                if isinstance(patterns_data, dict):
                    for field, info in patterns_data.items():
                        # Handle case where info is a dict with pattern details
                        if isinstance(info, dict):
                            patterns[field] = ExtractionPattern(
                                field_name=field,
                                pattern=info.get('pattern', ''),
                                description=info.get('description', ''),
                                sample_match=info.get('sample_match', ''),
                                confidence=0.8
                            )
                        # Handle case where info is just a string (the pattern itself)
                        elif isinstance(info, str):
                            patterns[field] = ExtractionPattern(
                                field_name=field,
                                pattern=info,
                                description='',
                                sample_match='',
                                confidence=0.6
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
            except Exception as e:
                # Catch any other parsing errors and return a helpful message
                return TemplateAnalysis(
                    company_name="Unknown",
                    invoice_indicators=[],
                    suggested_patterns={},
                    line_item_pattern="",
                    line_item_columns=[],
                    notes=[f"Error parsing AI response: {str(e)}", "Please try again or use a different AI provider."]
                )

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
        """Refine an extraction pattern based on user feedback."""
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
                try:
                    re.compile(line)
                    return line
                except re.error:
                    continue

        return current_pattern

    def test_pattern(self, pattern: str, text: str) -> List[str]:
        """Test a regex pattern against text."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = compiled.findall(text)
            result = []
            for m in matches[:20]:
                if isinstance(m, tuple):
                    result.append(" | ".join(str(x) for x in m))
                else:
                    result.append(str(m))
            return result
        except re.error as e:
            return [f"Regex error: {e}"]




class ClaudeProvider(AIProvider):
    """Anthropic Claude API provider."""

    name = "Claude (Anthropic)"
    requires_api_key = True

    MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.anthropic.com/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        # Test with a minimal request
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                },
                timeout=10
            )
            if response.status_code == 200:
                return True, "Claude API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("Claude API key not configured")

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"Claude API error: {error_msg}")

        result = response.json()
        return result.get('content', [{}])[0].get('text', '')


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    name = "OpenAI"
    requires_api_key = True

    MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.openai.com/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "OpenAI API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"OpenAI API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider - access to multiple models."""

    name = "OpenRouter"
    requires_api_key = True

    MODELS = [
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "google/gemini-pro-1.5",
        "meta-llama/llama-3.1-70b-instruct",
        "mistralai/mistral-large",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://openrouter.ai/api/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "OpenRouter API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        # Could fetch from API, but return static list for simplicity
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://tariffmill.com",
                "X-Title": "TariffMill Template Builder"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"OpenRouter API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class GoogleGeminiProvider(AIProvider):
    """Google Gemini API provider."""

    name = "Google Gemini"
    requires_api_key = True

    MODELS = [
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models?key={self.api_key}",
                timeout=10
            )
            if response.status_code == 200:
                return True, "Google Gemini API connected"
            elif response.status_code == 401 or response.status_code == 403:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("Google Gemini API key not configured")

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "I understand. I will follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        response = requests.post(
            f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096
                }
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"Google Gemini API error: {error_msg}")

        result = response.json()
        candidates = result.get('candidates', [])
        if candidates:
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if parts:
                return parts[0].get('text', '')
        return ''


class MistralProvider(AIProvider):
    """Mistral AI API provider."""

    name = "Mistral AI"
    requires_api_key = True

    MODELS = [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "open-mixtral-8x22b",
        "open-mixtral-8x7b",
        "codestral-latest",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.mistral.ai/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "Mistral AI API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("Mistral AI API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"Mistral AI API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class GroqProvider(AIProvider):
    """Groq API provider - ultra-fast inference."""

    name = "Groq"
    requires_api_key = True

    MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.groq.com/openai/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "Groq API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("Groq API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"Groq API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class DeepSeekProvider(AIProvider):
    """DeepSeek API provider."""

    name = "DeepSeek"
    requires_api_key = True

    MODELS = [
        "deepseek-chat",
        "deepseek-coder",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.deepseek.com/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "DeepSeek API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("DeepSeek API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"DeepSeek API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class XAIProvider(AIProvider):
    """xAI (Grok) API provider."""

    name = "xAI (Grok)"
    requires_api_key = True

    MODELS = [
        "grok-2-latest",
        "grok-2-vision-latest",
        "grok-beta",
    ]

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model or self.MODELS[0]
        self.base_url = "https://api.x.ai/v1"

    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.api_key:
            return False, "API key not configured"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return True, "xAI API connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_available_models(self) -> List[str]:
        return self.MODELS

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            raise RuntimeError("xAI API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise RuntimeError(f"xAI API error: {error_msg}")

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')


class AIProviderManager:
    """Manages AI providers and API key storage."""

    PROVIDERS = {
        'claude': ClaudeProvider,
        'openai': OpenAIProvider,
        'gemini': GoogleGeminiProvider,
        'mistral': MistralProvider,
        'groq': GroqProvider,
        'deepseek': DeepSeekProvider,
        'xai': XAIProvider,
        'openrouter': OpenRouterProvider,
    }

    def __init__(self, settings_path: Path = None):
        self.settings_path = settings_path or Path.home() / ".tariffmill" / "ai_settings.json"
        self._settings = self._load_settings()
        self._current_provider = None

    def _load_settings(self) -> dict:
        """Load settings from file."""
        if self.settings_path.exists():
            try:
                return json.loads(self.settings_path.read_text())
            except Exception:
                pass
        return {
            'default_provider': 'claude',
            'api_keys': {},
            'selected_models': {}
        }

    def _save_settings(self):
        """Save settings to file."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(self._settings, indent=2))

    def get_api_key(self, provider_name: str) -> Optional[str]:
        """Get stored API key for a provider."""
        return self._settings.get('api_keys', {}).get(provider_name)

    def set_api_key(self, provider_name: str, api_key: str):
        """Store API key for a provider."""
        if 'api_keys' not in self._settings:
            self._settings['api_keys'] = {}
        self._settings['api_keys'][provider_name] = api_key
        self._save_settings()

    def get_selected_model(self, provider_name: str) -> Optional[str]:
        """Get selected model for a provider."""
        return self._settings.get('selected_models', {}).get(provider_name)

    def set_selected_model(self, provider_name: str, model: str):
        """Set selected model for a provider."""
        if 'selected_models' not in self._settings:
            self._settings['selected_models'] = {}
        self._settings['selected_models'][provider_name] = model
        self._save_settings()

    def get_default_provider(self) -> str:
        """Get default provider name."""
        return self._settings.get('default_provider', 'claude')

    def set_default_provider(self, provider_name: str):
        """Set default provider."""
        self._settings['default_provider'] = provider_name
        self._save_settings()

    def get_provider(self, provider_name: str = None) -> AIProvider:
        """Get a configured provider instance."""
        provider_name = provider_name or self.get_default_provider()

        if provider_name not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")

        provider_class = self.PROVIDERS[provider_name]
        api_key = self.get_api_key(provider_name)
        model = self.get_selected_model(provider_name)

        return provider_class(api_key=api_key, model=model)

    def get_available_providers(self) -> List[Tuple[str, str, bool]]:
        """
        Get list of available providers with their status.

        Returns:
            List of (provider_key, display_name, is_configured)
        """
        result = []
        for key, provider_class in self.PROVIDERS.items():
            name = provider_class.name
            if provider_class.requires_api_key:
                is_configured = bool(self.get_api_key(key))
            else:
                is_configured = True
            result.append((key, name, is_configured))
        return result

    def test_provider(self, provider_name: str) -> Tuple[bool, str]:
        """Test if a provider is working."""
        try:
            provider = self.get_provider(provider_name)
            return provider.is_available()
        except Exception as e:
            return False, str(e)


def generate_template_code(analysis: TemplateAnalysis, template_name: str, class_name: str) -> str:
    """
    Generate complete Python template code from analysis.

    This is a standalone function that can be used by any provider.
    """
    # Build indicator checks
    indicator_checks = []
    for indicator in analysis.invoice_indicators[:5]:
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
    for i, col in enumerate(columns[:10]):
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
