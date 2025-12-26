"""
Template Pattern Wizard
A step-by-step wizard for creating OCR invoice templates using a pattern library.
No AI required - uses pre-built patterns with live testing.
"""

import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout,
    QStackedWidget, QWidget, QSplitter, QMessageBox, QCheckBox,
    QPlainTextEdit, QHeaderView, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor


# =============================================================================
# PATTERN LIBRARY - Common regex patterns for invoice fields
# =============================================================================

PATTERN_LIBRARY = {
    'invoice_number': [
        {
            'name': 'Standard Invoice #',
            'pattern': r'[Ii]nvoice\s*#?\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches "Invoice #: ABC123" or "Invoice: 12345"',
            'example': 'Invoice #: INV-2024-001'
        },
        {
            'name': 'Invoice No.',
            'pattern': r'[Ii]nvoice\s+[Nn]o\.?\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches "Invoice No.: ABC123"',
            'example': 'Invoice No. 12345'
        },
        {
            'name': 'Proforma Invoice',
            'pattern': r'[Pp]roforma\s+[Ii]nvoice\s*#?\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches proforma invoice numbers',
            'example': 'Proforma Invoice: PI-2024-100'
        },
        {
            'name': 'Invoice Number (labeled)',
            'pattern': r'[Ii]nvoice\s+[Nn]umber\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches "Invoice Number: ABC123"',
            'example': 'Invoice Number: 2024/INV/001'
        },
        {
            'name': 'Inv #',
            'pattern': r'[Ii]nv\.?\s*#?\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches abbreviated "Inv #: 123"',
            'example': 'Inv# 12345'
        },
        {
            'name': 'Reference/Ref Number',
            'pattern': r'[Rr]ef(?:erence)?\s*(?:[Nn]o\.?|#)?\s*:?\s*([A-Z0-9][\w\-/]+)',
            'description': 'Matches reference numbers',
            'example': 'Ref No.: REF-001'
        },
    ],
    'project_number': [
        {
            'name': 'Project #',
            'pattern': r'[Pp]roject\s*#?\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Project #: PRJ-001"',
            'example': 'Project #: PRJ-2024-001'
        },
        {
            'name': 'Project Code',
            'pattern': r'[Pp]roject\s+[Cc]ode\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Project Code: ABC123"',
            'example': 'Project Code: PC-12345'
        },
        {
            'name': 'PO Number',
            'pattern': r'[Pp]\.?[Oo]\.?\s*(?:[Nn]o\.?|#)?\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches Purchase Order numbers',
            'example': 'PO# 45678'
        },
        {
            'name': 'Order Number',
            'pattern': r'[Oo]rder\s*(?:[Nn]o\.?|#)?\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Order No: 12345"',
            'example': 'Order No.: ORD-2024-001'
        },
        {
            'name': 'Job Number',
            'pattern': r'[Jj]ob\s*(?:[Nn]o\.?|#)?\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Job #: J-001"',
            'example': 'Job # J-2024-100'
        },
    ],
    'date': [
        {
            'name': 'MM/DD/YYYY',
            'pattern': r'(\d{1,2}/\d{1,2}/\d{2,4})',
            'description': 'US format: 12/31/2024',
            'example': '12/31/2024'
        },
        {
            'name': 'DD/MM/YYYY',
            'pattern': r'(\d{1,2}/\d{1,2}/\d{2,4})',
            'description': 'European format: 31/12/2024',
            'example': '31/12/2024'
        },
        {
            'name': 'YYYY-MM-DD (ISO)',
            'pattern': r'(\d{4}-\d{2}-\d{2})',
            'description': 'ISO format: 2024-12-31',
            'example': '2024-12-31'
        },
        {
            'name': 'Month DD, YYYY',
            'pattern': r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            'description': 'Written: December 31, 2024',
            'example': 'December 31, 2024'
        },
        {
            'name': 'DD Month YYYY',
            'pattern': r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            'description': 'Written: 31 December 2024',
            'example': '31 December 2024'
        },
        {
            'name': 'DD.MM.YYYY',
            'pattern': r'(\d{1,2}\.\d{1,2}\.\d{2,4})',
            'description': 'Dot format: 31.12.2024',
            'example': '31.12.2024'
        },
        {
            'name': 'Date with label',
            'pattern': r'[Dd]ate\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            'description': 'Matches "Date: 12/31/2024"',
            'example': 'Date: 12/31/2024'
        },
    ],
    'amount': [
        {
            'name': 'USD Amount ($)',
            'pattern': r'\$\s*([\d,]+\.?\d*)',
            'description': 'Matches $1,234.56',
            'example': '$1,234.56'
        },
        {
            'name': 'EUR Amount (€)',
            'pattern': r'€\s*([\d,]+\.?\d*)',
            'description': 'Matches €1.234,56',
            'example': '€1,234.56'
        },
        {
            'name': 'GBP Amount (£)',
            'pattern': r'£\s*([\d,]+\.?\d*)',
            'description': 'Matches £1,234.56',
            'example': '£1,234.56'
        },
        {
            'name': 'Currency code prefix',
            'pattern': r'([A-Z]{3})\s*([\d,]+\.?\d*)',
            'description': 'Matches USD 1,234.56',
            'example': 'USD 1,234.56'
        },
        {
            'name': 'Plain number with decimals',
            'pattern': r'([\d,]+\.\d{2})',
            'description': 'Matches 1,234.56 (no currency)',
            'example': '1,234.56'
        },
        {
            'name': 'Total Amount labeled',
            'pattern': r'[Tt]otal\s*:?\s*\$?\s*([\d,]+\.?\d*)',
            'description': 'Matches "Total: $1,234.56"',
            'example': 'Total: $1,234.56'
        },
    ],
    'quantity': [
        {
            'name': 'Integer quantity',
            'pattern': r'(\d+)\s*(?:pcs?|pieces?|units?|ea\.?)?',
            'description': 'Matches "10 pcs" or "10"',
            'example': '10 pcs'
        },
        {
            'name': 'Decimal quantity',
            'pattern': r'(\d+(?:\.\d+)?)',
            'description': 'Matches "10.5"',
            'example': '10.5'
        },
        {
            'name': 'Qty labeled',
            'pattern': r'[Qq]ty\.?\s*:?\s*(\d+(?:\.\d+)?)',
            'description': 'Matches "Qty: 10"',
            'example': 'Qty: 10'
        },
    ],
    'part_number': [
        {
            'name': 'Alphanumeric part #',
            'pattern': r'([A-Z]{2,}[\-]?\d+[\w\-]*)',
            'description': 'Matches "ABC-12345" or "PN123"',
            'example': 'ABC-12345'
        },
        {
            'name': 'Part # labeled',
            'pattern': r'[Pp]art\s*#?\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Part #: ABC123"',
            'example': 'Part #: PN-001'
        },
        {
            'name': 'SKU',
            'pattern': r'[Ss][Kk][Uu]\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "SKU: ABC123"',
            'example': 'SKU: SKU-12345'
        },
        {
            'name': 'Item/Product Code',
            'pattern': r'(?:[Ii]tem|[Pp]roduct)\s*[Cc]ode\s*:?\s*([A-Z0-9][\w\-]+)',
            'description': 'Matches "Item Code: IC001"',
            'example': 'Item Code: IC-001'
        },
    ],
    'weight': [
        {
            'name': 'Kilograms (kg)',
            'pattern': r'([\d,]+\.?\d*)\s*[Kk][Gg]\.?',
            'description': 'Matches "10.5 kg"',
            'example': '10.5 kg'
        },
        {
            'name': 'Pounds (lbs)',
            'pattern': r'([\d,]+\.?\d*)\s*(?:[Ll][Bb][Ss]?\.?|[Pp]ounds?)',
            'description': 'Matches "23.1 lbs"',
            'example': '23.1 lbs'
        },
        {
            'name': 'Grams (g)',
            'pattern': r'([\d,]+\.?\d*)\s*[Gg](?:rams?)?',
            'description': 'Matches "500 g"',
            'example': '500 g'
        },
        {
            'name': 'Net Weight labeled',
            'pattern': r'[Nn]et\s+[Ww]eight\s*:?\s*([\d,]+\.?\d*)\s*(?:[Kk][Gg]|[Ll][Bb][Ss]?)?',
            'description': 'Matches "Net Weight: 10.5 kg"',
            'example': 'Net Weight: 10.5 kg'
        },
    ],
}

# Line item pattern templates
LINE_ITEM_PATTERNS = [
    {
        'name': 'Part - Description - Qty - Price - Total',
        'pattern': r'^([A-Z0-9][\w\-]+)\s+(.{10,50})\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)',
        'columns': ['part_number', 'description', 'quantity', 'unit_price', 'total_price'],
        'description': 'Standard 5-column format'
    },
    {
        'name': 'Part - Qty - Price - Total',
        'pattern': r'^([A-Z0-9][\w\-]+)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)',
        'columns': ['part_number', 'quantity', 'unit_price', 'total_price'],
        'description': '4-column without description'
    },
    {
        'name': 'Description - Qty - Price',
        'pattern': r'^(.{10,60})\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)',
        'columns': ['description', 'quantity', 'total_price'],
        'description': 'Simple 3-column format'
    },
    {
        'name': 'Part - Description - Qty - Total',
        'pattern': r'^([A-Z0-9][\w\-]+)\s+(.{10,50})\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)',
        'columns': ['part_number', 'description', 'quantity', 'total_price'],
        'description': '4-column without unit price'
    },
    {
        'name': 'Custom (define your own)',
        'pattern': '',
        'columns': [],
        'description': 'Write your own pattern'
    },
]


class PatternTestWidget(QWidget):
    """Widget for testing regex patterns against sample text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Pattern input
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter regex pattern...")
        self.pattern_input.textChanged.connect(self.test_pattern)
        pattern_layout.addWidget(self.pattern_input)
        layout.addLayout(pattern_layout)

        # Sample text
        layout.addWidget(QLabel("Sample Text:"))
        self.sample_text = QPlainTextEdit()
        self.sample_text.setMaximumHeight(100)
        self.sample_text.textChanged.connect(self.test_pattern)
        layout.addWidget(self.sample_text)

        # Results
        layout.addWidget(QLabel("Matches:"))
        self.results = QListWidget()
        self.results.setMaximumHeight(80)
        layout.addWidget(self.results)

    def set_pattern(self, pattern: str):
        self.pattern_input.setText(pattern)

    def set_sample_text(self, text: str):
        self.sample_text.setPlainText(text)

    def get_pattern(self) -> str:
        return self.pattern_input.text()

    def test_pattern(self):
        self.results.clear()
        pattern = self.pattern_input.text()
        text = self.sample_text.toPlainText()

        if not pattern or not text:
            return

        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = compiled.findall(text)

            if matches:
                for match in matches[:10]:
                    if isinstance(match, tuple):
                        display = " | ".join(str(m) for m in match)
                    else:
                        display = str(match)
                    item = QListWidgetItem(f"✓ {display}")
                    item.setForeground(QColor("#27ae60"))
                    self.results.addItem(item)
            else:
                item = QListWidgetItem("No matches found")
                item.setForeground(QColor("#e74c3c"))
                self.results.addItem(item)

        except re.error as e:
            item = QListWidgetItem(f"Regex error: {e}")
            item.setForeground(QColor("#e74c3c"))
            self.results.addItem(item)


class TemplateWizard(QDialog):
    """Step-by-step wizard for creating invoice templates."""

    template_created = pyqtSignal(str, str)  # template_name, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Pattern Wizard")
        self.setMinimumSize(900, 700)

        # Template data
        self.template_data = {
            'name': '',
            'company': '',
            'indicators': [],
            'patterns': {},
            'line_item_pattern': '',
            'line_item_columns': [],
            'extra_columns': [],
        }
        self.sample_text = ""

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Template Pattern Wizard")
        title.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Create invoice templates step-by-step using pre-built patterns")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # Stacked widget for wizard steps
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Create wizard pages
        self.create_step1_basics()
        self.create_step2_sample()
        self.create_step3_patterns()
        self.create_step4_line_items()
        self.create_step5_review()

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.btn_back = QPushButton("← Back")
        self.btn_back.clicked.connect(self.go_back)
        self.btn_back.setEnabled(False)
        nav_layout.addWidget(self.btn_back)

        nav_layout.addStretch()

        self.step_label = QLabel("Step 1 of 5")
        nav_layout.addWidget(self.step_label)

        nav_layout.addStretch()

        self.btn_next = QPushButton("Next →")
        self.btn_next.clicked.connect(self.go_next)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)

    def create_step1_basics(self):
        """Step 1: Basic template information."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>Step 1: Basic Information</h3>"))
        layout.addWidget(QLabel("Enter the basic details for your template."))

        form = QFormLayout()

        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("e.g., acme_corp")
        form.addRow("Template Name:", self.template_name)

        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("e.g., Acme Corporation")
        form.addRow("Company/Supplier:", self.company_name)

        layout.addLayout(form)

        # Indicators section
        layout.addWidget(QLabel("<b>Invoice Indicators</b>"))
        layout.addWidget(QLabel("Enter unique text that identifies this invoice format (one per line):"))

        self.indicators_input = QPlainTextEdit()
        self.indicators_input.setPlaceholderText("e.g.,\nAcme Corporation\nInvoice Date:\nPayment Terms:")
        self.indicators_input.setMaximumHeight(120)
        layout.addWidget(self.indicators_input)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_step2_sample(self):
        """Step 2: Load sample invoice text."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>Step 2: Sample Invoice</h3>"))
        layout.addWidget(QLabel("Paste or load a sample invoice text for pattern testing."))

        btn_layout = QHBoxLayout()
        btn_load = QPushButton("Load from File...")
        btn_load.clicked.connect(self.load_sample_file)
        btn_layout.addWidget(btn_load)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.sample_input = QPlainTextEdit()
        self.sample_input.setPlaceholderText("Paste invoice text here...")
        layout.addWidget(self.sample_input, 1)

        self.stack.addWidget(page)

    def create_step3_patterns(self):
        """Step 3: Select extraction patterns."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>Step 3: Extraction Patterns</h3>"))
        layout.addWidget(QLabel("Select patterns for each field. Test them against your sample."))

        splitter = QSplitter(Qt.Horizontal)

        # Left: Pattern selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Field selector
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel("Field:"))
        self.field_selector = QComboBox()
        self.field_selector.addItems(['invoice_number', 'project_number', 'date', 'amount', 'part_number', 'quantity', 'weight'])
        self.field_selector.currentTextChanged.connect(self.on_field_changed)
        field_layout.addWidget(self.field_selector)
        left_layout.addLayout(field_layout)

        # Pattern list
        left_layout.addWidget(QLabel("Available Patterns:"))
        self.pattern_list = QListWidget()
        self.pattern_list.itemClicked.connect(self.on_pattern_selected)
        left_layout.addWidget(self.pattern_list)

        # Selected patterns table
        left_layout.addWidget(QLabel("Selected Patterns:"))
        self.selected_patterns = QTableWidget()
        self.selected_patterns.setColumnCount(2)
        self.selected_patterns.setHorizontalHeaderLabels(['Field', 'Pattern'])
        self.selected_patterns.horizontalHeader().setStretchLastSection(True)
        self.selected_patterns.setMaximumHeight(150)
        left_layout.addWidget(self.selected_patterns)

        btn_add = QPushButton("Add Selected Pattern")
        btn_add.clicked.connect(self.add_selected_pattern)
        left_layout.addWidget(btn_add)

        splitter.addWidget(left_widget)

        # Right: Pattern tester
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("<b>Pattern Tester</b>"))
        self.pattern_tester = PatternTestWidget()
        right_layout.addWidget(self.pattern_tester)

        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])

        layout.addWidget(splitter, 1)

        self.stack.addWidget(page)

        # Initialize pattern list
        self.on_field_changed('invoice_number')

    def create_step4_line_items(self):
        """Step 4: Line item pattern."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>Step 4: Line Item Pattern</h3>"))
        layout.addWidget(QLabel("Select or create a pattern for extracting line items."))

        # Template selector
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.line_template = QComboBox()
        for tpl in LINE_ITEM_PATTERNS:
            self.line_template.addItem(tpl['name'])
        self.line_template.currentIndexChanged.connect(self.on_line_template_changed)
        template_layout.addWidget(self.line_template)
        layout.addLayout(template_layout)

        # Description
        self.line_template_desc = QLabel()
        self.line_template_desc.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.line_template_desc)

        # Pattern editor
        layout.addWidget(QLabel("Pattern:"))
        self.line_pattern_edit = QLineEdit()
        self.line_pattern_edit.textChanged.connect(self.test_line_pattern)
        layout.addWidget(self.line_pattern_edit)

        # Columns
        columns_layout = QHBoxLayout()
        columns_layout.addWidget(QLabel("Columns:"))
        self.line_columns_edit = QLineEdit()
        self.line_columns_edit.setPlaceholderText("part_number, description, quantity, total_price")
        columns_layout.addWidget(self.line_columns_edit)
        layout.addLayout(columns_layout)

        # Extra columns
        extra_layout = QHBoxLayout()
        extra_layout.addWidget(QLabel("Extra columns for output:"))
        self.extra_columns = QLineEdit()
        self.extra_columns.setPlaceholderText("e.g., unit_price, net_weight")
        extra_layout.addWidget(self.extra_columns)
        layout.addLayout(extra_layout)

        # Test results
        layout.addWidget(QLabel("Line Item Matches:"))
        self.line_results = QPlainTextEdit()
        self.line_results.setReadOnly(True)
        self.line_results.setMaximumHeight(200)
        layout.addWidget(self.line_results)

        layout.addStretch()

        self.stack.addWidget(page)

        # Initialize
        self.on_line_template_changed(0)

    def create_step5_review(self):
        """Step 5: Review and save."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>Step 5: Review & Save</h3>"))
        layout.addWidget(QLabel("Review your template configuration and save."))

        # Summary
        self.review_text = QPlainTextEdit()
        self.review_text.setReadOnly(True)
        layout.addWidget(self.review_text, 1)

        # Save button
        btn_save = QPushButton("Save Template")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        btn_save.clicked.connect(self.save_template)
        layout.addWidget(btn_save)

        self.stack.addWidget(page)

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def go_back(self):
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.update_navigation()

    def go_next(self):
        current = self.stack.currentIndex()

        # Validate current step
        if not self.validate_step(current):
            return

        if current < self.stack.count() - 1:
            # Prepare next step
            self.prepare_step(current + 1)
            self.stack.setCurrentIndex(current + 1)
            self.update_navigation()

    def update_navigation(self):
        current = self.stack.currentIndex()
        total = self.stack.count()

        self.btn_back.setEnabled(current > 0)
        self.btn_next.setText("Finish" if current == total - 1 else "Next →")
        self.step_label.setText(f"Step {current + 1} of {total}")

    def validate_step(self, step: int) -> bool:
        if step == 0:  # Basics
            name = self.template_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Validation", "Please enter a template name.")
                return False
            # Validate name format
            name = name.lower().replace(' ', '_').replace('-', '_')
            if not name.replace('_', '').isalnum():
                QMessageBox.warning(self, "Validation", "Template name should only contain letters, numbers, and underscores.")
                return False
            self.template_data['name'] = name
            self.template_data['company'] = self.company_name.text().strip() or "Unknown Supplier"
            self.template_data['indicators'] = [
                line.strip() for line in self.indicators_input.toPlainText().split('\n')
                if line.strip()
            ]

        elif step == 1:  # Sample
            self.sample_text = self.sample_input.toPlainText()
            if not self.sample_text:
                QMessageBox.warning(self, "Validation", "Please provide sample invoice text for pattern testing.")
                return False

        elif step == 2:  # Patterns
            if self.selected_patterns.rowCount() == 0:
                reply = QMessageBox.question(
                    self, "No Patterns",
                    "You haven't selected any extraction patterns. Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return False

            # Collect patterns
            self.template_data['patterns'] = {}
            for row in range(self.selected_patterns.rowCount()):
                field = self.selected_patterns.item(row, 0).text()
                pattern = self.selected_patterns.item(row, 1).text()
                self.template_data['patterns'][field] = pattern

        elif step == 3:  # Line items
            self.template_data['line_item_pattern'] = self.line_pattern_edit.text()
            columns_text = self.line_columns_edit.text()
            self.template_data['line_item_columns'] = [
                c.strip() for c in columns_text.split(',') if c.strip()
            ]
            extra_text = self.extra_columns.text()
            self.template_data['extra_columns'] = [
                c.strip() for c in extra_text.split(',') if c.strip()
            ]

        return True

    def prepare_step(self, step: int):
        if step == 2:  # Patterns - load sample text into tester
            self.pattern_tester.set_sample_text(self.sample_text)

        elif step == 4:  # Review
            self.update_review()

    # -------------------------------------------------------------------------
    # Pattern Selection
    # -------------------------------------------------------------------------

    def on_field_changed(self, field: str):
        self.pattern_list.clear()
        patterns = PATTERN_LIBRARY.get(field, [])

        for p in patterns:
            item = QListWidgetItem(f"{p['name']}\n{p['description']}")
            item.setData(Qt.UserRole, p)
            self.pattern_list.addItem(item)

    def on_pattern_selected(self, item: QListWidgetItem):
        pattern_data = item.data(Qt.UserRole)
        if pattern_data:
            self.pattern_tester.set_pattern(pattern_data['pattern'])

    def add_selected_pattern(self):
        field = self.field_selector.currentText()
        pattern = self.pattern_tester.get_pattern()

        if not pattern:
            QMessageBox.warning(self, "No Pattern", "Please select or enter a pattern first.")
            return

        # Check if field already exists
        for row in range(self.selected_patterns.rowCount()):
            if self.selected_patterns.item(row, 0).text() == field:
                self.selected_patterns.item(row, 1).setText(pattern)
                return

        # Add new row
        row = self.selected_patterns.rowCount()
        self.selected_patterns.insertRow(row)
        self.selected_patterns.setItem(row, 0, QTableWidgetItem(field))
        self.selected_patterns.setItem(row, 1, QTableWidgetItem(pattern))

    # -------------------------------------------------------------------------
    # Line Item Pattern
    # -------------------------------------------------------------------------

    def on_line_template_changed(self, index: int):
        template = LINE_ITEM_PATTERNS[index]
        self.line_template_desc.setText(template['description'])
        self.line_pattern_edit.setText(template['pattern'])
        self.line_columns_edit.setText(', '.join(template['columns']))
        self.test_line_pattern()

    def test_line_pattern(self):
        pattern = self.line_pattern_edit.text()
        if not pattern or not self.sample_text:
            self.line_results.setPlainText("Enter a pattern and load sample text to test.")
            return

        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = compiled.findall(self.sample_text)

            if matches:
                result_lines = [f"Found {len(matches)} matches:\n"]
                for i, match in enumerate(matches[:10], 1):
                    if isinstance(match, tuple):
                        result_lines.append(f"{i}. {' | '.join(str(m) for m in match)}")
                    else:
                        result_lines.append(f"{i}. {match}")
                self.line_results.setPlainText('\n'.join(result_lines))
            else:
                self.line_results.setPlainText("No matches found. Try adjusting the pattern.")

        except re.error as e:
            self.line_results.setPlainText(f"Regex error: {e}")

    # -------------------------------------------------------------------------
    # File Loading
    # -------------------------------------------------------------------------

    def load_sample_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Sample Invoice",
            "", "Text files (*.txt);;All files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.sample_input.setPlainText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load file: {e}")

    # -------------------------------------------------------------------------
    # Review & Save
    # -------------------------------------------------------------------------

    def update_review(self):
        lines = [
            f"Template Name: {self.template_data['name']}",
            f"Company: {self.template_data['company']}",
            "",
            "Invoice Indicators:",
        ]
        for ind in self.template_data['indicators']:
            lines.append(f"  - {ind}")

        lines.extend(["", "Extraction Patterns:"])
        for field, pattern in self.template_data['patterns'].items():
            lines.append(f"  {field}: {pattern}")

        lines.extend([
            "",
            f"Line Item Pattern: {self.template_data['line_item_pattern']}",
            f"Columns: {', '.join(self.template_data['line_item_columns'])}",
            f"Extra Columns: {', '.join(self.template_data['extra_columns'])}",
        ])

        self.review_text.setPlainText('\n'.join(lines))

    def save_template(self):
        """Generate and save the template file."""
        try:
            # Generate template code
            code = self.generate_template_code()

            # Determine save path
            templates_dir = Path(__file__).parent / "templates"
            if not templates_dir.exists():
                templates_dir = Path.cwd() / "templates"

            file_name = f"{self.template_data['name']}.py"
            file_path = templates_dir / file_name

            # Check if exists
            if file_path.exists():
                reply = QMessageBox.question(
                    self, "File Exists",
                    f"Template '{file_name}' already exists. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # Save file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            QMessageBox.information(
                self, "Success",
                f"Template saved to:\n{file_path}\n\n"
                "Restart the application or refresh templates to use it."
            )

            self.template_created.emit(self.template_data['name'], str(file_path))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")

    def generate_template_code(self) -> str:
        """Generate Python code for the template."""
        data = self.template_data
        class_name = ''.join(word.capitalize() for word in data['name'].split('_')) + 'Template'

        # Build indicators check
        indicators = data['indicators']
        if indicators:
            checks = ' and '.join(f"'{ind.lower()}' in text.lower()" for ind in indicators[:3])
        else:
            checks = "True  # No indicators defined"

        # Build patterns
        pattern_methods = []
        for field, pattern in data['patterns'].items():
            method_name = f"extract_{field}"
            escaped_pattern = pattern.replace("'", "\\'")
            pattern_methods.append(f'''
    def {method_name}(self, text: str) -> str:
        """Extract {field.replace('_', ' ')}."""
        pattern = r'{escaped_pattern}'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "UNKNOWN"''')

        # Line items
        line_pattern = data['line_item_pattern'].replace("'", "\\'")
        line_columns = data['line_item_columns']
        extra_columns = data['extra_columns']

        # Generate column assignments
        col_assignments = []
        for i, col in enumerate(line_columns):
            col_assignments.append(f"                        '{col}': groups[{i}] if len(groups) > {i} else '',")

        code = f'''"""
{class_name} - Invoice template
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {data['company']}
Created with Template Pattern Wizard
"""

import re
from typing import List, Dict
from .base_template import BaseTemplate


class {class_name}(BaseTemplate):
    """
    Invoice template for {data['company']}.
    """

    name = "{data['name'].replace('_', ' ').title()}"
    description = "Invoice template for {data['company']}"
    client = "{data['company']}"
    version = "1.0.0"
    enabled = True

    extra_columns = {extra_columns!r}

    def can_process(self, text: str) -> bool:
        """Check if this template can process the invoice."""
        return {checks}

    def get_confidence_score(self, text: str) -> float:
        """Return confidence score for this template."""
        if not self.can_process(text):
            return 0.0

        score = 0.5
        text_lower = text.lower()

        # Add confidence based on indicators
        indicators = {[ind.lower() for ind in indicators]!r}
        for indicator in indicators:
            if indicator in text_lower:
                score += 0.1

        return min(score, 1.0)
{"".join(pattern_methods)}

    def extract_manufacturer_name(self, text: str) -> str:
        """Extract manufacturer/supplier name."""
        return "{data['company']}"

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from invoice."""
        line_items = []
        seen_items = set()

        lines = text.split('\\n')
        pattern = re.compile(r'{line_pattern}', re.IGNORECASE)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                groups = match.groups()

                try:
                    item = {{
{chr(10).join(col_assignments)}
                    }}

                    # Create dedup key
                    item_key = "_".join(str(v) for v in item.values())
                    if item_key not in seen_items:
                        seen_items.add(item_key)
                        line_items.append(item)

                except (IndexError, ValueError):
                    continue

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


# For testing
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    wizard = TemplateWizard()
    wizard.show()
    sys.exit(app.exec_())
