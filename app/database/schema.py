import sqlite3

from app.database.connection import get_connection
from app.utils.time_utils import now_iso_utc7


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    sale_price INTEGER NOT NULL DEFAULT 0,
    retail_price INTEGER NOT NULL DEFAULT 0,
    worker_price INTEGER NOT NULL DEFAULT 0,
    dealer_price INTEGER NOT NULL DEFAULT 0,
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
    customer_price_group TEXT NOT NULL DEFAULT 'auto',
    note TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_no TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    seller_name TEXT NOT NULL DEFAULT 'Cửa hàng',
    phone TEXT,
    email TEXT,
    tax_code TEXT,
    address TEXT,
    electronic_invoice_path TEXT,
    warehouse_invoice_path TEXT,
    total_amount INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    seller_name TEXT NOT NULL DEFAULT 'Cửa hàng',
    note TEXT,
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
    retail_price INTEGER NOT NULL DEFAULT 0,
    worker_price INTEGER NOT NULL DEFAULT 0,
    dealer_price INTEGER NOT NULL DEFAULT 0,
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


PRODUCTS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts
USING fts5(
    product_code,
    name,
    description,
    content='products',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""


PRODUCTS_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS products_fts_ai AFTER INSERT ON products BEGIN
    INSERT INTO products_fts(rowid, product_code, name, description)
    VALUES (new.rowid, new.product_code, new.name, COALESCE(new.description, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_ad AFTER DELETE ON products BEGIN
    INSERT INTO products_fts(products_fts, rowid, product_code, name, description)
    VALUES ('delete', old.rowid, old.product_code, old.name, COALESCE(old.description, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_au AFTER UPDATE ON products BEGIN
    INSERT INTO products_fts(products_fts, rowid, product_code, name, description)
    VALUES ('delete', old.rowid, old.product_code, old.name, COALESCE(old.description, ''));
    INSERT INTO products_fts(rowid, product_code, name, description)
    VALUES (new.rowid, new.product_code, new.name, COALESCE(new.description, ''));
END;
"""


REQUIRED_TABLE_COLUMNS = {
    "products": {
        "product_code": "TEXT",
        "name": "TEXT NOT NULL",
        "category": "TEXT",
        "unit": "TEXT",
        "quantity": "INTEGER NOT NULL DEFAULT 0",
        "sale_price": "INTEGER NOT NULL DEFAULT 0",
        "retail_price": "INTEGER NOT NULL DEFAULT 0",
        "worker_price": "INTEGER NOT NULL DEFAULT 0",
        "dealer_price": "INTEGER NOT NULL DEFAULT 0",
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
        "customer_price_group": "TEXT NOT NULL DEFAULT 'auto'",
        "note": "TEXT",
    },
    "invoices": {
        "invoice_no": "TEXT",
        "created_at": "TEXT NOT NULL",
        "customer_name": "TEXT NOT NULL",
        "seller_name": "TEXT NOT NULL DEFAULT 'Cửa hàng'",
        "phone": "TEXT",
        "email": "TEXT",
        "tax_code": "TEXT",
        "address": "TEXT",
        "electronic_invoice_path": "TEXT",
        "warehouse_invoice_path": "TEXT",
        "total_amount": "INTEGER NOT NULL",
    },
    "quotations": {
        "id": "INTEGER",
        "created_at": "TEXT NOT NULL",
        "customer_name": "TEXT NOT NULL",
        "seller_name": "TEXT NOT NULL DEFAULT 'Cửa hàng'",
        "note": "TEXT",
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
        "retail_price": "INTEGER NOT NULL DEFAULT 0",
        "worker_price": "INTEGER NOT NULL DEFAULT 0",
        "dealer_price": "INTEGER NOT NULL DEFAULT 0",
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


def _backfill_product_price_columns(conn) -> None:
    product_columns = set(_table_columns(conn, "products"))
    history_columns = set(_table_columns(conn, "product_update_history"))
    product_custom_expr = "COALESCE(custom_price, 0)" if "custom_price" in product_columns else "0"
    history_custom_expr = "COALESCE(custom_price, 0)" if "custom_price" in history_columns else "0"

    conn.execute(
        f"""
        UPDATE products
        SET
            retail_price = CASE
                WHEN COALESCE(retail_price, 0) = 0 AND COALESCE(sale_price, 0) > 0 THEN sale_price
                WHEN COALESCE(retail_price, 0) = 0 AND {product_custom_expr} > 0 THEN {product_custom_expr}
                ELSE COALESCE(retail_price, 0)
            END,
            worker_price = COALESCE(worker_price, 0),
            dealer_price = COALESCE(dealer_price, 0)
        """
    )
    conn.execute(
        f"""
        UPDATE products
        SET sale_price = CASE
            WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
            WHEN COALESCE(worker_price, 0) > 0 THEN worker_price
            WHEN COALESCE(dealer_price, 0) > 0 THEN dealer_price
            WHEN {product_custom_expr} > 0 THEN {product_custom_expr}
            ELSE COALESCE(sale_price, 0)
        END
        """
    )

    conn.execute(
        f"""
        UPDATE product_update_history
        SET
            retail_price = CASE
                WHEN COALESCE(retail_price, 0) = 0 AND COALESCE(sale_price, 0) > 0 THEN sale_price
                WHEN COALESCE(retail_price, 0) = 0 AND {history_custom_expr} > 0 THEN {history_custom_expr}
                ELSE COALESCE(retail_price, 0)
            END,
            worker_price = COALESCE(worker_price, 0),
            dealer_price = COALESCE(dealer_price, 0)
        """
    )
    conn.execute(
        f"""
        UPDATE product_update_history
        SET sale_price = CASE
            WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
            WHEN COALESCE(worker_price, 0) > 0 THEN worker_price
            WHEN COALESCE(dealer_price, 0) > 0 THEN dealer_price
            WHEN {history_custom_expr} > 0 THEN {history_custom_expr}
            ELSE COALESCE(sale_price, 0)
        END
        """
    )


def _normalize_customer_price_groups(conn) -> None:
    if "customer_price_group" not in set(_table_columns(conn, "customers")):
        return
    conn.execute(
        """
        UPDATE customers
        SET customer_price_group = 'retail_price'
        WHERE customer_price_group = 'custom_price'
        """
    )


def _drop_products_fts(conn) -> None:
    conn.executescript(
        """
        DROP TRIGGER IF EXISTS products_fts_ai;
        DROP TRIGGER IF EXISTS products_fts_ad;
        DROP TRIGGER IF EXISTS products_fts_au;
        DROP TABLE IF EXISTS products_fts;
        """
    )


def _rebuild_products_without_custom_price(conn) -> None:
    if "custom_price" not in set(_table_columns(conn, "products")):
        return

    _drop_products_fts(conn)
    conn.execute("ALTER TABLE products RENAME TO products_old")
    conn.execute(
        """
        CREATE TABLE products (
            product_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            sale_price INTEGER NOT NULL DEFAULT 0,
            retail_price INTEGER NOT NULL DEFAULT 0,
            worker_price INTEGER NOT NULL DEFAULT 0,
            dealer_price INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            description TEXT,
            note TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO products (
            product_code, name, category, unit, quantity, sale_price, retail_price, worker_price, dealer_price, updated_at, description, note
        )
        SELECT
            product_code,
            name,
            category,
            unit,
            quantity,
            CASE
                WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
                WHEN COALESCE(worker_price, 0) > 0 THEN worker_price
                WHEN COALESCE(dealer_price, 0) > 0 THEN dealer_price
                WHEN COALESCE(custom_price, 0) > 0 THEN custom_price
                ELSE COALESCE(sale_price, 0)
            END,
            CASE
                WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
                WHEN COALESCE(custom_price, 0) > 0 THEN custom_price
                ELSE COALESCE(sale_price, 0)
            END,
            COALESCE(worker_price, 0),
            COALESCE(dealer_price, 0),
            updated_at,
            description,
            note
        FROM products_old
        """
    )
    conn.execute("DROP TABLE products_old")


def _rebuild_product_update_history_without_custom_price(conn) -> None:
    if "custom_price" not in set(_table_columns(conn, "product_update_history")):
        return

    conn.execute("ALTER TABLE product_update_history RENAME TO product_update_history_old")
    conn.execute(
        """
        CREATE TABLE product_update_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            name TEXT NOT NULL,
            unit TEXT,
            quantity INTEGER NOT NULL,
            sale_price INTEGER NOT NULL,
            retail_price INTEGER NOT NULL DEFAULT 0,
            worker_price INTEGER NOT NULL DEFAULT 0,
            dealer_price INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            note TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (product_code) REFERENCES products(product_code) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO product_update_history (
            id, product_code, name, unit, quantity, sale_price, retail_price, worker_price, dealer_price, description, note, changed_at
        )
        SELECT
            id,
            product_code,
            name,
            unit,
            quantity,
            CASE
                WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
                WHEN COALESCE(worker_price, 0) > 0 THEN worker_price
                WHEN COALESCE(dealer_price, 0) > 0 THEN dealer_price
                WHEN COALESCE(custom_price, 0) > 0 THEN custom_price
                ELSE COALESCE(sale_price, 0)
            END,
            CASE
                WHEN COALESCE(retail_price, 0) > 0 THEN retail_price
                WHEN COALESCE(custom_price, 0) > 0 THEN custom_price
                ELSE COALESCE(sale_price, 0)
            END,
            COALESCE(worker_price, 0),
            COALESCE(dealer_price, 0),
            description,
            note,
            changed_at
        FROM product_update_history_old
        """
    )
    conn.execute("DROP TABLE product_update_history_old")


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


def _ensure_products_fts(conn) -> None:
    try:
        conn.execute(PRODUCTS_FTS_SQL)
        conn.executescript(PRODUCTS_FTS_TRIGGERS_SQL)

        product_count = int(conn.execute("SELECT COUNT(*) FROM products").fetchone()[0])
        indexed_count = int(conn.execute("SELECT COUNT(*) FROM products_fts_docsize").fetchone()[0])
        if product_count != indexed_count:
            conn.execute("INSERT INTO products_fts(products_fts) VALUES ('rebuild')")
    except sqlite3.OperationalError:
        # Fallback an toàn nếu SQLite hiện tại không có FTS5.
        pass


def init_schema() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        _ensure_missing_columns(conn)
        _backfill_product_price_columns(conn)
        _migrate_invoice_items_without_product_fk(conn)
        _normalize_customer_price_groups(conn)
        _rebuild_products_without_custom_price(conn)
        _rebuild_product_update_history_without_custom_price(conn)
        conn.executescript(INDEX_SQL)
        _ensure_products_fts(conn)


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
                    SET name = ?, category = ?, unit = ?, quantity = ?, sale_price = ?, retail_price = ?, worker_price = ?, dealer_price = ?, updated_at = ?, description = ?, note = ?
                    WHERE product_code = ?
                    """,
                    (row[1], row[2], row[3], row[4], row[5], row[5], 0, 0, row[6], row[7], row[8], row[0]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO products (
                        product_code, name, category, unit, quantity, sale_price, retail_price, worker_price, dealer_price, updated_at, description, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row[0], row[1], row[2], row[3], row[4], row[5], row[5], 0, 0, row[6], row[7], row[8]),
                )
