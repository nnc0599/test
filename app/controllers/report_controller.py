from app.models.repositories import ReportRepository


class ReportController:
    def __init__(self, repo: ReportRepository):
        self.repo = repo

    def summary(self) -> dict:
        return {
            "today": self.repo.revenue_today(),
            "month": self.repo.revenue_month(),
        }

    def by_day(self) -> list[dict]:
        return self.repo.revenue_by_day()

    def by_month(self) -> list[dict]:
        return self.repo.revenue_by_month()
