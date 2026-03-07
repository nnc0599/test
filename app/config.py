from pathlib import Path

APP_NAME = "Sales Desktop App"
DEFAULT_ADMIN_PASSWORD = "12345678"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "sales_app.db"

MIN_FONT_PX = 15
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 720
