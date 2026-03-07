from app.database.connection import get_connection
from app.utils.time_utils import now_iso_utc7


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    sale_price INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    description TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_no TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    total_amount INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    line_total INTEGER NOT NULL,
    FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE,
    FOREIGN KEY (product_code) REFERENCES products(product_code)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT,
    customer_name TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    payment_date TEXT,
    total_amount INTEGER NOT NULL,
    paid_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE
);
"""


EXPECTED_TABLE_COLUMNS = {
    "products": [
        "product_code",
        "name",
        "unit",
        "quantity",
        "sale_price",
        "updated_at",
        "description",
        "note",
    ],
    "customers": ["id", "full_name", "phone", "address", "note"],
    "invoices": ["invoice_no", "created_at", "customer_name", "phone", "address", "total_amount"],
    "invoice_items": [
        "id",
        "invoice_no",
        "product_code",
        "product_name",
        "quantity",
        "unit_price",
        "line_total",
    ],
    "payments": [
        "id",
        "invoice_no",
        "customer_name",
        "purchase_date",
        "payment_date",
        "total_amount",
        "paid_amount",
        "remaining_amount",
    ],
}


def _table_columns(conn, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _schema_matches(conn) -> bool:
    for table_name, expected_columns in EXPECTED_TABLE_COLUMNS.items():
        if _table_columns(conn, table_name) != expected_columns:
            return False
    return True


def init_schema() -> None:
    with get_connection() as conn:
        has_products = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'products'"
        ).fetchone()
        if has_products and not _schema_matches(conn):
            conn.execute("DROP TABLE IF EXISTS payments")
            conn.execute("DROP TABLE IF EXISTS invoice_items")
            conn.execute("DROP TABLE IF EXISTS invoices")
            conn.execute("DROP TABLE IF EXISTS customers")
            conn.execute("DROP TABLE IF EXISTS products")
        conn.executescript(SCHEMA_SQL)


def seed_sample_products() -> None:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
        if count > 0:
            return
        now = now_iso_utc7()
        conn.executemany(
            """
            INSERT INTO products (
                product_code, name, unit, quantity, sale_price, updated_at, description, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "SP001",
                    "Pin Nang Luong 550W",
                    "tam",
                    200,
                    3500000,
                    now,
                    "Pin nang luong mat troi hieu suat cao, phu hop he thong dan dung.",
                    "Khoi tao mau",
                ),
                (
                    "SP002",
                    "Bien Tan Hybrid 5kW",
                    "bo",
                    45,
                    9800000,
                    now,
                    "Bien tan hybrid ho tro luu tru, giam hao phi dien nang.",
                    "Khoi tao mau",
                ),
            ],
        )
