# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


spec_path = Path(globals().get("SPEC") or "pyinstaller/traceloom.spec").resolve()
project_root = spec_path.parents[1]

datas = [
    (str(project_root / "traceloom" / "bundled"), "traceloom/bundled"),
    (str(project_root / "traceloom" / "resources"), "traceloom/resources"),
]

a = Analysis(
    [str(project_root / "traceloom" / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pkg_resources._vendor.appdirs",
        "pkg_resources._vendor.packaging",
        "pkg_resources._vendor.pyparsing",
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
    [],
    exclude_binaries=True,
    name="traceloom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="traceloom",
)
