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
    email TEXT,
    tax_code TEXT,
    address TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_no TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    tax_code TEXT,
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

CREATE TABLE IF NOT EXISTS product_update_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT,
    quantity INTEGER NOT NULL,
    sale_price INTEGER NOT NULL,
    description TEXT,
    note TEXT,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (product_code) REFERENCES products(product_code) ON DELETE CASCADE
);
"""


REQUIRED_TABLE_COLUMNS = {
    "products": {
        "product_code": "TEXT",
        "name": "TEXT NOT NULL",
        "unit": "TEXT",
        "quantity": "INTEGER NOT NULL DEFAULT 0",
        "sale_price": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TEXT NOT NULL",
        "description": "TEXT",
        "note": "TEXT",
    },
    "customers": {
        "id": "INTEGER",
        "full_name": "TEXT NOT NULL",
        "phone": "TEXT",
        "email": "TEXT",
        "tax_code": "TEXT",
        "address": "TEXT",
        "note": "TEXT",
    },
    "invoices": {
        "invoice_no": "TEXT",
        "created_at": "TEXT NOT NULL",
        "customer_name": "TEXT NOT NULL",
        "phone": "TEXT",
        "email": "TEXT",
        "tax_code": "TEXT",
        "address": "TEXT",
        "total_amount": "INTEGER NOT NULL",
    },
    "invoice_items": {
        "id": "INTEGER",
        "invoice_no": "TEXT NOT NULL",
        "product_code": "TEXT NOT NULL",
        "product_name": "TEXT NOT NULL",
        "quantity": "INTEGER NOT NULL",
        "unit_price": "INTEGER NOT NULL",
        "line_total": "INTEGER NOT NULL",
    },
    "payments": {
        "id": "INTEGER",
        "invoice_no": "TEXT",
        "customer_name": "TEXT NOT NULL",
        "purchase_date": "TEXT NOT NULL",
        "payment_date": "TEXT",
        "total_amount": "INTEGER NOT NULL",
        "paid_amount": "INTEGER NOT NULL",
        "remaining_amount": "INTEGER NOT NULL",
    },
    "product_update_history": {
        "id": "INTEGER",
        "product_code": "TEXT NOT NULL",
        "name": "TEXT NOT NULL",
        "unit": "TEXT",
        "quantity": "INTEGER NOT NULL",
        "sale_price": "INTEGER NOT NULL",
        "description": "TEXT",
        "note": "TEXT",
        "changed_at": "TEXT NOT NULL",
    },
}


def _table_columns(conn, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _ensure_missing_columns(conn) -> None:
    for table_name, required_columns in REQUIRED_TABLE_COLUMNS.items():
        existing_columns = set(_table_columns(conn, table_name))
        for column_name, column_definition in required_columns.items():
            if column_name in existing_columns:
                continue
            conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )


def init_schema() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        _ensure_missing_columns(conn)


def seed_sample_products() -> None:
    with get_connection() as conn:
        now = now_iso_utc7()
        sample_rows = [
        ]

        for row in sample_rows:
            exists = conn.execute(
                "SELECT product_code FROM products WHERE product_code = ?",
                (row[0],),
            ).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE products
                    SET name = ?, unit = ?, quantity = ?, sale_price = ?, updated_at = ?, description = ?, note = ?
                    WHERE product_code = ?
                    """,
                    (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[0]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO products (
                        product_code, name, unit, quantity, sale_price, updated_at, description, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
