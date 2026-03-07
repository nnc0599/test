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

    def create_invoice(self, customer_data: dict, invoice_data: dict, lines: list[dict]) -> None:
        if not lines:
            raise ValueError("Hoa don phai co it nhat 1 hang hoa")
        if not customer_data.get("full_name", "").strip():
            raise ValueError("Ho ten khach hang khong duoc de trong")
        if not customer_data.get("customer_code", "").strip():
            raise ValueError("Ma khach hang khong duoc de trong")

        created_at = invoice_data.get("created_at") or now_iso_utc7()

        self.customer_repo.upsert_customer(customer_data)

        payload = {
            "invoice_no": invoice_data["invoice_no"],
            "created_at": created_at,
            "customer_code": customer_data["customer_code"],
            "customer_name": customer_data["full_name"],
            "phone": customer_data.get("phone", ""),
            "address": customer_data.get("address", ""),
            "ship_fee": int(invoice_data.get("ship_fee", 0)),
            "total_amount": int(invoice_data["total_amount"]),
            "paid_amount": int(invoice_data.get("paid_amount", 0)),
            "payment_date": invoice_data.get("payment_date", created_at),
        }
        self.invoice_repo.create_invoice(payload, lines)
