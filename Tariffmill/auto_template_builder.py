"""
Auto Template Builder for OCRMill
Automatically analyzes PDF invoices and generates extraction templates with minimal user input.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QGroupBox, QFileDialog, QMessageBox,
    QProgressBar, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class PatternDetector:
    """Detects common invoice patterns without AI."""

    # Common invoice number patterns
    INVOICE_PATTERNS = [
        (r'(?:Proforma\s+)?[Ii]nvoice\s+(?:[Nn]o\.?|[Nn]umber|#)\s*:?\s*([A-Z0-9][\w\-/]+)', 'Invoice No'),
        (r'[Ii]nvoice\s*:?\s*#?\s*(\d+(?:/\d+)?)', 'Invoice'),
        (r'[Ff]actura\s*(?:[Nn]o\.?)?\s*:?\s*(\d+)', 'Factura'),
        (r'[Ii]nv\.?\s*#?\s*(\d+)', 'Inv'),
    ]

    # Common project/PO patterns
    PROJECT_PATTERNS = [
        (r'[Pp]roject\s*(?:[Nn]o\.?|[Nn]umber)?\s*:?\s*(US\d+[A-Z]\d+)', 'Project US'),
        (r'[Pp]roject\s*:?\s*(\w+[\-\d]+\w*)', 'Project'),
        (r'P\.?O\.?\s*(?:[Nn]o\.?|#)?\s*:?\s*(\w+)', 'PO'),
        (r'[Oo]rder\s*(?:[Nn]o\.?)?\s*:?\s*(\w+)', 'Order'),
    ]

    # Common line item patterns (part number, qty, price)
    LINE_PATTERNS = [
        # Part - Qty - Unit Price - Total
        r'^([A-Z0-9][\w\-\.]+)\s+(\d+(?:[,\.]\d+)?)\s+(?:pcs?|un|units?)?\s*[\$€]?([\d,]+\.?\d*)\s+[\$€]?([\d,]+\.?\d*)',
        # Part - Description - Qty - Price
        r'^([A-Z0-9][\w\-\.]+)\s+.{10,50}\s+(\d+(?:[,\.]\d+)?)\s+[\$€]?([\d,]+\.?\d*)',
        # Simple: Part - Qty - Price
        r'^([A-Z0-9][\w\-\.]{3,})\s+(\d+)\s+[\$€]?([\d,]+\.?\d*)',
    ]

    # Company identifier patterns
    COMPANY_INDICATORS = [
        r'(?:From|Supplier|Vendor|Seller)[\s:]+([A-Z][A-Za-z\s&\.]+(?:Ltd|LLC|Inc|Corp|GmbH|s\.r\.o\.|S\.A\.|SRL)?)',
        r'^([A-Z][A-Za-z\s&\.]+(?:Ltd|LLC|Inc|Corp|GmbH|s\.r\.o\.|S\.A\.|SRL))\s*$',
    ]

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split('\n')

    def detect_company_name(self) -> str:
        """Try to detect the company/supplier name."""
        for pattern in self.COMPANY_INDICATORS:
            match = re.search(pattern, self.text, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up common suffixes
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 3 and len(name) < 50:
                    return name
        return "Unknown Supplier"

    def detect_invoice_pattern(self) -> Tuple[str, str]:
        """Detect the invoice number pattern and a sample match."""
        for pattern, name in self.INVOICE_PATTERNS:
            match = re.search(pattern, self.text)
            if match:
                return pattern, match.group(1)
        return self.INVOICE_PATTERNS[0][0], ""

    def detect_project_pattern(self) -> Tuple[str, str]:
        """Detect the project/PO pattern and a sample match."""
        for pattern, name in self.PROJECT_PATTERNS:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return pattern, match.group(1)
        return self.PROJECT_PATTERNS[0][0], ""

    def detect_line_item_pattern(self) -> Tuple[str, List[str], List[Dict]]:
        """
        Detect the line item pattern.
        Returns: (pattern, column_names, sample_matches)
        """
        best_pattern = None
        best_matches = []
        best_columns = ['part_number', 'quantity', 'total_price']

        for pattern in self.LINE_PATTERNS:
            matches = []
            for line in self.lines:
                line = line.strip()
                if not line:
                    continue
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    matches.append({
                        'part_number': groups[0] if len(groups) > 0 else '',
                        'quantity': groups[1] if len(groups) > 1 else '',
                        'total_price': groups[-1] if len(groups) > 2 else groups[1] if len(groups) > 1 else '',
                    })

            if len(matches) > len(best_matches):
                best_pattern = pattern
                best_matches = matches

        if best_pattern:
            return best_pattern, best_columns, best_matches

        # Fall back to a generic pattern
        return self.LINE_PATTERNS[0], best_columns, []

    def detect_unique_identifiers(self) -> List[str]:
        """Find unique text that identifies this invoice format."""
        identifiers = []

        # Look for company name
        company = self.detect_company_name()
        if company and company != "Unknown Supplier":
            identifiers.append(company.lower())

        # Look for common headers/labels unique to this format
        unique_labels = []
        label_patterns = [
            r'^([A-Za-z\s]{5,30})\s*:',  # "Label:"
            r'^([A-Z][A-Za-z\s]{5,30})$',  # Header lines
        ]

        for pattern in label_patterns:
            for line in self.lines[:30]:  # Check first 30 lines
                match = re.match(pattern, line.strip())
                if match:
                    label = match.group(1).strip().lower()
                    if len(label) > 4 and label not in ['invoice', 'date', 'total', 'amount']:
                        unique_labels.append(label)

        # Add top 3 unique labels
        for label in unique_labels[:3]:
            if label not in identifiers:
                identifiers.append(label)

        return identifiers if identifiers else ['invoice']


class AutoAnalysisWorker(QThread):
    """Background worker for automatic analysis."""
    finished = pyqtSignal(dict)  # analysis results
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            self.progress.emit("Analyzing invoice structure...")
            detector = PatternDetector(self.text)

            self.progress.emit("Detecting company name...")
            company = detector.detect_company_name()

            self.progress.emit("Finding invoice number pattern...")
            inv_pattern, inv_sample = detector.detect_invoice_pattern()

            self.progress.emit("Finding project number pattern...")
            proj_pattern, proj_sample = detector.detect_project_pattern()

            self.progress.emit("Detecting line item patterns...")
            line_pattern, line_columns, line_samples = detector.detect_line_item_pattern()

            self.progress.emit("Identifying unique markers...")
            identifiers = detector.detect_unique_identifiers()

            results = {
                'company_name': company,
                'invoice_pattern': inv_pattern,
                'invoice_sample': inv_sample,
                'project_pattern': proj_pattern,
                'project_sample': proj_sample,
                'line_pattern': line_pattern,
                'line_columns': line_columns,
                'line_samples': line_samples,
                'identifiers': identifiers,
            }

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class AutoTemplateBuilderDialog(QDialog):
    """
    Automated Template Builder Dialog.
    Analyzes PDF and generates template with minimal user input.
    """

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto Template Builder")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setMinimumSize(800, 600)

        self.current_text = ""
        self.analysis_results = None
        self.worker = None

        self.setup_ui()

    def setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "<b>Automatic Template Builder</b><br><br>"
            "1. Load a sample PDF invoice<br>"
            "2. The system will automatically analyze it and detect patterns<br>"
            "3. Enter a template name and click Generate<br><br>"
            "No AI or external services required!"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # PDF selection
        file_group = QGroupBox("Step 1: Load Sample Invoice")
        file_layout = QHBoxLayout(file_group)
        self.pdf_path = QLineEdit()
        self.pdf_path.setPlaceholderText("Select a sample PDF invoice...")
        self.pdf_path.setReadOnly(True)
        browse_btn = QPushButton("Browse PDF...")
        browse_btn.clicked.connect(self.browse_pdf)
        file_layout.addWidget(self.pdf_path, 1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        # Analysis results
        results_group = QGroupBox("Step 2: Analysis Results")
        results_layout = QVBoxLayout(results_group)

        # Status
        self.status_label = QLabel("Load a PDF to begin analysis...")
        self.status_label.setStyleSheet("color: gray;")
        results_layout.addWidget(self.status_label)

        # Results display
        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # Template name
        name_group = QGroupBox("Step 3: Template Name")
        name_layout = QHBoxLayout(name_group)
        name_layout.addWidget(QLabel("Name:"))
        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("e.g., acme_corp (lowercase, underscores)")
        name_layout.addWidget(self.template_name, 1)
        layout.addWidget(name_group)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Buttons
        button_layout = QHBoxLayout()

        self.generate_btn = QPushButton("Generate Template")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_template)
        self.generate_btn.setStyleSheet("font-weight: bold; padding: 10px 20px;")

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.generate_btn)
        layout.addLayout(button_layout)

    def browse_pdf(self):
        """Browse for a PDF file."""
        if not HAS_PDFPLUMBER:
            QMessageBox.warning(
                self, "Missing Dependency",
                "pdfplumber is not installed.\n\nRun: pip install pdfplumber"
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sample Invoice PDF",
            "", "PDF Files (*.pdf)"
        )

        if file_path:
            self.pdf_path.setText(file_path)
            self.extract_and_analyze(file_path)

    def extract_and_analyze(self, pdf_path: str):
        """Extract text from PDF and run analysis."""
        try:
            self.status_label.setText("Extracting text from PDF...")
            self.status_label.setStyleSheet("color: blue;")
            QApplication.processEvents()

            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                self.current_text = text

                if not text.strip():
                    self.status_label.setText("No text could be extracted from PDF")
                    self.status_label.setStyleSheet("color: red;")
                    return

                # Run analysis
                self.run_analysis()

        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", f"Failed to process PDF: {e}")

    def run_analysis(self):
        """Run automatic pattern detection."""
        self.status_label.setText("Analyzing invoice patterns...")
        self.status_label.setStyleSheet("color: blue;")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.generate_btn.setEnabled(False)

        self.worker = AutoAnalysisWorker(self.current_text)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.start()

    def on_analysis_complete(self, results: dict):
        """Handle completed analysis."""
        self.analysis_results = results
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)

        self.status_label.setText("Analysis complete! Review results and generate template.")
        self.status_label.setStyleSheet("color: green;")

        # Display results
        output = []
        output.append(f"Company Detected: {results['company_name']}")
        output.append(f"")
        output.append(f"Invoice Pattern: {results['invoice_pattern'][:60]}...")
        output.append(f"  Sample Match: {results['invoice_sample']}")
        output.append(f"")
        output.append(f"Project Pattern: {results['project_pattern'][:60]}...")
        output.append(f"  Sample Match: {results['project_sample']}")
        output.append(f"")
        output.append(f"Line Items Found: {len(results['line_samples'])}")
        if results['line_samples']:
            output.append(f"  First item: {results['line_samples'][0]}")
        output.append(f"")
        output.append(f"Unique Identifiers: {', '.join(results['identifiers'])}")

        self.results_text.setPlainText('\n'.join(output))

        # Auto-suggest template name from company
        if results['company_name'] and results['company_name'] != "Unknown Supplier":
            name = results['company_name'].lower()
            name = re.sub(r'[^a-z0-9]+', '_', name)
            name = re.sub(r'_+', '_', name).strip('_')
            self.template_name.setText(name[:30])

    def on_analysis_error(self, error: str):
        """Handle analysis error."""
        self.progress.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red;")

    def generate_template(self):
        """Generate the template file."""
        if not self.analysis_results:
            QMessageBox.warning(self, "No Analysis", "Please load and analyze a PDF first.")
            return

        name = self.template_name.text().strip().lower()
        name = re.sub(r'[^a-z0-9_]', '', name)

        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid template name.")
            return

        # Generate class name
        class_name = ''.join(word.capitalize() for word in name.split('_')) + 'Template'

        # Generate template code
        code = self.generate_template_code(name, class_name)

        # Save template
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        file_path = templates_dir / f"{name}.py"

        if file_path.exists():
            result = QMessageBox.question(
                self, "File Exists",
                f"{name}.py already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return

        try:
            file_path.write_text(code)

            # Auto-register the template
            registered = self._auto_register_template(templates_dir, name, class_name)

            if registered:
                QMessageBox.information(
                    self, "Template Created",
                    f"Template '{name}' has been created and registered!\n\n"
                    f"Click 'Refresh' in the Templates tab to see it."
                )
            else:
                QMessageBox.information(
                    self, "Template Saved",
                    f"Template saved to:\n{file_path}\n\n"
                    f"Auto-registration failed. Please manually add to templates/__init__.py:\n\n"
                    f"from .{name} import {class_name}\n"
                    f"TEMPLATE_REGISTRY['{name}'] = {class_name}"
                )

            self.template_created.emit(name, str(file_path))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")

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

    def generate_template_code(self, name: str, class_name: str) -> str:
        """Generate the Python template code."""
        r = self.analysis_results

        # Escape patterns for Python string
        inv_pattern = r['invoice_pattern'].replace('\\', '\\\\').replace("'", "\\'")
        proj_pattern = r['project_pattern'].replace('\\', '\\\\').replace("'", "\\'")
        line_pattern = r['line_pattern'].replace('\\', '\\\\').replace("'", "\\'")

        # Build identifiers check
        identifier_checks = []
        for ident in r['identifiers'][:3]:
            ident_escaped = ident.replace("'", "\\'").lower()
            identifier_checks.append(f"'{ident_escaped}' in text.lower()")

        identifiers_code = ' and '.join(identifier_checks) if identifier_checks else 'True'

        code = f'''"""
{class_name} - Auto-generated invoice template
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {r['company_name']}
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class {class_name}(BaseTemplate):
    """
    Invoice template for {r['company_name']}.
    Auto-generated by TariffMill Auto Template Builder.
    """

    name = "{name.replace('_', ' ').title()}"
    description = "Invoice template for {r['company_name']}"
    client = "{r['company_name']}"
    version = "1.0.0"
    enabled = True

    extra_columns = ['unit_price', 'net_weight']

    def can_process(self, text: str) -> bool:
        """Check if this template can process the invoice."""
        return {identifiers_code}

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for this template."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        # Add confidence based on pattern matches
        if re.search(r'{inv_pattern}', text, re.IGNORECASE):
            score += 0.2
        if re.search(r'{proj_pattern}', text, re.IGNORECASE):
            score += 0.2
        return min(score, 1.0)

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number."""
        pattern = r'{inv_pattern}'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "UNKNOWN"

    def extract_project_number(self, text: str) -> str:
        """Extract project number."""
        pattern = r'{proj_pattern}'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
        return "UNKNOWN"

    def extract_manufacturer_name(self, text: str) -> str:
        """Extract manufacturer/supplier name."""
        return "{r['company_name']}"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        line_items = []
        seen_items = set()

        lines = text.split('\\n')

        # Primary line item pattern
        pattern = re.compile(r'{line_pattern}', re.IGNORECASE)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                groups = match.groups()

                part_number = groups[0] if len(groups) > 0 else ''
                quantity = groups[1] if len(groups) > 1 else '1'
                total_price = groups[-1] if len(groups) > 2 else groups[1] if len(groups) > 1 else '0'

                # Clean numeric values
                quantity = re.sub(r'[^\\d.]', '', str(quantity))
                total_price = re.sub(r'[^\\d.]', '', str(total_price))

                # Deduplication
                item_key = f"{{part_number}}_{{quantity}}_{{total_price}}"
                if item_key not in seen_items and part_number:
                    seen_items.add(item_key)

                    qty = float(quantity) if quantity else 1
                    price = float(total_price) if total_price else 0
                    unit_price = price / qty if qty > 0 else price

                    line_items.append({{
                        'part_number': part_number,
                        'quantity': quantity,
                        'total_price': total_price,
                        'unit_price': f"{{unit_price:.2f}}",
                    }})

        return line_items

    def is_packing_list(self, text: str) -> bool:
        """Check if document is a packing list."""
        text_lower = text.lower()
        if 'packing list' in text_lower or 'packing slip' in text_lower:
            if 'invoice' not in text_lower:
                return True
        return False
'''
        return code
