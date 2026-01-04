# -*- mode: python ; coding: utf-8 -*-
# TariffMill macOS Build Specification
# Run with: pyinstaller TariffMill_macOS.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['tariffmill.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Resources', 'Resources'),
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'pdfplumber',
        'pdfplumber.utils',
        'pdfminer',
        'pdfminer.high_level',
        'pdfminer.layout',
        'pdfminer.pdfparser',
        'pdfminer.pdfdocument',
        'pdfminer.pdfpage',
        'pdfminer.pdfinterp',
        'pdfminer.converter',
        'pdfminer.cmapdb',
        'pdfminer.psparser',
        'PIL',
        'PIL.Image',
        'anthropic',
        'openai',
        'reportlab',
        'reportlab.lib',
        'reportlab.platypus',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'tk', 'tcl'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TariffMill',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Required for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TariffMill',
)

# Create macOS .app bundle
app = BUNDLE(
    coll,
    name='TariffMill.app',
    icon='Resources/tariffmill_icon.icns',
    bundle_identifier='com.processlogiclabs.tariffmill',
    info_plist={
        'CFBundleName': 'TariffMill',
        'CFBundleDisplayName': 'TariffMill',
        'CFBundleGetInfoString': 'Customs Entry Processing Application',
        'CFBundleIdentifier': 'com.processlogiclabs.tariffmill',
        'CFBundleVersion': '0.97.26',
        'CFBundleShortVersionString': '0.97.26',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'LSMinimumSystemVersion': '10.13.0',
    },
)