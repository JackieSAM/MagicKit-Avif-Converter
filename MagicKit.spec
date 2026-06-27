# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MagicKit Image Converter.
# Build with:  pyinstaller MagicKit.spec
#
# This spec exists (instead of a bare `pyinstaller converter.py`) because two
# things break a naive build of this app:
#   1. customtkinter ships its own theme/font assets as data files that
#      PyInstaller won't pick up automatically -> blank/broken UI at runtime.
#   2. pillow-avif-plugin registers itself with Pillow via a plugin import;
#      PyInstaller's import scanner can miss it -> AVIF silently "works" in
#      dev but fails in the packaged .exe.
# Both are handled explicitly below so the build doesn't quietly regress.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
hiddenimports = []

try:
    datas += collect_data_files("customtkinter")
except Exception:
    pass

hiddenimports += collect_submodules("pillow_avif")
hiddenimports += ["PIL._tkinter_finder"]

block_cipher = None

a = Analysis(
    ["converter.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="MagicKit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX compression occasionally trips AV false-positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # put an .ico path here if you add an app icon
)
