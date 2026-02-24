# -*- mode: python ; coding: utf-8 -*-
# Windows build spec — run: pyinstaller pm-altr-win.spec --clean --noconfirm

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
    console=False,            # No terminal window (windowed mode)
    icon=None,                # Set to 'icon.ico' if you have one
    target_arch=None,
)
