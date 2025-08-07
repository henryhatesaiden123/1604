# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\gemini02\\1604\\vMixTimecodeApp\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\gemini02\\1604\\vMixTimecodeApp\\settings.json', '.'), ('D:\\gemini02\\1604\\vMixTimecodeApp\\logs', 'logs'), ('D:\\gemini02\\1604\\vMixTimecodeApp\\src', 'src')],
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
    name='vMixTimecodeApp',
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
)
