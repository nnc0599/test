from app.models.repositories import CustomerRepository, InvoiceRepository, ProductRepository
from app.utils.item_sort import sort_items_by_unit_price_desc
from app.utils.time_utils import now_iso_utc7


class OrderController:
    def __init__(
        self,
        product_repo: ProductRepository,
        customer_repo: CustomerRepository,
        invoice_repo: InvoiceRepository,
    ):
        self.product_repo = product_repo
        self.customer_repo = customer_repo
        self.invoice_repo = invoice_repo

    def search_products(self, keyword: str) -> list[dict]:
        if not keyword.strip():
            return self.product_repo.list_products()[:20]
        return self.product_repo.search_products(keyword)

    def list_customers(self) -> list[dict]:
        return self.customer_repo.list_customers()

    def search_customers(self, keyword: str) -> list[dict]:
        if not keyword.strip():
            return self.customer_repo.list_customers()[:20]
        return self.customer_repo.search_customers(keyword)

    def list_invoices(self) -> list[dict]:
        return self.invoice_repo.list_invoices()

    def search_invoices(
        self,
        keyword: str,
        period_type: str = "all",
        period_value: str = "",
    ) -> list[dict]:
        return self.invoice_repo.search_invoices(keyword, period_type, period_value)

    def get_invoice_detail(self, invoice_no: str) -> dict | None:
        detail = self.invoice_repo.get_invoice_detail(invoice_no)
        if not detail:
            return None
        detail["items"] = sort_items_by_unit_price_desc(detail.get("items", []))
        return detail

    def list_recent_quotations(self, limit: int = 50) -> list[dict]:
        return self.invoice_repo.list_recent_quotations(limit)

    def list_recent_orders(self, limit: int = 50) -> list[dict]:
        return [
            row
            for row in self.list_recent_quotations(limit)
            if str(row.get("doc_type") or "quotation") == "order"
            or int(row.get("paid_amount", 0) or 0) > 0
        ]

    def list_recent_pending_quotations(self, limit: int = 50) -> list[dict]:
        return [
            row
            for row in self.list_recent_quotations(limit)
            if str(row.get("doc_type") or "quotation") == "quotation"
            and int(row.get("paid_amount", 0) or 0) <= 0
        ]

    def get_quotation_detail(self, quotation_id: int) -> dict | None:
        detail = self.invoice_repo.get_quotation_detail(quotation_id)
        if not detail:
            return None
        detail["items"] = sort_items_by_unit_price_desc(detail.get("items", []))
        return detail

    def generate_invoice_no(self) -> str:
        return self.invoice_repo.generate_invoice_no()

    def create_invoice(self, customer_data: dict, invoice_data: dict, lines: list[dict]) -> None:
        if not lines:
            raise ValueError("Hóa đơn phải có ít nhất 1 hàng hóa")
        if not customer_data.get("full_name", "").strip():
            raise ValueError("Họ tên khách hàng không được để trống")

        created_at = invoice_data.get("created_at") or now_iso_utc7()

        self.customer_repo.upsert_customer(customer_data)

        payload = {
            "invoice_no": invoice_data["invoice_no"],
            "created_at": created_at,
            "customer_name": customer_data["full_name"],
            "seller_name": invoice_data.get("seller_name", "Cửa hàng"),
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "email": customer_data.get("email", ""),
            "tax_code": customer_data.get("tax_code", ""),
            "total_amount": int(invoice_data["total_amount"]),
            "paid_amount": int(invoice_data.get("paid_amount", 0)),
            "payment_date": invoice_data.get("payment_date", created_at),
        }
        self.invoice_repo.create_invoice(payload, sort_items_by_unit_price_desc(lines))

    def create_quotation(self, customer_data: dict, quotation_data: dict, lines: list[dict]) -> int:
        if not lines:
            raise ValueError("Báo giá phải có ít nhất 1 hàng hóa")
        if not customer_data.get("full_name", "").strip():
            raise ValueError("Họ tên khách hàng không được để trống")

        created_at = quotation_data.get("created_at") or now_iso_utc7()
        paid_amount = int(quotation_data.get("paid_amount", 0))
        doc_type = quotation_data.get("doc_type", "quotation")

        payload = {
            "created_at": created_at,
            "customer_name": customer_data["full_name"],
            "seller_name": quotation_data.get("seller_name", "Cửa hàng"),
            "note": quotation_data.get("note", ""),
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "email": customer_data.get("email", ""),
            "tax_code": customer_data.get("tax_code", ""),
            "goods_amount": int(quotation_data.get("goods_amount", 0)),
            "ship_fee": int(quotation_data.get("ship_fee", 0)),
            "total_amount": int(quotation_data["total_amount"]),
            "paid_amount": paid_amount,
            "export_path": quotation_data.get("export_path", ""),
            "doc_type": doc_type,
        }
        return self.invoice_repo.create_quotation(payload, sort_items_by_unit_price_desc(lines))

    def update_quotation(self, quotation_id: int, customer_data: dict, quotation_data: dict, lines: list[dict]) -> None:
        if not lines:
            raise ValueError("Báo giá phải có ít nhất 1 hàng hóa")
        if not customer_data.get("full_name", "").strip():
            raise ValueError("Họ tên khách hàng không được để trống")

        created_at = quotation_data.get("created_at") or now_iso_utc7()
        paid_amount = int(quotation_data.get("paid_amount", 0))
        doc_type = quotation_data.get("doc_type", "quotation")

        payload = {
            "created_at": created_at,
            "customer_name": customer_data["full_name"],
            "seller_name": quotation_data.get("seller_name", "Cửa hàng"),
            "note": quotation_data.get("note", ""),
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "email": customer_data.get("email", ""),
            "tax_code": customer_data.get("tax_code", ""),
            "goods_amount": int(quotation_data.get("goods_amount", 0)),
            "ship_fee": int(quotation_data.get("ship_fee", 0)),
            "total_amount": int(quotation_data["total_amount"]),
            "paid_amount": paid_amount,
            "doc_type": doc_type,
        }
        self.invoice_repo.update_quotation(quotation_id, payload, sort_items_by_unit_price_desc(lines))

    def update_quotation_export_path(self, quotation_id: int, export_path: str) -> None:
        self.invoice_repo.update_quotation_export_path(quotation_id, export_path)

    def cancel_quotation(self, quotation_id: int) -> None:
        self.invoice_repo.delete_quotation(quotation_id)

    def update_invoice(self, invoice_no: str, customer_data: dict, invoice_data: dict, lines: list[dict]) -> None:
        if not lines:
            raise ValueError("Hóa đơn phải có ít nhất 1 hàng hóa")
        if not customer_data.get("full_name", "").strip():
            raise ValueError("Họ tên khách hàng không được để trống")

        created_at = invoice_data.get("created_at") or now_iso_utc7()
        self.customer_repo.upsert_customer(customer_data)

        payload = {
            "invoice_no": invoice_no,
            "created_at": created_at,
            "customer_name": customer_data["full_name"],
            "seller_name": invoice_data.get("seller_name", "Cửa hàng"),
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "email": customer_data.get("email", ""),
            "tax_code": customer_data.get("tax_code", ""),
            "total_amount": int(invoice_data["total_amount"]),
            "paid_amount": int(invoice_data.get("paid_amount", 0)),
            "payment_date": invoice_data.get("payment_date", created_at),
        }
        self.invoice_repo.update_invoice(invoice_no, payload, sort_items_by_unit_price_desc(lines))

    def delete_invoice(self, invoice_no: str) -> None:
        self.invoice_repo.delete_invoice(invoice_no)

    def export_quotation_to_invoice(self, quotation_id: int, invoice_no: str, export_created_at: str | None = None) -> None:
        detail = self.get_quotation_detail(quotation_id)
        if not detail:
            raise ValueError("Không tìm thấy bản báo giá")

        quotation = detail["quotation"]
        customer_data = {
            "full_name": quotation["customer_name"],
            "phone": quotation.get("phone", ""),
            "address": quotation.get("address", ""),
            "email": quotation.get("email", ""),
            "tax_code": quotation.get("tax_code", ""),
            "note": "Tự động cập nhật khi xuất hóa đơn từ báo giá",
        }
        self.customer_repo.upsert_customer(customer_data)
        self.invoice_repo.export_quotation_to_invoice(quotation_id, invoice_no, export_created_at=export_created_at)
