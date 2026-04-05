import os
import sys
from pathlib import Path

APP_NAME = "Phần Mềm Bán Hàng"
DEFAULT_ADMIN_PASSWORD = "12345678"

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_bundle_root() -> Path:
	if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
		return Path(sys._MEIPASS)
	return PROJECT_ROOT


def _resolve_runtime_root() -> Path:
	override = os.environ.get("SALES_APP_HOME", "").strip()
	if override:
		return Path(override).expanduser().resolve()
	if getattr(sys, "frozen", False):
		return Path(sys.executable).resolve().parent
	return PROJECT_ROOT


BUNDLE_ROOT = _resolve_bundle_root()
RUNTIME_ROOT = _resolve_runtime_root()
RESOURCE_DATA_DIR = BUNDLE_ROOT / "data"
DATA_DIR = RUNTIME_ROOT / "data"
DB_PATH = DATA_DIR / "sales_app.db"
TEMPLATE_PATH = RESOURCE_DATA_DIR / "template.docx"
SCREEN_IMAGE_PATH = RESOURCE_DATA_DIR / "Screen.png"
EXPORT_DIR = DATA_DIR / "exported_invoices"

MIN_FONT_PX = 15
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 840

PRODUCT_CATEGORIES = (
	"Pin NLMT",
	"Pin lưu trữ 48V",
	"Pin lưu trữ 24V",
	"Biến tần bơm",
	"Biến tần",
	"Biến tần Hybrid",
	"Phụ kiện",
)

PRODUCT_CATEGORY_DISPLAY_PRIORITY = (
	"Pin NLMT",
	"Biến tần Hybrid",
	"Biến tần",
	"Biến tần bơm",
	"Pin lưu trữ 48V",
	"Pin lưu trữ 24V",
	"Phụ kiện",
)
