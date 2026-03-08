from app.models.repositories import ReportRepository


class ReportController:
    def __init__(self, repo: ReportRepository):
        self.repo = repo

    def revenue_report(self, period_type: str, period_value: str) -> dict:
        rows = self.repo.revenue_by_period(period_type, period_value)
        return {
            "rows": rows,
            "invoice_count": len(rows),
            "total_amount": sum(int(item["total_amount"]) for item in rows),
        }

    def sold_products_report(self, period_type: str, period_value: str) -> dict:
        rows = self.repo.sold_products_by_period(period_type, period_value)
        return {
            "rows": rows,
            "product_count": len(rows),
            "total_quantity": sum(int(item["sold_quantity"]) for item in rows),
            "total_amount": sum(int(item["sold_amount"]) for item in rows),
        }

    def stock_products_report(self) -> dict:
        rows = self.repo.stock_products()
        return {
            "rows": rows,
            "product_count": len(rows),
            "total_quantity": sum(int(item["quantity"]) for item in rows),
            "total_value": sum(int(item["quantity"]) * int(item["sale_price"]) for item in rows),
        }
