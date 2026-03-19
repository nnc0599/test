from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database import connection
from app.database.connection import get_connection
from app.database.schema import init_schema
from app.models.repositories import InvoiceRepository


class QuotationInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._original_data_dir = connection.DATA_DIR
        self._original_db_path = connection.DB_PATH

        temp_path = Path(self._temp_dir.name)
        connection.DATA_DIR = temp_path
        connection.DB_PATH = temp_path / "sales_app.db"

        init_schema()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO products (
                    product_code,
                    name,
                    category,
                    unit,
                    quantity,
                    sale_price,
                    retail_price,
                    worker_price,
                    dealer_price,
                    updated_at,
                    description,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "SP_TEST",
                    "Test Product",
                    "Phụ kiện",
                    "cai",
                    10,
                    1000,
                    1000,
                    900,
                    800,
                    "2026-03-19 10:00:00",
                    "",
                    "",
                ),
            )

    def tearDown(self) -> None:
        connection.DATA_DIR = self._original_data_dir
        connection.DB_PATH = self._original_db_path
        self._temp_dir.cleanup()

    def test_create_and_update_quotation_do_not_reduce_stock(self) -> None:
        repo = InvoiceRepository()

        quotation_id = repo.create_quotation(
            {
                "created_at": "2026-03-19 10:00:00",
                "customer_name": "Bao Gia Test",
                "phone": "0900000001",
                "email": "",
                "tax_code": "",
                "address": "",
                "goods_amount": 3000,
                "ship_fee": 0,
                "total_amount": 3000,
                "status": "pending",
                "export_path": "",
                "exported_invoice_no": "",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 3,
                    "unit_price": 1000,
                    "line_total": 3000,
                }
            ],
        )

        with get_connection() as conn:
            quantity_after_create = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertEqual(quantity_after_create, 10)

        repo.update_quotation(
            quotation_id,
            {
                "created_at": "2026-03-19 10:05:00",
                "customer_name": "Bao Gia Test",
                "phone": "0900000001",
                "email": "",
                "tax_code": "",
                "address": "",
                "goods_amount": 5000,
                "ship_fee": 0,
                "total_amount": 5000,
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 5,
                    "unit_price": 1000,
                    "line_total": 5000,
                }
            ],
        )

        with get_connection() as conn:
            quantity_after_update = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertEqual(quantity_after_update, 10)

    def test_export_quotation_to_invoice_reduces_stock(self) -> None:
        repo = InvoiceRepository()

        quotation_id = repo.create_quotation(
            {
                "created_at": "2026-03-19 11:00:00",
                "customer_name": "Bao Gia Test",
                "phone": "0900000002",
                "email": "",
                "tax_code": "",
                "address": "",
                "goods_amount": 4000,
                "ship_fee": 0,
                "total_amount": 4000,
                "status": "pending",
                "export_path": "",
                "exported_invoice_no": "",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 4,
                    "unit_price": 1000,
                    "line_total": 4000,
                }
            ],
        )

        repo.export_quotation_to_invoice(quotation_id, "000001")

        with get_connection() as conn:
            quantity_after_export = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]
            exported_row = conn.execute(
                "SELECT status, exported_invoice_no FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()
            invoice_row = conn.execute(
                "SELECT invoice_no FROM invoices WHERE invoice_no = ?",
                ("000001",),
            ).fetchone()

        self.assertEqual(quantity_after_export, 6)
        self.assertEqual(exported_row["status"], "exported")
        self.assertEqual(exported_row["exported_invoice_no"], "000001")
        self.assertIsNotNone(invoice_row)


if __name__ == "__main__":
    unittest.main()