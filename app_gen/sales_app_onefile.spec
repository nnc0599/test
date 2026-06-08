import os
from pathlib import Path


PROJECT_ROOT = Path(os.environ["SALES_APP_PROJECT_ROOT"])
ENTRY_SCRIPT = PROJECT_ROOT / "run.py"
DATA_DIR = PROJECT_ROOT / "data"

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(DATA_DIR / "template.docx"), "data"),
        (str(DATA_DIR / "Screen.png"), "data"),
    ],
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
    name="sales_app",
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
    onefile=True,
)

