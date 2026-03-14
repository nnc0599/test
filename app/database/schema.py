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

CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    tax_code TEXT,
    address TEXT,
    goods_amount INTEGER NOT NULL DEFAULT 0,
    ship_fee INTEGER NOT NULL DEFAULT 0,
    total_amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    export_path TEXT,
    exported_invoice_no TEXT
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    unit TEXT,
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    line_total INTEGER NOT NULL,
    FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quotation_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    unit TEXT,
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    line_total INTEGER NOT NULL,
    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
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


INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_invoices_created_at_invoice_no
ON invoices(created_at DESC, invoice_no DESC);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_no
ON invoice_items(invoice_no);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_no_price
ON invoice_items(invoice_no, unit_price DESC, line_total DESC, product_name COLLATE NOCASE, id);

CREATE INDEX IF NOT EXISTS idx_invoice_items_product_code_invoice_no
ON invoice_items(product_code, invoice_no);

CREATE INDEX IF NOT EXISTS idx_quotation_items_quotation_id_price
ON quotation_items(quotation_id, unit_price DESC, line_total DESC, product_name COLLATE NOCASE, id);

CREATE INDEX IF NOT EXISTS idx_products_in_stock_name
ON products(name COLLATE NOCASE, product_code)
WHERE quantity > 0;

CREATE INDEX IF NOT EXISTS idx_products_updated_at
ON products(updated_at DESC, product_code);

CREATE INDEX IF NOT EXISTS idx_products_name_code
ON products(name COLLATE NOCASE, product_code);

CREATE INDEX IF NOT EXISTS idx_product_update_history_product_changed_at
ON product_update_history(product_code, changed_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_quotations_pending_recent
ON quotations(created_at DESC, id DESC)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_quotations_status_created_at
ON quotations(status, created_at DESC, id DESC);
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
    "quotations": {
        "id": "INTEGER",
        "created_at": "TEXT NOT NULL",
        "customer_name": "TEXT NOT NULL",
        "phone": "TEXT",
        "email": "TEXT",
        "tax_code": "TEXT",
        "address": "TEXT",
        "goods_amount": "INTEGER NOT NULL DEFAULT 0",
        "ship_fee": "INTEGER NOT NULL DEFAULT 0",
        "total_amount": "INTEGER NOT NULL DEFAULT 0",
        "status": "TEXT NOT NULL DEFAULT 'pending'",
        "export_path": "TEXT",
        "exported_invoice_no": "TEXT",
    },
    "invoice_items": {
        "id": "INTEGER",
        "invoice_no": "TEXT NOT NULL",
        "product_code": "TEXT NOT NULL",
        "product_name": "TEXT NOT NULL",
        "unit": "TEXT",
        "quantity": "INTEGER NOT NULL",
        "unit_price": "INTEGER NOT NULL",
        "line_total": "INTEGER NOT NULL",
    },
    "quotation_items": {
        "id": "INTEGER",
        "quotation_id": "INTEGER NOT NULL",
        "product_code": "TEXT NOT NULL",
        "product_name": "TEXT NOT NULL",
        "unit": "TEXT",
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


def _invoice_items_has_product_fk(conn) -> bool:
    rows = conn.execute("PRAGMA foreign_key_list(invoice_items)").fetchall()
    return any(row[2] == "products" for row in rows)


def _migrate_invoice_items_without_product_fk(conn) -> None:
    if not _invoice_items_has_product_fk(conn):
        return

    conn.execute("ALTER TABLE invoice_items RENAME TO invoice_items_old")
    conn.execute(
        """
        CREATE TABLE invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT NOT NULL,
            unit TEXT,
            quantity INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            line_total INTEGER NOT NULL,
            FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO invoice_items (
            id, invoice_no, product_code, product_name, unit, quantity, unit_price, line_total
        )
        SELECT
            id, invoice_no, product_code, product_name, unit, quantity, unit_price, line_total
        FROM invoice_items_old
        """
    )
    conn.execute("DROP TABLE invoice_items_old")


def init_schema() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        _ensure_missing_columns(conn)
        _migrate_invoice_items_without_product_fk(conn)
        conn.executescript(INDEX_SQL)


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
