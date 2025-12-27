"""
AI Template Generator for TariffMill

Allows users to generate invoice templates using AI models (OpenAI, Anthropic, or local models).
The AI analyzes sample invoice text and generates a complete template class.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QTextEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QCheckBox, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QProgressBar, QApplication, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

# Base directory for templates
BASE_DIR = Path(__file__).parent

# Try to import AI libraries
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class AIGeneratorThread(QThread):
    """Background thread for AI template generation."""
    finished = pyqtSignal(str)  # Generated code
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    stream_update = pyqtSignal(str)  # Streaming text updates (full text so far)
    cancelled = pyqtSignal()  # Emitted when cancelled

    def __init__(self, provider: str, model: str, api_key: str,
                 invoice_text: str, template_name: str, supplier_name: str,
                 country: str, client: str):
        super().__init__()
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.invoice_text = invoice_text
        self.template_name = template_name
        self.supplier_name = supplier_name
        self.country = country
        self.client = client
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the generation."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled

    def run(self):
        try:
            if self._cancelled:
                self.cancelled.emit()
                return

            self.progress.emit("Preparing prompt...")
            prompt = self._build_prompt()

            if self._cancelled:
                self.cancelled.emit()
                return

            self.progress.emit(f"Calling {self.provider} API...")

            if self.provider == "OpenAI":
                result = self._call_openai(prompt)
            elif self.provider == "Anthropic":
                result = self._call_anthropic(prompt)
            elif self.provider == "Ollama (Local)":
                result = self._call_ollama(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            if self._cancelled:
                self.cancelled.emit()
                return

            self.progress.emit("Processing response...")
            code = self._extract_code(result)
            self.finished.emit(code)

        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
            else:
                self.cancelled.emit()

    def _build_prompt(self) -> str:
        """Build the prompt for AI template generation."""
        # Truncate invoice text if too long
        invoice_sample = self.invoice_text[:8000] if len(self.invoice_text) > 8000 else self.invoice_text

        prompt = f'''You are an expert Python developer creating invoice parsing templates.
Analyze this sample invoice text and generate a complete Python template class.

SAMPLE INVOICE TEXT:
```
{invoice_sample}
```

REQUIREMENTS:
1. Template Name: {self.template_name}
2. Supplier Name: {self.supplier_name}
3. Country of Origin: {self.country}
4. Client: {self.client}

Generate a Python class that:
1. Inherits from BaseTemplate
2. Has a can_process() method that identifies this supplier's invoices
3. Has extract_invoice_number() to find the invoice number
4. Has extract_project_number() to find PO/project numbers
5. Has extract_line_items() to extract part numbers, quantities, and prices
6. Uses regex patterns appropriate for this invoice format

The class should follow this structure:

```python
"""
{self.supplier_name} Template

Auto-generated template for invoices from {self.supplier_name}.
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class {self._to_class_name(self.template_name)}(BaseTemplate):
    """Template for {self.supplier_name} invoices."""

    name = "{self.supplier_name}"
    description = "Invoices from {self.supplier_name}"
    client = "{self.client}"
    version = "1.0.0"
    enabled = True

    extra_columns = ['po_number', 'unit_price', 'description', 'country_origin']

    # Keywords to identify this supplier
    SUPPLIER_KEYWORDS = [
        # Add lowercase keywords here
    ]

    def can_process(self, text: str) -> bool:
        """Check if this is a {self.supplier_name} invoice."""
        text_lower = text.lower()
        for keyword in self.SUPPLIER_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for template matching."""
        if not self.can_process(text):
            return 0.0
        return 0.8

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number using regex patterns."""
        patterns = [
            # Add patterns based on the invoice format
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract PO/project number."""
        patterns = [
            # Add patterns for PO numbers
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Return the manufacturer name."""
        return "{self.supplier_name.upper()}"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        items = []
        # Add extraction logic based on the invoice format
        # Look for patterns like: part_number quantity price

        return items

    def post_process_items(self, items: List[Dict]) -> List[Dict]:
        """Post-process - deduplicate and validate."""
        if not items:
            return items

        seen = set()
        unique_items = []

        for item in items:
            key = f"{{item['part_number']}}_{{item['quantity']}}_{{item['total_price']}}"
            if key not in seen:
                seen.add(key)
                # Add country of origin
                item['country_origin'] = '{self.country}'
                unique_items.append(item)

        return unique_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is only a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower and 'invoice' not in text_lower:
            return True
        return False
```

IMPORTANT:
1. Analyze the invoice text carefully to identify the actual patterns used
2. Create specific regex patterns for invoice numbers, PO numbers, and line items
3. The SUPPLIER_KEYWORDS should contain unique identifiers from the invoice
4. The extract_line_items() method should parse the actual table format from the invoice
5. Return ONLY the Python code, no explanations

Generate the complete, working Python template code:
'''
        return prompt

    def _to_class_name(self, template_name: str) -> str:
        """Convert template name to class name."""
        return ''.join(word.title() for word in template_name.split('_')) + 'Template'

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert Python developer specializing in invoice parsing and OCR templates."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.3
        )
        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

    def _check_ollama_status(self) -> tuple:
        """
        Check if Ollama is running and the model is available.
        Returns: (is_running: bool, available_models: list, error_message: str)
        """
        import urllib.request
        import urllib.error
        import json

        # Check if Ollama server is running
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                models = [m.get('name', '').split(':')[0] for m in result.get('models', [])]
                return True, models, ""
        except urllib.error.URLError as e:
            if "Connection refused" in str(e) or "No connection" in str(e):
                return False, [], "not_running"
            return False, [], str(e)
        except Exception as e:
            return False, [], str(e)

    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API."""
        import urllib.request
        import urllib.error
        import json
        import platform
        import socket

        # First check if Ollama is running
        is_running, available_models, error_type = self._check_ollama_status()

        if not is_running:
            system = platform.system()

            if error_type == "not_running":
                # Ollama not running - provide platform-specific instructions
                if system == "Windows":
                    install_instructions = (
                        "Ollama is not running or not installed.\n\n"
                        "To install Ollama on Windows:\n"
                        "1. Download from: https://ollama.com/download\n"
                        "2. Run the installer\n"
                        "3. Open a terminal and run: ollama serve\n"
                        "4. In another terminal, pull a model: ollama pull llama3.1\n\n"
                        "After installation, start Ollama and try again."
                    )
                elif system == "Darwin":  # macOS
                    install_instructions = (
                        "Ollama is not running or not installed.\n\n"
                        "To install Ollama on macOS:\n"
                        "1. Download from: https://ollama.com/download\n"
                        "   Or use Homebrew: brew install ollama\n"
                        "2. Start Ollama: ollama serve\n"
                        "3. Pull a model: ollama pull llama3.1\n\n"
                        "After installation, start Ollama and try again."
                    )
                else:  # Linux
                    install_instructions = (
                        "Ollama is not running or not installed.\n\n"
                        "To install Ollama on Linux:\n"
                        "1. Run: curl -fsSL https://ollama.com/install.sh | sh\n"
                        "2. Start Ollama: ollama serve\n"
                        "3. Pull a model: ollama pull llama3.1\n\n"
                        "After installation, start Ollama and try again."
                    )
                raise ConnectionError(install_instructions)
            else:
                raise ConnectionError(f"Failed to connect to Ollama: {error_type}")

        # Check if the requested model is available
        model_base = self.model.split(':')[0]
        if available_models and model_base not in available_models:
            available_list = ', '.join(available_models) if available_models else 'none'
            raise ValueError(
                f"Model '{self.model}' is not installed in Ollama.\n\n"
                f"Available models: {available_list}\n\n"
                f"To install this model, run:\n"
                f"  ollama pull {self.model}\n\n"
                f"Or select one of the available models from the dropdown."
            )

        # Make the API call with streaming
        url = "http://localhost:11434/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": True  # Enable streaming for better UX
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        try:
            # 5 minute timeout for large prompts on slower hardware
            full_response = ""
            with urllib.request.urlopen(req, timeout=300) as response:
                # Read streaming response line by line
                for line in response:
                    if self._cancelled:
                        return full_response  # Return what we have so far

                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            full_response += chunk['response']
                            # Emit streaming update with character count in progress
                            char_count = len(full_response)
                            self.progress.emit(f"Generating... ({char_count} chars)")
                            # Send the full text so far for preview
                            self.stream_update.emit(full_response)

                        # Check if generation is complete
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

                return full_response
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise ValueError(
                    f"Model '{self.model}' not found.\n\n"
                    f"Pull the model first:\n  ollama pull {self.model}"
                )
            raise ConnectionError(f"Ollama API error: HTTP {e.code} - {e.reason}")
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                raise TimeoutError(
                    f"Generation timed out after 5 minutes.\n\n"
                    f"Suggestions:\n"
                    f"1. Try a smaller/faster model:\n"
                    f"   - llama3.2:1b (fastest)\n"
                    f"   - phi3 or mistral (fast)\n\n"
                    f"2. Use shorter invoice text (first 1-2 pages)\n\n"
                    f"3. Use a cloud provider (OpenAI/Anthropic) for faster results"
                )
            raise ConnectionError(
                f"Lost connection to Ollama during generation.\n\n"
                f"Error: {e}\n\n"
                f"Make sure Ollama is still running."
            )
        except socket.timeout:
            raise TimeoutError(
                f"Generation timed out after 5 minutes.\n\n"
                f"Suggestions:\n"
                f"1. Try a smaller/faster model:\n"
                f"   - llama3.2:1b (fastest)\n"
                f"   - phi3 or mistral (fast)\n\n"
                f"2. Use shorter invoice text (first 1-2 pages)\n\n"
                f"3. Use a cloud provider (OpenAI/Anthropic) for faster results"
            )
        except Exception as e:
            if "timed out" in str(e).lower():
                raise TimeoutError(
                    f"Generation timed out after 5 minutes.\n\n"
                    f"Suggestions:\n"
                    f"1. Try a smaller/faster model:\n"
                    f"   - llama3.2:1b (fastest)\n"
                    f"   - phi3 or mistral (fast)\n\n"
                    f"2. Use shorter invoice text (first 1-2 pages)\n\n"
                    f"3. Use a cloud provider (OpenAI/Anthropic) for faster results"
                )
            raise ConnectionError(f"Ollama error: {e}")

    def _extract_code(self, response: str) -> str:
        """Extract Python code from AI response."""
        # Try to find code block
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Try without language specifier
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Return the whole response if no code blocks found
        # but try to clean it up
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            if line.strip().startswith('"""') or line.strip().startswith('import ') or line.strip().startswith('from '):
                in_code = True
            if in_code:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines)

        return response


class AITemplateGeneratorDialog(QDialog):
    """
    Dialog for generating invoice templates using AI models.

    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Ollama (local models)
    """

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.generator_thread = None
        self.invoice_text = ""
        self.templates_data = []  # Store template info

        self.setWindowTitle("AI Template Generator")
        self.setMinimumSize(1100, 750)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("AI Template Generator")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        desc = QLabel(
            "Use AI to generate new OCR templates from sample invoices."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; margin-bottom: 15px;")
        layout.addWidget(desc)

        # AI Provider Settings
        provider_group = QGroupBox("AI Provider")
        provider_layout = QFormLayout()

        self.provider_combo = QComboBox()
        # Always show all providers - status indicator will show if they're available
        providers = ["OpenAI", "Anthropic", "Ollama (Local)"]
        self.provider_combo.addItems(providers)
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addRow("Provider:", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        provider_layout.addRow("Model:", self.model_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Enter API key (not needed for Ollama)")
        self.api_key_edit.textChanged.connect(self._update_status_indicator)
        provider_layout.addRow("API Key:", self.api_key_edit)

        # Status indicator row
        status_row = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedWidth(20)
        self.status_label = QLabel("Checking...")
        self.check_status_btn = QPushButton("Check Status")
        self.check_status_btn.setFixedWidth(100)
        self.check_status_btn.clicked.connect(self._update_status_indicator)
        status_row.addWidget(self.status_indicator)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.check_status_btn)
        provider_layout.addRow("Status:", status_row)

        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Update models for initial provider
        self.on_provider_changed(self.provider_combo.currentText())

        # Initial status check
        self._update_status_indicator()

        # Invoice Input
        input_group = QGroupBox("Sample Invoice")
        input_layout = QVBoxLayout()

        # File selection row
        file_row = QHBoxLayout()
        self.pdf_path_edit = QLineEdit()
        self.pdf_path_edit.setPlaceholderText("Select a PDF invoice or paste text below...")
        self.pdf_path_edit.setReadOnly(True)
        file_row.addWidget(self.pdf_path_edit, stretch=1)

        browse_btn = QPushButton("Browse PDF...")
        browse_btn.clicked.connect(self.browse_pdf)
        file_row.addWidget(browse_btn)

        input_layout.addLayout(file_row)

        self.invoice_text_edit = QPlainTextEdit()
        self.invoice_text_edit.setPlaceholderText(
            "Paste invoice text here, or load from PDF above.\n\n"
            "The AI will analyze this text to create extraction patterns."
        )
        self.invoice_text_edit.setFont(QFont("Courier New", 9))
        input_layout.addWidget(self.invoice_text_edit)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group, stretch=1)

        # Template Settings
        settings_group = QGroupBox("Template Settings")
        settings_layout = QFormLayout()

        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("e.g., acme_corp (lowercase with underscores)")
        settings_layout.addRow("Template Name:", self.template_name_edit)

        self.supplier_name_edit = QLineEdit()
        self.supplier_name_edit.setPlaceholderText("e.g., Acme Corporation")
        settings_layout.addRow("Supplier Name:", self.supplier_name_edit)

        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("e.g., Sigma Corporation")
        settings_layout.addRow("Client:", self.client_edit)

        self.country_edit = QLineEdit()
        self.country_edit.setPlaceholderText("e.g., CHINA, INDIA, USA")
        settings_layout.addRow("Country of Origin:", self.country_edit)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Generated Code Preview
        preview_group = QGroupBox("Generated Template (Preview)")
        preview_layout = QVBoxLayout()

        self.code_preview = QPlainTextEdit()
        self.code_preview.setReadOnly(True)
        self.code_preview.setFont(QFont("Courier New", 9))
        self.code_preview.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 5px;
            }
        """)
        self.code_preview.setPlaceholderText("Generated template code will appear here...")
        preview_layout.addWidget(self.code_preview)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, stretch=1)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.generate_btn = QPushButton("Generate Template")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                padding: 10px 25px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_template)
        btn_layout.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px 25px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_generation)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Template")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 25px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.save_btn.clicked.connect(self.save_template)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _get_ollama_models(self) -> list:
        """Get list of available Ollama models."""
        import urllib.request
        import urllib.error
        import json

        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as response:
                result = json.loads(response.read().decode('utf-8'))
                models = []
                for m in result.get('models', []):
                    name = m.get('name', '')
                    # Remove the :latest suffix for cleaner display
                    if ':latest' in name:
                        name = name.replace(':latest', '')
                    if name and name not in models:
                        models.append(name)
                return models
        except Exception:
            return []

    def _get_saved_api_key(self, provider: str) -> str:
        """Get saved API key from database."""
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).parent / "tariffmill.db"
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = ?", (f'api_key_{provider}',))
            row = c.fetchone()
            conn.close()
            return row[0] if row else ""
        except Exception:
            return ""

    def _save_api_key(self, provider: str, api_key: str):
        """Save API key to database."""
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).parent / "tariffmill.db"
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            # Ensure app_config table exists
            c.execute("""CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")
            c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                     (f'api_key_{provider}', api_key))
            conn.commit()
            conn.close()
            print(f"Saved API key for {provider} to database")
        except Exception as e:
            print(f"Failed to save API key: {e}")

    def _update_status_indicator(self, _=None):
        """Update the status indicator based on current provider and settings."""
        provider = self.provider_combo.currentText()

        if provider == "Ollama (Local)":
            # Check if Ollama is running
            models = self._get_ollama_models()
            if models:
                self.status_indicator.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")
                self.status_label.setText(f"Ready - {len(models)} model(s) available")
                self.status_label.setStyleSheet("color: #27ae60;")
            else:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Not connected - Ollama not running")
                self.status_label.setStyleSheet("color: #e74c3c;")

        elif provider == "OpenAI":
            # Check if openai package is installed
            if not HAS_OPENAI:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Package not installed - Run: pip install openai")
                self.status_label.setStyleSheet("color: #e74c3c;")
                return

            api_key = self.api_key_edit.text().strip()
            if api_key:
                if api_key.startswith("sk-"):
                    self.status_indicator.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")
                    self.status_label.setText("Ready - API key configured")
                    self.status_label.setStyleSheet("color: #27ae60;")
                else:
                    self.status_indicator.setStyleSheet("color: #f39c12; font-size: 16px; font-weight: bold;")
                    self.status_label.setText("Warning - API key format looks incorrect")
                    self.status_label.setStyleSheet("color: #f39c12;")
            else:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Not ready - Enter OpenAI API key")
                self.status_label.setStyleSheet("color: #e74c3c;")

        elif provider == "Anthropic":
            # Check if anthropic package is installed
            if not HAS_ANTHROPIC:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Package not installed - Run: pip install anthropic")
                self.status_label.setStyleSheet("color: #e74c3c;")
                return

            api_key = self.api_key_edit.text().strip()
            if api_key:
                if api_key.startswith("sk-ant-"):
                    self.status_indicator.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")
                    self.status_label.setText("Ready - API key configured")
                    self.status_label.setStyleSheet("color: #27ae60;")
                else:
                    self.status_indicator.setStyleSheet("color: #f39c12; font-size: 16px; font-weight: bold;")
                    self.status_label.setText("Warning - API key format looks incorrect")
                    self.status_label.setStyleSheet("color: #f39c12;")
            else:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Not ready - Enter Anthropic API key")
                self.status_label.setStyleSheet("color: #e74c3c;")

    def on_provider_changed(self, provider: str):
        """Update model list when provider changes."""
        self.model_combo.clear()

        if provider == "OpenAI":
            self.model_combo.addItems(["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])
            self.api_key_edit.setEnabled(True)
            self.api_key_edit.setPlaceholderText("Enter OpenAI API key")
            # Try to load from database first, then environment
            saved_key = self._get_saved_api_key('openai')
            if saved_key:
                self.api_key_edit.setText(saved_key)
            elif os.environ.get('OPENAI_API_KEY'):
                self.api_key_edit.setText(os.environ['OPENAI_API_KEY'])
        elif provider == "Anthropic":
            self.model_combo.addItems(["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"])
            self.api_key_edit.setEnabled(True)
            self.api_key_edit.setPlaceholderText("Enter Anthropic API key")
            # Try to load from database first, then environment
            saved_key = self._get_saved_api_key('anthropic')
            if saved_key:
                self.api_key_edit.setText(saved_key)
            elif os.environ.get('ANTHROPIC_API_KEY'):
                self.api_key_edit.setText(os.environ['ANTHROPIC_API_KEY'])
        elif provider == "Ollama (Local)":
            # Try to get available models from Ollama
            available_models = self._get_ollama_models()
            if available_models:
                self.model_combo.addItems(available_models)
            else:
                # Fallback to common models if Ollama not running
                self.model_combo.addItems(["llama3.1", "llama3", "codellama", "mistral", "mixtral", "deepseek-coder"])
            self.api_key_edit.setEnabled(False)
            self.api_key_edit.setPlaceholderText("Not needed for local Ollama")
            self.api_key_edit.clear()

        # Update status indicator after provider change
        self._update_status_indicator()

    def browse_pdf(self):
        """Browse for PDF file and extract text."""
        if not HAS_PDFPLUMBER:
            QMessageBox.warning(
                self, "Missing Dependency",
                "pdfplumber is required to load PDFs.\n\n"
                "Install with: pip install pdfplumber"
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Invoice PDF",
            str(Path.home()),
            "PDF Files (*.pdf);;All Files (*.*)"
        )

        if not path:
            return

        try:
            self.pdf_path_edit.setText(path)

            # Extract text from PDF
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages[:5]:  # First 5 pages
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            full_text = '\n\n'.join(text_parts)
            self.invoice_text_edit.setPlainText(full_text)

            # Try to auto-detect supplier name
            self._auto_detect_supplier(full_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract PDF text:\n{e}")

    def _auto_detect_supplier(self, text: str):
        """Try to auto-detect supplier name from invoice text."""
        # Look for common patterns
        lines = text.split('\n')

        # First few non-empty lines often contain company name
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 5 and len(line) < 60:
                # Skip lines that look like addresses or dates
                if re.match(r'^[\d\s\-/]+$', line):  # Just numbers
                    continue
                if re.search(r'\d{4}', line):  # Contains year
                    continue
                if '@' in line or 'www.' in line.lower():  # Email/web
                    continue

                # This might be a company name
                if not self.supplier_name_edit.text():
                    self.supplier_name_edit.setText(line)
                    # Generate template name
                    template_name = re.sub(r'[^a-z0-9]+', '_', line.lower()).strip('_')
                    self.template_name_edit.setText(template_name[:30])
                break

    def generate_template(self):
        """Start AI template generation."""
        # Validate inputs
        invoice_text = self.invoice_text_edit.toPlainText().strip()
        if not invoice_text:
            QMessageBox.warning(self, "Missing Input", "Please provide invoice text or load a PDF.")
            return

        template_name = self.template_name_edit.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Missing Input", "Please enter a template name.")
            return

        if not re.match(r'^[a-z][a-z0-9_]*$', template_name):
            QMessageBox.warning(
                self, "Invalid Name",
                "Template name must be lowercase, start with a letter, "
                "and contain only letters, numbers, and underscores."
            )
            return

        supplier_name = self.supplier_name_edit.text().strip()
        if not supplier_name:
            QMessageBox.warning(self, "Missing Input", "Please enter a supplier name.")
            return

        provider = self.provider_combo.currentText()
        api_key = self.api_key_edit.text().strip()

        # Check if required package is installed
        if provider == "OpenAI" and not HAS_OPENAI:
            QMessageBox.warning(
                self, "Package Not Installed",
                "The OpenAI package is not installed.\n\n"
                "Install it with:\n  pip install openai"
            )
            return

        if provider == "Anthropic" and not HAS_ANTHROPIC:
            QMessageBox.warning(
                self, "Package Not Installed",
                "The Anthropic package is not installed.\n\n"
                "Install it with:\n  pip install anthropic"
            )
            return

        if provider in ["OpenAI", "Anthropic"] and not api_key:
            QMessageBox.warning(self, "Missing API Key", f"Please enter your {provider} API key.")
            return

        # Save API key immediately when starting generation
        if provider == "OpenAI" and api_key:
            self._save_api_key('openai', api_key)
        elif provider == "Anthropic" and api_key:
            self._save_api_key('anthropic', api_key)

        # Start generation
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Generating...")
        self.generate_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.save_btn.setEnabled(False)

        self.generator_thread = AIGeneratorThread(
            provider=provider,
            model=self.model_combo.currentText(),
            api_key=api_key,
            invoice_text=invoice_text,
            template_name=template_name,
            supplier_name=supplier_name,
            country=self.country_edit.text().strip() or "UNKNOWN",
            client=self.client_edit.text().strip() or "Universal"
        )
        self.generator_thread.finished.connect(self.on_generation_complete)
        self.generator_thread.error.connect(self.on_generation_error)
        self.generator_thread.progress.connect(self.on_progress)
        self.generator_thread.stream_update.connect(self.on_stream_update)
        self.generator_thread.cancelled.connect(self.on_generation_cancelled)
        self.generator_thread.start()

    def on_progress(self, message: str):
        """Update progress message."""
        self.progress_bar.setFormat(message)

    def on_stream_update(self, text: str):
        """Update preview with streaming text from Ollama."""
        # Show raw streaming text in preview (will be processed on completion)
        self.code_preview.setPlainText(text)
        # Scroll to bottom to show latest content
        scrollbar = self.code_preview.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_generation_complete(self, code: str):
        """Handle successful generation."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.save_btn.setEnabled(True)

        self.code_preview.setPlainText(code)

        # Save API key to database on successful generation
        provider = self.provider_combo.currentText()
        api_key = self.api_key_edit.text().strip()
        if provider == "OpenAI" and api_key:
            self._save_api_key('openai', api_key)
        elif provider == "Anthropic" and api_key:
            self._save_api_key('anthropic', api_key)

        QMessageBox.information(
            self, "Generation Complete",
            "Template generated successfully!\n\n"
            "Review the code in the preview, then click 'Save Template' to save it."
        )

    def on_generation_error(self, error: str):
        """Handle generation error."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setVisible(True)
        self.cancel_btn.setVisible(False)

        QMessageBox.critical(
            self, "Generation Error",
            f"Failed to generate template:\n\n{error}"
        )

    def cancel_generation(self):
        """Cancel the ongoing generation."""
        if self.generator_thread and self.generator_thread.isRunning():
            self.progress_bar.setFormat("Cancelling...")
            self.cancel_btn.setEnabled(False)
            self.generator_thread.cancel()
            # Force terminate after a short wait if still running
            if not self.generator_thread.wait(2000):  # Wait 2 seconds
                self.generator_thread.terminate()
                self.generator_thread.wait()
            self.on_generation_cancelled()

    def on_generation_cancelled(self):
        """Handle cancelled generation."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setFormat("Cancelled")

    def save_template(self):
        """Save the generated template."""
        code = self.code_preview.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "No Code", "No template code to save.")
            return

        template_name = self.template_name_edit.text().strip()

        # Determine templates directory
        templates_dir = Path(__file__).parent / 'templates'
        if not templates_dir.exists():
            templates_dir = Path(__file__).parent.parent / 'Tariffmill' / 'templates'

        file_path = templates_dir / f"{template_name}.py"

        # Check if file already exists
        if file_path.exists():
            reply = QMessageBox.question(
                self, "File Exists",
                f"Template '{template_name}' already exists.\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Save the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Save AI metadata alongside the template
            import json
            from datetime import datetime
            metadata_path = file_path.with_suffix('.ai_meta.json')
            metadata = {
                'provider': self.provider_combo.currentText(),
                'model': self.model_combo.currentText(),
                'template_name': template_name,
                'supplier_name': self.supplier_name_edit.text().strip(),
                'country': self.country_edit.text().strip(),
                'client': self.client_edit.text().strip(),
                'invoice_text': self.invoice_text_edit.toPlainText().strip()[:5000],  # Limit size
                'created_at': datetime.now().isoformat(),
                'conversation_history': []  # For future chat modifications
            }
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            QMessageBox.information(
                self, "Template Saved",
                f"Template saved successfully!\n\n"
                f"File: {file_path}\n\n"
                f"The template will be available after refreshing templates."
            )

            # Emit signal
            self.template_created.emit(template_name, str(file_path))

            # Save settings
            self.save_settings()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")

    def load_settings(self):
        """Load saved settings (API keys, preferred provider)."""
        # Try to load from environment variables first
        if os.environ.get('OPENAI_API_KEY') and self.provider_combo.currentText() == "OpenAI":
            self.api_key_edit.setText(os.environ['OPENAI_API_KEY'])
        elif os.environ.get('ANTHROPIC_API_KEY') and self.provider_combo.currentText() == "Anthropic":
            self.api_key_edit.setText(os.environ['ANTHROPIC_API_KEY'])

    def save_settings(self):
        """Save settings for next time."""
        # Could save to a config file, but for now just keep in memory
        pass



class AITemplateChatThread(QThread):
    """Background thread for AI chat modifications."""
    finished = pyqtSignal(str)  # Modified code
    error = pyqtSignal(str)
    stream_update = pyqtSignal(str)

    def __init__(self, provider: str, model: str, api_key: str,
                 current_code: str, user_message: str, conversation_history: list,
                 invoice_text: str = ""):
        super().__init__()
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.current_code = current_code
        self.user_message = user_message
        self.conversation_history = conversation_history
        self.invoice_text = invoice_text
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            # Build the system prompt
            system_prompt = """You are an expert Python developer helping to modify an OCR invoice template.
The user has an existing template and wants to make modifications.

Current template code:
```python
{code}
```

{invoice_context}

When making changes:
1. Preserve the overall structure (class name, imports, base class)
2. Only modify the specific parts the user asks about
3. Return the COMPLETE modified template code
4. Wrap the code in ```python ... ``` markers
5. Explain what you changed after the code block

If the user asks a question, answer it and then provide the modified code if applicable."""

            invoice_context = ""
            if self.invoice_text:
                invoice_context = f"\nSample invoice text for reference:\n```\n{self.invoice_text[:2000]}\n```"

            system_msg = system_prompt.format(code=self.current_code, invoice_context=invoice_context)

            if self.provider == "OpenAI":
                result = self._call_openai(system_msg)
            elif self.provider == "Anthropic":
                result = self._call_anthropic(system_msg)
            elif self.provider == "Ollama (Local)":
                result = self._call_ollama(system_msg)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            if self._cancelled:
                return

            self.finished.emit(result)

        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def _call_openai(self, system_msg: str) -> str:
        if not HAS_OPENAI:
            raise ImportError("openai package not installed")

        client = openai.OpenAI(api_key=self.api_key)

        messages = [{"role": "system", "content": system_msg}]
        for msg in self.conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": self.user_message})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4000,
            temperature=0.3
        )
        return response.choices[0].message.content

    def _call_anthropic(self, system_msg: str) -> str:
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed")

        client = anthropic.Anthropic(api_key=self.api_key)

        messages = []
        for msg in self.conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": self.user_message})

        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_msg,
            messages=messages
        )
        return response.content[0].text

    def _call_ollama(self, system_msg: str) -> str:
        import urllib.request

        messages = [{"role": "system", "content": system_msg}]
        for msg in self.conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": self.user_message})

        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False
        }).encode('utf-8')

        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {}).get('content', '')


class AITemplateChatDialog(QDialog):
    """Dialog for chatting with AI to modify templates."""
    template_modified = pyqtSignal(str)  # Emitted when template is saved

    def __init__(self, template_path: str, metadata: dict, parent=None):
        super().__init__(parent)
        self.template_path = Path(template_path)
        self.metadata = metadata
        self.conversation_history = metadata.get('conversation_history', [])
        self.chat_thread = None

        self.setWindowTitle(f"AI Template Editor - {self.template_path.stem}")
        self.resize(1000, 700)
        self.setup_ui()
        self.load_template()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header with provider info
        header_layout = QHBoxLayout()
        provider = self.metadata.get('provider', 'Unknown')
        model = self.metadata.get('model', 'Unknown')
        header_label = QLabel(f"<b>AI Provider:</b> {provider} | <b>Model:</b> {model}")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # Provider/Model selection for modifications
        header_layout.addWidget(QLabel("Use:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Anthropic", "OpenAI", "Ollama (Local)"])
        # Set to original provider
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        header_layout.addWidget(self.provider_combo)

        self.model_combo = QComboBox()
        self._on_provider_changed(self.provider_combo.currentText())
        # Set to original model if found
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        header_layout.addWidget(self.model_combo)

        layout.addLayout(header_layout)

        # Main content: code on left, chat on right
        content_layout = QHBoxLayout()

        # Code editor (left side)
        code_group = QGroupBox("Template Code")
        code_layout = QVBoxLayout(code_group)
        self.code_edit = QPlainTextEdit()
        self.code_edit.setFont(QFont("Consolas", 10))
        code_layout.addWidget(self.code_edit)
        content_layout.addWidget(code_group, 3)

        # Chat area (right side) - VS Code dark theme
        chat_group = QGroupBox("Chat with AI")
        chat_group.setStyleSheet("""
            QGroupBox {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #cccccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #cccccc;
            }
        """)
        chat_layout = QVBoxLayout(chat_group)

        # Chat history display - VS Code style
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #787878;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        chat_layout.addWidget(self.chat_display, 1)

        # Message input - VS Code style
        self.message_input = QPlainTextEdit()
        self.message_input.setMaximumHeight(100)
        self.message_input.setPlaceholderText("Type your modification request here...\n(e.g., 'Change the invoice number regex to match format INV-XXXXX')")
        self.message_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 8px;
                font-family: "Segoe UI", sans-serif;
                font-size: 10pt;
            }
            QPlainTextEdit:focus {
                border: 1px solid #007acc;
            }
        """)
        chat_layout.addWidget(self.message_input)

        # Chat buttons - VS Code styled
        chat_btn_layout = QHBoxLayout()

        button_style = """
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8c;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #6e6e6e;
            }
        """
        secondary_button_style = """
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #5a5a5a;
            }
        """

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(button_style)
        self.send_btn.clicked.connect(self.send_message)
        chat_btn_layout.addWidget(self.send_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(secondary_button_style)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_request)
        chat_btn_layout.addWidget(self.cancel_btn)

        chat_btn_layout.addStretch()

        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #388a34;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #45a340;
            }
            QPushButton:pressed {
                background-color: #2d722a;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #5a5a5a;
            }
        """)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_changes)
        chat_btn_layout.addWidget(self.apply_btn)

        chat_layout.addLayout(chat_btn_layout)
        content_layout.addWidget(chat_group, 2)

        layout.addLayout(content_layout)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save Template")
        save_btn.clicked.connect(self.save_template)
        btn_layout.addWidget(save_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Load any existing chat history
        self._display_chat_history()

    def _on_provider_changed(self, provider: str):
        """Update model list when provider changes."""
        self.model_combo.clear()
        if provider == "OpenAI":
            self.model_combo.addItems(["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])
        elif provider == "Anthropic":
            self.model_combo.addItems(["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"])
        elif provider == "Ollama (Local)":
            self.model_combo.addItems(["llama3.1", "llama3", "codellama", "mistral"])

    def _get_api_key(self, provider: str) -> str:
        """Get API key for the provider."""
        # Try database first
        try:
            import sqlite3
            db_path = Path(__file__).parent / "tariffmill.db"
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            key_name = 'openai' if provider == "OpenAI" else 'anthropic'
            c.execute("SELECT value FROM app_config WHERE key = ?", (f'api_key_{key_name}',))
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
        except:
            pass

        # Fall back to environment
        if provider == "OpenAI":
            return os.environ.get('OPENAI_API_KEY', '')
        elif provider == "Anthropic":
            return os.environ.get('ANTHROPIC_API_KEY', '')
        return ""

    def load_template(self):
        """Load the template code."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.code_edit.setPlainText(f.read())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load template: {e}")

    def _format_message_html(self, role: str, content: str) -> str:
        """Format a chat message as VS Code-style HTML."""
        # Escape HTML in content but preserve code blocks
        import html as html_module

        # Process code blocks first
        def replace_code_block(match):
            code = html_module.escape(match.group(1))
            return f'</p><pre style="background-color: #0d0d0d; color: #d4d4d4; padding: 12px; border-radius: 6px; font-family: Consolas, monospace; font-size: 11px; margin: 8px 0; border-left: 3px solid #007acc; overflow-x: auto;">{code}</pre><p style="margin: 0; line-height: 1.6;">'

        # Replace ```python...``` blocks
        formatted = re.sub(r'```(?:python)?\s*(.*?)\s*```', replace_code_block, content, flags=re.DOTALL)

        # Escape remaining HTML (but not our inserted HTML)
        parts = re.split(r'(<pre.*?</pre>)', formatted, flags=re.DOTALL)
        escaped_parts = []
        for part in parts:
            if part.startswith('<pre'):
                escaped_parts.append(part)
            else:
                escaped_parts.append(html_module.escape(part))
        formatted = ''.join(escaped_parts)

        # Replace inline code `code`
        formatted = re.sub(r'`([^`]+)`', r'<code style="background-color: #3c3c3c; color: #ce9178; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; font-size: 11px;">\1</code>', formatted)

        # Replace newlines with <br> (but not in code blocks)
        parts = re.split(r'(<pre.*?</pre>)', formatted, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if not part.startswith('<pre'):
                parts[i] = part.replace('\n', '<br>')
        formatted = ''.join(parts)

        if role == 'user':
            # User message - right-aligned blue bubble
            return f'''
            <div style="margin: 12px 0; text-align: right;">
                <div style="display: inline-block; max-width: 85%; text-align: left;">
                    <div style="color: #808080; font-size: 9px; margin-bottom: 4px;">You</div>
                    <div style="background-color: #264f78; color: #ffffff; padding: 10px 14px; border-radius: 12px 12px 4px 12px;">
                        <p style="margin: 0; line-height: 1.6;">{formatted}</p>
                    </div>
                </div>
            </div>
            '''
        else:
            # AI message - left-aligned gray bubble
            return f'''
            <div style="margin: 12px 0; text-align: left;">
                <div style="display: inline-block; max-width: 85%; text-align: left;">
                    <div style="color: #808080; font-size: 9px; margin-bottom: 4px;">🤖 AI Assistant</div>
                    <div style="background-color: #2d2d2d; color: #e0e0e0; padding: 10px 14px; border-radius: 12px 12px 12px 4px; border: 1px solid #404040;">
                        <p style="margin: 0; line-height: 1.6;">{formatted}</p>
                    </div>
                </div>
            </div>
            '''

    def _display_chat_history(self):
        """Display existing chat history."""
        self.chat_display.clear()
        html_content = '<div style="font-family: Segoe UI, sans-serif;">'
        for msg in self.conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            html_content += self._format_message_html(role, content)
        html_content += '</div>'
        self.chat_display.setHtml(html_content)

    def send_message(self):
        """Send a message to the AI."""
        message = self.message_input.toPlainText().strip()
        if not message:
            return

        provider = self.provider_combo.currentText()
        api_key = self._get_api_key(provider)

        if provider in ["OpenAI", "Anthropic"] and not api_key:
            QMessageBox.warning(self, "Missing API Key",
                              f"No API key found for {provider}.\n\n"
                              "Please configure it in Configuration > Billing tab or set environment variable.")
            return

        # Add user message to display and history
        self.conversation_history.append({"role": "user", "content": message})
        self._display_chat_history()
        self.message_input.clear()
        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Disable send, enable cancel
        self.send_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        # Start AI request
        self.chat_thread = AITemplateChatThread(
            provider=provider,
            model=self.model_combo.currentText(),
            api_key=api_key,
            current_code=self.code_edit.toPlainText(),
            user_message=message,
            conversation_history=self.conversation_history,
            invoice_text=self.metadata.get('invoice_text', '')
        )
        self.chat_thread.finished.connect(self._on_response)
        self.chat_thread.error.connect(self._on_error)
        self.chat_thread.start()

    def cancel_request(self):
        """Cancel the current AI request."""
        if self.chat_thread:
            self.chat_thread.cancel()
            self.chat_thread = None
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _on_response(self, response: str):
        """Handle AI response."""
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        # Add to history and redisplay
        self.conversation_history.append({"role": "assistant", "content": response})
        self._display_chat_history()

        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Extract code if present
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            self.pending_code = code_match.group(1)
            self.apply_btn.setEnabled(True)
            # Add system notification about code detection
            self._append_system_message("Code changes detected. Click 'Apply Changes' to update the template.")
        else:
            self.pending_code = None

    def _append_system_message(self, message: str, is_error: bool = False):
        """Append a system notification message to the chat display."""
        color = "#f48771" if is_error else "#4ec9b0"  # Red for error, teal for info
        icon = "⚠️" if is_error else "ℹ️"
        html = f'''
        <div style="margin: 8px 0; text-align: center;">
            <div style="display: inline-block; background-color: #252526; color: {color}; padding: 8px 16px; border-radius: 6px; font-size: 10px; border: 1px solid #404040;">
                {icon} {message}
            </div>
        </div>
        '''
        # Get current HTML and append
        current_html = self.chat_display.toHtml()
        # Find closing div and insert before it
        if '</div></body>' in current_html:
            current_html = current_html.replace('</div></body>', f'{html}</div></body>')
        else:
            self.chat_display.append(html)
            return
        self.chat_display.setHtml(current_html)
        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_error(self, error: str):
        """Handle AI error."""
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._append_system_message(f"Error: {error}", is_error=True)

    def apply_changes(self):
        """Apply the AI-suggested code changes."""
        if hasattr(self, 'pending_code') and self.pending_code:
            self.code_edit.setPlainText(self.pending_code)
            self.apply_btn.setEnabled(False)
            self._append_system_message("Changes applied to code editor.")

    def save_template(self):
        """Save the modified template."""
        code = self.code_edit.toPlainText()

        try:
            # Save template code
            with open(self.template_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Update metadata with conversation history
            self.metadata['conversation_history'] = self.conversation_history
            self.metadata['last_modified'] = datetime.now().isoformat()

            metadata_path = self.template_path.with_suffix('.ai_meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)

            QMessageBox.information(self, "Saved", "Template saved successfully!")
            self.template_modified.emit(str(self.template_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")


class AITemplateEditorDialog(QDialog):
    """
    Unified AI Template Editor for editing both AI-generated and regular templates.
    Features a code editor on the left and AI chat assistant on the right.
    """
    template_modified = pyqtSignal(str)  # Emitted when template is saved

    def __init__(self, template_path: str, metadata: dict, parent=None):
        super().__init__(parent)
        self.template_path = Path(template_path)
        self.metadata = metadata
        self.conversation_history = metadata.get('conversation_history', [])
        self.chat_thread = None
        self.is_ai_template = bool(metadata.get('provider'))

        self.setWindowTitle(f"Template Editor - {self.template_path.stem}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setup_ui()
        self.load_template()

        # Show welcome message for templates without conversation history
        if not self.conversation_history:
            self._show_welcome_message()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header bar with template info and AI provider selection
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #2d2d30; border-radius: 6px; padding: 5px;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 8, 10, 8)

        # Template name
        name_label = QLabel(f"<b style='color: #dcdcdc; font-size: 14px;'>{self.template_path.stem}</b>")
        header_layout.addWidget(name_label)

        # AI indicator
        if self.is_ai_template:
            provider = self.metadata.get('provider', '')
            ai_badge = QLabel(f"🤖 AI Generated ({provider})")
            ai_badge.setStyleSheet("color: #4ec9b0; font-size: 11px; padding: 2px 8px; background-color: #1e3a1e; border-radius: 4px;")
            header_layout.addWidget(ai_badge)

        header_layout.addStretch()

        # AI Provider selection
        header_layout.addWidget(QLabel("<span style='color: #9cdcfe;'>AI Provider:</span>"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Anthropic", "OpenAI", "Ollama (Local)"])
        self.provider_combo.setFixedWidth(140)
        if self.is_ai_template:
            idx = self.provider_combo.findText(self.metadata.get('provider', ''))
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        header_layout.addWidget(self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setFixedWidth(200)
        self._on_provider_changed(self.provider_combo.currentText())
        if self.is_ai_template:
            idx = self.model_combo.findText(self.metadata.get('model', ''))
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        header_layout.addWidget(self.model_combo)

        layout.addWidget(header_widget)

        # Main splitter - code editor on left, chat on right
        main_splitter = QSplitter(Qt.Horizontal)

        # === LEFT SIDE: Code Editor ===
        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(5)

        # Code editor header
        code_header = QHBoxLayout()
        code_label = QLabel("<b style='color: #dcdcdc;'>Template Code</b>")
        code_header.addWidget(code_label)
        code_header.addStretch()

        # Syntax validation indicator
        self.syntax_indicator = QLabel("✓ Valid")
        self.syntax_indicator.setStyleSheet("color: #4ec9b0; font-size: 10px;")
        code_header.addWidget(self.syntax_indicator)
        code_layout.addLayout(code_header)

        # Code editor with dark theme
        self.code_edit = QPlainTextEdit()
        self.code_edit.setFont(QFont("Consolas", 11))
        self.code_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #264f78;
            }
        """)
        self.code_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.code_edit.textChanged.connect(self._validate_syntax)
        code_layout.addWidget(self.code_edit, 1)

        main_splitter.addWidget(code_widget)

        # === RIGHT SIDE: AI Chat Panel ===
        chat_widget = QWidget()
        chat_widget.setStyleSheet("background-color: #252526; border-radius: 6px;")
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(8)

        # Chat header
        chat_label = QLabel("<b style='color: #dcdcdc;'>AI Assistant</b>")
        chat_layout.addWidget(chat_label)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #787878;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        chat_layout.addWidget(self.chat_display, 1)

        # Message input
        self.message_input = QPlainTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Ask the AI to modify the template...\n(e.g., 'Add support for a new date format' or 'Fix the regex for invoice numbers')")
        self.message_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 8px;
                font-family: "Segoe UI", sans-serif;
                font-size: 10pt;
            }
            QPlainTextEdit:focus {
                border: 1px solid #007acc;
            }
        """)
        chat_layout.addWidget(self.message_input)

        # Chat buttons
        chat_btn_layout = QHBoxLayout()
        chat_btn_layout.setSpacing(8)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1177bb; }
            QPushButton:pressed { background-color: #0d5a8c; }
            QPushButton:disabled { background-color: #3c3c3c; color: #6e6e6e; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        chat_btn_layout.addWidget(self.send_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #2d2d2d; color: #5a5a5a; }
        """)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_request)
        chat_btn_layout.addWidget(self.cancel_btn)

        chat_btn_layout.addStretch()

        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #388a34;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a340; }
            QPushButton:disabled { background-color: #2d2d2d; color: #5a5a5a; }
        """)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_changes)
        chat_btn_layout.addWidget(self.apply_btn)

        chat_layout.addLayout(chat_btn_layout)

        main_splitter.addWidget(chat_widget)

        # Set splitter proportions (60% code, 40% chat)
        main_splitter.setSizes([700, 500])
        layout.addWidget(main_splitter, 1)

        # Bottom button bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Left side buttons
        self.test_btn = QPushButton("Test Template")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d6ee8; }
        """)
        self.test_btn.clicked.connect(self._test_template)
        btn_layout.addWidget(self.test_btn)

        btn_layout.addStretch()

        # Right side buttons
        save_btn = QPushButton("Save Template")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #388a34;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #45a340; }
        """)
        save_btn.clicked.connect(self.save_template)
        btn_layout.addWidget(save_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 10px 24px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _on_provider_changed(self, provider: str):
        """Update model list when provider changes."""
        self.model_combo.clear()
        if provider == "OpenAI":
            self.model_combo.addItems(["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])
        elif provider == "Anthropic":
            self.model_combo.addItems(["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"])
        elif provider == "Ollama (Local)":
            self.model_combo.addItems(["llama3.1", "llama3", "codellama", "mistral"])

    def _get_api_key(self, provider: str) -> str:
        """Get API key for the provider."""
        try:
            import sqlite3
            db_path = Path(__file__).parent / "tariffmill.db"
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            key_name = 'openai' if provider == "OpenAI" else 'anthropic'
            c.execute("SELECT value FROM app_config WHERE key = ?", (f'api_key_{key_name}',))
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
        except:
            pass

        if provider == "OpenAI":
            return os.environ.get('OPENAI_API_KEY', '')
        elif provider == "Anthropic":
            return os.environ.get('ANTHROPIC_API_KEY', '')
        return ""

    def load_template(self):
        """Load the template code."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.code_edit.setPlainText(f.read())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load template: {e}")

    def _show_welcome_message(self):
        """Show a welcome message in the chat for new templates."""
        welcome_html = '''
        <div style="font-family: Segoe UI, sans-serif; padding: 10px;">
            <div style="background-color: #2d2d2d; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="color: #4ec9b0; font-size: 14px; font-weight: bold; margin-bottom: 10px;">
                    👋 Welcome to the AI Template Editor
                </div>
                <div style="color: #cccccc; line-height: 1.6;">
                    <p>You can ask me to help you modify this template. Here are some things I can do:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Fix regex patterns for extracting data</li>
                        <li>Add support for new invoice formats</li>
                        <li>Improve error handling</li>
                        <li>Add new extraction fields</li>
                        <li>Explain how the template works</li>
                    </ul>
                    <p style="color: #9cdcfe; margin-top: 10px;">
                        💡 <b>Tip:</b> Be specific about what you want to change. For example:<br>
                        <i>"Change the invoice number regex to match format INV-2024-XXXXX"</i>
                    </p>
                </div>
            </div>
        </div>
        '''
        self.chat_display.setHtml(welcome_html)

    def _validate_syntax(self):
        """Validate Python syntax of the template code."""
        code = self.code_edit.toPlainText()
        try:
            compile(code, '<template>', 'exec')
            self.syntax_indicator.setText("✓ Valid")
            self.syntax_indicator.setStyleSheet("color: #4ec9b0; font-size: 10px;")
        except SyntaxError as e:
            self.syntax_indicator.setText(f"✗ Line {e.lineno}: {e.msg}")
            self.syntax_indicator.setStyleSheet("color: #f48771; font-size: 10px;")

    def _test_template(self):
        """Test the template by attempting to import it."""
        code = self.code_edit.toPlainText()
        try:
            compile(code, '<template>', 'exec')
            exec(code, {'__name__': '__main__'})
            QMessageBox.information(self, "Test Passed", "Template syntax is valid and can be imported!")
        except Exception as e:
            QMessageBox.warning(self, "Test Failed", f"Template has errors:\n\n{e}")

    def _format_message_html(self, role: str, content: str) -> str:
        """Format a chat message as styled HTML."""
        import html as html_module

        # Process code blocks
        def replace_code_block(match):
            code = html_module.escape(match.group(1))
            return f'</p><pre style="background-color: #0d0d0d; color: #d4d4d4; padding: 12px; border-radius: 6px; font-family: Consolas, monospace; font-size: 11px; margin: 8px 0; border-left: 3px solid #007acc; overflow-x: auto; white-space: pre-wrap;">{code}</pre><p style="margin: 0; line-height: 1.6;">'

        formatted = re.sub(r'```(?:python)?\s*(.*?)\s*```', replace_code_block, content, flags=re.DOTALL)

        # Escape remaining HTML
        parts = re.split(r'(<pre.*?</pre>)', formatted, flags=re.DOTALL)
        escaped_parts = []
        for part in parts:
            if part.startswith('<pre'):
                escaped_parts.append(part)
            else:
                escaped_parts.append(html_module.escape(part))
        formatted = ''.join(escaped_parts)

        # Inline code
        formatted = re.sub(r'`([^`]+)`', r'<code style="background-color: #3c3c3c; color: #ce9178; padding: 2px 6px; border-radius: 3px; font-family: Consolas;">\1</code>', formatted)

        # Newlines
        parts = re.split(r'(<pre.*?</pre>)', formatted, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if not part.startswith('<pre'):
                parts[i] = part.replace('\n', '<br>')
        formatted = ''.join(parts)

        if role == 'user':
            return f'''
            <div style="margin: 12px 0; text-align: right;">
                <div style="display: inline-block; max-width: 85%; text-align: left;">
                    <div style="color: #808080; font-size: 9px; margin-bottom: 4px;">You</div>
                    <div style="background-color: #264f78; color: #ffffff; padding: 10px 14px; border-radius: 12px 12px 4px 12px;">
                        <p style="margin: 0; line-height: 1.6;">{formatted}</p>
                    </div>
                </div>
            </div>
            '''
        else:
            return f'''
            <div style="margin: 12px 0; text-align: left;">
                <div style="display: inline-block; max-width: 85%; text-align: left;">
                    <div style="color: #808080; font-size: 9px; margin-bottom: 4px;">🤖 AI Assistant</div>
                    <div style="background-color: #2d2d2d; color: #e0e0e0; padding: 10px 14px; border-radius: 12px 12px 12px 4px; border: 1px solid #404040;">
                        <p style="margin: 0; line-height: 1.6;">{formatted}</p>
                    </div>
                </div>
            </div>
            '''

    def _display_chat_history(self):
        """Display chat history."""
        if not self.conversation_history:
            self._show_welcome_message()
            return

        html_content = '<div style="font-family: Segoe UI, sans-serif;">'
        for msg in self.conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            html_content += self._format_message_html(role, content)
        html_content += '</div>'
        self.chat_display.setHtml(html_content)

    def send_message(self):
        """Send a message to the AI."""
        message = self.message_input.toPlainText().strip()
        if not message:
            return

        provider = self.provider_combo.currentText()
        api_key = self._get_api_key(provider)

        if provider in ["OpenAI", "Anthropic"] and not api_key:
            QMessageBox.warning(self, "Missing API Key",
                              f"No API key found for {provider}.\n\n"
                              "Please configure it in Configuration > Billing tab or set environment variable.")
            return

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})
        self._display_chat_history()
        self.message_input.clear()

        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Disable send, enable cancel
        self.send_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        # Start AI request
        self.chat_thread = AITemplateChatThread(
            provider=provider,
            model=self.model_combo.currentText(),
            api_key=api_key,
            current_code=self.code_edit.toPlainText(),
            user_message=message,
            conversation_history=self.conversation_history[:-1],  # Exclude the message we just added
            invoice_text=self.metadata.get('invoice_text', '')
        )
        self.chat_thread.finished.connect(self._on_response)
        self.chat_thread.error.connect(self._on_error)
        self.chat_thread.start()

    def cancel_request(self):
        """Cancel the current AI request."""
        if self.chat_thread:
            self.chat_thread.cancel()
            self.chat_thread = None
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _on_response(self, response: str):
        """Handle AI response."""
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        # Add to history and redisplay
        self.conversation_history.append({"role": "assistant", "content": response})
        self._display_chat_history()

        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Extract code if present
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            self.pending_code = code_match.group(1)
            self.apply_btn.setEnabled(True)
        else:
            self.pending_code = None

    def _on_error(self, error: str):
        """Handle AI error."""
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        QMessageBox.warning(self, "AI Error", f"Error communicating with AI:\n\n{error}")

    def apply_changes(self):
        """Apply the AI-suggested code changes."""
        if hasattr(self, 'pending_code') and self.pending_code:
            self.code_edit.setPlainText(self.pending_code)
            self.apply_btn.setEnabled(False)
            QMessageBox.information(self, "Applied", "Code changes applied to the editor.")

    def save_template(self):
        """Save the modified template."""
        code = self.code_edit.toPlainText()

        # Validate syntax before saving
        try:
            compile(code, '<template>', 'exec')
        except SyntaxError as e:
            reply = QMessageBox.question(
                self, "Syntax Error",
                f"The template has syntax errors:\n\nLine {e.lineno}: {e.msg}\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            # Save template code
            with open(self.template_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Update metadata with conversation history
            self.metadata['conversation_history'] = self.conversation_history
            self.metadata['last_modified'] = datetime.now().isoformat()
            self.metadata['provider'] = self.provider_combo.currentText()
            self.metadata['model'] = self.model_combo.currentText()

            metadata_path = self.template_path.with_suffix('.ai_meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)

            QMessageBox.information(self, "Saved", "Template saved successfully!")
            self.template_modified.emit(str(self.template_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")


def main():
    """Test the dialog standalone."""
    import sys
    app = QApplication(sys.argv)
    dialog = AITemplateGeneratorDialog()
    dialog.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()