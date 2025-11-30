#!/usr/bin/env python3
# ==============================================================================
# APPLICATION CONFIGURATION - CHANGE THESE TO RENAME THE APPLICATION
# ==============================================================================
APP_NAME = "Derivative Mill"
VERSION = "v1.08"
DB_NAME = "derivativemill.db"  # Database filename (will be created in Resources folder)

# ==============================================================================
"""
{APP_NAME} {VERSION} - FINAL RELEASE
100% COMPLIANT WITH AUGUST 18, 2025 FEDERAL REGISTER
Primary Articles: Hard-coded exactly as published
Derivative Articles: tariff_232 table + official derivative subheadings
Exact 8-digit match only
Steel to "08", Flag blank
Aluminum to "07", Flag "Y"
New Design: Settings gear, Folder Locations in dialog, Saved Profiles on Process tab
Full app | ZERO ERRORS | PROFESSIONAL | FINAL
"""


import sys
import os
import json
import time
import shutil
import traceback
import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
import sqlite3
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer, QSize, QEventLoop, QRect
from PyQt5.QtGui import QColor, QFont, QDrag, QKeySequence, QIcon, QPixmap, QPainter, QDoubleValidator, QCursor, QPen, QTextCursor, QTextCharFormat
from PyQt5.QtSvg import QSvgRenderer
from openpyxl.styles import Font as ExcelFont, Alignment
import tempfile

# OCR support for scanned invoices
try:
    from ocr import is_scanned_pdf, extract_from_scanned_invoice
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ----------------------------------------------------------------------
# Global Logger
# ----------------------------------------------------------------------
class ErrorLogger:
    def __init__(self):
        self.logs = []
    def log(self, level, message):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{ts}] {level.upper():7} | {message}"
        self.logs.append(entry)
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
        print(entry)
    def info(self, msg): self.log("info", msg)
    def debug(self, msg): self.log("debug", msg)
    def warning(self, msg): self.log("warning", msg)
    def error(self, msg):
        self.log("ERROR", msg)
        if hasattr(sys, 'exc_info') and sys.exc_info()[0]:
            tb = traceback.format_exc()
            for line in tb.splitlines():
                self.log("TRACE", line)
    def success(self, msg): self.log("success", msg)
    def get_logs(self): return "\n".join(self.logs)

logger = ErrorLogger()

# ----------------------------------------------------------------------
# Global Paths
# ----------------------------------------------------------------------
# Handle PyInstaller frozen executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys.executable).parent
    # For bundled resources in onefile mode, use _MEIPASS temp directory
    if hasattr(sys, '_MEIPASS'):
        TEMP_RESOURCES_DIR = Path(sys._MEIPASS) / "Resources"
    else:
        TEMP_RESOURCES_DIR = BASE_DIR / "Resources"
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    TEMP_RESOURCES_DIR = BASE_DIR / "Resources"

RESOURCES_DIR = BASE_DIR / "Resources"
INPUT_DIR = BASE_DIR / "Input"
OUTPUT_DIR = BASE_DIR / "Output"
PROCESSED_DIR = INPUT_DIR / "Processed"
OUTPUT_PROCESSED_DIR = OUTPUT_DIR / "Processed"
PROCESSED_PDF_DIR = BASE_DIR / "ProcessedPDFs"
MAPPING_FILE = BASE_DIR / "column_mapping.json"
SHIPMENT_MAPPING_FILE = BASE_DIR / "shipment_mapping.json"

for p in (RESOURCES_DIR, INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, OUTPUT_PROCESSED_DIR, PROCESSED_PDF_DIR):
    p.mkdir(exist_ok=True)

DB_PATH = RESOURCES_DIR / DB_NAME

def get_232_info(hts_code):
    if not hts_code:
        return None, "", ""
    hts_clean = str(hts_code).replace(".", "").strip().upper()
    hts_8 = hts_clean[:8]
    hts_10 = hts_clean[:10]
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT material, declaration_required FROM tariff_232 WHERE hts_code = ?", (hts_10,))
        row = c.fetchone()
        if not row and len(hts_clean) >= 8:
            c.execute("SELECT material, declaration_required FROM tariff_232 WHERE hts_code = ?", (hts_8,))
            row = c.fetchone()
        conn.close()
        if row:
            material = row[0]
            dec_code = row[1] if row[1] else ""
            dec_type = dec_code.split(" - ")[0] if " - " in dec_code else dec_code
            smelt_flag = "Y" if material in ["Aluminum", "Wood", "Copper"] else ""
            return material, dec_type, smelt_flag
    except Exception as e:
        logger.error(f"Error querying tariff_232 for HTS {hts_clean}: {e}")
        pass
    if hts_clean.startswith(('7601','7604','7605','7606','7607','7608','7609')) or hts_clean.startswith('76169951'):
        return "Aluminum", "07", "Y"
    if hts_clean.startswith((""" '7206','7207','7208','7209','7210','7211','7212','7213','7214','7215',
                            '7216','7217','7218','7219','7220','7221','7222','7223','7224','7225',
                            '7226','7227','7228','7229','7301','7302','7303','7304','7305','7306',
                            '7307','7308','7309','7310','7311','7312','7313','7314','7315','7316',
                            '7317','7318','7320','7321','7322','7323','7324','7325','7326' """)):
        return "Steel", "08", ""
    if hts_8 in ('76141050', '76149020', '76149040', '76149050'):
        return "Aluminum", "07", "Y"
    return None, "", ""

# ----------------------------------------------------------------------
# Database Init
# ----------------------------------------------------------------------
def init_database():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS parts_master (
            part_number TEXT PRIMARY KEY, description TEXT, hts_code TEXT, country_origin TEXT,
            mid TEXT, client_code TEXT, steel_ratio REAL DEFAULT 1.0, non_steel_ratio REAL DEFAULT 0.0, last_updated TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS tariff_232 (
            hts_code TEXT PRIMARY KEY,
            material TEXT,
            classification TEXT,
            chapter TEXT,
            chapter_description TEXT,
            declaration_required TEXT,
            notes TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sec_232_actions (
            tariff_no TEXT PRIMARY KEY,
            action TEXT,
            description TEXT,
            advalorem_rate TEXT,
            effective_date TEXT,
            expiration_date TEXT,
            specific_rate TEXT,
            additional_declaration TEXT,
            note TEXT,
            link TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS mapping_profiles (
            profile_name TEXT PRIMARY KEY, mapping_json TEXT, created_date TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY, value TEXT
        )""")

        # Migration: Add client_code column to parts_master if it doesn't exist
        try:
            c.execute("PRAGMA table_info(parts_master)")
            columns = [col[1] for col in c.fetchall()]
            if 'client_code' not in columns:
                c.execute("ALTER TABLE parts_master ADD COLUMN client_code TEXT")
                logger.info("Added client_code column to parts_master")
        except Exception as e:
            logger.warning(f"Failed to check/add client_code column: {e}")

        conn.commit()
        conn.close()
        logger.success("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

init_database()

# ----------------------------------------------------------------------
# Drag & Drop Components
# ----------------------------------------------------------------------
class DraggableLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("background:#6b6b6b;border:2px solid #aaa;border-radius:8px;padding:12px;font-weight:bold;color:#ffffff;cursor:hand;")
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(QCursor(Qt.OpenHandCursor))  # Show hand cursor
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.text())
            drag.setMimeData(mime)
            pixmap = QPixmap(self.size())
            pixmap.fill(Qt.transparent)
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction)
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            # This helps with drag detection
            pass

class DropTarget(QLabel):
    dropped = pyqtSignal(str, str)
    def __init__(self, field_key, field_name, drop_label=None):
        # Use custom drop_label if provided, otherwise use field_name
        label_text = drop_label if drop_label else field_name
        super().__init__(f"Drop {label_text} here")
        self.field_key = field_key
        # Unified style, proportional sizing
        self.setStyleSheet("font-size: 12pt; padding: 8px; background: #f8f8f8; border: 2px solid #bbb; border-radius: 8px; color: #222;")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.column_name = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    def dragEnterEvent(self, e): 
        if e.mimeData().hasText(): e.accept()
    def dropEvent(self, e):
        col = e.mimeData().text()
        self.column_name = col
        self.setText(f"{self.field_key}\n<- {col}")
        self.setProperty("occupied", True)
        self.style().unpolish(self); self.style().polish(self)
        self.dropped.emit(self.field_key, col)
        e.accept()

class ForceEditableLineEdit(QLineEdit):
    """QLineEdit that forces itself to remain editable no matter what"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_editable = True
        # Set properties immediately
        self.setReadOnly(False)
        self.setEnabled(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def setReadOnly(self, readonly):
        """Override setReadOnly to always stay editable"""
        if self._force_editable and readonly:
            return  # Ignore attempts to make readonly
        super().setReadOnly(readonly)

    def setEnabled(self, enabled):
        """Override setEnabled to always stay enabled"""
        if self._force_editable and not enabled:
            return  # Ignore attempts to disable
        super().setEnabled(enabled)

    def mousePressEvent(self, event):
        """Force editable on mouse click"""
        super(ForceEditableLineEdit, self).setReadOnly(False)
        super(ForceEditableLineEdit, self).setEnabled(True)
        self.setFocus()
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        """Accept all focus events and force editable state"""
        super(ForceEditableLineEdit, self).setReadOnly(False)
        super(ForceEditableLineEdit, self).setEnabled(True)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        """Force editable before processing any key event"""
        from PyQt5.QtCore import Qt

        # For Tab keys, manually move focus to next/previous widget
        if event.key() == Qt.Key_Tab:
            # Move focus to next widget in tab order
            self.focusNextChild()
            event.accept()
            return
        elif event.key() == Qt.Key_Backtab:
            # Move focus to previous widget in tab order
            self.focusPreviousChild()
            event.accept()
            return

        super(ForceEditableLineEdit, self).setReadOnly(False)
        super(ForceEditableLineEdit, self).setEnabled(True)
        super().keyPressEvent(event)

class AutoSelectListWidget(QListWidget):
    """QListWidget that auto-selects first item when receiving focus via Tab"""
    def focusInEvent(self, event):
        """Select first item when receiving focus if nothing is selected"""
        super().focusInEvent(event)
        # Only auto-select if no item is currently selected and list has items
        if not self.currentItem() and self.count() > 0:
            self.setCurrentRow(0)

class FileDropZone(QLabel):
    """Drag-and-drop zone for importing CSV/Excel files"""
    file_dropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setText("📁 Drag & Drop CSV/Excel File Here\n\nor click to browse")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(120)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.update_style(False)
        
    def update_style(self, hover=False):
        if hover:
            self.setStyleSheet("""
                QLabel {
                    background: #e3f2fd;
                    border: 3px dashed #2196F3;
                    border-radius: 10px;
                    font-size: 14pt;
                    font-weight: bold;
                    color: #1976D2;
                    padding: 20px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background: #f5f5f5;
                    border: 3px dashed #999;
                    border-radius: 10px;
                    font-size: 14pt;
                    font-weight: bold;
                    color: #666;
                    padding: 20px;
                }
            """)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.update_style(True)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        self.update_style(False)
    
    def dropEvent(self, event):
        self.update_style(False)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.csv', '.xlsx', '.xls')):
                self.file_dropped.emit(file_path)
                event.accept()
            else:
                QMessageBox.warning(self, "Invalid File", 
                    "Please drop a CSV or Excel file (.csv, .xlsx, .xls)")
                event.ignore()
    
    def mousePressEvent(self, event):
        # Clicking opens file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV/Excel File", str(INPUT_DIR), 
            "CSV/Excel Files (*.csv *.xlsx *.xls)"
        )
        if file_path:
            self.file_dropped.emit(file_path)



# ----------------------------------------------------------------------
# VISUAL PDF PATTERN TRAINER WITH DRAWING CANVAS
# ----------------------------------------------------------------------
class HighlightableTextEdit(QPlainTextEdit):
    """Custom text edit that allows highlighting text and naming selections"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.highlights = {}  # Maps text position to (name, color)
        self.selected_start = -1
        self.selected_end = -1

    def contextMenuEvent(self, event):
        """Show context menu on right-click with highlight option"""
        cursor = self.cursorForPosition(event.pos())

        # Check if user has text selected
        if not self.textCursor().hasSelection():
            return

        menu = QMenu(self)
        highlight_action = menu.addAction("Name This Selection...")
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == highlight_action:
            self.highlight_selection()

    def highlight_selection(self):
        """Prompt user to name the selected text and highlight it"""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            QMessageBox.warning(self, "No Selection", "Please select text first")
            return

        selected_text = cursor.selectedText()

        # Get name for this selection
        dialog = ElementNameDialog(
            title="Name Data Element",
            prompt=f"Name this element:\n\n'{selected_text}'",
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            name = dialog.get_text()
            if name:
                # Get selection range
                start = cursor.selectionStart()
                end = cursor.selectionEnd()

                # Store highlight info
                self.highlights[(start, end)] = name

                # Apply highlighting
                self.apply_highlights()

    def apply_highlights(self):
        """Apply all highlights to the document"""
        # Get text format for highlighting
        colors = [Qt.red, Qt.blue, Qt.green, Qt.magenta, Qt.yellow, Qt.cyan]

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.setTextCursor(cursor)

        # Clear previous formatting
        fmt = QTextCharFormat()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)

        # Apply new highlights
        for (start, end), name in self.highlights.items():
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, end - start)

            # Create format with background color
            fmt = QTextCharFormat()
            color_idx = hash(name) % len(colors)
            fmt.setBackground(QColor(colors[color_idx]))
            fmt.setForeground(Qt.black)
            fmt.setFontWeight(QFont.Bold)

            cursor.setCharFormat(fmt)

    def get_named_selections(self):
        """Return dictionary of named text selections"""
        result = {}
        text = self.toPlainText()
        for (start, end), name in self.highlights.items():
            if start < len(text) and end <= len(text):
                selected = text[start:end]
                if name not in result:
                    result[name] = []
                result[name].append(selected)
        return result


class ElementNameDialog(QDialog):
    """Custom dialog for naming elements with proper text visibility"""

    def __init__(self, title="Name Element", prompt="Enter name:", default_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Label with explicit styling for dark mode
        label = QLabel(prompt)
        label.setStyleSheet("""
            QLabel {
                color: black;
                font-weight: bold;
            }
        """)
        layout.addWidget(label)

        # Text input
        self.text_input = QLineEdit()
        self.text_input.setText(default_text)
        self.text_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                color: black;
                selection-background-color: #0078d7;
                selection-color: white;
            }
        """)
        layout.addWidget(self.text_input)

        # Buttons with explicit styling for dark mode
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        button_style = """
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d9;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
        ok_btn.setStyleSheet(button_style)
        cancel_btn.setStyleSheet(button_style)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_text(self):
        """Return the entered text"""
        return self.text_input.text()


class PDFDrawingCanvas(QLabel):
    """Custom label that allows drawing rectangles and naming elements"""

    def __init__(self, pixmap):
        super().__init__()
        self.base_pixmap = pixmap
        self.current_pixmap = pixmap.copy()
        self.setPixmap(self.current_pixmap)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #ccc; background: white;")

        # Drawing state
        self.drawing = False
        self.start_point = None
        self.current_rect = None
        self.annotations = []  # List of (rect, name) tuples
        self.colors = [Qt.red, Qt.blue, Qt.green, Qt.magenta, Qt.yellow, Qt.cyan]
        self.color_index = 0

        # Editing state
        self.editing_index = None
        self.editing_edge = None  # Which edge is being dragged: 'top', 'bottom', 'left', 'right', 'move'
        self.EDGE_SIZE = 8  # Size of edge handles

    def get_annotation_at_point(self, point):
        """Find annotation box at given point (returns topmost/last one if overlapping)"""
        # Iterate in reverse to get the topmost (most recently drawn) annotation
        for idx in range(len(self.annotations) - 1, -1, -1):
            rect, name = self.annotations[idx]
            if rect.contains(point):
                return idx
        return None

    def get_edge_at_point(self, rect, point):
        """Determine which edge of rectangle is at point (for resizing)"""
        edges = {
            'top': QRect(rect.x(), rect.y() - self.EDGE_SIZE, rect.width(), self.EDGE_SIZE * 2),
            'bottom': QRect(rect.x(), rect.bottom() - self.EDGE_SIZE, rect.width(), self.EDGE_SIZE * 2),
            'left': QRect(rect.x() - self.EDGE_SIZE, rect.y(), self.EDGE_SIZE * 2, rect.height()),
            'right': QRect(rect.right() - self.EDGE_SIZE, rect.y(), self.EDGE_SIZE * 2, rect.height()),
        }

        for edge_name, edge_rect in edges.items():
            if edge_rect.contains(point):
                return edge_name

        # Check if in center for moving
        inner_rect = rect.adjusted(self.EDGE_SIZE, self.EDGE_SIZE, -self.EDGE_SIZE, -self.EDGE_SIZE)
        if inner_rect.contains(point):
            return 'move'

        return None

    def mousePressEvent(self, event):
        """Start drawing or editing"""
        point = event.pos()

        # Check if clicking on existing annotation
        idx = self.get_annotation_at_point(point)
        if idx is not None:
            rect, name = self.annotations[idx]
            edge = self.get_edge_at_point(rect, point)
            if edge:
                self.editing_index = idx
                self.editing_edge = edge
                self.start_point = point
                return

        # Otherwise, start drawing new rectangle
        self.drawing = True
        self.start_point = point
        self.current_rect = None

    def mouseMoveEvent(self, event):
        """Update rectangle while dragging or resize, and update cursor"""
        point = event.pos()

        # Editing mode
        if self.editing_index is not None and self.editing_edge:
            rect, name = self.annotations[self.editing_index]
            delta_x = point.x() - self.start_point.x()
            delta_y = point.y() - self.start_point.y()

            if self.editing_edge == 'top':
                rect.setTop(rect.top() + delta_y)
                self.setCursor(Qt.SizeVerCursor)
            elif self.editing_edge == 'bottom':
                rect.setBottom(rect.bottom() + delta_y)
                self.setCursor(Qt.SizeVerCursor)
            elif self.editing_edge == 'left':
                rect.setLeft(rect.left() + delta_x)
                self.setCursor(Qt.SizeHorCursor)
            elif self.editing_edge == 'right':
                rect.setRight(rect.right() + delta_x)
                self.setCursor(Qt.SizeHorCursor)
            elif self.editing_edge == 'move':
                rect.translate(delta_x, delta_y)
                self.setCursor(Qt.OpenHandCursor)

            # Ensure minimum size
            if rect.width() < 20:
                rect.setWidth(20)
            if rect.height() < 20:
                rect.setHeight(20)

            self.annotations[self.editing_index] = (rect, name)
            self.start_point = point
            self.redraw()
            return

        # Drawing mode
        if self.drawing and self.start_point:
            self.current_rect = QRect(self.start_point, event.pos()).normalized()
            self.redraw()
            return

        # Hover feedback: show cursor when hovering over resizable areas
        idx = self.get_annotation_at_point(point)
        if idx is not None:
            rect, name = self.annotations[idx]
            edge = self.get_edge_at_point(rect, point)
            if edge == 'top' or edge == 'bottom':
                self.setCursor(Qt.SizeVerCursor)
            elif edge == 'left' or edge == 'right':
                self.setCursor(Qt.SizeHorCursor)
            elif edge == 'move':
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """Finish drawing and ask for element name"""
        if self.editing_index is not None:
            self.editing_index = None
            self.editing_edge = None
            return

        if self.drawing and self.current_rect and self.current_rect.width() > 10 and self.current_rect.height() > 10:
            # Ask user to name this element
            dialog = ElementNameDialog(
                title="Name Element",
                prompt="Enter name for this data element:\n(e.g., Part Number, Price, Qty)",
                parent=self
            )
            if dialog.exec_() == QDialog.Accepted:
                name = dialog.get_text()
                if name:
                    self.annotations.append((self.current_rect, name))
                    self.redraw()

        self.drawing = False
        self.current_rect = None

    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        point = event.pos()
        idx = self.get_annotation_at_point(point)

        if idx is None:
            return

        # Create context menu
        menu = QMenu(self)

        edit_action = menu.addAction("Edit Box Dimensions...")
        rename_action = menu.addAction("Rename Element...")
        delete_action = menu.addAction("Delete Element")

        action = menu.exec_(self.mapToGlobal(point))

        if action == edit_action:
            self.show_edit_box_dialog(idx)
        elif action == rename_action:
            self.show_rename_dialog(idx)
        elif action == delete_action:
            self.delete_annotation(idx)

    def show_edit_box_dialog(self, idx):
        """Show dialog to edit box dimensions precisely"""
        rect, name = self.annotations[idx]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Box - {name}")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        # Create form layout
        form = QFormLayout()

        x_input = QSpinBox()
        x_input.setRange(-5000, 5000)
        x_input.setValue(rect.x())
        form.addRow("X Position:", x_input)

        y_input = QSpinBox()
        y_input.setRange(-5000, 5000)
        y_input.setValue(rect.y())
        form.addRow("Y Position:", y_input)

        width_input = QSpinBox()
        width_input.setRange(20, 5000)
        width_input.setValue(rect.width())
        form.addRow("Width:", width_input)

        height_input = QSpinBox()
        height_input.setRange(20, 5000)
        height_input.setValue(rect.height())
        form.addRow("Height:", height_input)

        layout.addLayout(form)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            new_rect = QRect(x_input.value(), y_input.value(), width_input.value(), height_input.value())
            self.annotations[idx] = (new_rect, name)
            self.redraw()

    def show_rename_dialog(self, idx):
        """Show dialog to rename an element"""
        rect, old_name = self.annotations[idx]

        dialog = ElementNameDialog(
            title="Rename Element",
            prompt="Enter new name:",
            default_text=old_name,
            parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            name = dialog.get_text()
            if name:
                self.annotations[idx] = (rect, name)
                self.redraw()

    def delete_annotation(self, idx):
        """Delete an annotation"""
        del self.annotations[idx]
        self.redraw()

    def redraw(self):
        """Redraw pixmap with annotations and current rectangle"""
        self.current_pixmap = self.base_pixmap.copy()

        painter = QPainter(self.current_pixmap)
        painter.setFont(QFont("Arial", 8, QFont.Bold))

        # Draw existing annotations
        for idx, (rect, name) in enumerate(self.annotations):
            color = self.colors[idx % len(self.colors)]
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw label with solid background and black text for contrast
            label_bg = QColor(color)
            label_bg.setAlpha(220)  # Make slightly transparent
            painter.fillRect(rect.x(), rect.y() - 20, len(name) * 7 + 6, 18, label_bg)
            painter.setPen(QPen(Qt.black, 1))
            painter.drawText(rect.x() + 3, rect.y() - 5, name)

        # Draw current rectangle being drawn
        if self.current_rect:
            pen = QPen(Qt.gray, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.current_rect)

        painter.end()
        self.setPixmap(self.current_pixmap)

    def get_annotations(self):
        """Return list of annotated elements"""
        return self.annotations

    def clear_annotations(self):
        """Clear all annotations"""
        self.annotations = []
        self.redraw()


class PDFPatternTrainerDialog(QDialog):
    """Interactive PDF viewer for visual OCR pattern training with drawing"""

    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.setWindowTitle(f"Visual Pattern Trainer - {Path(pdf_path).name}")
        self.resize(1500, 1000)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Draw boxes around data elements and name them.\n"
            "Click and drag to create rectangles. You'll be asked to name each element."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background: #f0f0f0; padding: 10px; border-radius: 3px;")
        layout.addWidget(instructions)

        # PDF display with drawing capability
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]

                # Render page to image with HIGH quality (300 DPI)
                import io
                from PIL import Image
                pil_image = page.to_image(resolution=300).original

                # Convert to QPixmap
                image_data = io.BytesIO()
                pil_image.save(image_data, format='PNG', quality=95)
                image_data.seek(0)

                self.pixmap = QPixmap()
                self.pixmap.loadFromData(image_data.read())
                self.pixmap = self.pixmap.scaledToWidth(1400, Qt.SmoothTransformation)

                # Create drawing canvas
                self.canvas = PDFDrawingCanvas(self.pixmap)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load PDF: {str(e)}")
            self.canvas = PDFDrawingCanvas(QPixmap())

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

        # Annotations display
        annotations_group = QGroupBox("Marked Elements")
        annotations_layout = QVBoxLayout()

        self.annotations_list = QListWidget()
        self.annotations_list.setMaximumHeight(120)
        annotations_layout.addWidget(self.annotations_list)

        # Buttons for annotations
        annotation_btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setStyleSheet(self.get_button_style("info"))
        btn_refresh.clicked.connect(self.refresh_annotations_list)
        annotation_btn_layout.addWidget(btn_refresh)

        btn_clear = QPushButton("Clear All")
        btn_clear.setStyleSheet(self.get_button_style("danger"))
        btn_clear.clicked.connect(self.clear_all_annotations)
        annotation_btn_layout.addWidget(btn_clear)

        annotations_layout.addLayout(annotation_btn_layout)
        annotations_group.setLayout(annotations_layout)
        layout.addWidget(annotations_group)

        # Instructions
        pattern_instructions = QLabel(
            "<b>How to use:</b><br>"
            "1. Draw a box around a data element (e.g., one part number)<br>"
            "2. Enter a name for it (e.g., 'Part Number', 'Price', 'Qty')<br>"
            "3. Box will appear with color-coded label<br>"
            "4. Repeat for other data elements<br>"
            "5. Use the marked elements to understand invoice format<br>"
            "6. Create regex patterns based on what you learn"
        )
        pattern_instructions.setWordWrap(True)
        pattern_instructions.setStyleSheet("background: #fffbea; padding: 10px; border-radius: 3px; font-size: 9pt;")
        layout.addWidget(pattern_instructions)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        # Initialize annotations list
        self.refresh_annotations_list()

    def get_button_style(self, style_type):
        """Return button style (simplified)"""
        styles = {
            "info": "background: #2196F3; color: white; padding: 5px; border-radius: 3px;",
            "danger": "background: #f44336; color: white; padding: 5px; border-radius: 3px;",
        }
        return styles.get(style_type, "")

    def refresh_annotations_list(self):
        """Update the list of marked elements"""
        self.annotations_list.clear()
        for idx, (rect, name) in enumerate(self.canvas.get_annotations(), 1):
            self.annotations_list.addItem(f"{idx}. {name} (at x={rect.x()}, y={rect.y()})")

    def clear_all_annotations(self):
        """Clear all annotations"""
        reply = QMessageBox.question(
            self, "Clear All",
            "Remove all marked elements?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear_annotations()
            self.refresh_annotations_list()

# ----------------------------------------------------------------------
# MAIN APPLICATION — FINAL DESIGN
# ----------------------------------------------------------------------
from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgRenderer

class DerivativeMill(QMainWindow):
    def eventFilter(self, obj, event):
        """Application-level event filter - intercepts ALL events before any widget processing"""
        from PyQt5.QtCore import QEvent, Qt

        # Intercept ALL keyboard events at application level
        if event.type() == QEvent.KeyPress:
            focused_widget = QApplication.focusWidget()

            # CRITICAL FIX: Forward ALL keyboard events (including Tab) to ci_input/wt_input
            # The ForceEditableLineEdit.keyPressEvent will handle Tab specially with focusNextChild()
            if hasattr(self, 'ci_input') and hasattr(self, 'wt_input'):
                if focused_widget in [self.ci_input, self.wt_input]:
                    # Only process once per event - when it comes from QWindow
                    if obj.__class__.__name__ == 'QWindow':
                        # Manually send the event to the focused widget (including Tab keys)
                        QApplication.sendEvent(focused_widget, event)
                        return True  # We handled it, block further propagation

        return False  # Let ALL other events continue normally

    def setup_tab_by_index(self, index):
        """Initialize tab by index using existing setup methods."""
        tab_setup_methods = {
            1: self.setup_shipment_mapping_tab,
            2: self.setup_import_tab,
            3: self.setup_master_tab,
            4: self.setup_log_tab,
            5: self.setup_config_tab,
            6: self.setup_actions_tab,
            7: self.setup_guide_tab
        }
        if index in tab_setup_methods:
            tab_setup_methods[index]()
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        # Compact default size - fully scalable with no minimum constraint
        self.setGeometry(50, 50, 1200, 700)

        # Install application-level event filter to intercept ALL keyboard events
        QApplication.instance().installEventFilter(self)

        # Track processed events to prevent duplicates
        self._processed_events = set()
        
        # Set window icon (use TEMP_RESOURCES_DIR for bundled resources)
        icon_path = TEMP_RESOURCES_DIR / "banner_bg.png"
        if not icon_path.exists():
            icon_path = TEMP_RESOURCES_DIR / "icon.ico"
        if not icon_path.exists():
            icon_path = TEMP_RESOURCES_DIR / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.current_csv = None
        self.shipment_mapping = {}
        self.selected_mid = ""
        self.current_worker = None
        self.missing_df = None
        self.csv_total_value = 0.0
        self.last_processed_df = None
        self.last_output_filename = None
        self.shipment_targets = {}  # Prevent attribute error before tab setup

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Modern header with watermill logo on left, text in center
        header_container = QWidget()
        header_container.setStyleSheet("background: transparent; border: none;")
        header_container.setFixedHeight(48)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(20, 6, 20, 6)
        header_layout.setSpacing(10)

        # Watermill logo on left (larger and more opaque)
        bg_path = TEMP_RESOURCES_DIR / "banner_bg.png"
        fixed_header_height = 48
        if bg_path.exists():
            bg_label = QLabel()
            pixmap = QPixmap(str(bg_path))
            scaled_pixmap = pixmap.scaled(fixed_header_height, fixed_header_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter_pixmap = QPixmap(scaled_pixmap.size())
            painter_pixmap.fill(Qt.transparent)
            from PyQt5.QtGui import QPainter
            painter = QPainter(painter_pixmap)
            painter.setOpacity(0.85)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()
            bg_label.setPixmap(painter_pixmap)
            bg_label.setStyleSheet("background: transparent;")
            bg_label.setFixedSize(fixed_header_height, fixed_header_height)
            self.header_bg_label = bg_label
        else:
            self.header_bg_label = None

        # App name centered
        app_name = QLabel(f"{APP_NAME}")
        app_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        app_name.setFixedHeight(fixed_header_height)
        # Set font color based on theme
        dark_mode_teal_color = "#42A0BD"  # Matches enabled Process Invoice button color in dark mode
        light_mode_color = "#555555"  # Original color for light mode
        color = dark_mode_teal_color if hasattr(self, 'current_theme') and self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"] else light_mode_color
        app_name.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {color};
            font-family: 'Impact', 'Arial Black', sans-serif;
            padding: 0px;
        """)
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(3, 3)
        app_name.setGraphicsEffect(shadow)
        # Add logo and title directly to the QHBoxLayout, both vertically centered, same height
        if self.header_bg_label:
            header_layout.addWidget(self.header_bg_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(app_name, 1, Qt.AlignVCenter)


        layout.addWidget(header_container)



        # Add a native menu bar with a Settings action (gear icon)
        menubar = QMenuBar(self)
        settings_menu = menubar.addMenu("Settings")
        # Use a standard gear icon from QStyle
        gear_icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        settings_action = QAction(gear_icon, "Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)
        layout.setMenuBar(menubar)
        self.settings_action = settings_action

        # Top status bar removed per user request
        # Create a dummy status object that ignores all calls
        class DummyStatus:
            def setText(self, text): pass
            def setStyleSheet(self, style): pass
            def setAlignment(self, align): pass
        self.status = DummyStatus()

        # Add spacing between header and tabs
        layout.addSpacing(20)

        self.tabs = QTabWidget()
        self.tab_process = QWidget()
        self.tab_shipment_map = QWidget()
        self.tab_import = QWidget()
        self.tab_master = QWidget()
        self.tab_log = QWidget()
        self.tab_config = QWidget()
        self.tab_actions = QWidget()
        self.tab_ocr_training = QWidget()
        self.tab_guide = QWidget()
        self.tabs.addTab(self.tab_process, "Process Shipment")
        self.tabs.addTab(self.tab_shipment_map, "Invoice Mapping Profiles")
        self.tabs.addTab(self.tab_import, "Parts Import")
        self.tabs.addTab(self.tab_master, "Parts View")
        self.tabs.addTab(self.tab_log, "Log View")
        self.tabs.addTab(self.tab_config, "Customs Config")
        self.tabs.addTab(self.tab_actions, "Section 232 Actions")
        self.tabs.addTab(self.tab_ocr_training, "OCR Training")
        self.tabs.addTab(self.tab_guide, "User Guide")
        
        # Only tabs (no settings icon here)
        tabs_container = QWidget()
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(10)
        tabs_layout.addWidget(self.tabs)
        layout.addWidget(tabs_container)
        
        # Bottom status bar with export progress indicator
        bottom_bar = QWidget()
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(10, 3, 10, 3)
        bottom_bar_layout.setSpacing(10)
        
        self.bottom_status = QLabel("Ready")
        bottom_bar_layout.addWidget(self.bottom_status, 1)
        
        # Export progress indicator (hidden by default)
        self.export_progress_widget = QWidget()
        export_progress_layout = QHBoxLayout(self.export_progress_widget)
        export_progress_layout.setContentsMargins(0, 0, 0, 0)
        export_progress_layout.setSpacing(5)
        
        self.export_status_label = QLabel("")
        self.export_status_label.setStyleSheet("font-size: 8pt; color: #666666;")
        export_progress_layout.addWidget(self.export_status_label)
        
        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setMaximum(100)
        self.export_progress_bar.setFixedWidth(120)
        self.export_progress_bar.setFixedHeight(14)
        self.export_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #b0b0b0;
                border-radius: 3px;
                background-color: #f5f5f5;
                text-align: center;
                font-size: 7pt;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 2px;
            }
        """)
        export_progress_layout.addWidget(self.export_progress_bar)
        
        bottom_bar_layout.addWidget(self.export_progress_widget)
        self.export_progress_widget.hide()
        
        self.bottom_bar = bottom_bar  # Store reference for theme updates
        bottom_bar.setFixedHeight(20)
        layout.addWidget(bottom_bar)

        # Track which tabs have been initialized (lazy loading for performance)
        self.tabs_initialized = set()
        

        # Only set up the first tab immediately for faster startup
        self.setup_process_tab()
        self.tabs_initialized.add(0)

        # Connect to tab change signal for lazy initialization
        self.tabs.currentChanged.connect(self.on_tab_changed)



        logger.success(f"{APP_NAME} {VERSION} GUI ready")

    # Removed deferred_initialization; tabs are now lazily loaded only when selected
    
    def initialize_data(self, splash=None, progress_callback=None):
        """Initialize database and load all data before showing window"""
        steps = [
            ("Loading configuration...", self.load_config_paths),
            ("Applying theme...", self.apply_saved_theme),
            ("Applying font size...", self.apply_saved_font_size),
            ("Loading MIDs...", self.load_available_mids),
            ("Loading profiles...", self.load_mapping_profiles),
            # Removed output file scanning on startup
            ("Scanning input files...", self.refresh_input_files),
            ("Starting auto-refresh...", self.setup_auto_refresh),
            ("Finalizing...", self.update_status_bar_styles),
        ]
        
        total_steps = len(steps)
        for i, (message, func) in enumerate(steps):
            if splash:
                splash.setText(f"{message}\nPlease wait...")
            if progress_callback:
                progress_callback(int((i / total_steps) * 100))
            QApplication.processEvents()
            
            try:
                func()
            except Exception as e:
                logger.error(f"Error during {message}: {e}")
        
        if progress_callback:
            progress_callback(100)

        # Ensure input fields are enabled after all initialization
        if hasattr(self, '_enable_input_fields'):
            self._enable_input_fields()

        logger.success(f"{APP_NAME} {VERSION} loaded successfully")
    
    def on_tab_changed(self, index):
        """Initialize tabs lazily when they are first accessed"""
        if index in self.tabs_initialized:
            return

        # Map tab index to setup method
        tab_setup_methods = {
            1: self.setup_shipment_mapping_tab,
            2: self.setup_import_tab,
            3: self.setup_master_tab,
            4: self.setup_log_tab,
            5: self.setup_config_tab,
            6: self.setup_actions_tab,
            7: self.setup_ocr_training_tab,
            8: self.setup_guide_tab
        }
        
        # Initialize the tab
        if index in tab_setup_methods:
            tab_setup_methods[index]()
            self.tabs_initialized.add(index)
            logger.debug(f"Initialized tab {index}")
    
    def apply_saved_theme(self):
        """Load and apply the saved theme preference on startup"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'theme'")
            row = c.fetchone()
            conn.close()
            if row:
                self.apply_theme(row[0])
            else:
                # Default to Fusion (Light) if no preference saved
                self.apply_theme("Fusion (Light)")
        except:
            # Use Fusion (Light) as default theme if database error
            self.apply_theme("Fusion (Light)")

    def apply_saved_font_size(self):
        """Load and apply the saved font size preference on startup"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'font_size'")
            row = c.fetchone()
            conn.close()
            if row:
                self.apply_font_size(int(row[0]))
            else:
                # Default to 10pt if no preference saved
                self.apply_font_size(10)
        except:
            # Use 10pt as default font size if database error
            self.apply_font_size(10)

    def load_config_paths(self):
        try:
            self.bottom_status.setText("Loading Directory location...")
            QApplication.processEvents()
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'input_dir'")
            row = c.fetchone()
            global INPUT_DIR, PROCESSED_DIR
            if row:
                INPUT_DIR = Path(row[0])
                PROCESSED_DIR = INPUT_DIR / "Processed"
                PROCESSED_DIR.mkdir(exist_ok=True)
                QApplication.processEvents()
            c.execute("SELECT value FROM app_config WHERE key = 'output_dir'")
            row = c.fetchone()
            if row:
                global OUTPUT_DIR
                OUTPUT_DIR = Path(row[0])
                OUTPUT_DIR.mkdir(exist_ok=True)
                QApplication.processEvents()
            conn.close()
            self.bottom_status.setText("Ready")
            QApplication.processEvents()
        except Exception as e:
            logger.error(f"Config load failed: {e}")
            self.bottom_status.setText("Config load failed")
            QApplication.processEvents()

    def setup_process_tab(self):
        layout = QVBoxLayout(self.tab_process)

        # MAIN CONTAINER: Left side (controls) + Right side (preview) with splitter
        main_container = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT SIDE: Single outer box containing all controls
        left_outer_box = QGroupBox("Controls")
        left_side = QVBoxLayout(left_outer_box)
        left_side.setSpacing(10)
        left_side.setContentsMargins(10, 10, 10, 10)
        
        # INPUT FILES LIST — now inside Shipment File group
        self.input_files_list = AutoSelectListWidget()
        self.input_files_list.setSelectionMode(QListWidget.SingleSelection)
        self.input_files_list.itemClicked.connect(self.load_selected_input_file)
        # Connect itemActivated for Enter key and double-click support
        self.input_files_list.itemActivated.connect(self.load_selected_input_file)
        # Allow focus for tab navigation
        self.input_files_list.setFocusPolicy(Qt.StrongFocus)
        self.refresh_input_btn = QPushButton("Refresh")
        self.refresh_input_btn.setFixedHeight(25)
        self.refresh_input_btn.clicked.connect(self.refresh_input_files)

        # INVOICE VALUES
        values_group = QGroupBox("Invoice Values")
        values_layout = QFormLayout()
        values_layout.setLabelAlignment(Qt.AlignRight)

        self.ci_input = ForceEditableLineEdit("")
        self.ci_input.setObjectName("ci_input")
        self.ci_input.setPlaceholderText("Enter CI value...")
        self.ci_input.textChanged.connect(self.update_invoice_check)

        self.wt_input = ForceEditableLineEdit("")
        self.wt_input.setObjectName("wt_input")
        self.wt_input.setPlaceholderText("Enter net weight...")
        self.wt_input.textChanged.connect(self.update_invoice_check)

        values_layout.addRow("CI Value (USD):", self.ci_input)
        values_layout.addRow("Net Weight (kg):", self.wt_input)

        # MID selector (moved above Invoice Check)
        self.mid_label = QLabel("MID:")
        self.mid_combo = QComboBox()
        self.mid_combo.setFocusPolicy(Qt.StrongFocus)  # Ensure combo accepts keyboard focus
        self.mid_combo.currentTextChanged.connect(self.on_mid_changed)
        values_layout.addRow(self.mid_label, self.mid_combo)

        # Removed broken setTabOrder calls - they were causing Qt warnings and possibly blocking keyboard input

        # Invoice check label and Edit Values button
        self.invoice_check_label = QLabel("No file loaded")
        self.invoice_check_label.setWordWrap(True)
        self.invoice_check_label.setStyleSheet("font-size: 7pt;")
        self.invoice_check_label.setAlignment(Qt.AlignCenter)

        vbox_check = QVBoxLayout()
        vbox_check.setSpacing(12)
        vbox_check.setContentsMargins(0, 10, 0, 0)

        vbox_check.addWidget(self.invoice_check_label, alignment=Qt.AlignCenter)
        
        # Edit Values button (initially hidden, shown when values don't match)
        self.edit_values_btn = QPushButton("Edit Values")
        self.edit_values_btn.setFixedSize(120, 30)
        self.edit_values_btn.setStyleSheet(self.get_button_style("warning"))
        self.edit_values_btn.setVisible(False)
        self.edit_values_btn.clicked.connect(self.start_processing_with_editable_preview)
        vbox_check.addWidget(self.edit_values_btn, alignment=Qt.AlignCenter)
        
        vbox_check.addStretch()

        values_layout.addRow("Invoice Check:", vbox_check)
        values_group.setLayout(values_layout)

        # SHIPMENT FILE (merged with Saved Profiles and Input Files)
        file_group = QGroupBox("Shipment File")
        file_group.setObjectName("SavedProfilesGroup")
        file_layout = QFormLayout()
        file_layout.setLabelAlignment(Qt.AlignRight)
        # Profile selector
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self.load_selected_profile)
        file_layout.addRow("Map Profile:", self.profile_combo)
        # Input files list and refresh button (moved here)
        file_layout.addRow("Input Files:", self.input_files_list)
        file_layout.addRow("", self.refresh_input_btn)
        # File display (read-only, shows selected file from Input Files list)
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.update_file_label_style()  # Set initial style based on theme
        file_layout.addRow("Selected File:", self.file_label)
        file_group.setLayout(file_layout)
        left_side.addWidget(file_group)
        left_side.addWidget(values_group)

        # ACTIONS GROUP — Clear All + Export Worksheet buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setFixedHeight(35)
        self.clear_btn.setStyleSheet(self.get_button_style("danger"))
        self.clear_btn.clicked.connect(self.clear_all)

        self.process_btn = QPushButton("Process Invoice")
        self.process_btn.setEnabled(False)
        self.process_btn.setFixedHeight(35)
        self.process_btn.setStyleSheet(self.get_button_style("success"))
        self.process_btn.clicked.connect(self._process_or_export)
        # Make button respond to Enter/Return key when focused
        self.process_btn.setAutoDefault(True)
        self.process_btn.setDefault(False)  # Don't make it the default for the whole window

        actions_layout.addWidget(self.process_btn)
        actions_layout.addWidget(self.clear_btn)
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        left_side.addWidget(actions_group)

        # BATCH PROCESSING GROUP — process multiple PDFs from supplier folders
        batch_group = QGroupBox("Batch Invoice Processing")
        batch_layout = QVBoxLayout()

        # Supplier folder selector
        supplier_selector_layout = QHBoxLayout()
        supplier_selector_layout.addWidget(QLabel("Supplier:"))
        self.batch_supplier_combo = QComboBox()
        self.batch_supplier_combo.setMinimumWidth(150)
        supplier_selector_layout.addWidget(self.batch_supplier_combo)
        supplier_selector_layout.addStretch()
        batch_layout.addLayout(supplier_selector_layout)

        # Process button
        self.batch_process_btn = QPushButton("Process All PDFs")
        self.batch_process_btn.setFixedHeight(35)
        self.batch_process_btn.setStyleSheet(self.get_button_style("success"))
        self.batch_process_btn.clicked.connect(self.start_batch_processing)
        batch_layout.addWidget(self.batch_process_btn)

        # Progress bar (hidden by default)
        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        self.batch_progress.setMaximum(100)
        batch_layout.addWidget(self.batch_progress)

        # Status label
        self.batch_status_label = QLabel("Ready for batch processing")
        self.batch_status_label.setWordWrap(True)
        self.batch_status_label.setStyleSheet("font-size: 8pt; color: #666666;")
        batch_layout.addWidget(self.batch_status_label)

        batch_group.setLayout(batch_layout)
        left_side.addWidget(batch_group)

        # EXPORTED FILES GROUP — shows recent exports
        exports_group = QGroupBox("Exported Files")
        exports_layout = QVBoxLayout()
        
        self.exports_list = AutoSelectListWidget()
        self.exports_list.setSelectionMode(QListWidget.SingleSelection)
        self.exports_list.itemDoubleClicked.connect(self.open_exported_file)
        # Connect itemActivated for Enter key support
        self.exports_list.itemActivated.connect(self.open_exported_file)
        # Allow focus for tab navigation
        self.exports_list.setFocusPolicy(Qt.StrongFocus)
        exports_layout.addWidget(self.exports_list)

        self.refresh_exports_btn = QPushButton("Refresh")
        self.refresh_exports_btn.setFixedHeight(25)
        self.refresh_exports_btn.clicked.connect(self.refresh_exported_files)
        exports_layout.addWidget(self.refresh_exports_btn)
        
        exports_group.setLayout(exports_layout)
        left_side.addWidget(exports_group)
        
        # Set maximum width for left controls to keep it compact
        left_outer_box.setMaximumWidth(350)

        # Add left_outer_box to splitter
        splitter.addWidget(left_outer_box)

        # RIGHT SIDE: Preview table in a widget
        right_widget = QWidget()
        right_side = QVBoxLayout(right_widget)
        right_side.setContentsMargins(0, 0, 0, 0)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_side.addWidget(self.progress)

        preview_group = QGroupBox("Result Preview")
        preview_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "Product No","Value","HTS","MID","Wt","Dec","Melt","Cast","Smelt","Flag","232%","Non-232%","232 Status"
        ])
        # Make columns manually resizable instead of auto-stretch
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSortingEnabled(False)  # Disabled for better performance
        # Match body font size to the header font size and make non-bold
        header_font = self.table.horizontalHeader().font()
        header_font.setBold(False)
        self.table.horizontalHeader().setFont(header_font)
        self.table.setFont(header_font)

        # Enable clicking header to select entire column
        self.table.horizontalHeader().sectionClicked.connect(self.select_column)

        # Connect signal to save column widths when they change
        self.table.horizontalHeader().sectionResized.connect(self.save_column_widths)

        # Load saved column widths
        self.load_column_widths()

        # Apply green focus color stylesheet
        self.update_table_stylesheet()

        preview_layout.addWidget(self.table)
        preview_group.setLayout(preview_layout)
        right_side.addWidget(preview_group, 1)

        # Add right widget to splitter
        splitter.addWidget(right_widget)

        # Set initial splitter sizes - minimize left, maximize right (15% left, 85% right)
        splitter.setSizes([200, 1000])

        # Make the splitter collapsible on the left side
        splitter.setCollapsible(0, False)  # Don't allow full collapse
        splitter.setCollapsible(1, False)
        
        # Add splitter to main container
        main_container.addWidget(splitter)

        layout.addLayout(main_container, 1)

        # Set up tab order for keyboard navigation through controls
        # Order: Map Profile → Input Files → Refresh (Shipment) → CI Value → Net Weight →
        #        MID → Process Invoice → Edit Values → Clear All → Exported Files → Refresh (Exports)
        self.setTabOrder(self.profile_combo, self.input_files_list)
        self.setTabOrder(self.input_files_list, self.refresh_input_btn)
        self.setTabOrder(self.refresh_input_btn, self.ci_input)
        self.setTabOrder(self.ci_input, self.wt_input)
        self.setTabOrder(self.wt_input, self.mid_combo)
        self.setTabOrder(self.mid_combo, self.process_btn)
        self.setTabOrder(self.process_btn, self.edit_values_btn)
        self.setTabOrder(self.edit_values_btn, self.clear_btn)
        self.setTabOrder(self.clear_btn, self.exports_list)
        self.setTabOrder(self.exports_list, self.refresh_exports_btn)

        # Populate supplier combo for batch processing
        self.refresh_supplier_combo()

        self.tab_process.setLayout(layout)
        self._install_preview_shortcuts()

        # Ensure input fields are enabled on startup
        self._enable_input_fields()

        # Refresh supplier folders for batch processing
        self.refresh_supplier_combo()

        # Create a timer to continuously force fields to be editable
        # This works around whatever is locking the fields
        from PyQt5.QtCore import QTimer
        self._field_watchdog_timer = QTimer()
        self._field_watchdog_timer.timeout.connect(self._force_fields_editable)
        self._field_watchdog_timer.start(100)  # Check every 100ms

        # Event filter already installed in __init__, don't install again
    
    def _force_fields_editable(self):
        """Watchdog timer callback that forces fields to stay editable"""
        if hasattr(self, 'ci_input'):
            # Bypass the override and force the parent class method
            QLineEdit.setReadOnly(self.ci_input, False)
            QLineEdit.setEnabled(self.ci_input, True)
        if hasattr(self, 'wt_input'):
            QLineEdit.setReadOnly(self.wt_input, False)
            QLineEdit.setEnabled(self.wt_input, True)

    def _enable_input_fields(self):
        """Ensure CI and Weight input fields are enabled and ready for input"""
        # Block signals to prevent recursion during enable
        if hasattr(self, 'ci_input'):
            self.ci_input.blockSignals(True)
            self.ci_input.setReadOnly(False)
            self.ci_input.setEnabled(True)
            self.ci_input.setFocusPolicy(Qt.StrongFocus)
            # Force immediate visual update
            self.ci_input.update()
            self.ci_input.blockSignals(False)

        if hasattr(self, 'wt_input'):
            self.wt_input.blockSignals(True)
            self.wt_input.setReadOnly(False)
            self.wt_input.setEnabled(True)
            self.wt_input.setFocusPolicy(Qt.StrongFocus)
            # Force immediate visual update
            self.wt_input.update()
            self.wt_input.blockSignals(False)

    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(700, 750)  # Increased size for better layout
        layout = QVBoxLayout(dialog)

        # Create tab widget for better organization
        tabs = QTabWidget()

        # ===== TAB 1: APPEARANCE =====
        appearance_widget = QWidget()
        appearance_layout = QVBoxLayout(appearance_widget)

        # Theme Settings Group
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout()
        
        # Use local variable instead of instance variable
        theme_combo = QComboBox()
        theme_combo.addItems(["System Default", "Fusion (Light)", "Windows", "Fusion (Dark)", "Ocean", "Teal Professional"])
        
        # Load saved theme preference and set combo without triggering signal
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'theme'")
            row = c.fetchone()
            conn.close()
            
            if row:
                saved_theme = row[0]
                index = theme_combo.findText(saved_theme)
                if index >= 0:
                    # Block signals to prevent double-applying theme
                    theme_combo.blockSignals(True)
                    theme_combo.setCurrentIndex(index)
                    theme_combo.blockSignals(False)
        except:
            pass
        
        theme_combo.currentTextChanged.connect(self.apply_theme)
        theme_layout.addRow("Application Theme:", theme_combo)

        theme_info = QLabel("<small>Theme changes apply immediately. System Default uses your Windows theme settings.</small>")
        theme_info.setWordWrap(True)
        theme_info.setStyleSheet("color:#666; padding:5px;")
        theme_layout.addRow("", theme_info)

        # Font Size Slider
        font_size_layout = QHBoxLayout()
        font_size_slider = QSlider(Qt.Horizontal)
        font_size_slider.setMinimum(8)
        font_size_slider.setMaximum(16)
        font_size_slider.setValue(10)  # Default
        font_size_slider.setTickPosition(QSlider.TicksBelow)
        font_size_slider.setTickInterval(1)

        font_size_value_label = QLabel("10pt")
        font_size_value_label.setMinimumWidth(40)

        # Load saved font size preference
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'font_size'")
            row = c.fetchone()
            conn.close()

            if row:
                saved_font_size = int(row[0])
                font_size_slider.setValue(saved_font_size)
                font_size_value_label.setText(f"{saved_font_size}pt")
        except:
            pass

        # Connect slider to update label and apply font size
        def update_font_size(value):
            font_size_value_label.setText(f"{value}pt")
            self.apply_font_size(value)

        font_size_slider.valueChanged.connect(update_font_size)

        font_size_layout.addWidget(font_size_slider)
        font_size_layout.addWidget(font_size_value_label)

        theme_layout.addRow("Font Size:", font_size_layout)

        theme_group.setLayout(theme_layout)
        appearance_layout.addWidget(theme_group)

        # Excel Viewer Settings Group
        viewer_group = QGroupBox("Excel File Viewer")
        viewer_layout = QFormLayout()

        # Excel viewer combo box
        viewer_combo = QComboBox()
        if sys.platform == 'linux':
            viewer_combo.addItems(["System Default", "Gnumeric"])
        else:
            viewer_combo.addItems(["System Default"])
            viewer_combo.setEnabled(False)  # Only relevant on Linux

        # Load saved preference
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'excel_viewer'")
            row = c.fetchone()
            conn.close()

            if row:
                saved_viewer = row[0]
                index = viewer_combo.findText(saved_viewer)
                if index >= 0:
                    viewer_combo.setCurrentIndex(index)
        except:
            pass

        # Save preference when changed
        def save_viewer_preference(viewer):
            try:
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('excel_viewer', ?)", (viewer,))
                conn.commit()
                conn.close()
                logger.info(f"Excel viewer preference changed to: {viewer}")
            except Exception as e:
                logger.error(f"Failed to save excel viewer preference: {e}")

        viewer_combo.currentTextChanged.connect(save_viewer_preference)
        viewer_layout.addRow("Open Exported Files With:", viewer_combo)

        viewer_info = QLabel("<small>Choose which application opens exported Excel files. (Linux only)</small>")
        viewer_info.setWordWrap(True)
        viewer_info.setStyleSheet("color:#666; padding:5px;")
        viewer_layout.addRow("", viewer_info)

        viewer_group.setLayout(viewer_layout)
        appearance_layout.addWidget(viewer_group)

        # Preview Table Colors Group
        colors_group = QGroupBox("Preview Table Row Colors")
        colors_layout = QFormLayout()

        # Helper function to create color picker button
        def create_color_button(config_key, default_color):
            """Create a color picker button with saved color"""
            button = QPushButton()
            button.setFixedSize(100, 30)

            # Load saved color or use default
            saved_color = default_color
            try:
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("SELECT value FROM app_config WHERE key = ?", (config_key,))
                row = c.fetchone()
                conn.close()
                if row:
                    saved_color = row[0]
            except:
                pass

            # Set button style with current color
            button.setStyleSheet(f"background-color: {saved_color}; border: 1px solid #999;")

            def pick_color():
                color = QColorDialog.getColor(QColor(saved_color), dialog, "Choose Color")
                if color.isValid():
                    color_hex = color.name()
                    button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #999;")
                    # Save to database
                    try:
                        conn = sqlite3.connect(str(DB_PATH))
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                                  (config_key, color_hex))
                        conn.commit()
                        conn.close()
                        logger.info(f"Saved color preference {config_key}: {color_hex}")
                        # Refresh the preview table if it exists
                        if hasattr(self, 'table') and self.table.rowCount() > 0:
                            self.refresh_preview_colors()
                    except Exception as e:
                        logger.error(f"Failed to save color preference: {e}")

            button.clicked.connect(pick_color)
            return button

        # 232 Steel rows color picker
        steel_color_btn = create_color_button('preview_steel_color', '#4a4a4a')
        colors_layout.addRow("Section 232 Rows:", steel_color_btn)

        # Non-232 rows color picker
        non232_color_btn = create_color_button('preview_non232_color', '#ff0000')
        colors_layout.addRow("Non-232 Rows:", non232_color_btn)

        colors_info = QLabel("<small>Choose font colors for different row types in the preview table.</small>")
        colors_info.setWordWrap(True)
        colors_info.setStyleSheet("color:#666; padding:5px;")
        colors_layout.addRow("", colors_info)

        colors_group.setLayout(colors_layout)
        appearance_layout.addWidget(colors_group)

        # Add stretch to appearance tab
        appearance_layout.addStretch()
        tabs.addTab(appearance_widget, "Appearance")

        # ===== TAB 2: FOLDER LOCATIONS =====
        folders_widget = QWidget()
        folders_layout = QVBoxLayout(folders_widget)

        group = QGroupBox("Folder Locations")
        glayout = QFormLayout()
        
        # Input folder display and button
        global INPUT_DIR, OUTPUT_DIR
        input_dir_str = str(INPUT_DIR) if 'INPUT_DIR' in globals() and INPUT_DIR else "(not set)"
        output_dir_str = str(OUTPUT_DIR) if 'OUTPUT_DIR' in globals() and OUTPUT_DIR else "(not set)"

        # Helper function to create path display widget
        def create_path_display(path_str):
            """Create a read-only text edit for displaying file paths"""
            text_edit = QPlainTextEdit()
            text_edit.setPlainText(path_str)
            text_edit.setReadOnly(True)
            text_edit.setFixedHeight(45)

            # Apply theme-aware styling
            is_dark = hasattr(self, 'current_theme') and self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]
            if is_dark:
                text_edit.setStyleSheet("background:#2d2d2d; padding:5px; border:1px solid #555; color:#e0e0e0; font-family: monospace;")
            else:
                text_edit.setStyleSheet("background:#f0f0f0; padding:5px; border:1px solid #ccc; color:#000000; font-family: monospace;")

            return text_edit

        input_path_display = create_path_display(input_dir_str)

        input_btn = QPushButton("Change Input Folder")
        input_btn.clicked.connect(lambda: self.select_input_folder(input_path_display))
        glayout.addRow("Input Folder:", input_path_display)
        glayout.addRow("", input_btn)

        # Output folder display and button
        output_path_display = create_path_display(output_dir_str)

        output_btn = QPushButton("Change Output Folder")
        output_btn.clicked.connect(lambda: self.select_output_folder(output_path_display))
        glayout.addRow("Output Folder:", output_path_display)
        glayout.addRow("", output_btn)

        # Processed PDF folder display and button
        global PROCESSED_PDF_DIR
        processed_pdf_dir_str = str(PROCESSED_PDF_DIR) if 'PROCESSED_PDF_DIR' in globals() and PROCESSED_PDF_DIR else "(not set)"
        processed_pdf_path_display = create_path_display(processed_pdf_dir_str)

        processed_pdf_btn = QPushButton("Change Processed PDF Folder")
        processed_pdf_btn.clicked.connect(lambda: self.select_processed_pdf_folder(processed_pdf_path_display))
        glayout.addRow("Processed PDF Folder:", processed_pdf_path_display)
        glayout.addRow("", processed_pdf_btn)

        group.setLayout(glayout)
        folders_layout.addWidget(group)

        folders_layout.addStretch()
        tabs.addTab(folders_widget, "Folders")

        # ===== TAB 3: SUPPLIER FOLDERS =====
        suppliers_widget = QWidget()
        suppliers_layout = QVBoxLayout(suppliers_widget)

        # Info box
        info_box = QGroupBox("Supplier Folder Management")
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "Manage supplier folders in your Input directory. Each supplier folder can contain PDF invoices "
            "for batch processing. Create new suppliers or remove existing ones."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        info_box.setLayout(info_layout)
        suppliers_layout.addWidget(info_box)

        # Suppliers list group
        suppliers_group = QGroupBox("Suppliers in Input Folder")
        suppliers_group_layout = QVBoxLayout()

        # List widget showing suppliers
        self.settings_suppliers_list = QListWidget()
        self.settings_suppliers_list.setMinimumHeight(200)
        suppliers_group_layout.addWidget(self.settings_suppliers_list)

        # Buttons layout
        suppliers_btn_layout = QHBoxLayout()

        btn_add_supplier = QPushButton("+ Add New Supplier")
        btn_add_supplier.setStyleSheet(self.get_button_style("success"))
        btn_add_supplier.clicked.connect(self.add_new_supplier_dialog)
        suppliers_btn_layout.addWidget(btn_add_supplier)

        btn_remove_supplier = QPushButton("- Remove Selected")
        btn_remove_supplier.setStyleSheet(self.get_button_style("danger"))
        btn_remove_supplier.clicked.connect(lambda: self.remove_selected_supplier(self.settings_suppliers_list))
        suppliers_btn_layout.addWidget(btn_remove_supplier)

        btn_open_supplier = QPushButton("Open Folder")
        btn_open_supplier.setStyleSheet(self.get_button_style("default"))
        btn_open_supplier.clicked.connect(lambda: self.open_supplier_folder(self.settings_suppliers_list))
        suppliers_btn_layout.addWidget(btn_open_supplier)

        btn_refresh_suppliers = QPushButton("Refresh List")
        btn_refresh_suppliers.setStyleSheet(self.get_button_style("info"))
        btn_refresh_suppliers.clicked.connect(self.refresh_suppliers_list)
        suppliers_btn_layout.addWidget(btn_refresh_suppliers)

        suppliers_group_layout.addLayout(suppliers_btn_layout)
        suppliers_group.setLayout(suppliers_group_layout)
        suppliers_layout.addWidget(suppliers_group)

        # Status label
        self.suppliers_count_label = QLabel("Loading suppliers...")
        self.suppliers_count_label.setStyleSheet("font-weight:bold; padding:5px;")
        suppliers_layout.addWidget(self.suppliers_count_label)

        suppliers_layout.addStretch()
        tabs.addTab(suppliers_widget, "Suppliers")

        # Load suppliers list when dialog opens
        self.refresh_suppliers_list()

        # Add tabs to main dialog layout
        layout.addWidget(tabs)
        dialog.exec_()

        # After Settings dialog closes, refresh supplier combo in case suppliers were added/removed
        self.refresh_supplier_combo()
    
    def apply_theme(self, theme_name):
        """Apply the selected theme to the application"""
        app = QApplication.instance()
        
        # Store current theme name
        self.current_theme = theme_name
        
        if theme_name == "System Default":
            app.setStyle("")
            app.setPalette(app.style().standardPalette())
        elif theme_name == "Fusion (Light)":
            app.setStyle("Fusion")
            app.setPalette(app.style().standardPalette())
        elif theme_name == "Windows":
            app.setStyle("Windows")
            app.setPalette(app.style().standardPalette())
        elif theme_name == "Fusion (Dark)":
            app.setStyle("Fusion")
            dark_palette = self.get_dark_palette()
            app.setPalette(dark_palette)
        elif theme_name == "Ocean":
            app.setStyle("Fusion")
            ocean_palette = self.get_ocean_palette()
            app.setPalette(ocean_palette)
        elif theme_name == "Teal Professional":
            app.setStyle("Fusion")
            teal_palette = self.get_teal_professional_palette()
            app.setPalette(teal_palette)
        
        # Refresh button styles to match new theme
        self.refresh_button_styles()

        # Update file label style for new theme
        if hasattr(self, 'file_label'):
            self.update_file_label_style()

        # Update status bar styles for new theme
        self.update_status_bar_styles()

        # Update table stylesheet for new theme
        self.update_table_stylesheet()
        
        # Save theme preference
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('theme', ?)", (theme_name,))
            conn.commit()
            conn.close()
            logger.info(f"Theme changed to: {theme_name}")
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")

    def apply_font_size(self, size):
        """Apply the selected font size to the application"""
        app = QApplication.instance()

        # Get current font and update size
        font = app.font()
        font.setPointSize(size)
        app.setFont(font)

        # Save font size preference
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('font_size', ?)", (str(size),))
            conn.commit()
            conn.close()
            logger.info(f"Font size changed to: {size}pt")
        except Exception as e:
            logger.error(f"Failed to save font size: {e}")

    def update_file_label_style(self):
        """Update file label background based on current theme"""
        if not hasattr(self, 'current_theme'):
            self.current_theme = "System Default"
        
        # Use white background for light themes, darker background for dark themes
        if self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]:
            self.file_label.setStyleSheet("background:#2d2d2d; padding:5px; border:1px solid #555; color:#e0e0e0;")
        else:
            self.file_label.setStyleSheet("background:white; padding:5px; border:1px solid #ccc;")
    
    def update_status_bar_styles(self):
        """Update status bar backgrounds based on current theme"""
        if not hasattr(self, 'current_theme'):
            self.current_theme = "System Default"
        
        is_dark = self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]
        
        if is_dark:
            # Dark theme status bars
            self.status.setStyleSheet("font-size:14pt; padding:8px; background:#2d2d2d; color:#e0e0e0;")
            self.bottom_status.setStyleSheet("font-size:9pt; color:#b0b0b0;")
            if hasattr(self, 'bottom_bar'):
                self.bottom_bar.setStyleSheet("""
                    QWidget {
                        background: #2d2d2d;
                        border-top: 1px solid #404040;
                    }
                """)
        else:
            # Light theme status bars
            self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0; color:#000000;")
            self.bottom_status.setStyleSheet("font-size:9pt; color:#555555;")
            if hasattr(self, 'bottom_bar'):
                self.bottom_bar.setStyleSheet("""
                    QWidget {
                        background: #e8e8e8;
                        border-top: 1px solid #d0d0d0;
                    }
                """)
    
    def update_status_bar_styles(self):
        """Update status bar backgrounds based on current theme"""
        if not hasattr(self, 'current_theme'):
            self.current_theme = "System Default"
        
        is_dark = self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]
        
        if is_dark:
            # Dark theme status bars
            self.status.setStyleSheet("font-size:14pt; padding:8px; background:#2d2d2d; color:#e0e0e0;")
            self.bottom_status.setStyleSheet("font-size:9pt; color:#b0b0b0;")
            if hasattr(self, 'bottom_bar'):
                self.bottom_bar.setStyleSheet("""
                    QWidget {
                        background: #2d2d2d;
                        border-top: 1px solid #404040;
                    }
                """)
        else:
            # Light theme status bars
            self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0; color:#000000;")
            self.bottom_status.setStyleSheet("font-size:9pt; color:#555555;")
            if hasattr(self, 'bottom_bar'):
                self.bottom_bar.setStyleSheet("""
                    QWidget {
                        background: #e8e8e8;
                        border-top: 1px solid #d0d0d0;
                    }
                """)

    def update_table_stylesheet(self):
        """Update table stylesheet with green focus color for current theme"""
        if not hasattr(self, 'table'):
            return

        # Set green focus color that works with all themes
        self.table.setStyleSheet("""
            QTableWidget::item:focus {
                background-color: #90EE90;
                border: 2px solid #228B22;
            }
        """)

    def get_preview_row_color(self, is_steel_row):
        """Get the color for preview table rows based on steel content"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            if is_steel_row:
                c.execute("SELECT value FROM app_config WHERE key = 'preview_steel_color'")
                row = c.fetchone()
                conn.close()
                return QColor(row[0]) if row else QColor("#4a4a4a")
            else:
                c.execute("SELECT value FROM app_config WHERE key = 'preview_non232_color'")
                row = c.fetchone()
                conn.close()
                return QColor(row[0]) if row else QColor("#ff0000")
        except:
            # Return defaults if database query fails
            return QColor("#4a4a4a") if is_steel_row else QColor("#ff0000")

    def refresh_preview_colors(self):
        """Refresh all row colors in the preview table based on current settings"""
        if not hasattr(self, 'table') or self.table.rowCount() == 0:
            return

        try:
            # Temporarily disconnect itemChanged signal to avoid triggering edits
            self.table.blockSignals(True)

            for row in range(self.table.rowCount()):
                # Get the steel ratio from the table's 232% column (index 10)
                steel_item = self.table.item(row, 10)
                if steel_item:
                    steel_text = steel_item.text().replace('%', '')
                    try:
                        steel_ratio = float(steel_text) / 100.0
                        is_steel_row = steel_ratio > 0.0
                        row_color = self.get_preview_row_color(is_steel_row)

                        # Update color for all items in this row
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            if item:
                                item.setForeground(row_color)
                    except ValueError:
                        pass  # Skip if can't parse percentage

            self.table.blockSignals(False)
        except Exception as e:
            logger.error(f"Error refreshing preview colors: {e}")
            self.table.blockSignals(False)

    def refresh_button_styles(self):
        """Refresh all button styles to match current theme"""
        # Process tab buttons
        if hasattr(self, 'clear_btn'):
            self.clear_btn.setStyleSheet(self.get_button_style("danger"))
        if hasattr(self, 'process_btn'):
            self.process_btn.setStyleSheet(self.get_button_style("success"))
        if hasattr(self, 'edit_values_btn'):
            self.edit_values_btn.setStyleSheet(self.get_button_style("warning"))
        
        # Import tab - need to find and update buttons in the tab
        if hasattr(self, 'tab_import'):
            for btn in self.tab_import.findChildren(QPushButton):
                if btn.text() == "Load CSV File":
                    btn.setStyleSheet(self.get_button_style("info"))
                elif btn.text() == "Reset Mapping":
                    btn.setStyleSheet(self.get_button_style("danger"))
                elif btn.text() == "IMPORT NOW":
                    btn.setStyleSheet(self.get_button_style("success") + "QPushButton { font-size:16pt; padding:15px; }")
        
        # Shipment Mapping tab
        if hasattr(self, 'tab_shipment_map'):
            for btn in self.tab_shipment_map.findChildren(QPushButton):
                if btn.text() == "Save Current Mapping As...":
                    btn.setStyleSheet(self.get_button_style("success"))
                elif btn.text() == "Delete Profile":
                    btn.setStyleSheet(self.get_button_style("danger"))
                elif btn.text() == "Load CSV to Map":
                    btn.setStyleSheet(self.get_button_style("info"))
                elif btn.text() == "Reset Current":
                    btn.setStyleSheet(self.get_button_style("danger"))
        
        # Master/Parts View tab
        if hasattr(self, 'tab_master'):
            for btn in self.tab_master.findChildren(QPushButton):
                if btn.text() == "Run Query":
                    btn.setStyleSheet(self.get_button_style("info"))
                elif btn.text() == "Execute":
                    btn.setStyleSheet(self.get_button_style("success"))
        
        # Config tab
        if hasattr(self, 'tab_config'):
            for btn in self.tab_config.findChildren(QPushButton):
                if btn.text() == "Import Section 232 Tariffs (CSV/Excel)":
                    btn.setStyleSheet(self.get_button_style("success"))
                elif btn.text() == "Import from CSV":
                    btn.setStyleSheet(self.get_button_style("info"))
                elif btn.text() == "Refresh View":
                    btn.setStyleSheet(self.get_button_style("info"))

    
    def get_dark_palette(self):
        """Create a Windows 11 dark mode inspired theme"""
        from PyQt5.QtGui import QPalette, QColor
        
        palette = QPalette()
        # Windows 11 dark theme colors
        palette.setColor(QPalette.Window, QColor(41, 41, 41))  # Main background
        palette.setColor(QPalette.WindowText, QColor(243, 243, 243))  # Primary text
        palette.setColor(QPalette.Base, QColor(51, 51, 51))  # Secondary background for input fields
        palette.setColor(QPalette.AlternateBase, QColor(115, 115, 115))  # Tertiary background for alternating rows
        palette.setColor(QPalette.ToolTipBase, QColor(45, 45, 45))  # Tertiary background
        palette.setColor(QPalette.ToolTipText, QColor(243, 243, 243))  # Primary text
        palette.setColor(QPalette.Text, QColor(243, 243, 243))  # Primary text in text boxes
        palette.setColor(QPalette.Button, QColor(45, 45, 45))  # Tertiary background for buttons
        palette.setColor(QPalette.ButtonText, QColor(243, 243, 243))  # Primary text on buttons
        palette.setColor(QPalette.BrightText, QColor(164, 38, 44))  # Danger/error red
        palette.setColor(QPalette.Link, QColor(0, 120, 212))  # Accent blue
        palette.setColor(QPalette.Highlight, QColor(22, 120, 212))  # Selection/highlight blue
        palette.setColor(QPalette.HighlightedText, QColor(243, 243, 243))  # Primary text
        return palette
    
    def get_ocean_palette(self):
        """Create an ocean-themed color palette with deep blues and teals"""
        from PyQt5.QtGui import QPalette, QColor
        
        palette = QPalette()
        # Deep ocean blue backgrounds
        palette.setColor(QPalette.Window, QColor(28, 57, 87))  # Deep ocean blue
        palette.setColor(QPalette.WindowText, QColor(230, 245, 255))  # Light blue-white text
        palette.setColor(QPalette.Base, QColor(15, 35, 55))  # Darker blue for input fields
        palette.setColor(QPalette.AlternateBase, QColor(35, 65, 95))  # Lighter ocean blue
        palette.setColor(QPalette.ToolTipBase, QColor(200, 230, 255))  # Light blue
        palette.setColor(QPalette.ToolTipText, QColor(15, 35, 55))  # Dark blue
        palette.setColor(QPalette.Text, QColor(230, 245, 255))  # Light blue-white text
        palette.setColor(QPalette.Button, QColor(40, 75, 110))  # Medium ocean blue
        palette.setColor(QPalette.ButtonText, QColor(230, 245, 255))  # Light text
        palette.setColor(QPalette.BrightText, QColor(0, 255, 200))  # Bright teal
        palette.setColor(QPalette.Link, QColor(100, 200, 255))  # Bright cyan
        palette.setColor(QPalette.Highlight, QColor(0, 150, 180))  # Teal highlight
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # White text
        return palette
    
    def get_teal_professional_palette(self):
        """Create a teal professional palette matching customs management software"""
        from PyQt5.QtGui import QPalette, QColor
        
        palette = QPalette()
        # Modern teal theme with consistent light backgrounds
        palette.setColor(QPalette.Window, QColor(235, 245, 245))  # Very light muted teal background
        palette.setColor(QPalette.WindowText, QColor(33, 33, 33))  # Dark grey text for readability
        palette.setColor(QPalette.Base, QColor(235, 245, 245))  # Same as Window for consistency
        palette.setColor(QPalette.AlternateBase, QColor(225, 238, 238))  # Slightly darker for alternating rows
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(33, 33, 33))
        palette.setColor(QPalette.Text, QColor(33, 33, 33))  # Dark grey text
        palette.setColor(QPalette.Button, QColor(70, 150, 180))  # Softer, brighter teal for buttons
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))  # White text on buttons
        palette.setColor(QPalette.BrightText, QColor(255, 90, 90))  # Softer red
        palette.setColor(QPalette.Link, QColor(50, 130, 160))  # Appealing link color
        palette.setColor(QPalette.Highlight, QColor(80, 180, 210))  # Bright, appealing highlight
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # White highlighted text
        return palette

    def get_button_style(self, button_type="default"):
        """
        Generate theme-aware button styles using current palette colors.
        
        Args:
            button_type: "default", "primary", "danger", "info", "warning", "success"
        
        Returns:
            CSS stylesheet string that adapts to current theme
        """
        from PyQt5.QtGui import QPalette, QColor
        from PyQt5.QtWidgets import QApplication
        
        palette = QApplication.palette()
        
        # Get base colors from theme
        base_bg = palette.color(QPalette.Button)
        base_text = palette.color(QPalette.ButtonText)
        highlight = palette.color(QPalette.Highlight)
        
        # Check if we're in a dark theme
        is_dark_theme = hasattr(self, 'current_theme') and self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]
        
        # In dark themes, all buttons use teal
        if is_dark_theme:
            bg = QColor(66, 160, 189)  # Teal
            hover_bg = QColor(53, 128, 151)  # Darker Teal
            disabled_bg = QColor(160, 160, 160)  # Grey
        # In light themes, use different colors per button type
        elif button_type == "primary" or button_type == "success":
            # Green for success/primary actions
            bg = QColor(40, 167, 69)  # Green
            hover_bg = QColor(33, 136, 56)  # Darker green
            disabled_bg = QColor(160, 160, 160)  # Grey
        elif button_type == "danger":
            # Red for destructive actions
            bg = QColor(220, 53, 69)  # Red
            hover_bg = QColor(200, 35, 51)  # Darker red
            disabled_bg = QColor(160, 160, 160)  # Grey
        elif button_type == "info":
            # Blue for informational actions
            bg = QColor(0, 120, 215)  # Blue
            hover_bg = QColor(0, 95, 184)  # Darker blue
            disabled_bg = QColor(160, 160, 160)  # Grey
        elif button_type == "warning":
            # Orange for warning actions
            bg = QColor(255, 152, 0)  # Orange
            hover_bg = QColor(230, 126, 34)  # Darker orange
            disabled_bg = QColor(160, 160, 160)  # Grey
        else:  # default - use theme colors
            bg = base_bg
            hover_bg = highlight
            disabled_bg = QColor(160, 160, 160)
        
        # Text color - white for dark buttons, black for light buttons
        text_color = QColor(255, 255, 255) if bg.lightness() < 128 else QColor(0, 0, 0)
        
        return f"""
            QPushButton {{
                background-color: rgb({bg.red()}, {bg.green()}, {bg.blue()});
                color: rgb({text_color.red()}, {text_color.green()}, {text_color.blue()});
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgb({hover_bg.red()}, {hover_bg.green()}, {hover_bg.blue()});
            }}
            QPushButton:disabled {{
                background-color: rgb({disabled_bg.red()}, {disabled_bg.green()}, {disabled_bg.blue()});
            }}
        """

    def clear_all(self):
        self.current_csv = None
        self.file_label.setText("No file selected")
        self.ci_input.clear()
        self.wt_input.clear()
        self.mid_combo.setCurrentIndex(-1)
        self.selected_mid = ""
        self.table.setRowCount(0)
        self.process_btn.setEnabled(False)
        self.process_btn.setText("Process Invoice")  # Reset button text
        self.progress.setVisible(False)
        self.invoice_check_label.setText("No file loaded")
        self.csv_total_value = 0.0
        self.edit_values_btn.setVisible(False)
        self.bottom_status.setText("Cleared")
        self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0;")
        logger.info("Process tab cleared")

    def browse_file(self):
        # Simple profile check without focus manipulation
        current_profile = self.profile_combo.currentText()
        if not current_profile or current_profile == "-- Select Profile --":
            QMessageBox.warning(
                self,
                "Mapping Profile Required",
                "<b>You must select a mapping profile before loading a shipment file.</b><br><br>"
                "Please choose one from the <b>Saved Profiles</b> dropdown.",
                QMessageBox.Ok
            )
            # Re-enable input fields after modal dialog
            self._enable_input_fields()
            return
        # -------------------------------------------------------------------------

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Shipment File", str(INPUT_DIR), "CSV/Excel (*.csv *.xlsx)"
        )
        if not path:
            return

        self.current_csv = path
        self.file_label.setText(Path(path).name)
        
        # Clear previous processing state when loading new file
        self.last_processed_df = None
        self.table.setRowCount(0)

        try:
            col_map = {v: k for k, v in self.shipment_mapping.items()}
            if Path(path).suffix.lower() == ".xlsx":
                df = pd.read_excel(path, dtype=str)
            else:
                df = pd.read_csv(path, dtype=str)
            df = df.rename(columns=col_map)

            if 'value_usd' in df.columns:
                total = pd.to_numeric(df['value_usd'], errors='coerce').sum()
                self.csv_total_value = round(total, 2)
                self.update_invoice_check()  # This will control button state
        except Exception as e:
            logger.error(f"browse_file value read failed: {e}")
            self.invoice_check_label.setText("Could not read value column")

        logger.info(f"Loaded: {Path(path).name}")

        # Force focus to ci_input and ensure keyboard input works
        QApplication.processEvents()  # Process any pending events first
        self.ci_input.setFocus(Qt.OtherFocusReason)
        self.ci_input.activateWindow()
        logger.info(f"Set focus to ci_input: hasFocus={self.ci_input.hasFocus()}")
        
    def update_invoice_check(self):
        # Guard against re-entrancy
        if getattr(self, '_updating_invoice_check', False):
            return
        self._updating_invoice_check = True

        try:
            if not self.current_csv:
                self.invoice_check_label.setText("No file loaded")
                # Gold color in dark theme (text-shadow not supported in Qt)
                if hasattr(self, 'current_theme') and self.current_theme in ["Fusion (Dark)", "Ocean", "Teal Professional"]:
                    self.invoice_check_label.setStyleSheet("background:transparent; color: gold; font-weight:bold; font-size:7pt; padding:3px;")
                else:
                    self.invoice_check_label.setStyleSheet("background:transparent; color: #A4262C; font-weight:bold; font-size:7pt; padding:3px;")
                self.edit_values_btn.setVisible(False)
                return

            user_text = self.ci_input.text().replace(',', '').strip()
            try:
                user_val = float(user_text) if user_text else 0.0
            except:
                user_val = 0.0

            diff = abs(user_val - self.csv_total_value)
            threshold = 0.01
            
            # Update the invoice check label and Edit Values button
            if user_val == 0.0:
                self.invoice_check_label.setText(f"CSV Total: ${self.csv_total_value:,.2f}")
                self.invoice_check_label.setStyleSheet("background:#0078D4; color:white; font-weight:bold; font-size:7pt; padding:3px;")
                self.edit_values_btn.setVisible(False)
            elif diff <= threshold:
                self.invoice_check_label.setText(f"✓ Match: ${self.csv_total_value:,.2f}")
                self.invoice_check_label.setStyleSheet("background:#107C10; color:white; font-weight:bold; font-size:7pt; padding:3px;")
                self.edit_values_btn.setVisible(False)
            else:
                # Values don't match - show comparison and Edit Values button
                self.invoice_check_label.setText(
                    f"CSV Total: ${self.csv_total_value:,.2f}\n"
                    f"Difference: ${diff:,.2f}"
                )
                self.invoice_check_label.setStyleSheet("background:#ff9800; color:white; font-weight:bold; font-size:7pt; padding:3px;")
                # Show Edit Values button only if haven't processed yet
                if self.last_processed_df is None:
                    self.edit_values_btn.setVisible(True)
                else:
                    self.edit_values_btn.setVisible(False)
            
            # Button state control - require invoice check match before processing
            has_weight = bool(self.wt_input.text().strip())
            has_ci_value = bool(user_text)
            has_mid = bool(self.selected_mid)
            values_match = diff <= threshold

            # Changed from >= 2 to >= 1 to allow profiles with minimal column mappings
            if self.current_csv and len(self.shipment_mapping) >= 1:
                if self.last_processed_df is None:
                    # Haven't processed yet - require weight, CI value, AND invoice values must match
                    # MID can be selected later, so not required for initial processing
                    if has_weight and has_ci_value and values_match:
                        self.process_btn.setEnabled(True)
                        self.process_btn.setText("Process Invoice")
                    else:
                        self.process_btn.setEnabled(False)
                        self.process_btn.setText("Process Invoice")
                else:
                    # Already processed - button becomes Export, only enabled when values match
                    if values_match:
                        self.process_btn.setEnabled(True)
                        self.process_btn.setText("Export Worksheet")
                    else:
                        self.process_btn.setEnabled(False)
                        self.process_btn.setText("Export Worksheet")

            # Always ensure input fields stay enabled
            self._enable_input_fields()
        finally:
            self._updating_invoice_check = False
    def select_input_folder(self, display_widget=None):
        global INPUT_DIR, PROCESSED_DIR
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder", str(INPUT_DIR))
        if folder:
            INPUT_DIR = Path(folder)
            PROCESSED_DIR = INPUT_DIR / "Processed"
            PROCESSED_DIR.mkdir(exist_ok=True)
            if display_widget:
                if isinstance(display_widget, QPlainTextEdit):
                    display_widget.setPlainText(str(INPUT_DIR))
                else:
                    display_widget.setText(str(INPUT_DIR))
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config VALUES ('input_dir', ?)", (str(INPUT_DIR),))
            conn.commit()
            conn.close()
            self.status.setText(f"Input folder: {INPUT_DIR}")
            self.refresh_input_files()

    def select_output_folder(self, display_widget=None):
        global OUTPUT_DIR
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(OUTPUT_DIR))
        if folder:
            OUTPUT_DIR = Path(folder)
            OUTPUT_DIR.mkdir(exist_ok=True)
            if display_widget:
                if isinstance(display_widget, QPlainTextEdit):
                    display_widget.setPlainText(str(OUTPUT_DIR))
                else:
                    display_widget.setText(str(OUTPUT_DIR))
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config VALUES ('output_dir', ?)", (str(OUTPUT_DIR),))
            conn.commit()
            conn.close()
            self.status.setText(f"Output folder: {OUTPUT_DIR}")
            self.refresh_exported_files()

    def select_processed_pdf_folder(self, display_widget=None):
        global PROCESSED_PDF_DIR
        folder = QFileDialog.getExistingDirectory(self, "Select Processed PDF Folder", str(PROCESSED_PDF_DIR))
        if folder:
            PROCESSED_PDF_DIR = Path(folder)
            PROCESSED_PDF_DIR.mkdir(exist_ok=True)
            if display_widget:
                if isinstance(display_widget, QPlainTextEdit):
                    display_widget.setPlainText(str(PROCESSED_PDF_DIR))
                else:
                    display_widget.setText(str(PROCESSED_PDF_DIR))
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config VALUES ('processed_pdf_dir', ?)", (str(PROCESSED_PDF_DIR),))
            conn.commit()
            conn.close()
            self.status.setText(f"Processed PDF folder: {PROCESSED_PDF_DIR}")
            logger.info(f"Processed PDF folder changed to: {PROCESSED_PDF_DIR}")

    def move_pdf_to_processed(self, pdf_path):
        """
        Move a processed PDF file to the Processed PDF folder.

        Args:
            pdf_path (str or Path): Path to the PDF file to move

        Returns:
            bool: True if move was successful, False otherwise
        """
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logger.warning(f"PDF file not found for processing: {pdf_path}")
                return False

            # Get destination path
            dest_path = PROCESSED_PDF_DIR / pdf_file.name

            # Handle duplicate filenames
            if dest_path.exists():
                base_name = pdf_file.stem
                ext = pdf_file.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = PROCESSED_PDF_DIR / f"{base_name}_{counter}{ext}"
                    counter += 1

            # Move the file
            shutil.move(str(pdf_file), str(dest_path))
            logger.info(f"Moved processed PDF to: {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to move PDF to processed folder: {e}")
            return False

    def load_file_as_dataframe(self, file_path):
        """Load CSV or Excel file and return as DataFrame"""
        file_path_str = str(file_path)
        if file_path_str.lower().endswith('.xlsx') or file_path_str.lower().endswith('.xls'):
            return pd.read_excel(file_path_str, dtype=str, keep_default_na=False).fillna("")
        else:
            return pd.read_csv(file_path_str, dtype=str, keep_default_na=False).fillna("")

    def start_processing_with_editable_preview(self):
        if not self.current_csv:
            return
        # Process with user's entered CI value, generate preview for editing
        # Do NOT change the CI input - keep user's entered value
        self.process_btn.setText("Export Worksheet")
        self.process_btn.setEnabled(False)
        self.start_processing()

    def start_processing(self):
        if not self.current_csv:
            QMessageBox.critical(self, "Error", "Please select a file")
            return
        if len(self.shipment_mapping) < 2:
            QMessageBox.critical(self, "Error", "Map Part Number and Value USD")
            return
        
        # Verify Net Weight is entered
        wt_text = self.wt_input.text().strip()
        if not wt_text:
            self.wt_input.setStyleSheet("border: 2px solid #ff4444; background-color: #ffebee;")
            QTimer.singleShot(1200, lambda: self.wt_input.setStyleSheet(""))
            self.wt_input.setFocus()
            QMessageBox.warning(self, "Net Weight Required", "Please enter the Net Weight (kg) before processing.")
            return
        
        try:
            wt_val = float(wt_text.replace(',', ''))
            if wt_val <= 0:
                raise ValueError()
        except:
            self.wt_input.setStyleSheet("border: 2px solid #ff4444; background-color: #ffebee;")
            QTimer.singleShot(1200, lambda: self.wt_input.setStyleSheet(""))
            self.wt_input.setFocus()
            QMessageBox.warning(self, "Invalid Net Weight", "Please enter a valid Net Weight greater than zero.")
            return
        
        # Verify MID is selected
        if not self.selected_mid:
            self.mid_combo.setStyleSheet("border: 2px solid #ff4444; background-color: #ffebee;")
            QTimer.singleShot(1200, lambda: self.mid_combo.setStyleSheet(""))
            self.mid_combo.setFocus()
            QMessageBox.warning(self, "MID Required", "Please select a MID (Melt ID) before processing.")
            return

        self.process_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status.setText("Processing...")

        # Directly process the CSV/Excel file synchronously (single-threaded)
        try:
            self.status.setText("Loading file...")
            df = self.load_file_as_dataframe(self.current_csv)
            vr = Path(self.current_csv).stem
            col_map = {v:k for k,v in self.shipment_mapping.items()}
            df = df.rename(columns=col_map)
            if not {'part_number','value_usd'}.issubset(df.columns):
                self.status.setText("Missing Part Number or Value USD")
                return
            def safe_float(text):
                if pd.isna(text) or text == "": return 0.0
                try:
                    return float(str(text).replace(',', '').strip())
                except:
                    return 0.0
            df['value_usd'] = pd.to_numeric(df['value_usd'], errors='coerce').fillna(0)
            csv_total = df['value_usd'].sum()
            user_ci = safe_float(self.ci_input.text())
            wt = safe_float(self.wt_input.text())
            if wt <= 0:
                self.status.setText("Net Weight must be greater than zero")
                return
            # Invoice diff
            self.handle_invoice_diff(csv_total, user_ci)
            conn = sqlite3.connect(str(DB_PATH))
            parts = pd.read_sql("SELECT part_number, hts_code, steel_ratio, non_steel_ratio FROM parts_master", conn)
            conn.close()
            df = df.merge(parts, on='part_number', how='left', suffixes=('', '_master'))
            if 'hts_code_master' in df.columns:
                df['hts_code'] = df['hts_code'].fillna(df['hts_code_master'])
            else:
                df['hts_code'] = df['hts_code'].fillna('')
            df['steel_ratio'] = pd.to_numeric(df['steel_ratio'], errors='coerce').fillna(1.0)
            df['non_steel_ratio'] = pd.to_numeric(df['non_steel_ratio'], errors='coerce').fillna(0.0)
            missing = df[
                (df['hts_code'].isnull() | (df['hts_code'] == '')) |
                (df['value_usd'] == 0) |
                (df['steel_ratio'].isnull())
            ].copy()
            if not missing.empty:
                missing = missing[['part_number', 'hts_code', 'value_usd', 'steel_ratio']].copy()
                missing.columns = ['Part Number', 'HTS Code', 'Value USD', 'Sec 232 Ratio']
                missing = missing.fillna('')
                self.log_missing_data_warning(missing)
            self._process_with_complete_data(df, vr, user_ci, wt)
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self.status.setText(f"Processing failed: {str(e)}")

    def _process_with_complete_data(self, df, vr, user_ci, wt):
        """
        Process the DataFrame with complete data, calculate required fields, and update the preview table.
        This matches the provided working script for derivatives.
        """
        df = df.copy()

        # Steel/NonSteel ratios BEFORE calculating weight
        df['SteelRatio'] = pd.to_numeric(df.get('steel_ratio', 1.0), errors='coerce').fillna(1.0)
        df['NonSteelRatio'] = pd.to_numeric(df.get('non_steel_ratio', 0.0), errors='coerce').fillna(0.0)

        # Split rows by steel/non-steel content BEFORE calculating CalcWtNet
        original_row_count = len(df)
        expanded_rows = []
        for _, row in df.iterrows():
            steel_ratio = row['SteelRatio']
            non_steel_ratio = row['NonSteelRatio']
            original_value = row['value_usd']

            # Create non-steel portion row (if non_steel_ratio > 0)
            if non_steel_ratio > 0:
                non_steel_row = row.copy()
                non_steel_row['value_usd'] = original_value * non_steel_ratio
                non_steel_row['SteelRatio'] = 0.0  # 0% steel in this portion
                non_steel_row['NonSteelRatio'] = non_steel_ratio  # Keep original non-steel ratio
                expanded_rows.append(non_steel_row)

            # Create steel portion row (if steel_ratio > 0)
            if steel_ratio > 0:
                steel_row = row.copy()
                steel_row['value_usd'] = original_value * steel_ratio
                steel_row['SteelRatio'] = steel_ratio  # Keep original steel ratio
                steel_row['NonSteelRatio'] = non_steel_ratio  # Keep original non-steel ratio
                expanded_rows.append(steel_row)

        # Rebuild dataframe from expanded rows
        df = pd.DataFrame(expanded_rows).reset_index(drop=True)
        logger.info(f"Row expansion: {original_row_count} → {len(expanded_rows)} rows")

        # Now calculate CalcWtNet based on expanded rows
        total_value = df['value_usd'].sum()
        if total_value == 0:
            df['CalcWtNet'] = 0.0
        else:
            df['CalcWtNet'] = (df['value_usd'] / total_value) * wt

        # Set HTSCode and MID
        df['HTSCode'] = df.get('hts_code', '')
        mid = self.selected_mid if hasattr(self, 'selected_mid') else ''
        df['MID'] = mid
        melt = str(mid)[:2] if mid else ''

        # Derivative fields (exact 8-digit match, flag logic)
        dec_type_list = []
        country_melt_list = []
        country_cast_list = []
        prim_country_smelt_list = []
        prim_smelt_flag_list = []
        flag_list = []
        for _, r in df.iterrows():
            hts = r.get('hts_code', '')
            hts_clean = str(hts).replace('.', '').strip().upper()
            hts_8 = hts_clean[:8]
            hts_10 = hts_clean[:10]
            material, dec_type, smelt_flag = get_232_info(hts)
            # Only exact 8-digit match for derivatives
            dec_type_list.append(dec_type)
            country_melt_list.append(melt)
            country_cast_list.append(melt)
            prim_country_smelt_list.append(melt)
            prim_smelt_flag_list.append(smelt_flag)
            flag_list.append(f"232_{material}" if material else '')

        df['DecTypeCd'] = dec_type_list
        df['CountryofMelt'] = country_melt_list
        df['CountryOfCast'] = country_cast_list
        df['PrimCountryOfSmelt'] = prim_country_smelt_list
        df['PrimSmeltFlag'] = prim_smelt_flag_list
        df['_232_flag'] = flag_list

        # Rename columns for preview
        df['Product No'] = df['part_number']
        df['ValueUSD'] = df['value_usd']

        preview_cols = [
            'Product No','ValueUSD','HTSCode','MID','CalcWtNet','DecTypeCd',
            'CountryofMelt','CountryOfCast','PrimCountryOfSmelt','PrimSmeltFlag',
            'SteelRatio','NonSteelRatio','_232_flag'
        ]
        preview_df = df[preview_cols].copy()
        self.on_done(preview_df, vr, None)
    
    def start_processing_with_editable_preview(self):
        """Open the CSV file in default editor for user to edit directly"""
        if not self.current_csv:
            return
        
        try:
            # Open the CSV file with the default system application
            import subprocess
            if sys.platform == 'win32':
                os.startfile(self.current_csv)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', self.current_csv])
            else:  # linux
                subprocess.run(['xdg-open', self.current_csv])
            
            # Show message to user
            QMessageBox.information(
                self, 
                "Edit File", 
                f"Opening file for editing:\n{Path(self.current_csv).name}\n\n"
                "Edit the values, save the file, then return here.\n"
                "The CI Value input will be updated when you reload the file."
            )
            
            # Reload the file to get updated values
            self.reload_csv_values()
            
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")
    
    def reload_csv_values(self):
        """Reload CSV to recalculate total after external edits"""
        if not self.current_csv:
            return
        
        try:
            col_map = {v: k for k, v in self.shipment_mapping.items()}
            if Path(self.current_csv).suffix.lower() == ".xlsx":
                df = pd.read_excel(self.current_csv, dtype=str)
            else:
                df = pd.read_csv(self.current_csv, dtype=str)
            df = df.rename(columns=col_map)

            if 'value_usd' in df.columns:
                # Check for rows where value_usd is blank, empty, or zero
                original_count = len(df)
                df['value_usd'] = pd.to_numeric(df['value_usd'], errors='coerce')
                zero_rows_df = df[df['value_usd'].isna() | (df['value_usd'] == 0)]
                zero_count = len(zero_rows_df)
                
                removed_count = 0
                if zero_count > 0:
                    # Prompt user to confirm deletion
                    reply = QMessageBox.question(
                        self,
                        "Remove Zero Value Rows",
                        f"Found {zero_count} row(s) with blank or zero values.\n\n"
                        f"Do you want to remove these rows?\n\n"
                        f"• Yes: Remove rows and continue processing\n"
                        f"• No: Keep all rows and process as is",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Remove the zero value rows
                        df = df[df['value_usd'].notna() & (df['value_usd'] != 0)]
                        removed_count = original_count - len(df)
                        
                        # Save cleaned data back to file
                        if removed_count > 0:
                            # Rename back to original columns for saving
                            reverse_map = {k: v for k, v in self.shipment_mapping.items()}
                            save_df = df.rename(columns=reverse_map)
                            
                            if Path(self.current_csv).suffix.lower() == ".xlsx":
                                save_df.to_excel(self.current_csv, index=False)
                            else:
                                save_df.to_csv(self.current_csv, index=False)
                            
                            logger.info(f"Removed {removed_count} rows with blank/zero values")
                    else:
                        # User chose No - keep all rows
                        logger.info(f"User chose to keep {zero_count} row(s) with blank/zero values")
                
                # Calculate total
                total = df['value_usd'].sum()
                self.csv_total_value = round(total, 2)
                # Don't overwrite user's CI input - just update the check
                self.update_invoice_check()
                
                if removed_count > 0:
                    self.status.setText(f"File reloaded - Removed {removed_count} blank/zero rows")
                    self.status.setStyleSheet("background:#ff9800; color:white; font-weight:bold; padding:8px;")
                elif zero_count > 0:
                    self.status.setText(f"File reloaded - Kept {zero_count} blank/zero rows")
                    self.status.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:8px;")
                else:
                    self.status.setText("File reloaded - Check invoice values")
                    self.status.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:8px;")
        except Exception as e:
            logger.error(f"reload_csv_values failed: {e}")
            QMessageBox.warning(self, "Reload Error", f"Failed to reload values:\n{e}")

    def handle_invoice_diff(self, csv_sum, user_entered):
        # Display-only; enablement handled by update/check methods
        diff = abs(csv_sum - user_entered)
        threshold = 0.01
        if diff > threshold:
            self.invoice_check_label.setText(
                f": CSV = ${csv_sum:,.2f} | "
                f"Entered = ${user_entered:,.2f} | Diff = ${diff:,.2f}"
            )
            self.invoice_check_label.setStyleSheet("background:#A4262C; color:white; font-weight:bold; font-size:7pt; padding:3px;")
        else:
            self.invoice_check_label.setText(f"Match: ${csv_sum:,.2f}")
            self.invoice_check_label.setStyleSheet("background:#107C10; color:white; font-weight:bold; font-size:7pt; padding:3px;")

    def save_edited_values_and_process(self):
        if not hasattr(self, 'editable_invoice_df'):
            return

        try:
            updated = 0
            for row in range(self.missing_table.rowCount()):
                value_item = self.missing_table.item(row, 1)
                if value_item:
                    clean_val = value_item.text().replace('$', '').replace(',', '').strip()
                    try:
                        new_val = float(clean_val)
                        self.editable_invoice_df.at[row, 'value_usd'] = new_val
                        updated += 1
                    except:
                        self.editable_invoice_df.at[row, 'value_usd'] = 0.0

            # Save back to original file
            if self.editable_invoice_path.suffix.lower() == ".xlsx":
                self.editable_invoice_df.to_excel(self.editable_invoice_path, index=False)
            else:
                self.editable_invoice_df.to_csv(self.editable_invoice_path, index=False)

            # Update totals and UI
            new_total = float(self.editable_invoice_df['value_usd'].sum())
            self.ci_input.setText(f"{new_total:,.2f}")
            self.csv_total_value = round(new_total, 2)
            self.update_invoice_check()

            QMessageBox.information(self, "Success", 
                f"Updated {updated} line values!\n\n"
                f"New invoice total: ${new_total:,.2f}\n\n"
                "Starting processing...")

            # Hide button and reprocess
            self.save_and_process_btn.setVisible(False)
            self.start_processing()

        except Exception as e:
            logger.error(f"save_edited_values_and_process failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save edits:\n{e}")

    # ====================== MISSING DATA HANDLER ======================
    def log_missing_data_warning(self, missing_df):
        """Log missing data as warning but allow processing to continue"""
        # Note: missing_df has 'Part Number' column (with capital letters)
        part_col = 'Part Number' if 'Part Number' in missing_df.columns else 'part_number'
        parts_list = ", ".join(str(p) for p in missing_df[part_col].tolist()[:10])
        if len(missing_df) > 10:
            parts_list += f" ... and {len(missing_df) - 10} more"
        
        logger.warning(f"Found {len(missing_df)} parts with missing data: {parts_list}")
        self.status.setText(f"⚠ Warning: {len(missing_df)} parts have missing data - review in preview")
        self.status.setStyleSheet("background:#f7bfa1; color:white; font-weight:bold; padding:8px;")

    def on_worker_error(self, msg):
        self.progress.setVisible(False)
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)
        self.status.setText("Error")
        self.status.setStyleSheet("background:#dd6e74; color:white; font-weight:bold;")

    def on_done(self, df, vr, fname):
        # Populate preview with editable Value column; export later when totals match
        self.progress.setVisible(False)
        self.last_processed_df = df.copy()
        self.last_output_filename = f"Upload_Sheet_{vr}_{datetime.now():%Y%m%d_%H%M}.xlsx"

        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)  # Disable sorting while populating
        self.table.setRowCount(len(df))
        has_232 = False
        for i, r in df.iterrows():
            flag = r.get('_232_flag', '')
            if flag:
                has_232 = True

            value_item = QTableWidgetItem(f"{r['ValueUSD']:,.2f}")
            value_item.setData(Qt.UserRole, r['ValueUSD'])

            # For steel rows (SteelRatio > 0), show 0.0% in NonSteelRatio column
            steel_ratio_val = r.get('SteelRatio', 0.0) or 0.0
            non_steel_ratio_val = r.get('NonSteelRatio', 0.0) or 0.0
            is_steel_row = steel_ratio_val > 0.0

            if is_steel_row and non_steel_ratio_val > 0:
                non_steel_display = "0.0%"  # Show 0.0% for steel rows
            else:
                non_steel_display = f"{non_steel_ratio_val*100:.1f}%" if non_steel_ratio_val > 0 else ""

            items = [
                QTableWidgetItem(str(r['Product No'])),
                value_item,
                QTableWidgetItem(r.get('HTSCode','')),
                QTableWidgetItem(r.get('MID','')),
                QTableWidgetItem(str(int(round(r['CalcWtNet'])))),
                QTableWidgetItem(r.get('DecTypeCd','')),
                QTableWidgetItem(r.get('CountryofMelt','')),
                QTableWidgetItem(r.get('CountryOfCast','')),
                QTableWidgetItem(r.get('PrimCountryOfSmelt','')),
                QTableWidgetItem(r.get('PrimSmeltFlag','')),
                QTableWidgetItem(f"{steel_ratio_val*100:.1f}%"),
                QTableWidgetItem(non_steel_display),
                QTableWidgetItem(flag)
            ]

            # Make all items editable except 232%, Non-232%, and 232 Status
            for idx, item in enumerate(items):
                if idx not in [10, 11, 12]:  # Not 232%, Non-232%, 232 Status
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)

            # Set font colors: 232 content rows charcoal gray, non-232 rows red
            row_color = self.get_preview_row_color(is_steel_row)
            for item in items:
                item.setForeground(row_color)
                f = item.font()
                f.setBold(False)
                item.setFont(f)
                item.setTextAlignment(Qt.AlignCenter)  # Center text in all columns

            for j, it in enumerate(items):
                self.table.setItem(i, j, it)

        self.table.setSortingEnabled(True)  # Re-enable sorting after populating
        self.table.blockSignals(False)
        self.table.itemChanged.connect(self.on_preview_value_edited)
        self.recalculate_total_and_check_match()

        # if has_232:
        #     self.status.setText("SECTION 232 ITEMS • EDIT VALUES • EXPORT WHEN READY")
        #     self.status.setStyleSheet("background:#A4262C; color:white; font-weight:bold; font-size:16pt; padding:10px;")
        # else:
        #     self.status.setText("Edit values • Export when total matches")
        #     self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0;")

    def setup_import_tab(self):
        layout = QVBoxLayout(self.tab_import)
        title = QLabel("<h2>Parts Import from CSV/Excel</h2><p>Drag & drop columns to map fields</p>")
        title.setAlignment(Qt.AlignCenter)
        # Lighten font in dark mode
        if self.current_theme and "dark" in self.current_theme.lower():
            title.setStyleSheet("color: #e0e0e0;")
        else:
            title.setStyleSheet("color: #333;")
        layout.addWidget(title)

        # Buttons at top
        button_widget = QWidget()
        btn_layout = QHBoxLayout(button_widget)
        btn_load = QPushButton("Load CSV/Excel File")
        btn_load.setStyleSheet(self.get_button_style("info"))
        btn_load.clicked.connect(self.load_csv_for_import)
        btn_reset = QPushButton("Reset Mapping")
        btn_reset.setStyleSheet(self.get_button_style("danger"))
        btn_reset.clicked.connect(self.reset_import_mapping)
        btn_import = QPushButton("Import Now")
        btn_import.setFixedSize(100, 28)
        btn_import.setStyleSheet(self.get_button_style("success") + "QPushButton { font-size:10pt; padding:4px; }")
        btn_import.clicked.connect(self.start_parts_import)
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_import)
        layout.addWidget(button_widget)

        # Main drag/drop area with scroll
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(20)

        left = QGroupBox("CSV/Excel Columns - Drag")
        left_outer_layout = QVBoxLayout()
        
        # Add scroll area for columns
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        left_layout = QVBoxLayout(scroll_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        self.drag_labels = []
        # Don't add stretch here - it will be added after labels are loaded
        
        scroll_area.setWidget(scroll_widget)
        left_outer_layout.addWidget(scroll_area)
        left.setLayout(left_outer_layout)
        
        # Store reference to left_layout for adding labels later
        self.import_left_layout = left_layout

        right = QGroupBox("Available Fields - Drop Here")
        right_outer_layout = QVBoxLayout()
        
        # Add scroll area for drop targets
        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        right_scroll_widget = QWidget()
        right_layout = QFormLayout(right_scroll_widget)
        right_layout.setLabelAlignment(Qt.AlignRight)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        self.import_targets = {}
        fields = {
            "part_number": "Part Number *",
            "hts_code": "HTS Code *",
            "mid": "MID *",
            "steel_ratio": "Sec 232 Content Ratio *",
            "client_code": "Client Code"
        }
        drop_labels = {
            "steel_ratio": "Sec232 ratio"
        }
        for key, name in fields.items():
            drop_label = drop_labels.get(key)
            target = DropTarget(key, name, drop_label)
            target.dropped.connect(self.on_import_drop)
            is_required = "*" in name
            label_text = name.replace(" *", "")
            if is_required:
                label = QLabel(f"{label_text}: <span style='color:red;'>*</span>")
            else:
                label = QLabel(f"{label_text}:")
            right_layout.addRow(label, target)
            self.import_targets[key] = target
        
        right_scroll_area.setWidget(right_scroll_widget)
        right_outer_layout.addWidget(right_scroll_area)
        right.setLayout(right_outer_layout)

        main_layout.addWidget(left, 1)
        main_layout.addWidget(right, 2)
        layout.addWidget(main_widget, 1)
        self.import_widget = main_widget

        self.import_csv_path = None
        self.tab_import.setLayout(layout)

    def load_csv_for_import_from_path(self, path):
        """Load CSV/Excel file from a given path (used by drag-and-drop)"""
        if not path:
            return
        self.import_csv_path = path
        try:
            # Handle both CSV and Excel files
            if path.lower().endswith('.xlsx'):
                df = pd.read_excel(path, nrows=0, dtype=str)
            else:
                df = pd.read_csv(path, nrows=0, dtype=str)
            cols = list(df.columns)

            # Clear previous mappings when loading new file
            for target in self.import_targets.values():
                target.column_name = None
                target.setText(f"Drop {target.field_key} here")
                target.setProperty("occupied", False)
                target.style().unpolish(target)
                target.style().polish(target)

            # Clear existing labels
            for label in self.drag_labels:
                label.setParent(None)
                label.deleteLater()
            self.drag_labels = []
            
            # Add new labels directly to the layout
            for col in cols:
                lbl = DraggableLabel(col)
                self.import_left_layout.addWidget(lbl)
                self.drag_labels.append(lbl)

            # Add stretch at the end to push labels to the top
            self.import_left_layout.addStretch()

            # Try to restore saved mappings if they match columns in the new file
            if MAPPING_FILE.exists():
                try:
                    saved_mapping = json.loads(MAPPING_FILE.read_text())
                    # Restore mappings only if the column exists in the new file
                    for field_key, column_name in saved_mapping.items():
                        if column_name in cols and field_key in self.import_targets:
                            target = self.import_targets[field_key]
                            target.column_name = column_name
                            target.setText(f"{field_key}\n<- {column_name}")
                            target.setProperty("occupied", True)
                            target.style().unpolish(target)
                            target.style().polish(target)
                            logger.info(f"Restored mapping: {field_key} <- {column_name}")
                except Exception as e:
                    logger.warning(f"Failed to restore saved mappings: {e}")

            logger.info(f"Loaded CSV for import (drag-drop): {Path(path).name}")
            self.bottom_status.setText(f"CSV loaded: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read CSV:\n{e}")
    
    def load_csv_for_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV/Excel", str(INPUT_DIR), "CSV/Excel Files (*.csv *.xlsx)")
        if not path: return
        self.load_csv_for_import_from_path(path)
    
    def load_csv_for_import_old(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV/Excel", str(INPUT_DIR), "CSV/Excel Files (*.csv *.xlsx)")
        if not path: return
        self.import_csv_path = path
        try:
            # Handle both CSV and Excel files
            if path.lower().endswith('.xlsx'):
                df = pd.read_excel(path, nrows=0, dtype=str)
            else:
                df = pd.read_csv(path, nrows=0, dtype=str)
            cols = list(df.columns)
            for label in self.drag_labels:
                label.setParent(None)
            self.drag_labels = []
            left_layout = self.import_widget.layout().itemAt(0).widget().layout()
            for col in cols:
                lbl = DraggableLabel(col)
                left_layout.insertWidget(left_layout.count()-1, lbl)
                self.drag_labels.append(lbl)
            logger.info(f"Loaded CSV for import: {Path(path).name}")
            self.bottom_status.setText(f"CSV loaded: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read CSV:\n{e}")

    def reset_import_mapping(self):
        if QMessageBox.question(self, "Reset", "Clear all field mappings and column list?") != QMessageBox.Yes:
            return
        
        # Clear drop targets (right side)
        for target in self.import_targets.values():
            target.column_name = None
            target.setText(f"Drop {target.field_key} here")
            target.setProperty("occupied", False)
            target.style().unpolish(target); target.style().polish(target)
        
        # Clear drag labels (left side - CSV/Excel columns)
        for label in self.drag_labels:
            label.setParent(None)
            label.deleteLater()
        self.drag_labels = []
        
        # Clear the file path
        self.import_csv_path = None
        
        # Delete mapping file if it exists
        if MAPPING_FILE.exists():
            MAPPING_FILE.unlink()
        
        logger.info("Import mapping and column list reset")
        self.bottom_status.setText("Import mapping cleared")

    def on_import_drop(self, field_key, column_name):
        for k, t in self.import_targets.items():
            if t.column_name == column_name and k != field_key:
                t.column_name = None
                t.setText(f"Drop {t.field_key} here")
                t.setProperty("occupied", False)
                t.style().unpolish(t); t.style().polish(t)

        # Update the target that received the drop
        target = self.import_targets[field_key]
        target.column_name = column_name
        target.setText(f"{field_key}\n<- {column_name}")
        target.setProperty("occupied", True)
        target.style().unpolish(target); target.style().polish(target)

        self.current_mapping = getattr(self, 'current_mapping', {})
        self.current_mapping[field_key] = column_name
        MAPPING_FILE.write_text(json.dumps(self.current_mapping, indent=2))

    def start_parts_import(self):
        if not self.import_csv_path:
            QMessageBox.warning(self, "No File", "Load a CSV or Excel file first")
            return
        mapping = {k: t.column_name for k, t in self.import_targets.items() if t.column_name}
        required_fields = ['part_number','hts_code','mid','steel_ratio']
        missing = [f for f in required_fields if f not in mapping]
        if missing:
            field_names = {
                'part_number': 'Part Number',
                'hts_code': 'HTS Code',
                'mid': 'MID',
                'steel_ratio': 'Sec 232 Content Ratio'
            }
            missing_names = [field_names[f] for f in missing]
            QMessageBox.warning(self, "Incomplete Mapping", 
                f"Please map all mandatory fields:\n\n{', '.join(missing_names)}")
            return
        self.status.setText("Importing parts...")
        # Directly import parts synchronously (single-threaded)
        try:
            self.status.setText("Importing parts...")
            # Handle both CSV and Excel files
            if self.import_csv_path.lower().endswith('.xlsx'):
                df = pd.read_excel(self.import_csv_path, dtype=str, keep_default_na=False)
            else:
                df = pd.read_csv(self.import_csv_path, dtype=str, keep_default_na=False)
            df = df.fillna("").rename(columns=str.strip)
            col_map = {v: k for k, v in mapping.items()}
            df = df.rename(columns=col_map)
            required = ['part_number','hts_code','mid','steel_ratio']
            missing = [f for f in required if f not in df.columns]
            if missing:
                QMessageBox.critical(self, "Error", f"Missing required fields: {', '.join(missing)}")
                self.status.setText("Import failed")
                return
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            updated = inserted = 0
            now = datetime.now().isoformat()
            for _, r in df.iterrows():
                part = str(r.get('part_number', '')).strip()
                if not part: continue
                desc = str(r.get('description', r.get('Description', ''))).strip()
                hts = str(r.get('hts_code', '')).strip()
                origin = str(r.get('country_origin', '')).strip().upper()[:2]
                mid = str(r.get('mid', '')).strip()
                # Get client_code if it was mapped, otherwise empty string
                client_code = str(r.get('client_code', '')).strip() if 'client_code' in df.columns else ""
                steel_str = str(r.get('steel_ratio', r.get('Sec 232 Content Ratio', r.get('Steel %', '')))).strip()
                try:
                    if steel_str:
                        steel_ratio = float(steel_str)
                        if steel_ratio > 1.0: steel_ratio /= 100.0
                        steel_ratio = max(0.0, min(1.0, steel_ratio))
                    else:
                        steel_ratio = 0.0  # Default to 0% steel if no ratio provided
                    non_steel_ratio = 1.0 - steel_ratio
                except:
                    steel_ratio = 0.0
                    non_steel_ratio = 1.0
                c.execute("""INSERT INTO parts_master (part_number, description, hts_code, country_origin, mid, client_code, steel_ratio, non_steel_ratio, last_updated)
                          VALUES (?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(part_number) DO UPDATE SET
                          description=excluded.description, hts_code=excluded.hts_code,
                          country_origin=excluded.country_origin, mid=excluded.mid,
                          client_code=excluded.client_code, steel_ratio=excluded.steel_ratio,
                          non_steel_ratio=excluded.non_steel_ratio, last_updated=excluded.last_updated""",
                          (part, desc, hts, origin, mid, client_code, steel_ratio, non_steel_ratio, now))
                if c.rowcount:
                    inserted += 1 if conn.total_changes > updated+inserted else 0
                    updated += 1 if conn.total_changes == updated+inserted else 0
            conn.commit(); conn.close()
            QMessageBox.information(self, "Success", f"Imported!\nUpdated: {updated}\nInserted: {inserted}")
            
            # Only refresh parts table if Parts View tab has been initialized
            if hasattr(self, 'parts_table'):
                self.refresh_parts_table()
            
            self.load_available_mids()
            self.bottom_status.setText("Import complete")
        except Exception as e:
            logger.error(f"Import failed: {e}")
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
            self.status.setText("Import failed")

    def setup_shipment_mapping_tab(self):
        logger.debug(f"setup_shipment_mapping_tab called - tab_shipment_map={self.tab_shipment_map}")
        layout = QVBoxLayout(self.tab_shipment_map)
        title = QLabel("<h2>Invoice Mapping Profiles</h2><p>Save and load column mappings</p>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Buttons at top - wrap in widget for proper rendering
        top_bar_widget = QWidget()
        top_bar = QHBoxLayout(top_bar_widget)
        self.profile_combo_map = QComboBox()
        self.profile_combo_map.setMinimumWidth(300)
        self.profile_combo_map.currentTextChanged.connect(self.load_selected_profile_full)
        top_bar.addWidget(QLabel("Saved Profiles:"))
        top_bar.addWidget(self.profile_combo_map)

        # Load profiles immediately after creating the combo box
        self.load_mapping_profiles()

        btn_save = QPushButton("Save Current Mapping As...")
        btn_save.setStyleSheet(self.get_button_style("success"))
        btn_save.clicked.connect(self.save_mapping_profile)
        btn_delete = QPushButton("Delete Profile")
        btn_delete.setStyleSheet(self.get_button_style("danger"))
        btn_delete.clicked.connect(self.delete_mapping_profile)
        btn_load_csv = QPushButton("Load Invoice File")
        btn_load_csv.setStyleSheet(self.get_button_style("info"))
        btn_load_csv.clicked.connect(self.load_csv_for_shipment_mapping)
        btn_reset = QPushButton("Reset Current")
        btn_reset.setStyleSheet(self.get_button_style("danger"))
        btn_reset.clicked.connect(self.reset_current_mapping)
        top_bar.addWidget(btn_load_csv)
        top_bar.addWidget(btn_reset)
        top_bar.addWidget(btn_save)
        top_bar.addWidget(btn_delete)
        top_bar.addStretch()
        layout.addWidget(top_bar_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.shipment_widget = QWidget()
        self.shipment_layout = QHBoxLayout(self.shipment_widget)

        left = QGroupBox("Your CSV Columns - Drag")
        left_layout = QVBoxLayout()
        self.shipment_drag_labels = []
        left_layout.addStretch()
        left.setLayout(left_layout)

        right = QGroupBox("Required Fields - Drop")
        right_layout = QFormLayout()
        right_layout.setLabelAlignment(Qt.AlignRight)
        self.shipment_targets = {}
        fields = {
            "part_number": "Part Number *",
            "value_usd": "Value USD *"
        }
        for key, name in fields.items():
            target = DropTarget(key, name)
            target.dropped.connect(self.on_shipment_drop)
            right_layout.addRow(f"{name}:", target)
            self.shipment_targets[key] = target
        right.setLayout(right_layout)

        self.shipment_layout.addWidget(left,1); self.shipment_layout.addWidget(right,1)
        scroll_layout.addWidget(self.shipment_widget)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
        self.tab_shipment_map.setLayout(layout)

    def load_csv_for_shipment_mapping(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Invoice File",
            str(INPUT_DIR),
            "All Supported (*.csv *.xlsx *.pdf);;CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )
        if not path: return
        try:
            # Determine file type and extract data accordingly
            file_ext = Path(path).suffix.lower()

            if file_ext == '.pdf':
                # Check if PDF is scanned (image-based) or digital (text-based)
                if OCR_AVAILABLE and is_scanned_pdf(path):
                    # Scanned PDF: use OCR extraction
                    logger.info(f"Scanned PDF detected: {Path(path).name} - using OCR")
                    df, metadata = extract_from_scanned_invoice(path)

                    # Show OCR confidence and warnings to user
                    confidence = metadata.get('success', False)
                    if confidence:
                        QMessageBox.information(
                            self,
                            "OCR Extraction Complete",
                            f"Successfully extracted {len(df)} rows from scanned invoice.\n\n"
                            f"Note: Please review the extracted data carefully as OCR accuracy may vary.\n"
                            f"You can adjust the column mappings before processing."
                        )
                        # Move PDF to processed folder after successful OCR extraction
                        self.move_pdf_to_processed(path)
                else:
                    # Digital PDF: use pdfplumber table extraction
                    df = self.extract_pdf_table(path)
                    logger.info(f"Digital PDF detected: {Path(path).name} - using table extraction")
                    # Move PDF to processed folder after successful extraction
                    self.move_pdf_to_processed(path)
            elif file_ext == '.xlsx':
                df = pd.read_excel(path, nrows=0, dtype=str)
            else:  # .csv
                df = pd.read_csv(path, nrows=0, dtype=str)

            cols = list(df.columns)

            # Clear existing labels
            for label in self.shipment_drag_labels:
                label.setParent(None)
            self.shipment_drag_labels = []

            # Add new labels from extracted columns
            left_layout = self.shipment_widget.layout().itemAt(0).widget().layout()
            for col in cols:
                lbl = DraggableLabel(col)
                left_layout.insertWidget(left_layout.count()-1, lbl)
                self.shipment_drag_labels.append(lbl)

            # Determine file type for status message
            file_type = "PDF" if file_ext == '.pdf' else ("Excel" if file_ext == '.xlsx' else "CSV")
            logger.info(f"{file_type} file loaded for mapping: {Path(path).name}")
            self.status.setText(f"{file_type} file loaded: {Path(path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read file:\n{e}")
            logger.error(f"File loading failed: {str(e)}")

    def extract_pdf_table(self, pdf_path):
        """
        Extract tabular data from PDF invoices using pdfplumber.

        Attempts to find and extract the first valid table from the PDF.
        If no table found, tries text-based extraction as fallback.
        Returns a DataFrame with the extracted data.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            pd.DataFrame: DataFrame with extracted table data

        Raises:
            Exception: If PDF cannot be processed or no table found
        """
        try:
            import pdfplumber
        except ImportError:
            raise Exception("PDF support requires: pip install pdfplumber")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    raise ValueError("PDF is empty")

                # Iterate through pages to find a valid table
                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()

                    if tables and len(tables) > 0:
                        # Use the largest table (by row count)
                        table = max(tables, key=len)

                        if len(table) > 1:  # Need headers + at least 1 data row
                            # Convert to DataFrame
                            headers = table[0]
                            data = table[1:]

                            # Filter out completely empty rows
                            data = [row for row in data if any(cell for cell in row)]

                            if len(data) > 0:
                                df = pd.DataFrame(data, columns=headers)
                                logger.info(f"PDF table extracted from page {page_idx + 1}: {df.shape}")
                                return df

                # No table found - try text-based extraction as fallback
                logger.info("No structured table found in PDF, attempting text-based extraction")
                return self._extract_pdf_text_fallback(pdf_path)

        except ValueError as ve:
            raise Exception(f"PDF extraction error: {str(ve)}")
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")

    def _extract_pdf_text_fallback(self, pdf_path):
        """
        Fallback method to extract text-based data from PDFs without tables.

        Attempts supplier-specific extraction (e.g., AROMATE invoices).
        Falls back to generic text extraction if no supplier pattern matches.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            pd.DataFrame: DataFrame with extracted data or text lines

        Raises:
            Exception: If PDF cannot be read
        """
        try:
            import pdfplumber
            import re
        except ImportError:
            raise Exception("PDF support requires: pip install pdfplumber")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF is empty")

                text = pdf.pages[0].extract_text()
                if not text:
                    raise ValueError("No text found in PDF")

                # Try AROMATE invoice extraction (SKU# based)
                if "AROMATE" in text or "SKU#" in text:
                    logger.info("Detected AROMATE-style invoice, using regex extraction")
                    return self._extract_aromate_invoice(text)

                # Fallback: generic text extraction
                logger.info("Using generic text extraction")
                all_text = [line.strip() for line in text.split('\n') if line.strip()]

                df = pd.DataFrame({
                    'text_line': all_text
                })

                logger.info(f"PDF text extracted: {len(all_text)} lines")
                return df

        except Exception as e:
            raise Exception(f"PDF text extraction failed: {str(e)}")

    def _extract_aromate_invoice(self, text):
        """
        Extract AROMATE invoice data using regex pattern matching.

        Extracts SKU, quantity, unit price, and total price from AROMATE invoices.

        Args:
            text (str): Extracted PDF text

        Returns:
            pd.DataFrame: DataFrame with part_number, quantity, unit_price, total_price
        """
        import re

        # Pattern matches both formats:
        # Format 1: SKU# 1562485 76,080 PCS USD 0.6580 USD 50,060.64
        # Format 2: SKU# 2641486 15,120 PCS 0.7140 10,795.68
        pattern = r'SKU#\s*(\d+)\s+(\d+(?:,\d{3})*)\s+PCS\s+(?:USD\s+)?([\d.]+)\s+(?:USD\s+)?([\d,]+\.\d{2})'

        matches = re.findall(pattern, text)

        if not matches:
            logger.warning("AROMATE pattern not found, falling back to generic text extraction")
            all_text = [line.strip() for line in text.split('\n') if line.strip()]
            return pd.DataFrame({'text_line': all_text})

        # Convert matches to DataFrame
        data = []
        for sku, qty, unit_price, total_price in matches:
            data.append({
                'part_number': sku,
                'quantity': int(qty.replace(',', '')),
                'unit_price': float(unit_price),
                'total_price': float(total_price.replace(',', ''))
            })

        df = pd.DataFrame(data)
        logger.info(f"AROMATE invoice extraction successful: {len(df)} items extracted")
        return df

    def get_supplier_folders(self):
        """Get list of supplier folders in Input directory"""
        suppliers = []
        try:
            if INPUT_DIR.exists():
                for folder in INPUT_DIR.iterdir():
                    if folder.is_dir() and folder.name != "Processed":
                        suppliers.append(folder.name)
        except Exception as e:
            logger.error(f"Error scanning supplier folders: {e}")
        return sorted(suppliers)

    def refresh_supplier_combo(self):
        """Refresh the supplier dropdown in batch processing section"""
        if hasattr(self, 'batch_supplier_combo'):
            current = self.batch_supplier_combo.currentText()
            self.batch_supplier_combo.blockSignals(True)
            self.batch_supplier_combo.clear()
            self.batch_supplier_combo.addItem("-- Select Supplier --")
            suppliers = self.get_supplier_folders()
            for supplier in suppliers:
                self.batch_supplier_combo.addItem(supplier)
            # Try to restore previous selection
            idx = self.batch_supplier_combo.findText(current)
            if idx >= 0:
                self.batch_supplier_combo.setCurrentIndex(idx)
            self.batch_supplier_combo.blockSignals(False)

    def start_batch_processing(self):
        """Start batch processing of PDFs from selected supplier folder"""
        supplier = self.batch_supplier_combo.currentText()

        if supplier == "-- Select Supplier --" or not supplier:
            QMessageBox.warning(self, "No Supplier Selected", "Please select a supplier folder to process")
            return

        supplier_folder = INPUT_DIR / supplier
        logger.debug(f"Batch processing: INPUT_DIR={INPUT_DIR}, supplier={supplier}, full_path={supplier_folder}, exists={supplier_folder.exists()}")

        if not supplier_folder.exists():
            # Show more detailed error message
            QMessageBox.warning(self, "Folder Not Found",
                f"Supplier folder not found: {supplier}\n\n"
                f"Expected path: {supplier_folder}\n"
                f"Input folder: {INPUT_DIR}")
            return

        # Find all PDF files
        pdf_files = list(supplier_folder.glob("*.pdf"))

        if not pdf_files:
            QMessageBox.information(self, "No PDFs Found", f"No PDF files found in {supplier} folder")
            return

        # Show progress bar and update status
        self.batch_progress.setVisible(True)
        self.batch_progress.setValue(0)
        self.batch_progress.setMaximum(len(pdf_files))
        self.batch_status_label.setText(f"Processing {len(pdf_files)} PDFs from {supplier}...")
        QApplication.processEvents()

        # Process each PDF
        output_files = []
        errors = []

        for idx, pdf_file in enumerate(pdf_files):
            try:
                # Extract data from PDF with supplier-specific template
                if OCR_AVAILABLE and is_scanned_pdf(str(pdf_file)):
                    logger.info(f"Scanned PDF detected: {pdf_file.name}")
                    try:
                        # Use supplier-specific OCR template
                        df, metadata = extract_from_scanned_invoice(str(pdf_file), supplier_name=supplier)
                    except Exception as ocr_error:
                        # If OCR fails, fall back to digital PDF extraction
                        logger.warning(f"OCR extraction failed for {pdf_file.name}, falling back to digital extraction: {ocr_error}")
                        df = self.extract_pdf_table(str(pdf_file))
                else:
                    logger.info(f"Digital PDF detected: {pdf_file.name}")
                    df = self.extract_pdf_table(str(pdf_file))

                # Save to individual CSV file with timestamp in Input folder for further processing
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                pdf_name = pdf_file.stem
                output_file = INPUT_DIR / f"{pdf_name}_extracted_{timestamp}.csv"
                df.to_csv(output_file, index=False)
                output_files.append(output_file)

                # Move PDF to processed folder
                self.move_pdf_to_processed(str(pdf_file))

                logger.info(f"Processed {pdf_file.name}: extracted {len(df)} rows")

            except Exception as e:
                errors.append((pdf_file.name, str(e)))
                logger.error(f"Error processing {pdf_file.name}: {e}")

            # Update progress
            self.batch_progress.setValue(idx + 1)
            QApplication.processEvents()

        # Show completion message
        self.batch_progress.setVisible(False)

        if output_files:
            file_list = "\n".join([f"  • {f.name}" for f in output_files])
            message = f"Batch processing complete!\n\n"
            message += f"✓ {len(output_files)} files processed\n"
            if errors:
                message += f"⚠ {len(errors)} files skipped\n"
            message += f"\nOutput files:\n{file_list}"
            QMessageBox.information(self, "Batch Processing Complete", message)
            self.batch_status_label.setText(f"✓ Processed {len(output_files)} PDFs from {supplier}")
        else:
            QMessageBox.warning(self, "No Files Processed", f"Could not extract data from any PDFs\n\nErrors: {len(errors)}")
            self.batch_status_label.setText(f"✗ Failed to process PDFs from {supplier}")

        # Refresh exported files list
        self.refresh_exported_files()

    def refresh_suppliers_list(self):
        """Refresh the suppliers list in Settings dialog"""
        if not hasattr(self, 'settings_suppliers_list'):
            return

        try:
            suppliers = self.get_supplier_folders()
            self.settings_suppliers_list.blockSignals(True)
            self.settings_suppliers_list.clear()

            for supplier in suppliers:
                supplier_path = INPUT_DIR / supplier
                pdf_count = len(list(supplier_path.glob("*.pdf")))
                display_text = f"{supplier} ({pdf_count} PDFs)"
                self.settings_suppliers_list.addItem(display_text)

            self.suppliers_count_label.setText(f"Total: {len(suppliers)} suppliers")
            self.settings_suppliers_list.blockSignals(False)

        except Exception as e:
            logger.error(f"Error refreshing suppliers list: {e}")
            self.suppliers_count_label.setText("Error loading suppliers")

    def add_new_supplier_dialog(self):
        """Show dialog to create a new supplier folder"""
        text, ok = QInputDialog.getText(
            self, "Add New Supplier", "Enter supplier name:",
            text="NEW_SUPPLIER"
        )

        if ok and text:
            self.create_supplier_folder(text)

    def create_supplier_folder(self, supplier_name):
        """Create a new supplier folder in the Input directory"""
        if not supplier_name or not supplier_name.strip():
            QMessageBox.warning(self, "Invalid Name", "Supplier name cannot be empty")
            return

        # Sanitize folder name
        supplier_name = supplier_name.strip()

        try:
            supplier_path = INPUT_DIR / supplier_name

            if supplier_path.exists():
                QMessageBox.warning(self, "Folder Exists", f"Supplier folder '{supplier_name}' already exists")
                return

            # Create folder
            supplier_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created supplier folder: {supplier_path}")

            # Refresh displays
            self.refresh_suppliers_list()
            self.refresh_supplier_combo()

            QMessageBox.information(self, "Success", f"Created supplier folder: {supplier_name}")

        except Exception as e:
            logger.error(f"Error creating supplier folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create supplier folder:\n{str(e)}")

    def remove_selected_supplier(self, list_widget):
        """Remove selected supplier folder (empty folders only)"""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a supplier to remove")
            return

        # Extract supplier name from display text (remove PDF count)
        display_text = current_item.text()
        supplier_name = display_text.split(" (")[0]

        try:
            supplier_path = INPUT_DIR / supplier_name

            if not supplier_path.exists():
                QMessageBox.warning(self, "Not Found", f"Supplier folder '{supplier_name}' not found")
                self.refresh_suppliers_list()
                return

            # Check if folder is empty (excluding hidden files)
            items = [item for item in supplier_path.iterdir() if not item.name.startswith('.')]
            if items:
                QMessageBox.warning(
                    self, "Folder Not Empty",
                    f"Cannot remove '{supplier_name}' - folder contains {len(items)} file(s).\n\n"
                    "Please remove all files first or move them to a different location."
                )
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                f"Remove supplier folder '{supplier_name}'?\n\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                supplier_path.rmdir()
                logger.info(f"Removed supplier folder: {supplier_path}")
                self.refresh_suppliers_list()
                self.refresh_supplier_combo()
                QMessageBox.information(self, "Success", f"Removed supplier folder: {supplier_name}")

        except Exception as e:
            logger.error(f"Error removing supplier folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove supplier folder:\n{str(e)}")

    def open_supplier_folder(self, list_widget):
        """Open selected supplier folder in file explorer"""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a supplier folder to open")
            return

        # Extract supplier name from display text
        display_text = current_item.text()
        supplier_name = display_text.split(" (")[0]

        try:
            supplier_path = INPUT_DIR / supplier_name

            if not supplier_path.exists():
                QMessageBox.warning(self, "Not Found", f"Supplier folder '{supplier_name}' not found")
                self.refresh_suppliers_list()
                return

            # Open folder in file explorer
            if sys.platform == 'linux':
                subprocess.run(['xdg-open', str(supplier_path)], check=False)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', str(supplier_path)], check=False)
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['explorer', str(supplier_path)], check=False)

            logger.info(f"Opened supplier folder: {supplier_path}")

        except Exception as e:
            logger.error(f"Error opening supplier folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open supplier folder:\n{str(e)}")

    def on_shipment_drop(self, field_key, column_name):
        for k, t in self.shipment_targets.items():
            if t.column_name == column_name and k != field_key:
                t.column_name = None
                t.setText(f"Drop {t.field_key} here")
                t.setProperty("occupied", False)
                t.style().unpolish(t); t.style().polish(t)
        self.shipment_mapping[field_key] = column_name
        SHIPMENT_MAPPING_FILE.write_text(json.dumps(self.shipment_mapping, indent=2))
        logger.info(f"Shipment mapping saved: {field_key} to {column_name}")

    def reset_current_mapping(self):
        self.shipment_mapping = {}
        
        # Clear drop targets (right side)
        for target in self.shipment_targets.values():
            target.column_name = None
            target.setText(f"Drop {target.field_key} here")
            target.setProperty("occupied", False)
            target.style().unpolish(target); target.style().polish(target)
        
        # Clear CSV columns drag labels (left side)
        for label in self.shipment_drag_labels:
            label.setParent(None)
            label.deleteLater()
        self.shipment_drag_labels = []
        
        self.status.setText("Current mapping reset")

    def load_mapping_profiles(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT profile_name FROM mapping_profiles ORDER BY created_date DESC", conn)
            conn.close()
            
            # Update Process tab combo (tab 0 - always initialized)
            if hasattr(self, 'profile_combo'):
                self.profile_combo.blockSignals(True)
                self.profile_combo.clear()
                self.profile_combo.addItem("-- Select Profile --")
                for name in df['profile_name'].tolist():
                    self.profile_combo.addItem(name)
                self.profile_combo.blockSignals(False)
            
            # Update Invoice Mapping Profiles tab combo (tab 1 - may not be initialized yet)
            if hasattr(self, 'profile_combo_map'):
                self.profile_combo_map.blockSignals(True)
                self.profile_combo_map.clear()
                self.profile_combo_map.addItem("-- Select Profile --")
                for name in df['profile_name'].tolist():
                    self.profile_combo_map.addItem(name)
                self.profile_combo_map.blockSignals(False)
                
            logger.info(f"Loaded {len(df)} mapping profiles")
        except Exception as e:
            logger.error(f"Failed to load mapping profiles: {e}")

    def save_mapping_profile(self):
        name, ok = QInputDialog.getText(self, "Save Mapping Profile", "Enter profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if self.profile_combo.findText(name) != -1:
            if QMessageBox.question(self, "Overwrite?", f"Profile '{name}' exists. Overwrite?") != QMessageBox.Yes:
                return
        
        mapping_str = json.dumps(self.shipment_mapping)
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO mapping_profiles (profile_name, mapping_json) VALUES (?, ?)",
                      (name, mapping_str))
            conn.commit()
            conn.close()
            self.load_mapping_profiles()
            # Only update the combo on the Invoice Mapping Profiles tab (where save button is)
            self.profile_combo_map.setCurrentText(name)
            logger.success(f"Mapping profile saved: {name}")
            self.status.setText(f"Profile saved: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")

    def load_selected_profile(self, name):
        if not name or name == "-- Select Profile --":
            return
        self.load_selected_profile_full(name)

    def load_selected_profile_full(self, name):
        if not name or name == "-- Select Profile --":
            # Clear all mappings and reset UI
            self.shipment_mapping = {}

            # Clear drop targets
            for target in self.shipment_targets.values():
                target.column_name = None
                target.setText(f"Drop {target.field_key.replace('_', ' ')} here")
                target.setProperty("occupied", False)
                target.style().unpolish(target)
                target.style().polish(target)

            # Clear draggable CSV columns
            for label in self.shipment_drag_labels:
                label.deleteLater()
            self.shipment_drag_labels.clear()

            self.bottom_status.setText("Profile cleared")
            return

        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT mapping_json FROM mapping_profiles WHERE profile_name = ?", (name,))
            row = c.fetchone()
            conn.close()
            if row:
                self.shipment_mapping = json.loads(row[0])
                self.apply_current_mapping()
                logger.info(f"Profile loaded: {name}")
                self.bottom_status.setText(f"Loaded profile: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load failed: {e}")

    def delete_mapping_profile(self):
        # Get profile name from Invoice Mapping Profiles tab combo (where delete button is)
        name = self.profile_combo_map.currentText()
        if not name or name == "-- Select Profile --":
            return
        if QMessageBox.question(self, "Delete", f"Delete profile '{name}'?") != QMessageBox.Yes:
            return
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("DELETE FROM mapping_profiles WHERE profile_name = ?", (name,))
            conn.commit()
            conn.close()
            self.load_mapping_profiles()
            # Reset both combos to default after deletion
            self.profile_combo.setCurrentIndex(0)
            self.profile_combo_map.setCurrentIndex(0)
            logger.info(f"Profile deleted: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def apply_current_mapping(self):
        # Batch UI updates to prevent GUI freezing
        for key, target in self.shipment_targets.items():
            col = self.shipment_mapping.get(key)
            if col:
                target.column_name = col
                target.setText(f"{key}\n<- {col}")
                target.setProperty("occupied", True)
            else:
                target.column_name = None
                target.setText(f"Drop {key.replace('_', ' ')} here")
                target.setProperty("occupied", False)
        
        # Apply all style updates at once after setting properties
        for target in self.shipment_targets.values():
            target.style().unpolish(target)
            target.style().polish(target)

    def setup_master_tab(self):
        layout = QVBoxLayout(self.tab_master)
        title = QLabel("<h2>Parts View - Click any cell to edit</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        edit_box = QHBoxLayout()
        btn_add = QPushButton("Add Row")
        btn_add.setStyleSheet(self.get_button_style("success"))
        btn_del = QPushButton("Delete Selected")
        btn_del.setStyleSheet(self.get_button_style("danger"))
        btn_save = QPushButton("Save Changes")
        btn_save.setStyleSheet(self.get_button_style("success"))
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet(self.get_button_style("info"))
        btn_add.clicked.connect(self.add_part_row)
        btn_del.clicked.connect(self.delete_selected_parts)
        btn_save.clicked.connect(self.save_parts_table)
        btn_refresh.clicked.connect(self.refresh_parts_table)
        edit_box.addWidget(QLabel("Edit:"))
        edit_box.addWidget(btn_add); edit_box.addWidget(btn_del); edit_box.addWidget(btn_save); edit_box.addWidget(btn_refresh)
        edit_box.addStretch()
        layout.addLayout(edit_box)

        # SQL Query Builder
        query_group = QGroupBox("SQL Query Builder")
        query_layout = QVBoxLayout()
        
        query_controls = QHBoxLayout()
        query_controls.addWidget(QLabel("SELECT * FROM parts_master WHERE"))
        
        self.query_field = QComboBox()
        self.query_field.addItems(["part_number", "description", "hts_code", "country_origin", "mid", "client_code", "steel_ratio", "non_steel_ratio"])
        query_controls.addWidget(self.query_field)
        
        self.query_operator = QComboBox()
        self.query_operator.addItems(["=", "LIKE", ">", "<", ">=", "<=", "!="])
        query_controls.addWidget(self.query_operator)
        
        self.query_value = QLineEdit()
        self.query_value.setPlaceholderText("Enter value...")
        self.query_value.setReadOnly(False)
        self.query_value.setEnabled(True)
        self.query_value.setStyleSheet("QLineEdit { color: white; background-color: #333333; padding: 5px; border: 1px solid #555; }")
        query_controls.addWidget(self.query_value, 1)
        
        btn_run_query = QPushButton("Run Query")
        btn_run_query.setStyleSheet(self.get_button_style("info"))
        btn_run_query.clicked.connect(self.run_custom_query)
        query_controls.addWidget(btn_run_query)
        
        btn_clear_query = QPushButton("Show All")
        btn_clear_query.setStyleSheet(self.get_button_style("default"))
        btn_clear_query.clicked.connect(self.refresh_parts_table)
        query_controls.addWidget(btn_clear_query)
        
        query_layout.addLayout(query_controls)
        
        # Custom SQL input
        custom_sql_layout = QHBoxLayout()
        custom_sql_layout.addWidget(QLabel("Custom SQL:"))
        self.custom_sql_input = QLineEdit()
        self.custom_sql_input.setPlaceholderText("SELECT * FROM parts_master WHERE ...")
        self.custom_sql_input.setReadOnly(False)
        self.custom_sql_input.setEnabled(True)
        self.custom_sql_input.setStyleSheet("QLineEdit { color: white; background-color: #333333; padding: 5px; border: 1px solid #555; }")
        custom_sql_layout.addWidget(self.custom_sql_input, 1)
        btn_run_custom = QPushButton("Execute")
        btn_run_custom.setStyleSheet(self.get_button_style("success"))
        btn_run_custom.clicked.connect(self.run_custom_sql)
        custom_sql_layout.addWidget(btn_run_custom)
        query_layout.addLayout(custom_sql_layout)
        
        self.query_result_label = QLabel("Ready")
        self.query_result_label.setStyleSheet("padding:5px; background:#f0f0f0;")
        query_layout.addWidget(self.query_result_label)
        
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Quick Search:"))
        self.search_field_combo = QComboBox()
        self.search_field_combo.addItems(["All Fields","part_number","description","hts_code","country_origin","mid","client_code","steel_ratio","non_steel_ratio"])
        # Refocus search input after combo selection
        self.search_field_combo.currentIndexChanged.connect(lambda: self.search_input.setFocus())
        search_box.addWidget(self.search_field_combo)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter...")
        self.search_input.setReadOnly(False)
        self.search_input.setEnabled(True)
        self.search_input.setStyleSheet("QLineEdit { color: white; background-color: #333333; padding: 5px; border: 1px solid #555; }")
        self.search_input.textChanged.connect(self.filter_parts_table)
        search_box.addWidget(self.search_input, 1)
        layout.addLayout(search_box)

        table_box = QGroupBox("Parts Master Table")
        tl = QVBoxLayout()
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(9)
        self.parts_table.setHorizontalHeaderLabels([
            "part_number", "description", "hts_code", "country_origin", "mid", "client_code", "steel_ratio", "non_steel_ratio", "updated_date"
        ])
        self.parts_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.parts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parts_table.setSortingEnabled(False)  # Disabled for better performance
        tl.addWidget(self.parts_table)
        table_box.setLayout(tl)
        layout.addWidget(table_box, 1)

        self.refresh_parts_table()
        self.tab_master.setLayout(layout)

    def refresh_parts_table(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT * FROM parts_master ORDER BY part_number", conn)
            conn.close()
            self.populate_parts_table(df)
            self.query_result_label.setText("Showing all parts")
            self.query_result_label.setStyleSheet("padding:5px; background:#f0f0f0;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load parts:\n{e}")

    def add_part_row(self):
        row = self.parts_table.rowCount()
        self.parts_table.insertRow(row)
        self.parts_table.setItem(row, 0, QTableWidgetItem("NEW_PART"))

    def delete_selected_parts(self):
        rows = sorted(set(index.row() for index in self.parts_table.selectedIndexes()), reverse=True)
        if not rows:
            QMessageBox.information(self, "Info", "Select rows to delete")
            return
        if QMessageBox.question(self, "Confirm", f"Delete {len(rows)} parts?") != QMessageBox.Yes:
            return
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        deleted = 0
        for row in rows:
            part = self.parts_table.item(row, 0).text().strip()
            if part and part != "NEW_PART":
                c.execute("DELETE FROM parts_master WHERE part_number=?", (part,))
                deleted += c.rowcount
                self.parts_table.removeRow(row)
        conn.commit(); conn.close()
        QMessageBox.information(self, "Success", f"Deleted {deleted} parts")
        self.load_available_mids()

    def save_parts_table(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            now = datetime.now().isoformat()
            saved = 0
            for row in range(self.parts_table.rowCount()):
                items = [self.parts_table.item(row, col) for col in range(9)]
                if not items[0] or not items[0].text().strip(): continue
                part = items[0].text().strip()
                desc = items[1].text() if items[1] else ""
                hts = items[2].text() if items[2] else ""
                origin = (items[3].text() or "").upper()[:2]
                mid = items[4].text() if items[4] else ""
                client_code = items[5].text() if items[5] else ""
                try:
                    steel = float(items[6].text())
                    steel = max(0.0, min(1.0, steel))
                    non_steel = 1.0 - steel
                except:
                    steel = 1.0; non_steel = 0.0
                c.execute("""INSERT INTO parts_master (part_number, description, hts_code, country_origin, mid, client_code, steel_ratio, non_steel_ratio, last_updated)
                          VALUES (?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(part_number) DO UPDATE SET
                          description=excluded.description, hts_code=excluded.hts_code,
                          country_origin=excluded.country_origin, mid=excluded.mid,
                          client_code=excluded.client_code, steel_ratio=excluded.steel_ratio,
                          non_steel_ratio=excluded.non_steel_ratio, last_updated=excluded.last_updated""",
                          (part, desc, hts, origin, mid, client_code, steel, non_steel, now))
                if c.rowcount: saved += 1
            conn.commit(); conn.close()
            QMessageBox.information(self, "Success", f"Saved {saved} parts!")
            self.bottom_status.setText("Database saved")
            self.load_available_mids()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{e}")

    def filter_parts_table(self, text):
        text = text.lower().strip()
        if not text:
            for row in range(self.parts_table.rowCount()):
                self.parts_table.setRowHidden(row, False)
            return
        for row in range(self.parts_table.rowCount()):
            match = any(text in (self.parts_table.item(row, col).text() or "").lower() 
                       for col in range(self.parts_table.columnCount()))
            self.parts_table.setRowHidden(row, not match)

    def run_custom_query(self):
        """Execute SQL query builder query"""
        try:
            field = self.query_field.currentText()
            operator = self.query_operator.currentText()
            value = self.query_value.text().strip()
            
            if not value:
                QMessageBox.warning(self, "Query Error", "Please enter a value to search for.")
                return
            
            # Build WHERE clause
            if operator == "LIKE":
                where_clause = f"{field} LIKE ?"
                params = (f"%{value}%",)
            else:
                where_clause = f"{field} {operator} ?"
                params = (value,)
            
            sql = f"SELECT * FROM parts_master WHERE {where_clause} ORDER BY part_number"
            
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql(sql, conn, params=params)
            conn.close()
            
            self.populate_parts_table(df)
            self.query_result_label.setText(f"Query returned {len(df)} results")
            self.query_result_label.setStyleSheet("padding:5px; background:#107C10; color:white;")
            logger.info(f"Query executed: {sql} with params {params}")
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self.query_result_label.setText(f"Query Error: {str(e)}")
            self.query_result_label.setStyleSheet("padding:5px; background:#A4262C; color:white;")
            QMessageBox.critical(self, "Query Error", f"Failed to execute query:\n{e}")

    def run_custom_sql(self):
        """Execute custom SQL query"""
        try:
            sql = self.custom_sql_input.text().strip()
            
            if not sql:
                QMessageBox.warning(self, "Query Error", "Please enter a SQL query.")
                return
            
            # Basic validation - must be SELECT and FROM parts_master
            if not sql.upper().startswith("SELECT"):
                QMessageBox.warning(self, "Query Error", "Only SELECT queries are allowed.")
                return
            
            if "parts_master" not in sql.lower():
                QMessageBox.warning(self, "Query Error", "Query must reference 'parts_master' table.")
                return
            
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql(sql, conn)
            conn.close()
            
            self.populate_parts_table(df)
            self.query_result_label.setText(f"Custom query returned {len(df)} results")
            self.query_result_label.setStyleSheet("padding:5px; background:#d4edda; color:#155724;")
            logger.info(f"Custom SQL executed: {sql}")
            
        except Exception as e:
            logger.error(f"Custom SQL execution failed: {e}")
            self.query_result_label.setText(f"SQL Error: {str(e)}")
            self.query_result_label.setStyleSheet("padding:5px; background:#A4262C; color:white;")
            QMessageBox.critical(self, "SQL Error", f"Failed to execute SQL:\n{e}")

    def populate_parts_table(self, df):
        """Populate the parts table with a dataframe"""
        self.parts_table.blockSignals(True)
        self.parts_table.setRowCount(len(df))
        # Map table column headers to dataframe column indices
        # Database columns: part_number, description, hts_code, country_origin, mid, client_code, steel_ratio, non_steel_ratio, last_updated
        for i, row in df.iterrows():
            # Column 0: part_number
            self.parts_table.setItem(i, 0, QTableWidgetItem(str(row['part_number']) if 'part_number' in df.columns else ""))
            # Column 1: description
            self.parts_table.setItem(i, 1, QTableWidgetItem(str(row['description']) if 'description' in df.columns else ""))
            # Column 2: hts_code
            self.parts_table.setItem(i, 2, QTableWidgetItem(str(row['hts_code']) if 'hts_code' in df.columns else ""))
            # Column 3: country_origin
            self.parts_table.setItem(i, 3, QTableWidgetItem(str(row['country_origin']) if 'country_origin' in df.columns else ""))
            # Column 4: mid
            self.parts_table.setItem(i, 4, QTableWidgetItem(str(row['mid']) if 'mid' in df.columns else ""))
            # Column 5: client_code
            self.parts_table.setItem(i, 5, QTableWidgetItem(str(row['client_code']) if 'client_code' in df.columns else ""))
            # Column 6: steel_ratio
            self.parts_table.setItem(i, 6, QTableWidgetItem(str(row['steel_ratio']) if 'steel_ratio' in df.columns else ""))
            # Column 7: non_steel_ratio
            self.parts_table.setItem(i, 7, QTableWidgetItem(str(row['non_steel_ratio']) if 'non_steel_ratio' in df.columns else ""))
            # Column 8: updated_date (maps to last_updated in database)
            self.parts_table.setItem(i, 8, QTableWidgetItem(str(row['last_updated']) if 'last_updated' in df.columns else ""))
        self.parts_table.blockSignals(False)

    # ...existing code...

    def setup_config_tab(self):
        layout = QVBoxLayout(self.tab_config)
        title = QLabel("<h2>Customs Configuration</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Buttons at top
        top_bar = QHBoxLayout()
        btn_import_excel = QPushButton("Import Section 232 Tariffs (CSV/Excel)")
        btn_import_excel.setStyleSheet(self.get_button_style("success"))
        btn_import_excel.clicked.connect(self.import_tariff_232)
        btn_refresh = QPushButton("Refresh View")
        btn_refresh.setStyleSheet(self.get_button_style("info"))
        btn_refresh.clicked.connect(self.refresh_tariff_view)
        top_bar.addWidget(btn_import_excel)
        top_bar.addWidget(btn_refresh)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Section 232 Tariff Viewer
        group1 = QGroupBox("Section 232 Tariff List")
        g1_layout = QVBoxLayout()

        # Search and filter
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Filter:"))
        self.tariff_filter = QLineEdit()
        self.tariff_filter.setPlaceholderText("Search HTS code, classification, or chapter...")
        self.tariff_filter.textChanged.connect(self.filter_tariff_table)
        filter_bar.addWidget(self.tariff_filter)

        self.tariff_material_filter = QComboBox()
        self.tariff_material_filter.addItems(["All", "Steel", "Aluminum", "Wood", "Copper"])
        self.tariff_material_filter.currentTextChanged.connect(self.filter_tariff_table)
        filter_bar.addWidget(QLabel("Material:"))
        filter_bar.addWidget(self.tariff_material_filter)
        self.bottom_status.setText("Loading Exported Files...")
        QApplication.processEvents()
        # ...existing code...
        self.bottom_status.setText("Ready")
        
        # Add color toggle checkbox
        self.tariff_color_toggle = QCheckBox("Color by Material")
        self.tariff_color_toggle.setChecked(False)  # Disabled by default
        self.tariff_color_toggle.stateChanged.connect(self.filter_tariff_table)
        filter_bar.addWidget(self.tariff_color_toggle)
        
        g1_layout.addLayout(filter_bar)
        
        # Table
        self.tariff_table = QTableWidget()
        self.tariff_table.setColumnCount(7)
        self.tariff_table.setHorizontalHeaderLabels(["HTS Code", "Material", "Classification", 
                       "Chapter", "Chapter Description", 
                       "Declaration", "Notes"])
        self.tariff_table.horizontalHeader().setStretchLastSection(True)
        self.tariff_table.setAlternatingRowColors(True)
        self.tariff_table.setStyleSheet("")
        self.tariff_table.setSortingEnabled(False)  # Disabled for better performance
        g1_layout.addWidget(self.tariff_table)
        
        # Count label
        self.tariff_count_label = QLabel("Total: 0 tariff codes")
        self.tariff_count_label.setStyleSheet("font-weight:bold; padding:5px;")
        g1_layout.addWidget(self.tariff_count_label)
        
        group1.setLayout(g1_layout)
        layout.addWidget(group1)

        self.tab_config.setLayout(layout)
        
        # Load initial data
        self.refresh_tariff_view()

    def import_tariff_232(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Section 232 Tariffs CSV", "", "CSV Files (*.csv);;Excel (*.xlsx)")
        if not path:
            return
        try:
            # Read file based on extension
            if path.lower().endswith('.csv'):
                df = pd.read_csv(path, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(path, header=0)
            
            df = df.fillna("")
            
            # Check if it's the new comprehensive format
            if 'HTS Code' in df.columns and 'Material' in df.columns and 'Classification' in df.columns:
                # New comprehensive CSV format with all columns
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("DELETE FROM tariff_232")
                
                imported = 0
                for _, row in df.iterrows():
                    hts_code = str(row['HTS Code']).strip().replace(".", "")[:10]
                    material = str(row['Material']).strip()
                    classification = str(row['Classification']).strip()
                    chapter = str(row['Chapter']).strip()
                    chapter_desc = str(row['Chapter Description']).strip()
                    declaration = str(row['Declaration Required']).strip()
                    notes = str(row['Notes']).strip()
                    
                    if hts_code and material in ['Steel', 'Aluminum', 'Wood', 'Copper']:
                        c.execute("""INSERT OR REPLACE INTO tariff_232 
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (hts_code, material, classification, chapter, 
                                  chapter_desc, declaration, notes))
                        imported += 1
                
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", 
                    f"Imported {imported} Section 232 tariff codes\n\n"
                    f"Format: Comprehensive 7-column CSV")
                logger.success(f"tariff_232 table updated with {imported} codes (comprehensive format)")
                self.status.setText(f"Section 232 list imported: {imported} codes")
            elif 'HTS Code' in df.columns and 'Material' in df.columns:
                # Simple CSV format (HTS Code, Material only)
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("DELETE FROM tariff_232")
                
                imported = 0
                for _, row in df.iterrows():
                    hts_code = str(row['HTS Code']).strip().replace(".", "")[:10]
                    material = str(row['Material']).strip()
                    
                    if hts_code and material in ['Steel', 'Aluminum', 'Wood', 'Copper']:
                        c.execute("""INSERT OR REPLACE INTO tariff_232 
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (hts_code, material, '', '', '', '', ''))
                        imported += 1
                
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", f"Imported {imported} Section 232 tariff codes")
                logger.success(f"tariff_232 table updated with {imported} codes")
                self.status.setText(f"Section 232 list imported: {imported} codes")
            else:
                # Legacy Excel format (2 columns: steel, aluminum)
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("DELETE FROM tariff_232")
                steel_codes = [str(x).replace(".", "")[:10] for x in df.iloc[1:, 0] if pd.notna(x) and str(x).strip()]
                alum_codes = [str(x).replace(".", "")[:10] for x in df.iloc[1:, 1] if pd.notna(x) and str(x).strip()]
                for code in steel_codes:
                    if code:
                        c.execute("""INSERT OR REPLACE INTO tariff_232 
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (code, 'Steel', '', '', '', '', ''))
                for code in alum_codes:
                    if code:
                        c.execute("""INSERT OR REPLACE INTO tariff_232 
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (code, 'Aluminum', '', '', '', '', ''))
                conn.commit()
                conn.close()
                imported = len(steel_codes) + len(alum_codes)
                QMessageBox.information(self, "Success", 
                    f"Imported {imported} 232 codes\n\n"
                    f"Format: Legacy Excel (2-column)")
                logger.success("tariff_232 table updated (legacy format)")
                self.status.setText("Section 232 list imported")
            
            self.refresh_tariff_view()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {e}")
            logger.error(f"Section 232 import error: {e}")


    def refresh_tariff_view(self):
        """Load and display all tariff codes from database"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("""SELECT hts_code, material, classification, chapter, 
                                       chapter_description, declaration_required, notes 
                                FROM tariff_232 
                                ORDER BY material, chapter, hts_code""", conn)
            conn.close()
            
            self.tariff_full_data = df  # Store for filtering
            self.filter_tariff_table()
            
        except Exception as e:
            logger.error(f"Refresh tariff view failed: {e}")
            self.tariff_table.setRowCount(0)
            self.tariff_count_label.setText("Error loading tariff data")

    def filter_tariff_table(self):
        """Filter and display tariff table based on search criteria"""
        try:
            if not hasattr(self, 'tariff_full_data') or self.tariff_full_data.empty:
                self.tariff_table.setRowCount(0)
                self.tariff_count_label.setText("No tariff data")
                return
            
            df = self.tariff_full_data.copy()
            
            # Apply text filter - search across HTS code, classification, and chapter description
            search_text = self.tariff_filter.text().strip().lower()
            if search_text:
                mask = (df['hts_code'].astype(str).str.lower().str.contains(search_text, na=False) |
                       df['classification'].astype(str).str.lower().str.contains(search_text, na=False) |
                       df['chapter_description'].astype(str).str.lower().str.contains(search_text, na=False))
                df = df[mask]
            
            # Apply material filter
            material_filter = self.tariff_material_filter.currentText()
            if material_filter != "All":
                df = df[df['material'] == material_filter]
            
            # Populate table
            self.tariff_table.setSortingEnabled(False)
            self.tariff_table.setRowCount(len(df))
            
            for row_idx, (_, row) in enumerate(df.iterrows()):
                # Create items for all 7 columns
                items = [
                    QTableWidgetItem(str(row['hts_code'])),
                    QTableWidgetItem(str(row['material'])),
                    QTableWidgetItem(str(row['classification'])),
                    QTableWidgetItem(str(row['chapter'])),
                    QTableWidgetItem(str(row['chapter_description'])),
                    QTableWidgetItem(str(row['declaration_required'])),
                    QTableWidgetItem(str(row['notes']))
                ]
                
                # Make all items read-only
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                # Color code by material (if toggle is enabled)
                if self.tariff_color_toggle.isChecked():
                    material_colors = {
                        'Steel': QColor('#e3f2fd'),      # Light blue
                        'Aluminum': QColor('#fff3e0'),   # Light orange
                        'Wood': QColor('#f1f8e9'),       # Light green
                        'Copper': QColor('#ffe0b2')      # Light copper/bronze
                    }
                    
                    material = row['material']
                    if material in material_colors:
                        bg_color = material_colors[material]
                        # Apply color to entire row for better visibility
                        for item in items:
                            item.setBackground(bg_color)
                
                # Add items to table
                for col_idx, item in enumerate(items):
                    self.tariff_table.setItem(row_idx, col_idx, item)
            
            self.tariff_table.setSortingEnabled(True)
            self.tariff_count_label.setText(f"Total: {len(df)} tariff codes (filtered from {len(self.tariff_full_data)})")
            
        except Exception as e:
            logger.error(f"Filter tariff table failed: {e}")
            logger.trace(traceback.format_exc())
            self.tariff_table.setRowCount(0)

    def setup_log_tab(self):
        layout = QVBoxLayout(self.tab_log)
        title = QLabel("<h2>Log View</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        log_box = QGroupBox("Real-time Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_text.customContextMenuRequested.connect(self.log_context_menu)
        log_layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.setStyleSheet("background:#0078D7; color:white; font-weight:bold;")
        btn_copy.clicked.connect(self.copy_log_to_clipboard)
        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(lambda: (self.log_text.clear(), logger.logs.clear()))
        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        
        log_box.setLayout(log_layout)
        layout.addWidget(log_box)

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(500)
        self.tab_log.setLayout(layout)

    def setup_actions_tab(self):
        """Section 232 Actions Reference Tab - Chapter 99 tariff actions"""
        layout = QVBoxLayout(self.tab_actions)
        
        # Title
        title = QLabel("<h2>Section 232 Tariff Actions (Chapter 99)</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Info box
        info_box = QGroupBox("Reference Information")
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "This table contains the Chapter 99 tariff action codes and rates for Section 232 duties. "
            "These are the actual tariff numbers used in ACE for declaring Section 232 merchandise."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        btn_import = QPushButton("Import Actions CSV")
        btn_import.setStyleSheet(self.get_button_style("info"))
        btn_import.clicked.connect(self.import_actions_csv)
        btn_layout.addWidget(btn_import)

        btn_refresh = QPushButton("Refresh View")
        btn_refresh.setStyleSheet(self.get_button_style("default"))
        btn_refresh.clicked.connect(self.refresh_actions_view)
        btn_layout.addWidget(btn_refresh)

        # Edit mode toggle
        self.actions_edit_mode = False
        self.btn_edit_actions = QPushButton("Enable Edit Mode")
        self.btn_edit_actions.setStyleSheet(self.get_button_style("warning"))
        self.btn_edit_actions.clicked.connect(self.toggle_actions_edit_mode)
        btn_layout.addWidget(self.btn_edit_actions)

        # Save/Cancel buttons (hidden by default)
        self.btn_save_actions = QPushButton("Save Changes")
        self.btn_save_actions.setStyleSheet(self.get_button_style("success"))
        self.btn_save_actions.clicked.connect(self.save_actions_changes)
        self.btn_save_actions.setVisible(False)
        btn_layout.addWidget(self.btn_save_actions)

        self.btn_cancel_actions = QPushButton("Cancel")
        self.btn_cancel_actions.setStyleSheet(self.get_button_style("default"))
        self.btn_cancel_actions.clicked.connect(self.cancel_actions_edit)
        self.btn_cancel_actions.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_actions)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Filter bar
        filter_bar = QHBoxLayout()
        self.actions_filter = QLineEdit()
        self.actions_filter.setPlaceholderText("Search tariff number, action, or description...")
        self.actions_filter.textChanged.connect(self.filter_actions_table)
        filter_bar.addWidget(self.actions_filter)
        
        self.actions_material_filter = QComboBox()
        self.actions_material_filter.addItems(["All", "Steel", "Aluminum", "Copper", "Wood"])
        self.actions_material_filter.currentTextChanged.connect(self.filter_actions_table)
        filter_bar.addWidget(QLabel("Commodity:"))
        filter_bar.addWidget(self.actions_material_filter)
        
        # Add color toggle checkbox
        self.actions_color_toggle = QCheckBox("Color by Material")
        self.actions_color_toggle.setChecked(False)  # Disabled by default
        self.actions_color_toggle.stateChanged.connect(self.filter_actions_table)
        filter_bar.addWidget(self.actions_color_toggle)
        
        layout.addLayout(filter_bar)
        
        # Table
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(10)
        self.actions_table.setHorizontalHeaderLabels([
            "Tariff No", "Action", "Description", "Ad Valorem Rate",
            "Effective Date", "Expiration Date", "Specific Rate",
            "Additional Declaration", "Note", "Link"
        ])
        self.actions_table.horizontalHeader().setStretchLastSection(True)
        self.actions_table.setAlternatingRowColors(True)
        self.actions_table.setStyleSheet("")
        self.actions_table.setSortingEnabled(True)
        layout.addWidget(self.actions_table)
        
        # Count label
        self.actions_count_label = QLabel("Total: 0 actions")
        self.actions_count_label.setStyleSheet("font-weight:bold; padding:5px;")
        layout.addWidget(self.actions_count_label)
        
        self.tab_actions.setLayout(layout)
        
        # Load data
        self.refresh_actions_view()

    def import_actions_csv(self):
        """Import Section 232 Actions from CSV/TSV"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Section 232 Actions File", "",
            "CSV/TSV Files (*.csv *.txt);;All Files (*.*)"
        )
        if not path:
            return
        
        try:
            # Try to detect the delimiter and read the file
            if path.lower().endswith('.txt'):
                # For .txt files, assume tab-delimited
                df = pd.read_csv(path, sep='\t', dtype=str, keep_default_na=False)
            else:
                # For .csv files, let pandas auto-detect
                df = pd.read_csv(path, dtype=str, keep_default_na=False)
            
            df = df.fillna("")
            
            # Normalize column names (strip whitespace)
            df.columns = df.columns.str.strip()
            
            # Check for required columns
            required_cols = ['Tariff No', 'Action']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                QMessageBox.warning(self, "Invalid Format", 
                    f"CSV is missing required columns: {', '.join(missing_cols)}\n\n"
                    f"Found columns: {', '.join(df.columns.tolist())}")
                return
            
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("DELETE FROM sec_232_actions")
            
            imported = 0
            for _, row in df.iterrows():
                tariff_no = str(row.get('Tariff No', '')).strip()
                action = str(row.get('Action', '')).strip()
                description = str(row.get('Tariff Description', '')).strip()
                advalorem = str(row.get('Advalorem Rate', '')).strip()
                effective = str(row.get('Effective Date', '')).strip()
                expiration = str(row.get('Expiration Date', '')).strip()
                specific = str(row.get('Specific Rate', '')).strip()
                declaration = str(row.get('Additional Declaration Required', '')).strip()
                note = str(row.get('Note', '')).strip()
                link = str(row.get('Link', '')).strip()
                
                if tariff_no and action:
                    c.execute("""INSERT OR REPLACE INTO sec_232_actions 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (tariff_no, action, description, advalorem, effective, 
                              expiration, specific, declaration, note, link))
                    imported += 1
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", 
                f"Imported {imported} Section 232 action records")
            logger.success(f"sec_232_actions table updated with {imported} records")
            self.status.setText(f"Section 232 actions imported: {imported} records")
            self.refresh_actions_view()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {e}")
            logger.error(f"Section 232 actions import error: {e}")

    def refresh_actions_view(self):
        """Load and display all Section 232 actions from database"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("""SELECT tariff_no, action, description, advalorem_rate,
                                       effective_date, expiration_date, specific_rate,
                                       additional_declaration, note, link
                                FROM sec_232_actions
                                ORDER BY tariff_no""", conn)
            conn.close()
            
            self.actions_full_data = df
            self.filter_actions_table()
            
        except Exception as e:
            logger.error(f"Refresh actions view failed: {e}")
            self.actions_table.setRowCount(0)
            self.actions_count_label.setText("Error loading actions data")

    def filter_actions_table(self):
        """Filter and display actions table based on search criteria"""
        try:
            if not hasattr(self, 'actions_full_data') or self.actions_full_data.empty:
                self.actions_table.setRowCount(0)
                self.actions_count_label.setText("No actions data")
                return
            
            df = self.actions_full_data.copy()
            
            # Apply text filter
            search_text = self.actions_filter.text().strip().lower()
            if search_text:
                mask = (df['tariff_no'].astype(str).str.lower().str.contains(search_text, na=False) |
                       df['action'].astype(str).str.lower().str.contains(search_text, na=False) |
                       df['description'].astype(str).str.lower().str.contains(search_text, na=False) |
                       df['note'].astype(str).str.lower().str.contains(search_text, na=False))
                df = df[mask]
            
            # Apply material filter
            material_filter = self.actions_material_filter.currentText()
            if material_filter != "All":
                # Filter by action column containing material name
                df = df[df['action'].str.contains(material_filter, case=False, na=False)]
            
            # Populate table
            self.actions_table.setSortingEnabled(False)
            self.actions_table.setRowCount(len(df))
            
            for row_idx, (_, row) in enumerate(df.iterrows()):
                items = [
                    QTableWidgetItem(str(row['tariff_no'])),
                    QTableWidgetItem(str(row['action'])),
                    QTableWidgetItem(str(row['description'])),
                    QTableWidgetItem(str(row['advalorem_rate'])),
                    QTableWidgetItem(str(row['effective_date'])),
                    QTableWidgetItem(str(row['expiration_date'])),
                    QTableWidgetItem(str(row['specific_rate'])),
                    QTableWidgetItem(str(row['additional_declaration'])),
                    QTableWidgetItem(str(row['note'])),
                    QTableWidgetItem(str(row['link']))
                ]
                
                # Make items editable/read-only based on edit mode
                # Columns that can be edited: Action (1), Description (2), Note (8), Link (9)
                editable_columns = {1, 2, 8, 9}
                for col_idx, item in enumerate(items):
                    if col_idx in editable_columns and self.actions_edit_mode:
                        # Enable editing
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        # Read-only
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                # Apply color coding if toggle is enabled
                if self.actions_color_toggle.isChecked():
                    material_colors = {
                        'Steel': QColor('#e3f2fd'),
                        'Aluminum': QColor('#fff3e0'),
                        'Wood': QColor('#f1f8e9'),
                        'Copper': QColor('#ffe0b2')
                    }
                    
                    action_text = str(row['action']).upper()
                    bg_color = None
                    
                    if 'STEEL' in action_text:
                        bg_color = material_colors['Steel']
                    elif 'ALUMINUM' in action_text:
                        bg_color = material_colors['Aluminum']
                    elif 'COPPER' in action_text:
                        bg_color = material_colors['Copper']
                    elif 'WOOD' in action_text or 'LUMBER' in action_text or 'FURNITURE' in action_text:
                        bg_color = material_colors['Wood']
                    
                    # Apply background color to entire row
                    if bg_color:
                        for item in items:
                            item.setBackground(bg_color)
                
                # Highlight expired actions regardless of toggle state
                if 'EXPIRED' in str(row['note']).upper():
                    for item in items:
                        item.setForeground(QColor('#999999'))  # Gray out expired
                
                # Add items to table
                for col_idx, item in enumerate(items):
                    self.actions_table.setItem(row_idx, col_idx, item)
            
            self.actions_table.setSortingEnabled(True)
            self.actions_count_label.setText(
                f"Total: {len(df)} actions (filtered from {len(self.actions_full_data)})"
            )
            
        except Exception as e:
            logger.error(f"Filter actions table failed: {e}")
            self.actions_table.setRowCount(0)

    def toggle_actions_edit_mode(self):
        """Toggle edit mode for Section 232 Actions table"""
        self.actions_edit_mode = not self.actions_edit_mode

        if self.actions_edit_mode:
            # Entering edit mode
            self.btn_edit_actions.setText("Disable Edit Mode")
            self.btn_edit_actions.setStyleSheet(self.get_button_style("danger"))
            self.btn_save_actions.setVisible(True)
            self.btn_cancel_actions.setVisible(True)
            self.actions_filter.setEnabled(False)
            self.actions_material_filter.setEnabled(False)
            self.actions_color_toggle.setEnabled(False)

            # Store original data for cancel functionality
            if hasattr(self, 'actions_full_data'):
                self.actions_original_data = self.actions_full_data.copy()

            # Re-render table with editable cells
            self.filter_actions_table()
        else:
            # Exiting edit mode (cancel)
            self.cancel_actions_edit()

    def save_actions_changes(self):
        """Save changes made to Section 232 Actions table to database"""
        if not hasattr(self, 'actions_full_data'):
            QMessageBox.warning(self, "No Data", "No actions data to save")
            return

        try:
            # Collect all current table data
            updated_rows = []
            for row_idx in range(self.actions_table.rowCount()):
                row_data = []
                for col_idx in range(self.actions_table.columnCount()):
                    item = self.actions_table.item(row_idx, col_idx)
                    row_data.append(item.text() if item else "")
                updated_rows.append(row_data)

            # Create DataFrame from updated rows
            columns = ['tariff_no', 'action', 'description', 'advalorem_rate',
                      'effective_date', 'expiration_date', 'specific_rate',
                      'additional_declaration', 'note', 'link']
            df_updated = pd.DataFrame(updated_rows, columns=columns)

            # Update database
            conn = sqlite3.connect(str(DB_PATH))
            df_updated.to_sql('sec_232_actions', conn, if_exists='replace', index=False)
            conn.close()

            # Update internal data
            self.actions_full_data = df_updated

            # Exit edit mode
            self.actions_edit_mode = False
            self.btn_edit_actions.setText("Enable Edit Mode")
            self.btn_edit_actions.setStyleSheet(self.get_button_style("warning"))
            self.btn_save_actions.setVisible(False)
            self.btn_cancel_actions.setVisible(False)
            self.actions_filter.setEnabled(True)
            self.actions_material_filter.setEnabled(True)
            self.actions_color_toggle.setEnabled(True)

            # Refresh display
            self.filter_actions_table()

            QMessageBox.information(self, "Success", f"Saved {len(df_updated)} actions to database")
            logger.success(f"Saved {len(df_updated)} Section 232 actions to database")

        except Exception as e:
            logger.error(f"Save actions failed: {e}")
            QMessageBox.critical(self, "Save Failed", f"Error saving changes:\n{str(e)}")

    def cancel_actions_edit(self):
        """Cancel edit mode and discard changes"""
        self.actions_edit_mode = False
        self.btn_edit_actions.setText("Enable Edit Mode")
        self.btn_edit_actions.setStyleSheet(self.get_button_style("warning"))
        self.btn_save_actions.setVisible(False)
        self.btn_cancel_actions.setVisible(False)
        self.actions_filter.setEnabled(True)
        self.actions_material_filter.setEnabled(True)
        self.actions_color_toggle.setEnabled(True)

        # Restore original data if available
        if hasattr(self, 'actions_original_data'):
            self.actions_full_data = self.actions_original_data.copy()
            del self.actions_original_data

        # Refresh display
        self.filter_actions_table()

    def setup_ocr_training_tab(self):
        """OCR Training and Template Customization Tab"""
        layout = QVBoxLayout(self.tab_ocr_training)

        # Title
        title = QLabel("<h2>OCR Training & Template Customization</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Info box
        info_box = QGroupBox("OCR Extraction Patterns")
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "Train the OCR system to recognize invoice data more accurately. "
            "Create supplier-specific templates with custom extraction patterns (regex) "
            "for Part Numbers, Values, and other fields."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)

        # Create splitter for two-column layout
        splitter = QSplitter(Qt.Horizontal)

        # LEFT COLUMN: Template Selection and Management
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Supplier selection
        supplier_group = QGroupBox("Supplier Templates")
        supplier_layout = QVBoxLayout()

        supplier_select_layout = QHBoxLayout()
        supplier_select_layout.addWidget(QLabel("Supplier:"))
        self.ocr_supplier_combo = QComboBox()
        self.ocr_supplier_combo.addItem("(Create New)")
        self.ocr_supplier_combo.currentTextChanged.connect(self.on_ocr_supplier_selected)
        supplier_select_layout.addWidget(self.ocr_supplier_combo)
        supplier_layout.addLayout(supplier_select_layout)

        # Supplier name input for new templates
        supplier_name_layout = QHBoxLayout()
        supplier_name_layout.addWidget(QLabel("New Name:"))
        self.ocr_new_supplier_input = QLineEdit()
        self.ocr_new_supplier_input.setPlaceholderText("e.g., ACME_CORP")
        self.ocr_new_supplier_input.setEnabled(True)  # Enabled by default for creating new templates
        supplier_name_layout.addWidget(self.ocr_new_supplier_input)
        supplier_layout.addLayout(supplier_name_layout)

        # Template buttons
        template_btn_layout = QHBoxLayout()
        btn_load = QPushButton("Load")
        btn_load.setStyleSheet(self.get_button_style("info"))
        btn_load.clicked.connect(self.load_ocr_template)
        template_btn_layout.addWidget(btn_load)

        btn_save = QPushButton("Save")
        btn_save.setStyleSheet(self.get_button_style("success"))
        btn_save.clicked.connect(self.save_ocr_template)
        template_btn_layout.addWidget(btn_save)

        btn_delete = QPushButton("Delete")
        btn_delete.setStyleSheet(self.get_button_style("danger"))
        btn_delete.clicked.connect(self.delete_ocr_template)
        template_btn_layout.addWidget(btn_delete)

        supplier_layout.addLayout(template_btn_layout)
        supplier_group.setLayout(supplier_layout)
        left_layout.addWidget(supplier_group)

        # Test PDF section
        test_group = QGroupBox("Test Extraction")
        test_layout = QVBoxLayout()

        test_btn = QPushButton("Select PDF to Test")
        test_btn.setStyleSheet(self.get_button_style("info"))
        test_btn.clicked.connect(self.select_pdf_for_ocr_test)
        test_layout.addWidget(test_btn)

        self.ocr_test_file_label = QLabel("No file selected")
        self.ocr_test_file_label.setWordWrap(True)
        self.ocr_test_file_label.setStyleSheet("font-size: 8pt; color: #666;")
        test_layout.addWidget(self.ocr_test_file_label)

        test_extract_btn = QPushButton("Run OCR Test")
        test_extract_btn.setStyleSheet(self.get_button_style("success"))
        test_extract_btn.clicked.connect(self.run_ocr_test)
        test_layout.addWidget(test_extract_btn)

        # Visual pattern training button
        visual_btn = QPushButton("Visual Pattern Training")
        visual_btn.setStyleSheet(self.get_button_style("warning"))
        visual_btn.clicked.connect(self.open_visual_pattern_trainer)
        test_layout.addWidget(visual_btn)

        test_group.setLayout(test_layout)
        left_layout.addWidget(test_group)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # RIGHT COLUMN: Pattern Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        patterns_group = QGroupBox("Extraction Patterns (Regex)")
        patterns_layout = QVBoxLayout()

        # Help button
        help_btn = QPushButton("? Pattern Guide")
        help_btn.setStyleSheet(self.get_button_style("info"))
        help_btn.setMaximumWidth(150)
        help_btn.clicked.connect(self.show_pattern_help)
        patterns_layout.addWidget(help_btn)

        # Create scrollable area for patterns
        patterns_scroll = QScrollArea()
        patterns_scroll.setWidgetResizable(True)
        patterns_scroll_widget = QWidget()
        patterns_scroll_layout = QVBoxLayout(patterns_scroll_widget)

        # Pattern fields with descriptions
        self.ocr_patterns = {}
        pattern_descriptions = {
            'part_number_header': (
                'Part Number Header Pattern',
                'Find the column header for part numbers\n'
                'Examples: "Part Number", "SKU", "Item Code", "Part#"\n'
                'Default: (part\\s*(?:number|num|no|#|code|id)|sku|product\\s*(?:number|id|code)|item\\s*(?:number|code))'
            ),
            'part_number_value': (
                'Part Number Value Pattern',
                'Match the actual part number values\n'
                'Examples: "ABC-123", "SKU12345", "PART_001"\n'
                'Default: ([A-Z0-9\\-_.]{3,25})'
            ),
            'value_header': (
                'Value/Price Header Pattern',
                'Find the column header for prices or values\n'
                'Examples: "Price", "Amount", "Total", "Invoice", "Qty"\n'
                'Default: (price|unit\\s*price|value|amount|cost|rate|total|invoice|qty|quantity)'
            ),
            'value_pattern': (
                'Value/Price Pattern',
                'Match numeric price/value amounts\n'
                'Examples: "$100.00", "99.99", "1,500.50"\n'
                'Default: \\$?\\s*(\\d{1,10}(?:[,\\.]?\\d{1,3})*(?:\\.\\d{2})?)'
            ),
            'quantity_pattern': (
                'Quantity Pattern',
                'Find quantity numbers\n'
                'Examples: "qty: 5", "Qty 10", "quantity: 25"\n'
                'Default: qty:?\\s*(\\d+)'
            ),
            'description': (
                'Description Pattern',
                'Find item description fields\n'
                'Examples: "Description", "Item Description", "Desc"\n'
                'Default: (description|desc|item\\s*description)'
            )
        }

        for key, (label, description) in pattern_descriptions.items():
            pattern_layout = QVBoxLayout()
            pattern_layout.addWidget(QLabel(f"<b>{label}</b>"))

            # Description text
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 8pt; color: #666; background: #f5f5f5; padding: 5px; border-radius: 3px;")
            pattern_layout.addWidget(desc_label)

            # Pattern editor
            pattern_edit = QPlainTextEdit()
            pattern_edit.setFixedHeight(40)
            self.ocr_patterns[key] = pattern_edit
            pattern_layout.addWidget(pattern_edit)
            patterns_scroll_layout.addLayout(pattern_layout)

        patterns_scroll_layout.addStretch()
        patterns_scroll.setWidget(patterns_scroll_widget)
        patterns_layout.addWidget(patterns_scroll)

        patterns_group.setLayout(patterns_layout)
        right_layout.addWidget(patterns_group, 1)  # Give patterns proportional space

        # Results display with highlighting support
        results_group = QGroupBox("Extraction Results - Highlight & Name Data Elements")
        results_layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "1. Run OCR Test to extract text\n"
            "2. Select text in results area and right-click\n"
            "3. Choose 'Name This Selection...' to identify data elements\n"
            "4. Highlighted selections will be used to build patterns"
        )
        instructions.setStyleSheet("font-size: 9pt; color: #666; background: #f5f5f5; padding: 5px; border-radius: 3px;")
        instructions.setWordWrap(True)
        results_layout.addWidget(instructions)

        self.ocr_results_text = HighlightableTextEdit()
        self.ocr_results_text.setMinimumHeight(200)
        self.ocr_results_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: monospace;
                font-size: 10px;
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                padding: 5px;
            }
        """)
        results_layout.addWidget(self.ocr_results_text)

        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group, 1)  # Give results proportional space

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)
        self.tab_ocr_training.setLayout(layout)

        # Load available templates
        self.refresh_ocr_templates()

    def refresh_ocr_templates(self):
        """Load and display available OCR templates"""
        try:
            from ocr.field_detector import get_template_manager
            manager = get_template_manager()
            templates = manager.list_templates()

            self.ocr_supplier_combo.blockSignals(True)
            self.ocr_supplier_combo.clear()
            self.ocr_supplier_combo.addItem("(Create New)")

            for template_name in templates:
                self.ocr_supplier_combo.addItem(template_name)

            self.ocr_supplier_combo.blockSignals(False)

            # Ensure the input field is enabled since we start with "(Create New)"
            self.ocr_new_supplier_input.setEnabled(True)
            self.ocr_new_supplier_input.setText("")

        except Exception as e:
            logger.error(f"Error loading templates: {e}")

    def on_ocr_supplier_selected(self, supplier_name):
        """Handle supplier selection in OCR tab"""
        if supplier_name == "(Create New)":
            self.ocr_new_supplier_input.setEnabled(True)
            self.ocr_new_supplier_input.setText("")
            # Clear pattern fields if they exist
            if hasattr(self, 'ocr_patterns'):
                for pattern_edit in self.ocr_patterns.values():
                    pattern_edit.setPlainText("")
        else:
            self.ocr_new_supplier_input.setEnabled(False)
            self.load_ocr_template()

    def show_pattern_help(self):
        """Show detailed help about regex patterns"""
        help_text = """
<h2>OCR Pattern Help - Regex Patterns Explained</h2>

<h3>1. Part Number Header Pattern</h3>
<b>Purpose:</b> Identifies the column header row that contains part numbers
<b>What it does:</b> Looks for text like "Part Number", "SKU", "Item Code"
<b>Example patterns:</b>
• part\\s*number - matches "part number" with any whitespace
• sku - matches "SKU" (case-insensitive)
• item\\s*code - matches "item code"

<h3>2. Part Number Value Pattern</h3>
<b>Purpose:</b> Matches the actual part number values in the data rows
<b>What it does:</b> Extracts values like "ABC-123", "SKU12345", "PART_001"
<b>Example patterns:</b>
• [A-Z0-9\\-_.]{{3,25}} - matches 3-25 alphanumeric characters with dashes/underscores
• [A-Z0-9]+ - matches uppercase letters and numbers only

<h3>3. Value/Price Header Pattern</h3>
<b>Purpose:</b> Identifies the column header for prices or monetary values
<b>What it does:</b> Looks for text like "Price", "Amount", "Total"
<b>Example patterns:</b>
• price - matches "price"
• amount|total|value - matches "amount" OR "total" OR "value"
• unit\\s*price - matches "unit price"

<h3>4. Value/Price Pattern</h3>
<b>Purpose:</b> Extracts actual numeric values from the invoice
<b>What it does:</b> Matches "$100.00", "99.99", "1,500.50"
<b>Example patterns:</b>
• \\d+\\.\\d{{2}} - matches numbers like "100.00"
• \\$?\\s*\\d+ - matches optional "$" followed by numbers

<h3>5. Quantity Pattern</h3>
<b>Purpose:</b> Finds quantity/count information
<b>What it does:</b> Matches "qty: 5", "Qty 10", "quantity: 25"
<b>Example patterns:</b>
• qty:?\\s*\\d+ - matches "qty 5" or "qty: 5"
• \\d+ - matches any number

<h3>6. Description Pattern</h3>
<b>Purpose:</b> Identifies item description columns
<b>What it does:</b> Looks for "Description", "Item Description", "Desc"
<b>Example patterns:</b>
• description - matches "description"
• desc|item\\s*desc - matches "desc" OR "item desc"

<h3>Regex Special Characters</h3>
• \\s = whitespace (space, tab, newline)
• \\d = any digit (0-9)
• + = one or more times
• * = zero or more times
• ? = optional (0 or 1 times)
• | = OR (alternative)
• [A-Z] = any uppercase letter
• [0-9] = any digit
• {{3,25}} = between 3 and 25 times
• () = capture group (returns the matched text)
• \\. = literal period (dot needs backslash)
• \\- = literal hyphen (dash needs backslash)

<h3>Quick Tips</h3>
1. Use parentheses () to capture the part you want extracted
2. Test your patterns with "Run OCR Test" to see results
3. Keep patterns simple - they should match only what you need
4. Use | (OR) to match multiple variations
5. Case matters! Use (?i) for case-insensitive matching
        """

        # Show in a dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Pattern Help")
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setHtml(help_text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec_()

    def load_ocr_template(self):
        """Load selected OCR template"""
        try:
            from ocr.field_detector import get_template_manager
            supplier_name = self.ocr_supplier_combo.currentText()

            if supplier_name == "(Create New)" or not supplier_name:
                return

            manager = get_template_manager()
            template = manager.get_template(supplier_name)

            # Load patterns into UI
            if not hasattr(self, 'ocr_patterns'):
                logger.error("OCR patterns dictionary not initialized")
                return

            for key, pattern_edit in self.ocr_patterns.items():
                pattern = template.patterns.get(key, "")
                pattern_edit.setPlainText(pattern)

            logger.info(f"Loaded OCR template: {supplier_name}")
            QMessageBox.information(self, "Loaded", f"Template '{supplier_name}' loaded successfully")

        except Exception as e:
            logger.error(f"Error loading template: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load template: {str(e)}")

    def save_ocr_template(self):
        """Save OCR template"""
        try:
            from ocr.field_detector import SupplierTemplate, get_template_manager

            supplier_name = self.ocr_supplier_combo.currentText()

            if supplier_name == "(Create New)":
                supplier_name = self.ocr_new_supplier_input.text().strip()
                if not supplier_name:
                    QMessageBox.warning(self, "Invalid Name", "Please enter a supplier name")
                    return

            # Collect patterns from UI
            patterns = {}
            for key, pattern_edit in self.ocr_patterns.items():
                patterns[key] = pattern_edit.toPlainText().strip()

            # Create and save template
            template = SupplierTemplate(supplier_name, patterns=patterns)
            manager = get_template_manager()
            manager.save_template(template)

            logger.success(f"Saved OCR template: {supplier_name}")
            QMessageBox.information(self, "Success", f"Template '{supplier_name}' saved successfully")

            # Refresh template list
            self.refresh_ocr_templates()
            self.ocr_supplier_combo.setCurrentText(supplier_name)

        except Exception as e:
            logger.error(f"Error saving template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save template: {str(e)}")

    def delete_ocr_template(self):
        """Delete OCR template"""
        try:
            supplier_name = self.ocr_supplier_combo.currentText()

            if supplier_name == "(Create New)":
                QMessageBox.warning(self, "No Template", "Please select a template to delete")
                return

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete template '{supplier_name}'?\n\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                from pathlib import Path
                from ocr.field_detector import get_template_manager
                manager = get_template_manager()
                template_file = manager.templates_dir / f"{supplier_name}.json"

                if template_file.exists():
                    template_file.unlink()
                    del manager.templates[supplier_name]

                logger.success(f"Deleted OCR template: {supplier_name}")
                QMessageBox.information(self, "Success", f"Template '{supplier_name}' deleted")

                # Refresh template list
                self.refresh_ocr_templates()

        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete template: {str(e)}")

    def select_pdf_for_ocr_test(self):
        """Select a PDF file to test OCR extraction"""
        pdf_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF for OCR Test", str(INPUT_DIR),
            "PDF Files (*.pdf);;All Files (*.*)"
        )

        if pdf_path:
            self.ocr_test_pdf = pdf_path
            pdf_name = Path(pdf_path).name
            self.ocr_test_file_label.setText(f"Selected: {pdf_name}")

    def run_ocr_test(self):
        """Discover all extractable text from the PDF without applying patterns"""
        if not hasattr(self, 'ocr_test_pdf'):
            QMessageBox.warning(self, "No File", "Please select a PDF first")
            return

        try:
            from ocr.ocr_extract import extract_from_scanned_invoice, preview_extraction

            supplier_name = self.ocr_supplier_combo.currentText()
            if supplier_name == "(Create New)":
                supplier_name = self.ocr_new_supplier_input.text().strip() or "test"

            results = f"=== OCR Text Discovery ===\n\n"
            results += f"PDF: {Path(self.ocr_test_pdf).name}\n"
            results += f"Supplier: {supplier_name}\n\n"

            # Try to extract raw text from the PDF
            raw_text = ""
            extraction_method = ""

            # First try digital PDF extraction
            try:
                preview = preview_extraction(self.ocr_test_pdf, max_lines=500)
                if preview.get('text_preview') and 'Error' not in preview.get('text_preview', ''):
                    raw_text = preview.get('text_preview', '')
                    extraction_method = "Digital PDF (pdfplumber)"
            except Exception:
                pass

            # If no text found, try OCR
            if not raw_text:
                try:
                    df, metadata = extract_from_scanned_invoice(self.ocr_test_pdf, supplier_name)
                    raw_text = metadata.get('raw_text', '')
                    extraction_method = "Scanned PDF (Tesseract OCR)"
                except Exception as ocr_error:
                    results += "=== Error ===\n"
                    results += f"Could not extract text from PDF.\n\n"
                    results += f"Details: {str(ocr_error)}\n\n"
                    results += "Suggestions:\n"
                    results += "1. Check that tesseract-ocr is installed\n"
                    results += "2. PDF may not be a valid image-based document\n"
                    results += "3. Try using Visual Pattern Trainer to manually mark elements\n"
                    self.ocr_results_text.setPlainText(results)
                    logger.error(f"OCR discovery failed: {ocr_error}")
                    return

            if not raw_text:
                results += "=== No Text Found ===\n"
                results += "The PDF does not contain extractable text.\n\n"
                results += "Next Steps:\n"
                results += "1. Use 'Visual Pattern Trainer' to manually mark data elements\n"
                results += "2. Draw boxes around the part numbers, values, and quantities\n"
                results += "3. The trainer will help create patterns for this PDF\n"
                self.ocr_results_text.setPlainText(results)
                logger.warning(f"No text discovered in {Path(self.ocr_test_pdf).name}")
                return

            # Display discovered text
            results += f"=== Extraction Method ===\n{extraction_method}\n\n"
            results += f"=== Extracted Text ({len(raw_text)} chars) ===\n"
            results += "This is all the text discovered in the PDF.\n"
            results += "Use the Visual Pattern Trainer to highlight the data elements.\n\n"
            results += "─" * 60 + "\n"
            results += raw_text
            results += "\n" + "─" * 60 + "\n\n"
            results += "=== Next Steps ===\n"
            results += "1. Review the text above to identify the data you need\n"
            results += "2. Click 'Visual Pattern Trainer' to draw boxes around elements\n"
            results += "3. Name each element (Part Number, Value, Qty, etc.)\n"
            results += "4. Save the pattern when done\n"

            self.ocr_results_text.setPlainText(results)
            logger.info(f"OCR discovery completed: {len(raw_text)} characters extracted")

        except Exception as e:
            logger.error(f"OCR discovery failed: {e}")
            self.ocr_results_text.setPlainText(f"Unexpected Error: {str(e)}\n\nCheck the logs for details.")

    def open_visual_pattern_trainer(self):
        """Open visual PDF pattern training dialog"""
        if not hasattr(self, 'ocr_test_pdf'):
            QMessageBox.warning(self, "No File", "Please select a PDF file first using 'Select PDF to Test'")
            return

        try:
            dialog = PDFPatternTrainerDialog(self.ocr_test_pdf, self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error opening visual trainer: {e}")
            QMessageBox.critical(self, "Error", f"Could not open visual trainer:\n{str(e)}")

    def setup_guide_tab(self):
        layout = QVBoxLayout(self.tab_guide)
        
        # Title
        title = QLabel(f"<h1>{APP_NAME} User Guide</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Guide content
        guide_html = f"""
        <style>
            body {{ font-family: Segoe UI, Arial, sans-serif; }}
            h1 {{ color: #0078D7; text-align: center; border-bottom: 3px solid #0078D7; padding-bottom: 15px; margin-bottom: 30px; }}
            h2 {{ color: #0078D7; border-left: 5px solid #0078D7; padding-left: 15px; margin-top: 30px; margin-bottom: 15px; font-size: 18px; }}
            h3 {{ color: #006D77; margin-top: 20px; margin-bottom: 10px; font-size: 16px; }}
            h4 {{ color: #555; margin-top: 12px; margin-bottom: 8px; font-size: 14px; }}
            p {{ line-height: 1.6; margin: 10px 0; }}

            .section {{ margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
            .step {{ margin-left: 20px; margin-bottom: 12px; line-height: 1.7; }}
            .workflow {{ background-color: #e7f5ff; padding: 15px; border-left: 5px solid #0078D7; margin: 15px 0; border-radius: 3px; }}
            .note {{ background-color: #fff3cd; padding: 12px 15px; border-left: 5px solid #ffc107; margin: 15px 0; border-radius: 3px; }}
            .tip {{ background-color: #d1ecf1; padding: 12px 15px; border-left: 5px solid #0c5460; margin: 15px 0; border-radius: 3px; }}
            .warning {{ background-color: #f8d7da; padding: 12px 15px; border-left: 5px solid #dc3545; margin: 15px 0; border-radius: 3px; }}
            .key-field {{ background-color: #e3f2fd; padding: 8px 12px; border-radius: 3px; display: inline-block; margin: 3px 0; font-weight: 500; }}
            .button-text {{ background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}

            ul {{ margin: 10px 0 10px 25px; line-height: 1.8; }}
            li {{ margin: 5px 0; }}

            .workflow-step {{ margin: 12px 0; padding-left: 25px; }}
            .workflow-step::before {{ content: "→ "; color: #0078D7; font-weight: bold; margin-left: -20px; margin-right: 8px; }}
        </style>
        
        <h2>🚀 Welcome to {APP_NAME}</h2>
        <p>A professional customs documentation processing system for streamlining invoice processing, parts management, and Section 232 tariff compliance.</p>

        <h2>📋 Initial Setup (One-Time Configuration)</h2>
        <p>Complete these steps before your first invoice processing:</p>

        <h3>Step 1: Import Parts Database</h3>
        <div class="workflow">
            <b>Location:</b> <span class="button-text">Parts Import</span> tab<br>
            <div class="workflow-step"><span class="button-text">Load CSV File</span> - Select your parts master CSV</div>
            <div class="workflow-step">Drag column headers to match required fields:
                <ul style="margin-top: 8px;">
                    <li><span class="key-field">Part Number</span> (Required)</li>
                    <li><span class="key-field">HTS Code</span> (Required)</li>
                    <li><span class="key-field">Country of Origin</span> (Required)</li>
                    <li><span class="key-field">MID</span> (Required)</li>
                    <li><span class="key-field">Description</span> (Optional)</li>
                    <li><span class="key-field">Sec 232 Content Ratio</span> (Optional)</li>
                </ul>
            </div>
            <div class="workflow-step"><span class="button-text">IMPORT NOW</span> - Load parts into database</div>
        </div>
        <div class="note">
            <b>💡 Note:</b> Column mappings are automatically saved and reused for future imports from the same source.
        </div>

        <h3>Step 2: Import Section 232 Tariff Codes</h3>
        <div class="workflow">
            <b>Location:</b> <span class="button-text">Customs Config</span> tab<br>
            <h4>Option A: Official CBP Excel File</h4>
            <div class="workflow-step">Click <span class="button-text">Import Section 232 Tariffs</span></div>
            <div class="workflow-step">Select the official CBP Excel file - System auto-imports for Steel, Aluminum, Wood, Copper</div>

            <h4 style="margin-top: 15px;">Option B: Custom CSV File</h4>
            <div class="workflow-step">Click <span class="button-text">Import from CSV</span></div>
            <div class="workflow-step">Map HTS Code and Material columns</div>
            <div class="workflow-step">Choose import mode: Add/Update or Replace All</div>
            <div class="workflow-step">Click <span class="button-text">Import</span></div>
        </div>
        <div class="tip">
            <b>💡 Tip:</b> Use the filter box to quickly search for specific HTS codes or materials.
        </div>

        <h3>Step 3: Create Invoice Mapping Profiles</h3>
        <div class="workflow">
            <b>Location:</b> <span class="button-text">Invoice Mapping Profiles</span> tab<br>
            <div class="workflow-step"><span class="button-text">Load Invoice File</span> - Select CSV, Excel, or PDF from your supplier
                <ul style="margin-top: 8px;">
                    <li><b>CSV/Excel:</b> Auto-detects column headers</li>
                    <li><b>PDF:</b> Automatically extracts tables (uses the largest table if multiple)</li>
                </ul>
            </div>
            <div class="workflow-step">Drag invoice columns to required fields:
                <ul style="margin-top: 8px;">
                    <li><span class="key-field">Part Number</span> - Maps to your parts database</li>
                    <li><span class="key-field">Value USD</span> - Invoice line item value</li>
                </ul>
            </div>
            <div class="workflow-step"><span class="button-text">Save Current Mapping As...</span> - Save with supplier name</div>
        </div>
        <div class="note">
            <b>💡 Note:</b> Create one profile per supplier for quick format switching. PDF support automatically extracts tables from invoices.
        </div>

        <h2>📊 Processing Invoices (Main Workflow)</h2>
        <p><b>Location:</b> <span class="button-text">Process Shipment</span> tab</p>
        <p>The application uses a <b>two-stage verification workflow</b> to prevent data entry errors.</p>

        <h3>Stage 1: Data Preparation</h3>
        <div class="workflow">
            <div class="workflow-step"><b>Select Mapping Profile</b> - Choose the profile matching your supplier's invoice format</div>
            <div class="workflow-step"><b>Load Invoice File</b> - Browse and select your CSV invoice file</div>
            <div class="workflow-step"><b>Enter Required Information:</b>
                <ul style="margin-top: 8px;">
                    <li><span class="key-field">Total Weight</span> - Shipment weight in kg</li>
                    <li><span class="key-field">CI Total</span> - Commercial Invoice total value</li>
                    <li><span class="key-field">MID</span> - Select Manufacturer ID</li>
                </ul>
            </div>
            <div class="workflow-step"><span class="button-text">Process Invoice</span> - Loads raw CSV data for review (2 columns only)</div>
        </div>
        <div class="warning">
            <b>⚠️ Review Stage:</b> Verify the raw data before proceeding. Check for missing parts, incorrect values, or duplicates.
        </div>

        <h3>Stage 2: Processing & Export</h3>
        <div class="workflow">
            <div class="workflow-step"><span class="button-text">Apply Derivatives</span> - Expand to full 13-column data with Section 232 processing</div>
            <div class="workflow-step"><b>Review & Edit (Optional):</b>
                <ul style="margin-top: 8px;">
                    <li>Edit any cell by clicking on it</li>
                    <li><span class="button-text">Add Row</span> - Add missing items</li>
                    <li><span class="button-text">Delete Row</span> - Remove unwanted items</li>
                    <li><span class="button-text">Copy Column</span> - Copy data to clipboard</li>
                </ul>
            </div>
            <div class="workflow-step"><b>Verify Totals Match</b> - Status bar shows green when preview total equals CI Total</div>
            <div class="workflow-step"><span class="button-text">Export Worksheet</span> - Generates Excel file (Output/Upload_Sheet_YYYYMMDD_HHMM.xlsx)</div>
        </div>
        <div class="tip">
            <b>💡 Tip:</b> Double-click exported files in the list to open directly in Excel.
        </div>

        <h2>🔧 Managing Parts Database</h2>
        <p><b>Location:</b> <span class="button-text">Parts View</span> tab</p>
        <div class="section">
            <div class="workflow-step"><b>Quick Search</b> - Filter all fields in real-time</div>
            <div class="workflow-step"><b>SQL Query Builder</b> - Advanced filtering for complex searches</div>
            <div class="workflow-step"><b>Edit Data</b> - Click any cell to modify part information</div>
            <div class="workflow-step"><b>Bulk Operations:</b>
                <ul style="margin-top: 8px;">
                    <li><span class="button-text">Add Row</span> - Create new parts</li>
                    <li><span class="button-text">Delete Selected</span> - Remove parts</li>
                    <li><span class="button-text">Save Changes</span> - Update database</li>
                </ul>
            </div>
        </div>

        <h2>📝 Section 232 Compliance</h2>
        <p><span class="key-field">Section 232</span> refers to national security tariffs on protected materials (Steel, Aluminum, Wood, Copper).</p>
        <p>{APP_NAME} automatically:</p>
        <ul>
            <li>Identifies Section 232-subject items using HTS codes</li>
            <li>Marks them with <b>bold formatting</b> in preview tables</li>
            <li>Calculates percentage breakdowns in exports</li>
            <li>Highlights non-232 items in <b>red font</b></li>
        </ul>

        <h2>❓ Troubleshooting</h2>
        <div class="section">
            <h4>"Process Invoice" button is disabled</h4>
            <ul style="margin-top: 8px;">
                <li>✓ Select a Mapping Profile</li>
                <li>✓ Load an invoice file (use Browse button)</li>
                <li>✓ Enter Total Weight</li>
                <li>✓ Enter CI Total</li>
                <li>✓ Select a MID</li>
            </ul>

            <h4>Totals don't match between preview and CI Total</h4>
            <ul style="margin-top: 8px;">
                <li>Check for missing or duplicate rows</li>
                <li>Verify all line items are in the CSV file</li>
                <li>Edit values directly in the preview table</li>
                <li>Recalculate to confirm match</li>
            </ul>

            <h4>Part not found in database</h4>
            <ul style="margin-top: 8px;">
                <li>Import the part via <span class="button-text">Parts Import</span> tab</li>
                <li>Or add manually in <span class="button-text">Parts View</span> tab with required fields</li>
                <li>Required: Part Number, HTS Code, Country of Origin, MID</li>
            </ul>

            <h4>Need more details</h4>
            <p>Check the <span class="button-text">Log View</span> tab for detailed operation logs and error messages.</p>
        </div>

        <h2>⚡ Keyboard Shortcuts & Features</h2>
        <div class="section">
            <ul>
                <li><b>Ctrl+B</b> - Toggle bold formatting on selected cells</li>
                <li><b>Click column headers</b> - Select entire column for copying</li>
                <li><b>Auto-refresh</b> - Active only on Process Shipment tab (optimized)</li>
                <li><b>File management</b> - Processed files auto-move to Processed folders</li>
                <li><b>Auto-archive</b> - Exports older than 3 days move to Output/Processed</li>
            </ul>
        </div>

        <h2>🎨 Customization</h2>
        <div class="section">
            <p><b>Themes:</b> Click <span class="button-text">⚙ Settings</span> to choose your preferred appearance:</p>
            <ul>
                <li><b>System Default</b> - Windows theme</li>
                <li><b>Fusion (Light)</b> - Clean professional light</li>
                <li><b>Windows</b> - Native Windows appearance</li>
                <li><b>Fusion (Dark)</b> - Modern dark with blue accents</li>
                <li><b>Ocean</b> - Deep blue with teal highlights</li>
                <li><b>Teal Professional</b> - Light with soft teal accents</li>
            </ul>
            <p style="margin-top: 10px;"><b>Folders:</b> Configure input/output directories in Settings</p>
        </div>

        <h2>📞 Support</h2>
        <p><b>For detailed logs and troubleshooting:</b> Check the <span class="button-text">Log View</span> tab</p>
        <p><b>Version:</b> {APP_NAME} {VERSION} | <b>Status:</b> Production Ready</p>
        """
        
        guide_text = QLabel(guide_html)
        guide_text.setWordWrap(True)
        guide_text.setTextFormat(Qt.RichText)
        guide_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        guide_text.setStyleSheet("padding: 20px; background: white; color: #000000;")
        
        scroll_layout.addWidget(guide_text)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.tab_guide.setLayout(layout)

    def on_preview_value_edited(self, item):
        # Only update for Value column edits
        if item.column() != 1:
            return
        text = item.text().replace('$', '').replace(',', '').strip()
        try:
            new_val = float(text)
            if new_val < 0:
                raise ValueError()
            item.setData(Qt.UserRole, new_val)
            item.setText(f"{new_val:,.2f}")
        except Exception:
            old_val = item.data(Qt.UserRole) or 0.0
            item.setText(f"{old_val:,.2f}")
        self.recalculate_total_and_check_match()

    def add_preview_row(self):
        """Add a new empty row to the preview table"""
        if self.last_processed_df is None:
            QMessageBox.warning(self, "No Data", "Please process a shipment first before adding rows.")
            return
        
        # Disconnect signals while adding row
        self.table.blockSignals(True)
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Create default items for the new row
        default_mid = self.selected_mid or ""
        default_melt = str(default_mid)[:2] if default_mid else ""
        
        value_item = QTableWidgetItem("0.00")
        value_item.setData(Qt.UserRole, 0.0)
        value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        
        items = [
            QTableWidgetItem("NEW_PART"),  # Product No
            value_item,  # Value
            QTableWidgetItem(""),  # HTS
            QTableWidgetItem(default_mid),  # MID
            QTableWidgetItem("0.00"),  # Wt
            QTableWidgetItem("CO"),  # Dec
            QTableWidgetItem(default_melt),  # Melt
            QTableWidgetItem(""),  # Cast
            QTableWidgetItem(""),  # Smelt
            QTableWidgetItem(""),  # Flag
            QTableWidgetItem("100.0%"),  # 232%
            QTableWidgetItem(""),  # Non-232%
            QTableWidgetItem("")  # 232 Status
        ]
        
        # Make all items editable except ratios and 232 status
        for i, item in enumerate(items):
            if i not in [10, 11, 12]:  # Not 232%, Non-232%, 232 Status
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.table.setItem(row, i, item)
        
        self.table.blockSignals(False)
        self.recalculate_total_and_check_match()
        logger.info(f"Added new row at position {row + 1}")

    def delete_preview_row(self):
        """Delete selected row(s) from the preview table"""
        if self.last_processed_df is None:
            QMessageBox.warning(self, "No Data", "No preview data to delete.")
            return
        
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select row(s) to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(selected_rows)} row(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Disconnect signals while deleting
        self.table.blockSignals(True)
        
        for row in selected_rows:
            self.table.removeRow(row)
            logger.info(f"Deleted row {row + 1}")
        
        self.table.blockSignals(False)
        self.recalculate_total_and_check_match()
        self.status.setText(f"Deleted {len(selected_rows)} row(s)")

    def copy_column_to_clipboard(self):
        """Copy selected column data to clipboard"""
        if self.last_processed_df is None:
            QMessageBox.warning(self, "No Data", "No preview data available.")
            return
        
        # Get selected cells
        selected = self.table.selectedIndexes()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select cells from a column to copy.")
            return
        
        # Determine if user selected a single column or multiple cells
        columns = set(index.column() for index in selected)
        
        if len(columns) == 1:
            # Single column selected - copy all values from that column
            col = list(columns)[0]
            column_data = []
            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                if item:
                    # For Value column, use the stored float value
                    if col == 1:
                        value = item.data(Qt.UserRole)
                        column_data.append(str(value) if value is not None else "")
                    else:
                        column_data.append(item.text())
                else:
                    column_data.append("")
            
            # Copy to clipboard
            clipboard_text = "\n".join(column_data)
            QApplication.clipboard().setText(clipboard_text)
            
            # Get column name
            header = self.table.horizontalHeaderItem(col)
            col_name = header.text() if header else f"Column {col + 1}"
            QMessageBox.information(self, "Copied", f"Copied {len(column_data)} values from '{col_name}' to clipboard.")
            logger.info(f"Copied column '{col_name}' to clipboard ({len(column_data)} rows)")
        else:
            # Multiple columns or mixed selection - copy selected cells as tab-separated
            # Group by row
            by_row = {}
            for index in selected:
                row = index.row()
                col = index.column()
                if row not in by_row:
                    by_row[row] = {}
                by_row[row][col] = index
            
            # Build clipboard text
            rows_text = []
            for row in sorted(by_row.keys()):
                cells = []
                for col in sorted(by_row[row].keys()):
                    item = self.table.item(row, col)
                    if item:
                        if col == 1:  # Value column
                            value = item.data(Qt.UserRole)
                            cells.append(str(value) if value is not None else "")
                        else:
                            cells.append(item.text())
                    else:
                        cells.append("")
                rows_text.append("\t".join(cells))
            
            clipboard_text = "\n".join(rows_text)
            QApplication.clipboard().setText(clipboard_text)
            QMessageBox.information(self, "Copied", f"Copied {len(selected)} cells to clipboard (tab-separated).")
            logger.info(f"Copied {len(selected)} selected cells to clipboard")

    def select_column(self, column_index):
        """Select entire column when header is clicked"""
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column_index)
            if item:
                item.setSelected(True)

    def save_column_widths(self):
        """Save column widths to database for persistence"""
        try:
            widths = {}
            for col in range(self.table.columnCount()):
                header_text = self.table.horizontalHeaderItem(col).text()
                widths[header_text] = self.table.columnWidth(col)

            import json
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('column_widths', ?)",
                     (json.dumps(widths),))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Could not save column widths: {e}")

    def load_column_widths(self):
        """Load saved column widths from database"""
        try:
            import json
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'column_widths'")
            row = c.fetchone()
            conn.close()

            if row:
                widths = json.loads(row[0])
                for col in range(self.table.columnCount()):
                    header_text = self.table.horizontalHeaderItem(col).text()
                    if header_text in widths:
                        self.table.setColumnWidth(col, widths[header_text])
        except Exception as e:
            logger.debug(f"Could not load column widths: {e}")

    def recalculate_total_and_check_match(self):
        if self.last_processed_df is None:
            return
        total = 0.0
        for i in range(self.table.rowCount()):
            cell = self.table.item(i, 1)
            total += (cell.data(Qt.UserRole) or 0.0) if cell else 0.0
        
        # Don't update CI input - let user keep their target value
        # Just compare the preview total against the CI input
        ci_text = self.ci_input.text().replace(',', '').strip()
        try:
            target_value = float(ci_text) if ci_text else self.csv_total_value
        except:
            target_value = self.csv_total_value
        
        diff = abs(total - target_value)
        threshold = 0.01
        if diff <= threshold:
            self.process_btn.setEnabled(True)
            self.process_btn.setText("Export Worksheet")
            self.process_btn.setFocus()  # Keep focus on button so user can press Enter to export
            self.status.setText("VALUES MATCH → READY TO EXPORT")
            self.status.setStyleSheet("background:#107C10; color:white; font-weight:bold; font-size:16pt;")
        else:
            self.process_btn.setEnabled(False)
            self.process_btn.setText("Export Worksheet (Values Don't Match)")
            self.status.setText(f"Preview: ${total:,.2f} • Target: ${target_value:,.2f}")

    def _process_or_export(self):
        # If no preview yet, run processing; otherwise proceed to export
        if self.last_processed_df is None:
            self.start_processing()
        else:
            self.final_export()


    def final_export(self):
        if self.last_processed_df is None:
            return
        
        # Check if table has rows before attempting export
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Empty Preview", "No data to export. Please process a shipment file first.")
            return
            
        # Ensure totals match prior to export
        running_total = 0.0
        for i in range(self.table.rowCount()):
            cell = self.table.item(i, 1)
            running_total += (cell.data(Qt.UserRole) or 0.0) if cell else 0.0
        
        # Compare against CI input value (what user entered/approved)
        ci_text = self.ci_input.text().replace(',', '').strip()
        try:
            target_value = float(ci_text)
        except:
            target_value = self.csv_total_value
        
        if abs(running_total - target_value) > 0.05:
            QMessageBox.warning(self, "Totals Mismatch", f"Values don't match invoice total.\nPreview: ${running_total:,.2f}\nTarget: ${target_value:,.2f}")
            return

        out = OUTPUT_DIR / (self.last_output_filename or f"Upload_Sheet_{datetime.now():%Y%m%d_%H%M}.xlsx")
        
        # Rebuild DataFrame from current table state (handles added/deleted/edited rows)
        export_data = []
        for i in range(self.table.rowCount()):
            value_cell = self.table.item(i, 1)
            value = value_cell.data(Qt.UserRole) if value_cell else 0.0
            
            # Get steel and non-steel ratios as floats
            steel_text = self.table.item(i, 10).text() if self.table.item(i, 10) else "100.0%"
            nonsteel_text = self.table.item(i, 11).text() if self.table.item(i, 11) else "0.0%"
            steel_ratio = float(steel_text.replace('%', '')) / 100.0
            nonsteel_ratio = float(nonsteel_text.replace('%', '')) / 100.0 if nonsteel_text else 0.0
            
            row_data = {
                'Product No': self.table.item(i, 0).text() if self.table.item(i, 0) else "",
                'ValueUSD': value,
                'HTSCode': self.table.item(i, 2).text() if self.table.item(i, 2) else "",
                'MID': self.table.item(i, 3).text() if self.table.item(i, 3) else "",
                'CalcWtNet': round(float(self.table.item(i, 4).text())) if self.table.item(i, 4) and self.table.item(i, 4).text() else 0,
                'DecTypeCd': self.table.item(i, 5).text() if self.table.item(i, 5) else "CO",
                'CountryofMelt': self.table.item(i, 6).text() if self.table.item(i, 6) else "",
                'CountryOfCast': self.table.item(i, 7).text() if self.table.item(i, 7) else "",
                'PrimCountryOfSmelt': self.table.item(i, 8).text() if self.table.item(i, 8) else "",
                'PrimSmeltFlag': self.table.item(i, 9).text() if self.table.item(i, 9) else "",
                'SteelRatio': steel_ratio,
                'NonSteelRatio': nonsteel_ratio,
                '_232_flag': self.table.item(i, 12).text() if self.table.item(i, 12) else ""
            }
            export_data.append(row_data)
        
        df_out = pd.DataFrame(export_data)
        
        # Build mask BEFORE converting to percentage strings
        nonsteel_mask = df_out['NonSteelRatio'].fillna(0).astype(float) > 0
        df_out['SteelRatio'] = (df_out['SteelRatio'] * 100).round(1).astype(str) + "%"
        df_out['NonSteelRatio'] = (df_out['NonSteelRatio'] * 100).round(1).astype(str) + "%"
        df_out['232_Status'] = df_out['_232_flag'].fillna('')
        cols = ['Product No','ValueUSD','HTSCode','MID','CalcWtNet','DecTypeCd',
                'CountryofMelt','CountryOfCast','PrimCountryOfSmelt','PrimSmeltFlag',
                'SteelRatio','NonSteelRatio','232_Status']
        try:
            t_start = time.time()
            
            # Show export progress indicator
            self.export_progress_widget.show()
            self.export_status_label.setText("Exporting:")
            self.export_progress_bar.setValue(0)
            QApplication.processEvents()
            
            # Check if output directory is on network (slower) or local
            output_str = str(OUTPUT_DIR)
            is_network = output_str.startswith('\\\\') or (len(output_str) > 1 and output_str[1] == ':' and not output_str.startswith('C:'))
            
            # If network path, use local temp then copy (40x faster!)
            if is_network:
                self.bottom_status.setText("Generating export file...")
                self.export_progress_bar.setValue(10)
                QApplication.processEvents()
                
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                    temp_path = Path(tmp.name)
                
                self.export_progress_bar.setValue(20)
                QApplication.processEvents()
                
                with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                    df_out[cols].to_excel(writer, index=False)
                    t_write = time.time() - t_start
                    
                    self.export_progress_bar.setValue(50)
                    QApplication.processEvents()
                    
                    # Apply Arial font to all cells and red font to non-steel rows
                    t_format_start = time.time()
                    ws = next(iter(writer.sheets.values()))

                    # Set Arial font for all cells (including header)
                    arial_font = ExcelFont(name='Arial', size=11, color="00000000")  # Explicit black
                    red_arial_font = ExcelFont(name='Arial', size=11, color="00FF0000")
                    
                    # Apply font to header row
                    for col_idx in range(1, len(cols) + 1):
                        ws.cell(row=1, column=col_idx).font = ExcelFont(name='Arial', size=11, bold=True)
                    
                    # Apply font to data rows
                    nonsteel_indices = [i for i, val in enumerate(nonsteel_mask.tolist()) if val]
                    for row_idx in range(len(df_out)):
                        row_num = row_idx + 2
                        is_nonsteel = row_idx in nonsteel_indices
                        cell_font = red_arial_font if is_nonsteel else arial_font
                        for col_idx in range(1, len(cols) + 1):
                            ws.cell(row=row_num, column=col_idx).font = cell_font
                    
                    t_format = time.time() - t_format_start
                
                self.export_progress_bar.setValue(70)
                QApplication.processEvents()
                
                # Copy to network location
                self.bottom_status.setText("Copying to network location...")
                self.export_status_label.setText("Copying:")
                t_copy_start = time.time()
                out = OUTPUT_DIR / (self.last_output_filename or f"Upload_Sheet_{datetime.now():%Y%m%d_%H%M}.xlsx")
                shutil.copy2(temp_path, out)
                temp_path.unlink()
                t_copy = time.time() - t_copy_start
                
                self.export_progress_bar.setValue(90)
                QApplication.processEvents()
                
                t_total = time.time() - t_start
                logger.info(f"Export timing - Write: {t_write:.2f}s, Format: {t_format:.2f}s, Copy: {t_copy:.2f}s, Total: {t_total:.2f}s")
            else:
                # Local path - direct write
                self.export_progress_bar.setValue(20)
                QApplication.processEvents()
                
                out = OUTPUT_DIR / (self.last_output_filename or f"Upload_Sheet_{datetime.now():%Y%m%d_%H%M}.xlsx")
                with pd.ExcelWriter(out, engine='openpyxl') as writer:
                    df_out[cols].to_excel(writer, index=False)
                    t_write = time.time() - t_start
                    
                    self.export_progress_bar.setValue(60)
                    QApplication.processEvents()
                    
                    # Apply formatting: Arial font, center alignment, auto-sized columns
                    t_format_start = time.time()
                    ws = next(iter(writer.sheets.values()))

                    # Create font and alignment styles
                    red_font = ExcelFont(name="Arial", color="00FF0000")
                    normal_font = ExcelFont(name="Arial", color="00000000")  # Explicit black color
                    center_alignment = Alignment(horizontal="center", vertical="center")

                    # Apply red font to rows where NonSteelRatio > 0, normal font to others
                    nonsteel_indices = [i for i, val in enumerate(nonsteel_mask.tolist()) if val]
                    for row_num in range(2, len(df_out) + 2):  # Start at 2 (after header)
                        is_nonsteel = (row_num - 2) in nonsteel_indices
                        font_to_use = red_font if is_nonsteel else normal_font

                        for col_idx in range(1, len(cols) + 1):
                            cell = ws.cell(row=row_num, column=col_idx)
                            cell.font = font_to_use
                            cell.alignment = center_alignment

                    # Apply Arial font and center alignment to header row
                    for col_idx in range(1, len(cols) + 1):
                        cell = ws.cell(row=1, column=col_idx)
                        cell.font = normal_font
                        cell.alignment = center_alignment

                    # Auto-size columns based on content with padding
                    for col_idx, column in enumerate(ws.columns, 1):
                        max_length = 0
                        column_letter = ws.cell(row=1, column=col_idx).column_letter

                        for cell in column:
                            try:
                                if cell.value:
                                    max_length = max(max_length, len(str(cell.value)))
                            except:
                                pass

                        # Add padding (2 extra characters) and set column width
                        adjusted_width = max_length + 2
                        ws.column_dimensions[column_letter].width = adjusted_width

                    t_format = time.time() - t_format_start
                
                self.export_progress_bar.setValue(90)
                QApplication.processEvents()
                
                t_total = time.time() - t_start
                logger.info(f"Export timing - Write: {t_write:.2f}s, Format: {t_format:.2f}s, Total: {t_total:.2f}s")
            
            self.export_progress_bar.setValue(100)
            QApplication.processEvents()
            
            # Move processed CSV to Processed folder
            if self.current_csv and Path(self.current_csv).exists():
                try:
                    source_file = Path(self.current_csv)
                    dest_file = PROCESSED_DIR / source_file.name
                    
                    # If destination exists, remove it first
                    if dest_file.exists():
                        dest_file.unlink()
                    
                    source_file.rename(dest_file)
                    logger.info(f"Moved processed file: {source_file.name} -> Processed/")
                    self.current_csv = None
                except Exception as e:
                    logger.warning(f"Could not move CSV to Processed folder: {e}")
            
            self.refresh_exported_files()
            self.refresh_input_files()  # Refresh to show file moved
            
            # Hide progress indicator after brief delay
            QTimer.singleShot(500, self.export_progress_widget.hide)
            
            QMessageBox.information(self, "Success", f"Export complete!\nSaved: {out.name}")
            logger.success(f"Export complete: {out.name}")
        except Exception as e:
            self.export_progress_widget.hide()
            QMessageBox.critical(self, "Export Failed", str(e))
            return
        self.clear_all()

    def log_context_menu(self, pos):
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec_(self.log_text.mapToGlobal(pos))
        if action == copy_action:
            self.log_text.copy()

    def copy_log_to_clipboard(self):
        QApplication.clipboard().setText(self.log_text.toPlainText())
        QMessageBox.information(self, "Copied", "Log copied to clipboard!")

    def update_log(self):
        self.log_text.setPlainText(logger.get_logs())
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _install_preview_shortcuts(self):
        # Install Ctrl+B on the preview table to toggle bold on selected cells
        try:
            self._bold_shortcut = QShortcut(QKeySequence("Ctrl+B"), self.table)
            self._bold_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            self._bold_shortcut.activated.connect(self.toggle_preview_bold)
        except Exception:
            pass

    def toggle_preview_bold(self):
        items = self.table.selectedItems()
        if not items:
            return
        # Toggle based on the first selected item's current bold state
        target_bold = not items[0].font().bold()
        for it in items:
            f = it.font()
            f.setBold(target_bold)
            it.setFont(f)

    def load_available_mids(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT DISTINCT mid FROM parts_master WHERE mid IS NOT NULL AND mid != '' ORDER BY mid", conn)
            conn.close()
            self.available_mids = df['mid'].tolist()
            if self.available_mids:
                self.mid_combo.clear()
                self.mid_combo.addItem("-- Select MID --")  # Placeholder item
                self.mid_combo.addItems(self.available_mids)
                self.mid_combo.setCurrentIndex(0)  # Start with placeholder
                self.selected_mid = ""  # No default selection
        except Exception as e:
            logger.error(f"MID load failed: {e}")

    def on_mid_changed(self, text):
        """Handle MID selection change"""
        if text and text != "-- Select MID --":
            self.selected_mid = text
        else:
            self.selected_mid = ""

    def refresh_exported_files(self):
        """Load and display exported files from Output folder"""
        try:
            # Remember current selection and focus state
            current_item = self.exports_list.currentItem()
            current_file = current_item.text() if current_item else None
            had_focus = self.exports_list.hasFocus()

            # Block signals during refresh to prevent triggering events
            self.exports_list.blockSignals(True)
            self.exports_list.clear()
            if OUTPUT_DIR.exists():
                files = sorted(OUTPUT_DIR.glob("Upload_Sheet_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[:20]:  # Show last 20 files
                    self.exports_list.addItem(f.name)

            # Restore selection if the file still exists
            if current_file:
                items = self.exports_list.findItems(current_file, Qt.MatchExactly)
                if items:
                    self.exports_list.setCurrentItem(items[0])
            # If widget had focus but no previous selection, select first item
            elif had_focus and self.exports_list.count() > 0:
                self.exports_list.setCurrentRow(0)

            # Unblock signals after refresh complete
            self.exports_list.blockSignals(False)
        except Exception as e:
            logger.error(f"Refresh exports failed: {e}")
            # Make sure to unblock signals even on error
            self.exports_list.blockSignals(False)

    def refresh_input_files(self):
        """Load and display CSV/Excel files from Input folder"""
        try:
            # Remember current selection and focus state
            current_item = self.input_files_list.currentItem()
            current_file = current_item.text() if current_item else None
            had_focus = self.input_files_list.hasFocus()

            # Block signals during refresh to prevent triggering events
            self.input_files_list.blockSignals(True)
            self.input_files_list.clear()
            if INPUT_DIR.exists():
                # Combine CSV, XLSX, and XLS files
                csv_files = list(INPUT_DIR.glob("*.csv"))
                xlsx_files = list(INPUT_DIR.glob("*.xlsx"))
                xls_files = list(INPUT_DIR.glob("*.xls"))
                files = sorted(csv_files + xlsx_files + xls_files, key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[:50]:  # Show up to 50 files
                    self.input_files_list.addItem(f.name)
            
            # Restore selection if the file still exists
            if current_file:
                items = self.input_files_list.findItems(current_file, Qt.MatchExactly)
                if items:
                    self.input_files_list.setCurrentItem(items[0])
            # If widget had focus but no previous selection, select first item
            elif had_focus and self.input_files_list.count() > 0:
                self.input_files_list.setCurrentRow(0)

            # Unblock signals after refresh complete
            self.input_files_list.blockSignals(False)
        except Exception as e:
            logger.error(f"Refresh input files failed: {e}")
            # Make sure to unblock signals even on error
            self.input_files_list.blockSignals(False)

    def load_selected_input_file(self, item):
        """Load the selected CSV file from Input folder"""
        # Check if a map profile is selected first
        current_profile = self.profile_combo.currentText()
        if not current_profile or current_profile == "-- Select Profile --":
            QMessageBox.warning(self, "No Profile", "Please select a Map Profile first.")
            # Re-enable input fields after modal dialog
            self._enable_input_fields()
            return
        
        try:
            file_path = INPUT_DIR / item.text()
            if file_path.exists():
                self.current_csv = str(file_path)
                self.file_label.setText(file_path.name)
                
                # Clear previous processing state when loading new file
                self.last_processed_df = None
                self.table.setRowCount(0)

                # Read total value - handle both CSV and Excel files
                col_map = {v: k for k, v in self.shipment_mapping.items()}
                if file_path.suffix.lower() == '.xlsx':
                    df = pd.read_excel(file_path, dtype=str)
                else:
                    df = pd.read_csv(file_path, dtype=str)
                df = df.rename(columns=col_map)

                if 'value_usd' in df.columns:
                    total = pd.to_numeric(df['value_usd'], errors='coerce').sum()
                    self.csv_total_value = round(total, 2)
                    # Don't auto-populate CI input - just update the check
                    self.update_invoice_check()  # This will control button state

                self.bottom_status.setText(f"Loaded: {file_path.name}")
                logger.info(f"Loaded: {file_path.name}")

                # Ensure input fields remain editable after loading
                self._enable_input_fields()

                # CRITICAL FIX: Modal dialogs fix the keyboard lock by triggering Qt event processing
                # When "No Profile" dialog is dismissed, _enable_input_fields() is called
                # and the modal event loop refresh fixes keyboard routing
                # Simulate the same effect here by processing events + enabling fields
                QApplication.processEvents()  # Process any pending Qt events
                self._enable_input_fields()  # Re-enable fields (same as after dialog dismissal)

                # Force widget style refresh (same as reselecting profile)
                for widget in [self.ci_input, self.wt_input]:
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)

                # Move keyboard focus to CI input
                self.input_files_list.clearFocus()  # Remove focus from list
                self.ci_input.setFocus(Qt.OtherFocusReason)  # Give focus to CI input
                logger.info(f"[FOCUS] ci_input.hasFocus()={self.ci_input.hasFocus()}")
        except Exception as e:
            logger.error(f"Load input file failed: {e}")
            self.status.setText(f"Error loading file: {e}")
            QMessageBox.warning(self, "Error", f"Could not load file:\n{e}")
            # Ensure fields stay enabled even after error
            self._enable_input_fields()

    def open_exported_file(self, item):
        """Open the selected exported file with user's preferred application"""
        try:
            file_path = OUTPUT_DIR / item.text()
            if file_path.exists():
                import subprocess
                if sys.platform == 'win32':
                    os.startfile(str(file_path))
                elif sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', str(file_path)])
                else:  # Linux and other Unix-like systems
                    # Check user preference for Excel viewer
                    viewer_preference = "System Default"
                    try:
                        conn = sqlite3.connect(str(DB_PATH))
                        c = conn.cursor()
                        c.execute("SELECT value FROM app_config WHERE key = 'excel_viewer'")
                        row = c.fetchone()
                        conn.close()
                        if row:
                            viewer_preference = row[0]
                    except:
                        pass

                    if viewer_preference == "Gnumeric":
                        subprocess.run(['gnumeric', str(file_path)])
                    else:
                        subprocess.run(['xdg-open', str(file_path)])
        except Exception as e:
            logger.error(f"Open file failed: {e}")
            QMessageBox.warning(self, "Error", f"Could not open file:\n{e}")

    def setup_auto_refresh(self):
        """Set up automatic refresh timers for file lists"""
        # Track last modification times to avoid unnecessary refreshes
        self.last_input_mtime = 0
        self.last_output_mtime = 0
        
        # Auto-refresh input files every 10 seconds
        self.input_refresh_timer = QTimer(self)
        self.input_refresh_timer.timeout.connect(self.refresh_input_files_light)
        self.input_refresh_timer.start(10000)  # 10000ms = 10 seconds
        
        # Auto-refresh exported files every 10 seconds
        self.export_refresh_timer = QTimer(self)
        self.export_refresh_timer.timeout.connect(self.refresh_exported_files_light)
        self.export_refresh_timer.start(10000)  # 10000ms = 10 seconds
        
        # Clean up old exported files every 30 minutes
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_old_exports)
        self.cleanup_timer.start(1800000)  # 1800000ms = 30 minutes
        
        # Run cleanup once on startup
        QTimer.singleShot(5000, self.cleanup_old_exports)  # Wait 5 seconds after startup
        
        logger.info("Auto-refresh enabled for file lists (10 second interval)")
    
    def refresh_input_files_light(self):
        """Lightweight refresh - only update if directory has changed and on Process Shipment tab"""
        try:
            # Only refresh if on Process Shipment tab (tab index 0)
            if self.tabs.currentIndex() != 0:
                return
            
            if not INPUT_DIR.exists():
                return
            
            # Check if directory has been modified
            dir_mtime = INPUT_DIR.stat().st_mtime
            if dir_mtime != self.last_input_mtime:
                self.last_input_mtime = dir_mtime
                self.refresh_input_files()
        except:
            pass  # Silently ignore errors during auto-refresh
    
    def refresh_exported_files_light(self):
        """Lightweight refresh - only update if directory has changed and on Process Shipment tab"""
        try:
            # Only refresh if on Process Shipment tab (tab index 0)
            if self.tabs.currentIndex() != 0:
                return
            
            if not OUTPUT_DIR.exists():
                return
            
            # Check if directory has been modified
            dir_mtime = OUTPUT_DIR.stat().st_mtime
            if dir_mtime != self.last_output_mtime:
                self.last_output_mtime = dir_mtime
                self.refresh_exported_files()
        except:
            pass  # Silently ignore errors during auto-refresh
    
    def cleanup_old_exports(self):
        """Move exported files older than 3 days to Output/Processed directory"""
        try:
            if not OUTPUT_DIR.exists():
                return
            
            # Ensure Output/Processed directory exists
            OUTPUT_PROCESSED_DIR.mkdir(exist_ok=True)
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=3)
            moved_count = 0
            
            # Process all .xlsx files in Output directory
            for file_path in OUTPUT_DIR.glob("*.xlsx"):
                try:
                    # Skip if it's a directory
                    if file_path.is_dir():
                        continue
                    
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    # Move if older than 3 days
                    if file_mtime < cutoff_date:
                        dest_path = OUTPUT_PROCESSED_DIR / file_path.name
                        
                        # Handle duplicate filenames
                        if dest_path.exists():
                            base_name = file_path.stem
                            ext = file_path.suffix
                            counter = 1
                            while dest_path.exists():
                                dest_path = OUTPUT_PROCESSED_DIR / f"{base_name}_{counter}{ext}"
                                counter += 1
                        
                        # Move the file
                        shutil.move(str(file_path), str(dest_path))
                        moved_count += 1
                        logger.info(f"Moved old export to Processed: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to move {file_path.name}: {e}")
            
            if moved_count > 0:
                logger.info(f"Cleanup: Moved {moved_count} exported file(s) older than 3 days to Output/Processed")
                # Refresh the exported files list if we're on the Process Shipment tab
                if self.tabs.currentIndex() == 0:
                    self.refresh_exported_files()
        except Exception as e:
            logger.error(f"Cleanup old exports failed: {e}")

if __name__ == "__main__":
    import traceback
    app = QApplication(sys.argv)
    try:
        # Theme will be set by apply_saved_theme() during initialization
        icon_path = TEMP_RESOURCES_DIR / "banner_bg.png"
        if not icon_path.exists():
            icon_path = TEMP_RESOURCES_DIR / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # Create and show splash screen
        splash_widget = QWidget()
        splash_widget.setFixedSize(500, 300)
        splash_widget.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        splash_widget.setAttribute(Qt.WA_TranslucentBackground)
        splash_layout = QVBoxLayout(splash_widget)
        splash_layout.setContentsMargins(0, 0, 0, 0)
        splash_container = QWidget()
        splash_container.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border: 3px solid #0078D4;
                border-radius: 15px;
            }
        """)
        container_layout = QVBoxLayout(splash_container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(20)
        title_label = QLabel(f"<h1 style='color: #0078D4;'>{APP_NAME}</h1>")
        title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title_label)
        splash_message = QLabel("Initializing application\nPlease wait...")
        splash_message.setStyleSheet("color: #f3f3f3; font-size: 12pt; font-weight: bold;")
        splash_message.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(splash_message)
        splash_progress = QProgressBar()
        splash_progress.setRange(0, 100)
        splash_progress.setValue(0)
        splash_progress.setTextVisible(True)
        splash_progress.setFormat("%p%")
        splash_progress.setFixedHeight(20)
        splash_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #1e1e1e;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 3px;
            }
        """)
        container_layout.addWidget(splash_progress)
        splash_layout.addWidget(splash_container)
        splash_widget.show()
        screen_geo = app.desktop().availableGeometry()
        splash_widget.move(
            (screen_geo.width() - splash_widget.width()) // 2,
            (screen_geo.height() - splash_widget.height()) // 2
        )
        app.processEvents()
        
        logger.info("Application started")
        splash_message.setText("Creating main window...\nPlease wait...")
        splash_progress.setValue(10)
        app.processEvents()
        
        win = DerivativeMill()
        win.setWindowTitle(f"{APP_NAME} {VERSION}")
        splash_widget.close()
        win.show()

        def finish_initialization():
            win.status.setText("Initializing application...")
            win.load_config_paths()
            win.status.setText("Applying theme...")
            win.apply_saved_theme()
            win.status.setText("Loading MIDs...")
            win.load_available_mids()
            win.status.setText("Loading profiles...")
            win.load_mapping_profiles()
            win.status.setText("Scanning input files...")
            win.refresh_input_files()
            win.status.setText("Starting auto-refresh...")
            win.setup_auto_refresh()
            win.status.setText("Ready")
            # Final aggressive enable after all initialization
            QTimer.singleShot(0, win._enable_input_fields)
            QTimer.singleShot(100, win._enable_input_fields)
            QTimer.singleShot(500, win._enable_input_fields)
            QTimer.singleShot(1000, win._enable_input_fields)

        # Start initialization after window is shown
        QTimer.singleShot(100, finish_initialization)
        sys.exit(app.exec_())
    except Exception as e:
        error_msg = f"Unhandled Exception:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Application Error", error_msg)
        except Exception:
            pass
        sys.exit(1)
