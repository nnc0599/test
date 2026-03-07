from __future__ import annotations

from typing import Iterable

from app.database.connection import get_connection
from app.utils.time_utils import now_iso_utc7, today_utc7


class ProductRepository:
    def list_products(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_code, name, unit, quantity, sale_price, updated_at, description, note
                FROM products
                ORDER BY updated_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_product(self, product_code: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT product_code, name, unit, quantity, sale_price, updated_at, description, note
                FROM products
                WHERE product_code = ?
                """,
                (product_code,),
            ).fetchone()
            return dict(row) if row else None

    def add_product(self, payload: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO products (
                    product_code, name, unit, quantity, sale_price, updated_at, description, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["product_code"],
                    payload["name"],
                    payload.get("unit", ""),
                    int(payload.get("quantity", 0)),
                    int(payload.get("sale_price", 0)),
                    now_iso_utc7(),
                    payload.get("description", ""),
                    payload.get("note", ""),
                ),
            )

    def update_product(self, product_code: str, payload: dict) -> None:
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT product_code, name, unit, quantity, sale_price, updated_at, description, note
                FROM products
                WHERE product_code = ?
                """,
                (product_code,),
            ).fetchone()
            if not existing:
                raise ValueError("Sản phẩm không tồn tại")

            updated_at = now_iso_utc7()
            new_quantity = int(payload.get("quantity", 0))
            new_sale_price = int(payload.get("sale_price", 0))
            conn.execute(
                """
                UPDATE products
                SET
                    name = ?,
                    unit = ?,
                    quantity = ?,
                    sale_price = ?,
                    updated_at = ?,
                    description = ?,
                    note = ?
                WHERE product_code = ?
                """,
                (
                    payload["name"],
                    payload.get("unit", ""),
                    new_quantity,
                    new_sale_price,
                    updated_at,
                    payload.get("description", ""),
                    payload["note"],
                    product_code,
                ),
            )

            quantity_changed = int(existing["quantity"]) != new_quantity
            price_changed = int(existing["sale_price"]) != new_sale_price
            if quantity_changed or price_changed:
                conn.execute(
                    """
                    INSERT INTO product_update_history (
                        product_code, name, unit, quantity, sale_price, description, note, changed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_code,
                        payload["name"],
                        payload.get("unit", ""),
                        new_quantity,
                        new_sale_price,
                        payload.get("description", ""),
                        payload["note"],
                        updated_at,
                    ),
                )

    def list_product_update_history(self, product_code: str) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    product_code,
                    name,
                    unit,
                    quantity,
                    sale_price,
                    description,
                    note,
                    changed_at
                FROM product_update_history
                WHERE product_code = ?
                ORDER BY changed_at DESC, id DESC
                """,
                (product_code,),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_product(self, product_code: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM products WHERE product_code = ?", (product_code,))

    def search_products(self, keyword: str) -> list[dict]:
        like_kw = f"%{keyword.strip()}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_code, name, unit, quantity, sale_price, updated_at, description, note
                FROM products
                WHERE product_code LIKE ? OR name LIKE ? OR description LIKE ?
                ORDER BY name ASC
                LIMIT 20
                """,
                (like_kw, like_kw, like_kw),
            ).fetchall()
            return [dict(row) for row in rows]

    def decrease_stocks(self, lines: Iterable[dict]) -> None:
        with get_connection() as conn:
            for line in lines:
                cursor = conn.execute(
                    """
                    UPDATE products
                    SET quantity = quantity - ?
                    WHERE product_code = ? AND quantity >= ?
                    """,
                    (line["quantity"], line["product_code"], line["quantity"]),
                )
                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Sản phẩm {line['product_code']} không đủ số lượng để xuất kho."
                    )


class CustomerRepository:
    def upsert_customer(self, payload: dict) -> None:
        with get_connection() as conn:
            phone = payload.get("phone", "").strip()
            exists = None
            if phone:
                exists = conn.execute(
                    "SELECT id FROM customers WHERE phone = ?",
                    (phone,),
                ).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE customers
                    SET full_name = ?, phone = ?, email = ?, tax_code = ?, address = ?, note = ?
                    WHERE id = ?
                    """,
                    (
                        payload["full_name"],
                        payload.get("phone", ""),
                        payload.get("email", ""),
                        payload.get("tax_code", ""),
                        payload.get("address", ""),
                        payload.get("note", ""),
                        exists["id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO customers (full_name, phone, email, tax_code, address, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["full_name"],
                        payload.get("phone", ""),
                        payload.get("email", ""),
                        payload.get("tax_code", ""),
                        payload.get("address", ""),
                        payload.get("note", ""),
                    ),
                )

    def list_customers(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT full_name, phone, email, tax_code, address, note
                FROM customers
                ORDER BY id DESC
                LIMIT 200
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def search_customers(self, keyword: str) -> list[dict]:
        like_kw = f"%{keyword.strip()}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT full_name, phone, email, tax_code, address, note
                FROM customers
                WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ? OR tax_code LIKE ? OR address LIKE ?
                ORDER BY id DESC
                LIMIT 20
                """,
                (like_kw, like_kw, like_kw, like_kw, like_kw),
            ).fetchall()
            return [dict(row) for row in rows]


class InvoiceRepository:
    def create_invoice(self, payload: dict, lines: list[dict]) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO invoices (
                    invoice_no, created_at, customer_name, phone, email, tax_code, address, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["invoice_no"],
                    payload["created_at"],
                    payload["customer_name"],
                    payload.get("phone", ""),
                    payload.get("email", ""),
                    payload.get("tax_code", ""),
                    payload.get("address", ""),
                    int(payload["total_amount"]),
                ),
            )

            conn.executemany(
                """
                INSERT INTO invoice_items (
                    invoice_no, product_code, product_name, unit, quantity, unit_price, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        payload["invoice_no"],
                        line["product_code"],
                        line["product_name"],
                        line.get("unit", ""),
                        int(line["quantity"]),
                        int(line["unit_price"]),
                        int(line["line_total"]),
                    )
                    for line in lines
                ],
            )

            for line in lines:
                cursor = conn.execute(
                    """
                    UPDATE products
                    SET quantity = quantity - ?
                    WHERE product_code = ? AND quantity >= ?
                    """,
                    (line["quantity"], line["product_code"], line["quantity"]),
                )
                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Sản phẩm {line['product_code']} không đủ số lượng để xuất kho."
                    )

            paid_amount = int(payload.get("paid_amount", 0))
            total = int(payload["total_amount"])
            conn.execute(
                """
                INSERT INTO payments (
                    invoice_no, customer_name, purchase_date, payment_date, total_amount, paid_amount, remaining_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["invoice_no"],
                    payload["customer_name"],
                    payload["created_at"],
                    payload.get("payment_date", payload["created_at"]),
                    total,
                    paid_amount,
                    total - paid_amount,
                ),
            )

    def list_invoices(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    invoices.invoice_no,
                    invoices.created_at,
                    invoices.customer_name,
                    invoices.phone,
                    invoices.email,
                    invoices.tax_code,
                    invoices.address,
                    invoices.total_amount,
                    COUNT(invoice_items.id) AS item_count
                FROM invoices
                LEFT JOIN invoice_items ON invoice_items.invoice_no = invoices.invoice_no
                GROUP BY
                    invoices.invoice_no,
                    invoices.created_at,
                    invoices.customer_name,
                    invoices.phone,
                    invoices.email,
                    invoices.tax_code,
                    invoices.address,
                    invoices.total_amount
                ORDER BY invoices.created_at DESC
                LIMIT 200
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_invoice_detail(self, invoice_no: str) -> dict | None:
        with get_connection() as conn:
            invoice = conn.execute(
                """
                SELECT invoice_no, created_at, customer_name, phone, email, tax_code, address, total_amount
                FROM invoices
                WHERE invoice_no = ?
                """,
                (invoice_no,),
            ).fetchone()
            if not invoice:
                return None

            items = conn.execute(
                """
                SELECT
                    invoice_items.product_code,
                    invoice_items.product_name,
                    COALESCE(invoice_items.unit, products.unit, '') AS unit,
                    invoice_items.quantity,
                    invoice_items.unit_price,
                    invoice_items.line_total
                FROM invoice_items
                LEFT JOIN products ON products.product_code = invoice_items.product_code
                WHERE invoice_items.invoice_no = ?
                ORDER BY invoice_items.id ASC
                """,
                (invoice_no,),
            ).fetchall()
            return {
                "invoice": dict(invoice),
                "items": [dict(row) for row in items],
            }


class ReportRepository:
    def revenue_today(self) -> int:
        day = today_utc7()
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                WHERE substr(created_at, 1, 10) = ?
                """,
                (day,),
            ).fetchone()
            return int(row["total"])

    def revenue_month(self) -> int:
        month = today_utc7()[:7]
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                WHERE substr(created_at, 1, 7) = ?
                """,
                (month,),
            ).fetchone()
            return int(row["total"])

    def revenue_by_day(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT substr(created_at, 1, 10) AS day, COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                GROUP BY substr(created_at, 1, 10)
                ORDER BY day DESC
                LIMIT 31
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def revenue_by_month(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT substr(created_at, 1, 7) AS month, COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                GROUP BY substr(created_at, 1, 7)
                ORDER BY month DESC
                LIMIT 24
                """
            ).fetchall()
            return [dict(row) for row in rows]
