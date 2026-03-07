from app.models.repositories import CustomerRepository, InvoiceRepository, ProductRepository
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

    def get_invoice_detail(self, invoice_no: str) -> dict | None:
        return self.invoice_repo.get_invoice_detail(invoice_no)

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
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "email": customer_data.get("email", ""),
            "tax_code": customer_data.get("tax_code", ""),
            "total_amount": int(invoice_data["total_amount"]),
            "paid_amount": int(invoice_data.get("paid_amount", 0)),
            "payment_date": invoice_data.get("payment_date", created_at),
        }
        self.invoice_repo.create_invoice(payload, lines)
