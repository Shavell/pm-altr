# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pygments.lexers.data',
        'pygments.formatters.html',
        'pygments.styles.monokai',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pm-altr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # No terminal window
    target_arch=None,
)

app = BUNDLE(
    exe,
    name='PM-ALTR.app',
    bundle_identifier='com.pm-altr.app',
)
