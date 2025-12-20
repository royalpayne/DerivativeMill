"""
AI-Assisted Template Builder for CRMill
Semi-guided template creation using local Ollama LLM.
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

from ollama_helper import OllamaHelper, TemplateAnalysis, ExtractionPattern


class AnalysisWorker(QThread):
    """Background worker for AI analysis."""
    finished = pyqtSignal(object)  # TemplateAnalysis
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, helper: OllamaHelper, text: str):
        super().__init__()
        self.helper = helper
        self.text = text

    def run(self):
        try:
            self.progress.emit("Analyzing invoice structure...")
            analysis = self.helper.analyze_invoice_text(self.text)
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


class TemplateBuilderDialog(QDialog):
    """
    AI-Assisted Template Builder Dialog.

    Guides users through creating invoice templates with AI suggestions.
    """

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Template Builder")
        self.setMinimumSize(1200, 800)

        self.ollama = OllamaHelper()
        self.current_text = ""
        self.analysis: Optional[TemplateAnalysis] = None
        self.patterns: Dict[str, str] = {}
        self.worker = None

        self.setup_ui()
        self.check_ollama_status()

    def setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)

        # Status bar at top
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)

        self.ollama_status = QLabel("Checking Ollama status...")
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(150)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.check_ollama_status)

        status_layout.addWidget(QLabel("Ollama:"))
        status_layout.addWidget(self.ollama_status)
        status_layout.addStretch()
        status_layout.addWidget(QLabel("Model:"))
        status_layout.addWidget(self.model_combo)
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

    def check_ollama_status(self):
        """Check if Ollama is available."""
        available, message = self.ollama.is_available()

        if available:
            self.ollama_status.setText(f"<span style='color:green;'>{message}</span>")
            self.ollama_status.setStyleSheet("color: green;")
            models = self.ollama.get_available_models()
            self.model_combo.clear()
            self.model_combo.addItems(models)

            # Select best model
            best = self.ollama.get_best_model()
            if best:
                idx = self.model_combo.findText(best)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
        else:
            self.ollama_status.setText(message)
            self.ollama_status.setStyleSheet("color: red;")
            self.model_combo.clear()
            self.model_combo.addItem("No models available")

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

        # Update model selection
        model = self.model_combo.currentText()
        if model and model != "No models available":
            self.ollama.model = model

        self.analyze_btn.setEnabled(False)
        self.analysis_status.setText("Analyzing...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate

        self.worker = AnalysisWorker(self.ollama, self.current_text)
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

        matches = self.ollama.test_pattern(pattern, self.current_text)

        if matches:
            result = f"Found {len(matches)} match(es):\n\n"
            result += "\n".join(f"  {i+1}. {m}" for i, m in enumerate(matches))
        else:
            result = "No matches found."

        self.test_results.setPlainText(result)

    def refine_pattern(self):
        """Refine pattern with AI."""
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
            refined = self.ollama.refine_pattern(field, current_pattern, sample, desired)

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

        # Generate code
        code = self.ollama.generate_template_code(
            self.analysis, template_name, class_name
        )

        self.code_preview.setPlainText(code)

    def save_template(self):
        """Save the template to file."""
        code = self.code_preview.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "No Code", "Please generate code first.")
            return

        template_name = self.template_name.text().strip()
        if not template_name:
            QMessageBox.warning(self, "No Name", "Please enter a template name.")
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
            QMessageBox.information(
                self, "Template Saved",
                f"Template saved to:\n{file_path}\n\n"
                f"Remember to register it in templates/__init__.py"
            )
            self.template_created.emit(template_name, str(file_path))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save template: {e}")

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
