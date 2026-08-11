# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
version_file = root / "build" / "windows-version-info.txt"
if not version_file.is_file():
    raise SystemExit("Run scripts/release.py --write-version-info build/windows-version-info.txt first")

a = Analysis(
    [str(root / "packaging" / "entrypoint.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets" / "mdpeek.ico"), "assets")],
    # PyInstaller's maintained Pygments hook discovers the lexer modules.
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "PIL"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MDPeek",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "assets" / "mdpeek.ico"),
    version=str(version_file),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MDPeek",
)
