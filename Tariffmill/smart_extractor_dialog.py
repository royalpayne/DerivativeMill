"""
Smart Extractor Dialog for TariffMill

PyQt5 UI for the SmartExtractor that provides an intuitive interface
for extracting line items from commercial invoices.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QGroupBox,
    QFormLayout, QLineEdit, QTextEdit, QSplitter, QHeaderView,
    QMessageBox, QProgressBar, QComboBox, QSpinBox, QCheckBox,
    QTabWidget, QWidget, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor

from pathlib import Path
import os

try:
    from smart_extractor import SmartExtractor, ExtractionResult, LineItem
except ImportError:
    from Tariffmill.smart_extractor import SmartExtractor, ExtractionResult, LineItem


class ExtractorThread(QThread):
    """Background thread for PDF extraction."""
    finished = pyqtSignal(object)  # ExtractionResult
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, pdf_path: str, pages: int = 5):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages

    def run(self):
        try:
            self.progress.emit("Extracting text from PDF...")
            extractor = SmartExtractor()
            result = extractor.extract_from_pdf(self.pdf_path, self.pages)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SmartExtractorDialog(QDialog):
    """
    Dialog for extracting line items from commercial invoices.

    Uses data shape recognition to find part numbers, quantities,
    and prices regardless of their position in the document.
    """

    # Signal emitted when extraction is complete with results
    extraction_complete = pyqtSignal(object)  # ExtractionResult

    def __init__(self, parent=None, pdf_path: str = None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.result = None
        self.extractor_thread = None

        self.setWindowTitle("Smart Invoice Extractor")
        self.setMinimumSize(1000, 700)
        self.setup_ui()

        # Auto-load if PDF path provided
        if pdf_path and Path(pdf_path).exists():
            self.pdf_path_edit.setText(pdf_path)
            self.extract_invoice()

    def setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("Smart Invoice Extractor")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        desc = QLabel(
            "Extracts line items by recognizing data shapes (part codes, quantities, prices) "
            "rather than fixed positions. Works with inconsistent invoice layouts."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; margin-bottom: 15px;")
        layout.addWidget(desc)

        # File selection
        file_group = QGroupBox("Invoice File")
        file_layout = QHBoxLayout()

        self.pdf_path_edit = QLineEdit()
        self.pdf_path_edit.setPlaceholderText("Select a PDF invoice to extract...")
        self.pdf_path_edit.setReadOnly(True)
        file_layout.addWidget(self.pdf_path_edit, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_pdf)
        file_layout.addWidget(browse_btn)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 50)
        self.pages_spin.setValue(5)
        self.pages_spin.setPrefix("Pages: ")
        self.pages_spin.setToolTip("Number of pages to process")
        file_layout.addWidget(self.pages_spin)

        extract_btn = QPushButton("Extract")
        extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        extract_btn.clicked.connect(self.extract_invoice)
        file_layout.addWidget(extract_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Results area with tabs
        self.tabs = QTabWidget()

        # Tab 1: Line Items Table
        items_widget = QWidget()
        items_layout = QVBoxLayout(items_widget)

        # Header info
        header_group = QGroupBox("Invoice Details")
        header_form = QFormLayout()

        self.supplier_label = QLabel("-")
        header_form.addRow("Supplier:", self.supplier_label)

        self.invoice_label = QLabel("-")
        header_form.addRow("Invoice #:", self.invoice_label)

        self.po_label = QLabel("-")
        header_form.addRow("PO Numbers:", self.po_label)

        self.items_count_label = QLabel("-")
        header_form.addRow("Items Found:", self.items_count_label)

        self.total_value_label = QLabel("-")
        self.total_value_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        header_form.addRow("Invoice Total:", self.total_value_label)

        header_group.setLayout(header_form)
        items_layout.addWidget(header_group)

        # Line items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Part Number", "Quantity", "Unit Price", "Total Price", "Description", "Confidence"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        items_layout.addWidget(self.items_table)

        self.tabs.addTab(items_widget, "Line Items")

        # Tab 2: Raw Text
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)

        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Courier New", 10))
        self.raw_text.setStyleSheet("background-color: #f8f9fa;")
        raw_layout.addWidget(self.raw_text)

        self.tabs.addTab(raw_widget, "Raw Text")

        layout.addWidget(self.tabs, stretch=1)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_btn)

        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.clicked.connect(self.export_csv)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def browse_pdf(self):
        """Open file dialog to select PDF."""
        start_dir = str(Path.home())
        if self.pdf_path_edit.text():
            start_dir = str(Path(self.pdf_path_edit.text()).parent)

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Invoice PDF",
            start_dir,
            "PDF Files (*.pdf);;All Files (*.*)"
        )

        if path:
            self.pdf_path_edit.setText(path)
            self.extract_invoice()

    def extract_invoice(self):
        """Start extraction in background thread."""
        pdf_path = self.pdf_path_edit.text()
        if not pdf_path or not Path(pdf_path).exists():
            QMessageBox.warning(self, "No File", "Please select a PDF file first.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFormat("Extracting...")

        # Clear previous results
        self.items_table.setRowCount(0)
        self.raw_text.clear()
        self.copy_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        # Start extraction thread
        self.extractor_thread = ExtractorThread(pdf_path, self.pages_spin.value())
        self.extractor_thread.finished.connect(self.on_extraction_complete)
        self.extractor_thread.error.connect(self.on_extraction_error)
        self.extractor_thread.progress.connect(self.on_progress)
        self.extractor_thread.start()

    def on_progress(self, message: str):
        """Update progress message."""
        self.progress_bar.setFormat(message)

    def on_extraction_complete(self, result: ExtractionResult):
        """Handle successful extraction."""
        self.progress_bar.setVisible(False)
        self.result = result

        # Update header info
        self.supplier_label.setText(result.supplier_name or "Unknown")
        self.invoice_label.setText(result.invoice_number or "Not found")
        self.po_label.setText(", ".join(result.po_numbers) if result.po_numbers else "None found")
        self.items_count_label.setText(str(len(result.line_items)))

        # Calculate and display invoice total
        total_value = 0.0
        for item in result.line_items:
            try:
                # Parse total_price, handling various formats
                price_str = item.total_price.replace('$', '').replace(',', '').strip()
                if price_str:
                    total_value += float(price_str)
            except (ValueError, AttributeError):
                pass
        self.total_value_label.setText(f"${total_value:,.2f}")

        # Populate table
        self.items_table.setRowCount(len(result.line_items))
        for row, item in enumerate(result.line_items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.part_number))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.quantity))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.unit_price))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.total_price))
            self.items_table.setItem(row, 4, QTableWidgetItem(item.description))

            # Confidence with color coding
            conf_item = QTableWidgetItem(f"{item.confidence:.0%}")
            if item.confidence >= 0.9:
                conf_item.setBackground(QColor("#d5f5e3"))  # Green
            elif item.confidence >= 0.7:
                conf_item.setBackground(QColor("#fef9e7"))  # Yellow
            else:
                conf_item.setBackground(QColor("#fadbd8"))  # Red
            self.items_table.setItem(row, 5, conf_item)

        # Resize columns
        self.items_table.resizeColumnsToContents()

        # Show raw text
        self.raw_text.setPlainText(result.raw_text)

        # Enable actions
        self.copy_btn.setEnabled(len(result.line_items) > 0)
        self.export_btn.setEnabled(len(result.line_items) > 0)

        # Emit signal
        self.extraction_complete.emit(result)

        # Show summary
        if len(result.line_items) == 0:
            QMessageBox.information(
                self, "No Items Found",
                "No line items were detected in this invoice.\n\n"
                "This may happen if:\n"
                "- The invoice format is not recognized\n"
                "- The PDF text extraction failed\n"
                "- The invoice uses an unusual layout"
            )

    def on_extraction_error(self, error: str):
        """Handle extraction error."""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(
            self, "Extraction Error",
            f"Failed to extract invoice data:\n\n{error}"
        )

    def copy_to_clipboard(self):
        """Copy line items to clipboard as tab-separated values."""
        if not self.result or not self.result.line_items:
            return

        lines = ["Part Number\tQuantity\tUnit Price\tTotal Price\tDescription"]
        for item in self.result.line_items:
            lines.append(f"{item.part_number}\t{item.quantity}\t{item.unit_price}\t{item.total_price}\t{item.description}")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)

        QMessageBox.information(
            self, "Copied",
            f"Copied {len(self.result.line_items)} line items to clipboard.\n\n"
            "You can paste this into Excel or other spreadsheet applications."
        )

    def export_csv(self):
        """Export line items to CSV file."""
        if not self.result or not self.result.line_items:
            return

        # Suggest filename based on invoice
        suggested = "extracted_items.csv"
        if self.result.invoice_number:
            suggested = f"invoice_{self.result.invoice_number}_items.csv"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV",
            str(Path.home() / suggested),
            "CSV Files (*.csv)"
        )

        if not path:
            return

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("Part Number,Quantity,Unit Price,Total Price,Description\n")
                for item in self.result.line_items:
                    # Escape quotes in description
                    desc = item.description.replace('"', '""')
                    f.write(f'"{item.part_number}","{item.quantity}","{item.unit_price}","{item.total_price}","{desc}"\n')

            QMessageBox.information(
                self, "Exported",
                f"Exported {len(self.result.line_items)} line items to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")


def main():
    """Test the dialog standalone."""
    import sys
    app = QApplication(sys.argv)
    dialog = SmartExtractorDialog()
    dialog.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
