# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['DerivativeMill\\derivativemill.py'],
    pathex=[],
    binaries=[],
    datas=[('DerivativeMill/Resources', 'Resources'), ('DerivativeMill/Input', 'Input'), ('DerivativeMill/Output', 'Output'), ('DerivativeMill/Section_232_Actions.csv', '.'), ('DerivativeMill/Section_232_Tariffs_Compiled.csv', '.'), ('DerivativeMill/shipment_mapping.json', '.'), ('DerivativeMill/column_mapping.json', '.'), ('DerivativeMill/README.md', '.'), ('DerivativeMill/Resources/References', 'Resources/References')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DerivativeMill',
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
    icon=['DerivativeMill\\Resources\\icon.ico'],
)
