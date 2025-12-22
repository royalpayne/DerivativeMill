"""
AI-Assisted Template Builder for OCRMill
Semi-guided template creation using multiple AI providers (Ollama, Claude, OpenAI, OpenRouter).
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QPlainTextEdit, QLineEdit, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSplitter, QTabWidget, QWidget, QFileDialog, QMessageBox,
    QProgressBar, QListWidget, QListWidgetItem, QCheckBox,
    QSpinBox, QDialogButtonBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

from ai_providers import (
    AIProvider, AIProviderManager, TemplateAnalysis, ExtractionPattern,
    generate_template_code
)


class AnalysisWorker(QThread):
    """Background worker for AI analysis."""
    finished = pyqtSignal(object)  # TemplateAnalysis
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, provider: AIProvider, text: str):
        super().__init__()
        self.provider = provider
        self.text = text

    def run(self):
        try:
            self.progress.emit("Analyzing invoice structure...")
            analysis = self.provider.analyze_invoice_text(self.text)
            self.finished.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))


class PythonHighlighter(QSyntaxHighlighter):
    """Simple Python syntax highlighter for template preview."""

    def __init__(self, parent):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF6B6B"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ['class', 'def', 'return', 'import', 'from', 'if', 'else',
                    'for', 'in', 'try', 'except', 'True', 'False', 'None', 'self']
        for word in keywords:
            self.highlighting_rules.append((rf'\b{word}\b', keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#98C379"))
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#5C6370"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r'#[^\n]*', comment_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#61AFEF"))
        self.highlighting_rules.append((r'\bdef\s+(\w+)', function_format))

        # Classes
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#E5C07B"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\bclass\s+(\w+)', class_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class OllamaModelWorker(QThread):
    """Background worker for pulling Ollama models."""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    def _find_ollama_executable(self):
        """Find the Ollama executable on the system."""
        import shutil
        import os

        # First try PATH
        ollama_path = shutil.which('ollama')
        if ollama_path:
            return ollama_path

        # Common Windows installation paths
        if os.name == 'nt':
            # Get username safely
            try:
                username = os.getlogin()
            except OSError:
                username = os.environ.get('USERNAME', '')

            possible_paths = [
                # Most common installation location
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Ollama', 'ollama.exe'),
                # User home directory variations
                os.path.expanduser(r'~\AppData\Local\Programs\Ollama\ollama.exe'),
                os.path.join(r'C:\Users', username, 'AppData', 'Local', 'Programs', 'Ollama', 'ollama.exe'),
                # Program Files locations
                os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'Ollama', 'ollama.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'), 'Ollama', 'ollama.exe'),
                # Fallback hardcoded paths
                r'C:\Program Files\Ollama\ollama.exe',
            ]

            for path in possible_paths:
                if path and os.path.exists(path):
                    return path

        # macOS/Linux paths
        else:
            possible_paths = [
                '/usr/local/bin/ollama',
                '/usr/bin/ollama',
                os.path.expanduser('~/.local/bin/ollama'),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path

        return None

    def run(self):
        import subprocess
        import sys
        import os
        try:
            # Find Ollama executable
            ollama_exe = self._find_ollama_executable()
            if not ollama_exe:
                # Provide helpful error with debug info
                localappdata = os.environ.get('LOCALAPPDATA', 'not set')
                expected_path = os.path.join(localappdata, 'Programs', 'Ollama', 'ollama.exe')
                self.finished.emit(
                    False,
                    f"Ollama executable not found.\n"
                    f"Expected at: {expected_path}\n"
                    f"Please ensure Ollama is installed from https://ollama.ai"
                )
                return

            # Get startupinfo to hide console on Windows
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            self.progress.emit(f"Downloading {self.model_name}... This may take several minutes.")

            # Run ollama pull command
            # Use encoding='utf-8' and errors='replace' to handle special characters in progress output
            result = subprocess.run(
                [ollama_exe, 'pull', self.model_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo,
                creationflags=creationflags,
                timeout=1800  # 30 minute timeout for large models
            )

            if result.returncode == 0:
                self.finished.emit(True, f"Model '{self.model_name}' downloaded successfully!")
            else:
                # Clean up error message - replace any problematic characters
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                # Remove non-printable characters
                error_msg = ''.join(c if c.isprintable() or c in '\n\r\t' else '?' for c in error_msg)
                self.finished.emit(False, f"Failed: {error_msg}")

        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Download timed out. Try running 'ollama pull' manually.")
        except FileNotFoundError:
            self.finished.emit(False, "Ollama not found. Please install from https://ollama.ai")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class APIKeyDialog(QDialog):
    """Dialog for configuring AI provider API keys."""

    def __init__(self, provider_manager, parent=None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        self.setWindowTitle("Configure AI Providers")
        self.setMinimumWidth(550)
        self.ollama_worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Configure AI providers for template generation.\n"
            "Ollama runs locally (free). Cloud providers require API keys."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Ollama (Local) - First since it's free
        ollama_group = QGroupBox("Ollama (Local - Free)")
        ollama_layout = QFormLayout(ollama_group)

        # Model selection dropdown
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setMinimumWidth(200)
        self.ollama_model_combo.addItems([
            "llama3.2:3b",
            "llama3.2:1b",
            "llama3.1:8b",
            "mistral:7b",
            "qwen2.5:7b",
            "codellama:7b",
            "phi3:mini",
        ])
        ollama_layout.addRow("Model to Download:", self.ollama_model_combo)

        # Download button and status
        ollama_btn_layout = QHBoxLayout()
        self.ollama_download_btn = QPushButton("Download Model")
        self.ollama_download_btn.clicked.connect(self.download_ollama_model)
        self.ollama_status = QLabel("")
        ollama_btn_layout.addWidget(self.ollama_download_btn)
        ollama_btn_layout.addWidget(self.ollama_status)
        ollama_btn_layout.addStretch()
        ollama_layout.addRow("", ollama_btn_layout)

        # Progress bar for download
        self.ollama_progress = QProgressBar()
        self.ollama_progress.setRange(0, 0)  # Indeterminate
        self.ollama_progress.setVisible(False)
        ollama_layout.addRow("", self.ollama_progress)

        # Installed models display
        self.ollama_installed = QLabel("")
        self.refresh_ollama_models()
        ollama_layout.addRow("Installed:", self.ollama_installed)

        ollama_link = QLabel('<a href="https://ollama.ai">Download Ollama</a> | <a href="https://ollama.ai/library">Browse Models</a>')
        ollama_link.setOpenExternalLinks(True)
        ollama_layout.addRow("", ollama_link)

        layout.addWidget(ollama_group)

        # Provider API key inputs
        self.key_inputs = {}

        # Claude (Anthropic)
        claude_group = QGroupBox("Claude (Anthropic)")
        claude_layout = QFormLayout(claude_group)
        self.claude_key = QLineEdit()
        self.claude_key.setEchoMode(QLineEdit.Password)
        self.claude_key.setPlaceholderText("sk-ant-...")
        self.claude_key.setText(self.provider_manager.get_api_key('claude') or '')
        claude_layout.addRow("API Key:", self.claude_key)

        claude_link = QLabel('<a href="https://console.anthropic.com/settings/keys">Get API key from Anthropic Console</a>')
        claude_link.setOpenExternalLinks(True)
        claude_layout.addRow("", claude_link)

        self.claude_test = QPushButton("Test Connection")
        self.claude_test.clicked.connect(lambda: self.test_provider('claude', self.claude_key.text()))
        self.claude_status = QLabel("")
        test_layout = QHBoxLayout()
        test_layout.addWidget(self.claude_test)
        test_layout.addWidget(self.claude_status)
        test_layout.addStretch()
        claude_layout.addRow("", test_layout)

        layout.addWidget(claude_group)
        self.key_inputs['claude'] = self.claude_key

        # OpenAI
        openai_group = QGroupBox("OpenAI")
        openai_layout = QFormLayout(openai_group)
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("sk-...")
        self.openai_key.setText(self.provider_manager.get_api_key('openai') or '')
        openai_layout.addRow("API Key:", self.openai_key)

        openai_link = QLabel('<a href="https://platform.openai.com/api-keys">Get API key from OpenAI</a>')
        openai_link.setOpenExternalLinks(True)
        openai_layout.addRow("", openai_link)

        self.openai_test = QPushButton("Test Connection")
        self.openai_test.clicked.connect(lambda: self.test_provider('openai', self.openai_key.text()))
        self.openai_status = QLabel("")
        test_layout2 = QHBoxLayout()
        test_layout2.addWidget(self.openai_test)
        test_layout2.addWidget(self.openai_status)
        test_layout2.addStretch()
        openai_layout.addRow("", test_layout2)

        layout.addWidget(openai_group)
        self.key_inputs['openai'] = self.openai_key

        # OpenRouter
        openrouter_group = QGroupBox("OpenRouter (Access multiple models)")
        openrouter_layout = QFormLayout(openrouter_group)
        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.Password)
        self.openrouter_key.setPlaceholderText("sk-or-...")
        self.openrouter_key.setText(self.provider_manager.get_api_key('openrouter') or '')
        openrouter_layout.addRow("API Key:", self.openrouter_key)

        openrouter_link = QLabel('<a href="https://openrouter.ai/keys">Get API key from OpenRouter</a>')
        openrouter_link.setOpenExternalLinks(True)
        openrouter_layout.addRow("", openrouter_link)

        self.openrouter_test = QPushButton("Test Connection")
        self.openrouter_test.clicked.connect(lambda: self.test_provider('openrouter', self.openrouter_key.text()))
        self.openrouter_status = QLabel("")
        test_layout3 = QHBoxLayout()
        test_layout3.addWidget(self.openrouter_test)
        test_layout3.addWidget(self.openrouter_status)
        test_layout3.addStretch()
        openrouter_layout.addRow("", test_layout3)

        layout.addWidget(openrouter_group)
        self.key_inputs['openrouter'] = self.openrouter_key

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_keys)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def test_provider(self, provider_name: str, api_key: str):
        """Test a provider connection."""
        if not api_key:
            status_label = getattr(self, f"{provider_name}_status")
            status_label.setText("Enter API key first")
            status_label.setStyleSheet("color: orange;")
            return

        # Temporarily set the key and test
        self.provider_manager.set_api_key(provider_name, api_key)
        available, message = self.provider_manager.test_provider(provider_name)

        status_label = getattr(self, f"{provider_name}_status")
        if available:
            status_label.setText("✓ Connected")
            status_label.setStyleSheet("color: green;")
        else:
            status_label.setText(f"✗ {message}")
            status_label.setStyleSheet("color: red;")

    def save_keys(self):
        """Save all API keys."""
        for provider_name, input_widget in self.key_inputs.items():
            key = input_widget.text().strip()
            if key:
                self.provider_manager.set_api_key(provider_name, key)

        self.accept()

    def refresh_ollama_models(self):
        """Refresh the list of installed Ollama models."""
        try:
            from ai_providers import OllamaProvider
            provider = OllamaProvider()
            models = provider.get_available_models()
            if models:
                # Show first 3 models, add "..." if more
                display = ", ".join(models[:3])
                if len(models) > 3:
                    display += f", ... (+{len(models) - 3} more)"
                self.ollama_installed.setText(display)
                self.ollama_installed.setStyleSheet("color: green;")
            else:
                self.ollama_installed.setText("No models installed")
                self.ollama_installed.setStyleSheet("color: orange;")
        except Exception as e:
            self.ollama_installed.setText(f"Error: {e}")
            self.ollama_installed.setStyleSheet("color: red;")

    def download_ollama_model(self):
        """Download the selected Ollama model."""
        model = self.ollama_model_combo.currentText()
        if not model:
            return

        # Disable button and show progress
        self.ollama_download_btn.setEnabled(False)
        self.ollama_progress.setVisible(True)
        self.ollama_status.setText(f"Downloading {model}...")
        self.ollama_status.setStyleSheet("color: blue;")

        # Start download worker
        self.ollama_worker = OllamaModelWorker(model)
        self.ollama_worker.finished.connect(self.on_ollama_download_complete)
        self.ollama_worker.progress.connect(lambda msg: self.ollama_status.setText(msg))
        self.ollama_worker.start()

    def on_ollama_download_complete(self, success: bool, message: str):
        """Handle Ollama model download completion."""
        self.ollama_download_btn.setEnabled(True)
        self.ollama_progress.setVisible(False)

        if success:
            self.ollama_status.setText("✓ " + message)
            self.ollama_status.setStyleSheet("color: green;")
            self.refresh_ollama_models()
        else:
            self.ollama_status.setText("✗ " + message)
            self.ollama_status.setStyleSheet("color: red;")


class TemplateBuilderDialog(QDialog):
    """
    AI-Assisted Template Builder Dialog.

    Guides users through creating invoice templates with AI suggestions.
    Supports multiple AI providers: Ollama (local), Claude, OpenAI, OpenRouter.
    """

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Template Builder")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setMinimumSize(1200, 800)

        self.provider_manager = AIProviderManager()
        self.current_provider = None
        self.current_text = ""
        self.analysis: Optional[TemplateAnalysis] = None
        self.patterns: Dict[str, str] = {}
        self.worker = None

        self.setup_ui()
        self.refresh_provider_status()

    def setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)

        # Provider selection bar at top
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)

        # Provider dropdown
        status_layout.addWidget(QLabel("AI Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(150)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        status_layout.addWidget(self.provider_combo)

        # Provider status
        self.provider_status = QLabel("Checking...")
        status_layout.addWidget(self.provider_status)

        # Configure button (for API keys)
        self.configure_btn = QPushButton("Configure...")
        self.configure_btn.clicked.connect(self.show_api_key_dialog)
        status_layout.addWidget(self.configure_btn)

        status_layout.addStretch()

        # Model dropdown
        status_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        status_layout.addWidget(self.model_combo)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_provider_status)
        status_layout.addWidget(self.refresh_btn)

        layout.addWidget(self.status_frame)

        # Main content - tabbed interface
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Tab 1: Load Sample
        self.setup_load_tab()

        # Tab 2: AI Analysis
        self.setup_analysis_tab()

        # Tab 3: Pattern Editor
        self.setup_patterns_tab()

        # Tab 4: Preview & Save
        self.setup_preview_tab()

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Bottom buttons
        button_layout = QHBoxLayout()
        self.prev_btn = QPushButton("< Previous")
        self.prev_btn.clicked.connect(self.prev_tab)
        self.next_btn = QPushButton("Next >")
        self.next_btn.clicked.connect(self.next_tab)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.prev_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.next_btn)
        layout.addLayout(button_layout)

        self.update_nav_buttons()
        self.tabs.currentChanged.connect(self.update_nav_buttons)

    def setup_load_tab(self):
        """Setup the sample loading tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "Step 1: Load a sample invoice PDF\n\n"
            "Select a PDF invoice that represents the format you want to create a template for. "
            "The AI will analyze the text and suggest extraction patterns."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # PDF selection
        file_layout = QHBoxLayout()
        self.pdf_path = QLineEdit()
        self.pdf_path.setPlaceholderText("Select a sample PDF invoice...")
        self.pdf_path.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_pdf)

        file_layout.addWidget(self.pdf_path)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Extracted text preview
        text_group = QGroupBox("Extracted Text Preview")
        text_layout = QVBoxLayout(text_group)
        self.text_preview = QPlainTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setFont(QFont("Consolas", 10))
        text_layout.addWidget(self.text_preview)
        layout.addWidget(text_group, 1)

        # Manual text option
        manual_btn = QPushButton("Or paste text manually...")
        manual_btn.clicked.connect(self.show_manual_input)
        layout.addWidget(manual_btn)

        self.tabs.addTab(tab, "1. Load Sample")

    def setup_analysis_tab(self):
        """Setup the AI analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "Step 2: AI Analysis\n\n"
            "Click 'Analyze' to have the AI examine the invoice and suggest extraction patterns. "
            "Review the suggestions and adjust as needed."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Analyze button
        analyze_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze with AI")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setEnabled(False)
        self.analysis_status = QLabel("")
        analyze_layout.addWidget(self.analyze_btn)
        analyze_layout.addWidget(self.analysis_status)
        analyze_layout.addStretch()
        layout.addLayout(analyze_layout)

        # Results splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Analysis results
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)

        # Company name
        company_layout = QFormLayout()
        self.company_name = QLineEdit()
        company_layout.addRow("Company Name:", self.company_name)
        results_layout.addLayout(company_layout)

        # Indicators
        self.indicators_list = QListWidget()
        self.indicators_list.setMaximumHeight(100)
        results_layout.addWidget(QLabel("Invoice Indicators:"))
        results_layout.addWidget(self.indicators_list)

        # Suggested patterns table
        results_layout.addWidget(QLabel("Suggested Patterns:"))
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(4)
        self.patterns_table.setHorizontalHeaderLabels(["Field", "Pattern", "Sample Match", "Use"])
        self.patterns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        results_layout.addWidget(self.patterns_table)

        splitter.addWidget(results_group)

        # Right: Notes and line items
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Line item pattern
        line_group = QGroupBox("Line Item Pattern")
        line_layout = QVBoxLayout(line_group)
        self.line_pattern = QPlainTextEdit()
        self.line_pattern.setMaximumHeight(80)
        self.line_pattern.setFont(QFont("Consolas", 10))
        line_layout.addWidget(self.line_pattern)

        self.line_columns = QLineEdit()
        self.line_columns.setPlaceholderText("part_number, quantity, total_price, ...")
        line_layout.addWidget(QLabel("Columns (comma-separated):"))
        line_layout.addWidget(self.line_columns)
        right_layout.addWidget(line_group)

        # Notes
        notes_group = QGroupBox("AI Notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_text = QPlainTextEdit()
        self.notes_text.setReadOnly(True)
        notes_layout.addWidget(self.notes_text)
        right_layout.addWidget(notes_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, 1)

        self.tabs.addTab(tab, "2. AI Analysis")

    def setup_patterns_tab(self):
        """Setup the pattern editor tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "Step 3: Test & Refine Patterns\n\n"
            "Test each pattern against the sample text. Click 'Refine with AI' if a pattern "
            "doesn't work correctly, or edit it manually."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Pattern list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.pattern_list = QListWidget()
        self.pattern_list.currentRowChanged.connect(self.on_pattern_selected)
        left_layout.addWidget(QLabel("Patterns:"))
        left_layout.addWidget(self.pattern_list)

        # Add custom pattern
        add_layout = QHBoxLayout()
        self.new_pattern_name = QLineEdit()
        self.new_pattern_name.setPlaceholderText("New pattern name...")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_custom_pattern)
        add_layout.addWidget(self.new_pattern_name)
        add_layout.addWidget(add_btn)
        left_layout.addLayout(add_layout)

        splitter.addWidget(left_widget)

        # Right: Pattern editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Pattern input
        self.pattern_edit = QPlainTextEdit()
        self.pattern_edit.setMaximumHeight(80)
        self.pattern_edit.setFont(QFont("Consolas", 10))
        right_layout.addWidget(QLabel("Regex Pattern:"))
        right_layout.addWidget(self.pattern_edit)

        # Test buttons
        test_layout = QHBoxLayout()
        test_btn = QPushButton("Test Pattern")
        test_btn.clicked.connect(self.test_current_pattern)
        refine_btn = QPushButton("Refine with AI")
        refine_btn.clicked.connect(self.refine_pattern)
        test_layout.addWidget(test_btn)
        test_layout.addWidget(refine_btn)
        test_layout.addStretch()
        right_layout.addLayout(test_layout)

        # Test results
        self.test_results = QPlainTextEdit()
        self.test_results.setReadOnly(True)
        self.test_results.setFont(QFont("Consolas", 10))
        right_layout.addWidget(QLabel("Test Results:"))
        right_layout.addWidget(self.test_results)

        # Desired output for refinement
        self.desired_output = QLineEdit()
        self.desired_output.setPlaceholderText("Enter desired extraction result for AI refinement...")
        right_layout.addWidget(QLabel("Desired Output (for refinement):"))
        right_layout.addWidget(self.desired_output)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter, 1)

        self.tabs.addTab(tab, "3. Test Patterns")

    def setup_preview_tab(self):
        """Setup the preview and save tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Template metadata
        meta_group = QGroupBox("Template Metadata")
        meta_layout = QFormLayout(meta_group)

        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("e.g., acme_corp")
        meta_layout.addRow("Template Name:", self.template_name)

        self.class_name = QLineEdit()
        self.class_name.setPlaceholderText("e.g., AcmeCorpTemplate")
        meta_layout.addRow("Class Name:", self.class_name)

        self.template_enabled = QCheckBox("Enable template after creation")
        self.template_enabled.setChecked(True)
        meta_layout.addRow("", self.template_enabled)

        layout.addWidget(meta_group)

        # Code preview
        code_group = QGroupBox("Generated Template Code")
        code_layout = QVBoxLayout(code_group)

        self.code_preview = QPlainTextEdit()
        self.code_preview.setFont(QFont("Consolas", 10))
        self.highlighter = PythonHighlighter(self.code_preview.document())
        code_layout.addWidget(self.code_preview)

        # Generate button
        gen_layout = QHBoxLayout()
        generate_btn = QPushButton("Generate Code")
        generate_btn.clicked.connect(self.generate_code)
        gen_layout.addWidget(generate_btn)
        gen_layout.addStretch()
        code_layout.addLayout(gen_layout)

        layout.addWidget(code_group, 1)

        # Save button
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Save Template")
        save_btn.clicked.connect(self.save_template)
        save_btn.setStyleSheet("font-weight: bold; padding: 10px 20px;")
        save_layout.addStretch()
        save_layout.addWidget(save_btn)
        layout.addLayout(save_layout)

        self.tabs.addTab(tab, "4. Save Template")

    def refresh_provider_status(self):
        """Refresh provider list and status."""
        # Populate provider combo
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()

        providers = self.provider_manager.get_available_providers()
        default_provider = self.provider_manager.get_default_provider()
        default_idx = 0

        for i, (key, name, is_configured) in enumerate(providers):
            status = "" if is_configured else " (not configured)"
            self.provider_combo.addItem(f"{name}{status}", key)
            if key == default_provider:
                default_idx = i

        self.provider_combo.setCurrentIndex(default_idx)
        self.provider_combo.blockSignals(False)

        # Update status for current provider
        self.on_provider_changed(default_idx)

    def on_provider_changed(self, index: int):
        """Handle provider selection change."""
        if index < 0:
            return

        provider_key = self.provider_combo.itemData(index)
        if not provider_key:
            return

        # Test provider availability
        available, message = self.provider_manager.test_provider(provider_key)

        if available:
            self.provider_status.setText(message)
            self.provider_status.setStyleSheet("color: green;")

            # Get provider and update model list
            try:
                self.current_provider = self.provider_manager.get_provider(provider_key)
                models = self.current_provider.get_available_models()
                self.model_combo.clear()
                self.model_combo.addItems(models)

                # Select saved model or first
                saved_model = self.provider_manager.get_selected_model(provider_key)
                if saved_model:
                    idx = self.model_combo.findText(saved_model)
                    if idx >= 0:
                        self.model_combo.setCurrentIndex(idx)

                # Save as default
                self.provider_manager.set_default_provider(provider_key)

            except Exception as e:
                self.provider_status.setText(f"Error: {e}")
                self.provider_status.setStyleSheet("color: red;")
        else:
            self.provider_status.setText(message)
            self.provider_status.setStyleSheet("color: red;")
            self.model_combo.clear()
            self.model_combo.addItem("Configure API key first")
            self.current_provider = None

    def on_model_changed(self, index: int):
        """Handle model selection change."""
        if index < 0 or not self.current_provider:
            return

        model = self.model_combo.currentText()
        if model and model != "Configure API key first":
            provider_key = self.provider_combo.itemData(self.provider_combo.currentIndex())
            if provider_key:
                self.provider_manager.set_selected_model(provider_key, model)
                self.current_provider.model = model

    def show_api_key_dialog(self):
        """Show dialog to configure API keys."""
        dialog = APIKeyDialog(self.provider_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_provider_status()

    def browse_pdf(self):
        """Browse for a PDF file."""
        if not HAS_PDFPLUMBER:
            QMessageBox.warning(
                self, "Missing Dependency",
                "pdfplumber is not installed. Run: pip install pdfplumber"
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sample Invoice PDF",
            "", "PDF Files (*.pdf)"
        )

        if file_path:
            self.pdf_path.setText(file_path)
            self.extract_pdf_text(file_path)

    def extract_pdf_text(self, pdf_path: str):
        """Extract text from PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n---PAGE BREAK---\n"

                self.current_text = text
                self.text_preview.setPlainText(text)
                self.analyze_btn.setEnabled(bool(text.strip()))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract PDF text: {e}")

    def show_manual_input(self):
        """Allow manual text input."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Paste Invoice Text")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)
        text_edit = QPlainTextEdit()
        text_edit.setPlaceholderText("Paste the extracted invoice text here...")
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            self.current_text = text_edit.toPlainText()
            self.text_preview.setPlainText(self.current_text)
            self.analyze_btn.setEnabled(bool(self.current_text.strip()))

    def run_analysis(self):
        """Run AI analysis on the text."""
        if not self.current_text.strip():
            return

        if not self.current_provider:
            QMessageBox.warning(
                self, "No Provider",
                "Please select and configure an AI provider first."
            )
            return

        # Update model selection
        model = self.model_combo.currentText()
        if model and model != "Configure API key first":
            self.current_provider.model = model

        self.analyze_btn.setEnabled(False)
        self.analysis_status.setText("Analyzing...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate

        self.worker = AnalysisWorker(self.current_provider, self.current_text)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.progress.connect(lambda msg: self.analysis_status.setText(msg))
        self.worker.start()

    def on_analysis_complete(self, analysis: TemplateAnalysis):
        """Handle completed analysis."""
        self.analysis = analysis
        self.progress.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.analysis_status.setText("Analysis complete!")

        # Populate UI
        self.company_name.setText(analysis.company_name)

        # Indicators
        self.indicators_list.clear()
        for indicator in analysis.invoice_indicators:
            item = QListWidgetItem(indicator)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.indicators_list.addItem(item)

        # Patterns table
        self.patterns_table.setRowCount(0)
        for field, pattern in analysis.suggested_patterns.items():
            row = self.patterns_table.rowCount()
            self.patterns_table.insertRow(row)
            self.patterns_table.setItem(row, 0, QTableWidgetItem(field))
            self.patterns_table.setItem(row, 1, QTableWidgetItem(pattern.pattern))
            self.patterns_table.setItem(row, 2, QTableWidgetItem(pattern.sample_match))

            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.patterns_table.setCellWidget(row, 3, checkbox)

            # Store pattern
            self.patterns[field] = pattern.pattern

        # Line items
        self.line_pattern.setPlainText(analysis.line_item_pattern)
        self.line_columns.setText(", ".join(analysis.line_item_columns))

        # Notes
        self.notes_text.setPlainText("\n".join(analysis.notes))

        # Update pattern list
        self.update_pattern_list()

        # Auto-generate template name
        if analysis.company_name:
            name = analysis.company_name.lower().replace(' ', '_')
            name = re.sub(r'[^a-z0-9_]', '', name)
            self.template_name.setText(name)
            self.class_name.setText(name.title().replace('_', '') + 'Template')

    def on_analysis_error(self, error: str):
        """Handle analysis error."""
        self.progress.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.analysis_status.setText(f"Error: {error}")
        QMessageBox.critical(self, "Analysis Error", f"AI analysis failed: {error}")

    def update_pattern_list(self):
        """Update the pattern list widget."""
        self.pattern_list.clear()
        for field in self.patterns:
            self.pattern_list.addItem(field)

        # Add line_items pattern
        self.pattern_list.addItem("line_items")

    def on_pattern_selected(self, row: int):
        """Handle pattern selection."""
        if row < 0:
            return

        item = self.pattern_list.item(row)
        if not item:
            return

        field = item.text()
        if field == "line_items":
            self.pattern_edit.setPlainText(self.line_pattern.toPlainText())
        else:
            self.pattern_edit.setPlainText(self.patterns.get(field, ''))

    def add_custom_pattern(self):
        """Add a custom pattern."""
        name = self.new_pattern_name.text().strip()
        if not name:
            return

        name = name.lower().replace(' ', '_')
        if name not in self.patterns:
            self.patterns[name] = ''
            self.pattern_list.addItem(name)
            self.new_pattern_name.clear()

    def test_current_pattern(self):
        """Test the current pattern."""
        pattern = self.pattern_edit.toPlainText().strip()
        if not pattern or not self.current_text:
            return

        if self.current_provider:
            matches = self.current_provider.test_pattern(pattern, self.current_text)
        else:
            # Fallback to basic regex test
            import re
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                matches = compiled.findall(self.current_text)[:20]
            except re.error as e:
                matches = [f"Regex error: {e}"]

        if matches:
            result = f"Found {len(matches)} match(es):\n\n"
            result += "\n".join(f"  {i+1}. {m}" for i, m in enumerate(matches))
        else:
            result = "No matches found."

        self.test_results.setPlainText(result)

    def refine_pattern(self):
        """Refine pattern with AI."""
        if not self.current_provider:
            QMessageBox.warning(
                self, "No Provider",
                "Please select and configure an AI provider first."
            )
            return

        current_item = self.pattern_list.currentItem()
        if not current_item:
            return

        field = current_item.text()
        current_pattern = self.pattern_edit.toPlainText().strip()
        desired = self.desired_output.text().strip()

        if not desired:
            QMessageBox.information(
                self, "Refinement",
                "Please enter the desired output in the field below."
            )
            return

        self.analysis_status.setText("Refining pattern...")

        try:
            # Use first 500 chars of sample text
            sample = self.current_text[:500]
            refined = self.current_provider.refine_pattern(field, current_pattern, sample, desired)

            self.pattern_edit.setPlainText(refined)
            self.patterns[field] = refined
            self.analysis_status.setText("Pattern refined!")

            # Auto-test
            self.test_current_pattern()

        except Exception as e:
            self.analysis_status.setText(f"Refinement failed: {e}")

    def generate_code(self):
        """Generate template code."""
        if not self.analysis:
            QMessageBox.warning(self, "No Analysis", "Please run AI analysis first.")
            return

        template_name = self.template_name.text().strip()
        class_name = self.class_name.text().strip()

        if not template_name or not class_name:
            QMessageBox.warning(self, "Missing Info", "Please enter template and class names.")
            return

        # Update analysis with current values
        self.analysis.company_name = self.company_name.text().strip()

        # Get indicators from list
        indicators = []
        for i in range(self.indicators_list.count()):
            item = self.indicators_list.item(i)
            if item:
                indicators.append(item.text())
        self.analysis.invoice_indicators = indicators

        # Update line pattern
        self.analysis.line_item_pattern = self.line_pattern.toPlainText().strip()
        self.analysis.line_item_columns = [
            c.strip() for c in self.line_columns.text().split(',') if c.strip()
        ]

        # Update patterns from table
        for row in range(self.patterns_table.rowCount()):
            field_item = self.patterns_table.item(row, 0)
            pattern_item = self.patterns_table.item(row, 1)
            checkbox = self.patterns_table.cellWidget(row, 3)

            if field_item and pattern_item and checkbox and checkbox.isChecked():
                field = field_item.text()
                pattern = pattern_item.text()
                if field in self.analysis.suggested_patterns:
                    self.analysis.suggested_patterns[field].pattern = pattern

        # Generate code using standalone function
        code = generate_template_code(
            self.analysis, template_name, class_name
        )

        self.code_preview.setPlainText(code)

    def save_template(self):
        """Save the template to file and auto-register it."""
        code = self.code_preview.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "No Code", "Please generate code first.")
            return

        template_name = self.template_name.text().strip()
        class_name = self.class_name.text().strip()
        if not template_name:
            QMessageBox.warning(self, "No Name", "Please enter a template name.")
            return
        if not class_name:
            QMessageBox.warning(self, "No Class Name", "Please enter a class name.")
            return

        # Determine templates directory
        templates_dir = Path(__file__).parent / "templates"
        if not templates_dir.exists():
            templates_dir.mkdir(parents=True)

        file_name = f"{template_name}.py"
        file_path = templates_dir / file_name

        # Check if exists
        if file_path.exists():
            result = QMessageBox.question(
                self, "File Exists",
                f"{file_name} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return

        # Write file
        try:
            file_path.write_text(code)

            # Auto-register the template in __init__.py
            registered = self._auto_register_template(templates_dir, template_name, class_name)

            if registered:
                QMessageBox.information(
                    self, "Template Created",
                    f"Template '{template_name}' has been created and registered!\n\n"
                    f"Click 'Refresh' in the Templates tab to see it."
                )
            else:
                QMessageBox.information(
                    self, "Template Saved",
                    f"Template saved to:\n{file_path}\n\n"
                    f"Auto-registration failed. Please manually add to templates/__init__.py:\n\n"
                    f"from .{template_name} import {class_name}\n"
                    f"TEMPLATE_REGISTRY['{template_name}'] = {class_name}"
                )

            self.template_created.emit(template_name, str(file_path))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save template: {e}")

    def _auto_register_template(self, templates_dir: Path, template_name: str, class_name: str) -> bool:
        """
        Auto-register the template in templates/__init__.py.
        Returns True if successful, False otherwise.
        """
        init_file = templates_dir / "__init__.py"
        if not init_file.exists():
            return False

        try:
            content = init_file.read_text()

            # Check if already registered
            if f"'{template_name}'" in content or f'"{template_name}"' in content:
                return True  # Already registered

            # Add import statement after other imports
            import_line = f"from .{template_name} import {class_name}\n"

            # Find the last import line
            lines = content.split('\n')
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('from .') and 'import' in line:
                    last_import_idx = i

            # Insert new import after last import
            lines.insert(last_import_idx + 1, import_line.rstrip())

            # Add to TEMPLATE_REGISTRY
            registry_entry = f"    '{template_name}': {class_name},"

            # Find TEMPLATE_REGISTRY and add entry before closing brace
            new_lines = []
            in_registry = False
            added_entry = False

            for line in lines:
                if 'TEMPLATE_REGISTRY' in line and '{' in line:
                    in_registry = True
                if in_registry and '}' in line and not added_entry:
                    # Add our entry before the closing brace
                    new_lines.append(registry_entry)
                    added_entry = True
                    in_registry = False
                new_lines.append(line)

            # Write back
            init_file.write_text('\n'.join(new_lines))
            return True

        except Exception as e:
            print(f"Auto-register failed: {e}")
            return False

    def update_nav_buttons(self):
        """Update navigation button states."""
        current = self.tabs.currentIndex()
        self.prev_btn.setEnabled(current > 0)

        if current == self.tabs.count() - 1:
            self.next_btn.setText("Finish")
        else:
            self.next_btn.setText("Next >")

    def prev_tab(self):
        """Go to previous tab."""
        current = self.tabs.currentIndex()
        if current > 0:
            self.tabs.setCurrentIndex(current - 1)

    def next_tab(self):
        """Go to next tab."""
        current = self.tabs.currentIndex()
        if current < self.tabs.count() - 1:
            self.tabs.setCurrentIndex(current + 1)
        else:
            self.save_template()
