from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


bundle_dir = Path(SPECPATH)

datas = [
    (str(bundle_dir / "template.docx"), "."),
    (str(bundle_dir / "Screen.png"), "."),
]
datas += collect_data_files("docx")
datas += collect_data_files("openpyxl")

hiddenimports = collect_submodules("docx") + collect_submodules("openpyxl")


a = Analysis(
    [str(bundle_dir / "run.py")],
    pathex=[str(bundle_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="app_b",
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