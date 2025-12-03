# -*- mode: python ; coding: utf-8 -*-
# ==============================================================================
# PyInstaller Configuration for Derivative Mill Windows Executable
# ==============================================================================
# This spec file configures PyInstaller to create a standalone Windows
# executable from the Python source code. It includes all dependencies,
# resources, and configuration needed for distribution.
#
# Execution: pyinstaller build_windows.spec
# Output: dist/DerivativeMill.exe (one-file bundle)
# ==============================================================================

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Determine project root directory dynamically
# This works whether spec file is in scripts/ or moved elsewhere
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Analysis phase: collect Python code and dependencies
a = Analysis(
    # Entry point: main application module
    [os.path.join(project_root, 'DerivativeMill', 'derivativemill.py').replace('\\', '/')],
    pathex=[project_root],
    binaries=[],
    # Bundle non-code data files
    datas=[
        (os.path.join(project_root, 'DerivativeMill', 'Resources'), 'DerivativeMill/Resources'),
        (os.path.join(project_root, 'README.md'), '.'),
    ],
    # Explicitly include PyQt5 modules and data dependencies
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'pandas',
        'openpyxl',
        'pdfplumber',
        'PIL',
    ] + collect_submodules('PyQt5'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create ZIP archive with pure Python code
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Build executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DerivativeMill',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'DerivativeMill', 'Resources', 'derivativemill.ico').replace('\\', '/') if sys.platform == 'win32' else None,
)

# Alternative: one-directory bundle for development/debugging
# Uncomment below to use instead of one-file EXE above
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='DerivativeMill'
# )
