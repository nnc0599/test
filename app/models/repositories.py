from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Iterable
import re

from app.database.connection import get_connection
from app.utils.time_utils import now_iso_utc7, today_utc7


def _period_bounds(period_type: str, period_value: str) -> tuple[str, str]:
    normalized_type = period_type.strip().lower()
    normalized_value = period_value.strip()

    if normalized_type == "day":
        start = datetime.strptime(normalized_value[:10], "%Y-%m-%d")
        end = start + timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    if normalized_type == "month":
        start = datetime.strptime(f"{normalized_value[:7]}-01", "%Y-%m-%d")
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    if normalized_type == "year":
        year = int(normalized_value[:4])
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    raise ValueError("Kiểu kỳ báo cáo không hợp lệ")


def _prefix_bounds(value: str) -> tuple[str, str]:
    normalized_value = value.strip()
    return normalized_value, f"{normalized_value}\uffff"


def _build_fts5_query(value: str) -> str:
    tokens = [token for token in re.findall(r"\S+", value.strip()) if token]
    if not tokens:
        return ""

    escaped_tokens = []
    for token in tokens:
        escaped_token = token.replace('"', '""')
        escaped_tokens.append(f'"{escaped_token}"*')
    return " AND ".join(escaped_tokens)


class ProductRepository:
    def _search_products_with_fts(
        self,
        conn,
        normalized_keyword: str,
        code_prefix_start: str,
        code_prefix_end: str,
        name_prefix_start: str,
        name_prefix_end: str,
        limit: int,
    ) -> list[dict]:
        fts_query = _build_fts5_query(normalized_keyword)
        if not fts_query:
            return []

        rows = conn.execute(
            """
            WITH prioritized_products AS (
                SELECT
                    product_code,
                    name,
                    category,
                    unit,
                    quantity,
                    sale_price,
                    updated_at,
                    description,
                    note,
                    0 AS priority
                FROM products
                WHERE product_code = ?

                UNION ALL

                SELECT
                    product_code,
                    name,
                    category,
                    unit,
                    quantity,
                    sale_price,
                    updated_at,
                    description,
                    note,
                    1 AS priority
                FROM products
                WHERE product_code >= ? AND product_code < ?
                  AND product_code <> ?

                UNION ALL

                SELECT
                    product_code,
                    name,
                    category,
                    unit,
                    quantity,
                    sale_price,
                    updated_at,
                    description,
                    note,
                    2 AS priority
                FROM products
                WHERE name >= ? COLLATE NOCASE AND name < ? COLLATE NOCASE
                  AND product_code <> ?
                  AND NOT (product_code >= ? AND product_code < ?)

                UNION ALL

                SELECT
                    products.product_code,
                    products.name,
                    products.category,
                    products.unit,
                    products.quantity,
                    products.sale_price,
                    products.updated_at,
                    products.description,
                    products.note,
                    3 AS priority
                FROM products_fts
                INNER JOIN products ON products.rowid = products_fts.rowid
                WHERE products_fts MATCH ?
                  AND products.product_code <> ?
                  AND NOT (products.product_code >= ? AND products.product_code < ?)
                  AND NOT (products.name >= ? COLLATE NOCASE AND products.name < ? COLLATE NOCASE)
            )
            SELECT
                product_code,
                name,
                category,
                unit,
                quantity,
                sale_price,
                updated_at,
                description,
                note
            FROM prioritized_products
            ORDER BY
                priority ASC,
                name COLLATE NOCASE ASC,
                updated_at DESC,
                product_code ASC
            LIMIT ?
            """,
            (
                normalized_keyword,
                code_prefix_start,
                code_prefix_end,
                normalized_keyword,
                name_prefix_start,
                name_prefix_end,
                normalized_keyword,
                code_prefix_start,
                code_prefix_end,
                fts_query,
                normalized_keyword,
                code_prefix_start,
                code_prefix_end,
                name_prefix_start,
                name_prefix_end,
                limit,
            ),
        ).fetchall()
        return [dict(row) for row in rows]

    def _search_products_with_like_fallback(
        self,
        conn,
        normalized_keyword: str,
        code_prefix_start: str,
        code_prefix_end: str,
        name_prefix_start: str,
        name_prefix_end: str,
        excluded_codes: list[str],
        limit: int,
    ) -> list[dict]:
        if limit <= 0:
            return []

        contains_kw = f"%{normalized_keyword}%"
        excluded_clause = ""
        params: list[str | int] = [
            contains_kw,
            contains_kw,
            normalized_keyword,
            code_prefix_start,
            code_prefix_end,
            name_prefix_start,
            name_prefix_end,
        ]

        if excluded_codes:
            placeholders = ", ".join("?" for _ in excluded_codes)
            excluded_clause = f"AND product_code NOT IN ({placeholders})"
            params.extend(excluded_codes)

        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT
                product_code,
                name,
                category,
                unit,
                quantity,
                sale_price,
                updated_at,
                description,
                note
            FROM products
            WHERE (name LIKE ? OR description LIKE ?)
              AND product_code <> ?
              AND NOT (product_code >= ? AND product_code < ?)
              AND NOT (name >= ? COLLATE NOCASE AND name < ? COLLATE NOCASE)
              {excluded_clause}
            ORDER BY name COLLATE NOCASE ASC, updated_at DESC, product_code ASC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_products(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_code, name, category, unit, quantity, sale_price, updated_at, description, note
                FROM products
                ORDER BY updated_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_product(self, product_code: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT product_code, name, category, unit, quantity, sale_price, updated_at, description, note
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
                    product_code, name, category, unit, quantity, sale_price, updated_at, description, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["product_code"],
                    payload["name"],
                    payload.get("category", ""),
                    payload.get("unit", ""),
                    int(payload.get("quantity", 0)),
                    int(payload.get("sale_price", 0)),
                    now_iso_utc7(),
                    payload.get("description", ""),
                    payload.get("note", ""),
                ),
            )

    def add_products(self, payloads: list[dict]) -> None:
        product_codes = [payload["product_code"].strip() for payload in payloads]
        duplicated_codes = sorted(
            code for code, count in Counter(product_codes).items() if code and count > 1
        )
        if duplicated_codes:
            raise ValueError(
                "Mã sản phẩm bị trùng trong file: " + ", ".join(duplicated_codes)
            )

        with get_connection() as conn:
            placeholders = ", ".join("?" for _ in product_codes)
            existing_rows = conn.execute(
                f"SELECT product_code FROM products WHERE product_code IN ({placeholders})",
                product_codes,
            ).fetchall()
            existing_codes = sorted(row["product_code"] for row in existing_rows)
            if existing_codes:
                raise ValueError(
                    "Mã sản phẩm đã tồn tại: " + ", ".join(existing_codes)
                )

            current_time = now_iso_utc7()
            conn.executemany(
                """
                INSERT INTO products (
                    product_code, name, category, unit, quantity, sale_price, updated_at, description, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        payload["product_code"],
                        payload.get("name", ""),
                        payload.get("category", ""),
                        payload.get("unit", ""),
                        int(payload.get("quantity", 0)),
                        int(payload.get("sale_price", 0)),
                        current_time,
                        payload.get("description", ""),
                        payload.get("note", ""),
                    )
                    for payload in payloads
                ],
            )

    def update_product(self, product_code: str, payload: dict) -> None:
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT product_code, name, category, unit, quantity, sale_price, updated_at, description, note
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
                    category = ?,
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
                    payload.get("category", ""),
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
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return []

        code_prefix_start, code_prefix_end = _prefix_bounds(normalized_keyword)
        name_prefix_start, name_prefix_end = _prefix_bounds(normalized_keyword)
        with get_connection() as conn:
            try:
                rows = self._search_products_with_fts(
                    conn,
                    normalized_keyword,
                    code_prefix_start,
                    code_prefix_end,
                    name_prefix_start,
                    name_prefix_end,
                    20,
                )
            except Exception:
                rows = []

            if len(rows) >= 20:
                return rows

            excluded_codes = [str(row["product_code"]) for row in rows]
            fallback_rows = self._search_products_with_like_fallback(
                conn,
                normalized_keyword,
                code_prefix_start,
                code_prefix_end,
                name_prefix_start,
                name_prefix_end,
                excluded_codes,
                20 - len(rows),
            )
            return rows + fallback_rows

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

    def update_quotation(self, quotation_id: int, payload: dict, lines: list[dict]) -> None:
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id, status
                FROM quotations
                WHERE id = ?
                """,
                (quotation_id,),
            ).fetchone()
            if not existing:
                raise ValueError("Không tìm thấy bản báo giá")
            if str(existing["status"] or "") != "pending":
                raise ValueError("Bản báo giá này không còn khả dụng để chỉnh sửa")

            conn.execute(
                """
                UPDATE quotations
                SET
                    created_at = ?,
                    customer_name = ?,
                    phone = ?,
                    email = ?,
                    tax_code = ?,
                    address = ?,
                    goods_amount = ?,
                    ship_fee = ?,
                    total_amount = ?,
                    status = 'pending',
                    exported_invoice_no = ''
                WHERE id = ?
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
                    quotation_id,
                ),
            )

            conn.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quotation_id,))
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
                    quotation_items.product_code,
                    quotation_items.product_name,
                    COALESCE(products.category, '') AS category,
                    quotation_items.unit,
                    quotation_items.quantity,
                    quotation_items.unit_price,
                    quotation_items.line_total
                FROM quotation_items
                LEFT JOIN products ON products.product_code = quotation_items.product_code
                WHERE quotation_items.quotation_id = ?
                ORDER BY quotation_items.unit_price DESC, quotation_items.line_total DESC, quotation_items.product_name COLLATE NOCASE ASC, quotation_items.id ASC
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
                    quotation_items.product_code,
                    quotation_items.product_name,
                    COALESCE(products.category, '') AS category,
                    quotation_items.unit,
                    quotation_items.quantity,
                    quotation_items.unit_price,
                    quotation_items.line_total
                FROM quotation_items
                LEFT JOIN products ON products.product_code = quotation_items.product_code
                WHERE quotation_items.quotation_id = ?
                ORDER BY quotation_items.unit_price DESC, quotation_items.line_total DESC, quotation_items.product_name COLLATE NOCASE ASC, quotation_items.id ASC
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
        if normalized_period_type in {"day", "month"} and period_value:
            start, end = _period_bounds(normalized_period_type, period_value)
            clauses.append("invoices.created_at >= ? AND invoices.created_at < ?")
            params.extend([start, end])

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
                    COALESCE(products.category, '') AS category,
                    COALESCE(invoice_items.unit, products.unit, '') AS unit,
                    invoice_items.quantity,
                    invoice_items.unit_price,
                    invoice_items.line_total
                FROM invoice_items
                LEFT JOIN products ON products.product_code = invoice_items.product_code
                WHERE invoice_items.invoice_no = ?
                ORDER BY invoice_items.unit_price DESC, invoice_items.line_total DESC, invoice_items.product_name COLLATE NOCASE ASC, invoice_items.id ASC
                """,
                (invoice_no,),
            ).fetchall()
            return {
                "invoice": dict(invoice),
                "items": [dict(row) for row in items],
            }

    def update_invoice(self, invoice_no: str, payload: dict, lines: list[dict]) -> None:
        """Cập nhật hóa đơn: hoàn kho cũ, trừ kho mới, cập nhật bảng invoices/invoice_items/payments."""
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT invoice_no FROM invoices WHERE invoice_no = ?",
                (invoice_no,),
            ).fetchone()
            if not existing:
                raise ValueError("Không tìm thấy hóa đơn cần cập nhật")

            # Hoàn lại tồn kho của các mặt hàng cũ
            old_items = conn.execute(
                "SELECT product_code, quantity FROM invoice_items WHERE invoice_no = ?",
                (invoice_no,),
            ).fetchall()
            for old_item in old_items:
                conn.execute(
                    "UPDATE products SET quantity = quantity + ? WHERE product_code = ?",
                    (int(old_item["quantity"]), old_item["product_code"]),
                )

            # Xóa các dòng hàng hóa cũ (payments cũ cũng xóa luôn)
            conn.execute("DELETE FROM invoice_items WHERE invoice_no = ?", (invoice_no,))
            conn.execute("DELETE FROM payments WHERE invoice_no = ?", (invoice_no,))

            # Cập nhật thông tin header hóa đơn
            conn.execute(
                """
                UPDATE invoices
                SET
                    created_at = ?,
                    customer_name = ?,
                    phone = ?,
                    email = ?,
                    tax_code = ?,
                    address = ?,
                    total_amount = ?
                WHERE invoice_no = ?
                """,
                (
                    payload["created_at"],
                    payload["customer_name"],
                    payload.get("phone", ""),
                    payload.get("email", ""),
                    payload.get("tax_code", ""),
                    payload.get("address", ""),
                    int(payload["total_amount"]),
                    invoice_no,
                ),
            )

            # Chèn lại dòng hàng hóa mới và trừ kho
            conn.executemany(
                """
                INSERT INTO invoice_items (
                    invoice_no, product_code, product_name, unit, quantity, unit_price, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        invoice_no,
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
                    (int(line["quantity"]), line["product_code"], int(line["quantity"])),
                )
                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Sản phẩm {line['product_code']} không đủ số lượng để xuất kho."
                    )

            # Tạo lại bản ghi thanh toán
            total = int(payload["total_amount"])
            conn.execute(
                """
                INSERT INTO payments (
                    invoice_no, customer_name, purchase_date, payment_date,
                    total_amount, paid_amount, remaining_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_no,
                    payload["customer_name"],
                    payload["created_at"],
                    payload.get("payment_date", payload["created_at"]),
                    total,
                    int(payload.get("paid_amount", 0)),
                    total - int(payload.get("paid_amount", 0)),
                ),
            )

    def delete_invoice(self, invoice_no: str) -> None:
        """Xóa hóa đơn: hoàn kho đầy đủ rồi xóa bản ghi (CASCADE xóa invoice_items và payments)."""
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT invoice_no FROM invoices WHERE invoice_no = ?",
                (invoice_no,),
            ).fetchone()
            if not existing:
                raise ValueError("Không tìm thấy hóa đơn cần xóa")

            # Hoàn lại tồn kho
            old_items = conn.execute(
                "SELECT product_code, quantity FROM invoice_items WHERE invoice_no = ?",
                (invoice_no,),
            ).fetchall()
            for old_item in old_items:
                conn.execute(
                    "UPDATE products SET quantity = quantity + ? WHERE product_code = ?",
                    (int(old_item["quantity"]), old_item["product_code"]),
                )

            # Xóa hóa đơn; invoice_items và payments tự xóa theo CASCADE
            conn.execute("DELETE FROM invoices WHERE invoice_no = ?", (invoice_no,))


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

    @staticmethod
    def _period_bounds(period_type: str, period_value: str) -> tuple[str, str]:
        return _period_bounds(period_type, period_value)

    def revenue_today(self) -> int:
        day = today_utc7()
        start, end = self._period_bounds("day", day)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                WHERE created_at >= ? AND created_at < ?
                """,
                (start, end),
            ).fetchone()
            return int(row["total"])

    def revenue_month(self) -> int:
        month = today_utc7()[:7]
        start, end = self._period_bounds("month", month)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM invoices
                WHERE created_at >= ? AND created_at < ?
                """,
                (start, end),
            ).fetchone()
            return int(row["total"])

    def revenue_by_period(self, period_type: str, period_value: str) -> list[dict]:
        start, end = self._period_bounds(period_type, period_value)
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT invoice_no, created_at, customer_name, phone, total_amount
                FROM invoices
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at DESC, invoice_no DESC
                """,
                (start, end),
            ).fetchall()
            return [dict(row) for row in rows]

    def sold_products_by_period(self, period_type: str, period_value: str) -> list[dict]:
        start, end = self._period_bounds(period_type, period_value)
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    invoice_items.product_code,
                    invoice_items.product_name,
                    COALESCE(products.category, '') AS category,
                    COALESCE(invoice_items.unit, '') AS unit,
                    SUM(invoice_items.quantity) AS sold_quantity,
                    SUM(invoice_items.line_total) AS sold_amount
                FROM invoice_items
                INNER JOIN invoices ON invoices.invoice_no = invoice_items.invoice_no
                LEFT JOIN products ON products.product_code = invoice_items.product_code
                WHERE invoices.created_at >= ? AND invoices.created_at < ?
                GROUP BY invoice_items.product_code, invoice_items.product_name, COALESCE(products.category, ''), COALESCE(invoice_items.unit, '')
                ORDER BY sold_quantity DESC, sold_amount DESC, invoice_items.product_name ASC
                """,
                (start, end),
            ).fetchall()
            return [dict(row) for row in rows]

    def stock_products(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_code, name, category, quantity, sale_price
                FROM products
                WHERE quantity > 0
                ORDER BY name COLLATE NOCASE ASC, product_code ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]
