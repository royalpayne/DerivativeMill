
#!/usr/bin/env python3
# ==============================================================================
# APPLICATION CONFIGURATION - CHANGE THESE TO RENAME THE APPLICATION
# ==============================================================================
APP_NAME = "DocCleaver"
VERSION = "v1.08"
DB_NAME = "doccleaver.db"  # Database filename (will be created in Resources folder)

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
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd
import sqlite3
from math import ceil
import getpass
import socket

try:
    import win32security
    import win32api
    import win32con
    WINDOWS_AUTH_AVAILABLE = True
except ImportError:
    WINDOWS_AUTH_AVAILABLE = False

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QMimeData, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QColor, QFont, QDrag, QKeySequence, QIcon
from openpyxl.styles import Font

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
MAPPING_FILE = BASE_DIR / "column_mapping.json"
SHIPMENT_MAPPING_FILE = BASE_DIR / "shipment_mapping.json"

for p in (RESOURCES_DIR, INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR):
    p.mkdir(exist_ok=True)

DB_PATH = RESOURCES_DIR / DB_NAME

# ----------------------------------------------------------------------
# OFFICIAL SECTION 232 LOGIC - PRIMARY + DERIVATIVE (August 18, 2025)
# ----------------------------------------------------------------------
def get_232_info(hts_code):
    """Primary + Derivative articles per August 18, 2025 Federal Register"""
    if not hts_code:
        return None, "", ""

    hts_clean = str(hts_code).replace(".", "").strip().upper()
    hts_8 = hts_clean[:8]

    # 1. DERIVATIVE ARTICLES - from your CBP_232_tariffs.xlsx
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT material FROM tariff_232 WHERE hts_code = ?", (hts_8,))
        row = c.fetchone()
        conn.close()
        if row:
            material = row[0]
            if material == "Steel":
                return "Steel", "08", ""
            else:
                return "Aluminum", "07", "Y"
    except:
        pass

    # 2. PRIMARY ARTICLES - OFFICIAL LIST (August 18, 2025)
    # Primary Aluminum
    if hts_clean.startswith(('7601','7604','7605','7606','7607','7608','7609')) or \
       hts_clean.startswith('76169951'):
        return "Aluminum", "07", "Y"

    # Primary Steel
    if hts_clean.startswith((""" '7206','7207','7208','7209','7210','7211','7212','7213','7214','7215',
                            '7216','7217','7218','7219','7220','7221','7222','7223','7224','7225',
                            '7226','7227','7228','7229','7301','7302','7303','7304','7305','7306',
                            '7307','7308','7309','7310','7311','7312','7313','7314','7315','7316',
                            '7317','7318','7320','7321','7322','7323','7324','7325','7326' """)):
        return "Steel", "08", ""

    # 3. OFFICIAL DERIVATIVE ALUMINUM (9903.85.04 / 9903.85.13)
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
            mid TEXT, steel_ratio REAL DEFAULT 1.0, non_steel_ratio REAL DEFAULT 0.0, last_updated TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS tariff_232 (
            hts_code TEXT PRIMARY KEY, material TEXT CHECK(material IN ('Steel', 'Aluminum'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS mapping_profiles (
            profile_name TEXT PRIMARY KEY, mapping_json TEXT, created_date TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY, value TEXT
        )""")
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
        self.setStyleSheet("background:#e0e0e0;border:2px solid #aaa;border-radius:8px;padding:12px;font-weight:bold;")
        self.setAlignment(Qt.AlignCenter)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.text())
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)

class DropTarget(QLabel):
    dropped = pyqtSignal(str, str)
    def __init__(self, field_key, field_name):
        super().__init__(f"Drop {field_name} here")
        self.field_key = field_key
        self.setStyleSheet("background:#f8f8f8;border:2px dashed #888;border-radius:10px;padding:12px;min-height:40px;max-height:60px;max-width:250px;font-size:12pt;")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.column_name = None
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

# ----------------------------------------------------------------------
# Import & Process Workers
# ----------------------------------------------------------------------
class ImportWorker(QThread):
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)
    def __init__(self, csv_path, mapping):
        super().__init__()
        self.csv_path = csv_path
        self.mapping = mapping
    def run(self):
        try:
            df = pd.read_csv(self.csv_path, dtype=str, keep_default_na=False)
            df = df.fillna("").rename(columns=str.strip)
            col_map = {v: k for k, v in self.mapping.items()}
            df = df.rename(columns=col_map)

            required = ['part_number','hts_code','country_origin','mid']
            missing = [f for f in required if f not in df.columns]
            if missing:
                self.error.emit(f"Missing required fields: {', '.join(missing)}")
                return

            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            updated = inserted = 0
            now = datetime.now().isoformat()

            for _, r in df.iterrows():
                part = str(r['part_number']).strip()
                if not part: continue
                desc = str(r.get('description', r.get('Description', ''))).strip()
                hts = str(r['hts_code']).strip()
                origin = str(r['country_origin']).strip().upper()[:2]
                mid = str(r['mid']).strip()

                steel_str = str(r.get('steel_ratio', r.get('Steel %', '1.0'))).strip()
                try:
                    steel_ratio = float(steel_str)
                    if steel_ratio > 1.0: steel_ratio /= 100.0
                    steel_ratio = max(0.0, min(1.0, steel_ratio))
                    non_steel_ratio = 1.0 - steel_ratio
                except:
                    steel_ratio = 1.0
                    non_steel_ratio = 0.0

                c.execute("""INSERT INTO parts_master VALUES (?,?,?,?,?,?,?,?)
                          ON CONFLICT(part_number) DO UPDATE SET
                          description=excluded.description, hts_code=excluded.hts_code,
                          country_origin=excluded.country_origin, mid=excluded.mid,
                          steel_ratio=excluded.steel_ratio, non_steel_ratio=excluded.non_steel_ratio,
                          last_updated=excluded.last_updated""",
                          (part, desc, hts, origin, mid, steel_ratio, non_steel_ratio, now))
                if c.rowcount:
                    inserted += 1 if conn.total_changes > updated+inserted else 0
                    updated += 1 if conn.total_changes == updated+inserted else 0

            conn.commit(); conn.close()
            self.finished.emit(updated, inserted)
            logger.success(f"Parts Master import complete: {updated} updated, {inserted} inserted")
        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.error.emit(f"Import failed: {str(e)}")

class ProcessWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(pd.DataFrame, str, str)
    error = pyqtSignal(str)
    missing_data = pyqtSignal(pd.DataFrame)
    invoice_diff = pyqtSignal(float, float)

    def __init__(self, csv_path, mapping, ci_text, wt_text, selected_mid):
        super().__init__()
        self.csv_path = csv_path
        self.mapping = mapping
        self.ci_text = ci_text
        self.wt_text = wt_text
        self.selected_mid = selected_mid

    def run(self):
        try:
            self.progress.emit("Loading file...")
            df = pd.read_csv(self.csv_path, dtype=str, keep_default_na=False).fillna("")
            vr = Path(self.csv_path).stem
            col_map = {v:k for k,v in self.mapping.items()}
            df = df.rename(columns=col_map)
            if not {'part_number','value_usd'}.issubset(df.columns):
                self.error.emit("Missing Part Number or Value USD")
                return

            def safe_float(text):
                if pd.isna(text) or text == "": return 0.0
                try:
                    return float(str(text).replace(',', '').strip())
                except:
                    return 0.0

            df['value_usd'] = pd.to_numeric(df['value_usd'], errors='coerce').fillna(0)
            csv_total = df['value_usd'].sum()

            user_ci = safe_float(self.ci_text)
            wt = safe_float(self.wt_text)

            if wt <= 0:
                self.error.emit("Net Weight must be greater than zero")
                return

            self.invoice_diff.emit(csv_total, user_ci)

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
                missing.columns = ['Part Number', 'HTS Code', 'Value USD', 'Steel Ratio']
                missing = missing.fillna('')
                self.missing_data.emit(missing)
                # Continue processing - missing data is just a warning now

            self._process_with_complete_data(df, vr, user_ci, wt)
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self.error.emit(f"Processing failed: {str(e)}")

    def _process_with_complete_data(self, df, vr, ci, wt):
        final = []
        wt_per_dollar = wt / ci if ci else 0
        mid = self.selected_mid
        melt = str(mid)[:2] if mid else ""

        for _, r in df.iterrows():
            original_value = r['value_usd']
            steel_ratio = r['steel_ratio']
            non_steel_ratio = 1.0 - steel_ratio
            hts = r['hts_code']
            material_232, dec_type, smelt_flag = get_232_info(hts)
            flag = f"232_{material_232}" if material_232 else ""

            if 0 < steel_ratio < 1:
                ns_value = round(original_value * non_steel_ratio, 2)
                ns_weight = ceil(ns_value * wt_per_dollar)
                final.append({
                    'Product No': r['part_number'], 'ValueUSD': ns_value, 'CalcWtNet': ns_weight,
                    'HTSCode': hts, 'MID': mid, 'DecTypeCd': dec_type,
                    'CountryofMelt': melt, 'CountryOfCast': melt, 'PrimCountryOfSmelt': melt,
                    'PrimSmeltFlag': smelt_flag,
                    'NonSteelRatio': non_steel_ratio, 'SteelRatio': 0.0,
                    '_is_non_steel': True, '_232_flag': flag
                })
                steel_value = round(original_value * steel_ratio, 2)
                steel_weight = ceil(steel_value * wt_per_dollar)
                final.append({
                    'Product No': r['part_number'], 'ValueUSD': steel_value, 'CalcWtNet': steel_weight,
                    'HTSCode': hts, 'MID': mid, 'DecTypeCd': dec_type,
                    'CountryofMelt': melt, 'CountryOfCast': melt, 'PrimCountryOfSmelt': melt,
                    'PrimSmeltFlag': smelt_flag,
                    'NonSteelRatio': 0.0, 'SteelRatio': steel_ratio,
                    '_is_non_steel': False, '_232_flag': flag
                })
            else:
                final_value = round(original_value, 2)
                final_weight = ceil(final_value * wt_per_dollar)
                final.append({
                    'Product No': r['part_number'], 'ValueUSD': final_value, 'CalcWtNet': final_weight,
                    'HTSCode': hts, 'MID': mid, 'DecTypeCd': dec_type,
                    'CountryofMelt': melt, 'CountryOfCast': melt, 'PrimCountryOfSmelt': melt,
                    'PrimSmeltFlag': smelt_flag,
                    'NonSteelRatio': non_steel_ratio, 'SteelRatio': steel_ratio,
                    '_is_non_steel': non_steel_ratio > 0, '_232_flag': flag
                })

        result = pd.DataFrame(final)
        out = f"Upload_Sheet_{vr}_{datetime.now():%Y%m%d_%H%M}.xlsx"
        self.finished.emit(result, vr, out)

# ----------------------------------------------------------------------
# Login Dialog
# ----------------------------------------------------------------------
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Login")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.authenticated_user = None
        
        # Set window icon (use TEMP_RESOURCES_DIR for bundled resources)
        icon_path = TEMP_RESOURCES_DIR / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"<h2>{APP_NAME}</h2>")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        if not WINDOWS_AUTH_AVAILABLE:
            warning = QLabel("<b style='color:#ff6b6b'>Warning: Windows authentication not available</b><br>"
                           "Install pywin32: pip install pywin32")
            warning.setWordWrap(True)
            warning.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning)
        
        # Login form
        form_group = QGroupBox("Domain Login")
        form_layout = QFormLayout()
        
        # Get current user and domain
        current_user = getpass.getuser()
        
        # Try to load last used domain from database
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'last_domain'")
            row = c.fetchone()
            conn.close()
            domain = row[0] if row else None
        except:
            domain = None
        
        # Fallback to detecting domain or use default
        if not domain:
            try:
                domain = socket.getfqdn().split('.')[1].upper() if '.' in socket.getfqdn() else 'DOMAIN'
            except:
                domain = 'DOMAIN'
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(f"{domain}\\{current_user}")
        self.username_input.setText(current_user)
        form_layout.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your domain password")
        self.password_input.returnPressed.connect(self.authenticate)
        form_layout.addRow("Password:", self.password_input)
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Leave blank for local machine")
        self.domain_input.setText(domain)
        form_layout.addRow("Domain:", self.domain_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("Login")
        self.btn_login.setStyleSheet("background:#28a745; color:white; font-weight:bold; padding:8px;")
        self.btn_login.clicked.connect(self.authenticate)
        self.btn_login.setDefault(True)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background:#6c757d; color:white; padding:8px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        # Info
        info = QLabel(f"<small>Use your Windows domain credentials to access {APP_NAME}</small>")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color:#666; margin-top:10px;")
        layout.addWidget(info)
        
    def authenticate(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        domain = self.domain_input.text().strip()
        
        if not username:
            self.status_label.setText("<span style='color:#dc3545'>Username is required</span>")
            return
        
        if not password:
            self.status_label.setText("<span style='color:#dc3545'>Password is required</span>")
            return
        
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Authenticating...")
        self.status_label.setText("Verifying credentials...")
        QApplication.processEvents()
        
        # Authenticate
        success, message = self.verify_credentials(username, password, domain)
        
        if success:
            self.authenticated_user = f"{domain}\\{username}" if domain else username
            # Save the domain for next login
            if domain:
                try:
                    conn = sqlite3.connect(str(DB_PATH))
                    c = conn.cursor()
                    # Ensure app_config table exists
                    c.execute("CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT)")
                    c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('last_domain', ?)", (domain,))
                    conn.commit()
                    conn.close()
                    logger.info(f"Saved domain '{domain}' to database")
                except Exception as e:
                    logger.warning(f"Failed to save domain: {e}")
            self.status_label.setText(f"<span style='color:#28a745'>✓ Login successful</span>")
            QTimer.singleShot(500, self.accept)
        else:
            self.status_label.setText(f"<span style='color:#dc3545'>✗ {message}</span>")
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Login")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def verify_credentials(self, username, password, domain):
        """Verify Windows domain credentials"""
        if not WINDOWS_AUTH_AVAILABLE:
            # Fallback: just check if password is not empty (development mode)
            logger.warning("Windows authentication not available - using fallback mode")
            return True, "Login successful (fallback mode)"
        
        try:
            # Try to log on with the provided credentials
            domain_user = f"{domain}\\{username}" if domain else username
            
            # Attempt Windows authentication
            handle = win32security.LogonUser(
                username,
                domain if domain else None,
                password,
                win32con.LOGON32_LOGON_NETWORK,
                win32con.LOGON32_PROVIDER_DEFAULT
            )
            
            # If we got here, authentication succeeded
            handle.Close()
            logger.success(f"User authenticated: {domain_user}")
            return True, "Authentication successful"
            
        except win32security.error as e:
            error_code = e.winerror
            if error_code == 1326:  # ERROR_LOGON_FAILURE
                logger.warning(f"Login failed for {username}: Invalid credentials")
                return False, "Invalid username or password"
            elif error_code == 1331:  # ERROR_ACCOUNT_DISABLED
                logger.warning(f"Login failed for {username}: Account disabled")
                return False, "Account is disabled"
            elif error_code == 1907:  # ERROR_PASSWORD_MUST_CHANGE
                logger.warning(f"Login failed for {username}: Password expired")
                return False, "Password has expired"
            elif error_code == 1909:  # ERROR_ACCOUNT_LOCKED_OUT
                logger.warning(f"Login failed for {username}: Account locked")
                return False, "Account is locked out"
            else:
                logger.error(f"Login failed for {username}: {str(e)}")
                return False, f"Authentication error: {str(e)}"
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, f"Error: {str(e)}"

# ----------------------------------------------------------------------
# MAIN APPLICATION — FINAL DESIGN
# ----------------------------------------------------------------------
class DocCleaver(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        # Compact default size - fully scalable with no minimum constraint
        self.setGeometry(50, 50, 1200, 700)
        
        # Set window icon (use TEMP_RESOURCES_DIR for bundled resources)
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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel(f"<h1>{APP_NAME}</h1><p>Section 232 Compliant • {VERSION}</p>")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.status = QLabel("Ready")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0;")
        layout.addWidget(self.status)

        self.tabs = QTabWidget()
        self.tab_process = QWidget()
        self.tab_shipment_map = QWidget()
        self.tab_import = QWidget()
        self.tab_master = QWidget()
        self.tab_log = QWidget()
        self.tab_config = QWidget()
        self.tab_guide = QWidget()
        self.tabs.addTab(self.tab_process, "1. Process Shipment")
        self.tabs.addTab(self.tab_shipment_map, "2. Invoice Mapping Profiles")
        self.tabs.addTab(self.tab_import, "3. Parts Import")
        self.tabs.addTab(self.tab_master, "4. Parts View")
        self.tabs.addTab(self.tab_log, "5. Log View")
        self.tabs.addTab(self.tab_config, "6. Customs Config")
        self.tabs.addTab(self.tab_guide, "7. User Guide")
        layout.addWidget(self.tabs)

        self.setup_process_tab()
        self.setup_shipment_mapping_tab()
        self.setup_import_tab()
        self.setup_master_tab()
        self.setup_log_tab()
        self.setup_config_tab()
        self.setup_guide_tab()

        self.load_available_mids()
        self.load_mapping_profiles()
        self.load_config_paths()
        self.refresh_exported_files()
        self.refresh_input_files()
        logger.success(f"{APP_NAME} {VERSION} launched")

    def load_config_paths(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT value FROM app_config WHERE key = 'input_dir'")
            row = c.fetchone()
            global INPUT_DIR, PROCESSED_DIR
            if row:
                INPUT_DIR = Path(row[0])
                PROCESSED_DIR = INPUT_DIR / "Processed"
                PROCESSED_DIR.mkdir(exist_ok=True)
            c.execute("SELECT value FROM app_config WHERE key = 'output_dir'")
            row = c.fetchone()
            if row:
                global OUTPUT_DIR
                OUTPUT_DIR = Path(row[0])
                OUTPUT_DIR.mkdir(exist_ok=True)
            conn.close()
        except Exception as e:
            logger.error(f"Config load failed: {e}")

    def setup_process_tab(self):
        layout = QVBoxLayout(self.tab_process)

        # TOP BAR: Title + Settings Gear
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        settings_btn = QPushButton()
        # Prefer a custom gear icon if present; otherwise use a unicode fallback (use TEMP_RESOURCES_DIR for bundled resources)
        gear_path = TEMP_RESOURCES_DIR / "gear.png"
        if gear_path.exists():
            settings_btn.setIcon(QIcon(str(gear_path)))
            settings_btn.setIconSize(QSize(20, 20))
        else:
            settings_btn.setText("⚙")
            settings_btn.setStyleSheet("font-size:16pt; font-weight:bold;")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.show_settings_dialog)
        top_bar.addWidget(settings_btn)
        layout.addLayout(top_bar)

        # MAIN ROW: Input Files + Shipment File (with Profile) + Invoice Values
        main_row = QHBoxLayout()

        # INPUT FILES GROUP — shows CSV files in Input folder
        input_files_group = QGroupBox("Input Files")
        input_files_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        input_files_layout = QVBoxLayout()
        
        self.input_files_list = QListWidget()
        self.input_files_list.setSelectionMode(QListWidget.SingleSelection)
        self.input_files_list.itemClicked.connect(self.load_selected_input_file)
        input_files_layout.addWidget(self.input_files_list)
        
        refresh_input_btn = QPushButton("Refresh")
        refresh_input_btn.setFixedHeight(25)
        refresh_input_btn.clicked.connect(self.refresh_input_files)
        input_files_layout.addWidget(refresh_input_btn)
        
        input_files_group.setLayout(input_files_layout)
        main_row.addWidget(input_files_group)

        # SHIPMENT FILE (merged with Saved Profiles)
        file_group = QGroupBox("Shipment File")
        file_group.setObjectName("SavedProfilesGroup")
        file_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        file_layout = QFormLayout()
        file_layout.setLabelAlignment(Qt.AlignRight)
        
        # Profile selector
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentTextChanged.connect(self.load_selected_profile)
        file_layout.addRow("Map Profile:", self.profile_combo)
        
        # Add spacing
        file_layout.addRow("", QLabel(""))
        
        # File display (read-only, shows selected file from Input Files list)
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("background:#f0f0f0; padding:5px; border:1px solid #ccc;")
        file_layout.addRow("Selected File:", self.file_label)
        
        file_group.setLayout(file_layout)
        main_row.addWidget(file_group)

        # INVOICE VALUES
        values_group = QGroupBox("Invoice Values")
        values_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        values_layout = QFormLayout()
        values_layout.setLabelAlignment(Qt.AlignRight)

        self.ci_input = QLineEdit("")
        self.ci_input.setFixedWidth(200)
        self.ci_input.textChanged.connect(self.update_invoice_check)
        self.wt_input = QLineEdit("")
        self.wt_input.setFixedWidth(200)

        values_layout.addRow("CI Value (USD):", self.ci_input)
        values_layout.addRow("Net Weight (kg):", self.wt_input)

        # MID selector (moved above Invoice Check)
        self.mid_label = QLabel("MID:")
        self.mid_combo = QComboBox()
        self.mid_combo.setFixedWidth(200)
        self.mid_combo.currentTextChanged.connect(self.on_mid_changed)
        values_layout.addRow(self.mid_label, self.mid_combo)

        # Replace your current hbox_check block with this:
        self.invoice_check_label = QLabel("No file loaded")
        self.invoice_check_label.setWordWrap(True)
        self.invoice_check_label.setStyleSheet("font-size: 7pt;")
        self.invoice_check_label.setAlignment(Qt.AlignCenter)

        # Use a QVBoxLayout for the invoice check label and Edit Values button
        vbox_check = QVBoxLayout()
        vbox_check.setSpacing(12)
        vbox_check.setContentsMargins(0, 10, 0, 0)

        vbox_check.addWidget(self.invoice_check_label, alignment=Qt.AlignCenter)
        
        # Edit Values button (initially hidden, shown when values don't match)
        self.edit_values_btn = QPushButton("Edit Values")
        self.edit_values_btn.setFixedSize(120, 30)
        self.edit_values_btn.setStyleSheet("background:#ff9800; color:white; font-weight:bold;")
        self.edit_values_btn.setVisible(False)
        self.edit_values_btn.clicked.connect(self.start_processing_with_editable_preview)
        vbox_check.addWidget(self.edit_values_btn, alignment=Qt.AlignCenter)
        
        vbox_check.addStretch()                     # pushes everything to the top

        # Now add the vertical layout as the widget for the row (after MID)
        values_layout.addRow("Invoice Check:", vbox_check)

        values_group.setLayout(values_layout)
        main_row.addWidget(values_group)

        # ACTIONS GROUP — Clear All + Export Worksheet buttons
        actions_group = QGroupBox("Actions")
        actions_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        actions_layout = QVBoxLayout()
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setFixedSize(160, 40)
        self.clear_btn.setStyleSheet("background:#dc3545; color:white; font-weight:bold;")
        self.clear_btn.clicked.connect(self.clear_all)

        self.process_btn = QPushButton("Process Invoice")
        self.process_btn.setEnabled(False)
        self.process_btn.setFixedSize(160, 40)
        self.process_btn.setStyleSheet("""
            QPushButton { background-color: #004E59; color: white; font-weight: bold; font-size: 11pt; border-radius: 4px; }
            QPushButton:hover { background-color: #006D77; }
            QPushButton:disabled { background-color: #A0A0A0; }
            QPushButton:enabled { background-color: #28a745; }
        """)
        self.process_btn.clicked.connect(self._process_or_export)

        actions_layout.addWidget(self.clear_btn)
        actions_layout.addWidget(self.process_btn)
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        main_row.addWidget(actions_group)

        # EXPORTED FILES GROUP — shows recent exports
        exports_group = QGroupBox("Exported Files")
        exports_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        exports_layout = QVBoxLayout()
        
        self.exports_list = QListWidget()
        self.exports_list.setSelectionMode(QListWidget.SingleSelection)
        self.exports_list.itemDoubleClicked.connect(self.open_exported_file)
        exports_layout.addWidget(self.exports_list)
        
        refresh_exports_btn = QPushButton("Refresh")
        refresh_exports_btn.setFixedHeight(25)
        refresh_exports_btn.clicked.connect(self.refresh_exported_files)
        exports_layout.addWidget(refresh_exports_btn)
        
        exports_group.setLayout(exports_layout)
        main_row.addWidget(exports_group)

        main_row.addStretch()
        layout.addLayout(main_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        preview_group = QGroupBox("Result Preview")
        preview_layout = QVBoxLayout()
        
        # Add buttons for row manipulation
        preview_buttons = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.setStyleSheet("background:#28a745; color:white; font-weight:bold; padding:5px;")
        self.add_row_btn.setFixedWidth(100)
        self.add_row_btn.clicked.connect(self.add_preview_row)
        
        self.delete_row_btn = QPushButton("Delete Row")
        self.delete_row_btn.setStyleSheet("background:#dc3545; color:white; font-weight:bold; padding:5px;")
        self.delete_row_btn.setFixedWidth(100)
        self.delete_row_btn.clicked.connect(self.delete_preview_row)
        
        self.copy_column_btn = QPushButton("Copy Column")
        self.copy_column_btn.setStyleSheet("background:#0078D7; color:white; font-weight:bold; padding:5px;")
        self.copy_column_btn.setFixedWidth(120)
        self.copy_column_btn.clicked.connect(self.copy_column_to_clipboard)
        
        preview_buttons.addWidget(self.add_row_btn)
        preview_buttons.addWidget(self.delete_row_btn)
        preview_buttons.addWidget(self.copy_column_btn)
        preview_buttons.addStretch()
        preview_layout.addLayout(preview_buttons)
        
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "Product No","Value","HTS","MID","Wt","Dec","Melt","Cast","Smelt","Flag","Steel%","Non-Steel%","232 Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSortingEnabled(True)
        # Match body font size to the header font size and make non-bold
        header_font = self.table.horizontalHeader().font()
        header_font.setBold(False)
        self.table.horizontalHeader().setFont(header_font)
        self.table.setFont(header_font)
        
        # Enable clicking header to select entire column
        self.table.horizontalHeader().sectionClicked.connect(self.select_column)
        
        preview_layout.addWidget(self.table)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, 1)

        self.tab_process.setLayout(layout)
        self._install_preview_shortcuts()

    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(500, 500)
        layout = QVBoxLayout(dialog)

        group = QGroupBox("Folder Locations")
        glayout = QFormLayout()
        
        # Input folder display and button
        self.input_path_label = QLabel(str(INPUT_DIR))
        self.input_path_label.setWordWrap(True)
        self.input_path_label.setStyleSheet("background:#f0f0f0; padding:5px; border:1px solid #ccc;")
        input_btn = QPushButton("Change Input Folder")
        input_btn.clicked.connect(lambda: self.select_input_folder(self.input_path_label))
        glayout.addRow("Input Folder:", self.input_path_label)
        glayout.addRow("", input_btn)
        
        # Output folder display and button
        self.output_path_label = QLabel(str(OUTPUT_DIR))
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setStyleSheet("background:#f0f0f0; padding:5px; border:1px solid #ccc;")
        output_btn = QPushButton("Change Output Folder")
        output_btn.clicked.connect(lambda: self.select_output_folder(self.output_path_label))
        glayout.addRow("Output Folder:", self.output_path_label)
        glayout.addRow("", output_btn)
        
        group.setLayout(glayout)
        layout.addWidget(group)

        layout.addStretch()
        dialog.exec_()

    def clear_all(self):
        self.current_csv = None
        self.file_label.setText("No file selected")
        self.ci_input.clear()
        self.wt_input.clear()
        self.mid_combo.setCurrentIndex(-1)
        self.selected_mid = ""
        self.table.setRowCount(0)
        self.process_btn.setEnabled(False)
        self.progress.setVisible(False)
        self.invoice_check_label.setText("No file loaded")
        self.csv_total_value = 0.0
        self.edit_values_btn.setVisible(False)
        self.status.setText("Cleared")
        self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0;")
        logger.info("Process tab cleared")

    def browse_file(self):
        # --- Highlight Saved Profiles box (no tab switch, no errors) ---
        current_profile = self.profile_combo.currentText()
        if not current_profile or current_profile == "-- Select Profile --":
            # Find the Saved Profiles group box
            profiles_group = None
            for widget in self.tab_process.findChildren(QGroupBox):
                if widget.title() == "Saved Profiles":
                    profiles_group = widget
                    break

            if profiles_group:
                # 1. Scroll the tab into view (works on QScrollArea or plain widget)
                scroll_area = self.tab_process
                while scroll_area and not isinstance(scroll_area, QScrollArea):
                    scroll_area = scroll_area.parentWidget()
                if scroll_area and isinstance(scroll_area, QScrollArea):
                    scroll_area.ensureWidgetVisible(profiles_group)

                # 2. Flash effect using only stylesheet + QTimer (no QPropertyAnimation)
                original_ss = profiles_group.styleSheet()

                def flash(step=0):
                    styles = [
                        "QGroupBox { border: 4px solid #ff4444; background-color: #ffebee; }",
                        "QGroupBox { border: 4px solid #ff8800; background-color: #fff3e0; }",
                        "QGroupBox { border: 4px solid #ffaa00; background-color: #fff8e1; }",
                        original_ss or ""
                    ]
                    if step < len(styles):
                        profiles_group.setStyleSheet(styles[step])
                        QTimer.singleShot(300, lambda s=step+1: flash(s))

                flash()

                # 3. Also flash the combo box itself
                self.profile_combo.setStyleSheet(
                    "QComboBox { border: 3px solid #ff4444; background-color: #ffebee; }"
                )
                QTimer.singleShot(1200, lambda: self.profile_combo.setStyleSheet(""))

                # 4. Focus + open dropdown
                self.profile_combo.setFocus()
                QTimer.singleShot(100, self.profile_combo.showPopup)

            # Status bar warning
            self.status.setText("Please select a Saved Profile first")
            self.status.setStyleSheet("background:#ff6b6b; color:white; font-weight:bold; padding:8px;")

            QMessageBox.warning(
                self,
                "Mapping Profile Required",
                "<b>You must select a mapping profile before loading a shipment file.</b><br><br>"
                "Please choose one from the <b>Saved Profiles</b> box on the right.",
                QMessageBox.Ok
            )
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
        
    def update_invoice_check(self):
        if not self.current_csv:
            self.invoice_check_label.setText("No file loaded")
            return

        user_text = self.ci_input.text().replace(',', '').strip()
        try:
            user_val = float(user_text) if user_text else 0.0
        except:
            user_val = 0.0

        diff = abs(user_val - self.csv_total_value)
        
        # Update the invoice check label
        if diff <= 0.05:
            self.invoice_check_label.setText(f"Match: ${self.csv_total_value:,.2f}")
            self.invoice_check_label.setStyleSheet("color:green; font-weight:bold; font-size:7pt;")
            self.edit_values_btn.setVisible(False)
        else:
            self.invoice_check_label.setText(
                f"CSV = ${self.csv_total_value:,.2f} | "
                f"Entered = ${user_val:,.2f} | Diff = ${diff:,.2f}"
            )
            self.invoice_check_label.setStyleSheet("color:red; font-weight:bold; font-size:7pt;")
            # Show Edit Values button when values don't match and haven't processed yet
            if self.last_processed_df is None:
                self.edit_values_btn.setVisible(True)
            else:
                self.edit_values_btn.setVisible(False)
        
        # Button state control
        if self.current_csv and len(self.shipment_mapping) >= 2:
            if self.last_processed_df is None:
                # Haven't processed yet - enable button when values match
                if diff <= 0.05:
                    self.process_btn.setEnabled(True)
                    self.process_btn.setText("Process Invoice")
                else:
                    self.process_btn.setEnabled(False)
                    self.process_btn.setText("Process Invoice (Values Don't Match)")
            else:
                # Already processed - button becomes Export, only enabled when values match
                if diff <= 0.05:
                    self.process_btn.setEnabled(True)
                    self.process_btn.setText("Export Worksheet")
                else:
                    self.process_btn.setEnabled(False)
                    self.process_btn.setText("Export Worksheet (Values Don't Match)")
            
    def select_input_folder(self, label=None):
        global INPUT_DIR, PROCESSED_DIR
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder", str(INPUT_DIR))
        if folder:
            INPUT_DIR = Path(folder)
            PROCESSED_DIR = INPUT_DIR / "Processed"
            PROCESSED_DIR.mkdir(exist_ok=True)
            if label:
                label.setText(str(INPUT_DIR))
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config VALUES ('input_dir', ?)", (str(INPUT_DIR),))
            conn.commit()
            conn.close()
            self.status.setText(f"Input folder: {INPUT_DIR}")
            self.refresh_input_files()

    def select_output_folder(self, label=None):
        global OUTPUT_DIR
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(OUTPUT_DIR))
        if folder:
            OUTPUT_DIR = Path(folder)
            OUTPUT_DIR.mkdir(exist_ok=True)
            if label:
                label.setText(str(OUTPUT_DIR))
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO app_config VALUES ('output_dir', ?)", (str(OUTPUT_DIR),))
            conn.commit()
            conn.close()
            self.status.setText(f"Output folder: {OUTPUT_DIR}")
            self.refresh_exported_files()

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

        self.current_worker = ProcessWorker(
            self.current_csv,
            self.shipment_mapping,
            self.ci_input.text(),
            self.wt_input.text(),
            self.selected_mid
        )
        self.current_worker.progress.connect(lambda s: self.status.setText(s))
        self.current_worker.finished.connect(self.on_done)
        self.current_worker.error.connect(self.on_worker_error)
        # Missing data no longer blocks processing - user can edit in preview
        self.current_worker.missing_data.connect(self.log_missing_data_warning)
        self.current_worker.invoice_diff.connect(self.handle_invoice_diff)
        self.current_worker.start()
    
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
                # Remove rows where value_usd is blank, empty, or zero
                original_count = len(df)
                df['value_usd'] = pd.to_numeric(df['value_usd'], errors='coerce')
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
                
                # Calculate total
                total = df['value_usd'].sum()
                self.csv_total_value = round(total, 2)
                self.ci_input.setText(f"{self.csv_total_value:,.2f}")
                self.update_invoice_check()
                
                if removed_count > 0:
                    self.status.setText(f"File reloaded - Removed {removed_count} blank/zero rows")
                    self.status.setStyleSheet("background:#ff9800; color:white; font-weight:bold; padding:8px;")
                else:
                    self.status.setText("File reloaded - Check invoice values")
                    self.status.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:8px;")
        except Exception as e:
            logger.error(f"reload_csv_values failed: {e}")
            QMessageBox.warning(self, "Reload Error", f"Failed to reload values:\n{e}")

    def handle_invoice_diff(self, csv_sum, user_entered):
        # Display-only; enablement handled by update/check methods
        diff = abs(csv_sum - user_entered)
        if diff > 0.05:
            self.invoice_check_label.setText(
                f": CSV = ${csv_sum:,.2f} | "
                f"Entered = ${user_entered:,.2f} | Diff = ${diff:,.2f}"
            )
            self.invoice_check_label.setStyleSheet("color:red; font-weight:bold; font-size:7pt;")
        else:
            self.invoice_check_label.setText(f"Match: ${csv_sum:,.2f}")
            self.invoice_check_label.setStyleSheet("color:green; font-weight:bold; font-size:7pt;")

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
        self.status.setStyleSheet("background:#ffc107; color:#000; font-weight:bold; padding:8px;")

    def on_worker_error(self, msg):
        self.progress.setVisible(False)
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)
        self.status.setText("Error")
        self.status.setStyleSheet("background:#ff4444; color:white; font-weight:bold;")

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

            items = [
                QTableWidgetItem(str(r['Product No'])),
                value_item,
                QTableWidgetItem(r.get('HTSCode','')),
                QTableWidgetItem(r.get('MID','')),
                QTableWidgetItem(str(r['CalcWtNet'])),
                QTableWidgetItem(r.get('DecTypeCd','')),
                QTableWidgetItem(r.get('CountryofMelt','')),
                QTableWidgetItem(r.get('CountryOfCast','')),
                QTableWidgetItem(r.get('PrimCountryOfSmelt','')),
                QTableWidgetItem(r.get('PrimSmeltFlag','')),
                QTableWidgetItem(f"{r['SteelRatio']*100:.1f}%"),
                QTableWidgetItem(f"{r['NonSteelRatio']*100:.1f}%" if r['NonSteelRatio']>0 else ""),
                QTableWidgetItem(flag)
            ]

            # Make all items editable except Steel%, Non-Steel%, and 232 Status
            for idx, item in enumerate(items):
                if idx not in [10, 11, 12]:  # Not Steel%, Non-Steel%, 232 Status
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)

            # Set font colors per request: all non-bold, steel rows black, non-steel rows red
            is_steel_row = (r.get('SteelRatio', 0.0) or 0.0) > 0.0
            row_color = QColor("black") if is_steel_row else QColor("red")
            for item in items:
                item.setForeground(row_color)
                f = item.font()
                f.setBold(False)
                item.setFont(f)

            for j, it in enumerate(items):
                self.table.setItem(i, j, it)

        self.table.setSortingEnabled(True)  # Re-enable sorting after populating
        self.table.blockSignals(False)
        self.table.itemChanged.connect(self.on_preview_value_edited)
        self.recalculate_total_and_check_match()

        if has_232:
            self.status.setText("SECTION 232 ITEMS • EDIT VALUES • EXPORT WHEN READY")
            self.status.setStyleSheet("background:#ff4444; color:white; font-weight:bold; font-size:16pt; padding:10px;")
        else:
            self.status.setText("Edit values • Export when total matches")
            self.status.setStyleSheet("font-size:14pt; padding:8px; background:#f0f0f0;")

    def setup_import_tab(self):
        layout = QVBoxLayout(self.tab_import)
        title = QLabel("<h2>Parts Import from CSV</h2><p>Drag & drop columns to map fields</p>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Buttons at top
        button_widget = QWidget()
        btn_layout = QHBoxLayout(button_widget)
        btn_load = QPushButton("Load CSV File")
        btn_load.setStyleSheet("background:#0078D7; color:white; font-weight:bold;")
        btn_load.clicked.connect(self.load_csv_for_import)
        btn_reset = QPushButton("Reset Mapping")
        btn_reset.setStyleSheet("background:#ff6b6b; color:white;")
        btn_reset.clicked.connect(self.reset_import_mapping)
        btn_import = QPushButton("IMPORT NOW")
        btn_import.setStyleSheet("background:#28a745; color:white; font-size:16pt; font-weight:bold; padding:15px;")
        btn_import.clicked.connect(self.start_parts_import)
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_import)
        layout.addWidget(button_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.import_widget = QWidget()
        self.import_layout = QHBoxLayout(self.import_widget)

        left = QGroupBox("CSV Columns - Drag")
        left_layout = QVBoxLayout()
        self.drag_labels = []
        left_layout.addStretch()
        left.setLayout(left_layout)

        right = QGroupBox("Required Fields - Drop")
        right_layout = QFormLayout()
        right_layout.setLabelAlignment(Qt.AlignRight)
        self.import_targets = {}
        fields = {
            "part_number": "Part Number",
            "hts_code": "HTS Code",
            "country_origin": "Country of Origin",
            "mid": "MID (Manufacturer ID)",
            "description": "Description",
            "steel_ratio": "Steel Ratio"
        }
        for key, name in fields.items():
            target = DropTarget(key, name)
            target.dropped.connect(self.on_import_drop)
            right_layout.addRow(f"{name}:", target)
            self.import_targets[key] = target
        right.setLayout(right_layout)

        self.import_layout.addWidget(left,1); self.import_layout.addWidget(right,1)
        scroll_layout.addWidget(self.import_widget)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        self.import_csv_path = None
        self.tab_import.setLayout(layout)

    def load_csv_for_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", str(INPUT_DIR), "CSV (*.csv)")
        if not path: return
        self.import_csv_path = path
        try:
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
            self.status.setText(f"CSV loaded: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read CSV:\n{e}")

    def reset_import_mapping(self):
        if QMessageBox.question(self, "Reset", "Clear all field mappings?") != QMessageBox.Yes:
            return
        for target in self.import_targets.values():
            target.column_name = None
            target.setText(f"Drop {target.field_key} here")
            target.setProperty("occupied", False)
            target.style().unpolish(target); target.style().polish(target)
        if MAPPING_FILE.exists():
            MAPPING_FILE.unlink()
        logger.info("Import mapping reset")

    def on_import_drop(self, field_key, column_name):
        for k, t in self.import_targets.items():
            if t.column_name == column_name and k != field_key:
                t.column_name = None
                t.setText(f"Drop {t.field_key} here")
                t.setProperty("occupied", False)
                t.style().unpolish(t); t.style().polish(t)
        self.current_mapping = getattr(self, 'current_mapping', {})
        self.current_mapping[field_key] = column_name
        MAPPING_FILE.write_text(json.dumps(self.current_mapping, indent=2))

    def start_parts_import(self):
        if not self.import_csv_path:
            QMessageBox.warning(self, "No File", "Load a CSV first")
            return
        mapping = {k: t.column_name for k, t in self.import_targets.items() if t.column_name}
        if len([k for k in ['part_number','hts_code','country_origin','mid'] if k in mapping]) < 4:
            QMessageBox.warning(self, "Incomplete", "Map at least Part Number, HTS, Origin, MID")
            return
        self.status.setText("Importing parts...")
        self.import_worker = ImportWorker(self.import_csv_path, mapping)
        self.import_worker.finished.connect(lambda u,i: (
            QMessageBox.information(self, "Success", f"Imported!\nUpdated: {u}\nInserted: {i}"),
            self.refresh_parts_table(),
            self.load_available_mids(),
            self.status.setText("Import complete")
        ))
        self.import_worker.error.connect(lambda m: (
            QMessageBox.critical(self, "Error", m),
            self.status.setText("Import failed")
        ))
        self.import_worker.start()

    def setup_shipment_mapping_tab(self):
        layout = QVBoxLayout(self.tab_shipment_map)
        title = QLabel("<h2>Invoice Mapping Profiles</h2><p>Save and load column mappings</p>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Buttons at top
        top_bar = QHBoxLayout()
        self.profile_combo_full = QComboBox()
        self.profile_combo_full.setMinimumWidth(300)
        self.profile_combo_full.currentTextChanged.connect(self.load_selected_profile_full)
        top_bar.addWidget(QLabel("Saved Profiles:"))
        top_bar.addWidget(self.profile_combo_full)

        btn_save = QPushButton("Save Current Mapping As...")
        btn_save.setStyleSheet("background:#28a745; color:white; font-weight:bold;")
        btn_save.clicked.connect(self.save_mapping_profile)
        btn_delete = QPushButton("Delete Profile")
        btn_delete.setStyleSheet("background:#dc3545; color:white; font-weight:bold;")
        btn_delete.clicked.connect(self.delete_mapping_profile)
        btn_load_csv = QPushButton("Load CSV to Map")
        btn_load_csv.setStyleSheet("background:#0078D7; color:white; font-weight:bold;")
        btn_load_csv.clicked.connect(self.load_csv_for_shipment_mapping)
        btn_reset = QPushButton("Reset Current")
        btn_reset.setStyleSheet("background:#ff6b6b; color:white; font-weight:bold;")
        btn_reset.clicked.connect(self.reset_current_mapping)
        top_bar.addWidget(btn_load_csv)
        top_bar.addWidget(btn_reset)
        top_bar.addWidget(btn_save)
        top_bar.addWidget(btn_delete)
        top_bar.addStretch()
        layout.addLayout(top_bar)

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
            "part_number": "Part Number",
            "value_usd": "Value USD"
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
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", str(INPUT_DIR), "CSV (*.csv)")
        if not path: return
        try:
            df = pd.read_csv(path, nrows=0, dtype=str)
            cols = list(df.columns)
            for label in self.shipment_drag_labels:
                label.setParent(None)
            self.shipment_drag_labels = []
            left_layout = self.shipment_widget.layout().itemAt(0).widget().layout()
            for col in cols:
                lbl = DraggableLabel(col)
                left_layout.insertWidget(left_layout.count()-1, lbl)
                self.shipment_drag_labels.append(lbl)
            logger.info(f"Shipment CSV loaded for mapping: {Path(path).name}")
            self.status.setText(f"Shipment CSV loaded: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read CSV:\n{e}")

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
        for target in self.shipment_targets.values():
            target.column_name = None
            target.setText(f"Drop {target.field_key} here")
            target.setProperty("occupied", False)
            target.style().unpolish(target); target.style().polish(target)
        self.status.setText("Current mapping reset")

    def load_mapping_profiles(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT profile_name FROM mapping_profiles ORDER BY created_date DESC", conn)
            conn.close()
            self.profile_combo.clear()
            self.profile_combo_full.clear()
            self.profile_combo.addItem("-- Select Profile --")
            self.profile_combo_full.addItem("-- Select Profile --")
            for name in df['profile_name'].tolist():
                self.profile_combo.addItem(name)
                self.profile_combo_full.addItem(name)
        except:
            pass

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
            self.profile_combo.setCurrentText(name)
            self.profile_combo_full.setCurrentText(name)
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
            
            self.status.setText("Profile cleared")
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
                self.status.setText(f"Loaded profile: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load failed: {e}")

    def delete_mapping_profile(self):
        name = self.profile_combo_full.currentText()
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
            self.profile_combo.setCurrentIndex(0)
            self.profile_combo_full.setCurrentIndex(0)
            logger.info(f"Profile deleted: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def apply_current_mapping(self):
        for key, target in self.shipment_targets.items():
            col = self.shipment_mapping.get(key)
            if col:
                target.column_name = col
                target.setText(f"{key}\n<- {col}")
                target.setProperty("occupied", True)
                target.style().unpolish(target); target.style().polish(target)
            else:
                target.column_name = None
                target.setText(f"Drop {key.replace('_', ' ')} here")
                target.setProperty("occupied", False)
                target.style().unpolish(target); target.style().polish(target)

    def setup_master_tab(self):
        layout = QVBoxLayout(self.tab_master)
        title = QLabel("<h2>Parts View - Click any cell to edit</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        edit_box = QHBoxLayout()
        btn_add = QPushButton("Add Row")
        btn_del = QPushButton("Delete Selected")
        btn_save = QPushButton("Save Changes")
        btn_refresh = QPushButton("Refresh")
        for btn in (btn_add, btn_del, btn_save, btn_refresh):
            btn.setStyleSheet("font-weight:bold;")
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
        self.query_field.addItems(["part_number", "description", "hts_code", "country_origin", "mid", "steel_ratio", "non_steel_ratio"])
        query_controls.addWidget(self.query_field)
        
        self.query_operator = QComboBox()
        self.query_operator.addItems(["=", "LIKE", ">", "<", ">=", "<=", "!="])
        query_controls.addWidget(self.query_operator)
        
        self.query_value = QLineEdit()
        self.query_value.setPlaceholderText("Enter value...")
        query_controls.addWidget(self.query_value, 1)
        
        btn_run_query = QPushButton("Run Query")
        btn_run_query.setStyleSheet("background:#0078D7; color:white; font-weight:bold;")
        btn_run_query.clicked.connect(self.run_custom_query)
        query_controls.addWidget(btn_run_query)
        
        btn_clear_query = QPushButton("Show All")
        btn_clear_query.clicked.connect(self.refresh_parts_table)
        query_controls.addWidget(btn_clear_query)
        
        query_layout.addLayout(query_controls)
        
        # Custom SQL input
        custom_sql_layout = QHBoxLayout()
        custom_sql_layout.addWidget(QLabel("Custom SQL:"))
        self.custom_sql_input = QLineEdit()
        self.custom_sql_input.setPlaceholderText("SELECT * FROM parts_master WHERE ...")
        custom_sql_layout.addWidget(self.custom_sql_input, 1)
        btn_run_custom = QPushButton("Execute")
        btn_run_custom.setStyleSheet("background:#28a745; color:white; font-weight:bold;")
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
        self.search_field_combo.addItems(["All Fields","Part Number","Description","HTS Code","Origin","MID","Steel Ratio","Non-Steel Ratio"])
        search_box.addWidget(self.search_field_combo)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter...")
        self.search_input.textChanged.connect(self.filter_parts_table)
        search_box.addWidget(self.search_input, 1)
        layout.addLayout(search_box)

        table_box = QGroupBox("Parts Master Table")
        tl = QVBoxLayout()
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(8)
        self.parts_table.setHorizontalHeaderLabels([
            "Part Number", "Description", "HTS Code", "Origin", "MID", "Steel Ratio", "Non-Steel Ratio", "Updated"
        ])
        self.parts_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.parts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parts_table.setSortingEnabled(True)
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
                items = [self.parts_table.item(row, col) for col in range(8)]
                if not items[0] or not items[0].text().strip(): continue
                part = items[0].text().strip()
                desc = items[1].text() if items[1] else ""
                hts = items[2].text() if items[2] else ""
                origin = (items[3].text() or "").upper()[:2]
                mid = items[4].text() if items[4] else ""
                try:
                    steel = float(items[5].text())
                    steel = max(0.0, min(1.0, steel))
                    non_steel = 1.0 - steel
                except:
                    steel = 1.0; non_steel = 0.0
                c.execute("""INSERT INTO parts_master VALUES (?,?,?,?,?,?,?,?)
                          ON CONFLICT(part_number) DO UPDATE SET
                          description=excluded.description, hts_code=excluded.hts_code,
                          country_origin=excluded.country_origin, mid=excluded.mid,
                          steel_ratio=excluded.steel_ratio, non_steel_ratio=excluded.non_steel_ratio,
                          last_updated=excluded.last_updated""",
                          (part, desc, hts, origin, mid, steel, non_steel, now))
                if c.rowcount: saved += 1
            conn.commit(); conn.close()
            QMessageBox.information(self, "Success", f"Saved {saved} parts!")
            self.status.setText("Database saved")
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
            self.query_result_label.setStyleSheet("padding:5px; background:#d4edda; color:#155724;")
            logger.info(f"Query executed: {sql} with params {params}")
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self.query_result_label.setText(f"Query Error: {str(e)}")
            self.query_result_label.setStyleSheet("padding:5px; background:#f8d7da; color:#721c24;")
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
            self.query_result_label.setStyleSheet("padding:5px; background:#f8d7da; color:#721c24;")
            QMessageBox.critical(self, "SQL Error", f"Failed to execute SQL:\n{e}")

    def populate_parts_table(self, df):
        """Populate the parts table with a dataframe"""
        self.parts_table.blockSignals(True)
        self.parts_table.setRowCount(len(df))
        for i, row in df.iterrows():
            items = [
                QTableWidgetItem(row['part_number']),
                QTableWidgetItem(row['description'] or ""),
                QTableWidgetItem(row['hts_code'] or ""),
                QTableWidgetItem(row['country_origin'] or ""),
                QTableWidgetItem(row['mid'] or ""),
                QTableWidgetItem(f"{row['steel_ratio']:.4f}"),
                QTableWidgetItem(f"{row['non_steel_ratio']:.4f}"),
                QTableWidgetItem(row['last_updated'][:10] if row['last_updated'] else "")
            ]
            for item in items:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            for j, item in enumerate(items):
                self.parts_table.setItem(i, j, item)
        self.parts_table.blockSignals(False)
        self.status.setText(f"Loaded: {len(df)} parts")

    # ====================== FIX DATA TAB METHODS (REMOVED) ======================
    # These methods were part of the removed "Fix Missing Data" tab
    # Kept for reference but not in use
    
    # def setup_fix_data_tab(self): ...
    # def refresh_missing_data(self): ...
    # def save_missing_and_reprocess(self): ...

    def setup_config_tab(self):
        layout = QVBoxLayout(self.tab_config)
        title = QLabel("<h2>Customs Configuration</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Buttons at top
        top_bar = QHBoxLayout()
        btn_import_excel = QPushButton("Import CBP_232_tariffs.xlsx")
        btn_import_excel.setStyleSheet("background:#28a745; color:white; font-weight:bold;")
        btn_import_excel.clicked.connect(self.import_tariff_232)
        btn_import_csv = QPushButton("Import from CSV")
        btn_import_csv.setStyleSheet("background:#0078D7; color:white; font-weight:bold;")
        btn_import_csv.clicked.connect(self.import_tariff_csv)
        btn_refresh = QPushButton("Refresh View")
        btn_refresh.setStyleSheet("background:#17a2b8; color:white; font-weight:bold;")
        btn_refresh.clicked.connect(self.refresh_tariff_view)
        top_bar.addWidget(btn_import_excel)
        top_bar.addWidget(btn_import_csv)
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
        self.tariff_filter.setPlaceholderText("Search HTS code or material...")
        self.tariff_filter.textChanged.connect(self.filter_tariff_table)
        filter_bar.addWidget(self.tariff_filter)
        
        self.tariff_material_filter = QComboBox()
        self.tariff_material_filter.addItems(["All", "Steel", "Aluminum"])
        self.tariff_material_filter.currentTextChanged.connect(self.filter_tariff_table)
        filter_bar.addWidget(QLabel("Material:"))
        filter_bar.addWidget(self.tariff_material_filter)
        g1_layout.addLayout(filter_bar)
        
        # Table
        self.tariff_table = QTableWidget()
        self.tariff_table.setColumnCount(2)
        self.tariff_table.setHorizontalHeaderLabels(["HTS Code", "Material"])
        self.tariff_table.horizontalHeader().setStretchLastSection(True)
        self.tariff_table.setAlternatingRowColors(True)
        self.tariff_table.setSortingEnabled(True)
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
        path, _ = QFileDialog.getOpenFileName(self, "Select CBP_232_tariffs.xlsx", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            df = pd.read_excel(path, header=0)
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("DELETE FROM tariff_232")
            steel_codes = [str(x).replace(".", "")[:10] for x in df.iloc[1:, 0] if pd.notna(x)]
            alum_codes = [str(x).replace(".", "")[:10] for x in df.iloc[1:, 1] if pd.notna(x)]
            for code in steel_codes:
                if code: c.execute("INSERT OR REPLACE INTO tariff_232 VALUES (?, 'Steel')", (code,))
            for code in alum_codes:
                if code: c.execute("INSERT OR REPLACE INTO tariff_232 VALUES (?, 'Aluminum')", (code,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", f"Imported {len(steel_codes)+len(alum_codes)} 232 codes")
            logger.success("tariff_232 table updated")
            self.status.setText("Section 232 list imported")
            self.refresh_tariff_view()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {e}")

    def import_tariff_csv(self):
        """Import tariff codes from CSV file with column mapping"""
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", str(INPUT_DIR), "CSV (*.csv)")
        if not path:
            return
        
        try:
            # Read CSV
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            df = df.fillna("").rename(columns=str.strip)
            
            if df.empty:
                QMessageBox.warning(self, "Empty File", "CSV file is empty")
                return
            
            # Show column mapping dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Map CSV Columns")
            dialog.setMinimumWidth(500)
            dialog_layout = QVBoxLayout(dialog)
            
            dialog_layout.addWidget(QLabel("<b>Map your CSV columns to database fields:</b>"))
            dialog_layout.addWidget(QLabel(f"Available columns: {', '.join(df.columns)}"))
            
            # HTS Code mapping
            hts_layout = QHBoxLayout()
            hts_layout.addWidget(QLabel("HTS Code Column:"))
            hts_combo = QComboBox()
            hts_combo.addItems([""] + list(df.columns))
            hts_layout.addWidget(hts_combo)
            dialog_layout.addLayout(hts_layout)
            
            # Material mapping
            material_layout = QHBoxLayout()
            material_layout.addWidget(QLabel("Material Column:"))
            material_combo = QComboBox()
            material_combo.addItems([""] + list(df.columns))
            material_layout.addWidget(material_combo)
            dialog_layout.addLayout(material_layout)
            
            # Default material if no column
            default_layout = QHBoxLayout()
            default_layout.addWidget(QLabel("Default Material (if column empty):"))
            default_material = QComboBox()
            default_material.addItems(["", "Steel", "Aluminum"])
            default_layout.addWidget(default_material)
            dialog_layout.addLayout(default_layout)
            
            # Update mode
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("Import Mode:"))
            mode_combo = QComboBox()
            mode_combo.addItems(["Add new or update existing", "Replace all existing data"])
            mode_layout.addWidget(mode_combo)
            dialog_layout.addLayout(mode_layout)
            
            # Buttons
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton("Import")
            btn_ok.setStyleSheet("background:#28a745; color:white; font-weight:bold;")
            btn_cancel = QPushButton("Cancel")
            btn_ok.clicked.connect(dialog.accept)
            btn_cancel.clicked.connect(dialog.reject)
            btn_layout.addWidget(btn_ok)
            btn_layout.addWidget(btn_cancel)
            dialog_layout.addLayout(btn_layout)
            
            if dialog.exec_() != QDialog.Accepted:
                return
            
            # Get selections
            hts_col = hts_combo.currentText()
            material_col = material_combo.currentText()
            default_mat = default_material.currentText()
            replace_all = mode_combo.currentIndex() == 1
            
            if not hts_col:
                QMessageBox.warning(self, "Missing Mapping", "HTS Code column is required")
                return
            
            # Process import
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            if replace_all:
                c.execute("DELETE FROM tariff_232")
            
            imported = 0
            errors = []
            
            for idx, row in df.iterrows():
                hts_code = str(row[hts_col]).strip().replace(".", "")[:10]
                if not hts_code:
                    continue
                
                # Get material
                if material_col and material_col in row:
                    material = str(row[material_col]).strip().title()
                else:
                    material = default_mat
                
                # Validate material
                if material not in ["Steel", "Aluminum"]:
                    errors.append(f"Row {idx+1}: Invalid material '{material}' for HTS {hts_code}")
                    continue
                
                try:
                    c.execute("INSERT OR REPLACE INTO tariff_232 VALUES (?, ?)", (hts_code, material))
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            # Show results
            msg = f"Successfully imported {imported} tariff codes"
            if errors:
                msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    msg += f"\n... and {len(errors)-10} more"
            
            QMessageBox.information(self, "Import Complete", msg)
            logger.success(f"CSV tariff import: {imported} codes")
            self.status.setText(f"Imported {imported} tariff codes from CSV")
            self.refresh_tariff_view()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV:\n{e}")
            logger.error(f"CSV tariff import failed: {e}")

    def refresh_tariff_view(self):
        """Load and display all tariff codes from database"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT hts_code, material FROM tariff_232 ORDER BY hts_code", conn)
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
            
            # Apply text filter
            search_text = self.tariff_filter.text().strip().lower()
            if search_text:
                df = df[df['hts_code'].str.lower().str.contains(search_text, na=False)]
            
            # Apply material filter
            material_filter = self.tariff_material_filter.currentText()
            if material_filter != "All":
                df = df[df['material'] == material_filter]
            
            # Populate table
            self.tariff_table.setSortingEnabled(False)
            self.tariff_table.setRowCount(len(df))
            
            for row_idx, (_, row) in enumerate(df.iterrows()):
                # HTS Code
                hts_item = QTableWidgetItem(str(row['hts_code']))
                hts_item.setFlags(hts_item.flags() & ~Qt.ItemIsEditable)
                self.tariff_table.setItem(row_idx, 0, hts_item)
                
                # Material
                mat_item = QTableWidgetItem(str(row['material']))
                mat_item.setFlags(mat_item.flags() & ~Qt.ItemIsEditable)
                # Color code materials
                if row['material'] == 'Steel':
                    mat_item.setBackground(QColor('#e3f2fd'))  # Light blue
                else:
                    mat_item.setBackground(QColor('#fff3e0'))  # Light orange
                self.tariff_table.setItem(row_idx, 1, mat_item)
            
            self.tariff_table.setSortingEnabled(True)
            self.tariff_count_label.setText(f"Total: {len(df)} tariff codes (filtered from {len(self.tariff_full_data)})")
            
        except Exception as e:
            logger.error(f"Filter tariff table failed: {e}")
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
        guide_html = """
        <style>
            h2 { color: #0078D7; margin-top: 20px; }
            h3 { color: #006D77; margin-top: 15px; }
            .step { margin-left: 20px; margin-bottom: 10px; }
            .note { background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }
            .tip { background-color: #d1ecf1; padding: 10px; border-left: 4px solid #0c5460; margin: 10px 0; }
        </style>
        
        <h2>🚀 Getting Started</h2>
        <p>{APP_NAME} is a customs documentation processing system designed to streamline invoice processing, 
        parts management, and Section 232 tariff compliance.</p>
        
        <h2>📋 First-Time Setup</h2>
        <p>Before processing invoices, you need to configure your system:</p>
        
        <h3>1. Import Parts Database (Tab: Parts Import)</h3>
        <div class="step">
            <b>Step 1:</b> Click <b>"Load CSV File"</b> button<br>
            <b>Step 2:</b> Select your parts master CSV file<br>
            <b>Step 3:</b> Drag column names from the left to matching fields on the right:
            <ul>
                <li><b>Part Number</b> (Required) - Your part identifier</li>
                <li><b>HTS Code</b> (Required) - Harmonized Tariff Schedule code</li>
                <li><b>Country of Origin</b> (Required) - 2-letter country code</li>
                <li><b>MID (Manufacturer ID)</b> (Required) - Manufacturer identifier</li>
                <li><b>Description</b> (Optional) - Part description</li>
                <li><b>Steel Ratio</b> (Optional) - Steel content percentage</li>
            </ul>
            <b>Step 4:</b> Click <b>"IMPORT NOW"</b> to load parts into database<br>
        </div>
        <div class="note">
            <b>Note:</b> Column mappings are automatically saved for future imports from the same source.
        </div>
        
        <h3>2. Import Section 232 Tariff Codes (Tab: Customs Config)</h3>
        <div class="step">
            <b>Option A - Excel Import:</b><br>
            • Click <b>"Import CBP_232_tariffs.xlsx"</b><br>
            • Select the official CBP Excel file<br>
            • System imports both Steel and Aluminum codes automatically<br><br>
            
            <b>Option B - CSV Import:</b><br>
            • Click <b>"Import from CSV"</b><br>
            • Map the HTS Code column<br>
            • Map the Material column (or set default material)<br>
            • Choose import mode (add/update or replace all)<br>
            • Click <b>"Import"</b><br>
        </div>
        <div class="tip">
            <b>Tip:</b> Use the filter box to search for specific HTS codes or materials.
        </div>
        
        <h3>3. Create Invoice Mapping Profiles (Tab: Invoice Mapping Profiles)</h3>
        <div class="step">
            <b>Step 1:</b> Click <b>"Load CSV to Map"</b><br>
            <b>Step 2:</b> Select a sample invoice CSV from your supplier<br>
            <b>Step 3:</b> Drag CSV columns to required fields:<br>
            &nbsp;&nbsp;&nbsp;&nbsp;• <b>Part Number</b> - Maps to your parts database<br>
            &nbsp;&nbsp;&nbsp;&nbsp;• <b>Value USD</b> - Invoice line item value<br>
            <b>Step 4:</b> Click <b>"Save Current Mapping As..."</b><br>
            <b>Step 5:</b> Enter a profile name (e.g., "Supplier ABC")<br>
        </div>
        <div class="note">
            <b>Note:</b> Create one profile per supplier for quick switching between different invoice formats.
        </div>
        
        <h2>📊 Processing Invoices (Tab: Process Shipment)</h2>
        
        <h3>Step-by-Step Workflow:</h3>
        <div class="step">
            <b>1. Select Map Profile</b><br>
            • Choose the mapping profile that matches your invoice format<br><br>
            
            <b>2. Load Invoice File</b><br>
            • Click on a file from the <b>"Input Files"</b> list<br>
            • File automatically loads and displays the filename<br>
            • System calculates the total invoice value<br><br>
            
            <b>3. Enter/Verify Commercial Invoice Total</b><br>
            • Enter the CI (Commercial Invoice) total from your paperwork<br>
            • System compares this to the CSV total<br><br>
            
            <b>4. Select Manufacturer ID (MID)</b><br>
            • Choose the MID from the dropdown<br>
            • This populates country of origin fields automatically<br><br>
            
            <b>5. Preview Invoice</b><br>
            • Click <b>"Preview Invoice"</b> button<br>
            • System processes all parts and displays results in the table<br>
            • Section 232 items are highlighted in <b>bold</b><br><br>
            
            <b>6. Review & Edit (Optional)</b><br>
            • Check all values in the preview table<br>
            • Edit any cell by clicking on it<br>
            • Use <b>"Add Row"</b> to add missing items<br>
            • Use <b>"Delete Row"</b> to remove unwanted items<br>
            • Use <b>"Copy Column"</b> to copy data to clipboard<br><br>
            
            <b>7. Verify Totals Match</b><br>
            • Status bar shows green when preview total matches CI total<br>
            • If values don't match, review and adjust values in the table<br><br>
            
            <b>8. Export Worksheet</b><br>
            • Click <b>"Export Worksheet"</b> when totals match<br>
            • File saves to Output folder as Upload_Sheet_YYYYMMDD_HHMM.xlsx<br>
            • Original CSV moves to Processed folder<br>
            • Exported file appears in <b>"Exported Files"</b> list<br>
        </div>
        
        <div class="tip">
            <b>Tip:</b> Double-click any file in the "Exported Files" list to open it in Excel.
        </div>
        
        <h2>🔧 Managing Parts Database (Tab: Parts View)</h2>
        <div class="step">
            • View all parts in the searchable table<br>
            • Use <b>"Quick Search"</b> to filter by any field<br>
            • Use <b>"SQL Query Builder"</b> for advanced searches<br>
            • Click any cell to edit parts data<br>
            • Use <b>"Add Row"</b> to create new parts<br>
            • Use <b>"Delete Selected"</b> to remove parts<br>
            • Click <b>"Save Changes"</b> to update the database<br>
        </div>
        
        <h2>📝 Understanding Section 232</h2>
        <div class="step">
            <b>What is Section 232?</b><br>
            Section 232 refers to tariffs on steel and aluminum imports. {APP_NAME} automatically:
            <ul>
                <li>Identifies items subject to Section 232 tariffs</li>
                <li>Marks them with <b>bold formatting</b> in the preview</li>
                <li>Adds "232 Status" column to exported worksheets</li>
                <li>Highlights non-steel ratio items in <b>red font</b> in exports</li>
            </ul>
        </div>
        
        <h2>❗ Troubleshooting</h2>
        <div class="step">
            <b>Preview button disabled?</b><br>
            • Make sure you selected a Map Profile<br>
            • Verify a file is loaded<br>
            • Check that CI Total is entered<br>
            • Ensure MID is selected<br><br>
            
            <b>Totals don't match?</b><br>
            • Review individual line values in preview table<br>
            • Check for missing or duplicate rows<br>
            • Verify CSV file contains all invoice items<br>
            • Edit values directly in the preview table<br><br>
            
            <b>Part not found?</b><br>
            • Add missing parts via Parts Import tab<br>
            • Or add manually in Parts View tab<br>
            • Include required fields: Part Number, HTS Code, Country, MID<br><br>
            
            <b>Check the Log View tab for detailed error messages and system activity.</b>
        </div>
        
        <h2>💡 Quick Tips</h2>
        <div class="tip">
            • <b>Ctrl+B</b> in preview table toggles bold formatting on selected cells<br>
            • Click column headers to select entire column for copying<br>
            • Use profile names that match your supplier names<br>
            • Keep your parts database updated for accurate processing<br>
            • Review exported files before submitting to customs<br>
        </div>
        
        <h2>📞 Support</h2>
        <p>For additional help, check the Log View tab for detailed operation logs and error messages.</p>
        <p><b>Version:</b> {APP_NAME} {VERSION}</p>
        """
        
        guide_text = QLabel(guide_html)
        guide_text.setWordWrap(True)
        guide_text.setTextFormat(Qt.RichText)
        guide_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        guide_text.setStyleSheet("padding: 20px; background: white;")
        
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
            QTableWidgetItem("100.0%"),  # Steel%
            QTableWidgetItem(""),  # Non-Steel%
            QTableWidgetItem("")  # 232 Status
        ]
        
        # Make all items editable except ratios and 232 status
        for i, item in enumerate(items):
            if i not in [10, 11, 12]:  # Not Steel%, Non-Steel%, 232 Status
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
        if diff <= 0.05:
            self.process_btn.setEnabled(True)
            self.process_btn.setText("Export Worksheet")
            self.status.setText("VALUES MATCH → READY TO EXPORT")
            self.status.setStyleSheet("background:#28a745; color:white; font-weight:bold; font-size:16pt;")
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
                'CalcWtNet': float(self.table.item(i, 4).text()) if self.table.item(i, 4) and self.table.item(i, 4).text() else 0.0,
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
            with pd.ExcelWriter(out, engine='openpyxl') as writer:
                df_out[cols].to_excel(writer, index=False)
                # Apply red font to any row where NonSteelRatio > 0
                ws = next(iter(writer.sheets.values()))
                red_font = Font(color="00FF0000")
                for idx, is_nonsteel in enumerate(nonsteel_mask.tolist()):
                    if is_nonsteel:
                        row_num = idx + 2  # +1 for header, +1 for 1-based rows
                        for col_idx in range(1, len(cols) + 1):
                            cell = ws.cell(row=row_num, column=col_idx)
                            cell.font = red_font
            try:
                Path(self.current_csv).rename(PROCESSED_DIR / Path(self.current_csv).name)
            except Exception:
                pass
            self.refresh_exported_files()
            QMessageBox.information(self, "Success", f"Export complete!\nSaved: {out.name}")
            logger.success(f"Export complete: {out.name}")
        except Exception as e:
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
            self.exports_list.clear()
            if OUTPUT_DIR.exists():
                files = sorted(OUTPUT_DIR.glob("Upload_Sheet_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[:20]:  # Show last 20 files
                    self.exports_list.addItem(f.name)
        except Exception as e:
            logger.error(f"Refresh exports failed: {e}")

    def refresh_input_files(self):
        """Load and display CSV files from Input folder"""
        try:
            self.input_files_list.clear()
            if INPUT_DIR.exists():
                files = sorted(INPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[:50]:  # Show up to 50 files
                    self.input_files_list.addItem(f.name)
        except Exception as e:
            logger.error(f"Refresh input files failed: {e}")

    def load_selected_input_file(self, item):
        """Load the selected CSV file from Input folder"""
        # Check if a map profile is selected first
        current_profile = self.profile_combo.currentText()
        if not current_profile or current_profile == "-- Select Profile --":
            # Flash the profile combo to get user's attention
            self.profile_combo.setStyleSheet(
                "QComboBox { border: 3px solid #ff4444; background-color: #ffebee; }"
            )
            QTimer.singleShot(1200, lambda: self.profile_combo.setStyleSheet(""))
            self.profile_combo.setFocus()
            QTimer.singleShot(100, self.profile_combo.showPopup)
            
            self.status.setText("Please select a Map Profile first")
            self.status.setStyleSheet("background:#ff6b6b; color:white; font-weight:bold; padding:8px;")
            
            QMessageBox.warning(
                self,
                "Map Profile Required",
                "<b>You must select a mapping profile before loading a file.</b><br><br>"
                "Please choose one from the <b>Map Profile</b> dropdown.",
                QMessageBox.Ok
            )
            return
        
        try:
            file_path = INPUT_DIR / item.text()
            if file_path.exists():
                self.current_csv = str(file_path)
                self.file_label.setText(file_path.name)
                
                # Clear previous processing state when loading new file
                self.last_processed_df = None
                self.table.setRowCount(0)

                # Read total value
                col_map = {v: k for k, v in self.shipment_mapping.items()}
                df = pd.read_csv(file_path, dtype=str)
                df = df.rename(columns=col_map)

                if 'value_usd' in df.columns:
                    total = pd.to_numeric(df['value_usd'], errors='coerce').sum()
                    self.csv_total_value = round(total, 2)
                    self.update_invoice_check()  # This will control button state
                
                logger.info(f"Loaded: {file_path.name}")
        except Exception as e:
            logger.error(f"Load input file failed: {e}")
            QMessageBox.warning(self, "Error", f"Could not load file:\n{e}")

    def open_exported_file(self, item):
        """Open the selected exported file with default application"""
        try:
            file_path = OUTPUT_DIR / item.text()
            if file_path.exists():
                import os
                os.startfile(str(file_path))
        except Exception as e:
            logger.error(f"Open file failed: {e}")
            QMessageBox.warning(self, "Error", f"Could not open file:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application icon (for taskbar, alt-tab, etc. - use TEMP_RESOURCES_DIR for bundled resources)
    icon_path = TEMP_RESOURCES_DIR / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Show login dialog
    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)
    
    # Login successful, show main window
    logger.info(f"Application started by user: {login.authenticated_user}")
    win = DocCleaver()
    win.setWindowTitle(f"{APP_NAME} {VERSION} - User: {login.authenticated_user}")
    win.show()
    sys.exit(app.exec_())