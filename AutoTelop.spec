# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building the Auto Telop desktop app.

Build:
    pip install pyinstaller
    pyinstaller AutoTelop.spec

Produces:
    macOS : dist/AutoTelop.app
    Windows: dist/AutoTelop/AutoTelop.exe  (BUNDLE below is macOS-only)

Notes:
- Whisper model weights are NOT bundled; they download on first run into
  the user's cache (~/.cache/whisper). This keeps the app size reasonable.
- ffmpeg/ffprobe must be available on the user's machine (brew install ffmpeg
  on macOS). They are not bundled here.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ("templates", "templates"),
    ("VERSION", "."),
    ("config.default.yaml", "."),
    ("guide.html", "."),
]
# Whisper ships assets (mel filters, tokenizer, etc.) that must be included.
datas += collect_data_files("whisper")

hiddenimports = []
hiddenimports += collect_submodules("whisper")

block_cipher = None

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoTelop",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="AutoTelop",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AutoTelop.app",
        icon=None,
        bundle_identifier="com.kazuu234.autotelop",
        info_plist={
            "CFBundleShortVersionString": open("VERSION").read().strip(),
            "NSHighResolutionCapable": True,
        },
    )
