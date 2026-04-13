from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database import connection
from app.database.connection import get_connection
from app.database.schema import init_schema
from app.models.repositories import InvoiceRepository
from app.utils.invoice_attachments import (
    cleanup_obsolete_invoice_attachments,
    delete_invoice_attachment_dir,
    invoice_attachment_dir,
    stage_invoice_attachments,
)


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
                "SELECT invoice_no, seller_name FROM invoices WHERE invoice_no = ?",
                ("000001",),
            ).fetchone()

        self.assertEqual(quantity_after_export, 6)
        self.assertEqual(exported_row["status"], "exported")
        self.assertEqual(exported_row["exported_invoice_no"], "000001")
        self.assertIsNotNone(invoice_row)
        self.assertEqual(invoice_row["seller_name"], "Nhân viên C")

    def test_create_and_update_invoice_persist_attachment_paths(self) -> None:
        repo = InvoiceRepository()

        repo.create_invoice(
            {
                "invoice_no": "000123",
                "created_at": "2026-03-19 12:00:00",
                "customer_name": "Khach A",
                "phone": "0900000003",
                "email": "",
                "tax_code": "",
                "address": "Dia chi A",
                "seller_name": "Nhân viên D",
                "electronic_invoice_path": "/tmp/hoa_don_dien_tu.pdf",
                "warehouse_invoice_path": "/tmp/hoa_don_xuat_kho.pdf",
                "total_amount": 2000,
                "paid_amount": 0,
                "payment_date": "2026-03-19 12:00:00",
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

        created_detail = repo.get_invoice_detail("000123")
        self.assertIsNotNone(created_detail)
        self.assertEqual(created_detail["invoice"]["electronic_invoice_path"], "/tmp/hoa_don_dien_tu.pdf")
        self.assertEqual(created_detail["invoice"]["warehouse_invoice_path"], "/tmp/hoa_don_xuat_kho.pdf")

        repo.update_invoice(
            "000123",
            {
                "created_at": "2026-03-19 12:30:00",
                "customer_name": "Khach A",
                "phone": "0900000003",
                "email": "",
                "tax_code": "",
                "address": "Dia chi B",
                "seller_name": "Nhân viên E",
                "electronic_invoice_path": "/tmp/hoa_don_dien_tu_v2.pdf",
                "warehouse_invoice_path": "",
                "total_amount": 3000,
                "paid_amount": 0,
                "payment_date": "2026-03-19 12:30:00",
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

        updated_detail = repo.get_invoice_detail("000123")
        self.assertIsNotNone(updated_detail)
        self.assertEqual(updated_detail["invoice"]["electronic_invoice_path"], "/tmp/hoa_don_dien_tu_v2.pdf")
        self.assertEqual(updated_detail["invoice"]["warehouse_invoice_path"], "")

    def test_stage_invoice_attachments_copies_into_app_data_dir(self) -> None:
        source_electronic = Path(self._temp_dir.name) / "hoa_don_dien_tu.pdf"
        source_warehouse = Path(self._temp_dir.name) / "hoa_don_xuat_kho.pdf"
        source_electronic.write_text("electronic", encoding="utf-8")
        source_warehouse.write_text("warehouse", encoding="utf-8")

        staged_data, created_paths, kept_paths = stage_invoice_attachments(
            "000456",
            {
                "electronic_invoice_path": str(source_electronic),
                "warehouse_invoice_path": str(source_warehouse),
            },
        )

        electronic_copy = Path(staged_data["electronic_invoice_path"])
        warehouse_copy = Path(staged_data["warehouse_invoice_path"])
        target_dir = invoice_attachment_dir("000456")

        self.assertTrue(electronic_copy.exists())
        self.assertTrue(warehouse_copy.exists())
        self.assertEqual(electronic_copy.parent, target_dir)
        self.assertEqual(warehouse_copy.parent, target_dir)
        self.assertEqual(len(created_paths), 2)
        self.assertEqual(len(kept_paths), 2)
        self.assertEqual(electronic_copy.read_text(encoding="utf-8"), "electronic")
        self.assertEqual(warehouse_copy.read_text(encoding="utf-8"), "warehouse")

        replacement_electronic = Path(self._temp_dir.name) / "hoa_don_dien_tu_moi.pdf"
        replacement_electronic.write_text("electronic-v2", encoding="utf-8")
        restaged_data, _, new_kept_paths = stage_invoice_attachments(
            "000456",
            {
                "electronic_invoice_path": str(replacement_electronic),
                "warehouse_invoice_path": "",
            },
        )

        cleanup_obsolete_invoice_attachments("000456", new_kept_paths)

        new_electronic_copy = Path(restaged_data["electronic_invoice_path"])
        self.assertTrue(new_electronic_copy.exists())
        self.assertEqual(new_electronic_copy.read_text(encoding="utf-8"), "electronic-v2")
        self.assertFalse(electronic_copy.exists())
        self.assertFalse(warehouse_copy.exists())

        delete_invoice_attachment_dir("000456")
        self.assertFalse(target_dir.exists())


if __name__ == "__main__":
    unittest.main()