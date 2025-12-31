# -*- mode: python ; coding: utf-8 -*-
import os

# Python 3.12 installation directory
PYTHON_DIR = r'C:\Users\payne\AppData\Local\Programs\Python\Python312'

a = Analysis(
    ['tariffmill.py'],
    pathex=[],
    binaries=[
        # Bundle VC++ runtime DLLs required by Python
        (os.path.join(PYTHON_DIR, 'vcruntime140.dll'), '.'),
        (os.path.join(PYTHON_DIR, 'vcruntime140_1.dll'), '.'),
    ],
    datas=[('Resources', 'Resources')],
    hiddenimports=['pdfplumber', 'pdfplumber.utils', 'pdfminer', 'pdfminer.high_level', 'pdfminer.layout', 'pdfminer.pdfparser', 'pdfminer.pdfdocument', 'pdfminer.pdfpage', 'pdfminer.pdfinterp', 'pdfminer.converter', 'pdfminer.cmapdb', 'pdfminer.psparser', 'PIL', 'PIL.Image', 'anthropic', 'openai'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Native splash screen - shows IMMEDIATELY when exe is launched (before Python loads)
splash = Splash(
    'Resources\\splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(350, 280),
    text_size=14,
    text_color='#cccccc',
    text_default='Initializing...',
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
    a.datas,
    [],
    name='TariffMill',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Resources\\icon.ico'],
)
