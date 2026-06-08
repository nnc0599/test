from __future__ import annotations

import os
import shutil
from pathlib import Path

import PyInstaller.__main__

APP_GEN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_GEN_DIR.parent
DIST_DIR = APP_GEN_DIR
BUILD_DIR = APP_GEN_DIR / "build"
SPEC_PATH = APP_GEN_DIR / "sales_app_onefile.spec"
EXECUTABLE_NAME = "sales_app"

def clean_previous_build() -> None:
    for path in [BUILD_DIR, DIST_DIR / EXECUTABLE_NAME, DIST_DIR / f"{EXECUTABLE_NAME}.exe"]:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

def main() -> int:
    clean_previous_build()
    os.environ["SALES_APP_PROJECT_ROOT"] = str(PROJECT_ROOT)

    PyInstaller.__main__.run(
        [
            str(SPEC_PATH),
            "--noconfirm",
            "--clean",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
