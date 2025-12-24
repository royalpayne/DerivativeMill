"""
Token Template Builder Dialog for TariffMill

PyQt5 UI for the token-based template builder.
Shows tokenized text with classifications, detected patterns,
and lets users map token types to fields.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QPlainTextEdit, QFileDialog, QGroupBox,
    QFormLayout, QMessageBox, QSplitter, QWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QCheckBox, QProgressBar, QStatusBar, QScrollArea,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QBrush

from token_template_builder import (
    TokenTemplateAnalyzer, TokenType, Token, TokenizedLine,
    DetectedPattern, Tokenizer
)


# Color scheme for token types
TOKEN_COLORS = {
    TokenType.DATE_ISO: QColor(100, 149, 237),      # Cornflower blue
    TokenType.DATE_US: QColor(100, 149, 237),
    TokenType.DATE_EU: QColor(100, 149, 237),
    TokenType.DATE_COMPACT: QColor(100, 149, 237),
    TokenType.INTEGER: QColor(144, 238, 144),        # Light green
    TokenType.DECIMAL: QColor(144, 238, 144),
    TokenType.CURRENCY: QColor(255, 215, 0),         # Gold
    TokenType.PERCENTAGE: QColor(255, 182, 193),     # Light pink
    TokenType.PART_CODE: QColor(255, 165, 0),        # Orange
    TokenType.BRACKETED_CODE: QColor(255, 140, 0),   # Dark orange
    TokenType.HTS_CODE: QColor(186, 85, 211),        # Medium orchid
    TokenType.PO_NUMBER: QColor(0, 206, 209),        # Dark turquoise
    TokenType.INVOICE_CODE: QColor(0, 191, 255),     # Deep sky blue
    TokenType.WORD: QColor(211, 211, 211),           # Light gray
    TokenType.PHRASE: QColor(192, 192, 192),         # Silver
    TokenType.UNIT: QColor(152, 251, 152),           # Pale green
    TokenType.COUNTRY: QColor(135, 206, 250),        # Light sky blue
    TokenType.SEPARATOR: QColor(169, 169, 169),      # Dark gray
    TokenType.EMPTY: QColor(245, 245, 245),          # White smoke
    TokenType.UNKNOWN: QColor(255, 99, 71),          # Tomato
}


class AnalysisWorker(QThread):
    """Worker thread for PDF analysis."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path

    def run(self):
        try:
            self.progress.emit("Loading PDF...")
            analyzer = TokenTemplateAnalyzer()

            self.progress.emit("Tokenizing text...")
            analyzer.analyze_pdf(self.pdf_path)

            self.progress.emit("Detecting patterns...")
            # Already done in analyze_pdf

            self.progress.emit("Analysis complete")
            self.finished.emit(analyzer)

        except Exception as e:
            self.error.emit(str(e))


class TokenLegendWidget(QWidget):
    """Shows legend of token type colors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        # Show key token types
        key_types = [
            (TokenType.PART_CODE, "Code"),
            (TokenType.CURRENCY, "Price"),
            (TokenType.INTEGER, "Number"),
            (TokenType.DATE_COMPACT, "Date"),
            (TokenType.HTS_CODE, "HTS"),
            (TokenType.COUNTRY, "Country"),
        ]

        for token_type, label in key_types:
            color = TOKEN_COLORS.get(token_type, QColor(200, 200, 200))

            indicator = QLabel("●")
            indicator.setStyleSheet(f"color: {color.name()}; font-size: 14px;")
            layout.addWidget(indicator)

            text = QLabel(label)
            text.setStyleSheet("font-size: 10px; color: #666;")
            layout.addWidget(text)

        layout.addStretch()


class TokenizedTextView(QTableWidget):
    """
    Displays tokenized text with color-coded token types.
    Each row is a line, each column is a token.
    """

    token_clicked = pyqtSignal(Token, int, int)  # token, row, col

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tokenized_lines: List[TokenizedLine] = []
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectItems)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.cellClicked.connect(self._on_cell_clicked)
        self.setFont(QFont("Consolas", 9))
        self.verticalHeader().setDefaultSectionSize(24)

    def set_tokenized_lines(self, lines: List[TokenizedLine], max_cols: int = 12):
        """Populate the table with tokenized lines."""
        self.tokenized_lines = lines

        # Find max columns needed
        actual_max_cols = min(max_cols, max(len(l.tokens) for l in lines) if lines else 1)

        self.setRowCount(len(lines))
        self.setColumnCount(actual_max_cols + 1)  # +1 for line number

        # Headers
        headers = ["Line"] + [f"Token {i+1}" for i in range(actual_max_cols)]
        self.setHorizontalHeaderLabels(headers)

        for row, line in enumerate(lines):
            # Line number
            line_item = QTableWidgetItem(str(line.line_number + 1))
            line_item.setBackground(QColor(240, 240, 240))
            line_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 0, line_item)

            # Tokens
            for col, token in enumerate(line.tokens[:actual_max_cols]):
                item = QTableWidgetItem(token.value)
                color = TOKEN_COLORS.get(token.token_type, QColor(255, 255, 255))
                item.setBackground(color)
                item.setToolTip(f"{token.token_type.name}\n{token.value}")
                self.setItem(row, col + 1, item)

        self.resizeColumnsToContents()

        # Cap column widths
        for i in range(self.columnCount()):
            if self.columnWidth(i) > 200:
                self.setColumnWidth(i, 200)

    def _on_cell_clicked(self, row: int, col: int):
        """Handle cell click."""
        if col == 0:  # Line number column
            return

        if row < len(self.tokenized_lines):
            line = self.tokenized_lines[row]
            token_idx = col - 1
            if token_idx < len(line.tokens):
                self.token_clicked.emit(line.tokens[token_idx], row, token_idx)


class PatternListWidget(QTreeWidget):
    """Shows detected patterns with samples."""

    pattern_selected = pyqtSignal(DetectedPattern)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.patterns: List[DetectedPattern] = []
        self.setHeaderLabels(["Pattern", "Frequency", "Confidence"])
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)
        self.setColumnWidth(0, 300)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 80)

    def set_patterns(self, patterns: List[DetectedPattern]):
        """Populate with detected patterns."""
        self.patterns = patterns
        self.clear()

        for i, pattern in enumerate(patterns):
            item = QTreeWidgetItem([
                pattern.simplified_signature,
                str(pattern.frequency),
                f"{pattern.confidence:.0%}"
            ])
            item.setData(0, Qt.UserRole, i)

            # Color based on confidence
            if pattern.confidence >= 0.7:
                item.setBackground(0, QColor(200, 255, 200))
            elif pattern.confidence >= 0.4:
                item.setBackground(0, QColor(255, 255, 200))

            # Add sample lines as children
            for sample in pattern.sample_lines[:3]:
                child = QTreeWidgetItem([sample.raw_text[:100], "", ""])
                child.setForeground(0, QBrush(QColor(100, 100, 100)))
                item.addChild(child)

            self.addTopLevelItem(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        # Only emit for top-level items (patterns, not samples)
        if item.parent() is None:
            idx = item.data(0, Qt.UserRole)
            if idx is not None and idx < len(self.patterns):
                self.pattern_selected.emit(self.patterns[idx])


class FieldMappingWidget(QWidget):
    """Widget for mapping token positions to field names."""

    mapping_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pattern: Optional[DetectedPattern] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Field Mapping")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        desc = QLabel("Assign field names to token positions in the detected pattern.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(desc)

        # Mapping table
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(["Position", "Token Type", "Field Name"])
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        self.mapping_table.setAlternatingRowColors(True)
        layout.addWidget(self.mapping_table)

        # Field name options
        self.field_options = [
            "", "part_number", "quantity", "unit_price", "total_price",
            "hs_code", "description", "po_number", "date", "country_origin",
            "unit", "line_number", "custom"
        ]

    def set_pattern(self, pattern: DetectedPattern):
        """Set the pattern to configure field mapping for."""
        self.current_pattern = pattern

        if not pattern or not pattern.sample_lines:
            self.mapping_table.setRowCount(0)
            return

        sample = pattern.sample_lines[0]
        tokens = [t for t in sample.tokens if t.token_type != TokenType.EMPTY]

        self.mapping_table.setRowCount(len(tokens))

        for i, token in enumerate(tokens):
            # Position
            pos_item = QTableWidgetItem(str(i + 1))
            pos_item.setFlags(pos_item.flags() & ~Qt.ItemIsEditable)
            self.mapping_table.setItem(i, 0, pos_item)

            # Token type
            type_item = QTableWidgetItem(token.token_type.name)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            color = TOKEN_COLORS.get(token.token_type, QColor(255, 255, 255))
            type_item.setBackground(color)
            self.mapping_table.setItem(i, 1, type_item)

            # Field name dropdown
            combo = QComboBox()
            combo.addItems(self.field_options)

            # Pre-select based on auto-mapping
            if i in pattern.field_mapping:
                field_name = pattern.field_mapping[i]
                if field_name in self.field_options:
                    combo.setCurrentText(field_name)

            combo.currentTextChanged.connect(self._on_mapping_changed)
            self.mapping_table.setCellWidget(i, 2, combo)

        self.mapping_table.resizeColumnsToContents()

    def _on_mapping_changed(self):
        """Handle mapping change."""
        if not self.current_pattern:
            return

        mapping = {}
        for i in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(i, 2)
            if combo and combo.currentText():
                mapping[i] = combo.currentText()

        self.current_pattern.field_mapping = mapping
        self.mapping_changed.emit(mapping)

    def get_mapping(self) -> Dict[int, str]:
        """Get the current field mapping."""
        mapping = {}
        for i in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(i, 2)
            if combo and combo.currentText():
                mapping[i] = combo.currentText()
        return mapping


class TokenTemplateDialog(QDialog):
    """
    Main dialog for the token-based template builder.
    """

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Token-Based Template Builder")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        self.setMinimumSize(1400, 900)

        self.analyzer: Optional[TokenTemplateAnalyzer] = None
        self.current_pdf = ""

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Token-Based Template Builder")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # PDF selection
        self.pdf_label = QLabel("No PDF loaded")
        self.pdf_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.pdf_label)

        self.btn_open = QPushButton("Open PDF")
        self.btn_open.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self.btn_open.clicked.connect(self._open_pdf)
        header_layout.addWidget(self.btn_open)

        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "This builder analyzes invoice text by recognizing DATA SHAPES (dates, codes, prices, quantities) "
            "instead of fixed positions. It handles inconsistent layouts by matching what the data IS, not where it is."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; padding: 5px; background: #f8f8f8; border-radius: 3px;")
        layout.addWidget(desc)

        # Progress bar (hidden by default)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Main content - tabbed
        self.tabs = QTabWidget()

        # Tab 1: Tokenized View
        token_tab = QWidget()
        token_layout = QVBoxLayout(token_tab)

        # Legend
        self.legend = TokenLegendWidget()
        token_layout.addWidget(self.legend)

        # Tokenized text table
        self.token_view = TokenizedTextView()
        self.token_view.token_clicked.connect(self._on_token_clicked)
        token_layout.addWidget(self.token_view)

        self.tabs.addTab(token_tab, "Tokenized Text")

        # Tab 2: Detected Patterns
        pattern_tab = QWidget()
        pattern_layout = QHBoxLayout(pattern_tab)

        # Pattern list
        pattern_left = QWidget()
        pattern_left_layout = QVBoxLayout(pattern_left)
        pattern_left_layout.setContentsMargins(0, 0, 0, 0)

        pattern_header = QLabel("Detected Patterns")
        pattern_header.setStyleSheet("font-weight: bold;")
        pattern_left_layout.addWidget(pattern_header)

        self.pattern_list = PatternListWidget()
        self.pattern_list.pattern_selected.connect(self._on_pattern_selected)
        pattern_left_layout.addWidget(self.pattern_list)

        pattern_layout.addWidget(pattern_left, 2)

        # Field mapping
        self.field_mapping = FieldMappingWidget()
        pattern_layout.addWidget(self.field_mapping, 1)

        self.tabs.addTab(pattern_tab, "Patterns & Field Mapping")

        # Tab 3: Analysis Summary
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        summary_layout.addWidget(self.summary_text)

        self.tabs.addTab(summary_tab, "Analysis Summary")

        # Tab 4: Generated Code
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)

        self.code_view = QPlainTextEdit()
        self.code_view.setFont(QFont("Consolas", 10))
        self.code_view.setReadOnly(True)
        code_layout.addWidget(self.code_view)

        self.tabs.addTab(code_tab, "Generated Code")

        layout.addWidget(self.tabs, 1)

        # Bottom: Template settings and actions
        bottom_layout = QHBoxLayout()

        # Settings
        settings_group = QGroupBox("Template Settings")
        settings_layout = QFormLayout(settings_group)

        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("e.g., supplier_name")
        self.template_name.textChanged.connect(self._update_code_preview)
        settings_layout.addRow("Template Name:", self.template_name)

        self.supplier_name = QLineEdit()
        self.supplier_name.setPlaceholderText("e.g., Acme Corporation Ltd.")
        self.supplier_name.textChanged.connect(self._update_code_preview)
        settings_layout.addRow("Supplier Name:", self.supplier_name)

        bottom_layout.addWidget(settings_group)

        bottom_layout.addStretch()

        # Action buttons
        self.btn_generate = QPushButton("Generate Template")
        self.btn_generate.setStyleSheet(
            "font-weight: bold; padding: 15px 30px; font-size: 14px; "
            "background-color: #3498db; color: white;"
        )
        self.btn_generate.setEnabled(False)
        self.btn_generate.clicked.connect(self._generate_template)
        bottom_layout.addWidget(self.btn_generate)

        self.btn_save = QPushButton("Save Template")
        self.btn_save.setStyleSheet(
            "font-weight: bold; padding: 15px 30px; font-size: 14px; "
            "background-color: #27ae60; color: white;"
        )
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_template)
        bottom_layout.addWidget(self.btn_save)

        layout.addLayout(bottom_layout)

        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Open a PDF to begin analysis")

    def _open_pdf(self):
        """Open and analyze a PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Invoice PDF", "", "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        self.current_pdf = file_path
        self.pdf_label.setText(f"Loading: {Path(file_path).name}")

        # Show progress
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.show()

        # Run analysis in background
        self.worker = AnalysisWorker(file_path)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.progress.connect(self._on_analysis_progress)
        self.worker.start()

    def _on_analysis_progress(self, message: str):
        """Handle progress update."""
        self.status_bar.showMessage(message)

    def _on_analysis_finished(self, analyzer: TokenTemplateAnalyzer):
        """Handle analysis completion."""
        self.analyzer = analyzer
        self.progress.hide()

        # Update UI
        self.pdf_label.setText(f"Loaded: {Path(self.current_pdf).name}")
        self.pdf_label.setStyleSheet("color: #27ae60; font-weight: bold;")

        # Populate tokenized view
        self.token_view.set_tokenized_lines(analyzer.tokenized_lines)

        # Populate pattern list
        self.pattern_list.set_patterns(analyzer.patterns)

        # Update summary
        self._update_summary()

        # Set supplier name if detected
        if analyzer.supplier_name:
            self.supplier_name.setText(analyzer.supplier_name)
            # Generate template name from supplier
            name = analyzer.supplier_name.lower()
            name = re.sub(r'[^a-z0-9]+', '_', name)
            name = re.sub(r'_+', '_', name).strip('_')[:30]
            self.template_name.setText(name)

        # Enable buttons
        self.btn_generate.setEnabled(True)

        self.status_bar.showMessage(
            f"Analysis complete: {len(analyzer.tokenized_lines)} lines, "
            f"{len(analyzer.patterns)} patterns detected"
        )

    def _on_analysis_error(self, error: str):
        """Handle analysis error."""
        self.progress.hide()
        self.pdf_label.setText("Error loading PDF")
        self.pdf_label.setStyleSheet("color: #e74c3c;")
        QMessageBox.critical(self, "Analysis Error", error)
        self.status_bar.showMessage("Analysis failed")

    def _on_token_clicked(self, token: Token, row: int, col: int):
        """Handle token click in the tokenized view."""
        self.status_bar.showMessage(
            f"Token: {token.value} | Type: {token.token_type.name} | "
            f"Line {row + 1}, Position {col + 1}"
        )

    def _on_pattern_selected(self, pattern: DetectedPattern):
        """Handle pattern selection."""
        self.field_mapping.set_pattern(pattern)
        self.status_bar.showMessage(
            f"Pattern selected: {pattern.simplified_signature} "
            f"({pattern.frequency} occurrences, {pattern.confidence:.0%} confidence)"
        )

    def _update_summary(self):
        """Update the analysis summary tab."""
        if not self.analyzer:
            return

        summary = self.analyzer.get_analysis_summary()

        text = "=" * 60 + "\n"
        text += "TOKEN-BASED ANALYSIS SUMMARY\n"
        text += "=" * 60 + "\n\n"

        text += f"Supplier: {summary['supplier_name'] or 'Unknown'}\n"
        text += f"Total lines: {summary['total_lines']}\n"
        text += f"Patterns found: {summary['patterns_found']}\n\n"

        if summary['header_fields']:
            text += "HEADER FIELDS:\n"
            for field, value in summary['header_fields'].items():
                text += f"  {field}: {value}\n"
            text += "\n"

        if summary['top_patterns']:
            text += "TOP PATTERNS (likely line items):\n\n"
            for i, p in enumerate(summary['top_patterns'], 1):
                text += f"Pattern {i}:\n"
                text += f"  Signature: {p['signature']}\n"
                text += f"  Frequency: {p['frequency']} lines\n"
                text += f"  Confidence: {p['confidence']:.0%}\n"
                text += f"  Sample: {p['sample']}\n"
                if p['field_mapping']:
                    text += f"  Auto-mapped: {p['field_mapping']}\n"
                text += "\n"

        self.summary_text.setText(text)

    def _update_code_preview(self):
        """Update the code preview."""
        if not self.analyzer:
            return

        template_name = self.template_name.text().strip() or "new_template"
        template_name = re.sub(r'[^a-z0-9_]', '', template_name.lower())

        # Update analyzer's supplier name
        if self.supplier_name.text().strip():
            self.analyzer.supplier_name = self.supplier_name.text().strip()

        try:
            code = self.analyzer.generate_template(template_name)
            self.code_view.setPlainText(code)
        except Exception as e:
            self.code_view.setPlainText(f"Error generating code: {e}")

    def _generate_template(self):
        """Generate template code."""
        if not self.analyzer:
            QMessageBox.warning(self, "No Analysis", "Please analyze a PDF first.")
            return

        template_name = self.template_name.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Missing Name", "Please enter a template name.")
            return

        template_name = re.sub(r'[^a-z0-9_]', '', template_name.lower())

        # Update analyzer's supplier name
        if self.supplier_name.text().strip():
            self.analyzer.supplier_name = self.supplier_name.text().strip()

        try:
            code = self.analyzer.generate_template(template_name)
            self.code_view.setPlainText(code)
            self.tabs.setCurrentIndex(3)  # Switch to code tab
            self.btn_save.setEnabled(True)
            self.status_bar.showMessage("Template code generated - review and save")
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def _save_template(self):
        """Save the generated template."""
        template_name = self.template_name.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Missing Name", "Please enter a template name.")
            return

        template_name = re.sub(r'[^a-z0-9_]', '', template_name.lower())
        code = self.code_view.toPlainText()

        if not code:
            QMessageBox.warning(self, "No Code", "Generate template code first.")
            return

        # Save to templates directory
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        file_path = templates_dir / f"{template_name}.py"

        if file_path.exists():
            result = QMessageBox.question(
                self, "File Exists",
                f"{template_name}.py already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return

        try:
            file_path.write_text(code)

            # Try to register in __init__.py
            self._register_template(templates_dir, template_name)

            QMessageBox.information(
                self, "Success",
                f"Template saved to:\n{file_path}\n\n"
                "Refresh templates in TariffMill to use it."
            )

            self.template_created.emit(template_name, str(file_path))
            self.status_bar.showMessage(f"Template saved: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _register_template(self, templates_dir: Path, template_name: str):
        """Try to register template in __init__.py."""
        init_file = templates_dir / "__init__.py"
        if not init_file.exists():
            return

        try:
            content = init_file.read_text()

            # Check if already registered
            if f"'{template_name}'" in content or f'"{template_name}"' in content:
                return

            # Generate class name
            class_name = ''.join(word.capitalize() for word in template_name.split('_')) + 'Template'

            # Add import
            import_line = f"from .{template_name} import {class_name}\n"

            lines = content.split('\n')
            last_import = 0
            for i, line in enumerate(lines):
                if line.startswith('from .') and 'import' in line:
                    last_import = i

            lines.insert(last_import + 1, import_line.rstrip())

            # Add to registry
            registry_entry = f"    '{template_name}': {class_name},"
            new_lines = []
            in_registry = False

            for line in lines:
                if 'TEMPLATE_REGISTRY' in line and '{' in line:
                    in_registry = True
                if in_registry and '}' in line:
                    new_lines.append(registry_entry)
                    in_registry = False
                new_lines.append(line)

            init_file.write_text('\n'.join(new_lines))

        except Exception:
            pass  # Registration is optional


def main():
    """Test the dialog standalone."""
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = TokenTemplateDialog()
    dialog.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()