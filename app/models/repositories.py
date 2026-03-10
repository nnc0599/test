from __future__ import annotations

from typing import Iterable
import re

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
    def generate_invoice_no(self) -> str:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT invoice_no
                FROM invoices
                """
            ).fetchall()

        max_number = 0
        for row in rows:
            invoice_no = str(row["invoice_no"] or "").strip()
            if re.fullmatch(r"\d{6}", invoice_no):
                max_number = max(max_number, int(invoice_no))

        return f"{max_number + 1:06d}"

    def _insert_invoice_records(self, conn, payload: dict, lines: list[dict]) -> None:
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

    def create_invoice(self, payload: dict, lines: list[dict]) -> None:
        with get_connection() as conn:
            self._insert_invoice_records(conn, payload, lines)

    def create_quotation(self, payload: dict, lines: list[dict]) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quotations (
                    created_at,
                    customer_name,
                    phone,
                    email,
                    tax_code,
                    address,
                    goods_amount,
                    ship_fee,
                    total_amount,
                    status,
                    export_path,
                    exported_invoice_no
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["created_at"],
                    payload["customer_name"],
                    payload.get("phone", ""),
                    payload.get("email", ""),
                    payload.get("tax_code", ""),
                    payload.get("address", ""),
                    int(payload.get("goods_amount", 0)),
                    int(payload.get("ship_fee", 0)),
                    int(payload["total_amount"]),
                    payload.get("status", "pending"),
                    payload.get("export_path", ""),
                    payload.get("exported_invoice_no", ""),
                ),
            )
            quotation_id = int(cursor.lastrowid)

            conn.executemany(
                """
                INSERT INTO quotation_items (
                    quotation_id, product_code, product_name, unit, quantity, unit_price, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        quotation_id,
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
            return quotation_id

    def update_quotation_export_path(self, quotation_id: int, export_path: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE quotations SET export_path = ? WHERE id = ?",
                (export_path, quotation_id),
            )

    def list_recent_quotations(self, limit: int = 50) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, customer_name, phone, goods_amount, total_amount, created_at
                FROM quotations
                WHERE status = 'pending'
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_quotation_detail(self, quotation_id: int) -> dict | None:
        with get_connection() as conn:
            quotation = conn.execute(
                """
                SELECT
                    id,
                    created_at,
                    customer_name,
                    phone,
                    email,
                    tax_code,
                    address,
                    goods_amount,
                    ship_fee,
                    total_amount,
                    status,
                    export_path,
                    exported_invoice_no
                FROM quotations
                WHERE id = ?
                """,
                (quotation_id,),
            ).fetchone()
            if not quotation:
                return None

            items = conn.execute(
                """
                SELECT
                    product_code,
                    product_name,
                    unit,
                    quantity,
                    unit_price,
                    line_total
                FROM quotation_items
                WHERE quotation_id = ?
                ORDER BY id ASC
                """,
                (quotation_id,),
            ).fetchall()
            return {
                "quotation": dict(quotation),
                "items": [dict(row) for row in items],
            }

    def delete_quotation(self, quotation_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM quotations WHERE id = ?", (quotation_id,))

    def export_quotation_to_invoice(self, quotation_id: int, invoice_no: str) -> None:
        with get_connection() as conn:
            quotation = conn.execute(
                """
                SELECT
                    id,
                    created_at,
                    customer_name,
                    phone,
                    email,
                    tax_code,
                    address,
                    total_amount,
                    status
                FROM quotations
                WHERE id = ?
                """,
                (quotation_id,),
            ).fetchone()
            if not quotation:
                raise ValueError("Không tìm thấy bản báo giá")
            if str(quotation["status"] or "") != "pending":
                raise ValueError("Bản báo giá này không còn khả dụng để xuất hóa đơn")

            items = conn.execute(
                """
                SELECT
                    product_code,
                    product_name,
                    unit,
                    quantity,
                    unit_price,
                    line_total
                FROM quotation_items
                WHERE quotation_id = ?
                ORDER BY id ASC
                """,
                (quotation_id,),
            ).fetchall()
            item_rows = [dict(row) for row in items]
            if not item_rows:
                raise ValueError("Bản báo giá không có sản phẩm để xuất hóa đơn")

            payload = {
                "invoice_no": invoice_no,
                "created_at": quotation["created_at"],
                "customer_name": quotation["customer_name"],
                "phone": quotation["phone"],
                "email": quotation["email"],
                "tax_code": quotation["tax_code"],
                "address": quotation["address"],
                "total_amount": int(quotation["total_amount"]),
                "paid_amount": 0,
                "payment_date": quotation["created_at"],
            }
            self._insert_invoice_records(conn, payload, item_rows)
            conn.execute(
                """
                UPDATE quotations
                SET status = 'exported', exported_invoice_no = ?
                WHERE id = ?
                """,
                (invoice_no, quotation_id),
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

    def search_invoices(
        self,
        keyword: str,
        period_type: str = "all",
        period_value: str = "",
    ) -> list[dict]:
        normalized_keyword = keyword.strip()
        clauses: list[str] = []
        params: list[str] = []

        if normalized_keyword:
            like_keyword = f"%{normalized_keyword}%"
            clauses.append("(invoices.invoice_no LIKE ? OR invoices.customer_name LIKE ? OR invoices.phone LIKE ?)")
            params.extend([like_keyword, like_keyword, like_keyword])

        normalized_period_type = period_type.strip().lower()
        if normalized_period_type == "day" and period_value:
            clauses.append("substr(invoices.created_at, 1, 10) = ?")
            params.append(period_value[:10])
        elif normalized_period_type == "month" and period_value:
            clauses.append("substr(invoices.created_at, 1, 7) = ?")
            params.append(period_value[:7])

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with get_connection() as conn:
            rows = conn.execute(
                f"""
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
                {where_clause}
                GROUP BY
                    invoices.invoice_no,
                    invoices.created_at,
                    invoices.customer_name,
                    invoices.phone,
                    invoices.email,
                    invoices.tax_code,
                    invoices.address,
                    invoices.total_amount
                ORDER BY invoices.created_at DESC, invoices.invoice_no DESC
                LIMIT 200
                """,
                tuple(params),
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
    @staticmethod
    def _period_prefix(period_type: str, period_value: str) -> tuple[int, str]:
        normalized_type = period_type.strip().lower()
        period_lengths = {
            "day": 10,
            "month": 7,
            "year": 4,
        }
        if normalized_type not in period_lengths:
            raise ValueError("Kiểu kỳ báo cáo không hợp lệ")

        length = period_lengths[normalized_type]
        normalized_value = period_value.strip()[:length]
        return length, normalized_value

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

    def revenue_by_period(self, period_type: str, period_value: str) -> list[dict]:
        prefix_length, prefix_value = self._period_prefix(period_type, period_value)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT invoice_no, created_at, customer_name, phone, total_amount
                FROM invoices
                WHERE substr(created_at, 1, {prefix_length}) = ?
                ORDER BY created_at DESC, invoice_no DESC
                """,
                (prefix_value,),
            ).fetchall()
            return [dict(row) for row in rows]

    def sold_products_by_period(self, period_type: str, period_value: str) -> list[dict]:
        prefix_length, prefix_value = self._period_prefix(period_type, period_value)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    invoice_items.product_code,
                    invoice_items.product_name,
                    COALESCE(invoice_items.unit, '') AS unit,
                    SUM(invoice_items.quantity) AS sold_quantity,
                    SUM(invoice_items.line_total) AS sold_amount
                FROM invoice_items
                INNER JOIN invoices ON invoices.invoice_no = invoice_items.invoice_no
                WHERE substr(invoices.created_at, 1, {prefix_length}) = ?
                GROUP BY invoice_items.product_code, invoice_items.product_name, COALESCE(invoice_items.unit, '')
                ORDER BY sold_quantity DESC, sold_amount DESC, invoice_items.product_name ASC
                """,
                (prefix_value,),
            ).fetchall()
            return [dict(row) for row in rows]

    def stock_products(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_code, name, quantity, sale_price
                FROM products
                WHERE quantity > 0
                ORDER BY name ASC, product_code ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]
