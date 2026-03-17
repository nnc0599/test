import sys
from pathlib import Path

APP_NAME = "Phần Mềm Bán Hàng"
DEFAULT_ADMIN_PASSWORD = "12345678"

def _resolve_project_root() -> Path:
	if getattr(sys, "frozen", False):
		return Path(sys.executable).resolve().parent
	return Path(__file__).resolve().parent.parent


def _resolve_bundle_root() -> Path:
	bundle_dir = getattr(sys, "_MEIPASS", None)
	if bundle_dir:
		return Path(bundle_dir)
	return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _resolve_project_root()
BUNDLE_ROOT = _resolve_bundle_root()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "sales_app.db"

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
