# -*- mode: python ; coding: utf-8 -*-


"""
PyInstaller spec for PyDoc v1.0.0 Stable.

Build:
    pip install pyinstaller pywebview pystray pillow keyboard
    pyinstaller PyDoc.spec            # -> dist/PyDoc.exe  (single file, no console)

This bundles the web UI (web/), the offline Material Symbols font and icon
list, and the default themes.json into a self-contained executable. Runtime
data (config.json, shortcuts.json, store.json, Shortcuts/, Icons/, Profiles/,
Screenshots/) is created next to the .exe on first run.

Drop an icon at  Icons/app.ico  before building to brand the executable.
"""

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
HERE = os.path.abspath(os.getcwd())

# --- bundle the front-end + offline assets + default theme file -------------
datas = [
    ("web", "web"),
    ("themes.json", "."),
]

# include a starter Shortcuts folder + README if present
if os.path.isdir(os.path.join(HERE, "Shortcuts")):
    datas.append(("Shortcuts", "Shortcuts"))

# --- make sure optional native deps are fully collected ---------------------
hiddenimports = ["webview", "pystray", "PIL", "keyboard"]
binaries = []
for pkg in ("webview", "pystray", "PIL"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# optional .exe icon
_icon = os.path.join(HERE, "Icons", "app.ico")
icon = _icon if os.path.exists(_icon) else None


a = Analysis(
    ["launcher.py"],
    pathex=[HERE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PyDoc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version="version_info.txt" if os.path.exists(os.path.join(HERE, "version_info.txt")) else None,
)
