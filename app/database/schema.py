from app.database.connection import get_connection
from app.utils.time_utils import now_iso_utc7


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    warranty TEXT,
    unit TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    sale_price INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    description TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_code TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    tax_code TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_no TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    customer_code TEXT,
    customer_name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    total_amount INTEGER NOT NULL,
    ship_fee INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_code) REFERENCES customers(customer_code)
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
    customer_name TEXT NOT NULL,
    customer_code TEXT,
    purchase_date TEXT NOT NULL,
    payment_date TEXT,
    total_amount INTEGER NOT NULL,
    paid_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    FOREIGN KEY (customer_code) REFERENCES customers(customer_code)
);
"""


def init_schema() -> None:
    with get_connection() as conn:
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
                product_code, name, warranty, unit, quantity, sale_price, updated_at, description, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "SP001",
                    "Pin Nang Luong 550W",
                    "12 thang",
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
                    "24 thang",
                    "bo",
                    45,
                    9800000,
                    now,
                    "Bien tan hybrid ho tro luu tru, giam hao phi dien nang.",
                    "Khoi tao mau",
                ),
            ],
        )
