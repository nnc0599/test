from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database import connection
from app.database.connection import get_connection
from app.database.schema import init_schema
from app.controllers.order_controller import OrderController
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
                "seller_name": "Nhân viên A",
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
                "seller_name": "Nhân viên B",
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
            quotation_seller = conn.execute(
                "SELECT seller_name FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()[0]

        self.assertEqual(quantity_after_update, 10)
        self.assertEqual(quotation_seller, "Nhân viên B")

    def test_quotation_allows_existing_product_with_zero_stock(self) -> None:
        repo = InvoiceRepository()

        with get_connection() as conn:
            conn.execute(
                "UPDATE products SET quantity = 0 WHERE product_code = ?",
                ("SP_TEST",),
            )

        quotation_id = repo.create_quotation(
            {
                "created_at": "2026-03-19 10:10:00",
                "customer_name": "Bao Gia Het Hang",
                "phone": "0900000005",
                "email": "",
                "tax_code": "",
                "address": "",
                "seller_name": "Nhân viên F",
                "goods_amount": 2000,
                "ship_fee": 0,
                "total_amount": 2000,
                "paid_amount": 0,
                "doc_type": "quotation",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 2,
                    "unit_price": 1000,
                    "line_total": 2000,
                }
            ],
        )

        with get_connection() as conn:
            saved_row = conn.execute(
                "SELECT doc_type FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()
            quantity_after_create = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["doc_type"], "quotation")
        self.assertEqual(quantity_after_create, 0)

    def test_order_and_invoice_reject_existing_product_with_zero_stock(self) -> None:
        repo = InvoiceRepository()

        with get_connection() as conn:
            conn.execute(
                "UPDATE products SET quantity = 0 WHERE product_code = ?",
                ("SP_TEST",),
            )

        line = {
            "product_code": "SP_TEST",
            "product_name": "Test Product",
            "unit": "cai",
            "quantity": 1,
            "unit_price": 1000,
            "line_total": 1000,
        }

        with self.assertRaises(ValueError):
            repo.create_quotation(
                {
                    "created_at": "2026-03-19 10:20:00",
                    "customer_name": "Don Hang Het Hang",
                    "phone": "0900000006",
                    "email": "",
                    "tax_code": "",
                    "address": "",
                    "seller_name": "Nhân viên G",
                    "goods_amount": 1000,
                    "ship_fee": 0,
                    "total_amount": 1000,
                    "paid_amount": 0,
                    "doc_type": "order",
                },
                [line],
            )

        with self.assertRaises(ValueError):
            repo.create_invoice(
                {
                    "invoice_no": "000001",
                    "created_at": "2026-03-19 10:30:00",
                    "customer_name": "Hoa Don Het Hang",
                    "seller_name": "Nhân viên H",
                    "phone": "0900000007",
                    "email": "",
                    "tax_code": "",
                    "address": "",
                    "total_amount": 1000,
                    "paid_amount": 0,
                    "payment_date": "2026-03-19 10:30:00",
                },
                [line],
            )

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
                "seller_name": "Nhân viên C",
                "goods_amount": 4000,
                "ship_fee": 0,
                "total_amount": 4000,
                "paid_amount": 1500,
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

        repo.export_quotation_to_invoice(quotation_id, "000001", export_created_at="2026-03-20 09:30:00")

        with get_connection() as conn:
            quantity_after_export = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]
            exported_row = conn.execute(
                "SELECT status, exported_invoice_no, paid_amount FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()
            invoice_row = conn.execute(
                "SELECT invoice_no, seller_name, created_at FROM invoices WHERE invoice_no = ?",
                ("000001",),
            ).fetchone()
            payment_row = conn.execute(
                "SELECT paid_amount, remaining_amount FROM payments WHERE invoice_no = ?",
                ("000001",),
            ).fetchone()

        self.assertEqual(quantity_after_export, 6)
        self.assertEqual(exported_row["status"], "exported")
        self.assertEqual(exported_row["exported_invoice_no"], "000001")
        self.assertEqual(exported_row["paid_amount"], 1500)
        self.assertIsNotNone(invoice_row)
        self.assertEqual(invoice_row["seller_name"], "Nhân viên C")
        self.assertEqual(invoice_row["created_at"], "2026-03-20 09:30:00")
        self.assertIsNotNone(payment_row)
        self.assertEqual(payment_row["paid_amount"], 1500)
        self.assertEqual(payment_row["remaining_amount"], 2500)

    def test_generate_invoice_no_uses_next_numeric_sequence(self) -> None:
        repo = InvoiceRepository()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO invoices (
                    invoice_no, created_at, customer_name, seller_name, phone, email, tax_code, address, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("000001", "2026-03-19 08:00:00", "Khach A", "Nhan vien", "", "", "", "", 1000),
            )
            conn.execute(
                """
                INSERT INTO invoices (
                    invoice_no, created_at, customer_name, seller_name, phone, email, tax_code, address, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("000009", "2026-03-19 08:30:00", "Khach B", "Nhan vien", "", "", "", "", 2000),
            )

        self.assertEqual(repo.generate_invoice_no(), "000010")

    def test_order_controller_persists_doc_type_for_orders(self) -> None:
        controller = OrderController(
            product_repo=None,
            customer_repo=None,
            invoice_repo=InvoiceRepository(),
        )

        quotation_id = controller.create_quotation(
            {
                "full_name": "Don Hang Test",
                "phone": "0900000003",
                "email": "",
                "tax_code": "",
                "address": "",
            },
            {
                "created_at": "2026-03-19 12:00:00",
                "seller_name": "Nhân viên D",
                "note": "",
                "goods_amount": 2000,
                "ship_fee": 0,
                "total_amount": 2000,
                "paid_amount": 0,
                "doc_type": "order",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 2,
                    "unit_price": 1000,
                    "line_total": 2000,
                }
            ],
        )

        with get_connection() as conn:
            saved_row = conn.execute(
                "SELECT doc_type FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["doc_type"], "order")

        with get_connection() as conn:
            quantity_after_order = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertEqual(quantity_after_order, 8)

    def test_quotation_with_deposit_stays_out_of_quotation_list_and_keeps_stock(self) -> None:
        repo = InvoiceRepository()
        controller = OrderController(
            product_repo=None,
            customer_repo=None,
            invoice_repo=repo,
        )

        repo.create_quotation(
            {
                "created_at": "2026-03-19 13:00:00",
                "customer_name": "Bao Gia Coc",
                "phone": "0900000004",
                "email": "",
                "tax_code": "",
                "address": "",
                "seller_name": "Nhân viên E",
                "goods_amount": 1000,
                "ship_fee": 0,
                "total_amount": 1000,
                "paid_amount": 500,
                "status": "pending",
                "export_path": "",
                "exported_invoice_no": "",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 1,
                    "unit_price": 1000,
                    "line_total": 1000,
                }
            ],
        )

        order_rows = controller.list_recent_orders(10)
        quotation_rows = controller.list_recent_pending_quotations(10)

        with get_connection() as conn:
            quantity_after_create = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertTrue(any(int(row.get("paid_amount", 0) or 0) == 500 for row in order_rows))
        self.assertFalse(any(int(row.get("paid_amount", 0) or 0) == 500 for row in quotation_rows))
        self.assertEqual(quantity_after_create, 10)

    def test_controller_does_not_convert_saved_quotation_with_deposit_to_order(self) -> None:
        controller = OrderController(
            product_repo=None,
            customer_repo=None,
            invoice_repo=InvoiceRepository(),
        )

        quotation_id = controller.create_quotation(
            {
                "full_name": "Bao Gia Co Coc",
                "phone": "0900000008",
                "email": "",
                "tax_code": "",
                "address": "",
            },
            {
                "created_at": "2026-03-19 13:30:00",
                "seller_name": "Nhân viên I",
                "note": "",
                "goods_amount": 1000,
                "ship_fee": 0,
                "total_amount": 1000,
                "paid_amount": 500,
                "doc_type": "quotation",
            },
            [
                {
                    "product_code": "SP_TEST",
                    "product_name": "Test Product",
                    "unit": "cai",
                    "quantity": 1,
                    "unit_price": 1000,
                    "line_total": 1000,
                }
            ],
        )

        with get_connection() as conn:
            saved_row = conn.execute(
                "SELECT doc_type FROM quotations WHERE id = ?",
                (quotation_id,),
            ).fetchone()
            quantity_after_create = conn.execute(
                "SELECT quantity FROM products WHERE product_code = ?",
                ("SP_TEST",),
            ).fetchone()[0]

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["doc_type"], "quotation")
        self.assertEqual(quantity_after_create, 10)


if __name__ == "__main__":
    unittest.main()